//! Rust owner for the two `/design` rendering verbs `render-gate` and
//! `render-final-summary` (#8581).
//!
//! Atomically replaces the Python registrations for `design render-gate`
//! (`larch.design.design_gate_render`) and `design render-final-summary`
//! (`larch.design.design_summary`). The frozen Python references live under
//! `fixtures/rust-parity/` and drive the byte-parity harness in
//! `crates/larch-cli/tests/design_gate_summary_migrated_parity.rs`.
//!
//! `render-gate` is a pure KEY=value renderer that reproduces the Python
//! `argparse` grammar (prog `cli.py`) byte-for-byte, including its usage and
//! error strings. `render-final-summary` is orchestration only: it reuses the
//! already-Rust report/difficulty/review-provenance owners, shells out to the
//! still-Python `render run-summary` with an unchanged argument vector so the
//! rendered body stays byte-identical, then applies the enrichment and prefix
//! passes.

use std::{
    collections::BTreeMap,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use serde_json::{Map, Value};

use larch_core::{
    DESIGN_ASSESSMENT, ReviewProvenance, guideline_active_exception, redact_outbound,
    report::{
        CODEX_MINI_MODELS, CURSOR_GROK_MODELS, LoadResult, build_issue_detail_section,
        count_load_result, load_issue_detail_groups, map_outcome_display,
    },
    review_provenance,
};

use crate::design_step0_commands::utf8_arguments;
use crate::python_verb::run_python_verb;
use crate::runtime_entrypoint::run_verified_larch;

const PYTHON_BRIDGE_TIMEOUT: Duration = Duration::from_secs(120);

// ---------------------------------------------------------------------------
// render-gate: constants copied verbatim from design_gate_render.py
// ---------------------------------------------------------------------------

const GATE_RENDER_USAGE: &str = "usage: cli.py [-h] --gate {A,B,C} [--without-see-full-plan] [--accepted-count ACCEPTED_COUNT] [--approve-requested {false,true}] [--design-tmpdir DESIGN_TMPDIR] [--panel-failed {false,true}] [--accepted-audit-escalation {false,true}]";
const GATE_RENDER_PROG: &str = "cli.py";

const ROUND_CAP: i64 = 2;
const GATE_C_OTHER_AFFORDANCE: &str = "Use Other to request debate <decision>: <option A> vs <option B> (or debate <candidate-id> when fingerprint-valid candidates exist).";
const GATE_C_APPROVE_LABEL: &str = "Approve final design";
const GATE_C_PANEL_FAILED_APPROVE_LABEL: &str = "Approve final design (acknowledge panel failure)";

// ---------------------------------------------------------------------------
// render-gate: GateRender row model (port of GateRender.rows)
// ---------------------------------------------------------------------------

struct GateRender {
    gate: &'static str,
    header: &'static str,
    question: String,
    options: Vec<(String, String)>,
    extra: Vec<(String, String)>,
}

impl GateRender {
    fn rows(&self) -> Vec<(String, String)> {
        let mut rows: Vec<(String, String)> = vec![
            ("GATE_RENDER_STATUS".to_owned(), "ok".to_owned()),
            ("GATE".to_owned(), self.gate.to_owned()),
        ];
        if !self.header.is_empty() {
            rows.push(("HEADER".to_owned(), self.header.to_owned()));
        }
        if !self.question.is_empty() {
            rows.push(("QUESTION".to_owned(), self.question.clone()));
        }
        rows.push(("OPTION_COUNT".to_owned(), self.options.len().to_string()));
        for (index, (label, description)) in self.options.iter().enumerate() {
            let position = index + 1;
            rows.push((format!("OPTION_{position}_LABEL"), label.clone()));
            rows.push((format!("OPTION_{position}_DESCRIPTION"), description.clone()));
        }
        rows.extend(self.extra.iter().cloned());
        rows
    }
}

// ---------------------------------------------------------------------------
// render-gate: argument parsing (port of _arg_parser + render_gate_main)
// ---------------------------------------------------------------------------

/// Emit the argparse-style usage + error diagnostic to stderr and exit 2.
fn gate_arg_error(message: &str) -> ExitCode {
    eprintln!("{GATE_RENDER_USAGE}");
    eprintln!("{GATE_RENDER_PROG}: error: {message}");
    ExitCode::from(2)
}

/// Argparse `-h`/`--help` body (below the usage line). Reproduces the frozen
/// Python parser's auto-help so `design render-gate --help` stays byte-parity.
const GATE_RENDER_HELP_BODY: &str = concat!(
    "Render /design Gate A/B/C prompt copy as KEY=value rows\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --gate {A,B,C}\n",
    "  --without-see-full-plan\n",
    "  --accepted-count ACCEPTED_COUNT\n",
    "  --approve-requested {false,true}\n",
    "  --design-tmpdir DESIGN_TMPDIR\n",
    "  --panel-failed {false,true}\n",
    "  --accepted-audit-escalation {false,true}\n",
);

/// Emit argparse's `-h`/`--help` output to stdout and exit 0.
fn gate_help() -> ExitCode {
    println!("{GATE_RENDER_USAGE}");
    println!();
    print!("{GATE_RENDER_HELP_BODY}");
    ExitCode::SUCCESS
}

#[allow(clippy::struct_excessive_bools)] // Mirrors the render-gate CLI flag set.
struct GateArgs {
    gate: String,
    without_see_full_plan: bool,
    accepted_count: i64,
    approve_requested: bool,
    design_tmpdir: Option<String>,
    panel_failed: bool,
    accepted_audit_escalation: bool,
}

/// Parse the raw argv into `GateArgs`, or an argparse-faithful error exit.
///
/// Mirrors Python `argparse` for the tested surface: `--flag value` and
/// `--flag=value`, required `--gate`, `{A,B,C}` / `{false,true}` choices,
/// integer coercion for `--accepted-count`, unrecognized-argument and
/// missing-value diagnostics. Later occurrences win, matching argparse.
#[allow(clippy::too_many_lines)] // Faithful mirror of the argparse parser surface.
fn parse_gate_args(argv: &[String]) -> Result<GateArgs, ExitCode> {
    let mut gate: Option<String> = None;
    let mut without_see_full_plan = false;
    let mut accepted_count: i64 = 0;
    let mut approve_requested = String::from("false");
    let mut design_tmpdir: Option<String> = None;
    let mut panel_failed = String::from("false");
    let mut accepted_audit_escalation = String::from("false");
    let mut extras: Vec<String> = Vec::new();

    let take_value = |name: &str, inline: Option<String>, index: &mut usize| -> Result<String, ExitCode> {
        if let Some(value) = inline {
            return Ok(value);
        }
        *index += 1;
        if *index < argv.len() {
            Ok(argv[*index].clone())
        } else {
            Err(gate_arg_error(&format!("argument {name}: expected one argument")))
        }
    };

    let choice_check = |name: &str, value: &str, choices: &[&str]| -> Result<(), ExitCode> {
        if choices.contains(&value) {
            Ok(())
        } else {
            let rendered: Vec<String> = choices.iter().map(|choice| format!("'{choice}'")).collect();
            Err(gate_arg_error(&format!(
                "argument {name}: invalid choice: '{value}' (choose from {})",
                rendered.join(", ")
            )))
        }
    };

    let mut i = 0;
    while i < argv.len() {
        let token = argv[i].clone();
        let (name, inline) = match token.split_once('=') {
            Some((n, v)) => (n.to_owned(), Some(v.to_owned())),
            None => (token.clone(), None),
        };
        match name.as_str() {
            "--gate" => {
                let value = take_value("--gate", inline, &mut i)?;
                choice_check("--gate", &value, &["A", "B", "C"])?;
                gate = Some(value);
            }
            "--without-see-full-plan" => {
                without_see_full_plan = true;
            }
            "--accepted-count" => {
                let value = take_value("--accepted-count", inline, &mut i)?;
                accepted_count = match parse_py_int(&value) {
                    Some(parsed) => parsed,
                    None => {
                        return Err(gate_arg_error(&format!(
                            "argument --accepted-count: invalid int value: '{value}'"
                        )));
                    }
                };
            }
            "--approve-requested" => {
                let value = take_value("--approve-requested", inline, &mut i)?;
                choice_check("--approve-requested", &value, &["false", "true"])?;
                approve_requested = value;
            }
            "--design-tmpdir" => {
                design_tmpdir = Some(take_value("--design-tmpdir", inline, &mut i)?);
            }
            "--panel-failed" => {
                let value = take_value("--panel-failed", inline, &mut i)?;
                choice_check("--panel-failed", &value, &["false", "true"])?;
                panel_failed = value;
            }
            "--accepted-audit-escalation" => {
                let value = take_value("--accepted-audit-escalation", inline, &mut i)?;
                choice_check("--accepted-audit-escalation", &value, &["false", "true"])?;
                accepted_audit_escalation = value;
            }
            "-h" | "--help" => {
                return Err(gate_help());
            }
            _ => {
                extras.push(token);
            }
        }
        i += 1;
    }

    let Some(gate) = gate else {
        return Err(gate_arg_error("the following arguments are required: --gate"));
    };
    if !extras.is_empty() {
        return Err(gate_arg_error(&format!(
            "unrecognized arguments: {}",
            extras.join(" ")
        )));
    }

    Ok(GateArgs {
        gate,
        without_see_full_plan,
        accepted_count,
        approve_requested: approve_requested == "true",
        design_tmpdir,
        panel_failed: panel_failed == "true",
        accepted_audit_escalation: accepted_audit_escalation == "true",
    })
}

/// Port of Python `int(value)` for the argparse coercion: trims ASCII
/// whitespace, accepts an optional sign, then all-ASCII digits (with the
/// underscore digit grouping Python allows).
fn parse_py_int(value: &str) -> Option<i64> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return None;
    }
    let (sign, digits) = trimmed.strip_prefix('-').map_or_else(
        || (1i64, trimmed.strip_prefix('+').unwrap_or(trimmed)),
        |rest| (-1i64, rest),
    );
    if digits.is_empty() {
        return None;
    }
    // Python allows single underscores between digits; reject leading/trailing
    // or doubled underscores.
    let mut normalized = String::with_capacity(digits.len());
    let bytes = digits.as_bytes();
    for (offset, character) in digits.char_indices() {
        if character == '_' {
            let prev_ok = offset > 0 && bytes[offset - 1].is_ascii_digit();
            let next_ok = offset + 1 < bytes.len() && bytes[offset + 1].is_ascii_digit();
            if !prev_ok || !next_ok {
                return None;
            }
            continue;
        }
        if !character.is_ascii_digit() {
            return None;
        }
        normalized.push(character);
    }
    normalized.parse::<i64>().ok().map(|magnitude| sign * magnitude)
}

