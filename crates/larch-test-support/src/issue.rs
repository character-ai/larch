//! Offline issue-domain fixtures, snapshots, and a loopback GitHub service stub.
//!
//! The graph fixtures own all state below a private temporary root. The service
//! stub is the sole exception: it binds an ephemeral loopback listener so an
//! HTTP adapter can be exercised without a remote endpoint.

use std::{
    any::Any,
    collections::{BTreeMap, BTreeSet, VecDeque},
    fmt,
    io::{self, ErrorKind, Read as _, Write as _},
    net::{Shutdown, TcpListener, TcpStream},
    path::Path,
    sync::{Arc, Mutex, mpsc},
    thread::{self, JoinHandle},
    time::Duration,
};

use crate::{
    BoundedBytes, ExecutionSnapshot, HttpResponse, HttpResponseBuilder, HttpResponseError,
    ParityDifference, TestWorkspace,
    snapshot_util::{find_bytes, fnv1a, path_bytes, redact_matching_lines, replace_all},
};

const ISSUE_GRAPH_SNAPSHOT_SCHEMA: u32 = 1;
const ISSUE_STDOUT_SNAPSHOT_SCHEMA: u32 = 1;
const ISSUE_LIMIT: usize = 256;
const ISSUE_EDGE_LIMIT: usize = 1024;
const ISSUE_LABEL_LIMIT: usize = 64;
const ISSUE_COMMENT_LIMIT: usize = 64;
const ISSUE_STDOUT_FIELD_LIMIT: usize = 256;
const REQUEST_HEADER_LIMIT: usize = 64 * 1024;
const REQUEST_BODY_LIMIT: usize = 1024 * 1024;

const SENSITIVE_LINE_NEEDLES: [&[u8]; 10] = [
    b"authorization",
    b"bearer ",
    b"password",
    b"credential",
    b"api_key",
    b"api-key",
    b"access_token",
    b"secret-token",
    b"token=",
    b"\"token\":",
];

const GITHUB_TOKEN_PREFIXES: [&[u8]; 6] =
    [b"ghp_", b"gho_", b"ghs_", b"ghu_", b"ghr_", b"github_pat_"];

/// Named issue-graph shape used by issue-domain parity tests.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IssueFixture {
    Absent,
    Partial,
    Conflicting,
    Committed,
}

impl IssueFixture {
    /// Return the semantic state represented by this fixture.
    #[must_use]
    pub const fn state(self) -> IssueGraphState {
        match self {
            Self::Absent => IssueGraphState::Absent,
            Self::Partial => IssueGraphState::Partial,
            Self::Conflicting => IssueGraphState::Conflicting,
            Self::Committed => IssueGraphState::Committed,
        }
    }
}

/// Coarse semantic completeness of an issue graph fixture.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IssueGraphState {
    Absent,
    Partial,
    Conflicting,
    Committed,
}

impl IssueGraphState {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Absent => "absent",
            Self::Partial => "partial",
            Self::Conflicting => "conflicting",
            Self::Committed => "committed",
        }
    }
}

/// Public lifecycle state of a GitHub issue.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IssueState {
    Open,
    Closed,
}

impl IssueState {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Open => "open",
            Self::Closed => "closed",
        }
    }
}

/// One issue record in an isolated issue graph.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueRecord {
    pub number: u64,
    pub title: String,
    pub body: String,
    pub state: IssueState,
    pub labels: Vec<String>,
    pub comments: Vec<String>,
}

/// A directed issue relation. For sub-issues `source` is the parent; for
/// blocked-by relationships `source` is the blocked issue.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct IssueEdge {
    pub source: u64,
    pub target: u64,
}

impl IssueEdge {
    #[must_use]
    pub const fn new(source: u64, target: u64) -> Self {
        Self { source, target }
    }
}

/// Builder for one isolated in-memory issue graph.
#[derive(Clone, Debug)]
pub struct IssueGraphBuilder {
    fixture: IssueFixture,
    repository_slug: String,
}

impl IssueGraphBuilder {
    #[must_use]
    pub fn new(fixture: IssueFixture) -> Self {
        Self {
            fixture,
            repository_slug: "character-ai/larch".to_owned(),
        }
    }

    /// Set the repository identity that fixture bodies may reference.
    ///
    /// Snapshots replace this value with `<REPOSITORY>`.
    #[must_use]
    pub fn repository_slug(mut self, repository_slug: impl Into<String>) -> Self {
        self.repository_slug = repository_slug.into();
        self
    }

    /// Build the fixture without changing the process environment or cwd.
    ///
    /// # Errors
    /// Returns private-workspace setup failures.
    pub fn build(self) -> io::Result<IssueGraph> {
        let Self {
            fixture,
            repository_slug,
        } = self;
        let workspace = TestWorkspace::new()?;
        let root = workspace.root().to_string_lossy();
        let (issues, sub_issues, blocked_by) =
            fixture_records(fixture, root.as_ref(), &repository_slug);
        Ok(IssueGraph {
            workspace,
            state: fixture.state(),
            repository_slug,
            issues,
            sub_issues,
            blocked_by,
        })
    }
}

/// An owned, isolated issue graph.
#[derive(Debug)]
pub struct IssueGraph {
    workspace: TestWorkspace,
    state: IssueGraphState,
    repository_slug: String,
    issues: BTreeMap<u64, IssueRecord>,
    sub_issues: BTreeSet<IssueEdge>,
    blocked_by: BTreeSet<IssueEdge>,
}

impl IssueGraph {
    #[must_use]
    pub fn builder(fixture: IssueFixture) -> IssueGraphBuilder {
        IssueGraphBuilder::new(fixture)
    }

    #[must_use]
    pub fn root(&self) -> &Path {
        self.workspace.root()
    }

    #[must_use]
    pub const fn state(&self) -> IssueGraphState {
        self.state
    }

