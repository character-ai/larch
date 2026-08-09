//! Rust-owned `run-log publish` and `run-log sync` command boundaries.

use std::{
    collections::HashMap,
    ffi::OsString,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{
    google_storage::GoogleCloudStorage,
    run_lifecycle::{
        self, LifecycleHomes, PublicationResult, PublishRunRequest, RepositorySyncResult,
    },
    runtime::LarchRuntime,
};
use larch_core::{
    RunLogStorageResolution, ToolRepositoryStorage, format_preflight_stdout,
    resolve_run_log_storage,
};

use crate::{
    argparse_compat::parse,
    run_log_commands::{
        PreflightFailure, preflight_enabled_storage, resolve_repository_environment_path,
        s3_compatible_store,
    },
};

const PUBLISH_OPTIONS: &[&str] = &[
    "--repo-root",
    "--skill",
    "--run-id",
    "--staging-root",
    "--log-root",
    "--pre-scrub-violations",
];
const PUBLISH_USAGE: &str = "usage: cli.py run-log publish [-h] --repo-root REPO_ROOT --skill SKILL\n                              --run-id RUN_ID [--staging-root STAGING_ROOT]\n                              [--log-root LOG_ROOT]\n                              [--pre-scrub-violations PRE_SCRUB_VIOLATIONS]";
const PUBLISH_HELP: &str = "usage: cli.py run-log publish [-h] --repo-root REPO_ROOT --skill SKILL\n                              --run-id RUN_ID [--staging-root STAGING_ROOT]\n                              [--log-root LOG_ROOT]\n                              [--pre-scrub-violations PRE_SCRUB_VIOLATIONS]\n\noptions:\n  -h, --help            show this help message and exit\n  --repo-root REPO_ROOT\n  --skill SKILL\n  --run-id RUN_ID\n  --staging-root STAGING_ROOT\n  --log-root LOG_ROOT\n  --pre-scrub-violations PRE_SCRUB_VIOLATIONS";
const SYNC_USAGE: &str = "usage: cli.py run-log sync [-h] [--repo-root REPO_ROOT]";
const SYNC_HELP: &str = "usage: cli.py run-log sync [-h] [--repo-root REPO_ROOT]\n\noptions:\n  -h, --help            show this help message and exit\n  --repo-root REPO_ROOT";

type ResolvedRunLog = (PathBuf, RunLogStorageResolution, HashMap<String, String>);

struct PublishArguments {
    repo_root: PathBuf,
    skill: String,
    run_id: String,
    staging_root: Option<PathBuf>,
    log_root: Option<PathBuf>,
    pre_scrub_violations: u64,
}

/// Execute the Rust-owned `run-log publish` command.
#[must_use]
pub fn publish(arguments: &[OsString]) -> ExitCode {
    if has_help(arguments) {
        println!("{PUBLISH_HELP}");
        return ExitCode::SUCCESS;
    }
    let publish_arguments = match parse_publish_arguments(arguments) {
        Ok(value) => value,
        Err(code) => return code,
    };
    let (repo_root, resolution, environment) = match resolve(&publish_arguments.repo_root) {
        Ok(value) => value,
        Err((code, message)) => {
            eprintln!("publication failed: {message}");
            return ExitCode::from(code);
        }
    };
    let Some(storage) = resolution.storage() else {
        print_disabled_publish(&resolution);
        return ExitCode::SUCCESS;
    };
    if let Err(error) = preflight_enabled_storage(storage, &environment) {
        eprintln!("publication failed: {}", preflight_error(&error));
        return ExitCode::FAILURE;
    }
    let homes = match LifecycleHomes::from_environment(&environment) {
        Ok(homes) => homes,
        Err(error) => {
            eprintln!("publication failed: {error}");
            return ExitCode::FAILURE;
        }
    };
    let (staging_root, secret_scrub_violations) =
        match prepare_publish_staging(&publish_arguments, &repo_root, &environment) {
            Ok(value) => value,
            Err(error) => {
                eprintln!("publication failed: {error}");
                return ExitCode::FAILURE;
            }
        };
    publish_result(
        &PublishRunRequest {
            homes: &homes,
            storage,
            skill: &publish_arguments.skill,
            run_id: &publish_arguments.run_id,
            staging_root: staging_root.as_deref(),
        },
        &environment,
        secret_scrub_violations,
    )
}

fn parse_publish_arguments(arguments: &[OsString]) -> Result<PublishArguments, ExitCode> {
    let parsed = parse(arguments, PUBLISH_OPTIONS, 0);
    if let Some(error) = parsed.error() {
        return Err(publish_argument_failure(&error));
    }
    let missing: Vec<&str> = ["--repo-root", "--skill", "--run-id"]
        .into_iter()
        .filter(|option| parsed.value(option).is_none())
        .collect();
    if !missing.is_empty() {
        return Err(publish_argument_failure(&format!(
            "the following arguments are required: {}",
            missing.join(", ")
        )));
    }
    let Some(repo_root) = parsed.value("--repo-root") else {
        unreachable!("required publish option was checked above");
    };
    let Some(skill) = parsed.value("--skill").and_then(|value| value.to_str()) else {
        return Err(publish_argument_failure(
            "argument --skill must be valid UTF-8",
        ));
    };
    let Some(run_id) = parsed.value("--run-id").and_then(|value| value.to_str()) else {
        return Err(publish_argument_failure(
            "argument --run-id must be valid UTF-8",
        ));
    };
    let staging_root = parsed.value("--staging-root").map(PathBuf::from);
    let log_root = parsed.value("--log-root").map(PathBuf::from);
    if staging_root.is_some() && log_root.is_some() {
        return Err(publish_argument_failure(
            "--staging-root and --log-root are mutually exclusive",
        ));
    }
    let pre_scrub = parsed
        .value("--pre-scrub-violations")
        .map_or("0", |value| value.to_str().unwrap_or_default());
    if pre_scrub.is_empty() || !pre_scrub.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(publish_argument_failure(
            "--pre-scrub-violations must be a non-negative integer",
        ));
    }
    let Ok(pre_scrub_violations) = pre_scrub.parse::<u64>() else {
        return Err(publish_argument_failure(
            "--pre-scrub-violations must be a non-negative integer",
        ));
    };
    Ok(PublishArguments {
        repo_root: PathBuf::from(repo_root),
        skill: skill.to_owned(),
        run_id: run_id.to_owned(),
        staging_root,
        log_root,
        pre_scrub_violations,
    })
}

