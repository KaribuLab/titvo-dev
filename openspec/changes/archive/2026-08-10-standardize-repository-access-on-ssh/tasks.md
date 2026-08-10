## 1. SSH Provider Configuration

- [x] 1.1 Add the `github_ssh_private_key` parameter key and a typed host configuration mapping for GitHub and Bitbucket.
- [x] 1.2 Implement exact-host parsing and canonical SSH URL construction for supported HTTPS and SCP-style repository URLs.
- [x] 1.3 Add unit tests for GitHub and Bitbucket URL normalization, provider key selection, malformed URLs, and unsupported hosts.

## 2. Generic SSH Repository Client

- [x] 2.1 Refactor `SshGitRepoClient` to receive validated repository coordinates and the selected private-key parameter without Bitbucket-specific constants or messages.
- [x] 2.2 Preserve shallow branch and commit checkout, ref resolution, file listing, download, and cleanup behavior for both providers.
- [x] 2.3 Make `RepoFactoryService` return isolated SSH client state for every job while sharing only stateless dependencies.
- [x] 2.4 Add tests proving concurrent GitHub and Bitbucket jobs cannot share clone URLs, keys, temporary directories, resolved SHAs, or cleanup state.

## 3. SSH-Only Routing

- [x] 3.1 Route both GitHub and Bitbucket repository URLs exclusively through the generic SSH client without changing the MCP input contract.
- [x] 3.2 Update commit and full-scan service tests to cover both providers, missing keys, preparation failures, result events, S3 prefixes, and cleanup.

## 4. API Removal

- [x] 4.1 Remove the GitHub Octokit client, the unused Bitbucket Axios client, their unit tests, and dependency-injection registrations.
- [x] 4.2 Remove API token parameter keys and obsolete Octokit mocks from remaining tests.
- [x] 4.3 Remove `@octokit/rest` and `axios` from `package.json`, regenerate `package-lock.json`, and verify neither dependency remains referenced.

## 5. Migration And Verification

- [x] 5.1 Add or update local provisioning support for provider SSH key parameters without committing private key material.
- [x] 5.2 Run unit tests, lint, and production build for `src/mcp/git-commit-files`.
- [x] 5.3 Document the deployment order: provision GitHub deploy key, deploy SSH-only version, validate directly, then retire API token parameters.

## 6. Documentation

- [x] 6.1 Update `docs/architecture.md` to describe SSH-only GitHub and Bitbucket repository access and per-job client isolation.
- [x] 6.2 Update `docs/dev-env-structure.md` with the local SSH key parameter setup required by `git-commit-files`.
