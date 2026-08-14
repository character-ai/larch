//! Offline unit coverage for the four `/research` Rust commands.

use std::collections::BTreeMap;
use std::ffi::OsString;
use std::path::Path;

use tempfile::tempdir;

use super::citations::{ValidateRequest, validate_citations};
use super::render::{FindingsContext, render_findings_issue_batch};
use super::{
    FetchResult, FetchSeams, Resolver, check_fileline, compute_banner, extract_dois,
    extract_filelines, extract_urls, fetch_url, is_blocked_ip, is_private_hostname,
    run_planner_core, sanitize_planner_line,
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
    assert_eq!(
        run_planner_core(&collision, &output),
        ("delimiter_collision", 1)
    );

    let good = dir.path().join("good.txt");
    std::fs::write(&good, "- First?\n* Second?\nnot a question\n").expect("write");
    assert_eq!(run_planner_core(&good, &output), ("success", 0));
    assert_eq!(
        std::fs::read_to_string(&output).expect("read"),
        "First?\nSecond?\n"
    );

    let bad = dir.path().join("bad.txt");
    std::fs::write(&bad, "a?\nb?\n").expect("write");
    let missing_parent = dir.path().join("nope").join("out.txt");
    assert_eq!(run_planner_core(&bad, &missing_parent), ("bad_path", 2));
}

