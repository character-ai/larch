//! UTF-8 filesystem and same-directory atomic publication adapters.

use crate::{ConfinedPath, PathIntent, PathSafetyError, PathSafetyErrorKind, TemporaryRoot};
use larch_core::{CommentPolicy, EnvFile, KvDocument, KvError, ParseOptions};
use std::{
    error::Error,
    fmt,
    fs::{self, File},
    io::{self, Read as _, Write},
    os::unix::fs::PermissionsExt,
    path::{Path, PathBuf},
};

#[cfg(unix)]
use std::os::unix::fs::OpenOptionsExt as _;

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

/// Open a regular file confined with [`PathIntent::Read`] without following symlinks.
///
/// # Errors
///
/// Returns [`FileIoError`] for unsafe paths or I/O failures.
pub fn open_confined_read(path: &ConfinedPath) -> Result<File, FileIoError> {
    let raw_path = require_intent(path, PathIntent::Read)?;
    let mut options = File::options();
    options.read(true);
    #[cfg(unix)]
    options.custom_flags(nix::libc::O_NOFOLLOW);
    options
        .open(raw_path)
        .map_err(|error| io_error(raw_path, &error))
}

/// Read a regular file confined with [`PathIntent::Read`] as strict UTF-8.
///
/// # Errors
///
/// Returns [`FileIoError`] for unsafe paths, I/O failures, or invalid UTF-8.
pub fn read_utf8(path: &ConfinedPath) -> Result<String, FileIoError> {
    let raw_path = path.path();
    let mut file = open_confined_read(path)?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)
        .map_err(|error| io_error(raw_path, &error))?;
    String::from_utf8(bytes).map_err(|error| {
        FileIoError::new(FileIoErrorKind::InvalidUtf8, raw_path, error.to_string())
    })
}

/// Read an arbitrary legacy CLI input file with UTF-8 replacement semantics.
///
/// Missing and non-regular paths return `None`, matching `Path.is_file()`.
/// This compatibility reader intentionally follows symlinks; state-bearing
/// writes and trusted reads must use [`ConfinedPath`] instead.
///
/// # Errors
///
/// Returns [`FileIoError`] when metadata or file reading fails.
pub fn read_optional_utf8_lossy(path: &Path) -> Result<Option<String>, FileIoError> {
    match fs::metadata(path) {
        Ok(metadata) if metadata.is_file() => fs::read(path)
            .map(|bytes| Some(String::from_utf8_lossy(&bytes).into_owned()))
            .map_err(|error| io_error(path, &error)),
        Ok(_) => Ok(None),
        Err(error)
            if matches!(
                error.kind(),
                io::ErrorKind::NotFound | io::ErrorKind::NotADirectory
            ) =>
        {
            Ok(None)
        }
        Err(error) => Err(io_error(path, &error)),
    }
}

/// Remove a file, treating an already-absent path as success.
///
/// # Errors
///
/// Returns [`FileIoError`] when removal fails for any reason other than absence.
pub fn remove_optional_file(path: &Path) -> Result<(), FileIoError> {
    absent_is_success(fs::remove_file(path)).map_err(|error| io_error(path, &error))
}

/// Treat an already-absent filesystem target as a successful mutation.
pub fn absent_is_success(result: io::Result<()>) -> io::Result<()> {
    result.or_else(|error| {
        if error.kind() == io::ErrorKind::NotFound {
            Ok(())
        } else {
            Err(error)
        }
    })
}

/// Read a legacy session KV file and reject every carriage return.
///
/// # Errors
///
/// Returns [`FileIoError`] for I/O failure or carriage-return injection.
pub fn read_session_kv_text(path: &Path) -> Result<Option<String>, FileIoError> {
    let text = read_optional_utf8_lossy(path)?;
    if text.as_ref().is_some_and(|value| value.contains('\r')) {
        return Err(FileIoError::new(
            FileIoErrorKind::InvalidWireFormat,
            path,
            format!(
                "session env file contains carriage return: {}",
                path.display()
            ),
        ));
    }
    Ok(text)
}

