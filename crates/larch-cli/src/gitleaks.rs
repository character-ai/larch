//! Checksum-pinned Gitleaks bootstrap and scanner command.
//!
//! # Crate survey (issue #8096)
//!
//! | Need | Candidates | Selection |
//! | --- | --- | --- |
//! | Public release download | direct HTTP client, `larch-adapters` GitHub release service | Reuse the adapter-owned anonymous public-release downloader so this command owns no HTTP client or URL construction. |
//! | Gzip tar extraction | hand-written tar parser, workspace `flate2`, `tar` | Use maintained `flate2` and `tar`; bespoke code owns only the pinned artifact and checksum policy. |
//! | External scanner execution | direct `Command`, `TokioProcessRunner` | Use the shared typed process runner and its closed `ScannerProgram` allowlist. |

use std::{
    env,
    ffi::OsString,
    fs,
    future::Future,
    io::{Read as _, Write as _},
    num::NonZeroUsize,
    path::{Component, Path, PathBuf},
    pin::Pin,
    process::ExitCode,
    time::Duration,
};

use flate2::read::GzDecoder;
use larch_adapters::{
    GitRef, TokioProcessRunner,
    github::{PublicReleaseAsset, PublicReleaseDownloader, ReleaseServiceError},
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    ExternalProcessRunner, ExternalProgram, ProcessOutput, ProcessRequest, ScannerProgram,
};
use larch_lint::{GitleaksArguments, GitleaksMode};
use sha2::{Digest as _, Sha256};

const VERSION: &str = "8.18.4";
const ARCHIVE_MAX_BYTES: u64 = 16 * 1024 * 1024;
const BINARY_MAX_BYTES: u64 = 32 * 1024 * 1024;
const VERSION_TIMEOUT: Duration = Duration::from_secs(10);
const SCAN_TIMEOUT: Duration = Duration::from_secs(15 * 60);
const SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
const OUTPUT_LIMIT: usize = 16 * 1024 * 1024;

#[derive(Clone, Copy)]
struct Artifact {
    filename: &'static str,
    archive_sha256: &'static str,
    binary_sha256: &'static str,
}

#[derive(Clone, Copy)]
struct Platform {
    system: &'static str,
    architecture: &'static str,
    artifact: Artifact,
}

#[derive(Debug)]
enum Failure {
    Configuration(String),
    Preparation(String),
}

impl Failure {
    fn configuration(message: impl Into<String>) -> Self {
        Self::Configuration(message.into())
    }

    fn preparation(message: impl Into<String>) -> Self {
        Self::Preparation(message.into())
    }
}

type DownloadFuture<'a> =
    Pin<Box<dyn Future<Output = Result<Vec<u8>, ReleaseServiceError>> + Send + 'a>>;

/// Injectable boundary for the adapter-owned public release download.
trait ReleaseAssetDownloader: Send + Sync {
    fn download<'a>(&'a self, asset: &'a PublicReleaseAsset) -> DownloadFuture<'a>;
}

impl ReleaseAssetDownloader for PublicReleaseDownloader {
    fn download<'a>(&'a self, asset: &'a PublicReleaseAsset) -> DownloadFuture<'a> {
        Box::pin(Self::download(self, asset))
    }
}

/// Run the checksum-pinned Gitleaks command.
#[must_use]
pub fn run(arguments: &GitleaksArguments) -> ExitCode {
    match run_inner(arguments) {
        Ok(exit) => exit,
        Err(Failure::Configuration(message)) => {
            eprintln!("ERROR: {message}");
            ExitCode::from(2)
        }
        Err(Failure::Preparation(message)) => {
            eprintln!("ERROR: could not prepare gitleaks {VERSION}: {message}");
            ExitCode::from(2)
        }
    }
}

fn run_inner(arguments: &GitleaksArguments) -> Result<ExitCode, Failure> {
    let repository = repository_root(arguments.repo_root())?;
    require_config(&repository)?;
    let cache_root = cache_root(arguments.cache_dir())?;
    let runtime = LarchRuntime::new().map_err(|error| {
        Failure::preparation(format!("cannot initialize larch runtime: {error}"))
    })?;
    runtime.block_on(run_async(arguments, &repository, &cache_root))
}

async fn run_async(
    arguments: &GitleaksArguments,
    repository: &Path,
    cache_root: &Path,
) -> Result<ExitCode, Failure> {
    let downloader =
        PublicReleaseDownloader::new().map_err(|error| Failure::preparation(error.to_string()))?;
    let runner = TokioProcessRunner::default();
    run_async_with(arguments, repository, cache_root, &downloader, &runner).await
}

async fn run_async_with<D, R>(
    arguments: &GitleaksArguments,
    repository: &Path,
    cache_root: &Path,
    downloader: &D,
    runner: &R,
) -> Result<ExitCode, Failure>
where
    D: ReleaseAssetDownloader + ?Sized,
    R: ExternalProcessRunner + ?Sized,
{
    run_async_with_platform(
        arguments,
        repository,
        cache_root,
        platform()?,
        downloader,
        runner,
    )
    .await
}