#[test]
fn extractors_sort_dedupe_and_trim() {
    let text = "See https://arxiv.org/abs/1. Also https://arxiv.org/abs/1, and 10.1234/foo; plus src/main.rs:10-20 and Makefile:3.";
    assert_eq!(
        extract_urls(text),
        vec!["https://arxiv.org/abs/1".to_owned()]
    );
    assert_eq!(extract_dois(text), vec!["10.1234/foo".to_owned()]);
    let filelines = extract_filelines(text);
    assert!(
        filelines.contains(&"src/main.rs:10-20".to_owned()),
        "{filelines:?}"
    );
    assert!(
        filelines.contains(&"Makefile:3".to_owned()),
        "{filelines:?}"
    );
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
    assert_eq!(
        fetch_url("https://example.com/", 10, &seams(&resolver, &ok)).token(),
        "PASS"
    );

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
    assert_eq!(
        check_fileline("file.txt:2", Some(&root)),
        FetchResult::pass()
    );
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
    assert!(
        sidecar.contains("Citation validation is a no-op"),
        "{sidecar}"
    );
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
    assert!(
        sidecar.contains("| `src.rs:1` | file-line | PASS |"),
        "{sidecar}"
    );
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

// ---------------------------------------------------------------------------
// CLI entrypoints
// ---------------------------------------------------------------------------

#[test]
fn banner_entrypoint_covers_help_missing_and_emit() {
    let _help = super::banner(&[OsString::from("--help")]);
    let _missing = super::banner(&[]);
    let dir = tempdir().expect("tempdir");
    let status = dir.path().join("lane.txt");
    std::fs::write(&status, "RESEARCH_A_STATUS=fallback_claude\n").expect("write");
    let _emitted = super::banner(&[status.into_os_string()]);
}

#[test]
fn run_planner_entrypoint_writes_output_and_reports_reasons() {
    let dir = tempdir().expect("tempdir");
    let _help = super::run_planner(&[OsString::from("--help")]);

    let raw = dir.path().join("raw.txt");
    std::fs::write(&raw, "- One?\n* Two?\nnot a question\n").expect("write");

    // Missing --output surfaces the missing_arg refusal.
    let _missing = super::run_planner(&[OsString::from("--raw"), raw.clone().into_os_string()]);

    let output = dir.path().join("plan.txt");
    let ok_args = vec![
        OsString::from("--raw"),
        raw.into_os_string(),
        OsString::from("--output"),
        output.clone().into_os_string(),
    ];
    let _ok = super::run_planner(&ok_args);
    assert_eq!(
        std::fs::read_to_string(&output).expect("read"),
        "One?\nTwo?\n"
    );

    // An empty raw file surfaces a REASON refusal instead of writing output.
    let empty = dir.path().join("empty.txt");
    std::fs::write(&empty, "").expect("write");
    let reason_args = vec![
        OsString::from("--raw"),
        empty.into_os_string(),
        OsString::from("--output"),
        dir.path().join("unused.txt").into_os_string(),
    ];
    let _reason = super::run_planner(&reason_args);
    assert!(!dir.path().join("unused.txt").exists());
}

fn findings_batch_args(report: &Path, output: &Path, question: &Path) -> Vec<OsString> {
    vec![
        OsString::from("--report"),
        report.as_os_str().to_owned(),
        OsString::from("--output"),
        output.as_os_str().to_owned(),
        OsString::from("--research-question-file"),
        question.as_os_str().to_owned(),
        OsString::from("--branch"),
        OsString::from("main"),
        OsString::from("--commit"),
        OsString::from("abc123"),
    ]
}

#[test]
fn render_findings_batch_entrypoint_covers_every_exit() {
    let dir = tempdir().expect("tempdir");
    let _help = super::render_findings_batch(&[OsString::from("--help")]);
    // A missing required option surfaces the usage diagnostic.
    let _bad = super::render_findings_batch(&[OsString::from("--report"), OsString::from("/x")]);

    let question = dir.path().join("question.txt");
    std::fs::write(&question, "\n\nWhat is the answer?\n").expect("write");

    // Success path: findings present, output written, COUNT emitted.
    let report = dir.path().join("report.md");
    std::fs::write(
        &report,
        "### Findings Summary\n\n1. Alpha finding here.\n2. Beta finding here.\n\n### Risk Assessment\n- Low\n",
    )
    .expect("write");
    let output = dir.path().join("batch.md");
    let _ok = super::render_findings_batch(&findings_batch_args(&report, &output, &question));
    let payload = std::fs::read_to_string(&output).expect("read");
    assert!(payload.contains("### Alpha finding here"), "{payload}");

    // Report file not found returns the not-found diagnostic.
    let _missing = super::render_findings_batch(&findings_batch_args(
        &dir.path().join("nope.md"),
        &output,
        &question,
    ));

    // Empty Findings Summary section: zero findings, empty-section warning.
    let empty_report = dir.path().join("empty.md");
    std::fs::write(
        &empty_report,
        "### Findings Summary\n\n### Risk Assessment\n",
    )
    .expect("write");
    let empty_output = dir.path().join("empty-batch.md");
    let _empty = super::render_findings_batch(&findings_batch_args(
        &empty_report,
        &empty_output,
        &dir.path().join("absent-question.txt"),
    ));

    // Absent Findings Summary section: zero findings, section-absent warning.
    let absent_report = dir.path().join("absent.md");
    std::fs::write(&absent_report, "## Report\n\nNo findings section.\n").expect("write");
    let absent_output = dir.path().join("absent-batch.md");
    let _absent = super::render_findings_batch(&findings_batch_args(
        &absent_report,
        &absent_output,
        &question,
    ));
}

#[test]
fn validate_citations_command_covers_run_paths() {
    let dir = tempdir().expect("tempdir");
    let root = dir.path().canonicalize().expect("canonicalize");
    let _help = super::validate_citations_command(&[OsString::from("--help")]);
    // Missing --tmpdir surfaces the usage refusal.
    let _missing = super::validate_citations_command(&[
        OsString::from("--report"),
        OsString::from("/x"),
        OsString::from("--output"),
        OsString::from("/y"),
    ]);

    let report = root.join("report.md");
    std::fs::write(&report, "See Cargo.toml:1 for the manifest.\n").expect("write");
    let output = root.join("sidecar.md");
    let tmp = root.join("tmp");

    // Invalid limit writes a degraded sidecar and refuses.
    let bad_limit = vec![
        OsString::from("--report"),
        report.as_os_str().to_owned(),
        OsString::from("--output"),
        output.as_os_str().to_owned(),
        OsString::from("--tmpdir"),
        tmp.as_os_str().to_owned(),
        OsString::from("--budget-seconds"),
        OsString::from("0"),
    ];
    let _bad = super::validate_citations_command(&bad_limit);
    assert!(
        std::fs::read_to_string(&output)
            .expect("read")
            .contains("invalid argument"),
    );

    // Success path with only a file-line claim needs no network.
    let ok_args = vec![
        OsString::from("--report"),
        report.as_os_str().to_owned(),
        OsString::from("--output"),
        output.as_os_str().to_owned(),
        OsString::from("--tmpdir"),
        tmp.as_os_str().to_owned(),
    ];
    let _ok = super::validate_citations_command(&ok_args);
    assert!(
        std::fs::read_to_string(&output)
            .expect("read")
            .contains("Citation Validation"),
    );
}

// ---------------------------------------------------------------------------
// citations ledger, credibility, and degraded sidecars
// ---------------------------------------------------------------------------

#[test]
fn validate_citations_reports_degraded_for_unreadable_reports() {
    let dir = tempdir().expect("tempdir");
    let tmp = dir.path().join("tmp");

    let missing_output = dir.path().join("missing.md");
    let missing = ValidateRequest {
        report: &dir.path().join("nope.md"),
        output: &missing_output,
        tmpdir: &tmp,
        budget_seconds: 5,
        per_fetch_timeout: 1,
        max_claims: 200,
    };
    assert_eq!(validate_citations(&missing, None, None), (0, 0, 0, 0));
    assert!(
        std::fs::read_to_string(&missing_output)
            .expect("read")
            .contains("input report not readable"),
    );

    let subdir = dir.path().join("as-dir");
    std::fs::create_dir(&subdir).expect("mkdir");
    let dir_output = dir.path().join("dir.md");
    let as_dir = ValidateRequest {
        report: &subdir,
        output: &dir_output,
        tmpdir: &tmp,
        budget_seconds: 5,
        per_fetch_timeout: 1,
        max_claims: 200,
    };
    assert_eq!(validate_citations(&as_dir, None, None), (0, 0, 0, 0));
}

#[test]
fn validate_citations_classifies_hosts_dois_and_credibility_tiers() {
    let dir = tempdir().expect("tempdir");
    let root = dir.path().canonicalize().expect("canonicalize");
    std::fs::write(root.join("README.md"), "line one\n").expect("write");
    let report = root.join("report.md");
    std::fs::write(
        &report,
        "Refs: https://github.com/a/b and https://en.wikipedia.org/wiki/T and https://example.com/p and 10.5555/aaa and 10.6666/bbb and README.md:1\n",
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
        if target.contains("10.5555") {
            FetchResult::new("UNKNOWN", "redirect-not-followed")
        } else if target.contains("doi.org") {
            FetchResult::new("FAIL", "head-not-found")
        } else {
            FetchResult::pass()
        }
    };
    let (_pass, _fail, _unknown, total) = validate_citations(&request, Some(&fetcher), Some(&root));
    assert!(total >= 6, "total was {total}");
    let sidecar = std::fs::read_to_string(&output).expect("read");
    assert!(sidecar.contains("well-known reputable origin"), "{sidecar}");
    assert!(sidecar.contains("no allow-list entry"), "{sidecar}");
    assert!(
        sidecar.contains("| `README.md:1` | file-line | PASS |"),
        "{sidecar}"
    );
}

#[test]
fn validate_citations_truncates_and_clips_long_claims() {
    let dir = tempdir().expect("tempdir");
    let root = dir.path().canonicalize().expect("canonicalize");
    let long_path: String = "a".repeat(100);
    let report = root.join("report.md");
    std::fs::write(
        &report,
        format!("Link https://example.com/{long_path} and 10.5555/keep\n"),
    )
    .expect("write");
    let output = root.join("sidecar.md");
    let request = ValidateRequest {
        report: &report,
        output: &output,
        tmpdir: &root.join("tmp"),
        budget_seconds: 5,
        per_fetch_timeout: 1,
        max_claims: 1,
    };
    let fetcher = |_target: &str| FetchResult::pass();
    let _counts = validate_citations(&request, Some(&fetcher), Some(&root));
    let sidecar = std::fs::read_to_string(&output).expect("read");
    assert!(sidecar.contains("..."), "{sidecar}");
    assert!(sidecar.contains("max-claims"), "{sidecar}");
}

// ---------------------------------------------------------------------------
// render splitter, titles, escaping, and metadata
// ---------------------------------------------------------------------------

fn render_context() -> FindingsContext<'static> {
    FindingsContext {
        research_question: "Q?",
        branch: "main",
        commit: "abc123",
        timestamp: "2026-08-14T00:00:00Z",
    }
}

