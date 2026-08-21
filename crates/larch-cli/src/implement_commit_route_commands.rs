//! Rust owners for `implement commit`, `implement commit-route`, and
//! `implement checks-commit-route` (#8611).
//!
//! `commit` is the thin implementation-commit wrapper: it validates argv,
//! rehydrates the session, marks Step 4 timing, runs `git commit` through the
//! verified bootstrap, and emits `COMMITTED`/`SHA`/`ERROR`. `commit-route`
//! orchestrates the review-fix commit at Steps 5/7, seeding a durable stall on
//! failure. `checks-commit-route` is the per-site checks + commit + rebase
//! checkpoint composite. Every heavy leg (`review-and-fix commit-fixes`,
//! `checks run-relevant`, `implement scope-disposition`, `run-log
//! append-failure`, `implement step-8-seed-initial`, `push checkpoint-probe`)
//! is an already-Rust sub-verb this module sequences around the pure helpers in
//! `larch_core::implement::commit_route`.

use std::{
    collections::BTreeMap,
    env,
    ffi::{OsStr, OsString},
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_adapters::GixRepository;
use larch_core::{
    ChildEnvironment, ProcessOutput, RepositoryRead as _, Revision, emit_kv,
    implement::{
        CHECKS_DEADLINE_MS, COMMIT_ROUTE_DEADLINE_MS, COMMIT_ROUTE_SUCCESS_OUTCOMES,
        CommitRouteFailure, CommitRouteSite, STEP4_COMMIT_SITE, STEP5_RESUME_COMMIT_RELAY_KEYS,
        ShipStatePatch, Step4CommitSeed, checks_pass, checks_relay_line,
        commit_route_failure_log_path, commit_route_failure_log_text, commit_route_site,
        commit_route_site_names, fold_commit_error, nul_pathspec_bytes, parse_line_anchored,
        parse_whitespace_kv_line, patch_ship_state_stall, path_readable_nonempty, read_nul_pathspec,
        read_redacted_message, step3_self_edit_additions,
    },
    write_bytes_atomic,
};

use crate::{
    argparse_compat::{choice_error, parse_required_with_help, usage_error},
    implement_child_seam::resolve_plugin_root,
    implement_commands::{read_kv_first, write_atomic},
    implement_dispatch_commands::{
        capture_postlaunch_porcelain, resolve_repo_root_output, run_verified_larch_env_in_timeout,
        untracked_local_status,
    },
    implement_scope_disposition_commands::{
        compute_and_write_plan_coverage, invalidate_if_stale, plan_coverage_contract_rows,
    },
};

// ---------------------------------------------------------------------------
// usage/help strings
// ---------------------------------------------------------------------------

const COMMIT_HELP: &str =
    "usage: cli.py implement commit [-h]\n\noptions:\n  -h, --help  show this help message and exit\n";

const ROUTE_PROG: &str = "cli.py implement commit-route";
const ROUTE_USAGE: &str = "usage: cli.py implement commit-route [-h] --site\n                                     {step5-resume-handoff,step5-self-review,step7}\n                                     [--implement-tmpdir IMPLEMENT_TMPDIR]\n                                     [--emit-next-action {true,false}]\n";
const ROUTE_HELP: &str = "usage: cli.py implement commit-route [-h] --site\n                                     {step5-resume-handoff,step5-self-review,step7}\n                                     [--implement-tmpdir IMPLEMENT_TMPDIR]\n                                     [--emit-next-action {true,false}]\n\noptions:\n  -h, --help            show this help message and exit\n  --site {step5-resume-handoff,step5-self-review,step7}\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --emit-next-action {true,false}\n";
const ROUTE_OPTIONS: [&str; 3] = ["--site", "--implement-tmpdir", "--emit-next-action"];

const CHECKS_PROG: &str = "cli.py implement checks-commit-route";
const CHECKS_USAGE: &str = "usage: cli.py implement checks-commit-route [-h] --checks-site CHECKS_SITE\n                                            --commit-site\n                                            {step4,step5-resume-handoff,step5-self-review,step7}\n                                            [--checks-deadline-ms CHECKS_DEADLINE_MS]\n                                            [--commit-deadline-ms COMMIT_DEADLINE_MS]\n                                            [--emit-step7-breadcrumb]\n                                            [--rebase-checkpoint-4r]\n                                            [--rebase-checkpoint-7r]\n                                            [--forked-target {true,false}]\n";
const CHECKS_HELP: &str = "usage: cli.py implement checks-commit-route [-h] --checks-site CHECKS_SITE\n                                            --commit-site\n                                            {step4,step5-resume-handoff,step5-self-review,step7}\n                                            [--checks-deadline-ms CHECKS_DEADLINE_MS]\n                                            [--commit-deadline-ms COMMIT_DEADLINE_MS]\n                                            [--emit-step7-breadcrumb]\n                                            [--rebase-checkpoint-4r]\n                                            [--rebase-checkpoint-7r]\n                                            [--forked-target {true,false}]\n\noptions:\n  -h, --help            show this help message and exit\n  --checks-site CHECKS_SITE\n  --commit-site {step4,step5-resume-handoff,step5-self-review,step7}\n  --checks-deadline-ms CHECKS_DEADLINE_MS\n  --commit-deadline-ms COMMIT_DEADLINE_MS\n  --emit-step7-breadcrumb\n  --rebase-checkpoint-4r\n  --rebase-checkpoint-7r\n  --forked-target {true,false}\n";
const CHECKS_OPTIONS: [&str; 5] = [
    "--checks-site",
    "--commit-site",
    "--checks-deadline-ms",
    "--commit-deadline-ms",
    "--forked-target",
];

/// Outer deadline for a single leg's verified-larch child.
fn leg_timeout(deadline_ms: u64) -> Duration {
    Duration::from_millis(deadline_ms.max(1))
}

/// Domain of the Rust-owned `git` verb the commit wrapper routes through.
///
/// Kept as a constant so the argv is composed through the verified bootstrap's
/// typed `git commit` surface rather than a raw `["git", ...]` literal.
const LARCH_GIT_DOMAIN: &str = "git";

/// One typed `larch git commit` invocation the wrapper composes.
enum GitCommitRequest<'a> {
    /// `git commit -m <message> <files...>`.
    Named { message: &'a str, files: &'a [String] },
    /// `git commit -m <message> --only --pathspec-from-file <path> [--pathspec-file-nul]`.
    Pathspec {
        message: &'a str,
        pathspec_from_file: &'a str,
        pathspec_file_nul: bool,
    },
}

