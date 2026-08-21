//! Rust owner for design dialectic candidate and debate commands (#8584, #8593).

use std::{
    collections::{BTreeMap, BTreeSet},
    ffi::{OsStr, OsString},
    fs,
    path::PathBuf,
    process::ExitCode,
    thread,
    time::{Duration, Instant},
};

use larch_adapters::{
    PathIntent, TemporaryRoot, atomic_write_utf8_in, read_utf8, remove_file_if_present,
};
use larch_core::design::{
    DialecticCandidate, DialecticCandidateSet, dialectic_plan_fingerprint, dialectic_slugify,
    infer_dialectic_plan_choice, parse_dialectic_candidates, reconcile_dialectic_candidates,
    render_dialectic_candidates_compact, render_dialectic_candidates_pretty,
};
use larch_core::{
    ensure_ascii_json, python_float, python_int as parse_python_integer, split_text_lines,
    trim_python_whitespace,
};
use regex::RegexBuilder;
use serde::Serialize;
use serde_json::{Value, json};

use crate::{
    argparse_compat::parse_required_with_help, run_log_entry_commands::append_execution_issue,
    runtime_entrypoint::run_verified_larch_with_timeout,
};

const AUTO_CANDIDATES: &str = "dialectic-clarifier-candidates.json";
const MANUAL_CANDIDATES: &str = "dialectic-manual-candidates.json";
const RAW_PENDING: &str = ".dialectic-raw-pending.json";
const STATUS_FILE: &str = "dialectic-clarifier-status.json";
const DIGEST_FILE: &str = "dialectic-clarifier-digest.md";
const GENERATION_FILE: &str = "dialectic-clarifier-generation.txt";
const BALLOT_FILE: &str = "dialectic-ballot.txt";
const MANUAL_REQUEST: &str = "dialectic-manual-request.txt";
const COMPLETED_GATEC: &str = ".completed/dialectic-gatec-terminal";
const JUDGE_COUNT: usize = 3;
const VOTE_THRESHOLD: usize = 2;

const WRITE_PROGRAM: &str = "cli.py design dialectic-write-candidates";
const WRITE_USAGE: &str = "usage: cli.py design dialectic-write-candidates [-h] --design-tmpdir\n                                                DESIGN_TMPDIR --content-file\n                                                CONTENT_FILE";
const WRITE_HELP: &str = "usage: cli.py design dialectic-write-candidates [-h] --design-tmpdir\n                                                DESIGN_TMPDIR --content-file\n                                                CONTENT_FILE\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --content-file CONTENT_FILE";

const PROMOTE_PROGRAM: &str = "cli.py design dialectic-promote-candidates";
const PROMOTE_USAGE: &str = "usage: cli.py design dialectic-promote-candidates [-h] --design-tmpdir\n                                                  DESIGN_TMPDIR\n                                                  [--raw-dialectic-file RAW_DIALECTIC_FILE]";
const PROMOTE_HELP: &str = "usage: cli.py design dialectic-promote-candidates [-h] --design-tmpdir\n                                                  DESIGN_TMPDIR\n                                                  [--raw-dialectic-file RAW_DIALECTIC_FILE]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --raw-dialectic-file RAW_DIALECTIC_FILE";

const VALIDATE_PROGRAM: &str = "cli.py design dialectic-validate-candidates";
const VALIDATE_USAGE: &str = "usage: cli.py design dialectic-validate-candidates [-h]\n                                                   [--content-file CONTENT_FILE]\n                                                   [--design-tmpdir DESIGN_TMPDIR]\n                                                   [--require-fingerprint]";
const VALIDATE_HELP: &str = "usage: cli.py design dialectic-validate-candidates [-h]\n                                                   [--content-file CONTENT_FILE]\n                                                   [--design-tmpdir DESIGN_TMPDIR]\n                                                   [--require-fingerprint]\n\noptions:\n  -h, --help            show this help message and exit\n  --content-file CONTENT_FILE\n  --design-tmpdir DESIGN_TMPDIR\n  --require-fingerprint";

const CLEAR_PROGRAM: &str = "cli.py design dialectic-clear-stale";
const CLEAR_USAGE: &str = "usage: cli.py design dialectic-clear-stale [-h] --design-tmpdir DESIGN_TMPDIR\n                                           --reason REASON";
const CLEAR_HELP: &str = "usage: cli.py design dialectic-clear-stale [-h] --design-tmpdir DESIGN_TMPDIR\n                                           --reason REASON\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --reason REASON";

const GATEC_PROGRAM: &str = "cli.py design dialectic-gatec";
const GATEC_USAGE: &str = "usage: cli.py design dialectic-gatec [-h] --design-tmpdir DESIGN_TMPDIR\n                                     [--probe-only]";
const GATEC_HELP: &str = "usage: cli.py design dialectic-gatec [-h] --design-tmpdir DESIGN_TMPDIR\n                                     [--probe-only]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --probe-only";

const MANUAL_PROGRAM: &str = "cli.py design dialectic-manual";
const MANUAL_USAGE: &str = "usage: cli.py design dialectic-manual [-h] --design-tmpdir DESIGN_TMPDIR\n                                      [--request-file REQUEST_FILE]\n                                      [--request REQUEST]";
const MANUAL_HELP: &str = "usage: cli.py design dialectic-manual [-h] --design-tmpdir DESIGN_TMPDIR\n                                      [--request-file REQUEST_FILE]\n                                      [--request REQUEST]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --request-file REQUEST_FILE\n  --request REQUEST";

#[derive(Clone, Debug)]
struct StatusSidecar {
    kind: String,
    plan_fingerprint: String,
    ordered_candidate_ids: Vec<String>,
    generation: i64,
    state: String,
}

#[derive(Clone, Debug, Serialize)]
struct DigestRow {
    decision_id: String,
    title: String,
    option_a: String,
    option_b: String,
    option_a_steelman: String,
    option_b_steelman: String,
    drafter_pick: String,
    panel_lean: String,
    rationale: String,
    disposition: String,
    thesis_votes: usize,
    anti_thesis_votes: usize,
}

struct DebateResult {
    text: String,
    ok: bool,
    rows: Vec<DigestRow>,
}

#[derive(Clone)]
struct Slot {
    name: String,
    output_name: String,
    arguments: Vec<OsString>,
}

trait DebateEffects {
    fn run_slots(
        &self,
        root: &TemporaryRoot,
        slots: &[Slot],
        deadline: Instant,
    ) -> (BTreeMap<String, String>, bool);
}

struct LiveDebateEffects;

