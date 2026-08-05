//! Validated process-identity capture and termination.
//!
//! A persisted PID or process-group ID is signaled only after the live process
//! still matches the recorded start time, pgid, and command signature. PID
//! reuse must never cause a signal (#6213).

use crate::redact;
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::{
    collections::BTreeSet,
    path::{Path, PathBuf},
    time::Duration,
};

/// Field count for `ps -o lstart=` (weekday month day time year).
pub const PS_LSTART_FIELD_COUNT: usize = 5;
/// Maximum command text retained in kill logs.
pub const COMMAND_LOG_LIMIT: usize = 500;
/// Retries when capturing a stable process-group leader identity.
pub const PROCESS_IDENTITY_CAPTURE_ATTEMPTS: u32 = 10;
/// Sleep between identity capture retries.
pub const PROCESS_IDENTITY_CAPTURE_SLEEP: Duration = Duration::from_millis(50);
/// Grace after a missing PID before treating a design Step 3 loop as failed.
pub const DESIGN_STEP3_MISSING_PID_GRACE: Duration = Duration::from_secs(5);
/// Timeout for identity `ps` probes.
pub const PROCESS_IDENTITY_PS_TIMEOUT: Duration = Duration::from_secs(5);
/// Delay between SIGTERM and SIGKILL escalation.
pub const TERMINATE_ESCALATION_SLEEP: Duration = Duration::from_secs(2);

/// Design Step 3 loop identity sidecar basename.
pub const DESIGN_STEP3_LOOP_IDENTITY_FILE: &str = ".step3-loop-identity.json";
/// Design Step 3 detached-wrapper marker basename.
pub const DESIGN_STEP3_WRAPPER_DETACHED_FILE: &str = ".step3-wrapper-detached";
/// Design Step 3 kill-log basename.
pub const DESIGN_STEP3_KILL_LOG_FILE: &str = "design-step3-kill.log.jsonl";
/// Implement Step 5 loop identity sidecar basename.
pub const IMPLEMENT_STEP5_LOOP_IDENTITY_FILE: &str = ".step5-loop-identity.json";
/// Implement Step 5 detached-wrapper marker basename.
pub const IMPLEMENT_STEP5_WRAPPER_DETACHED_FILE: &str = ".step5-wrapper-detached";
/// Implement Step 5 kill-log basename.
pub const IMPLEMENT_STEP5_KILL_LOG_FILE: &str = "implement-step5-kill.log.jsonl";
/// Finalize tmpdir-scoped kill-log basename.
pub const FINALIZE_KILL_LOG_FILE: &str = "finalize-kill.log.jsonl";

/// Persisted identity of a process that may later be signaled.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RecordedProcessIdentity {
    pub pid: i32,
    pub pgid: i32,
    pub start_time: String,
    pub command_signature: String,
    #[serde(default)]
    pub expected_signature: String,
}

/// Outcome of comparing a recorded identity against the live process.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ValidationResult {
    pub ok: bool,
    pub reason: String,
    pub current: Option<RecordedProcessIdentity>,
}

/// Result of one identity probe attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProcessIdentityProbeResult {
    pub identity: Option<RecordedProcessIdentity>,
    pub failure_reason: String,
}

/// Snapshot of a validated kill target immediately before signaling.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct KillTargetSnapshot {
    pub pid: i32,
    pub pgid: i32,
    pub descendants: Vec<i32>,
    pub command: String,
}

/// One kill-log JSONL event.
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct KillLogEvent {
    pub event: String,
    pub signal: String,
    pub pid: i32,
    pub pgid: i32,
    pub command: String,
    pub caller: String,
    pub reason: String,
    pub descendants: Vec<i32>,
    pub tmpdir_needle: String,
    pub physical_needle: String,
}

/// Termination signal used by validated process-group cleanup.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TerminateSignal {
    Term,
    Kill,
}

impl TerminateSignal {
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Term => "SIGTERM",
            Self::Kill => "SIGKILL",
        }
    }
}

/// Outcome of a host `ps` identity probe.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum IdentityProbeOutput {
    /// Probe succeeded with raw stdout.
    Stdout(String),
    /// Process is gone.
    Missing,
    /// Probe timed out.
    Timeout,
    /// Probe failed for another host reason.
    Error,
}

/// Injectable host surface for process identity and signaling.
pub trait ProcessIdentityHost {
    /// Return the process group id for `pid`, or `None` when the pid is gone.
    fn get_pgid(&self, pid: i32) -> Option<i32>;
    /// Run `ps -p <pid> -o lstart= -o command=` and classify the outcome.
    fn probe_ps_identity(&self, pid: i32) -> IdentityProbeOutput;
    /// Enumerate direct children of `pid` via `pgrep -P`.
    fn pgrep_children(&self, pid: i32) -> Vec<i32>;
    /// Enumerate members of process group `pgid` via `pgrep -g`.
    fn pgrep_group(&self, pgid: i32) -> Vec<i32>;
    /// Signal one process. Returns whether the signal was delivered.
    fn signal_process(&self, pid: i32, signal: TerminateSignal) -> bool;
    /// Signal one process group. Returns whether the signal was delivered.
    fn signal_group(&self, pgid: i32, signal: TerminateSignal) -> bool;
    /// Sleep for the requested duration.
    fn sleep(&self, duration: Duration);
    /// Monotonic clock used by await loops.
    fn monotonic_now(&self) -> Duration;
    /// Wall-clock seconds for kill-log timestamps.
    fn wall_time_secs(&self) -> f64;
    /// Current process id.
    fn current_pid(&self) -> i32;
    /// Parent process id.
    fn parent_pid(&self) -> i32;
    /// Parent of `pid`, when available.
    fn parent_of(&self, pid: i32) -> Option<i32>;
    /// Full process table as `(pid, command)` rows.
    fn list_processes(&self) -> Vec<(i32, String)>;
    /// Resolve a path the same way as Python `Path.resolve(strict=False)`.
    fn resolve_path(&self, path: &str) -> String;
    /// Append one UTF-8 line to a kill log, creating parents when needed.
    fn append_kill_log_line(&self, path: &Path, line: &str);
    /// Atomically write an identity JSON record.
    ///
    /// # Errors
    ///
    /// Returns a host-specific message when the destination cannot be written.
    fn write_identity_file(&self, path: &Path, text: &str) -> Result<(), String>;
    /// Read an identity JSON record.
    fn read_identity_file(&self, path: &Path) -> Option<String>;
    /// Remove a path if present.
    fn remove_file(&self, path: &Path);
    /// Return true when `path` is a regular non-symlink file.
    fn is_regular_file(&self, path: &Path) -> bool;
    /// Return mtime nanoseconds for a regular file.
    fn file_mtime_ns(&self, path: &Path) -> Option<u64>;
    /// Read a UTF-8 text file, replacing invalid sequences.
    fn read_text_lossy(&self, path: &Path) -> Option<String>;
}

