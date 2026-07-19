//! UTF-8 filesystem and same-directory atomic publication adapters.

use crate::{ConfinedPath, PathIntent, PathSafetyError, PathSafetyErrorKind};
use larch_core::{EnvFile, KvError};
use std::{
    error::Error,
    fmt,
    fs::{self, File},
    io::{self, Write},
    os::unix::fs::PermissionsExt,
    path::{Path, PathBuf},
};

/// Stable failure classes for filesystem-backed text primitives.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FileIoErrorKind {
    /// A path was relative, missing a filename, or crossed directories for a rename.
    InvalidPath,
    /// A requested file mode contained bits outside ordinary Unix permissions.
    InvalidMode,
    /// A path component or destination was a symlink.
    Symlink,
    /// A required directory or file had the wrong type.
    WrongFileType,
    /// File bytes were not valid UTF-8.
    InvalidUtf8,
    /// A `KEY=value` environment file violated its grammar.
    InvalidWireFormat,
    /// The operating system rejected the operation.
    Io,
    /// Publication completed, but syncing its containing directory failed.
    Durability,
}

/// A typed filesystem failure that retains the affected path.
#[derive(Debug)]
pub struct FileIoError {
    kind: FileIoErrorKind,
    path: PathBuf,
    message: String,
}

impl FileIoError {
    fn new(kind: FileIoErrorKind, path: &Path, message: impl Into<String>) -> Self {
        Self {
            kind,
            path: path.to_path_buf(),
            message: message.into(),
        }
    }

    /// Return the stable failure class.
    #[must_use]
    pub const fn kind(&self) -> FileIoErrorKind {
        self.kind
    }

    /// Return the path associated with the failure.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }
}

impl fmt::Display for FileIoError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}: {}", self.path.display(), self.message)
    }
}

impl Error for FileIoError {}

/// Read a regular file confined with [`PathIntent::Read`] as strict UTF-8.
///
/// # Errors
///
/// Returns [`FileIoError`] for unsafe paths, I/O failures, or invalid UTF-8.
pub fn read_utf8(path: &ConfinedPath) -> Result<String, FileIoError> {
    let raw_path = require_intent(path, PathIntent::Read)?;
    let bytes = fs::read(raw_path).map_err(|error| io_error(raw_path, &error))?;
    String::from_utf8(bytes).map_err(|error| {
        FileIoError::new(FileIoErrorKind::InvalidUtf8, raw_path, error.to_string())
    })
}

/// Atomically publish UTF-8 text to a path confined with [`PathIntent::Write`].
///
/// The parent must already exist. The temporary file is flushed and synced before
/// rename. A pre-publication failure leaves the prior destination untouched. A
/// [`FileIoErrorKind::Durability`] failure means the complete new destination is
/// visible but its directory entry could not be confirmed durable.
///
/// # Errors
///
/// Returns [`FileIoError`] for unsafe paths or any failed filesystem operation.
pub fn atomic_write_utf8(path: &ConfinedPath, text: &str, mode: u32) -> Result<(), FileIoError> {
    atomic_write_bytes(path, text.as_bytes(), mode)
}

/// Atomically publish exact bytes to a path confined with [`PathIntent::Write`].
///
/// # Errors
///
/// Returns [`FileIoError`] for unsafe paths or any failed filesystem operation.
pub fn atomic_write_bytes(path: &ConfinedPath, data: &[u8], mode: u32) -> Result<(), FileIoError> {
    atomic_write_with(path, mode, |file| file.write_all(data))?;
    let written = fs::read(path.path()).map_err(|error| io_error(path.path(), &error))?;
    if written != data {
        return Err(FileIoError::new(
            FileIoErrorKind::Io,
            path.path(),
            "post-write verification failed",
        ));
    }
    Ok(())
}

/// Rename a regular file over a same-directory destination.
///
/// Both paths must be confined with [`PathIntent::Write`].
///
/// # Errors
///
/// Returns [`FileIoError`] if either path is unsafe, the source is not regular,
/// or the paths do not share one lexical parent. [`FileIoErrorKind::Durability`]
/// means the rename completed but its directory entry could not be synced.
pub fn rename_same_directory(
    source: &ConfinedPath,
    destination: &ConfinedPath,
) -> Result<(), FileIoError> {
    let source_path = require_intent(source, PathIntent::Write)?;
    let destination_path = require_intent(destination, PathIntent::Write)?;
    if source_path.parent() != destination_path.parent() {
        return Err(FileIoError::new(
            FileIoErrorKind::InvalidPath,
            destination_path,
            "atomic rename requires one directory",
        ));
    }
    require_existing_file(source_path)?;
    fs::rename(source_path, destination_path)
        .map_err(|error| io_error(destination_path, &error))?;
    destination
        .revalidate()
        .map_err(|error| path_safety_error(destination_path, &error))?;
    sync_parent(destination_path)
}

