//! Rust owners for the four `/implement` Step 8 ship-routing commands.
//!
//! The ship engine itself remains Python during the #7681 migration. These
//! commands own its version fence, durable argv reconstruction, bgjob adapter,
//! and post-OOS checkpoint bookkeeping. The two remaining Python ship verbs use
//! the one reviewed migration seam. The phantom probe composes its typed Rust
//! owner in process; Rust subprocesses enter through the verified bootstrap.

use std::{
    env,
    ffi::{OsStr, OsString},
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_core::{
    DuplicatePolicy, HostUtilityProgram, KvDocument, ParseOptions, ProcessOutput,
    ndjson_filed_evidence, private_atomic_write, read_universal_newlines, report::RunLogCorpus,
    validate_run_id,
};

use crate::{
    argparse_compat::{ParsedCommandLine, parse_required_with_help},
    child_process::run_host_utility,
    implement_child_seam::{delegate_python, resolve_plugin_root},
    implement_commands::expected_tmpdir_basename_prefix,
    implement_dispatch_commands::{
        delegate_verified_larch, forward_output, opt_string, parse_command_with_tmpdir,
        rehydrate_session, run_bgjob_adapt, safe_merge_env, tmpdir_from_env, unlink_safe,
    },
    tracking_issue_commands::adoption_sentinel_identity,
};

const GUARD_PROGRAM: &str = "cli.py implement step-8-python-guard";
const GUARD_USAGE: &str = "usage: cli.py implement step-8-python-guard [-h]";
const GUARD_HELP: &str = "usage: cli.py implement step-8-python-guard [-h]\n\noptions:\n  -h, --help  show this help message and exit";
const SEED_PROGRAM: &str = "cli.py implement step-8-seed-initial";
const SEED_USAGE: &str = concat!(
    "usage: cli.py implement step-8-seed-initial [-h] [--merge MERGE]\n",
    "                                            [--draft DRAFT]\n",
    "                                            [--no-admin-fallback NO_ADMIN_FALLBACK]\n",
    "                                            [--no-logs-commit NO_LOGS_COMMIT]\n",
    "                                            [--manifest-path MANIFEST_PATH]\n",
    "                                            [--tool-label TOOL_LABEL]\n",
    "                                            [--stall-tracking STALL_TRACKING]\n",
    "                                            [--stall-step STALL_STEP]\n",
    "                                            [--bail-reason BAIL_REASON]\n",
    "                                            [--bail-failure-detail-log BAIL_FAILURE_DETAIL_LOG]",
);
const SEED_HELP: &str = concat!(
    "usage: cli.py implement step-8-seed-initial [-h] [--merge MERGE]\n",
    "                                            [--draft DRAFT]\n",
    "                                            [--no-admin-fallback NO_ADMIN_FALLBACK]\n",
    "                                            [--no-logs-commit NO_LOGS_COMMIT]\n",
    "                                            [--manifest-path MANIFEST_PATH]\n",
    "                                            [--tool-label TOOL_LABEL]\n",
    "                                            [--stall-tracking STALL_TRACKING]\n",
    "                                            [--stall-step STALL_STEP]\n",
    "                                            [--bail-reason BAIL_REASON]\n",
    "                                            [--bail-failure-detail-log BAIL_FAILURE_DETAIL_LOG]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --merge MERGE\n",
    "  --draft DRAFT\n",
    "  --no-admin-fallback NO_ADMIN_FALLBACK\n",
    "  --no-logs-commit NO_LOGS_COMMIT\n",
    "  --manifest-path MANIFEST_PATH\n",
    "  --tool-label TOOL_LABEL\n",
    "  --stall-tracking STALL_TRACKING\n",
    "  --stall-step STALL_STEP\n",
    "  --bail-reason BAIL_REASON\n",
    "  --bail-failure-detail-log BAIL_FAILURE_DETAIL_LOG",
);
const SHIP_PROGRAM: &str = "cli.py implement step-8-ship";
const SHIP_USAGE: &str = concat!(
    "usage: cli.py implement step-8-ship [-h] [--bgjob-child]\n",
    "                                    [--merge-result-env MERGE_RESULT_ENV]",
);
const SHIP_HELP: &str = concat!(
    "usage: cli.py implement step-8-ship [-h] [--bgjob-child]\n",
    "                                    [--merge-result-env MERGE_RESULT_ENV]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --bgjob-child\n",
    "  --merge-result-env MERGE_RESULT_ENV",
);
const OOS_PROGRAM: &str = "cli.py implement step-8-oos-checkpoint";
const OOS_USAGE: &str = "usage: cli.py implement step-8-oos-checkpoint [-h]";
const OOS_HELP: &str = "usage: cli.py implement step-8-oos-checkpoint [-h]\n\noptions:\n  -h, --help  show this help message and exit";
const SHIP_STEP: &str = "implement-step8-ship";
const SHIP_BUDGET_SECONDS: u32 = 21_600;
const PYTHON_GUARD_DETAIL: &str = "Python ship driver requires Python 3.11 or newer";
const PYTHON_GUARD_JSON: &str = "{\"detail\":\"Python ship driver requires Python 3.11 or newer\",\"failed_run_id\":\"\",\"ledger_dispatcher\":\"\",\"ledger_exit_code\":null,\"ledger_failure_detail_log\":\"\",\"ledger_phase\":\"\",\"ledger_ready\":false,\"ledger_site\":\"\",\"ledger_step\":\"\",\"ledger_trigger\":\"\",\"merge_result\":\"\",\"needs_user_reason\":\"\",\"outcome\":\"STALLED\",\"pr_number\":null,\"pr_url\":\"\"}";
const SEED_OPTIONS: [&str; 10] = [
    "--merge",
    "--draft",
    "--no-admin-fallback",
    "--no-logs-commit",
    "--manifest-path",
    "--tool-label",
    "--stall-tracking",
    "--stall-step",
    "--bail-reason",
    "--bail-failure-detail-log",
];
#[rustfmt::skip]
const SHIP_STATE_ALLOWED_KEYS: &[&str] = &[
    "PHASE", "BRANCH_NAME", "ISSUE_NUMBER", "RUN_ID",
    "REPO", "REPO_UNAVAILABLE", "FORKED_TARGET", "IMPLEMENT_TMPDIR",
    "MANIFEST_PATH", "MERGE", "DRAFT", "PR_CLOSED",
    "PR_NUMBER", "PR_URL", "PR_TITLE", "MERGE_RESULT",
    "CI_FIX_REBASE_PENDING", "CI_FIX_REBASE_PENDING_HEAD", "LAST_MONITORED_HEAD",
    "REBASE_COUNT", "FIX_ATTEMPTS", "ITERATION", "TRANSIENT_RETRIES",
    "RESUME_PHASE", "CALLER_KIND", "CONFLICT_FILES", "STALL_TRACKING", "STALL_STEP",
    "EXIT_CODE", "BAIL_REASON", "BAIL_NEEDS_USER_INPUT", "FAILED_RUN_ID", "BAIL_FAILURE_DETAIL_LOG",
    "EXPECTED_SESSION_ID", "EXPECTED_TMPDIR_BASENAME_PREFIX", "NO_LOGS_COMMIT", "NO_ADMIN_FALLBACK",
    "DESIGN_ONLY_DONE", "DEFERRED", "DONE_RENAME_APPLIED", "CI_PASSED", "TOOL_LABEL", "OOS_PENDING",
    "EMERGENCY_REPAIR_BRANCH", "ORIGINAL_BRANCH_FORBIDDEN", "MAIN_REPAIR_RUN_ID", "MAIN_REPAIR_HEAD",
    "EMERGENCY_REPAIR_PR_NUMBER", "MAIN_HEALTH_REPAIR_COMMITTED", "MAIN_HEALTH_REPAIR_FAILED_RUN_ID",
    "MAIN_HEALTH_REPAIR_BASE_SHA", "MAIN_HEALTH_REPAIR_HEAD", "MAIN_HEALTH_HEAD_SHA",
];

/// Refuse a host whose `python3` cannot run the still-Python ship engine.
pub fn step8_python_guard(arguments: &[OsString]) -> ExitCode {
    if let Err(code) = parse_required_with_help(
        arguments,
        GUARD_PROGRAM,
        GUARD_USAGE,
        GUARD_HELP,
        &[],
        &[],
        &[],
    ) {
        return code;
    }
    ExitCode::from(run_python_guard())
}

fn run_python_guard() -> u8 {
    let probe = run_host_utility(
        HostUtilityProgram::Python3,
        [
            OsString::from("-c"),
            OsString::from("import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"),
        ],
        Duration::from_secs(10),
    );
    if probe.is_ok_and(|output| output.status().success()) {
        return 0;
    }
    eprintln!("ERROR: {PYTHON_GUARD_DETAIL}");
    println!("{PYTHON_GUARD_JSON}");
    4
}

/// Reconstruct and delegate the canonical create-if-absent ship-state seed.
pub fn step8_seed_initial(arguments: &[OsString]) -> ExitCode {
    let (parsed, tmpdir) = match parse_command_with_tmpdir(
        arguments,
        SEED_PROGRAM,
        SEED_USAGE,
        SEED_HELP,
        &SEED_OPTIONS,
        &[],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let state_file = tmpdir.join("ship-pr-state.sh");
    if state_has_shell_kv(&state_file) {
        eprintln!(
            "step-8-seed-initial: initial ship state is create-if-absent only; refusing to re-seed non-empty ship-pr-state.sh"
        );
        return ExitCode::from(2);
    }
    let durable = match resolve_seed_durable(&tmpdir) {
        Ok(durable) => durable,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(2);
        }
    };
    delegate_python_forward(
        seed_initial_argv(&tmpdir, state_file, &parsed, &durable),
        Duration::from_secs(600),
    )
}

struct SeedDurable {
    bootstrap: PathBuf,
    seed: PathBuf,
    session: PathBuf,
    branch: String,
    issue: String,
    run_id: String,
    repo: String,
    mapped_tool: String,
}

fn resolve_seed_durable(tmpdir: &Path) -> Result<SeedDurable, &'static str> {
    let bootstrap = tmpdir.join("bootstrap-routing.env");
    let seed = tmpdir.join("ship-seed-input.env");
    let session = tmpdir.join("session-env.sh");
    let parent = tmpdir.join("parent-issue.md");
    let sentinel = adoption_sentinel_identity(&parent);
    let branch = first_nonempty([
        read_first(&bootstrap, "BRANCH_NAME"),
        read_first(&parent, "BRANCH_NAME"),
        String::new(),
    ]);
    let issue = first_nonempty([
        read_first(&bootstrap, "ISSUE_NUMBER"),
        read_first(&parent, "ISSUE_NUMBER"),
        sentinel
            .as_ref()
            .map(|row| row.0.clone())
            .unwrap_or_default(),
    ]);
    let run_id = first_nonempty([
        read_first(&bootstrap, "RUN_ID"),
        read_first(&session, "LARCH_RUN_ID"),
        read_first(&parent, "RUN_ID"),
        sentinel
            .as_ref()
            .map(|row| row.1.clone())
            .unwrap_or_default(),
    ]);
    let repo = first_nonempty([read_first(&bootstrap, "REPO"), read_first(&session, "REPO")]);
    validate_seed_identity(&branch, &issue, &run_id, &repo)?;
    let mapped_tool = match read_first(&bootstrap, "coder").as_str() {
        "codex" => "Codex",
        "cursor" => "Cursor",
        "" => "",
        _ => "claude",
    }
    .to_owned();
    Ok(SeedDurable {
        bootstrap,
        seed,
        session,
        branch,
        issue,
        run_id,
        repo,
        mapped_tool,
    })
}

