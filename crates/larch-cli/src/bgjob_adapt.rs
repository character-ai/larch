//! Rust-owned `bgjob adapt` compatibility boundary.
//!
//! The daemon, wait, status, and reap commands remain Python-owned during the
//! staged migration. This command owns the durable decision, registry, and
//! reattachment protocol and invokes only the retained Python `bgjob start`
//! seam to create the daemon process.

use larch_adapters::{
    SystemProcessIdentityHost, validate_design_tmpdir as validate_session_tmpdir,
};
use larch_core::{
    BGJOB_INPUT_FP_SUFFIX, BGJOB_RC_KEY, BGJOB_STATUS_DONE, BGJOB_STATUS_KEY, BGJOB_STATUS_STARTED,
    BgjobError, JobSpec, KvDocument, LivenessVerdict, MalformedLinePolicy, OwnerIdentity,
    ParseOptions, RegistryEntry, bgjob_dir, checked_dir, child_liveness,
    cleanup_cache_sessions_root, daemon_liveness, default_run_id, ensure_under, entry_expired,
    log_paths, parse_allowlisted_env_line, private_atomic_write, read_entry, read_process_identity,
    registry_path, registry_root, result_env_path, validate_initial_merge_rows,
    validate_merge_result_env, validate_run_id, validate_slug,
};
use std::{
    collections::BTreeMap,
    env,
    ffi::{OsStr, OsString},
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::{Command, ExitCode},
};

#[cfg(unix)]
use nix::{
    errno::Errno,
    fcntl::{AtFlags, FlockArg, OFlag, open, openat},
    sys::stat::{Mode, SFlag, fchmod, fstat, fstatat},
    unistd::{UnlinkatFlags, unlinkat},
};
#[cfg(unix)]
use std::os::{
    fd::{AsRawFd as _, OwnedFd},
    unix::fs::MetadataExt as _,
};

#[cfg(unix)]
#[allow(deprecated)]
use nix::fcntl::flock;

const DESIGN_SESSION_ENV_KEYS: &[&str] = &[
    "DESIGN_TMPDIR",
    "SESSION_TMPDIR",
    "SESSION_ID",
    "REPO",
    "REPO_ROOT",
    "ISSUE_NUMBER",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT",
    "CLAUDE_PLUGIN_ROOT",
    "LARCH_CLAUDE_SOURCE_FILE",
    "LARCH_RUN_ID",
    "LARCH_LIVE_MUTATION_OK",
];

#[derive(Clone, Debug, Default)]
struct ParsedArguments {
    step: String,
    tmpdir: String,
    run_id: String,
    budget_s: Option<i64>,
    log_dir: String,
    owner_pid: String,
    sentinels: Vec<String>,
    session_env_path: String,
    clear_on_fresh: String,
    replace_completed_result: bool,
    input_fingerprint: String,
    merge_result_env: String,
    initial_merge_rows: Vec<(String, String)>,
    command: Vec<String>,
}

#[derive(Clone, Debug, Default)]
struct AdaptOptions {
    clear_on_fresh: Option<PathBuf>,
    replace_completed_result: bool,
    input_fingerprint: String,
}

#[derive(Clone, Debug, Default)]
struct SessionValues {
    rows: Vec<(String, String)>,
}

impl SessionValues {
    fn get(&self, key: &str) -> Option<&str> {
        self.rows
            .iter()
            .find(|(candidate, _)| candidate == key)
            .map(|(_, value)| value.as_str())
    }

    fn insert(&mut self, key: String, value: String) {
        if let Some((_, existing)) = self
            .rows
            .iter_mut()
            .find(|(candidate, _)| candidate == &key)
        {
            *existing = value;
        } else {
            self.rows.push((key, value));
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct RegistrySnapshot {
    path: PathBuf,
    entry: Option<RegistryEntry>,
    fingerprint: Option<FileFingerprint>,
    invalid: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ProcessState {
    live: bool,
    proven_dead: bool,
    identity_mismatch: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct FileFingerprint {
    device: u64,
    inode: u64,
    modified_ns: i128,
    size: u64,
}

#[derive(Debug)]
struct DecisionError {
    token: &'static str,
    completed_output: Option<String>,
}

type DecisionResult<T> = Result<T, DecisionError>;

impl DecisionError {
    const fn token(token: &'static str) -> Self {
        Self {
            token,
            completed_output: None,
        }
    }

    const fn done(output: String) -> Self {
        Self {
            token: "result-emitted",
            completed_output: Some(output),
        }
    }
}

/// Run the Rust-owned adapter and preserve its `BGJOB_*` stdout grammar.
pub fn adapt(arguments: &[OsString]) -> ExitCode {
    if has_top_level_option(arguments, "--resolve-session-env") {
        return resolve_session_env_argv(arguments);
    }
    if has_top_level_option(arguments, "-h") || has_top_level_option(arguments, "--help") {
        print_help();
        return ExitCode::SUCCESS;
    }
    let parsed = match parse_arguments(arguments) {
        Ok(parsed) => parsed,
        Err(token) => return error(token),
    };
    let result = build_request(parsed).and_then(|(spec, options, session_values, owner_pid)| {
        let root = registry_root().map_err(|_| DecisionError::token("registry-failed"))?;
        let cwd = env::current_dir()
            .and_then(fs::canonicalize)
            .map_err(|_| DecisionError::token("invalid-input"))?;
        let host = SystemAdapterHost::new();
        let owner_pid = host.validated_owner_pid(&owner_pid)?;
        run_with_host(&host, &root, &cwd, spec, options, session_values, owner_pid)
    });
    match result {
        Ok(output) => write_stdout(&output),
        Err(decision_error) => error(decision_error.token),
    }
}

fn has_top_level_option(arguments: &[OsString], option: &str) -> bool {
    arguments
        .iter()
        .take_while(|argument| argument.as_os_str() != OsStr::new("--"))
        .any(|argument| argument.as_os_str() == OsStr::new(option))
}

fn print_help() {
    println!(
        "usage: bgjob adapt --step STEP [--tmpdir PATH] --budget-s SECONDS [options] -- COMMAND..."
    );
}

fn error(token: &str) -> ExitCode {
    std::io::stdout()
        .write_all(format!("BGJOB_ERROR={token}\n").as_bytes())
        .map_or(ExitCode::FAILURE, |()| ExitCode::from(2))
}

fn write_stdout(value: &str) -> ExitCode {
    std::io::stdout()
        .write_all(value.as_bytes())
        .map_or(ExitCode::FAILURE, |()| ExitCode::SUCCESS)
}

fn parse_arguments(arguments: &[OsString]) -> Result<ParsedArguments, &'static str> {
    let values = arguments
        .iter()
        .map(|argument| argument.to_str().map(str::to_owned).ok_or("invalid-input"))
        .collect::<Result<Vec<_>, _>>()?;
    let mut parsed = ParsedArguments::default();
    let mut index = 0;
    let mut command_mode = false;
    while index < values.len() {
        let value = &values[index];
        if command_mode {
            parsed.command.push(value.clone());
            index += 1;
            continue;
        }
        if value == "--" {
            command_mode = true;
            index += 1;
            continue;
        }
        if !value.starts_with('-') {
            command_mode = true;
            parsed.command.push(value.clone());
            index += 1;
            continue;
        }
        let (name, inline) = split_option(value);
        match name {
            "--step" => parsed.step = option_value(&values, &mut index, inline)?,
            "--tmpdir" => parsed.tmpdir = option_value(&values, &mut index, inline)?,
            "--run-id" => parsed.run_id = option_value(&values, &mut index, inline)?,
            "--budget-s" => {
                let raw = option_value(&values, &mut index, inline)?;
                parsed.budget_s = raw.parse::<i64>().ok();
                if parsed.budget_s.is_none() {
                    return Err("invalid-input");
                }
            }
            "--log-dir" => parsed.log_dir = option_value(&values, &mut index, inline)?,
            "--owner-pid" => parsed.owner_pid = option_value(&values, &mut index, inline)?,
            "--sentinel" => parsed
                .sentinels
                .push(option_value(&values, &mut index, inline)?),
            "--session-env-path" => {
                parsed.session_env_path = option_value(&values, &mut index, inline)?;
            }
            "--clear-on-fresh" => {
                parsed.clear_on_fresh = option_value(&values, &mut index, inline)?;
            }
            "--input-fingerprint" => {
                parsed.input_fingerprint = option_value(&values, &mut index, inline)?;
            }
            "--merge-result-env" => {
                parsed.merge_result_env = option_value(&values, &mut index, inline)?;
            }
            "--initial-merge-row" => {
                let row = option_value(&values, &mut index, inline)?;
                parsed
                    .initial_merge_rows
                    .push(parse_single_kv_row(&row).ok_or("invalid-input")?);
            }
            "--replace-completed-result" if inline.is_none() => {
                parsed.replace_completed_result = true;
            }
            _ => return Err("invalid-input"),
        }
        index += 1;
    }
    if parsed.command.is_empty() {
        return Err("missing-command");
    }
    if parsed.budget_s.is_none() {
        return Err("invalid-input");
    }
    if parsed.budget_s.is_some_and(|value| value <= 0) {
        return Err("invalid-budget");
    }
    Ok(parsed)
}

fn split_option(value: &str) -> (&str, Option<&str>) {
    value.find('=').map_or((value, None), |position| {
        (&value[..position], Some(&value[position + 1..]))
    })
}

fn parse_single_kv_row(value: &str) -> Option<(String, String)> {
    if value.contains(['\n', '\r']) {
        return None;
    }
    let document = KvDocument::parse(value, ParseOptions::legacy()).ok()?;
    let [row] = document.rows() else {
        return None;
    };
    Some((row.key().to_owned(), row.value().to_owned()))
}

fn option_value(
    values: &[String],
    index: &mut usize,
    inline: Option<&str>,
) -> Result<String, &'static str> {
    if let Some(value) = inline {
        return Ok(value.to_owned());
    }
    *index += 1;
    values.get(*index).cloned().ok_or("invalid-input")
}

fn build_request(
    parsed: ParsedArguments,
) -> DecisionResult<(JobSpec, AdaptOptions, SessionValues, String)> {
    let session_values = if parsed.session_env_path.is_empty() {
        SessionValues::default()
    } else {
        resolve_session_env(Path::new(&parsed.session_env_path), &parsed.owner_pid)?
    };
    let tmpdir = resolve_tmpdir(&parsed.tmpdir, &session_values)?;
    let step =
        validate_slug(&parsed.step, "step").map_err(|_| DecisionError::token("invalid-input"))?;
    let cwd = env::current_dir()
        .and_then(fs::canonicalize)
        .map_err(|_| DecisionError::token("invalid-input"))?;
    let run_id = resolve_run_id(&parsed.run_id, &tmpdir, &cwd);
    let log_dir = (!parsed.log_dir.is_empty()).then(|| Path::new(&parsed.log_dir));
    let (log_dir, _, _) =
        log_paths(&tmpdir, log_dir, &step).map_err(|_| DecisionError::token("invalid-input"))?;
    let sentinels = parsed
        .sentinels
        .iter()
        .map(|path| ensure_under(Path::new(path), &tmpdir, "sentinel"))
        .collect::<Result<Vec<_>, BgjobError>>()
        .map_err(|_| DecisionError::token("invalid-input"))?;
    let spec = JobSpec {
        step,
        tmpdir,
        log_dir,
        budget_s: parsed.budget_s.expect("validated budget"),
        command: parsed.command,
        run_id,
        owner: OwnerIdentity { recorded: None },
        sentinel_paths: sentinels,
        merge_result_env: (!parsed.merge_result_env.is_empty())
            .then(|| PathBuf::from(parsed.merge_result_env)),
        initial_merge_rows: parsed.initial_merge_rows,
    };
    let options = AdaptOptions {
        clear_on_fresh: (!parsed.clear_on_fresh.is_empty())
            .then(|| PathBuf::from(parsed.clear_on_fresh)),
        replace_completed_result: parsed.replace_completed_result,
        input_fingerprint: parsed.input_fingerprint,
    };
    Ok((spec, options, session_values, parsed.owner_pid))
}

fn resolve_tmpdir(raw: &str, session_values: &SessionValues) -> DecisionResult<PathBuf> {
    let session_tmpdir = session_values.get("DESIGN_TMPDIR").unwrap_or("");
    if !raw.is_empty()
        && !session_tmpdir.is_empty()
        && canonical_or_absolute(Path::new(raw)) != canonical_or_absolute(Path::new(session_tmpdir))
    {
        return Err(DecisionError::token("session-env-tmpdir-mismatch"));
    }
    let design_tmpdir = env::var("DESIGN_TMPDIR").unwrap_or_default();
    let implement_tmpdir = env::var("IMPLEMENT_TMPDIR").unwrap_or_default();
    let selected = [raw, session_tmpdir, &design_tmpdir, &implement_tmpdir]
        .into_iter()
        .find(|value| !value.is_empty())
        .ok_or_else(|| DecisionError::token("missing-tmpdir"))?;
    checked_dir(Path::new(selected), "tmpdir", true)
        .map_err(|_| DecisionError::token("invalid-input"))
}

fn resolve_run_id(explicit: &str, tmpdir: &Path, cwd: &Path) -> String {
    let mut candidates = vec![
        explicit.to_owned(),
        env::var("LARCH_RUN_ID").unwrap_or_default(),
    ];
    for name in ["session-env.sh", "source-env.sh"] {
        let path = tmpdir.join(name);
        if let Ok(text) = fs::read_to_string(path) {
            candidates.extend(text.lines().filter_map(run_id_from_line));
        }
    }
    candidates
        .into_iter()
        .find_map(|candidate| validate_run_id(&candidate).ok())
        .unwrap_or_else(|| default_run_id(tmpdir, cwd))
}

fn run_id_from_line(line: &str) -> Option<String> {
    ["LARCH_RUN_ID=", "export LARCH_RUN_ID="]
        .iter()
        .find_map(|prefix| line.strip_prefix(prefix))
        .map(|raw| raw.trim().trim_matches(['\'', '"']).to_owned())
}

fn canonical_or_absolute(path: &Path) -> PathBuf {
    fs::canonicalize(path).unwrap_or_else(|_| {
        if path.is_absolute() {
            path.to_path_buf()
        } else {
            env::current_dir().map_or_else(|_| path.to_path_buf(), |cwd| cwd.join(path))
        }
    })
}

fn resolve_session_env_argv(arguments: &[OsString]) -> ExitCode {
    let values = match parse_resolver_arguments(arguments) {
        Ok((path, owner_pid)) => resolve_session_env(&path, &owner_pid),
        Err(token) => return error(token),
    };
    match values {
        Ok(values) => {
            let mut output = String::new();
            for (key, value) in values.rows {
                output.push_str("export ");
                output.push_str(&key);
                output.push('=');
                output.push_str(&shell_quote(&value));
                output.push('\n');
            }
            write_stdout(&output)
        }
        Err(decision_error) => error(decision_error.token),
    }
}

fn parse_resolver_arguments(arguments: &[OsString]) -> Result<(PathBuf, String), &'static str> {
    let values = arguments
        .iter()
        .map(|argument| argument.to_str().map(str::to_owned).ok_or("invalid-input"))
        .collect::<Result<Vec<_>, _>>()?;
    let mut path = String::new();
    let mut owner_pid = String::new();
    let mut resolved = false;
    let mut index = 0;
    while index < values.len() {
        let (name, inline) = split_option(&values[index]);
        match name {
            "--resolve-session-env" if inline.is_none() => resolved = true,
            "--session-env-path" => path = option_value(&values, &mut index, inline)?,
            "--owner-pid" => owner_pid = option_value(&values, &mut index, inline)?,
            _ => return Err("invalid-input"),
        }
        index += 1;
    }
    if !resolved || path.is_empty() {
        return Err("invalid-input");
    }
    Ok((PathBuf::from(path), owner_pid))
}

fn resolve_session_env(path: &Path, owner_pid: &str) -> DecisionResult<SessionValues> {
    let source = session_env_source(path, owner_pid)?;
    let text =
        fs::read_to_string(&source).map_err(|_| DecisionError::token("session-env-unsafe"))?;
    let mut values = SessionValues::default();
    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') || line == "#!/usr/bin/env bash" {
            continue;
        }
        let Some((key, value)) =
            parse_allowlisted_env_line(line, DESIGN_SESSION_ENV_KEYS, None, true)
        else {
            return Err(DecisionError::token("session-env-malformed"));
        };
        if key != "CLAUDE_PLUGIN_ROOT" {
            values.insert(key, value);
        }
    }
    let raw_tmpdir = values.get("DESIGN_TMPDIR").unwrap_or("");
    if raw_tmpdir.is_empty() {
        return Err(DecisionError::token("design-tmpdir-missing"));
    }
    let tmpdir = validate_design_tmpdir(raw_tmpdir)?;
    values.insert("DESIGN_TMPDIR".to_owned(), tmpdir.display().to_string());
    Ok(values)
}

