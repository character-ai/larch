//! Typed, injectable external-process execution port.

use crate::{SafeText, env};
use std::{
    error::Error,
    ffi::{OsStr, OsString},
    fmt,
    future::Future,
    num::NonZeroUsize,
    path::{Path, PathBuf},
    pin::Pin,
    time::Duration,
};

/// A true external vendor product that larch may invoke.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VendorProgram {
    /// Anthropic's Claude Code executable.
    Claude,
    /// `OpenAI`'s Codex executable.
    Codex,
    /// Anysphere's Cursor agent executable.
    Cursor,
}

/// A checksum-pinned security scanner distributed outside the Rust workspace.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ScannerProgram {
    executable: PathBuf,
}

/// Closed host-utility allowlist for compatibility probes unavailable in-process.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum HostUtilityProgram {
    /// Inspect processes holding one validated file path open.
    Lsof,
    /// Bounded process-table probes for identity capture and cleanup.
    Ps,
    /// Bounded child and process-group enumeration.
    Pgrep,
    /// Read one named macOS keychain item for a vendor credential preflight.
    Security,
}

/// Approved GitHub CLI operations used to acquire the active `gh` credential.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubCliOperation {
    /// Read the token held by the authenticated GitHub CLI session.
    AuthToken,
}

impl GitHubCliOperation {
    /// Return the fixed arguments for this operation.
    #[must_use]
    pub const fn arguments(self) -> [&'static str; 4] {
        match self {
            Self::AuthToken => ["auth", "token", "--hostname", "github.com"],
        }
    }

    /// Return the stable operation label.
    #[must_use]
    pub const fn operation(self) -> &'static str {
        match self {
            Self::AuthToken => "github.auth-token",
        }
    }

    /// Return the allowlist rationale.
    #[must_use]
    pub const fn reason(self) -> &'static str {
        "GitHub credential acquisition through the operator-authenticated gh session"
    }
}

impl HostUtilityProgram {
    /// Return the fixed executable name.
    #[must_use]
    pub const fn executable(self) -> &'static str {
        match self {
            Self::Lsof => "lsof",
            Self::Ps => "ps",
            Self::Pgrep => "pgrep",
            Self::Security => "security",
        }
    }

    /// Return the stable operation label.
    #[must_use]
    pub const fn operation(self) -> &'static str {
        match self {
            Self::Lsof => "host.open-file-probe",
            Self::Ps => "host.process-identity-probe",
            Self::Pgrep => "host.process-group-probe",
            Self::Security => "host.keychain-credential-read",
        }
    }

    /// Return the allowlist rationale.
    #[must_use]
    pub const fn reason(self) -> &'static str {
        match self {
            Self::Lsof => {
                "bounded open-file holder probe required for safe stale Git index-lock recovery"
            }
            Self::Ps => {
                "bounded process start-time and command probes required for validated process termination"
            }
            Self::Pgrep => {
                "bounded descendant and process-group enumeration required for validated process termination"
            }
            Self::Security => {
                "macOS keychain read required to prove a Cursor service token is present and readable before launch"
            }
        }
    }
}

impl VendorProgram {
    /// Return the fixed executable name.
    #[must_use]
    pub const fn executable(self) -> &'static str {
        match self {
            Self::Claude => "claude",
            Self::Codex => "codex",
            Self::Cursor => "cursor",
        }
    }

    /// Return the allowlist rationale.
    #[must_use]
    pub const fn reason(self) -> &'static str {
        "vendor agent product whose behavior is available only through its executable"
    }
}

impl ScannerProgram {
    /// Bind the Gitleaks scanner to an already-verified executable path.
    #[must_use]
    pub fn gitleaks(executable: impl Into<PathBuf>) -> Self {
        Self {
            executable: executable.into(),
        }
    }

    /// Return the verified scanner executable path.
    #[must_use]
    pub fn executable(&self) -> &OsStr {
        self.executable.as_os_str()
    }

    /// Return the allowlist rationale.
    #[must_use]
    pub const fn reason(&self) -> &'static str {
        "checksum-pinned external secret scanner required by the repository security policy"
    }
}

