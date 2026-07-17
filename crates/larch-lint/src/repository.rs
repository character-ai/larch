use std::{
    collections::BTreeSet,
    fmt,
    path::{Component, Path, PathBuf},
    process::Command,
};

use globset::{Glob, GlobSet, GlobSetBuilder};

use crate::runner::LintError;

/// A validated, UTF-8 repository-relative path.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct RepoPath(String);

impl RepoPath {
    pub(crate) fn from_trusted(raw: &str) -> Self {
        Self(raw.to_owned())
    }

    fn parse(raw: &str) -> Result<Self, LintError> {
        let path = Path::new(raw);
        if raw.is_empty()
            || path.is_absolute()
            || path.components().any(|component| {
                matches!(
                    component,
                    Component::CurDir
                        | Component::ParentDir
                        | Component::RootDir
                        | Component::Prefix(_)
                )
            })
        {
            return Err(LintError::new(format!("unsafe tracked path: {raw:?}")));
        }
        Ok(Self(raw.to_owned()))
    }

    /// Return the stable slash-separated repository-relative representation.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for RepoPath {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt(formatter)
    }
}

/// A narrow adapter for the Git operations the runner owns.
pub trait Git {
    /// Resolve the repository root for `cwd`.
    ///
    /// # Errors
    ///
    /// Returns an error when the root cannot be determined or trusted.
    fn repository_root(&self, cwd: &Path) -> Result<PathBuf, LintError>;

    /// Return NUL-delimited, non-ignored paths currently known to Git in `root`.
    ///
    /// # Errors
    ///
    /// Returns an error when Git cannot provide its working-tree file view.
    fn tracked_paths(&self, root: &Path) -> Result<Vec<u8>, LintError>;
}

/// Production adapter that treats Git's non-ignored working tree as discovery authority.
#[derive(Clone, Copy, Debug, Default)]
pub struct GitCli;

impl Git for GitCli {
    fn repository_root(&self, cwd: &Path) -> Result<PathBuf, LintError> {
        let output = command_output(
            Command::new("git")
                .arg("-C")
                .arg(cwd)
                .args(["rev-parse", "--show-toplevel"]),
            "resolve repository root",
        )?;
        let root = std::str::from_utf8(&output)
            .map_err(|error| LintError::new(format!("repository root is not UTF-8: {error}")))?;
        let root = root.strip_suffix('\n').ok_or_else(|| {
            LintError::new("repository root response is missing a trailing newline")
        })?;
        let root = root.strip_suffix('\r').unwrap_or(root);
        if root.is_empty() || root.contains('\n') || root.contains('\r') {
            return Err(LintError::new("repository root response is malformed"));
        }
        Ok(PathBuf::from(root))
    }

    fn tracked_paths(&self, root: &Path) -> Result<Vec<u8>, LintError> {
        command_output(
            Command::new("git").arg("-C").arg(root).args([
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ]),
            "discover tracked files",
        )
    }
}

fn command_output(command: &mut Command, operation: &str) -> Result<Vec<u8>, LintError> {
    let output = command
        .output()
        .map_err(|error| LintError::new(format!("cannot {operation}: {error}")))?;
    if !output.status.success() {
        return Err(LintError::new(format!(
            "cannot {operation}: git exited with {}",
            output.status
        )));
    }
    if !output.stderr.is_empty() {
        return Err(LintError::new(format!(
            "cannot {operation}: git wrote diagnostics"
        )));
    }
    Ok(output.stdout)
}

/// A repository snapshot whose files are current non-ignored regular files.
#[derive(Debug)]
pub struct Repository {
    root: PathBuf,
    paths: Vec<RepoPath>,
}

