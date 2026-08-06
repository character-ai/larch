//! Rust-owned background-job daemon start, wait, status, and reap.
//!
//! `start` validates its request, then re-executes this same binary in the
//! detached daemon role. The daemon owns the child process group, the durable
//! registry row, and the completed result envelope; `wait` is the only
//! foreground reader of that envelope.

use crate::argparse_compat::{split_inline_option, take_option_value, utf8_arguments};
use larch_adapters::SystemProcessIdentityHost;
use larch_core::{
    BGJOB_RC_ORPHANED, BGJOB_RC_TIMEOUT, BGJOB_STATUS_DEAD, BGJOB_STATUS_DONE, BGJOB_STATUS_KEY,
    BGJOB_STATUS_STARTED, BGJOB_STATUS_WAIT, BGJOB_WAIT_HARD_DEADLINE_GRACE_S,
    BGJOB_WAIT_MAX_CHUNK_S, BgjobError, JobSpec, OwnerIdentity, OwnerValidationState,
    RecordedProcessIdentity, RegistryEntry, ValidationResult, bgjob_dir, check_owner_validation,
    checked_dir, child_liveness, daemon_liveness, daemon_poll_interval_s, ensure_under,
    entry_expired, epoch_now, iter_entries, log_paths, log_tail, merge_rows, ordered_rows,
    orphan_diagnostic, owner_grace_s, owner_pid_candidate, private_atomic_write, read_entry,
    read_for, read_process_identity, render_rows, resolve_run_id, result_env_path, result_rows,
    startup_env_path, startup_in_progress, startup_rows, terminate_validated_process_group,
    unlink_entry, validate_run_id, validate_slug, validate_timing_overrides, write_entry,
};
use nix::unistd::{Pid, getpgid, setsid};
use std::{
    env,
    ffi::OsString,
    fs::{self, File, OpenOptions},
    io::{BufRead as _, BufReader, Write as _},
    os::unix::{
        fs::OpenOptionsExt as _,
        process::{CommandExt as _, ExitStatusExt as _},
    },
    path::{Path, PathBuf},
    process::{Child, Command, ExitCode, Stdio},
    thread,
    time::{Duration, Instant},
};

/// Marks the re-executed process that owns the detached monitor loop.
const ENV_DAEMON_ROLE: &str = "LARCH_BGJOB_DAEMON_ROLE";
/// Carries the owner identity the launching process already captured.
const ENV_DAEMON_OWNER: &str = "LARCH_BGJOB_DAEMON_OWNER";
/// Session temporary directory consulted when `--tmpdir` is omitted.
const ENV_IMPLEMENT_TMPDIR: &str = "IMPLEMENT_TMPDIR";
const IDENTITY_CAPTURE_TIMEOUT: Duration = Duration::from_secs(5);
const IDENTITY_CAPTURE_SLEEP: Duration = Duration::from_millis(50);
const CHILD_REAP_TIMEOUT: Duration = Duration::from_secs(5);
const MIN_POLL_SLEEP: f64 = 0.05;
const DAEMON_CALLER: &str = "bgjob-daemon";
const REAP_CALLER: &str = "bgjob-reap";

#[derive(Clone, Debug, Default)]
struct StartArguments {
    step: String,
    tmpdir: String,
    run_id: String,
    budget_s: Option<i64>,
    log_dir: String,
    owner_pid: String,
    sentinels: Vec<String>,
    merge_result_env: String,
    command: Vec<String>,
}

#[derive(Clone, Debug)]
struct WaitArguments {
    step: String,
    tmpdir: String,
    run_id: String,
    max_wait_s: i64,
    poll_interval_s: f64,
}

impl Default for WaitArguments {
    fn default() -> Self {
        Self {
            step: String::new(),
            tmpdir: String::new(),
            run_id: String::new(),
            max_wait_s: BGJOB_WAIT_MAX_CHUNK_S,
            poll_interval_s: 1.0,
        }
    }
}

/// Launch a detached background job, or run the detached monitor loop.
#[must_use]
pub fn start(arguments: &[OsString]) -> ExitCode {
    if requests_help(arguments) {
        return help(
            "usage: bgjob start --step STEP [--tmpdir PATH] --budget-s SECONDS [options] -- COMMAND...",
        );
    }
    let parsed = match parse_start(arguments) {
        Ok(parsed) => parsed,
        Err(token) => return error(token),
    };
    if env::var_os(ENV_DAEMON_ROLE).is_some() {
        // The daemon owns the acknowledgement pipe, so it never prints
        // diagnostics: a post-acknowledgement write would race a closed reader.
        return build_spec(&parsed, inherited_owner())
            .map_err(|error| one_line(&error))
            .and_then(|spec| daemon_body(&spec))
            .map_or_else(|_| ExitCode::from(2), |()| ExitCode::SUCCESS);
    }
    match launch(&parsed) {
        Ok(output) => {
            print!("{output}");
            ExitCode::SUCCESS
        }
        Err(message) => error(&message),
    }
}

/// Report the completed result, a chunk timeout, or an unrecoverable daemon.
#[must_use]
pub fn wait(arguments: &[OsString]) -> ExitCode {
    if requests_help(arguments) {
        return help("usage: bgjob wait --step STEP [--tmpdir PATH] [--max-wait-s SECONDS]");
    }
    let parsed = match parse_wait(arguments) {
        Ok(parsed) => parsed,
        Err(token) => return error(token),
    };
    if parsed.max_wait_s > BGJOB_WAIT_MAX_CHUNK_S {
        return error(&format!("max-wait-too-large MAX={BGJOB_WAIT_MAX_CHUNK_S}"));
    }
    match wait_once(&parsed) {
        Ok(output) => {
            print!("{output}");
            ExitCode::SUCCESS
        }
        Err(message) => error(&message),
    }
}

/// Print one row per durable registry entry with its child liveness.
#[must_use]
pub fn status(arguments: &[OsString]) -> ExitCode {
    if requests_help(arguments) {
        return help("usage: bgjob status");
    }
    let host = SystemProcessIdentityHost::new();
    let mut output = String::new();
    for (path, entry) in iter_entries() {
        let row = match entry {
            None => format!("BGJOB_STATUS=INVALID REGISTRY={}\n", path.display()),
            Some(entry) => {
                let live = child_liveness(&host, &entry);
                format!(
                    "BGJOB_STATUS=REGISTRY STEP={} RUN_ID={} LIVE={} REASON={}\n",
                    entry.step, entry.run_id, live.live, live.reason
                )
            }
        };
        output.push_str(&row);
    }
    print!("{output}");
    ExitCode::SUCCESS
}