fn validate_seed_identity(
    branch: &str,
    issue: &str,
    run_id: &str,
    repo: &str,
) -> Result<(), &'static str> {
    if branch.is_empty() {
        return Err("step-8-seed-initial: BRANCH_NAME is required but missing from durable inputs");
    }
    if issue.is_empty() || !issue.chars().all(|character| character.is_ascii_digit()) {
        return Err("step-8-seed-initial: ISSUE_NUMBER must be a non-empty digit value");
    }
    if run_id.is_empty() {
        return Err("step-8-seed-initial: RUN_ID is required but missing from durable inputs");
    }
    if repo.is_empty() {
        return Err("step-8-seed-initial: REPO is required but missing from durable inputs");
    }
    Ok(())
}

fn seed_initial_argv(
    tmpdir: &Path,
    state_file: PathBuf,
    parsed: &ParsedCommandLine,
    durable: &SeedDurable,
) -> Vec<OsString> {
    let value = |flag: &str| opt_string(parsed.value(flag));
    vec![
        "ship".into(),
        "seed-initial-state".into(),
        "--tmpdir".into(),
        tmpdir.as_os_str().into(),
        "--state-file".into(),
        state_file.into_os_string(),
        "--branch".into(),
        durable.branch.clone().into(),
        "--issue".into(),
        durable.issue.clone().into(),
        "--repo".into(),
        durable.repo.clone().into(),
        "--run-id".into(),
        durable.run_id.clone().into(),
        "--manifest-path".into(),
        first_nonempty([
            value("--manifest-path"),
            read_first(&durable.seed, "MANIFEST_PATH"),
        ])
        .into(),
        "--tool-label".into(),
        first_nonempty([
            value("--tool-label"),
            read_first(&durable.seed, "TOOL_LABEL"),
            durable.mapped_tool.clone(),
            "claude".to_owned(),
        ])
        .into(),
        "--merge".into(),
        seed_option(parsed, "--merge", &durable.seed, "MERGE").into(),
        "--draft".into(),
        seed_option(parsed, "--draft", &durable.seed, "DRAFT").into(),
        "--forked".into(),
        first_nonempty([
            read_first(&durable.seed, "FORKED_TARGET"),
            read_first(&durable.session, "FORKED_TARGET"),
            "false".into(),
        ])
        .into(),
        "--repo-unavailable".into(),
        first_nonempty([
            read_first(&durable.bootstrap, "REPO_UNAVAILABLE"),
            read_first(&durable.session, "REPO_UNAVAILABLE"),
            "false".into(),
        ])
        .into(),
        "--deferred".into(),
        first_nonempty([
            read_first(&durable.bootstrap, "DEFERRED"),
            read_first(&durable.seed, "DEFERRED"),
            "false".into(),
        ])
        .into(),
        "--no-admin-fallback".into(),
        seed_option(
            parsed,
            "--no-admin-fallback",
            &durable.seed,
            "NO_ADMIN_FALLBACK",
        )
        .into(),
        "--no-logs-commit".into(),
        seed_option(parsed, "--no-logs-commit", &durable.seed, "NO_LOGS_COMMIT").into(),
        "--expected-session-id".into(),
        read_trimmed(&tmpdir.join("session-id")).into(),
        "--expected-tmpdir-basename-prefix".into(),
        expected_tmpdir_basename_prefix().into(),
        "--stall-tracking".into(),
        first_nonempty([value("--stall-tracking"), "false".into()]).into(),
        "--stall-step".into(),
        value("--stall-step").into(),
        "--bail-reason".into(),
        value("--bail-reason").into(),
        "--bail-failure-detail-log".into(),
        value("--bail-failure-detail-log").into(),
    ]
}

