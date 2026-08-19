//! Daemon-side owner validation, timing controls, and wire-row composition.
//!
//! Every decision the background-job daemon and its foreground wait make about
//! ownership, orphaning, and result content lives here so the process-owning
//! CLI layer keeps only signal, fork, and file-descriptor mechanics.

use std::{env, time::Duration};

use crate::{
    BGJOB_ELAPSED_KEY, BGJOB_RC_KEY, BgjobError, COMMAND_LOG_LIMIT, KvDocument, ParseOptions,
    ProcessIdentityHost, RecordedProcessIdentity, ValidationResult, bounded_command, redact,
    reject_line_value, validate_process_identity,
};

/// Stable waiting status token.
pub const BGJOB_STATUS_WAIT: &str = "WAIT";
/// Stable unrecoverable status token.
pub const BGJOB_STATUS_DEAD: &str = "DEAD";
/// Result code recorded when the runtime budget expires.
pub const BGJOB_RC_TIMEOUT: &str = "timeout";
/// Result code recorded when the session owner is gone.
pub const BGJOB_RC_ORPHANED: &str = "orphaned";
/// Default foreground wait chunk, in seconds.
///
/// Most skill steps use this short chunk under the Bash foreground timeout
/// ceiling. Longer callers must pass an explicit `--max-wait-s`.
pub const BGJOB_WAIT_DEFAULT_CHUNK_S: i64 = 270;
/// Maximum allowed wait chunk, in seconds (#8707).
///
/// Sized for `/complete-umbrella` leaf waits that run as background Bash so a
/// typical hour-scale leaf finishes in one or two wait calls. A continuous
/// wait refreshes the wait lease on every poll for the whole chunk.
pub const BGJOB_WAIT_MAX_CHUNK_S: i64 = 7200;
/// Extra seconds before a wait abandons its chunk unconditionally.
pub const BGJOB_WAIT_HARD_DEADLINE_GRACE_S: u64 = 30;
/// Seconds a startup marker keeps a wait patient before it reports `DEAD`.
pub const BGJOB_STARTUP_GRACE_S: i64 = 25;
/// Maximum foreground acknowledgement wait before coordinated startup recovery.
pub const BGJOB_STARTUP_ACK_TIMEOUT_S: f64 = 25.0;
/// Seconds an unvalidatable owner keeps its job alive before orphaning.
pub const BGJOB_OWNER_GRACE_S: f64 = 120.0;
/// Seconds a foreground-wait lease stays fresh after its last refresh (#8639).
///
/// Sized above the default wait chunk plus the owner grace so an orchestrator
/// can return `WAIT`, re-enter an identical `bgjob wait`, and still protect the
/// child when the start-time owner PID was an ephemeral tool shell. A single
/// long wait refreshes the lease on every poll, so the TTL only covers the
/// gap between chunk returns.
pub const BGJOB_WAIT_LEASE_TTL_S: f64 = 390.0;
/// Consecutive owner-validation failures required before the grace clock starts.
pub const BGJOB_OWNER_VALIDATION_FAILURE_THRESHOLD: u32 = 3;
/// Seconds between daemon monitor polls.
pub const BGJOB_DAEMON_POLL_INTERVAL_S: f64 = 1.0;
/// Minimum excess wall-clock advance that identifies a suspended daemon.
pub const BGJOB_SUSPEND_MIN_GAP_S: f64 = 30.0;
/// Trailing stderr bytes a dead-daemon report may quote.
pub const BGJOB_LOG_TAIL_BYTES: usize = 4096;
/// Test-only override for the owner grace window.
pub const ENV_TEST_BGJOB_OWNER_GRACE_S: &str = "LARCH_TEST_BGJOB_OWNER_GRACE_S";
/// Test-only override for the daemon poll interval.
pub const ENV_TEST_BGJOB_DAEMON_POLL_INTERVAL_S: &str = "LARCH_TEST_BGJOB_DAEMON_POLL_INTERVAL_S";
/// Test-only override for the bounded daemon-start acknowledgement wait.
pub const ENV_TEST_BGJOB_STARTUP_ACK_TIMEOUT_S: &str = "LARCH_TEST_BGJOB_STARTUP_ACK_TIMEOUT_S";
/// Explicit session-owner pid supplied by an orchestrator.
pub const ENV_BGJOB_OWNER_PID: &str = "LARCH_BGJOB_OWNER_PID";
/// Opt-in Darwin idle-sleep guard for a background job's requested command.
pub const ENV_BGJOB_CAFFEINATE: &str = "LARCH_BGJOB_CAFFEINATE";
/// Session-owner pid exported by the larch skill layer.
pub const ENV_LARCH_CLAUDE_PID: &str = "LARCH_CLAUDE_PID";
/// Session-owner pid exported by the Claude Code harness.
pub const ENV_CLAUDE_PID: &str = "CLAUDE_PID";
/// Result-env key naming the workflow step.
pub const BGJOB_STEP_KEY: &str = "STEP";
/// Startup-marker key naming the launch epoch.
pub const BGJOB_START_EPOCH_KEY: &str = "START_EPOCH";