impl DebateEffects for LiveDebateEffects {
    #[allow(clippy::needless_collect)] // Launch every slot before joining so panel work stays concurrent.
    fn run_slots(
        &self,
        root: &TemporaryRoot,
        slots: &[Slot],
        deadline: Instant,
    ) -> (BTreeMap<String, String>, bool) {
        let results = thread::scope(|scope| {
            let handles = slots
                .iter()
                .map(|slot| {
                    let arguments = slot.arguments.clone();
                    let timeout = deadline.saturating_duration_since(Instant::now());
                    (
                        slot,
                        scope.spawn(move || run_verified_larch_with_timeout(&arguments, timeout)),
                    )
                })
                .collect::<Vec<_>>();
            handles
                .into_iter()
                .map(|(slot, handle)| (slot, handle.join()))
                .collect::<Vec<_>>()
        });
        let mut outputs = BTreeMap::new();
        let mut completed = true;
        for (slot, result) in results {
            let Ok(result) = result else {
                completed = false;
                continue;
            };
            let Ok(output) = result else {
                completed = false;
                continue;
            };
            if !output.status().success() {
                continue;
            }
            if let Ok(text) = read_root_lossy(root, &slot.output_name) {
                let text = text.trim().to_owned();
                if !text.is_empty() {
                    let _ = outputs.insert(slot.name.clone(), text);
                }
            }
        }
        (outputs, completed)
    }
}

fn resolve_design_root(path: &OsStr) -> Result<TemporaryRoot, String> {
    let path = PathBuf::from(path);
    let valid = fs::symlink_metadata(&path)
        .is_ok_and(|metadata| metadata.is_dir() && !metadata.file_type().is_symlink());
    if !valid {
        return Err("design tmpdir must be an existing non-symlink directory".to_owned());
    }
    let canonical = fs::canonicalize(path)
        .map_err(|_error| "design tmpdir must be an existing non-symlink directory".to_owned())?;
    TemporaryRoot::resolve(Some(&canonical))
        .map_err(|_error| "design tmpdir must be an existing non-symlink directory".to_owned())
}

fn read_root_text(root: &TemporaryRoot, name: &str) -> Result<String, String> {
    let confined = root
        .confine(root.path().join(name), PathIntent::Read)
        .map_err(|error| error.to_string())?;
    read_utf8(&confined).map_err(|error| error.to_string())
}

fn read_root_bytes(root: &TemporaryRoot, name: &str) -> Result<Vec<u8>, String> {
    crate::launcher_support::read_confined_bytes_checked(&root.path().join(name))
}

fn root_file_exists(root: &TemporaryRoot, name: &str) -> bool {
    root.confine(root.path().join(name), PathIntent::Read)
        .is_ok()
}

fn write_root_text(root: &TemporaryRoot, name: &str, text: &str) -> Result<(), String> {
    atomic_write_utf8_in(root, &root.path().join(name), text, false, 0o600)
        .map_err(|error| error.to_string())
}

fn unlink_root_file(root: &TemporaryRoot, name: &str) -> Result<(), String> {
    root.revalidate().map_err(|error| error.to_string())?;
    let path = root.path().join(name);
    remove_file_if_present(&path)?;
    root.revalidate().map_err(|error| error.to_string())
}

fn plan_bytes(root: &TemporaryRoot) -> Result<Vec<u8>, String> {
    if !root_file_exists(root, "plan.txt") {
        return Err("plan.txt missing".to_owned());
    }
    read_root_bytes(root, "plan.txt")
}

fn plan_fingerprint(root: &TemporaryRoot) -> Result<String, String> {
    plan_bytes(root).map(|bytes| dialectic_plan_fingerprint(&bytes))
}

fn promote_content(root: &TemporaryRoot, content: &str) -> Result<(), String> {
    let plan = plan_bytes(root)?;
    let fingerprint = dialectic_plan_fingerprint(&plan);
    let candidates = parse_dialectic_candidates(content, Some(&fingerprint), false)
        .map_err(|error| error.to_string())?;
    reconcile_dialectic_candidates(&candidates, &String::from_utf8_lossy(&plan))
        .map_err(|error| error.to_string())?;
    let output =
        render_dialectic_candidates_pretty(&candidates).map_err(|error| error.to_string())?;
    write_root_text(root, AUTO_CANDIDATES, &output)
}

fn kv_safe(value: &str) -> String {
    let mut safe = String::new();
    let mut separator_pending = false;
    for character in value.chars() {
        if character.is_ascii_alphanumeric() || matches!(character, '_' | '.' | ':' | '-') {
            if separator_pending && !safe.is_empty() {
                safe.push('-');
            }
            separator_pending = false;
            safe.push(character);
        } else {
            separator_pending = true;
        }
    }
    let safe = safe.trim_matches('-');
    let safe = safe.get(..safe.len().min(160)).unwrap_or(safe);
    if safe.is_empty() {
        "invalid".to_owned()
    } else {
        safe.to_owned()
    }
}

fn print_write_failure(reason: &str) {
    println!("DIALECTIC_CANDIDATES_WRITTEN=false");
    println!("DIALECTIC_CANDIDATES_FAIL_REASON={}", kv_safe(reason));
}

