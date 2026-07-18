//! Production clock adapters for business time and asynchronous deadlines.

use std::time::{Duration, SystemTime};

use larch_core::{AsyncClock, BusinessClock, MonotonicClock, MonotonicTime, Sleep};

/// The production wall clock.
#[derive(Clone, Copy, Debug, Default)]
pub struct SystemClock;

impl BusinessClock for SystemClock {
    fn now(&self) -> SystemTime {
        SystemTime::now()
    }
}

/// A Tokio-backed monotonic clock with an adapter-owned epoch.
#[derive(Clone, Copy, Debug)]
pub struct TokioClock {
    epoch: tokio::time::Instant,
}

impl TokioClock {
    /// Create a clock whose epoch is the current Tokio instant.
    #[must_use]
    pub fn new() -> Self {
        Self {
            epoch: tokio::time::Instant::now(),
        }
    }
}

impl Default for TokioClock {
    fn default() -> Self {
        Self::new()
    }
}

impl MonotonicClock for TokioClock {
    fn now(&self) -> MonotonicTime {
        MonotonicTime::from_elapsed(tokio::time::Instant::now().duration_since(self.epoch))
    }
}

impl AsyncClock for TokioClock {
    fn sleep(&self, duration: Duration) -> Sleep<'_> {
        Box::pin(tokio::time::sleep(duration))
    }
}

#[cfg(test)]
mod tests {
    use std::time::Duration;

    use larch_core::{AsyncClock, MonotonicClock};

    use super::TokioClock;
    use crate::runtime::LarchRuntime;

    #[test]
    fn tokio_clock_uses_paused_time() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        runtime.block_on(async {
            let clock = TokioClock::new();

            clock.sleep(Duration::from_secs(30)).await;

            assert_eq!(clock.now().elapsed(), Duration::from_secs(30));
        });
    }
}