const MIN_PACKED_ROW_TOKENS: usize = 2;

/// Consecutive owner-validation failures and when the grace clock started.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct OwnerValidationState {
    /// Monotonic instant at which the owner first stayed unvalidatable.
    pub missing_since: Option<Duration>,
    /// Consecutive validation failures observed so far.
    pub failure_count: u32,
}

/// One owner-validation poll: the next state and whether the job is orphaned.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OwnerValidationStep {
    /// State carried into the next poll.
    pub state: OwnerValidationState,
    /// Whether the owner stayed gone past the grace window.
    pub orphaned: bool,
    /// The failing validation, when one ran.
    pub validation: Option<ValidationResult>,
}

/// Clock samples and the one-shot owner grace granted after a suspend.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct WakeGraceState {
    last_monotonic: Duration,
    last_wall_s: f64,
    grace_until: Option<Duration>,
}

impl WakeGraceState {
    /// Capture the daemon's initial clock samples.
    #[must_use]
    pub fn new(host: &dyn ProcessIdentityHost) -> Self {
        Self {
            last_monotonic: host.monotonic_now(),
            last_wall_s: host.wall_time_secs(),
            grace_until: None,
        }
    }
}

/// One daemon clock poll and its wake-grace decision.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct WakeGraceStep {
    /// State carried into the next monitor poll.
    pub state: WakeGraceState,
    /// Current monotonic clock sample.
    pub monotonic_now: Duration,
    /// Current wall-clock sample.
    pub wall_time_s: f64,
    /// Whether this poll detected one new suspend gap.
    pub suspend_detected: bool,
    /// Whether orphaning must wait for a foreground waiter to refresh its lease.
    pub grace_active: bool,
}

/// Daemon monitor timing and owner-validation state.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct MonitorLivenessState {
    started: Duration,
    wake: WakeGraceState,
    owner: OwnerValidationState,
}

impl MonitorLivenessState {
    /// Capture the monitor's monotonic start and initial wake samples.
    #[must_use]
    pub fn new(host: &dyn ProcessIdentityHost) -> Self {
        Self {
            started: host.monotonic_now(),
            wake: WakeGraceState::new(host),
            owner: OwnerValidationState::default(),
        }
    }
}

/// One monitor poll after wake grace and owner validation are combined.
#[derive(Clone, Debug, PartialEq)]
pub struct MonitorLivenessStep {
    /// State carried into the next monitor poll.
    pub state: MonitorLivenessState,
    /// Suspend-pausing runtime elapsed since monitor start.
    pub elapsed: Duration,
    /// Current wall time for heartbeat and wait-lease TTL reads.
    pub wall_time_s: f64,
    /// Whether this poll detected one new suspend gap.
    pub suspend_detected: bool,
    /// Whether the owner is orphaned after wake grace is applied.
    pub orphaned: bool,
    /// Consecutive owner-validation failures observed so far.
    pub owner_failure_count: u32,
    /// The latest owner validation, when the job records an owner.
    pub validation: Option<ValidationResult>,
}

