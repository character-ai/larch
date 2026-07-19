use std::{
    ffi::{OsStr, OsString},
    fmt::{self, Write as _},
    fs, io,
    path::{Path, PathBuf},
    process::{Command, ExitStatus, Stdio},
};

#[cfg(unix)]
use std::os::unix::{ffi::OsStringExt, fs::PermissionsExt, process::ExitStatusExt};

use crate::{TestEnvironment, TestWorkspace, filesystem::validate_relative};

const SNAPSHOT_BYTE_LIMIT: usize = 1024 * 1024;
const SNAPSHOT_ENTRY_LIMIT: usize = 4096;
const SNAPSHOT_SCHEMA: u32 = 1;

/// Git object format selected when a repository is initialized.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum GitObjectFormat {
    /// The traditional SHA-1 object format.
    #[default]
    Sha1,
    /// Git's SHA-256 object format.
    Sha256,
}

impl GitObjectFormat {
    const fn argument(self) -> &'static str {
        match self {
            Self::Sha1 => "sha1",
            Self::Sha256 => "sha256",
        }
    }
}

/// A named repository state shared by differential tests.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitFixture {
    Unborn,
    Detached,
    Refs,
    Changes,
    Conflict,
    NonUtf8Path,
    SpecialFiles,
    AttributesAndFilters,
    SparseCheckout,
    Submodule,
    LinkedWorktree,
    HooksSigningAndRemotes,
    Corrupt,
}

/// A platform or installed-Git capability used by named fixtures.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FixtureCapability {
    Sha256,
    NonUtf8Paths,
    Symlinks,
    ExecutableBits,
    SparseCheckout,
    Submodules,
    LinkedWorktrees,
}

/// An explicit reason why a fixture is unsupported on this host.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FixtureSkip {
    capability: FixtureCapability,
    reason: String,
}

impl FixtureSkip {
    #[must_use]
    pub const fn capability(&self) -> FixtureCapability {
        self.capability
    }

    #[must_use]
    pub fn reason(&self) -> &str {
        &self.reason
    }
}

impl fmt::Display for FixtureSkip {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{:?}: {}", self.capability, self.reason)
    }
}

impl std::error::Error for FixtureSkip {}

/// Builder for an isolated Git repository.
#[derive(Clone, Debug)]
pub struct GitRepositoryBuilder {
    object_format: GitObjectFormat,
    fixture: GitFixture,
}

impl GitRepositoryBuilder {
    #[must_use]
    pub const fn new(fixture: GitFixture) -> Self {
        Self {
            object_format: GitObjectFormat::Sha1,
            fixture,
        }
    }

    #[must_use]
    pub const fn object_format(mut self, object_format: GitObjectFormat) -> Self {
        self.object_format = object_format;
        self
    }

    /// Build the selected fixture without changing process-global state.
    ///
    /// # Errors
    /// Returns I/O, Git, or explicit capability-skip errors.
    pub fn build(self) -> Result<GitRepository, GitFixtureError> {
        let repository = GitRepository::initialize(self.object_format)?;
        repository.setup(self.fixture)?;
        Ok(repository)
    }
}

/// Error returned while constructing or inspecting a Git fixture.
#[derive(Debug)]
pub enum GitFixtureError {
    Io(io::Error),
    Git(GitCommandOutput),
    Skip(FixtureSkip),
}

impl fmt::Display for GitFixtureError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(error) => write!(formatter, "Git fixture I/O failed: {error}"),
            Self::Git(output) => write!(
                formatter,
                "Git fixture command failed with {:?}: {}",
                output.code,
                String::from_utf8_lossy(&output.stderr)
            ),
            Self::Skip(skip) => write!(formatter, "Git fixture skipped: {skip}"),
        }
    }
}

impl std::error::Error for GitFixtureError {}

impl From<io::Error> for GitFixtureError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

impl From<FixtureSkip> for GitFixtureError {
    fn from(skip: FixtureSkip) -> Self {
        Self::Skip(skip)
    }
}

/// Captured bytes and exit classification from an installed-Git invocation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitCommandOutput {
    pub code: Option<i32>,
    pub interrupted: bool,
    pub stdout: Vec<u8>,
    pub stderr: Vec<u8>,
}

impl GitCommandOutput {
    #[must_use]
    pub fn success(&self) -> bool {
        self.code == Some(0) && !self.interrupted
    }
}

/// An isolated repository and all state owned by its fixture.
#[derive(Debug)]
pub struct GitRepository {
    workspace: TestWorkspace,
    root: PathBuf,
    transcript_root: PathBuf,
    git: PathBuf,
    environment: TestEnvironment,
}

impl GitRepository {
    #[must_use]
    pub const fn builder(fixture: GitFixture) -> GitRepositoryBuilder {
        GitRepositoryBuilder::new(fixture)
    }

    #[must_use]
    pub fn root(&self) -> &Path {
        &self.root
    }

    #[must_use]
    pub fn workspace_root(&self) -> &Path {
        self.workspace.root()
    }

    #[must_use]
    pub fn transcript_root(&self) -> &Path {
        &self.transcript_root
    }

    /// Run installed Git with a cleared, fixture-owned environment.
    ///
    /// # Errors
    /// Returns process-start errors. A nonzero Git exit is captured in the result.
    pub fn git<I, S>(&self, arguments: I) -> io::Result<GitCommandOutput>
    where
        I: IntoIterator<Item = S>,
        S: AsRef<OsStr>,
    {
        self.run_at(&self.root, arguments)
    }

    /// Write bytes under the repository root without following symlink ancestors.
    ///
    /// # Errors
    /// Rejects unsafe relative paths and returns filesystem errors.
    pub fn write(&self, relative: impl AsRef<Path>, contents: &[u8]) -> io::Result<PathBuf> {
        validate_relative(relative.as_ref())?;
        let workspace_relative = Path::new("repo").join(relative.as_ref());
        self.workspace.write(workspace_relative, contents)
    }

