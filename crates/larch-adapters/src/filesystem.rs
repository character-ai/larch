//! Trusted roots, confined paths, and owned temporary resources.
//!
//! Root constructors require a caller-selected absolute path. Repository and
//! plugin roots resolve a symlinked input once, then expose only the canonical
//! directory. Temporary roots reject a symlink at the supplied root itself;
//! platform ancestor aliases are canonicalized. Confined
//! reads, writes, cleanup targets, and cache targets reject symlinks at every
//! existing component. Callers must revalidate a [`ConfinedPath`] at the point
//! of use to catch changes after initial validation.

use std::{
    env,
    error::Error,
    fmt,
    fs::{self, File},
    io,
    path::{Component, Path, PathBuf},
};

use tempfile::{Builder, NamedTempFile, TempDir};

const TEMP_PREFIX_MAX_BYTES: usize = 64;

/// The operation for which a confined path was validated.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum PathIntent {
    /// Read an existing regular file.
    Read,
    /// Create or replace a regular file below an existing directory.
    Write,
    /// Remove an existing regular file or directory, but never the root.
    Cleanup,
    /// Read or write an existing regular cache entry, or create a new one.
    Cache,
}

/// Stable categories for path-safety failures.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum PathSafetyErrorKind {
    /// No explicit root candidate was supplied.
    MissingRoot,
    /// A root or absolute candidate was relative.
    NotAbsolute,
    /// Lexical normalization would cross above the supplied path base.
    Traversal,
    /// A candidate lies outside its trusted root.
    EscapesRoot,
    /// A path component is a symbolic link.
    Symlink,
    /// A required path does not exist.
    Missing,
    /// A required directory is another file type.
    NotDirectory,
    /// A required regular file is another file type.
    NotRegularFile,
    /// A write or cache file has another hard link.
    MultipleLinks,
    /// Cleanup targeted the trusted root itself.
    RootCleanup,
    /// A temporary-resource prefix was unsafe.
    InvalidTempPrefix,
    /// The trusted root was replaced after resolution.
    RootChanged,
    /// The operating system rejected a filesystem operation.
    Io,
}

/// A typed, fail-closed path validation or filesystem failure.
#[derive(Debug)]
pub struct PathSafetyError {
    kind: PathSafetyErrorKind,
    path: Option<PathBuf>,
    operation: &'static str,
    source: Option<io::Error>,
}

impl PathSafetyError {
    fn new(kind: PathSafetyErrorKind, path: impl Into<Option<PathBuf>>) -> Self {
        Self {
            kind,
            path: path.into(),
            operation: "validate path",
            source: None,
        }
    }

    fn io(operation: &'static str, path: &Path, source: io::Error) -> Self {
        let kind = if source.kind() == io::ErrorKind::NotFound {
            PathSafetyErrorKind::Missing
        } else {
            PathSafetyErrorKind::Io
        };
        Self {
            kind,
            path: Some(path.to_path_buf()),
            operation,
            source: Some(source),
        }
    }

    /// Return the stable failure category.
    #[must_use]
    pub const fn kind(&self) -> PathSafetyErrorKind {
        self.kind
    }

    /// Return the path associated with the failure, when one exists.
    #[must_use]
    pub fn path(&self) -> Option<&Path> {
        self.path.as_deref()
    }
}

impl fmt::Display for PathSafetyError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        let detail = match self.kind {
            PathSafetyErrorKind::MissingRoot => "an explicit root is required",
            PathSafetyErrorKind::NotAbsolute => "path must be absolute",
            PathSafetyErrorKind::Traversal => "path traversal escapes its base",
            PathSafetyErrorKind::EscapesRoot => "path escapes its trusted root",
            PathSafetyErrorKind::Symlink => "symbolic links are not allowed",
            PathSafetyErrorKind::Missing => "required path is missing",
            PathSafetyErrorKind::NotDirectory => "path is not a directory",
            PathSafetyErrorKind::NotRegularFile => "path is not a regular file",
            PathSafetyErrorKind::MultipleLinks => "writable file has multiple hard links",
            PathSafetyErrorKind::RootCleanup => "the trusted root cannot be removed",
            PathSafetyErrorKind::InvalidTempPrefix => "temporary prefix is unsafe",
            PathSafetyErrorKind::RootChanged => "trusted root identity changed",
            PathSafetyErrorKind::Io => "filesystem operation failed",
        };
        match &self.path {
            Some(path) => write!(
                formatter,
                "{} for {}: {}",
                self.operation,
                path.display(),
                detail
            ),
            None => write!(formatter, "{}: {detail}", self.operation),
        }
    }
}

impl Error for PathSafetyError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        self.source.as_ref().map(|source| source as &dyn Error)
    }
}

#[derive(Clone, Debug, Eq, Hash, PartialEq)]
struct CanonicalRoot {
    path: PathBuf,
    identity: RootIdentity,
}

#[cfg(unix)]
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
struct RootIdentity {
    device: u64,
    inode: u64,
}

#[cfg(not(unix))]
#[derive(Clone, Debug, Eq, Hash, PartialEq)]
struct RootIdentity(PathBuf);

impl RootIdentity {
    #[cfg(unix)]
    fn capture(_path: &Path, metadata: &fs::Metadata) -> Self {
        use std::os::unix::fs::MetadataExt;

        Self {
            device: metadata.dev(),
            inode: metadata.ino(),
        }
    }

    #[cfg(not(unix))]
    fn capture(path: &Path, _metadata: &fs::Metadata) -> Self {
        Self(path.to_path_buf())
    }

    #[cfg(unix)]
    fn matches(&self, _path: &Path, metadata: &fs::Metadata) -> bool {
        use std::os::unix::fs::MetadataExt;

        self.device == metadata.dev() && self.inode == metadata.ino()
    }

