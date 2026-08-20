//! Bounded retry that waits out network-unreachable failures.
//!
//! A `/complete-umbrella` or ship-driver step that wakes on a laptop with no
//! internet hits a DNS failure, connect timeout, or refused or reset
//! connection on its first `gh` or `git` call. This driver retries only that
//! network-unreachable class inside a bounded connectivity window, leaving
//! every other failure — HTTP 4xx and 5xx included — fail-closed exactly as
//! before. It stays transport-agnostic: the caller supplies the operation, the
//! connectivity wait, and the unreachable classification.

/// A failure that can report whether it was network-unreachable.
pub trait Unreachable {
    /// Return whether the failure was a network-unreachable transport error
    /// (DNS failure, connect timeout, or a refused or reset connection).
    fn is_unreachable(&self) -> bool;
}

/// One connectivity-wait outcome the retry driver consumes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ConnectivityWait {
    online: bool,
    waited_seconds: u64,
    probe_attempts: u64,
}

impl ConnectivityWait {
    /// Build a connectivity-wait outcome from its count-only fields.
    #[must_use]
    pub const fn new(online: bool, waited_seconds: u64, probe_attempts: u64) -> Self {
        Self {
            online,
            waited_seconds,
            probe_attempts,
        }
    }

    /// Return whether every required endpoint became reachable.
    #[must_use]
    pub const fn online(self) -> bool {
        self.online
    }
}

/// Count-only metrics recorded across one offline-aware retry sequence, emitted
/// as KVs for run-log visibility.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct OfflineRetryMetrics {
    retry_count: u64,
    wait_seconds: u64,
    probe_attempts: u64,
}

impl OfflineRetryMetrics {
    /// Return the number of times the operation was re-run after an
    /// unreachable failure.
    #[must_use]
    pub const fn retry_count(self) -> u64 {
        self.retry_count
    }

    /// Return the total awake seconds spent waiting for connectivity.
    #[must_use]
    pub const fn wait_seconds(self) -> u64 {
        self.wait_seconds
    }

    /// Return the total number of endpoint probe rounds.
    #[must_use]
    pub const fn probe_attempts(self) -> u64 {
        self.probe_attempts
    }

    /// Return the field-wise saturating sum of two metric sets, so a driver
    /// that accumulates several offline-aware sequences can fold their counts
    /// into one run total.
    #[must_use]
    pub const fn merged(self, other: Self) -> Self {
        Self {
            retry_count: self.retry_count.saturating_add(other.retry_count),
            wait_seconds: self.wait_seconds.saturating_add(other.wait_seconds),
            probe_attempts: self.probe_attempts.saturating_add(other.probe_attempts),
        }
    }

    const fn record_wait(&mut self, wait: ConnectivityWait) {
        self.wait_seconds = self.wait_seconds.saturating_add(wait.waited_seconds);
        self.probe_attempts = self.probe_attempts.saturating_add(wait.probe_attempts);
    }

    const fn record_retry(&mut self) {
        self.retry_count = self.retry_count.saturating_add(1);
    }
}

/// Drive `operation` to success, waiting out network-unreachable failures.
///
/// `operation` runs each attempt from scratch and must re-read any state a
/// mutation depends on, so a mutation retried after a timed-out request
/// converges on its landed result instead of double-applying. On an
/// unreachable failure the driver calls `wait_online`; if connectivity returns
/// within its bounded window and the retry budget is not spent, the driver
/// records a retry and re-runs `operation`. When the window ceiling is reached
/// (`wait_online` reports offline) or the retry budget is exhausted, the driver
/// fails closed with the last error. Every non-unreachable failure fails closed
/// immediately, with no wait.
///
/// # Errors
///
/// Returns the last operation error after a terminal failure, a spent retry
/// budget, or an exhausted connectivity window.
pub fn retry_while_unreachable<T, E: Unreachable>(
    metrics: &mut OfflineRetryMetrics,
    max_retries: u32,
    mut operation: impl FnMut() -> Result<T, E>,
    mut wait_online: impl FnMut() -> ConnectivityWait,
) -> Result<T, E> {
    loop {
        let error = match operation() {
            Ok(value) => return Ok(value),
            Err(error) => error,
        };
        if !error.is_unreachable() {
            return Err(error);
        }
        let wait = wait_online();
        metrics.record_wait(wait);
        if !wait.online() || metrics.retry_count >= u64::from(max_retries) {
            return Err(error);
        }
        metrics.record_retry();
    }
}