/// Read a session KV file with comment skipping and last-key-wins semantics.
///
/// # Errors
///
/// Returns [`FileIoError`] for I/O failure or carriage-return injection.
pub fn read_kv_raw(path: &Path) -> Result<Vec<(String, String)>, FileIoError> {
    let Some(text) = read_session_kv_text(path)? else {
        return Ok(Vec::new());
    };
    let mut options = ParseOptions::legacy();
    options.comments = CommentPolicy::Skip;
    let document = KvDocument::parse(&text, options).map_err(|error| wire_error(path, &error))?;
    let mut selected = Vec::new();
    for row in document.rows() {
        match selected.iter_mut().find(|(key, _value)| key == row.key()) {
            Some((_key, value)) => row.value().clone_into(value),
            None => selected.push((row.key().to_owned(), row.value().to_owned())),
        }
    }
    Ok(selected)
}

/// Read the first raw value for one key from a session KV file.
///
/// # Errors
///
/// Returns [`FileIoError`] for I/O failure or carriage-return injection.
pub fn read_first_raw_key(path: &Path, key: &str) -> Result<Option<String>, FileIoError> {
    let Some(text) = read_session_kv_text(path)? else {
        return Ok(None);
    };
    let document = KvDocument::parse(&text, ParseOptions::legacy())
        .map_err(|error| wire_error(path, &error))?;
    Ok(document
        .rows()
        .iter()
        .find(|row| row.key() == key)
        .map(|row| row.value().to_owned()))
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
    Ok(())
}

/// Atomically publish UTF-8 below a trusted temporary root.
///
/// When `create_parent` is true, missing parent directories are created as
/// private directories through [`TemporaryRoot::ensure_directory`].
///
/// # Errors
///
/// Returns [`FileIoError`] for unsafe paths, directory creation, or publication
/// failures.
pub fn atomic_write_utf8_in(
    root: &TemporaryRoot,
    target: &Path,
    text: &str,
    create_parent: bool,
    mode: u32,
) -> Result<(), FileIoError> {
    atomic_write_in_with(root, target, create_parent, mode, |file| {
        file.write_all(text.as_bytes())
    })
}

/// Atomically publish bytes below a validated temporary root.
///
/// # Errors
///
/// Returns [`FileIoError`] for unsafe paths, directory creation, or publication
/// failures.
pub fn atomic_write_bytes_in(
    root: &TemporaryRoot,
    target: &Path,
    bytes: &[u8],
    create_parent: bool,
    mode: u32,
) -> Result<(), FileIoError> {
    atomic_write_in_with(root, target, create_parent, mode, |file| {
        file.write_all(bytes)
    })
}

