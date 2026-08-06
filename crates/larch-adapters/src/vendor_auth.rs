//! Vendor credential preflight and the cross-process reviewer-probe cache.
//!
//! Credentials never touch this module's process environment, stdout, or any
//! artifact it writes. A keychain secret is carried only inside
//! [`CursorCredential`], which redacts itself, and reaches a vendor only as a
//! typed child-environment override on an approved [`ProcessRequest`].

use crate::{
    ConfinedPath, FileIoError, PathIntent, PathSafetyError, TemporaryRoot, atomic_write_utf8_in,
    file_io::{absent_is_success, io_error, path_safety_error},
    vendor_lifecycle::{StartupLockConfig, StartupLockGuard},
};
use larch_core::{
    CURSOR_AUTH_MAX_ATTEMPTS, CURSOR_AUTH_RETRY_DELAY, CodexGateDetail, CursorCredential,
    ExternalProcessRunner, ExternalProgram, HostPlatform, HostUtilityProgram, ProbeTtl,
    ProcessCancellation, ProcessRequest, ReviewAuthVerdict, codex_gate_detail_file_name,
    codex_probe_update_lock_file_name, cursor_keychain_arguments, cursor_preflight_refusal,
    fresh_probe_verdict, keychain_credential, parse_codex_gate_detail, probe_cache_user,
    probe_stamp_contents, probe_stamp_file_name, render_codex_gate_detail,
};
use std::{
    ffi::OsString,
    fs, io,
    num::NonZeroUsize,
    path::{Path, PathBuf},
    time::{Duration, SystemTime},
};

/// Private mode for every probe-cache artifact.
const CACHE_FILE_MODE: u32 = 0o600;

/// Bounded capture ceiling for one keychain read.
const KEYCHAIN_OUTPUT_LIMIT: usize = 16 * 1024;

/// Bounded timeout for one keychain read.
const KEYCHAIN_TIMEOUT: Duration = Duration::from_secs(10);

/// Bounded shutdown grace for one keychain read.
const KEYCHAIN_SHUTDOWN_GRACE: Duration = Duration::from_secs(1);

/// Resolved inputs for one Cursor authentication preflight.
#[derive(Clone, Debug)]
pub struct CursorPreflightConfig {
    platform: HostPlatform,
    environment_credential: Option<CursorCredential>,
    caller: String,
    retry_delay: Duration,
}

impl CursorPreflightConfig {
    /// Resolve preflight inputs without reading ambient process state.
    #[must_use]
    pub fn from_values(platform: &str, api_key: Option<&str>, caller: &str) -> Self {
        Self {
            platform: HostPlatform::classify(platform),
            environment_credential: api_key.and_then(CursorCredential::parse),
            caller: caller.to_owned(),
            retry_delay: CURSOR_AUTH_RETRY_DELAY,
        }
    }

    /// Shorten the inter-attempt pause for deterministic tests.
    #[must_use]
    pub const fn with_retry_delay(mut self, retry_delay: Duration) -> Self {
        self.retry_delay = retry_delay;
        self
    }
}

/// Outcome of a Cursor service-token preread.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum CursorTokenPreread {
    /// Cursor may launch. A resolved credential is injected into the child.
    Proceed(Option<CursorCredential>),
    /// A keychain entry exists but its `-w` read returned no token.
    ///
    /// Proceeding here lets the Cursor slot auth-fail in-process and return a
    /// canned, un-reviewed response that the panel scores as clean (#5518), so
    /// the caller reports [`larch_core::CURSOR_PREREAD_FAIL_MESSAGE`] instead.
    Unreadable,
}

/// Everything a keychain-backed preflight needs from the composition root.
#[derive(Clone, Copy, Debug)]
pub struct VendorAuthContext<'a> {
    /// Temporary root that owns the shared Darwin startup lock.
    pub temporary_root: &'a TemporaryRoot,
    /// Startup-lock configuration for the Cursor vendor.
    pub startup_lock: &'a StartupLockConfig,
    /// Absolute working directory for the keychain child.
    pub working_directory: &'a Path,
}

