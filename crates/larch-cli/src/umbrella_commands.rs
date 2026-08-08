//! The five `/umbrella` verbs that prepare a source issue and own its record.
//!
//! `/umbrella` files a flat set of leaf issues from one approved decomposition.
//! The skill decides what the leaves are; these verbs decide what survives a
//! crash between two of them:
//!
//! * `prepare` reads the source issue once and refuses everything the flow
//!   cannot convert — a closed issue, a pull request, an issue already carrying
//!   a plan block, and an `[UMBRELLA]` without a durable record. The one
//!   protected-title carve-out is the prepared-partition path, and it is only
//!   reachable with `--managed-partition true`.
//! * `persist-proposal` publishes the record before any leaf is filed, either
//!   from a caller-drafted record or from an exact parent-approved partition
//!   whose batch and edge list are read only through their declared roots.
//! * `mark-in-flight`, `record-resolved`, and `reconcile-in-flight` move one
//!   named leaf between the three states the record recognizes. Recovery binds
//!   a leaf only to a single remote issue carrying its exact title and body.
//!
//! Every refusal publishes `UMBRELLA_FAILED=true` and one stable `REASON=`
//! token at exit code 2, matching the Python contract callers branch on. Issue
//! text and stored records are untrusted (G-Sec-2): they are hashed, compared,
//! and re-rendered, never interpreted.

use crate::{
    github_repository_resolution::validate_repo_slug,
    github_service::{ServiceFailure, with_github_service},
};
use larch_adapters::{
    ConfinedPath, PathIntent, TemporaryRoot, atomic_write_utf8, github::OctocrabGitHubService,
    read_utf8, runtime::Cancellation,
};
use larch_core::{
    CandidateIssue, GitHubIssueState, GitHubService, ProposalRecord, ResolvedLeaf,
    UmbrellaSnapshot, check_leaf_cap, classify_umbrella_source, emit_kv,
    is_managed_partition_title, is_positive_decimal, mark_leaf_in_flight, parse_proposal,
    prepare_proposal_from_batch, reconcile_in_flight, record_leaf_resolved, render_proposal,
    render_snapshot,
};
use serde_json::Value;
use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

/// Exit code every refused umbrella verb reports.
const EXIT_REFUSED: u8 = 2;
/// Mode bits a published record and snapshot carry.
const RECORD_MODE: u32 = 0o600;

/// Publish the refusal contract two rows at a time and report its exit code.
fn refuse(reason: &str) -> ExitCode {
    emit_kv("UMBRELLA_FAILED", "true");
    emit_kv("REASON", reason);
    ExitCode::from(EXIT_REFUSED)
}

/// Read one strict `--flag value` command line, as the Python readers did.
///
/// Every token must name a permitted flag that has not been seen and must be
/// followed by its value; anything else is a usage refusal. There are no
/// positional arguments, no `=` spellings, and no repeats.
fn parse_values(arguments: &[OsString], permitted: &[&str]) -> Option<BTreeMap<String, String>> {
    let mut values = BTreeMap::new();
    let mut index = 0;
    while index < arguments.len() {
        let flag = arguments[index].to_str()?;
        if !permitted.contains(&flag) || values.contains_key(flag) || index + 1 >= arguments.len() {
            return None;
        }
        let value = arguments[index + 1].to_str()?;
        let _ = values.insert(flag.to_owned(), value.to_owned());
        index += 2;
    }
    Some(values)
}

/// Report whether every required flag is present.
fn has_required(values: &BTreeMap<String, String>, required: &[&str]) -> bool {
    required.iter().all(|flag| values.contains_key(*flag))
}

/// Read the optional `--managed-partition` boolean, refusing any other word.
fn managed_partition(values: &BTreeMap<String, String>) -> Option<bool> {
    match values
        .get("--managed-partition")
        .map_or("false", String::as_str)
    {
        "true" => Some(true),
        "false" => Some(false),
        _ => None,
    }
}

/// Resolve one command-line path against the working directory.
fn absolute(path: &str, reason: &'static str) -> Result<PathBuf, &'static str> {
    let candidate = Path::new(path);
    if candidate.is_absolute() {
        return Ok(candidate.to_path_buf());
    }
    env::current_dir()
        .map(|directory| directory.join(candidate))
        .map_err(|_| reason)
}

/// Re-anchor one declared path onto the canonical spelling of its root.
///
/// A trusted root is canonical, so a path declared through a platform alias
/// such as the macOS `/tmp` would otherwise read as an escape. Containment is
/// still decided by the declared spelling, exactly as the Python owner decided
/// it, and the confinement below re-checks the result for traversal, symlinked
/// components, and file type.
fn anchored(
    root: &TemporaryRoot,
    declared_root: &Path,
    path: &Path,
    intent: PathIntent,
    reason: &'static str,
) -> Result<ConfinedPath, &'static str> {
    let relative = path.strip_prefix(declared_root).map_err(|_| reason)?;
    root.confine(root.path().join(relative), intent)
        .map_err(|_| reason)
}

