//! Table-driven parity for the drafter response grammar.
//!
//! `tests/fixtures/drafter/recorded-outputs.json` records raw drafter responses
//! together with the verdict the retired Python parser produced for each. Every
//! case is replayed through the Rust owner so a grammar change that would move
//! a recorded response to a different verdict fails here.

use std::{collections::BTreeMap, fs, path::PathBuf};

use larch_core::{
    DrafterDialectic, DrafterScout, parse_drafter_output, plan_contains_standalone_scout_manifest,
    terminal_diff_lines,
};
use serde::Deserialize;

#[derive(Deserialize)]
struct Case {
    raw: String,
    verdict: Verdict,
}

#[derive(Deserialize)]
struct Verdict {
    /// Present only for a response the parser rejects outright.
    #[serde(default)]
    error: Option<String>,
    #[serde(default)]
    plan: Option<String>,
    #[serde(default)]
    plan_lines: Option<usize>,
    #[serde(default)]
    diff_lines: Option<u64>,
    #[serde(default)]
    summary: Option<String>,
    #[serde(default)]
    scout: Option<String>,
    #[serde(default)]
    scout_fail_reason: Option<String>,
    #[serde(default)]
    dialectic_raw: Option<String>,
    #[serde(default)]
    dialectic_fail_reason: Option<String>,
}

fn corpus() -> BTreeMap<String, Case> {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/drafter/recorded-outputs.json");
    let text = fs::read_to_string(&path).expect("recorded drafter corpus is readable");
    serde_json::from_str(&text).expect("recorded drafter corpus is well formed")
}

#[test]
fn every_recorded_response_reproduces_its_python_verdict() {
    let corpus = corpus();
    assert!(corpus.len() >= 40, "corpus lost cases: {}", corpus.len());
    for (name, case) in &corpus {
        let parsed = match parse_drafter_output(&case.raw) {
            Ok(parsed) => {
                assert!(
                    case.verdict.error.is_none(),
                    "{name}: expected rejection {:?}, got a parse",
                    case.verdict.error
                );
                parsed
            }
            Err(error) => {
                assert_eq!(
                    Some(error.message()),
                    case.verdict.error.as_deref(),
                    "{name}: rejection text drifted"
                );
                continue;
            }
        };
        assert_eq!(
            Some(parsed.plan_body.as_str()),
            case.verdict.plan.as_deref(),
            "{name}: plan body"
        );
        assert_eq!(
            Some(parsed.plan_lines),
            case.verdict.plan_lines,
            "{name}: plan line count"
        );
        assert_eq!(
            Some(parsed.diff_lines),
            case.verdict.diff_lines,
            "{name}: diff_lines trailer"
        );
        assert_eq!(
            parsed.summary.as_deref(),
            case.verdict.summary.as_deref(),
            "{name}: summary body"
        );
        assert_scout(name, &parsed.scout, &case.verdict);
        assert_dialectic(name, &parsed.dialectic, &case.verdict);
    }
}

fn assert_scout(name: &str, scout: &DrafterScout, verdict: &Verdict) {
    let manifest = match scout {
        DrafterScout::Manifest(manifest) => Some(manifest.as_str()),
        DrafterScout::Absent | DrafterScout::Invalid(..) => None,
    };
    assert_eq!(
        manifest,
        verdict.scout.as_deref(),
        "{name}: scout manifest body"
    );
    assert_eq!(
        scout.fail_reason(),
        verdict.scout_fail_reason.as_deref().unwrap_or_default(),
        "{name}: scout fail reason"
    );
}

fn assert_dialectic(name: &str, dialectic: &DrafterDialectic, verdict: &Verdict) {
    // The Rust core stops at the sentinel boundary and hands the raw block to
    // the design-domain candidate validator, so `invalid_dialectic_json` is a
    // validator verdict rather than a parser verdict. Everything up to that
    // hand-off must match byte for byte.
    match dialectic {
        DrafterDialectic::Candidate(text) => {
            assert_eq!(
                Some(text.as_str()),
                verdict.dialectic_raw.as_deref(),
                "{name}: dialectic hand-off text"
            );
        }
        DrafterDialectic::Absent => {
            assert_eq!(verdict.dialectic_raw, None, "{name}: unexpected hand-off");
            assert_eq!(
                verdict.dialectic_fail_reason.as_deref(),
                Some(""),
                "{name}: absent dialectic carries no reason"
            );
        }
        DrafterDialectic::Invalid(reason) => {
            assert_eq!(verdict.dialectic_raw, None, "{name}: unexpected hand-off");
            assert_eq!(
                verdict.dialectic_fail_reason.as_deref(),
                Some(*reason),
                "{name}: dialectic sentinel reason"
            );
        }
    }
}

#[test]
fn recorded_plans_agree_on_trailers_and_embedded_manifests() {
    for (name, case) in &corpus() {
        let Ok(parsed) = parse_drafter_output(&case.raw) else {
            continue;
        };
        assert_eq!(
            terminal_diff_lines(&parsed.plan_body),
            Some(parsed.diff_lines),
            "{name}: trailer re-read"
        );
        assert!(
            !plan_contains_standalone_scout_manifest(&parsed.plan_body),
            "{name}: an accepted plan must never embed a scout manifest"
        );
    }
}