/// Collapse whitespace and newlines the same way as the Python owner.
#[must_use]
pub fn normalize_command_signature(value: &str) -> String {
    value
        .replace(['\r', '\n'], " ")
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}

/// Bound a command string for kill-log retention.
#[must_use]
pub fn bounded_command(value: &str, limit: usize) -> String {
    let normalized = normalize_command_signature(value);
    if normalized.len() <= limit {
        return normalized;
    }
    let keep = limit.saturating_sub(1);
    let mut truncated = normalized.chars().take(keep).collect::<String>();
    truncated.push('…');
    truncated
}

/// Parse `ps` identity stdout into a recorded identity.
#[must_use]
#[allow(clippy::similar_names)]
pub fn parse_ps_identity(
    process_id: i32,
    process_group_id: i32,
    stdout: &str,
    expected_signature: &str,
) -> Option<RecordedProcessIdentity> {
    for raw in stdout.lines() {
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            continue;
        }
        let mut parts = trimmed.split_whitespace();
        let mut start_parts = Vec::with_capacity(PS_LSTART_FIELD_COUNT);
        for _ in 0..PS_LSTART_FIELD_COUNT {
            start_parts.push(parts.next()?);
        }
        let command = parts.collect::<Vec<_>>().join(" ");
        return Some(RecordedProcessIdentity {
            pid: process_id,
            pgid: process_group_id,
            start_time: normalize_command_signature(&start_parts.join(" ")),
            command_signature: normalize_command_signature(&command),
            expected_signature: normalize_command_signature(expected_signature),
        });
    }
    None
}

/// Probe the live identity for one pid.
#[must_use]
#[allow(clippy::similar_names)]
pub fn probe_process_identity(
    host: &dyn ProcessIdentityHost,
    process_id: i32,
    expected_signature: &str,
) -> ProcessIdentityProbeResult {
    let mut failure_reason = String::from("missing-pid");
    if process_id <= 0 {
        return ProcessIdentityProbeResult {
            identity: None,
            failure_reason,
        };
    }
    let Some(process_group_id) = host.get_pgid(process_id) else {
        return ProcessIdentityProbeResult {
            identity: None,
            failure_reason,
        };
    };
    match host.probe_ps_identity(process_id) {
        IdentityProbeOutput::Error => failure_reason = String::from("identity-probe-error"),
        IdentityProbeOutput::Timeout => failure_reason = String::from("identity-probe-timeout"),
        IdentityProbeOutput::Missing => {}
        IdentityProbeOutput::Stdout(stdout) => {
            if let Some(identity) =
                parse_ps_identity(process_id, process_group_id, &stdout, expected_signature)
            {
                return ProcessIdentityProbeResult {
                    identity: Some(identity),
                    failure_reason: String::new(),
                };
            }
        }
    }
    ProcessIdentityProbeResult {
        identity: None,
        failure_reason,
    }
}

/// Read the live identity for one pid.
#[must_use]
pub fn read_process_identity(
    host: &dyn ProcessIdentityHost,
    pid: i32,
    expected_signature: &str,
) -> Option<RecordedProcessIdentity> {
    probe_process_identity(host, pid, expected_signature).identity
}

/// Retry identity capture until the process group is stable.
#[must_use]
pub fn read_stable_process_identity(
    host: &dyn ProcessIdentityHost,
    pid: i32,
    expected_signature: &str,
    require_pgid_match: bool,
) -> Option<RecordedProcessIdentity> {
    for attempt in 0..PROCESS_IDENTITY_CAPTURE_ATTEMPTS {
        if let Some(identity) = read_process_identity(host, pid, expected_signature)
            && (!require_pgid_match || identity.pgid == pid)
        {
            return Some(identity);
        }
        if attempt + 1 < PROCESS_IDENTITY_CAPTURE_ATTEMPTS {
            host.sleep(PROCESS_IDENTITY_CAPTURE_SLEEP);
        }
    }
    None
}

/// Validate that a recorded identity still names the same live process.
#[must_use]
pub fn validate_process_identity(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
) -> ValidationResult {
    let probe = probe_process_identity(host, recorded.pid, &recorded.expected_signature);
    let Some(current) = probe.identity else {
        return ValidationResult {
            ok: false,
            reason: probe.failure_reason,
            current: None,
        };
    };
    if current.pgid != recorded.pgid {
        return ValidationResult {
            ok: false,
            reason: "pgid-mismatch".to_owned(),
            current: Some(current),
        };
    }
    if normalize_command_signature(&current.start_time)
        != normalize_command_signature(&recorded.start_time)
    {
        return ValidationResult {
            ok: false,
            reason: "start-time-mismatch".to_owned(),
            current: Some(current),
        };
    }
    let recorded_command = normalize_command_signature(&recorded.command_signature);
    let current_command = normalize_command_signature(&current.command_signature);
    if !recorded_command.is_empty() && current_command != recorded_command {
        return ValidationResult {
            ok: false,
            reason: "command-mismatch".to_owned(),
            current: Some(current),
        };
    }
    let expected = normalize_command_signature(&recorded.expected_signature);
    if !expected.is_empty() && !current_command.contains(&expected) {
        return ValidationResult {
            ok: false,
            reason: "expected-command-mismatch".to_owned(),
            current: Some(current),
        };
    }
    ValidationResult {
        ok: true,
        reason: "ok".to_owned(),
        current: Some(current),
    }
}

/// Recursively collect descendant pids of `pid`.
#[must_use]
pub fn collect_descendants(host: &dyn ProcessIdentityHost, pid: i32) -> Vec<i32> {
    let mut descendants = Vec::new();
    for child in host.pgrep_children(pid) {
        descendants.extend(collect_descendants(host, child));
        descendants.push(child);
    }
    descendants
}

