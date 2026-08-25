//! Rust owners for ship pre-driver routing and pre-fix rebase repair (#8622).
//!
//! The commands in this module preserve the frozen Python wire contracts while
//! composing existing Rust owners for scope validation, Git, GitHub, OOS, and
//! stall recovery. No production path re-enters the retired Python handlers.

use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::OsString,
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    thread,
    time::Duration,
};

use larch_adapters::GixRepository;
use larch_core::{
    DuplicatePolicy, KvDocument, MalformedLinePolicy, ParseOptions, ProcessOutput,
    RepositoryRead as _, Revision, StatusOptions, emit_kv, private_atomic_write,
    read_confined_regular_text, read_confined_result_env, read_universal_newlines,
};

use crate::{
    argparse_compat::parse_required_with_help,
    implement_child_seam::resolve_plugin_root,
    implement_dispatch_commands::{
        delegate_verified_larch, opt_string, rehydrate_session, resolve_repo_root_output,
    },
    implement_scope_disposition_commands::validate_ship_disposition,
    implement_ship_commands::{patch_ship_state_keys, state_has_shell_kv},
    push_network::current_branch_from,
    push_rebase::sorted_lossy_unmerged_paths,
};

const ROUTE_PROGRAM: &str = "cli.py ship route-exit";
const ROUTE_USAGE: &str =
    "usage: cli.py ship route-exit [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]";
const ROUTE_HELP: &str = concat!(
    "usage: cli.py ship route-exit [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --implement-tmpdir IMPLEMENT_TMPDIR",
);
const NORMALIZE_PROGRAM: &str = "cli.py ship normalize-assessment-handoff";
const NORMALIZE_USAGE: &str = concat!(
    "usage: cli.py ship normalize-assessment-handoff [-h]\n",
    "                                                [--implement-tmpdir IMPLEMENT_TMPDIR]",
);
const NORMALIZE_HELP: &str = concat!(
    "usage: cli.py ship normalize-assessment-handoff [-h]\n",
    "                                                [--implement-tmpdir IMPLEMENT_TMPDIR]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --implement-tmpdir IMPLEMENT_TMPDIR",
);
const PRE_DRIVER_PROGRAM: &str = "cli.py ship pre-driver";
const PRE_DRIVER_USAGE: &str = "usage: cli.py ship pre-driver [-h]";
const PRE_DRIVER_HELP: &str = concat!(
    "usage: cli.py ship pre-driver [-h]\n",
    "\n",
    "options:\n",
    "  -h, --help  show this help message and exit",
);
const PRE_FIX_PROGRAM: &str = "cli.py ship pre-fix-rebase";
const PRE_FIX_USAGE: &str = concat!(
    "usage: cli.py ship pre-fix-rebase [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]\n",
    "                                  [--cwd CWD]",
);
const PRE_FIX_HELP: &str = concat!(
    "usage: cli.py ship pre-fix-rebase [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]\n",
    "                                  [--cwd CWD]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --implement-tmpdir IMPLEMENT_TMPDIR\n",
    "  --cwd CWD",
);

const RESULT_ENV: &str = "bgjob/implement-step8-ship.result.env";
const HANDOFF_ENV: &str = ".ship-route-exit-handoff.env";
const DETAIL_FILE: &str = ".ship-route-exit-detail.txt";
const RETRY_FILE: &str = "ship-pr-net-retries-python.count";
const PRE_FIX_SENTINEL: &str = ".ship-pre-fix-rebase-ok";
const PHASE14_FLAG: &str = "ship-pr-rrr-after-phase14.flag";
const SHIP_STATE: &str = "ship-pr-state.sh";
const SHIP_STEP: &str = "implement-step8-ship";
const CONFLICT_RESUME_PHASE: &str = "ship-pr-rrr-phase14";
const CONFLICT_CALLER_KIND: &str = "ship_pr_pre_push";
const CONFLICT_TERMINAL_CLEAR_KEYS: [&str; 5] = [
    "EXIT_CODE",
    "BAIL_REASON",
    "BAIL_NEEDS_USER_INPUT",
    "FAILED_RUN_ID",
    "BAIL_FAILURE_DETAIL_LOG",
];
const DETAIL_FILE_MAX: usize = 300;
const TRANSIENT_STALL_RETRY: i64 = 4;
const TRANSIENT_DELAY_SECONDS: u64 = 30;

const LEDGER_KEYS: [&str; 8] = [
    "ledger_ready",
    "ledger_site",
    "ledger_trigger",
    "ledger_step",
    "ledger_phase",
    "ledger_dispatcher",
    "ledger_exit_code",
    "ledger_failure_detail_log",
];
const HEALTH_HANDOFF_KEYS: [&str; 10] = [
    "MAIN_HEALTH_HEAD_SHA",
    "MAIN_HEALTH_REPAIR_COMMITTED",
    "MAIN_HEALTH_REPAIR_FAILED_RUN_ID",
    "MAIN_HEALTH_REPAIR_BASE_SHA",
    "MAIN_HEALTH_REPAIR_HEAD",
    "EMERGENCY_REPAIR_BRANCH",
    "ORIGINAL_BRANCH_FORBIDDEN",
    "MAIN_REPAIR_RUN_ID",
    "MAIN_REPAIR_HEAD",
    "EMERGENCY_REPAIR_PR_NUMBER",
];

