use std::{
    env, fs,
    os::unix::fs::PermissionsExt as _,
    path::Path,
    process::{Command, Output},
};

use tempfile::TempDir;

fn output(root: &Path, args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .current_dir(root)
        .env("CLAUDE_PROJECT_DIR", root)
        .args(args)
        .output()
        .expect("run larch")
}

fn git(root: &Path, args: &[&str]) -> Output {
    Command::new("git")
        .current_dir(root)
        .args(args)
        .output()
        .expect("run git")
}

fn git_success(root: &Path, args: &[&str]) {
    let output = git(root, args);
    assert!(
        output.status.success(),
        "git {args:?}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

fn repository(fixture: &TempDir) -> std::path::PathBuf {
    let root = fixture.path().join("repository");
    fs::create_dir_all(&root).expect("repository root");
    git_success(&root, &["init", "--quiet"]);
    git_success(&root, &["config", "user.name", "Larch Test"]);
    git_success(
        &root,
        &["config", "user.email", "larch-test@example.invalid"],
    );
    fs::write(root.join("tracked.txt"), "before\n").expect("tracked file");
    git_success(&root, &["add", "tracked.txt"]);
    git_success(&root, &["commit", "--quiet", "-m", "initial"]);
    root
}

#[allow(clippy::literal_string_with_formatting_args)] // The shell fixture deliberately uses `${...}` expansion.
fn plugin(root: &Path) -> std::path::PathBuf {
    let plugin = root.join("plugin");
    let scripts = plugin.join("scripts");
    fs::create_dir_all(&scripts).expect("fixture scripts");
    let bootstrap = scripts.join("larch.sh");
    fs::write(
        &bootstrap,
        r#"#!/bin/sh
set -eu
domain=${1:-}
verb=${2:-}
shift 2 || true
case "$domain:$verb" in
  token:mark|timing:mark) exit 0 ;;
  git:commit) exec git commit "$@" ;;
  *) exit 0 ;;
esac
"#,
    )
    .expect("fixture bootstrap");
    fs::set_permissions(&bootstrap, fs::Permissions::from_mode(0o755))
        .expect("fixture bootstrap mode");
    plugin
}

#[allow(clippy::literal_string_with_formatting_args)] // The shell fixture deliberately uses `${...}` expansion.
fn step5_plugin(root: &Path) -> std::path::PathBuf {
    let plugin = root.join("step5-plugin");
    let scripts = plugin.join("scripts");
    fs::create_dir_all(&scripts).expect("fixture scripts");
    let bootstrap = scripts.join("larch.sh");
    fs::write(
        &bootstrap,
        r#"#!/bin/sh
set -eu
domain=${1:-}
verb=${2:-}
shift 2 || true
case "$domain:$verb" in
  timing:mark|git:snapshot-untracked|run-log:write|run-log:write-round|voting:write-tally) exit 0 ;;
  timing:record-round)
    ledger=""
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --ledger) ledger=$2; shift 2 ;;
        *) shift ;;
      esac
    done
    : > "$ledger.recorded"
    exit 0
    ;;
  review:core)
    output_dir=""
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --output-dir) output_dir=$2; shift 2 ;;
        *) shift ;;
      esac
    done
    printf '%s\n' '### FINDING_1: update tracked content' '- **Suggested revision**: update it.' > "$output_dir/accepted-findings.md"
    : > "$output_dir/findings.md"
    : > "$output_dir/rejected-findings.md"
    printf 'REVIEW_CORE_STATUS=fix-required\nACCEPTED_COUNT=1\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\nACCEPTED_FINDINGS_FILE=%s\nREJECTED_FINDINGS_FILE=%s\n' "$output_dir/accepted-findings.md" "$output_dir/rejected-findings.md"
    ;;
  review:compose-findings)
    output=""
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --output) output=$2; shift 2 ;;
        *) shift ;;
      esac
    done
    : > "$output"
    ;;
  agent:launch-codex-exec)
    output=""
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --output) output=$2; shift 2 ;;
        *) shift ;;
      esac
    done
    printf 'APPLIED: FINDING_1\n' > "$output"
    printf '%s|%s|%s\n' "${LARCH_TOKEN_SESSION_ID:-}" "${LARCH_TIMING_LEDGER:-}" "${LARCH_TIMING_SKILL:-}" > "${output%/*}/coder-context.txt"
    printf 'after\n' > tracked.txt
    ;;
  git:commit) exec git commit "$@" ;;
  *) exit 0 ;;
esac
"#,
    )
    .expect("fixture bootstrap");
    fs::set_permissions(&bootstrap, fs::Permissions::from_mode(0o755))
        .expect("fixture bootstrap mode");
    plugin
}