async fn run_async_with_platform<D, R>(
    arguments: &GitleaksArguments,
    repository: &Path,
    cache_root: &Path,
    platform: Platform,
    downloader: &D,
    runner: &R,
) -> Result<ExitCode, Failure>
where
    D: ReleaseAssetDownloader + ?Sized,
    R: ExternalProcessRunner + ?Sized,
{
    let binary = ensure_binary_with_platform(cache_root, platform, downloader).await?;
    let scanner = ScannerProgram::gitleaks(binary);
    let cancellation = Cancellation::new();
    let version = run_scanner(
        runner,
        &cancellation,
        repository,
        &scanner,
        [OsString::from("version")],
        VERSION_TIMEOUT,
    )
    .await?;
    if !version.status().success()
        || version.stdout_truncated()
        || version.stderr_truncated()
        || std::str::from_utf8(version.stdout()).ok().map(str::trim) != Some(VERSION)
    {
        relay(&version)?;
        return Err(Failure::preparation(format!(
            "expected gitleaks version {VERSION}"
        )));
    }
    if arguments.mode() == GitleaksMode::Verify {
        relay(&version)?;
        return Ok(ExitCode::SUCCESS);
    }
    let scanner_arguments = scanner_arguments(arguments, repository)?;
    let scan = run_scanner(
        runner,
        &cancellation,
        repository,
        &scanner,
        scanner_arguments,
        SCAN_TIMEOUT,
    )
    .await?;
    relay(&scan)?;
    Ok(process_exit_code(&scan))
}

fn repository_root(value: Option<&Path>) -> Result<PathBuf, Failure> {
    let current = env::current_dir().map_err(|error| {
        Failure::configuration(format!("cannot resolve current directory: {error}"))
    })?;
    let candidate = value.map_or_else(
        || current.clone(),
        |path| {
            if path.is_absolute() {
                path.to_path_buf()
            } else {
                current.join(path)
            }
        },
    );
    fs::canonicalize(&candidate).map_err(|error| {
        Failure::configuration(format!("cannot resolve gitleaks repository root: {error}"))
    })
}

fn require_config(repository: &Path) -> Result<(), Failure> {
    let path = repository.join(".gitleaks.toml");
    let metadata = fs::symlink_metadata(&path).map_err(|_| {
        Failure::configuration(format!(
            "required gitleaks config is not a regular file: {}",
            path.display()
        ))
    })?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(Failure::configuration(format!(
            "required gitleaks config is not a regular file: {}",
            path.display()
        )));
    }
    Ok(())
}

fn cache_root(value: Option<&Path>) -> Result<PathBuf, Failure> {
    let candidate = match value {
        Some(path) => path.to_path_buf(),
        None => default_cache_root()?,
    };
    if candidate.is_absolute() {
        return Ok(candidate);
    }
    let current = env::current_dir().map_err(|error| {
        Failure::preparation(format!("cannot resolve current directory: {error}"))
    })?;
    Ok(current.join(candidate))
}

fn default_cache_root() -> Result<PathBuf, Failure> {
    if let Some(value) = env::var_os("XDG_CACHE_HOME").filter(|value| !value.is_empty()) {
        return Ok(PathBuf::from(value).join("larch/tools/gitleaks"));
    }
    let home = env::var_os("HOME")
        .filter(|value| !value.is_empty())
        .ok_or_else(|| Failure::preparation("cannot resolve home directory for gitleaks cache"))?;
    Ok(PathBuf::from(home).join(".cache/larch/tools/gitleaks"))
}

async fn ensure_binary_with_platform<D>(
    cache_root: &Path,
    platform: Platform,
    downloader: &D,
) -> Result<PathBuf, Failure>
where
    D: ReleaseAssetDownloader + ?Sized,
{
    let binary = ensure_binary_for(cache_root, platform, downloader).await?;
    if !is_verified_binary(&binary, platform.artifact.binary_sha256)? {
        return Err(Failure::preparation(
            "cached gitleaks binary did not retain its verified identity",
        ));
    }
    set_executable(&binary)?;
    Ok(binary)
}

async fn ensure_binary_for<D>(
    cache_root: &Path,
    platform: Platform,
    downloader: &D,
) -> Result<PathBuf, Failure>
where
    D: ReleaseAssetDownloader + ?Sized,
{
    let destination = cache_root
        .join(VERSION)
        .join(format!("{}-{}", platform.system, platform.architecture))
        .join("gitleaks");
    let parent = destination
        .parent()
        .ok_or_else(|| Failure::preparation("gitleaks cache path has no parent"))?;
    ensure_cache_directory(parent)?;
    if is_verified_binary(&destination, platform.artifact.binary_sha256)? {
        set_executable(&destination)?;
        return Ok(destination);
    }
    let asset = PublicReleaseAsset::new(
        "gitleaks",
        "gitleaks",
        &format!("v{VERSION}"),
        platform.artifact.filename,
        ARCHIVE_MAX_BYTES,
    )
    .map_err(|error| Failure::preparation(error.to_string()))?;
    let archive = downloader
        .download(&asset)
        .await
        .map_err(|error| Failure::preparation(error.to_string()))?;
    if sha256(&archive) != platform.artifact.archive_sha256 {
        return Err(Failure::preparation(format!(
            "checksum mismatch for {}",
            platform.artifact.filename
        )));
    }
    let binary = extract_binary(&archive)?;
    if sha256(&binary) != platform.artifact.binary_sha256 {
        return Err(Failure::preparation(format!(
            "extracted binary checksum mismatch for {}",
            platform.artifact.filename
        )));
    }
    let temporary = tempfile::Builder::new()
        .prefix("install-")
        .tempdir_in(parent)
        .map_err(|error| Failure::preparation(format!("cannot stage gitleaks binary: {error}")))?;
    let staged = temporary.path().join("gitleaks");
    fs::write(&staged, binary)
        .map_err(|error| Failure::preparation(format!("cannot write gitleaks binary: {error}")))?;
    set_executable(&staged)?;
    ensure_cache_destination(&destination)?;
    fs::rename(&staged, &destination).map_err(|error| {
        Failure::preparation(format!("cannot install gitleaks binary: {error}"))
    })?;
    if !is_verified_binary(&destination, platform.artifact.binary_sha256)? {
        return Err(Failure::preparation(
            "installed gitleaks binary did not retain its verified identity",
        ));
    }
    set_executable(&destination)?;
    Ok(destination)
}

