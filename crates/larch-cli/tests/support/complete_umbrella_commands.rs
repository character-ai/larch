use super::*;
use larch_adapters::github::OctocrabGitHubService;
use larch_core::{is_transient_claude_api_error, parse_claude_envelope};
use larch_test_support::{GitFixture, GitRepository, IssueServiceExchange, IssueServiceStub};
use serde_json::{Value, json};
use std::collections::VecDeque;

const UMBRELLA: u64 = 40;
const LEAF: u64 = 41;
const GAP: u64 = 42;
const PROPOSAL_BODY: &str = "Requirements\n<!-- larch:umbrella-proposal v1 -->";
const BEFORE: &str = "2026-08-01T00:00:00Z";
const AFTER: &str = "2026-08-01T00:01:00Z";
const CLOSED_AT: &str = "2026-08-01T00:02:00Z";

fn service(exchanges: Vec<IssueServiceExchange>) -> (OctocrabGitHubService, IssueServiceStub) {
    let server = IssueServiceStub::start(exchanges).expect("start issue service stub");
    let client = octocrab::Octocrab::builder()
        .personal_token(String::from("test-token"))
        .base_uri(server.base_url())
        .expect("stub base URI")
        .upload_uri(server.base_url())
        .expect("stub upload URI")
        .build()
        .expect("stub client");
    (OctocrabGitHubService::with_test_client(client), server)
}

fn response(status: u16, body: impl AsRef<[u8]>) -> IssueServiceExchange {
    IssueServiceExchange::any_json(status, body.as_ref().to_vec())
        .expect("valid issue service response")
}

fn issue_json(
    number: u64,
    id: u64,
    title: &str,
    body: &str,
    state: &str,
    updated_at: &str,
) -> String {
    let mut issue: Value = serde_json::from_str(include_str!(
        "../../../larch-adapters/fixtures/github_issue.json"
    ))
    .expect("valid issue fixture");
    issue["id"] = json!(id);
    issue["number"] = json!(number);
    issue["title"] = json!(title);
    issue["body"] = json!(body);
    issue["state"] = json!(state);
    issue["updated_at"] = json!(updated_at);
    issue["url"] = json!(format!("https://api.github.com/repos/o/r/issues/{number}"));
    issue["html_url"] = json!(format!("https://github.com/o/r/issues/{number}"));
    issue["labels"] = json!([]);
    issue.to_string()
}

fn refs(values: &[(u64, u64, &str)]) -> String {
    Value::Array(
        values
            .iter()
            .map(|(number, id, state)| json!({ "number": number, "id": id, "state": state }))
            .collect(),
    )
    .to_string()
}

fn repository() -> GitHubRepositoryRef {
    GitHubRepositoryRef::new("o", "r").expect("valid repository")
}

fn closed_graph(parent: &str, leaf: &str) -> Vec<IssueServiceExchange> {
    closed_graph_with_parent_blockers(parent, leaf, &[(LEAF, 410, "closed")])
}

fn closed_graph_with_parent_blockers(
    parent: &str,
    leaf: &str,
    parent_blockers: &[(u64, u64, &str)],
) -> Vec<IssueServiceExchange> {
    vec![
        response(200, parent),
        response(200, refs(&[(LEAF, 410, "closed")])),
        response(200, refs(parent_blockers)),
        response(200, leaf),
        response(200, "[]"),
    ]
}

fn open_graph(parent: &str, leaf: &str) -> Vec<IssueServiceExchange> {
    vec![
        response(200, parent),
        response(200, refs(&[(LEAF, 410, "open")])),
        response(200, refs(&[(LEAF, 410, "open")])),
        response(200, leaf),
        response(200, "[]"),
        response(200, "[]"),
    ]
}

fn attachment_exchanges(
    parent: &str,
    leaf: &str,
    leaf_ref: &str,
    parent_ref: &str,
) -> Vec<IssueServiceExchange> {
    vec![
        response(200, parent),
        response(200, "[]"),
        response(200, leaf),
        response(200, "[]"),
        response(404, "{}"),
        response(200, "[]"),
        response(201, "{}"),
        response(200, leaf_ref),
        response(200, parent),
        response(200, "[]"),
        response(201, "{}"),
        response(200, leaf_ref),
        response(200, parent),
        response(200, leaf_ref),
        response(200, leaf_ref),
        response(200, leaf),
        response(200, "[]"),
        response(200, "[]"),
        response(200, leaf_ref),
        response(200, parent),
        response(200, "[]"),
        response(200, leaf),
        response(200, "[]"),
        response(200, parent_ref),
        response(200, leaf_ref),
        response(200, parent),
        response(200, leaf_ref),
        response(200, parent),
        response(200, leaf_ref),
        response(200, leaf_ref),
        response(200, leaf),
        response(200, "[]"),
        response(200, "[]"),
        response(200, leaf_ref),
    ]
}

#[test]
fn repository_and_positive_issue_inputs_fail_closed() {
    assert!(parse_repository("owner/repo").is_ok());
    assert!(parse_repository("../repo").is_err());
    assert!(require_issue(1, "--issue").is_ok());
    assert!(require_issue(0, "--issue").is_err());
    assert!(require_operator(true).is_ok());
    assert!(require_operator(false).is_err());
    assert!(temporary_root(Path::new("/"), "root").is_err());
}

#[test]
fn command_dispatch_rejects_invalid_inputs_before_remote_work() {
    let files = || GapFileArguments {
        root: PathBuf::from("relative"),
        title_file: PathBuf::from("title"),
        body_file: PathBuf::from("body"),
    };
    let leaf = || LeafArguments {
        repository: String::from("o/r"),
        umbrella: UMBRELLA,
        leaf: LEAF,
    };
    let commands = [
        CompleteUmbrellaCommand::Start(ParentMutationArguments {
            repository: String::from("o/r"),
            issue: UMBRELLA,
            operator_invoked: false,
        }),
        CompleteUmbrellaCommand::Next(NextArguments {
            repository: String::from("o/r"),
            issue: 0,
            output_root: PathBuf::from("relative"),
            output: PathBuf::from("snapshot"),
        }),
        CompleteUmbrellaCommand::RunLeaves(RunLeavesArguments {
            repository: String::from("o/r"),
            repo_root: PathBuf::from("missing"),
            umbrella: UMBRELLA,
            model: String::from("unknown"),
            output_root: PathBuf::from("relative"),
            output: PathBuf::from("snapshot"),
            result_env: PathBuf::from("result"),
            operator_invoked: true,
        }),
        CompleteUmbrellaCommand::RunChild(RunChildArguments {
            repository: String::from("o/r"),
            repo_root: PathBuf::from("missing"),
            umbrella: UMBRELLA,
            leaf: LEAF,
            model: String::from("unknown"),
            output_root: PathBuf::from("relative"),
            output: PathBuf::from("output"),
            result_env: PathBuf::from("result"),
        }),
        CompleteUmbrellaCommand::VerifyChild(LeafArguments {
            umbrella: 0,
            ..leaf()
        }),
        CompleteUmbrellaCommand::RecoverOrphanedChild(RecoverOrphanedChildArguments {
            leaf: leaf(),
            root: PathBuf::from("relative"),
            result_env: PathBuf::from("result.env"),
        }),
        CompleteUmbrellaCommand::ResetLeaf(ResetLeafArguments {
            leaf: LeafArguments {
                umbrella: 0,
                ..leaf()
            },
            operator_invoked: false,
        }),
        CompleteUmbrellaCommand::ValidateGap(ValidateGapArguments {
            umbrella: 0,
            files: files(),
        }),
        CompleteUmbrellaCommand::AttachLeaf(AttachLeafArguments {
            leaf: leaf(),
            operator_invoked: false,
            files: files(),
        }),
        CompleteUmbrellaCommand::Finish(ParentMutationArguments {
            repository: String::from("o/r"),
            issue: UMBRELLA,
            operator_invoked: false,
        }),
    ];

    for command in commands {
        assert_eq!(run(command), ExitCode::FAILURE);
    }
}

