//! The six `/deps` verbs: the dependency audit's reads, plan, and one apply.
//!
//! `/deps` fetches every open issue once, scans explicit references out of
//! untrusted prose, records the operator's proposals, composes one plan, and
//! then applies exactly that plan. The verbs are deliberately separate files on
//! disk rather than one long-running process: the operator's approval gate sits
//! between the plan and the apply, and the plan is the only thing that crosses
//! it.
//!
//! Everything that leaves this process goes through [`DepsGateway`], so the
//! ordering, the fail-closed apply, and the partial-failure accounting are
//! exercised in process against a double. Composition itself belongs to
//! [`larch_core`].
//!
//! Ports `larch.issue.deps_audit`.

use std::{
    collections::{BTreeMap, BTreeSet},
    ffi::OsString,
    fs,
    io::ErrorKind,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{
    TokioProcessRunner,
    github::{DependencyRef, IssueMutationOwner, OctocrabGitHubService},
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    DepsEdge, DepsFetchedIssue, DepsIssueMap, DepsLiveIssue, DepsPlanInputs, GH_ERROR_CHARS,
    GitHubIssue, GitHubIssueList, GitHubIssueListMode, GitHubIssueState, GitHubOperationError,
    GitHubOperationErrorKind, GitHubRepositoryRef, GitHubService as _, IssueMutationField,
    IssueMutationRequest, IssueMutationSnapshot, MUTATION_ERROR_CHARS, deps_compact_json,
    deps_explicit_refs, deps_failed_fetch, deps_fetch_artifacts, deps_flat_error, deps_issue_map,
    deps_normal_edge, deps_plan, deps_plan_writes_allowed, deps_pretty_json, deps_proposal_edges,
    deps_proposal_mutations, deps_revalidate_edge, deps_sanitize_outbound_body,
    deps_snapshot_numbers, deps_validate_snapshot_membership, deps_warning, emit_kv,
    json_positive_integer, python_str,
};
use serde_json::{Value, json};

use crate::{
    argparse_compat::{ParsedCommandLine, missing, parse_with_flags, read_stdin, usage_error},
    blocker_commands::resolve_repo_for,
    github_repository_resolution::{remote_slug, repository_ref, validate_repo_slug},
    issue_dependency_commands::{EdgeAuthorization, apply_blocked_by, in_process_edge},
    issue_mutation_support::authorization_request,
};

/// Exit code every `argparse`-shaped refusal reports.
const USAGE_EXIT: u8 = 2;

// ---------------------------------------------------------------------------
// Effect seam
// ---------------------------------------------------------------------------

/// One open issue as the audit reads it, before any composition.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DepsOpenIssue {
    /// The issue number.
    pub number: u64,
    /// The issue title.
    pub title: String,
    /// The issue body, untrusted.
    pub body: String,
    /// The label names, in read order.
    pub labels: Vec<String>,
}

/// Why the open-issue snapshot could not be read.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DepsReadFailure {
    /// The stable warning code the snapshot publishes.
    pub code: &'static str,
    /// The already-bounded diagnostic.
    pub detail: String,
}

/// Everything `/deps` does outside this process.
///
/// The audit never reaches GitHub or Git directly, so its snapshot composition,
/// plan, and fail-closed apply are all exercised against a double.
pub trait DepsGateway {
    /// Return the checkout's `origin` slug, or `""` when there is none.
    fn origin_slug(&self) -> String;
    /// Read every open issue in `repo`.
    ///
    /// # Errors
    /// Returns the classified failure the snapshot reports as a warning.
    fn open_issues(&self, repo: &str) -> Result<Vec<DepsOpenIssue>, DepsReadFailure>;
    /// Read one issue's comments as `(id, body)` pairs.
    ///
    /// # Errors
    /// Returns the diagnostic the snapshot records as a comment warning.
    fn comments(&self, repo: &str, issue: u64) -> Result<Vec<(u64, String)>, String>;
    /// Read one direction of one issue's native dependency edges.
    ///
    /// # Errors
    /// Returns the diagnostic the snapshot records as a dependency warning.
    fn dependencies(&self, repo: &str, issue: u64, blocking: bool) -> Result<Vec<u64>, String>;
    /// Read one issue's live title and state, or `None` when the read failed.
    fn live_issue(&self, repo: &str, issue: u64) -> Option<DepsLiveIssue>;
    /// Replace one issue body through the freshness-checked mutation owner.
    ///
    /// # Errors
    /// Returns the bounded diagnostic the apply receipt records.
    fn rewrite_body(&self, repo: &str, issue: u64, body: &str) -> Result<(), String>;
    /// Close one issue as not planned.
    ///
    /// # Errors
    /// Returns the bounded diagnostic the apply receipt records.
    fn close_issue(&self, repo: &str, issue: u64) -> Result<(), String>;
    /// Record `client` as blocked by `blocker` in GitHub's native issue graph.
    ///
    /// # Errors
    /// Returns the bounded diagnostic the apply receipt records.
    fn add_blocked_by(&self, repo: &str, client: u64, blocker: u64) -> Result<(), String>;
}

/// The production gateway, holding one hardened client for the whole verb.
///
/// A single audit reads three endpoints for every open issue, so the client and
/// its credential lookup are built once and reused rather than rebuilt per call.
pub struct LiveDeps {
    runtime: LarchRuntime,
    service: OctocrabGitHubService,
    cancellation: Cancellation,
}

impl LiveDeps {
    /// Build the live gateway and its one GitHub client.
    ///
    /// # Errors
    /// Returns the setup diagnostic when the runtime or the client cannot be
    /// built.
    pub fn new() -> Result<Self, String> {
        let working_directory = std::env::current_dir()
            .map_err(|error| format!("cannot resolve directory: {error}"))?;
        let runtime =
            LarchRuntime::new().map_err(|error| format!("cannot initialize runtime: {error}"))?;
        let cancellation = Cancellation::new();
        let service = runtime.block_on(async {
            let runner = TokioProcessRunner::default();
            OctocrabGitHubService::from_gh(&runner, &working_directory, &cancellation)
                .await
                .map_err(|error| error.to_string())
        })?;
        Ok(Self {
            runtime,
            service,
            cancellation,
        })
    }

