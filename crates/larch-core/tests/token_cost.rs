//! Differential parity tests for the token cost model and pricing tables.
//!
//! Both fixtures are recorded output of the Python owner
//! (`larch.report.report_tokens_cost.token_cost_from_args`,
//! `render_cost_line_from_args`, `token_cost_argv`, and `price_run`) over
//! exactly the inputs stored beside them. Regenerate them together from Python
//! whenever a rate or an output shape changes, and review a changed byte as a
//! pricing contract change rather than a Rust detail.

use larch_core::{
    CLAUDE_OPUS_4_8_MODEL, RATE_TABLE, TOKEN_VENDORS, TokenCostError, TokenCounts,
    TokenObservationKind, TokenObservations, TokenRunRecord, TokenVendor, aggregate_vendor_tokens,
    cursor_buckets_are_detailed, display_rates, exact_rate_row, price_counts, price_run,
    python_round, rate_row, render_cost_kv, render_cost_line, vendor_totals_from_report,
};
use serde_json::{Map, Value, json};
use std::collections::BTreeMap;

const ARGV_CASES: &str = include_str!("fixtures/token_cost/argv-cases.json");
const RECORD_CASES: &str = include_str!("fixtures/token_cost/record-cases.json");
const FLAGS: &str = include_str!("fixtures/token_cost/flags.json");

fn cases(body: &str) -> Vec<Value> {
    serde_json::from_str(body).expect("recorded Python cases parse")
}

fn text(case: &Value, key: &str) -> String {
    case[key]
        .as_str()
        .unwrap_or_else(|| panic!("case field {key} is a string"))
        .to_owned()
}

fn argv_of(case: &Value) -> Vec<String> {
    case["argv"]
        .as_array()
        .expect("argv is an array")
        .iter()
        .map(|item| item.as_str().expect("argv item is a string").to_owned())
        .collect()
}

fn env_of(case: &Value) -> BTreeMap<String, String> {
    case["env"]
        .as_object()
        .expect("env is an object")
        .iter()
        .map(|(name, value)| {
            (
                name.clone(),
                value.as_str().expect("env value is a string").to_owned(),
            )
        })
        .collect()
}

fn report_of(case: &Value) -> Map<String, Value> {
    case["report"]
        .as_object()
        .expect("report is an object")
        .clone()
}

fn record_from_report(report: Map<String, Value>, main_model: &str) -> TokenRunRecord {
    TokenRunRecord {
        number: 8087,
        title: "fixture".to_owned(),
        url: String::new(),
        started_at: "2026-07-01T00:00:00Z".to_owned(),
        closed_at: "2026-07-01T01:00:00Z".to_owned(),
        claude: vendor_totals_from_report(&report, TokenVendor::Claude),
        codex: vendor_totals_from_report(&report, TokenVendor::Codex),
        cursor: vendor_totals_from_report(&report, TokenVendor::Cursor),
        claude_sub: vendor_totals_from_report(&report, TokenVendor::ClaudeSub),
        phase_rows: Vec::new(),
        raw_report: report,
        main_model: main_model.to_owned(),
    }
}

fn observations() -> TokenObservations {
    TokenObservations::default()
}

#[test]
fn every_recorded_flag_case_prices_exactly_like_the_python_owner() {
    for case in cases(ARGV_CASES) {
        let name = text(&case, "name");
        let argv = argv_of(&case);
        let env = env_of(&case);
        let (counts, claude_model) =
            TokenCounts::from_cost_argv(&argv).unwrap_or_else(|error| panic!("{name}: {error}"));
        let rates = display_rates(&env, &claude_model, &mut observations());
        let values = price_counts(&counts, &rates);
        assert_eq!(render_cost_kv(&values), text(&case, "kv"), "kv for {name}");
        assert_eq!(
            render_cost_line(&values),
            text(&case, "line"),
            "cost line for {name}"
        );
        let quiet = if counts.is_zero() {
            String::new()
        } else {
            render_cost_line(&values)
        };
        assert_eq!(quiet, text(&case, "quiet_line"), "quiet line for {name}");
    }
}