#[test]
fn child_terminal_status_accepts_only_complete_success_marker() {
    assert_eq!(
        child_terminal_status("summary\nCOMPLETE_UMBRELLA_CHILD_STATUS=complete\n"),
        Some(ChildResultStatus::Complete)
    );
    assert_eq!(
        child_terminal_status("summary\nCOMPLETE_UMBRELLA_CHILD_STATUS=needs-design\n"),
        Some(ChildResultStatus::NeedsDesign)
    );
    assert_eq!(
        child_terminal_status(
            "summary\nCOMPLETE_UMBRELLA_CHILD_STATUS=needs-orchestrator-finalize\n"
        ),
        None
    );
    assert!(ChildResultStatus::Complete.envelope_complete());
    assert!(!ChildResultStatus::NeedsDesign.envelope_complete());
    assert!(!ChildResultStatus::Failed.envelope_complete());
    assert_eq!(
        child_terminal_status("COMPLETE_UMBRELLA_CHILD_STATUS=failed\n"),
        None
    );
    assert_eq!(child_terminal_status("summary\n"), None);
}

#[test]
fn orphaned_child_recovery_requires_the_exact_transport_and_leaf_identity() {
    let valid =
        format!("BGJOB_RC=orphaned\nSTEP=complete-umbrella-leaf-{LEAF}\nCHILD_ISSUE={LEAF}\n");
    assert!(validate_orphaned_child_result(&valid, LEAF).is_ok());
    assert!(
        validate_orphaned_child_result(
            &format!("BGJOB_RC=timeout\nSTEP=complete-umbrella-leaf-{LEAF}\n"),
            LEAF,
        )
        .is_err()
    );
    assert!(
        validate_orphaned_child_result(
            &format!("BGJOB_RC=orphaned\nSTEP=complete-umbrella-leaf-{GAP}\n"),
            LEAF,
        )
        .is_err()
    );
    assert!(
        validate_orphaned_child_result(
            &format!("BGJOB_RC=orphaned\nSTEP=complete-umbrella-leaf-{LEAF}\nCHILD_ISSUE={GAP}\n"),
            LEAF,
        )
        .is_err()
    );
    assert!(
        validate_orphaned_child_result(
            &format!("BGJOB_RC=orphaned\nBGJOB_RC=0\nSTEP=complete-umbrella-leaf-{LEAF}\n"),
            LEAF,
        )
        .is_err()
    );

    let driver = format!(
        "BGJOB_RC=orphaned\nSTEP={RUN_LEAVES_STEP}\nNEXT_ACTION=verify\nCURRENT_LEAF={LEAF}\n"
    );
    assert!(validate_orphaned_child_result(&driver, LEAF).is_ok());
    assert!(
        validate_orphaned_child_result(
            &format!(
                "BGJOB_RC=orphaned\nSTEP={RUN_LEAVES_STEP}\nNEXT_ACTION=audit\nCURRENT_LEAF={LEAF}\n"
            ),
            LEAF,
        )
        .is_err()
    );
    assert!(
        validate_orphaned_child_result(
            &format!(
                "BGJOB_RC=orphaned\nSTEP={RUN_LEAVES_STEP}\nNEXT_ACTION=launch\nCURRENT_LEAF={GAP}\n"
            ),
            LEAF,
        )
        .is_err()
    );
}

#[derive(Default)]
struct FakeRunLeavesOperations {
    graphs: VecDeque<Result<GraphState, String>>,
    syncs: VecDeque<Result<(), String>>,
    children: VecDeque<ChildAttempt>,
    snapshots: usize,
    child_leaves: Vec<u64>,
    resets: Vec<u64>,
    results: Vec<RunLeavesEnvelope>,
}

impl RunLeavesOperations for FakeRunLeavesOperations {
    fn read_graph(&mut self) -> Result<GraphState, String> {
        self.graphs
            .pop_front()
            .unwrap_or_else(|| Err("unexpected graph read".to_owned()))
    }

    fn write_snapshot(&mut self, _graph: &GraphState) -> Result<(), String> {
        self.snapshots += 1;
        Ok(())
    }

    fn sync_main(&mut self) -> Result<(), String> {
        self.syncs
            .pop_front()
            .unwrap_or_else(|| Err("unexpected main synchronization".to_owned()))
    }

    fn run_child(&mut self, leaf: u64) -> ChildAttempt {
        self.child_leaves.push(leaf);
        self.children
            .pop_front()
            .unwrap_or_else(|| ChildAttempt::Failed("unexpected child launch".to_owned()))
    }

    fn reset_leaf(&mut self, leaf: u64) -> Result<(), String> {
        self.resets.push(leaf);
        Ok(())
    }

    fn write_result(&mut self, envelope: &RunLeavesEnvelope) -> Result<(), String> {
        self.results.push(envelope.clone());
        Ok(())
    }
}

fn driver_graph(leaves: &[(u64, GitHubIssueState, bool)]) -> GraphState {
    let parent = GitHubIssue {
        id: 400,
        number: UMBRELLA,
        title: String::from("[IMPLEMENTING] [UMBRELLA] Ship it"),
        body: String::from(PROPOSAL_BODY),
        state: GitHubIssueState::Open,
        state_reason: String::new(),
        url: String::from("https://github.com/o/r/issues/40"),
        author: String::from("author"),
        labels: Vec::new(),
        comments: 0,
        created_at: String::from(BEFORE),
        closed_at: String::new(),
        updated_at: String::from(BEFORE),
        is_pull_request: false,
    };
    GraphState {
        parent: parent.clone(),
        leaves: leaves
            .iter()
            .map(|(number, state, implementing)| {
                let lifecycle = if *state == GitHubIssueState::Closed {
                    "[DONE] "
                } else if *implementing {
                    "[IMPLEMENTING] "
                } else {
                    ""
                };
                LeafState {
                    issue: GitHubIssue {
                        id: number * 10,
                        number: *number,
                        title: format!("{lifecycle}[LEAF OF {UMBRELLA}] Leaf {number}"),
                        state: *state,
                        ..parent.clone()
                    },
                    open_blockers: Vec::new(),
                }
            })
            .collect(),
        open_orphan_blockers: Vec::new(),
    }
}

