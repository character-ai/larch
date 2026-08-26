//! Advisory hook commands with confined, descriptor-relative local state.

use std::{
    env,
    ffi::OsString,
    fs,
    io::{self, BufRead as _, BufReader, Read as _, Write as _},
    path::{Path, PathBuf},
    process::{Command, ExitCode, Stdio},
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use chrono::Utc;
use larch_adapters::{GixRepository, bgjob_registry::find_entry_for_clone, read_first_raw_key};
use larch_core::{
    Head, ReferenceKind, ReferenceTarget, RepositoryRead as _, StatusOptions, binary_on_path,
    implement_session_roots,
};
use serde::Serialize;
use serde_json::{Map, Value};
use sha2::{Digest as _, Sha256};

#[cfg(unix)]
#[allow(deprecated)]
use nix::fcntl::flock;
#[cfg(unix)]
use nix::{
    errno::Errno,
    fcntl::{AtFlags, FlockArg, OFlag, open, openat, renameat},
    sys::stat::{Mode, SFlag, fchmod, fstat, fstatat, mkdirat},
    unistd::{UnlinkatFlags, unlinkat},
};
#[cfg(unix)]
use std::os::unix::ffi::OsStringExt as _;
#[cfg(unix)]
use std::{
    fs::File,
    os::fd::{AsRawFd as _, OwnedFd},
    thread,
    time::Instant,
};
#[cfg(unix)]
use uuid::Uuid;

const WINDOW_SECONDS: u8 = 30;
const THRESHOLD_COUNT: &str = "3";
const STATE_DIR_NAME: &str = "larch-read-poll";
const TMP_FALLBACK: &str = "/private/tmp";
const REMINDER_TEXT: &str = "Read-poll detected: repeated identical Read calls. Use one read after state changes instead of polling.";
const MAX_STDIN_BYTES: usize = 65_536;
const MAX_STATE_BYTES: u64 = 512;
const MAX_SYMLINK_HOPS: usize = 40;
const ACTIVATION_TTL: Duration = Duration::from_secs(360 * 60);
const ACTIVATION_SCAN_LIMIT: usize = 4_096;
pub const DENY_EDIT_WRITE_TOKENS: &[&str] = &[
    "research",
    "audit-umbrella",
    "file-bug",
    "complete-umbrella",
    "debate",
    "triage",
    "umbrella",
];
const DENY_EDIT_WRITE_REASON: &str = "The active skill is read-only-repo -- Edit/Write/NotebookEdit outside /tmp or the larch session cache is not permitted.";
const BLOCK_READ_STDIN_REASON: &str =
    "submodule edit guard: failed to read stdin, blocking as precaution";
const BLOCK_PARSE_REASON: &str =
    "submodule edit guard: failed to parse tool input, blocking as precaution";
const BLOCK_ABSOLUTE_REASON: &str =
    "submodule edit guard: tool_input.file_path is not absolute, blocking as precaution";
const BACKGROUND_MALFORMED_REASON: &str =
    "run_in_background denied: malformed hook JSON cannot rule out Bash background launch";
const BACKGROUND_PARSE_REASON: &str = "run_in_background denied: cannot parse Bash tool_input";
const BACKGROUND_CWD_REASON: &str =
    "run_in_background denied: missing canonical cwd for Bash background launch";
const BACKGROUND_REGISTRY_REASON: &str =
    "run_in_background denied: cannot read active bgjob registry entry";
const SESSIONSTART_JQ_ONLY_FALLBACK: &str = r#"{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"larch hook preflight: jq not on PATH (install jq for advisory hook output)."}}"#;
const SESSIONSTART_JQ_GIT_FALLBACK: &str = r#"{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"larch hook preflight: jq not on PATH and git not on PATH; install jq and git for advisory hook output."}}"#;
const SESSIONSTART_GIT_MISSING: &str = "larch hook preflight: git not on PATH. The submodule-edit guard and most larch scripts depend on git.";
const SESSIONSTART_SPARSE_DRIFT: &str = "larch hook preflight: larch-local marketplace sparse checkout is out of date; run /upgrade-larch to repair it.";
const SESSIONSTART_DIRTY: &str = "larch hook preflight: working tree has uncommitted changes; the next /implement will fail preflight or inherit them.";
const SESSIONSTART_STASH: &str = "larch hook preflight: leftover larch-managed stash detected (run 'git stash list | grep larch-' to inspect).";
const SESSIONSTART_INTERRUPTED: &str =
    "larch hook preflight: interrupted rebase/merge/cherry-pick state on disk.";
const SESSIONSTART_UNMERGED: &str = "larch hook preflight: local feature branch(es) not merged into main; consider deleting or pushing.";
const SESSIONSTART_REVIEW_BOUNDARY_PREFIX: &str =
    "larch hook preflight: pending post-/review boundary in active /implement tmpdir";
const CLEANUP_LOG_PREFIX: &str = "larch-cleanup-sessionstart";
#[cfg(any(not(unix), test))]
const AUDIT_LOG_RELATIVE: &str = ".claude/hook-audit.log";
#[cfg(unix)]
const STATE_DIRECTORY_MODE: Mode = Mode::S_IRWXU;
#[cfg(unix)]
const STATE_FILE_MODE: Mode = Mode::from_bits_retain(0o600);
#[cfg(unix)]
const AUDIT_DIRECTORY_MODE: Mode = Mode::S_IRWXU;
#[cfg(unix)]
const AUDIT_FILE_MODE: Mode = Mode::from_bits_retain(0o600);
#[cfg(unix)]
const LOCK_WAIT: Duration = Duration::from_millis(100);
#[cfg(unix)]
const TEMP_ATTEMPTS: usize = 8;

#[derive(Clone, Debug, Eq, PartialEq)]
struct ReadEvent {
    cwd: String,
    file_path: String,
    offset: String,
    session_id: String,
    conversation_id: String,
    now: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct StateRow {
    path_hash: String,
    offset: String,
    count: String,
    epoch: String,
}

#[derive(Serialize)]
struct DenyEnvelope<'reason> {
    #[serde(rename = "hookSpecificOutput")]
    hook_specific_output: DenyOutput<'reason>,
}

#[derive(Serialize)]
struct DenyOutput<'reason> {
    #[serde(rename = "hookEventName")]
    hook_event_name: &'static str,
    #[serde(rename = "permissionDecision")]
    permission_decision: &'static str,
    #[serde(rename = "permissionDecisionReason")]
    permission_decision_reason: &'reason str,
}

#[derive(Serialize)]
struct SessionstartEnvelope<'context> {
    #[serde(rename = "hookSpecificOutput")]
    hook_specific_output: SessionstartOutput<'context>,
}

#[derive(Serialize)]
struct SessionstartOutput<'context> {
    #[serde(rename = "hookEventName")]
    hook_event_name: &'static str,
    #[serde(rename = "additionalContext")]
    additional_context: &'context str,
}

#[derive(Serialize)]
struct StopEnvelope<'reason> {
    decision: &'static str,
    reason: &'reason str,
}

#[derive(Serialize)]
struct AuditRecord<'payload> {
    ts: &'payload str,
    event: &'static str,
    payload: &'payload Value,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct HookContext {
    cwd: String,
    session_id: String,
    stop_hook_active: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ProbeError {
    SymlinkLimit,
    ReadLink,
    EmptyTarget,
    Lookup,
    Canonicalize,
}

fn deny_envelope(reason: &str) -> String {
    serde_json::to_string(&DenyEnvelope {
        hook_specific_output: DenyOutput {
            hook_event_name: "PreToolUse",
            permission_decision: "deny",
            permission_decision_reason: reason,
        },
    })
    .expect("a deny envelope containing only strings is serializable")
}

fn emit_deny(reason: &str) {
    let _ = writeln!(io::stdout().lock(), "{}", deny_envelope(reason));
}

fn read_stdin_bytes() -> Result<Vec<u8>, ()> {
    let mut input = Vec::new();
    io::stdin()
        .lock()
        .take((MAX_STDIN_BYTES + 1) as u64)
        .read_to_end(&mut input)
        .map_err(|_| ())?;
    (input.len() <= MAX_STDIN_BYTES).then_some(input).ok_or(())
}

fn read_all_stdin_bytes() -> Result<Vec<u8>, ()> {
    let mut input = Vec::new();
    io::stdin().lock().read_to_end(&mut input).map_err(|_| ())?;
    Ok(input)
}

fn emit_line(value: &str) {
    let _ = writeln!(io::stdout().lock(), "{value}");
}

fn sessionstart_envelope(context: &str) -> String {
    serde_json::to_string_pretty(&SessionstartEnvelope {
        hook_specific_output: SessionstartOutput {
            hook_event_name: "SessionStart",
            additional_context: context,
        },
    })
    .expect("a SessionStart envelope containing strings is serializable")
}

fn stop_envelope(reason: &str) -> String {
    serde_json::to_string(&StopEnvelope {
        decision: "block",
        reason,
    })
    .expect("a Stop envelope containing strings is serializable")
}

fn hook_context(input: &[u8]) -> HookContext {
    let Ok(Value::Object(payload)) = serde_json::from_slice(input) else {
        return HookContext::default();
    };
    HookContext {
        cwd: json_text(payload.get("cwd")).unwrap_or_default(),
        session_id: json_text(payload.get("session_id")).unwrap_or_default(),
        stop_hook_active: json_text(payload.get("stop_hook_active")).as_deref() == Ok("true"),
    }
}

fn hook_session_roots() -> [PathBuf; 3] {
    implement_session_roots(
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    )
}

fn implement_session_dir_exists(roots: &[PathBuf], hook_cwd: &str) -> bool {
    if hook_cwd.is_empty() {
        return false;
    }
    roots.iter().any(|root| {
        fs::read_dir(root).is_ok_and(|entries| {
            entries.flatten().any(|entry| {
                entry
                    .file_name()
                    .to_string_lossy()
                    .starts_with("claude-implement-")
                    && entry.path().is_dir()
            })
        })
    })
}

fn active_implement_tmpdir(context: &HookContext) -> Option<PathBuf> {
    let roots = hook_session_roots();
    if !implement_session_dir_exists(&roots, &context.cwd) {
        return None;
    }
    let resolved = crate::session_lifecycle_commands::resolve_implement_tmpdir_for_hook(
        &context.cwd,
        &context.session_id,
    );
    (!resolved.is_empty()).then(|| PathBuf::from(resolved))
}

fn pending_review_boundary(tmpdir: &Path) -> Option<String> {
    if tmpdir.join(".run-cleaned-up").is_file()
        || !tmpdir.join("review-round-summary.md").is_file()
        || tmpdir.join(".review-boundary-passed").is_file()
    {
        return None;
    }
    Some(tmpdir.file_name().map_or_else(
        || "<implement-tmpdir>".into(),
        |name| name.to_string_lossy().into_owned(),
    ))
}

fn active_review_boundary(context: &HookContext) -> Option<String> {
    active_implement_tmpdir(context).and_then(|tmpdir| pending_review_boundary(&tmpdir))
}

fn review_boundary_advisory(basename: &str) -> String {
    format!(
        "{SESSIONSTART_REVIEW_BOUNDARY_PREFIX} ({basename}); NEXT REQUIRED: execute Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order per skills/implement/SKILL.md Step 5, then touch .review-boundary-passed."
    )
}

fn sparse_checkout_dirs(repository: &GixRepository) -> Option<Vec<String>> {
    let git_dir = repository_path(&repository.location().git_dir);
    let text = fs::read_to_string(git_dir.join("info/sparse-checkout")).ok()?;
    let mut directories = Vec::new();
    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('!') || line == "/*" {
            continue;
        }
        let directory = line.trim_start_matches('/').trim_end_matches('/');
        if !directory.is_empty() && !directory.contains('*') {
            directories.push(directory.to_owned());
        }
    }
    directories.sort();
    directories.dedup();
    Some(directories)
}

fn marketplace_sparse_cone_drift(home: Option<&Path>) -> bool {
    let Some(home) = home.filter(|path| !path.as_os_str().is_empty()) else {
        return false;
    };
    let clone = home.join(".claude/plugins/marketplaces/larch-local");
    if !clone.join(".git").is_dir() || clone.join("larch-logs").is_dir() {
        return false;
    }
    let Ok(repository) = GixRepository::open(&clone) else {
        return false;
    };
    sparse_checkout_dirs(&repository)
        .is_some_and(|configured| !configured.is_empty() && configured != [".claude-plugin"])
}

