//! Safe compatibility owner for `cleanup run`.
//!
//! Cleanup deliberately treats every filesystem entry as hostile.  The only
//! recursive removals are direct children of canonical session roots, after a
//! fresh containment/symlink check and a bounded activity scan.  Active
//! session pointers are collected before the sweep so an old top-level mtime
//! cannot erase a live run.

use larch_adapters::{PathIntent, TemporaryRoot, progress_state, remove_session_tmpdir};
use larch_core::{KeyPolicy, parse_allowlisted_env_line};
use std::{
    collections::BTreeSet,
    env,
    ffi::OsString,
    fs, io,
    path::{Path, PathBuf},
    process::ExitCode,
    time::{Duration, SystemTime},
};

const DEFAULT_RETENTION_DAYS: u64 = 7;
const SECONDS_PER_DAY: u64 = 86_400;
const MAX_ACTIVITY_ENTRIES: usize = 10_000;
const TMP_FALLBACK: &str = "/tmp";
const TMP_PATTERNS: &[&str] = &[
    "claude-implement-*",
    "claude-fix-issue-*",
    "claude-review-*",
    "claudin-review-*",
    "claude-issue-test",
    "wait-reviewers-*",
    "test-health-empty-caller-env-*",
    "test-health-explicit-false-*",
    "test-health-explicit-true-*",
    "test-session-setup-*",
    "larch-*",
    "larch3-fresh",
    "larch3-plan-review-prompts.sh",
    "larch4-review.diff",
    "check-review-bogus.err",
    "commit-msg-*-review.txt",
    "commit-msg-review-*.txt",
    "cr-debug-design",
    "issue-*-design-comment.md",
];

/// Run the session cleanup and preserve its legacy stdout envelope.
pub fn run(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        eprintln!(
            "Warning: cleanup run ignores arguments: {}",
            arguments
                .iter()
                .map(|value| value.to_string_lossy())
                .collect::<Vec<_>>()
                .join(" ")
        );
    }
    let retention = retention_days();
    println!("SESSION_COUNT={}", claude_session_count());

    let cache_root = cache_sessions_root();
    let active = active_session_directories(&cache_root);
    if active.uncertain {
        eprintln!(
            "Warning: a live session pointer could not be validated; skipping age-based cleanup."
        );
    }
    let cache_removed = sweep_cache_root(&cache_root, retention, &active);
    println!("CACHE_REMOVED={cache_removed}");

    let tmp_removed = temporary_roots()
        .iter()
        .map(|root| sweep_temporary_root(root, retention, &active))
        .sum::<usize>();
    println!("TMP_REMOVED={tmp_removed}");

    let links_removed = reap_design_links(&cache_root);
    println!("SYMLINKS_REMOVED={links_removed}");
    let pointers_removed = reap_implement_pointers(&cache_root);
    println!("IMPLEMENT_POINTERS_REMOVED={pointers_removed}");

    let progress_removed = progress_cleanup(retention);
    println!("PROGRESS_REMOVED={progress_removed}");
    eprintln!();
    eprintln!("Cleanup complete:");
    eprintln!("  ~/.cache/larch/sessions/: {cache_removed} entries removed");
    eprintln!("  /tmp (larch patterns):    {tmp_removed} entries removed");
    eprintln!("  dangling design-env links: {links_removed} removed");
    eprintln!("  stale implement-env files: {pointers_removed} removed");
    eprintln!("  progress breadcrumbs:      {progress_removed} removed");
    ExitCode::SUCCESS
}

fn retention_days() -> u64 {
    let raw = env::var("LARCH_CLEANUP_RETENTION_DAYS").unwrap_or_else(|_| "7".to_owned());
    match raw.parse::<u64>() {
        Ok(days) if days > 0 => days,
        _ => {
            eprintln!("Warning: invalid LARCH_CLEANUP_RETENTION_DAYS='{raw}'; using 7.");
            DEFAULT_RETENTION_DAYS
        }
    }
}

