//! The eight `/umbrella` verbs that prepare a source issue, own its record,
//! and close the run out.
//!
//! `/umbrella` files a flat set of leaf issues from one approved decomposition.
//! The skill decides what the leaves are; these verbs decide what survives a
//! crash between two of them:
//!
//! * `prepare` reads the source issue once and refuses everything the flow
//!   cannot convert — a closed issue, a pull request, an issue already carrying
//!   a plan block, and an ambiguous record-less `[UMBRELLA]`. A record-less
//!   umbrella is adopted only after its graph has no ambiguous larch-owned
//!   state. The one
//!   protected-title carve-out is the prepared-partition path, and it is only
//!   reachable with `--managed-partition true`.
//! * `persist-proposal` publishes the record before any leaf is filed, either
//!   from a caller-drafted record or from an exact parent-approved partition
//!   whose batch and edge list are read only through their declared roots.
//! * `mark-in-flight`, `record-resolved`, and `reconcile-in-flight` move one
//!   named leaf between the three states the record recognizes. Recovery binds
//!   a leaf only to a single remote issue carrying its exact title and body.
//! * `mutate` is the one live write: it converts the source issue into the
//!   final `[UMBRELLA]` title and body, refusing anything that would drop the
//!   prefix or the embedded record a resumed run reads.
//! * `verify` proves every recorded leaf is resolved, still on contract, and
//!   still the exact issue the record bound it to, and only then publishes the
//!   completion sentinel. `verify-completion` is the parent's half of that
//!   proof: it rebuilds the expected sentinel from the batch it approved and
//!   compares every row.
//!
//! Every refusal publishes `UMBRELLA_FAILED=true` and one stable `REASON=`
//! token at exit code 2, matching the Python contract callers branch on. Issue
//! text and stored records are untrusted (G-Sec-2): they are hashed, compared,
//! and re-rendered, never interpreted.