/// Compose the verified-bootstrap argv for one [`GitCommitRequest`].
fn git_commit_argv(request: &GitCommitRequest) -> Vec<OsString> {
    let mut argv: Vec<OsString> = Vec::new();
    argv.push(OsString::from(LARCH_GIT_DOMAIN));
    argv.push(OsString::from("commit"));
    match request {
        GitCommitRequest::Named { message, files } => {
            argv.push(OsString::from("-m"));
            argv.push(OsString::from(*message));
            argv.extend(files.iter().map(OsString::from));
        }
        GitCommitRequest::Pathspec {
            message,
            pathspec_from_file,
            pathspec_file_nul,
        } => {
            argv.push(OsString::from("-m"));
            argv.push(OsString::from(*message));
            argv.push(OsString::from("--only"));
            argv.push(OsString::from("--pathspec-from-file"));
            argv.push(OsString::from(*pathspec_from_file));
            if *pathspec_file_nul {
                argv.push(OsString::from("--pathspec-file-nul"));
            }
        }
    }
    argv
}

// ---------------------------------------------------------------------------
// shared sub-verb invocation
// ---------------------------------------------------------------------------

fn os_args(parts: &[&str]) -> Vec<OsString> {
    parts.iter().map(OsString::from).collect()
}

/// Resolve the active plugin root, falling back to the tmpdir session env.
fn resolve_plugin_root_or_tmpdir(tmpdir: &Path) -> Result<PathBuf, String> {
    if let Ok(root) = resolve_plugin_root() {
        return Ok(root);
    }
    for (file, key) in [
        ("plugin-root.env", "CLAUDE_PLUGIN_ROOT"),
        ("session-env.sh", "LARCH_CLAUDE_PLUGIN_ROOT"),
    ] {
        let value = read_kv_first(&tmpdir.join(file), key);
        if !value.is_empty() {
            return Ok(PathBuf::from(value));
        }
    }
    Err("CLAUDE_PLUGIN_ROOT is required".to_owned())
}

