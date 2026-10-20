## MODIFIED Requirements

### Requirement: Existing scan contracts are preserved
The SSH-only repository path SHALL preserve the current commit/full scan selection behavior, S3 storage-prefix conventions, and result-event structure.

In `commit` mode the system SHALL select only the files added, copied, modified or renamed by the
requested commit relative to its first parent (`git diff-tree -r --diff-filter=ACMR <sha>^ <sha>`),
and MUST NOT select deleted files or files untouched by the commit. The clone
in `commit` mode SHALL fetch enough history for the first parent to be present. When the commit has
no parent, the system SHALL select the full tracked tree of that commit and log that decision.

#### Scenario: Run a commit scan
- **WHEN** a commit scan is processed through the SSH-only path for a commit that modifies
  `src/a.ts`, adds `src/b.ts` and deletes `src/c.ts` in a repository with 1 000 tracked files
- **THEN** the system selects exactly `src/a.ts` and `src/b.ts` and stores them under the existing
  commit prefix

#### Scenario: Commit scan of a merge commit
- **WHEN** a commit scan is processed for a merge commit
- **THEN** the system selects the files that differ from the merge's first parent

#### Scenario: Commit scan of a root commit
- **WHEN** a commit scan is processed for a commit with no parent
- **THEN** the system selects every tracked file of that commit and logs that the full tree was
  selected because the commit has no parent

#### Scenario: Commit scan does not list the whole tree
- **WHEN** a commit scan is processed through the SSH-only path for a non-root commit
- **THEN** the system does not invoke the full tracked-file listing used by full scans

#### Scenario: Run a full scan
- **WHEN** a full scan is processed through the SSH-only path
- **THEN** the system resolves the requested branch or ref, selects the full tracked snapshot, and stores it under the existing full-scan prefix