/// Approved installed-Git compatibility operations from issue #7671.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitCliOperation {
    ExactDiff,
    ConfigMutation,
    RemoteMutation,
    Add,
    Rm,
    Reset,
    Restore,
    Checkout,
    Clean,
    Apply,
    Commit,
    InterpretTrailers,
    BranchMutation,
    Worktree,
    Init,
    Clone,
    SparseCheckout,
    Rebase,
    Merge,
    Pull,
    Stash,
    Fetch,
    Push,
    LsRemote,
    TagMutation,
    SubmoduleUpdate,
    Version,
}

impl GitCliOperation {
    /// Return the fixed first argument for this compatibility method.
    #[must_use]
    pub const fn subcommand(self) -> &'static str {
        match self {
            Self::ExactDiff => "diff",
            Self::ConfigMutation => "config",
            Self::RemoteMutation => "remote",
            Self::Add => "add",
            Self::Rm => "rm",
            Self::Reset => "reset",
            Self::Restore => "restore",
            Self::Checkout => "checkout",
            Self::Clean => "clean",
            Self::Apply => "apply",
            Self::Commit => "commit",
            Self::InterpretTrailers => "interpret-trailers",
            Self::BranchMutation => "branch",
            Self::Worktree => "worktree",
            Self::Init => "init",
            Self::Clone => "clone",
            Self::SparseCheckout => "sparse-checkout",
            Self::Rebase => "rebase",
            Self::Merge => "merge",
            Self::Pull => "pull",
            Self::Stash => "stash",
            Self::Fetch => "fetch",
            Self::Push => "push",
            Self::LsRemote => "ls-remote",
            Self::TagMutation => "tag",
            Self::SubmoduleUpdate => "submodule",
            Self::Version => "--version",
        }
    }

    /// Return the allowlist rationale.
    #[must_use]
    pub const fn reason(self) -> &'static str {
        "installed Git compatibility exception approved by the canonical result in issue #7671"
    }
}

/// Closed executable allowlist. There is no arbitrary executable variant.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ExternalProgram {
    Vendor(VendorProgram),
    Scanner(ScannerProgram),
    Git(GitCliOperation),
    GitHub(GitHubCliOperation),
    HostUtility(HostUtilityProgram),
    /// A fixed larch program derived from a validated plugin root.
    Larch(LarchProgram),
    /// A migration-era larch Python verb derived from a validated plugin root.
    PythonVerb(PythonVerbProgram),
}

/// The still-Python `python3 <root>/python/cli.py` entry a Rust owner delegates to.
///
/// Migration leaves land one command at a time, so a Rust-owned verb can still
/// need a sibling verb that Python owns. This selects only the repository's own
/// dispatcher from a validated plugin root; it carries no arbitrary-executable
/// escape hatch and retires with the last Python-owned verb it names.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PythonVerbProgram {
    dispatcher: PathBuf,
}

impl PythonVerbProgram {
    /// Select the larch Python dispatcher from a plugin root.
    ///
    /// # Errors
    /// Rejects a non-absolute or lexically unsafe root.
    pub fn new(root: &Path) -> Result<Self, ProcessRequestError> {
        if !root.is_absolute()
            || root.components().any(|part| {
                matches!(
                    part,
                    std::path::Component::CurDir | std::path::Component::ParentDir
                )
            })
        {
            return Err(ProcessRequestError {
                kind: ProcessRequestErrorKind::UnsafeLarchProgramRoot,
            });
        }
        Ok(Self {
            dispatcher: root.join("python/cli.py"),
        })
    }

    fn dispatcher(&self) -> &OsStr {
        self.dispatcher.as_os_str()
    }
}

/// Fixed larch executable selected from a canonical plugin root.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LarchProgram {
    path: PathBuf,
    kind: LarchProgramKind,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum LarchProgramKind {
    Bootstrap,
    Binary,
}

impl LarchProgram {
    /// Select the bounded no-binary bootstrap exception from a plugin root.
    ///
    /// # Errors
    /// Rejects a non-absolute or lexically unsafe root.
    pub fn bootstrap(root: &Path) -> Result<Self, ProcessRequestError> {
        Self::from_root(root, LarchProgramKind::Bootstrap)
    }

    /// Select the release-matched larch executable from a plugin root.
    ///
    /// # Errors
    /// Rejects a non-absolute or lexically unsafe root.
    pub fn binary(root: &Path) -> Result<Self, ProcessRequestError> {
        Self::from_root(root, LarchProgramKind::Binary)
    }

