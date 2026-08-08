//! Differential parity tests for the token scan and usage extraction layer.
//!
//! The `*-report.json` fixtures are recorded output of the Python owner
//! (`larch.report.tokens.build_report_from_ledgers`, `_full_json`, and
//! `_summary_json`) over the `*.jsonl` inputs in the same directory. Regenerate
//! them from Python whenever the owner's shape changes.

use larch_core::{
    RunLogSelection, RunLogSlug, TokenCorpusScan, TokenObservationKind, TokenObservations,
    TokenReportError, TokenScanEvent, TokenScanWarningKind, TokenVendor, VendorTotals,
    build_report_from_ledgers, effective_vendor_total, full_report, read_report_inputs,
    report_has_numeric_tokens, resolve_run_report, run_log_ledger_path, safe_int, summary_report,
    token_phase_rows, token_report_basename, transcript_sources, vendor_totals_from_report,
};
use serde_json::{Map, Value, json};
use std::{fs, path::Path, path::PathBuf};
use tempfile::TempDir;

const LEDGER: &str = include_str!("fixtures/token_scan/ledger.jsonl");
const REROUTE_LEDGER: &str = include_str!("fixtures/token_scan/reroute-ledger.jsonl");
const TRANSCRIPT: &str = include_str!("fixtures/token_scan/transcript.jsonl");
const LEDGER_REPORT: &str = include_str!("fixtures/token_scan/ledger-report.json");
const REROUTE_REPORT: &str = include_str!("fixtures/token_scan/reroute-report.json");
const FULL_REPORT: &str = include_str!("fixtures/token_scan/full-report.json");
const SUMMARY_REPORT: &str = include_str!("fixtures/token_scan/summary-report.json");
const MANIFEST: &str = "{\"schema_version\":2,\"run_id\":\"11111111-2222-4333-8444-555555555555\",\
    \"skill\":\"implement\",\"issue_number\":8086,\"title\":\"Port the token scan layer\",\
    \"started_at\":\"2026-06-25T00:00:00Z\",\"updated_at\":\"2026-06-25T00:05:00Z\",\
    \"model_roster\":{\"main\":\"claude-opus-4-8\"}}\n";
const RUN_ID: &str = "11111111-2222-4333-8444-555555555555";

fn expected(body: &str) -> Value {
    serde_json::from_str(body).expect("recorded Python report parses")
}

fn write(root: &Path, relative: &str, body: &str) {
    let path = root.join(relative);
    fs::create_dir_all(path.parent().expect("fixture parent")).expect("create fixture parent");
    fs::write(path, body).expect("write fixture");
}

fn ledger_in(root: &Path, name: &str, body: &str) -> PathBuf {
    write(root, name, body);
    root.join(name)
}

fn run_dir(root: &Path, skill: &str) -> PathBuf {
    root.join("larch-logs").join(skill).join(RUN_ID)
}

fn implement_run(root: &Path, report: Option<&str>) -> PathBuf {
    let relative = format!("larch-logs/implement/{RUN_ID}");
    write(root, &format!("{relative}/manifest.json"), MANIFEST);
    if let Some(report) = report {
        write(root, &format!("{relative}/token-report.json"), report);
    }
    run_dir(root, "implement")
}

fn scan_events(root: &Path, skill: &str, limit: Option<usize>) -> Vec<TokenScanEvent> {
    TokenCorpusScan::new(
        root.join("larch-logs"),
        RunLogSelection::for_skill(RunLogSlug::parse(skill).expect("valid skill")),
        Some("character-ai/larch"),
        limit,
    )
    .collect()
}

#[test]
fn a_committed_ledger_rebuilds_the_python_owner_report() {
    let temp = TempDir::new().expect("temp");
    let ledger = ledger_in(temp.path(), "larch-tokens-a.jsonl", LEDGER);
    let mut observations = TokenObservations::default();
    let report = build_report_from_ledgers(&[ledger], &mut observations).expect("report");
    assert_eq!(Value::Object(report), expected(LEDGER_REPORT));
}