#[test]
fn apply_findings_empty_preserves_the_no_findings_envelope() {
    let fixture = TempDir::new().expect("fixture");
    let root = repository(&fixture);
    let findings = fixture.path().join("findings.md");
    let review = fixture.path().join("review");
    fs::write(&findings, "").expect("findings");

    let result = output(
        &root,
        &[
            "review-and-fix",
            "apply-findings",
            "--findings-file",
            findings.to_str().expect("findings path"),
            "--review-tmpdir",
            review.to_str().expect("review path"),
        ],
    );

    assert!(result.status.success());
    assert_eq!(
        String::from_utf8_lossy(&result.stdout),
        "REVIEW_AND_FIX_STATUS=no-findings\nFIX_COUNT=0\nCODER_TOOL=none\nCODER_STATUS=skipped\nSUBMODULE_SCRUB_COUNT=0\nSUBMODULE_REVERT_COUNT=0\n",
    );
}

#[test]
fn apply_findings_rehydrates_session_context_and_uses_its_flat_timing_ledger() {
    let fixture = TempDir::new().expect("fixture");
    let root = repository(&fixture);
    let findings = fixture.path().join("findings.md");
    let review = fixture.path().join("review");
    let session = fixture.path().join("session-env.sh");
    fs::write(
        &findings,
        "### FINDING_1: update tracked content\n- **Suggested revision**: update it.\n",
    )
    .expect("findings");
    fs::write(
        &session,
        "CODEX_BINARY_FOUND=true\nCURSOR_BINARY_FOUND=false\nLARCH_TOKEN_SESSION_ID=flat-repair-session\nLARCH_TIMING_LEDGER=/tmp/stale-ledger.tsv\n",
    )
    .expect("session");
    let fixture_plugin = step5_plugin(fixture.path());
    let bin = fixture.path().join("bin");
    fs::create_dir_all(&bin).expect("fixture bin");
    let codex = bin.join("codex");
    fs::write(&codex, "#!/bin/sh\nexit 0\n").expect("codex stub");
    fs::set_permissions(&codex, fs::Permissions::from_mode(0o755)).expect("codex mode");
    let system_path = env::var_os("PATH").expect("PATH");
    let path =
        env::join_paths(std::iter::once(bin).chain(env::split_paths(&system_path))).expect("PATH");

    let result = Command::new(env!("CARGO_BIN_EXE_larch"))
        .current_dir(&root)
        .env("CLAUDE_PROJECT_DIR", &root)
        .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin)
        .env("PATH", path)
        .args([
            "review-and-fix",
            "apply-findings",
            "--findings-file",
            findings.to_str().expect("findings path"),
            "--review-tmpdir",
            review.to_str().expect("review path"),
            "--session-env-path",
            session.to_str().expect("session path"),
        ])
        .output()
        .expect("apply findings");

    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    assert!(String::from_utf8_lossy(&result.stdout).contains("REVIEW_AND_FIX_STATUS=complete\n"));
    assert_eq!(
        fs::read_to_string(review.join("coder-context.txt")).expect("coder session context"),
        format!(
            "flat-repair-session|{}|\n",
            review.join("timing-ledger.tsv").display()
        )
    );
}

#[test]
fn check_changes_ignores_preexisting_untracked_files_without_a_baseline() {
    let fixture = TempDir::new().expect("fixture");
    let root = repository(&fixture);
    fs::write(root.join("preexisting.tmp"), "before\n").expect("preexisting untracked file");

    let no_baseline = output(&root, &["review-and-fix", "check-changes"]);
    assert!(no_baseline.status.success());
    assert_eq!(
        String::from_utf8_lossy(&no_baseline.stdout),
        "FILES_CHANGED=false\nUNTRACKED_BASELINE=missing\nGIT_PROBE_FAILED=false\n",
    );

    let baseline = fixture.path().join("untracked-baseline.txt");
    fs::write(&baseline, "preexisting.tmp\n").expect("baseline");
    fs::write(root.join("new.tmp"), "after\n").expect("new untracked file");
    let with_baseline = output(
        &root,
        &[
            "review-and-fix",
            "check-changes",
            "--baseline",
            baseline.to_str().expect("baseline path"),
        ],
    );
    assert!(with_baseline.status.success());
    assert_eq!(
        String::from_utf8_lossy(&with_baseline.stdout),
        "FILES_CHANGED=true\nUNTRACKED_BASELINE=present\nGIT_PROBE_FAILED=false\n",
    );
}

