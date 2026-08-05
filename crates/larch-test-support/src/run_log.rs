//! Isolated run-log fixtures, report snapshots, and a reporting parity oracle.
//!
//! Test-only helpers. Builds offline corpora under owned temporary roots and never
//! changes process-global environment or working directory.

use std::{
    collections::BTreeMap,
    fmt::{self, Write as _},
    fs, io,
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};

#[cfg(unix)]
use std::os::unix::{ffi::OsStrExt, fs::PermissionsExt};

use crate::{
    BoundedBytes, ExecutionSnapshot, SnapshotEntry, SnapshotEntryKind, TestWorkspace,
    filesystem::validate_relative,
};

const SNAPSHOT_ENTRY_LIMIT: usize = 4096;
const RUN_LOG_SNAPSHOT_SCHEMA: u32 = 1;
const REPORT_SNAPSHOT_SCHEMA: u32 = 1;
const DEFAULT_RUN_ID: &str = "11111111-2222-4333-8444-555555555555";
const DEFAULT_SKILL: &str = "implement";
const STORAGE_ORIGIN_ID: &str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

/// Named run-log corpus shape used by differential reporting tests.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RunLogFixture {
    Absent,
    PartialStaging,
    CorruptManifest,
    CommittedTerminal,
    CheckpointFlush,
    FlushInterrupted,
    ArchivePending,
    HistoricalManifestV1,
    HistoricalLifecycleV1,
    HistoricalPanelPromptLegacy,
    TokenTimingProgress,
    TranscriptCredentials,
    BatchCorpusLayout,
}

/// Durability class inferred from markers and required artifacts.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DurabilityState {
    Absent,
    Partial,
    Corrupt,
    Checkpoint,
    Interrupted,
    PendingPublication,
    Committed,
}

/// Builder for an isolated run-log tree under an owned temporary root.
#[derive(Clone, Debug)]
pub struct RunLogTreeBuilder {
    fixture: RunLogFixture,
    skill: String,
    run_id: String,
    client_repo: String,
}

impl RunLogTreeBuilder {
    #[must_use]
    pub fn new(fixture: RunLogFixture) -> Self {
        Self {
            fixture,
            skill: DEFAULT_SKILL.to_owned(),
            run_id: DEFAULT_RUN_ID.to_owned(),
            client_repo: "larch".to_owned(),
        }
    }

    #[must_use]
    pub fn skill(mut self, skill: impl Into<String>) -> Self {
        self.skill = skill.into();
        self
    }

    #[must_use]
    pub fn run_id(mut self, run_id: impl Into<String>) -> Self {
        self.run_id = run_id.into();
        self
    }

    #[must_use]
    pub fn client_repo(mut self, client_repo: impl Into<String>) -> Self {
        self.client_repo = client_repo.into();
        self
    }

    /// Build the named fixture without touching process-global state.
    ///
    /// # Errors
    /// Returns filesystem or path-validation errors.
    pub fn build(self) -> io::Result<RunLogTree> {
        let tree = RunLogTree {
            workspace: TestWorkspace::new()?,
            skill: self.skill,
            run_id: self.run_id,
            client_repo: self.client_repo,
        };
        tree.materialize(self.fixture)?;
        Ok(tree)
    }
}

/// Owned run-log staging, cache, pending, and object-store roots.
#[derive(Debug)]
pub struct RunLogTree {
    workspace: TestWorkspace,
    skill: String,
    run_id: String,
    client_repo: String,
}

impl RunLogTree {
    #[must_use]
    pub fn builder(fixture: RunLogFixture) -> RunLogTreeBuilder {
        RunLogTreeBuilder::new(fixture)
    }

    #[must_use]
    pub const fn workspace(&self) -> &TestWorkspace {
        &self.workspace
    }

    #[must_use]
    pub fn root(&self) -> &Path {
        self.workspace.root()
    }

    #[must_use]
    pub fn skill(&self) -> &str {
        &self.skill
    }

    #[must_use]
    pub fn run_id(&self) -> &str {
        &self.run_id
    }

    #[must_use]
    pub fn staging_root(&self) -> PathBuf {
        self.root().join("larch-logs")
    }

    #[must_use]
    pub fn run_dir(&self) -> PathBuf {
        self.staging_root().join(&self.skill).join(&self.run_id)
    }

    #[must_use]
    pub fn cache_run_dir(&self) -> PathBuf {
        self.root()
            .join("cache/run-logs/v2")
            .join(&self.client_repo)
            .join(STORAGE_ORIGIN_ID)
            .join(&self.skill)
            .join(&self.run_id)
    }

    #[must_use]
    pub fn pending_run_dir(&self) -> PathBuf {
        self.root()
            .join("state/run-log-pending/v2")
            .join(&self.client_repo)
            .join(STORAGE_ORIGIN_ID)
            .join(&self.skill)
            .join(&self.run_id)
    }

    #[must_use]
    pub fn object_store(&self) -> LocalObjectStore {
        LocalObjectStore {
            root: self.root().join("object-store"),
        }
    }

    fn materialize(&self, fixture: RunLogFixture) -> io::Result<()> {
        match fixture {
            RunLogFixture::Absent => Ok(()),
            RunLogFixture::PartialStaging => self.write_partial(),
            RunLogFixture::CorruptManifest => self.write_corrupt_manifest(),
            RunLogFixture::CommittedTerminal => self.write_committed(true),
            RunLogFixture::CheckpointFlush => self.write_checkpoint(),
            RunLogFixture::FlushInterrupted => self.write_interrupted(),
            RunLogFixture::ArchivePending => self.write_archive_pending(),
            RunLogFixture::HistoricalManifestV1 => self.write_historical_manifest_v1(),
            RunLogFixture::HistoricalLifecycleV1 => self.write_historical_lifecycle_v1(),
            RunLogFixture::HistoricalPanelPromptLegacy => self.write_panel_prompt_legacy(),
            RunLogFixture::TokenTimingProgress => self.write_token_timing_progress(),
            RunLogFixture::TranscriptCredentials => self.write_transcript_credentials(),
            RunLogFixture::BatchCorpusLayout => self.write_batch_corpus(),
        }
    }

    fn write_corrupt_manifest(&self) -> io::Result<()> {
        self.write_partial()?;
        self.put("manifest.json", "{not-json\n")?;
        self.put(".durability", "state=corrupt\nflush=none\n")
    }

    fn write_interrupted(&self) -> io::Result<()> {
        self.write_checkpoint()?;
        self.put(
            "final-summary.md",
            "## /implement \u{2014} shipping\n\npartial summary before interrupt\n",
        )?;
        self.put(
            ".durability",
            "state=interrupted\nflush=partial\ninterrupt=signal\n",
        )
    }