/// Publish one artifact atomically through its own parent directory.
///
/// The parent is resolved as a trusted root, so the published leaf may not be a
/// symlink and the write cannot follow one out of the directory the caller
/// named.
fn publish(path: &str, text: &str, reason: &'static str) -> Result<(), &'static str> {
    let target = absolute(path, reason)?;
    let parent = target.parent().ok_or(reason)?;
    let root = TemporaryRoot::resolve(Some(parent)).map_err(|_| reason)?;
    let confined = anchored(&root, parent, &target, PathIntent::Write, reason)?;
    atomic_write_utf8(&confined, text, RECORD_MODE).map_err(|_| reason)
}

/// Read one durable record from a caller-named path.
fn load_record(path: &str) -> Result<ProposalRecord, &'static str> {
    let text = fs::read_to_string(path).map_err(|_| "invalid-proposal-record")?;
    let record = parse_proposal(&text).map_err(larch_core::UmbrellaRefusal::reason)?;
    if validate_repo_slug(&record.repository) {
        Ok(record)
    } else {
        Err("invalid-proposal-record")
    }
}

/// Publish one record after proving it stays inside the leaf bound.
fn persist_record(path: &str, record: &ProposalRecord) -> Result<(), &'static str> {
    check_leaf_cap(record).map_err(larch_core::UmbrellaRefusal::reason)?;
    publish(path, &render_proposal(record), "proposal-write-failed")
}

/// The one GitHub effect `/umbrella` preparation performs, behind one seam.
///
/// Preparation is a judgement about a source issue: which titles and bodies may
/// become an umbrella, which may resume one, and which may not be touched at
/// all. That judgement is only testable if the read is replaceable, so it goes
/// through this trait and the live implementation makes no decision of its own.
trait SnapshotSource {
    /// Read one bounded source snapshot, or name the refusal reason.
    fn read(&self, repository: &str, issue: &str) -> Result<UmbrellaSnapshot, &'static str>;
}

/// The live source: one typed issue read through the hardened GitHub client.
struct LiveSnapshotSource;

impl SnapshotSource for LiveSnapshotSource {
    fn read(&self, repository: &str, issue: &str) -> Result<UmbrellaSnapshot, &'static str> {
        if !validate_repo_slug(repository) || !is_positive_decimal(issue) {
            return Err("invalid-identity");
        }
        let reference = crate::github_repository_resolution::repository_ref(repository)
            .map_err(|()| "invalid-identity")?;
        let number: u64 = issue.parse().map_err(|_| "invalid-identity")?;
        let subject = match with_github_service(async |service, cancellation| {
            read_issue(service, cancellation, &reference, number).await
        }) {
            Ok(subject) => subject,
            Err(ServiceFailure::Setup(_) | ServiceFailure::Operation(_)) => {
                return Err("read-failed");
            }
        };
        // `gh issue view` refused a pull request number outright, so the
        // observable Python outcome for one was the transport refusal below.
        if subject.is_pull_request || subject.number != number {
            return Err("read-failed");
        }
        // The freshness field is republished as a contract row, so a value that
        // could forge a second row is refused the way Python refused one whose
        // shape was not an exact UTC timestamp.
        if subject.updated_at.is_empty() || subject.updated_at.contains(['\r', '\n']) {
            return Err("invalid-read-back");
        }
        Ok(UmbrellaSnapshot {
            repository: repository.to_owned(),
            number: issue.to_owned(),
            title: subject.title,
            body: subject.body,
            state: match subject.state {
                GitHubIssueState::Open => "OPEN",
                GitHubIssueState::Closed | GitHubIssueState::All => "CLOSED",
            }
            .to_owned(),
            updated_at: subject.updated_at,
        })
    }
}

async fn read_issue(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    reference: &larch_core::GitHubRepositoryRef,
    number: u64,
) -> Result<larch_core::GitHubIssue, String> {
    service
        .issue(reference, number, cancellation)
        .await
        .map_err(|error| error.to_string())
}

/// Validate one source issue and publish its bounded snapshot.
pub fn prepare(arguments: &[OsString]) -> ExitCode {
    let Some(values) = parse_values(
        arguments,
        &["--repo", "--issue", "--output", "--managed-partition"],
    ) else {
        return refuse("usage");
    };
    if !has_required(&values, &["--repo", "--issue", "--output"]) {
        return refuse("usage");
    }
    let Some(managed) = managed_partition(&values) else {
        return refuse("usage");
    };
    match prepare_with(
        &LiveSnapshotSource,
        &values["--repo"],
        &values["--issue"],
        &values["--output"],
        managed,
    ) {
        Ok(updated_at) => {
            emit_kv("UMBRELLA_READY", "true");
            emit_kv("UPDATED_AT", &updated_at);
            ExitCode::SUCCESS
        }
        Err(reason) => refuse(reason),
    }
}

/// Read, classify, and publish one source snapshot; report its freshness field.
fn prepare_with(
    source: &impl SnapshotSource,
    repository: &str,
    issue: &str,
    output: &str,
    managed: bool,
) -> Result<String, &'static str> {
    let snapshot = source.read(repository, issue)?;
    classify_umbrella_source(&snapshot.title, &snapshot.body, &snapshot.state, managed)
        .map_err(larch_core::UmbrellaRefusal::reason)?;
    publish(output, &render_snapshot(&snapshot), "snapshot-failed")?;
    Ok(snapshot.updated_at)
}

