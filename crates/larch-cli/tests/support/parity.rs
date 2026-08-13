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

const UPDATE_GOLDENS_ENV: &str = "LARCH_UPDATE_PARITY_GOLDENS";
const PLATFORM_TEMP_ROOT: &str = "/tmp";
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(30);
const DIAGNOSTIC_PATH_LIMIT: usize = 8;
/// A private `flock` inode used only to serialize session activation and
/// cleanup. It is neither a wire artifact nor a command payload, and the
/// frozen Python owner predates it, so black-box parity deliberately excludes
/// this one implementation-detail file while still rejecting a symlink there.
const SESSION_ACTIVITY_LOCK_RELATIVE: &str =
    ".home/.cache/larch/sessions/.larch-session-activity.lock";
/// A private, stable `flock` inode that serializes replacement of the
/// stall-recovery attempt ledger. It has no wire meaning and is deliberately
/// excluded from Python-era parity captures, while ordinary lock files remain
/// observable.
const STALL_RECOVERY_ATTEMPT_LOCK_NAME: &str = ".stall-recovery-attempts.lock";
static RFC3339_UTC: OnceLock<Regex> = OnceLock::new();
static PROCESS_IDENTITY: OnceLock<Regex> = OnceLock::new();
static STATUSLINE_STAMP: OnceLock<Regex> = OnceLock::new();
static CHOOSE_FROM: OnceLock<Regex> = OnceLock::new();
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
}