    #[cfg(not(unix))]
    fn matches(&self, path: &Path, _metadata: &fs::Metadata) -> bool {
        fs::canonicalize(path).is_ok_and(|canonical| canonical == self.0)
    }
}

/// Compare an opened Unix descriptor's identity with visible path metadata.
///
/// Callers use this after opening a no-follow descriptor to reject a path that
/// was replaced between the open and the metadata lookup.
#[cfg(unix)]
#[must_use]
pub fn same_file_stat_metadata(stat: &nix::sys::stat::FileStat, metadata: &fs::Metadata) -> bool {
    use std::os::unix::fs::MetadataExt as _;

    i128::from(stat.st_dev) == i128::from(metadata.dev())
        && i128::from(stat.st_ino) == i128::from(metadata.ino())
}

impl CanonicalRoot {
    fn resolve(
        candidate: Option<&Path>,
        reject_input_symlinks: bool,
    ) -> Result<Self, PathSafetyError> {
        let candidate = candidate
            .ok_or_else(|| PathSafetyError::new(PathSafetyErrorKind::MissingRoot, None))?;
        if !candidate.is_absolute() {
            return Err(PathSafetyError::new(
                PathSafetyErrorKind::NotAbsolute,
                Some(candidate.to_path_buf()),
            ));
        }
        let normalized = normalize_path(candidate)?;
        if reject_input_symlinks {
            match fs::symlink_metadata(&normalized) {
                Ok(metadata) if metadata.file_type().is_symlink() => {
                    return Err(PathSafetyError::new(
                        PathSafetyErrorKind::Symlink,
                        Some(normalized),
                    ));
                }
                Ok(_) => {}
                Err(source) => {
                    return Err(PathSafetyError::io("inspect root", &normalized, source));
                }
            }
        }
        let canonical = fs::canonicalize(&normalized)
            .map_err(|source| PathSafetyError::io("resolve root", &normalized, source))?;
        let metadata = fs::symlink_metadata(&canonical)
            .map_err(|source| PathSafetyError::io("inspect root", &canonical, source))?;
        if !metadata.file_type().is_dir() {
            return Err(PathSafetyError::new(
                PathSafetyErrorKind::NotDirectory,
                Some(canonical),
            ));
        }
        let identity = RootIdentity::capture(&canonical, &metadata);
        Ok(Self {
            path: canonical,
            identity,
        })
    }

    fn path(&self) -> &Path {
        &self.path
    }

    fn revalidate(&self) -> Result<(), PathSafetyError> {
        let metadata = validate_root_path(self.path())?;
        if !self.identity.matches(self.path(), &metadata) {
            return Err(PathSafetyError::new(
                PathSafetyErrorKind::RootChanged,
                Some(self.path.clone()),
            ));
        }
        Ok(())
    }

    fn confine(
        &self,
        candidate: &Path,
        intent: PathIntent,
    ) -> Result<ConfinedPath, PathSafetyError> {
        let joined = if candidate.is_absolute() {
            candidate.to_path_buf()
        } else {
            self.path().join(candidate)
        };
        let path = normalize_path(&joined)?;
        if !path.starts_with(self.path()) {
            return Err(PathSafetyError::new(
                PathSafetyErrorKind::EscapesRoot,
                Some(path),
            ));
        }
        let confined = ConfinedPath {
            root: self.clone(),
            path,
            intent,
        };
        confined.revalidate()?;
        Ok(confined)
    }
}

macro_rules! root_type {
    ($name:ident, $reject_symlinks:literal, $description:literal) => {
        #[doc = $description]
        #[derive(Clone, Debug, Eq, Hash, PartialEq)]
        pub struct $name(CanonicalRoot);

        impl $name {
            /// Resolve a caller-selected absolute directory without an ambient fallback.
            ///
            /// # Errors
            ///
            /// Returns [`PathSafetyError`] when the candidate is absent, relative,
            /// missing, symlinked contrary to this root's policy, or not a directory.
            pub fn resolve(candidate: Option<&Path>) -> Result<Self, PathSafetyError> {
                CanonicalRoot::resolve(candidate, $reject_symlinks).map(Self)
            }

            /// Return the canonical root directory.
            #[must_use]
            pub fn path(&self) -> &Path {
                self.0.path()
            }

            /// Validate a path below this root for a specific use.
            ///
            /// # Errors
            ///
            /// Returns [`PathSafetyError`] when the path escapes, is missing when
            /// required, contains a symlink, or has the wrong file type.
            pub fn confine(
                &self,
                candidate: impl AsRef<Path>,
                intent: PathIntent,
            ) -> Result<ConfinedPath, PathSafetyError> {
                self.0.confine(candidate.as_ref(), intent)
            }
        }
    };
}

root_type!(
    RepositoryRoot,
    false,
    "A canonical, caller-selected consumer repository root."
);
root_type!(
    PluginRoot,
    false,
    "A canonical, caller-selected installed plugin root."
);
root_type!(
    TemporaryRoot,
    true,
    "A canonical, non-symlinked root owned for temporary and cache resources."
);

impl TemporaryRoot {
    /// Revalidate the root identity before a caller performs an unlink that
    /// intentionally targets a symlink.
    ///
    /// Symlink cleanup cannot use [`Self::confine`] because that method
    /// correctly rejects the symlink leaf. Callers must revalidate this root
    /// immediately before unlinking such a leaf instead.
    ///
    /// # Errors
    ///
    /// Returns [`PathSafetyError`] when the root was replaced or became
    /// unsafe since resolution.
    pub fn revalidate(&self) -> Result<(), PathSafetyError> {
        self.0.revalidate()
    }