fn platform() -> Result<Platform, Failure> {
    platform_for(env::consts::OS, env::consts::ARCH)
}

fn platform_for(system_input: &str, architecture_input: &str) -> Result<Platform, Failure> {
    let system = match system_input {
        "macos" | "darwin" => "darwin",
        "linux" => "linux",
        other => return Err(unsupported_platform(other, architecture_input)),
    };
    let architecture = match architecture_input {
        "aarch64" | "arm64" => "arm64",
        "x86_64" | "amd64" => "x64",
        other => return Err(unsupported_platform(system, other)),
    };
    let artifact = match (system, architecture) {
        ("darwin", "arm64") => Artifact {
            filename: "gitleaks_8.18.4_darwin_arm64.tar.gz",
            archive_sha256: "a480d8593acd8215b22402cf0f3f88b01dcd3610c63b5391db640f7767e62104",
            binary_sha256: "a86787a498e702f8820fc73c219ca44ecdf1f415eed8daf922888ffd6c4cf680",
        },
        ("darwin", "x64") => Artifact {
            filename: "gitleaks_8.18.4_darwin_x64.tar.gz",
            archive_sha256: "1a69e5666b13cd374889cbcb1939ed1573b63b551251283d5d2329a53cf58e2f",
            binary_sha256: "3f83ea726b8f10c16dfa7ea08c73d1474ddbfe24db4a00e6764ec9abac05e19e",
        },
        ("linux", "arm64") => Artifact {
            filename: "gitleaks_8.18.4_linux_arm64.tar.gz",
            archive_sha256: "bf5f7f466ebfade1296c8bd32cf7d3f592c2aa78836aa9980ffbe2cadca7a861",
            binary_sha256: "fc286fab02c3a0ba80670fc9f8cb1b495a2f62eb953d26113cfa3562f76b340b",
        },
        ("linux", "x64") => Artifact {
            filename: "gitleaks_8.18.4_linux_x64.tar.gz",
            archive_sha256: "ba6dbb656933921c775ee5a2d1c13a91046e7952e9d919f9bac4cec61d628e7d",
            binary_sha256: "46a05260e7cce527f132cb618de59d22262b8b5eb47f66c288447b95c7a98b7e",
        },
        _ => return Err(unsupported_platform(system, architecture)),
    };
    Ok(Platform {
        system,
        architecture,
        artifact,
    })
}

fn unsupported_platform(system: &str, architecture: &str) -> Failure {
    Failure::preparation(format!(
        "unsupported gitleaks platform: {system}/{architecture}"
    ))
}

fn is_verified_binary(path: &Path, expected: &str) -> Result<bool, Failure> {
    let metadata = match fs::symlink_metadata(path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(false),
        Err(error) => {
            return Err(Failure::preparation(format!(
                "cannot inspect cached gitleaks binary: {error}"
            )));
        }
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(Failure::preparation(format!(
            "cached gitleaks binary is not a regular file: {}",
            path.display()
        )));
    }
    sha256_file(path).map(|actual| actual == expected)
}

fn ensure_cache_directory(path: &Path) -> Result<(), Failure> {
    if !path.is_absolute() {
        return Err(Failure::preparation(format!(
            "gitleaks cache path must be absolute: {}",
            path.display()
        )));
    }
    let mut current = PathBuf::new();
    for component in path.components() {
        match component {
            Component::Prefix(prefix) => current.push(prefix.as_os_str()),
            Component::RootDir => current.push(component.as_os_str()),
            Component::Normal(segment) => {
                current.push(segment);
                ensure_real_directory(&current)?;
            }
            Component::CurDir | Component::ParentDir => {
                return Err(Failure::preparation(format!(
                    "gitleaks cache path contains an unsafe component: {}",
                    path.display()
                )));
            }
        }
    }
    Ok(())
}

fn ensure_real_directory(path: &Path) -> Result<(), Failure> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if !metadata.file_type().is_symlink() && metadata.is_dir() => Ok(()),
        Ok(_) => Err(Failure::preparation(format!(
            "gitleaks cache directory is not a real directory: {}",
            path.display()
        ))),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => match fs::create_dir(path) {
            Ok(()) => Ok(()),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {
                ensure_real_directory(path)
            }
            Err(error) => Err(Failure::preparation(format!(
                "cannot create gitleaks cache directory {}: {error}",
                path.display()
            ))),
        },
        Err(error) => Err(Failure::preparation(format!(
            "cannot inspect gitleaks cache directory {}: {error}",
            path.display()
        ))),
    }
}