impl SeedFile {
    pub fn text(relative_path: &str, contents: &str) -> Self {
        Self {
            relative_path: PathBuf::from(relative_path),
            contents: contents.as_bytes().to_vec(),
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
pub struct ParityCase {
    pub name: &'static str,
    pub python: Program,
    pub rust: Program,
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
            .prefix("larch-parity-")
            .tempdir_in(&base)
            .map_err(|error| format!("create parity sandbox: {error}"))?;
        let root = directory
            .path()
            .canonicalize()
            .map_err(|error| format!("canonicalize parity sandbox: {error}"))?;
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
            fs::write(&path, &seed.contents)
                .map_err(|error| format!("write seed {}: {error}", path.display()))?;
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

pub fn assert_case(case: &ParityCase, golden_path: &Path) -> Result<(), String> {
    validate_program(&case.python, "python")?;
    validate_program(&case.rust, "rust")?;
    let python_sandbox = Sandbox::new(&case.seed_files)?;
    let rust_sandbox = Sandbox::new(&case.seed_files)?;
    let record_paths: BTreeSet<PathBuf> = case.side_effect_records.iter().cloned().collect();
    for path in &record_paths {
        validate_relative_path(path)?;
    }

    let python = run_program(&case.python, &python_sandbox, &record_paths)?;
    let rust = run_program(&case.rust, &rust_sandbox, &record_paths)?;
    let python = normalize_capture(python, python_sandbox.root(), &case.normalization);
    let rust = normalize_capture(rust, rust_sandbox.root(), &case.normalization);
    if python != rust {
        return Err(mismatch_diagnostic(case.name, &python, &rust));
    }
    assert_golden(case.name, &python, golden_path)
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
            "parity fixture path must be a confined relative path: {}",
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
        .env("LARCH_PARITY_LIVE_SERVICES", "disabled")
        .env("NO_OPEN_BROWSER", "1")
        .env("NO_PROXY", "")
        .env("PATH", sandbox.root().join(".bin"))
        .env("PYTHONDONTWRITEBYTECODE", "1")
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
        .map_err(|error| format!("launch parity command {}: {error}", executable.display()))?;
    if let Some(input) = stdin {
        child
            .stdin
            .take()
            .ok_or_else(|| "write parity command stdin: pipe unavailable".to_owned())?
            .write_all(input)
            .map_err(|error| format!("write parity command stdin: {error}"))?;
    }
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "capture parity command stdout: pipe unavailable".to_owned())?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| "capture parity command stderr: pipe unavailable".to_owned())?;
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
                "parity command {} timed out after {timeout:?}",
                executable.display()
            ));
        }
        Err(error) => {
            let _ = child.kill();
            let _ = child.wait();
            join_reader(stdout_reader, "stdout")?;
            join_reader(stderr_reader, "stderr")?;
            return Err(format!(
                "wait for parity command {}: {error}",
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
        .map_err(|_| format!("capture parity command {label}: reader thread panicked"))?
        .map_err(|error| format!("capture parity command {label}: {error}"))
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
                "parity command created a forbidden symlink: {}",
                path.display()
            ));
        }
        if metadata.is_dir() {
            capture_directory(root, &path, record_paths, files, side_effects)?;
            continue;
        }
        if !metadata.is_file() {
            return Err(format!(
                "parity command created a non-file artifact: {}",
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
        .ok_or_else(|| format!("parity fixture path is not UTF-8: {}", path.display()))
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

/// Collapse an `argparse` usage block and its indented continuation lines into
/// one logical line.
///
/// `argparse` wraps the `usage:` line to the terminal width, and the wrapping
/// algorithm changed across Python versions: 3.13 keeps an option and its
/// metavar together where earlier versions split them. The Rust CLI mimics one
/// fixed width. The wrapping is therefore presentation that varies with the
/// live Python on the runner, not a behavioral difference, so the parity oracle
/// joins each block into a single line before comparing. This runs
/// unconditionally because usage wrapping is never a meaningful parity signal.
fn collapse_usage_wrapping(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut lines = text.lines().peekable();
    let mut first = true;
    while let Some(line) = lines.next() {
        if !first {
            out.push('\n');
        }
        first = false;
        if let Some(rest) = line.strip_prefix("usage:") {
            out.push_str("usage:");
            out.push_str(rest.trim_end());
            // argparse always separates the usage block from the rest of the
            // message with a blank or unindented line, so consume only indented
            // non-empty continuations.
            while let Some(next) = lines.peek() {
                if next.starts_with(char::is_whitespace) && !next.trim().is_empty() {
                    let continuation = lines.next().unwrap_or_default();
                    out.push(' ');
                    out.push_str(continuation.trim());
                } else {
                    break;
                }
            }
        } else {
            out.push_str(line);
        }
    }
    if text.ends_with('\n') {
        out.push('\n');
    }
    out
}

/// Strip the per-choice quoting inside an `argparse` `(choose from ...)` clause.
///
/// Python 3.13 renders an invalid-choice error as `(choose from a, b)` while
/// earlier versions quote each choice as `(choose from 'a', 'b')`. The Rust CLI
/// mimics the quoted form. Like usage wrapping, this is argparse presentation
/// that varies with the live Python on the runner, so the oracle drops the
/// per-choice quotes before comparing. Only the choice list is rewritten; the
/// quoted invalid value that precedes the clause is left untouched.
fn normalize_choose_from(text: &str) -> String {
    choose_from_pattern()
        .replace_all(text, |captures: &regex::Captures| {
            format!("(choose from {})", captures[1].replace('\'', ""))
        })
        .into_owned()
}

fn choose_from_pattern() -> &'static Regex {
    CHOOSE_FROM.get_or_init(|| {
        Regex::new(r"\(choose from ([^)]*)\)")
            .expect("choose-from normalization regex should compile")
    })
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
            NormalizationRule::ProcessIdentity => process_identity_pattern()
                .replace_all(&normalized, "${1}=<PID>")
                .into_owned(),
            NormalizationRule::StatuslineStamp => statusline_stamp_pattern()
                .replace_all(&normalized, "larch <STAMP>:")
                .into_owned(),
        };
    }
    normalize_choose_from(&collapse_usage_wrapping(&normalized))
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
        Regex::new(r"\b(pid|ppid)=\d+")
            .expect("process identity normalization regex should compile")
    })
}

