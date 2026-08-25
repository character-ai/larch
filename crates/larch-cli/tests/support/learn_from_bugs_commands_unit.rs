use super::*;
use crate::github_service::with_test_github_service;
use larch_adapters::github::OctocrabGitHubService;
use larch_test_support::{IssueServiceExchange, IssueServiceStub};
use serde_json::json;
use std::os::unix::fs::PermissionsExt as _;
use std::sync::Arc;

fn issue(number: u64, title: &str, body: &str) -> GitHubIssue {
    GitHubIssue {
        id: number,
        number,
        title: title.to_owned(),
        body: body.to_owned(),
        state: GitHubIssueState::Closed,
        state_reason: String::new(),
        url: format!("https://example.invalid/issues/{number}"),
        author: String::new(),
        assignees: Vec::new(),
        labels: Vec::new(),
        comments: 0,
        created_at: String::new(),
        closed_at: "2026-08-09T12:00:00Z".to_owned(),
        updated_at: String::new(),
        is_pull_request: false,
    }
}

fn proposal(id: &str, status: &str, filed_issue: Option<i64>) -> Proposal {
    Proposal {
        id: id.to_owned(),
        kind: "lint".to_owned(),
        target: "module:python/larch/lint/lint_delta.py".to_owned(),
        run_date: "2026-08-09".to_owned(),
        status: status.to_owned(),
        filed_issue,
    }
}

fn state(proposals: Vec<Proposal>) -> StateRecord {
    StateRecord {
        run_date: "2026-08-09".to_owned(),
        repo: "owner/repo".to_owned(),
        search: "[BUG] in:title".to_owned(),
        state: "closed".to_owned(),
        selected_count: 2,
        highest: 8,
        scan_started_at: Some("2026-08-09T10:00:00Z".to_owned()),
        proposals,
    }
}

fn arguments(values: &[&str]) -> Vec<OsString> {
    values.iter().map(OsString::from).collect()
}

#[test]
fn zones_preserve_data_and_reject_empty_parts() {
    assert_eq!(
        resolve_zone_search(" design , implement ", false, false).unwrap(),
        format!("{BUG_PREFIX} (design OR implement) in:title,body")
    );
    assert_eq!(
        resolve_zone_search("design,,implement", false, false).unwrap_err(),
        "--zones contains an empty zone name"
    );
    assert_eq!(
        resolve_zone_search("design$(boom)", false, false).unwrap(),
        format!("{BUG_PREFIX} (design$(boom)) in:title,body")
    );
}

#[test]
fn empty_path_arguments_keep_python_path_dot_semantics() {
    assert_eq!(path_from_argument(""), PathBuf::from("."));
    assert_eq!(path_from_argument("out"), PathBuf::from("out"));
}

#[test]
fn coverage_index_filters_sources_and_ignores_fenced_guidelines() {
    let directory = tempfile::tempdir().unwrap();
    fs::write(
        directory.path().join("ARCHITECTURAL_GUIDELINES.md"),
        "```markdown\n### G-Fake-1: ignored\n```\n### G-Real-1: used\n",
    )
    .unwrap();
    fs::create_dir_all(directory.path().join("python/larch/lint")).unwrap();
    fs::write(
        directory.path().join("python/larch/lint/lint_nested.py"),
        "# fixture\n",
    )
    .unwrap();
    fs::create_dir_all(directory.path().join("python/larch/lint/lint_directory.py")).unwrap();
    fs::create_dir_all(directory.path().join("scripts")).unwrap();
    fs::write(
        directory.path().join("scripts/lint-alpha"),
        "#!/bin/sh\n# fixture\n",
    )
    .unwrap();
    fs::write(
        directory.path().join("scripts/lint-alpha.py"),
        "#!/usr/bin/env python3\n# duplicate fixture\n",
    )
    .unwrap();
    fs::write(
        directory
            .path()
            .join("scripts/lint-readability-preamble.tsv"),
        "artifact\n",
    )
    .unwrap();
    fs::write(
        directory
            .path()
            .join("scripts/lint-readability-preamble.tsv.md"),
        "artifact docs\n",
    )
    .unwrap();
    fs::write(
        directory.path().join("scripts/lint-zeta.rb"),
        "#!/usr/bin/env ruby\n# fixture\n",
    )
    .unwrap();
    fs::create_dir_all(directory.path().join("crates/larch-lint/src/rules")).unwrap();
    fs::write(
        directory
            .path()
            .join("crates/larch-lint/src/rules/lifecycle_prefix.rs"),
        "//! Reject duplicated lifecycle prefixes.\n//! Later detail.\ncrate::register_rule!(METADATA, RULE);\n",
    )
    .unwrap();
    fs::write(
        directory
            .path()
            .join("crates/larch-lint/src/rules/undocumented.rs"),
        "const FIXTURE: &str = \"fixture\";\ncrate::register_rule!(METADATA, RULE);\n",
    )
    .unwrap();
    fs::write(
        directory
            .path()
            .join("crates/larch-lint/src/rules/helper.rs"),
        "//! Shared helper, not a lint rule.\n",
    )
    .unwrap();
    let coverage = coverage_index(directory.path());
    assert_eq!(
        coverage.guidelines,
        vec![("G-Real-1".to_owned(), "used".to_owned())]
    );
    assert_eq!(coverage.python_lints, vec!["lint_nested".to_owned()]);
    assert_eq!(
        coverage.script_lints,
        vec!["lint-alpha".to_owned(), "lint-zeta".to_owned()]
    );
    assert_eq!(
        coverage.rust_lints,
        vec![
            (
                "lifecycle_prefix".to_owned(),
                "Reject duplicated lifecycle prefixes.".to_owned(),
            ),
            ("undocumented".to_owned(), String::new()),
        ]
    );
}

#[test]
fn digest_keeps_ascii_safe_json() {
    assert_eq!(ascii_json_string("é😀\n"), "\"\\u00e9\\ud83d\\ude00\\n\"");
}

#[test]
fn digest_uses_only_the_diagnostic_prefix_and_structured_sections() {
    let digest = build_digest(&issue(
        7,
        &format!("{DONE_TITLE_PREFIX}{BUG_PREFIX} structured"),
        "## Summary\n\nuseful signal\n\n## Root cause\n\nintroduced by #5\n\n## Plan\n\nignored",
    ));
    assert_eq!(digest.title, format!("{BUG_PREFIX} structured"));
    assert!(digest.structured);
    assert_eq!(
        digest.sections[0],
        ("summary".to_owned(), "useful signal".to_owned())
    );
    assert_eq!(digest.origin.kind, "regression");
    assert_eq!(digest.origin.reference, Some(5));
    assert!(!serialize_digest(&digest).contains("ignored"));
}