/// Run one already-Rust larch sub-verb through the verified bootstrap.
fn run_larch(
    plugin_root: &Path,
    cwd: &Path,
    args: &[OsString],
    extra: &[(ChildEnvironment, OsString)],
    timeout: Duration,
) -> Result<ProcessOutput, String> {
    run_verified_larch_env_in_timeout(cwd, plugin_root, args, extra, timeout)
}

fn stdout_text(output: &ProcessOutput) -> String {
    String::from_utf8_lossy(output.stdout()).into_owned()
}

fn stderr_text(output: &ProcessOutput) -> String {
    String::from_utf8_lossy(output.stderr()).into_owned()
}

fn forward_stderr(output: &ProcessOutput) {
    if !output.stderr().is_empty() {
        let _ = std::io::stderr().write_all(output.stderr());
    }
}

// ---------------------------------------------------------------------------
// git probes (in-process via gix)
// ---------------------------------------------------------------------------

/// The current working tree's dirty paths, `--untracked-files=all` style.
fn working_tree_paths(repo_root: &Path) -> Option<Vec<String>> {
    let status = untracked_local_status(repo_root)?;
    let mut paths = std::collections::BTreeSet::<String>::new();
    for change in status.tree_to_index.entries() {
        paths.insert(String::from_utf8_lossy(change.path.as_bytes()).into_owned());
    }
    for change in status.index_to_worktree.entries() {
        paths.insert(String::from_utf8_lossy(change.path.as_bytes()).into_owned());
    }
    for path in &status.untracked {
        paths.insert(String::from_utf8_lossy(path.as_bytes()).into_owned());
    }
    Some(paths.into_iter().collect())
}

/// Resolve `HEAD` to its full 40-character hex, or empty when unavailable.
fn head_sha(repo_root: &Path) -> String {
    let Ok(repo) = GixRepository::open(repo_root) else {
        return String::new();
    };
    repo.resolve_revision(&Revision::new(b"HEAD".to_vec()))
        .map(|object| object.to_hex())
        .unwrap_or_default()
}

/// Discover the git top-level of the current working directory.
fn repo_root_toplevel() -> Option<PathBuf> {
    use std::os::unix::ffi::OsStringExt as _;
    let cwd = env::current_dir().ok()?;
    let work_dir = GixRepository::discover(&cwd).ok()?.location().work_dir?;
    let bytes = work_dir.as_bytes().to_vec();
    (!bytes.contains(&0)).then(|| PathBuf::from(OsString::from_vec(bytes)))
}

/// True when none of `subset` (or the whole tree when `None`) is dirty.
fn subset_clean(repo_root: &Path, subset: Option<&[String]>) -> Option<bool> {
    let dirty = working_tree_paths(repo_root)?;
    match subset {
        None => Some(dirty.is_empty()),
        Some(subset) => {
            let wanted: std::collections::BTreeSet<&str> =
                subset.iter().map(String::as_str).collect();
            Some(!dirty.iter().any(|path| wanted.contains(path.as_str())))
        }
    }
}

// ---------------------------------------------------------------------------
// implement commit
// ---------------------------------------------------------------------------

const COMMIT_KNOWN_FLAGS: [&str; 6] = [
    "--message",
    "-m",
    "--pathspec-from-file",
    "--pathspec-file-nul",
    "--help",
    "-h",
];