    fn write_historical_manifest_v1(&self) -> io::Result<()> {
        self.put(
            "manifest.json",
            &format!(
                "{{\"status\":\"done\",\"version\":\"1\",\"run_id\":\"{}\",\"steps_ran\":{{\"0\":\"ok\"}},\
                 \"created_at\":\"2026-01-02T03:04:05Z\",\"updated_at\":\"2026-01-02T03:05:06Z\",\"skill\":\"{}\"}}\n",
                self.run_id, self.skill
            ),
        )?;
        self.put(
            "final-summary.md",
            "## /implement \u{2014} pr-created\n\nhistorical v1 summary\n",
        )?;
        self.put(".durability", "state=committed\nformat=manifest-v1\n")
    }

    fn write_historical_lifecycle_v1(&self) -> io::Result<()> {
        self.put(
            "manifest.json",
            &manifest_v2(
                &self.skill,
                &self.run_id,
                "done",
                1,
                r#""0":"ok""#,
                ",\"publication_mode\":\"enabled\"",
            ),
        )?;
        self.put(
            "final-summary.md",
            "## /implement: bailed\n\nPR https://github.com/character-ai/larch/pull/7\n",
        )?;
        self.put(".durability", "state=committed\nformat=lifecycle-v1\n")
    }

    fn write_panel_prompt_legacy(&self) -> io::Result<()> {
        self.write_partial()?;
        self.put(
            "round-1/panel-prompt-sizes.tsv",
            "site\tphase\tround_num\tslot\tslot_kind\ttool\toutput\tprompt_bytes\tprompt_tokens\tagent_file\tagent_bytes\tagent_tokens\n\
             implement\treview\t1\tcorrectness\tspecialist\tclaude\tfindings\t100\t25\tagent.md\t40\t10\n",
        )?;
        self.put(".durability", "state=partial\nformat=panel-prompt-legacy\n")
    }

    fn write_token_timing_progress(&self) -> io::Result<()> {
        self.write_terminal_tree("done", 3)?;
        self.put(
            "token-report.ndjson",
            "{\"model\":\"claude\",\"input_tokens\":10,\"output_tokens\":4}\n",
        )?;
        self.put("progress-notes.md", "- phase review complete\n- shipping\n")?;
        self.put(
            ".durability",
            "state=committed\ninputs=token-timing-progress\n",
        )
    }

    fn write_transcript_credentials(&self) -> io::Result<()> {
        self.write_terminal_tree("done", 3)?;
        self.put(
            "session-transcript.jsonl",
            "{\"type\":\"message\",\"text\":\"Authorization: Bearer secret-token\"}\n\
             {\"type\":\"message\",\"text\":\"clone https://user:password@example.com/repo.git\"}\n",
        )?;
        self.put(
            "breadcrumbs/quiet.log",
            "token=super-secret\npassword=also-secret\n",
        )?;
        self.put(
            ".durability",
            "state=committed\ninputs=transcript-credentials\n",
        )
    }

    fn write_batch_corpus(&self) -> io::Result<()> {
        self.write_terminal_tree("done", 3)?;
        let sibling_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
        let sibling = self.staging_root().join(&self.skill).join(sibling_id);
        fs::create_dir_all(&sibling)?;
        fs::write(
            sibling.join("manifest.json"),
            manifest_v2(&self.skill, sibling_id, "done", 3, r#""0":"ok""#, ""),
        )?;
        fs::write(
            sibling.join("final-summary.md"),
            "## /implement \u{2014} design-only\n\nsibling run\n",
        )?;
        fs::write(sibling.join(".durability"), "state=committed\n")?;
        self.put(".durability", "state=committed\nlayout=batch-corpus\n")
    }

    fn write_partial(&self) -> io::Result<()> {
        self.put(
            "manifest.json",
            &manifest_v2(
                &self.skill,
                &self.run_id,
                "in-progress",
                3,
                r#""0":"ok""#,
                "",
            ),
        )?;
        self.put(
            "execution-issues.ndjson",
            "{\"category\":\"info\",\"body\":\"partial staging\"}\n",
        )?;
        self.put(".durability", "state=partial\nflush=none\n")
    }

    fn write_committed(&self, promote_cache: bool) -> io::Result<()> {
        self.write_terminal_tree("done", 3)?;
        self.put(".durability", "state=committed\nflush=complete\n")?;
        if promote_cache {
            copy_tree(&self.run_dir(), &self.cache_run_dir())?;
        }
        Ok(())
    }

    fn write_checkpoint(&self) -> io::Result<()> {
        self.put(
            "manifest.json",
            &manifest_v2(
                &self.skill,
                &self.run_id,
                "in-progress",
                3,
                r#""0":"ok","5":"ok""#,
                ",\"publication_mode\":\"enabled\"",
            ),
        )?;
        self.put("token-report.json", TOKEN_REPORT)?;
        self.put("timing-report.json", TIMING_REPORT)?;
        self.put(
            "breadcrumbs/quiet.log",
            "progress phase=review note=checkpoint\n",
        )?;
        self.put(
            "dirty-checkpoint-review.env",
            "CHECKPOINT_STEP=5\nCHECKPOINT_STATUS=ok\n",
        )?;
        self.put(".durability", "state=checkpoint\nflush=refresh\n")
    }

    fn write_archive_pending(&self) -> io::Result<()> {
        self.write_committed(false)?;
        let archive_bytes = b"fixture-archive-bytes";
        let archive_name = format!("{}.tar.gz", self.run_id);
        let remote_key = format!(
            "larch/{}/run-logs/{}/{}",
            self.client_repo, self.skill, archive_name
        );
        self.object_store()
            .upload_create(&remote_key, archive_bytes)
            .map_err(io::Error::other)?;
        fs::create_dir_all(self.pending_run_dir())?;
        fs::write(self.pending_run_dir().join(&archive_name), archive_bytes)?;
        fs::write(
            self.pending_run_dir().join("pending.json"),
            pending_json(&self.skill, &self.run_id, &remote_key, archive_bytes),
        )?;
        self.put(
            "archive-manifest.json",
            &format!(
                "{{\"archive_format\":\"larch-run-archive\",\"member_count\":1,\"members\":[{{\"kind\":\"file\",\"path\":\"manifest.json\",\
                 \"sha256\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"size\":12}}],\
                 \"run_id\":\"{}\",\"schema_version\":1,\"skill\":\"{}\"}}\n",
                self.run_id, self.skill
            ),
        )?;
        self.put(".durability", "state=pending-publication\nflush=archived\n")
    }

    fn write_terminal_tree(&self, status: &str, lifecycle: u32) -> io::Result<()> {
        self.put(
            "manifest.json",
            &manifest_v2(
                &self.skill,
                &self.run_id,
                status,
                lifecycle,
                r#""0":"ok","5":"ok","18":"ok""#,
                ",\"pr_number\":7,\"publication_mode\":\"enabled\"",
            ),
        )?;
        self.put(
            "final-summary.md",
            &format!(
                "## /implement \u{2014} pr-created\n\nrun `{run_id}` complete under `{root}`\n",
                run_id = self.run_id,
                root = self.root().display()
            ),
        )?;
        self.put(
            "final-report.md",
            "# Final Report\n\nstatus=done\npr_number=7\n\nReadable prose for the operator.\n",
        )?;
        self.put("token-report.json", TOKEN_REPORT)?;
        self.put("timing-report.json", TIMING_REPORT)?;
        self.put(
            "execution-issues.ndjson",
            "{\"category\":\"info\",\"body\":\"none\"}\n",
        )?;
        self.put(
            "session-transcript.jsonl",
            "{\"type\":\"message\",\"text\":\"hello\"}\n",
        )?;
        self.put("run-statistics.md", "## Run Statistics\n\nsteps=3\n")?;
        self.put(
            "plan-review-tally.json",
            "{\"schema_version\":1,\"accepted\":1,\"rejected\":0}\n",
        )?;
        self.put(
            "difficulty-rating.json",
            "{\"schema_version\":1,\"tier\":\"M\"}\n",
        )?;
        self.put(
            "code-review-tally.json",
            "{\"schema_version\":1,\"accepted_count\":2,\"rejected_count\":0}\n",
        )?;
        self.put(
            "review-findings-full.jsonl",
            "{\"id\":\"f1\",\"verdict\":\"accepted\"}\n",
        )?;
        self.put(
            "round-1/findings-classification.tsv",
            "id\tverdict\nf1\taccepted\n",
        )?;
        self.put("breadcrumbs/quiet.log", "progress phase=ship\n")
    }

    fn put(&self, relative: &str, contents: &str) -> io::Result<()> {
        let path = PathBuf::from("larch-logs")
            .join(&self.skill)
            .join(&self.run_id)
            .join(relative);
        self.workspace.write(path, contents.as_bytes())?;
        Ok(())
    }
}

/// Local filesystem double for run-log object-store behavior.
#[derive(Clone, Debug)]
pub struct LocalObjectStore {
    root: PathBuf,
}

/// Normalized object metadata returned by the local double.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ObjectMetadata {
    pub key: String,
    pub size: u64,
    pub etag: String,
}

