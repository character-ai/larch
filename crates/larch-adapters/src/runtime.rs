//! Shared asynchronous runtime, cancellation, and task-ownership primitives.

use std::{
    error::Error, fmt, future::Future, io, num::NonZeroUsize, pin::Pin, sync::Arc, time::Duration,
};

use tokio::{
    runtime::{Builder, Runtime},
    sync::Semaphore,
    task::JoinSet,
    time,
};
use tokio_util::sync::CancellationToken;

/// The process-wide Tokio runtime owned by the CLI composition root.
pub struct LarchRuntime {
    inner: Runtime,
}

impl LarchRuntime {
    /// Build the production multi-thread runtime with all selected drivers.
    ///
    /// # Errors
    ///
    /// Returns an operating-system error when Tokio cannot initialize a driver
    /// or worker thread.
    pub fn new() -> io::Result<Self> {
        Builder::new_multi_thread()
            .enable_all()
            .thread_name("larch-worker")
            .build()
            .map(|inner| Self { inner })
    }

    /// Build a single-thread executor for tests and narrow tools.
    ///
    /// # Errors
    ///
    /// Returns an operating-system error when Tokio cannot initialize a driver.
    pub fn current_thread() -> io::Result<Self> {
        Builder::new_current_thread()
            .enable_all()
            .build()
            .map(|inner| Self { inner })
    }

    /// Run one top-level asynchronous command to completion.
    pub fn block_on<F: Future>(&self, future: F) -> F::Output {
        self.inner.block_on(future)
    }

    /// Build a paused single-thread executor for deterministic tests.
    ///
    /// # Errors
    ///
    /// Returns an operating-system error when Tokio cannot initialize a driver.
    pub fn paused_current_thread() -> io::Result<Self> {
        Builder::new_current_thread()
            .enable_all()
            .start_paused(true)
            .build()
            .map(|inner| Self { inner })
    }
}

/// A hierarchical cooperative-cancellation signal.
#[derive(Clone)]
pub struct Cancellation {
    token: CancellationToken,
}

impl Cancellation {
    /// Create an independent root cancellation signal.
    #[must_use]
    pub fn new() -> Self {
        Self {
            token: CancellationToken::new(),
        }
    }

    /// Create a child cancelled by this signal without allowing upward cancellation.
    #[must_use]
    pub fn child(&self) -> Self {
        Self {
            token: self.token.child_token(),
        }
    }

    /// Request cooperative cancellation.
    pub fn cancel(&self) {
        self.token.cancel();
    }

    /// Return whether cancellation has been requested.
    #[must_use]
    pub fn is_cancelled(&self) -> bool {
        self.token.is_cancelled()
    }

    /// Wait until cancellation is requested.
    pub async fn cancelled(&self) {
        self.token.cancelled().await;
    }
}

impl Default for Cancellation {
    fn default() -> Self {
        Self::new()
    }
}

/// Why an asynchronous operation did not produce its output.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CompletionError {
    /// The caller's cancellation signal fired first.
    Cancelled,
    /// The operation exceeded its caller-provided timeout.
    TimedOut,
}

impl fmt::Display for CompletionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Cancelled => formatter.write_str("operation cancelled"),
            Self::TimedOut => formatter.write_str("operation timed out"),
        }
    }
}

impl Error for CompletionError {}

/// Run an operation until it completes, is cancelled, or reaches its timeout.
///
/// # Errors
///
/// Returns [`CompletionError::Cancelled`] when `cancellation` fires first, or
/// [`CompletionError::TimedOut`] when `timeout` expires first.
pub async fn run_until<F>(
    cancellation: &Cancellation,
    timeout: Duration,
    operation: F,
) -> Result<F::Output, CompletionError>
where
    F: Future,
{
    tokio::select! {
        biased;
        () = cancellation.cancelled() => Err(CompletionError::Cancelled),
        result = time::timeout(timeout, operation) => {
            result.map_err(|_elapsed| CompletionError::TimedOut)
        }
    }
}