fn session_env_source(path: &Path, owner_pid: &str) -> DecisionResult<PathBuf> {
    let metadata = fs::symlink_metadata(path).map_err(|error| {
        if error.kind() == std::io::ErrorKind::NotFound {
            DecisionError::token("session-env-missing")
        } else {
            DecisionError::token("session-env-unsafe")
        }
    })?;
    if !metadata.file_type().is_symlink() {
        return metadata
            .is_file()
            .then(|| path.to_path_buf())
            .ok_or_else(|| DecisionError::token("session-env-missing"));
    }
    if !valid_owner_pid(owner_pid) || !trusted_session_link(path, owner_pid) {
        return Err(DecisionError::token("session-env-unsafe"));
    }
    fs::canonicalize(path)
        .ok()
        .filter(|resolved| {
            fs::symlink_metadata(resolved)
                .is_ok_and(|target| target.is_file() && !target.file_type().is_symlink())
        })
        .ok_or_else(|| DecisionError::token("session-env-unsafe"))
}

fn valid_owner_pid(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 7
        && value.bytes().next().is_some_and(|byte| byte != b'0')
        && value.bytes().all(|byte| byte.is_ascii_digit())
}

fn trusted_session_link(path: &Path, owner_pid: &str) -> bool {
    let Some(home) = env::var_os("HOME") else {
        return false;
    };
    let expected = PathBuf::from(home)
        .join(".cache/larch/sessions")
        .join(format!("current-design-env-{owner_pid}.sh"));
    if path != expected {
        return false;
    }
    let Some(mut ancestor) = path.parent() else {
        return false;
    };
    loop {
        if fs::symlink_metadata(ancestor).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
            return false;
        }
        match ancestor.parent() {
            Some(parent) if parent != ancestor => ancestor = parent,
            _ => return true,
        }
    }
}

fn validate_design_tmpdir(raw: &str) -> DecisionResult<PathBuf> {
    let xdg_cache_home = env::var_os("XDG_CACHE_HOME");
    let home = env::var_os("HOME");
    let tmpdir = env::var_os("TMPDIR");
    let cache_root = cleanup_cache_sessions_root(xdg_cache_home.as_deref(), home.as_deref());
    validate_session_tmpdir(raw, tmpdir.as_deref(), &cache_root)
        .map_err(|_| DecisionError::token("design-tmpdir-invalid"))?;
    let resolved =
        fs::canonicalize(raw).map_err(|_| DecisionError::token("design-tmpdir-invalid"))?;
    fs::metadata(&resolved)
        .is_ok_and(|metadata| metadata.is_dir())
        .then_some(resolved)
        .ok_or_else(|| DecisionError::token("design-tmpdir-invalid"))
}

fn shell_quote(value: &str) -> String {
    if !value.is_empty()
        && value.bytes().all(|byte| {
            byte.is_ascii_alphanumeric()
                || matches!(
                    byte,
                    b'_' | b'@' | b'%' | b'+' | b'=' | b':' | b',' | b'.' | b'/' | b'-'
                )
        })
    {
        return value.to_owned();
    }
    format!("'{}'", value.replace('\'', "'\"'\"'"))
}

trait AdapterHost {
    fn daemon_liveness(&self, entry: &RegistryEntry) -> LivenessVerdict;
    fn child_liveness(&self, entry: &RegistryEntry) -> LivenessVerdict;
    fn plugin_root(&self, tmpdir: &Path) -> DecisionResult<PathBuf>;
    fn start(&self, request: &StartRequest) -> DecisionResult<String>;
}

struct SystemAdapterHost {
    identity_host: SystemProcessIdentityHost,
}

impl SystemAdapterHost {
    fn new() -> Self {
        Self {
            identity_host: SystemProcessIdentityHost::new(),
        }
    }

    fn validated_owner_pid(&self, raw: &str) -> DecisionResult<String> {
        let candidates = [
            raw.to_owned(),
            env::var("LARCH_BGJOB_OWNER_PID").unwrap_or_default(),
            env::var("LARCH_CLAUDE_PID").unwrap_or_default(),
            env::var("CLAUDE_PID").unwrap_or_default(),
        ];
        let candidate = candidates
            .into_iter()
            .find(|value| !value.is_empty())
            .ok_or_else(|| DecisionError::token("invalid-input"))?;
        let pid = candidate
            .parse::<i32>()
            .map_err(|_| DecisionError::token("invalid-input"))?;
        read_process_identity(&self.identity_host, pid, "")
            .is_some()
            .then_some(candidate)
            .ok_or_else(|| DecisionError::token("invalid-input"))
    }
}

impl AdapterHost for SystemAdapterHost {
    fn daemon_liveness(&self, entry: &RegistryEntry) -> LivenessVerdict {
        daemon_liveness(&self.identity_host, entry)
    }

    fn child_liveness(&self, entry: &RegistryEntry) -> LivenessVerdict {
        child_liveness(&self.identity_host, entry)
    }

    fn plugin_root(&self, tmpdir: &Path) -> DecisionResult<PathBuf> {
        rehydrate_plugin_root(tmpdir)
    }

    fn start(&self, request: &StartRequest) -> DecisionResult<String> {
        let output = python_start_command(request)
            .output()
            .map_err(|_| DecisionError::token("daemon-start-exception"))?;
        if !output.status.success() {
            return Err(DecisionError::token("daemon-start-failed"));
        }
        let stdout = String::from_utf8(output.stdout)
            .map_err(|_| DecisionError::token("daemon-start-failed"))?;
        validate_started_stdout(stdout, &request.spec.step)
    }
}

fn python_start_command(request: &StartRequest) -> Command {
    let mut command = Command::new("python3"); // lint-subprocess-via-runner: ok retained Python-owned bgjob start compatibility seam until #8063
    command
        .arg(request.plugin_root.join("python/cli.py"))
        .arg("bgjob")
        .arg("start")
        .arg("--step")
        .arg(&request.spec.step)
        .arg("--tmpdir")
        .arg(&request.spec.tmpdir)
        .arg("--run-id")
        .arg(&request.spec.run_id)
        .arg("--budget-s")
        .arg(request.spec.budget_s.to_string())
        .arg("--log-dir")
        .arg(&request.spec.log_dir)
        .env("CLAUDE_PLUGIN_ROOT", &request.plugin_root);
    for (key, value) in &request.session_values.rows {
        command.env(key, value);
    }
    if !request.owner_pid.is_empty() {
        command.arg("--owner-pid").arg(&request.owner_pid);
    }
    for sentinel in &request.spec.sentinel_paths {
        command.arg("--sentinel").arg(sentinel);
    }
    if let Some(merge_result_env) = &request.spec.merge_result_env {
        command.arg("--merge-result-env").arg(merge_result_env);
    }
    command.arg("--").args(&request.spec.command);
    command
}

fn validate_started_stdout(stdout: String, step: &str) -> DecisionResult<String> {
    if !stdout.starts_with(&format!(
        "{BGJOB_STATUS_KEY}={BGJOB_STATUS_STARTED} STEP={step} PGID="
    )) {
        return Err(DecisionError::token("daemon-start-failed"));
    }
    Ok(stdout)
}

#[derive(Clone, Debug)]
struct StartRequest {
    spec: JobSpec,
    plugin_root: PathBuf,
    session_values: SessionValues,
    owner_pid: String,
}

struct Adapter<'a, Host: AdapterHost> {
    host: &'a Host,
    registry_root: &'a Path,
    cwd: &'a Path,
    spec: JobSpec,
    options: AdaptOptions,
    session_values: SessionValues,
    owner_pid: String,
}

