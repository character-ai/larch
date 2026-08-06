//! Offline coverage for the shared issue analysis core.
//!
//! Issue-side cases build their population from the issue-domain fixtures and
//! compare it through the issue parity oracle. Corpus cases build isolated
//! run-log trees and read them through the shared run-log walker.

use chrono::{DateTime, NaiveDate, Utc};
use larch_core::{
    CategoryMode, CorpusFilter, EvidenceIndex, EvidenceOrdering, EvidenceSource, GateFailure,
    GroundTruthEvidence, GroundTruthMode, GroundTruthRow, GroundTruthVoter, IncentiveEra,
    IssueCategory, IssueLifecycle, IssueSummary, NotLaterReason, OutcomeBucket, OutcomeDirection,
    PanelKind, PanelVerdict, VerdictGateInputs, VoterBallot, accepted_finding_evidence,
    analyze_ground_truth, apply_verdict_gate, candidate_evidence, categorize, category_breakdown,
    classify_in_scope, coverage_stats, diagnostic_paths, distinctive_tokens, evidence_ordering,
    issue_evidence, normalize_diagnostic_path, parse_timestamp, percentile,
    realized_alignment_rate, run_dir_key, scan_ground_truth_corpus, strip_prefixes, strong_match,
    title_tokens, version_components, version_meets_floor,
};
use larch_test_support::{
    ExecutionSnapshot, IssueFixture, IssueGraph, IssueGraphSnapshot, IssueParityOracle, IssueState,
};
use serde_json::{Value, json};
use std::{fs, path::Path};
use tempfile::TempDir;

fn timestamp(value: &str) -> DateTime<Utc> {
    DateTime::parse_from_rfc3339(value)
        .expect("fixture timestamp should parse")
        .with_timezone(&Utc)
}

fn date(value: &str) -> NaiveDate {
    NaiveDate::parse_from_str(value, "%Y-%m-%d").expect("fixture date should parse")
}

/// Build the analysis population from an issue-domain fixture graph, giving
/// each issue a deterministic creation date derived from its number.
fn fixture_population(graph: &IssueGraph) -> Vec<IssueSummary> {
    graph
        .issues()
        .map(|record| {
            let day = record.number % 28 + 1;
            let mut payload = json!({
                "number": record.number,
                "title": record.title,
                "body": record.body,
                "state": record.state.as_str().to_uppercase(),
                "labels": record.labels,
                "createdAt": format!("2026-03-{day:02}T00:00:00Z"),
            });
            if record.state == IssueState::Closed {
                payload["closedAt"] = Value::String(format!("2026-04-{day:02}T00:00:00Z"));
                payload["closedByPullRequestsReferences"] =
                    json!([{"url": format!("https://example.invalid/pull/{}", record.number)}]);
            }
            IssueSummary::from_json(&payload).expect("fixture issue should load")
        })
        .collect()
}

fn issue(number: u64, title: &str, body: &str, created_at: &str) -> IssueSummary {
    IssueSummary::from_json(&json!({
        "number": number,
        "title": title,
        "body": body,
        "state": "OPEN",
        "createdAt": created_at,
    }))
    .expect("issue should load")
}

fn row(finding_id: &str, verdict: PanelVerdict, prose: &str) -> GroundTruthRow {
    GroundTruthRow {
        panel_kind: PanelKind::CodeReview,
        run_id: "run-1".to_owned(),
        run_dir_key: "implement/run-1".to_owned(),
        round_num: 1,
        started_at: Some(timestamp("2026-04-01T00:00:00Z")),
        run_ended_at: Some(timestamp("2026-04-02T00:00:00Z")),
        multi_round: false,
        finding_id: finding_id.to_owned(),
        title: "Redaction misses the token suffix".to_owned(),
        prose_text: prose.to_owned(),
        category: "Bug fix".to_owned(),
        verdict,
        weak_reason: None,
        voters: vec![
            GroundTruthVoter {
                voter: "voter-1".to_owned(),
                ballot: VoterBallot::Yes,
                severity: "HIGH".to_owned(),
            },
            GroundTruthVoter {
                voter: "voter-2".to_owned(),
                ballot: VoterBallot::No,
                severity: String::new(),
            },
            GroundTruthVoter {
                voter: "voter-3".to_owned(),
                ballot: VoterBallot::Missing,
                severity: String::new(),
            },
        ],
    }
}

