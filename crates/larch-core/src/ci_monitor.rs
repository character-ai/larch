//! Pure CI status classification and monitor transitions.

use crate::{CheckBucket, CheckRun, PullRequestMergeState};

pub const CI_POLL_INTERVAL_SECONDS: u64 = 10;
pub const CI_MAX_ITERATIONS: u64 = 50;
pub const CI_MAX_REBASES: u64 = 20;
pub const CI_MAX_FIX_ATTEMPTS: u64 = 10;
pub const CI_STATUS_FAILURE_LIMIT: u8 = 3;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CiStatusKind {
    Pass,
    Fail,
    Pending,
    Merged,
    Error,
    NoChecks,
}

impl CiStatusKind {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pass => "pass",
            Self::Fail => "fail",
            Self::Pending => "pending",
            Self::Merged => "merged",
            Self::Error => "error",
            Self::NoChecks => "NO_CHECKS",
        }
    }

    #[must_use]
    pub fn parse(value: &str) -> Option<Self> {
        Some(match value {
            "pass" => Self::Pass,
            "fail" => Self::Fail,
            "pending" => Self::Pending,
            "merged" => Self::Merged,
            "error" => Self::Error,
            "NO_CHECKS" => Self::NoChecks,
            _ => return None,
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CiStatus {
    pub kind: CiStatusKind,
    pub behind_count: usize,
    pub failed_run_id: Option<String>,
    pub conflicted: bool,
    pub checks_empty: bool,
    pub checks_observed: bool,
}

impl CiStatus {
    #[must_use]
    pub const fn pending() -> Self {
        Self {
            kind: CiStatusKind::Pending,
            behind_count: 0,
            failed_run_id: None,
            conflicted: false,
            checks_empty: false,
            checks_observed: false,
        }
    }

    #[must_use]
    pub const fn error() -> Self {
        Self {
            kind: CiStatusKind::Error,
            behind_count: 0,
            failed_run_id: None,
            conflicted: false,
            checks_empty: false,
            checks_observed: false,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CiDecision {
    pub action: &'static str,
    pub bail_reason: Option<&'static str>,
}

impl CiDecision {
    #[must_use]
    pub const fn action(action: &'static str) -> Self {
        Self {
            action,
            bail_reason: None,
        }
    }

    #[must_use]
    pub const fn bail(reason: &'static str) -> Self {
        Self {
            action: "bail",
            bail_reason: Some(reason),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CiCounters {
    pub iteration: u64,
    pub rebase_count: u64,
    pub fix_attempts: u64,
}

#[must_use]
pub const fn decide(status: &CiStatus, counters: CiCounters) -> CiDecision {
    match status.kind {
        CiStatusKind::Merged => return CiDecision::action("already_merged"),
        CiStatusKind::Error => return CiDecision::bail("ci-status-error"),
        CiStatusKind::Pass if status.behind_count == 0 || !status.conflicted => {
            return CiDecision::action("merge");
        }
        _ => {}
    }
    if counters.iteration >= CI_MAX_ITERATIONS {
        return CiDecision::bail("ci-timeout");
    }
    if counters.rebase_count >= CI_MAX_REBASES {
        return CiDecision::bail("ci-too-many-rebases");
    }
    if counters.fix_attempts >= CI_MAX_FIX_ATTEMPTS {
        return CiDecision::bail("fix-attempts-exhausted");
    }
    match status.kind {
        CiStatusKind::Pending | CiStatusKind::NoChecks => CiDecision::action("wait"),
        CiStatusKind::Pass => CiDecision::action("rebase"),
        CiStatusKind::Fail if status.behind_count > 0 && status.failed_run_id.is_none() => {
            CiDecision::action("rebase_then_evaluate")
        }
        CiStatusKind::Fail => CiDecision::action("evaluate_failure"),
        CiStatusKind::Merged => CiDecision::action("already_merged"),
        CiStatusKind::Error => CiDecision::bail("ci-status-error"),
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CheckObservation {
    pub kind: CiStatusKind,
    pub failed_run_id: Option<String>,
    pub empty: bool,
}

#[must_use]
pub fn classify_checks(checks: &[CheckRun], empty_checks_grace: u64) -> CheckObservation {
    if checks.is_empty() {
        return CheckObservation {
            kind: if empty_checks_grace == 0 {
                CiStatusKind::Pending
            } else {
                CiStatusKind::NoChecks
            },
            failed_run_id: None,
            empty: true,
        };
    }
    if let Some(check) = checks
        .iter()
        .find(|check| check.bucket == CheckBucket::Fail)
    {
        return CheckObservation {
            kind: CiStatusKind::Fail,
            failed_run_id: check.details_url.as_deref().and_then(run_id_from_url),
            empty: false,
        };
    }
    CheckObservation {
        kind: if checks
            .iter()
            .any(|check| check.bucket == CheckBucket::Pending)
        {
            CiStatusKind::Pending
        } else {
            CiStatusKind::Pass
        },
        failed_run_id: None,
        empty: false,
    }
}

fn run_id_from_url(url: &str) -> Option<String> {
    let tail = url.split("/actions/runs/").nth(1)?;
    let id: String = tail.chars().take_while(char::is_ascii_digit).collect();
    (!id.is_empty()).then_some(id)
}

#[must_use]
pub const fn conflicted(merge_state: PullRequestMergeState) -> bool {
    matches!(
        merge_state,
        PullRequestMergeState::Dirty | PullRequestMergeState::Unknown
    )
}

/// Track consecutive status failures with the legacy third-failure bail.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct StatusFailureState {
    failures: u8,
}

impl StatusFailureState {
    /// Record one status observation, degrading transient errors to pending.
    ///
    /// # Errors
    /// Returns the legacy bail decision after three consecutive status errors.
    pub fn observe(&mut self, mut status: CiStatus) -> Result<CiStatus, CiDecision> {
        if status.kind != CiStatusKind::Error {
            self.failures = 0;
            return Ok(status);
        }
        self.failures = self.failures.saturating_add(1);
        if self.failures >= CI_STATUS_FAILURE_LIMIT {
            return Err(CiDecision::bail("ci-status-stale"));
        }
        status.kind = CiStatusKind::Pending;
        Ok(status)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[rustfmt::skip]
    fn status(kind: CiStatusKind, behind: usize, conflicted: bool) -> CiStatus { CiStatus { kind, behind_count: behind, failed_run_id: None, conflicted, checks_empty: false, checks_observed: true } }

    #[test]
    #[rustfmt::skip]
    fn decision_matrix_preserves_pending_and_conflicted_transitions() {
        let counters = CiCounters { iteration: 0, rebase_count: 0, fix_attempts: 0 };
        for (kind, conflicted, expected) in [
            (CiStatusKind::Pending, false, "wait"),
            (CiStatusKind::Pass, true, "rebase"),
            (CiStatusKind::Pass, false, "merge"),
            (CiStatusKind::Fail, false, "rebase_then_evaluate"),
        ] {
            assert_eq!(decide(&status(kind, 2, conflicted), counters).action, expected);
        }
    }

    #[test]
    #[rustfmt::skip]
    fn limits_apply_after_an_immediately_mergeable_status() {
        let counters = CiCounters { iteration: CI_MAX_ITERATIONS, rebase_count: CI_MAX_REBASES, fix_attempts: CI_MAX_FIX_ATTEMPTS };
        assert_eq!(decide(&status(CiStatusKind::Pass, 0, false), counters).action, "merge");
        assert_eq!(decide(&status(CiStatusKind::Pending, 0, false), counters).bail_reason, Some("ci-timeout"));
    }

    #[test]
    #[rustfmt::skip]
    fn failed_check_yields_the_first_actions_run_id() {
        let checks=[CheckRun { name: "test".to_owned(), status: "completed".to_owned(), conclusion: Some("failure".to_owned()), details_url: Some("https://github.com/o/r/actions/runs/123/job/4".to_owned()), bucket: CheckBucket::Fail }];
        let observed=classify_checks(&checks,0); assert_eq!(observed.kind,CiStatusKind::Fail); assert_eq!(observed.failed_run_id.as_deref(),Some("123"));
    }

    #[test]
    #[rustfmt::skip]
    fn third_consecutive_status_error_bails() {
        let mut failures=StatusFailureState::default(); for _ in 0..2 { assert_eq!(failures.observe(CiStatus::error()).unwrap().kind,CiStatusKind::Pending); }
        assert_eq!(failures.observe(CiStatus::error()).unwrap_err().bail_reason,Some("ci-status-stale"));
    }
}