/// Remove finished, unreadable, and expired registry entries.
#[must_use]
pub fn reap(arguments: &[OsString]) -> ExitCode {
    if requests_help(arguments) {
        return help("usage: bgjob reap");
    }
    let host = SystemProcessIdentityHost::new();
    let mut count = 0_u64;
    for (path, entry) in iter_entries() {
        let Some(entry) = entry else {
            unlink_entry(&path);
            count += 1;
            continue;
        };
        let completed = fs::symlink_metadata(&entry.result_env)
            .is_ok_and(|metadata| !metadata.file_type().is_symlink() && metadata.is_file());
        if completed
            || (!child_liveness(&host, &entry).live && !daemon_liveness(&host, &entry).live)
        {
            unlink_entry(&path);
            count += 1;
            continue;
        }
        if entry_expired(&entry) {
            let _ = terminate_validated_process_group(
                &host,
                &entry.child,
                None,
                REAP_CALLER,
                "expired-registry",
            );
            unlink_entry(&path);
            count += 1;
        }
    }
    println!("BGJOB_REAPED={count}");
    ExitCode::SUCCESS
}

/// Launch the detached daemon for `spec` and return its `STARTED` stdout line.
///
/// `extra_env` is applied to the daemon and therefore to the job child, which
/// is how a rehydrated session environment reaches the launched command.
///
/// # Errors
///
/// Returns a one-line failure message when the daemon cannot be launched or
/// never acknowledges its child.
pub fn spawn_daemon(spec: &JobSpec, extra_env: &[(String, String)]) -> Result<String, String> {
    validate_timing_overrides().map_err(|error| one_line(&error))?;
    let executable = env::current_exe().map_err(|error| one_line(&error))?;
    let mut command = Command::new(executable); // lint-subprocess-via-runner: ok the daemon must outlive this process, so it cannot be a runner-owned child
    command
        .args(daemon_arguments(spec))
        .env(ENV_DAEMON_ROLE, "1")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    for (key, value) in extra_env {
        command.env(key, value);
    }
    if let Some(owner) = spec.owner.recorded.as_ref() {
        command.env(ENV_DAEMON_OWNER, render_rows(&owner_rows(owner)));
    } else {
        command.env_remove(ENV_DAEMON_OWNER);
    }
    // The daemon inherits this process group so its own `setsid` can succeed;
    // a spawn-time process group would make it a leader and block detachment.
    let mut child = command.spawn().map_err(|error| one_line(&error))?;
    let Some(pgid) = read_acknowledgement(&mut child) else {
        return Err("daemon-start-failed".to_owned());
    };
    Ok(format!(
        "{BGJOB_STATUS_KEY}={BGJOB_STATUS_STARTED} STEP={} PGID={pgid}\n",
        spec.step
    ))
}

fn read_acknowledgement(child: &mut Child) -> Option<String> {
    let stdout = child.stdout.take()?;
    let mut line = String::new();
    let _ = BufReader::new(stdout).read_line(&mut line).ok()?;
    let parts: Vec<&str> = line.split_whitespace().collect();
    let [_child_pid, pgid] = parts.as_slice() else {
        return None;
    };
    Some((*pgid).to_owned())
}

fn daemon_arguments(spec: &JobSpec) -> Vec<OsString> {
    let mut arguments: Vec<OsString> = vec![
        "bgjob".into(),
        "start".into(),
        "--step".into(),
        spec.step.clone().into(),
        "--tmpdir".into(),
        spec.tmpdir.clone().into(),
        "--run-id".into(),
        spec.run_id.clone().into(),
        "--budget-s".into(),
        spec.budget_s.to_string().into(),
        "--log-dir".into(),
        spec.log_dir.clone().into(),
    ];
    for sentinel in &spec.sentinel_paths {
        arguments.push("--sentinel".into());
        arguments.push(sentinel.clone().into());
    }
    if let Some(merge) = spec.merge_result_env.as_ref() {
        arguments.push("--merge-result-env".into());
        arguments.push(merge.clone().into());
    }
    arguments.push("--".into());
    arguments.extend(spec.command.iter().map(Into::into));
    arguments
}

fn launch(parsed: &StartArguments) -> Result<String, String> {
    let owner = owner_identity_from_env(&parsed.owner_pid).map_err(|error| one_line(&error))?;
    let spec = build_spec(parsed, owner).map_err(|error| one_line(&error))?;
    spawn_daemon(&spec, &[])
}

fn inherited_owner() -> OwnerIdentity {
    OwnerIdentity {
        recorded: owner_from_rows(&env::var(ENV_DAEMON_OWNER).unwrap_or_default()),
    }
}

fn owner_from_rows(text: &str) -> Option<RecordedProcessIdentity> {
    let rows = ordered_rows(text);
    let value = |key: &str| {
        rows.iter()
            .find(|(candidate, _)| candidate == key)
            .map(|(_, value)| value.clone())
    };
    Some(RecordedProcessIdentity {
        pid: value("PID")?.parse().ok()?,
        pgid: value("PGID")?.parse().ok()?,
        start_time: value("START_TIME")?,
        command_signature: value("COMMAND")?,
        expected_signature: value("EXPECTED").unwrap_or_default(),
    })
}

fn owner_rows(owner: &RecordedProcessIdentity) -> Vec<(String, String)> {
    vec![
        ("PID".to_owned(), owner.pid.to_string()),
        ("PGID".to_owned(), owner.pgid.to_string()),
        ("START_TIME".to_owned(), owner.start_time.clone()),
        ("COMMAND".to_owned(), owner.command_signature.clone()),
        ("EXPECTED".to_owned(), owner.expected_signature.clone()),
    ]
}

