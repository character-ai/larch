//! The single asynchronous retry execution loop for service adapters.

use std::{error::Error, fmt, future::Future};

use larch_core::{
    AsyncClock, AttemptOutcome, Deadline, Jitter, RetryDecision, RetryObservation, RetryPolicy,
};

use crate::runtime::Cancellation;

/// A successful retry execution with its total attempt count.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RetrySuccess<T> {
    value: T,
    attempts: usize,
}

impl<T> RetrySuccess<T> {
    /// Return the successful operation value.
    #[must_use]
    pub fn into_value(self) -> T {
        self.value
    }

    /// Return the total number of attempts.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        self.attempts
    }
}

/// Why the retry executor did not produce a value.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RetryFailure<E> {
    /// The domain stopped retrying or the attempt budget was exhausted.
    Operation {
        /// The last operation error, retained for the caller but never observed.
        error: E,
        /// Total operation attempts.
        attempts: usize,
        /// Closed terminal classification.
        outcome: AttemptOutcome,
    },
    /// Caller cancellation stopped execution.
    Cancelled {
        /// Number of attempts started before cancellation.
        attempts: usize,
    },
    /// The propagated deadline stopped execution.
    DeadlineExceeded {
        /// Number of attempts started before the deadline.
        attempts: usize,
    },
}

impl<E> RetryFailure<E> {
    /// Return the number of operation attempts started.
    #[must_use]
    pub const fn attempts(&self) -> usize {
        match self {
            Self::Operation { attempts, .. }
            | Self::Cancelled { attempts }
            | Self::DeadlineExceeded { attempts } => *attempts,
        }
    }
}

impl<E> fmt::Display for RetryFailure<E> {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::Operation { .. } => "operation failed after bounded retries",
            Self::Cancelled { .. } => "retry operation cancelled",
            Self::DeadlineExceeded { .. } => "retry deadline exceeded",
        })
    }
}

impl<E: Error + 'static> Error for RetryFailure<E> {}

/// Configured owner of cancellation, deadline, jitter, and retry observations.
pub struct RetryExecutor<'a, C, J, O> {
    cancellation: &'a Cancellation,
    clock: &'a C,
    policy: RetryPolicy,
    deadline: Option<Deadline>,
    jitter: J,
    observer: O,
}

impl<'a, C, J, O> RetryExecutor<'a, C, J, O>
where
    C: AsyncClock,
    J: Jitter + Send,
    O: FnMut(RetryObservation) + Send,
{
    /// Create one retry executor for an operation ownership domain.
    #[must_use]
    pub const fn new(
        cancellation: &'a Cancellation,
        clock: &'a C,
        policy: RetryPolicy,
        deadline: Option<Deadline>,
        jitter: J,
        observer: O,
    ) -> Self {
        Self {
            cancellation,
            clock,
            policy,
            deadline,
            jitter,
            observer,
        }
    }

    /// Run one fallible asynchronous operation under the configured policy.
    ///
    /// The classifier receives the typed operation error and returns only a
    /// closed retry decision. The observer never receives that error.
    ///
    /// # Errors
    ///
    /// Returns the last operation error after a terminal classification or
    /// exhaustion. Cancellation and deadline expiration return distinct errors.
    pub async fn run<Operation, OperationFuture, Classify, T, E>(
        &mut self,
        mut operation: Operation,
        mut classify: Classify,
    ) -> Result<RetrySuccess<T>, RetryFailure<E>>
    where
        Operation: FnMut() -> OperationFuture + Send,
        OperationFuture: Future<Output = Result<T, E>> + Send,
        Classify: FnMut(&E) -> RetryDecision + Send,
        T: Send,
        E: Send,
    {
        let mut attempts = 0_usize;
        loop {
            if self.cancellation.is_cancelled() {
                return Err(self.cancelled(attempts));
            }
            if self
                .deadline
                .is_some_and(|deadline| deadline.is_elapsed(self.clock))
            {
                return Err(self.deadline_exceeded(attempts));
            }

            attempts += 1;
            let result =
                run_attempt(self.cancellation, self.clock, self.deadline, operation()).await;
            let operation_result = match result {
                AttemptResult::Completed(result) => result,
                AttemptResult::Cancelled => return Err(self.cancelled(attempts)),
                AttemptResult::DeadlineExceeded => {
                    return Err(self.deadline_exceeded(attempts));
                }
            };

            let error = match operation_result {
                Ok(value) => {
                    self.observe(attempts, AttemptOutcome::Succeeded, None);
                    return Ok(RetrySuccess { value, attempts });
                }
                Err(error) => error,
            };

            match classify(&error) {
                RetryDecision::Stop(reason) => {
                    let outcome = AttemptOutcome::Stopped(reason);
                    self.observe(attempts, outcome, None);
                    return Err(RetryFailure::Operation {
                        error,
                        attempts,
                        outcome,
                    });
                }
                RetryDecision::Retry(class) if attempts >= self.policy.max_attempts().get() => {
                    let outcome = AttemptOutcome::Exhausted(class);
                    self.observe(attempts, outcome, None);
                    return Err(RetryFailure::Operation {
                        error,
                        attempts,
                        outcome,
                    });
                }
                RetryDecision::Retry(class) => {
                    let delay = self.policy.delay_after(attempts, &mut self.jitter);
                    self.observe(attempts, AttemptOutcome::Retrying(class), Some(delay));
                    match wait_for_backoff(self.cancellation, self.clock, self.deadline, delay)
                        .await
                    {
                        WaitResult::Complete => {}
                        WaitResult::Cancelled => return Err(self.cancelled(attempts)),
                        WaitResult::DeadlineExceeded => {
                            return Err(self.deadline_exceeded(attempts));
                        }
                    }
                }
            }
        }
    }

    fn cancelled<E>(&mut self, attempts: usize) -> RetryFailure<E> {
        self.observe(attempts, AttemptOutcome::Cancelled, None);
        RetryFailure::Cancelled { attempts }
    }

    fn deadline_exceeded<E>(&mut self, attempts: usize) -> RetryFailure<E> {
        self.observe(attempts, AttemptOutcome::DeadlineExceeded, None);
        RetryFailure::DeadlineExceeded { attempts }
    }

    fn observe(
        &mut self,
        attempt: usize,
        outcome: AttemptOutcome,
        next_delay: Option<std::time::Duration>,
    ) {
        (self.observer)(RetryObservation::new(attempt, outcome, next_delay));
    }
}

