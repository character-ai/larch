//! UTF-8 filesystem and same-directory atomic publication adapters.

use larch_core::{EnvFile, KvError};
use std::{
    error::Error,
    fmt,
    fs::{self, File},
    io::{self, Write},
    os::unix::fs::PermissionsExt,
    path::{Component, Path, PathBuf},
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

/// Read a regular, non-symlinked file as strict UTF-8.
///
/// # Errors
///
/// Returns [`FileIoError`] for unsafe paths, I/O failures, or invalid UTF-8.
pub fn read_utf8(path: &Path) -> Result<String, FileIoError> {
    validate_absolute(path)?;
    validate_ancestors(path)?;
    validate_regular_destination(path, false)?;
    let bytes = fs::read(path).map_err(|error| io_error(path, &error))?;
    String::from_utf8(bytes)
        .map_err(|error| FileIoError::new(FileIoErrorKind::InvalidUtf8, path, error.to_string()))
}

/// Atomically publish UTF-8 text from a temporary file in the destination directory.
///
/// The parent must already exist. The temporary file is flushed and synced before
/// rename. A pre-publication failure leaves the prior destination untouched. A
/// [`FileIoErrorKind::Durability`] failure means the complete new destination is
/// visible but its directory entry could not be confirmed durable.
///
/// # Errors
///
/// Returns [`FileIoError`] for unsafe paths or any failed filesystem operation.
pub fn atomic_write_utf8(path: &Path, text: &str, mode: u32) -> Result<(), FileIoError> {
    atomic_write_with(path, mode, |file| file.write_all(text.as_bytes()))
}

/// Rename a regular file over a same-directory destination.
///
/// # Errors
///
/// Returns [`FileIoError`] if either path is unsafe, the source is not regular,
/// or the paths do not share one lexical parent. [`FileIoErrorKind::Durability`]
/// means the rename completed but its directory entry could not be synced.
pub fn rename_same_directory(source: &Path, destination: &Path) -> Result<(), FileIoError> {
    validate_absolute(source)?;
    validate_absolute(destination)?;
    if source.parent() != destination.parent() {
        return Err(FileIoError::new(
            FileIoErrorKind::InvalidPath,
            destination,
            "atomic rename requires one directory",
        ));
    }
    validate_ancestors(source)?;
    validate_ancestors(destination)?;
    validate_regular_destination(source, false)?;
    validate_regular_destination(destination, true)?;
    fs::rename(source, destination).map_err(|error| io_error(destination, &error))?;
    sync_parent(destination)
}

/// Strictly read, allowlist-update, and atomically rewrite an environment file.
///
/// A missing destination starts empty. Any invalid existing record or update
/// aborts before publication, leaving the destination unchanged.
///
/// # Errors
///
/// Returns [`FileIoError`] for unsafe paths, malformed state, or publication failure.
pub fn guarded_update_env(
    path: &Path,
    updates: &[(&str, &str)],
    allowed_keys: &[&str],
    mode: u32,
) -> Result<(), FileIoError> {
    validate_absolute(path)?;
    validate_ancestors(path)?;
    let mut env = match fs::symlink_metadata(path) {
        Ok(_) => EnvFile::parse(&read_utf8(path)?).map_err(|error| wire_error(path, &error))?,
        Err(error) if error.kind() == io::ErrorKind::NotFound => EnvFile::empty(),
        Err(error) => return Err(io_error(path, &error)),
    };
    env.apply_guarded(updates, allowed_keys)
        .map_err(|error| wire_error(path, &error))?;
    let rendered = env.render().map_err(|error| wire_error(path, &error))?;
    atomic_write_utf8(path, &rendered, mode)
}

fn atomic_write_with(
    path: &Path,
    mode: u32,
    write: impl FnOnce(&mut File) -> io::Result<()>,
) -> Result<(), FileIoError> {
    validate_absolute(path)?;
    validate_mode(path, mode)?;
    validate_ancestors(path)?;
    validate_regular_destination(path, true)?;
    let parent = path.parent().ok_or_else(|| {
        FileIoError::new(FileIoErrorKind::InvalidPath, path, "path has no parent")
    })?;
    let name = path
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or_else(|| {
            FileIoError::new(
                FileIoErrorKind::InvalidPath,
                path,
                "path has no UTF-8 filename",
            )
        })?;
    let mut temporary = tempfile::Builder::new()
        .prefix(&format!(".{name}."))
        .suffix(".tmp")
        .tempfile_in(parent)
        .map_err(|error| io_error(path, &error))?;
    temporary
        .as_file()
        .set_permissions(fs::Permissions::from_mode(mode))
        .map_err(|error| io_error(path, &error))?;
    write(temporary.as_file_mut()).map_err(|error| io_error(path, &error))?;
    temporary
        .as_file_mut()
        .flush()
        .map_err(|error| io_error(path, &error))?;
    temporary
        .as_file()
        .sync_all()
        .map_err(|error| io_error(path, &error))?;
    validate_ancestors(path)?;
    validate_regular_destination(path, true)?;
    temporary
        .persist(path)
        .map_err(|error| io_error(path, &error.error))?;
    validate_regular_destination(path, false)?;
    sync_parent(path)
}

fn validate_absolute(path: &Path) -> Result<(), FileIoError> {
    if !path.is_absolute()
        || path.file_name().is_none()
        || path
            .components()
            .any(|component| matches!(component, Component::CurDir | Component::ParentDir))
    {
        return Err(FileIoError::new(
            FileIoErrorKind::InvalidPath,
            path,
            "path must be absolute, normalized, and name a file",
        ));
    }
    Ok(())
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

fn validate_ancestors(path: &Path) -> Result<(), FileIoError> {
    let parent = path.parent().ok_or_else(|| {
        FileIoError::new(FileIoErrorKind::InvalidPath, path, "path has no parent")
    })?;
    for ancestor in parent.ancestors() {
        let metadata = fs::symlink_metadata(ancestor).map_err(|error| io_error(path, &error))?;
        if metadata.file_type().is_symlink() {
            return Err(FileIoError::new(
                FileIoErrorKind::Symlink,
                path,
                format!("symlinked path component: {}", ancestor.display()),
            ));
        }
        if !metadata.is_dir() {
            return Err(FileIoError::new(
                FileIoErrorKind::WrongFileType,
                path,
                format!("path component is not a directory: {}", ancestor.display()),
            ));
        }
    }
    Ok(())
}

fn validate_regular_destination(path: &Path, missing_allowed: bool) -> Result<(), FileIoError> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() => Err(FileIoError::new(
            FileIoErrorKind::Symlink,
            path,
            "refusing symlinked file",
        )),
        Ok(metadata) if !metadata.is_file() => Err(FileIoError::new(
            FileIoErrorKind::WrongFileType,
            path,
            "path is not a regular file",
        )),
        Ok(_) => Ok(()),
        Err(error) if missing_allowed && error.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(io_error(path, &error)),
    }
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

#[cfg(test)]
mod tests {
    use super::{
        FileIoErrorKind, atomic_write_utf8, atomic_write_with, durability_error,
        guarded_update_env, read_utf8, rename_same_directory,
    };
    use std::{
        fs, io,
        io::Write,
        os::unix::fs::PermissionsExt,
        path::{Path, PathBuf},
    };

    #[test]
    fn atomic_write_publishes_exact_bytes_and_mode() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = canonical_temp_root(&directory);
        let path = root.join("state.env");

        atomic_write_utf8(&path, "A=one\nB=two=2\n", 0o600).expect("write should succeed");

        assert_eq!(
            fs::read(&path).expect("file should read"),
            b"A=one\nB=two=2\n"
        );
        assert_eq!(
            fs::metadata(&path)
                .expect("metadata should read")
                .permissions()
                .mode()
                & 0o777,
            0o600
        );
        assert_no_temporary_files(&root);
    }

    #[test]
    fn failed_atomic_write_preserves_complete_old_destination() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = canonical_temp_root(&directory);
        let path = root.join("state.env");
        fs::write(&path, b"OLD=complete\n").expect("fixture should write");

        let error = atomic_write_with(&path, 0o600, |file| {
            file.write_all(b"NEW=partial")?;
            Err(io::Error::other("injected failure"))
        })
        .expect_err("injected write should fail");

        assert_eq!(error.kind(), FileIoErrorKind::Io);
        assert_eq!(
            fs::read(&path).expect("old file should remain"),
            b"OLD=complete\n"
        );
        assert_no_temporary_files(&root);
    }

    #[test]
    fn utf8_reads_fail_explicitly_and_paths_fail_closed() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let invalid = canonical_temp_root(&directory).join("invalid.txt");
        fs::write(&invalid, [0xff]).expect("fixture should write");
        assert_eq!(
            read_utf8(&invalid)
                .expect_err("invalid UTF-8 should fail")
                .kind(),
            FileIoErrorKind::InvalidUtf8
        );
        assert_eq!(
            atomic_write_utf8(Path::new("relative.env"), "A=1\n", 0o600)
                .expect_err("relative path should fail")
                .kind(),
            FileIoErrorKind::InvalidPath
        );
        assert_eq!(
            atomic_write_utf8(Path::new("/tmp/../tmp/state.env"), "A=1\n", 0o600)
                .expect_err("parent traversal should fail")
                .kind(),
            FileIoErrorKind::InvalidPath
        );
        assert_eq!(
            atomic_write_utf8(&invalid, "A=1\n", 0o1_000)
                .expect_err("special mode bits should fail")
                .kind(),
            FileIoErrorKind::InvalidMode
        );
    }

    #[test]
    fn symlinked_destinations_and_ancestors_are_rejected() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = canonical_temp_root(&directory);
        let real = root.join("real");
        fs::create_dir(&real).expect("real directory should create");
        let linked = root.join("linked");
        std::os::unix::fs::symlink(&real, &linked).expect("symlink should create");
        let path = linked.join("state.env");

        let error =
            atomic_write_utf8(&path, "A=1\n", 0o600).expect_err("symlinked ancestor should fail");
        assert_eq!(error.kind(), FileIoErrorKind::Symlink);
        assert!(!real.join("state.env").exists());

        let target = root.join("target");
        fs::write(&target, b"unchanged").expect("target should write");
        let destination = root.join("destination");
        std::os::unix::fs::symlink(&target, &destination).expect("destination link should create");
        let error = atomic_write_utf8(&destination, "changed", 0o600)
            .expect_err("symlinked destination should fail");
        assert_eq!(error.kind(), FileIoErrorKind::Symlink);
        assert_eq!(fs::read(&target).expect("target should read"), b"unchanged");
    }

    #[test]
    fn same_directory_rename_replaces_whole_destination() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let root = canonical_temp_root(&directory);
        let source = root.join("source");
        let destination = root.join("destination");
        fs::write(&source, b"new").expect("source should write");
        fs::write(&destination, b"old").expect("destination should write");

        rename_same_directory(&source, &destination).expect("rename should succeed");

        assert_eq!(
            fs::read(&destination).expect("destination should read"),
            b"new"
        );
        assert!(!source.exists());
    }

    #[test]
    fn guarded_env_update_is_exact_and_preserves_destination_on_rejection() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let path = canonical_temp_root(&directory).join("state.env");
        fs::write(&path, b"B=old\nA=keep\n").expect("fixture should write");

        guarded_update_env(&path, &[("B", "new"), ("C", "three")], &["B", "C"], 0o600)
            .expect("guarded update should succeed");
        assert_eq!(
            fs::read(&path).expect("updated file should read"),
            include_bytes!("../../../fixtures/rust-io/env-update.golden")
        );
        let before = fs::read(&path).expect("updated fixture should read");
        let error = guarded_update_env(&path, &[("B", "x\nFORGED=y")], &["B"], 0o600)
            .expect_err("line-forging update should fail");
        assert_eq!(error.kind(), FileIoErrorKind::InvalidWireFormat);
        assert_eq!(fs::read(&path).expect("old file should remain"), before);
    }

    #[test]
    fn guarded_env_update_rejects_malformed_existing_state() {
        let directory = tempfile::tempdir().expect("tempdir should create");
        let path = canonical_temp_root(&directory).join("state.env");
        fs::write(&path, b"A=one\nmalformed\n").expect("fixture should write");

        let error = guarded_update_env(&path, &[("A", "two")], &["A"], 0o600)
            .expect_err("malformed state should fail");

        assert_eq!(error.kind(), FileIoErrorKind::InvalidWireFormat);
        assert_eq!(
            fs::read(&path).expect("old file should remain"),
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

    fn canonical_temp_root(directory: &tempfile::TempDir) -> PathBuf {
        directory
            .path()
            .canonicalize()
            .expect("temporary directory should canonicalize")
    }
}