// ---------------------------------------------------------------------------
// render-gate: gate builders (port of _render_gate_a/b/c)
// ---------------------------------------------------------------------------

fn gate_a_options(without_see_full_plan: bool) -> Vec<(String, String)> {
    let core = vec![
        (
            "Ready for review".to_owned(),
            "Launch the design review against the current plan.".to_owned(),
        ),
        (
            "Discuss more".to_owned(),
            "Continue the post-plan discussion before review.".to_owned(),
        ),
    ];
    if without_see_full_plan {
        return core;
    }
    let mut options = vec![(
        "See full plan".to_owned(),
        "Re-display the current plan, then return to this prompt without advancing.".to_owned(),
    )];
    options.extend(core);
    options
}

fn render_gate_a(without_see_full_plan: bool) -> GateRender {
    GateRender {
        gate: "A",
        header: "Design discussion",
        question: "All open design questions appear discussed. Ready to launch the design review, or would you like to discuss more first?".to_owned(),
        options: gate_a_options(without_see_full_plan),
        extra: Vec::new(),
    }
}

/// Port of `_render_gate_b`; returns the `ValueError` message on a negative
/// `--accepted-count` (argparse then routes it through `parser.error`).
fn render_gate_b(accepted_count: i64, approve_requested: bool) -> Result<GateRender, String> {
    if accepted_count < 0 {
        return Err("--accepted-count must be non-negative".to_owned());
    }
    if approve_requested {
        return Ok(GateRender {
            gate: "B",
            header: "",
            question: String::new(),
            options: Vec::new(),
            extra: vec![
                ("PROMPT_REQUIRED".to_owned(), "true".to_owned()),
                (
                    "EXPLICIT_COPY_OWNER".to_owned(),
                    "skills/design/references/approval-gates-explicit.md".to_owned(),
                ),
            ],
        });
    }
    Ok(GateRender {
        gate: "B",
        header: "",
        question: String::new(),
        options: Vec::new(),
        extra: vec![
            ("PROMPT_REQUIRED".to_owned(), "false".to_owned()),
            (
                "AUTO_APPLY_MESSAGE".to_owned(),
                format!("\u{2139} 3.5: Gate B — auto-applying {accepted_count} accepted finding(s)"),
            ),
        ],
    })
}

/// Port of `_review_count`: `(count, warning)` from review-round-count.txt.
fn review_count(design_tmpdir: Option<&str>) -> (i64, &'static str) {
    let Some(tmpdir) = design_tmpdir else {
        return (0, "");
    };
    if tmpdir.is_empty() {
        return (0, "");
    }
    let path = Path::new(tmpdir).join("review-round-count.txt");
    let Ok(metadata) = std::fs::symlink_metadata(&path) else {
        return (0, "");
    };
    if !metadata.is_file() || metadata.file_type().is_symlink() {
        return (0, "");
    }
    let Ok(bytes) = std::fs::read(&path) else {
        return (0, "");
    };
    let raw = String::from_utf8_lossy(&bytes);
    let raw = raw.trim();
    if raw.is_empty() {
        return (0, "");
    }
    if !raw.bytes().all(|byte| byte.is_ascii_digit()) {
        return (0, "non-numeric");
    }
    (raw.parse::<i64>().unwrap_or(0), "")
}

const fn gate_c_approve_description(panel_failed: bool, accepted_audit_escalation: bool) -> &'static str {
    if accepted_audit_escalation && panel_failed {
        return "Approve despite the main-agent accepted-findings audit's strong dissent and acknowledge panel failure, then continue immediately to finalize.";
    }
    if accepted_audit_escalation {
        return "Approve despite the main-agent accepted-findings audit's strong dissent and continue immediately to finalize.";
    }
    "Approve the current plan and continue immediately to finalize."
}

#[allow(clippy::fn_params_excessive_bools)] // Mirrors the render-gate flag set.
fn gate_c_options(
    without_see_full_plan: bool,
    at_cap: bool,
    panel_failed: bool,
    accepted_audit_escalation: bool,
) -> Vec<(String, String)> {
    let approve_label = if panel_failed {
        GATE_C_PANEL_FAILED_APPROVE_LABEL
    } else {
        GATE_C_APPROVE_LABEL
    };
    let mut options = vec![(
        approve_label.to_owned(),
        gate_c_approve_description(panel_failed, accepted_audit_escalation).to_owned(),
    )];
    if !without_see_full_plan {
        options.push((
            "See full plan".to_owned(),
            "Show the full current plan, then return to this prompt without advancing.".to_owned(),
        ));
    }
    options.push((
        "Discuss further".to_owned(),
        "Return to Gate A discussion before another review pass.".to_owned(),
    ));
    if !at_cap {
        options.push((
            "Re-run review panel".to_owned(),
            "Launch another review panel against the current plan.".to_owned(),
        ));
    }
    options
}

fn gate_c_question(at_cap: bool) -> String {
    let base = if at_cap {
        "Final design plan is ready. Approve, see the full plan, or discuss further?"
    } else {
        "Final design plan is ready. Approve, see the full plan, discuss further, or re-run the review panel against this plan?"
    };
    format!("{base} {GATE_C_OTHER_AFFORDANCE}")
}

fn render_gate_c(
    design_tmpdir: Option<&str>,
    without_see_full_plan: bool,
    panel_failed: bool,
    accepted_audit_escalation: bool,
) -> GateRender {
    let (count, warning) = review_count(design_tmpdir);
    let at_cap = count >= ROUND_CAP;
    let mut extra: Vec<(String, String)> =
        vec![("REVIEW_ROUND_CAP".to_owned(), ROUND_CAP.to_string())];
    if !warning.is_empty() {
        extra.push(("REVIEW_ROUND_COUNT_WARN".to_owned(), warning.to_owned()));
    }
    GateRender {
        gate: "C",
        header: "Final design",
        question: gate_c_question(at_cap),
        options: gate_c_options(
            without_see_full_plan,
            at_cap,
            panel_failed,
            accepted_audit_escalation,
        ),
        extra,
    }
}