/// Route one completed Step 8 ship result into its durable prompt handoff.
pub fn route_exit(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        ROUTE_PROGRAM,
        ROUTE_USAGE,
        ROUTE_HELP,
        &["--implement-tmpdir"],
        &[],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = selected_tmpdir(opt_string(parsed.value("--implement-tmpdir")));
    if tmpdir.as_os_str().is_empty() {
        eprintln!(
            "ship route-exit: --implement-tmpdir is required or IMPLEMENT_TMPDIR must be set"
        );
        return ExitCode::from(2);
    }
    let handoff = tmpdir.join(HANDOFF_ENV);
    let (driver_rc, fields) = match read_route_result(&tmpdir) {
        Ok(result) => result,
        Err(message) => return route_failure(&handoff, &message),
    };
    let mut action = match classify_route(driver_rc, &fields) {
        Ok(action) => action,
        Err(message) => return route_failure(&handoff, &message),
    };
    let route_fields = if driver_rc == 4 {
        let conflict = conflict_handoff_fields(&tmpdir);
        if !conflict.is_empty() {
            "conflict-fix".clone_into(&mut action);
            conflict
        } else if fields
            .get("DETAIL")
            .is_some_and(|detail| detail == "no-ci-checks-observed")
            && safe_regular(&tmpdir.join(PHASE14_FLAG))
        {
            "reship".clone_into(&mut action);
            BTreeMap::new()
        } else {
            BTreeMap::new()
        }
    } else {
        BTreeMap::new()
    };
    let mut delay = 0;
    if action == "transient" {
        let count_file = tmpdir.join(RETRY_FILE);
        let retry = read_retry_count(&count_file).saturating_add(1);
        if let Err(error) = write_private(&count_file, &format!("{retry}\n"), &tmpdir) {
            return route_failure(
                &handoff,
                &format!("cannot persist transient retry counter: {error}"),
            );
        }
        if retry >= TRANSIENT_STALL_RETRY {
            seed_transient_stall(&tmpdir);
            "stall".clone_into(&mut action);
        } else {
            delay = TRANSIENT_DELAY_SECONDS;
            thread::sleep(Duration::from_secs(delay));
            "reship".clone_into(&mut action);
        }
    }
    if let Err(error) = write_route_handoff(&tmpdir, &fields, &action, delay, &route_fields) {
        return route_failure(
            &handoff,
            &format!("cannot write route-exit handoff: {error}"),
        );
    }
    emit_kv("NEXT_ACTION", &action);
    ExitCode::SUCCESS
}

/// Normalize legacy assessment aliases into the canonical combined handoff.
pub fn normalize_assessment_handoff(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        NORMALIZE_PROGRAM,
        NORMALIZE_USAGE,
        NORMALIZE_HELP,
        &["--implement-tmpdir"],
        &[],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = selected_tmpdir(opt_string(parsed.value("--implement-tmpdir")));
    if tmpdir.as_os_str().is_empty() {
        eprintln!("ship normalize-assessment-handoff: --implement-tmpdir is required");
        return ExitCode::from(2);
    }
    let canonical = match normalize_handoff(&tmpdir) {
        Ok(canonical) => canonical,
        Err(message) => {
            eprintln!("ship normalize-assessment-handoff: {message}");
            return ExitCode::from(2);
        }
    };
    emit_kv("NEXT_ACTION", "assessments");
    emit_kv("ASSESSMENT_REQUESTED_KINDS", &canonical);
    ExitCode::SUCCESS
}

/// Run the pre-ship guard, scope gate, initial state seed, and OOS filing gate.
pub fn pre_driver(arguments: &[OsString]) -> ExitCode {
    if let Err(code) = parse_required_with_help(
        arguments,
        PRE_DRIVER_PROGRAM,
        PRE_DRIVER_USAGE,
        PRE_DRIVER_HELP,
        &[],
        &[],
        &[],
    ) {
        return code;
    }
    let raw = env::var_os("IMPLEMENT_TMPDIR").unwrap_or_default();
    if raw.is_empty() {
        eprintln!("IMPLEMENT_TMPDIR required");
        emit_kv("NEXT_ACTION", "halt-seed");
        return ExitCode::from(2);
    }
    let tmpdir = PathBuf::from(raw);
    rehydrate_session(&tmpdir);
    let Some(repo_root) = resolve_repo_root(&tmpdir) else {
        emit_kv("NEXT_ACTION", "halt-seed");
        return ExitCode::from(2);
    };

    let state = tmpdir.join(SHIP_STATE);
    let manifest = resolve_manifest(&tmpdir, &state);
    match validate_ship_disposition(&tmpdir, &repo_root, manifest.as_deref()) {
        Ok(validation) if validation.ok => {}
        Ok(validation) if validation.reason.starts_with("scope-disposition-") => {
            emit_kv("needs_user_reason", "scope-disposition");
            emit_kv("NEXT_ACTION", "halt-scope-disposition");
            return ExitCode::from(3);
        }
        Ok(validation) => {
            eprintln!("ship pre-driver: {}", validation.reason);
            return ExitCode::from(4);
        }
        Err(message) => {
            eprintln!("ship pre-driver: {message}");
            return ExitCode::from(4);
        }
    }

    if !state_has_shell_kv(&state) {
        let seed = run_larch(
            &repo_root,
            &["implement".into(), "step-8-seed-initial".into()],
        );
        let seed_rc = forward_child_to_stderr(&seed);
        if seed_rc != 0 {
            emit_kv("NEXT_ACTION", "halt-seed");
            return ExitCode::from(u8::try_from(seed_rc).unwrap_or(1));
        }
    }
    let oos = run_larch(
        &repo_root,
        &[
            "oos".into(),
            "file".into(),
            "--implement-tmpdir".into(),
            tmpdir.as_os_str().into(),
        ],
    );
    let oos_rc = forward_child_to_stderr(&oos);
    if oos_rc != 0 {
        let security_sidecar = oos.as_ref().ok().is_some_and(|output| {
            serde_json::from_slice::<serde_json::Value>(output.stdout())
                .ok()
                .and_then(|value| {
                    value
                        .get("status")
                        .and_then(|status| status.as_str())
                        .map(str::to_owned)
                })
                .is_some_and(|status| status == "security_sidecar_present")
        });
        emit_kv(
            "NEXT_ACTION",
            if security_sidecar {
                "oos-pipeline"
            } else {
                "halt-oos"
            },
        );
        return ExitCode::from(u8::try_from(oos_rc).unwrap_or(1));
    }
    emit_kv("NEXT_ACTION", "ship");
    ExitCode::SUCCESS
}

