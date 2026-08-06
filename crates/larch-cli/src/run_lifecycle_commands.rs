//! CLI composition for the five shared run-lifecycle commands.

use std::{collections::HashMap, fmt::Write as _, path::PathBuf, process::ExitCode};

use clap::Args;
use larch_adapters::{
    google_storage::GoogleCloudStorage,
    run_lifecycle::{
        self, FinishRequest, LifecycleHomes, StartRequest, StartedRun, TerminalResult,
    },
    runtime::LarchRuntime,
};
use larch_core::{
    LifecycleOutcome, RunLogStorageMode, RunLogStorageReason, RunLogStorageResolution,
    format_preflight_stdout, local_namespace_id, repository_leaf_from_remote,
    resolve_run_log_storage,
};

use crate::run_log_commands::{
    PreflightFailure, preflight_enabled_storage, resolve_repository_environment_path,
    s3_compatible_store,
};

/// Arguments for lifecycle admission.
#[derive(Args)]
pub struct LifecycleStartArguments {
    #[arg(long)]
    repo_root: PathBuf,
    #[arg(long)]
    skill: String,
    #[arg(long)]
    run_id: Option<String>,
    #[arg(long)]
    log_root: Option<PathBuf>,
    #[arg(long, default_value_t = String::new())]
    parent_skill: String,
    #[arg(long, default_value_t = String::new())]
    parent_run_id: String,
    #[arg(long, default_value_t = String::new())]
    issue: String,
    #[arg(long)]
    lifecycle_parent_context: Option<PathBuf>,
    #[arg(long)]
    adopt_existing: bool,
    #[arg(long, hide = true)]
    rehydrate: bool,
}

/// Arguments shared by all terminal lifecycle commands.
#[derive(Args)]
pub struct LifecycleTerminalArguments {
    #[arg(long)]
    repo_root: PathBuf,
    #[arg(long)]
    skill: String,
    #[arg(long)]
    run_id: String,
    #[arg(long, default_value_t = 0, hide = true)]
    pre_scrub_violations: u64,
}

/// Execute `run-log lifecycle-start`.
#[must_use]
pub fn start(arguments: &LifecycleStartArguments) -> ExitCode {
    let adopt_existing = arguments.adopt_existing || arguments.rehydrate;
    if arguments.rehydrate
        && (arguments.run_id.is_none()
            || arguments.log_root.is_some()
            || !arguments.parent_skill.is_empty()
            || !arguments.parent_run_id.is_empty()
            || arguments.lifecycle_parent_context.is_some()
            || !arguments.issue.is_empty())
    {
        eprintln!(
            "run lifecycle start failed: --rehydrate requires only --repo-root, --skill, and --run-id"
        );
        return ExitCode::FAILURE;
    }
    let persisted = if adopt_existing {
        arguments
            .run_id
            .as_deref()
            .map(|run_id| (arguments.skill.as_str(), run_id))
    } else {
        None
    };
    let (repo_root, resolution, local, environment, homes) =
        match resolve(&arguments.repo_root, persisted) {
            Ok(value) => value,
            Err((code, error)) => {
                eprintln!("run lifecycle start failed: {error}");
                return ExitCode::from(code);
            }
        };
    if arguments.rehydrate {
        return match run_lifecycle::load(
            &repo_root,
            &arguments.skill,
            arguments
                .run_id
                .as_deref()
                .expect("rehydration validated a run ID"),
            &resolution,
            &local,
            &homes,
        ) {
            Ok(started) => {
                print_start(&started, false);
                ExitCode::SUCCESS
            }
            Err(error) => {
                eprintln!("run lifecycle start failed: {error}");
                ExitCode::FAILURE
            }
        };
    }
    if let Some(storage) = resolution.storage()
        && let Err(error) = preflight_enabled_storage(storage, &environment)
    {
        eprintln!("run lifecycle start failed: {}", preflight_message(error));
        return ExitCode::FAILURE;
    }
    match run_lifecycle::start(&StartRequest {
        repo_root: &repo_root,
        resolution: &resolution,
        local_resolution: &local,
        homes: &homes,
        environment: &environment,
        skill: &arguments.skill,
        run_id: arguments.run_id.as_deref(),
        log_root: arguments.log_root.as_deref(),
        parent_skill: &arguments.parent_skill,
        parent_run_id: &arguments.parent_run_id,
        parent_context: arguments.lifecycle_parent_context.as_deref(),
        issue: &arguments.issue,
        adopt_existing: arguments.adopt_existing,
    }) {
        Ok(started) => {
            print_start(&started, !arguments.rehydrate);
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("run lifecycle start failed: {error}");
            ExitCode::FAILURE
        }
    }
}