/// Port of `_validate_rows` + `_emit_rows`: refuse CR/LF, else print rows.
fn emit_gate_rows(rows: &[(String, String)]) -> Result<(), ExitCode> {
    for (key, value) in rows {
        if value.contains('\n') || value.contains('\r') {
            eprintln!("ERROR: rendered value for {key} contains CR/LF");
            return Err(ExitCode::from(2));
        }
    }
    let mut buffer = String::new();
    for (key, value) in rows {
        buffer.push_str(key);
        buffer.push('=');
        buffer.push_str(value);
        buffer.push('\n');
    }
    print!("{buffer}");
    Ok(())
}

/// Rust owner for `design render-gate` (#8581).
pub fn render_gate(arguments: &[OsString]) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let parsed = match parse_gate_args(&argv) {
        Ok(parsed) => parsed,
        Err(exit) => return exit,
    };
    let render = match parsed.gate.as_str() {
        "A" => render_gate_a(parsed.without_see_full_plan),
        "B" => match render_gate_b(parsed.accepted_count, parsed.approve_requested) {
            Ok(render) => render,
            Err(message) => return gate_arg_error(&message),
        },
        _ => render_gate_c(
            parsed.design_tmpdir.as_deref(),
            parsed.without_see_full_plan,
            parsed.panel_failed,
            parsed.accepted_audit_escalation,
        ),
    };
    match emit_gate_rows(&render.rows()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(exit) => exit,
    }
}

// ---------------------------------------------------------------------------
// render-final-summary: constants (port of design_summary.py module scope)
// ---------------------------------------------------------------------------

const VALID_OUTCOMES: [&str; 18] = [
    "approved",
    "approved-partition",
    "cancelled-clarify",
    "cancelled-already-planned",
    "cancelled-reentry-guard",
    "cancelled-title-filter",
    "cancelled-sprawl",
    "cancelled-plan-size",
    "cancelled-decompose",
    "cancelled-outline",
    "failed-plan-write",
    "failed-publish",
    "failed-postplan",
    "failed-clarify",
    "failed-judge-panel",
    "failed-publish-tail",
    "publish-skipped",
    "paused",
];
const APPROVED_OUTCOMES: [&str; 2] = ["approved", "approved-partition"];
const OOS_FILE_MAP_FIELD_COUNT: usize = 3;
const MISSING_INVARIANT_ASSESSMENT_SUMMARY_WARNING: &str =
    "**\u{26a0} Missing architectural-invariant-assessment.md; Gate C assessment did not persist.**";
const MISSING_GUIDELINE_ASSESSMENT_SUMMARY_WARNING: &str =
    "**\u{26a0} Missing architectural-guideline-assessment.md; Gate C assessment did not persist.**";
const GUIDELINE_EXCEPTION_DISCLOSURE_PREFIX: &str = "**Gate C guideline exception recorded:**";
/// Storage-resolution reasons a disabled-publication manifest may carry (mirror
/// of the sibling constant in `execution_issue_commands.rs`).
const DISABLED_STORAGE_REASONS: [&str; 3] = [
    "config-file-missing",
    "larch-table-missing",
    "storage-base-uri-omitted",
];

// ---------------------------------------------------------------------------
// render-final-summary: small filesystem/env helpers
// ---------------------------------------------------------------------------

/// Best-effort UTF-8 read that never fails (`errors="replace"` in Python).
fn read_lossy(path: &Path) -> Option<String> {
    fs::read(path).ok().map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
}

fn is_regular_file(path: &Path) -> bool {
    fs::symlink_metadata(path)
        .map(|metadata| metadata.is_file() && !metadata.file_type().is_symlink())
        .unwrap_or(false)
}

fn file_size(path: &Path) -> u64 {
    fs::metadata(path).map(|metadata| metadata.len()).unwrap_or(0)
}

/// Port of `_read_source_env_value`.
fn read_source_env_value(path: &Path, key: &str) -> String {
    if !is_regular_file(path) {
        return String::new();
    }
    let Some(text) = read_lossy(path) else {
        return String::new();
    };
    let export_prefix = format!("export {key}=");
    let prefix = format!("{key}=");
    for line in text.lines() {
        let value = if let Some(rest) = line.strip_prefix(&export_prefix) {
            rest
        } else if let Some(rest) = line.strip_prefix(&prefix) {
            rest
        } else {
            continue;
        };
        return value.trim().trim_matches('"').trim_matches('\'').to_owned();
    }
    String::new()
}

/// Coerce a JSON bucket count the way Python `int(value or 0)` does.
fn json_int(value: Option<&Value>) -> i64 {
    match value {
        Some(Value::Number(number)) => number.as_i64().or_else(|| {
            #[allow(clippy::cast_possible_truncation)] // Mirrors Python int() truncation.
            number.as_f64().map(|float| float as i64)
        }).unwrap_or(0),
        _ => 0,
    }
}

// ---------------------------------------------------------------------------
// render-final-summary: larch subprocess seams
// ---------------------------------------------------------------------------

/// Port of `_run_larch(*args)`: invoke one Rust-owned verb through the verified
/// bootstrap and capture streams + exit code.
fn run_larch_capture(args: &[OsString]) -> (i32, Vec<u8>, Vec<u8>) {
    match run_verified_larch(args) {
        Ok(output) => (
            output.status().code().unwrap_or(1),
            output.stdout().to_vec(),
            output.stderr().to_vec(),
        ),
        Err(_error) => (1, Vec::new(), Vec::new()),
    }
}

fn os_args(values: &[&str]) -> Vec<OsString> {
    values.iter().map(OsString::from).collect()
}

// ---------------------------------------------------------------------------
// render-final-summary: token report and cost args
// ---------------------------------------------------------------------------

/// Port of `_cursor_buckets_by_model`.
fn cursor_buckets_by_model(data: &Map<String, Value>) -> BTreeMap<String, i64> {
    let Some(Value::Object(cbm)) = data.get("BUCKETS_cursor_by_model") else {
        return BTreeMap::new();
    };
    let mut composer = (0i64, 0i64, 0i64);
    let mut grok = (0i64, 0i64, 0i64);
    for (model, raw) in cbm {
        let Value::Object(bucket) = raw else {
            continue;
        };
        let target = if CURSOR_GROK_MODELS.contains(&model.as_str()) {
            &mut grok
        } else {
            &mut composer
        };
        target.0 += json_int(bucket.get("input"));
        target.1 += json_int(bucket.get("cache_read"));
        target.2 += json_int(bucket.get("output"));
    }
    BTreeMap::from([
        ("U_IN".to_owned(), composer.0),
        ("U_CR".to_owned(), composer.1),
        ("U_OUT".to_owned(), composer.2),
        ("U_GROK_IN".to_owned(), grok.0),
        ("U_GROK_CR".to_owned(), grok.1),
        ("U_GROK_OUT".to_owned(), grok.2),
    ])
}

/// Port of `_read_token_report`.
fn read_token_report(design_tmpdir: &Path) -> BTreeMap<String, i64> {
    let tok_json = design_tmpdir.join("token-report-final.json");
    if !is_regular_file(&tok_json) {
        return BTreeMap::new();
    }
    let Some(text) = read_lossy(&tok_json) else {
        return BTreeMap::new();
    };
    let Ok(Value::Object(data)) = serde_json::from_str::<Value>(&text) else {
        return BTreeMap::new();
    };
    let mut buckets: BTreeMap<String, i64> = BTreeMap::new();
    for (vendor, prefix) in [("claude", "C"), ("codex", "D"), ("cursor", "U"), ("claude_sub", "CS")] {
        let bkey = format!("BUCKETS_{vendor}");
        if let Some(Value::Object(bucket)) = data.get(&bkey) {
            buckets.insert(format!("{prefix}_IN"), json_int(bucket.get("input")));
            buckets.insert(format!("{prefix}_CR"), json_int(bucket.get("cache_read")));
            if vendor == "claude" || vendor == "claude_sub" {
                buckets.insert(format!("{prefix}_CW5"), json_int(bucket.get("cache_create_5m")));
                buckets.insert(format!("{prefix}_CW1"), json_int(bucket.get("cache_create_1h")));
            }
            buckets.insert(format!("{prefix}_OUT"), json_int(bucket.get("output")));
        }
        if let Some(Value::Object(totals_owner)) = data.get(vendor)
            && let Some(Value::Object(totals)) = totals_owner.get("totals")
        {
            buckets.insert(format!("{}_T", vendor.to_uppercase()), json_int(totals.get("total")));
        }
    }
    if let Some(Value::Object(by_model)) = data.get("BUCKETS_codex_by_model") {
        let mut main = (0i64, 0i64, 0i64);
        let mut mini = (0i64, 0i64, 0i64);
        for (model, raw) in by_model {
            let Value::Object(bucket) = raw else {
                continue;
            };
            let target = if CODEX_MINI_MODELS.contains(&model.as_str()) {
                &mut mini
            } else {
                &mut main
            };
            target.0 += json_int(bucket.get("input"));
            target.1 += json_int(bucket.get("cached_input"));
            target.2 += json_int(bucket.get("output"));
        }
        buckets.insert("D_IN".to_owned(), main.0);
        buckets.insert("D_CR".to_owned(), main.1);
        buckets.insert("D_OUT".to_owned(), main.2);
        buckets.insert("D_MINI_IN".to_owned(), mini.0);
        buckets.insert("D_MINI_CR".to_owned(), mini.1);
        buckets.insert("D_MINI_OUT".to_owned(), mini.2);
    }
    buckets.extend(cursor_buckets_by_model(&data));
    buckets
}

