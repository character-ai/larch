//! Filesystem and object-store adapter for the shared run lifecycle.

use std::{
    collections::{BTreeMap, HashMap},
    fmt::Write as _,
    fs::{self, File, OpenOptions},
    io::{Read as _, Write as _},
    path::{Path, PathBuf},
    sync::LazyLock,
};

use chrono::{SecondsFormat, Utc};
use flate2::{Compression, GzBuilder, read::GzDecoder};
use larch_core::{
    LIFECYCLE_CONTEXT_BASENAME, LIFECYCLE_SCHEMA_VERSION, LifecycleContext, LifecycleError,
    LifecycleOutcome, ManifestDocument, ManifestUpdate, ManifestV2Seed, ObjectStore,
    ObjectStoreError, RunLogLayout, RunLogSlug, RunLogStorageMode, RunLogStorageResolution,
    ToolRepositoryStorage, UNIVERSAL_EXECUTION_ISSUES, UNIVERSAL_FINAL_REPORT,
    UNIVERSAL_SESSION_TRANSCRIPT, redact, validate_run_log_slug,
};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value, json};
use sha2::{Digest, Sha256};
use unicase::UniCase;
use unicode_normalization::UnicodeNormalization as _;
use uuid::Uuid;

use regex::Regex;

use crate::{
    PathIntent, TemporaryRoot, atomic_write_bytes, ensure_directory_chain,
    run_log_manifest::ManifestStore,
};

const ARCHIVE_MANIFEST_NAME: &str = "archive-manifest.json";
const PENDING_ARCHIVE_NAME: &str = "archive.tar.gz";
const PENDING_METADATA_NAME: &str = "retry.json";
const ARCHIVE_MAX_MEMBERS: usize = 10_000;
const ARCHIVE_MAX_MEMBER_BYTES: u64 = 256 * 1024 * 1024;
const ARCHIVE_MAX_EXPANDED_BYTES: u64 = 1024 * 1024 * 1024;

static QUIET_LOG_NAME: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^larch-quiet-[A-Za-z0-9._-]+-[0-9]+\.log$")
        .expect("quiet-log filename regex is valid")
});

/// Explicit XDG roots used by one lifecycle invocation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LifecycleHomes {
    pub state: PathBuf,
    pub cache: PathBuf,
}

impl LifecycleHomes {
    /// Resolve absolute XDG roots from one environment snapshot.
    ///
    /// # Errors
    /// Returns a lifecycle error for a relative configured root or missing home fallback.
    pub fn from_environment(environment: &HashMap<String, String>) -> Result<Self, LifecycleError> {
        let home = environment
            .get("HOME")
            .filter(|value| !value.is_empty())
            .map(PathBuf::from);
        let state = configured_home(environment, "XDG_STATE_HOME")
            .or_else(|| home.as_ref().map(|value| value.join(".local/state")))
            .ok_or_else(|| LifecycleError::new("HOME is required to resolve lifecycle state"))?;
        let cache = configured_home(environment, "XDG_CACHE_HOME")
            .or_else(|| home.as_ref().map(|value| value.join(".cache")))
            .ok_or_else(|| LifecycleError::new("HOME is required to resolve lifecycle cache"))?;
        if !state.is_absolute() {
            return Err(LifecycleError::new(
                "XDG_STATE_HOME must be an absolute path",
            ));
        }
        if !cache.is_absolute() {
            return Err(LifecycleError::new(
                "XDG_CACHE_HOME must be an absolute path",
            ));
        }
        Ok(Self {
            state: normalize_absolute(&state)?,
            cache: normalize_absolute(&cache)?,
        })
    }
}

fn configured_home(environment: &HashMap<String, String>, key: &str) -> Option<PathBuf> {
    environment
        .get(key)
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

/// Inputs for lifecycle start after repository and storage admission.
pub struct StartRequest<'a> {
    pub repo_root: &'a Path,
    pub resolution: &'a RunLogStorageResolution,
    pub local_resolution: &'a RunLogStorageResolution,
    pub homes: &'a LifecycleHomes,
    pub environment: &'a HashMap<String, String>,
    pub skill: &'a str,
    pub run_id: Option<&'a str>,
    pub log_root: Option<&'a Path>,
    pub parent_skill: &'a str,
    pub parent_run_id: &'a str,
    pub parent_context: Option<&'a Path>,
    pub issue: &'a str,
    pub adopt_existing: bool,
}

/// Validated, persisted state for one admitted run.
#[derive(Clone, Debug)]
pub struct StartedRun {
    pub context: LifecycleContext,
    pub context_file: PathBuf,
    pub resolution: RunLogStorageResolution,
}

/// Inputs for one terminal lifecycle transition.
pub struct FinishRequest<'a> {
    pub repo_root: &'a Path,
    pub active_resolution: &'a RunLogStorageResolution,
    pub local_resolution: &'a RunLogStorageResolution,
    pub homes: &'a LifecycleHomes,
    pub environment: &'a HashMap<String, String>,
    pub skill: &'a str,
    pub run_id: &'a str,
    pub outcome: LifecycleOutcome,
    pub pre_scrub_violations: u64,
}

/// Verified immutable publication postconditions.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PublicationResult {
    pub remote_key: String,
    pub archive_sha256: String,
    pub cache_dir: PathBuf,
}

/// Completed terminal transition and its pinned storage state.
#[derive(Clone, Debug)]
pub struct TerminalResult {
    pub outcome: LifecycleOutcome,
    pub resolution: RunLogStorageResolution,
    pub publication: Option<PublicationResult>,
    pub secret_scrub_violations: u64,
    pub files_scrubbed: u64,
    pub breadcrumb_warning: Option<String>,
}

/// Start or idempotently adopt one lifecycle run.
///
/// # Errors
/// Returns a lifecycle error before exposing a partial success envelope.
pub fn start(request: &StartRequest<'_>) -> Result<StartedRun, LifecycleError> {
    validate_identity(request.skill, request.run_id.unwrap_or("generated"))?;
    let parent = resolve_parent(request)?;
    let run_id = request
        .run_id
        .map_or_else(|| Uuid::new_v4().to_string(), str::to_owned);
    validate_identity(request.skill, &run_id)?;
    if !request.issue.is_empty() && !request.issue.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(LifecycleError::new(format!(
            "invalid issue: {}",
            request.issue
        )));
    }
    if request.adopt_existing
        && has_persisted_context(
            request.homes,
            request.resolution,
            request.local_resolution,
            request.skill,
            &run_id,
        )?
    {
        let existing = load(
            request.repo_root,
            request.skill,
            &run_id,
            request.resolution,
            request.local_resolution,
            request.homes,
        )?;
        if let Some(requested) = request.log_root
            && (!requested.is_absolute()
                || normalize_absolute(requested)? != existing.context.log_root)
        {
            return Err(LifecycleError::new(
                "existing lifecycle context does not match requested log root",
            ));
        }
        prepare_manifest(
            request,
            &existing.context,
            parent.as_ref(),
            &existing.resolution,
            true,
        )?;
        ensure_execution_issues(&existing.context)?;
        return Ok(existing);
    }
    let selected_log_root = request.log_root.map_or_else(
        || lifecycle_root(request.homes, request.resolution).join("staging"),
        Path::to_path_buf,
    );
    if !selected_log_root.is_absolute() {
        return Err(LifecycleError::new("lifecycle log root must be absolute"));
    }
    let log_root = normalize_absolute(&selected_log_root)?;
    let context = LifecycleContext::new(
        request.repo_root.to_path_buf(),
        request.resolution,
        request.skill.to_owned(),
        run_id,
        log_root,
    );
    prepare_manifest(request, &context, parent.as_ref(), request.resolution, true)?;
    ensure_execution_issues(&context)?;
    let context_file = context_path(
        request.homes,
        request.resolution,
        request.skill,
        &context.run_id,
    );
    if context_file.is_file() {
        let existing = load(
            request.repo_root,
            request.skill,
            &context.run_id,
            request.resolution,
            request.local_resolution,
            request.homes,
        )?;
        if existing.context != context {
            return Err(LifecycleError::new(
                "existing lifecycle context does not match adoption",
            ));
        }
    } else {
        let text = context_json(&context)?;
        atomic_write(&context_file, &text, 0o600)?;
    }
    Ok(StartedRun {
        context,
        context_file,
        resolution: request.resolution.clone(),
    })
}

fn ensure_execution_issues(context: &LifecycleContext) -> Result<(), LifecycleError> {
    let issues = context.run_dir.join(UNIVERSAL_EXECUTION_ISSUES);
    if !safe_regular_file(&issues)? {
        atomic_write(&issues, b"", 0o600)?;
    }
    Ok(())
}

fn resolve_parent(request: &StartRequest<'_>) -> Result<Option<(String, String)>, LifecycleError> {
    let parent = explicit_parent(request.parent_skill, request.parent_run_id)?;
    let Some(parent_context) = request.parent_context else {
        return Ok(parent);
    };
    if parent.is_some() {
        return Err(LifecycleError::new(
            "parent context cannot be combined with explicit parent identity",
        ));
    }
    if !parent_context.is_absolute() || !safe_regular_file(parent_context)? {
        return Err(LifecycleError::new(
            "parent lifecycle context is missing or unsafe",
        ));
    }
    let raw = read_context(parent_context)?;
    let loaded = load(
        request.repo_root,
        &raw.skill,
        &raw.run_id,
        request.resolution,
        request.local_resolution,
        request.homes,
    )?;
    if loaded.context_file != parent_context {
        return Err(LifecycleError::new(
            "parent lifecycle context path mismatch",
        ));
    }
    Ok(Some((raw.skill, raw.run_id)))
}

fn prepare_manifest(
    request: &StartRequest<'_>,
    context: &LifecycleContext,
    parent: Option<&(String, String)>,
    resolution: &RunLogStorageResolution,
    validate_parent: bool,
) -> Result<(), LifecycleError> {
    ensure_safe_directory(&context.run_dir)?;
    let path = context.run_dir.join("manifest.json");
    let existed = safe_regular_file(&path)?;
    if existed && !request.adopt_existing {
        return Err(LifecycleError::new(format!(
            "run ID already exists: {}",
            context.run_id
        )));
    }
    if !existed {
        let manifest = initial_manifest(request, context, parent, resolution)?;
        atomic_write(&path, manifest.canonical_json().as_bytes(), 0o600)?;
        return Ok(());
    }
    let manifest = read_json_object(&path, "lifecycle manifest")?;
    validate_manifest_identity(&manifest, context)?;
    if validate_parent {
        validate_manifest_parent(&manifest, parent)?;
    }
    let needs_lifecycle_fields = manifest.get("lifecycle_schema_version").is_none();
    if needs_lifecycle_fields {
        update_manifest(context, &lifecycle_manifest_updates(resolution), &now())?;
    } else if manifest.get("lifecycle_schema_version") != Some(&json!(LIFECYCLE_SCHEMA_VERSION))
        || !manifest_matches_resolution(&manifest, resolution)
    {
        return Err(LifecycleError::new(
            "run-log publication or repository identity changed after lifecycle start",
        ));
    }
    Ok(())
}

/// Report whether a safely-addressable context exists in either pinned namespace.
///
/// # Errors
/// Returns a lifecycle error for an unsafe context path.
pub fn has_persisted_context(
    homes: &LifecycleHomes,
    active_resolution: &RunLogStorageResolution,
    local_resolution: &RunLogStorageResolution,
    skill: &str,
    run_id: &str,
) -> Result<bool, LifecycleError> {
    validate_identity(skill, run_id)?;
    let local = context_path(homes, local_resolution, skill, run_id);
    if safe_regular_file(&local)? {
        return Ok(true);
    }
    let active = context_path(homes, active_resolution, skill, run_id);
    if active == local {
        return Ok(false);
    }
    safe_regular_file(&active)
}