    #[must_use]
    pub fn repository_slug(&self) -> &str {
        &self.repository_slug
    }

    #[must_use]
    pub fn issue(&self, number: u64) -> Option<&IssueRecord> {
        self.issues.get(&number)
    }

    pub fn issues(&self) -> impl Iterator<Item = &IssueRecord> {
        self.issues.values()
    }

    pub fn sub_issues(&self) -> impl Iterator<Item = IssueEdge> + '_ {
        self.sub_issues.iter().copied()
    }

    pub fn blocked_by(&self) -> impl Iterator<Item = IssueEdge> + '_ {
        self.blocked_by.iter().copied()
    }
}

/// One normalized issue node in a semantic snapshot.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueNodeSnapshot {
    pub number: u64,
    pub title: BoundedBytes,
    pub body: BoundedBytes,
    pub state: IssueState,
    pub labels: Vec<BoundedBytes>,
    pub labels_truncated: bool,
    pub comments: Vec<BoundedBytes>,
    pub comments_truncated: bool,
}

/// Bounded semantic snapshot of an issue graph.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueGraphSnapshot {
    pub schema: u32,
    pub execution: ExecutionSnapshot,
    pub state: IssueGraphState,
    pub issues: Vec<IssueNodeSnapshot>,
    pub issues_truncated: bool,
    pub sub_issues: Vec<IssueEdge>,
    pub sub_issues_truncated: bool,
    pub blocked_by: Vec<IssueEdge>,
    pub blocked_by_truncated: bool,
}

impl IssueGraphSnapshot {
    /// Capture a stable, redacted view of an isolated issue graph.
    #[must_use]
    pub fn capture(graph: &IssueGraph, execution: ExecutionSnapshot) -> Self {
        let mut issues: Vec<_> = graph
            .issues
            .values()
            .map(|issue| capture_issue_node(issue, graph.root(), graph.repository_slug()))
            .collect();
        let issues_truncated = issues.len() > ISSUE_LIMIT;
        issues.truncate(ISSUE_LIMIT);

        let mut sub_issues: Vec<_> = graph.sub_issues().collect();
        let sub_issues_truncated = sub_issues.len() > ISSUE_EDGE_LIMIT;
        sub_issues.truncate(ISSUE_EDGE_LIMIT);

        let mut blocked_by: Vec<_> = graph.blocked_by().collect();
        let blocked_by_truncated = blocked_by.len() > ISSUE_EDGE_LIMIT;
        blocked_by.truncate(ISSUE_EDGE_LIMIT);

        Self {
            schema: ISSUE_GRAPH_SNAPSHOT_SCHEMA,
            execution,
            state: graph.state(),
            issues,
            issues_truncated,
            sub_issues,
            sub_issues_truncated,
            blocked_by,
            blocked_by_truncated,
        }
    }
}

/// One exact machine field captured from issue-domain stdout.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueStdoutField {
    pub key: String,
    pub value: BoundedBytes,
}

/// Snapshot of issue-domain stdout: ordered exact machine fields and normalized prose.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueStdoutSnapshot {
    pub schema: u32,
    pub fields: Vec<IssueStdoutField>,
    pub fields_truncated: bool,
    pub prose: BoundedBytes,
}

impl IssueStdoutSnapshot {
    /// Capture issue stdout using the operation's temporary root and repository slug.
    #[must_use]
    pub fn capture(stdout: &[u8], root: &Path, repository_slug: &str) -> Self {
        let mut fields = Vec::new();
        let mut prose = Vec::new();
        let mut fields_truncated = false;
        for line in stdout.split_inclusive(|byte| *byte == b'\n') {
            if let Some((key, value)) = stdout_field(line) {
                if fields.len() < ISSUE_STDOUT_FIELD_LIMIT {
                    fields.push(IssueStdoutField {
                        key: String::from_utf8_lossy(key).into_owned(),
                        value: BoundedBytes::new(&normalize_issue_text(
                            value,
                            root,
                            repository_slug,
                        )),
                    });
                } else {
                    fields_truncated = true;
                }
            } else {
                prose.extend_from_slice(line);
            }
        }
        Self {
            schema: ISSUE_STDOUT_SNAPSHOT_SCHEMA,
            fields,
            fields_truncated,
            prose: BoundedBytes::new(&normalize_prose(&prose, root, repository_slug)),
        }
    }
}

/// Differential parity oracle for issue graph and stdout snapshots.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct IssueParityOracle;

impl IssueParityOracle {
    #[must_use]
    pub const fn new() -> Self {
        Self
    }

    /// Compare graph snapshots and name only the semantic channels that differ.
    #[must_use]
    pub fn compare_graphs(
        &self,
        left: &IssueGraphSnapshot,
        right: &IssueGraphSnapshot,
    ) -> Vec<ParityDifference> {
        let mut differences = Vec::new();
        push_difference(
            &mut differences,
            "schema",
            &left.schema.to_string(),
            &right.schema.to_string(),
        );
        push_difference(
            &mut differences,
            "state",
            left.state.as_str(),
            right.state.as_str(),
        );
        compare_execution(&mut differences, &left.execution, &right.execution);
        compare_graph_channel(
            &mut differences,
            "issues",
            &left.issues,
            left.issues_truncated,
            &right.issues,
            right.issues_truncated,
        );
        compare_graph_channel(
            &mut differences,
            "sub_issues",
            &left.sub_issues,
            left.sub_issues_truncated,
            &right.sub_issues,
            right.sub_issues_truncated,
        );
        compare_graph_channel(
            &mut differences,
            "blocked_by",
            &left.blocked_by,
            left.blocked_by_truncated,
            &right.blocked_by,
            right.blocked_by_truncated,
        );
        differences
    }