impl Repository {
    /// Discover and validate the repository that contains `cwd`.
    ///
    /// # Errors
    ///
    /// Returns an error when Git discovery, tracked-file validation, or the
    /// symlink policy prevents a trustworthy repository snapshot.
    pub fn discover(git: &dyn Git, cwd: &Path) -> Result<Self, LintError> {
        let root = git.repository_root(cwd)?.canonicalize().map_err(|error| {
            LintError::new(format!("cannot canonicalize repository root: {error}"))
        })?;
        let stream = git.tracked_paths(&root)?;
        let discovered = parse_tracked_paths(&stream)?;
        let mut paths = Vec::with_capacity(discovered.len());
        for path in discovered {
            let candidate = root.join(path.as_str());
            let metadata = match std::fs::symlink_metadata(&candidate) {
                Ok(metadata) => metadata,
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => continue,
                Err(error) => {
                    return Err(LintError::new(format!(
                        "{path}: cannot inspect tracked path: {error}"
                    )));
                }
            };
            if metadata.file_type().is_symlink() {
                return Err(LintError::new(format!(
                    "{path}: tracked symlinks are not supported"
                )));
            }
            if !metadata.is_file() {
                return Err(LintError::new(format!(
                    "{path}: tracked path is not a regular file"
                )));
            }
            paths.push(path);
        }
        Ok(Self { root, paths })
    }

    /// Return the canonical repository root.
    #[must_use]
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// Return sorted repository-relative paths.
    #[must_use]
    pub fn paths(&self) -> &[RepoPath] {
        &self.paths
    }

    /// Read one tracked regular file as UTF-8.
    ///
    /// # Errors
    ///
    /// Returns an error when `path` is not tracked, is no longer a regular
    /// file, cannot be read, or is not UTF-8.
    pub fn read_utf8(&self, path: &RepoPath) -> Result<String, LintError> {
        if self.paths.binary_search(path).is_err() {
            return Err(LintError::new(format!("{path}: path is not tracked")));
        }
        let candidate = self.root.join(path.as_str());
        let metadata = std::fs::symlink_metadata(&candidate).map_err(|error| {
            LintError::new(format!("{path}: cannot inspect tracked path: {error}"))
        })?;
        if metadata.file_type().is_symlink() || !metadata.is_file() {
            return Err(LintError::new(format!(
                "{path}: tracked path is no longer a regular file"
            )));
        }
        std::fs::read_to_string(candidate)
            .map_err(|error| LintError::new(format!("{path}: cannot read UTF-8 source: {error}")))
    }
}

fn parse_tracked_paths(stream: &[u8]) -> Result<Vec<RepoPath>, LintError> {
    if !stream.is_empty() && !stream.ends_with(&[0]) {
        return Err(LintError::new(
            "tracked-file response is not NUL-terminated",
        ));
    }
    let mut paths = BTreeSet::new();
    for raw in stream
        .split(|byte| *byte == 0)
        .filter(|record| !record.is_empty())
    {
        let raw = std::str::from_utf8(raw)
            .map_err(|error| LintError::new(format!("tracked path is not UTF-8: {error}")))?;
        let path = RepoPath::parse(raw)?;
        if !paths.insert(path) {
            return Err(LintError::new(format!("duplicate tracked path: {raw}")));
        }
    }
    Ok(paths.into_iter().collect())
}

/// Rule-owned include and exclusion patterns for tracked paths.
#[derive(Debug)]
pub struct PathSelector {
    includes: GlobSet,
    excludes: GlobSet,
}

impl PathSelector {
    /// Compile repository-relative glob patterns.
    ///
    /// # Errors
    ///
    /// Returns an error when a pattern is invalid or cannot be compiled.
    pub fn new(includes: &[&str], excludes: &[&str]) -> Result<Self, LintError> {
        Ok(Self {
            includes: compile_globs(includes)?,
            excludes: compile_globs(excludes)?,
        })
    }

    /// Select matching paths in the repository's deterministic order.
    #[must_use]
    pub fn select<'repository>(
        &self,
        repository: &'repository Repository,
    ) -> Vec<&'repository RepoPath> {
        repository
            .paths()
            .iter()
            .filter(|path| {
                (self.includes.is_empty() || self.includes.is_match(path.as_str()))
                    && !self.excludes.is_match(path.as_str())
            })
            .collect()
    }
}

fn compile_globs(patterns: &[&str]) -> Result<GlobSet, LintError> {
    let mut builder = GlobSetBuilder::new();
    for pattern in patterns {
        let glob = Glob::new(pattern)
            .map_err(|error| LintError::new(format!("invalid path glob {pattern:?}: {error}")))?;
        builder.add(glob);
    }
    builder
        .build()
        .map_err(|error| LintError::new(format!("cannot build path selector: {error}")))
}

#[cfg(test)]
mod tests {
    use std::path::{Path, PathBuf};

    use super::{Git, LintError, PathSelector, RepoPath, Repository, parse_tracked_paths};
    use crate::{Finding, Rule, RuleOutput, run};

