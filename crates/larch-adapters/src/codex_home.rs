//! Confined, private Codex-home preparation for vendor launches.
//!
//! The legacy launcher copied selected user settings into a temporary
//! `CODEX_HOME`. This adapter preserves that behavior without placing a
//! symlink, credential, or writable path outside the private root.

use crate::{
    ConfinedPath, PathIntent, PathSafetyError, SecureTempDir, TemporaryRoot, atomic_write_bytes,
    atomic_write_utf8, remove_optional_file,
};
use larch_core::{
    ChildEnvironment, CodexEnvAuth, CodexReviewAuthPort, ReviewAuthVerdict, strip_codex_config,
};
use std::{
    error::Error,
    ffi::OsString,
    fmt, fs,
    io::ErrorKind,
    path::{Path, PathBuf},
};

const CODEX_HOME_PREFIX: &str = "larch-codex-home-";
const PRIVATE_FILE_MODE: u32 = 0o600;

/// A failure preparing a private Codex home.
#[derive(Debug)]
pub struct CodexHomeError {
    exit_code: i32,
    message: String,
}

impl CodexHomeError {
    fn setup(error: impl fmt::Display) -> Self {
        Self {
            exit_code: 1,
            message: format!("codex auth setup failed: {error}"),
        }
    }

    fn input(message: impl Into<String>) -> Self {
        Self {
            exit_code: 2,
            message: message.into(),
        }
    }

    /// Legacy-compatible refusal code.
    #[must_use]
    pub const fn exit_code(&self) -> i32 {
        self.exit_code
    }
}

impl fmt::Display for CodexHomeError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl Error for CodexHomeError {}

/// An owned private Codex home that is removed with its secure temporary directory.
#[derive(Debug)]
pub struct CodexHomeContext {
    directory: SecureTempDir,
}

impl CodexHomeContext {
    /// Create and populate a private Codex home below `temporary_root`.
    ///
    /// User configuration is copied only after credential and prior-instruction
    /// stripping. When environment-key auth is omitted, a regular user
    /// `auth.json` is copied into the private home instead of symlinked.
    ///
    /// # Errors
    ///
    /// Returns a stable preflight refusal for an unsafe trusted-instructions
    /// input, unsafe root, or any failed private-home publication.
    pub fn create(
        temporary_root: &TemporaryRoot,
        user_home: &Path,
        trusted_instructions: Option<&Path>,
        auth: CodexEnvAuth,
    ) -> Result<Self, CodexHomeError> {
        let directory = SecureTempDir::create(temporary_root, CODEX_HOME_PREFIX)
            .map_err(CodexHomeError::setup)?;
        populate_home(
            temporary_root,
            directory.path(),
            user_home,
            trusted_instructions,
            auth,
        )?;
        Ok(Self { directory })
    }

    /// Absolute path of the private Codex home.
    #[must_use]
    pub fn path(&self) -> &Path {
        self.directory.path()
    }

    /// Typed child-environment override for the owned vendor process.
    #[must_use]
    pub fn child_environment(&self) -> (ChildEnvironment, OsString) {
        (
            ChildEnvironment::CodexHome,
            self.path().as_os_str().to_owned(),
        )
    }

    /// Revalidate and remove the private home now.
    ///
    /// # Errors
    ///
    /// Returns when the secure directory was replaced or cannot be removed.
    pub fn close(self) -> Result<(), PathSafetyError> {
        self.directory.close()
    }
}

/// A reusable preflight adapter for a caller-owned home below one private root.
#[derive(Clone, Debug)]
pub struct CodexHomePreparer {
    temporary_root: TemporaryRoot,
    user_home: PathBuf,
    auth: CodexEnvAuth,
}

impl CodexHomePreparer {
    /// Bind the private root, source home, and already-resolved auth decision.
    #[must_use]
    pub const fn new(
        temporary_root: TemporaryRoot,
        user_home: PathBuf,
        auth: CodexEnvAuth,
    ) -> Self {
        Self {
            temporary_root,
            user_home,
            auth,
        }
    }

    /// Populate an explicit home only after confining it below the private root.
    ///
    /// # Errors
    ///
    /// Returns when `home` escapes the root, contains a symlink, or preparation
    /// cannot complete.
    pub fn prepare(
        &self,
        home: &Path,
        trusted_instructions: Option<&Path>,
    ) -> Result<(), CodexHomeError> {
        self.temporary_root
            .ensure_directory(home)
            .map_err(CodexHomeError::setup)?;
        let confined = self
            .temporary_root
            .confine(home, PathIntent::Cleanup)
            .map_err(CodexHomeError::setup)?;
        populate_home(
            &self.temporary_root,
            confined.path(),
            &self.user_home,
            trusted_instructions,
            self.auth,
        )
    }
}