    fn from_root(root: &Path, kind: LarchProgramKind) -> Result<Self, ProcessRequestError> {
        if !root.is_absolute()
            || root.components().any(|part| {
                matches!(
                    part,
                    std::path::Component::CurDir | std::path::Component::ParentDir
                )
            })
        {
            return Err(ProcessRequestError {
                kind: ProcessRequestErrorKind::UnsafeLarchProgramRoot,
            });
        }
        let path = match kind {
            LarchProgramKind::Bootstrap => root.join("scripts/larch.sh"),
            LarchProgramKind::Binary => root.join("bin/larch"),
        };
        Ok(Self { path, kind })
    }

    fn executable(&self) -> &OsStr {
        self.path.as_os_str()
    }

    const fn operation(&self) -> &'static str {
        match self.kind {
            LarchProgramKind::Bootstrap => "larch.bootstrap",
            LarchProgramKind::Binary => "larch.self-check",
        }
    }

    const fn reason(&self) -> &'static str {
        match self.kind {
            LarchProgramKind::Bootstrap => {
                "bounded no-binary bootstrap exception approved by issue #7670"
            }
            LarchProgramKind::Binary => "release-matched larch executable self-check",
        }
    }
}

impl ExternalProgram {
    /// Return the executable path selected by the closed allowlist.
    #[must_use]
    pub fn executable(&self) -> &OsStr {
        match self {
            Self::Vendor(program) => OsStr::new(program.executable()),
            Self::Scanner(program) => program.executable(),
            Self::Git(_) => OsStr::new("git"),
            Self::GitHub(_) => OsStr::new("gh"),
            Self::HostUtility(program) => OsStr::new(program.executable()),
            Self::Larch(program) => program.executable(),
            Self::PythonVerb(_) => OsStr::new("python3"),
        }
    }

    /// Return the stable operation label used for structured observations.
    #[must_use]
    pub const fn operation(&self) -> &'static str {
        match self {
            Self::Vendor(VendorProgram::Claude) => "vendor.claude",
            Self::Vendor(VendorProgram::Codex) => "vendor.codex",
            Self::Vendor(VendorProgram::Cursor) => "vendor.cursor",
            Self::Scanner(_) => "scanner.gitleaks",
            Self::Git(operation) => operation.subcommand(),
            Self::GitHub(operation) => operation.operation(),
            Self::HostUtility(program) => program.operation(),
            Self::Larch(program) => program.operation(),
            Self::PythonVerb(_) => "larch.python-verb",
        }
    }

    /// Return the reason this program is allowed.
    #[must_use]
    pub const fn reason(&self) -> &'static str {
        match self {
            Self::Vendor(program) => program.reason(),
            Self::Scanner(program) => program.reason(),
            Self::Git(operation) => operation.reason(),
            Self::GitHub(operation) => operation.reason(),
            Self::HostUtility(program) => program.reason(),
            Self::Larch(program) => program.reason(),
            Self::PythonVerb(_) => {
                "migration-era delegation to a larch verb Python still owns, per issue #7677"
            }
        }
    }

    /// Append the fixed operation prefix before caller-owned arguments.
    pub fn append_fixed_arguments(&self, arguments: &mut Vec<OsString>) {
        match self {
            Self::Git(operation) => {
                arguments.insert(0, OsString::from(operation.subcommand()));
            }
            Self::GitHub(operation) => {
                arguments.splice(0..0, operation.arguments().into_iter().map(OsString::from));
            }
            Self::PythonVerb(program) => {
                arguments.insert(0, program.dispatcher().to_os_string());
            }
            Self::Vendor(_) | Self::Scanner(_) | Self::HostUtility(_) | Self::Larch(_) => {}
        }
    }
}

/// Environment keys that an owned child may inherit or override.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum ChildEnvironment {
    Path,
    Home,
    User,
    LogName,
    Shell,
    TempDir,
    Temp,
    Tmp,
    Lang,
    LcAll,
    LcCtype,
    Term,
    ColorTerm,
    NoColor,
    SshAuthSock,
    SshAgentPid,
    Display,
    GpgTty,
    GitTerminalPrompt,
    GitEditor,
    AnthropicApiKey,
    OpenAiApiKey,
    CursorApiKey,
    CursorConfigDir,
    CodexHome,
    NoOpenBrowser,
    ClaudePluginRoot,
    ClaudePluginData,
    GhConfigDir,
    XdgConfigHome,
}

