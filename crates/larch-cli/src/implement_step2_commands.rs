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
