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
/// Maximum time spent proving a signaled process group is gone.
pub const TERMINATE_CONFIRM_TIMEOUT: Duration = Duration::from_secs(5);
/// Delay between process-group absence probes after signaling.
pub const TERMINATE_CONFIRM_POLL: Duration = Duration::from_millis(50);

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
    /// Kernel-supplied process birth identity. Records written before this
    /// field existed deliberately fail closed rather than authorizing a
    /// signal from only a second-resolution `ps` timestamp.
    #[serde(default)]
    pub birth_identity: Option<ProcessBirthIdentity>,
    pub command_signature: String,
    #[serde(default)]
    pub expected_signature: String,
}

/// Strong, kernel-derived process birth identity that survives `exec`.
///
/// The representation is intentionally platform-specific. Darwin exposes a
/// microsecond creation timestamp through `proc_pidinfo`; Linux combines the
/// boot UUID with the process's `/proc/<pid>/stat` start tick. Neither value
/// changes when a process replaces its image with `exec`.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(tag = "platform", rename_all = "kebab-case")]
pub enum ProcessBirthIdentity {
    /// Darwin `proc_bsdinfo` creation timestamp.
    Darwin {
        /// Seconds since the Unix epoch.
        seconds: u64,
        /// Microseconds within `seconds`.
        microseconds: u64,
    },
    /// Linux boot UUID plus `/proc/<pid>/stat` field 22.
    Linux {
        /// UUID for the current kernel boot.
        boot_id: String,
        /// Process start clock ticks since boot.
        start_ticks: u64,
    },
}

impl ProcessBirthIdentity {
    /// Render the single-line durable registry representation.
    #[must_use]
    pub fn wire_value(&self) -> String {
        match self {
            Self::Darwin {
                seconds,
                microseconds,
            } => format!("darwin:{seconds}:{microseconds}"),
            Self::Linux {
                boot_id,
                start_ticks,
            } => format!("linux:{boot_id}:{start_ticks}"),
        }
    }

    /// Parse a durable registry representation.
    #[must_use]
    pub fn parse_wire_value(value: &str) -> Option<Self> {
        let mut parts = value.split(':');
        let platform = parts.next()?;
        let first = parts.next()?;
        let second = parts.next()?;
        if parts.next().is_some() {
            return None;
        }
        let identity = match platform {
            "darwin" => Self::Darwin {
                seconds: first.parse().ok()?,
                microseconds: second.parse().ok()?,
            },
            "linux" if is_linux_boot_id(first) => Self::Linux {
                boot_id: first.to_owned(),
                start_ticks: second.parse().ok()?,
            },
            _ => return None,
        };
        identity.is_valid().then_some(identity)
    }

    /// Return whether this value is structurally safe to persist or compare.
    #[must_use]
    pub fn is_valid(&self) -> bool {
        match self {
            Self::Darwin { microseconds, .. } => *microseconds < 1_000_000,
            Self::Linux { boot_id, .. } => is_linux_boot_id(boot_id),
        }
    }
}

fn is_linux_boot_id(value: &str) -> bool {
    value.len() == 36
        && value.chars().enumerate().all(|(index, character)| {
            if matches!(index, 8 | 13 | 18 | 23) {
                character == '-'
            } else {
                character.is_ascii_hexdigit()
            }
        })
}

/// Outcome of comparing a recorded identity against the live process.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ValidationResult {
    pub ok: bool,
    pub reason: String,
    pub current: Option<RecordedProcessIdentity>,
}

/// Outcome of terminating a persisted process group and proving it is absent.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TerminationResult {
    /// Whether the recorded group is proven absent after cleanup.
    pub terminated: bool,
    /// Stable success or failure reason.
    pub reason: String,
    /// The last identity validation performed while cleaning up.
    pub validation: ValidationResult,
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

/// Command-signature policy for a persisted process identity.
///
/// A freshly captured wrapper normally retains an exact command signature. A
/// child that deliberately `exec`s keeps its PID, process group, start time,
/// and kernel birth identity but necessarily changes that command text; its
/// owning runtime may opt into the latter policy without relaxing the
/// PID-reuse checks.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProcessIdentityValidationPolicy {
    /// Require the exact captured command and expected command substring.
    ExactCommand,
    /// Permit an in-place command transition while retaining PID, PGID, and
    /// start-time validation.
    AllowCommandTransition,
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

/// Outcome of a kernel process-birth-identity probe.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ProcessBirthIdentityProbeOutput {
    /// A validated kernel identity for the current process incarnation.
    Identity(ProcessBirthIdentity),
    /// The process is gone.
    Missing,
    /// The current platform has no supported kernel identity source.
    Unsupported,
    /// The host could not safely capture the identity.
    Error,
}