fn run_with_host<Host: AdapterHost>(
    host: &Host,
    registry_root: &Path,
    cwd: &Path,
    spec: JobSpec,
    options: AdaptOptions,
    session_values: SessionValues,
    owner_pid: String,
) -> DecisionResult<String> {
    let _lock = DecisionLock::open(registry_root, &spec.run_id, &spec.step)?;
    let adapter = Adapter {
        host,
        registry_root,
        cwd,
        spec,
        options,
        session_values,
        owner_pid,
    };
    match adapter.decide() {
        Ok(output) => Ok(output),
        Err(error) => match error.completed_output {
            Some(output) => Ok(output),
            None => Err(error),
        },
    }
}

impl<Host: AdapterHost> Adapter<'_, Host> {
    fn decide(&self) -> DecisionResult<String> {
        let mut completed = self.read_completed_result()?;
        if completed.is_some() && !self.options.replace_completed_result {
            if self.completed_is_stale()? {
                self.invalidate_completed_result()?;
                completed = None;
            } else if let Some(output) = completed {
                return Ok(output);
            }
        }
        let mut snapshot = self.snapshot_registry()?;
        if self.options.replace_completed_result {
            self.replacement_registry_check(&snapshot)?;
            snapshot = self.snapshot_registry()?;
        }
        if completed.is_some() {
            self.invalidate_completed_result()?;
            snapshot = self.snapshot_registry()?;
        }
        if snapshot.invalid {
            return Err(DecisionError::token("registry-invalid"));
        }
        let Some(entry) = snapshot.entry.clone() else {
            self.raise_if_result()?;
            return self.start_fresh();
        };
        self.validate_entry(&entry)?;
        let daemon_state = process_state(&self.host.daemon_liveness(&entry));
        let child_state = process_state(&self.host.child_liveness(&entry));
        if entry_expired(&entry) {
            return self.handle_expired(&snapshot, daemon_state, child_state);
        }
        self.handle_active(&snapshot, &entry, daemon_state, child_state)
    }

    fn read_completed_result(&self) -> DecisionResult<Option<String>> {
        let root = bgjob_dir(&self.spec.tmpdir).map_err(|_| DecisionError::token("unsafe-path"))?;
        let result = result_env_path(&self.spec.tmpdir, &self.spec.step)
            .map_err(|_| DecisionError::token("unsafe-path"))?;
        let Some(text) = read_trusted_regular(&result, &root)? else {
            return Ok(None);
        };
        let rows = parse_completed_rows(&text, &self.spec.step);
        Ok(rows.map(|rows| format_done(&rows)))
    }

    fn snapshot_registry(&self) -> DecisionResult<RegistrySnapshot> {
        let path = registry_path(&self.spec.run_id, &self.spec.step, Some(self.registry_root))
            .map_err(|_| DecisionError::token("registry-failed"))?;
        let Ok(before) = stat_fingerprint(&path) else {
            return Ok(RegistrySnapshot {
                path,
                entry: None,
                fingerprint: None,
                invalid: true,
            });
        };
        let Some(before) = before else {
            return Ok(RegistrySnapshot {
                path,
                entry: None,
                fingerprint: None,
                invalid: false,
            });
        };
        let entry = read_entry(&path);
        let after = stat_fingerprint(&path).unwrap_or_default();
        if entry.is_none() || after.as_ref() != Some(&before) {
            return Ok(RegistrySnapshot {
                path,
                entry: None,
                fingerprint: after,
                invalid: true,
            });
        }
        Ok(RegistrySnapshot {
            path,
            entry,
            fingerprint: after,
            invalid: false,
        })
    }

    fn validate_entry(&self, entry: &RegistryEntry) -> DecisionResult<()> {
        let expected_result = result_env_path(&self.spec.tmpdir, &self.spec.step)
            .map_err(|_| DecisionError::token("registry-invalid"))?;
        let matches = entry.step == self.spec.step
            && entry.run_id == self.spec.run_id
            && entry.tmpdir == self.spec.tmpdir
            && entry.clone_path == self.cwd
            && entry.result_env == expected_result;
        if !matches {
            return Err(DecisionError::token("registry-identity-mismatch"));
        }
        let valid_identity = |identity: &larch_core::RecordedProcessIdentity| {
            identity.pid > 0
                && identity.pgid > 0
                && !identity.start_time.is_empty()
                && !identity.command_signature.is_empty()
        };
        if entry.start_epoch <= 0
            || entry.budget_s <= 0
            || !valid_identity(&entry.daemon)
            || !valid_identity(&entry.child)
        {
            return Err(DecisionError::token("registry-invalid"));
        }
        Ok(())
    }

    fn verify_same_snapshot(
        &self,
        previous: &RegistrySnapshot,
    ) -> DecisionResult<RegistrySnapshot> {
        let current = self.snapshot_registry()?;
        if current.invalid
            || current.fingerprint != previous.fingerprint
            || current.entry != previous.entry
        {
            self.raise_if_result()?;
            return Err(DecisionError::token("registry-replaced"));
        }
        Ok(current)
    }

    fn clear_expired(&self, snapshot: &RegistrySnapshot) -> DecisionResult<()> {
        self.raise_if_result()?;
        let current = self.verify_same_snapshot(snapshot)?;
        self.raise_if_result()?;
        let current = self.verify_same_snapshot(&current)?;
        unlink_regular_under(&current.path, self.registry_root, "registry-clear-failed")
    }

    fn clear_verified_dead_registry(&self, snapshot: &RegistrySnapshot) -> DecisionResult<()> {
        let current = self.verify_same_snapshot(snapshot)?;
        unlink_regular_under(&current.path, self.registry_root, "registry-clear-failed")
    }

    fn handle_expired(
        &self,
        snapshot: &RegistrySnapshot,
        daemon_state: ProcessState,
        child_state: ProcessState,
    ) -> DecisionResult<String> {
        if daemon_state.live || child_state.live {
            return Err(DecisionError::token("expired-live"));
        }
        if !daemon_state.proven_dead || !child_state.proven_dead {
            return Err(DecisionError::token("registry-identity-unverifiable"));
        }
        self.clear_expired(snapshot)?;
        if let Some(output) = self.read_completed_result()? {
            return Ok(output);
        }
        self.start_fresh()
    }

    fn handle_active(
        &self,
        snapshot: &RegistrySnapshot,
        entry: &RegistryEntry,
        daemon_state: ProcessState,
        child_state: ProcessState,
    ) -> DecisionResult<String> {
        if !daemon_state.live {
            if child_state.live {
                return Err(DecisionError::token("registry-ownership-lost"));
            }
            if !daemon_state.proven_dead || !child_state.proven_dead {
                return Err(DecisionError::token("registry-identity-unverifiable"));
            }
            return Err(DecisionError::token("registry-dead"));
        }
        if !child_state.live && child_state.identity_mismatch {
            return Err(DecisionError::token("registry-identity-unverifiable"));
        }
        if let Some(output) = self.read_completed_result()? {
            return Ok(output);
        }
        let _ = self.verify_same_snapshot(snapshot)?;
        Ok(format!(
            "{BGJOB_STATUS_KEY}={BGJOB_STATUS_STARTED} STEP={} PGID={}\n",
            self.spec.step, entry.child.pgid
        ))
    }

    fn replacement_registry_check(&self, snapshot: &RegistrySnapshot) -> DecisionResult<()> {
        if snapshot.invalid {
            return Err(DecisionError::token("registry-invalid"));
        }
        let Some(entry) = &snapshot.entry else {
            return Ok(());
        };
        self.validate_entry(entry)?;
        let daemon_state = process_state(&self.host.daemon_liveness(entry));
        let child_state = process_state(&self.host.child_liveness(entry));
        if daemon_state.live || child_state.live {
            return Err(DecisionError::token("replace-active"));
        }
        if !daemon_state.proven_dead || !child_state.proven_dead {
            return Err(DecisionError::token("registry-identity-unverifiable"));
        }
        self.clear_verified_dead_registry(snapshot)
    }

    fn completed_is_stale(&self) -> DecisionResult<bool> {
        if self.options.input_fingerprint.is_empty() {
            return Ok(false);
        }
        Ok(self.read_stored_input_fingerprint()? != self.options.input_fingerprint)
    }

    fn read_stored_input_fingerprint(&self) -> DecisionResult<String> {
        let root = bgjob_dir(&self.spec.tmpdir).map_err(|_| DecisionError::token("unsafe-path"))?;
        let path = root.join(format!("{}{}", self.spec.step, BGJOB_INPUT_FP_SUFFIX));
        match read_trusted_regular(&path, &root) {
            Ok(Some(text)) => Ok(text.trim().to_owned()),
            Ok(None) | Err(_) => Ok(String::new()),
        }
    }

    fn write_input_fingerprint(&self) -> DecisionResult<()> {
        if self.options.input_fingerprint.is_empty() {
            return Ok(());
        }
        let root = bgjob_dir(&self.spec.tmpdir)
            .map_err(|_| DecisionError::token("input-fp-write-failed"))?;
        let path = root.join(format!("{}{}", self.spec.step, BGJOB_INPUT_FP_SUFFIX));
        private_atomic_write(
            &path,
            &format!("{}\n", self.options.input_fingerprint),
            &root,
        )
        .map_err(|_| DecisionError::token("input-fp-write-failed"))
    }

    fn invalidate_completed_result(&self) -> DecisionResult<()> {
        let root = bgjob_dir(&self.spec.tmpdir).map_err(|_| DecisionError::token("unsafe-path"))?;
        let path = result_env_path(&self.spec.tmpdir, &self.spec.step)
            .map_err(|_| DecisionError::token("unsafe-path"))?;
        match read_trusted_regular(&path, &root)? {
            Some(_) => unlink_regular_under(&path, &self.spec.tmpdir, "result-clear-failed"),
            None => Ok(()),
        }
    }

    fn start_fresh(&self) -> DecisionResult<String> {
        let plugin_root = self.host.plugin_root(&self.spec.tmpdir)?;
        if let Some(output) = self.read_completed_result()? {
            return Ok(output);
        }
        let final_registry = self.snapshot_registry()?;
        if final_registry.invalid || final_registry.entry.is_some() {
            return Err(DecisionError::token("registry-replaced"));
        }
        self.raise_if_result()?;
        let launch_spec = self.prepare_launch_spec()?;
        self.raise_if_result()?;
        let final_registry = self.snapshot_registry()?;
        if final_registry.invalid || final_registry.entry.is_some() {
            return Err(DecisionError::token("registry-replaced"));
        }
        self.raise_if_result()?;
        self.write_input_fingerprint()?;
        let cleared = self.clear_before_fresh()?;
        let request = StartRequest {
            spec: launch_spec,
            plugin_root,
            session_values: self.session_values.clone(),
            owner_pid: self.owner_pid.clone(),
        };
        match self.host.start(&request) {
            Ok(output) => Ok(output),
            Err(error) => {
                self.restore_cleared_path(cleared)?;
                Err(error)
            }
        }
    }

    fn prepare_launch_spec(&self) -> DecisionResult<JobSpec> {
        let root = bgjob_dir(&self.spec.tmpdir).map_err(|_| DecisionError::token("unsafe-path"))?;
        fs::create_dir_all(&root).map_err(|_| DecisionError::token("unsafe-path"))?;
        let root_is_safe = fs::symlink_metadata(&root)
            .is_ok_and(|metadata| !metadata.file_type().is_symlink() && metadata.is_dir());
        if !root_is_safe {
            return Err(DecisionError::token("unsafe-path"));
        }
        let candidate = self
            .spec
            .merge_result_env
            .clone()
            .unwrap_or_else(|| root.join(format!("{}.merge.env", self.spec.step)));
        reject_symlink_parents(&candidate, &self.spec.tmpdir)?;
        let merge_env = validate_merge_result_env(&candidate, &self.spec.tmpdir)
            .map_err(|_| DecisionError::token("unsafe-path"))?;
        let initial_rows = validate_initial_merge_rows(&self.spec.initial_merge_rows)
            .map_err(|_| DecisionError::token("unsafe-path"))?;
        let mut text = String::new();
        for (key, value) in &initial_rows {
            text.push_str(key);
            text.push('=');
            text.push_str(value);
            text.push('\n');
        }
        let write_root = if merge_env.parent() == Some(root.as_path()) {
            root.as_path()
        } else {
            self.spec.tmpdir.as_path()
        };
        private_atomic_write(&merge_env, &text, write_root)
            .map_err(|_| DecisionError::token("unsafe-path"))?;
        let mut launch_spec = self.spec.clone();
        launch_spec.command.extend([
            "--bgjob-child".to_owned(),
            "--merge-result-env".to_owned(),
            merge_env.display().to_string(),
        ]);
        launch_spec.merge_result_env = Some(merge_env);
        launch_spec.initial_merge_rows = initial_rows;
        Ok(launch_spec)
    }

    fn clear_before_fresh(&self) -> DecisionResult<Option<PathBuf>> {
        let Some(candidate) = &self.options.clear_on_fresh else {
            return Ok(None);
        };
        let path = ensure_under(candidate, &self.spec.tmpdir, "clear-on-fresh")
            .map_err(|_| DecisionError::token("unsafe-path"))?;
        reject_symlink_parents(&path, &self.spec.tmpdir)?;
        let metadata = fs::symlink_metadata(&path);
        match metadata {
            Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_file() => {
                return Err(DecisionError::token("unsafe-path"));
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(_) => return Err(DecisionError::token("unsafe-path")),
            Ok(_) => {}
        }
        unlink_regular_under(&path, &self.spec.tmpdir, "clear-on-fresh-failed")?;
        Ok(Some(path))
    }

    fn restore_cleared_path(&self, path: Option<PathBuf>) -> DecisionResult<()> {
        let Some(path) = path else {
            return Ok(());
        };
        if read_trusted_regular(&path, &self.spec.tmpdir)?.is_some() {
            return Ok(());
        }
        private_atomic_write(&path, "", &self.spec.tmpdir)
            .map_err(|_| DecisionError::token("clear-on-fresh-restore-failed"))
    }

    fn raise_if_result(&self) -> DecisionResult<()> {
        self.read_completed_result()?
            .map_or(Ok(()), |output| Err(DecisionError::done(output)))
    }
}

