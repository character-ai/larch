use std::{
    fs, io,
    path::{Component, Path, PathBuf},
};

use tempfile::TempDir;

/// An owned temporary directory with confined fixture paths.
#[derive(Debug)]
pub struct TestWorkspace {
    directory: TempDir,
}

impl TestWorkspace {
    /// Create an empty workspace that is removed when dropped.
    ///
    /// # Errors
    /// Returns the temporary-directory creation error.
    pub fn new() -> io::Result<Self> {
        tempfile::Builder::new()
            .prefix("larch-test-")
            .tempdir()
            .map(|directory| Self { directory })
    }

    /// Return the absolute fixture root.
    #[must_use]
    pub fn root(&self) -> &Path {
        self.directory.path()
    }

    /// Resolve a non-empty confined relative path.
    ///
    /// # Errors
    /// Rejects absolute paths, empty paths, and `.` or `..` components.
    pub fn path(&self, relative: impl AsRef<Path>) -> io::Result<PathBuf> {
        let relative = relative.as_ref();
        validate_relative(relative)?;
        reject_symlink_components(self.root(), relative)?;
        Ok(self.root().join(relative))
    }

    /// Create a confined directory and its parents.
    ///
    /// # Errors
    /// Returns path validation or filesystem errors.
    pub fn create_dir(&self, relative: impl AsRef<Path>) -> io::Result<PathBuf> {
        let path = self.path(relative)?;
        fs::create_dir_all(&path)?;
        Ok(path)
    }

    /// Write bytes to a confined path, creating parent directories.
    ///
    /// # Errors
    /// Returns path validation or filesystem errors.
    pub fn write(
        &self,
        relative: impl AsRef<Path>,
        contents: impl AsRef<[u8]>,
    ) -> io::Result<PathBuf> {
        let path = self.path(relative)?;
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(&path, contents)?;
        Ok(path)
    }

    /// Read bytes from a confined path.
    ///
    /// # Errors
    /// Returns path validation or filesystem errors.
    pub fn read(&self, relative: impl AsRef<Path>) -> io::Result<Vec<u8>> {
        fs::read(self.path(relative)?)
    }
}

pub fn validate_relative(path: &Path) -> io::Result<()> {
    if path.as_os_str().is_empty()
        || path
            .components()
            .any(|component| !matches!(component, Component::Normal(_)))
    {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            format!(
                "test fixture path must be a confined relative path: {}",
                path.display()
            ),
        ));
    }
    Ok(())
}

fn reject_symlink_components(root: &Path, relative: &Path) -> io::Result<()> {
    let mut candidate = root.to_path_buf();
    for component in relative.components() {
        candidate.push(component);
        match fs::symlink_metadata(&candidate) {
            Ok(metadata) if metadata.file_type().is_symlink() => {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidInput,
                    format!(
                        "test fixture path crosses a symlink: {}",
                        candidate.display()
                    ),
                ));
            }
            Ok(_) => {}
            Err(error) if error.kind() == io::ErrorKind::NotFound => break,
            Err(error) => return Err(error),
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::{io::ErrorKind, path::Path};

    use super::TestWorkspace;

    #[test]
    fn workspace_builds_files_without_changing_process_state() {
        let original = std::env::current_dir().expect("current directory");
        let workspace = TestWorkspace::new().expect("test workspace");

        workspace
            .write("nested/input.txt", b"fixture\n")
            .expect("write fixture");

        assert_eq!(
            workspace.read("nested/input.txt").expect("read fixture"),
            b"fixture\n"
        );
        assert_eq!(
            std::env::current_dir().expect("current directory"),
            original
        );
    }

    #[test]
    fn workspace_rejects_escape_and_absolute_paths() {
        let workspace = TestWorkspace::new().expect("test workspace");
        for path in [Path::new("../escape"), workspace.root()] {
            assert_eq!(
                workspace
                    .path(path)
                    .expect_err("unsafe path must fail")
                    .kind(),
                ErrorKind::InvalidInput
            );
        }
    }

    #[cfg(unix)]
    #[test]
    fn workspace_rejects_symlinked_ancestors() {
        use std::os::unix::fs::symlink;

        let workspace = TestWorkspace::new().expect("test workspace");
        let outside = tempfile::tempdir().expect("outside workspace");
        symlink(outside.path(), workspace.root().join("linked")).expect("fixture symlink");

        assert_eq!(
            workspace
                .write("linked/escape.txt", b"escape")
                .expect_err("symlink escape must fail")
                .kind(),
            ErrorKind::InvalidInput
        );
        assert!(!outside.path().join("escape.txt").exists());
    }
}