/// Injectable host surface for process identity and signaling.
pub trait ProcessIdentityHost {
    /// Return the process group id for `pid`, or `None` when the pid is gone.
    fn get_pgid(&self, pid: i32) -> Option<i32>;
    /// Run `ps -p <pid> -o lstart= -o command=` and classify the outcome.
    fn probe_ps_identity(&self, pid: i32) -> IdentityProbeOutput;
    /// Capture a kernel process-birth identity for `pid`.
    ///
    /// The default deliberately fails closed for test hosts and unsupported
    /// platforms. Production hosts must implement a supported source before
    /// persisted process identities can be captured or signaled.
    fn probe_process_birth_identity(&self, _pid: i32) -> ProcessBirthIdentityProbeOutput {
        ProcessBirthIdentityProbeOutput::Unsupported
    }
    /// Return whether `pid` is an exited, unreaped process that cannot execute or own live work.
    fn process_is_zombie(&self, _pid: i32) -> bool {
        false
    }
    /// Enumerate direct children of `pid` via `pgrep -P`.
    fn pgrep_children(&self, pid: i32) -> Vec<i32>;
    /// Enumerate members of process group `pgid` via `pgrep -g`.
    fn pgrep_group(&self, pgid: i32) -> Vec<i32>;
    /// Enumerate members of process group `pgid`, returning `None` when the
    /// probe itself could not establish the answer.
    ///
    /// The default keeps existing in-memory hosts simple. Production hosts
    /// override it so a cleanup path never treats a failed `pgrep` call as
    /// proof that a process group is absent.
    fn pgrep_group_checked(&self, pgid: i32) -> Option<Vec<i32>> {
        Some(self.pgrep_group(pgid))
    }
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
            birth_identity: None,
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
    if host.process_is_zombie(process_id) {
        return ProcessIdentityProbeResult {
            identity: None,
            failure_reason,
        };
    }
    // Read the kernel identity before looking up `ps`. If the PID is reused
    // while the weaker text fields are being collected, the closing birth
    // probe below makes that mixed snapshot fail instead of persisting the
    // new process's birth identity alongside the old process's `ps` data.
    let first_birth_identity = match read_birth_identity(host, process_id) {
        Ok(identity) => identity,
        Err(reason) => {
            return ProcessIdentityProbeResult {
                identity: None,
                failure_reason: reason.to_owned(),
            };
        }
    };
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
            // A Linux zombie retains its PID and PGID until reaped but cannot
            // own work or safely match an exact command signature.
            if host.process_is_zombie(process_id) {
                return ProcessIdentityProbeResult {
                    identity: None,
                    failure_reason: "missing-pid".to_owned(),
                };
            }
            if let Some(mut identity) =
                parse_ps_identity(process_id, process_group_id, &stdout, expected_signature)
            {
                let Some(final_process_group_id) = host.get_pgid(process_id) else {
                    return ProcessIdentityProbeResult {
                        identity: None,
                        failure_reason: "missing-pid".to_owned(),
                    };
                };
                if final_process_group_id != process_group_id {
                    return ProcessIdentityProbeResult {
                        identity: None,
                        failure_reason: "pgid-changed-during-identity-probe".to_owned(),
                    };
                }
                let final_birth_identity = match read_birth_identity(host, process_id) {
                    Ok(identity) => identity,
                    Err(reason) => {
                        return ProcessIdentityProbeResult {
                            identity: None,
                            failure_reason: reason.to_owned(),
                        };
                    }
                };
                if first_birth_identity != final_birth_identity {
                    return ProcessIdentityProbeResult {
                        identity: None,
                        failure_reason: "process-birth-identity-unstable".to_owned(),
                    };
                }
                identity.birth_identity = Some(first_birth_identity);
                return ProcessIdentityProbeResult {
                    identity: Some(identity),
                    failure_reason: String::new(),
                };
            }
            // A successful `ps` invocation that does not conform to its
            // allowlisted format is not proof that the PID disappeared.
            // Keep recovery and cleanup fail-closed instead of treating an
            // unreadable live process as safely absent.
            failure_reason = String::from("identity-probe-error");
        }
    }
    ProcessIdentityProbeResult {
        identity: None,
        failure_reason,
    }
}

fn read_birth_identity(
    host: &dyn ProcessIdentityHost,
    process_id: i32,
) -> Result<ProcessBirthIdentity, &'static str> {
    match host.probe_process_birth_identity(process_id) {
        ProcessBirthIdentityProbeOutput::Identity(identity) if identity.is_valid() => Ok(identity),
        ProcessBirthIdentityProbeOutput::Identity(_) | ProcessBirthIdentityProbeOutput::Error => {
            Err("process-birth-identity-probe-error")
        }
        ProcessBirthIdentityProbeOutput::Missing => Err("missing-pid"),
        ProcessBirthIdentityProbeOutput::Unsupported => Err("process-birth-identity-unsupported"),
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
    validate_process_identity_with_policy(
        host,
        recorded,
        ProcessIdentityValidationPolicy::ExactCommand,
    )
}