fn reflog_contains_larch(path: &Path) -> bool {
    let Ok(file) = fs::File::open(path) else {
        return false;
    };
    BufReader::new(file).split(b'\n').any(|line| {
        line.is_ok_and(|bytes| {
            bytes
                .iter()
                .position(|byte| *byte == b'\t')
                .is_some_and(|separator| {
                    bytes[separator + 1..]
                        .windows(6)
                        .any(|window| window == b"larch-")
                })
        })
    })
}

const fn object_target(target: &ReferenceTarget) -> Option<&larch_core::ObjectId> {
    match target {
        ReferenceTarget::Object(id) => Some(id),
        ReferenceTarget::Symbolic(_) => None,
    }
}

fn has_unmerged_local_branch(repository: &GixRepository) -> bool {
    let Ok(references) = repository.references() else {
        return false;
    };
    let Some(main) = references
        .iter()
        .find(|reference| reference.name.as_bytes() == b"refs/heads/main")
        .and_then(|reference| object_target(&reference.target))
    else {
        return false;
    };
    let current = match repository.head() {
        Ok(Head::Symbolic { name, .. }) => Some(name),
        Ok(Head::Detached { .. } | Head::Unborn { .. }) | Err(_) => None,
    };
    references.iter().any(|reference| {
        reference.kind == ReferenceKind::LocalBranch
            && reference.name.as_bytes() != b"refs/heads/main"
            && current
                .as_ref()
                .is_none_or(|name| name.as_bytes() != reference.name.as_bytes())
            && object_target(&reference.target)
                .is_some_and(|tip| repository.is_ancestor(tip, main).ok() == Some(false))
    })
}

fn stalled_run_advisory(git_dir: &Path) -> Option<String> {
    let sentinel = git_dir.join("larch-stalled-run.txt");
    if !sentinel.is_file() {
        return None;
    }
    let issue = read_first_raw_key(&sentinel, "ISSUE_NUMBER")
        .ok()
        .flatten()
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "unknown".to_owned());
    let step = read_first_raw_key(&sentinel, "STALL_STEP")
        .ok()
        .flatten()
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "unknown".to_owned());
    let stash = read_first_raw_key(&sentinel, "STASH_REF")
        .ok()
        .flatten()
        .unwrap_or_default();
    Some(if stash.is_empty() {
        format!(
            "larch hook preflight: a prior /implement run for #{issue} stalled at step {step}. No working-tree edits were stashed; inspect 'git status' / the issue for context."
        )
    } else {
        format!(
            "larch hook preflight: a prior /implement run for #{issue} stalled at step {step}. Working-tree edits stashed as {stash}. Resume via 'git stash apply {stash}' or drop via 'git stash drop {stash}'."
        )
    })
}

fn repository_health_advisories(start: &Path) -> Vec<String> {
    let Ok(repository) = GixRepository::discover(start) else {
        return Vec::new();
    };
    let location = repository.location();
    let git_dir = repository_path(&location.git_dir);
    let common_dir = repository_path(&location.common_dir);
    let mut advisories = Vec::new();
    if repository
        .local_status(&StatusOptions::default())
        .is_ok_and(|status| status.is_dirty())
    {
        advisories.push(SESSIONSTART_DIRTY.to_owned());
    }
    if reflog_contains_larch(&common_dir.join("logs/refs/stash")) {
        advisories.push(SESSIONSTART_STASH.to_owned());
    }
    if ["REBASE_HEAD", "MERGE_HEAD", "CHERRY_PICK_HEAD"]
        .iter()
        .any(|name| git_dir.join(name).exists())
    {
        advisories.push(SESSIONSTART_INTERRUPTED.to_owned());
    }
    if has_unmerged_local_branch(&repository) {
        advisories.push(SESSIONSTART_UNMERGED.to_owned());
    }
    if let Some(advisory) = stalled_run_advisory(&git_dir) {
        advisories.push(advisory);
    }
    advisories
}

fn health_advisories(
    input: &[u8],
    git_available: bool,
    home: Option<&Path>,
    current_dir: Option<&Path>,
) -> Vec<String> {
    let mut advisories = Vec::new();
    if git_available {
        if marketplace_sparse_cone_drift(home) {
            advisories.push(SESSIONSTART_SPARSE_DRIFT.to_owned());
        }
        if let Some(current_dir) = current_dir {
            advisories.extend(repository_health_advisories(current_dir));
        }
    } else {
        advisories.push(SESSIONSTART_GIT_MISSING.to_owned());
    }
    if let Some(basename) = active_review_boundary(&hook_context(input)) {
        advisories.push(review_boundary_advisory(&basename));
    }
    advisories
}

/// Run the advisory `hook sessionstart-health` command.
pub fn sessionstart_health(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        return ExitCode::SUCCESS;
    }
    let path = env::var("PATH").ok();
    let jq_available = binary_on_path("jq", path.as_deref());
    let git_available = binary_on_path("git", path.as_deref());
    if !jq_available {
        emit_line(if git_available {
            SESSIONSTART_JQ_ONLY_FALLBACK
        } else {
            SESSIONSTART_JQ_GIT_FALLBACK
        });
        return ExitCode::SUCCESS;
    }
    let input = read_stdin_bytes().unwrap_or_default();
    let home = env::var_os("HOME").filter(|value| !value.is_empty());
    let current_dir = env::current_dir().ok();
    let advisories = health_advisories(
        &input,
        git_available,
        home.as_deref().map(Path::new),
        current_dir.as_deref(),
    );
    if !advisories.is_empty() {
        emit_line(&sessionstart_envelope(&advisories.join(" ")));
    }
    ExitCode::SUCCESS
}

fn stop_reason(tmpdir_basename: &str) -> String {
    format!(
        "You halted mid-Step-5 (post-/review boundary).\n\nNEXT REQUIRED: execute the Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order per skills/implement/SKILL.md Step 5 post-/review directives, then touch .review-boundary-passed inside the active /implement tmpdir ({tmpdir_basename}) to release this guard.\n\nOperator escape: hard-quit the session, OR touch .run-cleaned-up inside the active /implement tmpdir to intentionally abandon the run."
    )
}

/// Run the post-review `hook stop-fail-close` command.
pub fn stop_fail_close(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        return ExitCode::SUCCESS;
    }
    let Ok(input) = read_stdin_bytes() else {
        return ExitCode::SUCCESS;
    };
    let context = hook_context(&input);
    if context.stop_hook_active {
        return ExitCode::SUCCESS;
    }
    if let Some(basename) = active_review_boundary(&context) {
        emit_line(&stop_envelope(&stop_reason(&basename)));
    }
    ExitCode::SUCCESS
}

fn audit_row(payload: &Value, timestamp: &str) -> Result<Vec<u8>, ()> {
    let mut row = serde_json::to_vec(&AuditRecord {
        ts: timestamp,
        event: "PostToolUse",
        payload,
    })
    .map_err(|_| ())?;
    row.push(b'\n');
    Ok(row)
}

#[cfg(unix)]
fn append_audit_record(project_dir: &Path, payload: &Value, timestamp: &str) -> Result<(), ()> {
    let project_dir = fs::canonicalize(project_dir).map_err(|_| ())?;
    let project = open(
        &project_dir,
        OFlag::O_RDONLY | OFlag::O_DIRECTORY | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
        Mode::empty(),
    )
    .map_err(|_| ())?;
    match mkdirat(&project, ".claude", AUDIT_DIRECTORY_MODE) {
        Ok(()) | Err(Errno::EEXIST) => {}
        Err(_) => return Err(()),
    }
    let audit_dir = openat(
        &project,
        ".claude",
        OFlag::O_RDONLY | OFlag::O_DIRECTORY | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
        Mode::empty(),
    )
    .map_err(|_| ())?;
    let opened_dir = fstat(&audit_dir).map_err(|_| ())?;
    let visible_dir = fstatat(&project, ".claude", AtFlags::AT_SYMLINK_NOFOLLOW).map_err(|_| ())?;
    if entry_kind(&opened_dir) != SFlag::S_IFDIR
        || entry_kind(&visible_dir) != SFlag::S_IFDIR
        || !same_file(&opened_dir, &visible_dir)
    {
        return Err(());
    }
    match fstatat(&audit_dir, "hook-audit.log", AtFlags::AT_SYMLINK_NOFOLLOW) {
        Ok(stat) if is_single_link_regular(&stat) => {}
        Err(Errno::ENOENT) => {}
        Ok(_) | Err(_) => return Err(()),
    }
    let descriptor = openat(
        &audit_dir,
        "hook-audit.log",
        OFlag::O_WRONLY | OFlag::O_CREAT | OFlag::O_APPEND | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
        AUDIT_FILE_MODE,
    )
    .map_err(|_| ())?;
    let opened_log = fstat(&descriptor).map_err(|_| ())?;
    let visible_log =
        fstatat(&audit_dir, "hook-audit.log", AtFlags::AT_SYMLINK_NOFOLLOW).map_err(|_| ())?;
    let current_dir = fstatat(&project, ".claude", AtFlags::AT_SYMLINK_NOFOLLOW).map_err(|_| ())?;
    if !is_single_link_regular(&opened_log)
        || !is_single_link_regular(&visible_log)
        || !same_file(&opened_log, &visible_log)
        || !same_file(&opened_dir, &current_dir)
    {
        return Err(());
    }
    fchmod(&descriptor, AUDIT_FILE_MODE).map_err(|_| ())?;
    let row = audit_row(payload, timestamp)?;
    let mut file = File::from(descriptor);
    file.write_all(&row).map_err(|_| ())
}

#[cfg(not(unix))]
fn append_audit_record(project_dir: &Path, payload: &Value, timestamp: &str) -> Result<(), ()> {
    let project_dir = fs::canonicalize(project_dir).map_err(|_| ())?;
    let audit_dir = project_dir.join(".claude");
    match fs::symlink_metadata(&audit_dir) {
        Ok(metadata) if metadata.is_dir() && !metadata.file_type().is_symlink() => {}
        Err(error) if error.kind() == io::ErrorKind::NotFound => {
            fs::create_dir(&audit_dir).map_err(|_| ())?;
        }
        Ok(_) | Err(_) => return Err(()),
    }
    let log = project_dir.join(AUDIT_LOG_RELATIVE);
    if fs::symlink_metadata(&log)
        .is_ok_and(|metadata| metadata.file_type().is_symlink() || !metadata.is_file())
    {
        return Err(());
    }
    let row = audit_row(payload, timestamp)?;
    let mut file = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(log)
        .map_err(|_| ())?;
    file.write_all(&row).map_err(|_| ())
}

fn append_audit_input(project_dir: &Path, input: &[u8], timestamp: &str) -> Result<(), ()> {
    let payload @ Value::Object(_) = serde_json::from_slice(input).map_err(|_| ())? else {
        return Err(());
    };
    append_audit_record(project_dir, &payload, timestamp)
}

/// Run the opt-in advisory `hook audit-edit-write` command.
pub fn audit_edit_write(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        return ExitCode::SUCCESS;
    }
    let Ok(input) = read_all_stdin_bytes() else {
        return ExitCode::SUCCESS;
    };
    let project_dir = env::var_os("CLAUDE_PROJECT_DIR")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .or_else(|| env::current_dir().ok());
    if let Some(project_dir) = project_dir {
        let timestamp = Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string();
        let _ = append_audit_input(&project_dir, &input, &timestamp);
    }
    ExitCode::SUCCESS
}

