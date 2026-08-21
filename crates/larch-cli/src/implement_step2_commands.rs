//! Rust owners for `implement run-dispatch` and `implement step2-dispatch` (#8623).
//!
//! `run-dispatch` is the serialized launcher: it takes the per-tmpdir dispatch
//! lock, marks the Step 2 telemetry budget, runs `step2-dispatch` as a child, and
//! republishes the child's stdout as this leg's bgjob envelope. `step2-dispatch`
//! is the orchestrator: it routes the coder, runs the external implementer
//! launcher, validates the returned manifest, commits a complete result, and
//! emits the Step 2 `KEY=value` contract.
//!
//! Policy stays with its existing owners. `agent launch-*-implement` owns the
//! launcher, `implement scope-disposition` owns plan coverage, `oos
//! materialize-manifest` owns OOS materialization, `difficulty write-record`
//! owns the difficulty ledger, and the still-Python `issue governance-gate`
//! owns migration governance. This module sequences them and owns only the
//! manifest schema routing that the Step 2 contract itself defines.

use std::{
    env,
    ffi::{OsStr, OsString},
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::{Mutex, PoisonError},
};

use larch_adapters::{AddRequest, CommitMessage, CommitRequest, GitFilePath, GixRepository};
use larch_core::{
    ArchitecturalKind, ArchitecturalStatus, ChangeKind, ChildEnvironment, GitHubRepositoryRef,
    GitHubService as _, Head, LauncherArtifact, ProcessOutput, RepositoryRead as _, Revision,
    detect_codex_cli_gate, emit_kv,
    implement::{
        CompletionRetryInvalid, CompletionRetryState, DispatchState, MANIFEST_STATUSES, RESUME_CAP,
        SAFE_CODERS, WRAPPER_VALIDATION_RC, child_stdout_is_claude_fallback,
        clear_external_scout_paths, complete_schema_valid, declared_paths, json_scalar_string,
        manifest_legacy_fingerprint, manifest_status, model_value_safe, needs_qa_questions_present,
        oos_materialize_should_bail, parse_completion_retry_state, qa_pending_valid,
        repaired_qa_questions, require_architectural_acknowledgment, sanitize_bail_reason,
        sanitize_manifest_obj, step2_token_mark_eligible, submodule_status_dirty,
        validate_manifest_paths,
    },
    is_quota_failure, normalize_tier, read_architectural_knowledge, redact_secrets_only, tier_valid,
    write_bytes_atomic,
};
use serde_json::{Map, Value};

use crate::{
    argparse_compat::{choice_error, parse_required_with_help, usage_error},
    implement_child_seam::resolve_plugin_root,
    implement_commands::{kv_value, read_kv_first, write_atomic},
    implement_dispatch_commands::{
        capture_postlaunch_porcelain, capture_prelaunch_porcelain, delegate_python,
        delegate_verified_larch, rehydrate_session, run_verified_larch_env_in,
    },
    implement_launcher_commands::{
        CODEX_IMPLEMENT_MODEL, cursor_implement_model, read_architectural_knowledge,
    },
    implement_preflight_commands::governance_gate_argv,
    python_verb::publish_session_environment,
};

const RUN_PROG: &str = "cli.py implement run-dispatch";
const RUN_USAGE: &str = "usage: cli.py implement run-dispatch [-h]\n                                     [--implement-tmpdir IMPLEMENT_TMPDIR]\n                                     --coder CODER [--answers ANSWERS]\n                                     [--difficulty {,TRIVIAL,MODERATE,HARD}]\n                                     [--bgjob-child]\n                                     [--merge-result-env MERGE_RESULT_ENV]\n";
const RUN_HELP: &str = "usage: cli.py implement run-dispatch [-h]\n                                     [--implement-tmpdir IMPLEMENT_TMPDIR]\n                                     --coder CODER [--answers ANSWERS]\n                                     [--difficulty {,TRIVIAL,MODERATE,HARD}]\n                                     [--bgjob-child]\n                                     [--merge-result-env MERGE_RESULT_ENV]\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --coder CODER\n  --answers ANSWERS\n  --difficulty {,TRIVIAL,MODERATE,HARD}\n  --bgjob-child\n  --merge-result-env MERGE_RESULT_ENV\n";