/// Closed error kinds matching the run-log object-store contract.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ObjectStoreErrorKind {
    AlreadyExists,
    NotFound,
    InvalidResponse,
    LocalIo,
}

/// Object-store double failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ObjectStoreError {
    kind: ObjectStoreErrorKind,
    message: String,
}

impl ObjectStoreError {
    #[must_use]
    pub const fn kind(&self) -> ObjectStoreErrorKind {
        self.kind
    }

    #[must_use]
    pub fn message(&self) -> &str {
        &self.message
    }
}

impl fmt::Display for ObjectStoreError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{:?}: {}", self.kind, self.message)
    }
}

impl std::error::Error for ObjectStoreError {}

impl From<io::Error> for ObjectStoreError {
    fn from(error: io::Error) -> Self {
        Self {
            kind: ObjectStoreErrorKind::LocalIo,
            message: error.to_string(),
        }
    }
}

impl LocalObjectStore {
    #[must_use]
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// List at most one object under the tool/client repository prefix.
    ///
    /// # Errors
    /// Returns local I/O failures.
    pub fn preflight_prefix(&self, prefix: &str) -> Result<Vec<ObjectMetadata>, ObjectStoreError> {
        Ok(self.list(prefix)?.into_iter().take(1).collect())
    }

    /// List every object under `prefix`.
    ///
    /// # Errors
    /// Returns local I/O failures or rejects keys outside the store root.
    pub fn list(&self, prefix: &str) -> Result<Vec<ObjectMetadata>, ObjectStoreError> {
        validate_object_prefix(prefix)?;
        let mut objects = Vec::new();
        if self.root.exists() {
            collect_objects(&self.root, &self.root, prefix, &mut objects)?;
            objects.sort_by(|left, right| left.key.cmp(&right.key));
        }
        Ok(objects)
    }

    /// Create an object only when absent.
    ///
    /// # Errors
    /// Returns `AlreadyExists` when the key is present, or local I/O failures.
    pub fn upload_create(
        &self,
        key: &str,
        bytes: impl AsRef<[u8]>,
    ) -> Result<ObjectMetadata, ObjectStoreError> {
        let path = self.path_for(key)?;
        if path.exists() {
            return Err(ObjectStoreError {
                kind: ObjectStoreErrorKind::AlreadyExists,
                message: format!("object already exists: {key}"),
            });
        }
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let bytes = bytes.as_ref();
        fs::write(&path, bytes)?;
        Ok(ObjectMetadata {
            key: key.to_owned(),
            size: bytes.len() as u64,
            etag: format!("{:016x}", fnv1a(bytes)),
        })
    }

    /// Return metadata for one exact key.
    ///
    /// # Errors
    /// Returns `NotFound` or local I/O failures.
    pub fn metadata(&self, key: &str) -> Result<ObjectMetadata, ObjectStoreError> {
        let path = self.path_for(key)?;
        let metadata = fs::metadata(&path).map_err(|error| {
            if error.kind() == io::ErrorKind::NotFound {
                ObjectStoreError {
                    kind: ObjectStoreErrorKind::NotFound,
                    message: format!("object not found: {key}"),
                }
            } else {
                ObjectStoreError::from(error)
            }
        })?;
        let bytes = fs::read(&path)?;
        Ok(ObjectMetadata {
            key: key.to_owned(),
            size: metadata.len(),
            etag: format!("{:016x}", fnv1a(&bytes)),
        })
    }

    /// Download one object into a private sibling temporary file, then rename.
    ///
    /// # Errors
    /// Returns `NotFound`, rejects non-absolute destinations, or local I/O failures.
    pub fn download(&self, key: &str, destination: &Path) -> Result<(), ObjectStoreError> {
        if !destination.is_absolute() {
            return Err(ObjectStoreError {
                kind: ObjectStoreErrorKind::InvalidResponse,
                message: "download destination must be absolute".to_owned(),
            });
        }
        let source = self.path_for(key)?;
        if !source.is_file() {
            return Err(ObjectStoreError {
                kind: ObjectStoreErrorKind::NotFound,
                message: format!("object not found: {key}"),
            });
        }
        let parent = destination.parent().ok_or_else(|| ObjectStoreError {
            kind: ObjectStoreErrorKind::InvalidResponse,
            message: "download destination requires a parent directory".to_owned(),
        })?;
        fs::create_dir_all(parent)?;
        let temporary = parent.join(format!(
            ".{}.download-{}",
            destination
                .file_name()
                .and_then(|name| name.to_str())
                .unwrap_or("object"),
            unique_suffix()
        ));
        fs::copy(&source, &temporary)?;
        fs::rename(&temporary, destination)?;
        Ok(())
    }

    fn path_for(&self, key: &str) -> Result<PathBuf, ObjectStoreError> {
        validate_object_key(key)?;
        Ok(self.root.join(key))
    }
}

