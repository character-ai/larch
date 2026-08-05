use std::{
    error::Error,
    ffi::OsString,
    fmt, fs,
    io::{self, Read},
    num::NonZeroUsize,
    path::{Path, PathBuf},
    sync::atomic::{AtomicUsize, Ordering},
    thread,
    time::Duration,
};

use larch_core::{
    ChildEnvironment, ExternalProgram, ProcessRequest, ProcessRequestError, VendorProgram,
};
use serde::{Deserialize, Serialize};

use crate::TestWorkspace;

const SCRIPT_SCHEMA_VERSION: u8 = 1;
const MAX_SCRIPT_FILE_BYTES: usize = 8 * 1024 * 1024;
const MAX_SCRIPT_OUTPUT_BYTES: usize = 1024 * 1024;
const MAX_CHUNKS: usize = 256;
const MAX_INTER_CHUNK_DELAY_MS: u64 = 60_000;
const FIXTURE_ERROR_EXIT_CODE: i32 = 125;
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(2);
const DEFAULT_SHUTDOWN_GRACE: Duration = Duration::from_millis(250);
const DEFAULT_OUTPUT_LIMIT: NonZeroUsize = NonZeroUsize::new(1024 * 1024).unwrap();

/// Fixed script name read from the fake vendor process working directory.
pub const VENDOR_FIXTURE_SCRIPT_FILE: &str = ".larch-vendor-script.json";

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
enum VendorFamily {
    Claude,
    Codex,
    Cursor,
}

impl From<VendorProgram> for VendorFamily {
    fn from(program: VendorProgram) -> Self {
        match program {
            VendorProgram::Claude => Self::Claude,
            VendorProgram::Codex => Self::Codex,
            VendorProgram::Cursor => Self::Cursor,
        }
    }
}

impl From<VendorFamily> for VendorProgram {
    fn from(family: VendorFamily) -> Self {
        match family {
            VendorFamily::Claude => Self::Claude,
            VendorFamily::Codex => Self::Codex,
            VendorFamily::Cursor => Self::Cursor,
        }
    }
}

/// Destination stream for one ordered fixture chunk.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum VendorStream {
    Stdout,
    Stderr,
}

/// One byte-preserving UTF-8 chunk in a declarative vendor replay.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct VendorChunk {
    stream: VendorStream,
    text: String,
}

impl VendorChunk {
    /// Build a stdout chunk.
    #[must_use]
    pub fn stdout(text: impl Into<String>) -> Self {
        Self {
            stream: VendorStream::Stdout,
            text: text.into(),
        }
    }

    /// Build a stderr chunk.
    #[must_use]
    pub fn stderr(text: impl Into<String>) -> Self {
        Self {
            stream: VendorStream::Stderr,
            text: text.into(),
        }
    }

    /// Return the destination stream.
    #[must_use]
    pub const fn stream(&self) -> VendorStream {
        self.stream
    }

    /// Return the exact chunk text.
    #[must_use]
    pub fn text(&self) -> &str {
        &self.text
    }
}

/// Declarative behavior replayed by one fake vendor executable.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct VendorScript {
    schema_version: u8,
    vendor: VendorFamily,
    chunks: Vec<VendorChunk>,
    inter_chunk_delay_ms: u64,
    exit_code: i32,
    #[serde(default)]
    never_exit: bool,
}

impl VendorScript {
    /// Build an empty successful replay for one vendor family.
    #[must_use]
    pub fn new(vendor: VendorProgram) -> Self {
        Self {
            schema_version: SCRIPT_SCHEMA_VERSION,
            vendor: vendor.into(),
            chunks: Vec::new(),
            inter_chunk_delay_ms: 0,
            exit_code: 0,
            never_exit: false,
        }
    }

    /// Replace the ordered stream chunks.
    #[must_use]
    pub fn with_chunks(mut self, chunks: impl IntoIterator<Item = VendorChunk>) -> Self {
        self.chunks = chunks.into_iter().collect();
        self
    }

    /// Set the delay inserted between adjacent chunks.
    #[must_use]
    pub const fn with_inter_chunk_delay_ms(mut self, delay_ms: u64) -> Self {
        self.inter_chunk_delay_ms = delay_ms;
        self
    }