fn evidence(source: EvidenceSource, title: &str, text: &str) -> GroundTruthEvidence {
    GroundTruthEvidence {
        source,
        run_id: String::new(),
        run_dir_key: String::new(),
        round_num: 0,
        started_at: None,
        created_at: Some(timestamp("2026-05-01T00:00:00Z")),
        title: title.to_owned(),
        text: text.to_owned(),
        category: "Bug fix".to_owned(),
        issue_number: Some(42),
        not_planned: false,
    }
}

fn write_file(root: &Path, relative: &str, body: &str) {
    let path = root.join(relative);
    fs::create_dir_all(path.parent().expect("fixture path has a parent"))
        .expect("fixture directory should be creatable");
    fs::write(path, body).expect("fixture file should be writable");
}

#[test]
fn fixture_population_categorizes_and_covers_deterministically() {
    let graph = IssueGraph::builder(IssueFixture::Committed)
        .build()
        .expect("issue fixture should build");
    let issues = fixture_population(&graph);
    let categories = categorize(&issues, CategoryMode::Default, 10);

    assert_eq!(issues.len(), 5);
    assert_eq!(
        issues
            .iter()
            .map(|issue| issue.default_category().as_str())
            .collect::<Vec<_>>(),
        ["Test coverage"; 5],
        "every committed fixture body names a fixture, so one rule wins"
    );
    assert_eq!(
        category_breakdown(&issues, &categories)
            .iter()
            .map(|row| (row.label.clone(), row.count))
            .collect::<Vec<_>>(),
        [("Test coverage".to_owned(), 5)]
    );
    let stats = coverage_stats(&issues);
    assert_eq!((stats.total, stats.open, stats.closed), (5, 4, 1));
    assert_eq!(stats.oldest, Some(date("2026-03-17")));
    assert_eq!(stats.newest, Some(date("2026-03-21")));
    assert_eq!(stats.median_close_days, Some(31.0));
    assert!((stats.pr_closed_pct - 100.0).abs() < f64::EPSILON);
}

#[test]
fn issue_fixture_snapshots_agree_and_expose_injected_differences() {
    let left = IssueGraph::builder(IssueFixture::Committed)
        .build()
        .expect("issue fixture should build");
    let right = IssueGraph::builder(IssueFixture::Committed)
        .build()
        .expect("issue fixture should build");
    let oracle = IssueParityOracle::new();
    let left_snapshot = IssueGraphSnapshot::capture(&left, ExecutionSnapshot::success());
    let right_snapshot = IssueGraphSnapshot::capture(&right, ExecutionSnapshot::success());

    assert!(
        oracle
            .compare_graphs(&left_snapshot, &right_snapshot)
            .is_empty()
    );
    // Fixture bodies embed their own temporary root, so the derived indexes,
    // not the raw records, are what must not vary between roots.
    let left_issues = fixture_population(&left);
    let right_issues = fixture_population(&right);
    assert_eq!(
        categorize(&left_issues, CategoryMode::Default, 10),
        categorize(&right_issues, CategoryMode::Default, 10)
    );
    assert_eq!(coverage_stats(&left_issues), coverage_stats(&right_issues));

    let conflicting = IssueGraph::builder(IssueFixture::Conflicting)
        .build()
        .expect("issue fixture should build");
    let conflicting_snapshot =
        IssueGraphSnapshot::capture(&conflicting, ExecutionSnapshot::success());
    assert!(
        !oracle
            .compare_graphs(&left_snapshot, &conflicting_snapshot)
            .is_empty()
    );
}