/// Detect a suspend and grant one wait-lease TTL of monotonic wake grace.
///
/// The state advances its wall sample when it detects a gap, so one observed
/// jump cannot renew the grace on later polls. A later, distinct suspend can.
#[must_use]
pub fn check_wake_grace(host: &dyn ProcessIdentityHost, state: WakeGraceState) -> WakeGraceStep {
    let monotonic_now = host.monotonic_now();
    let wall_time_s = host.wall_time_secs();
    let monotonic_delta_s = monotonic_now
        .saturating_sub(state.last_monotonic)
        .as_secs_f64();
    let wall_delta_s = wall_time_s - state.last_wall_s;
    let suspend_detected =
        wall_delta_s.is_finite() && wall_delta_s > monotonic_delta_s + BGJOB_SUSPEND_MIN_GAP_S;
    let mut grace_until = if suspend_detected {
        Some(monotonic_now.saturating_add(Duration::from_secs_f64(BGJOB_WAIT_LEASE_TTL_S)))
    } else {
        state.grace_until
    };
    let grace_active = grace_until.is_some_and(|deadline| monotonic_now < deadline);
    if !grace_active {
        grace_until = None;
    }
    WakeGraceStep {
        state: WakeGraceState {
            last_monotonic: monotonic_now,
            last_wall_s: wall_time_s,
            grace_until,
        },
        monotonic_now,
        wall_time_s,
        suspend_detected,
        grace_active,
    }
}

/// Advance daemon timing, wake grace, and owner validation by one poll.
#[must_use]
pub fn check_monitor_liveness(
    host: &dyn ProcessIdentityHost,
    owner: Option<&RecordedProcessIdentity>,
    mut state: MonitorLivenessState,
    owner_grace_s: f64,
) -> MonitorLivenessStep {
    let wake = check_wake_grace(host, state.wake);
    state.wake = wake.state;
    if wake.suspend_detected {
        state.owner = OwnerValidationState::default();
    }
    let elapsed = wake.monotonic_now.saturating_sub(state.started);
    let owner_step = check_owner_validation(host, owner, state.owner, elapsed, owner_grace_s);
    state.owner = owner_step.state;
    MonitorLivenessStep {
        state,
        elapsed,
        wall_time_s: wake.wall_time_s,
        suspend_detected: wake.suspend_detected,
        orphaned: owner_step.orphaned && !wake.grace_active,
        owner_failure_count: owner_step.state.failure_count,
        validation: owner_step.validation,
    }
}

/// Read a non-negative finite timing override, or fall back to `default`.
///
/// # Errors
///
/// Returns [`BgjobError::Invalid`] when the override is not a finite,
/// non-negative number of seconds.
pub fn timing_override_or_default(
    env_name: &str,
    default: f64,
    label: &str,
) -> Result<f64, BgjobError> {
    let raw = env::var(env_name).unwrap_or_default();
    parse_timing_override(&raw, env_name, default, label)
}

/// Parse one raw timing override, falling back to `default` when it is unset.
///
/// # Errors
///
/// Returns [`BgjobError::Invalid`] when `raw` is not a finite, non-negative
/// number of seconds.
pub fn parse_timing_override(
    raw: &str,
    env_name: &str,
    default: f64,
    label: &str,
) -> Result<f64, BgjobError> {
    if raw.is_empty() {
        return Ok(default);
    }
    let invalid = || BgjobError::Invalid(format!("invalid {label} override {env_name}={raw:?}"));
    let value = raw.parse::<f64>().map_err(|_| invalid())?;
    if !value.is_finite() || value < 0.0 {
        return Err(invalid());
    }
    Ok(value)
}

/// Return the seconds an unvalidatable owner keeps its job alive.
///
/// # Errors
///
/// Returns [`BgjobError::Invalid`] for a malformed override.
pub fn owner_grace_s() -> Result<f64, BgjobError> {
    timing_override_or_default(
        ENV_TEST_BGJOB_OWNER_GRACE_S,
        BGJOB_OWNER_GRACE_S,
        "bgjob owner grace",
    )
}

/// Return the seconds between daemon monitor polls.
///
/// # Errors
///
/// Returns [`BgjobError::Invalid`] for a malformed override.
pub fn daemon_poll_interval_s() -> Result<f64, BgjobError> {
    timing_override_or_default(
        ENV_TEST_BGJOB_DAEMON_POLL_INTERVAL_S,
        BGJOB_DAEMON_POLL_INTERVAL_S,
        "bgjob daemon poll interval",
    )
}

/// Return the bounded foreground acknowledgement wait for a daemon start.
///
/// # Errors
///
/// Returns an error for a malformed test override.
pub fn startup_ack_timeout_s() -> Result<f64, BgjobError> {
    timing_override_or_default(
        ENV_TEST_BGJOB_STARTUP_ACK_TIMEOUT_S,
        BGJOB_STARTUP_ACK_TIMEOUT_S,
        "bgjob startup acknowledgement timeout",
    )
}

