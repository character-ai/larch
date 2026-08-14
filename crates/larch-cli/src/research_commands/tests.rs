//! Offline unit coverage for the four `/research` Rust commands.

use std::path::Path;

use tempfile::tempdir;

use super::citations::{ValidateRequest, validate_citations};
use super::render::{FindingsContext, render_findings_issue_batch};
use super::{
    FetchResult, FetchSeams, Resolver, check_fileline, compute_banner, extract_dois,
    extract_filelines, extract_urls, fetch_url, is_blocked_ip, is_private_hostname, run_planner_core,
    sanitize_planner_line,
};

fn seams<'a>(
    resolver: &'a Resolver<'a>,
    connector: &'a (dyn Fn(&str, &str, u64) -> Result<u16, &'static str> + 'a),
) -> FetchSeams<'a> {
    FetchSeams {
        resolver: Some(resolver),
        connector: Some(connector),
    }
}

#[test]
fn banner_counts_only_fallback_status_lines() {
    let dir = tempdir().expect("tempdir");
    let path = dir.path().join("lane-status.txt");
    std::fs::write(
        &path,
        "RESEARCH_A_STATUS=fallback_claude\nRESEARCH_B_STATUS=ok\nRESEARCH_C_STATUS=fallback_x\n",
    )
    .expect("write");
    let banner = compute_banner(&path);
    assert!(banner.contains("2 of 4"), "banner was {banner:?}");
    assert_eq!(compute_banner(Path::new("/no/such/file")), "");
}

#[test]
fn planner_sanitizes_and_classifies_each_branch() {
    assert_eq!(sanitize_planner_line("- What now?\t"), "What now?");
    let dir = tempdir().expect("tempdir");
    let output = dir.path().join("out.txt");

    let empty = dir.path().join("empty.txt");
    std::fs::write(&empty, "").expect("write");
    assert_eq!(run_planner_core(&empty, &output), ("empty_input", 1));

    let one = dir.path().join("one.txt");
    std::fs::write(&one, "Only one question?\n").expect("write");
    assert_eq!(run_planner_core(&one, &output), ("count_below_minimum", 1));

    let five = dir.path().join("five.txt");
    std::fs::write(&five, "a?\nb?\nc?\nd?\ne?\n").expect("write");
    assert_eq!(run_planner_core(&five, &output), ("count_above_maximum", 1));

    let collision = dir.path().join("collision.txt");
    std::fs::write(&collision, "a||b?\nc?\n").expect("write");
    assert_eq!(run_planner_core(&collision, &output), ("delimiter_collision", 1));

    let good = dir.path().join("good.txt");
    std::fs::write(&good, "- First?\n* Second?\nnot a question\n").expect("write");
    assert_eq!(run_planner_core(&good, &output), ("success", 0));
    assert_eq!(std::fs::read_to_string(&output).expect("read"), "First?\nSecond?\n");

    let bad = dir.path().join("bad.txt");
    std::fs::write(&bad, "a?\nb?\n").expect("write");
    let missing_parent = dir.path().join("nope").join("out.txt");
    assert_eq!(run_planner_core(&bad, &missing_parent), ("bad_path", 2));
}

#[test]
fn extractors_sort_dedupe_and_trim() {
    let text = "See https://arxiv.org/abs/1. Also https://arxiv.org/abs/1, and 10.1234/foo; plus src/main.rs:10-20 and Makefile:3.";
    assert_eq!(extract_urls(text), vec!["https://arxiv.org/abs/1".to_owned()]);
    assert_eq!(extract_dois(text), vec!["10.1234/foo".to_owned()]);
    let filelines = extract_filelines(text);
    assert!(filelines.contains(&"src/main.rs:10-20".to_owned()), "{filelines:?}");
    assert!(filelines.contains(&"Makefile:3".to_owned()), "{filelines:?}");
}

#[test]
fn ssrf_guards_reject_private_targets() {
    assert!(is_blocked_ip("127.0.0.1"));
    assert!(is_blocked_ip("10.0.0.1"));
    assert!(is_blocked_ip("169.254.1.1"));
    assert!(is_blocked_ip("100.64.0.1"));
    assert!(is_blocked_ip("::1"));
    assert!(is_blocked_ip("fc00::1"));
    assert!(!is_blocked_ip("93.184.216.34"));
    assert!(is_private_hostname("localhost"));
    assert!(is_private_hostname("api.localhost"));
    assert!(!is_private_hostname("example.com"));
}

