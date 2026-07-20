//! GitHub credential acquisition through the authenticated GitHub CLI session.

use crate::{
    ExternalProcessRunner, ExternalProgram, GitHubCliOperation, ProcessCancellation,
    ProcessErrorKind, ProcessRequest,
};
use std::{error::Error, fmt, num::NonZeroUsize, path::Path, time::Duration};

const TOKEN_TIMEOUT: Duration = Duration::from_secs(10);
const TOKEN_SHUTDOWN_GRACE: Duration = Duration::from_secs(1);
const TOKEN_OUTPUT_LIMIT: NonZeroUsize = NonZeroUsize::new(64 * 1024).unwrap();

/// Validated credential returned by `gh auth token`.
///
/// This type deliberately does not implement `Debug` so derived diagnostics
/// cannot expose the credential.
pub struct GitHubToken(String);

impl GitHubToken {
    /// Expose the credential only at the authenticated transport boundary.
    #[must_use]
    pub fn expose(&self) -> &str {
        &self.0
    }
}

/// Reason GitHub credential acquisition failed before network access.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubTokenErrorKind {
    CliUnavailable,
    NotAuthenticated,
    Interrupted,
    InvalidOutput,
    InvalidWorkingDirectory,
}

/// Secret-free GitHub credential acquisition error.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GitHubTokenError {
    kind: GitHubTokenErrorKind,
}

impl GitHubTokenError {
    #[must_use]
    pub const fn kind(self) -> GitHubTokenErrorKind {
        self.kind
    }

    const fn new(kind: GitHubTokenErrorKind) -> Self {
        Self { kind }
    }
}

impl fmt::Display for GitHubTokenError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self.kind {
            GitHubTokenErrorKind::CliUnavailable => {
                "GitHub CLI (gh) is required; install gh and run `gh auth login`"
            }
            GitHubTokenErrorKind::NotAuthenticated => {
                "GitHub CLI is not authenticated; run `gh auth login`"
            }
            GitHubTokenErrorKind::Interrupted => {
                "could not read the GitHub CLI credential; retry `gh auth token`"
            }
            GitHubTokenErrorKind::InvalidOutput => {
                "GitHub CLI returned an invalid credential; run `gh auth login`"
            }
            GitHubTokenErrorKind::InvalidWorkingDirectory => {
                "GitHub CLI credential lookup requires an absolute working directory"
            }
        })
    }
}

impl Error for GitHubTokenError {}

