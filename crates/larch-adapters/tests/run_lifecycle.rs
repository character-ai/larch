use std::{
    collections::HashMap,
    fs,
    io::Read as _,
    path::{Path, PathBuf},
    sync::{Arc, Mutex},
};

use flate2::{Compression, read::GzDecoder, write::GzEncoder};
use larch_adapters::run_lifecycle::{
    FinishRequest, LifecycleHomes, StartRequest, finish, has_persisted_context, load, start,
};
use larch_core::{
    LifecycleContext, LifecycleOutcome, ObjectPage, ObjectStore, ObjectStoreError,
    ObjectStoreFuture, RemoteObject, RunLogStorageMode, RunLogStorageReason,
    RunLogStorageResolution, StorageBase, ToolRepositoryStorage, injected_storage_resolution,
};
use sha2::{Digest as _, Sha256};
use tempfile::TempDir;

#[derive(Clone, Default)]
struct MemoryStore {
    objects: Arc<Mutex<HashMap<String, Vec<u8>>>>,
    fail_uploads: Arc<Mutex<usize>>,
    mismatched_upload_metadata: bool,
}

impl MemoryStore {
    fn fail_once() -> Self {
        Self {
            fail_uploads: Arc::new(Mutex::new(1)),
            ..Self::default()
        }
    }

    fn mismatched_upload_metadata() -> Self {
        Self {
            mismatched_upload_metadata: true,
            ..Self::default()
        }
    }

    fn keys(&self) -> Vec<String> {
        let mut keys: Vec<_> = self.objects.lock().unwrap().keys().cloned().collect();
        keys.sort();
        keys
    }

    fn object(&self, key: &str) -> Vec<u8> {
        self.objects.lock().unwrap()[key].clone()
    }
}

impl ObjectStore for MemoryStore {
    fn preflight_prefix<'a>(
        &'a self,
        _bucket: &'a str,
        _prefix: &'a str,
    ) -> ObjectStoreFuture<'a, ()> {
        Box::pin(async { Ok(()) })
    }

    fn list_page<'a>(
        &'a self,
        _bucket: &'a str,
        prefix: &'a str,
        _page_token: Option<&'a str>,
    ) -> ObjectStoreFuture<'a, ObjectPage> {
        Box::pin(async move {
            let objects = self.objects.lock().unwrap().clone();
            Ok(ObjectPage {
                objects: objects
                    .into_iter()
                    .filter(|(key, _)| key.starts_with(prefix))
                    .map(|(key, bytes)| RemoteObject {
                        size: bytes.len() as u64,
                        key,
                        etag: None,
                        version: None,
                    })
                    .collect(),
                next_page_token: None,
            })
        })
    }

    fn upload_create<'a>(
        &'a self,
        _bucket: &'a str,
        key: &'a str,
        source: &'a Path,
    ) -> ObjectStoreFuture<'a, RemoteObject> {
        Box::pin(async move {
            let mut failures = self.fail_uploads.lock().unwrap();
            if *failures != 0 {
                *failures -= 1;
                return Err(ObjectStoreError::Transport);
            }
            drop(failures);
            let bytes = fs::read(source).map_err(|_| ObjectStoreError::LocalIo)?;
            let mut stored = bytes.clone();
            if self.mismatched_upload_metadata {
                stored.push(0);
            }
            {
                let mut objects = self.objects.lock().unwrap();
                if objects.contains_key(key) {
                    return Err(ObjectStoreError::AlreadyExists);
                }
                objects.insert(key.to_owned(), stored);
            }
            Ok(RemoteObject {
                key: key.to_owned(),
                size: bytes.len() as u64,
                etag: None,
                version: None,
            })
        })
    }

    fn download<'a>(
        &'a self,
        _bucket: &'a str,
        key: &'a str,
        destination: &'a Path,
    ) -> ObjectStoreFuture<'a, ()> {
        Box::pin(async move {
            let bytes = self
                .objects
                .lock()
                .unwrap()
                .get(key)
                .cloned()
                .ok_or(ObjectStoreError::NotFound)?;
            fs::write(destination, bytes).map_err(|_| ObjectStoreError::LocalIo)
        })
    }

    fn metadata<'a>(
        &'a self,
        _bucket: &'a str,
        key: &'a str,
    ) -> ObjectStoreFuture<'a, RemoteObject> {
        Box::pin(async move {
            let size = self
                .objects
                .lock()
                .unwrap()
                .get(key)
                .map(Vec::len)
                .ok_or(ObjectStoreError::NotFound)?;
            Ok(RemoteObject {
                key: key.to_owned(),
                size: size as u64,
                etag: None,
                version: None,
            })
        })
    }
}

struct Harness {
    _temporary: TempDir,
    repo: PathBuf,
    homes: LifecycleHomes,
    environment: HashMap<String, String>,
    enabled: RunLogStorageResolution,
    local: RunLogStorageResolution,
}

impl Harness {
    fn new() -> Self {
        let temporary = tempfile::tempdir().unwrap();
        let root = fs::canonicalize(temporary.path()).unwrap();
        let repo = root.join("repo");
        fs::create_dir(&repo).unwrap();
        let homes = LifecycleHomes {
            state: root.join("state"),
            cache: root.join("cache"),
        };
        let enabled = injected_storage_resolution(ToolRepositoryStorage::new(
            StorageBase::new("gs", "bucket"),
            "client",
        ));
        let local = RunLogStorageResolution::new(
            RunLogStorageMode::Disabled,
            RunLogStorageReason::ConfigFileMissing,
            None,
            "client",
            Some("local-id".to_owned()),
        )
        .unwrap();
        Self {
            _temporary: temporary,
            repo,
            homes,
            environment: HashMap::new(),
            enabled,
            local,
        }
    }

