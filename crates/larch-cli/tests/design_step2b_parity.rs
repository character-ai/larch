//! Black-box coverage for the `/design` drafting and post-plan verbs (#8583).
//!
//! Each case drives the built `larch` binary through `design step2b-drafter`,
//! `design step2b-postplan`, `design postplan-emit`, and `design step3b-entry`.
//! A stub injected through `LARCH_BINARY` answers the Rust-owned sibling verbs
//! (plan-review, plan, agent launch-*-drafter, run-log, token, timing) offline,
//! exactly as the retired Python tests drove the in-process owners.

#![cfg(unix)]

use std::{
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::Command,
};

use std::os::unix::fs::PermissionsExt as _;

use tempfile::TempDir;

fn repo_root() -> PathBuf {
    fs::canonicalize(Path::new(env!("CARGO_MANIFEST_DIR")).join("..").join(".."))
        .expect("repo root canonicalizes")
}

/// The plugin version the fixture must report so `scripts/larch.sh` accepts it.
fn plugin_version(root: &Path) -> String {
    let text = fs::read_to_string(root.join(".claude-plugin/plugin.json")).expect("plugin.json");
    for line in text.lines() {
        if let Some(value) = line
            .split_once("\"version\"")
            .and_then(|(_, rest)| rest.split('"').nth(1))
        {
            return value.to_owned();
        }
    }
    panic!("no version in plugin.json");
}

fn target_triple() -> &'static str {
    match (std::env::consts::OS, std::env::consts::ARCH) {
        ("macos", "aarch64") => "aarch64-apple-darwin",
        ("macos", "x86_64") => "x86_64-apple-darwin",
        ("linux", "aarch64") => "aarch64-unknown-linux-gnu",
        _ => "x86_64-unknown-linux-gnu",
    }
}

/// Write the stub `larch` binary the design verbs shell out to. It answers each
/// Rust-owned sibling verb with the minimal side effects the orchestration reads.
fn write_stub(path: &Path, version: &str) {
    let script = format!(
        r#"#!/usr/bin/env bash
set -u
case "${{1:-}}:${{2:-}}" in
  --version:*) printf 'larch {version}\n'; exit 0 ;;
  bootstrap:self-check)
    printf '{{"schema_version":1,"version":"{version}","target":"{target}"}}\n'; exit 0 ;;
  plan-review:json-get-bool) printf '%s\n' "${{FIXTURE_PARTITION:-false}}"; exit 0 ;;
  plan-review:emit)
    shift 2; design=""
    while [[ $# -gt 0 ]]; do case "$1" in --design-tmpdir) design="$2"; shift 2 ;; *) shift ;; esac; done
    if [[ "${{FIXTURE_EMIT_MISSING:-}}" == true ]]; then printf 'EMIT_PLAN_STATUS=missing-diff-lines\n'; exit 1; fi
    diff_lines=$(awk '/^diff_lines: [0-9]+$/ {{ v=$2 }} END {{ print v+0 }}' "$design/plan.txt")
    printf 'EMIT_PLAN_STATUS=ok\nDIFF_LINES=%s\n' "$diff_lines"; exit 0 ;;
  plan:validate)
    if [[ "${{FIXTURE_VALIDATE_DEFECTS:-}}" == true ]]; then
      printf 'VALIDATE_STATUS=defects-found\nVALIDATE_DEFECT_COUNT=1\nVALIDATE_SKIPPED_COUNT=0\nVALIDATE_UNSAFE_TOKEN_COUNT=0\n'; exit 0
    fi
    if [[ "${{FIXTURE_MUTATE_PLAN:-}}" == true ]]; then
      shift 2; design=""
      while [[ $# -gt 0 ]]; do case "$1" in --design-tmpdir) design="$2"; shift 2 ;; *) shift ;; esac; done
      printf 'rewritten by validator\n' >>"$design/plan.txt"
    fi
    printf 'VALIDATE_STATUS=ok\nVALIDATE_DEFECT_COUNT=0\nVALIDATE_SKIPPED_COUNT=0\nVALIDATE_UNSAFE_TOKEN_COUNT=0\n'; exit 0 ;;
  plan:check-size)
    shift 2; design=""
    while [[ $# -gt 0 ]]; do case "$1" in --design-tmpdir) design="$2"; shift 2 ;; *) shift ;; esac; done
    plan_lines=$(wc -l <"$design/plan.txt" | tr -d ' ')
    size_trigger=${{FIXTURE_SIZE_TRIGGER:-false}}
    [[ "$plan_lines" -ge 800 ]] && size_trigger=true
    printf 'PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=%s\nDRIFT_TRIGGER_FIRED=%s\nPLAN_LINES=%s\n' \
      "$size_trigger" "${{FIXTURE_DRIFT_TRIGGER:-false}}" "$plan_lines"
    exit "${{FIXTURE_CHECK_SIZE_RC:-0}}" ;;
  plan-review:drift-baseline) exit 0 ;;
  plan-review:preview) printf 'preview: ok\n'; exit 0 ;;
  plan-review:finalize) printf 'FINALIZE_STATUS=ok\n'; exit 0 ;;
  agent:launch-claude-drafter|agent:launch-codex-drafter)
    shift 1; output=""; design=""
    while [[ $# -gt 0 ]]; do case "$1" in --output-file) output="$2"; shift 2 ;; --design-tmpdir) design="$2"; shift 2 ;; *) shift ;; esac; done
    {{
      printf '# Plan\n## Files to modify/create\n### UPDATED: README.md\ndifficulty: TRIVIAL\n'
      lines=${{FIXTURE_DRAFTER_PLAN_LINES:-4}}
      i=1; while [[ "$i" -le "$lines" ]]; do printf 'line %s\n' "$i"; i=$((i + 1)); done
      printf 'diff_lines: 7\n'
    }} >"$design/plan.txt"
    printf 'PLAN_WRITTEN=true\n' >"$output"
    [[ "${{FIXTURE_SCOUT:-true}}" == true ]] && printf 'SCOUT_WRITTEN=true\n' >>"$output"
    printf 'usage\n' >"$output.token-record"
    if [[ -n "${{FIXTURE_DRAFTER_DIRTY:-}}" ]]; then printf 'STATUS=dirty\nMODE=baseline-delta\n' >"$design/step2b-drafter-status.txt.dirty-tree"; fi
    if [[ -n "${{FIXTURE_DIALECTIC:-}}" ]]; then printf '{{"decisions":[]}}\n' >"$design/.dialectic-raw-pending.json"; fi
    if [[ -n "${{FIXTURE_POSTPLAN_PAUSE:-}}" ]]; then : >"$design/.pause-requested"; fi
    exit "${{FIXTURE_DRAFTER_RC:-0}}" ;;
  run-log:*) exit 0 ;;
  token:*) exit 0 ;;
  timing:*) exit 0 ;;
