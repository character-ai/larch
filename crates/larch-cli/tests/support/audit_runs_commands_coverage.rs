//! Focused offline coverage for the run-audit compatibility commands.
//!
//! Artifact fixtures exercise the same hostile archived-run handling as the
//! command, while loopback GitHub exchanges keep command-level range and
//! mapping coverage offline.

use super::*;
use crate::github_service::with_test_github_service;
use chrono::{TimeZone, Utc};
use larch_adapters::github::OctocrabGitHubService;
use larch_test_support::{IssueServiceExchange, IssueServiceStub};
use serde_json::json;
use std::{
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    sync::Arc,
};
use tempfile::tempdir;

fn write(root: &Path, relative: &str, contents: &str) {
    let path = root.join(relative);
    fs::create_dir_all(path.parent().expect("fixture parent")).expect("fixture parent");
    fs::write(path, contents).expect("fixture file");
}

fn fixture_run(root: &Path) -> PathBuf {
    let run = root.join("larch-logs/implement/run-a");
    fs::create_dir_all(run.join("round-1")).expect("round one");
    fs::create_dir_all(run.join("round-3")).expect("round three");
    write(
        &run,
        "manifest.json",
        r#"{"schema_version":2,"pr_number":7,"started_at":"2026-08-09T12:00:00Z","ended_at":"done","larch_version":"56.2.2","steps_ran":{"step8":true}}"#,
    );
    run
}

fn result(value: &Value) -> &str {
    value["result"].as_str().expect("scan result")
}

fn clean_outcome(kind: AssessmentKind) -> Value {
    let mut value = json!({
        "schema_version": "1",
        "phase": "implement",
        "step": "8",
        "base_ref": "origin/main",
        "head_sha": "abc123",
        "outcome": "clean",
        "reason": "clean-note",
        "assessment_kind": "clean",
    });
    value[match kind {
        AssessmentKind::Guidelines => "guidelines_status",
        AssessmentKind::Invariants => "invariants_status",
    }] = json!("present");
    value
}

fn arguments(values: &[&str]) -> Vec<OsString> {
    values.iter().map(OsString::from).collect()
}

fn audit_pull_request(number: u64, title: &str, body: &str, merged_at: Option<&str>) -> Value {
    let mut value = json!({
        "number": number,
        "title": title,
        "body": body,
        "base": {"ref": "main"},
        "merged_at": merged_at,
    });
    if merged_at.is_none() {
        value["merged_at"] = Value::Null;
    }
    value
}

fn audit_issue(number: u64, title: &str, body: &str) -> Value {
    let mut issue: Value = serde_json::from_str(include_str!(
        "../../../larch-adapters/fixtures/github_issue.json"
    ))
    .expect("issue fixture");
    issue["number"] = json!(number);
    issue["id"] = json!(number);
    issue["title"] = json!(title);
    issue["body"] = json!(body);
    issue["state"] = json!("closed");
    issue["closed_at"] = json!("2026-08-09T12:00:00Z");
    issue
}

fn loopback_service(base: String) -> Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> {
    Arc::new(move || OctocrabGitHubService::with_test_base(&base))
}