    /// Create a private directory tree below this trusted root.
    ///
    /// Every existing and newly created component is checked without following
    /// symlinks. The root identity is revalidated before and after mutation.
    ///
    /// # Errors
    ///
    /// Returns [`PathSafetyError`] for escape, symlink, wrong-type, race, or I/O
    /// failures.
    pub fn ensure_directory(
        &self,
        candidate: impl AsRef<Path>,
    ) -> Result<PathBuf, PathSafetyError> {
        self.0.revalidate()?;
        let joined = if candidate.as_ref().is_absolute() {
            candidate.as_ref().to_path_buf()
        } else {
            self.path().join(candidate)
        };
        let directory = normalize_path(joined)?;
        let relative = directory.strip_prefix(self.path()).map_err(|_error| {
            PathSafetyError::new(PathSafetyErrorKind::EscapesRoot, Some(directory.clone()))
        })?;
        let mut current = self.path().to_path_buf();
        for component in relative.components() {
            current.push(component.as_os_str());
            match fs::symlink_metadata(&current) {
                Ok(metadata) if metadata.file_type().is_symlink() => {
                    return Err(PathSafetyError::new(
                        PathSafetyErrorKind::Symlink,
                        Some(current),
                    ));
                }
                Ok(metadata) if metadata.is_dir() => {}
                Ok(_) => {
                    return Err(PathSafetyError::new(
                        PathSafetyErrorKind::NotDirectory,
                        Some(current),
                    ));
                }
                Err(source) if source.kind() == io::ErrorKind::NotFound => {
                    let mut builder = fs::DirBuilder::new();
                    #[cfg(unix)]
                    {
                        use std::os::unix::fs::DirBuilderExt as _;

                        builder.mode(0o700);
                    }
                    match builder.create(&current) {
                        Ok(()) => {}
                        Err(error) if error.kind() == io::ErrorKind::AlreadyExists => {}
                        Err(error) => {
                            return Err(PathSafetyError::io(
                                "create trusted directory",
                                &current,
                                error,
                            ));
                        }
                    }
                    let metadata = fs::symlink_metadata(&current).map_err(|error| {
                        PathSafetyError::io("inspect created directory", &current, error)
                    })?;
                    if metadata.file_type().is_symlink() {
                        return Err(PathSafetyError::new(
                            PathSafetyErrorKind::Symlink,
                            Some(current),
                        ));
                    }
                    if !metadata.is_dir() {
                        return Err(PathSafetyError::new(
                            PathSafetyErrorKind::NotDirectory,
                            Some(current),
                        ));
                    }
                    #[cfg(unix)]
                    set_unix_permissions(&current, 0o700)?;
                }
                Err(source) => {
                    return Err(PathSafetyError::io(
                        "inspect trusted directory",
                        &current,
                        source,
                    ));
                }
            }
        }
        self.0.revalidate()?;
        Ok(directory)
    }
}

/// A normalized path whose containment, type, and symlink policy were checked.
///
/// Validation is a snapshot. Call [`Self::revalidate`] immediately before an
/// open, write, rename, or removal. APIs that can mutate or delete data should
/// accept this type instead of a raw [`Path`].
#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub struct ConfinedPath {
    root: CanonicalRoot,
    path: PathBuf,
    intent: PathIntent,
}

impl ConfinedPath {
    /// Return the normalized absolute path.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Return the trusted root used during validation.
    #[must_use]
    pub fn root(&self) -> &Path {
        self.root.path()
    }

    /// Return the use-specific validation policy.
    #[must_use]
    pub const fn intent(&self) -> PathIntent {
        self.intent
    }

    /// Re-run containment, symlink, existence, and file-type checks.
    ///
    /// # Errors
    ///
    /// Returns [`PathSafetyError`] when the live filesystem no longer matches
    /// the policy recorded by this value.
    pub fn revalidate(&self) -> Result<(), PathSafetyError> {
        validate_confined(self)
    }
}

/// An owned temporary directory revalidated and removed on drop or by
/// [`SecureTempDir::close`].
///
/// Prefer `close` when cleanup failures matter. If pre-cleanup revalidation
/// fails, automatic cleanup is disabled so an attacker-controlled replacement
/// is not removed.
#[derive(Debug)]
pub struct SecureTempDir {
    inner: TempDir,
    confined: ConfinedPath,
}

impl SecureTempDir {
    /// Create a mode-`0700` directory below an explicit temporary root.
    ///
    /// # Errors
    ///
    /// Returns [`PathSafetyError`] for an unsafe prefix, changed root, creation
    /// failure, or a post-creation confinement failure.
    pub fn create(root: &TemporaryRoot, prefix: &str) -> Result<Self, PathSafetyError> {
        validate_temp_prefix(prefix)?;
        root.0.revalidate()?;
        let mut inner = Builder::new()
            .prefix(prefix)
            .tempdir_in(root.path())
            .map_err(|source| {
                PathSafetyError::io("create temporary directory", root.path(), source)
            })?;
        #[cfg(unix)]
        set_unix_permissions(inner.path(), 0o700)?;
        let confined = match root.confine(inner.path(), PathIntent::Cleanup) {
            Ok(confined) => confined,
            Err(error) => {
                inner.disable_cleanup(true);
                return Err(error);
            }
        };
        Ok(Self { inner, confined })
    }

    /// Return the owned directory path.
    #[must_use]
    pub fn path(&self) -> &Path {
        self.inner.path()
    }

    /// Keep this verified directory after the handle drops.
    ///
    /// The directory is revalidated at the persistence boundary.  A failed
    /// revalidation leaves cleanup enabled only when it can still be proven
    /// safe by [`Drop`]; otherwise the replacement is left for inspection.
    ///
    /// # Errors
    ///
    /// Returns [`PathSafetyError`] when the owned directory or its root changed
    /// before it could become a durable session resource.
    pub fn keep(mut self) -> Result<PathBuf, PathSafetyError> {
        self.confined.revalidate()?;
        let path = self.inner.path().to_path_buf();
        self.inner.disable_cleanup(true);
        Ok(path)
    }