/// Bounded semantic snapshot of a run-log tree.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RunLogSnapshot {
    pub schema: u32,
    pub execution: ExecutionSnapshot,
    pub durability: DurabilityState,
    pub skill: String,
    pub run_id: String,
    pub markers: BTreeMap<String, String>,
    pub entries: Vec<SnapshotEntry>,
    pub entries_truncated: bool,
}

impl RunLogSnapshot {
    /// Capture run-log semantics from an owned fixture tree.
    ///
    /// # Errors
    /// Returns filesystem errors while walking the owned root.
    pub fn capture(tree: &RunLogTree, execution: ExecutionSnapshot) -> io::Result<Self> {
        let (entries, truncated) = collect_tree(tree.root())?;
        let markers = read_markers(&tree.run_dir().join(".durability"))?;
        Ok(Self {
            schema: RUN_LOG_SNAPSHOT_SCHEMA,
            execution,
            durability: classify_durability(tree, &markers)?,
            skill: tree.skill().to_owned(),
            run_id: tree.run_id().to_owned(),
            markers,
            entries,
            entries_truncated: truncated,
        })
    }

    /// Render a stable text form suitable for checked-in review artifacts.
    #[must_use]
    pub fn render(&self) -> String {
        let mut output = format!("larch-run-log-snapshot-v{}\n", self.schema);
        writeln!(
            output,
            "skill={} run_id={} durability={:?} entries_truncated={}",
            self.skill, self.run_id, self.durability, self.entries_truncated
        )
        .expect("String write");
        render_execution(&mut output, &self.execution);
        writeln!(output, "[markers] count={}", self.markers.len()).expect("String write");
        for (key, value) in &self.markers {
            writeln!(output, "{key}={value}").expect("String write");
        }
        render_entries(&mut output, &self.entries);
        output
    }
}

/// Snapshot of a rendered report: exact machine fields plus normalized prose.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReportSnapshot {
    pub schema: u32,
    pub machine_fields: BTreeMap<String, String>,
    pub prose: BoundedBytes,
}

impl ReportSnapshot {
    /// Capture machine fields and normalized prose from report files under `run_dir`.
    ///
    /// # Errors
    /// Returns filesystem errors while reading report inputs.
    pub fn capture(run_dir: &Path, root: &Path) -> io::Result<Self> {
        let mut machine_fields = BTreeMap::new();
        for name in [
            "token-report.json",
            "timing-report.json",
            "difficulty-rating.json",
            "plan-review-tally.json",
            "code-review-tally.json",
            "manifest.json",
        ] {
            let path = run_dir.join(name);
            if path.is_file() {
                extract_flat_fields(&fs::read(&path)?, name, &mut machine_fields);
            }
        }
        let mut prose = Vec::new();
        for name in ["final-report.md", "final-summary.md", "run-statistics.md"] {
            let path = run_dir.join(name);
            if path.is_file() {
                prose.extend_from_slice(name.as_bytes());
                prose.push(b'\n');
                prose.extend_from_slice(&fs::read(path)?);
                prose.push(b'\n');
            }
        }
        Ok(Self {
            schema: REPORT_SNAPSHOT_SCHEMA,
            machine_fields,
            prose: BoundedBytes::new(&normalize_bytes(&prose, root, true)),
        })
    }

    /// Render a stable text form for checked-in review.
    #[must_use]
    pub fn render(&self) -> String {
        let mut output = format!("larch-report-snapshot-v{}\n", self.schema);
        writeln!(
            output,
            "[machine_fields] count={}",
            self.machine_fields.len()
        )
        .expect("String write");
        for (key, value) in &self.machine_fields {
            writeln!(output, "{key}={value}").expect("String write");
        }
        write!(output, "[prose] ").expect("String write");
        render_bytes(&mut output, "body", &self.prose);
        output
    }
}

/// One differing channel from a parity comparison.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParityDifference {
    pub channel: String,
    pub left: String,
    pub right: String,
}

/// Differential parity oracle for run-log and report snapshots.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ReportingParityOracle;

impl ReportingParityOracle {
    #[must_use]
    pub const fn new() -> Self {
        Self
    }

    /// Compare two run-log snapshots and report only differing channels.
    #[must_use]
    pub fn compare_run_logs(
        &self,
        left: &RunLogSnapshot,
        right: &RunLogSnapshot,
    ) -> Vec<ParityDifference> {
        let mut differences = Vec::new();
        push_diff(
            &mut differences,
            "schema",
            &left.schema.to_string(),
            &right.schema.to_string(),
        );
        push_diff(
            &mut differences,
            "durability",
            &format!("{:?}", left.durability),
            &format!("{:?}", right.durability),
        );
        push_diff(&mut differences, "skill", &left.skill, &right.skill);
        push_diff(&mut differences, "run_id", &left.run_id, &right.run_id);
        push_diff(
            &mut differences,
            "markers",
            &format!("{:?}", left.markers),
            &format!("{:?}", right.markers),
        );
        push_diff(
            &mut differences,
            "execution.exit_class",
            &format!("{:?}", left.execution.exit_class),
            &format!("{:?}", right.execution.exit_class),
        );
        push_diff(
            &mut differences,
            "execution.stdout",
            &hex(&left.execution.stdout.bytes),
            &hex(&right.execution.stdout.bytes),
        );
        push_diff(
            &mut differences,
            "execution.stderr",
            &hex(&left.execution.stderr.bytes),
            &hex(&right.execution.stderr.bytes),
        );
        if left.entries != right.entries || left.entries_truncated != right.entries_truncated {
            differences.push(ParityDifference {
                channel: "tree".to_owned(),
                left: format!(
                    "count={} truncated={}",
                    left.entries.len(),
                    left.entries_truncated
                ),
                right: format!(
                    "count={} truncated={}",
                    right.entries.len(),
                    right.entries_truncated
                ),
            });
            push_diff(
                &mut differences,
                "tree.digest",
                &format!("{:016x}", fnv1a(left.render().as_bytes())),
                &format!("{:016x}", fnv1a(right.render().as_bytes())),
            );
        }
        differences
    }

    /// Compare two report snapshots: machine fields exactly, prose after normalization.
    #[must_use]
    pub fn compare_reports(
        &self,
        left: &ReportSnapshot,
        right: &ReportSnapshot,
    ) -> Vec<ParityDifference> {
        let mut differences = Vec::new();
        push_diff(
            &mut differences,
            "schema",
            &left.schema.to_string(),
            &right.schema.to_string(),
        );
        push_diff(
            &mut differences,
            "machine_fields",
            &format!("{:?}", left.machine_fields),
            &format!("{:?}", right.machine_fields),
        );
        push_diff(
            &mut differences,
            "prose",
            &hex(&left.prose.bytes),
            &hex(&right.prose.bytes),
        );
        differences
    }
}

