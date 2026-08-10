## Context

`git-commit-files` currently selects Octokit for GitHub and a local Git/SSH clone for Bitbucket. The SSH client already implements the repository operations required by commit and full scans, but it hard-codes `bitbucket.org`, reads only `bitbucket_ssh_private_key`, and stores clone state on a singleton provider while SQS records are processed concurrently.

The target state is one SSH-based access path for GitHub and Bitbucket without changing the MCP request contract, scan-mode behavior, S3 layout, or result events.

## Goals / Non-Goals

**Goals:**

- Use Git/SSH for all supported GitHub and Bitbucket repository access.
- Resolve the SSH host and private-key parameter internally from the repository URL.
- Preserve existing commit/full scan behavior and output contracts.
- Prevent concurrent jobs from sharing clone, key-file, or resolved-ref state.
- Remove API-only clients, credentials, tests, mocks, and dependencies.

**Non-Goals:**

- Supporting additional Git hosts.
- Changing how commit files or full snapshots are selected.
- Redesigning encrypted parameter storage.
- Changing SSH host-key verification policy.
- Accepting credentials or parameter identifiers from MCP input.

## Decisions

### Use a host configuration map

The repository factory will parse and validate the exact host, then resolve an internal configuration:

| Host | SSH user | Private-key parameter |
|---|---|---|
| `github.com` | `git` | `github_ssh_private_key` |
| `bitbucket.org` | `git` | `bitbucket_ssh_private_key` |

The SSH client will receive the validated repository coordinates and selected parameter identifier. It will not infer credentials from caller-controlled input.

Alternative considered: select credentials from an MCP provider or access-mode field. This adds public API surface without adding useful behavior once API access is removed.

### Normalize HTTPS and SSH repository URLs to canonical SSH URLs

Both `https://host/namespace/repository[.git]` and `git@host:namespace/repository[.git]` will be accepted for supported hosts and normalized to `git@host:namespace/repository.git`. Parsing will compare the exact host rather than using substring matching.

Alternative considered: require callers to send only SSH URLs. This would unnecessarily break existing callers that already send GitHub HTTPS URLs.

### Create isolated SSH client state per job

`RepoFactoryService.getClientForRepoUrl()` will return a fresh SSH client/session for each processing request. The parameter service and command-execution infrastructure may remain shared, but `cloneUrl`, temporary paths, and resolved SHA MUST belong to one job only.

Alternative considered: keep the singleton and process SQS records sequentially. That avoids races but reduces throughput and leaves the client unsafe for any other concurrent caller.

### Keep secret resolution inside the repository-access boundary

The factory will select the internal parameter identifier and the SSH client will obtain its decrypted value immediately before preparing the clone. The raw private key will only be written to a mode `0600` temporary file and removed during cleanup.

Alternative considered: resolve the raw key in the factory and pass it through service layers. This spreads secret material across more objects and requires broader asynchronous interface changes.

### Remove all provider API implementations

The GitHub Octokit client and the already-unwired Bitbucket Axios client will be removed together with API token keys and API-only dependencies. Repository operations will continue through the existing `RepoClient`/`CloneableRepoClient` contract.

Alternative considered: leave API clients as dormant fallback code. This retains maintenance and dependency cost without a supported runtime path.

## Risks / Trade-offs

- [Missing or unauthorized GitHub deploy key] -> Provision and validate `github_ssh_private_key` before deploying the SSH-only application version.
- [Existing HTTPS GitHub requests now require SSH credentials] -> Normalize URLs internally and document the breaking credential migration; do not change the MCP input shape.
- [Large repositories consume Lambda temporary storage and time] -> Preserve shallow clone behavior and existing cleanup; monitor failures before changing Lambda sizing.
- [Mutable state leaks between jobs] -> Return a fresh SSH client/session per request and add concurrent-job tests.
- [Malformed URL targets an unintended host] -> Parse supported URL forms and compare the exact hostname against the allowlist before constructing the clone URL.
- [API removal complicates rollback] -> Retain API token parameters operationally until the SSH deployment passes direct validation, then remove them separately.

## Migration Plan

1. Provision an encrypted `github_ssh_private_key` parameter and authorize its public key on required GitHub repositories.
2. Deploy the generalized SSH path while retaining existing API token parameters for rollback.
3. Validate GitHub and Bitbucket commit/full scans directly after deployment, including concurrent jobs.
4. Remove obsolete API token values after the deployment is stable.
5. Roll back by redeploying the previous application image while retained API tokens are still available.

## Open Questions

None. Key rotation and repository authorization remain operational procedures using the existing parameter store.