fn launch_cleanup_sessionstart(plugin_root: &Path, temporary_root: &Path) {
    let entrypoint = plugin_root.join("scripts/larch.sh");
    if !entrypoint.is_file() {
        return;
    }
    let mut reap = Command::new(&entrypoint); // lint-subprocess-via-runner: ok the hook re-enters the verified bootstrap for an existing first-party command
    let _ = reap
        .args(["bgjob", "reap"])
        .env("CLAUDE_PLUGIN_ROOT", plugin_root)
        .env("LARCH_BOOTSTRAP_NO_INSTALL", "1")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status();

    let log_path = temporary_root.join(format!("{CLEANUP_LOG_PREFIX}-{}.log", std::process::id()));
    let mut log_options = fs::OpenOptions::new();
    log_options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt as _;
        log_options.mode(0o600);
    }
    let log = log_options.open(log_path).ok();
    let mut cleanup = Command::new(&entrypoint); // lint-subprocess-via-runner: ok the detached cleanup must outlive this hook and still enter through the verified bootstrap
    cleanup
        .args(["cleanup", "run"])
        .env("CLAUDE_PLUGIN_ROOT", plugin_root)
        .env("LARCH_BOOTSTRAP_NO_INSTALL", "1")
        .env_remove("LARCH_TEST_TMP_ROOT")
        .stdin(Stdio::null());
    if let Some(log) = log {
        if let Ok(stderr) = log.try_clone() {
            cleanup.stdout(Stdio::from(log)).stderr(Stdio::from(stderr));
        } else {
            cleanup.stdout(Stdio::null()).stderr(Stdio::null());
        }
    } else {
        cleanup.stdout(Stdio::null()).stderr(Stdio::null());
    }
    let _ = cleanup.spawn();
}

/// Run the advisory `hook cleanup-sessionstart` command.
pub fn cleanup_sessionstart(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        return ExitCode::SUCCESS;
    }
    let Some(plugin_root) = env::var_os("CLAUDE_PLUGIN_ROOT")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
    else {
        return ExitCode::SUCCESS;
    };
    let temporary_root = env::var_os("TMPDIR")
        .filter(|value| !value.is_empty())
        .map_or_else(|| PathBuf::from("/tmp"), PathBuf::from);
    launch_cleanup_sessionstart(&plugin_root, &temporary_root);
    ExitCode::SUCCESS
}

/// Run the advisory `hook sessionstart-statusline` command.
pub fn sessionstart_statusline(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        return ExitCode::SUCCESS;
    }
    let Ok(input) = read_stdin_bytes() else {
        return ExitCode::SUCCESS;
    };
    let Some(plugin_root) = env::var_os("CLAUDE_PLUGIN_ROOT")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
    else {
        return ExitCode::SUCCESS;
    };
    let payload = String::from_utf8_lossy(&input);
    crate::progress_commands::sessionstart_statusline(&payload, &plugin_root);
    ExitCode::SUCCESS
}

fn json_text(value: Option<&Value>) -> Result<String, ()> {
    match value {
        None | Some(Value::Null) => Ok(String::new()),
        Some(Value::String(value)) => Ok(value.clone()),
        Some(value) => serde_json::to_string(value).map_err(|_| ()),
    }
}

fn block_file_path(input: &[u8]) -> Result<Option<String>, ()> {
    let payload: Value = serde_json::from_slice(input).map_err(|_| ())?;
    let payload = payload.as_object().ok_or(())?;
    let Some(tool_input) = payload.get("tool_input") else {
        return Ok(None);
    };
    if tool_input.is_null() {
        return Ok(None);
    }
    let tool_input = tool_input.as_object().ok_or(())?;
    let path = json_text(tool_input.get("file_path"))?;
    Ok((!path.is_empty()).then_some(path))
}

fn resolve_probe_directory(path: &Path) -> Result<Option<PathBuf>, ProbeError> {
    let mut resolved = path.to_path_buf();
    let mut hops = 0_usize;
    loop {
        match fs::symlink_metadata(&resolved) {
            Ok(metadata) if metadata.file_type().is_symlink() => {
                if hops >= MAX_SYMLINK_HOPS {
                    return Err(ProbeError::SymlinkLimit);
                }
                let target = fs::read_link(&resolved).map_err(|_| ProbeError::ReadLink)?;
                if target.as_os_str().is_empty() {
                    return Err(ProbeError::EmptyTarget);
                }
                resolved = if target.is_absolute() {
                    target
                } else {
                    resolved
                        .parent()
                        .unwrap_or_else(|| Path::new("/"))
                        .join(target)
                };
                hops += 1;
            }
            Ok(_) => break,
            Err(error)
                if matches!(
                    error.kind(),
                    io::ErrorKind::NotFound | io::ErrorKind::NotADirectory
                ) =>
            {
                break;
            }
            Err(_) => return Err(ProbeError::Lookup),
        }
    }

    let mut probe = resolved.as_path();
    loop {
        if probe == Path::new("/") {
            return Ok(None);
        }
        match fs::metadata(probe) {
            Ok(metadata) => {
                let directory = if metadata.is_file() {
                    probe.parent().unwrap_or_else(|| Path::new("/"))
                } else {
                    probe
                };
                return fs::canonicalize(directory)
                    .map(Some)
                    .map_err(|_| ProbeError::Canonicalize);
            }
            Err(error)
                if matches!(
                    error.kind(),
                    io::ErrorKind::NotFound | io::ErrorKind::NotADirectory
                ) =>
            {
                probe = probe.parent().ok_or(ProbeError::Lookup)?;
            }
            Err(_) => return Err(ProbeError::Lookup),
        }
    }
}

#[cfg(unix)]
fn repository_path(path: &larch_core::GitPath) -> PathBuf {
    PathBuf::from(OsString::from_vec(path.as_bytes().to_vec()))
}

#[cfg(not(unix))]
fn repository_path(path: &larch_core::GitPath) -> PathBuf {
    PathBuf::from(String::from_utf8_lossy(path.as_bytes()).into_owned())
}

fn discovered_worktree_root(start: &Path) -> Option<PathBuf> {
    let repository = GixRepository::discover(start).ok()?;
    let work_dir = repository.location().work_dir?;
    fs::canonicalize(repository_path(&work_dir)).ok()
}

fn block_submodule_reason(
    input: &[u8],
    project_dir: Option<&Path>,
    current_dir: Option<&Path>,
) -> Option<String> {
    let file_path = match block_file_path(input) {
        Ok(Some(path)) => PathBuf::from(path),
        Ok(None) => return None,
        Err(()) => return Some(BLOCK_PARSE_REASON.to_owned()),
    };
    if !file_path.is_absolute() {
        return Some(BLOCK_ABSOLUTE_REASON.to_owned());
    }
    let repo_root = project_dir
        .and_then(discovered_worktree_root)
        .or_else(|| current_dir.and_then(discovered_worktree_root))?;
    let probe_dir = match resolve_probe_directory(&file_path) {
        Ok(Some(path)) => path,
        Ok(None) | Err(ProbeError::Lookup | ProbeError::Canonicalize) => return None,
        Err(ProbeError::SymlinkLimit) => {
            return Some(format!(
                "submodule edit guard: symlink resolution exceeded {MAX_SYMLINK_HOPS} hops (possible cycle), blocking as precaution"
            ));
        }
        Err(ProbeError::ReadLink) => {
            return Some(format!(
                "submodule edit guard: readlink failed on '{}', blocking as precaution",
                file_path.display()
            ));
        }
        Err(ProbeError::EmptyTarget) => {
            return Some(format!(
                "submodule edit guard: readlink returned empty target for '{}', blocking as precaution",
                file_path.display()
            ));
        }
    };
    let file_repository = GixRepository::discover(&probe_dir).ok()?;
    let file_location = file_repository.location();
    let file_repo_root =
        fs::canonicalize(repository_path(file_location.work_dir.as_ref()?)).ok()?;
    if file_repo_root == repo_root {
        return None;
    }
    let file_git_dir = fs::canonicalize(repository_path(&file_location.common_dir)).ok()?;
    let superproject = GixRepository::open(&repo_root).ok()?;
    let checkouts = superproject.submodule_checkouts().ok()?;
    let is_submodule = checkouts.into_iter().any(|checkout| {
        fs::canonicalize(checkout.work_dir).ok().as_ref() == Some(&file_repo_root)
            && fs::canonicalize(checkout.git_dir).ok().as_ref() == Some(&file_git_dir)
    });
    if !is_submodule {
        return None;
    }
    let submodule_path = file_repo_root
        .strip_prefix(&repo_root)
        .ok()?
        .to_string_lossy();
    Some(format!(
        "This file is inside the '{submodule_path}' submodule. Never edit submodules directly here; file PRs in the submodule's own repo instead."
    ))
}

/// Run the fail-closed `hook block-submodule-edit` command.
pub fn block_submodule_edit(_arguments: &[OsString]) -> ExitCode {
    let Ok(input) = read_stdin_bytes() else {
        emit_deny(BLOCK_READ_STDIN_REASON);
        return ExitCode::SUCCESS;
    };
    let project_dir = env::var_os("CLAUDE_PROJECT_DIR").filter(|value| !value.is_empty());
    let current_dir = env::current_dir().ok();
    if let Some(reason) = block_submodule_reason(
        &input,
        project_dir.as_deref().map(Path::new),
        current_dir.as_deref(),
    ) {
        emit_deny(&reason);
    }
    ExitCode::SUCCESS
}

fn cache_root(xdg_cache_home: Option<&Path>, home: Option<&Path>) -> Option<PathBuf> {
    xdg_cache_home
        .filter(|path| !path.as_os_str().is_empty())
        .map(Path::to_path_buf)
        .or_else(|| {
            home.filter(|path| !path.as_os_str().is_empty())
                .map(|path| path.join(".cache"))
        })
}

fn recognized_edit_token(token: &str) -> bool {
    DENY_EDIT_WRITE_TOKENS.contains(&token)
}

fn activation_is_live(token: &str, cache_root: &Path, now: SystemTime) -> bool {
    if !recognized_edit_token(token) {
        return false;
    }
    let activation = cache_root.join("larch/deny-edit-write-active");
    let mut pending = vec![activation];
    let mut observed = 0_usize;
    let prefix = format!("{token}-");
    while let Some(directory) = pending.pop() {
        let Ok(entries) = fs::read_dir(directory) else {
            return false;
        };
        for entry in entries {
            let Ok(entry) = entry else {
                return false;
            };
            observed += 1;
            if observed > ACTIVATION_SCAN_LIMIT {
                return false;
            }
            let Ok(metadata) = fs::symlink_metadata(entry.path()) else {
                return false;
            };
            if metadata.file_type().is_dir() {
                pending.push(entry.path());
                continue;
            }
            if !metadata.file_type().is_file()
                || !entry
                    .file_name()
                    .as_encoded_bytes()
                    .starts_with(prefix.as_bytes())
            {
                continue;
            }
            let Ok(modified) = metadata.modified() else {
                return false;
            };
            if modified > now
                || now
                    .duration_since(modified)
                    .is_ok_and(|age| age < ACTIVATION_TTL)
            {
                return true;
            }
        }
    }
    false
}

fn edit_target(input: &[u8]) -> Result<PathBuf, ()> {
    let payload: Value = serde_json::from_slice(input).map_err(|_| ())?;
    let payload = payload.as_object().ok_or(())?;
    let tool_input = payload
        .get("tool_input")
        .and_then(Value::as_object)
        .ok_or(())?;
    ["file_path", "notebook_path"]
        .into_iter()
        .filter_map(|name| tool_input.get(name).and_then(Value::as_str))
        .find(|path| !path.is_empty())
        .map(PathBuf::from)
        .ok_or(())
}

fn active_edit_reason(input: &[u8], cache_root: &Path) -> Option<&'static str> {
    let Ok(target) = edit_target(input) else {
        return Some(DENY_EDIT_WRITE_REASON);
    };
    if !target.is_absolute() {
        return Some(DENY_EDIT_WRITE_REASON);
    }
    let Ok(temporary_root) = fs::canonicalize("/tmp") else {
        return Some(DENY_EDIT_WRITE_REASON);
    };
    let sessions_root = fs::canonicalize(cache_root.join("larch/sessions"))
        .ok()
        .filter(|path| path.is_dir());
    let Ok(Some(probe_dir)) = resolve_probe_directory(&target) else {
        return Some(DENY_EDIT_WRITE_REASON);
    };
    if probe_dir.starts_with(&temporary_root)
        || sessions_root
            .as_ref()
            .is_some_and(|root| probe_dir.starts_with(root))
    {
        None
    } else {
        Some(DENY_EDIT_WRITE_REASON)
    }
}