/// `(bucket-key, cost flag)` pairs in the exact order `_build_cost_args` emits.
const COST_ARG_MAPPING: [(&str, &str); 26] = [
    ("CLAUDE_T", "--claude-tokens"),
    ("CODEX_T", "--codex-tokens"),
    ("CURSOR_T", "--cursor-tokens"),
    ("CLAUDE_SUB_T", "--claude-sub-tokens"),
    ("C_IN", "--claude-input-tokens"),
    ("C_CR", "--claude-cache-read-tokens"),
    ("C_CW5", "--claude-cache-write-5m-tokens"),
    ("C_CW1", "--claude-cache-write-1h-tokens"),
    ("C_OUT", "--claude-output-tokens"),
    ("D_IN", "--codex-input-tokens"),
    ("D_CR", "--codex-cached-input-tokens"),
    ("D_OUT", "--codex-output-tokens"),
    ("D_MINI_IN", "--codex-mini-input-tokens"),
    ("D_MINI_CR", "--codex-mini-cached-input-tokens"),
    ("D_MINI_OUT", "--codex-mini-output-tokens"),
    ("U_IN", "--cursor-input-tokens"),
    ("U_CR", "--cursor-cache-read-tokens"),
    ("U_OUT", "--cursor-output-tokens"),
    ("U_GROK_IN", "--cursor-grok-input-tokens"),
    ("U_GROK_CR", "--cursor-grok-cache-read-tokens"),
    ("U_GROK_OUT", "--cursor-grok-output-tokens"),
    ("CS_IN", "--claude-sub-input-tokens"),
    ("CS_CR", "--claude-sub-cache-read-tokens"),
    ("CS_CW5", "--claude-sub-cache-write-5m-tokens"),
    ("CS_CW1", "--claude-sub-cache-write-1h-tokens"),
    ("CS_OUT", "--claude-sub-output-tokens"),
];

/// Port of `_build_cost_args`.
fn build_cost_args(buckets: &BTreeMap<String, i64>) -> Vec<String> {
    let sum: i64 = buckets
        .iter()
        .filter(|(key, _)| !key.ends_with("_T"))
        .map(|(_, value)| *value)
        .sum();
    if sum == 0 {
        return vec!["--cost-unavailable".to_owned()];
    }
    let mut args: Vec<String> = Vec::new();
    for (key, flag) in COST_ARG_MAPPING {
        if let Some(value) = buckets.get(key) {
            args.push(flag.to_owned());
            args.push(value.to_string());
        }
    }
    args
}

// ---------------------------------------------------------------------------
// render-final-summary: summary-field helpers
// ---------------------------------------------------------------------------

/// Port of `_duration`.
fn duration(design_tmpdir: &Path) -> String {
    let path = design_tmpdir.join("timing-report-final.json");
    if !is_regular_file(&path) {
        return "N/A".to_owned();
    }
    let Some(text) = read_lossy(&path) else {
        return "N/A".to_owned();
    };
    let Ok(Value::Object(data)) = serde_json::from_str::<Value>(&text) else {
        return "N/A".to_owned();
    };
    let value = data.get("total_hms").or_else(|| data.get("total_seconds"));
    match value {
        Some(Value::String(text)) if !text.is_empty() => text.clone(),
        Some(Value::Number(number)) => {
            let rendered = number.to_string();
            if rendered == "0" { "N/A".to_owned() } else { rendered }
        }
        _ => "N/A".to_owned(),
    }
}

/// Port of `_oos_info`.
fn oos_info(design_tmpdir: &Path) -> (i64, String) {
    let sentinel = design_tmpdir.join("oos-issues-created.md");
    if !sentinel.is_file() {
        return (0, String::new());
    }
    let Some(text) = fs::read_to_string(&sentinel).ok() else {
        return (0, String::new());
    };
    let mut urls: Vec<String> = Vec::new();
    for raw_line in text.split('\n') {
        if !raw_line.starts_with("OOS_FILE_MAP\t") {
            continue;
        }
        let parts: Vec<&str> = raw_line.split('\t').collect();
        if parts.len() < OOS_FILE_MAP_FIELD_COUNT {
            continue;
        }
        let url = parts[2].trim();
        if !url.is_empty() {
            urls.push(url.to_owned());
        }
    }
    let count = i64::try_from(urls.len()).unwrap_or(i64::MAX);
    (count, urls.join("\n"))
}

/// Port of `_plan_review_line` (uses the Rust `review_provenance` owner).
fn plan_review_line(design_tmpdir: &Path) -> String {
    let ReviewProvenance { status, rounds_completed, present: _ } =
        review_provenance(design_tmpdir);
    if status.is_empty() {
        return "N/A".to_owned();
    }
    if rounds_completed > 0 {
        let unit = if rounds_completed == 1 { "round" } else { "rounds" };
        return format!("{status} ({rounds_completed} {unit})");
    }
    status
}

/// Port of `_dynamic_archetypes_line`.
fn dynamic_archetypes_line(design_tmpdir: &Path) -> String {
    let status_file = design_tmpdir.join("step2b-drafter-status.txt");
    if !status_file.is_file() {
        return "static-only, drafter absent".to_owned();
    }
    let text = read_lossy(&status_file).unwrap_or_default();
    let scout_written = kv_value_last(&text, "SCOUT_WRITTEN");
    if scout_written != "true" {
        let reason = kv_value_last(&text, "SCOUT_FAIL_REASON");
        let reason = if reason.is_empty() { "absent" } else { &reason };
        return format!("static-only, drafter {reason}");
    }
    let manifest = design_tmpdir.join("scout-plan-manifest.json");
    let count = match read_lossy(&manifest).and_then(|body| serde_json::from_str::<Value>(&body).ok()) {
        Some(Value::Object(data)) => match data.get("archetypes") {
            Some(Value::Array(items)) => items.len(),
            _ => 0,
        },
        Some(_) => 0,
        None => return "static-only, drafter filter_failed".to_owned(),
    };
    if count > 0 {
        format!("ok ({count})")
    } else {
        "static-only, drafter empty".to_owned()
    }
}

/// Read the last `KEY=value` occurrence, stripping trailing CR (mirror of
/// `larch_io.kv_value(..., first_match=False, cr_strip="strip")`).
fn kv_value_last(text: &str, key: &str) -> String {
    let prefix = format!("{key}=");
    let mut result = String::new();
    for line in text.split('\n') {
        if let Some(rest) = line.strip_prefix(&prefix) {
            rest.trim_end_matches(['\r', '\n']).clone_into(&mut result);
        }
    }
    result
}

/// Port of `_difficulty_summary_line`.
fn difficulty_summary_line(design_tmpdir: &Path) -> String {
    let record_path = design_tmpdir.join(larch_core::DIFFICULTY_RECORD_BASENAME);
    if is_regular_file(&record_path)
        && let Some(text) = read_lossy(&record_path)
        && let Ok(Value::Object(data)) = serde_json::from_str::<Value>(&text)
    {
        return larch_core::difficulty_line(&data);
    }
    let raw_rating = larch_core::read_rating_file(&design_tmpdir.join(larch_core::DESIGN_RAW_RATING_BASENAME));
    if let Some(rating) = raw_rating {
        return format!("predicted {0}; applied {0}", rating.adjusted_tier);
    }
    let plan_path = design_tmpdir.join("plan.txt");
    if is_regular_file(&plan_path)
        && let Some(text) = read_lossy(&plan_path)
    {
        let tier = larch_core::plan_difficulty(&text);
        if !tier.is_empty() {
            return format!("predicted {tier}; applied {tier}");
        }
    }
    String::new()
}