/// Validate and normalize a candidate payload from a file or stdin.
pub fn validate_candidates(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        VALIDATE_PROGRAM,
        VALIDATE_USAGE,
        VALIDATE_HELP,
        &["--content-file", "--design-tmpdir"],
        &["--require-fingerprint"],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let content = if let Some(path) = parsed.value("--content-file") {
        match fs::read_to_string(path) {
            Ok(content) => content,
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        }
    } else {
        let mut content = String::new();
        if let Err(error) = std::io::Read::read_to_string(&mut std::io::stdin(), &mut content) {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
        content
    };
    let fingerprint = match parsed.value("--design-tmpdir") {
        Some(path) => match resolve_design_root(path).and_then(|root| plan_fingerprint(&root)) {
            Ok(fingerprint) => Some(fingerprint),
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        },
        None => None,
    };
    match parse_dialectic_candidates(
        &content,
        fingerprint.as_deref(),
        parsed.flag("--require-fingerprint"),
    ) {
        Ok(candidates) => {
            let output = match render_dialectic_candidates_compact(&candidates) {
                Ok(output) => output,
                Err(error) => {
                    eprintln!("{error}");
                    return ExitCode::FAILURE;
                }
            };
            println!("DIALECTIC_CANDIDATES_VALID=true");
            println!("{output}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            println!("DIALECTIC_CANDIDATES_VALID=false");
            println!(
                "DIALECTIC_CANDIDATES_FAIL_REASON={}",
                kv_safe(&error.to_string())
            );
            ExitCode::FAILURE
        }
    }
}

/// Promote the pending drafter sidecar against the current plan, fail-open.
pub fn promote_candidates(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        PROMOTE_PROGRAM,
        PROMOTE_USAGE,
        PROMOTE_HELP,
        &["--design-tmpdir", "--raw-dialectic-file"],
        &[],
        &["--design-tmpdir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let root = match resolve_design_root(parsed.value("--design-tmpdir").expect("required option"))
    {
        Ok(root) => root,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    let raw = parsed
        .value("--raw-dialectic-file")
        .map_or_else(|| root.path().join(RAW_PENDING), PathBuf::from);
    if !fs::metadata(&raw).is_ok_and(|metadata| metadata.is_file()) {
        print_write_failure("absent");
        return ExitCode::SUCCESS;
    }
    let result = fs::read_to_string(&raw)
        .map_err(|error| error.to_string())
        .and_then(|content| promote_content(&root, &content));
    if let Err(error) = result {
        print_write_failure(&error);
        return ExitCode::SUCCESS;
    }
    if let Err(error) = fs::remove_file(&raw)
        && error.kind() != std::io::ErrorKind::NotFound
    {
        eprintln!("{}: {error}", raw.display());
        return ExitCode::FAILURE;
    }
    println!("DIALECTIC_CANDIDATES_WRITTEN=true");
    ExitCode::SUCCESS
}

/// Write candidate JSON from a required content file.
pub fn write_candidates(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        WRITE_PROGRAM,
        WRITE_USAGE,
        WRITE_HELP,
        &["--design-tmpdir", "--content-file"],
        &[],
        &["--design-tmpdir", "--content-file"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let root = match resolve_design_root(parsed.value("--design-tmpdir").expect("required option"))
    {
        Ok(root) => root,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    let source = parsed.value("--content-file").expect("required option");
    if !fs::metadata(source).is_ok_and(|metadata| metadata.is_file()) {
        print_write_failure("content-file-missing");
        return ExitCode::from(2);
    }
    let result = fs::read_to_string(source)
        .map_err(|error| error.to_string())
        .and_then(|content| promote_content(&root, &content));
    match result {
        Ok(()) => {
            println!("DIALECTIC_CANDIDATES_WRITTEN=true");
            ExitCode::SUCCESS
        }
        Err(error) => {
            print_write_failure(&error);
            ExitCode::from(2)
        }
    }
}

fn candidate_set(
    root: &TemporaryRoot,
    name: &str,
    fingerprint: &str,
) -> Option<DialecticCandidateSet> {
    let content = read_root_text(root, name).ok()?;
    parse_dialectic_candidates(&content, Some(fingerprint), true).ok()
}

fn read_generation(root: &TemporaryRoot) -> i64 {
    read_root_text(root, GENERATION_FILE)
        .ok()
        .and_then(|text| text.trim().parse::<i64>().ok())
        .unwrap_or_default()
        .max(0)
}

fn python_int(value: Option<&Value>) -> i64 {
    let Some(value) = value else {
        return 0;
    };
    if let Some(value) = value.as_bool() {
        return i64::from(value);
    }
    if let Some(value) = value.as_str() {
        return parse_python_integer(value).unwrap_or_default();
    }
    let Some(value) = value.as_number() else {
        return 0;
    };
    value
        .as_i64()
        .or_else(|| value.as_u64().and_then(|value| i64::try_from(value).ok()))
        .or_else(|| {
            let value = value.as_f64()?;
            value
                .is_finite()
                .then(|| value.trunc().to_string().parse().ok())
                .flatten()
        })
        .unwrap_or_default()
}

fn status_from_file(root: &TemporaryRoot) -> Option<StatusSidecar> {
    let payload: Value = serde_json::from_str(&read_root_text(root, STATUS_FILE).ok()?).ok()?;
    let object = payload.as_object()?;
    let ids = object.get("ordered_candidate_ids")?.as_array()?;
    let ordered_candidate_ids = ids
        .iter()
        .map(Value::as_str)
        .collect::<Option<Vec<_>>>()?
        .into_iter()
        .map(str::to_owned)
        .collect();
    let generation = python_int(object.get("generation"));
    let state = match object.get("state") {
        Some(Value::String(state)) => state.clone(),
        Some(_) => return None,
        None => String::new(),
    };
    Some(StatusSidecar {
        kind: object.get("kind")?.as_str()?.to_owned(),
        plan_fingerprint: object.get("plan_fingerprint")?.as_str()?.to_owned(),
        ordered_candidate_ids,
        generation,
        state,
    })
}

fn preserve_manual_status(root: &TemporaryRoot, fingerprint: &str) -> bool {
    let Some(manual) = candidate_set(root, MANUAL_CANDIDATES, fingerprint) else {
        return false;
    };
    let Some(status) = status_from_file(root) else {
        return false;
    };
    root_file_exists(root, DIGEST_FILE)
        && status.kind == "manual"
        && status.plan_fingerprint == manual.plan_fingerprint
        && status.ordered_candidate_ids == manual.ordered_ids()
        && status.generation == read_generation(root)
        && matches!(status.state.as_str(), "complete" | "fallback")
}

fn clear_stale(root: &TemporaryRoot) -> Result<(), String> {
    let fingerprint = plan_fingerprint(root).ok();
    let auto_valid = fingerprint
        .as_deref()
        .and_then(|current| candidate_set(root, AUTO_CANDIDATES, current))
        .is_some();
    if !auto_valid {
        unlink_root_file(root, AUTO_CANDIDATES)?;
    }
    let manual_preserved = fingerprint
        .as_deref()
        .is_some_and(|current| preserve_manual_status(root, current));
    let status_valid = status_from_file(root).is_some_and(|status| {
        fingerprint.as_deref() == Some(status.plan_fingerprint.as_str())
            && ((status.kind == "auto" && auto_valid)
                || (status.kind == "manual" && manual_preserved))
    });
    if !status_valid {
        unlink_root_file(root, STATUS_FILE)?;
        unlink_root_file(root, DIGEST_FILE)?;
    }
    if !manual_preserved {
        unlink_root_file(root, MANUAL_CANDIDATES)?;
        unlink_root_file(root, MANUAL_REQUEST)?;
    }
    Ok(())
}

/// Remove stale candidate artifacts while retaining the pre-promotion raw file.
pub fn clear_stale_candidates(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        CLEAR_PROGRAM,
        CLEAR_USAGE,
        CLEAR_HELP,
        &["--design-tmpdir", "--reason"],
        &[],
        &["--design-tmpdir", "--reason"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let result = resolve_design_root(parsed.value("--design-tmpdir").expect("required option"))
        .and_then(|root| clear_stale(&root));
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("dialectic-clear-stale: {error}");
            ExitCode::from(2)
        }
    }
}

fn read_root_lossy(root: &TemporaryRoot, name: &str) -> Result<String, String> {
    read_root_bytes(root, name).map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
}

fn artifact_present(root: &TemporaryRoot, name: &str) -> bool {
    root.revalidate().is_ok() && fs::symlink_metadata(root.path().join(name)).is_ok()
}

fn skip_approve_requested(root: &TemporaryRoot) -> bool {
    read_root_text(root, "run-params.json")
        .ok()
        .and_then(|text| serde_json::from_str::<Value>(&text).ok())
        .and_then(|value| value.as_object().cloned())
        .and_then(|object| object.get("skip_approve_requested").cloned())
        == Some(Value::Bool(true))
}

fn cached_digest_valid(
    root: &TemporaryRoot,
    candidates: &DialecticCandidateSet,
    kind: &str,
) -> bool {
    let Some(status) = status_from_file(root) else {
        return false;
    };
    root_file_exists(root, DIGEST_FILE)
        && status.kind == kind
        && status.plan_fingerprint == candidates.plan_fingerprint
        && status.ordered_candidate_ids == candidates.ordered_ids()
        && status.generation == read_generation(root)
        && matches!(status.state.as_str(), "complete" | "fallback")
}

fn bump_generation(root: &TemporaryRoot) -> Result<i64, String> {
    let generation = read_generation(root).saturating_add(1);
    write_root_text(root, GENERATION_FILE, &format!("{generation}\n"))?;
    Ok(generation)
}

fn write_json(root: &TemporaryRoot, name: &str, value: &Value) -> Result<(), String> {
    let text = serde_json::to_string_pretty(value).map_err(|error| error.to_string())?;
    write_root_text(root, name, &(ensure_ascii_json(&text) + "\n"))
}

fn write_status(
    root: &TemporaryRoot,
    kind: &str,
    candidates: &DialecticCandidateSet,
    generation: i64,
    state: &str,
    rows: Option<&[DigestRow]>,
) -> Result<(), String> {
    let mut value = json!({
        "kind": kind,
        "plan_fingerprint": candidates.plan_fingerprint,
        "ordered_candidate_ids": candidates.ordered_ids(),
        "generation": generation,
        "state": state,
    });
    if let (Some(rows), Some(object)) = (rows, value.as_object_mut()) {
        let rows = serde_json::to_value(rows).map_err(|error| error.to_string())?;
        let _ = object.insert("rows".to_owned(), rows);
    }
    write_json(root, STATUS_FILE, &value)
}

fn fail_open_status(
    root: &TemporaryRoot,
    kind: &str,
    candidates: &DialecticCandidateSet,
) -> Result<(), String> {
    let generation = bump_generation(root)?;
    unlink_root_file(root, DIGEST_FILE)?;
    if read_generation(root) == generation {
        write_status(root, kind, candidates, generation, "fallback", None)?;
    }
    Ok(())
}

fn budget_seconds() -> f64 {
    let parsed = std::env::var("LARCH_DIALECTIC_BUDGET_SECONDS")
        .ok()
        .and_then(|value| python_float(&value))
        .unwrap_or(300.0);
    if parsed.is_nan() {
        1.0
    } else {
        parsed.clamp(1.0, 600.0)
    }
}

fn option_text<'a>(decision: &'a DialecticCandidate, option: &str) -> &'a str {
    if option == "option_a" {
        &decision.option_a
    } else {
        &decision.option_b
    }
}

fn other_option(option: &str) -> &'static str {
    if option == "option_a" {
        "option_b"
    } else {
        "option_a"
    }
}

fn strip_attribution(text: &str) -> String {
    RegexBuilder::new(r"\b(?:Anthropic|Sonnet|Opus|Haiku|Cursor|Codex|Claude)\b")
        .case_insensitive(true)
        .build()
        .map_or_else(
            |_error| text.to_owned(),
            |pattern| pattern.replace_all(text, "").into_owned(),
        )
}

fn slot_prompt(decision: &DialecticCandidate, option: &str) -> String {
    format!(
        "You are a read-only /design dialectic clarifier debater. Return a compact steelman for the assigned option only. Do not use tools.\n\nDecision: {}\nOption A: {}\nOption B: {}\nTradeoff: {}\nAssigned option: {option} = {}\n",
        decision.title,
        decision.option_a,
        decision.option_b,
        decision.tradeoff,
        option_text(decision, option),
    )
}

fn steelman<'a>(
    steelmen: &'a BTreeMap<(String, String), String>,
    decision_id: &str,
    option: &str,
) -> Option<&'a str> {
    steelmen
        .get(&(decision_id.to_owned(), option.to_owned()))
        .map(String::as_str)
}