#[test]
fn run_leaves_verifies_and_selects_from_one_fresh_graph_per_iteration() {
    let mut operations = FakeRunLeavesOperations {
        graphs: VecDeque::from([
            Ok(driver_graph(&[
                (LEAF, GitHubIssueState::Open, false),
                (GAP, GitHubIssueState::Open, false),
            ])),
            Ok(driver_graph(&[
                (LEAF, GitHubIssueState::Closed, false),
                (GAP, GitHubIssueState::Open, false),
            ])),
            Ok(driver_graph(&[
                (LEAF, GitHubIssueState::Closed, false),
                (GAP, GitHubIssueState::Closed, false),
            ])),
        ]),
        syncs: VecDeque::from([Ok(()), Ok(()), Ok(()), Ok(())]),
        children: VecDeque::from([ChildAttempt::Complete, ChildAttempt::Complete]),
        ..FakeRunLeavesOperations::default()
    };

    assert_eq!(execute_run_leaves(&mut operations), Ok(2));
    assert!(operations.graphs.is_empty());
    assert!(operations.syncs.is_empty());
    assert_eq!(operations.snapshots, 3);
    assert_eq!(operations.child_leaves, vec![LEAF, GAP]);
    assert_eq!(
        operations.results,
        vec![
            RunLeavesEnvelope::Progress {
                action: "launch",
                leaf: LEAF,
                completed: 0,
            },
            RunLeavesEnvelope::Progress {
                action: "verify",
                leaf: LEAF,
                completed: 0,
            },
            RunLeavesEnvelope::Progress {
                action: "launch",
                leaf: GAP,
                completed: 1,
            },
            RunLeavesEnvelope::Progress {
                action: "verify",
                leaf: GAP,
                completed: 1,
            },
            RunLeavesEnvelope::Audit { completed: 2 },
        ]
    );
}

#[test]
fn run_leaves_stops_on_child_or_remote_verification_failure() {
    let mut child_failure = FakeRunLeavesOperations {
        graphs: VecDeque::from([Ok(driver_graph(&[(LEAF, GitHubIssueState::Open, false)]))]),
        syncs: VecDeque::from([Ok(())]),
        children: VecDeque::from([ChildAttempt::Failed("ship failed".to_owned())]),
        ..FakeRunLeavesOperations::default()
    };
    let failure = execute_run_leaves(&mut child_failure).expect_err("child failure");
    assert_eq!(failure.step, "run-child");
    assert_eq!(failure.leaf, Some(LEAF));
    assert_eq!(child_failure.snapshots, 1);

    let mut verification_failure = FakeRunLeavesOperations {
        graphs: VecDeque::from([
            Ok(driver_graph(&[(LEAF, GitHubIssueState::Open, false)])),
            Ok(driver_graph(&[(LEAF, GitHubIssueState::Open, true)])),
        ]),
        syncs: VecDeque::from([Ok(()), Ok(())]),
        children: VecDeque::from([ChildAttempt::Complete]),
        ..FakeRunLeavesOperations::default()
    };
    let failure = execute_run_leaves(&mut verification_failure)
        .expect_err("remote lifecycle must verify before another selection");
    assert_eq!(failure.step, "verify-child");
    assert_eq!(failure.leaf, Some(LEAF));
    assert_eq!(verification_failure.snapshots, 1);
    assert_eq!(verification_failure.child_leaves, vec![LEAF]);
}

#[test]
fn run_leaves_reports_the_exact_sync_step_before_launch() {
    let mut operations = FakeRunLeavesOperations {
        graphs: VecDeque::from([Ok(driver_graph(&[(LEAF, GitHubIssueState::Open, false)]))]),
        syncs: VecDeque::from([Err("working tree is dirty".to_owned())]),
        children: VecDeque::from([ChildAttempt::Complete]),
        ..FakeRunLeavesOperations::default()
    };

    let failure = execute_run_leaves(&mut operations).expect_err("sync failure");
    assert_eq!(failure.step, "sync-before-child");
    assert_eq!(failure.leaf, Some(LEAF));
    assert_eq!(failure.reason, "working tree is dirty");
    assert!(operations.child_leaves.is_empty());
    assert_eq!(
        operations.results.last(),
        Some(&RunLeavesEnvelope::Failure(failure))
    );
}

#[test]
fn run_leaves_retries_only_the_same_transient_leaf_and_resets_needs_design() {
    let mut transient = FakeRunLeavesOperations {
        graphs: VecDeque::from([
            Ok(driver_graph(&[(LEAF, GitHubIssueState::Open, false)])),
            Ok(driver_graph(&[(LEAF, GitHubIssueState::Closed, false)])),
        ]),
        syncs: VecDeque::from([Ok(()), Ok(()), Ok(()), Ok(())]),
        children: VecDeque::from([
            ChildAttempt::TransientApi("network one".to_owned()),
            ChildAttempt::TransientApi("network two".to_owned()),
            ChildAttempt::Complete,
        ]),
        ..FakeRunLeavesOperations::default()
    };
    assert_eq!(execute_run_leaves(&mut transient), Ok(1));
    assert_eq!(transient.child_leaves, vec![LEAF, LEAF, LEAF]);
    assert_eq!(transient.resets, vec![LEAF, LEAF]);
    assert!(transient.syncs.is_empty());

    let mut needs_design = FakeRunLeavesOperations {
        graphs: VecDeque::from([Ok(driver_graph(&[(LEAF, GitHubIssueState::Open, false)]))]),
        syncs: VecDeque::from([Ok(())]),
        children: VecDeque::from([ChildAttempt::NeedsDesign]),
        ..FakeRunLeavesOperations::default()
    };
    let failure = execute_run_leaves(&mut needs_design).expect_err("needs design");
    assert_eq!(failure.next_action, "needs-design");
    assert_eq!(failure.step, "run-child");
    assert_eq!(needs_design.resets, vec![LEAF]);
    assert_eq!(
        needs_design.results.last(),
        Some(&RunLeavesEnvelope::Failure(failure))
    );
}

#[test]
fn run_leaves_envelopes_and_child_results_are_exact() {
    let failure = RunLeavesFailure::failed("run-child", Some(LEAF), "first\nsecond");
    assert_eq!(failure.reason, "first second");
    assert_eq!(
        RunLeavesEnvelope::Failure(failure)
            .render()
            .expect("failure envelope"),
        "FAILED_LEAF=41\nFAILED_STEP=run-child\nFAILURE_REASON=first second\nNEXT_ACTION=failed\n"
    );

    let complete =
        format!("CHILD_STATUS=complete\nCHILD_ISSUE={LEAF}\nCHILD_ENVELOPE_COMPLETE=true\n");
    assert_eq!(
        classify_child_attempt(LEAF, Ok(()), Ok(complete)),
        ChildAttempt::Complete
    );
    let transient = format!(
        "CHILD_STATUS=failed\nCHILD_ISSUE={LEAF}\nCHILD_ENVELOPE_COMPLETE=false\nCHILD_FAILURE_CLASS={COMPLETE_UMBRELLA_CHILD_FAILURE_TRANSIENT_API}\n"
    );
    assert_eq!(
        classify_child_attempt(LEAF, Err("temporary API failure".to_owned()), Ok(transient),),
        ChildAttempt::TransientApi("temporary API failure".to_owned())
    );
}

