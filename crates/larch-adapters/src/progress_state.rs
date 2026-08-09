//! Clone-scoped progress breadcrumb state: layout, activation, and appends.
//!
//! Every writer is best effort and fail silent: a missing, corrupt, or
//! symlink-swapped path yields `false` rather than an error, because progress
//! breadcrumbs must never fail a workflow step. Path safety, directory
//! creation, and atomic publication reuse the [`crate::filesystem`] and
//! [`crate::file_io`] owners instead of re-deriving confinement here.

use crate::{
    PathIntent, TemporaryRoot, assert_no_symlink_path_or_ancestors, atomic_write_utf8,
    ensure_directory_chain, git::GixRepository,
};
use larch_core::RepositoryRead as _;
use larch_core::{
    CURRENT_RUN_FILENAME, CURRENT_RUN_LOCK_FILENAME, PROGRESS_DIRNAME, RUN_BREADCRUMB_FILENAME,
    breadcrumb_line, progress_clone_digest, progress_run_id_error, validate_progress_run_id,
};
use nix::{
    dir::Dir,
    fcntl::{AtFlags, Flock, FlockArg, OFlag, open, openat},
    sys::stat::{Mode, SFlag, fstat, fstatat},
    unistd::{UnlinkatFlags, dup, unlinkat},
};
use std::{
    collections::BTreeSet,
    ffi::OsStr,
    fs::{self, OpenOptions},
    io::{Read as _, Write as _},
    os::{
        fd::OwnedFd,
        unix::fs::{MetadataExt as _, OpenOptionsExt as _},
    },
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};

const SECONDS_PER_DAY: u64 = 86_400;
const CLONE_DIGEST_HEX_LENGTH: usize = 16;

/// Resolved locations for one clone's progress state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProgressPaths {
    clone_dir: PathBuf,
    clone_identity: PathBuf,
}

impl ProgressPaths {
    /// Return the clone-scoped progress directory.
    #[must_use]
    pub fn clone_dir(&self) -> &Path {
        &self.clone_dir
    }

    /// Return the canonical consumer clone root this state is keyed by.
    #[must_use]
    pub fn clone_identity(&self) -> &Path {
        &self.clone_identity
    }

    /// Return the clone-scoped active-run pointer path.
    #[must_use]
    pub fn current_pointer(&self) -> PathBuf {
        self.clone_dir.join(CURRENT_RUN_FILENAME)
    }

    /// Return the breadcrumb log path for one run.
    #[must_use]
    pub fn run_breadcrumbs(&self, run_id: &str) -> PathBuf {
        self.clone_dir.join(run_id).join(RUN_BREADCRUMB_FILENAME)
    }
}

/// Resolve the larch cache home from an explicit environment snapshot.
///
/// `LARCH_TEST_CACHE_HOME` wins so offline harnesses stay off the real cache,
/// then `XDG_CACHE_HOME`, then `$HOME/.cache`.
#[must_use]
pub fn progress_cache_home(
    test_cache_home: Option<&OsStr>,
    xdg_cache_home: Option<&OsStr>,
    home: Option<&OsStr>,
) -> PathBuf {
    for candidate in [test_cache_home, xdg_cache_home] {
        if let Some(value) = candidate.filter(|value| !value.is_empty()) {
            return PathBuf::from(value);
        }
    }
    home.filter(|value| !value.is_empty()).map_or_else(
        || PathBuf::from("/.cache"),
        |value| Path::new(value).join(".cache"),
    )
}

/// Return the clone-scoped progress paths for one repository root.
///
/// The clone identity is the consumer repository top level when `repo_root`
/// sits in a work tree, and the canonical path otherwise, matching the writer
/// and reader halves of the retired Python owner.
#[must_use]
pub fn progress_paths(cache_home: &Path, repo_root: &Path) -> ProgressPaths {
    let canonical = canonical_clone_root(repo_root);
    let digest = progress_clone_digest(&canonical.to_string_lossy());
    ProgressPaths {
        clone_dir: cache_home.join("larch").join(PROGRESS_DIRNAME).join(digest),
        clone_identity: canonical,
    }
}

