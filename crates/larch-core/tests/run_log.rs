//! Round-trip coverage for run-log layout, identity, and tolerant readers.

use larch_core::{
    ExecutionIssueFormat, ExecutionIssueLedger, ManifestFormatVersion, ManifestRecord, RoundNumber,
    RunLogLayout, RunLogSlug, validate_run_log_slug,
};
use serde_json::json;

#[test]
fn validate_run_log_slug_matches_python_contract() {
    for value in ["run-1", "-abc123", "abc.DEF_123", "current", "."] {
        assert!(validate_run_log_slug(value), "{value}");
    }
    for value in ["", "../evil", "a..b", "bad/slash", r"bad\slash", "bad space", "bad*char"] {
        assert!(!validate_run_log_slug(value), "{value}");
    }
}

#[test]
fn historical_manifest_shapes_round_trip_with_detected_version() {
    let v1 = ManifestRecord::parse_value(json!({
        "status": "done",
        "version": "1",
        "run_id": "11111111-2222-4333-8444-555555555555",
        "steps_ran": {"0": "ok"},
        "created_at": "2026-01-02T03:04:05Z",
        "updated_at": "2026-01-02T03:05:06Z",
        "skill": "implement"
    }))
    .expect("v1");
    assert_eq!(v1.detected_version(), ManifestFormatVersion::V1);
    assert_eq!(v1.status(), "done");
    assert_eq!(v1.extra().get("skill"), Some(&json!("implement")));

    let lifecycle_v1 = ManifestRecord::parse_value(json!({
        "schema_version": 2,
        "status": "done",
        "run_id": "11111111-2222-4333-8444-555555555555",
        "skill": "implement",
        "started_at": "t0",
        "updated_at": "t1",
        "steps_ran": {"0": "ok"},
        "lifecycle_schema_version": 1,
        "publication_mode": "enabled"
    }))
    .expect("lifecycle v1 on schema v2");
    assert_eq!(lifecycle_v1.detected_version(), ManifestFormatVersion::V2);
    assert_eq!(
        lifecycle_v1.extra().get("lifecycle_schema_version"),
        Some(&json!(1))
    );

    let v2 = ManifestRecord::parse_value(json!({
        "schema_version": 2,
        "status": "partial",
        "run_id": "abc",
        "skill": "design",
        "started_at": "t0",
        "updated_at": "t1",
        "steps_ran": {},
        "pr_number": 12
    }))
    .expect("v2");
    assert_eq!(v2.detected_version(), ManifestFormatVersion::V2);
    assert_eq!(v2.reserved().get("skill"), Some(&json!("design")));
    assert_eq!(v2.reserved().get("pr_number"), Some(&json!(12)));
}

#[test]
fn unknown_and_truncated_manifests_fail_with_stable_reasons() {
    assert_eq!(
        ManifestRecord::parse_bytes(br#"{"schema_version":2"#)
            .unwrap_err()
            .reason(),
        "invalid-json"
    );
    assert_eq!(
        ManifestRecord::parse_value(json!({"status": "partial"}))
            .unwrap_err()
            .reason(),
        "missing-version"
    );
    assert_eq!(
        ManifestRecord::parse_value(json!({"schema_version": 3}))
            .unwrap_err()
            .reason(),
        "unknown-schema-version"
    );
    assert_eq!(
        ManifestRecord::parse_value(json!({"version": "9"}))
            .unwrap_err()
            .reason(),
        "unknown-version"
    );
}

#[test]
fn layout_and_round_identity_use_validated_slugs() {
    let skill = RunLogSlug::parse("implement").unwrap();
    let run_id = RunLogSlug::parse("11111111-2222-4333-8444-555555555555").unwrap();
    let layout = RunLogLayout::under_repo("/repo", skill, run_id);
    assert!(
        layout
            .run_dir()
            .ends_with("larch-logs/implement/11111111-2222-4333-8444-555555555555")
    );
    assert_eq!(RoundNumber::new(1).unwrap().dir_name(), "round-1");
    assert_eq!(
        layout.round_dir(1).file_name().and_then(|name| name.to_str()),
        Some("round-1")
    );
}

#[test]
fn execution_issue_entry_formats_round_trip() {
    let markdown = ExecutionIssueLedger::parse_markdown(
        "### Warnings\n\nwatch this\n\n### CI Issues\n\nbuild failed\n",
    );
    assert_eq!(markdown.detected_format(), ExecutionIssueFormat::Markdown);
    assert_eq!(markdown.entries().len(), 2);

    let ndjson = ExecutionIssueLedger::parse_ndjson(
        "{\"category\":\"Warnings\",\"body\":\"watch this\"}\n",
    )
    .expect("ndjson");
    assert_eq!(ndjson.detected_format(), ExecutionIssueFormat::Ndjson);
    assert_eq!(ndjson.entries()[0].body(), "watch this");
    assert_eq!(
        ExecutionIssueLedger::parse_ndjson("{\"category\":\"Warnings\",\"body\":")
            .unwrap_err()
            .reason(),
        "invalid-json"
    );
}