    /// Revalidate and remove the owned directory now.
    ///
    /// # Errors
    ///
    /// Returns [`PathSafetyError`] when validation or recursive cleanup fails.
    /// A validation failure disables automatic cleanup and leaves the path for
    /// an operator to inspect.
    pub fn close(mut self) -> Result<(), PathSafetyError> {
        if let Err(error) = self.confined.revalidate() {
            self.inner.disable_cleanup(true);
            return Err(error);
        }
        let path = self.inner.path().to_path_buf();
        drop(self);
        verify_removed(&path, "remove temporary directory")
    }
}

impl Drop for SecureTempDir {
    fn drop(&mut self) {
        if self.confined.revalidate().is_err() {
            self.inner.disable_cleanup(true);
        }
    }
}

/// An owned temporary regular file revalidated and removed on drop or by
/// [`SecureTempFile::close`].
///
/// Files are mode `0600` on Unix. A validation failure before explicit cleanup
/// disables automatic cleanup and leaves the path for inspection.
#[derive(Debug)]
pub struct SecureTempFile {
    inner: NamedTempFile,
    confined: ConfinedPath,
}

impl SecureTempFile {
    /// Create a private regular file below an explicit temporary root.
    ///
    /// # Errors
    ///
    /// Returns [`PathSafetyError`] for an unsafe prefix, changed root, creation
    /// failure, or a post-creation confinement failure.
    pub fn create(root: &TemporaryRoot, prefix: &str) -> Result<Self, PathSafetyError> {
        validate_temp_prefix(prefix)?;
        root.0.revalidate()?;
        let mut inner = Builder::new()
            .prefix(prefix)
            .tempfile_in(root.path())
            .map_err(|source| PathSafetyError::io("create temporary file", root.path(), source))?;
        #[cfg(unix)]
        set_unix_permissions(inner.path(), 0o600)?;
        let confined = match root.confine(inner.path(), PathIntent::Cleanup) {
            Ok(confined) => confined,
            Err(error) => {
                inner.disable_cleanup(true);
                return Err(error);
            }
        };
        Ok(Self { inner, confined })
    }

    /// Return the owned file path.
    #[must_use]
    pub fn path(&self) -> &Path {
        self.inner.path()
    }

    /// Borrow the open private file.
    #[must_use]
    pub fn file(&self) -> &File {
        self.inner.as_file()
    }

    /// Mutably borrow the open private file.
    pub fn file_mut(&mut self) -> &mut File {
        self.inner.as_file_mut()
    }

    /// Revalidate and remove the owned file now.
    ///
    /// # Errors
    ///
    /// Returns [`PathSafetyError`] when validation or cleanup fails. A
    /// validation failure disables automatic cleanup.
    pub fn close(mut self) -> Result<(), PathSafetyError> {
        if let Err(error) = self.confined.revalidate() {
            self.inner.disable_cleanup(true);
            return Err(error);
        }
        let path = self.inner.path().to_path_buf();
        drop(self);
        verify_removed(&path, "remove temporary file")
    }
}

impl Drop for SecureTempFile {
    fn drop(&mut self) {
        if self.confined.revalidate().is_err() {
            self.inner.disable_cleanup(true);
        }
    }
}

/// Normalize an absolute or relative path without consulting the process cwd.
///
/// The function removes `.` components and resolves `..` components. It rejects
/// a `..` that would cross above the supplied relative base or filesystem root.
/// Native platform component rules apply: for example, `\` is a normal filename
/// byte on Unix and a separator on Windows.
///
/// # Errors
///
/// Returns [`PathSafetyError`] when normalization would traverse above the base.
pub fn normalize_path(path: impl AsRef<Path>) -> Result<PathBuf, PathSafetyError> {
    let path = path.as_ref();
    let mut normalized = PathBuf::new();
    let mut normal_components = 0_usize;
    for component in path.components() {
        match component {
            Component::Prefix(_) | Component::RootDir => normalized.push(component.as_os_str()),
            Component::CurDir => {}
            Component::Normal(value) => {
                normalized.push(value);
                normal_components += 1;
            }
            Component::ParentDir => {
                if normal_components == 0 {
                    return Err(PathSafetyError::new(
                        PathSafetyErrorKind::Traversal,
                        Some(path.to_path_buf()),
                    ));
                }
                let removed = normalized.pop();
                debug_assert!(removed, "a counted normal component must be removable");
                normal_components -= 1;
            }
        }
    }
    if normalized.as_os_str().is_empty() {
        normalized.push(".");
    }
    Ok(normalized)
}

/// Resolve existing symlinks while permitting a missing final suffix.
///
/// # Errors
///
/// Returns [`PathSafetyError`] when no existing ancestor can be resolved or an
/// operating-system lookup fails.
pub fn resolve_allow_missing(path: impl AsRef<Path>) -> Result<PathBuf, PathSafetyError> {
    let supplied = path.as_ref();
    let absolute = if supplied.is_absolute() {
        supplied.to_path_buf()
    } else {
        env::current_dir()
            .map_err(|source| PathSafetyError::io("resolve current directory", supplied, source))?
            .join(supplied)
    };
    let mut existing = absolute.as_path();
    let mut suffix = Vec::new();
    let mut second_pass = false;
    loop {
        match fs::symlink_metadata(existing) {
            Ok(metadata) => {
                let mut resolved = match fs::canonicalize(existing) {
                    Ok(path) => path,
                    Err(source)
                        if source.kind() == io::ErrorKind::NotFound
                            && metadata.file_type().is_symlink() =>
                    {
                        let target = fs::read_link(existing).map_err(|error| {
                            PathSafetyError::io("read dangling symlink", existing, error)
                        })?;
                        let target = if target.is_absolute() {
                            target
                        } else {
                            existing
                                .parent()
                                .unwrap_or_else(|| Path::new("/"))
                                .join(target)
                        };
                        resolve_allow_missing(target)?
                    }
                    Err(source) => {
                        return Err(PathSafetyError::io(
                            "resolve existing path",
                            existing,
                            source,
                        ));
                    }
                };
                for component in suffix.iter().rev() {
                    resolved.push(component);
                }
                let resolved = normalize_path(resolved)?;
                return if second_pass {
                    resolve_allow_missing(resolved)
                } else {
                    Ok(resolved)
                };
            }
            Err(source)
                if matches!(
                    source.kind(),
                    io::ErrorKind::NotFound | io::ErrorKind::NotADirectory
                ) =>
            {
                let component = existing.components().next_back().ok_or_else(|| {
                    PathSafetyError::new(PathSafetyErrorKind::Missing, Some(absolute.clone()))
                })?;
                second_pass |= matches!(component, Component::ParentDir | Component::CurDir);
                suffix.push(component.as_os_str().to_os_string());
                existing = existing.parent().ok_or_else(|| {
                    PathSafetyError::new(PathSafetyErrorKind::Missing, Some(absolute.clone()))
                })?;
            }
            Err(source) => {
                return Err(PathSafetyError::io("resolve path", existing, source));
            }
        }
    }
}

