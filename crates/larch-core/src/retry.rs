//! Typed retry classification, bounded backoff, and safe observations.

use std::{error::Error, fmt, num::NonZeroUsize, time::Duration};

/// Central retry defaults shared by service adapters.
pub mod defaults {
    use std::time::Duration;

    /// Maximum number of attempts, including the first attempt.
    pub const MAX_ATTEMPTS: usize = 3;
    /// Initial backoff before the second attempt.
    pub const INITIAL_BACKOFF: Duration = Duration::from_secs(2);
    /// Maximum backoff between attempts.
    pub const MAX_BACKOFF: Duration = Duration::from_secs(4);
}

/// A retryable failure class selected by domain code.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum RetryClass {
    /// A transient transport or infrastructure failure.
    Transient,
    /// A dependency asked the caller to reduce its request rate.
    Throttled,
    /// A concurrent update may succeed after reconciliation and delay.
    Conflict,
}

/// A terminal classification that prevents another attempt.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum StopReason {
    /// The caller supplied invalid arguments or configuration.
    Usage,
    /// The caller lacks required authentication or authority.
    Authorization,
    /// The domain recognizes a permanent failure.
    Permanent,
}

/// The typed retry decision returned by domain code.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum RetryDecision {
    /// Retry after bounded backoff.
    Retry(RetryClass),
    /// Stop immediately without sleeping.
    Stop(StopReason),
}

/// A secret-free attempt outcome suitable for metrics and logs.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum AttemptOutcome {
    /// The operation succeeded.
    Succeeded,
    /// The operation will be attempted again.
    Retrying(RetryClass),
    /// The retry budget was exhausted.
    Exhausted(RetryClass),
    /// Domain classification stopped the loop.
    Stopped(StopReason),
    /// Caller cancellation stopped the loop.
    Cancelled,
    /// The propagated deadline stopped the loop.
    DeadlineExceeded,
}

/// Structured retry data that excludes operation errors and payload text.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RetryObservation {
    attempt: usize,
    outcome: AttemptOutcome,
    next_delay: Option<Duration>,
}

impl RetryObservation {
    /// Create an observation from closed, non-sensitive fields.
    #[must_use]
    pub const fn new(
        attempt: usize,
        outcome: AttemptOutcome,
        next_delay: Option<Duration>,
    ) -> Self {
        Self {
            attempt,
            outcome,
            next_delay,
        }
    }

    /// Return the number of completed or active attempts.
    #[must_use]
    pub const fn attempt(self) -> usize {
        self.attempt
    }

    /// Return the closed attempt outcome.
    #[must_use]
    pub const fn outcome(self) -> AttemptOutcome {
        self.outcome
    }

    /// Return the bounded delay before the next attempt, when present.
    #[must_use]
    pub const fn next_delay(self) -> Option<Duration> {
        self.next_delay
    }
}

/// Supplies non-cryptographic jitter samples to retry policy.
pub trait Jitter {
    /// Return one sample across the full `u64` range.
    fn sample(&mut self) -> u64;
}

/// A deterministic xorshift jitter source with an injectable seed.
#[derive(Clone, Debug)]
pub struct DeterministicJitter {
    state: u64,
}

impl DeterministicJitter {
    /// Create a deterministic source. A zero seed maps to a fixed non-zero seed.
    #[must_use]
    pub const fn seeded(seed: u64) -> Self {
        const NON_ZERO_SEED: u64 = 0x9e37_79b9_7f4a_7c15;
        Self {
            state: if seed == 0 { NON_ZERO_SEED } else { seed },
        }
    }
}

impl Jitter for DeterministicJitter {
    fn sample(&mut self) -> u64 {
        self.state ^= self.state << 13;
        self.state ^= self.state >> 7;
        self.state ^= self.state << 17;
        self.state
    }
}

/// Retry-policy construction failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RetryPolicyError {
    /// The maximum delay was smaller than the initial delay.
    BackoffOrder,
}

impl fmt::Display for RetryPolicyError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("maximum backoff must be at least the initial backoff")
    }
}

impl Error for RetryPolicyError {}

/// Central bounded-attempt and exponential-backoff policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RetryPolicy {
    max_attempts: NonZeroUsize,
    initial_backoff: Duration,
    max_backoff: Duration,
}

