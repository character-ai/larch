use std::{
    fs,
    os::unix::fs::PermissionsExt as _,
    path::{Path, PathBuf},
    process::{Command, Output},
};

use tempfile::TempDir;

#[allow(clippy::literal_string_with_formatting_args, clippy::too_many_lines)] // One shell fixture models the nested legacy command surface exercised by every contract case.
fn install_plugin(root: &Path) -> PathBuf {
    let plugin = root.join("plugin");
    let scripts = plugin.join("scripts");
    fs::create_dir_all(&scripts).expect("fixture scripts");
    let bootstrap = scripts.join("larch.sh");
    fs::write(
        &bootstrap,
        r#"#!/bin/sh
set -eu

scenario=$(cat "$CLAUDE_PLUGIN_ROOT/scenario")
domain=${1:-}
verb=${2:-}
shift 2 || true

value_after() {
  target=$1
  shift
  while [ "$#" -gt 0 ]; do
    if [ "$1" = "$target" ]; then
      printf '%s' "${2:-}"
      return
    fi
    shift
  done
}

review_tmp=$(value_after --review-tmpdir "$@")
output_dir=$(value_after --output-dir "$@")
findings=$(value_after --findings-file "$@")
oos=$(value_after --oos-file "$@")

case "$domain:$verb" in
  review:gather-context)
    if [ "$scenario" = "description-empty" ]; then
      printf 'MODE=description\nSCOPE_FILES_COUNT=0\n'
    else
      printf 'MODE=diff\nDIFF_FILE=%s/diff.patch\nFILE_LIST_FILE=%s/scope-files.txt\nCOMMIT_COUNT=1\n' "$output_dir" "$output_dir"
      if [ "$scenario" = "dispatch-bootstrap-failure" ]; then
        rm "$0"
      fi
    fi
    ;;
  review:dispatch-panel)
    mkdir -p "$review_tmp"
    if [ "$scenario" = "dispatch-exit" ]; then
      exit 7
    elif [ "$scenario" = "static-dropped-slots" ]; then
      correctness="$review_tmp/codex-specialist-correctness-output.txt"
      edge_cases="$review_tmp/codex-specialist-edge-cases-output.txt"
      testing="$review_tmp/cursor-specialist-testing-output.txt"
      printf 'review output\n' >"$correctness"
      printf 'review output\n' >"$edge_cases"
      printf 'review output\n' >"$testing"
      printf '{"agent":"codex","output":"%s"}\n{"agent":"codex","output":"%s"}\n{"agent":"cursor","output":"%s"}\n' "$correctness" "$edge_cases" "$testing" >"$review_tmp/panel-manifest.ndjson"
      printf 'ignored\ndyn-specialist\tcodex\tstraggler-dropped\nedge-cases\tcodex\tstraggler-dropped\ntesting\tcursor\ttool-absent\ncorrectness\tcodex\treviewer-failed\n' >"$review_tmp/dropped-slots.tsv"
      printf 'PANEL_MODE=waterfall\nPANEL_SHAPE=hard\nPANEL_TIER=MODERATE\nPANEL_MANIFEST=%s/panel-manifest.ndjson\nEXTERNAL_OUTPUT_FILES=%s %s %s\nDROPPED_SLOTS_FILE=%s/dropped-slots.tsv\n' "$review_tmp" "$correctness" "$edge_cases" "$testing" "$review_tmp"
    elif [ "$scenario" != "static-coverage-failure" ]; then
      : >"$review_tmp/panel-manifest.ndjson"
      printf 'PANEL_MODE=waterfall\nPANEL_SHAPE=hard\nPANEL_TIER=MODERATE\nPANEL_MANIFEST=%s/panel-manifest.ndjson\n' "$review_tmp"
    else
      printf 'PANEL_MODE=waterfall\nPANEL_SHAPE=hard\nPANEL_TIER=MODERATE\n'
    fi
    if [ "$scenario" = "pruned-empty" ]; then
      printf 'SCOUT_STATUS=na\nDYNAMIC_SLOTS=0\nSTATIC_SLOT_COUNT=0\nPANEL_PRUNED_EMPTY=true\nPRUNE_STATUS=pruned-empty\nSLOT_COUNT=1\nLAUNCHED_SLOTS=1\n'
    else
      printf 'SCOUT_STATUS=na\nDYNAMIC_SLOTS=0\nSTATIC_SLOT_COUNT=0\nPANEL_PRUNED_EMPTY=false\nSLOT_COUNT=1\nLAUNCHED_SLOTS=1\n'
    fi
    if [ "$scenario" = "collect-bootstrap-failure" ]; then
      rm "$0"
    fi
    ;;
  review:collect-findings)
    if [ "$scenario" = "threshold-no-output" ]; then
      printf 'FINDINGS_COUNT=1\n'
      exit 0
    fi
    if [ "$scenario" = "parseable-no-collector" ]; then
      printf '### FINDING_1: correctness: source: detail\n- **Reviewer(s)**: alpha\n- **Concern**: concrete\n' >"$findings"
      : >"$oos"
      printf 'FINDINGS_COUNT=0\n'
      exit 0
    fi
    if [ "$scenario" = "static-dropped-slots" ]; then
      correctness="$review_tmp/codex-specialist-correctness-output.txt"
      edge_cases="$review_tmp/codex-specialist-edge-cases-output.txt"
      testing="$review_tmp/cursor-specialist-testing-output.txt"
      printf 'REVIEWER_FILE=%s\nSTATUS=OK\n\nREVIEWER_FILE=%s\nSTATUS=NOT_SUBSTANTIVE\n\nREVIEWER_FILE=%s\nSTATUS=OK\n' "$correctness" "$edge_cases" "$testing" >"$(dirname "$findings")/collector-results.env"
      : >"$findings"
      : >"$oos"
      printf 'FINDINGS_COUNT=0\n'
      exit 0
    fi
    if [ "$scenario" = "proposer-map-failure" ]; then
      printf '### FINDING_1: correctness: source: detail\n- **Concern**: missing reviewer\n' >"$findings"
    else
      printf '### FINDING_1: correctness: source: detail\n- **Reviewer(s)**: alpha\n- **Concern**: concrete\n' >"$findings"
    fi
    : >"$oos"
    printf 'REVIEWER_FILE=none\nSTATUS=OK\n' >"$(dirname "$findings")/collector-results.env"
    printf 'FINDINGS_COUNT=1\n'
    ;;
  review:check-reviewer-failure-threshold)
    printf 'THRESHOLD_OK=true\nTHRESHOLD_REASON=\nNOT_SUBSTANTIVE_SLOTS=0\n'
    ;;
  review:prune-nit-findings)
    printf 'PRUNED_COUNT=0\nINSCOPE_REMAINING=1\nSTATUS=ok\n'
    if [ "$scenario" = "aggregate-bootstrap-failure" ]; then
      rm "$0"
    fi
    ;;
  review:aggregate-findings)
    if [ "$scenario" = "aggregate-zero" ]; then
      printf 'REASON=ok\nMERGED_COUNT=0\n'
    else
      printf 'REASON=ok\nMERGED_COUNT=1\n'
    fi
    ;;
  agent:dispatch-voters)
    mkdir -p "$review_tmp"
    for index in 1 2 3; do
      voter="$review_tmp/voter-$index.txt"
      printf 'vote\n' >"$voter"
      printf 'VOTER_%s_PATH=%s\nVOTER_%s_STATUS=complete\nVOTER_%s_TOOL=codex-voter-%s\n' "$index" "$voter" "$index" "$index" "$index"
    done
    if [ "$scenario" = "tally-bootstrap-failure" ]; then
      rm "$0"
    fi
    ;;
  review:tally-code-votes)
    if [ "$scenario" = "tally-failure" ]; then
      exit 7
    fi
    classification="$review_tmp/classification.tsv"
    printf 'FINDING_1\taccepted\n' >"$classification"
    printf 'TALLY_STATUS=ok\nACCEPTED_COUNT=1\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\nOUT_OF_SCOPE_DRIFT_COUNT=0\nFINDINGS_CLASSIFICATION_TSV_FILE=%s\n' "$classification"
    ;;
  review:reviewer-prune)
    printf 'fixture prune warning\n' >&2
    exit 1
    ;;
  review:emit-tally|run-log:write-round|progress:note|timing:record-vendor-task)
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
"#,
    )
    .expect("fixture bootstrap");
    fs::set_permissions(&bootstrap, fs::Permissions::from_mode(0o755))
        .expect("fixture bootstrap mode");
    plugin
}