/// Rebase and force-push the persisted feature branch before autonomous repair.
pub fn pre_fix_rebase(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        PRE_FIX_PROGRAM,
        PRE_FIX_USAGE,
        PRE_FIX_HELP,
        &["--implement-tmpdir", "--cwd"],
        &[],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = selected_tmpdir(opt_string(parsed.value("--implement-tmpdir")));
    if !tmpdir.is_dir() {
        return pre_fix_failure("--implement-tmpdir is required and must be an existing directory");
    }
    let _ = fs::remove_file(tmpdir.join(PRE_FIX_SENTINEL));
    let cwd_arg = opt_string(parsed.value("--cwd"));
    let context = match prepare_pre_fix(&tmpdir, &cwd_arg) {
        Ok(context) => context,
        Err(code) => return code,
    };
    run_pre_fix_rebase(&tmpdir, &context)
}

struct PreFixContext {
    state_path: PathBuf,
    state: BTreeMap<String, String>,
    cwd: PathBuf,
}

fn prepare_pre_fix(tmpdir: &Path, cwd_arg: &str) -> Result<PreFixContext, ExitCode> {
    let state_path = tmpdir.join(SHIP_STATE);
    if !safe_regular(&state_path) {
        return Err(pre_fix_failure("ship-pr-state.sh is missing"));
    }
    let state = read_kv(&state_path);
    if state.get("REPO").is_none_or(String::is_empty) {
        return Err(pre_fix_failure("REPO is missing from ship-pr-state.sh"));
    }
    if state.get("RUN_ID").is_none_or(String::is_empty) {
        return Err(pre_fix_failure("RUN_ID is missing from ship-pr-state.sh"));
    }
    let cwd = if cwd_arg.is_empty() {
        resolve_repo_root(tmpdir).unwrap_or_else(|| env::current_dir().unwrap_or_default())
    } else {
        PathBuf::from(cwd_arg)
    };
    if let Some(error) = validate_checkout(&cwd, &state) {
        return Err(pre_fix_failure(&error));
    }
    Ok(PreFixContext {
        state_path,
        state,
        cwd,
    })
}

fn run_pre_fix_rebase(tmpdir: &Path, context: &PreFixContext) -> ExitCode {
    let PreFixContext {
        state_path,
        state,
        cwd,
    } = context;
    let route_fields = conflict_handoff_fields(tmpdir);
    if rebase_in_progress(cwd) {
        if route_fields.is_empty() {
            return emit_pre_fix("stall", "stall", "");
        }
        if let Err(error) = persist_conflict(tmpdir, &route_fields, false) {
            return pre_fix_failure(&format!("cannot write conflict handoff: {error}"));
        }
        return finish_pre_fix(tmpdir, "conflict", "conflict-fix", "");
    }
    if !route_fields.is_empty() {
        if let Err(error) = persist_conflict(tmpdir, &route_fields, false) {
            return pre_fix_failure(&format!("cannot write conflict handoff: {error}"));
        }
        return finish_pre_fix(tmpdir, "conflict", "conflict-fix", "");
    }
    if phase14_skip_allowed(tmpdir) || state.get("PR_CLOSED").is_some_and(|value| truthy(value)) {
        return finish_pre_fix(tmpdir, "skip", "continue", "");
    }

    let before = head_oid(cwd);
    let remote = if state
        .get("FORKED_TARGET")
        .is_some_and(|value| truthy(value))
    {
        "upstream"
    } else {
        "origin"
    };
    let first = run_rebase_command(cwd, remote, true);
    if first.setup_error {
        return pre_fix_failure(&format!("handoff setup failed: {}", first.detail));
    }
    if first.rc == 1 && !first.conflicts.is_empty() {
        let conflict = conflict_fields(&first.conflicts);
        if let Err(error) = persist_conflict(tmpdir, &conflict, true) {
            return pre_fix_failure(&format!("cannot write conflict handoff: {error}"));
        }
        return finish_pre_fix(tmpdir, "conflict", "conflict-fix", "");
    }
    if first.rc != 0 {
        return emit_pre_fix("stall", "stall", &first.detail);
    }

    let sync = match run_larch(
        cwd,
        &[
            "git".into(),
            "sync-local-main".into(),
            "--base-remote".into(),
            remote.into(),
            "--base-ref".into(),
            "main".into(),
        ],
    ) {
        Ok(output) => output,
        Err(message) => return pre_fix_failure(&format!("handoff setup failed: {message}")),
    };
    if !sync.status().success()
        && String::from_utf8_lossy(sync.stderr()).contains("refusing to update local 'main'")
    {
        return emit_pre_fix(
            "stall",
            "stall",
            "cli.py git sync-local-main: refusing to update local 'main' while checked out on main",
        );
    }

    let pushed = run_rebase_command(cwd, remote, false);
    if pushed.setup_error {
        return pre_fix_failure(&format!("handoff setup failed: {}", pushed.detail));
    }
    if pushed.rc == 1 && !pushed.conflicts.is_empty() {
        let conflict = conflict_fields(&pushed.conflicts);
        if let Err(error) = persist_conflict(tmpdir, &conflict, true) {
            return pre_fix_failure(&format!("cannot write conflict handoff: {error}"));
        }
        return finish_pre_fix(tmpdir, "conflict", "conflict-fix", "");
    }
    if pushed.rc != 0 {
        return emit_pre_fix("stall", "stall", &pushed.detail);
    }
    if before != head_oid(cwd) {
        let count = state
            .get("REBASE_COUNT")
            .and_then(|value| value.trim().parse::<i64>().ok())
            .unwrap_or(0)
            .saturating_add(1);
        if let Err(error) =
            patch_ship_state_keys(state_path, &[("REBASE_COUNT", count.to_string())], &[])
        {
            return pre_fix_failure(&format!("handoff setup failed: {error}"));
        }
    }
    finish_pre_fix(tmpdir, "ok", "continue", "")
}