#[test]
fn an_implement_row_outside_step_two_is_rerouted_into_a_synthetic_step() {
    let temp = TempDir::new().expect("temp");
    let ledger = ledger_in(temp.path(), "larch-tokens-b.jsonl", REROUTE_LEDGER);
    let mut observations = TokenObservations::default();
    let report = build_report_from_ledgers(&[ledger], &mut observations).expect("report");
    assert_eq!(Value::Object(report), expected(REROUTE_REPORT));
}

#[test]
fn a_ledger_without_marks_fails_loudly_instead_of_pricing_nothing() {
    let temp = TempDir::new().expect("temp");
    let ledger = ledger_in(
        temp.path(),
        "larch-tokens-c.jsonl",
        "{\"type\":\"vendor\",\"vendor\":\"codex\",\"input\":5,\"ts\":\"2026-06-25T00:00:00Z\"}\n",
    );
    let mut observations = TokenObservations::default();
    assert_eq!(
        build_report_from_ledgers(&[ledger], &mut observations),
        Err(TokenReportError::NoStepMarks)
    );
    assert_eq!(
        TokenReportError::NoStepMarks.to_string(),
        "no step marks in ledger"
    );
}

#[test]
fn historical_transcript_shapes_still_parse_and_deduplicate() {
    let temp = TempDir::new().expect("temp");
    let ledger = ledger_in(temp.path(), "larch-tokens-a.jsonl", LEDGER);
    let transcript = ledger_in(temp.path(), "transcript.jsonl", TRANSCRIPT);
    let inputs = read_report_inputs(&ledger, &[transcript]).expect("inputs");
    // Two request/message pairs survive: the repeated `requestId|id` key keeps
    // its first position with the later payload, and the two field-identical
    // rows without ids collapse on their fingerprint.
    assert_eq!(inputs.claude.len(), 2);
    assert_eq!(inputs.claude[0].skill, "inferred:Step 0 \u{2014} setup");
    assert_eq!(
        inputs.claude[1].skill,
        "inferred:Step 2 \u{2014} implementation"
    );
    assert_eq!(inputs.claude[1].cache_create_5m, 4);
    assert_eq!(
        Value::Object(full_report(&inputs)),
        expected(FULL_REPORT),
        "full report parity"
    );
    assert_eq!(
        Value::Object(summary_report(&inputs)),
        expected(SUMMARY_REPORT),
        "summary report parity"
    );
}

#[test]
fn split_and_legacy_cache_creation_shapes_both_land_in_the_five_minute_tier() {
    let temp = TempDir::new().expect("temp");
    let ledger = ledger_in(
        temp.path(),
        "larch-tokens-d.jsonl",
        "{\"type\":\"mark\",\"step\":\"Step 0\",\"ts\":\"2026-06-25T00:00:00Z\"}\n",
    );
    let transcript = ledger_in(
        temp.path(),
        "legacy.jsonl",
        concat!(
            r#"{"type":"assistant","requestId":"x","timestamp":"2026-06-25T00:00:10Z","message":{"id":"1","usage":{"cache_creation":{"5m":3,"ephemeral_1h_input_tokens":4}}}}"#,
            "\n",
            r#"{"type":"assistant","requestId":"y","timestamp":"2026-06-25T00:00:20Z","usage":{"cache_creation_input_tokens":6}}"#,
            "\n",
        ),
    );
    let inputs = read_report_inputs(&ledger, &[transcript]).expect("inputs");
    assert_eq!(inputs.claude[0].cache_create_5m, 3);
    assert_eq!(inputs.claude[0].cache_create_1h, 4);
    assert_eq!(inputs.claude[0].cache_create, 7);
    assert_eq!(inputs.claude[1].cache_create_5m, 6);
    assert_eq!(inputs.claude[1].cache_create_1h, 0);
}