impl ChildEnvironment {
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Path => "PATH",
            Self::Home => "HOME",
            Self::User => "USER",
            Self::LogName => "LOGNAME",
            Self::Shell => "SHELL",
            Self::TempDir => "TMPDIR",
            Self::Temp => "TEMP",
            Self::Tmp => "TMP",
            Self::Lang => "LANG",
            Self::LcAll => "LC_ALL",
            Self::LcCtype => "LC_CTYPE",
            Self::Term => "TERM",
            Self::ColorTerm => "COLORTERM",
            Self::NoColor => "NO_COLOR",
            Self::SshAuthSock => "SSH_AUTH_SOCK",
            Self::SshAgentPid => "SSH_AGENT_PID",
            Self::Display => "DISPLAY",
            Self::GpgTty => "GPG_TTY",
            Self::GitTerminalPrompt => "GIT_TERMINAL_PROMPT",
            Self::GitEditor => "GIT_EDITOR",
            Self::AnthropicApiKey => env::ANTHROPIC_API_KEY,
            Self::OpenAiApiKey => env::OPENAI_API_KEY,
            Self::CursorApiKey => env::CURSOR_API_KEY,
            Self::CursorConfigDir => env::CURSOR_CONFIG_DIR,
            Self::CodexHome => env::CODEX_HOME,
            Self::NoOpenBrowser => env::NO_OPEN_BROWSER,
            Self::ClaudePluginRoot => env::CLAUDE_PLUGIN_ROOT,
            Self::ClaudePluginData => env::CLAUDE_PLUGIN_DATA,
            Self::GhConfigDir => env::GH_CONFIG_DIR,
            Self::XdgConfigHome => env::XDG_CONFIG_HOME,
        }
    }

    /// Iterate over the complete production inheritance allowlist.
    pub fn production() -> impl Iterator<Item = Self> {
        [
            Self::Path,
            Self::Home,
            Self::User,
            Self::LogName,
            Self::Shell,
            Self::TempDir,
            Self::Temp,
            Self::Tmp,
            Self::Lang,
            Self::LcAll,
            Self::LcCtype,
            Self::Term,
            Self::ColorTerm,
            Self::NoColor,
            Self::SshAuthSock,
            Self::SshAgentPid,
            Self::Display,
            Self::GpgTty,
            Self::GitTerminalPrompt,
        ]
        .into_iter()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProcessRequestErrorKind {
    RelativeWorkingDirectory,
    ZeroTimeout,
    ZeroShutdownGrace,
    UnsafeLarchProgramRoot,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProcessRequestError {
    kind: ProcessRequestErrorKind,
}

impl ProcessRequestError {
    #[must_use]
    pub const fn kind(self) -> ProcessRequestErrorKind {
        self.kind
    }
}

impl fmt::Display for ProcessRequestError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self.kind {
            ProcessRequestErrorKind::RelativeWorkingDirectory => {
                "child working directory must be absolute"
            }
            ProcessRequestErrorKind::ZeroTimeout => "child timeout must be non-zero",
            ProcessRequestErrorKind::ZeroShutdownGrace => {
                "child shutdown grace period must be non-zero"
            }
            ProcessRequestErrorKind::UnsafeLarchProgramRoot => {
                "larch program root must be absolute and lexically safe"
            }
        })
    }
}

impl Error for ProcessRequestError {}

/// Complete input for one owned child process.
#[derive(Clone, Eq, PartialEq)]
pub struct ProcessRequest {
    program: ExternalProgram,
    arguments: Vec<OsString>,
    working_directory: PathBuf,
    environment: Vec<(ChildEnvironment, OsString)>,
    stdin: Vec<u8>,
    timeout: Duration,
    shutdown_grace: Duration,
    output_limit: NonZeroUsize,
}

impl fmt::Debug for ProcessRequest {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("ProcessRequest")
            .field("program", &self.program)
            .field("argument_count", &self.arguments.len())
            .field(
                "environment_keys",
                &self
                    .environment
                    .iter()
                    .map(|(key, _value)| key.name())
                    .collect::<Vec<_>>(),
            )
            .field("stdin_bytes", &self.stdin.len())
            .field("timeout", &self.timeout)
            .field("shutdown_grace", &self.shutdown_grace)
            .field("output_limit", &self.output_limit)
            .finish_non_exhaustive()
    }
}