    #[derive(Debug)]
    struct FakeGit {
        root: PathBuf,
        stream: Vec<u8>,
    }

    impl Git for FakeGit {
        fn repository_root(&self, _cwd: &Path) -> Result<PathBuf, LintError> {
            Ok(self.root.clone())
        }

        fn tracked_paths(&self, _root: &Path) -> Result<Vec<u8>, LintError> {
            Ok(self.stream.clone())
        }
    }

    #[derive(Debug)]
    struct FixtureRule;

    impl Rule for FixtureRule {
        fn name(&self) -> &'static str {
            "fixture"
        }

        fn description(&self) -> &'static str {
            "fixture rule"
        }

        fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
            assert_eq!(repository.paths().len(), 2);
            Ok(RuleOutput::from_findings(vec![
                Finding::new("z.md", 1, "later"),
                Finding::new("a.md", 2, "first"),
            ]))
        }
    }

    #[test]
    fn tracked_paths_sort_deterministically() {
        let paths = parse_tracked_paths(b"z.md\0a.md\0").expect("valid paths");
        assert_eq!(
            paths,
            [RepoPath("a.md".to_owned()), RepoPath("z.md".to_owned())]
        );
    }

    #[test]
    fn tracked_paths_reject_malformed_and_unsafe_records() {
        assert!(parse_tracked_paths(b"missing-null").is_err());
        assert!(parse_tracked_paths(b"./not-normalized\0").is_err());
        assert!(parse_tracked_paths(b"../escape\0").is_err());
        assert!(parse_tracked_paths(b"not-utf8-\xff\0").is_err());
    }

    #[test]
    fn source_read_rejects_non_utf8_contents() {
        let temporary = tempfile::tempdir().expect("tempdir");
        std::fs::write(temporary.path().join("invalid.txt"), [0xff]).expect("write fixture");
        let repository = Repository::discover(
            &FakeGit {
                root: temporary.path().to_path_buf(),
                stream: b"invalid.txt\0".to_vec(),
            },
            temporary.path(),
        )
        .expect("discover fixture repository");
        let path = RepoPath::parse("invalid.txt").expect("valid path");
        assert!(repository.read_utf8(&path).is_err());
    }

    #[test]
    fn current_snapshot_ignores_deleted_index_paths() {
        let temporary = tempfile::tempdir().expect("tempdir");
        std::fs::write(temporary.path().join("present.txt"), "present").expect("write fixture");
        let repository = Repository::discover(
            &FakeGit {
                root: temporary.path().to_path_buf(),
                stream: b"deleted.txt\0present.txt\0".to_vec(),
            },
            temporary.path(),
        )
        .expect("discover fixture repository");
        assert_eq!(repository.paths(), [RepoPath("present.txt".to_owned())]);
    }

    #[test]
    fn selector_applies_includes_and_exclusions() {
        let temporary = tempfile::tempdir().expect("tempdir");
        std::fs::write(temporary.path().join("keep.md"), "keep").expect("write fixture");
        std::fs::write(temporary.path().join("skip.md"), "skip").expect("write fixture");
        let repository = Repository::discover(
            &FakeGit {
                root: temporary.path().to_path_buf(),
                stream: b"skip.md\0keep.md\0".to_vec(),
            },
            temporary.path(),
        )
        .expect("discover fixture repository");
        let selector = PathSelector::new(&["*.md"], &["skip.md"]).expect("selector");
        assert_eq!(
            selector.select(&repository),
            [&RepoPath("keep.md".to_owned())]
        );
    }

    #[test]
    fn runner_sorts_fixture_rule_findings() {
        let temporary = tempfile::tempdir().expect("tempdir");
        std::fs::write(temporary.path().join("a.md"), "a").expect("write fixture");
        std::fs::write(temporary.path().join("z.md"), "z").expect("write fixture");
        let repository = Repository::discover(
            &FakeGit {
                root: temporary.path().to_path_buf(),
                stream: b"z.md\0a.md\0".to_vec(),
            },
            temporary.path(),
        )
        .expect("discover fixture repository");
        let rule = FixtureRule;
        let rules: [&dyn Rule; 1] = [&rule];
        let findings = run(&repository, rules).expect("run fixture rule");
        assert_eq!(findings.findings()[0].to_string(), "a.md:2: first");
    }
}