fn process_state(verdict: &LivenessVerdict) -> ProcessState {
    ProcessState {
        live: verdict.live,
        proven_dead: !verdict.live && verdict.reason == "missing-pid",
        identity_mismatch: !verdict.live
            && matches!(
                verdict.reason.as_str(),
                "pgid-mismatch"
                    | "start-time-mismatch"
                    | "command-mismatch"
                    | "expected-command-mismatch"
            ),
    }
}

fn parse_completed_rows(text: &str, step: &str) -> Option<Vec<(String, String)>> {
    if text.contains('\r') {
        return None;
    }
    let options = ParseOptions {
        malformed_lines: MalformedLinePolicy::Reject,
        ..ParseOptions::legacy()
    };
    let document = KvDocument::parse(text, options).ok()?;
    let rows = document
        .rows()
        .iter()
        .map(|row| (!row.key().is_empty()).then(|| (row.key().to_owned(), row.value().to_owned())))
        .collect::<Option<Vec<_>>>()?;
    let values = rows.iter().cloned().collect::<BTreeMap<_, _>>();
    (!values.get(BGJOB_RC_KEY).is_none_or(String::is_empty)
        && values.get("STEP").is_some_and(|value| value == step))
    .then_some(rows)
}

fn format_done(rows: &[(String, String)]) -> String {
    let mut output = format!("{BGJOB_STATUS_KEY}={BGJOB_STATUS_DONE}\n");
    for (key, value) in rows {
        output.push_str(key);
        output.push('=');
        output.push_str(value);
        output.push('\n');
    }
    output
}

fn read_trusted_regular(path: &Path, root: &Path) -> DecisionResult<Option<String>> {
    let path = ensure_under(path, root, "trusted file")
        .map_err(|_| DecisionError::token("unsafe-path"))?;
    match fs::symlink_metadata(&path) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err(DecisionError::token("unsafe-path")),
        Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_file() => {
            return Err(DecisionError::token("unsafe-path"));
        }
        Ok(_) => {}
    }
    reject_symlink_parents(&path, root)?;
    fs::read_to_string(path)
        .map(Some)
        .map_err(|_| DecisionError::token("unsafe-path"))
}

fn reject_symlink_parents(path: &Path, root: &Path) -> DecisionResult<()> {
    let root = fs::canonicalize(root).map_err(|_| DecisionError::token("unsafe-path"))?;
    let mut parent = path
        .parent()
        .ok_or_else(|| DecisionError::token("unsafe-path"))?;
    loop {
        let metadata =
            fs::symlink_metadata(parent).map_err(|_| DecisionError::token("unsafe-path"))?;
        if metadata.file_type().is_symlink() || !metadata.is_dir() {
            return Err(DecisionError::token("unsafe-path"));
        }
        let resolved = fs::canonicalize(parent).map_err(|_| DecisionError::token("unsafe-path"))?;
        if resolved == root {
            return Ok(());
        }
        parent = parent
            .parent()
            .ok_or_else(|| DecisionError::token("unsafe-path"))?;
    }
}

fn stat_fingerprint(path: &Path) -> Result<Option<FileFingerprint>, ()> {
    let metadata = match fs::symlink_metadata(path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err(()),
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(());
    }
    #[cfg(unix)]
    {
        Ok(Some(FileFingerprint {
            device: metadata.dev(),
            inode: metadata.ino(),
            modified_ns: i128::from(metadata.mtime()) * 1_000_000_000_i128
                + i128::from(metadata.mtime_nsec()),
            size: metadata.size(),
        }))
    }
    #[cfg(not(unix))]
    {
        let modified_ns = metadata
            .modified()
            .ok()
            .and_then(|time| time.duration_since(std::time::UNIX_EPOCH).ok())
            .map_or(0, |duration| i128::from(duration.as_nanos() as u64));
        Ok(Some(FileFingerprint {
            device: 0,
            inode: 0,
            modified_ns,
            size: metadata.len(),
        }))
    }
}

fn rehydrate_plugin_root(tmpdir: &Path) -> DecisionResult<PathBuf> {
    rehydrate_plugin_root_from(tmpdir, env::var_os("CLAUDE_PLUGIN_ROOT"))
}

fn rehydrate_plugin_root_from(
    tmpdir: &Path,
    configured_root: Option<OsString>,
) -> DecisionResult<PathBuf> {
    let mut raw_root = configured_root
        .and_then(|value| value.into_string().ok())
        .unwrap_or_default();
    if raw_root.is_empty() {
        raw_root = plugin_root_from_file(&tmpdir.join("plugin-root.env"), "CLAUDE_PLUGIN_ROOT")?;
    }
    if raw_root.is_empty() {
        raw_root =
            plugin_root_from_file(&tmpdir.join("session-env.sh"), "LARCH_CLAUDE_PLUGIN_ROOT")?;
    }
    if raw_root.is_empty() || raw_root == "${CLAUDE_PLUGIN_ROOT}" || raw_root.contains(['\n', '\r'])
    {
        return Err(DecisionError::token("plugin-root-missing"));
    }
    let root = expand_home_path(Path::new(&raw_root));
    let metadata =
        fs::symlink_metadata(&root).map_err(|_| DecisionError::token("plugin-root-invalid"))?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() || !root.is_absolute() {
        return Err(DecisionError::token("plugin-root-invalid"));
    }
    let root = fs::canonicalize(root).map_err(|_| DecisionError::token("plugin-root-invalid"))?;
    fs::symlink_metadata(root.join("python/cli.py"))
        .is_ok_and(|metadata| metadata.is_file())
        .then_some(root)
        .ok_or_else(|| DecisionError::token("plugin-root-invalid"))
}

fn plugin_root_from_file(path: &Path, key: &str) -> DecisionResult<String> {
    match fs::symlink_metadata(path) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(String::new()),
        Err(_) => return Err(DecisionError::token("plugin-root-invalid")),
        Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_file() => {
            return Err(DecisionError::token("plugin-root-invalid"));
        }
        Ok(_) => {}
    }
    let text = fs::read_to_string(path).map_err(|_| DecisionError::token("plugin-root-invalid"))?;
    if text.contains('\r') {
        return Err(DecisionError::token("plugin-root-invalid"));
    }
    let document = KvDocument::parse(&text, ParseOptions::legacy())
        .map_err(|_| DecisionError::token("plugin-root-invalid"))?;
    Ok(document
        .rows()
        .iter()
        .find(|row| row.key() == key)
        .map_or_else(String::new, |row| row.value().to_owned()))
}

fn expand_home_path(path: &Path) -> PathBuf {
    let Some(raw) = path.to_str() else {
        return path.to_path_buf();
    };
    if raw == "~" {
        return env::var_os("HOME").map_or_else(|| path.to_path_buf(), PathBuf::from);
    }
    raw.strip_prefix("~/").map_or_else(
        || path.to_path_buf(),
        |tail| {
            env::var_os("HOME")
                .map_or_else(|| path.to_path_buf(), |home| PathBuf::from(home).join(tail))
        },
    )
}

#[cfg(unix)]
struct DecisionLock {
    _root: OwnedFd,
    _lock: OwnedFd,
}

#[cfg(unix)]
impl DecisionLock {
    fn open(root: &Path, run_id: &str, step: &str) -> DecisionResult<Self> {
        let run_id = validate_run_id(run_id).map_err(|_| DecisionError::token("lock-failed"))?;
        let step = validate_slug(step, "step").map_err(|_| DecisionError::token("lock-failed"))?;
        let root_fd = open(
            root,
            OFlag::O_RDONLY | OFlag::O_DIRECTORY | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
            Mode::empty(),
        )
        .map_err(|error| lock_failure("open-root", error))?;
        let opened_root = fstat(&root_fd).map_err(|error| lock_failure("fstat-root", error))?;
        let current_root =
            fs::symlink_metadata(root).map_err(|error| lock_failure("stat-root", error))?;
        if !same_stat_metadata(&opened_root, &current_root) {
            return Err(DecisionError::token("lock-failed"));
        }
        let name = format!("{run_id}-{step}.lock");
        let lock_fd =
            open_lock_file(&root_fd, &name).map_err(|error| lock_failure("open-lock", error))?;
        let opened_lock = fstat(&lock_fd).map_err(|error| lock_failure("fstat-lock", error))?;
        let visible_lock = fstatat(&root_fd, name.as_str(), AtFlags::AT_SYMLINK_NOFOLLOW)
            .map_err(|error| lock_failure("fstatat-lock", error))?;
        if file_type(&opened_lock) != SFlag::S_IFREG
            || opened_lock.st_dev != visible_lock.st_dev
            || opened_lock.st_ino != visible_lock.st_ino
        {
            return Err(DecisionError::token("unsafe-path"));
        }
        fchmod(&lock_fd, Mode::from_bits_truncate(0o600))
            .map_err(|error| lock_failure("chmod-lock", error))?;
        // `O_CLOEXEC` ensures the retained Python daemon start process cannot
        // inherit this lock across its fork/exec boundary.
        #[allow(deprecated)]
        flock(lock_fd.as_raw_fd(), FlockArg::LockExclusive)
            .map_err(|error| lock_failure("flock", error))?;
        Ok(Self {
            _root: root_fd,
            _lock: lock_fd,
        })
    }
}

#[cfg(unix)]
fn open_lock_file(root: &OwnedFd, name: &str) -> nix::Result<OwnedFd> {
    let flags = OFlag::O_RDWR | OFlag::O_CREAT | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC;
    let mode = Mode::from_bits_truncate(0o600);
    let mut retries = 0;
    loop {
        match openat(root, name, flags, mode) {
            Err(Errno::ENOENT) if retries < 8 => {
                retries += 1;
                std::thread::yield_now();
            }
            result => return result,
        }
    }
}

#[cfg(unix)]
fn lock_failure(_stage: &str, _error: impl std::fmt::Display) -> DecisionError {
    DecisionError::token("lock-failed")
}

#[cfg(not(unix))]
struct DecisionLock;

#[cfg(not(unix))]
impl DecisionLock {
    fn open(_root: &Path, _run_id: &str, _step: &str) -> DecisionResult<Self> {
        Err(DecisionError::token("lock-failed"))
    }
}

#[cfg(unix)]
fn same_stat_metadata(stat: &nix::sys::stat::FileStat, metadata: &fs::Metadata) -> bool {
    i128::from(stat.st_dev) == i128::from(metadata.dev())
        && i128::from(stat.st_ino) == i128::from(metadata.ino())
}