/// Rehydrate one persisted lifecycle context without inherited shell state.
///
/// # Errors
/// Returns a lifecycle error for missing, unsafe, or drifted context.
pub fn load(
    repo_root: &Path,
    skill: &str,
    run_id: &str,
    active_resolution: &RunLogStorageResolution,
    local_resolution: &RunLogStorageResolution,
    homes: &LifecycleHomes,
) -> Result<StartedRun, LifecycleError> {
    validate_identity(skill, run_id)?;
    let disabled = context_path(homes, local_resolution, skill, run_id);
    let context_file = if safe_regular_file(&disabled)? {
        disabled
    } else {
        context_path(homes, active_resolution, skill, run_id)
    };
    if !safe_regular_file(&context_file)? {
        return Err(LifecycleError::new(format!(
            "lifecycle context is missing or unsafe: {}",
            context_file.display()
        )));
    }
    let context = read_context(&context_file)?;
    let resolution = context.validate(
        repo_root,
        skill,
        run_id,
        active_resolution,
        local_resolution,
    )?;
    Ok(StartedRun {
        context,
        context_file,
        resolution,
    })
}

/// Record a terminal outcome and publish through the injected object-store port.
///
/// # Errors
/// Returns a lifecycle error while retaining staging/context and durable pending state.
pub async fn finish(
    request: &FinishRequest<'_>,
    store: Option<&dyn ObjectStore>,
) -> Result<TerminalResult, LifecycleError> {
    let started = load(
        request.repo_root,
        request.skill,
        request.run_id,
        request.active_resolution,
        request.local_resolution,
        request.homes,
    )?;
    ensure_existing_safe_directory(&started.context.run_dir)?;
    let manifest_path = started.context.run_dir.join("manifest.json");
    let manifest = read_json_object(&manifest_path, "lifecycle manifest")?;
    validate_manifest_identity(&manifest, &started.context)?;
    if manifest.get("lifecycle_schema_version") != Some(&json!(LIFECYCLE_SCHEMA_VERSION)) {
        return Err(LifecycleError::new(
            "unsupported or missing lifecycle schema version",
        ));
    }
    if !manifest_matches_resolution(&manifest, &started.resolution) {
        return Err(LifecycleError::new(
            "run-log publication or repository identity changed after lifecycle start",
        ));
    }
    let finished_at = write_terminal_artifacts(&started.context, request.outcome, &manifest)?;
    update_manifest(
        &started.context,
        &[
            ("status".to_owned(), json!("done")),
            (
                "terminal_outcome".to_owned(),
                json!(request.outcome.as_str()),
            ),
            ("finished_at".to_owned(), json!(finished_at)),
        ],
        &now(),
    )?;
    if started.resolution.mode() == RunLogStorageMode::Disabled {
        remove_tree_strict(
            started
                .context_file
                .parent()
                .ok_or_else(|| LifecycleError::new("lifecycle context parent is missing"))?,
        )?;
        remove_tree_strict(&started.context.run_dir)?;
        return Ok(TerminalResult {
            outcome: request.outcome,
            resolution: started.resolution,
            publication: None,
            secret_scrub_violations: request.pre_scrub_violations,
            files_scrubbed: 0,
            breadcrumb_warning: None,
        });
    }
    verify_run_completeness(
        &started.context.run_dir,
        &started.context.skill,
        request.repo_root,
    )?;
    let storage = started
        .resolution
        .storage()
        .ok_or_else(|| LifecycleError::new("enabled lifecycle storage is missing"))?;
    let store = store.ok_or_else(|| LifecycleError::new("enabled object store is missing"))?;
    let breadcrumb_warning = publish_breadcrumbs(
        &started.context.log_root,
        &started.context.run_dir,
        request.environment,
    )
    .err()
    .map(|error| error.to_string());
    let (scrubbed, files_scrubbed) = scrub_tree(&started.context.run_dir)?;
    let secret_scrub_violations = request
        .pre_scrub_violations
        .checked_add(scrubbed)
        .ok_or_else(|| LifecycleError::new("secret scrub violation count overflowed"))?;
    let publication = publish(request.homes, storage, &started.context, store).await?;
    if let Some(parent) = started.context_file.parent() {
        let _ = fs::remove_dir_all(parent);
    }
    Ok(TerminalResult {
        outcome: request.outcome,
        resolution: started.resolution,
        publication: Some(publication),
        secret_scrub_violations,
        files_scrubbed,
        breadcrumb_warning,
    })
}

fn context_json(context: &LifecycleContext) -> Result<Vec<u8>, LifecycleError> {
    let mut values = BTreeMap::new();
    values.insert("client_repo", json!(context.client_repo));
    values.insert("local_namespace_id", json!(context.local_namespace_id));
    values.insert("log_root", json!(context.log_root));
    values.insert("publication_mode", json!(context.publication_mode));
    values.insert("repo_root", json!(context.repo_root));
    values.insert("run_dir", json!(context.run_dir));
    values.insert("run_id", json!(context.run_id));
    values.insert("schema_version", json!(context.schema_version));
    values.insert("skill", json!(context.skill));
    values.insert("storage_base_uri", json!(context.storage_base_uri));
    values.insert("storage_origin_id", json!(context.storage_origin_id));
    values.insert(
        "storage_resolution_reason",
        json!(context.storage_resolution_reason),
    );
    values.insert("tool_repo_uri", json!(context.tool_repo_uri));
    let encoded =
        serde_json::to_string(&values).map_err(|error| LifecycleError::new(error.to_string()))?;
    let mut ascii = String::with_capacity(encoded.len() + 1);
    for character in encoded.chars() {
        if character.is_ascii() {
            ascii.push(character);
        } else {
            let codepoint = character as u32;
            if codepoint <= 0xffff {
                let _ = write!(ascii, "\\u{codepoint:04x}");
            } else {
                let adjusted = codepoint - 0x1_0000;
                let high = 0xd800 + (adjusted >> 10);
                let low = 0xdc00 + (adjusted & 0x3ff);
                let _ = write!(ascii, "\\u{high:04x}\\u{low:04x}");
            }
        }
    }
    ascii.push('\n');
    Ok(ascii.into_bytes())
}

fn validate_identity(skill: &str, run_id: &str) -> Result<(), LifecycleError> {
    if !validate_run_log_slug(skill) {
        return Err(LifecycleError::new(format!("invalid skill: {skill:?}")));
    }
    if run_id != "generated" && !validate_run_log_slug(run_id) {
        return Err(LifecycleError::new(format!("invalid run-id: {run_id:?}")));
    }
    Ok(())
}

fn explicit_parent(skill: &str, run_id: &str) -> Result<Option<(String, String)>, LifecycleError> {
    if skill.is_empty() != run_id.is_empty() {
        return Err(LifecycleError::new(
            "--parent-skill and --parent-run-id must be provided together",
        ));
    }
    if skill.is_empty() {
        return Ok(None);
    }
    validate_identity(skill, run_id)?;
    Ok(Some((skill.to_owned(), run_id.to_owned())))
}

fn lifecycle_root(homes: &LifecycleHomes, resolution: &RunLogStorageResolution) -> PathBuf {
    let (kind, identity) = resolution.storage().map_or_else(
        || {
            (
                "local-repositories",
                resolution
                    .local_namespace_id()
                    .unwrap_or_default()
                    .to_owned(),
            )
        },
        |storage| ("storage-origins", storage.storage_origin_id()),
    );
    homes
        .state
        .join("larch/run-lifecycle/v3")
        .join(resolution.client_repo())
        .join(kind)
        .join(identity)
}

fn context_path(
    homes: &LifecycleHomes,
    resolution: &RunLogStorageResolution,
    skill: &str,
    run_id: &str,
) -> PathBuf {
    lifecycle_root(homes, resolution)
        .join("contexts")
        .join(skill)
        .join(run_id)
        .join(LIFECYCLE_CONTEXT_BASENAME)
}

fn initial_manifest(
    request: &StartRequest<'_>,
    context: &LifecycleContext,
    parent: Option<&(String, String)>,
    resolution: &RunLogStorageResolution,
) -> Result<ManifestDocument, LifecycleError> {
    let timestamp = now();
    let issue = if request.issue.is_empty() {
        Value::Null
    } else {
        json!(
            request
                .issue
                .parse::<u64>()
                .map_err(|error| LifecycleError::new(error.to_string()))?
        )
    };
    let model = request
        .environment
        .get("CLAUDE_CODE_MODEL")
        .filter(|value| !value.is_empty())
        .or_else(|| {
            request
                .environment
                .get("CLAUDE_MODEL")
                .filter(|value| !value.is_empty())
        })
        .cloned()
        .or_else(|| transcript_main_model(request.repo_root, request.environment))
        .unwrap_or_else(|| "unknown".to_owned());
    let effort = request
        .environment
        .get("CLAUDE_CODE_EFFORT_LEVEL")
        .filter(|value| !value.is_empty())
        .or_else(|| request.environment.get("CLAUDE_EFFORT"))
        .map_or("unknown", String::as_str);
    let mut extra: BTreeMap<String, Value> =
        lifecycle_manifest_updates(resolution).into_iter().collect();
    extra.insert(
        "parent_run_id".to_owned(),
        parent.map_or(Value::Null, |value| json!(value.1)),
    );
    extra.insert(
        "parent_skill".to_owned(),
        parent.map_or(Value::Null, |value| json!(value.0)),
    );
    extra.insert("issue_number".to_owned(), issue);
    ManifestDocument::synthesize_v2(ManifestV2Seed {
        skill: context.skill.clone(),
        run_id: context.run_id.clone(),
        timestamp,
        larch_version: env!("CARGO_PKG_VERSION").to_owned(),
        main_model: model,
        effort: effort.to_owned(),
        steps_ran: BTreeMap::new(),
        extra,
    })
    .map_err(|error| LifecycleError::new(error.to_string()))
}

fn transcript_main_model(
    repo_root: &Path,
    environment: &HashMap<String, String>,
) -> Option<String> {
    let home = environment.get("HOME").filter(|value| !value.is_empty())?;
    let repo_root = fs::canonicalize(repo_root).ok()?;
    let project_key = repo_root.to_str()?.replace('/', "-");
    let project_dir = Path::new(home).join(".claude/projects").join(project_key);
    if !project_dir.is_dir() {
        return None;
    }
    let requested = ["LARCH_CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID"]
        .iter()
        .filter_map(|key| environment.get(*key))
        .find(|value| valid_claude_session_id(value));
    let transcript = if let Some(session_id) = requested {
        let candidate = project_dir.join(format!("{session_id}.jsonl"));
        candidate.is_file().then_some(candidate)
    } else {
        sorted_entries(&project_dir)
            .ok()?
            .into_iter()
            .filter(|entry| {
                entry
                    .path()
                    .extension()
                    .is_some_and(|value| value == "jsonl")
            })
            .filter_map(|entry| {
                let path = entry.path();
                let modified = entry.metadata().ok()?.modified().ok()?;
                path.is_file().then_some((modified, path))
            })
            .max_by_key(|(modified, _)| *modified)
            .map(|(_, path)| path)
    }?;
    let bytes = fs::read(transcript).ok()?;
    for line in String::from_utf8_lossy(&bytes).lines() {
        if !line.contains("\"assistant\"") {
            continue;
        }
        let Ok(value) = serde_json::from_str::<Value>(line) else {
            continue;
        };
        if value.get("type") != Some(&json!("assistant")) {
            continue;
        }
        if let Some(model) = value
            .get("message")
            .and_then(|message| message.get("model"))
            .and_then(Value::as_str)
            .filter(|model| !model.is_empty())
        {
            return Some(model.to_owned());
        }
    }
    None
}

fn valid_claude_session_id(value: &str) -> bool {
    (1..=128).contains(&value.len())
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-'))
}