/// Emit the usage refusal and `COMMITTED=false` envelope for a bad commit argv.
fn commit_usage_fail(error: &str) -> ExitCode {
    eprintln!(
        "Usage: implement commit --message MSG [--pathspec-from-file PATH [--pathspec-file-nul]] [files...]"
    );
    eprintln!(
        "HINT: --stage-all belongs to review-and-fix commit-fixes (Step 5 review fixes); implementation commits name specific files or use --pathspec-from-file."
    );
    emit_kv("COMMITTED", "false");
    emit_kv("SHA", "");
    emit_kv("ERROR", error);
    ExitCode::from(2)
}

/// Scan the commit argv for `--help` and unknown/valueless options.
fn scan_commit_argv(argv: &[OsString]) -> Option<ExitCode> {
    let mut index = 0;
    while index < argv.len() {
        let arg = argv[index].to_string_lossy();
        if arg == "--help" || arg == "-h" {
            print!("{COMMIT_HELP}");
            return Some(ExitCode::SUCCESS);
        }
        if arg.starts_with('-') && !COMMIT_KNOWN_FLAGS.contains(&arg.as_ref()) {
            return Some(commit_usage_fail(&format!("unknown option: {arg}")));
        }
        if arg == "--message" || arg == "-m" || arg == "--pathspec-from-file" {
            let next_is_value = argv
                .get(index + 1)
                .map(|value| !value.to_string_lossy().starts_with('-'))
                .unwrap_or(false);
            if !next_is_value {
                return Some(commit_usage_fail(&format!("{arg} requires a value")));
            }
            index += 2;
            continue;
        }
        index += 1;
    }
    None
}

struct CommitArgs {
    message: String,
    pathspec_from_file: String,
    pathspec_file_nul: bool,
    files: Vec<String>,
}

fn parse_commit_argv(argv: &[OsString]) -> CommitArgs {
    let mut parsed = CommitArgs {
        message: String::new(),
        pathspec_from_file: String::new(),
        pathspec_file_nul: false,
        files: Vec::new(),
    };
    let mut index = 0;
    while index < argv.len() {
        let arg = argv[index].to_string_lossy().into_owned();
        match arg.as_str() {
            "--message" | "-m" => {
                parsed.message = argv
                    .get(index + 1)
                    .map(|value| value.to_string_lossy().into_owned())
                    .unwrap_or_default();
                index += 2;
            }
            "--pathspec-from-file" => {
                parsed.pathspec_from_file = argv
                    .get(index + 1)
                    .map(|value| value.to_string_lossy().into_owned())
                    .unwrap_or_default();
                index += 2;
            }
            "--pathspec-file-nul" => {
                parsed.pathspec_file_nul = true;
                index += 1;
            }
            _ => {
                parsed.files.push(arg);
                index += 1;
            }
        }
    }
    parsed
}

/// Rehydrate the Step 4 session triplet from the tmpdir session env, if unset.
fn commit_session_env(tmpdir: Option<&Path>) -> Vec<(ChildEnvironment, OsString)> {
    let mut rows = Vec::new();
    let Some(tmpdir) = tmpdir else {
        return rows;
    };
    let env_file = tmpdir.join("session-env.sh");
    for (key, child) in [
        ("LARCH_TOKEN_SESSION_ID", ChildEnvironment::LarchTokenSessionId),
        (
            "LARCH_CLAUDE_SOURCE_FILE",
            ChildEnvironment::LarchClaudeSourceFile,
        ),
        ("LARCH_TIMING_LEDGER", ChildEnvironment::LarchTimingLedger),
    ] {
        if env::var_os(key).is_some() {
            continue;
        }
        let value = read_kv_first(&env_file, key);
        if !value.is_empty() {
            rows.push((child, OsString::from(value)));
        }
    }
    rows
}

/// Mark the Step 4 commit token and timing ledgers (best effort).
fn mark_commit_timing(plugin_root: &Path, cwd: &Path, session: &[(ChildEnvironment, OsString)]) {
    let _ = run_larch(
        plugin_root,
        cwd,
        &os_args(&["token", "mark", "Step 4 — commit implementation"]),
        session,
        Duration::from_secs(600),
    );
    let mut timing_env = session.to_vec();
    timing_env.push((
        ChildEnvironment::LarchTimingSkill,
        OsString::from("implement"),
    ));
    let _ = run_larch(
        plugin_root,
        cwd,
        &os_args(&["timing", "mark", "Step 4 — commit implementation"]),
        &timing_env,
        Duration::from_secs(600),
    );
}