struct RebaseCommandResult {
    rc: i32,
    conflicts: String,
    detail: String,
    setup_error: bool,
}

fn run_rebase_command(cwd: &Path, remote: &str, no_push: bool) -> RebaseCommandResult {
    let mut arguments: Vec<OsString> = vec!["push".into(), "rebase".into()];
    if no_push {
        arguments.extend(["--no-push".into(), "--keep-on-conflict".into()]);
    }
    arguments.extend([
        "--base-remote".into(),
        remote.into(),
        "--base-ref".into(),
        "main".into(),
    ]);
    match run_larch(cwd, &arguments) {
        Ok(output) => {
            let fields = KvDocument::parse(
                &String::from_utf8_lossy(output.stdout()),
                ParseOptions::legacy(),
            )
            .map(|document| document.select(DuplicatePolicy::Last))
            .unwrap_or_default();
            let stderr = String::from_utf8_lossy(output.stderr());
            let detail = [
                fields
                    .get("REBASE_ERROR")
                    .map(String::as_str)
                    .unwrap_or_default(),
                fields
                    .get("PUSH_ERROR")
                    .map(String::as_str)
                    .unwrap_or_default(),
                stderr.trim(),
            ]
            .into_iter()
            .find(|value| !value.is_empty())
            .unwrap_or("rebase failed");
            let rc = output.status().code().unwrap_or(1);
            let conflicts = fields
                .get("CONFLICT_FILES")
                .cloned()
                .filter(|value| !value.is_empty())
                .unwrap_or_else(|| {
                    if rc == 1 {
                        unmerged_paths(cwd)
                    } else {
                        String::new()
                    }
                });
            RebaseCommandResult {
                rc,
                conflicts,
                detail: safe_line(detail),
                setup_error: false,
            }
        }
        Err(message) => RebaseCommandResult {
            rc: 1,
            conflicts: String::new(),
            detail: safe_line(&message),
            setup_error: true,
        },
    }
}

fn validate_checkout(cwd: &Path, state: &BTreeMap<String, String>) -> Option<String> {
    let branch = current_branch_from(cwd);
    let expected_branch = state
        .get("BRANCH_NAME")
        .map(String::as_str)
        .unwrap_or_default();
    if branch.as_deref() != Some(expected_branch) {
        return Some(format!(
            "checked-out branch {} does not match ship-pr-state.sh BRANCH_NAME {}",
            python_repr(branch.as_deref()),
            python_repr(Some(expected_branch))
        ));
    }
    if matches!(branch.as_deref(), Some("main" | "master"))
        && !state
            .get("FORKED_TARGET")
            .is_some_and(|value| truthy(value))
    {
        return Some(format!(
            "refusing pre-fix rebase on checked-out branch {} without a forked target",
            python_repr(branch.as_deref())
        ));
    }
    let resolved = run_larch(cwd, &["gh".into(), "resolve-repo".into()])
        .ok()
        .filter(|output| output.status().success())
        .map(|output| String::from_utf8_lossy(output.stdout()).trim().to_owned());
    let expected_repo = state.get("REPO").map(String::as_str).unwrap_or_default();
    if resolved.as_deref() != Some(expected_repo) {
        return Some(format!(
            "checked-out repo {} does not match ship-pr-state.sh REPO {}",
            python_repr(resolved.as_deref()),
            python_repr(Some(expected_repo))
        ));
    }
    None
}

fn rebase_in_progress(cwd: &Path) -> bool {
    let Ok(repository) = GixRepository::discover(cwd) else {
        return false;
    };
    let location = repository.location();
    let mut git_dir =
        PathBuf::from(String::from_utf8_lossy(location.git_dir.as_bytes()).into_owned());
    if git_dir.is_relative() {
        git_dir = cwd.join(git_dir);
    }
    git_dir.join("rebase-merge").is_dir() || git_dir.join("rebase-apply").is_dir()
}

fn head_oid(cwd: &Path) -> Option<String> {
    let repository = GixRepository::discover(cwd).ok()?;
    repository
        .resolve_revision(&Revision::new(b"HEAD"))
        .ok()
        .map(|object| object.to_hex())
}

fn unmerged_paths(cwd: &Path) -> String {
    let Ok(repository) = GixRepository::discover(cwd) else {
        return String::new();
    };
    let Ok(status) = repository.local_status(&StatusOptions::default()) else {
        return String::new();
    };
    sorted_lossy_unmerged_paths(&status).join(",")
}

fn conflict_fields(conflicts: &str) -> BTreeMap<String, String> {
    BTreeMap::from([
        ("RESUME_PHASE".to_owned(), CONFLICT_RESUME_PHASE.to_owned()),
        ("CALLER_KIND".to_owned(), CONFLICT_CALLER_KIND.to_owned()),
        ("CONFLICT_FILES".to_owned(), conflicts.to_owned()),
    ])
}

fn persist_conflict(
    tmpdir: &Path,
    fields: &BTreeMap<String, String>,
    write_phase_flag: bool,
) -> Result<(), String> {
    let conflicts = fields.get("CONFLICT_FILES").cloned().unwrap_or_default();
    if conflicts.is_empty() {
        return Err("conflict handoff has no files".to_owned());
    }
    validate_conflict_files(&conflicts)?;
    if write_phase_flag {
        write_private(&tmpdir.join(PHASE14_FLAG), "", tmpdir)?;
    }
    patch_ship_state_keys(
        &tmpdir.join(SHIP_STATE),
        &[
            ("PHASE", "rebase".to_owned()),
            (
                "RESUME_PHASE",
                fields.get("RESUME_PHASE").cloned().unwrap_or_default(),
            ),
            (
                "CALLER_KIND",
                fields.get("CALLER_KIND").cloned().unwrap_or_default(),
            ),
            ("CONFLICT_FILES", conflicts),
            ("CI_FIX_REBASE_PENDING", "false".to_owned()),
            ("CI_FIX_REBASE_PENDING_HEAD", String::new()),
        ],
        &CONFLICT_TERMINAL_CLEAR_KEYS,
    )?;
    patch_handoff(
        tmpdir,
        &[
            (
                "RESUME_PHASE",
                fields.get("RESUME_PHASE").cloned().unwrap_or_default(),
            ),
            (
                "CALLER_KIND",
                fields.get("CALLER_KIND").cloned().unwrap_or_default(),
            ),
            (
                "CONFLICT_FILES",
                fields.get("CONFLICT_FILES").cloned().unwrap_or_default(),
            ),
            ("PRE_FIX_REBASE_STATUS", "conflict".to_owned()),
            ("NEXT_ACTION", "conflict-fix".to_owned()),
        ],
    )
}

