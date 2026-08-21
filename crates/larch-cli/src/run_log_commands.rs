//! `run-log` command boundary.

use crate::argparse_compat::{ParsedCommandLine, parse, parse_with_flags};
use crate::python_verb::plugin_root_directory;
use larch_adapters::git::GixRepository;
use larch_adapters::run_lifecycle;
use larch_adapters::run_log_manifest::{ManifestStore, ManifestStoreError, utc_now};
use larch_adapters::runtime::LarchRuntime;
use larch_adapters::s3_storage::{R2Endpoint, S3Storage};
use larch_core::{
    ConfigKey, ConfigScope, KvDocument, MalformedLinePolicy, ManifestUpdate, ObjectStore,
    ObjectStoreError, ParseOptions, RepositoryRead, RunLogLayout, RunLogSlug, RunLogStorageMode,
    StorageConfigurationError, StoragePreflightError, ToolRepositoryStorage, TranscriptError,
    format_preflight_stdout, render_session_transcript as render_transcript,
    repository_leaf_from_remote, require_enabled_storage, resolve_run_log_storage,
    validate_run_log_slug,
};
use sha2::{Digest as _, Sha256};
use std::{
    collections::HashMap,
    env,
    ffi::OsString,
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
};

const ARCHIVE_OPTIONS: &[&str] = &["--staging-root", "--output-dir", "--skill", "--run-id"];
const MATERIALIZE_OPTIONS: &[&str] = &[
    "--archive-path",
    "--expected-manifest-sha256",
    "--run-dir",
    "--skill",
    "--run-id",
    "--staging-root",
];
const MATERIALIZE_PUBLIC_OPTIONS: &[&str] = &["--archive-path", "--run-dir", "--skill", "--run-id"];

/// Run the Rust-owned `run-log archive` command.
#[must_use]
pub fn archive(arguments: &[OsString]) -> ExitCode {
    if has_help(arguments) {
        archive_help();
        return ExitCode::SUCCESS;
    }
    let parsed = parse(arguments, ARCHIVE_OPTIONS, 0);
    if let Some(error) = parsed.error() {
        return archive_argument_failure("archive", &error);
    }
    if let Some(missing) = missing_options(
        &parsed,
        &["--staging-root", "--output-dir", "--skill", "--run-id"],
    ) {
        return archive_argument_failure("archive", &missing);
    }
    let Some(staging_root) = parsed.value("--staging-root") else {
        unreachable!("required archive option was checked above");
    };
    let Some(output_dir) = parsed.value("--output-dir") else {
        unreachable!("required archive option was checked above");
    };
    let Some(skill) = parsed.value("--skill").and_then(|value| value.to_str()) else {
        return archive_argument_failure("archive", "argument --skill must be valid UTF-8");
    };
    let Some(run_id) = parsed.value("--run-id").and_then(|value| value.to_str()) else {
        return archive_argument_failure("archive", "argument --run-id must be valid UTF-8");
    };
    match run_lifecycle::archive_run_directory(
        Path::new(staging_root),
        Path::new(output_dir),
        skill,
        run_id,
    ) {
        Ok(result) => {
            println!("ARCHIVE_PATH={}", result.archive_path.display());
            println!("ARCHIVE_SHA256={}", result.archive_sha256);
            println!("MANIFEST_SHA256={}", result.manifest_sha256);
            println!("MEMBER_COUNT={}", result.member_count);
            ExitCode::SUCCESS
        }
        Err(error) => archive_failure(&error.to_string()),
    }
}

