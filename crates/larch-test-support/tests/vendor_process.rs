use std::{future::Future, num::NonZeroUsize, pin::Pin, time::Duration};

use larch_adapters::{TokioProcessRunner, runtime::LarchRuntime};
use larch_core::{
    ChildEnvironment, ExternalProcessRunner, ExternalProgram, ProcessCancellation,
    ProcessErrorKind, ProcessRequest, VendorProgram,
};
use larch_test_support::{
    NeverCancelled, TestWorkspace, VendorBinarySet, VendorChunk, VendorContractFixture,
    VendorProcessHarness, VendorRunOptions, VendorScript,
};

const VENDORS: [VendorProgram; 3] = [
    VendorProgram::Claude,
    VendorProgram::Codex,
    VendorProgram::Cursor,
];
const TIMEOUT_AND_CANCELLATION_DELAY: Duration = Duration::from_secs(1);

struct DelayedCancellation(Duration);

impl ProcessCancellation for DelayedCancellation {
    fn is_cancelled(&self) -> bool {
        false
    }

    fn cancelled(&self) -> Pin<Box<dyn Future<Output = ()> + Send + '_>> {
        Box::pin(tokio::time::sleep(self.0))
    }
}

fn binaries() -> VendorBinarySet {
    VendorBinarySet::new(
        env!("CARGO_BIN_EXE_claude"),
        env!("CARGO_BIN_EXE_codex"),
        env!("CARGO_BIN_EXE_cursor"),
    )
    .expect("Cargo-built vendor binaries")
}

fn runtime() -> LarchRuntime {
    LarchRuntime::current_thread().expect("test runtime")
}

const fn label(vendor: VendorProgram) -> &'static str {
    vendor.executable()
}

#[test]
fn every_vendor_replays_success_and_nonzero_exit() {
    let harness = VendorProcessHarness::new(&binaries()).expect("vendor harness");
    let runner = TokioProcessRunner::default();
    let runtime = runtime();

    for vendor in VENDORS {
        let success = VendorScript::new(vendor)
            .with_chunks([
                VendorChunk::stdout(format!("{}-out-1\n", label(vendor))),
                VendorChunk::stderr(format!("{}-err\n", label(vendor))),
                VendorChunk::stdout(format!("{}-out-2\n", label(vendor))),
            ])
            .with_inter_chunk_delay_ms(1);
        let output = runtime
            .block_on(
                runner.run(
                    harness
                        .request_with(
                            &success,
                            VendorRunOptions::default().with_stdin(vec![b'x'; 128 * 1024]),
                        )
                        .expect("success request"),
                    &NeverCancelled,
                ),
            )
            .expect("fake vendor success");
        assert!(output.status().success(), "{vendor:?}");
        assert_eq!(
            output.stdout(),
            format!("{}-out-1\n{}-out-2\n", label(vendor), label(vendor)).as_bytes(),
            "{vendor:?}"
        );
        assert_eq!(
            output.stderr(),
            format!("{}-err\n", label(vendor)).as_bytes(),
            "{vendor:?}"
        );

        let failure = VendorScript::new(vendor)
            .with_chunks([VendorChunk::stderr(format!("{}-failed\n", label(vendor)))])
            .with_exit_code(7);
        let output = runtime
            .block_on(runner.run(
                harness.request(&failure).expect("failure request"),
                &NeverCancelled,
            ))
            .expect("nonzero vendor exits are captured outputs");
        assert!(!output.status().success(), "{vendor:?}");
        assert_eq!(output.status().code(), Some(7), "{vendor:?}");
    }
}