#[test]
fn default_category_honors_rule_order_stems_and_strict_words() {
    let cases = [
        (
            "Tracking issue",
            "Tracking issue for /implement\n\nOriginal prompt: go",
            IssueCategory::TrackingUmbrella,
        ),
        (
            "[RESEARCH v2] Investigate the docs",
            "body",
            IssueCategory::ResearchInvestigation,
        ),
        ("Bugs in the parser", "body", IssueCategory::BugFix),
        (
            "Validation of the payload",
            "body",
            IssueCategory::HardeningValidationSecurity,
        ),
        (
            "Determinism of the walker",
            "body",
            IssueCategory::DeterminismHaltPrevention,
        ),
        ("Prefix affix suffix", "body", IssueCategory::Other),
        ("Docker build", "body", IssueCategory::Other),
        (
            "Simplify the launcher",
            "body",
            IssueCategory::RefactorCodeClarity,
        ),
        (
            "Reduce token cost",
            "body",
            IssueCategory::PerformanceTokenCostReduction,
        ),
    ];
    for (title, body, expected) in cases {
        let summary = issue(1, title, body, "2026-03-01T00:00:00Z");
        assert_eq!(summary.default_category(), expected, "title: {title}");
    }
    assert_eq!(
        strip_prefixes("[DONE] [OOS] Fix the walker"),
        "Fix the walker"
    );
    assert_eq!(
        title_tokens("[STALLED] The redaction walker and its fixture"),
        ["redaction", "walker", "its", "fixture"]
    );
}

#[test]
fn auto_categorization_ranks_leaders_and_breaks_ties_by_first_appearance() {
    let issues: Vec<IssueSummary> = vec![
        issue(1, "walker redaction fails", "", "2026-03-01T00:00:00Z"),
        issue(2, "walker timeout", "", "2026-03-02T00:00:00Z"),
        issue(3, "redaction gap", "", "2026-03-03T00:00:00Z"),
        issue(4, "unrelated concern", "", "2026-03-04T00:00:00Z"),
    ];
    let categories = categorize(&issues, CategoryMode::Auto, 1);

    assert_eq!(categories.label_for(1).label(), "Auto: walker");
    assert_eq!(categories.label_for(2).label(), "Auto: walker");
    assert_eq!(categories.label_for(3).label(), "Other");
    assert_eq!(categories.label_for(4).label(), "Other");
    assert_eq!(categories.len(), 4);
    assert_eq!(categorize(&issues, CategoryMode::Auto, 1), categories);

    // Leader ranking breaks ties by first appearance in issue order, so a
    // reordered population moves the tie deterministically instead of by hash.
    let mut reordered = issues;
    reordered.reverse();
    assert_eq!(
        categorize(&reordered, CategoryMode::Auto, 1)
            .label_for(1)
            .label(),
        "Auto: redaction"
    );
}

#[test]
fn percentiles_interpolate_and_tolerate_degenerate_populations() {
    assert_eq!(percentile(&[], 50.0), None);
    assert_eq!(percentile(&[4.0], 90.0), Some(4.0));
    assert_eq!(percentile(&[1.0, 2.0, 3.0, 4.0], 50.0), Some(2.5));
    assert_eq!(percentile(&[1.0, 2.0, 3.0, 4.0], 0.0), Some(1.0));
    assert_eq!(percentile(&[1.0, 2.0, 3.0, 4.0], 100.0), Some(4.0));
    assert_eq!(coverage_stats(&[]).median_close_days, None);
    assert!(coverage_stats(&[]).pr_closed_pct.abs() < f64::EPSILON);

    // Python divides total_seconds(), so sub-second lifetimes must survive.
    let subsecond = IssueSummary::from_json(&json!({
        "number": 1,
        "state": "CLOSED",
        "createdAt": "2026-01-01T00:00:00.000000Z",
        "closedAt": "2026-01-02T00:00:00.900000Z",
    }))
    .expect("issue loads");
    let median = coverage_stats(&[subsecond])
        .median_close_days
        .expect("one closed issue yields a median");
    assert!(
        (median - 1.000_010_416_666_666_7).abs() < 1e-12,
        "median: {median}"
    );
}

