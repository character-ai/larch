use std::{collections::VecDeque, future, sync::Mutex};

use larch_core::{
    ExternalProcessRunner, ProcessCancellation, ProcessError, ProcessErrorKind, ProcessFuture,
    ProcessOutput, ProcessRequest, ProcessStatus,
};

/// Builder for captured process results.
#[derive(Clone, Debug)]
pub struct ProcessOutputBuilder {
    code: Option<i32>,
    success: bool,
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    stdout_truncated: bool,
    stderr_truncated: bool,
}

impl ProcessOutputBuilder {
    /// Start with a successful empty exit.
    #[must_use]
    pub const fn success() -> Self {
        Self {
            code: Some(0),
            success: true,
            stdout: Vec::new(),
            stderr: Vec::new(),
            stdout_truncated: false,
            stderr_truncated: false,
        }
    }

    /// Start with a failed empty exit.
    #[must_use]
    pub const fn failure(code: i32) -> Self {
        Self {
            code: Some(code),
            success: false,
            stdout: Vec::new(),
            stderr: Vec::new(),
            stdout_truncated: false,
            stderr_truncated: false,
        }
    }

    /// Set stdout bytes.
    #[must_use]
    pub fn stdout(mut self, stdout: impl Into<Vec<u8>>) -> Self {
        self.stdout = stdout.into();
        self
    }

    /// Set stderr bytes.
    #[must_use]
    pub fn stderr(mut self, stderr: impl Into<Vec<u8>>) -> Self {
        self.stderr = stderr.into();
        self
    }

    /// Mark either captured stream as truncated.
    #[must_use]
    pub const fn truncated(mut self, stdout: bool, stderr: bool) -> Self {
        self.stdout_truncated = stdout;
        self.stderr_truncated = stderr;
        self
    }

    /// Build the typed output.
    #[must_use]
    pub fn build(self) -> ProcessOutput {
        ProcessOutput::new(
            ProcessStatus::new(self.success, self.code),
            self.stdout,
            self.stderr,
            self.stdout_truncated,
            self.stderr_truncated,
        )
    }
}

/// A queued fake that records requests and never starts a process.
#[derive(Debug, Default)]
pub struct FakeProcessRunner {
    responses: Mutex<VecDeque<Result<ProcessOutput, ProcessError>>>,
    requests: Mutex<Vec<ProcessRequest>>,
}

impl FakeProcessRunner {
    /// Queue responses in call order.
    #[must_use]
    pub fn new(responses: impl IntoIterator<Item = Result<ProcessOutput, ProcessError>>) -> Self {
        Self {
            responses: Mutex::new(responses.into_iter().collect()),
            requests: Mutex::new(Vec::new()),
        }
    }

    /// Return a snapshot of all received requests.
    ///
    /// # Panics
    /// Panics if another test thread poisoned the fixture lock.
    #[must_use]
    pub fn requests(&self) -> Vec<ProcessRequest> {
        self.requests
            .lock()
            .expect("fake process request lock poisoned")
            .clone()
    }
}

impl ExternalProcessRunner for FakeProcessRunner {
    fn run<'a>(
        &'a self,
        request: ProcessRequest,
        cancellation: &'a dyn ProcessCancellation,
    ) -> ProcessFuture<'a> {
        self.requests
            .lock()
            .expect("fake process request lock poisoned")
            .push(request);
        Box::pin(async move {
            if cancellation.is_cancelled() {
                return Err(ProcessError::new(
                    ProcessErrorKind::Cancelled,
                    "fake process cancelled",
                    None,
                ));
            }
            self.responses
                .lock()
                .expect("fake process response lock poisoned")
                .pop_front()
                .unwrap_or_else(|| {
                    Err(ProcessError::new(
                        ProcessErrorKind::Wait,
                        "fake process response queue exhausted",
                        None,
                    ))
                })
        })
    }
}

/// Cancellation fixture that remains pending.
#[derive(Clone, Copy, Debug, Default)]
pub struct NeverCancelled;

impl ProcessCancellation for NeverCancelled {
    fn is_cancelled(&self) -> bool {
        false
    }

    fn cancelled(&self) -> std::pin::Pin<Box<dyn Future<Output = ()> + Send + '_>> {
        Box::pin(future::pending())
    }
}

#[cfg(test)]
mod tests {
    use std::{future::Future, num::NonZeroUsize, time::Duration};

    use larch_core::{
        ExternalProcessRunner, ExternalProgram, ProcessErrorKind, ProcessStatus, VendorProgram,
    };

    use super::{FakeProcessRunner, NeverCancelled, ProcessOutputBuilder};
    use crate::TestWorkspace;

    fn request(workspace: &TestWorkspace, vendor: VendorProgram) -> larch_core::ProcessRequest {
        larch_core::ProcessRequest::new(
            ExternalProgram::Vendor(vendor),
            ["exec"],
            workspace.root().to_path_buf(),
            Duration::from_secs(1),
            Duration::from_millis(100),
            NonZeroUsize::new(1024).expect("non-zero output limit"),
        )
        .expect("process request")
    }

    #[test]
    fn fake_records_requests_and_returns_queued_bytes() {
        let workspace = TestWorkspace::new().expect("test workspace");
        let runner = FakeProcessRunner::new([Ok(ProcessOutputBuilder::success()
            .stdout(b"ok\n".to_vec())
            .build())]);
        let mut future =
            Box::pin(runner.run(request(&workspace, VendorProgram::Codex), &NeverCancelled));
        let waker = std::task::Waker::noop();
        let mut context = std::task::Context::from_waker(waker);
        let std::task::Poll::Ready(result) = future.as_mut().poll(&mut context) else {
            panic!("fake response should be ready");
        };

        assert_eq!(result.expect("fake output").stdout(), b"ok\n");
        assert_eq!(runner.requests().len(), 1);
    }

    #[test]
    fn output_builder_preserves_failures_and_truncation() {
        let output = ProcessOutputBuilder::failure(17)
            .stderr(b"failed".to_vec())
            .truncated(false, true)
            .build();

        assert_eq!(output.status(), ProcessStatus::new(false, Some(17)));
        assert!(output.stderr_truncated());
    }

    #[test]
    fn exhausted_queue_fails_loudly() {
        let workspace = TestWorkspace::new().expect("test workspace");
        let runner = FakeProcessRunner::default();
        let mut future =
            Box::pin(runner.run(request(&workspace, VendorProgram::Claude), &NeverCancelled));
        let waker = std::task::Waker::noop();
        let mut context = std::task::Context::from_waker(waker);
        let std::task::Poll::Ready(result) = future.as_mut().poll(&mut context) else {
            panic!("fake error should be ready");
        };

        assert_eq!(
            result.expect_err("empty queue must fail").kind(),
            ProcessErrorKind::Wait
        );
    }
}
