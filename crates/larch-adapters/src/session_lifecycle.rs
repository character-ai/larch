//! Session temp-directory lifecycle effects: design-tmpdir validation,
//! implement-tmpdir resolution, session-id publication, and confined removal.
//!
//! Every entry point takes its roots, clock, and environment snapshot from the
//! caller so the composition root owns ambient state. Removal and publication
//! reuse the confinement and atomic-write owners in [`crate::filesystem`] and
//! [`crate::file_io`] instead of re-deriving path safety here.

use crate::{
    PathIntent, TemporaryRoot, atomic_write_utf8, open_confined_read, parent_directory,
    read_first_raw_key, safe_output_parent, write_confined_file, writer_target_allowed,
};
use chrono::{SecondsFormat, Utc};
use larch_core::{
    IMPLEMENT_SENTINEL_RELATIVE_PATHS, IMPLEMENT_TMPDIR_PREFIX, design_tmpdir_syntax_error,
    prefers_implement_candidate,
};
use std::{
    ffi::OsStr,
    fs::{self, OpenOptions},
    io::{Read as _, Write as _},
    path::{Path, PathBuf},
    time::UNIX_EPOCH,
};
use uuid::Uuid;

#[cfg(unix)]
use nix::{errno::Errno, sys::signal::kill, unistd::Pid};

/// Basename of the append-only cleanup audit trail written before removal.
pub const CLEANUP_AUDIT_LOG_NAME: &str = "larch-cleanup-audit.log";

/// Private marker left while `session setup` still owns a new session directory.
///
/// A successful setup removes this marker at its commit point. A process killed
/// before that point leaves the marker behind for the confined cleanup sweep.
pub const UNCOMMITTED_SESSION_SETUP_MARKER: &str = ".larch-session-setup";

const UNCOMMITTED_SETUP_STATE: &str = "STATE=uncommitted";
const UNCOMMITTED_SETUP_OWNER_PID_PREFIX: &str = "OWNER_PID=";
const UNCOMMITTED_SETUP_MARKER_MAX_BYTES: u64 = 256;

/// Whether [`write_session_id`] minted a new identity or kept the existing one.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum SessionIdOutcome {
    /// A non-empty identity already existed and was left untouched.
    Preserved(String),
    /// A fresh identity was published to the target path.
    Written(String),
}

impl SessionIdOutcome {
    /// Return the identity now stored at the target path.
    #[must_use]
    pub fn session_id(&self) -> &str {
        match self {
            Self::Preserved(value) | Self::Written(value) => value,
        }
    }
}

/// Inputs for one implement-tmpdir resolution.
#[derive(Clone, Copy, Debug)]
pub struct ImplementTmpdirQuery<'a> {
    /// Absolute clone path the hook is running in; an empty value resolves to none.
    pub hook_cwd: &'a str,
    /// Session roots to scan, in the order the legacy resolver used.
    pub roots: &'a [PathBuf],
    /// Optional session identity that pins the match and bypasses the TTL.
    pub session_id: &'a str,
    /// Freshness window in seconds; zero or negative disables expiry.
    pub ttl_seconds: i64,
    /// Current Unix time in seconds.
    pub now: i64,
}

/// Validate a `/design` temp directory against the resolved session allowlist.
///
/// # Errors
///
/// Returns the exact operator diagnostic when the candidate is malformed, names
/// a non-directory, resolves through a broken leaf symlink, or lands outside the
/// cache-sessions, `TMPDIR`, and `/tmp` allowlist after resolution.
pub fn validate_design_tmpdir(
    candidate: &str,
    tmpdir: Option<&OsStr>,
    cache_sessions_root: &Path,
) -> Result<(), String> {
    if let Some(message) = design_tmpdir_syntax_error(candidate) {
        return Err(message.to_owned());
    }
    let (ancestor, tail) = split_ancestor_tail(candidate);
    let Ok(resolved_ancestor) = fs::canonicalize(&ancestor) else {
        return Err("design-tmpdir: parent resolution failed".to_owned());
    };
    let mut resolved = if tail.as_os_str().is_empty() {
        resolved_ancestor
    } else {
        resolved_ancestor.join(&tail)
    };
    let path = Path::new(candidate);
    if path.exists() {
        let is_symlink = fs::symlink_metadata(path).is_ok_and(|data| data.file_type().is_symlink());
        if !path.is_dir() {
            return Err(if is_symlink {
                "design-tmpdir: leaf symlink must resolve to a directory".to_owned()
            } else {
                "design-tmpdir: path must name a directory".to_owned()
            });
        }
        match fs::canonicalize(path) {
            Ok(canonical) => resolved = canonical,
            Err(_) if is_symlink => {
                return Err("design-tmpdir: leaf symlink must resolve to a directory".to_owned());
            }
            Err(_) => {}
        }
    }
    let allowlist = [
        canonical_prefix(cache_sessions_root),
        tmpdir
            .filter(|value| !value.is_empty())
            .map(|value| canonical_prefix(Path::new(value)))
            .unwrap_or_default(),
        canonical_prefix(Path::new("/tmp")),
    ];
    let comparable = format!("{}/", resolved.to_string_lossy().trim_end_matches('/'));
    if allowlist
        .iter()
        .any(|prefix| !prefix.is_empty() && comparable.starts_with(prefix.as_str()))
    {
        return Ok(());
    }
    Err(format!(
        "design-tmpdir: path not under allowlist after resolution: {}",
        resolved.display()
    ))
}