#[test]
fn issue_records_reject_unusable_numbers_and_read_not_planned_signals() {
    assert_eq!(IssueSummary::from_json(&json!("scalar")), None);
    assert_eq!(IssueSummary::from_json(&json!({"number": 0})), None);
    assert_eq!(IssueSummary::from_json(&json!({"number": "12a"})), None);
    assert_eq!(IssueSummary::from_json(&json!({"number": true})), None);
    let parsed = IssueSummary::from_json(&json!({"number": "12"})).expect("digit string loads");
    assert_eq!(parsed.number, 12);
    assert_eq!(parsed.state, IssueLifecycle::Unknown);

    // Python never trims `state`, so a padded value stays unclassified.
    let padded = IssueSummary::from_json(&json!({"number": 13, "state": " OPEN"}))
        .expect("padded state loads");
    assert_eq!(padded.state, IssueLifecycle::Unknown);
    assert_eq!(coverage_stats(&[padded]).open, 0);

    // Python coerces truthy label scalars through `str(value)` and drops falsy
    // ones, so a numeric or boolean label still reaches the label set.
    let labelled = IssueSummary::from_json(&json!({
        "number": 5,
        "labels": [{"name": " WontFix "}, "not-planned", 7, {"name": 5}, 0, false, null],
    }))
    .expect("labels load");
    assert_eq!(labelled.labels, ["wontfix", "not-planned", "7", "5"]);
    assert!(labelled.not_planned());

    let degraded = IssueSummary::from_json(&json!({
        "number": 6,
        "stateReason": "not_planned",
        "_larch_degraded_fields": ["stateReason"],
    }))
    .expect("degraded record loads");
    assert!(!degraded.not_planned());

    let body_signal =
        IssueSummary::from_json(&json!({"number": 7, "body": "We have no plan to fix this."}))
            .expect("body record loads");
    assert!(body_signal.not_planned());
}

#[test]
fn diagnostic_paths_normalize_line_hints_and_reject_escapes() {
    assert_eq!(
        normalize_diagnostic_path("`./python/larch/io.py:42`"),
        "python/larch/io.py"
    );
    assert_eq!(normalize_diagnostic_path("a/../b.py"), "");
    assert_eq!(normalize_diagnostic_path("~/secrets.py"), "");
    assert_eq!(normalize_diagnostic_path("..."), "");

    // Python keeps the leading separator and any line hint that a trailing
    // separator un-anchors. Both sides of a match run through the same rule, so
    // this leaf preserves the artifact rather than changing which rows match.
    let paths = diagnostic_paths("see python/larch/io.py:42 and Makefile:7 for detail");
    assert!(
        paths.contains(" python/larch/io.py:42 "),
        "paths: {paths:?}"
    );
    assert!(paths.contains(" makefile"), "paths: {paths:?}");
    assert!(diagnostic_paths("no references here").is_empty());
    assert_eq!(
        distinctive_tokens("Redaction walker fails"),
        ["fails", "redaction", "walker"]
            .into_iter()
            .map(str::to_owned)
            .collect()
    );
}

#[test]
fn strong_match_requires_path_or_token_agreement() {
    let subject = row(
        "FINDING_1",
        PanelVerdict::Rejected,
        "python/larch/io.py:12 leaks the token suffix",
    );
    let sharing_path = evidence(
        EvidenceSource::Issue,
        "Token suffix leak",
        "python/larch/io.py still leaks the suffix",
    );
    let unrelated = evidence(
        EvidenceSource::Issue,
        "Unrelated cache warmup",
        "nothing in common at all",
    );

    assert!(strong_match(&subject, &sharing_path));
    assert!(!strong_match(&subject, &unrelated));
}