#[test]
fn plan_marker_requires_the_named_block_wire_spacing() {
    assert_eq!(
        diagnostic_prefix("signal\n<!-- larch:plan:start -->\nignored"),
        "signal\n"
    );
    assert_eq!(
        diagnostic_prefix("signal\n<!--larch:plan:start -->\nretained"),
        "signal\n<!--larch:plan:start -->\nretained"
    );
}

#[test]
fn state_wire_is_sorted_and_ascii_safe() {
    let state = StateRecord {
        run_date: "2026-08-09T12:00:00Z".to_owned(),
        repo: "owner/répo".to_owned(),
        search: "[BUG] 😀".to_owned(),
        state: "closed".to_owned(),
        selected_count: 1,
        highest: 7,
        scan_started_at: Some("2026-08-09T11:00:00Z".to_owned()),
        proposals: Vec::new(),
    };
    let text = serialize_state(&state).unwrap();
    assert!(text.starts_with("{\n  \"highest_closed_issue_number_scanned\": 7,"));
    assert!(text.contains("owner/r\\u00e9po"));
    assert!(text.contains("[BUG] \\ud83d\\ude00"));
    assert!(text.ends_with("}\n"));
}

#[test]
fn audit_scan_boundary_prefers_a_nonempty_scan_start_then_run_date() {
    let mut scanned = state(Vec::new());
    scanned.scan_started_at = Some("2026-08-09T10:00:00Z".to_owned());
    assert_eq!(
        audit_scan_boundary_from_state(scanned),
        ("owner/repo".to_owned(), "2026-08-09T10:00:00Z".to_owned())
    );

    let mut fallback = state(Vec::new());
    fallback.scan_started_at = Some(String::new());
    assert_eq!(
        audit_scan_boundary_from_state(fallback),
        ("owner/repo".to_owned(), "2026-08-09".to_owned())
    );
}

#[test]
fn state_writer_detects_a_stale_snapshot_and_keeps_private_permissions() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("state.json");
    let state = StateRecord {
        run_date: "2026-08-09T12:00:00Z".to_owned(),
        repo: "owner/repo".to_owned(),
        search: "[BUG] in:title".to_owned(),
        state: "closed".to_owned(),
        selected_count: 0,
        highest: 0,
        scan_started_at: Some("2026-08-09T11:00:00Z".to_owned()),
        proposals: Vec::new(),
    };
    let missing = state_snapshot(&path).unwrap();
    write_state_locked(&path, state.clone(), None, None, directory.path(), &missing).unwrap();
    #[cfg(unix)]
    assert_eq!(
        fs::metadata(&path).unwrap().permissions().mode() & 0o777,
        0o600
    );
    let recorded_snapshot = state_snapshot(&path).unwrap();
    fs::write(&path, "{}\n").unwrap();
    assert!(
        write_state_locked(
            &path,
            state,
            None,
            None,
            directory.path(),
            &recorded_snapshot,
        )
        .unwrap_err()
        .starts_with("analysis state changed concurrently:")
    );
}

#[test]
fn proposal_targets_keep_python_validation_boundaries() {
    assert!(
        proposal_from_value(
            &json!({
                "id": "rust-test",
                "type": "test",
                "target": "crates/larch-cli/src/main.rs::run",
                "run_date": "2026-08-09",
                "status": "pending",
                "filed_issue": null,
            }),
            None,
        )
        .is_some()
    );
    for target in [
        "crates/larch-cli/src/main.rs::",
        "notes.txt::test_bad",
        "ARCHITECTURAL_GUIDELINES.md#one#two",
        "check:crates/larch-cli/src/main.rs#run#again",
    ] {
        assert!(proposal_from_value(
        &json!({
                "id": "bad-target",
                "type": if target.starts_with("ARCHITECTURAL") { "guideline" } else if target.starts_with("check:") { "lint" } else { "test" },
                "target": target,
                "run_date": "2026-08-09",
                "status": "pending",
                "filed_issue": null,
            }),
            None,
        )
        .is_none());
    }
    assert!(
        proposal_from_value(
            &json!({
                "id": "wrong-check-kind",
                "type": "invariant",
                "target": "check:crates/larch-cli/src/main.rs#run",
                "run_date": "2026-08-09",
                "status": "pending",
                "filed_issue": null,
            }),
            None,
        )
        .is_none()
    );
    for filed_issue in [json!(0), json!(-1), json!(true), json!("1")] {
        assert!(
            proposal_from_value(
                &json!({
                    "id": "bad-filed-issue", "type": "lint", "target": "registration:lint",
                    "run_date": "2026-08-09", "status": "pending", "filed_issue": filed_issue,
                }),
                None,
            )
            .is_none()
        );
    }
}

#[test]
fn lint_registration_probe_ignores_comments_and_string_literals() {
    let root = tempfile::tempdir().unwrap();
    let rule = root.path().join("crates/larch-lint/src/rules/audit.rs");
    fs::create_dir_all(rule.parent().unwrap()).unwrap();
    fs::write(
        &rule,
        "// const NAME: &str = \"audit\";\nconst OTHER: &str = \"audit\";\n",
    )
    .unwrap();
    assert!(!lint_registration_adopted("audit", root.path()));
    fs::write(
        &rule,
        "const NAME: &str = \"audit\";\ncrate::register_rule!(METADATA, RULE);\n",
    )
    .unwrap();
    assert!(lint_registration_adopted("audit", root.path()));

    fs::remove_file(&rule).unwrap();
    let root_rule = root
        .path()
        .join("crates/larch-lint/src/command_registry.rs");
    fs::write(
        root_rule,
        "const NAME: &str = \"command-registry\";\ncrate::register_rule!(METADATA, RULE);\n",
    )
    .unwrap();
    assert!(lint_registration_adopted("command-registry", root.path()));
}

#[cfg(unix)]
#[test]
fn proposal_target_cannot_follow_an_escaping_symlink() {
    use std::os::unix::fs::symlink;

    let root = tempfile::tempdir().unwrap();
    let outside = tempfile::tempdir().unwrap();
    symlink(outside.path(), root.path().join("escape")).unwrap();
    assert!(
        proposal_from_value(
            &json!({
                "id": "escaping-module",
                "type": "lint",
                "target": "module:escape/rule.py",
                "run_date": "2026-08-09",
                "status": "pending",
                "filed_issue": null,
            }),
            Some(root.path()),
        )
        .is_none()
    );
}