/// Resolve the live `/implement` temp directory for one clone, or an empty string.
///
/// A candidate qualifies when it carries an implement sentinel, a keepalive file
/// naming this clone, and either a matching session identity or a sentinel mtime
/// inside the freshness window. Unreadable candidates are skipped, never fatal.
#[must_use]
pub fn resolve_implement_tmpdir(query: &ImplementTmpdirQuery<'_>) -> String {
    if query.hook_cwd.is_empty() {
        return String::new();
    }
    let mut best = String::new();
    let mut best_mtime = -1_i64;
    for root in query.roots {
        let Ok(entries) = fs::read_dir(root) else {
            continue;
        };
        for entry in entries.flatten() {
            let candidate = entry.path();
            if !entry
                .file_name()
                .to_string_lossy()
                .starts_with(IMPLEMENT_TMPDIR_PREFIX)
            {
                continue;
            }
            let Some(mtime) = implement_candidate_mtime(&candidate, query) else {
                continue;
            };
            let text = candidate.to_string_lossy().into_owned();
            if prefers_implement_candidate(&text, mtime, &best, best_mtime) {
                best_mtime = mtime;
                best = text;
            }
        }
    }
    best
}

/// Idempotently publish a session identity below an allowed session root.
///
/// A pre-existing non-empty file keeps its first line. Otherwise a fresh
/// identity is written with mode `0600` through the shared atomic-write owner.
///
/// # Errors
///
/// Returns the exact operator diagnostic when the target escapes the allowed
/// session roots, its parent is not a usable directory, any path component is a
/// symlink, or publication fails.
pub fn write_session_id(
    output: &Path,
    allowed_roots: &[PathBuf],
) -> Result<SessionIdOutcome, String> {
    if !writer_target_allowed(output, allowed_roots) {
        return Err(format!(
            "output path not under allowed session root: {}",
            output.display()
        ));
    }
    let parent = parent_directory(output);
    fs::create_dir_all(&parent).map_err(|error| format!("{}: {error}", parent.display()))?;
    if !safe_output_parent(output) {
        return Err(format!(
            "output parent is not a writable directory: {}",
            parent.display()
        ));
    }
    if let Ok(metadata) = fs::metadata(output)
        && metadata.is_file()
        && metadata.len() > 0
    {
        let existing = fs::read(output).map_or_else(
            |_error| String::new(),
            |bytes| {
                String::from_utf8_lossy(&bytes)
                    .split('\n')
                    .next()
                    .unwrap_or_default()
                    .to_owned()
            },
        );
        return Ok(SessionIdOutcome::Preserved(existing));
    }
    let session_id = Uuid::new_v4().to_string();
    write_confined_file(output, &format!("{session_id}\n"), 0o600, "session-id")?;
    Ok(SessionIdOutcome::Written(session_id))
}

/// Mark a newly-created session directory as owned by an in-flight setup.
///
/// The marker is written through the existing confined atomic-write owner. It
/// is intentionally private and contains only the setup process ID needed by
/// recovery to avoid deleting a directory whose creator is still running.
///
/// # Errors
///
/// Returns an error when `directory` is not a direct-or-descendant safe path
/// below `root`, or when the marker cannot be published atomically.
pub fn write_uncommitted_session_setup_marker(
    root: &TemporaryRoot,
    directory: &Path,
    owner_pid: u32,
) -> Result<(), String> {
    let directory = confined_session_directory(root, directory)?;
    let marker = root
        .confine(
            directory.path().join(UNCOMMITTED_SESSION_SETUP_MARKER),
            PathIntent::Write,
        )
        .map_err(|error| error.to_string())?;
    let text =
        format!("{UNCOMMITTED_SETUP_STATE}\n{UNCOMMITTED_SETUP_OWNER_PID_PREFIX}{owner_pid}\n");
    atomic_write_utf8(&marker, &text, 0o600).map_err(|error| error.to_string())
}