/// Validate a recorded identity with an explicit command-transition policy.
#[must_use]
pub fn validate_process_identity_with_policy(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
    policy: ProcessIdentityValidationPolicy,
) -> ValidationResult {
    validate_recorded_identity(host, recorded, policy, BirthIdentityPolicy::Required)
}

/// Validate a recorded identity published before birth identity was captured.
///
/// A record that carries a birth identity is held to it exactly as
/// [`validate_process_identity`] does. One that does not is validated on pid,
/// pgid, start time, and command signature alone, because refusing it outright
/// would strand the process group its publisher asked us to clean up. Only a
/// writer whose wire format predates the field may use this; the last such
/// publisher is the Python commit-route leg runner, retired by #8611.
#[must_use]
pub fn validate_process_identity_allowing_absent_birth(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
) -> ValidationResult {
    validate_recorded_identity(
        host,
        recorded,
        ProcessIdentityValidationPolicy::ExactCommand,
        BirthIdentityPolicy::EnforcedWhenRecorded,
    )
}

/// Whether a record must carry a kernel process-birth identity to validate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum BirthIdentityPolicy {
    Required,
    EnforcedWhenRecorded,
}

fn validate_recorded_identity(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
    policy: ProcessIdentityValidationPolicy,
    birth_policy: BirthIdentityPolicy,
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
    let Some(recorded_birth_identity) = recorded.birth_identity.as_ref() else {
        if birth_policy == BirthIdentityPolicy::EnforcedWhenRecorded {
            return validate_recorded_command(recorded, current, policy);
        }
        return ValidationResult {
            ok: false,
            reason: "missing-process-birth-identity".to_owned(),
            current: Some(current),
        };
    };
    if !recorded_birth_identity.is_valid() {
        return ValidationResult {
            ok: false,
            reason: "invalid-process-birth-identity".to_owned(),
            current: Some(current),
        };
    }
    if current.birth_identity.as_ref() != Some(recorded_birth_identity) {
        return ValidationResult {
            ok: false,
            reason: "process-birth-identity-mismatch".to_owned(),
            current: Some(current),
        };
    }
    validate_recorded_command(recorded, current, policy)
}

/// Compare the command text of a process already proven to be the recorded one.
fn validate_recorded_command(
    recorded: &RecordedProcessIdentity,
    current: RecordedProcessIdentity,
    policy: ProcessIdentityValidationPolicy,
) -> ValidationResult {
    if policy == ProcessIdentityValidationPolicy::ExactCommand {
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
        if !host.process_is_zombie(member) && seen.insert(member) {
            members.push(member);
        }
    }
    members
}

