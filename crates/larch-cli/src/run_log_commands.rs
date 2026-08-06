//! `run-log` command boundary.

use larch_adapters::git::GixRepository;
use larch_adapters::run_log_manifest::{ManifestStore, ManifestStoreError, utc_now};
use larch_adapters::runtime::LarchRuntime;
use larch_core::{
    ConfigKey, ConfigScope, ManifestUpdate, ObjectStore, ObjectStoreError, RepositoryRead,
    RunLogLayout, RunLogSlug, StorageConfigurationError, StoragePreflightError,
    ToolRepositoryStorage, format_preflight_stdout, repository_leaf_from_remote,
    resolve_run_log_storage, validate_run_log_slug,
};
use sha2::{Digest as _, Sha256};
use std::{
    collections::HashMap,
    env,
    ffi::OsString,
    fs,
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

/// Run the Rust-owned `run-log manifest` compatibility command.
#[must_use]
pub fn manifest(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_manifest(arguments) {
        Ok(parsed) => parsed,
        Err(ManifestParseError::Arguments(message)) => {
            emit_manifest_argument_error(&message);
            return manifest_failure("invalid manifest arguments");
        }
    };
    let skill = match RunLogSlug::parse(&parsed.skill) {
        Ok(skill) => skill,
        Err(_error) => {
            eprintln!("invalid skill: {}", parsed.skill);
            return manifest_failure("invalid manifest arguments");
        }
    };
    let run_id = match RunLogSlug::parse(&parsed.run_id) {
        Ok(run_id) => run_id,
        Err(_error) => {
            eprintln!("invalid run-id: {}", parsed.run_id);
            return manifest_failure("invalid manifest arguments");
        }
    };
    let log_root = match resolve_log_root(&parsed.log_root) {
        Ok(log_root) => log_root,
        Err(message) => {
            eprintln!("{message}");
            return manifest_failure("invalid manifest arguments");
        }
    };
    let updates = match parse_manifest_updates(&parsed.fields) {
        Ok(updates) => updates,
        Err(message) => return manifest_failure(&message),
    };
    let layout = RunLogLayout::new(log_root.clone(), skill, run_id);
    let path = layout.manifest_path();
    let store = match ManifestStore::open(&log_root) {
        Ok(store) => store,
        Err(ManifestStoreError::PathSafety(error))
            if matches!(
                error.kind(),
                larch_adapters::PathSafetyErrorKind::Missing
                    | larch_adapters::PathSafetyErrorKind::NotDirectory
            ) =>
        {
            return manifest_failure(&format!("manifest not found: {}", path.display()));
        }
        Err(error) => return manifest_failure(&error.to_string()),
    };
    match store.update(&layout, &updates, &utc_now()) {
        Ok(written) => {
            emit_log_envelope(Some(&written), true, false, "");
            ExitCode::SUCCESS
        }
        Err(error) => manifest_failure(&error.to_string()),
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
    let (repo_root, origin) = discover_repo_identity(&start)?;
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
    // Temporary S3/R2 transport matching Python `object_store` until a native
    // adapter clears cargo-deny duplicate review (#8076 / #8080).
    let mut command = Command::new("aws"); // lint-subprocess-via-runner: ok temporary AWS CLI S3/R2 preflight transport until native adapter
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
        && account
            .bytes()
            .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
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

fn discover_repo_identity(start: &Path) -> Result<(PathBuf, String), PreflightFailure> {
    let repository = GixRepository::discover(start).map_err(|_| {
        PreflightFailure::Configuration(StorageConfigurationError::new(format!(
            "could not discover a Git repository root from startup CWD {}",
            start.display()
        )))
    })?;
    let location = repository.location();
    let work_dir = location.work_dir.as_ref().ok_or_else(|| {
        PreflightFailure::Configuration(StorageConfigurationError::new(format!(
            "could not discover a Git repository root from startup CWD {}",
            start.display()
        )))
    })?;
    let repo_root = PathBuf::from(String::from_utf8_lossy(work_dir.as_bytes()).into_owned());
    let origin = read_origin_url(&repository)?;
    Ok((repo_root, origin))
}

fn read_origin_url(repository: &GixRepository) -> Result<String, PreflightFailure> {
    let key = ConfigKey::new("remote.origin.url").map_err(|_| {
        PreflightFailure::Configuration(StorageConfigurationError::new(
            "could not read local remote.origin.url; configure an origin repository remote",
        ))
    })?;
    let values = repository.config_values(&key).map_err(|_| {
        PreflightFailure::Configuration(StorageConfigurationError::new(
            "could not read local remote.origin.url; configure an origin repository remote",
        ))
    })?;
    let remote = values
        .iter()
        .rev()
        .find(|value| matches!(value.scope, ConfigScope::Repository | ConfigScope::Worktree))
        .or_else(|| values.last())
        .map(|value| String::from_utf8_lossy(&value.value).trim().to_owned())
        .filter(|value| !value.is_empty())
        .ok_or_else(|| {
            PreflightFailure::Configuration(StorageConfigurationError::new(
                "local remote.origin.url is missing; configure an origin repository remote",
            ))
        })?;
    let _ = repository_leaf_from_remote(&remote).map_err(PreflightFailure::Configuration)?;
    Ok(remote)
}

enum ParseOutcome {
    Help,
    Error(String),
    Ok(String),
}

struct ManifestArguments {
    log_root: String,
    skill: String,
    run_id: String,
    fields: Vec<String>,
}

enum ManifestParseError {
    Arguments(String),
}

fn parse_manifest(arguments: &[OsString]) -> Result<ManifestArguments, ManifestParseError> {
    let mut log_root = String::new();
    let mut skill: Option<String> = None;
    let mut run_id: Option<String> = None;
    let mut fields = Vec::new();
    let mut pending = arguments.iter();
    while let Some(raw) = pending.next() {
        let Some(flag) = raw.to_str() else {
            return Err(ManifestParseError::Arguments(format!(
                "unrecognized arguments: {}",
                raw.to_string_lossy()
            )));
        };
        let (name, value) = if let Some(value) = flag.strip_prefix("--log-root=") {
            ("--log-root", value)
        } else if let Some(value) = flag.strip_prefix("--skill=") {
            ("--skill", value)
        } else if let Some(value) = flag.strip_prefix("--run-id=") {
            ("--run-id", value)
        } else if let Some(value) = flag.strip_prefix("--field=") {
            ("--field", value)
        } else if matches!(flag, "--log-root" | "--skill" | "--run-id" | "--field") {
            let Some(next) = pending.next() else {
                return Err(ManifestParseError::Arguments(format!(
                    "argument {flag}: expected one argument"
                )));
            };
            let Some(value) = next.to_str() else {
                return Err(ManifestParseError::Arguments(format!(
                    "argument {flag}: expected one argument"
                )));
            };
            (flag, value)
        } else {
            return Err(ManifestParseError::Arguments(format!(
                "unrecognized arguments: {flag}"
            )));
        };
        match name {
            "--log-root" => value.clone_into(&mut log_root),
            "--skill" => skill = Some(value.to_owned()),
            "--run-id" => run_id = Some(value.to_owned()),
            "--field" => fields.push(value.to_owned()),
            _ => unreachable!("manifest parser only recognizes fixed flags"),
        }
    }
    let mut missing = Vec::new();
    if skill.is_none() {
        missing.push("--skill");
    }
    if run_id.is_none() {
        missing.push("--run-id");
    }
    if !missing.is_empty() {
        return Err(ManifestParseError::Arguments(format!(
            "the following arguments are required: {}",
            missing.join(", ")
        )));
    }
    let skill = skill.expect("required skill is checked above");
    let run_id = run_id.expect("required run id is checked above");
    Ok(ManifestArguments {
        log_root,
        skill,
        run_id,
        fields,
    })
}

fn parse_manifest_updates(fields: &[String]) -> Result<Vec<ManifestUpdate>, String> {
    fields
        .iter()
        .map(|assignment| {
            let Some((key, raw)) = assignment.split_once('=') else {
                return Err(format!("invalid field assignment: {assignment}"));
            };
            Ok((key.to_owned(), parse_manifest_scalar(raw)))
        })
        .collect()
}

fn parse_manifest_scalar(raw: &str) -> serde_json::Value {
    match raw {
        "null" => serde_json::Value::Null,
        "true" => serde_json::Value::Bool(true),
        "false" => serde_json::Value::Bool(false),
        _ if manifest_integer(raw) => raw
            .parse::<i64>()
            .map(serde_json::Value::from)
            .or_else(|_error| raw.parse::<u64>().map(serde_json::Value::from))
            .unwrap_or_else(|_error| serde_json::Value::String(raw.to_owned())),
        _ => serde_json::Value::String(raw.to_owned()),
    }
}

fn manifest_integer(value: &str) -> bool {
    let digits = value.strip_prefix('-').unwrap_or(value);
    !digits.is_empty() && digits.bytes().all(|byte| byte.is_ascii_digit())
}

fn resolve_log_root(raw: &str) -> Result<PathBuf, String> {
    let raw = if raw.is_empty() {
        env::var("LARCH_LOG_ROOT").unwrap_or_default()
    } else {
        raw.to_owned()
    };
    let temporary_root = env::var("IMPLEMENT_TMPDIR")
        .ok()
        .filter(|value| !value.is_empty())
        .map(PathBuf::from);
    if raw.is_empty() {
        return temporary_root
            .map(|root| root.join("larch-logs"))
            .ok_or_else(|| {
                "--log-root is required (or export LARCH_LOG_ROOT for test isolation)".to_owned()
            });
    }
    let path = PathBuf::from(&raw);
    if let Some(temporary_root) = temporary_root {
        if !temporary_root.is_absolute() {
            return Err("IMPLEMENT_TMPDIR must be an absolute path".to_owned());
        }
        let rebased = if path.is_absolute() {
            if path.starts_with(&temporary_root) {
                path
            } else {
                let stripped = path.strip_prefix(Path::new("/")).unwrap_or(path.as_path());
                temporary_root.join(stripped)
            }
        } else {
            temporary_root.join(path)
        };
        if !larch_adapters::path_under(&rebased, &temporary_root) {
            return Err("--log-root escapes IMPLEMENT_TMPDIR".to_owned());
        }
        return Ok(rebased);
    }
    if !path.is_absolute() {
        return Err(format!("--log-root must be an absolute path: {raw}"));
    }
    Ok(path)
}

fn emit_manifest_argument_error(message: &str) {
    eprintln!(
        "usage: cli.py run-log manifest [--log-root LOG_ROOT] --skill SKILL --run-id RUN_ID [--field FIELD]"
    );
    eprintln!("cli.py run-log manifest: error: {message}");
}

fn manifest_failure(message: &str) -> ExitCode {
    emit_log_envelope(None, false, false, message);
    ExitCode::FAILURE
}

fn emit_log_envelope(path: Option<&Path>, written: bool, unchanged: bool, error: &str) {
    let bytes = path
        .and_then(|path| fs::read(path).ok())
        .unwrap_or_default();
    let size = path
        .and_then(|path| fs::metadata(path).ok())
        .map_or(0, |metadata| metadata.len());
    let sha256 = path.map_or_else(String::new, |_| format!("{:x}", Sha256::digest(bytes)));
    println!("LOG_WRITTEN={}", if written { "true" } else { "false" });
    println!(
        "LOG_PATH={}",
        path.map_or_else(String::new, |path| path.display().to_string())
    );
    println!("BYTES={size}");
    println!("SHA256={sha256}");
    println!("COMMIT_SHA=");
    println!("UNCHANGED={}", if unchanged { "true" } else { "false" });
    if !error.is_empty() {
        println!("ERROR={error}");
    }
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