/// Remove a verified uncommitted marker at `session setup`'s commit point.
///
/// # Errors
///
/// Returns an error when the marker is absent, unsafe, or cannot be removed.
pub fn commit_uncommitted_session_setup(
    root: &TemporaryRoot,
    directory: &Path,
) -> Result<(), String> {
    let directory = confined_session_directory(root, directory)?;
    let marker = root
        .confine(
            directory.path().join(UNCOMMITTED_SESSION_SETUP_MARKER),
            PathIntent::Cleanup,
        )
        .map_err(|error| error.to_string())?;
    marker.revalidate().map_err(|error| error.to_string())?;
    fs::remove_file(marker.path()).map_err(|error| error.to_string())
}

/// Remove stale, uncommitted `session setup` directories directly below `root`.
///
/// Recovery is deliberately marker-based rather than age-based: a crash should
/// be recoverable on the next cleanup pass, while a still-live setup must never
/// be consumed. Invalid markers, symlinked entries, unsafe roots, and owners
/// whose liveness cannot be disproven are retained fail-closed.
#[must_use]
pub fn recover_uncommitted_session_setups(root: &TemporaryRoot) -> usize {
    let Ok(entries) = fs::read_dir(root.path()) else {
        return 0;
    };
    let mut removed = 0;
    for entry in entries.flatten() {
        let candidate = entry.path();
        let Some(owner_pid) = uncommitted_setup_owner(root, &candidate) else {
            continue;
        };
        if uncommitted_setup_owner_is_live(owner_pid) {
            continue;
        }
        // Re-read the marker immediately before removal. A setup that raced
        // from an earlier state toward commit must be retained rather than
        // deleted using a stale directory observation.
        if uncommitted_setup_owner(root, &candidate) != Some(owner_pid) {
            continue;
        }
        let Ok(confined) = root.confine(&candidate, PathIntent::Cleanup) else {
            continue;
        };
        if confined.revalidate().is_err() {
            continue;
        }
        if remove_session_tmpdir(confined.path()).is_ok()
            && fs::symlink_metadata(&candidate).is_err()
        {
            removed += 1;
        }
    }
    removed
}

fn confined_session_directory(
    root: &TemporaryRoot,
    directory: &Path,
) -> Result<crate::ConfinedPath, String> {
    root.confine(directory, PathIntent::Cleanup)
        .map_err(|error| error.to_string())
}

fn uncommitted_setup_owner(root: &TemporaryRoot, directory: &Path) -> Option<u32> {
    let directory = confined_session_directory(root, directory).ok()?;
    let marker = root
        .confine(
            directory.path().join(UNCOMMITTED_SESSION_SETUP_MARKER),
            PathIntent::Read,
        )
        .ok()?;
    let marker_file = open_confined_read(&marker).ok()?;
    if marker_file.metadata().ok()?.len() > UNCOMMITTED_SETUP_MARKER_MAX_BYTES {
        return None;
    }
    let mut bytes = Vec::new();
    marker_file
        .take(UNCOMMITTED_SETUP_MARKER_MAX_BYTES.saturating_add(1))
        .read_to_end(&mut bytes)
        .ok()?;
    if u64::try_from(bytes.len()).ok()? > UNCOMMITTED_SETUP_MARKER_MAX_BYTES {
        return None;
    }
    let text = String::from_utf8(bytes).ok()?;
    let mut lines = text.lines();
    if lines.next()? != UNCOMMITTED_SETUP_STATE {
        return None;
    }
    let owner_pid = lines
        .next()?
        .strip_prefix(UNCOMMITTED_SETUP_OWNER_PID_PREFIX)?
        .parse::<u32>()
        .ok()
        .filter(|pid| *pid != 0)?;
    if lines.next().is_some() {
        return None;
    }
    Some(owner_pid)
}

#[cfg(unix)]
fn uncommitted_setup_owner_is_live(owner_pid: u32) -> bool {
    let Ok(owner_pid) = i32::try_from(owner_pid) else {
        return true;
    };
    match kill(Pid::from_raw(owner_pid), None) {
        Err(Errno::ESRCH) => false,
        // A failed liveness probe must not authorize recursive removal. This
        // also retains a rare PID-reuse ambiguity until a later cleanup pass.
        _ => true,
    }
}

#[cfg(not(unix))]
fn uncommitted_setup_owner_is_live(_owner_pid: u32) -> bool {
    // The released executable is currently Unix-only. Keep a conservative
    // fallback for cross-platform test builds rather than guessing PID state.
    true
}