#[test]
fn check_changes_preserves_the_non_parser_help_failure_envelope() {
    let fixture = TempDir::new().expect("fixture");
    let root = repository(&fixture);

    let result = output(&root, &["review-and-fix", "check-changes", "--help"]);

    assert!(result.status.success());
    assert_eq!(
        String::from_utf8_lossy(&result.stderr),
        "ERROR=Unknown argument: --help\n"
    );
    assert_eq!(
        String::from_utf8_lossy(&result.stdout),
        "FILES_CHANGED=false\nUNTRACKED_BASELINE=missing\nGIT_PROBE_FAILED=false\n"
    );
}

#[test]
fn step5_preflight_failure_persists_the_stall_envelope() {
    let fixture = TempDir::new().expect("fixture");
    let root = repository(&fixture);
    let implementation = fixture.path().join("implementation");
    fs::create_dir_all(&implementation).expect("implementation");

    let result = output(
        &root,
        &[
            "review-and-fix",
            "step5",
            "--implement-tmpdir",
            implementation.to_str().expect("implementation path"),
            "--mode",
            "loop",
        ],
    );

    assert_eq!(result.status.code(), Some(2));
    let stdout = String::from_utf8_lossy(&result.stdout);
    assert!(stdout.contains("STEP5_REVIEW_STATUS=stall\n"));
    assert!(stdout.contains("STALL_REASON=preflight-failed\n"));
    let persisted = fs::read_to_string(implementation.join(".step5-review-result.env"))
        .expect("persisted envelope");
    assert_eq!(persisted, stdout);
}

#[test]
fn step5_loop_commits_the_coder_delta_and_persists_its_complete_transcript() {
    let fixture = TempDir::new().expect("fixture");
    let root = repository(&fixture);
    fs::write(root.join("tracked.txt"), "before-coder\n").expect("preexisting change");
    git_success(&root, &["add", "tracked.txt"]);
    let implementation = fixture.path().join("implementation");
    fs::create_dir_all(&implementation).expect("implementation");
    fs::write(
        implementation.join("session-env.sh"),
        "RUN_ID=review-and-fix-test\nCODEX_BINARY_FOUND=true\nCURSOR_BINARY_FOUND=false\nLARCH_TOKEN_SESSION_ID=repair-session\nLARCH_TIMING_LEDGER=/tmp/repair-ledger.tsv\n",
    )
    .expect("session env");
    fs::write(implementation.join("plan.txt"), "plan\n").expect("plan");
    fs::write(implementation.join("feature-description.txt"), "feature\n").expect("feature");
    let fixture_plugin = step5_plugin(fixture.path());
    let bin = fixture.path().join("bin");
    fs::create_dir_all(&bin).expect("fixture bin");
    let codex = bin.join("codex");
    fs::write(&codex, "#!/bin/sh\nexit 0\n").expect("codex stub");
    fs::set_permissions(&codex, fs::Permissions::from_mode(0o755)).expect("codex mode");
    let system_path = env::var_os("PATH").expect("PATH");
    let path =
        env::join_paths(std::iter::once(bin).chain(env::split_paths(&system_path))).expect("PATH");

    let result = Command::new(env!("CARGO_BIN_EXE_larch"))
        .current_dir(&root)
        .env("CLAUDE_PROJECT_DIR", &root)
        .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin)
        .env("PATH", path)
        .args([
            "review-and-fix",
            "step5",
            "--implement-tmpdir",
            implementation.to_str().expect("implementation path"),
            "--mode",
            "loop",
            "--codex-available",
            "true",
            "--cursor-available",
            "false",
        ])
        .output()
        .expect("step5");

    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    let transcript = "STEP5_REVIEW_STATUS=complete\nSTALL_TRACKING=false\nSTALL_REASON=\nROUNDS_COMPLETED=1\nFINAL_ROUND_NUM=1\nFINAL_REVIEW_AND_FIX_STATUS=fix-applied\nCODER_STATUS=applied\nFILES_CHANGED_HINT=";
    let stdout = String::from_utf8_lossy(&result.stdout);
    assert!(stdout.starts_with(transcript), "{stdout}");
    assert!(
        stdout.contains("EFFECTIVE_ROUND_CAP=2\nPANEL_TIER=MODERATE\nAUDIT_UPGRADE=false\n"),
        "{stdout}"
    );
    assert_eq!(
        fs::read_to_string(implementation.join(".step5-review-result.env"))
            .expect("persisted transcript"),
        stdout,
    );
    assert_eq!(
        fs::read_to_string(root.join("tracked.txt")).expect("tracked content"),
        "after\n"
    );
    assert_eq!(
        fs::read_to_string(implementation.join("round-1/coder-context.txt"))
            .expect("coder session context"),
        format!(
            "repair-session|{}|\n",
            implementation.join("timing-ledger.tsv").display()
        )
    );
    assert_eq!(
        String::from_utf8_lossy(&git(&root, &["show", "--format=", "--name-only", "HEAD"]).stdout),
        "tracked.txt\n"
    );
    assert!(implementation.join("progress/done").is_file());
    assert!(implementation.join("round-1/round-start-s").is_file());
    assert!(implementation.join("timing-ledger.tsv.recorded").is_file());
}