/// Port of `_persist_difficulty_record`.
fn persist_difficulty_record(design_tmpdir: &Path, run_id: &str) {
    if run_id.is_empty() || run_id == "unknown" {
        return;
    }
    let record_path = design_tmpdir.join(larch_core::DIFFICULTY_RECORD_BASENAME);
    if !is_regular_file(&record_path) {
        let mut raw_rating = larch_core::read_rating_file(
            &design_tmpdir.join(larch_core::DESIGN_RAW_RATING_BASENAME),
        );
        if raw_rating.is_none() {
            for candidate in [
                design_tmpdir.join("composed-plan.md"),
                design_tmpdir.join("plan.txt"),
            ] {
                if !is_regular_file(&candidate) {
                    continue;
                }
                let Some(text) = read_lossy(&candidate) else {
                    continue;
                };
                let tier = larch_core::plan_difficulty(&text);
                if !tier.is_empty() {
                    let object = serde_json::json!({
                        "predicted_tier": tier,
                        "confidence": "medium",
                        "rationale": "design plan metadata",
                    });
                    if let Ok(rating) = larch_core::validate_rating_object(&object) {
                        raw_rating = Some(rating);
                    }
                    break;
                }
            }
        }
        let Some(rating) = raw_rating else {
            return;
        };
        let build = larch_core::BuildRecord {
            rater: "design",
            rater_tool: "claude",
            rater_model: "unknown",
            design_rating: Some(&rating),
            implement_rating: None,
            fallback_rating: None,
            changed_paths: &[],
            floors: &[],
            panel_skipped: "",
            audit_upgrade: "",
            escalations: &[],
            override_source: "",
            override_tier: "",
            panel_tier: "",
            round_cap: None,
            codex_model_role: "",
            audit_evaluated: None,
            escalated_round: None,
        };
        if let Ok(record) = larch_core::build_record(build) {
            let _ = larch_core::write_record_map(&record_path, &record);
        }
    }
    let _ = run_larch_capture(&[
        OsString::from("run-log"),
        OsString::from("write"),
        OsString::from("--skill"),
        OsString::from("design"),
        OsString::from("--run-id"),
        OsString::from(run_id),
        OsString::from("--batch"),
        OsString::from("difficulty-rating"),
        OsString::from("--input-file"),
        record_path.into_os_string(),
    ]);
}

/// Port of `_refresh_final_reports`.
///
/// The token refresh goes through the Python `cli.py` seam exactly as the
/// pre-cutover module did (`_run_cli`); that verb is no longer registered
/// there, so it writes nothing, matching the frozen reference byte-for-byte.
/// The timing refresh runs the Rust `timing report` owner through the verified
/// bootstrap, mirroring `_run_larch`.
fn refresh_final_reports(design_tmpdir: &Path) {
    let token_output = design_tmpdir.join("token-report-final.json");
    let _ = run_python_verb(
        [
            OsString::from("token"),
            OsString::from("report"),
            OsString::from("--full"),
            OsString::from("--format"),
            OsString::from("json"),
            OsString::from("--output"),
            token_output.into_os_string(),
        ],
        PYTHON_BRIDGE_TIMEOUT,
    );
    let timing_output = design_tmpdir.join("timing-report-final.json");
    let _ = run_larch_capture(&[
        OsString::from("timing"),
        OsString::from("report"),
        OsString::from("--full"),
        OsString::from("--format"),
        OsString::from("json"),
        OsString::from("--output"),
        timing_output.into_os_string(),
    ]);
}

/// Port of `_published_run_logs_path`.
fn published_run_logs_path(design_tmpdir: &Path, run_id: &str) -> String {
    if run_id.is_empty() || run_id == "unknown" {
        return "N/A".to_owned();
    }
    let result_env = design_tmpdir.join(".design-publish-result.env");
    if !is_regular_file(&result_env) {
        return "N/A".to_owned();
    }
    let Some(text) = read_lossy(&result_env) else {
        return "N/A".to_owned();
    };
    if kv_value_last(&text, "LOG_PUBLISH_COMPLETED") != "true" {
        return "N/A".to_owned();
    }
    let repo_root_raw = read_source_env_value(&design_tmpdir.join("source-env.sh"), "REPO_ROOT");
    let manifest = design_tmpdir
        .join("larch-logs")
        .join("design")
        .join(run_id)
        .join("manifest.json");
    design_run_log_reference(
        if repo_root_raw.is_empty() { None } else { Some(Path::new(&repo_root_raw)) },
        run_id,
        &manifest,
    )
}

/// Port of `storage_config.run_log_reference` for `skill="design"`.
fn design_run_log_reference(repo_root: Option<&Path>, run_id: &str, manifest: &Path) -> String {
    let disabled = format!(
        "no archive published because run-log storage was disabled, skill `design`, run ID `{run_id}`"
    );
    if design_pins_disabled_publication(manifest, run_id) {
        return disabled;
    }
    let mut provider = "unknown".to_owned();
    if let Some(repo_root) = repo_root
        && let Ok((repo_root, origin, environ)) =
            crate::run_log_commands::resolve_repository_environment_path(Some(repo_root))
        && let Ok(resolution) = larch_core::resolve_run_log_storage(&repo_root, &environ, &origin)
    {
        if resolution.mode() == larch_core::RunLogStorageMode::Disabled {
            return disabled;
        }
        if let Ok(storage) = larch_core::require_enabled_storage(&resolution) {
            storage.scheme().clone_into(&mut provider);
        }
    }
    format!("provider `{provider}`, skill `design`, run ID `{run_id}`")
}

/// Port of `storage_config._pins_disabled_publication` for `skill="design"`.
fn design_pins_disabled_publication(manifest: &Path, run_id: &str) -> bool {
    if manifest.is_symlink() || !manifest.is_file() {
        return false;
    }
    let Some(text) = read_lossy(manifest) else {
        return false;
    };
    let Ok(Value::Object(document)) = serde_json::from_str::<Value>(&text) else {
        return false;
    };
    let string = |key: &str| document.get(key).and_then(Value::as_str);
    if document.get("lifecycle_schema_version").and_then(Value::as_u64)
        != Some(larch_core::LIFECYCLE_SCHEMA_VERSION)
        || string("publication_mode") != Some("disabled")
        || !string("storage_resolution_reason")
            .is_some_and(|reason| DISABLED_STORAGE_REASONS.contains(&reason))
        || string("skill") != Some("design")
        || string("run_id") != Some(run_id)
    {
        return false;
    }
    if !string("local_namespace_id").is_some_and(|value| {
        value.len() == 64
            && value
                .chars()
                .all(|character| character.is_ascii_hexdigit() && !character.is_ascii_uppercase())
    }) {
        return false;
    }
    ["storage_base_uri", "tool_repo_uri", "storage_origin_id"]
        .iter()
        .all(|field| document.get(*field).is_none_or(Value::is_null))
}

// ---------------------------------------------------------------------------
// render-final-summary: enrichment and prefix passes
// ---------------------------------------------------------------------------

/// Port of `_append_render_warning`.
fn append_render_warning(design_tmpdir: &Path, message: &str) {
    let log = design_tmpdir.join("execution-issues.md");
    let _ = crate::run_log_entry_commands::append_execution_issue(
        &log,
        "Warnings",
        &format!("- **design-summary**: {message}"),
    );
}

/// Port of `review_phase_detail.render_design_review_detail` (the only helper
/// the render-final-summary path reaches). Invokes the shared phase-detail
/// renderer in-process, then redacts and drops truncated output.
fn render_design_review_detail(design_tmpdir: &Path) -> String {
    let rounds_root = design_tmpdir.join("plan-review");
    if !(rounds_root.is_dir()) {
        return String::new();
    }
    let timing_ledger = design_tmpdir.join("timing-ledger.tsv");
    let findings_file = design_tmpdir.join("review-findings-full.jsonl");
    let token_ledger = latest_token_ledger(design_tmpdir);
    let request = larch_adapters::phase_detail::RenderRequest {
        rounds_root: &rounds_root,
        skill: larch_adapters::phase_detail::PhaseSkill::Design,
        timing_ledger: timing_ledger.is_file().then_some(timing_ledger.as_path()),
        token_ledger: token_ledger.as_deref(),
        findings_file: findings_file.is_file().then_some(findings_file.as_path()),
        top_n: 7,
        gantt_enabled: true,
    };
    let stdout = larch_adapters::phase_detail::render_phase_detail(&request);
    if stdout.trim().is_empty() {
        return String::new();
    }
    let text = redact_outbound(&stdout);
    if text.contains("[content truncated") {
        return String::new();
    }
    text
}