/// Collect group members while preserving a failed probe as a fail-closed result.
#[must_use]
pub fn collect_process_group_members_checked(
    host: &dyn ProcessIdentityHost,
    pgid: i32,
) -> Option<Vec<i32>> {
    let mut members = Vec::new();
    let mut seen = BTreeSet::new();
    for member in host.pgrep_group_checked(pgid)? {
        if !host.process_is_zombie(member) && seen.insert(member) {
            members.push(member);
        }
    }
    Some(members)
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

/// Record one intended signal against a target snapshot before it is sent.
pub fn log_signal(
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

struct SignalRequest<'a> {
    log_path: Option<&'a Path>,
    recorded: &'a RecordedProcessIdentity,
    descendants: &'a [i32],
    command: &'a str,
    signal: TerminateSignal,
    caller: &'a str,
    reason: &'a str,
}

fn signal_group_and_descendants(
    host: &dyn ProcessIdentityHost,
    request: &SignalRequest<'_>,
    policy: ProcessIdentityValidationPolicy,
) -> ValidationResult {
    let initial = validate_process_identity_with_policy(host, request.recorded, policy);
    if !initial.ok {
        return initial;
    }
    let snapshot = KillTargetSnapshot {
        pid: request.recorded.pid,
        pgid: request.recorded.pgid,
        descendants: request.descendants.to_vec(),
        command: initial
            .current
            .as_ref()
            .map_or(request.command, |current| {
                current.command_signature.as_str()
            })
            .to_owned(),
    };
    log_signal(
        host,
        request.log_path,
        request.signal,
        &snapshot,
        request.caller,
        request.reason,
    );
    // The log records intent before the external effect. Revalidate after
    // that write so the actual signal follows the strongest available kernel
    // identity check as closely as the platform's separate validation and
    // `killpg` APIs permit.
    let validation = validate_process_identity_with_policy(host, request.recorded, policy);
    if !validation.ok {
        return validation;
    }
    host.signal_group(request.recorded.pgid, request.signal);
    // Group signaling reaches descendants that remain in the owned group.
    // Do not separately signal a stale descendant PID: its identity was not
    // persisted and it could now name an unrelated process.
    validation
}

/// Capture live non-leader group members before a graceful group signal.
///
/// A valid member is a short-lived escalation anchor only: it binds the
/// numeric process group after the validated leader exits in response to TERM.
/// It is never used after the terminating call returns, and it is revalidated
/// immediately before the KILL signal.
fn capture_group_escalation_anchors(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
) -> Vec<RecordedProcessIdentity> {
    collect_process_group_members_checked(host, recorded.pgid)
        .unwrap_or_default()
        .into_iter()
        .filter(|pid| *pid != recorded.pid)
        .filter_map(|pid| read_process_identity(host, pid, ""))
        .filter(|identity| identity.pgid == recorded.pgid)
        .collect()
}

/// Revalidate a pre-TERM group member before escalating a now-leaderless
/// group. A member with the same stable birth identity proves that the PGID
/// still belongs to the group we just signalled, so the KILL cannot target a
/// recycled numeric group.
fn signal_group_from_escalation_anchor(
    host: &dyn ProcessIdentityHost,
    anchors: &[RecordedProcessIdentity],
    log_path: Option<&Path>,
    caller: &str,
    reason: &str,
) -> Option<ValidationResult> {
    for anchor in anchors {
        let initial = validate_process_identity_with_policy(
            host,
            anchor,
            ProcessIdentityValidationPolicy::AllowCommandTransition,
        );
        if !initial.ok {
            continue;
        }
        let snapshot = KillTargetSnapshot {
            pid: anchor.pid,
            pgid: anchor.pgid,
            descendants: Vec::new(),
            command: initial.current.as_ref().map_or_else(
                || anchor.command_signature.clone(),
                |current| current.command_signature.clone(),
            ),
        };
        log_signal(
            host,
            log_path,
            TerminateSignal::Kill,
            &snapshot,
            caller,
            reason,
        );
        // The log is intentionally before the external effect. A second
        // validation closes the same logging-to-signal window as the normal
        // leader path and keeps PID-reuse protection intact.
        let validation = validate_process_identity_with_policy(
            host,
            anchor,
            ProcessIdentityValidationPolicy::AllowCommandTransition,
        );
        if !validation.ok {
            continue;
        }
        host.signal_group(anchor.pgid, TerminateSignal::Kill);
        return Some(validation);
    }
    None
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
    terminate_validated_process_group_with_policy(
        host,
        recorded,
        ProcessIdentityValidationPolicy::ExactCommand,
        log_path,
        caller,
        reason,
    )
}

/// Terminate a process group after validation under `policy`.
///
/// This records every intended signal before it is sent. Call
/// [`terminate_validated_process_group_and_confirm`] when a caller must not
/// release durable ownership until the group is proven absent.
#[must_use]
pub fn terminate_validated_process_group_with_policy(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
    policy: ProcessIdentityValidationPolicy,
    log_path: Option<&Path>,
    caller: &str,
    reason: &str,
) -> ValidationResult {
    let validation = validate_process_identity_with_policy(host, recorded, policy);
    if !validation.ok && validation.reason != "missing-pid" {
        return validation;
    }
    if !validation.ok {
        // Once the persisted group leader is gone, a recycled numeric PGID
        // cannot be tied safely to this record. Retain the durable state and
        // let the caller prove absence; never signal an unrelated group.
        return validation;
    }
    // Preserve an independently validated member before TERM. A TERM may
    // correctly make the group leader disappear while a descendant that
    // ignored TERM remains. The anchor lets the KILL escalation prove that
    // the numeric PGID still names this exact group instead of stranding it.
    let escalation_anchors = capture_group_escalation_anchors(host, recorded);
    let descendants = collect_descendants(host, recorded.pid);
    let current = validation.current.unwrap_or_else(|| recorded.clone());
    let validation = signal_group_and_descendants(
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
        policy,
    );
    if !validation.ok {
        // The leader can exit in the narrow log-to-signal revalidation
        // window. The pre-captured member still ties this numeric group to
        // the just-validated leader, so use the same two-validation anchor
        // path rather than leaving a live descendant group unowned.
        if validation.reason == "missing-pid"
            && let Some(validation) = signal_group_from_escalation_anchor(
                host,
                &escalation_anchors,
                log_path,
                caller,
                reason,
            )
        {
            return validation;
        }
        return validation;
    }
    host.sleep(TERMINATE_ESCALATION_SLEEP);
    let leader = validate_process_identity_with_policy(host, recorded, policy);
    if !leader.ok {
        if leader.reason == "missing-pid"
            && let Some(validation) = signal_group_from_escalation_anchor(
                host,
                &escalation_anchors,
                log_path,
                caller,
                reason,
            )
        {
            return validation;
        }
        // A group whose leader disappeared without a still-validated member
        // remains durable and retryable rather than being signalled by a bare
        // potentially recycled PGID.
        return leader;
    }
    let kill_descendants = collect_descendants(host, recorded.pid);
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
        policy,
    )
}