    fn initialize(object_format: GitObjectFormat) -> Result<Self, GitFixtureError> {
        let workspace = TestWorkspace::new()?;
        let root = workspace.create_dir("repo")?;
        let transcript_root = workspace.create_dir("transcripts")?;
        let git = find_git()?;
        let git_parent = git.parent().ok_or_else(|| {
            io::Error::new(
                io::ErrorKind::NotFound,
                "installed Git has no parent directory",
            )
        })?;
        let helper_bin = workspace.create_dir("bin")?;
        let child_path = std::env::join_paths([git_parent, helper_bin.as_path()])
            .map_err(|error| io::Error::new(io::ErrorKind::InvalidInput, error))?;
        let environment = TestEnvironment::isolated(&workspace)?
            .set("PATH", child_path)
            .set("LARCH_GIT_FIXTURE_TRANSCRIPTS", &transcript_root)
            .set("LC_ALL", "C")
            .set("TZ", "UTC")
            .set("GIT_CONFIG_NOSYSTEM", "1")
            .set("GIT_CONFIG_GLOBAL", null_device())
            .set("GIT_TERMINAL_PROMPT", "0")
            .set("GIT_AUTHOR_NAME", "Larch Fixture")
            .set("GIT_AUTHOR_EMAIL", "fixture@example.invalid")
            .set("GIT_COMMITTER_NAME", "Larch Fixture")
            .set("GIT_COMMITTER_EMAIL", "fixture@example.invalid")
            .set("GIT_AUTHOR_DATE", "2001-02-03T04:05:06Z")
            .set("GIT_COMMITTER_DATE", "2001-02-03T04:05:06Z");
        let repository = Self {
            workspace,
            root,
            transcript_root,
            git,
            environment,
        };
        let output = repository.git([
            OsStr::new("init"),
            OsStr::new("--quiet"),
            OsStr::new("--initial-branch=main"),
            OsStr::new("--object-format"),
            OsStr::new(object_format.argument()),
        ])?;
        if output.success() {
            Ok(repository)
        } else if object_format == GitObjectFormat::Sha256 {
            Err(FixtureSkip {
                capability: FixtureCapability::Sha256,
                reason: diagnostic(&output),
            }
            .into())
        } else {
            Err(GitFixtureError::Git(output))
        }
    }

    fn setup(&self, fixture: GitFixture) -> Result<(), GitFixtureError> {
        match fixture {
            GitFixture::Unborn => Ok(()),
            GitFixture::Detached => self.setup_detached(),
            GitFixture::Refs => self.setup_refs(),
            GitFixture::Changes => self.setup_changes(),
            GitFixture::Conflict => self.setup_conflict(),
            GitFixture::NonUtf8Path => self.setup_non_utf8_path(),
            GitFixture::SpecialFiles => self.setup_special_files(),
            GitFixture::AttributesAndFilters => self.setup_attributes(),
            GitFixture::SparseCheckout => self.setup_sparse_checkout(),
            GitFixture::Submodule => self.setup_submodule(),
            GitFixture::LinkedWorktree => self.setup_linked_worktree(),
            GitFixture::HooksSigningAndRemotes => self.setup_hooks_signing_remotes(),
            GitFixture::Corrupt => self.setup_corrupt(),
        }
    }

    fn run_at<I, S>(&self, directory: &Path, arguments: I) -> io::Result<GitCommandOutput>
    where
        I: IntoIterator<Item = S>,
        S: AsRef<OsStr>,
    {
        let output = Command::new(&self.git) // lint-subprocess-via-runner: ok test-only installed-Git oracle from issue 7730
            .args(arguments)
            .current_dir(directory)
            .env_clear()
            .envs(self.environment.iter())
            .output()?;
        Ok(command_output(output.status, output.stdout, output.stderr))
    }

    fn run_with_input<I, S>(&self, arguments: I, input: &[u8]) -> io::Result<GitCommandOutput>
    where
        I: IntoIterator<Item = S>,
        S: AsRef<OsStr>,
    {
        let mut child = Command::new(&self.git) // lint-subprocess-via-runner: ok test-only installed-Git oracle from issue 7730
            .args(arguments)
            .current_dir(&self.root)
            .env_clear()
            .envs(self.environment.iter())
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()?;
        let mut stdin = child
            .stdin
            .take()
            .ok_or_else(|| io::Error::other("Git fixture stdin was not piped"))?;
        std::io::Write::write_all(&mut stdin, input)?;
        drop(stdin);
        let output = child.wait_with_output()?;
        Ok(command_output(output.status, output.stdout, output.stderr))
    }

    fn checked<I, S>(&self, arguments: I) -> Result<GitCommandOutput, GitFixtureError>
    where
        I: IntoIterator<Item = S>,
        S: AsRef<OsStr>,
    {
        let output = self.git(arguments)?;
        if output.success() {
            Ok(output)
        } else {
            Err(GitFixtureError::Git(output))
        }
    }

    fn seed_commit(&self) -> Result<(), GitFixtureError> {
        self.write("tracked.txt", b"base\n")?;
        self.checked(["add", "--", "tracked.txt"])?;
        self.checked(["commit", "--quiet", "-m", "base"])?;
        Ok(())
    }

    fn setup_detached(&self) -> Result<(), GitFixtureError> {
        self.seed_commit()?;
        self.checked(["checkout", "--quiet", "--detach", "HEAD"])?;
        Ok(())
    }

    fn setup_refs(&self) -> Result<(), GitFixtureError> {
        self.seed_commit()?;
        self.checked(["branch", "topic"])?;
        self.checked(["update-ref", "refs/remotes/origin/main", "HEAD"])?;
        self.checked(["tag", "v1"])?;
        Ok(())
    }

    fn setup_changes(&self) -> Result<(), GitFixtureError> {
        self.write(".gitignore", b"ignored.txt\n")?;
        self.seed_commit()?;
        self.write("tracked.txt", b"unstaged\n")?;
        self.write("staged.txt", b"staged\n")?;
        self.checked(["add", "--", "staged.txt"])?;
        self.write("untracked.txt", b"untracked\n")?;
        self.write("ignored.txt", b"ignored\n")?;
        Ok(())
    }