/// Run the Rust-owned `run-log materialize` command.
///
/// The two hidden modes are typed internal consumer routes for verifying an
/// existing cache and promoting a staging tree pinned by an archive manifest.
#[must_use]
pub fn materialize(arguments: &[OsString]) -> ExitCode {
    if has_help(arguments) {
        materialize_help();
        return ExitCode::SUCCESS;
    }
    let parsed = match parse_materialize_arguments(arguments) {
        Ok(parsed) => parsed,
        Err(exit_code) => return exit_code,
    };
    let Some(run_dir) = parsed.value("--run-dir") else {
        unreachable!("required materialize option was checked above");
    };
    let Some(skill) = parsed.value("--skill").and_then(|value| value.to_str()) else {
        return archive_argument_failure("materialize", "argument --skill must be valid UTF-8");
    };
    let Some(run_id) = parsed.value("--run-id").and_then(|value| value.to_str()) else {
        return archive_argument_failure("materialize", "argument --run-id must be valid UTF-8");
    };
    let archive_path = parsed.value("--archive-path");
    let staging_root = parsed.value("--staging-root");
    let expected_manifest_sha256 = parsed
        .value("--expected-manifest-sha256")
        .and_then(|value| value.to_str());
    let result = if parsed.flag("--verify-existing") {
        if archive_path.is_some() || staging_root.is_some() || expected_manifest_sha256.is_some() {
            return archive_argument_failure(
                "materialize",
                "--verify-existing cannot be combined with archive or staging inputs",
            );
        }
        run_lifecycle::verify_materialized_run_directory(Path::new(run_dir), skill, run_id)
    } else if let Some(staging_root) = staging_root {
        if archive_path.is_some() {
            return archive_argument_failure(
                "materialize",
                "--archive-path and --staging-root are mutually exclusive",
            );
        }
        let Some(expected_manifest_sha256) = expected_manifest_sha256 else {
            return archive_argument_failure(
                "materialize",
                "the following arguments are required: --expected-manifest-sha256",
            );
        };
        run_lifecycle::promote_staging_run_directory(
            Path::new(staging_root),
            Path::new(run_dir),
            skill,
            run_id,
            expected_manifest_sha256,
        )
    } else {
        if expected_manifest_sha256.is_some() {
            return archive_argument_failure(
                "materialize",
                "--expected-manifest-sha256 requires --staging-root",
            );
        }
        let Some(archive_path) = archive_path else {
            return archive_argument_failure(
                "materialize",
                "the following arguments are required: --archive-path",
            );
        };
        run_lifecycle::materialize_run_archive(
            Path::new(archive_path),
            Path::new(run_dir),
            skill,
            run_id,
        )
    };
    match result {
        Ok(result) => {
            println!("RUN_DIR={}", result.run_dir.display());
            println!("MANIFEST_SHA256={}", result.manifest_sha256);
            println!("MEMBER_COUNT={}", result.member_count);
            println!("EXPANDED_SIZE={}", result.expanded_size);
            ExitCode::SUCCESS
        }
        Err(error) => archive_failure(&error.to_string()),
    }
}

fn parse_materialize_arguments(arguments: &[OsString]) -> Result<ParsedCommandLine, ExitCode> {
    let internal_mode = arguments.iter().any(|argument| {
        matches!(
            argument.to_str(),
            Some("--verify-existing" | "--staging-root" | "--expected-manifest-sha256")
        ) || argument.to_str().is_some_and(|value| {
            value.starts_with("--verify-existing=")
                || value.starts_with("--staging-root=")
                || value.starts_with("--expected-manifest-sha256=")
        })
    });
    let parsed = if internal_mode {
        parse_with_flags(arguments, MATERIALIZE_OPTIONS, &["--verify-existing"], 0)
    } else {
        parse(arguments, MATERIALIZE_PUBLIC_OPTIONS, 0)
    };
    if let Some(error) = parsed.error() {
        return Err(archive_argument_failure("materialize", &error));
    }
    let required = if internal_mode {
        &["--run-dir", "--skill", "--run-id"][..]
    } else {
        MATERIALIZE_PUBLIC_OPTIONS
    };
    if let Some(missing) = missing_options(&parsed, required) {
        return Err(archive_argument_failure("materialize", &missing));
    }
    Ok(parsed)
}

fn has_help(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .any(|argument| matches!(argument.to_str(), Some("-h" | "--help")))
}

fn missing_options(parsed: &ParsedCommandLine, options: &[&str]) -> Option<String> {
    let missing: Vec<&str> = options
        .iter()
        .copied()
        .filter(|option| parsed.value(option).is_none())
        .collect();
    (!missing.is_empty()).then(|| {
        format!(
            "the following arguments are required: {}",
            missing.join(", ")
        )
    })
}

fn archive_help() {
    println!(
        "usage: cli.py run-log archive [-h] --staging-root STAGING_ROOT --output-dir\n                              OUTPUT_DIR --skill SKILL --run-id RUN_ID\n\noptions:\n  -h, --help            show this help message and exit\n  --staging-root STAGING_ROOT\n  --output-dir OUTPUT_DIR\n  --skill SKILL\n  --run-id RUN_ID"
    );
}

