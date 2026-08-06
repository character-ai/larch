//! Filesystem adapters for vendor startup locks and stall diagnostics.
//!
//! Process creation and termination stay in [`crate::process`]. Artifact paths
//! are explicit so this module does not duplicate the launcher suffix owner.

use crate::{
    FileIoError, PathIntent, PathSafetyError, TemporaryRoot, atomic_write_utf8_in,
    file_io::absent_is_success,
};
use larch_core::{
    CursorStallRecord, ExitCode, LauncherArtifactKind, LauncherArtifactPaths, TimeoutStallRecord,
    VendorProgram, render_cursor_stall_json, render_timeout_stall_json,
};
use std::{
    error::Error,
    fmt, fs, io,
    path::Path,
    thread::{self, JoinHandle},
    time::{Duration, SystemTime, UNIX_EPOCH},
};

const DEFAULT_LOCK_TTL: Duration = Duration::from_secs(30);
const DEFAULT_LOCK_TRIES: usize = 300;
const DEFAULT_LOCK_RETRY_DELAY: Duration = Duration::from_millis(100);
const DEFAULT_LOCK_RELEASE_DELAY: Duration = Duration::from_millis(500);
const DIAGNOSTIC_FILE_MODE: u32 = 0o600;

/// Explicit Darwin startup-lock configuration resolved by composition code.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StartupLockConfig {
    program: VendorProgram,
    darwin: bool,
    user: String,
    ttl: Duration,
    tries: usize,
    retry_delay: Duration,
    release_delay: Duration,
}

impl StartupLockConfig {
    /// Parse the legacy environment values without reading ambient process state.
    ///
    /// Empty users retain the legacy `larch` fallback. Invalid non-empty user
    /// names are rejected so a lock cannot escape the supplied temporary root.
    ///
    /// # Errors
    /// Returns [`StartupLockError::UnsafeUser`] for a path-bearing user name.
    pub fn from_values(
        program: VendorProgram,
        platform: &str,
        user: Option<&str>,
        ttl: Option<&str>,
        tries: Option<&str>,
        release_delay: Option<&str>,
    ) -> Result<Self, StartupLockError> {
        let user = user.filter(|value| !value.is_empty()).unwrap_or("larch");
        if !user
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-' | b'.'))
        {
            return Err(StartupLockError::UnsafeUser);
        }
        Ok(Self {
            program,
            darwin: platform == "Darwin",
            user: user.to_owned(),
            ttl: positive_seconds(ttl).unwrap_or(DEFAULT_LOCK_TTL),
            tries: positive_usize(tries).unwrap_or(DEFAULT_LOCK_TRIES),
            retry_delay: DEFAULT_LOCK_RETRY_DELAY,
            release_delay: nonnegative_seconds(release_delay).unwrap_or(DEFAULT_LOCK_RELEASE_DELAY),
        })
    }

    /// Override the retry interval for deterministic integration tests.
    #[must_use]
    pub const fn with_retry_delay(mut self, retry_delay: Duration) -> Self {
        self.retry_delay = retry_delay;
        self
    }

    const fn enabled(&self) -> bool {
        self.darwin && matches!(self.program, VendorProgram::Codex | VendorProgram::Cursor)
    }

    fn basename(&self) -> String {
        format!("larch-external-startup-{}.lock", self.user)
    }
}

fn positive_seconds(value: Option<&str>) -> Option<Duration> {
    let seconds = positive_usize(value)?;
    Some(Duration::from_secs(u64::try_from(seconds).ok()?))
}

fn positive_usize(value: Option<&str>) -> Option<usize> {
    let value = value?;
    if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    value.parse().ok().filter(|parsed| *parsed > 0)
}

fn nonnegative_seconds(value: Option<&str>) -> Option<Duration> {
    let seconds: f64 = value?.parse().ok()?;
    if !seconds.is_finite() || seconds < 0.0 {
        return None;
    }
    Duration::try_from_secs_f64(seconds).ok()
}

/// Startup lock acquisition, release, or validation failure.
#[derive(Debug)]
pub enum StartupLockError {
    /// The user component could alter the lock path.
    UnsafeUser,
    /// The configured temporary root or lock path failed confinement.
    Path(PathSafetyError),
    /// A filesystem or release-thread operation failed.
    Io(io::Error),
    /// The delayed release thread panicked.
    ReleasePanicked,
}

impl fmt::Display for StartupLockError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::UnsafeUser => formatter.write_str("startup lock user contains unsafe bytes"),
            Self::Path(error) => write!(formatter, "startup lock path is unsafe: {error}"),
            Self::Io(error) => write!(formatter, "startup lock I/O failed: {error}"),
            Self::ReleasePanicked => formatter.write_str("startup lock release thread panicked"),
        }
    }
}