    fn setup_conflict(&self) -> Result<(), GitFixtureError> {
        self.seed_commit()?;
        self.checked(["branch", "other"])?;
        self.write("tracked.txt", b"main\n")?;
        self.checked(["commit", "--quiet", "-am", "main change"])?;
        self.checked(["checkout", "--quiet", "other"])?;
        self.write("tracked.txt", b"other\n")?;
        self.checked(["commit", "--quiet", "-am", "other change"])?;
        self.checked(["checkout", "--quiet", "main"])?;
        let merge = self.git(["merge", "--no-edit", "other"])?;
        if merge.success() {
            return Err(io::Error::other("conflict fixture merged cleanly").into());
        }
        Ok(())
    }

    #[cfg(unix)]
    fn setup_non_utf8_path(&self) -> Result<(), GitFixtureError> {
        let raw_name = OsString::from_vec(b"non-utf8-\xff".to_vec());
        if let Err(error) = self.write(Path::new(&raw_name), b"raw name\n") {
            return Err(FixtureSkip {
                capability: FixtureCapability::NonUtf8Paths,
                reason: error.to_string(),
            }
            .into());
        }
        self.checked(["add", "--all"])?;
        self.checked(["commit", "--quiet", "-m", "raw path"])?;
        Ok(())
    }

    #[cfg(not(unix))]
    fn setup_non_utf8_path(&self) -> Result<(), GitFixtureError> {
        Err(FixtureSkip {
            capability: FixtureCapability::NonUtf8Paths,
            reason: "raw byte paths require Unix".to_owned(),
        }
        .into())
    }

    #[cfg(unix)]
    fn setup_special_files(&self) -> Result<(), GitFixtureError> {
        use std::os::unix::fs::symlink;

        self.write("executable.sh", b"#!/bin/sh\nexit 0\n")?;
        let executable = self.root.join("executable.sh");
        fs::set_permissions(&executable, fs::Permissions::from_mode(0o755))?;
        symlink("executable.sh", self.root.join("link"))?;
        self.checked(["add", "--all"])?;
        self.checked(["commit", "--quiet", "-m", "special files"])?;
        Ok(())
    }

    #[cfg(not(unix))]
    fn setup_special_files(&self) -> Result<(), GitFixtureError> {
        Err(FixtureSkip {
            capability: FixtureCapability::Symlinks,
            reason: "symlinks and executable bits require Unix".to_owned(),
        }
        .into())
    }

    #[cfg(unix)]
    fn setup_attributes(&self) -> Result<(), GitFixtureError> {
        let filter = self.workspace.root().join("bin/larch-filter");
        let script = "#!/bin/sh\nprintf '%s\\n' \"$1\" >> \"${LARCH_GIT_FIXTURE_TRANSCRIPTS}/filter.log\"\n/bin/cat\n";
        fs::write(&filter, script)?;
        fs::set_permissions(&filter, fs::Permissions::from_mode(0o755))?;
        self.write(
            ".gitattributes",
            b"filtered.txt filter=larch eol=crlf\n*.bin -text\n",
        )?;
        self.checked(["config", "filter.larch.clean", "larch-filter clean"])?;
        self.checked(["config", "filter.larch.smudge", "larch-filter smudge"])?;
        self.write("filtered.txt", b"one\ntwo\n")?;
        self.write("payload.bin", b"\x00\xff\n")?;
        self.checked(["add", "--all"])?;
        self.checked(["commit", "--quiet", "-m", "attributes"])?;
        Ok(())
    }

    #[cfg(not(unix))]
    fn setup_attributes(&self) -> Result<(), GitFixtureError> {
        Err(FixtureSkip {
            capability: FixtureCapability::ExecutableBits,
            reason: "executable filter fixtures require Unix".to_owned(),
        }
        .into())
    }

    fn setup_sparse_checkout(&self) -> Result<(), GitFixtureError> {
        self.write("keep/file.txt", b"keep\n")?;
        self.write("omit/file.txt", b"omit\n")?;
        self.checked(["add", "--all"])?;
        self.checked(["commit", "--quiet", "-m", "sparse seed"])?;
        let init = self.git(["sparse-checkout", "init", "--cone"])?;
        if !init.success() {
            return Err(FixtureSkip {
                capability: FixtureCapability::SparseCheckout,
                reason: diagnostic(&init),
            }
            .into());
        }
        self.checked(["sparse-checkout", "set", "keep"])?;
        Ok(())
    }

    fn setup_submodule(&self) -> Result<(), GitFixtureError> {
        let source = self.workspace.create_dir("submodule-source")?;
        self.checked_at(&source, ["init", "--quiet", "--initial-branch=main"])?;
        fs::write(source.join("child.txt"), b"child\n")?;
        self.checked_at(&source, ["add", "--all"])?;
        self.checked_at(&source, ["commit", "--quiet", "-m", "child"])?;
        self.seed_commit()?;
        let output = self.git([
            OsStr::new("-c"),
            OsStr::new("protocol.file.allow=always"),
            OsStr::new("submodule"),
            OsStr::new("add"),
            OsStr::new("--quiet"),
            source.as_os_str(),
            OsStr::new("submodule"),
        ])?;
        if !output.success() {
            return Err(FixtureSkip {
                capability: FixtureCapability::Submodules,
                reason: diagnostic(&output),
            }
            .into());
        }
        self.checked(["commit", "--quiet", "-am", "add submodule"])?;
        Ok(())
    }

    fn checked_at<I, S>(&self, directory: &Path, arguments: I) -> Result<(), GitFixtureError>
    where
        I: IntoIterator<Item = S>,
        S: AsRef<OsStr>,
    {
        let output = self.run_at(directory, arguments)?;
        if output.success() {
            Ok(())
        } else {
            Err(GitFixtureError::Git(output))
        }
    }