/// Run the token-scoped, fail-closed `hook deny-edit-write` command.
pub fn deny_edit_write(arguments: &[OsString]) -> ExitCode {
    let token = arguments
        .first()
        .and_then(|value| value.to_str())
        .unwrap_or_default();
    let xdg_cache_home = env::var_os("XDG_CACHE_HOME").filter(|value| !value.is_empty());
    let home = env::var_os("HOME").filter(|value| !value.is_empty());
    let Some(cache_root) = cache_root(
        xdg_cache_home.as_deref().map(Path::new),
        home.as_deref().map(Path::new),
    ) else {
        return ExitCode::SUCCESS;
    };
    if !activation_is_live(token, &cache_root, SystemTime::now()) {
        return ExitCode::SUCCESS;
    }
    let Ok(input) = read_stdin_bytes() else {
        emit_deny(DENY_EDIT_WRITE_REASON);
        return ExitCode::SUCCESS;
    };
    if let Some(reason) = active_edit_reason(&input, &cache_root) {
        emit_deny(reason);
    }
    ExitCode::SUCCESS
}

fn is_documented_bgjob_wait(command: &str) -> bool {
    let mut normalized = command.replace(['\n', '\r', '\t'], " ").trim().to_owned();
    while normalized.contains("  ") {
        normalized = normalized.replace("  ", " ");
    }
    if ["&&", "||", ";", "|", "`", "$(", ">", "<"]
        .iter()
        .any(|token| normalized.contains(token))
    {
        return false;
    }
    let arguments = normalized
        .strip_prefix("${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh")
        .or_else(|| normalized.strip_prefix("\"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh\""));
    arguments.is_some_and(|arguments| {
        arguments.starts_with(" bgjob wait ") || arguments == " bgjob wait"
    })
}

fn background_fields(payload: &Value) -> Result<Option<(String, String)>, ()> {
    let Some(payload) = payload.as_object() else {
        return Ok(None);
    };
    if json_text(payload.get("tool_name"))? != "Bash" {
        return Ok(None);
    }
    let tool_input = match payload.get("tool_input") {
        None | Some(Value::Null) => Map::new(),
        Some(Value::Object(value)) => value.clone(),
        Some(_) => return Err(()),
    };
    let run_in_background = json_text(tool_input.get("run_in_background"))?;
    let command = json_text(tool_input.get("command"))?;
    let cwd = json_text(payload.get("cwd"))?;
    let background = run_in_background == "true"
        || (command.contains("run_in_background") && command.contains("true"));
    Ok(background.then_some((cwd, command)))
}

fn deny_run_in_background_reason(input: &[u8], registry_root: &Path) -> Option<String> {
    let payload: Value = match serde_json::from_slice(input) {
        Ok(payload) => payload,
        Err(_) => return Some(BACKGROUND_MALFORMED_REASON.to_owned()),
    };
    let (cwd, command) = match background_fields(&payload) {
        Ok(Some(fields)) => fields,
        Ok(None) => return None,
        Err(()) => return Some(BACKGROUND_PARSE_REASON.to_owned()),
    };
    if is_documented_bgjob_wait(&command) {
        return None;
    }
    let cwd = fs::canonicalize(cwd).ok().filter(|path| path.is_dir());
    let Some(cwd) = cwd else {
        return Some(BACKGROUND_CWD_REASON.to_owned());
    };
    match find_entry_for_clone(registry_root, &cwd) {
        Ok(Some(entry)) => Some(format!(
            "run_in_background denied: active larch bgjob registry exists for this clone ({})",
            entry.display()
        )),
        Ok(None) => None,
        Err(_) => Some(BACKGROUND_REGISTRY_REASON.to_owned()),
    }
}

/// Run the fail-closed `hook deny-run-in-background` command.
pub fn deny_run_in_background(_arguments: &[OsString]) -> ExitCode {
    if env::var("LARCH_HOOK_DENY_RUN_IN_BACKGROUND_DISABLE").as_deref() == Ok("1")
        || env::var("LARCH_CLAUDE_SUBPROCESS_HOOK_EXEMPT").as_deref() == Ok("1")
    {
        return ExitCode::SUCCESS;
    }
    let Ok(input) = read_stdin_bytes() else {
        emit_deny(BACKGROUND_MALFORMED_REASON);
        return ExitCode::SUCCESS;
    };
    let registry_root = env::var_os("LARCH_BGJOB_REGISTRY_ROOT")
        .filter(|value| !value.is_empty())
        .map_or_else(
            || {
                env::var_os("HOME").map_or_else(
                    || PathBuf::from("/.cache/larch/daemons"),
                    |home| PathBuf::from(home).join(".cache/larch/daemons"),
                )
            },
            PathBuf::from,
        );
    if let Some(reason) = deny_run_in_background_reason(&input, &registry_root) {
        emit_deny(&reason);
    }
    ExitCode::SUCCESS
}

/// Run the advisory `hook anti-read-poll` command.
///
/// Every failure intentionally returns success without output: Claude hook
/// notifications must never block the tool event that triggered them.
pub fn anti_read_poll(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        return ExitCode::SUCCESS;
    }
    let Some(event) = parse_stdin_event() else {
        return ExitCode::SUCCESS;
    };

    #[cfg(unix)]
    {
        if process_event(&event).is_ok_and(|count| count == THRESHOLD_COUNT) {
            emit_reminder();
        }
    }
    #[cfg(not(unix))]
    {
        let _ = event;
    }

    ExitCode::SUCCESS
}

fn parse_stdin_event() -> Option<ReadEvent> {
    let input = read_stdin_bytes().ok()?;
    let payload: Value = serde_json::from_slice(&input).ok()?;
    parse_payload(&payload)
}

fn parse_payload(payload: &Value) -> Option<ReadEvent> {
    let payload = payload.as_object()?;
    if string_field(payload, "tool_name") != "Read" {
        return None;
    }
    let tool_input = payload.get("tool_input")?.as_object()?;
    let file_path = string_field(tool_input, "file_path");
    if file_path.is_empty() {
        return None;
    }
    Some(ReadEvent {
        cwd: nonempty_or_root(string_field(payload, "cwd")),
        file_path,
        offset: offset_value(tool_input.get("offset")),
        session_id: string_field(payload, "session_id"),
        conversation_id: string_field(payload, "conversation_id"),
        now: now_value()?,
    })
}

fn string_field(object: &Map<String, Value>, name: &str) -> String {
    object
        .get(name)
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned()
}

fn nonempty_or_root(value: String) -> String {
    if value.is_empty() {
        "/".to_owned()
    } else {
        value
    }
}

fn offset_value(value: Option<&Value>) -> String {
    let raw = match value {
        Some(Value::String(value)) => value.clone(),
        Some(Value::Number(value)) => value.to_string(),
        _ => "0".to_owned(),
    };
    if is_offset(&raw) { raw } else { "0".to_owned() }
}

fn is_offset(value: &str) -> bool {
    let bytes = value.as_bytes();
    let start = usize::from(bytes.first() == Some(&b'-'));
    bytes.len() > start && bytes[start..].iter().all(u8::is_ascii_digit)
}

fn now_value() -> Option<String> {
    match env::var("HOOK_ANTI_READ_POLL_NOW") {
        Ok(value) if !value.is_empty() => normalize_decimal(&value),
        Ok(_) | Err(env::VarError::NotPresent) => SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .ok()
            .map(|duration| duration.as_secs().to_string()),
        Err(env::VarError::NotUnicode(_)) => None,
    }
}

fn session_key(event: &ReadEvent, discriminator: Option<&str>) -> String {
    if !event.session_id.is_empty() {
        return event.session_id.clone();
    }
    if !event.conversation_id.is_empty() {
        return event.conversation_id.clone();
    }
    discriminator.filter(|value| !value.is_empty()).map_or_else(
        || "nosession".to_owned(),
        |value| format!("nosession-{value}"),
    )
}

fn stable_digest(value: &str) -> String {
    let digest = Sha256::digest(value.as_bytes());
    format!("{digest:x}")[..32].to_owned()
}

fn state_basename(cwd: &str, resolved_session_key: &str) -> String {
    let cwd_hash = stable_digest(if cwd.is_empty() { "/" } else { cwd });
    let session_hash = stable_digest(resolved_session_key);
    format!("read-{cwd_hash}-{session_hash}.state")
}

fn path_hash(file_path: &str) -> String {
    stable_digest(file_path)
}

fn normalize_decimal(value: &str) -> Option<String> {
    if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    let trimmed = value.trim_start_matches('0');
    Some(if trimmed.is_empty() {
        "0".to_owned()
    } else {
        trimmed.to_owned()
    })
}

fn increment_decimal(value: &str) -> String {
    let mut bytes = value.as_bytes().to_vec();
    for digit in bytes.iter_mut().rev() {
        if *digit == b'9' {
            *digit = b'0';
        } else {
            *digit += 1;
            return String::from_utf8_lossy(&bytes).into_owned();
        }
    }
    let mut incremented = Vec::with_capacity(bytes.len() + 1);
    incremented.push(b'1');
    incremented.extend(bytes);
    String::from_utf8_lossy(&incremented).into_owned()
}

fn decimal_at_least(left: &str, right: &str) -> bool {
    left.len() > right.len() || (left.len() == right.len() && left >= right)
}

fn elapsed_is_in_window(now: &str, prior: &str) -> bool {
    if !decimal_at_least(now, prior) {
        return false;
    }
    let mut borrow = 0_i16;
    let mut difference = Vec::with_capacity(now.len());
    let now_bytes = now.as_bytes();
    let prior_bytes = prior.as_bytes();
    for index in 0..now_bytes.len() {
        let now_index = now_bytes.len() - index - 1;
        let prior_digit = prior_bytes
            .get(prior_bytes.len().wrapping_sub(index + 1))
            .map_or(0_i16, |byte| i16::from(*byte - b'0'));
        let mut digit = i16::from(now_bytes[now_index] - b'0') - borrow - prior_digit;
        if digit < 0 {
            digit += 10;
            borrow = 1;
        } else {
            borrow = 0;
        }
        let encoded_digit = match digit {
            0 => b'0',
            1 => b'1',
            2 => b'2',
            3 => b'3',
            4 => b'4',
            5 => b'5',
            6 => b'6',
            7 => b'7',
            8 => b'8',
            9 => b'9',
            _ => return false,
        };
        difference.push(encoded_digit);
    }
    while difference.len() > 1 && difference.last() == Some(&b'0') {
        difference.pop();
    }
    match difference.len() {
        0 => true,
        1 => difference[0] - b'0' <= WINDOW_SECONDS,
        2 => (difference[1] - b'0') * 10 + (difference[0] - b'0') <= WINDOW_SECONDS,
        _ => false,
    }
}

fn parse_state_row(raw: &str) -> Option<StateRow> {
    let fields: Vec<&str> = raw.trim_end_matches('\n').split('\t').collect();
    if fields.len() != 4 {
        return None;
    }
    Some(StateRow {
        path_hash: fields[0].to_owned(),
        offset: fields[1].to_owned(),
        count: normalize_decimal(fields[2])?,
        epoch: normalize_decimal(fields[3])?,
    })
}

fn count_for(event: &ReadEvent, prior: Option<&StateRow>, event_path_hash: &str) -> String {
    let Some(prior) = prior else {
        return "1".to_owned();
    };
    if prior.path_hash == event_path_hash
        && prior.offset == event.offset
        && elapsed_is_in_window(&event.now, &prior.epoch)
    {
        increment_decimal(&prior.count)
    } else {
        "1".to_owned()
    }
}

fn emit_reminder() {
    let _ = writeln!(
        io::stdout().lock(),
        "{{\"hookSpecificOutput\":{{\"additionalContext\":\"{REMINDER_TEXT}\",\"hookEventName\":\"PostToolUse\"}}}}"
    );
}

#[cfg(unix)]
fn state_parent() -> Option<PathBuf> {
    let path = env::var_os("TMPDIR")
        .filter(|value| !value.is_empty())
        .map_or_else(|| PathBuf::from(TMP_FALLBACK), PathBuf::from);
    path.is_absolute().then_some(path)
}

#[cfg(unix)]
fn process_event(event: &ReadEvent) -> Result<String, ()> {
    let root = state_parent().ok_or(())?;
    let discriminator = env::var("HOOK_ANTI_READ_POLL_DISCRIMINATOR").ok();
    process_event_at(event, &root, discriminator.as_deref())
}