#[test]
fn evidence_ordering_proves_or_refuses_every_ordering_channel() {
    let mut subject = row("FINDING_1", PanelVerdict::Accepted, "prose");
    let mut same_run = evidence(EvidenceSource::AcceptedFinding, "later", "later");
    same_run.run_dir_key = "implement/run-1".to_owned();
    same_run.round_num = 2;
    assert_eq!(
        evidence_ordering(&subject, &same_run),
        EvidenceOrdering::Later
    );

    same_run.round_num = 1;
    assert_eq!(
        evidence_ordering(&subject, &same_run),
        EvidenceOrdering::NotLater(NotLaterReason::SameRunNotLater)
    );

    let mut other_panel = same_run;
    other_panel.run_dir_key = "design/run-9".to_owned();
    assert_eq!(
        evidence_ordering(&subject, &other_panel),
        EvidenceOrdering::NotLater(NotLaterReason::PanelRootMismatch)
    );

    let later_issue = evidence(EvidenceSource::Issue, "later", "later");
    assert_eq!(
        evidence_ordering(&subject, &later_issue),
        EvidenceOrdering::Later
    );

    let mut earlier_issue = later_issue.clone();
    earlier_issue.created_at = Some(timestamp("2026-03-01T00:00:00Z"));
    assert_eq!(
        evidence_ordering(&subject, &earlier_issue),
        EvidenceOrdering::NotLater(NotLaterReason::NotLater)
    );

    subject.multi_round = true;
    subject.run_ended_at = Some(timestamp("2026-06-01T00:00:00Z"));
    assert_eq!(
        evidence_ordering(&subject, &later_issue),
        EvidenceOrdering::NotLater(NotLaterReason::SameRunUnproved)
    );

    subject.started_at = None;
    assert_eq!(
        evidence_ordering(&subject, &later_issue),
        EvidenceOrdering::NotLater(NotLaterReason::TimestampDegraded)
    );
}

#[test]
fn classification_buckets_separate_weak_degraded_and_realized_outcomes() {
    let mut weak = row("FINDING_1", PanelVerdict::Accepted, "prose");
    weak.weak_reason = Some("TSV/prose verdict disagreement".to_owned());
    assert_eq!(
        classify_in_scope(&weak, &[], None).bucket,
        OutcomeBucket::WeakProseVerdict
    );

    let missing = row("FINDING_2", PanelVerdict::Missing, "prose");
    assert_eq!(
        classify_in_scope(&missing, &[], None).bucket,
        OutcomeBucket::WeakPanelVerdict
    );

    let accepted = row(
        "FINDING_3",
        PanelVerdict::Accepted,
        "python/larch/io.py:12 leaks the token suffix",
    );
    let reversal = evidence(
        EvidenceSource::Issue,
        "Revert the token suffix redaction",
        "python/larch/io.py reverted the suffix change",
    );
    assert_eq!(
        classify_in_scope(&accepted, std::slice::from_ref(&reversal), None).bucket,
        OutcomeBucket::AcceptedRevertedOrRegressed
    );
    assert_eq!(
        classify_in_scope(
            &accepted,
            std::slice::from_ref(&reversal),
            Some("gh rate limit")
        )
        .bucket,
        OutcomeBucket::EnrichmentDegradedReversal
    );
    assert_eq!(
        classify_in_scope(&accepted, &[], None).bucket,
        OutcomeBucket::AcceptedNoCounterevidence
    );

    let rejected = row(
        "FINDING_4",
        PanelVerdict::Rejected,
        "python/larch/io.py:12 leaks the token suffix",
    );
    let resurfacing = evidence(
        EvidenceSource::Issue,
        "Fix the token suffix leak",
        "python/larch/io.py still leaks the suffix",
    );
    assert_eq!(
        classify_in_scope(&rejected, std::slice::from_ref(&resurfacing), None).bucket,
        OutcomeBucket::RejectedResurfaced
    );
    assert_eq!(
        classify_in_scope(
            &rejected,
            std::slice::from_ref(&resurfacing),
            Some("gh rate limit")
        )
        .bucket,
        OutcomeBucket::EnrichmentDegradedResurfacing
    );

    let mut not_planned = resurfacing.clone();
    not_planned.not_planned = true;
    assert_eq!(
        classify_in_scope(&rejected, &[not_planned], None).bucket,
        OutcomeBucket::RejectedNotObserved
    );

    let mut undated = resurfacing;
    undated.created_at = None;
    let outcome = classify_in_scope(&rejected, &[undated], None);
    assert_eq!(outcome.bucket, OutcomeBucket::RejectedNotObserved);
    assert_eq!(outcome.timestamp_degraded_matches, 1);
}