/// Return whether a resolved candidate equals or descends from a resolved root.
#[must_use]
pub fn path_under(path: impl AsRef<Path>, root: impl AsRef<Path>) -> bool {
    resolve_allow_missing(path)
        .and_then(|candidate| resolve_allow_missing(root).map(|root| candidate.starts_with(root)))
        .unwrap_or(false)
}

/// Return whether a resolved candidate is a strict descendant of a resolved root.
#[must_use]
pub fn path_strictly_under(path: impl AsRef<Path>, root: impl AsRef<Path>) -> bool {
    resolve_allow_missing(path)
        .and_then(|candidate| {
            resolve_allow_missing(root).map(|root| candidate != root && candidate.starts_with(root))
        })
        .unwrap_or(false)
}

/// Check the legacy strict-descendant policy for a session temporary directory.
#[must_use]
pub fn is_allowed_session_tmpdir(path: impl AsRef<Path>, roots: &[PathBuf]) -> bool {
    !path.as_ref().as_os_str().is_empty()
        && roots
            .iter()
            .any(|root| path_strictly_under(path.as_ref(), root))
}

/// Check the legacy equal-or-descendant policy for a session writer target.
#[must_use]
pub fn writer_target_allowed(path: impl AsRef<Path>, roots: &[PathBuf]) -> bool {
    roots.iter().any(|root| path_under(path.as_ref(), root))
}

/// Create `directory` and every missing ancestor without following symlinks.
///
/// The nearest existing ancestor anchors a [`TemporaryRoot`], so the whole
/// chain is created through the same confinement checks a write would use.
///
/// # Errors
///
/// Returns [`PathSafetyError`] when no existing ancestor is reachable, an
/// ancestor is a symlink or non-directory, or creation fails.
pub fn ensure_directory_chain(directory: &Path) -> Result<(), PathSafetyError> {
    let mut anchor = directory;
    while !anchor.exists() {
        anchor = anchor.parent().ok_or_else(|| {
            PathSafetyError::new(PathSafetyErrorKind::Missing, Some(directory.to_path_buf()))
        })?;
    }
    let relative = directory.strip_prefix(anchor).map_err(|_error| {
        PathSafetyError::new(
            PathSafetyErrorKind::EscapesRoot,
            Some(directory.to_path_buf()),
        )
    })?;
    let root = TemporaryRoot::resolve(Some(anchor))?;
    // The trusted root is canonical, so the tail is rejoined to it rather than
    // to the caller's possibly symlinked spelling.
    root.ensure_directory(root.path().join(relative))
        .map(|_created| ())
}

/// Return whether an output parent is an existing non-symlinked directory.
#[must_use]
pub fn safe_output_parent(path: impl AsRef<Path>) -> bool {
    path.as_ref().parent().is_some_and(|parent| {
        fs::symlink_metadata(parent)
            .is_ok_and(|metadata| metadata.is_dir() && !metadata.file_type().is_symlink())
    })
}

fn validate_confined(confined: &ConfinedPath) -> Result<(), PathSafetyError> {
    if !confined.path.is_absolute() || !confined.root.path().is_absolute() {
        return Err(PathSafetyError::new(
            PathSafetyErrorKind::NotAbsolute,
            Some(confined.path.clone()),
        ));
    }
    if !confined.path.starts_with(confined.root.path()) {
        return Err(PathSafetyError::new(
            PathSafetyErrorKind::EscapesRoot,
            Some(confined.path.clone()),
        ));
    }
    confined.root.revalidate()?;
    if confined.intent == PathIntent::Cleanup && confined.path == confined.root.path() {
        return Err(PathSafetyError::new(
            PathSafetyErrorKind::RootCleanup,
            Some(confined.path.clone()),
        ));
    }

    let relative = confined
        .path
        .strip_prefix(confined.root.path())
        .map_err(|_error| {
            PathSafetyError::new(
                PathSafetyErrorKind::EscapesRoot,
                Some(confined.path.clone()),
            )
        })?;
    let components = relative.components().collect::<Vec<_>>();
    let mut current = confined.root.path.clone();
    for (index, component) in components.iter().enumerate() {
        current.push(component.as_os_str());
        let is_leaf = index + 1 == components.len();
        match fs::symlink_metadata(&current) {
            Ok(metadata) => validate_component_type(&current, &metadata, is_leaf, confined.intent)?,
            Err(source)
                if source.kind() == io::ErrorKind::NotFound
                    && is_leaf
                    && matches!(confined.intent, PathIntent::Write | PathIntent::Cache) => {}
            Err(source) => {
                return Err(PathSafetyError::io(
                    "inspect confined path",
                    &current,
                    source,
                ));
            }
        }
    }
    Ok(())
}