/// Read the Cursor service token once through the approved process layer.
///
/// Returns `None` for a non-zero exit, an unreadable entry, or an empty token.
pub async fn read_cursor_keychain_token<R: ExternalProcessRunner>(
    runner: &R,
    working_directory: &Path,
    cancellation: &dyn ProcessCancellation,
) -> Option<CursorCredential> {
    let request = ProcessRequest::new(
        ExternalProgram::HostUtility(HostUtilityProgram::Security),
        cursor_keychain_arguments().map(OsString::from),
        working_directory.to_path_buf(),
        KEYCHAIN_TIMEOUT,
        KEYCHAIN_SHUTDOWN_GRACE,
        NonZeroUsize::new(KEYCHAIN_OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN),
    )
    .ok()?;
    let output = runner.run(request, cancellation).await.ok()?;
    let exit_code = output.status().code().unwrap_or(1);
    keychain_credential(exit_code, &String::from_utf8_lossy(output.stdout()))
}

/// Prove that Cursor can authenticate before a launch or probe starts.
///
/// A usable `CURSOR_API_KEY` short-circuits, and a non-Darwin host has no
/// keychain to consult. Otherwise the keychain read runs under the shared
/// vendor startup lock with bounded retries, and a failure returns the exact
/// operator guidance rather than letting Cursor emit its cryptic keychain
/// error.
pub async fn cursor_auth_preflight<R: ExternalProcessRunner>(
    runner: &R,
    config: &CursorPreflightConfig,
    context: VendorAuthContext<'_>,
    cancellation: &dyn ProcessCancellation,
) -> ReviewAuthVerdict {
    if config.environment_credential.is_some() || config.platform != HostPlatform::Darwin {
        return ReviewAuthVerdict::ok();
    }
    let _lock = StartupLockGuard::acquire(context.temporary_root, context.startup_lock);
    for attempt in 1..=CURSOR_AUTH_MAX_ATTEMPTS {
        if read_cursor_keychain_token(runner, context.working_directory, cancellation)
            .await
            .is_some()
        {
            return ReviewAuthVerdict::ok();
        }
        if attempt < CURSOR_AUTH_MAX_ATTEMPTS && !config.retry_delay.is_zero() {
            tokio::time::sleep(config.retry_delay).await;
        }
    }
    cursor_preflight_refusal(&config.caller)
}

/// Resolve the credential a Cursor child should receive, or fail closed.
pub async fn cursor_preread_service_token<R: ExternalProcessRunner>(
    runner: &R,
    config: &CursorPreflightConfig,
    context: VendorAuthContext<'_>,
    cancellation: &dyn ProcessCancellation,
) -> CursorTokenPreread {
    if let Some(credential) = config.environment_credential.clone() {
        return CursorTokenPreread::Proceed(Some(credential));
    }
    if config.platform != HostPlatform::Darwin {
        return CursorTokenPreread::Proceed(None);
    }
    let _lock = StartupLockGuard::acquire(context.temporary_root, context.startup_lock);
    read_cursor_keychain_token(runner, context.working_directory, cancellation)
        .await
        .map_or(CursorTokenPreread::Unreadable, |credential| {
            CursorTokenPreread::Proceed(Some(credential))
        })
}

/// Isolated environment one Cursor probe runs under.
///
/// The session owns the private configuration directory and the resolved
/// credential. Both are released when the session value is dropped, so a
/// successful probe, a failed probe, a timeout, and a cancellation all take the
/// same cleanup path; there is no success-only teardown branch to miss.
#[derive(Debug)]
pub struct CursorProbeSession {
    config: crate::CursorConfigContext,
    credential: Option<CursorCredential>,
}

impl CursorProbeSession {
    /// Open a probe session below `temporary_root` for one resolved credential.
    ///
    /// # Errors
    /// Returns when the private configuration directory cannot be created.
    pub fn open(
        temporary_root: &TemporaryRoot,
        home: &Path,
        credential: Option<CursorCredential>,
    ) -> Result<Self, PathSafetyError> {
        Ok(Self {
            config: crate::CursorConfigContext::create(temporary_root, home)?,
            credential,
        })
    }