    fn start(
        &self,
        resolution: &RunLogStorageResolution,
        skill: &str,
        run_id: &str,
        parent_context: Option<&Path>,
    ) -> larch_adapters::run_lifecycle::StartedRun {
        start(&StartRequest {
            repo_root: &self.repo,
            resolution,
            local_resolution: &self.local,
            homes: &self.homes,
            environment: &self.environment,
            skill,
            run_id: Some(run_id),
            log_root: None,
            parent_skill: "",
            parent_run_id: "",
            parent_context,
            issue: "8077",
            adopt_existing: false,
        })
        .unwrap()
    }

    fn request<'a>(
        &'a self,
        resolution: &'a RunLogStorageResolution,
        skill: &'a str,
        run_id: &'a str,
    ) -> StartRequest<'a> {
        StartRequest {
            repo_root: &self.repo,
            resolution,
            local_resolution: &self.local,
            homes: &self.homes,
            environment: &self.environment,
            skill,
            run_id: Some(run_id),
            log_root: None,
            parent_skill: "",
            parent_run_id: "",
            parent_context: None,
            issue: "8077",
            adopt_existing: false,
        }
    }

    fn pending_dir(&self, skill: &str, run_id: &str) -> PathBuf {
        let storage = self.enabled.storage().unwrap();
        self.homes
            .state
            .join("larch/run-log-pending/v2")
            .join(&storage.client_repo)
            .join(storage.storage_origin_id())
            .join(skill)
            .join(run_id)
    }

    fn cache_dir(&self, skill: &str, run_id: &str) -> PathBuf {
        let storage = self.enabled.storage().unwrap();
        self.homes
            .cache
            .join("larch/run-logs/v2")
            .join(&storage.client_repo)
            .join(storage.storage_origin_id())
            .join(skill)
            .join(run_id)
    }
}

fn finish_request<'a>(harness: &'a Harness, run_id: &'a str) -> FinishRequest<'a> {
    FinishRequest {
        repo_root: &harness.repo,
        active_resolution: &harness.enabled,
        local_resolution: &harness.local,
        homes: &harness.homes,
        environment: &harness.environment,
        skill: "review",
        run_id,
        outcome: LifecycleOutcome::Failure,
        pre_scrub_violations: 0,
    }
}

fn archive_bytes(entries: &[(&str, tar::EntryType)]) -> Vec<u8> {
    let encoder = GzEncoder::new(Vec::new(), Compression::default());
    let mut archive = tar::Builder::new(encoder);
    for (name, entry_type) in entries {
        let mut header = tar::Header::new_ustar();
        header.set_path(name).unwrap();
        header.set_size(0);
        header.set_mode(if entry_type.is_dir() { 0o755 } else { 0o644 });
        header.set_uid(0);
        header.set_gid(0);
        header.set_mtime(0);
        header.set_username("").unwrap();
        header.set_groupname("").unwrap();
        header.set_entry_type(*entry_type);
        header.set_cksum();
        archive.append(&header, &[][..]).unwrap();
    }
    archive.into_inner().unwrap().finish().unwrap()
}

fn replace_pending_archive(harness: &Harness, run_id: &str, bytes: &[u8]) {
    let pending = harness.pending_dir("review", run_id);
    fs::write(pending.join("archive.tar.gz"), bytes).unwrap();
    let retry_path = pending.join("retry.json");
    let mut retry: serde_json::Value =
        serde_json::from_slice(&fs::read(&retry_path).unwrap()).unwrap();
    retry["archive_sha256"] = serde_json::json!(format!("{:x}", Sha256::digest(bytes)));
    retry["archive_size"] = serde_json::json!(bytes.len());
    fs::write(retry_path, serde_json::to_vec(&retry).unwrap()).unwrap();
}

#[test]
fn start_recovers_the_main_model_from_the_active_transcript() {
    let mut harness = Harness::new();
    let home = harness.homes.state.parent().unwrap().to_path_buf();
    let project_key = harness.repo.to_str().unwrap().replace('/', "-");
    let project = home.join(".claude/projects").join(project_key);
    fs::create_dir_all(&project).unwrap();
    fs::write(
        project.join("session-1.jsonl"),
        b"{\"type\":\"user\"}\n{\"type\":\"assistant\",\"message\":{\"model\":\"claude-test\"}}\n",
    )
    .unwrap();
    harness
        .environment
        .insert("HOME".to_owned(), home.to_string_lossy().into_owned());
    harness
        .environment
        .insert("CLAUDE_CODE_SESSION_ID".to_owned(), "session-1".to_owned());

    let started = harness.start(&harness.local, "review", "model", None);
    let manifest: serde_json::Value =
        serde_json::from_slice(&fs::read(started.context.run_dir.join("manifest.json")).unwrap())
            .unwrap();

    assert_eq!(manifest["model_roster"]["main"], "claude-test");
}

