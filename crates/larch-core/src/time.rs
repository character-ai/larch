//! Injectable business-time and monotonic-time ports.

use std::{future::Future, pin::Pin, time::Duration, time::SystemTime};

/// A monotonic instant measured from an adapter-owned epoch.
#[derive(Clone, Copy, Debug, Default, Eq, Ord, PartialEq, PartialOrd)]
pub struct MonotonicTime(Duration);

impl MonotonicTime {
    /// Create a monotonic instant from an elapsed duration.
    #[must_use]
    pub const fn from_elapsed(elapsed: Duration) -> Self {
        Self(elapsed)
    }

    /// Return the elapsed duration from the adapter-owned epoch.
    #[must_use]
    pub const fn elapsed(self) -> Duration {
        self.0
    }

    /// Advance this instant without panicking on duration overflow.
    #[must_use]
    pub const fn saturating_add(self, duration: Duration) -> Self {
        Self(self.0.saturating_add(duration))
    }
}

/// An absolute monotonic deadline that can be propagated to child operations.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Deadline(MonotonicTime);

impl Deadline {
    /// Create a deadline relative to the supplied monotonic clock.
    #[must_use]
    pub fn after(clock: &impl MonotonicClock, timeout: Duration) -> Self {
        Self(clock.now().saturating_add(timeout))
    }

    /// Create a child deadline bounded by both this deadline and `timeout`.
    #[must_use]
    pub fn child(self, clock: &impl MonotonicClock, timeout: Duration) -> Self {
        Self(self.0.min(clock.now().saturating_add(timeout)))
    }

    /// Return the remaining duration, or zero when the deadline has passed.
    #[must_use]
    pub fn remaining(self, clock: &impl MonotonicClock) -> Duration {
        self.0.elapsed().saturating_sub(clock.now().elapsed())
    }

    /// Return whether the deadline has passed.
    #[must_use]
    pub fn is_elapsed(self, clock: &impl MonotonicClock) -> bool {
        self.remaining(clock).is_zero()
    }
}

/// Injectable wall clock for timestamps that carry business meaning.
pub trait BusinessClock {
    /// Return the current wall-clock time.
    fn now(&self) -> SystemTime;
}

/// Injectable monotonic clock for elapsed-time and deadline decisions.
pub trait MonotonicClock {
    /// Return the current monotonic instant.
    fn now(&self) -> MonotonicTime;
}

/// A boxed sleep future supplied by an asynchronous clock adapter.
pub type Sleep<'a> = Pin<Box<dyn Future<Output = ()> + Send + 'a>>;

/// Injectable asynchronous monotonic clock used by bounded waits.
pub trait AsyncClock: MonotonicClock + Send + Sync {
    /// Wait for `duration` according to this clock.
    fn sleep(&self, duration: Duration) -> Sleep<'_>;
}

#[cfg(test)]
mod tests {
    use std::{cell::Cell, time::Duration};

    use super::{Deadline, MonotonicClock, MonotonicTime};

    struct FakeClock(Cell<Duration>);

    impl FakeClock {
        const fn new() -> Self {
            Self(Cell::new(Duration::ZERO))
        }

        fn advance(&self, duration: Duration) {
            self.0.set(self.0.get().saturating_add(duration));
        }
    }

    impl MonotonicClock for FakeClock {
        fn now(&self) -> MonotonicTime {
            MonotonicTime::from_elapsed(self.0.get())
        }
    }

    #[test]
    fn deadline_tracks_an_injected_clock_without_wall_time() {
        let clock = FakeClock::new();
        let deadline = Deadline::after(&clock, Duration::from_secs(10));

        clock.advance(Duration::from_secs(4));

        assert_eq!(deadline.remaining(&clock), Duration::from_secs(6));
        assert!(!deadline.is_elapsed(&clock));
        clock.advance(Duration::from_secs(6));
        assert!(deadline.is_elapsed(&clock));
    }

    #[test]
    fn child_deadline_never_outlives_its_parent() {
        let clock = FakeClock::new();
        let parent = Deadline::after(&clock, Duration::from_secs(10));

        assert_eq!(parent.child(&clock, Duration::from_secs(30)), parent);
        assert_eq!(
            parent
                .child(&clock, Duration::from_secs(3))
                .remaining(&clock),
            Duration::from_secs(3)
        );
    }
}