    fn repository(repo: &str) -> Result<GitHubRepositoryRef, String> {
        repository_ref(repo).map_err(|()| format!("repository slug is invalid: {repo}"))
    }
}

/// Reduce one issue-graph read to its distinct, sorted issue numbers.
fn edge_numbers(refs: &[DependencyRef]) -> Vec<u64> {
    let mut numbers: Vec<u64> = refs.iter().map(DependencyRef::issue_number).collect();
    numbers.sort_unstable();
    numbers.dedup();
    numbers
}

/// Classify one failed open-issue read into the warning the snapshot publishes.
///
/// Python distinguished a `gh` failure from an unparseable response; the typed
/// adapter reports the latter as a malformed response, so the two codes survive.
fn read_failure(error: &GitHubOperationError) -> DepsReadFailure {
    DepsReadFailure {
        code: match error.kind() {
            GitHubOperationErrorKind::MalformedResponse => "json_invalid",
            _other => "gh_api_failed",
        },
        detail: deps_flat_error(&error.to_string(), GH_ERROR_CHARS),
    }
}

/// Normalize one listed issue set into the rows the audit reads.
///
/// The REST list returns pull requests alongside issues, where `gh issue list`
/// did not, so they are dropped here.
fn open_rows_from(listed: Vec<GitHubIssue>) -> Vec<DepsOpenIssue> {
    let mut rows: Vec<DepsOpenIssue> = listed
        .into_iter()
        .filter(|issue| !issue.is_pull_request && issue.state == GitHubIssueState::Open)
        .map(|issue| DepsOpenIssue {
            number: issue.number,
            title: issue.title,
            body: issue.body,
            labels: issue
                .labels
                .into_iter()
                .map(|label| label.name)
                .filter(|name| !name.is_empty())
                .collect(),
        })
        .collect();
    rows.sort_by_key(|row| row.number);
    rows
}

/// Spell one live issue state the way the apply-time predicates read it.
fn live_state(state: GitHubIssueState) -> String {
    match state {
        GitHubIssueState::Open => "open".to_owned(),
        GitHubIssueState::Closed => "closed".to_owned(),
        GitHubIssueState::All => String::new(),
    }
}

/// Compose the body-only compare-and-swap one approved rewrite applies.
fn body_mutation_request(snapshot: &IssueMutationSnapshot, body: &str) -> IssueMutationRequest {
    IssueMutationRequest {
        repository: snapshot.repository.clone(),
        issue: snapshot.issue,
        expected_updated_at: snapshot.updated_at.clone(),
        expected_state: snapshot.state,
        fields: BTreeSet::from([IssueMutationField::Body]),
        title: None,
        body: Some(body.to_owned()),
        labels: None,
        marker: None,
        lease: None,
    }
}

impl DepsGateway for LiveDeps {
    fn origin_slug(&self) -> String {
        remote_slug("origin").unwrap_or_default()
    }

    fn open_issues(&self, repo: &str) -> Result<Vec<DepsOpenIssue>, DepsReadFailure> {
        let repository = Self::repository(repo).map_err(|detail| DepsReadFailure {
            code: "gh_api_failed",
            detail,
        })?;
        let bound = self.service.transport_policy().limits().items();
        // A dependency audit must reason over every open issue, so the open
        // snapshot is exhaustive: an over-bound corpus fails closed through
        // `read_failure` rather than silently narrowing the audit's reach.
        let request = GitHubIssueList {
            repo: repository,
            state: GitHubIssueState::Open,
            labels: Vec::new(),
            limit: bound,
            mode: GitHubIssueListMode::Exhaustive,
        };
        let listed = self
            .runtime
            .block_on(async { self.service.list_issues(&request, &self.cancellation).await })
            .map_err(|error| read_failure(&error))?;
        Ok(open_rows_from(listed.issues))
    }

    fn comments(&self, repo: &str, issue: u64) -> Result<Vec<(u64, String)>, String> {
        let repository = Self::repository(repo)?;
        self.runtime
            .block_on(async {
                self.service
                    .list_comments(&repository, issue, &self.cancellation)
                    .await
            })
            .map(|comments| {
                comments
                    .into_iter()
                    .map(|comment| (comment.id, comment.body))
                    .collect()
            })
            .map_err(|error| deps_flat_error(&error.to_string(), GH_ERROR_CHARS))
    }

    fn dependencies(&self, repo: &str, issue: u64, blocking: bool) -> Result<Vec<u64>, String> {
        let repository = Self::repository(repo)?;
        self.runtime
            .block_on(async {
                if blocking {
                    self.service
                        .list_blocking(
                            &self.cancellation,
                            repository.owner(),
                            repository.name(),
                            issue,
                        )
                        .await
                } else {
                    self.service
                        .list_blocked_by(
                            &self.cancellation,
                            repository.owner(),
                            repository.name(),
                            issue,
                        )
                        .await
                }
            })
            .map(|refs| edge_numbers(&refs))
            .map_err(|error| deps_flat_error(&error.to_string(), GH_ERROR_CHARS))
    }

    fn live_issue(&self, repo: &str, issue: u64) -> Option<DepsLiveIssue> {
        let repository = Self::repository(repo).ok()?;
        let live = self
            .runtime
            .block_on(async {
                self.service
                    .issue(&repository, issue, &self.cancellation)
                    .await
            })
            .ok()?;
        Some(DepsLiveIssue {
            title: live.title,
            state: live_state(live.state),
        })
    }