fn lifecycle_manifest_updates(resolution: &RunLogStorageResolution) -> Vec<ManifestUpdate> {
    let storage = resolution.storage();
    vec![
        ("status".to_owned(), json!("in-progress")),
        (
            "lifecycle_schema_version".to_owned(),
            json!(LIFECYCLE_SCHEMA_VERSION),
        ),
        (
            "publication_mode".to_owned(),
            json!(resolution.mode().as_str()),
        ),
        (
            "storage_resolution_reason".to_owned(),
            json!(resolution.reason().as_str()),
        ),
        (
            "storage_base_uri".to_owned(),
            storage.map_or(Value::Null, |value| json!(value.base.uri())),
        ),
        ("client_repo".to_owned(), json!(resolution.client_repo())),
        (
            "tool_repo_uri".to_owned(),
            storage.map_or(Value::Null, |value| json!(value.uri())),
        ),
        (
            "storage_origin_id".to_owned(),
            storage.map_or(Value::Null, |value| json!(value.storage_origin_id())),
        ),
        (
            "local_namespace_id".to_owned(),
            resolution
                .local_namespace_id()
                .map_or(Value::Null, |value| json!(value)),
        ),
        ("terminal_outcome".to_owned(), Value::Null),
        ("finished_at".to_owned(), Value::Null),
    ]
}

fn update_manifest(
    context: &LifecycleContext,
    updates: &[ManifestUpdate],
    updated_at: &str,
) -> Result<(), LifecycleError> {
    let skill = RunLogSlug::parse(&context.skill)
        .map_err(|error| LifecycleError::new(error.to_string()))?;
    let run_id = RunLogSlug::parse(&context.run_id)
        .map_err(|error| LifecycleError::new(error.to_string()))?;
    let layout = RunLogLayout::new(&context.log_root, skill, run_id);
    let store = ManifestStore::open(&context.log_root)
        .map_err(|error| LifecycleError::new(error.to_string()))?;
    store
        .update(&layout, updates, updated_at)
        .map(|_path| ())
        .map_err(|error| LifecycleError::new(error.to_string()))
}

fn validate_manifest_identity(
    manifest: &Map<String, Value>,
    context: &LifecycleContext,
) -> Result<(), LifecycleError> {
    if manifest.get("schema_version") != Some(&json!(2))
        || manifest.get("skill") != Some(&json!(context.skill))
        || manifest.get("run_id") != Some(&json!(context.run_id))
    {
        return Err(LifecycleError::new("lifecycle manifest identity mismatch"));
    }
    Ok(())
}

fn validate_manifest_parent(
    manifest: &Map<String, Value>,
    expected: Option<&(String, String)>,
) -> Result<(), LifecycleError> {
    let matches = expected.map_or_else(
        || {
            manifest.get("parent_skill").is_none_or(Value::is_null)
                && manifest.get("parent_run_id").is_none_or(Value::is_null)
        },
        |parent| {
            manifest.get("parent_skill") == Some(&json!(parent.0))
                && manifest.get("parent_run_id") == Some(&json!(parent.1))
        },
    );
    if !matches {
        return Err(LifecycleError::new(
            "existing lifecycle parent identity mismatch",
        ));
    }
    Ok(())
}

fn manifest_matches_resolution(
    manifest: &Map<String, Value>,
    resolution: &RunLogStorageResolution,
) -> bool {
    let storage = resolution.storage();
    manifest.get("publication_mode") == Some(&json!(resolution.mode().as_str()))
        && manifest.get("storage_resolution_reason") == Some(&json!(resolution.reason().as_str()))
        && manifest.get("client_repo") == Some(&json!(resolution.client_repo()))
        && manifest.get("storage_base_uri")
            == Some(&storage.map_or(Value::Null, |value| json!(value.base.uri())))
        && manifest.get("tool_repo_uri")
            == Some(&storage.map_or(Value::Null, |value| json!(value.uri())))
        && manifest.get("storage_origin_id")
            == Some(&storage.map_or(Value::Null, |value| json!(value.storage_origin_id())))
        && manifest.get("local_namespace_id")
            == Some(
                &resolution
                    .local_namespace_id()
                    .map_or(Value::Null, |value| json!(value)),
            )
}

fn write_terminal_artifacts(
    context: &LifecycleContext,
    outcome: LifecycleOutcome,
    manifest: &Map<String, Value>,
) -> Result<String, LifecycleError> {
    if let Some(existing) = manifest
        .get("terminal_outcome")
        .filter(|value| !value.is_null())
        && existing != &json!(outcome.as_str())
    {
        return Err(LifecycleError::new(format!(
            "run already recorded terminal outcome {existing:?}, not {:?}",
            outcome.as_str()
        )));
    }
    let report = format!(
        "# Skill run final report\n\n- Skill: `{}`\n- Run ID: `{}`\n- Outcome: `{}`\n",
        context.skill,
        context.run_id,
        outcome.as_str(),
    );
    let report_path = context.run_dir.join(UNIVERSAL_FINAL_REPORT);
    if report_path.is_file() && fs::read_to_string(&report_path).unwrap_or_default() != report {
        return Err(LifecycleError::new(
            "existing universal final report does not match terminal outcome",
        ));
    }
    atomic_write(&report_path, report.as_bytes(), 0o600)?;
    if !context.run_dir.join(UNIVERSAL_SESSION_TRANSCRIPT).is_file() {
        let issue = serde_json::to_string(&json!({
            "body": format!(
                "{UNIVERSAL_SESSION_TRANSCRIPT} was unavailable for {} run {}; the universal final report and lifecycle metadata were preserved.",
                context.skill, context.run_id
            ),
            "category": "Warnings",
            "phase": "terminal",
            "step": "run-lifecycle",
        }))
        .map_err(|error| LifecycleError::new(error.to_string()))?
            + "\n";
        let issues_path = context.run_dir.join(UNIVERSAL_EXECUTION_ISSUES);
        let mut issues = fs::read_to_string(&issues_path).unwrap_or_default();
        if !issues.contains(&issue) {
            issues.push_str(&issue);
            atomic_write(&issues_path, issues.as_bytes(), 0o600)?;
        }
    }
    match manifest.get("finished_at") {
        Some(Value::String(value)) if !value.is_empty() => Ok(value.clone()),
        None | Some(Value::Null | Value::String(_)) => Ok(now_precise()),
        Some(_) => Err(LifecycleError::new(
            "lifecycle manifest finished_at is invalid",
        )),
    }
}

struct RequiredArtifact {
    slug: String,
    relative_path: String,
}

impl RequiredArtifact {
    fn new(slug: impl Into<String>, relative_path: impl Into<String>) -> Self {
        Self {
            slug: slug.into(),
            relative_path: relative_path.into(),
        }
    }
}

fn verify_run_completeness(
    run_dir: &Path,
    skill: &str,
    repo_root: &Path,
) -> Result<(), LifecycleError> {
    let manifest = read_json_object(&run_dir.join("manifest.json"), "lifecycle manifest")?;
    let mut required = vec![
        RequiredArtifact::new("final-report", UNIVERSAL_FINAL_REPORT),
        RequiredArtifact::new("session-transcript", UNIVERSAL_SESSION_TRANSCRIPT),
    ];
    match skill {
        "implement" => required.extend(required_implement_artifacts(run_dir, &manifest)),
        "design" => required.extend(required_design_artifacts(run_dir, repo_root)?),
        _ => {}
    }
    let issues = committed_issues(run_dir)?;
    let missing: Vec<_> = required
        .iter()
        .filter(|artifact| !artifact_present_or_waived(run_dir, artifact, &issues))
        .map(|artifact| format!("{}:{}", artifact.slug, artifact.relative_path))
        .collect();
    if missing.is_empty() {
        Ok(())
    } else {
        Err(LifecycleError::new(format!(
            "run-log incomplete: {}",
            missing.join(", ")
        )))
    }
}

fn required_implement_artifacts(
    run_dir: &Path,
    manifest: &Map<String, Value>,
) -> Vec<RequiredArtifact> {
    let mut required = Vec::new();
    if manifest
        .get("steps_ran")
        .and_then(Value::as_object)
        .and_then(|steps| steps.get("step18"))
        == Some(&Value::Bool(true))
    {
        required.extend([
            RequiredArtifact::new("final-summary", "final-summary.md"),
            RequiredArtifact::new("token-report", "token-report.json"),
            RequiredArtifact::new("timing-report", "timing-report.json"),
            RequiredArtifact::new("execution-issues", UNIVERSAL_EXECUTION_ISSUES),
            RequiredArtifact::new("session-transcript", UNIVERSAL_SESSION_TRANSCRIPT),
        ]);
    }
    if run_dir.join("code-review-tally.json").is_file() {
        required.push(RequiredArtifact::new(
            "review-findings-full",
            "review-findings-full.jsonl",
        ));
    }
    required
}

fn required_design_artifacts(
    run_dir: &Path,
    repo_root: &Path,
) -> Result<Vec<RequiredArtifact>, LifecycleError> {
    let mut required = Vec::new();
    let publish_reached = run_dir.join("final-summary.md").is_file()
        || run_dir.join("version-bump-reasoning.md").is_file();
    if publish_reached {
        required.push(RequiredArtifact::new("final-summary", "final-summary.md"));
    }
    if publish_reached || run_dir.join(UNIVERSAL_SESSION_TRANSCRIPT).is_file() {
        required.push(RequiredArtifact::new(
            "session-transcript",
            UNIVERSAL_SESSION_TRANSCRIPT,
        ));
    }
    let review_root = run_dir.join("plan-review");
    if review_root.is_dir() {
        for entry in sorted_entries(&review_root)? {
            let name = entry.file_name().to_string_lossy().into_owned();
            if name.starts_with("round-") && entry.path().is_dir() {
                required.push(RequiredArtifact::new(
                    format!("plan-review-{name}"),
                    format!("plan-review/{name}/findings-classification.tsv"),
                ));
            }
        }
    }
    if design_approved(run_dir) {
        let invariants = repo_root.join("ARCHITECTURAL_INVARIANTS.md");
        if readable_architecture_file(&invariants)
            .as_deref()
            .is_some_and(has_invariant_entry)
        {
            required.push(RequiredArtifact::new(
                "invariant-assessment",
                "architectural-invariant-assessment.md",
            ));
        }
        if readable_architecture_file(&repo_root.join("ARCHITECTURAL_GUIDELINES.md")).is_some() {
            required.push(RequiredArtifact::new(
                "guideline-assessment",
                "architectural-guideline-assessment.md",
            ));
        }
    }
    Ok(required)
}

fn readable_architecture_file(path: &Path) -> Option<String> {
    let metadata = fs::symlink_metadata(path).ok()?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return None;
    }
    fs::read_to_string(path).ok()
}

fn has_invariant_entry(contents: &str) -> bool {
    static HEADING: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"^#{1,6}\s+I-[A-Za-z0-9-]+-[0-9]+:\s*\S")
            .expect("invariant-heading regex is valid")
    });
    let mut fence = None;
    for line in contents.lines() {
        let trimmed = line.trim_start();
        let marker = if trimmed.starts_with("```") {
            Some('`')
        } else if trimmed.starts_with("~~~") {
            Some('~')
        } else {
            None
        };
        if let Some(marker) = marker {
            if fence == Some(marker) {
                fence = None;
            } else if fence.is_none() {
                fence = Some(marker);
            }
            continue;
        }
        if fence.is_none() && HEADING.is_match(line) {
            return true;
        }
    }
    false
}

fn design_approved(run_dir: &Path) -> bool {
    fs::read_to_string(run_dir.join("final-summary.md"))
        .unwrap_or_default()
        .lines()
        .filter_map(|line| line.strip_prefix("## /design run "))
        .filter_map(|line| line.rsplit_once(':').map(|(_, outcome)| outcome.trim()))
        .any(|outcome| matches!(outcome, "approved" | "approved-partition"))
}

fn committed_issues(run_dir: &Path) -> Result<Vec<(String, String)>, LifecycleError> {
    let text = fs::read_to_string(run_dir.join(UNIVERSAL_EXECUTION_ISSUES)).map_err(io_error)?;
    let mut issues = Vec::new();
    for line in text.lines().filter(|line| !line.trim().is_empty()) {
        let Ok(Value::Object(row)) = serde_json::from_str::<Value>(line) else {
            continue;
        };
        if let (Some(category), Some(body)) = (
            row.get("category").and_then(Value::as_str),
            row.get("body").and_then(Value::as_str),
        ) {
            issues.push((category.to_owned(), body.to_owned()));
        }
    }
    Ok(issues)
}