fn canonical_clone_root(repo_root: &Path) -> PathBuf {
    if let Some(work_dir) = GixRepository::discover(repo_root)
        .ok()
        .and_then(|repository| repository.location().work_dir)
    {
        let path = PathBuf::from(String::from_utf8_lossy(work_dir.as_bytes()).into_owned());
        if let Ok(canonical) = fs::canonicalize(&path) {
            return canonical;
        }
    }
    fs::canonicalize(repo_root).unwrap_or_else(|_error| repo_root.to_path_buf())
}

/// Return the active run ID for a clone without creating progress state.
///
/// The pointer is opened once with `O_NOFOLLOW` and its type is confirmed on
/// that same descriptor, so a symlink swapped in after an inspection cannot
/// redirect the read the way a check-then-open pair would allow.
#[must_use]
pub fn read_active_run_id(paths: &ProgressPaths) -> Option<String> {
    let mut handle = OpenOptions::new()
        .read(true)
        .custom_flags(nix::libc::O_NOFOLLOW | nix::libc::O_NONBLOCK)
        .open(paths.current_pointer())
        .ok()?;
    if !handle.metadata().ok()?.file_type().is_file() {
        return None;
    }
    let mut bytes = Vec::new();
    handle.read_to_end(&mut bytes).ok()?;
    let text = String::from_utf8_lossy(&bytes);
    let first_line = text.split_inclusive('\n').next().unwrap_or_default();
    validate_progress_run_id(first_line.trim_end()).map(ToOwned::to_owned)
}

/// Point a clone's active-run pointer at `run_id`, creating its run directory.
///
/// # Errors
///
/// Returns the operator diagnostic when the run ID is unsafe or the pointer
/// cannot be published.
pub fn activate_run(paths: &ProgressPaths, run_id: &str) -> Result<(), String> {
    if let Some(message) = progress_run_id_error(run_id) {
        return Err(message);
    }
    let safe_run_id = validate_progress_run_id(run_id).unwrap_or_default();
    ensure_directory_chain(&paths.clone_dir.join(safe_run_id))
        .map_err(|error| format!("progress directory creation failed: {error}"))?;
    let root = clone_root(paths)?;
    let _guard = acquire_pointer_lock(&paths.clone_dir)?;
    let pointer = root
        .confine(root.path().join(CURRENT_RUN_FILENAME), PathIntent::Write)
        .map_err(|error| format!("unsafe progress pointer: {error}"))?;
    atomic_write_utf8(&pointer, &format!("{safe_run_id}\n"), 0o600)
        .map_err(|error| format!("progress pointer write failed: {error}"))
}

/// Clear the active-run pointer only while `expected_run_id` still owns it.
#[must_use]
pub fn deactivate_run(paths: &ProgressPaths, expected_run_id: &str) -> bool {
    let Some(safe_run_id) = validate_progress_run_id(expected_run_id) else {
        return false;
    };
    clear_pointer(paths, Some(safe_run_id))
}

/// Clear the active-run pointer regardless of its prior owner.
#[must_use]
pub fn clear_active_run(paths: &ProgressPaths) -> bool {
    clear_pointer(paths, None)
}

fn clear_pointer(paths: &ProgressPaths, expected_run_id: Option<&str>) -> bool {
    if !paths.clone_dir.is_dir() {
        return false;
    }
    let Ok(_guard) = acquire_pointer_lock(&paths.clone_dir) else {
        return false;
    };
    let pointer = paths.current_pointer();
    if !fs::symlink_metadata(&pointer).is_ok_and(|data| data.file_type().is_file()) {
        return false;
    }
    if expected_run_id
        .is_some_and(|expected| read_active_run_id(paths).as_deref() != Some(expected))
    {
        return false;
    }
    fs::remove_file(&pointer).is_ok()
}

/// Append one breadcrumb to the clone's active run, if a valid pointer exists.
#[must_use]
pub fn append_breadcrumb(paths: &ProgressPaths, skill: &str, step: &str, text: &str) -> bool {
    let Some(line) = breadcrumb_line(skill, step, text) else {
        return false;
    };
    let Some(run_id) = read_active_run_id(paths) else {
        return false;
    };
    let Ok(root) = clone_root(paths) else {
        return false;
    };
    let target = root.path().join(&run_id).join(RUN_BREADCRUMB_FILENAME);
    append_line(&root, &target, &line)
}

