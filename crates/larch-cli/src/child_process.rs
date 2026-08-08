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
use larch_core::{ExternalProcessRunner as _, ExternalProgram, ProcessOutput, ProcessRequest};

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
    let runtime = LarchRuntime::current_thread().map_err(|error| error.to_string())?;
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    runtime
        .block_on(runner.run(request, &Cancellation::new()))
        .map_err(|error| error.message().to_owned())
}