fn artifact_present_or_waived(
    run_dir: &Path,
    artifact: &RequiredArtifact,
    issues: &[(String, String)],
) -> bool {
    if run_dir.join(&artifact.relative_path).is_file() {
        return true;
    }
    let mut tokens = vec![
        artifact.relative_path.to_lowercase(),
        artifact.slug.to_lowercase(),
    ];
    if !artifact.relative_path.contains("plan-review/round-")
        && let Some(name) = Path::new(&artifact.relative_path).file_name()
    {
        tokens.push(name.to_string_lossy().to_lowercase());
    }
    issues.iter().any(|(category, body)| {
        matches!(
            category.as_str(),
            "Pre-existing Code Issues"
                | "Tool Failures"
                | "Permission Prompts"
                | "External Reviewer Issues"
                | "CI Issues"
                | "Warnings"
                | "Q/A"
        ) && tokens
            .iter()
            .any(|token| body.to_lowercase().contains(token))
    })
}

fn publish_breadcrumbs(
    log_root: &Path,
    run_dir: &Path,
    environment: &HashMap<String, String>,
) -> Result<(), LifecycleError> {
    if log_root.file_name().and_then(|value| value.to_str()) != Some("larch-logs") {
        return Ok(());
    }
    let Some(source) = log_root.parent() else {
        return Ok(());
    };
    if !source.is_dir() || !breadcrumb_source_confined(source, environment)? {
        return Ok(());
    }
    let mut output = String::new();
    for entry in sorted_entries(source)? {
        let name = entry.file_name().to_string_lossy().into_owned();
        if !QUIET_LOG_NAME.is_match(&name) {
            continue;
        }
        let metadata = fs::symlink_metadata(entry.path()).map_err(io_error)?;
        if metadata.file_type().is_symlink() {
            return Err(LifecycleError::new(format!(
                "refusing unsafe quiet log: {}",
                entry.path().display()
            )));
        }
        if !metadata.is_file() {
            continue;
        }
        reject_hardlink(&metadata, &entry.path())?;
        let (bytes, _) = read_stable_regular_file(&entry.path())?;
        let contents = String::from_utf8_lossy(&bytes);
        let _ = writeln!(output, "=== {name} ===");
        let redacted = redact(&contents);
        output.push_str(redacted.text());
        if !redacted.text().is_empty() && !redacted.text().ends_with('\n') {
            output.push('\n');
        }
    }
    if !output.is_empty() {
        replace_breadcrumbs(run_dir, output.as_bytes())?;
    }
    Ok(())
}

fn replace_breadcrumbs(run_dir: &Path, contents: &[u8]) -> Result<(), LifecycleError> {
    let destination = run_dir.join("breadcrumbs");
    let parent = run_dir
        .parent()
        .ok_or_else(|| LifecycleError::new("run directory has no parent"))?;
    let run_name = run_dir
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or_else(|| LifecycleError::new("run directory name is not valid UTF-8"))?;
    let staged = parent.join(format!(
        ".{run_name}.breadcrumbs.{}-{}",
        std::process::id(),
        Uuid::new_v4()
    ));
    let backup = parent.join(format!(".{run_name}.breadcrumbs.removing"));
    let result = (|| {
        ensure_safe_directory(&staged)?;
        atomic_write(&staged.join("quiet.log"), contents, 0o600)?;
        if destination
            .symlink_metadata()
            .is_ok_and(|metadata| metadata.file_type().is_symlink() || !metadata.is_dir())
        {
            return Err(LifecycleError::new(
                "refusing to replace unsafe breadcrumbs destination",
            ));
        }
        if backup.exists() {
            if destination.exists() {
                remove_tree_strict(&backup)?;
            } else {
                fs::rename(&backup, &destination).map_err(io_error)?;
            }
        }
        let moved = destination.exists();
        if moved {
            fs::rename(&destination, &backup).map_err(io_error)?;
        }
        if let Err(error) = fs::rename(&staged, &destination) {
            if moved && !destination.exists() {
                let _ = fs::rename(&backup, &destination);
            }
            return Err(io_error(error));
        }
        sync_directory(parent)?;
        if backup.exists() {
            remove_tree_strict(&backup)?;
        }
        Ok(())
    })();
    if staged.exists() {
        let _ = fs::remove_dir_all(&staged);
    }
    result
}

fn breadcrumb_source_confined(
    source: &Path,
    environment: &HashMap<String, String>,
) -> Result<bool, LifecycleError> {
    let roots: Vec<PathBuf> = [
        "IMPLEMENT_TMPDIR",
        "DESIGN_TMPDIR",
        "REVIEW_TMPDIR",
        "RESEARCH_TMPDIR",
    ]
    .iter()
    .filter_map(|key| environment.get(*key))
    .filter(|value| !value.trim().is_empty())
    .map(|value| normalize_absolute(Path::new(value)))
    .collect::<Result<_, _>>()?;
    if roots.is_empty() {
        return Ok(true);
    }
    let source = normalize_absolute(source)?;
    Ok(roots.iter().any(|root| source.starts_with(root)))
}

fn scrub_tree(root: &Path) -> Result<(u64, u64), LifecycleError> {
    let mut violations = 0_u64;
    let mut files_scrubbed = 0_u64;
    for path in tree_files(root)? {
        let Ok((bytes, metadata)) = read_stable_regular_file(&path) else {
            continue;
        };
        let Ok(original) = String::from_utf8(bytes) else {
            continue;
        };
        let result = redact(&original);
        let discovered = u64::try_from(result.findings().values().sum::<usize>())
            .map_err(|_| LifecycleError::new("secret scrub violation count overflowed"))?;
        violations = violations
            .checked_add(discovered)
            .ok_or_else(|| LifecycleError::new("secret scrub violation count overflowed"))?;
        if result.text() != original {
            let verified = redact(result.text());
            if !verified.findings().is_empty() || verified.text() != result.text() {
                return Err(LifecycleError::new(format!(
                    "secret survived scrubbing in {}",
                    path.display()
                )));
            }
            atomic_write(
                &path,
                result.text().as_bytes(),
                normalized_mode_from_metadata(&metadata),
            )?;
            files_scrubbed = files_scrubbed
                .checked_add(1)
                .ok_or_else(|| LifecycleError::new("scrubbed file count overflowed"))?;
        }
    }
    Ok((violations, files_scrubbed))
}

async fn publish(
    homes: &LifecycleHomes,
    storage: &ToolRepositoryStorage,
    context: &LifecycleContext,
    store: &dyn ObjectStore,
) -> Result<PublicationResult, LifecycleError> {
    let paths = PublicationPaths::new(homes, storage, &context.skill, &context.run_id);
    let _lock = PublicationLock::acquire(&paths.lock_file)?;
    let retrying_pending = existing_safe_directory(&paths.pending_dir)?;
    let mut pending = if retrying_pending {
        load_pending(&paths, storage, context)?
    } else {
        create_pending(&paths, storage, context)?
    };
    pending.attempts = pending
        .attempts
        .checked_add(1)
        .ok_or_else(|| LifecycleError::new("publication attempt count overflowed"))?;
    pending.last_error.clear();
    write_pending(&paths, &pending)?;
    let object_key = format!("{}/{}", storage.prefix(), pending.remote_key);
    let upload = store
        .upload_create(storage.bucket(), &object_key, &paths.pending_archive)
        .await;
    let remote_verified = match upload {
        Ok(remote) if remote.key == object_key && remote.size == pending.archive_size => store
            .metadata(storage.bucket(), &object_key)
            .await
            .is_ok_and(|metadata| {
                metadata.key == object_key && metadata.size == pending.archive_size
            }),
        Ok(_) => false,
        Err(ObjectStoreError::AlreadyExists) => {
            remote_matches(store, storage.bucket(), &object_key, &paths, &pending)
                .await
                .unwrap_or(false)
        }
        Err(_) => return publication_failure(&paths, &mut pending, "object-transport"),
    };
    if !remote_verified {
        return publication_failure(&paths, &mut pending, "publication-invariant");
    }
    if publish_cache(
        &paths,
        (!retrying_pending).then_some(context.run_dir.as_path()),
        &context.skill,
        &context.run_id,
        &pending.manifest_sha256,
    )
    .is_err()
    {
        return publication_failure(&paths, &mut pending, "local-integrity");
    }
    let completed = paths.pending_dir.with_file_name(format!(
        ".{}.complete-{}-{}",
        paths
            .pending_dir
            .file_name()
            .and_then(|value| value.to_str())
            .unwrap_or("run"),
        std::process::id(),
        Uuid::new_v4()
    ));
    if fs::rename(&paths.pending_dir, &completed).is_err() {
        return publication_failure(&paths, &mut pending, "local-integrity");
    }
    if let Some(parent) = completed.parent()
        && sync_directory(parent).is_err()
    {
        return Err(LifecycleError::new("run-log archive publication failed"));
    }
    let _ = fs::remove_dir_all(completed);
    if ensure_existing_safe_directory(&context.run_dir).is_ok() {
        let _ = fs::remove_dir_all(&context.run_dir);
    }
    Ok(PublicationResult {
        remote_key: pending.remote_key,
        archive_sha256: pending.archive_sha256,
        cache_dir: paths.cache_dir,
    })
}

fn publication_failure<T>(
    paths: &PublicationPaths,
    pending: &mut PendingPublication,
    token: &str,
) -> Result<T, LifecycleError> {
    token.clone_into(&mut pending.last_error);
    write_pending(paths, pending)?;
    Err(LifecycleError::new("run-log archive publication failed"))
}