#[test]
fn diagnostic_parsing_ignores_fences_and_keeps_compatible_sections() {
    assert_eq!(
        diagnostic_prefix("signal\r\n## Approach\r\nignored"),
        "signal\r\n"
    );
    assert_eq!(
        diagnostic_prefix("signal\n### UPDATED: scope\nignored"),
        "signal\n"
    );
    assert_eq!(
        line_starts("one\r\ntwo\nthree"),
        vec![(0, "one"), (5, "two"), (9, "three")]
    );
    let lines = [
        "before",
        "```rust",
        "## hidden",
        "```",
        "after",
        "~~~~",
        "tail",
    ];
    assert_eq!(fenced_indices(&lines), HashSet::from([2, 6]));

    let sections = diagnostic_sections(
        "## Summary\r\nsummary text\r\n```markdown\r\n## Root cause\r\nignored\r\n```\r\n**Impact**: user impact\r\n### Root Cause Analysis\r\nroot text\r\n",
    );
    assert_eq!(
        sections,
        vec![
            (
                "summary".to_owned(),
                "summary text\r\n```markdown\r\n## Root cause\r\nignored\r\n```".to_owned(),
            ),
            ("impact".to_owned(), "user impact".to_owned()),
            ("root cause analysis".to_owned(), "root text".to_owned()),
        ]
    );

    let (selected, structured, class) = pick_sections(
        "## Summary\nsummary\n## Impact\nimpact\n## Classification\nIMPLEMENTATION_BUG, owning surface CLI\n## Root Cause\nroot\n## Root Cause Analysis\nmore root\n## Suggested Fix\nfix\n## Suggested Fix(es)\nother fix\n## Repro\nrepro\n",
    );
    assert!(structured);
    assert_eq!(
        selected.iter().map(|(name, _)| name).collect::<Vec<_>>(),
        vec![
            "summary",
            "impact",
            "classification",
            "root cause analysis",
            "suggested fix(es)",
            "repro",
        ]
    );
    let class = class.expect("classification");
    assert_eq!(class.kind, "IMPLEMENTATION_BUG");
    assert_eq!(class.surface, "CLI");

    let (title_only, structured, _) = pick_sections("short signal");
    assert!(!structured);
    assert_eq!(title_only, vec![("_title_only".to_owned(), String::new())]);
    let (freeform, structured, _) = pick_sections(
        "plain diagnostic signal with enough content to exceed the title-only threshold\n| a | b |\n|---|---|\n| c | d |\n",
    );
    assert!(!structured);
    assert_eq!(freeform[0].0, "_freeform");
    assert!(freeform[0].1.contains("[table elided: 3 lines]"));
}

#[test]
fn classification_and_table_parsers_handle_fences_and_fallbacks() {
    let classification = parse_classification("CONFIGURATION_GAP (triaged), owning surface CONFIG")
        .expect("classification");
    assert_eq!(
        (
            classification.kind.as_str(),
            classification.surface.as_str()
        ),
        ("CONFIGURATION_GAP", "CONFIG")
    );
    assert!(parse_classification("not a classification").is_none());
    let harness = parse_harness_classification(
        "```text\nroot-cause class: WRONG\nowning surface: WRONG\n```\nRoot-cause class: `DESIGN_GAP`\nowning surface: `WORKFLOW`",
    )
    .expect("harness classification");
    assert_eq!(
        (harness.kind.as_str(), harness.surface.as_str()),
        ("DESIGN_GAP", "WORKFLOW")
    );
    assert!(parse_harness_classification("root-cause class: ONE").is_none());

    assert!(is_table_row(" | a | b | "));
    assert!(is_table_row("╔══╗"));
    assert!(!is_table_row("ordinary text"));
    assert_eq!(
        elide_tables("before\n| one |\nnext\n╔══╗\n║ x ║\n╚══╝\nafter"),
        "before\n| one |\nnext\n[table elided: 3 lines]\nafter"
    );
    assert_eq!(squeeze("a\n\n\nb", 5), "a\nb");
    assert_eq!(squeeze("abcdef", 3), "abc…");

    assert_eq!(
        first_origin_reference(&[
            "introduced by #9 then incomplete fix of #2".to_owned(),
            "introduced in #7".to_owned(),
        ]),
        Some(9)
    );
    assert_eq!(
        first_origin_reference(&["persists after #42".to_owned()]),
        Some(42)
    );
    assert_eq!(first_origin_reference(&["no reference".to_owned()]), None);
}

#[test]
fn origin_classification_handles_all_fallbacks() {
    let cases = [
        (
            "[BUG] introduced by PR #4",
            "short",
            None,
            ("regression", Some(4), None),
        ),
        (
            "[BUG] regression without a number",
            "short",
            None,
            ("regression", None, None),
        ),
        (
            "[BUG] missing behavior",
            "## Root cause\nthe behavior was never designed",
            None,
            ("spec-gap", None, None),
        ),
        (
            "[BUG] fresh behavior",
            "## Root cause\nfirst time this path ran",
            None,
            ("new-code", None, None),
        ),
        (
            "[BUG] configuration",
            "short",
            Some(BugClass {
                kind: "CONFIGURATION_GAP".to_owned(),
                surface: "CONFIG".to_owned(),
            }),
            ("spec-gap", None, None),
        ),
        (
            "[BUG] unclear",
            "## Root Cause\nunknown details",
            None,
            ("unknown", None, Some("inconclusive")),
        ),
        (
            "[BUG] unclear",
            "short",
            None,
            ("unknown", None, Some("no-classification-signal")),
        ),
    ];
    for (title, body, class, expected) in cases {
        let origin = classify_origin(title, body, class.as_ref());
        assert_eq!(
            (origin.kind, origin.reference, origin.unknown_reason),
            expected,
            "{title}"
        );
    }
}