/// Collect unique members of a process group.
#[must_use]
pub fn collect_process_group_members(host: &dyn ProcessIdentityHost, pgid: i32) -> Vec<i32> {
    let mut members = Vec::new();
    let mut seen = BTreeSet::new();
    for member in host.pgrep_group(pgid) {
        if seen.insert(member) {
            members.push(member);
        }
    }
    members
}

/// Serialize and append one kill-log event after outbound redaction.
pub fn append_kill_log(host: &dyn ProcessIdentityHost, path: Option<&Path>, event: &KillLogEvent) {
    let Some(path) = path else {
        return;
    };
    let Ok(Value::Object(mut payload)) = serde_json::to_value(event) else {
        return;
    };
    for value in payload.values_mut() {
        if let Value::String(text) = value {
            let redacted = redact(text).text().to_owned();
            *text = redacted;
        }
    }
    if let Some(Value::String(command)) = payload.get_mut("command") {
        *command = bounded_command(command, COMMAND_LOG_LIMIT);
    }
    payload.insert("ts".to_owned(), Value::from(host.wall_time_secs()));
    let Ok(line) = serde_json::to_string(&Value::Object(sorted_object(&payload))) else {
        return;
    };
    host.append_kill_log_line(path, &format!("{line}\n"));
}

fn sorted_object(map: &Map<String, Value>) -> Map<String, Value> {
    let mut ordered = Map::new();
    let mut keys = map.keys().cloned().collect::<Vec<_>>();
    keys.sort_unstable();
    for key in keys {
        if let Some(value) = map.get(&key) {
            ordered.insert(key, value.clone());
        }
    }
    ordered
}

fn log_signal(
    host: &dyn ProcessIdentityHost,
    log_path: Option<&Path>,
    signal: TerminateSignal,
    snapshot: &KillTargetSnapshot,
    caller: &str,
    reason: &str,
) {
    append_kill_log(
        host,
        log_path,
        &KillLogEvent {
            event: "signal".to_owned(),
            signal: signal.name().to_owned(),
            pid: snapshot.pid,
            pgid: snapshot.pgid,
            command: snapshot.command.clone(),
            caller: caller.to_owned(),
            reason: reason.to_owned(),
            descendants: snapshot.descendants.clone(),
            tmpdir_needle: String::new(),
            physical_needle: String::new(),
        },
    );
}

fn validated_missing_leader_members(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
) -> Option<Vec<i32>> {
    let descendants = collect_process_group_members(host, recorded.pgid);
    if descendants.is_empty() {
        return None;
    }
    let mut validated_members = Vec::with_capacity(descendants.len());
    for child in descendants {
        let child_identity = read_process_identity(host, child, &recorded.expected_signature)?;
        if child_identity.pgid != recorded.pgid {
            return None;
        }
        validated_members.push(child);
    }
    Some(validated_members)
}

struct SignalRequest<'a> {
    log_path: Option<&'a Path>,
    recorded: &'a RecordedProcessIdentity,
    descendants: &'a [i32],
    command: &'a str,
    signal: TerminateSignal,
    caller: &'a str,
    reason: &'a str,
}

fn signal_group_and_descendants(host: &dyn ProcessIdentityHost, request: &SignalRequest<'_>) {
    let snapshot = KillTargetSnapshot {
        pid: request.recorded.pid,
        pgid: request.recorded.pgid,
        descendants: request.descendants.to_vec(),
        command: request.command.to_owned(),
    };
    log_signal(
        host,
        request.log_path,
        request.signal,
        &snapshot,
        request.caller,
        request.reason,
    );
    host.signal_group(request.recorded.pgid, request.signal);
    for child in request.descendants {
        append_kill_log(
            host,
            request.log_path,
            &KillLogEvent {
                event: "signal".to_owned(),
                signal: request.signal.name().to_owned(),
                pid: *child,
                pgid: request.recorded.pgid,
                command: String::new(),
                caller: request.caller.to_owned(),
                reason: request.reason.to_owned(),
                descendants: Vec::new(),
                tmpdir_needle: String::new(),
                physical_needle: String::new(),
            },
        );
        let _ = host.signal_process(*child, request.signal);
    }
}

/// Terminate a process group only when the recorded identity still matches.
#[must_use]
pub fn terminate_validated_process_group(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
    log_path: Option<&Path>,
    caller: &str,
    reason: &str,
) -> ValidationResult {
    let validation = validate_process_identity(host, recorded);
    if !validation.ok && validation.reason != "missing-pid" {
        return validation;
    }
    let current = validation
        .current
        .clone()
        .unwrap_or_else(|| recorded.clone());
    let descendants = if validation.ok {
        collect_descendants(host, recorded.pid)
    } else {
        let Some(members) = validated_missing_leader_members(host, recorded) else {
            return validation;
        };
        members
    };
    signal_group_and_descendants(
        host,
        &SignalRequest {
            log_path,
            recorded,
            descendants: &descendants,
            command: &current.command_signature,
            signal: TerminateSignal::Term,
            caller,
            reason,
        },
    );
    host.sleep(TERMINATE_ESCALATION_SLEEP);
    let validation = validate_process_identity(host, recorded);
    if !validation.ok && validation.reason != "missing-pid" {
        return validation;
    }
    let kill_descendants = if validation.ok {
        collect_descendants(host, recorded.pid)
    } else {
        collect_process_group_members(host, recorded.pgid)
    };
    if !validation.ok && kill_descendants.is_empty() {
        return ValidationResult {
            ok: true,
            reason: "ok".to_owned(),
            current: Some(current),
        };
    }
    let command = validation
        .current
        .as_ref()
        .unwrap_or(&current)
        .command_signature
        .clone();
    signal_group_and_descendants(
        host,
        &SignalRequest {
            log_path,
            recorded,
            descendants: &kill_descendants,
            command: &command,
            signal: TerminateSignal::Kill,
            caller,
            reason,
        },
    );
    if !validation.ok && validation.reason == "missing-pid" {
        return ValidationResult {
            ok: true,
            reason: "ok".to_owned(),
            current: Some(current),
        };
    }
    validation
}