#[test]
fn every_recorded_run_report_prices_exactly_like_the_python_owner() {
    for case in cases(RECORD_CASES) {
        let name = text(&case, "name");
        let main_model = text(&case, "main_model");
        let record = record_from_report(report_of(&case), &main_model);
        let argv = argv_of(&case);
        let from_record = TokenCounts::from_run_record(&record, &mut observations());
        let from_argv = TokenCounts::from_cost_argv(&argv);
        if let Some(kv) = case["kv"].as_str() {
            let counts = from_record
                .clone()
                .unwrap_or_else(|error| panic!("{name}: {error}"));
            let (argv_counts, argv_model) = from_argv
                .clone()
                .unwrap_or_else(|error| panic!("{name}: {error}"));
            assert_eq!(counts, argv_counts, "record counts match argv for {name}");
            assert_eq!(argv_model, main_model, "recorded model for {name}");
            let rates = display_rates(&BTreeMap::new(), &main_model, &mut observations());
            assert_eq!(
                render_cost_kv(&price_counts(&counts, &rates)),
                kv,
                "kv for {name}"
            );
        } else {
            assert!(
                matches!(from_record, Err(TokenCostError::NegativeCount(_lane))),
                "{name} refuses a negative bucket"
            );
            assert!(
                matches!(from_argv, Err(TokenCostError::InvalidCount(_raw))),
                "{name} refuses a negative count argument"
            );
        }
        let cost = price_run(&record, &BTreeMap::new(), &mut observations());
        let expected = &case["cost"];
        assert_eq!(
            json!({
                "claude_cost": cost.claude_cost,
                "codex_cost": cost.codex_cost,
                "cursor_cost": cost.cursor_cost,
                "cursor_composer_cost": cost.cursor_composer_cost,
                "cursor_grok_cost": cost.cursor_grok_cost,
                "claude_sub_cost": cost.claude_sub_cost,
                "total_cost": cost.total_cost,
                "priced_by_token_cost": cost.priced_by_token_cost,
            }),
            *expected,
            "run cost for {name}"
        );
    }
}

#[test]
fn an_unpriced_main_model_is_reported_and_still_costs_more_than_zero() {
    let mut sink = observations();
    let rates = display_rates(&BTreeMap::new(), "made-up-model-9", &mut sink);
    let opus = exact_rate_row(TokenVendor::Claude, CLAUDE_OPUS_4_8_MODEL).expect("opus row");
    assert!((rates.claude_input - opus.input).abs() < f64::EPSILON);
    assert!(rates.claude_input > 0.0);
    let reported: Vec<_> = sink
        .entries()
        .iter()
        .filter(|entry| entry.kind() == TokenObservationKind::UnpricedModel)
        .map(|entry| (entry.vendor().to_owned(), entry.detail().to_owned()))
        .collect();
    assert_eq!(
        reported,
        vec![("claude".to_owned(), "made-up-model-9".to_owned())]
    );
}

#[test]
fn an_unpriced_per_model_bucket_is_reported_for_every_lane() {
    let report = json!({
        "BUCKETS_codex": {"input": 10, "cached_input": 20, "output": 5},
        "BUCKETS_codex_by_model": {"gpt-9-unknown": {"input": 10, "cached_input": 20, "output": 5}},
        "BUCKETS_cursor": {"input": 10, "cache_read": 20, "output": 5},
        "BUCKETS_cursor_by_model": {"cursor-unknown": {"input": 10, "cache_read": 20, "output": 5}},
        "BUCKETS_claude_sub": {"input": 10, "cache_read": 20, "output": 5},
        "BUCKETS_claude_sub_by_model": {"glm-5.2": {"input": 10, "cache_read": 20, "output": 5}},
    });
    let record = record_from_report(
        report.as_object().expect("report object").clone(),
        CLAUDE_OPUS_4_8_MODEL,
    );
    let mut sink = observations();
    let counts = TokenCounts::from_run_record(&record, &mut sink).expect("counts");
    let mut reported: Vec<_> = sink
        .entries()
        .iter()
        .filter(|entry| entry.kind() == TokenObservationKind::UnpricedModel)
        .map(|entry| (entry.vendor().to_owned(), entry.detail().to_owned()))
        .collect();
    reported.sort();
    assert_eq!(
        reported,
        vec![
            ("claude_sub".to_owned(), "glm-5.2".to_owned()),
            ("codex".to_owned(), "gpt-9-unknown".to_owned()),
            ("cursor".to_owned(), "cursor-unknown".to_owned()),
        ]
    );
    // The substituted rows still price the tokens, so nothing is lost.
    assert_eq!(counts.codex.total(), 35);
    assert_eq!(counts.cursor.total(), 35);
    assert_eq!(counts.claude_sub.total(), 35);
}

