//! Clone-scoped progress breadcrumb state: layout, activation, and appends.
//!
//! Every writer is best effort and fail silent: a missing, corrupt, or
//! symlink-swapped path yields `false` rather than an error, because progress
//! breadcrumbs must never fail a workflow step. Path safety, directory
//! creation, and atomic publication reuse the [`crate::filesystem`] and
//! [`crate::file_io`] owners instead of re-deriving confinement here.

use crate::{
    PathIntent, TemporaryRoot, atomic_write_utf8, ensure_directory_chain, git::GixRepository,
};
use larch_core::RepositoryRead as _;
use larch_core::{
    CURRENT_RUN_FILENAME, CURRENT_RUN_LOCK_FILENAME, PROGRESS_DIRNAME, RUN_BREADCRUMB_FILENAME,
    breadcrumb_line, progress_clone_digest, progress_run_id_error, validate_progress_run_id,
};
use nix::fcntl::{Flock, FlockArg};
use std::{
    ffi::OsStr,
    fs::{self, OpenOptions},
    io::{Read as _, Write as _},
    os::unix::fs::OpenOptionsExt as _,
    path::{Path, PathBuf},
};

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
        .custom_flags(nix::libc::O_NOFOLLOW)
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
        .custom_flags(nix::libc::O_NOFOLLOW)
        .open(path)
    else {
        return false;
    };
    handle.write_all(line.as_bytes()).is_ok()
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
        .custom_flags(nix::libc::O_NOFOLLOW)
        .open(&path)
        .map_err(|error| format!("progress pointer lock failed: {error}"))?;
    Flock::lock(file, FlockArg::LockExclusive)
        .map_err(|(_file, error)| format!("progress pointer lock failed: {error}"))
}

#[cfg(test)]
mod tests {
    use super::{
        activate_run, append_breadcrumb, append_breadcrumb_for_run, clear_active_run,
        deactivate_run, progress_cache_home, progress_paths, read_active_run_id,
    };
    use std::{ffi::OsStr, fs};
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
        assert!(deactivate_run(&paths, "run-1"));
        assert_eq!(read_active_run_id(&paths), None);
        assert!(!clear_active_run(&paths));

        activate_run(&paths, "run-3").expect("reactivate");

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
}