/// Reject malformed timing overrides before a daemon detaches.
///
/// # Errors
///
/// Returns [`BgjobError::Invalid`] for a malformed override.
pub fn validate_timing_overrides() -> Result<(), BgjobError> {
    let _ = owner_grace_s()?;
    let _ = daemon_poll_interval_s()?;
    let _ = startup_ack_timeout_s()?;
    Ok(())
}

/// Resolve the session-owner pid from an explicit value or the session env.
#[must_use]
pub fn owner_pid_candidate(explicit: &str) -> Option<String> {
    [
        explicit.to_owned(),
        env::var(ENV_BGJOB_OWNER_PID).unwrap_or_default(),
        env::var(ENV_LARCH_CLAUDE_PID).unwrap_or_default(),
        env::var(ENV_CLAUDE_PID).unwrap_or_default(),
    ]
    .into_iter()
    .find(|value| !value.is_empty())
}

/// Advance the owner-validation state machine by one poll.
///
/// The recorded identity, not the bare pid, decides liveness, so a reused pid
/// never resurrects a dead owner (#6604).
#[must_use]
pub fn check_owner_validation(
    host: &dyn ProcessIdentityHost,
    owner: Option<&RecordedProcessIdentity>,
    state: OwnerValidationState,
    now: Duration,
    grace_s: f64,
) -> OwnerValidationStep {
    let Some(owner) = owner else {
        return OwnerValidationStep {
            state,
            orphaned: false,
            validation: None,
        };
    };
    let validation = validate_process_identity(host, owner);
    if validation.ok {
        return OwnerValidationStep {
            state: OwnerValidationState::default(),
            orphaned: false,
            validation: Some(validation),
        };
    }
    let failure_count = state.failure_count.saturating_add(1);
    if failure_count < BGJOB_OWNER_VALIDATION_FAILURE_THRESHOLD.max(1) {
        return OwnerValidationStep {
            state: OwnerValidationState {
                missing_since: None,
                failure_count,
            },
            orphaned: false,
            validation: Some(validation),
        };
    }
    let missing_since = state.missing_since.unwrap_or(now);
    let elapsed = now.saturating_sub(missing_since).as_secs_f64();
    OwnerValidationStep {
        state: OwnerValidationState {
            missing_since: Some(missing_since),
            failure_count,
        },
        orphaned: elapsed >= grace_s,
        validation: Some(validation),
    }
}

/// Parse `KEY=value` text preserving first-appearance order and last value.
///
/// The Python owner returned a `dict`, so downstream readers see the order a
/// key first appeared with the value its last row carried.
#[must_use]
pub fn ordered_rows(text: &str) -> Vec<(String, String)> {
    let Ok(document) = KvDocument::parse(text, ParseOptions::legacy()) else {
        return Vec::new();
    };
    let mut rows: Vec<(String, String)> = Vec::new();
    for row in document.rows() {
        upsert(&mut rows, row.key().to_owned(), row.value().to_owned());
    }
    rows
}

/// Merge a child-authored envelope into daemon-authored result rows.
///
/// Reserved keys stay daemon-owned, and whitespace-packed relay lines are
/// unpacked into their individual rows.
#[must_use]
pub fn merge_rows(text: &str) -> Vec<(String, String)> {
    let reserved = [BGJOB_RC_KEY, BGJOB_ELAPSED_KEY, BGJOB_STEP_KEY];
    let mut merged: Vec<(String, String)> = ordered_rows(text)
        .into_iter()
        .filter(|(key, _)| !key.is_empty() && !reserved.contains(&key.as_str()))
        .collect();
    for line in text.lines() {
        if line.matches('=').count() < MIN_PACKED_ROW_TOKENS {
            continue;
        }
        let tokens: Vec<&str> = line.split_whitespace().collect();
        if tokens.len() < MIN_PACKED_ROW_TOKENS
            || !tokens.iter().all(|token| is_packed_token(token))
        {
            continue;
        }
        for (key, value) in ordered_rows(&tokens.join("\n")) {
            if key.is_empty() || reserved.contains(&key.as_str()) {
                continue;
            }
            upsert(&mut merged, key, value);
        }
    }
    merged
}