fn prepare_publish_staging(
    arguments: &PublishArguments,
    repo_root: &Path,
    environment: &HashMap<String, String>,
) -> Result<(Option<PathBuf>, u64), String> {
    let Some(log_root) = arguments.log_root.as_deref() else {
        let direct_scrub_violations = match arguments.staging_root.as_deref() {
            Some(staging_root) => run_lifecycle::scrub_run_for_publication(staging_root)
                .map(|(violations, _files)| violations)
                .map_err(|error| error.to_string())?,
            None => 0,
        };
        let secret_scrub_violations = arguments
            .pre_scrub_violations
            .checked_add(direct_scrub_violations)
            .ok_or_else(|| "secret scrub violation count overflowed".to_owned())?;
        return Ok((arguments.staging_root.clone(), secret_scrub_violations));
    };
    let prepared = run_lifecycle::prepare_run_for_publication(
        log_root,
        repo_root,
        &arguments.skill,
        &arguments.run_id,
        environment,
        arguments.pre_scrub_violations,
    )
    .map_err(|error| error.to_string())?;
    if let Some(warning) = prepared.breadcrumb_warning {
        eprintln!("WARN: larch-log commit breadcrumb publish failed: {warning}");
    }
    Ok((Some(prepared.run_dir), prepared.secret_scrub_violations))
}

fn publish_result(
    request: &PublishRunRequest<'_>,
    environment: &HashMap<String, String>,
    secret_scrub_violations: u64,
) -> ExitCode {
    publish_outcome(
        publish_with_store(request, environment),
        secret_scrub_violations,
    )
}

