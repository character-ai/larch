//! Bounded connectivity waiting over an injected probe and monotonic clock.

use std::{error::Error, fmt, future::Future, pin::Pin, time::Duration};

use crate::{AsyncClock, Deadline, ProcessCancellation};

/// Default awake-time ceiling for one connectivity wait.
pub const DEFAULT_NET_WAIT_CEILING: Duration = Duration::from_secs(6 * 60 * 60);
/// Largest configurable ceiling, keeping every individual wait bounded and
/// avoiding oversized asynchronous timer deadlines.
pub const MAX_NET_WAIT_CEILING: Duration = Duration::from_secs(7 * 24 * 60 * 60);
/// Initial delay after the first offline probe.
pub const DEFAULT_NET_WAIT_INITIAL_BACKOFF: Duration = Duration::from_secs(5);
/// Maximum delay between offline probes.
pub const DEFAULT_NET_WAIT_MAX_BACKOFF: Duration = Duration::from_secs(5 * 60);

/// One fixed-endpoint connectivity probe result.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ConnectivityStatus {
    /// Every required endpoint was reachable.
    Online,
    /// At least one required endpoint was not reachable.
    Offline,
}

/// Future returned by a connectivity probe port.
pub type ConnectivityProbeFuture<'a> =
    Pin<Box<dyn Future<Output = ConnectivityStatus> + Send + 'a>>;

/// Effect boundary for probing the fixed services a workflow needs.
pub trait ConnectivityProbe: Send + Sync {
    /// Probe every required endpoint within `timeout`.
    fn probe(&self, timeout: Duration) -> ConnectivityProbeFuture<'_>;
}

/// Validated monotonic wait and backoff policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WaitOnlinePolicy {
    ceiling: Duration,
    initial_backoff: Duration,
    max_backoff: Duration,
}

impl WaitOnlinePolicy {
    /// Create a bounded connectivity wait policy.
    ///
    /// # Errors
    ///
    /// Returns [`WaitOnlinePolicyError`] for a zero duration or inverted
    /// backoff range.
    pub const fn new(
        ceiling: Duration,
        initial_backoff: Duration,
        max_backoff: Duration,
    ) -> Result<Self, WaitOnlinePolicyError> {
        if ceiling.is_zero() {
            return Err(WaitOnlinePolicyError::ZeroCeiling);
        }
        if ceiling.as_nanos() > MAX_NET_WAIT_CEILING.as_nanos() {
            return Err(WaitOnlinePolicyError::CeilingTooLarge);
        }
        if initial_backoff.is_zero() {
            return Err(WaitOnlinePolicyError::ZeroInitialBackoff);
        }
        if max_backoff.as_nanos() < initial_backoff.as_nanos() {
            return Err(WaitOnlinePolicyError::BackoffOrder);
        }
        Ok(Self {
            ceiling,
            initial_backoff,
            max_backoff,
        })
    }

    /// Return the monotonic wait ceiling.
    #[must_use]
    pub const fn ceiling(self) -> Duration {
        self.ceiling
    }

    fn delay_after(self, failed_attempt: u32) -> Duration {
        let exponent = failed_attempt.saturating_sub(1);
        let multiplier = 1_u128.checked_shl(exponent).unwrap_or(u128::MAX);
        let nanos = self
            .initial_backoff
            .as_nanos()
            .saturating_mul(multiplier)
            .min(self.max_backoff.as_nanos());
        duration_from_nanos(nanos)
    }
}

impl Default for WaitOnlinePolicy {
    fn default() -> Self {
        Self {
            ceiling: DEFAULT_NET_WAIT_CEILING,
            initial_backoff: DEFAULT_NET_WAIT_INITIAL_BACKOFF,
            max_backoff: DEFAULT_NET_WAIT_MAX_BACKOFF,
        }
    }
}

/// Invalid connectivity wait policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum WaitOnlinePolicyError {
    /// The whole wait had no time budget.
    ZeroCeiling,
    /// The whole wait exceeded the configured hard limit.
    CeilingTooLarge,
    /// The first retry delay was zero.
    ZeroInitialBackoff,
    /// The maximum delay was below the first delay.
    BackoffOrder,
}

impl fmt::Display for WaitOnlinePolicyError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::ZeroCeiling => formatter.write_str("connectivity wait ceiling must be positive"),
            Self::CeilingTooLarge => write!(
                formatter,
                "connectivity wait ceiling must not exceed {} seconds",
                MAX_NET_WAIT_CEILING.as_secs()
            ),
            Self::ZeroInitialBackoff => {
                formatter.write_str("connectivity initial backoff must be positive")
            }
            Self::BackoffOrder => formatter
                .write_str("connectivity maximum backoff must be at least the initial backoff"),
        }
    }
}