/// Publish the durable record, from a drafted record or a parent partition.
pub fn persist_proposal(arguments: &[OsString]) -> ExitCode {
    let prepared_flags = [
        "--snapshot",
        "--prepared-root",
        "--prepared-input",
        "--prepared-deps",
        "--completion-sentinel",
        "--output-root",
        "--output",
        "--issue-input-output",
        "--deps-output",
    ];
    let mut permitted = vec!["--proposal"];
    permitted.extend_from_slice(&prepared_flags);
    let Some(values) = parse_values(arguments, &permitted) else {
        return refuse("usage");
    };
    if values.contains_key("--proposal") {
        if values.len() != 2 || !values.contains_key("--output") {
            return refuse("usage");
        }
        return match load_record(&values["--proposal"])
            .and_then(|record| persist_record(&values["--output"], &record))
        {
            Ok(()) => {
                emit_kv("PROPOSAL_PERSISTED", "true");
                ExitCode::SUCCESS
            }
            Err(reason) => refuse(reason),
        };
    }
    if values.len() != prepared_flags.len() {
        return refuse("usage");
    }
    match persist_prepared_proposal(&values) {
        Ok(leaves) => {
            emit_kv("PROPOSAL_PERSISTED", "true");
            emit_kv("LEAF_COUNT", &leaves.to_string());
            ExitCode::SUCCESS
        }
        Err(reason) => refuse(reason),
    }
}

/// The two trusted roots one prepared-partition invocation declares.
struct PreparedRoots {
    prepared: TemporaryRoot,
    prepared_declared: PathBuf,
    output: TemporaryRoot,
    output_declared: PathBuf,
}

impl PreparedRoots {
    /// Confine one declared prepared-artifact path for a declared use.
    fn prepared(&self, path: &str, intent: PathIntent) -> Result<ConfinedPath, &'static str> {
        anchored(
            &self.prepared,
            &self.prepared_declared,
            Path::new(path),
            intent,
            "invalid-prepared-partition",
        )
    }

    /// Confine one declared output path for a declared use.
    fn output(&self, path: &str, intent: PathIntent) -> Result<ConfinedPath, &'static str> {
        anchored(
            &self.output,
            &self.output_declared,
            Path::new(path),
            intent,
            "invalid-prepared-partition",
        )
    }
}

/// Convert one exact parent-approved partition into the durable record.
///
/// The completion sentinel is checked first: its presence means the parent
/// already consumed this partition, so re-running would file a second copy of
/// every leaf. Every read and write below is confined to the root the caller
/// declared for it, so a prepared artifact cannot name a file outside it.
fn persist_prepared_proposal(values: &BTreeMap<String, String>) -> Result<usize, &'static str> {
    let paths = [
        "--snapshot",
        "--prepared-root",
        "--prepared-input",
        "--prepared-deps",
        "--completion-sentinel",
        "--output-root",
        "--output",
        "--issue-input-output",
        "--deps-output",
    ];
    if paths
        .iter()
        .any(|flag| !Path::new(&values[*flag]).is_absolute())
    {
        return Err("invalid-prepared-path");
    }
    let roots = PreparedRoots {
        prepared: TemporaryRoot::resolve(Some(Path::new(&values["--prepared-root"])))
            .map_err(|_| "invalid-prepared-partition")?,
        prepared_declared: PathBuf::from(&values["--prepared-root"]),
        output: TemporaryRoot::resolve(Some(Path::new(&values["--output-root"])))
            .map_err(|_| "invalid-prepared-partition")?,
        output_declared: PathBuf::from(&values["--output-root"]),
    };
    let sentinel = roots.prepared(&values["--completion-sentinel"], PathIntent::Write)?;
    if sentinel.path().exists() {
        return Err("stale-completion-sentinel");
    }
    let snapshot = read_prepared_snapshot(&roots, &values["--snapshot"])?;
    let input_text = read_utf8(&roots.prepared(&values["--prepared-input"], PathIntent::Read)?)
        .map_err(|_| "invalid-prepared-partition")?;
    let deps_text = read_utf8(&roots.prepared(&values["--prepared-deps"], PathIntent::Read)?)
        .map_err(|_| "invalid-prepared-partition")?;
    let (record, issue_input) = prepare_proposal_from_batch(&snapshot, &input_text, &deps_text)
        .map_err(larch_core::UmbrellaRefusal::reason)?;
    for (flag, text) in [
        ("--output", render_proposal(&record)),
        ("--issue-input-output", issue_input),
        ("--deps-output", deps_text),
    ] {
        atomic_write_utf8(
            &roots.output(&values[flag], PathIntent::Write)?,
            &text,
            RECORD_MODE,
        )
        .map_err(|_| "invalid-prepared-partition")?;
    }
    Ok(record.leaves.len())
}