/// Strictly read, allowlist-update, and atomically rewrite an environment file.
///
/// The path must be confined with [`PathIntent::Write`]. A missing destination
/// starts empty. Any invalid existing record or update aborts before publication,
/// leaving the destination unchanged.
///
/// # Errors
///
/// Returns [`FileIoError`] for unsafe paths, malformed state, or publication failure.
pub fn guarded_update_env(
    path: &ConfinedPath,
    updates: &[(&str, &str)],
    allowed_keys: &[&str],
    mode: u32,
) -> Result<(), FileIoError> {
    let raw_path = require_intent(path, PathIntent::Write)?;
    let mut env = match fs::symlink_metadata(raw_path) {
        Ok(_) => {
            let bytes = fs::read(raw_path).map_err(|error| io_error(raw_path, &error))?;
            let text = String::from_utf8(bytes).map_err(|error| {
                FileIoError::new(FileIoErrorKind::InvalidUtf8, raw_path, error.to_string())
            })?;
            EnvFile::parse(&text).map_err(|error| wire_error(raw_path, &error))?
        }
        Err(error) if error.kind() == io::ErrorKind::NotFound => EnvFile::empty(),
        Err(error) => return Err(io_error(raw_path, &error)),
    };
    env.apply_guarded(updates, allowed_keys)
        .map_err(|error| wire_error(raw_path, &error))?;
    let rendered = env.render().map_err(|error| wire_error(raw_path, &error))?;
    atomic_write_utf8(path, &rendered, mode)
}

fn atomic_write_with(
    path: &ConfinedPath,
    mode: u32,
    write: impl FnOnce(&mut File) -> io::Result<()>,
) -> Result<(), FileIoError> {
    let raw_path = require_intent(path, PathIntent::Write)?;
    validate_mode(raw_path, mode)?;
    let parent = raw_path.parent().ok_or_else(|| {
        FileIoError::new(FileIoErrorKind::InvalidPath, raw_path, "path has no parent")
    })?;
    let name = raw_path
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or_else(|| {
            FileIoError::new(
                FileIoErrorKind::InvalidPath,
                raw_path,
                "path has no UTF-8 filename",
            )
        })?;
    let mut temporary = tempfile::Builder::new()
        .prefix(&format!(".{name}."))
        .suffix(".tmp")
        .tempfile_in(parent)
        .map_err(|error| io_error(raw_path, &error))?;
    temporary
        .as_file()
        .set_permissions(fs::Permissions::from_mode(mode))
        .map_err(|error| io_error(raw_path, &error))?;
    write(temporary.as_file_mut()).map_err(|error| io_error(raw_path, &error))?;
    temporary
        .as_file_mut()
        .flush()
        .map_err(|error| io_error(raw_path, &error))?;
    temporary
        .as_file()
        .sync_all()
        .map_err(|error| io_error(raw_path, &error))?;
    path.revalidate()
        .map_err(|error| path_safety_error(raw_path, &error))?;
    temporary
        .persist(raw_path)
        .map_err(|error| io_error(raw_path, &error.error))?;
    path.revalidate()
        .map_err(|error| path_safety_error(raw_path, &error))?;
    sync_parent(raw_path)
}

fn validate_mode(path: &Path, mode: u32) -> Result<(), FileIoError> {
    if mode & !0o777 != 0 {
        return Err(FileIoError::new(
            FileIoErrorKind::InvalidMode,
            path,
            "mode must contain only ordinary Unix permission bits",
        ));
    }
    Ok(())
}

fn require_existing_file(path: &Path) -> Result<(), FileIoError> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.is_file() => Ok(()),
        Ok(_) => Err(FileIoError::new(
            FileIoErrorKind::WrongFileType,
            path,
            "path is not a regular file",
        )),
        Err(error) => Err(io_error(path, &error)),
    }
}

fn require_intent(path: &ConfinedPath, expected: PathIntent) -> Result<&Path, FileIoError> {
    let raw_path = path.path();
    if path.intent() != expected {
        return Err(FileIoError::new(
            FileIoErrorKind::InvalidPath,
            raw_path,
            format!("path requires {expected:?} intent"),
        ));
    }
    path.revalidate()
        .map_err(|error| path_safety_error(raw_path, &error))?;
    Ok(raw_path)
}

fn sync_parent(path: &Path) -> Result<(), FileIoError> {
    let parent = path.parent().ok_or_else(|| {
        FileIoError::new(FileIoErrorKind::InvalidPath, path, "path has no parent")
    })?;
    File::open(parent)
        .and_then(|directory| directory.sync_all())
        .map_err(|error| durability_error(path, &error))
}