fn ballot_text(
    candidates: &DialecticCandidateSet,
    steelmen: &BTreeMap<(String, String), String>,
) -> String {
    let mut lines = vec![
        "You are a judge on a three-agent dialectic clarifier panel.".to_owned(),
        "Vote THESIS or ANTI_THESIS for each DECISION_N.".to_owned(),
        String::new(),
    ];
    for (index, decision) in candidates.decisions.iter().enumerate() {
        let chosen = decision.drafter_pick.as_str();
        let alternative = other_option(chosen);
        let first_role = if index % 2 == 0 {
            "THESIS"
        } else {
            "ANTI_THESIS"
        };
        let second_role = if first_role == "THESIS" {
            "ANTI_THESIS"
        } else {
            "THESIS"
        };
        let role_option = |role: &str| {
            if role == "THESIS" {
                chosen
            } else {
                alternative
            }
        };
        lines.extend([
            format!("DECISION_{}: {}", index + 1, decision.id),
            format!("Title: {}", decision.title),
            format!(
                "THESIS means current-plan choice: {}",
                option_text(decision, chosen)
            ),
            format!(
                "ANTI_THESIS means alternative: {}",
                option_text(decision, alternative)
            ),
            format!(
                "Defense A ({first_role}): {}",
                strip_attribution(
                    steelman(steelmen, &decision.id, role_option(first_role))
                        .unwrap_or("(no defense)")
                )
            ),
            format!(
                "Defense B ({second_role}): {}",
                strip_attribution(
                    steelman(steelmen, &decision.id, role_option(second_role))
                        .unwrap_or("(no defense)")
                )
            ),
            String::new(),
        ]);
    }
    lines
        .push("Return one line per item: DECISION_N: THESIS|ANTI_THESIS - short reason".to_owned());
    lines.join("\n") + "\n"
}