fn ensure_cache_destination(path: &Path) -> Result<(), Failure> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if !metadata.file_type().is_symlink() && metadata.is_file() => Ok(()),
        Ok(_) => Err(Failure::preparation(format!(
            "cached gitleaks binary is not a regular file: {}",
            path.display()
        ))),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(Failure::preparation(format!(
            "cannot inspect cached gitleaks binary {}: {error}",
            path.display()
        ))),
    }
}

fn extract_binary(archive: &[u8]) -> Result<Vec<u8>, Failure> {
    let decoder = GzDecoder::new(archive);
    let mut bundle = tar::Archive::new(decoder);
    let entries = bundle.entries().map_err(|error| {
        Failure::preparation(format!("cannot read gitleaks release archive: {error}"))
    })?;
    for entry in entries {
        let mut entry = entry.map_err(|error| {
            Failure::preparation(format!("cannot read gitleaks release archive: {error}"))
        })?;
        if entry.path().map_err(|error| {
            Failure::preparation(format!("cannot read gitleaks archive path: {error}"))
        })? != Path::new("gitleaks")
        {
            continue;
        }
        let size = entry.size();
        if !entry.header().entry_type().is_file() || size == 0 || size > BINARY_MAX_BYTES {
            return Err(Failure::preparation(
                "gitleaks release archive has an invalid binary member",
            ));
        }
        let capacity = usize::try_from(size)
            .map_err(|_| Failure::preparation("gitleaks release binary is too large"))?;
        let mut binary = Vec::with_capacity(capacity);
        entry.read_to_end(&mut binary).map_err(|error| {
            Failure::preparation(format!("cannot read gitleaks release binary: {error}"))
        })?;
        if u64::try_from(binary.len()).ok() != Some(size) || binary.len() as u64 > BINARY_MAX_BYTES
        {
            return Err(Failure::preparation(
                "gitleaks release binary size does not match its archive member",
            ));
        }
        return Ok(binary);
    }
    Err(Failure::preparation(
        "gitleaks release archive has no gitleaks binary",
    ))
}

fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn sha256_file(path: &Path) -> Result<String, Failure> {
    let mut file = fs::File::open(path).map_err(|error| {
        Failure::preparation(format!("cannot read cached gitleaks binary: {error}"))
    })?;
    let mut digest = Sha256::new();
    let mut buffer = vec![0_u8; 1024 * 1024];
    loop {
        let read = file.read(&mut buffer).map_err(|error| {
            Failure::preparation(format!("cannot read cached gitleaks binary: {error}"))
        })?;
        if read == 0 {
            return Ok(format!("{:x}", digest.finalize()));
        }
        digest.update(&buffer[..read]);
    }
}

fn set_executable(path: &Path) -> Result<(), Failure> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt as _;

        let metadata = fs::symlink_metadata(path).map_err(|error| {
            Failure::preparation(format!("cannot inspect gitleaks binary: {error}"))
        })?;
        if metadata.file_type().is_symlink() || !metadata.is_file() {
            return Err(Failure::preparation(format!(
                "gitleaks binary is not a regular file: {}",
                path.display()
            )));
        }
        let mut permissions = metadata.permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(path, permissions).map_err(|error| {
            Failure::preparation(format!("cannot mark gitleaks binary executable: {error}"))
        })?;
    }
    #[cfg(not(unix))]
    let _ = path;
    Ok(())
}

fn scanner_arguments(
    arguments: &GitleaksArguments,
    repository: &Path,
) -> Result<Vec<OsString>, Failure> {
    scan_arguments_for(arguments.mode(), arguments.log_opts(), repository)
}

fn scan_arguments_for(
    mode: GitleaksMode,
    log_opts: Option<&str>,
    repository: &Path,
) -> Result<Vec<OsString>, Failure> {
    let config = repository.join(".gitleaks.toml");
    let mut result = vec![
        OsString::from("detect"),
        OsString::from("--source"),
        OsString::from("."),
        OsString::from("--config"),
        config.into_os_string(),
        OsString::from("--redact"),
        OsString::from("--no-banner"),
    ];
    match mode {
        GitleaksMode::WorkingTree => result.push(OsString::from("--no-git")),
        GitleaksMode::History => {
            let log_opts = log_opts
                .filter(|value| !value.is_empty())
                .ok_or_else(|| Failure::preparation("--log-opts is required for a history scan"))?;
            validate_history_range(log_opts)?;
            result.extend([OsString::from("--log-opts"), OsString::from(log_opts)]);
        }
        GitleaksMode::Verify => {
            return Err(Failure::preparation(
                "verify mode does not run a scanner command",
            ));
        }
    }
    Ok(result)
}

fn validate_history_range(value: &str) -> Result<(), Failure> {
    let mut parts = value.split("..");
    let base = parts.next().unwrap_or_default();
    let head = parts.next().unwrap_or_default();
    if parts.next().is_some()
        || base.is_empty()
        || head.is_empty()
        || base.ends_with('.')
        || head.starts_with('.')
        || GitRef::new(base).is_err()
        || GitRef::new(head).is_err()
    {
        return Err(Failure::preparation(
            "--log-opts must be one bounded <base>..<head> revision range",
        ));
    }
    Ok(())
}