    fn rewrite_body(&self, repo: &str, issue: u64, body: &str) -> Result<(), String> {
        let repository = Self::repository(repo)?;
        let owner = IssueMutationOwner::new(&self.service);
        self.runtime.block_on(async {
            let snapshot = owner
                .read_snapshot(&repository, issue, &self.cancellation)
                .await
                .map_err(|error| deps_flat_error(&error.to_string(), MUTATION_ERROR_CHARS))?;
            let request = body_mutation_request(&snapshot, body);
            owner
                .apply(
                    &self.cancellation,
                    &authorization_request("", "", "", true),
                    &request,
                )
                .await
                .map(|_verified| ())
                .map_err(|error| deps_flat_error(&error.to_string(), MUTATION_ERROR_CHARS))
        })
    }

    fn close_issue(&self, repo: &str, issue: u64) -> Result<(), String> {
        let repository = Self::repository(repo)?;
        let owner = IssueMutationOwner::new(&self.service);
        self.runtime.block_on(async {
            owner
                .close_not_planned(&self.cancellation, &repository, issue)
                .await
                .map(|_closed| ())
                .map_err(|error| deps_flat_error(&error, GH_ERROR_CHARS))
        })
    }

    fn add_blocked_by(&self, repo: &str, client: u64, blocker: u64) -> Result<(), String> {
        // `/deps` writes only what the operator approved at its own gate, so
        // the edge carries the operator-invoked authorization the Python
        // entrypoint spawned `block-issue add-blocked-by --operator-invoked` for.
        apply_blocked_by(&in_process_edge(
            Self::repository(repo)?,
            client,
            blocker,
            EdgeAuthorization::OperatorInvoked,
        ))
        .map_err(|error| deps_flat_error(&error, GH_ERROR_CHARS))
    }
}

// ---------------------------------------------------------------------------
// Command lines
// ---------------------------------------------------------------------------

const RESOLVE_REPO_USAGE: &str = "usage: cli.py deps resolve-repo [-h] [--repo REPO]";
const RESOLVE_REPO_HELP: &str = concat!(
    "usage: cli.py deps resolve-repo [-h] [--repo REPO]\n",
    "\n",
    "options:\n",
    "  -h, --help   show this help message and exit\n",
    "  --repo REPO\n",
);
const FETCH_USAGE: &str = "usage: cli.py deps fetch [-h] --repo REPO --output-file OUTPUT_FILE";
const FETCH_HELP: &str = concat!(
    "usage: cli.py deps fetch [-h] --repo REPO --output-file OUTPUT_FILE\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --repo REPO\n",
    "  --output-file OUTPUT_FILE\n",
);
const EXPLICIT_REFS_USAGE: &str = concat!(
    "usage: cli.py deps explicit-refs [-h] --fetch-file FETCH_FILE --output-file\n",
    "                                 OUTPUT_FILE",
);
const EXPLICIT_REFS_HELP: &str = concat!(
    "usage: cli.py deps explicit-refs [-h] --fetch-file FETCH_FILE --output-file\n",
    "                                 OUTPUT_FILE\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --fetch-file FETCH_FILE\n",
    "  --output-file OUTPUT_FILE\n",
);
const WRITE_PROPOSALS_USAGE: &str = concat!(
    "usage: cli.py deps write-proposals [-h] --output-file OUTPUT_FILE --fetch-file\n",
    "                                   FETCH_FILE",
);
const WRITE_PROPOSALS_HELP: &str = concat!(
    "usage: cli.py deps write-proposals [-h] --output-file OUTPUT_FILE --fetch-file\n",
    "                                   FETCH_FILE\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --output-file OUTPUT_FILE\n",
    "  --fetch-file FETCH_FILE\n",
);
const PLAN_USAGE: &str = concat!(
    "usage: cli.py deps plan [-h] --fetch-file FETCH_FILE --proposals-file\n",
    "                        PROPOSALS_FILE [--pair-cap PAIR_CAP]",
);
const PLAN_HELP: &str = concat!(
    "usage: cli.py deps plan [-h] --fetch-file FETCH_FILE --proposals-file\n",
    "                        PROPOSALS_FILE [--pair-cap PAIR_CAP]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --fetch-file FETCH_FILE\n",
    "  --proposals-file PROPOSALS_FILE\n",
    "  --pair-cap PAIR_CAP\n",
);
const APPLY_USAGE: &str = concat!(
    "usage: cli.py deps apply [-h] --repo REPO --plan-file PLAN_FILE\n",
    "                         [--rewrites-only] [--edges-only]",
);
const APPLY_HELP: &str = concat!(
    "usage: cli.py deps apply [-h] --repo REPO --plan-file PLAN_FILE\n",
    "                         [--rewrites-only] [--edges-only]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --repo REPO\n",
    "  --plan-file PLAN_FILE\n",
    "  --rewrites-only\n",
    "  --edges-only\n",
);

/// Report whether the line asks for help, which `argparse` answers first.
fn asks_for_help(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .any(|argument| argument == "-h" || argument == "--help")
}