#[test]
fn run_leaves_main_sync_fast_forwards_and_rejects_another_branch() {
    let repository = GitRepository::builder(GitFixture::Refs)
        .build()
        .expect("Git fixture");
    let remote = repository.workspace_root().join("remote.git");
    let remote_text = remote.to_str().expect("UTF-8 fixture path");
    for arguments in [
        vec!["init", "--quiet", "--bare", remote_text],
        vec!["remote", "add", "origin", remote_text],
        vec!["push", "--quiet", "origin", "main"],
    ] {
        let output = repository.git(arguments).expect("fixture Git command");
        assert!(output.success(), "fixture Git command failed: {output:?}");
    }
    repository
        .write("remote.txt", b"remote commit\n")
        .expect("remote fixture file");
    for arguments in [
        ["add", "--", "remote.txt"].as_slice(),
        ["commit", "--quiet", "-m", "remote"].as_slice(),
        ["push", "--quiet", "origin", "main"].as_slice(),
        ["reset", "--quiet", "--hard", "HEAD^"].as_slice(),
    ] {
        let output = repository.git(arguments).expect("fixture Git command");
        assert!(output.success(), "fixture Git command failed: {output:?}");
    }

    synchronize_main(repository.root()).expect("fast-forward main");
    let head = repository
        .git(["rev-parse", "HEAD"])
        .expect("local revision");
    let origin = repository
        .git(["rev-parse", "origin/main"])
        .expect("remote revision");
    assert_eq!(head.stdout, origin.stdout);

    let checkout = repository
        .git(["checkout", "--quiet", "topic"])
        .expect("topic checkout");
    assert!(checkout.success(), "topic checkout failed: {checkout:?}");
    assert!(
        synchronize_main(repository.root())
            .expect_err("non-main checkout")
            .contains("not on branch main")
    );
}