use crate::{
    github_repository_resolution::validate_repo_slug,
    github_service::{ServiceFailure, with_github_service},
    issue_mutation_support::authorization_request,
};
use larch_adapters::{
    ConfinedPath, PathIntent, TemporaryRoot, atomic_write_utf8,
    github::{DependencyRef, IssueMutationOwner, OctocrabGitHubService},
    read_utf8,
    runtime::Cancellation,
};
use larch_core::{
    ADOPTED_UMBRELLA_SOURCE, CandidateIssue, CompletionSentinel, GitHubIssueState, GitHubService,
    ISSUE_DEDUP_LIMIT, IssueMutationField, IssueMutationRequest, ProposalRecord, RemoteLeaf,
    ResolvedLeaf, UMBRELLA_PROPOSAL_TOKEN, UmbrellaSnapshot, check_leaf_cap,
    classify_umbrella_source, completion_sentinel_for_record, emit_kv,
    expected_completion_sentinel, is_managed_partition_title, is_positive_decimal,
    is_umbrella_title, mark_leaf_in_flight, parse_drafted_proposal, parse_proposal,
    prepare_proposal_from_batch, reconcile_in_flight, record_leaf_resolved, render_proposal,
    render_snapshot, validate_final_umbrella, verify_graph_state,
};
use serde_json::Value;
use std::{
    collections::{BTreeMap, BTreeSet},
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
/// Stable refusal emitted when a record-less umbrella is still blocked.
const OPEN_BLOCKERS: &str = "open-blockers";

const PREPARE_USAGE: &str = "Usage: umbrella prepare --repo OWNER/REPO --issue N --output PATH [--managed-partition true|false]";
const PERSIST_PROPOSAL_USAGE: &str = "Usage: umbrella persist-proposal (--proposal PATH --output PATH | --snapshot PATH --batch-input PATH [--deps PATH] --output PATH --issue-input-output PATH --deps-output PATH | --snapshot PATH --prepared-root PATH --prepared-input PATH --prepared-deps PATH --completion-sentinel PATH --output-root PATH --output PATH --issue-input-output PATH --deps-output PATH)";
const MARK_IN_FLIGHT_USAGE: &str =
    "Usage: umbrella mark-in-flight --proposal PATH --identity SHA256";
const RECORD_RESOLVED_USAGE: &str = "Usage: umbrella record-resolved --proposal PATH --identity SHA256 --number N --url URL [--issue-id ID]";
const RECONCILE_IN_FLIGHT_USAGE: &str =
    "Usage: umbrella reconcile-in-flight --proposal PATH --identity SHA256 --candidates PATH";
const MUTATE_USAGE: &str = "Usage: umbrella mutate --repo OWNER/REPO --issue N --title TITLE --body-file PATH [--managed-partition true|false] [--adopted-umbrella true|false]";
const VERIFY_USAGE: &str = "Usage: umbrella verify --proposal PATH --leaves PATH [--sentinel-file PATH --sentinel-root PATH --prepared-input PATH --prepared-deps PATH]";
const VERIFY_COMPLETION_USAGE: &str = "Usage: umbrella verify-completion --repo OWNER/REPO --issue N --sentinel-file PATH --sentinel-root PATH --prepared-input PATH --prepared-deps PATH";

/// Publish the refusal contract two rows at a time and report its exit code.
fn refuse(reason: &str) -> ExitCode {
    emit_kv("UMBRELLA_FAILED", "true");
    emit_kv("REASON", reason);
    ExitCode::from(EXIT_REFUSED)
}

/// Print the owning verb's usage whenever the stable refusal reason is usage.
fn refuse_with_usage(reason: &str, usage: &str) -> ExitCode {
    if reason == "usage" {
        eprintln!("{usage}");
    }
    refuse(reason)
}

/// Honor the raw-parser help spelling before interpreting the remaining line.
fn help_requested(arguments: &[OsString], usage: &str) -> Option<ExitCode> {
    if arguments
        .iter()
        .any(|argument| matches!(argument.to_str(), Some("-h" | "--help")))
    {
        eprintln!("{usage}");
        Some(ExitCode::SUCCESS)
    } else {
        None
    }
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

/// Read one optional boolean flag, refusing any word other than `true` or `false`.
fn optional_boolean(values: &BTreeMap<String, String>, flag: &str) -> Option<bool> {
    match values.get(flag).map_or("false", String::as_str) {
        "true" => Some(true),
        "false" => Some(false),
        _ => None,
    }
}

/// Read the optional `--managed-partition` boolean.
fn managed_partition(values: &BTreeMap<String, String>) -> Option<bool> {
    optional_boolean(values, "--managed-partition")
}

/// Read the optional `--adopted-umbrella` boolean.
fn adopted_umbrella(values: &BTreeMap<String, String>) -> Option<bool> {
    optional_boolean(values, "--adopted-umbrella")
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

/// Read one caller-drafted record with actionable leaf-contract refusals.
fn load_drafted_record(path: &str) -> Result<ProposalRecord, &'static str> {
    let text = fs::read_to_string(path).map_err(|_| "invalid-proposal-record")?;
    let record = parse_drafted_proposal(&text).map_err(larch_core::UmbrellaRefusal::reason)?;
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
/// through this trait and the live implementation provides only graph evidence.
struct SnapshotRead {
    snapshot: UmbrellaSnapshot,
    adoption_safe: bool,
}

trait SnapshotSource {
    /// Read one bounded source snapshot, or name the refusal reason.
    fn read(&self, repository: &str, issue: &str) -> Result<SnapshotRead, &'static str>;
}

/// The live source: one typed issue read through the hardened GitHub client.
struct LiveSnapshotSource;

impl SnapshotSource for LiveSnapshotSource {
    fn read(&self, repository: &str, issue: &str) -> Result<SnapshotRead, &'static str> {
        if !validate_repo_slug(repository) || !is_positive_decimal(issue) {
            return Err("invalid-identity");
        }
        let reference = crate::github_repository_resolution::repository_ref(repository)
            .map_err(|()| "invalid-identity")?;
        let number: u64 = issue.parse().map_err(|_| "invalid-identity")?;
        let source = match with_github_service(async |service, cancellation| {
            read_source_snapshot(service, cancellation, &reference, repository, issue, number).await
        }) {
            Ok(source) => source,
            Err(ServiceFailure::Operation(reason)) if reason == "invalid-read-back" => {
                return Err("invalid-read-back");
            }
            Err(ServiceFailure::Operation(reason)) if reason == OPEN_BLOCKERS => {
                return Err(OPEN_BLOCKERS);
            }
            Err(ServiceFailure::Setup(_) | ServiceFailure::Operation(_)) => {
                return Err("read-failed");
            }
        };
        Ok(source)
    }
}

async fn read_source_snapshot(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    reference: &larch_core::GitHubRepositoryRef,
    repository: &str,
    issue: &str,
    number: u64,
) -> Result<SnapshotRead, String> {
    let subject = read_issue(service, cancellation, reference, number).await?;
    // `gh issue view` refused a pull request number outright, so the
    // observable Python outcome for one was the transport refusal below.
    if subject.is_pull_request || subject.number != number {
        return Err("read-failed".to_owned());
    }
    // The freshness field is republished as a contract row, so a value that
    // could forge a second row is refused the way Python refused one whose
    // shape was not an exact UTC timestamp.
    if subject.updated_at.is_empty() || subject.updated_at.contains(['\r', '\n']) {
        return Err("invalid-read-back".to_owned());
    }
    let adoption_safe = subject.state == GitHubIssueState::Open
        && is_umbrella_title(&subject.title)
        && !subject.body.contains(UMBRELLA_PROPOSAL_TOKEN)
        && adoption_graph_is_unambiguous(service, cancellation, reference, number).await?;
    Ok(SnapshotRead {
        snapshot: UmbrellaSnapshot {
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
            adopted_umbrella: false,
        },
        adoption_safe,
    })
}

/// Prove a record-less umbrella has no graph state that blocks its adoption.
///
/// Closed blockers are already satisfied and need no inspection. An open
/// blocker means the umbrella is not ready, while direct children make the
/// graph incompatible. Dependency metadata supplies those facts, so this must
/// never fetch a blocker issue or its body.
async fn adoption_graph_is_unambiguous(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    reference: &larch_core::GitHubRepositoryRef,
    umbrella: u64,
) -> Result<bool, String> {
    let direct_children = service
        .list_sub_issues(cancellation, reference.owner(), reference.name(), umbrella)
        .await
        .map_err(|error| error.to_string())?;
    if !direct_children.is_empty() {
        return Ok(false);
    }
    let blockers = service
        .list_blocked_by(cancellation, reference.owner(), reference.name(), umbrella)
        .await
        .map_err(|error| error.to_string())?;
    if blockers.iter().any(DependencyRef::is_open) {
        return Err(OPEN_BLOCKERS.to_owned());
    }
    Ok(true)
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
    if let Some(exit_code) = help_requested(arguments, PREPARE_USAGE) {
        return exit_code;
    }
    let Some(values) = parse_values(
        arguments,
        &["--repo", "--issue", "--output", "--managed-partition"],
    ) else {
        return refuse_with_usage("usage", PREPARE_USAGE);
    };
    if !has_required(&values, &["--repo", "--issue", "--output"]) {
        return refuse_with_usage("usage", PREPARE_USAGE);
    }
    let Some(managed) = managed_partition(&values) else {
        return refuse_with_usage("usage", PREPARE_USAGE);
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
        Err(reason) => refuse_with_usage(reason, PREPARE_USAGE),
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
    let mut source = source.read(repository, issue)?;
    let classification = classify_umbrella_source(
        &source.snapshot.title,
        &source.snapshot.body,
        &source.snapshot.state,
        managed,
        source.adoption_safe,
    )
    .map_err(larch_core::UmbrellaRefusal::reason)?;
    source.snapshot.adopted_umbrella = classification.is_adopted();
    publish(
        output,
        &render_snapshot(&source.snapshot),
        "snapshot-failed",
    )?;
    Ok(source.snapshot.updated_at)
}

/// Publish the durable record, from a drafted record or a parent partition.
pub fn persist_proposal(arguments: &[OsString]) -> ExitCode {
    if let Some(exit_code) = help_requested(arguments, PERSIST_PROPOSAL_USAGE) {
        return exit_code;
    }
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
    let standard_required = [
        "--snapshot",
        "--batch-input",
        "--output",
        "--issue-input-output",
        "--deps-output",
    ];
    let permitted = [
        "--proposal",
        "--snapshot",
        "--batch-input",
        "--deps",
        "--prepared-root",
        "--prepared-input",
        "--prepared-deps",
        "--completion-sentinel",
        "--output-root",
        "--output",
        "--issue-input-output",
        "--deps-output",
    ];
    let Some(values) = parse_values(arguments, &permitted) else {
        return refuse_with_usage("usage", PERSIST_PROPOSAL_USAGE);
    };
    if values.contains_key("--proposal") {
        if values.len() != 2 || !values.contains_key("--output") {
            return refuse_with_usage("usage", PERSIST_PROPOSAL_USAGE);
        }
        return match load_drafted_record(&values["--proposal"])
            .and_then(|record| persist_record(&values["--output"], &record))
        {
            Ok(()) => {
                emit_kv("PROPOSAL_PERSISTED", "true");
                ExitCode::SUCCESS
            }
            Err(reason) => refuse_with_usage(reason, PERSIST_PROPOSAL_USAGE),
        };
    }
    if values.contains_key("--batch-input") {
        if !has_required(&values, &standard_required)
            || values
                .keys()
                .any(|flag| !standard_required.contains(&flag.as_str()) && flag != "--deps")
        {
            return refuse_with_usage("usage", PERSIST_PROPOSAL_USAGE);
        }
        return match persist_standard_proposal(&values) {
            Ok(leaves) => {
                emit_kv("PROPOSAL_PERSISTED", "true");
                emit_kv("LEAF_COUNT", &leaves.to_string());
                ExitCode::SUCCESS
            }
            Err(reason) => refuse_with_usage(reason, PERSIST_PROPOSAL_USAGE),
        };
    }
    if values.len() != prepared_flags.len() {
        return refuse_with_usage("usage", PERSIST_PROPOSAL_USAGE);
    }
    match persist_prepared_proposal(&values) {
        Ok(leaves) => {
            emit_kv("PROPOSAL_PERSISTED", "true");
            emit_kv("LEAF_COUNT", &leaves.to_string());
            ExitCode::SUCCESS
        }
        Err(reason) => refuse_with_usage(reason, PERSIST_PROPOSAL_USAGE),
    }
}

/// The inferred scratch root for one standard-path proposal composition.
struct StandardRoot {
    root: TemporaryRoot,
    declared: PathBuf,
}

impl StandardRoot {
    /// Infer the root from the source snapshot and reject every escaping path.
    fn from_snapshot(path: &str) -> Result<Self, &'static str> {
        let snapshot = absolute(path, "invalid-standard-path")?;
        let declared = snapshot
            .parent()
            .ok_or("invalid-standard-path")?
            .to_path_buf();
        let root = TemporaryRoot::resolve(Some(&declared)).map_err(|_| "invalid-standard-path")?;
        Ok(Self { root, declared })
    }

    fn confine(&self, path: &str, intent: PathIntent) -> Result<ConfinedPath, &'static str> {
        let target = absolute(path, "invalid-standard-path")?;
        anchored(
            &self.root,
            &self.declared,
            &target,
            intent,
            "invalid-standard-path",
        )
    }
}

/// Convert a standard verbal-path batch into all three durable artifacts.
fn persist_standard_proposal(values: &BTreeMap<String, String>) -> Result<usize, &'static str> {
    let root = StandardRoot::from_snapshot(&values["--snapshot"])?;
    let snapshot_path = root.confine(&values["--snapshot"], PathIntent::Read)?;
    let batch_path = root.confine(&values["--batch-input"], PathIntent::Read)?;
    let source_deps = values
        .get("--deps")
        .map(|path| root.confine(path, PathIntent::Read))
        .transpose()?;
    let proposal_path = root.confine(&values["--output"], PathIntent::Write)?;
    let issue_input_path = root.confine(&values["--issue-input-output"], PathIntent::Write)?;
    let deps_output_path = root.confine(&values["--deps-output"], PathIntent::Write)?;

    let mut occupied = BTreeSet::from([
        snapshot_path.path().to_path_buf(),
        batch_path.path().to_path_buf(),
    ]);
    if let Some(path) = &source_deps {
        let _ = occupied.insert(path.path().to_path_buf());
    }
    for output in [&proposal_path, &issue_input_path, &deps_output_path] {
        if !occupied.insert(output.path().to_path_buf()) {
            return Err("invalid-standard-path");
        }
    }

    let snapshot_text = read_utf8(&snapshot_path).map_err(|_| "invalid-snapshot")?;
    let snapshot = parse_snapshot(&snapshot_text, false)?;
    let input_text = read_utf8(&batch_path).map_err(|_| "invalid-prepared-partition")?;
    let deps_text = source_deps.as_ref().map_or_else(
        || Ok(String::new()),
        |path| read_utf8(path).map_err(|_| "invalid-prepared-partition"),
    )?;
    let (record, issue_input) = prepare_proposal_from_batch(&snapshot, &input_text, &deps_text)
        .map_err(larch_core::UmbrellaRefusal::reason)?;
    // The proposal is the durable mutation prerequisite, so publish it last.
    // A failed companion write can leave only overwrite-safe scratch output,
    // never a proposal that appears ready for leaf filing.
    for (path, text) in [
        (&issue_input_path, issue_input),
        (&deps_output_path, deps_text),
        (&proposal_path, render_proposal(&record)),
    ] {
        atomic_write_utf8(path, &text, RECORD_MODE).map_err(|_| "proposal-write-failed")?;
    }
    Ok(record.leaves.len())
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
    parse_snapshot(&text, true)
}

