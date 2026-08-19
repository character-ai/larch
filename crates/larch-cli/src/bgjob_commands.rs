//! Rust-owned background-job daemon start, wait, status, and reap.
//!
//! `start` validates its request, then re-executes this same binary in the
//! detached daemon role. The daemon owns the child process group, the durable
//! registry row, and the completed result envelope; `wait` is the only
//! foreground reader of that envelope.
//! Runtime budgets and wake grace use the daemon's monotonic clock. Registry
//! heartbeat and foreground wait-lease TTLs use wall-clock epochs because they
//! cross process boundaries.

use crate::argparse_compat::{split_inline_option, take_option_value, utf8_arguments};
use larch_adapters::{
    SystemProcessIdentityHost,
    bgjob_recovery::{
        BgjobRecoveryOutcome, append_teardown_diagnostic_at, open_verified_log,
        read_completed_result, read_result, recover_abandoned_entry, remove_result_residue,
    },
};
use larch_core::{
    BGJOB_RC_ORPHANED, BGJOB_RC_TIMEOUT, BGJOB_STATUS_DEAD, BGJOB_STATUS_DONE, BGJOB_STATUS_KEY,
    BGJOB_STATUS_STARTED, BGJOB_STATUS_WAIT, BGJOB_WAIT_DEFAULT_CHUNK_S,
    BGJOB_WAIT_HARD_DEADLINE_GRACE_S, BGJOB_WAIT_LEASE_TTL_S, BGJOB_WAIT_MAX_CHUNK_S, BgjobError,
    ENV_BGJOB_CAFFEINATE, JobSpec, MonitorLivenessState, OwnerIdentity, ProcessBirthIdentity,
    ProcessIdentityHost, ProcessIdentityValidationPolicy, RecordedProcessIdentity, RegistryEntry,
    ValidationResult, bgjob_dir, check_monitor_liveness, checked_dir, child_liveness,
    clear_completion_residue, collect_process_group_members_checked, confirm_process_group_absent,
    daemon_liveness, daemon_poll_interval_s, ensure_under, epoch_now,
    finish_completion_transaction, iter_entries, log_paths, log_tail, merge_rows, ordered_rows,
    orphan_diagnostic, owner_grace_s, owner_pid_candidate, phase_barrier,
    prepare_completion_transaction, private_atomic_write, read_entry, read_for,
    read_merge_result_env, read_process_identity, refresh_wait_lease, registry_path, render_rows,
    resolve_run_id, result_env_path, result_rows, startup_ack_timeout_s, startup_env_path,
    startup_in_progress, startup_rows, terminate_validated_process_group_with_policy, unlink_entry,
    validate_merge_result_env, validate_run_id, validate_slug, validate_terminal_stdout_key,
    validate_timing_overrides, wait_lease_is_fresh_at, worker_status_path, write_entry,
    write_entry_at,
};
use nix::{
    sys::signal::{Signal, killpg},
    unistd::{Pid, getpgid, setsid},
};
use std::{
    env,
    ffi::OsString,
    fs::{self, File},
    io::{BufRead as _, BufReader, Write as _},
    os::unix::process::{CommandExt as _, ExitStatusExt as _},
    path::{Path, PathBuf},
    process::{Child, ChildStdin, Command, ExitCode, Stdio},
    thread,
    time::{Duration, Instant},
};

/// Marks the re-executed process that owns the detached monitor loop.
const ENV_DAEMON_ROLE: &str = "LARCH_BGJOB_DAEMON_ROLE";
/// Carries the owner identity the launching process already captured.
const ENV_DAEMON_OWNER: &str = "LARCH_BGJOB_DAEMON_OWNER";
/// Marks the worker gated until the daemon publishes its durable registry row.
const ENV_WORKER_ROLE: &str = "LARCH_BGJOB_WORKER_ROLE";
/// Owned session directory passed only to the internal worker.
const ENV_WORKER_TMPDIR: &str = "LARCH_BGJOB_WORKER_TMPDIR";
/// Stable workflow step passed only to the internal worker.
const ENV_WORKER_STEP: &str = "LARCH_BGJOB_WORKER_STEP";
/// Session temporary directory consulted when `--tmpdir` is omitted.
const ENV_IMPLEMENT_TMPDIR: &str = "IMPLEMENT_TMPDIR";
const CAFFEINATE_PATH: &str = "/usr/bin/caffeinate";
const IDENTITY_CAPTURE_TIMEOUT: Duration = Duration::from_secs(5);
const IDENTITY_CAPTURE_SLEEP: Duration = Duration::from_millis(50);
const CHILD_REAP_TIMEOUT: Duration = Duration::from_secs(5);
const MIN_POLL_SLEEP: f64 = 0.05;
const DAEMON_CALLER: &str = "bgjob-daemon";
const REAP_CALLER: &str = "bgjob-reap";
const RECOVERY_CALLER: &str = "bgjob-recovery";
const WORKER_GATE: &str = "START\n";

struct SpawnedWorker {
    child: Child,
    gate: Option<ChildStdin>,
}

struct AcknowledgementFailure {
    reader: Option<std::thread::JoinHandle<()>>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct WorkerCommand {
    program: OsString,
    arguments: Vec<OsString>,
}

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
    terminal_stdout_key: String,
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
            max_wait_s: BGJOB_WAIT_DEFAULT_CHUNK_S,
            poll_interval_s: 1.0,
        }
    }
}