    /// Set the process exit code used after all chunks are flushed.
    #[must_use]
    pub const fn with_exit_code(mut self, exit_code: i32) -> Self {
        self.exit_code = exit_code;
        self
    }

    /// Keep the process alive after all chunks are flushed.
    #[must_use]
    pub const fn with_never_exit(mut self, never_exit: bool) -> Self {
        self.never_exit = never_exit;
        self
    }

    /// Return the vendor family represented by this script.
    #[must_use]
    pub fn vendor(&self) -> VendorProgram {
        self.vendor.into()
    }

    /// Return the ordered chunks.
    #[must_use]
    pub fn chunks(&self) -> &[VendorChunk] {
        &self.chunks
    }

    /// Return the configured inter-chunk delay.
    #[must_use]
    pub const fn inter_chunk_delay_ms(&self) -> u64 {
        self.inter_chunk_delay_ms
    }

    /// Return the configured exit code.
    #[must_use]
    pub const fn exit_code(&self) -> i32 {
        self.exit_code
    }

    /// Return whether the runner stays alive after replay.
    #[must_use]
    pub const fn never_exits(&self) -> bool {
        self.never_exit
    }

    /// Parse and validate one declarative script.
    ///
    /// # Errors
    /// Rejects oversized, malformed, unknown-version, or unbounded scripts.
    pub fn from_json(bytes: &[u8]) -> Result<Self, VendorFixtureError> {
        if bytes.len() > MAX_SCRIPT_FILE_BYTES {
            return Err(VendorFixtureError::Invalid("vendor script exceeds 8 MiB"));
        }
        let script: Self = serde_json::from_slice(bytes)?;
        script.validate()?;
        Ok(script)
    }

    /// Serialize one validated script for a fake executable.
    ///
    /// # Errors
    /// Rejects invalid script bounds or JSON serialization failure.
    pub fn to_json(&self) -> Result<Vec<u8>, VendorFixtureError> {
        self.validate()?;
        let mut bytes = serde_json::to_vec_pretty(self)?;
        bytes.push(b'\n');
        if bytes.len() > MAX_SCRIPT_FILE_BYTES {
            return Err(VendorFixtureError::Invalid("vendor script exceeds 8 MiB"));
        }
        Ok(bytes)
    }

    fn validate(&self) -> Result<(), VendorFixtureError> {
        if self.schema_version != SCRIPT_SCHEMA_VERSION {
            return Err(VendorFixtureError::Invalid(
                "unsupported vendor script schema version",
            ));
        }
        if self.chunks.len() > MAX_CHUNKS {
            return Err(VendorFixtureError::Invalid(
                "vendor script has more than 256 chunks",
            ));
        }
        let total_bytes = self
            .chunks
            .iter()
            .try_fold(0_usize, |total, chunk| total.checked_add(chunk.text.len()));
        if total_bytes.is_none_or(|total| total > MAX_SCRIPT_OUTPUT_BYTES) {
            return Err(VendorFixtureError::Invalid(
                "vendor script output exceeds 1 MiB",
            ));
        }
        if self.inter_chunk_delay_ms > MAX_INTER_CHUNK_DELAY_MS {
            return Err(VendorFixtureError::Invalid(
                "vendor script inter-chunk delay exceeds 60 seconds",
            ));
        }
        if !(0..=255).contains(&self.exit_code) {
            return Err(VendorFixtureError::Invalid(
                "vendor script exit code must be between 0 and 255",
            ));
        }
        Ok(())
    }
}

/// Recorded vendor contracts carried forward from `python/tests/agents/`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VendorContractFixture {
    CodexSuccess,
    CodexQuota,
    CodexConnectivity,
    CodexCliGate,
    CodexPolicyRejection,
    CodexTruncated,
    CursorSuccess,
    CursorConnectivity,
    CursorRefusal,
    CursorParseError,
    ClaudeOk,
    ClaudeIsError,
    ClaudeEmptyResult,
    ClaudeMissingResult,
    ClaudeNonStringResult,
    ClaudeMalformedJson,
    ClaudeNonObject,
    Redaction,
}