/// Testable rooted variant of [`atomic_write_utf8_in`].
///
/// # Errors
///
/// Returns [`FileIoError`] when the target is unsafe, parent creation fails,
/// the writer fails, or atomic publication cannot be completed durably.
pub fn atomic_write_in_with(
    root: &TemporaryRoot,
    target: &Path,
    create_parent: bool,
    mode: u32,
    write: impl FnOnce(&mut File) -> io::Result<()>,
) -> Result<(), FileIoError> {
    let joined = if target.is_absolute() {
        target.to_path_buf()
    } else {
        root.path().join(target)
    };
    if create_parent {
        let parent = joined.parent().ok_or_else(|| {
            FileIoError::new(FileIoErrorKind::InvalidPath, &joined, "path has no parent")
        })?;
        root.ensure_directory(parent)
            .map_err(|error| path_safety_error(parent, &error))?;
    }
    let confined = root
        .confine(&joined, PathIntent::Write)
        .map_err(|error| path_safety_error(&joined, &error))?;
    atomic_write_with(&confined, mode, write)
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

pub fn io_error(path: &Path, error: &io::Error) -> FileIoError {
    FileIoError::new(FileIoErrorKind::Io, path, error.to_string())
}

fn durability_error(path: &Path, error: &io::Error) -> FileIoError {
    FileIoError::new(FileIoErrorKind::Durability, path, error.to_string())
}

pub fn path_safety_error(path: &Path, error: &PathSafetyError) -> FileIoError {
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
        FileIoErrorKind, atomic_write_utf8, atomic_write_utf8_in, atomic_write_with,
        durability_error, guarded_update_env, open_confined_read, read_first_raw_key, read_kv_raw,
        read_session_kv_text, read_utf8, rename_same_directory,
    };
    use crate::{PathIntent, PathSafetyErrorKind, TemporaryRoot};
    use std::{
        fs, io,
        io::Write,
        os::unix::fs::PermissionsExt,
        path::Path,
        sync::{
            Arc,
            atomic::{AtomicUsize, Ordering},
        },
        thread,
    };

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

    #[cfg(unix)]
    #[test]
    fn confined_reads_revalidate_before_opening() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = temporary_root(&directory);
        let source = root.path().join("source");
        let target = root.path().join("target");
        fs::write(&source, b"safe").expect("source fixture");
        fs::write(&target, b"target").expect("target fixture");
        let confined = root
            .confine("source", PathIntent::Read)
            .expect("source should confine");
        fs::remove_file(&source).expect("remove source");
        std::os::unix::fs::symlink(&target, &source).expect("swap source with symlink");

        assert_eq!(
            open_confined_read(&confined)
                .expect_err("swapped symlink must fail")
                .kind(),
            FileIoErrorKind::Symlink
        );
        assert_eq!(fs::read(&target).expect("target unchanged"), b"target");
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

    #[test]
    fn session_read_primitives_preserve_duplicate_comment_and_replacement_rules() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let path = directory.path().join("state.env");
        fs::write(&path, b"#COMMENT=value\nA=first\nA=last\nBAD=\xff\n")
            .expect("fixture should write");

        let raw = read_kv_raw(&path).expect("raw KV should read");
        assert_eq!(
            raw,
            [
                ("A".to_owned(), "last".to_owned()),
                ("BAD".to_owned(), "\u{fffd}".to_owned())
            ]
        );
        assert_eq!(
            read_first_raw_key(&path, "A").expect("first key should read"),
            Some("first".to_owned())
        );
        fs::write(&path, b"A=one\r\n").expect("CR fixture should write");
        assert_eq!(
            read_session_kv_text(&path)
                .expect_err("carriage returns should fail")
                .kind(),
            FileIoErrorKind::InvalidWireFormat
        );
    }

    #[test]
    fn rooted_atomic_write_creates_private_parents_and_files() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = temporary_root(&directory);
        let target = root.path().join("nested/state.env");

        atomic_write_utf8_in(&root, &target, "A=one\n", true, 0o600)
            .expect("rooted write should succeed");

        assert_eq!(fs::read(&target).expect("state should read"), b"A=one\n");
        assert_eq!(
            fs::metadata(target.parent().expect("target parent"))
                .expect("parent metadata")
                .permissions()
                .mode()
                & 0o777,
            0o700
        );
        assert_eq!(
            fs::metadata(&target)
                .expect("file metadata")
                .permissions()
                .mode()
                & 0o777,
            0o600
        );
    }

    #[test]
    fn concurrent_atomic_writers_never_publish_partial_or_interleaved_bytes() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = temporary_root(&directory);
        let target = root.path().join("state.env");
        let values = Arc::new(vec![
            "A=aaaaaaaaaaaaaaaa\n".to_owned(),
            "B=bbbbbbbbbbbbbbbb\n".to_owned(),
            "C=cccccccccccccccc\n".to_owned(),
            "D=dddddddddddddddd\n".to_owned(),
        ]);
        fs::write(&target, values[0].as_bytes()).expect("initial value should write");
        let active = Arc::new(AtomicUsize::new(values.len()));
        let reader_target = target.clone();
        let reader_values = Arc::clone(&values);
        let reader_active = Arc::clone(&active);
        let reader = thread::spawn(move || {
            while reader_active.load(Ordering::Acquire) != 0 {
                let observed =
                    fs::read_to_string(&reader_target).expect("published value should read");
                assert!(
                    reader_values.contains(&observed),
                    "partial value: {observed:?}"
                );
            }
        });
        let writers = values
            .iter()
            .map(|value| {
                let value = value.clone();
                let writer_root = root.clone();
                let writer_target = target.clone();
                let writer_active = Arc::clone(&active);
                thread::spawn(move || {
                    for _ in 0..20 {
                        atomic_write_utf8_in(&writer_root, &writer_target, &value, false, 0o600)
                            .expect("concurrent write should succeed");
                    }
                    writer_active.fetch_sub(1, Ordering::Release);
                })
            })
            .collect::<Vec<_>>();
        for writer in writers {
            writer.join().expect("writer should not panic");
        }
        reader.join().expect("reader should not panic");
        let final_value = fs::read_to_string(&target).expect("final value should read");
        assert!(values.contains(&final_value));
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