fn owner_identity_from_env(explicit: &str) -> Result<OwnerIdentity, BgjobError> {
    let candidate = owner_pid_candidate(explicit).ok_or_else(|| {
        BgjobError::Invalid(
            "could not capture process identity for owner pid: missing session owner pid"
                .to_owned(),
        )
    })?;
    let missing = || {
        BgjobError::Invalid(format!(
            "could not capture process identity for owner pid {candidate}"
        ))
    };
    let pid = candidate
        .parse::<i32>()
        .ok()
        .filter(|pid| *pid > 0)
        .ok_or_else(missing)?;
    let host = SystemProcessIdentityHost::new();
    let recorded = read_process_identity(&host, pid, "").ok_or_else(missing)?;
    Ok(OwnerIdentity {
        recorded: Some(recorded),
    })
}

fn build_spec(parsed: &StartArguments, owner: OwnerIdentity) -> Result<JobSpec, BgjobError> {
    let step = validate_slug(&parsed.step, "step")?;
    let tmpdir = checked_dir(Path::new(&parsed.tmpdir), "tmpdir", true)?;
    let clone_path = env::current_dir().map_err(|error| BgjobError::Io(error.to_string()))?;
    let run_id = resolve_run_id(&parsed.run_id, &tmpdir, &clone_path);
    let log_dir_argument = (!parsed.log_dir.is_empty()).then(|| PathBuf::from(&parsed.log_dir));
    let (log_dir, _, _) = log_paths(&tmpdir, log_dir_argument.as_deref(), &step)?;
    let sentinel_paths = parsed
        .sentinels
        .iter()
        .map(|raw| ensure_under(Path::new(raw), &tmpdir, "sentinel"))
        .collect::<Result<Vec<_>, _>>()?;
    let merge_result_env = match parsed.merge_result_env.as_str() {
        "" => None,
        raw => Some(checked_merge_env(Path::new(raw))?),
    };
    Ok(JobSpec {
        step,
        tmpdir,
        log_dir,
        budget_s: parsed.budget_s.unwrap_or_default(),
        command: parsed.command.clone(),
        run_id,
        owner,
        sentinel_paths,
        merge_result_env,
        initial_merge_rows: Vec::new(),
    })
}

fn checked_merge_env(path: &Path) -> Result<PathBuf, BgjobError> {
    let is_link = |candidate: &Path| {
        fs::symlink_metadata(candidate).is_ok_and(|metadata| metadata.file_type().is_symlink())
    };
    if is_link(path) {
        return Err(BgjobError::Invalid(format!(
            "merge-result-env must not be a symlink: {}",
            path.display()
        )));
    }
    if path.parent().is_some_and(is_link) {
        return Err(BgjobError::Invalid(format!(
            "merge-result-env parent must not be a symlink: {}",
            path.display()
        )));
    }
    Ok(path.to_path_buf())
}

/// Return whether the caller asked for usage before the command separator.
fn requests_help(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .take_while(|argument| argument.as_os_str() != "--")
        .any(|argument| argument == "-h" || argument == "--help")
}

fn help(usage: &str) -> ExitCode {
    println!("{usage}");
    ExitCode::SUCCESS
}

fn one_line(error: &impl ToString) -> String {
    error.to_string().replace(['\n', '\r'], " ")
}

fn error(detail: &str) -> ExitCode {
    println!("BGJOB_ERROR={detail}");
    ExitCode::from(2)
}

fn parse_start(arguments: &[OsString]) -> Result<StartArguments, &'static str> {
    let values = utf8_arguments(arguments, "invalid-argument-encoding")?;
    let mut parsed = StartArguments::default();
    let mut index = 0;
    while index < values.len() {
        let value = &values[index];
        if value == "--" {
            parsed.command.extend_from_slice(&values[index + 1..]);
            break;
        }
        if !value.starts_with('-') {
            parsed.command.extend_from_slice(&values[index..]);
            break;
        }
        let (name, inline) = split_inline_option(value);
        match name {
            "--step" => {
                parsed.step =
                    take_option_value(&values, &mut index, inline, "missing-option-argument")?;
            }
            "--tmpdir" => {
                parsed.tmpdir =
                    take_option_value(&values, &mut index, inline, "missing-option-argument")?;
            }
            "--run-id" => {
                parsed.run_id =
                    take_option_value(&values, &mut index, inline, "missing-option-argument")?;
            }
            "--log-dir" => {
                parsed.log_dir =
                    take_option_value(&values, &mut index, inline, "missing-option-argument")?;
            }
            "--owner-pid" => {
                parsed.owner_pid =
                    take_option_value(&values, &mut index, inline, "missing-option-argument")?;
            }
            "--merge-result-env" => {
                parsed.merge_result_env =
                    take_option_value(&values, &mut index, inline, "missing-option-argument")?;
            }
            "--sentinel" => parsed.sentinels.push(take_option_value(
                &values,
                &mut index,
                inline,
                "missing-option-argument",
            )?),
            "--budget-s" => {
                let raw =
                    take_option_value(&values, &mut index, inline, "missing-option-argument")?;
                parsed.budget_s = Some(raw.parse::<i64>().map_err(|_| "invalid-budget")?);
            }
            _ => return Err("unrecognized-argument"),
        }
        index += 1;
    }
    finish_start(parsed)
}

fn finish_start(mut parsed: StartArguments) -> Result<StartArguments, &'static str> {
    if parsed.command.is_empty() {
        return Err("missing-command");
    }
    match parsed.budget_s {
        None => return Err("missing-budget"),
        Some(budget) if budget <= 0 => return Err("invalid-budget"),
        Some(_) => {}
    }
    if parsed.tmpdir.is_empty() {
        parsed.tmpdir = env_string(ENV_IMPLEMENT_TMPDIR);
    }
    if parsed.tmpdir.is_empty() {
        return Err("missing-tmpdir");
    }
    Ok(parsed)
}