#[test]
fn origin_classification_recognizes_corpus_prose() {
    let cases = [
        (
            "This is a design gap, not a regression.",
            ("spec-gap", None),
        ),
        ("This is not a larch defect.", ("spec-gap", None)),
        (
            "This is a Python-migration regression.",
            ("regression", None),
        ),
        (
            "This is a design gap, not a Python-migration regression.",
            ("spec-gap", None),
        ),
        (
            "The defect was introduced by #17.",
            ("regression", Some(17)),
        ),
        (
            "The defect was introduced by PR #18.",
            ("regression", Some(18)),
        ),
        ("This is a residual of #19.", ("regression", Some(19))),
        (
            "This was the first live run of review synthesis.",
            ("new-code", None),
        ),
        (
            "The CLI contract has a contract underspecification.",
            ("spec-gap", None),
        ),
        ("This is a skill contract gap.", ("spec-gap", None)),
        ("This is a guidance gap.", ("spec-gap", None)),
        ("This is an observability gap.", ("spec-gap", None)),
        ("This is a child prompt gap.", ("spec-gap", None)),
        (
            "There is a gap in the leaf thin-orchestrator contract.",
            ("spec-gap", None),
        ),
        ("The route is under-specified.", ("spec-gap", None)),
        (
            "This is intentional fail-closed behavior.",
            ("spec-gap", None),
        ),
        ("This is not a bug inside larch.", ("spec-gap", None)),
        ("There is a missing rollback path.", ("spec-gap", None)),
        ("There is no bounded retry.", ("spec-gap", None)),
        (
            "The prompt has no fail-closed instruction.",
            ("spec-gap", None),
        ),
        (
            "The design assumes the branch stays clean.",
            ("spec-gap", None),
        ),
        (
            "Both conditions were introduced together by migration #20.",
            ("regression", Some(20)),
        ),
        (
            "The filter predates the freshness gate (#21).",
            ("regression", Some(21)),
        ),
        (
            "The commands were migrated without help handling.",
            ("regression", None),
        ),
        ("Python 3.13 changed help formatting.", ("regression", None)),
    ];
    for (prose, expected) in cases {
        let body = format!("## Root cause analysis\n\n{prose}");
        let origin = classify_origin("[BUG] corpus fixture", &body, None);
        assert_eq!((origin.kind, origin.reference), expected, "{prose}");
    }

    let summary_only = classify_origin(
        "[BUG] summary fixture",
        "## Summary\n\nThe design assumes the branch stays clean.\n\n## Root cause\n\nUnknown.",
        None,
    );
    assert_eq!(
        (summary_only.kind, summary_only.reference),
        ("unknown", None)
    );

    let negated = classify_origin(
        "[BUG] negated fixture",
        "## Root cause\n\nThis is not a #8058 migration regression.",
        None,
    );
    assert_eq!((negated.kind, negated.reference), ("unknown", None));
    let mixed = classify_origin(
        "[BUG] mixed fixture",
        "## Root cause\n\nThis is not a migration regression. A later defect is a regression.",
        None,
    );
    assert_eq!((mixed.kind, mixed.reference), ("regression", None));
}

#[test]
fn digest_wire_escapes_and_includes_optional_fields() {
    assert_eq!(
        ascii_json_string("\"\\\u{08}\u{0c}\r\t\u{1f}"),
        "\"\\\"\\\\\\b\\f\\r\\t\\u001f\""
    );
    assert_eq!(ascii_json("é😀"), "\\u00e9\\ud83d\\ude00");
    let digest = Digest {
        number: 9,
        title: "title".to_owned(),
        closed_at: "2026-08-09".to_owned(),
        url: "https://example.invalid/9".to_owned(),
        state: "OPEN".to_owned(),
        structured: false,
        prefix_chars: 4,
        sections: vec![("_freeform".to_owned(), "value".to_owned())],
        origin: Origin {
            kind: "unknown",
            reference: None,
            unknown_reason: Some("inconclusive"),
        },
        classification: Some(BugClass {
            kind: "DESIGN_GAP".to_owned(),
            surface: "CLI".to_owned(),
        }),
    };
    let wire = serialize_digest(&digest);
    assert!(wire.contains("\"origin\": {\"kind\": \"unknown\", \"ref\": null}"));
    assert!(wire.contains("\"class\": {\"kind\": \"DESIGN_GAP\", \"surface\": \"CLI\"}"));
}

fn digest_record(
    number: u64,
    title: &str,
    kind: &'static str,
    reference: Option<u64>,
    unknown_reason: Option<&'static str>,
) -> Digest {
    Digest {
        number,
        title: title.to_owned(),
        closed_at: "2026-08-09".to_owned(),
        url: format!("https://example.invalid/{number}"),
        state: "CLOSED".to_owned(),
        structured: false,
        prefix_chars: 0,
        sections: vec![("_title_only".to_owned(), String::new())],
        origin: Origin {
            kind,
            reference,
            unknown_reason,
        },
        classification: None,
    }
}

#[test]
fn digest_chunking_preserves_ordered_artifacts() {
    let temporary = tempfile::tempdir().unwrap();
    let records = vec![
        digest_record(4, &"a".repeat(20_000), "regression", Some(1), None),
        digest_record(5, &"b".repeat(20_000), "regression", Some(5), None),
        digest_record(6, "new", "new-code", None, None),
        digest_record(7, "gap", "spec-gap", None, None),
        digest_record(8, "unknown", "unknown", None, Some("inconclusive")),
    ];
    let (paths, chars) = write_digest_chunks(temporary.path(), &records).unwrap();
    assert_eq!(paths.len(), 2);
    assert_eq!(paths[0].file_name().unwrap(), "digest-01.jsonl");
    assert_eq!(paths[1].file_name().unwrap(), "digest-02.jsonl");
    assert_eq!(
        chars,
        records
            .iter()
            .map(serialize_digest)
            .map(|record| record.chars().count())
            .sum::<usize>()
    );
    assert!(
        fs::read_to_string(&paths[0])
            .unwrap()
            .contains("\"number\": 4")
    );
    assert!(
        fs::read_to_string(&paths[1])
            .unwrap()
            .contains("\"number\": 5")
    );
    let excessive = digest_record(
        9,
        &"x".repeat(DIGEST_CHUNK_CHAR_LIMIT),
        "unknown",
        None,
        Some("no-classification-signal"),
    );
    assert_eq!(
        write_digest_chunks(temporary.path(), &[excessive]).unwrap_err(),
        "digest record exceeds the configured chunk token limit"
    );
}