#[test]
#[allow(clippy::too_many_lines)] // One table preserves small Python-compatible scalar boundaries.
fn compatibility_helpers_keep_parser_and_mapping_boundaries() {
    let arguments = [OsString::from("--help")];
    assert!(wants_help(&arguments));
    assert!(!wants_help(&[OsString::from("--hel")]));
    assert_eq!(audit_help("unknown"), ExitCode::SUCCESS);
    assert!(valid_skill("design", "audit-test"));
    assert!(valid_skill("implement", "audit-test"));
    assert!(!valid_skill("other", "audit-test"));

    assert_eq!(normalized_log_root("", "implement"), "larch-logs/implement");
    assert_eq!(
        normalized_log_root("/tmp/larch-logs", "design"),
        "/tmp/larch-logs/design"
    );
    assert_eq!(normalized_log_root("logs/custom", "design"), "logs/custom");
    assert_eq!(
        design_run_id(
            "chore(larch-logs): design run ABCDEF01-2345-6789-ABCD-EF0123456789 (issue #4)"
        ),
        Some("ABCDEF01-2345-6789-ABCD-EF0123456789".to_owned())
    );
    assert_eq!(design_run_id("ordinary"), None);
    assert_eq!(closing_issue("Fixes #12"), Some("12".to_owned()));
    assert_eq!(closing_issue("Closes #12 and closes #13"), None);
    assert_eq!(closing_issue("no closing wire"), None);
    assert!(matches_skill(
        "design",
        "chore(larch-logs): design run ABCDEF01-2345-6789-ABCD-EF0123456789"
    ));
    assert!(!matches_skill(
        "implement",
        "chore(larch-logs): design run ABCDEF01-2345-6789-ABCD-EF0123456789"
    ));
    assert!(matches_audit_title(
        "implement",
        "[Run Logs Audit 2026 Report]"
    ));
    assert!(matches_audit_title(
        "design",
        "[Design Run Logs Audit 2026 Report]"
    ));
    assert!(!matches_audit_title(
        "design",
        "[Run Logs Audit 2026 Report]"
    ));
    assert_eq!(
        frontmatter_last_pr("---\naudited_pr_range:\n  last: \"42\"\n---\n"),
        Some(42)
    );
    assert_eq!(frontmatter_last_pr("body\n---\nlast: 42\n---"), None);
    assert!(valid_full_instant("2026-08-09T12:00:00Z"));
    assert!(valid_full_instant("2026-08-09T12:00+07:00"));
    assert!(!valid_full_instant("2026-08-09"));
    assert_eq!(explicit_pr_number("#42"), Some(42));
    assert_eq!(explicit_pr_number("PR #42"), Some(42));
    assert_eq!(explicit_pr_number("42"), None);

    assert_eq!(
        render_pacific_timestamp(Utc.with_ymd_and_hms(2026, 3, 8, 10, 0, 0).unwrap()),
        "2026-03-08T03:00-07:00"
    );
    assert_eq!(
        pacific_offset_hours(Utc.with_ymd_and_hms(2026, 11, 1, 9, 0, 0).unwrap()),
        -8
    );
    assert_eq!(first_sunday(2026, 3).day(), 1);
    assert_eq!(second_sunday(2026, 3).day(), 8);

    assert_eq!(top_frontmatter("---\na: 1\n---\nignored"), "a: 1");
    assert_eq!(top_frontmatter("not frontmatter\n---\n"), "");
    assert_eq!(prior_value("count: 12\n", "count"), 12);
    assert_eq!(prior_value("count: nope\n", "count"), 0);
    assert_eq!(number_value(Some(&json!(12))), 12);
    assert_eq!(number_value(Some(&json!(" 9 "))), 9);
    assert_eq!(number_value(Some(&json!(-1))), 0);
    assert_eq!(value_string(&json!({"a": true}), "a"), "true");
    assert_eq!(value_string(&json!({"a": false}), "a"), "false");
    assert_eq!(value_string(&json!({"a": 2}), "a"), "2");
    assert_eq!(category(&json!({"category": false})), "false");
    assert_eq!(category(&json!({"category": null})), "");
    assert!(json_truthy(Some(&json!([1]))));
    assert!(!json_truthy(Some(&json!([]))));
    assert!(json_truthy(Some(&json!(-1))));
    assert!(!json_truthy(Some(&json!(0))));
    assert_eq!(clean_controls("  line\n\tvalue\u{0000}  "), "linevalue");
    assert_eq!(clean_reason("  line\n\tvalue\u{0000}  "), "line  value");
    assert_eq!(nonempty_or("", "fallback"), "fallback");
    assert_eq!(nonempty_or("value", "fallback"), "value");
}