fn validate_conflict_files(conflicts: &str) -> Result<(), String> {
    for path in conflicts.split(',') {
        if path.is_empty()
            || path.trim() != path
            || path.starts_with('/')
            || path.contains('\\')
            || !path
                .chars()
                .all(|character| character.is_ascii_alphanumeric() || "._/-".contains(character))
            || path
                .split('/')
                .any(|component| matches!(component, "" | "." | ".."))
        {
            return Err("invalid CONFLICT_FILES entry".to_owned());
        }
    }
    Ok(())
}

fn patch_handoff(tmpdir: &Path, updates: &[(&str, String)]) -> Result<(), String> {
    let handoff_path = tmpdir.join(HANDOFF_ENV);
    let mut fields: Vec<(String, String)> = if safe_regular(&handoff_path) {
        read_universal_newlines(&handoff_path).map_or_else(Vec::new, |text| {
            KvDocument::parse(&text, ParseOptions::legacy()).map_or_else(
                |_| Vec::new(),
                |document| {
                    document
                        .rows()
                        .iter()
                        .filter(|row| !row.key().is_empty())
                        .fold(Vec::new(), |mut rows, row| {
                            if !rows
                                .iter()
                                .any(|existing: &(String, String)| existing.0 == row.key())
                            {
                                rows.push((row.key().to_owned(), row.value().to_owned()));
                            }
                            rows
                        })
                },
            )
        })
    } else {
        Vec::new()
    };
    for (key, value) in updates {
        let value = safe_line(value);
        if !value.is_empty() {
            if let Some(row) = fields.iter_mut().find(|row| row.0 == *key) {
                value.clone_into(&mut row.1);
            } else {
                fields.push(((*key).to_owned(), value));
            }
        }
    }
    let body = fields
        .into_iter()
        .map(|(key, value)| format!("{key}={value}"))
        .collect::<Vec<_>>()
        .join("\n");
    write_private(&handoff_path, &format!("{body}\n"), tmpdir)
}

fn phase14_skip_allowed(tmpdir: &Path) -> bool {
    let flag = tmpdir.join(PHASE14_FLAG);
    if !safe_regular(&flag) {
        return false;
    }
    let fields = read_kv(&flag);
    fields
        .get("RESUME_PHASE")
        .is_some_and(|value| value.trim() == CONFLICT_RESUME_PHASE)
        && fields.get("REASON").is_some_and(|value| {
            matches!(
                value.trim(),
                "mergeStateStatus=DIRTY" | "mergeStateStatus=BEHIND"
            )
        })
}

fn truthy(value: &str) -> bool {
    matches!(
        value.trim().to_ascii_lowercase().as_str(),
        "1" | "true" | "yes" | "on"
    )
}

fn python_repr(value: Option<&str>) -> String {
    value.map_or_else(|| "None".to_owned(), |text| format!("'{text}'"))
}

fn pre_fix_failure(message: &str) -> ExitCode {
    eprintln!("ship pre-fix-rebase: {message}");
    ExitCode::from(2)
}

fn finish_pre_fix(tmpdir: &Path, status: &str, action: &str, detail: &str) -> ExitCode {
    if matches!(action, "continue" | "conflict-fix")
        && let Err(error) = write_private(
            &tmpdir.join(PRE_FIX_SENTINEL),
            "PRE_FIX_REBASE_OK=true\n",
            tmpdir,
        )
    {
        return pre_fix_failure(&format!("cannot write pre-fix rebase sentinel: {error}"));
    }
    emit_pre_fix(status, action, detail)
}

fn emit_pre_fix(status: &str, action: &str, detail: &str) -> ExitCode {
    emit_kv("PRE_FIX_REBASE_STATUS", status);
    emit_kv("NEXT_ACTION", action);
    if !detail.is_empty() {
        emit_kv("DETAIL", &safe_line(detail));
    }
    ExitCode::SUCCESS
}

fn selected_tmpdir(argument: String) -> PathBuf {
    if argument.is_empty() {
        env::var_os("IMPLEMENT_TMPDIR").map_or_else(PathBuf::new, PathBuf::from)
    } else {
        PathBuf::from(argument)
    }
}

fn run_larch(cwd: &Path, arguments: &[OsString]) -> Result<ProcessOutput, String> {
    let root = resolve_plugin_root()?;
    delegate_verified_larch(cwd, &root, arguments)
}

fn forward_child_to_stderr(result: &Result<ProcessOutput, String>) -> i32 {
    match result {
        Ok(output) => {
            let _ = std::io::stderr().write_all(output.stdout());
            let _ = std::io::stderr().write_all(output.stderr());
            output.status().code().unwrap_or(1)
        }
        Err(message) => {
            eprintln!("{message}");
            1
        }
    }
}

