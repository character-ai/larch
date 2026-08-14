use std::{
    collections::{BTreeMap, BTreeSet},
    fmt,
    path::{Component, Path, PathBuf},
    process::Command,
    sync::{Arc, OnceLock},
};

use globset::{Glob, GlobSet, GlobSetBuilder};

use crate::{
    command_registry::CommandRegistryAnalysis,
    runner::LintError,
    syntax::{parse_bash, parse_python},
};

/// A lazily materialized immutable fact set for one repository snapshot.
///
/// Both successful values and deterministic failures are retained so parallel
/// policy rules share one analysis attempt instead of racing to repeat it.
#[derive(Debug)]
pub struct AnalysisCache<T> {
    value: OnceLock<Result<Arc<T>, LintError>>,
}

impl<T> AnalysisCache<T> {
    pub(crate) const fn new() -> Self {
        Self {
            value: OnceLock::new(),
        }
    }

    pub(crate) fn get_or_init(
        &self,
        initialize: impl FnOnce() -> Result<T, LintError>,
    ) -> Result<Arc<T>, LintError> {
        match self.value.get_or_init(|| initialize().map(Arc::new)) {
            Ok(value) => Ok(Arc::clone(value)),
            Err(error) => Err(error.clone()),
        }
    }
}

impl<T> Default for AnalysisCache<T> {
    fn default() -> Self {
        Self::new()
    }
}

/// A validated, UTF-8 repository-relative path.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct RepoPath(String);

impl RepoPath {
    pub(crate) fn from_trusted(raw: &str) -> Self {
        Self(raw.to_owned())
    }