impl Error for WaitOnlinePolicyError {}

/// Count-only result of one bounded connectivity wait.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WaitOnlineResult {
    online: bool,
    probe_attempts: u32,
    waited: Duration,
}

impl WaitOnlineResult {
    /// Create a count-only result. Probe adapters and tests may use this to
    /// cross the effect boundary without exposing transport diagnostics.
    #[must_use]
    pub const fn new(online: bool, probe_attempts: u32, waited: Duration) -> Self {
        Self {
            online,
            probe_attempts,
            waited,
        }
    }

    /// Return whether every fixed endpoint became reachable.
    #[must_use]
    pub const fn online(self) -> bool {
        self.online
    }

    /// Return the number of endpoint probe rounds.
    #[must_use]
    pub const fn probe_attempts(self) -> u32 {
        self.probe_attempts
    }

    /// Return monotonic awake time consumed by this wait.
    #[must_use]
    pub const fn waited(self) -> Duration {
        self.waited
    }
}

/// Why a connectivity wait did not reach a normal online or ceiling result.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum WaitOnlineError {
    /// The caller cancelled the wait.
    Cancelled,
}

impl fmt::Display for WaitOnlineError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("connectivity wait cancelled")
    }
}

impl Error for WaitOnlineError {}

/// Probe until every required endpoint is reachable or the monotonic ceiling
/// expires.
///
/// # Errors
///
/// Returns [`WaitOnlineError::Cancelled`] when the caller cancels the wait.
pub async fn wait_online(
    probe: &impl ConnectivityProbe,
    clock: &impl AsyncClock,
    cancellation: &dyn ProcessCancellation,
    policy: WaitOnlinePolicy,
) -> Result<WaitOnlineResult, WaitOnlineError> {
    let started = clock.now();
    let deadline = Deadline::after(clock, policy.ceiling());
    let mut probe_attempts = 0_u32;
    loop {
        if cancellation.is_cancelled() {
            return Err(WaitOnlineError::Cancelled);
        }
        let remaining = deadline.remaining(clock);
        if remaining.is_zero() {
            return Ok(WaitOnlineResult::new(
                false,
                probe_attempts,
                elapsed_since(clock, started),
            ));
        }
        probe_attempts = probe_attempts.saturating_add(1);
        if probe.probe(remaining).await == ConnectivityStatus::Online {
            return Ok(WaitOnlineResult::new(
                true,
                probe_attempts,
                elapsed_since(clock, started),
            ));
        }
        let remaining = deadline.remaining(clock);
        if remaining.is_zero() {
            continue;
        }
        let delay = policy.delay_after(probe_attempts).min(remaining);
        clock.sleep(delay).await;
    }
}

fn elapsed_since(clock: &impl AsyncClock, started: crate::MonotonicTime) -> Duration {
    clock.now().elapsed().saturating_sub(started.elapsed())
}

fn duration_from_nanos(nanos: u128) -> Duration {
    const NANOS_PER_SECOND: u128 = 1_000_000_000;
    Duration::new(
        u64::try_from(nanos / NANOS_PER_SECOND).unwrap_or(u64::MAX),
        u32::try_from(nanos % NANOS_PER_SECOND).expect("subsecond nanoseconds fit in u32"),
    )
}

#[cfg(test)]
mod tests {
    use std::{
        collections::VecDeque,
        future,
        sync::{
            Arc, Mutex,
            atomic::{AtomicBool, AtomicU64, Ordering},
        },
        task::{Context, Poll, Waker},
    };

    use super::*;

    #[derive(Default)]
    struct ManualClock(AtomicU64);

    impl crate::MonotonicClock for ManualClock {
        fn now(&self) -> crate::MonotonicTime {
            crate::MonotonicTime::from_elapsed(Duration::from_secs(self.0.load(Ordering::SeqCst)))
        }
    }