/// A task ended without returning its output.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TaskFailure {
    /// The owner aborted the task during bounded shutdown.
    Aborted,
    /// The task panicked.
    Panicked,
}

/// Counts from draining an owned task set.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct ShutdownReport {
    completed: usize,
    aborted: usize,
    panicked: usize,
}

impl ShutdownReport {
    /// Return the number of tasks that completed normally.
    #[must_use]
    pub const fn completed(self) -> usize {
        self.completed
    }

    /// Return the number of tasks aborted after the grace period.
    #[must_use]
    pub const fn aborted(self) -> usize {
        self.aborted
    }

    /// Return the number of tasks that panicked.
    #[must_use]
    pub const fn panicked(self) -> usize {
        self.panicked
    }

    const fn record(&mut self, result: Result<(), TaskFailure>) {
        match result {
            Ok(()) => self.completed += 1,
            Err(TaskFailure::Aborted) => self.aborted += 1,
            Err(TaskFailure::Panicked) => self.panicked += 1,
        }
    }
}

/// A bounded set that owns every task it spawns.
pub struct TaskSet<T: 'static> {
    cancellation: Cancellation,
    permits: Arc<Semaphore>,
    tasks: JoinSet<T>,
}

impl<T> TaskSet<T>
where
    T: Send + 'static,
{
    /// Create a task set under `parent` with a non-zero concurrency limit.
    #[must_use]
    pub fn new(parent: &Cancellation, limit: NonZeroUsize) -> Self {
        Self {
            cancellation: parent.child(),
            permits: Arc::new(Semaphore::new(limit.get())),
            tasks: JoinSet::new(),
        }
    }

    /// Spawn one task after a capacity slot becomes available.
    ///
    /// The task receives a child cancellation signal. Cancelling it cannot
    /// cancel sibling tasks or the parent operation.
    ///
    /// # Errors
    ///
    /// Returns [`CompletionError::Cancelled`] when the task set is cancelled
    /// before a capacity slot becomes available.
    pub async fn spawn<F, Fut>(&mut self, task: F) -> Result<(), CompletionError>
    where
        F: FnOnce(Cancellation) -> Fut + Send + 'static,
        Fut: Future<Output = T> + Send + 'static,
    {
        let permit = tokio::select! {
            biased;
            () = self.cancellation.cancelled() => return Err(CompletionError::Cancelled),
            permit = Arc::clone(&self.permits).acquire_owned() => {
                permit.map_err(|_closed| CompletionError::Cancelled)?
            }
        };
        let cancellation = self.cancellation.child();
        self.tasks.spawn(async move {
            let _permit = permit;
            task(cancellation).await
        });
        Ok(())
    }

    /// Wait for the next task result, if any tasks remain.
    pub async fn join_next(&mut self) -> Option<Result<T, TaskFailure>> {
        self.tasks.join_next().await.map(|result| {
            result.map_err(|error| {
                if error.is_cancelled() {
                    TaskFailure::Aborted
                } else {
                    TaskFailure::Panicked
                }
            })
        })
    }

    /// Cancel all tasks, allow bounded cooperative cleanup, then abort stragglers.
    pub async fn shutdown(mut self, grace: Duration) -> ShutdownReport {
        self.cancellation.cancel();
        let deadline = time::sleep(grace);
        tokio::pin!(deadline);
        let mut report = ShutdownReport::default();

        while !self.tasks.is_empty() {
            tokio::select! {
                biased;
                result = self.join_next() => {
                    if let Some(result) = result {
                        report.record(result.map(|_output| ()));
                    }
                }
                () = &mut deadline => {
                    self.tasks.abort_all();
                    break;
                }
            }
        }
        while let Some(result) = self.join_next().await {
            report.record(result.map(|_output| ()));
        }
        report
    }
}