fn materialize_help() {
    println!(
        "usage: cli.py run-log materialize [-h] --archive-path ARCHIVE_PATH --run-dir\n                                  RUN_DIR --skill SKILL --run-id RUN_ID\n\noptions:\n  -h, --help            show this help message and exit\n  --archive-path ARCHIVE_PATH\n  --run-dir RUN_DIR\n  --skill SKILL\n  --run-id RUN_ID"
    );
}

fn archive_argument_failure(command: &str, message: &str) -> ExitCode {
    let usage = match command {
        "archive" => {
            "usage: cli.py run-log archive [-h] --staging-root STAGING_ROOT --output-dir\n                              OUTPUT_DIR --skill SKILL --run-id RUN_ID"
        }
        "materialize" => {
            "usage: cli.py run-log materialize [-h] --archive-path ARCHIVE_PATH --run-dir\n                                  RUN_DIR --skill SKILL --run-id RUN_ID"
        }
        _ => unreachable!("only the archive commands use this parser"),
    };
    eprintln!("{usage}");
    eprintln!("cli.py run-log {command}: error: {message}");
    ExitCode::from(2)
}

fn archive_failure(error: &str) -> ExitCode {
    let one_line = error.replace(['\n', '\r'], " ");
    println!("ERROR={one_line}");
    ExitCode::FAILURE
}

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

/// Run the Rust-owned `run-log publish-breadcrumbs` command.
///
/// `--source-dir` names the session's `breadcrumbs/` publication hint, so the
/// session root that actually holds the quiet logs is its parent. `--dest-dir`
/// is the published `breadcrumbs/` directory, replaced atomically.
#[must_use]
pub fn publish_breadcrumbs(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &["--source-dir", "--dest-dir"], 0);
    // `argparse` reported a mid-parse error before the required-option check,
    // and exited 2 for either; the Python caller returned that code unchanged.
    if let Some(error) = parsed.error() {
        eprintln!("publish-breadcrumbs: {error}");
        return ExitCode::from(2);
    }
    let (Some(source_dir), Some(dest_dir)) =
        (parsed.value("--source-dir"), parsed.value("--dest-dir"))
    else {
        eprintln!("publish-breadcrumbs: --source-dir and --dest-dir are required");
        return ExitCode::from(2);
    };
    let source_dir = Path::new(source_dir);
    // `Path::parent` yields an empty path for a single-component argument,
    // where Python's `Path.parent` yielded `.`. Live callers always pass an
    // absolute hint; a relative one is refused by the confinement check
    // whenever a session tmpdir is set.
    let source_root = source_dir
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    let environment: HashMap<String, String> = env::vars().collect();
    match run_lifecycle::publish_breadcrumbs(source_root, Path::new(dest_dir), &environment) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("publish-breadcrumbs: {error}");
            ExitCode::from(1)
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

pub enum PreflightFailure {
    Configuration(StorageConfigurationError),
    Provider(StoragePreflightError),
}

fn run_storage_preflight(repo_root_flag: Option<&str>) -> Result<String, PreflightFailure> {
    let (_, resolution, environ) = resolve_storage(repo_root_flag)?;
    if let Some(storage) = resolution.storage() {
        preflight_enabled_storage(storage, &environ)?;
    }
    Ok(format_preflight_stdout(&resolution))
}

pub fn resolve_storage(
    repo_root_flag: Option<&str>,
) -> Result<
    (
        PathBuf,
        larch_core::RunLogStorageResolution,
        HashMap<String, String>,
    ),
    PreflightFailure,
> {
    resolve_storage_from_environment(resolve_repository_environment(repo_root_flag)?)
}

/// Resolve the current repository's configured storage from a path anchor.
pub fn resolve_storage_path(
    repo_root_flag: Option<&Path>,
) -> Result<
    (
        PathBuf,
        larch_core::RunLogStorageResolution,
        HashMap<String, String>,
    ),
    PreflightFailure,
> {
    resolve_storage_from_environment(resolve_repository_environment_path(repo_root_flag)?)
}