/// Scan one command line, answering `--help` and refusing an unusable one.
fn scan(
    arguments: &[OsString],
    options: &[&'static str],
    flags: &[&'static str],
    help: &str,
) -> Result<ParsedCommandLine, ExitCode> {
    if asks_for_help(arguments) {
        print!("{help}");
        return Err(ExitCode::SUCCESS);
    }
    Ok(parse_with_flags(arguments, options, flags, 0))
}

/// Refuse one command line the way `argparse` refuses it.
fn refuse(usage: &str, program: &str, error: &str) -> ExitCode {
    usage_error(usage, program, error, USAGE_EXIT)
}

/// Read the required option values, or the `argparse` missing-argument error.
fn required<'line>(
    parsed: &'line ParsedCommandLine,
    names: &[&'static str],
) -> Result<Vec<&'line str>, String> {
    let present: Vec<(&str, bool)> = names
        .iter()
        .map(|name| (*name, parsed.value(name).is_some()))
        .collect();
    if present.iter().any(|(_name, found)| !found) {
        return Err(missing(&present));
    }
    Ok(names
        .iter()
        .map(|name| {
            parsed
                .value(name)
                .and_then(std::ffi::OsStr::to_str)
                .unwrap_or_default()
        })
        .collect())
}

// ---------------------------------------------------------------------------
// File helpers
// ---------------------------------------------------------------------------

/// Read one JSON document, reporting the Python diagnostic shape on failure.
fn load_json(path: &str, desc: &str) -> Result<Value, String> {
    let text = fs::read_to_string(path).map_err(|error| {
        if error.kind() == ErrorKind::NotFound {
            format!("{desc}: file not found: {path}")
        } else {
            format!("{desc}: cannot read: {path}")
        }
    })?;
    serde_json::from_str(&text).map_err(|error| format!("{desc}: invalid JSON: {error}"))
}

/// Read the operator snapshot and prove it is an `ok` document.
fn load_ok_document(path: &str, desc: &str) -> Result<Value, String> {
    let document = load_json(path, desc)?;
    if document.get("status") == Some(&Value::String("ok".to_owned())) {
        Ok(document)
    } else {
        Err(format!("{desc}: status is not ok"))
    }
}

/// Resolve and read the machine snapshot the operator snapshot names.
///
/// The pointer is untrusted operator input, so only its file name survives and
/// it must resolve to a sibling of the snapshot that named it: a plan can never
/// be validated against a corpus from somewhere else on disk.
fn resolve_machine_fetch(fetch_file: &str, fetch: &Value) -> Result<Value, String> {
    let named = python_str(fetch.get("machine_fetch_file"));
    let named = named.trim();
    if named.is_empty() {
        return Err("fetch-file: machine_fetch_file is required".to_owned());
    }
    let directory = absolute(Path::new(fetch_file))
        .parent()
        .map(Path::to_path_buf)
        .ok_or("fetch-file: machine_fetch_file is required")?;
    // Only the file name survives, so the pointer always resolves to a sibling
    // of the snapshot that named it however much traversal it tried to carry.
    let Some(name) = Path::new(named).file_name() else {
        return Err("fetch-file: machine_fetch_file is required".to_owned());
    };
    let candidate = directory.join(name);
    let machine = load_json(&candidate.to_string_lossy(), "machine-fetch-file")?;
    if machine.get("status") == Some(&Value::String("ok".to_owned())) {
        Ok(machine)
    } else {
        Err("machine-fetch-file: status is not ok".to_owned())
    }
}

/// Normalize one path without touching the filesystem.
///
/// The Python entrypoint resolved both sides of the sibling check, so only the
/// lexical shape matters here; a snapshot directory that does not exist yet must
/// still compare equal to itself.
fn absolute(path: &Path) -> PathBuf {
    let mut resolved = if path.is_absolute() {
        PathBuf::new()
    } else {
        std::env::current_dir().unwrap_or_default()
    };
    for component in path.components() {
        match component {
            std::path::Component::CurDir => {}
            std::path::Component::ParentDir => {
                let _popped = resolved.pop();
            }
            other => resolved.push(other),
        }
    }
    resolved
}

/// Write one document, reporting the failure as the caller's own refusal.
fn write_document(path: &str, text: &str) -> Result<(), String> {
    if let Some(parent) = Path::new(path).parent()
        && !parent.as_os_str().is_empty()
    {
        fs::create_dir_all(parent)
            .map_err(|error| format!("cannot create {}: {error}", parent.display()))?;
    }
    fs::write(path, text).map_err(|error| format!("cannot write {path}: {error}"))
}

/// Publish one composed document on stdout, exactly as Python emitted it.
fn emit_json(payload: &Value) -> ExitCode {
    println!("{}", deps_compact_json(payload));
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// deps resolve-repo
// ---------------------------------------------------------------------------

/// Resolve the audited repository and report whether `origin` matches it.
pub fn resolve_repo(arguments: &[OsString]) -> ExitCode {
    let parsed = match scan(arguments, &["--repo"], &[], RESOLVE_REPO_HELP) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    if let Some(error) = parsed.error() {
        return refuse(RESOLVE_REPO_USAGE, "cli.py deps resolve-repo", &error);
    }
    let explicit = parsed
        .value("--repo")
        .and_then(std::ffi::OsStr::to_str)
        .unwrap_or_default();
    run_resolve_repo(explicit, &LiveDepsOrigin)
}

/// The one Git read `deps resolve-repo` needs, kept behind its own seam.
pub trait DepsOrigin {
    /// Return the checkout's `origin` slug, or `""` when there is none.
    fn origin_slug(&self) -> String;
    /// Return the ambient repository slug, or `None`.
    fn ambient_repo(&self) -> Option<String>;
}

struct LiveDepsOrigin;

impl DepsOrigin for LiveDepsOrigin {
    fn origin_slug(&self) -> String {
        remote_slug("origin").unwrap_or_default()
    }

    fn ambient_repo(&self) -> Option<String> {
        resolve_repo_for(None)
    }
}

fn run_resolve_repo(explicit: &str, origin: &impl DepsOrigin) -> ExitCode {
    let repo = if explicit.is_empty() {
        let Some(repo) = origin.ambient_repo().filter(|repo| !repo.is_empty()) else {
            eprintln!("ERROR=Could not determine repository");
            return ExitCode::from(1);
        };
        repo
    } else if validate_repo_slug(explicit) {
        explicit.to_owned()
    } else {
        eprintln!("ERROR=--repo must be exactly owner/name");
        return ExitCode::from(1);
    };
    let origin_slug = origin.origin_slug();
    let matches = !origin_slug.is_empty() && origin_slug == repo;
    emit_kv("REPO", &repo);
    emit_kv("ORIGIN_SLUG", &origin_slug);
    emit_kv("ORIGIN_MATCHES", if matches { "true" } else { "false" });
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// deps fetch
// ---------------------------------------------------------------------------

/// Read every open issue, its comments, and its dependency edges into one snapshot.
pub fn fetch(arguments: &[OsString]) -> ExitCode {
    let parsed = match scan(arguments, &["--repo", "--output-file"], &[], FETCH_HELP) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    if let Some(error) = parsed.value_error() {
        return refuse(FETCH_USAGE, "cli.py deps fetch", error);
    }
    let values = match required(&parsed, &["--repo", "--output-file"]) {
        Ok(values) => values,
        Err(error) => return refuse(FETCH_USAGE, "cli.py deps fetch", &error),
    };
    if let Some(error) = parsed.error() {
        return refuse(FETCH_USAGE, "cli.py deps fetch", &error);
    }
    let (repo, output_file) = (values[0], values[1]);
    if !validate_repo_slug(repo) {
        eprintln!("ERROR=--repo must be exactly owner/name");
        return ExitCode::from(1);
    }
    let gateway = match LiveDeps::new() {
        Ok(gateway) => gateway,
        Err(detail) => {
            // A client that cannot be built is the same failed snapshot a
            // refused read produces, so the verb still writes its output file.
            return finish_fetch(
                output_file,
                &deps_failed_fetch(
                    repo,
                    &[deps_warning(
                        "gh_api_failed",
                        &format!("open issue fetch failed: {detail}"),
                        &[],
                    )],
                ),
                1,
            );
        }
    };
    run_fetch(repo, output_file, &gateway)
}

fn run_fetch(repo: &str, output_file: &str, gateway: &impl DepsGateway) -> ExitCode {
    // A bare file name has an empty parent, and joining onto it yields the same
    // relative sibling names the Python entrypoint recorded.
    let directory = Path::new(output_file)
        .parent()
        .map_or_else(PathBuf::new, Path::to_path_buf);
    let listed = match gateway.open_issues(repo) {
        Ok(listed) => listed,
        Err(failure) => {
            let message = if failure.code == "json_invalid" {
                format!("open issue JSON invalid: {}", failure.detail)
            } else {
                format!("open issue fetch failed: {}", failure.detail)
            };
            return finish_fetch(
                output_file,
                &deps_failed_fetch(repo, &[deps_warning(failure.code, &message, &[])]),
                1,
            );
        }
    };
    let mut warnings: Vec<Value> = Vec::new();
    let mut issues: Vec<DepsFetchedIssue> = Vec::new();
    let mut existing: BTreeSet<DepsEdge> = BTreeSet::new();
    for row in listed {
        let comments = match gateway.comments(repo, row.number) {
            Ok(comments) => comments,
            Err(detail) => {
                warnings.push(deps_warning(
                    "comments_read_failed",
                    &format!("comments read failed for #{}: {detail}", row.number),
                    &[("issue", json!(row.number))],
                ));
                Vec::new()
            }
        };
        for blocking in [false, true] {
            let direction = if blocking { "blocking" } else { "blocked_by" };
            match gateway.dependencies(repo, row.number, blocking) {
                Ok(numbers) => {
                    for other in numbers {
                        let edge = if blocking {
                            (other, row.number)
                        } else {
                            (row.number, other)
                        };
                        if edge.0 != edge.1 {
                            let _ = existing.insert(edge);
                        }
                    }
                }
                Err(detail) => warnings.push(deps_warning(
                    "dependency_read_failed",
                    &format!(
                        "dependency {direction} read failed for #{}: {detail}",
                        row.number
                    ),
                    &[
                        ("issue", json!(row.number)),
                        ("direction", json!(direction)),
                    ],
                )),
            }
        }
        issues.push(DepsFetchedIssue {
            number: row.number,
            title: row.title,
            body: row.body,
            labels: row.labels,
            comments: comments
                .into_iter()
                .map(|(id, body)| (json!(id), body))
                .collect(),
        });
    }
    let corpus_path = directory.join("issues-corpus.xml");
    let machine_path = directory.join("fetch-machine.json");
    let artifacts = deps_fetch_artifacts(
        repo,
        &issues,
        &existing,
        &warnings,
        &directory.join("issue-bodies").to_string_lossy(),
        &corpus_path.to_string_lossy(),
        &machine_path.to_string_lossy(),
    );
    for (path, text) in [
        (&corpus_path, artifacts.corpus),
        (&machine_path, deps_pretty_json(&artifacts.machine)),
    ] {
        if let Err(error) = write_document(&path.to_string_lossy(), &text) {
            eprintln!("ERROR={error}");
            return ExitCode::from(1);
        }
    }
    finish_fetch(output_file, &artifacts.operator, 0)
}

fn finish_fetch(output_file: &str, payload: &Value, code: u8) -> ExitCode {
    if let Err(error) = write_document(output_file, &deps_pretty_json(payload)) {
        eprintln!("ERROR={error}");
        return ExitCode::from(1);
    }
    ExitCode::from(code)
}

// ---------------------------------------------------------------------------
// deps explicit-refs
// ---------------------------------------------------------------------------

/// Scan every fetched body and comment for explicit dependency declarations.
pub fn explicit_refs(arguments: &[OsString]) -> ExitCode {
    let parsed = match scan(
        arguments,
        &["--fetch-file", "--output-file"],
        &[],
        EXPLICIT_REFS_HELP,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    if let Some(error) = parsed.value_error() {
        return refuse(EXPLICIT_REFS_USAGE, "cli.py deps explicit-refs", error);
    }
    let values = match required(&parsed, &["--fetch-file", "--output-file"]) {
        Ok(values) => values,
        Err(error) => return refuse(EXPLICIT_REFS_USAGE, "cli.py deps explicit-refs", &error),
    };
    if let Some(error) = parsed.error() {
        return refuse(EXPLICIT_REFS_USAGE, "cli.py deps explicit-refs", &error);
    }
    match snapshot_issues(values[0]).and_then(|issues| {
        write_document(values[1], &deps_pretty_json(&deps_explicit_refs(&issues)))
    }) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("ERROR={error}");
            ExitCode::from(1)
        }
    }
}

/// Read the machine snapshot the operator snapshot at `fetch_file` names.
fn snapshot_issues(fetch_file: &str) -> Result<DepsIssueMap, String> {
    let fetch = load_ok_document(fetch_file, "fetch-file")?;
    Ok(deps_issue_map(&resolve_machine_fetch(fetch_file, &fetch)?))
}

// ---------------------------------------------------------------------------
// deps write-proposals
// ---------------------------------------------------------------------------

/// Validate the operator's proposal document and record it under the session.
pub fn write_proposals(arguments: &[OsString]) -> ExitCode {
    let parsed = match scan(
        arguments,
        &["--output-file", "--fetch-file"],
        &[],
        WRITE_PROPOSALS_HELP,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    if let Some(error) = parsed.value_error() {
        return refuse(WRITE_PROPOSALS_USAGE, "cli.py deps write-proposals", error);
    }
    let values = match required(&parsed, &["--output-file", "--fetch-file"]) {
        Ok(values) => values,
        Err(error) => return refuse(WRITE_PROPOSALS_USAGE, "cli.py deps write-proposals", &error),
    };
    if let Some(error) = parsed.error() {
        return refuse(WRITE_PROPOSALS_USAGE, "cli.py deps write-proposals", &error);
    }
    match validated_proposals(values[1], &read_stdin())
        .and_then(|proposals| write_document(values[0], &deps_pretty_json(&proposals)))
    {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("ERROR={error}");
            ExitCode::from(1)
        }
    }
}

fn validated_proposals(fetch_file: &str, stdin: &str) -> Result<Value, String> {
    let text = if stdin.is_empty() { "{}" } else { stdin };
    let proposals: Value =
        serde_json::from_str(text).map_err(|error| format!("proposal JSON: {error}"))?;
    if !proposals.is_object() {
        return Err("proposal JSON must be an object".to_owned());
    }
    let _rewrites = deps_proposal_mutations(&proposals, "rewrites")?;
    let _closes = deps_proposal_mutations(&proposals, "closes")?;
    let _edges = deps_proposal_edges(&proposals)?;
    let issues = snapshot_issues(fetch_file)?;
    deps_validate_snapshot_membership(&proposals, &issues.keys().copied().collect())?;
    Ok(proposals)
}

// ---------------------------------------------------------------------------
// deps plan
// ---------------------------------------------------------------------------

/// Compose the one plan the operator approves before anything is mutated.
pub fn plan(arguments: &[OsString]) -> ExitCode {
    let parsed = match scan(
        arguments,
        &["--fetch-file", "--proposals-file", "--pair-cap"],
        &[],
        PLAN_HELP,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    if let Some(error) = parsed.value_error() {
        return refuse(PLAN_USAGE, "cli.py deps plan", error);
    }
    let pair_cap = match parsed.value("--pair-cap").and_then(std::ffi::OsStr::to_str) {
        None => None,
        Some(text) => match text.parse::<i64>() {
            Ok(value) => Some(value),
            Err(_error) => {
                return refuse(
                    PLAN_USAGE,
                    "cli.py deps plan",
                    &format!("argument --pair-cap: invalid int value: '{text}'"),
                );
            }
        },
    };
    let values = match required(&parsed, &["--fetch-file", "--proposals-file"]) {
        Ok(values) => values,
        Err(error) => return refuse(PLAN_USAGE, "cli.py deps plan", &error),
    };
    if let Some(error) = parsed.error() {
        return refuse(PLAN_USAGE, "cli.py deps plan", &error);
    }
    let pair_cap = match pair_cap {
        Some(value) if value < 0 => {
            eprintln!("ERROR=--pair-cap must be non-negative");
            return ExitCode::from(1);
        }
        #[expect(
            clippy::cast_sign_loss,
            reason = "the negative half is refused on the line above"
        )]
        Some(value) => Some(value as u64),
        None => None,
    };
    match run_plan(values[0], values[1], pair_cap, &LiveDepsOrigin) {
        Ok(payload) => emit_json(&payload),
        Err(error) => {
            let _code = emit_json(&json!({"status": "failed", "error": error}));
            ExitCode::from(1)
        }
    }
}

fn run_plan(
    fetch_file: &str,
    proposals_file: &str,
    pair_cap: Option<u64>,
    origin: &impl DepsOrigin,
) -> Result<Value, String> {
    let fetch = load_ok_document(fetch_file, "fetch-file")?;
    let repo = python_str(fetch.get("repo"));
    if repo.is_empty() {
        return Err("fetch-file: repo is required".to_owned());
    }
    let issues = deps_issue_map(&resolve_machine_fetch(fetch_file, &fetch)?);
    let proposals = load_json(proposals_file, "proposals-file")?;
    if !proposals.is_object() {
        return Err("proposals-file: expected JSON object".to_owned());
    }
    let mut existing: BTreeSet<DepsEdge> = BTreeSet::new();
    if let Some(rows) = fetch.get("existing_edges").and_then(Value::as_array) {
        for row in rows {
            let _ = existing.insert(deps_normal_edge(row)?);
        }
    }
    let origin_slug = origin.origin_slug();
    let warnings = fetch
        .get("warnings")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    deps_plan(&DepsPlanInputs {
        repo: &repo,
        issues: &issues,
        existing: &existing,
        proposals: &proposals,
        pair_cap,
        origin_matches: !origin_slug.is_empty() && origin_slug == repo,
        warnings,
    })
}

// ---------------------------------------------------------------------------
// deps apply
// ---------------------------------------------------------------------------

/// Apply exactly the mutations the approved plan carries, and nothing else.
pub fn apply(arguments: &[OsString]) -> ExitCode {
    let parsed = match scan(
        arguments,
        &["--repo", "--plan-file"],
        &["--rewrites-only", "--edges-only"],
        APPLY_HELP,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    if let Some(error) = parsed.value_error() {
        return refuse(APPLY_USAGE, "cli.py deps apply", error);
    }
    let values = match required(&parsed, &["--repo", "--plan-file"]) {
        Ok(values) => values,
        Err(error) => return refuse(APPLY_USAGE, "cli.py deps apply", &error),
    };
    if let Some(error) = parsed.error() {
        return refuse(APPLY_USAGE, "cli.py deps apply", &error);
    }
    let scope = ApplyScope {
        rewrites_only: parsed.flag("--rewrites-only"),
        edges_only: parsed.flag("--edges-only"),
    };
    if scope.rewrites_only && scope.edges_only {
        eprintln!("ERROR=--rewrites-only and --edges-only are mutually exclusive");
        return ExitCode::from(1);
    }
    let plan = match load_apply_plan(values[1], values[0]) {
        Ok(plan) => plan,
        Err(error) => {
            eprintln!("ERROR={error}");
            return ExitCode::from(1);
        }
    };
    let gateway = match LiveDeps::new() {
        Ok(gateway) => gateway,
        Err(detail) => {
            eprintln!("ERROR={detail}");
            return ExitCode::from(1);
        }
    };
    emit_json(&run_apply(values[0], &plan, scope, &gateway))
}

/// Which half of an approved plan this apply pass is allowed to touch.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct ApplyScope {
    /// Apply body rewrites and stale closes only.
    pub rewrites_only: bool,
    /// Apply dependency edges only.
    pub edges_only: bool,
}

/// One approved plan, after its structural preconditions have been proven.
struct ApprovedPlan {
    document: Value,
    dependency_writes_allowed: bool,
    snapshot: Option<BTreeSet<u64>>,
}

/// Prove the plan is one this apply may act on at all.
///
/// Every check here is a refusal, never a repair: a plan that lost its snapshot,
/// names another repository, or disagrees with its own audit metadata is not a
/// plan the operator approved.
fn load_apply_plan(plan_file: &str, repo: &str) -> Result<ApprovedPlan, String> {
    let document = load_ok_document(plan_file, "plan-file")?;
    let has_mutations = ["rewrites", "closes", "edges_to_write"].iter().any(|key| {
        document
            .get(*key)
            .and_then(Value::as_array)
            .is_some_and(|rows| !rows.is_empty())
    });
    let snapshot = deps_snapshot_numbers(&document);
    if has_mutations && snapshot.is_none() {
        return Err(
            "plan-file: snapshot_issue_numbers is required and must be non-empty when plan contains mutations"
                .to_owned(),
        );
    }
    let plan_repo = python_str(document.get("repo"));
    if has_mutations && plan_repo.is_empty() {
        return Err("plan-file: repo is required when plan contains mutations".to_owned());
    }
    if !plan_repo.is_empty() && plan_repo != repo {
        return Err("plan-file: repo does not match --repo".to_owned());
    }
    let dependency_writes_allowed = deps_plan_writes_allowed(&document)?;
    Ok(ApprovedPlan {
        document,
        dependency_writes_allowed,
        snapshot,
    })
}

/// One apply pass's receipt, accumulated as each mutation settles.
#[derive(Default)]
struct ApplyReceipt {
    applied: Vec<Value>,
    skipped: Vec<Value>,
    failed: Vec<Value>,
    warnings: Vec<Value>,
}

impl ApplyReceipt {
    fn into_payload(self) -> Value {
        let counts = json!({
            "applied": self.applied.len(),
            "skipped": self.skipped.len(),
            "failed": self.failed.len(),
            "warnings": self.warnings.len(),
        });
        json!({
            "status": if self.failed.is_empty() { "ok" } else { "partial" },
            "applied": self.applied,
            "skipped": self.skipped,
            "failed": self.failed,
            "warnings": self.warnings,
            "counts": counts,
        })
    }
}

fn plan_rows<'plan>(plan: &'plan Value, key: &str) -> Vec<&'plan Value> {
    plan.get(key)
        .and_then(Value::as_array)
        .map(|rows| rows.iter().filter(|row| row.is_object()).collect())
        .unwrap_or_default()
}