/// Read the managed source snapshot the parent partition was approved against.
fn read_prepared_snapshot(
    roots: &PreparedRoots,
    path: &str,
) -> Result<UmbrellaSnapshot, &'static str> {
    let text = read_utf8(&roots.output(path, PathIntent::Read)?)
        .map_err(|_| "invalid-prepared-partition")?;
    let value: Value = serde_json::from_str(&text).map_err(|_| "invalid-prepared-partition")?;
    let row = value.as_object().ok_or("invalid-prepared-partition")?;
    let mut snapshot = UmbrellaSnapshot::default();
    for (field, slot) in [
        ("repository", &mut snapshot.repository),
        ("number", &mut snapshot.number),
        ("title", &mut snapshot.title),
        ("body", &mut snapshot.body),
        ("state", &mut snapshot.state),
        ("updated_at", &mut snapshot.updated_at),
    ] {
        match row.get(field) {
            Some(Value::String(value)) => slot.clone_from(value),
            _ => return Err("invalid-snapshot"),
        }
    }
    if !is_positive_decimal(&snapshot.number) {
        return Err("invalid-umbrella");
    }
    if !validate_repo_slug(&snapshot.repository)
        || !snapshot.state.eq_ignore_ascii_case("open")
        || snapshot.updated_at.is_empty()
        || !is_managed_partition_title(&snapshot.title)
    {
        return Err("invalid-snapshot");
    }
    Ok(snapshot)
}

/// Record that one named leaf was handed to `/issue`.
pub fn mark_in_flight(arguments: &[OsString]) -> ExitCode {
    let Some(values) = parse_values(arguments, &["--proposal", "--identity"]) else {
        return refuse("usage");
    };
    if !has_required(&values, &["--proposal", "--identity"]) {
        return refuse("usage");
    }
    let outcome = load_record(&values["--proposal"]).and_then(|record| {
        let updated = mark_leaf_in_flight(&record, &values["--identity"])
            .map_err(larch_core::UmbrellaRefusal::reason)?;
        persist_record(&values["--proposal"], &updated)
    });
    match outcome {
        Ok(()) => {
            emit_kv("IN_FLIGHT_PERSISTED", "true");
            ExitCode::SUCCESS
        }
        Err(reason) => refuse(reason),
    }
}

/// Bind one named leaf to the remote issue `/issue` created for it.
pub fn record_resolved(arguments: &[OsString]) -> ExitCode {
    let Some(values) = parse_values(
        arguments,
        &[
            "--proposal",
            "--identity",
            "--number",
            "--url",
            "--issue-id",
        ],
    ) else {
        return refuse("usage");
    };
    if !has_required(&values, &["--proposal", "--identity", "--number", "--url"]) {
        return refuse("usage");
    }
    let resolved = ResolvedLeaf {
        identity: values["--identity"].clone(),
        number: values["--number"].clone(),
        url: values["--url"].clone(),
        issue_id: values
            .get("--issue-id")
            .cloned()
            .unwrap_or_else(String::new),
    };
    match resolve_into(&values["--proposal"], &resolved) {
        Ok(()) => {
            emit_kv("RESOLVED_PERSISTED", "true");
            ExitCode::SUCCESS
        }
        Err(reason) => refuse(reason),
    }
}

/// Apply one resolution to the record on disk and republish it.
fn resolve_into(path: &str, resolved: &ResolvedLeaf) -> Result<(), &'static str> {
    if !is_positive_decimal(&resolved.number) {
        return Err("invalid-leaf");
    }
    // A row value carrying a line break could forge a second contract row, and
    // the Python emitter raised an unhandled error rather than refusing.
    if resolved.url.is_empty() || resolved.url.contains(['\r', '\n']) {
        return Err("invalid-resolved-leaf");
    }
    let record = load_record(path)?;
    let updated =
        record_leaf_resolved(&record, resolved).map_err(larch_core::UmbrellaRefusal::reason)?;
    persist_record(path, &updated)
}

/// Bind one in-flight leaf to the single remote issue that carries it.
pub fn reconcile_in_flight_command(arguments: &[OsString]) -> ExitCode {
    let Some(values) = parse_values(arguments, &["--proposal", "--identity", "--candidates"])
    else {
        return refuse("usage");
    };
    if !has_required(&values, &["--proposal", "--identity", "--candidates"]) {
        return refuse("usage");
    }
    match reconcile(
        &values["--proposal"],
        &values["--identity"],
        &values["--candidates"],
    ) {
        Ok(resolved) => {
            emit_kv("RECONCILED", "true");
            emit_kv("ISSUE_NUMBER", &resolved.number);
            emit_kv("ISSUE_URL", &resolved.url);
            ExitCode::SUCCESS
        }
        Err(reason) => refuse(reason),
    }
}

/// Recover one leaf from the candidate list and persist the binding.
fn reconcile(
    proposal: &str,
    identity: &str,
    candidates: &str,
) -> Result<ResolvedLeaf, &'static str> {
    let text = fs::read_to_string(candidates).map_err(|_| "invalid-proposal-record")?;
    let value: Value = serde_json::from_str(&text).map_err(|_| "invalid-proposal-record")?;
    let rows = value.as_array().ok_or("ambiguous-in-flight-recovery")?;
    let mut parsed = Vec::with_capacity(rows.len());
    for row in rows {
        parsed.push(candidate_issue(row).ok_or("ambiguous-in-flight-recovery")?);
    }
    let record = load_record(proposal)?;
    let resolved = reconcile_in_flight(&record, identity, &parsed)
        .map_err(larch_core::UmbrellaRefusal::reason)?;
    resolve_into(proposal, &resolved)?;
    Ok(resolved)
}