/// Decode the snapshot fields shared by the standard and prepared composers.
fn parse_snapshot(text: &str, require_managed: bool) -> Result<UmbrellaSnapshot, &'static str> {
    let value: Value = serde_json::from_str(text).map_err(|_| "invalid-prepared-partition")?;
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
    snapshot.adopted_umbrella = match row.get("source") {
        None => false,
        Some(Value::String(source)) if source == ADOPTED_UMBRELLA_SOURCE => true,
        Some(_) => return Err("invalid-snapshot"),
    };
    if !is_positive_decimal(&snapshot.number) {
        return Err("invalid-umbrella");
    }
    if !validate_repo_slug(&snapshot.repository)
        || !snapshot.state.eq_ignore_ascii_case("open")
        || snapshot.updated_at.is_empty()
        || snapshot.title.is_empty()
        || (require_managed && !is_managed_partition_title(&snapshot.title))
        || (require_managed && snapshot.adopted_umbrella)
    {
        return Err("invalid-snapshot");
    }
    Ok(snapshot)
}

/// Record that one named leaf was handed to `/issue`.
pub fn mark_in_flight(arguments: &[OsString]) -> ExitCode {
    if let Some(exit_code) = help_requested(arguments, MARK_IN_FLIGHT_USAGE) {
        return exit_code;
    }
    let Some(values) = parse_values(arguments, &["--proposal", "--identity"]) else {
        return refuse_with_usage("usage", MARK_IN_FLIGHT_USAGE);
    };
    if !has_required(&values, &["--proposal", "--identity"]) {
        return refuse_with_usage("usage", MARK_IN_FLIGHT_USAGE);
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
        Err(reason) => refuse_with_usage(reason, MARK_IN_FLIGHT_USAGE),
    }
}

/// Bind one named leaf to the remote issue `/issue` created for it.
pub fn record_resolved(arguments: &[OsString]) -> ExitCode {
    if let Some(exit_code) = help_requested(arguments, RECORD_RESOLVED_USAGE) {
        return exit_code;
    }
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
        return refuse_with_usage("usage", RECORD_RESOLVED_USAGE);
    };
    if !has_required(&values, &["--proposal", "--identity", "--number", "--url"]) {
        return refuse_with_usage("usage", RECORD_RESOLVED_USAGE);
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
        Err(reason) => refuse_with_usage(reason, RECORD_RESOLVED_USAGE),
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
    if let Some(exit_code) = help_requested(arguments, RECONCILE_IN_FLIGHT_USAGE) {
        return exit_code;
    }
    let Some(values) = parse_values(arguments, &["--proposal", "--identity", "--candidates"])
    else {
        return refuse_with_usage("usage", RECONCILE_IN_FLIGHT_USAGE);
    };
    if !has_required(&values, &["--proposal", "--identity", "--candidates"]) {
        return refuse_with_usage("usage", RECONCILE_IN_FLIGHT_USAGE);
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
        Err(reason) => refuse_with_usage(reason, RECONCILE_IN_FLIGHT_USAGE),
    }
}