/// Terminate a process group and prove that no member remains.
///
/// A failed identity or process-group probe is not absence. The caller keeps
/// its durable recovery record in that case so a later owner can retry without
/// falsely publishing a terminal success envelope.
#[must_use]
pub fn terminate_validated_process_group_and_confirm(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
    policy: ProcessIdentityValidationPolicy,
    log_path: Option<&Path>,
    caller: &str,
    reason: &str,
) -> TerminationResult {
    let initial = terminate_validated_process_group_with_policy(
        host, recorded, policy, log_path, caller, reason,
    );
    if !initial.ok && initial.reason != "missing-pid" {
        return TerminationResult {
            terminated: false,
            reason: initial.reason.clone(),
            validation: initial,
        };
    }

    confirm_process_group_absent(host, recorded, policy)
}

/// Prove that a persisted process group has no remaining member.
///
/// This is separate from signaling so a direct child owner can reap its child
/// before checking for a zombie process-group leader.
#[must_use]
pub fn confirm_process_group_absent(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
    policy: ProcessIdentityValidationPolicy,
) -> TerminationResult {
    let deadline = host
        .monotonic_now()
        .saturating_add(TERMINATE_CONFIRM_TIMEOUT);
    let mut last = validate_process_identity_with_policy(host, recorded, policy);
    loop {
        if last.ok {
            // The PID still names the validated process, so absence has not
            // yet been proven.
        } else if last.reason == "missing-pid" {
            match collect_process_group_members_checked(host, recorded.pgid) {
                None => {
                    return TerminationResult {
                        terminated: false,
                        reason: "process-group-probe-error".to_owned(),
                        validation: last,
                    };
                }
                Some(members) if members.is_empty() => {
                    return TerminationResult {
                        terminated: true,
                        reason: "terminated".to_owned(),
                        validation: last,
                    };
                }
                Some(_) => {}
            }
        } else {
            return TerminationResult {
                terminated: false,
                reason: last.reason.clone(),
                validation: last,
            };
        }

        if host.monotonic_now() >= deadline {
            return TerminationResult {
                terminated: false,
                reason: "process-group-still-live".to_owned(),
                validation: last,
            };
        }
        host.sleep(TERMINATE_CONFIRM_POLL);
        last = validate_process_identity_with_policy(host, recorded, policy);
    }
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
    if let Some(birth_identity) = recorded.birth_identity.as_ref() {
        payload.insert(
            "birth_identity".to_owned(),
            serde_json::to_value(birth_identity).unwrap_or(Value::Null),
        );
    }
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
        birth_identity: object
            .get("birth_identity")
            .and_then(|value| serde_json::from_value::<ProcessBirthIdentity>(value.clone()).ok())
            .filter(ProcessBirthIdentity::is_valid),
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
    let termination = terminate_validated_process_group_and_confirm(
        host,
        &recorded,
        ProcessIdentityValidationPolicy::ExactCommand,
        Some(&tmpdir.join(DESIGN_STEP3_KILL_LOG_FILE)),
        "design-step3-review",
        "step3-trap-cleanup",
    );
    if termination.terminated {
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
        collections::{HashMap, HashSet},
        sync::atomic::{AtomicU64, Ordering},
    };

    #[derive(Default)]
    struct FakeHost {
        pgid: HashMap<i32, i32>,
        ps: RefCell<HashMap<i32, Vec<IdentityProbeOutput>>>,
        birth: RefCell<HashMap<i32, Vec<ProcessBirthIdentityProbeOutput>>>,
        ps_birth_after: RefCell<HashMap<i32, Vec<ProcessBirthIdentityProbeOutput>>>,
        birth_after_log: RefCell<Option<(i32, Vec<ProcessBirthIdentityProbeOutput>)>>,
        zombies: HashSet<i32>,
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

    fn fake_birth_identity(pid: i32) -> ProcessBirthIdentity {
        ProcessBirthIdentity::Darwin {
            seconds: 1,
            microseconds: u64::try_from(pid).unwrap_or_default(),
        }
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
            let result = queue.remove(0);
            if let Some(replacement) = self.ps_birth_after.borrow_mut().remove(&pid) {
                self.birth.borrow_mut().insert(pid, replacement);
            }
            result
        }
        fn probe_process_birth_identity(&self, pid: i32) -> ProcessBirthIdentityProbeOutput {
            let mut birth = self.birth.borrow_mut();
            if let Some(queue) = birth.get_mut(&pid)
                && !queue.is_empty()
            {
                return queue.remove(0);
            }
            self.pgid
                .get(&pid)
                .map_or(ProcessBirthIdentityProbeOutput::Missing, |_| {
                    ProcessBirthIdentityProbeOutput::Identity(fake_birth_identity(pid))
                })
        }
        fn process_is_zombie(&self, pid: i32) -> bool {
            self.zombies.contains(&pid)
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
            if let Some((pid, replacement)) = self.birth_after_log.borrow_mut().take() {
                self.birth.borrow_mut().insert(pid, replacement);
            }
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
            birth_identity: Some(fake_birth_identity(123)),
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
    fn zombie_identity_is_missing_and_not_a_live_group_member() {
        let mut host = FakeHost::default();
        host.pgid.insert(123, 123);
        host.groups.insert(123, vec![123]);
        host.zombies.insert(123);

        assert_eq!(
            validate_process_identity(&host, &recorded()).reason,
            "missing-pid"
        );
        assert!(collect_process_group_members(&host, 123).is_empty());
        assert!(
            confirm_process_group_absent(
                &host,
                &recorded(),
                ProcessIdentityValidationPolicy::ExactCommand,
            )
            .terminated
        );
    }

    #[test]
    fn exec_policy_requires_a_matching_birth_identity() {
        let mut host = FakeHost::default();
        host.pgid.insert(123, 123);
        host.ps.borrow_mut().insert(
            123,
            vec![
                ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run"),
                ps_stdout("child after exec"),
                ps_stdout("unrelated recycled command"),
                ps_stdout("unrelated recycled command"),
                ps_stdout("unrelated recycled command"),
            ],
        );
        let recorded = recorded();
        assert_eq!(validate_process_identity(&host, &recorded).reason, "ok");
        assert!(
            validate_process_identity_with_policy(
                &host,
                &recorded,
                ProcessIdentityValidationPolicy::AllowCommandTransition,
            )
            .ok
        );

        // All of these fields deliberately collide with the recorded row,
        // including the second-resolution `lstart` value. Only the kernel
        // birth identity distinguishes an unrelated PID reuse.
        host.birth.borrow_mut().insert(
            123,
            vec![
                ProcessBirthIdentityProbeOutput::Identity(ProcessBirthIdentity::Darwin {
                    seconds: 2,
                    microseconds: 123,
                }),
                ProcessBirthIdentityProbeOutput::Identity(ProcessBirthIdentity::Darwin {
                    seconds: 2,
                    microseconds: 123,
                }),
            ],
        );
        assert_eq!(
            validate_process_identity_with_policy(
                &host,
                &recorded,
                ProcessIdentityValidationPolicy::AllowCommandTransition,
            )
            .reason,
            "process-birth-identity-mismatch"
        );

        let mut stale = recorded.clone();
        stale.start_time = "Fri Jul 3 17:01:01 2026".to_owned();
        assert_eq!(
            validate_process_identity_with_policy(
                &host,
                &stale,
                ProcessIdentityValidationPolicy::AllowCommandTransition,
            )
            .reason,
            "start-time-mismatch"
        );

        host.pgid.insert(123, 456);
        assert_eq!(
            validate_process_identity_with_policy(
                &host,
                &recorded,
                ProcessIdentityValidationPolicy::AllowCommandTransition,
            )
            .reason,
            "pgid-mismatch"
        );

        host.pgid.insert(123, 123);
        host.ps
            .borrow_mut()
            .insert(123, vec![ps_stdout("unrelated recycled command")]);
        host.birth.borrow_mut().insert(
            123,
            vec![
                ProcessBirthIdentityProbeOutput::Identity(ProcessBirthIdentity::Darwin {
                    seconds: 2,
                    microseconds: 123,
                }),
                ProcessBirthIdentityProbeOutput::Identity(ProcessBirthIdentity::Darwin {
                    seconds: 2,
                    microseconds: 123,
                }),
            ],
        );
        let result = terminate_validated_process_group_with_policy(
            &host,
            &recorded,
            ProcessIdentityValidationPolicy::AllowCommandTransition,
            None,
            "test",
            "same-second-pid-reuse",
        );
        assert_eq!(result.reason, "process-birth-identity-mismatch");
        assert!(
            host.signals.borrow().is_empty(),
            "a same-second PID and PGID collision must receive no signal"
        );
    }

    #[test]
    fn capture_rejects_pid_reuse_while_ps_snapshot_is_collected() {
        let mut host = FakeHost::default();
        host.pgid.insert(123, 123);
        host.ps
            .borrow_mut()
            .insert(123, vec![ps_stdout("wrapper before reuse")]);
        let recycled = ProcessBirthIdentityProbeOutput::Identity(ProcessBirthIdentity::Darwin {
            seconds: 2,
            microseconds: 123,
        });
        // The old capture order read `ps` first, so both subsequent birth
        // probes would have seen the recycled process and accepted a mixed
        // snapshot. The initial birth probe must bracket `ps` instead.
        host.ps_birth_after
            .borrow_mut()
            .insert(123, vec![recycled.clone(), recycled]);

        let probe = probe_process_identity(&host, 123, "wrapper");
        assert!(probe.identity.is_none());
        assert_eq!(probe.failure_reason, "process-birth-identity-unstable");
    }

    #[test]
    fn legacy_identity_without_birth_proof_never_authorizes_an_exec_signal() {
        let mut host = FakeHost::default();
        host.pgid.insert(123, 123);
        host.ps.borrow_mut().insert(
            123,
            vec![ps_stdout("child after exec"), ps_stdout("child after exec")],
        );
        let mut legacy = recorded();
        legacy.birth_identity = None;
        assert_eq!(
            validate_process_identity_with_policy(
                &host,
                &legacy,
                ProcessIdentityValidationPolicy::AllowCommandTransition,
            )
            .reason,
            "missing-process-birth-identity"
        );
        let result = terminate_validated_process_group_with_policy(
            &host,
            &legacy,
            ProcessIdentityValidationPolicy::AllowCommandTransition,
            Some(Path::new("/tmp/legacy-identity.jsonl")),
            "test",
            "legacy",
        );
        assert_eq!(result.reason, "missing-process-birth-identity");
        assert!(host.signals.borrow().is_empty());
    }

    #[test]
    fn pid_reuse_after_log_does_not_signal_a_mismatched_process() {
        let mut host = FakeHost::default();
        host.pgid.insert(123, 123);
        // The first two validations match the recorded identity. The target
        // is then replaced after intent is logged but before the kernel group
        // signal. A revalidation must prevent that signal entirely.
        host.ps.borrow_mut().insert(
            123,
            vec![
                ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run"),
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
        assert!(signals.is_empty());
        assert!(
            host.files
                .borrow()
                .get(Path::new("/tmp/kill.jsonl"))
                .is_some_and(|text| text.contains("\"signal\":\"SIGTERM\"")),
            "the durable log still records the intended, but rejected, signal"
        );
    }

    #[test]
    fn exec_policy_revalidates_birth_identity_after_logging_intent() {
        let mut host = FakeHost::default();
        host.pgid.insert(123, 123);
        host.ps.borrow_mut().insert(
            123,
            vec![
                ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run"),
                ps_stdout("child after exec"),
                ps_stdout("unrelated recycled command"),
            ],
        );
        host.children.insert(123, Vec::new());
        let recycled = ProcessBirthIdentityProbeOutput::Identity(ProcessBirthIdentity::Darwin {
            seconds: 2,
            microseconds: 123,
        });
        *host.birth_after_log.borrow_mut() = Some((123, vec![recycled.clone(), recycled]));

        let result = terminate_validated_process_group_with_policy(
            &host,
            &recorded(),
            ProcessIdentityValidationPolicy::AllowCommandTransition,
            Some(Path::new("/tmp/exec-after-log.jsonl")),
            "test",
            "same-second-pid-reuse",
        );
        assert_eq!(result.reason, "process-birth-identity-mismatch");
        assert!(
            host.signals.borrow().is_empty(),
            "an exec-capable row must not signal after its birth identity changes"
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
                ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run"),
                ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run"),
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
        assert_eq!(
            signals,
            vec![
                (123, TerminateSignal::Term, true),
                (123, TerminateSignal::Kill, true),
            ]
        );
    }

    #[test]
    fn escalation_uses_a_validated_member_when_term_removes_the_group_leader() {
        let mut host = FakeHost::default();
        host.pgid.extend([(123, 123), (10, 123)]);
        host.groups.insert(123, vec![123, 10]);
        host.children.insert(123, vec![10]);
        host.children.insert(10, Vec::new());
        // The leader validates for initial capture and TERM, then exits. The
        // previously captured member remains in the same group and is checked
        // again before KILL can use the numeric PGID.
        host.ps.borrow_mut().insert(
            123,
            vec![
                ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run"),
                ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run"),
                ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run"),
                IdentityProbeOutput::Missing,
            ],
        );
        host.ps.borrow_mut().insert(
            10,
            vec![
                ps_stdout("sleep 60"),
                ps_stdout("sleep 60"),
                ps_stdout("sleep 60"),
            ],
        );

        let result = terminate_validated_process_group(
            &host,
            &recorded(),
            Some(Path::new("/tmp/leaderless-escalation.jsonl")),
            "test",
            "leaderless",
        );
        assert!(result.ok, "{result:?}");
        assert_eq!(
            host.signals.borrow().as_slice(),
            &[
                (123, TerminateSignal::Term, true),
                (123, TerminateSignal::Kill, true),
            ]
        );
        let log = host
            .files
            .borrow()
            .get(Path::new("/tmp/leaderless-escalation.jsonl"))
            .cloned()
            .unwrap_or_default();
        assert!(log.contains("\"pid\":10"), "{log:?}");
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
                IdentityProbeOutput::Missing, // teardown confirms group absence
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
    fn teardown_loop_identity_retains_its_sidecar_until_the_group_is_absent() {
        let mut host = FakeHost::default();
        host.pgid.insert(123, 123);
        let matching = ps_stdout("/usr/bin/python3 /repo/python/cli.py plan-review run");
        host.ps.borrow_mut().insert(
            123,
            vec![
                matching.clone(), // write_loop_identity
                matching,         // teardown pre-signal validation
                IdentityProbeOutput::Missing,
            ],
        );
        host.groups.insert(123, vec![999]);
        let tmp = PathBuf::from("/tmp/design-loop-retain");
        assert_eq!(
            write_loop_identity(&host, tmp.to_str().unwrap(), "123", "plan-review run"),
            0
        );

        assert_eq!(
            teardown_loop_identity(&host, tmp.to_str().unwrap(), "123"),
            0
        );
        assert!(
            host.is_regular_file(&tmp.join(DESIGN_STEP3_LOOP_IDENTITY_FILE)),
            "an unproven group must retain the sidecar for a later safe recovery"
        );
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
        host.ps
            .borrow_mut()
            .insert(5, vec![IdentityProbeOutput::Stdout(String::new())]);
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
            birth_identity: Some(fake_birth_identity(7)),
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
            vec![
                matching.clone(),
                matching.clone(),
                matching.clone(),
                matching.clone(),
                matching.clone(),
                matching,
            ],
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
            birth_identity: Some(fake_birth_identity(50)),
            command_signature: "worker cmd".to_owned(),
            expected_signature: "worker".to_owned(),
        };
        let path = PathBuf::from("/tmp/identity-roundtrip.json");
        write_identity_record(&host, &path, &recorded, None).expect("write");
        assert_eq!(read_identity_record(&host, &path), Some(recorded.clone()));
        let persisted = host.files.borrow().get(&path).cloned().unwrap_or_default();
        assert!(persisted.contains("\"birth_identity\""));
        let mut legacy: Value = serde_json::from_str(&persisted).expect("identity JSON");
        legacy
            .as_object_mut()
            .expect("identity object")
            .remove("birth_identity");
        host.files.borrow_mut().insert(
            path.clone(),
            serde_json::to_string(&legacy).expect("legacy identity JSON"),
        );
        let legacy = read_identity_record(&host, &path).expect("legacy identity record");
        assert!(legacy.birth_identity.is_none());
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
            birth_identity: Some(fake_birth_identity(8)),
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
    fn missing_leader_never_signals_a_recycled_process_group() {
        let mut host = FakeHost::default();
        host.pgid.insert(8, 8);
        host.pgid.insert(80, 8);
        host.groups.insert(8, vec![80]);
        let recorded = RecordedProcessIdentity {
            pid: 8,
            pgid: 8,
            start_time: "Fri Jul 3 17:01:02 2026".to_owned(),
            birth_identity: Some(fake_birth_identity(8)),
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
        assert_eq!(validation.reason, "missing-pid");
        assert!(
            host.signals.borrow().is_empty(),
            "a missing leader must not authorize a signal to a recycled PGID"
        );
        let termination = terminate_validated_process_group_and_confirm(
            &host,
            &recorded,
            ProcessIdentityValidationPolicy::ExactCommand,
            None,
            "test",
            "missing-leader",
        );
        assert!(!termination.terminated);
        assert_eq!(termination.reason, "process-group-still-live");
    }

    #[test]
    fn await_and_helpers_cover_grace_and_invalid_inputs() {
        let mut host = FakeHost::default();
        host.pgid.insert(8, 8);
        let recorded = RecordedProcessIdentity {
            pid: 8,
            pgid: 8,
            start_time: "Fri Jul 3 17:01:02 2026".to_owned(),
            birth_identity: Some(fake_birth_identity(8)),
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