impl RetryPolicy {
    /// Create a validated retry policy.
    ///
    /// # Errors
    ///
    /// Returns [`RetryPolicyError::BackoffOrder`] when `max_backoff` is less
    /// than `initial_backoff`.
    pub const fn new(
        max_attempts: NonZeroUsize,
        initial_backoff: Duration,
        max_backoff: Duration,
    ) -> Result<Self, RetryPolicyError> {
        if max_backoff.as_nanos() < initial_backoff.as_nanos() {
            return Err(RetryPolicyError::BackoffOrder);
        }
        Ok(Self {
            max_attempts,
            initial_backoff,
            max_backoff,
        })
    }

    /// Return the attempt budget, including the first attempt.
    #[must_use]
    pub const fn max_attempts(self) -> NonZeroUsize {
        self.max_attempts
    }

    /// Return a full-jitter exponential delay bounded by `max_backoff`.
    #[must_use]
    pub fn delay_after(self, failed_attempt: usize, jitter: &mut impl Jitter) -> Duration {
        let exponent = u32::try_from(failed_attempt.saturating_sub(1)).unwrap_or(u32::MAX);
        let multiplier = 1_u128.checked_shl(exponent).unwrap_or(u128::MAX);
        let ceiling_nanos = self
            .initial_backoff
            .as_nanos()
            .saturating_mul(multiplier)
            .min(self.max_backoff.as_nanos());
        let ceiling = duration_from_nanos(ceiling_nanos);
        scale_duration(ceiling, jitter.sample())
    }
}

impl Default for RetryPolicy {
    fn default() -> Self {
        Self {
            max_attempts: NonZeroUsize::new(defaults::MAX_ATTEMPTS)
                .expect("central retry attempts must be non-zero"),
            initial_backoff: defaults::INITIAL_BACKOFF,
            max_backoff: defaults::MAX_BACKOFF,
        }
    }
}

fn scale_duration(ceiling: Duration, sample: u64) -> Duration {
    let scaled = ceiling.as_nanos().saturating_mul(u128::from(sample)) / u128::from(u64::MAX);
    duration_from_nanos(scaled)
}

fn duration_from_nanos(nanos: u128) -> Duration {
    const NANOS_PER_SECOND: u128 = 1_000_000_000;
    let seconds = nanos / NANOS_PER_SECOND;
    let subsecond_nanos = nanos % NANOS_PER_SECOND;
    Duration::new(
        u64::try_from(seconds).unwrap_or(u64::MAX),
        u32::try_from(subsecond_nanos).expect("subsecond nanoseconds fit in u32"),
    )
}

#[cfg(test)]
mod tests {
    use std::{num::NonZeroUsize, time::Duration};

    use super::{DeterministicJitter, Jitter, RetryPolicy, RetryPolicyError, defaults};

    struct MaximumJitter;

    impl Jitter for MaximumJitter {
        fn sample(&mut self) -> u64 {
            u64::MAX
        }
    }

    #[test]
    fn default_backoff_is_centralized_and_bounded() {
        let policy = RetryPolicy::default();
        let mut jitter = MaximumJitter;

        assert_eq!(policy.max_attempts().get(), defaults::MAX_ATTEMPTS);
        assert_eq!(policy.delay_after(1, &mut jitter), Duration::from_secs(2));
        assert_eq!(policy.delay_after(2, &mut jitter), Duration::from_secs(4));
        assert_eq!(policy.delay_after(99, &mut jitter), Duration::from_secs(4));
    }

    #[test]
    fn seeded_jitter_is_deterministic() {
        let mut left = DeterministicJitter::seeded(42);
        let mut right = DeterministicJitter::seeded(42);

        for _ in 0..4 {
            assert_eq!(left.sample(), right.sample());
        }
    }

    #[test]
    fn large_attempt_numbers_reach_a_custom_cap_without_overflow() {
        let policy = RetryPolicy::new(
            NonZeroUsize::new(100).expect("fixture is non-zero"),
            Duration::from_nanos(1),
            Duration::from_secs(10),
        )
        .expect("fixture policy should be valid");

        assert_eq!(
            policy.delay_after(100, &mut MaximumJitter),
            Duration::from_secs(10)
        );
    }

    #[test]
    fn policy_rejects_an_inverted_backoff_range() {
        let result = RetryPolicy::new(
            NonZeroUsize::new(2).expect("fixture is non-zero"),
            Duration::from_secs(2),
            Duration::from_secs(1),
        );

        assert_eq!(result, Err(RetryPolicyError::BackoffOrder));
    }
}