#[test]
fn unknown_models_and_unknown_usage_fields_are_reported_not_dropped() {
    let temp = TempDir::new().expect("temp");
    let ledger = ledger_in(temp.path(), "larch-tokens-a.jsonl", LEDGER);
    let transcript = ledger_in(temp.path(), "transcript.jsonl", TRANSCRIPT);
    let inputs = read_report_inputs(&ledger, &[transcript]).expect("inputs");
    let mut observations = inputs.observations.clone();
    let report = full_report(&inputs);
    let _priced = larch_core::full_report_with_observations(&inputs, &mut observations);
    let kinds: Vec<(TokenObservationKind, &str, &str)> = observations
        .entries()
        .iter()
        .map(|entry| (entry.kind(), entry.vendor(), entry.detail()))
        .collect();
    assert!(kinds.contains(&(
        TokenObservationKind::UnknownUsageField,
        "claude",
        "weird_field"
    )));
    assert!(kinds.contains(&(
        TokenObservationKind::NormalizedModel,
        "claude_sub",
        "claude-sonnet-4-6[1m]"
    )));
    assert!(kinds.contains(&(
        TokenObservationKind::DefaultedModel,
        "claude_sub",
        "claude-opus-4-8"
    )));
    assert!(kinds.contains(&(TokenObservationKind::DefaultedModel, "codex", "gpt-5.6-sol")));
    // An unpinned vendor id keeps its exact spelling in the report.
    assert!(
        report
            .get("vendors")
            .and_then(Value::as_array)
            .is_some_and(|vendors| vendors.contains(&Value::from("mystery"))),
        "an unknown vendor lane survives extraction"
    );
    assert!(!observations.truncated());
}

#[test]
fn an_unpinned_model_id_is_reported_and_kept_verbatim() {
    let temp = TempDir::new().expect("temp");
    let ledger = ledger_in(
        temp.path(),
        "larch-tokens-e.jsonl",
        concat!(
            "{\"type\":\"mark\",\"step\":\"Step 0\",\"ts\":\"2026-06-25T00:00:00Z\"}\n",
            r#"{"type":"vendor","vendor":"codex","model":"gpt-9-unreleased","input":4,"ts":"2026-06-25T00:00:10Z"}"#,
            "\n",
        ),
    );
    let mut observations = TokenObservations::default();
    let report = build_report_from_ledgers(&[ledger], &mut observations).expect("report");
    assert_eq!(
        report.get("BUCKETS_codex_by_model"),
        Some(
            &json!({"gpt-9-unreleased": {"cached_input": 0, "input": 4, "output": 0, "total": 4}})
        )
    );
    assert!(observations.entries().iter().any(|entry| {
        entry.kind() == TokenObservationKind::UnpinnedModel && entry.detail() == "gpt-9-unreleased"
    }));
}

#[test]
fn vendor_totals_fall_back_to_buckets_and_prefer_component_sums() {
    let report: Map<String, Value> = json!({
        "codex": {"totals": {"input": 10, "output": 2, "total": 12}},
        "BUCKETS_codex": {"input": 10, "cached_input": 7, "output": 2, "total": 19},
        "BUCKETS_claude": {"input": 0, "cache_read": 0, "cache_create_5m": 0,
                           "cache_create_1h": 0, "output": 0, "total": 0},
    })
    .as_object()
    .expect("object")
    .clone();
    let codex = vendor_totals_from_report(&report, TokenVendor::Codex);
    assert_eq!(
        codex.cached_input, 7,
        "a missing totals field reads BUCKETS"
    );
    assert_eq!(effective_vendor_total(&codex, TokenVendor::Codex), 19);
    assert!(report_has_numeric_tokens(&report));
    let separated: Map<String, Value> = json!({"BUCKETS_cursor": {"cache_read": "1,234"}})
        .as_object()
        .expect("object")
        .clone();
    assert_eq!(
        vendor_totals_from_report(&separated, TokenVendor::Cursor).cache_read,
        1234,
        "the BUCKETS fallback coerces like safe_int, not like a strict token read"
    );

    let legacy = VendorTotals {
        cache_create: 5,
        ..VendorTotals::default()
    };
    assert_eq!(
        larch_core::claude_effective_cache_create(&legacy),
        (5, 0),
        "legacy cache creation is priced at the five-minute tier"
    );
    assert_eq!(
        effective_vendor_total(
            &VendorTotals {
                total: 9,
                ..VendorTotals::default()
            },
            TokenVendor::Claude
        ),
        9,
        "an all-zero component sum falls back to the explicit total"
    );
}