fn wire_error(path: &Path, error: &KvError) -> FileIoError {
    FileIoError::new(FileIoErrorKind::InvalidWireFormat, path, error.to_string())
}

fn io_error(path: &Path, error: &io::Error) -> FileIoError {
    FileIoError::new(FileIoErrorKind::Io, path, error.to_string())
}

fn durability_error(path: &Path, error: &io::Error) -> FileIoError {
    FileIoError::new(FileIoErrorKind::Durability, path, error.to_string())
}

fn path_safety_error(path: &Path, error: &PathSafetyError) -> FileIoError {
    let kind = match error.kind() {
        PathSafetyErrorKind::Symlink => FileIoErrorKind::Symlink,
        PathSafetyErrorKind::NotDirectory | PathSafetyErrorKind::NotRegularFile => {
            FileIoErrorKind::WrongFileType
        }
        PathSafetyErrorKind::Missing | PathSafetyErrorKind::Io => FileIoErrorKind::Io,
        PathSafetyErrorKind::MissingRoot
        | PathSafetyErrorKind::NotAbsolute
        | PathSafetyErrorKind::Traversal
        | PathSafetyErrorKind::EscapesRoot
        | PathSafetyErrorKind::MultipleLinks
        | PathSafetyErrorKind::RootCleanup
        | PathSafetyErrorKind::InvalidTempPrefix
        | PathSafetyErrorKind::RootChanged => FileIoErrorKind::InvalidPath,
    };
    FileIoError::new(kind, error.path().unwrap_or(path), error.to_string())
}

#[cfg(test)]
mod tests {
    use super::{
        FileIoErrorKind, atomic_write_utf8, atomic_write_with, durability_error,
        guarded_update_env, read_utf8, rename_same_directory,
    };
    use crate::{PathIntent, PathSafetyErrorKind, TemporaryRoot};
    use std::{fs, io, io::Write, os::unix::fs::PermissionsExt, path::Path};

    #[test]
    fn atomic_write_publishes_exact_bytes_and_mode() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = temporary_root(&directory);
        let path = root
            .confine("state.env", PathIntent::Write)
            .expect("write path should confine");

        atomic_write_utf8(&path, "A=one\nB=two=2\n", 0o600).expect("write should succeed");