/// Recover one leaf from the candidate list and persist the binding.
///
/// The caller supplies newest-first rows. Only the shared dedup prefix is
/// admitted, so an oversized or stale handoff cannot widen recovery.
fn reconcile(
    proposal: &str,
    identity: &str,
    candidates: &str,
) -> Result<ResolvedLeaf, &'static str> {
    let text = fs::read_to_string(candidates).map_err(|_| "invalid-proposal-record")?;
    let value: Value = serde_json::from_str(&text).map_err(|_| "invalid-proposal-record")?;
    let rows = value.as_array().ok_or("ambiguous-in-flight-recovery")?;
    if rows.len() > ISSUE_DEDUP_LIMIT {
        eprintln!(
            "WARN: umbrella in-flight reconciliation was capped at the first {ISSUE_DEDUP_LIMIT} candidate rows; remaining rows were omitted"
        );
    }
    let mut parsed = Vec::with_capacity(rows.len().min(ISSUE_DEDUP_LIMIT));
    for row in rows.iter().take(ISSUE_DEDUP_LIMIT) {
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

/// One trusted root a completion artifact is read or published through.
///
/// A declared root is re-resolved once and every artifact below it is confined
/// against the canonical spelling, so a platform alias such as the macOS `/tmp`
/// is not mistaken for an escape and a symlinked component still refuses.
struct SentinelRoot {
    root: TemporaryRoot,
    declared: PathBuf,
}

impl SentinelRoot {
    fn resolve(path: &str, reason: &'static str) -> Result<Self, &'static str> {
        let declared = absolute(path, reason)?;
        Ok(Self {
            root: TemporaryRoot::resolve(Some(&declared)).map_err(|_| reason)?,
            declared,
        })
    }

    fn confine(
        &self,
        path: &str,
        intent: PathIntent,
        reason: &'static str,
    ) -> Result<ConfinedPath, &'static str> {
        let target = absolute(path, reason)?;
        anchored(&self.root, &self.declared, &target, intent, reason)
    }

    fn read(&self, path: &str, reason: &'static str) -> Result<String, &'static str> {
        read_utf8(&self.confine(path, PathIntent::Read, reason)?).map_err(|_| reason)
    }
}

/// The four paths one completion sentinel is written or checked through.
struct CompletionPaths<'values> {
    sentinel_file: &'values str,
    sentinel_root: &'values str,
    prepared_input: &'values str,
    prepared_deps: &'values str,
}

impl<'values> CompletionPaths<'values> {
    /// The four flags that name a completion group, in scanner order.
    const FLAGS: [&'static str; 4] = [
        "--sentinel-file",
        "--sentinel-root",
        "--prepared-input",
        "--prepared-deps",
    ];

    /// Read the group, which is all four non-empty paths or none at all.
    ///
    /// `Ok(None)` reports that the caller asked for no sentinel at all, which
    /// `verify` alone is allowed to do.
    ///
    /// # Errors
    /// Returns the usage refusal for a partial or empty-valued group.
    fn read(values: &'values BTreeMap<String, String>) -> Result<Option<Self>, &'static str> {
        let present = Self::FLAGS
            .iter()
            .filter(|flag| values.contains_key(**flag))
            .count();
        if present == 0 {
            return Ok(None);
        }
        if present != Self::FLAGS.len() || Self::FLAGS.iter().any(|flag| values[*flag].is_empty()) {
            return Err("usage");
        }
        Ok(Some(Self {
            sentinel_file: &values[Self::FLAGS[0]],
            sentinel_root: &values[Self::FLAGS[1]],
            prepared_input: &values[Self::FLAGS[2]],
            prepared_deps: &values[Self::FLAGS[3]],
        }))
    }
}

/// Convert the source issue into its final `[UMBRELLA]` title and body.
pub fn mutate(arguments: &[OsString]) -> ExitCode {
    if let Some(exit_code) = help_requested(arguments, MUTATE_USAGE) {
        return exit_code;
    }
    let Some(values) = parse_values(
        arguments,
        &[
            "--repo",
            "--issue",
            "--title",
            "--body-file",
            "--managed-partition",
            "--adopted-umbrella",
        ],
    ) else {
        return refuse_with_usage("usage", MUTATE_USAGE);
    };
    if !has_required(&values, &["--repo", "--issue", "--title", "--body-file"]) {
        return refuse_with_usage("usage", MUTATE_USAGE);
    }
    let Some(managed) = managed_partition(&values) else {
        return refuse_with_usage("usage", MUTATE_USAGE);
    };
    let Some(adopted) = adopted_umbrella(&values) else {
        return refuse_with_usage("usage", MUTATE_USAGE);
    };
    let Some(mode) = UmbrellaMutationMode::from_flags(managed, adopted) else {
        return refuse_with_usage("usage", MUTATE_USAGE);
    };
    match mutate_with(
        &LiveUmbrellaMutation,
        &values["--repo"],
        &values["--issue"],
        &values["--title"],
        &values["--body-file"],
        mode,
    ) {
        Ok(()) => {
            emit_kv("UMBRELLA_MUTATED", "true");
            ExitCode::SUCCESS
        }
        Err(reason) => refuse_with_usage(reason, MUTATE_USAGE),
    }
}

/// The source contract the final umbrella mutation must preserve.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum UmbrellaMutationMode {
    Standard,
    ManagedPartition,
    AdoptedUmbrella,
}

impl UmbrellaMutationMode {
    /// Reject the mutually exclusive managed-partition and adoption paths.
    const fn from_flags(managed_partition: bool, adopted_umbrella: bool) -> Option<Self> {
        match (managed_partition, adopted_umbrella) {
            (false, false) => Some(Self::Standard),
            (true, false) => Some(Self::ManagedPartition),
            (false, true) => Some(Self::AdoptedUmbrella),
            (true, true) => None,
        }
    }
}

/// The one GitHub effect `/umbrella` finalization performs, behind one seam.
///
/// Finalization is a judgement about what may replace a live issue's title and
/// body, and that judgement is only provable if the write is replaceable. The
/// live implementation below makes no decision the seam does not carry.
trait UmbrellaMutation {
    /// Write the final title and body, or name the refusal reason.
    fn finalize(
        &self,
        repository: &str,
        issue: &str,
        title: &str,
        body: &str,
        mode: UmbrellaMutationMode,
    ) -> Result<(), &'static str>;
}

/// Read the body file, prove the contract, then perform the one write.
///
/// The body is read before the contract is checked because the contract is
/// about the body, exactly as the Python owner ordered it: a caller that names
/// an unreadable file learns that first.
fn mutate_with(
    sink: &impl UmbrellaMutation,
    repository: &str,
    issue: &str,
    title: &str,
    body_file: &str,
    mode: UmbrellaMutationMode,
) -> Result<(), &'static str> {
    let body = fs::read_to_string(body_file).map_err(|_| "mutation-failed")?;
    validate_final_umbrella(title, &body).map_err(larch_core::UmbrellaRefusal::reason)?;
    sink.finalize(repository, issue, title, &body, mode)
}

/// The live write: one compare-and-swap through the shared mutation owner.
struct LiveUmbrellaMutation;

impl UmbrellaMutation for LiveUmbrellaMutation {
    fn finalize(
        &self,
        repository: &str,
        issue: &str,
        title: &str,
        body: &str,
        mode: UmbrellaMutationMode,
    ) -> Result<(), &'static str> {
        if !validate_repo_slug(repository) || !is_positive_decimal(issue) {
            return Err("invalid-identity");
        }
        let reference = crate::github_repository_resolution::repository_ref(repository)
            .map_err(|()| "invalid-identity")?;
        let number: u64 = issue.parse().map_err(|_| "invalid-identity")?;
        let outcome = with_github_service(async |service, cancellation| {
            Ok(finalize_umbrella(
                &IssueMutationOwner::new(service),
                cancellation,
                &reference,
                number,
                (title, body, mode),
            )
            .await)
        });
        match outcome {
            Ok(result) => result,
            Err(ServiceFailure::Setup(_) | ServiceFailure::Operation(_)) => Err("read-failed"),
        }
    }
}

/// Apply the final title and body as one field-scoped, read-back-proved write.
///
/// The managed carve-out adds the umbrella-conversion field, which is what
/// permits a protected `[DESIGNING]` or `[IMPLEMENTING]` body to be replaced at
/// all; the mutation owner then enforces the conversion's own shape.
async fn finalize_umbrella(
    owner: &IssueMutationOwner<'_>,
    cancellation: &Cancellation,
    reference: &larch_core::GitHubRepositoryRef,
    issue: u64,
    contract: (&str, &str, UmbrellaMutationMode),
) -> Result<(), &'static str> {
    let (title, body, mode) = contract;
    let before = owner
        .read_snapshot(reference, issue, cancellation)
        .await
        .map_err(larch_core::IssueMutationError::reason)?;
    let mut fields = BTreeSet::from([IssueMutationField::Title, IssueMutationField::Body]);
    match mode {
        UmbrellaMutationMode::Standard => {}
        UmbrellaMutationMode::ManagedPartition => {
            let _ = fields.insert(IssueMutationField::UmbrellaConversion);
        }
        UmbrellaMutationMode::AdoptedUmbrella => {
            let _ = fields.insert(IssueMutationField::UmbrellaAdoption);
        }
    }
    let request = IssueMutationRequest {
        repository: reference.clone(),
        issue,
        expected_updated_at: before.updated_at.clone(),
        expected_state: before.state,
        fields,
        title: Some(title.to_owned()),
        body: Some(body.to_owned()),
        labels: None,
        marker: None,
        lease: None,
    };
    // `/umbrella` is an operator-invoked skill and the Python owner took no
    // authorization of its own here, so the gate is satisfied in operator mode
    // rather than re-deriving a session context this verb never receives.
    owner
        .apply(
            cancellation,
            &authorization_request("", "", "", true),
            &request,
        )
        .await
        .map(|_verified| ())
        .map_err(larch_core::IssueMutationError::reason)
}

/// Prove the recorded graph landed, then publish the completion sentinel.
pub fn verify(arguments: &[OsString]) -> ExitCode {
    if let Some(exit_code) = help_requested(arguments, VERIFY_USAGE) {
        return exit_code;
    }
    let mut permitted = vec!["--proposal", "--leaves"];
    permitted.extend_from_slice(&CompletionPaths::FLAGS);
    let Some(values) = parse_values(arguments, &permitted) else {
        return refuse_with_usage("usage", VERIFY_USAGE);
    };
    if !has_required(&values, &["--proposal", "--leaves"]) {
        return refuse_with_usage("usage", VERIFY_USAGE);
    }
    let completion = match CompletionPaths::read(&values) {
        Ok(completion) => completion,
        Err(reason) => return refuse_with_usage(reason, VERIFY_USAGE),
    };
    match verify_graph(
        &values["--proposal"],
        &values["--leaves"],
        completion.as_ref(),
    ) {
        Ok(()) => {
            emit_kv("GRAPH_VERIFIED", "true");
            ExitCode::SUCCESS
        }
        Err(reason) => refuse_with_usage(reason, VERIFY_USAGE),
    }
}