    fn setup_linked_worktree(&self) -> Result<(), GitFixtureError> {
        self.seed_commit()?;
        let linked = self.workspace.root().join("linked-worktree");
        let output = self.git([
            OsStr::new("worktree"),
            OsStr::new("add"),
            OsStr::new("--quiet"),
            OsStr::new("-b"),
            OsStr::new("linked"),
            linked.as_os_str(),
        ])?;
        if !output.success() {
            return Err(FixtureSkip {
                capability: FixtureCapability::LinkedWorktrees,
                reason: diagnostic(&output),
            }
            .into());
        }
        Ok(())
    }

    #[cfg(unix)]
    fn setup_hooks_signing_remotes(&self) -> Result<(), GitFixtureError> {
        self.seed_commit()?;
        let hook = self.root.join(".git/hooks/pre-commit");
        let script = "#!/bin/sh\nprintf 'pre-commit\\n' >> \"${LARCH_GIT_FIXTURE_TRANSCRIPTS}/pre-commit.log\"\n";
        fs::write(&hook, script)?;
        fs::set_permissions(&hook, fs::Permissions::from_mode(0o755))?;
        let helper = self.workspace.root().join("bin/larch-credential-helper");
        let helper_script = "#!/bin/sh\nprintf 'helper\\n' >> \"${LARCH_GIT_FIXTURE_TRANSCRIPTS}/credential-helper.log\"\nprintf 'username=fixture\\npassword=fixture-secret\\n'\n";
        fs::write(&helper, helper_script)?;
        fs::set_permissions(&helper, fs::Permissions::from_mode(0o755))?;
        let askpass = self.workspace.root().join("bin/larch-askpass");
        let askpass_script = "#!/bin/sh\nprintf 'askpass\\n' >> \"${LARCH_GIT_FIXTURE_TRANSCRIPTS}/askpass.log\"\nprintf 'fixture-secret\\n'\n";
        fs::write(&askpass, askpass_script)?;
        fs::set_permissions(&askpass, fs::Permissions::from_mode(0o755))?;
        self.checked(["config", "commit.gpgSign", "true"])?;
        self.checked(["config", "tag.gpgSign", "true"])?;
        self.checked(["config", "user.signingKey", "fixture-key"])?;
        self.checked([
            "remote",
            "add",
            "origin",
            "https://user:secret@example.invalid/repo.git",
        ])?;
        self.checked([
            "remote",
            "add",
            "ssh-origin",
            "ssh://git@example.invalid/repo.git",
        ])?;
        self.checked(["config", "credential.helper", "!larch-credential-helper"])?;
        self.checked(["config", "core.askPass", "larch-askpass"])?;
        let credential = self.run_with_input(
            ["credential", "fill"],
            b"protocol=https\nhost=example.invalid\n\n",
        )?;
        if !credential.success() {
            return Err(GitFixtureError::Git(credential));
        }
        self.write("hooked.txt", b"hooked\n")?;
        self.checked(["add", "hooked.txt"])?;
        let commit = self.git([
            "-c",
            "commit.gpgSign=false",
            "commit",
            "--quiet",
            "-m",
            "hooked",
        ])?;
        if !commit.success() {
            return Err(GitFixtureError::Git(commit));
        }
        Ok(())
    }

    #[cfg(not(unix))]
    fn setup_hooks_signing_remotes(&self) -> Result<(), GitFixtureError> {
        Err(FixtureSkip {
            capability: FixtureCapability::ExecutableBits,
            reason: "executable hook fixtures require Unix".to_owned(),
        }
        .into())
    }

    fn setup_corrupt(&self) -> Result<(), GitFixtureError> {
        self.seed_commit()?;
        let object = self.checked(["rev-parse", "HEAD"])?;
        let hex = String::from_utf8(object.stdout)
            .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
        let hex = hex.trim();
        let object_path = self
            .root
            .join(".git/objects")
            .join(&hex[..2])
            .join(&hex[2..]);
        #[cfg(unix)]
        {
            let mut permissions = fs::metadata(&object_path)?.permissions();
            permissions.set_mode(0o600);
            fs::set_permissions(&object_path, permissions)?;
        }
        #[cfg(not(unix))]
        {
            let mut permissions = fs::metadata(&object_path)?.permissions();
            permissions.set_readonly(false);
            fs::set_permissions(&object_path, permissions)?;
        }
        fs::write(object_path, b"corrupt")?;
        Ok(())
    }
}

/// Public result bytes supplied by the operation under comparison.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionSnapshot {
    pub exit_class: ExitClass,
    stdout: BoundedBytes,
    stderr: BoundedBytes,
}

impl ExecutionSnapshot {
    #[must_use]
    pub fn success() -> Self {
        Self {
            exit_class: ExitClass::Success,
            stdout: BoundedBytes::new(&[]),
            stderr: BoundedBytes::new(&[]),
        }
    }

    #[must_use]
    pub fn from_git(repository: &GitRepository, output: &GitCommandOutput) -> Self {
        let exit_class = if output.interrupted {
            ExitClass::Interrupted
        } else if output.code == Some(0) {
            ExitClass::Success
        } else {
            ExitClass::Failure(output.code)
        };
        Self {
            exit_class,
            stdout: bounded_normalized(&output.stdout, repository),
            stderr: bounded_normalized(&output.stderr, repository),
        }
    }
}

/// Stable exit category for a compared operation or probe.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExitClass {
    Success,
    Failure(Option<i32>),
    Interrupted,
}

/// Bounded exact bytes plus a full-input checksum when truncation occurs.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BoundedBytes {
    pub bytes: Vec<u8>,
    pub total_len: usize,
    pub checksum: u64,
    pub truncated: bool,
}

impl BoundedBytes {
    #[must_use]
    pub fn new(bytes: &[u8]) -> Self {
        Self {
            bytes: bytes[..bytes.len().min(SNAPSHOT_BYTE_LIMIT)].to_vec(),
            total_len: bytes.len(),
            checksum: fnv1a(bytes),
            truncated: bytes.len() > SNAPSHOT_BYTE_LIMIT,
        }
    }
}