#[test]
fn render_findings_covers_fences_subquestions_and_open_questions() {
    let report = r"### Findings Summary

1. First finding sentence. Second sentence ignored.
   more detail on first
2. Second finding here.

```text
inside fence line
```

#### Subquestion 2

- Bullet finding one
- Bullet finding two

### Risk Assessment
- High
> quoted risk note

### Open Questions
- What about scaling?
";
    let (count, payload, section_absent) = render_findings_issue_batch(report, &render_context());
    assert!(count >= 1, "count was {count}");
    assert!(!section_absent);
    assert!(payload.contains("### First finding sentence"), "{payload}");
    assert!(payload.contains("**Risk**: High"), "{payload}");
    assert!(payload.contains("**Open questions**"), "{payload}");
}

#[test]
fn render_findings_covers_titles_and_heading_escapes() {
    let report = r"### Findings Summary

1. ...............
2. This finding has an extremely long descriptive title that certainly exceeds eighty characters for truncation coverage indeed yes absolutely.
### fake heading
```
fenced body
```
";
    let (count, payload, _absent) = render_findings_issue_batch(report, &render_context());
    assert!(count >= 1, "count was {count}");
    assert!(payload.contains("### Finding 1"), "{payload}");
    assert!(
        payload.contains("### This finding has an extremely long descriptive title"),
        "{payload}"
    );
    assert!(payload.contains("\\### fake heading"), "{payload}");
}