fn seed_option(parsed: &ParsedCommandLine, flag: &str, seed: &Path, key: &str) -> String {
    first_nonempty([
        opt_string(parsed.value(flag)),
        read_first(seed, key),
        "false".into(),
    ])
}

/// Launch or run the Step 8 ship bgjob.
pub fn step8_ship(arguments: &[OsString]) -> ExitCode {
    let (parsed, tmpdir) = match parse_command_with_tmpdir(
        arguments,
        SHIP_PROGRAM,
        SHIP_USAGE,
        SHIP_HELP,
        &["--merge-result-env"],
        &["--bgjob-child"],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    if parsed.flag("--bgjob-child") {
        let merge_env = opt_string(parsed.value("--merge-result-env"));
        if merge_env.is_empty() {
            eprintln!("step-8-ship: --merge-result-env is required in child mode");
            return ExitCode::from(2);
        }
        return step8_ship_child(&tmpdir, &merge_env);
    }
    let result = (|| {
        let merge = safe_merge_env(
            &tmpdir,
            &tmpdir.join("bgjob").join(format!("{SHIP_STEP}.merge.env")),
        )?;
        run_bgjob_adapt(
            &tmpdir,
            SHIP_STEP,
            SHIP_BUDGET_SECONDS,
            "step-8-ship",
            &merge,
            &[],
            &[],
            None,
            true,
        )
    })();
    result.unwrap_or_else(|_error| {
        println!("BGJOB_ERROR=invalid-input");
        ExitCode::from(2)
    })
}

fn step8_ship_child(tmpdir: &Path, merge_result_env: &str) -> ExitCode {
    let state = tmpdir.join("ship-pr-state.sh");
    let selected = |environment: &str, key: &str, default: &str| {
        first_nonempty([
            env::var(environment).unwrap_or_default(),
            read_first(&state, key),
            default.to_owned(),
        ])
    };
    let branch = selected("BRANCH_NAME", "BRANCH_NAME", "");
    let issue = selected("ISSUE_NUMBER", "ISSUE_NUMBER", "");
    let run_id = selected("RUN_ID", "RUN_ID", "");
    let repo = selected("REPO", "REPO", "");
    let merge = selected("merge", "MERGE", "false");
    let draft = selected("draft", "DRAFT", "false");
    let forked = selected("forked_target", "FORKED_TARGET", "false");
    let repo_unavailable = selected("REPO_UNAVAILABLE", "REPO_UNAVAILABLE", "false");
    let manifest = selected("MANIFEST_PATH", "MANIFEST_PATH", "");
    let tool = selected("coder", "TOOL_LABEL", "claude");
    let no_admin = selected("no_admin_fallback", "NO_ADMIN_FALLBACK", "false");
    let no_logs = selected("no_logs_commit", "NO_LOGS_COMMIT", "false");
    for (name, value) in [
        ("BRANCH_NAME", branch.as_str()),
        ("RUN_ID", run_id.as_str()),
        ("REPO", repo.as_str()),
    ] {
        if value.is_empty() {
            eprintln!(
                "step-8-ship: missing {name} (not exported and absent from ship-pr-state.sh)"
            );
            return ExitCode::from(2);
        }
    }
    let guard = run_python_guard();
    if guard != 0 {
        return ExitCode::from(guard);
    }
    emit_phantom_probe();
    delegate_python_forward(
        vec![
            "ship".into(),
            "pr".into(),
            "--branch".into(),
            branch.into(),
            "--issue".into(),
            issue.into(),
            "--repo".into(),
            repo.into(),
            "--run-id".into(),
            run_id.into(),
            "--tmpdir".into(),
            tmpdir.as_os_str().into(),
            "--manifest-path".into(),
            manifest.into(),
            "--state-file".into(),
            state.into_os_string(),
            "--tool-label".into(),
            tool.into(),
            "--merge".into(),
            merge.into(),
            "--draft".into(),
            draft.into(),
            "--forked".into(),
            forked.into(),
            "--repo-unavailable".into(),
            repo_unavailable.into(),
            "--no-admin-fallback".into(),
            no_admin.into(),
            "--no-logs-commit".into(),
            no_logs.into(),
            "--result-env-path".into(),
            merge_result_env.into(),
            "--expected-session-id".into(),
            read_trimmed(&tmpdir.join("session-id")).into(),
            "--expected-tmpdir-basename-prefix".into(),
            expected_tmpdir_basename_prefix().into(),
        ],
        Duration::from_secs(u64::from(SHIP_BUDGET_SECONDS)),
    )
}

fn emit_phantom_probe() {
    for line in crate::phantom_probe_lines("8-pre-ship", None, true) {
        eprintln!("{line}");
    }
}

/// Run the OOS disposition checkpoint and its Step 8 post-pass bookkeeping.
pub fn step8_oos_checkpoint(arguments: &[OsString]) -> ExitCode {
    if let Err(code) =
        parse_required_with_help(arguments, OOS_PROGRAM, OOS_USAGE, OOS_HELP, &[], &[], &[])
    {
        return code;
    }
    let Ok(tmpdir) = tmpdir_from_env() else {
        return ExitCode::from(2);
    };
    rehydrate_session(&tmpdir);
    let mut argv = vec![
        "oos".into(),
        "disposition-checkpoint".into(),
        "--implement-tmpdir".into(),
        tmpdir.as_os_str().into(),
    ];
    if let Some(design) = env::var_os("DESIGN_TMPDIR").filter(|value| !value.is_empty()) {
        argv.extend(["--design-tmpdir".into(), design]);
    }
    let result = match verified_larch(&argv) {
        Ok(output) => output,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::from(1);
        }
    };
    let rc = result.status().code().unwrap_or(1);
    let stderr = result.stderr();
    let err = tmpdir.join("oos-disposition-checkpoint.stderr.log");
    let diagnostic_safe = if stderr.is_empty() {
        private_input_safe(&err)
    } else {
        append_private_bytes(&err, stderr, &tmpdir)
    };
    if diagnostic_safe {
        log_checkpoint_failure(&tmpdir, rc, &err);
    } else {
        eprintln!("step-8-oos-checkpoint: refusing unsafe stderr log");
    }
    if rc != 0 {
        println!("OOS_CHECKPOINT_RC={rc}");
        println!("NEXT_ACTION=stall");
        return ExitCode::SUCCESS;
    }
    match checkpoint_bookkeeping(&tmpdir) {
        Ok(()) => {
            refresh_execution_issues(&tmpdir);
            println!("OOS_CHECKPOINT_RC=0");
            println!("NEXT_ACTION=reship");
        }
        Err(error) => {
            eprintln!("step-8-oos-checkpoint: bookkeeping failed: {error}");
            println!("OOS_CHECKPOINT_RC=2");
            println!("NEXT_ACTION=stall");
        }
    }
    ExitCode::SUCCESS
}