impl Error for StartupLockError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Path(error) => Some(error),
            Self::Io(error) => Some(error),
            Self::UnsafeUser | Self::ReleasePanicked => None,
        }
    }
}

impl From<PathSafetyError> for StartupLockError {
    fn from(error: PathSafetyError) -> Self {
        Self::Path(error)
    }
}

impl From<io::Error> for StartupLockError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

/// Owned startup-lock state. Dropping an unreleased lock removes it immediately.
#[derive(Debug)]
pub struct StartupLockState {
    path: Option<crate::ConfinedPath>,
}

impl StartupLockState {
    /// Return whether this invocation acquired the lock.
    #[must_use]
    pub const fn is_acquired(&self) -> bool {
        self.path.is_some()
    }
}

impl Drop for StartupLockState {
    fn drop(&mut self) {
        if let Some(path) = self.path.take() {
            let _removed = remove_lock(&path);
        }
    }
}

/// Acquire the shared Darwin Codex/Cursor startup lock with bounded retries.
///
/// Unsupported platforms and Claude return an unacquired state. Exhaustion is
/// also non-fatal, matching the legacy launcher.
///
/// # Errors
/// Returns a confinement or filesystem failure for an unsafe lock carrier.
pub fn external_startup_lock_acquire(
    temporary_root: &TemporaryRoot,
    config: &StartupLockConfig,
) -> Result<StartupLockState, StartupLockError> {
    if !config.enabled() {
        return Ok(StartupLockState { path: None });
    }
    let lock_path = temporary_root.path().join(config.basename());
    for _ in 0..config.tries {
        let candidate = temporary_root.confine(&lock_path, PathIntent::Cache)?;
        let mut builder = fs::DirBuilder::new();
        #[cfg(unix)]
        {
            use std::os::unix::fs::DirBuilderExt;
            builder.mode(0o700);
        }
        match builder.create(candidate.path()) {
            Ok(()) => {
                let acquired = match temporary_root.confine(&lock_path, PathIntent::Cache) {
                    Ok(acquired) => acquired,
                    Err(error) => {
                        let _removed = remove_lock(&candidate);
                        return Err(error.into());
                    }
                };
                return Ok(StartupLockState {
                    path: Some(acquired),
                });
            }
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => {
                if lock_is_stale(&candidate, config.ttl) && remove_lock(&candidate).is_ok() {
                    continue;
                }
            }
            Err(error) => return Err(error.into()),
        }
        if !config.retry_delay.is_zero() {
            thread::sleep(config.retry_delay);
        }
    }
    Ok(StartupLockState { path: None })
}

fn lock_is_stale(path: &crate::ConfinedPath, ttl: Duration) -> bool {
    path.revalidate().is_ok()
        && fs::symlink_metadata(path.path())
            .ok()
            .and_then(|metadata| metadata.modified().ok())
            .and_then(|modified| modified.elapsed().ok())
            .is_some_and(|age| age >= ttl)
}

fn remove_lock(path: &crate::ConfinedPath) -> Result<(), StartupLockError> {
    path.revalidate()?;
    absent_is_success(fs::remove_dir(path.path())).map_err(Into::into)
}

/// Handle that owns the non-daemon-equivalent delayed release.
///
/// Dropping this handle joins the release thread. Keep it alive while starting
/// the vendor so the delay overlaps launch work rather than blocking it.
#[must_use = "keep the delayed startup-lock release alive through vendor startup"]
pub struct StartupLockRelease {
    handle: Option<JoinHandle<Result<(), StartupLockError>>>,
}

impl StartupLockRelease {
    /// Wait for delayed release and surface its error.
    ///
    /// # Errors
    /// Returns a removal failure or release-thread panic.
    pub fn wait(mut self) -> Result<(), StartupLockError> {
        join_release(self.handle.take())
    }
}

impl Drop for StartupLockRelease {
    fn drop(&mut self) {
        let _released = join_release(self.handle.take());
    }
}

/// Acquire-and-release wrapper that keeps the startup lock scoped to a block.
pub struct StartupLockGuard {
    _release: Option<StartupLockRelease>,
}

impl StartupLockGuard {
    /// Best-effort acquire; lock failure leaves an unlocked guard.
    #[must_use]
    pub fn acquire(temporary_root: &TemporaryRoot, config: &StartupLockConfig) -> Self {
        let release = external_startup_lock_acquire(temporary_root, config)
            .and_then(|state| external_startup_lock_release_after(state, config))
            .ok();
        Self { _release: release }
    }
}

fn join_release(
    handle: Option<JoinHandle<Result<(), StartupLockError>>>,
) -> Result<(), StartupLockError> {
    match handle {
        Some(handle) => handle
            .join()
            .map_err(|_panic| StartupLockError::ReleasePanicked)?,
        None => Ok(()),
    }
}