impl VendorContractFixture {
    /// Return every checked-in contract fixture.
    #[must_use]
    pub const fn all() -> &'static [Self] {
        &[
            Self::CodexSuccess,
            Self::CodexQuota,
            Self::CodexConnectivity,
            Self::CodexCliGate,
            Self::CodexPolicyRejection,
            Self::CodexTruncated,
            Self::CursorSuccess,
            Self::CursorConnectivity,
            Self::CursorRefusal,
            Self::CursorParseError,
            Self::ClaudeOk,
            Self::ClaudeIsError,
            Self::ClaudeEmptyResult,
            Self::ClaudeMissingResult,
            Self::ClaudeNonStringResult,
            Self::ClaudeMalformedJson,
            Self::ClaudeNonObject,
            Self::Redaction,
        ]
    }

    /// Parse the embedded fixture without filesystem or network access.
    ///
    /// # Errors
    /// Returns a schema or validation error if the checked-in fixture drifts.
    pub fn load(self) -> Result<VendorScript, VendorFixtureError> {
        VendorScript::from_json(self.bytes())
    }

    /// Return the fixture basename.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::CodexSuccess => "codex-success.json",
            Self::CodexQuota => "codex-quota.json",
            Self::CodexConnectivity => "codex-connectivity.json",
            Self::CodexCliGate => "codex-cli-gate.json",
            Self::CodexPolicyRejection => "codex-policy-rejection.json",
            Self::CodexTruncated => "codex-truncated.json",
            Self::CursorSuccess => "cursor-success.json",
            Self::CursorConnectivity => "cursor-connectivity.json",
            Self::CursorRefusal => "cursor-refusal.json",
            Self::CursorParseError => "cursor-parse-error.json",
            Self::ClaudeOk => "claude-ok.json",
            Self::ClaudeIsError => "claude-is-error.json",
            Self::ClaudeEmptyResult => "claude-empty-result.json",
            Self::ClaudeMissingResult => "claude-missing-result.json",
            Self::ClaudeNonStringResult => "claude-non-string-result.json",
            Self::ClaudeMalformedJson => "claude-malformed-json.json",
            Self::ClaudeNonObject => "claude-non-object.json",
            Self::Redaction => "redaction.json",
        }
    }

    const fn bytes(self) -> &'static [u8] {
        match self {
            Self::CodexSuccess => include_bytes!("../fixtures/vendor/codex-success.json"),
            Self::CodexQuota => include_bytes!("../fixtures/vendor/codex-quota.json"),
            Self::CodexConnectivity => {
                include_bytes!("../fixtures/vendor/codex-connectivity.json")
            }
            Self::CodexCliGate => include_bytes!("../fixtures/vendor/codex-cli-gate.json"),
            Self::CodexPolicyRejection => {
                include_bytes!("../fixtures/vendor/codex-policy-rejection.json")
            }
            Self::CodexTruncated => include_bytes!("../fixtures/vendor/codex-truncated.json"),
            Self::CursorSuccess => include_bytes!("../fixtures/vendor/cursor-success.json"),
            Self::CursorConnectivity => {
                include_bytes!("../fixtures/vendor/cursor-connectivity.json")
            }
            Self::CursorRefusal => include_bytes!("../fixtures/vendor/cursor-refusal.json"),
            Self::CursorParseError => include_bytes!("../fixtures/vendor/cursor-parse-error.json"),
            Self::ClaudeOk => include_bytes!("../fixtures/vendor/claude-ok.json"),
            Self::ClaudeIsError => include_bytes!("../fixtures/vendor/claude-is-error.json"),
            Self::ClaudeEmptyResult => {
                include_bytes!("../fixtures/vendor/claude-empty-result.json")
            }
            Self::ClaudeMissingResult => {
                include_bytes!("../fixtures/vendor/claude-missing-result.json")
            }
            Self::ClaudeNonStringResult => {
                include_bytes!("../fixtures/vendor/claude-non-string-result.json")
            }
            Self::ClaudeMalformedJson => {
                include_bytes!("../fixtures/vendor/claude-malformed-json.json")
            }
            Self::ClaudeNonObject => include_bytes!("../fixtures/vendor/claude-non-object.json"),
            Self::Redaction => include_bytes!("../fixtures/vendor/redaction.json"),
        }
    }
}

/// Absolute paths to the three Cargo-built fake vendor binaries.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VendorBinarySet {
    claude: PathBuf,
    codex: PathBuf,
    cursor: PathBuf,
}