#[test]
fn origin_headline_counts_ordered_origins() {
    let records = vec![
        digest_record(4, "regression", "regression", Some(1), None),
        digest_record(5, "self-reference", "regression", Some(5), None),
        digest_record(6, "new", "new-code", None, None),
        digest_record(7, "gap", "spec-gap", None, None),
        digest_record(8, "unknown", "unknown", None, Some("inconclusive")),
    ];
    let headline = render_origin_headline(&records);
    assert!(headline.contains("- regression: 2 (40.0%)"));
    assert!(headline.contains("- new-code: 1 (20.0%)"));
    assert!(headline.contains("- spec-gap: 1 (20.0%)"));
    assert!(headline.contains("- unknown: 1 (20.0%)"));
    assert!(headline.contains("  - signal present but inconclusive: 1 (20.0%)"));
    assert!(headline.contains("- #1 -> #4"));
    assert!(headline.contains("- #5 -> #5 (suspect: self-reference)"));
    assert!(headline.ends_with("2/5 (40.0%)\n"));
    assert_eq!(pct_one_decimal(0, 0), "0.0");
    assert_eq!(
        render_origin_headline(&[]),
        "#### Origin distribution (selected=0)\n- regression: 0 (0.0%)\n- new-code: 0 (0.0%)\n- spec-gap: 0 (0.0%)\n- unknown: 0 (0.0%)\n#### Referenced regression chains\n(none)\n#### Regression ratio\nn/a (0/0)\n"
    );
}

#[test]
fn argparse_primitives_preserve_help_and_strict_parse_behavior() {
    assert!(help_requested(&arguments(&["-h"]), false));
    assert!(!help_requested(&arguments(&["--he"]), false));
    assert!(help_requested(&arguments(&["--he"]), true));
    assert!(
        help_explicit_argument(&arguments(&["--help=value"]), false, "usage", "program",).is_some()
    );
    assert!(
        help_explicit_argument(&arguments(&["--he=value"]), true, "usage", "program",).is_some()
    );
    assert_eq!(
        split_inline_option("--name=value"),
        Some(("--name", "value"))
    );
    assert_eq!(split_inline_option("plain"), None);

    let parsed = strict_parse(
        &arguments(&["--value", "text", "--flag"]),
        &["--value"],
        &["--flag"],
        "usage",
        "program",
        false,
    )
    .unwrap();
    assert_eq!(
        required_option(&parsed, "--value", "usage", "program"),
        Ok("text".to_owned())
    );
    assert_eq!(option_text(&parsed, "--value"), Some("text".to_owned()));
    assert_eq!(option_text(&parsed, "--missing"), None);
    assert!(required_option(&parsed, "--missing", "usage", "program").is_err());
    assert_eq!(
        strict_unrecognized(
            &arguments(&["--value", "text", "--flag", "--unknown", "--", "tail"]),
            &["--value"],
            &["--flag"],
        ),
        Some("unrecognized arguments: --unknown -- tail".to_owned())
    );
    assert_eq!(
        strict_unrecognized(&arguments(&["--value=text"]), &["--value"], &[]),
        None
    );
    assert!(
        strict_parse(
            &arguments(&["--value"]),
            &["--value"],
            &[],
            "usage",
            "program",
            false,
        )
        .is_err()
    );
    assert!(
        strict_parse(
            &arguments(&["--unknown"]),
            &["--value"],
            &[],
            "usage",
            "program",
            true,
        )
        .is_err()
    );
}

#[test]
fn integer_options_and_filesystem_primitives_preserve_boundaries() {
    assert_eq!(parse_int("-3", "--count", "usage", "program"), Ok(-3));
    assert!(parse_int("three", "--count", "usage", "program").is_err());
    let parsed = strict_parse(
        &arguments(&["--one", "1", "--two", "not-a-number"]),
        &["--one", "--two"],
        &[],
        "usage",
        "program",
        false,
    )
    .unwrap();
    assert!(parse_integer_options(&parsed, &["--one", "--two"], "usage", "program").is_err());
    let parsed = strict_parse(
        &arguments(&["--one", "1", "--ignored", "word"]),
        &["--one", "--ignored"],
        &[],
        "usage",
        "program",
        false,
    )
    .unwrap();
    assert_eq!(
        parse_integer_options(&parsed, &["--one"], "usage", "program").unwrap(),
        BTreeMap::from([("--one", 1)])
    );

    let directory = tempfile::tempdir().unwrap();
    assert_eq!(
        canonical_root(directory.path()).unwrap(),
        fs::canonicalize(directory.path()).unwrap()
    );
    assert!(canonical_root(&directory.path().join("missing")).is_err());
    assert_eq!(resolve_repo("owner/repo"), Ok("owner/repo".to_owned()));
    assert!(resolve_repo("not a repository").is_err());
    assert!(
        fetch_issues("owner/repo", "query", "closed", 0)
            .unwrap()
            .is_empty()
    );
    assert_eq!(
        fetch_issues("owner/repo", "query", "closed", -1),
        Err("invalid issue limit".to_owned())
    );
    let output = create_out_dir(&directory.path().join("nested/output")).unwrap();
    assert!(output.is_dir());
    let written = output.join("payload.txt");
    plain_atomic_write(&written, "payload").unwrap();
    assert_eq!(fs::read_to_string(written).unwrap(), "payload");
}

#[test]
fn coverage_scanners_handle_missing_marked_unmarked_and_sorted_sources() {
    let directory = tempfile::tempdir().unwrap();
    assert!(scan_guidelines(&directory.path().join("missing.md")).is_empty());
    assert!(scan_marked(&directory.path().join("missing.md"), &INVARIANT_HEADING_RE).is_empty());
    assert!(scan_lints(&directory.path().join("missing"), "lint_", &[Some("py")]).is_empty());
    assert_eq!(
        coverage_index(directory.path()).guidelines_status,
        "missing"
    );

    let guidelines = directory.path().join("guidelines.md");
    fs::write(
        &guidelines,
        "## First unmarked heading ##\n```markdown\n## Fenced heading\n```\n### Second unmarked\n",
    )
    .unwrap();
    assert_eq!(
        scan_guidelines(&guidelines),
        vec![
            (
                "First unmarked heading".to_owned(),
                "First unmarked heading".to_owned()
            ),
            ("Second unmarked".to_owned(), "Second unmarked".to_owned()),
        ]
    );
    fs::write(
        &guidelines,
        "### G-Second-2: Second\n### G-First-1: First\n",
    )
    .unwrap();
    assert_eq!(
        scan_guidelines(&guidelines),
        vec![
            ("G-Second-2".to_owned(), "Second".to_owned()),
            ("G-First-1".to_owned(), "First".to_owned()),
        ]
    );
    let invariants = directory.path().join("invariants.md");
    fs::write(
        &invariants,
        "### I-Real-1: Real\n```text\n### I-Fake-1: Fake\n```\n",
    )
    .unwrap();
    assert_eq!(
        scan_marked(&invariants, &INVARIANT_HEADING_RE),
        vec![("I-Real-1".to_owned(), "Real".to_owned())]
    );

    let lints = directory.path().join("lints");
    fs::create_dir_all(&lints).unwrap();
    for name in ["lint_zeta.py", "lint_alpha.py", "lint_skip.txt", "other.py"] {
        fs::write(lints.join(name), "").unwrap();
    }
    assert_eq!(
        scan_lints(&lints, "lint_", &[Some("py")]),
        vec!["lint_alpha".to_owned(), "lint_zeta".to_owned()]
    );
}

