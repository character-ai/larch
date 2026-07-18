use std::{
    sync::Mutex,
    time::{Duration, SystemTime},
};

use larch_core::{AsyncClock, BusinessClock, MonotonicClock, MonotonicTime, Sleep};

#[derive(Clone, Copy, Debug)]
struct ClockState {
    wall: SystemTime,
    elapsed: Duration,
}

/// A thread-safe clock advanced only by the test.
#[derive(Debug)]
pub struct TestClock {
    state: Mutex<ClockState>,
}

impl TestClock {
    /// Start at a fixed wall time and zero monotonic time.
    #[must_use]
    pub const fn new(wall: SystemTime) -> Self {
        Self {
            state: Mutex::new(ClockState {
                wall,
                elapsed: Duration::ZERO,
            }),
        }
    }

    /// Advance wall and monotonic time together.
    ///
    /// # Panics
    /// Panics if the fixture lock is poisoned or wall time overflows.
    pub fn advance(&self, duration: Duration) {
        let mut state = self.state.lock().expect("test clock lock poisoned");
        state.wall = state
            .wall
            .checked_add(duration)
            .expect("test clock wall time overflow");
        state.elapsed = state.elapsed.saturating_add(duration);
    }
}

impl BusinessClock for TestClock {
    fn now(&self) -> SystemTime {
        self.state.lock().expect("test clock lock poisoned").wall
    }
}

impl MonotonicClock for TestClock {
    fn now(&self) -> MonotonicTime {
        MonotonicTime::from_elapsed(self.state.lock().expect("test clock lock poisoned").elapsed)
    }
}

impl AsyncClock for TestClock {
    fn sleep(&self, duration: Duration) -> Sleep<'_> {
        Box::pin(async move { self.advance(duration) })
    }
}

#[cfg(test)]
mod tests {
    use std::{future::Future, time::Duration, time::SystemTime};

    use larch_core::{AsyncClock, BusinessClock, MonotonicClock};

    use super::TestClock;

    #[test]
    fn manual_advance_updates_both_clock_domains() {
        let clock = TestClock::new(SystemTime::UNIX_EPOCH);

        clock.advance(Duration::from_secs(4));

        assert_eq!(
            BusinessClock::now(&clock),
            SystemTime::UNIX_EPOCH + Duration::from_secs(4)
        );
        assert_eq!(
            MonotonicClock::now(&clock).elapsed(),
            Duration::from_secs(4)
        );
    }

    #[test]
    fn async_sleep_completes_without_real_time() {
        let clock = TestClock::new(SystemTime::UNIX_EPOCH);
        let mut future = Box::pin(clock.sleep(Duration::from_secs(30)));
        let waker = std::task::Waker::noop();
        let mut context = std::task::Context::from_waker(waker);

        assert!(future.as_mut().poll(&mut context).is_ready());
        assert_eq!(
            MonotonicClock::now(&clock).elapsed(),
            Duration::from_secs(30)
        );
    }
}