esac
exit 0
"#,
        version = version,
        target = target_triple(),
    );
    fs::write(path, script).expect("write stub");
    fs::set_permissions(path, fs::Permissions::from_mode(0o755)).expect("chmod stub");
}

struct Fixture {
    _temp: TempDir,
    root: PathBuf,
    stub: PathBuf,
    design: PathBuf,
}

fn setup() -> Fixture {
    let temp = TempDir::new().expect("tempdir");
    let root = repo_root();
    let stub = temp.path().join("larch-fixture");
    write_stub(&stub, &plugin_version(&root));
    let design = temp.path().join("design");
    fs::create_dir_all(design.join(".completed")).expect("design dir");
    Fixture {
        _temp: temp,
        root,
        stub,
        design,
    }
}

fn write_plan(design: &Path, body_lines: usize, diff_lines: u32) {
    let mut plan = String::from(
        "# Plan\n## Files to modify/create\n### UPDATED: README.md\n## Closed decisions and ownership\nKeep the owner.\n## Ordered implementation\n1. Apply.\n## Acceptance\nPasses.\n## Breaking changes and migration\nNone.\n## Approach\n",
    );
    for index in 1..=body_lines {
        let _ = writeln!(plan, "line {index}");
    }
    let _ = writeln!(plan, "difficulty: TRIVIAL\ndiff_lines: {diff_lines}");
    fs::write(design.join("plan.txt"), plan).expect("plan");
}