impl VendorBinarySet {
    /// Validate the fake binaries supplied by an integration test.
    ///
    /// # Errors
    /// Rejects relative, missing, symlinked, non-regular, or non-executable paths.
    pub fn new(
        claude: impl Into<PathBuf>,
        codex: impl Into<PathBuf>,
        cursor: impl Into<PathBuf>,
    ) -> Result<Self, VendorFixtureError> {
        let binaries = Self {
            claude: claude.into(),
            codex: codex.into(),
            cursor: cursor.into(),
        };
        for program in [
            VendorProgram::Claude,
            VendorProgram::Codex,
            VendorProgram::Cursor,
        ] {
            validate_binary(program, binaries.path(program))?;
        }
        Ok(binaries)
    }

    /// Return the fake binary path for one vendor.
    #[must_use]
    pub fn path(&self, program: VendorProgram) -> &Path {
        match program {
            VendorProgram::Claude => &self.claude,
            VendorProgram::Codex => &self.codex,
            VendorProgram::Cursor => &self.cursor,
        }
    }
}

/// Per-invocation request options for [`VendorProcessHarness`].
#[derive(Clone, Debug)]
pub struct VendorRunOptions {
    arguments: Vec<OsString>,
    stdin: Vec<u8>,
    timeout: Duration,
    shutdown_grace: Duration,
    output_limit: NonZeroUsize,
}

impl VendorRunOptions {
    /// Replace the vendor argument vector.
    #[must_use]
    pub fn with_arguments<I, A>(mut self, arguments: I) -> Self
    where
        I: IntoIterator<Item = A>,
        A: Into<OsString>,
    {
        self.arguments = arguments.into_iter().map(Into::into).collect();
        self
    }

    /// Replace the bytes written to vendor stdin.
    #[must_use]
    pub fn with_stdin(mut self, stdin: impl Into<Vec<u8>>) -> Self {
        self.stdin = stdin.into();
        self
    }

    /// Set the process timeout.
    #[must_use]
    pub const fn with_timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
    }

    /// Set the graceful shutdown interval.
    #[must_use]
    pub const fn with_shutdown_grace(mut self, shutdown_grace: Duration) -> Self {
        self.shutdown_grace = shutdown_grace;
        self
    }

    /// Set the per-stream capture limit.
    #[must_use]
    pub const fn with_output_limit(mut self, output_limit: NonZeroUsize) -> Self {
        self.output_limit = output_limit;
        self
    }
}

impl Default for VendorRunOptions {
    fn default() -> Self {
        Self {
            arguments: Vec::new(),
            stdin: Vec::new(),
            timeout: DEFAULT_TIMEOUT,
            shutdown_grace: DEFAULT_SHUTDOWN_GRACE,
            output_limit: DEFAULT_OUTPUT_LIMIT,
        }
    }
}

/// Owned harness that makes only Cargo-built fake vendors reachable on `PATH`.
#[derive(Debug)]
pub struct VendorProcessHarness {
    workspace: TestWorkspace,
    binary_directory: PathBuf,
    next_invocation: AtomicUsize,
}

impl VendorProcessHarness {
    /// Install private copies of all three fake vendor executables.
    ///
    /// # Errors
    /// Returns a validation or confined-filesystem error.
    pub fn new(binaries: &VendorBinarySet) -> Result<Self, VendorFixtureError> {
        let workspace = TestWorkspace::new()?;
        let binary_directory = workspace.create_dir("bin")?;
        for program in [
            VendorProgram::Claude,
            VendorProgram::Codex,
            VendorProgram::Cursor,
        ] {
            let destination = binary_directory.join(program.executable());
            let _bytes = fs::copy(binaries.path(program), &destination)?;
            validate_binary(program, &destination)?;
        }
        Ok(Self {
            workspace,
            binary_directory,
            next_invocation: AtomicUsize::new(0),
        })
    }

    /// Build a typed process request with isolated defaults.
    ///
    /// # Errors
    /// Returns a script, filesystem, or process-request validation error.
    pub fn request(&self, script: &VendorScript) -> Result<ProcessRequest, VendorFixtureError> {
        self.request_with(script, VendorRunOptions::default())
    }

