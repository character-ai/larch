//! Rust owner for `/validate-merged` prepare, ingest, report, and durable state.
//!
//! Finder and refuter JSONL stay untrusted agent output: this module never
//! executes those bytes. Durable publication goes through a locked, symlink-safe
//! replacement of one compact marker.

use std::{
    collections::BTreeMap,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt as _;

use chrono::Utc;
use larch_core::private_atomic_write;
use serde_json::{Map, Value, json};
use sha2::{Digest as _, Sha256};

use crate::{
    analysis_state,
    analyze_bugs_commands::{self, SweepCandidateData, exact_keys},
    analyze_bugs_sweep::{
        self, emit_rows, sweep_ingest_finder, sweep_ingest_refuter, sweep_prepare,
        sweep_state_path, write_sweep_state,
    },
    argparse_compat::{
        ParsedCommandLine, missing, parse_with_flags, split_inline_option, unrecognized_arguments,
        usage_error,
    },
    github_repository_resolution::ambient_repo,
};

const PREPARE_PROGRAM: &str = "python/cli.py validate-merged prepare";
const PREPARE_USAGE: &str = "usage: python/cli.py validate-merged prepare [-h] [--root ROOT] --run-dir\n                                             RUN_DIR [--repo REPO]\n                                             [--max-merges MAX_MERGES]";
const PREPARE_HELP: &str = "usage: python/cli.py validate-merged prepare [-h] [--root ROOT] --run-dir\n                                             RUN_DIR [--repo REPO]\n                                             [--max-merges MAX_MERGES]\n\noptions:\n  -h, --help            show this help message and exit\n  --root ROOT\n  --run-dir RUN_DIR\n  --repo REPO\n  --max-merges MAX_MERGES\n";
const FINDER_PROGRAM: &str = "python/cli.py validate-merged ingest-finder";
const FINDER_USAGE: &str =
    "usage: python/cli.py validate-merged ingest-finder [-h] --run-dir RUN_DIR";
const FINDER_HELP: &str = "usage: python/cli.py validate-merged ingest-finder [-h] --run-dir RUN_DIR\n\noptions:\n  -h, --help         show this help message and exit\n  --run-dir RUN_DIR\n";
const REFUTER_PROGRAM: &str = "python/cli.py validate-merged ingest-refuter";
const REFUTER_USAGE: &str =
    "usage: python/cli.py validate-merged ingest-refuter [-h] --run-dir RUN_DIR";
const REFUTER_HELP: &str = "usage: python/cli.py validate-merged ingest-refuter [-h] --run-dir RUN_DIR\n\noptions:\n  -h, --help         show this help message and exit\n  --run-dir RUN_DIR\n";
const REPORT_PROGRAM: &str = "python/cli.py validate-merged report";
const REPORT_USAGE: &str = "usage: python/cli.py validate-merged report [-h] [--root ROOT] --run-dir\n                                            RUN_DIR [--repo REPO]\n                                            --state-output STATE_OUTPUT";
const REPORT_HELP: &str = "usage: python/cli.py validate-merged report [-h] [--root ROOT] --run-dir\n                                            RUN_DIR [--repo REPO]\n                                            --state-output STATE_OUTPUT\n\noptions:\n  -h, --help            show this help message and exit\n  --root ROOT\n  --run-dir RUN_DIR\n  --repo REPO\n  --state-output STATE_OUTPUT\n";
const WRITE_PROGRAM: &str = "python/cli.py validate-merged write-state";
const WRITE_USAGE: &str = "usage: python/cli.py validate-merged write-state [-h] [--root ROOT] --repo\n                                                 REPO --state-input\n                                                 STATE_INPUT\n                                                 [--expected-digest EXPECTED_DIGEST]";
const WRITE_HELP: &str = "usage: python/cli.py validate-merged write-state [-h] [--root ROOT] --repo\n                                                 REPO --state-input\n                                                 STATE_INPUT\n                                                 [--expected-digest EXPECTED_DIGEST]\n\noptions:\n  -h, --help            show this help message and exit\n  --root ROOT\n  --repo REPO\n  --state-input STATE_INPUT\n  --expected-digest EXPECTED_DIGEST\n";

const STATE_SCHEMA_VERSION: u64 = 1;
const STATE_RELPATH: &str = "validate-merged/state.json";
const DEFAULT_MAX_MERGES: i64 = 20;
const MAX_JSON_BYTES: u64 = 64 * 1024 * 1024;
const SHA256_HEX_LENGTH: usize = 64;

#[derive(Clone, Debug, Eq, PartialEq)]
struct UnresolvedCandidate {
    merge_sha: String,
    file: String,
    symbol: String,
    description: String,
    severity: String,
    confidence: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ValidateMergedState {
    schema_version: u64,
    repo: String,
    last_successful_tip: String,
    completed_at: String,
    merge_watermark: String,
    pending_merge_shas: Vec<String>,
    unresolved_candidates: Vec<UnresolvedCandidate>,
}

/// Dispatch `validate-merged prepare`.
#[must_use]
pub fn prepare(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--root", "--run-dir", "--repo", "--max-merges"];
    let parsed = match parse_command(
        arguments,
        OPTIONS,
        PREPARE_USAGE,
        PREPARE_PROGRAM,
        PREPARE_HELP,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let run_dir = match required_options(&parsed, &["--run-dir"], PREPARE_USAGE, PREPARE_PROGRAM) {
        Ok(values) => PathBuf::from(&values[0]),
        Err(code) => return code,
    };
    let max_merges = match integer_option(
        &parsed,
        "--max-merges",
        DEFAULT_MAX_MERGES,
        PREPARE_USAGE,
        PREPARE_PROGRAM,
    ) {
        Ok(value) => value,
        Err(code) => return code,
    };
    let max_merges = usize::try_from(max_merges).unwrap_or(0);
    if max_merges == 0 {
        return fail("--max-merges must be a positive integer");
    }
    let root = path_option(&parsed, "--root");
    let repo = match resolve_repo(&option_text(&parsed, "--repo")) {
        Ok(repo) => repo,
        Err(error) => return fail(&error),
    };
    match prepare_inner(&root, &run_dir, &repo, max_merges) {
        Ok(rows) => {
            emit_rows(&rows);
            ExitCode::SUCCESS
        }
        Err(error) => fail(&error),
    }
}

/// Dispatch `validate-merged ingest-finder`.
#[must_use]
pub fn ingest_finder(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--run-dir"];
    let parsed = match parse_command(
        arguments,
        OPTIONS,
        FINDER_USAGE,
        FINDER_PROGRAM,
        FINDER_HELP,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let run_dir = match required_options(&parsed, &["--run-dir"], FINDER_USAGE, FINDER_PROGRAM) {
        Ok(values) => PathBuf::from(&values[0]),
        Err(code) => return code,
    };
    match sweep_ingest_finder(&run_dir) {
        Ok(rows) => {
            emit_rows(&rows);
            ExitCode::SUCCESS
        }
        Err(error) => fail(&error),
    }
}

/// Dispatch `validate-merged ingest-refuter`.
#[must_use]
pub fn ingest_refuter(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--run-dir"];
    let parsed = match parse_command(
        arguments,
        OPTIONS,
        REFUTER_USAGE,
        REFUTER_PROGRAM,
        REFUTER_HELP,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let run_dir = match required_options(&parsed, &["--run-dir"], REFUTER_USAGE, REFUTER_PROGRAM) {
        Ok(values) => PathBuf::from(&values[0]),
        Err(code) => return code,
    };
    match sweep_ingest_refuter(&run_dir) {
        Ok(rows) => {
            emit_rows(&rows);
            ExitCode::SUCCESS
        }
        Err(error) => fail(&error),
    }
}

/// Dispatch `validate-merged report`.
#[must_use]
pub fn report(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--root", "--run-dir", "--repo", "--state-output"];
    let parsed = match parse_command(
        arguments,
        OPTIONS,
        REPORT_USAGE,
        REPORT_PROGRAM,
        REPORT_HELP,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let values = match required_options(
        &parsed,
        &["--run-dir", "--state-output"],
        REPORT_USAGE,
        REPORT_PROGRAM,
    ) {
        Ok(values) => values,
        Err(code) => return code,
    };
    let run_dir = PathBuf::from(&values[0]);
    let state_output = PathBuf::from(&values[1]);
    let root = path_option(&parsed, "--root");
    let repo = match resolve_repo(&option_text(&parsed, "--repo")) {
        Ok(repo) => repo,
        Err(error) => return fail(&error),
    };
    match report_inner(&root, &run_dir, &repo, &state_output) {
        Ok((text, rows)) => {
            print!("{text}");
            emit_rows(&rows);
            ExitCode::SUCCESS
        }
        Err(error) => fail(&error),
    }
}

/// Dispatch `validate-merged write-state`.
#[must_use]
pub fn write_state(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--root", "--repo", "--state-input", "--expected-digest"];
    let parsed = match parse_command(arguments, OPTIONS, WRITE_USAGE, WRITE_PROGRAM, WRITE_HELP) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let values = match required_options(
        &parsed,
        &["--repo", "--state-input"],
        WRITE_USAGE,
        WRITE_PROGRAM,
    ) {
        Ok(values) => values,
        Err(code) => return code,
    };
    let repo = values[0].clone();
    let state_input = PathBuf::from(&values[1]);
    let root = path_option(&parsed, "--root");
    let expected = option_text(&parsed, "--expected-digest");
    match write_state_inner(&root, &repo, &state_input, &expected) {
        Ok(rows) => {
            emit_rows(&rows);
            ExitCode::SUCCESS
        }
        Err(error) => fail(&error),
    }
}

fn prepare_inner(
    root: &Path,
    run_dir: &Path,
    repo: &str,
    max_merges: usize,
) -> Result<Vec<(String, String)>, String> {
    let durable_path = analysis_state::marker_path(root, STATE_RELPATH)?;
    let durable = load_state(&durable_path, repo)?;
    analyze_bugs_commands::private_dir(run_dir)?;
    let ledger = run_dir.join("validate-merged-ledger.jsonl");
    if let Some(state) = &durable {
        write_sweep_state(
            &sweep_state_path(&ledger)?,
            &state.merge_watermark,
            &state.completed_at,
            &state.pending_merge_shas,
        )?;
    }
    let mut prepared = sweep_prepare(run_dir, &ledger, repo, max_merges)?;
    let snapshot = analysis_state::read_snapshot(&durable_path)?;
    replace_row(
        &mut prepared.rows,
        "STATE_PATH",
        durable_path.display().to_string(),
    );
    prepared.rows.push((
        "STATE_SOURCE".to_owned(),
        if durable.is_some() {
            "committed".to_owned()
        } else {
            "first-run-48-hours".to_owned()
        },
    ));
    prepared
        .rows
        .push(("STATE_DIGEST".to_owned(), snapshot.digest));
    Ok(prepared.rows)
}

fn report_inner(
    root: &Path,
    run_dir: &Path,
    repo: &str,
    state_output: &Path,
) -> Result<(String, Vec<(String, String)>), String> {
    let artifact = analyze_bugs_commands::load_validated_sweep(run_dir)?
        .ok_or_else(|| "validated merge result is missing".to_owned())?;
    let current = load_state(&analysis_state::marker_path(root, STATE_RELPATH)?, repo)?;
    let mut by_identity = BTreeMap::new();
    if let Some(current) = current {
        for item in current.unresolved_candidates {
            by_identity.insert(candidate_key(&item), item);
        }
    }
    for item in artifact.candidates.into_iter().map(candidate_from_sweep) {
        by_identity.insert(candidate_key(&item), item);
    }
    let unresolved = by_identity.into_values().collect::<Vec<_>>();
    let state = ValidateMergedState {
        schema_version: STATE_SCHEMA_VERSION,
        repo: repo.to_owned(),
        last_successful_tip: artifact.pinned_tip.clone(),
        completed_at: now_utc(),
        merge_watermark: artifact.pinned_tip,
        pending_merge_shas: artifact.pending_shas,
        unresolved_candidates: unresolved,
    };
    let table = if state.unresolved_candidates.is_empty() {
        "None.".to_owned()
    } else {
        let mut rows = vec![vec![
            "Merge".to_owned(),
            "File".to_owned(),
            "Symbol".to_owned(),
            "Severity".to_owned(),
            "Confidence".to_owned(),
            "Description".to_owned(),
        ]];
        rows.extend(state.unresolved_candidates.iter().map(|item| {
            vec![
                analyze_bugs_commands::short_sha(&item.merge_sha),
                item.file.clone(),
                item.symbol.clone(),
                item.severity.clone(),
                item.confidence.clone(),
                item.description.clone(),
            ]
        }));
        analyze_bugs_commands::markdown_table(&rows)
    };
    let text = format!(
        "# Validate merged changes\n\n\
Recent first-parent merges were checked for possible unfiled bugs.\n\n\
## Possible unfiled bugs\n\n\
{table}\n\n\
Selected merges: {}\n\
Pending merges: {}\n\
Unresolved candidates: {}\n\n\
State is ready for publication only after this final report succeeds.\n\n",
        artifact.selected_count,
        state.pending_merge_shas.len(),
        state.unresolved_candidates.len()
    );
    write_state_file(state_output, &state)?;
    Ok((
        text,
        vec![
            (
                "STATE_OUTPUT".to_owned(),
                state_output.display().to_string(),
            ),
            ("STATE_RELPATH".to_owned(), STATE_RELPATH.to_owned()),
        ],
    ))
}

fn write_state_inner(
    root: &Path,
    repo: &str,
    state_input: &Path,
    expected_digest: &str,
) -> Result<Vec<(String, String)>, String> {
    let state =
        load_state(state_input, repo)?.ok_or_else(|| "state input is missing".to_owned())?;
    let target = analysis_state::marker_path(root, STATE_RELPATH)?;
    let expected = if expected_digest.is_empty() {
        analysis_state::read_snapshot(&target)?.digest
    } else {
        expected_digest.to_owned()
    };
    if expected != "missing"
        && (expected.len() != SHA256_HEX_LENGTH
            || expected
                .bytes()
                .any(|byte| !byte.is_ascii_hexdigit() || byte.is_ascii_uppercase()))
    {
        return Err("expected analysis-state digest must be 'missing' or SHA-256".to_owned());
    }
    let payload = serialize_state(&state)?;
    let digest = write_state_locked(&target, payload.as_bytes(), &expected)?;
    Ok(vec![
        ("STATE_RELPATH".to_owned(), STATE_RELPATH.to_owned()),
        ("STATE_PATH".to_owned(), target.display().to_string()),
        ("STATE_DIGEST".to_owned(), digest),
    ])
}

fn candidate_from_sweep(item: SweepCandidateData) -> UnresolvedCandidate {
    UnresolvedCandidate {
        merge_sha: item.merge_sha,
        file: item.file,
        symbol: item.symbol,
        description: item.description,
        severity: item.severity,
        confidence: item.confidence,
    }
}

fn candidate_key(item: &UnresolvedCandidate) -> (String, String, String, String) {
    (
        item.merge_sha.clone(),
        item.file.clone(),
        item.symbol.clone(),
        item.description.clone(),
    )
}

#[allow(clippy::too_many_lines)] // Every committed marker field is checked before state advances.
fn load_state(path: &Path, repo: &str) -> Result<Option<ValidateMergedState>, String> {
    if !path.exists() {
        return Ok(None);
    }
    let metadata = fs::metadata(path).map_err(|error| {
        format!(
            "malformed committed state marker: {}: {error}",
            path.display()
        )
    })?;
    if metadata.len() > MAX_JSON_BYTES {
        return Err(format!(
            "malformed committed state marker: {}: input exceeds {MAX_JSON_BYTES} bytes",
            path.display()
        ));
    }
    let value: Value = serde_json::from_slice(&fs::read(path).map_err(|error| {
        format!(
            "malformed committed state marker: {}: {error}",
            path.display()
        )
    })?)
    .map_err(|error| {
        format!(
            "malformed committed state marker: {}: {error}",
            path.display()
        )
    })?;
    let object = value
        .as_object()
        .ok_or_else(|| "committed state marker has unexpected keys".to_owned())?;
    if !exact_keys(
        object,
        &[
            "completed_at",
            "last_successful_tip",
            "merge_watermark",
            "pending_merge_shas",
            "repo",
            "schema_version",
            "unresolved_candidates",
        ],
    ) {
        return Err("committed state marker has unexpected keys".to_owned());
    }
    let schema_version = object
        .get("schema_version")
        .and_then(Value::as_u64)
        .ok_or_else(|| {
            "committed state marker has an unsupported schema or foreign repository".to_owned()
        })?;
    let stored_repo = object.get("repo").and_then(Value::as_str).ok_or_else(|| {
        "committed state marker has an unsupported schema or foreign repository".to_owned()
    })?;
    if schema_version != STATE_SCHEMA_VERSION || stored_repo != repo {
        return Err(
            "committed state marker has an unsupported schema or foreign repository".to_owned(),
        );
    }
    let pending_raw = object
        .get("pending_merge_shas")
        .and_then(Value::as_array)
        .ok_or_else(|| "committed state marker has malformed arrays".to_owned())?;
    let candidates_raw = object
        .get("unresolved_candidates")
        .and_then(Value::as_array)
        .ok_or_else(|| "committed state marker has malformed arrays".to_owned())?;
    let mut pending = Vec::new();
    let mut seen = std::collections::BTreeSet::new();
    for item in pending_raw {
        let sha = analyze_bugs_sweep::require_full_sha(
            item.as_str().unwrap_or_default(),
            "pending merge SHA",
        )?;
        if !seen.insert(sha.clone()) {
            return Err("committed state marker has duplicate pending merge SHAs".to_owned());
        }
        pending.push(sha);
    }
    let mut candidates = Vec::new();
    for item in candidates_raw {
        candidates.push(candidate_from_raw(item)?);
    }
    Ok(Some(ValidateMergedState {
        schema_version: STATE_SCHEMA_VERSION,
        repo: repo.to_owned(),
        last_successful_tip: analyze_bugs_sweep::require_full_sha(
            object
                .get("last_successful_tip")
                .and_then(Value::as_str)
                .unwrap_or_default(),
            "last_successful_tip",
        )?,
        completed_at: timestamp(
            object
                .get("completed_at")
                .and_then(Value::as_str)
                .unwrap_or_default(),
            "completed_at",
        )?,
        merge_watermark: analyze_bugs_sweep::require_full_sha(
            object
                .get("merge_watermark")
                .and_then(Value::as_str)
                .unwrap_or_default(),
            "merge_watermark",
        )?,
        pending_merge_shas: pending,
        unresolved_candidates: candidates,
    }))
}

fn candidate_from_raw(raw: &Value) -> Result<UnresolvedCandidate, String> {
    let object = raw
        .as_object()
        .ok_or_else(|| "unresolved candidate has unexpected fields".to_owned())?;
    if !exact_keys(
        object,
        &[
            "confidence",
            "description",
            "file",
            "merge_sha",
            "severity",
            "symbol",
        ],
    ) {
        return Err("unresolved candidate has unexpected fields".to_owned());
    }
    let merge_sha = analyze_bugs_sweep::require_full_sha(
        object
            .get("merge_sha")
            .and_then(Value::as_str)
            .unwrap_or_default(),
        "candidate merge_sha",
    )?;
    let file = nonempty_string(object, "file")?;
    let symbol = nonempty_string(object, "symbol")?;
    let description = nonempty_string(object, "description")?;
    let severity = nonempty_string(object, "severity")?;
    let confidence = nonempty_string(object, "confidence")?;
    Ok(UnresolvedCandidate {
        merge_sha,
        file,
        symbol,
        description,
        severity,
        confidence,
    })
}

fn nonempty_string(object: &Map<String, Value>, field: &str) -> Result<String, String> {
    object
        .get(field)
        .and_then(Value::as_str)
        .filter(|value| !value.is_empty())
        .map(str::to_owned)
        .ok_or_else(|| "unresolved candidate fields must be non-empty strings".to_owned())
}

fn write_state_file(path: &Path, state: &ValidateMergedState) -> Result<(), String> {
    if state.schema_version != STATE_SCHEMA_VERSION {
        return Err("refusing to write an unsupported state schema".to_owned());
    }
    let mut seen = std::collections::BTreeSet::new();
    for sha in &state.pending_merge_shas {
        if !seen.insert(sha) {
            return Err("refusing to write duplicate pending merge SHAs".to_owned());
        }
    }
    analyze_bugs_commands::private_write(path, &serialize_state(state)?)
}

fn serialize_state(state: &ValidateMergedState) -> Result<String, String> {
    let value = json!({
        "completed_at": state.completed_at,
        "last_successful_tip": state.last_successful_tip,
        "merge_watermark": state.merge_watermark,
        "pending_merge_shas": state.pending_merge_shas,
        "repo": state.repo,
        "schema_version": state.schema_version,
        "unresolved_candidates": state.unresolved_candidates.iter().map(|item| json!({
            "confidence": item.confidence,
            "description": item.description,
            "file": item.file,
            "merge_sha": item.merge_sha,
            "severity": item.severity,
            "symbol": item.symbol,
        })).collect::<Vec<_>>(),
    });
    let mut text = serde_json::to_string_pretty(&value).map_err(|error| error.to_string())?;
    text.push('\n');
    Ok(text)
}

fn write_state_locked(path: &Path, data: &[u8], expected_digest: &str) -> Result<String, String> {
    let locked = analysis_state::lock_existing(path, expected_digest)?;
    let text = std::str::from_utf8(data).map_err(|error| error.to_string())?;
    private_atomic_write(path, text, &locked.parent).map_err(|error| error.to_string())?;
    #[cfg(unix)]
    fs::set_permissions(path, fs::Permissions::from_mode(0o600))
        .map_err(|error| format!("could not write analysis state: {error}"))?;
    Ok(format!("{:x}", Sha256::digest(data)))
}

fn resolve_repo(explicit: &str) -> Result<String, String> {
    if !explicit.is_empty() {
        return Ok(explicit.to_owned());
    }
    ambient_repo().ok_or_else(|| "could not resolve GitHub repo; pass --repo OWNER/REPO".to_owned())
}

fn timestamp(value: &str, label: &str) -> Result<String, String> {
    if !analyze_bugs_sweep::sweep_timestamp(value) {
        return Err(format!(
            "{label} must be an ISO-8601 UTC timestamp ending in Z"
        ));
    }
    Ok(value.to_owned())
}

fn now_utc() -> String {
    Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string()
}

fn replace_row(rows: &mut [(String, String)], key: &str, value: String) {
    if let Some((_, current)) = rows.iter_mut().find(|(name, _)| name == key) {
        *current = value;
    }
}

fn fail(error: &str) -> ExitCode {
    eprintln!("validate-merged: {error}");
    ExitCode::from(2)
}

fn parse_command(
    arguments: &[OsString],
    options: &[&'static str],
    usage: &str,
    program: &str,
    help: &str,
) -> Result<ParsedCommandLine, ExitCode> {
    if let Some(code) = help_explicit_argument(arguments, usage, program) {
        return Err(code);
    }
    if help_requested(arguments) {
        print!("{help}");
        return Err(ExitCode::SUCCESS);
    }
    let parsed = parse_with_flags(arguments, options, &[], 0);
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(usage, program, error, 2));
    }
    if let Some(error) = unrecognized_arguments(arguments, options, &["-h", "--help"]) {
        return Err(usage_error(usage, program, &error, 2));
    }
    Ok(parsed)
}

fn help_requested(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .any(|argument| matches!(argument.to_string_lossy().as_ref(), "-h" | "--help"))
}

fn help_explicit_argument(arguments: &[OsString], usage: &str, program: &str) -> Option<ExitCode> {
    for argument in arguments {
        let text = argument.to_string_lossy();
        let (name, value) = split_inline_option(&text);
        if matches!(name, "-h" | "--help")
            && let Some(value) = value
        {
            return Some(usage_error(
                usage,
                program,
                &format!("argument -h/--help: ignored explicit argument '{value}'"),
                2,
            ));
        }
    }
    None
}

fn required_options(
    parsed: &ParsedCommandLine,
    options: &[&'static str],
    usage: &str,
    program: &str,
) -> Result<Vec<String>, ExitCode> {
    let present = options
        .iter()
        .map(|option| (*option, parsed.value(option).is_some()))
        .collect::<Vec<_>>();
    if present.iter().any(|(_, found)| !*found) {
        return Err(usage_error(usage, program, &missing(&present), 2));
    }
    Ok(options
        .iter()
        .map(|option| option_text(parsed, option))
        .collect())
}

fn integer_option(
    parsed: &ParsedCommandLine,
    option: &str,
    default: i64,
    usage: &str,
    program: &str,
) -> Result<i64, ExitCode> {
    let Some(value) = parsed.value(option) else {
        return Ok(default);
    };
    let text = value.to_string_lossy();
    text.parse().map_err(|_| {
        usage_error(
            usage,
            program,
            &format!("argument {option}: invalid int value: '{text}'"),
            2,
        )
    })
}

fn option_text(parsed: &ParsedCommandLine, option: &str) -> String {
    parsed
        .value(option)
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default()
}

fn path_option(parsed: &ParsedCommandLine, option: &str) -> PathBuf {
    let value = option_text(parsed, option);
    if value.is_empty() {
        PathBuf::from(".")
    } else {
        PathBuf::from(value)
    }
}