#[cfg(unix)]
const fn file_type(stat: &nix::sys::stat::FileStat) -> SFlag {
    SFlag::from_bits_truncate(stat.st_mode)
}

fn unlink_regular_under(path: &Path, root: &Path, failure: &'static str) -> DecisionResult<()> {
    #[cfg(unix)]
    {
        let path = ensure_under(path, root, "unlink file")
            .map_err(|_| DecisionError::token("unsafe-path"))?;
        reject_symlink_parents(&path, root)?;
        let parent = path
            .parent()
            .ok_or_else(|| DecisionError::token("unsafe-path"))?;
        let name = path
            .file_name()
            .ok_or_else(|| DecisionError::token("unsafe-path"))?;
        let directory = open(
            parent,
            OFlag::O_RDONLY | OFlag::O_DIRECTORY | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
            Mode::empty(),
        )
        .map_err(|_| DecisionError::token("unsafe-path"))?;
        let opened_parent = fstat(&directory).map_err(|_| DecisionError::token("unsafe-path"))?;
        let current_parent =
            fs::symlink_metadata(parent).map_err(|_| DecisionError::token("unsafe-path"))?;
        if !same_stat_metadata(&opened_parent, &current_parent) {
            return Err(DecisionError::token("unsafe-path"));
        }
        let current = match fstatat(&directory, name, AtFlags::AT_SYMLINK_NOFOLLOW) {
            Ok(current) => current,
            Err(Errno::ENOENT) => return Ok(()),
            Err(_) => return Err(DecisionError::token(failure)),
        };
        if file_type(&current) != SFlag::S_IFREG {
            return Err(DecisionError::token("unsafe-path"));
        }
        unlinkat(&directory, name, UnlinkatFlags::NoRemoveDir)
            .map_err(|_| DecisionError::token(failure))?;
        match fstatat(&directory, name, AtFlags::AT_SYMLINK_NOFOLLOW) {
            Err(Errno::ENOENT) => Ok(()),
            _ => Err(DecisionError::token(failure)),
        }
    }
    #[cfg(not(unix))]
    {
        let _ = (path, root, failure);
        Err(DecisionError::token("unsafe-path"))
    }
}

#[cfg(test)]
mod tests {
    use super::{
        AdaptOptions, Adapter, AdapterHost, DecisionLock, DecisionResult, JobSpec, LivenessVerdict,
        OwnerIdentity, RegistryEntry, SessionValues, StartRequest, SystemAdapterHost, adapt,
        build_request, format_done, has_top_level_option, log_paths, parse_arguments,
        parse_completed_rows, parse_resolver_arguments, parse_single_kv_row, plugin_root_from_file,
        process_state, python_start_command, read_trusted_regular, rehydrate_plugin_root_from,
        resolve_run_id, resolve_session_env, resolve_session_env_argv, resolve_tmpdir,
        result_env_path, run_id_from_line, run_with_host, session_env_source, shell_quote,
        stat_fingerprint, trusted_session_link, unlink_regular_under, valid_owner_pid,
        validate_design_tmpdir, validate_started_stdout, write_stdout,
    };
    use larch_core::{RecordedProcessIdentity, write_entry_at};
    use std::{
        env,
        ffi::OsString,
        fs,
        path::{Path, PathBuf},
        sync::atomic::{AtomicUsize, Ordering},
        sync::{Arc, Barrier, Mutex},
        thread,
        time::{SystemTime, UNIX_EPOCH},
    };

    struct FakeHost {
        starts: AtomicUsize,
        plugin_root: PathBuf,
        registry_root: PathBuf,
    }

    impl FakeHost {
        fn identity(pid: i32) -> RecordedProcessIdentity {
            RecordedProcessIdentity {
                pid,
                pgid: 303,
                start_time: format!("start-{pid}"),
                command_signature: "fake-command".to_owned(),
                expected_signature: String::new(),
            }
        }
    }

    impl AdapterHost for FakeHost {
        fn daemon_liveness(&self, _entry: &RegistryEntry) -> LivenessVerdict {
            verdict(self.starts.load(Ordering::SeqCst) > 0)
        }

        fn child_liveness(&self, _entry: &RegistryEntry) -> LivenessVerdict {
            verdict(self.starts.load(Ordering::SeqCst) > 0)
        }

        fn plugin_root(&self, _tmpdir: &Path) -> DecisionResult<PathBuf> {
            Ok(self.plugin_root.clone())
        }

        fn start(&self, request: &StartRequest) -> DecisionResult<String> {
            self.starts.fetch_add(1, Ordering::SeqCst);
            let entry = RegistryEntry {
                step: request.spec.step.clone(),
                run_id: request.spec.run_id.clone(),
                tmpdir: request.spec.tmpdir.clone(),
                log_dir: request.spec.log_dir.clone(),
                clone_path: env::current_dir()
                    .expect("cwd")
                    .canonicalize()
                    .expect("canonical cwd"),
                daemon: Self::identity(101),
                child: Self::identity(202),
                owner: None,
                start_epoch: now(),
                budget_s: request.spec.budget_s,
                stdout_log: request
                    .spec
                    .log_dir
                    .join(format!("{}.stdout.log", request.spec.step)),
                stderr_log: request
                    .spec
                    .log_dir
                    .join(format!("{}.stderr.log", request.spec.step)),
                result_env: result_env_path(&request.spec.tmpdir, &request.spec.step)
                    .expect("result path"),
            };
            write_entry_at(&entry, Some(&self.registry_root)).expect("registry write");
            Ok(format!(
                "BGJOB_STATUS=STARTED STEP={} PGID=303\n",
                request.spec.step
            ))
        }
    }

    struct ScenarioHost {
        starts: AtomicUsize,
        plugin_root: PathBuf,
        daemon: LivenessVerdict,
        child: LivenessVerdict,
        start_error: Option<&'static str>,
        captured: Mutex<Option<StartRequest>>,
    }

    impl ScenarioHost {
        fn new(plugin_root: PathBuf, daemon: LivenessVerdict, child: LivenessVerdict) -> Self {
            Self {
                starts: AtomicUsize::new(0),
                plugin_root,
                daemon,
                child,
                start_error: None,
                captured: Mutex::new(None),
            }
        }

        fn failing(
            plugin_root: PathBuf,
            daemon: LivenessVerdict,
            child: LivenessVerdict,
            token: &'static str,
        ) -> Self {
            Self {
                start_error: Some(token),
                ..Self::new(plugin_root, daemon, child)
            }
        }
    }

    impl AdapterHost for ScenarioHost {
        fn daemon_liveness(&self, _entry: &RegistryEntry) -> LivenessVerdict {
            self.daemon.clone()
        }

        fn child_liveness(&self, _entry: &RegistryEntry) -> LivenessVerdict {
            self.child.clone()
        }

        fn plugin_root(&self, _tmpdir: &Path) -> DecisionResult<PathBuf> {
            Ok(self.plugin_root.clone())
        }

        fn start(&self, request: &StartRequest) -> DecisionResult<String> {
            self.starts.fetch_add(1, Ordering::SeqCst);
            *self.captured.lock().expect("captured request") = Some(request.clone());
            if let Some(token) = self.start_error {
                return Err(super::DecisionError::token(token));
            }
            Ok(format!(
                "BGJOB_STATUS=STARTED STEP={} PGID=303\n",
                request.spec.step
            ))
        }
    }

    fn verdict(live: bool) -> LivenessVerdict {
        LivenessVerdict {
            live,
            reason: if live { "ok" } else { "missing-pid" }.to_owned(),
        }
    }

    fn dead_verdict(reason: &str) -> LivenessVerdict {
        LivenessVerdict {
            live: false,
            reason: reason.to_owned(),
        }
    }

