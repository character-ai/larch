//! `run-log` command boundary.

use larch_adapters::runtime::LarchRuntime;
use larch_core::{
    ObjectStore, ObjectStoreError, StorageConfigurationError, StoragePreflightError,
    ToolRepositoryStorage, format_preflight_stdout, repository_leaf_from_remote,
    resolve_run_log_storage, validate_run_log_slug,
};
use std::{
    collections::HashMap,
    env,
    ffi::OsString,
    io::Write as _,
    path::{Path, PathBuf},
    process::{Command, ExitCode, Stdio},
};

/// Run the Rust-owned `run-log validate-run-id` command.
pub fn validate_run_id(arguments: &[OsString]) -> ExitCode {
    match parse_validate_run_id(arguments) {
        ParseOutcome::Help => {
            println!("Usage: run-log validate-run-id --run-id RUN_ID");
            ExitCode::SUCCESS
        }
        ParseOutcome::Error(message) => {
            eprintln!("{message}");
            // Match Python argparse missing-required exit code.
            ExitCode::from(2)
        }
        ParseOutcome::Ok(run_id) => {
            let valid = validate_run_log_slug(&run_id);
            if writeln!(
                std::io::stdout(),
                "VALID={}",
                if valid { "true" } else { "false" }
            )
            .is_err()
            {
                return ExitCode::FAILURE;
            }
            ExitCode::SUCCESS
        }
    }
}

/// Run the Rust-owned `run-log storage-preflight` command.
#[must_use]
pub fn storage_preflight(arguments: &[OsString]) -> ExitCode {
    match parse_storage_preflight(arguments) {
        ParseOutcome::Help => {
            println!("Usage: run-log storage-preflight [--repo-root PATH]");
            ExitCode::SUCCESS
        }
        ParseOutcome::Error(message) => {
            eprintln!("{message}");
            ExitCode::from(2)
        }
        ParseOutcome::Ok(repo_root_flag) => {
            let flag = if repo_root_flag.is_empty() {
                None
            } else {
                Some(repo_root_flag.as_str())
            };
            match run_storage_preflight(flag) {
                Ok(output) => {
                    print!("{output}");
                    ExitCode::SUCCESS
                }
                Err(PreflightFailure::Configuration(error)) => {
                    eprintln!("storage preflight failed: {error}");
                    ExitCode::from(2)
                }
                Err(PreflightFailure::Provider(error)) => {
                    eprintln!("storage preflight failed: {error}");
                    ExitCode::from(1)
                }
            }
        }
    }
}

enum PreflightFailure {
    Configuration(StorageConfigurationError),
    Provider(StoragePreflightError),
}

fn run_storage_preflight(repo_root_flag: Option<&str>) -> Result<String, PreflightFailure> {
    let start = repo_root_flag
        .map_or_else(env::current_dir, |value| Ok(PathBuf::from(value)))
        .map_err(|_| {
            PreflightFailure::Configuration(StorageConfigurationError::new(
                "could not discover a Git repository root from startup CWD",
            ))
        })?;
    let repo_root = discover_repo_root(&start).ok_or_else(|| {
        PreflightFailure::Configuration(StorageConfigurationError::new(format!(
            "could not discover a Git repository root from startup CWD {}",
            start.display()
        )))
    })?;
    let origin = read_origin_url(&repo_root)?;
    let environ: HashMap<String, String> = env::vars().collect();
    let resolution = resolve_run_log_storage(&repo_root, &environ, &origin)
        .map_err(PreflightFailure::Configuration)?;
    if let Some(storage) = resolution.storage() {
        preflight_enabled_storage(storage, &environ)?;
    }
    Ok(format_preflight_stdout(&resolution))
}

fn preflight_enabled_storage(
    storage: &ToolRepositoryStorage,
    environ: &HashMap<String, String>,
) -> Result<(), PreflightFailure> {
    let prefix = format!("{}/", storage.prefix());
    let result = match storage.scheme() {
        "gs" => preflight_gcs(storage.bucket(), &prefix),
        "s3" | "r2" => preflight_aws_cli(storage, environ, &prefix),
        _ => Err(StoragePreflightError::new(format!(
            "{} prefix preflight failed for the configured larch repository namespace; verify provider credentials and prefix-scoped list access",
            storage.scheme()
        ))),
    };
    result.map_err(PreflightFailure::Provider)
}