/// Compose the exact completed-result rows for one finished job.
///
/// # Errors
///
/// Returns [`BgjobError::Invalid`] when a merged value would forge a record.
pub fn result_rows(
    step: &str,
    rc: &str,
    elapsed_s: i64,
    merge: &[(String, String)],
) -> Result<Vec<(String, String)>, BgjobError> {
    let mut rows = vec![
        (BGJOB_RC_KEY.to_owned(), rc.to_owned()),
        (BGJOB_ELAPSED_KEY.to_owned(), elapsed_s.to_string()),
        (BGJOB_STEP_KEY.to_owned(), step.to_owned()),
    ];
    rows.extend(merge.iter().cloned());
    rows.into_iter()
        .map(|(key, value)| Ok((key.clone(), reject_line_value(&value, &key)?)))
        .collect()
}

/// Compose the startup-marker rows a wait consults before reporting `DEAD`.
#[must_use]
pub fn startup_rows(step: &str, start_epoch: i64) -> Vec<(String, String)> {
    vec![
        (BGJOB_STEP_KEY.to_owned(), step.to_owned()),
        (BGJOB_START_EPOCH_KEY.to_owned(), start_epoch.to_string()),
    ]
}

/// Return whether a startup marker still covers an in-flight daemon launch.
#[must_use]
pub fn startup_in_progress(rows: &[(String, String)], step: &str, now_epoch: i64) -> bool {
    let lookup = |key: &str| {
        rows.iter()
            .find(|(candidate, _)| candidate == key)
            .map(|(_, value)| value.as_str())
    };
    let Some(Ok(start_epoch)) = lookup(BGJOB_START_EPOCH_KEY).map(str::parse::<i64>) else {
        return false;
    };
    let age_s = now_epoch.saturating_sub(start_epoch);
    lookup(BGJOB_STEP_KEY) == Some(step) && (0..=BGJOB_STARTUP_GRACE_S).contains(&age_s)
}

/// Compose the redacted diagnostic appended to stderr when a job is orphaned.
#[must_use]
pub fn orphan_diagnostic(
    owner: Option<&RecordedProcessIdentity>,
    validation: &ValidationResult,
    failure_count: u32,
) -> String {
    let mut rows = vec![
        ("BGJOB_ORPHAN_REASON".to_owned(), validation.reason.clone()),
        (
            "OWNER_PID".to_owned(),
            owner.map_or_else(String::new, |identity| identity.pid.to_string()),
        ),
        ("OWNER_FAILURE_COUNT".to_owned(), failure_count.to_string()),
    ];
    if let Some(current) = validation.current.as_ref() {
        rows.extend([
            ("OWNER_CURRENT_PGID".to_owned(), current.pgid.to_string()),
            (
                "OWNER_CURRENT_START_TIME".to_owned(),
                current.start_time.clone(),
            ),
            (
                "OWNER_CURRENT_COMMAND".to_owned(),
                bounded_command(&current.command_signature, COMMAND_LOG_LIMIT),
            ),
        ]);
    }
    redact_outbound(&render_rows(&rows))
}

/// Render `KEY=value` rows, dropping any row that would forge a record.
#[must_use]
pub fn render_rows(rows: &[(String, String)]) -> String {
    let mut rendered = String::new();
    for (key, value) in rows {
        if reject_line_value(value, key).is_ok() {
            rendered.push_str(key);
            rendered.push('=');
            rendered.push_str(value);
            rendered.push('\n');
        }
    }
    rendered
}

/// Quote the trailing stderr bytes a dead-daemon report carries on one line.
#[must_use]
pub fn log_tail(text: &str) -> String {
    let start = text
        .char_indices()
        .rev()
        .take(BGJOB_LOG_TAIL_BYTES)
        .last()
        .map_or(0, |(index, _)| index);
    let tail = text.get(start..).unwrap_or_default();
    redact_outbound(tail).replace('\n', "\\n")
}

/// Redact outbound diagnostics while preserving the caller's newline intent.
#[must_use]
pub fn redact_outbound(text: &str) -> String {
    if text.is_empty() {
        return String::new();
    }
    let redacted = redact(text).text().to_owned();
    if text.ends_with('\n') {
        redacted
    } else {
        redacted.trim_end_matches('\n').to_owned()
    }
}

fn upsert(rows: &mut Vec<(String, String)>, key: String, value: String) {
    if let Some((_, existing)) = rows.iter_mut().find(|(candidate, _)| *candidate == key) {
        *existing = value;
    } else {
        rows.push((key, value));
    }
}

fn is_packed_token(token: &str) -> bool {
    let Some((key, _)) = token.split_once('=') else {
        return false;
    };
    !key.is_empty()
        && key
            .bytes()
            .all(|byte| byte.is_ascii_uppercase() || byte.is_ascii_digit() || byte == b'_')
}