fn run_core_with_args(
    fixture: &TempDir,
    plugin: &Path,
    scenario: &str,
    mode: &str,
    extra_args: &[&str],
) -> Output {
    fs::write(plugin.join("scenario"), scenario).expect("scenario");
    let review = fixture.path().join(format!("review-{scenario}"));
    let session = fixture
        .path()
        .join(format!("session-{scenario}/session-env.sh"));
    let implementation = fixture.path().join(format!("implementation-{scenario}"));
    let timing = fixture.path().join(format!("timing-{scenario}.tsv"));
    fs::create_dir_all(session.parent().expect("session parent")).expect("session parent");
    fs::create_dir_all(&implementation).expect("implementation");
    fs::write(&timing, "header\n").expect("timing ledger");

    let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
    command
        .env("CLAUDE_PLUGIN_ROOT", plugin)
        .env("IMPLEMENT_TMPDIR", &implementation)
        .env("LARCH_RUN_ID", "run-8445")
        .env("LARCH_TIMING_LEDGER", &timing);
    if scenario == "session-run-id" {
        fs::write(&session, "export LARCH_RUN_ID=session-run-id\n").expect("session run id");
        command.env_remove("LARCH_RUN_ID");
    }
    if scenario == "timing-ledger-fallback" {
        fs::write(implementation.join("timing-ledger.tsv"), "header\n")
            .expect("fallback timing ledger");
        command.env_remove("LARCH_TIMING_LEDGER");
    }
    command
        .args(["review", "core", "--mode", mode, "--output-dir"])
        .arg(&review)
        .args([
            "--codex-available",
            "true",
            "--cursor-available",
            "true",
            "--session-env-path",
        ])
        .arg(&session)
        .args(["--run-id", "run-8445", "--prune-ledger"])
        .arg(review.join("prune-ledger.tsv"))
        .args(extra_args)
        .output()
        .expect("run review core")
}