fn outside_snapshot(snapshot: Option<&BTreeSet<u64>>, issue: u64) -> bool {
    snapshot.is_some_and(|numbers| !numbers.contains(&issue))
}

fn run_apply(
    repo: &str,
    plan: &ApprovedPlan,
    scope: ApplyScope,
    gateway: &impl DepsGateway,
) -> Value {
    let mut receipt = ApplyReceipt::default();
    let origin_slug = gateway.origin_slug();
    let regular_refresh_allowed = plan.document.get("regular_refresh_allowed")
        == Some(&Value::Bool(true))
        && !origin_slug.is_empty()
        && origin_slug == repo;
    if !scope.edges_only {
        apply_refreshes(repo, plan, regular_refresh_allowed, gateway, &mut receipt);
    }
    if !scope.rewrites_only {
        apply_edges(repo, plan, gateway, &mut receipt);
    }
    receipt.into_payload()
}

fn apply_refreshes(
    repo: &str,
    plan: &ApprovedPlan,
    allowed: bool,
    gateway: &impl DepsGateway,
    receipt: &mut ApplyReceipt,
) {
    let rewrites = plan_rows(&plan.document, "rewrites");
    let closes = plan_rows(&plan.document, "closes");
    let refreshes_planned = !rewrites.is_empty() || !closes.is_empty();
    if refreshes_planned && !allowed {
        for (kind, rows) in [
            ("rewrite", rewrites.as_slice()),
            ("close", closes.as_slice()),
        ] {
            for row in rows {
                if let Some(issue) = json_positive_integer(row.get("issue")) {
                    receipt.skipped.push(json!({
                        "kind": kind,
                        "issue": issue,
                        "reason": "regular refresh not allowed",
                    }));
                }
            }
        }
        return;
    }
    for (kind, rows) in [
        ("rewrite", rewrites.as_slice()),
        ("close", closes.as_slice()),
    ] {
        for row in rows {
            let Some(issue) = json_positive_integer(row.get("issue")) else {
                continue;
            };
            if outside_snapshot(plan.snapshot.as_ref(), issue) {
                receipt.skipped.push(json!({
                    "kind": kind,
                    "issue": issue,
                    "reason": "issue was not in fetch snapshot",
                }));
                continue;
            }
            if !gateway
                .live_issue(repo, issue)
                .is_some_and(|live| live.is_open_mutable_regular())
            {
                receipt.skipped.push(json!({
                    "kind": kind,
                    "issue": issue,
                    "reason": "issue is no longer open mutable REGULAR",
                }));
                continue;
            }
            let outcome = if kind == "rewrite" {
                gateway.rewrite_body(
                    repo,
                    issue,
                    &deps_sanitize_outbound_body(&python_str(row.get("body"))),
                )
            } else {
                gateway.close_issue(repo, issue)
            };
            match outcome {
                Ok(()) => receipt.applied.push(json!({"kind": kind, "issue": issue})),
                Err(error) => receipt.failed.push(json!({
                    "kind": kind,
                    "issue": issue,
                    "error": error,
                })),
            }
        }
    }
}

