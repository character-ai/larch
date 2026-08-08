//! In-process coverage for the `/deps` driver against a gateway double.
//!
//! The live gateway is the only thing these tests replace: every ordering,
//! refusal, and accounting decision below is the one production takes.

#[cfg(test)]
mod deps_audit_tests {
    use std::{
        cell::RefCell,
        collections::{BTreeMap, BTreeSet},
        fs,
    };

    use larch_core::{DepsLiveIssue, deps_pretty_json};
    use serde_json::{Value, json};
    use tempfile::TempDir;

    use super::super::{
        ApplyScope, DepsGateway, DepsOpenIssue, DepsOrigin, DepsReadFailure, absolute, apply,
        body_mutation_request, edge_numbers, explicit_refs, fetch, live_state, load_apply_plan,
        load_json, open_rows_from, plan as plan_verb, read_failure, refresh_dependency_graph,
        resolve_machine_fetch, resolve_repo, run_apply, run_fetch, run_plan, run_resolve_repo,
        validated_proposals, write_proposals,
    };
    use larch_core::{
        GitHubIssue, GitHubIssueState, GitHubLabel, GitHubOperationError, GitHubOperationErrorKind,
        GitHubRepositoryRef, IssueMutationField, IssueMutationSnapshot,
    };
    use std::{ffi::OsString, process::ExitCode};

    /// One scripted gateway: it records every call and answers from its tables.
    #[derive(Default)]
    struct FakeGateway {
        origin: String,
        open: Option<Vec<DepsOpenIssue>>,
        open_failure: Option<DepsReadFailure>,
        comments: BTreeMap<u64, Result<Vec<(u64, String)>, String>>,
        dependencies: BTreeMap<(u64, bool), Result<Vec<u64>, String>>,
        live: BTreeMap<u64, DepsLiveIssue>,
        rewrite_failures: BTreeSet<u64>,
        close_failures: BTreeSet<u64>,
        edge_failures: BTreeSet<(u64, u64)>,
        calls: RefCell<Vec<String>>,
    }

    impl FakeGateway {
        fn record(&self, call: String) {
            self.calls.borrow_mut().push(call);
        }

        fn calls(&self) -> Vec<String> {
            self.calls.borrow().clone()
        }
    }

    impl DepsGateway for FakeGateway {
        fn origin_slug(&self) -> String {
            self.origin.clone()
        }

        fn open_issues(&self, _repo: &str) -> Result<Vec<DepsOpenIssue>, DepsReadFailure> {
            self.record("open_issues".to_owned());
            match (&self.open_failure, &self.open) {
                (Some(failure), _) => Err(failure.clone()),
                (None, Some(rows)) => Ok(rows.clone()),
                (None, None) => Ok(Vec::new()),
            }
        }

        fn comments(&self, _repo: &str, issue: u64) -> Result<Vec<(u64, String)>, String> {
            self.record(format!("comments {issue}"));
            self.comments.get(&issue).cloned().unwrap_or(Ok(Vec::new()))
        }

        fn dependencies(
            &self,
            _repo: &str,
            issue: u64,
            blocking: bool,
        ) -> Result<Vec<u64>, String> {
            self.record(format!("dependencies {issue} {blocking}"));
            self.dependencies
                .get(&(issue, blocking))
                .cloned()
                .unwrap_or(Ok(Vec::new()))
        }

        fn live_issue(&self, _repo: &str, issue: u64) -> Option<DepsLiveIssue> {
            self.record(format!("live {issue}"));
            self.live.get(&issue).cloned()
        }

        fn rewrite_body(&self, _repo: &str, issue: u64, body: &str) -> Result<(), String> {
            self.record(format!("rewrite {issue} {body}"));
            if self.rewrite_failures.contains(&issue) {
                return Err("rewrite refused".to_owned());
            }
            Ok(())
        }

        fn close_issue(&self, _repo: &str, issue: u64) -> Result<(), String> {
            self.record(format!("close {issue}"));
            if self.close_failures.contains(&issue) {
                return Err("close refused".to_owned());
            }
            Ok(())
        }

        fn add_blocked_by(&self, _repo: &str, client: u64, blocker: u64) -> Result<(), String> {
            self.record(format!("edge {client} {blocker}"));
            if self.edge_failures.contains(&(client, blocker)) {
                return Err("edge refused".to_owned());
            }
            Ok(())
        }
    }

    struct FakeOrigin {
        origin: &'static str,
        ambient: Option<&'static str>,
    }

    impl DepsOrigin for FakeOrigin {
        fn origin_slug(&self) -> String {
            self.origin.to_owned()
        }

        fn ambient_repo(&self) -> Option<String> {
            self.ambient.map(str::to_owned)
        }
    }

    fn open_issue(number: u64, title: &str, body: &str) -> DepsOpenIssue {
        DepsOpenIssue {
            number,
            title: title.to_owned(),
            body: body.to_owned(),
            labels: vec!["bug".to_owned()],
        }
    }

    fn live(title: &str, state: &str) -> DepsLiveIssue {
        DepsLiveIssue {
            title: title.to_owned(),
            state: state.to_owned(),
        }
    }

    fn exit_code(code: std::process::ExitCode) -> String {
        format!("{code:?}")
    }

    /// Write one snapshot pair and return `(fetch path, directory)`.
    fn snapshot(directory: &TempDir, repo: &str, issues: &Value, existing: &Value) -> String {
        let machine = directory.path().join("fetch-machine.json");
        fs::write(
            &machine,
            deps_pretty_json(&json!({"status": "ok", "repo": repo, "issues": issues})),
        )
        .expect("write machine snapshot");
        let fetch = directory.path().join("fetch.json");
        fs::write(
            &fetch,
            deps_pretty_json(&json!({
                "status": "ok",
                "repo": repo,
                "existing_edges": existing,
                "warnings": [],
                "machine_fetch_file": machine.to_string_lossy(),
            })),
        )
        .expect("write operator snapshot");
        fetch.to_string_lossy().into_owned()
    }