/// Port of `_latest_token_ledger`.
#[allow(clippy::case_sensitive_file_extension_comparisons)] // Mirrors the Python `*.jsonl` glob.
fn latest_token_ledger(tmpdir: &Path) -> Option<PathBuf> {
    let mut ledgers: Vec<(std::time::SystemTime, PathBuf)> = Vec::new();
    for entry in fs::read_dir(tmpdir).ok()?.flatten() {
        let path = entry.path();
        let Some(name) = path.file_name().and_then(|name| name.to_str()) else {
            continue;
        };
        if name.starts_with("larch-tokens-") && name.ends_with(".jsonl") {
            let mtime = entry
                .metadata()
                .and_then(|metadata| metadata.modified())
                .unwrap_or(std::time::UNIX_EPOCH);
            ledgers.push((mtime, path));
        }
    }
    ledgers.sort_by(|left, right| left.0.cmp(&right.0));
    ledgers.pop().map(|(_, path)| path)
}

/// Port of `_join_prefixed_summary`.
fn join_prefixed_summary(prefix_sections: &[String], summary_body: &str) -> String {
    let sections: Vec<String> = prefix_sections
        .iter()
        .filter(|section| !section.trim().is_empty())
        .map(|section| section.trim_matches('\n').to_owned())
        .collect();
    if sections.is_empty() {
        return summary_body.to_owned();
    }
    let mut joined = sections;
    joined.push(summary_body.trim_matches('\n').to_owned());
    format!("{}\n", joined.join("\n\n"))
}

/// Port of `_write_enriched_post_publish_summary`.
fn write_enriched_post_publish_summary(
    design_tmpdir: &Path,
    out_file: &Path,
    load_result: &LoadResult,
) -> i32 {
    let Some(summary_body) = fs::read_to_string(out_file).ok() else {
        return enriched_degraded_recovery(design_tmpdir, out_file, None);
    };
    let issue_detail = build_issue_detail_section(load_result, |kind, details| {
        crate::final_report_commands::assess_issue_details(design_tmpdir, kind, details)
    });
    let detail = render_design_review_detail(design_tmpdir);
    let body = join_prefixed_summary(&[detail, issue_detail], &summary_body);
    if fs::write(out_file, &body).is_err() {
        return enriched_degraded_recovery(design_tmpdir, out_file, Some(&summary_body));
    }
    print!("{body}");
    if !body.ends_with('\n') {
        println!();
    }
    0
}

/// Port of the `OSError` recovery branch of `_write_enriched_post_publish_summary`.
fn enriched_degraded_recovery(
    design_tmpdir: &Path,
    out_file: &Path,
    _summary_body: Option<&str>,
) -> i32 {
    let message = "design render-final-summary: failed to write enriched summary".to_owned();
    eprintln!("{message}");
    append_render_warning(design_tmpdir, &message);
    let reloaded = load_issue_detail_groups(design_tmpdir, None, false);
    if out_file.is_file()
        && let Some(degraded_body) = fs::read_to_string(out_file).ok()
    {
        let detail = render_design_review_detail(design_tmpdir);
        let issue_detail = build_issue_detail_section(&reloaded, |kind, details| {
            crate::final_report_commands::assess_issue_details(design_tmpdir, kind, details)
        });
        let rebuilt = if !detail.is_empty() || !issue_detail.is_empty() {
            join_prefixed_summary(&[detail, issue_detail], &degraded_body)
        } else {
            format!(
                "{}\n\n**\u{26a0} Enrich degraded: exec issue detail unavailable.**\n",
                degraded_body.trim_end_matches('\n')
            )
        };
        let _ = fs::write(out_file, rebuilt);
    }
    1
}

/// Port of `_missing_assessment_summary_warnings`.
fn missing_assessment_summary_warnings(design_tmpdir: &Path) -> Vec<String> {
    let mut warnings: Vec<String> = Vec::new();
    for (marker_name, message) in [
        (".missing-invariant-assessment-warning", MISSING_INVARIANT_ASSESSMENT_SUMMARY_WARNING),
        (".missing-guideline-assessment-warning", MISSING_GUIDELINE_ASSESSMENT_SUMMARY_WARNING),
    ] {
        let marker = design_tmpdir.join(marker_name);
        if marker.exists() && !marker.is_symlink() {
            warnings.push(message.to_owned());
        }
    }
    warnings
}

/// Port of `_prefix_missing_assessment_warnings`.
fn prefix_missing_assessment_warnings(design_tmpdir: &Path, out_file: &Path) {
    let warnings = missing_assessment_summary_warnings(design_tmpdir);
    if warnings.is_empty() {
        return;
    }
    if out_file.is_symlink() || !out_file.is_file() {
        return;
    }
    let Some(body) = fs::read_to_string(out_file).ok() else {
        return;
    };
    let prefix_lines: Vec<String> = warnings
        .into_iter()
        .filter(|warning| !body.contains(warning.as_str()))
        .collect();
    if prefix_lines.is_empty() {
        return;
    }
    let _ = fs::write(out_file, format!("{}\n\n{body}", prefix_lines.join("\n")));
}

/// Port of `_guideline_exception_disclosure`.
fn guideline_exception_disclosure(design_tmpdir: &Path) -> String {
    let note_path = design_tmpdir.join(DESIGN_ASSESSMENT);
    if note_path.is_symlink() || !note_path.is_file() {
        return String::new();
    }
    let Some(note) = read_lossy(&note_path) else {
        return String::new();
    };
    let Some(exception) = guideline_active_exception(&note) else {
        return String::new();
    };
    let redacted = redact_outbound(&exception.rationale).replace('\n', " ");
    let redacted = redacted.trim();
    if redacted.is_empty() {
        return String::new();
    }
    format!(
        "{GUIDELINE_EXCEPTION_DISCLOSURE_PREFIX} {redacted} (author: main-agent, date: {})",
        exception.date
    )
}

/// Port of `_prefix_guideline_exception_disclosure`.
fn prefix_guideline_exception_disclosure(design_tmpdir: &Path, outcome: &str, out_file: &Path) {
    if !APPROVED_OUTCOMES.contains(&outcome) {
        return;
    }
    let disclosure = guideline_exception_disclosure(design_tmpdir);
    if disclosure.is_empty() {
        return;
    }
    if out_file.is_symlink() || !out_file.is_file() {
        return;
    }
    let Some(body) = fs::read_to_string(out_file).ok() else {
        return;
    };
    if body.contains(&disclosure) {
        return;
    }
    let _ = fs::write(out_file, format!("{disclosure}\n\n{body}"));
}

/// Port of `_emit_report_gate_sidecars_file`.
fn emit_report_gate_sidecars_file(design_tmpdir: &Path) {
    let handoff = design_tmpdir.join("design-report-gate-sidecars.md");
    let sidecars = [
        design_tmpdir.join("design-failure-chat-print.md"),
        design_tmpdir.join("design-failure-operator-action-chat.md"),
    ];
    let mut chunks: Vec<String> = Vec::new();
    for sidecar in &sidecars {
        if sidecar.is_file() && file_size(sidecar) > 0
            && let Some(text) = fs::read_to_string(sidecar).ok()
        {
            chunks.push(text);
        }
    }
    if chunks.is_empty() {
        return;
    }
    let mut body = chunks.join("\n");
    if !body.ends_with('\n') {
        body.push('\n');
    }
    if fs::write(&handoff, body).is_ok() {
        println!("REPORT_GATE_SIDECARS_FILE={}", handoff.display());
    }
}