fn mismatch_diagnostic(case_name: &str, python: &Capture, rust: &Capture) -> String {
    let mut differences = Vec::new();
    if python.exit_code != rust.exit_code {
        differences.push(format!(
            "exit code: python={:?}, rust={:?}",
            python.exit_code, rust.exit_code
        ));
    }
    push_value_difference(&mut differences, "stdout", &python.stdout, &rust.stdout);
    push_value_difference(&mut differences, "stderr", &python.stderr, &rust.stderr);
    push_map_differences(&mut differences, "file", &python.files, &rust.files);
    push_map_differences(
        &mut differences,
        "side effect",
        &python.side_effects,
        &rust.side_effects,
    );
    format!(
        "parity mismatch in {case_name}:\n  {}",
        differences.join("\n  ")
    )
}

fn push_value_difference<T: std::fmt::Debug + PartialEq>(
    differences: &mut Vec<String>,
    label: &str,
    python: &T,
    rust: &T,
) {
    if python != rust {
        differences.push(format!(
            "{label}: python={}, rust={}",
            concise_debug(python),
            concise_debug(rust)
        ));
    }
}

fn push_map_differences<T: std::fmt::Debug + PartialEq>(
    differences: &mut Vec<String>,
    label: &str,
    python: &BTreeMap<String, T>,
    rust: &BTreeMap<String, T>,
) {
    let keys: BTreeSet<_> = python.keys().chain(rust.keys()).collect();
    let mismatches: Vec<_> = keys
        .into_iter()
        .filter(|key| python.get(*key) != rust.get(*key))
        .collect();
    for path in mismatches.iter().take(DIAGNOSTIC_PATH_LIMIT) {
        differences.push(format!(
            "{label} {path}: python={}, rust={}",
            concise_debug(&python.get(*path)),
            concise_debug(&rust.get(*path))
        ));
    }
    if mismatches.len() > DIAGNOSTIC_PATH_LIMIT {
        differences.push(format!(
            "{label}s: {} more mismatched paths omitted",
            mismatches.len() - DIAGNOSTIC_PATH_LIMIT
        ));
    }
}

fn concise(value: &str) -> String {
    const LIMIT: usize = 240;
    let escaped = format!("{value:?}");
    if escaped.chars().count() <= LIMIT {
        return escaped;
    }
    let prefix: String = escaped.chars().take(LIMIT).collect();
    format!("{prefix}...[truncated]")
}

fn concise_debug(value: &impl std::fmt::Debug) -> String {
    concise(&format!("{value:?}"))
}