fn launcher_arguments(
    root: &TemporaryRoot,
    prompt_name: &str,
    output_name: &str,
    timeout: u64,
) -> Vec<OsString> {
    [
        "agent".into(),
        "launch-claude-subprocess".into(),
        "--prompt-file".into(),
        root.path().join(prompt_name).into_os_string(),
        "--output-file".into(),
        root.path().join(output_name).into_os_string(),
        "--timeout".into(),
        timeout.to_string().into(),
        "--timing-task-kind".into(),
        "claude-plan-generic".into(),
        "--allow-root".into(),
        root.path().as_os_str().to_owned(),
    ]
    .into()
}

fn parse_judge_votes(
    text: &str,
    judge: usize,
    candidates: &DialecticCandidateSet,
) -> Vec<(String, String)> {
    let Ok(pattern) = RegexBuilder::new(r"DECISION[_ -]?(\d+)\s*:?\s*(THESIS|ANTI_THESIS)\b")
        .case_insensitive(true)
        .build()
    else {
        return Vec::new();
    };
    let mut seen: BTreeMap<(usize, String), String> = BTreeMap::new();
    let mut conflicted: BTreeSet<(usize, String)> = BTreeSet::new();
    for line in split_text_lines(text) {
        let Some(captures) = pattern.captures(line) else {
            continue;
        };
        let Some(number) = captures
            .get(1)
            .and_then(|value| value.as_str().parse::<usize>().ok())
        else {
            continue;
        };
        let Some(decision) = number
            .checked_sub(1)
            .and_then(|index| candidates.decisions.get(index))
        else {
            continue;
        };
        let key = (judge, decision.id.clone());
        if conflicted.contains(&key) {
            continue;
        }
        let token = captures[2].to_ascii_uppercase();
        if let Some(prior) = seen.get(&key) {
            if prior != &token {
                let _ = conflicted.insert(key.clone());
                let _ = seen.remove(&key);
            }
        } else {
            let _ = seen.insert(key, token);
        }
    }
    seen.into_iter()
        .map(|((_judge, decision), token)| (decision, token))
        .collect()
}

fn escape_untrusted_line(line: &str) -> String {
    let mut cleaned = line.replace("```", "`\u{200b}``");
    let machine = RegexBuilder::new(r"^(?:LARCH_[A-Z0-9_]*|[A-Z][A-Z0-9_]*=.*)$")
        .build()
        .is_ok_and(|pattern| pattern.is_match(&cleaned));
    if machine {
        cleaned.insert(0, '\\');
    }
    format!("> {cleaned}")
}

fn escape_untrusted(text: &str) -> String {
    if text.is_empty() {
        return "> ".to_owned();
    }
    split_text_lines(text)
        .into_iter()
        .map(escape_untrusted_line)
        .collect::<Vec<_>>()
        .join("\n")
}

fn sanitize_display_field(text: &str) -> String {
    let mut cleaned = split_text_lines(text).join(" ");
    cleaned = trim_python_whitespace(&cleaned).replace("```", "`\u{200b}``");
    let machine = RegexBuilder::new(r"^(?:LARCH_[A-Z0-9_]*|[A-Z][A-Z0-9_]*=.*)$")
        .build()
        .is_ok_and(|pattern| pattern.is_match(&cleaned));
    if machine {
        cleaned.insert(0, '\\');
    }
    cleaned
}

fn digest_from_rows(rows: &[DigestRow]) -> String {
    let mut lines = vec![
        "## Dialectic Clarifier (advisory, untrusted)".to_owned(),
        String::new(),
        "This digest is display-only. Approve final design keeps the current plan. Use Discuss further to change it.".to_owned(),
    ];
    for row in rows {
        lines.extend([
            String::new(),
            format!("### Decision: {}", sanitize_display_field(&row.title)),
            format!(
                "- **Candidate id**: `{}`",
                sanitize_display_field(&row.decision_id)
            ),
            format!(
                "- **Drafter pick**: {}",
                sanitize_display_field(&row.drafter_pick)
            ),
            format!(
                "- **Panel lean (advisory)**: {}",
                sanitize_display_field(&row.panel_lean)
            ),
            format!(
                "- **Disposition**: {}",
                sanitize_display_field(&row.disposition)
            ),
            format!(
                "- **Vote tally**: THESIS={} ANTI_THESIS={}",
                row.thesis_votes, row.anti_thesis_votes
            ),
            "- **Option A steelman**:".to_owned(),
            escape_untrusted(&row.option_a_steelman),
            "- **Option B steelman**:".to_owned(),
            escape_untrusted(&row.option_b_steelman),
            "- **Panel rationale (advisory)**:".to_owned(),
            escape_untrusted(&row.rationale),
            "- **Operator note**: Approve keeps current plan; Discuss further to change it."
                .to_owned(),
        ]);
    }
    lines.join("\n").trim_end().to_owned() + "\n"
}