/// `implement commit` compatibility command.
pub fn commit(arguments: &[OsString]) -> ExitCode {
    if let Some(code) = scan_commit_argv(arguments) {
        return code;
    }
    let parsed = parse_commit_argv(arguments);
    if parsed.message.trim().is_empty() {
        return commit_usage_fail("--message is required");
    }
    let tmpdir = env::var_os("IMPLEMENT_TMPDIR")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from);
    let session = commit_session_env(tmpdir.as_deref());
    let cwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let plugin_root = match resolve_plugin_root_or_tmpdir(tmpdir.as_deref().unwrap_or(&cwd)) {
        Ok(root) => root,
        Err(error) => {
            emit_kv("COMMITTED", "false");
            emit_kv("SHA", "");
            emit_kv("ERROR", &error);
            return ExitCode::from(1);
        }
    };
    mark_commit_timing(&plugin_root, &cwd, &session);
    emit_commit_result(&plugin_root, &cwd, &parsed, &session)
}

fn build_commit_args(parsed: &CommitArgs) -> Vec<OsString> {
    let request = if parsed.pathspec_from_file.is_empty() {
        GitCommitRequest::Named {
            message: &parsed.message,
            files: &parsed.files,
        }
    } else {
        GitCommitRequest::Pathspec {
            message: &parsed.message,
            pathspec_from_file: &parsed.pathspec_from_file,
            pathspec_file_nul: parsed.pathspec_file_nul,
        }
    };
    git_commit_argv(&request)
}

fn emit_commit_result(
    plugin_root: &Path,
    cwd: &Path,
    parsed: &CommitArgs,
    session: &[(ChildEnvironment, OsString)],
) -> ExitCode {
    let args = build_commit_args(parsed);
    let outcome = run_larch(plugin_root, cwd, &args, session, Duration::from_secs(600));
    let output = match outcome {
        Ok(output) => output,
        Err(error) => {
            emit_kv("COMMITTED", "false");
            emit_kv("SHA", "");
            emit_kv("ERROR", &fold_commit_error(&error, ""));
            return ExitCode::from(1);
        }
    };
    let code = output.status().code().unwrap_or(1);
    if code == 0 {
        emit_kv("COMMITTED", "true");
        emit_kv("SHA", &head_sha(cwd));
        ExitCode::SUCCESS
    } else {
        emit_kv("COMMITTED", "false");
        emit_kv("SHA", "");
        emit_kv(
            "ERROR",
            &fold_commit_error(&stderr_text(&output), &stdout_text(&output)),
        );
        ExitCode::from(u8::try_from(code).unwrap_or(1))
    }
}

// ---------------------------------------------------------------------------
// scope-coverage relay
// ---------------------------------------------------------------------------

fn resolve_relay_manifest(tmpdir: &Path) -> Option<PathBuf> {
    let manifest = tmpdir.join("manifest.json");
    if manifest.is_file() {
        return Some(manifest);
    }
    let codex = tmpdir.join("codex-step2-out").join("manifest.json");
    codex.is_file().then_some(codex)
}

