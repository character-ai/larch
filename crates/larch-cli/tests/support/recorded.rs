use std::{
    collections::{BTreeMap, BTreeSet},
    env, fs,
    io::{self, Read, Write},
    path::{Component, Path, PathBuf},
    process::{Command, Output, Stdio},
    sync::OnceLock,
    thread,
    time::Duration,
};

use regex::Regex;
use serde_json::{Value, json};
use tempfile::TempDir;
use wait_timeout::ChildExt;

const UPDATE_GOLDENS_ENV: &str = "LARCH_UPDATE_RECORDED_GOLDENS";
const PLATFORM_TEMP_ROOT: &str = "/tmp";
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(30);
/// A private `flock` inode used only to serialize session activation and
/// cleanup. It is neither a wire artifact nor a command payload, so recorded
/// captures exclude this implementation-detail file while still rejecting a
/// symlink there.
const SESSION_ACTIVITY_LOCK_RELATIVE: &str =
    ".home/.cache/larch/sessions/.larch-session-activity.lock";
/// A private, stable `flock` inode that serializes replacement of the
/// stall-recovery attempt ledger. It has no wire meaning and is excluded from
/// recorded captures, while ordinary lock files remain observable.
const STALL_RECOVERY_ATTEMPT_LOCK_NAME: &str = ".stall-recovery-attempts.lock";
/// Coverage-instrumented binaries drop `*.profraw` LLVM profile files into
/// their working directory when the recorded suite runs under `cargo llvm-cov`.
/// They are an instrumentation byproduct, never a genuine CLI side effect, so
/// the capture ignores them so coverage runs retain the normal contract.
const LLVM_PROFRAW_EXTENSION: &str = "profraw";
static RFC3339_UTC: OnceLock<Regex> = OnceLock::new();
static PROCESS_IDENTITY: OnceLock<Regex> = OnceLock::new();
static PUBLISH_ATTEMPT_ID: OnceLock<Regex> = OnceLock::new();
static PARENT_PROCESS: OnceLock<Regex> = OnceLock::new();
static REFRESH_EPOCH: OnceLock<Regex> = OnceLock::new();
static STATUSLINE_STAMP: OnceLock<Regex> = OnceLock::new();
const BLOCKED_ENVIRONMENT_KEYS: &[&str] = &[
    "ALL_PROXY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "CLOUDSDK_CONFIG",
    "GH_ENTERPRISE_TOKEN",
    "GH_HOST",
    "GH_TOKEN",
    "GITHUB_API_URL",
    "GITHUB_GRAPHQL_URL",
    "GITHUB_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "LARCH_GH_TOKEN",
    "LARCH_SLACK_WEBHOOK_URL",
    "NO_PROXY",
];

#[derive(Clone, Debug)]
pub struct Program {
    executable: PathBuf,
    arguments: Vec<String>,
    environment: BTreeMap<String, String>,
    stdin: Option<Vec<u8>>,
    timeout: Duration,
}

impl Program {
    pub fn new(executable: impl Into<PathBuf>) -> Self {
        Self {
            executable: executable.into(),
            arguments: Vec::new(),
            environment: BTreeMap::new(),
            stdin: None,
            timeout: DEFAULT_TIMEOUT,
        }
    }

    pub fn args<I, S>(mut self, arguments: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        self.arguments.extend(arguments.into_iter().map(Into::into));
        self
    }

    pub fn env(mut self, key: &str, value: &str) -> Self {
        self.environment.insert(key.to_owned(), value.to_owned());
        self
    }

    pub fn stdin(mut self, input: &[u8]) -> Self {
        self.stdin = Some(input.to_vec());
        self
    }

    pub const fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
    }
}

#[derive(Clone, Debug)]
pub struct SeedFile {
    relative_path: PathBuf,
    contents: Vec<u8>,
    executable: bool,
    expand_root: bool,
}