#[test]
fn render_findings_covers_paragraph_mode() {
    let report = "### Findings Summary\n\nSome prose finding paragraph.\nContinued line.\n\nAnother paragraph after blank.\n";
    let (count, _payload, _absent) = render_findings_issue_batch(report, &render_context());
    assert!(count >= 1, "count was {count}");
}

// ---------------------------------------------------------------------------
// SSRF, URL parsing, status taxonomy, and file-line internals
// ---------------------------------------------------------------------------

#[test]
fn classify_status_covers_client_server_and_unrecognized() {
    assert_eq!(
        super::classify_status(418).token(),
        "FAIL(head-client-error-418)"
    );
    assert_eq!(
        super::classify_status(503).token(),
        "FAIL(head-server-error-503)"
    );
    assert_eq!(
        super::classify_status(600).token(),
        "UNKNOWN(unrecognized-status-600)"
    );
}

#[test]
fn url_parts_parse_covers_ipv6_userinfo_and_bad_ports() {
    let v6 = super::UrlParts::parse("https://[::1]:8443/path").expect("v6");
    assert_eq!(v6.host, "::1");
    assert_eq!(v6.port, 8443);
    let userinfo = super::UrlParts::parse("https://user@Example.COM/x").expect("userinfo");
    assert_eq!(userinfo.host, "example.com");
    assert_eq!(userinfo.port, 443);
    assert!(super::UrlParts::parse("https://host:999999/").is_none());
    assert!(super::UrlParts::parse("http://plain/").is_none());
}

#[test]
fn resolve_public_ips_refuses_localhost_via_the_real_resolver() {
    let (addresses, refusal) = super::resolve_public_ips("localhost", 443, 2, None);
    assert!(addresses.is_empty());
    assert_eq!(refusal, Some("ssrf-private-resolved"));
}

#[test]
fn parallel_fetch_results_handles_empty_and_missing_reports() {
    let empty: BTreeMap<String, String> = BTreeMap::new();
    let never = |_target: &str| FetchResult::pass();
    assert!(super::parallel_fetch_results(&empty, 1, 1, &never).is_empty());

    let mut slow_targets: BTreeMap<String, String> = BTreeMap::new();
    slow_targets.insert("k".to_owned(), "https://example.com/".to_owned());
    let slow = |_target: &str| {
        std::thread::sleep(std::time::Duration::from_millis(1500));
        FetchResult::pass()
    };
    let results = super::parallel_fetch_results(&slow_targets, 1, 1, &slow);
    assert_eq!(
        results.get("k").expect("filled").token(),
        "UNKNOWN(timeout)"
    );
}

#[test]
fn check_fileline_covers_directories_and_git_root_probe() {
    let dir = tempdir().expect("tempdir");
    let root = dir.path().canonicalize().expect("canonicalize");
    std::fs::create_dir(root.join("sub")).expect("mkdir");
    assert_eq!(
        check_fileline("sub", Some(&root)),
        FetchResult::new("FAIL", "path-is-directory")
    );

    // A `None` root probes the surrounding git checkout for the manifest.
    assert_eq!(check_fileline("Cargo.toml", None), FetchResult::pass());
}