#[test]
fn legacy_cursor_grok_ledger_ids_keep_the_current_grok_rate() {
    let report = json!({
        "BUCKETS_cursor": {"input": 1_000_000, "cache_read": 1_000_000, "output": 1_000_000},
        "BUCKETS_cursor_by_model": {
            "cursor-grok-4.5-high": {"input": 1_000_000, "cache_read": 0, "output": 0},
            "grok-4.5": {"input": 0, "cache_read": 1_000_000, "output": 1_000_000},
        },
    });
    let record = record_from_report(
        report.as_object().expect("report object").clone(),
        CLAUDE_OPUS_4_8_MODEL,
    );
    let mut sink = observations();
    let cost = price_run(&record, &BTreeMap::new(), &mut sink);

    assert_eq!(cost.cursor_grok_cost, Some(8.5));
    assert!((cost.cursor_cost - 8.5).abs() < f64::EPSILON);
    let reported: Vec<_> = sink
        .entries()
        .iter()
        .filter(|entry| entry.kind() == TokenObservationKind::UnpricedModel)
        .map(|entry| (entry.vendor().to_owned(), entry.detail().to_owned()))
        .collect();
    assert_eq!(
        reported,
        vec![
            ("cursor".to_owned(), "cursor-grok-4.5-high".to_owned()),
            ("cursor".to_owned(), "grok-4.5".to_owned()),
        ]
    );
}

#[test]
fn a_priced_model_is_never_reported_as_unpriced() {
    let mut sink = observations();
    for (vendor, model, _row) in &RATE_TABLE {
        let _row = rate_row(*vendor, model, &mut sink);
    }
    assert!(sink.entries().is_empty(), "{:?}", sink.entries());
}

#[test]
fn the_rate_table_has_one_row_per_vendor_and_model() {
    let mut seen: Vec<(TokenVendor, &str)> = Vec::new();
    for (vendor, model, row) in &RATE_TABLE {
        assert!(
            !seen.contains(&(*vendor, model)),
            "duplicate rate row for {model}"
        );
        seen.push((*vendor, model));
        assert!(row.input >= 0.0 && row.cache_read >= 0.0 && row.output >= 0.0);
    }
    for vendor in TOKEN_VENDORS {
        let mut sink = observations();
        let fallback = rate_row(vendor, "", &mut sink);
        assert!(fallback.input > 0.0, "{vendor:?} has a positive default");
        assert!(sink.entries().is_empty(), "an empty model reports nothing");
    }
}

#[test]
fn rounding_matches_python_ties_to_even() {
    assert!((python_round(0.125, 2) - 0.12).abs() < f64::EPSILON);
    assert!((python_round(0.135, 2) - 0.14).abs() < f64::EPSILON);
    assert!((python_round(2.675, 2) - 2.67).abs() < f64::EPSILON);
    assert!((python_round(1.0e18, 2) - 1.0e18).abs() < f64::EPSILON);
}

#[test]
fn a_cursor_split_is_detailed_only_when_every_bucket_is_an_exact_integer() {
    let exact = json!({"composer-2.5": {"input": 1, "cache_read": 2, "output": 3}});
    assert!(cursor_buckets_are_detailed(Some(&exact)));
    let strings = json!({"composer-2.5": {"input": "1", "cache_read": " 2 ", "output": 3}});
    assert!(cursor_buckets_are_detailed(Some(&strings)));
    let missing = json!({"composer-2.5": {"input": 1}});
    assert!(cursor_buckets_are_detailed(Some(&missing)));
    for rejected in [
        json!({"composer-2.5": {"input": 1.0, "cache_read": 2, "output": 3}}),
        json!({"composer-2.5": {"input": true, "cache_read": 2, "output": 3}}),
        json!({"composer-2.5": {"input": null, "cache_read": 2, "output": 3}}),
        json!({"composer-2.5": {"input": "-1", "cache_read": 2, "output": 3}}),
        json!({"composer-2.5": {"input": "1,0", "cache_read": 2, "output": 3}}),
        json!({"composer-2.5": 5}),
        json!({}),
    ] {
        assert!(
            !cursor_buckets_are_detailed(Some(&rejected)),
            "{rejected} is not detailed"
        );
    }
    assert!(!cursor_buckets_are_detailed(None));
}