impl SeedFile {
    pub fn text(relative_path: &str, contents: &str) -> Self {
        Self {
            relative_path: PathBuf::from(relative_path),
            contents: contents.as_bytes().to_vec(),
            executable: false,
            expand_root: false,
        }
    }

    #[allow(dead_code)]
    pub fn bytes(relative_path: &str, contents: &[u8]) -> Self {
        Self {
            relative_path: PathBuf::from(relative_path),
            contents: contents.to_vec(),
            executable: false,
            expand_root: false,
        }
    }

    #[cfg(unix)]
    #[allow(dead_code)]
    pub fn executable_text(relative_path: &str, contents: &str) -> Self {
        Self {
            relative_path: PathBuf::from(relative_path),
            contents: contents.as_bytes().to_vec(),
            executable: true,
            expand_root: false,
        }
    }

    #[allow(dead_code)]
    pub fn expanded_text(relative_path: &str, contents: &str) -> Self {
        Self {
            relative_path: PathBuf::from(relative_path),
            contents: contents.as_bytes().to_vec(),
            executable: false,
            expand_root: true,
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub enum NormalizationRule {
    SandboxRoot,
    Rfc3339Utc,
    ProcessIdentity,
    StatuslineStamp,
}

#[derive(Clone, Debug)]
pub struct RecordedCase {
    pub name: &'static str,
    pub program: Program,
    pub seed_files: Vec<SeedFile>,
    pub side_effect_records: Vec<PathBuf>,
    pub normalization: Vec<NormalizationRule>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum CapturedContent {
    Text(String),
    Binary(Vec<u8>),
}

type FileSnapshot = BTreeMap<String, CapturedContent>;
type SideEffectSnapshot = BTreeMap<String, String>;
type TreeSnapshot = (FileSnapshot, SideEffectSnapshot);

#[derive(Clone, Debug, Eq, PartialEq)]
struct Capture {
    exit_code: Option<i32>,
    stdout: CapturedContent,
    stderr: CapturedContent,
    files: FileSnapshot,
    side_effects: SideEffectSnapshot,
}

struct Sandbox {
    _directory: TempDir,
    root: PathBuf,
}

impl Sandbox {
    fn new(seed_files: &[SeedFile]) -> Result<Self, String> {
        // Anchor at the canonicalized platform temporary root rather than
        // `env::temp_dir()`. Session-tmpdir allowlists accept `/tmp`, so a
        // sandbox under the macOS `$TMPDIR` (`/var/folders/...`) would record a
        // refusal where Linux records success. Canonicalizing keeps the recorded
        // spelling free of root-owned platform aliases (`/var` -> `private/var`).
        let base = PathBuf::from(PLATFORM_TEMP_ROOT)
            .canonicalize()
            .map_err(|error| format!("canonicalize {PLATFORM_TEMP_ROOT}: {error}"))?;
        let directory = tempfile::Builder::new()
            .prefix("larch-recorded-")
            .tempdir_in(&base)
            .map_err(|error| format!("create recorded sandbox: {error}"))?;
        let root = directory
            .path()
            .canonicalize()
            .map_err(|error| format!("canonicalize recorded sandbox: {error}"))?;
        for relative in [".home", ".tmp", ".bin"] {
            fs::create_dir(root.join(relative))
                .map_err(|error| format!("create sandbox directory {relative}: {error}"))?;
        }
        let sandbox = Self {
            _directory: directory,
            root,
        };
        for seed in seed_files {
            let path = sandbox.safe_path(&seed.relative_path)?;
            if let Some(parent) = path.parent() {
                fs::create_dir_all(parent)
                    .map_err(|error| format!("create seed parent {}: {error}", parent.display()))?;
            }
            let contents = if seed.expand_root {
                let text = std::str::from_utf8(&seed.contents)
                    .map_err(|error| format!("expand seed {} as UTF-8: {error}", path.display()))?;
                expand_sandbox(text, sandbox.root()).into_bytes()
            } else {
                seed.contents.clone()
            };
            fs::write(&path, contents)
                .map_err(|error| format!("write seed {}: {error}", path.display()))?;
            #[cfg(unix)]
            if seed.executable {
                use std::os::unix::fs::PermissionsExt as _;
                let mut permissions = fs::metadata(&path)
                    .map_err(|error| format!("inspect seed {}: {error}", path.display()))?
                    .permissions();
                permissions.set_mode(0o755);
                fs::set_permissions(&path, permissions)
                    .map_err(|error| format!("make seed executable {}: {error}", path.display()))?;
            }
        }
        Ok(sandbox)
    }

    fn root(&self) -> &Path {
        &self.root
    }

    fn safe_path(&self, relative: &Path) -> Result<PathBuf, String> {
        validate_relative_path(relative)?;
        Ok(self.root().join(relative))
    }
}

pub fn assert_recorded_case(case: &RecordedCase, golden_path: &Path) -> Result<(), String> {
    validate_program(&case.program, "recorded command")?;
    let sandbox = Sandbox::new(&case.seed_files)?;
    let record_paths: BTreeSet<PathBuf> = case.side_effect_records.iter().cloned().collect();
    for path in &record_paths {
        validate_relative_path(path)?;
    }

    let capture = run_program(&case.program, &sandbox, &record_paths)?;
    let capture = normalize_capture(capture, sandbox.root(), &case.normalization);
    assert_golden(case.name, &capture, golden_path)
}

fn validate_program(program: &Program, label: &str) -> Result<(), String> {
    if !program.executable.is_absolute() {
        return Err(format!(
            "{label} executable must be an absolute path: {}",
            program.executable.display()
        ));
    }
    for key in program.environment.keys() {
        if BLOCKED_ENVIRONMENT_KEYS.contains(&key.as_str()) {
            return Err(format!(
                "{label} environment override {key} is blocked; use a fixture service"
            ));
        }
    }
    Ok(())
}

fn validate_relative_path(path: &Path) -> Result<(), String> {
    if path.as_os_str().is_empty()
        || path
            .components()
            .any(|component| !matches!(component, Component::Normal(_)))
    {
        return Err(format!(
            "recorded fixture path must be a confined relative path: {}",
            path.display()
        ));
    }
    Ok(())
}

fn run_program(
    program: &Program,
    sandbox: &Sandbox,
    record_paths: &BTreeSet<PathBuf>,
) -> Result<Capture, String> {
    let mut command = Command::new(&program.executable);
    command
        .current_dir(sandbox.root())
        .env_clear()
        .env("ALL_PROXY", "http://127.0.0.1:9")
        .env("AWS_EC2_METADATA_DISABLED", "true")
        .env("CLOUDSDK_CONFIG", sandbox.root().join(".cloud-disabled"))
        .env("GH_HOST", "127.0.0.1:9")
        .env("GITHUB_API_URL", "http://127.0.0.1:9")
        .env("GITHUB_GRAPHQL_URL", "http://127.0.0.1:9/graphql")
        .env("HOME", sandbox.root().join(".home"))
        .env("HTTPS_PROXY", "http://127.0.0.1:9")
        .env("HTTP_PROXY", "http://127.0.0.1:9")
        .env("LANG", "C")
        .env("LARCH_RECORDED_LIVE_SERVICES", "disabled")
        .env("NO_OPEN_BROWSER", "1")
        .env("NO_PROXY", "")
        .env("PATH", sandbox.root().join(".bin"))
        .env("TMPDIR", sandbox.root().join(".tmp"));
    if let Some(profile) = env::var_os("LLVM_PROFILE_FILE") {
        command.env("LLVM_PROFILE_FILE", profile);
    }
    for argument in &program.arguments {
        command.arg(expand_sandbox(argument, sandbox.root()));
    }
    for (key, value) in &program.environment {
        command.env(key, expand_sandbox(value, sandbox.root()));
    }
    let output = output_with_timeout(
        command,
        &program.executable,
        program.stdin.as_deref(),
        program.timeout,
    )?;
    let (files, side_effects) = capture_tree(sandbox.root(), record_paths)?;
    Ok(Capture {
        exit_code: output.status.code(),
        stdout: captured_content(output.stdout),
        stderr: captured_content(output.stderr),
        files,
        side_effects,
    })
}

fn output_with_timeout(
    mut command: Command,
    executable: &Path,
    stdin: Option<&[u8]>,
    timeout: Duration,
) -> Result<Output, String> {
    command
        .stdin(if stdin.is_some() {
            Stdio::piped()
        } else {
            Stdio::null()
        })
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = command
        .spawn()
        .map_err(|error| format!("launch recorded command {}: {error}", executable.display()))?;
    if let Some(input) = stdin {
        child
            .stdin
            .take()
            .ok_or_else(|| "write recorded command stdin: pipe unavailable".to_owned())?
            .write_all(input)
            .map_err(|error| format!("write recorded command stdin: {error}"))?;
    }
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "capture recorded command stdout: pipe unavailable".to_owned())?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| "capture recorded command stderr: pipe unavailable".to_owned())?;
    let stdout_reader = thread::spawn(move || read_stream(stdout));
    let stderr_reader = thread::spawn(move || read_stream(stderr));
    let status = match child.wait_timeout(timeout) {
        Ok(Some(status)) => status,
        Ok(None) => {
            let _ = child.kill();
            let _ = child.wait();
            join_reader(stdout_reader, "stdout")?;
            join_reader(stderr_reader, "stderr")?;
            return Err(format!(
                "recorded command {} timed out after {timeout:?}",
                executable.display()
            ));
        }
        Err(error) => {
            let _ = child.kill();
            let _ = child.wait();
            join_reader(stdout_reader, "stdout")?;
            join_reader(stderr_reader, "stderr")?;
            return Err(format!(
                "wait for recorded command {}: {error}",
                executable.display()
            ));
        }
    };
    Ok(Output {
        status,
        stdout: join_reader(stdout_reader, "stdout")?,
        stderr: join_reader(stderr_reader, "stderr")?,
    })
}

fn read_stream(mut stream: impl Read) -> io::Result<Vec<u8>> {
    let mut bytes = Vec::new();
    stream.read_to_end(&mut bytes)?;
    Ok(bytes)
}

fn join_reader(
    reader: thread::JoinHandle<io::Result<Vec<u8>>>,
    label: &str,
) -> Result<Vec<u8>, String> {
    reader
        .join()
        .map_err(|_| format!("capture recorded command {label}: reader thread panicked"))?
        .map_err(|error| format!("capture recorded command {label}: {error}"))
}

fn captured_content(bytes: Vec<u8>) -> CapturedContent {
    match String::from_utf8(bytes) {
        Ok(text) => CapturedContent::Text(text),
        Err(error) => CapturedContent::Binary(error.into_bytes()),
    }
}

fn expand_sandbox(value: &str, root: &Path) -> String {
    value.replace("{sandbox}", &root.to_string_lossy())
}

fn capture_tree(root: &Path, record_paths: &BTreeSet<PathBuf>) -> Result<TreeSnapshot, String> {
    let mut files = BTreeMap::new();
    let mut side_effects = BTreeMap::new();
    capture_directory(root, root, record_paths, &mut files, &mut side_effects)?;
    for relative in record_paths {
        let key = path_key(relative)?;
        side_effects.entry(key).or_default();
    }
    Ok((files, side_effects))
}

fn capture_directory(
    root: &Path,
    directory: &Path,
    record_paths: &BTreeSet<PathBuf>,
    files: &mut BTreeMap<String, CapturedContent>,
    side_effects: &mut BTreeMap<String, String>,
) -> Result<(), String> {
    let mut entries: Vec<_> = fs::read_dir(directory)
        .map_err(|error| format!("read sandbox directory {}: {error}", directory.display()))?
        .collect::<Result<_, _>>()
        .map_err(|error| format!("read sandbox entry: {error}"))?;
    entries.sort_by_key(fs::DirEntry::file_name);
    for entry in entries {
        let path = entry.path();
        let metadata = fs::symlink_metadata(&path)
            .map_err(|error| format!("inspect sandbox path {}: {error}", path.display()))?;
        if metadata.file_type().is_symlink() {
            return Err(format!(
                "recorded command created a forbidden symlink: {}",
                path.display()
            ));
        }
        if metadata.is_dir() {
            capture_directory(root, &path, record_paths, files, side_effects)?;
            continue;
        }
        if !metadata.is_file() {
            return Err(format!(
                "recorded command created a non-file artifact: {}",
                path.display()
            ));
        }
        let relative = path
            .strip_prefix(root)
            .map_err(|error| format!("derive sandbox-relative path: {error}"))?;
        if relative == Path::new(SESSION_ACTIVITY_LOCK_RELATIVE)
            || relative
                .file_name()
                .is_some_and(|name| name == STALL_RECOVERY_ATTEMPT_LOCK_NAME)
            || relative
                .extension()
                .is_some_and(|extension| extension == LLVM_PROFRAW_EXTENSION)
        {
            continue;
        }
        let key = path_key(relative)?;
        let bytes = fs::read(&path)
            .map_err(|error| format!("read sandbox file {}: {error}", path.display()))?;
        if record_paths.contains(relative) {
            let text = String::from_utf8(bytes)
                .map_err(|error| format!("side-effect record {key} is not UTF-8: {error}"))?;
            side_effects.insert(key, text);
        } else {
            files.insert(key, captured_content(bytes));
        }
    }
    Ok(())
}

fn path_key(path: &Path) -> Result<String, String> {
    path.to_str()
        .map(str::to_owned)
        .ok_or_else(|| format!("recorded fixture path is not UTF-8: {}", path.display()))
}

fn normalize_capture(
    mut capture: Capture,
    sandbox_root: &Path,
    rules: &[NormalizationRule],
) -> Capture {
    normalize_content(&mut capture.stdout, sandbox_root, rules);
    normalize_content(&mut capture.stderr, sandbox_root, rules);
    for contents in capture.files.values_mut() {
        normalize_content(contents, sandbox_root, rules);
    }
    for record in capture.side_effects.values_mut() {
        *record = normalize_text(record, sandbox_root, rules);
    }
    capture
}

fn normalize_content(
    content: &mut CapturedContent,
    sandbox_root: &Path,
    rules: &[NormalizationRule],
) {
    if let CapturedContent::Text(text) = content {
        *text = normalize_text(text, sandbox_root, rules);
    }
}

fn normalize_text(text: &str, sandbox_root: &Path, rules: &[NormalizationRule]) -> String {
    let mut normalized = text.to_owned();
    for rule in rules {
        normalized = match rule {
            // Replace the canonical spelling first: a command that resolves a
            // path emits `/private/var/...` where the sandbox root is `/var/...`.
            NormalizationRule::SandboxRoot => {
                let canonical = fs::canonicalize(sandbox_root).unwrap_or_default();
                let canonical = canonical.to_string_lossy().into_owned();
                if canonical.is_empty() {
                    normalized
                } else {
                    normalized.replace(canonical.as_str(), "<SANDBOX>")
                }
                .replace(sandbox_root.to_string_lossy().as_ref(), "<SANDBOX>")
            }
            NormalizationRule::Rfc3339Utc => rfc3339_utc_pattern()
                .replace_all(&normalized, "<TIMESTAMP>")
                .into_owned(),
            NormalizationRule::ProcessIdentity => {
                let with_pids = process_identity_pattern()
                    .replace_all(&normalized, "${1}=<PID>")
                    .into_owned();
                let with_attempts = publish_attempt_id_pattern()
                    .replace_all(&with_pids, "${1}=<ATTEMPT_ID>")
                    .into_owned();
                let with_parent = parent_process_pattern()
                    .replace_all(&with_attempts, "parent=<PROCESS>")
                    .into_owned();
                refresh_epoch_pattern()
                    .replace_all(&with_parent, "REFRESH_EPOCH=<EPOCH>")
                    .into_owned()
            }
            NormalizationRule::StatuslineStamp => statusline_stamp_pattern()
                .replace_all(&normalized, "larch <STAMP>:")
                .into_owned(),
        };
    }
    normalized
}

fn statusline_stamp_pattern() -> &'static Regex {
    STATUSLINE_STAMP.get_or_init(|| {
        Regex::new(r"larch \d{2}:\d{2}:")
            .expect("statusline stamp normalization regex should compile")
    })
}

fn rfc3339_utc_pattern() -> &'static Regex {
    RFC3339_UTC.get_or_init(|| {
        Regex::new(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)\b")
            .expect("RFC 3339 normalization regex should compile")
    })
}

