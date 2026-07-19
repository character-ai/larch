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
pub use repository::GixRepository;
pub use validate::{GitConfigKey, GitPath, GitRef, GitRefspec, GitRemote, GitToken, GitUrl};

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
                staged: true,
                paths: vec![GitPath::new("tracked.txt").unwrap()],
            },
            &["restore", "--staged", "--", "tracked.txt"],
        );
        check(
            &CheckoutRequest::Branch {
                create: true,
                force: false,
                name: GitRef::new("topic").unwrap(),
                start_point: Some(GitRef::new("HEAD").unwrap()),
            },
            &["checkout", "-b", "topic", "HEAD"],
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
                patch: GitPath::new("change.patch").unwrap(),
                index: true,
                check: false,
            },
            &["apply", "--index", "change.patch"],
        );
        check(
            &CommitRequest {
                message: Some(CommitMessage::Literal("msg".into())),
                amend: false,
                no_edit: false,
                allow_empty: true,
                paths: Vec::new(),
            },
            &["commit", "--allow-empty", "-m", "msg"],
        );
        check(
            &InterpretTrailersRequest {
                trailers: vec!["Signed-off-by: A <a@b>".into()],
                in_place: None,
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
                path: GitPath::new("linked-worktree").unwrap(),
                start_point: None,
            },
            &["worktree", "add", "-b", "linked", "linked-worktree"],
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
            },
            &["pull", "origin", "main"],
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
            },
            &["fetch", "--quiet", "origin", "main"],
        );
        check(
            &PushRequest {
                remote: GitRemote::new("origin").unwrap(),
                refspec: GitRefspec::new("HEAD:main").unwrap(),
                force_with_lease: Some(ForceWithLease::Enabled),
            },
            &["push", "--force-with-lease", "origin", "HEAD:main"],
        );
        check(
            &LsRemoteRequest {
                remote: GitRemote::new("origin").unwrap(),
                patterns: vec![GitRef::new("HEAD").unwrap()],
            },
            &["ls-remote", "origin", "HEAD"],
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
                paths: vec![GitPath::new("a").unwrap()],
            }
            .arguments()
            .is_err()
        );
        assert!(
            ExactDiffRequest {
                cached: false,
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
                name: GitRef::new("topic").unwrap(),
                start_point: Some(GitRef::new("HEAD").unwrap()),
            }
            .arguments()
            .is_err()
        );
        assert!(
            InterpretTrailersRequest {
                trailers: vec!["Signed-off-by: A <a@b>".into()],
                in_place: Some(GitPath::new("MSG").unwrap()),
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
                pathspec_from_file: Some(GitPath::new("specs.txt").unwrap()),
                paths: Vec::new(),
            },
            &["add", "--force", "--pathspec-from-file=specs.txt"],
        );
        assert_argv(
            &AddRequest {
                all: true,
                force: false,
                pathspec_from_file: None,
                paths: Vec::new(),
            },
            &["add", "--all"],
        );
        assert!(
            AddRequest {
                all: false,
                force: false,
                pathspec_from_file: Some(GitPath::new("specs.txt").unwrap()),
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
                message: Some(CommitMessage::File(GitPath::new("MSG").unwrap())),
                amend: true,
                no_edit: false,
                allow_empty: false,
                paths: vec![GitPath::new("tracked.txt").unwrap()],
            },
            &["commit", "--amend", "--file", "MSG", "--", "tracked.txt"],
        );
        assert_argv(
            &CommitRequest {
                message: None,
                amend: true,
                no_edit: true,
                allow_empty: false,
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
                paths: Vec::new(),
            }
            .arguments()
            .is_err()
        );
        assert!(
            InterpretTrailersRequest {
                trailers: Vec::new(),
                in_place: None,
                stdin: Vec::new(),
            }
            .arguments()
            .is_err()
        );
        assert_argv(
            &InterpretTrailersRequest {
                trailers: vec!["Reviewed-by: A <a@b>".into()],
                in_place: Some(GitPath::new("MSG").unwrap()),
                stdin: Vec::new(),
            },
            &[
                "interpret-trailers",
                "--trailer",
                "Reviewed-by: A <a@b>",
                "--in-place",
                "MSG",
            ],
        );
        assert!(
            InterpretTrailersRequest {
                trailers: vec!["Reviewed-by: A <a@b>".into()],
                in_place: Some(GitPath::new("MSG").unwrap()),
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
                path: GitPath::new("wt").unwrap(),
                start_point: Some(GitRef::new("HEAD").unwrap()),
            },
            &["worktree", "add", "wt", "HEAD"],
        );
        assert_argv(
            &WorktreeRequest::Remove {
                force: true,
                path: GitPath::new("wt").unwrap(),
            },
            &["worktree", "remove", "--force", "wt"],
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
            &PushRequest {
                remote: GitRemote::new("origin").unwrap(),
                refspec: GitRefspec::new("HEAD:main").unwrap(),
                force_with_lease: Some(ForceWithLease::Expecting(GitRef::new("abc").unwrap())),
            },
            &["push", "--force-with-lease=abc", "origin", "HEAD:main"],
        );
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
    fn differential_success_and_failure_families() {
        let runtime = LarchRuntime::current_thread().expect("runtime");
        let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));

        let repository = GitRepository::builder(GitFixture::Changes)
            .build()
            .expect("fixture");
        let git = GitCli::new(&runner, policy(repository.root()));
        let oracle_version = repository.git(["--version"]).expect("oracle version");
        let adapter_version = runtime
            .block_on(git.version(&NeverCancelled))
            .expect("adapter version");
        assert_eq!(oracle_version.stdout, adapter_version.output().stdout());

        let oracle = GitRepository::builder(GitFixture::Changes)
            .build()
            .expect("oracle");
        let adapter_repo = GitRepository::builder(GitFixture::Changes)
            .build()
            .expect("adapter");
        oracle.write("extra.txt", b"extra\n").unwrap();
        adapter_repo.write("extra.txt", b"extra\n").unwrap();
        let oracle_add = oracle.git(["add", "--", "extra.txt"]).unwrap();
        assert!(oracle_add.success());
        let oracle_snapshot =
            SemanticSnapshot::capture(&oracle, ExecutionSnapshot::from_git(&oracle, &oracle_add))
                .unwrap();
        let adapter = GitCli::new(&runner, policy(adapter_repo.root()));
        runtime
            .block_on(adapter.add(
                AddRequest {
                    all: false,
                    force: false,
                    pathspec_from_file: None,
                    paths: vec![GitPath::new("extra.txt").unwrap()],
                },
                &NeverCancelled,
            ))
            .unwrap();
        let adapter_snapshot =
            SemanticSnapshot::capture(&adapter_repo, ExecutionSnapshot::success()).unwrap();
        assert_eq!(oracle_snapshot.index, adapter_snapshot.index);

        let branch_repo = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("branch");
        runtime
            .block_on(
                GitCli::new(&runner, policy(branch_repo.root())).branch_mutation(
                    BranchMutationRequest::Create {
                        force: false,
                        name: GitRef::new("adapter-topic").unwrap(),
                        start_point: None,
                    },
                    &NeverCancelled,
                ),
            )
            .unwrap();
        let branch_snapshot =
            SemanticSnapshot::capture(&branch_repo, ExecutionSnapshot::success()).unwrap();
        assert!(
            branch_snapshot
                .refs
                .stdout
                .bytes
                .windows(b"refs/heads/adapter-topic".len())
                .any(|window| window == b"refs/heads/adapter-topic")
        );

        let failure_repo = GitRepository::builder(GitFixture::Unborn)
            .build()
            .expect("unborn");
        assert!(matches!(
            runtime.block_on(GitCli::new(&runner, policy(failure_repo.root())).reset(
                ResetRequest {
                    mode: ResetMode::Hard,
                    target: GitRef::new("missing-ref").unwrap(),
                    paths: Vec::new(),
                },
                &NeverCancelled,
            )),
            Err(GitCliError::Failed(_))
        ));
    }
}