fn resolve_repo_root(tmpdir: &Path) -> Option<PathBuf> {
    let output = resolve_repo_root_output(tmpdir);
    if !output.status().success() {
        return None;
    }
    let text = String::from_utf8_lossy(output.stdout());
    KvDocument::parse(&text, ParseOptions::legacy())
        .ok()
        .and_then(|document| document.select(DuplicatePolicy::Last).remove("REPO_ROOT"))
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

fn resolve_manifest(tmpdir: &Path, state: &Path) -> Option<PathBuf> {
    let persisted = read_kv(state).remove("MANIFEST_PATH").unwrap_or_default();
    if !persisted.is_empty() {
        return Some(PathBuf::from(persisted));
    }
    [
        tmpdir.join("manifest.json"),
        tmpdir.join("codex-step2-out/manifest.json"),
    ]
    .into_iter()
    .find(|path| path.is_file())
}

fn read_route_result(tmpdir: &Path) -> Result<(i32, BTreeMap<String, String>), String> {
    let path = tmpdir.join(RESULT_ENV);
    let text = read_confined_result_env(&path, tmpdir)
        .map_err(|error| format!("invalid bgjob result env for route-exit: {error}"))?
        .ok_or_else(|| "invalid bgjob result env for route-exit: missing file".to_owned())?;
    if text.contains('\r') {
        return Err("invalid bgjob result env for route-exit: carriage return".to_owned());
    }
    let fields = parse_fields(&text, true)
        .map_err(|_| "malformed bgjob result env for route-exit".to_owned())?;
    if fields.get("STEP").map(String::as_str) != Some(SHIP_STEP) {
        return Err("bgjob result env has an unexpected step".to_owned());
    }
    let raw_rc = fields
        .get("BGJOB_RC")
        .map(String::as_str)
        .unwrap_or_default();
    if matches!(raw_rc, "timeout" | "orphaned") {
        return Err(format!("bgjob result blocks route-exit: BGJOB_RC={raw_rc}"));
    }
    let rc = raw_rc
        .parse::<i32>()
        .map_err(|_| format!("invalid BGJOB_RC in bgjob result env: {raw_rc:?}"))?;
    Ok((rc, fields))
}

fn classify_route(rc: i32, fields: &BTreeMap<String, String>) -> Result<String, String> {
    let outcome = required_field(fields, "outcome")?;
    match rc {
        0 => Ok(if outcome == "OK" {
            "complete"
        } else {
            "reship"
        }
        .to_owned()),
        1 if outcome == "INTERNAL_ERROR" => Ok("tool-failure".to_owned()),
        1 => Err("exit 1 requires outcome=INTERNAL_ERROR".to_owned()),
        3 => Ok(classify_needs_user(required_field(fields, "NEEDS_USER_REASON")?).to_owned()),
        4 => Ok("stall".to_owned()),
        6 => Ok("transient".to_owned()),
        other => Err(format!("unsupported driver exit code: {other}")),
    }
}

fn required_field<'a>(fields: &'a BTreeMap<String, String>, key: &str) -> Result<&'a str, String> {
    fields
        .get(key)
        .map(String::as_str)
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| {
            let payload_key = if key == "NEEDS_USER_REASON" {
                "needs_user_reason"
            } else {
                key
            };
            format!("missing required result field: {payload_key}")
        })
}

fn classify_needs_user(reason: &str) -> &'static str {
    match reason {
        "postmerge-main-ci-fail" => "postmerge-repair",
        "scope-disposition" => "halt-scope-disposition",
        "oos-filing" => "oos-pipeline",
        "architectural-assessments" => "assessments",
        "architectural-invariants-assessment" | "architectural-invariants-violation" => {
            "invariants-assessment"
        }
        "architectural-guidelines-assessment" => "guidelines-assessment",
        "first-fixer-non-health"
        | "ship-pr-internal-lint-fix"
        | "local-unfixable"
        | "main-ci-fail"
        | "flaky-defect-unfixed" => "ci-fix",
        value if value.starts_with("ci-local-unfixable:") => "ci-fix",
        _ => "operator-bail",
    }
}

fn conflict_handoff_fields(tmpdir: &Path) -> BTreeMap<String, String> {
    let state = read_kv(&tmpdir.join(SHIP_STATE));
    let resume = state.get("RESUME_PHASE").cloned().unwrap_or_default();
    let caller = state.get("CALLER_KIND").cloned().unwrap_or_default();
    let conflicts = state.get("CONFLICT_FILES").cloned().unwrap_or_default();
    if resume == CONFLICT_RESUME_PHASE && caller == CONFLICT_CALLER_KIND && !conflicts.is_empty() {
        BTreeMap::from([
            ("RESUME_PHASE".to_owned(), resume),
            ("CALLER_KIND".to_owned(), caller),
            ("CONFLICT_FILES".to_owned(), conflicts),
        ])
    } else {
        BTreeMap::new()
    }
}