impl ProcessRequest {
    /// Build a request whose executable and Git subcommand come from closed enums.
    /// # Errors
    /// Rejects relative working directories and zero timeout or shutdown durations.
    pub fn new<I, A>(
        program: ExternalProgram,
        arguments: I,
        working_directory: PathBuf,
        timeout: Duration,
        shutdown_grace: Duration,
        output_limit: NonZeroUsize,
    ) -> Result<Self, ProcessRequestError>
    where
        I: IntoIterator<Item = A>,
        A: Into<OsString>,
    {
        if !working_directory.is_absolute() {
            return Err(ProcessRequestError {
                kind: ProcessRequestErrorKind::RelativeWorkingDirectory,
            });
        }
        if timeout.is_zero() {
            return Err(ProcessRequestError {
                kind: ProcessRequestErrorKind::ZeroTimeout,
            });
        }
        if shutdown_grace.is_zero() {
            return Err(ProcessRequestError {
                kind: ProcessRequestErrorKind::ZeroShutdownGrace,
            });
        }
        Ok(Self {
            program,
            arguments: arguments.into_iter().map(Into::into).collect(),
            working_directory,
            environment: Vec::new(),
            stdin: Vec::new(),
            timeout,
            shutdown_grace,
            output_limit,
        })
    }

    /// Add one typed environment override.
    #[must_use]
    pub fn with_environment(mut self, key: ChildEnvironment, value: impl Into<OsString>) -> Self {
        self.environment.retain(|(existing, _)| *existing != key);
        self.environment.push((key, value.into()));
        self
    }

    /// Supply bytes for the child's standard input.
    #[must_use]
    pub fn with_stdin(mut self, stdin: impl Into<Vec<u8>>) -> Self {
        self.stdin = stdin.into();
        self
    }

    #[must_use]
    pub const fn program(&self) -> &ExternalProgram {
        &self.program
    }

    #[must_use]
    pub fn arguments(&self) -> &[OsString] {
        &self.arguments
    }

    #[must_use]
    pub fn working_directory(&self) -> &Path {
        &self.working_directory
    }

    #[must_use]
    pub fn environment(&self) -> &[(ChildEnvironment, OsString)] {
        &self.environment
    }

    #[must_use]
    pub fn stdin(&self) -> &[u8] {
        &self.stdin
    }

    #[must_use]
    pub const fn timeout(&self) -> Duration {
        self.timeout
    }

    #[must_use]
    pub const fn shutdown_grace(&self) -> Duration {
        self.shutdown_grace
    }

    #[must_use]
    pub const fn output_limit(&self) -> NonZeroUsize {
        self.output_limit
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProcessStatus {
    success: bool,
    code: Option<i32>,
}

impl ProcessStatus {
    #[must_use]
    pub const fn new(success: bool, code: Option<i32>) -> Self {
        Self { success, code }
    }

    #[must_use]
    pub const fn success(self) -> bool {
        self.success
    }

    #[must_use]
    pub const fn code(self) -> Option<i32> {
        self.code
    }
}

/// Captured child output. Raw bytes stay available for byte-oriented adapters.
#[derive(Clone, Eq, PartialEq)]
pub struct ProcessOutput {
    status: ProcessStatus,
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    stdout_truncated: bool,
    stderr_truncated: bool,
}

impl fmt::Debug for ProcessOutput {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("ProcessOutput")
            .field("status", &self.status)
            .field("stdout_bytes", &self.stdout.len())
            .field("stderr_bytes", &self.stderr.len())
            .field("stdout_truncated", &self.stdout_truncated)
            .field("stderr_truncated", &self.stderr_truncated)
            .finish()
    }
}

impl ProcessOutput {
    #[must_use]
    pub const fn new(
        status: ProcessStatus,
        stdout: Vec<u8>,
        stderr: Vec<u8>,
        stdout_truncated: bool,
        stderr_truncated: bool,
    ) -> Self {
        Self {
            status,
            stdout,
            stderr,
            stdout_truncated,
            stderr_truncated,
        }
    }

    #[must_use]
    pub const fn status(&self) -> ProcessStatus {
        self.status
    }
    #[must_use]
    pub fn stdout(&self) -> &[u8] {
        &self.stdout
    }
    #[must_use]
    pub fn stderr(&self) -> &[u8] {
        &self.stderr
    }
    #[must_use]
    pub const fn stdout_truncated(&self) -> bool {
        self.stdout_truncated
    }
    #[must_use]
    pub const fn stderr_truncated(&self) -> bool {
        self.stderr_truncated
    }