fn parse_wait(arguments: &[OsString]) -> Result<WaitArguments, &'static str> {
    let values = utf8_arguments(arguments, "invalid-argument-encoding")?;
    let mut parsed = WaitArguments::default();
    let mut index = 0;
    while index < values.len() {
        let (name, inline) = split_inline_option(&values[index]);
        match name {
            "--step" => {
                parsed.step =
                    take_option_value(&values, &mut index, inline, "missing-option-argument")?;
            }
            "--tmpdir" => {
                parsed.tmpdir =
                    take_option_value(&values, &mut index, inline, "missing-option-argument")?;
            }
            "--run-id" => {
                parsed.run_id =
                    take_option_value(&values, &mut index, inline, "missing-option-argument")?;
            }
            "--max-wait-s" => {
                let raw =
                    take_option_value(&values, &mut index, inline, "missing-option-argument")?;
                parsed.max_wait_s = raw.parse::<i64>().map_err(|_| "invalid-max-wait")?;
            }
            "--poll-interval-s" => {
                let raw =
                    take_option_value(&values, &mut index, inline, "missing-option-argument")?;
                parsed.poll_interval_s = raw.parse::<f64>().map_err(|_| "invalid-poll-interval")?;
            }
            _ => return Err("unrecognized-argument"),
        }
        index += 1;
    }
    if parsed.step.is_empty() {
        return Err("missing-step");
    }
    if parsed.tmpdir.is_empty() {
        parsed.tmpdir = env_string(ENV_IMPLEMENT_TMPDIR);
    }
    if parsed.tmpdir.is_empty() {
        return Err("missing-tmpdir");
    }
    Ok(parsed)
}

fn env_string(name: &str) -> String {
    env::var(name).unwrap_or_default()
}

// ---------------------------------------------------------------------------
// Daemon role
// ---------------------------------------------------------------------------

fn daemon_body(spec: &JobSpec) -> Result<(), String> {
    // Detach from the launching session so the job outlives its orchestrator
    // shell, exactly as the Python daemon's `setsid` did.
    setsid().map_err(|error| one_line(&error))?;
    // Build the identity host before the child exists so capture starts as
    // close to launch as possible: a process that exits first leaves no `ps`
    // row to bind.
    let host = SystemProcessIdentityHost::new();
    fs::create_dir_all(&spec.log_dir).map_err(|error| one_line(&error))?;
    let result = result_env_path(&spec.tmpdir, &spec.step).map_err(|error| one_line(&error))?;
    if let Some(parent) = result.parent() {
        fs::create_dir_all(parent).map_err(|error| one_line(&error))?;
    }
    let _ = fs::remove_file(&result);
    let stdout_log = spec.log_dir.join(format!("{}.stdout.log", spec.step));
    let stderr_log = spec.log_dir.join(format!("{}.stderr.log", spec.step));
    let stdout_handle =
        open_verified_log(&stdout_log, &spec.log_dir).map_err(|error| one_line(&error))?;
    let stderr_handle =
        open_verified_log(&stderr_log, &spec.log_dir).map_err(|error| one_line(&error))?;
    let mut child =
        spawn_job(spec, stdout_handle, stderr_handle).map_err(|error| one_line(&error))?;
    let startup = acknowledge_start(spec, &child)?;
    match register_and_monitor(&host, spec, &mut child, &stdout_log, &stderr_log, &startup) {
        Ok(()) => Ok(()),
        Err(message) => {
            // Publish the failed result before dropping the startup marker: a
            // wait that sees neither artifact reports a spurious dead daemon.
            let _ = write_result(spec, "2", 0);
            let _ = fs::remove_file(&startup);
            Err(message)
        }
    }
}

fn register_and_monitor(
    host: &SystemProcessIdentityHost,
    spec: &JobSpec,
    child: &mut Child,
    stdout_log: &Path,
    stderr_log: &Path,
    startup: &Path,
) -> Result<(), String> {
    let child_pid = i32::try_from(child.id()).map_err(|error| one_line(&error))?;
    let expected = spec
        .command
        .iter()
        .take(2)
        .cloned()
        .collect::<Vec<_>>()
        .join(" ");
    let Some(child_identity) = capture_identity(host, child_pid, &expected) else {
        // A child that finished before its identity could be bound is a
        // completed job, not a launch failure: an exited process leaves no
        // `ps` row to bind, so record its real result code instead.
        if let Ok(Some(status)) = child.try_wait() {
            write_result(spec, &exit_token(status), 0)?;
            let _ = fs::remove_file(startup);
            return Ok(());
        }
        kill_and_reap(host, child, None);
        return Err(format!(
            "could not capture process identity for pid {child_pid}"
        ));
    };
    let daemon_pid = i32::try_from(std::process::id()).map_err(|error| one_line(&error))?;
    let Some(daemon_identity) = capture_identity(host, daemon_pid, "") else {
        kill_and_reap(host, child, Some(&child_identity));
        return Err("could not capture daemon process identity".to_owned());
    };
    let entry = RegistryEntry {
        step: spec.step.clone(),
        run_id: spec.run_id.clone(),
        tmpdir: spec.tmpdir.clone(),
        log_dir: spec.log_dir.clone(),
        clone_path: env::current_dir().map_err(|error| one_line(&error))?,
        daemon: daemon_identity,
        child: child_identity.clone(),
        owner: spec.owner.recorded.clone(),
        start_epoch: epoch_now(),
        budget_s: spec.budget_s,
        stdout_log: stdout_log.to_path_buf(),
        stderr_log: stderr_log.to_path_buf(),
        result_env: result_env_path(&spec.tmpdir, &spec.step).map_err(|error| one_line(&error))?,
    };
    let registry = match write_entry(&entry) {
        Ok(path) => path,
        Err(failure) => {
            kill_and_reap(host, child, Some(&child_identity));
            return Err(one_line(&failure));
        }
    };
    let _ = fs::remove_file(startup);
    monitor(spec, child, &child_identity, &registry, host)
}

/// Render one finished child's result code the way the Python owner did.
fn exit_token(status: std::process::ExitStatus) -> String {
    status
        .code()
        .or_else(|| status.signal().map(|signal| -signal))
        .unwrap_or_default()
        .to_string()
}

fn kill_and_reap(
    host: &SystemProcessIdentityHost,
    child: &mut Child,
    identity: Option<&RecordedProcessIdentity>,
) {
    match identity {
        Some(identity) => {
            let _ = terminate_validated_process_group(
                host,
                identity,
                None,
                DAEMON_CALLER,
                "startup-failed",
            );
        }
        None => {
            let _ = child.kill();
        }
    }
    reap_child(child, CHILD_REAP_TIMEOUT);
}

