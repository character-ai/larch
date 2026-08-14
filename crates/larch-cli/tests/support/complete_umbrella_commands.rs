use super::*;
use larch_adapters::github::OctocrabGitHubService;
use larch_test_support::{IssueServiceExchange, IssueServiceStub};
use serde_json::{Value, json};

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
        response(404, "{}"),
        response(200, refs(&[(LEAF, 410, "closed")])),
        response(200, refs(parent_blockers)),
        response(200, leaf),
        response(200, "[]"),
    ]
}

fn open_graph(parent: &str, leaf: &str) -> Vec<IssueServiceExchange> {
    vec![
        response(200, parent),
        response(404, "{}"),
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
        response(404, "{}"),
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
        response(404, "{}"),
        response(200, leaf_ref),
        response(200, leaf_ref),
        response(200, leaf),
        response(200, "[]"),
        response(200, "[]"),
        response(200, leaf_ref),
        response(200, parent),
        response(404, "{}"),
        response(200, leaf),
        response(200, "[]"),
        response(200, parent_ref),
        response(200, leaf_ref),
        response(200, parent),
        response(200, leaf_ref),
        response(200, parent),
        response(404, "{}"),
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
fn child_terminal_status_accepts_only_bounded_success_markers() {
    assert_eq!(
        child_terminal_status("summary\nCOMPLETE_UMBRELLA_CHILD_STATUS=complete\n"),
        Some(ChildResultStatus::Complete)
    );
    assert_eq!(
        child_terminal_status(
            "summary\nCOMPLETE_UMBRELLA_CHILD_STATUS=needs-orchestrator-finalize\n"
        ),
        Some(ChildResultStatus::NeedsOrchestratorFinalize)
    );
    assert_eq!(
        ChildResultStatus::NeedsOrchestratorFinalize.value(),
        "needs-orchestrator-finalize"
    );
    assert!(ChildResultStatus::NeedsOrchestratorFinalize.envelope_complete());
    assert!(!ChildResultStatus::Failed.envelope_complete());
    assert_eq!(
        child_terminal_status("COMPLETE_UMBRELLA_CHILD_STATUS=failed\n"),
        None
    );
    assert_eq!(child_terminal_status("summary\n"), None);
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
        response(200, &original),
        response(404, "{}"),
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
    assert!(
        String::from_utf8_lossy(&requests[4].body.bytes)
            .contains("[IMPLEMENTING] [UMBRELLA] Ship it")
    );
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
        response(404, "{}"),
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
    assert!(String::from_utf8_lossy(&requests[16].body.bytes).contains("completed"));
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
        response(404, "{}"),
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
        &graph
            .leaves
            .iter()
            .map(|leaf| CompleteUmbrellaLeaf {
                number: leaf.issue.number,
                open: leaf.issue.state == GitHubIssueState::Open,
                open_blockers: leaf.open_blockers.clone(),
            })
            .collect::<Vec<_>>(),
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
async fn graph_diagnostics_name_closed_leaf_and_failed_lifecycle_invariant() {
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
        "[IMPLEMENTING] [LEAF OF 40] Implement it",
        &format!("{}\n\nDone.", umbrella_leaf_opening(UMBRELLA)),
        "closed",
        BEFORE,
    );
    let (client, server) = service(vec![
        response(200, &parent),
        response(404, "{}"),
        response(200, refs(&[(LEAF, 410, "closed")])),
        response(200, refs(&[(LEAF, 410, "closed")])),
        response(200, &invalid_title),
    ]);
    let Err(error) = read_graph(&client, &Cancellation::new(), &repository(), UMBRELLA).await
    else {
        panic!("closed leaf title must remain exact");
    };
    assert_eq!(
        error,
        "direct leaf #41 is closed without the exact [DONE] lifecycle title"
    );
    server.join().expect("title stub completed");

    let invalid_body = issue_json(
        LEAF,
        410,
        "[DONE] [LEAF OF 40] Implement it",
        "Wrong first line\n\nDone.",
        "closed",
        BEFORE,
    );
    let (client, server) = service(vec![
        response(200, &parent),
        response(404, "{}"),
        response(200, refs(&[(LEAF, 410, "closed")])),
        response(200, refs(&[(LEAF, 410, "closed")])),
        response(200, &invalid_body),
    ]);
    let Err(error) = read_graph(&client, &Cancellation::new(), &repository(), UMBRELLA).await
    else {
        panic!("closed leaf body must retain the exact opening");
    };
    assert_eq!(
        error,
        "direct leaf #41 violates the exact first-line body invariant"
    );
    server.join().expect("body stub completed");
}

#[tokio::test]
async fn finish_refuses_a_closed_implementing_leaf_before_mutating_the_parent() {
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
    let (client, server) = service(vec![
        response(200, &parent),
        response(404, "{}"),
        response(200, refs(&[(LEAF, 410, "closed")])),
        response(200, refs(&[(LEAF, 410, "closed")])),
        response(200, &stale_leaf),
    ]);

    let error = finish_remote(&client, &Cancellation::new(), &repository(), UMBRELLA)
        .await
        .expect_err("terminal title drift must stop completion");
    assert_eq!(
        error,
        "direct leaf #41 is closed without the exact [DONE] lifecycle title"
    );
    server
        .join()
        .expect("completion stopped before a parent mutation request");
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

    let (client, server) = service(vec![
        response(200, &active_parent),
        response(
            200,
            json!({ "number": 1, "id": 10, "state": "open" }).to_string(),
        ),
    ]);
    assert!(
        read_graph(&client, &Cancellation::new(), &repository(), UMBRELLA,)
            .await
            .is_err()
    );
    server.join().expect("nested graph stub completed");

    let (client, server) = service(vec![
        response(200, &active_parent),
        response(404, "{}"),
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
        response(404, "{}"),
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