impl<T: 'static> Drop for TaskSet<T> {
    fn drop(&mut self) {
        self.cancellation.cancel();
        self.tasks.abort_all();
    }
}

/// Boxed cancellation-safe wait future returned by a managed child.
pub type ChildWait<'a, T> = Pin<Box<dyn Future<Output = io::Result<T>> + Send + 'a>>;

/// The process adapter contract required for bounded child shutdown.
pub trait ChildProcess: Send {
    /// The child's exit-status representation.
    type Exit: Send;

    /// Ask the whole owned child group to stop gracefully.
    ///
    /// # Errors
    ///
    /// Returns an adapter error when the graceful shutdown request cannot be
    /// delivered.
    fn request_shutdown(&mut self) -> io::Result<()>;

    /// Force the whole owned child group to stop.
    ///
    /// # Errors
    ///
    /// Returns an adapter error when the force-kill request cannot be delivered.
    fn force_kill(&mut self) -> io::Result<()>;

    /// Wait for and reap the child. Dropping this future must be cancellation-safe.
    fn wait(&mut self) -> ChildWait<'_, Self::Exit>;
}

/// Request graceful child-group shutdown, escalate after `grace`, and reap the leader.
///
/// When the leader exits during grace, one final group force-kill removes a
/// descendant that ignored the graceful request. Process adapters must treat
/// an already-empty group as a successful force-kill.
///
/// # Errors
///
/// Returns a control-request error after attempting cleanup. Otherwise returns
/// the child-wait error. A failed force-kill receives one final bounded reap
/// attempt before the error is returned.
pub async fn shutdown_child<C>(child: &mut C, grace: Duration) -> io::Result<C::Exit>
where
    C: ChildProcess,
{
    let graceful_error = request_shutdown_with_retry(child).await.err();
    if graceful_error.is_none()
        && let Ok(status) = time::timeout(grace, child.wait()).await
    {
        force_kill_with_retry(child).await?;
        return status;
    }

    if let Err(force_error) = force_kill_with_retry(child).await {
        let _reap_attempt = time::timeout(grace, child.wait()).await;
        return Err(graceful_error.unwrap_or(force_error));
    }

    let status = child.wait().await;
    if let Some(error) = graceful_error {
        return Err(error);
    }
    status
}

const PROCESS_GROUP_SIGNAL_RETRY_DELAY: Duration = Duration::from_millis(10);

async fn request_shutdown_with_retry<C>(child: &mut C) -> io::Result<()>
where
    C: ChildProcess,
{
    retry_permission_denied(|| child.request_shutdown()).await
}

async fn force_kill_with_retry<C>(child: &mut C) -> io::Result<()>
where
    C: ChildProcess,
{
    retry_permission_denied(|| child.force_kill()).await
}

async fn retry_permission_denied(operation: impl FnMut() -> io::Result<()>) -> io::Result<()> {
    let mut operation = operation;
    match operation() {
        Err(error) if error.kind() == io::ErrorKind::PermissionDenied => {
            // A process group can be changing membership while its leader is
            // reaped. Retry once before reporting a control failure so teardown
            // still reaches its descendants.
            time::sleep(PROCESS_GROUP_SIGNAL_RETRY_DELAY).await;
            operation()
        }
        result => result,
    }
}

/// The operating-system event that requested root cancellation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ShutdownSignal {
    /// Interactive interrupt, normally Ctrl-C.
    Interrupt,
    /// Service termination request on Unix.
    Terminate,
}