/// Append one breadcrumb to a named run without changing the active pointer.
#[must_use]
pub fn append_breadcrumb_for_run(
    paths: &ProgressPaths,
    run_id: &str,
    skill: &str,
    step: &str,
    text: &str,
) -> bool {
    let Some(line) = breadcrumb_line(skill, step, text) else {
        return false;
    };
    let Some(safe_run_id) = validate_progress_run_id(run_id) else {
        return false;
    };
    if ensure_directory_chain(&paths.clone_dir.join(safe_run_id)).is_err() {
        return false;
    }
    let Ok(root) = clone_root(paths) else {
        return false;
    };
    let target = root.path().join(safe_run_id).join(RUN_BREADCRUMB_FILENAME);
    append_line(&root, &target, &line)
}

fn append_line(root: &TemporaryRoot, path: &Path, line: &str) -> bool {
    let Ok(confined) = root.confine(path, PathIntent::Cache) else {
        return false;
    };
    let path = confined.path();
    let Ok(mut handle) = OpenOptions::new()
        .create(true)
        .append(true)
        .mode(0o600)
        .custom_flags(nix::libc::O_NOFOLLOW | nix::libc::O_NONBLOCK)
        .open(path)
    else {
        return false;
    };
    handle.write_all(line.as_bytes()).is_ok()
}

/// Remove stale progress runs and legacy flat logs below one cache home.
///
/// The cleanup owner never follows a symlink while traversing the progress
/// tree. It holds each clone's pointer lock while choosing stale runs, leaves
/// the active run intact, and removes entries only through pinned directory
/// descriptors. A missing or hostile cache tree remains a fail-silent no-op.
#[must_use]
pub fn cleanup_old_progress_files(cache_home: &Path, retention_days: u64) -> usize {
    cleanup_old_progress_files_at(cache_home, retention_days, SystemTime::now())
}

fn cleanup_old_progress_files_at(cache_home: &Path, retention_days: u64, now: SystemTime) -> usize {
    if retention_days == 0 {
        return 0;
    }
    let Some(retention_seconds) = retention_days.checked_mul(SECONDS_PER_DAY) else {
        return 0;
    };
    let Ok(elapsed) = now.duration_since(UNIX_EPOCH) else {
        return 0;
    };
    let cutoff_seconds = elapsed.as_secs().saturating_sub(retention_seconds);
    let Ok(cutoff_seconds) = i64::try_from(cutoff_seconds) else {
        return 0;
    };
    let progress_dir = cache_home.join("larch").join(PROGRESS_DIRNAME);
    if assert_no_symlink_path_or_ancestors(&progress_dir).is_err() {
        return 0;
    }
    let Ok(root) = TemporaryRoot::resolve(Some(&progress_dir)) else {
        return 0;
    };
    let Some(directory) = open_verified_directory(root.path()) else {
        return 0;
    };

    let mut clone_names = BTreeSet::new();
    let mut removed = 0;
    let Some(entry_names) = directory_entry_names(&directory) else {
        return 0;
    };
    for name in entry_names {
        let Ok(stat) = fstatat(&directory, name.as_str(), AtFlags::AT_SYMLINK_NOFOLLOW) else {
            continue;
        };
        if let Some(clone_name) = name.strip_suffix(".log") {
            if is_clone_digest(clone_name) {
                clone_names.insert(clone_name.to_owned());
            }
            if is_regular_file(&stat)
                && is_older_than(&stat, cutoff_seconds)
                && unlinkat(&directory, name.as_str(), UnlinkatFlags::NoRemoveDir).is_ok()
            {
                removed += 1;
            }
        }
        if is_clone_digest(&name) && is_directory(&stat) {
            clone_names.insert(name);
        }
    }
    for clone_name in clone_names {
        removed += cleanup_clone_directory(&directory, &clone_name, cutoff_seconds);
    }
    removed
}

fn cleanup_clone_directory(root: &OwnedFd, clone_name: &str, cutoff_seconds: i64) -> usize {
    let Some(clone) = open_verified_directory_at(root, clone_name) else {
        return 0;
    };
    let Some(_lock) = acquire_pointer_lock_at(&clone) else {
        return 0;
    };
    let active_run_id = read_active_run_id_from_directory(&clone);
    let mut removed = 0;
    let Some(run_ids) = directory_entry_names(&clone) else {
        return 0;
    };
    for run_id in run_ids {
        if validate_progress_run_id(&run_id).is_none()
            || active_run_id.as_deref() == Some(run_id.as_str())
        {
            continue;
        }
        if cleanup_run_directory(&clone, &run_id, cutoff_seconds) {
            removed += 1;
        }
    }
    removed
}