#[tokio::test]
async fn every_terminal_outcome_publishes_the_required_envelope_artifacts() {
    let harness = Harness::new();
    let store = MemoryStore::default();
    for (run_id, outcome) in [
        ("success", LifecycleOutcome::Success),
        ("failure", LifecycleOutcome::Failure),
        ("cancelled", LifecycleOutcome::Cancelled),
        ("early", LifecycleOutcome::EarlyReturn),
    ] {
        let started = harness.start(&harness.enabled, "review", run_id, None);
        let result = finish(
            &FinishRequest {
                repo_root: &harness.repo,
                active_resolution: &harness.enabled,
                local_resolution: &harness.local,
                homes: &harness.homes,
                environment: &harness.environment,
                skill: "review",
                run_id,
                outcome,
                pre_scrub_violations: 0,
            },
            Some(&store),
        )
        .await
        .unwrap();
        let publication = result.publication.unwrap();
        assert_eq!(
            publication.remote_key,
            format!("run-logs/review/{run_id}.tar.gz")
        );
        assert!(publication.cache_dir.join("final-report.md").is_file());
        assert!(
            publication
                .cache_dir
                .join("archive-manifest.json")
                .is_file()
        );
        assert!(
            publication
                .cache_dir
                .join("execution-issues.ndjson")
                .is_file()
        );
        assert!(!started.context_file.exists());
        assert!(!started.context.run_dir.exists());
    }
    assert_eq!(store.keys().len(), 4);
}

#[tokio::test]
async fn nested_runs_keep_distinct_identity_and_archives() {
    let harness = Harness::new();
    let store = MemoryStore::default();
    let parent = harness.start(&harness.enabled, "design", "parent", None);
    let child = harness.start(
        &harness.enabled,
        "review",
        "child",
        Some(&parent.context_file),
    );
    let child_manifest: serde_json::Value =
        serde_json::from_slice(&fs::read(child.context.run_dir.join("manifest.json")).unwrap())
            .unwrap();
    assert_eq!(child_manifest["parent_skill"], "design");
    assert_eq!(child_manifest["parent_run_id"], "parent");
    for (skill, run_id) in [("review", "child"), ("design", "parent")] {
        finish(
            &FinishRequest {
                repo_root: &harness.repo,
                active_resolution: &harness.enabled,
                local_resolution: &harness.local,
                homes: &harness.homes,
                environment: &harness.environment,
                skill,
                run_id,
                outcome: LifecycleOutcome::Success,
                pre_scrub_violations: 0,
            },
            Some(&store),
        )
        .await
        .unwrap();
    }
    assert_eq!(
        store.keys(),
        vec![
            format!(
                "{}/run-logs/design/parent.tar.gz",
                harness.enabled.storage().unwrap().prefix()
            ),
            format!(
                "{}/run-logs/review/child.tar.gz",
                harness.enabled.storage().unwrap().prefix()
            ),
        ]
    );
}

#[tokio::test]
async fn disabled_context_remains_local_after_configuration_appears() {
    let harness = Harness::new();
    for (run_id, outcome) in [
        ("local-success", LifecycleOutcome::Success),
        ("local-failure", LifecycleOutcome::Failure),
        ("local-cancelled", LifecycleOutcome::Cancelled),
        ("local-early", LifecycleOutcome::EarlyReturn),
    ] {
        let started = harness.start(&harness.local, "review", run_id, None);
        let rehydrated = load(
            &harness.repo,
            "review",
            run_id,
            &harness.enabled,
            &harness.local,
            &harness.homes,
        )
        .unwrap();
        assert_eq!(rehydrated.resolution.mode(), RunLogStorageMode::Disabled);
        let result = finish(
            &FinishRequest {
                repo_root: &harness.repo,
                active_resolution: &harness.enabled,
                local_resolution: &harness.local,
                homes: &harness.homes,
                environment: &harness.environment,
                skill: "review",
                run_id,
                outcome,
                pre_scrub_violations: 0,
            },
            None,
        )
        .await
        .unwrap();
        assert_eq!(result.outcome, outcome);
        assert!(result.publication.is_none());
        assert!(!started.context_file.exists());
        assert!(!started.context.run_dir.exists());
    }
}

#[test]
fn adoption_rehydrates_explicit_log_root_without_inherited_parent_state() {
    let harness = Harness::new();
    let parent = harness.start(&harness.enabled, "design", "parent-adopt", None);
    let explicit_root = harness.repo.join("café-larch-logs");
    let child = start(&StartRequest {
        repo_root: &harness.repo,
        resolution: &harness.enabled,
        local_resolution: &harness.local,
        homes: &harness.homes,
        environment: &harness.environment,
        skill: "review",
        run_id: Some("child-adopt"),
        log_root: Some(&explicit_root),
        parent_skill: "",
        parent_run_id: "",
        parent_context: Some(&parent.context_file),
        issue: "8077",
        adopt_existing: false,
    })
    .unwrap();
    let context_text = fs::read_to_string(&child.context_file).unwrap();
    assert!(
        context_text
            .starts_with("{\"client_repo\":\"client\",\"local_namespace_id\":null,\"log_root\":")
    );
    assert!(context_text.contains("caf\\u00e9-larch-logs"));
    assert!(context_text.ends_with("\"tool_repo_uri\":\"gs://bucket/larch/client\"}\n"));
    assert_eq!(context_text.lines().count(), 1);

    let adopted = load(
        &harness.repo,
        "review",
        "child-adopt",
        &harness.enabled,
        &harness.local,
        &harness.homes,
    )
    .unwrap();

    assert_eq!(adopted.context, child.context);
    assert_eq!(adopted.context_file, child.context_file);
}