/// Append one invocation record to the cleanup audit trail, best effort.
///
/// A failure to record is never fatal: the audit trail is observability, and
/// refusing cleanup because it could not be written would strand session state.
pub fn append_cleanup_audit(audit_log: &Path, parent_command: &str, target: &str) {
    let record = format!(
        "{} pid={} ppid={} parent={parent_command} dir={target}\n",
        Utc::now().to_rfc3339_opts(SecondsFormat::Secs, true),
        std::process::id(),
        parent_process_id(),
    );
    if let Ok(mut handle) = OpenOptions::new().create(true).append(true).open(audit_log) {
        let _ignored = handle.write_all(record.as_bytes());
    }
}

/// Remove a session temp directory that is already known to be an allowed root.
///
/// Nothing to remove is success: an absent target and a dangling symlink both
/// return `Ok`, matching the legacy existence probe that resolved symlinks. A
/// live symlink and a non-directory are refused rather than followed or deleted,
/// and the removal is verified before returning.
///
/// # Errors
///
/// Returns the exact operator diagnostic when the target is a live symlink or a
/// non-directory, when removal fails, or when the directory survives removal.
pub fn remove_session_tmpdir(target: &Path) -> Result<(), String> {
    let Ok(link_metadata) = fs::symlink_metadata(target) else {
        return Ok(());
    };
    // A dangling symlink, or any target this process cannot stat through, was
    // "missing" to the legacy verb and must stay a silent no-op.
    let Ok(metadata) = fs::metadata(target) else {
        return Ok(());
    };
    if link_metadata.file_type().is_symlink() {
        return Err("cleanup-tmpdir failed: Cannot call rmtree on a symbolic link".to_owned());
    }
    if !metadata.is_dir() {
        return Err(format!(
            "cleanup-tmpdir failed: not a directory: {}",
            target.display()
        ));
    }
    fs::remove_dir_all(target).map_err(|error| format!("cleanup-tmpdir failed: {error}"))?;
    if fs::symlink_metadata(target).is_ok() {
        return Err(format!(
            "cleanup-tmpdir failed: directory still exists: {}",
            target.display()
        ));
    }
    Ok(())
}

fn implement_candidate_mtime(candidate: &Path, query: &ImplementTmpdirQuery<'_>) -> Option<i64> {
    if !candidate.is_dir() {
        return None;
    }
    let sentinel = IMPLEMENT_SENTINEL_RELATIVE_PATHS
        .iter()
        .map(|relative| candidate.join(relative))
        .find(|path| path.is_file())?;
    let keepalive = candidate.join(".larch-keepalive");
    if !keepalive.is_file() {
        return None;
    }
    if read_first_raw_key(&keepalive, "CLONE_PATH").ok()?? != query.hook_cwd {
        return None;
    }
    let session_match = if query.session_id.is_empty() {
        false
    } else {
        if read_first_raw_key(&keepalive, "SESSION_ID").ok()?? != query.session_id {
            return None;
        }
        true
    };
    let mtime = i64::try_from(
        fs::metadata(&sentinel)
            .ok()?
            .modified()
            .ok()?
            .duration_since(UNIX_EPOCH)
            .ok()?
            .as_secs(),
    )
    .ok()?;
    if !session_match
        && query.ttl_seconds > 0
        && (query.now <= 0 || query.now - mtime >= query.ttl_seconds)
    {
        return None;
    }
    Some(mtime)
}

/// Split a candidate into its deepest existing ancestor and the missing tail.
fn split_ancestor_tail(candidate: &str) -> (PathBuf, PathBuf) {
    let trimmed = candidate.trim_end_matches('/');
    let mut current = PathBuf::from(if trimmed.is_empty() { "/" } else { trimmed });
    let mut segments: Vec<std::ffi::OsString> = Vec::new();
    while !current.exists() && current != Path::new("/") {
        if let Some(name) = current.file_name() {
            segments.push(name.to_os_string());
        }
        current = current.parent().map_or_else(
            || PathBuf::from("/"),
            |parent| {
                if parent.as_os_str().is_empty() {
                    PathBuf::from("/")
                } else {
                    parent.to_path_buf()
                }
            },
        );
    }
    let mut tail = PathBuf::new();
    for segment in segments.iter().rev() {
        tail.push(segment);
    }
    (current, tail)
}

fn canonical_prefix(prefix: &Path) -> String {
    let resolved = if prefix.is_dir() {
        fs::canonicalize(prefix).unwrap_or_else(|_error| prefix.to_path_buf())
    } else {
        prefix.to_path_buf()
    };
    format!("{}/", resolved.to_string_lossy().trim_end_matches('/'))
}

/// Return the identifier of the process that invoked this one.
#[cfg(unix)]
#[must_use]
pub fn parent_process_id() -> u32 {
    nix::unistd::getppid().as_raw().unsigned_abs()
}

/// Return the identifier of the process that invoked this one.
#[cfg(not(unix))]
#[must_use]
pub const fn parent_process_id() -> u32 {
    0
}