#[test]
fn scalar_date_and_target_validation_match_the_accepted_wire_forms() {
    assert_eq!(scalar_string(&json!("text")), Some("text".to_owned()));
    assert_eq!(scalar_string(&json!(42)), Some("42".to_owned()));
    assert_eq!(scalar_string(&json!(true)), Some("True".to_owned()));
    assert_eq!(scalar_string(&Value::Null), Some(String::new()));
    assert_eq!(scalar_string(&json!(["not", "scalar"])), None);
    assert_eq!(int_field(Some(&json!("-4")), 9), -4);
    assert_eq!(int_field(Some(&json!("not-int")), 9), 9);
    assert_eq!(int_field(None, 9), 9);

    for value in [
        "2026-08-09",
        "2026-08-09T12:34:56Z",
        "2026-08-09T12:34:56+00:00",
    ] {
        assert!(valid_date(value), "{value}");
    }
    for value in ["", "2026-13-09", "2026-08-09Tnot-time"] {
        assert!(!valid_date(value), "{value}");
    }

    for (kind, target) in [
        ("fix", "fix:repair-token"),
        ("hook", "hook:pre-commit"),
        ("lint", "check:crates/larch-cli/src/main.rs#run"),
        ("test", "check:crates/larch-cli/src/main.rs#run"),
        ("lint", "registration:learn-from-bugs"),
        ("lint", "module:python/larch/lint/lint_delta.py"),
        ("invariant", "ARCHITECTURAL_INVARIANTS.md#I-One"),
        ("guideline", "ARCHITECTURAL_GUIDELINES.md#G-One"),
        ("test", "python/tests/test_delta.py::test_delta"),
        ("test", "crates/larch-cli/src/main.rs::dispatch"),
    ] {
        assert!(valid_target(kind, target, None), "{kind}: {target}");
    }
    for (kind, target) in [
        ("fix", "fix:UPPER"),
        ("hook", "hook:bad\nvalue"),
        ("lint", "check:../escape#run"),
        ("lint", "registration:bad/value"),
        ("lint", "module:python/larch/lint/lint_delta.rs"),
        ("guideline", "ARCHITECTURAL_GUIDELINES.md#"),
        ("test", "python/tests/test_delta.py::not_a_test"),
        ("test", "crates/larch-cli/src/main.rs::not-valid-symbol!"),
    ] {
        assert!(!valid_target(kind, target, None), "{kind}: {target}");
    }
    assert!(valid_relative_path("nested/file.py", &[".py"], None));
    for path in [
        "",
        "/absolute.py",
        "nested\\file.py",
        "../escape.py",
        "nested//file.py",
    ] {
        assert!(!valid_relative_path(path, &[".py"], None), "{path}");
    }
}

#[test]
fn state_values_support_legacy_current_and_rejected_wire_forms() {
    let base = json!({
        "schema_version": 1,
        "run_date": 20_260_809,
        "repo": true,
        "search": null,
        "state": false,
        "selected_count": "3",
        "highest_closed_issue_number_scanned": 8,
    });
    let old = state_from_value(&base).expect("v1 state");
    assert_eq!(old.run_date, "20260809");
    assert_eq!(old.repo, "True");
    assert_eq!(old.search, "");
    assert_eq!(old.state, "False");
    assert_eq!((old.selected_count, old.highest), (3, 8));
    assert!(old.proposals.is_empty());

    let proposal_record = json!({
        "id": "lint-delta",
        "type": "lint",
        "target": "module:python/larch/lint/lint_delta.py",
        "run_date": "2026-08-09T12:00:00Z",
        "status": "adopted",
        "filed_issue": 12,
    });
    let current = json!({
        "schema_version": "2",
        "run_date": "2026-08-09",
        "repo": "owner/repo",
        "proposals": [proposal_record],
        "scan_started_at": "2026-08-09T12:00:00Z",
    });
    let current = state_from_value(&current).expect("v2 state");
    assert_eq!(current.proposals.len(), 1);
    assert_eq!(current.proposals[0].filed_issue, Some(12));
    assert_eq!(
        current.scan_started_at.as_deref(),
        Some("2026-08-09T12:00:00Z")
    );

    for invalid in [
        json!({"schema_version": 3, "run_date": "2026-08-09", "repo": "owner/repo"}),
        json!({"schema_version": 1, "run_date": "", "repo": "owner/repo"}),
        json!({"schema_version": 1, "run_date": "2026-08-09", "repo": ""}),
        json!({"schema_version": 2, "run_date": "2026-08-09", "repo": "owner/repo"}),
        json!({
            "schema_version": 2,
            "run_date": "2026-08-09",
            "repo": "owner/repo",
            "proposals": [
                {"id":"same","type":"fix","target":"fix:one","run_date":"2026-08-09","status":"pending","filed_issue":null},
                {"id":"same","type":"fix","target":"fix:one","run_date":"2026-08-09","status":"pending","filed_issue":null}
            ],
        }),
    ] {
        assert!(state_from_value(&invalid).is_none());
    }
}