/// Acquire the sole GitHub credential through the closed `gh auth token` process operation.
///
/// # Errors
/// Returns a secret-free error when `gh` is absent, unauthenticated, interrupted,
/// or returns malformed or truncated output.
pub async fn acquire_github_token<R: ExternalProcessRunner + ?Sized>(
    runner: &R,
    working_directory: &Path,
    cancellation: &dyn ProcessCancellation,
) -> Result<GitHubToken, GitHubTokenError> {
    let request = ProcessRequest::new(
        ExternalProgram::GitHub(GitHubCliOperation::AuthToken),
        std::iter::empty::<&str>(),
        working_directory.to_path_buf(),
        TOKEN_TIMEOUT,
        TOKEN_SHUTDOWN_GRACE,
        TOKEN_OUTPUT_LIMIT,
    )
    .map_err(|_| GitHubTokenError::new(GitHubTokenErrorKind::InvalidWorkingDirectory))?;
    let output = runner.run(request, cancellation).await.map_err(|error| {
        let kind = match error.kind() {
            ProcessErrorKind::Cancelled | ProcessErrorKind::TimedOut => {
                GitHubTokenErrorKind::Interrupted
            }
            ProcessErrorKind::Spawn
            | ProcessErrorKind::Input
            | ProcessErrorKind::Wait
            | ProcessErrorKind::Capture
            | ProcessErrorKind::Termination => GitHubTokenErrorKind::CliUnavailable,
        };
        GitHubTokenError::new(kind)
    })?;
    if !output.status().success() {
        return Err(GitHubTokenError::new(
            GitHubTokenErrorKind::NotAuthenticated,
        ));
    }
    if output.stdout_truncated() || output.stderr_truncated() {
        return Err(GitHubTokenError::new(GitHubTokenErrorKind::InvalidOutput));
    }
    let raw = String::from_utf8(output.stdout().to_vec())
        .map_err(|_| GitHubTokenError::new(GitHubTokenErrorKind::InvalidOutput))?;
    let token = raw.trim();
    if token.is_empty() || token.bytes().any(|byte| !byte.is_ascii_graphic()) {
        return Err(GitHubTokenError::new(GitHubTokenErrorKind::InvalidOutput));
    }
    Ok(GitHubToken(token.to_owned()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{ProcessError, ProcessFuture, ProcessOutput, ProcessStatus};
    use std::{
        future::{self, Future},
        sync::{Arc, Mutex},
        task::{Context, Poll, Wake, Waker},
    };

    struct NoopWake;

    impl Wake for NoopWake {
        fn wake(self: Arc<Self>) {}
    }

    fn block_on<F: Future>(future: F) -> F::Output {
        let waker = Waker::from(Arc::new(NoopWake));
        let mut context = Context::from_waker(&waker);
        let mut future = Box::pin(future);
        loop {
            match future.as_mut().poll(&mut context) {
                Poll::Ready(output) => return output,
                Poll::Pending => std::thread::yield_now(),
            }
        }
    }

    struct NeverCancelled;

    impl ProcessCancellation for NeverCancelled {
        fn is_cancelled(&self) -> bool {
            false
        }

        fn cancelled(&self) -> std::pin::Pin<Box<dyn Future<Output = ()> + Send + '_>> {
            Box::pin(future::pending())
        }
    }

    struct FakeRunner {
        result: Mutex<Option<Result<ProcessOutput, ProcessError>>>,
        requests: Mutex<Vec<ProcessRequest>>,
    }

    impl FakeRunner {
        fn new(result: Result<ProcessOutput, ProcessError>) -> Self {
            Self {
                result: Mutex::new(Some(result)),
                requests: Mutex::new(Vec::new()),
            }
        }
    }

    impl ExternalProcessRunner for FakeRunner {
        fn run<'a>(
            &'a self,
            request: ProcessRequest,
            _cancellation: &'a dyn ProcessCancellation,
        ) -> ProcessFuture<'a> {
            self.requests.lock().expect("request lock").push(request);
            let result = self
                .result
                .lock()
                .expect("result lock")
                .take()
                .expect("one fake result");
            Box::pin(async move { result })
        }
    }

    fn output(success: bool, stdout: &[u8]) -> ProcessOutput {
        ProcessOutput::new(
            ProcessStatus::new(success, Some(i32::from(!success))),
            stdout.to_vec(),
            Vec::new(),
            false,
            false,
        )
    }

    #[test]
    fn token_lookup_uses_only_the_closed_gh_operation() {
        let runner = FakeRunner::new(Ok(output(true, b"opaque-token\n")));
        let cwd = std::env::current_dir().expect("cwd");
        let token = block_on(acquire_github_token(&runner, &cwd, &NeverCancelled)).expect("token");

        assert_eq!(token.expose(), "opaque-token");
        let requests = runner.requests.into_inner().expect("requests");
        assert_eq!(requests.len(), 1);
        assert_eq!(
            requests[0].program(),
            &ExternalProgram::GitHub(GitHubCliOperation::AuthToken)
        );
        assert!(requests[0].arguments().is_empty());
        assert!(requests[0].environment().is_empty());
        let mut arguments = requests[0].arguments().to_vec();
        requests[0].program().append_fixed_arguments(&mut arguments);
        assert_eq!(
            arguments,
            ["auth", "token", "--hostname", "github.com"].map(std::ffi::OsString::from)
        );
    }

    #[test]
    fn token_lookup_rejects_unauthenticated_and_invalid_output() {
        let cwd = std::env::current_dir().expect("cwd");
        let unavailable = FakeRunner::new(Err(ProcessError::new(
            ProcessErrorKind::Spawn,
            "raw process detail",
            None,
        )));
        let error = block_on(acquire_github_token(&unavailable, &cwd, &NeverCancelled))
            .err()
            .expect("missing gh must fail");
        assert_eq!(error.kind(), GitHubTokenErrorKind::CliUnavailable);
        assert!(error.to_string().contains("install gh"));
        assert!(!error.to_string().contains("raw process detail"));

        let unauthenticated = FakeRunner::new(Ok(output(false, b"")));
        let error = block_on(acquire_github_token(
            &unauthenticated,
            &cwd,
            &NeverCancelled,
        ))
        .err()
        .expect("unauthenticated gh must fail");
        assert_eq!(error.kind(), GitHubTokenErrorKind::NotAuthenticated);
        assert!(error.to_string().contains("gh auth login"));

        let empty = FakeRunner::new(Ok(output(true, b" \n")));
        let error = block_on(acquire_github_token(&empty, &cwd, &NeverCancelled))
            .err()
            .expect("empty token must fail");
        assert_eq!(error.kind(), GitHubTokenErrorKind::InvalidOutput);

        let multiline = FakeRunner::new(Ok(output(true, b"first\nsecond\n")));
        let error = block_on(acquire_github_token(&multiline, &cwd, &NeverCancelled))
            .err()
            .expect("multiline token must fail");
        assert_eq!(error.kind(), GitHubTokenErrorKind::InvalidOutput);
    }
}