impl CodexReviewAuthPort for CodexHomePreparer {
    fn prepare_home(&self, home: &Path, trusted_instructions: &Path) -> ReviewAuthVerdict {
        let trusted =
            (!trusted_instructions.as_os_str().is_empty()).then_some(trusted_instructions);
        match self.prepare(home, trusted) {
            Ok(()) => ReviewAuthVerdict::ok(),
            Err(error) => ReviewAuthVerdict::refuse(error.exit_code(), error.to_string()),
        }
    }
}

fn populate_home(
    temporary_root: &TemporaryRoot,
    home: &Path,
    user_home: &Path,
    trusted_instructions: Option<&Path>,
    auth: CodexEnvAuth,
) -> Result<(), CodexHomeError> {
    let config_path = home.join("config.toml");
    let auth_path = home.join("auth.json");
    remove_private_file(temporary_root, &config_path)?;
    remove_private_file(temporary_root, &auth_path)?;

    let user_codex = user_home.join(".codex");
    let source_config = read_regular_file(&user_codex.join("config.toml"))?
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .unwrap_or_default();
    let config = match trusted_instructions {
        Some(path) => {
            let body = read_trusted_instructions(path)?;
            format!(
                "instructions = '''\n{body}\n'''\n\n{}",
                strip_codex_config(&source_config, true)
            )
        }
        None => strip_codex_config(&source_config, false),
    };
    if !config.is_empty() {
        write_private_text(temporary_root, &config_path, &config)?;
    }

    if auth == CodexEnvAuth::Omit
        && let Some(source_auth) = read_regular_file(&user_codex.join("auth.json"))?
    {
        write_private_bytes(temporary_root, &auth_path, &source_auth)?;
    }
    Ok(())
}

fn read_trusted_instructions(path: &Path) -> Result<String, CodexHomeError> {
    let metadata = match fs::symlink_metadata(path) {
        Ok(metadata) => metadata,
        Err(error) if matches!(error.kind(), ErrorKind::NotFound | ErrorKind::NotADirectory) => {
            return Err(CodexHomeError::input(format!(
                "--trusted-instructions-file not found: {}",
                path.display()
            )));
        }
        Err(error) => return Err(CodexHomeError::setup(error)),
    };
    if metadata.file_type().is_symlink() {
        return Err(CodexHomeError::input(
            "--trusted-instructions-file must not be a symlink",
        ));
    }
    if !metadata.is_file() {
        return Err(CodexHomeError::input(format!(
            "--trusted-instructions-file not found: {}",
            path.display()
        )));
    }
    let body = fs::read(path).map_err(CodexHomeError::setup)?;
    let body = String::from_utf8_lossy(&body).into_owned();
    if body.contains("'''") {
        return Err(CodexHomeError::input(
            "trusted instructions file contains TOML triple-single-quote delimiter",
        ));
    }
    Ok(body)
}

fn read_regular_file(path: &Path) -> Result<Option<Vec<u8>>, CodexHomeError> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.is_file() && !metadata.file_type().is_symlink() => {
            fs::read(path).map(Some).map_err(CodexHomeError::setup)
        }
        Ok(_) => Ok(None),
        Err(error) if matches!(error.kind(), ErrorKind::NotFound | ErrorKind::NotADirectory) => {
            Ok(None)
        }
        Err(error) => Err(CodexHomeError::setup(error)),
    }
}

fn remove_private_file(temporary_root: &TemporaryRoot, path: &Path) -> Result<(), CodexHomeError> {
    match fs::symlink_metadata(path) {
        Ok(_) => {
            let confined = temporary_root
                .confine(path, PathIntent::Cleanup)
                .map_err(CodexHomeError::setup)?;
            remove_optional_file(confined.path()).map_err(CodexHomeError::setup)
        }
        Err(error) if error.kind() == ErrorKind::NotFound => Ok(()),
        Err(error) => Err(CodexHomeError::setup(error)),
    }
}

fn write_private_text(
    temporary_root: &TemporaryRoot,
    path: &Path,
    text: &str,
) -> Result<(), CodexHomeError> {
    let confined = confine_private_write(temporary_root, path)?;
    atomic_write_utf8(&confined, text, PRIVATE_FILE_MODE).map_err(CodexHomeError::setup)
}