fn write_route_handoff(
    tmpdir: &Path,
    fields: &BTreeMap<String, String>,
    action: &str,
    delay: u64,
    route_fields: &BTreeMap<String, String>,
) -> Result<(), String> {
    let mut lines = Vec::new();
    for (source, target) in [
        ("FAILED_RUN_ID", "FAILED_RUN_ID"),
        ("NEEDS_USER_REASON", "NEEDS_USER_REASON"),
    ] {
        let value = safe_line(fields.get(source).map(String::as_str).unwrap_or_default());
        if !value.is_empty() {
            lines.push(format!("{target}={value}"));
        }
    }
    if action == "ci-fix" {
        let scope = if fields
            .get("NEEDS_USER_REASON")
            .is_some_and(|value| value == "main-ci-fail")
        {
            "main"
        } else {
            "pr"
        };
        lines.push(format!("CI_FAILURE_SCOPE={scope}"));
        let failed = fields
            .get("FAILED_JOBS_COUNT")
            .and_then(|value| value.trim().parse::<i64>().ok())
            .unwrap_or(0)
            .max(0);
        lines.push(format!("FAILED_JOBS_COUNT={failed}"));
        let errors = safe_line(
            fields
                .get("CI_ERRORS_FILE")
                .map(String::as_str)
                .unwrap_or_default(),
        );
        lines.push(format!("CI_ERRORS_FILE={errors}"));
        if errors.is_empty() {
            lines.push(format!(
                "CI_ERRORS_DISTILL_CLASS={}",
                safe_line(
                    fields
                        .get("CI_ERRORS_DISTILL_CLASS")
                        .map(String::as_str)
                        .unwrap_or_default()
                )
            ));
        }
    }
    if let Some(detail) = fields.get("DETAIL").filter(|detail| !detail.is_empty()) {
        if detail.contains(['\r', '\n']) || detail.chars().count() > DETAIL_FILE_MAX {
            let body = if detail.ends_with('\n') {
                detail.clone()
            } else {
                format!("{detail}\n")
            };
            let path = tmpdir.join(DETAIL_FILE);
            write_private(&path, &body, tmpdir)?;
            lines.push(format!("DETAIL_FILE={}", path.display()));
        } else {
            lines.push(format!("DETAIL={}", safe_line(detail)));
        }
    }
    for key in LEDGER_KEYS {
        if let Some(value) = fields.get(key) {
            lines.push(format!("{key}={}", safe_line(value)));
        }
    }
    for key in HEALTH_HANDOFF_KEYS {
        if let Some(value) = fields
            .get(key)
            .map(|value| safe_line(value))
            .filter(|value| !value.is_empty())
        {
            lines.push(format!("{key}={value}"));
        }
    }
    for key in ["RESUME_PHASE", "CALLER_KIND", "CONFLICT_FILES"] {
        if let Some(value) = route_fields
            .get(key)
            .map(|value| safe_line(value))
            .filter(|value| !value.is_empty())
        {
            lines.push(format!("{key}={value}"));
        }
    }
    if matches!(action, "ci-fix" | "reship") {
        let _ = fs::remove_file(tmpdir.join(PRE_FIX_SENTINEL));
        lines.push("PRE_FIX_REBASE_REQUIRED=true".to_owned());
    }
    lines.push(format!("NEXT_ACTION={action}"));
    if delay != 0 {
        lines.push(format!("RESHIP_DELAY_SECONDS={delay}"));
    }
    write_private(
        &tmpdir.join(HANDOFF_ENV),
        &format!("{}\n", lines.join("\n")),
        tmpdir,
    )
}

fn route_failure(handoff: &Path, message: &str) -> ExitCode {
    let _ = fs::remove_file(handoff);
    eprintln!("ship route-exit: {message}");
    ExitCode::from(2)
}

fn read_retry_count(path: &Path) -> i64 {
    if !safe_regular(path) {
        return 0;
    }
    fs::read_to_string(path)
        .ok()
        .and_then(|text| text.trim().parse::<i64>().ok())
        .unwrap_or(0)
}

fn seed_transient_stall(tmpdir: &Path) {
    let result = env::current_dir()
        .map_err(|error| error.to_string())
        .and_then(|cwd| {
            run_larch(
                &cwd,
                &[
                    "stall-recovery".into(),
                    "seed-terminal-state".into(),
                    "--implement-tmpdir".into(),
                    tmpdir.as_os_str().into(),
                    "--stall-step".into(),
                    "transient-retry-cap".into(),
                    "--phase".into(),
                    "ci-initial".into(),
                ],
            )
        });
    if result
        .as_ref()
        .map_or(true, |output| !output.status().success())
    {
        eprintln!(
            "ship route-exit: transient retry-cap stall seed failed; continuing with NEXT_ACTION=stall"
        );
        let _ = forward_child_to_stderr(&result);
    }
}

fn normalize_handoff(tmpdir: &Path) -> Result<String, String> {
    let handoff = tmpdir.join(HANDOFF_ENV);
    let text = read_confined_regular(&handoff, tmpdir)
        .map_err(|_| "missing or unsafe .ship-route-exit-handoff.env".to_owned())?;
    let fields =
        parse_fields(&text, false).map_err(|key| format!("duplicate handoff key: {key}"))?;
    let raw = match fields
        .get("NEXT_ACTION")
        .map(String::as_str)
        .unwrap_or_default()
    {
        "invariants-assessment" => "invariants".to_owned(),
        "guidelines-assessment" => "guidelines".to_owned(),
        "assessments" => assessment_detail(tmpdir, &fields)?,
        _ => return Err("NEXT_ACTION is not an assessment handoff".to_owned()),
    };
    if raw.is_empty() || raw.trim() != raw || raw.chars().any(char::is_whitespace) {
        return Err("assessment kinds must be nonempty canonical tokens".to_owned());
    }
    let requested: Vec<&str> = raw.split(',').collect();
    let unique: BTreeSet<&str> = requested.iter().copied().collect();
    if requested.iter().any(|kind| kind.is_empty()) || unique.len() != requested.len() {
        return Err("assessment kinds must not contain empty or duplicate tokens".to_owned());
    }
    if let Some(unknown) = unique
        .iter()
        .copied()
        .find(|kind| !matches!(*kind, "invariants" | "guidelines"))
    {
        return Err(format!("unsupported assessment kind: {unknown}"));
    }
    let canonical = ["invariants", "guidelines"]
        .into_iter()
        .filter(|kind| unique.contains(kind))
        .collect::<Vec<_>>()
        .join(",");
    let mut rewritten: Vec<String> = text
        .lines()
        .map(str::to_owned)
        .filter(|line| {
            ![
                "NEXT_ACTION=",
                "DETAIL=",
                "DETAIL_FILE=",
                "NEEDS_USER_REASON=",
            ]
            .iter()
            .any(|prefix| line.starts_with(prefix))
        })
        .collect();
    rewritten.push("NEXT_ACTION=assessments".to_owned());
    rewritten.push(format!("DETAIL={canonical}"));
    write_private(&handoff, &format!("{}\n", rewritten.join("\n")), tmpdir)
        .map_err(|error| format!("cannot safely rewrite assessment handoff: {error}"))?;
    Ok(canonical)
}