    /// Compare issue stdout snapshots without treating prose as machine fields.
    #[must_use]
    pub fn compare_stdout(
        &self,
        left: &IssueStdoutSnapshot,
        right: &IssueStdoutSnapshot,
    ) -> Vec<ParityDifference> {
        let mut differences = Vec::new();
        push_difference(
            &mut differences,
            "schema",
            &left.schema.to_string(),
            &right.schema.to_string(),
        );
        compare_graph_channel(
            &mut differences,
            "stdout.fields",
            &left.fields,
            left.fields_truncated,
            &right.fields,
            right.fields_truncated,
        );
        push_difference(
            &mut differences,
            "stdout.prose",
            &bounded_summary(&left.prose),
            &bounded_summary(&right.prose),
        );
        differences
    }
}

/// One response the issue service stub will replay.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum IssueServiceResponse {
    Http(HttpResponse),
    Disconnect,
}

/// One recorded request/response exchange for the issue service stub.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueServiceExchange {
    expected: Option<ExpectedRequest>,
    response: IssueServiceResponse,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ExpectedRequest {
    method: String,
    path: String,
}

impl IssueServiceExchange {
    /// Replay a response only when the client sends the exact method and path.
    #[must_use]
    pub fn new(method: impl Into<String>, path: impl Into<String>, response: HttpResponse) -> Self {
        Self {
            expected: Some(ExpectedRequest {
                method: method.into(),
                path: path.into(),
            }),
            response: IssueServiceResponse::Http(response),
        }
    }

    /// Replay a response for the next request regardless of its route.
    #[must_use]
    pub const fn any(response: HttpResponse) -> Self {
        Self {
            expected: None,
            response: IssueServiceResponse::Http(response),
        }
    }

    /// Build a JSON response for an exact request.
    ///
    /// # Errors
    /// Returns invalid HTTP fixture response configuration.
    pub fn json(
        method: impl Into<String>,
        path: impl Into<String>,
        status: u16,
        body: impl Into<Vec<u8>>,
    ) -> Result<Self, HttpResponseError> {
        Ok(Self::new(method, path, json_response(status, body.into())?))
    }

    /// Build a JSON response for an unconstrained recorded request.
    ///
    /// # Errors
    /// Returns invalid HTTP fixture response configuration.
    pub fn any_json(status: u16, body: impl Into<Vec<u8>>) -> Result<Self, HttpResponseError> {
        Ok(Self::any(json_response(status, body.into())?))
    }

    /// Build a page with the supplied relative pagination continuation.
    ///
    /// # Errors
    /// Returns invalid HTTP fixture response configuration.
    pub fn pagination(
        method: impl Into<String>,
        path: impl Into<String>,
        status: u16,
        body: impl Into<Vec<u8>>,
        next_page: impl AsRef<str>,
    ) -> Result<Self, HttpResponseError> {
        let response = HttpResponseBuilder::new(status)
            .header("content-type", "application/json")?
            .header("link", &format!("<{}>; rel=\"next\"", next_page.as_ref()))?
            .body(body)
            .build()?;
        Ok(Self::new(method, path, response))
    }

    /// Build a retryable GitHub rate-limit response.
    ///
    /// # Errors
    /// Returns invalid HTTP fixture response configuration.
    pub fn rate_limited(
        method: impl Into<String>,
        path: impl Into<String>,
        retry_after_seconds: u64,
        body: impl Into<Vec<u8>>,
    ) -> Result<Self, HttpResponseError> {
        let response = HttpResponseBuilder::new(429)
            .header("content-type", "application/json")?
            .header("retry-after", &retry_after_seconds.to_string())?
            .body(body)
            .build()?;
        Ok(Self::new(method, path, response))
    }

    /// Build a GitHub mutation-conflict response.
    ///
    /// # Errors
    /// Returns invalid HTTP fixture response configuration.
    pub fn conflict(
        method: impl Into<String>,
        path: impl Into<String>,
        body: impl Into<Vec<u8>>,
    ) -> Result<Self, HttpResponseError> {
        Self::json(method, path, 409, body)
    }

    /// Drop the next exact request before sending an HTTP response.
    pub fn disconnect(method: impl Into<String>, path: impl Into<String>) -> Self {
        Self {
            expected: Some(ExpectedRequest {
                method: method.into(),
                path: path.into(),
            }),
            response: IssueServiceResponse::Disconnect,
        }
    }
}

/// A redacted request recorded by the loopback service stub.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueServiceRequest {
    pub method: String,
    pub path: String,
    pub headers: BTreeMap<String, String>,
    pub body: BoundedBytes,
}

/// A loopback-only service that replays recorded GitHub issue responses.
pub struct IssueServiceStub {
    base_url: String,
    requests: Arc<Mutex<Vec<IssueServiceRequest>>>,
    completed: mpsc::Receiver<()>,
    shutdown: Option<mpsc::Sender<()>>,
    worker: Option<JoinHandle<io::Result<()>>>,
}

impl IssueServiceStub {
    /// Start a private loopback listener for the supplied recorded exchanges.
    ///
    /// # Errors
    /// Returns the loopback bind or worker setup error. It never resolves DNS
    /// or contacts a non-loopback address.
    pub fn start(exchanges: impl IntoIterator<Item = IssueServiceExchange>) -> io::Result<Self> {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        listener.set_nonblocking(true)?;
        let base_url = format!("http://{}/", listener.local_addr()?);
        let requests = Arc::new(Mutex::new(Vec::new()));
        let worker_requests = Arc::clone(&requests);
        let exchanges = VecDeque::from_iter(exchanges);
        let (shutdown, receiver) = mpsc::channel();
        let (complete, completed) = mpsc::channel();
        if exchanges.is_empty() {
            let _ = complete.send(());
        }
        let worker = thread::spawn(move || {
            serve_issue_stub(listener, exchanges, worker_requests, receiver, complete)
        });
        Ok(Self {
            base_url,
            requests,
            completed,
            shutdown: Some(shutdown),
            worker: Some(worker),
        })
    }