#[cfg(unix)]
fn process_event_at(
    event: &ReadEvent,
    temporary_root: &Path,
    discriminator: Option<&str>,
) -> Result<String, ()> {
    let state = StateDirectory::open(temporary_root)?;
    let name = state_basename(&event.cwd, &session_key(event, discriminator));
    let _lock = state.lock(&name)?;
    state.verify_current()?;
    let previous = read_state_row(&state, &name)?;
    let digest = path_hash(&event.file_path);
    let count = count_for(event, previous.as_ref(), &digest);
    let row = StateRow {
        path_hash: digest,
        offset: event.offset.clone(),
        count: count.clone(),
        epoch: event.now.clone(),
    };
    write_state_row(&state, &name, &row)?;
    Ok(count)
}

#[cfg(unix)]
struct StateDirectory {
    parent: OwnedFd,
    directory: OwnedFd,
}

#[cfg(unix)]
impl StateDirectory {
    fn open(temporary_root: &Path) -> Result<Self, ()> {
        let parent = open(
            temporary_root,
            OFlag::O_RDONLY | OFlag::O_DIRECTORY | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
            Mode::empty(),
        )
        .map_err(|_| ())?;
        if entry_kind(&fstat(&parent).map_err(|_| ())?) != SFlag::S_IFDIR {
            return Err(());
        }
        match mkdirat(&parent, STATE_DIR_NAME, STATE_DIRECTORY_MODE) {
            Ok(()) | Err(Errno::EEXIST) => {}
            Err(_) => return Err(()),
        }
        let directory = openat(
            &parent,
            STATE_DIR_NAME,
            OFlag::O_RDONLY | OFlag::O_DIRECTORY | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
            Mode::empty(),
        )
        .map_err(|_| ())?;
        let state = Self { parent, directory };
        state.verify_current()?;
        fchmod(&state.directory, STATE_DIRECTORY_MODE).map_err(|_| ())?;
        state.verify_current()?;
        Ok(state)
    }

    fn verify_current(&self) -> Result<(), ()> {
        let opened = fstat(&self.directory).map_err(|_| ())?;
        let visible =
            fstatat(&self.parent, STATE_DIR_NAME, AtFlags::AT_SYMLINK_NOFOLLOW).map_err(|_| ())?;
        if entry_kind(&opened) != SFlag::S_IFDIR
            || entry_kind(&visible) != SFlag::S_IFDIR
            || !same_file(&opened, &visible)
        {
            return Err(());
        }
        Ok(())
    }

    fn lock(&self, state_name: &str) -> Result<OwnedFd, ()> {
        self.verify_current()?;
        let lock_name = format!(".{state_name}.lock");
        match fstatat(
            &self.directory,
            lock_name.as_str(),
            AtFlags::AT_SYMLINK_NOFOLLOW,
        ) {
            Ok(stat) if is_single_link_regular(&stat) => {}
            Err(Errno::ENOENT) => {}
            Ok(_) | Err(_) => return Err(()),
        }
        let lock = openat(
            &self.directory,
            lock_name.as_str(),
            OFlag::O_RDWR
                | OFlag::O_CREAT
                | OFlag::O_NOFOLLOW
                | OFlag::O_NONBLOCK
                | OFlag::O_CLOEXEC,
            STATE_FILE_MODE,
        )
        .map_err(|_| ())?;
        let opened = fstat(&lock).map_err(|_| ())?;
        let visible = fstatat(
            &self.directory,
            lock_name.as_str(),
            AtFlags::AT_SYMLINK_NOFOLLOW,
        )
        .map_err(|_| ())?;
        if !is_single_link_regular(&opened)
            || !is_single_link_regular(&visible)
            || !same_file(&opened, &visible)
        {
            return Err(());
        }
        fchmod(&lock, STATE_FILE_MODE).map_err(|_| ())?;
        assert_current_regular_entry(self, lock_name.as_str(), &opened)?;
        let deadline = Instant::now() + LOCK_WAIT;
        loop {
            #[allow(deprecated)] // `flock` is the portable BSD/Linux advisory lock primitive.
            match flock(lock.as_raw_fd(), FlockArg::LockExclusiveNonblock) {
                Ok(()) => {
                    assert_current_regular_entry(self, lock_name.as_str(), &opened)?;
                    self.verify_current()?;
                    return Ok(lock);
                }
                Err(error) if error == Errno::EWOULDBLOCK || error == Errno::EAGAIN => {
                    if Instant::now() >= deadline {
                        return Err(());
                    }
                    thread::yield_now();
                }
                Err(_) => return Err(()),
            }
        }
    }
}

#[cfg(unix)]
const fn entry_kind(stat: &nix::sys::stat::FileStat) -> SFlag {
    let raw_mode = stat.st_mode;
    SFlag::from_bits_truncate(raw_mode)
}

#[cfg(unix)]
fn same_file(left: &nix::sys::stat::FileStat, right: &nix::sys::stat::FileStat) -> bool {
    (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)
}

#[cfg(unix)]
fn is_single_link_regular(stat: &nix::sys::stat::FileStat) -> bool {
    stat.st_nlink == 1 && entry_kind(stat) == SFlag::S_IFREG
}

#[cfg(unix)]
fn assert_current_regular_entry(
    state: &StateDirectory,
    name: &str,
    expected: &nix::sys::stat::FileStat,
) -> Result<(), ()> {
    let current = fstatat(&state.directory, name, AtFlags::AT_SYMLINK_NOFOLLOW).map_err(|_| ())?;
    if !is_single_link_regular(&current) || !same_file(expected, &current) {
        return Err(());
    }
    Ok(())
}

#[cfg(unix)]
fn read_state_row(state: &StateDirectory, name: &str) -> Result<Option<StateRow>, ()> {
    state.verify_current()?;
    let visible = match fstatat(&state.directory, name, AtFlags::AT_SYMLINK_NOFOLLOW) {
        Ok(stat) => stat,
        Err(Errno::ENOENT) => return Ok(None),
        Err(_) => return Err(()),
    };
    if entry_kind(&visible) == SFlag::S_IFLNK {
        unlinkat(&state.directory, name, UnlinkatFlags::NoRemoveDir).map_err(|_| ())?;
        return Ok(None);
    }
    if entry_kind(&visible) != SFlag::S_IFREG {
        return Err(());
    }
    let descriptor = openat(
        &state.directory,
        name,
        OFlag::O_RDONLY | OFlag::O_NOFOLLOW | OFlag::O_NONBLOCK | OFlag::O_CLOEXEC,
        Mode::empty(),
    )
    .map_err(|_| ())?;
    let opened = fstat(&descriptor).map_err(|_| ())?;
    let current = fstatat(&state.directory, name, AtFlags::AT_SYMLINK_NOFOLLOW).map_err(|_| ())?;
    if entry_kind(&opened) != SFlag::S_IFREG
        || entry_kind(&current) != SFlag::S_IFREG
        || !same_file(&opened, &current)
    {
        return Err(());
    }
    let mut bytes = Vec::new();
    File::from(descriptor)
        .take(MAX_STATE_BYTES)
        .read_to_end(&mut bytes)
        .map_err(|_| ())?;
    let raw = String::from_utf8(bytes).map_err(|_| ())?;
    Ok(parse_state_row(&raw))
}

#[cfg(unix)]
fn write_state_row(state: &StateDirectory, name: &str, row: &StateRow) -> Result<(), ()> {
    state.verify_current()?;
    let (temporary_name, descriptor) = create_temp_file(state, name)?;
    let result = (|| {
        let opened = fstat(&descriptor).map_err(|_| ())?;
        if !is_single_link_regular(&opened) {
            return Err(());
        }
        let text = format!(
            "{}\t{}\t{}\t{}\n",
            row.path_hash, row.offset, row.count, row.epoch
        );
        let mut temporary = File::from(descriptor);
        temporary.write_all(text.as_bytes()).map_err(|_| ())?;
        temporary.flush().map_err(|_| ())?;
        fchmod(&temporary, STATE_FILE_MODE).map_err(|_| ())?;
        temporary.sync_all().map_err(|_| ())?;
        drop(temporary);

        state.verify_current()?;
        assert_current_regular_entry(state, temporary_name.as_str(), &opened)?;
        assert_or_unlink_replaceable_destination(state, name)?;
        state.verify_current()?;
        assert_current_regular_entry(state, temporary_name.as_str(), &opened)?;
        renameat(
            &state.directory,
            temporary_name.as_str(),
            &state.directory,
            name,
        )
        .map_err(|_| ())?;
        state.verify_current()?;
        assert_current_regular_entry(state, name, &opened)
    })();
    if result.is_err() {
        let _ = unlinkat(
            &state.directory,
            temporary_name.as_str(),
            UnlinkatFlags::NoRemoveDir,
        );
    }
    result
}

#[cfg(unix)]
fn create_temp_file(state: &StateDirectory, name: &str) -> Result<(String, OwnedFd), ()> {
    for _ in 0..TEMP_ATTEMPTS {
        let temporary_name = format!(".{name}.tmp.{}", Uuid::new_v4().simple());
        match openat(
            &state.directory,
            temporary_name.as_str(),
            OFlag::O_WRONLY | OFlag::O_CREAT | OFlag::O_EXCL | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
            STATE_FILE_MODE,
        ) {
            Ok(descriptor) => {
                let opened = fstat(&descriptor).map_err(|_| ())?;
                if !is_single_link_regular(&opened) {
                    return Err(());
                }
                return Ok((temporary_name, descriptor));
            }
            Err(Errno::EEXIST) => {}
            Err(_) => return Err(()),
        }
    }
    Err(())
}

#[cfg(unix)]
fn assert_or_unlink_replaceable_destination(state: &StateDirectory, name: &str) -> Result<(), ()> {
    match fstatat(&state.directory, name, AtFlags::AT_SYMLINK_NOFOLLOW) {
        Err(Errno::ENOENT) => Ok(()),
        Ok(stat) if entry_kind(&stat) == SFlag::S_IFLNK => {
            unlinkat(&state.directory, name, UnlinkatFlags::NoRemoveDir).map_err(|_| ())
        }
        Ok(stat) if is_single_link_regular(&stat) => Ok(()),
        Err(_) | Ok(_) => Err(()),
    }
}

#[cfg(test)]
mod tests {
    use super::{
        ACTIVATION_TTL, AUDIT_LOG_RELATIVE, BACKGROUND_CWD_REASON, BACKGROUND_MALFORMED_REASON,
        BACKGROUND_PARSE_REASON, BACKGROUND_REGISTRY_REASON, BLOCK_ABSOLUTE_REASON,
        BLOCK_PARSE_REASON, CLEANUP_LOG_PREFIX, DENY_EDIT_WRITE_REASON, HookContext, REMINDER_TEXT,
        ReadEvent, SESSIONSTART_DIRTY, SESSIONSTART_GIT_MISSING, SESSIONSTART_INTERRUPTED,
        SESSIONSTART_JQ_GIT_FALLBACK, SESSIONSTART_JQ_ONLY_FALLBACK, SESSIONSTART_SPARSE_DRIFT,
        SESSIONSTART_STASH, SESSIONSTART_UNMERGED, STATE_DIR_NAME, StateDirectory, StateRow,
        activation_is_live, active_edit_reason, append_audit_input, block_submodule_reason,
        count_for, deny_envelope, deny_run_in_background_reason, elapsed_is_in_window,
        health_advisories, hook_context, implement_session_dir_exists, increment_decimal,
        launch_cleanup_sessionstart, marketplace_sparse_cone_drift, normalize_decimal,
        parse_payload, parse_state_row, path_hash, pending_review_boundary, process_event_at,
        reflog_contains_larch, repository_health_advisories, review_boundary_advisory,
        sessionstart_envelope, sparse_checkout_dirs, stalled_run_advisory, state_basename,
        stop_envelope, stop_reason, write_state_row,
    };
    use larch_adapters::GixRepository;
    use larch_test_support::{GitFixture, GitRepository};
    #[cfg(unix)]
    use nix::{sys::stat::Mode, unistd::mkfifo};
    use serde_json::{Value, json};
    #[cfg(unix)]
    use std::os::unix::fs::PermissionsExt as _;
    use std::{
        fs,
        path::Path,
        sync::{Arc, Barrier},
        thread,
        time::{Duration, SystemTime},
    };
    use tempfile::TempDir;