#[allow(clippy::too_many_lines)] // Debate stages share one generation-checked transaction.
fn run_debate(
    root: &TemporaryRoot,
    candidates: &DialecticCandidateSet,
    kind: &str,
    generation: i64,
    effects: &dyn DebateEffects,
) -> Result<DebateResult, String> {
    let budget = budget_seconds();
    let deadline = Instant::now() + Duration::from_secs_f64(budget);
    root.ensure_directory(".dialectic-prompts")
        .map_err(|error| error.to_string())?;
    let timeout = Duration::from_secs_f64((budget / 2.0).min(120.0))
        .as_secs()
        .max(1);
    let mut slots = Vec::new();
    for decision in &candidates.decisions {
        for option in ["option_a", "option_b"] {
            let name = format!("debater-{}-{option}", decision.id);
            let prompt_name = format!(".dialectic-prompts/{name}.txt");
            let output_name = format!("dialectic-{name}.txt");
            write_root_text(root, &prompt_name, &slot_prompt(decision, option))?;
            slots.push(Slot {
                name,
                output_name: output_name.clone(),
                arguments: launcher_arguments(root, &prompt_name, &output_name, timeout),
            });
        }
    }
    let (debater_outputs, debaters_ok) = effects.run_slots(root, &slots, deadline);
    if !debaters_ok {
        fail_open_status(root, kind, candidates)?;
        return Ok(DebateResult {
            text: "Dialectic clarifier exceeded its debater budget; continuing without blocking Gate C.".to_owned(),
            ok: false,
            rows: Vec::new(),
        });
    }
    let mut steelmen = BTreeMap::new();
    for decision in &candidates.decisions {
        for option in ["option_a", "option_b"] {
            let name = format!("debater-{}-{option}", decision.id);
            let text = debater_outputs.get(&name).map_or_else(
                || {
                    format!(
                        "No complete steelman was produced for {}.",
                        option_text(decision, option)
                    )
                },
                |text| strip_attribution(text),
            );
            let _ = steelmen.insert((decision.id.clone(), option.to_owned()), text);
        }
    }
    let ballot = ballot_text(candidates, &steelmen);
    write_root_text(root, BALLOT_FILE, &ballot)?;
    let mut judge_slots = Vec::new();
    for judge in 1..=JUDGE_COUNT {
        let name = format!("judge-{judge}");
        let prompt_name = format!(".dialectic-prompts/{name}.txt");
        let output_name = format!("dialectic-{name}.txt");
        write_root_text(root, &prompt_name, &ballot)?;
        judge_slots.push(Slot {
            name,
            output_name: output_name.clone(),
            arguments: launcher_arguments(root, &prompt_name, &output_name, timeout),
        });
    }
    let (judge_outputs, judges_ok) = effects.run_slots(root, &judge_slots, deadline);
    if !judges_ok {
        fail_open_status(root, kind, candidates)?;
        return Ok(DebateResult {
            text:
                "Dialectic clarifier exceeded its judge budget; continuing without blocking Gate C."
                    .to_owned(),
            ok: false,
            rows: Vec::new(),
        });
    }
    let mut votes = Vec::new();
    for judge in 1..=JUDGE_COUNT {
        votes.extend(parse_judge_votes(
            judge_outputs
                .get(&format!("judge-{judge}"))
                .map_or("", String::as_str),
            judge,
            candidates,
        ));
    }
    let mut rows = Vec::new();
    for decision in &candidates.decisions {
        let thesis_votes = votes
            .iter()
            .filter(|(id, token)| id == &decision.id && token == "THESIS")
            .count();
        let anti_thesis_votes = votes
            .iter()
            .filter(|(id, token)| id == &decision.id && token == "ANTI_THESIS")
            .count();
        let chosen = decision.drafter_pick.as_str();
        let alternative = other_option(chosen);
        let (lean, disposition, rationale) = if thesis_votes + anti_thesis_votes == 0 {
            (
                chosen,
                "fallback-to-synthesis",
                "Judge output was malformed or absent, so the current plan remains the advisory fallback.",
            )
        } else if anti_thesis_votes >= VOTE_THRESHOLD {
            (
                alternative,
                "voted",
                "At least two judges preferred the alternative side.",
            )
        } else if thesis_votes >= VOTE_THRESHOLD {
            (
                chosen,
                "voted",
                "At least two judges preferred the current-plan side.",
            )
        } else {
            (
                chosen,
                "fallback-to-synthesis",
                "The judge panel did not reach a threshold, so the current plan remains the advisory fallback.",
            )
        };
        rows.push(DigestRow {
            decision_id: decision.id.clone(),
            title: decision.title.clone(),
            option_a: decision.option_a.clone(),
            option_b: decision.option_b.clone(),
            option_a_steelman: steelman(&steelmen, &decision.id, "option_a")
                .unwrap_or_default()
                .to_owned(),
            option_b_steelman: steelman(&steelmen, &decision.id, "option_b")
                .unwrap_or_default()
                .to_owned(),
            drafter_pick: format!("{chosen} ({})", option_text(decision, chosen)),
            panel_lean: format!("{lean} ({})", option_text(decision, lean)),
            rationale: rationale.to_owned(),
            disposition: disposition.to_owned(),
            thesis_votes,
            anti_thesis_votes,
        });
    }
    let digest = digest_from_rows(&rows);
    if read_generation(root) != generation {
        return Ok(DebateResult {
            text:
                "Dialectic clarifier generation changed before digest write; stale output ignored."
                    .to_owned(),
            ok: false,
            rows: Vec::new(),
        });
    }
    write_root_text(root, DIGEST_FILE, &digest)?;
    write_status(root, kind, candidates, generation, "complete", Some(&rows))?;
    Ok(DebateResult {
        text: digest,
        ok: true,
        rows,
    })
}

const fn manual_shape_help() -> &'static str {
    "Use Other as `debate <decision>: <option A> vs <option B>` or `debate <candidate-id>` when current candidates are fingerprint-valid."
}

fn infer_manual_drafter_pick(
    root: &TemporaryRoot,
    title: &str,
    option_a: &str,
    option_b: &str,
) -> Result<String, String> {
    if let Ok(fingerprint) = plan_fingerprint(root)
        && let Some(auto) = candidate_set(root, AUTO_CANDIDATES, &fingerprint)
    {
        let slug = dialectic_slugify(title, "manual-decision");
        for decision in auto.decisions {
            if decision.id == slug || decision.title.trim().eq_ignore_ascii_case(title.trim()) {
                return Ok(decision.drafter_pick);
            }
            if (decision.option_a == option_a && decision.option_b == option_b)
                || (decision.option_a == option_b && decision.option_b == option_a)
            {
                return Ok(match decision.drafter_pick.as_str() {
                    "option_a" if decision.option_a == option_a => "option_a",
                    "option_a" => "option_b",
                    "option_b" if decision.option_b == option_b => "option_b",
                    _ => "option_a",
                }
                .to_owned());
            }
        }
    }
    let plan = read_root_lossy(root, "plan.txt").unwrap_or_default();
    infer_dialectic_plan_choice(&plan, option_a, option_b)
        .map(str::to_owned)
        .map_err(|error| {
            format!(
                "Cannot infer which option matches the current plan from this free-form request ({error}). {}",
                manual_shape_help()
            )
        })
}