#[cfg(test)]
mod tests {
    use super::{
        BGJOB_OWNER_GRACE_S, ENV_TEST_BGJOB_OWNER_GRACE_S, MonitorLivenessState,
        OwnerValidationState, check_monitor_liveness, check_owner_validation, is_packed_token,
        log_tail, merge_rows, ordered_rows, orphan_diagnostic, parse_timing_override,
        redact_outbound, render_rows, result_rows, startup_in_progress, startup_rows,
        timing_override_or_default,
    };
    use crate::{
        IdentityProbeOutput, ProcessBirthIdentity, ProcessBirthIdentityProbeOutput,
        ProcessIdentityHost, RecordedProcessIdentity, TerminateSignal,
    };
    use std::{cell::Cell, path::Path, time::Duration};

    struct OwnerHost {
        live: bool,
        monotonic: Cell<Duration>,
        wall_s: Cell<f64>,
    }

    impl OwnerHost {
        fn new(live: bool) -> Self {
            Self {
                live,
                monotonic: Cell::new(Duration::ZERO),
                wall_s: Cell::new(0.0),
            }
        }

        fn set_clocks(&self, monotonic: Duration, wall_s: f64) {
            self.monotonic.set(monotonic);
            self.wall_s.set(wall_s);
        }
    }

    impl ProcessIdentityHost for OwnerHost {
        fn get_pgid(&self, pid: i32) -> Option<i32> {
            self.live.then_some(pid)
        }

        fn probe_ps_identity(&self, _pid: i32) -> IdentityProbeOutput {
            if self.live {
                IdentityProbeOutput::Stdout("Fri Jul 3 17:01:02 2026 owner".to_owned())
            } else {
                IdentityProbeOutput::Missing
            }
        }

        fn probe_process_birth_identity(&self, pid: i32) -> ProcessBirthIdentityProbeOutput {
            self.live
                .then_some(ProcessBirthIdentity::Darwin {
                    seconds: 1,
                    microseconds: u64::try_from(pid).unwrap_or_default(),
                })
                .map_or(
                    ProcessBirthIdentityProbeOutput::Missing,
                    ProcessBirthIdentityProbeOutput::Identity,
                )
        }

        fn pgrep_children(&self, _pid: i32) -> Vec<i32> {
            Vec::new()
        }

        fn pgrep_group(&self, _pgid: i32) -> Vec<i32> {
            Vec::new()
        }

        fn signal_process(&self, _pid: i32, _signal: TerminateSignal) -> bool {
            false
        }

        fn signal_group(&self, _pgid: i32, _signal: TerminateSignal) -> bool {
            false
        }

        fn sleep(&self, _duration: Duration) {}

        fn monotonic_now(&self) -> Duration {
            self.monotonic.get()
        }

        fn wall_time_secs(&self) -> f64 {
            self.wall_s.get()
        }

        fn current_pid(&self) -> i32 {
            0
        }

        fn parent_pid(&self) -> i32 {
            0
        }

        fn parent_of(&self, _pid: i32) -> Option<i32> {
            None
        }

        fn list_processes(&self) -> Vec<(i32, String)> {
            Vec::new()
        }

        fn resolve_path(&self, path: &str) -> String {
            path.to_owned()
        }

        fn append_kill_log_line(&self, _path: &Path, _line: &str) {}

        fn write_identity_file(&self, _path: &Path, _text: &str) -> Result<(), String> {
            Ok(())
        }

        fn read_identity_file(&self, _path: &Path) -> Option<String> {
            None
        }

        fn remove_file(&self, _path: &Path) {}

        fn is_regular_file(&self, _path: &Path) -> bool {
            false
        }

        fn file_mtime_ns(&self, _path: &Path) -> Option<u64> {
            None
        }

        fn read_text_lossy(&self, _path: &Path) -> Option<String> {
            None
        }
    }

    fn owner() -> RecordedProcessIdentity {
        RecordedProcessIdentity {
            pid: 4321,
            pgid: 4321,
            start_time: "Fri Jul 3 17:01:02 2026".to_owned(),
            birth_identity: Some(ProcessBirthIdentity::Darwin {
                seconds: 1,
                microseconds: 4321,
            }),
            command_signature: "owner".to_owned(),
            expected_signature: String::new(),
        }
    }