fn spawn_job(spec: &JobSpec, stdout: File, stderr: File) -> std::io::Result<Child> {
    let (program, arguments) = spec
        .command
        .split_first()
        .ok_or_else(|| std::io::Error::other("empty command"))?;
    let mut command = Command::new(program); // lint-subprocess-via-runner: ok the daemon intentionally owns the long-running job process group
    command
        .args(arguments)
        .stdin(Stdio::null())
        .stdout(Stdio::from(stdout))
        .stderr(Stdio::from(stderr))
        .env_remove(ENV_DAEMON_ROLE)
        .env_remove(ENV_DAEMON_OWNER);
    command.process_group(0);
    command.spawn()
}

fn acknowledge_start(spec: &JobSpec, child: &Child) -> Result<PathBuf, String> {
    let child_pid = i32::try_from(child.id()).map_err(|error| one_line(&error))?;
    let pgid = getpgid(Some(Pid::from_raw(child_pid))).map_err(|error| one_line(&error))?;
    let startup = write_startup_marker(spec).map_err(|error| one_line(&error))?;
    let mut stdout = std::io::stdout();
    stdout
        .write_all(format!("{child_pid} {pgid}\n").as_bytes())
        .and_then(|()| stdout.flush())
        .map_err(|error| one_line(&error))?;
    Ok(startup)
}

fn write_startup_marker(spec: &JobSpec) -> Result<PathBuf, BgjobError> {
    let startup = startup_env_path(&spec.tmpdir, &spec.step)?;
    let root = bgjob_dir(&spec.tmpdir)?;
    let rows = startup_rows(&spec.step, epoch_now());
    private_atomic_write(&startup, &render_rows(&rows), &root)?;
    Ok(startup)
}

fn monitor(
    spec: &JobSpec,
    child: &mut Child,
    child_identity: &RecordedProcessIdentity,
    registry: &Path,
    host: &SystemProcessIdentityHost,
) -> Result<(), String> {
    let grace_s = owner_grace_s().map_err(|error| one_line(&error))?;
    let poll = Duration::from_secs_f64(
        daemon_poll_interval_s()
            .map_err(|error| one_line(&error))?
            .max(0.0),
    );
    let budget = Duration::from_secs(u64::try_from(spec.budget_s.max(0)).unwrap_or(u64::MAX));
    let started = Instant::now();
    let mut owner_state = OwnerValidationState::default();
    let rc_token = loop {
        let now = started.elapsed();
        if let Some(status) = child.try_wait().map_err(|error| one_line(&error))? {
            break exit_token(status);
        }
        if now >= budget {
            terminate(host, child_identity, BGJOB_RC_TIMEOUT);
            break BGJOB_RC_TIMEOUT.to_owned();
        }
        let step = check_owner_validation(
            host,
            spec.owner.recorded.as_ref(),
            owner_state,
            now,
            grace_s,
        );
        owner_state = step.state;
        if let (true, Some(validation)) = (step.orphaned, step.validation.as_ref()) {
            append_orphan_diagnostic(spec, validation, owner_state.failure_count);
            terminate(host, child_identity, BGJOB_RC_ORPHANED);
            break BGJOB_RC_ORPHANED.to_owned();
        }
        thread::sleep(poll);
    };
    let elapsed_s = i64::try_from(started.elapsed().as_secs()).unwrap_or(i64::MAX);
    if rc_token == BGJOB_RC_TIMEOUT || rc_token == BGJOB_RC_ORPHANED {
        reap_child(child, CHILD_REAP_TIMEOUT);
    }
    write_result(spec, &rc_token, elapsed_s)?;
    unlink_entry(registry);
    Ok(())
}

fn terminate(
    host: &SystemProcessIdentityHost,
    child_identity: &RecordedProcessIdentity,
    reason: &str,
) {
    let _ = terminate_validated_process_group(host, child_identity, None, DAEMON_CALLER, reason);
}

fn reap_child(child: &mut Child, timeout: Duration) {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        match child.try_wait() {
            Ok(Some(_)) | Err(_) => return,
            Ok(None) => thread::sleep(IDENTITY_CAPTURE_SLEEP),
        }
    }
}

fn capture_identity(
    host: &SystemProcessIdentityHost,
    pid: i32,
    expected: &str,
) -> Option<RecordedProcessIdentity> {
    let deadline = Instant::now() + IDENTITY_CAPTURE_TIMEOUT;
    loop {
        if let Some(identity) = read_process_identity(host, pid, expected) {
            return Some(identity);
        }
        if Instant::now() >= deadline {
            return None;
        }
        thread::sleep(IDENTITY_CAPTURE_SLEEP);
    }
}

fn write_result(spec: &JobSpec, rc: &str, elapsed_s: i64) -> Result<(), String> {
    let result = result_env_path(&spec.tmpdir, &spec.step).map_err(|error| one_line(&error))?;
    let root = bgjob_dir(&spec.tmpdir).map_err(|error| one_line(&error))?;
    fs::create_dir_all(&root).map_err(|error| one_line(&error))?;
    let merged = spec
        .merge_result_env
        .as_deref()
        .map(read_merge_text)
        .map_or_else(Vec::new, |text| merge_rows(&text));
    let rows = result_rows(&spec.step, rc, elapsed_s, &merged).map_err(|error| one_line(&error))?;
    private_atomic_write(&result, &render_rows(&rows), &root).map_err(|error| one_line(&error))?;
    for sentinel in &spec.sentinel_paths {
        let safe =
            ensure_under(sentinel, &spec.tmpdir, "sentinel").map_err(|error| one_line(&error))?;
        private_atomic_write(&safe, "", &spec.tmpdir).map_err(|error| one_line(&error))?;
    }
    Ok(())
}

fn read_merge_text(path: &Path) -> String {
    if fs::symlink_metadata(path)
        .is_ok_and(|metadata| metadata.file_type().is_symlink() || !metadata.is_file())
    {
        return String::new();
    }
    let Ok(text) = fs::read_to_string(path) else {
        return String::new();
    };
    if text.contains('\r') {
        String::new()
    } else {
        text
    }
}