fn cleanup_run_directory(parent: &OwnedFd, run_id: &str, cutoff_seconds: i64) -> bool {
    let Some(run) = open_verified_directory_at(parent, run_id) else {
        return false;
    };
    let Ok(run_stat) = fstat(&run) else {
        return false;
    };
    let activity_stat = fstatat(&run, RUN_BREADCRUMB_FILENAME, AtFlags::AT_SYMLINK_NOFOLLOW)
        .ok()
        .filter(is_regular_file)
        .unwrap_or(run_stat);
    if !is_older_than(&activity_stat, cutoff_seconds) {
        return false;
    }
    if !remove_directory_contents(&run) || !same_directory_at(parent, run_id, &run) {
        return false;
    }
    unlinkat(parent, run_id, UnlinkatFlags::RemoveDir).is_ok()
}

fn remove_directory_contents(directory: &OwnedFd) -> bool {
    let Some(entry_names) = directory_entry_names(directory) else {
        return false;
    };
    for name in entry_names {
        let Ok(stat) = fstatat(directory, name.as_str(), AtFlags::AT_SYMLINK_NOFOLLOW) else {
            return false;
        };
        if is_directory(&stat) {
            let Some(child) = open_verified_directory_at(directory, &name) else {
                return false;
            };
            if !remove_directory_contents(&child) || !same_directory_at(directory, &name, &child) {
                return false;
            }
            if unlinkat(directory, name.as_str(), UnlinkatFlags::RemoveDir).is_err() {
                return false;
            }
        } else if unlinkat(directory, name.as_str(), UnlinkatFlags::NoRemoveDir).is_err() {
            return false;
        }
    }
    true
}

fn open_verified_directory(path: &Path) -> Option<OwnedFd> {
    let directory = open(
        path,
        OFlag::O_RDONLY | OFlag::O_DIRECTORY | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
        Mode::empty(),
    )
    .ok()?;
    let opened = fstat(&directory).ok()?;
    let visible = fs::symlink_metadata(path).ok()?;
    (is_directory(&opened) && same_stat_metadata(&opened, &visible)).then_some(directory)
}

fn open_verified_directory_at(parent: &OwnedFd, name: &str) -> Option<OwnedFd> {
    let directory = openat(
        parent,
        name,
        OFlag::O_RDONLY | OFlag::O_DIRECTORY | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
        Mode::empty(),
    )
    .ok()?;
    same_directory_at(parent, name, &directory).then_some(directory)
}

fn same_directory_at(parent: &OwnedFd, name: &str, directory: &OwnedFd) -> bool {
    let Ok(opened) = fstat(directory) else {
        return false;
    };
    let Ok(visible) = fstatat(parent, name, AtFlags::AT_SYMLINK_NOFOLLOW) else {
        return false;
    };
    is_directory(&opened) && is_directory(&visible) && same_file_stat(&opened, &visible)
}

fn directory_entry_names(directory: &OwnedFd) -> Option<Vec<String>> {
    let duplicate = dup(directory).ok()?;
    let mut entries = Dir::from_fd(duplicate).ok()?;
    let mut names = Vec::new();
    for entry in entries.iter() {
        let name = entry.ok()?.file_name().to_str().ok()?.to_owned();
        if name != "." && name != ".." {
            names.push(name);
        }
    }
    Some(names)
}

fn acquire_pointer_lock_at(directory: &OwnedFd) -> Option<Flock<OwnedFd>> {
    let file = openat(
        directory,
        CURRENT_RUN_LOCK_FILENAME,
        OFlag::O_RDWR | OFlag::O_CREAT | OFlag::O_NOFOLLOW | OFlag::O_NONBLOCK | OFlag::O_CLOEXEC,
        Mode::from_bits_truncate(0o600),
    )
    .ok()?;
    if !is_regular_file(&fstat(&file).ok()?) {
        return None;
    }
    Flock::lock(file, FlockArg::LockExclusive).ok()
}

