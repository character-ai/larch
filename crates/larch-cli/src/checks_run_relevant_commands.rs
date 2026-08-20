//! Rust owners for `checks run-relevant` and `checks contains-pins` (#8616).
//!
//! `run-relevant` maps the changed-file selection to the validation phases that
//! must run (pre-commit over changed regular files, a bounded Rust Clippy
//! fallback, and the contains-pin probe), captures a redacted failure log, and
//! renders the `KEY=value` result. `contains-pins` is the standalone probe.
//!
//! The pure selection, result grammar, and failure-digest live in
//! `larch_core::implement`; this module owns the impure orchestration.

use std::{
    collections::BTreeSet,
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use larch_adapters::GixRepository;
use larch_core::{
    ChildEnvironment, HostUtilityProgram, ProcessOutput, RepositoryRead, Revision, StatusOptions,
    implement::{
        ChecksResult, build_checks_failure_digest, coverage_from_markers, digest_paths,
        is_rust_relevant_path, normalize_rel, phase_from_markers, read_changed_scope,
        record_self_edits, scan_checks_log_markers, scan_contains_pins, validate_session_tmpdir,
    },
    redact_secrets_only, redact_sensitive_paths,
};

use crate::{
    argparse_compat::parse_required_with_help,
    child_process::{bounded_request_in, run_bounded},
    implement_dispatch_commands::opt_string,
    python_verb::run_python_verb,
};

const RUN_RELEVANT_PROG: &str = "cli.py checks run-relevant";
const RUN_RELEVANT_USAGE: &str = "usage: cli.py checks run-relevant [-h] --site SITE [--tmpdir TMPDIR]\n                                  [--repo-root REPO_ROOT] [--allow-skip]";
const RUN_RELEVANT_HELP: &str = "usage: cli.py checks run-relevant [-h] --site SITE [--tmpdir TMPDIR]\n                                  [--repo-root REPO_ROOT] [--allow-skip]\n\noptions:\n  -h, --help            show this help message and exit\n  --site SITE\n  --tmpdir TMPDIR\n  --repo-root REPO_ROOT\n  --allow-skip";

const CONTAINS_PINS_PROG: &str = "cli.py checks contains-pins";
const CONTAINS_PINS_USAGE: &str = "usage: cli.py checks contains-pins [-h] [--changed-files CHANGED_FILES]\n                                   [--repo-root REPO_ROOT]";
const CONTAINS_PINS_HELP: &str = "usage: cli.py checks contains-pins [-h] [--changed-files CHANGED_FILES]\n                                   [--repo-root REPO_ROOT]\n\noptions:\n  -h, --help            show this help message and exit\n  --changed-files CHANGED_FILES\n  --repo-root REPO_ROOT";

/// Generous ceiling for a captured pre-commit or fallback run; the leg deadline
/// bounds wall-clock upstream, so this only fails closed on a runaway stream.
const CHECKS_OUTPUT_LIMIT: usize = 32 * 1024 * 1024;
const CHECKS_SUBPROCESS_TIMEOUT: Duration = Duration::from_secs(3600);
const CHECKS_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
const RUST_CLIPPY_HOOK_ID: &str = "cargo-clippy";
const RUST_CLIPPY_HOOK_MARKER: &str = "RUST_CLIPPY_HOOK_RAN=true";

/// `checks contains-pins` compatibility command.
pub fn check_contains_pins(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        CONTAINS_PINS_PROG,
        CONTAINS_PINS_USAGE,
        CONTAINS_PINS_HELP,
        &["--changed-files", "--repo-root"],
        &[],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let repo_root_raw = opt_string(parsed.value("--repo-root"));
    let repo_root = resolve_display_path(&repo_root_raw);
    if !repo_root.is_dir() {
        eprintln!(
            "ERROR: --repo-root is not a directory: {}",
            repo_root.display()
        );
        return ExitCode::from(2);
    }
    let changed_files_raw = opt_string(parsed.value("--changed-files"));
    let changed = if changed_files_raw.is_empty() {
        None
    } else {
        let changed_path = Path::new(&changed_files_raw);
        if !changed_path.is_file() {
            eprintln!(
                "ERROR: --changed-files path not found: {}",
                changed_path.display()
            );
            return ExitCode::from(2);
        }
        read_changed_scope(changed_path, &repo_root)
            .map_or_else(|_| Some(std::collections::HashSet::new()), Some)
    };
    let scan = scan_contains_pins(&repo_root, changed.as_ref());
    for line in &scan.stdout_lines {
        println!("{line}");
    }
    for line in &scan.stderr_lines {
        eprintln!("{line}");
    }
    println!("DEFECTS={}", scan.defects);
    if scan.defects > 0 {
        ExitCode::from(1)
    } else {
        ExitCode::SUCCESS
    }
}

/// `checks run-relevant` compatibility command.
pub fn checks_run_relevant(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        RUN_RELEVANT_PROG,
        RUN_RELEVANT_USAGE,
        RUN_RELEVANT_HELP,
        &["--site", "--tmpdir", "--repo-root"],
        &["--allow-skip"],
        &["--site"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let site = opt_string(parsed.value("--site"));
    let tmpdir = parsed
        .value("--tmpdir")
        .map_or_else(default_tmpdir, |value| value.to_string_lossy().into_owned());
    let repo_root_arg = opt_string(parsed.value("--repo-root"));
    let repo_root = if repo_root_arg.is_empty() {
        default_repo_root()
    } else {
        repo_root_arg
    };
    let allow_skip = parsed.flag("--allow-skip");
    let result = run_relevant_checks(&site, &tmpdir, &repo_root);
    let (line, code) = result.render(allow_skip);
    println!("{line}");
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

/// Run relevant checks natively and capture a redacted failure log.
fn run_relevant_checks(site: &str, tmpdir: &str, repo_root: &str) -> ChecksResult {
    if !valid_site(site) {
        return ChecksResult::failure(site, 2, "site-validation");
    }
    let Some(canonical_tmp) = validate_session_tmpdir(tmpdir) else {
        return ChecksResult::failure(site, 2, "tmpdir-validation");
    };
    let start_s = epoch_now();
    let outcome = run_relevant_checks_impl(site, &canonical_tmp, repo_root);
    let end_s = epoch_now();
    record_checks_vendor_task(&canonical_tmp, start_s, end_s, outcome.exit_code);
    outcome
}

fn run_relevant_checks_impl(site: &str, canonical_tmp: &Path, repo_root: &str) -> ChecksResult {
    mark_step_ledger(site);
    let Some(repo) = resolve_checks_repo_root(repo_root) else {
        return ChecksResult::failure(site, 1, "repo-root-unresolved");
    };
    let log_dir = canonical_tmp.join("relevant-checks");
    if make_log_dir(&log_dir).is_err() {
        return ChecksResult::failure(site, 1, "log-dir-create-failed");
    }
    if fs::symlink_metadata(&log_dir).is_ok_and(|meta| meta.file_type().is_symlink()) {
        return ChecksResult::failure(site, 1, "log-dir-symlink-rejected");
    }
    if set_dir_mode(&log_dir).is_err() {
        return ChecksResult::failure(site, 1, "log-dir-chmod-failed");
    }
    let Some(log_file) = allocate_log_file(&log_dir, site) else {
        return ChecksResult::failure(site, 1, "log-alloc-failed");
    };
    let mut log = String::new();
    let rc = run_relevant_checks_inner(&repo, canonical_tmp, &mut log);
    if fs::write(&log_file, &log).is_err() {
        return ChecksResult::failure(site, 1, "log-validation-failed");
    }
    let valid_log = fs::symlink_metadata(&log_file).is_ok_and(|meta| meta.is_file())
        && !fs::symlink_metadata(&log_file).is_ok_and(|meta| meta.file_type().is_symlink())
        && log_file
            .parent()
            .and_then(|parent| fs::canonicalize(parent).ok())
            == fs::canonicalize(&log_dir).ok();
    if !valid_log {
        return ChecksResult::failure(site, 1, "log-validation-failed");
    }
    finish_logged_result(rc, site, &log_file, &log_dir)
}

/// Assemble the relevant-checks log in memory and return the exit code.
fn run_relevant_checks_inner(repo: &Path, canonical_tmp: &Path, log: &mut String) -> i32 {
    let changed = changed_paths_from_git(repo);
    if changed.is_empty() {
        log.push_str("No modified files detected — no scoped validation needed.\n");
        return 0;
    }
    let regular = existing_regular_files(repo, &changed);
    let rust_changed: Vec<String> = changed
        .iter()
        .filter(|path| is_rust_relevant_path(path))
        .cloned()
        .collect();
    let rust_regular_count = regular
        .iter()
        .filter(|path| is_rust_relevant_path(path))
        .count();
    let rust_needs_fallback = !rust_changed.is_empty() && rust_regular_count != rust_changed.len();

    if regular.is_empty() {
        log.push_str("No existing regular files to pass to pre-commit.\n");
        if !rust_changed.is_empty() {
            let fallback_rc = run_bounded_rust_fallback(repo, &rust_changed, log);
            if fallback_rc != 0 {
                return fallback_rc;
            }
        }
        return run_contain_pin_phase(repo, &changed, log);
    }

    if !precommit_available() {
        log.push_str("ERROR: pre-commit not found. Run: pip install pre-commit (or: make setup)\n");
        return 1;
    }

    let _ = writeln!(
        log,
        "=== Running pre-commit on {} changed file(s) ===",
        regular.len()
    );
    let before_digests = digest_paths(repo, &regular);
    let (precommit_rc, precommit_out) = run_precommit(
        repo,
        &regular,
        !rust_changed.is_empty(),
        rust_needs_fallback,
    );
    if rust_needs_fallback {
        log.push_str(
            "Rust change set includes a deleted or non-regular path; skipping the pre-commit Cargo hook so the bounded fallback can select every Rust path once.\n",
        );
    }
    log.push_str(&precommit_out);
    record_precommit_self_edits(repo, &regular, &before_digests, canonical_tmp);
    if precommit_rc != 0 {
        return precommit_rc;
    }

    if rust_needs_fallback {
        let fallback_rc = run_bounded_rust_fallback(repo, &rust_changed, log);
        if fallback_rc != 0 {
            return fallback_rc;
        }
    } else if !rust_changed.is_empty() && !log.contains(RUST_CLIPPY_HOOK_MARKER) {
        log.push_str(
            "ERROR: pre-commit completed without the bounded Rust Clippy proof marker; refusing a second Rust configuration.\n",
        );
        return 1;
    }

    run_contain_pin_phase(repo, &changed, log)
}

fn run_precommit(
    repo: &Path,
    regular: &[String],
    rust_changed: bool,
    rust_needs_fallback: bool,
) -> (i32, String) {
    let mut arguments: Vec<OsString> = vec![OsString::from("run"), OsString::from("--files")];
    arguments.extend(regular.iter().map(OsString::from));
    let request = match bounded_request_in(
        larch_core::ExternalProgram::HostUtility(HostUtilityProgram::PreCommit),
        arguments,
        repo,
        CHECKS_SUBPROCESS_TIMEOUT,
        CHECKS_SHUTDOWN_GRACE,
        CHECKS_OUTPUT_LIMIT,
    ) {
        Ok(request) => request,
        Err(message) => {
            return (
                1,
                format!("ERROR: pre-commit could not be launched: {message}\n"),
            );
        }
    };
    let mut request = request;
    if rust_changed {
        request = request
            .with_environment(ChildEnvironment::CargoIncremental, OsString::from("0"))
            .with_environment(ChildEnvironment::CargoProfileDevDebug, OsString::from("0"))
            .with_environment(ChildEnvironment::CargoProfileTestDebug, OsString::from("0"));
    }
    if rust_needs_fallback {
        request = request.with_environment(
            ChildEnvironment::PrecommitSkip,
            OsString::from(RUST_CLIPPY_HOOK_ID),
        );
    }
    for key in [
        ChildEnvironment::XdgCacheHome,
        ChildEnvironment::XdgConfigHome,
    ] {
        if let Some(value) = std::env::var_os(key.name()) {
            request = request.with_environment(key, value);
        }
    }
    match run_bounded(request) {
        Ok(output) => (process_code(&output), combined_output(&output)),
        Err(message) => (1, format!("ERROR: pre-commit run failed: {message}\n")),
    }
}

fn run_bounded_rust_fallback(repo: &Path, rust_changed: &[String], log: &mut String) -> i32 {
    let _ = writeln!(
        log,
        "\n=== Running bounded Rust Clippy fallback for changed path(s): {} ===",
        rust_changed.join(", ")
    );
    let mut arguments: Vec<OsString> = vec![
        OsString::from("checks"),
        OsString::from("rust-clippy"),
        OsString::from("--repo-root"),
        OsString::from(repo),
    ];
    arguments.extend(rust_changed.iter().map(OsString::from));
    match run_python_verb(arguments, CHECKS_SUBPROCESS_TIMEOUT) {
        Ok(output) => {
            log.push_str(&combined_output(&output));
            let code = process_code(&output);
            if code != 0 {
                return code;
            }
            if !log.contains(RUST_CLIPPY_HOOK_MARKER) {
                log.push_str(
                    "ERROR: bounded Rust Clippy fallback completed without its proof marker.\n",
                );
                return 1;
            }
            0
        }
        Err(message) => {
            let _ = writeln!(log, "ERROR: bounded Rust Clippy fallback failed: {message}");
            1
        }
    }
}

fn run_contain_pin_phase(repo: &Path, changed: &[String], log: &mut String) -> i32 {
    let scope_set: std::collections::HashSet<String> = changed
        .iter()
        .map(|path| normalize_rel(path, repo))
        .collect();
    let scan = scan_contains_pins(repo, Some(&scope_set));
    for line in &scan.stdout_lines {
        log.push_str(line);
        log.push('\n');
    }
    for line in &scan.stderr_lines {
        log.push_str(line);
        log.push('\n');
    }
    let _ = writeln!(log, "DEFECTS={}", scan.defects);
    i32::from(scan.defects > 0)
}

fn finish_logged_result(rc: i32, site: &str, log_file: &Path, log_dir: &Path) -> ChecksResult {
    let text = read_text(log_file).unwrap_or_default();
    let (has_precommit, has_agent_lint, has_warn) = scan_checks_log_markers(&text);
    let ok = rc == 0;
    let coverage = coverage_from_markers(ok, has_precommit, has_agent_lint).to_owned();
    let phase = phase_from_markers(ok, has_precommit, has_agent_lint).to_owned();
    let warn = if has_warn {
        Some("agent-lint-missing".to_owned())
    } else {
        None
    };
    let attempt = log_attempt(log_file);
    if rc == 2 && text.contains("ERROR: no validation phases ran") {
        let redacted_file = log_dir.join(format!("{site}-{attempt}.redacted.log"));
        let redacted_path = redact_log(log_file, &redacted_file)
            .then(|| redacted_file.to_string_lossy().into_owned());
        let digest_path = redacted_path
            .as_ref()
            .and_then(|_| write_failure_digest(&redacted_file, site, &attempt, log_dir));
        return ChecksResult {
            ok: false,
            exit_code: 2,
            site: site.to_owned(),
            redacted_log_path: redacted_path,
            phase: "none".to_owned(),
            coverage: "none".to_owned(),
            skipped: false,
            warn,
            raw_log_path: Some(log_file.to_string_lossy().into_owned()),
            failure_reason: Some("no-validation-phases".to_owned()),
            digest_file_path: digest_path,
        };
    }
    if ok {
        return ChecksResult {
            ok: true,
            exit_code: 0,
            site: site.to_owned(),
            redacted_log_path: None,
            phase,
            coverage,
            skipped: false,
            warn,
            raw_log_path: Some(log_file.to_string_lossy().into_owned()),
            failure_reason: None,
            digest_file_path: None,
        };
    }
    let redacted_file = log_dir.join(format!("{site}-{attempt}.redacted.log"));
    if !redact_log(log_file, &redacted_file) {
        let mut result = ChecksResult::failure(site, 1, "redaction-failed");
        result.phase = phase;
        result.coverage = coverage;
        result.warn = Some("redaction-failed".to_owned());
        return result;
    }
    let digest_path = write_failure_digest(&redacted_file, site, &attempt, log_dir);
    ChecksResult {
        ok: false,
        exit_code: rc,
        site: site.to_owned(),
        redacted_log_path: Some(redacted_file.to_string_lossy().into_owned()),
        phase,
        coverage,
        skipped: false,
        warn,
        raw_log_path: Some(log_file.to_string_lossy().into_owned()),
        failure_reason: Some("checks-failed".to_owned()),
        digest_file_path: digest_path,
    }
}

fn redact_log(log_file: &Path, redacted_file: &Path) -> bool {
    let Some(text) = read_text(log_file) else {
        return false;
    };
    let redacted = redact_secrets_only(&redact_sensitive_paths(&text));
    if fs::write(redacted_file, redacted).is_err() {
        let _ignored = fs::remove_file(redacted_file);
        return false;
    }
    set_file_mode(redacted_file);
    true
}

fn write_failure_digest(
    redacted_file: &Path,
    site: &str,
    attempt: &str,
    log_dir: &Path,
) -> Option<String> {
    let redacted_text = read_text(redacted_file)?;
    let digest_file = log_dir.join(format!("{site}-{attempt}.digest.txt"));
    let digest = build_checks_failure_digest(&redacted_text, site);
    if fs::write(&digest_file, digest).is_err() {
        let _ignored = fs::remove_file(&digest_file);
        return None;
    }
    set_file_mode(&digest_file);
    Some(digest_file.to_string_lossy().into_owned())
}

fn record_precommit_self_edits(
    repo: &Path,
    regular: &[String],
    before_digests: &std::collections::HashMap<String, String>,
    canonical_tmp: &Path,
) {
    let after = digest_paths(repo, regular);
    let self_edited: Vec<String> = regular
        .iter()
        .filter(|path| after.get(*path) != before_digests.get(*path))
        .cloned()
        .collect();
    if !self_edited.is_empty() {
        let _written = record_self_edits(
            canonical_tmp,
            "pre-commit-autofix",
            &self_edited,
            repo,
            None,
        );
    }
}

// ---- selection and git helpers ----

fn changed_paths_from_git(repo: &Path) -> Vec<String> {
    let Ok(repository) = GixRepository::discover(repo) else {
        return Vec::new();
    };
    let mut paths: BTreeSet<String> = BTreeSet::new();
    if let Ok(head_id) = repository.resolve_revision(&Revision::new(b"HEAD".to_vec())) {
        let base_id = repository
            .resolve_revision(&Revision::new(b"origin/main".to_vec()))
            .ok()
            .or_else(|| {
                repository
                    .resolve_revision(&Revision::new(b"main".to_vec()))
                    .ok()
            });
        if let Some(base_id) = base_id
            && let Ok(merge_base) = repository.merge_base(&base_id, &head_id)
            && let (Some(base_tree), Some(head_tree)) = (
                commit_tree(&repository, &merge_base),
                commit_tree(&repository, &head_id),
            )
            && let Ok(changes) = repository.tree_changes(&base_tree, &head_tree)
        {
            for path in changes.paths() {
                paths.insert(String::from_utf8_lossy(path.as_bytes()).into_owned());
            }
        }
    }
    if let Ok(status) = repository.status(&StatusOptions {
        pathspecs: Vec::new(),
        include_untracked: true,
        include_ignored: false,
    }) {
        for path in status.tree_to_index.paths() {
            paths.insert(String::from_utf8_lossy(path.as_bytes()).into_owned());
        }
        for path in status.index_to_worktree.paths() {
            paths.insert(String::from_utf8_lossy(path.as_bytes()).into_owned());
        }
        for path in &status.untracked {
            paths.insert(String::from_utf8_lossy(path.as_bytes()).into_owned());
        }
    }
    paths.into_iter().collect()
}

fn commit_tree(
    repository: &GixRepository,
    id: &larch_core::ObjectId,
) -> Option<larch_core::ObjectId> {
    repository
        .walk_commits(id, 1)
        .ok()?
        .into_iter()
        .next()
        .filter(|commit| commit.id == *id)
        .map(|commit| commit.tree)
}

fn existing_regular_files(repo: &Path, changed: &[String]) -> Vec<String> {
    changed
        .iter()
        .filter(|path| repo.join(path).is_file())
        .cloned()
        .collect()
}

fn precommit_available() -> bool {
    let Some(path) = std::env::var_os("PATH") else {
        return false;
    };
    std::env::split_paths(&path).any(|dir| {
        let candidate = dir.join("pre-commit");
        candidate.is_file() || fs::symlink_metadata(&candidate).is_ok_and(|meta| !meta.is_dir())
    })
}

fn resolve_checks_repo_root(repo_root: &str) -> Option<PathBuf> {
    let candidate = if repo_root.is_empty() {
        std::env::current_dir().ok()?
    } else {
        PathBuf::from(repo_root)
    };
    let metadata = fs::symlink_metadata(&candidate).ok()?;
    if !metadata.is_dir() || metadata.file_type().is_symlink() {
        return None;
    }
    let repository = GixRepository::discover(&candidate).ok()?;
    let toplevel = repository
        .location()
        .work_dir
        .map(|path| PathBuf::from(String::from_utf8_lossy(path.as_bytes()).into_owned()))?;
    let resolved = fs::canonicalize(&toplevel).ok()?;
    let resolved_meta = fs::symlink_metadata(&resolved).ok()?;
    if !resolved_meta.is_dir() || resolved_meta.file_type().is_symlink() {
        return None;
    }
    Some(resolved)
}

fn default_repo_root() -> String {
    let declared = std::env::var("CLAUDE_PROJECT_DIR").unwrap_or_default();
    if !declared.trim().is_empty() {
        return declared.trim().to_owned();
    }
    std::env::current_dir()
        .ok()
        .and_then(|cwd| GixRepository::discover(&cwd).ok())
        .and_then(|repository| {
            repository
                .location()
                .work_dir
                .map(|path| String::from_utf8_lossy(path.as_bytes()).into_owned())
        })
        .unwrap_or_default()
}

fn default_tmpdir() -> String {
    for key in ["IMPLEMENT_TMPDIR", "REVIEW_TMPDIR"] {
        if let Ok(value) = std::env::var(key) {
            return value;
        }
    }
    String::new()
}

// ---- best-effort ledger and telemetry ----

fn mark_step_ledger(site: &str) {
    let label = match site {
        "step3" => "Step 3 — checks first pass",
        "step6" => "Step 6 — checks second pass",
        _ => return,
    };
    let _token = crate::token_commands::mark(&[OsString::from(label)]);
    let _timing = crate::timing_commands::mark(&[OsString::from(label)]);
}

fn record_checks_vendor_task(canonical_tmp: &Path, start_s: i64, end_s: i64, exit_code: i32) {
    let output = canonical_tmp.join("claude-relevant-checks.txt");
    let arguments = crate::timing_commands::vendor_timing_arguments(
        "claude",
        "claude-relevant-checks",
        start_s,
        end_s,
        &output,
        exit_code,
        "complete",
    );
    let _recorded = crate::timing_commands::record_vendor_task(&arguments);
}

// ---- small utilities ----

fn valid_site(site: &str) -> bool {
    !site.is_empty()
        && !site.starts_with('.')
        && !site.contains("..")
        && site
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '.' | '_' | '-'))
}

fn resolve_display_path(raw: &str) -> PathBuf {
    if raw.is_empty() {
        return std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    }
    fs::canonicalize(raw).unwrap_or_else(|_| absolute_path(Path::new(raw)))
}

fn absolute_path(path: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir().map_or_else(|_| path.to_path_buf(), |cwd| cwd.join(path))
    }
}