#[test]
fn proposal_files_and_reconciliation_retain_stable_history() {
    let directory = tempfile::tempdir().unwrap();
    let root = directory.path();
    fs::create_dir_all(root.join("python/larch/lint")).unwrap();
    fs::write(root.join("python/larch/lint/lint_delta.py"), "# fixture\n").unwrap();
    let proposals = root.join("proposals.jsonl");
    fs::write(
        &proposals,
        "\n{\"id\":\"lint-delta\",\"type\":\"lint\",\"target\":\"module:python/larch/lint/lint_delta.py\",\"run_date\":\"2026-08-09\",\"status\":\"proposed\",\"filed_issue\":null}\n{\"id\":\"lint-delta\",\"type\":\"lint\",\"target\":\"module:python/larch/lint/lint_delta.py\",\"run_date\":\"2026-08-09\",\"status\":\"pending\",\"filed_issue\":17}\n",
    )
    .unwrap();
    let records = read_proposals(&proposals, root).unwrap();
    assert_eq!(records.len(), 1);
    assert_eq!(records[0].status, "pending");
    assert_eq!(records[0].filed_issue, Some(17));
    fs::write(&proposals, "not JSON\n").unwrap();
    assert!(
        read_proposals(&proposals, root)
            .unwrap_err()
            .starts_with("invalid proposal JSONL line 1:")
    );
    fs::write(
        &proposals,
        "{\"id\":\"lint-delta\",\"type\":\"lint\",\"target\":\"module:python/larch/lint/lint_delta.py\",\"run_date\":\"2026-08-09\",\"status\":\"pending\",\"filed_issue\":1}\n{\"id\":\"lint-delta\",\"type\":\"lint\",\"target\":\"module:python/larch/lint/lint_other.py\",\"run_date\":\"2026-08-09\",\"status\":\"pending\",\"filed_issue\":1}\n",
    )
    .unwrap();
    assert_eq!(
        read_proposals(&proposals, root).unwrap_err(),
        "conflicting stable proposal content for lint-delta"
    );

    let historical = proposal("lint-delta", "proposed", Some(1));
    let mut residual = proposal("lint-delta", "pending", None);
    residual.filed_issue = Some(1);
    let reconciled = reconcile_proposals(
        std::slice::from_ref(&historical),
        std::slice::from_ref(&residual),
        std::slice::from_ref(&historical),
    )
    .unwrap();
    assert_eq!(reconciled[0].status, "pending");
    let not_current = proposal("lint-delta", "adopted", Some(1));
    let preserved = reconcile_proposals(
        std::slice::from_ref(&historical),
        std::slice::from_ref(&residual),
        std::slice::from_ref(&not_current),
    )
    .unwrap();
    assert_eq!(preserved[0].status, "proposed");
    let new = proposal("new-proposal", "pending", None);
    assert_eq!(
        reconcile_proposals(&[], std::slice::from_ref(&new), &[])
            .unwrap()
            .len(),
        1
    );
    let mut changed = residual;
    changed.target = "module:python/larch/lint/lint_other.py".to_owned();
    assert_eq!(
        reconcile_proposals(std::slice::from_ref(&historical), &[changed], &[]).unwrap_err(),
        "conflicting stable proposal content for lint-delta"
    );
    let conflicting_issue = proposal("lint-delta", "pending", Some(2));
    assert_eq!(
        reconcile_proposals(std::slice::from_ref(&historical), &[conflicting_issue], &[],)
            .unwrap_err(),
        "conflicting filed issues for lint-delta"
    );
}

#[test]
fn state_file_reads_snapshots_and_locked_writes_fail_closed() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("state.json");
    assert!(read_state_file(&path).unwrap().is_none());
    let missing = state_snapshot(&path).unwrap();
    assert_eq!(missing.digest, "missing");
    assert_eq!(missing.data, None);

    fs::create_dir(&path).unwrap();
    assert!(read_state_file(&path).unwrap().is_none());
    assert!(
        state_snapshot(&path)
            .unwrap_err()
            .starts_with("analysis state is not a regular file:")
    );
    fs::remove_dir(&path).unwrap();
    fs::write(&path, "not JSON\n").unwrap();
    assert_eq!(read_state_file(&path).unwrap_err(), "invalid state");
    let first = state_snapshot(&path).unwrap();
    let before = fs::metadata(&path).unwrap();
    fs::write(&path, "different JSON length\n").unwrap();
    let after = fs::metadata(&path).unwrap();
    assert!(!same_state_metadata(&before, &after));
    assert_ne!(first.digest, state_snapshot(&path).unwrap().digest);

    let snapshot = state_snapshot(&path).unwrap();
    assert_eq!(
        write_state_locked(
            &path,
            state(Vec::new()),
            None,
            None,
            directory.path(),
            &snapshot,
        )
        .unwrap_err(),
        "existing state marker is invalid or unsupported"
    );
    let valid_snapshot = state_snapshot(&directory.path().join("fresh.json")).unwrap();
    let fresh = directory.path().join("fresh.json");
    let (written, digest) = write_state_locked(
        &fresh,
        state(Vec::new()),
        None,
        None,
        directory.path(),
        &valid_snapshot,
    )
    .unwrap();
    assert_eq!(written.repo, "owner/repo");
    assert_eq!(digest.len(), 64);

    let proposal_state = directory.path().join("proposal-state.json");
    let proposal_snapshot = state_snapshot(&proposal_state).unwrap();
    let proposal_file = directory.path().join("residual.jsonl");
    fs::write(
        &proposal_file,
        "{\"id\":\"lint-delta\",\"type\":\"lint\",\"target\":\"module:python/larch/lint/lint_delta.py\",\"run_date\":\"2026-08-09\",\"status\":\"pending\",\"filed_issue\":null}\n",
    )
    .unwrap();
    fs::create_dir_all(directory.path().join("python/larch/lint")).unwrap();
    fs::write(directory.path().join("python/larch/lint/lint_delta.py"), "").unwrap();
    write_state_locked(
        &proposal_state,
        state(Vec::new()),
        Some(&proposal_file),
        None,
        directory.path(),
        &proposal_snapshot,
    )
    .unwrap();
    let preserve_snapshot = state_snapshot(&proposal_state).unwrap();
    assert_eq!(
        write_state_locked(
            &proposal_state,
            state(Vec::new()),
            None,
            None,
            directory.path(),
            &preserve_snapshot,
        )
        .unwrap_err(),
        "--proposals-file is required to preserve proposal history"
    );
}

#[cfg(unix)]
#[test]
fn state_paths_and_locks_reject_untrusted_symlinks() {
    use std::os::unix::fs::symlink;

    let directory = tempfile::tempdir().unwrap();
    let outside = tempfile::tempdir().unwrap();
    let linked = directory.path().join("linked");
    symlink(outside.path(), &linked).unwrap();
    let state_path = linked.join("state.json");
    assert!(has_symlink_ancestor(&state_path));
    assert!(
        state_snapshot(&state_path)
            .unwrap_err()
            .starts_with("refusing symlinked analysis state:")
    );
    let lock_target = directory.path().join("state.json");
    let lock = directory.path().join(".state.json.lock");
    symlink(outside.path().join("lock"), lock).unwrap();
    assert!(
        lock_state(&lock_target)
            .unwrap_err()
            .starts_with("could not lock analysis state:")
    );
}