fn read_active_run_id_from_directory(directory: &OwnedFd) -> Option<String> {
    let descriptor = openat(
        directory,
        CURRENT_RUN_FILENAME,
        OFlag::O_RDONLY | OFlag::O_NOFOLLOW | OFlag::O_NONBLOCK | OFlag::O_CLOEXEC,
        Mode::empty(),
    )
    .ok()?;
    if !is_regular_file(&fstat(&descriptor).ok()?) {
        return None;
    }
    let mut handle = fs::File::from(descriptor);
    let mut bytes = Vec::new();
    handle.read_to_end(&mut bytes).ok()?;
    let text = String::from_utf8_lossy(&bytes);
    let first_line = text.split_inclusive('\n').next().unwrap_or_default();
    validate_progress_run_id(first_line.trim_end()).map(ToOwned::to_owned)
}

fn is_clone_digest(name: &str) -> bool {
    name.len() == CLONE_DIGEST_HEX_LENGTH
        && name
            .bytes()
            .all(|byte| byte.is_ascii_digit() || matches!(byte, b'a'..=b'f'))
}

const fn is_older_than(stat: &nix::sys::stat::FileStat, cutoff_seconds: i64) -> bool {
    stat.st_mtime < cutoff_seconds
}

fn is_regular_file(stat: &nix::sys::stat::FileStat) -> bool {
    file_type(stat) == SFlag::S_IFREG
}

fn is_directory(stat: &nix::sys::stat::FileStat) -> bool {
    file_type(stat) == SFlag::S_IFDIR
}

const fn file_type(stat: &nix::sys::stat::FileStat) -> SFlag {
    SFlag::from_bits_truncate(stat.st_mode)
}

fn same_stat_metadata(stat: &nix::sys::stat::FileStat, metadata: &fs::Metadata) -> bool {
    i128::from(stat.st_dev) == i128::from(metadata.dev())
        && i128::from(stat.st_ino) == i128::from(metadata.ino())
}

const fn same_file_stat(left: &nix::sys::stat::FileStat, right: &nix::sys::stat::FileStat) -> bool {
    left.st_dev == right.st_dev && left.st_ino == right.st_ino
}

/// Anchor confinement for one clone's already-created progress directory.
///
/// The returned root is canonical, so callers rebuild paths from
/// [`TemporaryRoot::path`] instead of the caller's original spelling.
fn clone_root(paths: &ProgressPaths) -> Result<TemporaryRoot, String> {
    TemporaryRoot::resolve(Some(&paths.clone_dir))
        .map_err(|error| format!("unsafe progress clone directory: {error}"))
}

/// Take the clone-local exclusive lock guarding the active-run pointer.
///
/// Activation and every clearing route share this lock, so a late deactivation
/// from an older run can never race a newer run's activation. The lock releases
/// when the returned guard drops.
fn acquire_pointer_lock(clone_dir: &Path) -> Result<Flock<fs::File>, String> {
    let path = clone_dir.join(CURRENT_RUN_LOCK_FILENAME);
    let file = OpenOptions::new()
        .create(true)
        .append(true)
        .mode(0o600)
        .custom_flags(nix::libc::O_NOFOLLOW | nix::libc::O_NONBLOCK)
        .open(&path)
        .map_err(|error| format!("progress pointer lock failed: {error}"))?;
    Flock::lock(file, FlockArg::LockExclusive)
        .map_err(|(_file, error)| format!("progress pointer lock failed: {error}"))
}

#[cfg(test)]
mod tests {
    use super::{
        CLONE_DIGEST_HEX_LENGTH, SECONDS_PER_DAY, activate_run, append_breadcrumb,
        append_breadcrumb_for_run, cleanup_old_progress_files_at, clear_active_run, deactivate_run,
        progress_cache_home, progress_paths, read_active_run_id,
    };
    use larch_core::{CURRENT_RUN_FILENAME, PROGRESS_DIRNAME, RUN_BREADCRUMB_FILENAME};
    use std::{
        ffi::OsStr,
        fs,
        time::{Duration, UNIX_EPOCH},
    };
    use tempfile::TempDir;

    #[test]
    fn cache_home_prefers_the_test_override_then_xdg_then_home() {
        assert_eq!(
            progress_cache_home(Some(OsStr::new("/t")), Some(OsStr::new("/x")), None),
            std::path::PathBuf::from("/t")
        );
        assert_eq!(
            progress_cache_home(Some(OsStr::new("")), Some(OsStr::new("/x")), None),
            std::path::PathBuf::from("/x")
        );
        assert_eq!(
            progress_cache_home(None, None, Some(OsStr::new("/home/u"))),
            std::path::PathBuf::from("/home/u/.cache")
        );
    }

