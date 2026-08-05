//! Recorded-fixture classification table and file-backed diagnostic contracts.

use std::path::Path;

use larch_adapters::{
    TemporaryRoot,
    vendor_diagnostics::{
        external_stream_reset, parse_codex_usage_file, read_launcher_artifact, read_launcher_exit,
        select_failed_agent_stderr_source, write_failed_agent_stderr_tail, write_failure_diag,
    },
};
use larch_core::{
    AuthVerdict, CodexGateSignal, FailureClass, FailureReason, LaunchFailureInputs,
    LauncherArtifact, LauncherArtifactKind, LauncherArtifactPaths, StderrCaptureMode,
    VendorProgram, classify_launch_failure, detect_codex_cli_gate,
};
use larch_test_support::{
    TestWorkspace, VendorChunk, VendorContractFixture, VendorScript, VendorStream,
};

/// The synthetic credential-shaped token carried by the redaction fixture.
const FIXTURE_SECRET: &str = "sk-ant-abcdefghijklmnopqrstuvwxyz0123456789";

struct FixtureStreams {
    stdout: String,
    stderr: String,
    exit_code: i32,
    vendor: VendorProgram,
}

fn streams(fixture: VendorContractFixture) -> FixtureStreams {
    let script: VendorScript = fixture
        .load()
        .unwrap_or_else(|error| panic!("{}: {error}", fixture.name()));
    let collect = |wanted: VendorStream| {
        script
            .chunks()
            .iter()
            .filter(|chunk: &&VendorChunk| chunk.stream() == wanted)
            .map(|chunk: &VendorChunk| chunk.text().to_owned())
            .collect::<String>()
    };
    FixtureStreams {
        stdout: collect(VendorStream::Stdout),
        stderr: collect(VendorStream::Stderr),
        exit_code: script.exit_code(),
        vendor: script.vendor(),
    }
}

fn artifact(text: &str) -> LauncherArtifact {
    if text.is_empty() {
        LauncherArtifact::missing()
    } else {
        LauncherArtifact::present(text)
    }
}

#[test]
fn every_recorded_fixture_classifies_to_its_documented_row() {
    // The launcher sidecar carries vendor stderr and the output file carries
    // vendor stdout, so each fixture replays through the real classifier inputs.
    let table = [
        (
            VendorContractFixture::CodexQuota,
            FailureClass::Health,
            FailureReason::Quota,
        ),
        (
            VendorContractFixture::CodexConnectivity,
            FailureClass::Health,
            FailureReason::OpenAiStreamDisconnected,
        ),
        (
            VendorContractFixture::CursorConnectivity,
            FailureClass::Health,
            FailureReason::CursorApiUnreachable,
        ),
        (
            VendorContractFixture::CursorRefusal,
            FailureClass::Other,
            FailureReason::Refusal,
        ),
        (
            VendorContractFixture::CursorParseError,
            FailureClass::Other,
            FailureReason::Parse,
        ),
        (
            VendorContractFixture::CodexCliGate,
            FailureClass::Other,
            FailureReason::Unknown,
        ),
        (
            VendorContractFixture::Redaction,
            FailureClass::Other,
            FailureReason::Unknown,
        ),
        (
            VendorContractFixture::CodexSuccess,
            FailureClass::None,
            FailureReason::None,
        ),
        (
            VendorContractFixture::CodexPolicyRejection,
            FailureClass::None,
            FailureReason::None,
        ),
        (
            VendorContractFixture::CodexTruncated,
            FailureClass::None,
            FailureReason::None,
        ),
        (
            VendorContractFixture::CursorSuccess,
            FailureClass::None,
            FailureReason::None,
        ),
    ];
    let mut covered = Vec::new();
    for (fixture, class, reason) in table {
        let recorded = streams(fixture);
        let sidecar = artifact(&recorded.stderr);
        let output = artifact(&recorded.stdout);
        let failure = classify_launch_failure(&LaunchFailureInputs {
            launcher_exit: recorded.exit_code,
            tool: recorded.vendor,
            auth_verdict: AuthVerdict::Unclassified,
            binary_present: true,
            sidecar: Some(&sidecar),
            output: Some(&output),
        });
        assert_eq!(failure.class(), class, "{} class", fixture.name());
        assert_eq!(failure.reason(), reason, "{} reason", fixture.name());
        covered.push(fixture.name());
    }
    // Claude envelope fixtures all record a clean exit, so they share one row.
    for fixture in VendorContractFixture::all()
        .iter()
        .filter(|fixture: &&VendorContractFixture| fixture.name().starts_with("claude-"))
    {
        let recorded = streams(*fixture);
        let output = artifact(&recorded.stdout);
        let failure = classify_launch_failure(&LaunchFailureInputs {
            launcher_exit: recorded.exit_code,
            tool: recorded.vendor,
            auth_verdict: AuthVerdict::Unclassified,
            binary_present: true,
            sidecar: None,
            output: Some(&output),
        });
        assert_eq!(failure.class(), FailureClass::None, "{}", fixture.name());
        covered.push(fixture.name());
    }
    assert_eq!(
        covered.len(),
        VendorContractFixture::all().len(),
        "every recorded fixture needs a classification row"
    );
}