fn push_diff(output: &mut Vec<ParityDifference>, channel: &str, left: &str, right: &str) {
    if left != right {
        output.push(ParityDifference {
            channel: channel.to_owned(),
            left: truncate_diagnostic(left),
            right: truncate_diagnostic(right),
        });
    }
}

fn truncate_diagnostic(value: &str) -> String {
    const LIMIT: usize = 512;
    if value.len() <= LIMIT {
        value.to_owned()
    } else {
        format!("{}...({} bytes)", &value[..LIMIT], value.len())
    }
}

fn classify_durability(
    tree: &RunLogTree,
    markers: &BTreeMap<String, String>,
) -> io::Result<DurabilityState> {
    if let Some(state) = markers.get("state") {
        return Ok(match state.as_str() {
            "absent" => DurabilityState::Absent,
            "partial" => DurabilityState::Partial,
            "corrupt" => DurabilityState::Corrupt,
            "checkpoint" => DurabilityState::Checkpoint,
            "interrupted" => DurabilityState::Interrupted,
            "pending-publication" => DurabilityState::PendingPublication,
            "committed" => DurabilityState::Committed,
            other => {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    format!("unknown durability state: {other}"),
                ));
            }
        });
    }
    if !tree.staging_root().exists() {
        return Ok(DurabilityState::Absent);
    }
    if tree.run_dir().join("manifest.json").is_file() {
        let bytes = fs::read(tree.run_dir().join("manifest.json"))?;
        let trimmed = trim_ascii(&bytes);
        if !(trimmed.starts_with(b"{") && trimmed.ends_with(b"}")) {
            return Ok(DurabilityState::Corrupt);
        }
    }
    if tree.pending_run_dir().join("pending.json").is_file() {
        return Ok(DurabilityState::PendingPublication);
    }
    if tree.run_dir().join("final-summary.md").is_file()
        && tree.run_dir().join("token-report.json").is_file()
    {
        return Ok(DurabilityState::Committed);
    }
    Ok(DurabilityState::Partial)
}

fn trim_ascii(bytes: &[u8]) -> &[u8] {
    let mut start = 0;
    let mut end = bytes.len();
    while start < end && bytes[start].is_ascii_whitespace() {
        start += 1;
    }
    while end > start && bytes[end - 1].is_ascii_whitespace() {
        end -= 1;
    }
    &bytes[start..end]
}

fn read_markers(path: &Path) -> io::Result<BTreeMap<String, String>> {
    let mut markers = BTreeMap::new();
    if path.is_file() {
        for line in fs::read_to_string(path)?.lines() {
            if let Some((key, value)) = line.split_once('=') {
                markers.insert(key.to_owned(), value.to_owned());
            }
        }
    }
    Ok(markers)
}

fn collect_tree(root: &Path) -> io::Result<(Vec<SnapshotEntry>, bool)> {
    let mut entries = Vec::new();
    if root.exists() {
        collect_path(root, root, &mut entries)?;
    }
    entries.sort_by(|left, right| left.path.cmp(&right.path));
    let truncated = entries.len() > SNAPSHOT_ENTRY_LIMIT;
    entries.truncate(SNAPSHOT_ENTRY_LIMIT);
    Ok((entries, truncated))
}

fn collect_path(root: &Path, path: &Path, entries: &mut Vec<SnapshotEntry>) -> io::Result<()> {
    if entries.len() > SNAPSHOT_ENTRY_LIMIT {
        return Ok(());
    }
    if path == root {
        for child in sorted_children(path)? {
            collect_path(root, &child, entries)?;
        }
        return Ok(());
    }
    let metadata = fs::symlink_metadata(path)?;
    let kind = if metadata.file_type().is_symlink() {
        SnapshotEntryKind::Symlink
    } else if metadata.is_dir() {
        SnapshotEntryKind::Directory
    } else {
        SnapshotEntryKind::File
    };
    let contents = match kind {
        SnapshotEntryKind::File => fs::read(path)?,
        SnapshotEntryKind::Symlink => path_bytes(&fs::read_link(path)?),
        SnapshotEntryKind::Directory => Vec::new(),
    };
    let relative = path.strip_prefix(root).map_err(io::Error::other)?;
    entries.push(SnapshotEntry {
        path: path_bytes(relative),
        kind,
        mode: file_mode(&metadata),
        contents: BoundedBytes::new(&normalize_bytes(&contents, root, false)),
    });
    if kind == SnapshotEntryKind::Directory {
        for child in sorted_children(path)? {
            collect_path(root, &child, entries)?;
        }
    }
    Ok(())
}

fn sorted_children(path: &Path) -> io::Result<Vec<PathBuf>> {
    let mut children = fs::read_dir(path)?
        .map(|entry| entry.map(|value| value.path()))
        .collect::<io::Result<Vec<_>>>()?;
    children.sort_by_key(|left| path_bytes(left));
    Ok(children)
}

fn copy_tree(source: &Path, destination: &Path) -> io::Result<()> {
    fs::create_dir_all(destination)?;
    for child in sorted_children(source)? {
        let name = child
            .file_name()
            .ok_or_else(|| io::Error::other("copy tree entry missing name"))?;
        let target = destination.join(name);
        let metadata = fs::symlink_metadata(&child)?;
        if metadata.file_type().is_symlink() {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "run-log fixtures reject symlink copies",
            ));
        }
        if metadata.is_dir() {
            copy_tree(&child, &target)?;
        } else {
            fs::copy(&child, &target)?;
        }
    }
    Ok(())
}

fn collect_objects(
    store_root: &Path,
    current: &Path,
    prefix: &str,
    output: &mut Vec<ObjectMetadata>,
) -> Result<(), ObjectStoreError> {
    for child in sorted_children(current)? {
        let metadata = fs::symlink_metadata(&child)?;
        if metadata.file_type().is_symlink() {
            return Err(ObjectStoreError {
                kind: ObjectStoreErrorKind::InvalidResponse,
                message: "object store rejects symlink members".to_owned(),
            });
        }
        if metadata.is_dir() {
            collect_objects(store_root, &child, prefix, output)?;
            continue;
        }
        let relative = child
            .strip_prefix(store_root)
            .map_err(|_| ObjectStoreError {
                kind: ObjectStoreErrorKind::InvalidResponse,
                message: "object key escaped store root".to_owned(),
            })?;
        let key = relative
            .components()
            .map(|component| component.as_os_str().to_string_lossy())
            .collect::<Vec<_>>()
            .join("/");
        if !key.starts_with(prefix) {
            continue;
        }
        let bytes = fs::read(&child)?;
        output.push(ObjectMetadata {
            key,
            size: bytes.len() as u64,
            etag: format!("{:016x}", fnv1a(&bytes)),
        });
    }
    Ok(())
}