    /// Build a typed process request with explicit invocation options.
    ///
    /// # Errors
    /// Returns a script, filesystem, or process-request validation error.
    pub fn request_with(
        &self,
        script: &VendorScript,
        options: VendorRunOptions,
    ) -> Result<ProcessRequest, VendorFixtureError> {
        let invocation = self.next_invocation.fetch_add(1, Ordering::Relaxed);
        let relative_directory = format!("runs/{invocation}");
        let working_directory = self.workspace.create_dir(&relative_directory)?;
        let relative_script = format!("{relative_directory}/{VENDOR_FIXTURE_SCRIPT_FILE}");
        let _script_path = self.workspace.write(relative_script, script.to_json()?)?;
        ProcessRequest::new(
            ExternalProgram::Vendor(script.vendor()),
            options.arguments,
            working_directory,
            options.timeout,
            options.shutdown_grace,
            options.output_limit,
        )
        .map(|request| {
            request
                .with_environment(ChildEnvironment::Path, self.binary_directory.as_os_str())
                .with_stdin(options.stdin)
        })
        .map_err(VendorFixtureError::ProcessRequest)
    }

    /// Return the private directory used as the complete child `PATH`.
    #[must_use]
    pub fn binary_directory(&self) -> &Path {
        &self.binary_directory
    }
}

/// Run one Cargo-built fake vendor process. This function does not return.
#[doc(hidden)]
pub fn vendor_test_binary_main(expected: VendorProgram) -> ! {
    let result = replay_script(expected);
    let exit_code = match result {
        Ok(exit_code) => exit_code,
        Err(error) => {
            eprintln!("larch fake vendor: {error}");
            FIXTURE_ERROR_EXIT_CODE
        }
    };
    std::process::exit(exit_code)
}

fn replay_script(expected: VendorProgram) -> Result<i32, VendorFixtureError> {
    let bytes = read_script_file()?;
    let script = VendorScript::from_json(&bytes)?;
    if script.vendor() != expected {
        return Err(VendorFixtureError::VendorMismatch {
            expected,
            actual: script.vendor(),
        });
    }
    let _stdin_bytes = io::copy(&mut io::stdin().lock(), &mut io::sink())?;
    let stdout = io::stdout();
    let stderr = io::stderr();
    let mut stdout = stdout.lock();
    let mut stderr = stderr.lock();
    for (index, chunk) in script.chunks().iter().enumerate() {
        if index != 0 && script.inter_chunk_delay_ms() != 0 {
            thread::sleep(Duration::from_millis(script.inter_chunk_delay_ms()));
        }
        let writer: &mut dyn io::Write = match chunk.stream() {
            VendorStream::Stdout => &mut stdout,
            VendorStream::Stderr => &mut stderr,
        };
        writer.write_all(chunk.text().as_bytes())?;
        writer.flush()?;
    }
    if script.never_exits() {
        loop {
            thread::park();
        }
    }
    Ok(script.exit_code())
}

fn read_script_file() -> Result<Vec<u8>, VendorFixtureError> {
    let path = Path::new(VENDOR_FIXTURE_SCRIPT_FILE);
    let path_metadata = fs::symlink_metadata(path)?;
    if path_metadata.file_type().is_symlink() || !path_metadata.file_type().is_file() {
        return Err(VendorFixtureError::Invalid(
            "vendor script is not a regular non-symlink file",
        ));
    }
    let file = fs::File::open(path)?;
    if file.metadata()?.len() > MAX_SCRIPT_FILE_BYTES as u64 {
        return Err(VendorFixtureError::Invalid("vendor script exceeds 8 MiB"));
    }
    let mut bytes = Vec::new();
    file.take((MAX_SCRIPT_FILE_BYTES + 1) as u64)
        .read_to_end(&mut bytes)?;
    if bytes.len() > MAX_SCRIPT_FILE_BYTES {
        return Err(VendorFixtureError::Invalid("vendor script exceeds 8 MiB"));
    }
    Ok(bytes)
}