    // ------------------------------------------------------------ resolve-repo

    #[test]
    fn resolve_repo_reports_the_slug_and_whether_origin_agrees() {
        let ambient = FakeOrigin {
            origin: "o/r",
            ambient: Some("o/r"),
        };
        assert_eq!(
            exit_code(run_resolve_repo("", &ambient)),
            exit_code(std::process::ExitCode::SUCCESS)
        );
        // An explicit slug that is not the checkout's origin still resolves.
        assert_eq!(
            exit_code(run_resolve_repo("other/repo", &ambient)),
            exit_code(std::process::ExitCode::SUCCESS)
        );
        // An unusable explicit slug and an unresolvable ambient one both refuse.
        assert_eq!(
            exit_code(run_resolve_repo("../escape", &ambient)),
            exit_code(std::process::ExitCode::from(1))
        );
        let unresolvable = FakeOrigin {
            origin: "",
            ambient: None,
        };
        assert_eq!(
            exit_code(run_resolve_repo("", &unresolvable)),
            exit_code(std::process::ExitCode::from(1))
        );
    }

    // ------------------------------------------------------------------- fetch

    #[test]
    fn fetch_composes_three_artifacts_and_records_every_read_failure() {
        let directory = TempDir::new().expect("temp directory");
        let output = directory.path().join("out").join("fetch.json");
        let gateway = FakeGateway {
            open: Some(vec![
                open_issue(7, "plain", "Blocked by #9"),
                open_issue(9, "[DESIGNED] owned", ""),
            ]),
            comments: BTreeMap::from([
                (7, Ok(vec![(42, "note".to_owned())])),
                (9, Err("comments unavailable".to_owned())),
            ]),
            dependencies: BTreeMap::from([
                ((7, false), Ok(vec![9, 7])),
                ((9, true), Err("blocking unavailable".to_owned())),
            ]),
            ..FakeGateway::default()
        };

        let code = run_fetch("o/r", &output.to_string_lossy(), &gateway);

        assert_eq!(exit_code(code), exit_code(std::process::ExitCode::SUCCESS));
        let operator = load_json(&output.to_string_lossy(), "fetch").expect("operator snapshot");
        assert_eq!(operator["status"], json!("ok"));
        // The self-edge from the dependency read is dropped; #7 blocked by #9 stays.
        assert_eq!(operator["existing_edges"], json!([[7, 9]]));
        let codes: Vec<&str> = operator["warnings"]
            .as_array()
            .expect("warning rows")
            .iter()
            .map(|row| row["code"].as_str().expect("a code"))
            .collect();
        assert_eq!(
            codes,
            vec!["comments_read_failed", "dependency_read_failed"]
        );
        assert!(operator["issues"][0].get("body").is_none());
        let machine_path = operator["machine_fetch_file"].as_str().expect("a path");
        let machine = load_json(machine_path, "machine").expect("machine snapshot");
        assert_eq!(machine["issues"][0]["body"], json!("Blocked by #9"));
        let corpus = fs::read_to_string(
            operator["untrusted_corpus_file"]
                .as_str()
                .expect("a corpus path"),
        )
        .expect("read corpus");
        assert!(corpus.contains("<deps_issue_7 encoding=\"literal-redacted\">"));
        // The transient issue-body directory never survives the fetch.
        assert!(!directory.path().join("out").join("issue-bodies").exists());
    }

    #[test]
    fn a_refused_open_issue_read_still_writes_a_failed_snapshot() {
        let directory = TempDir::new().expect("temp directory");
        let output = directory.path().join("fetch.json");
        for (code, expected) in [
            ("json_invalid", "json_invalid"),
            ("gh_api_failed", "gh_api_failed"),
        ] {
            let gateway = FakeGateway {
                open_failure: Some(DepsReadFailure {
                    code,
                    detail: "boom".to_owned(),
                }),
                ..FakeGateway::default()
            };

            let exit = run_fetch("o/r", &output.to_string_lossy(), &gateway);

            assert_eq!(exit_code(exit), exit_code(std::process::ExitCode::from(1)));
            let payload = load_json(&output.to_string_lossy(), "fetch").expect("failed snapshot");
            assert_eq!(payload["status"], json!("failed"));
            assert_eq!(payload["warnings"][0]["code"], json!(expected));
            assert!(!directory.path().join("fetch-machine.json").exists());
        }
    }

    // ------------------------------------------------- snapshot pointer handling

    #[test]
    fn the_machine_pointer_must_name_a_sibling_of_the_snapshot_that_declared_it() {
        let directory = TempDir::new().expect("temp directory");
        let fetch = directory.path().join("fetch.json");
        fs::write(&fetch, "{}").expect("write snapshot");
        let fetch_path = fetch.to_string_lossy().into_owned();

        assert_eq!(
            resolve_machine_fetch(&fetch_path, &json!({})),
            Err("fetch-file: machine_fetch_file is required".to_owned())
        );
        assert_eq!(
            resolve_machine_fetch(&fetch_path, &json!({"machine_fetch_file": "   "})),
            Err("fetch-file: machine_fetch_file is required".to_owned())
        );
        // A traversal attempt keeps only the file name, so it lands in the snapshot
        // directory and is refused for being absent rather than followed.
        let refusal = resolve_machine_fetch(
            &fetch_path,
            &json!({"machine_fetch_file": "../../etc/passwd"}),
        )
        .expect_err("an absent sibling");
        assert!(
            refusal.starts_with("machine-fetch-file: file not found:")
                && refusal.ends_with("passwd"),
            "{refusal}"
        );
        let machine = directory.path().join("fetch-machine.json");
        fs::write(&machine, "{\"status\": \"failed\"}").expect("write machine");
        assert_eq!(
            resolve_machine_fetch(
                &fetch_path,
                &json!({"machine_fetch_file": "fetch-machine.json"})
            ),
            Err("machine-fetch-file: status is not ok".to_owned())
        );
        fs::write(&machine, "{\"status\": \"ok\"}").expect("rewrite machine");
        assert_eq!(
            resolve_machine_fetch(
                &fetch_path,
                &json!({"machine_fetch_file": "fetch-machine.json"})
            ),
            Ok(json!({"status": "ok"}))
        );
    }