#[cfg(test)]
mod tests {
    use super::{
        ImplementTmpdirQuery, SessionIdOutcome, commit_uncommitted_session_setup,
        recover_uncommitted_session_setups, remove_session_tmpdir, resolve_implement_tmpdir,
        split_ancestor_tail, validate_design_tmpdir, write_session_id,
        write_uncommitted_session_setup_marker,
    };
    use crate::TemporaryRoot;
    use larch_core::allowed_session_roots;
    use std::{
        ffi::OsStr,
        fs,
        path::{Path, PathBuf},
        time::{SystemTime, UNIX_EPOCH},
    };
    use tempfile::tempdir;

    fn now_seconds() -> i64 {
        i64::try_from(
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .expect("clock after epoch")
                .as_secs(),
        )
        .expect("seconds fit in i64")
    }

    fn seed_implement_session(root: &Path, name: &str, clone: &str, session: &str) -> PathBuf {
        seed_implement_session_with(
            root,
            name,
            "design-export/manifest.env",
            &format!(
                "# larch session identity (hook routing)\nCLONE_PATH={clone}\nSESSION_ID={session}\n"
            ),
        )
    }

    fn seed_implement_session_with(
        root: &Path,
        name: &str,
        sentinel: &str,
        keepalive: &str,
    ) -> PathBuf {
        let directory = root.join(name);
        let sentinel_path = directory.join(sentinel);
        fs::create_dir_all(sentinel_path.parent().expect("sentinel parent"))
            .expect("session directories");
        fs::write(&sentinel_path, "sentinel\n").expect("sentinel");
        fs::write(directory.join(".larch-keepalive"), keepalive).expect("keepalive");
        directory
    }

    fn set_mtime(path: &Path, seconds: u64) {
        fs::File::options()
            .write(true)
            .open(path)
            .expect("open sentinel for mtime")
            .set_modified(UNIX_EPOCH + std::time::Duration::from_secs(seconds))
            .expect("set sentinel mtime");
    }

    fn query<'a>(clone: &'a str, roots: &'a [PathBuf], now: i64) -> ImplementTmpdirQuery<'a> {
        ImplementTmpdirQuery {
            hook_cwd: clone,
            roots,
            session_id: "",
            ttl_seconds: 0,
            now,
        }
    }

    #[test]
    fn split_ancestor_tail_stops_at_the_deepest_existing_directory() {
        let directory = tempdir().expect("fixture tempdir");
        let existing = directory.path().canonicalize().expect("canonical fixture");
        let candidate = existing.join("missing/leaf");

        let (ancestor, tail) = split_ancestor_tail(&candidate.to_string_lossy());

        assert_eq!(ancestor, existing);
        assert_eq!(tail, PathBuf::from("missing/leaf"));
    }

    #[test]
    fn design_tmpdir_accepts_the_tmpdir_allowlist_and_rejects_outsiders() {
        let directory = tempdir().expect("fixture tempdir");
        let tmpdir = directory.path();
        let session = tmpdir.join("claude-design-abc");
        fs::create_dir(&session).expect("design session");
        let cache_root = tmpdir.join("cache/larch/sessions");

        assert_eq!(
            validate_design_tmpdir(
                &session.to_string_lossy(),
                Some(tmpdir.as_os_str()),
                &cache_root
            ),
            Ok(())
        );
        assert_eq!(
            validate_design_tmpdir(
                &session.join("missing").to_string_lossy(),
                Some(tmpdir.as_os_str()),
                &cache_root
            ),
            Ok(())
        );
        // Not a tempdir: every platform's temporary root is itself allowlisted,
        // on Linux through `/tmp` and on macOS through `TMPDIR`.
        let error = validate_design_tmpdir("/etc", Some(OsStr::new("")), &cache_root)
            .expect_err("outside path must fail");
        assert!(error.starts_with("design-tmpdir: path not under allowlist after resolution: "));
    }

    #[test]
    fn design_tmpdir_rejects_files_and_missing_ancestors() {
        let directory = tempdir().expect("fixture tempdir");
        let tmpdir = directory.path();
        let file = tmpdir.join("not-a-directory");
        fs::write(&file, b"x").expect("fixture file");

        assert_eq!(
            validate_design_tmpdir(
                &file.to_string_lossy(),
                Some(tmpdir.as_os_str()),
                Path::new("/nonexistent")
            ),
            Err("design-tmpdir: path must name a directory".to_owned())
        );
        assert_eq!(
            validate_design_tmpdir("/", Some(tmpdir.as_os_str()), Path::new("/nonexistent"))
                .expect_err("root is outside the allowlist"),
            "design-tmpdir: path not under allowlist after resolution: /"
        );
    }

