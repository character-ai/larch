//! Rust owner for `design pause-save` and `design pause-load` (#8589).

use std::{
    env,
    ffi::OsString,
    fs::{self, FileTimes},
    io::{self, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{
    GixRepository, PathIntent, SecureTempDir, TemporaryRoot, atomic_write_in_with,
    atomic_write_utf8_in, ensure_directory_chain, open_confined_read, remove_optional_file,
    run_lifecycle, validate_design_tmpdir,
};
use larch_core::{
    DuplicatePolicy, KvDocument, ParseOptions, PauseMarker, RepositoryRead, RunLogStorageMode,
    cleanup_cache_sessions_root, determine_pause_step, parse_pause_marker, pause_body_hash,
    redact_secrets_only, render_pause_state, valid_pause_step, validate_issue,
};
use serde_json::Value;

use crate::{
    bootstrap_support::valid_run_id,
    design_step0_commands::{
        env_get, load_source_env, resolve_owned_run_id, resolve_persisted_repo_root,
    },
    github_repository_resolution::{ambient_repo, repository_ref, validate_repo_slug},
    github_service::{ServiceFailure, with_github_service},
    run_log_commands,
    runtime_entrypoint::{plugin_root, run_verified_larch},
};

const SAVE_USAGE: &str =
    "Usage: design-pause-save.sh --design-tmpdir PATH --issue N [--repo OWNER/REPO]";
const LOAD_USAGE: &str =
    "Usage: design-pause-load.sh --design-tmpdir PATH --issue N [--repo OWNER/REPO]";

#[derive(Clone, Debug)]
struct PauseRequest {
    design_tmpdir: PathBuf,
    issue: String,
    repo: String,
}

enum ParsedRequest {
    Help,
    Request(PauseRequest),
    Usage,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum StorageAdmission {
    Enabled,
    Disabled,
    NotGitWorktree,
    LifecycleUnavailable,
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum CacheLookup {
    Found(PathBuf),
    Disabled,
    NotGitWorktree,
    Missing,
}

#[derive(Clone, Debug, Default)]
struct CapturedRun {
    rc: i32,
    stdout: String,
    stderr: String,
}

trait PauseEffects {
    fn plugin_root(&self) -> Option<PathBuf>;
    fn resolve_repo(&self, explicit: &str, persisted: &str) -> String;
    fn issue_body(&self, repo: &str, issue: u64) -> Result<String, String>;
    fn storage_admission(&self, request: &PauseRequest, run_id: &str) -> StorageAdmission;
    fn publish(&self, request: &PauseRequest, run_id: &str) -> CapturedRun;
    fn marker_write(&self, request: &PauseRequest, content: Option<&Path>) -> bool;
    fn worktree_available(&self) -> bool {
        true
    }
    fn cached_run(&self, run_id: &str) -> CacheLookup;
    fn deactivate_progress(&self, repo_root: &Path, run_id: &str);
}

struct LiveEffects;

impl PauseEffects for LiveEffects {
    fn plugin_root(&self) -> Option<PathBuf> {
        plugin_root().ok()
    }

    fn resolve_repo(&self, explicit: &str, persisted: &str) -> String {
        if !explicit.is_empty() {
            return explicit.to_owned();
        }
        if !persisted.is_empty() {
            return persisted.to_owned();
        }
        ambient_repo().unwrap_or_default()
    }

    fn issue_body(&self, repo: &str, issue: u64) -> Result<String, String> {
        let reference =
            repository_ref(repo).map_err(|()| "repository slug is unavailable".to_owned())?;
        with_github_service(async |service, cancellation| {
            larch_core::GitHubService::issue(service, &reference, issue, cancellation)
                .await
                .map(|value| value.body)
                .map_err(|error| error.to_string())
        })
        .map_err(ServiceFailure::into_detail)
    }

    fn storage_admission(&self, request: &PauseRequest, run_id: &str) -> StorageAdmission {
        let Some(persisted_root) = resolve_persisted_repo_root(&request.design_tmpdir) else {
            return StorageAdmission::LifecycleUnavailable;
        };
        let Ok(repository) = GixRepository::discover(&persisted_root) else {
            return StorageAdmission::NotGitWorktree;
        };
        if repository.location().work_dir.is_none() {
            return StorageAdmission::NotGitWorktree;
        }
        let Ok((repo_root, _origin, _environment)) =
            run_log_commands::resolve_repository_environment_path(Some(&persisted_root))
        else {
            return StorageAdmission::LifecycleUnavailable;
        };
        let output = run_verified_larch(&[
            "run-log".into(),
            "lifecycle-start".into(),
            "--repo-root".into(),
            repo_root.into_os_string(),
            "--skill".into(),
            "design".into(),
            "--run-id".into(),
            run_id.into(),
            "--adopt-existing".into(),
            "--rehydrate".into(),
        ]);
        let Ok(output) = output else {
            return StorageAdmission::LifecycleUnavailable;
        };
        let (rc, stdout, _stderr) = output.decoded_streams();
        if rc != 0 {
            return StorageAdmission::LifecycleUnavailable;
        }
        match kv_last(&stdout, "RUN_LOG_STORAGE").as_str() {
            "enabled" => StorageAdmission::Enabled,
            "disabled" => StorageAdmission::Disabled,
            _ => StorageAdmission::LifecycleUnavailable,
        }
    }

    fn publish(&self, request: &PauseRequest, run_id: &str) -> CapturedRun {
        let mut arguments = vec![
            "design".into(),
            "log-publish".into(),
            "--reason".into(),
            "pause".into(),
            "--design-tmpdir".into(),
            request.design_tmpdir.as_os_str().to_owned(),
            "--run-id".into(),
            run_id.into(),
            "--issue".into(),
            request.issue.as_str().into(),
            "--outcome".into(),
            "paused".into(),
        ];
        append_repo(&mut arguments, &request.repo);
        capture(run_verified_larch(&arguments))
    }

    fn marker_write(&self, request: &PauseRequest, content: Option<&Path>) -> bool {
        let mut arguments = vec![
            "named-block".into(),
            "write".into(),
            "--marker".into(),
            "design-pause".into(),
        ];
        match content {
            Some(path) => arguments.extend(["--content-file".into(), path.as_os_str().to_owned()]),
            None => arguments.push("--delete".into()),
        }
        arguments.extend(["--issue".into(), request.issue.as_str().into()]);
        append_repo(&mut arguments, &request.repo);
        let captured = capture(run_verified_larch(&arguments));
        forward(&captured);
        captured.rc == 0
    }

    fn worktree_available(&self) -> bool {
        current_worktree()
    }

    fn cached_run(&self, run_id: &str) -> CacheLookup {
        if !current_worktree() {
            return CacheLookup::NotGitWorktree;
        }
        let Ok((_repo_root, resolution, environment)) =
            run_log_commands::resolve_storage_path(None)
        else {
            return CacheLookup::Missing;
        };
        if resolution.mode() == RunLogStorageMode::Disabled {
            return CacheLookup::Disabled;
        }
        let (Some(storage), Ok(homes)) = (
            resolution.storage(),
            run_lifecycle::LifecycleHomes::from_environment(&environment),
        ) else {
            return CacheLookup::Missing;
        };
        let Ok(cache) =
            run_lifecycle::published_run_cache_directory(&homes, storage, "design", run_id)
        else {
            return CacheLookup::Missing;
        };
        run_lifecycle::verify_materialized_run_directory(&cache, "design", run_id)
            .map_or(CacheLookup::Missing, |result| {
                CacheLookup::Found(result.run_dir)
            })
    }

    fn deactivate_progress(&self, repo_root: &Path, run_id: &str) {
        let _ = run_verified_larch(&[
            "progress".into(),
            "deactivate".into(),
            "--repo-root".into(),
            repo_root.as_os_str().to_owned(),
            "--run-id".into(),
            run_id.into(),
        ]);
    }
}

/// Entry point for `larch design pause-save`.
#[must_use]
pub fn pause_save_main(arguments: &[OsString]) -> ExitCode {
    pause_save_with(arguments, &LiveEffects)
}

/// Entry point for `larch design pause-load`.
#[must_use]
pub fn pause_load_main(arguments: &[OsString]) -> ExitCode {
    pause_load_with(arguments, &LiveEffects)
}

fn parse_request(arguments: &[OsString]) -> ParsedRequest {
    let values = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect::<Vec<_>>();
    let mut request = PauseRequest {
        design_tmpdir: PathBuf::new(),
        issue: String::new(),
        repo: String::new(),
    };
    let mut index = 0;
    while index < values.len() {
        match values[index].as_str() {
            "--design-tmpdir" | "--issue" | "--repo" if index + 1 < values.len() => {
                match values[index].as_str() {
                    "--design-tmpdir" => request.design_tmpdir = values[index + 1].as_str().into(),
                    "--issue" => values[index + 1].clone_into(&mut request.issue),
                    "--repo" => values[index + 1].clone_into(&mut request.repo),
                    _ => unreachable!(),
                }
                index += 2;
            }
            "-h" | "--help" => return ParsedRequest::Help,
            _ => return ParsedRequest::Usage,
        }
    }
    if request.design_tmpdir.as_os_str().is_empty() || request.issue.is_empty() {
        ParsedRequest::Usage
    } else {
        ParsedRequest::Request(request)
    }
}

#[allow(clippy::too_many_lines)] // One ordered publish transaction preserves the legacy failure contract.
fn pause_save_with(arguments: &[OsString], effects: &dyn PauseEffects) -> ExitCode {
    let mut request = match parse_request(arguments) {
        ParsedRequest::Help => return ExitCode::SUCCESS,
        ParsedRequest::Usage => {
            println!("{SAVE_USAGE}");
            return ExitCode::FAILURE;
        }
        ParsedRequest::Request(request) => request,
    };
    let Some(design_tmpdir) = validated_tmpdir(&request.design_tmpdir, false) else {
        emit_failure("PAUSE_OK", "tmpdir-not-allowed");
        return ExitCode::SUCCESS;
    };
    if !design_tmpdir.is_dir() {
        emit_failure("PAUSE_OK", "tmpdir-missing");
        return ExitCode::SUCCESS;
    }
    request.design_tmpdir = design_tmpdir;
    let Some(issue) = positive_issue(&request.issue) else {
        emit_failure("PAUSE_OK", "invalid-issue");
        return ExitCode::SUCCESS;
    };
    let source_env = request.design_tmpdir.join("source-env.sh");
    let source_values = load_source_env(source_env.to_str().unwrap_or_default(), "");
    request.repo = effects.resolve_repo(&request.repo, env_get(&source_values, "REPO", ""));
    if !request.repo.is_empty() && !validate_repo_slug(&request.repo) {
        emit_failure("PAUSE_OK", "invalid-repo");
        return ExitCode::SUCCESS;
    }
    let persisted_run_id = env_get(&source_values, "SESSION_ID", "");
    let run_id = if persisted_run_id.is_empty() {
        env::var("SESSION_ID").unwrap_or_default()
    } else {
        persisted_run_id.to_owned()
    };
    if !valid_run_id(&run_id) {
        emit_failure("PAUSE_OK", "invalid-run-id");
        return ExitCode::SUCCESS;
    }
    match effects.storage_admission(&request, &run_id) {
        StorageAdmission::Enabled => {}
        StorageAdmission::Disabled => {
            eprintln!(
                "Cross-session /design pause requires configured run-log storage; configure [larch].storage_base_uri or set LARCH_STORAGE_BASE_URI."
            );
            emit_failure("PAUSE_OK", "run-log-storage-disabled");
            return ExitCode::SUCCESS;
        }
        StorageAdmission::NotGitWorktree => {
            emit_failure("PAUSE_OK", "not-git-worktree");
            return ExitCode::SUCCESS;
        }
        StorageAdmission::LifecycleUnavailable => {
            emit_failure("PAUSE_OK", "lifecycle-context-unavailable");
            return ExitCode::SUCCESS;
        }
    }
    let Some(root) = effects.plugin_root() else {
        emit_failure("PAUSE_OK", "lifecycle-context-unavailable");
        return ExitCode::SUCCESS;
    };
    let registry =
        fs::read_to_string(root.join("skills/design/scripts/step-name-registry.tsv")).ok();
    let completed = request.design_tmpdir.join(".completed");
    let step = determine_pause_step(
        request.design_tmpdir.join(".step3-reentry").is_file(),
        |step| completed.join(format!("step-{step}")).is_file(),
        registry.as_deref(),
    );
    let body = match effects.issue_body(&request.repo, issue) {
        Ok(body) => body,
        Err(error) => {
            eprintln!("{}", redact_secrets_only(&error));
            return ExitCode::FAILURE;
        }
    };
    let Ok(state) = render_pause_state(
        &step,
        &request.issue,
        &run_id,
        &request.repo,
        request.design_tmpdir.join(".brainstorm-done").is_file(),
        &pause_body_hash(&body),
    ) else {
        emit_failure("PAUSE_OK", "state-write-failed");
        return ExitCode::SUCCESS;
    };
    let Ok(design_root) = TemporaryRoot::resolve(Some(&request.design_tmpdir)) else {
        emit_failure("PAUSE_OK", "tmpdir-not-allowed");
        return ExitCode::SUCCESS;
    };
    let state_file = request.design_tmpdir.join("pause-state.txt");
    if atomic_write_utf8_in(
        &design_root,
        &state_file,
        &redact_secrets_only(&state),
        false,
        0o600,
    )
    .is_err()
    {
        emit_failure("PAUSE_OK", "state-write-failed");
        return ExitCode::SUCCESS;
    }
    let publish = effects.publish(&request, &run_id);
    if kv_last(&publish.stdout, "PUBLISH_OK") != "true" {
        let recovery = kv_last(&publish.stdout, "RECOVERY_BRANCH");
        if recovery.is_empty() {
            emit_failure("PAUSE_OK", "publish-and-recovery-failed");
        } else {
            println!("PAUSE_OK=false");
            println!("ERROR=publish-local-recovery-only");
            println!("LOG_RECOVERY_BRANCH={recovery}");
        }
        return ExitCode::SUCCESS;
    }
    if !effects.marker_write(&request, Some(&state_file)) {
        emit_failure("PAUSE_OK", "marker-write-failed");
        return ExitCode::SUCCESS;
    }
    let _ = remove_optional_file(&request.design_tmpdir.join(".pause-requested"));
    if atomic_write_utf8_in(
        &design_root,
        &request.design_tmpdir.join(".pause-save-complete"),
        "",
        false,
        0o600,
    )
    .is_err()
    {
        emit_failure("PAUSE_OK", "state-write-failed");
        return ExitCode::SUCCESS;
    }
    if let Some(repo_root) = resolve_persisted_repo_root(&request.design_tmpdir) {
        let effective_run =
            resolve_owned_run_id(&request.design_tmpdir).unwrap_or_else(|| run_id.clone());
        effects.deactivate_progress(&repo_root, &effective_run);
    }
    println!("PAUSE_OK=true");
    println!("STEP={step}");
    println!("RUN_ID={run_id}");
    ExitCode::SUCCESS
}

#[allow(clippy::too_many_lines)] // Staging, identity checks, and marker policy form one restore transaction.
fn pause_load_with(arguments: &[OsString], effects: &dyn PauseEffects) -> ExitCode {
    let mut request = match parse_request(arguments) {
        ParsedRequest::Help => return ExitCode::SUCCESS,
        ParsedRequest::Usage => {
            println!("{LOAD_USAGE}");
            return ExitCode::FAILURE;
        }
        ParsedRequest::Request(request) => request,
    };
    let Some(design_tmpdir) = validated_tmpdir(&request.design_tmpdir, true) else {
        emit_failure("LOAD_OK", "tmpdir-not-allowed");
        return ExitCode::SUCCESS;
    };
    request.design_tmpdir = design_tmpdir;
    let Some(issue) = positive_issue(&request.issue) else {
        emit_failure("LOAD_OK", "invalid-issue");
        return ExitCode::SUCCESS;
    };
    request.repo = effects.resolve_repo(&request.repo, "");
    if !request.repo.is_empty() && !validate_repo_slug(&request.repo) {
        emit_failure("LOAD_OK", "invalid-repo");
        return ExitCode::SUCCESS;
    }
    let body = match effects.issue_body(&request.repo, issue) {
        Ok(body) => body,
        Err(error) => {
            eprintln!("{}", redact_secrets_only(&error));
            return ExitCode::FAILURE;
        }
    };
    let payload = match parse_pause_marker(&body) {
        PauseMarker::Absent => {
            emit_failure("LOAD_OK", "no-pause-marker");
            return ExitCode::SUCCESS;
        }
        PauseMarker::Malformed => {
            return permanent_load_failure(effects, &request, "malformed-pause-marker");
        }
        PauseMarker::Present(payload) => payload,
    };
    let run_id = payload.get("RUN_ID").cloned().unwrap_or_default();
    let mut step = payload.get("STEP").cloned().unwrap_or_default();
    if payload.get("ISSUE_NUMBER").map(String::as_str) != Some(request.issue.as_str()) {
        return permanent_load_failure(effects, &request, "issue-mismatch");
    }
    let marker_repo = payload.get("REPO").map_or("", String::as_str);
    if !marker_repo.is_empty() && !request.repo.is_empty() && marker_repo != request.repo {
        return permanent_load_failure(effects, &request, "repo-mismatch");
    }
    if !valid_run_id(&run_id) {
        return permanent_load_failure(effects, &request, "invalid-run-id");
    }
    if !effects.worktree_available() {
        emit_failure("LOAD_OK", "not-git-worktree");
        return ExitCode::SUCCESS;
    }
    if payload
        .get("LOG_RECOVERY_BRANCH")
        .is_some_and(|value| !value.is_empty())
    {
        return permanent_load_failure(effects, &request, "legacy-git-snapshot");
    }
    let cached_run = match effects.cached_run(&run_id) {
        CacheLookup::Found(path) => path,
        CacheLookup::Disabled => {
            eprintln!(
                "Cross-session /design resume requires configured run-log storage; configure [larch].storage_base_uri or set LARCH_STORAGE_BASE_URI."
            );
            emit_failure("LOAD_OK", "run-log-storage-disabled");
            return ExitCode::SUCCESS;
        }
        CacheLookup::NotGitWorktree => {
            emit_failure("LOAD_OK", "not-git-worktree");
            return ExitCode::SUCCESS;
        }
        CacheLookup::Missing => {
            emit_failure("LOAD_OK", "snapshot-not-found");
            return ExitCode::SUCCESS;
        }
    };
    let Ok(design_root) = TemporaryRoot::resolve(Some(&request.design_tmpdir)) else {
        emit_failure("LOAD_OK", "tmpdir-not-allowed");
        return ExitCode::SUCCESS;
    };
    let Ok(restore) = SecureTempDir::create(&design_root, "design-pause-load-restore.") else {
        emit_failure("LOAD_OK", "snapshot-extract-failed");
        return ExitCode::SUCCESS;
    };
    let Ok(restore_root) = TemporaryRoot::resolve(Some(restore.path())) else {
        emit_failure("LOAD_OK", "snapshot-extract-failed");
        return ExitCode::SUCCESS;
    };
    if copy_snapshot_to_stage(&cached_run, &restore_root).is_err() {
        emit_failure("LOAD_OK", "snapshot-extract-failed");
        return ExitCode::SUCCESS;
    }
    for required in ["manifest.json", "run-params.json", "pause-state.txt"] {
        if !restore.path().join(required).is_file() {
            emit_failure("LOAD_OK", "missing-restored-artifact");
            return ExitCode::SUCCESS;
        }
    }
    if !manifest_matches(
        &restore.path().join("manifest.json"),
        &request.issue,
        &run_id,
    ) {
        return permanent_load_failure(effects, &request, "manifest-mismatch");
    }
    if !valid_pause_step(&step) {
        return permanent_load_failure(effects, &request, "invalid-step");
    }
    if atomic_write_utf8_in(
        &restore_root,
        &restore.path().join(".resume-loaded"),
        "",
        false,
        0o600,
    )
    .is_err()
    {
        emit_failure("LOAD_OK", "snapshot-extract-failed");
        return ExitCode::SUCCESS;
    }
    if install_snapshot(&restore_root, &design_root).is_err() {
        emit_failure("LOAD_OK", "unsafe-restored-path");
        return ExitCode::SUCCESS;
    }
    let _ = remove_optional_file(&request.design_tmpdir.join(".pause-save-complete"));
    let _ = remove_optional_file(&request.design_tmpdir.join(".pause-requested"));
    let completed = request.design_tmpdir.join(".completed");
    if step == "5c" && completed.join("step-5b").is_file() && !completed.join("step-5b.5").is_file()
    {
        "5b.5".clone_into(&mut step);
    }
    let marker_cleared = effects.marker_write(&request, None);
    println!("LOAD_OK=true");
    println!("STEP={step}");
    println!(
        "SESSION_ID={}",
        payload.get("SESSION_ID").unwrap_or(&run_id)
    );
    println!("RUN_ID={run_id}");
    println!(
        "BRAINSTORM_DONE={}",
        payload
            .get("BRAINSTORM_DONE")
            .map_or("false", String::as_str)
    );
    if !request.repo.is_empty() {
        println!("REPO={}", request.repo);
    }
    println!(
        "MARKER_CLEARED={}",
        if marker_cleared { "true" } else { "false" }
    );
    if !marker_cleared {
        println!("WARN=marker-delete-failed");
    }
    ExitCode::SUCCESS
}

fn validated_tmpdir(path: &Path, create: bool) -> Option<PathBuf> {
    let raw = path.to_str()?;
    let cache_root = cleanup_cache_sessions_root(
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    );
    validate_design_tmpdir(raw, env::var_os("TMPDIR").as_deref(), &cache_root).ok()?;
    if create && ensure_directory_chain(path).is_err() {
        return None;
    }
    let resolved = if path.exists() {
        fs::canonicalize(path).ok()?
    } else {
        path.to_path_buf()
    };
    validate_design_tmpdir(
        resolved.to_str()?,
        env::var_os("TMPDIR").as_deref(),
        &cache_root,
    )
    .ok()?;
    Some(resolved)
}

fn current_worktree() -> bool {
    let Ok(cwd) = env::current_dir() else {
        return false;
    };
    GixRepository::discover(cwd)
        .ok()
        .is_some_and(|repository| repository.location().work_dir.is_some())
}

fn copy_snapshot_to_stage(source: &Path, stage: &TemporaryRoot) -> Result<(), ()> {
    let source_root = TemporaryRoot::resolve(Some(source)).map_err(|_error| ())?;
    let entries = sorted_entries(source_root.path())?;
    for entry in entries {
        if entry.file_name() == run_lifecycle::ARCHIVE_MANIFEST_NAME {
            continue;
        }
        copy_entry(
            &source_root,
            &entry.path(),
            stage,
            Path::new(&entry.file_name()),
        )?;
    }
    Ok(())
}

fn copy_entry(
    source_root: &TemporaryRoot,
    source: &Path,
    destination: &TemporaryRoot,
    relative: &Path,
) -> Result<(), ()> {
    let metadata = fs::symlink_metadata(source).map_err(|_error| ())?;
    if metadata.file_type().is_symlink() {
        return Err(());
    }
    if metadata.is_dir() {
        destination
            .ensure_directory(relative)
            .map_err(|_error| ())?;
        for entry in sorted_entries(source)? {
            copy_entry(
                source_root,
                &entry.path(),
                destination,
                &relative.join(entry.file_name()),
            )?;
        }
        return Ok(());
    }
    if !metadata.is_file() {
        return Err(());
    }
    let confined = source_root
        .confine(source, PathIntent::Read)
        .map_err(|_error| ())?;
    let mut input = open_confined_read(&confined).map_err(|_error| ())?;
    let times = FileTimes::new()
        .set_accessed(metadata.accessed().map_err(|_error| ())?)
        .set_modified(metadata.modified().map_err(|_error| ())?);
    atomic_write_in_with(
        destination,
        relative,
        true,
        file_mode(&metadata),
        |output| {
            io::copy(&mut input, output)?;
            output.set_times(times)
        },
    )
    .map_err(|_error| ())
}

fn install_snapshot(source: &TemporaryRoot, destination: &TemporaryRoot) -> Result<(), ()> {
    for entry in sorted_entries(source.path())? {
        preflight_entry(
            &entry.path(),
            destination.path(),
            Path::new(&entry.file_name()),
        )?;
    }
    for entry in sorted_entries(source.path())? {
        copy_entry(
            source,
            &entry.path(),
            destination,
            Path::new(&entry.file_name()),
        )?;
    }
    Ok(())
}

fn preflight_entry(source: &Path, root: &Path, relative: &Path) -> Result<(), ()> {
    let metadata = fs::symlink_metadata(source).map_err(|_error| ())?;
    if metadata.file_type().is_symlink() || (!metadata.is_dir() && !metadata.is_file()) {
        return Err(());
    }
    preflight_target(root, relative, metadata.is_dir())?;
    if metadata.is_dir() {
        for entry in sorted_entries(source)? {
            preflight_entry(&entry.path(), root, &relative.join(entry.file_name()))?;
        }
    }
    Ok(())
}

fn preflight_target(root: &Path, relative: &Path, source_is_dir: bool) -> Result<(), ()> {
    let target = root.join(relative);
    let mut current = root.to_path_buf();
    for component in relative.components() {
        current.push(component.as_os_str());
        let Ok(metadata) = fs::symlink_metadata(&current) else {
            return Ok(());
        };
        if metadata.file_type().is_symlink() {
            return Err(());
        }
        if current == target {
            if source_is_dir != metadata.is_dir() || (!source_is_dir && !metadata.is_file()) {
                return Err(());
            }
        } else if !metadata.is_dir() {
            return Err(());
        }
    }
    Ok(())
}

fn sorted_entries(path: &Path) -> Result<Vec<fs::DirEntry>, ()> {
    let mut entries = fs::read_dir(path)
        .map_err(|_error| ())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_error| ())?;
    entries.sort_by_key(fs::DirEntry::file_name);
    Ok(entries)
}

#[cfg(unix)]
fn file_mode(metadata: &fs::Metadata) -> u32 {
    use std::os::unix::fs::PermissionsExt as _;
    metadata.permissions().mode() & 0o777
}

#[cfg(not(unix))]
fn file_mode(_metadata: &fs::Metadata) -> u32 {
    0o600
}

fn manifest_matches(path: &Path, issue: &str, run_id: &str) -> bool {
    let Ok(bytes) = fs::read(path) else {
        return false;
    };
    let Ok(Value::Object(manifest)) = serde_json::from_str(&String::from_utf8_lossy(&bytes)) else {
        return false;
    };
    let manifest_issue = json_scalar(manifest.get("issue_number"));
    let manifest_run = json_scalar(manifest.get("run_id"));
    (manifest_issue.is_empty() || manifest_issue == issue)
        && (manifest_run.is_empty() || manifest_run == run_id)
}

fn json_scalar(value: Option<&Value>) -> String {
    match value {
        None | Some(Value::Null) => String::new(),
        Some(Value::String(value)) => value.clone(),
        Some(value) => value.to_string(),
    }
}

fn permanent_load_failure(
    effects: &dyn PauseEffects,
    request: &PauseRequest,
    error: &str,
) -> ExitCode {
    let _cleared = effects.marker_write(request, None);
    emit_failure("LOAD_OK", error);
    ExitCode::SUCCESS
}

fn capture(output: Result<larch_core::ProcessOutput, String>) -> CapturedRun {
    output.map_or_else(
        |error| CapturedRun {
            rc: 1,
            stderr: error,
            ..CapturedRun::default()
        },
        |output| {
            let (rc, stdout, stderr) = output.decoded_streams();
            CapturedRun { rc, stdout, stderr }
        },
    )
}

fn forward(output: &CapturedRun) {
    let _ = io::stdout().write_all(output.stdout.as_bytes());
    let _ = io::stderr().write_all(output.stderr.as_bytes());
}

fn append_repo(arguments: &mut Vec<OsString>, repo: &str) {
    if !repo.is_empty() {
        arguments.extend(["--repo".into(), repo.into()]);
    }
}

fn positive_issue(value: &str) -> Option<u64> {
    validate_issue(value).then(|| value.parse().ok()).flatten()
}

fn kv_last(text: &str, key: &str) -> String {
    KvDocument::parse(text, ParseOptions::legacy())
        .map(|document| document.select(DuplicatePolicy::Last))
        .ok()
        .and_then(|values| values.get(key).cloned())
        .unwrap_or_default()
}

fn emit_failure(key: &str, error: &str) {
    println!("{key}=false");
    println!("ERROR={error}");
}

#[cfg(test)]
mod tests {
    use std::cell::{Cell, RefCell};

    use larch_core::{DESIGN_PAUSE_END as END, DESIGN_PAUSE_START as START};

    use super::*;

    macro_rules! ok {
        ($call:expr) => {
            assert_eq!($call, ExitCode::SUCCESS)
        };
    }

    const VALID_FIELDS: &str = "ISSUE_NUMBER=42\nREPO=owner/repo\nRUN_ID=run-42\nSTEP=2\n";
    const VALID_MANIFEST: &str = r#"{"issue_number":"42","run_id":"run-42"}"#;

    struct FakeEffects {
        root: PathBuf,
        body: RefCell<Result<String, String>>,
        cache: RefCell<CacheLookup>,
        admission: Cell<StorageAdmission>,
        publish: RefCell<CapturedRun>,
        marker_ok: Cell<bool>,
    }

    impl FakeEffects {
        fn new(root: PathBuf) -> Self {
            Self {
                root,
                body: RefCell::new(Ok("issue body\n".into())),
                cache: RefCell::new(CacheLookup::Missing),
                admission: Cell::new(StorageAdmission::Enabled),
                publish: RefCell::new(CapturedRun {
                    stdout: "PUBLISH_OK=true\n".into(),
                    ..CapturedRun::default()
                }),
                marker_ok: Cell::new(true),
            }
        }
    }

    impl PauseEffects for FakeEffects {
        fn plugin_root(&self) -> Option<PathBuf> {
            Some(self.root.clone())
        }
        fn resolve_repo(&self, explicit: &str, _persisted: &str) -> String {
            explicit.to_owned()
        }
        fn issue_body(&self, _repo: &str, _issue: u64) -> Result<String, String> {
            self.body.borrow().clone()
        }
        fn storage_admission(&self, _request: &PauseRequest, _run_id: &str) -> StorageAdmission {
            self.admission.get()
        }
        fn publish(&self, _request: &PauseRequest, _run_id: &str) -> CapturedRun {
            self.publish.borrow().clone()
        }
        fn marker_write(&self, _request: &PauseRequest, content: Option<&Path>) -> bool {
            if !self.marker_ok.get() {
                return false;
            }
            if let Some(path) = content {
                let state = fs::read_to_string(path).expect("pause state");
                *self.body.borrow_mut() = Ok(format!("body\n{START}\n{state}{END}\n"));
            }
            true
        }
        fn cached_run(&self, _run_id: &str) -> CacheLookup {
            self.cache.borrow().clone()
        }
        fn deactivate_progress(&self, _root: &Path, _run_id: &str) {}
    }

    fn request(root: &Path, issue: &str, repo: &str) -> Vec<OsString> {
        vec![
            "--design-tmpdir".into(),
            root.as_os_str().into(),
            "--issue".into(),
            issue.into(),
            "--repo".into(),
            repo.into(),
        ]
    }

    fn args(root: &Path) -> Vec<OsString> {
        request(root, "42", "owner/repo")
    }

    fn put(root: &Path, name: &str, content: &str) {
        fs::write(root.join(name), content).expect("fixture write");
    }

    fn write_source(design: &Path, repo_root: &Path, run_id: &str) {
        let content = format!(
            "export SESSION_ID={run_id}\nexport REPO=owner/repo\nexport REPO_ROOT={}\n",
            repo_root.display()
        );
        put(design, "source-env.sh", &content);
    }

    fn setup(root: &Path) -> (PathBuf, FakeEffects) {
        let plugin = root.join("plugin");
        fs::create_dir_all(plugin.join("skills/design/scripts")).expect("plugin");
        put(
            &plugin,
            "skills/design/scripts/step-name-registry.tsv",
            "step\tname\n0\tsetup\n1\tone\n2\ttwo\n",
        );
        let design = root.join("design");
        fs::create_dir_all(design.join(".completed")).expect("design");
        write_source(&design, root, "run-42");
        put(&design, ".completed/step-1", "sentinel\n");
        (design, FakeEffects::new(plugin))
    }

    fn marker(fields: &str) -> String {
        format!("{START}\n{fields}{END}\n")
    }

    fn set_marker(effects: &FakeEffects, fields: &str) {
        *effects.body.borrow_mut() = Ok(marker(fields));
    }

    fn cache(root: &Path, name: &str, manifest: &str) -> PathBuf {
        let path = root.join(name);
        fs::create_dir_all(&path).expect("cache");
        put(&path, "pause-state.txt", "state\n");
        put(&path, "run-params.json", "{}\n");
        put(&path, "manifest.json", manifest);
        path
    }

    #[test]
    fn save_contract_covers_validation_and_transaction_failures() {
        let temp = tempfile::tempdir().expect("fixture");
        let (design, effects) = setup(temp.path());
        let missing = temp.path().join("missing");
        ok!(pause_save_with(&args(&missing), &effects));
        write_source(&design, temp.path(), "bad/run");
        ok!(pause_save_with(&args(&design), &effects));
        write_source(&design, temp.path(), "run-42");
        effects.admission.set(StorageAdmission::Disabled);
        ok!(pause_save_with(&args(&design), &effects));
        effects.admission.set(StorageAdmission::Enabled);
        *effects.body.borrow_mut() = Err("issue read failed".into());
        assert_eq!(pause_save_with(&args(&design), &effects), ExitCode::FAILURE);
        *effects.body.borrow_mut() = Ok("body\n".into());
        fs::create_dir(design.join("pause-state.txt")).expect("state collision");
        ok!(pause_save_with(&args(&design), &effects));
        fs::remove_dir(design.join("pause-state.txt")).expect("remove collision");
        for stdout in [
            "PUBLISH_OK=false\n",
            "PUBLISH_OK=false\nRECOVERY_BRANCH=recovery/run-42\n",
        ] {
            effects.publish.borrow_mut().stdout = stdout.into();
            ok!(pause_save_with(&args(&design), &effects));
        }
        effects.publish.borrow_mut().stdout = "PUBLISH_OK=true\n".into();
        effects.marker_ok.set(false);
        ok!(pause_save_with(&args(&design), &effects));
    }

    #[test]
    fn load_contract_covers_identity_storage_and_retry_policy() {
        let temp = tempfile::tempdir().expect("fixture");
        let design = temp.path().join("design");
        let effects = FakeEffects::new(temp.path().to_path_buf());
        assert_eq!(pause_load_with(&[], &effects), ExitCode::FAILURE);
        ok!(pause_load_with(
            &request(&design, "0", "owner/repo"),
            &effects
        ));
        *effects.body.borrow_mut() = Err("issue read failed".into());
        assert_eq!(pause_load_with(&args(&design), &effects), ExitCode::FAILURE);
        for body in [
            "body\n".to_owned(),
            marker("BROKEN\n"),
            marker("ISSUE_NUMBER=43\nREPO=owner/repo\nRUN_ID=run-42\nSTEP=2\n"),
            marker("ISSUE_NUMBER=42\nREPO=owner/repo\nRUN_ID=bad/run\nSTEP=2\n"),
        ] {
            *effects.body.borrow_mut() = Ok(body);
            ok!(pause_load_with(&args(&design), &effects));
        }
        set_marker(
            &effects,
            &format!("{VALID_FIELDS}LOG_RECOVERY_BRANCH=old\n"),
        );
        ok!(pause_load_with(&args(&design), &effects));
        set_marker(&effects, VALID_FIELDS);
        for lookup in [
            CacheLookup::Disabled,
            CacheLookup::NotGitWorktree,
            CacheLookup::Missing,
            CacheLookup::Found(temp.path().join("absent")),
        ] {
            *effects.cache.borrow_mut() = lookup;
            ok!(pause_load_with(&args(&design), &effects));
        }
    }

    #[test]
    fn restore_validation_and_round_trip_preserve_files_and_marker_policy() {
        let temp = tempfile::tempdir().expect("fixture");
        let (design, effects) = setup(temp.path());
        put(&design, "run-params.json", "{}\n");
        put(&design, "manifest.json", VALID_MANIFEST);
        put(&design, "architectural-invariant-gatec-tier2.count", "1\n");
        let assessment = "architectural-guideline-assessment.md";
        put(&design, assessment, "assessment\n");
        ok!(pause_save_with(&args(&design), &effects));
        let snapshot = temp.path().join("snapshot");
        fs::create_dir(&snapshot).expect("snapshot");
        let snapshot_root = TemporaryRoot::resolve(Some(&snapshot)).expect("snapshot root");
        copy_snapshot_to_stage(&design, &snapshot_root).expect("snapshot copy");
        let pinned = std::time::UNIX_EPOCH + std::time::Duration::from_secs(1_700_000_000);
        let sentinel = snapshot.join(".completed/step-1");
        fs::OpenOptions::new()
            .write(true)
            .open(&sentinel)
            .expect("open sentinel")
            .set_times(FileTimes::new().set_accessed(pinned).set_modified(pinned))
            .expect("pin time");
        fs::remove_dir_all(design.join(".completed")).expect("clear completed");
        for name in [
            "run-params.json",
            "architectural-invariant-gatec-tier2.count",
            "architectural-guideline-assessment.md",
        ] {
            fs::remove_file(design.join(name)).expect("clear artifact");
        }
        *effects.cache.borrow_mut() = CacheLookup::Found(snapshot.clone());
        ok!(pause_load_with(&args(&design), &effects));
        let restored = design.join(".completed/step-1");
        assert_eq!(fs::read_to_string(&restored).unwrap(), "sentinel\n");
        assert_eq!(fs::metadata(restored).unwrap().modified().unwrap(), pinned);
        for (name, expected) in [
            ("architectural-invariant-gatec-tier2.count", "1\n"),
            (assessment, "assessment\n"),
        ] {
            assert_eq!(fs::read_to_string(design.join(name)).unwrap(), expected);
        }
        set_marker(&effects, VALID_FIELDS);
        let drift = cache(temp.path(), "drift", r#"{"issue_number":"43"}"#);
        *effects.cache.borrow_mut() = CacheLookup::Found(drift);
        ok!(pause_load_with(&args(&design), &effects));
        set_marker(
            &effects,
            "ISSUE_NUMBER=42\nREPO=owner/repo\nRUN_ID=run-42\nSTEP=unknown\n",
        );
        *effects.cache.borrow_mut() = CacheLookup::Found(snapshot);
        ok!(pause_load_with(&args(&design), &effects));
    }

    #[test]
    #[cfg(unix)]
    fn restore_and_helper_edges_reject_unsafe_paths() {
        let temp = tempfile::tempdir().expect("fixture");
        let design = temp.path().join("design");
        let effects = FakeEffects::new(temp.path().to_path_buf());
        set_marker(&effects, VALID_FIELDS);
        let missing = temp.path().join("missing-artifacts");
        fs::create_dir(&missing).expect("missing cache");
        *effects.cache.borrow_mut() = CacheLookup::Found(missing);
        ok!(pause_load_with(&args(&design), &effects));
        let valid = cache(temp.path(), "valid", VALID_MANIFEST);
        fs::create_dir_all(valid.join(".completed")).expect("completed");
        put(&valid, ".completed/step-5b", "");
        *effects.cache.borrow_mut() = CacheLookup::Found(valid);
        set_marker(
            &effects,
            "ISSUE_NUMBER=42\nREPO=owner/repo\nRUN_ID=run-42\nSTEP=5c\n",
        );
        effects.marker_ok.set(false);
        ok!(pause_load_with(&args(&design), &effects));
        assert!(design.join(".completed/step-5b").is_file());
        let source = temp.path().join("unsafe-source");
        let stage = temp.path().join("stage");
        fs::create_dir(&source).expect("source");
        fs::create_dir(&stage).expect("stage");
        put(&source, run_lifecycle::ARCHIVE_MANIFEST_NAME, "");
        #[cfg(unix)]
        std::os::unix::fs::symlink(temp.path().join("outside"), source.join("z-link"))
            .expect("symlink");
        let stage_root = TemporaryRoot::resolve(Some(&stage)).expect("stage root");
        assert!(copy_snapshot_to_stage(&source, &stage_root).is_err());
        assert!(sorted_entries(&temp.path().join("absent")).is_err());
    }

    #[test]
    fn manifest_and_live_read_helpers_cover_legacy_shapes() {
        let temp = tempfile::tempdir().expect("fixture");
        let manifest = temp.path().join("manifest.json");
        put(temp.path(), "manifest.json", r#"{"other":"value"}"#);
        assert!(manifest_matches(&manifest, "42", "run-42"));
        let design = temp.path().join("design");
        fs::create_dir(&design).expect("design");
        let live = LiveEffects;
        assert_eq!(live.resolve_repo("", "c/d"), "c/d");
        assert!(!live.resolve_repo("", "").is_empty());
        let request = PauseRequest {
            design_tmpdir: design.clone(),
            issue: "42".into(),
            repo: "owner/repo".into(),
        };
        let admission = live.storage_admission(&request, "run-42");
        assert_eq!(admission, StorageAdmission::LifecycleUnavailable);
        write_source(&design, temp.path(), "run-42");
        let admission = live.storage_admission(&request, "run-42");
        assert_eq!(admission, StorageAdmission::NotGitWorktree);
    }
}