fn claude_session_count() -> usize {
    let Ok(output) = std::process::Command::new("pgrep")
        .args(["-x", "claude"])
        .output()
    else {
        return 0;
    };
    if !output.status.success() {
        return 0;
    }
    String::from_utf8_lossy(&output.stdout)
        .lines()
        .filter(|line| !line.trim().is_empty())
        .count()
}

fn cache_sessions_root() -> PathBuf {
    env::var_os("XDG_CACHE_HOME")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .or_else(|| {
            env::var_os("HOME")
                .filter(|value| !value.is_empty())
                .map(PathBuf::from)
                .map(|home| home.join(".cache"))
        })
        .unwrap_or_else(|| PathBuf::from("/tmp/.cache"))
        .join("larch")
        .join("sessions")
}

fn temporary_roots() -> Vec<PathBuf> {
    if let Some(root) = env::var_os("LARCH_TEST_TMP_ROOT").filter(|value| !value.is_empty()) {
        return canonical_directory(&PathBuf::from(root))
            .into_iter()
            .collect();
    }
    let mut roots = BTreeSet::new();
    for raw in [
        env::var_os("TMPDIR").filter(|value| !value.is_empty()),
        Some(OsString::from(TMP_FALLBACK)),
    ]
    .into_iter()
    .flatten()
    {
        if let Some(root) = canonical_directory(&PathBuf::from(raw)) {
            roots.insert(root);
        }
    }
    roots.into_iter().collect()
}

fn canonical_directory(path: &Path) -> Option<PathBuf> {
    let metadata = fs::symlink_metadata(path).ok()?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return None;
    }
    fs::canonicalize(path).ok()
}

#[derive(Default)]
struct ActiveSessions {
    directories: BTreeSet<PathBuf>,
    uncertain: bool,
}

fn active_session_directories(cache_root: &Path) -> ActiveSessions {
    let mut active = ActiveSessions::default();
    for key in ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "SESSION_TMPDIR"] {
        if let Some(value) = env::var_os(key).filter(|value| !value.is_empty()) {
            add_active_path(&mut active.directories, Path::new(&value));
        }
    }
    let Ok(entries) = fs::read_dir(cache_root) else {
        if cache_root.exists() {
            active.uncertain = true;
        }
        return active;
    };
    for entry in entries.flatten() {
        let name = entry.file_name();
        let name = name.to_string_lossy();
        let path = entry.path();
        if name.starts_with("current-design-env-") && name.ends_with(".sh") {
            match fs::canonicalize(&path) {
                Ok(target) => match read_env_key(&target, "DESIGN_TMPDIR")
                    .or_else(|| read_env_key(&target, "SESSION_TMPDIR"))
                {
                    Some(value) => add_active_path(&mut active.directories, Path::new(&value)),
                    None => active.uncertain = true,
                },
                Err(error) if error.kind() != io::ErrorKind::NotFound => active.uncertain = true,
                Err(_) => {}
            }
        } else if name.starts_with("current-implement-env-") && name.ends_with(".sh") {
            match read_env_key(&path, "IMPLEMENT_TMPDIR") {
                Some(value) => add_active_path(&mut active.directories, Path::new(&value)),
                None => active.uncertain = true,
            }
        }
    }
    active
}

fn add_active_path(active: &mut BTreeSet<PathBuf>, path: &Path) {
    if let Some(path) = canonical_directory(path) {
        active.insert(path);
    }
}

fn read_env_key(path: &Path, key: &str) -> Option<String> {
    let metadata = fs::symlink_metadata(path).ok()?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return None;
    }
    let bytes = fs::read(path).ok()?;
    let text = String::from_utf8_lossy(&bytes);
    text.lines().find_map(|line| {
        parse_allowlisted_env_line(line, &[key], Some(KeyPolicy::Environment), true)
            .map(|(_key, value)| value)
    })
}

fn sweep_cache_root(root: &Path, retention: u64, active: &ActiveSessions) -> usize {
    sweep_root(root, retention, active, |_| true, false, "cache cleanup")
}