const STEP2_PROG: &str = "cli.py implement step2-dispatch";
const STEP2_USAGE: &str = "usage: cli.py implement step2-dispatch [-h] --tmpdir TMPDIR --plan-file\n                                       PLAN_FILE --feature-file FEATURE_FILE\n                                       [--coder CODER]\n                                       [--codex-available CODEX_AVAILABLE]\n                                       [--cursor-present CURSOR_PRESENT]\n                                       [--codex-present CODEX_PRESENT]\n                                       [--cursor-available CURSOR_AVAILABLE]\n                                       [--codex-binary-found CODEX_BINARY_FOUND]\n                                       [--cursor-binary-found CURSOR_BINARY_FOUND]\n                                       [--answers ANSWERS]\n                                       [--completion-retry]\n                                       [--difficulty {,TRIVIAL,MODERATE,HARD}]\n";
const STEP2_HELP: &str = "usage: cli.py implement step2-dispatch [-h] --tmpdir TMPDIR --plan-file\n                                       PLAN_FILE --feature-file FEATURE_FILE\n                                       [--coder CODER]\n                                       [--codex-available CODEX_AVAILABLE]\n                                       [--cursor-present CURSOR_PRESENT]\n                                       [--codex-present CODEX_PRESENT]\n                                       [--cursor-available CURSOR_AVAILABLE]\n                                       [--codex-binary-found CODEX_BINARY_FOUND]\n                                       [--cursor-binary-found CURSOR_BINARY_FOUND]\n                                       [--answers ANSWERS]\n                                       [--completion-retry]\n                                       [--difficulty {,TRIVIAL,MODERATE,HARD}]\n\noptions:\n  -h, --help            show this help message and exit\n  --tmpdir TMPDIR\n  --plan-file PLAN_FILE\n  --feature-file FEATURE_FILE\n  --coder CODER\n  --codex-available CODEX_AVAILABLE\n  --cursor-present CURSOR_PRESENT\n  --codex-present CODEX_PRESENT\n  --cursor-available CURSOR_AVAILABLE\n  --codex-binary-found CODEX_BINARY_FOUND\n  --cursor-binary-found CURSOR_BINARY_FOUND\n  --answers ANSWERS\n  --completion-retry\n  --difficulty {,TRIVIAL,MODERATE,HARD}\n";

const IMPLEMENT_STEP2_LABEL: &str = "implement-step2";
const LAUNCHER_TIMEOUT_SECONDS: &str = "7200";
const ARCH_KNOWLEDGE_SNAPSHOT: &str = "step2-architectural-knowledge.env";
const PRIOR_ATTEMPT_REASON: &str = "prior-attempt-unfinalized";
const COMPLETION_RETRY_STATE_INVALID: &str = "completion-retry-state-invalid";
const COMPLETION_RETRY_STATE_STALE: &str = "completion-retry-state-stale";
const COMPLETION_RETRY_CAP: u32 = 3;
/// Bounded prefix of launcher stdout the `KEY=value` scan reads.
const LAUNCHER_KV_LIMIT: usize = 65_536;
/// `--difficulty` accepts the tiers plus the explicit unset token.
const DIFFICULTY_CHOICES: [&str; 4] = ["", "TRIVIAL", "MODERATE", "HARD"];
/// Every `run-dispatch` option, for the shared choice validator.
const RUN_OPTIONS: [&str; 8] = [
    "--implement-tmpdir",
    "--coder",
    "--answers",
    "--difficulty",
    "--bgjob-child",
    "--merge-result-env",
    "-h",
    "--help",
];
/// Every `step2-dispatch` option, for the shared choice validator.
const STEP2_OPTIONS: [&str; 15] = [
    "--tmpdir",
    "--plan-file",
    "--feature-file",
    "--coder",
    "--codex-available",
    "--cursor-present",
    "--codex-present",
    "--cursor-available",
    "--codex-binary-found",
    "--cursor-binary-found",
    "--answers",
    "--completion-retry",
    "--difficulty",
    "-h",
    "--help",
];

include!("implement_step2_commands_impl.rs");

// ---------------------------------------------------------------------------
// implement run-dispatch
// ---------------------------------------------------------------------------