fn validate_component_type(
    path: &Path,
    metadata: &fs::Metadata,
    is_leaf: bool,
    intent: PathIntent,
) -> Result<(), PathSafetyError> {
    let file_type = metadata.file_type();
    if file_type.is_symlink() {
        return Err(PathSafetyError::new(
            PathSafetyErrorKind::Symlink,
            Some(path.to_path_buf()),
        ));
    }
    if !is_leaf && !file_type.is_dir() {
        return Err(PathSafetyError::new(
            PathSafetyErrorKind::NotDirectory,
            Some(path.to_path_buf()),
        ));
    }
    if is_leaf {
        let accepted = match intent {
            PathIntent::Read | PathIntent::Write => file_type.is_file(),
            PathIntent::Cleanup | PathIntent::Cache => file_type.is_file() || file_type.is_dir(),
        };
        if !accepted {
            return Err(PathSafetyError::new(
                PathSafetyErrorKind::NotRegularFile,
                Some(path.to_path_buf()),
            ));
        }
        if file_type.is_file()
            && matches!(intent, PathIntent::Write | PathIntent::Cache)
            && has_multiple_links(metadata)
        {
            return Err(PathSafetyError::new(
                PathSafetyErrorKind::MultipleLinks,
                Some(path.to_path_buf()),
            ));
        }
    }
    Ok(())
}

#[cfg(unix)]
fn has_multiple_links(metadata: &fs::Metadata) -> bool {
    use std::os::unix::fs::MetadataExt;

    metadata.nlink() > 1
}

#[cfg(not(unix))]
const fn has_multiple_links(_metadata: &fs::Metadata) -> bool {
    false
}

fn validate_root_path(root: &Path) -> Result<fs::Metadata, PathSafetyError> {
    let metadata = fs::symlink_metadata(root)
        .map_err(|source| PathSafetyError::io("inspect trusted root", root, source))?;
    if metadata.file_type().is_symlink() {
        return Err(PathSafetyError::new(
            PathSafetyErrorKind::Symlink,
            Some(root.to_path_buf()),
        ));
    }
    if !metadata.file_type().is_dir() {
        return Err(PathSafetyError::new(
            PathSafetyErrorKind::NotDirectory,
            Some(root.to_path_buf()),
        ));
    }
    Ok(metadata)
}

fn verify_removed(path: &Path, operation: &'static str) -> Result<(), PathSafetyError> {
    match fs::symlink_metadata(path) {
        Err(source) if source.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(source) => Err(PathSafetyError::io(operation, path, source)),
        Ok(_) => Err(PathSafetyError::new(
            PathSafetyErrorKind::Io,
            Some(path.to_path_buf()),
        )),
    }
}

fn validate_temp_prefix(prefix: &str) -> Result<(), PathSafetyError> {
    let valid = !prefix.is_empty()
        && prefix.len() <= TEMP_PREFIX_MAX_BYTES
        && prefix
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'));
    if valid {
        Ok(())
    } else {
        Err(PathSafetyError::new(
            PathSafetyErrorKind::InvalidTempPrefix,
            None,
        ))
    }
}

#[cfg(unix)]
fn set_unix_permissions(path: &Path, mode: u32) -> Result<(), PathSafetyError> {
    use std::os::unix::fs::PermissionsExt;

    fs::set_permissions(path, fs::Permissions::from_mode(mode))
        .map_err(|source| PathSafetyError::io("set private permissions", path, source))
}

#[cfg(test)]
mod tests {
    use super::{
        PathIntent, PathSafetyErrorKind, PluginRoot, RepositoryRoot, SecureTempDir, SecureTempFile,
        TemporaryRoot, is_allowed_session_tmpdir, normalize_path, path_strictly_under, path_under,
        resolve_allow_missing, safe_output_parent, writer_target_allowed,
    };
    use std::{
        fs,
        io::Write,
        path::{Path, PathBuf},
    };
    use tempfile::tempdir;

    #[test]
    fn roots_require_explicit_absolute_existing_directories() {
        let directory = tempdir().expect("fixture tempdir");
        let relative = Path::new("relative-root");
        let file = directory.path().join("file");
        fs::write(&file, b"fixture").expect("fixture file");

        assert_eq!(
            RepositoryRoot::resolve(None)
                .expect_err("missing root must fail")
                .kind(),
            PathSafetyErrorKind::MissingRoot
        );
        assert_eq!(
            RepositoryRoot::resolve(Some(relative))
                .expect_err("relative root must fail")
                .kind(),
            PathSafetyErrorKind::NotAbsolute
        );
        assert_eq!(
            PluginRoot::resolve(Some(&file))
                .expect_err("file root must fail")
                .kind(),
            PathSafetyErrorKind::NotDirectory
        );
        assert_eq!(
            RepositoryRoot::resolve(Some(directory.path()))
                .expect("existing root")
                .path(),
            directory.path().canonicalize().expect("canonical fixture")
        );
    }

    #[test]
    fn session_paths_resolve_symlinks_and_distinguish_strict_containment() {
        let directory = tempdir().expect("fixture tempdir");
        let root = directory.path().join("root");
        let outside = directory.path().join("outside");
        fs::create_dir(&root).expect("root should create");
        fs::create_dir(&outside).expect("outside should create");
        std::os::unix::fs::symlink(&outside, root.join("escape"))
            .expect("escape symlink should create");

        assert_eq!(
            resolve_allow_missing(root.join("missing/file"))
                .expect("missing suffix should resolve"),
            fs::canonicalize(&root)
                .expect("root should canonicalize")
                .join("missing/file")
        );
        assert!(path_under(&root, &root));
        assert!(!path_strictly_under(&root, &root));
        assert!(path_strictly_under(root.join("child"), &root));
        fs::write(root.join("file"), b"x").expect("file should create");
        assert!(path_under(root.join("file/child"), &root));
        assert!(!path_under(root.join("escape/file"), &root));
        assert!(!path_under(root.join("escape/../file"), &root));
        std::os::unix::fs::symlink(root.join("missing-target"), root.join("dangling"))
            .expect("dangling symlink should create");
        assert_eq!(
            resolve_allow_missing(root.join("dangling/child"))
                .expect("dangling target should resolve"),
            fs::canonicalize(&root)
                .expect("root should canonicalize")
                .join("missing-target/child")
        );
        assert!(writer_target_allowed(&root, std::slice::from_ref(&root)));
        assert!(!is_allowed_session_tmpdir(
            &root,
            std::slice::from_ref(&root)
        ));
        assert!(is_allowed_session_tmpdir(
            root.join("child"),
            std::slice::from_ref(&root)
        ));
    }