/// Execute one of the four terminal lifecycle commands.
#[must_use]
pub fn terminal(
    arguments: &LifecycleTerminalArguments,
    action: &'static str,
    outcome: LifecycleOutcome,
) -> ExitCode {
    let (repo_root, active, local, environment, homes) = match resolve(
        &arguments.repo_root,
        Some((&arguments.skill, &arguments.run_id)),
    ) {
        Ok(value) => value,
        Err((code, error)) => {
            print_terminal_failure(action, &error);
            return ExitCode::from(code);
        }
    };
    let loaded = match run_lifecycle::load(
        &repo_root,
        &arguments.skill,
        &arguments.run_id,
        &active,
        &local,
        &homes,
    ) {
        Ok(value) => value,
        Err(error) => {
            print_terminal_failure(action, &error.to_string());
            return ExitCode::FAILURE;
        }
    };
    let request = FinishRequest {
        repo_root: &repo_root,
        active_resolution: &active,
        local_resolution: &local,
        homes: &homes,
        environment: &environment,
        skill: &arguments.skill,
        run_id: &arguments.run_id,
        outcome,
        pre_scrub_violations: arguments.pre_scrub_violations,
    };
    match finish_with_store(&request, &loaded) {
        Ok(result) => {
            if let Some(error) = &result.breadcrumb_warning {
                eprintln!("WARN: larch-log commit breadcrumb publish failed: {error}");
            }
            if result.secret_scrub_violations > arguments.pre_scrub_violations {
                print_scrub_warning(
                    result.secret_scrub_violations - arguments.pre_scrub_violations,
                    result.files_scrubbed,
                    &loaded.context.run_dir,
                );
            }
            print_terminal(&result, &arguments.skill, &arguments.run_id);
            ExitCode::SUCCESS
        }
        Err(error) => {
            print_terminal_failure(action, &error);
            ExitCode::FAILURE
        }
    }
}

fn finish_with_store(
    request: &FinishRequest<'_>,
    loaded: &StartedRun,
) -> Result<TerminalResult, String> {
    let runtime = LarchRuntime::new().map_err(|error| error.to_string())?;
    let Some(storage) = loaded.resolution.storage() else {
        return runtime
            .block_on(run_lifecycle::finish(request, None))
            .map_err(|error| error.to_string());
    };
    match storage.scheme() {
        "gs" => runtime.block_on(async {
            let store = GoogleCloudStorage::new()
                .await
                .map_err(|_| "GCS object-store authentication failed".to_owned())?;
            run_lifecycle::finish(request, Some(&store))
                .await
                .map_err(|error| error.to_string())
        }),
        "s3" | "r2" => runtime.block_on(async {
            let store = s3_compatible_store(storage.scheme(), request.environment)
                .await
                .map_err(|error| error.to_string())?;
            run_lifecycle::finish(request, Some(&store))
                .await
                .map_err(|error| error.to_string())
        }),
        _ => Err("unsupported lifecycle object-store scheme".to_owned()),
    }
}

type Resolved = (
    PathBuf,
    RunLogStorageResolution,
    RunLogStorageResolution,
    HashMap<String, String>,
    LifecycleHomes,
);

fn resolve(
    repo_root: &std::path::Path,
    persisted: Option<(&str, &str)>,
) -> Result<Resolved, (u8, String)> {
    let (repo_root, origin, environment) = resolve_repository_environment_path(Some(repo_root))
        .map_err(|error| (2, preflight_message(error)))?;
    let repo_root = std::fs::canonicalize(repo_root).map_err(|error| (2, error.to_string()))?;
    let client_repo =
        repository_leaf_from_remote(&origin).map_err(|error| (2, error.to_string()))?;
    let local = RunLogStorageResolution::new(
        RunLogStorageMode::Disabled,
        RunLogStorageReason::ConfigFileMissing,
        None,
        client_repo,
        Some(local_namespace_id(&repo_root).map_err(|error| (2, error.to_string()))?),
    )
    .map_err(|error| (2, error.to_string()))?;
    let homes =
        LifecycleHomes::from_environment(&environment).map_err(|error| (1, error.to_string()))?;
    if let Some((skill, run_id)) = persisted
        && run_lifecycle::has_persisted_context(&homes, &local, &local, skill, run_id)
            .map_err(|error| (1, error.to_string()))?
    {
        return Ok((repo_root, local.clone(), local, environment, homes));
    }
    let active = resolve_run_log_storage(&repo_root, &environment, &origin)
        .map_err(|error| (2, preflight_message(PreflightFailure::Configuration(error))))?;
    Ok((repo_root, active, local, environment, homes))
}