async fn run_attempt<C, F, T, E>(
    cancellation: &Cancellation,
    clock: &C,
    deadline: Option<Deadline>,
    operation: F,
) -> AttemptResult<Result<T, E>>
where
    C: AsyncClock,
    F: Future<Output = Result<T, E>> + Send,
    T: Send,
    E: Send,
{
    if let Some(deadline) = deadline {
        let remaining = deadline.remaining(clock);
        tokio::select! {
            biased;
            () = cancellation.cancelled() => AttemptResult::Cancelled,
            result = operation => AttemptResult::Completed(result),
            () = clock.sleep(remaining) => AttemptResult::DeadlineExceeded,
        }
    } else {
        tokio::select! {
            biased;
            () = cancellation.cancelled() => AttemptResult::Cancelled,
            result = operation => AttemptResult::Completed(result),
        }
    }
}

async fn wait_for_backoff<C>(
    cancellation: &Cancellation,
    clock: &C,
    deadline: Option<Deadline>,
    delay: std::time::Duration,
) -> WaitResult
where
    C: AsyncClock,
{
    if let Some(deadline) = deadline {
        let remaining = deadline.remaining(clock);
        if delay >= remaining {
            tokio::select! {
                biased;
                () = cancellation.cancelled() => WaitResult::Cancelled,
                () = clock.sleep(remaining) => WaitResult::DeadlineExceeded,
            }
        } else {
            tokio::select! {
                biased;
                () = cancellation.cancelled() => WaitResult::Cancelled,
                () = clock.sleep(delay) => WaitResult::Complete,
            }
        }
    } else {
        tokio::select! {
            biased;
            () = cancellation.cancelled() => WaitResult::Cancelled,
            () = clock.sleep(delay) => WaitResult::Complete,
        }
    }
}

enum AttemptResult<T> {
    Completed(T),
    Cancelled,
    DeadlineExceeded,
}

enum WaitResult {
    Complete,
    Cancelled,
    DeadlineExceeded,
}

#[cfg(test)]
mod tests {
    use std::{convert::Infallible, future, time::Duration};

    use larch_core::{
        AttemptOutcome, Deadline, Jitter, RetryClass, RetryDecision, RetryObservation, RetryPolicy,
        StopReason,
    };

    use super::{RetryExecutor, RetryFailure};
    use crate::{clock::TokioClock, runtime::Cancellation, runtime::LarchRuntime};

    struct MaximumJitter;

    impl Jitter for MaximumJitter {
        fn sample(&mut self) -> u64 {
            u64::MAX
        }
    }