#[test]
fn the_codex_gate_fixture_reports_its_model_and_signal() {
    let recorded = streams(VendorContractFixture::CodexCliGate);
    let gate = detect_codex_cli_gate(&recorded.stderr, "").expect("codex CLI gate");
    assert_eq!(gate.model(), "gpt-5.6-terra");
    assert_eq!(gate.signal(), CodexGateSignal::NewerCodexRequired);
    assert_eq!(
        gate.message(),
        "codex CLI too old for gpt-5.6-terra; run `npm install -g @openai/codex@latest`"
    );
}

#[test]
fn the_secret_bearing_fixture_never_reaches_an_emitted_diagnostic() {
    let workspace = TestWorkspace::new().expect("workspace");
    let root = TemporaryRoot::resolve(Some(workspace.root())).expect("temporary root");
    // Confined writes compare against the canonical root, so anchor on it.
    let output = root.path().join("review.txt");
    let paths = LauncherArtifactPaths::new(&output);
    let secret_body = streams(VendorContractFixture::Redaction).stderr;
    assert!(secret_body.contains(FIXTURE_SECRET));
    let _sidecar = workspace
        .write("review.txt.sidecar", secret_body.as_bytes())
        .expect("sidecar");
    let _events = workspace
        .write(
            "review.txt.events.jsonl",
            b"turn.failed after the vendor error\n" as &[u8],
        )
        .expect("events");

    let source = select_failed_agent_stderr_source(&paths, StderrCaptureMode::Separate, None)
        .expect("selection")
        .expect("sidecar is the first non-empty candidate");
    assert_eq!(source, paths.path(LauncherArtifactKind::Sidecar));
    assert!(
        write_failed_agent_stderr_tail(&root, &source, &paths, None, None).expect("tail write")
    );
    write_failure_diag(&root, &paths, None, None, None).expect("failure diag");

    for kind in [
        LauncherArtifactKind::StderrTail,
        LauncherArtifactKind::FailureDiag,
    ] {
        let emitted = read_launcher_artifact(&paths.path(kind)).expect("emitted artifact");
        assert!(emitted.exists(), "{kind:?} must exist");
        assert!(
            !emitted.text().contains(FIXTURE_SECRET),
            "{kind:?} leaked the fixture secret: {}",
            emitted.text()
        );
        assert!(emitted.text().contains("<REDACTED-TOKEN>"), "{kind:?}");
    }
}

#[test]
fn an_appended_carrier_scrubs_the_bytes_an_unmigrated_writer_left_behind() {
    let workspace = TestWorkspace::new().expect("workspace");
    let root = TemporaryRoot::resolve(Some(workspace.root())).expect("temporary root");
    let output = root.path().join("review.txt");
    let paths = LauncherArtifactPaths::new(&output);
    let _carrier = workspace
        .write(
            "review.txt.failure-diag",
            format!("===== legacy =====\nunscrubbed {FIXTURE_SECRET}\n").as_bytes(),
        )
        .expect("legacy carrier");
    let _sidecar = workspace
        .write("review.txt.sidecar", b"fresh vendor failure\n" as &[u8])
        .expect("sidecar");

    write_failure_diag(&root, &paths, None, None, None).expect("failure diag");

    let carrier =
        read_launcher_artifact(&paths.path(LauncherArtifactKind::FailureDiag)).expect("carrier");
    assert!(
        carrier.text().contains("fresh vendor failure"),
        "{}",
        carrier.text()
    );
    assert!(
        !carrier.text().contains(FIXTURE_SECRET),
        "rewritten legacy bytes leaked the secret: {}",
        carrier.text()
    );
}

