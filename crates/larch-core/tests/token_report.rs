//! Differential parity tests for the `/report-tokens` analyzer and renderer.
//!
//! Every expectation under `tests/data/token_report` was recorded from the
//! retired Python implementation over the same three records before deletion,
//! so a drift in the Rust renderer shows up as a byte diff rather than a
//! judgement call.

use std::{fs, path::PathBuf};

use larch_core::report::{
    PricedRun, ReportSection, RunCost, SectionPriority, TokenPhaseRow, TokenRates, TokenRunRecord,
    TokenVendor, VendorTotals, assemble_issue_body, cache_ndjson, daily_costs, display_rates,
    render_report, title_for_skill,
};

/// GitHub's issue-body limit, mirroring `config.GITHUB_ISSUE_BODY_MAX_BYTES`.
const BODY_LIMIT: usize = 65_536;

fn fixture(name: &str) -> String {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/data/token_report")
        .join(name);
    fs::read_to_string(&path).unwrap_or_else(|error| panic!("read {}: {error}", path.display()))
}

const fn totals(
    input: i64,
    cache_read: i64,
    cache_create_5m: i64,
    cached_input: i64,
    output: i64,
) -> VendorTotals {
    VendorTotals {
        input,
        cache_read,
        cache_create: 0,
        cache_create_5m,
        cache_create_1h: 0,
        cached_input,
        output,
        total: 0,
    }
}

fn phase(
    vendor: TokenVendor,
    step: &str,
    input: i64,
    cache_read: i64,
    output: i64,
    total: i64,
) -> TokenPhaseRow {
    TokenPhaseRow {
        vendor,
        step: step.to_owned(),
        input,
        cache_read,
        cache_create: 0,
        output,
        total,
    }
}

fn record(number: i64, started_at: &str, closed_at: &str) -> TokenRunRecord {
    TokenRunRecord {
        number,
        title: format!("Issue #{number}"),
        url: format!("https://github.com/character-ai/larch/issues/{number}"),
        started_at: started_at.to_owned(),
        closed_at: closed_at.to_owned(),
        claude: VendorTotals::default(),
        codex: VendorTotals::default(),
        cursor: VendorTotals::default(),
        claude_sub: VendorTotals::default(),
        phase_rows: Vec::new(),
        raw_report: serde_json::Map::new(),
        main_model: String::new(),
    }
}

/// The three recorded runs the compatibility fixtures were rendered from.
fn runs() -> Vec<PricedRun> {
    let mut first = record(101, "2026-05-01T10:00:00Z", "2026-05-01T12:00:00Z");
    first.claude = totals(1000, 20_000, 500, 0, 3000);
    first.codex = totals(4000, 0, 0, 1000, 900);
    first.cursor = totals(1500, 700, 0, 0, 250);
    first.claude_sub = totals(800, 100, 0, 0, 60);
    first.phase_rows = vec![
        phase(
            TokenVendor::Claude,
            "Step 2 \u{2014} implementation",
            1000,
            20_000,
            3000,
            24_000,
        ),
        phase(
            TokenVendor::Codex,
            "Step 5 \u{2014} review",
            4000,
            0,
            900,
            4900,
        ),
    ];
    let mut second = record(102, "2026-05-02T09:30:00Z", "2026-05-02T11:00:00Z");
    second.claude = totals(500, 1000, 0, 0, 200);
    second.codex = totals(100, 0, 0, 0, 10);
    second.phase_rows = vec![phase(
        TokenVendor::Claude,
        "Step 2 \u{2014} implementation",
        500,
        1000,
        200,
        1700,
    )];
    let mut third = record(103, "", "");
    third.claude = totals(10, 0, 0, 0, 5);
    vec![
        PricedRun {
            record: first,
            cost: RunCost {
                claude_cost: 1.23,
                codex_cost: 0.45,
                cursor_cost: 0.11,
                cursor_composer_cost: Some(0.08),
                cursor_grok_cost: Some(0.03),
                claude_sub_cost: 0.07,
                total_cost: 1.86,
                priced_by_token_cost: true,
            },
        },
        PricedRun {
            record: second,
            cost: RunCost {
                claude_cost: 0.30,
                codex_cost: 0.02,
                cursor_cost: 0.0,
                cursor_composer_cost: None,
                cursor_grok_cost: None,
                claude_sub_cost: 0.0,
                total_cost: 0.32,
                priced_by_token_cost: false,
            },
        },
        PricedRun {
            record: third,
            cost: RunCost {
                claude_cost: 0.01,
                codex_cost: 0.0,
                cursor_cost: 0.0,
                cursor_composer_cost: None,
                cursor_grok_cost: None,
                claude_sub_cost: 0.0,
                total_cost: 0.01,
                priced_by_token_cost: true,
            },
        },
    ]
}