#[test]
fn analysis_indexes_evidence_and_scores_every_voter() {
    let rejected = row(
        "FINDING_1",
        PanelVerdict::Rejected,
        "python/larch/io.py:12 leaks the token suffix",
    );
    let issues = vec![issue(
        42,
        "Fix the token suffix leak",
        "python/larch/io.py still leaks the suffix",
        "2026-05-01T00:00:00Z",
    )];
    let analysis = analyze_ground_truth(std::slice::from_ref(&rejected), &issues, None);

    assert_eq!(analysis.outcomes.len(), 1);
    assert_eq!(
        analysis.outcomes[0].bucket,
        OutcomeBucket::RejectedResurfaced
    );
    assert_eq!(
        analysis.outcomes[0].direction(),
        OutcomeDirection::SupportsAcceptance
    );
    assert_eq!(analysis.stats.decisive_rows, 1);
    assert_eq!(analysis.stats.weak_rows, 0);
    assert_eq!(
        analysis
            .stats
            .buckets
            .get(&OutcomeBucket::RejectedResurfaced),
        Some(&1)
    );
    assert!(!analysis.stats.large_corpus_skip);

    let metrics: Vec<_> = analysis
        .metrics
        .iter()
        .map(|metric| {
            (
                metric.voter.as_str(),
                metric.decisive,
                metric.aligned,
                metric.misaligned,
                metric.missing,
                metric.false_negative_no,
            )
        })
        .collect();
    assert_eq!(
        metrics,
        [
            ("voter-1", 1, 1, 0, 0, 0),
            ("voter-2", 1, 0, 1, 0, 1),
            ("voter-3", 0, 0, 0, 1, 0),
        ]
    );
    assert_eq!(analysis.severity_metrics.len(), 1);
    assert_eq!(analysis.severity_metrics[0].severity, "HIGH");
    assert_eq!(analysis.severity_metrics[0].decisive_yes, 1);
    assert_eq!(analysis.severity_metrics[0].missing_severity, 0);

    assert_eq!(realized_alignment_rate(0, 0), None);
    assert_eq!(realized_alignment_rate(3, 1), Some(0.75));

    let degraded = analyze_ground_truth(&[rejected], &issues, Some("gh rate limit"));
    assert_eq!(degraded.stats.enrichment_degraded_rows, 1);
    assert_eq!(
        degraded.outcomes[0].bucket,
        OutcomeBucket::EnrichmentDegradedResurfacing
    );
}