    #[must_use]
    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    /// Return the redacted requests observed so far.
    ///
    /// # Errors
    /// Returns an error when the request log lock is poisoned.
    pub fn requests(&self) -> io::Result<Vec<IssueServiceRequest>> {
        self.requests
            .lock()
            .map(|requests| requests.clone())
            .map_err(|_| io::Error::other("issue stub request log lock poisoned"))
    }

    /// Stop the listener, verify the recorded exchange queue was consumed, and
    /// return its redacted request log.
    ///
    /// # Errors
    /// Returns worker, request-log, or unconsumed-exchange errors.
    pub fn finish(mut self) -> io::Result<Vec<IssueServiceRequest>> {
        let _ = self.completed.recv_timeout(Duration::from_secs(1));
        self.stop()?;
        self.requests()
    }

    /// Compatibility helper for existing thread-join shaped test fixtures.
    ///
    /// # Errors
    /// Returns the worker panic or stub error payload.
    pub fn join(self) -> thread::Result<()> {
        self.finish()
            .map(|_| ())
            .map_err(|error| Box::new(error) as Box<dyn Any + Send>)
    }

    fn stop(&mut self) -> io::Result<()> {
        if let Some(sender) = self.shutdown.take() {
            let _ = sender.send(());
        }
        let Some(worker) = self.worker.take() else {
            return Ok(());
        };
        worker
            .join()
            .map_err(|_| io::Error::other("issue stub worker panicked"))?
    }
}

impl Drop for IssueServiceStub {
    fn drop(&mut self) {
        let _ = self.stop();
    }
}

#[allow(clippy::too_many_lines)] // One immutable corpus keeps every named graph auditable together.
fn fixture_records(
    fixture: IssueFixture,
    root: &str,
    repository_slug: &str,
) -> (
    BTreeMap<u64, IssueRecord>,
    BTreeSet<IssueEdge>,
    BTreeSet<IssueEdge>,
) {
    let (records, sub_issues, blocked_by) = match fixture {
        IssueFixture::Absent => (vec![], vec![], vec![]),
        IssueFixture::Partial => (
            vec![fixture_issue(
                100,
                "[DESIGNING] Partial issue fixture",
                "<!-- larch:plan:start -->\n## Plan\ninterrupted before end marker\n",
                IssueState::Open,
                &["migration"],
                &[],
            )],
            vec![(100, 101)],
            vec![],
        ),
        IssueFixture::Conflicting => (
            vec![
                fixture_issue(
                    100,
                    "[IMPLEMENTING] Conflicting issue fixture",
                    "<!-- larch:plan:start -->\nfirst\n<!-- larch:plan:end -->\n\
                     <!-- larch:plan:start -->\nsecond\n<!-- larch:plan:end -->\n",
                    IssueState::Open,
                    &["lifecycle:designed", "lifecycle:implementing"],
                    &[],
                ),
                fixture_issue(
                    101,
                    "Cycle child",
                    "conflicting graph child\n",
                    IssueState::Closed,
                    &[],
                    &[],
                ),
            ],
            vec![(100, 101), (101, 100)],
            vec![(100, 101)],
        ),
        IssueFixture::Committed => (
            vec![
                fixture_issue(
                    100,
                    "[UMBRELLA] Issue fixture graph",
                    "## Fixture umbrella\n\
                     Repository: <FIXTURE_REPOSITORY>\n\
                     Root: <FIXTURE_ROOT>\n\
                     <!-- larch:umbrella-proposal\n\
                     {\"version\":1,\"repository\":\"<FIXTURE_REPOSITORY>\"}\n\
                     -->\n",
                    IssueState::Open,
                    &["zeta", "area:issues"],
                    &["umbrella proposal recorded\n"],
                ),
                fixture_issue(
                    101,
                    "[DESIGNED] Wire-body fixture",
                    "Before wire block\n\
                     <!-- larch:plan:start -->\n\
                     ## Plan\n\
                     1. Exercise the fixture.\n\
                     <!-- larch:plan:end -->\n",
                    IssueState::Open,
                    &["alpha", "migration"],
                    &[
                        "<!-- larch:clarify-request id=fixture -->\nWhat remains?\n",
                        "<!-- larch:clarify-response id=fixture -->\nNothing.\n",
                    ],
                ),
                fixture_issue(
                    102,
                    "Plain body fixture",
                    "This issue intentionally has no larch wire block.\n",
                    IssueState::Closed,
                    &["beta"],
                    &["ordinary issue comment\n"],
                ),
                fixture_issue(
                    103,
                    "[IMPLEMENTING] Tracking record fixture",
                    "Tracking issue body\n",
                    IssueState::Open,
                    &[],
                    &[
                        "<!-- larch:plan v1 runid=issue-fixture -->\nplan digest\n",
                        "<!-- larch:metadata v1 runid=issue-fixture -->\nmetadata digest\n",
                    ],
                ),
                fixture_issue(
                    104,
                    "OOS manifest fixture",
                    "## Out-of-scope observations\n",
                    IssueState::Open,
                    &[],
                    &[
                        "<!-- larch:oos-manifest v1 -->\n{\"proposal\":\"fixture\",\"state\":\"pending\"}\n",
                        "Authorization: Bearer ghp_fixturecredential\n",
                    ],
                ),
            ],
            vec![(100, 101), (100, 102), (101, 103)],
            vec![(101, 102), (103, 101)],
        ),
    };
    let issues = records
        .into_iter()
        .map(|issue| {
            let number = issue.number;
            (number, materialize_issue(issue, root, repository_slug))
        })
        .collect();
    let edges = |pairs: Vec<(u64, u64)>| {
        pairs
            .into_iter()
            .map(|(source, target)| IssueEdge::new(source, target))
            .collect()
    };
    (issues, edges(sub_issues), edges(blocked_by))
}

