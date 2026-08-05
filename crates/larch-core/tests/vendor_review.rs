//! Table tests for codex/cursor review-result adapters (#8114).

use larch_core::{
    CURSOR_DEGRADED_RESPONSE, CURSOR_EMPTY_RESPONSE, CURSOR_NO_ISSUES_JSON, CodexReviewAuthPort,
    CursorResultWrite, CursorReviewAuthPort, LauncherArtifactKind, LauncherArtifactPaths,
    ResearchOutputValidator, ReviewAuthVerdict, VendorLaunchRequest, codex_compact_sentinel_offset,
    cursor_has_structured_findings, cursor_input_work_tokens, cursor_normalize_no_issues,
    cursor_output_tokens, effective_review_token_cap, is_cursor_empty_result,
    plan_cursor_result_write, plan_retry_artifact_reset, render_cap_hit_artifacts,
    render_cursor_empty_response, render_cursor_no_work_diag, resolve_codex_review_model,
    review_retry_delay_secs, run_codex_review_preflight, run_cursor_review_preflight,
};
use serde_json::Value;
use std::path::{Path, PathBuf};

fn fixture(name: &str) -> String {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/review")
        .join(name);
    std::fs::read_to_string(&path).unwrap_or_else(|error| {
        panic!("read fixture {}: {error}", path.display());
    })
}

fn fixture_json(name: &str) -> Value {
    serde_json::from_str(&fixture(name)).expect("fixture JSON")
}

struct OkCodexAuth;
impl CodexReviewAuthPort for OkCodexAuth {
    fn prepare_home(&self, _home: &Path, _trusted: &Path) -> ReviewAuthVerdict {
        ReviewAuthVerdict::ok()
    }
}

struct FailCodexAuth;
impl CodexReviewAuthPort for FailCodexAuth {
    fn prepare_home(&self, _home: &Path, _trusted: &Path) -> ReviewAuthVerdict {
        ReviewAuthVerdict::refuse(7, "codex auth setup failed")
    }
}

struct CursorAuth {
    ok: bool,
    preread: bool,
}
impl CursorReviewAuthPort for CursorAuth {
    fn auth_preflight(&self) -> ReviewAuthVerdict {
        if self.ok {
            ReviewAuthVerdict::ok()
        } else {
            ReviewAuthVerdict::refuse(1, "cursor auth missing")
        }
    }
    fn preread_service_token(&self) -> bool {
        self.preread
    }
}

struct AlwaysFailValidator;
impl ResearchOutputValidator for AlwaysFailValidator {
    fn validate(&self, _result_text: &str) -> bool {
        false
    }
}

#[test]
fn normalization_table_matches_recorded_cursor_outputs() {
    let structured = fixture("structured_findings.txt");
    let cases = [
        (
            "no_issues_bare.txt",
            CURSOR_NO_ISSUES_JSON.to_owned(),
            false,
        ),
        (
            "no_issues_literal.txt",
            CURSOR_NO_ISSUES_JSON.to_owned(),
            false,
        ),
        ("structured_findings.txt", structured, true),
        (
            "embedded_prose_sentinel.txt",
            CURSOR_NO_ISSUES_JSON.to_owned(),
            false,
        ),
    ];
    for (name, expected, structured) in cases {
        let raw = fixture(name);
        assert_eq!(
            cursor_has_structured_findings(&raw),
            structured,
            "{name} structured"
        );
        assert_eq!(
            cursor_normalize_no_issues(&raw),
            expected,
            "{name} normalize"
        );
    }
}

#[test]
fn token_accounting_matches_recorded_usage_shapes() {
    let cases = [
        ("canned_no_work_envelope.json", 0, 8),
        ("genuine_no_issues_envelope.json", 6200, 8),
        ("degraded_short_envelope.json", 10, 1001),
        ("usage_missing.json", 0, 0),
        ("usage_string_tokens.json", 15, 4),
        ("usage_non_numeric.json", 5, 0),
    ];
    for (name, input_work, output) in cases {
        let obj = fixture_json(name);
        assert_eq!(
            cursor_input_work_tokens(&obj),
            input_work,
            "{name} input work"
        );
        assert_eq!(cursor_output_tokens(&obj), output, "{name} output");
    }
}