#[test]
#[allow(clippy::too_many_lines)] // The fixture intentionally spans every safe artifact reader branch.
fn artifact_readers_and_review_classifiers_handle_complete_and_degraded_runs() {
    let temporary = tempdir().expect("temporary run");
    let run = fixture_run(temporary.path());
    write(&run, "root-note.md", "root\r\ntext\r\n");
    write(&run, "round-3/round-note.txt", "round\n");
    write(
        &run,
        "round-1/voting-tally.md",
        "| FINDING_A | 0 | 0 | 2 | body | rejected |\n",
    );
    write(
        &run,
        "review-findings-full.jsonl",
        concat!(
            r#"{"id":"OOS_1","phase":"plan-review","outcome":"accepted","category":"wrong-category"}"#,
            "\n",
            r####"{"id":"REJ_1","phase":"code-review","outcome":"rejected","category":false,"prose_body":"### FINDING_A: security"}"####,
            "\n",
            r#"{"id":"RETRO","phase":"retroactive-backfill","outcome":"accepted","category":"security"}"#,
            "\n",
            "not-json\n",
            "[]\n"
        ),
    );
    write(
        &run,
        "code-review-tally.json",
        r#"{"mode":"self-review","accepted_count":2,"rejected_count":"1"}"#,
    );

    let rounds = round_directories(&run);
    assert_eq!(
        rounds.iter().map(|path| run_name(path)).collect::<Vec<_>>(),
        ["round-1", "round-3"]
    );
    assert_eq!(
        read_text(&run.join("root-note.md")),
        Some("root\ntext\n".to_owned())
    );
    assert_eq!(
        manifest_json(&run.join("manifest.json")).expect("manifest JSON")["pr_number"],
        7
    );
    assert_eq!(manifest_json(&run.join("missing.json")), None);
    let (rows, malformed) = ndjson_rows(&run.join("review-findings-full.jsonl"));
    assert_eq!(rows.len(), 3);
    assert!(malformed);
    assert_eq!(
        ndjson_rows(&run.join("missing.ndjson")),
        (Vec::new(), false)
    );
    assert_eq!(
        effective_review_rows(&run, "design", rows.clone(), malformed).len(),
        3
    );
    assert_eq!(
        effective_review_rows(&run, "implement", rows, false).len(),
        2
    );
    assert_eq!(
        effective_review_rows(&run, "implement", Vec::new(), false).len(),
        3
    );

    let required = temporary.path().join("required.tsv");
    fs::write(
        &required,
        "relative_path\tcondition\nmanifest.json\talways\nroot-note.md\talways\nround-*/round-note.txt\talways\n",
    )
    .expect("required fixture");
    assert_eq!(
        result(&required_file_scan(&run, 7, Some(&required))),
        "pass"
    );
    fs::write(&required, "missing.md\talways\n").expect("missing fixture");
    let missing = required_file_scan(&run, 7, Some(&required));
    assert_eq!(result(&missing), "fail");
    assert_eq!(missing["missing"], json!(["missing.md"]));
    fs::write(&required, "root-note.md\tunknown-condition\n").expect("invalid fixture");
    assert_eq!(
        result(&required_file_scan(&run, 7, Some(&required))),
        "error"
    );
    assert_eq!(result(&required_file_scan(&run, 7, None)), "skip");
    assert!(required_glob_hit(&run, "root-note.md"));
    assert!(required_glob_hit(&run, "round-*/round-note.txt"));
    assert!(!required_glob_hit(&run, "missing*.md"));
    assert_eq!(result(&exon_scan(&run, 7)), "fail");

    let reviews = vec![
        json!({"id":"OOS_1","phase":"plan-review","outcome":"accepted","category":"wrong-category"}),
        json!({"id":"OK","phase":"plan-review","outcome":"accepted","category":"security"}),
        json!({"id":"REJ_1","category":false,"prose_body":"### FINDING_X: correctness"}),
    ];
    assert_eq!(mangled_review_rows(&reviews).len(), 1);
    let rejected = rejected_blank_category_scan(&reviews, 7, "rej-category-blank");
    assert_eq!(result(&rejected), "fail");
    assert_eq!(rejected["rej_blank_with_cat_in_prose"], 1);
    assert_eq!(
        result(&rejected_blank_category_scan(
            &[json!({"id":"REJ_2"})],
            7,
            "rej"
        )),
        "pass"
    );

    assert!(invalid_run_directory(&run, "implement").is_none());
    assert!(
        invalid_run_directory(&run.parent().expect("skill root"), "implement")
            .expect("skill root rejected")
            .contains("specific run")
    );
    assert!(
        invalid_run_directory(&run, "design")
            .expect("wrong skill rejected")
            .contains("--skill=design")
    );
    assert_eq!(parent_issue_number(&run.join("parent-issue.md")), None);
    write(&run, "parent-issue.md", "ISSUE_NUMBER=12\n");
    assert_eq!(
        parent_issue_number(&run.join("parent-issue.md")),
        Some("12".to_owned())
    );
    assert_eq!(parent_issue_candidates(&[run.clone()], "12"), [run.clone()]);
    assert!(manifest_epoch(&run) > 0.0);
    assert_eq!(
        manifest_fields(&run.join("manifest.json")),
        (
            "2026-08-09T12:00:00Z".to_owned(),
            "56.2.2".to_owned(),
            String::new()
        )
    );
}