/// Launch a detached background job, or run the detached monitor loop.
#[must_use]
pub fn start(arguments: &[OsString]) -> ExitCode {
    if env::var_os(ENV_WORKER_ROLE).is_some() {
        return worker(arguments);
    }
    if requests_help(arguments) {
        return help(
            "usage: bgjob start --step STEP [--tmpdir PATH] --budget-s SECONDS [--terminal-stdout-key KEY] [options] -- COMMAND...",
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

/// Remove finished, unreadable, and recoverably abandoned registry entries.
#[must_use]
pub fn reap(arguments: &[OsString]) -> ExitCode {
    if requests_help(arguments) {
        return help("usage: bgjob reap");
    }
    let host = SystemProcessIdentityHost::new();
    let mut count = 0_u64;
    let mut failures = Vec::new();
    for (path, entry) in iter_entries() {
        let Some(entry) = entry else {
            // A malformed row may be the last durable record for work whose
            // identity cannot be decoded. Never discard it merely because
            // this consumer cannot parse it.
            failures.push("registry-invalid".to_owned());
            continue;
        };
        let daemon = daemon_liveness(&host, &entry);
        let completed =
            read_completed_result(&entry.tmpdir, &entry.result_env, &entry.step).is_some();
        if completed {
            // A current daemon unlinks its own completed row. When it has
            // already died, recovery verifies the group before either keeping
            // the terminal envelope or removing it for safe teardown.
            if daemon.live {
                continue;
            }
            match recover_abandoned_entry(
                &host,
                &path,
                &entry,
                REAP_CALLER,
                "reap-completed-result",
            ) {
                BgjobRecoveryOutcome::Recovered | BgjobRecoveryOutcome::Gone => count += 1,
                BgjobRecoveryOutcome::Failed(reason) => failures.push(recovery_diag(&reason)),
                BgjobRecoveryOutcome::Busy => {}
            }
            continue;
        }
        // A live daemon is the sole normal owner of its child and timeout
        // path. Reap recovers only after the daemon has died, which avoids
        // racing a healthy daemon's result publication and unlink.
        if daemon.live {
            continue;
        }
        match recover_abandoned_entry(&host, &path, &entry, REAP_CALLER, "reap-daemon-dead") {
            BgjobRecoveryOutcome::Recovered | BgjobRecoveryOutcome::Gone => count += 1,
            BgjobRecoveryOutcome::Failed(reason) => failures.push(recovery_diag(&reason)),
            BgjobRecoveryOutcome::Busy => {}
        }
    }
    if failures.is_empty() {
        println!("BGJOB_REAPED={count}");
        return ExitCode::SUCCESS;
    }
    print!(
        "{}",
        render_rows(&[
            ("BGJOB_REAPED".to_owned(), count.to_string()),
            (
                "BGJOB_RECOVERY_FAILED".to_owned(),
                failures.len().to_string()
            ),
            ("BGJOB_DIAG".to_owned(), failures.remove(0)),
        ])
    );
    ExitCode::from(2)
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
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    for (key, value) in extra_env {
        command.env(key, value);
    }
    // Rehydration is job input, never authority to select an internal role.
    command
        .env(ENV_DAEMON_ROLE, "1")
        .env_remove(ENV_WORKER_ROLE)
        .env_remove(ENV_WORKER_TMPDIR)
        .env_remove(ENV_WORKER_STEP);
    if let Some(owner) = spec.owner.recorded.as_ref() {
        command.env(ENV_DAEMON_OWNER, render_rows(&owner_rows(owner)));
    } else {
        command.env_remove(ENV_DAEMON_OWNER);
    }
    // The daemon inherits this process group so its own `setsid` can succeed;
    // a spawn-time process group would make it a leader and block detachment.
    let mut child = command.spawn().map_err(|error| one_line(&error))?;
    let timeout = Duration::from_secs_f64(
        startup_ack_timeout_s()
            .map_err(|error| one_line(&error))?
            .max(0.0),
    );
    let pgid = match read_acknowledgement(&mut child, timeout) {
        Ok(pgid) => pgid,
        Err(mut failure) => {
            teardown_unacknowledged_daemon(&mut child, spec, failure.reader.take());
            return Err("daemon-start-failed".to_owned());
        }
    };
    if pgid
        .parse::<i32>()
        .ok()
        .filter(|value| *value > 0)
        .is_none()
    {
        teardown_unacknowledged_daemon(&mut child, spec, None);
        return Err("daemon-start-failed".to_owned());
    }
    Ok(format!(
        "{BGJOB_STATUS_KEY}={BGJOB_STATUS_STARTED} STEP={} PGID={pgid}\n",
        spec.step
    ))
}

fn read_acknowledgement(
    child: &mut Child,
    timeout: Duration,
) -> Result<String, AcknowledgementFailure> {
    let Some(stdout) = child.stdout.take() else {
        return Err(AcknowledgementFailure { reader: None });
    };
    let (sender, receiver) = std::sync::mpsc::sync_channel(1);
    let reader = thread::spawn(move || {
        let mut line = String::new();
        let result = BufReader::new(stdout)
            .read_line(&mut line)
            .ok()
            .map(|_| line);
        let _ = sender.send(result);
    });
    let Some(line) = receiver.recv_timeout(timeout).ok().flatten() else {
        return Err(AcknowledgementFailure {
            reader: Some(reader),
        });
    };
    if reader.join().is_err() {
        return Err(AcknowledgementFailure { reader: None });
    }
    let parts: Vec<&str> = line.split_whitespace().collect();
    let [child_pid, pgid] = parts.as_slice() else {
        return Err(AcknowledgementFailure { reader: None });
    };
    if child_pid
        .parse::<i32>()
        .ok()
        .filter(|value| *value > 0)
        .is_none()
        || pgid
            .parse::<i32>()
            .ok()
            .filter(|value| *value > 0)
            .is_none()
    {
        return Err(AcknowledgementFailure { reader: None });
    }
    Ok((*pgid).to_owned())
}

fn teardown_unacknowledged_daemon(
    daemon: &mut Child,
    spec: &JobSpec,
    reader: Option<std::thread::JoinHandle<()>>,
) {
    let _ = daemon.kill();
    let _ = daemon.wait();
    if let Some(reader) = reader {
        let _ = reader.join();
    }
    let Ok(registry) = registry_path(&spec.run_id, &spec.step, None) else {
        return;
    };
    let Some(entry) = read_entry(&registry) else {
        return;
    };
    let host = SystemProcessIdentityHost::new();
    let _ = recover_abandoned_entry(
        &host,
        &registry,
        &entry,
        RECOVERY_CALLER,
        "startup-acknowledgement-failed",
    );
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
    if let Some(key) = spec.terminal_stdout_key.as_ref() {
        arguments.push("--terminal-stdout-key".into());
        arguments.push(key.clone().into());
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
        birth_identity: value("BIRTH_IDENTITY")
            .and_then(|value| ProcessBirthIdentity::parse_wire_value(&value)),
        command_signature: value("COMMAND")?,
        expected_signature: value("EXPECTED").unwrap_or_default(),
    })
}

fn owner_rows(owner: &RecordedProcessIdentity) -> Vec<(String, String)> {
    vec![
        ("PID".to_owned(), owner.pid.to_string()),
        ("PGID".to_owned(), owner.pgid.to_string()),
        ("START_TIME".to_owned(), owner.start_time.clone()),
        (
            "BIRTH_IDENTITY".to_owned(),
            owner
                .birth_identity
                .as_ref()
                .map_or_else(String::new, ProcessBirthIdentity::wire_value),
        ),
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
        raw => Some(validate_merge_result_env(Path::new(raw), &tmpdir)?),
    };
    let terminal_stdout_key = match parsed.terminal_stdout_key.as_str() {
        "" => None,
        raw => Some(validate_terminal_stdout_key(raw)?),
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
        terminal_stdout_key,
        initial_merge_rows: Vec::new(),
    })
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

fn one_line(error: &(impl ToString + ?Sized)) -> String {
    error.to_string().replace(['\n', '\r'], " ")
}

fn wall_epoch(wall_time_s: f64) -> Result<i64, String> {
    let duration =
        Duration::try_from_secs_f64(wall_time_s).map_err(|_| "invalid-wall-clock".to_owned())?;
    i64::try_from(duration.as_secs()).map_err(|_| "invalid-wall-clock".to_owned())
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
            "--terminal-stdout-key" => {
                parsed.terminal_stdout_key =
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
                let value = raw.parse::<i64>().map_err(|_| "invalid-max-wait")?;
                if !(0..=BGJOB_WAIT_MAX_CHUNK_S).contains(&value) {
                    return Err("invalid-max-wait");
                }
                parsed.max_wait_s = value;
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
    // Capture the persistent worker leader before releasing its private gate.
    let host = SystemProcessIdentityHost::new();
    fs::create_dir_all(&spec.log_dir).map_err(|error| one_line(&error))?;
    let root = bgjob_dir(&spec.tmpdir).map_err(|error| one_line(&error))?;
    fs::create_dir_all(&root).map_err(|error| one_line(&error))?;
    clear_completion_residue(&spec.tmpdir, &spec.step).map_err(|error| one_line(&error))?;
    let worker_status =
        worker_status_path(&spec.tmpdir, &spec.step).map_err(|error| one_line(&error))?;
    let _ = remove_result_residue(&worker_status);
    let stdout_log = spec.log_dir.join(format!("{}.stdout.log", spec.step));
    let stderr_log = spec.log_dir.join(format!("{}.stderr.log", spec.step));
    let stdout_handle =
        open_verified_log(&stdout_log, &spec.log_dir).map_err(|error| one_line(&error))?;
    let stderr_handle =
        open_verified_log(&stderr_log, &spec.log_dir).map_err(|error| one_line(&error))?;
    let mut worker =
        spawn_job(spec, stdout_handle, stderr_handle).map_err(|error| one_line(&error))?;
    if let Err(error) = phase_barrier("after-child-spawn") {
        // The gate has not opened, so this direct child handle is still the
        // only process that can own the group. Reap it before reporting the
        // interrupted pre-registry phase.
        kill_and_reap(&host, &mut worker.child, None);
        return Err(one_line(&error));
    }
    let (child_identity, mut entry, registry) =
        match register_startup(&host, spec, &mut worker.child, &stdout_log, &stderr_log) {
            Ok(startup) => startup,
            Err(error) => {
                // Before a row exists the gate prevents the worker from starting
                // the requested command. Reap the worker's dedicated group before
                // reporting a failed launch.
                kill_and_reap(&host, &mut worker.child, None);
                return Err(error);
            }
        };
    // Later failures leave this durable row claimable by a waiter or reaper.
    phase_barrier("after-registry-publication").map_err(|error| one_line(&error))?;
    let startup = match write_startup_marker(spec, &child_identity, &registry) {
        Ok(startup) => startup,
        Err(error) => {
            return teardown_registered_startup(
                &host,
                spec,
                &mut worker.child,
                &child_identity,
                &registry,
                None,
                &one_line(&error),
            );
        }
    };
    phase_barrier("after-startup-marker").map_err(|error| one_line(&error))?;
    if let Err(error) = release_worker(&mut worker) {
        return teardown_registered_startup(
            &host,
            spec,
            &mut worker.child,
            &child_identity,
            &registry,
            Some(&startup),
            &error,
        );
    }
    if let Err(error) = acknowledge_start(&worker.child) {
        return teardown_registered_startup(
            &host,
            spec,
            &mut worker.child,
            &child_identity,
            &registry,
            Some(&startup),
            &error,
        );
    }
    phase_barrier("after-acknowledgement").map_err(|error| one_line(&error))?;
    let _ = fs::remove_file(&startup);
    match monitor(
        spec,
        &mut worker.child,
        &child_identity,
        &mut entry,
        &registry,
        &host,
    ) {
        Ok(()) => Ok(()),
        Err(message) => {
            // Registration succeeded before the gate opened. A later error
            // leaves its complete durable row for the shared recovery owner.
            Err(message)
        }
    }
}

fn register_startup(
    host: &SystemProcessIdentityHost,
    spec: &JobSpec,
    child: &mut Child,
    stdout_log: &Path,
    stderr_log: &Path,
) -> Result<(RecordedProcessIdentity, RegistryEntry, PathBuf), String> {
    let child_pid = i32::try_from(child.id()).map_err(|error| one_line(&error))?;
    let Some(child_identity) = capture_identity(host, child_pid, "") else {
        return Err(format!(
            "could not capture process identity for pid {child_pid}"
        ));
    };
    let daemon_pid = i32::try_from(std::process::id()).map_err(|error| one_line(&error))?;
    let Some(daemon_identity) = capture_identity(host, daemon_pid, "") else {
        kill_and_reap(host, child, Some(&child_identity));
        return Err("could not capture daemon process identity".to_owned());
    };
    phase_barrier("after-identity-capture").map_err(|error| one_line(&error))?;
    let start_epoch = wall_epoch(host.wall_time_secs())?;
    let entry = RegistryEntry {
        step: spec.step.clone(),
        run_id: spec.run_id.clone(),
        tmpdir: spec.tmpdir.clone(),
        log_dir: spec.log_dir.clone(),
        clone_path: env::current_dir().map_err(|error| one_line(&error))?,
        daemon: daemon_identity,
        child: child_identity.clone(),
        // The worker itself never execs: it remains the durable group leader
        // while the requested command and all group descendants run.
        child_allows_exec: false,
        owner: spec.owner.recorded.clone(),
        start_epoch,
        heartbeat_epoch: start_epoch,
        budget_s: spec.budget_s,
        stdout_log: stdout_log.to_path_buf(),
        stderr_log: stderr_log.to_path_buf(),
        result_env: result_env_path(&spec.tmpdir, &spec.step).map_err(|error| one_line(&error))?,
        recovery_inputs_recorded: true,
        merge_result_env: spec.merge_result_env.clone(),
        terminal_stdout_key: spec.terminal_stdout_key.clone(),
        sentinel_paths: spec.sentinel_paths.clone(),
    };
    let registry = match write_entry(&entry) {
        Ok(path) => path,
        Err(failure) => {
            kill_and_reap(host, child, Some(&child_identity));
            return Err(one_line(&failure));
        }
    };
    Ok((child_identity, entry, registry))
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
            let validation = terminate_validated_process_group_with_policy(
                host,
                identity,
                ProcessIdentityValidationPolicy::ExactCommand,
                None,
                DAEMON_CALLER,
                "startup-failed",
            );
            if !validation.ok {
                kill_direct_child_group(child);
            }
        }
        None => kill_direct_child_group(child),
    }
    reap_child(child, CHILD_REAP_TIMEOUT);
}

/// Kill the dedicated process group of a child we still own directly.
///
/// This is limited to startup failures before a durable identity can be
/// recorded. `spawn_job` creates this group with the child's own PID, and the
/// unreaped `Child` handle prevents PID reuse while the direct cleanup runs.
fn kill_direct_child_group(child: &mut Child) {
    let Ok(child_pid) = i32::try_from(child.id()) else {
        let _ = child.kill();
        return;
    };
    let group = getpgid(Some(Pid::from_raw(child_pid)))
        .ok()
        .map(Pid::as_raw)
        .filter(|pgid| *pgid == child_pid);
    if let Some(group) = group {
        let group = Pid::from_raw(group);
        let _ = killpg(group, Signal::SIGTERM);
        thread::sleep(IDENTITY_CAPTURE_SLEEP);
        let _ = killpg(group, Signal::SIGKILL);
    } else {
        let _ = child.kill();
    }
}

fn spawn_job(spec: &JobSpec, stdout: File, stderr: File) -> std::io::Result<SpawnedWorker> {
    let executable = env::current_exe()?;
    let mut command = Command::new(executable); // lint-subprocess-via-runner: ok the detached worker intentionally owns the long-running job process group
    command
        .args(["bgjob", "start"])
        .args(&spec.command)
        .stdin(Stdio::piped())
        .stdout(Stdio::from(stdout))
        .stderr(Stdio::from(stderr))
        .env_remove(ENV_DAEMON_ROLE)
        .env_remove(ENV_DAEMON_OWNER)
        .env(ENV_WORKER_ROLE, "1")
        .env(ENV_WORKER_TMPDIR, &spec.tmpdir)
        .env(ENV_WORKER_STEP, &spec.step);
    command.process_group(0);
    let mut child = command.spawn()?;
    let gate = child
        .stdin
        .take()
        .ok_or_else(|| std::io::Error::other("worker gate unavailable"))?;
    Ok(SpawnedWorker {
        child,
        gate: Some(gate),
    })
}

fn release_worker(worker: &mut SpawnedWorker) -> Result<(), String> {
    let Some(mut gate) = worker.gate.take() else {
        return Err("worker-gate-unavailable".to_owned());
    };
    gate.write_all(WORKER_GATE.as_bytes())
        .and_then(|()| gate.flush())
        .map_err(|error| one_line(&error))
}

fn acknowledge_start(child: &Child) -> Result<(), String> {
    let child_pid = i32::try_from(child.id()).map_err(|error| one_line(&error))?;
    let pgid = getpgid(Some(Pid::from_raw(child_pid))).map_err(|error| one_line(&error))?;
    phase_barrier("before-acknowledgement").map_err(|error| one_line(&error))?;
    let mut stdout = std::io::stdout();
    stdout
        .write_all(format!("{child_pid} {pgid}\n").as_bytes())
        .and_then(|()| stdout.flush())
        .map_err(|error| one_line(&error))?;
    Ok(())
}

fn write_startup_marker(
    spec: &JobSpec,
    child: &RecordedProcessIdentity,
    registry: &Path,
) -> Result<PathBuf, BgjobError> {
    let startup = startup_env_path(&spec.tmpdir, &spec.step)?;
    let root = bgjob_dir(&spec.tmpdir)?;
    let mut rows = startup_rows(&spec.step, epoch_now());
    rows.extend([
        ("RUN_ID".to_owned(), spec.run_id.clone()),
        ("STARTUP_PHASE".to_owned(), "registry-published".to_owned()),
        ("CHILD_PID".to_owned(), child.pid.to_string()),
        ("CHILD_PGID".to_owned(), child.pgid.to_string()),
        ("CHILD_START_TIME".to_owned(), child.start_time.clone()),
        (
            "CHILD_BIRTH_IDENTITY".to_owned(),
            child
                .birth_identity
                .as_ref()
                .map_or_else(String::new, larch_core::ProcessBirthIdentity::wire_value),
        ),
        ("REGISTRY".to_owned(), registry.display().to_string()),
    ]);
    private_atomic_write(&startup, &render_rows(&rows), &root)?;
    Ok(startup)
}

fn teardown_registered_startup(
    host: &SystemProcessIdentityHost,
    spec: &JobSpec,
    child: &mut Child,
    child_identity: &RecordedProcessIdentity,
    registry: &Path,
    startup: Option<&Path>,
    reason: &str,
) -> Result<(), String> {
    let teardown = terminate_and_confirm_child(
        host,
        child,
        child_identity,
        ProcessIdentityValidationPolicy::ExactCommand,
        &TeardownRequest {
            log_dir: &spec.log_dir,
            step: &spec.step,
            reason: "startup-failed",
            caller: DAEMON_CALLER,
        },
    );
    match teardown {
        Ok(()) => {
            unlink_entry(registry);
            if let Some(startup) = startup {
                let _ = fs::remove_file(startup);
            }
            Err(reason.to_owned())
        }
        Err(teardown_reason) => {
            append_teardown_diagnostic(spec, "startup-failed", &teardown_reason);
            Err(reason.to_owned())
        }
    }
}

fn worker(arguments: &[OsString]) -> ExitCode {
    worker_body(arguments).map_or_else(
        |_| ExitCode::from(2),
        |rc| {
            rc.parse::<u8>()
                .map_or_else(|_| ExitCode::from(2), ExitCode::from)
        },
    )
}

fn worker_body(arguments: &[OsString]) -> Result<String, String> {
    let command = utf8_arguments(arguments, "invalid-worker-command").map_err(ToOwned::to_owned)?;
    let (program, arguments) = command
        .split_first()
        .ok_or_else(|| "missing-worker-command".to_owned())?;
    let tmpdir = PathBuf::from(env::var(ENV_WORKER_TMPDIR).map_err(|_| "missing-worker-tmpdir")?);
    let step = env::var(ENV_WORKER_STEP).map_err(|_| "missing-worker-step")?;
    let status_path = worker_status_path(&tmpdir, &step).map_err(|error| one_line(&error))?;
    let root = bgjob_dir(&tmpdir).map_err(|error| one_line(&error))?;

    // The daemon holds the write end until it has captured this persistent
    // leader and atomically published the registry row. An EOF means the
    // daemon died before that point, so the worker exits without launching
    // application work.
    let mut gate = String::new();
    BufReader::new(std::io::stdin())
        .read_line(&mut gate)
        .map_err(|error| one_line(&error))?;
    if gate != WORKER_GATE {
        return Err("worker-gate-not-released".to_owned());
    }

    let launch = worker_command(program, arguments);
    let mut requested = Command::new(&launch.program); // lint-subprocess-via-runner: ok the durable worker owns the requested long-running child
    requested
        .args(&launch.arguments)
        .stdin(Stdio::null())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .env_remove(ENV_DAEMON_ROLE)
        .env_remove(ENV_DAEMON_OWNER)
        .env_remove(ENV_WORKER_ROLE)
        .env_remove(ENV_WORKER_TMPDIR)
        .env_remove(ENV_WORKER_STEP);
    let exit_status = if let Ok(mut child) = requested.spawn() {
        child.wait().map_err(|error| one_line(&error))?
    } else {
        write_worker_status(&status_path, &root, &step, "2")?;
        return Ok("2".to_owned());
    };
    let rc = exit_token(exit_status);
    wait_for_worker_group()?;
    write_worker_status(&status_path, &root, &step, &rc)?;
    Ok(rc)
}

fn worker_command(program: &str, arguments: &[String]) -> WorkerCommand {
    worker_command_for(
        program,
        arguments,
        cfg!(target_os = "macos"),
        env::var(ENV_BGJOB_CAFFEINATE).as_deref() == Ok("true"),
        Path::new(CAFFEINATE_PATH).is_file(),
    )
}

fn worker_command_for(
    program: &str,
    arguments: &[String],
    darwin: bool,
    caffeinate_enabled: bool,
    caffeinate_available: bool,
) -> WorkerCommand {
    if darwin && caffeinate_enabled && caffeinate_available {
        let mut wrapped_arguments = Vec::with_capacity(arguments.len().saturating_add(2));
        wrapped_arguments.extend([OsString::from("-i"), OsString::from(program)]);
        wrapped_arguments.extend(arguments.iter().map(OsString::from));
        return WorkerCommand {
            program: OsString::from(CAFFEINATE_PATH),
            arguments: wrapped_arguments,
        };
    }
    WorkerCommand {
        program: OsString::from(program),
        arguments: arguments.iter().map(OsString::from).collect(),
    }
}

fn write_worker_status(path: &Path, root: &Path, step: &str, rc: &str) -> Result<(), String> {
    let rows = [
        ("WORKER_RC".to_owned(), rc.to_owned()),
        ("STEP".to_owned(), step.to_owned()),
    ];
    private_atomic_write(path, &render_rows(&rows), root).map_err(|error| one_line(&error))
}

fn wait_for_worker_group() -> Result<(), String> {
    let pid = i32::try_from(std::process::id()).map_err(|error| one_line(&error))?;
    let group_id = getpgid(Some(Pid::from_raw(pid)))
        .map_err(|error| one_line(&error))?
        .as_raw();
    let host = SystemProcessIdentityHost::new();
    loop {
        if let Some(members) = collect_process_group_members_checked(&host, group_id)
            && members.iter().all(|member| *member == pid)
            && host.get_pgid(pid) == Some(group_id)
        {
            return Ok(());
        }
        // A failed probe is not evidence that descendants are gone. Staying
        // alive leaves the recorded group leader available to the daemon's
        // bounded budget/orphan teardown path.
        thread::sleep(IDENTITY_CAPTURE_SLEEP);
    }
}

fn worker_result_token(spec: &JobSpec, status: std::process::ExitStatus) -> String {
    let Ok(path) = worker_status_path(&spec.tmpdir, &spec.step) else {
        return exit_token(status);
    };
    let Some(rows) = read_result(&path) else {
        return exit_token(status);
    };
    let value = |key: &str| {
        rows.iter()
            .find(|(candidate, _)| candidate == key)
            .map(|(_, value)| value.as_str())
    };
    match (value("WORKER_RC"), value("STEP")) {
        (Some(rc), Some(step)) if !rc.is_empty() && step == spec.step => rc.to_owned(),
        _ => exit_token(status),
    }
}

fn monitor(
    spec: &JobSpec,
    child: &mut Child,
    child_identity: &RecordedProcessIdentity,
    entry: &mut RegistryEntry,
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
    let mut monitor_state = MonitorLivenessState::new(host);
    let (terminal, elapsed) = loop {
        let step =
            check_monitor_liveness(host, spec.owner.recorded.as_ref(), monitor_state, grace_s);
        monitor_state = step.state;
        let elapsed = step.elapsed;
        refresh_registry_heartbeat(entry, registry, step.wall_time_s)?;
        // Test-only phase barriers can stop the daemon after its worker
        // becomes a zombie but before this direct parent reaps it. That is
        // the real missing-pid recovery window `wait` must handle without a
        // process panic or a silent terminal-envelope loss.
        phase_barrier("before-worker-reap").map_err(|error| one_line(&error))?;
        match child.try_wait() {
            Ok(Some(status)) => {
                phase_barrier("after-leader-exit").map_err(|error| one_line(&error))?;
                break (
                    MonitorTerminal::Exited(worker_result_token(spec, status)),
                    elapsed,
                );
            }
            Ok(None) => {}
            Err(error) => break (MonitorTerminal::WaitError(one_line(&error)), elapsed),
        }
        if elapsed >= budget {
            break (MonitorTerminal::Teardown(BGJOB_RC_TIMEOUT), elapsed);
        }
        if let (true, Some(validation)) = (step.orphaned, step.validation.as_ref()) {
            // An active foreground wait refreshes a lease under the session
            // tmpdir. Keep the child alive while that lease is fresh so an
            // ephemeral start-shell owner (#8639) cannot orphan a still-waited
            // job. When wait stops, the lease ages out and orphaning resumes.
            if wait_lease_is_fresh_at(
                &spec.tmpdir,
                &spec.step,
                BGJOB_WAIT_LEASE_TTL_S,
                step.wall_time_s,
            ) {
                host.sleep(poll);
                continue;
            }
            append_orphan_diagnostic(spec, validation, step.owner_failure_count);
            break (MonitorTerminal::Teardown(BGJOB_RC_ORPHANED), elapsed);
        }
        host.sleep(poll);
    };
    let (rc_token, teardown_reason) = match terminal {
        MonitorTerminal::Exited(rc) => (rc, "child-exited"),
        MonitorTerminal::Teardown(reason) => (reason.to_owned(), reason),
        MonitorTerminal::WaitError(reason) => {
            append_teardown_diagnostic(spec, "child-wait-error", &reason);
            ("2".to_owned(), "child-wait-error")
        }
    };
    let elapsed_s = i64::try_from(elapsed.as_secs()).unwrap_or(i64::MAX);
    if let Err(reason) = terminate_and_confirm_child(
        host,
        child,
        child_identity,
        ProcessIdentityValidationPolicy::ExactCommand,
        &TeardownRequest {
            log_dir: &spec.log_dir,
            step: &spec.step,
            reason: teardown_reason,
            caller: DAEMON_CALLER,
        },
    ) {
        append_teardown_diagnostic(spec, teardown_reason, &reason);
        // Retain the registry and omit a terminal result: daemon-death
        // recovery can retry from the durable identity instead of claiming a
        // timed-out/orphaned group is gone when it is not.
        return Ok(());
    }
    write_result(spec, &rc_token, elapsed_s)?;
    if let Ok(path) = worker_status_path(&spec.tmpdir, &spec.step) {
        let _ = remove_result_residue(&path);
    }
    unlink_entry(registry);
    Ok(())
}

fn refresh_registry_heartbeat(
    entry: &mut RegistryEntry,
    registry: &Path,
    wall_time_s: f64,
) -> Result<(), String> {
    entry.heartbeat_epoch = wall_epoch(wall_time_s)?;
    let root = registry
        .parent()
        .ok_or_else(|| "registry-path-has-no-parent".to_owned())?;
    let written = write_entry_at(entry, Some(root)).map_err(|error| one_line(&error))?;
    if written != registry {
        return Err("registry-heartbeat-path-mismatch".to_owned());
    }
    Ok(())
}

enum MonitorTerminal {
    Exited(String),
    Teardown(&'static str),
    WaitError(String),
}

struct TeardownRequest<'a> {
    log_dir: &'a Path,
    step: &'a str,
    reason: &'a str,
    caller: &'a str,
}

fn terminate_and_confirm_child(
    host: &SystemProcessIdentityHost,
    child: &mut Child,
    child_identity: &RecordedProcessIdentity,
    policy: ProcessIdentityValidationPolicy,
    request: &TeardownRequest<'_>,
) -> Result<(), String> {
    let kill_log = request
        .log_dir
        .join(format!("{}.kill.log.jsonl", request.step));
    let validation = terminate_validated_process_group_with_policy(
        host,
        child_identity,
        policy,
        Some(&kill_log),
        request.caller,
        request.reason,
    );
    if !validation.ok && validation.reason != "missing-pid" {
        return Err(validation.reason);
    }
    // Reap the direct worker before proving the group absent; Linux otherwise
    // retains its zombie in the numeric group.
    reap_child(child, CHILD_REAP_TIMEOUT);
    let confirmation = confirm_process_group_absent(host, child_identity, policy);
    if confirmation.terminated {
        Ok(())
    } else {
        Err(confirmation.reason)
    }
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
    let merged = spec
        .merge_result_env
        .as_deref()
        .map(|path| read_merge_text(path, &spec.tmpdir))
        .transpose()?
        .map_or_else(Vec::new, |text| merge_rows(&text));
    let rows = result_rows(&spec.step, rc, elapsed_s, &merged).map_err(|error| one_line(&error))?;
    let transaction = prepare_completion_transaction(
        &spec.tmpdir,
        &spec.step,
        &spec.sentinel_paths,
        &render_rows(&rows),
    )
    .map_err(|error| one_line(&error))?;
    finish_completion_transaction(&transaction).map_err(|error| one_line(&error))
}

fn read_merge_text(path: &Path, tmpdir: &Path) -> Result<String, String> {
    read_merge_result_env(path, tmpdir).map_err(|error| one_line(&error))
}

fn append_orphan_diagnostic(spec: &JobSpec, validation: &ValidationResult, failure_count: u32) {
    let stderr_log = spec.log_dir.join(format!("{}.stderr.log", spec.step));
    let _ = fs::create_dir_all(&spec.log_dir);
    let text = orphan_diagnostic(spec.owner.recorded.as_ref(), validation, failure_count);
    if let Ok(mut handle) = open_verified_log(&stderr_log, &spec.log_dir) {
        let _ = handle.write_all(text.as_bytes());
    }
}

fn append_teardown_diagnostic(spec: &JobSpec, context: &str, reason: &str) {
    append_teardown_diagnostic_at(&spec.log_dir, &spec.step, context, reason);
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
        // Refresh before every poll so an ephemeral start-time owner cannot
        // orphan a job the orchestrator is still waiting on (#8639).
        refresh_wait_lease(&tmpdir, &step).map_err(|error| one_line(&error))?;
        if let Some(rows) = read_completed_result(&tmpdir, &result_path, &step) {
            return Ok(done_rows(&rows));
        }
        let (registry, entry) =
            read_for(&tmpdir, &step, run_id.as_deref()).map_err(|error| one_line(&error))?;
        let Some(entry) = entry else {
            // `None` means the daemon published its registry row while the
            // startup marker was being watched, so re-read it next iteration.
            // The sleep keeps that re-read a poll rather than a hot spin.
            if let Some(output) =
                missing_registry(&tmpdir, &result_path, &registry, parsed, &step, deadline)
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
            if let Some(rows) = read_completed_result(&tmpdir, &result_path, &step) {
                return Ok(done_rows(&rows));
            }
            match recover_abandoned_entry(
                &host,
                &registry,
                &entry,
                RECOVERY_CALLER,
                "daemon-dead-wait",
            ) {
                BgjobRecoveryOutcome::Recovered => {
                    let tail = stderr_tail(&entry);
                    return Ok(dead_rows(&[
                        ("BGJOB_DIAG", "daemon-dead-recovered"),
                        ("STDERR_TAIL", tail.as_str()),
                    ]));
                }
                BgjobRecoveryOutcome::Failed(reason) => {
                    let tail = stderr_tail(&entry);
                    return Ok(retryable_recovery_rows(
                        parsed.max_wait_s,
                        &recovery_diag(&reason),
                        &tail,
                    ));
                }
                BgjobRecoveryOutcome::Busy | BgjobRecoveryOutcome::Gone => {
                    // Another cleaner may have finished or a normal result
                    // may have appeared. Re-enter through the result read
                    // rather than publishing a terminal state while recovery
                    // remains unresolved.
                    thread::sleep(poll_sleep(parsed.poll_interval_s, deadline));
                    continue;
                }
            }
        }
        if Instant::now() >= deadline {
            return Ok(wait_rows(parsed.max_wait_s));
        }
        thread::sleep(poll_sleep(parsed.poll_interval_s, deadline));
    }
}