    /// Redact captured stdout before an observability or diagnostic write.
    #[must_use]
    pub fn safe_stdout(&self) -> SafeText {
        SafeText::from_untrusted(String::from_utf8_lossy(&self.stdout))
    }

    /// Redact captured stderr before an observability or diagnostic write.
    #[must_use]
    pub fn safe_stderr(&self) -> SafeText {
        SafeText::from_untrusted(String::from_utf8_lossy(&self.stderr))
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProcessErrorKind {
    Spawn,
    Input,
    Wait,
    Capture,
    Cancelled,
    TimedOut,
    Termination,
}

#[derive(Clone, Eq, PartialEq)]
pub struct ProcessError {
    kind: ProcessErrorKind,
    message: SafeText,
    output: Option<ProcessOutput>,
}

impl fmt::Debug for ProcessError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("ProcessError")
            .field("kind", &self.kind)
            .field("message", &self.message)
            .field("output", &self.output)
            .finish()
    }
}

impl ProcessError {
    #[must_use]
    pub fn new(
        kind: ProcessErrorKind,
        message: impl AsRef<str>,
        output: Option<ProcessOutput>,
    ) -> Self {
        Self {
            kind,
            message: SafeText::from_untrusted(message),
            output,
        }
    }

    #[must_use]
    pub const fn kind(&self) -> ProcessErrorKind {
        self.kind
    }
    #[must_use]
    pub fn message(&self) -> &str {
        self.message.as_str()
    }
    #[must_use]
    pub const fn output(&self) -> Option<&ProcessOutput> {
        self.output.as_ref()
    }
}

impl fmt::Display for ProcessError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.message.as_str())
    }
}

impl Error for ProcessError {}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProcessEventKind {
    Started,
    Exited,
    Cancelled,
    TimedOut,
    Failed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProcessEvent {
    kind: ProcessEventKind,
    operation: &'static str,
    exit_code: Option<i32>,
    stdout_bytes: usize,
    stderr_bytes: usize,
}

impl ProcessEvent {
    #[must_use]
    pub const fn new(
        kind: ProcessEventKind,
        operation: &'static str,
        exit_code: Option<i32>,
        stdout_bytes: usize,
        stderr_bytes: usize,
    ) -> Self {
        Self {
            kind,
            operation,
            exit_code,
            stdout_bytes,
            stderr_bytes,
        }
    }
    #[must_use]
    pub const fn kind(self) -> ProcessEventKind {
        self.kind
    }
    #[must_use]
    pub const fn operation(self) -> &'static str {
        self.operation
    }
    #[must_use]
    pub const fn exit_code(self) -> Option<i32> {
        self.exit_code
    }
    #[must_use]
    pub const fn stdout_bytes(self) -> usize {
        self.stdout_bytes
    }
    #[must_use]
    pub const fn stderr_bytes(self) -> usize {
        self.stderr_bytes
    }
}

/// Count-only structured process observation sink. It never receives argv or payload bytes.
pub trait ProcessObserver: Send + Sync {
    fn observe(&self, event: ProcessEvent);
}

/// Cooperative cancellation port used by process runners and fakes.
pub trait ProcessCancellation: Send + Sync {
    fn is_cancelled(&self) -> bool;
    fn cancelled(&self) -> Pin<Box<dyn Future<Output = ()> + Send + '_>>;
}

pub type ProcessFuture<'a> =
    Pin<Box<dyn Future<Output = Result<ProcessOutput, ProcessError>> + Send + 'a>>;