async fn run_scanner<R>(
    runner: &R,
    cancellation: &Cancellation,
    repository: &Path,
    scanner: &ScannerProgram,
    arguments: impl IntoIterator<Item = OsString>,
    timeout: Duration,
) -> Result<ProcessOutput, Failure>
where
    R: ExternalProcessRunner + ?Sized,
{
    let request = ProcessRequest::new(
        ExternalProgram::Scanner(scanner.clone()),
        arguments,
        repository.to_path_buf(),
        timeout,
        SHUTDOWN_GRACE,
        NonZeroUsize::new(OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN),
    )
    .map_err(|error| Failure::preparation(error.to_string()))?;
    runner.run(request, cancellation).await.map_err(|error| {
        if let Some(output) = error.output() {
            let _ = relay(output);
        }
        Failure::preparation(error.to_string())
    })
}

fn relay(output: &ProcessOutput) -> Result<(), Failure> {
    // Gitleaks itself runs with `--redact`; relay its original output so the
    // former Python wrapper's user-visible scanner contract remains intact.
    std::io::stdout()
        .lock()
        .write_all(output.stdout())
        .map_err(|error| Failure::preparation(format!("cannot write gitleaks stdout: {error}")))?;
    std::io::stderr()
        .lock()
        .write_all(output.stderr())
        .map_err(|error| Failure::preparation(format!("cannot write gitleaks stderr: {error}")))
}

fn process_exit_code(output: &ProcessOutput) -> ExitCode {
    output
        .status()
        .code()
        .and_then(|code| u8::try_from(code).ok())
        .map_or_else(|| ExitCode::from(2), ExitCode::from)
}

#[cfg(test)]
mod tests {
    use super::*;
    use larch_core::{ProcessFuture, ProcessStatus};
    use std::sync::Mutex;

    struct FakeDownloader {
        archive: Vec<u8>,
        calls: Mutex<usize>,
    }

    impl FakeDownloader {
        fn new(archive: Vec<u8>) -> Self {
            Self {
                archive,
                calls: Mutex::new(0),
            }
        }
    }

    impl ReleaseAssetDownloader for FakeDownloader {
        fn download<'a>(&'a self, _asset: &'a PublicReleaseAsset) -> DownloadFuture<'a> {
            *self.calls.lock().expect("download calls") += 1;
            let archive = self.archive.clone();
            Box::pin(async move { Ok(archive) })
        }
    }

    #[derive(Default)]
    struct FakeRunner {
        requests: Mutex<Vec<ProcessRequest>>,
    }