fn append_orphan_diagnostic(spec: &JobSpec, validation: &ValidationResult, failure_count: u32) {
    let stderr_log = spec.log_dir.join(format!("{}.stderr.log", spec.step));
    let _ = fs::create_dir_all(&spec.log_dir);
    let text = orphan_diagnostic(spec.owner.recorded.as_ref(), validation, failure_count);
    if let Ok(mut handle) = open_verified_log(&stderr_log, &spec.log_dir) {
        let _ = handle.write_all(text.as_bytes());
    }
}

fn open_verified_log(path: &Path, root: &Path) -> Result<File, BgjobError> {
    let root_metadata =
        fs::symlink_metadata(root).map_err(|error| BgjobError::Io(error.to_string()))?;
    if root_metadata.file_type().is_symlink() || !root_metadata.is_dir() {
        return Err(BgjobError::Invalid(format!(
            "log root must be a regular directory: {}",
            root.display()
        )));
    }
    let verified_root =
        fs::canonicalize(root).map_err(|error| BgjobError::Io(error.to_string()))?;
    let verified_path = ensure_under(path, &verified_root, "log file")?;
    if fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(BgjobError::Invalid(format!(
            "log file must not be a symlink: {}",
            path.display()
        )));
    }
    let mut options = OpenOptions::new();
    options.append(true).create(true);
    #[cfg(unix)]
    {
        options.mode(0o600).custom_flags(nix::libc::O_NOFOLLOW);
    }
    let file = options
        .open(&verified_path)
        .map_err(|error| BgjobError::Io(error.to_string()))?;
    let opened = file
        .metadata()
        .map_err(|error| BgjobError::Io(error.to_string()))?;
    if opened.is_file() {
        Ok(file)
    } else {
        Err(BgjobError::Invalid(format!(
            "log file must be regular: {}",
            path.display()
        )))
    }
}

// ---------------------------------------------------------------------------
// Foreground wait
// ---------------------------------------------------------------------------

fn wait_once(parsed: &WaitArguments) -> Result<String, String> {
    let step = validate_slug(&parsed.step, "step").map_err(|error| one_line(&error))?;
    let run_id = match parsed.run_id.as_str() {
        "" => None,
        raw => Some(validate_run_id(raw).map_err(|error| one_line(&error))?),
    };
    let tmpdir = PathBuf::from(&parsed.tmpdir);
    let result_path = result_env_path(&tmpdir, &step).map_err(|error| one_line(&error))?;
    let now = Instant::now();
    let chunk = Duration::from_secs(u64::try_from(parsed.max_wait_s.max(0)).unwrap_or_default());
    let deadline = now + chunk;
    let hard_deadline = deadline + Duration::from_secs(BGJOB_WAIT_HARD_DEADLINE_GRACE_S);
    let host = SystemProcessIdentityHost::new();
    loop {
        if Instant::now() >= hard_deadline {
            return Err("hard-deadline".to_owned());
        }
        if let Some(rows) = read_result(&result_path) {
            return Ok(done_rows(&rows));
        }
        let (registry, entry) =
            read_for(&tmpdir, &step, run_id.as_deref()).map_err(|error| one_line(&error))?;
        let Some(entry) = entry else {
            // `None` means the daemon published its registry row while the
            // startup marker was being watched, so re-read it next iteration.
            // The sleep keeps that re-read a poll rather than a hot spin.
            if let Some(output) = missing_registry(&result_path, &registry, parsed, &step, deadline)
            {
                return Ok(output);
            }
            thread::sleep(poll_sleep(parsed.poll_interval_s, deadline));
            continue;
        };
        let daemon = daemon_liveness(&host, &entry);
        if !daemon.live {
            // The daemon writes its result before exiting; re-read once so a
            // completion observed between the two reads is not reported dead.
            if let Some(rows) = read_result(&result_path) {
                return Ok(done_rows(&rows));
            }
            let tail = stderr_tail(&entry);
            return Ok(dead_rows(&[
                ("BGJOB_DIAG", daemon.reason.as_str()),
                ("STDERR_TAIL", tail.as_str()),
            ]));
        }
        if Instant::now() >= deadline {
            return Ok(wait_rows(parsed.max_wait_s));
        }
        thread::sleep(poll_sleep(parsed.poll_interval_s, deadline));
    }
}

fn missing_registry(
    result_path: &Path,
    registry: &Path,
    parsed: &WaitArguments,
    step: &str,
    deadline: Instant,
) -> Option<String> {
    if let Some(rows) = read_result(result_path) {
        return Some(done_rows(&rows));
    }
    let tmpdir = PathBuf::from(&parsed.tmpdir);
    while startup_marker_live(&tmpdir, step) {
        if Instant::now() >= deadline {
            return Some(wait_rows(parsed.max_wait_s));
        }
        thread::sleep(poll_sleep(parsed.poll_interval_s, deadline));
    }
    // The daemon drops its startup marker only after a durable successor
    // exists, so re-read both before reporting an unrecoverable daemon.
    if let Some(rows) = read_result(result_path) {
        return Some(done_rows(&rows));
    }
    if read_entry(registry).is_some() {
        return None;
    }
    Some(dead_rows(&[
        ("BGJOB_DIAG", "missing-registry"),
        ("REGISTRY", &registry.display().to_string()),
    ]))
}

fn startup_marker_live(tmpdir: &Path, step: &str) -> bool {
    let Ok(path) = startup_env_path(tmpdir, step) else {
        return false;
    };
    let Some(rows) = read_result(&path) else {
        return false;
    };
    startup_in_progress(&rows, step, epoch_now())
}

fn poll_sleep(poll_interval_s: f64, deadline: Instant) -> Duration {
    let remaining = deadline
        .saturating_duration_since(Instant::now())
        .as_secs_f64();
    Duration::from_secs_f64(poll_interval_s.min(remaining).max(MIN_POLL_SLEEP))
}

fn read_result(path: &Path) -> Option<Vec<(String, String)>> {
    let metadata = fs::symlink_metadata(path).ok()?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return None;
    }
    let bytes = fs::read(path).ok()?;
    let text = String::from_utf8_lossy(&bytes);
    if text.contains('\r') {
        return Some(Vec::new());
    }
    Some(ordered_rows(&text))
}