#[test]
fn ordinary_adoption_rejects_an_omitted_existing_parent() {
    let harness = Harness::new();
    let parent = harness.start(&harness.enabled, "design", "strict-parent", None);
    let child = harness.start(
        &harness.enabled,
        "review",
        "strict-child",
        Some(&parent.context_file),
    );

    let result = start(&StartRequest {
        repo_root: &harness.repo,
        resolution: &harness.enabled,
        local_resolution: &harness.local,
        homes: &harness.homes,
        environment: &harness.environment,
        skill: "review",
        run_id: Some("strict-child"),
        log_root: None,
        parent_skill: "",
        parent_run_id: "",
        parent_context: None,
        issue: "",
        adopt_existing: true,
    });

    assert!(result.is_err());
    assert!(child.context_file.is_file());
}

#[tokio::test]
async fn manifest_storage_drift_fails_before_terminal_artifacts() {
    let harness = Harness::new();
    let started = harness.start(&harness.enabled, "review", "manifest-drift", None);
    let manifest_path = started.context.run_dir.join("manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&fs::read(&manifest_path).unwrap()).unwrap();
    manifest["tool_repo_uri"] = serde_json::json!("gs://other/larch/client");
    fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();

    let result = finish(
        &FinishRequest {
            repo_root: &harness.repo,
            active_resolution: &harness.enabled,
            local_resolution: &harness.local,
            homes: &harness.homes,
            environment: &harness.environment,
            skill: "review",
            run_id: "manifest-drift",
            outcome: LifecycleOutcome::Failure,
            pre_scrub_violations: 0,
        },
        Some(&MemoryStore::default()),
    )
    .await;
    assert!(result.is_err());
    assert!(!started.context.run_dir.join("final-report.md").exists());
}

#[tokio::test]
async fn failed_upload_retains_pending_state_and_retries_without_shell_state() {
    let harness = Harness::new();
    let store = MemoryStore::fail_once();
    let started = harness.start(&harness.enabled, "review", "retry", None);
    let result_path = started.context.run_dir.join("result.txt");
    fs::write(&result_path, b"published snapshot\n").unwrap();
    let request = FinishRequest {
        repo_root: &harness.repo,
        active_resolution: &harness.enabled,
        local_resolution: &harness.local,
        homes: &harness.homes,
        environment: &harness.environment,
        skill: "review",
        run_id: "retry",
        outcome: LifecycleOutcome::Failure,
        pre_scrub_violations: 0,
    };
    assert!(finish(&request, Some(&store)).await.is_err());
    assert!(started.context_file.is_file());
    assert!(started.context.run_dir.is_dir());
    assert!(
        harness
            .homes
            .state
            .join("larch/run-log-pending/v2/client")
            .is_dir()
    );
    fs::write(&result_path, b"later mutable staging\n").unwrap();
    let retried = finish(&request, Some(&store)).await.unwrap();
    let cache_dir = retried.publication.unwrap().cache_dir;
    assert_eq!(
        fs::read_to_string(cache_dir.join("result.txt")).unwrap(),
        "published snapshot\n"
    );
    assert_eq!(store.keys().len(), 1);
}

#[tokio::test]
async fn successful_upload_metadata_is_verified() {
    let harness = Harness::new();
    let store = MemoryStore::mismatched_upload_metadata();
    let started = harness.start(&harness.enabled, "review", "corrupt-remote", None);
    let result = finish(
        &FinishRequest {
            repo_root: &harness.repo,
            active_resolution: &harness.enabled,
            local_resolution: &harness.local,
            homes: &harness.homes,
            environment: &harness.environment,
            skill: "review",
            run_id: "corrupt-remote",
            outcome: LifecycleOutcome::Success,
            pre_scrub_violations: 0,
        },
        Some(&store),
    )
    .await;
    assert!(result.is_err());
    assert!(started.context_file.is_file());
    assert!(started.context.run_dir.is_dir());
}

#[tokio::test]
async fn required_specialized_artifact_must_exist_or_have_a_durable_waiver() {
    let harness = Harness::new();
    let store = MemoryStore::default();
    let started = harness.start(&harness.enabled, "implement", "completeness", None);
    fs::write(
        started.context.run_dir.join("code-review-tally.json"),
        b"{}\n",
    )
    .unwrap();
    let request = FinishRequest {
        repo_root: &harness.repo,
        active_resolution: &harness.enabled,
        local_resolution: &harness.local,
        homes: &harness.homes,
        environment: &harness.environment,
        skill: "implement",
        run_id: "completeness",
        outcome: LifecycleOutcome::Failure,
        pre_scrub_violations: 0,
    };
    let error = finish(&request, Some(&store)).await.unwrap_err();
    assert!(error.to_string().contains("review-findings-full.jsonl"));
    assert!(store.keys().is_empty());

    let issues = started.context.run_dir.join("execution-issues.ndjson");
    let mut contents = fs::read_to_string(&issues).unwrap();
    contents.push_str(
        "{\"category\":\"Warnings\",\"body\":\"review-findings-full.jsonl was unavailable\"}\n",
    );
    fs::write(issues, contents).unwrap();
    assert!(
        finish(&request, Some(&store))
            .await
            .unwrap()
            .publication
            .is_some()
    );
}

#[tokio::test]
async fn secrets_are_scrubbed_before_archive_and_cache_publication() {
    let harness = Harness::new();
    let store = MemoryStore::default();
    let started = harness.start(&harness.enabled, "review", "redaction", None);
    let secret = format!("ghp_{}", "A".repeat(24));
    fs::write(
        started.context.run_dir.join("session-transcript.jsonl"),
        format!("{{\"token\":\"{secret}\"}}\n"),
    )
    .unwrap();
    let result = finish(
        &FinishRequest {
            repo_root: &harness.repo,
            active_resolution: &harness.enabled,
            local_resolution: &harness.local,
            homes: &harness.homes,
            environment: &harness.environment,
            skill: "review",
            run_id: "redaction",
            outcome: LifecycleOutcome::Success,
            pre_scrub_violations: 0,
        },
        Some(&store),
    )
    .await
    .unwrap();
    assert_eq!(result.secret_scrub_violations, 1);
    let publication = result.publication.unwrap();
    let cached =
        fs::read_to_string(publication.cache_dir.join("session-transcript.jsonl")).unwrap();
    assert!(cached.contains("<REDACTED-TOKEN>"));
    assert!(!cached.contains(&secret));
    let object_key = format!(
        "{}/{}",
        harness.enabled.storage().unwrap().prefix(),
        publication.remote_key
    );
    let mut expanded = Vec::new();
    GzDecoder::new(store.object(&object_key).as_slice())
        .read_to_end(&mut expanded)
        .unwrap();
    assert!(!String::from_utf8_lossy(&expanded).contains(&secret));
}

#[tokio::test]
async fn breadcrumb_replacement_does_not_publish_transaction_artifacts() {
    let mut harness = Harness::new();
    let session = harness.repo.parent().unwrap().to_path_buf();
    let log_root = session.join("larch-logs");
    harness.environment.insert(
        "IMPLEMENT_TMPDIR".to_owned(),
        session.to_string_lossy().into_owned(),
    );
    let started = start(&StartRequest {
        repo_root: &harness.repo,
        resolution: &harness.enabled,
        local_resolution: &harness.local,
        homes: &harness.homes,
        environment: &harness.environment,
        skill: "review",
        run_id: Some("breadcrumbs"),
        log_root: Some(&log_root),
        parent_skill: "",
        parent_run_id: "",
        parent_context: None,
        issue: "8077",
        adopt_existing: false,
    })
    .unwrap();
    fs::create_dir(started.context.run_dir.join("breadcrumbs")).unwrap();
    fs::write(
        started.context.run_dir.join("breadcrumbs/stale.txt"),
        b"stale\n",
    )
    .unwrap();
    fs::write(
        session.join("larch-quiet-review-1.log"),
        b"current breadcrumb\n",
    )
    .unwrap();

    let result = finish(
        &FinishRequest {
            repo_root: &harness.repo,
            active_resolution: &harness.enabled,
            local_resolution: &harness.local,
            homes: &harness.homes,
            environment: &harness.environment,
            skill: "review",
            run_id: "breadcrumbs",
            outcome: LifecycleOutcome::Success,
            pre_scrub_violations: 0,
        },
        Some(&MemoryStore::default()),
    )
    .await
    .unwrap();
    let cache = result.publication.unwrap().cache_dir;
    assert!(!cache.join("breadcrumbs/stale.txt").exists());
    assert!(
        fs::read_to_string(cache.join("breadcrumbs/quiet.log"))
            .unwrap()
            .contains("current breadcrumb")
    );
    assert!(fs::read_dir(log_root.join("review")).unwrap().all(|entry| {
        !entry
            .unwrap()
            .file_name()
            .to_string_lossy()
            .starts_with('.')
    }));
}

#[tokio::test]
async fn archive_supports_normalized_utf8_paths_beyond_the_base_header() {
    let harness = Harness::new();
    let store = MemoryStore::default();
    let started = harness.start(&harness.enabled, "review", "pax", None);
    let long_name = format!("{}.txt", "é".repeat(55));
    fs::write(started.context.run_dir.join(&long_name), b"unicode path\n").unwrap();
    let result = finish(
        &FinishRequest {
            repo_root: &harness.repo,
            active_resolution: &harness.enabled,
            local_resolution: &harness.local,
            homes: &harness.homes,
            environment: &harness.environment,
            skill: "review",
            run_id: "pax",
            outcome: LifecycleOutcome::Success,
            pre_scrub_violations: 0,
        },
        Some(&store),
    )
    .await
    .unwrap();
    let publication = result.publication.unwrap();
    assert!(publication.cache_dir.join(&long_name).is_file());
    let object_key = format!(
        "{}/{}",
        harness.enabled.storage().unwrap().prefix(),
        publication.remote_key
    );
    let object = store.object(&object_key);
    let mut archive = tar::Archive::new(GzDecoder::new(object.as_slice()));
    let paths: Vec<_> = archive
        .entries()
        .unwrap()
        .map(|entry| entry.unwrap().path().unwrap().into_owned())
        .collect();
    assert!(paths.contains(&PathBuf::from(long_name)));
}

#[tokio::test]
async fn archive_rejects_backslashes_and_full_unicode_casefold_collisions() {
    let harness = Harness::new();
    let store = MemoryStore::default();
    let backslash = harness.start(&harness.enabled, "review", "backslash", None);
    fs::write(backslash.context.run_dir.join("bad\\name.txt"), b"unsafe\n").unwrap();
    let request = |run_id| FinishRequest {
        repo_root: &harness.repo,
        active_resolution: &harness.enabled,
        local_resolution: &harness.local,
        homes: &harness.homes,
        environment: &harness.environment,
        skill: "review",
        run_id,
        outcome: LifecycleOutcome::Success,
        pre_scrub_violations: 0,
    };
    assert!(finish(&request("backslash"), Some(&store)).await.is_err());

    let collision = harness.start(&harness.enabled, "review", "casefold", None);
    fs::write(collision.context.run_dir.join("Maße.txt"), b"first\n").unwrap();
    fs::write(collision.context.run_dir.join("MASSE.txt"), b"second\n").unwrap();
    let distinct_casefold_entries = fs::read_dir(&collision.context.run_dir)
        .unwrap()
        .filter_map(Result::ok)
        .filter(|entry| matches!(entry.file_name().to_str(), Some("Maße.txt" | "MASSE.txt")))
        .count()
        == 2;
    if distinct_casefold_entries {
        assert!(finish(&request("casefold"), Some(&store)).await.is_err());
    }
    assert!(store.keys().is_empty());
}

#[test]
fn admission_rejects_invalid_issue_log_root_duplicate_and_adoption_drift() {
    let harness = Harness::new();

    let mut invalid_issue = harness.request(&harness.enabled, "review", "invalid-issue");
    invalid_issue.issue = "80x77";
    assert!(
        start(&invalid_issue)
            .unwrap_err()
            .to_string()
            .contains("invalid issue")
    );

    let relative_root = Path::new("relative-logs");
    let mut relative = harness.request(&harness.enabled, "review", "relative-root");
    relative.log_root = Some(relative_root);
    assert!(
        start(&relative)
            .unwrap_err()
            .to_string()
            .contains("log root must be absolute")
    );

    harness.start(&harness.enabled, "review", "duplicate", None);
    assert!(
        start(&harness.request(&harness.enabled, "review", "duplicate"))
            .unwrap_err()
            .to_string()
            .contains("run ID already exists")
    );

    let adopted = harness.start(&harness.enabled, "review", "adopt-root", None);
    let different_root = harness.repo.join("different-logs");
    let mut wrong_root = harness.request(&harness.enabled, "review", "adopt-root");
    wrong_root.log_root = Some(&different_root);
    wrong_root.adopt_existing = true;
    assert!(
        start(&wrong_root)
            .unwrap_err()
            .to_string()
            .contains("does not match requested log root")
    );

    let manifest_path = adopted.context.run_dir.join("manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&fs::read(&manifest_path).unwrap()).unwrap();
    manifest["lifecycle_schema_version"] = serde_json::json!(999);
    fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();
    let mut drifted = harness.request(&harness.enabled, "review", "adopt-root");
    drifted.adopt_existing = true;
    assert!(
        start(&drifted)
            .unwrap_err()
            .to_string()
            .contains("publication or repository identity changed")
    );
}

#[test]
fn parent_and_context_lookup_fail_closed_for_ambiguous_or_missing_state() {
    let harness = Harness::new();
    let parent = harness.start(&harness.enabled, "design", "parent-validation", None);

    let mut ambiguous = harness.request(&harness.enabled, "review", "ambiguous-parent");
    ambiguous.parent_skill = "design";
    ambiguous.parent_run_id = "parent-validation";
    ambiguous.parent_context = Some(&parent.context_file);
    assert!(
        start(&ambiguous)
            .unwrap_err()
            .to_string()
            .contains("cannot be combined")
    );

    let relative_context = Path::new("context.json");
    let mut relative = harness.request(&harness.enabled, "review", "relative-parent");
    relative.parent_context = Some(relative_context);
    assert!(
        start(&relative)
            .unwrap_err()
            .to_string()
            .contains("missing or unsafe")
    );

    let copied_context = harness.repo.join("copied-parent-context.json");
    fs::copy(&parent.context_file, &copied_context).unwrap();
    let mut copied = harness.request(&harness.enabled, "review", "copied-parent");
    copied.parent_context = Some(&copied_context);
    assert!(
        start(&copied)
            .unwrap_err()
            .to_string()
            .contains("parent lifecycle context path mismatch")
    );

    assert!(
        has_persisted_context(
            &harness.homes,
            &harness.enabled,
            &harness.local,
            "design",
            "parent-validation",
        )
        .unwrap()
    );
    assert!(
        !has_persisted_context(
            &harness.homes,
            &harness.local,
            &harness.local,
            "review",
            "missing",
        )
        .unwrap()
    );
    assert!(
        load(
            &harness.repo,
            "review",
            "missing",
            &harness.enabled,
            &harness.local,
            &harness.homes,
        )
        .unwrap_err()
        .to_string()
        .contains("lifecycle context is missing or unsafe")
    );
}

fn validation_context(harness: &Harness) -> LifecycleContext {
    LifecycleContext::new(
        harness.repo.clone(),
        &harness.enabled,
        "review".to_owned(),
        "context-validation".to_owned(),
        harness.repo.join("logs"),
    )
}

#[test]
fn persisted_context_validation_rejects_identity_path_and_mode_drift() {
    let harness = Harness::new();
    let context = validation_context(&harness);
    assert_eq!(
        context
            .validate(
                &harness.repo,
                "review",
                "context-validation",
                &harness.enabled,
                &harness.local,
            )
            .unwrap(),
        harness.enabled
    );

    let mut wrong_identity = context.clone();
    wrong_identity.schema_version = 0;
    assert!(
        wrong_identity
            .validate(
                &harness.repo,
                "review",
                "context-validation",
                &harness.enabled,
                &harness.local,
            )
            .unwrap_err()
            .to_string()
            .contains("identity mismatch")
    );

    let mut wrong_path = context.clone();
    wrong_path.run_dir = harness.repo.join("elsewhere");
    assert!(
        wrong_path
            .validate(
                &harness.repo,
                "review",
                "context-validation",
                &harness.enabled,
                &harness.local,
            )
            .unwrap_err()
            .to_string()
            .contains("staging path mismatch")
    );

    let mut unknown_mode = context;
    unknown_mode.publication_mode = "unknown".to_owned();
    assert!(
        unknown_mode
            .validate(
                &harness.repo,
                "review",
                "context-validation",
                &harness.enabled,
                &harness.local,
            )
            .unwrap_err()
            .to_string()
            .contains("publication identity are missing")
    );
}

#[test]
fn persisted_context_validation_rejects_storage_drift() {
    let harness = Harness::new();
    let context = validation_context(&harness);
    let drifted_storage = injected_storage_resolution(ToolRepositoryStorage::new(
        StorageBase::new("gs", "different-bucket"),
        "client",
    ));
    assert!(
        context
            .validate(
                &harness.repo,
                "review",
                "context-validation",
                &drifted_storage,
                &harness.local,
            )
            .unwrap_err()
            .to_string()
            .contains("configured storage or Git origin changed")
    );
    assert!(
        context
            .validate(
                &harness.repo,
                "review",
                "context-validation",
                &harness.local,
                &harness.local,
            )
            .unwrap_err()
            .to_string()
            .contains("disabled lifecycle context identity mismatch")
    );
}

#[test]
fn persisted_context_validation_preserves_and_checks_disabled_reasons() {
    let harness = Harness::new();
    for reason in [
        RunLogStorageReason::LarchTableMissing,
        RunLogStorageReason::StorageBaseUriOmitted,
    ] {
        let resolution = RunLogStorageResolution::new(
            RunLogStorageMode::Disabled,
            reason,
            None,
            "client",
            Some("local-id".to_owned()),
        )
        .unwrap();
        let disabled = LifecycleContext::new(
            harness.repo.clone(),
            &resolution,
            "review".to_owned(),
            "disabled-reason".to_owned(),
            harness.repo.join("disabled-logs"),
        );
        assert_eq!(
            disabled
                .validate(
                    &harness.repo,
                    "review",
                    "disabled-reason",
                    &harness.enabled,
                    &harness.local,
                )
                .unwrap()
                .reason(),
            reason
        );
    }

    let mut disabled = LifecycleContext::new(
        harness.repo.clone(),
        &harness.local,
        "review".to_owned(),
        "disabled-invalid".to_owned(),
        harness.repo.join("disabled-logs"),
    );
    disabled.client_repo = "different-client".to_owned();
    assert!(
        disabled
            .validate(
                &harness.repo,
                "review",
                "disabled-invalid",
                &harness.enabled,
                &harness.local,
            )
            .is_err()
    );
    disabled.client_repo = "client".to_owned();
    disabled.storage_resolution_reason = "unknown".to_owned();
    assert!(
        disabled
            .validate(
                &harness.repo,
                "review",
                "disabled-invalid",
                &harness.enabled,
                &harness.local,
            )
            .is_err()
    );
}

#[test]
fn adoption_repairs_legacy_manifests_and_reconciles_context_creation_races() {
    let harness = Harness::new();
    let existing = harness.start(&harness.enabled, "review", "adopt-success", None);
    let mut adoption = harness.request(&harness.enabled, "review", "adopt-success");
    adoption.adopt_existing = true;
    assert_eq!(start(&adoption).unwrap().context, existing.context);

    let manifest_path = existing.context.run_dir.join("manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&fs::read(&manifest_path).unwrap()).unwrap();
    manifest
        .as_object_mut()
        .unwrap()
        .remove("lifecycle_schema_version");
    fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();
    start(&adoption).unwrap();
    let repaired: serde_json::Value =
        serde_json::from_slice(&fs::read(&manifest_path).unwrap()).unwrap();
    assert_eq!(repaired["lifecycle_schema_version"], 3);

    manifest = repaired;
    manifest["client_repo"] = serde_json::json!("different-client");
    fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();
    assert!(
        start(&adoption)
            .unwrap_err()
            .to_string()
            .contains("publication or repository identity changed")
    );

    let raced = harness.start(&harness.enabled, "review", "context-race", None);
    fs::remove_dir_all(&raced.context.run_dir).unwrap();
    assert_eq!(
        start(&harness.request(&harness.enabled, "review", "context-race"))
            .unwrap()
            .context,
        raced.context
    );

    let explicit_root = harness.repo.join("explicit-race-logs");
    let mut explicit = harness.request(&harness.enabled, "review", "context-mismatch");
    explicit.log_root = Some(&explicit_root);
    let explicit = start(&explicit).unwrap();
    fs::remove_dir_all(&explicit.context.run_dir).unwrap();
    assert!(
        start(&harness.request(&harness.enabled, "review", "context-mismatch"))
            .unwrap_err()
            .to_string()
            .contains("existing lifecycle context does not match adoption")
    );
}

#[test]
fn transcript_fallback_skips_invalid_records_and_selects_the_latest_candidate() {
    let mut harness = Harness::new();
    let home = harness.homes.state.parent().unwrap().to_path_buf();
    let project_key = harness.repo.to_str().unwrap().replace('/', "-");
    let project = home.join(".claude/projects").join(project_key);
    fs::create_dir_all(&project).unwrap();
    fs::write(
        project.join("fallback.jsonl"),
        concat!(
            "{\"assistant\":\n",
            "{\"type\":\"tool\",\"message\":{\"model\":\"assistant\"}}\n",
            "{\"type\":\"assistant\",\"message\":{\"model\":\"\"}}\n",
            "{\"type\":\"assistant\",\"message\":{\"model\":\"fallback-model\"}}\n",
        ),
    )
    .unwrap();
    harness
        .environment
        .insert("HOME".to_owned(), home.to_string_lossy().into_owned());

    let started = harness.start(&harness.local, "review", "fallback-model", None);
    let manifest: serde_json::Value =
        serde_json::from_slice(&fs::read(started.context.run_dir.join("manifest.json")).unwrap())
            .unwrap();
    assert_eq!(manifest["model_roster"]["main"], "fallback-model");
}

#[tokio::test]
async fn existing_remote_object_reconciles_after_local_cache_failure() {
    let harness = Harness::new();
    harness.start(&harness.enabled, "review", "remote-reconcile", None);
    let cache = harness.cache_dir("review", "remote-reconcile");
    fs::create_dir_all(&cache).unwrap();
    let store = MemoryStore::default();
    let request = finish_request(&harness, "remote-reconcile");

    assert!(finish(&request, Some(&store)).await.is_err());
    assert_eq!(store.keys().len(), 1);
    fs::remove_dir_all(&cache).unwrap();
    let result = finish(&request, Some(&store)).await.unwrap();
    assert_eq!(result.publication.unwrap().cache_dir, cache);
    assert!(cache.join("archive-manifest.json").is_file());
}

#[tokio::test]
async fn pending_retry_rejects_missing_files_and_identity_drift() {
    let harness = Harness::new();

    harness.start(&harness.enabled, "review", "pending-missing", None);
    let missing_request = finish_request(&harness, "pending-missing");
    assert!(
        finish(&missing_request, Some(&MemoryStore::fail_once()))
            .await
            .is_err()
    );
    fs::remove_file(
        harness
            .pending_dir("review", "pending-missing")
            .join("archive.tar.gz"),
    )
    .unwrap();
    assert!(
        finish(&missing_request, Some(&MemoryStore::default()))
            .await
            .is_err()
    );

    harness.start(&harness.enabled, "review", "pending-drift", None);
    let drift_request = finish_request(&harness, "pending-drift");
    assert!(
        finish(&drift_request, Some(&MemoryStore::fail_once()))
            .await
            .is_err()
    );
    let retry_path = harness
        .pending_dir("review", "pending-drift")
        .join("retry.json");
    let mut retry: serde_json::Value =
        serde_json::from_slice(&fs::read(&retry_path).unwrap()).unwrap();
    retry["client_repo"] = serde_json::json!("different-client");
    fs::write(retry_path, serde_json::to_vec(&retry).unwrap()).unwrap();
    assert!(
        finish(&drift_request, Some(&MemoryStore::default()))
            .await
            .is_err()
    );
}

#[tokio::test]
async fn pending_retry_rejects_unsafe_ordered_and_case_colliding_archives() {
    let harness = Harness::new();
    let cases = [
        (
            "unsafe-type",
            archive_bytes(&[("unsafe-link", tar::EntryType::Symlink)]),
        ),
        (
            "bad-order",
            archive_bytes(&[
                ("b", tar::EntryType::Regular),
                ("a", tar::EntryType::Regular),
            ]),
        ),
        (
            "case-collision",
            archive_bytes(&[
                ("A", tar::EntryType::Regular),
                ("a", tar::EntryType::Regular),
            ]),
        ),
    ];
    for (run_id, archive) in cases {
        harness.start(&harness.enabled, "review", run_id, None);
        let request = finish_request(&harness, run_id);
        assert!(
            finish(&request, Some(&MemoryStore::fail_once()))
                .await
                .is_err()
        );
        replace_pending_archive(&harness, run_id, &archive);
        assert!(
            finish(&request, Some(&MemoryStore::default()))
                .await
                .is_err()
        );
    }
}

#[tokio::test]
async fn terminalization_rejects_schema_finished_at_and_context_corruption() {
    let harness = Harness::new();

    let schema = harness.start(&harness.enabled, "review", "schema-drift", None);
    let schema_manifest = schema.context.run_dir.join("manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&fs::read(&schema_manifest).unwrap()).unwrap();
    manifest["lifecycle_schema_version"] = serde_json::json!(999);
    fs::write(&schema_manifest, serde_json::to_vec(&manifest).unwrap()).unwrap();
    assert!(
        finish(
            &finish_request(&harness, "schema-drift"),
            Some(&MemoryStore::default())
        )
        .await
        .unwrap_err()
        .to_string()
        .contains("unsupported or missing lifecycle schema version")
    );

    let finished = harness.start(&harness.enabled, "review", "finished-at", None);
    let finished_manifest = finished.context.run_dir.join("manifest.json");
    manifest = serde_json::from_slice(&fs::read(&finished_manifest).unwrap()).unwrap();
    manifest["finished_at"] = serde_json::json!(42);
    fs::write(&finished_manifest, serde_json::to_vec(&manifest).unwrap()).unwrap();
    assert!(
        finish(
            &finish_request(&harness, "finished-at"),
            Some(&MemoryStore::default())
        )
        .await
        .unwrap_err()
        .to_string()
        .contains("finished_at is invalid")
    );

    let context = harness.start(&harness.enabled, "review", "context-json", None);
    fs::write(&context.context_file, b"{").unwrap();
    assert!(
        load(
            &harness.repo,
            "review",
            "context-json",
            &harness.enabled,
            &harness.local,
            &harness.homes,
        )
        .unwrap_err()
        .to_string()
        .contains("must be valid JSON")
    );
}