/// Classify a `git` subprocess stderr or stdout blob as a network-unreachable
/// failure.
///
/// The `git` CLI has no typed connection error, so a fetch, rebase, or push
/// that could not reach the remote is recognized by the fixed diagnostics git
/// prints for DNS failure, a refused or reset connection, and a connect
/// timeout. HTTP-level remote refusals (`The requested URL returned error: 403`
/// and similar) are deliberately excluded so only the unreachable class
/// retries.
#[must_use]
pub fn git_output_is_unreachable(text: &str) -> bool {
    const SIGNATURES: &[&str] = &[
        "could not resolve host",
        "could not resolve hostname",
        "couldn't resolve host",
        "temporary failure in name resolution",
        "name or service not known",
        "connection refused",
        "connection reset",
        "connection timed out",
        "operation timed out",
        "failed to connect to",
        "couldn't connect to server",
        "network is unreachable",
        "no route to host",
        "unable to look up",
    ];
    let lower = text.to_ascii_lowercase();
    SIGNATURES.iter().any(|signature| lower.contains(signature))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    struct FakeError {
        unreachable: bool,
        tag: u32,
    }

    impl Unreachable for FakeError {
        fn is_unreachable(&self) -> bool {
            self.unreachable
        }
    }

    fn online(waited: u64, probes: u64) -> ConnectivityWait {
        ConnectivityWait::new(true, waited, probes)
    }

    fn offline(waited: u64, probes: u64) -> ConnectivityWait {
        ConnectivityWait::new(false, waited, probes)
    }

    #[test]
    fn unreachable_failures_retry_within_the_window() {
        let mut metrics = OfflineRetryMetrics::default();
        let mut attempts = 0_u32;
        let mut waits = 0_u32;
        let value = retry_while_unreachable(
            &mut metrics,
            5,
            || {
                attempts += 1;
                if attempts < 3 {
                    Err(FakeError {
                        unreachable: true,
                        tag: attempts,
                    })
                } else {
                    Ok("ok")
                }
            },
            || {
                waits += 1;
                online(4, 2)
            },
        )
        .expect("comes online and succeeds");

        assert_eq!(value, "ok");
        assert_eq!(attempts, 3);
        assert_eq!(metrics.retry_count(), 2);
        assert_eq!(metrics.wait_seconds(), 8);
        assert_eq!(metrics.probe_attempts(), 4);
    }

    #[test]
    fn http_errors_do_not_retry_or_wait() {
        let mut metrics = OfflineRetryMetrics::default();
        let mut attempts = 0_u32;
        let mut waited = false;
        let error = retry_while_unreachable(
            &mut metrics,
            5,
            || {
                attempts += 1;
                Err::<(), _>(FakeError {
                    unreachable: false,
                    tag: 7,
                })
            },
            || {
                waited = true;
                online(1, 1)
            },
        )
        .expect_err("a non-unreachable failure fails closed");

        assert_eq!(attempts, 1);
        assert_eq!(error.tag, 7);
        assert!(!waited, "connectivity is never probed for an HTTP error");
        assert_eq!(metrics, OfflineRetryMetrics::default());
    }

    #[test]
    fn an_exhausted_window_restores_fail_closed() {
        let mut metrics = OfflineRetryMetrics::default();
        let mut attempts = 0_u32;
        let error = retry_while_unreachable(
            &mut metrics,
            5,
            || {
                attempts += 1;
                Err::<(), _>(FakeError {
                    unreachable: true,
                    tag: attempts,
                })
            },
            || offline(9, 3),
        )
        .expect_err("an exhausted window fails closed");

        assert_eq!(attempts, 1);
        assert_eq!(error.tag, 1);
        assert_eq!(metrics.retry_count(), 0);
        assert_eq!(metrics.wait_seconds(), 9);
        assert_eq!(metrics.probe_attempts(), 3);
    }

    #[test]
    fn a_flapping_link_stops_at_the_retry_budget() {
        let mut metrics = OfflineRetryMetrics::default();
        let mut attempts = 0_u32;
        let error = retry_while_unreachable(
            &mut metrics,
            2,
            || {
                attempts += 1;
                Err::<(), _>(FakeError {
                    unreachable: true,
                    tag: attempts,
                })
            },
            || online(1, 1),
        )
        .expect_err("the retry budget bounds a flapping link");

        // Two retries after the first attempt, then fail closed on the third
        // unreachable failure without a further re-run.
        assert_eq!(attempts, 3);
        assert_eq!(error.tag, 3);
        assert_eq!(metrics.retry_count(), 2);
    }

    #[test]
    fn a_mutation_retried_after_a_timeout_does_not_double_apply() {
        // The first attempt's mutation lands remotely but its acknowledgement
        // times out. The re-run re-reads state, sees the landed result, and
        // returns success without issuing a second mutation.
        let mut metrics = OfflineRetryMetrics::default();
        let mut applied = 0_u32;
        let mut attempts = 0_u32;
        let value = retry_while_unreachable(
            &mut metrics,
            5,
            || {
                attempts += 1;
                if attempts == 1 {
                    // The mutation lands, then the response times out.
                    applied += 1;
                    Err(FakeError {
                        unreachable: true,
                        tag: 1,
                    })
                } else if applied == 1 {
                    // Re-read observes the landed state; no second mutation.
                    Ok("already-applied")
                } else {
                    applied += 1;
                    Ok("applied-twice")
                }
            },
            || online(2, 1),
        )
        .expect("re-read converges on the landed mutation");

        assert_eq!(value, "already-applied");
        assert_eq!(applied, 1, "the mutation is applied exactly once");
        assert_eq!(metrics.retry_count(), 1);
    }

    #[test]
    fn git_signatures_match_unreachable_but_not_http_refusals() {
        assert!(git_output_is_unreachable(
            "fatal: unable to access 'https://github.com/x/y.git/': Could not resolve host: github.com"
        ));
        assert!(git_output_is_unreachable(
            "ssh: connect to host github.com port 22: Connection refused"
        ));
        assert!(git_output_is_unreachable(
            "fatal: unable to access '...': Failed to connect to github.com port 443: Operation timed out"
        ));
        assert!(!git_output_is_unreachable(
            "fatal: unable to access '...': The requested URL returned error: 403"
        ));
        assert!(!git_output_is_unreachable(
            "error: failed to push some refs to 'origin'"
        ));
    }
}