#[test]
fn normalize_status_replays_and_persists_the_captured_envelope() {
    let fixture = TempDir::new().expect("fixture");
    let root = repository(&fixture);
    let implementation = fixture.path().join("implementation");
    fs::create_dir_all(&implementation).expect("implementation");
    let captured = fixture.path().join("captured.out");
    let transcript = "STEP5_REVIEW_STATUS=complete\nSTALL_TRACKING=false\nSTALL_REASON=\nROUNDS_COMPLETED=1\nFINAL_ROUND_NUM=1\nFINAL_REVIEW_AND_FIX_STATUS=complete\nCODER_STATUS=skipped\nFILES_CHANGED_HINT=\nEFFECTIVE_ROUND_CAP=2\n";
    fs::write(&captured, transcript).expect("captured transcript");

    let result = output(
        &root,
        &[
            "review-and-fix",
            "normalize-status",
            "--implement-tmpdir",
            implementation.to_str().expect("implementation path"),
            "--stdout-file",
            captured.to_str().expect("captured path"),
            "--loop-rc",
            "7",
        ],
    );

    assert_eq!(result.status.code(), Some(7));
    assert_eq!(String::from_utf8_lossy(&result.stdout), transcript);
    assert_eq!(
        fs::read_to_string(implementation.join(".step5-review-result.env"))
            .expect("persisted envelope"),
        transcript,
    );
}

#[test]
fn self_review_snapshot_commits_only_its_delta() {
    let fixture = TempDir::new().expect("fixture");
    let root = repository(&fixture);
    let implementation = fixture.path().join("implementation");
    fs::create_dir_all(&implementation).expect("implementation");
    let fixture_plugin = plugin(fixture.path());

    let snapshot = Command::new(env!("CARGO_BIN_EXE_larch"))
        .current_dir(&root)
        .env("CLAUDE_PROJECT_DIR", &root)
        .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin)
        .args([
            "review-and-fix",
            "write-pre-self-review-snapshot",
            "--implement-tmpdir",
            implementation.to_str().expect("implementation path"),
        ])
        .output()
        .expect("write snapshot");
    assert!(
        snapshot.status.success(),
        "{}",
        String::from_utf8_lossy(&snapshot.stderr)
    );

    fs::write(root.join("tracked.txt"), "after\n").expect("review edit");
    fs::write(
        implementation.join("self-review-accepted.md"),
        "### [Code Review] Self-review accepted\n",
    )
    .expect("accepted marker");
    let commit = Command::new(env!("CARGO_BIN_EXE_larch"))
        .current_dir(&root)
        .env("CLAUDE_PROJECT_DIR", &root)
        .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin)
        .env("IMPLEMENT_TMPDIR", &implementation)
        .args(["review-and-fix", "commit-fixes", "--stage-all"])
        .output()
        .expect("commit review delta");
    assert!(
        commit.status.success(),
        "{}",
        String::from_utf8_lossy(&commit.stderr)
    );
    assert!(String::from_utf8_lossy(&commit.stdout).contains("COMMIT_OUTCOME=ok\n"));
    let files = git(&root, &["show", "--format=", "--name-only", "HEAD"]);
    assert_eq!(String::from_utf8_lossy(&files.stdout), "tracked.txt\n");
}

#[test]
fn self_review_snapshot_replaces_stale_patch_artifacts() {
    let fixture = TempDir::new().expect("fixture");
    let root = repository(&fixture);
    let implementation = fixture.path().join("implementation");
    fs::create_dir_all(&implementation).expect("implementation");
    let args = [
        "review-and-fix",
        "write-pre-self-review-snapshot",
        "--implement-tmpdir",
        implementation.to_str().expect("implementation path"),
    ];

    let first = output(&root, &args);
    assert!(
        first.status.success(),
        "{}",
        String::from_utf8_lossy(&first.stderr)
    );
    let stale = implementation.join("self-review-snapshot/pre-self-review-path-diffs/stale");
    fs::write(&stale, "stale\n").expect("stale patch artifact");

    let second = output(&root, &args);
    assert!(
        second.status.success(),
        "{}",
        String::from_utf8_lossy(&second.stderr)
    );
    assert!(!stale.exists());
}