fn sweep_temporary_root(root: &Path, retention: u64, active: &ActiveSessions) -> usize {
    sweep_root(
        root,
        retention,
        active,
        matches_temporary_pattern,
        true,
        "tmp-root cleanup",
    )
}

fn sweep_root(
    root: &Path,
    retention: u64,
    active: &ActiveSessions,
    accepted: impl Fn(&str) -> bool,
    remove_files: bool,
    label: &str,
) -> usize {
    if active.uncertain {
        return 0;
    }
    let Some(canonical_root) = canonical_directory(root) else {
        return 0;
    };
    let Ok(root_guard) = TemporaryRoot::resolve(Some(&canonical_root)) else {
        eprintln!(
            "Warning: failed to validate '{root}'; skipping {label}.",
            root = root.display()
        );
        return 0;
    };
    let Ok(entries) = fs::read_dir(root_guard.path()) else {
        eprintln!(
            "Warning: failed to enumerate '{}'; skipping {label}.",
            root_guard.path().display()
        );
        return 0;
    };
    let cutoff = cutoff(retention);
    let mut removed = 0;
    for entry in entries.flatten() {
        let path = entry.path();
        let name = entry.file_name();
        if !accepted(&name.to_string_lossy()) || active.directories.contains(&path) {
            continue;
        }
        let Ok(metadata) = fs::symlink_metadata(&path) else {
            continue;
        };
        if metadata.file_type().is_symlink() || !(metadata.is_file() || metadata.is_dir()) {
            continue;
        }
        if metadata.is_file() && !remove_files {
            continue;
        }
        if !older_than(&metadata, cutoff) {
            continue;
        }
        if metadata.is_dir() && has_recent_activity(&path, cutoff).unwrap_or(true) {
            continue;
        }
        let Ok(confined) = root_guard.confine(&path, PathIntent::Cleanup) else {
            continue;
        };
        if confined.revalidate().is_err() {
            continue;
        }
        let removed_this = if metadata.is_dir() {
            remove_session_tmpdir(confined.path()).is_ok()
        } else {
            fs::remove_file(confined.path()).is_ok()
        };
        if removed_this && fs::symlink_metadata(&path).is_err() {
            removed += 1;
        }
    }
    removed
}

fn cutoff(retention: u64) -> SystemTime {
    let duration = Duration::from_secs(retention.saturating_mul(SECONDS_PER_DAY));
    SystemTime::now()
        .checked_sub(duration)
        .unwrap_or(SystemTime::UNIX_EPOCH)
}

fn older_than(metadata: &fs::Metadata, cutoff: SystemTime) -> bool {
    metadata.modified().is_ok_and(|modified| modified < cutoff)
}

/// Return `Ok(true)` when a bounded nested scan finds fresh activity.
fn has_recent_activity(path: &Path, cutoff: SystemTime) -> Result<bool, io::Error> {
    let mut pending = vec![(path.to_path_buf(), 0_usize)];
    let mut scanned = 0;
    while let Some((current, depth)) = pending.pop() {
        scanned += 1;
        if scanned > MAX_ACTIVITY_ENTRIES {
            return Ok(true);
        }
        let metadata = fs::symlink_metadata(&current)?;
        if metadata.file_type().is_symlink() {
            return Ok(true);
        }
        if metadata.modified().is_ok_and(|modified| modified >= cutoff) {
            return Ok(true);
        }
        if depth == 5 || !metadata.is_dir() {
            continue;
        }
        for child in fs::read_dir(&current)? {
            pending.push((child?.path(), depth + 1));
        }
    }
    Ok(false)
}

fn matches_temporary_pattern(name: &str) -> bool {
    TMP_PATTERNS
        .iter()
        .any(|pattern| wildcard_match(pattern, name))
}

fn wildcard_match(pattern: &str, value: &str) -> bool {
    let mut parts = pattern.split('*');
    let first = parts.next().unwrap_or_default();
    if !value.starts_with(first) {
        return false;
    }
    let mut remaining = &value[first.len()..];
    let mut trailing_star = pattern.ends_with('*');
    for part in parts {
        if part.is_empty() {
            continue;
        }
        let Some(index) = remaining.find(part) else {
            return false;
        };
        remaining = &remaining[index + part.len()..];
        trailing_star = false;
    }
    trailing_star || remaining.is_empty()
}