/// Port of `_run_design_failure_report_gate`.
fn run_design_failure_report_gate(
    design_tmpdir: &Path,
    phase: &str,
    outcome: &str,
    repo: &str,
    issue: &str,
    run_id: &str,
) {
    if phase != "post" {
        return;
    }
    let ex_log = design_tmpdir.join("execution-issues.md");
    let out_file = design_tmpdir.join("design-failure-report.stdout.log");
    let err_file = design_tmpdir.join("design-failure-report.stderr.log");
    let mut args: Vec<OsString> = vec![
        OsString::from("design"),
        OsString::from("failure-report"),
        OsString::from("--design-tmpdir"),
        design_tmpdir.as_os_str().to_owned(),
        OsString::from("--outcome"),
        OsString::from(outcome),
    ];
    if !repo.is_empty() {
        args.push(OsString::from("--repo"));
        args.push(OsString::from(repo));
    }
    if !issue.is_empty() {
        args.push(OsString::from("--issue"));
        args.push(OsString::from(issue));
    }
    if !run_id.is_empty() {
        args.push(OsString::from("--run-id"));
        args.push(OsString::from(run_id));
    }
    let (gate_rc, stdout, stderr) = run_larch_capture(&args);
    let _ = fs::write(&out_file, &stdout);
    let _ = fs::write(&err_file, &stderr);
    if gate_rc != 0 {
        let _ = run_larch_capture(&[
            OsString::from("run-log"),
            OsString::from("append-failure"),
            OsString::from("--log"),
            ex_log.as_os_str().to_owned(),
            OsString::from("--site"),
            OsString::from("design failure report gate"),
            OsString::from("--tool"),
            OsString::from("design-failure-report.sh"),
            OsString::from("--exit-code"),
            OsString::from(gate_rc.to_string()),
            OsString::from("--category"),
            OsString::from("Warnings"),
            OsString::from("--redact"),
            OsString::from("--output-file"),
            err_file.as_os_str().to_owned(),
        ]);
    }
}

/// Port of `invoke_render`: shell out to the still-Python `render run-summary`
/// with an unchanged argument vector so the rendered body stays byte-identical.
#[allow(clippy::too_many_arguments)]
fn invoke_render(
    design_tmpdir: &Path,
    outcome: &str,
    mode_str: &str,
    run_id: &str,
    duration: &str,
    issue: &str,
    issue_url: &str,
    oos_count: i64,
    oos_urls: &str,
    exec_issues: usize,
    warnings: usize,
    plan_review_line: &str,
    dynamic_archetypes_line: &str,
    difficulty_line: &str,
    run_logs_path: &str,
    cost_args: &[String],
) -> i32 {
    let out_file = design_tmpdir.join("final-summary.md");
    let manifest_candidates = [
        design_tmpdir.join("manifest.json"),
        design_tmpdir.join("larch-logs").join("design").join(run_id).join("manifest.json"),
    ];
    let manifest_path = manifest_candidates
        .iter()
        .find(|candidate| candidate.is_file())
        .unwrap_or(&manifest_candidates[0])
        .display()
        .to_string();
    let issue_number = if issue.is_empty() { "0" } else { issue };
    let mut args: Vec<OsString> = os_args(&[
        "render",
        "run-summary",
        "--skill",
        "design",
        "--outcome",
        outcome,
        "--mode",
        mode_str,
        "--run-id",
        run_id,
        "--duration",
        duration,
        "--issue-number",
        issue_number,
        "--issue-url",
        issue_url,
        "--pr-number",
        "0",
        "--pr-url",
        "N/A",
        "--plan-review-line",
        plan_review_line,
        "--difficulty-line",
        difficulty_line,
        "--dynamic-archetypes-line",
        dynamic_archetypes_line,
        "--code-review-line",
        "N/A",
        "--oos-count",
        &oos_count.to_string(),
        "--oos-urls",
        oos_urls,
        "--exec-issues",
        &exec_issues.to_string(),
        "--warnings",
        &warnings.to_string(),
        "--run-logs-path",
        run_logs_path,
        "--manifest-path",
        &manifest_path,
        "--output-file",
        &out_file.display().to_string(),
    ]);
    for value in cost_args {
        args.push(OsString::from(value));
    }
    match run_python_verb(args, PYTHON_BRIDGE_TIMEOUT) {
        Ok(output) => output.status().code().unwrap_or(1),
        Err(_error) => 1,
    }
}

/// Port of `upsert_final_summary_from_disk`.
fn upsert_final_summary_from_disk(
    issue: &str,
    session_id: &str,
    repo: &str,
    final_summary_path: &Path,
) -> bool {
    if final_summary_path.is_symlink()
        || !final_summary_path.is_file()
        || file_size(final_summary_path) == 0
    {
        return false;
    }
    if issue.is_empty() || issue == "0" || session_id.is_empty() {
        return false;
    }
    let marker = format!("<!-- larch:final-summary v1 runid={session_id} -->");
    let mut args: Vec<OsString> = vec![
        OsString::from("tracking-issue"),
        OsString::from("upsert-summary"),
        OsString::from("--issue"),
        OsString::from(issue),
        OsString::from("--marker"),
        OsString::from(marker),
        OsString::from("--content-file"),
        final_summary_path.as_os_str().to_owned(),
    ];
    if !repo.is_empty() {
        args.push(OsString::from("--repo"));
        args.push(OsString::from(repo));
    }
    let (rc, _stdout, _stderr) = run_larch_capture(&args);
    rc == 0
}

// ---------------------------------------------------------------------------
// render-final-summary: argument parsing + orchestration
// ---------------------------------------------------------------------------

#[allow(clippy::struct_excessive_bools)] // Mirrors the flag-set of the retired argv loop.
struct FinalSummaryArgs {
    outcome: String,
    mode_str: String,
    repo: String,
    design_tmpdir_arg: String,
    issue_number_arg: String,
    session_id_arg: String,
    issue_number_set: bool,
    session_id_set: bool,
    phase: &'static str,
    upsert_summary_comment: bool,
}

/// Port of the manual arg loop in `render_final_summary_main`.
fn parse_final_summary_args(argv: &[String]) -> FinalSummaryArgs {
    let mut parsed = FinalSummaryArgs {
        outcome: String::new(),
        mode_str: "N/A".to_owned(),
        repo: String::new(),
        design_tmpdir_arg: String::new(),
        issue_number_arg: String::new(),
        session_id_arg: String::new(),
        issue_number_set: false,
        session_id_set: false,
        phase: "post",
        upsert_summary_comment: true,
    };
    let mut i = 0;
    while i < argv.len() {
        let token = argv[i].as_str();
        let next = argv.get(i + 1);
        match token {
            "--outcome" if next.is_some() => {
                next.unwrap().clone_into(&mut parsed.outcome);
                i += 2;
            }
            "--mode" if next.is_some() => {
                next.unwrap().clone_into(&mut parsed.mode_str);
                i += 2;
            }
            "--repo" if next.is_some() => {
                next.unwrap().clone_into(&mut parsed.repo);
                i += 2;
            }
            "--design-tmpdir" if next.is_some() => {
                next.unwrap().clone_into(&mut parsed.design_tmpdir_arg);
                i += 2;
            }
            "--issue-number" if next.is_some() => {
                next.unwrap().clone_into(&mut parsed.issue_number_arg);
                parsed.issue_number_set = true;
                i += 2;
            }
            "--session-id" if next.is_some() => {
                next.unwrap().clone_into(&mut parsed.session_id_arg);
                parsed.session_id_set = true;
                i += 2;
            }
            "--pre-publish-only" => {
                parsed.phase = "pre";
                i += 1;
            }
            "--post-publish-only" => {
                parsed.phase = "post";
                i += 1;
            }
            "--skip-summary-upsert" => {
                parsed.upsert_summary_comment = false;
                i += 1;
            }
            _ => {
                i += 1;
            }
        }
    }
    parsed
}

