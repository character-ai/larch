#[rustfmt::skip] mod implementation { #![allow(clippy::literal_string_with_formatting_args)] use std::{ env, fs, os::unix::fs::PermissionsExt as _, path::Path, process::{Command, Output}, }; use tempfile::TempDir; fn output(root: &Path, args: &[&str]) -> Output { Command::new(env!("CARGO_BIN_EXE_larch")) .current_dir(root) .env("CLAUDE_PROJECT_DIR", root) .args(args) .output() .expect("run larch") } fn git(root: &Path, args: &[&str]) -> Output { Command::new("git") .current_dir(root)
.args(args) .output() .expect("run git") } fn git_success(root: &Path, args: &[&str]) { let output = git(root, args); assert!( output.status.success(), "git {args:?}: {}", String::from_utf8_lossy(&output.stderr) ); } fn repository(fixture: &TempDir) -> std::path::PathBuf { let root = fixture.path().join("repository"); fs::create_dir_all(&root).expect("repository root"); git_success(&root, &["init", "--quiet"]); git_success(&root,
&["config", "user.name", "Larch Test"]); git_success( &root, &["config", "user.email", "larch-test@example.invalid"], ); fs::write(root.join("tracked.txt"), "before\n").expect("tracked file"); git_success(&root, &["add", "tracked.txt"]); git_success(&root, &["commit", "--quiet", "-m", "initial"]); root } #[allow(clippy::literal_string_with_formatting_args)] // The shell fixture deliberately uses `${...}` expansion.
fn plugin(root: &Path) -> std::path::PathBuf { let plugin = root.join("plugin"); let scripts = plugin.join("scripts"); fs::create_dir_all(&scripts).expect("fixture scripts"); let bootstrap = scripts.join("larch.sh"); fs::write( &bootstrap, r#"#!/bin/sh
set -eu
domain=${1:-}
verb=${2:-}
shift 2 || true
case "$domain:$verb" in
  token:mark|timing:mark) exit 0 ;;
  git:commit) exec git commit "$@" ;;
  *) exit 0 ;;