/// Render an identity record as indented, sorted JSON.
#[must_use]
pub fn identity_to_json(
    recorded: &RecordedProcessIdentity,
    extra: Option<&Map<String, Value>>,
) -> String {
    let mut payload = Map::new();
    payload.insert("pid".to_owned(), Value::from(recorded.pid));
    payload.insert("pgid".to_owned(), Value::from(recorded.pgid));
    payload.insert(
        "start_time".to_owned(),
        Value::String(recorded.start_time.clone()),
    );
    payload.insert(
        "command_signature".to_owned(),
        Value::String(recorded.command_signature.clone()),
    );
    payload.insert(
        "expected_signature".to_owned(),
        Value::String(recorded.expected_signature.clone()),
    );
    if let Some(extra) = extra {
        for (key, value) in extra {
            payload.insert(key.clone(), value.clone());
        }
    }
    let mut text = serde_json::to_string_pretty(&Value::Object(sorted_object(&payload)))
        .unwrap_or_else(|_| "{}".to_owned());
    text.push('\n');
    text
}

/// Persist an identity record.
///
/// # Errors
///
/// Returns the host write error when the destination cannot be published.
pub fn write_identity_record(
    host: &dyn ProcessIdentityHost,
    path: &Path,
    recorded: &RecordedProcessIdentity,
    extra: Option<&Map<String, Value>>,
) -> Result<(), String> {
    host.write_identity_file(path, &identity_to_json(recorded, extra))
}

/// Read a persisted identity record.
#[must_use]
pub fn read_identity_record(
    host: &dyn ProcessIdentityHost,
    path: &Path,
) -> Option<RecordedProcessIdentity> {
    let text = host.read_identity_file(path)?;
    let payload: Value = serde_json::from_str(&text).ok()?;
    let object = payload.as_object()?;
    Some(RecordedProcessIdentity {
        pid: object.get("pid")?.as_i64()?.try_into().ok()?,
        pgid: object.get("pgid")?.as_i64()?.try_into().ok()?,
        start_time: object.get("start_time")?.as_str()?.to_owned(),
        command_signature: object.get("command_signature")?.as_str()?.to_owned(),
        expected_signature: object
            .get("expected_signature")
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_owned(),
    })
}

fn validated_tmpdir(raw: &str) -> Option<PathBuf> {
    if raw.is_empty() {
        return None;
    }
    let path = PathBuf::from(raw);
    if !path.is_absolute() {
        return None;
    }
    Some(path)
}

/// Whether a Step 3 review-result env reports loop completion.
#[must_use]
pub fn result_env_has_step3_status(
    host: &dyn ProcessIdentityHost,
    tmpdir: &Path,
    since_mtime_ns: u64,
) -> bool {
    let result_env = tmpdir.join(".step3-review-result.env");
    if !host.is_regular_file(&result_env) {
        return false;
    }
    if since_mtime_ns > 0
        && host
            .file_mtime_ns(&result_env)
            .is_none_or(|mtime| mtime < since_mtime_ns)
    {
        return false;
    }
    let Some(text) = host.read_text_lossy(&result_env) else {
        return false;
    };
    for line in text.lines() {
        if let Some(value) = line.strip_prefix("STEP3_REVIEW_LOOP_STATUS=")
            && !value.is_empty()
        {
            return true;
        }
        if line == "LOOP_STATUS=zero-findings-degraded-panel" {
            return true;
        }
    }
    false
}

/// Poll until the recorded loop process exits or the timeout elapses.
#[must_use]
pub fn await_loop_poll(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
    tmpdir: &Path,
    identity_mtime_ns: u64,
    timeout: Duration,
    require_step3_result_env: bool,
) -> i32 {
    let mut missing_pid_since: Option<Duration> = None;
    let deadline = host.monotonic_now().saturating_add(timeout);
    while host.monotonic_now() < deadline {
        let validation = validate_process_identity(host, recorded);
        if validation.ok {
            missing_pid_since = None;
            host.sleep(Duration::from_millis(200));
            continue;
        }
        if validation.reason == "missing-pid" {
            if !require_step3_result_env {
                let now = host.monotonic_now();
                match missing_pid_since {
                    None => missing_pid_since = Some(now),
                    Some(started)
                        if now.saturating_sub(started) >= DESIGN_STEP3_MISSING_PID_GRACE =>
                    {
                        return 0;
                    }
                    Some(_) => {}
                }
                host.sleep(Duration::from_millis(200));
                continue;
            }
            if result_env_has_step3_status(host, tmpdir, identity_mtime_ns) {
                return 0;
            }
            let now = host.monotonic_now();
            match missing_pid_since {
                None => missing_pid_since = Some(now),
                Some(started) if now.saturating_sub(started) >= DESIGN_STEP3_MISSING_PID_GRACE => {
                    return 1;
                }
                Some(_) => {}
            }
            host.sleep(Duration::from_millis(200));
            continue;
        }
        break;
    }
    1
}

fn parse_pid_argument(raw: &str) -> Option<i32> {
    if raw.is_empty() || !raw.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    raw.parse().ok()
}

/// Capture and persist the design Step 3 loop identity.
#[must_use]
pub fn write_loop_identity(
    host: &dyn ProcessIdentityHost,
    design_tmpdir: &str,
    pid_raw: &str,
    expected_signature: &str,
) -> i32 {
    let Some(tmpdir) = validated_tmpdir(design_tmpdir) else {
        return 0;
    };
    let Some(pid) = parse_pid_argument(pid_raw) else {
        return 0;
    };
    let Some(identity) = read_stable_process_identity(host, pid, expected_signature, true) else {
        return 0;
    };
    let _ = write_identity_record(
        host,
        &tmpdir.join(DESIGN_STEP3_LOOP_IDENTITY_FILE),
        &identity,
        None,
    );
    0
}