        assert_eq!(
            fs::read(path.path()).expect("file should read"),
            b"A=one\nB=two=2\n"
        );
        assert_eq!(
            fs::metadata(path.path())
                .expect("metadata should read")
                .permissions()
                .mode()
                & 0o777,
            0o600
        );
        assert_no_temporary_files(root.path());
    }

    #[test]
    fn failed_atomic_write_preserves_complete_old_destination() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = temporary_root(&directory);
        fs::write(root.path().join("state.env"), b"OLD=complete\n").expect("fixture should write");
        let path = root
            .confine("state.env", PathIntent::Write)
            .expect("write path should confine");

        let error = atomic_write_with(&path, 0o600, |file| {
            file.write_all(b"NEW=partial")?;
            Err(io::Error::other("injected failure"))
        })
        .expect_err("injected write should fail");

        assert_eq!(error.kind(), FileIoErrorKind::Io);
        assert_eq!(
            fs::read(path.path()).expect("old file should remain"),
            b"OLD=complete\n"
        );
        assert_no_temporary_files(root.path());
    }

    #[test]
    fn utf8_reads_fail_explicitly_and_paths_fail_closed() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = temporary_root(&directory);
        fs::write(root.path().join("invalid.txt"), [0xff]).expect("fixture should write");
        let invalid_read = root
            .confine("invalid.txt", PathIntent::Read)
            .expect("read path should confine");
        assert_eq!(
            read_utf8(&invalid_read)
                .expect_err("invalid UTF-8 should fail")
                .kind(),
            FileIoErrorKind::InvalidUtf8
        );
        let invalid_write = root
            .confine("invalid.txt", PathIntent::Write)
            .expect("write path should confine");
        assert_eq!(
            atomic_write_utf8(&invalid_read, "A=1\n", 0o600)
                .expect_err("read intent must not authorize a write")
                .kind(),
            FileIoErrorKind::InvalidPath
        );
        assert_eq!(
            root.confine("../escape.env", PathIntent::Write)
                .expect_err("parent traversal should fail")
                .kind(),
            PathSafetyErrorKind::EscapesRoot
        );
        assert_eq!(
            atomic_write_utf8(&invalid_write, "A=1\n", 0o1_000)
                .expect_err("special mode bits should fail")
                .kind(),
            FileIoErrorKind::InvalidMode
        );
    }

    #[test]
    fn symlinked_destinations_and_ancestors_are_rejected() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = temporary_root(&directory);
        let real = root.path().join("real");
        fs::create_dir(&real).expect("real directory should create");
        let linked = root.path().join("linked");
        std::os::unix::fs::symlink(&real, &linked).expect("symlink should create");

        let error = root
            .confine("linked/state.env", PathIntent::Write)
            .expect_err("symlinked ancestor should fail");
        assert_eq!(error.kind(), PathSafetyErrorKind::Symlink);
        assert!(!real.join("state.env").exists());

        let target = root.path().join("target");
        fs::write(&target, b"unchanged").expect("target should write");
        let destination = root.path().join("destination");
        std::os::unix::fs::symlink(&target, &destination).expect("destination link should create");
        let error = root
            .confine("destination", PathIntent::Write)
            .expect_err("symlinked destination should fail");
        assert_eq!(error.kind(), PathSafetyErrorKind::Symlink);
        assert_eq!(fs::read(&target).expect("target should read"), b"unchanged");

        let swapped = root
            .confine("swapped", PathIntent::Write)
            .expect("missing write destination should confine");
        std::os::unix::fs::symlink(&target, swapped.path()).expect("swap link should create");
        let error = atomic_write_utf8(&swapped, "changed", 0o600)
            .expect_err("operation must revalidate a previously confined path");
        assert_eq!(error.kind(), FileIoErrorKind::Symlink);
        assert_eq!(fs::read(&target).expect("target should read"), b"unchanged");
    }

    #[test]
    fn same_directory_rename_replaces_whole_destination() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = temporary_root(&directory);
        fs::write(root.path().join("source"), b"new").expect("source should write");
        fs::write(root.path().join("destination"), b"old").expect("destination should write");
        let source = root
            .confine("source", PathIntent::Write)
            .expect("source should confine");
        let destination = root
            .confine("destination", PathIntent::Write)
            .expect("destination should confine");

        rename_same_directory(&source, &destination).expect("rename should succeed");

        assert_eq!(
            fs::read(destination.path()).expect("destination should read"),
            b"new"
        );
        assert!(!source.path().exists());
    }

    #[test]
    fn guarded_env_update_is_exact_and_preserves_destination_on_rejection() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = temporary_root(&directory);
        fs::write(root.path().join("state.env"), b"B=old\nA=keep\n").expect("fixture should write");
        let path = root
            .confine("state.env", PathIntent::Write)
            .expect("write path should confine");

        guarded_update_env(&path, &[("B", "new"), ("C", "three")], &["B", "C"], 0o600)
            .expect("guarded update should succeed");
        assert_eq!(
            fs::read(path.path()).expect("updated file should read"),
            include_bytes!("../../../fixtures/rust-io/env-update.golden")
        );
        let before = fs::read(path.path()).expect("updated fixture should read");
        let error = guarded_update_env(&path, &[("B", "x\nFORGED=y")], &["B"], 0o600)
            .expect_err("line-forging update should fail");
        assert_eq!(error.kind(), FileIoErrorKind::InvalidWireFormat);
        assert_eq!(
            fs::read(path.path()).expect("old file should remain"),
            before
        );
    }

    #[test]
    fn guarded_env_update_rejects_malformed_existing_state() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = temporary_root(&directory);
        fs::write(root.path().join("state.env"), b"A=one\nmalformed\n")
            .expect("fixture should write");
        let path = root
            .confine("state.env", PathIntent::Write)
            .expect("write path should confine");

        let error = guarded_update_env(&path, &[("A", "two")], &["A"], 0o600)
            .expect_err("malformed state should fail");

        assert_eq!(error.kind(), FileIoErrorKind::InvalidWireFormat);
        assert_eq!(
            fs::read(path.path()).expect("old file should remain"),
            b"A=one\nmalformed\n"
        );
    }

    #[test]
    fn post_publication_sync_failures_have_a_distinct_durability_class() {
        let path = Path::new("/tmp/state.env");
        let error = durability_error(path, &io::Error::other("injected directory sync failure"));

        assert_eq!(error.kind(), FileIoErrorKind::Durability);
        assert_eq!(error.path(), path);
    }

    fn assert_no_temporary_files(directory: &Path) {
        let entries = fs::read_dir(directory)
            .expect("directory should read")
            .map(|entry| entry.expect("entry should read").file_name())
            .filter(|name| name.to_string_lossy().ends_with(".tmp"))
            .collect::<Vec<_>>();
        assert!(entries.is_empty(), "temporary files remained: {entries:?}");
    }

    fn temporary_root(directory: &tempfile::TempDir) -> TemporaryRoot {
        TemporaryRoot::resolve(Some(directory.path())).expect("temporary root should resolve")
    }
}