    fn now() -> i64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(1, |duration| {
                i64::try_from(duration.as_secs()).unwrap_or(i64::MAX)
            })
    }

    fn spec(tmpdir: &Path) -> JobSpec {
        let tmpdir = tmpdir.canonicalize().expect("tmpdir");
        let (log_dir, _, _) = log_paths(&tmpdir, None, "demo-step").expect("logs");
        JobSpec {
            step: "demo-step".to_owned(),
            tmpdir,
            log_dir,
            budget_s: 30,
            command: vec!["true".to_owned()],
            run_id: "run-1".to_owned(),
            owner: OwnerIdentity { recorded: None },
            sentinel_paths: Vec::new(),
            merge_result_env: None,
            initial_merge_rows: Vec::new(),
        }
    }

    fn dead_entry(spec: &JobSpec) -> RegistryEntry {
        RegistryEntry {
            step: spec.step.clone(),
            run_id: spec.run_id.clone(),
            tmpdir: spec.tmpdir.clone(),
            log_dir: spec.log_dir.clone(),
            clone_path: env::current_dir()
                .expect("cwd")
                .canonicalize()
                .expect("canonical cwd"),
            daemon: FakeHost::identity(11),
            child: FakeHost::identity(12),
            owner: None,
            start_epoch: 1,
            budget_s: 1,
            stdout_log: spec.log_dir.join("demo-step.stdout.log"),
            stderr_log: spec.log_dir.join("demo-step.stderr.log"),
            result_env: result_env_path(&spec.tmpdir, &spec.step).expect("result path"),
        }
    }

    fn active_entry(spec: &JobSpec) -> RegistryEntry {
        let mut entry = dead_entry(spec);
        entry.start_epoch = now();
        entry.budget_s = 60;
        entry
    }

    fn current_dir() -> PathBuf {
        env::current_dir()
            .expect("cwd")
            .canonicalize()
            .expect("canonical cwd")
    }

    fn run_scenario(
        host: &ScenarioHost,
        registry: &Path,
        spec: JobSpec,
        options: AdaptOptions,
    ) -> DecisionResult<String> {
        run_with_host(
            host,
            registry,
            &current_dir(),
            spec,
            options,
            SessionValues::default(),
            String::new(),
        )
    }

    #[test]
    fn completed_result_stdout_grammar_is_exact() {
        let tempdir = tempfile::tempdir().expect("tempdir");
        let spec = spec(tempdir.path());
        let result = result_env_path(&spec.tmpdir, &spec.step).expect("result path");
        fs::write(&result, "BGJOB_RC=0\nBGJOB_ELAPSED_S=1\nSTEP=demo-step\n").expect("result");
        let registry = tempdir.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");
        let host = FakeHost {
            starts: AtomicUsize::new(0),
            plugin_root: tempdir.path().to_path_buf(),
            registry_root: registry.clone(),
        };
        let cwd = env::current_dir()
            .expect("cwd")
            .canonicalize()
            .expect("canonical cwd");
        let output = run_with_host(
            &host,
            &registry,
            &cwd,
            spec,
            AdaptOptions::default(),
            SessionValues::default(),
            String::new(),
        )
        .expect("completed result");
        assert_eq!(
            output,
            "BGJOB_STATUS=DONE\nBGJOB_RC=0\nBGJOB_ELAPSED_S=1\nSTEP=demo-step\n"
        );
        assert_eq!(host.starts.load(Ordering::SeqCst), 0);
    }

    #[cfg(unix)]
    #[test]
    fn symlinked_completed_result_refuses_before_launch() {
        use std::os::unix::fs::symlink;

        let tempdir = tempfile::tempdir().expect("tempdir");
        let spec = spec(tempdir.path());
        let result = result_env_path(&spec.tmpdir, &spec.step).expect("result path");
        let target = tempdir.path().join("result-target.env");
        fs::write(&target, "BGJOB_RC=0\nSTEP=demo-step\n").expect("target result");
        symlink(&target, &result).expect("result symlink");
        let registry = tempdir.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");
        let host = FakeHost {
            starts: AtomicUsize::new(0),
            plugin_root: tempdir.path().to_path_buf(),
            registry_root: registry.clone(),
        };
        let cwd = env::current_dir()
            .expect("cwd")
            .canonicalize()
            .expect("canonical cwd");

        let error = run_with_host(
            &host,
            &registry,
            &cwd,
            spec,
            AdaptOptions::default(),
            SessionValues::default(),
            String::new(),
        )
        .expect_err("symlinked result must be rejected");

        assert_eq!(error.token, "unsafe-path");
        assert_eq!(host.starts.load(Ordering::SeqCst), 0);
    }

    #[cfg(unix)]
    #[test]
    fn trusted_file_reader_rejects_symlinked_parents() {
        use std::os::unix::fs::symlink;

        let sandbox = tempfile::tempdir().expect("tempdir");
        let outside = tempfile::tempdir().expect("outside");
        let link = sandbox.path().join("linked-parent");
        symlink(outside.path(), &link).expect("directory link");
        let linked_file = link.join("state.env");
        fs::write(outside.path().join("state.env"), "STATE=outside\n").expect("state file");
        assert!(read_trusted_regular(&linked_file, sandbox.path()).is_err());
    }

    #[test]
    fn concurrent_adapt_clears_one_dead_entry_and_launches_once() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        let registry = sandbox.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");
        let initial = spec(sandbox.path());
        write_entry_at(&dead_entry(&initial), Some(&registry)).expect("dead registry");
        let host = Arc::new(FakeHost {
            starts: AtomicUsize::new(0),
            plugin_root: sandbox.path().to_path_buf(),
            registry_root: registry.clone(),
        });
        let barrier = Arc::new(Barrier::new(2));
        let cwd = env::current_dir()
            .expect("cwd")
            .canonicalize()
            .expect("canonical cwd");
        let workers = (0..2)
            .map(|_| {
                let host = Arc::clone(&host);
                let barrier = Arc::clone(&barrier);
                let registry = registry.clone();
                let cwd = cwd.clone();
                let job_tmpdir = sandbox.path().to_path_buf();
                thread::spawn(move || {
                    barrier.wait();
                    run_with_host(
                        host.as_ref(),
                        &registry,
                        &cwd,
                        spec(&job_tmpdir),
                        AdaptOptions::default(),
                        SessionValues::default(),
                        String::new(),
                    )
                })
            })
            .collect::<Vec<_>>();
        for worker in workers {
            let result = worker.join().expect("worker");
            let output = result.expect("adapter result");
            assert_eq!(output, "BGJOB_STATUS=STARTED STEP=demo-step PGID=303\n");
        }
        assert_eq!(host.starts.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn active_registry_liveness_cases_reattach_or_fail_closed() {
        let cases = [
            (verdict(true), verdict(true), None),
            (verdict(true), dead_verdict("missing-pid"), None),
            (
                dead_verdict("missing-pid"),
                verdict(true),
                Some("registry-ownership-lost"),
            ),
            (
                dead_verdict("missing-pid"),
                dead_verdict("missing-pid"),
                Some("registry-dead"),
            ),
            (
                dead_verdict("missing-pid"),
                dead_verdict("start-time-mismatch"),
                Some("registry-identity-unverifiable"),
            ),
            (
                verdict(true),
                dead_verdict("command-mismatch"),
                Some("registry-identity-unverifiable"),
            ),
        ];
        for (daemon, child, expected_error) in cases {
            let sandbox = tempfile::tempdir().expect("tempdir");
            let registry = sandbox.path().join("registry");
            fs::create_dir_all(&registry).expect("registry");
            let job = spec(sandbox.path());
            write_entry_at(&active_entry(&job), Some(&registry)).expect("active registry");
            let host = ScenarioHost::new(sandbox.path().to_path_buf(), daemon, child);
            let result = run_scenario(&host, &registry, job, AdaptOptions::default());

            match expected_error {
                Some(token) => assert_eq!(result.expect_err("decision failure").token, token),
                None => assert_eq!(
                    result.expect("reattached result"),
                    "BGJOB_STATUS=STARTED STEP=demo-step PGID=303\n"
                ),
            }
            assert_eq!(host.starts.load(Ordering::SeqCst), 0);
        }
    }

    #[test]
    fn expired_and_replace_dead_entries_clear_then_restart() {
        for replace_completed_result in [false, true] {
            let sandbox = tempfile::tempdir().expect("tempdir");
            let registry = sandbox.path().join("registry");
            fs::create_dir_all(&registry).expect("registry");
            let job = spec(sandbox.path());
            write_entry_at(&dead_entry(&job), Some(&registry)).expect("dead registry");
            let host = ScenarioHost::new(
                sandbox.path().to_path_buf(),
                dead_verdict("missing-pid"),
                dead_verdict("missing-pid"),
            );

            let output = run_scenario(
                &host,
                &registry,
                job,
                AdaptOptions {
                    replace_completed_result,
                    ..AdaptOptions::default()
                },
            )
            .expect("replacement start");
            assert_eq!(output, "BGJOB_STATUS=STARTED STEP=demo-step PGID=303\n");
            assert_eq!(host.starts.load(Ordering::SeqCst), 1);
        }
    }

    #[test]
    fn live_expired_or_replace_active_entries_are_not_replaced() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        let registry = sandbox.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");
        let expired = spec(sandbox.path());
        write_entry_at(&dead_entry(&expired), Some(&registry)).expect("expired registry");
        let live_host =
            ScenarioHost::new(sandbox.path().to_path_buf(), verdict(true), verdict(true));
        assert_eq!(
            run_scenario(&live_host, &registry, expired, AdaptOptions::default())
                .expect_err("expired live")
                .token,
            "expired-live"
        );

        let active = spec(sandbox.path());
        write_entry_at(&active_entry(&active), Some(&registry)).expect("active registry");
        assert_eq!(
            run_scenario(
                &live_host,
                &registry,
                active,
                AdaptOptions {
                    replace_completed_result: true,
                    ..AdaptOptions::default()
                },
            )
            .expect_err("active replacement")
            .token,
            "replace-active"
        );
    }

    #[test]
    fn stale_and_replaced_completed_results_launch_with_fresh_metadata() {
        for replace_completed_result in [false, true] {
            let sandbox = tempfile::tempdir().expect("tempdir");
            let registry = sandbox.path().join("registry");
            fs::create_dir_all(&registry).expect("registry");
            let mut job = spec(sandbox.path());
            job.command = vec!["worker".to_owned(), "--flag".to_owned()];
            job.initial_merge_rows = vec![("OUTCOME".to_owned(), "continue".to_owned())];
            let result = result_env_path(&job.tmpdir, &job.step).expect("result path");
            fs::write(&result, "BGJOB_RC=0\nSTEP=demo-step\n").expect("completed result");
            if !replace_completed_result {
                fs::write(job.tmpdir.join("bgjob/demo-step.input-fp"), "old\n")
                    .expect("fingerprint");
            }
            let host = ScenarioHost::new(
                sandbox.path().to_path_buf(),
                dead_verdict("missing-pid"),
                dead_verdict("missing-pid"),
            );

            let output = run_scenario(
                &host,
                &registry,
                job.clone(),
                AdaptOptions {
                    replace_completed_result,
                    input_fingerprint: "new".to_owned(),
                    ..AdaptOptions::default()
                },
            )
            .expect("fresh start");
            assert_eq!(output, "BGJOB_STATUS=STARTED STEP=demo-step PGID=303\n");
            assert_eq!(host.starts.load(Ordering::SeqCst), 1);
            assert!(!result.exists());
            assert_eq!(
                fs::read_to_string(job.tmpdir.join("bgjob/demo-step.input-fp"))
                    .expect("new fingerprint"),
                "new\n"
            );
            let request = host
                .captured
                .lock()
                .expect("captured request")
                .clone()
                .expect("start request");
            assert_eq!(
                request.spec.command,
                [
                    "worker",
                    "--flag",
                    "--bgjob-child",
                    "--merge-result-env",
                    request
                        .spec
                        .merge_result_env
                        .as_ref()
                        .expect("merge env")
                        .to_str()
                        .expect("utf8 merge env"),
                ]
            );
            assert_eq!(
                fs::read_to_string(request.spec.merge_result_env.expect("merge env"))
                    .expect("merge content"),
                "OUTCOME=continue\n"
            );
        }
    }

    #[test]
    fn failed_launch_restores_a_cleared_file() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        let registry = sandbox.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");
        let job = spec(sandbox.path());
        let cleared = job.tmpdir.join("clear-on-fresh.env");
        fs::write(&cleared, "old state\n").expect("clear target");
        let host = ScenarioHost::failing(
            sandbox.path().to_path_buf(),
            dead_verdict("missing-pid"),
            dead_verdict("missing-pid"),
            "daemon-start-failed",
        );

        assert_eq!(
            run_scenario(
                &host,
                &registry,
                job,
                AdaptOptions {
                    clear_on_fresh: Some(cleared.clone()),
                    ..AdaptOptions::default()
                },
            )
            .expect_err("failed launch")
            .token,
            "daemon-start-failed"
        );
        assert_eq!(host.starts.load(Ordering::SeqCst), 1);
        assert_eq!(fs::read_to_string(cleared).expect("restored file"), "");
    }

    #[test]
    fn adapter_internal_file_protocol_covers_fresh_completed_and_invalid_states() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        let registry = sandbox.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");
        let mut job = spec(sandbox.path());
        job.merge_result_env = Some(job.tmpdir.join("custom-merge.env"));
        job.initial_merge_rows = vec![("OUTCOME".to_owned(), "continue".to_owned())];
        let host = ScenarioHost::new(
            sandbox.path().to_path_buf(),
            dead_verdict("missing-pid"),
            dead_verdict("missing-pid"),
        );
        let cwd = current_dir();
        let adapter = Adapter {
            host: &host,
            registry_root: &registry,
            cwd: &cwd,
            spec: job.clone(),
            options: AdaptOptions {
                input_fingerprint: "fresh".to_owned(),
                ..AdaptOptions::default()
            },
            session_values: SessionValues::default(),
            owner_pid: String::new(),
        };

        let absent = adapter.snapshot_registry().expect("absent snapshot");
        assert!(!absent.invalid);
        assert!(absent.entry.is_none());
        let launch = adapter.prepare_launch_spec().expect("launch spec");
        assert_eq!(
            launch.initial_merge_rows,
            [("OUTCOME".to_owned(), "continue".to_owned())]
        );
        assert_eq!(
            fs::read_to_string(launch.merge_result_env.expect("merge env")).expect("merge rows"),
            "OUTCOME=continue\n"
        );
        adapter
            .write_input_fingerprint()
            .expect("write fingerprint");
        assert_eq!(
            adapter
                .read_stored_input_fingerprint()
                .expect("read fingerprint"),
            "fresh"
        );
        assert!(!adapter.completed_is_stale().expect("fresh fingerprint"));

        let result = result_env_path(&job.tmpdir, &job.step).expect("result path");
        fs::write(&result, "BGJOB_RC=0\nSTEP=demo-step\n").expect("completed result");
        assert_eq!(
            adapter.read_completed_result().expect("completed result"),
            Some("BGJOB_STATUS=DONE\nBGJOB_RC=0\nSTEP=demo-step\n".to_owned())
        );
        assert_eq!(
            adapter.raise_if_result().expect_err("result emitted").token,
            "result-emitted"
        );
        adapter.invalidate_completed_result().expect("clear result");
        assert!(!result.exists());
        adapter
            .invalidate_completed_result()
            .expect("clear missing result");

        let cleared = job.tmpdir.join("clear-on-fresh.env");
        let clear_adapter = Adapter {
            options: AdaptOptions {
                clear_on_fresh: Some(cleared.clone()),
                ..AdaptOptions::default()
            },
            ..adapter
        };
        assert_eq!(
            clear_adapter.clear_before_fresh().expect("missing clear"),
            None
        );
        fs::write(&cleared, "old\n").expect("clear target");
        assert_eq!(
            clear_adapter.clear_before_fresh().expect("clear target"),
            Some(cleared.clone())
        );
        assert!(!cleared.exists());
        clear_adapter
            .restore_cleared_path(Some(cleared.clone()))
            .expect("restore target");
        assert_eq!(fs::read_to_string(&cleared).expect("restored target"), "");
        fs::write(&cleared, "new\n").expect("new target");
        clear_adapter
            .restore_cleared_path(Some(cleared.clone()))
            .expect("keep target");
        assert_eq!(fs::read_to_string(&cleared).expect("kept target"), "new\n");
        clear_adapter
            .restore_cleared_path(None)
            .expect("no restore");

        fs::write(&absent.path, "not=a registry\n").expect("malformed registry");
        assert!(
            clear_adapter
                .snapshot_registry()
                .expect("invalid snapshot")
                .invalid
        );
    }

    #[test]
    fn snapshot_replacement_and_active_completed_result_paths_are_safe() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        let registry = sandbox.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");
        let job = spec(sandbox.path());
        let host = ScenarioHost::new(sandbox.path().to_path_buf(), verdict(true), verdict(true));
        let cwd = current_dir();
        let adapter = Adapter {
            host: &host,
            registry_root: &registry,
            cwd: &cwd,
            spec: job.clone(),
            options: AdaptOptions::default(),
            session_values: SessionValues::default(),
            owner_pid: String::new(),
        };
        let before = adapter.snapshot_registry().expect("empty snapshot");
        write_entry_at(&active_entry(&job), Some(&registry)).expect("replacement registry");
        assert_eq!(
            adapter
                .verify_same_snapshot(&before)
                .expect_err("replaced registry")
                .token,
            "registry-replaced"
        );

        let result = result_env_path(&job.tmpdir, &job.step).expect("result path");
        fs::write(&result, "BGJOB_RC=0\nSTEP=demo-step\n").expect("completed result");
        assert_eq!(
            run_scenario(&host, &registry, job.clone(), AdaptOptions::default())
                .expect("active completed result"),
            "BGJOB_STATUS=DONE\nBGJOB_RC=0\nSTEP=demo-step\n"
        );

        fs::remove_file(&result).expect("remove completed result");
        let unverified = ScenarioHost::new(
            sandbox.path().to_path_buf(),
            dead_verdict("start-time-mismatch"),
            dead_verdict("missing-pid"),
        );
        assert_eq!(
            run_scenario(
                &unverified,
                &registry,
                job,
                AdaptOptions {
                    replace_completed_result: true,
                    ..AdaptOptions::default()
                },
            )
            .expect_err("unverifiable replacement")
            .token,
            "registry-identity-unverifiable"
        );
    }

    #[cfg(unix)]
    #[test]
    fn symlinked_fingerprint_clear_target_and_registry_are_rejected() {
        use std::os::unix::fs::symlink;

        let sandbox = tempfile::tempdir().expect("tempdir");
        let outside = tempfile::tempdir().expect("outside");
        let registry = sandbox.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");
        let job = spec(sandbox.path());
        let host = ScenarioHost::new(
            sandbox.path().to_path_buf(),
            dead_verdict("missing-pid"),
            dead_verdict("missing-pid"),
        );
        let cwd = current_dir();
        let fingerprint_target = outside.path().join("fingerprint");
        fs::write(&fingerprint_target, "old\n").expect("fingerprint target");
        let fingerprint = job.tmpdir.join("bgjob/demo-step.input-fp");
        symlink(&fingerprint_target, &fingerprint).expect("fingerprint symlink");
        let clear_target = job.tmpdir.join("clear.env");
        symlink(&fingerprint_target, &clear_target).expect("clear symlink");
        let adapter = Adapter {
            host: &host,
            registry_root: &registry,
            cwd: &cwd,
            spec: job,
            options: AdaptOptions {
                clear_on_fresh: Some(clear_target),
                input_fingerprint: "new".to_owned(),
                ..AdaptOptions::default()
            },
            session_values: SessionValues::default(),
            owner_pid: String::new(),
        };
        assert_eq!(
            adapter
                .read_stored_input_fingerprint()
                .expect("fingerprint fallback"),
            ""
        );
        assert_eq!(
            adapter
                .clear_before_fresh()
                .expect_err("clear symlink")
                .token,
            "unsafe-path"
        );

        let registry_target = outside.path().join("registry.env");
        fs::write(&registry_target, "STATE=outside\n").expect("registry target");
        symlink(&registry_target, registry.join("run-1-demo-step.env")).expect("registry symlink");
        assert_eq!(
            adapter
                .snapshot_registry()
                .expect_err("registry symlink")
                .token,
            "registry-failed"
        );
    }

    #[test]
    fn invalid_launch_metadata_is_rejected_before_starting() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        let outside = tempfile::tempdir().expect("outside");
        let registry = sandbox.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");
        let mut job = spec(sandbox.path());
        job.merge_result_env = Some(outside.path().join("escape.env"));
        let host = ScenarioHost::new(
            sandbox.path().to_path_buf(),
            dead_verdict("missing-pid"),
            dead_verdict("missing-pid"),
        );
        let cwd = current_dir();
        let adapter = Adapter {
            host: &host,
            registry_root: &registry,
            cwd: &cwd,
            spec: job,
            options: AdaptOptions::default(),
            session_values: SessionValues::default(),
            owner_pid: String::new(),
        };
        assert_eq!(
            adapter
                .prepare_launch_spec()
                .expect_err("escaped merge result")
                .token,
            "unsafe-path"
        );
    }

    #[test]
    fn malformed_and_mismatched_registry_records_fail_before_launch() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        let registry = sandbox.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");
        let job = spec(sandbox.path());
        let path = registry.join("run-1-demo-step.env");
        fs::write(&path, "not=a registry record\n").expect("malformed registry");
        let host = ScenarioHost::new(
            sandbox.path().to_path_buf(),
            dead_verdict("missing-pid"),
            dead_verdict("missing-pid"),
        );
        assert_eq!(
            run_scenario(&host, &registry, job.clone(), AdaptOptions::default())
                .expect_err("invalid registry")
                .token,
            "registry-invalid"
        );

        let mut mismatched = active_entry(&job);
        mismatched.clone_path = sandbox.path().canonicalize().expect("sandbox path");
        write_entry_at(&mismatched, Some(&registry)).expect("mismatched registry");
        assert_eq!(
            run_scenario(&host, &registry, job, AdaptOptions::default())
                .expect_err("identity mismatch")
                .token,
            "registry-identity-mismatch"
        );
        let valid_job = spec(sandbox.path());
        let mut invalid = active_entry(&valid_job);
        invalid.daemon.pid = 0;
        write_entry_at(&invalid, Some(&registry)).expect("invalid registry");
        assert_eq!(
            run_scenario(&host, &registry, valid_job, AdaptOptions::default())
                .expect_err("invalid identity")
                .token,
            "registry-invalid"
        );
        assert_eq!(host.starts.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn done_formatter_preserves_ordered_rows() {
        assert_eq!(
            format_done(&[
                ("FIRST".to_owned(), "one".to_owned()),
                ("FIRST".to_owned(), "two".to_owned())
            ]),
            "BGJOB_STATUS=DONE\nFIRST=one\nFIRST=two\n"
        );
    }

    #[test]
    fn completed_rows_reject_malformed_records_and_preserve_duplicate_order() {
        let valid = parse_completed_rows(
            "BGJOB_RC=0\nSTEP=demo-step\nDUP=one\nDUP=two\n",
            "demo-step",
        )
        .expect("valid completed rows");
        assert_eq!(
            valid,
            vec![
                ("BGJOB_RC".to_owned(), "0".to_owned()),
                ("STEP".to_owned(), "demo-step".to_owned()),
                ("DUP".to_owned(), "one".to_owned()),
                ("DUP".to_owned(), "two".to_owned()),
            ]
        );
        for malformed in [
            "BGJOB_RC=0\nSTEP=demo-step\nnot-a-kv\n",
            "=0\nSTEP=demo-step\n",
            "STEP=demo-step\n",
            "BGJOB_RC=0\nSTEP=other\n",
        ] {
            assert!(parse_completed_rows(malformed, "demo-step").is_none());
        }
    }

    #[test]
    fn parser_preserves_full_adapter_contract() {
        let arguments = [
            "--step",
            "demo-step",
            "--tmpdir",
            "/tmp/session",
            "--run-id",
            "run-1",
            "--budget-s",
            "30",
            "--merge-result-env",
            "/tmp/session/bgjob/demo-step.merge.env",
            "--initial-merge-row",
            "OUTCOME=continue=now",
            "--replace-completed-result",
            "--",
            "python3",
            "worker.py",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        let parsed = parse_arguments(&arguments).expect("adapter arguments");

        assert_eq!(parsed.step, "demo-step");
        assert_eq!(parsed.tmpdir, "/tmp/session");
        assert_eq!(parsed.run_id, "run-1");
        assert_eq!(parsed.budget_s, Some(30));
        assert_eq!(
            parsed.initial_merge_rows,
            vec![("OUTCOME".to_owned(), "continue=now".to_owned())]
        );
        assert!(parsed.replace_completed_result);
        assert_eq!(parsed.command, ["python3", "worker.py"]);

        let malformed = [
            "--step",
            "demo-step",
            "--budget-s",
            "30",
            "--initial-merge-row",
            "OUTCOME=continue\nforged",
            "--",
            "worker",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        assert!(matches!(parse_arguments(&malformed), Err("invalid-input")));
    }

    #[test]
    fn parser_and_path_helpers_reject_malformed_inputs() {
        let resolver = [
            "--resolve-session-env",
            "--session-env-path=/tmp/session-env.sh",
            "--owner-pid",
            "123",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        assert_eq!(
            parse_resolver_arguments(&resolver).expect("resolver arguments"),
            (PathBuf::from("/tmp/session-env.sh"), "123".to_owned())
        );
        assert!(parse_resolver_arguments(&[OsString::from("--resolve-session-env")]).is_err());
        assert_eq!(
            parse_single_kv_row("OUTCOME=continue=now"),
            Some(("OUTCOME".to_owned(), "continue=now".to_owned()))
        );
        assert!(parse_single_kv_row("OUTCOME=continue\nFORGED=value").is_none());
        assert!(parse_single_kv_row("not-a-row").is_none());
        for value in ["1", "1234567"] {
            assert!(valid_owner_pid(value), "{value}");
        }
        for value in ["", "0", "01", "12345678", "12x"] {
            assert!(!valid_owner_pid(value), "{value:?}");
        }
        assert_eq!(
            run_id_from_line("export LARCH_RUN_ID='run-1'"),
            Some("run-1".to_owned())
        );
        assert_eq!(
            run_id_from_line("LARCH_RUN_ID=run-2"),
            Some("run-2".to_owned())
        );
        assert_eq!(run_id_from_line("OTHER=value"), None);

        let sandbox = tempfile::tempdir().expect("tempdir");
        let current = sandbox.path().canonicalize().expect("canonical sandbox");
        assert_eq!(
            resolve_tmpdir(
                current.to_str().expect("utf8 path"),
                &SessionValues::default()
            )
            .expect("selected tmpdir"),
            current
        );
        let other = tempfile::tempdir().expect("other");
        let values = SessionValues {
            rows: vec![(
                "DESIGN_TMPDIR".to_owned(),
                other.path().display().to_string(),
            )],
        };
        assert_eq!(
            resolve_tmpdir(current.to_str().expect("utf8 path"), &values)
                .expect_err("mismatched tmpdir")
                .token,
            "session-env-tmpdir-mismatch"
        );
        assert_eq!(
            resolve_run_id("run-explicit", &current, &current),
            "run-explicit"
        );

        let trusted = sandbox.path().join("trusted.env");
        fs::write(&trusted, "KEY=value\n").expect("trusted file");
        assert_eq!(
            read_trusted_regular(&trusted, &current).expect("trusted read"),
            Some("KEY=value\n".to_owned())
        );
        assert_eq!(
            read_trusted_regular(&current.join("missing.env"), &current).expect("missing read"),
            None
        );
        assert!(read_trusted_regular(other.path(), &current).is_err());
        assert!(
            stat_fingerprint(&trusted)
                .expect("fingerprint result")
                .is_some()
        );

        let plugin_root = sandbox.path().join("plugin-root.env");
        fs::write(&plugin_root, "CLAUDE_PLUGIN_ROOT=/plugin\n").expect("plugin root file");
        assert_eq!(
            plugin_root_from_file(&plugin_root, "CLAUDE_PLUGIN_ROOT").expect("plugin root"),
            "/plugin"
        );
        fs::write(&plugin_root, "CLAUDE_PLUGIN_ROOT=/plugin\r\n").expect("invalid plugin root");
        assert_eq!(
            plugin_root_from_file(&plugin_root, "CLAUDE_PLUGIN_ROOT")
                .expect_err("carriage return")
                .token,
            "plugin-root-invalid"
        );
    }

    fn wire_arguments(
        tmpdir: &Path,
        sentinel: &Path,
        merge: &Path,
        log_dir: &Path,
    ) -> Vec<OsString> {
        [
            "--step",
            "demo-step",
            "--tmpdir",
            tmpdir.to_str().expect("utf8 tmpdir"),
            "--run-id",
            "run-1",
            "--budget-s=30",
            "--log-dir",
            log_dir.to_str().expect("utf8 log dir"),
            "--owner-pid",
            "123",
            "--sentinel",
            sentinel.to_str().expect("utf8 sentinel"),
            "--clear-on-fresh",
            tmpdir.join("clear.env").to_str().expect("utf8 clear path"),
            "--input-fingerprint",
            "fingerprint",
            "--merge-result-env",
            merge.to_str().expect("utf8 merge path"),
            "--initial-merge-row",
            "OUTCOME=continue",
            "--replace-completed-result",
            "--",
            "worker",
        ]
        .into_iter()
        .map(OsString::from)
        .collect()
    }

    #[test]
    fn request_builder_preserves_wire_options() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        let tmpdir = sandbox.path().canonicalize().expect("canonical tmpdir");
        let sentinel = tmpdir.join("sentinel.env");
        let merge = tmpdir.join("merge.env");
        let log_dir = tmpdir.join("logs");
        let arguments = wire_arguments(&tmpdir, &sentinel, &merge, &log_dir);
        let (job, options, session_values, owner_pid) =
            build_request(parse_arguments(&arguments).expect("arguments")).expect("request");
        assert_eq!(session_values.rows, Vec::<(String, String)>::new());
        assert_eq!(job.sentinel_paths, vec![sentinel]);
        assert_eq!(job.merge_result_env, Some(merge));
        assert_eq!(
            job.initial_merge_rows,
            [("OUTCOME".to_owned(), "continue".to_owned())]
        );
        assert_eq!(options.clear_on_fresh, Some(tmpdir.join("clear.env")));
        assert!(options.replace_completed_result);
        assert_eq!(options.input_fingerprint, "fingerprint");
        assert_eq!(owner_pid, "123");
    }

    #[test]
    fn python_start_command_preserves_the_wire_contract() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        let tmpdir = sandbox.path().canonicalize().expect("canonical tmpdir");
        let sentinel = tmpdir.join("sentinel.env");
        let merge = tmpdir.join("merge.env");
        let log_dir = tmpdir.join("logs");
        let arguments = wire_arguments(&tmpdir, &sentinel, &merge, &log_dir);
        let (job, _, _, owner_pid) =
            build_request(parse_arguments(&arguments).expect("arguments")).expect("request");

        let request = StartRequest {
            spec: job,
            plugin_root: current_dir(),
            session_values: SessionValues {
                rows: vec![("SESSION_ID".to_owned(), "session one".to_owned())],
            },
            owner_pid,
        };
        let command = python_start_command(&request);
        assert_eq!(command.get_program(), "python3");
        let args = command
            .get_args()
            .map(|argument| argument.to_str().expect("utf8 argument"))
            .collect::<Vec<_>>();
        assert_eq!(
            args,
            [
                current_dir()
                    .join("python/cli.py")
                    .to_str()
                    .expect("utf8 cli"),
                "bgjob",
                "start",
                "--step",
                "demo-step",
                "--tmpdir",
                tmpdir.to_str().expect("utf8 tmpdir"),
                "--run-id",
                "run-1",
                "--budget-s",
                "30",
                "--log-dir",
                log_dir
                    .canonicalize()
                    .expect("canonical log dir")
                    .to_str()
                    .expect("utf8 log dir"),
                "--owner-pid",
                "123",
                "--sentinel",
                sentinel.to_str().expect("utf8 sentinel"),
                "--merge-result-env",
                merge.to_str().expect("utf8 merge"),
                "--",
                "worker",
            ]
        );
        assert!(command.get_envs().any(|(key, value)| {
            key == "SESSION_ID" && value == Some(std::ffi::OsStr::new("session one"))
        }));
        assert!(command.get_envs().any(|(key, value)| {
            key == "CLAUDE_PLUGIN_ROOT" && value == Some(current_dir().as_os_str())
        }));
    }

    #[test]
    fn started_stdout_validation_preserves_the_wire_contract() {
        assert_eq!(
            validate_started_stdout(
                "BGJOB_STATUS=STARTED STEP=demo-step PGID=303\n".to_owned(),
                "demo-step"
            )
            .expect("valid start"),
            "BGJOB_STATUS=STARTED STEP=demo-step PGID=303\n"
        );
        assert_eq!(
            validate_started_stdout("BGJOB_STATUS=DONE\n".to_owned(), "demo-step")
                .expect_err("invalid start")
                .token,
            "daemon-start-failed"
        );
    }

    #[test]
    fn top_level_and_system_owner_paths_have_stable_outcomes() {
        assert_eq!(
            adapt(&[OsString::from("--help")]),
            std::process::ExitCode::SUCCESS
        );
        assert_eq!(
            adapt(&[OsString::from("--unknown")]),
            std::process::ExitCode::from(2)
        );
        assert_eq!(
            adapt(&[
                OsString::from("--resolve-session-env"),
                OsString::from("--unknown"),
            ]),
            std::process::ExitCode::from(2)
        );
        let host = SystemAdapterHost::new();
        assert_eq!(
            host.validated_owner_pid("not-a-pid")
                .expect_err("invalid owner")
                .token,
            "invalid-input"
        );
        let current_pid = std::process::id().to_string();
        assert_eq!(
            host.validated_owner_pid(&current_pid)
                .expect("current owner"),
            current_pid
        );

        let sandbox = tempfile::tempdir().expect("tempdir");
        let invalid_request = [
            "--step",
            "bad/step",
            "--tmpdir",
            sandbox.path().to_str().expect("utf8 tmpdir"),
            "--budget-s",
            "30",
            "--",
            "worker",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        assert_eq!(adapt(&invalid_request), std::process::ExitCode::from(2));
        assert_eq!(
            write_stdout("BGJOB_STATUS=STARTED\n"),
            std::process::ExitCode::SUCCESS
        );
    }

    #[test]
    fn session_plugin_lock_and_unlink_helpers_are_isolated_and_fail_closed() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        let source = sandbox.path().join("session-env.sh");
        fs::write(
            &source,
            format!(
                "#!/usr/bin/env bash\n# comment\nexport CLAUDE_PLUGIN_ROOT=/ignored\nexport DESIGN_TMPDIR={}\nexport SESSION_ID='session one'\n",
                sandbox.path().display(),
            ),
        )
        .expect("session env");
        assert_eq!(
            session_env_source(&source, "").expect("session source"),
            source
        );
        assert!(!trusted_session_link(
            &sandbox.path().join("not-the-session-link"),
            "123"
        ));
        assert_eq!(
            resolve_session_env_argv(&[
                OsString::from("--resolve-session-env"),
                OsString::from("--session-env-path"),
                source.into_os_string(),
            ]),
            std::process::ExitCode::SUCCESS
        );
        assert_eq!(
            session_env_source(sandbox.path(), "")
                .expect_err("directory source")
                .token,
            "session-env-missing"
        );

        let plugin_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../..")
            .canonicalize()
            .expect("repository root");
        fs::write(
            sandbox.path().join("plugin-root.env"),
            format!("CLAUDE_PLUGIN_ROOT={}\n", plugin_root.display()),
        )
        .expect("plugin root env");
        assert_eq!(
            rehydrate_plugin_root_from(sandbox.path(), None).expect("file plugin root"),
            plugin_root
        );
        assert_eq!(
            rehydrate_plugin_root_from(sandbox.path(), Some(plugin_root.clone().into_os_string()),)
                .expect("configured plugin root"),
            plugin_root
        );
        assert_eq!(
            rehydrate_plugin_root_from(
                sandbox.path(),
                Some(OsString::from("${CLAUDE_PLUGIN_ROOT}")),
            )
            .expect_err("placeholder plugin root")
            .token,
            "plugin-root-missing"
        );

        let registry = sandbox.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");
        let regular = registry.join("regular.env");
        fs::write(&regular, "STATE=ready\n").expect("regular file");
        unlink_regular_under(&regular, &registry, "unlink-failed").expect("unlink regular");
        assert!(!regular.exists());
        unlink_regular_under(&regular, &registry, "unlink-failed").expect("unlink missing");
        assert!(unlink_regular_under(&registry, &registry, "unlink-failed").is_err());
        assert!(stat_fingerprint(&registry).is_err());
        assert!(read_trusted_regular(&registry, &registry).is_err());
        let Err(error) = DecisionLock::open(&registry, "bad/run", "demo-step") else {
            panic!("unsafe lock name must fail");
        };
        assert_eq!(error.token, "lock-failed");
        let _lock = DecisionLock::open(&registry, "run-1", "demo-step").expect("decision lock");
    }

    #[test]
    fn process_state_and_session_env_errors_are_classified_stably() {
        let live = process_state(&verdict(true));
        assert!(live.live);
        assert!(!live.proven_dead);
        let missing = process_state(&dead_verdict("missing-pid"));
        assert!(!missing.live);
        assert!(missing.proven_dead);
        assert!(!missing.identity_mismatch);
        assert!(process_state(&dead_verdict("expected-command-mismatch")).identity_mismatch);

        let sandbox = tempfile::tempdir().expect("tempdir");
        let empty = sandbox.path().join("empty-env.sh");
        fs::write(&empty, "# no design tmpdir\n").expect("empty session env");
        assert_eq!(
            resolve_session_env(&empty, "")
                .expect_err("missing design tmpdir")
                .token,
            "design-tmpdir-missing"
        );
        let malformed = sandbox.path().join("malformed-env.sh");
        fs::write(
            &malformed,
            format!(
                "export DESIGN_TMPDIR={}\nUNTRUSTED=value\n",
                sandbox.path().display()
            ),
        )
        .expect("malformed session env");
        assert_eq!(
            resolve_session_env(&malformed, "")
                .expect_err("malformed session env")
                .token,
            "session-env-malformed"
        );
        assert_eq!(
            resolve_session_env(&sandbox.path().join("missing-env.sh"), "")
                .expect_err("missing session env")
                .token,
            "session-env-missing"
        );
    }

    #[test]
    fn adapter_help_does_not_consume_child_help_flag() {
        let arguments = ["--step", "demo-step", "--", "worker", "--help"]
            .into_iter()
            .map(OsString::from)
            .collect::<Vec<_>>();

        assert!(!has_top_level_option(&arguments, "--help"));
    }

    #[test]
    fn session_env_preserves_source_order_for_wrapper_exports() {
        let tempdir = tempfile::tempdir().expect("tempdir");
        let source = tempdir.path().join("session-env.sh");
        fs::write(
            &source,
            format!(
                "export SESSION_ID='session one'\nexport DESIGN_TMPDIR={}\n",
                tempdir.path().display()
            ),
        )
        .expect("session env");

        let values = resolve_session_env(&source, "").expect("session values");
        let canonical_tmpdir = tempdir.path().canonicalize().expect("canonical tmpdir");

        assert_eq!(
            values.rows,
            vec![
                ("SESSION_ID".to_owned(), "session one".to_owned()),
                (
                    "DESIGN_TMPDIR".to_owned(),
                    canonical_tmpdir.display().to_string(),
                ),
            ]
        );
        assert_eq!(shell_quote("session one"), "'session one'");
    }

    #[cfg(unix)]
    #[test]
    fn design_tmpdir_resolver_accepts_an_allowed_directory_symlink() {
        use std::os::unix::fs::symlink;

        let sandbox = tempfile::tempdir().expect("tempdir");
        let target = sandbox.path().join("target");
        let link = sandbox.path().join("link");
        fs::create_dir(&target).expect("target directory");
        symlink(&target, &link).expect("directory symlink");

        assert_eq!(
            validate_design_tmpdir(link.to_str().expect("utf8 path")).expect("trusted tmpdir"),
            target.canonicalize().expect("canonical target")
        );
    }

    #[cfg(unix)]
    #[test]
    fn decision_lock_is_close_on_exec() {
        use nix::{
            fcntl::{FcntlArg, FdFlag, OFlag, fcntl, open},
            sys::stat::Mode,
        };

        let tempdir = tempfile::tempdir().expect("tempdir");
        let registry = tempdir.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");
        let root = open(
            &registry,
            OFlag::O_RDONLY | OFlag::O_DIRECTORY | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
            Mode::empty(),
        )
        .expect("registry root");
        let lock = super::open_lock_file(&root, "run-1-demo-step.lock").expect("lock");
        let flags = fcntl(&lock, FcntlArg::F_GETFD).expect("fcntl flags");

        assert!(FdFlag::from_bits_truncate(flags).contains(FdFlag::FD_CLOEXEC));
    }
}