/// One installed-Git probe preserved even when the repository is corrupt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProbeSnapshot {
    pub exit_class: ExitClass,
    pub stdout: BoundedBytes,
    pub stderr: BoundedBytes,
}

/// Kind of filesystem entry in a semantic snapshot.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SnapshotEntryKind {
    File,
    Directory,
    Symlink,
}

/// Byte-path filesystem state with stable mode and bounded content.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SnapshotEntry {
    pub path: Vec<u8>,
    pub kind: SnapshotEntryKind,
    pub mode: u32,
    pub contents: BoundedBytes,
}

/// Bounded semantic repository state for differential comparisons.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SemanticSnapshot {
    pub schema: u32,
    pub execution: ExecutionSnapshot,
    pub head_symbolic: ProbeSnapshot,
    pub head_object: ProbeSnapshot,
    pub objects: ProbeSnapshot,
    pub refs: ProbeSnapshot,
    pub reflogs: ProbeSnapshot,
    pub index: ProbeSnapshot,
    pub index_flags: ProbeSnapshot,
    pub untracked: ProbeSnapshot,
    pub ignored: ProbeSnapshot,
    pub linked_worktrees: ProbeSnapshot,
    pub config: ProbeSnapshot,
    pub worktree: Vec<SnapshotEntry>,
    pub operation_state: Vec<SnapshotEntry>,
    pub transcripts: Vec<SnapshotEntry>,
    pub fsck: ProbeSnapshot,
    pub entries_truncated: bool,
}

impl SemanticSnapshot {
    /// Capture repository semantics without requiring a healthy object database.
    ///
    /// # Errors
    /// Returns filesystem or process-start errors. Git probe failures are data.
    pub fn capture(repository: &GitRepository, execution: ExecutionSnapshot) -> io::Result<Self> {
        let (worktree, worktree_cut) = collect_tree(repository, &repository.root, true)?;
        let (operation_state, state_cut) = collect_operation_state(repository)?;
        let (transcripts, transcript_cut) =
            collect_tree(repository, &repository.transcript_root, false)?;
        Ok(Self {
            schema: SNAPSHOT_SCHEMA,
            execution,
            head_symbolic: probe(repository, ["symbolic-ref", "--quiet", "HEAD"])?,
            head_object: probe(repository, ["rev-parse", "--verify", "HEAD"])?,
            objects: probe(
                repository,
                [
                    "cat-file",
                    "--batch-all-objects",
                    "--batch-check=%(objectname) %(objecttype)",
                ],
            )?,
            refs: probe(
                repository,
                [
                    "for-each-ref",
                    "--format=%(refname)%00%(objectname)%00%(objecttype)",
                ],
            )?,
            reflogs: probe(
                repository,
                ["reflog", "show", "--all", "--format=%gd%x00%H%x00%gs"],
            )?,
            index: probe(repository, ["ls-files", "--stage", "-z"])?,
            index_flags: probe(repository, ["ls-files", "-v", "-z"])?,
            untracked: probe(
                repository,
                ["ls-files", "--others", "--exclude-standard", "-z"],
            )?,
            ignored: probe(
                repository,
                [
                    "ls-files",
                    "--others",
                    "--ignored",
                    "--exclude-standard",
                    "-z",
                ],
            )?,
            linked_worktrees: probe(repository, ["worktree", "list", "--porcelain", "-z"])?,
            config: probe(repository, ["config", "--null", "--list", "--show-origin"])?,
            worktree,
            operation_state,
            transcripts,
            fsck: probe(repository, ["fsck", "--full", "--no-dangling"])?,
            entries_truncated: worktree_cut || state_cut || transcript_cut,
        })
    }

    /// Render a stable, byte-safe text form suitable for checked-in snapshots.
    #[must_use]
    pub fn render(&self) -> String {
        let mut output = format!("larch-git-snapshot-v{}\n", self.schema);
        render_execution(&mut output, "execution", &self.execution);
        for (name, probe) in [
            ("head_symbolic", &self.head_symbolic),
            ("head_object", &self.head_object),
            ("objects", &self.objects),
            ("refs", &self.refs),
            ("reflogs", &self.reflogs),
            ("index", &self.index),
            ("index_flags", &self.index_flags),
            ("untracked", &self.untracked),
            ("ignored", &self.ignored),
            ("linked_worktrees", &self.linked_worktrees),
            ("config", &self.config),
            ("fsck", &self.fsck),
        ] {
            render_probe(&mut output, name, probe);
        }
        render_entries(&mut output, "worktree", &self.worktree);
        render_entries(&mut output, "operation_state", &self.operation_state);
        render_entries(&mut output, "transcripts", &self.transcripts);
        writeln!(output, "entries_truncated={}", self.entries_truncated)
            .expect("writing to String cannot fail");
        output
    }
}

fn probe<I, S>(repository: &GitRepository, arguments: I) -> io::Result<ProbeSnapshot>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let output = repository.git(arguments)?;
    Ok(ProbeSnapshot {
        exit_class: ExecutionSnapshot::from_git(repository, &output).exit_class,
        stdout: bounded_normalized(&output.stdout, repository),
        stderr: bounded_normalized(&output.stderr, repository),
    })
}

fn collect_operation_state(repository: &GitRepository) -> io::Result<(Vec<SnapshotEntry>, bool)> {
    let git_dir = repository.root.join(".git");
    let mut entries = Vec::new();
    for name in [
        "MERGE_HEAD",
        "MERGE_MSG",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "REBASE_HEAD",
        "BISECT_LOG",
        "rebase-merge",
        "rebase-apply",
        "sequencer",
    ] {
        let path = git_dir.join(name);
        if path.exists() {
            collect_path(repository, &git_dir, &path, &mut entries)?;
        }
    }
    entries.sort_by(|left, right| left.path.cmp(&right.path));
    let truncated = entries.len() > SNAPSHOT_ENTRY_LIMIT;
    entries.truncate(SNAPSHOT_ENTRY_LIMIT);
    Ok((entries, truncated))
}