#[test]
fn transient_claude_api_envelopes_classify_from_terminal_reason_or_connectivity() {
    let api_error = parse_claude_envelope(
        r#"{"is_error":true,"terminal_reason":"api_error","result":"API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)"}"#,
    );
    assert!(is_transient_claude_api_error(&api_error));
    assert_eq!(api_error.terminal_reason, "api_error");
    assert!(api_error.is_error);

    let connectivity = parse_claude_envelope(
        r#"{"is_error":true,"result":"API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)"}"#,
    );
    assert!(is_transient_claude_api_error(&connectivity));

    let permanent = parse_claude_envelope(r#"{"is_error":true,"result":"policy refusal"}"#);
    assert!(!is_transient_claude_api_error(&permanent));

    let ok = parse_claude_envelope(
        "{\"result\":\"verified\\nCOMPLETE_UMBRELLA_CHILD_STATUS=complete\"}",
    );
    assert!(!is_transient_claude_api_error(&ok));
}

#[test]
fn expected_paths_and_leaf_files_fail_closed() {
    let directory = tempfile::tempdir().expect("temporary root");
    let root = temporary_root(directory.path(), "root").expect("trusted root");
    let file = directory.path().join("file");
    fs::write(&file, "content").expect("fixture");

    assert!(canonical_directory(&file, "directory").is_err());
    assert!(temporary_root(Path::new("relative"), "root").is_err());
    assert!(
        confine_session_path(
            Path::new("relative"),
            directory.path(),
            &root,
            PathIntent::Read,
            "file",
        )
        .is_err()
    );
    assert!(
        confine_session_path(
            directory.path(),
            directory.path(),
            &root,
            PathIntent::Read,
            "file",
        )
        .is_err()
    );

    let title_file = directory.path().join("title");
    let body_file = directory.path().join("body");
    fs::write(&title_file, "Close the gap\n").expect("title fixture");
    fs::write(&body_file, "").expect("empty body fixture");
    let arguments = GapFileArguments {
        root: directory.path().to_path_buf(),
        title_file,
        body_file: body_file.clone(),
    };
    assert!(read_expected_audit_leaf(UMBRELLA, &arguments).is_err());
    fs::write(&body_file, "Wrong umbrella opening\n").expect("body fixture");
    assert!(read_expected_audit_leaf(UMBRELLA, &arguments).is_err());
}

#[tokio::test]
async fn start_remote_applies_only_the_active_title_transition() {
    let original = issue_json(
        UMBRELLA,
        400,
        "[UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let active = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        AFTER,
    );
    let (client, server) = service(vec![
        // read_graph runnability pre-check (zero leaves -> audit-runnable).
        response(200, &original),
        response(200, "[]"),
        response(200, "[]"),
        // read_snapshot, then apply (read, PATCH, read-back).
        response(200, &original),
        response(200, &original),
        response(200, &active),
        response(200, &active),
    ]);

    start_remote(&client, &Cancellation::new(), &repository(), UMBRELLA)
        .await
        .expect("active transition");

    let requests = server.finish().expect("stub completed");
    assert_eq!(
        requests
            .iter()
            .filter(|request| request.method == "PATCH")
            .count(),
        1
    );
    let patch = requests
        .iter()
        .find(|request| request.method == "PATCH")
        .expect("one title PATCH");
    assert!(
        String::from_utf8_lossy(&patch.body.bytes).contains("[IMPLEMENTING] [UMBRELLA] Ship it")
    );
}

#[tokio::test]
async fn start_refuses_an_open_non_leaf_parent_blocker_without_renaming() {
    let original = issue_json(
        UMBRELLA,
        400,
        "[UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let leaf = issue_json(
        LEAF,
        410,
        "[LEAF OF 40] Implement it",
        &format!("{}\n\nWork remains.", umbrella_leaf_opening(UMBRELLA)),
        "open",
        BEFORE,
    );
    let (client, server) = service(vec![
        response(200, &original),
        response(200, refs(&[(LEAF, 410, "open")])),
        response(200, refs(&[(LEAF, 410, "open"), (GAP, 420, "open")])),
        response(200, &leaf),
        response(200, "[]"),
        response(200, "[]"),
    ]);

    let error = start_remote(&client, &Cancellation::new(), &repository(), UMBRELLA)
        .await
        .expect_err("open non-leaf parent blocker must refuse start");
    assert_eq!(
        error,
        "cannot start while open non-leaf parent blockers remain: 42"
    );
    let requests = server.finish().expect("stub completed");
    assert!(requests.iter().all(|request| request.method != "PATCH"));
}

#[tokio::test]
async fn start_refuses_a_deadlocked_umbrella_without_renaming() {
    let original = issue_json(
        UMBRELLA,
        400,
        "[UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let leaf = issue_json(
        LEAF,
        410,
        "[LEAF OF 40] Implement it",
        &format!("{}\n\nWork remains.", umbrella_leaf_opening(UMBRELLA)),
        "open",
        BEFORE,
    );
    let (client, server) = service(vec![
        response(200, &original),
        response(200, refs(&[(LEAF, 410, "open")])),
        response(200, refs(&[(LEAF, 410, "open")])),
        response(200, &leaf),
        response(200, "[]"),
        response(200, refs(&[(99, 990, "open")])),
    ]);

    let error = start_remote(&client, &Cancellation::new(), &repository(), UMBRELLA)
        .await
        .expect_err("a fully blocked leaf graph must refuse start");
    assert_eq!(
        error,
        "cannot start a deadlocked umbrella while every open leaf is blocked: 41"
    );
    let requests = server.finish().expect("stub completed");
    assert!(requests.iter().all(|request| request.method != "PATCH"));
}

#[tokio::test]
async fn reset_leaf_remote_strips_only_the_active_prefix() {
    let parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let body = format!("{}\n\nTask.", umbrella_leaf_opening(UMBRELLA));
    let active_leaf = issue_json(
        LEAF,
        410,
        "[IMPLEMENTING] [LEAF OF 40] Task",
        &body,
        "open",
        BEFORE,
    );
    let idle_leaf = issue_json(LEAF, 410, "[LEAF OF 40] Task", &body, "open", AFTER);
    let mut exchanges = open_graph(&parent, &active_leaf);
    exchanges.extend([
        response(200, &active_leaf),
        response(200, &active_leaf),
        response(200, &idle_leaf),
        response(200, &idle_leaf),
    ]);
    let (client, server) = service(exchanges);
    let arguments = LeafArguments {
        repository: String::from("o/r"),
        umbrella: UMBRELLA,
        leaf: LEAF,
    };

    reset_leaf_remote(&client, &Cancellation::new(), &repository(), &arguments)
        .await
        .expect("idle transition");

    let requests = server.finish().expect("stub completed");
    assert_eq!(
        requests
            .iter()
            .filter(|request| request.method == "PATCH")
            .count(),
        1
    );
}

#[tokio::test]
async fn reset_leaf_remote_is_idempotent_for_an_idle_leaf() {
    let parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let body = format!("{}\n\nTask.", umbrella_leaf_opening(UMBRELLA));
    let idle_leaf = issue_json(LEAF, 410, "[LEAF OF 40] Task", &body, "open", BEFORE);
    let (client, server) = service(open_graph(&parent, &idle_leaf));
    let arguments = LeafArguments {
        repository: String::from("o/r"),
        umbrella: UMBRELLA,
        leaf: LEAF,
    };

    reset_leaf_remote(&client, &Cancellation::new(), &repository(), &arguments)
        .await
        .expect("already idle");

    let requests = server.finish().expect("stub completed");
    assert!(requests.iter().all(|request| request.method != "PATCH"));
}

#[tokio::test]
async fn reset_leaf_remote_preserves_a_designed_leaf_for_design_reentry() {
    let parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let body = format!("{}\n\nTask.", umbrella_leaf_opening(UMBRELLA));
    let designed_leaf = issue_json(
        LEAF,
        410,
        "[DESIGNED] [LEAF OF 40] Task",
        &body,
        "open",
        BEFORE,
    );
    let (client, server) = service(open_graph(&parent, &designed_leaf));
    let arguments = LeafArguments {
        repository: String::from("o/r"),
        umbrella: UMBRELLA,
        leaf: LEAF,
    };

    reset_leaf_remote(&client, &Cancellation::new(), &repository(), &arguments)
        .await
        .expect("designed leaf remains design-admissible");

    let requests = server.finish().expect("stub completed");
    assert!(requests.iter().all(|request| request.method != "PATCH"));
}

#[tokio::test]
async fn attachment_is_idempotent_and_replays_both_native_edges_with_exact_read_back() {
    let parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let opening = umbrella_leaf_opening(UMBRELLA);
    let body = format!("{opening}\n\nClose the audited gap.");
    let leaf = issue_json(
        GAP,
        420,
        "[LEAF OF 40] Close the gap",
        &body,
        "open",
        BEFORE,
    );
    let leaf_ref = refs(&[(GAP, 420, "open")]);
    let parent_ref = json!({ "number": UMBRELLA, "id": 400, "state": "open" }).to_string();
    let (service, server) = service(attachment_exchanges(&parent, &leaf, &leaf_ref, &parent_ref));
    let arguments = LeafArguments {
        repository: String::from("o/r"),
        umbrella: UMBRELLA,
        leaf: GAP,
    };
    let expected = ExpectedAuditLeaf {
        remote_title: String::from("[LEAF OF 40] Close the gap"),
        body,
    };

    attach_leaf_remote(
        &service,
        &Cancellation::new(),
        &repository(),
        &arguments,
        &expected,
    )
    .await
    .expect("verified attachment");
    attach_leaf_remote(
        &service,
        &Cancellation::new(),
        &repository(),
        &arguments,
        &expected,
    )
    .await
    .expect("idempotent attachment");

    let requests = server.finish().expect("stub completed");
    assert_eq!(
        requests
            .iter()
            .filter(|request| request.method == "POST")
            .count(),
        2
    );
    assert!(
        requests
            .iter()
            .any(|request| request.path.ends_with("/sub_issues"))
    );
    assert!(
        requests
            .iter()
            .any(|request| request.path.ends_with("/dependencies/blocked_by"))
    );
}

#[tokio::test]
async fn attachment_stops_when_the_parent_finishes_between_edges() {
    let active_parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let done_parent = issue_json(
        UMBRELLA,
        400,
        "[DONE] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        AFTER,
    );
    let body = format!(
        "{}\n\nClose the audited gap.",
        umbrella_leaf_opening(UMBRELLA)
    );
    let leaf = issue_json(
        GAP,
        420,
        "[LEAF OF 40] Close the gap",
        &body,
        "open",
        BEFORE,
    );
    let leaf_ref = refs(&[(GAP, 420, "open")]);
    let (service, server) = service(vec![
        response(200, &active_parent),
        response(200, "[]"),
        response(200, &leaf),
        response(200, "[]"),
        response(404, "{}"),
        response(200, "[]"),
        response(201, "{}"),
        response(200, &leaf_ref),
        response(200, &done_parent),
    ]);
    let arguments = LeafArguments {
        repository: String::from("o/r"),
        umbrella: UMBRELLA,
        leaf: GAP,
    };
    let expected = ExpectedAuditLeaf {
        remote_title: String::from("[LEAF OF 40] Close the gap"),
        body,
    };

    assert!(
        attach_leaf_remote(
            &service,
            &Cancellation::new(),
            &repository(),
            &arguments,
            &expected,
        )
        .await
        .is_err()
    );

    let requests = server.finish().expect("stub completed");
    assert_eq!(
        requests
            .iter()
            .filter(|request| request.method == "POST")
            .count(),
        1
    );
    assert!(requests[6].path.ends_with("/sub_issues"));
}

#[tokio::test]
async fn finish_remote_proves_closed_leaves_and_ignores_closed_historical_extra_blockers() {
    let active_parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let done_parent = issue_json(
        UMBRELLA,
        400,
        "[DONE] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        AFTER,
    );
    let closed_parent = issue_json(
        UMBRELLA,
        400,
        "[DONE] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "closed",
        CLOSED_AT,
    );
    let leaf = issue_json(
        LEAF,
        410,
        "[DONE] [LEAF OF 40] Implement it",
        &format!("{}\n\nDone.", umbrella_leaf_opening(UMBRELLA)),
        "closed",
        BEFORE,
    );
    let parent_blockers = [(LEAF, 410, "closed"), (GAP, 420, "closed")];
    let mut exchanges = closed_graph_with_parent_blockers(&active_parent, &leaf, &parent_blockers);
    exchanges.extend([
        response(200, &active_parent),
        response(200, &active_parent),
        response(200, &done_parent),
        response(200, &done_parent),
    ]);
    exchanges.extend(closed_graph_with_parent_blockers(
        &done_parent,
        &leaf,
        &parent_blockers,
    ));
    exchanges.push(response(200, &closed_parent));
    exchanges.extend(closed_graph_with_parent_blockers(
        &closed_parent,
        &leaf,
        &parent_blockers,
    ));
    let (service, server) = service(exchanges);

    finish_remote(&service, &Cancellation::new(), &repository(), UMBRELLA)
        .await
        .expect("verified finish");

    let requests = server.finish().expect("stub completed");
    assert_eq!(
        requests
            .iter()
            .filter(|request| request.method == "PATCH")
            .count(),
        2
    );
    assert!(requests.iter().any(|request| {
        request.method == "PATCH"
            && String::from_utf8_lossy(&request.body.bytes).contains("completed")
    }));
}

#[tokio::test]
async fn finish_refuses_an_open_non_leaf_parent_blocker() {
    let active_parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let leaf = issue_json(
        LEAF,
        410,
        "[DONE] [LEAF OF 40] Implement it",
        &format!("{}\n\nDone.", umbrella_leaf_opening(UMBRELLA)),
        "closed",
        BEFORE,
    );
    let (client, server) = service(closed_graph_with_parent_blockers(
        &active_parent,
        &leaf,
        &[(LEAF, 410, "closed"), (GAP, 420, "open")],
    ));

    let error = finish_remote(&client, &Cancellation::new(), &repository(), UMBRELLA)
        .await
        .expect_err("open non-leaf parent blocker must refuse completion");
    assert_eq!(
        error,
        "cannot finish while open non-leaf parent blockers remain: 42"
    );
    let requests = server.finish().expect("stub completed");
    assert!(requests.iter().all(|request| request.method != "PATCH"));
}

#[tokio::test]
async fn next_graph_reports_an_open_non_leaf_parent_blocker_separately() {
    let parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let leaf = issue_json(
        LEAF,
        410,
        "[LEAF OF 40] Implement it",
        &format!("{}\n\nWork remains.", umbrella_leaf_opening(UMBRELLA)),
        "open",
        BEFORE,
    );
    let (client, server) = service(vec![
        response(200, &parent),
        response(200, refs(&[(LEAF, 410, "open")])),
        response(200, refs(&[(LEAF, 410, "open"), (GAP, 420, "open")])),
        response(200, &leaf),
        response(200, "[]"),
        response(200, "[]"),
    ]);

    let graph = read_graph(&client, &Cancellation::new(), &repository(), UMBRELLA)
        .await
        .expect("valid direct leaf with a separately reported parent blocker");
    assert_eq!(graph.open_orphan_blockers, vec![GAP]);
    let selection = select_complete_umbrella_leaf(
        &selection_leaves(&graph.leaves),
        &graph.open_orphan_blockers,
    );
    assert_eq!(
        next_action_fields(&selection),
        vec![
            ("NEXT_ACTION", "orphan-blocker".to_owned()),
            ("ORPHAN_BLOCKERS", "42".to_owned()),
        ]
    );
    server.join().expect("orphan graph stub completed");
}

#[tokio::test]
async fn next_excludes_closed_leaves_with_stale_or_arbitrary_titles() {
    let parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let stale_implementing = issue_json(
        LEAF,
        410,
        "[IMPLEMENTING] [LEAF OF 40] Already shipped",
        &format!("{}\n\nDone.", umbrella_leaf_opening(UMBRELLA)),
        "closed",
        BEFORE,
    );
    let arbitrary_closed = issue_json(
        GAP,
        420,
        "Finished without a lifecycle prefix",
        "Wrong first line\n\nStill closed.",
        "closed",
        BEFORE,
    );
    let open_leaf = issue_json(
        43,
        430,
        "[LEAF OF 40] Still open",
        &format!("{}\n\nWork remains.", umbrella_leaf_opening(UMBRELLA)),
        "open",
        BEFORE,
    );
    let (client, server) = service(vec![
        response(200, &parent),
        response(
            200,
            refs(&[
                (LEAF, 410, "closed"),
                (GAP, 420, "closed"),
                (43, 430, "open"),
            ]),
        ),
        response(
            200,
            refs(&[
                (LEAF, 410, "closed"),
                (GAP, 420, "closed"),
                (43, 430, "open"),
            ]),
        ),
        response(200, &stale_implementing),
        response(200, "[]"),
        response(200, &arbitrary_closed),
        response(200, "[]"),
        response(200, &open_leaf),
        response(200, "[]"),
        response(200, "[]"),
    ]);

    let graph = read_graph(&client, &Cancellation::new(), &repository(), UMBRELLA)
        .await
        .expect("closed title drift must not abort next enumeration");
    assert_eq!(graph.leaves.len(), 3);
    let selection = select_complete_umbrella_leaf(
        &selection_leaves(&graph.leaves),
        &graph.open_orphan_blockers,
    );
    assert_eq!(
        next_action_fields(&selection),
        vec![
            ("NEXT_ACTION", "launch".to_owned()),
            ("NEXT_LEAF", "43".to_owned()),
        ]
    );
    server
        .join()
        .expect("stale closed leaf graph stub completed");
}

#[tokio::test]
async fn graph_diagnostics_still_name_open_leaf_lifecycle_failures() {
    let parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let invalid_title = issue_json(
        LEAF,
        410,
        "[DONE] [LEAF OF 40] Still open",
        &format!("{}\n\nWork remains.", umbrella_leaf_opening(UMBRELLA)),
        "open",
        BEFORE,
    );
    let (client, server) = service(vec![
        response(200, &parent),
        response(200, refs(&[(LEAF, 410, "open")])),
        response(200, refs(&[(LEAF, 410, "open")])),
        response(200, &invalid_title),
    ]);
    let Err(error) = read_graph(&client, &Cancellation::new(), &repository(), UMBRELLA).await
    else {
        panic!("open leaf title must remain exact");
    };
    assert_eq!(
        error,
        "direct leaf #41 violates the exact lifecycle-title invariant"
    );
    server.join().expect("open title stub completed");

    let invalid_body = issue_json(
        LEAF,
        410,
        "[LEAF OF 40] Still open",
        "Wrong first line\n\nWork remains.",
        "open",
        BEFORE,
    );
    let (client, server) = service(vec![
        response(200, &parent),
        response(200, refs(&[(LEAF, 410, "open")])),
        response(200, refs(&[(LEAF, 410, "open")])),
        response(200, &invalid_body),
    ]);
    let Err(error) = read_graph(&client, &Cancellation::new(), &repository(), UMBRELLA).await
    else {
        panic!("open leaf body must retain the exact opening");
    };
    assert_eq!(
        error,
        "direct leaf #41 violates the exact first-line body invariant"
    );
    server.join().expect("open body stub completed");
}

#[tokio::test]
async fn finish_accepts_closed_leaves_with_stale_implementing_titles() {
    let active_parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let done_parent = issue_json(
        UMBRELLA,
        400,
        "[DONE] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        AFTER,
    );
    let closed_parent = issue_json(
        UMBRELLA,
        400,
        "[DONE] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "closed",
        CLOSED_AT,
    );
    let stale_leaf = issue_json(
        LEAF,
        410,
        "[IMPLEMENTING] [LEAF OF 40] Implement it",
        &format!("{}\n\nDone.", umbrella_leaf_opening(UMBRELLA)),
        "closed",
        BEFORE,
    );
    let mut exchanges = closed_graph(&active_parent, &stale_leaf);
    exchanges.extend([
        response(200, &active_parent),
        response(200, &active_parent),
        response(200, &done_parent),
        response(200, &done_parent),
    ]);
    exchanges.extend(closed_graph(&done_parent, &stale_leaf));
    exchanges.push(response(200, &closed_parent));
    exchanges.extend(closed_graph(&closed_parent, &stale_leaf));
    let (service, server) = service(exchanges);

    finish_remote(&service, &Cancellation::new(), &repository(), UMBRELLA)
        .await
        .expect("stale closed leaf titles must not block finish");

    let requests = server.finish().expect("stub completed");
    assert!(requests.iter().any(|request| {
        request.method == "PATCH"
            && String::from_utf8_lossy(&request.body.bytes).contains("completed")
    }));
}

#[tokio::test]
async fn child_verification_reads_the_fresh_closed_graph() {
    let parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let leaf = issue_json(
        LEAF,
        410,
        "[DONE] [LEAF OF 40] Implement it",
        &format!("{}\n\nDone.", umbrella_leaf_opening(UMBRELLA)),
        "closed",
        BEFORE,
    );
    let (service, server) = service(closed_graph(&parent, &leaf));
    let arguments = LeafArguments {
        repository: String::from("o/r"),
        umbrella: UMBRELLA,
        leaf: LEAF,
    };

    verify_child_remote(&service, &Cancellation::new(), &repository(), &arguments)
        .await
        .expect("verified child");
    server.join().expect("stub completed");
}

#[tokio::test]
async fn orphaned_child_recovery_accepts_an_exact_result_after_remote_completion() {
    let parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let leaf = issue_json(
        LEAF,
        410,
        "[DONE] [LEAF OF 40] Implement it",
        &format!("{}\n\nDone.", umbrella_leaf_opening(UMBRELLA)),
        "closed",
        BEFORE,
    );
    let (service, server) = service(closed_graph(&parent, &leaf));
    let arguments = LeafArguments {
        repository: String::from("o/r"),
        umbrella: UMBRELLA,
        leaf: LEAF,
    };
    let result = format!("BGJOB_RC=orphaned\nSTEP=complete-umbrella-leaf-{LEAF}\n");

    recover_orphaned_child_remote(
        &service,
        &Cancellation::new(),
        &repository(),
        &arguments,
        &result,
    )
    .await
    .expect("remote completion recovers the orphaned transport");
    server.join().expect("stub completed");
}

#[tokio::test]
async fn child_verification_still_requires_exact_done_title_on_the_shipped_leaf() {
    let parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let stale_leaf = issue_json(
        LEAF,
        410,
        "[IMPLEMENTING] [LEAF OF 40] Implement it",
        &format!("{}\n\nDone.", umbrella_leaf_opening(UMBRELLA)),
        "closed",
        BEFORE,
    );
    let (service, server) = service(closed_graph(&parent, &stale_leaf));
    let arguments = LeafArguments {
        repository: String::from("o/r"),
        umbrella: UMBRELLA,
        leaf: LEAF,
    };

    let error = verify_child_remote(&service, &Cancellation::new(), &repository(), &arguments)
        .await
        .expect_err("verify-child must keep the exact [DONE] assertion");
    assert_eq!(
        error,
        "child must be closed with the exact [DONE] leaf prefix"
    );
    server.join().expect("stale verify-child stub completed");
}

#[tokio::test]
async fn remote_graph_checks_reject_incomplete_or_nested_lifecycles() {
    let active_parent = issue_json(
        UMBRELLA,
        400,
        "[IMPLEMENTING] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let done_parent = issue_json(
        UMBRELLA,
        400,
        "[DONE] [UMBRELLA] Ship it",
        PROPOSAL_BODY,
        "closed",
        CLOSED_AT,
    );
    let open_leaf = issue_json(
        LEAF,
        410,
        "[LEAF OF 40] Implement it",
        &format!("{}\n\nWork remains.", umbrella_leaf_opening(UMBRELLA)),
        "open",
        BEFORE,
    );
    let closed_leaf = issue_json(
        LEAF,
        410,
        "[DONE] [LEAF OF 40] Implement it",
        &format!("{}\n\nDone.", umbrella_leaf_opening(UMBRELLA)),
        "closed",
        BEFORE,
    );

    let nested_child = issue_json(
        99,
        990,
        "[UMBRELLA] Nested child",
        PROPOSAL_BODY,
        "open",
        BEFORE,
    );
    let (client, server) = service(vec![
        response(200, &active_parent),
        response(200, refs(&[(99, 990, "open")])),
        response(200, refs(&[(99, 990, "open")])),
        response(200, &nested_child),
    ]);
    let Err(nested_error) =
        read_graph(&client, &Cancellation::new(), &repository(), UMBRELLA).await
    else {
        panic!("umbrella children must refuse");
    };
    assert_eq!(nested_error, "nested umbrellas are not supported");
    server.join().expect("nested graph stub completed");

    let (client, server) = service(vec![
        response(200, &active_parent),
        response(200, refs(&[(LEAF, 410, "open")])),
        response(200, "[]"),
    ]);
    assert!(
        read_graph(&client, &Cancellation::new(), &repository(), UMBRELLA,)
            .await
            .is_err()
    );
    server.join().expect("missing edge stub completed");

    let (client, server) = service(open_graph(&active_parent, &open_leaf));
    assert!(
        finish_remote(&client, &Cancellation::new(), &repository(), UMBRELLA,)
            .await
            .is_err()
    );
    server.join().expect("open leaf stub completed");

    let (client, server) = service(closed_graph(&done_parent, &closed_leaf));
    finish_remote(&client, &Cancellation::new(), &repository(), UMBRELLA)
        .await
        .expect("closed done graph is idempotent");
    server.join().expect("closed graph stub completed");

    let (client, server) = service(vec![
        response(200, &active_parent),
        response(200, "[]"),
        response(200, "[]"),
    ]);
    let arguments = LeafArguments {
        repository: String::from("o/r"),
        umbrella: UMBRELLA,
        leaf: GAP,
    };
    assert!(
        verify_child_remote(&client, &Cancellation::new(), &repository(), &arguments)
            .await
            .is_err()
    );
    server.join().expect("missing child stub completed");
}

#[test]
fn next_snapshot_covers_launch_audit_orphan_deadlock_and_inactive_refusal() {
    let directory = tempfile::tempdir().expect("temporary root");
    let parent = GitHubIssue {
        id: 400,
        number: UMBRELLA,
        title: String::from("[IMPLEMENTING] [UMBRELLA] Ship it"),
        body: String::from(PROPOSAL_BODY),
        state: GitHubIssueState::Open,
        state_reason: String::new(),
        url: String::from("https://github.com/o/r/issues/40"),
        author: String::from("author"),
        labels: Vec::new(),
        comments: 0,
        created_at: String::from(BEFORE),
        closed_at: String::new(),
        updated_at: String::from(BEFORE),
        is_pull_request: false,
    };
    let leaf = |number, state, open_blockers| LeafState {
        issue: GitHubIssue {
            number,
            state,
            title: format!("[LEAF OF 40] Leaf {number}"),
            ..parent.clone()
        },
        open_blockers,
    };
    let arguments = |name: &str| NextArguments {
        repository: String::from("o/r"),
        issue: UMBRELLA,
        output_root: directory.path().to_path_buf(),
        output: directory.path().join(name),
    };

    let mut active = leaf(42, GitHubIssueState::Open, Vec::new());
    active.issue.title = format!("{IMPLEMENTING_PREFIX}[LEAF OF 40] Leaf 42");
    let active_input = selection_leaves(&[active]);
    let active_selection = select_complete_umbrella_leaf(&active_input, &[]);
    assert_eq!(active_selection, CompleteUmbrellaNext::Deadlocked(vec![42]));
    assert_eq!(
        next_action_fields(&active_selection),
        vec![
            ("NEXT_ACTION", "deadlock".to_owned()),
            ("BLOCKED_LEAVES", "42".to_owned()),
        ]
    );

    emit_next(
        &arguments("launch.json"),
        &GraphState {
            parent: parent.clone(),
            leaves: vec![leaf(43, GitHubIssueState::Open, Vec::new())],
            open_orphan_blockers: Vec::new(),
        },
    )
    .expect("launch snapshot");
    emit_next(
        &arguments("audit.json"),
        &GraphState {
            parent: parent.clone(),
            leaves: Vec::new(),
            open_orphan_blockers: Vec::new(),
        },
    )
    .expect("audit snapshot");
    emit_next(
        &arguments("deadlock.json"),
        &GraphState {
            parent: parent.clone(),
            leaves: vec![leaf(44, GitHubIssueState::Open, vec![99])],
            open_orphan_blockers: Vec::new(),
        },
    )
    .expect("deadlock snapshot");
    emit_next(
        &arguments("orphan-blocker.json"),
        &GraphState {
            parent: parent.clone(),
            leaves: Vec::new(),
            open_orphan_blockers: vec![99],
        },
    )
    .expect("orphan-blocker snapshot");
    let mut inactive = parent;
    inactive.state = GitHubIssueState::Closed;
    assert!(
        emit_next(
            &arguments("inactive.json"),
            &GraphState {
                parent: inactive,
                leaves: Vec::new(),
                open_orphan_blockers: Vec::new(),
            },
        )
        .is_err()
    );

    let snapshot =
        fs::read_to_string(directory.path().join("launch.json")).expect("written snapshot");
    assert!(snapshot.contains("\"repository\": \"o/r\""));
    assert_eq!(join_numbers(&[3, 5, 8]), "3 5 8");
    assert_eq!(state_token(GitHubIssueState::All), "all");
}

#[test]
fn next_action_fields_preserve_valid_order_and_distinguish_orphan_blockers() {
    assert_eq!(
        next_action_fields(&CompleteUmbrellaNext::Launch(41)),
        vec![
            ("NEXT_ACTION", "launch".to_owned()),
            ("NEXT_LEAF", "41".to_owned()),
        ]
    );
    assert_eq!(
        next_action_fields(&CompleteUmbrellaNext::Audit),
        vec![("NEXT_ACTION", "audit".to_owned())]
    );
    assert_eq!(
        next_action_fields(&CompleteUmbrellaNext::Deadlocked(vec![43, 44])),
        vec![
            ("NEXT_ACTION", "deadlock".to_owned()),
            ("BLOCKED_LEAVES", "43 44".to_owned()),
        ]
    );
    assert_eq!(
        next_action_fields(&CompleteUmbrellaNext::OrphanBlocked(vec![42, 99])),
        vec![
            ("NEXT_ACTION", "orphan-blocker".to_owned()),
            ("ORPHAN_BLOCKERS", "42 99".to_owned()),
        ]
    );
}

#[cfg(unix)]
#[test]
fn expected_files_reject_symlinks_and_oversize_content() {
    use std::os::unix::fs::symlink;

    let directory = tempfile::tempdir().expect("temporary root");
    let root = temporary_root(directory.path(), "root").expect("trusted root");
    let real = directory.path().join("real.txt");
    fs::write(&real, "four").expect("fixture");
    let link = directory.path().join("link.txt");
    symlink(&real, &link).expect("symlink fixture");
    let real_directory = directory.path().join("real-directory");
    fs::create_dir(&real_directory).expect("directory fixture");
    fs::write(real_directory.join("nested.txt"), "four").expect("nested fixture");
    let linked_directory = directory.path().join("linked-directory");
    symlink(&real_directory, &linked_directory).expect("directory symlink fixture");
    let nested_link = linked_directory.join("nested.txt");

    assert!(read_expected_file(&link, directory.path(), &root, "file", 8).is_err());
    assert!(read_expected_file(&nested_link, directory.path(), &root, "file", 8).is_err());
    assert!(write_private_file(&link, "changed", directory.path(), &root).is_err());
    assert!(read_expected_file(&real, directory.path(), &root, "file", 3).is_err());
    assert_eq!(
        read_expected_file(&real, directory.path(), &root, "file", 4)
            .expect("bounded regular file"),
        "four"
    );
}