/// Read one candidate row, refusing anything that is not a JSON object.
///
/// A row that carries no usable number, URL, title, or body is kept with empty
/// fields so it can never match the recorded leaf, exactly as the Python
/// comparison treated a row whose fields had the wrong type.
fn candidate_issue(row: &Value) -> Option<CandidateIssue> {
    let row = row.as_object()?;
    let text = |key: &str| match row.get(key) {
        Some(Value::String(value)) => value.clone(),
        _ => String::new(),
    };
    let issue_id = match row.get("id") {
        Some(Value::String(value)) => value.clone(),
        Some(Value::Number(value)) => value.to_string(),
        _ => String::new(),
    };
    Some(CandidateIssue {
        number: row.get("number").and_then(Value::as_u64),
        url: text("url"),
        title: text("title"),
        body: text("body"),
        issue_id,
    })
}

#[cfg(test)]
mod tests {
    use super::{
        SnapshotSource, absolute, candidate_issue, load_record, mark_in_flight, parse_values,
        persist_prepared_proposal, persist_proposal, prepare, prepare_with, reconcile,
        reconcile_in_flight_command, record_resolved, resolve_into,
    };
    use larch_core::{
        ExpectedLeaf, LeafState, MANAGED_PARTITION_PREFIXES, ProposalRecord, ResolvedLeaf,
        UmbrellaSnapshot, leaf_identity, mark_leaf_in_flight, render_proposal,
        umbrella_leaf_opening_text,
    };
    use std::{
        collections::BTreeMap,
        ffi::OsString,
        fs,
        path::{Path, PathBuf},
        process::ExitCode,
    };
    use tempfile::TempDir;

    /// Resolve one temporary directory through every symlinked ancestor.
    ///
    /// The trusted-root readers refuse a symlinked component, and the platform
    /// temporary directory is reached through one on macOS, so a fixture names
    /// the resolved directory rather than the link that leads to it.
    fn root(directory: &TempDir) -> PathBuf {
        fs::canonicalize(directory.path()).expect("resolve the temporary root")
    }

    fn text_path(path: &Path) -> String {
        path.to_str().expect("utf-8 path").to_owned()
    }

    /// Compose one managed lifecycle title from the shared prefix owner.
    fn managed_title(rest: &str) -> String {
        format!("{}{rest}", MANAGED_PARTITION_PREFIXES[0])
    }

    /// Render one managed source snapshot with a caller-chosen issue number.
    fn managed_snapshot(number: &str) -> String {
        format!(
            "{{\"repository\": \"owner/repo\", \"number\": \"{number}\", \"title\": \"{}\", \"body\": \"Shared.\", \"state\": \"OPEN\", \"updated_at\": \"2026-08-03T00:00:00Z\"}}\n",
            managed_title("Split")
        )
    }

    struct FixedSource(Result<UmbrellaSnapshot, &'static str>);

    impl SnapshotSource for FixedSource {
        fn read(&self, _repository: &str, _issue: &str) -> Result<UmbrellaSnapshot, &'static str> {
            self.0.clone()
        }
    }

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn snapshot(title: &str, body: &str, state: &str) -> UmbrellaSnapshot {
        UmbrellaSnapshot {
            repository: "owner/repo".to_owned(),
            number: "12".to_owned(),
            title: title.to_owned(),
            body: body.to_owned(),
            state: state.to_owned(),
            updated_at: "2026-08-03T00:00:00Z".to_owned(),
        }
    }

    fn record() -> ProposalRecord {
        let body = format!(
            "{}\n\nImplement the leaf.",
            umbrella_leaf_opening_text("12")
        );
        let title = "[LEAF OF 12] One".to_owned();
        ProposalRecord {
            umbrella: "12".to_owned(),
            repository: "owner/repo".to_owned(),
            expected_updated_at: "2026-07-26T00:00:00Z".to_owned(),
            common_context: "context".to_owned(),
            leaves: vec![ExpectedLeaf {
                identity: leaf_identity(&title, &body),
                title,
                body,
                ..ExpectedLeaf::default()
            }],
            ..ProposalRecord::default()
        }
    }

    fn write(directory: &Path, name: &str, text: &str) -> String {
        let path = directory.join(name);
        fs::write(&path, text).expect("seed file");
        text_path(&path)
    }

    #[test]
    fn a_command_line_must_be_strict_flag_value_pairs() {
        assert_eq!(
            parse_values(&arguments(&["--a", "1"]), &["--a"]),
            Some(BTreeMap::from([("--a".to_owned(), "1".to_owned())]))
        );
        assert_eq!(parse_values(&arguments(&["--a"]), &["--a"]), None);
        assert_eq!(
            parse_values(&arguments(&["--a", "1", "--a", "2"]), &["--a"]),
            None
        );
        assert_eq!(parse_values(&arguments(&["--b", "1"]), &["--a"]), None);
        assert_eq!(parse_values(&arguments(&["--a=1"]), &["--a"]), None);
        assert!(
            absolute("relative", "proposal-write-failed")
                .expect("resolves")
                .is_absolute()
        );
    }