    #[test]
    fn activation_appends_and_owner_scoped_clearing_round_trip() {
        let sandbox = TempDir::new().expect("sandbox");
        let clone = sandbox.path().join("clone");
        fs::create_dir_all(&clone).expect("clone");
        let paths = progress_paths(sandbox.path(), &clone);

        assert_eq!(read_active_run_id(&paths), None);
        assert!(!append_breadcrumb(
            &paths,
            "design",
            "1",
            "before activation"
        ));

        activate_run(&paths, "run-1").expect("activate");

        assert_eq!(read_active_run_id(&paths).as_deref(), Some("run-1"));
        assert!(append_breadcrumb(&paths, "design", "1", "started"));
        assert_eq!(
            fs::read_to_string(paths.run_breadcrumbs("run-1")).expect("log"),
            "[design 1] started\n"
        );
        assert!(!append_breadcrumb(&paths, "design", "1", "see https://x"));
        assert!(append_breadcrumb_for_run(
            &paths,
            "run-2",
            "design",
            "2",
            "other run"
        ));
        assert_eq!(read_active_run_id(&paths).as_deref(), Some("run-1"));
        assert!(!deactivate_run(&paths, "run-2"));
        activate_run(&paths, "run-3").expect("replace active run");
        assert_eq!(read_active_run_id(&paths).as_deref(), Some("run-3"));
        assert!(paths.clone_dir().join("run-1").is_dir());
        assert!(!deactivate_run(&paths, "run-1"));
        assert!(deactivate_run(&paths, "run-3"));
        assert_eq!(read_active_run_id(&paths), None);
        assert!(!clear_active_run(&paths));

        activate_run(&paths, "run-4").expect("reactivate");

        assert!(clear_active_run(&paths));
        assert_eq!(read_active_run_id(&paths), None);
    }

    #[test]
    fn a_symlinked_pointer_is_never_read_or_cleared() {
        let sandbox = TempDir::new().expect("sandbox");
        let clone = sandbox.path().join("clone");
        fs::create_dir_all(&clone).expect("clone");
        let paths = progress_paths(sandbox.path(), &clone);
        activate_run(&paths, "run-1").expect("activate");
        let decoy = sandbox.path().join("decoy");
        fs::write(&decoy, "run-9\n").expect("decoy");
        fs::remove_file(paths.current_pointer()).expect("remove pointer");
        std::os::unix::fs::symlink(&decoy, paths.current_pointer()).expect("symlink");

        assert_eq!(read_active_run_id(&paths), None);
        assert!(!clear_active_run(&paths));
        assert!(paths.current_pointer().is_symlink());
    }

    #[test]
    fn unsafe_run_ids_are_refused_by_every_writer() {
        let sandbox = TempDir::new().expect("sandbox");
        let clone = sandbox.path().join("clone");
        fs::create_dir_all(&clone).expect("clone");
        let paths = progress_paths(sandbox.path(), &clone);

        assert!(activate_run(&paths, "../escape").is_err());
        assert!(activate_run(&paths, "current").is_err());
        assert!(!append_breadcrumb_for_run(
            &paths, "..", "design", "1", "text"
        ));
        assert!(!deactivate_run(&paths, "current"));
    }