/// Await the design Step 3 loop identity.
#[must_use]
pub fn await_loop_identity(
    host: &dyn ProcessIdentityHost,
    design_tmpdir: &str,
    pid_raw: &str,
    timeout_s: &str,
    reattach: bool,
) -> i32 {
    let Some(tmpdir) = validated_tmpdir(design_tmpdir) else {
        return 1;
    };
    let Ok(timeout_s) = timeout_s.parse::<f64>() else {
        return 1;
    };
    if timeout_s <= 0.0 {
        return 1;
    }
    let Some(pid) = parse_pid_argument(pid_raw) else {
        return 1;
    };
    let sidecar = tmpdir.join(DESIGN_STEP3_LOOP_IDENTITY_FILE);
    let Some(recorded) = read_identity_record(host, &sidecar) else {
        return 1;
    };
    if recorded.pid != pid {
        return 1;
    }
    let detached_marker = tmpdir.join(DESIGN_STEP3_WRAPPER_DETACHED_FILE);
    if !reattach && !host.is_regular_file(&detached_marker) {
        return 1;
    }
    let Some(identity_mtime_ns) = host.file_mtime_ns(&sidecar).filter(|value| *value > 0) else {
        return 1;
    };
    await_loop_poll(
        host,
        &recorded,
        &tmpdir,
        identity_mtime_ns,
        Duration::from_secs_f64(timeout_s),
        true,
    )
}

/// Tear down the design Step 3 loop identity after validated termination.
#[must_use]
pub fn teardown_loop_identity(
    host: &dyn ProcessIdentityHost,
    design_tmpdir: &str,
    pid_raw: &str,
) -> i32 {
    let Some(tmpdir) = validated_tmpdir(design_tmpdir) else {
        return 0;
    };
    let Some(pid) = parse_pid_argument(pid_raw) else {
        return 0;
    };
    let sidecar = tmpdir.join(DESIGN_STEP3_LOOP_IDENTITY_FILE);
    let Some(recorded) = read_identity_record(host, &sidecar) else {
        return 0;
    };
    if recorded.pid != pid {
        return 0;
    }
    let validation = terminate_validated_process_group(
        host,
        &recorded,
        Some(&tmpdir.join(DESIGN_STEP3_KILL_LOG_FILE)),
        "design-step3-review",
        "step3-trap-cleanup",
    );
    if validation.ok {
        host.remove_file(&sidecar);
    }
    0
}

/// Capture and persist the implement Step 5 loop identity.
#[must_use]
pub fn write_step5_loop_identity(
    host: &dyn ProcessIdentityHost,
    implement_tmpdir: &str,
    pid_raw: &str,
    expected_signature: &str,
) -> i32 {
    let Some(tmpdir) = validated_tmpdir(implement_tmpdir) else {
        return 0;
    };
    let Some(pid) = parse_pid_argument(pid_raw) else {
        return 0;
    };
    let Some(identity) = read_stable_process_identity(host, pid, expected_signature, true) else {
        return 0;
    };
    let _ = write_identity_record(
        host,
        &tmpdir.join(IMPLEMENT_STEP5_LOOP_IDENTITY_FILE),
        &identity,
        None,
    );
    0
}

fn collect_ancestor_pids(host: &dyn ProcessIdentityHost, pid: i32, max_depth: usize) -> Vec<i32> {
    if pid <= 0 {
        return Vec::new();
    }
    let mut ancestors = Vec::new();
    let mut seen = BTreeSet::from([pid]);
    let mut current = pid;
    for _ in 0..max_depth {
        let Some(parent) = host.parent_of(current) else {
            break;
        };
        if parent <= 1 || !seen.insert(parent) {
            break;
        }
        ancestors.push(parent);
        current = parent;
    }
    ancestors
}