fn fixture_issue(
    number: u64,
    title: &str,
    body: &str,
    state: IssueState,
    labels: &[&str],
    comments: &[&str],
) -> IssueRecord {
    IssueRecord {
        number,
        title: title.to_owned(),
        body: body.to_owned(),
        state,
        labels: labels.iter().map(|value| (*value).to_owned()).collect(),
        comments: comments.iter().map(|value| (*value).to_owned()).collect(),
    }
}

fn materialize_issue(mut issue: IssueRecord, root: &str, repository_slug: &str) -> IssueRecord {
    let replace = |value: String| {
        value
            .replace("<FIXTURE_ROOT>", root)
            .replace("<FIXTURE_REPOSITORY>", repository_slug)
    };
    issue.title = replace(issue.title);
    issue.body = replace(issue.body);
    issue.labels = issue.labels.into_iter().map(&replace).collect();
    issue.comments = issue.comments.into_iter().map(replace).collect();
    issue
}

fn capture_issue_node(
    issue: &IssueRecord,
    root: &Path,
    repository_slug: &str,
) -> IssueNodeSnapshot {
    let mut labels: Vec<_> = issue
        .labels
        .iter()
        .map(|label| {
            BoundedBytes::new(&normalize_issue_text(
                label.as_bytes(),
                root,
                repository_slug,
            ))
        })
        .collect();
    labels.sort_by(|left, right| left.bytes.cmp(&right.bytes));
    let labels_truncated = labels.len() > ISSUE_LABEL_LIMIT;
    labels.truncate(ISSUE_LABEL_LIMIT);

    let mut comments: Vec<_> = issue
        .comments
        .iter()
        .map(|comment| {
            BoundedBytes::new(&normalize_issue_text(
                comment.as_bytes(),
                root,
                repository_slug,
            ))
        })
        .collect();
    let comments_truncated = comments.len() > ISSUE_COMMENT_LIMIT;
    comments.truncate(ISSUE_COMMENT_LIMIT);

    IssueNodeSnapshot {
        number: issue.number,
        title: BoundedBytes::new(&normalize_issue_text(
            issue.title.as_bytes(),
            root,
            repository_slug,
        )),
        body: BoundedBytes::new(&normalize_issue_text(
            issue.body.as_bytes(),
            root,
            repository_slug,
        )),
        state: issue.state,
        labels,
        labels_truncated,
        comments,
        comments_truncated,
    }
}

fn normalize_issue_text(input: &[u8], root: &Path, repository_slug: &str) -> Vec<u8> {
    let mut normalized = replace_all(input, &path_bytes(root), b"<ROOT>");
    if !repository_slug.is_empty() {
        normalized = replace_all(&normalized, repository_slug.as_bytes(), b"<REPOSITORY>");
    }
    redact_issue_credentials(&normalized)
}

fn normalize_prose(input: &[u8], root: &Path, repository_slug: &str) -> Vec<u8> {
    let normalized = normalize_issue_text(input, root, repository_slug);
    replace_all(&normalized, b"\r\n", b"\n")
}

fn redact_issue_credentials(input: &[u8]) -> Vec<u8> {
    let redacted_lines = redact_matching_lines(input, &SENSITIVE_LINE_NEEDLES);
    redact_github_tokens(&redacted_lines)
}

fn redact_github_tokens(input: &[u8]) -> Vec<u8> {
    let mut output = Vec::with_capacity(input.len());
    let mut index = 0;
    while index < input.len() {
        if let Some(prefix) = GITHUB_TOKEN_PREFIXES
            .iter()
            .find(|prefix| input[index..].starts_with(prefix))
        {
            output.extend_from_slice(b"<REDACTED>");
            index += prefix.len();
            while index < input.len() && github_token_byte(input[index]) {
                index += 1;
            }
        } else {
            output.push(input[index]);
            index += 1;
        }
    }
    output
}

const fn github_token_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-')
}

fn stdout_field(line: &[u8]) -> Option<(&[u8], &[u8])> {
    let line = strip_line_ending(line);
    let equals = line.iter().position(|byte| *byte == b'=')?;
    let key = &line[..equals];
    valid_stdout_key(key).then_some((key, &line[equals + 1..]))
}

fn strip_line_ending(line: &[u8]) -> &[u8] {
    let line = line.strip_suffix(b"\n").unwrap_or(line);
    line.strip_suffix(b"\r").unwrap_or(line)
}

fn valid_stdout_key(key: &[u8]) -> bool {
    !key.is_empty()
        && key[0].is_ascii_uppercase()
        && key
            .iter()
            .all(|byte| byte.is_ascii_uppercase() || byte.is_ascii_digit() || *byte == b'_')
}

fn compare_execution(
    differences: &mut Vec<ParityDifference>,
    left: &ExecutionSnapshot,
    right: &ExecutionSnapshot,
) {
    push_difference(
        differences,
        "execution.exit_class",
        &format!("{:?}", left.exit_class),
        &format!("{:?}", right.exit_class),
    );
    push_difference(
        differences,
        "execution.stdout",
        &bounded_summary(&left.stdout),
        &bounded_summary(&right.stdout),
    );
    push_difference(
        differences,
        "execution.stderr",
        &bounded_summary(&left.stderr),
        &bounded_summary(&right.stderr),
    );
}

fn compare_graph_channel<T: fmt::Debug + PartialEq>(
    differences: &mut Vec<ParityDifference>,
    channel: &str,
    left: &[T],
    left_truncated: bool,
    right: &[T],
    right_truncated: bool,
) {
    if left == right && left_truncated == right_truncated {
        return;
    }
    differences.push(ParityDifference {
        channel: channel.to_owned(),
        left: format!(
            "count={} truncated={} digest={:016x}",
            left.len(),
            left_truncated,
            fnv1a(format!("{left:?}").as_bytes())
        ),
        right: format!(
            "count={} truncated={} digest={:016x}",
            right.len(),
            right_truncated,
            fnv1a(format!("{right:?}").as_bytes())
        ),
    });
}