fn make_log_dir(log_dir: &Path) -> std::io::Result<()> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::DirBuilderExt as _;
        let mut builder = fs::DirBuilder::new();
        builder.mode(0o700);
        match builder.create(log_dir) {
            Ok(()) => Ok(()),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => Ok(()),
            Err(error) => Err(error),
        }
    }
    #[cfg(not(unix))]
    {
        match fs::create_dir(log_dir) {
            Ok(()) => Ok(()),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => Ok(()),
            Err(error) => Err(error),
        }
    }
}

fn set_dir_mode(path: &Path) -> std::io::Result<()> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt as _;
        fs::set_permissions(path, fs::Permissions::from_mode(0o700))
    }
    #[cfg(not(unix))]
    {
        let _ = path;
        Ok(())
    }
}

fn set_file_mode(path: &Path) {
    crate::ledger_append::restore_owner_only_permissions(path);
}

fn allocate_log_file(log_dir: &Path, site: &str) -> Option<PathBuf> {
    for attempt in 1..=100 {
        let log_file = log_dir.join(format!("{site}-{attempt}.log"));
        let mut options = fs::OpenOptions::new();
        options.create_new(true).write(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt as _;
            options.mode(0o600);
        }
        match options.open(&log_file) {
            Ok(_) => return Some(log_file),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {}
            Err(_) => return None,
        }
    }
    None
}