    #[cfg(unix)]
    #[test]
    fn design_tmpdir_distinguishes_file_and_dangling_leaf_symlinks() {
        let directory = tempdir().expect("fixture tempdir");
        let tmpdir = directory.path();
        fs::write(tmpdir.join("target-file"), b"x").expect("symlink target file");
        let to_file = tmpdir.join("to-file");
        std::os::unix::fs::symlink(tmpdir.join("target-file"), &to_file).expect("file symlink");
        let dangling = tmpdir.join("dangling");
        std::os::unix::fs::symlink(tmpdir.join("absent"), &dangling).expect("dangling symlink");

        assert_eq!(
            validate_design_tmpdir(
                &to_file.to_string_lossy(),
                Some(tmpdir.as_os_str()),
                Path::new("/nonexistent")
            ),
            Err("design-tmpdir: leaf symlink must resolve to a directory".to_owned())
        );
        // A dangling leaf never resolves, so the missing-suffix rule applies and
        // the still-contained path stays acceptable, matching the legacy writer.
        assert_eq!(
            validate_design_tmpdir(
                &dangling.to_string_lossy(),
                Some(tmpdir.as_os_str()),
                Path::new("/nonexistent")
            ),
            Ok(())
        );
    }

    #[test]
    fn implement_resolution_binds_to_clone_session_and_freshness() {
        let directory = tempdir().expect("fixture tempdir");
        let root = directory.path().to_path_buf();
        let clone = "/clone/path";
        let fresh = seed_implement_session(&root, "claude-implement-fresh", clone, "S1");
        let _other_clone =
            seed_implement_session(&root, "claude-implement-other", "/elsewhere", "S1");
        let roots = [root];
        let now = now_seconds();

        let matched = resolve_implement_tmpdir(&ImplementTmpdirQuery {
            hook_cwd: clone,
            roots: &roots,
            session_id: "",
            ttl_seconds: 3600,
            now,
        });
        assert_eq!(matched, fresh.to_string_lossy());

        let session_bound = resolve_implement_tmpdir(&ImplementTmpdirQuery {
            hook_cwd: clone,
            roots: &roots,
            session_id: "S2",
            ttl_seconds: 3600,
            now,
        });
        assert_eq!(session_bound, "");

        let expired = resolve_implement_tmpdir(&ImplementTmpdirQuery {
            hook_cwd: clone,
            roots: &roots,
            session_id: "",
            ttl_seconds: 1,
            now: now + 10_000,
        });
        assert_eq!(expired, "");

        let session_bypasses_ttl = resolve_implement_tmpdir(&ImplementTmpdirQuery {
            hook_cwd: clone,
            roots: &roots,
            session_id: "S1",
            ttl_seconds: 1,
            now: now + 10_000,
        });
        assert_eq!(session_bypasses_ttl, fresh.to_string_lossy());

        assert_eq!(
            resolve_implement_tmpdir(&ImplementTmpdirQuery {
                hook_cwd: "",
                roots: &roots,
                session_id: "",
                ttl_seconds: 3600,
                now,
            }),
            ""
        );
    }

    #[test]
    fn implement_resolution_skips_candidates_without_a_sentinel_or_keepalive() {
        let directory = tempdir().expect("fixture tempdir");
        let root = directory.path().to_path_buf();
        let bare = root.join("claude-implement-bare");
        fs::create_dir(&bare).expect("bare session");
        let sentinel_only = root.join("claude-implement-sentinel");
        fs::create_dir(&sentinel_only).expect("sentinel session");
        fs::write(sentinel_only.join(".release-armed"), "").expect("sentinel");

        assert_eq!(
            resolve_implement_tmpdir(&ImplementTmpdirQuery {
                hook_cwd: "/clone/path",
                roots: &[root],
                session_id: "",
                ttl_seconds: 3600,
                now: now_seconds(),
            }),
            ""
        );
    }

    /// Return a temp root with no symlinked ancestor.
    ///
    /// macOS resolves `$TMPDIR` through `/var -> /private/var`, and the session
    /// writer refuses a symlinked ancestor, so tests must canonicalize first.
    fn real_temp_root(directory: &tempfile::TempDir) -> PathBuf {
        directory.path().canonicalize().expect("canonical tempdir")
    }

