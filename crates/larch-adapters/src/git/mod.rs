//! Git adapters: trusted `gix` repository reads and closed typed Git CLI mutations.
//!
//! Read-only repository metadata stays on [`GixRepository`]. Installed-Git
//! compatibility exceptions use [`GitCli`] operation-specific methods — there is
//! no public arbitrary-argv Git escape hatch.

mod ops;
mod repository;
mod validate;

use std::{
    error::Error,
    ffi::OsString,
    fmt,
    num::NonZeroUsize,
    path::{Path, PathBuf},
    time::Duration,
};

use larch_core::{
    ChildEnvironment, ExternalProcessRunner, ExternalProgram, ProcessCancellation, ProcessError,
    ProcessErrorKind, ProcessOutput, ProcessRequest, ProcessRequestError, SafeText,
};

pub use ops::{
    AddRequest, ApplyRequest, BranchMutationRequest, CheckoutRequest, CleanRequest, CloneRequest,
    CommitMessage, CommitRequest, ConfigMutationRequest, ExactDiffRequest, FetchRequest,
    ForceWithLease, InitRequest, InterpretTrailersRequest, LsRemoteRequest, MergeRequest,
    PullRequest, PushRequest, RebaseRequest, RemoteMutationRequest, ResetMode, ResetRequest,
    RestoreRequest, RmRequest, SparseCheckoutRequest, StashRequest, SubmoduleRequest,
    TagMutationRequest, VersionRequest, WorktreeRequest,
};
pub use repository::{GixRepository, unified_blob_diff};
pub use validate::{
    GitConfigKey, GitFilePath, GitPath, GitRef, GitRefspec, GitRemote, GitToken, GitUrl,
    WorktreePath,
};

use ops::GitOperation;

const DEFAULT_TIMEOUT: Duration = Duration::from_secs(120);
const DEFAULT_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
const DEFAULT_OUTPUT_LIMIT: usize = 8 * 1024 * 1024;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitCliInputErrorKind {
    Empty,
    NulByte,
    OptionInjection,
    AbsolutePath,
    UnsafePath,
    InvalidRef,
    InvalidRemote,
    InvalidRefspec,
    InvalidConfigKey,
    NonUnicode,
    UnsupportedCombination,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitCliInputError {
    kind: GitCliInputErrorKind,
    message: SafeText,
}

impl GitCliInputError {
    pub(crate) fn new(kind: GitCliInputErrorKind, message: impl AsRef<str>) -> Self {
        Self {
            kind,
            message: SafeText::from_untrusted(message),
        }
    }

    #[must_use]
    pub const fn kind(&self) -> GitCliInputErrorKind {
        self.kind
    }

    #[must_use]
    pub fn message(&self) -> &str {
        self.message.as_str()
    }
}

impl fmt::Display for GitCliInputError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.message.as_str())
    }
}

impl Error for GitCliInputError {}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum GitCliError {
    Input(GitCliInputError),
    Request(ProcessRequestError),
    Process(ProcessError),
    Failed(GitCliResult),
}

impl fmt::Display for GitCliError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Input(error) => error.fmt(formatter),
            Self::Request(error) => error.fmt(formatter),
            Self::Process(error) => error.fmt(formatter),
            Self::Failed(result) => write!(
                formatter,
                "git {} failed with {:?}",
                result.operation,
                result.output.status().code()
            ),
        }
    }
}

impl Error for GitCliError {}

impl From<GitCliInputError> for GitCliError {
    fn from(error: GitCliInputError) -> Self {
        Self::Input(error)
    }
}

impl From<ProcessRequestError> for GitCliError {
    fn from(error: ProcessRequestError) -> Self {
        Self::Request(error)
    }
}