/// The only injectable interface through which product code executes a child.
pub trait ExternalProcessRunner: Send + Sync {
    fn run<'a>(
        &'a self,
        request: ProcessRequest,
        cancellation: &'a dyn ProcessCancellation,
    ) -> ProcessFuture<'a>;
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    struct NeverCancelled;
    impl ProcessCancellation for NeverCancelled {
        fn is_cancelled(&self) -> bool {
            false
        }
        fn cancelled(&self) -> Pin<Box<dyn Future<Output = ()> + Send + '_>> {
            Box::pin(std::future::pending())
        }
    }

    #[derive(Default)]
    struct FakeRunner {
        calls: Mutex<Vec<ProcessRequest>>,
    }
    impl ExternalProcessRunner for FakeRunner {
        fn run<'a>(
            &'a self,
            request: ProcessRequest,
            _cancellation: &'a dyn ProcessCancellation,
        ) -> ProcessFuture<'a> {
            self.calls.lock().expect("fake lock").push(request);
            Box::pin(async move {
                Ok(ProcessOutput::new(
                    ProcessStatus::new(true, Some(0)),
                    Vec::new(),
                    Vec::new(),
                    false,
                    false,
                ))
            })
        }
    }

    #[test]
    fn fake_runner_records_typed_requests_without_launching_a_vendor() {
        let runner = FakeRunner::default();
        let request = ProcessRequest::new(
            ExternalProgram::Vendor(VendorProgram::Codex),
            ["exec", "--help"],
            std::env::current_dir().expect("cwd"),
            Duration::from_secs(1),
            Duration::from_millis(100),
            NonZeroUsize::new(1024).expect("non-zero"),
        )
        .expect("request");
        let _result = runner.run(request, &NeverCancelled);
        assert_eq!(runner.calls.lock().expect("fake lock").len(), 1);
    }

    #[test]
    fn request_rejects_relative_working_directories_and_zero_durations() {
        let limit = NonZeroUsize::new(1).expect("non-zero");
        let error = ProcessRequest::new(
            ExternalProgram::Git(GitCliOperation::ExactDiff),
            std::iter::empty::<&str>(),
            PathBuf::from("relative"),
            Duration::from_secs(1),
            Duration::from_secs(1),
            limit,
        )
        .expect_err("relative cwd must fail");
        assert_eq!(
            error.kind(),
            ProcessRequestErrorKind::RelativeWorkingDirectory
        );
    }

    #[test]
    fn git_operation_prefix_cannot_be_replaced_by_caller_arguments() {
        let mut arguments = vec![OsString::from("--exit-code")];
        ExternalProgram::Git(GitCliOperation::ExactDiff).append_fixed_arguments(&mut arguments);
        assert_eq!(arguments, ["diff", "--exit-code"]);
    }

    #[test]
    fn larch_programs_are_derived_from_absolute_safe_roots() {
        let error = LarchProgram::bootstrap(Path::new("relative"))
            .expect_err("relative plugin root must fail");
        assert_eq!(
            error.kind(),
            ProcessRequestErrorKind::UnsafeLarchProgramRoot
        );
        let root = std::env::current_dir().expect("absolute cwd");
        let bootstrap = LarchProgram::bootstrap(&root).expect("safe bootstrap root");
        let binary = LarchProgram::binary(&root).expect("safe binary root");
        assert_eq!(
            bootstrap.executable(),
            root.join("scripts/larch.sh").as_os_str()
        );
        assert_eq!(binary.executable(), root.join("bin/larch").as_os_str());
    }

    #[test]
    fn captured_diagnostics_redact_before_display() {
        let token = ["ghp_", "abcdefghijklmnopqrstuvwxyz0123456789AB"].concat();
        let output = ProcessOutput::new(
            ProcessStatus::new(false, Some(1)),
            Vec::new(),
            token.as_bytes().to_vec(),
            false,
            false,
        );
        assert_eq!(output.safe_stderr().as_str(), "<REDACTED-TOKEN>");
    }

    #[test]
    fn debug_output_omits_arguments_environment_values_stdin_and_captured_bytes() {
        let token = ["ghp_", "abcdefghijklmnopqrstuvwxyz0123456789AB"].concat();
        let request = ProcessRequest::new(
            ExternalProgram::Vendor(VendorProgram::Codex),
            [token.as_str()],
            std::env::current_dir().expect("cwd"),
            Duration::from_secs(1),
            Duration::from_secs(1),
            NonZeroUsize::new(10).expect("non-zero"),
        )
        .expect("request")
        .with_environment(ChildEnvironment::OpenAiApiKey, token.as_str())
        .with_stdin(token.as_bytes().to_vec());
        let output = ProcessOutput::new(
            ProcessStatus::new(false, Some(1)),
            token.as_bytes().to_vec(),
            token.as_bytes().to_vec(),
            false,
            false,
        );

        assert!(!format!("{request:?}").contains(&token));
        assert!(!format!("{output:?}").contains(&token));
        let error = ProcessError::new(ProcessErrorKind::Wait, "failed", Some(output));
        assert!(!format!("{error:?}").contains(&token));
    }
}