fn checkpoint_bookkeeping(tmpdir: &Path) -> Result<(), String> {
    let run_id = resolve_disposition_run_id(tmpdir);
    if validate_run_id(&run_id).is_err() {
        return Err("cannot resolve canonical run id".to_owned());
    }
    let run_dir = tmpdir.join("larch-logs").join("implement").join(&run_id);
    let stats = run_dir.join("run-statistics.md");
    let stats_existed = stats.is_file();
    let mut stamp_attempted = false;
    let result = (|| {
        let count = read_universal_newlines(&run_dir.join("oos-issues.ndjson"))
            .map_or(0, |text| ndjson_filed_evidence(&text).len());
        private_atomic_write(
            &stats,
            &format!("Run {run_id}: {count} OOS issue(s) filed.\n"),
            tmpdir,
        )
        .map_err(|error| error.to_string())?;
        stamp_attempted = true;
        if !stamp_step9a1(tmpdir, &run_id, true)? {
            return Err("manifest stamp returned false".to_owned());
        }
        patch_oos_pending(&tmpdir.join("ship-pr-state.sh"))
    })();
    if result.is_err() {
        let rollback_complete = !stamp_attempted || stamp_step9a1(tmpdir, &run_id, false).is_ok();
        if rollback_complete && !stats_existed {
            let _ = unlink_safe(&stats, tmpdir);
        }
    }
    result
}

