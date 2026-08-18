//! Black-box parity tests for the four `debate` publication verbs.
//!
//! GitHub reads and writes run against a loopback-only typed service stub, so
//! these tests never acquire a credential or touch the network. They pin the
//! exact stdout envelope bytes, the written artifact bytes, the exit-code
//! classes, and the GitHub title-transition and comment-verify side effects
//! against the fixtures ported from the retired `test_publication.py`.

#[cfg(test)]
mod publication_tests {
    use super::super::{
        error_envelope, run_comment_verify, run_issue_prepare, run_proposal_link,
        run_title_transition, success_envelope,
    };
    use crate::github_service::with_test_github_service;
    use larch_adapters::github::OctocrabGitHubService;
    use larch_test_support::{IssueServiceExchange, IssueServiceStub};
    use serde_json::{Value, json};
    use std::ffi::OsString;
    use std::fs;
    use std::path::Path;
    use std::sync::Arc;
    use tempfile::TempDir;

    const ORIGINAL_TITLE: &str = "Choose a queue design";
    const PREPARED_AT: &str = "2026-08-05T12:00:00Z";

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn issue_json(title: &str, body: &str, state: &str, updated_at: &str) -> String {
        let mut value: Value = serde_json::from_str(include_str!(
            "../../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("valid issue fixture");
        value["id"] = json!(170);
        value["number"] = json!(17);
        value["title"] = json!(title);
        value["body"] = json!(body);
        value["state"] = json!(state);
        value["labels"] = json!([]);
        value["updated_at"] = json!(updated_at);
        value["url"] = json!("https://api.github.com/repos/owner/repo/issues/17");
        value["repository_url"] = json!("https://api.github.com/repos/owner/repo");
        value["html_url"] = json!("https://github.com/owner/repo/issues/17");
        value.to_string()
    }

    fn issue_exchange(
        title: &str,
        body: &str,
        state: &str,
        updated_at: &str,
    ) -> IssueServiceExchange {
        IssueServiceExchange::any_json(200, issue_json(title, body, state, updated_at))
            .expect("valid issue response")
    }

    fn comment_json(id: u64, body: &str) -> Value {
        let user = serde_json::from_str::<Value>(&issue_json("T", "B", "open", PREPARED_AT))
            .expect("issue fixture")["user"]
            .clone();
        json!({
            "id": id,
            "node_id": format!("C_{id}"),
            "url": format!("https://api.github.com/repos/owner/repo/issues/comments/{id}"),
            "html_url": format!("https://github.com/owner/repo/issues/17#issuecomment-{id}"),
            "body": body,
            "user": user,
            "created_at": PREPARED_AT,
            "updated_at": PREPARED_AT,
        })
    }

    fn comments_exchange(comments: &Value) -> IssueServiceExchange {
        IssueServiceExchange::any_json(200, comments.to_string()).expect("valid comments response")
    }

    fn service(
        exchanges: Vec<IssueServiceExchange>,
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

    fn seed_metadata(root: &Path) {
        let text = concat!(
            "{\"debated_title\":\"[DEBATED] Choose a queue design\",",
            "\"debating_title\":\"[DEBATING] Choose a queue design\",",
            "\"issue\":\"17\",",
            "\"issue_url\":\"https://github.com/owner/repo/issues/17\",",
            "\"original_title\":\"Choose a queue design\",",
            "\"prepared_updated_at\":\"2026-08-05T12:00:00Z\",",
            "\"repository\":\"owner/repo\"}\n",
        );
        fs::write(root.join("debate-source.json"), text).expect("seed metadata");
    }

    #[test]
    fn issue_prepare_writes_sorted_metadata_and_bounded_subject() {
        let root = TempDir::new().expect("tempdir");
        let (factory, server) = service(vec![issue_exchange(
            ORIGINAL_TITLE,
            "Compare bounded and unbounded queues.",
            "open",
            PREPARED_AT,
        )]);
        let prepared = with_test_github_service(factory, || {
            run_issue_prepare(&arguments(&[
                "--debate-tmpdir",
                &root.path().to_string_lossy(),
                "--repo",
                "owner/repo",
                "--issue",
                "17",
            ]))
        })
        .expect("issue-prepare succeeds");
        assert!(server.finish().expect("stub finished").len() == 1);

        assert_eq!(
            prepared.metadata.debating_title,
            "[DEBATING] Choose a queue design"
        );
        assert_eq!(
            prepared.metadata.debated_title,
            "[DEBATED] Choose a queue design"
        );

        let metadata_bytes =
            fs::read_to_string(root.path().join("debate-source.json")).expect("read metadata");
        assert_eq!(
            metadata_bytes,
            concat!(
                "{\"debated_title\":\"[DEBATED] Choose a queue design\",",
                "\"debating_title\":\"[DEBATING] Choose a queue design\",",
                "\"issue\":\"17\",",
                "\"issue_url\":\"https://github.com/owner/repo/issues/17\",",
                "\"original_title\":\"Choose a queue design\",",
                "\"prepared_updated_at\":\"2026-08-05T12:00:00Z\",",
                "\"repository\":\"owner/repo\"}\n",
            )
        );

        let subject =
            fs::read_to_string(root.path().join("debate-subject.md")).expect("read subject");
        assert!(subject.starts_with("# Debate subject\n"));
        assert!(subject.contains("Compare bounded and unbounded queues."));

        let expected_envelope = format!(
            concat!(
                "{{\"error_class\":null,\"metadata_path\":\"{mp}\",\"ok\":true,",
                "\"operation\":\"issue-prepare\",\"source_issue\":\"17\",",
                "\"source_url\":\"https://github.com/owner/repo/issues/17\",",
                "\"subject_path\":\"{sp}\"}}"
            ),
            mp = prepared.metadata_path.to_string_lossy(),
            sp = prepared.subject_path.to_string_lossy(),
        );
        let envelope = success_envelope(
            "issue-prepare",
            vec![
                (
                    "metadata_path",
                    Value::String(prepared.metadata_path.to_string_lossy().into_owned()),
                ),
                (
                    "subject_path",
                    Value::String(prepared.subject_path.to_string_lossy().into_owned()),
                ),
                (
                    "source_issue",
                    Value::String(prepared.metadata.issue.clone()),
                ),
                (
                    "source_url",
                    Value::String(prepared.metadata.issue_url.clone()),
                ),
            ],
        );
        assert_eq!(envelope, expected_envelope);
    }

    #[test]
    fn issue_prepare_refuses_a_closed_source() {
        let root = TempDir::new().expect("tempdir");
        let (factory, _server) = service(vec![issue_exchange(
            ORIGINAL_TITLE,
            "Body.",
            "closed",
            PREPARED_AT,
        )]);
        let refused = with_test_github_service(factory, || {
            run_issue_prepare(&arguments(&[
                "--debate-tmpdir",
                &root.path().to_string_lossy(),
                "--repo",
                "owner/repo",
                "--issue",
                "17",
            ]))
        });
        assert!(refused.is_err());
    }

    #[test]
    fn issue_prepare_refuses_a_lifecycle_owned_title() {
        let root = TempDir::new().expect("tempdir");
        let (factory, _server) = service(vec![issue_exchange(
            "[DEBATING] busy",
            "Body.",
            "open",
            PREPARED_AT,
        )]);
        let refused = with_test_github_service(factory, || {
            run_issue_prepare(&arguments(&[
                "--debate-tmpdir",
                &root.path().to_string_lossy(),
                "--repo",
                "owner/repo",
                "--issue",
                "17",
            ]))
        });
        assert!(refused.is_err());
    }

    #[test]
    fn title_transition_start_applies_the_debating_title() {
        let root = TempDir::new().expect("tempdir");
        seed_metadata(root.path());
        let debating = "[DEBATING] Choose a queue design";
        let after = "2026-08-05T12:00:01Z";
        let (factory, server) = service(vec![
            issue_exchange(ORIGINAL_TITLE, "Body.", "open", PREPARED_AT),
            issue_exchange(ORIGINAL_TITLE, "Body.", "open", PREPARED_AT),
            issue_exchange(debating, "Body.", "open", after),
            issue_exchange(debating, "Body.", "open", after),
        ]);
        let outcome = with_test_github_service(factory, || {
            run_title_transition(&arguments(&[
                "--debate-tmpdir",
                &root.path().to_string_lossy(),
                "--mode",
                "start",
            ]))
        })
        .expect("start transition succeeds");
        assert_eq!(outcome, (true, true, after.to_owned()));
        assert_eq!(server.finish().expect("stub finished").len(), 4);

        let envelope = success_envelope(
            "title-transition",
            vec![
                ("changed", Value::Bool(true)),
                ("owned", Value::Bool(true)),
                ("updated_at", Value::String(after.to_owned())),
            ],
        );
        assert_eq!(
            envelope,
            format!(
                "{{\"changed\":true,\"error_class\":null,\"ok\":true,\
                 \"operation\":\"title-transition\",\"owned\":true,\
                 \"updated_at\":\"{after}\"}}"
            )
        );
    }

    #[test]
    fn title_transition_restore_skips_a_foreign_title() {
        let root = TempDir::new().expect("tempdir");
        seed_metadata(root.path());
        let (factory, server) = service(vec![issue_exchange(
            "Operator-owned replacement",
            "Body.",
            "open",
            "2026-08-05T12:00:02Z",
        )]);
        let outcome = with_test_github_service(factory, || {
            run_title_transition(&arguments(&[
                "--debate-tmpdir",
                &root.path().to_string_lossy(),
                "--mode",
                "restore",
            ]))
        })
        .expect("restore transition succeeds");
        assert_eq!(outcome, (false, false, "2026-08-05T12:00:02Z".to_owned()));
        assert_eq!(server.finish().expect("stub finished").len(), 1);
    }

    #[test]
    fn proposal_link_appends_the_source_backlink() {
        let root = TempDir::new().expect("tempdir");
        seed_metadata(root.path());
        let body_path = root.path().join("proposal-body.md");
        fs::write(&body_path, "Use a bounded queue.\n").expect("write body");

        let artifact = run_proposal_link(&arguments(&[
            "--debate-tmpdir",
            &root.path().to_string_lossy(),
            "--body-file",
            &body_path.to_string_lossy(),
        ]))
        .expect("proposal-link succeeds");

        let linked = fs::read_to_string(&artifact).expect("read linked body");
        assert!(linked.starts_with("Use a bounded queue.\n"));
        assert!(linked.contains("Source: [#17](https://github.com/owner/repo/issues/17)"));
    }

    #[test]
    fn proposal_link_rejects_a_noncanonical_body() {
        let root = TempDir::new().expect("tempdir");
        seed_metadata(root.path());
        let other = root.path().join("other.md");
        fs::write(&other, "Unverified body.\n").expect("write other");

        let refused = run_proposal_link(&arguments(&[
            "--debate-tmpdir",
            &root.path().to_string_lossy(),
            "--body-file",
            &other.to_string_lossy(),
        ]));
        assert!(refused.is_err());
    }

    #[test]
    fn comment_verify_accepts_an_exact_fresh_readback() {
        let root = TempDir::new().expect("tempdir");
        seed_metadata(root.path());
        let marker = "<!-- larch:debate-aborted runid=test-run -->";
        let content_path = root.path().join("aborted-comment.md");
        fs::write(
            &content_path,
            "The debate ended before proposal publication. No outcome was adopted.\n",
        )
        .expect("write content");
        let body = format!(
            "{marker}\n\nThe debate ended before proposal publication. No outcome was adopted."
        );
        let (factory, server) = service(vec![comments_exchange(&json!([comment_json(91, &body)]))]);

        let comment_id = with_test_github_service(factory, || {
            run_comment_verify(&arguments(&[
                "--debate-tmpdir",
                &root.path().to_string_lossy(),
                "--marker",
                marker,
                "--content-file",
                &content_path.to_string_lossy(),
            ]))
        })
        .expect("comment-verify succeeds");
        assert_eq!(comment_id, "91");
        assert_eq!(server.finish().expect("stub finished").len(), 1);
    }

    #[test]
    fn comment_verify_rejects_a_mismatched_body() {
        let root = TempDir::new().expect("tempdir");
        seed_metadata(root.path());
        let marker = "<!-- larch:debate-proposal runid=test-run -->";
        let content_path = root.path().join("proposal-comment.md");
        fs::write(&content_path, "Proposal: #18\n").expect("write content");
        let (factory, _server) = service(vec![comments_exchange(&json!([comment_json(
            92,
            &format!("{marker}\n\nforeign")
        )]))]);

        let refused = with_test_github_service(factory, || {
            run_comment_verify(&arguments(&[
                "--debate-tmpdir",
                &root.path().to_string_lossy(),
                "--marker",
                marker,
                "--content-file",
                &content_path.to_string_lossy(),
            ]))
        });
        assert!(refused.is_err());
    }

    #[test]
    fn usage_errors_emit_the_per_verb_error_envelope() {
        assert!(run_issue_prepare(&[]).is_err());
        assert!(run_title_transition(&[]).is_err());
        assert!(run_proposal_link(&[]).is_err());
        assert!(run_comment_verify(&[]).is_err());

        assert_eq!(
            error_envelope("issue-prepare", "validation"),
            "{\"error_class\":\"validation\",\"ok\":false,\"operation\":\"issue-prepare\"}"
        );
        assert_eq!(
            error_envelope("title-transition", "mutation"),
            "{\"error_class\":\"mutation\",\"ok\":false,\"operation\":\"title-transition\"}"
        );
        assert_eq!(
            error_envelope("proposal-link", "validation"),
            "{\"error_class\":\"validation\",\"ok\":false,\"operation\":\"proposal-link\"}"
        );
        assert_eq!(
            error_envelope("comment-verify", "postcondition"),
            "{\"error_class\":\"postcondition\",\"ok\":false,\"operation\":\"comment-verify\"}"
        );
    }
}