fn default_rates() -> TokenRates {
    display_rates(
        &std::collections::BTreeMap::new(),
        "",
        &mut larch_core::report::TokenObservations::default(),
    )
}

fn render(
    skill: &str,
    runs: &[PricedRun],
    actual: Option<f64>,
    include: bool,
) -> (String, Vec<ReportSection>) {
    let rendered = render_report(skill, runs, &default_rates(), actual, include, "<CACHE>");
    (rendered.body, rendered.sections)
}

#[test]
fn report_body_matches_the_recorded_contract() {
    let runs = runs();
    for (skill, actual, include, name) in [
        ("design", None, false, "body-design-none-stdout.txt"),
        ("design", Some(2.5), false, "body-design-actual-stdout.txt"),
        ("design", Some(2.5), true, "body-design-actual-issue.txt"),
        ("implement", None, false, "body-implement-none-stdout.txt"),
        (
            "implement",
            Some(2.5),
            false,
            "body-implement-actual-stdout.txt",
        ),
        (
            "implement",
            Some(2.5),
            true,
            "body-implement-actual-issue.txt",
        ),
    ] {
        let (body, _sections) = render(skill, &runs, actual, include);
        assert_eq!(body, fixture(name), "body drift for {name}");
    }
}

#[test]
fn detailed_cursor_split_adds_its_vendor_rows() {
    let runs = runs();
    let (body, sections) = render("implement", &runs[..1], None, false);
    assert_eq!(body, fixture("body-detailed.txt"));
    let (issue, omitted) =
        assemble_issue_body(&sections, BODY_LIMIT, "implement").expect("assemble");
    assert_eq!(issue, fixture("issue-detailed.txt"));
    assert!(omitted.is_empty());
}

#[test]
fn issue_body_matches_the_recorded_contract() {
    let runs = runs();
    for (skill, actual, include, name) in [
        ("design", None, false, "issue-design-none-stdout.txt"),
        ("design", Some(2.5), true, "issue-design-actual-issue.txt"),
        ("implement", None, false, "issue-implement-none-stdout.txt"),
        (
            "implement",
            Some(2.5),
            true,
            "issue-implement-actual-issue.txt",
        ),
    ] {
        let (_body, sections) = render(skill, &runs, actual, include);
        let (issue, omitted) = assemble_issue_body(&sections, BODY_LIMIT, skill).expect("assemble");
        assert_eq!(issue, fixture(name), "issue drift for {name}");
        assert!(omitted.is_empty(), "unexpected trimming for {name}");
    }
}

#[test]
fn cache_rows_match_the_recorded_contract() {
    assert_eq!(cache_ndjson(&runs()), fixture("cache-rows.ndjson"));
}

#[test]
fn daily_costs_match_the_recorded_contract() {
    // These are the points the retired `plot-input-{design,implement}.json`
    // fixtures carried for both skills; the chart is rendered in process now,
    // so the recorded numbers live with the aggregation they came from.
    assert_eq!(
        daily_costs(&runs()),
        vec![
            ("2026-05-01".to_owned(), 1.86),
            ("2026-05-02".to_owned(), 0.32),
        ]
    );
}

#[test]
fn daily_costs_of_no_runs_are_empty() {
    assert!(daily_costs(&[]).is_empty());
}

#[test]
fn titles_match_the_recorded_contract() {
    let expected = fixture("titles.txt");
    let rendered = format!(
        "{}\n{}\n{}\n",
        title_for_skill("design", "2026-05-03 07:15 UTC"),
        title_for_skill("implement", "2026-05-03 07:15 UTC"),
        title_for_skill("debate", "2026-05-03 07:15 UTC")
    );
    assert_eq!(rendered, expected);
}

#[test]
fn oversized_bodies_drop_the_lowest_priority_sections_first() {
    let runs = runs();
    let (_body, sections) = render("implement", &runs, None, false);
    let (body, omitted) = assemble_issue_body(&sections, 400, "implement").expect("assemble");
    assert!(
        omitted.starts_with(&["Rates used for display/fallback".to_owned()]),
        "unexpected omission order: {omitted:?}"
    );
    assert!(body.contains("Report body trimmed"));
    assert!(
        omitted.contains(&"Report Tokens Analysis".to_owned()),
        "the summary is droppable when nothing else fits: {omitted:?}"
    );
}

#[test]
fn empty_runs_render_every_section_without_a_panic() {
    let (body, sections) = render("design", &[], None, false);
    assert!(body.starts_with("## Report Tokens Analysis"));
    assert!(body.contains("Analyzed 0 parseable runs."));
    assert!(body.ends_with("Cache JSON: <CACHE>"));
    assert_eq!(sections.len(), 8);
    assert_eq!(sections[5].priority, SectionPriority::Trends);
    assert_eq!(cache_ndjson(&[]), "");
}