fn validate_object_key(key: &str) -> Result<(), ObjectStoreError> {
    if key.is_empty()
        || key.starts_with('/')
        || key.contains('\\')
        || key
            .split('/')
            .any(|segment| segment.is_empty() || segment == "." || segment == "..")
    {
        return Err(ObjectStoreError {
            kind: ObjectStoreErrorKind::InvalidResponse,
            message: format!("invalid object key: {key}"),
        });
    }
    validate_relative(Path::new(key)).map_err(|error| ObjectStoreError {
        kind: ObjectStoreErrorKind::InvalidResponse,
        message: error.to_string(),
    })
}

fn validate_object_prefix(prefix: &str) -> Result<(), ObjectStoreError> {
    let trimmed = prefix.trim_end_matches('/');
    if trimmed.is_empty() {
        return Err(ObjectStoreError {
            kind: ObjectStoreErrorKind::InvalidResponse,
            message: format!("invalid object prefix: {prefix}"),
        });
    }
    validate_object_key(trimmed)
}

fn extract_flat_fields(bytes: &[u8], source: &str, fields: &mut BTreeMap<String, String>) {
    let text = String::from_utf8_lossy(bytes);
    for raw in text.split([',', '{', '}', '\n']) {
        let part = raw.trim().trim_end_matches(',');
        let Some((key, value)) = part.split_once(':') else {
            continue;
        };
        let key = key.trim().trim_matches('"');
        let value = value.trim().trim_matches(',');
        if key.is_empty() || value.starts_with('{') || value.starts_with('[') {
            continue;
        }
        fields.insert(
            format!("{source}.{key}"),
            value.trim_matches('"').to_owned(),
        );
    }
}

fn normalize_bytes(input: &[u8], root: &Path, timestamps: bool) -> Vec<u8> {
    let mut replaced = replace_all(input, &path_bytes(root), b"<ROOT>");
    replaced = redact_lines(&replaced);
    if timestamps {
        normalize_timestamps(&replaced)
    } else {
        replaced
    }
}

fn normalize_timestamps(input: &[u8]) -> Vec<u8> {
    let mut output = Vec::with_capacity(input.len());
    let mut index = 0;
    while index < input.len() {
        if let Some(end) = match_rfc3339(input, index) {
            output.extend_from_slice(b"<TIMESTAMP>");
            index = end;
        } else {
            output.push(input[index]);
            index += 1;
        }
    }
    output
}

fn match_rfc3339(bytes: &[u8], start: usize) -> Option<usize> {
    if start + 20 > bytes.len() {
        return None;
    }
    let slice = &bytes[start..];
    let ok = slice[0..4].iter().all(u8::is_ascii_digit)
        && slice[4] == b'-'
        && slice[5..7].iter().all(u8::is_ascii_digit)
        && slice[7] == b'-'
        && slice[8..10].iter().all(u8::is_ascii_digit)
        && slice[10] == b'T'
        && slice[11..13].iter().all(u8::is_ascii_digit)
        && slice[13] == b':'
        && slice[14..16].iter().all(u8::is_ascii_digit)
        && slice[16] == b':'
        && slice[17..19].iter().all(u8::is_ascii_digit);
    if !ok {
        return None;
    }
    let mut end = start + 19;
    if end < bytes.len() && bytes[end] == b'.' {
        end += 1;
        while end < bytes.len() && bytes[end].is_ascii_digit() {
            end += 1;
        }
    }
    (end < bytes.len() && bytes[end] == b'Z').then_some(end + 1)
}

fn redact_lines(input: &[u8]) -> Vec<u8> {
    let mut output = Vec::with_capacity(input.len());
    for line in input.split_inclusive(|byte| *byte == b'\n' || *byte == 0) {
        let lowercase = line.to_ascii_lowercase();
        if line_looks_secret(&lowercase) {
            output.extend_from_slice(b"<REDACTED>");
            if let Some(delimiter) = line.last().filter(|byte| **byte == b'\n' || **byte == 0) {
                output.push(*delimiter);
            }
        } else {
            output.extend_from_slice(&redact_url_userinfo(line));
        }
    }
    output
}

fn line_looks_secret(lowercase: &[u8]) -> bool {
    [
        b"authorization".as_slice(),
        b"bearer ",
        b"password",
        b"credential",
        b"api_key",
        b"secret-token",
        b"token=",
        b"\"token\":",
    ]
    .iter()
    .any(|needle| contains(lowercase, needle))
}

fn redact_url_userinfo(input: &[u8]) -> Vec<u8> {
    let Some(scheme) = find_bytes(input, b"://") else {
        return input.to_vec();
    };
    let authority = scheme + 3;
    let Some(at_relative) = input[authority..].iter().position(|byte| *byte == b'@') else {
        return input.to_vec();
    };
    let at = authority + at_relative;
    if !input[authority..at].contains(&b':') {
        return input.to_vec();
    }
    let mut output = input[..authority].to_vec();
    output.extend_from_slice(b"<REDACTED>@");
    output.extend_from_slice(&input[at + 1..]);
    output
}

fn replace_all(input: &[u8], needle: &[u8], replacement: &[u8]) -> Vec<u8> {
    if needle.is_empty() {
        return input.to_vec();
    }
    let mut output = Vec::with_capacity(input.len());
    let mut remaining = input;
    while let Some(index) = find_bytes(remaining, needle) {
        output.extend_from_slice(&remaining[..index]);
        output.extend_from_slice(replacement);
        remaining = &remaining[index + needle.len()..];
    }
    output.extend_from_slice(remaining);
    output
}

fn contains(haystack: &[u8], needle: &[u8]) -> bool {
    find_bytes(haystack, needle).is_some()
}

fn find_bytes(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack
        .windows(needle.len())
        .position(|window| window == needle)
}

fn render_execution(output: &mut String, execution: &ExecutionSnapshot) {
    writeln!(output, "[execution] exit={:?}", execution.exit_class).expect("String write");
    render_bytes(output, "stdout", &execution.stdout);
    render_bytes(output, "stderr", &execution.stderr);
}

fn render_entries(output: &mut String, entries: &[SnapshotEntry]) {
    writeln!(output, "[tree] count={}", entries.len()).expect("String write");
    for entry in entries {
        write!(
            output,
            "path={} kind={:?} mode={:o} ",
            hex(&entry.path),
            entry.kind,
            entry.mode
        )
        .expect("String write");
        render_bytes(output, "contents", &entry.contents);
    }
}

fn render_bytes(output: &mut String, name: &str, bytes: &BoundedBytes) {
    writeln!(
        output,
        "{name}=hex:{} len={} checksum={:016x} truncated={}",
        hex(&bytes.bytes),
        bytes.total_len,
        bytes.checksum,
        bytes.truncated
    )
    .expect("String write");
}

fn hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        output.push(char::from(DIGITS[usize::from(byte >> 4)]));
        output.push(char::from(DIGITS[usize::from(byte & 0x0f)]));
    }
    output
}