    #[test]
    fn safe_output_parent_and_directory_creation_reject_symlinks_and_wrong_types() {
        let directory = tempdir().expect("fixture tempdir");
        let root = TemporaryRoot::resolve(Some(directory.path())).expect("root should resolve");
        let created = root
            .ensure_directory("nested/private")
            .expect("nested directory should create");
        assert!(safe_output_parent(created.join("state.env")));
        fs::write(root.path().join("file"), b"x").expect("file should create");
        assert_eq!(
            root.ensure_directory("file/child")
                .expect_err("file ancestor should fail")
                .kind(),
            PathSafetyErrorKind::NotDirectory
        );
        std::os::unix::fs::symlink(&created, root.path().join("linked"))
            .expect("link should create");
        assert!(!safe_output_parent(root.path().join("linked/state.env")));
        assert_eq!(
            root.ensure_directory("linked/child")
                .expect_err("symlink ancestor should fail")
                .kind(),
            PathSafetyErrorKind::Symlink
        );
    }

    #[test]
    fn normalization_is_lexical_and_fail_closed() {
        assert_eq!(
            normalize_path("alpha/./beta/../file").expect("contained path"),
            PathBuf::from("alpha/file")
        );
        assert_eq!(
            normalize_path("alpha/..").expect("base path"),
            PathBuf::from(".")
        );
        assert_eq!(
            normalize_path("../escape")
                .expect_err("leading traversal must fail")
                .kind(),
            PathSafetyErrorKind::Traversal
        );
    }

    #[cfg(unix)]
    #[test]
    fn unix_normalization_preserves_backslash_as_filename_data() {
        assert_eq!(
            normalize_path(r"alpha\beta").expect("Unix filename"),
            PathBuf::from(r"alpha\beta")
        );
    }

    #[test]
    fn confinement_covers_relative_absolute_missing_and_escape_paths() {
        let directory = tempdir().expect("fixture tempdir");
        let root = RepositoryRoot::resolve(Some(directory.path())).expect("fixture root");
        let file = root.path().join("artifact.txt");
        fs::write(&file, b"fixture").expect("fixture file");

        let relative = root
            .confine("artifact.txt", PathIntent::Read)
            .expect("relative read");
        let absolute = root
            .confine(&file, PathIntent::Read)
            .expect("absolute read");
        assert_eq!(relative.path(), file);
        assert_eq!(absolute.path(), file);
        assert_eq!(
            root.confine("missing.txt", PathIntent::Read)
                .expect_err("missing read must fail")
                .kind(),
            PathSafetyErrorKind::Missing
        );
        assert!(root.confine("missing.txt", PathIntent::Write).is_ok());
        assert_eq!(
            root.confine("../escape", PathIntent::Write)
                .expect_err("relative escape must fail")
                .kind(),
            PathSafetyErrorKind::EscapesRoot
        );
        assert_eq!(
            root.confine(
                directory.path().parent().expect("parent"),
                PathIntent::Cleanup
            )
            .expect_err("absolute escape must fail")
            .kind(),
            PathSafetyErrorKind::EscapesRoot
        );
        assert_eq!(
            root.confine(root.path(), PathIntent::Cleanup)
                .expect_err("root cleanup must fail")
                .kind(),
            PathSafetyErrorKind::RootCleanup
        );
    }

    #[cfg(unix)]
    #[test]
    fn root_resolution_and_confined_uses_have_explicit_symlink_policies() {
        use std::os::unix::fs::symlink;

        let directory = tempdir().expect("fixture tempdir");
        let real_root = directory.path().join("real-root");
        let linked_root = directory.path().join("linked-root");
        let outside = directory.path().join("outside");
        fs::create_dir(&real_root).expect("real root");
        fs::create_dir(&outside).expect("outside root");
        fs::write(outside.join("secret"), b"outside").expect("outside file");
        symlink(&real_root, &linked_root).expect("root symlink");

        let root = RepositoryRoot::resolve(Some(&linked_root)).expect("root symlink resolves once");
        assert_eq!(
            root.path(),
            real_root.canonicalize().expect("canonical root")
        );
        assert_eq!(
            TemporaryRoot::resolve(Some(&linked_root))
                .expect_err("temporary root symlink must fail")
                .kind(),
            PathSafetyErrorKind::Symlink
        );

        symlink(outside.join("secret"), root.path().join("escape")).expect("escaping file symlink");
        assert_eq!(
            root.confine("escape", PathIntent::Read)
                .expect_err("symlink read must fail")
                .kind(),
            PathSafetyErrorKind::Symlink
        );
        symlink(&outside, root.path().join("escape-dir")).expect("escaping directory symlink");
        assert_eq!(
            root.confine("escape-dir/new", PathIntent::Write)
                .expect_err("symlink ancestor must fail")
                .kind(),
            PathSafetyErrorKind::Symlink
        );
    }

    #[cfg(unix)]
    #[test]
    fn revalidation_detects_a_symlink_swap_before_use() {
        use std::os::unix::fs::symlink;

        let directory = tempdir().expect("fixture tempdir");
        let outside = tempdir().expect("outside tempdir");
        let root = RepositoryRoot::resolve(Some(directory.path())).expect("fixture root");
        let confined = root
            .confine("future", PathIntent::Write)
            .expect("missing write target");
        symlink(outside.path(), confined.path()).expect("swap target to symlink");

        assert_eq!(
            confined.revalidate().expect_err("swap must fail").kind(),
            PathSafetyErrorKind::Symlink
        );
    }