    /// Absolute path of the private configuration directory.
    #[must_use]
    pub fn config_directory(&self) -> &Path {
        self.config.path()
    }

    /// Typed child-environment overrides for the probe child.
    #[must_use]
    pub fn child_environment(&self) -> Vec<(larch_core::ChildEnvironment, OsString)> {
        let mut overrides = larch_core::cursor_child_environment(self.credential.as_ref());
        overrides.push(self.config.child_environment());
        overrides
    }

    /// Revalidate and remove the private configuration directory now.
    ///
    /// # Errors
    /// Returns when confinement revalidation or cleanup fails.
    pub fn close(self) -> Result<(), PathSafetyError> {
        self.config.close()
    }
}

/// User-scoped reviewer-probe verdict and gate-detail cache.
///
/// Every entry lives under one temporary root and is confined before use, so a
/// symlinked or foreign cache path is rejected rather than followed.
#[derive(Debug)]
pub struct ProbeCache {
    root: TemporaryRoot,
    user: String,
    ttl: ProbeTtl,
}

impl ProbeCache {
    /// Build a cache rooted at a validated temporary directory.
    #[must_use]
    pub fn new(root: TemporaryRoot, user: Option<&str>, ttl: ProbeTtl) -> Self {
        Self {
            root,
            user: probe_cache_user(user),
            ttl,
        }
    }

    /// Return the reusable verdict for one probe kind, when still fresh.
    #[must_use]
    pub fn read_verdict(&self, kind: &str) -> Option<bool> {
        let entry = CacheEntry::read(&self.stamp_path(kind))?;
        fresh_probe_verdict(&entry.contents, entry.modified.elapsed().ok(), &self.ttl)
    }

    /// Publish a probe verdict for later reuse.
    ///
    /// # Errors
    /// Returns when the stamp path is unsafe or publication fails.
    pub fn write_verdict(&self, kind: &str, present: bool) -> Result<(), FileIoError> {
        atomic_write_utf8_in(
            &self.root,
            &self.stamp_path(kind),
            &probe_stamp_contents(present),
            true,
            CACHE_FILE_MODE,
        )
    }

    /// Read the cached Codex gate detail for one identity.
    ///
    /// A detail older than `max_age`, or older than the identity's own probe
    /// stamp, is discarded: the newer probe already superseded it. The
    /// supersession check compares modification times directly rather than two
    /// separately measured ages, which would drift by the interval between
    /// their measurements.
    #[must_use]
    pub fn read_gate_detail(&self, identity: &str, max_age: Duration) -> Option<CodexGateDetail> {
        if max_age.is_zero() {
            return None;
        }
        let entry = CacheEntry::read(&self.gate_detail_path(identity))?;
        if entry.modified.elapsed().ok()? > max_age {
            return None;
        }
        let stamp = modification_time(&self.stamp_path(identity));
        if stamp.is_some_and(|stamp| entry.modified < stamp) {
            return None;
        }
        parse_codex_gate_detail(&entry.contents, identity)
    }

    /// Publish the Codex gate detail for one identity.
    ///
    /// A failed publication clears any stale entry rather than leaving a
    /// partially written detail behind.
    ///
    /// # Errors
    /// Returns when both publication and the follow-up removal fail.
    pub fn write_gate_detail(
        &self,
        identity: &str,
        detail: &CodexGateDetail,
    ) -> Result<(), FileIoError> {
        let text = render_codex_gate_detail(identity, detail);
        if text.is_empty()
            || atomic_write_utf8_in(
                &self.root,
                &self.gate_detail_path(identity),
                &text,
                true,
                CACHE_FILE_MODE,
            )
            .is_err()
        {
            return self.clear_gate_detail(identity);
        }
        Ok(())
    }