    #[test]
    fn owner_grace_starts_only_after_three_consecutive_failures() {
        let missing = OwnerHost::new(false);
        let mut state = OwnerValidationState::default();
        for poll in 0..2_u32 {
            let step = check_owner_validation(
                &missing,
                Some(&owner()),
                state,
                Duration::from_secs(u64::from(poll)),
                0.0,
            );
            assert!(!step.orphaned, "poll {poll} orphaned too early");
            assert_eq!(step.state.missing_since, None);
            state = step.state;
        }
        let step =
            check_owner_validation(&missing, Some(&owner()), state, Duration::from_secs(2), 0.0);
        assert!(step.orphaned);
        assert_eq!(step.state.failure_count, 3);
        assert_eq!(
            step.validation.as_ref().map(|value| value.reason.as_str()),
            Some("missing-pid")
        );
    }

    #[test]
    fn owner_grace_window_delays_orphaning_and_a_live_owner_resets_it() {
        let missing = OwnerHost::new(false);
        let mut state = OwnerValidationState::default();
        for poll in 0..3_u32 {
            state = check_owner_validation(
                &missing,
                Some(&owner()),
                state,
                Duration::from_secs(u64::from(poll)),
                120.0,
            )
            .state;
        }
        assert_eq!(state.missing_since, Some(Duration::from_secs(2)));
        let inside = check_owner_validation(
            &missing,
            Some(&owner()),
            state,
            Duration::from_secs(100),
            120.0,
        );
        assert!(!inside.orphaned);
        let outside = check_owner_validation(
            &missing,
            Some(&owner()),
            state,
            Duration::from_secs(200),
            120.0,
        );
        assert!(outside.orphaned);

        let live = check_owner_validation(
            &OwnerHost::new(true),
            Some(&owner()),
            state,
            Duration::from_secs(200),
            120.0,
        );
        assert!(!live.orphaned);
        assert_eq!(live.state, OwnerValidationState::default());

        let absent = check_owner_validation(&missing, None, state, Duration::from_secs(200), 0.0);
        assert!(!absent.orphaned);
        assert!(absent.validation.is_none());
    }

    #[test]
    fn suspend_grants_one_fresh_owner_and_wait_lease_window_without_spurious_timeout() {
        let host = OwnerHost::new(false);
        host.set_clocks(Duration::ZERO, 1_000.0);
        let mut state = MonitorLivenessState::new(&host);
        for second in [0_u32, 1, 2, 121] {
            host.set_clocks(
                Duration::from_secs(u64::from(second)),
                1_000.0 + f64::from(second),
            );
            let step = check_monitor_liveness(&host, Some(&owner()), state, 120.0);
            assert!(!step.orphaned);
            state = step.state;
        }

        host.set_clocks(Duration::from_secs(122), 14_722.0);
        let wake = check_monitor_liveness(&host, Some(&owner()), state, 120.0);
        assert!(wake.suspend_detected);
        assert!(!wake.orphaned);
        assert_eq!(wake.elapsed, Duration::from_secs(122));
        assert!(wake.elapsed < Duration::from_secs(600));

        let same_jump = check_monitor_liveness(&host, Some(&owner()), wake.state, 120.0);
        assert!(!same_jump.suspend_detected);
        assert!(!same_jump.orphaned);

        host.set_clocks(Duration::from_secs(123), 14_723.0);
        let during_grace = check_monitor_liveness(&host, Some(&owner()), same_jump.state, 120.0);
        assert!(!during_grace.orphaned);

        host.set_clocks(Duration::from_secs(512), 15_112.0);
        let expired = check_monitor_liveness(&host, Some(&owner()), during_grace.state, 120.0);
        assert!(!expired.suspend_detected);
        assert!(expired.orphaned);
    }

    #[test]
    fn timing_overrides_reject_malformed_values_and_keep_defaults() {
        let grace = |raw: &str| {
            parse_timing_override(
                raw,
                ENV_TEST_BGJOB_OWNER_GRACE_S,
                BGJOB_OWNER_GRACE_S,
                "grace",
            )
        };
        assert!((grace("").expect("default") - BGJOB_OWNER_GRACE_S).abs() < f64::EPSILON);
        assert!((grace("0.25").expect("override") - 0.25).abs() < f64::EPSILON);
        assert!(grace("0").expect("zero override").abs() < f64::EPSILON);
        for invalid in ["not-a-float", "-0.01", "nan", "inf"] {
            let error = grace(invalid).expect_err("invalid override");
            assert!(
                format!("{error}").contains(ENV_TEST_BGJOB_OWNER_GRACE_S),
                "{invalid}"
            );
        }
        assert!(
            (timing_override_or_default("LARCH_TEST_BGJOB_ABSENT", BGJOB_OWNER_GRACE_S, "grace")
                .expect("absent key default")
                - BGJOB_OWNER_GRACE_S)
                .abs()
                < f64::EPSILON
        );
    }