#[test]
fn every_vendor_replays_timeout_and_cancellation_with_partial_output() {
    let harness = VendorProcessHarness::new(&binaries()).expect("vendor harness");
    let runner = TokioProcessRunner::default();
    let runtime = runtime();

    for vendor in VENDORS {
        let timeout_script = VendorScript::new(vendor)
            .with_chunks([VendorChunk::stdout(format!(
                "{}-timeout-partial\n",
                label(vendor)
            ))])
            .with_never_exit(true);
        let timeout_request = harness
            .request_with(
                &timeout_script,
                VendorRunOptions::default().with_timeout(TIMEOUT_AND_CANCELLATION_DELAY),
            )
            .expect("timeout request");
        let error = runtime
            .block_on(runner.run(timeout_request, &NeverCancelled))
            .expect_err("never-exit fixture must time out");
        assert_eq!(error.kind(), ProcessErrorKind::TimedOut, "{vendor:?}");
        assert_eq!(
            error.output().expect("timeout partial output").stdout(),
            format!("{}-timeout-partial\n", label(vendor)).as_bytes(),
            "{vendor:?}"
        );

        let cancel_script = VendorScript::new(vendor)
            .with_chunks([VendorChunk::stderr(format!(
                "{}-cancel-partial\n",
                label(vendor)
            ))])
            .with_never_exit(true);
        let error = runtime
            .block_on(
                runner.run(
                    harness
                        .request(&cancel_script)
                        .expect("cancellation request"),
                    &DelayedCancellation(TIMEOUT_AND_CANCELLATION_DELAY),
                ),
            )
            .expect_err("cancelled fixture must stop");
        assert_eq!(error.kind(), ProcessErrorKind::Cancelled, "{vendor:?}");
        assert_eq!(
            error
                .output()
                .expect("cancellation partial output")
                .stderr(),
            format!("{}-cancel-partial\n", label(vendor)).as_bytes(),
            "{vendor:?}"
        );
    }
}

#[cfg(unix)]
#[test]
fn timed_out_vendor_leaves_no_live_descendant() {
    use nix::{errno::Errno, sys::signal::kill, unistd::Pid};

    let harness = VendorProcessHarness::new(&binaries()).expect("vendor harness");
    let script = VendorScript::new(VendorProgram::Codex)
        .with_never_exit(true)
        .with_descendant_depth(2);
    let request = harness
        .request_with(
            &script,
            VendorRunOptions::default()
                .with_timeout(Duration::from_secs(2))
                .with_shutdown_grace(Duration::from_millis(100)),
        )
        .expect("descendant request");
    let error = runtime()
        .block_on(TokioProcessRunner::default().run(request, &NeverCancelled))
        .expect_err("hung process tree must time out");
    assert_eq!(error.kind(), ProcessErrorKind::TimedOut);

    let pids: Vec<i32> = std::fs::read_to_string(harness.pid_file(0))
        .expect("PID ledger")
        .lines()
        .map(|line| line.parse().expect("numeric PID"))
        .collect();
    assert_eq!(pids.len(), 3, "root, child, and grandchild must start");
    for _attempt in 0..50 {
        if pids
            .iter()
            .all(|pid| matches!(kill(Pid::from_raw(*pid), None), Err(Errno::ESRCH)))
        {
            return;
        }
        std::thread::sleep(Duration::from_millis(10));
    }
    let live: Vec<_> = pids
        .into_iter()
        .filter(|pid| !matches!(kill(Pid::from_raw(*pid), None), Err(Errno::ESRCH)))
        .collect();
    assert!(live.is_empty(), "live vendor descendants: {live:?}");
}