fn preflight_gcs(bucket: &str, prefix: &str) -> Result<(), StoragePreflightError> {
    let Ok(runtime) = LarchRuntime::new() else {
        return Err(StoragePreflightError::new(
            "GCS storage preflight could not build the local checkout transport; verify Cargo is installed and the locked larch-cli release build succeeds",
        ));
    };
    runtime.block_on(async {
        let store = larch_adapters::google_storage::GoogleCloudStorage::new()
            .await
            .map_err(|error| map_object_store_error("gs", error))?;
        store
            .preflight_prefix(bucket, prefix)
            .await
            .map_err(|error| map_object_store_error("gs", error))
    })
}

fn preflight_aws_cli(
    storage: &ToolRepositoryStorage,
    environ: &HashMap<String, String>,
    prefix: &str,
) -> Result<(), StoragePreflightError> {
    let mut command = Command::new("aws");
    command.args([
        "s3api",
        "list-objects-v2",
        "--bucket",
        storage.bucket(),
        "--prefix",
        prefix,
        "--max-keys",
        "1",
        "--no-paginate",
        "--output",
        "json",
    ]);
    if storage.scheme() == "r2" {
        let endpoint = validate_r2_endpoint(environ)?;
        command.args(["--endpoint-url", &endpoint]);
    }
    command
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let output = command.output().map_err(|_| {
        StoragePreflightError::new(format!(
            "AWS CLI is required for {} storage preflight; install 'aws' and retry",
            storage.scheme().to_ascii_uppercase()
        ))
    })?;
    if output.status.success() {
        return Ok(());
    }
    if output.status.code() == Some(127) {
        return Err(StoragePreflightError::new(format!(
            "AWS CLI is required for {} storage preflight; install 'aws' and retry",
            storage.scheme().to_ascii_uppercase()
        )));
    }
    Err(StoragePreflightError::new(format!(
        "{} prefix preflight failed for the configured larch repository namespace; verify provider credentials and prefix-scoped list access",
        storage.scheme()
    )))
}

fn validate_r2_endpoint(
    environ: &HashMap<String, String>,
) -> Result<String, StoragePreflightError> {
    let account = environ
        .get(larch_core::ENV_LARCH_R2_ACCOUNT_ID)
        .map(String::as_str)
        .unwrap_or_default();
    let endpoint = environ
        .get(larch_core::ENV_LARCH_R2_ENDPOINT)
        .map(String::as_str)
        .unwrap_or_default();
    let expected_host = format!("{account}.r2.cloudflarestorage.com");
    let valid = account.len() == 32
        && account.bytes().all(|byte| byte.is_ascii_hexdigit())
        && account.bytes().all(|byte| !byte.is_ascii_uppercase())
        && endpoint.starts_with("https://")
        && {
            let rest = &endpoint["https://".len()..];
            let host = rest.trim_end_matches('/');
            host == expected_host
                && !rest.contains('?')
                && !rest.contains('#')
                && !rest.contains('@')
        };
    if valid {
        Ok(endpoint.to_owned())
    } else {
        Err(StoragePreflightError::new(
            "r2 prefix preflight failed for the configured larch repository namespace; verify provider credentials and prefix-scoped list access",
        ))
    }
}

fn map_object_store_error(scheme: &str, error: ObjectStoreError) -> StoragePreflightError {
    match error {
        ObjectStoreError::Authentication
        | ObjectStoreError::AlreadyExists
        | ObjectStoreError::NotFound
        | ObjectStoreError::LocalIo
        | ObjectStoreError::InvalidResponse
        | ObjectStoreError::Transport => StoragePreflightError::new(format!(
            "{scheme} prefix preflight failed for the configured larch repository namespace; verify provider credentials and prefix-scoped list access"
        )),
    }
}

fn discover_repo_root(start: &Path) -> Option<PathBuf> {
    let output = Command::new("git")
        .args([
            "-C",
            &start.to_string_lossy(),
            "rev-parse",
            "--show-toplevel",
        ])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let text = String::from_utf8_lossy(&output.stdout).trim().to_owned();
    if text.is_empty() {
        return None;
    }
    let path = PathBuf::from(text);
    path.canonicalize().ok().filter(|root| root.is_dir())
}