#[test]
fn the_flag_grammar_accepts_exactly_the_python_flag_set() {
    let recorded: Vec<String> = serde_json::from_str(FLAGS).expect("recorded Python flags parse");
    assert_eq!(
        recorded.len(),
        41,
        "the Python owner defines 41 count flags"
    );
    for flag in &recorded {
        let argv = [flag.clone(), "7".to_owned()];
        let (counts, _model) = TokenCounts::from_cost_argv(&argv)
            .unwrap_or_else(|error| panic!("{flag} is accepted: {error}"));
        assert!(!counts.is_zero(), "{flag} assigns a count");
    }
    // Every plausible lane and field pairing that Python does not define stays
    // refused, so the derived grammar cannot silently widen the flag set.
    for lane in [
        "claude",
        "claude-sub",
        "claude-sub-sonnet",
        "claude-sub-haiku",
        "claude-sub-fable",
        "codex",
        "codex-mini",
        "cursor",
        "cursor-grok",
    ] {
        for field in [
            "input",
            "cache-read",
            "cached-input",
            "cache-write-5m",
            "cache-write-1h",
            "output",
            "",
        ] {
            let flag = if field.is_empty() {
                format!("--{lane}-tokens")
            } else {
                format!("--{lane}-{field}-tokens")
            };
            let accepted = TokenCounts::from_cost_argv(&[flag.clone(), "7".to_owned()]).is_ok();
            assert_eq!(
                accepted,
                recorded.contains(&flag),
                "{flag} acceptance matches the Python owner"
            );
        }
    }
}

#[test]
fn an_unknown_pricing_flag_is_refused_instead_of_ignored() {
    for argv in [
        vec!["--made-up-tokens".to_owned(), "5".to_owned()],
        vec!["--claude-sub-sonnet-tokens".to_owned(), "5".to_owned()],
        vec!["--claude-cache-write-9h-tokens".to_owned(), "5".to_owned()],
        vec!["--claude-input-tokens".to_owned()],
        vec!["--claude-model".to_owned()],
    ] {
        assert!(
            matches!(
                TokenCounts::from_cost_argv(&argv),
                Err(TokenCostError::UnknownFlag(_flag))
            ),
            "{argv:?} is refused"
        );
    }
    assert!(matches!(
        TokenCounts::from_cost_argv(&["--claude-input-tokens".to_owned(), "-5".to_owned()]),
        Err(TokenCostError::InvalidCount(_raw))
    ));
}

#[test]
fn a_repeated_flag_replaces_the_earlier_value() {
    let argv = [
        "--claude-input-tokens".to_owned(),
        "10".to_owned(),
        "--claude-input-tokens".to_owned(),
        "25".to_owned(),
    ];
    let (counts, _model) = TokenCounts::from_cost_argv(&argv).expect("counts");
    assert_eq!(counts.claude.input, 25);
}

#[test]
fn a_zero_cursor_bucket_flag_still_marks_the_split_as_detailed() {
    let argv = ["--cursor-input-tokens".to_owned(), "0".to_owned()];
    let (counts, _model) = TokenCounts::from_cost_argv(&argv).expect("counts");
    assert!(counts.cursor_detail_present);
    assert!(counts.is_zero());
}

#[test]
fn a_lane_total_prefers_components_over_the_recorded_total() {
    let report = json!({
        "claude": {"totals": {"input": 5, "cache_read": 7, "output": 3, "total": 999}},
        "codex": {"totals": {"input": 0, "cached_input": 0, "output": 0, "total": 42}},
    });
    let record = record_from_report(report.as_object().expect("object").clone(), "");
    assert_eq!(aggregate_vendor_tokens(&record, TokenVendor::Claude), 15);
    assert_eq!(aggregate_vendor_tokens(&record, TokenVendor::Codex), 42);
}