fn preflight_message(error: PreflightFailure) -> String {
    match error {
        PreflightFailure::Configuration(error) => error.to_string(),
        PreflightFailure::Provider(error) => error.to_string(),
    }
}

fn print_start(started: &StartedRun, preflight_performed: bool) {
    print!("{}", render_start(started, preflight_performed));
    if started.resolution.mode() == RunLogStorageMode::Disabled {
        eprintln!(
            "**⚠ Run-log publication is disabled ({}). This skill will run, but no remote run-log archive or synchronized cache entry will be created.**",
            started.resolution.reason()
        );
    }
}

fn render_start(started: &StartedRun, preflight_performed: bool) -> String {
    let mut output = String::new();
    let _ = writeln!(output, "RUN_ID={}", started.context.run_id);
    let _ = writeln!(output, "SKILL={}", started.context.skill);
    let _ = writeln!(output, "LOG_ROOT={}", started.context.log_root.display());
    let _ = writeln!(output, "RUN_DIR={}", started.context.run_dir.display());
    let _ = writeln!(output, "CONTEXT_FILE={}", started.context_file.display());
    let mut preflight = format_preflight_stdout(&started.resolution);
    if !preflight_performed && started.resolution.mode() == RunLogStorageMode::Enabled {
        preflight = preflight
            .replace(
                "STORAGE_PREFLIGHT=ok\n",
                "STORAGE_PREFLIGHT=skipped-rehydrate\n",
            )
            .replace("PREFLIGHT_OK=true\n", "PREFLIGHT_OK=false\n");
    }
    output.push_str(&preflight);
    output.push_str("LIFECYCLE_STARTED=true\n");
    output
}

fn print_terminal(result: &TerminalResult, skill: &str, run_id: &str) {
    print!("{}", render_terminal(result, skill, run_id));
    if result.publication.is_none() {
        eprintln!(
            "**⚠ Run-log publication skipped because storage was disabled at lifecycle start ({}).**",
            result.resolution.reason()
        );
    }
}

fn render_terminal(result: &TerminalResult, skill: &str, run_id: &str) -> String {
    let mut output = String::new();
    let _ = writeln!(output, "RUN_ID={run_id}");
    let _ = writeln!(output, "SKILL={skill}");
    let _ = writeln!(output, "OUTCOME={}", result.outcome.as_str());
    let _ = writeln!(output, "RUN_LOG_STORAGE={}", result.resolution.mode());
    let _ = writeln!(
        output,
        "RUN_LOG_STORAGE_REASON={}",
        result.resolution.reason()
    );
    if let Some(publication) = &result.publication {
        let _ = writeln!(output, "REMOTE_KEY={}", publication.remote_key);
        let _ = writeln!(output, "ARCHIVE_SHA256={}", publication.archive_sha256);
        let _ = writeln!(output, "CACHE_DIR={}", publication.cache_dir.display());
        let _ = writeln!(
            output,
            "SECRET_SCRUB_VIOLATIONS={}",
            result.secret_scrub_violations
        );
        output.push_str("RUN_LOG_PUBLICATION=published\nLIFECYCLE_FLUSHED=true\n");
    } else {
        output.push_str("RUN_LOG_PUBLICATION=skipped-disabled\nLIFECYCLE_FLUSHED=false\n");
    }
    output.push_str("LIFECYCLE_TERMINALIZED=true\n");
    output
}

fn print_scrub_warning(violations: u64, files: u64, directory: &std::path::Path) {
    eprintln!(
        "\n#############################################################################\n\
         ##  !!  SECRETS DETECTED AND SCRUBBED FROM RUN LOGS BEFORE FLUSH  !!\n\
         #############################################################################\n\
         ## scrubbed {violations} secret-shaped value(s) across {files} file(s) in:\n\
         ##   {}\n\
         ## The flush proceeds with redacted content, but a credential was almost\n\
         ## certainly exposed in this run -- ROTATE it now and check chat/PRs for\n\
         ## the same value.\n\
         #############################################################################",
        directory.display()
    );
}

fn print_terminal_failure(action: &str, error: &str) {
    print!("{}", terminal_failure_stdout());
    eprintln!("run lifecycle {action} failed: {error}");
}

const fn terminal_failure_stdout() -> &'static str {
    "RUN_LOG_PUBLICATION=failed\nLIFECYCLE_FLUSHED=false\nLIFECYCLE_TERMINALIZED=false\n"
}