fn collect_tree(
    repository: &GitRepository,
    root: &Path,
    omit_root_dot_git: bool,
) -> io::Result<(Vec<SnapshotEntry>, bool)> {
    let mut entries = Vec::new();
    for child in sorted_children(root)? {
        if omit_root_dot_git && child.file_name() == Some(OsStr::new(".git")) {
            continue;
        }
        collect_path(repository, root, &child, &mut entries)?;
        if entries.len() > SNAPSHOT_ENTRY_LIMIT {
            break;
        }
    }
    entries.sort_by(|left, right| left.path.cmp(&right.path));
    let truncated = entries.len() > SNAPSHOT_ENTRY_LIMIT;
    entries.truncate(SNAPSHOT_ENTRY_LIMIT);
    Ok((entries, truncated))
}

fn collect_path(
    repository: &GitRepository,
    root: &Path,
    path: &Path,
    entries: &mut Vec<SnapshotEntry>,
) -> io::Result<()> {
    if entries.len() > SNAPSHOT_ENTRY_LIMIT {
        return Ok(());
    }
    let metadata = fs::symlink_metadata(path)?;
    let kind = if metadata.file_type().is_symlink() {
        SnapshotEntryKind::Symlink
    } else if metadata.is_dir() {
        SnapshotEntryKind::Directory
    } else {
        SnapshotEntryKind::File
    };
    let contents = match kind {
        SnapshotEntryKind::File => fs::read(path)?,
        SnapshotEntryKind::Symlink => path_bytes(&fs::read_link(path)?),
        SnapshotEntryKind::Directory => Vec::new(),
    };
    let relative = path.strip_prefix(root).map_err(io::Error::other)?;
    entries.push(SnapshotEntry {
        path: path_bytes(relative),
        kind,
        mode: file_mode(&metadata),
        contents: bounded_normalized(&contents, repository),
    });
    if kind == SnapshotEntryKind::Directory {
        for child in sorted_children(path)? {
            collect_path(repository, root, &child, entries)?;
        }
    }
    Ok(())
}

fn sorted_children(path: &Path) -> io::Result<Vec<PathBuf>> {
    let mut children = fs::read_dir(path)?
        .map(|entry| entry.map(|value| value.path()))
        .collect::<io::Result<Vec<_>>>()?;
    children.sort_by_key(|left| path_bytes(left));
    Ok(children)
}

fn bounded_normalized(bytes: &[u8], repository: &GitRepository) -> BoundedBytes {
    BoundedBytes::new(&normalize_bytes(bytes, repository.workspace.root()))
}

fn normalize_bytes(input: &[u8], root: &Path) -> Vec<u8> {
    let replaced = replace_all(input, &path_bytes(root), b"<ROOT>");
    redact_lines(&replaced)
}

fn redact_lines(input: &[u8]) -> Vec<u8> {
    let mut output = Vec::with_capacity(input.len());
    for line in input.split_inclusive(|byte| *byte == b'\n' || *byte == 0) {
        let lowercase = line.to_ascii_lowercase();
        if [
            b"credential".as_slice(),
            b"password",
            b"token",
            b"authorization",
        ]
        .iter()
        .any(|needle| contains(&lowercase, needle))
        {
            output.extend_from_slice(b"<REDACTED>");
            if let Some(delimiter) = line.last().filter(|byte| **byte == b'\n' || **byte == 0) {
                output.push(*delimiter);
            }
        } else {
            output.extend_from_slice(&redact_url_userinfo(line));
        }
    }
    output
}

fn redact_url_userinfo(input: &[u8]) -> Vec<u8> {
    let Some(scheme) = find_bytes(input, b"://") else {
        return input.to_vec();
    };
    let authority = scheme + 3;
    let Some(at_relative) = input[authority..].iter().position(|byte| *byte == b'@') else {
        return input.to_vec();
    };
    let at = authority + at_relative;
    if !input[authority..at].contains(&b':') {
        return input.to_vec();
    }
    let mut output = input[..authority].to_vec();
    output.extend_from_slice(b"<REDACTED>@");
    output.extend_from_slice(&input[at + 1..]);
    output
}

fn replace_all(input: &[u8], needle: &[u8], replacement: &[u8]) -> Vec<u8> {
    if needle.is_empty() {
        return input.to_vec();
    }
    let mut output = Vec::with_capacity(input.len());
    let mut remaining = input;
    while let Some(index) = find_bytes(remaining, needle) {
        output.extend_from_slice(&remaining[..index]);
        output.extend_from_slice(replacement);
        remaining = &remaining[index + needle.len()..];
    }
    output.extend_from_slice(remaining);
    output
}

fn contains(haystack: &[u8], needle: &[u8]) -> bool {
    find_bytes(haystack, needle).is_some()
}

fn find_bytes(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack
        .windows(needle.len())
        .position(|window| window == needle)
}

fn render_execution(output: &mut String, name: &str, execution: &ExecutionSnapshot) {
    writeln!(output, "[{name}] exit={:?}", execution.exit_class)
        .expect("writing to String cannot fail");
    render_bytes(output, "stdout", &execution.stdout);
    render_bytes(output, "stderr", &execution.stderr);
}

fn render_probe(output: &mut String, name: &str, probe: &ProbeSnapshot) {
    writeln!(output, "[{name}] exit={:?}", probe.exit_class)
        .expect("writing to String cannot fail");
    render_bytes(output, "stdout", &probe.stdout);
    render_bytes(output, "stderr", &probe.stderr);
}

fn render_entries(output: &mut String, name: &str, entries: &[SnapshotEntry]) {
    writeln!(output, "[{name}] count={}", entries.len()).expect("writing to String cannot fail");
    for entry in entries {
        write!(
            output,
            "path={} kind={:?} mode={:o} ",
            hex(&entry.path),
            entry.kind,
            entry.mode
        )
        .expect("writing to String cannot fail");
        render_bytes(output, "contents", &entry.contents);
    }
}