fn write_private_bytes(
    temporary_root: &TemporaryRoot,
    path: &Path,
    bytes: &[u8],
) -> Result<(), CodexHomeError> {
    let confined = confine_private_write(temporary_root, path)?;
    atomic_write_bytes(&confined, bytes, PRIVATE_FILE_MODE).map_err(CodexHomeError::setup)
}

fn confine_private_write(
    temporary_root: &TemporaryRoot,
    path: &Path,
) -> Result<ConfinedPath, CodexHomeError> {
    temporary_root
        .confine(path, PathIntent::Write)
        .map_err(CodexHomeError::setup)
}

#[cfg(test)]
mod tests {
    use super::{CodexHomeContext, CodexHomePreparer};
    use larch_core::{ChildEnvironment, CodexEnvAuth};
    use std::{fs, path::Path};
    use tempfile::tempdir;

    fn private_root(path: &Path) -> crate::TemporaryRoot {
        crate::TemporaryRoot::resolve(Some(path)).expect("private root")
    }

    #[test]
    fn private_home_strips_config_and_copies_auth_without_a_symlink() {
        let private = tempdir().expect("private root");
        let user = tempdir().expect("user home");
        let codex = user.path().join(".codex");
        fs::create_dir(&codex).expect("user Codex dir");
        fs::write(
            codex.join("config.toml"),
            "model = \"kept\"\napi_key = \"secret\"\ninstructions = '''\nold\n'''\n",
        )
        .expect("config");
        fs::write(codex.join("auth.json"), "{\"token\":\"copied\"}\n").expect("auth");
        let trusted = user.path().join("trusted.md");
        fs::write(&trusted, "trusted instructions").expect("trusted instructions");

        let root = private_root(private.path());
        let context =
            CodexHomeContext::create(&root, user.path(), Some(&trusted), CodexEnvAuth::Omit)
                .expect("private context");
        assert!(context.path().starts_with(root.path()));
        assert!(
            !fs::symlink_metadata(context.path())
                .expect("home metadata")
                .file_type()
                .is_symlink()
        );
        let config = fs::read_to_string(context.path().join("config.toml")).expect("config");
        assert!(config.contains("trusted instructions"));
        assert!(!config.contains("secret"));
        assert!(!config.contains("old"));
        let auth = context.path().join("auth.json");
        assert!(auth.is_file());
        assert!(
            !fs::symlink_metadata(&auth)
                .expect("auth metadata")
                .file_type()
                .is_symlink()
        );
        assert_eq!(
            fs::read_to_string(auth).expect("auth"),
            "{\"token\":\"copied\"}\n"
        );
        let (key, value) = context.child_environment();
        assert_eq!(key, ChildEnvironment::CodexHome);
        assert_eq!(value, context.path().as_os_str());
    }

    #[test]
    fn environment_key_auth_does_not_copy_user_auth() {
        let private = tempdir().expect("private root");
        let user = tempdir().expect("user home");
        let codex = user.path().join(".codex");
        fs::create_dir(&codex).expect("user Codex dir");
        fs::write(codex.join("auth.json"), "{\"token\":\"user\"}\n").expect("auth");
        let context = CodexHomeContext::create(
            &private_root(private.path()),
            user.path(),
            None,
            CodexEnvAuth::Include,
        )
        .expect("private context");
        assert!(!context.path().join("auth.json").exists());
    }

    #[cfg(unix)]
    #[test]
    fn rejects_symlinked_trusted_instructions_and_escaped_homes() {
        let private = tempdir().expect("private root");
        let user = tempdir().expect("user home");
        let source = user.path().join("source.md");
        fs::write(&source, "trusted").expect("source");
        let trusted = user.path().join("trusted.md");
        std::os::unix::fs::symlink(&source, &trusted).expect("trusted link");
        let root = private_root(private.path());
        let error =
            CodexHomeContext::create(&root, user.path(), Some(&trusted), CodexEnvAuth::Omit)
                .expect_err("symlink must fail");
        assert_eq!(error.exit_code(), 2);
        assert_eq!(
            error.to_string(),
            "--trusted-instructions-file must not be a symlink"
        );

        let outside = tempdir().expect("outside");
        let preparer = CodexHomePreparer::new(root, user.path().to_path_buf(), CodexEnvAuth::Omit);
        let error = preparer
            .prepare(outside.path(), None)
            .expect_err("escaped home must fail");
        assert_eq!(error.exit_code(), 1);
        assert!(!outside.path().join("config.toml").exists());
    }
}