fn stamp_step9a1(tmpdir: &Path, run_id: &str, value: bool) -> Result<bool, String> {
    let manifest = tmpdir
        .join("larch-logs")
        .join("implement")
        .join(run_id)
        .join("manifest.json");
    if !manifest.is_file() {
        return Ok(false);
    }
    let output = verified_larch(&[
        "run-log".into(),
        "manifest".into(),
        "--log-root".into(),
        tmpdir.join("larch-logs").into_os_string(),
        "--skill".into(),
        "implement".into(),
        "--run-id".into(),
        run_id.into(),
        "--field".into(),
        format!("steps_ran.step9a1={value}").into(),
    ])
    .map_err(|error| format!("run-log manifest steps_ran.step9a1 update failed: {error}"))?;
    if !output.status().success() {
        let detail = output_detail(&output);
        return Err(format!(
            "run-log manifest steps_ran.step9a1 update failed: {detail}"
        ));
    }
    Ok(true)
}

fn resolve_disposition_run_id(tmpdir: &Path) -> String {
    let state = last_value_option(&tmpdir.join("finalize-state.sh"), "RUN_ID")
        .or_else(|| last_value_option(&tmpdir.join("ship-pr-state.sh"), "RUN_ID"))
        .unwrap_or_default();
    if !state.is_empty() {
        return state;
    }
    let session = tmpdir.join("session-id");
    if session.is_file() {
        return read_trimmed(&session);
    }
    let root = tmpdir.join("larch-logs").join("implement");
    let mut matches: Vec<PathBuf> = RunLogCorpus::new(root)
        .safe_child_run_directories()
        .into_iter()
        .filter(|path| path.join("oos-issues.ndjson").is_file())
        .collect();
    matches.sort();
    if matches.len() == 1 {
        return matches[0]
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_default();
    }
    String::new()
}