async fn remote_matches(
    store: &dyn ObjectStore,
    bucket: &str,
    key: &str,
    paths: &PublicationPaths,
    pending: &PendingPublication,
) -> Result<bool, LifecycleError> {
    let metadata = store
        .metadata(bucket, key)
        .await
        .map_err(|_| LifecycleError::new("immutable remote key metadata could not be verified"))?;
    if metadata.key != key || metadata.size != pending.archive_size {
        return Ok(false);
    }
    let downloaded = paths
        .pending_dir
        .join(format!(".remote-verify-{}", Uuid::new_v4()));
    if store.download(bucket, key, &downloaded).await.is_err() {
        let _ = fs::remove_file(&downloaded);
        return Err(LifecycleError::new(
            "immutable remote key could not be verified",
        ));
    }
    let digest = sha256_file(&downloaded);
    let _ = fs::remove_file(downloaded);
    Ok(digest? == (pending.archive_sha256.clone(), pending.archive_size))
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct PendingPublication {
    archive_sha256: String,
    archive_size: u64,
    attempts: u64,
    client_repo: String,
    last_error: String,
    manifest_sha256: String,
    remote_key: String,
    run_id: String,
    schema_version: u64,
    skill: String,
    storage_origin_id: String,
    tool_repo_uri: String,
}

struct PublicationPaths {
    pending_dir: PathBuf,
    pending_archive: PathBuf,
    pending_metadata: PathBuf,
    cache_dir: PathBuf,
    lock_file: PathBuf,
}

impl PublicationPaths {
    fn new(
        homes: &LifecycleHomes,
        storage: &ToolRepositoryStorage,
        skill: &str,
        run_id: &str,
    ) -> Self {
        let identity = storage.storage_origin_id();
        let pending_dir = homes
            .state
            .join("larch/run-log-pending/v2")
            .join(&storage.client_repo)
            .join(&identity)
            .join(skill)
            .join(run_id);
        Self {
            pending_archive: pending_dir.join(PENDING_ARCHIVE_NAME),
            pending_metadata: pending_dir.join(PENDING_METADATA_NAME),
            pending_dir,
            cache_dir: homes
                .cache
                .join("larch/run-logs/v2")
                .join(&storage.client_repo)
                .join(&identity)
                .join(skill)
                .join(run_id),
            lock_file: homes
                .state
                .join("larch/run-log-locks/v2")
                .join(&storage.client_repo)
                .join(identity)
                .join(skill)
                .join(format!("{run_id}.lock")),
        }
    }

    fn with_pending_dir(&self, pending_dir: PathBuf) -> Self {
        Self {
            pending_archive: pending_dir.join(PENDING_ARCHIVE_NAME),
            pending_metadata: pending_dir.join(PENDING_METADATA_NAME),
            pending_dir,
            cache_dir: self.cache_dir.clone(),
            lock_file: self.lock_file.clone(),
        }
    }
}

fn create_pending(
    paths: &PublicationPaths,
    storage: &ToolRepositoryStorage,
    context: &LifecycleContext,
) -> Result<PendingPublication, LifecycleError> {
    let parent = paths
        .pending_dir
        .parent()
        .ok_or_else(|| LifecycleError::new("pending publication parent is missing"))?;
    ensure_safe_directory(parent)?;
    let temporary_dir = parent.join(format!(
        ".{}.pending-{}-{}",
        context.run_id,
        std::process::id(),
        Uuid::new_v4()
    ));
    let temporary = paths.with_pending_dir(temporary_dir.clone());
    let created = (|| {
        ensure_safe_directory(&temporary.pending_dir)?;
        let archive = create_archive(
            &context.run_dir,
            &temporary.pending_archive,
            &context.skill,
            &context.run_id,
        )?;
        let pending = PendingPublication {
            archive_sha256: archive.archive_sha256,
            archive_size: archive.archive_size,
            attempts: 0,
            client_repo: storage.client_repo.clone(),
            last_error: String::new(),
            manifest_sha256: archive.manifest_sha256,
            remote_key: format!("run-logs/{}/{}.tar.gz", context.skill, context.run_id),
            run_id: context.run_id.clone(),
            schema_version: 2,
            skill: context.skill.clone(),
            storage_origin_id: storage.storage_origin_id(),
            tool_repo_uri: storage.uri(),
        };
        write_pending(&temporary, &pending)?;
        fs::rename(&temporary.pending_dir, &paths.pending_dir).map_err(io_error)?;
        sync_directory(parent)?;
        load_pending(paths, storage, context)
    })();
    if temporary_dir.exists() {
        let _ = fs::remove_dir_all(temporary_dir);
    }
    created
}

fn load_pending(
    paths: &PublicationPaths,
    storage: &ToolRepositoryStorage,
    context: &LifecycleContext,
) -> Result<PendingPublication, LifecycleError> {
    if !safe_regular_file(&paths.pending_metadata)? || !safe_regular_file(&paths.pending_archive)? {
        return Err(LifecycleError::new(
            "pending publication files are missing or unsafe",
        ));
    }
    let (metadata_bytes, _) = read_stable_regular_file(&paths.pending_metadata)?;
    let pending: PendingPublication = serde_json::from_slice(&metadata_bytes)
        .map_err(|_| LifecycleError::new("pending publication metadata is invalid JSON"))?;
    if pending.schema_version != 2
        || pending.tool_repo_uri != storage.uri()
        || pending.client_repo != storage.client_repo
        || pending.storage_origin_id != storage.storage_origin_id()
        || pending.skill != context.skill
        || pending.run_id != context.run_id
        || pending.remote_key != format!("run-logs/{}/{}.tar.gz", context.skill, context.run_id)
        || pending.archive_size == 0
        || !valid_sha256(&pending.archive_sha256)
        || !valid_sha256(&pending.manifest_sha256)
        || sha256_file(&paths.pending_archive)?
            != (pending.archive_sha256.clone(), pending.archive_size)
    {
        return Err(LifecycleError::new(
            "pending publication identity does not match the live request",
        ));
    }
    Ok(pending)
}

fn write_pending(
    paths: &PublicationPaths,
    pending: &PendingPublication,
) -> Result<(), LifecycleError> {
    let mut data =
        serde_json::to_vec(pending).map_err(|error| LifecycleError::new(error.to_string()))?;
    data.push(b'\n');
    atomic_write(&paths.pending_metadata, &data, 0o600)
}

fn publish_cache(
    paths: &PublicationPaths,
    staging: Option<&Path>,
    skill: &str,
    run_id: &str,
    expected_manifest_sha256: &str,
) -> Result<(), LifecycleError> {
    if existing_safe_directory(&paths.cache_dir)? {
        return verify_materialized_cache(
            &paths.cache_dir,
            skill,
            run_id,
            expected_manifest_sha256,
        );
    }
    if let Some(staging) = staging {
        let (manifest, manifest_sha256) = archive_manifest(staging, skill, run_id)?;
        if manifest_sha256 == expected_manifest_sha256 {
            return promote_staging_cache(
                paths,
                staging,
                skill,
                run_id,
                expected_manifest_sha256,
                &manifest,
            );
        }
    }
    materialize_pending_archive(paths, skill, run_id, expected_manifest_sha256)
}

fn promote_staging_cache(
    paths: &PublicationPaths,
    staging: &Path,
    skill: &str,
    run_id: &str,
    expected_manifest_sha256: &str,
    manifest: &[u8],
) -> Result<(), LifecycleError> {
    let parent = paths
        .cache_dir
        .parent()
        .ok_or_else(|| LifecycleError::new("cache directory parent is missing"))?;
    ensure_safe_directory(parent)?;
    let temporary = parent.join(format!(
        ".{}.cache-{}-{}",
        paths
            .cache_dir
            .file_name()
            .unwrap_or_default()
            .to_string_lossy(),
        std::process::id(),
        Uuid::new_v4()
    ));
    let result = (|| {
        copy_tree(staging, &temporary)?;
        set_path_mode(&temporary, 0o700)?;
        sync_directory(&temporary)?;
        atomic_write(&temporary.join(ARCHIVE_MANIFEST_NAME), manifest, 0o644)?;
        verify_materialized_cache(&temporary, skill, run_id, expected_manifest_sha256)?;
        fs::rename(&temporary, &paths.cache_dir).map_err(io_error)?;
        sync_directory(parent)?;
        if let Err(error) =
            verify_materialized_cache(&paths.cache_dir, skill, run_id, expected_manifest_sha256)
        {
            let _ = fs::remove_dir_all(&paths.cache_dir);
            let _ = sync_directory(parent);
            return Err(error);
        }
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_dir_all(&temporary);
    }
    result
}

fn materialize_pending_archive(
    paths: &PublicationPaths,
    skill: &str,
    run_id: &str,
    expected_manifest_sha256: &str,
) -> Result<(), LifecycleError> {
    let archive_metadata = fs::symlink_metadata(&paths.pending_archive).map_err(io_error)?;
    if archive_metadata.file_type().is_symlink()
        || !archive_metadata.is_file()
        || archive_metadata.len() == 0
    {
        return Err(LifecycleError::new(
            "pending run archive is missing or unsafe",
        ));
    }
    let parent = paths
        .cache_dir
        .parent()
        .ok_or_else(|| LifecycleError::new("cache directory parent is missing"))?;
    ensure_safe_directory(parent)?;
    let temporary = parent.join(format!(
        ".{}.materialize-{}-{}",
        paths
            .cache_dir
            .file_name()
            .unwrap_or_default()
            .to_string_lossy(),
        std::process::id(),
        Uuid::new_v4()
    ));
    let result = (|| {
        ensure_safe_directory(&temporary)?;
        set_path_mode(&temporary, 0o700)?;
        extract_pending_archive(&paths.pending_archive, archive_metadata.len(), &temporary)?;
        verify_materialized_cache(&temporary, skill, run_id, expected_manifest_sha256)?;
        fs::rename(&temporary, &paths.cache_dir).map_err(io_error)?;
        sync_directory(parent)?;
        if let Err(error) =
            verify_materialized_cache(&paths.cache_dir, skill, run_id, expected_manifest_sha256)
        {
            let _ = fs::remove_dir_all(&paths.cache_dir);
            let _ = sync_directory(parent);
            return Err(error);
        }
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_dir_all(&temporary);
    }
    result
}

fn extract_pending_archive(
    archive_path: &Path,
    compressed_size: u64,
    destination: &Path,
) -> Result<(), LifecycleError> {
    let file = File::open(archive_path).map_err(io_error)?;
    let mut archive = tar::Archive::new(GzDecoder::new(file));
    let mut names: HashMap<UniCase<String>, String> = HashMap::new();
    let mut previous = None;
    let mut expanded_bytes = 0_u64;
    let mut directories = Vec::new();
    for (index, entry) in archive.entries().map_err(io_error)?.enumerate() {
        if index >= ARCHIVE_MAX_MEMBERS {
            return Err(LifecycleError::new("archive exceeds member-count limit"));
        }
        let mut entry = entry.map_err(io_error)?;
        let path_bytes = entry.path_bytes();
        let raw_name = std::str::from_utf8(path_bytes.as_ref())
            .map_err(|_| LifecycleError::new("archive member path is not UTF-8"))?;
        let path = normalized_member_path(Path::new(raw_name))?;
        if path != raw_name {
            return Err(LifecycleError::new("archive member path is not canonical"));
        }
        if previous
            .as_ref()
            .is_some_and(|known: &String| known >= &path)
        {
            return Err(LifecycleError::new(
                "archive members are not in canonical order",
            ));
        }
        previous = Some(path.clone());
        if names
            .insert(UniCase::new(path.clone()), path.clone())
            .is_some()
        {
            return Err(LifecycleError::new(
                "ambiguous archive member path after normalization",
            ));
        }
        let (directory, size, normalized_mode) = validate_archive_header(entry.header(), &path)?;
        expanded_bytes = expanded_bytes
            .checked_add(size)
            .ok_or_else(|| LifecycleError::new("archive expanded size overflowed"))?;
        if expanded_bytes > ARCHIVE_MAX_EXPANDED_BYTES {
            return Err(LifecycleError::new(
                "archive exceeds total expanded-size limit",
            ));
        }
        let output = destination.join(path.split('/').collect::<PathBuf>());
        let parent = output
            .parent()
            .ok_or_else(|| LifecycleError::new("archive member parent is missing"))?;
        ensure_existing_safe_directory(parent)?;
        if directory {
            fs::create_dir(&output).map_err(io_error)?;
            set_path_mode(&output, 0o700)?;
            directories.push(output);
            continue;
        }
        let mut output_file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&output)
            .map_err(io_error)?;
        set_mode(&output_file, normalized_mode)?;
        let written = std::io::copy(&mut entry, &mut output_file).map_err(io_error)?;
        if written != size {
            return Err(LifecycleError::new("archive member is truncated"));
        }
        output_file.flush().map_err(io_error)?;
        output_file.sync_all().map_err(io_error)?;
    }
    if expanded_bytes
        > compressed_size
            .checked_mul(1_000)
            .ok_or_else(|| LifecycleError::new("archive compression ratio overflowed"))?
    {
        return Err(LifecycleError::new(
            "archive exceeds compression-ratio limit",
        ));
    }
    directories.sort_by_key(|path| std::cmp::Reverse(path.components().count()));
    for directory in directories {
        set_path_mode(&directory, 0o755)?;
        sync_directory(&directory)?;
    }
    sync_directory(destination)
}

fn validate_archive_header(
    header: &tar::Header,
    path: &str,
) -> Result<(bool, u64, u32), LifecycleError> {
    let entry_type = header.entry_type();
    let directory = entry_type.is_dir();
    if !directory && !entry_type.is_file() {
        return Err(LifecycleError::new(
            "archive contains an unsafe member type",
        ));
    }
    let size = header.size().map_err(io_error)?;
    if size > ARCHIVE_MAX_MEMBER_BYTES || (directory && size != 0) {
        return Err(LifecycleError::new("archive member exceeds its size limit"));
    }
    let mode = header.mode().map_err(io_error)?;
    let normalized_mode = if directory {
        0o755
    } else if path == ARCHIVE_MANIFEST_NAME {
        0o644
    } else if matches!(mode, 0o644 | 0o755) {
        mode
    } else {
        return Err(LifecycleError::new("archive file mode is not normalized"));
    };
    if mode != normalized_mode
        || header.mtime().map_err(io_error)? != 0
        || header.uid().map_err(io_error)? != 0
        || header.gid().map_err(io_error)? != 0
        || header
            .username()
            .map_err(|_| LifecycleError::new("archive username is not UTF-8"))?
            .is_some_and(|name| !name.is_empty())
        || header
            .groupname()
            .map_err(|_| LifecycleError::new("archive group name is not UTF-8"))?
            .is_some_and(|name| !name.is_empty())
    {
        return Err(LifecycleError::new(
            "archive member metadata is not normalized",
        ));
    }
    Ok((directory, size, normalized_mode))
}

fn verify_materialized_cache(
    cache_dir: &Path,
    skill: &str,
    run_id: &str,
    expected_manifest_sha256: &str,
) -> Result<(), LifecycleError> {
    let manifest_path = cache_dir.join(ARCHIVE_MANIFEST_NAME);
    if !safe_regular_file(&manifest_path)? {
        return Err(LifecycleError::new(
            "published cache is missing its archive manifest",
        ));
    }
    let (manifest, _) = read_stable_regular_file(&manifest_path)?;
    if manifest.len() as u64 > ARCHIVE_MAX_MEMBER_BYTES
        || hex_digest(&manifest) != expected_manifest_sha256
    {
        return Err(LifecycleError::new(
            "existing cache directory contains different run content",
        ));
    }
    let (actual, actual_sha256) = materialized_archive_manifest(cache_dir, skill, run_id)?;
    if actual != manifest || actual_sha256 != expected_manifest_sha256 {
        return Err(LifecycleError::new(
            "existing cache directory contains different run content",
        ));
    }
    Ok(())
}

fn valid_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

#[cfg(unix)]
struct PublicationLock {
    _lock: nix::fcntl::Flock<File>,
}

#[cfg(not(unix))]
struct PublicationLock(PathBuf);

impl PublicationLock {
    #[cfg(unix)]
    fn acquire(path: &Path) -> Result<Self, LifecycleError> {
        if let Some(parent) = path.parent() {
            ensure_safe_directory(parent)?;
        }
        if path
            .symlink_metadata()
            .is_ok_and(|metadata| metadata.file_type().is_symlink())
        {
            return Err(LifecycleError::new("refusing symlinked publication lock"));
        }
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(path)
            .map_err(|_| LifecycleError::new("run-log publication is already active"))?;
        set_mode(&file, 0o600)?;
        let lock = nix::fcntl::Flock::lock(file, nix::fcntl::FlockArg::LockExclusive)
            .map_err(|_| LifecycleError::new("run-log publication is already active"))?;
        Ok(Self { _lock: lock })
    }

    #[cfg(not(unix))]
    fn acquire(path: &Path) -> Result<Self, LifecycleError> {
        if let Some(parent) = path.parent() {
            ensure_safe_directory(parent)?;
        }
        OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .map_err(|_| LifecycleError::new("run-log publication is already active"))?;
        Ok(Self(path.to_path_buf()))
    }
}

#[cfg(not(unix))]
impl Drop for PublicationLock {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

struct ArchiveResult {
    archive_sha256: String,
    archive_size: u64,
    manifest_sha256: String,
}

#[derive(Clone)]
struct ArchiveMember {
    path: String,
    source: PathBuf,
    directory: bool,
    size: u64,
    sha256: Option<String>,
    mode: u32,
}

fn create_archive(
    staging: &Path,
    destination: &Path,
    skill: &str,
    run_id: &str,
) -> Result<ArchiveResult, LifecycleError> {
    let members = collect_members(staging)?;
    let (manifest, manifest_sha256) = archive_manifest_from_members(&members, skill, run_id)?;
    let file = File::create(destination).map_err(io_error)?;
    let gzip = GzBuilder::new().mtime(0).write(file, Compression::best());
    let mut archive = tar::Builder::new(gzip);
    let mut manifest_written = false;
    for member in &members {
        if !manifest_written && member.path.as_str() > ARCHIVE_MANIFEST_NAME {
            append_archive_member(&mut archive, ARCHIVE_MANIFEST_NAME, 0o644, false, &manifest)?;
            manifest_written = true;
        }
        let bytes = if member.directory {
            Vec::new()
        } else {
            read_stable_regular_file(&member.source)?.0
        };
        if !member.directory
            && (bytes.len() as u64 != member.size
                || member.sha256.as_deref() != Some(hex_digest(&bytes).as_str()))
        {
            return Err(LifecycleError::new(format!(
                "archive source changed while packaging: {}",
                member.source.display()
            )));
        }
        append_archive_member(
            &mut archive,
            &member.path,
            member.mode,
            member.directory,
            &bytes,
        )?;
    }
    if !manifest_written {
        append_archive_member(&mut archive, ARCHIVE_MANIFEST_NAME, 0o644, false, &manifest)?;
    }
    let gzip = archive.into_inner().map_err(io_error)?;
    let mut file = gzip.finish().map_err(io_error)?;
    file.flush().map_err(io_error)?;
    file.sync_all().map_err(io_error)?;
    let (archive_sha256, archive_size) = sha256_file(destination)?;
    Ok(ArchiveResult {
        archive_sha256,
        archive_size,
        manifest_sha256,
    })
}

fn archive_manifest(
    staging: &Path,
    skill: &str,
    run_id: &str,
) -> Result<(Vec<u8>, String), LifecycleError> {
    let members = collect_members(staging)?;
    archive_manifest_from_members(&members, skill, run_id)
}

fn materialized_archive_manifest(
    cache_dir: &Path,
    skill: &str,
    run_id: &str,
) -> Result<(Vec<u8>, String), LifecycleError> {
    let members = collect_materialized_members(cache_dir)?;
    let result = archive_manifest_from_members(&members, skill, run_id)?;
    let expanded_bytes = members
        .iter()
        .try_fold(result.0.len() as u64, |total, member| {
            total
                .checked_add(member.size)
                .ok_or_else(|| LifecycleError::new("materialized run directory size overflowed"))
        })?;
    if expanded_bytes > ARCHIVE_MAX_EXPANDED_BYTES {
        return Err(LifecycleError::new(
            "materialized run directory exceeds expanded-size limit",
        ));
    }
    Ok(result)
}

fn archive_manifest_from_members(
    members: &[ArchiveMember],
    skill: &str,
    run_id: &str,
) -> Result<(Vec<u8>, String), LifecycleError> {
    let records: Vec<Value> = members
        .iter()
        .map(|member| {
            json!({
                "kind": if member.directory { "directory" } else { "file" },
                "path": member.path,
                "sha256": member.sha256,
                "size": member.size,
            })
        })
        .collect();
    let mut bytes = serde_json::to_vec(&json!({
        "archive_format": "larch-run-archive",
        "member_count": records.len(),
        "members": records,
        "run_id": run_id,
        "schema_version": 1,
        "skill": skill,
    }))
    .map_err(|error| LifecycleError::new(error.to_string()))?;
    bytes.push(b'\n');
    let digest = hex_digest(&bytes);
    Ok((bytes, digest))
}

fn collect_members(root: &Path) -> Result<Vec<ArchiveMember>, LifecycleError> {
    collect_members_with_mode(root, false)
}

fn collect_materialized_members(root: &Path) -> Result<Vec<ArchiveMember>, LifecycleError> {
    collect_members_with_mode(root, true)
}

fn collect_members_with_mode(
    root: &Path,
    materialized_cache: bool,
) -> Result<Vec<ArchiveMember>, LifecycleError> {
    ensure_existing_safe_directory(root)?;
    let mut members = Vec::new();
    let mut expanded_bytes = 0_u64;
    collect_members_below(
        root,
        root,
        &mut members,
        materialized_cache,
        &mut expanded_bytes,
    )?;
    members.sort_by(|left, right| left.path.cmp(&right.path));
    let mut names: HashMap<UniCase<String>, String> = HashMap::new();
    names.insert(
        UniCase::new(ARCHIVE_MANIFEST_NAME.to_owned()),
        ARCHIVE_MANIFEST_NAME.to_owned(),
    );
    for member in &members {
        if member.path == ARCHIVE_MANIFEST_NAME {
            return Err(LifecycleError::new("archive member path is reserved"));
        }
        if names
            .insert(UniCase::new(member.path.clone()), member.path.clone())
            .is_some()
        {
            return Err(LifecycleError::new(
                "ambiguous archive member path after normalization",
            ));
        }
    }
    Ok(members)
}

fn collect_members_below(
    root: &Path,
    directory: &Path,
    output: &mut Vec<ArchiveMember>,
    materialized_cache: bool,
    expanded_bytes: &mut u64,
) -> Result<(), LifecycleError> {
    for entry in sorted_entries(directory)? {
        let path = entry.path();
        let metadata = fs::symlink_metadata(&path).map_err(io_error)?;
        if metadata.file_type().is_symlink() {
            return Err(LifecycleError::new(format!(
                "archive source contains a symlink: {}",
                path.display()
            )));
        }
        let relative = path
            .strip_prefix(root)
            .map_err(|error| LifecycleError::new(error.to_string()))?;
        let name = normalized_member_path(relative)?;
        if metadata.is_dir() {
            output.push(ArchiveMember {
                path: name,
                source: path.clone(),
                directory: true,
                size: 0,
                sha256: None,
                mode: 0o755,
            });
            if materialized_cache && output.len() > ARCHIVE_MAX_MEMBERS {
                return Err(LifecycleError::new(
                    "materialized run directory exceeds member-count limit",
                ));
            }
            collect_members_below(root, &path, output, materialized_cache, expanded_bytes)?;
        } else if metadata.is_file() {
            reject_hardlink(&metadata, &path)?;
            if materialized_cache && name == ARCHIVE_MANIFEST_NAME {
                continue;
            }
            if materialized_cache {
                if metadata.len() > ARCHIVE_MAX_MEMBER_BYTES {
                    return Err(LifecycleError::new(
                        "materialized archive member exceeds size limit",
                    ));
                }
                *expanded_bytes = expanded_bytes.checked_add(metadata.len()).ok_or_else(|| {
                    LifecycleError::new("materialized run directory size overflowed")
                })?;
                if *expanded_bytes > ARCHIVE_MAX_EXPANDED_BYTES {
                    return Err(LifecycleError::new(
                        "materialized run directory exceeds expanded-size limit",
                    ));
                }
            }
            let (bytes, stable_metadata) = read_stable_regular_file(&path)?;
            output.push(ArchiveMember {
                path: name,
                source: path.clone(),
                directory: false,
                size: stable_metadata.len(),
                sha256: Some(hex_digest(&bytes)),
                mode: normalized_mode_from_metadata(&stable_metadata),
            });
            if materialized_cache && output.len() > ARCHIVE_MAX_MEMBERS {
                return Err(LifecycleError::new(
                    "materialized run directory exceeds member-count limit",
                ));
            }
        } else {
            return Err(LifecycleError::new(format!(
                "archive source contains a special file: {}",
                path.display()
            )));
        }
    }
    Ok(())
}

fn append_archive_member(
    archive: &mut tar::Builder<impl std::io::Write>,
    name: &str,
    mode: u32,
    directory: bool,
    bytes: &[u8],
) -> Result<(), LifecycleError> {
    let mut header = tar::Header::new_ustar();
    if header.set_path(name).is_err() {
        archive
            .append_pax_extensions([("path", name.as_bytes())])
            .map_err(io_error)?;
        header.set_path("PaxEntry").map_err(io_error)?;
    }
    header.set_size(bytes.len() as u64);
    header.set_mode(mode);
    header.set_uid(0);
    header.set_gid(0);
    header.set_mtime(0);
    header.set_username("").map_err(io_error)?;
    header.set_groupname("").map_err(io_error)?;
    header.set_entry_type(if directory {
        tar::EntryType::Directory
    } else {
        tar::EntryType::Regular
    });
    header.set_cksum();
    archive.append(&header, bytes).map_err(io_error)
}

fn normalized_member_path(relative: &Path) -> Result<String, LifecycleError> {
    let mut parts = Vec::new();
    for component in relative.components() {
        let std::path::Component::Normal(raw) = component else {
            return Err(LifecycleError::new("archive member path is unsafe"));
        };
        let raw = raw
            .to_str()
            .ok_or_else(|| LifecycleError::new("archive member path is not UTF-8"))?;
        let normalized: String = raw.nfc().collect();
        if normalized.is_empty()
            || matches!(normalized.as_str(), "." | "..")
            || normalized.contains(['/', '\\'])
        {
            return Err(LifecycleError::new("archive member path is unsafe"));
        }
        parts.push(normalized);
    }
    if parts.is_empty() {
        return Err(LifecycleError::new("archive member path is empty"));
    }
    Ok(parts.join("/"))
}

fn read_context(path: &Path) -> Result<LifecycleContext, LifecycleError> {
    serde_json::from_slice(&read_stable_regular_file(path)?.0).map_err(|error| {
        LifecycleError::new(format!("lifecycle context must be valid JSON: {error}"))
    })
}

fn read_json_object(path: &Path, label: &str) -> Result<Map<String, Value>, LifecycleError> {
    if !safe_regular_file(path)? {
        return Err(LifecycleError::new(format!("{label} is missing or unsafe")));
    }
    let value: Value = serde_json::from_slice(&read_stable_regular_file(path)?.0)
        .map_err(|error| LifecycleError::new(format!("{label} is invalid JSON: {error}")))?;
    value
        .as_object()
        .cloned()
        .ok_or_else(|| LifecycleError::new(format!("{label} must be a JSON object")))
}

fn atomic_write(path: &Path, bytes: &[u8], mode: u32) -> Result<(), LifecycleError> {
    let parent = path
        .parent()
        .ok_or_else(|| LifecycleError::new("atomic-write parent is missing"))?;
    ensure_safe_directory(parent)?;
    let root = TemporaryRoot::resolve(Some(parent))
        .map_err(|error| LifecycleError::new(error.to_string()))?;
    let destination = root
        .confine(path, PathIntent::Write)
        .map_err(|error| LifecycleError::new(error.to_string()))?;
    atomic_write_bytes(&destination, bytes, mode)
        .map_err(|error| LifecycleError::new(error.to_string()))
}

fn ensure_safe_directory(path: &Path) -> Result<(), LifecycleError> {
    reject_existing_symlinks(path)?;
    ensure_directory_chain(path).map_err(|error| LifecycleError::new(error.to_string()))?;
    ensure_existing_safe_directory(path)
}

fn ensure_existing_safe_directory(path: &Path) -> Result<(), LifecycleError> {
    let metadata = fs::symlink_metadata(path).map_err(io_error)?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err(LifecycleError::new(format!(
            "lifecycle directory is missing or unsafe: {}",
            path.display()
        )));
    }
    reject_existing_symlinks(path)
}

fn existing_safe_directory(path: &Path) -> Result<bool, LifecycleError> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.is_dir() && !metadata.file_type().is_symlink() => {
            reject_existing_symlinks(path)?;
            Ok(true)
        }
        Ok(_) => Err(LifecycleError::new(format!(
            "lifecycle directory is unsafe: {}",
            path.display()
        ))),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(error) => Err(io_error(error)),
    }
}