fn manual_candidates_from_request(
    root: &TemporaryRoot,
    request: &str,
) -> Result<DialecticCandidateSet, String> {
    let fingerprint = plan_fingerprint(root)?;
    let text = trim_python_whitespace(request);
    let id_pattern = RegexBuilder::new(r"^debate(?:-this)?\s+([A-Za-z0-9_.:-]+)$")
        .case_insensitive(true)
        .dot_matches_new_line(true)
        .build()
        .map_err(|error| error.to_string())?;
    if let Some(captures) = id_pattern.captures(text) {
        let Some(auto) = candidate_set(root, AUTO_CANDIDATES, &fingerprint) else {
            return Err(manual_shape_help().to_owned());
        };
        let ident = &captures[1];
        if let Some(decision) = auto
            .decisions
            .into_iter()
            .find(|decision| decision.id == ident)
        {
            return Ok(DialecticCandidateSet {
                plan_fingerprint: fingerprint,
                decisions: vec![decision],
            });
        }
        return Err(manual_shape_help().to_owned());
    }
    let shape = RegexBuilder::new(r"^debate(?:-this)?\s+(.+?)\s*:\s*(.+?)\s+vs\s+(.+?)\s*$")
        .case_insensitive(true)
        .dot_matches_new_line(true)
        .build()
        .map_err(|error| error.to_string())?;
    let Some(captures) = shape.captures(text) else {
        return Err(manual_shape_help().to_owned());
    };
    let title = trim_python_whitespace(&captures[1]);
    let option_a = trim_python_whitespace(&captures[2]);
    let option_b = trim_python_whitespace(&captures[3]);
    let drafter_pick = infer_manual_drafter_pick(root, title, option_a, option_b)?;
    let payload = json!({
        "plan_fingerprint": fingerprint,
        "decisions": [{
            "id": dialectic_slugify(title, "manual-decision"),
            "title": title,
            "option_a": option_a,
            "option_b": option_b,
            "tradeoff": "Manual Gate C debate request.",
            "drafter_pick": drafter_pick,
            "why_this_matters": "The operator requested on-demand dialectic clarification at Gate C.",
        }],
    });
    parse_dialectic_candidates(
        &serde_json::to_string(&payload).map_err(|error| error.to_string())?,
        Some(&fingerprint),
        true,
    )
    .map_err(|error| error.to_string())
}

fn manual_covers_auto(manual: &DialecticCandidateSet, auto: &DialecticCandidateSet) -> bool {
    let manual_ids = manual.ordered_ids().into_iter().collect::<BTreeSet<_>>();
    auto.ordered_ids()
        .into_iter()
        .all(|candidate| manual_ids.contains(candidate))
}

fn append_debate_warning(root: &TemporaryRoot, message: &str) -> Result<(), String> {
    append_execution_issue(
        &root.path().join("execution-issues.md"),
        "Warnings",
        &format!("- **Dialectic clarifier warning**: {message}"),
    )
}

fn emit_debate_result(root: &TemporaryRoot, result: &DebateResult) -> Result<(), String> {
    if result.ok {
        print!("{}", result.text);
    } else {
        append_debate_warning(root, &result.text)?;
        println!("**⚠ Dialectic clarifier skipped:** {}", result.text);
    }
    let _ = &result.rows;
    Ok(())
}

fn run_gatec(
    root: &TemporaryRoot,
    probe_only: bool,
    effects: &dyn DebateEffects,
) -> Result<(), String> {
    let fingerprint = plan_fingerprint(root).ok();
    let candidates = fingerprint
        .as_deref()
        .and_then(|current| candidate_set(root, AUTO_CANDIDATES, current));
    let manual = fingerprint
        .as_deref()
        .and_then(|current| candidate_set(root, MANUAL_CANDIDATES, current));
    let manual_cached = manual
        .as_ref()
        .is_some_and(|manual| cached_digest_valid(root, manual, "manual"));
    let auto_cached = candidates
        .as_ref()
        .is_some_and(|auto| cached_digest_valid(root, auto, "auto"));
    let manual_authoritative = manual_cached
        && manual.as_ref().is_some_and(|manual| {
            candidates
                .as_ref()
                .is_none_or(|auto| auto_cached || manual_covers_auto(manual, auto))
        });
    let required = candidates.is_some()
        && !skip_approve_requested(root)
        && !auto_cached
        && !manual_authoritative;
    if probe_only {
        println!("DIALECTIC_GATEC_DEBATE_REQUIRED={required}");
        return Ok(());
    }
    if manual_authoritative {
        print!("{}", read_root_lossy(root, DIGEST_FILE)?);
        return Ok(());
    }
    let Some(candidates) = candidates else {
        if [
            AUTO_CANDIDATES,
            MANUAL_CANDIDATES,
            STATUS_FILE,
            DIGEST_FILE,
            MANUAL_REQUEST,
        ]
        .into_iter()
        .any(|name| artifact_present(root, name))
        {
            let _ = clear_stale(root);
        }
        return Ok(());
    };
    if skip_approve_requested(root) || auto_cached {
        if auto_cached {
            print!("{}", read_root_lossy(root, DIGEST_FILE)?);
        }
        return Ok(());
    }
    let generation = bump_generation(root)?;
    write_status(root, "auto", &candidates, generation, "running", None)?;
    emit_debate_result(
        root,
        &run_debate(root, &candidates, "auto", generation, effects)?,
    )
}