    #[test]
    fn preparation_publishes_only_a_convertible_source() {
        let directory = TempDir::new().expect("temporary directory");
        let output = text_path(&root(&directory).join("snapshot.json"));
        let source = FixedSource(Ok(snapshot("Regular issue", "Body.", "OPEN")));
        assert_eq!(
            prepare_with(&source, "owner/repo", "12", &output, false),
            Ok("2026-08-03T00:00:00Z".to_owned())
        );
        assert!(
            fs::read_to_string(&output)
                .expect("snapshot published")
                .starts_with("{\"body\": \"Body.\", \"number\": \"12\"")
        );
        for (source, managed, reason) in [
            (
                snapshot("Regular", "Body.", "CLOSED"),
                false,
                "closed-input",
            ),
            (
                snapshot("[PR] Thing", "Body.", "OPEN"),
                false,
                "incompatible-input",
            ),
            (
                snapshot(&managed_title("Work"), "<!-- larch:plan -->", "OPEN"),
                false,
                "incompatible-input",
            ),
            (
                snapshot("Regular", "Body.", "OPEN"),
                true,
                "incompatible-managed-partition",
            ),
            (
                snapshot("[UMBRELLA] Work", "Body.", "OPEN"),
                false,
                "incompatible-umbrella",
            ),
        ] {
            assert_eq!(
                prepare_with(
                    &FixedSource(Ok(source)),
                    "owner/repo",
                    "12",
                    &output,
                    managed
                ),
                Err(reason)
            );
        }
        assert_eq!(
            prepare_with(
                &FixedSource(Err("read-failed")),
                "owner/repo",
                "12",
                &output,
                false
            ),
            Err("read-failed")
        );
        assert_eq!(
            prepare_with(
                &FixedSource(Ok(snapshot(
                    &managed_title("Work"),
                    "<!-- larch:plan -->",
                    "OPEN"
                ))),
                "owner/repo",
                "12",
                "/larch-umbrella-missing-root/snapshot.json",
                true
            ),
            Err("snapshot-failed")
        );
    }

    #[test]
    fn a_leaf_moves_through_the_record_on_disk() {
        let directory = TempDir::new().expect("temporary directory");
        let identity = record().leaves[0].identity.clone();
        let marked = mark_leaf_in_flight(&record(), &identity).expect("marks in flight");
        // Named through the platform's own spelling, which reaches the
        // temporary root through a root-owned symlink on macOS.
        let path = write(directory.path(), "proposal.json", &render_proposal(&marked));
        let resolved = ResolvedLeaf {
            identity,
            number: "34".to_owned(),
            url: "https://example.test/issues/34".to_owned(),
            issue_id: "99".to_owned(),
        };
        assert_eq!(resolve_into(&path, &resolved), Ok(()));
        let stored = load_record(&path).expect("record reloads");
        assert_eq!(stored.leaves[0].state, LeafState::Resolved);
        assert_eq!(stored.leaves[0].number, "34");
        assert_eq!(
            resolve_into(
                &path,
                &ResolvedLeaf {
                    number: "0".to_owned(),
                    ..resolved.clone()
                }
            ),
            Err("invalid-leaf")
        );
        assert_eq!(
            resolve_into(
                &path,
                &ResolvedLeaf {
                    url: "https://example.test\nFORGED=true".to_owned(),
                    ..resolved.clone()
                }
            ),
            Err("invalid-resolved-leaf")
        );
        assert_eq!(
            resolve_into(
                &path,
                &ResolvedLeaf {
                    identity: "absent".to_owned(),
                    ..resolved
                }
            ),
            Err("unknown-leaf-identity")
        );
        assert_eq!(
            load_record("/larch-umbrella-absent.json"),
            Err("invalid-proposal-record")
        );
        let foreign = write(
            &root(&directory),
            "foreign.json",
            &render_proposal(&ProposalRecord {
                repository: "owner".to_owned(),
                ..record()
            }),
        );
        assert_eq!(load_record(&foreign), Err("invalid-proposal-record"));
    }