fn reject_existing_symlinks(path: &Path) -> Result<(), LifecycleError> {
    let mut current = Some(path);
    while let Some(candidate) = current {
        match fs::symlink_metadata(candidate) {
            Ok(metadata) if metadata.file_type().is_symlink() => {
                return Err(LifecycleError::new(format!(
                    "lifecycle path contains a symlink: {}",
                    candidate.display()
                )));
            }
            Ok(_) => {}
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(io_error(error)),
        }
        current = candidate.parent();
    }
    Ok(())
}

fn normalize_absolute(path: &Path) -> Result<PathBuf, LifecycleError> {
    if !path.is_absolute() {
        return Err(LifecycleError::new("lifecycle path must be absolute"));
    }
    let text = path
        .to_str()
        .ok_or_else(|| LifecycleError::new("lifecycle path is not UTF-8"))?;
    if text
        .chars()
        .any(|character| character.is_ascii_control() || character == '\u{7f}')
    {
        return Err(LifecycleError::new(
            "lifecycle path contains a control character",
        ));
    }
    if path.components().any(|component| {
        matches!(
            component,
            std::path::Component::CurDir | std::path::Component::ParentDir
        )
    }) {
        return Err(LifecycleError::new(
            "lifecycle path contains an unsafe component",
        ));
    }
    if path
        .symlink_metadata()
        .is_ok_and(|metadata| metadata.file_type().is_symlink())
    {
        return Err(LifecycleError::new(format!(
            "lifecycle path is a symlink: {}",
            path.display()
        )));
    }
    let mut cursor = path;
    let mut missing = Vec::new();
    while !cursor.exists() {
        let name = cursor
            .file_name()
            .ok_or_else(|| LifecycleError::new("lifecycle path has no existing ancestor"))?;
        missing.push(name.to_os_string());
        cursor = cursor
            .parent()
            .ok_or_else(|| LifecycleError::new("lifecycle path has no existing ancestor"))?;
    }
    let mut normalized = fs::canonicalize(cursor).map_err(io_error)?;
    for component in missing.iter().rev() {
        normalized.push(component);
    }
    Ok(normalized)
}