impl From<ProcessError> for GitCliError {
    fn from(error: ProcessError) -> Self {
        Self::Process(error)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitCliResult {
    operation: &'static str,
    output: ProcessOutput,
}

impl GitCliResult {
    #[must_use]
    pub const fn operation(&self) -> &'static str {
        self.operation
    }

    #[must_use]
    pub const fn output(&self) -> &ProcessOutput {
        &self.output
    }

    #[must_use]
    pub fn safe_stdout(&self) -> SafeText {
        self.output.safe_stdout()
    }

    #[must_use]
    pub fn safe_stderr(&self) -> SafeText {
        self.output.safe_stderr()
    }

    #[must_use]
    pub const fn truncated(&self) -> bool {
        self.output.stdout_truncated() || self.output.stderr_truncated()
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitCliPolicy {
    working_directory: PathBuf,
    timeout: Duration,
    shutdown_grace: Duration,
    output_limit: NonZeroUsize,
}

impl GitCliPolicy {
    /// # Errors
    /// Rejects relative working directories.
    ///
    /// # Panics
    /// Never panics: the default output limit is a nonzero compile-time constant.
    pub fn new(working_directory: impl Into<PathBuf>) -> Result<Self, GitCliError> {
        let working_directory = working_directory.into();
        if !working_directory.is_absolute() {
            return Err(GitCliInputError::new(
                GitCliInputErrorKind::AbsolutePath,
                "Git working directory must be absolute",
            )
            .into());
        }
        Ok(Self {
            working_directory,
            timeout: DEFAULT_TIMEOUT,
            shutdown_grace: DEFAULT_SHUTDOWN_GRACE,
            output_limit: NonZeroUsize::new(DEFAULT_OUTPUT_LIMIT).expect("non-zero constant"),
        })
    }

    #[must_use]
    pub const fn with_timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
    }

    #[must_use]
    pub const fn with_shutdown_grace(mut self, shutdown_grace: Duration) -> Self {
        self.shutdown_grace = shutdown_grace;
        self
    }

    #[must_use]
    pub const fn with_output_limit(mut self, output_limit: NonZeroUsize) -> Self {
        self.output_limit = output_limit;
        self
    }

    #[must_use]
    pub fn working_directory(&self) -> &Path {
        &self.working_directory
    }
}

/// Single public owner for installed-Git compatibility exceptions.
pub struct GitCli<'a, R> {
    runner: &'a R,
    policy: GitCliPolicy,
}

macro_rules! git_methods {
    ($($name:ident($ty:ty)),+ $(,)?) => {
        $(
            /// # Errors
            /// Returns input, request, process, or nonzero-Git failures.
            pub async fn $name(
                &self,
                request: $ty,
                cancellation: &dyn ProcessCancellation,
            ) -> Result<GitCliResult, GitCliError> {
                self.run(request, cancellation).await
            }
        )+
    };
}

impl<'a, R> GitCli<'a, R>
where
    R: ExternalProcessRunner,
{
    #[must_use]
    pub const fn new(runner: &'a R, policy: GitCliPolicy) -> Self {
        Self { runner, policy }
    }

    #[must_use]
    pub fn working_directory(&self) -> &Path {
        self.policy.working_directory()
    }

    /// Run `git --version`.
    ///
    /// # Errors
    /// Returns input, request, process, or nonzero-Git failures.
    pub async fn version(
        &self,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<GitCliResult, GitCliError> {
        self.run(VersionRequest, cancellation).await
    }

    git_methods!(
        exact_diff(ExactDiffRequest),
        config_mutation(ConfigMutationRequest),
        remote_mutation(RemoteMutationRequest),
        add(AddRequest),
        rm(RmRequest),
        reset(ResetRequest),
        restore(RestoreRequest),
        checkout(CheckoutRequest),
        clean(CleanRequest),
        apply(ApplyRequest),
        commit(CommitRequest),
        interpret_trailers(InterpretTrailersRequest),
        branch_mutation(BranchMutationRequest),
        worktree(WorktreeRequest),
        init(InitRequest),
        clone_repository(CloneRequest),
        sparse_checkout(SparseCheckoutRequest),
        rebase(RebaseRequest),
        merge(MergeRequest),
        pull(PullRequest),
        stash(StashRequest),
        fetch(FetchRequest),
        push(PushRequest),
        ls_remote(LsRemoteRequest),
        tag_mutation(TagMutationRequest),
        submodule(SubmoduleRequest),
    );

    async fn run<O>(
        &self,
        operation: O,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<GitCliResult, GitCliError>
    where
        O: GitOperation,
    {
        let arguments = operation.arguments()?;
        let request = ProcessRequest::new(
            ExternalProgram::Git(operation.operation()),
            arguments,
            self.policy.working_directory.clone(),
            self.policy.timeout,
            self.policy.shutdown_grace,
            self.policy.output_limit,
        )?
        .with_environment(ChildEnvironment::GitTerminalPrompt, OsString::from("0"))
        // Force a non-interactive editor: `git rebase --continue` after conflict
        // resolution creates a commit and otherwise opens core.editor, which hangs
        // (interactive) or fails (dumb terminal) in this headless runtime. Matches
        // the Python `GIT_EDITOR=true` posture; no larch git op wants an editor.
        .with_environment(ChildEnvironment::GitEditor, OsString::from("true"))
        .with_stdin(operation.stdin());
        let label = request.program().operation();
        let output = self.runner.run(request, cancellation).await?;
        let result = GitCliResult {
            operation: label,
            output,
        };
        if result.output.status().success() {
            Ok(result)
        } else {
            Err(GitCliError::Failed(result))
        }
    }
}

#[must_use]
pub const fn classify_process_error(error: &ProcessError) -> ProcessErrorKind {
    error.kind()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{NoopProcessObserver, TokioProcessRunner, runtime::LarchRuntime};
    use larch_test_support::{
        ExecutionSnapshot, FakeProcessRunner, GitFixture, GitRepository, NeverCancelled,
        ProcessOutputBuilder, SemanticSnapshot, TestWorkspace,
    };
    use std::sync::Arc;

    type DifferentialFamily = fn(&LarchRuntime, &TokioProcessRunner);

    #[derive(Clone, Copy)]
    enum DifferentialComparison {
        Exact,
        Semantic,
        StatusOnly,
    }

    fn policy(root: &Path) -> GitCliPolicy {
        GitCliPolicy::new(root.to_path_buf())
            .expect("absolute policy")
            .with_timeout(Duration::from_secs(30))
            .with_shutdown_grace(Duration::from_millis(200))
            .with_output_limit(NonZeroUsize::new(64 * 1024).expect("limit"))
    }

    fn argv(operation: &(impl GitOperation + ?Sized)) -> Vec<String> {
        let mut arguments = operation.arguments().expect("argv");
        ExternalProgram::Git(operation.operation()).append_fixed_arguments(&mut arguments);
        arguments
            .into_iter()
            .map(|value| value.to_string_lossy().into_owned())
            .collect()
    }

    #[test]
    #[allow(clippy::too_many_lines)] // one assertion per #7671 method family
    fn every_family_builds_fixed_argv_without_opaque_escape() {
        let check = |operation: &dyn GitOperation, want: &[&str]| {
            assert_eq!(argv(operation), want);
        };
        check(&VersionRequest, &["--version"]);
        check(
            &ExactDiffRequest {
                cached: true,
                binary: false,
                no_ext_diff: false,
                numstat_z_rename_50: false,
                unified_context: None,
                name_only: true,
                name_status: false,
                quiet: false,
                exit_code: true,
                base: Some(GitRef::new("HEAD").unwrap()),
                head: None,
                paths: vec![GitPath::new("tracked.txt").unwrap()],
            },
            &[
                "diff",
                "--cached",
                "--name-only",
                "--exit-code",
                "HEAD",
                "--",
                "tracked.txt",
            ],
        );
        check(
            &ExactDiffRequest {
                cached: true,
                binary: true,
                no_ext_diff: true,
                numstat_z_rename_50: false,
                unified_context: None,
                name_only: false,
                name_status: false,
                quiet: false,
                exit_code: false,
                base: None,
                head: None,
                paths: Vec::new(),
            },
            &["diff", "--cached", "--binary", "--no-ext-diff"],
        );
        check(
            &ConfigMutationRequest::Set {
                key: GitConfigKey::new("user.name").unwrap(),
                value: "Larch".into(),
            },
            &["config", "--local", "user.name", "Larch"],
        );
        check(
            &RemoteMutationRequest::Add {
                name: GitRemote::new("origin").unwrap(),
                url: GitUrl::new("https://example.invalid/repo.git").unwrap(),
            },
            &[
                "remote",
                "add",
                "origin",
                "https://example.invalid/repo.git",
            ],
        );
        check(
            &AddRequest {
                all: false,
                force: false,
                pathspec_from_file: None,
                pathspec_file_nul: false,
                paths: vec![GitPath::new("tracked.txt").unwrap()],
            },
            &["add", "--", "tracked.txt"],
        );
        check(
            &RmRequest {
                force: true,
                paths: vec![GitPath::new("tracked.txt").unwrap()],
            },
            &["rm", "--force", "--", "tracked.txt"],
        );
        check(
            &ResetRequest {
                mode: ResetMode::Hard,
                target: GitRef::new("HEAD").unwrap(),
                paths: Vec::new(),
            },
            &["reset", "--hard", "HEAD"],
        );
        check(
            &RestoreRequest {
                source: None,
                staged: true,
                paths: vec![GitPath::new("tracked.txt").unwrap()],
            },
            &["restore", "--staged", "--", "tracked.txt"],
        );
        check(
            &CheckoutRequest::Branch {
                create: true,
                force: false,
                no_track: false,
                name: GitRef::new("topic").unwrap(),
                start_point: Some(GitRef::new("HEAD").unwrap()),
            },
            &["checkout", "-b", "topic", "HEAD"],
        );
        check(
            &CheckoutRequest::Branch {
                create: true,
                force: false,
                no_track: true,
                name: GitRef::new("topic").unwrap(),
                start_point: Some(GitRef::new("origin/main").unwrap()),
            },
            &["checkout", "--no-track", "-b", "topic", "origin/main"],
        );
        check(
            &CleanRequest {
                directories: true,
                force: true,
            },
            &["clean", "--force", "-d"],
        );
        check(
            &ApplyRequest {
                patch: GitFilePath::new("change.patch").unwrap(),
                cached: false,
                index: true,
                check: false,
            },
            &["apply", "--index", "change.patch"],
        );
        check(
            &ApplyRequest {
                patch: GitFilePath::new("/tmp/change.patch").unwrap(),
                cached: true,
                index: false,
                check: false,
            },
            &["apply", "--cached", "/tmp/change.patch"],
        );
        check(
            &CommitRequest {
                message: Some(CommitMessage::Literal("msg".into())),
                amend: false,
                no_edit: false,
                allow_empty: true,
                only: false,
                pathspec_from_file: None,
                pathspec_file_nul: false,
                paths: Vec::new(),
            },
            &["commit", "--allow-empty", "-m", "msg"],
        );
        check(
            &InterpretTrailersRequest {
                trailers: vec!["Signed-off-by: A <a@b>".into()],
                in_place: None,
                add_if_different: false,
                add_if_missing: false,
                stdin: b"subject\n".to_vec(),
            },
            &["interpret-trailers", "--trailer", "Signed-off-by: A <a@b>"],
        );
        check(
            &BranchMutationRequest::Create {
                force: false,
                name: GitRef::new("topic").unwrap(),
                start_point: None,
            },
            &["branch", "topic"],
        );
        check(
            &WorktreeRequest::Add {
                branch: Some(GitRef::new("linked").unwrap()),
                detach: false,
                path: WorktreePath::new("/tmp/linked-worktree").unwrap(),
                start_point: None,
            },
            &["worktree", "add", "-b", "linked", "/tmp/linked-worktree"],
        );
        check(
            &InitRequest {
                directory: None,
                initial_branch: Some(GitRef::new("main").unwrap()),
            },
            &["init", "--initial-branch", "main"],
        );
        check(
            &CloneRequest {
                url: GitUrl::new("https://example.invalid/repo.git").unwrap(),
                directory: Some(GitPath::new("clone").unwrap()),
            },
            &["clone", "https://example.invalid/repo.git", "clone"],
        );
        check(
            &SparseCheckoutRequest::Set {
                paths: vec![GitPath::new("keep").unwrap()],
            },
            &["sparse-checkout", "set", "keep"],
        );
        check(&RebaseRequest::Abort, &["rebase", "--abort"]);
        check(
            &MergeRequest::Commit {
                theirs: GitRef::new("topic").unwrap(),
                no_edit: true,
            },
            &["merge", "--no-edit", "topic"],
        );
        check(
            &PullRequest {
                remote: GitRemote::new("origin").unwrap(),
                refspec: Some(GitRefspec::new("main").unwrap()),
                fast_forward_only: true,
            },
            &["pull", "--ff-only", "origin", "main"],
        );
        check(
            &StashRequest::Push {
                message: Some("wip".into()),
            },
            &["stash", "push", "-m", "wip"],
        );
        check(
            &FetchRequest {
                remote: GitRemote::new("origin").unwrap(),
                refspec: Some(GitRefspec::new("main").unwrap()),
                quiet: true,
                no_tags: true,
            },
            &["fetch", "--no-tags", "--quiet", "origin", "main"],
        );
        check(
            &PushRequest {
                remote: GitRemote::new("origin").unwrap(),
                refspec: GitRefspec::new("HEAD:main").unwrap(),
                force_with_lease: Some(ForceWithLease::Enabled),
                set_upstream: false,
            },
            &["push", "--force-with-lease", "origin", "HEAD:main"],
        );
        check(
            &LsRemoteRequest {
                remote: GitRemote::new("origin").unwrap(),
                patterns: vec![GitRef::new("HEAD").unwrap()],
                heads: false,
                exit_code: false,
            },
            &["ls-remote", "origin", "HEAD"],
        );
        check(
            &LsRemoteRequest {
                remote: GitRemote::new("origin").unwrap(),
                patterns: vec![GitRef::new("feat").unwrap()],
                heads: true,
                exit_code: true,
            },
            &["ls-remote", "--exit-code", "--heads", "origin", "feat"],
        );
        check(
            &TagMutationRequest::Create {
                force: false,
                name: GitRef::new("v1").unwrap(),
                target: None,
                message: Some("release".into()),
            },
            &["tag", "-m", "release", "v1"],
        );
        check(
            &SubmoduleRequest::Update {
                init: true,
                recursive: true,
            },
            &["submodule", "update", "--init", "--recursive"],
        );
        check(
            &SubmoduleRequest::Foreach {
                recursive: false,
                command: vec![GitToken::new("true").unwrap()],
            },
            &["submodule", "foreach", "true"],
        );
    }

    #[test]
    fn invalid_inputs_are_rejected_before_launch() {
        let runner = FakeProcessRunner::new([]);
        let workspace = TestWorkspace::new().expect("workspace");
        let git = GitCli::new(&runner, policy(workspace.root()));
        let runtime = LarchRuntime::current_thread().expect("runtime");
        assert!(matches!(
            runtime.block_on(git.add(
                AddRequest {
                    all: false,
                    force: false,
                    pathspec_from_file: None,
                    pathspec_file_nul: false,
                    paths: Vec::new(),
                },
                &NeverCancelled,
            )),
            Err(GitCliError::Input(_))
        ));
        assert!(runner.requests().is_empty());
        assert!(GitPath::new("-all").is_err());
        assert!(GitRef::new("--force").is_err());
        assert!(
            AddRequest {
                all: true,
                force: false,
                pathspec_from_file: None,
                pathspec_file_nul: false,
                paths: vec![GitPath::new("a").unwrap()],
            }
            .arguments()
            .is_err()
        );
        assert!(
            ExactDiffRequest {
                cached: false,
                binary: false,
                no_ext_diff: false,
                numstat_z_rename_50: false,
                unified_context: None,
                name_only: true,
                name_status: true,
                quiet: false,
                exit_code: false,
                base: None,
                head: None,
                paths: Vec::new(),
            }
            .arguments()
            .is_err()
        );
        assert!(
            CheckoutRequest::Branch {
                create: false,
                force: false,
                no_track: false,
                name: GitRef::new("topic").unwrap(),
                start_point: Some(GitRef::new("HEAD").unwrap()),
            }
            .arguments()
            .is_err()
        );
        assert!(
            CheckoutRequest::Branch {
                create: false,
                force: false,
                no_track: true,
                name: GitRef::new("topic").unwrap(),
                start_point: None,
            }
            .arguments()
            .is_err()
        );
        assert!(
            InterpretTrailersRequest {
                trailers: vec!["Signed-off-by: A <a@b>".into()],
                in_place: Some(GitFilePath::new("MSG").unwrap()),
                add_if_different: false,
                add_if_missing: false,
                stdin: b"body\n".to_vec(),
            }
            .arguments()
            .is_err()
        );
    }

    #[cfg(unix)]
    fn assert_argv(operation: &dyn GitOperation, want: &[&str]) {
        assert_eq!(argv(operation), want);
    }

    #[test]
    #[cfg(unix)]
    fn uncovered_validator_error_branches() {
        use std::os::unix::ffi::OsStringExt;

        assert_eq!(
            GitCliInputError::new(GitCliInputErrorKind::Empty, "empty").kind(),
            GitCliInputErrorKind::Empty
        );
        assert_eq!(
            GitCliInputError::new(GitCliInputErrorKind::Empty, "empty").message(),
            "empty"
        );

        assert!(GitPath::new("/abs").is_err());
        assert!(GitPath::new("..").is_err());
        assert!(GitPath::new("./ok").is_ok());
        assert!(WorktreePath::new("relative-worktree").is_err());
        assert!(WorktreePath::new("/tmp/audit-worktree").is_ok());
        assert!(
            WorktreeRequest::Add {
                branch: Some(GitRef::new("topic").unwrap()),
                detach: true,
                path: WorktreePath::new("/tmp/audit-worktree").unwrap(),
                start_point: None,
            }
            .arguments()
            .is_err()
        );
        assert!(GitRef::new(OsString::from_vec(vec![0xff])).is_err());
        assert!(GitRef::new("bad ref").is_err());
        assert!(GitRef::new("a@{u}").is_err());
        assert!(GitRemote::new(OsString::from_vec(vec![0xff])).is_err());
        assert!(GitRemote::new("origin:x").is_err());
        assert!(GitRefspec::new(OsString::from_vec(vec![0xff])).is_err());
        assert!(GitRefspec::new("has space").is_err());
        assert!(GitRefspec::new(":").is_err());
        assert!(GitRefspec::new("src:").is_err());
        assert!(GitConfigKey::new(OsString::from_vec(vec![0xff])).is_err());
        assert!(GitConfigKey::new("solo").is_err());
        assert!(GitUrl::new("").is_err());
        assert!(GitToken::new(OsString::from_vec(b"a\0b".to_vec())).is_err());
        assert!(
            ConfigMutationRequest::Set {
                key: GitConfigKey::new("user.name").unwrap(),
                value: OsString::new(),
            }
            .arguments()
            .is_err()
        );
        assert!(
            ConfigMutationRequest::Set {
                key: GitConfigKey::new("user.name").unwrap(),
                value: OsString::from_vec(b"a\0b".to_vec()),
            }
            .arguments()
            .is_err()
        );
    }

    #[test]
    #[cfg(unix)]
    fn uncovered_config_remote_add_reset_argv_branches() {
        assert_argv(
            &ExactDiffRequest {
                cached: false,
                binary: false,
                no_ext_diff: false,
                numstat_z_rename_50: false,
                unified_context: None,
                name_only: false,
                name_status: true,
                quiet: true,
                exit_code: false,
                base: Some(GitRef::new("HEAD").unwrap()),
                head: Some(GitRef::new("topic").unwrap()),
                paths: Vec::new(),
            },
            &["diff", "--name-status", "--quiet", "HEAD", "topic"],
        );
        assert_argv(
            &ConfigMutationRequest::Unset {
                key: GitConfigKey::new("user.email").unwrap(),
            },
            &["config", "--local", "--unset", "user.email"],
        );
        assert_argv(
            &ConfigMutationRequest::Add {
                key: GitConfigKey::new("remote.origin.fetch").unwrap(),
                value: "+refs/heads/*:refs/remotes/origin/*".into(),
            },
            &[
                "config",
                "--local",
                "--add",
                "remote.origin.fetch",
                "+refs/heads/*:refs/remotes/origin/*",
            ],
        );
        assert_argv(
            &RemoteMutationRequest::Remove {
                name: GitRemote::new("origin").unwrap(),
            },
            &["remote", "remove", "origin"],
        );
        assert_argv(
            &RemoteMutationRequest::SetUrl {
                name: GitRemote::new("origin").unwrap(),
                url: GitUrl::new("https://example.invalid/other.git").unwrap(),
            },
            &[
                "remote",
                "set-url",
                "origin",
                "https://example.invalid/other.git",
            ],
        );
        assert_argv(
            &RemoteMutationRequest::Rename {
                from: GitRemote::new("origin").unwrap(),
                to: GitRemote::new("upstream").unwrap(),
            },
            &["remote", "rename", "origin", "upstream"],
        );
        assert_argv(
            &AddRequest {
                all: false,
                force: true,
                pathspec_from_file: Some(GitFilePath::new("specs.txt").unwrap()),
                pathspec_file_nul: true,
                paths: Vec::new(),
            },
            &[
                "add",
                "--force",
                "--pathspec-from-file=specs.txt",
                "--pathspec-file-nul",
            ],
        );
        assert_argv(
            &AddRequest {
                all: true,
                force: false,
                pathspec_from_file: None,
                pathspec_file_nul: false,
                paths: Vec::new(),
            },
            &["add", "--all"],
        );
        assert!(
            AddRequest {
                all: false,
                force: false,
                pathspec_from_file: Some(GitFilePath::new("specs.txt").unwrap()),
                pathspec_file_nul: false,
                paths: vec![GitPath::new("a").unwrap()],
            }
            .arguments()
            .is_err()
        );
        assert_argv(
            &ResetRequest {
                mode: ResetMode::Soft,
                target: GitRef::new("HEAD").unwrap(),
                paths: Vec::new(),
            },
            &["reset", "--soft", "HEAD"],
        );
        assert_argv(
            &ResetRequest {
                mode: ResetMode::Mixed,
                target: GitRef::new("HEAD").unwrap(),
                paths: vec![GitPath::new("tracked.txt").unwrap()],
            },
            &["reset", "--mixed", "HEAD", "--", "tracked.txt"],
        );
        assert!(
            ResetRequest {
                mode: ResetMode::Hard,
                target: GitRef::new("HEAD").unwrap(),
                paths: vec![GitPath::new("tracked.txt").unwrap()],
            }
            .arguments()
            .is_err()
        );
    }

    #[test]
    #[cfg(unix)]
    fn uncovered_checkout_and_clean_argv_branches() {
        assert_argv(
            &CheckoutRequest::Paths {
                ours: true,
                theirs: false,
                paths: vec![GitPath::new("conflict.txt").unwrap()],
            },
            &["checkout", "--ours", "--", "conflict.txt"],
        );
        assert_argv(
            &CheckoutRequest::Paths {
                ours: false,
                theirs: true,
                paths: vec![GitPath::new("conflict.txt").unwrap()],
            },
            &["checkout", "--theirs", "--", "conflict.txt"],
        );
        assert!(
            CheckoutRequest::Paths {
                ours: true,
                theirs: true,
                paths: vec![GitPath::new("conflict.txt").unwrap()],
            }
            .arguments()
            .is_err()
        );
        assert_argv(
            &CheckoutRequest::Detach {
                target: GitRef::new("HEAD").unwrap(),
            },
            &["checkout", "--detach", "HEAD"],
        );
        assert!(
            CheckoutRequest::Branch {
                create: false,
                force: true,
                no_track: false,
                name: GitRef::new("topic").unwrap(),
                start_point: None,
            }
            .arguments()
            .is_err()
        );
        assert!(
            CleanRequest {
                directories: false,
                force: false,
            }
            .arguments()
            .is_err()
        );
    }

    #[test]
    #[cfg(unix)]
    fn uncovered_commit_and_trailer_argv_branches() {
        assert_argv(
            &CommitRequest {
                message: Some(CommitMessage::File(GitFilePath::new("MSG").unwrap())),
                amend: true,
                no_edit: false,
                allow_empty: false,
                only: true,
                pathspec_from_file: Some(GitFilePath::new("specs.nul").unwrap()),
                pathspec_file_nul: true,
                paths: Vec::new(),
            },
            &[
                "commit",
                "--amend",
                "--only",
                "--file",
                "MSG",
                "--pathspec-from-file=specs.nul",
                "--pathspec-file-nul",
            ],
        );
        assert_argv(
            &CommitRequest {
                message: None,
                amend: true,
                no_edit: true,
                allow_empty: false,
                only: false,
                pathspec_from_file: None,
                pathspec_file_nul: false,
                paths: Vec::new(),
            },
            &["commit", "--amend", "--no-edit"],
        );
        assert!(
            CommitRequest {
                message: None,
                amend: false,
                no_edit: false,
                allow_empty: false,
                only: false,
                pathspec_from_file: None,
                pathspec_file_nul: false,
                paths: Vec::new(),
            }
            .arguments()
            .is_err()
        );
        assert!(
            InterpretTrailersRequest {
                trailers: Vec::new(),
                in_place: None,
                add_if_different: false,
                add_if_missing: false,
                stdin: Vec::new(),
            }
            .arguments()
            .is_err()
        );
        assert_argv(
            &InterpretTrailersRequest {
                trailers: vec!["Reviewed-by: A <a@b>".into()],
                in_place: Some(GitFilePath::new("MSG").unwrap()),
                add_if_different: true,
                add_if_missing: true,
                stdin: Vec::new(),
            },
            &[
                "interpret-trailers",
                "--if-exists",
                "addIfDifferent",
                "--if-missing",
                "add",
                "--trailer",
                "Reviewed-by: A <a@b>",
                "--in-place",
                "MSG",
            ],
        );
        assert!(
            InterpretTrailersRequest {
                trailers: vec!["Reviewed-by: A <a@b>".into()],
                in_place: Some(GitFilePath::new("MSG").unwrap()),
                add_if_different: false,
                add_if_missing: false,
                stdin: Vec::new(),
            }
            .stdin()
            .is_empty()
        );
    }

    #[test]
    #[cfg(unix)]
    fn uncovered_branch_worktree_and_misc_argv_branches() {
        assert_argv(
            &BranchMutationRequest::Delete {
                force: true,
                name: GitRef::new("topic").unwrap(),
            },
            &["branch", "-D", "topic"],
        );
        assert_argv(
            &BranchMutationRequest::SetUpstream {
                name: GitRef::new("topic").unwrap(),
                upstream: GitRef::new("origin/topic").unwrap(),
            },
            &["branch", "--set-upstream-to", "origin/topic", "topic"],
        );
        assert_argv(
            &WorktreeRequest::Add {
                branch: None,
                detach: true,
                path: WorktreePath::new("/tmp/wt").unwrap(),
                start_point: Some(GitRef::new("HEAD").unwrap()),
            },
            &["worktree", "add", "--detach", "/tmp/wt", "HEAD"],
        );
        assert_argv(
            &WorktreeRequest::Remove {
                force: true,
                path: WorktreePath::new("/tmp/wt").unwrap(),
            },
            &["worktree", "remove", "--force", "/tmp/wt"],
        );
        assert_argv(
            &InitRequest {
                directory: Some(GitPath::new("repo").unwrap()),
                initial_branch: None,
            },
            &["init", "repo"],
        );
        assert_argv(
            &SparseCheckoutRequest::Init { cone: true },
            &["sparse-checkout", "init", "--cone"],
        );
        assert_argv(
            &SparseCheckoutRequest::Disable,
            &["sparse-checkout", "disable"],
        );
        assert!(
            SparseCheckoutRequest::Set { paths: Vec::new() }
                .arguments()
                .is_err()
        );
        assert_argv(
            &RebaseRequest::Start {
                onto: Some(GitRef::new("main").unwrap()),
                upstream: GitRef::new("upstream").unwrap(),
                branch: Some(GitRef::new("topic").unwrap()),
            },
            &["rebase", "--onto", "main", "upstream", "topic"],
        );
        assert_argv(&RebaseRequest::Continue, &["rebase", "--continue"]);
        assert_argv(&RebaseRequest::Skip, &["rebase", "--skip"]);
        assert_argv(&MergeRequest::Abort, &["merge", "--abort"]);
        assert_argv(&StashRequest::Pop, &["stash", "pop"]);
        assert_argv(&StashRequest::Drop, &["stash", "drop"]);
        assert_argv(
            &TagMutationRequest::Create {
                force: true,
                name: GitRef::new("v2").unwrap(),
                target: Some(GitRef::new("HEAD").unwrap()),
                message: None,
            },
            &["tag", "--force", "v2", "HEAD"],
        );
        assert_argv(
            &TagMutationRequest::Delete {
                name: GitRef::new("v1").unwrap(),
            },
            &["tag", "--delete", "v1"],
        );
        assert_argv(
            &SubmoduleRequest::Foreach {
                recursive: true,
                command: vec![GitToken::new("true").unwrap()],
            },
            &["submodule", "foreach", "--recursive", "true"],
        );
        assert!(
            SubmoduleRequest::Foreach {
                recursive: false,
                command: Vec::new(),
            }
            .arguments()
            .is_err()
        );
    }

    #[test]
    fn push_argv_includes_explicit_destination_lease_and_upstream() {
        assert_argv(
            &PushRequest {
                remote: GitRemote::new("origin").unwrap(),
                refspec: GitRefspec::new("HEAD:main").unwrap(),
                force_with_lease: Some(ForceWithLease::Expecting {
                    reference: GitRef::new("refs/heads/main").unwrap(),
                    oid: GitRef::new("abc").unwrap(),
                }),
                set_upstream: true,
            },
            &[
                "push",
                "--set-upstream",
                "--force-with-lease=refs/heads/main:abc",
                "origin",
                "HEAD:main",
            ],
        );
        assert_argv(
            &PushRequest {
                remote: GitRemote::new("origin").unwrap(),
                refspec: GitRefspec::new("HEAD:main").unwrap(),
                force_with_lease: Some(ForceWithLease::ExpectingAbsent {
                    reference: GitRef::new("refs/heads/main").unwrap(),
                }),
                set_upstream: false,
            },
            &[
                "push",
                "--force-with-lease=refs/heads/main:",
                "origin",
                "HEAD:main",
            ],
        );
    }

    #[test]
    fn fake_runner_records_cancellation_timeout_truncation_and_redaction() {
        let token = ["ghp_", "abcdefghijklmnopqrstuvwxyz0123456789AB"].concat();
        let runner = FakeProcessRunner::new([
            Err(ProcessError::new(
                ProcessErrorKind::Cancelled,
                "cancelled",
                None,
            )),
            Err(ProcessError::new(
                ProcessErrorKind::TimedOut,
                "timed out",
                None,
            )),
            Ok(ProcessOutputBuilder::success()
                .stdout(token.as_bytes().to_vec())
                .truncated(true, false)
                .build()),
            Ok(ProcessOutputBuilder::failure(1)
                .stderr(token.as_bytes().to_vec())
                .build()),
        ]);
        let workspace = TestWorkspace::new().expect("workspace");
        let git = GitCli::new(&runner, policy(workspace.root()));
        let runtime = LarchRuntime::current_thread().expect("runtime");
        assert!(matches!(
            runtime.block_on(git.version(&NeverCancelled)),
            Err(GitCliError::Process(ref e)) if e.kind() == ProcessErrorKind::Cancelled
        ));
        assert!(matches!(
            runtime.block_on(git.version(&NeverCancelled)),
            Err(GitCliError::Process(ref e)) if e.kind() == ProcessErrorKind::TimedOut
        ));
        let truncated = runtime.block_on(git.version(&NeverCancelled)).unwrap();
        assert!(truncated.truncated());
        assert_eq!(truncated.safe_stdout().as_str(), "<REDACTED-TOKEN>");
        match runtime.block_on(git.version(&NeverCancelled)) {
            Err(GitCliError::Failed(result)) => {
                assert_eq!(result.safe_stderr().as_str(), "<REDACTED-TOKEN>");
            }
            other => panic!("expected Failed, got {other:?}"),
        }
        let requests = runner.requests();
        assert_eq!(requests.len(), 4);
        assert!(requests.iter().all(|request| {
            request
                .environment()
                .iter()
                .any(|(key, value)| *key == ChildEnvironment::GitTerminalPrompt && value == "0")
                && !request.environment().iter().any(|(key, _)| {
                    matches!(
                        key,
                        ChildEnvironment::AnthropicApiKey
                            | ChildEnvironment::OpenAiApiKey
                            | ChildEnvironment::CursorApiKey
                    )
                })
        }));
    }

    #[test]
    fn differential_config_and_remote_family() {
        run_differential_family(differential_config_and_remote);
    }

    #[test]
    fn differential_index_and_worktree_family() {
        run_differential_family(differential_index_and_worktree);
    }

    #[test]
    fn differential_commit_and_trailers_family() {
        run_differential_family(differential_commit_and_trailers);
    }

    #[test]
    fn differential_checkout_family() {
        run_differential_family(differential_checkout);
    }

    #[test]
    fn differential_rebase_merge_pull_and_stash_family() {
        run_differential_family(differential_rebase_merge_pull_and_stash);
    }

    #[test]
    fn differential_fetch_push_and_ls_remote_family() {
        run_differential_family(differential_fetch_push_and_ls_remote);
    }

    #[test]
    fn differential_tag_family() {
        run_differential_family(differential_tag);
    }

    #[test]
    fn differential_submodule_family() {
        run_differential_family(differential_submodule);
    }

    fn run_differential_family(run: DifferentialFamily) {
        let runtime = LarchRuntime::current_thread().expect("runtime");
        let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
        run(&runtime, &runner);
    }

    fn differential_config_and_remote(runtime: &LarchRuntime, runner: &TokioProcessRunner) {
        assert_differential_case(
            "config set succeeds",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            ["config", "--local", "larch.fixture", "value"],
            |repository, runner, runtime| {
                runtime.block_on(
                    GitCli::new(runner, policy(repository.root())).config_mutation(
                        ConfigMutationRequest::Set {
                            key: GitConfigKey::new("larch.fixture").unwrap(),
                            value: "value".into(),
                        },
                        &NeverCancelled,
                    ),
                )
            },
        );
        assert_differential_case(
            "remote remove fails for an unknown remote",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            ["remote", "remove", "missing"],
            |repository, runner, runtime| {
                runtime.block_on(
                    GitCli::new(runner, policy(repository.root())).remote_mutation(
                        RemoteMutationRequest::Remove {
                            name: GitRemote::new("missing").unwrap(),
                        },
                        &NeverCancelled,
                    ),
                )
            },
        );
    }

    fn differential_index_and_worktree(runtime: &LarchRuntime, runner: &TokioProcessRunner) {
        assert_differential_case(
            "add succeeds",
            runtime,
            runner,
            GitFixture::Changes,
            |repository| {
                repository
                    .write("extra.txt", b"extra\n")
                    .expect("write fixture");
            },
            ["add", "--", "extra.txt"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).add(
                    AddRequest {
                        all: false,
                        force: false,
                        pathspec_from_file: None,
                        pathspec_file_nul: false,
                        paths: vec![GitPath::new("extra.txt").unwrap()],
                    },
                    &NeverCancelled,
                ))
            },
        );
        assert_differential_case(
            "rm fails for a missing path",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            ["rm", "--", "missing.txt"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).rm(
                    RmRequest {
                        force: false,
                        paths: vec![GitPath::new("missing.txt").unwrap()],
                    },
                    &NeverCancelled,
                ))
            },
        );
    }

    fn differential_commit_and_trailers(runtime: &LarchRuntime, runner: &TokioProcessRunner) {
        assert_status_differential_case(
            "commit succeeds",
            runtime,
            runner,
            GitFixture::Refs,
            |repository| {
                repository
                    .git(["config", "user.name", "Larch Fixture"])
                    .expect("configure fixture author");
                repository
                    .git(["config", "user.email", "fixture@example.invalid"])
                    .expect("configure fixture author");
            },
            ["commit", "--allow-empty", "-m", "fixture commit"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).commit(
                    CommitRequest {
                        message: Some(CommitMessage::Literal("fixture commit".into())),
                        amend: false,
                        no_edit: false,
                        allow_empty: true,
                        only: false,
                        pathspec_from_file: None,
                        pathspec_file_nul: false,
                        paths: Vec::new(),
                    },
                    &NeverCancelled,
                ))
            },
        );
        assert_differential_case(
            "interpret-trailers fails for a missing message file",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            [
                "interpret-trailers",
                "--trailer",
                "Reviewed-by: Larch <fixture@example.invalid>",
                "--in-place",
                "missing-message",
            ],
            |repository, runner, runtime| {
                runtime.block_on(
                    GitCli::new(runner, policy(repository.root())).interpret_trailers(
                        InterpretTrailersRequest {
                            trailers: vec!["Reviewed-by: Larch <fixture@example.invalid>".into()],
                            in_place: Some(GitFilePath::new("missing-message").unwrap()),
                            add_if_different: false,
                            add_if_missing: false,
                            stdin: Vec::new(),
                        },
                        &NeverCancelled,
                    ),
                )
            },
        );
    }

    fn differential_checkout(runtime: &LarchRuntime, runner: &TokioProcessRunner) {
        assert_differential_case(
            "checkout ours preserves conflict stages",
            runtime,
            runner,
            GitFixture::Conflict,
            |_| {},
            ["checkout", "--ours", "--", "tracked.txt"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).checkout(
                    CheckoutRequest::Paths {
                        ours: true,
                        theirs: false,
                        paths: vec![GitPath::new("tracked.txt").unwrap()],
                    },
                    &NeverCancelled,
                ))
            },
        );
        assert_differential_case(
            "checkout ours fails outside a conflict",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            ["checkout", "--ours", "--", "tracked.txt"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).checkout(
                    CheckoutRequest::Paths {
                        ours: true,
                        theirs: false,
                        paths: vec![GitPath::new("tracked.txt").unwrap()],
                    },
                    &NeverCancelled,
                ))
            },
        );
        assert_differential_case(
            "checkout succeeds",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            ["checkout", "topic"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).checkout(
                    CheckoutRequest::Branch {
                        create: false,
                        force: false,
                        no_track: false,
                        name: GitRef::new("topic").unwrap(),
                        start_point: None,
                    },
                    &NeverCancelled,
                ))
            },
        );
        assert_differential_case(
            "checkout creates an untracked branch",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            ["checkout", "--no-track", "-b", "new-topic", "origin/main"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).checkout(
                    CheckoutRequest::Branch {
                        create: true,
                        force: false,
                        no_track: true,
                        name: GitRef::new("new-topic").unwrap(),
                        start_point: Some(GitRef::new("origin/main").unwrap()),
                    },
                    &NeverCancelled,
                ))
            },
        );
        assert_differential_case(
            "checkout fails for a missing branch",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            ["checkout", "missing-branch"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).checkout(
                    CheckoutRequest::Branch {
                        create: false,
                        force: false,
                        no_track: false,
                        name: GitRef::new("missing-branch").unwrap(),
                        start_point: None,
                    },
                    &NeverCancelled,
                ))
            },
        );
    }

    fn differential_rebase_merge_pull_and_stash(
        runtime: &LarchRuntime,
        runner: &TokioProcessRunner,
    ) {
        assert_differential_case(
            "rebase abort restores pre-rebase state",
            runtime,
            runner,
            GitFixture::Refs,
            setup_rebase_conflict,
            ["rebase", "--abort"],
            |repository, runner, runtime| {
                runtime.block_on(
                    GitCli::new(runner, policy(repository.root()))
                        .rebase(RebaseRequest::Abort, &NeverCancelled),
                )
            },
        );
        assert_semantic_differential_case(
            "rebase skip advances past the conflicted commit",
            runtime,
            runner,
            GitFixture::Refs,
            setup_rebase_conflict,
            ["rebase", "--skip"],
            |repository, runner, runtime| {
                runtime.block_on(
                    GitCli::new(runner, policy(repository.root()))
                        .rebase(RebaseRequest::Skip, &NeverCancelled),
                )
            },
        );
        assert_differential_case(
            "rebase skip fails without active sequencer state",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            ["rebase", "--skip"],
            |repository, runner, runtime| {
                runtime.block_on(
                    GitCli::new(runner, policy(repository.root()))
                        .rebase(RebaseRequest::Skip, &NeverCancelled),
                )
            },
        );
        assert_status_differential_case(
            "stash succeeds",
            runtime,
            runner,
            GitFixture::Changes,
            |_| {},
            ["stash", "push", "-m", "fixture stash"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).stash(
                    StashRequest::Push {
                        message: Some("fixture stash".into()),
                    },
                    &NeverCancelled,
                ))
            },
        );
        assert_differential_case(
            "merge fails for a missing branch",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            ["merge", "--no-edit", "missing-branch"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).merge(
                    MergeRequest::Commit {
                        theirs: GitRef::new("missing-branch").unwrap(),
                        no_edit: true,
                    },
                    &NeverCancelled,
                ))
            },
        );
    }

    fn setup_rebase_conflict(repository: &GitRepository) {
        let main = repository
            .git(["rev-parse", "main"])
            .expect("resolve main fixture ref");
        assert!(main.success());
        let topic = repository
            .git(["checkout", "--quiet", "topic"])
            .expect("checkout topic fixture branch");
        assert!(topic.success());
        repository
            .write("tracked.txt", b"topic\n")
            .expect("write topic change");
        let topic_commit = repository
            .git(["commit", "--quiet", "-am", "topic change"])
            .expect("commit topic change");
        assert!(topic_commit.success());
        let main_checkout = repository
            .git(["checkout", "--quiet", "main"])
            .expect("checkout main fixture branch");
        assert!(main_checkout.success());
        repository
            .write("tracked.txt", b"main\n")
            .expect("write main change");
        let main_commit = repository
            .git(["commit", "--quiet", "-am", "main change"])
            .expect("commit main change");
        assert!(main_commit.success());
        let topic_checkout = repository
            .git(["checkout", "--quiet", "topic"])
            .expect("restore topic fixture branch");
        assert!(topic_checkout.success());
        let rebase = repository
            .git(["rebase", "main"])
            .expect("start conflicting rebase");
        assert!(!rebase.success(), "fixture rebase must conflict");
    }

    fn differential_fetch_push_and_ls_remote(runtime: &LarchRuntime, runner: &TokioProcessRunner) {
        assert_differential_case(
            "ls-remote succeeds",
            runtime,
            runner,
            GitFixture::Refs,
            |repository| {
                repository
                    .git(["remote", "add", "origin", "."])
                    .expect("configure fixture remote");
            },
            ["ls-remote", "origin", "HEAD"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).ls_remote(
                    LsRemoteRequest {
                        remote: GitRemote::new("origin").unwrap(),
                        patterns: vec![GitRef::new("HEAD").unwrap()],
                        heads: false,
                        exit_code: false,
                    },
                    &NeverCancelled,
                ))
            },
        );
        assert_differential_case(
            "fetch fails for an unknown remote",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            ["fetch", "missing"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).fetch(
                    FetchRequest {
                        remote: GitRemote::new("missing").unwrap(),
                        refspec: None,
                        quiet: false,
                        no_tags: false,
                    },
                    &NeverCancelled,
                ))
            },
        );
    }

    fn differential_tag(runtime: &LarchRuntime, runner: &TokioProcessRunner) {
        assert_differential_case(
            "tag create succeeds",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            ["tag", "fixture-v2"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).tag_mutation(
                    TagMutationRequest::Create {
                        force: false,
                        name: GitRef::new("fixture-v2").unwrap(),
                        target: None,
                        message: None,
                    },
                    &NeverCancelled,
                ))
            },
        );
        assert_differential_case(
            "tag delete fails for a missing tag",
            runtime,
            runner,
            GitFixture::Refs,
            |_| {},
            ["tag", "--delete", "missing-tag"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).tag_mutation(
                    TagMutationRequest::Delete {
                        name: GitRef::new("missing-tag").unwrap(),
                    },
                    &NeverCancelled,
                ))
            },
        );
    }

    fn differential_submodule(runtime: &LarchRuntime, runner: &TokioProcessRunner) {
        assert_status_differential_case(
            "submodule update succeeds",
            runtime,
            runner,
            GitFixture::Submodule,
            |_| {},
            ["submodule", "update", "--init", "--recursive"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).submodule(
                    SubmoduleRequest::Update {
                        init: true,
                        recursive: true,
                    },
                    &NeverCancelled,
                ))
            },
        );
        assert_status_differential_case(
            "submodule foreach propagates command failure",
            runtime,
            runner,
            GitFixture::Submodule,
            |_| {},
            ["submodule", "foreach", "false"],
            |repository, runner, runtime| {
                runtime.block_on(GitCli::new(runner, policy(repository.root())).submodule(
                    SubmoduleRequest::Foreach {
                        recursive: false,
                        command: vec![GitToken::new("false").unwrap()],
                    },
                    &NeverCancelled,
                ))
            },
        );
    }

    fn assert_differential_case<Setup, Run>(
        name: &str,
        runtime: &LarchRuntime,
        runner: &TokioProcessRunner,
        fixture: GitFixture,
        setup: Setup,
        oracle_arguments: impl IntoIterator<Item = &'static str>,
        run_adapter: Run,
    ) where
        Setup: Fn(&GitRepository),
        Run: Fn(
            &GitRepository,
            &TokioProcessRunner,
            &LarchRuntime,
        ) -> Result<GitCliResult, GitCliError>,
    {
        assert_differential_case_inner(
            name,
            (runtime, runner),
            fixture,
            setup,
            oracle_arguments,
            run_adapter,
            DifferentialComparison::Exact,
        );
    }

    fn assert_status_differential_case<Setup, Run>(
        name: &str,
        runtime: &LarchRuntime,
        runner: &TokioProcessRunner,
        fixture: GitFixture,
        setup: Setup,
        oracle_arguments: impl IntoIterator<Item = &'static str>,
        run_adapter: Run,
    ) where
        Setup: Fn(&GitRepository),
        Run: Fn(
            &GitRepository,
            &TokioProcessRunner,
            &LarchRuntime,
        ) -> Result<GitCliResult, GitCliError>,
    {
        // Independently initialized fixtures produce time-dependent commit IDs.
        assert_differential_case_inner(
            name,
            (runtime, runner),
            fixture,
            setup,
            oracle_arguments,
            run_adapter,
            DifferentialComparison::StatusOnly,
        );
    }

    fn assert_semantic_differential_case<Setup, Run>(
        name: &str,
        runtime: &LarchRuntime,
        runner: &TokioProcessRunner,
        fixture: GitFixture,
        setup: Setup,
        oracle_arguments: impl IntoIterator<Item = &'static str>,
        run_adapter: Run,
    ) where
        Setup: Fn(&GitRepository),
        Run: Fn(
            &GitRepository,
            &TokioProcessRunner,
            &LarchRuntime,
        ) -> Result<GitCliResult, GitCliError>,
    {
        // Git renders progress according to the inherited terminal environment.
        assert_differential_case_inner(
            name,
            (runtime, runner),
            fixture,
            setup,
            oracle_arguments,
            run_adapter,
            DifferentialComparison::Semantic,
        );
    }

    fn assert_differential_case_inner<Setup, Run>(
        name: &str,
        context: (&LarchRuntime, &TokioProcessRunner),
        fixture: GitFixture,
        setup: Setup,
        oracle_arguments: impl IntoIterator<Item = &'static str>,
        run_adapter: Run,
        comparison: DifferentialComparison,
    ) where
        Setup: Fn(&GitRepository),
        Run: Fn(
            &GitRepository,
            &TokioProcessRunner,
            &LarchRuntime,
        ) -> Result<GitCliResult, GitCliError>,
    {
        let (runtime, runner) = context;
        let oracle = GitRepository::builder(fixture)
            .build()
            .expect("oracle fixture");
        let adapter = GitRepository::builder(fixture)
            .build()
            .expect("adapter fixture");
        setup(&oracle);
        setup(&adapter);

        let oracle_output = oracle.git(oracle_arguments).expect("run installed Git");
        let adapter_result = run_adapter(&adapter, runner, runtime);
        let adapter_output = match adapter_result {
            Ok(result) => {
                assert!(
                    oracle_output.success(),
                    "{name}: adapter succeeded but oracle failed"
                );
                result.output().clone()
            }
            Err(GitCliError::Failed(result)) => {
                assert!(
                    !oracle_output.success(),
                    "{name}: adapter failed but oracle succeeded"
                );
                result.output().clone()
            }
            Err(error) => panic!("{name}: adapter did not execute Git: {error}"),
        };
        assert_eq!(
            oracle_output.code,
            adapter_output.status().code(),
            "{name}: exit code"
        );
        if matches!(comparison, DifferentialComparison::Exact) {
            assert_eq!(
                oracle_output.stdout,
                adapter_output.stdout(),
                "{name}: stdout"
            );
            assert_eq!(
                oracle_output.stderr,
                adapter_output.stderr(),
                "{name}: stderr"
            );
        }

        if matches!(
            comparison,
            DifferentialComparison::Exact | DifferentialComparison::Semantic
        ) {
            let oracle_snapshot = SemanticSnapshot::capture(
                &oracle,
                ExecutionSnapshot::from_git(&oracle, &oracle_output),
            )
            .expect("capture oracle semantics");
            let adapter_snapshot =
                SemanticSnapshot::capture(&adapter, ExecutionSnapshot::success())
                    .expect("capture adapter semantics");
            assert_semantic_state_eq(name, &oracle_snapshot, &adapter_snapshot);
        }
    }

    fn assert_semantic_state_eq(name: &str, oracle: &SemanticSnapshot, adapter: &SemanticSnapshot) {
        assert_eq!(oracle.schema, adapter.schema, "{name}: schema");
        assert_eq!(
            oracle.head_symbolic, adapter.head_symbolic,
            "{name}: symbolic HEAD"
        );
        assert_eq!(
            oracle.head_object, adapter.head_object,
            "{name}: HEAD object"
        );
        assert_eq!(oracle.objects, adapter.objects, "{name}: object database");
        assert_eq!(oracle.refs, adapter.refs, "{name}: refs");
        assert_eq!(oracle.index, adapter.index, "{name}: index");
        assert_eq!(
            oracle.index_flags, adapter.index_flags,
            "{name}: index flags"
        );
        assert_eq!(
            oracle.untracked, adapter.untracked,
            "{name}: untracked files"
        );
        assert_eq!(oracle.ignored, adapter.ignored, "{name}: ignored files");
        assert_eq!(
            oracle.linked_worktrees, adapter.linked_worktrees,
            "{name}: worktrees"
        );
        assert_eq!(oracle.config, adapter.config, "{name}: config");
        assert_eq!(
            oracle.worktree, adapter.worktree,
            "{name}: worktree contents"
        );
        assert_eq!(
            oracle.operation_state, adapter.operation_state,
            "{name}: operation state"
        );
        assert_eq!(
            oracle.transcripts, adapter.transcripts,
            "{name}: fixture transcripts"
        );
        assert_eq!(oracle.fsck, adapter.fsck, "{name}: fsck");
        assert_eq!(
            oracle.entries_truncated, adapter.entries_truncated,
            "{name}: snapshot bounds"
        );
    }
}