/// Kill processes whose command line mentions the session tmpdir.
#[must_use]
pub fn kill_session_background_processes(host: &dyn ProcessIdentityHost, tmpdir: &str) -> bool {
    if tmpdir.is_empty() {
        return false;
    }
    let mut skip = BTreeSet::new();
    let current_pid = host.current_pid();
    let parent_pid = host.parent_pid();
    for pid in [current_pid, parent_pid] {
        if pid > 0 {
            skip.insert(pid);
        }
    }
    for ancestor in collect_ancestor_pids(host, current_pid, 32) {
        skip.insert(ancestor);
    }
    if parent_pid > 1 && !skip.contains(&parent_pid) {
        for ancestor in collect_ancestor_pids(host, parent_pid, 32) {
            skip.insert(ancestor);
        }
    }
    let physical = host.resolve_path(tmpdir);
    let mut killed = false;
    for (pid, command) in host.list_processes() {
        if pid <= 0 || skip.contains(&pid) {
            continue;
        }
        let mentions_tmpdir = command.contains(tmpdir)
            || (!physical.is_empty() && physical != tmpdir && command.contains(&physical));
        if !mentions_tmpdir {
            continue;
        }
        append_kill_log(
            host,
            Some(&PathBuf::from(tmpdir).join(FINALIZE_KILL_LOG_FILE)),
            &KillLogEvent {
                event: "signal".to_owned(),
                signal: "SIGTERM".to_owned(),
                pid,
                pgid: 0,
                command,
                caller: "session kill-background-processes".to_owned(),
                reason: "tmpdir-scoped-background-cleanup".to_owned(),
                descendants: Vec::new(),
                tmpdir_needle: tmpdir.to_owned(),
                physical_needle: physical.clone(),
            },
        );
        if host.signal_process(pid, TerminateSignal::Term) {
            killed = true;
        }
    }
    killed
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        cell::RefCell,
        collections::HashMap,
        sync::atomic::{AtomicU64, Ordering},
    };

    #[derive(Default)]
    struct FakeHost {
        pgid: HashMap<i32, i32>,
        ps: RefCell<HashMap<i32, Vec<IdentityProbeOutput>>>,
        children: HashMap<i32, Vec<i32>>,
        groups: HashMap<i32, Vec<i32>>,
        parents: HashMap<i32, i32>,
        processes: Vec<(i32, String)>,
        signals: RefCell<Vec<(i32, TerminateSignal, bool)>>,
        files: RefCell<HashMap<PathBuf, String>>,
        mtimes: RefCell<HashMap<PathBuf, u64>>,
        now: AtomicU64,
        wall: RefCell<f64>,
        current_pid: i32,
        parent_pid: i32,
    }

    impl ProcessIdentityHost for FakeHost {
        fn get_pgid(&self, pid: i32) -> Option<i32> {
            self.pgid.get(&pid).copied()
        }
        fn probe_ps_identity(&self, pid: i32) -> IdentityProbeOutput {
            let mut map = self.ps.borrow_mut();
            let Some(queue) = map.get_mut(&pid) else {
                return IdentityProbeOutput::Missing;
            };
            if queue.is_empty() {
                return IdentityProbeOutput::Missing;
            }
            queue.remove(0)
        }
        fn pgrep_children(&self, pid: i32) -> Vec<i32> {
            self.children.get(&pid).cloned().unwrap_or_default()
        }
        fn pgrep_group(&self, pgid: i32) -> Vec<i32> {
            self.groups.get(&pgid).cloned().unwrap_or_default()
        }
        fn signal_process(&self, pid: i32, signal: TerminateSignal) -> bool {
            self.signals.borrow_mut().push((pid, signal, false));
            true
        }
        fn signal_group(&self, pgid: i32, signal: TerminateSignal) -> bool {
            self.signals.borrow_mut().push((pgid, signal, true));
            true
        }
        fn sleep(&self, _duration: Duration) {}
        fn monotonic_now(&self) -> Duration {
            Duration::from_millis(self.now.fetch_add(200, Ordering::Relaxed))
        }
        fn wall_time_secs(&self) -> f64 {
            *self.wall.borrow()
        }
        fn current_pid(&self) -> i32 {
            self.current_pid
        }
        fn parent_pid(&self) -> i32 {
            self.parent_pid
        }
        fn parent_of(&self, pid: i32) -> Option<i32> {
            self.parents.get(&pid).copied()
        }
        fn list_processes(&self) -> Vec<(i32, String)> {
            self.processes.clone()
        }
        fn resolve_path(&self, path: &str) -> String {
            path.to_owned()
        }
        fn append_kill_log_line(&self, path: &Path, line: &str) {
            let mut files = self.files.borrow_mut();
            files.entry(path.to_path_buf()).or_default().push_str(line);
        }
        fn write_identity_file(&self, path: &Path, text: &str) -> Result<(), String> {
            self.files
                .borrow_mut()
                .insert(path.to_path_buf(), text.to_owned());
            self.mtimes.borrow_mut().insert(path.to_path_buf(), 1_000);
            Ok(())
        }
        fn read_identity_file(&self, path: &Path) -> Option<String> {
            self.files.borrow().get(path).cloned()
        }
        fn remove_file(&self, path: &Path) {
            self.files.borrow_mut().remove(path);
            self.mtimes.borrow_mut().remove(path);
        }
        fn is_regular_file(&self, path: &Path) -> bool {
            self.files.borrow().contains_key(path)
        }
        fn file_mtime_ns(&self, path: &Path) -> Option<u64> {
            self.mtimes.borrow().get(path).copied()
        }
        fn read_text_lossy(&self, path: &Path) -> Option<String> {
            self.files.borrow().get(path).cloned()
        }
    }

    fn recorded() -> RecordedProcessIdentity {
        RecordedProcessIdentity {
            pid: 123,
            pgid: 123,
            start_time: "Fri Jul 3 17:01:02 2026".to_owned(),
            command_signature: "/usr/bin/python3 /repo/python/cli.py plan-review run".to_owned(),
            expected_signature: "plan-review run".to_owned(),
        }
    }

    fn ps_stdout(command: &str) -> IdentityProbeOutput {
        IdentityProbeOutput::Stdout(format!("Fri Jul  3 17:01:02 2026 {command}\n"))
    }

    #[test]
    fn normalize_collapses_whitespace_and_newlines() {
        assert_eq!(normalize_command_signature("a\nb\r  c"), "a b c");
        assert_eq!(bounded_command("abcdef", 4), "abc…");
    }

    #[test]
    fn validate_rejects_start_time_and_command_mismatches() {
        let mut host = FakeHost::default();
        host.pgid.insert(123, 123);
        host.ps.borrow_mut().insert(
            123,
            vec![ps_stdout(
                "/usr/bin/python3 /repo/python/cli.py plan-review run",
            )],
        );
        let mut bad_start = recorded();
        bad_start.start_time = "Fri Jul 3 17:01:01 2026".to_owned();
        assert_eq!(
            validate_process_identity(&host, &bad_start).reason,
            "start-time-mismatch"
        );

        host.ps
            .borrow_mut()
            .insert(123, vec![ps_stdout("sleep 100")]);
        let mut bad_command = recorded();
        bad_command.command_signature = "other command".to_owned();
        assert_eq!(
            validate_process_identity(&host, &bad_command).reason,
            "command-mismatch"
        );
    }

    #[test]
    fn pid_reuse_does_not_signal_mismatched_process() {
        let mut host = FakeHost::default();
        host.pgid.insert(123, 123);
        // First validation (pre-SIGTERM) matches the recorded identity.
        // After SIGTERM sleep, the same PID has been reused by an unrelated command.
        host.ps.borrow_mut().insert(
            123,
            vec![
                ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run"),
                ps_stdout("unrelated recycled command"),
            ],
        );
        host.children.insert(123, Vec::new());
        let result = terminate_validated_process_group(
            &host,
            &recorded(),
            Some(Path::new("/tmp/kill.jsonl")),
            "test",
            "unit",
        );
        assert_eq!(result.reason, "command-mismatch");
        let signals = host.signals.borrow().clone();
        assert_eq!(signals.len(), 1);
        assert_eq!(signals[0], (123, TerminateSignal::Term, true));
        assert!(
            !signals
                .iter()
                .any(|(_, signal, _)| *signal == TerminateSignal::Kill),
            "PID reuse must not escalate to SIGKILL"
        );
    }

    #[test]
    fn terminate_logs_before_signaling_and_escalates_when_still_matched() {
        let mut host = FakeHost::default();
        host.pgid.insert(123, 123);
        host.ps.borrow_mut().insert(
            123,
            vec![
                ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run"),
                ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run"),
            ],
        );
        host.children.insert(123, vec![10, 11]);
        host.children.insert(10, Vec::new());
        host.children.insert(11, Vec::new());
        let log = PathBuf::from("/tmp/kill.jsonl");
        let result =
            terminate_validated_process_group(&host, &recorded(), Some(&log), "test", "unit");
        assert!(result.ok);
        let text = host.files.borrow().get(&log).cloned().unwrap();
        assert!(text.contains("\"signal\":\"SIGTERM\""));
        let signals = host.signals.borrow().clone();
        assert!(signals.contains(&(123, TerminateSignal::Term, true)));
        assert!(signals.contains(&(10, TerminateSignal::Term, false)));
        assert!(signals.contains(&(11, TerminateSignal::Kill, false)));
    }

    #[test]
    fn kill_session_background_processes_skips_ancestors_and_logs() {
        let mut host = FakeHost {
            current_pid: 200,
            parent_pid: 100,
            ..FakeHost::default()
        };
        host.parents.insert(200, 100);
        host.parents.insert(100, 50);
        host.parents.insert(50, 1);
        host.processes = vec![
            (50, "ancestor".to_owned()),
            (999, "/tmp/session-dir worker".to_owned()),
        ];
        assert!(kill_session_background_processes(&host, "/tmp/session-dir"));
        let signals = host.signals.borrow().clone();
        assert_eq!(signals, vec![(999, TerminateSignal::Term, false)]);
        let log = PathBuf::from("/tmp/session-dir").join(FINALIZE_KILL_LOG_FILE);
        let text = host.files.borrow().get(&log).cloned().unwrap();
        assert!(text.contains("\"pid\":999"));
    }

    #[test]
    fn loop_identity_write_await_and_teardown_cover_happy_paths() {
        let mut host = FakeHost::default();
        host.pgid.insert(123, 123);
        let matching = ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run");
        host.ps.borrow_mut().insert(
            123,
            vec![
                matching.clone(),             // write_loop_identity
                IdentityProbeOutput::Missing, // await sees exit
                matching.clone(),             // teardown pre-signal validate
                IdentityProbeOutput::Missing, // teardown post-SIGTERM
                matching,                     // write_step5_loop_identity
            ],
        );
        let tmp = PathBuf::from("/tmp/design-loop");
        assert_eq!(
            write_loop_identity(&host, tmp.to_str().unwrap(), "123", "plan-review run"),
            0
        );
        let sidecar = tmp.join(DESIGN_STEP3_LOOP_IDENTITY_FILE);
        assert!(host.is_regular_file(&sidecar));
        host.files.borrow_mut().insert(
            tmp.join(DESIGN_STEP3_WRAPPER_DETACHED_FILE),
            "PID=123\n".to_owned(),
        );
        host.mtimes.borrow_mut().insert(sidecar.clone(), 2_000);
        host.files.borrow_mut().insert(
            tmp.join(".step3-review-result.env"),
            "STEP3_REVIEW_LOOP_STATUS=complete\n".to_owned(),
        );
        host.mtimes
            .borrow_mut()
            .insert(tmp.join(".step3-review-result.env"), 3_000);
        assert_eq!(
            await_loop_identity(&host, tmp.to_str().unwrap(), "123", "1", false),
            0
        );
        assert_eq!(
            teardown_loop_identity(&host, tmp.to_str().unwrap(), "123"),
            0
        );
        assert!(!host.is_regular_file(&sidecar));
        assert_eq!(
            write_step5_loop_identity(&host, tmp.to_str().unwrap(), "123", "review-and-fix step5"),
            0
        );
        assert!(host.is_regular_file(&tmp.join(IMPLEMENT_STEP5_LOOP_IDENTITY_FILE)));
    }

    #[test]
    fn parse_and_collect_helpers_cover_edge_inputs() {
        assert!(parse_ps_identity(1, 1, "", "").is_none());
        assert_eq!(
            parse_ps_identity(1, 1, "Fri Jul  3 17:01:02 2026 cmd with spaces\n", "cmd")
                .unwrap()
                .command_signature,
            "cmd with spaces"
        );
        let mut host = FakeHost::default();
        host.children.insert(1, vec![2]);
        host.children.insert(2, Vec::new());
        host.groups.insert(9, vec![9, 10, 10]);
        assert_eq!(collect_descendants(&host, 1), vec![2]);
        assert_eq!(collect_process_group_members(&host, 9), vec![9, 10]);
        assert!(probe_process_identity(&host, 0, "").identity.is_none());
        assert_eq!(
            probe_process_identity(&host, 5, "").failure_reason,
            "missing-pid"
        );
        host.pgid.insert(5, 5);
        host.ps
            .borrow_mut()
            .insert(5, vec![IdentityProbeOutput::Timeout]);
        assert_eq!(
            probe_process_identity(&host, 5, "").failure_reason,
            "identity-probe-timeout"
        );
        host.ps
            .borrow_mut()
            .insert(5, vec![IdentityProbeOutput::Error]);
        assert_eq!(
            probe_process_identity(&host, 5, "").failure_reason,
            "identity-probe-error"
        );
        assert!(!result_env_has_step3_status(&host, Path::new("/tmp/x"), 1));
        assert_eq!(await_loop_identity(&host, "relative", "1", "1", false), 1);
        assert_eq!(await_loop_identity(&host, "/tmp/x", "abc", "1", false), 1);
        assert_eq!(await_loop_identity(&host, "/tmp/x", "1", "0", false), 1);
        assert_eq!(TerminateSignal::Term.name(), "SIGTERM");
        assert_eq!(TerminateSignal::Kill.name(), "SIGKILL");
    }

    #[test]
    fn await_loop_poll_accepts_degraded_panel_status() {
        let mut host = FakeHost::default();
        host.pgid.insert(7, 7);
        let recorded = RecordedProcessIdentity {
            pid: 7,
            pgid: 7,
            start_time: "Fri Jul 3 17:01:02 2026".to_owned(),
            command_signature: "loop".to_owned(),
            expected_signature: "loop".to_owned(),
        };
        host.ps
            .borrow_mut()
            .insert(7, vec![IdentityProbeOutput::Missing]);
        let tmp = PathBuf::from("/tmp/await-degraded");
        host.files.borrow_mut().insert(
            tmp.join(".step3-review-result.env"),
            "LOOP_STATUS=zero-findings-degraded-panel\n".to_owned(),
        );
        host.mtimes
            .borrow_mut()
            .insert(tmp.join(".step3-review-result.env"), 5_000);
        assert_eq!(
            await_loop_poll(&host, &recorded, &tmp, 1_000, Duration::from_secs(1), true),
            0
        );
    }

    #[test]
    fn terminate_with_descendants_and_identity_record_round_trip() {
        let mut host = FakeHost::default();
        host.pgid.insert(50, 50);
        host.pgid.insert(51, 50);
        host.children.insert(50, vec![51]);
        host.children.insert(51, Vec::new());
        let matching = ps_stdout("worker cmd");
        host.ps.borrow_mut().insert(
            50,
            vec![matching.clone(), matching, IdentityProbeOutput::Missing],
        );
        host.ps.borrow_mut().insert(
            51,
            vec![
                ps_stdout("child cmd"),
                ps_stdout("child cmd"),
                IdentityProbeOutput::Missing,
            ],
        );
        let recorded = RecordedProcessIdentity {
            pid: 50,
            pgid: 50,
            start_time: "Fri Jul 3 17:01:02 2026".to_owned(),
            command_signature: "worker cmd".to_owned(),
            expected_signature: "worker".to_owned(),
        };
        let path = PathBuf::from("/tmp/identity-roundtrip.json");
        write_identity_record(&host, &path, &recorded, None).expect("write");
        assert_eq!(read_identity_record(&host, &path), Some(recorded.clone()));
        let validation = terminate_validated_process_group(
            &host,
            &recorded,
            Some(&PathBuf::from("/tmp/kill.jsonl")),
            "test",
            "unit",
        );
        assert!(validation.ok);
        assert!(!host.signals.borrow().is_empty());
    }

    #[test]
    fn validation_covers_pgid_and_expected_command_mismatches() {
        let mut host = FakeHost::default();
        host.pgid.insert(8, 9);
        host.ps.borrow_mut().insert(
            8,
            vec![IdentityProbeOutput::Stdout(
                "Fri Jul  3 17:01:02 2026 matching command\n".to_owned(),
            )],
        );
        let recorded = RecordedProcessIdentity {
            pid: 8,
            pgid: 8,
            start_time: "Fri Jul 3 17:01:02 2026".to_owned(),
            command_signature: "matching command".to_owned(),
            expected_signature: "matching".to_owned(),
        };
        assert_eq!(
            validate_process_identity(&host, &recorded).reason,
            "pgid-mismatch"
        );

        host.pgid.insert(8, 8);
        host.ps.borrow_mut().insert(
            8,
            vec![IdentityProbeOutput::Stdout(
                "Fri Jul  3 17:01:02 2026 matching command\n".to_owned(),
            )],
        );
        let mut expected_bad = recorded;
        expected_bad.expected_signature = "missing-token".to_owned();
        assert_eq!(
            validate_process_identity(&host, &expected_bad).reason,
            "expected-command-mismatch"
        );

        append_kill_log(
            &host,
            None,
            &KillLogEvent {
                event: "signal".to_owned(),
                signal: "SIGTERM".to_owned(),
                pid: 1,
                pgid: 1,
                command: "x".to_owned(),
                caller: "t".to_owned(),
                reason: "t".to_owned(),
                descendants: Vec::new(),
                tmpdir_needle: String::new(),
                physical_needle: String::new(),
            },
        );
    }

    #[test]
    fn terminate_covers_missing_leader_with_validated_members() {
        let mut host = FakeHost::default();
        host.pgid.insert(8, 8);
        host.pgid.insert(80, 8);
        host.groups.insert(8, vec![80]);
        let recorded = RecordedProcessIdentity {
            pid: 8,
            pgid: 8,
            start_time: "Fri Jul 3 17:01:02 2026".to_owned(),
            command_signature: "matching command".to_owned(),
            expected_signature: "matching".to_owned(),
        };
        host.ps
            .borrow_mut()
            .insert(8, vec![IdentityProbeOutput::Missing]);
        host.ps.borrow_mut().insert(
            80,
            vec![
                IdentityProbeOutput::Stdout(
                    "Fri Jul  3 17:01:02 2026 matching command\n".to_owned(),
                ),
                IdentityProbeOutput::Missing,
            ],
        );
        let validation = terminate_validated_process_group(
            &host,
            &recorded,
            Some(Path::new("/tmp/missing-leader.jsonl")),
            "test",
            "missing-leader",
        );
        assert!(validation.ok);
    }

    #[test]
    fn await_and_helpers_cover_grace_and_invalid_inputs() {
        let mut host = FakeHost::default();
        host.pgid.insert(8, 8);
        let recorded = RecordedProcessIdentity {
            pid: 8,
            pgid: 8,
            start_time: "Fri Jul 3 17:01:02 2026".to_owned(),
            command_signature: "matching command".to_owned(),
            expected_signature: "matching".to_owned(),
        };
        host.ps.borrow_mut().insert(
            8,
            vec![
                IdentityProbeOutput::Missing,
                IdentityProbeOutput::Stdout(
                    "Fri Jul  3 17:01:02 2026 matching command\n".to_owned(),
                ),
            ],
        );
        assert!(read_stable_process_identity(&host, 8, "matching", true).is_some());

        host.now.store(0, Ordering::Relaxed);
        host.ps.borrow_mut().insert(
            8,
            (0..20)
                .map(|_| IdentityProbeOutput::Missing)
                .collect::<Vec<_>>(),
        );
        assert_eq!(
            await_loop_poll(
                &host,
                &recorded,
                Path::new("/tmp/await-grace"),
                0,
                Duration::from_secs(10),
                false,
            ),
            0
        );

        host.files.borrow_mut().insert(
            PathBuf::from("/tmp/await-grace/.step3-review-result.env"),
            "STEP3_REVIEW_LOOP_STATUS=\n".to_owned(),
        );
        host.mtimes.borrow_mut().insert(
            PathBuf::from("/tmp/await-grace/.step3-review-result.env"),
            10,
        );
        assert!(!result_env_has_step3_status(
            &host,
            Path::new("/tmp/await-grace"),
            1
        ));

        assert_eq!(write_loop_identity(&host, "", "1", "x"), 0);
        assert_eq!(write_loop_identity(&host, "/tmp/x", "nope", "x"), 0);
        assert_eq!(teardown_loop_identity(&host, "", "1"), 0);
        assert_eq!(teardown_loop_identity(&host, "/tmp/x", "nope"), 0);
        assert_eq!(write_step5_loop_identity(&host, "", "1", "x"), 0);
        assert_eq!(write_step5_loop_identity(&host, "/tmp/x", "nope", "x"), 0);
    }
}