fn log_checkpoint_failure(tmpdir: &Path, rc: i32, err: &Path) {
    if rc == 0 {
        return;
    }
    let log = tmpdir.join("execution-issues.md");
    let text = read_universal_newlines(&log).unwrap_or_default();
    let already = if rc == 1 {
        text.contains("Step step-8-oos-checkpoint —")
            || (text.contains("step-8-oos-checkpoint")
                && !text.contains("step-8-oos-checkpoint-validation"))
    } else {
        text.contains("step-8-oos-checkpoint-validation")
    };
    if already {
        return;
    }
    let site = if rc == 1 {
        "step-8-oos-checkpoint"
    } else {
        "step-8-oos-checkpoint-validation"
    };
    let _ = verified_larch(&[
        "run-log".into(),
        "append-failure".into(),
        "--log".into(),
        log.into_os_string(),
        "--site".into(),
        site.into(),
        "--tool".into(),
        "larch oos disposition-checkpoint".into(),
        "--exit-code".into(),
        rc.to_string().into(),
        "--category".into(),
        "Tool Failures".into(),
        "--output-file".into(),
        err.as_os_str().into(),
        "--redact".into(),
    ]);
}

fn refresh_execution_issues(tmpdir: &Path) {
    let _ = verified_larch(&[
        "execution-issues".into(),
        "refresh".into(),
        "--implement-tmpdir".into(),
        tmpdir.as_os_str().into(),
        "--best-effort".into(),
    ]);
}