    #[test]
    fn a_relative_path_normalizes_without_touching_the_filesystem() {
        let current = std::env::current_dir().expect("a working directory");
        assert_eq!(
            absolute(std::path::Path::new("/a/./b/../c")).to_string_lossy(),
            "/a/c"
        );
        assert_eq!(absolute(std::path::Path::new("x")), current.join("x"));
    }

    // -------------------------------------------------------- write-proposals

    #[test]
    fn write_proposals_validates_every_target_against_the_snapshot() {
        let directory = TempDir::new().expect("temp directory");
        let fetch = snapshot(
            &directory,
            "o/r",
            &json!([{"number": 1, "title": "one"}, {"number": 2, "title": "two"}]),
            &json!([]),
        );

        assert_eq!(
            validated_proposals(&fetch, ""),
            Ok(json!({})),
            "an empty line reads as an empty document"
        );
        assert_eq!(
            validated_proposals(&fetch, "[]"),
            Err("proposal JSON must be an object".to_owned())
        );
        assert!(
            validated_proposals(&fetch, "not json")
                .expect_err("a refusal")
                .starts_with("proposal JSON:")
        );
        assert_eq!(
            validated_proposals(&fetch, r#"{"closes": [{"issue": 9}]}"#),
            Err("proposal references unknown open issue #9".to_owned())
        );
        assert_eq!(
            validated_proposals(&fetch, r#"{"rewrites": 3}"#),
            Err("proposals: rewrites must be a list".to_owned())
        );
        assert_eq!(
            validated_proposals(
                &fetch,
                r#"{"desired_edges": [{"client_issue": 1, "blocker_issue": 2}]}"#
            )
            .expect("a usable document")["desired_edges"][0]["blocker_issue"],
            json!(2)
        );
    }

    // -------------------------------------------------------------------- plan

    #[test]
    fn the_plan_verb_reads_both_snapshots_and_reports_its_refusals() {
        let directory = TempDir::new().expect("temp directory");
        let fetch = snapshot(
            &directory,
            "o/r",
            &json!([{"number": 1, "title": "one"}, {"number": 2, "title": "two"}]),
            &json!([[1, 2]]),
        );
        let proposals = directory.path().join("proposals.json");
        fs::write(
            &proposals,
            r#"{"desired_edges": [{"client_issue": 2, "blocker_issue": 1}]}"#,
        )
        .expect("write proposals");
        let proposals = proposals.to_string_lossy().into_owned();
        let matching = FakeOrigin {
            origin: "o/r",
            ambient: None,
        };

        let plan = run_plan(&fetch, &proposals, None, &matching).expect("a usable plan");
        assert_eq!(plan["repo"], json!("o/r"));
        assert_eq!(plan["regular_refresh_allowed"], json!(false));
        // #1 is already blocked by #2, so #2 blocked by #1 would close a cycle.
        assert_eq!(plan["skipped_edges"][0]["reason"], json!("cycle"));

        assert_eq!(
            run_plan("/nonexistent/fetch.json", &proposals, None, &matching),
            Err("fetch-file: file not found: /nonexistent/fetch.json".to_owned())
        );
        fs::write(&proposals, "[]").expect("rewrite proposals");
        assert_eq!(
            run_plan(&fetch, &proposals, None, &matching),
            Err("proposals-file: expected JSON object".to_owned())
        );

        let no_repo = directory.path().join("no-repo.json");
        fs::write(&no_repo, r#"{"status": "ok"}"#).expect("write snapshot");
        assert_eq!(
            run_plan(&no_repo.to_string_lossy(), &proposals, None, &matching),
            Err("fetch-file: repo is required".to_owned())
        );

        fs::write(&proposals, "{}").expect("restore proposals");
        let bad_edges = directory.path().join("bad-edges.json");
        fs::write(
            &bad_edges,
            deps_pretty_json(&json!({
                "status": "ok",
                "repo": "o/r",
                "existing_edges": [[0, 2]],
                "machine_fetch_file": "fetch-machine.json",
            })),
        )
        .expect("write snapshot");
        assert_eq!(
            run_plan(&bad_edges.to_string_lossy(), &proposals, None, &matching),
            Err("edge must carry positive client_issue and blocker_issue values".to_owned())
        );
    }

    // ------------------------------------------------------------------- apply

    fn write_plan(directory: &TempDir, plan: &Value) -> String {
        let path = directory.path().join("plan.json");
        fs::write(&path, deps_pretty_json(plan)).expect("write plan");
        path.to_string_lossy().into_owned()
    }

    #[test]
    fn a_plan_without_its_snapshot_or_repository_is_refused_before_any_mutation() {
        let directory = TempDir::new().expect("temp directory");
        let mutating = json!({
            "status": "ok",
            "repo": "o/r",
            "closes": [{"issue": 1, "reason": "gone"}],
        });
        assert_eq!(
            load_apply_plan(&write_plan(&directory, &mutating), "o/r")
                .err()
                .expect("a refusal"),
            "plan-file: snapshot_issue_numbers is required and must be non-empty when plan contains mutations"
        );
        let no_repo = json!({
            "status": "ok",
            "snapshot_issue_numbers": [1],
            "closes": [{"issue": 1}],
        });
        assert_eq!(
            load_apply_plan(&write_plan(&directory, &no_repo), "o/r")
                .err()
                .expect("a refusal"),
            "plan-file: repo is required when plan contains mutations"
        );
        let wrong_repo = json!({"status": "ok", "repo": "other/repo"});
        assert_eq!(
            load_apply_plan(&write_plan(&directory, &wrong_repo), "o/r")
                .err()
                .expect("a refusal"),
            "plan-file: repo does not match --repo"
        );
        let forged = json!({
            "status": "ok",
            "repo": "o/r",
            "pair_cap": 1,
            "counts": {"skipped_latent_pairs": 3},
            "dependency_writes_allowed": true,
        });
        assert_eq!(
            load_apply_plan(&write_plan(&directory, &forged), "o/r")
                .err()
                .expect("a refusal"),
            "plan-file: dependency_writes_allowed disagrees with audit metadata"
        );
        let not_ok = json!({"status": "failed"});
        assert_eq!(
            load_apply_plan(&write_plan(&directory, &not_ok), "o/r")
                .err()
                .expect("a refusal"),
            "plan-file: status is not ok"
        );
        // An empty plan needs neither a snapshot nor a repository.
        assert!(load_apply_plan(&write_plan(&directory, &json!({"status": "ok"})), "o/r").is_ok());
    }

    #[test]
    fn apply_writes_every_approved_mutation_and_records_each_refusal() {
        let directory = TempDir::new().expect("temp directory");
        let plan = json!({
            "status": "ok",
            "repo": "o/r",
            "regular_refresh_allowed": true,
            "snapshot_issue_numbers": [1, 2, 3, 4, 5],
            "rewrites": [
                {"issue": 1, "body": "fresh <!-- larch:plan --> body"},
                {"issue": 3, "body": "busy now"},
                {"issue": 9, "body": "outside"},
            ],
            "closes": [{"issue": 2}, {"issue": 4}],
            "edges_to_write": [
                {"client_issue": 1, "blocker_issue": 5},
                {"client_issue": 1, "blocker_issue": 9},
            ],
        });
        let plan_file = write_plan(&directory, &plan);
        let gateway = FakeGateway {
            origin: "o/r".to_owned(),
            open: Some(vec![open_issue(1, "one", ""), open_issue(5, "five", "")]),
            live: BTreeMap::from([
                (1, live("one", "open")),
                (2, live("two", "open")),
                (3, live("[IMPLEMENTING] three", "open")),
                (4, live("four", "closed")),
                (5, live("five", "open")),
            ]),
            close_failures: BTreeSet::from([2]),
            ..FakeGateway::default()
        };

        let receipt = run_apply(
            "o/r",
            &load_apply_plan(&plan_file, "o/r").expect("an approved plan"),
            ApplyScope::default(),
            &gateway,
        );

        assert_eq!(receipt["status"], json!("partial"));
        assert_eq!(
            receipt["counts"],
            json!({"applied": 2, "skipped": 4, "failed": 1, "warnings": 0})
        );
        assert_eq!(
            receipt["applied"],
            json!([
                {"kind": "rewrite", "issue": 1},
                {"kind": "edge", "client_issue": 1, "blocker_issue": 5},
            ])
        );
        assert_eq!(
            receipt["failed"],
            json!([{"kind": "close", "issue": 2, "error": "close refused"}])
        );
        let skipped: Vec<(String, String)> = receipt["skipped"]
            .as_array()
            .expect("skipped rows")
            .iter()
            .map(|row| {
                (
                    row["kind"].as_str().unwrap_or_default().to_owned(),
                    row["reason"].as_str().unwrap_or_default().to_owned(),
                )
            })
            .collect();
        assert_eq!(
            skipped,
            vec![
                (
                    "rewrite".to_owned(),
                    "issue is no longer open mutable REGULAR".to_owned()
                ),
                (
                    "rewrite".to_owned(),
                    "issue was not in fetch snapshot".to_owned()
                ),
                (
                    "close".to_owned(),
                    "issue is no longer open mutable REGULAR".to_owned()
                ),
                (
                    "edge".to_owned(),
                    "endpoint was not in fetch snapshot".to_owned()
                ),
            ]
        );
        // The proposed body is redacted and its control marker neutralized before
        // it ever reaches GitHub.
        assert!(
            gateway
                .calls()
                .iter()
                .any(|call| call == "rewrite 1 fresh <!-- larch-redacted:plan --> body\n"),
            "{:?}",
            gateway.calls()
        );
    }

    #[test]
    fn a_partial_audit_plan_writes_no_edge_at_all() {
        let directory = TempDir::new().expect("temp directory");
        let plan = json!({
            "status": "ok",
            "repo": "o/r",
            "pair_cap": 1,
            "counts": {"skipped_latent_pairs": 3},
            "dependency_writes_allowed": false,
            "snapshot_issue_numbers": [1, 2],
            "edges_to_write": [{"client_issue": 1, "blocker_issue": 2}],
        });
        let plan_file = write_plan(&directory, &plan);
        let gateway = FakeGateway {
            origin: "o/r".to_owned(),
            ..FakeGateway::default()
        };

        let receipt = run_apply(
            "o/r",
            &load_apply_plan(&plan_file, "o/r").expect("an approved plan"),
            ApplyScope::default(),
            &gateway,
        );

        assert_eq!(receipt["counts"]["applied"], json!(0));
        assert_eq!(
            receipt["skipped"][0]["reason"],
            json!("partial-audit block")
        );
        assert_eq!(receipt["warnings"][0]["code"], json!("partial_audit_block"));
        assert!(
            gateway.calls().is_empty(),
            "a blocked edge reaches nothing: {:?}",
            gateway.calls()
        );
    }

    #[test]
    fn an_incomplete_graph_refresh_blocks_every_edge_write() {
        let directory = TempDir::new().expect("temp directory");
        let plan = json!({
            "status": "ok",
            "repo": "o/r",
            "snapshot_issue_numbers": [1, 2],
            "edges_to_write": [{"client_issue": 1, "blocker_issue": 2}],
        });
        let plan_file = write_plan(&directory, &plan);
        let gateway = FakeGateway {
            origin: "o/r".to_owned(),
            open: Some(vec![open_issue(1, "one", ""), open_issue(2, "two", "")]),
            dependencies: BTreeMap::from([((2, true), Err("blocking unavailable".to_owned()))]),
            live: BTreeMap::from([(1, live("one", "open")), (2, live("two", "open"))]),
            ..FakeGateway::default()
        };

        let receipt = run_apply(
            "o/r",
            &load_apply_plan(&plan_file, "o/r").expect("an approved plan"),
            ApplyScope::default(),
            &gateway,
        );

        assert_eq!(
            receipt["skipped"][0]["reason"],
            json!("live dependency graph refresh incomplete")
        );
        assert!(!gateway.calls().iter().any(|call| call.starts_with("edge ")));
    }

    #[test]
    fn the_two_scope_flags_each_apply_only_their_own_half() {
        let directory = TempDir::new().expect("temp directory");
        let plan = json!({
            "status": "ok",
            "repo": "o/r",
            "regular_refresh_allowed": true,
            "snapshot_issue_numbers": [1, 2],
            "rewrites": [{"issue": 1, "body": "fresh"}],
            "edges_to_write": [{"client_issue": 1, "blocker_issue": 2}],
        });
        let plan_file = write_plan(&directory, &plan);
        let approved = load_apply_plan(&plan_file, "o/r").expect("an approved plan");
        let build = || FakeGateway {
            origin: "o/r".to_owned(),
            open: Some(vec![open_issue(1, "one", ""), open_issue(2, "two", "")]),
            live: BTreeMap::from([(1, live("one", "open")), (2, live("two", "open"))]),
            ..FakeGateway::default()
        };

        let rewrites_only = build();
        let receipt = run_apply(
            "o/r",
            &approved,
            ApplyScope {
                rewrites_only: true,
                edges_only: false,
            },
            &rewrites_only,
        );
        assert_eq!(receipt["applied"], json!([{"kind": "rewrite", "issue": 1}]));
        assert!(
            !rewrites_only
                .calls()
                .iter()
                .any(|call| call.starts_with("edge "))
        );

        let edges_only = build();
        let receipt = run_apply(
            "o/r",
            &approved,
            ApplyScope {
                rewrites_only: false,
                edges_only: true,
            },
            &edges_only,
        );
        assert_eq!(
            receipt["applied"],
            json!([{"kind": "edge", "client_issue": 1, "blocker_issue": 2}])
        );
        assert!(
            !edges_only
                .calls()
                .iter()
                .any(|call| call.starts_with("rewrite "))
        );
    }

    #[test]
    fn a_refresh_the_checkout_cannot_authorize_is_skipped_wholesale() {
        let directory = TempDir::new().expect("temp directory");
        let plan = json!({
            "status": "ok",
            "repo": "o/r",
            "regular_refresh_allowed": true,
            "snapshot_issue_numbers": [1],
            "rewrites": [{"issue": 1, "body": "fresh"}],
            "closes": [{"issue": 1}],
        });
        let plan_file = write_plan(&directory, &plan);
        let gateway = FakeGateway {
            origin: "other/repo".to_owned(),
            ..FakeGateway::default()
        };

        let receipt = run_apply(
            "o/r",
            &load_apply_plan(&plan_file, "o/r").expect("an approved plan"),
            ApplyScope::default(),
            &gateway,
        );

        assert_eq!(receipt["counts"]["skipped"], json!(2));
        assert_eq!(
            receipt["skipped"][0]["reason"],
            json!("regular refresh not allowed")
        );
        assert!(gateway.calls().is_empty());
    }

    #[test]
    fn a_malformed_planned_edge_is_reported_rather_than_repaired() {
        let directory = TempDir::new().expect("temp directory");
        let plan = json!({
            "status": "ok",
            "repo": "o/r",
            "snapshot_issue_numbers": [1, 2],
            "edges_to_write": [{"client_issue": 0, "blocker_issue": 2}],
        });
        let plan_file = write_plan(&directory, &plan);
        let gateway = FakeGateway {
            origin: "o/r".to_owned(),
            ..FakeGateway::default()
        };

        let receipt = run_apply(
            "o/r",
            &load_apply_plan(&plan_file, "o/r").expect("an approved plan"),
            ApplyScope::default(),
            &gateway,
        );

        assert_eq!(receipt["status"], json!("partial"));
        assert_eq!(
            receipt["failed"][0]["error"],
            json!("edge must carry positive client_issue and blocker_issue values")
        );
    }

    #[test]
    fn an_edge_that_fails_to_write_does_not_join_the_batch() {
        let directory = TempDir::new().expect("temp directory");
        let plan = json!({
            "status": "ok",
            "repo": "o/r",
            "snapshot_issue_numbers": [1, 2, 3],
            "edges_to_write": [
                {"client_issue": 1, "blocker_issue": 2},
                {"client_issue": 2, "blocker_issue": 1},
            ],
        });
        let plan_file = write_plan(&directory, &plan);
        let gateway = FakeGateway {
            origin: "o/r".to_owned(),
            open: Some(vec![open_issue(1, "one", ""), open_issue(2, "two", "")]),
            live: BTreeMap::from([(1, live("one", "open")), (2, live("two", "open"))]),
            edge_failures: BTreeSet::from([(1, 2)]),
            ..FakeGateway::default()
        };

        let receipt = run_apply(
            "o/r",
            &load_apply_plan(&plan_file, "o/r").expect("an approved plan"),
            ApplyScope::default(),
            &gateway,
        );

        // The first edge failed, so it never enters the batch and the reciprocal
        // edge is not refused as a cycle against an edge that was never written.
        assert_eq!(
            receipt["counts"],
            json!({"applied": 1, "skipped": 0, "failed": 1, "warnings": 0})
        );
        assert_eq!(
            receipt["applied"],
            json!([{"kind": "edge", "client_issue": 2, "blocker_issue": 1}])
        );
    }

    #[test]
    fn a_second_edge_is_validated_against_the_one_this_pass_just_wrote() {
        let directory = TempDir::new().expect("temp directory");
        let plan = json!({
            "status": "ok",
            "repo": "o/r",
            "snapshot_issue_numbers": [1, 2],
            "edges_to_write": [
                {"client_issue": 1, "blocker_issue": 2},
                {"client_issue": 2, "blocker_issue": 1},
            ],
        });
        let plan_file = write_plan(&directory, &plan);
        let gateway = FakeGateway {
            origin: "o/r".to_owned(),
            open: Some(vec![open_issue(1, "one", ""), open_issue(2, "two", "")]),
            live: BTreeMap::from([(1, live("one", "open")), (2, live("two", "open"))]),
            ..FakeGateway::default()
        };

        let receipt = run_apply(
            "o/r",
            &load_apply_plan(&plan_file, "o/r").expect("an approved plan"),
            ApplyScope::default(),
            &gateway,
        );

        assert_eq!(receipt["counts"]["applied"], json!(1));
        assert_eq!(receipt["skipped"][0]["reason"], json!("cycle"));
        assert_eq!(receipt["warnings"][0]["code"], json!("edge_apply_skipped"));
    }

    #[test]
    fn the_graph_refresh_reports_a_failed_snapshot_as_incomplete() {
        let gateway = FakeGateway {
            open_failure: Some(DepsReadFailure {
                code: "json_invalid",
                detail: "bad".to_owned(),
            }),
            ..FakeGateway::default()
        };

        let (edges, warnings, complete) = refresh_dependency_graph("o/r", &gateway);

        assert!(edges.is_empty() && !complete);
        assert_eq!(warnings[0]["code"], json!("json_invalid"));
        assert_eq!(
            warnings[0]["message"],
            json!("open issue JSON invalid: bad")
        );
    }

    // ------------------------------------------------------- command lines

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    /// Every verb answers `--help` with exit `0`, the way `argparse` did.
    #[test]
    fn each_verb_answers_the_help_action_before_anything_else() {
        for verb in [
            resolve_repo as fn(&[OsString]) -> ExitCode,
            fetch,
            explicit_refs,
            write_proposals,
            plan_verb,
            apply,
        ] {
            assert_eq!(
                exit_code(verb(&arguments(&["--help"]))),
                exit_code(ExitCode::SUCCESS)
            );
            // The action wins even beside options the verb would otherwise
            // refuse for being unusable.
            assert_eq!(
                exit_code(verb(&arguments(&["--repo", "-h"]))),
                exit_code(ExitCode::SUCCESS)
            );
        }
    }

    /// Every verb refuses a line it cannot use with the `argparse` exit code.
    #[test]
    fn each_verb_refuses_its_own_unusable_line() {
        for (verb, line) in [
            (
                resolve_repo as fn(&[OsString]) -> ExitCode,
                &["--bogus", "x"][..],
            ),
            (fetch, &[][..]),
            (
                fetch,
                &["--repo", "o/r", "--output-file", "out.json", "extra"][..],
            ),
            (explicit_refs, &[][..]),
            (write_proposals, &[][..]),
            (plan_verb, &[][..]),
            (
                plan_verb,
                &[
                    "--fetch-file",
                    "f",
                    "--proposals-file",
                    "p",
                    "--pair-cap",
                    "x",
                ][..],
            ),
            (plan_verb, &["--repo"][..]),
            (apply, &[][..]),
        ] {
            assert_eq!(
                exit_code(verb(&arguments(line))),
                exit_code(ExitCode::from(2)),
                "{line:?}"
            );
        }
    }

    #[test]
    fn the_verbs_that_reach_no_network_run_end_to_end_from_their_command_lines() {
        let directory = TempDir::new().expect("temp directory");
        let fetch_file = snapshot(
            &directory,
            "character-ai/larch",
            &json!([
                {"number": 1, "title": "one", "body": "Blocked by #2", "comments": []},
                {"number": 2, "title": "two", "body": "", "comments": []},
            ]),
            &json!([]),
        );
        let refs_file = directory.path().join("refs.json");
        assert_eq!(
            exit_code(explicit_refs(&arguments(&[
                "--fetch-file",
                &fetch_file,
                "--output-file",
                &refs_file.to_string_lossy(),
            ]))),
            exit_code(ExitCode::SUCCESS)
        );
        let refs = load_json(&refs_file.to_string_lossy(), "refs").expect("the written refs");
        assert_eq!(refs["counts"]["explicit_edges"], json!(1));

        let proposals_file = directory.path().join("proposals.json");
        assert_eq!(
            exit_code(plan_verb(&arguments(&[
                "--fetch-file",
                &fetch_file,
                "--proposals-file",
                &proposals_file.to_string_lossy(),
            ]))),
            exit_code(ExitCode::from(1)),
            "a missing proposals file is a failed plan, not a crash"
        );
        fs::write(
            &proposals_file,
            r#"{"desired_edges": [{"client_issue": 1, "blocker_issue": 2}]}"#,
        )
        .expect("write proposals");
        assert_eq!(
            exit_code(plan_verb(&arguments(&[
                "--fetch-file",
                &fetch_file,
                "--proposals-file",
                &proposals_file.to_string_lossy(),
                "--pair-cap",
                "2",
            ]))),
            exit_code(ExitCode::from(1)),
            "a capped pass without its metadata is refused"
        );
        assert_eq!(
            exit_code(plan_verb(&arguments(&[
                "--fetch-file",
                &fetch_file,
                "--proposals-file",
                &proposals_file.to_string_lossy(),
                "--pair-cap",
                "-1",
            ]))),
            exit_code(ExitCode::from(1))
        );
        assert_eq!(
            exit_code(plan_verb(&arguments(&[
                "--fetch-file",
                &fetch_file,
                "--proposals-file",
                &proposals_file.to_string_lossy(),
            ]))),
            exit_code(ExitCode::SUCCESS)
        );
    }

    #[test]
    fn write_proposals_reads_its_document_from_the_command_line_and_stdin() {
        let directory = TempDir::new().expect("temp directory");
        let fetch_file = snapshot(
            &directory,
            "o/r",
            &json!([{"number": 1, "title": "one"}]),
            &json!([]),
        );
        let output = directory.path().join("proposals.json");
        // Stdin is empty under the test harness, which reads as `{}`.
        assert_eq!(
            exit_code(write_proposals(&arguments(&[
                "--fetch-file",
                &fetch_file,
                "--output-file",
                &output.to_string_lossy(),
            ]))),
            exit_code(ExitCode::SUCCESS)
        );
        assert_eq!(
            fs::read_to_string(&output).expect("the document"),
            "{}
"
        );
    }

    #[test]
    fn the_two_live_verbs_refuse_before_they_build_a_client() {
        let directory = TempDir::new().expect("temp directory");
        assert_eq!(
            exit_code(fetch(&arguments(&[
                "--repo",
                "../escape",
                "--output-file",
                &directory.path().join("out.json").to_string_lossy(),
            ]))),
            exit_code(ExitCode::from(1))
        );
        assert_eq!(
            exit_code(apply(&arguments(&[
                "--repo",
                "o/r",
                "--plan-file",
                "/nonexistent/plan.json",
                "--rewrites-only",
                "--edges-only",
            ]))),
            exit_code(ExitCode::from(1))
        );
        assert_eq!(
            exit_code(apply(&arguments(&[
                "--repo",
                "o/r",
                "--plan-file",
                "/nonexistent/plan.json",
            ]))),
            exit_code(ExitCode::from(1))
        );
    }

    #[test]
    fn an_unwritable_output_path_is_reported_rather_than_panicking() {
        let directory = TempDir::new().expect("temp directory");
        let blocker = directory.path().join("file");
        fs::write(&blocker, "not a directory").expect("write blocker");
        let output = blocker.join("nested").join("refs.json");
        let fetch_file = snapshot(
            &directory,
            "o/r",
            &json!([{"number": 1, "title": "one"}]),
            &json!([]),
        );

        assert_eq!(
            exit_code(explicit_refs(&arguments(&[
                "--fetch-file",
                &fetch_file,
                "--output-file",
                &output.to_string_lossy(),
            ]))),
            exit_code(ExitCode::from(1))
        );
        let gateway = FakeGateway::default();
        assert_eq!(
            exit_code(run_fetch("o/r", &output.to_string_lossy(), &gateway)),
            exit_code(ExitCode::from(1))
        );
    }

    // ------------------------------------------------- effect-free gateway halves

    fn listed_issue(
        number: u64,
        title: &str,
        pull_request: bool,
        state: GitHubIssueState,
    ) -> GitHubIssue {
        GitHubIssue {
            id: number * 10,
            number,
            title: title.to_owned(),
            body: "body".to_owned(),
            state,
            url: String::new(),
            author: String::new(),
            labels: vec![
                GitHubLabel {
                    id: 1,
                    name: "bug".to_owned(),
                    color: String::new(),
                    description: String::new(),
                },
                GitHubLabel {
                    id: 2,
                    name: String::new(),
                    color: String::new(),
                    description: String::new(),
                },
            ],
            comments: 0,
            created_at: String::new(),
            closed_at: String::new(),
            updated_at: String::new(),
            is_pull_request: pull_request,
        }
    }

    #[test]
    fn the_listed_snapshot_drops_pull_requests_and_sorts_by_number() {
        let rows = open_rows_from(vec![
            listed_issue(9, "nine", false, GitHubIssueState::Open),
            listed_issue(4, "a pull request", true, GitHubIssueState::Open),
            listed_issue(2, "two", false, GitHubIssueState::Open),
            listed_issue(3, "closed", false, GitHubIssueState::Closed),
        ]);

        assert_eq!(
            rows.iter().map(|row| row.number).collect::<Vec<u64>>(),
            vec![2, 9]
        );
        // An unnamed label never reaches the snapshot.
        assert_eq!(rows[0].labels, vec!["bug".to_owned()]);
        assert!(open_rows_from(Vec::new()).is_empty());
    }

    #[test]
    fn a_dependency_read_reduces_to_distinct_sorted_numbers() {
        assert!(edge_numbers(&[]).is_empty());
    }

    #[test]
    fn only_a_malformed_response_reads_as_invalid_json() {
        assert_eq!(
            read_failure(&GitHubOperationError::new(
                GitHubOperationErrorKind::MalformedResponse,
                None,
                None,
                "bad body",
            ))
            .code,
            "json_invalid"
        );
        let transport = read_failure(&GitHubOperationError::new(
            GitHubOperationErrorKind::Transport,
            None,
            None,
            "unreachable\nhost",
        ));
        assert_eq!(transport.code, "gh_api_failed");
        assert_eq!(transport.detail, "unreachable host");
    }

    #[test]
    fn every_live_state_has_one_spelling_the_predicates_read() {
        assert_eq!(live_state(GitHubIssueState::Open), "open");
        assert_eq!(live_state(GitHubIssueState::Closed), "closed");
        assert_eq!(live_state(GitHubIssueState::All), "");
    }

    #[test]
    fn a_rewrite_swaps_only_the_body_against_the_snapshot_it_read() {
        let snapshot = IssueMutationSnapshot {
            repository: GitHubRepositoryRef::new("o", "r").expect("a usable slug"),
            issue: 12,
            title: "one".to_owned(),
            body: "old".to_owned(),
            labels: BTreeSet::new(),
            state: GitHubIssueState::Open,
            updated_at: "2026-08-08T00:00:00Z".to_owned(),
        };

        let request = body_mutation_request(&snapshot, "fresh");

        assert_eq!(request.issue, 12);
        assert_eq!(request.body.as_deref(), Some("fresh"));
        assert_eq!(request.expected_updated_at, "2026-08-08T00:00:00Z");
        assert_eq!(request.fields, BTreeSet::from([IssueMutationField::Body]));
        assert!(request.title.is_none() && request.labels.is_none());
    }

    // ------------------------------------------------------- remaining branches

    #[test]
    fn an_unreadable_input_path_is_refused_without_claiming_it_is_absent() {
        let directory = TempDir::new().expect("temp directory");
        let refusal = load_json(&directory.path().to_string_lossy(), "fetch-file")
            .expect_err("a directory is not a document");
        assert!(refusal.starts_with("fetch-file: cannot read:"), "{refusal}");
    }

    #[test]
    fn a_leading_current_directory_segment_normalizes_away() {
        let current = std::env::current_dir().expect("a working directory");
        assert_eq!(absolute(std::path::Path::new("./x")), current.join("x"));
    }

    #[test]
    fn each_verb_refuses_an_option_that_ends_the_line_without_its_value() {
        for (verb, line) in [
            (fetch as fn(&[OsString]) -> ExitCode, &["--repo"][..]),
            (explicit_refs, &["--fetch-file"][..]),
            (write_proposals, &["--output-file"][..]),
            (plan_verb, &["--fetch-file"][..]),
            (apply, &["--plan-file"][..]),
        ] {
            assert_eq!(
                exit_code(verb(&arguments(line))),
                exit_code(ExitCode::from(2)),
                "{line:?}"
            );
        }
    }

    #[test]
    fn each_verb_refuses_a_surplus_argument_after_its_required_options() {
        let directory = TempDir::new().expect("temp directory");
        let path = directory
            .path()
            .join("x.json")
            .to_string_lossy()
            .into_owned();
        for (verb, line) in [
            (
                explicit_refs as fn(&[OsString]) -> ExitCode,
                vec!["--fetch-file", &path, "--output-file", &path, "surplus"],
            ),
            (
                write_proposals,
                vec!["--output-file", &path, "--fetch-file", &path, "surplus"],
            ),
            (
                plan_verb,
                vec!["--fetch-file", &path, "--proposals-file", &path, "surplus"],
            ),
            (
                apply,
                vec!["--repo", "o/r", "--plan-file", &path, "surplus"],
            ),
        ] {
            assert_eq!(
                exit_code(verb(&arguments(&line))),
                exit_code(ExitCode::from(2)),
                "{line:?}"
            );
        }
    }

    #[test]
    fn a_blocking_read_contributes_its_mirrored_edge_to_both_graphs() {
        let gateway = FakeGateway {
            open: Some(vec![open_issue(1, "one", ""), open_issue(2, "two", "")]),
            dependencies: BTreeMap::from([((1, true), Ok(vec![2, 1])), ((2, false), Ok(vec![1]))]),
            ..FakeGateway::default()
        };

        let (edges, warnings, complete) = refresh_dependency_graph("o/r", &gateway);

        // `1 blocking 2` and `2 blocked by 1` are the same edge, and the
        // self-reference is dropped.
        assert_eq!(edges, BTreeSet::from([(2, 1)]));
        assert!(warnings.is_empty() && complete);

        let directory = TempDir::new().expect("temp directory");
        let output = directory.path().join("fetch.json");
        assert_eq!(
            exit_code(run_fetch("o/r", &output.to_string_lossy(), &gateway)),
            exit_code(ExitCode::SUCCESS)
        );
        let snapshot = load_json(&output.to_string_lossy(), "fetch").expect("the snapshot");
        assert_eq!(snapshot["existing_edges"], json!([[2, 1]]));
    }

    #[test]
    fn a_refused_graph_refresh_reports_the_gh_failure_class() {
        let gateway = FakeGateway {
            open_failure: Some(DepsReadFailure {
                code: "gh_api_failed",
                detail: "rate limited".to_owned(),
            }),
            ..FakeGateway::default()
        };

        let (_edges, warnings, complete) = refresh_dependency_graph("o/r", &gateway);

        assert!(!complete);
        assert_eq!(
            warnings[0]["message"],
            json!("open issue fetch failed: rate limited")
        );
    }

    #[test]
    fn a_plan_row_without_a_usable_issue_number_is_passed_over() {
        let directory = TempDir::new().expect("temp directory");
        let plan = json!({
            "status": "ok",
            "repo": "o/r",
            "regular_refresh_allowed": true,
            "snapshot_issue_numbers": [1],
            "rewrites": [{"reason": "no issue at all"}, "not an object"],
            "closes": [{"issue": 0}],
        });
        let plan_file = write_plan(&directory, &plan);
        let gateway = FakeGateway {
            origin: "o/r".to_owned(),
            ..FakeGateway::default()
        };

        let receipt = run_apply(
            "o/r",
            &load_apply_plan(&plan_file, "o/r").expect("an approved plan"),
            ApplyScope::default(),
            &gateway,
        );

        assert_eq!(
            receipt["counts"],
            json!({"applied": 0, "skipped": 0, "failed": 0, "warnings": 0})
        );
        assert!(gateway.calls().is_empty());
    }
}