    #[test]
    fn implement_resolution_uses_the_first_declared_sentinel_not_the_newest_file() {
        let directory = tempdir().expect("fixture tempdir");
        let root = directory.path().to_path_buf();
        let clone = "/clone/path";
        let keepalive = format!("CLONE_PATH={clone}\nSESSION_ID=S1\n");
        let ordered = seed_implement_session_with(
            &root,
            "claude-implement-ordered",
            "design-export/manifest.env",
            &keepalive,
        );
        set_mtime(&ordered.join("design-export/manifest.env"), 1_000);
        // A newer non-first sentinel in the same directory must not supply the mtime.
        fs::write(ordered.join("review-round-summary.md"), "newer\n").expect("newer sentinel");
        set_mtime(&ordered.join("review-round-summary.md"), 5_000);
        let review_only = seed_implement_session_with(
            &root,
            "claude-implement-review",
            "review-round-summary.md",
            &keepalive,
        );
        set_mtime(&review_only.join("review-round-summary.md"), 3_000);
        let roots = [root];

        assert_eq!(
            resolve_implement_tmpdir(&query(clone, &roots, 10_000)),
            review_only.to_string_lossy()
        );
    }

    #[test]
    fn implement_resolution_breaks_an_equal_mtime_tie_lexically() {
        let directory = tempdir().expect("fixture tempdir");
        let root = directory.path().to_path_buf();
        let clone = "/clone/path";
        let first = seed_implement_session(&root, "claude-implement-aaa", clone, "S1");
        let second = seed_implement_session(&root, "claude-implement-bbb", clone, "S1");
        for candidate in [&first, &second] {
            set_mtime(&candidate.join("design-export/manifest.env"), 1_000);
        }
        let roots = [root];

        assert_eq!(
            resolve_implement_tmpdir(&query(clone, &roots, 4_000)),
            first.to_string_lossy()
        );
    }

    #[test]
    fn implement_resolution_matches_clone_paths_containing_an_equals_sign() {
        let directory = tempdir().expect("fixture tempdir");
        let root = directory.path().to_path_buf();
        let clone = "/clone/repo=name";
        let wanted = seed_implement_session(&root, "claude-implement-equals", clone, "S1");
        let roots = [root];

        assert_eq!(
            resolve_implement_tmpdir(&query(clone, &roots, now_seconds())),
            wanted.to_string_lossy()
        );
    }

    #[test]
    fn implement_resolution_skips_a_keepalive_with_a_carriage_return() {
        let directory = tempdir().expect("fixture tempdir");
        let root = directory.path().to_path_buf();
        let clone = "/clone/path";
        let _malformed = seed_implement_session_with(
            &root,
            "claude-implement-malformed",
            "design-export/manifest.env",
            &format!("CLONE_PATH={clone}\rSESSION_ID=S1\n"),
        );
        let roots = [root];

        assert_eq!(
            resolve_implement_tmpdir(&query(clone, &roots, now_seconds())),
            ""
        );
    }

    #[test]
    fn session_id_publication_is_idempotent_and_private() {
        let directory = tempdir().expect("fixture tempdir");
        let root = real_temp_root(&directory);
        let roots = [root.clone()];
        let target = root.join("nested/session-id");

        let first = write_session_id(&target, &roots).expect("first write");
        let SessionIdOutcome::Written(minted) = first else {
            panic!("first call must mint an identity");
        };
        assert_eq!(
            fs::read_to_string(&target).expect("identity file"),
            format!("{minted}\n")
        );
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;
            assert_eq!(
                fs::metadata(&target)
                    .expect("identity metadata")
                    .permissions()
                    .mode()
                    & 0o777,
                0o600
            );
        }