/// Wait for SIGINT or, on Unix, SIGTERM.
///
/// # Errors
///
/// Returns an operating-system error when signal registration fails or the
/// registered signal stream closes.
pub async fn wait_for_shutdown_signal() -> io::Result<ShutdownSignal> {
    #[cfg(unix)]
    {
        let mut terminate =
            tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())?;
        tokio::select! {
            result = tokio::signal::ctrl_c() => {
                result.map(|()| ShutdownSignal::Interrupt)
            }
            signal = terminate.recv() => signal.map_or_else(
                || Err(io::Error::new(io::ErrorKind::BrokenPipe, "SIGTERM stream closed")),
                |()| Ok(ShutdownSignal::Terminate),
            )
        }
    }
    #[cfg(not(unix))]
    {
        tokio::signal::ctrl_c()
            .await
            .map(|()| ShutdownSignal::Interrupt)
    }
}

/// Wait for a shutdown signal and propagate it through `cancellation`.
///
/// # Errors
///
/// Returns an operating-system error from [`wait_for_shutdown_signal`]. The
/// cancellation signal remains unchanged on error.
pub async fn cancel_on_shutdown_signal(cancellation: &Cancellation) -> io::Result<ShutdownSignal> {
    let signal = wait_for_shutdown_signal().await?;
    cancellation.cancel();
    Ok(signal)
}

#[cfg(test)]
mod tests {
    use std::{
        future,
        sync::{
            Arc,
            atomic::{AtomicUsize, Ordering},
        },
    };

    use super::*;

    #[test]
    fn cancellation_wins_over_a_ready_timeout() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        let cancellation = Cancellation::new();
        cancellation.cancel();

        let result = runtime.block_on(run_until(
            &cancellation,
            Duration::ZERO,
            future::ready(7_u8),
        ));