fn assessment_detail(tmpdir: &Path, fields: &BTreeMap<String, String>) -> Result<String, String> {
    let detail = fields.get("DETAIL").cloned().unwrap_or_default();
    let detail_file = fields.get("DETAIL_FILE").cloned().unwrap_or_default();
    if !detail.is_empty() && !detail_file.is_empty() {
        return Err("DETAIL and DETAIL_FILE cannot both be set".to_owned());
    }
    if !detail.is_empty() {
        return Ok(detail);
    }
    if detail_file.is_empty() {
        return Err("missing assessment detail".to_owned());
    }
    let path = PathBuf::from(detail_file);
    let parent = path.parent().and_then(|value| fs::canonicalize(value).ok());
    if path.is_symlink() || !path.is_file() || parent != fs::canonicalize(tmpdir).ok() {
        return Err("unsafe DETAIL_FILE".to_owned());
    }
    read_confined_regular(&path, tmpdir).map_err(|error| format!("unsafe DETAIL_FILE: {error}"))
}

fn parse_fields(text: &str, reject_malformed: bool) -> Result<BTreeMap<String, String>, String> {
    if reject_malformed && text.lines().any(str::is_empty) {
        return Err(String::new());
    }
    let mut options = ParseOptions::legacy();
    if reject_malformed {
        options.malformed_lines = MalformedLinePolicy::Reject;
    }
    let document = KvDocument::parse(text, options).map_err(|_| String::new())?;
    let mut fields = BTreeMap::new();
    for row in document.rows() {
        if (reject_malformed && row.key().is_empty())
            || fields
                .insert(row.key().to_owned(), row.value().to_owned())
                .is_some()
        {
            return Err(row.key().to_owned());
        }
    }
    Ok(fields)
}

fn read_kv(path: &Path) -> BTreeMap<String, String> {
    read_universal_newlines(path)
        .and_then(|text| KvDocument::parse(&text, ParseOptions::legacy()).ok())
        .map(|document| document.select(DuplicatePolicy::First))
        .unwrap_or_default()
}

fn read_confined_regular(path: &Path, root: &Path) -> Result<String, String> {
    read_confined_regular_text(path, root, "unsafe file")
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "unsafe file".to_owned())
}

fn safe_regular(path: &Path) -> bool {
    fs::symlink_metadata(path).is_ok_and(|metadata| metadata.is_file())
}

fn write_private(path: &Path, text: &str, root: &Path) -> Result<(), String> {
    private_atomic_write(path, text, root).map_err(|error| error.to_string())
}

fn safe_line(value: &str) -> String {
    value.replace(['\r', '\n'], " ").trim().to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pre_fix_context(tmpdir: &Path, state: &str) -> PreFixContext {
        let state_path = tmpdir.join(SHIP_STATE);
        fs::write(&state_path, state).expect("ship state");
        PreFixContext {
            state_path,
            state: read_kv(&tmpdir.join(SHIP_STATE)),
            cwd: tmpdir.to_owned(),
        }
    }

    #[test]
    fn pre_fix_closed_pr_skips_every_git_mutation_but_writes_proof() {
        let root = tempfile::tempdir().expect("temporary root");
        let context = pre_fix_context(
            root.path(),
            "PHASE=checks\nBRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=owner/repo\nPR_CLOSED=true\n",
        );

        assert_eq!(run_pre_fix_rebase(root.path(), &context), ExitCode::SUCCESS);
        assert_eq!(
            fs::read_to_string(root.path().join(PRE_FIX_SENTINEL)).expect("proof"),
            "PRE_FIX_REBASE_OK=true\n"
        );
    }

    #[test]
    fn pre_fix_conflict_handoff_precedes_the_closed_pr_skip() {
        let root = tempfile::tempdir().expect("temporary root");
        let context = pre_fix_context(
            root.path(),
            "PHASE=checks\nBRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=owner/repo\nPR_CLOSED=true\nCI_FIX_REBASE_PENDING=true\nCI_FIX_REBASE_PENDING_HEAD=abc\nRESUME_PHASE=ship-pr-rrr-phase14\nCALLER_KIND=ship_pr_pre_push\nCONFLICT_FILES=src/lib.rs\nEXIT_CODE=4\nBAIL_REASON=stale\nBAIL_NEEDS_USER_INPUT=true\nFAILED_RUN_ID=77\nBAIL_FAILURE_DETAIL_LOG=/tmp/stale\n",
        );
        fs::write(
            root.path().join(HANDOFF_ENV),
            "legacy note\nKEEP=first\nKEEP=second\nNEXT_ACTION=stale\n",
        )
        .expect("handoff");

        assert_eq!(run_pre_fix_rebase(root.path(), &context), ExitCode::SUCCESS);
        let state = fs::read_to_string(root.path().join(SHIP_STATE)).expect("state");
        assert!(state.contains("PHASE=rebase\n"));
        assert!(state.contains("CONFLICT_FILES=src/lib.rs\n"));
        assert!(state.contains("CI_FIX_REBASE_PENDING=false\n"));
        assert!(state.contains("CI_FIX_REBASE_PENDING_HEAD=\n"));
        let handoff = fs::read_to_string(root.path().join(HANDOFF_ENV)).expect("handoff");
        assert!(handoff.lines().any(|line| line == "KEEP=first"));
        assert!(!handoff.lines().any(|line| line == "KEEP=second"));
        assert!(
            handoff
                .lines()
                .any(|line| line == "NEXT_ACTION=conflict-fix")
        );
        for stale in [
            "EXIT_CODE=",
            "BAIL_REASON=",
            "BAIL_NEEDS_USER_INPUT=",
            "FAILED_RUN_ID=",
            "BAIL_FAILURE_DETAIL_LOG=",
        ] {
            assert!(
                !state.lines().any(|line| line.starts_with(stale)),
                "{state}"
            );
        }
    }
}