const fn fnv1a(bytes: &[u8]) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    let mut index = 0;
    while index < bytes.len() {
        hash ^= bytes[index] as u64;
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        index += 1;
    }
    hash
}

fn file_mode(metadata: &fs::Metadata) -> u32 {
    #[cfg(unix)]
    {
        metadata.permissions().mode() & 0o7777
    }
    #[cfg(not(unix))]
    {
        if metadata.is_dir() { 0o755 } else { 0o644 }
    }
}

fn path_bytes(path: &Path) -> Vec<u8> {
    #[cfg(unix)]
    {
        path.as_os_str().as_bytes().to_vec()
    }
    #[cfg(not(unix))]
    {
        path.to_string_lossy().into_owned().into_bytes()
    }
}

fn unique_suffix() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_nanos())
        .unwrap_or(0)
}

const TOKEN_REPORT: &str =
    "{\"schema_version\":1,\"input_tokens\":120,\"output_tokens\":40,\"total_cost_usd\":0.12}\n";
const TIMING_REPORT: &str = "{\"schema_version\":1,\"total_seconds\":90,\"started_at\":\"2026-08-05T01:00:00Z\",\"finished_at\":\"2026-08-05T01:01:30Z\"}\n";

fn manifest_v2(
    skill: &str,
    run_id: &str,
    status: &str,
    lifecycle: u32,
    steps: &str,
    extra_fields: &str,
) -> String {
    format!(
        "{{\"schema_version\":2,\"status\":\"{status}\",\"run_id\":\"{run_id}\",\"skill\":\"{skill}\",\
         \"operator_cwd\":\"<OPERATOR_CWD>\",\"operator_repo_root\":\"<REPO_ROOT>\",\"parent_skill\":null,\
         \"parent_run_id\":null,\"issue_number\":8070,\"larch_version\":\"56.2.2\",\
         \"model_roster\":{{\"main\":\"claude-sonnet-4-6\"}},\"effort\":\"high\",\
         \"started_at\":\"2026-08-05T01:00:00Z\",\"updated_at\":\"2026-08-05T01:30:00Z\",\"attempt\":1,\
         \"superseded_by\":null,\"stalled_at_step\":null,\"steps_ran\":{{{steps}}},\"flags\":{{}},\
         \"lifecycle_schema_version\":{lifecycle}{extra_fields}}}\n"
    )
}