fn stderr_tail(entry: &RegistryEntry) -> String {
    let path = &entry.stderr_log;
    if fs::symlink_metadata(path)
        .is_ok_and(|metadata| metadata.file_type().is_symlink() || !metadata.is_file())
    {
        return String::new();
    }
    fs::read(path)
        .map(|bytes| log_tail(&String::from_utf8_lossy(&bytes)))
        .unwrap_or_default()
}

fn done_rows(rows: &[(String, String)]) -> String {
    let mut out = vec![(BGJOB_STATUS_KEY.to_owned(), BGJOB_STATUS_DONE.to_owned())];
    out.extend(rows.iter().cloned());
    render_rows(&out)
}

fn dead_rows(rows: &[(&str, &str)]) -> String {
    let mut out = vec![(BGJOB_STATUS_KEY.to_owned(), BGJOB_STATUS_DEAD.to_owned())];
    out.extend(
        rows.iter()
            .map(|(key, value)| ((*key).to_owned(), (*value).to_owned())),
    );
    render_rows(&out)
}

fn wait_rows(max_wait_s: i64) -> String {
    render_rows(&[
        (BGJOB_STATUS_KEY.to_owned(), BGJOB_STATUS_WAIT.to_owned()),
        ("ELAPSED_S".to_owned(), max_wait_s.to_string()),
    ])
}

#[cfg(test)]
mod tests {
    use super::{
        MIN_POLL_SLEEP, StartArguments, WaitArguments, checked_merge_env, daemon_arguments,
        dead_rows, done_rows, finish_start, inherited_owner, one_line, open_verified_log,
        owner_from_rows, owner_rows, parse_start, parse_wait, poll_sleep, read_merge_text,
        read_result, wait_rows, write_result,
    };
    use larch_core::{
        BGJOB_ELAPSED_KEY, BGJOB_RC_KEY, BGJOB_WAIT_MAX_CHUNK_S, BgjobError, JobSpec,
        OwnerIdentity, RecordedProcessIdentity, ordered_rows, render_rows,
    };
    use std::{
        ffi::OsString,
        fs,
        path::{Path, PathBuf},
        time::{Duration, Instant},
    };

    fn owner() -> RecordedProcessIdentity {
        RecordedProcessIdentity {
            pid: 4321,
            pgid: 4321,
            start_time: "Fri Jul 3 17:01:02 2026".to_owned(),
            command_signature: "claude --resume".to_owned(),
            expected_signature: String::new(),
        }
    }

    fn spec(tmpdir: &Path) -> JobSpec {
        JobSpec {
            step: "demo-step".to_owned(),
            tmpdir: tmpdir.to_path_buf(),
            log_dir: tmpdir.join("bgjob"),
            budget_s: 10,
            command: vec!["/bin/echo".to_owned(), "hello".to_owned()],
            run_id: "run-1".to_owned(),
            owner: OwnerIdentity {
                recorded: Some(owner()),
            },
            sentinel_paths: Vec::new(),
            merge_result_env: None,
            initial_merge_rows: Vec::new(),
        }
    }

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn start_arguments_require_a_command_a_budget_and_a_tmpdir() {
        let parsed = parse_start(&arguments(&[
            "--step",
            "demo-step",
            "--tmpdir=/tmp/session",
            "--budget-s",
            "30",
            "--sentinel",
            "/tmp/session/done",
            "--merge-result-env",
            "/tmp/session/merge.env",
            "--",
            "/bin/echo",
            "--flagged",
        ]))
        .expect("parsed start arguments");
        assert_eq!(parsed.step, "demo-step");
        assert_eq!(parsed.tmpdir, "/tmp/session");
        assert_eq!(parsed.budget_s, Some(30));
        assert_eq!(parsed.sentinels, ["/tmp/session/done"]);
        assert_eq!(parsed.command, ["/bin/echo", "--flagged"]);

        assert_eq!(
            parse_start(&arguments(&[
                "--step",
                "s",
                "--tmpdir",
                "/tmp",
                "--budget-s",
                "1"
            ]))
            .expect_err("missing command"),
            "missing-command"
        );
        assert_eq!(
            parse_start(&arguments(&[
                "--step",
                "s",
                "--tmpdir",
                "/tmp",
                "--",
                "/bin/echo"
            ]))
            .expect_err("missing budget"),
            "missing-budget"
        );
        assert_eq!(
            parse_start(&arguments(&[
                "--step",
                "s",
                "--tmpdir",
                "/tmp",
                "--budget-s",
                "0",
                "--",
                "/bin/echo"
            ]))
            .expect_err("invalid budget"),
            "invalid-budget"
        );
        assert_eq!(
            parse_start(&arguments(&["--unknown", "x", "--", "/bin/echo"]))
                .expect_err("unknown option"),
            "unrecognized-argument"
        );
        assert_eq!(
            parse_start(&arguments(&["--step"])).expect_err("dangling option"),
            "missing-option-argument"
        );
        assert_eq!(
            finish_start(StartArguments {
                command: vec!["/bin/echo".to_owned()],
                budget_s: Some(1),
                ..StartArguments::default()
            })
            .map_or_else(ToOwned::to_owned, |parsed| parsed.tmpdir),
            std::env::var("IMPLEMENT_TMPDIR").unwrap_or_else(|_| "missing-tmpdir".to_owned())
        );
    }

    #[test]
    fn wait_arguments_default_to_the_maximum_chunk_and_require_a_step() {
        let parsed = parse_wait(&arguments(&[
            "--step",
            "demo-step",
            "--tmpdir",
            "/tmp/session",
            "--run-id",
            "run-1",
            "--poll-interval-s",
            "0.1",
        ]))
        .expect("parsed wait arguments");
        assert_eq!(parsed.max_wait_s, BGJOB_WAIT_MAX_CHUNK_S);
        assert!((parsed.poll_interval_s - 0.1).abs() < f64::EPSILON);
        assert_eq!(
            parse_wait(&arguments(&["--tmpdir", "/tmp"])).expect_err("missing step"),
            "missing-step"
        );
        assert_eq!(
            parse_wait(&arguments(&[
                "--step",
                "s",
                "--tmpdir",
                "/tmp",
                "--max-wait-s",
                "x"
            ]))
            .expect_err("bad chunk"),
            "invalid-max-wait"
        );
        assert_eq!(
            parse_wait(&arguments(&[
                "--step",
                "s",
                "--tmpdir",
                "/tmp",
                "--poll-interval-s",
                "x"
            ]))
            .expect_err("bad interval"),
            "invalid-poll-interval"
        );
    }