/// Port of `render_final_summary_main`.
fn render_final_summary_impl(arguments: &[OsString]) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let parsed = parse_final_summary_args(&argv);
    let design_tmpdir = match resolve_validated_tmpdir(&parsed) {
        Ok(path) => path,
        Err(exit) => return exit,
    };

    let run_id_raw = if parsed.session_id_set {
        parsed.session_id_arg.clone()
    } else {
        std::env::var("SESSION_ID").unwrap_or_default()
    };
    let run_id = if run_id_raw.is_empty() { "unknown".to_owned() } else { run_id_raw };
    let issue = if parsed.issue_number_set {
        parsed.issue_number_arg.clone()
    } else {
        std::env::var("ISSUE_NUMBER").unwrap_or_default()
    };
    let issue_url = if !issue.is_empty()
        && issue != "0"
        && !parsed.repo.is_empty()
        && parsed.repo.contains('/')
    {
        format!("https://github.com/{}/issues/{issue}", parsed.repo)
    } else {
        "N/A".to_owned()
    };

    persist_difficulty_record(&design_tmpdir, &run_id);
    refresh_final_reports(&design_tmpdir);
    let cost_args = build_cost_args(&read_token_report(&design_tmpdir));
    let duration = duration(&design_tmpdir);
    let (oos_count, oos_urls) = oos_info(&design_tmpdir);
    let run_logs_path = published_run_logs_path(&design_tmpdir, &run_id);
    let out_file = design_tmpdir.join("final-summary.md");
    run_design_failure_report_gate(
        &design_tmpdir,
        parsed.phase,
        &parsed.outcome,
        &parsed.repo,
        &issue,
        &run_id,
    );
    let load_result = load_issue_detail_groups(&design_tmpdir, None, false);
    let (exec_issues, warnings) = count_load_result(&load_result);

    let rc = invoke_render(
        &design_tmpdir,
        &parsed.outcome,
        &parsed.mode_str,
        &run_id,
        &duration,
        &issue,
        &issue_url,
        oos_count,
        &oos_urls,
        exec_issues,
        warnings,
        &plan_review_line(&design_tmpdir),
        &dynamic_archetypes_line(&design_tmpdir),
        &difficulty_summary_line(&design_tmpdir),
        &run_logs_path,
        &cost_args,
    );

    if rc != 0 || !out_file.is_file() || file_size(&out_file) == 0 {
        write_degraded_fallback(
            &out_file,
            &run_id,
            &parsed.outcome,
            &duration,
            exec_issues,
            warnings,
        );
    }

    if parsed.phase == "pre" {
        prefix_missing_assessment_warnings(&design_tmpdir, &out_file);
        return ExitCode::SUCCESS;
    }

    let exit_rc = write_enriched_post_publish_summary(&design_tmpdir, &out_file, &load_result);
    prefix_missing_assessment_warnings(&design_tmpdir, &out_file);
    prefix_guideline_exception_disclosure(&design_tmpdir, &parsed.outcome, &out_file);
    let summary_written = exit_rc == 0 && out_file.is_file() && file_size(&out_file) > 0;

    if parsed.upsert_summary_comment && summary_written {
        let _ = upsert_final_summary_from_disk(&issue, &run_id, &parsed.repo, &out_file);
    }
    emit_report_gate_sidecars_file(&design_tmpdir);

    exit_from_i32(exit_rc)
}

/// Resolve `DESIGN_TMPDIR` and validate the outcome, mirroring the guard block
/// of `render_final_summary_main`.
fn resolve_validated_tmpdir(parsed: &FinalSummaryArgs) -> Result<PathBuf, ExitCode> {
    let design_tmpdir_str = if parsed.design_tmpdir_arg.is_empty() {
        std::env::var("DESIGN_TMPDIR").unwrap_or_default()
    } else {
        parsed.design_tmpdir_arg.clone()
    };
    if design_tmpdir_str.is_empty() {
        eprintln!("design render-final-summary: DESIGN_TMPDIR unset");
        return Err(ExitCode::from(2));
    }
    let design_tmpdir = PathBuf::from(&design_tmpdir_str);
    if !design_tmpdir.is_dir() {
        eprintln!("design render-final-summary: DESIGN_TMPDIR not a directory");
        return Err(ExitCode::from(2));
    }
    if parsed.outcome.is_empty() {
        eprintln!("design render-final-summary: --outcome is required");
        return Err(ExitCode::from(2));
    }
    if !VALID_OUTCOMES.contains(&parsed.outcome.as_str()) {
        eprintln!(
            "design render-final-summary: outcome not in enumeration: {}",
            parsed.outcome
        );
        return Err(ExitCode::from(2));
    }
    Ok(design_tmpdir)
}

/// Port of the degraded-fallback body write in `render_final_summary_main`.
fn write_degraded_fallback(
    out_file: &Path,
    run_id: &str,
    outcome: &str,
    duration: &str,
    exec_issues: usize,
    warnings: usize,
) {
    let body = format!(
        "## /design run {run_id}: {outcome}\n\n\
         **\u{26a0} Degraded fallback: full renderer failed.**\n\n\
         - **Outcome**: {outcome_display}\n\
         - **Duration**: {duration}\n\
         - **Cost**: N/A\n\
         - **Exec issues**: {exec_issues}\n\
         - **Warnings**: {warnings}\n",
        outcome_display = map_outcome_display(outcome),
    );
    let _ = fs::write(out_file, body);
}

/// Convert an `i32` process code to an `ExitCode` (saturating like the sibling
/// design owners).
fn exit_from_i32(code: i32) -> ExitCode {
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

/// Rust owner for `design render-final-summary` (#8581).
pub fn render_final_summary(arguments: &[OsString]) -> ExitCode {
    render_final_summary_impl(arguments)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn os(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn rows_for(values: &[&str]) -> Vec<(String, String)> {
        let argv = utf8_arguments(&os(values));
        let args = parse_gate_args(&argv).unwrap_or_else(|_| panic!("parse {values:?}"));
        match args.gate.as_str() {
            "A" => render_gate_a(args.without_see_full_plan).rows(),
            "B" => render_gate_b(args.accepted_count, args.approve_requested)
                .expect("gate b")
                .rows(),
            _ => render_gate_c(
                args.design_tmpdir.as_deref(),
                args.without_see_full_plan,
                args.panel_failed,
                args.accepted_audit_escalation,
            )
            .rows(),
        }
    }

    #[test]
    fn gate_a_lists_see_full_plan_first() {
        let rows = rows_for(&["--gate", "A"]);
        assert_eq!(rows[0], ("GATE_RENDER_STATUS".to_owned(), "ok".to_owned()));
        assert_eq!(rows[4], ("OPTION_COUNT".to_owned(), "3".to_owned()));
        assert_eq!(rows[5].1, "See full plan");
    }

    #[test]
    fn gate_a_without_see_full_plan_drops_option() {
        let rows = rows_for(&["--gate", "A", "--without-see-full-plan"]);
        assert_eq!(rows[4], ("OPTION_COUNT".to_owned(), "2".to_owned()));
        assert_eq!(rows[5].1, "Ready for review");
    }

    #[test]
    fn gate_b_auto_apply_message_carries_count() {
        let rows = rows_for(&["--gate", "B", "--accepted-count", "3"]);
        assert!(rows.iter().any(|(key, value)| key == "AUTO_APPLY_MESSAGE"
            && value == "\u{2139} 3.5: Gate B — auto-applying 3 accepted finding(s)"));
    }

    #[test]
    fn gate_b_approve_requested_switches_extras() {
        let rows = rows_for(&["--gate", "B", "--approve-requested", "true"]);
        assert!(rows.iter().any(|(key, value)| key == "PROMPT_REQUIRED" && value == "true"));
        assert!(rows.iter().any(|(key, _)| key == "EXPLICIT_COPY_OWNER"));
    }

    #[test]
    fn gate_c_panel_failed_uses_ack_label() {
        let rows = rows_for(&[
            "--gate",
            "C",
            "--panel-failed",
            "true",
            "--accepted-audit-escalation",
            "true",
        ]);
        assert_eq!(rows[5].1, "Approve final design (acknowledge panel failure)");
    }

    #[test]
    fn gate_b_negative_count_is_value_error() {
        assert_eq!(
            render_gate_b(-1, false).err(),
            Some("--accepted-count must be non-negative".to_owned())
        );
    }

    #[test]
    fn gate_a_negative_count_is_ignored() {
        // The negative guard only fires for Gate B; A ignores accepted-count.
        let argv = utf8_arguments(&os(&["--gate", "A", "--accepted-count", "-5"]));
        assert!(parse_gate_args(&argv).is_ok());
    }

    #[test]
    fn py_int_matches_python_coercion() {
        assert_eq!(parse_py_int("3"), Some(3));
        assert_eq!(parse_py_int(" -1 "), Some(-1));
        assert_eq!(parse_py_int("+7"), Some(7));
        assert_eq!(parse_py_int("1_000"), Some(1000));
        assert_eq!(parse_py_int("xx"), None);
        assert_eq!(parse_py_int("_1"), None);
        assert_eq!(parse_py_int(""), None);
    }
}