    impl ExternalProcessRunner for FakeRunner {
        fn run<'a>(
            &'a self,
            request: ProcessRequest,
            _cancellation: &'a dyn larch_core::ProcessCancellation,
        ) -> ProcessFuture<'a> {
            self.requests.lock().expect("requests").push(request);
            Box::pin(async {
                Ok(ProcessOutput::new(
                    ProcessStatus::new(true, Some(0)),
                    format!("{VERSION}\n").into_bytes(),
                    Vec::new(),
                    false,
                    false,
                ))
            })
        }
    }

    struct QueueRunner {
        requests: Mutex<Vec<ProcessRequest>>,
        responses: Mutex<Vec<ProcessOutput>>,
    }

    impl QueueRunner {
        fn new(responses: Vec<ProcessOutput>) -> Self {
            Self {
                requests: Mutex::new(Vec::new()),
                responses: Mutex::new(responses),
            }
        }
    }

    impl ExternalProcessRunner for QueueRunner {
        fn run<'a>(
            &'a self,
            request: ProcessRequest,
            _cancellation: &'a dyn larch_core::ProcessCancellation,
        ) -> ProcessFuture<'a> {
            self.requests.lock().expect("requests").push(request);
            let output = self.responses.lock().expect("responses").remove(0);
            Box::pin(async move { Ok(output) })
        }
    }

    fn output(stdout: &[u8], success: bool, code: i32) -> ProcessOutput {
        ProcessOutput::new(
            ProcessStatus::new(success, Some(code)),
            stdout.to_vec(),
            Vec::new(),
            false,
            false,
        )
    }

    fn arguments(mode: GitleaksMode, log_opts: Option<&str>) -> GitleaksArguments {
        GitleaksArguments::new(mode, log_opts.map(str::to_owned), None, None)
    }

    fn fixture_repository(temporary: &tempfile::TempDir) -> PathBuf {
        let repository = temporary.path().join("repository");
        fs::create_dir(&repository).expect("repository directory");
        fs::write(repository.join(".gitleaks.toml"), "title = \"fixture\"\n")
            .expect("gitleaks config");
        fs::canonicalize(repository).expect("canonical repository")
    }

    #[test]
    fn extract_binary_accepts_only_the_regular_top_level_member() {
        let archive_bytes = archive("gitleaks", b"fixture");
        assert_eq!(
            extract_binary(&archive_bytes).expect("extract fixture"),
            b"fixture"
        );
        let wrong_name = archive("README.md", b"fixture");
        assert!(matches!(
            extract_binary(&wrong_name),
            Err(Failure::Preparation(message)) if message.contains("no gitleaks binary")
        ));
    }

    #[test]
    fn public_entrypoint_rejects_invalid_roots_and_config_shapes_before_download() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let missing = temporary.path().join("missing");
        let invalid_root = GitleaksArguments::new(GitleaksMode::Verify, None, Some(missing), None);
        assert_eq!(run(&invalid_root), ExitCode::from(2));

        let repository = temporary.path().join("repository");
        fs::create_dir(&repository).expect("repository directory");
        let missing_config =
            GitleaksArguments::new(GitleaksMode::Verify, None, Some(repository.clone()), None);
        assert!(matches!(
            run_inner(&missing_config),
            Err(Failure::Configuration(message)) if message.contains("not a regular file")
        ));

        let config = repository.join(".gitleaks.toml");
        fs::create_dir(&config).expect("config directory");
        assert!(matches!(
            require_config(&repository),
            Err(Failure::Configuration(message)) if message.contains("not a regular file")
        ));
        fs::remove_dir(&config).expect("remove config directory");
        fs::write(&config, "title = \"fixture\"\n").expect("regular config");
        assert_eq!(
            repository_root(Some(&repository)).expect("repository root"),
            fs::canonicalize(&repository).expect("canonical repository")
        );
        require_config(&repository).expect("regular config accepted");
    }

    #[test]
    fn pinned_platform_and_scanner_argument_contracts_are_closed() {
        let platform = platform().expect("supported test platform");
        assert!(platform.artifact.filename.contains(VERSION));
        let repository = Path::new("/tmp/gitleaks-fixture");
        let working = scanner_arguments_for(GitleaksMode::WorkingTree, None, repository)
            .expect("working tree arguments");
        assert_eq!(
            working,
            vec![
                "detect",
                "--source",
                ".",
                "--config",
                "/tmp/gitleaks-fixture/.gitleaks.toml",
                "--redact",
                "--no-banner",
                "--no-git",
            ]
        );
        assert!(scanner_arguments_for(GitleaksMode::History, None, repository).is_err());
        assert_eq!(
            scanner_arguments_for(GitleaksMode::History, Some("base..head"), repository)
                .expect("history arguments")
                .last(),
            Some(&"base..head".to_owned())
        );
        assert!(scanner_arguments_for(GitleaksMode::History, Some("--all"), repository).is_err());
        assert!(
            scanner_arguments_for(GitleaksMode::History, Some("base...head"), repository).is_err()
        );
    }

    #[test]
    fn every_supported_platform_uses_the_pinned_artifact_identity() {
        let cases = [
            (
                "darwin",
                "arm64",
                "gitleaks_8.18.4_darwin_arm64.tar.gz",
                "a480d8593acd8215b22402cf0f3f88b01dcd3610c63b5391db640f7767e62104",
                "a86787a498e702f8820fc73c219ca44ecdf1f415eed8daf922888ffd6c4cf680",
            ),
            (
                "darwin",
                "x86_64",
                "gitleaks_8.18.4_darwin_x64.tar.gz",
                "1a69e5666b13cd374889cbcb1939ed1573b63b551251283d5d2329a53cf58e2f",
                "3f83ea726b8f10c16dfa7ea08c73d1474ddbfe24db4a00e6764ec9abac05e19e",
            ),
            (
                "linux",
                "aarch64",
                "gitleaks_8.18.4_linux_arm64.tar.gz",
                "bf5f7f466ebfade1296c8bd32cf7d3f592c2aa78836aa9980ffbe2cadca7a861",
                "fc286fab02c3a0ba80670fc9f8cb1b495a2f62eb953d26113cfa3562f76b340b",
            ),
            (
                "linux",
                "x86_64",
                "gitleaks_8.18.4_linux_x64.tar.gz",
                "ba6dbb656933921c775ee5a2d1c13a91046e7952e9d919f9bac4cec61d628e7d",
                "46a05260e7cce527f132cb618de59d22262b8b5eb47f66c288447b95c7a98b7e",
            ),
        ];
        for (system, architecture, filename, archive_sha256, binary_sha256) in cases {
            let platform = platform_for(system, architecture).expect("supported platform");
            assert_eq!(platform.artifact.filename, filename);
            assert_eq!(platform.artifact.archive_sha256, archive_sha256);
            assert_eq!(platform.artifact.binary_sha256, binary_sha256);
        }
        assert!(platform_for("windows", "x86_64").is_err());
    }

    #[test]
    fn checksum_verified_download_uses_the_injectable_adapter_boundary() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let cache = fs::canonicalize(temporary.path())
            .expect("canonical tempdir")
            .join("cache");
        let binary = b"verified scanner";
        let archive = archive("gitleaks", binary);
        let platform = fixture_platform(&archive, binary);
        let downloader = FakeDownloader::new(archive);
        let runtime = LarchRuntime::new().expect("runtime");

        let installed = runtime
            .block_on(ensure_binary_for(&cache, platform, &downloader))
            .expect("install verified scanner");
        assert_eq!(fs::read(&installed).expect("read scanner"), binary);
        assert_eq!(*downloader.calls.lock().expect("download calls"), 1);

        let reused = runtime
            .block_on(ensure_binary_for(&cache, platform, &downloader))
            .expect("reuse verified scanner");
        assert_eq!(reused, installed);
        assert_eq!(*downloader.calls.lock().expect("download calls"), 1);
    }

    #[test]
    fn verified_install_rechecks_the_binary_before_returning_its_path() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let cache = fs::canonicalize(temporary.path())
            .expect("canonical tempdir")
            .join("cache");
        let binary = b"verified scanner";
        let archive = archive("gitleaks", binary);
        let platform = fixture_platform(&archive, binary);
        let downloader = FakeDownloader::new(archive);
        let runtime = LarchRuntime::new().expect("runtime");

        let installed = runtime
            .block_on(ensure_binary_with_platform(&cache, platform, &downloader))
            .expect("install verified scanner");
        assert_eq!(fs::read(&installed).expect("read scanner"), binary);
        assert!(
            is_verified_binary(&installed, platform.artifact.binary_sha256)
                .expect("verify installed scanner")
        );
    }

    #[test]
    fn scanner_execution_uses_the_typed_injectable_runner() {
        let runner = FakeRunner::default();
        let cancellation = Cancellation::new();
        let runtime = LarchRuntime::new().expect("runtime");
        let output = runtime
            .block_on(run_scanner(
                &runner,
                &cancellation,
                Path::new("/tmp"),
                &ScannerProgram::gitleaks("/tmp/gitleaks-cache/gitleaks"),
                [OsString::from("version")],
                VERSION_TIMEOUT,
            ))
            .expect("run scanner");
        assert_eq!(output.stdout(), format!("{VERSION}\n").as_bytes());
        {
            let requests = runner.requests.lock().expect("requests");
            assert_eq!(requests.len(), 1);
            assert_eq!(
                requests[0].program(),
                &ExternalProgram::Scanner(ScannerProgram::gitleaks("/tmp/gitleaks-cache/gitleaks"))
            );
            assert_eq!(requests[0].arguments(), &[OsString::from("version")]);
            assert!(requests[0].environment().is_empty());
            drop(requests);
        }
    }

    #[test]
    fn scan_modes_verify_first_and_propagate_the_scanner_exit_code() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let repository = fixture_repository(&temporary);
        let cache = fs::canonicalize(temporary.path())
            .expect("canonical tempdir")
            .join("cache");
        let binary = b"verified scanner";
        let archive = archive("gitleaks", binary);
        let platform = fixture_platform(&archive, binary);
        let downloader = FakeDownloader::new(archive);
        let runner = QueueRunner::new(vec![
            output(format!("{VERSION}\n").as_bytes(), true, 0),
            output(b"", false, 1),
        ]);
        let runtime = LarchRuntime::new().expect("runtime");

        let exit = runtime
            .block_on(run_async_with_platform(
                &arguments(GitleaksMode::History, Some("base..HEAD")),
                &repository,
                &cache,
                platform,
                &downloader,
                &runner,
            ))
            .expect("scan result");
        assert_eq!(exit, ExitCode::from(1));
        {
            let requests = runner.requests.lock().expect("requests");
            assert_eq!(requests.len(), 2);
            assert_eq!(requests[0].arguments(), &[OsString::from("version")]);
            assert_eq!(
                requests[1].arguments(),
                &[
                    OsString::from("detect"),
                    OsString::from("--source"),
                    OsString::from("."),
                    OsString::from("--config"),
                    repository.join(".gitleaks.toml").into_os_string(),
                    OsString::from("--redact"),
                    OsString::from("--no-banner"),
                    OsString::from("--log-opts"),
                    OsString::from("base..HEAD"),
                ]
            );
            drop(requests);
        }
    }

    #[test]
    fn verify_rejects_a_wrong_version_without_scanning() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let repository = fixture_repository(&temporary);
        let cache = fs::canonicalize(temporary.path())
            .expect("canonical tempdir")
            .join("cache");
        let binary = b"verified scanner";
        let archive = archive("gitleaks", binary);
        let platform = fixture_platform(&archive, binary);
        let downloader = FakeDownloader::new(archive);
        let runner = QueueRunner::new(vec![output(b"8.30.1\n", true, 0)]);
        let runtime = LarchRuntime::new().expect("runtime");

        assert!(matches!(
            runtime.block_on(run_async_with_platform(
                &arguments(GitleaksMode::Verify, None),
                &repository,
                &cache,
                platform,
                &downloader,
                &runner,
            )),
            Err(Failure::Preparation(message)) if message.contains("expected gitleaks version")
        ));
        assert_eq!(runner.requests.lock().expect("requests").len(), 1);
    }

    #[test]
    fn verify_mode_returns_after_the_verified_version_probe() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let repository = fixture_repository(&temporary);
        let cache = fs::canonicalize(temporary.path())
            .expect("canonical tempdir")
            .join("cache");
        let binary = b"verified scanner";
        let archive = archive("gitleaks", binary);
        let platform = fixture_platform(&archive, binary);
        let downloader = FakeDownloader::new(archive);
        let runner = FakeRunner::default();
        let runtime = LarchRuntime::new().expect("runtime");

        let exit = runtime
            .block_on(run_async_with_platform(
                &arguments(GitleaksMode::Verify, None),
                &repository,
                &cache,
                platform,
                &downloader,
                &runner,
            ))
            .expect("verify result");
        assert_eq!(exit, ExitCode::SUCCESS);
        assert_eq!(runner.requests.lock().expect("requests").len(), 1);
    }

    #[test]
    fn host_platform_wrapper_stops_before_scanning_when_download_is_unverified() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let repository = fixture_repository(&temporary);
        let cache = fs::canonicalize(temporary.path())
            .expect("canonical tempdir")
            .join("cache");
        let downloader = FakeDownloader::new(Vec::new());
        let runner = FakeRunner::default();
        let runtime = LarchRuntime::new().expect("runtime");

        assert!(matches!(
            runtime.block_on(run_async_with(
                &arguments(GitleaksMode::Verify, None),
                &repository,
                &cache,
                &downloader,
                &runner,
            )),
            Err(Failure::Preparation(message)) if message.contains("checksum mismatch")
        ));
        assert_eq!(*downloader.calls.lock().expect("download calls"), 1);
        assert!(runner.requests.lock().expect("requests").is_empty());
    }

    #[test]
    fn cache_file_validation_and_exit_codes_fail_closed() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let root = fs::canonicalize(temporary.path()).expect("canonical tempdir");
        let binary = root.join("gitleaks");
        let expected = sha256(b"verified scanner");
        assert!(!is_verified_binary(&binary, &expected).expect("missing scanner"));

        fs::write(&binary, b"verified scanner").expect("write scanner");
        assert!(is_verified_binary(&binary, &expected).expect("verified scanner"));
        assert!(!is_verified_binary(&binary, "wrong").expect("mismatched scanner"));
        ensure_cache_destination(&binary).expect("regular destination");

        let directory = root.join("directory");
        fs::create_dir(&directory).expect("directory destination");
        assert!(matches!(
            ensure_cache_destination(&directory),
            Err(Failure::Preparation(message)) if message.contains("not a regular file")
        ));
        assert!(matches!(
            ensure_cache_directory(Path::new("relative-cache")),
            Err(Failure::Preparation(message)) if message.contains("must be absolute")
        ));
        let no_exit_code = ProcessOutput::new(
            ProcessStatus::new(false, None),
            Vec::new(),
            Vec::new(),
            false,
            false,
        );
        assert_eq!(process_exit_code(&no_exit_code), ExitCode::from(2));
    }

    #[test]
    fn relative_cache_roots_are_resolved_before_safe_directory_checks() {
        let current = env::current_dir().expect("current directory");
        assert_eq!(
            cache_root(Some(Path::new("gitleaks-cache"))).expect("relative cache root"),
            current.join("gitleaks-cache")
        );
    }

    #[test]
    fn manual_and_ci_scans_share_the_verified_bootstrap_entrypoint() {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
        let precommit = fs::read_to_string(root.join(".pre-commit-config.yaml"))
            .expect("pre-commit configuration");
        let workflow =
            fs::read_to_string(root.join(".github/workflows/ci.yaml")).expect("CI workflow");
        assert!(precommit.contains(
            "\"$CLAUDE_PLUGIN_ROOT/scripts/larch.sh\" lint gitleaks --mode working-tree"
        ));
        assert!(
            workflow
                .contains("\"$CLAUDE_PLUGIN_ROOT/scripts/larch.sh\" lint gitleaks --mode verify")
        );
        assert!(workflow.contains(
            "\"$CLAUDE_PLUGIN_ROOT/scripts/larch.sh\" lint gitleaks --mode working-tree"
        ));
        assert!(workflow.contains(
            "\"$CLAUDE_PLUGIN_ROOT/scripts/larch.sh\" lint gitleaks --mode history --log-opts \"${BASE}..HEAD\""
        ));
        assert!(!precommit.contains("checks gitleaks"));
        assert!(!workflow.contains("python/larch/lint/gitleaks.py"));
    }

    #[cfg(unix)]
    #[test]
    fn cache_rejects_symlinked_components() {
        use std::os::unix::fs::symlink;

        let temporary = tempfile::tempdir().expect("tempdir");
        let root = fs::canonicalize(temporary.path()).expect("canonical tempdir");
        let target = root.join("target");
        fs::create_dir(&target).expect("target directory");
        let cache = root.join("cache");
        symlink(&target, &cache).expect("cache symlink");
        assert!(matches!(
            ensure_cache_directory(&cache.join("nested")),
            Err(Failure::Preparation(message)) if message.contains("not a real directory")
        ));
    }

    fn fixture_platform(archive: &[u8], binary: &[u8]) -> Platform {
        Platform {
            system: "fixture",
            architecture: "test",
            artifact: Artifact {
                filename: "fixture.tar.gz",
                archive_sha256: Box::leak(sha256(archive).into_boxed_str()),
                binary_sha256: Box::leak(sha256(binary).into_boxed_str()),
            },
        }
    }

    fn scanner_arguments_for(
        mode: GitleaksMode,
        log_opts: Option<&str>,
        repository: &Path,
    ) -> Result<Vec<String>, Failure> {
        scan_arguments_for(mode, log_opts, repository).map(|arguments| {
            arguments
                .into_iter()
                .map(|argument| argument.to_string_lossy().into_owned())
                .collect()
        })
    }

    fn archive(name: &str, contents: &[u8]) -> Vec<u8> {
        let mut bytes = Vec::new();
        {
            let encoder = flate2::write::GzEncoder::new(&mut bytes, flate2::Compression::default());
            let mut bundle = tar::Builder::new(encoder);
            let mut header = tar::Header::new_gnu();
            header.set_size(u64::try_from(contents.len()).expect("fixture length"));
            header.set_mode(0o755);
            header.set_cksum();
            bundle
                .append_data(&mut header, name, contents)
                .expect("append fixture member");
            bundle.finish().expect("finish tar fixture");
            let encoder = bundle.into_inner().expect("recover encoder");
            encoder.finish().expect("finish gzip fixture");
        }
        bytes
    }
}