/// Relay `PLAN_COVERAGE_*`/`TODOS_LEFT_*` disposition rows for a committed leg.
fn relay_scope_coverage(tmpdir: &Path) -> i32 {
    if !tmpdir.join("plan.txt").is_file() || !tmpdir.join("step2-baseline.txt").is_file() {
        return 0;
    }
    let repo_root = match std::fs::read_to_string(tmpdir.join("repo-root.txt")) {
        Ok(text) => {
            let raw = PathBuf::from(text.trim());
            std::fs::canonicalize(&raw).unwrap_or(raw)
        }
        Err(_) => {
            eprintln!("scope-disposition: persisted repository root is unavailable");
            return 2;
        }
    };
    if !repo_root.is_dir() {
        eprintln!("scope-disposition: persisted repository root is not a directory");
        return 2;
    }
    let manifest = resolve_relay_manifest(tmpdir);
    let coverage =
        match compute_and_write_plan_coverage(tmpdir, &repo_root, None, manifest.as_deref()) {
            Ok(coverage) => coverage,
            Err(error) => {
                eprintln!("scope-disposition: coverage recompute failed: {error}");
                return 4;
            }
        };
    for (key, value) in plan_coverage_contract_rows(&coverage) {
        emit_kv(key, &value);
    }
    if let Ok(true) = invalidate_if_stale(tmpdir, &repo_root, manifest.as_deref()) {
        emit_kv("PLAN_COVERAGE_DISPOSITION_INVALIDATED", "true");
    }
    0
}

// ---------------------------------------------------------------------------
// durable stall seed + failure log
// ---------------------------------------------------------------------------

fn write_failure_log(tmpdir: &Path, failure: &CommitRouteFailure) -> PathBuf {
    let path = commit_route_failure_log_path(tmpdir, &failure.site_name);
    let _ = write_atomic(&path, &commit_route_failure_log_text(failure));
    path
}

/// Append the redacted commit-route failure to the run log.
fn log_failure(
    plugin_root: &Path,
    cwd: &Path,
    tmpdir: &Path,
    site_name: &str,
    label: &str,
    tool: &str,
    exit_code: i32,
    output_file: &Path,
) {
    // #7074: append-failure renders "Step <site>: …"; strip the leading "step".
    let display_site = site_name.strip_prefix("step").filter(|rest| !rest.is_empty()).unwrap_or(site_name);
    let log = tmpdir.join("execution-issues.md");
    let args = vec![
        OsString::from("run-log"),
        OsString::from("append-failure"),
        OsString::from("--log"),
        log.into_os_string(),
        OsString::from("--site"),
        OsString::from(display_site),
        OsString::from("--tool"),
        OsString::from(tool),
        OsString::from("--exit-code"),
        OsString::from(exit_code.to_string()),
        OsString::from("--category"),
        OsString::from("Tool Failures"),
        OsString::from("--output-file"),
        output_file.as_os_str().to_owned(),
        OsString::from("--redact"),
    ];
    match run_larch(plugin_root, cwd, &args, &[], Duration::from_secs(600)) {
        Ok(output) if output.status().code() == Some(0) => {}
        Ok(output) => {
            eprintln!("commit-route: failed to append redacted failure log for {label}");
            forward_stderr(&output);
        }
        Err(error) => {
            eprintln!("commit-route: failed to append redacted failure log for {label}: {error}");
        }
    }
}