/// Resolve configured storage from an already-discovered repository environment.
pub fn resolve_storage_from_environment(
    (repo_root, origin, environ): (PathBuf, String, HashMap<String, String>),
) -> Result<
    (
        PathBuf,
        larch_core::RunLogStorageResolution,
        HashMap<String, String>,
    ),
    PreflightFailure,
> {
    let resolution = resolve_run_log_storage(&repo_root, &environ, &origin)
        .map_err(PreflightFailure::Configuration)?;
    Ok((repo_root, resolution, environ))
}

/// Resolve enabled storage, retaining the typed preflight failure boundary.
pub fn resolve_enabled_storage_path(
    repo_root_flag: Option<&Path>,
) -> Result<ToolRepositoryStorage, PreflightFailure> {
    let (_, resolution, _) = resolve_storage_path(repo_root_flag)?;
    require_enabled_storage(&resolution).map_err(PreflightFailure::Configuration)
}

pub fn resolve_repository_environment(
    repo_root_flag: Option<&str>,
) -> Result<(PathBuf, String, HashMap<String, String>), PreflightFailure> {
    resolve_repository_environment_path(repo_root_flag.map(Path::new))
}

pub fn resolve_repository_environment_path(
    repo_root_flag: Option<&Path>,
) -> Result<(PathBuf, String, HashMap<String, String>), PreflightFailure> {
    let start = repo_root_flag
        .map_or_else(env::current_dir, |value| Ok(value.to_path_buf()))
        .map_err(|_| {
            PreflightFailure::Configuration(StorageConfigurationError::new(
                "could not discover a Git repository root from startup CWD",
            ))
        })?;
    let (repo_root, origin) = discover_repo_identity(&start)?;
    let environ: HashMap<String, String> = env::vars().collect();
    Ok((repo_root, origin, environ))
}

/// Storage-resolution reasons a disabled-publication manifest may carry.
pub const DISABLED_STORAGE_REASONS: [&str; 3] = [
    "config-file-missing",
    "larch-table-missing",
    "storage-base-uri-omitted",
];

/// Render the provider-neutral run identity a public summary carries for
/// `skill` (`"implement"` or `"design"`).
///
/// A lifecycle manifest that pins this run to disabled storage answers first,
/// because a run whose archive was never published must say so even when the
/// clone's configuration has since changed. Otherwise the clone's own storage
/// resolution names the provider, and any resolution failure reads as
/// `unknown` rather than blocking the refresh.
pub fn run_log_reference(
    skill: &str,
    repo_root: Option<&Path>,
    run_id: &str,
    manifest: &Path,
) -> String {
    let disabled = format!(
        "no archive published because run-log storage was disabled, skill `{skill}`, run ID `{run_id}`"
    );
    if pins_disabled_publication(skill, manifest, run_id) {
        return disabled;
    }
    let mut provider = "unknown".to_owned();
    if let Some(repo_root) = repo_root
        && let Ok((repo_root, origin, environ)) =
            resolve_repository_environment_path(Some(repo_root))
        && let Ok(resolution) = resolve_run_log_storage(&repo_root, &environ, &origin)
    {
        if resolution.mode() == RunLogStorageMode::Disabled {
            return disabled;
        }
        if let Ok(storage) = require_enabled_storage(&resolution) {
            storage.scheme().clone_into(&mut provider);
        }
    }
    format!("provider `{provider}`, skill `{skill}`, run ID `{run_id}`")
}

/// Whether one lifecycle manifest pins this `skill` run to disabled publication.
pub fn pins_disabled_publication(skill: &str, manifest: &Path, run_id: &str) -> bool {
    if manifest.is_symlink() || !manifest.is_file() {
        return false;
    }
    let Ok(serde_json::Value::Object(document)) = serde_json::from_str::<serde_json::Value>(
        &crate::execution_issue_commands::read_lossy(manifest),
    ) else {
        return false;
    };
    let string = |key: &str| document.get(key).and_then(serde_json::Value::as_str);
    if document
        .get("lifecycle_schema_version")
        .and_then(serde_json::Value::as_u64)
        != Some(larch_core::LIFECYCLE_SCHEMA_VERSION)
        || string("publication_mode") != Some("disabled")
        || !string("storage_resolution_reason")
            .is_some_and(|reason| DISABLED_STORAGE_REASONS.contains(&reason))
        || string("skill") != Some(skill)
        || string("run_id") != Some(run_id)
    {
        return false;
    }
    if !string("local_namespace_id").is_some_and(|value| {
        value.len() == 64
            && value
                .chars()
                .all(|character| character.is_ascii_hexdigit() && !character.is_ascii_uppercase())
    }) {
        return false;
    }
    ["storage_base_uri", "tool_repo_uri", "storage_origin_id"]
        .iter()
        .all(|field| document.get(*field).is_none_or(serde_json::Value::is_null))
}