#[test]
fn candidate_selection_filters_by_overlap_and_panel_root() {
    let subject = row(
        "FINDING_1",
        PanelVerdict::Rejected,
        "python/larch/io.py:12 leaks the token suffix",
    );
    let issues = vec![
        issue(
            1,
            "Fix the token suffix leak",
            "python/larch/io.py still leaks the suffix",
            "2026-05-01T00:00:00Z",
        ),
        issue(
            2,
            "Totally unrelated",
            "nothing shared",
            "2026-05-01T00:00:00Z",
        ),
    ];
    let mut accepted_row = row(
        "FINDING_9",
        PanelVerdict::Accepted,
        "token suffix redaction leak",
    );
    accepted_row.run_dir_key = "design/run-2".to_owned();
    let accepted = EvidenceIndex::build(accepted_finding_evidence(std::slice::from_ref(
        &accepted_row,
    )));
    let indexed_issues = EvidenceIndex::build(issue_evidence(&issues));
    let candidates = candidate_evidence(&subject, &indexed_issues, &accepted);

    assert_eq!(candidates.len(), 1);
    assert_eq!(candidates[0].issue_number, Some(1));
    assert_eq!(
        candidate_evidence(&subject, &indexed_issues, &accepted),
        candidates
    );
    // The index carries each item's profile so the per-row filter never re-runs
    // the token and path extraction.
    assert_eq!(indexed_issues.len(), 2);
    assert!(
        indexed_issues
            .profile(0)
            .expect("indexed issue has a profile")
            .tokens()
            .contains("suffix")
    );
    assert_eq!(indexed_issues.positions("suffix"), [0]);
    assert!(EvidenceIndex::build(Vec::new()).is_empty());

    let mut weak_accepted = accepted_row;
    weak_accepted.weak_reason = Some("weak".to_owned());
    assert!(accepted_finding_evidence(&[weak_accepted]).is_empty());
}

#[test]
fn version_floors_and_the_verdict_gate_reject_in_precedence_order() {
    assert_eq!(version_components("v52.1.0-beta"), Some(vec![52, 1, 0]));
    assert_eq!(version_components("52.1"), Some(vec![52, 1, 0]));
    assert_eq!(version_components("beta"), None);
    assert_eq!(version_components(""), None);
    assert!(version_meets_floor("52.1.0", "52.1.0"));
    assert!(!version_meets_floor("52.0.9", "52.1.0"));
    assert!(!version_meets_floor("beta", "52.1.0"));

    let inputs = VerdictGateInputs {
        enrichment_degraded: false,
        targeted_fetch_degraded: false,
        qualifying_runs: 200,
        min_runs: 150,
    };
    assert_eq!(apply_verdict_gate(IncentiveEra::Shipped, inputs), None);
    assert_eq!(
        apply_verdict_gate(IncentiveEra::NotShipped, inputs),
        Some(GateFailure::CalibrationIncentiveNotShipped)
    );
    // An unreachable incentive issue is a distinct reason token in Python.
    assert_eq!(
        apply_verdict_gate(IncentiveEra::CheckUnavailable, inputs).map(GateFailure::as_str),
        Some("calibration_incentive_check_unavailable")
    );
    assert_eq!(
        apply_verdict_gate(
            IncentiveEra::Shipped,
            VerdictGateInputs {
                enrichment_degraded: true,
                targeted_fetch_degraded: true,
                ..inputs
            }
        ),
        Some(GateFailure::EnrichmentAndTargetedFetchDegraded)
    );
    assert_eq!(
        apply_verdict_gate(
            IncentiveEra::Shipped,
            VerdictGateInputs {
                qualifying_runs: 1,
                ..inputs
            }
        ),
        Some(GateFailure::CorpusBelowMinRuns)
    );
}

/// Build a corpus holding one qualifying design run with two rounds, one
/// pre-since implement run, one garbage-collected run, one version-less review
/// run, and one unreadable manifest.
fn build_corpus_tree(root: &Path) {
    write_file(
        root,
        "design/run-design/manifest.json",
        r#"{"issue_number":1,"started_at":"2026-07-01T00:00:00Z","ended_at":"2026-07-02T00:00:00Z","larch_version":"52.1.0"}"#,
    );
    write_file(
        root,
        "design/run-design/plan-review/round-1/findings-classification.tsv",
        "ok\n",
    );
    write_file(
        root,
        "design/run-design/plan-review/round-2/findings-classification.tsv",
        "ok\n",
    );
    write_file(
        root,
        "implement/run-impl/manifest.json",
        r#"{"issue_number":2,"started_at":"2026-05-01T00:00:00Z","larch_version":"51.0.0"}"#,
    );
    write_file(
        root,
        "implement/run-impl/round-1/findings-classification.tsv",
        "ok\n",
    );
    write_file(
        root,
        "implement/run-gc/manifest.json",
        r#"{"issue_number":3,"started_at":"2026-07-05T00:00:00Z","larch_version":"52.2.0"}"#,
    );
    write_file(root, "implement/run-gc/gc-slimmed", "");
    write_file(
        root,
        "implement/run-gc/round-1/findings-classification.tsv",
        "ok\n",
    );
    write_file(
        root,
        "review/run-review/manifest.json",
        r#"{"issue_number":4,"started_at":"2026-07-06T00:00:00Z"}"#,
    );
    write_file(
        root,
        "review/run-review/review-findings-classification-round-1.tsv",
        "ok\n",
    );
    write_file(
        root,
        "review/run-review/review-findings-classification-round-2.tsv",
        "ok\n",
    );
    write_file(root, "implement/run-broken/manifest.json", "{");
}