#[test]
#[allow(clippy::too_many_lines)] // Every result branch is an operator-visible audit classification.
fn signal_execution_and_timing_scans_preserve_artifact_evidence() {
    let temporary = tempdir().expect("temporary run");
    let run = fixture_run(temporary.path());
    write(
        &run,
        "round-1/round-meta.json",
        r#"{
          "reviewer_signals":[
            {"ns_retry_reason":"OUTPUT_EMPTY","output_basename":"review.txt","first_pass_trailing_content":true},
            {"ns_retry_reason":"unexpected","output_basename":"other.txt"},
            {"output_basename":"codex-generalist-output.txt","result_kind":"NO_ISSUES_FOUND"}
          ],
          "wrapper_logs":{"codex":"125s elapsed"},
          "coder":{"CODER_TOOL":"codex"}
        }"#,
    );
    write(&run, "round-1/review-ns-retry.txt", "known signal");
    write(&run, "round-1/unlisted-ns-retry.txt", "legacy sidecar");
    write(
        &run,
        "round-3/cursor-ci-stall-one.json",
        r#"{"channel":"nightly"}"#,
    );
    write(&run, "round-3/cursor-ci-stall-two.json", "not-json");
    write(
        &run,
        "round-3/panel-manifest.ndjson",
        concat!(
            r#"{"tool":"codex","slot":"generalist"}"#,
            "\n",
            r#"{"tool":"codex","slot":"codex-plan-generic"}"#,
            "\n",
            r#"{"tool":"cursor","slot":"generalist"}"#,
            "\n"
        ),
    );
    write(&run, "round-3/coder.env", "CODER_TOOL=cursor\n");
    write(
        &run,
        "execution-issues.ndjson",
        concat!(
            r#"{"category":"Warnings","body":"ordinary warning"}"#,
            "\n",
            r#"{"category":"Correctness","body":"Changelog rebase conflict found"}"#,
            "\n"
        ),
    );
    write(
        &run,
        "timing-report.json",
        r#"{"vendor_task_averages":[{"vendor":"codex","task_kind":"codex-review-generic","max_seconds":"130"}],"steps":[{"task":"step 5 code review","elapsed_seconds":80}]}"#,
    );

    let (signals_present, signals) = round_signals(&run);
    assert!(signals_present);
    assert_eq!(signals.len(), 3);
    let retries = ns_retry_scan(&run, 7, "ns-retry-sidecars", signals_present, &signals);
    assert_eq!(result(&retries), "fail");
    assert_eq!(retries["count"], 3);
    assert_eq!(retries["reasons"]["UNKNOWN"], 2);
    let legacy = ns_retry_scan(&run, 7, "ns", false, &[]);
    assert_eq!(result(&legacy), "fail");
    let empty = tempdir().expect("empty run");
    assert_eq!(
        result(&ns_retry_scan(empty.path(), 7, "ns", false, &[])),
        "skip"
    );
    assert!(is_txt_file_name("artifact.txt"));
    assert!(!is_txt_file_name("artifact.md"));
    assert_eq!(
        histogram(&["a".to_owned(), "a".to_owned(), "b".to_owned()])["a"],
        2
    );

    let stalls = cursor_stall_scan(&run, 7, "cursor-ci-stall-causes");
    assert_eq!(result(&stalls), "informational");
    assert_eq!(stalls["count"], 2);
    assert_eq!(stalls["parsed_files"], 1);
    assert_eq!(
        result(&cursor_stall_scan(empty.path(), 7, "cursor")),
        "pass"
    );
    let adherence = codex_adherence_scan(&run, 7, "codex-round1-adherence");
    assert_eq!(result(&adherence), "fail");
    assert_eq!(adherence["rounds_with_generic_codex"], json!([3]));
    assert_eq!(
        result(&codex_adherence_scan(empty.path(), 7, "adherence")),
        "pass"
    );

    assert_eq!(
        result(&execution_categories_scan(&run, 7, "execution")),
        "fail"
    );
    assert_eq!(
        result(&execution_categories_scan(empty.path(), 7, "execution")),
        "skip"
    );
    assert_eq!(
        result(&cache_freshness_scan(&run, 7, "cache", "56.3.0")),
        "informational"
    );
    assert_eq!(
        result(&cache_freshness_scan(&run, 7, "cache", "unknown")),
        "skip"
    );
    write(
        &run,
        "manifest.json",
        r#"{"larch_version":"","steps_ran":{"step8":true}}"#,
    );
    assert_eq!(
        result(&cache_freshness_scan(&run, 7, "cache", "56.3.0")),
        "fail"
    );
    write(
        &run,
        "manifest.json",
        r#"{"larch_version":"56.3.0","steps_ran":{"step8":true}}"#,
    );
    assert_eq!(
        result(&cache_freshness_scan(&run, 7, "cache", "56.3.0")),
        "pass"
    );
    assert_eq!(version_numbers("release-56.3.0"), [56, 3, 0]);
    assert_eq!(version_numbers("none"), [0]);
    assert_eq!(strict_version_tuple("56.3.0"), Some((56, 3, 0)));
    assert_eq!(strict_version_tuple("56.3"), None);
    assert_eq!(result(&changelog_scan(&run, 7, "changelog")), "fail");
    assert_eq!(
        result(&changelog_scan(empty.path(), 7, "changelog")),
        "skip"
    );

    let coder = coder_tool_scan(&run, 7, "coder-tool");
    assert_eq!(result(&coder), "pass");
    assert_eq!(coder["by_round"]["round-1"], "codex");
    assert_eq!(coder["by_round"]["round-3"], "cursor");
    assert_eq!(
        result(&trailing_content_scan(7, "trailing", true, &signals)),
        "fail"
    );
    assert_eq!(
        result(&trailing_content_scan(7, "trailing", false, &[])),
        "skip"
    );
    assert_eq!(
        result(&trailing_content_scan(7, "trailing", true, &[])),
        "pass"
    );
    let waste = codex_waste_scan(&run, 7, "codex-waste");
    assert_eq!(result(&waste), "fail");
    assert_eq!(waste["elapsed_seconds"], 125);
    assert_eq!(codex_timing_elapsed(&run), 130);
    assert_eq!(
        timing_seconds(&json!({"duration_seconds": "12.9"})),
        Some(12)
    );
    assert_eq!(timing_seconds(&json!({"duration_seconds": -1})), None);
    assert_eq!(timing_seconds(&json!({"duration_seconds": "nan"})), None);
}