#[cfg(test)]
mod tests {
    use super::{render_start, render_terminal, terminal_failure_stdout};
    use larch_adapters::run_lifecycle::{PublicationResult, StartedRun, TerminalResult};
    use larch_core::{
        LifecycleContext, LifecycleOutcome, RunLogStorageMode, RunLogStorageReason,
        RunLogStorageResolution, StorageBase, ToolRepositoryStorage, injected_storage_resolution,
    };
    use std::path::PathBuf;

    fn started(resolution: RunLogStorageResolution) -> StartedRun {
        StartedRun {
            context: LifecycleContext::new(
                PathBuf::from("/repo"),
                &resolution,
                "review".to_owned(),
                "run-1".to_owned(),
                PathBuf::from("/logs"),
            ),
            context_file: PathBuf::from("/state/context.json"),
            resolution,
        }
    }

    fn disabled() -> RunLogStorageResolution {
        RunLogStorageResolution::new(
            RunLogStorageMode::Disabled,
            RunLogStorageReason::ConfigFileMissing,
            None,
            "client",
            Some("local-id".to_owned()),
        )
        .unwrap()
    }

    #[test]
    fn start_envelope_covers_every_documented_key_and_storage_pair() {
        let enabled = started(injected_storage_resolution(ToolRepositoryStorage::new(
            StorageBase::new("gs", "bucket"),
            "client",
        )));
        assert_eq!(
            render_start(&enabled, true),
            "RUN_ID=run-1\nSKILL=review\nLOG_ROOT=/logs\nRUN_DIR=/logs/review/run-1\n\
             CONTEXT_FILE=/state/context.json\nRUN_LOG_STORAGE=enabled\n\
             RUN_LOG_STORAGE_REASON=injected-storage\nSTORAGE_BASE_URI=gs://bucket\n\
             CLIENT_REPO=client\nTOOL_REPO_URI=gs://bucket/larch/client\n\
             RUN_LOGS_URI=gs://bucket/larch/client/run-logs/\nSTORAGE_PREFLIGHT=ok\n\
             PREFLIGHT_OK=true\nLIFECYCLE_STARTED=true\n"
        );
        let local = started(disabled());
        let output = render_start(&local, true);
        for line in [
            "RUN_LOG_STORAGE=disabled",
            "RUN_LOG_STORAGE_REASON=config-file-missing",
            "STORAGE_BASE_URI=",
            "TOOL_REPO_URI=",
            "RUN_LOGS_URI=",
            "STORAGE_PREFLIGHT=skipped-disabled",
            "PREFLIGHT_OK=true",
            "LIFECYCLE_STARTED=true",
        ] {
            assert!(output.lines().any(|candidate| candidate == line));
        }
    }

    #[test]
    fn terminal_envelope_covers_published_disabled_and_failure_pairs() {
        let published = TerminalResult {
            outcome: LifecycleOutcome::Success,
            resolution: injected_storage_resolution(ToolRepositoryStorage::new(
                StorageBase::new("gs", "bucket"),
                "client",
            )),
            publication: Some(PublicationResult {
                remote_key: "run-logs/review/run-1.tar.gz".to_owned(),
                archive_sha256: "a".repeat(64),
                cache_dir: PathBuf::from("/cache/run-1"),
            }),
            secret_scrub_violations: 2,
            files_scrubbed: 1,
            breadcrumb_warning: None,
        };
        let output = render_terminal(&published, "review", "run-1");
        for line in [
            "RUN_ID=run-1",
            "SKILL=review",
            "OUTCOME=success",
            "REMOTE_KEY=run-logs/review/run-1.tar.gz",
            "ARCHIVE_SHA256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "CACHE_DIR=/cache/run-1",
            "SECRET_SCRUB_VIOLATIONS=2",
            "RUN_LOG_PUBLICATION=published",
            "LIFECYCLE_FLUSHED=true",
            "LIFECYCLE_TERMINALIZED=true",
        ] {
            assert!(output.lines().any(|candidate| candidate == line));
        }
        let skipped = TerminalResult {
            outcome: LifecycleOutcome::Cancelled,
            resolution: disabled(),
            publication: None,
            secret_scrub_violations: 0,
            files_scrubbed: 0,
            breadcrumb_warning: None,
        };
        let output = render_terminal(&skipped, "review", "run-2");
        assert!(output.contains("RUN_LOG_PUBLICATION=skipped-disabled\n"));
        assert!(output.contains("LIFECYCLE_FLUSHED=false\n"));
        assert!(output.contains("LIFECYCLE_TERMINALIZED=true\n"));
        assert!(!output.contains("REMOTE_KEY="));
        assert_eq!(
            terminal_failure_stdout(),
            "RUN_LOG_PUBLICATION=failed\nLIFECYCLE_FLUSHED=false\nLIFECYCLE_TERMINALIZED=false\n"
        );
    }
}