fn render_bytes(output: &mut String, name: &str, bytes: &BoundedBytes) {
    writeln!(
        output,
        "{name}=hex:{} len={} checksum={:016x} truncated={}",
        hex(&bytes.bytes),
        bytes.total_len,
        bytes.checksum,
        bytes.truncated
    )
    .expect("writing to String cannot fail");
}

fn hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        output.push(char::from(DIGITS[usize::from(byte >> 4)]));
        output.push(char::from(DIGITS[usize::from(byte & 0x0f)]));
    }
    output
}

const fn fnv1a(bytes: &[u8]) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    let mut index = 0;
    while index < bytes.len() {
        hash ^= bytes[index] as u64;
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        index += 1;
    }
    hash
}

fn command_output(status: ExitStatus, stdout: Vec<u8>, stderr: Vec<u8>) -> GitCommandOutput {
    #[cfg(unix)]
    let interrupted = status.signal().is_some();
    #[cfg(not(unix))]
    let interrupted = !status.success() && status.code().is_none();
    GitCommandOutput {
        code: status.code(),
        interrupted,
        stdout,
        stderr,
    }
}

fn find_git() -> io::Result<PathBuf> {
    let path = std::env::var_os("PATH")
        .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "PATH is not set"))?;
    for directory in std::env::split_paths(&path) {
        let candidate = directory.join(git_binary_name());
        if candidate.is_file() {
            return fs::canonicalize(candidate);
        }
    }
    Err(io::Error::new(
        io::ErrorKind::NotFound,
        "installed Git was not found on PATH",
    ))
}

const fn git_binary_name() -> &'static str {
    if cfg!(windows) { "git.exe" } else { "git" }
}

const fn null_device() -> &'static str {
    if cfg!(windows) { "NUL" } else { "/dev/null" }
}

fn diagnostic(output: &GitCommandOutput) -> String {
    let bytes = if output.stderr.is_empty() {
        &output.stdout
    } else {
        &output.stderr
    };
    String::from_utf8_lossy(bytes).trim().to_owned()
}

fn path_bytes(path: &Path) -> Vec<u8> {
    path.as_os_str().as_encoded_bytes().to_vec()
}

#[cfg(unix)]
fn file_mode(metadata: &fs::Metadata) -> u32 {
    metadata.permissions().mode() & 0o7777
}