/// Schedule release after the configured post-acquisition delay.
///
/// # Errors
/// Returns when the release thread cannot start.
pub fn external_startup_lock_release_after(
    mut state: StartupLockState,
    config: &StartupLockConfig,
) -> Result<StartupLockRelease, StartupLockError> {
    let Some(path) = state.path.take() else {
        return Ok(StartupLockRelease { handle: None });
    };
    let delay = config.release_delay;
    let release_path = path.clone();
    let handle = match thread::Builder::new()
        .name("larch-vendor-startup-lock-release".to_owned())
        .spawn(move || {
            thread::sleep(delay);
            remove_lock(&release_path)
        }) {
        Ok(handle) => handle,
        Err(error) => {
            let _removed = remove_lock(&path);
            return Err(error.into());
        }
    };
    Ok(StartupLockRelease {
        handle: Some(handle),
    })
}

/// Return the newest regular-file modification time below a tree.
///
/// `.git` directories, symlinked directories, and unreadable entries are
/// skipped. The marker is seconds since the Unix epoch, matching `st_mtime`.
#[must_use]
pub fn tree_latest_mtime(root: &Path) -> f64 {
    let mut latest = 0.0_f64;
    let mut pending = vec![root.to_path_buf()];
    while let Some(directory) = pending.pop() {
        let Ok(entries) = fs::read_dir(directory) else {
            continue;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            let Ok(file_type) = entry.file_type() else {
                continue;
            };
            if file_type.is_dir() {
                if entry.file_name() != ".git" {
                    pending.push(path);
                }
            } else if let Ok(metadata) = entry.metadata()
                && metadata.is_file()
                && let Ok(modified) = metadata.modified()
            {
                latest = latest.max(system_time_marker(modified));
            }
        }
    }
    latest
}

fn system_time_marker(time: SystemTime) -> f64 {
    match time.duration_since(UNIX_EPOCH) {
        Ok(duration) => duration.as_secs_f64(),
        Err(error) => -error.duration().as_secs_f64(),
    }
}

/// Measure one legacy stall channel and report whether its marker changed.
#[must_use]
#[allow(
    clippy::cast_precision_loss,
    clippy::float_cmp,
    reason = "legacy stall markers are exact st_size plus st_mtime f64 values"
)]
pub fn stall_channel_progress(channel: &str, output_file: &Path, last_marker: f64) -> (bool, f64) {
    let marker = if channel == "stdout" {
        regular_file_metadata(output_file).map_or(0.0, |metadata| metadata.len() as f64)
    } else if let Some(root) = channel.strip_prefix("tree:") {
        tree_latest_mtime(Path::new(root))
    } else if let Some(file) = channel.strip_prefix("file:") {
        regular_file_metadata(Path::new(file)).map_or(0.0, |metadata| {
            metadata.len() as f64 + metadata.modified().map_or(0.0, system_time_marker)
        })
    } else {
        return (false, last_marker);
    };
    (marker != last_marker, marker)
}

fn regular_file_metadata(path: &Path) -> Option<fs::Metadata> {
    fs::metadata(path).ok().filter(fs::Metadata::is_file)
}

/// Publish the detailed Cursor stall payload to caller-supplied artifact paths.
///
/// # Errors
/// Returns a confined-write failure for the primary artifact. The optional
/// compatibility sidecar is best effort, matching the legacy launcher.
pub fn write_cursor_ci_stall_artifacts(
    root: &TemporaryRoot,
    paths: &LauncherArtifactPaths,
    sidecar: Option<&Path>,
    record: &CursorStallRecord,
) -> Result<(), FileIoError> {
    let text = render_cursor_stall_json(record);
    atomic_write_utf8_in(
        root,
        &paths.path(LauncherArtifactKind::StallJson),
        &text,
        true,
        DIAGNOSTIC_FILE_MODE,
    )?;
    if let Some(sidecar) = sidecar {
        let _sidecar_written =
            atomic_write_utf8_in(root, sidecar, &text, true, DIAGNOSTIC_FILE_MODE);
    }
    Ok(())
}

/// Conditionally publish the compact timeout stall payload.
///
/// Returns false for a non-timeout exit or an existing regular artifact when
/// overwrite is disabled.
///
/// # Errors
/// Returns a confined-write failure.
pub fn write_timeout_stall_json(
    root: &TemporaryRoot,
    paths: &LauncherArtifactPaths,
    record: &TimeoutStallRecord<'_>,
    overwrite: bool,
) -> Result<bool, FileIoError> {
    if record.exit_code != ExitCode::Timeout.value() {
        return Ok(false);
    }
    let target = paths.path(LauncherArtifactKind::StallJson);
    if !overwrite && regular_file_metadata(&target).is_some() {
        return Ok(false);
    }
    atomic_write_utf8_in(
        root,
        &target,
        &render_timeout_stall_json(record),
        true,
        DIAGNOSTIC_FILE_MODE,
    )?;
    Ok(true)
}