/// Seed a durable stall: patch an existing ship state, else seed a fresh one.
fn seed_durable_stall(
    plugin_root: &Path,
    cwd: &Path,
    tmpdir: &Path,
    stall_step: &str,
    bail_reason: &str,
) -> bool {
    let state_file = tmpdir.join("ship-pr-state.sh");
    match patch_ship_state_stall(&state_file, stall_step, bail_reason) {
        ShipStatePatch::Patched => true,
        ShipStatePatch::Refused => {
            eprintln!("commit-route: refusing malformed or symlinked ship state: {}", state_file.display());
            false
        }
        ShipStatePatch::Absent => {
            let args = os_args(&[
                "implement",
                "step-8-seed-initial",
                "--stall-tracking",
                "true",
                "--stall-step",
                stall_step,
                "--bail-reason",
                bail_reason,
            ]);
            match run_larch(plugin_root, cwd, &args, &[], Duration::from_secs(600)) {
                Ok(output) => {
                    forward_stderr(&output);
                    output.status().code() == Some(0)
                }
                Err(error) => {
                    eprintln!("commit-route: durable stall seed failed: {error}");
                    false
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// implement commit-route
// ---------------------------------------------------------------------------

/// The return of the commit-route core: an exit code or a leg-mode outcome.
enum CommitRouteRun {
    Code(i32),
    Outcome(&'static str),
}

fn relay_commit_kvs(commit_output: &str, include_next_action: bool) {
    for line in commit_output.lines() {
        let Some((key, _)) = line.split_once('=') else {
            continue;
        };
        if key == "NEXT_ACTION" && !include_next_action {
            continue;
        }
        if STEP5_RESUME_COMMIT_RELAY_KEYS.contains(&key) {
            println!("{line}");
        }
    }
}

struct StallContext<'a> {
    plugin_root: &'a Path,
    cwd: &'a Path,
    tmpdir: &'a Path,
}

fn commit_route_stall(
    ctx: &StallContext,
    failure: &CommitRouteFailure,
    emit_next_action: bool,
) -> CommitRouteRun {
    let failure_log = write_failure_log(ctx.tmpdir, failure);
    log_failure(
        ctx.plugin_root,
        ctx.cwd,
        ctx.tmpdir,
        &failure.site_name,
        failure.site.failure_log_label,
        "scripts/larch.sh review-and-fix commit-fixes --stage-all",
        failure.exit_code,
        &failure_log,
    );
    let seeded = seed_durable_stall(
        ctx.plugin_root,
        ctx.cwd,
        ctx.tmpdir,
        failure.site.stall_step,
        failure.site.bail_reason,
    );
    if !seeded {
        if !emit_next_action {
            emit_kv("COMMIT_ROUTE_OUTCOME", "seed-failed");
            relay_commit_kvs(&failure.stdout, false);
            return CommitRouteRun::Outcome("seed-failed");
        }
        return CommitRouteRun::Code(1);
    }
    if !emit_next_action {
        emit_kv("COMMIT_ROUTE_OUTCOME", "seeded-stall");
        relay_commit_kvs(&failure.stdout, false);
        return CommitRouteRun::Outcome("seeded-stall");
    }
    relay_commit_kvs(&failure.stdout, false);
    emit_kv("NEXT_ACTION", "stall");
    CommitRouteRun::Code(0)
}

fn commit_route_porcelain_gate(repo_root: &Path) -> (bool, &'static str, String) {
    match subset_clean(repo_root, None) {
        None => (false, "git status probe failed", "git status probe failed".to_owned()),
        Some(true) => (true, "", String::new()),
        Some(false) => {
            let listing = working_tree_paths(repo_root)
                .map(|paths| paths.join("\n"))
                .unwrap_or_default();
            (false, "dirty tree after review fix commit", listing)
        }
    }
}

fn commit_route_run(
    ctx: &StallContext,
    site_name: &str,
    site: &CommitRouteSite,
    emit_next_action: bool,
) -> CommitRouteRun {
    let commit_result = run_larch(
        ctx.plugin_root,
        ctx.cwd,
        &os_args(&["review-and-fix", "commit-fixes", "--stage-all"]),
        &[],
        leg_timeout(COMMIT_ROUTE_DEADLINE_MS),
    );
    let (rc, commit_output, commit_stderr) = match commit_result {
        Ok(output) => (
            output.status().code().unwrap_or(1),
            stdout_text(&output),
            stderr_text(&output),
        ),
        Err(error) => (1, String::new(), error),
    };
    let outcomes = parse_line_anchored(&commit_output, "COMMIT_OUTCOME");
    if outcomes.len() != 1 {
        return commit_route_stall(
            ctx,
            &CommitRouteFailure {
                site_name: site_name.to_owned(),
                site: site.clone(),
                exit_code: if rc == 0 { 1 } else { rc },
                reason: "missing or malformed COMMIT_OUTCOME".to_owned(),
                stdout: commit_output,
                stderr: commit_stderr,
            },
            emit_next_action,
        );
    }
    let outcome = &outcomes[0];
    if !COMMIT_ROUTE_SUCCESS_OUTCOMES.contains(&outcome.as_str()) {
        return commit_route_stall(
            ctx,
            &CommitRouteFailure {
                site_name: site_name.to_owned(),
                site: site.clone(),
                exit_code: if rc == 0 { 1 } else { rc },
                reason: format!("COMMIT_OUTCOME={outcome}"),
                stdout: commit_output,
                stderr: commit_stderr,
            },
            emit_next_action,
        );
    }
    if site.porcelain_probe {
        let (ok, reason, detail) = commit_route_porcelain_gate(ctx.cwd);
        if !ok {
            return commit_route_stall(
                ctx,
                &CommitRouteFailure {
                    site_name: site_name.to_owned(),
                    site: site.clone(),
                    exit_code: 1,
                    reason: reason.to_owned(),
                    stdout: commit_output,
                    stderr: detail,
                },
                emit_next_action,
            );
        }
    }
    let coverage_rc = relay_scope_coverage(ctx.tmpdir);
    if coverage_rc != 0 {
        return if emit_next_action {
            CommitRouteRun::Code(coverage_rc)
        } else {
            CommitRouteRun::Outcome("seed-failed")
        };
    }
    if !emit_next_action {
        emit_kv("COMMIT_ROUTE_OUTCOME", "continue");
        relay_commit_kvs(&commit_output, false);
        return CommitRouteRun::Outcome("continue");
    }
    relay_commit_kvs(&commit_output, false);
    emit_kv("NEXT_ACTION", "continue");
    CommitRouteRun::Code(0)
}

/// `implement commit-route` compatibility command.
pub fn commit_route(arguments: &[OsString]) -> ExitCode {
    let sites = commit_route_site_names();
    let flags: [&str; 0] = [];
    let parsed = match parse_required_with_help(
        arguments,
        ROUTE_PROG,
        ROUTE_USAGE,
        ROUTE_HELP,
        &ROUTE_OPTIONS,
        &flags,
        &["--site"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    if let Some(error) = choice_error(
        arguments,
        &ROUTE_OPTIONS,
        &[
            ("--site", &sites),
            ("--emit-next-action", &["true", "false"]),
        ],
    ) {
        return usage_error(ROUTE_USAGE, ROUTE_PROG, &error, 2);
    }
    let site_name = parsed
        .value("--site")
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default();
    let Some(site) = commit_route_site(&site_name) else {
        return usage_error(ROUTE_USAGE, ROUTE_PROG, "argument --site: invalid choice", 2);
    };
    let raw_tmpdir = parsed
        .value("--implement-tmpdir")
        .map(|value| value.to_string_lossy().into_owned())
        .filter(|value| !value.is_empty())
        .or_else(|| env::var("IMPLEMENT_TMPDIR").ok())
        .unwrap_or_default();
    if raw_tmpdir.is_empty() {
        eprintln!("IMPLEMENT_TMPDIR required");
        return ExitCode::from(2);
    }
    let tmpdir = PathBuf::from(&raw_tmpdir);
    if !tmpdir.is_dir() {
        eprintln!("commit-route: implement tmpdir not found: {}", tmpdir.display());
        return ExitCode::from(2);
    }
    let emit_next_action = parsed
        .value("--emit-next-action")
        .map(|value| value.to_string_lossy() == "true")
        .unwrap_or(true);
    let plugin_root = match resolve_plugin_root_or_tmpdir(&tmpdir) {
        Ok(root) => root,
        Err(error) => {
            eprintln!("commit-route: {error}");
            return ExitCode::from(2);
        }
    };
    let cwd = env::current_dir().unwrap_or_else(|_| tmpdir.clone());
    let ctx = StallContext {
        plugin_root: &plugin_root,
        cwd: &cwd,
        tmpdir: &tmpdir,
    };
    match commit_route_run(&ctx, &site_name, &site, emit_next_action) {
        CommitRouteRun::Code(code) => ExitCode::from(u8::try_from(code).unwrap_or(1)),
        CommitRouteRun::Outcome(outcome) => {
            if outcome == "continue" || outcome == "seeded-stall" {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(1)
            }
        }
    }
}

include!("implement_commit_route_commands_checks.rs");