#[cfg(not(unix))]
fn file_mode(metadata: &fs::Metadata) -> u32 {
    if metadata.permissions().readonly() {
        0o444
    } else {
        0o666
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture_or_skip(builder: GitRepositoryBuilder) -> Option<GitRepository> {
        match builder.build() {
            Ok(repository) => Some(repository),
            Err(GitFixtureError::Skip(skip)) => {
                eprintln!("explicit capability skip: {skip}");
                None
            }
            Err(error) => panic!("fixture failed: {error}"),
        }
    }

    fn assert_named_semantics(fixture: GitFixture, snapshot: &SemanticSnapshot) {
        match fixture {
            GitFixture::Unborn => assert_ne!(snapshot.head_object.exit_class, ExitClass::Success),
            GitFixture::Detached => {
                assert_ne!(snapshot.head_symbolic.exit_class, ExitClass::Success);
                assert_eq!(snapshot.head_object.exit_class, ExitClass::Success);
            }
            GitFixture::Refs => {
                assert!(contains(
                    &snapshot.refs.stdout.bytes,
                    b"refs/remotes/origin/main"
                ));
                assert!(contains(&snapshot.refs.stdout.bytes, b"refs/tags/v1"));
            }
            GitFixture::Changes => {
                assert!(!snapshot.untracked.stdout.bytes.is_empty());
                assert!(!snapshot.ignored.stdout.bytes.is_empty());
            }
            GitFixture::Conflict => {
                assert!(contains(&snapshot.index.stdout.bytes, b" 1\ttracked.txt"));
                assert!(!snapshot.operation_state.is_empty());
            }
            GitFixture::NonUtf8Path => {
                assert!(
                    snapshot
                        .worktree
                        .iter()
                        .any(|entry| entry.path.contains(&0xff))
                );
            }
            GitFixture::SpecialFiles => {
                assert!(
                    snapshot
                        .worktree
                        .iter()
                        .any(|entry| entry.kind == SnapshotEntryKind::Symlink)
                );
                assert!(
                    snapshot
                        .worktree
                        .iter()
                        .any(|entry| entry.mode & 0o111 != 0)
                );
            }
            GitFixture::AttributesAndFilters => {
                assert!(!snapshot.transcripts.is_empty());
                assert!(contains(
                    &snapshot.config.stdout.bytes,
                    b"filter.larch.clean"
                ));
            }
            GitFixture::SparseCheckout => {
                assert!(contains(&snapshot.index_flags.stdout.bytes, b"S "));
            }
            GitFixture::Submodule => assert!(contains(&snapshot.index.stdout.bytes, b"160000")),
            GitFixture::LinkedWorktree => {
                assert!(contains(&snapshot.linked_worktrees.stdout.bytes, b"<ROOT>"));
            }
            GitFixture::HooksSigningAndRemotes => {
                assert!(snapshot.transcripts.len() >= 2);
                assert!(contains(&snapshot.config.stdout.bytes, b"ssh-origin"));
            }
            GitFixture::Corrupt => assert_ne!(snapshot.fsck.exit_class, ExitClass::Success),
        }
    }

    #[test]
    fn named_fixture_matrix_captures_required_states() {
        for fixture in [
            GitFixture::Unborn,
            GitFixture::Detached,
            GitFixture::Refs,
            GitFixture::Changes,
            GitFixture::Conflict,
            GitFixture::NonUtf8Path,
            GitFixture::SpecialFiles,
            GitFixture::AttributesAndFilters,
            GitFixture::SparseCheckout,
            GitFixture::Submodule,
            GitFixture::LinkedWorktree,
            GitFixture::HooksSigningAndRemotes,
        ] {
            let Some(repository) = fixture_or_skip(GitRepository::builder(fixture)) else {
                continue;
            };
            let snapshot = SemanticSnapshot::capture(&repository, ExecutionSnapshot::success())
                .expect("semantic snapshot");
            assert_eq!(snapshot.schema, SNAPSHOT_SCHEMA);
            assert!(snapshot.fsck.exit_class == ExitClass::Success);
            assert!(snapshot.render().starts_with("larch-git-snapshot-v1\n"));
            assert_named_semantics(fixture, &snapshot);
        }
    }

    #[test]
    fn sha256_snapshot_is_supported_or_explicitly_skipped() {
        let Some(repository) = fixture_or_skip(
            GitRepository::builder(GitFixture::Refs).object_format(GitObjectFormat::Sha256),
        ) else {
            return;
        };
        let snapshot = SemanticSnapshot::capture(&repository, ExecutionSnapshot::success())
            .expect("SHA-256 snapshot");
        assert!(
            snapshot
                .objects
                .stdout
                .bytes
                .windows(4)
                .any(|window| window == b"blob")
        );
    }

    #[test]
    fn snapshot_distinguishes_unborn_detached_conflict_and_corruption() {
        let unborn = GitRepository::builder(GitFixture::Unborn)
            .build()
            .expect("unborn");
        let detached = GitRepository::builder(GitFixture::Detached)
            .build()
            .expect("detached");
        let conflict = GitRepository::builder(GitFixture::Conflict)
            .build()
            .expect("conflict");
        let corrupt = GitRepository::builder(GitFixture::Corrupt)
            .build()
            .expect("corrupt");
        let capture = |repository: &GitRepository| {
            SemanticSnapshot::capture(repository, ExecutionSnapshot::success()).expect("snapshot")
        };
        let snapshots = [
            capture(&unborn),
            capture(&detached),
            capture(&conflict),
            capture(&corrupt),
        ];
        for left in 0..snapshots.len() {
            for right in left + 1..snapshots.len() {
                assert_ne!(snapshots[left], snapshots[right]);
            }
        }
        assert_ne!(snapshots[3].fsck.exit_class, ExitClass::Success);
        assert!(!snapshots[2].operation_state.is_empty());
    }

    #[test]
    fn public_results_cover_success_failure_and_interruption() {
        let repository = GitRepository::builder(GitFixture::Unborn)
            .build()
            .expect("repository");
        let success = GitCommandOutput {
            code: Some(0),
            interrupted: false,
            stdout: b"ok\n".to_vec(),
            stderr: Vec::new(),
        };
        let failure = GitCommandOutput {
            code: Some(7),
            interrupted: false,
            stdout: Vec::new(),
            stderr: b"failed\n".to_vec(),
        };
        let interrupted = GitCommandOutput {
            code: None,
            interrupted: true,
            stdout: Vec::new(),
            stderr: Vec::new(),
        };
        assert_eq!(
            ExecutionSnapshot::from_git(&repository, &success).exit_class,
            ExitClass::Success
        );
        assert_eq!(
            ExecutionSnapshot::from_git(&repository, &failure).exit_class,
            ExitClass::Failure(Some(7))
        );
        assert_eq!(
            ExecutionSnapshot::from_git(&repository, &interrupted).exit_class,
            ExitClass::Interrupted
        );
        let capture = |output: &GitCommandOutput| {
            SemanticSnapshot::capture(
                &repository,
                ExecutionSnapshot::from_git(&repository, output),
            )
            .expect("result snapshot")
        };
        let snapshots = [capture(&success), capture(&failure), capture(&interrupted)];
        assert_ne!(snapshots[0], snapshots[1]);
        assert_ne!(snapshots[1], snapshots[2]);
    }

    #[test]
    fn equivalent_fixtures_are_stable_without_process_mutation() {
        let original_directory = std::env::current_dir().expect("current directory");
        let original_environment =
            std::env::vars_os().collect::<std::collections::BTreeMap<_, _>>();
        let first = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("first fixture");
        let second = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("second fixture");
        let capture = |repository: &GitRepository| {
            SemanticSnapshot::capture(repository, ExecutionSnapshot::success()).expect("snapshot")
        };

        assert_eq!(capture(&first), capture(&second));
        assert_eq!(
            std::env::current_dir().expect("current directory"),
            original_directory
        );
        assert_eq!(
            std::env::vars_os().collect::<std::collections::BTreeMap<_, _>>(),
            original_environment
        );
    }

    #[test]
    fn snapshot_redacts_credentials_and_normalizes_roots() {
        let repository = GitRepository::builder(GitFixture::HooksSigningAndRemotes)
            .build()
            .expect("remote fixture");
        let snapshot =
            SemanticSnapshot::capture(&repository, ExecutionSnapshot::success()).expect("snapshot");
        assert!(!contains(&snapshot.config.stdout.bytes, b"secret"));
        assert!(contains(&snapshot.config.stdout.bytes, b"<REDACTED>"));

        let linked = GitRepository::builder(GitFixture::LinkedWorktree)
            .build()
            .expect("linked fixture");
        let linked_snapshot = SemanticSnapshot::capture(&linked, ExecutionSnapshot::success())
            .expect("linked snapshot");
        assert!(contains(
            &linked_snapshot.linked_worktrees.stdout.bytes,
            b"<ROOT>"
        ));
        assert!(!contains(
            &linked_snapshot.linked_worktrees.stdout.bytes,
            &path_bytes(linked.workspace_root())
        ));
    }

    #[test]
    fn byte_limits_keep_full_length_and_checksum() {
        let bytes = vec![b'x'; SNAPSHOT_BYTE_LIMIT + 1];
        let bounded = BoundedBytes::new(&bytes);
        assert!(bounded.truncated);
        assert_eq!(bounded.total_len, bytes.len());
        assert_eq!(bounded.bytes.len(), SNAPSHOT_BYTE_LIMIT);
        assert_eq!(bounded.checksum, fnv1a(&bytes));
    }
}