fn safe_regular_file(path: &Path) -> Result<bool, LifecycleError> {
    reject_existing_symlinks(path)?;
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.is_file() && !metadata.file_type().is_symlink() => Ok(true),
        Ok(_) => Err(LifecycleError::new(format!(
            "lifecycle file is unsafe: {}",
            path.display()
        ))),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(error) => Err(io_error(error)),
    }
}

fn remove_tree_strict(path: &Path) -> Result<(), LifecycleError> {
    ensure_existing_safe_directory(path)?;
    fs::remove_dir_all(path).map_err(io_error)?;
    if path.exists() {
        return Err(LifecycleError::new(format!(
            "lifecycle cleanup did not complete: {}",
            path.display()
        )));
    }
    Ok(())
}

#[cfg(unix)]
fn sync_directory(path: &Path) -> Result<(), LifecycleError> {
    File::open(path)
        .map_err(io_error)?
        .sync_all()
        .map_err(io_error)
}

#[cfg(not(unix))]
fn sync_directory(_path: &Path) -> Result<(), LifecycleError> {
    Ok(())
}

fn tree_files(root: &Path) -> Result<Vec<PathBuf>, LifecycleError> {
    Ok(collect_members(root)?
        .into_iter()
        .filter(|member| !member.directory)
        .map(|member| member.source)
        .collect())
}

fn sorted_entries(path: &Path) -> Result<Vec<fs::DirEntry>, LifecycleError> {
    let mut entries: Vec<_> = fs::read_dir(path)
        .map_err(io_error)?
        .collect::<Result<_, _>>()
        .map_err(io_error)?;
    entries.sort_by_key(fs::DirEntry::file_name);
    Ok(entries)
}

fn copy_tree(source: &Path, destination: &Path) -> Result<(), LifecycleError> {
    ensure_safe_directory(destination)?;
    for entry in sorted_entries(source)? {
        let source_path = entry.path();
        let component = normalized_member_path(Path::new(&entry.file_name()))?;
        let destination_path = destination.join(component);
        let metadata = fs::symlink_metadata(&source_path).map_err(io_error)?;
        if metadata.is_dir() && !metadata.file_type().is_symlink() {
            copy_tree(&source_path, &destination_path)?;
        } else if metadata.is_file() && !metadata.file_type().is_symlink() {
            let (bytes, stable_metadata) = read_stable_regular_file(&source_path)?;
            let mut output = OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&destination_path)
                .map_err(io_error)?;
            set_mode(&output, normalized_mode_from_metadata(&stable_metadata))?;
            output.write_all(&bytes).map_err(io_error)?;
            output.flush().map_err(io_error)?;
            output.sync_all().map_err(io_error)?;
        } else {
            return Err(LifecycleError::new("cache source contains an unsafe entry"));
        }
    }
    set_path_mode(destination, 0o755)?;
    sync_directory(destination)?;
    Ok(())
}

fn sha256_file(path: &Path) -> Result<(String, u64), LifecycleError> {
    let (mut file, expected) = open_stable_regular_file(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = vec![0_u8; 64 * 1024];
    loop {
        let count = file.read(&mut buffer).map_err(io_error)?;
        if count == 0 {
            break;
        }
        hasher.update(&buffer[..count]);
    }
    let current = fs::symlink_metadata(path).map_err(io_error)?;
    if !same_file_snapshot(&expected, &current) {
        return Err(LifecycleError::new(format!(
            "publication archive changed while reading: {}",
            path.display()
        )));
    }
    Ok((format!("{:x}", hasher.finalize()), expected.len()))
}

fn read_stable_regular_file(path: &Path) -> Result<(Vec<u8>, fs::Metadata), LifecycleError> {
    let (mut file, expected) = open_stable_regular_file(path)?;
    let capacity = usize::try_from(expected.len()).unwrap_or(0);
    let mut bytes = Vec::with_capacity(capacity);
    file.read_to_end(&mut bytes).map_err(io_error)?;
    let opened_after = file.metadata().map_err(io_error)?;
    let current = fs::symlink_metadata(path).map_err(io_error)?;
    if !same_file_snapshot(&expected, &opened_after)
        || !same_file_snapshot(&expected, &current)
        || u64::try_from(bytes.len()).ok() != Some(expected.len())
    {
        return Err(LifecycleError::new(format!(
            "regular file changed while reading: {}",
            path.display()
        )));
    }
    Ok((bytes, expected))
}

fn open_stable_regular_file(path: &Path) -> Result<(File, fs::Metadata), LifecycleError> {
    let expected = fs::symlink_metadata(path).map_err(io_error)?;
    if expected.file_type().is_symlink() || !expected.is_file() {
        return Err(LifecycleError::new(format!(
            "refusing unsafe regular-file read: {}",
            path.display()
        )));
    }
    reject_hardlink(&expected, path)?;
    let mut options = OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt as _;

        options.custom_flags(nix::libc::O_NOFOLLOW);
    }
    let file = options.open(path).map_err(io_error)?;
    let opened = file.metadata().map_err(io_error)?;
    if !same_file_snapshot(&expected, &opened) {
        return Err(LifecycleError::new(format!(
            "regular file changed while opening: {}",
            path.display()
        )));
    }
    Ok((file, expected))
}

#[cfg(unix)]
fn same_file_snapshot(left: &fs::Metadata, right: &fs::Metadata) -> bool {
    use std::os::unix::fs::MetadataExt as _;

    left.dev() == right.dev()
        && left.ino() == right.ino()
        && left.size() == right.size()
        && left.mtime() == right.mtime()
        && left.mtime_nsec() == right.mtime_nsec()
}

#[cfg(not(unix))]
fn same_file_snapshot(left: &fs::Metadata, right: &fs::Metadata) -> bool {
    left.len() == right.len() && left.modified().ok() == right.modified().ok()
}

fn hex_digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn now() -> String {
    Utc::now().to_rfc3339_opts(SecondsFormat::Secs, true)
}

fn now_precise() -> String {
    Utc::now().to_rfc3339_opts(SecondsFormat::Micros, true)
}

#[allow(clippy::needless_pass_by_value)] // `Result::map_err` supplies owned I/O errors.
fn io_error(error: std::io::Error) -> LifecycleError {
    LifecycleError::new(error.to_string())
}

#[cfg(unix)]
fn normalized_mode_from_metadata(metadata: &fs::Metadata) -> u32 {
    use std::os::unix::fs::PermissionsExt as _;

    if metadata.permissions().mode() & 0o111 == 0 {
        0o644
    } else {
        0o755
    }
}

#[cfg(not(unix))]
fn normalized_mode_from_metadata(_metadata: &fs::Metadata) -> u32 {
    0o644
}

#[cfg(unix)]
fn set_mode(file: &File, mode: u32) -> Result<(), LifecycleError> {
    use std::os::unix::fs::PermissionsExt as _;
    file.set_permissions(fs::Permissions::from_mode(mode))
        .map_err(io_error)
}

#[cfg(not(unix))]
fn set_mode(_file: &File, _mode: u32) -> Result<(), LifecycleError> {
    Ok(())
}