esac
"#, ) .expect("fixture bootstrap"); fs::set_permissions(&bootstrap, fs::Permissions::from_mode(0o755)) .expect("fixture bootstrap mode"); plugin } #[allow(clippy::literal_string_with_formatting_args)] // The shell fixture deliberately uses `${...}` expansion.
fn step5_plugin(root: &Path) -> std::path::PathBuf { let plugin = root.join("step5-plugin"); let scripts = plugin.join("scripts"); fs::create_dir_all(&scripts).expect("fixture scripts"); let bootstrap = scripts.join("larch.sh"); fs::write( &bootstrap, r#"#!/bin/sh
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
    if [ ! -f "$output_dir/../omit-findings" ]; then : > "$output_dir/findings.md"; fi
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
"#, ) .expect("fixture bootstrap"); fs::set_permissions(&bootstrap, fs::Permissions::from_mode(0o755)) .expect("fixture bootstrap mode"); plugin } #[test] fn apply_findings_empty_preserves_the_no_findings_envelope() { let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); let findings = fixture.path().join("findings.md"); let review = fixture.path().join("review"); fs::write(&findings, "").expect("findings");
let result = output( &root, &[ "review-and-fix", "apply-findings", "--findings-file", findings.to_str().expect("findings path"), "--review-tmpdir", review.to_str().expect("review path"), ], ); assert!(result.status.success()); assert_eq!( String::from_utf8_lossy(&result.stdout), "REVIEW_AND_FIX_STATUS=no-findings\nFIX_COUNT=0\nCODER_TOOL=none\nCODER_STATUS=skipped\nSUBMODULE_SCRUB_COUNT=0\nSUBMODULE_REVERT_COUNT=0\n",
); } #[test] fn apply_findings_scrubs_submodule_locations_without_regex_runtime_failure() { let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); fs::write( root.join(".gitmodules"), "[submodule \"vendor\"]\n\tpath = vendor/dependency\n\turl = example.invalid/repo\n", ) .expect("gitmodules"); let findings = fixture.path().join("findings.md"); let review = fixture.path().join("review"); fs::write(
&findings, "### FINDING_1: forbidden submodule edit\n- **Location**: vendor/dependency/src/lib.rs\n- **Suggested revision**: update it.\n", ) .expect("findings"); let result = output( &root, &[ "review-and-fix", "apply-findings", "--findings-file", findings.to_str().expect("findings path"), "--review-tmpdir", review.to_str().expect("review path"), ], ); assert!( result.status.success(), "{}", String::from_utf8_lossy(&result.stderr)
); let stdout = String::from_utf8_lossy(&result.stdout); assert!( stdout.contains("REVIEW_AND_FIX_STATUS=complete\n"), "{stdout}" ); assert!(stdout.contains("FIX_COUNT=0\n"), "{stdout}"); assert!(stdout.contains("SUBMODULE_SCRUB_COUNT=1\n"), "{stdout}"); } #[test] fn apply_findings_rehydrates_session_context_and_uses_its_flat_timing_ledger() { let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture);
let findings = fixture.path().join("findings.md"); let review = fixture.path().join("review"); let session = fixture.path().join("session-env.sh"); fs::write( &findings, "### FINDING_1: update tracked content\n- **Suggested revision**: update it.\n", ) .expect("findings"); fs::write( &session, "CODEX_BINARY_FOUND=true\nCURSOR_BINARY_FOUND=false\nLARCH_TOKEN_SESSION_ID=flat-repair-session\nLARCH_TIMING_LEDGER=/tmp/stale-ledger.tsv\n",
) .expect("session"); let fixture_plugin = step5_plugin(fixture.path()); let bin = fixture.path().join("bin"); fs::create_dir_all(&bin).expect("fixture bin"); let codex = bin.join("codex"); fs::write(&codex, "#!/bin/sh\nexit 0\n").expect("codex stub"); fs::set_permissions(&codex, fs::Permissions::from_mode(0o755)).expect("codex mode"); let system_path = env::var_os("PATH").expect("PATH"); let path = env::join_paths(std::iter::once(bin).chain(env::split_paths(&system_path))).expect("PATH");
let result = Command::new(env!("CARGO_BIN_EXE_larch")) .current_dir(&root) .env("CLAUDE_PROJECT_DIR", &root) .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin) .env("PATH", path) .args([ "review-and-fix", "apply-findings", "--findings-file", findings.to_str().expect("findings path"), "--review-tmpdir", review.to_str().expect("review path"), "--session-env-path", session.to_str().expect("session path"), ]) .output() .expect("apply findings");
assert!( result.status.success(), "{}", String::from_utf8_lossy(&result.stderr) ); assert!(String::from_utf8_lossy(&result.stdout).contains("REVIEW_AND_FIX_STATUS=complete\n")); assert_eq!( fs::read_to_string(review.join("coder-context.txt")).expect("coder session context"), format!( "flat-repair-session|{}|\n", review.join("timing-ledger.tsv").display() ) ); } #[test] fn check_changes_ignores_preexisting_untracked_files_without_a_baseline()
{ let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); fs::write(root.join("preexisting.tmp"), "before\n").expect("preexisting untracked file"); let no_baseline = output(&root, &["review-and-fix", "check-changes"]); assert!(no_baseline.status.success()); assert_eq!( String::from_utf8_lossy(&no_baseline.stdout), "FILES_CHANGED=false\nUNTRACKED_BASELINE=missing\nGIT_PROBE_FAILED=false\n", );
let baseline = fixture.path().join("untracked-baseline.txt"); fs::write(&baseline, "preexisting.tmp\n").expect("baseline"); fs::write(root.join("new.tmp"), "after\n").expect("new untracked file"); let with_baseline = output( &root, &[ "review-and-fix", "check-changes", "--baseline", baseline.to_str().expect("baseline path"), ], ); assert!(with_baseline.status.success()); assert_eq!( String::from_utf8_lossy(&with_baseline.stdout),
"FILES_CHANGED=true\nUNTRACKED_BASELINE=present\nGIT_PROBE_FAILED=false\n", ); } #[test] fn check_changes_preserves_the_non_parser_help_failure_envelope() { let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); let result = output(&root, &["review-and-fix", "check-changes", "--help"]); assert!(result.status.success()); assert_eq!( String::from_utf8_lossy(&result.stderr), "ERROR=Unknown argument: --help\n"
); assert_eq!( String::from_utf8_lossy(&result.stdout), "FILES_CHANGED=false\nUNTRACKED_BASELINE=missing\nGIT_PROBE_FAILED=false\n" ); } #[test] fn step5_preflight_failure_persists_the_stall_envelope() { let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); let implementation = fixture.path().join("implementation"); fs::create_dir_all(&implementation).expect("implementation"); let result = output(
&root, &[ "review-and-fix", "step5", "--implement-tmpdir", implementation.to_str().expect("implementation path"), "--mode", "loop", ], ); assert_eq!(result.status.code(), Some(2)); let stdout = String::from_utf8_lossy(&result.stdout); assert!(stdout.contains("STEP5_REVIEW_STATUS=stall\n")); assert!(stdout.contains("STALL_REASON=preflight-failed\n")); let persisted = fs::read_to_string(implementation.join(".step5-review-result.env"))
.expect("persisted envelope"); assert_eq!(persisted, stdout); } #[test] fn step5_classifier_diagnostic_is_tee_d_to_the_round_stderr_sidecar() { let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); let implementation = fixture.path().join("implementation"); fs::create_dir_all(&implementation).expect("implementation"); fs::write( implementation.join("session-env.sh"), "RUN_ID=classifier-test\nCODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=false\n",
) .expect("session env"); fs::write(implementation.join("plan.txt"), "plan\n").expect("plan"); fs::write(implementation.join("feature-description.txt"), "feature\n").expect("feature"); fs::write(implementation.join("omit-findings"), "").expect("missing findings marker"); let fixture_plugin = step5_plugin(fixture.path()); let result = Command::new(env!("CARGO_BIN_EXE_larch")) .current_dir(&root) .env("CLAUDE_PROJECT_DIR",
&root) .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin) .env( "PATH", env::join_paths([ std::path::PathBuf::from("/usr/bin"), std::path::PathBuf::from("/bin"), ]) .expect("PATH"), ) .args([ "review-and-fix", "step5", "--implement-tmpdir", implementation.to_str().expect("implementation path"), "--mode", "single", "--round-num", "1", "--codex-available", "false", "--cursor-available", "false", ]) .output() .expect("single round");
assert_eq!(result.status.code(), Some(2)); assert!( String::from_utf8_lossy(&result.stdout) .contains("REVIEW_AND_FIX_STATUS=classifier-failed\n") ); let diagnostic = "review-and-fix: findings file not readable for Important check:"; assert!(String::from_utf8_lossy(&result.stderr).contains(diagnostic)); assert!( fs::read_to_string(implementation.join("round-1/review-and-fix.stderr")) .expect("stderr sidecar") .contains(diagnostic)
); } #[test] fn step5_loop_commits_the_coder_delta_and_persists_its_complete_transcript() { let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); fs::write(root.join("tracked.txt"), "before-coder\n").expect("preexisting change"); git_success(&root, &["add", "tracked.txt"]); let implementation = fixture.path().join("implementation"); fs::create_dir_all(&implementation).expect("implementation");
fs::write( implementation.join("session-env.sh"), "RUN_ID=review-and-fix-test\nCODEX_BINARY_FOUND=true\nCURSOR_BINARY_FOUND=false\nLARCH_TOKEN_SESSION_ID=repair-session\nLARCH_TIMING_LEDGER=/tmp/repair-ledger.tsv\n", ) .expect("session env"); fs::write(implementation.join("plan.txt"), "plan\n").expect("plan"); fs::write(implementation.join("feature-description.txt"), "feature\n").expect("feature"); let fixture_plugin
= step5_plugin(fixture.path()); let bin = fixture.path().join("bin"); fs::create_dir_all(&bin).expect("fixture bin"); let codex = bin.join("codex"); fs::write(&codex, "#!/bin/sh\nexit 0\n").expect("codex stub"); fs::set_permissions(&codex, fs::Permissions::from_mode(0o755)).expect("codex mode"); let system_path = env::var_os("PATH").expect("PATH"); let path = env::join_paths(std::iter::once(bin).chain(env::split_paths(&system_path))).expect("PATH");
let result = Command::new(env!("CARGO_BIN_EXE_larch")) .current_dir(&root) .env("CLAUDE_PROJECT_DIR", &root) .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin) .env("PATH", path) .args([ "review-and-fix", "step5", "--implement-tmpdir", implementation.to_str().expect("implementation path"), "--mode", "loop", "--codex-available", "true", "--cursor-available", "false", ]) .output() .expect("step5"); assert!( result.status.success(),
"{}", String::from_utf8_lossy(&result.stderr) ); let transcript = "STEP5_REVIEW_STATUS=complete\nSTALL_TRACKING=false\nSTALL_REASON=\nROUNDS_COMPLETED=1\nFINAL_ROUND_NUM=1\nFINAL_REVIEW_AND_FIX_STATUS=fix-applied\nCODER_STATUS=applied\nFILES_CHANGED_HINT="; let stdout = String::from_utf8_lossy(&result.stdout); assert!(stdout.starts_with(transcript), "{stdout}"); assert!( stdout.contains("EFFECTIVE_ROUND_CAP=2\nPANEL_TIER=MODERATE\nAUDIT_UPGRADE=false\n"),
"{stdout}" ); assert_eq!( fs::read_to_string(implementation.join(".step5-review-result.env")) .expect("persisted transcript"), stdout, ); assert_eq!( fs::read_to_string(root.join("tracked.txt")).expect("tracked content"), "after\n" ); assert_eq!( fs::read_to_string(implementation.join("round-1/coder-context.txt")) .expect("coder session context"), format!( "repair-session|{}|\n", implementation.join("timing-ledger.tsv").display()
) ); assert_eq!( String::from_utf8_lossy(&git(&root, &["show", "--format=", "--name-only", "HEAD"]).stdout), "tracked.txt\n" ); assert!(implementation.join("progress/done").is_file()); assert!(implementation.join("round-1/round-start-s").is_file()); assert!(implementation.join("timing-ledger.tsv.recorded").is_file()); } #[test] fn normalize_status_replays_and_persists_the_captured_envelope() { let fixture = TempDir::new().expect("fixture");
let root = repository(&fixture); let implementation = fixture.path().join("implementation"); fs::create_dir_all(&implementation).expect("implementation"); let captured = fixture.path().join("captured.out"); let transcript = "STEP5_REVIEW_STATUS=complete\nSTALL_TRACKING=false\nSTALL_REASON=\nROUNDS_COMPLETED=1\nFINAL_ROUND_NUM=1\nFINAL_REVIEW_AND_FIX_STATUS=complete\nCODER_STATUS=skipped\nFILES_CHANGED_HINT=\nEFFECTIVE_ROUND_CAP=2\n";
fs::write(&captured, transcript).expect("captured transcript"); let result = output( &root, &[ "review-and-fix", "normalize-status", "--implement-tmpdir", implementation.to_str().expect("implementation path"), "--stdout-file", captured.to_str().expect("captured path"), "--loop-rc", "7", ], ); assert_eq!(result.status.code(), Some(7)); assert_eq!(String::from_utf8_lossy(&result.stdout), transcript); assert_eq!( fs::read_to_string(implementation.join(".step5-review-result.env"))
.expect("persisted envelope"), transcript, ); } #[test] fn self_review_snapshot_commits_only_its_delta() { let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); let implementation = fixture.path().join("implementation"); fs::create_dir_all(&implementation).expect("implementation"); let fixture_plugin = plugin(fixture.path()); let snapshot = Command::new(env!("CARGO_BIN_EXE_larch")) .current_dir(&root)
.env("CLAUDE_PROJECT_DIR", &root) .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin) .args([ "review-and-fix", "write-pre-self-review-snapshot", "--implement-tmpdir", implementation.to_str().expect("implementation path"), ]) .output() .expect("write snapshot"); assert!( snapshot.status.success(), "{}", String::from_utf8_lossy(&snapshot.stderr) ); fs::write(root.join("tracked.txt"), "after\n").expect("review edit"); fs::write(
implementation.join("self-review-accepted.md"), "### [Code Review] Self-review accepted\n", ) .expect("accepted marker"); let commit = Command::new(env!("CARGO_BIN_EXE_larch")) .current_dir(&root) .env("CLAUDE_PROJECT_DIR", &root) .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin) .env("IMPLEMENT_TMPDIR", &implementation) .args(["review-and-fix", "commit-fixes", "--stage-all"]) .output() .expect("commit review delta"); assert!(
commit.status.success(), "{}", String::from_utf8_lossy(&commit.stderr) ); assert!(String::from_utf8_lossy(&commit.stdout).contains("COMMIT_OUTCOME=ok\n")); let files = git(&root, &["show", "--format=", "--name-only", "HEAD"]); assert_eq!(String::from_utf8_lossy(&files.stdout), "tracked.txt\n"); } #[test] fn self_review_snapshot_replaces_stale_patch_artifacts() { let fixture = TempDir::new().expect("fixture"); let root
= repository(&fixture); let implementation = fixture.path().join("implementation"); fs::create_dir_all(&implementation).expect("implementation"); let args = [ "review-and-fix", "write-pre-self-review-snapshot", "--implement-tmpdir", implementation.to_str().expect("implementation path"), ]; let first = output(&root, &args); assert!( first.status.success(), "{}", String::from_utf8_lossy(&first.stderr) ); let stale = implementation.join("self-review-snapshot/pre-self-review-path-diffs/stale");
fs::write(&stale, "stale\n").expect("stale patch artifact"); let second = output(&root, &args); assert!( second.status.success(), "{}", String::from_utf8_lossy(&second.stderr) ); assert!(!stale.exists()); } #[allow(clippy::literal_string_with_formatting_args)] fn failed_launcher_plugin(root: &Path) -> std::path::PathBuf { let plugin = root.join("failed-launcher-plugin"); let scripts = plugin.join("scripts"); fs::create_dir_all(&scripts).expect("fixture scripts");
let bootstrap = scripts.join("larch.sh"); fs::write( &bootstrap, r#"#!/bin/sh
set -eu
domain=${1:-}
verb=${2:-}
shift 2 || true
case "$domain:$verb" in
  agent:launch-codex-exec|agent:launch-claude-review-fix)
    output=""
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --output) output=$2; shift 2 ;;
        *) shift ;;
      esac
    done
    printf 'APPLIED: FINDING_1\n' > "$output"
    printf 'coder debris\n' > tracked.txt
    mkdir -p coder-debris
    printf 'debris\n' > coder-debris/new.txt
    printf 'LAUNCHER_EXIT=7\nOUTPUT=%s\n' "$output"
    exit 0
    ;;
  *) exit 0 ;;