#[test]
fn every_vendor_replays_capture_truncation_and_empty_stdout() {
    let harness = VendorProcessHarness::new(&binaries()).expect("vendor harness");
    let runner = TokioProcessRunner::default();
    let runtime = runtime();

    for vendor in VENDORS {
        let partial = VendorScript::new(vendor).with_chunks([
            VendorChunk::stdout("partial-stream"),
            VendorChunk::stderr("stderr"),
        ]);
        let request = harness
            .request_with(
                &partial,
                VendorRunOptions::default()
                    .with_output_limit(NonZeroUsize::new(4).expect("non-zero limit")),
            )
            .expect("partial request");
        let output = runtime
            .block_on(runner.run(request, &NeverCancelled))
            .expect("partial capture");
        assert_eq!(output.stdout(), b"part", "{vendor:?}");
        assert_eq!(output.stderr(), b"stde", "{vendor:?}");
        assert!(output.stdout_truncated(), "{vendor:?}");
        assert!(output.stderr_truncated(), "{vendor:?}");

        let empty = VendorScript::new(vendor).with_chunks([VendorChunk::stderr(format!(
            "{}-stderr-only\n",
            label(vendor)
        ))]);
        let output = runtime
            .block_on(runner.run(
                harness.request(&empty).expect("empty stdout request"),
                &NeverCancelled,
            ))
            .expect("empty stdout capture");
        assert!(output.stdout().is_empty(), "{vendor:?}");
        assert!(!output.stderr().is_empty(), "{vendor:?}");
    }
}

#[test]
fn recorded_contracts_replay_legacy_vendor_shapes() {
    let harness = VendorProcessHarness::new(&binaries()).expect("vendor harness");
    let runner = TokioProcessRunner::default();
    let runtime = runtime();

    let codex = VendorContractFixture::CodexSuccess
        .load()
        .expect("codex fixture");
    let output = runtime
        .block_on(runner.run(
            harness.request(&codex).expect("codex request"),
            &NeverCancelled,
        ))
        .expect("codex replay");
    let codex_text = String::from_utf8(output.stdout().to_vec()).expect("codex UTF-8");
    assert!(codex_text.contains("\"type\":\"thread.started\""));
    assert!(codex_text.contains("\"thread_id\":\"019fc6b3-e6c4-7892-a97a-c80b30a7f5b0\""));
    assert!(codex_text.contains("\"input_tokens\":12"));
    assert!(codex_text.contains("\"cached_tokens\":5"));
    assert!(codex_text.contains("\"output_tokens\":7"));

    let cursor = VendorContractFixture::CursorSuccess
        .load()
        .expect("cursor fixture");
    let output = runtime
        .block_on(runner.run(
            harness.request(&cursor).expect("cursor request"),
            &NeverCancelled,
        ))
        .expect("cursor replay");
    let cursor_json: serde_json::Value =
        serde_json::from_slice(output.stdout()).expect("cursor JSON");
    assert_eq!(cursor_json["result"], "review ok");
    assert_eq!(cursor_json["usage"]["inputTokens"], 5);
    assert_eq!(cursor_json["usage"]["outputTokens"], 3);
    assert_eq!(cursor_json["usage"]["cacheReadTokens"], 2);
    assert_eq!(cursor_json["usage"]["cacheWriteTokens"], 1);

    for (fixture, expected) in [
        (
            VendorContractFixture::ClaudeOk,
            "{\"result\":\"review ok\",\"is_error\":false,\"usage\":{\"input_tokens\":10,\"output_tokens\":4}}\n",
        ),
        (
            VendorContractFixture::ClaudeIsError,
            "{\"result\":\"vendor error\",\"is_error\":true}\n",
        ),
        (
            VendorContractFixture::ClaudeEmptyResult,
            "{\"result\":\"\"}\n",
        ),
        (
            VendorContractFixture::ClaudeMissingResult,
            "{\"is_error\":false}\n",
        ),
        (
            VendorContractFixture::ClaudeNonStringResult,
            "{\"result\":42}\n",
        ),
        (VendorContractFixture::ClaudeMalformedJson, "{not-json\n"),
        (VendorContractFixture::ClaudeNonObject, "[\"result\"]\n"),
    ] {
        let script = fixture.load().expect("Claude envelope fixture");
        let output = runtime
            .block_on(runner.run(
                harness.request(&script).expect("Claude request"),
                &NeverCancelled,
            ))
            .expect("Claude replay");
        assert_eq!(output.stdout(), expected.as_bytes(), "{}", fixture.name());
    }
}