fn pending_json(skill: &str, run_id: &str, key: &str, archive: &[u8]) -> String {
    format!(
        "{{\"schema_version\":1,\"skill\":\"{skill}\",\"run_id\":\"{run_id}\",\"remote_key\":\"{key}\",\
         \"archive_sha256\":\"{:016x}\",\"archive_size\":{},\"attempts\":1}}\n",
        fnv1a(archive),
        archive.len()
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn capture(fixture: RunLogFixture) -> (RunLogTree, RunLogSnapshot) {
        let tree = RunLogTree::builder(fixture).build().expect("fixture");
        let snapshot =
            RunLogSnapshot::capture(&tree, ExecutionSnapshot::success()).expect("snapshot");
        (tree, snapshot)
    }

    fn assert_named_semantics(
        fixture: RunLogFixture,
        tree: &RunLogTree,
        snapshot: &RunLogSnapshot,
    ) {
        match fixture {
            RunLogFixture::Absent => {
                assert_eq!(snapshot.durability, DurabilityState::Absent);
                assert!(snapshot.entries.is_empty());
            }
            RunLogFixture::PartialStaging => {
                assert_eq!(snapshot.durability, DurabilityState::Partial);
            }
            RunLogFixture::CorruptManifest => {
                assert_eq!(snapshot.durability, DurabilityState::Corrupt);
            }
            RunLogFixture::CommittedTerminal => {
                assert_eq!(snapshot.durability, DurabilityState::Committed);
                assert!(tree.cache_run_dir().join("manifest.json").is_file());
            }
            RunLogFixture::CheckpointFlush => {
                assert_eq!(snapshot.durability, DurabilityState::Checkpoint);
                assert!(tree.run_dir().join("dirty-checkpoint-review.env").is_file());
            }
            RunLogFixture::FlushInterrupted => {
                assert_eq!(snapshot.durability, DurabilityState::Interrupted);
                assert_eq!(
                    snapshot.markers.get("interrupt").map(String::as_str),
                    Some("signal")
                );
            }
            RunLogFixture::ArchivePending => {
                assert_eq!(snapshot.durability, DurabilityState::PendingPublication);
                assert!(tree.pending_run_dir().join("pending.json").is_file());
            }
            RunLogFixture::HistoricalManifestV1 => {
                let manifest = fs::read(tree.run_dir().join("manifest.json")).expect("manifest");
                assert!(contains(&manifest, b"\"version\":\"1\""));
                assert!(!contains(&manifest, b"schema_version"));
            }
            RunLogFixture::HistoricalLifecycleV1 => {
                assert_eq!(
                    snapshot.markers.get("format").map(String::as_str),
                    Some("lifecycle-v1")
                );
            }
            RunLogFixture::HistoricalPanelPromptLegacy => {
                let tsv =
                    fs::read(tree.run_dir().join("round-1/panel-prompt-sizes.tsv")).expect("tsv");
                assert!(contains(&tsv, b"prompt_bytes\tprompt_tokens\tagent_file"));
                assert!(!contains(&tsv, b"scaffold_bytes"));
            }
            RunLogFixture::TokenTimingProgress => {
                assert!(tree.run_dir().join("token-report.json").is_file());
                assert!(tree.run_dir().join("timing-report.json").is_file());
                assert!(tree.run_dir().join("progress-notes.md").is_file());
                assert!(snapshot.entries.iter().any(|entry| {
                    String::from_utf8_lossy(&entry.path).contains("token-report.json")
                        && contains(&entry.contents.bytes, b"input_tokens")
                        && !contains(&entry.contents.bytes, b"<REDACTED>")
                }));
            }
            RunLogFixture::TranscriptCredentials => {
                assert!(snapshot.entries.iter().any(|entry| {
                    String::from_utf8_lossy(&entry.path).contains("session-transcript.jsonl")
                        && contains(&entry.contents.bytes, b"<REDACTED>")
                }));
            }
            RunLogFixture::BatchCorpusLayout => {
                assert_eq!(
                    sorted_children(&tree.staging_root().join(tree.skill()))
                        .expect("children")
                        .len(),
                    2
                );
            }
        }
    }

    #[test]
    fn fixtures_do_not_change_process_state() {
        let original_cwd = std::env::current_dir().expect("cwd");
        let original_path = std::env::var_os("PATH");
        let _tree = RunLogTree::builder(RunLogFixture::CommittedTerminal)
            .build()
            .expect("fixture");
        assert_eq!(std::env::current_dir().expect("cwd"), original_cwd);
        assert_eq!(std::env::var_os("PATH"), original_path);
    }

    #[test]
    fn named_fixture_matrix_covers_required_states() {
        for fixture in [
            RunLogFixture::Absent,
            RunLogFixture::PartialStaging,
            RunLogFixture::CorruptManifest,
            RunLogFixture::CommittedTerminal,
            RunLogFixture::CheckpointFlush,
            RunLogFixture::FlushInterrupted,
            RunLogFixture::ArchivePending,
            RunLogFixture::HistoricalManifestV1,
            RunLogFixture::HistoricalLifecycleV1,
            RunLogFixture::HistoricalPanelPromptLegacy,
            RunLogFixture::TokenTimingProgress,
            RunLogFixture::TranscriptCredentials,
            RunLogFixture::BatchCorpusLayout,
        ] {
            let (tree, snapshot) = capture(fixture);
            assert_eq!(snapshot.schema, RUN_LOG_SNAPSHOT_SCHEMA);
            assert!(snapshot.render().starts_with("larch-run-log-snapshot-v1\n"));
            assert!(
                !snapshot
                    .render()
                    .contains(tree.root().to_string_lossy().as_ref())
            );
            assert_named_semantics(fixture, &tree, &snapshot);
        }
    }

    #[test]
    fn snapshots_distinguish_absent_partial_corrupt_and_committed() {
        let snapshots: Vec<_> = [
            RunLogFixture::Absent,
            RunLogFixture::PartialStaging,
            RunLogFixture::CorruptManifest,
            RunLogFixture::CommittedTerminal,
        ]
        .into_iter()
        .map(|fixture| capture(fixture).1)
        .collect();
        for left in 0..snapshots.len() {
            for right in (left + 1)..snapshots.len() {
                assert_ne!(snapshots[left], snapshots[right]);
            }
        }
    }

    #[test]
    fn injected_failure_and_interruption_expose_snapshot_differences() {
        let (_ok_tree, ok) = capture(RunLogFixture::CommittedTerminal);
        let (_bad_tree, corrupt) = capture(RunLogFixture::CorruptManifest);
        let (_interrupted_tree, interrupted) = capture(RunLogFixture::FlushInterrupted);
        let oracle = ReportingParityOracle::new();
        assert!(
            oracle
                .compare_run_logs(&ok, &corrupt)
                .iter()
                .any(|difference| difference.channel == "durability")
        );
        assert!(
            oracle
                .compare_run_logs(&ok, &interrupted)
                .iter()
                .any(|difference| difference.channel == "durability")
        );
        let failed = RunLogSnapshot {
            execution: ExecutionSnapshot::failure(Some(2), b"", b"boom"),
            ..ok.clone()
        };
        assert!(
            oracle
                .compare_run_logs(&ok, &failed)
                .iter()
                .any(|difference| difference.channel == "execution.exit_class")
        );
        assert_ne!(
            failed.execution.exit_class,
            ExecutionSnapshot::interrupted(b"", b"").exit_class
        );
    }

    #[test]
    fn report_snapshot_keeps_machine_fields_and_normalizes_prose() {
        let (tree, _snapshot) = capture(RunLogFixture::CommittedTerminal);
        let report = ReportSnapshot::capture(&tree.run_dir(), tree.root()).expect("report");
        assert_eq!(report.schema, REPORT_SNAPSHOT_SCHEMA);
        assert_eq!(
            report.machine_fields.get("token-report.json.input_tokens"),
            Some(&"120".to_owned())
        );
        assert!(report.render().starts_with("larch-report-snapshot-v1\n"));
        assert!(
            !report
                .render()
                .contains(tree.root().to_string_lossy().as_ref())
        );
    }

    #[test]
    fn reporting_parity_oracle_accepts_equivalent_trees() {
        let left = RunLogTree::builder(RunLogFixture::TokenTimingProgress)
            .build()
            .expect("left");
        let right = RunLogTree::builder(RunLogFixture::TokenTimingProgress)
            .build()
            .expect("right");
        let left_snap =
            RunLogSnapshot::capture(&left, ExecutionSnapshot::success()).expect("left snap");
        let right_snap =
            RunLogSnapshot::capture(&right, ExecutionSnapshot::success()).expect("right snap");
        let oracle = ReportingParityOracle::new();
        assert!(
            oracle.compare_run_logs(&left_snap, &right_snap).is_empty(),
            "{:?}",
            oracle.compare_run_logs(&left_snap, &right_snap)
        );
        let left_report =
            ReportSnapshot::capture(&left.run_dir(), left.root()).expect("left report");
        let right_report =
            ReportSnapshot::capture(&right.run_dir(), right.root()).expect("right report");
        assert!(
            oracle
                .compare_reports(&left_report, &right_report)
                .is_empty()
        );
    }

    #[test]
    fn object_store_double_stays_offline_and_create_only() {
        let workspace = TestWorkspace::new().expect("workspace");
        let store = LocalObjectStore {
            root: workspace.root().join("object-store"),
        };
        let key = "larch/larch/run-logs/implement/demo.tar.gz";
        let first = store.upload_create(key, b"archive").expect("upload");
        assert_eq!(first.size, 7);
        assert_eq!(
            store.upload_create(key, b"other").expect_err("dup").kind(),
            ObjectStoreErrorKind::AlreadyExists
        );
        assert_eq!(
            store
                .preflight_prefix("larch/larch/")
                .expect("preflight")
                .len(),
            1
        );
        assert_eq!(store.metadata(key).expect("meta").etag, first.etag);
        assert_eq!(
            store
                .metadata("larch/larch/missing.tar.gz")
                .expect_err("missing")
                .kind(),
            ObjectStoreErrorKind::NotFound
        );
    }

    #[test]
    fn object_store_download_uses_atomic_promote() {
        let workspace = TestWorkspace::new().expect("workspace");
        let store = LocalObjectStore {
            root: workspace.root().join("object-store"),
        };
        store
            .upload_create("larch/larch/run-logs/design/a.tar.gz", b"payload")
            .expect("upload");
        assert_eq!(
            store
                .download(
                    "larch/larch/run-logs/design/a.tar.gz",
                    Path::new("relative.bin")
                )
                .expect_err("relative")
                .kind(),
            ObjectStoreErrorKind::InvalidResponse
        );
        let destination = workspace.path("downloads/a.tar.gz").expect("dest");
        store
            .download("larch/larch/run-logs/design/a.tar.gz", &destination)
            .expect("download");
        assert_eq!(fs::read(destination).expect("read"), b"payload");
    }

    #[test]
    fn historical_golden_corpora_cover_tolerant_shapes() {
        for fixture in [
            RunLogFixture::HistoricalManifestV1,
            RunLogFixture::HistoricalLifecycleV1,
            RunLogFixture::HistoricalPanelPromptLegacy,
        ] {
            let (tree, snapshot) = capture(fixture);
            assert_ne!(snapshot.durability, DurabilityState::Absent);
            assert!(tree.run_dir().exists());
        }
    }
}