    fn event(now: &str) -> ReadEvent {
        ReadEvent {
            cwd: "/project".to_owned(),
            file_path: "/project/private name.md".to_owned(),
            offset: "7".to_owned(),
            session_id: "session".to_owned(),
            conversation_id: String::new(),
            now: now.to_owned(),
        }
    }

    fn file_payload(path: &Path) -> Vec<u8> {
        serde_json::to_vec(&json!({"tool_input": {"file_path": path}})).expect("file payload")
    }

    fn background_payload(cwd: &Path, command: &str) -> Vec<u8> {
        serde_json::to_vec(&json!({
            "tool_name": "Bash",
            "cwd": cwd,
            "tool_input": {"command": command, "run_in_background": true},
        }))
        .expect("background payload")
    }

    #[cfg(unix)]
    #[test]
    fn submodule_guard_preserves_nested_repo_and_symlink_contracts() {
        use std::os::unix::fs::symlink;

        let repository = GitRepository::builder(GitFixture::Submodule)
            .build()
            .expect("submodule fixture");
        let root = repository.root();
        let submodule = root.join("submodule");

        assert!(
            block_submodule_reason(
                &file_payload(&root.join("tracked.txt")),
                Some(root),
                Some(root)
            )
            .is_none()
        );
        for target in [
            submodule.join("child.txt"),
            submodule.join("missing/parent/new.txt"),
        ] {
            let reason = block_submodule_reason(&file_payload(&target), Some(root), Some(root))
                .expect("submodule deny");
            assert!(reason.contains("'submodule' submodule"), "{reason}");
        }
        let reason = block_submodule_reason(
            &file_payload(&submodule.join("child.txt")),
            Some(&root.join("missing-project-dir")),
            Some(root),
        )
        .expect("cwd fallback deny");
        assert!(reason.contains("submodule"));
        let reason = block_submodule_reason(
            &file_payload(&submodule.join("child.txt")),
            Some(root),
            Some(&submodule),
        )
        .expect("project anchor deny");
        assert!(reason.contains("submodule"));

        let nested = root.join("nested");
        let output = repository
            .git([
                "init",
                "--quiet",
                nested.to_str().expect("UTF-8 fixture path"),
            ])
            .expect("initialize nested repository");
        assert!(
            output.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        fs::write(nested.join("file.txt"), "nested\n").expect("nested file");
        assert!(
            block_submodule_reason(
                &file_payload(&nested.join("file.txt")),
                Some(root),
                Some(root)
            )
            .is_none()
        );
        let outside = TempDir::new().expect("outside repository");
        assert!(
            block_submodule_reason(
                &file_payload(&outside.path().join("file.txt")),
                Some(root),
                Some(root),
            )
            .is_none()
        );

        symlink(root.join("tracked.txt"), root.join("super-link")).expect("superproject symlink");
        symlink(
            submodule.join("child.txt"),
            root.join("absolute-submodule-link"),
        )
        .expect("absolute submodule symlink");
        symlink("submodule/child.txt", root.join("relative-submodule-link"))
            .expect("relative submodule symlink");
        symlink("cycle-link", root.join("cycle-link")).expect("cycle symlink");
        assert!(
            block_submodule_reason(
                &file_payload(&root.join("super-link")),
                Some(root),
                Some(root)
            )
            .is_none()
        );
        for link in ["absolute-submodule-link", "relative-submodule-link"] {
            let reason =
                block_submodule_reason(&file_payload(&root.join(link)), Some(root), Some(root))
                    .expect("symlink into submodule denied");
            assert!(reason.contains("submodule"), "{reason}");
        }
        let cycle = block_submodule_reason(
            &file_payload(&root.join("cycle-link")),
            Some(root),
            Some(root),
        )
        .expect("cycle denied");
        assert!(cycle.contains("symlink"), "{cycle}");
    }

    #[test]
    fn submodule_guard_fails_closed_only_for_ambiguous_input() {
        let temporary = TempDir::new().expect("temporary root");
        assert_eq!(
            block_submodule_reason(b"not json", Some(temporary.path()), Some(temporary.path())),
            Some(BLOCK_PARSE_REASON.to_owned())
        );
        assert_eq!(
            block_submodule_reason(
                br#"{"tool_input":{"file_path":"relative.txt"}}"#,
                Some(temporary.path()),
                Some(temporary.path()),
            ),
            Some(BLOCK_ABSOLUTE_REASON.to_owned())
        );
        assert!(
            block_submodule_reason(
                &file_payload(&temporary.path().join("outside.txt")),
                None,
                Some(temporary.path()),
            )
            .is_none()
        );
        assert!(block_submodule_reason(br#"{"tool_input":{}}"#, None, None).is_none());
    }

    #[test]
    fn edit_activation_is_token_scoped_pid_agnostic_and_ttl_bounded() {
        let temporary = TempDir::new().expect("temporary cache");
        let activation = temporary.path().join("larch/deny-edit-write-active");
        fs::create_dir_all(&activation).expect("activation directory");
        let sentinel = activation.join("research-999999");
        fs::write(&sentinel, "").expect("activation sentinel");
        let modified = fs::metadata(&sentinel)
            .expect("sentinel metadata")
            .modified()
            .expect("sentinel mtime");
        assert!(activation_is_live("research", temporary.path(), modified));
        assert!(!activation_is_live("file-bug", temporary.path(), modified));
        assert!(!activation_is_live("", temporary.path(), modified));
        assert!(!activation_is_live("unknown", temporary.path(), modified));
        assert!(!activation_is_live(
            "research",
            temporary.path(),
            modified + ACTIVATION_TTL,
        ));

        for token in [
            "audit-umbrella",
            "file-bug",
            "complete-umbrella",
            "debate",
            "triage",
            "umbrella",
        ] {
            let path = activation.join(format!("{token}-1"));
            fs::write(&path, "").expect("token sentinel");
            let now = fs::metadata(&path)
                .expect("token metadata")
                .modified()
                .expect("token mtime");
            assert!(activation_is_live(token, temporary.path(), now), "{token}");
        }
        assert!(!activation_is_live(
            "research",
            &temporary.path().join("absent"),
            SystemTime::now(),
        ));
    }

    #[cfg(unix)]
    #[test]
    fn active_edit_guard_allows_only_canonical_scratch_roots() {
        use std::os::unix::fs::symlink;

        let cache = TempDir::new_in(env!("CARGO_MANIFEST_DIR")).expect("non-tmp cache root");
        let sessions = cache.path().join("larch/sessions");
        fs::create_dir_all(sessions.join("session-a")).expect("sessions root");
        let tmp = TempDir::new_in("/tmp").expect("/tmp scratch");
        let tmp_new = tmp.path().join("missing/leaf.txt");
        assert_eq!(
            active_edit_reason(&file_payload(&tmp_new), cache.path()),
            None
        );
        let tmp_existing = tmp.path().join("existing.txt");
        fs::write(&tmp_existing, "existing\n").expect("existing /tmp target");
        assert_eq!(
            active_edit_reason(&file_payload(&tmp_existing), cache.path()),
            None
        );
        assert_eq!(
            active_edit_reason(
                &serde_json::to_vec(&json!({
                    "tool_input": {"file_path": "", "notebook_path": tmp.path().join("new.ipynb")}
                }))
                .expect("notebook payload"),
                cache.path(),
            ),
            None
        );
        assert_eq!(
            active_edit_reason(
                &file_payload(&sessions.join("session-a/bodies/item.txt")),
                cache.path(),
            ),
            None
        );

        for payload in [
            file_payload(Path::new("relative.txt")),
            file_payload(Path::new("/tmp/../etc/passwd")),
            file_payload(&cache.path().join("larch/deny-edit-write-active/evil.txt")),
            file_payload(&cache.path().join("larch/sessions/../evil.txt")),
            b"not json".to_vec(),
            br#"{"tool_input":{}}"#.to_vec(),
        ] {
            assert_eq!(
                active_edit_reason(&payload, cache.path()),
                Some(DENY_EDIT_WRITE_REASON)
            );
        }

        let outside = cache.path().join("outside.txt");
        fs::write(&outside, "outside\n").expect("outside target");
        let link = tmp.path().join("outside-link");
        symlink(&outside, &link).expect("outside symlink");
        assert_eq!(
            active_edit_reason(&file_payload(&link), cache.path()),
            Some(DENY_EDIT_WRITE_REASON)
        );
        fs::remove_dir_all(&sessions).expect("remove sessions root");
        assert_eq!(
            active_edit_reason(
                &file_payload(&sessions.join("missing/session-body.txt")),
                cache.path(),
            ),
            Some(DENY_EDIT_WRITE_REASON)
        );
    }

    #[test]
    fn edit_deny_envelope_is_byte_stable() {
        assert_eq!(
            deny_envelope(DENY_EDIT_WRITE_REASON),
            r#"{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"The active skill is read-only-repo -- Edit/Write/NotebookEdit outside /tmp or the larch session cache is not permitted."}}"#
        );
    }

    #[test]
    fn background_guard_preserves_wait_carveout_and_registry_fail_closed_behavior() {
        let temporary = TempDir::new().expect("temporary root");
        let clone = temporary.path().join("clone");
        let registry = temporary.path().join("registry");
        fs::create_dir_all(&clone).expect("clone root");
        fs::create_dir_all(&registry).expect("registry root");
        let payload = background_payload(&clone, "sleep 1");
        assert_eq!(deny_run_in_background_reason(&payload, &registry), None);

        let row = registry.join("run-demo.env");
        fs::write(&row, format!("CLONE_PATH={}\n", clone.display())).expect("registry row");
        let reason = deny_run_in_background_reason(&payload, &registry).expect("active deny");
        assert!(reason.contains("active larch bgjob registry"), "{reason}");
        let fallback_gate = serde_json::to_vec(&json!({
            "tool_name": "Bash",
            "cwd": clone,
            "tool_input": {"command": "echo run_in_background=true"},
        }))
        .expect("fallback background payload");
        let reason = deny_run_in_background_reason(&fallback_gate, &registry)
            .expect("command-string background gate deny");
        assert!(reason.contains("active larch bgjob registry"), "{reason}");

        let wait = background_payload(
            &clone,
            "${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh bgjob wait --step leaf --tmpdir /tmp/x --max-wait-s 7200",
        );
        assert_eq!(deny_run_in_background_reason(&wait, &registry), None);
        let multiline_wait = background_payload(
            &clone,
            "\"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh\" bgjob wait \\\n  --step leaf \\\n  --tmpdir /tmp/x \\\n  --max-wait-s 7200",
        );
        assert_eq!(
            deny_run_in_background_reason(&multiline_wait, &registry),
            None
        );
        for command in [
            "/tmp/decoy/larch.sh bgjob wait --step leaf --tmpdir /tmp/x --max-wait-s 7200",
            "/tmp/decoy/scripts/larch.sh bgjob wait --step leaf --tmpdir /tmp/x --max-wait-s 7200",
            "sleep 1 && ${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh bgjob wait --step leaf --tmpdir /tmp/x --max-wait-s 7200",
        ] {
            let reason =
                deny_run_in_background_reason(&background_payload(&clone, command), &registry)
                    .expect("unsafe wait denied");
            assert!(reason.contains("active larch bgjob registry"), "{reason}");
        }

        assert_eq!(
            deny_run_in_background_reason(b"not json", &registry).as_deref(),
            Some(BACKGROUND_MALFORMED_REASON)
        );
        assert_eq!(
            deny_run_in_background_reason(
                br#"{"tool_name":"Bash","tool_input":{"run_in_background":true}}"#,
                &registry,
            )
            .as_deref(),
            Some(BACKGROUND_CWD_REASON)
        );
        assert_eq!(
            deny_run_in_background_reason(
                br#"{"tool_name":"Read","tool_input":{"run_in_background":true}}"#,
                &registry,
            ),
            None
        );
        assert_eq!(
            deny_run_in_background_reason(br#"{"tool_name":"Bash","tool_input":true}"#, &registry,)
                .as_deref(),
            Some(BACKGROUND_PARSE_REASON)
        );
        fs::write(&row, "not-kv\r\n").expect("malformed registry row");
        assert_eq!(
            deny_run_in_background_reason(&payload, &registry).as_deref(),
            Some(BACKGROUND_REGISTRY_REASON)
        );
    }

    #[test]
    fn sessionstart_and_stop_envelopes_keep_their_visible_bytes() {
        assert_eq!(
            SESSIONSTART_JQ_ONLY_FALLBACK,
            r#"{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"larch hook preflight: jq not on PATH (install jq for advisory hook output)."}}"#
        );
        assert_eq!(
            SESSIONSTART_JQ_GIT_FALLBACK,
            r#"{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"larch hook preflight: jq not on PATH and git not on PATH; install jq and git for advisory hook output."}}"#
        );
        assert_eq!(
            SESSIONSTART_GIT_MISSING,
            "larch hook preflight: git not on PATH. The submodule-edit guard and most larch scripts depend on git."
        );
        assert_eq!(
            SESSIONSTART_SPARSE_DRIFT,
            "larch hook preflight: larch-local marketplace sparse checkout is out of date; run /upgrade-larch to repair it."
        );
        assert_eq!(
            SESSIONSTART_DIRTY,
            "larch hook preflight: working tree has uncommitted changes; the next /implement will fail preflight or inherit them."
        );
        assert_eq!(
            SESSIONSTART_STASH,
            "larch hook preflight: leftover larch-managed stash detected (run 'git stash list | grep larch-' to inspect)."
        );
        assert_eq!(
            SESSIONSTART_INTERRUPTED,
            "larch hook preflight: interrupted rebase/merge/cherry-pick state on disk."
        );
        assert_eq!(
            SESSIONSTART_UNMERGED,
            "larch hook preflight: local feature branch(es) not merged into main; consider deleting or pushing."
        );
        assert_eq!(
            review_boundary_advisory("claude-implement-demo"),
            "larch hook preflight: pending post-/review boundary in active /implement tmpdir (claude-implement-demo); NEXT REQUIRED: execute Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order per skills/implement/SKILL.md Step 5, then touch .review-boundary-passed."
        );
        assert_eq!(
            sessionstart_envelope("first advisory. second advisory."),
            concat!(
                "{\n",
                "  \"hookSpecificOutput\": {\n",
                "    \"hookEventName\": \"SessionStart\",\n",
                "    \"additionalContext\": \"first advisory. second advisory.\"\n",
                "  }\n",
                "}"
            )
        );
        assert_eq!(
            health_advisories(b"not-json", false, None, None),
            vec![SESSIONSTART_GIT_MISSING.to_owned()]
        );

        let reason = stop_reason("claude-implement-demo");
        assert_eq!(
            reason,
            "You halted mid-Step-5 (post-/review boundary).\n\nNEXT REQUIRED: execute the Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order per skills/implement/SKILL.md Step 5 post-/review directives, then touch .review-boundary-passed inside the active /implement tmpdir (claude-implement-demo) to release this guard.\n\nOperator escape: hard-quit the session, OR touch .run-cleaned-up inside the active /implement tmpdir to intentionally abandon the run."
        );
        assert_eq!(
            stop_envelope(&reason),
            r#"{"decision":"block","reason":"You halted mid-Step-5 (post-/review boundary).\n\nNEXT REQUIRED: execute the Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order per skills/implement/SKILL.md Step 5 post-/review directives, then touch .review-boundary-passed inside the active /implement tmpdir (claude-implement-demo) to release this guard.\n\nOperator escape: hard-quit the session, OR touch .run-cleaned-up inside the active /implement tmpdir to intentionally abandon the run."}"#
        );
    }

    #[test]
    fn hook_context_and_review_boundary_fail_open_and_release_cleanly() {
        assert_eq!(hook_context(b"not-json"), HookContext::default());
        assert_eq!(
            hook_context(br#"{"cwd":"/clone","session_id":"session-a","stop_hook_active":true}"#),
            HookContext {
                cwd: "/clone".to_owned(),
                session_id: "session-a".to_owned(),
                stop_hook_active: true,
            }
        );
        assert_eq!(
            hook_context(br#"{"cwd":"/clone","session_id":null}"#).session_id,
            ""
        );

        let temporary = TempDir::new().expect("temporary root");
        let implementation = temporary.path().join("claude-implement-demo");
        fs::create_dir(&implementation).expect("implementation directory");
        assert_eq!(pending_review_boundary(&implementation), None);
        fs::write(implementation.join("review-round-summary.md"), "review\n")
            .expect("review summary");
        assert_eq!(
            pending_review_boundary(&implementation).as_deref(),
            Some("claude-implement-demo")
        );
        fs::write(implementation.join(".review-boundary-passed"), "").expect("boundary sentinel");
        assert_eq!(pending_review_boundary(&implementation), None);
        fs::remove_file(implementation.join(".review-boundary-passed"))
            .expect("remove boundary sentinel");
        fs::write(implementation.join(".run-cleaned-up"), "").expect("cleanup sentinel");
        assert_eq!(pending_review_boundary(&implementation), None);

        let roots = [temporary.path().to_path_buf()];
        assert!(implement_session_dir_exists(&roots, "/clone"));
        assert!(!implement_session_dir_exists(&roots, ""));
    }

    #[test]
    fn sessionstart_repository_probes_cover_dirty_stash_and_interrupted_state() {
        let dirty = GitRepository::builder(GitFixture::Changes)
            .build()
            .expect("changes fixture");
        assert!(
            repository_health_advisories(dirty.root())
                .iter()
                .any(|message| message == SESSIONSTART_DIRTY)
        );

        let stash = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("stash fixture");
        fs::write(stash.root().join("tracked.txt"), "stash me\n").expect("stash change");
        let output = stash
            .git(["stash", "push", "-m", "larch-managed"])
            .expect("create stash");
        assert!(
            output.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            repository_health_advisories(stash.root())
                .iter()
                .any(|message| message == SESSIONSTART_STASH)
        );

        let ordinary_stash = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("ordinary stash fixture");
        fs::write(ordinary_stash.root().join("tracked.txt"), "stash me\n")
            .expect("ordinary stash change");
        let output = ordinary_stash
            .git(["stash", "push", "-m", "operator-work"])
            .expect("create ordinary stash");
        assert!(
            output.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            !repository_health_advisories(ordinary_stash.root())
                .iter()
                .any(|message| message == SESSIONSTART_STASH)
        );

        let interrupted = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("interrupted fixture");
        fs::write(interrupted.root().join(".git/MERGE_HEAD"), "pending\n").expect("merge marker");
        assert!(
            repository_health_advisories(interrupted.root())
                .iter()
                .any(|message| message == SESSIONSTART_INTERRUPTED)
        );

        let reflog = interrupted.root().join("identity-only-stash-log");
        fs::write(
            &reflog,
            "old new Larch <larch-owner@example.invalid> 1 +0000\tOn main: operator work\n",
        )
        .expect("identity-only reflog");
        assert!(!reflog_contains_larch(&reflog));
        fs::write(
            &reflog,
            "old new Operator <operator@example.invalid> 1 +0000\tOn main: larch-managed\n",
        )
        .expect("larch-message reflog");
        assert!(reflog_contains_larch(&reflog));
    }

    #[test]
    fn sessionstart_repository_probes_cover_unmerged_branches_and_stall_sentinel() {
        let repository = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("refs fixture");
        for arguments in [
            vec!["checkout", "--quiet", "topic"],
            vec!["commit", "--quiet", "--allow-empty", "-m", "topic work"],
            vec!["checkout", "--quiet", "main"],
        ] {
            let output = repository.git(arguments).expect("git fixture command");
            assert!(
                output.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
        }
        let advisories = repository_health_advisories(repository.root());
        assert!(
            advisories
                .iter()
                .any(|message| message == SESSIONSTART_UNMERGED)
        );

        fs::write(
            repository.root().join(".git/larch-stalled-run.txt"),
            "ISSUE_NUMBER=77\nSTALL_STEP=12d\nSTASH_REF=stash@{0}\n",
        )
        .expect("stall sentinel");
        assert_eq!(
            stalled_run_advisory(&repository.root().join(".git")).as_deref(),
            Some(
                "larch hook preflight: a prior /implement run for #77 stalled at step 12d. Working-tree edits stashed as stash@{0}. Resume via 'git stash apply stash@{0}' or drop via 'git stash drop stash@{0}'."
            )
        );
        fs::write(
            repository.root().join(".git/larch-stalled-run.txt"),
            "ISSUE_NUMBER=88\nSTALL_STEP=8b\nSTASH_REF=\n",
        )
        .expect("clean stall sentinel");
        let advisory =
            stalled_run_advisory(&repository.root().join(".git")).expect("clean stall advisory");
        assert!(advisory.contains("No working-tree edits were stashed"));
        assert!(!advisory.contains("git stash apply"));

        let no_main = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("no-main fixture");
        let output = no_main
            .git(["branch", "-m", "master"])
            .expect("rename main");
        assert!(
            output.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            !repository_health_advisories(no_main.root())
                .iter()
                .any(|message| message == SESSIONSTART_UNMERGED)
        );
    }

    #[test]
    fn sessionstart_sparse_checkout_probe_reads_the_configured_cone() {
        let repository = GitRepository::builder(GitFixture::SparseCheckout)
            .build()
            .expect("sparse fixture");
        let repository = GixRepository::open(repository.root()).expect("open sparse fixture");
        assert_eq!(
            sparse_checkout_dirs(&repository),
            Some(vec!["keep".to_owned()])
        );

        let ordinary = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("ordinary fixture");
        let ordinary = GixRepository::open(ordinary.root()).expect("open ordinary fixture");
        assert_eq!(sparse_checkout_dirs(&ordinary), None);
    }

    #[cfg(unix)]
    #[test]
    fn sessionstart_sparse_checkout_probe_preserves_skip_and_drift_cases() {
        use std::os::unix::fs::symlink;

        let home = TempDir::new().expect("home");
        assert!(!marketplace_sparse_cone_drift(Some(home.path())));
        let marketplace = home.path().join(".claude/plugins/marketplaces/larch-local");
        fs::create_dir_all(marketplace.parent().expect("marketplace parent"))
            .expect("marketplace parent");
        fs::create_dir(&marketplace).expect("non-git marketplace");
        assert!(!marketplace_sparse_cone_drift(Some(home.path())));
        fs::remove_dir(&marketplace).expect("remove non-git marketplace");

        let repository = GitRepository::builder(GitFixture::SparseCheckout)
            .build()
            .expect("sparse fixture");
        symlink(repository.root(), &marketplace).expect("marketplace clone link");
        assert!(marketplace_sparse_cone_drift(Some(home.path())));

        fs::write(
            repository.root().join(".git/info/sparse-checkout"),
            "/*\n!/*/\n/.claude-plugin/\n",
        )
        .expect("matching sparse cone");
        assert!(!marketplace_sparse_cone_drift(Some(home.path())));

        fs::write(
            repository.root().join(".git/info/sparse-checkout"),
            "/*\n!/*/\n",
        )
        .expect("empty sparse cone");
        assert!(!marketplace_sparse_cone_drift(Some(home.path())));

        fs::create_dir(repository.root().join("larch-logs")).expect("legacy marketplace marker");
        fs::write(
            repository.root().join(".git/info/sparse-checkout"),
            "/*\n!/*/\n/other/\n",
        )
        .expect("drifted legacy cone");
        assert!(!marketplace_sparse_cone_drift(Some(home.path())));
    }

    #[test]
    fn audit_hook_appends_objects_and_skips_invalid_input() {
        let project = TempDir::new().expect("project root");
        append_audit_input(
            project.path(),
            br#"{"tool_name":"Edit","tool_input":{"file_path":"/tmp/a"}}"#,
            "2026-08-25T12:34:56Z",
        )
        .expect("append Edit row");
        append_audit_input(
            project.path(),
            br#"{"tool_name":"Write","tool_input":{"file_path":"/tmp/b"}}"#,
            "2026-08-25T12:34:57Z",
        )
        .expect("append Write row");
        let log = project.path().join(".claude/hook-audit.log");
        let rows: Vec<Value> = fs::read_to_string(&log)
            .expect("audit log")
            .lines()
            .map(|line| serde_json::from_str(line).expect("audit JSON row"))
            .collect();
        assert_eq!(rows.len(), 2);
        assert_eq!(rows[0]["ts"], "2026-08-25T12:34:56Z");
        assert_eq!(rows[0]["event"], "PostToolUse");
        assert_eq!(rows[0]["payload"]["tool_name"], "Edit");
        assert_eq!(rows[1]["payload"]["tool_name"], "Write");

        for invalid in [b"".as_slice(), b"not-json", br#"["not", "object"]"#] {
            assert!(append_audit_input(project.path(), invalid, "ignored").is_err());
        }
        assert_eq!(
            fs::read_to_string(log)
                .expect("unchanged audit log")
                .lines()
                .count(),
            2
        );
    }

    #[cfg(unix)]
    #[test]
    fn audit_hook_refuses_symlinked_and_non_regular_targets() {
        use std::os::unix::fs::symlink;

        let project = TempDir::new().expect("project root");
        let outside = TempDir::new().expect("outside root");
        symlink(outside.path(), project.path().join(".claude")).expect("symlink audit directory");
        assert!(append_audit_input(project.path(), br#"{"tool_name":"Edit"}"#, "ignored").is_err());
        assert!(!outside.path().join("hook-audit.log").exists());

        fs::remove_file(project.path().join(".claude")).expect("remove directory symlink");
        fs::create_dir(project.path().join(".claude")).expect("audit directory");
        let outside_log = outside.path().join("captured.jsonl");
        fs::write(&outside_log, "unchanged\n").expect("outside log");
        symlink(&outside_log, project.path().join(AUDIT_LOG_RELATIVE)).expect("symlink audit log");
        assert!(
            append_audit_input(project.path(), br#"{"tool_name":"Write"}"#, "ignored").is_err()
        );
        assert_eq!(
            fs::read_to_string(&outside_log).expect("unchanged outside log"),
            "unchanged\n"
        );

        fs::remove_file(project.path().join(AUDIT_LOG_RELATIVE)).expect("remove log symlink");
        fs::hard_link(&outside_log, project.path().join(AUDIT_LOG_RELATIVE))
            .expect("hard-linked audit log");
        assert!(append_audit_input(project.path(), br#"{"tool_name":"Edit"}"#, "ignored").is_err());
        assert_eq!(
            fs::read_to_string(&outside_log).expect("unchanged hard-linked log"),
            "unchanged\n"
        );

        fs::remove_file(project.path().join(AUDIT_LOG_RELATIVE)).expect("remove hard link");
        fs::create_dir(project.path().join(AUDIT_LOG_RELATIVE)).expect("directory at log path");
        assert!(append_audit_input(project.path(), br#"{"tool_name":"Edit"}"#, "ignored").is_err());
    }

    #[cfg(unix)]
    #[test]
    fn cleanup_sessionstart_reaps_before_detached_cleanup() {
        let temporary = TempDir::new().expect("temporary root");
        let scripts = temporary.path().join("scripts");
        fs::create_dir(&scripts).expect("scripts directory");
        let calls = temporary.path().join("calls.txt");
        let entrypoint = scripts.join("larch.sh");
        fs::write(
            &entrypoint,
            format!(
                "#!/bin/sh\nprintf '%s\\t%s\\n' \"$*\" \"${{LARCH_BOOTSTRAP_NO_INSTALL:-}}\" >> '{}'\n",
                calls.display()
            ),
        )
        .expect("stub entrypoint");
        fs::set_permissions(&entrypoint, fs::Permissions::from_mode(0o755))
            .expect("executable entrypoint");

        launch_cleanup_sessionstart(temporary.path(), temporary.path());
        let deadline = std::time::Instant::now() + Duration::from_secs(2);
        loop {
            let lines = fs::read_to_string(&calls).unwrap_or_default();
            if lines.lines().count() >= 2 || std::time::Instant::now() >= deadline {
                assert_eq!(lines, "bgjob reap\t1\ncleanup run\t1\n");
                break;
            }
            thread::sleep(Duration::from_millis(10));
        }
        assert!(
            temporary
                .path()
                .join(format!("{CLEANUP_LOG_PREFIX}-{}.log", std::process::id()))
                .is_file()
        );
        assert_eq!(
            fs::metadata(
                temporary
                    .path()
                    .join(format!("{CLEANUP_LOG_PREFIX}-{}.log", std::process::id()))
            )
            .expect("cleanup log metadata")
            .permissions()
            .mode()
                & 0o777,
            0o600
        );
    }

    #[test]
    fn parses_only_complete_read_events() {
        let valid = json!({
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/example", "offset": -3},
            "cwd": "",
            "session_id": "session",
        });
        let parsed = parse_payload(&valid).expect("valid event");
        assert_eq!(parsed.cwd, "/");
        assert_eq!(parsed.offset, "-3");
        assert!(parse_payload(&json!({"tool_name": "Bash"})).is_none());
        assert!(parse_payload(&json!({"tool_name": "Read", "tool_input": {}})).is_none());
        let decimal_offset = json!({
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/example", "offset": 1.5},
        });
        assert_eq!(parse_payload(&decimal_offset).expect("event").offset, "0");
    }

    #[test]
    fn decimal_helpers_keep_large_python_compatible_values() {
        assert_eq!(increment_decimal("999"), "1000");
        assert!(normalize_decimal("not-a-time").is_none());
        assert!(elapsed_is_in_window("100", "70"));
        assert!(!elapsed_is_in_window("101", "70"));
        assert!(elapsed_is_in_window(
            "100000000000000000000",
            "99999999999999999999"
        ));
        assert!(!elapsed_is_in_window("9", "10"));
        let prior = parse_state_row("digest\t7\t0002\t00070\n").expect("row");
        let current = event("100");
        assert_eq!(count_for(&current, Some(&prior), "digest"), "3");
    }

    #[cfg(unix)]
    #[test]
    fn counts_reads_and_persists_only_hashed_paths() {
        let temporary = TempDir::new().expect("temporary root");
        for now in ["100", "101", "102", "103"] {
            let count = process_event_at(&event(now), temporary.path(), None).expect("event");
            assert_eq!(count, (now.parse::<u8>().expect("time") - 99).to_string());
        }
        let name = state_basename("/project", "session");
        assert!(!name.contains("/project"));
        assert!(!name.contains("session"));
        let row = fs::read_to_string(temporary.path().join(STATE_DIR_NAME).join(&name))
            .expect("state row");
        assert_eq!(
            row,
            format!("{}\t7\t4\t103\n", path_hash("/project/private name.md"))
        );
        assert!(!row.contains("/project/private name.md"));
        let state_directory = temporary.path().join(STATE_DIR_NAME);
        assert_eq!(
            fs::metadata(&state_directory)
                .expect("state directory metadata")
                .permissions()
                .mode()
                & 0o777,
            0o700
        );
        assert_eq!(
            fs::metadata(state_directory.join(name))
                .expect("state file metadata")
                .permissions()
                .mode()
                & 0o777,
            0o600
        );
    }

    #[cfg(unix)]
    #[test]
    fn separates_sessions_and_resets_stale_or_malformed_rows() {
        let temporary = TempDir::new().expect("temporary root");
        let first = event("100");
        let second_session = ReadEvent {
            session_id: "other".to_owned(),
            now: "101".to_owned(),
            ..first.clone()
        };
        assert_eq!(
            process_event_at(&first, temporary.path(), None),
            Ok("1".to_owned())
        );
        assert_eq!(
            process_event_at(&second_session, temporary.path(), None),
            Ok("1".to_owned())
        );
        let stale = ReadEvent {
            now: "131".to_owned(),
            ..first.clone()
        };
        assert_eq!(
            process_event_at(&stale, temporary.path(), None),
            Ok("1".to_owned())
        );
        let name = state_basename("/project", "session");
        fs::write(
            temporary.path().join(STATE_DIR_NAME).join(name),
            "malformed\n",
        )
        .expect("write malformed state");
        let current = ReadEvent {
            now: "132".to_owned(),
            ..first
        };
        assert_eq!(
            process_event_at(&current, temporary.path(), None),
            Ok("1".to_owned())
        );
    }

    #[cfg(unix)]
    #[test]
    fn state_directory_and_leaf_attacks_fail_open_or_replace_only_the_leaf() {
        let temporary = TempDir::new().expect("temporary root");
        let redirect = temporary.path().join("redirect");
        fs::create_dir(&redirect).expect("redirect");
        std::os::unix::fs::symlink(&redirect, temporary.path().join(STATE_DIR_NAME))
            .expect("state symlink");
        assert!(process_event_at(&event("100"), temporary.path(), None).is_err());
        assert!(
            fs::read_dir(&redirect)
                .expect("redirect entries")
                .next()
                .is_none()
        );

        fs::remove_file(temporary.path().join(STATE_DIR_NAME)).expect("remove state symlink");
        let state = temporary.path().join(STATE_DIR_NAME);
        fs::create_dir(&state).expect("state directory");
        let name = state_basename("/project", "session");
        let poison = temporary.path().join("poison");
        fs::write(&poison, "unchanged\n").expect("poison");
        std::os::unix::fs::symlink(&poison, state.join(&name)).expect("leaf symlink");
        assert_eq!(
            process_event_at(&event("101"), temporary.path(), None),
            Ok("1".to_owned())
        );
        assert_eq!(
            fs::read_to_string(&poison).expect("poison read"),
            "unchanged\n"
        );
        assert!(state.join(name).is_file());
    }

    #[cfg(unix)]
    #[test]
    fn rejects_non_regular_leaf_and_detects_directory_replacement() {
        let temporary = TempDir::new().expect("temporary root");
        let state = temporary.path().join(STATE_DIR_NAME);
        fs::create_dir(&state).expect("state directory");
        let name = state_basename("/project", "session");
        fs::create_dir(state.join(&name)).expect("nonregular leaf");
        assert!(process_event_at(&event("100"), temporary.path(), None).is_err());

        fs::remove_dir_all(state.join(&name)).expect("remove nonregular leaf");
        mkfifo(state.join(&name).as_path(), Mode::S_IRUSR).expect("fifo leaf");
        assert!(process_event_at(&event("100"), temporary.path(), None).is_err());
        fs::remove_file(state.join(&name)).expect("remove fifo leaf");
        let open_state = StateDirectory::open(temporary.path()).expect("open state");
        let moved = temporary.path().join("moved-state");
        fs::rename(&state, &moved).expect("move state");
        fs::create_dir(&state).expect("replacement state");
        assert!(open_state.verify_current().is_err());
        assert!(
            write_state_row(
                &open_state,
                &name,
                &StateRow {
                    path_hash: path_hash("/project/private name.md"),
                    offset: "7".to_owned(),
                    count: "1".to_owned(),
                    epoch: "101".to_owned(),
                },
            )
            .is_err()
        );
        assert!(
            fs::read_dir(&state)
                .expect("replacement entries")
                .next()
                .is_none()
        );
    }

    #[cfg(unix)]
    #[test]
    fn concurrent_updates_leave_one_complete_regular_row() {
        let temporary = Arc::new(TempDir::new().expect("temporary root"));
        let barrier = Arc::new(Barrier::new(9));
        let mut workers = Vec::new();
        for _ in 0..8 {
            let temporary = Arc::clone(&temporary);
            let barrier = Arc::clone(&barrier);
            workers.push(thread::spawn(move || {
                barrier.wait();
                process_event_at(&event("100"), temporary.path(), None)
            }));
        }
        barrier.wait();
        let results: Vec<_> = workers
            .into_iter()
            .map(|worker| worker.join().expect("worker did not panic"))
            .collect();
        // The hook may deliberately skip a contended advisory update rather
        // than block a Read event. Successful concurrent writers must still
        // leave one complete, parseable state row.
        assert!(results.iter().any(Result::is_ok));
        let name = state_basename("/project", "session");
        let row = fs::read_to_string(temporary.path().join(STATE_DIR_NAME).join(name))
            .expect("state row");
        let parsed = parse_state_row(&row).expect("complete row");
        assert_eq!(parsed.path_hash, path_hash("/project/private name.md"));
        assert_eq!(parsed.offset, "7");
        assert_eq!(parsed.epoch, "100");
        assert!(
            parsed
                .count
                .parse::<u8>()
                .is_ok_and(|count| (1..=8).contains(&count))
        );
    }

    #[test]
    fn reminder_text_is_path_free_and_stable() {
        assert_eq!(
            REMINDER_TEXT,
            "Read-poll detected: repeated identical Read calls. Use one read after state changes instead of polling."
        );
        assert!(!REMINDER_TEXT.contains('/'));
    }
}