#[test]
fn a_deduplicated_carrier_still_scrubs_the_bytes_already_on_disk() {
    // The dedup no-op path must not leave an unscrubbed carrier behind: the
    // legacy body here already contains the recomposed section verbatim, so
    // plan_failure_diag_write returns Skip.
    let workspace = TestWorkspace::new().expect("workspace");
    let root = TemporaryRoot::resolve(Some(workspace.root())).expect("temporary root");
    let output = root.path().join("review.txt");
    let paths = LauncherArtifactPaths::new(&output);
    let sidecar_body = format!("turn.failed carrying {FIXTURE_SECRET}\n");
    let _sidecar = workspace
        .write("review.txt.sidecar", sidecar_body.as_bytes())
        .expect("sidecar");
    let _carrier = workspace
        .write(
            "review.txt.failure-diag",
            format!("===== sidecar =====\n{sidecar_body}trailing legacy line\n").as_bytes(),
        )
        .expect("legacy carrier");

    write_failure_diag(&root, &paths, None, None, None).expect("failure diag");

    let carrier =
        read_launcher_artifact(&paths.path(LauncherArtifactKind::FailureDiag)).expect("carrier");
    assert!(
        !carrier.text().contains(FIXTURE_SECRET),
        "deduplicated carrier kept the secret on disk: {}",
        carrier.text()
    );
    assert!(
        carrier.text().contains("<REDACTED-TOKEN>"),
        "{}",
        carrier.text()
    );
    assert!(
        carrier.text().contains("trailing legacy line"),
        "the scrubbed rewrite must preserve the rest of the carrier: {}",
        carrier.text()
    );
}

#[test]
fn an_oversized_stderr_tail_is_capped_without_splitting_a_sequence() {
    let workspace = TestWorkspace::new().expect("workspace");
    let root = TemporaryRoot::resolve(Some(workspace.root())).expect("temporary root");
    let output = root.path().join("review.txt");
    let paths = LauncherArtifactPaths::new(&output);
    // One line of 3-byte characters overruns the byte cap on an odd boundary.
    let _written = workspace
        .write("review.txt.sidecar", "€".repeat(4000).as_bytes())
        .expect("sidecar");
    let source = paths.path(LauncherArtifactKind::Sidecar);

    assert!(
        write_failed_agent_stderr_tail(&root, &source, &paths, Some(30), Some(5000))
            .expect("tail write")
    );
    let tail = read_launcher_artifact(&paths.path(LauncherArtifactKind::StderrTail))
        .expect("tail artifact");
    assert_eq!(tail.text().len(), 4998);
    assert!(tail.text().chars().all(|character| character == '€'));
}

#[test]
fn a_stream_reset_rolls_history_forward_and_truncates_the_target() {
    let workspace = TestWorkspace::new().expect("workspace");
    let root = TemporaryRoot::resolve(Some(workspace.root())).expect("temporary root");
    let _written = workspace
        .write("attempt.sidecar", b"first attempt failed\n" as &[u8])
        .expect("target");
    let target = root.path().join("attempt.sidecar");
    let history = root.path().join("attempt.sidecar.history");

    external_stream_reset(&root, &target, Some(&history), "attempt-1").expect("reset");
    let rolled = read_launcher_artifact(&history).expect("history");
    assert_eq!(
        rolled.text(),
        "===== attempt-1 =====\nfirst attempt failed\n\n"
    );
    assert!(
        read_launcher_artifact(&target)
            .expect("target")
            .is_empty_file()
    );

    external_stream_reset(&root, Path::new("/dev/null"), Some(&history), "ignored")
        .expect("null device is never touched");
    assert_eq!(read_launcher_artifact(&history).expect("history"), rolled);
}

#[test]
fn launcher_exit_and_usage_reads_prefer_the_recorded_sidecars() {
    let workspace = TestWorkspace::new().expect("workspace");
    let output = workspace
        .write("review.txt", b"LAUNCHER_EXIT=4\n" as &[u8])
        .expect("output");
    assert_eq!(read_launcher_exit(&output, 0).expect("exit"), 4);
    let _done = workspace
        .write("review.txt.done", b"9\n" as &[u8])
        .expect("done");
    assert_eq!(read_launcher_exit(&output, 0).expect("exit"), 9);

    let recorded = streams(VendorContractFixture::CodexSuccess);
    let events = workspace
        .write("review.txt.events.jsonl", recorded.stdout.as_bytes())
        .expect("events");
    let totals = parse_codex_usage_file(&events).expect("totals");
    assert_eq!(totals.uncached_input_tokens(), 7);
    assert_eq!(totals.cached_input_tokens(), 5);
    assert_eq!(totals.output_tokens(), 7);
    assert_eq!(totals.total_tokens(), 19);

    let missing = workspace.path("absent.jsonl").expect("absent path");
    assert_eq!(
        parse_codex_usage_file(&missing)
            .expect_err("absent events file")
            .to_string(),
        "events file missing"
    );
}