    pub(crate) fn parse(raw: &str) -> Result<Self, LintError> {
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

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegularFileStatus {
    Missing,
    Symlink,
    NotRegular,
    Regular,
}

pub fn regular_file_status(path: &Path) -> Result<RegularFileStatus, std::io::Error> {
    let metadata = match std::fs::symlink_metadata(path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(RegularFileStatus::Missing);
        }
        Err(error) => return Err(error),
    };
    if metadata.file_type().is_symlink() {
        Ok(RegularFileStatus::Symlink)
    } else if metadata.is_file() {
        Ok(RegularFileStatus::Regular)
    } else {
        Ok(RegularFileStatus::NotRegular)
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

    /// Return NUL-delimited paths recorded in Git's index.
    ///
    /// The default preserves lightweight test adapters whose discovery stream
    /// represents only committed fixture files. Production discovery overrides
    /// it so rules can distinguish untracked working-tree files.
    ///
    /// # Errors
    ///
    /// Returns an error when Git cannot provide its committed-file view.
    fn committed_paths(&self, root: &Path) -> Result<Vec<u8>, LintError> {
        self.tracked_paths(root)
    }
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
        let tagged = command_output(
            Command::new("git").arg("-C").arg(root).args([
                "ls-files",
                "-t",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ]),
            "discover tracked files",
        )?;
        materialized_tracked_paths(&tagged)
    }

    fn committed_paths(&self, root: &Path) -> Result<Vec<u8>, LintError> {
        command_output(
            Command::new("git")
                .arg("-C")
                .arg(root)
                .args(["ls-files", "--cached", "-z"]),
            "discover committed files",
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

fn materialized_tracked_paths(tagged: &[u8]) -> Result<Vec<u8>, LintError> {
    if !tagged.is_empty() && !tagged.ends_with(&[0]) {
        return Err(LintError::new(
            "tagged tracked-file response is not NUL-terminated",
        ));
    }
    let mut paths = Vec::new();
    for record in tagged
        .split(|byte| *byte == 0)
        .filter(|record| !record.is_empty())
    {
        if record.len() < 3 || record[1] != b' ' {
            return Err(LintError::new(
                "tagged tracked-file response has a malformed record",
            ));
        }
        if record[0] == b'S' {
            continue;
        }
        paths.extend_from_slice(&record[2..]);
        paths.push(0);
    }
    Ok(paths)
}

#[derive(Debug)]
struct SourceFile {
    bytes: Arc<[u8]>,
    utf8: OnceLock<Result<Arc<str>, String>>,
}

impl SourceFile {
    fn new(bytes: Vec<u8>) -> Self {
        Self {
            bytes: Arc::from(bytes),
            utf8: OnceLock::new(),
        }
    }

    fn utf8(&self, path: &RepoPath) -> Result<Arc<str>, LintError> {
        match self.utf8.get_or_init(|| {
            std::str::from_utf8(&self.bytes)
                .map(Arc::<str>::from)
                .map_err(|error| error.to_string())
        }) {
            Ok(source) => Ok(Arc::clone(source)),
            Err(error) => Err(LintError::new(format!(
                "{path}: cannot read UTF-8 source: {error}"
            ))),
        }
    }
}

/// A repository snapshot whose files are current non-ignored regular files.
pub struct Repository {
    root: PathBuf,
    paths: Vec<RepoPath>,
    committed_paths: Vec<RepoPath>,
    sources: BTreeMap<RepoPath, SourceFile>,
    bash_syntax: BTreeMap<RepoPath, OnceLock<Result<Arc<tree_sitter::Tree>, String>>>,
    python_syntax: BTreeMap<RepoPath, OnceLock<Result<Arc<tree_sitter::Tree>, String>>>,
    command_registry_analysis: OnceLock<Arc<CommandRegistryAnalysis>>,
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
        let committed = parse_tracked_paths(&git.committed_paths(&root)?)?;
        let mut paths = Vec::with_capacity(discovered.len());
        let mut sources = BTreeMap::new();
        let mut bash_syntax = BTreeMap::new();
        let mut python_syntax = BTreeMap::new();
        for path in discovered {
            // `plugin/` is a generated, byte-for-byte runtime projection. Lint
            // its canonical source paths once instead of reporting duplicates.
            if path.as_str().starts_with("plugin/") {
                continue;
            }
            let candidate = root.join(path.as_str());
            match regular_file_status(&candidate) {
                Ok(RegularFileStatus::Missing) => {}
                Ok(RegularFileStatus::Symlink) => {
                    return Err(LintError::new(format!(
                        "{path}: tracked symlinks are not supported"
                    )));
                }
                Ok(RegularFileStatus::NotRegular) => {
                    return Err(LintError::new(format!(
                        "{path}: tracked path is not a regular file"
                    )));
                }
                Ok(RegularFileStatus::Regular) => {
                    let bytes = std::fs::read(&candidate).map_err(|error| {
                        LintError::new(format!("{path}: cannot read source: {error}"))
                    })?;
                    bash_syntax.insert(path.clone(), OnceLock::new());
                    python_syntax.insert(path.clone(), OnceLock::new());
                    sources.insert(path.clone(), SourceFile::new(bytes));
                    paths.push(path);
                }
                Err(error) => {
                    return Err(LintError::new(format!(
                        "{path}: cannot inspect tracked path: {error}"
                    )));
                }
            }
        }
        Ok(Self {
            root,
            paths,
            committed_paths: committed,
            sources,
            bash_syntax,
            python_syntax,
            command_registry_analysis: OnceLock::new(),
        })
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

    /// Return sorted repository-relative paths recorded in Git's index.
    ///
    /// Unlike [`Self::paths`], this includes files omitted by sparse checkout.
    #[must_use]
    pub fn committed_paths(&self) -> &[RepoPath] {
        &self.committed_paths
    }

    /// Return whether a repository-relative path is recorded in Git's index.
    #[must_use]
    pub fn is_committed(&self, path: &RepoPath) -> bool {
        self.committed_paths.binary_search(path).is_ok()
    }

    /// Read one snapshotted regular file as UTF-8.
    ///
    /// # Errors
    ///
    /// Returns an error when `path` is absent from the validated snapshot or
    /// its snapshotted bytes are not UTF-8.
    pub fn read_utf8(&self, path: &RepoPath) -> Result<Arc<str>, LintError> {
        self.sources
            .get(path)
            .ok_or_else(|| LintError::new(format!("{path}: path is not tracked")))?
            .utf8(path)
    }

    /// Read a required tracked regular file as UTF-8.
    ///
    /// # Errors
    ///
    /// Returns `missing_message` when `path` is absent from the snapshot, or
    /// propagates the snapshot and UTF-8 validation errors from
    /// [`Self::read_utf8`].
    pub fn read_required_utf8(
        &self,
        path: &RepoPath,
        missing_message: impl Into<String>,
    ) -> Result<Arc<str>, LintError> {
        if self.paths.binary_search(path).is_err() {
            return Err(LintError::new(missing_message));
        }
        self.read_utf8(path)
    }

    /// Read one snapshotted regular file as bytes.
    ///
    /// # Errors
    ///
    /// Returns an error when `path` is absent from the validated snapshot.
    pub fn read_bytes(&self, path: &RepoPath) -> Result<Arc<[u8]>, LintError> {
        self.sources
            .get(path)
            .map(|source| Arc::clone(&source.bytes))
            .ok_or_else(|| LintError::new(format!("{path}: path is not tracked")))
    }

    /// Return shared parsed Bash syntax for one snapshotted source file.
    ///
    /// # Errors
    ///
    /// Returns an error when `path` is not tracked or its source cannot be parsed.
    pub fn bash_syntax(&self, path: &RepoPath) -> Result<Arc<tree_sitter::Tree>, LintError> {
        self.cached_syntax(path, &self.bash_syntax, parse_bash)
    }

    /// Return shared parsed Python syntax for one snapshotted source file.
    ///
    /// # Errors
    ///
    /// Returns an error when `path` is not tracked or its source cannot be parsed.
    pub fn python_syntax(&self, path: &RepoPath) -> Result<Arc<tree_sitter::Tree>, LintError> {
        self.cached_syntax(path, &self.python_syntax, parse_python)
    }

    /// Return the shared command-registry facts for this immutable snapshot.
    #[must_use]
    pub(crate) fn command_registry_analysis(&self) -> Arc<CommandRegistryAnalysis> {
        Arc::clone(
            self.command_registry_analysis
                .get_or_init(|| Arc::new(CommandRegistryAnalysis::new())),
        )
    }

    fn cached_syntax(
        &self,
        path: &RepoPath,
        cache: &BTreeMap<RepoPath, OnceLock<Result<Arc<tree_sitter::Tree>, String>>>,
        parse: fn(&str) -> Result<tree_sitter::Tree, LintError>,
    ) -> Result<Arc<tree_sitter::Tree>, LintError> {
        let source = self.read_utf8(path)?;
        let syntax = cache
            .get(path)
            .ok_or_else(|| LintError::new(format!("{path}: path is not tracked")))?;
        match syntax.get_or_init(|| {
            parse(&source)
                .map(Arc::new)
                .map_err(|error| format!("{path}: {error}"))
        }) {
            Ok(syntax) => Ok(Arc::clone(syntax)),
            Err(error) => Err(LintError::new(error.clone())),
        }
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
    use std::{
        path::{Path, PathBuf},
        sync::{
            Arc, Barrier,
            atomic::{AtomicUsize, Ordering},
        },
    };

    use super::{
        AnalysisCache, Git, LintError, PathSelector, RepoPath, Repository,
        materialized_tracked_paths, parse_tracked_paths,
    };
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
    fn materialized_paths_drop_sparse_index_entries() {
        assert_eq!(
            materialized_tracked_paths(b"H present.txt\0S sparse.txt\0? new.txt\0")
                .expect("valid tagged paths"),
            b"present.txt\0new.txt\0"
        );
        assert!(materialized_tracked_paths(b"H missing-null").is_err());
        assert!(materialized_tracked_paths(b"malformed\0").is_err());
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
    fn snapshot_reuses_contents_and_parsed_syntax() {
        let temporary = tempfile::tempdir().expect("tempdir");
        std::fs::write(temporary.path().join("module.py"), "print('before')\n")
            .expect("write Python fixture");
        std::fs::write(
            temporary.path().join("script.sh"),
            "printf '%s\\n' before\n",
        )
        .expect("write Bash fixture");
        let repository = Repository::discover(
            &FakeGit {
                root: temporary.path().to_path_buf(),
                stream: b"script.sh\0module.py\0".to_vec(),
            },
            temporary.path(),
        )
        .expect("discover fixture repository");
        let python = RepoPath::parse("module.py").expect("valid Python path");
        let shell = RepoPath::parse("script.sh").expect("valid Bash path");

        let first_bytes = repository.read_bytes(&python).expect("read Python bytes");
        let second_bytes = repository.read_bytes(&python).expect("reuse Python bytes");
        assert!(Arc::ptr_eq(&first_bytes, &second_bytes));

        let first_source = repository.read_utf8(&python).expect("read Python source");
        let second_source = repository.read_utf8(&python).expect("reuse Python source");
        assert!(Arc::ptr_eq(&first_source, &second_source));
        std::fs::write(temporary.path().join("module.py"), "print('after')\n")
            .expect("mutate fixture after discovery");
        assert_eq!(
            repository
                .read_utf8(&python)
                .expect("read snapshot")
                .as_ref(),
            "print('before')\n"
        );

        let first_python = repository.python_syntax(&python).expect("parse Python");
        let second_python = repository
            .python_syntax(&python)
            .expect("reuse Python parse");
        assert!(Arc::ptr_eq(&first_python, &second_python));
        let first_bash = repository.bash_syntax(&shell).expect("parse Bash");
        let second_bash = repository.bash_syntax(&shell).expect("reuse Bash parse");
        assert!(Arc::ptr_eq(&first_bash, &second_bash));
    }

    #[test]
    fn analysis_cache_shares_concurrent_successes_and_failures() {
        let success = Arc::new(AnalysisCache::<usize>::new());
        let success_calls = AtomicUsize::new(0);
        let success_start = Arc::new(Barrier::new(8));
        std::thread::scope(|scope| {
            for _ in 0..8 {
                let cache = Arc::clone(&success);
                let start = Arc::clone(&success_start);
                let calls = &success_calls;
                scope.spawn(move || {
                    start.wait();
                    let value = cache
                        .get_or_init(|| {
                            calls.fetch_add(1, Ordering::SeqCst);
                            Ok(42)
                        })
                        .expect("shared successful analysis");
                    assert_eq!(*value, 42);
                });
            }
        });
        assert_eq!(success_calls.load(Ordering::SeqCst), 1);
        let first = success
            .get_or_init(|| panic!("successful analysis must stay cached"))
            .expect("cached successful analysis");
        let second = success
            .get_or_init(|| panic!("successful analysis must stay cached"))
            .expect("cached successful analysis");
        assert!(Arc::ptr_eq(&first, &second));

        let failure = Arc::new(AnalysisCache::<usize>::new());
        let failure_calls = AtomicUsize::new(0);
        let failure_start = Arc::new(Barrier::new(8));
        std::thread::scope(|scope| {
            for _ in 0..8 {
                let cache = Arc::clone(&failure);
                let start = Arc::clone(&failure_start);
                let calls = &failure_calls;
                scope.spawn(move || {
                    start.wait();
                    let error = cache
                        .get_or_init(|| {
                            calls.fetch_add(1, Ordering::SeqCst);
                            Err(LintError::new("fixture analysis failure"))
                        })
                        .expect_err("shared failed analysis");
                    assert_eq!(error.to_string(), "fixture analysis failure");
                });
            }
        });
        assert_eq!(failure_calls.load(Ordering::SeqCst), 1);
        let error = failure
            .get_or_init(|| panic!("failed analysis must stay cached"))
            .expect_err("cached failed analysis");
        assert_eq!(error.to_string(), "fixture analysis failure");
    }

    #[test]
    fn current_snapshot_separates_missing_index_paths() {
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
        assert_eq!(
            repository.committed_paths(),
            [
                RepoPath("deleted.txt".to_owned()),
                RepoPath("present.txt".to_owned())
            ]
        );
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