pub fn preflight_enabled_storage(
    storage: &ToolRepositoryStorage,
    environ: &HashMap<String, String>,
) -> Result<(), PreflightFailure> {
    let prefix = format!("{}/", storage.prefix());
    let result = match storage.scheme() {
        "gs" => preflight_gcs(storage.bucket(), &prefix),
        "s3" | "r2" => preflight_s3_compatible(storage, environ, &prefix),
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

fn preflight_s3_compatible(
    storage: &ToolRepositoryStorage,
    environ: &HashMap<String, String>,
    prefix: &str,
) -> Result<(), StoragePreflightError> {
    let runtime = LarchRuntime::new().map_err(|_| storage_preflight_error(storage.scheme()))?;
    runtime.block_on(async {
        let store = s3_compatible_store(storage.scheme(), environ).await?;
        store
            .preflight_prefix(storage.bucket(), prefix)
            .await
            .map_err(|error| map_object_store_error(storage.scheme(), error))
    })
}

pub async fn s3_compatible_store(
    scheme: &str,
    environ: &HashMap<String, String>,
) -> Result<S3Storage, StoragePreflightError> {
    if scheme == "s3" {
        return S3Storage::s3(environ)
            .await
            .map_err(|error| map_object_store_error("s3", error));
    }
    if scheme != "r2" {
        return Err(storage_preflight_error(scheme));
    }
    let account = environ
        .get(larch_core::ENV_LARCH_R2_ACCOUNT_ID)
        .map(String::as_str)
        .unwrap_or_default();
    let endpoint = environ
        .get(larch_core::ENV_LARCH_R2_ENDPOINT)
        .map(String::as_str)
        .unwrap_or_default();
    let endpoint =
        R2Endpoint::parse(account, endpoint).map_err(|_| storage_preflight_error("r2"))?;
    S3Storage::r2(endpoint, environ)
        .await
        .map_err(|error| map_object_store_error("r2", error))
}

fn map_object_store_error(scheme: &str, error: ObjectStoreError) -> StoragePreflightError {
    match error {
        ObjectStoreError::Authentication
        | ObjectStoreError::AlreadyExists
        | ObjectStoreError::NotFound
        | ObjectStoreError::LocalIo
        | ObjectStoreError::InvalidResponse
        | ObjectStoreError::Transport => storage_preflight_error(scheme),
    }
}

fn storage_preflight_error(scheme: &str) -> StoragePreflightError {
    StoragePreflightError::new(format!(
        "{scheme} prefix preflight failed for the configured larch repository namespace; verify provider credentials and prefix-scoped list access"
    ))
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
    let options = ParseOptions {
        malformed_lines: MalformedLinePolicy::Reject,
        ..ParseOptions::legacy()
    };
    fields
        .iter()
        .map(|assignment| {
            let document = KvDocument::parse(assignment, options)
                .map_err(|_error| format!("invalid field assignment: {assignment}"))?;
            let [row] = document.rows() else {
                return Err(format!("invalid field assignment: {assignment}"));
            };
            Ok((row.key().to_owned(), parse_manifest_scalar(row.value())))
        })
        .collect()
}

fn parse_manifest_scalar(raw: &str) -> serde_json::Value {
    match raw {
        "null" => serde_json::Value::Null,
        "true" => serde_json::Value::Bool(true),
        "false" => serde_json::Value::Bool(false),
        _ if manifest_integer(raw) => {
            let negative = raw.starts_with('-');
            let digits = raw.strip_prefix('-').unwrap_or(raw).trim_start_matches('0');
            let normalized = if digits.is_empty() {
                "0".to_owned()
            } else if negative {
                format!("-{digits}")
            } else {
                digits.to_owned()
            };
            serde_json::from_str(&normalized)
                .unwrap_or_else(|_error| serde_json::Value::String(raw.to_owned()))
        }
        _ => serde_json::Value::String(raw.to_owned()),
    }
}

fn manifest_integer(value: &str) -> bool {
    let digits = value.strip_prefix('-').unwrap_or(value);
    !digits.is_empty() && digits.bytes().all(|byte| byte.is_ascii_digit())
}

/// Resolve `--log-root` against `LARCH_LOG_ROOT` and `IMPLEMENT_TMPDIR`.
///
/// Shared with the entry-write commands so one owner decides where a run-log
/// tree lives.
///
/// # Errors
///
/// Returns the operator-facing message when no root can be resolved, when the
/// temporary root is relative, or when the requested root escapes it.
pub fn resolve_log_root(raw: &str) -> Result<PathBuf, String> {
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

/// Emit the shared `run-log` stdout envelope.
///
/// `BYTES` and `SHA256` describe `path` only when it names a regular file, so a
/// missing path or a directory (the `write-round` destination) reports `0` and
/// an empty digest exactly as the Python owner did.
pub fn emit_log_envelope(path: Option<&Path>, written: bool, unchanged: bool, error: &str) {
    let regular_file = path.filter(|path| path.is_file());
    let size = regular_file
        .and_then(|path| fs::metadata(path).ok())
        .map_or(0, |metadata| metadata.len());
    let sha256 = regular_file
        .and_then(|path| fs::read(path).ok())
        .map_or_else(String::new, |bytes| format!("{:x}", Sha256::digest(bytes)));
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

const RENDER_TRANSCRIPT_OPTIONS: &[&str] = &["--input", "--output"];
const RENDER_TRANSCRIPT_USAGE: &str = "usage: cli.py [-h] --input INPUT [--output OUTPUT]";
const RENDER_TRANSCRIPT_HELP: &str = "usage: cli.py [-h] --input INPUT [--output OUTPUT]\n\nrender-session-transcript.py \u{2014} render a Claude Code session JSONL as a\nfiltered chat-view JSONL.\n\noptions:\n  -h, --help       show this help message and exit\n  --input INPUT    Path to raw Claude Code session JSONL\n  --output OUTPUT  Path to write filtered JSONL (default: stdout)";

/// Run the Rust-owned `run-log render-session-transcript` command.
///
/// Exit codes carry the contract its callers branch on: `2` for a missing or
/// unreadable input, `3` for an input that held no record, `4` for an input past
/// the renderer's size bound, and `1` for a failed write.
#[must_use]
pub fn render_session_transcript(arguments: &[OsString]) -> ExitCode {
    if has_help(arguments) {
        println!("{RENDER_TRANSCRIPT_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = parse(arguments, RENDER_TRANSCRIPT_OPTIONS, 0);
    if let Some(error) = parsed.error() {
        return render_transcript_argument_failure(&error);
    }
    let Some(input) = parsed.value("--input") else {
        return render_transcript_argument_failure("the following arguments are required: --input");
    };
    let rendered = match render_transcript(Path::new(input), plugin_root_directory().as_deref()) {
        Ok(rendered) => rendered,
        Err(error) => {
            eprintln!("render-session-transcript: {error}");
            return ExitCode::from(transcript_exit_code(&error));
        }
    };
    for line in rendered.warnings.lines() {
        eprintln!("render-session-transcript: {line}");
    }
    // An empty `--output` was falsy to the Python owner, which streamed instead.
    match parsed.value("--output").filter(|output| !output.is_empty()) {
        Some(output) => {
            if let Err(error) = fs::write(Path::new(output), rendered.text.as_bytes()) {
                eprintln!(
                    "render-session-transcript: could not write {}: {}",
                    Path::new(output).display(),
                    error.to_string().replace(['\n', '\r'], " ")
                );
                return ExitCode::FAILURE;
            }
        }
        None => {
            if std::io::stdout()
                .write_all(rendered.text.as_bytes())
                .is_err()
            {
                return ExitCode::FAILURE;
            }
        }
    }
    ExitCode::SUCCESS
}

/// Map one rendering refusal to the exit code its callers branch on.
const fn transcript_exit_code(error: &TranscriptError) -> u8 {
    match error {
        TranscriptError::Missing(_) | TranscriptError::Unreadable { .. } => 2,
        TranscriptError::NoRecords(_) => 3,
        TranscriptError::Oversized { .. } => 4,
    }
}

fn render_transcript_argument_failure(message: &str) -> ExitCode {
    eprintln!("{RENDER_TRANSCRIPT_USAGE}");
    eprintln!("cli.py: error: {message}");
    ExitCode::from(2)
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

#[cfg(test)]
mod reference_tests {
    use super::{pins_disabled_publication, run_log_reference};
    use std::fs;
    use std::path::Path;

    fn disabled_manifest_json(skill: &str, run_id: &str) -> String {
        let namespace = "a".repeat(64);
        format!(
            r#"{{
                "lifecycle_schema_version": 3,
                "publication_mode": "disabled",
                "storage_resolution_reason": "config-file-missing",
                "skill": "{skill}",
                "run_id": "{run_id}",
                "local_namespace_id": "{namespace}",
                "storage_base_uri": null,
                "tool_repo_uri": null,
                "storage_origin_id": null
            }}"#
        )
    }

    #[test]
    fn pins_disabled_publication_accepts_a_well_formed_disabled_manifest() {
        let dir = tempfile::tempdir().expect("tmp");
        let manifest = dir.path().join("manifest.json");
        fs::write(&manifest, disabled_manifest_json("design", "run-1")).expect("write");
        assert!(pins_disabled_publication("design", &manifest, "run-1"));
    }

    #[test]
    fn pins_disabled_publication_rejects_mismatches_and_missing_files() {
        let dir = tempfile::tempdir().expect("tmp");
        let manifest = dir.path().join("manifest.json");
        // Missing file.
        assert!(!pins_disabled_publication("design", &manifest, "run-1"));
        // Wrong run id.
        fs::write(&manifest, disabled_manifest_json("design", "other")).expect("write");
        assert!(!pins_disabled_publication("design", &manifest, "run-1"));
        // Wrong skill.
        assert!(!pins_disabled_publication("implement", &manifest, "other"));
        // Bad schema version.
        fs::write(
            &manifest,
            disabled_manifest_json("design", "run-1").replace(
                "\"lifecycle_schema_version\": 3",
                "\"lifecycle_schema_version\": 1",
            ),
        )
        .expect("write");
        assert!(!pins_disabled_publication("design", &manifest, "run-1"));
        // Non-null storage field.
        fs::write(
            &manifest,
            disabled_manifest_json("design", "run-1").replace(
                "\"storage_base_uri\": null",
                "\"storage_base_uri\": \"gs://x\"",
            ),
        )
        .expect("write");
        assert!(!pins_disabled_publication("design", &manifest, "run-1"));
        // Bad namespace id (not 64 hex chars).
        fs::write(
            &manifest,
            disabled_manifest_json("design", "run-1").replace(&"a".repeat(64), "deadbeef"),
        )
        .expect("write");
        assert!(!pins_disabled_publication("design", &manifest, "run-1"));
        // Not JSON at all.
        fs::write(&manifest, "not json").expect("write");
        assert!(!pins_disabled_publication("design", &manifest, "run-1"));
    }

    #[test]
    fn run_log_reference_reports_disabled_and_unknown_providers() {
        let dir = tempfile::tempdir().expect("tmp");
        let manifest = dir.path().join("manifest.json");
        // No manifest and no repo root: provider resolves to unknown.
        let unknown = run_log_reference("design", None, "run-1", &manifest);
        assert_eq!(
            unknown,
            "provider `unknown`, skill `design`, run ID `run-1`"
        );
        // A manifest pinning disabled publication answers first.
        fs::write(&manifest, disabled_manifest_json("design", "run-1")).expect("write");
        let disabled = run_log_reference("design", None, "run-1", &manifest);
        assert_eq!(
            disabled,
            "no archive published because run-log storage was disabled, skill `design`, run ID `run-1`"
        );
        // Repo root that is not a resolvable larch repository stays unknown.
        let stray: &Path = dir.path();
        let missing = dir.path().join("absent.json");
        let still_unknown = run_log_reference("implement", Some(stray), "run-9", &missing);
        assert_eq!(
            still_unknown,
            "provider `unknown`, skill `implement`, run ID `run-9`"
        );
    }
}