#[test]
fn typed_issue_fetch_uses_the_loopback_github_service_for_all_states() {
    let mut issue: Value = serde_json::from_str(include_str!(
        "../../../larch-adapters/fixtures/github_issue.json"
    ))
    .expect("issue fixture");
    issue["number"] = json!(71);
    issue["id"] = json!(71);
    let title = format!("{BUG_PREFIX} typed search");
    issue["title"] = json!(&title);
    issue["state"] = json!("closed");
    issue["closed_at"] = json!("2026-08-09T12:00:00Z");
    let response = json!({
        "total_count": 1,
        "incomplete_results": false,
        "items": [issue],
    })
    .to_string();
    let server = IssueServiceStub::start([
        IssueServiceExchange::any_json(200, response.clone()).expect("all-state exchange"),
        IssueServiceExchange::any_json(200, response).expect("closed-state exchange"),
    ])
    .expect("issue service");
    let base = server.base_url().to_owned();
    let service: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
        Arc::new(move || OctocrabGitHubService::with_test_base(&base));
    with_test_github_service(service, || {
        let all = fetch_issues("o/r", BUG_PREFIX, "all", 3).expect("all-state search");
        let closed = fetch_issues("o/r", BUG_PREFIX, "closed", 3).expect("closed-state search");
        assert_eq!(all[0].number, 71);
        assert_eq!(closed[0].title, title);
    });
    assert_eq!(server.finish().expect("requests").len(), 2);
}

#[test]
fn proposal_refresh_uses_the_typed_issue_service_and_records_both_evidence() {
    let directory = tempfile::tempdir().expect("temporary repository");
    fs::create_dir_all(directory.path().join("python/larch/lint")).expect("lint directory");
    fs::write(
        directory.path().join("python/larch/lint/lint_delta.py"),
        "# adopted\n",
    )
    .expect("lint module");
    let mut issue: Value = serde_json::from_str(include_str!(
        "../../../larch-adapters/fixtures/github_issue.json"
    ))
    .expect("issue fixture");
    issue["number"] = json!(71);
    issue["id"] = json!(71);
    issue["state"] = json!("closed");
    issue["state_reason"] = json!("completed");
    let server = IssueServiceStub::start([
        IssueServiceExchange::any_json(200, issue.to_string()).expect("typed issue exchange")
    ])
    .expect("issue service");
    let base = server.base_url().to_owned();
    let service: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
        Arc::new(move || OctocrabGitHubService::with_test_base(&base));
    with_test_github_service(service, || {
        let checked = refresh_proposals(
            &[proposal("lint-delta", "pending", Some(71))],
            directory.path(),
            "owner/repo",
        )
        .expect("proposal refresh");
        assert_eq!(checked[0].proposal.status, "adopted");
        assert_eq!(checked[0].adoption_evidence.as_deref(), Some("both"));
    });
    assert_eq!(server.finish().expect("requests").len(), 1);
}

#[test]
fn remaining_pure_branches_keep_zone_state_and_proposal_failures_explicit() {
    assert_eq!(github_state(GitHubIssueState::Open), "OPEN");
    assert_eq!(github_state(GitHubIssueState::All), "ALL");
    assert_eq!(
        resolve_zone_search("design", false, true),
        Err("--zones cannot be combined with verbal search text".to_owned())
    );
    assert_eq!(
        resolve_zone_search("  ", false, false),
        Err("--zones requires at least one non-empty zone name".to_owned())
    );
    assert_eq!(
        classify_origin(
            &format!("{BUG_PREFIX} no title signal"),
            &"long freeform evidence ".repeat(4),
            None,
        )
        .unknown_reason,
        Some("no-classification-signal")
    );
    for section in ["Suggested Fix(es)", "Suggested Fix", "Repro"] {
        let origin = classify_origin(
            &format!("{BUG_PREFIX} unclear"),
            &format!("## {section}\ntext"),
            None,
        );
        assert_eq!(origin.kind, "unknown");
        assert_eq!(origin.unknown_reason, Some("no-classification-signal"));
    }

    let directory = tempfile::tempdir().unwrap();
    fs::write(directory.path().join("ARCHITECTURAL_GUIDELINES.md"), "").unwrap();
    assert_eq!(coverage_index(directory.path()).guidelines_status, "empty");
    let non_directory = directory.path().join("not-a-directory");
    fs::write(&non_directory, "").unwrap();
    assert!(
        read_state_file(&non_directory.join("state.json"))
            .unwrap()
            .is_none()
    );
    assert!(!valid_target("unknown", "anything", None));

    let root = directory.path();
    fs::create_dir_all(root.join("python/larch/lint")).unwrap();
    fs::write(root.join("python/larch/lint/lint_delta.py"), "").unwrap();
    let proposals = root.join("proposals.jsonl");
    fs::write(
        &proposals,
        "{\"id\":\"lint-delta\",\"type\":\"lint\",\"target\":\"module:python/larch/lint/lint_delta.py\",\"run_date\":\"2026-08-09\",\"status\":\"pending\",\"filed_issue\":1}\n{\"id\":\"lint-delta\",\"type\":\"lint\",\"target\":\"module:python/larch/lint/lint_delta.py\",\"run_date\":\"2026-08-09\",\"status\":\"pending\",\"filed_issue\":2}\n",
    )
    .unwrap();
    assert_eq!(
        read_proposals(&proposals, root).unwrap_err(),
        "conflicting filed issues for lint-delta"
    );
    let historical = proposal("lint-delta", "adopted", Some(1));
    let duplicate = proposal("lint-delta", "pending", None);
    let merged = read_proposals(&proposals, root);
    assert!(merged.is_err());
    let updated = reconcile_proposals(
        std::slice::from_ref(&historical),
        std::slice::from_ref(&duplicate),
        &[],
    )
    .unwrap();
    assert_eq!(updated[0].status, "adopted");

    let state_path = root.join("state.json");
    let first = state_snapshot(&state_path).unwrap();
    write_state_locked(
        &state_path,
        state(vec![proposal("lint-delta", "pending", None)]),
        None,
        None,
        root,
        &first,
    )
    .unwrap();
    let next = state_snapshot(&state_path).unwrap();
    fs::write(
        &proposals,
        "{\"id\":\"lint-delta\",\"type\":\"lint\",\"target\":\"module:python/larch/lint/lint_delta.py\",\"run_date\":\"2026-08-09\",\"status\":\"adopted\",\"filed_issue\":null}\n",
    )
    .unwrap();
    let written = write_state_locked(
        &state_path,
        state(Vec::new()),
        Some(&proposals),
        None,
        root,
        &next,
    )
    .unwrap();
    assert_eq!(written.0.proposals[0].status, "pending");
}