/// `implement run-dispatch` compatibility command.
pub fn run_dispatch(arguments: &[OsString]) -> ExitCode {
    let request = match parse_run_dispatch(arguments) {
        Ok(request) => request,
        Err(code) => return code,
    };
    let RunDispatchRequest {
        tmpdir,
        plugin_root,
        coder,
        answers,
        codex_binary_found,
        cursor_binary_found,
        merge_result_env,
        child,
    } = request;

    let Some(lock) = DispatchLock::acquire(&tmpdir.join("dispatch.lock")) else {
        return ExitCode::from(2);
    };
    rehydrate_session(&tmpdir);
    // A Q/A resume continues an already-charged dispatch, so only a fresh
    // dispatch marks the Step 2 telemetry budget.
    let telemetry_marked = answers.is_empty()
        && mark_step2_telemetry(
            &tmpdir,
            &plugin_root,
            &coder,
            &codex_binary_found,
            &cursor_binary_found,
        );
    let outcome = run_verified_larch_env_in(&tmpdir, &plugin_root, &child, &[]);
    let result = match outcome {
        Ok(output) => output,
        Err(detail) => {
            drop(lock);
            eprintln!("implement run-dispatch: {detail}");
            return ExitCode::from(2);
        }
    };
    let stdout = String::from_utf8_lossy(result.stdout()).into_owned();
    if child_stdout_is_claude_fallback(&stdout) {
        clear_external_dispatch_seed(&tmpdir);
        let Some(repo_root) = discover_repo_root() else {
            drop(lock);
            eprintln!(
                "implement run-dispatch: git rev-parse --show-toplevel failed after claude_fallback"
            );
            return ExitCode::from(2);
        };
        let rc = capture_prelaunch_porcelain(&repo_root, &tmpdir);
        if rc != 0 {
            drop(lock);
            eprintln!(
                "implement run-dispatch: prelaunch porcelain capture failed after claude_fallback"
            );
            return ExitCode::from(rc);
        }
    }
    if telemetry_marked && !tmpdir.join(".step2-telemetry-marked").is_file() {
        write_step2_telemetry_sentinel(&tmpdir);
    }
    drop(lock);

    let code = result.status().code().unwrap_or(1);
    if !merge_result_env.is_empty()
        && code == 0
        && !publish_bgjob_envelope(&tmpdir, Path::new(&merge_result_env), &stdout)
    {
        eprintln!("implement run-dispatch: could not publish bgjob result envelope");
        return ExitCode::from(2);
    }
    if !stdout.is_empty() {
        let mut handle = std::io::stdout();
        let _written = handle.write_all(stdout.as_bytes());
        let _flushed = handle.flush();
    }
    let stderr = String::from_utf8_lossy(result.stderr()).into_owned();
    if !stderr.is_empty() {
        eprintln!("{}", stderr.trim_end_matches('\n'));
    }
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

// ---------------------------------------------------------------------------
// implement step2-dispatch
// ---------------------------------------------------------------------------

/// `implement step2-dispatch` compatibility command.
pub fn step2_dispatch(arguments: &[OsString]) -> ExitCode {
    match step2_dispatch_argv(arguments) {
        Ok(request) => run_step2_dispatch(&request),
        Err(code) => code,
    }
}

fn text(value: Option<&OsStr>) -> String {
    value
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default()
}

#[cfg(test)]
mod commands_tests {
    use super::fixtures::*;
    use super::*;

    #[test]
    fn text_defaults_empty_and_passes_through() {
        assert_eq!(text(None), "");
        assert_eq!(text(Some(OsStr::new("value"))), "value");
    }

    #[test]
    fn run_dispatch_requires_a_coder() {
        let code = run_dispatch(&test_arguments(&["--implement-tmpdir", "/nonexistent"]));
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::from(2)));
    }

    #[test]
    fn run_dispatch_help_exits_success() {
        let code = run_dispatch(&test_arguments(&["--help"]));
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
    }

    #[test]
    fn step2_dispatch_help_exits_success() {
        let code = step2_dispatch(&test_arguments(&["--help"]));
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
    }

    #[test]
    fn step2_dispatch_requires_a_directory_tmpdir() {
        let code = step2_dispatch(&test_arguments(&[
            "--tmpdir",
            "/nonexistent/step2/tmpdir",
            "--plan-file",
            "/nonexistent/step2/tmpdir/plan.txt",
            "--feature-file",
            "/nonexistent/step2/tmpdir/feature.txt",
            "--coder",
            "codex",
        ]));
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::from(2)));
    }

    /// A full `step2-dispatch` run for the `claude` coder never launches an
    /// external process: it is a same-process fallback, so it is safe to run
    /// end to end against a scratch tmpdir.
    #[test]
    fn step2_dispatch_full_run_falls_back_to_claude_for_the_claude_coder() {
        let dir = tempfile::tempdir().expect("tmpdir");
        test_write_fixture(&dir.path().join("plan.txt"), "plan\n");
        test_write_fixture(&dir.path().join("feature.txt"), "feature\n");
        let code = step2_dispatch(&test_arguments(&[
            "--tmpdir",
            dir.path().to_str().expect("utf8"),
            "--plan-file",
            dir.path().join("plan.txt").to_str().expect("utf8"),
            "--feature-file",
            dir.path().join("feature.txt").to_str().expect("utf8"),
            "--coder",
            "claude",
        ]));
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
        assert!(dir.path().join("step2-baseline.txt").is_file());
    }

    /// Ditto for a coder whose binary is explicitly reported absent: the
    /// dispatcher falls back to Claude before it would launch anything.
    #[test]
    fn step2_dispatch_full_run_falls_back_to_claude_when_the_binary_is_absent() {
        let dir = tempfile::tempdir().expect("tmpdir");
        test_write_fixture(&dir.path().join("plan.txt"), "plan\n");
        test_write_fixture(&dir.path().join("feature.txt"), "feature\n");
        let code = step2_dispatch(&test_arguments(&[
            "--tmpdir",
            dir.path().to_str().expect("utf8"),
            "--plan-file",
            dir.path().join("plan.txt").to_str().expect("utf8"),
            "--feature-file",
            dir.path().join("feature.txt").to_str().expect("utf8"),
            "--coder",
            "codex",
            "--codex-binary-found",
            "false",
        ]));
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
        assert!(dir.path().join("step2-baseline.txt").is_file());
    }

    // -- run_dispatch: forwarding a real child `step2-dispatch` process
    // (#8623 coverage) ---------------------------------------------------
    //
    // `run_dispatch` runs its `implement step2-dispatch` child, and
    // `mark_step2_telemetry`'s timing mark, through `run_verified_larch_env_in`,
    // which has no Rust-side test seam. Both go through one real
    // `scripts/larch.sh` stub under a fixture plugin root instead.

    /// A `run-dispatch` fixture whose `scripts/larch.sh` answers `timing mark`
    /// and forwards `child_stdout` as the `implement step2-dispatch` child's
    /// own stdout. `CODEX_BINARY_FOUND=true` keeps token-mark eligibility
    /// (and its separate `delegate_verified_larch` seam) out of scope here.
    #[cfg(unix)]
    fn run_dispatch_stub_fixture(child_stdout: &str) -> tempfile::TempDir {
        let dir = tempfile::tempdir().expect("tmpdir");
        let plugin_root = dir.path().join("plugin-root");
        fs::create_dir_all(&plugin_root).expect("plugin root");
        test_write_fixture(
            &dir.path().join("session-env.sh"),
            &format!(
                "LARCH_CLAUDE_PLUGIN_ROOT={}\nCODEX_BINARY_FOUND=true\n",
                plugin_root.display()
            ),
        );
        test_write_fixture(&dir.path().join("feature-description.txt"), "feature\n");
        test_write_fixture(&dir.path().join("plan.txt"), "plan\n");
        let script = format!(
            "#!/usr/bin/env bash\nset -euo pipefail\ncase \"${{1:-}} ${{2:-}}\" in\n  \"timing mark\")\n    exit 0\n    ;;\n  \"implement step2-dispatch\")\n    cat <<'STUBOUT'\n{child_stdout}\nSTUBOUT\n    exit 0\n    ;;\n  *)\n    exit 0\n    ;;\nesac\n"
        );
        test_stub_larch_sh(&plugin_root, &script);
        dir
    }

    #[test]
    #[cfg(unix)]
    fn run_dispatch_forwards_a_bailed_child_status_and_marks_telemetry() {
        let dir = run_dispatch_stub_fixture(
            "STATUS=bailed\nREASON=stub-bail-for-coverage\nTOOL=codex\nORCHESTRATOR_EDIT_AUTHORITY=forbidden",
        );
        let code = run_dispatch(&test_arguments(&[
            "--implement-tmpdir",
            dir.path().to_str().expect("utf8"),
            "--coder",
            "codex",
        ]));
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
        assert!(
            dir.path().join(".step2-telemetry-marked").is_file(),
            "a bailed-but-zero-exit child must still leave telemetry marked"
        );
    }

    #[test]
    #[cfg(unix)]
    fn run_dispatch_publishes_the_childs_stdout_as_a_bgjob_envelope() {
        let dir = run_dispatch_stub_fixture(
            "STATUS=complete\nTOOL=codex\nORCHESTRATOR_EDIT_AUTHORITY=forbidden",
        );
        let merge_result_env = dir.path().join("run-dispatch.result.env");
        let code = run_dispatch(&test_arguments(&[
            "--implement-tmpdir",
            dir.path().to_str().expect("utf8"),
            "--coder",
            "codex",
            "--bgjob-child",
            "--merge-result-env",
            merge_result_env.to_str().expect("utf8"),
        ]));
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
        let published = fs::read_to_string(&merge_result_env).expect("published envelope");
        assert!(published.contains("STATUS=complete"));
    }
}