/// Verify the record against the live leaf rows and write the sentinel.
fn verify_graph(
    proposal: &str,
    leaves: &str,
    completion: Option<&CompletionPaths<'_>>,
) -> Result<(), &'static str> {
    let record = load_record(proposal)?;
    verify_graph_state(&record, &read_remote_leaves(leaves)?)
        .map_err(larch_core::UmbrellaRefusal::reason)?;
    let Some(paths) = completion else {
        return Ok(());
    };
    // Every filesystem failure below is reported as one reason. The sentinel is
    // the only artifact this verb publishes, so a caller that cannot read the
    // partition and a caller that cannot write the proof are in the same place.
    let reason = "sentinel-write-failed";
    let root = SentinelRoot::resolve(paths.sentinel_root, reason)?;
    let input_text = root.read(paths.prepared_input, reason)?;
    let deps_text = root.read(paths.prepared_deps, reason)?;
    let sentinel = completion_sentinel_for_record(&record, &input_text, &deps_text)
        .map_err(larch_core::UmbrellaRefusal::reason)?;
    atomic_write_utf8(
        &root.confine(paths.sentinel_file, PathIntent::Write, reason)?,
        &sentinel.render(),
        RECORD_MODE,
    )
    .map_err(|_| reason)
}

/// Read the live leaf rows the recorded graph is verified against.
///
/// A field the row cannot supply as text is dropped rather than interpreted:
/// the comparison that follows is byte equality against a recorded leaf, so an
/// unusable field can only fail to match.
fn read_remote_leaves(path: &str) -> Result<Vec<RemoteLeaf>, &'static str> {
    let text = fs::read_to_string(path).map_err(|_| "invalid-proposal-record")?;
    let value: Value = serde_json::from_str(&text).map_err(|_| "invalid-proposal-record")?;
    let rows = value.as_array().ok_or("incomplete-graph-state")?;
    let mut leaves = Vec::with_capacity(rows.len());
    for row in rows {
        let row = row.as_object().ok_or("incomplete-graph-state")?;
        let text = |key: &str| match row.get(key) {
            Some(Value::String(value)) => value.clone(),
            _ => String::new(),
        };
        leaves.push(RemoteLeaf {
            number: row_number(row.get("number")),
            title: text("title"),
            body: text("body"),
        });
    }
    Ok(leaves)
}

/// Render one row's issue number the way the Python comparison rendered it.
///
/// Python coerced the field with `str(row.get("number") or "")`, so every falsy
/// spelling — absent, null, `false`, zero, an empty string — became the empty
/// string that matches no recorded leaf.
fn row_number(value: Option<&Value>) -> String {
    match value {
        Some(Value::String(text)) => text.clone(),
        Some(Value::Number(number)) if number.as_f64() != Some(0.0) => number.to_string(),
        Some(Value::Bool(true)) => String::from("True"),
        _ => String::new(),
    }
}

/// Prove one child's completion sentinel against the parent's own partition.
pub fn verify_completion(arguments: &[OsString]) -> ExitCode {
    if let Some(exit_code) = help_requested(arguments, VERIFY_COMPLETION_USAGE) {
        return exit_code;
    }
    let mut permitted = vec!["--repo", "--issue"];
    permitted.extend_from_slice(&CompletionPaths::FLAGS);
    let Some(values) = parse_values(arguments, &permitted) else {
        return refuse_with_usage("usage", VERIFY_COMPLETION_USAGE);
    };
    let Ok(Some(paths)) = CompletionPaths::read(&values) else {
        return refuse_with_usage("usage", VERIFY_COMPLETION_USAGE);
    };
    if !has_required(&values, &["--repo", "--issue"]) {
        return refuse_with_usage("usage", VERIFY_COMPLETION_USAGE);
    }
    match check_completion(&values["--repo"], &values["--issue"], &paths) {
        Ok(()) => {
            emit_kv("UMBRELLA_COMPLETION_VERIFIED", "true");
            emit_kv("UMBRELLA_NUMBER", &values["--issue"]);
            ExitCode::SUCCESS
        }
        Err(reason) => refuse_with_usage(reason, VERIFY_COMPLETION_USAGE),
    }
}

/// Rebuild the sentinel the live partition authorizes and compare every row.
fn check_completion(
    repository: &str,
    issue: &str,
    paths: &CompletionPaths<'_>,
) -> Result<(), &'static str> {
    if !is_positive_decimal(issue) {
        return Err("invalid-umbrella");
    }
    if !validate_repo_slug(repository) {
        return Err("invalid-repository");
    }
    let reason = "invalid-completion-sentinel";
    let root = SentinelRoot::resolve(paths.sentinel_root, reason)?;
    let stored = CompletionSentinel::parse(&root.read(paths.sentinel_file, reason)?)
        .map_err(larch_core::UmbrellaRefusal::reason)?;
    let expected = expected_completion_sentinel(
        repository,
        issue,
        &root.read(paths.prepared_input, reason)?,
        &root.read(paths.prepared_deps, reason)?,
    )
    .map_err(larch_core::UmbrellaRefusal::reason)?;
    if stored == expected {
        Ok(())
    } else {
        Err(larch_core::STALE_COMPLETION_SENTINEL.reason())
    }
}