    #[test]
    fn owner_identity_round_trips_through_the_daemon_environment() {
        assert_eq!(
            owner_from_rows(&render_rows(&owner_rows(&owner()))),
            Some(owner())
        );
        assert_eq!(owner_from_rows("PID=nope\nPGID=1\n"), None);
        assert_eq!(owner_from_rows("PID=1\n"), None);
        assert_eq!(owner_from_rows(""), None);
        assert!(inherited_owner().recorded.is_none());
    }

    #[test]
    fn daemon_arguments_replay_the_validated_launch_request() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        let mut job = spec(sandbox.path());
        job.sentinel_paths = vec![sandbox.path().join("done")];
        job.merge_result_env = Some(sandbox.path().join("merge.env"));
        let rendered: Vec<String> = daemon_arguments(&job)
            .into_iter()
            .map(|value| value.to_string_lossy().into_owned())
            .collect();
        assert_eq!(&rendered[..4], ["bgjob", "start", "--step", "demo-step"]);
        assert!(rendered.contains(&"--sentinel".to_owned()));
        assert!(rendered.contains(&"--merge-result-env".to_owned()));
        let separator = rendered
            .iter()
            .position(|value| value == "--")
            .expect("command separator");
        assert_eq!(&rendered[separator + 1..], ["/bin/echo", "hello"]);
        assert!(!daemon_arguments(&job).contains(&OsString::from("--owner-pid")));
    }

    #[test]
    fn result_writing_merges_child_rows_and_keeps_daemon_authority() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        fs::create_dir_all(sandbox.path().join("bgjob")).expect("bgjob dir");
        let merge = sandbox.path().join("merge.env");
        fs::write(&merge, "BGJOB_RC=9\nCUSTOM=ok\n").expect("merge env");
        let mut job = spec(sandbox.path());
        job.merge_result_env = Some(merge.clone());
        job.sentinel_paths = vec![sandbox.path().join("done.sentinel")];

        write_result(&job, "0", 7).expect("write result");
        let result = sandbox.path().join("bgjob/demo-step.result.env");
        let rows = ordered_rows(&fs::read_to_string(&result).expect("result text"));
        assert_eq!(
            rows,
            [
                (BGJOB_RC_KEY.to_owned(), "0".to_owned()),
                (BGJOB_ELAPSED_KEY.to_owned(), "7".to_owned()),
                ("STEP".to_owned(), "demo-step".to_owned()),
                ("CUSTOM".to_owned(), "ok".to_owned()),
            ]
        );
        assert!(sandbox.path().join("done.sentinel").is_file());
        assert_eq!(read_result(&result), Some(rows));
        assert_eq!(read_result(&sandbox.path().join("bgjob/absent.env")), None);

        fs::write(&merge, "CUSTOM=carriage\r\n").expect("cr merge env");
        assert_eq!(read_merge_text(&merge), String::new());
        assert_eq!(
            read_merge_text(&sandbox.path().join("absent.env")),
            String::new()
        );
    }

    #[test]
    fn wire_rows_and_path_guards_match_the_published_contract() {
        let sandbox = tempfile::tempdir().expect("tempdir");
        assert_eq!(
            done_rows(&[("BGJOB_RC".to_owned(), "0".to_owned())]),
            "BGJOB_STATUS=DONE\nBGJOB_RC=0\n"
        );
        assert_eq!(
            dead_rows(&[("BGJOB_DIAG", "missing-registry")]),
            "BGJOB_STATUS=DEAD\nBGJOB_DIAG=missing-registry\n"
        );
        assert_eq!(wait_rows(270), "BGJOB_STATUS=WAIT\nELAPSED_S=270\n");
        assert!(
            (poll_sleep(1.0, Instant::now()).as_secs_f64() - MIN_POLL_SLEEP).abs() < f64::EPSILON
        );
        assert_eq!(
            poll_sleep(0.5, Instant::now() + Duration::from_secs(30)),
            Duration::from_secs_f64(0.5)
        );
        assert_eq!(
            checked_merge_env(&sandbox.path().join("merge.env")).expect("plain merge env"),
            sandbox.path().join("merge.env")
        );
        assert_eq!(
            one_line(&BgjobError::Invalid("two\nlines".to_owned())),
            "two lines"
        );
    }

    #[cfg(unix)]
    #[test]
    fn symlinked_merge_envelopes_and_log_files_are_rejected() {
        use std::os::unix::fs::symlink;

        let sandbox = tempfile::tempdir().expect("tempdir");
        let outside = tempfile::tempdir().expect("outside");
        let target = outside.path().join("merge.env");
        fs::write(&target, "OUTCOME=continue\n").expect("target");
        let link = sandbox.path().join("merge.env");
        symlink(&target, &link).expect("merge symlink");
        assert!(checked_merge_env(&link).is_err());

        let parent_link = sandbox.path().join("parent");
        symlink(outside.path(), &parent_link).expect("parent symlink");
        assert!(checked_merge_env(&parent_link.join("merge.env")).is_err());

        let log_dir = sandbox.path().join("logs");
        fs::create_dir(&log_dir).expect("log dir");
        let log_target = outside.path().join("demo-step.stdout.log");
        fs::write(&log_target, "").expect("log target");
        let log_link = log_dir.join("demo-step.stdout.log");
        symlink(&log_target, &log_link).expect("log symlink");
        assert!(open_verified_log(&log_link, &log_dir).is_err());
        assert!(open_verified_log(&log_dir.join("fresh.log"), &log_dir).is_ok());
        assert!(
            open_verified_log(&log_dir.join("fresh.log"), &PathBuf::from("/missing-root")).is_err()
        );
    }

    #[test]
    fn wait_arguments_carry_their_defaults() {
        let parsed = WaitArguments::default();
        assert_eq!(parsed.max_wait_s, BGJOB_WAIT_MAX_CHUNK_S);
        assert!((parsed.poll_interval_s - 1.0).abs() < f64::EPSILON);
    }
}
