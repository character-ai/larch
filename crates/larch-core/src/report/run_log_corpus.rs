//! Typed, streaming run-log corpus readers.
//! Library parity for read-only Python batch/corpus selection; Python remains
//! the production owner until consumer cutovers move.
use crate::{ManifestRecord, RunLogLayout, RunLogSlug};
use chrono::{DateTime, NaiveDate, NaiveDateTime, Utc};
use serde_json::{Map, Value};
use std::{
    collections::VecDeque,
    error::Error,
    fmt, fs,
    path::{Path, PathBuf},
};
/// Write mode declared by a registered run-log batch.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum RunLogBatchMode {
    /// A writer replaces the prior batch payload atomically.
    Replace,
    /// A writer appends records to the batch payload.
    Append,
}
impl RunLogBatchMode {
    /// Return the Python registry token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Replace => "replace",
            Self::Append => "append",
        }
    }
}
/// Payload sanitizer declared by a registered run-log batch.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum RunLogBatchSanitizer {
    /// No structural payload validation.
    None,
    /// A JSON object payload.
    JsonObject,
    /// Newline-delimited JSON records.
    JsonLines,
    /// The implementation-plan body validator.
    PlanGoals,
}
impl RunLogBatchSanitizer {
    /// Return the Python registry token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::JsonObject => "json-object",
            Self::JsonLines => "json-lines",
            Self::PlanGoals => "plan-goals",
        }
    }
}
/// One registered run-log batch and its durable artifact contract.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub struct RunLogBatchSpec {
    slug: &'static str,
    extension: &'static str,
    mode: RunLogBatchMode,
    sanitizer: RunLogBatchSanitizer,
    rejects_session_tmpdir: bool,
}
impl RunLogBatchSpec {
    const fn new(
        slug: &'static str,
        extension: &'static str,
        mode: RunLogBatchMode,
        sanitizer: RunLogBatchSanitizer,
        rejects_session_tmpdir: bool,
    ) -> Self {
        Self {
            slug,
            extension,
            mode,
            sanitizer,
            rejects_session_tmpdir,
        }
    }
    /// Return the stable batch slug.
    #[must_use]
    pub const fn slug(self) -> &'static str {
        self.slug
    }
    #[must_use]
    pub const fn extension(self) -> &'static str {
        self.extension
    }
    #[must_use]
    pub const fn mode(self) -> RunLogBatchMode {
        self.mode
    }
    #[must_use]
    pub const fn sanitizer(self) -> RunLogBatchSanitizer {
        self.sanitizer
    }
    /// Return whether this durable payload rejects session-tmpdir pointers.
    #[must_use]
    pub const fn rejects_session_tmpdir(self) -> bool {
        self.rejects_session_tmpdir
    }
    /// Return this batch's artifact path below one run directory.
    #[must_use]
    pub fn path_in(self, run_dir: impl AsRef<Path>) -> PathBuf {
        run_dir
            .as_ref()
            .join(format!("{}{}", self.slug, self.extension))
    }
}
const BATCH_SPECS: &str = "\
architectural-guideline-outcome|.json|r|o|0
architectural-invariant-outcome|.json|r|o|0
checks-digest-sizes|.tsv|a|n|0
code-review-tally|.json|r|o|0
codex-commit-message|.txt|r|n|0
codex-impl-manifest-raw|.json|r|n|0
codex-impl-transcript|.txt|r|n|0
codex-impl-transcript-meta|.txt.meta|r|n|0
codex-impl-transcript-prompt|.txt|r|n|0
debate-participants|.tsv|r|n|1
debate-proposal|.md|r|n|1
debate-round-ledger|.ndjson|a|l|1
debate-stalemate-tally|.json|r|o|1
difficulty-rating|.json|r|o|0
execution-issues|.ndjson|a|l|0
final-bail-reason|.txt|r|n|0
include-probe-evidence|.md|r|n|0
oos-issues|.ndjson|a|l|0
panel-prompt-sizes|.tsv|r|n|0
parent-issue|.md|r|n|0
plan-goals-test|.md|r|p|0
plan-review-tally|.json|r|o|0
pre-review-head|.txt|r|n|0
pre-review-untracked|.txt|r|n|0
review-context|.md|r|n|0
review-findings|.ndjson|a|l|0
review-findings-classification-round-1|.tsv|r|n|0
review-findings-classification-round-2|.tsv|r|n|0
review-findings-classification-round-3|.tsv|r|n|0
review-findings-classification-round-4|.tsv|r|n|0
review-findings-classification-round-5|.tsv|r|n|0
review-findings-full|.jsonl|r|n|0
review-panel-manifest|.ndjson|r|n|0
review-round-summary|.md|r|n|0
review-scout-manifest|.json|r|o|0
review-tally|.md|r|n|0
reviewer-prune-ledger|.tsv|r|n|0
run-statistics|.md|r|n|0
scope-disposition|.json|r|o|0
session-transcript|.jsonl|r|n|0
ship-route-exit-handoff|.env|r|n|0
timing-report|.json|r|n|0
token-report|.json|r|n|0
vendor-failure-diagnostics|.txt|r|n|0
version-bump-reasoning|.md|r|n|0
";
fn parse_batch_spec(line: &'static str) -> RunLogBatchSpec {
    let mut fields = line.split('|');
    let slug = fields.next().expect("static run-log batch slug");
    let extension = fields.next().expect("static run-log batch extension");
    let mode = match fields.next().expect("static run-log batch mode") {
        "r" => RunLogBatchMode::Replace,
        "a" => RunLogBatchMode::Append,
        _ => unreachable!("invalid static run-log batch mode"),
    };
    let sanitizer = match fields.next().expect("static run-log batch sanitizer") {
        "n" => RunLogBatchSanitizer::None,
        "o" => RunLogBatchSanitizer::JsonObject,
        "l" => RunLogBatchSanitizer::JsonLines,
        "p" => RunLogBatchSanitizer::PlanGoals,
        _ => unreachable!("invalid static run-log batch sanitizer"),
    };
    let rejects_session_tmpdir = match fields.next().expect("static run-log batch reject flag") {
        "0" => false,
        "1" => true,
        _ => unreachable!("invalid static run-log batch reject flag"),
    };
    if fields.next().is_some() {
        unreachable!("invalid static run-log batch row");
    }
    RunLogBatchSpec::new(slug, extension, mode, sanitizer, rejects_session_tmpdir)
}
/// Iterate registered batch metadata in stable slug order.
pub fn run_log_batch_specs() -> impl Iterator<Item = RunLogBatchSpec> {
    BATCH_SPECS.lines().map(parse_batch_spec)
}
/// Return the registered metadata for slug.
#[must_use]
pub fn run_log_batch_spec(slug: &str) -> Option<RunLogBatchSpec> {
    BATCH_SPECS
        .lines()
        .find(|line| line.split_once('|').is_some_and(|(name, _)| name == slug))
        .map(parse_batch_spec)
}
/// Return the normalized outcome label from a final-summary heading.
#[must_use]
pub fn parse_preterminal_outcome_label(text: &str) -> Option<String> {
    for raw_line in text.lines() {
        let line = raw_line.trim();
        if !line.starts_with("## /") {
            continue;
        }
        let separator = match (line.rfind(": "), line.rfind(" — ")) {
            (Some(colon), Some(dash)) if dash > colon => (dash, " — "),
            (Some(colon), _) => (colon, ": "),
            (None, Some(dash)) => (dash, " — "),
            (None, None) => continue,
        };
        let label = line[separator.0 + separator.1.len()..]
            .trim()
            .to_lowercase();
        return (!label.is_empty()).then_some(label);
    }
    None
}
/// A closed timestamp range used to select committed runs.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RunLogTimeWindow {
    start: Option<DateTime<Utc>>,
    end: Option<DateTime<Utc>>,
}
impl RunLogTimeWindow {
    /// Create a closed time window.
    /// # Errors
    /// Returns [`RunLogTimeWindowError`] when start falls after end.
    pub fn new(
        start: Option<DateTime<Utc>>,
        end: Option<DateTime<Utc>>,
    ) -> Result<Self, RunLogTimeWindowError> {
        if start
            .as_ref()
            .zip(end.as_ref())
            .is_some_and(|(start, end)| start > end)
        {
            return Err(RunLogTimeWindowError);
        }
        Ok(Self { start, end })
    }
    fn contains(&self, timestamp: DateTime<Utc>) -> bool {
        self.start.as_ref().is_none_or(|start| timestamp >= *start)
            && self.end.as_ref().is_none_or(|end| timestamp <= *end)
    }
}
/// Typed invalid time-window error.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RunLogTimeWindowError;
impl fmt::Display for RunLogTimeWindowError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("run-log time window start must not fall after its end")
    }
}
impl Error for RunLogTimeWindowError {}
/// Typed filters for [`RunLogCorpus::select`].
#[derive(Clone, Debug, Default)]
pub struct RunLogSelection {
    skills: Vec<RunLogSlug>,
    window: Option<RunLogTimeWindow>,
}
impl RunLogSelection {
    /// Select every valid skill directory under the corpus root.
    #[must_use]
    pub const fn all() -> Self {
        Self {
            skills: Vec::new(),
            window: None,
        }
    }
    /// Select one validated skill.
    #[must_use]
    pub fn for_skill(skill: RunLogSlug) -> Self {
        Self {
            skills: vec![skill],
            window: None,
        }
    }
    /// Select the given skills in caller order, removing duplicate entries.
    #[must_use]
    pub fn for_skills(skills: impl IntoIterator<Item = RunLogSlug>) -> Self {
        let mut selected = Vec::new();
        for skill in skills {
            if !selected.contains(&skill) {
                selected.push(skill);
            }
        }
        Self {
            skills: selected,
            window: None,
        }
    }
    /// Add a closed started-at filter to this selection.
    #[must_use]
    pub const fn with_window(mut self, window: RunLogTimeWindow) -> Self {
        self.window = Some(window);
        self
    }
}
/// Why the corpus reader skipped or could not inspect an artifact.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum RunLogCorpusWarningKind {
    /// The requested corpus or skill root was missing, a file, or a symlink.
    RootMissing,
    /// The requested root could not be enumerated.
    RootUnreadable,
    /// A direct child was a symlink.
    ChildSymlink,
    /// A direct child could not be resolved.
    ChildUnresolvable,
    /// A direct child resolved outside its requested root.
    ChildEscapes,
    /// A top-level skill directory was not a valid run-log slug.
    InvalidSkill,
    /// A run directory was not a valid run-log slug.
    InvalidRunId,
    /// A primary manifest was absent.
    ManifestMissing,
    /// A primary manifest was a symlink.
    ManifestSymlink,
    /// A primary manifest was invalid JSON or unreadable.
    ManifestInvalid,
    /// A primary manifest JSON root was not an object.
    ManifestNotObject,
    /// A primary manifest lacked a positive numeric issue number.
    ManifestMissingIssueNumber,
    /// A time-window selection could not determine a run start time.
    WindowTimestampUnavailable,
}
/// A non-fatal, structured corpus-walk warning.
pub type RunLogCorpusWarning = super::PathWarning<RunLogCorpusWarningKind>;
/// One result from a streaming corpus selection.
#[derive(Clone, Debug)]
pub enum RunLogCorpusEvent {
    /// A manifest-accepted run directory.
    Run(Box<RunLogRun>),
    /// A recoverable malformed, partial, or unsafe artifact.
    Warning(RunLogCorpusWarning),
}
/// A typed primary run manifest accepted by corpus selection.
#[derive(Clone, Debug)]
pub struct RunLogManifest {
    fields: Map<String, Value>,
    typed_record: Option<ManifestRecord>,
    issue_number: u64,
}
impl RunLogManifest {
    fn from_fields(fields: Map<String, Value>) -> Self {
        let issue_number = positive_issue_number(fields.get("issue_number"))
            .expect("run-log manifest admission requires a positive issue number");
        let typed_record = ManifestRecord::parse_value(Value::Object(fields.clone())).ok();
        Self {
            fields,
            typed_record,
            issue_number,
        }
    }
    fn metadata_candidate(fields: Map<String, Value>) -> Self {
        Self {
            typed_record: ManifestRecord::parse_value(Value::Object(fields.clone())).ok(),
            fields,
            issue_number: 0,
        }
    }
    /// Return the positive issue number that admitted this run.
    #[must_use]
    pub const fn issue_number(&self) -> u64 {
        self.issue_number
    }
    /// Return the underlying JSON field for a consumer-specific parser.
    #[must_use]
    pub fn field(&self, key: &str) -> Option<&Value> {
        self.fields.get(key)
    }
    /// Return the known historical/current manifest record when its version is supported.
    #[must_use]
    pub const fn typed_record(&self) -> Option<&ManifestRecord> {
        self.typed_record.as_ref()
    }
    fn timestamp(&self, keys: &[&str]) -> TimestampRead {
        for key in keys {
            let Some(value) = self.fields.get(*key) else {
                continue;
            };
            let Value::String(raw) = value else {
                return TimestampRead::Invalid;
            };
            let raw = raw.trim();
            if raw.is_empty() {
                continue;
            }
            return parse_timestamp(raw).map_or(TimestampRead::Invalid, TimestampRead::Value);
        }
        TimestampRead::Empty
    }
    fn version(&self) -> VersionRead {
        let Some(Value::String(value)) = self.fields.get("larch_version") else {
            return VersionRead::Empty;
        };
        let value = value.trim();
        if value.is_empty() {
            return VersionRead::Empty;
        }
        if valid_larch_version(value) {
            VersionRead::Value(value.to_owned())
        } else {
            VersionRead::Invalid
        }
    }
}
/// One manifest-accepted, safe direct child of a skill root.
#[derive(Clone, Debug)]
pub struct RunLogRun {
    layout: RunLogLayout,
    directory: PathBuf,
    manifest: RunLogManifest,
}
impl RunLogRun {
    fn load(skill: RunLogSlug, directory: PathBuf) -> Result<Self, RunLogCorpusWarning> {
        let Some(name) = directory.file_name().and_then(|name| name.to_str()) else {
            return Err(RunLogCorpusWarning::new(
                RunLogCorpusWarningKind::InvalidRunId,
                directory,
                "run directory name is not valid UTF-8; skipping",
            ));
        };
        let run_id = RunLogSlug::parse(name).map_err(|error| {
            RunLogCorpusWarning::new(
                RunLogCorpusWarningKind::InvalidRunId,
                directory.clone(),
                format!(
                    "run directory {} has an invalid run id: {error}; skipping",
                    directory.display()
                ),
            )
        })?;
        let display = directory.display();
        let manifest_path = directory.join("manifest.json");
        let manifest_display = manifest_path.display();
        let metadata = fs::symlink_metadata(&manifest_path).map_err(|error| {
            let kind = if error.kind() == std::io::ErrorKind::NotFound {
                RunLogCorpusWarningKind::ManifestMissing
            } else {
                RunLogCorpusWarningKind::ManifestInvalid
            };
            RunLogCorpusWarning::new(
                kind,
                manifest_path.clone(),
                format!("manifest for {display} is missing or unreadable: {error}; skipping"),
            )
        })?;
        if metadata.file_type().is_symlink() {
            return Err(RunLogCorpusWarning::new(
                RunLogCorpusWarningKind::ManifestSymlink,
                manifest_path,
                format!("manifest.json at {display} is a symlink; skipping"),
            ));
        }
        if !metadata.is_file() {
            return Err(RunLogCorpusWarning::new(
                RunLogCorpusWarningKind::ManifestMissing,
                manifest_path,
                format!("manifest for {display} is missing; skipping"),
            ));
        }
        let bytes = fs::read(&manifest_path).map_err(|error| {
            RunLogCorpusWarning::new(
                RunLogCorpusWarningKind::ManifestInvalid,
                manifest_path.clone(),
                format!("invalid manifest.json at {manifest_display}: {error}; skipping"),
            )
        })?;
        let parsed: Value = serde_json::from_slice(&bytes).map_err(|error| {
            RunLogCorpusWarning::new(
                RunLogCorpusWarningKind::ManifestInvalid,
                manifest_path.clone(),
                format!("invalid manifest.json at {manifest_display}: {error}; skipping"),
            )
        })?;
        let Value::Object(fields) = parsed else {
            return Err(RunLogCorpusWarning::new(
                RunLogCorpusWarningKind::ManifestNotObject,
                manifest_path,
                format!("manifest for {display} is not a JSON object; skipping"),
            ));
        };
        if positive_issue_number(fields.get("issue_number")).is_none() {
            return Err(RunLogCorpusWarning::new(
                RunLogCorpusWarningKind::ManifestMissingIssueNumber,
                manifest_path,
                format!("manifest for {display} lacks numeric issue_number; skipping"),
            ));
        }
        let log_root = directory
            .parent()
            .and_then(Path::parent)
            .expect("safe corpus runs have a containing corpus root")
            .to_owned();
        Ok(Self {
            layout: RunLogLayout::new(log_root, skill, run_id),
            directory,
            manifest: RunLogManifest::from_fields(fields),
        })
    }
    /// Return the shared layout for the selected run.
    #[must_use]
    pub const fn layout(&self) -> &RunLogLayout {
        &self.layout
    }
    /// Return the selected run directory.
    #[must_use]
    pub fn directory(&self) -> &Path {
        &self.directory
    }
    /// Return the accepted primary manifest metadata.
    #[must_use]
    pub const fn manifest(&self) -> &RunLogManifest {
        &self.manifest
    }
    /// Return this run's path for a registered batch.
    #[must_use]
    pub fn batch_path(&self, spec: RunLogBatchSpec) -> PathBuf {
        spec.path_in(&self.directory)
    }
    /// Stream present regular batch artifacts in stable batch-slug order.
    pub fn batches(&self) -> impl Iterator<Item = RunLogBatchArtifact> + '_ {
        run_log_batch_specs().filter_map(move |spec| {
            let path = self.batch_path(spec);
            is_contained_regular_file(&self.directory, &path)
                .then_some(RunLogBatchArtifact { spec, path })
        })
    }
    /// Return a safe contained transcript path when one exists.
    #[must_use]
    pub fn session_transcript_path(&self) -> Option<PathBuf> {
        let path = self.directory.join("session-transcript.jsonl");
        is_contained_regular_file(&self.directory, &path).then_some(path)
    }
    /// Stream safe regular files below this validated run directory.
    #[must_use]
    pub fn files(&self) -> RunLogFileIter {
        RunLogFileIter::new(&self.directory)
    }
    /// Stream safe regular files with an exact basename.
    pub fn files_named(&self, name: &str) -> impl Iterator<Item = PathBuf> {
        let name = name.to_owned();
        self.files().filter(move |path| {
            path.file_name().and_then(|part| part.to_str()) == Some(name.as_str())
        })
    }
    /// Return canonical classification paths in deterministic order for this run's skill.
    #[must_use]
    pub fn classification_paths(&self, sort: RunLogRoundSort) -> Vec<PathBuf> {
        let Ok(canonical_run) = fs::canonicalize(&self.directory) else {
            return Vec::new();
        };
        let skill = self.layout.skill().as_str();
        let mut paths: Vec<PathBuf> = match skill {
            "design" | "implement" => self
                .files_named("findings-classification.tsv")
                .filter(|path| {
                    path.strip_prefix(&canonical_run)
                        .ok()
                        .is_some_and(|relative| classification_path_matches(skill, relative))
                })
                .collect(),
            "review" => self
                .files()
                .filter(|path| {
                    path.parent() == Some(canonical_run.as_path())
                        && path
                            .file_name()
                            .and_then(|name| name.to_str())
                            .is_some_and(is_review_classification_name)
                })
                .collect(),
            _ => Vec::new(),
        };
        sort_classification_paths(&mut paths, sort);
        paths
    }
    /// Return the first valid started timestamp from tolerant metadata candidates.
    #[must_use]
    pub fn started_at(
        &self,
        allow_updated_at_fallback: bool,
        continue_on_empty: bool,
    ) -> Option<DateTime<Utc>> {
        for metadata in self.metadata_candidates() {
            let started = metadata.timestamp(&["started_at"]);
            if let TimestampRead::Value(value) = started {
                return Some(value);
            }
            let invalid_started = matches!(started, TimestampRead::Invalid);
            if allow_updated_at_fallback {
                let updated = metadata.timestamp(&["updated_at"]);
                if let TimestampRead::Value(value) = updated {
                    return Some(value);
                }
                if invalid_started || matches!(updated, TimestampRead::Invalid) {
                    continue;
                }
            } else if invalid_started {
                continue;
            }
            if !continue_on_empty {
                return None;
            }
        }
        None
    }
    /// Return the first valid ended/completed/updated timestamp from metadata candidates.
    #[must_use]
    pub fn ended_at(&self, continue_on_empty: bool) -> Option<DateTime<Utc>> {
        for metadata in self.metadata_candidates() {
            let ended = metadata.timestamp(&["ended_at", "completed_at"]);
            if let TimestampRead::Value(value) = ended {
                return Some(value);
            }
            let updated = metadata.timestamp(&["updated_at"]);
            if let TimestampRead::Value(value) = updated {
                return Some(value);
            }
            if matches!(ended, TimestampRead::Invalid) || matches!(updated, TimestampRead::Invalid)
            {
                continue;
            }
            if !continue_on_empty {
                return None;
            }
        }
        None
    }
    /// Return the first valid larch version from metadata candidates.
    #[must_use]
    pub fn larch_version(&self, continue_on_empty: bool) -> Option<String> {
        for metadata in self.metadata_candidates() {
            match metadata.version() {
                VersionRead::Value(version) => return Some(version),
                VersionRead::Empty if !continue_on_empty => return None,
                VersionRead::Empty | VersionRead::Invalid => {}
            }
        }
        None
    }
    fn metadata_candidates(&self) -> impl Iterator<Item = RunLogManifest> {
        let alternate = load_metadata_candidate(&self.directory.join("run-manifest.json"));
        std::iter::once(self.manifest.clone()).chain(alternate)
    }
}
/// A present registered batch artifact within a selected run.
#[derive(Clone, Debug)]
pub struct RunLogBatchArtifact {
    spec: RunLogBatchSpec,
    path: PathBuf,
}
impl RunLogBatchArtifact {
    /// Return registered batch metadata.
    #[must_use]
    pub const fn spec(&self) -> RunLogBatchSpec {
        self.spec
    }
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }
}
/// Classification ordering for one run's files.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum RunLogRoundSort {
    /// Sort by the parsed round number, then by path.
    Numeric,
    /// Sort lexically by full path.
    Lexical,
}
/// Return the round number from a round directory or artifact filename.
#[must_use]
pub fn round_number_from_path(path: &Path) -> Option<u32> {
    for component in path.components().rev() {
        let Some(text) = component.as_os_str().to_str() else {
            continue;
        };
        if let Some(number) = exact_round_number(text) {
            return Some(number);
        }
    }
    path.file_name()
        .and_then(|name| name.to_str())
        .and_then(round_number_in_name)
}
/// A streaming safe-file reader for one validated run directory.
#[derive(Debug)]
pub struct RunLogFileIter {
    contain_root: PathBuf,
    directories: VecDeque<PathBuf>,
    entries: VecDeque<PathBuf>,
}
impl RunLogFileIter {
    const fn empty() -> Self {
        Self {
            contain_root: PathBuf::new(),
            directories: VecDeque::new(),
            entries: VecDeque::new(),
        }
    }
    fn new(run_dir: &Path) -> Self {
        let Ok(run_root) = fs::canonicalize(run_dir) else {
            return Self::empty();
        };
        let Some(parent) = run_root.parent() else {
            return Self::empty();
        };
        let Ok(contain_root) = fs::canonicalize(parent) else {
            return Self::empty();
        };
        if !run_root.starts_with(&contain_root) {
            return Self::empty();
        }
        Self {
            contain_root,
            directories: VecDeque::from([run_root]),
            entries: VecDeque::new(),
        }
    }
}
impl Iterator for RunLogFileIter {
    type Item = PathBuf;
    fn next(&mut self) -> Option<Self::Item> {
        loop {
            if let Some(path) = self.entries.pop_front() {
                let Ok(metadata) = fs::symlink_metadata(&path) else {
                    continue;
                };
                if metadata.file_type().is_symlink() {
                    continue;
                }
                let Ok(resolved) = fs::canonicalize(&path) else {
                    continue;
                };
                if !resolved.starts_with(&self.contain_root) {
                    continue;
                }
                if metadata.is_dir() {
                    self.directories.push_back(resolved);
                    continue;
                }
                if metadata.is_file() {
                    return Some(resolved);
                }
                continue;
            }
            let directory = self.directories.pop_front()?;
            let Ok(entries) = sorted_children(&directory) else {
                continue;
            };
            self.entries = VecDeque::from(entries);
        }
    }
}
/// Reader for one synchronized or explicitly supplied run-log corpus root.
#[derive(Clone, Debug)]
pub struct RunLogCorpus {
    root: PathBuf,
}
impl RunLogCorpus {
    /// Create a reader rooted at a synchronized or explicitly supplied corpus path.
    #[must_use]
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }
    /// Return the configured corpus root.
    #[must_use]
    pub fn root(&self) -> &Path {
        &self.root
    }
    /// Stream selected runs and warnings without preloading run contents or the corpus.
    #[must_use]
    pub fn select(&self, selection: RunLogSelection) -> RunLogCorpusIter {
        let mut pending = VecDeque::new();
        let skill_roots = if selection.skills.is_empty() {
            self.discover_skill_roots(&mut pending)
        } else {
            selection
                .skills
                .iter()
                .cloned()
                .map(|skill| SkillRoot {
                    path: self.root.join(skill.as_str()),
                    skill,
                })
                .collect()
        };
        RunLogCorpusIter {
            selection,
            skill_roots,
            current_skill: None,
            run_dirs: Vec::new().into_iter(),
            pending,
        }
    }

    /// Return safe direct run directories below this corpus root.
    ///
    /// This is the compatibility form for an explicitly supplied skill root.
    /// It shares the same containment and symlink handling as normal corpus
    /// discovery rather than inviting a second audit-specific directory walk.
    #[must_use]
    pub fn safe_child_run_directories(&self) -> Vec<PathBuf> {
        safe_child_directories(&self.root).directories
    }

    fn discover_skill_roots(
        &self,
        pending: &mut VecDeque<RunLogCorpusEvent>,
    ) -> VecDeque<SkillRoot> {
        let scan = safe_child_directories(&self.root);
        pending.extend(scan.warnings.into_iter().map(RunLogCorpusEvent::Warning));
        scan.directories
            .into_iter()
            .filter_map(|path| {
                let Some(name) = path.file_name().and_then(|name| name.to_str()) else {
                    pending.push_back(RunLogCorpusEvent::Warning(RunLogCorpusWarning::new(
                        RunLogCorpusWarningKind::InvalidSkill,
                        path,
                        "skill directory name is not valid UTF-8; skipping",
                    )));
                    return None;
                };
                match RunLogSlug::parse(name) {
                    Ok(skill) => Some(SkillRoot { skill, path }),
                    Err(error) => {
                        pending.push_back(RunLogCorpusEvent::Warning(RunLogCorpusWarning::new(
                            RunLogCorpusWarningKind::InvalidSkill,
                            path.clone(),
                            format!(
                                "skill directory {} is invalid: {error}; skipping",
                                path.display()
                            ),
                        )));
                        None
                    }
                }
            })
            .collect()
    }
}
#[derive(Clone, Debug)]
struct SkillRoot {
    skill: RunLogSlug,
    path: PathBuf,
}
/// Iterator returned by [`RunLogCorpus::select`].
#[derive(Debug)]
pub struct RunLogCorpusIter {
    selection: RunLogSelection,
    skill_roots: VecDeque<SkillRoot>,
    current_skill: Option<RunLogSlug>,
    run_dirs: std::vec::IntoIter<PathBuf>,
    pending: VecDeque<RunLogCorpusEvent>,
}
impl Iterator for RunLogCorpusIter {
    type Item = RunLogCorpusEvent;
    fn next(&mut self) -> Option<Self::Item> {
        loop {
            if let Some(event) = self.pending.pop_front() {
                return Some(event);
            }
            if let Some(directory) = self.run_dirs.next() {
                let Some(skill) = self.current_skill.clone() else {
                    continue;
                };
                let run = match RunLogRun::load(skill, directory) {
                    Ok(run) => run,
                    Err(warning) => return Some(RunLogCorpusEvent::Warning(warning)),
                };
                if let Some(window) = &self.selection.window {
                    let Some(started_at) = run.started_at(true, false) else {
                        return Some(RunLogCorpusEvent::Warning(RunLogCorpusWarning::new(
                            RunLogCorpusWarningKind::WindowTimestampUnavailable,
                            run.directory.clone(),
                            format!(
                                "run directory {} has no valid started-at timestamp for the selected window; skipping",
                                run.directory.display()
                            ),
                        )));
                    };
                    if !window.contains(started_at) {
                        continue;
                    }
                }
                return Some(RunLogCorpusEvent::Run(Box::new(run)));
            }
            let skill_root = self.skill_roots.pop_front()?;
            let scan = safe_child_directories(&skill_root.path);
            self.pending
                .extend(scan.warnings.into_iter().map(RunLogCorpusEvent::Warning));
            self.current_skill = Some(skill_root.skill);
            self.run_dirs = scan.directories.into_iter();
        }
    }
}
struct ChildDirectoryScan {
    directories: Vec<PathBuf>,
    warnings: Vec<RunLogCorpusWarning>,
}
impl ChildDirectoryScan {
    fn warning(warning: RunLogCorpusWarning) -> Self {
        Self {
            directories: Vec::new(),
            warnings: vec![warning],
        }
    }
}
fn resolve_safe_root(root: &Path) -> Result<PathBuf, RunLogCorpusWarning> {
    let display = root.display();
    let metadata = fs::symlink_metadata(root).map_err(|error| {
        RunLogCorpusWarning::new(
            RunLogCorpusWarningKind::RootMissing,
            root.to_owned(),
            format!("log root {display} is missing, not a directory, or a symlink: {error}; no run logs scanned"),
        )
    })?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err(RunLogCorpusWarning::new(
            RunLogCorpusWarningKind::RootMissing,
            root.to_owned(),
            format!(
                "log root {display} is missing, not a directory, or a symlink; no run logs scanned"
            ),
        ));
    }
    fs::canonicalize(root).map_err(|error| {
        RunLogCorpusWarning::new(
            RunLogCorpusWarningKind::RootMissing,
            root.to_owned(),
            format!("log root {display} is missing or unreadable: {error}; no run logs scanned"),
        )
    })
}
fn safe_child_directories(root: &Path) -> ChildDirectoryScan {
    let resolved_root = match resolve_safe_root(root) {
        Ok(path) => path,
        Err(warning) => return ChildDirectoryScan::warning(warning),
    };
    let root_display = root.display();
    let entries = match fs::read_dir(root) {
        Ok(entries) => entries,
        Err(error) => {
            return ChildDirectoryScan::warning(RunLogCorpusWarning::new(
                RunLogCorpusWarningKind::RootUnreadable,
                root.to_owned(),
                format!(
                    "log root {root_display} could not be enumerated: {error}; no run logs scanned"
                ),
            ));
        }
    };
    let mut directories = Vec::new();
    let mut warnings = Vec::new();
    for entry in entries {
        let entry = match entry {
            Ok(entry) => entry,
            Err(error) => {
                warnings.push(RunLogCorpusWarning::new(
                    RunLogCorpusWarningKind::RootUnreadable,
                    root.to_owned(),
                    format!("log root {root_display} could not be enumerated: {error}; no run logs scanned"),
                ));
                continue;
            }
        };
        let path = entry.path();
        let display = path.display();
        let metadata = match fs::symlink_metadata(&path) {
            Ok(metadata) => metadata,
            Err(error) => {
                warnings.push(RunLogCorpusWarning::new(
                    RunLogCorpusWarningKind::ChildUnresolvable,
                    path.clone(),
                    format!("could not inspect run directory {display}: {error}; skipping"),
                ));
                continue;
            }
        };
        if metadata.file_type().is_symlink() {
            warnings.push(RunLogCorpusWarning::new(
                RunLogCorpusWarningKind::ChildSymlink,
                path.clone(),
                format!("run directory {display} is a symlink; skipping"),
            ));
            continue;
        }
        if !metadata.is_dir() {
            continue;
        }
        let resolved = match fs::canonicalize(&path) {
            Ok(resolved) => resolved,
            Err(error) => {
                warnings.push(RunLogCorpusWarning::new(
                    RunLogCorpusWarningKind::ChildUnresolvable,
                    path.clone(),
                    format!("could not resolve run directory {display}: {error}; skipping"),
                ));
                continue;
            }
        };
        if !resolved.starts_with(&resolved_root) {
            warnings.push(RunLogCorpusWarning::new(
                RunLogCorpusWarningKind::ChildEscapes,
                path.clone(),
                format!("run directory {display} resolves outside {root_display}; skipping"),
            ));
            continue;
        }
        directories.push(path);
    }
    directories.sort();
    warnings.sort_by(|left, right| left.path().cmp(right.path()));
    ChildDirectoryScan {
        directories,
        warnings,
    }
}
#[derive(Clone, Copy)]
enum TimestampRead {
    Value(DateTime<Utc>),
    Empty,
    Invalid,
}
enum VersionRead {
    Value(String),
    Empty,
    Invalid,
}
fn is_regular_file(path: &Path) -> bool {
    fs::symlink_metadata(path)
        .is_ok_and(|metadata| !metadata.file_type().is_symlink() && metadata.is_file())
}
fn load_metadata_candidate(path: &Path) -> Option<RunLogManifest> {
    if !is_regular_file(path) {
        return None;
    }
    let Value::Object(fields) = serde_json::from_slice(&fs::read(path).ok()?).ok()? else {
        return None;
    };
    Some(RunLogManifest::metadata_candidate(fields))
}
fn positive_issue_number(value: Option<&Value>) -> Option<u64> {
    match value? {
        Value::Bool(_) | Value::Null | Value::Array(_) | Value::Object(_) => None,
        Value::Number(number) => number
            .as_u64()
            .or_else(|| number.as_i64().and_then(|value| u64::try_from(value).ok()))
            .or_else(|| number.as_f64().and_then(positive_float_to_u64))
            .filter(|value| *value > 0),
        Value::String(value) => {
            let normalized = value.trim().replace(',', "");
            normalized
                .parse::<u64>()
                .ok()
                .or_else(|| {
                    normalized
                        .parse::<i64>()
                        .ok()
                        .and_then(|value| u64::try_from(value).ok())
                })
                .or_else(|| {
                    normalized
                        .parse::<f64>()
                        .ok()
                        .and_then(positive_float_to_u64)
                })
                .filter(|value| *value > 0)
        }
    }
}
fn positive_float_to_u64(value: f64) -> Option<u64> {
    if !value.is_finite() || value <= 0.0 {
        return None;
    }
    value.trunc().to_string().parse().ok()
}
fn parse_timestamp(value: &str) -> Option<DateTime<Utc>> {
    DateTime::parse_from_rfc3339(value)
        .map(|value| value.with_timezone(&Utc))
        .or_else(|_| {
            NaiveDateTime::parse_from_str(value, "%Y-%m-%dT%H:%M:%S%.f")
                .map(|value| value.and_utc())
        })
        .or_else(|_| {
            NaiveDateTime::parse_from_str(value, "%Y-%m-%d %H:%M:%S%.f")
                .map(|value| value.and_utc())
        })
        .or_else(|_| {
            NaiveDate::parse_from_str(value, "%Y-%m-%d").map(|value| {
                value
                    .and_hms_opt(0, 0, 0)
                    .expect("midnight is always a valid time")
                    .and_utc()
            })
        })
        .ok()
}
fn valid_larch_version(value: &str) -> bool {
    let value = value.strip_prefix(['v', 'V']).unwrap_or(value);
    let (base, suffix) = value.find(['-', '+']).map_or((value, None), |index| {
        (&value[..index], Some(&value[index + 1..]))
    });
    let component_count = base.split('.').count();
    (1..=3).contains(&component_count)
        && base.split('.').all(|component| {
            !component.is_empty() && component.bytes().all(|byte| byte.is_ascii_digit())
        })
        && suffix.is_none_or(|suffix| {
            !suffix.is_empty()
                && suffix
                    .bytes()
                    .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'-'))
        })
}
fn is_contained_regular_file(run_dir: &Path, path: &Path) -> bool {
    if !is_regular_file(path) {
        return false;
    }
    let (Ok(resolved_run), Ok(resolved_path)) = (fs::canonicalize(run_dir), fs::canonicalize(path))
    else {
        return false;
    };
    resolved_path.starts_with(resolved_run)
}
fn sorted_children(path: &Path) -> std::io::Result<Vec<PathBuf>> {
    let mut children = fs::read_dir(path)?
        .map(|entry| entry.map(|entry| entry.path()))
        .collect::<std::io::Result<Vec<_>>>()?;
    children.sort();
    Ok(children)
}
fn exact_round_number(value: &str) -> Option<u32> {
    let number = value.strip_prefix("round-")?;
    (!number.is_empty() && number.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| number.parse().ok())
        .flatten()
}
fn round_number_in_name(value: &str) -> Option<u32> {
    let (offset, _) = value.match_indices("round-").next()?;
    let suffix = &value[offset..];
    let digits: String = suffix["round-".len()..]
        .chars()
        .take_while(char::is_ascii_digit)
        .collect();
    (!digits.is_empty()).then(|| digits.parse().ok()).flatten()
}
fn classification_path_matches(skill: &str, relative: &Path) -> bool {
    let parts: Vec<_> = relative.iter().filter_map(|part| part.to_str()).collect();
    match skill {
        "design" => {
            parts.len() == 3 && parts[0] == "plan-review" && exact_round_number(parts[1]).is_some()
        }
        "implement" => parts.len() == 2 && exact_round_number(parts[0]).is_some(),
        _ => false,
    }
}
fn is_review_classification_name(value: &str) -> bool {
    value
        .strip_prefix("review-findings-classification-round-")
        .and_then(|suffix| suffix.strip_suffix(".tsv"))
        .is_some()
}
fn sort_classification_paths(paths: &mut [PathBuf], sort: RunLogRoundSort) {
    match sort {
        RunLogRoundSort::Lexical => paths.sort(),
        RunLogRoundSort::Numeric => paths.sort_by(|left, right| {
            let left_round = round_number_from_path(left);
            let right_round = round_number_from_path(right);
            (left_round.is_none(), left_round.unwrap_or(0), left).cmp(&(
                right_round.is_none(),
                right_round.unwrap_or(0),
                right,
            ))
        }),
    }
}