#[test]
fn corpus_scan_is_ordered_classifies_gc_slimmed_runs_and_surfaces_warnings() {
    let temporary = TempDir::new().expect("temporary root");
    let root = temporary.path().join("larch-logs");
    build_corpus_tree(&root);

    let calibration = scan_ground_truth_corpus(
        &root,
        GroundTruthMode::Calibration,
        &CorpusFilter::default(),
    );
    assert_eq!(
        calibration
            .sources
            .iter()
            .map(|source| (source.panel_kind, source.run_id.as_str(), source.round_num))
            .collect::<Vec<_>>(),
        [
            (PanelKind::Design, "run-design", 1),
            (PanelKind::Design, "run-design", 2),
            (PanelKind::CodeReview, "run-impl", 1),
            (PanelKind::CodeReview, "run-review", 1),
            (PanelKind::CodeReview, "run-review", 2),
        ]
    );
    assert_eq!(calibration.stats.files_seen, 6);
    assert_eq!(calibration.stats.gc_slimmed_runs, 1);
    assert_eq!(calibration.stats.qualifying_runs, 0);
    assert!(!calibration.warnings.is_empty());
    assert!(calibration.sources[0].multi_round);
    assert!(!calibration.sources[2].multi_round);
    // Round-numbered filenames at the run root are not round directories, so a
    // standalone review run with two of them stays single-round.
    assert!(!calibration.sources[3].multi_round);
    assert!(!calibration.sources[4].multi_round);
    assert_eq!(
        calibration.sources[0].run_dir_key,
        "design/run-design".to_owned()
    );
    assert_eq!(
        calibration.sources[0].started_at,
        Some(timestamp("2026-07-01T00:00:00Z"))
    );
    assert_eq!(
        calibration.sources[0].run_ended_at,
        Some(timestamp("2026-07-02T00:00:00Z"))
    );

    let repeated = scan_ground_truth_corpus(
        &root,
        GroundTruthMode::Calibration,
        &CorpusFilter::default(),
    );
    assert_eq!(repeated.sources, calibration.sources);

    let verdict = scan_ground_truth_corpus(
        &root,
        GroundTruthMode::Verdict,
        &CorpusFilter {
            since_date: parse_timestamp("2026-06-26"),
            min_larch_version: Some("52.1.0".to_owned()),
        },
    );
    assert_eq!(
        verdict
            .sources
            .iter()
            .map(|source| source.run_id.as_str())
            .collect::<Vec<_>>(),
        ["run-design", "run-design"]
    );
    assert_eq!(verdict.stats.qualifying_runs, 1);
    assert_eq!(verdict.stats.excluded_pre_since_runs, 1);
    assert_eq!(verdict.stats.excluded_gc_slimmed_runs, 1);
    assert_eq!(verdict.stats.excluded_missing_version_runs, 1);
    assert_eq!(verdict.stats.files_seen, 2);

    assert_eq!(
        run_dir_key(&root.join("design/run-design"), &root),
        Some("design/run-design".to_owned())
    );
    assert_eq!(run_dir_key(Path::new("/elsewhere/run"), &root), None);
}