fn publish_outcome(
    result: Result<PublicationResult, String>,
    secret_scrub_violations: u64,
) -> ExitCode {
    match result {
        Ok(result) => {
            println!("REMOTE_KEY={}", result.remote_key);
            println!("ARCHIVE_SHA256={}", result.archive_sha256);
            println!("CACHE_DIR={}", result.cache_dir.display());
            println!("REMOTE_STATUS={}", result.remote_status.as_str());
            println!("CACHE_STATUS={}", result.cache_status.as_str());
            println!("SECRET_SCRUB_VIOLATIONS={secret_scrub_violations}");
            println!("PUBLISH_OK=true");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("publication failed: {error}");
            ExitCode::FAILURE
        }
    }
}

/// Execute the Rust-owned `run-log sync` command.
pub fn sync(arguments: &[OsString]) -> ExitCode {
    if has_help(arguments) {
        println!("{SYNC_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = parse(arguments, &["--repo-root"], 0);
    if let Some(error) = parsed.error() {
        return sync_argument_failure(&error);
    }
    let requested_root = parsed
        .value("--repo-root")
        .map_or_else(|| PathBuf::from("."), PathBuf::from);
    let (_repo_root, resolution, environment) = match resolve(&requested_root) {
        Ok(value) => value,
        Err((code, message)) => {
            eprintln!("run-log sync failed: {message}");
            return ExitCode::from(code);
        }
    };
    let Some(storage) = resolution.storage() else {
        print_disabled_sync(&resolution);
        return ExitCode::SUCCESS;
    };
    if let Err(error) = preflight_enabled_storage(storage, &environment) {
        eprintln!("run-log sync failed: {}", preflight_error(&error));
        return ExitCode::FAILURE;
    }
    let homes = match LifecycleHomes::from_environment(&environment) {
        Ok(homes) => homes,
        Err(error) => {
            eprintln!("run-log sync failed: {error}");
            return ExitCode::FAILURE;
        }
    };
    sync_outcome(sync_with_store(&homes, storage, &environment))
}

/// Synchronize once and return the unpacked corpus root.
///
/// This is the in-process form of `run-log sync` that report and analytics
/// commands need: they read the corpus themselves, so re-entering the CLI just
/// to parse `CORPUS_ROOT=` back out would add a process and a parser for no
/// gain. Disabled storage is a refusal here rather than an empty root, because
/// a reader that silently scans nothing reports a $0.00 total that looks real.
///
/// # Errors
/// Returns the refusal message for an unresolvable repository, disabled or
/// misconfigured storage, a failed preflight, or a failed synchronization.
pub fn synchronized_corpus_root(repo_root: &Path) -> Result<PathBuf, String> {
    let (_repo_root, resolution, environment) =
        resolve(repo_root).map_err(|(_code, message)| message)?;
    let Some(storage) = resolution.storage() else {
        return Err(format!(
            "run-log storage is disabled; configure [larch].storage_base_uri or set \
LARCH_STORAGE_BASE_URI ({})",
            resolution.reason().as_str()
        ));
    };
    preflight_enabled_storage(storage, &environment).map_err(|error| preflight_error(&error))?;
    let homes =
        LifecycleHomes::from_environment(&environment).map_err(|error| error.to_string())?;
    sync_with_store(&homes, storage, &environment).map(|result| result.corpus_root)
}

fn sync_outcome(result: Result<RepositorySyncResult, String>) -> ExitCode {
    match result {
        Ok(result) => {
            println!("CORPUS_ROOT={}", result.corpus_root.display());
            println!("LISTED_ARCHIVES={}", result.listed_count());
            println!("INVENTORY_SHA256={}", result.inventory_sha256);
            println!("PRESENT_RUNS={}", result.present_count());
            println!("DOWNLOADED_RUNS={}", result.downloaded_count());
            println!("REPAIRED_RUNS={}", result.repaired_count());
            println!("SYNC_OK=true");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("run-log sync failed: {error}");
            ExitCode::FAILURE
        }
    }
}

fn resolve(requested_root: &Path) -> Result<ResolvedRunLog, (u8, String)> {
    let (repo_root, origin, environment) =
        resolve_repository_environment_path(Some(requested_root))
            .map_err(|error| (2, preflight_error(&error)))?;
    let repo_root = std::fs::canonicalize(repo_root).map_err(|error| (2, error.to_string()))?;
    let resolution = resolve_run_log_storage(&repo_root, &environment, &origin)
        .map_err(|error| (2, error.to_string()))?;
    Ok((repo_root, resolution, environment))
}

fn publish_with_store(
    request: &PublishRunRequest<'_>,
    environment: &HashMap<String, String>,
) -> Result<PublicationResult, String> {
    let runtime = LarchRuntime::new().map_err(|error| error.to_string())?;
    match request.storage.scheme() {
        "gs" => runtime.block_on(async {
            let store = GoogleCloudStorage::new()
                .await
                .map_err(|_| "GCS object-store authentication failed".to_owned())?;
            run_lifecycle::publish_run(request, &store)
                .await
                .map_err(|error| error.to_string())
        }),
        "s3" | "r2" => runtime.block_on(async {
            let store = s3_compatible_store(request.storage.scheme(), environment)
                .await
                .map_err(|error| error.to_string())?;
            run_lifecycle::publish_run(request, &store)
                .await
                .map_err(|error| error.to_string())
        }),
        _ => Err("unsupported run-log object-store scheme".to_owned()),
    }
}

fn sync_with_store(
    homes: &LifecycleHomes,
    storage: &ToolRepositoryStorage,
    environment: &HashMap<String, String>,
) -> Result<RepositorySyncResult, String> {
    let runtime = LarchRuntime::new().map_err(|error| error.to_string())?;
    match storage.scheme() {
        "gs" => runtime.block_on(async {
            let store = GoogleCloudStorage::new()
                .await
                .map_err(|_| "GCS object-store authentication failed".to_owned())?;
            run_lifecycle::sync_repository_run_logs(homes, storage, &store)
                .await
                .map_err(|error| error.to_string())
        }),
        "s3" | "r2" => runtime.block_on(async {
            let store = s3_compatible_store(storage.scheme(), environment)
                .await
                .map_err(|error| error.to_string())?;
            run_lifecycle::sync_repository_run_logs(homes, storage, &store)
                .await
                .map_err(|error| error.to_string())
        }),
        _ => Err("unsupported run-log object-store scheme".to_owned()),
    }
}

fn print_disabled_publish(resolution: &RunLogStorageResolution) {
    print!("{}", format_preflight_stdout(resolution));
    println!("RUN_LOG_PUBLICATION=skipped-disabled");
    println!("SECRET_SCRUB_VIOLATIONS=0");
    println!("PUBLISH_OK=true");
}

fn print_disabled_sync(resolution: &RunLogStorageResolution) {
    print!("{}", format_preflight_stdout(resolution));
    println!("CORPUS_ROOT=");
    println!("LISTED_ARCHIVES=0");
    println!("INVENTORY_SHA256=");
    println!("PRESENT_RUNS=0");
    println!("DOWNLOADED_RUNS=0");
    println!("REPAIRED_RUNS=0");
    println!("SYNC_OK=true");
}

fn preflight_error(error: &PreflightFailure) -> String {
    match error {
        PreflightFailure::Configuration(error) => error.to_string(),
        PreflightFailure::Provider(error) => error.to_string(),
    }
}

fn has_help(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .any(|argument| matches!(argument.to_str(), Some("-h" | "--help")))
}

fn publish_argument_failure(message: &str) -> ExitCode {
    eprintln!("{PUBLISH_USAGE}");
    eprintln!("cli.py run-log publish: error: {message}");
    ExitCode::from(2)
}

fn sync_argument_failure(message: &str) -> ExitCode {
    eprintln!("{SYNC_USAGE}");
    eprintln!("cli.py run-log sync: error: {message}");
    ExitCode::from(2)
}

#[cfg(test)]
#[path = "../tests/support/run_log_publication_commands_unit.rs"]
mod tests;