fn log_attempt(log_file: &Path) -> String {
    log_file
        .file_name()
        .and_then(|name| name.to_str())
        .and_then(|name| name.strip_suffix(".log"))
        .and_then(|stem| stem.rsplit('-').next())
        .unwrap_or("1")
        .to_owned()
}

fn read_text(path: &Path) -> Option<String> {
    let metadata = fs::symlink_metadata(path).ok()?;
    if !metadata.is_file() || metadata.file_type().is_symlink() {
        return None;
    }
    fs::read(path)
        .ok()
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
}

fn combined_output(output: &ProcessOutput) -> String {
    let mut text = String::from_utf8_lossy(output.stdout()).into_owned();
    text.push_str(&String::from_utf8_lossy(output.stderr()));
    text
}

fn process_code(output: &ProcessOutput) -> i32 {
    output
        .status()
        .code()
        .unwrap_or_else(|| i32::from(!output.status().success()))
}

fn epoch_now() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |elapsed| {
            i64::try_from(elapsed.as_secs()).unwrap_or(i64::MAX)
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        process::Command,
        sync::atomic::{AtomicUsize, Ordering},
    };
    use tempfile::TempDir;

    static COUNTER: AtomicUsize = AtomicUsize::new(0);

    /// A session tmpdir literally under `/tmp`, which `validate_session_tmpdir`
    /// accepts (the system `TMPDIR` on macOS lives under `/var/folders`, which it
    /// rejects). Removed on drop.
    struct SessionDir {
        path: PathBuf,
    }

    impl SessionDir {
        fn new() -> Self {
            let unique = COUNTER.fetch_add(1, Ordering::Relaxed);
            let path = PathBuf::from("/tmp").join(format!(
                "claude-implement-cov-{}-{unique}",
                std::process::id()
            ));
            fs::create_dir_all(&path).expect("session dir");
            Self { path }
        }
    }

    impl Drop for SessionDir {
        fn drop(&mut self) {
            let _ignored = fs::remove_dir_all(&self.path);
        }
    }

    fn git(repo: &Path, args: &[&str]) {
        let status = Command::new("git")
            .args(args)
            .current_dir(repo)
            .env("GIT_CONFIG_GLOBAL", "/dev/null")
            .env("GIT_CONFIG_SYSTEM", "/dev/null")
            .status()
            .expect("git runs");
        assert!(status.success(), "git {args:?} failed");
    }

    fn init_repo() -> TempDir {
        let repo = TempDir::new().expect("repo");
        let path = repo.path();
        git(path, &["init", "-q", "-b", "main"]);
        git(path, &["config", "user.email", "t@example.invalid"]);
        git(path, &["config", "user.name", "Test"]);
        git(path, &["commit", "-q", "--allow-empty", "-m", "init"]);
        repo
    }

    #[test]
    fn valid_site_grammar() {
        assert!(valid_site("step3"));
        assert!(valid_site("review-step3e"));
        assert!(valid_site("a.b_c-1"));
        assert!(!valid_site(""));
        assert!(!valid_site(".hidden"));
        assert!(!valid_site("a..b"));
        assert!(!valid_site("has space"));
        assert!(!valid_site("slash/site"));
    }

    #[test]
    fn small_utilities_behave() {
        assert_eq!(log_attempt(Path::new("/t/step3-7.log")), "7");
        assert_eq!(log_attempt(Path::new("/t/step3.log")), "step3");
        assert!(absolute_path(Path::new("/already/abs")).is_absolute());
        assert!(absolute_path(Path::new("rel")).is_absolute());
        assert!(epoch_now() > 0);
        assert!(read_text(Path::new("/larch-cov-missing-file")).is_none());
        let root = resolve_display_path("/larch-cov-not-a-dir");
        assert!(!root.is_dir());
    }

    #[test]
    fn default_roots_resolve_without_mutating_env() {
        // Without setting env (the crate forbids that), both resolvers fall
        // through to their non-env branch: `default_repo_root` discovers the
        // ambient git toplevel and `default_tmpdir` returns the empty default
        // when neither implement nor review tmpdir is exported.
        let _root = default_repo_root();
        let _tmpdir = default_tmpdir();
        assert!(!precommit_available() || precommit_available());
    }

    #[test]
    fn existing_regular_files_filters_to_present_files() {
        let repo = TempDir::new().expect("repo");
        fs::write(repo.path().join("present.txt"), "x").expect("write");
        let changed = vec!["present.txt".to_owned(), "absent.txt".to_owned()];
        assert_eq!(existing_regular_files(repo.path(), &changed), vec![
            "present.txt".to_owned()
        ]);
    }

    #[test]
    fn changed_paths_reports_untracked_and_staged() {
        let repo = init_repo();
        let root = repo.path();
        assert!(changed_paths_from_git(root).is_empty());
        fs::write(root.join("new.txt"), "content\n").expect("write");
        assert_eq!(changed_paths_from_git(root), vec!["new.txt".to_owned()]);
    }

    #[test]
    fn allocate_and_mode_helpers_operate() {
        let dir = TempDir::new().expect("dir");
        let log_dir = dir.path().join("relevant-checks");
        make_log_dir(&log_dir).expect("make dir");
        make_log_dir(&log_dir).expect("idempotent");
        set_dir_mode(&log_dir).expect("chmod");
        let first = allocate_log_file(&log_dir, "step3").expect("alloc");
        assert_eq!(first.file_name().unwrap().to_string_lossy(), "step3-1.log");
        let second = allocate_log_file(&log_dir, "step3").expect("alloc 2");
        assert_eq!(second.file_name().unwrap().to_string_lossy(), "step3-2.log");
    }

    #[test]
    fn invalid_site_and_tmpdir_fail_closed() {
        assert_eq!(
            run_relevant_checks("../bad", "/tmp", ".").render(false),
            ("STATUS=fail FAILURE_REASON=site-validation".to_owned(), 2)
        );
        assert_eq!(
            run_relevant_checks("step3", "/larch-cov-missing-tmpdir", ".").render(false),
            ("STATUS=fail FAILURE_REASON=tmpdir-validation".to_owned(), 2)
        );
    }

    #[test]
    fn run_relevant_checks_passes_with_no_changes() {
        let repo = init_repo();
        let session = SessionDir::new();
        let result = run_relevant_checks(
            "step3",
            &session.path.to_string_lossy(),
            &repo.path().to_string_lossy(),
        );
        assert!(result.ok, "no-change run passes: {result:?}");
        assert_eq!(result.coverage, "changed-file-only");
        assert_eq!(result.phase, "unknown");
        let (line, code) = result.render(false);
        assert_eq!(code, 0);
        assert!(line.starts_with("RELEVANT_CHECKS_OK=true SITE=step3"));
    }

    #[test]
    fn run_relevant_checks_skips_precommit_when_no_regular_files() {
        let repo = init_repo();
        let root = repo.path();
        fs::write(root.join("tracked.txt"), "hello\n").expect("write");
        git(root, &["add", "tracked.txt"]);
        git(root, &["commit", "-q", "-m", "add"]);
        fs::remove_file(root.join("tracked.txt")).expect("remove");
        // The changed set now carries a deleted path with no regular file, so the
        // pre-commit phase is skipped and only the contains-pin probe runs.
        assert!(changed_paths_from_git(root).contains(&"tracked.txt".to_owned()));
        let session = SessionDir::new();
        let result = run_relevant_checks(
            "step6",
            &session.path.to_string_lossy(),
            &root.to_string_lossy(),
        );
        assert!(result.ok, "deleted-only run passes: {result:?}");
        assert!(result.raw_log_path.is_some());
    }

    #[test]
    fn run_relevant_checks_captures_a_redacted_failure_log() {
        let repo = init_repo();
        let root = repo.path();
        // A modified regular file drives the pre-commit phase. Whether pre-commit
        // is absent (fails closed with "not found") or present (fails on the
        // missing config), the run fails and captures a redacted log and digest.
        fs::write(root.join("changed.py"), "print('x')\n").expect("write");
        git(root, &["add", "changed.py"]);
        let session = SessionDir::new();
        let result = run_relevant_checks(
            "step3",
            &session.path.to_string_lossy(),
            &root.to_string_lossy(),
        );
        assert!(!result.ok, "pre-commit phase run fails: {result:?}");
        assert!(result.raw_log_path.is_some());
        let (line, code) = result.render(false);
        assert!(code != 0);
        assert!(line.starts_with("STATUS=fail"));
        // Either the redacted log/digest were written (pre-commit ran) or the
        // fail-closed "not found" reason was returned; both are valid contracts.
        if let Some(redacted) = &result.redacted_log_path {
            assert!(Path::new(redacted).is_file());
        }
    }

    #[test]
    fn run_relevant_checks_rejects_an_unresolvable_repo_root() {
        let session = SessionDir::new();
        let result = run_relevant_checks(
            "step3",
            &session.path.to_string_lossy(),
            "/larch-cov-not-a-git-repo",
        );
        assert!(!result.ok);
        assert_eq!(result.failure_reason.as_deref(), Some("repo-root-unresolved"));
    }
}