    #[test]
    fn recovery_persists_only_a_single_exact_match() {
        let directory = TempDir::new().expect("temporary directory");
        let identity = record().leaves[0].identity.clone();
        let marked = mark_leaf_in_flight(&record(), &identity).expect("marks in flight");
        let leaf = marked.leaves[0].clone();
        let path = write(
            &root(&directory),
            "proposal.json",
            &render_proposal(&marked),
        );
        let row = format!(
            "{{\"number\":34,\"url\":\"https://example.test/issues/34\",\"id\":99,\"title\":{},\"body\":{}}}",
            serde_json::to_string(&leaf.title).expect("title renders"),
            serde_json::to_string(&leaf.body).expect("body renders")
        );
        let candidates = write(&root(&directory), "candidates.json", &format!("[{row}]"));
        let resolved = reconcile(&path, &identity, &candidates).expect("recovers one issue");
        assert_eq!(
            (resolved.number.as_str(), resolved.issue_id.as_str()),
            ("34", "99")
        );
        assert_eq!(
            load_record(&path).expect("record reloads").leaves[0].state,
            LeafState::Resolved
        );
        let duplicated = write(&root(&directory), "two.json", &format!("[{row},{row}]"));
        assert_eq!(
            reconcile(&path, &identity, &duplicated),
            Err("ambiguous-in-flight-recovery")
        );
        let malformed = write(&root(&directory), "bad.json", "[3]");
        assert_eq!(
            reconcile(&path, &identity, &malformed),
            Err("ambiguous-in-flight-recovery")
        );
        let unusable = write(&root(&directory), "object.json", "{}");
        assert_eq!(
            reconcile(&path, &identity, &unusable),
            Err("ambiguous-in-flight-recovery")
        );
        assert_eq!(
            reconcile(&path, &identity, "/larch-umbrella-absent.json"),
            Err("invalid-proposal-record")
        );
        assert_eq!(
            candidate_issue(&serde_json::json!({"number": -3}))
                .expect("row parses")
                .number,
            None
        );
    }

    /// Drive each published entrypoint through its own argument vector.
    ///
    /// The five `pub fn` boundaries own the scanner, the required-flag check,
    /// and the contract rows a caller parses, so each is exercised here rather
    /// than only through the black-box parity cases.
    #[test]
    fn every_entrypoint_scans_its_own_command_line() {
        let directory = TempDir::new().expect("temporary directory");
        let sandbox = root(&directory);
        let identity = record().leaves[0].identity.clone();
        let marked = mark_leaf_in_flight(&record(), &identity).expect("marks in flight");
        let leaf = marked.leaves[0].clone();
        let path = write(&sandbox, "proposal.json", &render_proposal(&marked));
        let candidates = write(
            &sandbox,
            "candidates.json",
            &format!(
                "[{{\"number\":34,\"url\":\"https://example.test/issues/34\",\"id\":99,\"title\":{},\"body\":{}}}]",
                serde_json::to_string(&leaf.title).expect("title renders"),
                serde_json::to_string(&leaf.body).expect("body renders")
            ),
        );
        let refused = ExitCode::from(2);

        assert_eq!(prepare(&arguments(&["--repo", "owner/repo"])), refused);
        assert_eq!(prepare(&arguments(&["--repo"])), refused);
        assert_eq!(
            prepare(&arguments(&[
                "--repo",
                "owner/repo",
                "--issue",
                "12",
                "--output",
                "out.json",
                "--managed-partition",
                "maybe",
            ])),
            refused
        );
        assert_eq!(persist_proposal(&arguments(&[])), refused);
        assert_eq!(
            persist_proposal(&arguments(&[
                "--proposal",
                &path,
                "--output-root",
                &text_path(&sandbox)
            ])),
            refused
        );
        assert_eq!(
            persist_proposal(&arguments(&["--snapshot", &path])),
            refused
        );
        assert_eq!(mark_in_flight(&arguments(&["--proposal", &path])), refused);
        assert_eq!(
            record_resolved(&arguments(&["--proposal", &path, "--identity", &identity])),
            refused
        );
        assert_eq!(
            reconcile_in_flight_command(&arguments(&["--proposal", &path])),
            refused
        );

        let published = text_path(&sandbox.join("published.json"));
        assert_eq!(
            persist_proposal(&arguments(&["--proposal", &path, "--output", &published])),
            ExitCode::SUCCESS
        );
        assert_eq!(
            reconcile_in_flight_command(&arguments(&[
                "--proposal",
                &path,
                "--identity",
                &identity,
                "--candidates",
                &candidates,
            ])),
            ExitCode::SUCCESS
        );
        assert_eq!(
            load_record(&path).expect("record reloads").leaves[0].number,
            "34"
        );
        assert_eq!(
            mark_in_flight(&arguments(&["--proposal", &path, "--identity", &identity])),
            refused
        );
        assert_eq!(
            record_resolved(&arguments(&[
                "--proposal",
                &path,
                "--identity",
                &identity,
                "--number",
                "35",
                "--url",
                "https://example.test/issues/35",
            ])),
            ExitCode::SUCCESS
        );
    }