    /// Remove the cached Codex gate detail for one identity.
    ///
    /// # Errors
    /// Returns when the path is unsafe or removal fails for a reason other
    /// than the entry already being absent.
    pub fn clear_gate_detail(&self, identity: &str) -> Result<(), FileIoError> {
        let path = self.gate_detail_path(identity);
        match fs::symlink_metadata(&path) {
            Ok(metadata) if metadata.file_type().is_symlink() => return Ok(()),
            Ok(_) => {}
            Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(()),
            Err(error) => return Err(io_error(&path, &error)),
        }
        let confined = self
            .root
            .confine(&path, PathIntent::Cleanup)
            .map_err(|error| path_safety_error(&path, &error))?;
        absent_is_success(fs::remove_file(confined.path()))
            .map_err(|error| io_error(confined.path(), &error))
    }

    /// Take the exclusive update lock for one Codex probe identity.
    ///
    /// Concurrent probes serialize here, so exactly one of them runs the
    /// vendor and publishes a gate detail while the others wait and then
    /// observe the freshly written verdict.
    ///
    /// # Errors
    /// Returns when the lock path is unsafe or cannot be opened or locked.
    pub fn update_lock(&self, identity: &str) -> Result<ProbeUpdateLock, FileIoError> {
        let path = self
            .root
            .path()
            .join(codex_probe_update_lock_file_name(identity, &self.user));
        let confined = self
            .root
            .confine(&path, PathIntent::Cache)
            .map_err(|error| path_safety_error(&path, &error))?;
        ProbeUpdateLock::acquire(&confined)
    }

    fn stamp_path(&self, kind: &str) -> PathBuf {
        self.root
            .path()
            .join(probe_stamp_file_name(kind, &self.user))
    }

    fn gate_detail_path(&self, identity: &str) -> PathBuf {
        self.root
            .path()
            .join(codex_gate_detail_file_name(identity, &self.user))
    }
}

/// One cache entry read under a single `stat`, so its contents and its
/// modification time describe the same observation.
struct CacheEntry {
    contents: String,
    modified: SystemTime,
}

impl CacheEntry {
    fn read(path: &Path) -> Option<Self> {
        let modified = modification_time(path)?;
        let bytes = fs::read(path).ok()?;
        Some(Self {
            contents: String::from_utf8_lossy(&bytes).into_owned(),
            modified,
        })
    }
}

/// Return a regular, non-symlinked file's modification time.
fn modification_time(path: &Path) -> Option<SystemTime> {
    let metadata = fs::symlink_metadata(path).ok()?;
    if !metadata.is_file() || metadata.file_type().is_symlink() {
        return None;
    }
    metadata.modified().ok()
}

/// Held exclusive update lock. Dropping it releases the lock.
#[derive(Debug)]
pub struct ProbeUpdateLock {
    #[cfg(unix)]
    _flock: nix::fcntl::Flock<fs::File>,
    #[cfg(not(unix))]
    _file: fs::File,
}

impl ProbeUpdateLock {
    #[cfg(unix)]
    fn acquire(path: &ConfinedPath) -> Result<Self, FileIoError> {
        use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};

        let file = fs::OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .mode(CACHE_FILE_MODE)
            .custom_flags(nix::libc::O_NOFOLLOW)
            .open(path.path())
            .map_err(|error| io_error(path.path(), &error))?;
        let metadata = file
            .metadata()
            .map_err(|error| io_error(path.path(), &error))?;
        if !metadata.is_file() {
            return Err(io_error(
                path.path(),
                &io::Error::other("refusing a non-regular probe update lock"),
            ));
        }
        if metadata.permissions().mode() & 0o077 != 0 {
            fs::set_permissions(path.path(), fs::Permissions::from_mode(CACHE_FILE_MODE))
                .map_err(|error| io_error(path.path(), &error))?;
        }
        let flock = nix::fcntl::Flock::lock(file, nix::fcntl::FlockArg::LockExclusive)
            .map_err(|(_file, errno)| io_error(path.path(), &io::Error::from(errno)))?;
        Ok(Self { _flock: flock })
    }

    #[cfg(not(unix))]
    fn acquire(path: &ConfinedPath) -> Result<Self, FileIoError> {
        let file = fs::OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(path.path())
            .map_err(|error| io_error(path.path(), &error))?;
        Ok(Self { _file: file })
    }
}

// Behavioral coverage lives in `tests/vendor_auth.rs`, which exercises this
// module through its public composition boundary.