fn reap_design_links(cache_root: &Path) -> usize {
    let Some(root) = canonical_directory(cache_root) else {
        return 0;
    };
    let Ok(entries) = fs::read_dir(&root) else {
        return 0;
    };
    entries
        .flatten()
        .filter(|entry| {
            let name = entry.file_name();
            let name = name.to_string_lossy();
            name.starts_with("current-design-env-") && name.ends_with(".sh")
        })
        .filter(|entry| {
            let path = entry.path();
            fs::symlink_metadata(&path).is_ok_and(|metadata| metadata.file_type().is_symlink())
                && stale_design_link(&path)
                && fs::remove_file(path).is_ok()
        })
        .count()
}

/// A design pointer is stale when its target vanished or a verified env file
/// names a session directory that no longer exists.
///
/// The check intentionally happens again immediately before unlinking the
/// pointer. We never follow a target for removal; only the link itself can be
/// unlinked below the canonical cache root.
fn stale_design_link(path: &Path) -> bool {
    let Ok(target) = fs::canonicalize(path) else {
        return true;
    };
    let Some(tmpdir) =
        read_env_key(&target, "DESIGN_TMPDIR").or_else(|| read_env_key(&target, "SESSION_TMPDIR"))
    else {
        // An existing pointer whose contents cannot be validated may still
        // name a live session. Retain it; only a missing target is dangling.
        return false;
    };
    canonical_directory(Path::new(&tmpdir)).is_none()
}

fn reap_implement_pointers(cache_root: &Path) -> usize {
    let Some(root) = canonical_directory(cache_root) else {
        return 0;
    };
    let Ok(entries) = fs::read_dir(&root) else {
        return 0;
    };
    entries
        .flatten()
        .filter(|entry| {
            let name = entry.file_name();
            let name = name.to_string_lossy();
            name.starts_with("current-implement-env-") && name.ends_with(".sh")
        })
        .filter(|entry| {
            let path = entry.path();
            let regular_file = fs::symlink_metadata(&path)
                .is_ok_and(|metadata| metadata.is_file() && !metadata.file_type().is_symlink());
            let Some(tmpdir) = regular_file
                .then(|| read_env_key(&path, "IMPLEMENT_TMPDIR"))
                .flatten()
            else {
                return false;
            };
            !Path::new(&tmpdir).is_dir() && fs::remove_file(path).is_ok()
        })
        .count()
}

fn progress_cleanup(retention: u64) -> usize {
    let cache_home = progress_state::progress_cache_home(
        env::var_os("LARCH_TEST_CACHE_HOME").as_deref(),
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    );
    progress_state::cleanup_old_progress_files(&cache_home, retention)
}

#[cfg(test)]
mod tests {
    use super::{
        ActiveSessions, active_session_directories, matches_temporary_pattern, reap_design_links,
        reap_implement_pointers, sweep_cache_root, sweep_temporary_root, wildcard_match,
    };
    use std::{
        fs,
        time::{Duration, SystemTime},
    };

    fn age(path: &std::path::Path) {
        let old = SystemTime::now()
            .checked_sub(Duration::from_secs(10 * 86_400))
            .expect("old timestamp");
        fs::File::open(path)
            .expect("open stale fixture")
            .set_times(fs::FileTimes::new().set_modified(old))
            .expect("age stale fixture");
    }

    #[test]
    fn temporary_pattern_matcher_covers_literal_and_wildcard_forms() {
        assert!(matches_temporary_pattern("claude-implement-123"));
        assert!(matches_temporary_pattern("issue-77-design-comment.md"));
        assert!(!matches_temporary_pattern("unrelated"));
        assert!(wildcard_match(
            "commit-msg-*-review.txt",
            "commit-msg-42-review.txt"
        ));
    }