        let second = write_session_id(&target, &roots).expect("second write");
        assert_eq!(second, SessionIdOutcome::Preserved(minted));
    }

    #[test]
    fn session_id_publication_refuses_targets_outside_the_allowed_roots() {
        let directory = tempdir().expect("fixture tempdir");
        let outside = tempdir().expect("outside tempdir");
        let target = outside.path().join("session-id");

        assert_eq!(
            write_session_id(&target, &[directory.path().to_path_buf()])
                .expect_err("outside target must fail"),
            format!(
                "output path not under allowed session root: {}",
                target.display()
            )
        );
        assert!(!allowed_session_roots(None, None).is_empty());
    }

    #[cfg(unix)]
    #[test]
    fn session_id_publication_refuses_symlinked_parents_and_grandparents() {
        let directory = tempdir().expect("fixture tempdir");
        let root = real_temp_root(&directory);
        let real = root.join("real");
        let linked = root.join("linked");
        fs::create_dir_all(real.join("inner")).expect("real directories");
        std::os::unix::fs::symlink(&real, &linked).expect("ancestor symlink");
        let roots = [root];

        assert_eq!(
            write_session_id(&linked.join("session-id"), &roots)
                .expect_err("symlinked parent must fail"),
            format!(
                "output parent is not a writable directory: {}",
                linked.display()
            )
        );
        assert_eq!(
            write_session_id(&linked.join("inner/session-id"), &roots)
                .expect_err("symlinked grandparent must fail"),
            format!("refusing symlinked path or ancestor: {}", linked.display())
        );
    }

    #[test]
    fn removal_is_confined_verified_and_missing_tolerant() {
        let directory = tempdir().expect("fixture tempdir");
        let target = directory.path().join("session");
        fs::create_dir_all(target.join("nested")).expect("session tree");
        fs::write(target.join("nested/file"), b"x").expect("nested file");

        assert_eq!(remove_session_tmpdir(&target), Ok(()));
        assert!(!target.exists());
        assert_eq!(remove_session_tmpdir(&target), Ok(()));
    }

    #[cfg(unix)]
    #[test]
    fn removal_reports_a_blocked_directory_and_leaves_it_in_place() {
        use std::os::unix::fs::PermissionsExt as _;

        let directory = tempdir().expect("fixture tempdir");
        let target = directory.path().join("blocked");
        fs::create_dir(&target).expect("blocked directory");
        fs::write(target.join("keep"), b"x").expect("blocked child");
        fs::set_permissions(&target, fs::Permissions::from_mode(0o555))
            .expect("make directory read-only");

        let error = remove_session_tmpdir(&target).expect_err("blocked removal must fail");

        assert!(
            error.starts_with("cleanup-tmpdir failed: "),
            "unexpected diagnostic: {error}"
        );
        assert!(target.exists());
        fs::set_permissions(&target, fs::Permissions::from_mode(0o755))
            .expect("restore directory permissions");
    }

    #[cfg(unix)]
    #[test]
    fn removal_refuses_a_symlinked_target() {
        let directory = tempdir().expect("fixture tempdir");
        let real = directory.path().join("real");
        let link = directory.path().join("link");
        fs::create_dir(&real).expect("real directory");
        std::os::unix::fs::symlink(&real, &link).expect("target symlink");

        assert_eq!(
            remove_session_tmpdir(&link).expect_err("symlink target must fail"),
            "cleanup-tmpdir failed: Cannot call rmtree on a symbolic link"
        );
        assert!(real.is_dir());
    }

    #[cfg(unix)]
    #[test]
    fn uncommitted_recovery_refuses_a_symlinked_session_target() {
        let cleanup = tempdir().expect("cleanup root");
        let outside = tempdir().expect("outside root");
        let cleanup_root = TemporaryRoot::resolve(Some(cleanup.path())).expect("cleanup root");
        let outside_root = TemporaryRoot::resolve(Some(outside.path())).expect("outside root");
        let outside_session = outside_root.path().join("uncommitted");
        fs::create_dir(&outside_session).expect("outside session");
        write_uncommitted_session_setup_marker(&outside_root, &outside_session, std::process::id())
            .expect("outside marker");
        let link = cleanup_root.path().join("linked-uncommitted");
        std::os::unix::fs::symlink(&outside_session, &link).expect("session symlink");

        assert_eq!(recover_uncommitted_session_setups(&cleanup_root), 0);
        assert!(link.is_symlink());
        assert!(outside_session.is_dir());
    }

    #[test]
    fn uncommitted_commit_requires_and_removes_its_marker() {
        let directory = tempdir().expect("temporary root");
        let root = TemporaryRoot::resolve(Some(directory.path())).expect("temporary root");
        let session = root.path().join("uncommitted");
        fs::create_dir(&session).expect("session directory");

        assert!(commit_uncommitted_session_setup(&root, &session).is_err());
        write_uncommitted_session_setup_marker(&root, &session, std::process::id())
            .expect("uncommitted marker");
        commit_uncommitted_session_setup(&root, &session).expect("commit marker removal");

        assert!(
            !session
                .join(super::UNCOMMITTED_SESSION_SETUP_MARKER)
                .exists()
        );
    }

    #[cfg(unix)]
    #[test]
    fn removal_treats_a_dangling_symlink_as_nothing_to_remove() {
        let directory = tempdir().expect("fixture tempdir");
        let link = directory.path().join("dangling");
        std::os::unix::fs::symlink(directory.path().join("absent"), &link)
            .expect("dangling symlink");

        // The legacy verb probed existence through the link and exited 0.
        assert_eq!(remove_session_tmpdir(&link), Ok(()));
        assert!(
            fs::symlink_metadata(&link).is_ok(),
            "a dangling link must be left in place, not unlinked"
        );
    }

    #[test]
    fn removal_refuses_a_regular_file_target() {
        let directory = tempdir().expect("fixture tempdir");
        let file = directory.path().join("not-a-session");
        fs::write(&file, b"payload").expect("fixture file");

        assert_eq!(
            remove_session_tmpdir(&file).expect_err("file target must fail"),
            format!("cleanup-tmpdir failed: not a directory: {}", file.display())
        );
        assert!(file.is_file());
    }
}