fn run_core(fixture: &TempDir, plugin: &Path, scenario: &str) -> Output {
    run_core_with_args(fixture, plugin, scenario, "diff", &[])
}

fn stdout(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

#[test]
fn core_runs_the_verified_nested_round_and_lifecycle_hooks() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let review = fixture.path().join("review-success");
    fs::create_dir_all(&review).expect("review fixture");
    fs::write(
        review.join("competition-notice.md"),
        "competition context\n",
    )
    .expect("competition notice");
    let output = run_core(&fixture, &plugin, "success");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let rendered = stdout(&output);
    assert!(rendered.contains("REVIEW_CORE_STATUS=fix-required"));
    assert!(rendered.contains("ACCEPTED_COUNT=1"));
    assert!(rendered.contains("FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_1="));
}

#[test]
fn core_replays_snapshot_when_aggregation_returns_zero_merges() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = run_core(&fixture, &plugin, "aggregate-zero");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(stdout(&output).contains("REVIEW_CORE_STATUS=fix-required"));
}

#[test]
fn core_short_circuits_a_description_with_no_in_scope_files() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = run_core_with_args(&fixture, &plugin, "description-empty", "description", &[]);

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(stdout(&output).contains("REVIEW_CORE_STATUS=zero-findings"));
}

#[test]
fn core_reports_a_fully_pruned_panel_without_collecting_outputs() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = run_core(&fixture, &plugin, "pruned-empty");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(stdout(&output).contains("REVIEW_CORE_STATUS=prune-skipped"));
}

#[test]
fn core_preserves_dispatch_process_failures_in_its_public_envelope() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = run_core(&fixture, &plugin, "dispatch-exit");

    assert_eq!(output.status.code(), Some(2));
    assert!(stdout(&output).contains("THRESHOLD_REASON=dispatch-panel exited rc=7"));
}

#[test]
fn core_preserves_dispatch_bootstrap_failures_in_its_public_envelope() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = run_core(&fixture, &plugin, "dispatch-bootstrap-failure");

    assert_eq!(output.status.code(), Some(2));
    assert!(stdout(&output).contains("THRESHOLD_REASON=dispatch-panel failed:"));
}

#[test]
fn core_preserves_gather_bootstrap_failures_in_its_public_envelope() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = fixture.path().join("missing-plugin");
    fs::create_dir_all(&plugin).expect("missing plugin root");
    let review = fixture.path().join("review");
    let output = Command::new(env!("CARGO_BIN_EXE_larch"))
        .env("CLAUDE_PLUGIN_ROOT", &plugin)
        .args(["review", "core", "--mode", "diff", "--output-dir"])
        .arg(review)
        .args(["--codex-available", "true", "--cursor-available", "true"])
        .output()
        .expect("run review core with missing bootstrap");

    assert_eq!(output.status.code(), Some(2));
    assert!(stdout(&output).contains("THRESHOLD_REASON=gather-context failed:"));
}

#[test]
fn core_preserves_collector_and_aggregator_bootstrap_failures() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let collector = run_core(&fixture, &plugin, "collect-bootstrap-failure");
    assert_eq!(collector.status.code(), Some(2));
    assert!(stdout(&collector).contains("REVIEW_CORE_STATUS=panel-failed"));

    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let aggregator = run_core(&fixture, &plugin, "aggregate-bootstrap-failure");
    assert_eq!(aggregator.status.code(), Some(2));
    assert!(stdout(&aggregator).contains("REVIEW_CORE_STATUS=panel-failed"));
}

#[test]
fn core_preserves_voting_tally_bootstrap_failures() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = run_core(&fixture, &plugin, "tally-bootstrap-failure");

    assert_eq!(output.status.code(), Some(2));
    assert!(stdout(&output).contains("THRESHOLD_REASON=tally-code-votes failed"));
}