    #[test]
    fn a_prepared_partition_publishes_three_artifacts_below_its_roots() {
        let parent_directory = TempDir::new().expect("parent root");
        let child_directory = TempDir::new().expect("child root");
        let parent = root(&parent_directory);
        let child = root(&child_directory);
        let sentinel = parent.join("umbrella-complete.sentinel");
        let mut values = BTreeMap::from([
            (
                "--snapshot".to_owned(),
                write(&child, "snapshot.json", &managed_snapshot("12")),
            ),
            ("--prepared-root".to_owned(), text_path(&parent)),
            (
                "--prepared-input".to_owned(),
                write(
                    &parent,
                    "input.txt",
                    "### One\n\nFirst.\n\n### Two\n\nSecond.\n",
                ),
            ),
            (
                "--prepared-deps".to_owned(),
                write(&parent, "deps.tsv", "1\t2\n"),
            ),
            ("--completion-sentinel".to_owned(), text_path(&sentinel)),
            ("--output-root".to_owned(), text_path(&child)),
            (
                "--output".to_owned(),
                text_path(&child.join("proposal.json")),
            ),
            (
                "--issue-input-output".to_owned(),
                text_path(&child.join("issue-input.txt")),
            ),
            (
                "--deps-output".to_owned(),
                text_path(&child.join("deps.tsv")),
            ),
        ]);
        assert_eq!(persist_prepared_proposal(&values), Ok(2));
        let published = load_record(&values["--output"]).expect("record reloads");
        assert_eq!(published.leaves.len(), 2);
        assert_eq!(published.common_context, "Shared.");
        assert_eq!(
            fs::read_to_string(&values["--deps-output"]).expect("edge list copied"),
            "1\t2\n"
        );
        fs::write(&sentinel, "done\n").expect("seed the sentinel");
        assert_eq!(
            persist_prepared_proposal(&values),
            Err("stale-completion-sentinel")
        );
        fs::remove_file(&sentinel).expect("clear the sentinel");
        let _ = values.insert("--prepared-input".to_owned(), "relative.txt".to_owned());
        assert_eq!(
            persist_prepared_proposal(&values),
            Err("invalid-prepared-path")
        );
        let _ = values.insert(
            "--prepared-input".to_owned(),
            write(
                &parent,
                "outside.txt",
                "### One\n\nFirst.\n\n### Two\n\nSecond.\n",
            ),
        );
        let _ = values.insert(
            "--snapshot".to_owned(),
            write(
                &child,
                "unmanaged.json",
                "{\"repository\": \"owner/repo\", \"number\": \"12\", \"title\": \"Regular\", \"body\": \"Shared.\", \"state\": \"OPEN\", \"updated_at\": \"2026-08-03T00:00:00Z\"}\n",
            ),
        );
        assert_eq!(persist_prepared_proposal(&values), Err("invalid-snapshot"));
        let _ = values.insert(
            "--snapshot".to_owned(),
            write(&child, "zero.json", &managed_snapshot("0")),
        );
        assert_eq!(persist_prepared_proposal(&values), Err("invalid-umbrella"));
        let _ = values.insert(
            "--snapshot".to_owned(),
            write(&child, "malformed.json", "[]"),
        );
        assert_eq!(
            persist_prepared_proposal(&values),
            Err("invalid-prepared-partition")
        );
    }

    /// A prepared artifact must be a real regular file inside its own root.
    ///
    /// The three shapes below are the ones a parent partition could be
    /// redirected through: a link out of the declared root, a link inside it,
    /// and a directory standing where a file belongs.
    #[test]
    fn a_prepared_artifact_must_be_a_contained_regular_file() {
        let parent_directory = TempDir::new().expect("parent root");
        let child_directory = TempDir::new().expect("child root");
        let parent = root(&parent_directory);
        let child = root(&child_directory);
        let batch = "### One\n\nFirst.\n\n### Two\n\nSecond.\n";
        let outside = write(&child, "outside-input.txt", batch);
        let _ = write(&parent, "real-input.txt", batch);
        std::os::unix::fs::symlink(&outside, parent.join("escaping.txt")).expect("escaping link");
        std::os::unix::fs::symlink(parent.join("real-input.txt"), parent.join("inside.txt"))
            .expect("contained link");
        fs::create_dir(parent.join("directory.txt")).expect("directory in a file's place");
        let mut values = BTreeMap::from([
            (
                "--snapshot".to_owned(),
                write(&child, "snapshot.json", &managed_snapshot("12")),
            ),
            ("--prepared-root".to_owned(), text_path(&parent)),
            ("--prepared-input".to_owned(), String::new()),
            ("--prepared-deps".to_owned(), write(&parent, "deps.tsv", "")),
            (
                "--completion-sentinel".to_owned(),
                text_path(&parent.join("umbrella-complete.sentinel")),
            ),
            ("--output-root".to_owned(), text_path(&child)),
            (
                "--output".to_owned(),
                text_path(&child.join("proposal.json")),
            ),
            (
                "--issue-input-output".to_owned(),
                text_path(&child.join("issue-input.txt")),
            ),
            (
                "--deps-output".to_owned(),
                text_path(&child.join("deps.tsv")),
            ),
        ]);
        for name in ["escaping.txt", "inside.txt", "directory.txt"] {
            let _ = values.insert("--prepared-input".to_owned(), text_path(&parent.join(name)));
            assert_eq!(
                persist_prepared_proposal(&values),
                Err("invalid-prepared-partition"),
                "prepared input {name}"
            );
        }
        let _ = values.insert("--prepared-input".to_owned(), outside);
        assert_eq!(
            persist_prepared_proposal(&values),
            Err("invalid-prepared-partition")
        );
        let _ = values.insert(
            "--prepared-input".to_owned(),
            text_path(&parent.join("real-input.txt")),
        );
        assert_eq!(persist_prepared_proposal(&values), Ok(2));
    }
}