    #[test]
    fn cleanup_reaps_only_stale_non_active_entries_without_following_symlinks() {
        let sandbox = TempDir::new().expect("sandbox");
        let cache = sandbox.path().join("cache");
        let progress = cache.join("larch/progress");
        let clone = progress.join("a".repeat(CLONE_DIGEST_HEX_LENGTH));
        fs::create_dir_all(&clone).expect("clone directory");
        fs::write(clone.join(CURRENT_RUN_FILENAME), "active-run\n").expect("active pointer");
        let active = clone.join("active-run");
        let old = clone.join("old-run");
        let fresh = clone.join("fresh-run");
        for run in [&active, &old, &fresh] {
            fs::create_dir_all(run).expect("run directory");
            fs::write(run.join(RUN_BREADCRUMB_FILENAME), "[design 1] row\n").expect("log");
        }
        let legacy = progress.join(format!("{}.log", "b".repeat(CLONE_DIGEST_HEX_LENGTH)));
        fs::write(&legacy, "legacy\n").expect("legacy log");
        let outside = sandbox.path().join("outside.log");
        fs::write(&outside, "outside\n").expect("outside log");
        let linked = progress.join(format!("{}.log", "c".repeat(CLONE_DIGEST_HEX_LENGTH)));
        std::os::unix::fs::symlink(&outside, &linked).expect("legacy symlink");
        let outside_clone = sandbox.path().join("outside-clone");
        let outside_run = outside_clone.join("old-run");
        fs::create_dir_all(&outside_run).expect("outside run directory");
        let outside_log = outside_run.join(RUN_BREADCRUMB_FILENAME);
        fs::write(&outside_log, "outside\n").expect("outside run log");
        let linked_clone = progress.join("d".repeat(CLONE_DIGEST_HEX_LENGTH));
        std::os::unix::fs::symlink(&outside_clone, &linked_clone).expect("clone symlink");

        let now = UNIX_EPOCH + Duration::from_secs(100 * SECONDS_PER_DAY);
        let old_time = now - Duration::from_secs(8 * SECONDS_PER_DAY);
        let fresh_time = now - Duration::from_secs(SECONDS_PER_DAY);
        for path in [old.join(RUN_BREADCRUMB_FILENAME), legacy, outside_log] {
            fs::File::open(path)
                .expect("open old entry")
                .set_times(fs::FileTimes::new().set_modified(old_time))
                .expect("age old entry");
        }
        fs::File::open(fresh.join(RUN_BREADCRUMB_FILENAME))
            .expect("open fresh entry")
            .set_times(fs::FileTimes::new().set_modified(fresh_time))
            .expect("age fresh entry");

        assert_eq!(cleanup_old_progress_files_at(&cache, 7, now), 2);
        assert!(active.is_dir(), "the active run must remain");
        assert!(!old.exists(), "the stale run must be removed");
        assert!(fresh.is_dir(), "the fresh run must remain");
        assert!(
            !progress
                .join(format!("{}.log", "b".repeat(CLONE_DIGEST_HEX_LENGTH)))
                .exists()
        );
        assert!(linked.is_symlink(), "a symlinked legacy entry must remain");
        assert!(outside.exists(), "cleanup must never follow the symlink");
        assert!(linked_clone.is_symlink(), "a symlinked clone must remain");
        assert!(
            outside_run.is_dir(),
            "cleanup must not follow a clone symlink"
        );
    }

    #[test]
    fn cleanup_refuses_a_symlinked_progress_root() {
        let sandbox = TempDir::new().expect("sandbox");
        let cache = sandbox.path().join("cache");
        let larch = cache.join("larch");
        fs::create_dir_all(&larch).expect("cache parent");
        let outside = sandbox.path().join("outside-progress");
        fs::create_dir_all(&outside).expect("outside progress root");
        let stale = outside.join(format!("{}.log", "d".repeat(CLONE_DIGEST_HEX_LENGTH)));
        fs::write(&stale, "legacy\n").expect("outside legacy log");
        std::os::unix::fs::symlink(&outside, larch.join(PROGRESS_DIRNAME))
            .expect("progress symlink");

        let now = UNIX_EPOCH + Duration::from_secs(100 * SECONDS_PER_DAY);
        assert_eq!(cleanup_old_progress_files_at(&cache, 7, now), 0);
        assert!(stale.exists(), "the symlink target must remain untouched");
    }

    #[test]
    fn cleanup_refuses_a_symlinked_progress_ancestor() {
        let sandbox = TempDir::new().expect("sandbox");
        let cache = sandbox.path().join("cache");
        fs::create_dir_all(&cache).expect("cache parent");
        let outside_larch = sandbox.path().join("outside-larch");
        let progress = outside_larch.join(PROGRESS_DIRNAME);
        fs::create_dir_all(&progress).expect("outside progress root");
        let stale = progress.join(format!("{}.log", "e".repeat(CLONE_DIGEST_HEX_LENGTH)));
        fs::write(&stale, "legacy\n").expect("outside legacy log");
        std::os::unix::fs::symlink(&outside_larch, cache.join("larch"))
            .expect("larch ancestor symlink");

        let now = UNIX_EPOCH + Duration::from_secs(100 * SECONDS_PER_DAY);
        assert_eq!(cleanup_old_progress_files_at(&cache, 7, now), 0);
        assert!(stale.exists(), "the symlink target must remain untouched");
    }
}