#[test]
fn core_uses_session_and_fallback_timing_lifecycle_inputs() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let session_run_id = run_core(&fixture, &plugin, "session-run-id");
    assert!(
        session_run_id.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&session_run_id.stderr)
    );

    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let timing_fallback = run_core(&fixture, &plugin, "timing-ledger-fallback");
    assert!(
        timing_fallback.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&timing_fallback.stderr)
    );
}

#[test]
fn core_allows_parseable_output_when_collector_metadata_is_unavailable() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = run_core(&fixture, &plugin, "parseable-no-collector");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let threshold = fixture
        .path()
        .join("review-parseable-no-collector/review-core-threshold.env");
    assert!(
        fs::read_to_string(threshold)
            .expect("threshold artifact")
            .contains("COVERAGE_GATE_REASON=parseable reviewer output present")
    );
}

#[test]
fn core_accepts_static_reviewer_slot_exceptions_only_when_accounted_for() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = run_core(&fixture, &plugin, "static-dropped-slots");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(stdout(&output).contains("REVIEW_CORE_STATUS=zero-findings"));
}

#[test]
fn core_enforces_argument_grammar_and_the_round_cap_before_running_reviewers() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let capped = run_core_with_args(
        &fixture,
        &plugin,
        "round-two",
        "diff",
        &["--round-num", "2"],
    );

    assert!(
        capped.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&capped.stderr)
    );
    assert!(stdout(&capped).contains("REVIEW_CORE_STATUS=cap-reached"));

    let unknown = Command::new(env!("CARGO_BIN_EXE_larch"))
        .env("CLAUDE_PLUGIN_ROOT", &plugin)
        .args(["review", "core", "--unknown", "value"])
        .output()
        .expect("run unknown-option review core");
    assert_eq!(unknown.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&unknown.stderr).contains("unknown option: --unknown"));

    let missing = Command::new(env!("CARGO_BIN_EXE_larch"))
        .env("CLAUDE_PLUGIN_ROOT", &plugin)
        .args(["review", "core", "--mode"])
        .output()
        .expect("run missing-value review core");
    assert_eq!(missing.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&missing.stderr).contains("--mode requires a value"));
}

#[test]
fn core_fails_closed_when_the_requested_output_directory_is_a_file() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output_path = fixture.path().join("not-a-directory");
    fs::write(&output_path, "file").expect("output-file fixture");
    let output = Command::new(env!("CARGO_BIN_EXE_larch"))
        .env("CLAUDE_PLUGIN_ROOT", &plugin)
        .args(["review", "core", "--mode", "diff", "--output-dir"])
        .arg(output_path)
        .args(["--codex-available", "true", "--cursor-available", "true"])
        .output()
        .expect("run review core with file output");

    assert_eq!(output.status.code(), Some(2));
    assert!(stdout(&output).contains("THRESHOLD_REASON=review output directory failed:"));
}

#[test]
fn core_short_circuits_when_the_voting_tally_fails() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = run_core(&fixture, &plugin, "tally-failure");

    assert_eq!(output.status.code(), Some(2));
    assert!(stdout(&output).contains("THRESHOLD_REASON=tally-code-votes failed"));
}

#[test]
fn core_short_circuits_when_the_ballot_cannot_be_neutralized() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = run_core(&fixture, &plugin, "proposer-map-failure");

    assert_eq!(output.status.code(), Some(2));
    assert!(stdout(&output).contains("THRESHOLD_REASON=proposer-map-failed"));
}

#[test]
fn core_fails_closed_without_any_collector_or_parseable_output() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = run_core(&fixture, &plugin, "threshold-no-output");

    assert_eq!(output.status.code(), Some(2));
    assert!(stdout(&output).contains("THRESHOLD_REASON=no successful launched reviewer output"));
}

#[test]
fn core_fails_closed_when_static_reviewer_coverage_is_missing() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = run_core(&fixture, &plugin, "static-coverage-failure");

    assert_eq!(output.status.code(), Some(2));
    assert!(stdout(&output).contains("no successful static reviewer for archetype(s):"));
}

#[test]
fn core_rejects_invalid_public_arguments_before_spawning_the_bootstrap() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = install_plugin(fixture.path());
    let output = Command::new(env!("CARGO_BIN_EXE_larch"))
        .env("CLAUDE_PLUGIN_ROOT", &plugin)
        .args([
            "review",
            "core",
            "--mode",
            "not-a-mode",
            "--output-dir",
            "/tmp/review",
            "--codex-available",
            "true",
            "--cursor-available",
            "true",
            "--tier",
            "trivial",
        ])
        .output()
        .expect("run invalid review core");

    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("Usage: review core"));
}