#[cfg(test)]
mod tests {
    use super::{
        CompletionPaths, LiveSnapshotSource, OPEN_BLOCKERS, SnapshotRead, SnapshotSource,
        UmbrellaMutation, UmbrellaMutationMode, absolute, candidate_issue, check_completion,
        load_record, mark_in_flight, mutate, mutate_with, parse_values, persist_prepared_proposal,
        persist_proposal, persist_standard_proposal, prepare, prepare_with, reconcile,
        reconcile_in_flight_command, record_resolved, resolve_into, row_number, verify,
        verify_completion, verify_graph,
    };
    use crate::github_service::with_test_github_service;
    use larch_adapters::github::OctocrabGitHubService;
    use larch_core::{
        ExpectedLeaf, LeafState, MANAGED_PARTITION_PREFIXES, ProposalRecord, RemoteLeaf,
        ResolvedLeaf, UmbrellaSnapshot, leaf_identity, mark_leaf_in_flight,
        prepare_proposal_from_batch, render_proposal, render_snapshot, umbrella_leaf_opening_text,
        verify_graph_state,
    };
    use larch_test_support::{IssueServiceExchange, IssueServiceStub};
    use serde_json::{Value, json};
    use std::{
        cell::RefCell,
        collections::BTreeMap,
        ffi::OsString,
        fs,
        path::{Path, PathBuf},
        process::ExitCode,
        sync::Arc,
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

    struct FixedSource(Result<UmbrellaSnapshot, &'static str>, bool);

    impl SnapshotSource for FixedSource {
        fn read(&self, _repository: &str, _issue: &str) -> Result<SnapshotRead, &'static str> {
            Ok(SnapshotRead {
                snapshot: self.0.clone()?,
                adoption_safe: self.1,
            })
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
            adopted_umbrella: false,
        }
    }

    /// Build one complete typed issue response for the loopback GitHub service.
    fn issue_response(number: u64, id: u64, title: &str, body: &str) -> Value {
        let mut value: Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("valid issue fixture");
        value["id"] = json!(id);
        value["number"] = json!(number);
        value["title"] = json!(title);
        value["body"] = json!(body);
        value["state"] = json!("open");
        value["url"] = json!(format!(
            "https://example.test/repos/owner/repo/issues/{number}"
        ));
        value["repository_url"] = json!("https://example.test/repos/owner/repo");
        value["html_url"] = json!(format!("https://github.com/owner/repo/issues/{number}"));
        value["labels"] = json!([]);
        value["updated_at"] = json!("2026-08-03T00:00:00Z");
        value
    }

    /// Start one loopback-only typed GitHub service for a command unit test.
    fn service(
        exchanges: impl IntoIterator<Item = IssueServiceExchange>,
    ) -> (
        Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync>,
        IssueServiceStub,
    ) {
        let server = IssueServiceStub::start(exchanges).expect("start issue service stub");
        let base_url = server.base_url().to_owned();
        let factory: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base_url));
        (factory, server)
    }

    /// Exercise preparation through the injected live GitHub service.
    fn prepare_live(
        github: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync>,
        output: &str,
    ) -> ExitCode {
        with_test_github_service(github, || {
            prepare(&arguments(&[
                "--repo",
                "owner/repo",
                "--issue",
                "12",
                "--output",
                output,
            ]))
        })
    }

    /// Allocate one durable output path for a preparation test.
    fn snapshot_output() -> (TempDir, String) {
        let directory = TempDir::new().expect("temporary directory");
        let output = text_path(&root(&directory).join("snapshot.json"));
        (directory, output)
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
    fn preparation_publishes_only_an_eligible_source() {
        let directory = TempDir::new().expect("temporary directory");
        let output = text_path(&root(&directory).join("snapshot.json"));
        let source = FixedSource(Ok(snapshot("Regular issue", "Body.", "OPEN")), false);
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
                    &FixedSource(Ok(source), false),
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
                &FixedSource(Err("read-failed"), false),
                "owner/repo",
                "12",
                &output,
                false
            ),
            Err("read-failed")
        );
        assert_eq!(
            prepare_with(
                &FixedSource(
                    Ok(snapshot(
                        &managed_title("Work"),
                        "<!-- larch:plan -->",
                        "OPEN"
                    )),
                    false
                ),
                "owner/repo",
                "12",
                "/larch-umbrella-missing-root/snapshot.json",
                true
            ),
            Err("snapshot-failed")
        );

        let adopted = FixedSource(
            Ok(snapshot(
                "[UMBRELLA] External split",
                "External context.",
                "OPEN",
            )),
            true,
        );
        assert_eq!(
            prepare_with(&adopted, "owner/repo", "12", &output, false),
            Ok("2026-08-03T00:00:00Z".to_owned())
        );
        assert_eq!(
            fs::read_to_string(&output).expect("adoption snapshot published"),
            "{\"body\": \"External context.\", \"number\": \"12\", \"repository\": \"owner/repo\", \"source\": \"adopted-umbrella\", \"state\": \"OPEN\", \"title\": \"[UMBRELLA] External split\", \"updated_at\": \"2026-08-03T00:00:00Z\"}\n"
        );
    }

    #[test]
    fn live_preparation_adopts_only_a_recordless_umbrella_without_children_or_open_blockers() {
        let (_directory, output) = snapshot_output();
        let source = issue_response(12, 120, "[UMBRELLA] External split", "External context.");

        let (github, server) = service([
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/12",
                200,
                source.to_string(),
            )
            .expect("source response"),
            IssueServiceExchange::json("GET", "/repos/owner/repo/issues/12/sub_issues", 200, "[]")
                .expect("empty children response"),
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/12/dependencies/blocked_by",
                200,
                "[]",
            )
            .expect("empty blockers response"),
        ]);
        assert_eq!(prepare_live(github, &output), ExitCode::SUCCESS);
        assert!(
            fs::read_to_string(&output)
                .expect("adoption snapshot")
                .contains("\"source\": \"adopted-umbrella\"")
        );
        server.join().expect("empty graph was fully read");

        let (github, server) = service([
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/12",
                200,
                source.to_string(),
            )
            .expect("source response"),
            IssueServiceExchange::json("GET", "/repos/owner/repo/issues/12/sub_issues", 200, "[]")
                .expect("empty children response"),
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/12/dependencies/blocked_by",
                200,
                "[{\"number\":34,\"id\":340,\"state\":\"closed\"}]",
            )
            .expect("closed blocker response"),
        ]);
        assert_eq!(prepare_live(github, &output), ExitCode::SUCCESS);
        server
            .join()
            .expect("closed blocker is satisfied without a blocker read");

        let (github, server) = service([
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/12",
                200,
                source.to_string(),
            )
            .expect("source response"),
            IssueServiceExchange::json("GET", "/repos/owner/repo/issues/12/sub_issues", 200, "[]")
                .expect("empty children response"),
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/12/dependencies/blocked_by",
                200,
                "[{\"number\":34,\"id\":340,\"state\":\"open\"}]",
            )
            .expect("open blocker response"),
        ]);
        match with_test_github_service(github, || LiveSnapshotSource.read("owner/repo", "12")) {
            Err(reason) => assert_eq!(reason, OPEN_BLOCKERS),
            Ok(_) => panic!("an open blocker must refuse adoption"),
        }
        server
            .join()
            .expect("open blocker refuses before any blocker read");

        let direct_child = serde_json::json!([{ "number": 34, "id": 340, "state": "open" }]);
        let (github, server) = service([
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/12",
                200,
                source.to_string(),
            )
            .expect("source response"),
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/12/sub_issues",
                200,
                direct_child.to_string(),
            )
            .expect("direct child response"),
        ]);
        assert_eq!(prepare_live(github, &output), ExitCode::from(2));
        server.join().expect("direct child was fully read");
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

    #[test]
    fn recovery_ignores_candidates_beyond_the_shared_dedup_limit() {
        let directory = TempDir::new().expect("temporary directory");
        let identity = record().leaves[0].identity.clone();
        let marked = mark_leaf_in_flight(&record(), &identity).expect("marks in flight");
        let leaf = marked.leaves[0].clone();
        let path = write(
            &root(&directory),
            "proposal.json",
            &render_proposal(&marked),
        );
        let mut rows: Vec<Value> = (1..=larch_core::ISSUE_DEDUP_LIMIT)
            .map(|number| {
                json!({
                    "number": number,
                    "url": format!("https://example.test/issues/{number}"),
                    "id": number,
                    "title": format!("unrelated {number}"),
                    "body": "different",
                })
            })
            .collect();
        let omitted_number = larch_core::ISSUE_DEDUP_LIMIT + 1;
        rows.push(json!({
            "number": omitted_number,
            "url": format!("https://example.test/issues/{omitted_number}"),
            "id": omitted_number,
            "title": leaf.title,
            "body": leaf.body,
        }));
        let candidates = write(
            &root(&directory),
            "over-limit.json",
            &serde_json::to_string(&rows).expect("candidate rows render"),
        );

        assert_eq!(
            reconcile(&path, &identity, &candidates),
            Err("ambiguous-in-flight-recovery")
        );
        assert_eq!(
            load_record(&path).expect("record reloads").leaves[0].state,
            LeafState::InFlight
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

    #[test]
    fn a_standard_batch_composes_exact_record_and_issue_input_bytes() {
        let directory = TempDir::new().expect("temporary directory");
        let sandbox = root(&directory);
        let snapshot = write(
            &sandbox,
            "snapshot.json",
            &render_snapshot(&snapshot("Regular", "Shared.", "OPEN")),
        );
        let batch = write(
            &sandbox,
            "batch.md",
            "### One\n\nFirst.\n\n### Two\n\nSecond.",
        );
        let output = text_path(&sandbox.join("proposal.json"));
        let issue_input = text_path(&sandbox.join("issue-input.txt"));
        let deps_output = text_path(&sandbox.join("deps.tsv"));
        let mut values = BTreeMap::from([
            ("--snapshot".to_owned(), snapshot),
            ("--batch-input".to_owned(), batch),
            ("--output".to_owned(), output.clone()),
            ("--issue-input-output".to_owned(), issue_input.clone()),
            ("--deps-output".to_owned(), deps_output.clone()),
        ]);

        assert_eq!(persist_standard_proposal(&values), Ok(2));
        let record = load_record(&output).expect("record reloads");
        assert_eq!(
            record
                .leaves
                .iter()
                .map(|leaf| leaf.title.as_str())
                .collect::<Vec<_>>(),
            ["[LEAF OF 12] One", "[LEAF OF 12] Two"]
        );
        assert_eq!(
            record.leaves[1].body,
            format!("{}\n\nSecond.", umbrella_leaf_opening_text("12"))
        );
        assert_eq!(
            fs::read_to_string(&issue_input).expect("issue input"),
            format!(
                "### One\n\n{}\n\nFirst.\n### Two\n\n{}\n\nSecond.\n",
                umbrella_leaf_opening_text("12"),
                umbrella_leaf_opening_text("12")
            )
        );
        assert_eq!(fs::read_to_string(&deps_output).expect("deps output"), "");

        let mut resolved = record;
        let rows: Vec<RemoteLeaf> = resolved
            .leaves
            .iter_mut()
            .enumerate()
            .map(|(index, leaf)| {
                leaf.state = LeafState::Resolved;
                leaf.number = (20 + index).to_string();
                leaf.url = format!("https://example.test/issues/{}", 20 + index);
                RemoteLeaf {
                    number: leaf.number.clone(),
                    title: leaf.title.clone(),
                    body: leaf.body.clone(),
                }
            })
            .collect();
        assert_eq!(verify_graph_state(&resolved, &rows), Ok(()));

        let _ = values.insert("--deps-output".to_owned(), issue_input);
        assert_eq!(
            persist_standard_proposal(&values),
            Err("invalid-standard-path")
        );

        let outside = TempDir::new().expect("outside directory");
        let _ = values.insert("--deps-output".to_owned(), deps_output);
        let _ = values.insert(
            "--batch-input".to_owned(),
            write(
                &root(&outside),
                "outside.md",
                "### One\n\nFirst.\n\n### Two\n\nSecond.\n",
            ),
        );
        assert_eq!(
            persist_standard_proposal(&values),
            Err("invalid-standard-path")
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
    /// The exact parent-approved batch every completion case is built from.
    const PREPARED_BATCH: &str = "### One\n\nFirst.\n\n### Two\n\nSecond.\n";

    /// The six paths one completed `/umbrella` run leaves behind.
    struct Completion {
        proposal: String,
        leaves: String,
        sentinel: String,
        root: String,
        input: String,
        deps: String,
    }

    impl Completion {
        /// Confine the three completion artifacts to the fixture's own root.
        fn paths(&self) -> CompletionPaths<'_> {
            CompletionPaths {
                sentinel_file: &self.sentinel,
                sentinel_root: &self.root,
                prepared_input: &self.input,
                prepared_deps: &self.deps,
            }
        }

        /// The argument vector `verify-completion` reads this run through.
        fn completion_arguments(&self) -> Vec<OsString> {
            arguments(&[
                "--sentinel-file",
                &self.sentinel,
                "--sentinel-root",
                &self.root,
                "--prepared-input",
                &self.input,
                "--prepared-deps",
                &self.deps,
                "--repo",
                "owner/repo",
                "--issue",
                "12",
            ])
        }
    }

    /// Publish one prepared partition whose two leaves are already resolved.
    fn completion_fixture(parent: &Path) -> Completion {
        let source = UmbrellaSnapshot {
            repository: "owner/repo".to_owned(),
            number: "12".to_owned(),
            title: managed_title("Split"),
            body: "Shared.".to_owned(),
            state: "OPEN".to_owned(),
            updated_at: "2026-08-03T00:00:00Z".to_owned(),
            adopted_umbrella: false,
        };
        let (mut record, _issue_input) =
            prepare_proposal_from_batch(&source, PREPARED_BATCH, "1\t2\n")
                .expect("prepares the partition");
        let mut rows = Vec::with_capacity(record.leaves.len());
        for (index, leaf) in record.leaves.iter_mut().enumerate() {
            let number = 21 + index;
            leaf.state = LeafState::Resolved;
            leaf.number = number.to_string();
            leaf.url = format!("https://example.test/issues/{number}");
            rows.push(serde_json::json!({
                "number": number,
                "title": leaf.title,
                "body": leaf.body,
            }));
        }
        Completion {
            proposal: write(parent, "proposal.json", &render_proposal(&record)),
            leaves: write(
                parent,
                "leaves.json",
                &serde_json::Value::Array(rows).to_string(),
            ),
            sentinel: text_path(&parent.join("complete.sentinel")),
            root: text_path(parent),
            input: write(parent, "input.txt", PREPARED_BATCH),
            deps: write(parent, "deps.tsv", "1\t2\n"),
        }
    }

    /// One finalization sink that records the contract it was handed.
    struct RecordingMutation(RefCell<Vec<String>>);

    impl UmbrellaMutation for RecordingMutation {
        fn finalize(
            &self,
            repository: &str,
            issue: &str,
            title: &str,
            body: &str,
            mode: UmbrellaMutationMode,
        ) -> Result<(), &'static str> {
            self.0
                .borrow_mut()
                .push(format!("{repository} {issue} {title} {body} {mode:?}"));
            Ok(())
        }
    }

    /// One finalization sink standing in for a refused live mutation.
    struct RefusedMutation;

    impl UmbrellaMutation for RefusedMutation {
        fn finalize(
            &self,
            _repository: &str,
            _issue: &str,
            _title: &str,
            _body: &str,
            _mode: UmbrellaMutationMode,
        ) -> Result<(), &'static str> {
            Err("stale-identity")
        }
    }

    #[test]
    fn finalization_writes_only_a_body_that_keeps_the_umbrella_contract() {
        let directory = TempDir::new().expect("temporary directory");
        let sandbox = root(&directory);
        let body = write(
            &sandbox,
            "body.md",
            "Context\n<!-- larch:umbrella-proposal -->\n",
        );
        let bare = write(&sandbox, "bare.md", "Context only\n");
        let sink = RecordingMutation(RefCell::new(Vec::new()));

        assert_eq!(
            mutate_with(
                &sink,
                "owner/repo",
                "12",
                "[UMBRELLA] Split",
                &body,
                UmbrellaMutationMode::ManagedPartition,
            ),
            Ok(())
        );
        assert_eq!(
            sink.0.borrow().as_slice(),
            [
                "owner/repo 12 [UMBRELLA] Split Context\n<!-- larch:umbrella-proposal -->\n ManagedPartition"
            ]
        );
        assert_eq!(
            mutate_with(
                &sink,
                "owner/repo",
                "12",
                &managed_title("Split"),
                &body,
                UmbrellaMutationMode::Standard
            ),
            Err("invalid-final-umbrella")
        );
        assert_eq!(
            mutate_with(
                &sink,
                "owner/repo",
                "12",
                "[UMBRELLA] Split",
                &bare,
                UmbrellaMutationMode::Standard,
            ),
            Err("invalid-final-umbrella")
        );
        assert_eq!(
            mutate_with(
                &sink,
                "owner/repo",
                "12",
                "[UMBRELLA] Split",
                "/larch-umbrella-absent-body.md",
                UmbrellaMutationMode::Standard
            ),
            Err("mutation-failed")
        );
        assert_eq!(
            mutate_with(
                &RefusedMutation,
                "owner/repo",
                "12",
                "[UMBRELLA] Split",
                &body,
                UmbrellaMutationMode::Standard
            ),
            Err("stale-identity")
        );
        // Only the one accepted contract reached the sink.
        assert_eq!(sink.0.borrow().len(), 1);
    }

    #[test]
    fn a_verified_graph_publishes_the_sentinel_the_parent_rechecks() {
        let directory = TempDir::new().expect("temporary directory");
        let parent = root(&directory);
        let fixture = completion_fixture(&parent);
        let paths = fixture.paths();

        assert_eq!(
            verify_graph(&fixture.proposal, &fixture.leaves, Some(&paths)),
            Ok(())
        );
        let published = fs::read_to_string(&fixture.sentinel).expect("sentinel published");
        assert!(published.starts_with("UMBRELLA_SENTINEL_VERSION=2\nREPOSITORY=owner/repo\n"));
        assert!(published.ends_with("GRAPH_VERIFIED=true\n"));
        assert_eq!(check_completion("owner/repo", "12", &paths), Ok(()));

        // The parent rebuilds the proof from its own artifacts, so editing one
        // after the fact invalidates the sentinel without touching it.
        fs::write(&fixture.deps, "").expect("rewrite the edge list");
        assert_eq!(
            check_completion("owner/repo", "12", &paths),
            Err("stale-completion-sentinel")
        );
        assert_eq!(
            verify_graph(&fixture.proposal, &fixture.leaves, Some(&paths)),
            Err("stale-prepared-partition")
        );
        fs::write(&fixture.deps, "1\t2\n").expect("restore the edge list");
        assert_eq!(check_completion("owner/repo", "12", &paths), Ok(()));
    }

    #[test]
    fn verification_refuses_every_incomplete_or_unreadable_graph() {
        let directory = TempDir::new().expect("temporary directory");
        let parent = root(&directory);
        let fixture = completion_fixture(&parent);
        let paths = fixture.paths();

        assert_eq!(
            verify_graph(&fixture.proposal, "/larch-umbrella-absent.json", None),
            Err("invalid-proposal-record")
        );
        let unusable = write(&parent, "object.json", "{}\n");
        assert_eq!(
            verify_graph(&fixture.proposal, &unusable, None),
            Err("incomplete-graph-state")
        );
        let scalar_rows = write(&parent, "scalars.json", "[3]\n");
        assert_eq!(
            verify_graph(&fixture.proposal, &scalar_rows, None),
            Err("incomplete-graph-state")
        );
        let renumbered = write(
            &parent,
            "renumbered.json",
            "[{\"number\": 0, \"title\": \"t\", \"body\": \"b\"}]\n",
        );
        assert_eq!(
            verify_graph(&fixture.proposal, &renumbered, None),
            Err("incomplete-graph-state")
        );
        // A record whose leaves never resolved cannot authorize a sentinel.
        let pending = write(&parent, "pending.json", &render_proposal(&record()));
        assert_eq!(
            verify_graph(&pending, &fixture.leaves, None),
            Err("incomplete-graph-state")
        );
        assert!(!Path::new(&fixture.sentinel).exists());

        let missing_root = CompletionPaths {
            sentinel_root: "/larch-umbrella-missing-root",
            ..paths
        };
        assert_eq!(
            verify_graph(&fixture.proposal, &fixture.leaves, Some(&missing_root)),
            Err("sentinel-write-failed")
        );
        let escaping = CompletionPaths {
            prepared_input: "/larch-umbrella-outside/input.txt",
            ..paths
        };
        assert_eq!(
            verify_graph(&fixture.proposal, &fixture.leaves, Some(&escaping)),
            Err("sentinel-write-failed")
        );
    }

    #[test]
    fn a_completion_proof_is_refused_unless_every_row_is_rebuilt() {
        let directory = TempDir::new().expect("temporary directory");
        let parent = root(&directory);
        let fixture = completion_fixture(&parent);
        let paths = fixture.paths();
        assert_eq!(
            verify_graph(&fixture.proposal, &fixture.leaves, Some(&paths)),
            Ok(())
        );

        assert_eq!(
            check_completion("owner/repo", "0", &paths),
            Err("invalid-umbrella")
        );
        assert_eq!(
            check_completion("owner", "12", &paths),
            Err("invalid-repository")
        );
        assert_eq!(
            check_completion("owner/repo", "13", &paths),
            Err("stale-completion-sentinel")
        );
        let published = fs::read_to_string(&fixture.sentinel).expect("sentinel published");
        fs::write(&fixture.sentinel, published.replace('\n', "\r\n")).expect("rewrite the proof");
        assert_eq!(
            check_completion("owner/repo", "12", &paths),
            Err("invalid-completion-sentinel")
        );
        fs::write(&fixture.sentinel, "GRAPH_VERIFIED=true\n").expect("truncate the proof");
        assert_eq!(
            check_completion("owner/repo", "12", &paths),
            Err("invalid-completion-sentinel")
        );
        fs::remove_file(&fixture.sentinel).expect("drop the proof");
        assert_eq!(
            check_completion("owner/repo", "12", &paths),
            Err("invalid-completion-sentinel")
        );
        fs::write(&fixture.input, "### Only\n\nOne item.\n").expect("shrink the batch");
        assert_eq!(
            check_completion("owner/repo", "12", &paths),
            Err("invalid-completion-sentinel")
        );
    }

    #[test]
    fn every_completion_entrypoint_scans_its_own_command_line() {
        let directory = TempDir::new().expect("temporary directory");
        let parent = root(&directory);
        let fixture = completion_fixture(&parent);
        let refused = ExitCode::from(2);

        assert_eq!(mutate(&arguments(&["--repo", "owner/repo"])), refused);
        assert_eq!(mutate(&arguments(&["--repo"])), refused);
        assert_eq!(
            mutate(&arguments(&[
                "--repo",
                "owner/repo",
                "--issue",
                "12",
                "--title",
                "[UMBRELLA] Split",
                "--body-file",
                &fixture.input,
                "--managed-partition",
                "maybe",
            ])),
            refused
        );
        assert_eq!(
            verify(&arguments(&["--proposal", &fixture.proposal])),
            refused
        );
        assert_eq!(verify(&arguments(&["--leaves"])), refused);
        // A partial completion group is a usage refusal, not a missing proof.
        assert_eq!(
            verify(&arguments(&[
                "--proposal",
                &fixture.proposal,
                "--leaves",
                &fixture.leaves,
                "--sentinel-file",
                &fixture.sentinel,
            ])),
            refused
        );
        assert_eq!(
            verify(&arguments(&[
                "--proposal",
                &fixture.proposal,
                "--leaves",
                &fixture.leaves
            ])),
            ExitCode::SUCCESS
        );
        assert!(!Path::new(&fixture.sentinel).exists());
        assert_eq!(
            verify_completion(&arguments(&["--repo", "owner/repo"])),
            refused
        );
        assert_eq!(
            verify_completion(&arguments(&[
                "--sentinel-file",
                &fixture.sentinel,
                "--sentinel-root",
                &fixture.root,
                "--prepared-input",
                &fixture.input,
                "--prepared-deps",
                &fixture.deps,
            ])),
            refused
        );
        assert_eq!(verify_completion(&fixture.completion_arguments()), refused);

        assert_eq!(
            verify(&arguments(&[
                "--proposal",
                &fixture.proposal,
                "--leaves",
                &fixture.leaves,
                "--sentinel-file",
                &fixture.sentinel,
                "--sentinel-root",
                &fixture.root,
                "--prepared-input",
                &fixture.input,
                "--prepared-deps",
                &fixture.deps,
            ])),
            ExitCode::SUCCESS
        );
        assert_eq!(
            verify_completion(&fixture.completion_arguments()),
            ExitCode::SUCCESS
        );
    }

    #[test]
    fn mutate_rejects_invalid_or_conflicting_mode_flags() {
        let refused = ExitCode::from(2);
        assert_eq!(
            mutate(&arguments(&[
                "--repo",
                "owner/repo",
                "--issue",
                "12",
                "--title",
                "[UMBRELLA] Split",
                "--body-file",
                "/larch-umbrella-body.md",
                "--adopted-umbrella",
                "maybe",
            ])),
            refused
        );
        assert_eq!(
            mutate(&arguments(&[
                "--repo",
                "owner/repo",
                "--issue",
                "12",
                "--title",
                "[UMBRELLA] Split",
                "--body-file",
                "/larch-umbrella-body.md",
                "--managed-partition",
                "true",
                "--adopted-umbrella",
                "true",
            ])),
            refused
        );
    }

    #[test]
    fn a_row_number_matches_only_what_python_rendered() {
        assert_eq!(row_number(Some(&serde_json::json!(34))), "34");
        assert_eq!(row_number(Some(&serde_json::json!("34"))), "34");
        assert_eq!(row_number(Some(&serde_json::json!(true))), "True");
        for falsy in [
            serde_json::json!(0),
            serde_json::json!(false),
            serde_json::json!(null),
            serde_json::json!(""),
            serde_json::json!([34]),
        ] {
            assert_eq!(row_number(Some(&falsy)), "", "value {falsy}");
        }
        assert_eq!(row_number(None), "");
    }
}