#[test]
fn phase_rows_read_every_lane_and_name_a_missing_step() {
    let report: Map<String, Value> = json!({
        "claude": {"per_step": [{"step": "Step 0", "totals": {"input": 1, "total": 1}}]},
        "codex": {"per_step": [{"totals": {"input": 2, "cache_read": 1, "total": 3}}]},
    })
    .as_object()
    .expect("object")
    .clone();
    let rows = token_phase_rows(&report);
    assert_eq!(rows.len(), 2);
    assert_eq!(rows[0].vendor, TokenVendor::Claude);
    assert_eq!(rows[0].step, "Step 0");
    assert_eq!(rows[1].vendor, TokenVendor::Codex);
    assert_eq!(rows[1].step, "unknown");
    assert_eq!(rows[1].cache_read, 1);
}

#[test]
fn safe_int_matches_the_python_coercion_table() {
    assert_eq!(safe_int(Some(&json!("1,234")), 0), 1234);
    assert_eq!(safe_int(Some(&json!("2.9")), 0), 2);
    assert_eq!(safe_int(Some(&json!(-3.9)), 0), -3);
    assert_eq!(safe_int(Some(&json!(true)), 7), 7, "a bool is not an int");
    assert_eq!(safe_int(Some(&json!("nope")), 7), 7);
    assert_eq!(safe_int(None, 7), 7);
}

#[test]
fn the_session_scoped_ledger_wins_over_an_ambiguous_glob() {
    let temp = TempDir::new().expect("temp");
    let root = temp.path();
    // sha256("session-a")
    let digest = "b7b6c2e04d6e2d5c3ff77c0b9b6ab7b3a0c8e6b4e2e5c9a3d1f0a7c4b8e6d2f1";
    write(root, "session-id", "session-a\n");
    write(root, &format!("larch-tokens-{digest}.jsonl"), LEDGER);
    write(root, "larch-tokens-other.jsonl", LEDGER);
    assert_eq!(
        run_log_ledger_path(root),
        None,
        "two ledgers with no matching session digest stay ambiguous"
    );
    fs::remove_file(root.join("larch-tokens-other.jsonl")).expect("remove");
    assert_eq!(
        run_log_ledger_path(root),
        Some(root.join(format!("larch-tokens-{digest}.jsonl"))),
        "a single ledger is used even without a session match"
    );
}

#[test]
fn a_run_without_priceable_tokens_is_recovered_from_its_ledger() {
    let temp = TempDir::new().expect("temp");
    let dir = implement_run(temp.path(), Some("{\"schema_version\":1}\n"));
    write(
        temp.path(),
        &format!("larch-logs/implement/{RUN_ID}/larch-tokens-only.jsonl"),
        LEDGER,
    );
    let mut warnings = Vec::new();
    let mut observations = TokenObservations::default();
    let report =
        resolve_run_report(&dir, "implement", &mut warnings, &mut observations).expect("report");
    assert_eq!(
        report
            .get("BUCKETS_codex")
            .and_then(|bucket| bucket.get("input")),
        Some(&json!(1007))
    );
    assert!(
        warnings
            .iter()
            .any(|warning| warning.kind() == TokenScanWarningKind::LedgerRecovered)
    );
}

#[test]
fn every_unusable_report_shape_warns_with_its_own_reason() {
    let cases: [(&str, TokenScanWarningKind); 4] = [
        ("not json", TokenScanWarningKind::ReportUnreadable),
        ("[1,2]", TokenScanWarningKind::ReportNotObject),
        ("{}", TokenScanWarningKind::ReportEmpty),
        (
            "{\"BUCKETS_codex\":{\"input\":0}}",
            TokenScanWarningKind::ReportWithoutTokens,
        ),
    ];
    for (body, kind) in cases {
        let temp = TempDir::new().expect("temp");
        let dir = implement_run(temp.path(), Some(body));
        let mut warnings = Vec::new();
        let mut observations = TokenObservations::default();
        assert!(resolve_run_report(&dir, "implement", &mut warnings, &mut observations).is_none());
        assert!(
            warnings.iter().any(|warning| warning.kind() == kind),
            "expected {kind:?} for {body}"
        );
        assert!(warnings.iter().all(|warning| !warning.message().is_empty()));
    }

    let temp = TempDir::new().expect("temp");
    let dir = implement_run(temp.path(), None);
    let mut warnings = Vec::new();
    let mut observations = TokenObservations::default();
    assert!(resolve_run_report(&dir, "implement", &mut warnings, &mut observations).is_none());
    assert_eq!(warnings[0].kind(), TokenScanWarningKind::ReportMissing);
    assert!(
        warnings[0]
            .message()
            .ends_with("has no token-report.json; skipping")
    );
    assert_eq!(token_report_basename("design"), "token-report-final.json");
}