fn assert_golden(case_name: &str, capture: &Capture, path: &Path) -> Result<(), String> {
    let rendered = format!(
        "{}\n",
        serde_json::to_string_pretty(&capture_json(capture))
            .map_err(|error| format!("render parity golden: {error}"))?
    );
    if env::var(UPDATE_GOLDENS_ENV).as_deref() == Ok("1") {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).map_err(|error| {
                format!(
                    "create parity golden directory {}: {error}",
                    parent.display()
                )
            })?;
        }
        fs::write(path, rendered)
            .map_err(|error| format!("update parity golden {}: {error}", path.display()))?;
        return Ok(());
    }
    let expected = fs::read_to_string(path)
        .map_err(|error| format!("read parity golden {}: {error}", path.display()))?;
    if expected == rendered {
        Ok(())
    } else {
        Err(format!(
            "golden mismatch in {case_name}: {}; review the parity result, then rerun with {UPDATE_GOLDENS_ENV}=1",
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

#[cfg(test)]
mod tests {
    use super::{
        Capture, CapturedContent, NormalizationRule, Program, mismatch_diagnostic, normalize_text,
        validate_program,
    };
    use std::{
        collections::{BTreeMap, BTreeSet},
        fs,
        path::Path,
    };
    use tempfile::tempdir;

    #[test]
    fn capture_tree_excludes_only_named_private_lock_inodes() {
        let directory = tempdir().expect("parity sandbox");
        let root = directory.path();
        let lock = root.join(super::SESSION_ACTIVITY_LOCK_RELATIVE);
        fs::create_dir_all(lock.parent().expect("lock parent")).expect("lock parent");
        fs::write(&lock, "").expect("lock inode");
        fs::write(root.join(super::STALL_RECOVERY_ATTEMPT_LOCK_NAME), "")
            .expect("attempt lock inode");
        let nested = root
            .join("nested")
            .join(super::STALL_RECOVERY_ATTEMPT_LOCK_NAME);
        fs::create_dir_all(nested.parent().expect("nested lock parent"))
            .expect("nested lock parent");
        fs::write(&nested, "").expect("nested attempt lock inode");
        fs::write(root.join("unrelated.lock"), "kept").expect("ordinary artifact");

        let (files, side_effects) =
            super::capture_tree(root, &BTreeSet::new()).expect("capture tree");

        assert!(!files.contains_key(super::SESSION_ACTIVITY_LOCK_RELATIVE));
        assert!(!files.contains_key(super::STALL_RECOVERY_ATTEMPT_LOCK_NAME));
        assert!(!files.contains_key("nested/.stall-recovery-attempts.lock"));
        assert_eq!(
            files.get("unrelated.lock"),
            Some(&super::CapturedContent::Text("kept".to_owned()))
        );
        assert!(side_effects.is_empty());
    }

    #[test]
    fn normalization_replaces_only_named_nondeterminism() {
        let normalized = normalize_text(
            "/tmp/case/out at 2026-07-18T21:05:07.123Z; keep 2026-07-18",
            Path::new("/tmp/case"),
            &[
                NormalizationRule::SandboxRoot,
                NormalizationRule::Rfc3339Utc,
            ],
        );

        assert_eq!(normalized, "<SANDBOX>/out at <TIMESTAMP>; keep 2026-07-18");
    }

    #[test]
    fn process_identity_normalization_survives_both_pid_spellings() {
        let normalized = normalize_text(
            "2026-08-05T00:00:00Z pid=91 ppid=7 parent=? dir=/tmp/case/session",
            Path::new("/tmp/case"),
            &[
                NormalizationRule::SandboxRoot,
                NormalizationRule::Rfc3339Utc,
                NormalizationRule::ProcessIdentity,
            ],
        );

        assert_eq!(
            normalized,
            "<TIMESTAMP> pid=<PID> ppid=<PID> parent=? dir=<SANDBOX>/session"
        );
    }

    #[test]
    fn live_service_credentials_cannot_be_reintroduced() {
        for credential in ["LARCH_GH_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"] {
            let program = Program::new("/bin/fixture").env(credential, "secret");
            let error =
                validate_program(&program, "python").expect_err("credential must be blocked");

            assert!(error.contains(credential));
            assert!(error.contains("fixture service"));
        }
    }

    #[test]
    fn mismatch_diagnostic_names_channels_and_bounds_values() {
        let python = Capture {
            exit_code: Some(2),
            stdout: CapturedContent::Text("p".repeat(300)),
            stderr: CapturedContent::Text(String::new()),
            files: (0..10)
                .map(|index| {
                    (
                        format!("result-{index}.txt"),
                        CapturedContent::Text("python".to_owned()),
                    )
                })
                .collect(),
            side_effects: BTreeMap::new(),
        };
        let rust = Capture {
            exit_code: Some(65),
            stdout: CapturedContent::Text("r".repeat(300)),
            stderr: CapturedContent::Text("malformed".to_owned()),
            files: BTreeMap::new(),
            side_effects: BTreeMap::new(),
        };

        let diagnostic = mismatch_diagnostic("fixture", &python, &rust);

        assert!(diagnostic.starts_with("parity mismatch in fixture:"));
        assert!(diagnostic.contains("exit code:"));
        assert!(diagnostic.contains("stdout:"));
        assert!(diagnostic.contains("stderr:"));
        assert!(diagnostic.contains("file result-0.txt:"));
        assert!(diagnostic.contains("files: 2 more mismatched paths omitted"));
        assert!(diagnostic.contains("[truncated]"));
    }

    #[test]
    fn non_utf8_streams_stay_byte_exact() {
        let content = super::captured_content(vec![0, 255]);

        assert_eq!(content, CapturedContent::Binary(vec![0, 255]));
        assert_eq!(
            super::content_json(&content),
            serde_json::json!({"hex": "00ff"})
        );
    }
}