fn read_origin_url(repo_root: &Path) -> Result<String, PreflightFailure> {
    let output = Command::new("git")
        .args([
            "-C",
            &repo_root.to_string_lossy(),
            "config",
            "--local",
            "--get",
            "remote.origin.url",
        ])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .output()
        .map_err(|_| {
            PreflightFailure::Configuration(StorageConfigurationError::new(
                "could not read local remote.origin.url; configure an origin repository remote",
            ))
        })?;
    if !output.status.success() {
        return Err(PreflightFailure::Configuration(
            StorageConfigurationError::new(
                "local remote.origin.url is missing; configure an origin repository remote",
            ),
        ));
    }
    let remote = String::from_utf8_lossy(&output.stdout).trim().to_owned();
    if remote.is_empty() {
        return Err(PreflightFailure::Configuration(
            StorageConfigurationError::new(
                "local remote.origin.url is missing; configure an origin repository remote",
            ),
        ));
    }
    // Validate early so discovery failures stay configuration-class.
    let _ = repository_leaf_from_remote(&remote).map_err(PreflightFailure::Configuration)?;
    Ok(remote)
}

enum ParseOutcome {
    Help,
    Error(String),
    Ok(String),
}

fn parse_validate_run_id(arguments: &[OsString]) -> ParseOutcome {
    let mut run_id: Option<String> = None;
    let mut pending = arguments.iter();
    while let Some(raw) = pending.next() {
        let Some(flag) = raw.to_str() else {
            return ParseOutcome::Error(format!("unknown argument: {}", raw.to_string_lossy()));
        };
        if matches!(flag, "-h" | "--help") {
            return ParseOutcome::Help;
        }
        let value = if let Some(inline) = flag.strip_prefix("--run-id=") {
            inline
        } else if flag == "--run-id" {
            let Some(next) = pending.next() else {
                return ParseOutcome::Error("argument --run-id: expected one argument".to_owned());
            };
            let Some(text) = next.to_str() else {
                return ParseOutcome::Error(format!(
                    "argument --run-id: expected one argument, got {}",
                    next.to_string_lossy()
                ));
            };
            text
        } else {
            return ParseOutcome::Error(format!("unrecognized arguments: {flag}"));
        };
        if run_id.replace(value.to_owned()).is_some() {
            return ParseOutcome::Error("argument --run-id: conflicting values".to_owned());
        }
    }
    run_id.map_or_else(
        || ParseOutcome::Error("the following arguments are required: --run-id".to_owned()),
        ParseOutcome::Ok,
    )
}

fn parse_storage_preflight(arguments: &[OsString]) -> ParseOutcome {
    let mut repo_root = String::new();
    let mut pending = arguments.iter();
    while let Some(raw) = pending.next() {
        let Some(flag) = raw.to_str() else {
            return ParseOutcome::Error(format!("unknown argument: {}", raw.to_string_lossy()));
        };
        if matches!(flag, "-h" | "--help") {
            return ParseOutcome::Help;
        }
        let value = if let Some(inline) = flag.strip_prefix("--repo-root=") {
            inline
        } else if flag == "--repo-root" {
            let Some(next) = pending.next() else {
                return ParseOutcome::Error(
                    "argument --repo-root: expected one argument".to_owned(),
                );
            };
            let Some(text) = next.to_str() else {
                return ParseOutcome::Error(format!(
                    "argument --repo-root: expected one argument, got {}",
                    next.to_string_lossy()
                ));
            };
            text
        } else {
            return ParseOutcome::Error(format!("unrecognized arguments: {flag}"));
        };
        if !repo_root.is_empty() {
            return ParseOutcome::Error("argument --repo-root: conflicting values".to_owned());
        }
        value.clone_into(&mut repo_root);
    }
    ParseOutcome::Ok(repo_root)
}

#[cfg(test)]
mod tests {
    use super::{ParseOutcome, parse_storage_preflight, parse_validate_run_id};
    use std::ffi::OsString;

    fn args(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn parses_inline_and_split_run_id() {
        match parse_validate_run_id(&args(&["--run-id=-abc123"])) {
            ParseOutcome::Ok(value) => assert_eq!(value, "-abc123"),
            ParseOutcome::Help | ParseOutcome::Error(_) => panic!("expected ok"),
        }
        match parse_validate_run_id(&args(&["--run-id", "run-1"])) {
            ParseOutcome::Ok(value) => assert_eq!(value, "run-1"),
            ParseOutcome::Help | ParseOutcome::Error(_) => panic!("expected ok"),
        }
    }

    #[test]
    fn parses_optional_repo_root() {
        match parse_storage_preflight(&args(&[])) {
            ParseOutcome::Ok(value) => assert!(value.is_empty()),
            ParseOutcome::Help | ParseOutcome::Error(_) => panic!("expected ok"),
        }
        match parse_storage_preflight(&args(&["--repo-root", "/tmp/repo"])) {
            ParseOutcome::Ok(value) => assert_eq!(value, "/tmp/repo"),
            ParseOutcome::Help | ParseOutcome::Error(_) => panic!("expected ok"),
        }
    }
}