fn bounded_summary(bytes: &BoundedBytes) -> String {
    format!(
        "len={} checksum={:016x} truncated={}",
        bytes.total_len, bytes.checksum, bytes.truncated
    )
}

fn push_difference(
    differences: &mut Vec<ParityDifference>,
    channel: &str,
    left: &str,
    right: &str,
) {
    if left != right {
        differences.push(ParityDifference {
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

fn json_response(status: u16, body: Vec<u8>) -> Result<HttpResponse, HttpResponseError> {
    HttpResponseBuilder::new(status)
        .header("content-type", "application/json")?
        .body(body)
        .build()
}

#[allow(clippy::needless_pass_by_value)] // The worker owns its listener and channels for the thread lifetime.
fn serve_issue_stub(
    listener: TcpListener,
    mut exchanges: VecDeque<IssueServiceExchange>,
    requests: Arc<Mutex<Vec<IssueServiceRequest>>>,
    shutdown: mpsc::Receiver<()>,
    complete: mpsc::Sender<()>,
) -> io::Result<()> {
    loop {
        match shutdown.recv_timeout(Duration::from_millis(5)) {
            Ok(()) | Err(mpsc::RecvTimeoutError::Disconnected) => break,
            Err(mpsc::RecvTimeoutError::Timeout) => {}
        }
        match listener.accept() {
            Ok((socket, _)) => {
                serve_issue_request(socket, &mut exchanges, &requests)?;
                if exchanges.is_empty() {
                    let _ = complete.send(());
                }
            }
            Err(error) if error.kind() == ErrorKind::WouldBlock => {}
            Err(error) => return Err(error),
        }
    }
    if exchanges.is_empty() {
        Ok(())
    } else {
        Err(io::Error::other(format!(
            "issue stub stopped with {} unconsumed exchanges",
            exchanges.len()
        )))
    }
}

fn serve_issue_request(
    mut socket: TcpStream,
    exchanges: &mut VecDeque<IssueServiceExchange>,
    requests: &Arc<Mutex<Vec<IssueServiceRequest>>>,
) -> io::Result<()> {
    socket.set_nonblocking(false)?;
    let request = read_issue_request(&mut socket)?;
    requests
        .lock()
        .map_err(|_| io::Error::other("issue stub request log lock poisoned"))?
        .push(capture_issue_request(&request));
    let exchange = exchanges.pop_front().ok_or_else(|| {
        io::Error::other(format!(
            "unexpected issue stub request: expected no remaining exchange, got {}",
            request_summary(&request)
        ))
    })?;
    if let Some(expected) = exchange.expected {
        let actual = request_summary(&request);
        let wanted = format!("{} {}", expected.method, expected.path);
        if expected.method != request.method || expected.path != request.path {
            return Err(io::Error::other(format!(
                "unexpected issue stub request: expected {wanted}, got {actual}"
            )));
        }
    }
    write_issue_response(&mut socket, exchange.response)
}

struct ReceivedIssueRequest {
    method: String,
    path: String,
    headers: BTreeMap<String, String>,
    body: Vec<u8>,
}

fn read_issue_request(socket: &mut TcpStream) -> io::Result<ReceivedIssueRequest> {
    socket.set_read_timeout(Some(Duration::from_secs(5)))?;
    let mut bytes = Vec::new();
    let header_end = loop {
        if let Some(end) = find_bytes(&bytes, b"\r\n\r\n") {
            if end > REQUEST_HEADER_LIMIT {
                return Err(io::Error::other("issue stub request exceeded bounded size"));
            }
            break end;
        }
        if bytes.len() >= REQUEST_HEADER_LIMIT {
            return Err(io::Error::other("issue stub request exceeded bounded size"));
        }
        read_more(socket, &mut bytes)?;
    };
    let text = std::str::from_utf8(&bytes[..header_end])
        .map_err(|_| io::Error::other("malformed issue stub request: headers are not UTF-8"))?;
    let mut lines = text.split("\r\n");
    let mut request_line = lines
        .next()
        .ok_or_else(|| io::Error::other("malformed issue stub request: missing request line"))?
        .split_ascii_whitespace();
    let method = request_line
        .next()
        .ok_or_else(|| io::Error::other("malformed issue stub request: missing method"))?
        .to_owned();
    let path = request_line
        .next()
        .ok_or_else(|| io::Error::other("malformed issue stub request: missing path"))?
        .to_owned();
    if request_line.next().is_none() || request_line.next().is_some() || !path.starts_with('/') {
        return Err(io::Error::other("malformed issue stub request line"));
    }
    let headers: BTreeMap<_, _> = lines
        .filter_map(|line| line.split_once(':'))
        .map(|(name, value)| (name.to_ascii_lowercase(), value.trim().to_owned()))
        .collect();
    if headers.contains_key("transfer-encoding") {
        return Err(io::Error::other(
            "malformed issue stub request: transfer encoding is unsupported",
        ));
    }
    let body_length = headers
        .get("content-length")
        .map(|value| value.parse::<usize>())
        .transpose()
        .map_err(|_| io::Error::other("malformed issue stub request: invalid content-length"))?
        .unwrap_or(0);
    if body_length > REQUEST_BODY_LIMIT {
        return Err(io::Error::other("issue stub request exceeded bounded size"));
    }
    let expected = header_end
        .checked_add(4)
        .and_then(|length| length.checked_add(body_length))
        .ok_or_else(|| io::Error::other("issue stub request exceeded bounded size"))?;
    if expected > REQUEST_HEADER_LIMIT + REQUEST_BODY_LIMIT {
        return Err(io::Error::other("issue stub request exceeded bounded size"));
    }
    while bytes.len() < expected {
        read_more(socket, &mut bytes)?;
    }
    Ok(ReceivedIssueRequest {
        method,
        path,
        headers,
        body: bytes[header_end + 4..expected].to_vec(),
    })
}

fn read_more(socket: &mut TcpStream, bytes: &mut Vec<u8>) -> io::Result<()> {
    let mut buffer = [0_u8; 4096];
    let count = socket.read(&mut buffer)?;
    if count == 0 {
        return Err(io::Error::other(
            "malformed issue stub request: connection closed before complete request",
        ));
    }
    bytes.extend_from_slice(&buffer[..count]);
    Ok(())
}

fn capture_issue_request(request: &ReceivedIssueRequest) -> IssueServiceRequest {
    let headers = request
        .headers
        .iter()
        .map(|(name, value)| {
            let value = if matches!(name.as_str(), "authorization" | "cookie")
                || name.contains("token")
                || name.contains("key")
                || name.contains("secret")
            {
                "<REDACTED>".to_owned()
            } else {
                String::from_utf8_lossy(&redact_issue_credentials(value.as_bytes())).into_owned()
            };
            (name.clone(), value)
        })
        .collect();
    IssueServiceRequest {
        method: request.method.clone(),
        path: request.path.clone(),
        headers,
        body: BoundedBytes::new(&redact_issue_credentials(&request.body)),
    }
}

fn request_summary(request: &ReceivedIssueRequest) -> String {
    format!("{} {}", request.method, request.path)
}

fn write_issue_response(socket: &mut TcpStream, response: IssueServiceResponse) -> io::Result<()> {
    match response {
        IssueServiceResponse::Disconnect => {
            let _ = socket.shutdown(Shutdown::Both);
            Ok(())
        }
        IssueServiceResponse::Http(response) => {
            write!(socket, "HTTP/1.1 {} Stub\r\n", response.status())?;
            for (name, value) in response.headers() {
                if !matches!(name.as_str(), "connection" | "content-length") {
                    write!(socket, "{name}: {value}\r\n")?;
                }
            }
            write!(
                socket,
                "Content-Length: {}\r\nConnection: close\r\n\r\n",
                response.body().len()
            )?;
            socket.write_all(response.body())?;
            socket.flush()?;
            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use std::{
        io::{Read as _, Write as _},
        net::TcpStream,
    };

    use super::{
        BoundedBytes, ExecutionSnapshot, IssueFixture, IssueGraph, IssueGraphSnapshot,
        IssueGraphState, IssueParityOracle, IssueServiceExchange, IssueServiceStub,
        IssueStdoutSnapshot,
    };
    use crate::snapshot_util::{contains, find_bytes, path_bytes};

    fn capture(fixture: IssueFixture) -> (IssueGraph, IssueGraphSnapshot) {
        let graph = IssueGraph::builder(fixture).build().expect("fixture");
        let snapshot = IssueGraphSnapshot::capture(&graph, ExecutionSnapshot::success());
        (graph, snapshot)
    }

    #[test]
    fn fixtures_and_snapshots_cover_issue_domain_parity() {
        let cwd = std::env::current_dir().expect("cwd");
        let path = std::env::var_os("PATH");
        let (absent, absent_snapshot) = capture(IssueFixture::Absent);
        let (partial, partial_snapshot) = capture(IssueFixture::Partial);
        let (conflicting, conflicting_snapshot) = capture(IssueFixture::Conflicting);
        let (committed, committed_snapshot) = capture(IssueFixture::Committed);
        assert_eq!(
            [
                absent_snapshot.state,
                partial_snapshot.state,
                conflicting_snapshot.state,
                committed_snapshot.state,
            ],
            [
                IssueGraphState::Absent,
                IssueGraphState::Partial,
                IssueGraphState::Conflicting,
                IssueGraphState::Committed,
            ]
        );
        assert_eq!(absent.issues().count(), 0);
        assert!(
            partial
                .issue(100)
                .expect("partial issue")
                .body
                .contains("larch:plan:start")
        );
        assert_eq!(conflicting.sub_issues().count(), 2);
        let text = |number| {
            let issue = committed.issue(number).expect("committed issue");
            format!("{}{}", issue.body, issue.comments.concat())
        };
        for (number, needle) in [
            (100, "larch:umbrella-proposal"),
            (101, "larch:plan:end"),
            (102, "no larch wire block"),
            (103, "larch:plan v1"),
            (104, "larch:oos-manifest"),
        ] {
            assert!(text(number).contains(needle));
        }
        assert_ne!(absent_snapshot, partial_snapshot);
        assert_ne!(partial_snapshot, conflicting_snapshot);
        assert_ne!(conflicting_snapshot, committed_snapshot);

        let alternate = IssueGraph::builder(IssueFixture::Committed)
            .repository_slug("other-org/other-repository")
            .build()
            .expect("fixture");
        assert_eq!(
            committed_snapshot,
            IssueGraphSnapshot::capture(&alternate, ExecutionSnapshot::success())
        );
        let body = &committed_snapshot.issues[0].body.bytes;
        assert!(contains(body, b"<ROOT>") && contains(body, b"<REPOSITORY>"));
        assert!(!contains(body, &path_bytes(committed.root())));
        assert!(!contains(body, b"character-ai/larch"));
        assert!(
            committed_snapshot
                .issues
                .iter()
                .flat_map(|issue| &issue.comments)
                .all(|comment| !contains(&comment.bytes, b"ghp_fixturecredential"))
        );

        let stdout = format!(
            "ISSUE_NUMBER=101\r\nISSUE_URL=https://github.com/{}/issues/101\r\n\
             STATUS=ok\r\nRendered {} with ghp_fixture123\r\n",
            committed.repository_slug(),
            committed.root().display()
        );
        let stdout = IssueStdoutSnapshot::capture(
            stdout.as_bytes(),
            committed.root(),
            committed.repository_slug(),
        );
        assert_eq!(stdout.fields.len(), 3);
        assert_eq!(stdout.fields[0].key, "ISSUE_NUMBER");
        assert_eq!(stdout.fields[0].value.bytes, b"101");
        assert!(contains(&stdout.fields[1].value.bytes, b"<REPOSITORY>"));
        assert!(contains(&stdout.prose.bytes, b"<ROOT>"));
        assert!(!contains(&stdout.prose.bytes, b"ghp_fixture123"));
        assert!(!contains(&stdout.prose.bytes, b"\r"));

        let oracle = IssueParityOracle::new();
        let failed = IssueGraphSnapshot {
            execution: ExecutionSnapshot::failure(Some(2), b"", b"failure"),
            ..committed_snapshot.clone()
        };
        let interrupted = IssueGraphSnapshot {
            execution: ExecutionSnapshot::interrupted(b"", b"interrupted"),
            ..committed_snapshot.clone()
        };
        for (other, channel) in [
            (&partial_snapshot, "state"),
            (&failed, "execution.exit_class"),
            (&interrupted, "execution.exit_class"),
        ] {
            assert!(
                oracle
                    .compare_graphs(&committed_snapshot, other)
                    .iter()
                    .any(|difference| difference.channel == channel)
            );
        }
        let different_stdout = IssueStdoutSnapshot {
            prose: BoundedBytes::new(b"different"),
            ..stdout.clone()
        };
        assert!(
            oracle
                .compare_stdout(&stdout, &different_stdout)
                .iter()
                .any(|difference| difference.channel == "stdout.prose")
        );
        assert_eq!(std::env::current_dir().expect("cwd"), cwd);
        assert_eq!(std::env::var_os("PATH"), path);
    }

    #[test]
    fn service_stub_replays_pagination_rate_limits_conflicts_and_partial_batches() {
        let stub = IssueServiceStub::start([
            IssueServiceExchange::pagination(
                "GET",
                "/repos/o/r/issues?per_page=1",
                200,
                b"[{\"number\":1}]".to_vec(),
                "/repos/o/r/issues?page=2",
            )
            .expect("page"),
            IssueServiceExchange::rate_limited(
                "GET",
                "/repos/o/r/issues?page=2",
                1,
                b"{\"message\":\"slow down\"}".to_vec(),
            )
            .expect("rate limit"),
            IssueServiceExchange::json(
                "GET",
                "/repos/o/r/issues?page=2",
                200,
                b"[{\"number\":2}]".to_vec(),
            )
            .expect("retry page"),
            IssueServiceExchange::json("POST", "/repos/o/r/issues/1/labels", 200, b"[]".to_vec())
                .expect("first batch mutation"),
            IssueServiceExchange::conflict(
                "POST",
                "/repos/o/r/issues/2/labels",
                b"{\"message\":\"conflict\"}".to_vec(),
            )
            .expect("partial batch conflict"),
            IssueServiceExchange::disconnect("GET", "/repos/o/r/issues/3"),
        ])
        .expect("stub");

        let first = raw_response_bytes(&stub, "GET", "/repos/o/r/issues?per_page=1", b"");
        assert_eq!(response_status(&first), 200);
        assert!(contains(
            &first,
            b"link: </repos/o/r/issues?page=2>; rel=\"next\""
        ));
        let limited = raw_response_bytes(&stub, "GET", "/repos/o/r/issues?page=2", b"");
        assert_eq!(response_status(&limited), 429);
        assert!(contains(&limited, b"retry-after: 1"));
        assert_eq!(
            request_status(&stub, "GET", "/repos/o/r/issues?page=2", b""),
            200
        );
        assert_eq!(
            request_status(&stub, "POST", "/repos/o/r/issues/1/labels", b"[]"),
            200
        );
        assert_eq!(
            request_status(&stub, "POST", "/repos/o/r/issues/2/labels", b"[]"),
            409
        );
        assert!(raw_response_bytes(&stub, "GET", "/repos/o/r/issues/3", b"").is_empty());

        let requests = stub.finish().expect("stub completed");
        assert_eq!(requests.len(), 6);
        assert_eq!(requests[3].body.bytes, b"[]");
        assert_eq!(requests[0].headers["authorization"], "<REDACTED>");
    }

    fn response_status(bytes: &[u8]) -> u16 {
        let header_end = find_bytes(bytes, b"\r\n\r\n").expect("response headers");
        let header = std::str::from_utf8(&bytes[..header_end]).expect("response UTF-8");
        header
            .split("\r\n")
            .next()
            .expect("status")
            .split_ascii_whitespace()
            .nth(1)
            .expect("status code")
            .parse()
            .expect("numeric status")
    }

    fn request_status(stub: &IssueServiceStub, method: &str, path: &str, body: &[u8]) -> u16 {
        response_status(&raw_response_bytes(stub, method, path, body))
    }

    fn raw_response_bytes(
        stub: &IssueServiceStub,
        method: &str,
        path: &str,
        body: &[u8],
    ) -> Vec<u8> {
        let address = stub
            .base_url()
            .strip_prefix("http://")
            .expect("loopback URL")
            .trim_end_matches('/');
        let mut socket = TcpStream::connect(address).expect("connect loopback stub");
        write!(
            socket,
            "{method} {path} HTTP/1.1\r\nHost: larch.test\r\nAuthorization: Bearer ghp_fixturecredential\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            body.len()
        )
        .expect("request headers");
        socket.write_all(body).expect("request body");
        socket
            .shutdown(std::net::Shutdown::Write)
            .expect("finish request");
        let mut response = Vec::new();
        socket.read_to_end(&mut response).expect("response");
        response
    }
}