    #[cfg(unix)]
    #[test]
    fn revalidation_detects_trusted_root_replacement() {
        let directory = tempdir().expect("fixture tempdir");
        let root_path = directory.path().join("root");
        let displaced = directory.path().join("displaced");
        fs::create_dir(&root_path).expect("fixture root");
        let root = RepositoryRoot::resolve(Some(&root_path)).expect("resolved root");
        let confined = root
            .confine("future", PathIntent::Write)
            .expect("missing write target");

        fs::rename(&root_path, &displaced).expect("displace trusted root");
        fs::create_dir(&root_path).expect("replacement root");

        assert_eq!(
            confined
                .revalidate()
                .expect_err("root replacement must fail")
                .kind(),
            PathSafetyErrorKind::RootChanged
        );
    }

    #[cfg(unix)]
    #[test]
    fn writable_paths_reject_files_hard_linked_outside_the_root() {
        let directory = tempdir().expect("fixture tempdir");
        let outside = tempdir().expect("outside tempdir");
        let root = RepositoryRoot::resolve(Some(directory.path())).expect("fixture root");
        let file = root.path().join("shared");
        fs::write(&file, b"fixture").expect("fixture file");
        fs::hard_link(&file, outside.path().join("outside-link")).expect("outside hard link");

        assert!(root.confine(&file, PathIntent::Read).is_ok());
        assert_eq!(
            root.confine(&file, PathIntent::Write)
                .expect_err("multiply linked write must fail")
                .kind(),
            PathSafetyErrorKind::MultipleLinks
        );
        assert_eq!(
            root.confine(&file, PathIntent::Cache)
                .expect_err("multiply linked cache write must fail")
                .kind(),
            PathSafetyErrorKind::MultipleLinks
        );
    }

    #[test]
    fn secure_temp_resources_are_private_confined_and_explicitly_cleanable() {
        let directory = tempdir().expect("fixture tempdir");
        let root = TemporaryRoot::resolve(Some(directory.path())).expect("temporary root");
        let temp_dir = SecureTempDir::create(&root, "larch-dir-").expect("secure tempdir");
        let dir_path = temp_dir.path().to_path_buf();
        let mut temp_file = SecureTempFile::create(&root, "larch-file-").expect("secure tempfile");
        let file_path = temp_file.path().to_path_buf();
        temp_file
            .file_mut()
            .write_all(b"private")
            .expect("write temp file");

        assert!(dir_path.starts_with(root.path()));
        assert!(file_path.starts_with(root.path()));
        assert!(dir_path.is_dir());
        assert!(file_path.is_file());
        temp_file.close().expect("explicit file cleanup");
        temp_dir.close().expect("explicit directory cleanup");
        assert!(!file_path.exists());
        assert!(!dir_path.exists());
    }

    #[cfg(unix)]
    #[test]
    fn secure_temp_resources_use_private_unix_modes() {
        use std::os::unix::fs::PermissionsExt;

        let directory = tempdir().expect("fixture tempdir");
        let root = TemporaryRoot::resolve(Some(directory.path())).expect("temporary root");
        let temp_dir = SecureTempDir::create(&root, "dir-").expect("secure tempdir");
        let temp_file = SecureTempFile::create(&root, "file-").expect("secure tempfile");

        assert_eq!(
            fs::metadata(temp_dir.path())
                .expect("dir metadata")
                .permissions()
                .mode()
                & 0o777,
            0o700
        );
        assert_eq!(
            fs::metadata(temp_file.path())
                .expect("file metadata")
                .permissions()
                .mode()
                & 0o777,
            0o600
        );
    }

    #[cfg(unix)]
    #[test]
    fn drop_leaves_symlink_replacements_instead_of_cleaning_them() {
        use std::os::unix::fs::symlink;

        let directory = tempdir().expect("fixture tempdir");
        let outside = tempdir().expect("outside tempdir");
        let root = TemporaryRoot::resolve(Some(directory.path())).expect("temporary root");

        let temp_dir = SecureTempDir::create(&root, "dir-").expect("secure tempdir");
        let dir_path = temp_dir.path().to_path_buf();
        fs::remove_dir(&dir_path).expect("remove original tempdir");
        symlink(outside.path(), &dir_path).expect("replace tempdir with symlink");
        drop(temp_dir);
        assert!(
            fs::symlink_metadata(&dir_path)
                .expect("preserved directory symlink")
                .file_type()
                .is_symlink()
        );
        fs::remove_file(&dir_path).expect("clean directory symlink fixture");

        let temp_file = SecureTempFile::create(&root, "file-").expect("secure tempfile");
        let file_path = temp_file.path().to_path_buf();
        fs::remove_file(&file_path).expect("remove original tempfile");
        symlink(outside.path(), &file_path).expect("replace tempfile with symlink");
        drop(temp_file);
        assert!(
            fs::symlink_metadata(&file_path)
                .expect("preserved file symlink")
                .file_type()
                .is_symlink()
        );
        fs::remove_file(&file_path).expect("clean file symlink fixture");
    }

    #[test]
    fn temporary_prefixes_reject_separators_unicode_and_unbounded_names() {
        let directory = tempdir().expect("fixture tempdir");
        let root = TemporaryRoot::resolve(Some(directory.path())).expect("temporary root");
        for prefix in ["", "../escape", "nested/name", "café", &"x".repeat(65)] {
            assert_eq!(
                SecureTempFile::create(&root, prefix)
                    .expect_err("unsafe prefix must fail")
                    .kind(),
                PathSafetyErrorKind::InvalidTempPrefix,
                "{prefix:?}"
            );
        }
    }
}