    #[test]
    fn retries_to_success_without_real_sleeping() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        runtime.block_on(async {
            let cancellation = Cancellation::new();
            let clock = TokioClock::new();
            let mut observations = Vec::new();
            let mut attempts = 0_usize;
            let result = {
                let mut executor = RetryExecutor::new(
                    &cancellation,
                    &clock,
                    RetryPolicy::default(),
                    None,
                    MaximumJitter,
                    |observation| observations.push(observation),
                );
                executor
                    .run(
                        || {
                            attempts += 1;
                            future::ready(if attempts < 3 {
                                Err("sensitive response body")
                            } else {
                                Ok("ok")
                            })
                        },
                        |_error| RetryDecision::Retry(RetryClass::Transient),
                    )
                    .await
                    .expect("third attempt should succeed")
            };

            assert_eq!(result.into_value(), "ok");
            assert_eq!(attempts, 3);
            assert_eq!(
                observations,
                [
                    RetryObservation::new(
                        1,
                        AttemptOutcome::Retrying(RetryClass::Transient),
                        Some(Duration::from_secs(2)),
                    ),
                    RetryObservation::new(
                        2,
                        AttemptOutcome::Retrying(RetryClass::Transient),
                        Some(Duration::from_secs(4)),
                    ),
                    RetryObservation::new(3, AttemptOutcome::Succeeded, None),
                ]
            );
            assert!(!format!("{observations:?}").contains("sensitive"));
        });
    }

    #[test]
    fn reports_exhaustion_with_the_last_error() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        runtime.block_on(async {
            let cancellation = Cancellation::new();
            let clock = TokioClock::new();
            let mut executor = RetryExecutor::new(
                &cancellation,
                &clock,
                RetryPolicy::default(),
                None,
                MaximumJitter,
                |_observation| {},
            );

            let failure = executor
                .run(
                    || future::ready(Err::<Infallible, _>("last error")),
                    |_error| RetryDecision::Retry(RetryClass::Transient),
                )
                .await
                .expect_err("retry budget should exhaust");

            assert_eq!(failure.attempts(), 3);
            assert_eq!(
                failure,
                RetryFailure::Operation {
                    error: "last error",
                    attempts: 3,
                    outcome: AttemptOutcome::Exhausted(RetryClass::Transient),
                }
            );
        });
    }

    #[test]
    fn cancellation_stops_during_backoff() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        runtime.block_on(async {
            let cancellation = Cancellation::new();
            let cancel_from_observer = cancellation.clone();
            let clock = TokioClock::new();
            let mut executor = RetryExecutor::new(
                &cancellation,
                &clock,
                RetryPolicy::default(),
                None,
                MaximumJitter,
                move |observation| {
                    if matches!(observation.outcome(), AttemptOutcome::Retrying(_)) {
                        cancel_from_observer.cancel();
                    }
                },
            );

            let failure = executor
                .run(
                    || future::ready(Err::<Infallible, _>("temporary")),
                    |_error| RetryDecision::Retry(RetryClass::Transient),
                )
                .await
                .expect_err("cancellation should stop retrying");

            assert_eq!(failure, RetryFailure::Cancelled { attempts: 1 });
        });
    }

    #[test]
    fn cancellation_propagates_into_an_active_attempt() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        runtime.block_on(async {
            let cancellation = Cancellation::new();
            let cancel_from_attempt = cancellation.clone();
            let clock = TokioClock::new();
            let mut executor = RetryExecutor::new(
                &cancellation,
                &clock,
                RetryPolicy::default(),
                None,
                MaximumJitter,
                |_observation| {},
            );

            let failure = executor
                .run(
                    || {
                        let cancel_from_attempt = cancel_from_attempt.clone();
                        async move {
                            cancel_from_attempt.cancel();
                            future::pending::<Result<Infallible, &'static str>>().await
                        }
                    },
                    |_error| RetryDecision::Retry(RetryClass::Transient),
                )
                .await
                .expect_err("active cancellation should stop retrying");

            assert_eq!(failure, RetryFailure::Cancelled { attempts: 1 });
        });
    }

    #[test]
    fn every_permanent_class_stops_without_retry_or_sleep() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        runtime.block_on(async {
            for reason in [
                StopReason::Usage,
                StopReason::Authorization,
                StopReason::Permanent,
            ] {
                let cancellation = Cancellation::new();
                let clock = TokioClock::new();
                let mut attempts = 0_usize;
                let mut executor = RetryExecutor::new(
                    &cancellation,
                    &clock,
                    RetryPolicy::default(),
                    None,
                    MaximumJitter,
                    |_observation| {},
                );

                let failure = executor
                    .run(
                        || {
                            attempts += 1;
                            future::ready(Err::<Infallible, _>("do not retry"))
                        },
                        |_error| RetryDecision::Stop(reason),
                    )
                    .await
                    .expect_err("permanent classification should stop");

                assert_eq!(attempts, 1);
                assert_eq!(
                    failure,
                    RetryFailure::Operation {
                        error: "do not retry",
                        attempts: 1,
                        outcome: AttemptOutcome::Stopped(reason),
                    }
                );
            }
        });
    }

    #[test]
    fn propagated_deadline_bounds_an_attempt() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        runtime.block_on(async {
            let cancellation = Cancellation::new();
            let clock = TokioClock::new();
            let deadline = Deadline::after(&clock, Duration::from_secs(5));
            let mut executor = RetryExecutor::new(
                &cancellation,
                &clock,
                RetryPolicy::default(),
                Some(deadline),
                MaximumJitter,
                |_observation| {},
            );

            let failure = executor
                .run(
                    future::pending::<Result<Infallible, &'static str>>,
                    |_error| RetryDecision::Retry(RetryClass::Transient),
                )
                .await
                .expect_err("deadline should stop a pending operation");

            assert_eq!(failure, RetryFailure::DeadlineExceeded { attempts: 1 });
        });
    }
}
