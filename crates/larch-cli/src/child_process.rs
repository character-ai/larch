//! One bounded, captured child launch, owned once.
//!
//! Several commands need the same shape: run one approved program from the
//! current working directory under an explicit deadline, capture both streams
//! up to a cap, and read the result back. Keeping the request construction and
//! the runtime here means a caller states only what is specific to its child.

use std::{env, ffi::OsString, num::NonZeroUsize, sync::Arc, time::Duration};

use larch_adapters::{
    NoopProcessObserver, TokioProcessRunner,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    ExternalProcessRunner as _, ExternalProgram, ProcessError, ProcessErrorKind, ProcessOutput,
    ProcessRequest,
};

/// Build one bounded, captured child request for an approved program.
///
/// # Errors
/// Returns a stable message when the working directory or the request itself
/// is unusable.
pub fn bounded_request(
    program: ExternalProgram,
    arguments: impl IntoIterator<Item = OsString>,
    timeout: Duration,
    shutdown_grace: Duration,
    output_limit: usize,
) -> Result<ProcessRequest, String> {
    let working_directory = env::current_dir().map_err(|error| error.to_string())?;
    ProcessRequest::new(
        program,
        arguments,
        working_directory,
        timeout,
        shutdown_grace,
        NonZeroUsize::new(output_limit).unwrap_or(NonZeroUsize::MIN),
    )
    .map_err(|error| error.to_string())
}

/// Run one bounded child request to completion and return its captured output.
///
/// # Errors
/// Returns a stable message when the runtime cannot start or the child fails
/// to run to completion.
pub fn run_bounded(request: ProcessRequest) -> Result<ProcessOutput, String> {
    run_bounded_detailed(request).map_err(|error| error.message().to_owned())
}

/// Run one bounded child and keep the typed failure when it does not complete.
///
/// Callers that must tell a deadline from a missing executable — and that keep
/// whatever the child wrote before either — read the error kind and its
/// captured output instead of the collapsed message.
///
/// # Errors
/// Returns the runner's typed failure, including any partial captured output.
pub fn run_bounded_detailed(request: ProcessRequest) -> Result<ProcessOutput, ProcessError> {
    let runtime = LarchRuntime::current_thread()
        .map_err(|error| ProcessError::new(ProcessErrorKind::Spawn, error.to_string(), None))?;
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    runtime.block_on(runner.run(request, &Cancellation::new()))
}