fn apply_edges(
    repo: &str,
    plan: &ApprovedPlan,
    gateway: &impl DepsGateway,
    receipt: &mut ApplyReceipt,
) {
    let rows = plan_rows(&plan.document, "edges_to_write");
    let mutation_issues: BTreeSet<u64> = ["rewrites", "closes"]
        .iter()
        .flat_map(|key| plan_rows(&plan.document, key))
        .filter_map(|row| json_positive_integer(row.get("issue")))
        .collect();
    let mut batch: BTreeSet<DepsEdge> = BTreeSet::new();
    let mut live_edges: Option<BTreeSet<DepsEdge>> = None;
    let mut graph_complete = false;
    for row in rows {
        let Ok((client, blocker)) = deps_normal_edge(row) else {
            // The plan is machine written; a malformed edge is refused rather
            // than repaired, and the whole pass reports it as one failure.
            receipt.failed.push(json!({
                "kind": "edge",
                "error": "edge must carry positive client_issue and blocker_issue values",
            }));
            continue;
        };
        let skip = |receipt: &mut ApplyReceipt, reason: &str| {
            receipt.skipped.push(json!({
                "kind": "edge",
                "client_issue": client,
                "blocker_issue": blocker,
                "reason": reason,
            }));
        };
        if !plan.dependency_writes_allowed {
            skip(receipt, "partial-audit block");
            receipt.warnings.push(deps_warning(
                "partial_audit_block",
                &format!("Skipped dependency #{client} blocked by #{blocker}: partial-audit block"),
                &[],
            ));
            continue;
        }
        if outside_snapshot(plan.snapshot.as_ref(), client)
            || outside_snapshot(plan.snapshot.as_ref(), blocker)
        {
            skip(receipt, "endpoint was not in fetch snapshot");
            continue;
        }
        if live_edges.is_none() {
            let (edges, warnings, complete) = refresh_dependency_graph(repo, gateway);
            receipt.warnings.extend(warnings);
            graph_complete = complete;
            live_edges = Some(edges);
        }
        if !graph_complete {
            skip(receipt, "live dependency graph refresh incomplete");
            receipt.warnings.push(deps_warning(
                "graph_refresh_incomplete",
                &format!(
                    "Skipped dependency #{client} blocked by #{blocker}: live dependency graph refresh incomplete"
                ),
                &[],
            ));
            continue;
        }
        let mut live: BTreeMap<u64, DepsLiveIssue> = BTreeMap::new();
        for issue in [client, blocker]
            .into_iter()
            .chain(mutation_issues.iter().copied())
        {
            if let Some(meta) = gateway.live_issue(repo, issue) {
                let _previous = live.insert(issue, meta);
            }
        }
        let mut known = live_edges.clone().unwrap_or_default();
        known.extend(batch.iter().copied());
        if let Some(reason) = deps_revalidate_edge((client, blocker), &live, &known) {
            skip(receipt, reason);
            receipt.warnings.push(deps_warning(
                "edge_apply_skipped",
                &format!("Skipped dependency #{client} blocked by #{blocker}: {reason}"),
                &[],
            ));
            continue;
        }
        match gateway.add_blocked_by(repo, client, blocker) {
            Ok(()) => {
                receipt.applied.push(json!({
                    "kind": "edge",
                    "client_issue": client,
                    "blocker_issue": blocker,
                }));
                let _inserted = batch.insert((client, blocker));
            }
            Err(error) => receipt.failed.push(json!({
                "kind": "edge",
                "client_issue": client,
                "blocker_issue": blocker,
                "error": error,
            })),
        }
    }
}