esac
"#, ) .expect("fixture bootstrap"); fs::set_permissions(&bootstrap, fs::Permissions::from_mode(0o755)) .expect("fixture bootstrap mode"); plugin } #[allow(clippy::literal_string_with_formatting_args)] fn cursor_coder_plugin(root: &Path) -> std::path::PathBuf { let plugin = root.join("cursor-coder-plugin"); let scripts = plugin.join("scripts"); fs::create_dir_all(&scripts).expect("fixture scripts"); let bootstrap = scripts.join("larch.sh");
fs::write( &bootstrap, r#"#!/bin/sh
set -eu
domain=${1:-}
verb=${2:-}
shift 2 || true
case "$domain:$verb" in
  agent:cursor-wrap-prompt) printf 'wrapped: %s\n' "$1" ;;
  timing:record-vendor-task) exit 0 ;;
  *) exit 0 ;;
esac
"#, ) .expect("fixture bootstrap"); fs::set_permissions(&bootstrap, fs::Permissions::from_mode(0o755)) .expect("fixture bootstrap mode"); plugin } #[allow(clippy::literal_string_with_formatting_args)] fn handoff_failure_plugin(root: &Path) -> std::path::PathBuf { let plugin = root.join("handoff-failure-plugin"); let scripts = plugin.join("scripts"); fs::create_dir_all(&scripts).expect("fixture scripts"); let bootstrap
= scripts.join("larch.sh"); fs::write( &bootstrap, r#"#!/bin/sh
set -eu
domain=${1:-}
verb=${2:-}
shift 2 || true
case "$domain:$verb" in
  review:core)
    output_dir=""
    while [ "$#" -gt 0 ]; do
      case "$1" in --output-dir) output_dir=$2; shift 2 ;; *) shift ;; esac
    done
    printf '%s\n' '### FINDING_1: update tracked content' '- **Suggested revision**: update it.' > "$output_dir/accepted-findings.md"
    : > "$output_dir/findings.md"
    : > "$output_dir/rejected-findings.md"
    printf 'review diagnostic\n' >&2
    printf 'REVIEW_CORE_STATUS=fix-required\nACCEPTED_COUNT=1\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\nACCEPTED_FINDINGS_FILE=%s\nREJECTED_FINDINGS_FILE=%s\n' "$output_dir/accepted-findings.md" "$output_dir/rejected-findings.md"
    ;;
  review:compose-findings)
    output=""
    while [ "$#" -gt 0 ]; do
      case "$1" in --output) output=$2; shift 2 ;; *) shift ;; esac
    done
    : > "$output"
    ;;
  stall-recovery:record-escalation)
    implement=""
    detail=""
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --implement-tmpdir) implement=$2; shift 2 ;;
        --failure-detail-log) detail=$2; shift 2 ;;
        *) shift ;;
      esac
    done
    printf '%s\n' "$detail" > "$implement/failure-detail-arg.txt"
    printf 'record boom\n' >&2
    exit 9
    ;;
  run-log:write)
    batch=""
    while [ "$#" -gt 0 ]; do
      case "$1" in --batch) batch=$2; shift 2 ;; *) shift ;; esac
    done
    if [ "$batch" = difficulty-rating ]; then printf 'write boom\n' >&2; exit 6; fi
    ;;
  timing:record-vendor-task)
    ledger=""
    values=""
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --ledger) ledger=$2; shift 2 ;;
        --vendor|--task-kind|--exit-code|--status) values="$values $1=$2"; shift 2 ;;
        *) shift ;;
      esac
    done
    printf '%s\n' "$values" > "$ledger.vendor-task"
    ;;
  timing:mark|timing:record-round|git:snapshot-untracked|run-log:write-round|voting:write-tally) exit 0 ;;
  *) exit 0 ;;
