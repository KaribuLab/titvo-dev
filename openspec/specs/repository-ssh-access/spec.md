# repository-ssh-access Specification

## Purpose

Retrieve repository content from GitHub and Bitbucket exclusively through provider-specific SSH credentials and Git commands, standardizing on the Git/SSH workflow and removing provider API complexity and duplicate credential handling.

## Requirements

### Requirement: Supported repositories use SSH access
The system SHALL retrieve repository data from supported GitHub and Bitbucket repositories exclusively through Git commands authenticated with SSH.

#### Scenario: Access a GitHub repository
- **WHEN** a job references a repository hosted at `github.com`
- **THEN** the system uses the Git/SSH repository client and does not call the GitHub API

#### Scenario: Access a Bitbucket repository
- **WHEN** a job references a repository hosted at `bitbucket.org`
- **THEN** the system uses the Git/SSH repository client and does not call the Bitbucket API

### Requirement: Repository URLs are normalized safely
The system SHALL accept supported HTTPS and SCP-style SSH repository URLs, validate the exact host, and construct a canonical SSH clone URL from validated repository coordinates.

#### Scenario: Normalize an HTTPS GitHub URL
- **WHEN** a job provides `https://github.com/example/repository.git`
- **THEN** the system clones `git@github.com:example/repository.git`

#### Scenario: Preserve a valid Bitbucket SSH destination
- **WHEN** a job provides `git@bitbucket.org:workspace/repository.git`
- **THEN** the system clones the validated Bitbucket repository over SSH

#### Scenario: Reject an unsupported host
- **WHEN** a repository URL does not resolve to exactly `github.com` or `bitbucket.org`
- **THEN** the system rejects the repository before executing Git

### Requirement: Provider-specific SSH credentials are selected internally
The system SHALL select the private-key parameter from the validated repository host and MUST NOT accept a private key or parameter identifier from the MCP caller.

#### Scenario: Select the GitHub key
- **WHEN** the validated repository host is `github.com`
- **THEN** the system retrieves `github_ssh_private_key` from the existing encrypted parameter store

#### Scenario: Select the Bitbucket key
- **WHEN** the validated repository host is `bitbucket.org`
- **THEN** the system retrieves `bitbucket_ssh_private_key` from the existing encrypted parameter store

#### Scenario: Required key is unavailable
- **WHEN** the selected private-key parameter is missing or empty
- **THEN** the job fails without attempting to clone the repository

### Requirement: SSH job state is isolated
The system MUST isolate repository URL, temporary clone directory, temporary private-key file, and resolved commit state for each concurrently processed job.

#### Scenario: Process different providers concurrently
- **WHEN** GitHub and Bitbucket jobs are processed concurrently in one Lambda invocation
- **THEN** each job uses only its own repository, private key, clone directory, and resolved commit

#### Scenario: Clean up temporary credentials and repositories
- **WHEN** a job succeeds or fails after allocating temporary resources
- **THEN** the system removes that job's clone directory and private-key file without affecting another job

### Requirement: Existing scan contracts are preserved
The SSH-only repository path SHALL preserve the current commit/full scan selection behavior, S3 storage-prefix conventions, and result-event structure.

#### Scenario: Run a commit scan
- **WHEN** a commit scan is processed through the SSH-only path
- **THEN** the system selects files using the existing Git commit-scan behavior and stores them under the existing commit prefix

#### Scenario: Run a full scan
- **WHEN** a full scan is processed through the SSH-only path
- **THEN** the system resolves the requested branch or ref, selects the full tracked snapshot, and stores it under the existing full-scan prefix