/// Re-read the whole open dependency graph immediately before the first write.
///
/// A partial refresh is treated as no refresh: an edge is written only when the
/// graph it was validated against is known to be complete, because a missing
/// edge is exactly what would hide a cycle or a duplicate.
fn refresh_dependency_graph(
    repo: &str,
    gateway: &impl DepsGateway,
) -> (BTreeSet<DepsEdge>, Vec<Value>, bool) {
    let mut warnings: Vec<Value> = Vec::new();
    let listed = match gateway.open_issues(repo) {
        Ok(listed) => listed,
        Err(failure) => {
            let message = if failure.code == "json_invalid" {
                format!("open issue JSON invalid: {}", failure.detail)
            } else {
                format!("open issue fetch failed: {}", failure.detail)
            };
            return (
                BTreeSet::new(),
                vec![deps_warning(failure.code, &message, &[])],
                false,
            );
        }
    };
    let mut edges: BTreeSet<DepsEdge> = BTreeSet::new();
    let mut complete = true;
    for row in listed {
        for blocking in [false, true] {
            let direction = if blocking { "blocking" } else { "blocked_by" };
            match gateway.dependencies(repo, row.number, blocking) {
                Ok(numbers) => {
                    for other in numbers {
                        let edge = if blocking {
                            (other, row.number)
                        } else {
                            (row.number, other)
                        };
                        if edge.0 != edge.1 {
                            let _ = edges.insert(edge);
                        }
                    }
                }
                Err(detail) => {
                    complete = false;
                    warnings.push(deps_warning(
                        "dependency_read_failed",
                        &format!(
                            "dependency {direction} read failed for #{}: {detail}",
                            row.number
                        ),
                        &[
                            ("issue", json!(row.number)),
                            ("direction", json!(direction)),
                        ],
                    ));
                }
            }
        }
    }
    (edges, warnings, complete)
}

#[cfg(test)]
mod tests;
