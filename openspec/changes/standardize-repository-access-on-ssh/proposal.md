## Why

`git-commit-files` maintains separate repository access paths even though its Git/SSH workflow already supports the clone, checkout, listing, and download operations needed by both GitHub and Bitbucket. Standardizing on SSH removes unnecessary provider API complexity, rate-limit exposure, and duplicate credential handling.

## What Changes

- Route supported GitHub and Bitbucket repositories through one Git/SSH client.
- Select a provider-specific private-key parameter from the validated repository host.
- Add a `github_ssh_private_key` parameter alongside the existing Bitbucket SSH key.
- Generalize SSH clone URL parsing and construction so it no longer assumes Bitbucket.
- Isolate mutable clone and key state between concurrently processed jobs.
- Remove the GitHub and Bitbucket API clients, their API token parameters, tests, mocks, and API-only dependencies.
- **BREAKING**: GitHub repository access will require a configured SSH deploy key instead of `github_access_token`.

## Capabilities

### New Capabilities

- `repository-ssh-access`: Retrieve repository content from GitHub and Bitbucket exclusively through provider-specific SSH credentials and Git commands.

### Modified Capabilities

None.

## Impact

- Affects repository client selection, SSH clone setup, parameter names, dependency injection, and concurrent SQS record processing in `src/mcp/git-commit-files`.
- Requires provisioning and rotating `github_ssh_private_key` in the existing encrypted parameter store.
- Removes `@octokit/rest` and `axios` when no remaining code references them.
- Does not change the MCP input contract or AWS IAM permissions when the new key uses the existing parameter table and encryption secret.

## Non-goals

- Changing commit versus full-scan file-selection semantics.
- Supporting repository providers other than GitHub and Bitbucket.
- Accepting private keys or parameter names from MCP callers.
- Replacing the current parameter encryption mechanism or SSH host-key policy.