fn patch_oos_pending(path: &Path) -> Result<(), String> {
    patch_ship_state_keys(path, &[("OOS_PENDING", "false".to_owned())], &[])
}

/// Patch a reviewed subset of the durable ship state without widening its key
/// or value grammar.
pub fn patch_ship_state_keys(
    state_path: &Path,
    updates: &[(&str, String)],
    removals: &[&str],
) -> Result<(), String> {
    let parent = state_path.parent().ok_or("ship state has no parent")?;
    fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    let temporary = state_path.with_file_name(format!(
        "{}.tmp",
        state_path
            .file_name()
            .and_then(OsStr::to_str)
            .unwrap_or_default()
    ));
    if let Ok(metadata) = fs::symlink_metadata(state_path) {
        if metadata.file_type().is_symlink() {
            return Err(format!(
                "refusing to write symlinked ship state path: {}",
                state_path.display()
            ));
        }
        if !metadata.is_file() {
            return Err(format!(
                "refusing patch-only ship state write: {}",
                state_path.display()
            ));
        }
    }
    if fs::symlink_metadata(&temporary).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(format!(
            "refusing to write symlinked ship state path: {}",
            state_path.display()
        ));
    }
    let text = fs::read_to_string(state_path).map_err(|_error| {
        format!(
            "refusing patch-only ship state write: {}",
            state_path.display()
        )
    })?;
    let document = KvDocument::parse(&text, ParseOptions::legacy())
        .map_err(|_error| format!("cannot patch ship state: {}", state_path.display()))?;
    if let Some(key) = removals
        .iter()
        .find(|key| !SHIP_STATE_ALLOWED_KEYS.contains(key))
    {
        return Err(format!("invalid ship state patch key: {key}"));
    }
    let mut rows: Vec<(String, String)> = Vec::new();
    for row in document.rows() {
        let (key, value) = (row.key(), row.value());
        if !SHIP_STATE_ALLOWED_KEYS.contains(&key) || removals.contains(&key) {
            continue;
        }
        if let Some(existing) = rows.iter_mut().find(|row| row.0 == key) {
            value.clone_into(&mut existing.1);
        } else {
            rows.push((key.to_owned(), value.to_owned()));
        }
    }
    if rows.is_empty() {
        return Err(format!(
            "refusing patch-only ship state write: {}",
            state_path.display()
        ));
    }
    for (key, value) in updates {
        if !SHIP_STATE_ALLOWED_KEYS.contains(key) {
            return Err(format!("invalid ship state patch key: {key}"));
        }
        if let Some(row) = rows.iter_mut().find(|row| row.0 == *key) {
            value.clone_into(&mut row.1);
        } else {
            rows.push(((*key).to_owned(), value.clone()));
        }
    }
    validate_ship_rows(&rows)?;
    let mut body = String::new();
    for (key, value) in rows {
        body.push_str(&key);
        body.push('=');
        body.push_str(&value);
        body.push('\n');
    }
    private_atomic_write(state_path, &body, parent)
        .map_err(|_error| format!("cannot patch ship state: {}", state_path.display()))
}

