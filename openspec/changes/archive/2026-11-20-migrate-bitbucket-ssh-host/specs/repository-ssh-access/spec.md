# Spec Delta

## MODIFIED Requirements

### Requirement: Repository URLs are normalized safely
The system SHALL accept supported HTTPS and SCP-style SSH repository URLs, validate the exact host, and construct a canonical SSH clone URL from validated repository coordinates. Bitbucket inputs using `bitbucket.org` or SCP-style SSH using `ssh.bitbucket.org` SHALL use `ssh.bitbucket.org` as the Git transport host.

#### Scenario: Normalize an HTTPS GitHub URL
- **WHEN** a job provides `https://github.com/example/repository.git`
- **THEN** the system clones `git@github.com:example/repository.git`

#### Scenario: Preserve a valid Bitbucket SSH destination
- **WHEN** a job provides `git@bitbucket.org:workspace/repository.git`
- **THEN** the system clones `git@ssh.bitbucket.org:workspace/repository.git`

#### Scenario: Normalize an HTTPS Bitbucket URL
- **WHEN** a job provides `https://bitbucket.org/workspace/repository.git`
- **THEN** the system clones `git@ssh.bitbucket.org:workspace/repository.git` without requiring the caller to change its HTTPS URL

#### Scenario: Accept the new Bitbucket SSH hostname
- **WHEN** a job provides `git@ssh.bitbucket.org:workspace/repository.git`
- **THEN** the system clones that validated canonical SSH destination

#### Scenario: Reject an unsupported host
- **WHEN** a repository URL does not resolve to exactly `github.com`, `bitbucket.org` or `ssh.bitbucket.org`, including deceptive suffixes such as `ssh.bitbucket.org.example.com`
- **THEN** the system rejects the repository before executing Git

### Requirement: Provider-specific SSH credentials are selected internally
The system SHALL select the private-key parameter from the validated repository host and MUST NOT accept a private key or parameter identifier from the MCP caller. Both accepted Bitbucket hostnames SHALL select the same Bitbucket credential.

#### Scenario: Select the GitHub key
- **WHEN** the validated repository host is `github.com`
- **THEN** the system retrieves `github_ssh_private_key` from the existing encrypted parameter store

#### Scenario: Select the Bitbucket key
- **WHEN** the validated repository host is `bitbucket.org` or `ssh.bitbucket.org`
- **THEN** the system retrieves `bitbucket_ssh_private_key` from the existing encrypted parameter store

#### Scenario: Required key is unavailable
- **WHEN** the selected private-key parameter is missing or empty
- **THEN** the job fails without attempting to clone the repository