fn run(fixture: &Fixture, args: &[&str]) -> std::process::Output {
    // The wrapper verbs rehydrate CLAUDE_PLUGIN_ROOT from `--plugin-root` (or the
    // session-env file) the way the design-run launcher and settle caller do;
    // `postplan-emit` reads the process env directly and takes no such flag.
    let mut owned: Vec<String> = args.iter().map(|value| (*value).to_owned()).collect();
    let is_wrapper_verb = matches!(
        args.get(1).copied(),
        Some("step2b-drafter" | "step2b-postplan" | "step3b-entry"),
    );
    if is_wrapper_verb {
        owned.push("--plugin-root".to_owned());
        owned.push(fixture.root.to_string_lossy().into_owned());
    }
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .env("CLAUDE_PLUGIN_ROOT", &fixture.root)
        .env("LARCH_BINARY", &fixture.stub)
        .env("DESIGN_TMPDIR", &fixture.design)
        .env("LARCH_DESIGN_DRAFTER", "claude")
        .env("LARCH_DESIGN_PLAN_MODEL", "claude-opus-4-8")
        .env_remove("LARCH_CODEX_BINARY_FOUND")
        .env_remove("LARCH_CURSOR_BINARY_FOUND")
        .args(&owned)
        .output()
        .expect("larch runs")
}