#[test]
#[allow(clippy::too_many_lines)] // The outcome matrix is the public Step 8 compatibility contract.
fn assessment_and_outcome_scans_distinguish_missing_invalid_and_valid_artifacts() {
    let temporary = tempdir().expect("temporary run");
    let run = fixture_run(temporary.path());
    write(&run, "final-summary.md", "completed\n");

    assert_eq!(
        result(&assessment_scan(
            &run,
            7,
            "guideline-assessment",
            "architectural-guideline-assessment.md",
            CLEAN_GUIDELINE,
            "clean",
            "deviation",
            "guideline",
        )),
        "informational"
    );
    write(&run, "architectural-guideline-assessment.md", "\n");
    assert_eq!(
        result(&assessment_scan(
            &run,
            7,
            "guideline-assessment",
            "architectural-guideline-assessment.md",
            CLEAN_GUIDELINE,
            "clean",
            "deviation",
            "guideline",
        )),
        "fail"
    );
    write(
        &run,
        "architectural-guideline-assessment.md",
        &format!("{CLEAN_GUIDELINE}\n"),
    );
    let clean = assessment_scan(
        &run,
        7,
        "guideline-assessment",
        "architectural-guideline-assessment.md",
        CLEAN_GUIDELINE,
        "clean",
        "deviation",
        "guideline",
    );
    assert_eq!(result(&clean), "pass");
    assert_eq!(clean["assessment_kind"], "clean");
    write(
        &run,
        "architectural-guideline-assessment.md",
        "deviation noted\n",
    );
    assert_eq!(
        assessment_scan(
            &run,
            7,
            "guideline-assessment",
            "architectural-guideline-assessment.md",
            CLEAN_GUIDELINE,
            "clean",
            "deviation",
            "guideline",
        )["assessment_kind"],
        "deviation"
    );

    let guideline = || {
        outcome_scan(
            &run,
            7,
            "guideline-ship-outcome",
            GUIDELINE_OUTCOME,
            AssessmentKind::Guidelines,
        )
    };
    assert_eq!(result(&guideline()), "fail");
    write(
        &run,
        "manifest.json",
        r#"{"larch_version":"52.4.15","steps_ran":{"step8":true}}"#,
    );
    assert_eq!(result(&guideline()), "informational");
    write(
        &run,
        "manifest.json",
        r#"{"larch_version":"56.3.0","steps_ran":{"step8":true}}"#,
    );
    write(&run, GUIDELINE_OUTCOME, "\n");
    assert_eq!(result(&guideline()), "fail");
    write(&run, GUIDELINE_OUTCOME, "not JSON\n");
    assert_eq!(result(&guideline()), "fail");
    write(
        &run,
        GUIDELINE_OUTCOME,
        &serde_json::to_string(&clean_outcome(AssessmentKind::Guidelines)).expect("outcome JSON"),
    );
    let valid = guideline();
    assert_eq!(result(&valid), "pass");
    assert_eq!(valid["outcome"], "clean");

    write(
        &run,
        INVARIANT_OUTCOME,
        &serde_json::to_string(&clean_outcome(AssessmentKind::Invariants)).expect("outcome JSON"),
    );
    assert_eq!(
        result(&outcome_scan(
            &run,
            7,
            "invariant-ship-outcome",
            INVARIANT_OUTCOME,
            AssessmentKind::Invariants,
        )),
        "pass"
    );
    write(&run, "manifest.json", r#"{"steps_ran":{"step8":false}}"#);
    assert!(!step8_reachable(
        &run,
        &json!({"steps_ran":{"step8":false}}),
        7
    ));
    assert_eq!(result(&guideline()), "informational");
    assert_eq!(result(&oos_silent_drop_scan(&run, 7, "oos")), "skip");

    category_stats_scan(&[], false, false, false, 7, "design", None);
    category_stats_scan(&[], false, false, false, 7, "implement", None);
    category_stats_scan(
        &[json!({"id":"OOS_1","category":"security"})],
        true,
        true,
        false,
        7,
        "implement",
        None,
    );
    category_stats_scan(&[], true, false, true, 7, "implement", None);
    cross_cutting_scan(&run, 7);
    write(
        &run,
        "manifest.json",
        r#"{"schema_version":2,"pr_number":null,"ended_at":null}"#,
    );
    cross_cutting_scan(&run, 7);
}

#[test]
fn typed_audit_reads_resolve_all_supported_pr_descriptions() {
    let pulls = json!([
        audit_pull_request(
            11,
            "ordinary implementation",
            "Fixes #1",
            Some("2026-08-09T10:00:00Z"),
        ),
        audit_pull_request(
            12,
            "ordinary implementation follow-up",
            "Fixes #2",
            Some("2026-08-09T11:00:00Z"),
        ),
        audit_pull_request(
            13,
            "chore(larch-logs): design run ABCDEF01-2345-6789-ABCD-EF0123456789",
            "",
            Some("2026-08-09T12:00:00Z"),
        ),
    ]);
    let prior = audit_issue(
        90,
        "[Run Logs Audit 2026 Report]",
        "---\naudited_pr_range:\n  last: '11'\n---\n",
    );
    let server = IssueServiceStub::start([
        IssueServiceExchange::any_json(200, pulls.to_string()).expect("last PR listing"),
        IssueServiceExchange::any_json(200, pulls.to_string()).expect("since PR listing"),
        IssueServiceExchange::any_json(
            200,
            audit_pull_request(
                12,
                "ordinary implementation follow-up",
                "Fixes #2",
                Some("2026-08-09T11:00:00Z"),
            )
            .to_string(),
        )
        .expect("explicit PR"),
        IssueServiceExchange::any_json(200, json!([prior.clone()]).to_string())
            .expect("prior audit list"),
        IssueServiceExchange::any_json(200, prior.to_string()).expect("prior audit body"),
        IssueServiceExchange::any_json(
            200,
            audit_pull_request(
                11,
                "ordinary implementation",
                "Fixes #1",
                Some("2026-08-09T10:00:00Z"),
            )
            .to_string(),
        )
        .expect("prior PR"),
        IssueServiceExchange::any_json(200, pulls.to_string()).expect("post-audit PR listing"),
    ])
    .expect("GitHub loopback");
    let service = loopback_service(server.base_url().to_owned());

    with_test_github_service(service, || {
        let repo = repository_ref("o/r").expect("repository ref");
        let resolve = |verbal: &str| {
            with_github_service(async |service, cancellation| {
                resolve_prs_remote(service, cancellation, &repo, "implement", verbal).await
            })
            .expect("typed GitHub service")
        };

        let last = resolve("last 2 PRs");
        assert_eq!(last.numbers, [11, 12]);
        assert!(!last.implicit);

        let since = resolve("since 2026-08-09T10:30:00Z");
        assert_eq!(since.numbers, [12]);

        let explicit = resolve("PR #12");
        assert_eq!(explicit.numbers, [12]);

        let implicit = resolve("");
        assert!(implicit.implicit);
        assert_eq!(implicit.prior, "90");
        assert_eq!(implicit.numbers, [12]);
    });
    assert_eq!(server.finish().expect("recorded requests").len(), 7);
}

#[test]
fn mapping_uses_typed_pr_reads_for_implement_and_design_archives() {
    let temporary = tempdir().expect("temporary run corpus");
    let implement_root = temporary.path().join("larch-logs/implement");
    let parent = implement_root.join("parent-match");
    let fallback = implement_root.join("manifest-match");
    let tied_one = implement_root.join("ambiguous-one");
    let tied_two = implement_root.join("ambiguous-two");
    for directory in [&parent, &fallback, &tied_one, &tied_two] {
        fs::create_dir_all(directory).expect("run directory");
    }
    write(&parent, "parent-issue.md", "ISSUE_NUMBER=12\n");
    write(
        &parent,
        "manifest.json",
        r#"{"started_at":"2026-08-09T12:00:00Z","larch_version":"56.2.2"}"#,
    );
    write(
        &fallback,
        "manifest.json",
        r#"{"started_at":"2026-08-09T13:00:00Z","larch_version":"56.2.3","pr_number":9,"closes_issue":"13"}"#,
    );
    for directory in [&tied_one, &tied_two] {
        write(directory, "parent-issue.md", "ISSUE_NUMBER=14\n");
        write(
            directory,
            "manifest.json",
            r#"{"started_at":"2026-08-09T14:00:00Z","larch_version":"56.2.4"}"#,
        );
    }

    let server = IssueServiceStub::start([
        IssueServiceExchange::any_json(
            200,
            audit_pull_request(
                8,
                "ordinary implementation",
                "Fixes #12",
                Some("2026-08-09T12:00:00Z"),
            )
            .to_string(),
        )
        .expect("parent PR"),
        IssueServiceExchange::any_json(
            200,
            audit_pull_request(
                9,
                "ordinary implementation",
                "No closing issue wire",
                Some("2026-08-09T13:00:00Z"),
            )
            .to_string(),
        )
        .expect("fallback PR"),
        IssueServiceExchange::any_json(
            200,
            audit_pull_request(
                10,
                "ordinary implementation",
                "Closes #14",
                Some("2026-08-09T14:00:00Z"),
            )
            .to_string(),
        )
        .expect("ambiguous PR"),
        IssueServiceExchange::any_json(200, "{}").expect("malformed PR response"),
    ])
    .expect("GitHub loopback");
    let service = loopback_service(server.base_url().to_owned());
    let implementation_arguments = vec![
        OsString::from("--skill"),
        OsString::from("implement"),
        OsString::from("--pr-list"),
        OsString::from("8,9,10,11"),
        OsString::from("--repo"),
        OsString::from("o/r"),
        OsString::from("--log-root"),
        implement_root.into_os_string(),
    ];
    with_test_github_service(service, || {
        assert_eq!(map_runs(&implementation_arguments), ExitCode::SUCCESS);
    });
    assert_eq!(server.finish().expect("recorded requests").len(), 4);

    let design_root = temporary.path().join("larch-logs/design");
    let design_id = "ABCDEF01-2345-6789-ABCD-EF0123456789";
    write(
        &design_root.join(design_id),
        "manifest.json",
        r#"{"started_at":"2026-08-09T15:00:00Z","larch_version":"56.2.5"}"#,
    );
    let server = IssueServiceStub::start([IssueServiceExchange::any_json(
        200,
        audit_pull_request(
            13,
            &format!("chore(larch-logs): design run {design_id}"),
            "",
            Some("2026-08-09T15:00:00Z"),
        )
        .to_string(),
    )
    .expect("design PR")])
    .expect("GitHub loopback");
    let service = loopback_service(server.base_url().to_owned());
    let design_arguments = vec![
        OsString::from("--skill"),
        OsString::from("design"),
        OsString::from("--pr-list"),
        OsString::from("13"),
        OsString::from("--repo"),
        OsString::from("o/r"),
        OsString::from("--log-root"),
        design_root.into_os_string(),
    ];
    with_test_github_service(service, || {
        assert_eq!(map_runs(&design_arguments), ExitCode::SUCCESS);
    });
    assert_eq!(server.finish().expect("recorded requests").len(), 1);
}

#[test]
fn preflight_and_command_input_failures_keep_the_legacy_success_wires() {
    assert_eq!(
        preflight(&arguments(&["--skill", "unknown"])),
        ExitCode::SUCCESS
    );
    assert_eq!(
        preflight(&arguments(&[
            "--skill",
            "implement",
            "--repo",
            "not-a-slug"
        ])),
        ExitCode::SUCCESS
    );
    assert_eq!(
        resolve_prs(&arguments(&[
            "--skill",
            "implement",
            "--repo",
            "not-a-slug"
        ])),
        ExitCode::SUCCESS
    );
    assert_eq!(
        map_runs(&arguments(&[
            "--skill",
            "implement",
            "--pr-list",
            "not-a-number"
        ])),
        ExitCode::FAILURE
    );
}

#[test]
fn compatibility_verb_boundaries_keep_help_and_input_errors_stable() {
    for verb in [
        "preflight",
        "resolve-prs",
        "map-runs",
        "scan-run",
        "compute-counters",
        "pacific-timestamp",
    ] {
        assert_eq!(audit_help(verb), ExitCode::SUCCESS);
    }
    assert_eq!(preflight(&arguments(&["--help"])), ExitCode::SUCCESS);
    assert_ne!(preflight(&arguments(&[])), ExitCode::SUCCESS);
    assert_ne!(
        preflight(&arguments(&["--skill", "implement", "--unexpected"])),
        ExitCode::SUCCESS
    );
    assert_eq!(pacific_timestamp(&[]), ExitCode::SUCCESS);

    assert_eq!(resolve_prs(&arguments(&["--help"])), ExitCode::SUCCESS);
    assert_ne!(resolve_prs(&arguments(&[])), ExitCode::SUCCESS);
    assert_ne!(
        resolve_prs(&arguments(&["--skill", "unexpected"])),
        ExitCode::SUCCESS
    );

    let temporary = tempdir().expect("temporary command directory");
    let root = temporary.path().join("larch-logs/implement");
    let missing_directory = temporary.path().join("missing");
    fs::create_dir_all(&root).expect("log root");
    assert_eq!(map_runs(&arguments(&["--help"])), ExitCode::SUCCESS);
    assert_ne!(map_runs(&arguments(&[])), ExitCode::SUCCESS);
    assert_eq!(
        map_runs(&[
            OsString::from("--skill"),
            OsString::from("implement"),
            OsString::from("--pr-list"),
            OsString::from("bad-token"),
            OsString::from("--log-root"),
            root.into_os_string(),
        ]),
        ExitCode::SUCCESS
    );

    assert_eq!(compute_counters(&arguments(&["--help"])), ExitCode::SUCCESS);
    assert_ne!(compute_counters(&arguments(&[])), ExitCode::SUCCESS);
    assert_ne!(
        compute_counters(&[
            OsString::from("--scan-results-dir"),
            missing_directory.into_os_string(),
        ]),
        ExitCode::SUCCESS
    );

    assert_eq!(scan_run(&arguments(&["--help"])), ExitCode::SUCCESS);
    assert_ne!(scan_run(&arguments(&[])), ExitCode::SUCCESS);
    assert_ne!(
        scan_run(&arguments(&[
            "--skill",
            "unexpected",
            "--pr",
            "7",
            "--scans-tsv",
            "missing.tsv",
        ])),
        ExitCode::SUCCESS
    );
    assert_ne!(
        scan_run(&arguments(&[
            "--skill",
            "implement",
            "--pr",
            "7",
            "--scans-tsv",
            "missing.tsv",
        ])),
        ExitCode::SUCCESS
    );
}

#[test]
fn resolve_command_prints_the_typed_last_pr_result() {
    let server = IssueServiceStub::start([IssueServiceExchange::any_json(
        200,
        json!([audit_pull_request(
            12,
            "ordinary implementation",
            "Fixes #2",
            Some("2026-08-09T12:00:00Z"),
        )])
        .to_string(),
    )
    .expect("last PR listing")])
    .expect("GitHub loopback");
    let service = loopback_service(server.base_url().to_owned());
    with_test_github_service(service, || {
        assert_eq!(
            resolve_prs(&arguments(&[
                "--skill",
                "implement",
                "--repo",
                "o/r",
                "--verbal-description",
                "last 1 PR",
            ])),
            ExitCode::SUCCESS
        );
    });
    assert_eq!(server.finish().expect("recorded requests").len(), 1);
}

#[test]
fn typed_audit_resolution_rejects_each_ambiguous_or_incomplete_range() {
    let prior = audit_issue(
        90,
        "[Run Logs Audit 2026 Report]",
        "---\naudited_pr_range:\n  last: '11'\n---\n",
    );
    let no_new_pulls = json!([audit_pull_request(
        11,
        "ordinary implementation",
        "Fixes #1",
        Some("2026-08-09T10:00:00Z"),
    )]);
    let server = IssueServiceStub::start([
        IssueServiceExchange::any_json(200, "[]").expect("no prior audit"),
        IssueServiceExchange::any_json(200, json!([prior.clone()]).to_string())
            .expect("malformed prior list"),
        IssueServiceExchange::any_json(
            200,
            audit_issue(90, "[Run Logs Audit 2026 Report]", "not frontmatter").to_string(),
        )
        .expect("malformed prior body"),
        IssueServiceExchange::any_json(200, json!([prior.clone()]).to_string())
            .expect("unmerged prior list"),
        IssueServiceExchange::any_json(200, prior.clone().to_string()).expect("unmerged prior"),
        IssueServiceExchange::any_json(
            200,
            audit_pull_request(11, "ordinary implementation", "", None).to_string(),
        )
        .expect("unmerged PR"),
        IssueServiceExchange::any_json(200, json!([prior.clone()]).to_string())
            .expect("no-new prior list"),
        IssueServiceExchange::any_json(200, prior.to_string()).expect("no-new prior"),
        IssueServiceExchange::any_json(
            200,
            audit_pull_request(
                11,
                "ordinary implementation",
                "",
                Some("2026-08-09T10:00:00Z"),
            )
            .to_string(),
        )
        .expect("no-new prior PR"),
        IssueServiceExchange::any_json(200, no_new_pulls.to_string()).expect("no-new listing"),
        IssueServiceExchange::any_json(200, "[]").expect("empty last range"),
        IssueServiceExchange::any_json(200, "[]").expect("empty since range"),
        IssueServiceExchange::any_json(
            200,
            audit_pull_request(12, "", "", Some("2026-08-09T12:00:00Z")).to_string(),
        )
        .expect("empty explicit title"),
        IssueServiceExchange::any_json(
            200,
            audit_pull_request(
                13,
                "chore(larch-logs): design run ABCDEF01-2345-6789-ABCD-EF0123456789",
                "",
                Some("2026-08-09T12:00:00Z"),
            )
            .to_string(),
        )
        .expect("wrong explicit title"),
    ])
    .expect("GitHub loopback");
    let service = loopback_service(server.base_url().to_owned());

    with_test_github_service(service, || {
        let repo = repository_ref("o/r").expect("repository ref");
        let resolve_error = |verbal: &str| {
            with_github_service(async |service, cancellation| {
                resolve_prs_remote(service, cancellation, &repo, "implement", verbal).await
            })
            .expect_err("incomplete range must fail")
            .into_detail()
        };

        assert!(resolve_error("since last audit").contains("no prior audit-report"));
        assert!(resolve_error("since last audit").contains("malformed or missing frontmatter"));
        assert!(resolve_error("since last audit").contains("could not get mergedAt"));
        assert!(resolve_error("since last audit").contains("no new PRs merged"));
        assert!(resolve_error("last 1 PR").contains("empty PR list"));
        assert!(resolve_error("since 2026-08-09").contains("must be a full instant"));
        assert!(resolve_error("since 2026-08-09T12:00:00Z").contains("no PRs merged after"));
        assert!(resolve_error("#12").contains("could not resolve PR #12 title"));
        assert!(resolve_error("#13").contains("does not match"));
        assert!(resolve_error("arbitrary prose").contains("unrecognized verbal description"));
    });
    assert_eq!(server.finish().expect("recorded requests").len(), 14);
}