        assert_eq!(result, Err(CompletionError::Cancelled));
    }

    #[test]
    fn timeout_uses_the_paused_clock() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        let cancellation = Cancellation::new();

        let result = runtime.block_on(run_until(
            &cancellation,
            Duration::from_secs(30),
            future::pending::<()>(),
        ));

        assert_eq!(result, Err(CompletionError::TimedOut));
    }

    #[test]
    fn task_set_enforces_its_concurrency_limit() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        runtime.block_on(async {
            let current = Arc::new(AtomicUsize::new(0));
            let maximum = Arc::new(AtomicUsize::new(0));
            let mut tasks = TaskSet::new(
                &Cancellation::new(),
                NonZeroUsize::new(2).expect("two is non-zero"),
            );

            for _ in 0..3 {
                let current = Arc::clone(&current);
                let maximum = Arc::clone(&maximum);
                tasks
                    .spawn(move |_cancellation| async move {
                        let running = current.fetch_add(1, Ordering::SeqCst) + 1;
                        maximum.fetch_max(running, Ordering::SeqCst);
                        time::sleep(Duration::from_secs(1)).await;
                        current.fetch_sub(1, Ordering::SeqCst);
                    })
                    .await
                    .expect("task should spawn");
            }
            while let Some(result) = tasks.join_next().await {
                result.expect("task should complete");
            }

            assert_eq!(maximum.load(Ordering::SeqCst), 2);
        });
    }

    #[test]
    fn parent_cancellation_reaches_owned_tasks() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        runtime.block_on(async {
            let parent = Cancellation::new();
            let mut tasks = TaskSet::new(&parent, NonZeroUsize::new(1).expect("one is non-zero"));
            tasks
                .spawn(|cancellation| async move {
                    cancellation.cancelled().await;
                    17_u8
                })
                .await
                .expect("task should spawn");

            parent.cancel();

            assert_eq!(tasks.join_next().await, Some(Ok(17)));
        });
    }

    struct DropCounter(Arc<AtomicUsize>);

    impl Drop for DropCounter {
        fn drop(&mut self) {
            self.0.fetch_add(1, Ordering::SeqCst);
        }
    }

    #[test]
    fn task_set_aborts_and_drops_a_non_cooperative_task() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        runtime.block_on(async {
            let drops = Arc::new(AtomicUsize::new(0));
            let mut tasks = TaskSet::new(
                &Cancellation::new(),
                NonZeroUsize::new(1).expect("one is non-zero"),
            );
            tasks
                .spawn({
                    let drops = Arc::clone(&drops);
                    move |_cancellation| async move {
                        let _guard = DropCounter(drops);
                        future::pending::<()>().await;
                    }
                })
                .await
                .expect("task should spawn");
            tokio::task::yield_now().await;

            let report = tasks.shutdown(Duration::ZERO).await;

            assert_eq!(report.aborted(), 1);
            assert_eq!(drops.load(Ordering::SeqCst), 1);
        });
    }

    #[derive(Default)]
    struct FakeChild {
        graceful: bool,
        graceful_exit: Option<i32>,
        graceful_fails: bool,
        graceful_permission_denials: usize,
        forced: bool,
        force_permission_denials: usize,
        waits: usize,
    }

    impl ChildProcess for FakeChild {
        type Exit = i32;

        fn request_shutdown(&mut self) -> io::Result<()> {
            self.graceful = true;
            if self.graceful_permission_denials > 0 {
                self.graceful_permission_denials -= 1;
                return Err(io::Error::new(
                    io::ErrorKind::PermissionDenied,
                    "transient graceful shutdown denial",
                ));
            }
            if self.graceful_fails {
                Err(io::Error::new(
                    io::ErrorKind::PermissionDenied,
                    "graceful shutdown denied",
                ))
            } else {
                Ok(())
            }
        }

        fn force_kill(&mut self) -> io::Result<()> {
            self.forced = true;
            if self.force_permission_denials > 0 {
                self.force_permission_denials -= 1;
                Err(io::Error::new(
                    io::ErrorKind::PermissionDenied,
                    "transient force-kill denial",
                ))
            } else {
                Ok(())
            }
        }

        fn wait(&mut self) -> ChildWait<'_, Self::Exit> {
            self.waits += 1;
            if self.forced {
                Box::pin(future::ready(Ok(137)))
            } else if self.graceful
                && let Some(status) = self.graceful_exit
            {
                Box::pin(future::ready(Ok(status)))
            } else {
                Box::pin(future::pending())
            }
        }
    }

    #[test]
    fn child_shutdown_escalates_and_reaps_after_the_grace_period() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        let mut child = FakeChild::default();

        let status = runtime
            .block_on(shutdown_child(&mut child, Duration::from_secs(5)))
            .expect("forced child wait should succeed");

        assert!(child.graceful);
        assert!(child.forced);
        assert_eq!(child.waits, 2);
        assert_eq!(status, 137);
    }

    #[test]
    fn child_shutdown_forces_and_reaps_after_a_graceful_signal_error() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        let mut child = FakeChild {
            graceful_fails: true,
            ..FakeChild::default()
        };

        let error = runtime
            .block_on(shutdown_child(&mut child, Duration::from_secs(5)))
            .expect_err("the control-request error should remain visible");

        assert_eq!(error.kind(), io::ErrorKind::PermissionDenied);
        assert!(child.forced);
        assert_eq!(child.waits, 1);
    }

    #[test]
    fn child_shutdown_force_cleans_group_after_leader_exit() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        let mut child = FakeChild {
            graceful_exit: Some(143),
            ..FakeChild::default()
        };
        let status = runtime
            .block_on(shutdown_child(&mut child, Duration::from_secs(5)))
            .expect("graceful exit");
        assert_eq!(status, 143);
        assert!(child.forced);
    }

    #[test]
    fn child_shutdown_retries_a_transient_group_signal_denial() {
        let runtime = LarchRuntime::paused_current_thread().expect("test runtime should build");
        let mut child = FakeChild {
            graceful_exit: Some(143),
            graceful_permission_denials: 1,
            force_permission_denials: 1,
            ..FakeChild::default()
        };

        let status = runtime
            .block_on(shutdown_child(&mut child, Duration::from_secs(5)))
            .expect("one transient group-control denial should be retried");

        assert_eq!(status, 143);
        assert!(child.graceful);
        assert!(child.forced);
    }
}