    #[test]
    fn merged_result_rows_keep_daemon_authority_and_unpack_relay_lines() {
        let merged = merge_rows("BGJOB_RC=9\nCUSTOM=ok\nSTEP=bad\nBGJOB_ELAPSED_S=999\n");
        assert_eq!(merged, [("CUSTOM".to_owned(), "ok".to_owned())]);

        let packed = merge_rows(
            "STATUS=fail FAILURE_REASON=checks-failed EXIT_CODE=1 STEP=bad\nMESSAGE=hello world\n",
        );
        assert_eq!(
            merge_rows("ALPHA=1 BETA=2 ALPHA=3\n"),
            [
                ("ALPHA".to_owned(), "3".to_owned()),
                ("BETA".to_owned(), "2".to_owned()),
            ]
        );
        assert_eq!(
            packed,
            [
                ("STATUS".to_owned(), "fail".to_owned()),
                ("MESSAGE".to_owned(), "hello world".to_owned()),
                ("FAILURE_REASON".to_owned(), "checks-failed".to_owned()),
                ("EXIT_CODE".to_owned(), "1".to_owned()),
            ]
        );

        let rows = result_rows("demo-step", "0", 7, &packed).expect("result rows");
        assert_eq!(
            rows.iter()
                .map(|(key, value)| format!("{key}={value}"))
                .take(3)
                .collect::<Vec<_>>(),
            ["BGJOB_RC=0", "BGJOB_ELAPSED_S=7", "STEP=demo-step"]
        );
        assert!(
            result_rows(
                "demo-step",
                "0",
                7,
                &[("BAD".to_owned(), "one\ntwo".to_owned())]
            )
            .is_err()
        );
        assert_eq!(
            ordered_rows("A=1\nA=2\nB=3\n"),
            [
                ("A".to_owned(), "2".to_owned()),
                ("B".to_owned(), "3".to_owned()),
            ]
        );
        assert!(!is_packed_token("lower=1"));
        assert!(!is_packed_token("novalue"));
    }

    #[test]
    fn startup_marker_expires_after_its_grace_window() {
        let rows = ordered_rows(&render_rows(&startup_rows("demo-step", 1_000)));
        assert!(startup_in_progress(&rows, "demo-step", 1_000));
        assert!(startup_in_progress(&rows, "demo-step", 1_025));
        assert!(!startup_in_progress(&rows, "demo-step", 1_026));
        assert!(!startup_in_progress(&rows, "demo-step", 999));
        assert!(!startup_in_progress(&rows, "other-step", 1_000));
        assert!(!startup_in_progress(&[], "demo-step", 1_000));
    }

    #[test]
    fn diagnostics_and_tails_stay_single_line_and_redacted() {
        let validation = crate::ValidationResult {
            ok: false,
            reason: "missing-pid".to_owned(),
            current: Some(owner()),
        };
        let diagnostic = orphan_diagnostic(Some(&owner()), &validation, 3);
        assert!(diagnostic.contains("BGJOB_ORPHAN_REASON=missing-pid\n"));
        assert!(diagnostic.contains("OWNER_PID=4321\n"));
        assert!(diagnostic.contains("OWNER_FAILURE_COUNT=3\n"));
        assert!(diagnostic.contains("OWNER_CURRENT_PGID=4321\n"));

        let absent_owner = crate::ValidationResult {
            ok: false,
            reason: "missing-pid".to_owned(),
            current: None,
        };
        assert!(orphan_diagnostic(None, &absent_owner, 3).contains("OWNER_PID=\n"));

        assert_eq!(log_tail("first\nsecond\n"), "first\\nsecond\\n");
        assert_eq!(log_tail(""), "");
        assert_eq!(redact_outbound("plain"), "plain");
        assert_eq!(
            render_rows(&[("BAD".to_owned(), "one\ntwo".to_owned())]),
            ""
        );
    }
}