esac
"#, ) .expect("fixture bootstrap"); fs::set_permissions(&bootstrap, fs::Permissions::from_mode(0o755)) .expect("fixture bootstrap mode"); plugin } #[test] fn step5_handoff_carries_local_stderr_and_records_fail_open_helper_failures() { let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); let implementation = fixture.path().join("implementation"); fs::create_dir_all(&implementation).expect("implementation");
fs::write( implementation.join("session-env.sh"), "RUN_ID=handoff-test\nCODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=false\n", ) .expect("session env"); fs::write(implementation.join("plan.txt"), "plan\n").expect("plan"); fs::write(implementation.join("feature-description.txt"), "feature\n").expect("feature"); fs::write(implementation.join("difficulty-rating.json"), "{}\n").expect("difficulty"); let fixture_plugin =
handoff_failure_plugin(fixture.path()); let result = Command::new(env!("CARGO_BIN_EXE_larch")) .current_dir(&root) .env("CLAUDE_PROJECT_DIR", &root) .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin) .env( "PATH", env::join_paths([ std::path::PathBuf::from("/usr/bin"), std::path::PathBuf::from("/bin"), ]) .expect("PATH"), ) .args([ "review-and-fix", "step5", "--implement-tmpdir", implementation.to_str().expect("implementation path"),
"--mode", "loop", "--codex-available", "false", "--cursor-available", "false", ]) .output() .expect("step5 handoff"); assert!(result.status.success()); let stdout = String::from_utf8_lossy(&result.stdout); let sidecar = implementation.join("round-1/review-and-fix.stderr"); let canonical_sidecar = fs::canonicalize(&sidecar).expect("canonical stderr sidecar"); assert!(stdout.contains("STEP5_REVIEW_STATUS=coder-main-agent-required\n"));
assert!( stdout.contains(&format!( "STEP5_REVIEW_LEDGER_FAILURE_DETAIL_LOG={}\n", canonical_sidecar.display() )), "{stdout}" ); assert_eq!( fs::read_to_string(&sidecar).expect("stderr sidecar"), "review diagnostic\n" ); assert_eq!( fs::read_to_string(implementation.join("failure-detail-arg.txt")) .expect("escalation detail argument") .trim(), canonical_sidecar.display().to_string() ); let stderr = String::from_utf8_lossy(&result.stderr);
assert!(stderr.contains("record boom"), "{stderr}"); assert!( stderr.contains("difficulty-rating batch restage failed: helper-exit-6: write boom"), "{stderr}" ); let issues = fs::read_to_string(implementation.join("execution-issues.md")).expect("execution issues"); assert!( issues.contains("Tool Failure: record-escalation"), "{issues}" ); assert!( issues.contains("difficulty-rating` restage failed"), "{issues}" ); let
vendor_task = fs::read_to_string(implementation.join("timing-ledger.tsv.vendor-task")) .expect("main-agent-required timing task"); assert!(vendor_task.contains("--vendor=claude"), "{vendor_task}"); assert!(vendor_task.contains("--exit-code=4"), "{vendor_task}"); assert!(vendor_task.contains("--status=signal"), "{vendor_task}"); } #[test] fn cursor_coder_reuses_model_auth_environment_and_external_lifecycle_owners() { let
fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); let findings = fixture.path().join("findings.md"); let review = fixture.path().join("review"); let session = fixture.path().join("session-env.sh"); fs::write( &findings, "### FINDING_1: update tracked content\n- **Suggested revision**: update it.\n", ) .expect("findings"); fs::write( &session, "CODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=true\n",
) .expect("session"); let fixture_plugin = cursor_coder_plugin(fixture.path()); let bin = fixture.path().join("bin"); fs::create_dir_all(&bin).expect("fixture bin"); let cursor = bin.join("cursor"); fs::write( &cursor, "#!/bin/sh\nprintf 'argv=%s\\nenv=%s|%s\\n' \"$*\" \"${NO_OPEN_BROWSER:-}\" \"${CURSOR_API_KEY:-}\"\nprintf 'after cursor\\n' > tracked.txt\n", ) .expect("cursor stub"); fs::set_permissions(&cursor, fs::Permissions::from_mode(0o755)).expect("cursor mode");
let result = Command::new(env!("CARGO_BIN_EXE_larch")) .current_dir(&root) .env("CLAUDE_PROJECT_DIR", &root) .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin) .env("CURSOR_API_KEY", "  cursor-test-token  ") .env( "PATH", env::join_paths([ bin, std::path::PathBuf::from("/usr/bin"), std::path::PathBuf::from("/bin"), ]) .expect("PATH"), ) .args([ "review-and-fix", "apply-findings", "--findings-file", findings.to_str().expect("findings path"),
"--review-tmpdir", review.to_str().expect("review path"), "--session-env-path", session.to_str().expect("session path"), ]) .output() .expect("apply findings"); assert!( result.status.success(), "{}", String::from_utf8_lossy(&result.stderr) ); assert!(String::from_utf8_lossy(&result.stdout).contains("CODER_TOOL=cursor\n")); let log = fs::read_to_string(review.join("coder-output.log")).expect("cursor output"); assert!(log.contains("--model composer-2.5"),
"{log}"); assert!(log.contains("env=1|cursor-test-token"), "{log}"); assert_eq!( fs::read_to_string(root.join("tracked.txt")).expect("tracked"), "after cursor\n" ); assert_eq!( fs::read_to_string(review.join("coder-cursor.log.done")).expect("done sentinel"), "0\n" ); } #[test] fn failed_codex_and_claude_launcher_exits_restore_the_exact_dirty_baseline() { for (tool, session_text) in [ ( "codex", "CODEX_BINARY_FOUND=true\nCURSOR_BINARY_FOUND=false\n",
), ( "claude", "CODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=false\n", ), ] { let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); fs::write(root.join("tracked.txt"), "staged carryover\n").expect("baseline edit"); git_success(&root, &["add", "tracked.txt"]); let baseline = String::from_utf8_lossy(&git(&root, &["diff", "--cached", "--", "tracked.txt"]).stdout) .into_owned(); let findings =
fixture.path().join("findings.md"); let review = fixture.path().join("review"); let session = fixture.path().join("session-env.sh"); fs::write( &findings, "### FINDING_1: update tracked content\n- **Suggested revision**: update it.\n", ) .expect("findings"); fs::write(&session, session_text).expect("session"); let fixture_plugin = failed_launcher_plugin(fixture.path()); let bin = fixture.path().join("bin"); fs::create_dir_all(&bin).expect("fixture bin");
let vendor = bin.join(tool); fs::write(&vendor, "#!/bin/sh\nexit 0\n").expect("vendor stub"); fs::set_permissions(&vendor, fs::Permissions::from_mode(0o755)).expect("vendor mode"); let result = Command::new(env!("CARGO_BIN_EXE_larch")) .current_dir(&root) .env("CLAUDE_PROJECT_DIR", &root) .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin) .env( "PATH", env::join_paths([ bin, std::path::PathBuf::from("/usr/bin"), std::path::PathBuf::from("/bin"),
]) .expect("PATH"), ) .args([ "review-and-fix", "apply-findings", "--findings-file", findings.to_str().expect("findings path"), "--review-tmpdir", review.to_str().expect("review path"), "--session-env-path", session.to_str().expect("session path"), ]) .output() .expect("apply findings"); assert!( result.status.success(), "{tool}: {}", String::from_utf8_lossy(&result.stderr) ); assert!( String::from_utf8_lossy(&result.stdout)
.contains("REVIEW_AND_FIX_STATUS=coder-main-agent-required\n"), "{tool}" ); assert_eq!( fs::read_to_string(root.join("tracked.txt")).expect("tracked"), "staged carryover\n", "{tool}" ); assert_eq!( String::from_utf8_lossy(&git(&root, &["diff", "--cached", "--", "tracked.txt"]).stdout), baseline, "{tool}" ); assert!(!root.join("coder-debris").exists(), "{tool}"); } } fn write_round_snapshot(implementation: &Path, head:
&str, full: bool) { let snapshot = implementation.join(".pre-coder-snapshots").join("round-1"); fs::create_dir_all(&snapshot).expect("snapshot root"); fs::write(snapshot.join("pre-coder-head.txt"), format!("{head}\n")).expect("snapshot head"); fs::write(snapshot.join("pre-coder-untracked-paths.txt"), "").expect("snapshot untracked"); if full { fs::write(snapshot.join("pre-coder-tracked-paths.txt"), "").expect("snapshot tracked");
fs::create_dir_all(snapshot.join("pre-coder-path-diffs")).expect("snapshot patches"); } let round = implementation.join("round-1"); fs::create_dir_all(&round).expect("round"); fs::write(round.join("post-coder-head.txt"), format!("{head}\n")).expect("post coder head"); } #[test] fn commit_stage_all_collects_manual_repairs_from_full_round_snapshots() { let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture);
let implementation = fixture.path().join("implementation"); fs::create_dir_all(&implementation).expect("implementation"); let head = String::from_utf8_lossy(&git(&root, &["rev-parse", "HEAD"]).stdout) .trim() .to_owned(); write_round_snapshot(&implementation, &head, true); fs::write(root.join("tracked.txt"), "manual repair\n").expect("manual repair"); let fixture_plugin = plugin(fixture.path()); let result = Command::new(env!("CARGO_BIN_EXE_larch"))
.current_dir(&root) .env("CLAUDE_PROJECT_DIR", &root) .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin) .env("IMPLEMENT_TMPDIR", &implementation) .args(["review-and-fix", "commit-fixes", "--stage-all"]) .output() .expect("commit manual repair"); assert!( result.status.success(), "{}", String::from_utf8_lossy(&result.stderr) ); assert!(String::from_utf8_lossy(&result.stdout).contains("COMMIT_OUTCOME=ok\n")); assert_ne!( String::from_utf8_lossy(&git(&root,
&["rev-parse", "HEAD"]).stdout).trim(), head, ); } #[test] fn commit_stage_all_does_not_upgrade_head_only_mav_snapshots() { let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); let implementation = fixture.path().join("implementation"); fs::create_dir_all(&implementation).expect("implementation"); let head = String::from_utf8_lossy(&git(&root, &["rev-parse", "HEAD"]).stdout) .trim() .to_owned();
write_round_snapshot(&implementation, &head, false); fs::write(root.join("tracked.txt"), "manual repair\n").expect("manual repair"); let fixture_plugin = plugin(fixture.path()); let result = Command::new(env!("CARGO_BIN_EXE_larch")) .current_dir(&root) .env("CLAUDE_PROJECT_DIR", &root) .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin) .env("IMPLEMENT_TMPDIR", &implementation) .args(["review-and-fix", "commit-fixes", "--stage-all"])
.output() .expect("skip head-only snapshot"); assert!( result.status.success(), "{}", String::from_utf8_lossy(&result.stderr) ); assert!(String::from_utf8_lossy(&result.stdout).contains("COMMIT_OUTCOME=noop\n")); assert_eq!( String::from_utf8_lossy(&git(&root, &["rev-parse", "HEAD"]).stdout).trim(), head, ); assert_eq!( fs::read_to_string(root.join("tracked.txt")).expect("tracked"), "manual repair\n" ); } #[test] fn commit_stage_all_fails_closed_for_a_partial_round_snapshot()
{ let fixture = TempDir::new().expect("fixture"); let root = repository(&fixture); let implementation = fixture.path().join("implementation"); let round = implementation.join("round-1"); let snapshot = implementation.join(".pre-coder-snapshots/round-1"); fs::create_dir_all(&round).expect("round"); fs::create_dir_all(&snapshot).expect("snapshot"); let head = String::from_utf8_lossy(&git(&root, &["rev-parse", "HEAD"]).stdout)
.trim() .to_owned(); fs::write(snapshot.join("pre-coder-head.txt"), format!("{head}\n")).expect("partial snapshot"); fs::write(root.join("tracked.txt"), "manual repair\n").expect("manual repair"); let fixture_plugin = plugin(fixture.path()); let result = Command::new(env!("CARGO_BIN_EXE_larch")) .current_dir(&root) .env("CLAUDE_PROJECT_DIR", &root) .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin) .env("IMPLEMENT_TMPDIR", &implementation)
.args(["review-and-fix", "commit-fixes", "--stage-all"]) .output() .expect("reject partial snapshot"); assert_eq!(result.status.code(), Some(1)); let stdout = String::from_utf8_lossy(&result.stdout); assert!(stdout.contains("COMMITTED=false\n"), "{stdout}"); assert!(stdout.contains("COMMIT_OUTCOME=failed\n"), "{stdout}"); assert!(stdout.contains("PartialArtifacts"), "{stdout}"); assert_eq!( String::from_utf8_lossy(&git(&root,
&["rev-parse", "HEAD"]).stdout).trim(), head ); } }