    impl AsyncClock for ManualClock {
        fn sleep(&self, duration: Duration) -> crate::Sleep<'_> {
            Box::pin(async move {
                self.0.fetch_add(duration.as_secs(), Ordering::SeqCst);
            })
        }
    }

    struct FakeProbe {
        statuses: Mutex<VecDeque<ConnectivityStatus>>,
        timeouts: Mutex<Vec<Duration>>,
    }

    impl FakeProbe {
        fn new(statuses: impl IntoIterator<Item = ConnectivityStatus>) -> Self {
            Self {
                statuses: Mutex::new(statuses.into_iter().collect()),
                timeouts: Mutex::new(Vec::new()),
            }
        }
    }

    impl ConnectivityProbe for FakeProbe {
        fn probe(&self, timeout: Duration) -> ConnectivityProbeFuture<'_> {
            self.timeouts.lock().expect("timeouts lock").push(timeout);
            let status = self
                .statuses
                .lock()
                .expect("statuses lock")
                .pop_front()
                .unwrap_or(ConnectivityStatus::Offline);
            Box::pin(future::ready(status))
        }
    }

    struct TestCancellation(Arc<AtomicBool>);

    impl ProcessCancellation for TestCancellation {
        fn is_cancelled(&self) -> bool {
            self.0.load(Ordering::SeqCst)
        }

        fn cancelled(&self) -> Pin<Box<dyn Future<Output = ()> + Send + '_>> {
            Box::pin(future::pending())
        }
    }

    fn policy(ceiling: u64) -> WaitOnlinePolicy {
        WaitOnlinePolicy::new(
            Duration::from_secs(ceiling),
            Duration::from_secs(2),
            Duration::from_secs(4),
        )
        .expect("test policy")
    }

    fn block_on<F: Future>(future: F) -> F::Output {
        let mut future = Box::pin(future);
        let mut context = Context::from_waker(Waker::noop());
        loop {
            match future.as_mut().poll(&mut context) {
                Poll::Ready(output) => return output,
                Poll::Pending => std::thread::yield_now(),
            }
        }
    }

    #[test]
    fn offline_probes_back_off_until_the_exact_ceiling() {
        let clock = ManualClock::default();
        let probe = FakeProbe::new([]);
        let cancellation = TestCancellation(Arc::new(AtomicBool::new(false)));

        let result = block_on(wait_online(&probe, &clock, &cancellation, policy(7)))
            .expect("normal ceiling result");

        assert!(!result.online());
        assert_eq!(result.probe_attempts(), 3);
        assert_eq!(result.waited(), Duration::from_secs(7));
        assert_eq!(
            *probe.timeouts.lock().expect("timeouts lock"),
            vec![
                Duration::from_secs(7),
                Duration::from_secs(5),
                Duration::from_secs(1),
            ]
        );
    }

    #[test]
    fn online_result_preserves_probe_and_wait_counts() {
        let clock = ManualClock::default();
        let probe = FakeProbe::new([
            ConnectivityStatus::Offline,
            ConnectivityStatus::Offline,
            ConnectivityStatus::Online,
        ]);
        let cancellation = TestCancellation(Arc::new(AtomicBool::new(false)));

        let result = block_on(wait_online(&probe, &clock, &cancellation, policy(20)))
            .expect("online result");

        assert!(result.online());
        assert_eq!(result.probe_attempts(), 3);
        assert_eq!(result.waited(), Duration::from_secs(6));
    }

    #[test]
    fn cancellation_stops_before_a_probe() {
        let clock = ManualClock::default();
        let probe = FakeProbe::new([ConnectivityStatus::Online]);
        let cancellation = TestCancellation(Arc::new(AtomicBool::new(true)));

        let result = block_on(wait_online(&probe, &clock, &cancellation, policy(20)));

        assert_eq!(result, Err(WaitOnlineError::Cancelled));
        assert!(probe.timeouts.lock().expect("timeouts lock").is_empty());
    }

    #[test]
    fn policy_rejects_unbounded_shapes() {
        assert_eq!(
            WaitOnlinePolicy::new(
                Duration::ZERO,
                Duration::from_secs(1),
                Duration::from_secs(1),
            ),
            Err(WaitOnlinePolicyError::ZeroCeiling)
        );
        assert_eq!(
            WaitOnlinePolicy::new(
                Duration::from_secs(1),
                Duration::ZERO,
                Duration::from_secs(1),
            ),
            Err(WaitOnlinePolicyError::ZeroInitialBackoff)
        );
        assert_eq!(
            WaitOnlinePolicy::new(
                Duration::from_secs(1),
                Duration::from_secs(2),
                Duration::from_secs(1),
            ),
            Err(WaitOnlinePolicyError::BackoffOrder)
        );
        assert_eq!(
            WaitOnlinePolicy::new(
                MAX_NET_WAIT_CEILING + Duration::from_secs(1),
                Duration::from_secs(1),
                Duration::from_secs(1),
            ),
            Err(WaitOnlinePolicyError::CeilingTooLarge)
        );
    }

    #[test]
    fn default_backoff_grows_and_stops_at_the_cap() {
        let policy = WaitOnlinePolicy::default();

        assert_eq!(policy.delay_after(1), DEFAULT_NET_WAIT_INITIAL_BACKOFF);
        assert_eq!(policy.delay_after(2), Duration::from_secs(10));
        assert_eq!(policy.delay_after(u32::MAX), DEFAULT_NET_WAIT_MAX_BACKOFF);
    }
}