fn missing_registry(
    tmpdir: &Path,
    result_path: &Path,
    registry: &Path,
    parsed: &WaitArguments,
    step: &str,
    deadline: Instant,
) -> Option<String> {
    if let Some(rows) = read_completed_result(tmpdir, result_path, step) {
        return Some(done_rows(&rows));
    }
    while startup_marker_live(tmpdir, step) {
        if Instant::now() >= deadline {
            return Some(wait_rows(parsed.max_wait_s));
        }
        thread::sleep(poll_sleep(parsed.poll_interval_s, deadline));
    }
    // The daemon drops its startup marker only after a durable successor
    // exists, so re-read both before reporting an unrecoverable daemon.
    if let Some(rows) = read_completed_result(tmpdir, result_path, step) {
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

/// Report a recovery that still owns a durable row without falsely making it
/// terminal. Callers repeat their ordinary wait; a later recovery claimant can
/// either prove the process group absent or publish the normal result.
fn retryable_recovery_rows(max_wait_s: i64, reason: &str, tail: &str) -> String {
    render_rows(&[
        (BGJOB_STATUS_KEY.to_owned(), BGJOB_STATUS_WAIT.to_owned()),
        ("ELAPSED_S".to_owned(), max_wait_s.to_string()),
        ("BGJOB_RECOVERY".to_owned(), "retryable".to_owned()),
        ("BGJOB_DIAG".to_owned(), reason.to_owned()),
        ("STDERR_TAIL".to_owned(), tail.to_owned()),
    ])
}

fn recovery_diag(reason: &str) -> String {
    larch_core::redact_outbound(&one_line(reason))
}

#[cfg(test)]
mod tests {
    use super::{
        CAFFEINATE_PATH, MIN_POLL_SLEEP, StartArguments, WaitArguments, daemon_arguments,
        dead_rows, done_rows, finish_start, inherited_owner, one_line, open_verified_log,
        owner_from_rows, owner_rows, parse_start, parse_wait, poll_sleep, read_completed_result,
        read_merge_text, read_result, remove_result_residue, wait_rows, wall_epoch,
        worker_command_for, write_result,
    };
    use larch_core::{
        BGJOB_ELAPSED_KEY, BGJOB_RC_KEY, BGJOB_WAIT_DEFAULT_CHUNK_S, BGJOB_WAIT_MAX_CHUNK_S,
        BgjobError, JobSpec, OwnerIdentity, ProcessBirthIdentity, RecordedProcessIdentity,
        ordered_rows, render_rows, validate_merge_result_env,
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
            birth_identity: Some(ProcessBirthIdentity::Darwin {
                seconds: 1,
                microseconds: 4321,
            }),
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
            terminal_stdout_key: None,
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
            "--terminal-stdout-key",
            "NEXT_ACTION",
            "--",
            "/bin/echo",
            "--flagged",
        ]))
        .expect("parsed start arguments");
        assert_eq!(parsed.step, "demo-step");
        assert_eq!(parsed.tmpdir, "/tmp/session");
        assert_eq!(parsed.budget_s, Some(30));
        assert_eq!(parsed.sentinels, ["/tmp/session/done"]);
        assert_eq!(parsed.terminal_stdout_key, "NEXT_ACTION");
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
    fn wait_arguments_default_to_the_default_chunk_and_require_a_step() {
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
        assert_eq!(parsed.max_wait_s, BGJOB_WAIT_DEFAULT_CHUNK_S);
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
        let long = parse_wait(&arguments(&[
            "--step",
            "leaf",
            "--tmpdir",
            "/tmp/session",
            "--max-wait-s",
            "7200",
        ]))
        .expect("long leaf wait");
        assert_eq!(long.max_wait_s, BGJOB_WAIT_MAX_CHUNK_S);
        assert_eq!(
            parse_wait(&arguments(&[
                "--step",
                "leaf",
                "--tmpdir",
                "/tmp/session",
                "--max-wait-s",
                "7201"
            ]))
            .expect_err("above max"),
            "invalid-max-wait"
        );
    }

    #[test]
    fn owner_identity_round_trips_through_the_daemon_environment() {
        let rows = render_rows(&owner_rows(&owner()));
        assert!(rows.contains("BIRTH_IDENTITY=darwin:1:4321\n"));
        assert_eq!(owner_from_rows(&rows), Some(owner()));
        assert!(
            owner_from_rows(&rows.replace("BIRTH_IDENTITY=darwin:1:4321\n", ""))
                .expect("legacy owner")
                .birth_identity
                .is_none()
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
        job.terminal_stdout_key = Some("NEXT_ACTION".to_owned());
        let rendered: Vec<String> = daemon_arguments(&job)
            .into_iter()
            .map(|value| value.to_string_lossy().into_owned())
            .collect();
        assert_eq!(&rendered[..4], ["bgjob", "start", "--step", "demo-step"]);
        assert!(rendered.contains(&"--sentinel".to_owned()));
        assert!(rendered.contains(&"--merge-result-env".to_owned()));
        assert!(rendered.contains(&"--terminal-stdout-key".to_owned()));
        let separator = rendered
            .iter()
            .position(|value| value == "--")
            .expect("command separator");
        assert_eq!(&rendered[separator + 1..], ["/bin/echo", "hello"]);
        assert!(!daemon_arguments(&job).contains(&OsString::from("--owner-pid")));
    }

    #[test]
    fn caffeinate_wrap_is_darwin_only_opt_in_and_availability_gated() {
        let arguments = ["hello".to_owned()];
        for (darwin, enabled, available) in [
            (false, true, true),
            (true, false, true),
            (true, true, false),
        ] {
            let command = worker_command_for("/bin/echo", &arguments, darwin, enabled, available);
            assert_eq!(command.program, OsString::from("/bin/echo"));
            assert_eq!(command.arguments, [OsString::from("hello")]);
        }

        let wrapped = worker_command_for("/bin/echo", &arguments, true, true, true);
        assert_eq!(wrapped.program, OsString::from(CAFFEINATE_PATH));
        assert_eq!(
            wrapped.arguments,
            [
                OsString::from("-i"),
                OsString::from("/bin/echo"),
                OsString::from("hello"),
            ]
        );
        assert_eq!(wall_epoch(42.9), Ok(42));
        assert!(wall_epoch(f64::NAN).is_err());
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
        assert!(read_completed_result(sandbox.path(), &result, "demo-step").is_some());
        assert_eq!(read_result(&sandbox.path().join("bgjob/absent.env")), None);
        fs::write(&result, "BGJOB_RC=0\n").expect("partial result");
        assert!(
            read_completed_result(sandbox.path(), &result, "demo-step").is_none(),
            "a partial result must not claim a terminal completion"
        );
        remove_result_residue(&result).expect("remove partial result");
        assert!(!result.exists());

        fs::write(&merge, "CUSTOM=carriage\r\n").expect("cr merge env");
        assert_eq!(read_merge_text(&merge, sandbox.path()), Ok(String::new()));
        assert_eq!(
            read_merge_text(&sandbox.path().join("absent.env"), sandbox.path()),
            Ok(String::new())
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
            validate_merge_result_env(&sandbox.path().join("merge.env"), sandbox.path())
                .expect("plain merge env"),
            sandbox
                .path()
                .canonicalize()
                .expect("canonical sandbox")
                .join("merge.env")
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
        assert!(validate_merge_result_env(&link, sandbox.path()).is_err());

        let parent_link = sandbox.path().join("parent");
        symlink(outside.path(), &parent_link).expect("parent symlink");
        assert!(validate_merge_result_env(&parent_link.join("merge.env"), sandbox.path()).is_err());

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
        assert_eq!(parsed.max_wait_s, BGJOB_WAIT_DEFAULT_CHUNK_S);
        assert!((parsed.poll_interval_s - 1.0).abs() < f64::EPSILON);
    }
}