fn process_identity_pattern() -> &'static Regex {
    PROCESS_IDENTITY.get_or_init(|| {
        Regex::new(r"(?i)\b(pid|ppid|waiter_pid)=\d+")
            .expect("process identity normalization regex should compile")
    })
}

fn publish_attempt_id_pattern() -> &'static Regex {
    PUBLISH_ATTEMPT_ID.get_or_init(|| {
        Regex::new(r"(?i)\b(publish_attempt_id)=[A-Za-z0-9._-]+")
            .expect("publish attempt ID normalization regex should compile")
    })
}

fn parent_process_pattern() -> &'static Regex {
    PARENT_PROCESS.get_or_init(|| {
        Regex::new(r"\bparent=[^?\s]\S*")
            .expect("parent process normalization regex should compile")
    })
}

fn refresh_epoch_pattern() -> &'static Regex {
    REFRESH_EPOCH.get_or_init(|| {
        Regex::new(r"\bREFRESH_EPOCH=\d+")
            .expect("refresh epoch normalization regex should compile")
    })
}

fn assert_golden(case_name: &str, capture: &Capture, path: &Path) -> Result<(), String> {
    let rendered = format!(
        "{}\n",
        serde_json::to_string_pretty(&capture_json(capture))
            .map_err(|error| format!("render recorded golden: {error}"))?
    );
    if env::var(UPDATE_GOLDENS_ENV).as_deref() == Ok("1") {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).map_err(|error| {
                format!(
                    "create recorded golden directory {}: {error}",
                    parent.display()
                )
            })?;
        }
        fs::write(path, rendered)
            .map_err(|error| format!("update recorded golden {}: {error}", path.display()))?;
        return Ok(());
    }
    let expected = fs::read_to_string(path)
        .map_err(|error| format!("read recorded golden {}: {error}", path.display()))?;
    if expected == rendered {
        Ok(())
    } else {
        Err(format!(
            "golden mismatch in {case_name}: {}; review the recorded result, then rerun with {UPDATE_GOLDENS_ENV}=1",
            path.display()
        ))
    }
}

fn capture_json(capture: &Capture) -> Value {
    let files: BTreeMap<_, _> = capture
        .files
        .iter()
        .map(|(path, contents)| (path, content_json(contents)))
        .collect();
    json!({
        "exit_code": capture.exit_code,
        "stdout": content_json(&capture.stdout),
        "stderr": content_json(&capture.stderr),
        "files": files,
        "side_effects": capture.side_effects,
    })
}

fn content_json(content: &CapturedContent) -> Value {
    match content {
        CapturedContent::Text(text) => json!({"text": text}),
        CapturedContent::Binary(bytes) => json!({"hex": encode_hex(bytes)}),
    }
}

fn encode_hex(bytes: &[u8]) -> String {
    use std::fmt::Write as _;

    let mut encoded = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(encoded, "{byte:02x}").expect("writing to a string cannot fail");
    }
    encoded
}