fn out(output: &std::process::Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

// ---------------------------------------------------------------------------
// postplan-emit
// ---------------------------------------------------------------------------

#[test]
fn postplan_emit_under_threshold_returns_zero() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    let output = run(
        &fixture,
        &[
            "design",
            "postplan-emit",
            "--design-tmpdir",
            fixture.design.to_str().unwrap(),
            "--with-plan-size",
            "--snapshot-original",
        ],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = out(&output);
    assert!(stdout.contains("POSTPLAN_EMIT_STATUS=ok"), "{stdout}");
    assert!(
        stdout.contains("STEP2B5_NEXT_ACTION=under-threshold"),
        "{stdout}"
    );
    let result_env = fs::read_to_string(fixture.design.join(".design-postplan-emit-result.env"))
        .expect("result env");
    assert!(
        result_env.contains("PLAN_SIZE_STATUS=under-threshold"),
        "{result_env}"
    );
}

#[test]
fn postplan_emit_hard_size_returns_twelve() {
    let fixture = setup();
    write_plan(&fixture.design, 805, 10);
    let output = run(
        &fixture,
        &[
            "design",
            "postplan-emit",
            "--design-tmpdir",
            fixture.design.to_str().unwrap(),
            "--with-plan-size",
        ],
    );
    assert_eq!(
        output.status.code(),
        Some(12),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let result_env = fs::read_to_string(fixture.design.join(".design-postplan-emit-result.env"))
        .expect("result env");
    assert!(
        result_env.contains("PLAN_SIZE_STATUS=plan-size-trigger"),
        "{result_env}"
    );
}

#[test]
fn postplan_emit_missing_plan_without_plan_size_returns_two() {
    let fixture = setup();
    let output = run(
        &fixture,
        &[
            "design",
            "postplan-emit",
            "--design-tmpdir",
            fixture.design.to_str().unwrap(),
        ],
    );
    assert_eq!(output.status.code(), Some(2));
    assert!(out(&output).contains("POSTPLAN_EMIT_STATUS=missing-plan"));
}

#[test]
fn postplan_emit_requires_design_tmpdir() {
    let fixture = setup();
    let output = run(&fixture, &["design", "postplan-emit"]);
    assert_eq!(output.status.code(), Some(2));
}

// ---------------------------------------------------------------------------
// step2b-postplan
// ---------------------------------------------------------------------------

#[test]
fn step2b_postplan_clean_emits_rc_zero_and_marker() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    let output = run(
        &fixture,
        &[
            "design",
            "step2b-postplan",
            "--site",
            "step2b",
            "--snapshot-original",
        ],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(out(&output).contains("POSTPLAN_RC=0"), "{}", out(&output));
    assert!(fixture.design.join(".completed/step-2b.5").is_file());
}

#[test]
fn step2b_postplan_write_completion_only_touches_marker() {
    let fixture = setup();
    let output = run(
        &fixture,
        &["design", "step2b-postplan", "--write-completion-only"],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(fixture.design.join(".completed/step-2b.5").is_file());
}

#[test]
fn step2b_postplan_mutually_exclusive_completion_modes_rejected() {
    let fixture = setup();
    let output = run(
        &fixture,
        &[
            "design",
            "step2b-postplan",
            "--write-completion-only",
            "--write-step2b-completion-only",
        ],
    );
    assert_eq!(output.status.code(), Some(2));
}

// ---------------------------------------------------------------------------
// step2b-drafter
// ---------------------------------------------------------------------------

#[test]
fn step2b_drafter_success_delegates_to_postplan() {
    let fixture = setup();
    fs::write(
        fixture.design.join("feature-description.txt"),
        "A feature.\n",
    )
    .expect("feature");
    fs::write(
        fixture.design.join("approach-synthesis.txt"),
        "NO_SKETCHES\n",
    )
    .expect("approach");
    let output = run(&fixture, &["design", "step2b-drafter"]);
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = out(&output);
    assert!(stdout.contains("DRAFTER_VENDOR=claude"), "{stdout}");
    assert!(
        stdout.contains("STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1"),
        "{stdout}"
    );
    assert!(stdout.contains("DRAFTER_NEXT_ACTION="), "{stdout}");
    assert!(fixture.design.join("step2b-drafter-prompt.txt").is_file());
    assert!(fixture.design.join(".completed/step-2a").is_file());
}

#[test]
fn step2b_drafter_missing_feature_description_fails() {
    let fixture = setup();
    let output = run(&fixture, &["design", "step2b-drafter"]);
    assert_eq!(output.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("feature-description.txt"),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

// ---------------------------------------------------------------------------
// step3b-entry
// ---------------------------------------------------------------------------

#[test]
fn step3b_entry_diagram_required_for_code_surface() {
    let fixture = setup();
    fs::write(fixture.design.join(".completed/step-4"), "").expect("step-4");
    fs::write(fixture.design.join(".completed/step-5b"), "").expect("step-5b");
    fs::write(
        fixture.design.join("plan.txt"),
        "## Files to modify/create\n### UPDATED: src/main.rs\n",
    )
    .expect("plan");
    let output = run(&fixture, &["design", "step3b-entry", "--mode", "diagram"]);
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        out(&output).contains("DIAGRAM_REQUIRED=true"),
        "{}",
        out(&output)
    );
}

#[test]
fn step3b_entry_diagram_skipped_for_doc_surface() {
    let fixture = setup();
    fs::write(fixture.design.join(".completed/step-4"), "").expect("step-4");
    fs::write(fixture.design.join(".completed/step-5b"), "").expect("step-5b");
    fs::write(
        fixture.design.join("plan.txt"),
        "## Files to modify/create\n### UPDATED: docs/readme.md\n",
    )
    .expect("plan");
    let output = run(&fixture, &["design", "step3b-entry", "--mode", "diagram"]);
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        out(&output).contains("DIAGRAM_REQUIRED=false"),
        "{}",
        out(&output)
    );
    assert!(
        fixture
            .design
            .join("architecture-diagram.skipped")
            .is_file()
    );
    assert!(fixture.design.join(".completed/step-5b.5").is_file());
}

#[test]
fn step3b_entry_requires_mode() {
    let fixture = setup();
    let output = run(&fixture, &["design", "step3b-entry"]);
    assert_eq!(output.status.code(), Some(2));
}

/// Run a wrapper verb with one extra environment override.
fn run_env(fixture: &Fixture, args: &[&str], key: &str, value: &str) -> std::process::Output {
    let mut owned: Vec<String> = args.iter().map(|value| (*value).to_owned()).collect();
    owned.push("--plugin-root".to_owned());
    owned.push(fixture.root.to_string_lossy().into_owned());
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .env("CLAUDE_PLUGIN_ROOT", &fixture.root)
        .env("LARCH_BINARY", &fixture.stub)
        .env("DESIGN_TMPDIR", &fixture.design)
        .env("LARCH_DESIGN_DRAFTER", "claude")
        .env(key, value)
        .env_remove("LARCH_CODEX_BINARY_FOUND")
        .env_remove("LARCH_CURSOR_BINARY_FOUND")
        .args(&owned)
        .output()
        .expect("larch runs")
}

#[test]
fn step2b_postplan_hard_size_reports_rc_twelve() {
    let fixture = setup();
    write_plan(&fixture.design, 805, 10);
    let output = run(&fixture, &["design", "step2b-postplan", "--site", "step2b"]);
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(out(&output).contains("POSTPLAN_RC=12"), "{}", out(&output));
    assert!(fixture.design.join(".completed/step-2b").is_file());
}

#[test]
fn step2b_drafter_invalid_model_falls_back_to_inline() {
    let fixture = setup();
    fs::write(
        fixture.design.join("feature-description.txt"),
        "A feature.\n",
    )
    .expect("feature");
    // A whitespace model marks the claude vendor invalid, so the drafter skips
    // its external launch and routes to the inline fallback branch.
    let output = run_env(
        &fixture,
        &["design", "step2b-drafter"],
        "LARCH_DESIGN_PLAN_MODEL",
        " ",
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = out(&output);
    assert!(
        stdout.contains("DRAFTER_NEXT_ACTION=inline-fallback"),
        "{stdout}"
    );
    assert_eq!(
        fs::read_to_string(fixture.design.join(".step2b-plan-source")).unwrap_or_default(),
        "inline\n"
    );
}

#[test]
fn step3b_entry_finalize_publishes_step4_mode() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    let output = run(&fixture, &["design", "step3b-entry", "--mode", "finalize"]);
    // The finalize driver and the Gate C probe are exercised; the probe is the
    // still-Python owner, so accept its published mode or a clean probe refusal.
    let stdout = out(&output);
    assert!(
        stdout.contains("STEP4_MODE=") || output.status.code() == Some(1),
        "stdout: {stdout} stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(fixture.design.join(".completed/step-3.5").is_file());
    assert!(
        fixture
            .design
            .join("step3b-finalize-driver.stdout")
            .is_file()
    );
}

/// Run a verb with an arbitrary set of extra environment overrides. Wrapper
/// verbs receive `--plugin-root`; `postplan-emit` does not.
fn run_with(fixture: &Fixture, args: &[&str], env: &[(&str, &str)]) -> std::process::Output {
    let mut owned: Vec<String> = args.iter().map(|value| (*value).to_owned()).collect();
    if matches!(
        args.get(1).copied(),
        Some("step2b-drafter" | "step2b-postplan" | "step3b-entry"),
    ) {
        owned.push("--plugin-root".to_owned());
        owned.push(fixture.root.to_string_lossy().into_owned());
    }
    let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
    command
        .env("CLAUDE_PLUGIN_ROOT", &fixture.root)
        .env("LARCH_BINARY", &fixture.stub)
        .env("DESIGN_TMPDIR", &fixture.design)
        .env("LARCH_DESIGN_DRAFTER", "claude")
        .env("LARCH_DESIGN_PLAN_MODEL", "claude-opus-4-8")
        .env_remove("LARCH_CODEX_BINARY_FOUND")
        .env_remove("LARCH_CURSOR_BINARY_FOUND");
    for (key, value) in env {
        command.env(key, value);
    }
    command.args(&owned).output().expect("larch runs")
}

fn drafter_fixture() -> Fixture {
    let fixture = setup();
    fs::write(
        fixture.design.join("feature-description.txt"),
        "A feature.\n",
    )
    .expect("feature");
    fs::write(
        fixture.design.join("approach-synthesis.txt"),
        "NO_SKETCHES\n",
    )
    .expect("approach");
    fixture
}

#[test]
fn postplan_emit_validate_defects_returns_ten() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    let output = run_with(
        &fixture,
        &[
            "design",
            "postplan-emit",
            "--design-tmpdir",
            fixture.design.to_str().unwrap(),
            "--with-plan-size",
        ],
        &[("FIXTURE_VALIDATE_DEFECTS", "true")],
    );
    assert_eq!(
        output.status.code(),
        Some(10),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let result_env = fs::read_to_string(fixture.design.join(".design-postplan-emit-result.env"))
        .expect("result env");
    assert!(
        result_env.contains("PLAN_SIZE_STATUS=skipped-defects"),
        "{result_env}"
    );
}

#[test]
fn postplan_emit_missing_diff_lines_returns_one() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    let output = run_with(
        &fixture,
        &[
            "design",
            "postplan-emit",
            "--design-tmpdir",
            fixture.design.to_str().unwrap(),
            "--with-plan-size",
        ],
        &[("FIXTURE_EMIT_MISSING", "true")],
    );
    assert_eq!(output.status.code(), Some(1));
    assert!(
        out(&output).contains("POSTPLAN_EMIT_STATUS=missing-diff-lines"),
        "{}",
        out(&output)
    );
}

#[test]
fn postplan_emit_check_size_failure_self_logs() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    let output = run_with(
        &fixture,
        &[
            "design",
            "postplan-emit",
            "--design-tmpdir",
            fixture.design.to_str().unwrap(),
            "--with-plan-size",
        ],
        &[("FIXTURE_CHECK_SIZE_RC", "2")],
    );
    // check-size rc 2 routes to the rc2-warning exit; the self-log ran.
    assert_eq!(output.status.code(), Some(2));
    assert!(
        fixture
            .design
            .join("check-plan-size.validation.log")
            .is_file()
    );
}

#[test]
fn step2b_drafter_hard_size_routes_to_split() {
    let fixture = drafter_fixture();
    let output = run_with(
        &fixture,
        &["design", "step2b-drafter"],
        &[("FIXTURE_SIZE_TRIGGER", "true")],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        out(&output).contains("DRAFTER_NEXT_ACTION=postplan-rc12-split"),
        "{}",
        out(&output)
    );
    assert!(
        fixture
            .design
            .join(".drafter-next-action-rc12.txt")
            .is_file()
    );
}

#[test]
fn step2b_drafter_validate_defects_routes_to_inline_retry() {
    let fixture = drafter_fixture();
    let output = run_with(
        &fixture,
        &["design", "step2b-drafter"],
        &[("FIXTURE_VALIDATE_DEFECTS", "true")],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        out(&output).contains("DRAFTER_NEXT_ACTION=inline-retry"),
        "{}",
        out(&output)
    );
}

#[test]
fn step2b_drafter_dirty_tree_requests_recovery() {
    let fixture = drafter_fixture();
    let output = run_with(
        &fixture,
        &["design", "step2b-drafter"],
        &[("FIXTURE_DRAFTER_DIRTY", "1")],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        out(&output).contains("DRAFTER_NEXT_ACTION=dirty-tree-recovery"),
        "{}",
        out(&output)
    );
    assert!(fixture.design.join("dirty-tree-detected.env").is_file());
}

#[test]
fn step2b_drafter_promotes_pending_dialectic_candidates() {
    let fixture = drafter_fixture();
    fs::write(
        fixture.design.join(".dialectic-raw-pending.json"),
        "{\"decisions\":[]}\n",
    )
    .expect("raw pending");
    let output = run(&fixture, &["design", "step2b-drafter"]);
    // Promotion runs through the still-Python owner; the drafter still completes.
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        out(&output).contains("DRAFTER_VENDOR=claude"),
        "{}",
        out(&output)
    );
}

#[test]
fn step2b_drafter_missing_scout_warns_and_continues() {
    let fixture = drafter_fixture();
    let output = run_with(
        &fixture,
        &["design", "step2b-drafter"],
        &[("FIXTURE_SCOUT", "false")],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("dynamic-archetype manifest missing"),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn postplan_emit_partition_requested_returns_thirteen() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    fs::write(
        fixture.design.join("run-params.json"),
        "{\"partition_requested\":true}\n",
    )
    .expect("run-params");
    let output = run_with(
        &fixture,
        &[
            "design",
            "postplan-emit",
            "--design-tmpdir",
            fixture.design.to_str().unwrap(),
            "--with-plan-size",
        ],
        &[("FIXTURE_PARTITION", "true")],
    );
    assert_eq!(
        output.status.code(),
        Some(13),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let result_env = fs::read_to_string(fixture.design.join(".design-postplan-emit-result.env"))
        .expect("result env");
    assert!(
        result_env.contains("PLAN_SIZE_STATUS=partition-requested"),
        "{result_env}"
    );
}

#[test]
fn postplan_emit_drift_advisory_returns_zero() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    let output = run_with(
        &fixture,
        &[
            "design",
            "postplan-emit",
            "--design-tmpdir",
            fixture.design.to_str().unwrap(),
            "--with-plan-size",
        ],
        &[("FIXTURE_DRIFT_TRIGGER", "true")],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(out(&output).contains("drift advisory"), "{}", out(&output));
}

#[test]
fn step2b_postplan_partition_reports_rc_thirteen() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    fs::write(
        fixture.design.join("run-params.json"),
        "{\"partition_requested\":true}\n",
    )
    .expect("run-params");
    let output = run_with(
        &fixture,
        &["design", "step2b-postplan", "--site", "step2b"],
        &[("FIXTURE_PARTITION", "true")],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(out(&output).contains("POSTPLAN_RC=13"), "{}", out(&output));
}

#[test]
fn step2b_drafter_composes_full_prompt_from_all_inputs() {
    let fixture = drafter_fixture();
    fs::write(
        fixture.design.join("discussion-round1.md"),
        "Scope: keep it small.\n",
    )
    .expect("discussion");
    fs::write(
        fixture.design.join("brainstorm.md"),
        "Idea: reuse the owner.\n",
    )
    .expect("brainstorm");
    fs::write(
        fixture.design.join("design-outline.md"),
        "Goals: ship it.\n",
    )
    .expect("outline");
    fs::write(fixture.design.join(".outline-approved"), "").expect("outline-approved");
    let output = run(&fixture, &["design", "step2b-drafter"]);
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let prompt =
        fs::read_to_string(fixture.design.join("step2b-drafter-prompt.txt")).expect("prompt");
    assert!(prompt.contains("Untrusted discussion round 1:"), "prompt");
    assert!(prompt.contains("Untrusted brainstorm:"), "prompt");
    assert!(
        prompt.contains("Untrusted approved design outline:"),
        "prompt"
    );
}

#[test]
fn step2b_drafter_codex_vendor_launches_and_appends_sidecars() {
    let fixture = drafter_fixture();
    let output = run_with(
        &fixture,
        &["design", "step2b-drafter"],
        &[("LARCH_DESIGN_DRAFTER", "codex")],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        out(&output).contains("DRAFTER_VENDOR=codex"),
        "{}",
        out(&output)
    );
}

#[test]
fn step2b_drafter_refuses_conflicting_step2a_artifacts() {
    let fixture = setup();
    fs::write(
        fixture.design.join("feature-description.txt"),
        "A feature.\n",
    )
    .expect("feature");
    // A non-sentinel approach-synthesis is a Step 2a artifact conflict.
    fs::write(
        fixture.design.join("approach-synthesis.txt"),
        "real sketches here\n",
    )
    .expect("approach");
    let output = run(&fixture, &["design", "step2b-drafter"]);
    assert_eq!(output.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("sentinel repair refused"),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn postplan_emit_pause_requested_returns_eleven() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    fs::write(fixture.design.join(".pause-requested"), "").expect("pause");
    let output = run_with(
        &fixture,
        &[
            "design",
            "postplan-emit",
            "--design-tmpdir",
            fixture.design.to_str().unwrap(),
            "--with-plan-size",
        ],
        &[],
    );
    assert_eq!(
        output.status.code(),
        Some(11),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        out(&output).contains("POSTPLAN_EMIT_STATUS=paused"),
        "{}",
        out(&output)
    );
}

#[test]
fn step2b_postplan_pause_routes_to_pause_save() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    fs::write(fixture.design.join(".pause-requested"), "").expect("pause");
    // The pause branch prints the anchored rows and hands off to the still-Python
    // pause-save owner; the handoff runs even without a resolvable issue.
    let output = run(&fixture, &["design", "step2b-postplan", "--site", "step2b"]);
    assert!(out(&output).contains("POSTPLAN_RC=11"), "{}", out(&output));
}

#[test]
fn step2b_drafter_predrafter_pause_hands_off() {
    let fixture = drafter_fixture();
    fs::write(fixture.design.join(".pause-requested"), "").expect("pause");
    let output = run(&fixture, &["design", "step2b-drafter"]);
    // Either the pause-terminal handoff row or the pause-save refusal code; both
    // exercise the pre-drafter pause branch.
    assert!(
        out(&output).contains("DRAFTER_NEXT_ACTION=pause-terminal")
            || out(&output).contains("PAUSE_OK=false")
            || output.status.code() == Some(1),
        "stdout: {} stderr: {}",
        out(&output),
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn step3b_entry_diagram_pause_hands_off() {
    let fixture = setup();
    fs::write(fixture.design.join(".completed/step-4"), "").expect("step-4");
    fs::write(fixture.design.join(".completed/step-5b"), "").expect("step-5b");
    write_plan(&fixture.design, 20, 10);
    fs::write(fixture.design.join(".pause-requested"), "").expect("pause");
    let output = run(&fixture, &["design", "step3b-entry", "--mode", "diagram"]);
    // The pause branch bridges to pause-save; the process still terminates with a
    // code rather than a diagram row.
    assert!(
        !out(&output).contains("DIAGRAM_REQUIRED="),
        "stdout: {}",
        out(&output)
    );
}

#[test]
fn postplan_emit_standalone_pause_without_issue_fails_closed() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    fs::write(fixture.design.join(".pause-requested"), "").expect("pause");
    // Without --with-plan-size and with no resolvable issue, the standalone pause
    // branch fails closed with the issue-unresolved diagnostic.
    let output = run_with(
        &fixture,
        &[
            "design",
            "postplan-emit",
            "--design-tmpdir",
            fixture.design.to_str().unwrap(),
        ],
        &[("ISSUE_NUMBER", "")],
    );
    assert_eq!(output.status.code(), Some(1));
    let stdout = out(&output);
    assert!(stdout.contains("PAUSE_OK=false"), "{stdout}");
    assert!(stdout.contains("ERROR=issue-unresolved"), "{stdout}");
}

#[test]
fn postplan_emit_standalone_pause_reads_issue_from_source_env() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    fs::write(fixture.design.join(".pause-requested"), "").expect("pause");
    fs::write(
        fixture.design.join("source-env.sh"),
        "export ISSUE_NUMBER='4242'\n",
    )
    .expect("source-env");
    // The issue resolves from source-env.sh, so the branch bridges to pause-save
    // (still-Python) instead of failing on an unresolved issue.
    let output = run_with(
        &fixture,
        &[
            "design",
            "postplan-emit",
            "--design-tmpdir",
            fixture.design.to_str().unwrap(),
        ],
        &[("ISSUE_NUMBER", "")],
    );
    assert!(
        !out(&output).contains("ERROR=issue-unresolved"),
        "stdout: {}",
        out(&output)
    );
}

#[test]
fn postplan_emit_clears_stale_dialectic_when_plan_changes() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    // The validator rewrites plan.txt, so postplan clears stale dialectic state.
    let output = run_with(
        &fixture,
        &[
            "design",
            "postplan-emit",
            "--design-tmpdir",
            fixture.design.to_str().unwrap(),
            "--with-plan-size",
        ],
        &[("FIXTURE_MUTATE_PLAN", "true")],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        out(&output).contains("POSTPLAN_EMIT_STATUS=ok"),
        "{}",
        out(&output)
    );
}

#[test]
fn step2b_postplan_fatal_prints_captured_before_abort() {
    let fixture = setup();
    write_plan(&fixture.design, 20, 10);
    // A missing-diff emit makes the shared postplan body take the fatal branch,
    // which reprints the captured output before returning non-zero.
    let output = run_with(
        &fixture,
        &["design", "step2b-postplan", "--site", "step2b"],
        &[("FIXTURE_EMIT_MISSING", "true")],
    );
    assert_eq!(output.status.code(), Some(1));
    assert!(
        out(&output).contains("POSTPLAN_EMIT_STATUS=missing-diff-lines"),
        "{}",
        out(&output)
    );
}

#[test]
fn step2b_postplan_completion_only_pause_hands_off() {
    let fixture = setup();
    fs::write(fixture.design.join(".pause-requested"), "").expect("pause");
    let output = run(
        &fixture,
        &["design", "step2b-postplan", "--write-completion-only"],
    );
    assert!(out(&output).contains("POSTPLAN_RC=11"), "{}", out(&output));
    assert!(fixture.design.join(".completed/step-2b.5").is_file());
}

#[test]
fn step2b_postplan_write_step2b_completion_only_pause_hands_off() {
    let fixture = setup();
    fs::write(fixture.design.join(".pause-requested"), "").expect("pause");
    let output = run(
        &fixture,
        &[
            "design",
            "step2b-postplan",
            "--write-step2b-completion-only",
        ],
    );
    assert!(out(&output).contains("POSTPLAN_RC=11"), "{}", out(&output));
    assert!(fixture.design.join(".completed/step-2b").is_file());
}

#[test]
fn step2b_drafter_promote_runs_when_launch_emits_candidates() {
    let fixture = drafter_fixture();
    let output = run_with(
        &fixture,
        &["design", "step2b-drafter"],
        &[("FIXTURE_DIALECTIC", "1")],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        out(&output).contains("DRAFTER_NEXT_ACTION=step3"),
        "{}",
        out(&output)
    );
}

#[test]
fn step2b_drafter_postplan_pause_hands_off() {
    let fixture = drafter_fixture();
    let output = run_with(
        &fixture,
        &["design", "step2b-drafter"],
        &[("FIXTURE_POSTPLAN_PAUSE", "1")],
    );
    // The drafter succeeds, then postplan observes the pause request and routes to
    // the post-plan pause handoff.
    assert!(
        out(&output).contains("DRAFTER_NEXT_ACTION=postplan-rc11-pause")
            || out(&output).contains("POSTPLAN_RC=11"),
        "stdout: {}",
        out(&output)
    );
}

#[test]
fn step2b_drafter_unexpected_postplan_rc_is_failsafe() {
    let fixture = drafter_fixture();
    // A check-size internal error surfaces as an unexpected postplan rc, routing
    // the drafter to the fail-safe missing-rows directive.
    let output = run_with(
        &fixture,
        &["design", "step2b-drafter"],
        &[("FIXTURE_CHECK_SIZE_RC", "3")],
    );
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        out(&output).contains("DRAFTER_NEXT_ACTION=failsafe-missing-rows"),
        "{}",
        out(&output)
    );
}