#[test]
fn result_writes_cover_no_issues_degraded_and_empty() {
    let canned = fixture_json("canned_no_work_envelope.json");
    let result = canned["result"].as_str().expect("result");
    let normalized = cursor_normalize_no_issues(result);
    assert_eq!(
        plan_cursor_result_write(&normalized, &canned, None),
        CursorResultWrite::Degraded {
            diag: Some(render_cursor_no_work_diag(&canned))
        }
    );

    let genuine = fixture_json("genuine_no_issues_envelope.json");
    let genuine_result = genuine["result"].as_str().expect("result");
    assert_eq!(
        plan_cursor_result_write(&cursor_normalize_no_issues(genuine_result), &genuine, None),
        CursorResultWrite::Keep(CURSOR_NO_ISSUES_JSON.to_owned())
    );

    let short = fixture_json("degraded_short_envelope.json");
    assert_eq!(
        plan_cursor_result_write("short", &short, Some(&AlwaysFailValidator)),
        CursorResultWrite::Degraded { diag: None }
    );

    let empty = fixture_json("empty_result_envelope.json");
    assert!(is_cursor_empty_result(
        &fixture("empty_result_envelope.json"),
        true
    ));
    let (body, diag) = render_cursor_empty_response(&empty, 3);
    assert_eq!(body, CURSOR_EMPTY_RESPONSE);
    assert!(diag.contains("cursor-empty-result"));
    assert!(diag.contains("after 2 transient retries"));
    assert_eq!(CURSOR_DEGRADED_RESPONSE, "CURSOR_DEGRADED_RESPONSE\n");
}

#[test]
fn retry_artifact_reset_leaves_no_stale_codex_stream() {
    let plan = plan_retry_artifact_reset(
        "codex",
        "attempt",
        Some("stale sidecar stream"),
        Some("stale diag stream"),
        Some("{\"type\":\"event\"}\n"),
    );
    assert_eq!(
        plan.unlink_kinds,
        [
            LauncherArtifactKind::Sidecar,
            LauncherArtifactKind::Diag,
            LauncherArtifactKind::Events
        ]
    );
    assert_eq!(plan.history_entries.len(), 3);
    assert!(
        plan.history_entries
            .iter()
            .all(|entry| entry.contains("===== attempt"))
    );
    let paths = LauncherArtifactPaths::new("/session/review.txt");
    for kind in &plan.unlink_kinds {
        assert!(paths.path(*kind).as_os_str().len() > paths.output().as_os_str().len());
    }
}

#[test]
fn preflight_ports_and_model_resolution_and_cap_hit() {
    assert!(run_codex_review_preflight(&OkCodexAuth, Path::new("/h"), Path::new("/i")).is_ok());
    let refused =
        run_codex_review_preflight(&FailCodexAuth, Path::new("/h"), Path::new("/i")).unwrap_err();
    assert_eq!(refused.rc, 7);

    assert!(
        run_cursor_review_preflight(&CursorAuth {
            ok: true,
            preread: true
        })
        .is_ok()
    );
    let auth_fail = run_cursor_review_preflight(&CursorAuth {
        ok: false,
        preread: true,
    })
    .unwrap_err();
    assert!(auth_fail.failure_reason.contains("cursor-auth-preflight"));
    let preread_fail = run_cursor_review_preflight(&CursorAuth {
        ok: true,
        preread: false,
    })
    .unwrap_err();
    assert_eq!(preread_fail.rc, 2);
    let refusal = preread_fail.into_refusal("30", Path::new("/tmp/out.txt"));
    assert!(refusal.diag.contains("cursor-preread-service-token"));
    assert!(refusal.dirty_tree.contains("STATUS=unknown"));

    let request = resolve_codex_review_model(
        VendorLaunchRequest::new("/repo", "/tmp/out", "prompt"),
        vec!["-m".to_owned(), "gpt".to_owned()],
    );
    assert_eq!(request.model_args, ["-m", "gpt"]);

    assert_eq!(effective_review_token_cap(None, Some("25")), Some(25));
    let cap = render_cap_hit_artifacts(25, "TOTAL=99 STATUS=cap_hit\n", None);
    assert_eq!(cap.output, "STATUS=cap_hit\n");
    assert!(cap.warning.contains("25 tokens exceeded (99"));
    assert_eq!(review_retry_delay_secs(3, None, true, 1), 0);
    assert_eq!(review_retry_delay_secs(3, Some("2"), false, 1), 2);
    assert_eq!(
        codex_compact_sentinel_offset("LARCH_PROMPT_SENTINEL=1\n"),
        Some(0)
    );
}