#[cfg(unix)]
fn set_path_mode(path: &Path, mode: u32) -> Result<(), LifecycleError> {
    use std::os::unix::fs::PermissionsExt as _;
    fs::set_permissions(path, fs::Permissions::from_mode(mode)).map_err(io_error)
}

#[cfg(not(unix))]
fn set_path_mode(_path: &Path, _mode: u32) -> Result<(), LifecycleError> {
    Ok(())
}

#[cfg(unix)]
fn reject_hardlink(metadata: &fs::Metadata, path: &Path) -> Result<(), LifecycleError> {
    use std::os::unix::fs::MetadataExt as _;
    if metadata.nlink() > 1 {
        return Err(LifecycleError::new(format!(
            "regular-file input contains a hardlink: {}",
            path.display()
        )));
    }
    Ok(())
}

#[cfg(not(unix))]
fn reject_hardlink(_metadata: &fs::Metadata, _path: &Path) -> Result<(), LifecycleError> {
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use larch_core::{
        RunLogStorageMode, RunLogStorageReason, RunLogStorageResolution, StorageBase,
        ToolRepositoryStorage, injected_storage_resolution,
    };
    use tempfile::tempdir;

    use super::*;

    fn local_resolution() -> RunLogStorageResolution {
        RunLogStorageResolution::new(
            RunLogStorageMode::Disabled,
            RunLogStorageReason::ConfigFileMissing,
            None,
            "client",
            Some("local-id".to_owned()),
        )
        .expect("local resolution is valid")
    }

    fn enabled_resolution() -> RunLogStorageResolution {
        injected_storage_resolution(ToolRepositoryStorage::new(
            StorageBase::new("s3", "bucket"),
            "client",
        ))
    }

    #[test]
    fn environment_identity_and_path_validation_fail_closed() {
        assert!(LifecycleHomes::from_environment(&HashMap::new()).is_err());
        let mut environment = HashMap::from([
            ("XDG_STATE_HOME".to_owned(), "relative".to_owned()),
            ("XDG_CACHE_HOME".to_owned(), "/private/tmp/cache".to_owned()),
        ]);
        assert!(LifecycleHomes::from_environment(&environment).is_err());
        environment.insert("XDG_STATE_HOME".to_owned(), "/private/tmp/state".to_owned());
        environment.insert("XDG_CACHE_HOME".to_owned(), "relative".to_owned());
        assert!(LifecycleHomes::from_environment(&environment).is_err());
        let homes = LifecycleHomes::from_environment(&HashMap::from([(
            "HOME".to_owned(),
            "/private/tmp/home".to_owned(),
        )]))
        .expect("HOME fallbacks are valid");
        assert!(homes.state.ends_with(".local/state"));

        assert!(validate_identity("bad/skill", "run").is_err());
        assert!(validate_identity("review", "bad/run").is_err());
        assert_eq!(
            explicit_parent("", "").expect("empty parent is valid"),
            None
        );
        assert!(explicit_parent("review", "").is_err());
        assert_eq!(
            explicit_parent("review", "parent").expect("parent pair is valid"),
            Some(("review".to_owned(), "parent".to_owned()))
        );
        assert!(!valid_claude_session_id(""));
        assert!(!valid_claude_session_id("bad/session"));
        assert!(valid_claude_session_id("session_1-test"));

        assert!(normalize_absolute(Path::new("relative")).is_err());
        assert!(normalize_absolute(Path::new("/private/tmp/bad\npath")).is_err());
        assert!(normalize_absolute(Path::new("/private/tmp/../tmp")).is_err());
        let root = tempdir().expect("temporary path root is available");
        let canonical_root = fs::canonicalize(root.path()).expect("temporary root canonicalizes");
        assert_eq!(
            normalize_absolute(&canonical_root.join("missing/child"))
                .expect("missing suffix is normalized lexically"),
            canonical_root.join("missing/child")
        );
    }

    #[test]
    fn manifest_and_terminal_guards_reject_identity_and_outcome_drift() {
        let root = tempdir().expect("temporary lifecycle root is available");
        let resolution = local_resolution();
        let context = LifecycleContext::new(
            root.path().join("repo-😀"),
            &resolution,
            "review".to_owned(),
            "run".to_owned(),
            root.path().join("logs"),
        );
        fs::create_dir_all(&context.run_dir).expect("run directory is writable");
        fs::write(context.run_dir.join(UNIVERSAL_EXECUTION_ISSUES), b"")
            .expect("issue ledger is writable");
        let encoded = String::from_utf8(context_json(&context).expect("context JSON renders"))
            .expect("context JSON is UTF-8");
        assert!(encoded.contains("\\ud83d\\ude00"));

        let mut manifest: Map<String, Value> = lifecycle_manifest_updates(&resolution)
            .into_iter()
            .collect();
        manifest.insert("schema_version".to_owned(), json!(2));
        manifest.insert("skill".to_owned(), json!("review"));
        manifest.insert("run_id".to_owned(), json!("run"));
        assert!(validate_manifest_identity(&manifest, &context).is_ok());
        manifest.insert("run_id".to_owned(), json!("other"));
        assert!(validate_manifest_identity(&manifest, &context).is_err());
        manifest.insert("run_id".to_owned(), json!("run"));
        assert!(manifest_matches_resolution(&manifest, &resolution));
        manifest.insert("client_repo".to_owned(), json!("other"));
        assert!(!manifest_matches_resolution(&manifest, &resolution));

        let parent = ("design".to_owned(), "parent".to_owned());
        let mut parent_manifest = Map::new();
        parent_manifest.insert("parent_skill".to_owned(), json!("design"));
        parent_manifest.insert("parent_run_id".to_owned(), json!("parent"));
        assert!(validate_manifest_parent(&parent_manifest, Some(&parent)).is_ok());
        assert!(validate_manifest_parent(&parent_manifest, None).is_err());

        let mut terminal = Map::new();
        terminal.insert("terminal_outcome".to_owned(), json!("failure"));
        assert!(write_terminal_artifacts(&context, LifecycleOutcome::Success, &terminal).is_err());
        terminal.insert("terminal_outcome".to_owned(), Value::Null);
        fs::write(context.run_dir.join(UNIVERSAL_FINAL_REPORT), "wrong")
            .expect("conflicting report is writable");
        assert!(write_terminal_artifacts(&context, LifecycleOutcome::Success, &terminal).is_err());
        fs::remove_file(context.run_dir.join(UNIVERSAL_FINAL_REPORT))
            .expect("conflicting report is removable");
        terminal.insert("finished_at".to_owned(), json!(42));
        assert!(write_terminal_artifacts(&context, LifecycleOutcome::Success, &terminal).is_err());
    }

    #[test]
    fn completeness_helpers_cover_specialized_artifacts_and_durable_waivers() {
        let root = tempdir().expect("temporary completeness root is available");
        let run_dir = root.path().join("run");
        let repo = root.path().join("repo");
        fs::create_dir_all(run_dir.join("plan-review/round-2")).expect("review round is writable");
        fs::create_dir(&repo).expect("repository fixture is writable");
        fs::write(
            run_dir.join("final-summary.md"),
            "## /design run 1: approved-partition\n",
        )
        .expect("summary is writable");
        fs::write(run_dir.join(UNIVERSAL_SESSION_TRANSCRIPT), "transcript")
            .expect("transcript is writable");
        fs::write(
            repo.join("ARCHITECTURAL_INVARIANTS.md"),
            "# I-Test-1: Contract\n",
        )
        .expect("invariants are writable");
        fs::write(repo.join("ARCHITECTURAL_GUIDELINES.md"), "# Guidelines\n")
            .expect("guidelines are writable");
        let required = required_design_artifacts(&run_dir, &repo)
            .expect("design requirements are discoverable");
        let slugs: Vec<_> = required
            .iter()
            .map(|artifact| artifact.slug.as_str())
            .collect();
        assert!(slugs.contains(&"plan-review-round-2"));
        assert!(slugs.contains(&"invariant-assessment"));
        assert!(slugs.contains(&"guideline-assessment"));
        assert!(has_invariant_entry(
            "```\n# I-Fenced-1: No\n```\n# I-Live-1: Yes"
        ));

        let mut manifest = Map::new();
        manifest.insert("steps_ran".to_owned(), json!({"step18": true}));
        fs::write(run_dir.join("code-review-tally.json"), "{}").expect("review tally is writable");
        let implement = required_implement_artifacts(&run_dir, &manifest);
        assert!(
            implement
                .iter()
                .any(|artifact| artifact.slug == "token-report")
        );
        assert!(
            implement
                .iter()
                .any(|artifact| artifact.slug == "review-findings-full")
        );

        let issues_path = run_dir.join(UNIVERSAL_EXECUTION_ISSUES);
        fs::write(
            &issues_path,
            concat!(
                "not-json\n",
                "{\"category\":\"Warnings\",\"body\":\"token-report.json unavailable\"}\n"
            ),
        )
        .expect("issue ledger is writable");
        let issues = committed_issues(&run_dir).expect("committed issues are readable");
        let token = RequiredArtifact::new("token-report", "token-report.json");
        assert!(artifact_present_or_waived(&run_dir, &token, &issues));
        let unwaived = RequiredArtifact::new("other", "other.json");
        assert!(!artifact_present_or_waived(&run_dir, &unwaived, &issues));
    }

    #[test]
    fn filesystem_helpers_preserve_confinement_and_stable_file_identity() {
        let root = tempdir().expect("temporary filesystem root is available");
        let root_path = fs::canonicalize(root.path()).expect("temporary root canonicalizes");
        let source = root_path.join("source");
        fs::create_dir(&source).expect("source directory is writable");
        let file = source.join("payload");
        fs::write(&file, b"payload").expect("source file is writable");
        assert_eq!(normalized_member_path(Path::new("a/b")).unwrap(), "a/b");
        assert!(normalized_member_path(Path::new("")).is_err());
        assert!(normalized_member_path(Path::new("../escape")).is_err());
        assert!(normalized_member_path(Path::new("bad\\name")).is_err());
        assert_eq!(sha256_file(&file).expect("digest succeeds").1, 7);
        assert_eq!(read_stable_regular_file(&file).unwrap().0, b"payload");
        assert!(safe_regular_file(&root_path.join("missing")).is_ok_and(|value| !value));
        assert!(safe_regular_file(&source).is_err());
        assert!(existing_safe_directory(&source).unwrap());
        assert!(!existing_safe_directory(&root_path.join("missing")).unwrap());
        assert!(existing_safe_directory(&file).is_err());

        let destination = root_path.join("destination");
        copy_tree(&source, &destination).expect("safe tree copies");
        assert_eq!(fs::read(destination.join("payload")).unwrap(), b"payload");
        assert_eq!(tree_files(&destination).unwrap().len(), 1);
        fs::write(root_path.join("object.json"), "[]").expect("JSON fixture is writable");
        assert!(read_json_object(&root_path.join("object.json"), "object").is_err());
        fs::write(root_path.join("object.json"), "{").expect("JSON fixture is writable");
        assert!(read_json_object(&root_path.join("object.json"), "object").is_err());
        assert!(read_json_object(&root_path.join("absent.json"), "object").is_err());

        let removable = root_path.join("removable");
        fs::create_dir(&removable).expect("cleanup fixture is writable");
        remove_tree_strict(&removable).expect("safe tree is removed");
        assert!(!removable.exists());
        assert!(remove_tree_strict(&file).is_err());

        #[cfg(unix)]
        {
            let hardlink = root_path.join("hardlink");
            fs::hard_link(&file, &hardlink).expect("hardlink fixture is writable");
            assert!(open_stable_regular_file(&file).is_err());
            let symlink = root_path.join("symlink");
            std::os::unix::fs::symlink(&file, &symlink).expect("symlink fixture is writable");
            assert!(safe_regular_file(&symlink).is_err());
        }

        let enabled = enabled_resolution();
        let homes = LifecycleHomes {
            state: root_path.join("state"),
            cache: root_path.join("cache"),
        };
        assert!(
            lifecycle_root(&homes, &enabled)
                .to_string_lossy()
                .contains("storage-origins")
        );
    }
}