    #[cfg(unix)]
    #[test]
    fn implement_pointer_symlink_is_never_reaped() {
        let root = tempfile::tempdir().expect("cache root");
        let target = root.path().join("outside.env");
        fs::write(&target, "IMPLEMENT_TMPDIR=/missing\n").expect("pointer target");
        let link = root.path().join("current-implement-env-42.sh");
        std::os::unix::fs::symlink(&target, &link).expect("pointer link");

        assert_eq!(reap_implement_pointers(root.path()), 0);
        assert!(link.is_symlink());
        assert!(target.is_file());
    }

    #[test]
    fn stale_regular_implement_pointer_is_reaped() {
        let root = tempfile::tempdir().expect("cache root");
        let pointer = root.path().join("current-implement-env-42.sh");
        fs::write(&pointer, "IMPLEMENT_TMPDIR=/missing\n").expect("stale pointer");

        assert_eq!(reap_implement_pointers(root.path()), 1);
        assert!(!pointer.exists());
    }

    #[test]
    fn stale_cache_and_temporary_entries_are_removed_but_recent_activity_is_kept() {
        let root = tempfile::tempdir().expect("cleanup root");
        let cache = root.path().join("cache");
        let stale_cache = cache.join("stale-cache");
        let fresh_child = cache.join("recent-activity/child.txt");
        let temporary = root.path().join("temporary");
        let stale_tmp = temporary.join("larch-stale");
        fs::create_dir_all(&stale_cache).expect("stale cache");
        fs::create_dir_all(fresh_child.parent().expect("fresh parent")).expect("fresh cache");
        fs::write(&fresh_child, "fresh\n").expect("fresh child");
        fs::create_dir_all(&stale_tmp).expect("stale temp");
        age(&stale_cache);
        age(fresh_child.parent().expect("fresh parent"));
        age(&stale_tmp);

        assert_eq!(sweep_cache_root(&cache, 1, &ActiveSessions::default()), 1);
        assert!(!stale_cache.exists());
        assert!(fresh_child.is_file());
        assert_eq!(
            sweep_temporary_root(&temporary, 1, &ActiveSessions::default()),
            1
        );
        assert!(!stale_tmp.exists());
    }

    #[test]
    fn unreadable_current_pointer_fails_closed_for_age_cleanup() {
        let root = tempfile::tempdir().expect("cleanup root");
        let cache = root.path().join("cache");
        let stale = cache.join("stale");
        fs::create_dir_all(&stale).expect("stale cache");
        age(&stale);
        fs::write(
            cache.join("current-implement-env-42.sh"),
            "not an environment file\n",
        )
        .expect("unreadable pointer fixture");

        let active = active_session_directories(&cache);
        assert!(active.uncertain);
        assert_eq!(sweep_cache_root(&cache, 1, &active), 0);
        assert!(stale.is_dir());
    }

    #[cfg(unix)]
    #[test]
    fn dangling_design_links_are_reaped_and_quoted_live_targets_are_retained() {
        let root = tempfile::tempdir().expect("cleanup root");
        let cache = root.path().join("cache");
        fs::create_dir(&cache).expect("cache root");
        let missing_target = cache.join("design-missing.env");
        fs::write(&missing_target, "export DESIGN_TMPDIR=/missing\n").expect("missing target");
        let missing_link = cache.join("current-design-env-missing.sh");
        std::os::unix::fs::symlink(&missing_target, &missing_link).expect("missing link");
        let live = root.path().join("live design");
        fs::create_dir(&live).expect("live design");
        let live_target = cache.join("design-live.env");
        fs::write(
            &live_target,
            format!("export SESSION_TMPDIR='{}'\n", live.display()),
        )
        .expect("live target");
        let live_link = cache.join("current-design-env-live.sh");
        std::os::unix::fs::symlink(&live_target, &live_link).expect("live link");

        assert_eq!(reap_design_links(&cache), 1);
        assert!(!missing_link.exists());
        assert!(live_link.is_symlink());
    }
}