#[test]
fn a_symlinked_report_is_refused_before_it_is_read() {
    let temp = TempDir::new().expect("temp");
    let dir = implement_run(temp.path(), None);
    write(
        temp.path(),
        "outside.json",
        "{\"BUCKETS_codex\":{\"input\":9}}",
    );
    std::os::unix::fs::symlink(
        temp.path().join("outside.json"),
        dir.join("token-report.json"),
    )
    .expect("symlink");
    let mut warnings = Vec::new();
    let mut observations = TokenObservations::default();
    assert!(resolve_run_report(&dir, "implement", &mut warnings, &mut observations).is_none());
    assert_eq!(warnings[0].kind(), TokenScanWarningKind::ReportSymlink);
}

#[test]
fn the_corpus_scan_streams_records_and_honors_the_run_budget() {
    let temp = TempDir::new().expect("temp");
    let report = "{\"BUCKETS_codex\":{\"input\":5,\"cached_input\":1,\"output\":2,\"total\":8}}";
    let _first = implement_run(temp.path(), Some(report));
    let second = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
    write(
        temp.path(),
        &format!("larch-logs/implement/{second}/manifest.json"),
        &MANIFEST.replace(RUN_ID, second),
    );
    write(
        temp.path(),
        &format!("larch-logs/implement/{second}/token-report.json"),
        report,
    );

    let records: Vec<_> = scan_events(temp.path(), "implement", None)
        .into_iter()
        .filter_map(|event| match event {
            TokenScanEvent::Record(record) => Some(*record),
            _other => None,
        })
        .collect();
    assert_eq!(records.len(), 2);
    assert_eq!(records[0].number, 8086);
    assert_eq!(records[0].title, "Port the token scan layer");
    assert_eq!(
        records[0].url,
        "https://github.com/character-ai/larch/issues/8086"
    );
    assert_eq!(records[0].closed_at, "2026-06-25T00:05:00Z");
    assert_eq!(records[0].main_model, "claude-opus-4-8");
    assert_eq!(records[0].codex.cached_input, 1);

    let budgeted = scan_events(temp.path(), "implement", Some(1))
        .into_iter()
        .filter(|event| matches!(event, TokenScanEvent::Record(_)))
        .count();
    assert_eq!(budgeted, 1, "the run budget stops the walk early");

    // Laziness: taking one record must not require walking the whole corpus.
    let mut scan = TokenCorpusScan::new(
        temp.path().join("larch-logs"),
        RunLogSelection::all(),
        None,
        None,
    );
    let first = scan
        .find(|event| matches!(event, TokenScanEvent::Record(_)))
        .expect("a streamed record");
    match first {
        TokenScanEvent::Record(record) => assert!(record.url.is_empty()),
        _other => unreachable!("filtered above"),
    }
}

#[test]
fn transcript_sources_reject_a_missing_primary_and_sort_subagents() {
    let temp = TempDir::new().expect("temp");
    let missing = temp.path().join("absent.jsonl");
    assert_eq!(
        transcript_sources(&missing, None),
        Err(TokenReportError::TranscriptNotFound(missing.clone()))
    );
    write(temp.path(), "session/main.jsonl", TRANSCRIPT);
    write(temp.path(), "session/subagents/b.jsonl", TRANSCRIPT);
    write(temp.path(), "session/subagents/a.jsonl", TRANSCRIPT);
    write(temp.path(), "session/subagents/skip.txt", "ignored");
    let session = temp.path().join("session");
    let sources = transcript_sources(&session.join("main.jsonl"), Some(&session)).expect("sources");
    assert_eq!(
        sources,
        vec![
            session.join("main.jsonl"),
            session.join("subagents/a.jsonl"),
            session.join("subagents/b.jsonl"),
        ]
    );
}