#[test]
fn fetch_url_maps_the_full_status_taxonomy() {
    let resolver = |_host: &str, _port: u16| Ok(vec!["93.184.216.34".to_owned()]);
    let ok = |_url: &str, _ip: &str, _timeout: u64| Ok(200u16);
    assert_eq!(fetch_url("https://example.com/", 10, &seams(&resolver, &ok)).token(), "PASS");

    let redirect = |_url: &str, _ip: &str, _timeout: u64| Ok(301u16);
    assert_eq!(
        fetch_url("https://example.com/", 10, &seams(&resolver, &redirect)).token(),
        "UNKNOWN(redirect-not-followed)"
    );
    let not_found = |_url: &str, _ip: &str, _timeout: u64| Ok(404u16);
    assert_eq!(
        fetch_url("https://example.com/", 10, &seams(&resolver, &not_found)).token(),
        "FAIL(head-not-found)"
    );
    let forbidden = |_url: &str, _ip: &str, _timeout: u64| Ok(403u16);
    assert_eq!(
        fetch_url("https://example.com/", 10, &seams(&resolver, &forbidden)).token(),
        "UNKNOWN(head-not-supported)"
    );

    assert_eq!(
        fetch_url("http://example.com/", 10, &FetchSeams::default()).token(),
        "FAIL(non-https)"
    );
    assert_eq!(
        fetch_url("https://localhost/", 10, &FetchSeams::default()).token(),
        "FAIL(ssrf-private-host)"
    );

    let private_resolver = |_host: &str, _port: u16| Ok(vec!["10.0.0.5".to_owned()]);
    assert_eq!(
        fetch_url("https://example.com/", 10, &seams(&private_resolver, &ok)).token(),
        "FAIL(ssrf-private-resolved)"
    );
    let timeout_resolver = |_host: &str, _port: u16| Err("timeout");
    assert_eq!(
        fetch_url("https://example.com/", 10, &seams(&timeout_resolver, &ok)).token(),
        "UNKNOWN(timeout)"
    );
}

#[test]
fn check_fileline_covers_existence_and_range() {
    let dir = tempdir().expect("tempdir");
    let root = dir.path().canonicalize().expect("canonicalize");
    std::fs::write(root.join("file.txt"), "one\ntwo\nthree\n").expect("write");

    assert_eq!(check_fileline("file.txt", Some(&root)), FetchResult::pass());
    assert_eq!(check_fileline("file.txt:2", Some(&root)), FetchResult::pass());
    assert_eq!(
        check_fileline("file.txt:9", Some(&root)),
        FetchResult::new("FAIL", "line-out-of-range")
    );
    assert_eq!(
        check_fileline("file.txt:3-2", Some(&root)),
        FetchResult::new("FAIL", "line-range-empty")
    );
    assert_eq!(
        check_fileline("missing.txt:1", Some(&root)),
        FetchResult::new("FAIL", "file-not-found")
    );
    assert_eq!(
        check_fileline("file.txt", Some(Path::new("/no/such/root"))),
        FetchResult::new("FAIL", "file-not-found")
    );
}

#[test]
fn validate_citations_writes_the_no_op_sidecar() {
    let dir = tempdir().expect("tempdir");
    let report = dir.path().join("report.md");
    std::fs::write(&report, "No citations here.\n").expect("write");
    let output = dir.path().join("sidecar.md");
    let request = ValidateRequest {
        report: &report,
        output: &output,
        tmpdir: &dir.path().join("tmp"),
        budget_seconds: 5,
        per_fetch_timeout: 1,
        max_claims: 200,
    };
    let counts = validate_citations(&request, None, None);
    assert_eq!(counts, (0, 0, 0, 0));
    let sidecar = std::fs::read_to_string(&output).expect("read");
    assert!(sidecar.contains("Citation validation is a no-op"), "{sidecar}");
}

#[test]
fn validate_citations_renders_ledger_rows_with_injected_fetcher() {
    let dir = tempdir().expect("tempdir");
    let root = dir.path().canonicalize().expect("canonicalize");
    std::fs::write(root.join("src.rs"), "line\n").expect("write");
    let report = root.join("report.md");
    std::fs::write(
        &report,
        "Refs: https://arxiv.org/abs/2 and 10.5555/valid and src.rs:1 plus http://x.test/\n",
    )
    .expect("write");
    let output = root.join("sidecar.md");
    let request = ValidateRequest {
        report: &report,
        output: &output,
        tmpdir: &root.join("tmp"),
        budget_seconds: 5,
        per_fetch_timeout: 1,
        max_claims: 200,
    };
    let fetcher = |target: &str| {
        if target.contains("arxiv") || target.contains("doi.org") {
            FetchResult::pass()
        } else {
            FetchResult::new("FAIL", "non-https")
        }
    };
    let (pass, fail, unknown, total) = validate_citations(&request, Some(&fetcher), Some(&root));
    assert_eq!(total, 4, "pass={pass} fail={fail} unknown={unknown}");
    let sidecar = std::fs::read_to_string(&output).expect("read");
    assert!(sidecar.contains("| `src.rs:1` | file-line | PASS |"), "{sidecar}");
    assert!(sidecar.contains("Domain credibility"), "{sidecar}");
}

#[test]
fn findings_batch_reports_presence_and_absence() {
    let context = FindingsContext {
        research_question: "Q?",
        branch: "main",
        commit: "abc123",
        timestamp: "2026-08-14T00:00:00Z",
    };
    let (absent_count, _payload, section_absent) =
        render_findings_issue_batch("## Report\n\nNo findings.\n", &context);
    assert_eq!(absent_count, 0);
    assert!(section_absent);

    let report = "### Findings Summary\n\n1. First problem here.\n2. Second problem here.\n\n### Risk Assessment\n- High\n";
    let (count, payload, missing) = render_findings_issue_batch(report, &context);
    assert_eq!(count, 2);
    assert!(!missing);
    assert!(payload.contains("### First problem here"), "{payload}");
    assert!(payload.contains("**Risk**: High"), "{payload}");
}