/// Run the optional, fail-open Gate C dialectic clarifier.
pub fn gatec(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        GATEC_PROGRAM,
        GATEC_USAGE,
        GATEC_HELP,
        &["--design-tmpdir"],
        &["--probe-only"],
        &["--design-tmpdir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let root = match resolve_design_root(parsed.value("--design-tmpdir").expect("required option"))
    {
        Ok(root) => root,
        Err(error) => {
            eprintln!("dialectic-gatec: {error}");
            return ExitCode::from(2);
        }
    };
    let probe_only = parsed.flag("--probe-only");
    match run_gatec(&root, probe_only, &LiveDebateEffects) {
        Ok(()) => {
            if !probe_only {
                let _ = atomic_write_utf8_in(
                    &root,
                    &root.path().join(COMPLETED_GATEC),
                    "",
                    true,
                    0o600,
                );
            }
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("dialectic-gatec: {error}");
            ExitCode::FAILURE
        }
    }
}

fn run_manual(
    root: &TemporaryRoot,
    candidates: &DialecticCandidateSet,
    effects: &dyn DebateEffects,
) -> Result<(), String> {
    write_root_text(
        root,
        MANUAL_CANDIDATES,
        &render_dialectic_candidates_pretty(candidates).map_err(|error| error.to_string())?,
    )?;
    let generation = bump_generation(root)?;
    write_status(root, "manual", candidates, generation, "running", None)?;
    emit_debate_result(
        root,
        &run_debate(root, candidates, "manual", generation, effects)?,
    )
}

/// Run one operator-requested Gate C dialectic debate.
pub fn manual(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        MANUAL_PROGRAM,
        MANUAL_USAGE,
        MANUAL_HELP,
        &["--design-tmpdir", "--request-file", "--request"],
        &[],
        &["--design-tmpdir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let root = match resolve_design_root(parsed.value("--design-tmpdir").expect("required option"))
    {
        Ok(root) => root,
        Err(error) => {
            eprintln!("dialectic-manual: {error}");
            return ExitCode::from(2);
        }
    };
    let request = if let Some(path) = parsed
        .value("--request-file")
        .filter(|path| !path.is_empty())
    {
        let path = PathBuf::from(path);
        if !fs::metadata(&path).is_ok_and(|metadata| metadata.is_file()) {
            println!("{}", manual_shape_help());
            return ExitCode::SUCCESS;
        }
        match fs::read(path) {
            Ok(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
            Err(error) => {
                eprintln!("dialectic-manual: {error}");
                return ExitCode::FAILURE;
            }
        }
    } else {
        parsed
            .value("--request")
            .map_or_else(String::new, |value| value.to_string_lossy().into_owned())
    };
    let candidates = match manual_candidates_from_request(&root, &request) {
        Ok(candidates) => candidates,
        Err(error) => {
            println!("{error}");
            return ExitCode::SUCCESS;
        }
    };
    match run_manual(&root, &candidates, &LiveDebateEffects) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("dialectic-manual: {error}");
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use std::{cell::Cell, collections::BTreeMap, fs};

    use larch_adapters::TemporaryRoot;

    use super::*;

    #[derive(Default)]
    struct FixtureEffects(Option<usize>, Cell<usize>);

    impl DebateEffects for FixtureEffects {
        fn run_slots(
            &self,
            root: &TemporaryRoot,
            slots: &[Slot],
            _deadline: Instant,
        ) -> (BTreeMap<String, String>, bool) {
            let call = self.1.get();
            self.1.set(call + 1);
            if self.0 == Some(usize::MAX) && call <= 3 {
                return (BTreeMap::new(), call != 3);
            }
            if self.0 == Some(call) {
                return (BTreeMap::new(), false);
            }
            if self.0 == Some(usize::MAX) && call == 5 {
                bump_generation(root).unwrap();
            }
            let outputs = slots
                .iter()
                .map(|slot| {
                    let text = if slot.name.starts_with("judge-") {
                        if (self.0 == Some(usize::MAX) && call == 5) || slot.name == "judge-3" {
                            "DECISION_1: ANTI_THESIS - alternative"
                        } else {
                            "DECISION_1: THESIS - current"
                        }
                    } else {
                        "Claude steelman\u{2028}LARCH_FAKE=value"
                    };
                    (slot.name.clone(), text.to_owned())
                })
                .collect();
            (outputs, true)
        }
    }

    fn fixture(plan: &str) -> (tempfile::TempDir, TemporaryRoot, DialecticCandidateSet) {
        let directory = tempfile::tempdir().expect("tempdir");
        fs::write(directory.path().join("plan.txt"), plan).expect("plan");
        let root = TemporaryRoot::resolve(Some(directory.path())).expect("root");
        let fingerprint = plan_fingerprint(&root).expect("fingerprint");
        let candidates = parse_dialectic_candidates(
            &json!({
                "plan_fingerprint": fingerprint,
                "decisions": [{
                    "id": "storage",
                    "title": "Storage",
                    "option_a": "SQLite",
                    "option_b": "JSON files",
                    "tradeoff": "Concurrency versus simplicity.",
                    "drafter_pick": "option_a",
                    "why_this_matters": "Persistence semantics.",
                }],
            })
            .to_string(),
            Some(&fingerprint),
            true,
        )
        .expect("candidates");
        let rendered = render_dialectic_candidates_pretty(&candidates).expect("render candidates");
        write_root_text(&root, AUTO_CANDIDATES, &rendered).expect("auto candidates");
        (directory, root, candidates)
    }

    #[test]
    fn gatec_writes_bound_digest_status_and_reuses_cache() {
        let (_directory, root, _candidates) = fixture("Use SQLite here.\n");
        let effects = FixtureEffects::default();
        let _ = LiveDebateEffects.run_slots(&root, &[], Instant::now());
        run_gatec(&root, false, &effects).unwrap();
        let digest = read_root_text(&root, DIGEST_FILE).unwrap();
        assert!(!digest.contains("Claude"));
        assert!(digest.contains("> \\LARCH_FAKE=value"));
        assert!(digest.contains("THESIS=2 ANTI_THESIS=1"));
        assert!(
            read_root_text(&root, BALLOT_FILE)
                .unwrap()
                .contains("Defense A (THESIS)")
        );
        assert_eq!(status_from_file(&root).unwrap().state, "complete");
        run_gatec(&root, false, &effects).unwrap();
        run_gatec(&root, true, &effects).unwrap();
        assert_eq!(effects.1.get(), 2);
    }

    #[test]
    fn debate_timeout_invalidates_inflight_generation_and_drops_digest() {
        let (_directory, root, candidates) = fixture("Use SQLite here.\n");
        write_root_text(&root, DIGEST_FILE, "stale\n").unwrap();
        let generation = bump_generation(&root).unwrap();
        let effects = FixtureEffects(Some(0), Cell::default());
        let result = run_debate(&root, &candidates, "auto", generation, &effects).unwrap();
        assert!(emit_debate_result(&root, &result).is_ok() && !result.ok);
        assert_eq!(read_generation(&root), generation + 1);
        assert_eq!(status_from_file(&root).unwrap().state, "fallback");
        assert!(!artifact_present(&root, DIGEST_FILE));
        let empty = FixtureEffects(Some(usize::MAX), Cell::default());
        let debate =
            |generation| run_debate(&root, &candidates, "auto", generation, &empty).unwrap();
        assert!(debate(generation + 1).ok);
        assert!(!debate(generation + 1).ok);
        assert!(!debate(generation + 2).ok);
        unlink_root_file(&root, AUTO_CANDIDATES).unwrap();
        run_gatec(&root, false, &effects).unwrap();
        assert!(!artifact_present(&root, STATUS_FILE));
    }

    #[test]
    fn manual_request_infers_the_plan_side_and_vote_conflicts_are_discarded() {
        let (_directory, root, candidates) = fixture("Use SQLite here.\n");
        let manual =
            manual_candidates_from_request(&root, "debate Storage choice: SQLite vs JSON files")
                .unwrap();
        assert_eq!(manual.decisions[0].drafter_pick, "option_a");
        assert_eq!(manual.decisions[0].id, "storage-choice");
        let by_id = manual_candidates_from_request(&root, "debate storage").unwrap();
        assert_eq!(by_id.decisions[0].id, "storage");
        let effects = FixtureEffects::default();
        run_manual(&root, &candidates, &effects).unwrap();
        assert!(run_gatec(&root, false, &effects).is_ok());
        let conflict = "DECISION_1: THESIS\nDECISION_1: ANTI_THESIS";
        assert!(parse_judge_votes(conflict, 1, &candidates).is_empty());
    }
}