fn validate_binary(program: VendorProgram, path: &Path) -> Result<(), VendorFixtureError> {
    if !path.is_absolute() {
        return Err(VendorFixtureError::InvalidBinary {
            program,
            reason: "path is not absolute",
        });
    }
    let metadata = fs::symlink_metadata(path)
        .map_err(|error| VendorFixtureError::BinaryIo { program, error })?;
    if metadata.file_type().is_symlink() || !metadata.file_type().is_file() {
        return Err(VendorFixtureError::InvalidBinary {
            program,
            reason: "path is not a regular non-symlink file",
        });
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if metadata.permissions().mode() & 0o111 == 0 {
            return Err(VendorFixtureError::InvalidBinary {
                program,
                reason: "path is not executable",
            });
        }
    }
    Ok(())
}

/// Error returned by vendor fixture loading, staging, or replay.
#[derive(Debug)]
pub enum VendorFixtureError {
    Io(io::Error),
    Json(serde_json::Error),
    ProcessRequest(ProcessRequestError),
    BinaryIo {
        program: VendorProgram,
        error: io::Error,
    },
    Invalid(&'static str),
    InvalidBinary {
        program: VendorProgram,
        reason: &'static str,
    },
    VendorMismatch {
        expected: VendorProgram,
        actual: VendorProgram,
    },
}

impl fmt::Display for VendorFixtureError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(error) => write!(formatter, "vendor fixture I/O failed: {error}"),
            Self::Json(error) => write!(formatter, "vendor fixture JSON is invalid: {error}"),
            Self::ProcessRequest(error) => write!(formatter, "vendor request is invalid: {error}"),
            Self::BinaryIo { program, error } => {
                write!(
                    formatter,
                    "fake {program:?} binary cannot be inspected: {error}"
                )
            }
            Self::Invalid(reason) => write!(formatter, "vendor fixture is invalid: {reason}"),
            Self::InvalidBinary { program, reason } => {
                write!(formatter, "fake {program:?} binary is invalid: {reason}")
            }
            Self::VendorMismatch { expected, actual } => write!(
                formatter,
                "vendor fixture targets {actual:?}, not invoked fake {expected:?}"
            ),
        }
    }
}

impl Error for VendorFixtureError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Io(error) | Self::BinaryIo { error, .. } => Some(error),
            Self::Json(error) => Some(error),
            Self::ProcessRequest(error) => Some(error),
            Self::Invalid(_) | Self::InvalidBinary { .. } | Self::VendorMismatch { .. } => None,
        }
    }
}

impl From<io::Error> for VendorFixtureError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

impl From<serde_json::Error> for VendorFixtureError {
    fn from(error: serde_json::Error) -> Self {
        Self::Json(error)
    }
}

#[cfg(test)]
mod tests {
    use larch_core::VendorProgram;

    use super::{VendorChunk, VendorContractFixture, VendorScript};

    #[test]
    fn every_recorded_contract_loads_offline() {
        for fixture in VendorContractFixture::all() {
            let script = fixture
                .load()
                .unwrap_or_else(|error| panic!("{}: {error}", fixture.name()));
            assert_eq!(
                script.to_json().expect("serialize fixture").last(),
                Some(&b'\n')
            );
        }
    }

    #[test]
    fn scripts_round_trip_ordered_streams() {
        let script = VendorScript::new(VendorProgram::Codex)
            .with_chunks([VendorChunk::stdout("first"), VendorChunk::stderr("second")])
            .with_inter_chunk_delay_ms(4)
            .with_exit_code(7)
            .with_never_exit(true);

        assert_eq!(
            VendorScript::from_json(&script.to_json().expect("serialize script"))
                .expect("parse script"),
            script
        );
    }

    #[test]
    fn parser_rejects_unknown_fields_and_unbounded_values() {
        let unknown = br#"{"schema_version":1,"vendor":"claude","chunks":[],"inter_chunk_delay_ms":0,"exit_code":0,"unknown":true}"#;
        assert!(VendorScript::from_json(unknown).is_err());
        let delayed = VendorScript::new(VendorProgram::Cursor).with_inter_chunk_delay_ms(60_001);
        assert!(delayed.to_json().is_err());
        let oversized =
            VendorScript::new(VendorProgram::Claude).with_chunks([VendorChunk::stdout(
                "x".repeat(super::MAX_SCRIPT_OUTPUT_BYTES + 1),
            )]);
        assert!(oversized.to_json().is_err());
    }
}