#[test]
fn diagnostic_contracts_include_failure_text_truncation_and_redaction() {
    let harness = VendorProcessHarness::new(&binaries()).expect("vendor harness");
    let runner = TokioProcessRunner::default();
    let runtime = runtime();

    for (fixture, needle, expected_code) in [
        (VendorContractFixture::CodexQuota, "usage limit", 1),
        (
            VendorContractFixture::CodexConnectivity,
            "stream disconnected before completion",
            7,
        ),
        (
            VendorContractFixture::CodexCliGate,
            "requires a newer version of Codex",
            1,
        ),
        (
            VendorContractFixture::CursorConnectivity,
            "Failed to reach the Cursor API",
            8,
        ),
        (
            VendorContractFixture::CursorRefusal,
            "refused to continue",
            1,
        ),
        (VendorContractFixture::CursorParseError, "parse error", 1),
    ] {
        let script = fixture.load().expect("diagnostic fixture");
        let output = runtime
            .block_on(runner.run(
                harness.request(&script).expect("diagnostic request"),
                &NeverCancelled,
            ))
            .expect("diagnostic replay");
        let combined = format!(
            "{}{}",
            String::from_utf8_lossy(output.stdout()),
            String::from_utf8_lossy(output.stderr())
        );
        assert!(combined.contains(needle), "{}", fixture.name());
        assert_eq!(
            output.status().code(),
            Some(expected_code),
            "{}",
            fixture.name()
        );
    }

    let truncated = VendorContractFixture::CodexTruncated
        .load()
        .expect("truncated fixture");
    let output = runtime
        .block_on(runner.run(
            harness.request(&truncated).expect("truncated request"),
            &NeverCancelled,
        ))
        .expect("truncated replay");
    assert!(output.stdout().ends_with(b"\"input_tokens\":1"));

    let policy = VendorContractFixture::CodexPolicyRejection
        .load()
        .expect("policy fixture");
    let request = harness
        .request_with(
            &policy,
            VendorRunOptions::default().with_timeout(Duration::from_secs(2)),
        )
        .expect("policy request");
    let error = runtime
        .block_on(runner.run(request, &NeverCancelled))
        .expect_err("policy fixture waits for a watcher");
    assert_eq!(error.kind(), ProcessErrorKind::TimedOut);
    assert!(
        String::from_utf8_lossy(error.output().expect("policy output").stdout())
            .contains("Rejected")
    );

    let redaction = VendorContractFixture::Redaction
        .load()
        .expect("redaction fixture");
    let output = runtime
        .block_on(runner.run(
            harness.request(&redaction).expect("redaction request"),
            &NeverCancelled,
        ))
        .expect("redaction replay");
    assert!(String::from_utf8_lossy(output.stderr()).contains("sk-ant-"));
    assert!(!output.safe_stderr().as_str().contains("sk-ant-"));
    assert!(output.safe_stderr().as_str().contains("<REDACTED-TOKEN>"));
}

#[test]
fn missing_fake_fails_instead_of_searching_the_ambient_path() {
    let workspace = TestWorkspace::new().expect("test workspace");
    let empty_path = workspace.create_dir("empty-bin").expect("empty PATH");
    let runner = TokioProcessRunner::default();
    let runtime = runtime();

    for vendor in VENDORS {
        let request = ProcessRequest::new(
            ExternalProgram::Vendor(vendor),
            std::iter::empty::<&str>(),
            workspace.root().to_path_buf(),
            Duration::from_secs(1),
            Duration::from_millis(50),
            NonZeroUsize::new(1024).expect("non-zero limit"),
        )
        .expect("vendor request")
        .with_environment(ChildEnvironment::Path, empty_path.as_os_str());
        let error = runtime
            .block_on(runner.run(request, &NeverCancelled))
            .expect_err("ambient vendor executable must stay unreachable");
        assert_eq!(error.kind(), ProcessErrorKind::Spawn, "{vendor:?}");
    }
}