fn validate_ship_rows(rows: &[(String, String)]) -> Result<(), String> {
    for (key, value) in rows {
        if value.contains(['\n', '\r']) {
            return Err(format!("invalid newline in ship state value: {key}"));
        }
        if key == "BRANCH_NAME"
            && !value.is_empty()
            && (value.starts_with('-')
                || value.ends_with('/')
                || value.contains("..")
                || value.contains("//")
                || value.contains("@{")
                || !value
                    .chars()
                    .all(|c| c.is_ascii_alphanumeric() || "._/-".contains(c)))
        {
            return Err("invalid ship state BRANCH_NAME".to_owned());
        }
        if key == "PR_URL" && !valid_pr_url(value) {
            return Err("invalid ship state PR_URL".to_owned());
        }
        if key == "MERGE_RESULT"
            && !value.is_empty()
            && ![
                "merged",
                "admin_merged",
                "queued",
                "main_advanced",
                "ci_not_ready",
                "version_already_published",
                "policy_denied",
                "admin_failed",
                "review_required",
                "error",
                "already_merged",
            ]
            .contains(&value.as_str())
        {
            return Err("invalid ship state MERGE_RESULT".to_owned());
        }
    }
    Ok(())
}

fn valid_pr_url(value: &str) -> bool {
    value.is_empty()
        || (value
            .strip_prefix("http://")
            .or_else(|| value.strip_prefix("https://"))
            .is_some_and(|suffix| !suffix.is_empty())
            && value.chars().all(|character| {
                character.is_ascii_alphanumeric() || "._~:/?#[]@!$&'()*+,;=%-".contains(character)
            }))
}

fn verified_larch(arguments: &[OsString]) -> Result<ProcessOutput, String> {
    let root = resolve_plugin_root()?;
    let cwd = env::current_dir().map_err(|error| error.to_string())?;
    delegate_verified_larch(&cwd, &root, arguments)
}

fn delegate_python_forward(arguments: Vec<OsString>, timeout: Duration) -> ExitCode {
    match delegate_python(arguments, timeout) {
        Ok(output) => {
            forward_output(&output);
            ExitCode::from(u8::try_from(output.status().code().unwrap_or(1)).unwrap_or(1))
        }
        Err(error) => {
            eprintln!("{error}");
            ExitCode::from(1)
        }
    }
}

pub fn state_has_shell_kv(path: &Path) -> bool {
    read_kv_document(path).is_some_and(|document| {
        document.rows().iter().any(|row| {
            let key = row.key();
            let mut chars = key.chars();
            chars
                .next()
                .is_some_and(|c| c.is_ascii_alphabetic() || c == '_')
                && chars.all(|c| c.is_ascii_alphanumeric() || c == '_')
        })
    })
}

fn read_first(path: &Path, key: &str) -> String {
    read_kv_document(path)
        .and_then(|document| document.select(DuplicatePolicy::First).remove(key))
        .unwrap_or_default()
}

fn last_value_option(path: &Path, key: &str) -> Option<String> {
    read_kv_document(path).and_then(|document| document.select(DuplicatePolicy::Last).remove(key))
}

fn read_kv_document(path: &Path) -> Option<KvDocument> {
    read_universal_newlines(path)
        .and_then(|text| KvDocument::parse(&text, ParseOptions::legacy()).ok())
}

fn read_trimmed(path: &Path) -> String {
    read_universal_newlines(path)
        .map(|text| text.trim().to_owned())
        .unwrap_or_default()
}

fn first_nonempty<const N: usize>(values: [String; N]) -> String {
    values
        .into_iter()
        .find(|value| !value.is_empty())
        .unwrap_or_default()
}

fn append_private_bytes(path: &Path, bytes: &[u8], root: &Path) -> bool {
    let mut body = match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.is_file() => match fs::read(path) {
            Ok(body) => body,
            Err(_error) => return false,
        },
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Vec::new(),
        Ok(_) | Err(_) => return false,
    };
    body.extend_from_slice(bytes);
    private_atomic_write(path, &String::from_utf8_lossy(&body), root).is_ok()
}

fn private_input_safe(path: &Path) -> bool {
    match fs::symlink_metadata(path) {
        Ok(metadata) => metadata.is_file(),
        Err(error) => error.kind() == std::io::ErrorKind::NotFound,
    }
}

fn output_detail(output: &ProcessOutput) -> String {
    let stderr = String::from_utf8_lossy(output.stderr());
    if !stderr.trim().is_empty() {
        return stderr.trim().chars().take(300).collect();
    }
    let stdout = String::from_utf8_lossy(output.stdout());
    if !stdout.trim().is_empty() {
        return stdout.trim().chars().take(300).collect();
    }
    "run-log manifest failed".to_owned()
}
