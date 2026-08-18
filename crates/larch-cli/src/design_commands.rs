//! Rust owner for the `/design` Step 0 argv, route, and run-params verbs (#8577).
//!
//! Atomically replaces the Python registrations for `design parse-flags`,
//! `design route`, and `design init-runparams`. The frozen Python reference
//! lives at `fixtures/rust-parity/design_router_frozen/` behind
//! `fixtures/rust-parity/design_router_migrated_reference.py`.
//!
//! Retired branch note (design decision D3, leaf #8577): the Python router
//! shelled out to `issue title-eligibility` and mapped a non-zero subprocess
//! exit to `ROUTE=cancel-title-filter` with `TITLE_FILTER_REASON=error`. This
//! port calls the larch-core title predicates in-process, so that subprocess
//! failure branch is unreachable and the `error` reason is retired. The
//! `TITLE_FILTER_REASON` stdout grammar is preserved for the remaining
//! `lifecycle` and `archival` reasons.

use std::{
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_core::{
    OrderedJson, ParseOptions, ensure_ascii_json, parse_named_block, parse_single_kv_row,
    title_has_archival_report_prefix, title_lifecycle_reject_marker, title_starts_with_brainstorm,
};

use crate::{
    python_verb::run_python_verb, session_env_commands, tracking_issue_commands,
    voter_calibration_commands::resolve_like_python,
};

/// Bound for the delegated `design pause-load` bridge (leaf #8589 retires it).
const PAUSE_LOAD_TIMEOUT: Duration = Duration::from_secs(120);

/// The lifecycle marker whose plan-block special case reroutes. The shared
/// larch-core `LIFECYCLE_PREFIXES` entries carry a trailing space, while
/// `title_lifecycle_reject_marker` returns the bare bracket token this owner
/// compares against.
const DESIGNED_MARKER: &str = "[DESIGNED]";

const ROUTE_PROGRAM: &str = "design-route.sh";
const INIT_PROGRAM: &str = "design-init-runparams.sh";
const PAUSE_MARKER: &str = "<!-- larch:design-pause:start -->";
const ROUTE_USAGE: &str = "Usage: design-route.sh --design-tmpdir PATH --issue N --issue-title STR --issue-body-file PATH --has-clarify-label true|false --claude-pid N --session-id STR";
// The warn texts stay byte-identical to the retired Python `design_router.py`.
// `concat!` keeps each item's final source line ASCII-only for repository
// tooling that resolves proc-macro spans by byte column.
const MERGE_MISSING_WARN: &str = concat!(
    "**⚠ 0b: cannot merge current router flags into run-params.json on resumed/already-planned ",
    "flow; file missing or unsafe. Re-run from Step 0b after repairing run params.**",
);
const MERGE_PARSE_WARN: &str = concat!(
    "**⚠ 0b: jq unavailable or run-params parse failed; current router flags may not persist ",
    "into resumed/already-planned flow.**",
);
const RENAME_WARN: &str = concat!(
    "**⚠ 0b: [DESIGNING] rename failed (scripts/larch.sh tracking-issue rename); continuing ",
    "with run-params write. Re-invoke /design or rename manually if the title is still wrong.**",
);

fn utf8_arguments(arguments: &[OsString]) -> Vec<String> {
    arguments
        .iter()
        .map(|argument| argument.to_string_lossy().into_owned())
        .collect()
}

// ---------------------------------------------------------------------------
// `design parse-flags`
// ---------------------------------------------------------------------------

const SIMPLE_FLAGS: [(&str, usize); 4] = [
    ("-p", 0),
    ("--partition", 0),
    ("--brainstorm", 1),
    ("--no-dedup", 2),
];

const ONCE_FLAGS: [(&str, usize, &str); 3] = [
    ("--per-round-approval", 0, "--per-round-approval"),
    ("--skip-approve", 1, "--skip-approve"),
    ("-s", 1, "--skip-approve"),
];

const KNOWN_PUBLIC_FLAG_TOKENS: [&str; 11] = [
    "-p",
    "--partition",
    "--brainstorm",
    "--no-dedup",
    "--per-round-approval",
    "--skip-approve",
    "-s",
    "--run-id",
    "--difficulty",
    "--hard",
    "--lifecycle-parent-context",
];

#[derive(Default)]
struct ParseFlagsState {
    // partition, brainstorm, no-dedup by SIMPLE_FLAGS index.
    simple: [bool; 3],
    // per-round-approval, skip-approve by ONCE_FLAGS attribute index.
    once: [bool; 2],
    lifecycle_parent_context: String,
    run_id: String,
    difficulty: String,
    positional_args: Vec<String>,
    positional_kind: &'static str,
    positional_value: String,
    issue_captured: bool,
}

fn quote_single(value: &str) -> String {
    let parts: Vec<&str> = value.split('\'').collect();
    format!("'{}'", parts.join("'\"'\"'"))
}

/// Write `KEY='quoted'` rows through a `.NAME.tmp` sibling, like Python's
/// `_write_output`. Returns `false` on any filesystem failure.
fn write_parse_flags_output(output_path: &str, fields: &[(&str, String)]) -> bool {
    let path = Path::new(output_path);
    let parent = match path.parent() {
        Some(parent) if !parent.as_os_str().is_empty() => parent.to_path_buf(),
        _ => PathBuf::from("."),
    };
    if !parent.is_dir() {
        return false;
    }
    let name = path
        .file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .unwrap_or_default();
    let temp = parent.join(format!(".{name}.tmp"));
    let mut text = String::new();
    for (key, value) in fields {
        let _ = writeln!(text, "{key}={}", quote_single(value));
    }
    if fs::write(&temp, text).is_err() || fs::rename(&temp, path).is_err() {
        let _ = fs::remove_file(&temp);
        return false;
    }
    true
}

fn validation_error_message(token: &str) -> String {
    format!(
        "**⚠ /design: unrecognized or disallowed public flag — aborting before session setup.** {token}"
    )
}

fn emit_validation_error(token: &str, output_path: &str) -> ExitCode {
    let token = if token.contains('\n') || token.contains('\r') {
        "newline-in-value"
    } else {
        token
    };
    let message = validation_error_message(token);
    if !output_path.is_empty() {
        let _ = write_parse_flags_output(
            output_path,
            &[
                ("VALIDATION_ERROR", token.to_owned()),
                ("ERROR_MESSAGE", message.clone()),
            ],
        );
    }
    println!("VALIDATION_ERROR={token}");
    println!("ERROR_MESSAGE={message}");
    ExitCode::from(3)
}

fn is_all_digits(token: &str) -> bool {
    !token.is_empty() && token.chars().all(|character| character.is_ascii_digit())
}

fn apply_double_dash(state: &mut ParseFlagsState, rest: &[String]) {
    if state.issue_captured {
        return;
    }
    if rest.first().is_some_and(|first| is_all_digits(first)) {
        state.positional_kind = "issue";
        state.positional_value.clone_from(&rest[0]);
        state.issue_captured = true;
    } else {
        state.positional_args = rest.to_vec();
    }
}

/// The Python `--run-id` / `--difficulty` value parsing: on error the caller
/// receives the already-emitted exit code.
fn parse_value_flag(
    argv: &[String],
    index: usize,
    state: &mut ParseFlagsState,
    output_path: &str,
) -> Result<usize, ExitCode> {
    let token = &argv[index];
    let Some(value) = argv.get(index + 1) else {
        return Err(emit_validation_error(token, output_path));
    };
    if token == "--run-id" {
        if value.starts_with('-') || KNOWN_PUBLIC_FLAG_TOKENS.contains(&value.as_str()) {
            return Err(emit_validation_error(value, output_path));
        }
        state.run_id.clone_from(value);
        return Ok(index + 2);
    }
    let difficulty = value.to_uppercase();
    if !matches!(difficulty.as_str(), "TRIVIAL" | "MODERATE" | "HARD") {
        return Err(emit_validation_error(value, output_path));
    }
    state.difficulty = difficulty;
    Ok(index + 2)
}

fn parse_lifecycle_parent_context(
    argv: &[String],
    index: usize,
    state: &mut ParseFlagsState,
    output_path: &str,
) -> Result<usize, ExitCode> {
    if index != 0 || !state.lifecycle_parent_context.is_empty() {
        return Err(emit_validation_error(
            "--lifecycle-parent-context",
            output_path,
        ));
    }
    let Some(value) = argv.get(index + 1) else {
        return Err(emit_validation_error(
            "--lifecycle-parent-context",
            output_path,
        ));
    };
    if value.is_empty() || value.starts_with('-') {
        let token = if value.is_empty() {
            "--lifecycle-parent-context"
        } else {
            value
        };
        return Err(emit_validation_error(token, output_path));
    }
    state.lifecycle_parent_context.clone_from(value);
    Ok(index + 2)
}

/// Parse the public argv into a bound state, emitting the Python-exact
/// validation error and returning its exit code on rejection.
fn parse_design_flags(argv: &[String], output_path: &str) -> Result<ParseFlagsState, ExitCode> {
    let mut state = ParseFlagsState {
        positional_kind: "none",
        ..ParseFlagsState::default()
    };
    // Flags may appear on either side of a numeric issue positional
    // (non-contiguous argv): after capturing the issue id the loop keeps
    // parsing, so trailing flags are honored and unknown trailing flags
    // still error, rather than being silently dropped. A non-digit first
    // positional starts verbal feature text: flag parsing stops and the
    // remainder is taken literally.
    let mut index = 0;
    'tokens: while index < argv.len() {
        let token = &argv[index];
        if token == "--" {
            apply_double_dash(&mut state, &argv[index + 1..]);
            break;
        }
        if token == "--lifecycle-parent-context" {
            index = parse_lifecycle_parent_context(argv, index, &mut state, output_path)?;
            continue;
        }
        for (flag, slot) in SIMPLE_FLAGS {
            if token == flag {
                state.simple[slot] = true;
                index += 1;
                continue 'tokens;
            }
        }
        for (flag, slot, error_token) in ONCE_FLAGS {
            if token == flag {
                if state.once[slot] {
                    return Err(emit_validation_error(error_token, output_path));
                }
                state.once[slot] = true;
                index += 1;
                continue 'tokens;
            }
        }
        if token == "--run-id" || token == "--difficulty" {
            index = parse_value_flag(argv, index, &mut state, output_path)?;
            continue;
        }
        if token == "--hard" {
            return Err(emit_validation_error("--hard", output_path));
        }
        if token.starts_with('-') {
            return Err(emit_validation_error(token, output_path));
        }
        if !state.issue_captured && is_all_digits(token) {
            state.positional_kind = "issue";
            state.positional_value.clone_from(token);
            state.issue_captured = true;
            index += 1;
            continue;
        }
        if state.issue_captured {
            index += 1;
            continue;
        }
        state.positional_args = argv[index..].to_vec();
        break;
    }
    if state.run_id.contains('\n') || state.run_id.contains('\r') {
        return Err(emit_validation_error("newline-in-value", output_path));
    }
    for token in &state.positional_args {
        if token.contains('\n') || token.contains('\r') {
            return Err(emit_validation_error("newline-in-value", output_path));
        }
    }
    if !state.issue_captured && !state.positional_args.is_empty() {
        state.positional_kind = "verbal";
        state.positional_value = state.positional_args.join(" ");
    }
    Ok(state)
}

const fn bool_text(value: bool) -> &'static str {
    if value { "true" } else { "false" }
}

/// The `design parse-flags` entry point: Step 0-pre public argv validation.
pub fn parse_flags(arguments: &[OsString]) -> ExitCode {
    let mut argv = utf8_arguments(arguments);
    // Hidden --output is internal-only as the leading token pair; reject any
    // public appearance after stripping.
    let mut output_path = String::new();
    if argv.len() >= 2 && argv[0] == "--output" {
        output_path.clone_from(&argv[1]);
        argv.drain(..2);
    }
    if argv.iter().any(|token| token == "--output") {
        return emit_validation_error("--output", &output_path);
    }
    let state = match parse_design_flags(&argv, &output_path) {
        Ok(state) => state,
        Err(code) => return code,
    };
    let booleans = [
        ("partition_requested", state.simple[0]),
        ("brainstorm_requested", state.simple[1]),
        ("approve_requested", state.once[0]),
        ("skip_approve_requested", state.once[1]),
        ("no_dedup_requested", state.simple[2]),
    ];
    let mut output_fields: Vec<(&str, String)> = booleans
        .iter()
        .map(|(key, value)| (*key, bool_text(*value).to_owned()))
        .collect();
    output_fields.extend([
        (
            "lifecycle_parent_context",
            state.lifecycle_parent_context.clone(),
        ),
        ("run_id", state.run_id.clone()),
        ("difficulty", state.difficulty.clone()),
        ("POSITIONAL_KIND", state.positional_kind.to_owned()),
        ("POSITIONAL_VALUE", state.positional_value.clone()),
    ]);
    if !output_path.is_empty() && !write_parse_flags_output(&output_path, &output_fields) {
        return ExitCode::FAILURE;
    }
    for (key, value) in [
        ("PARTITION_REQUESTED", bool_text(state.simple[0]).to_owned()),
        (
            "BRAINSTORM_REQUESTED",
            bool_text(state.simple[1]).to_owned(),
        ),
        ("APPROVE_REQUESTED", bool_text(state.once[0]).to_owned()),
        (
            "SKIP_APPROVE_REQUESTED",
            bool_text(state.once[1]).to_owned(),
        ),
        ("NO_DEDUP_REQUESTED", bool_text(state.simple[2]).to_owned()),
        ("LIFECYCLE_PARENT_CONTEXT", state.lifecycle_parent_context),
        ("RUN_ID", state.run_id),
        ("DIFFICULTY", state.difficulty),
        ("POSITIONAL_KIND", state.positional_kind.to_owned()),
        ("POSITIONAL_VALUE", state.positional_value),
    ] {
        println!("{key}={value}");
    }
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// Shared KV plumbing for `route` and `init-runparams`
// ---------------------------------------------------------------------------

/// Parse `KEY=value` stdout rows in order, skipping empty keys, matching the
/// Python `larch_io.parse_kv(duplicate_policy="all", skip_empty_key=True)`.
fn parse_stdout_kv(text: &str) -> Vec<(String, String)> {
    let mut rows = Vec::new();
    for raw in text.split('\n') {
        let Some(row) = parse_single_kv_row(raw, ParseOptions::legacy()) else {
            continue;
        };
        if row.key().is_empty() {
            continue;
        }
        rows.push((row.key().to_owned(), row.value().to_owned()));
    }
    rows
}

fn kv_last<'a>(rows: &'a [(String, String)], key: &str, default: &'a str) -> &'a str {
    rows.iter()
        .rev()
        .find(|(row_key, _)| row_key == key)
        .map_or(default, |(_, value)| value.as_str())
}

fn kv_all<'a>(rows: &'a [(String, String)], key: &str) -> Vec<&'a str> {
    rows.iter()
        .filter(|(row_key, _)| row_key == key)
        .map(|(_, value)| value.as_str())
        .collect()
}

/// Write `KEY=value` rows non-atomically like the Python `_write_kv_file`;
/// failures are swallowed exactly like the `OSError` branch there.
fn write_kv_file(path: &Path, rows: &[(String, String)]) {
    let mut text = String::new();
    for (key, value) in rows {
        let _ = writeln!(text, "{key}={value}");
    }
    let _ = fs::write(path, text);
}

// ---------------------------------------------------------------------------
// Python-shaped run-params JSON merge
// ---------------------------------------------------------------------------

/// Python truthiness for a JSON value, matching `bool(data.get(key))`.
fn json_truthy(value: &OrderedJson) -> bool {
    match value {
        OrderedJson::Null => false,
        OrderedJson::Bool(value) => *value,
        OrderedJson::Number(value) => value.as_f64() != Some(0.0),
        OrderedJson::String(value) => !value.is_empty(),
        OrderedJson::Array(values) => !values.is_empty(),
        OrderedJson::Object(values) => !values.is_empty(),
    }
}

fn set_member(members: &mut Vec<(String, OrderedJson)>, key: &str, value: OrderedJson) {
    if let Some((_, existing)) = members.iter_mut().find(|(name, _)| name == key) {
        *existing = value;
    } else {
        members.push((key.to_owned(), value));
    }
}

fn json_string_literal(value: &str) -> Result<String, serde_json::Error> {
    Ok(ensure_ascii_json(&serde_json::to_string(value)?))
}

/// Render ordered JSON like Python's `json.dumps(value, indent=2)`.
fn python_json_indent2(value: &OrderedJson) -> Result<String, serde_json::Error> {
    let mut rendered = String::new();
    write_python_json_indent2(value, 0, &mut rendered)?;
    Ok(rendered)
}

fn write_python_json_indent2(
    value: &OrderedJson,
    level: usize,
    rendered: &mut String,
) -> Result<(), serde_json::Error> {
    let indent = "  ".repeat(level + 1);
    let closing = "  ".repeat(level);
    match value {
        OrderedJson::Null => rendered.push_str("null"),
        OrderedJson::Bool(value) => rendered.push_str(bool_text(*value)),
        OrderedJson::Number(value) => rendered.push_str(&value.to_string()),
        OrderedJson::String(value) => rendered.push_str(&json_string_literal(value)?),
        OrderedJson::Array(values) => {
            if values.is_empty() {
                rendered.push_str("[]");
                return Ok(());
            }
            rendered.push_str("[\n");
            for (index, value) in values.iter().enumerate() {
                if index > 0 {
                    rendered.push_str(",\n");
                }
                rendered.push_str(&indent);
                write_python_json_indent2(value, level + 1, rendered)?;
            }
            rendered.push('\n');
            rendered.push_str(&closing);
            rendered.push(']');
        }
        OrderedJson::Object(members) => {
            if members.is_empty() {
                rendered.push_str("{}");
                return Ok(());
            }
            rendered.push_str("{\n");
            for (index, (key, value)) in members.iter().enumerate() {
                if index > 0 {
                    rendered.push_str(",\n");
                }
                rendered.push_str(&indent);
                rendered.push_str(&json_string_literal(key)?);
                rendered.push_str(": ");
                write_python_json_indent2(value, level + 1, rendered)?;
            }
            rendered.push('\n');
            rendered.push_str(&closing);
            rendered.push('}');
        }
    }
    Ok(())
}

#[allow(clippy::struct_excessive_bools)] // Mirrors the Python merge signature.
struct MergeFlags {
    partition: bool,
    brainstorm: bool,
    approve: bool,
    skip_approve: bool,
    difficulty: String,
}

/// Merge the current router flags into `run-params.json`, matching the Python
/// `_merge_router_flags` warn texts, silent non-dict return, and rewrite shape.
fn merge_router_flags(run_params: &Path, warn_lines: &mut Vec<String>, flags: &MergeFlags) {
    if !(flags.partition
        || flags.brainstorm
        || flags.approve
        || flags.skip_approve
        || !flags.difficulty.is_empty())
    {
        return;
    }
    if run_params.is_symlink() || !run_params.is_file() {
        warn_lines.push(MERGE_MISSING_WARN.to_owned());
        return;
    }
    let Ok(text) = fs::read_to_string(run_params) else {
        warn_lines.push(MERGE_PARSE_WARN.to_owned());
        return;
    };
    let Ok(value) = serde_json::from_str::<OrderedJson>(&text) else {
        warn_lines.push(MERGE_PARSE_WARN.to_owned());
        return;
    };
    let OrderedJson::Object(mut members) = value else {
        return;
    };
    for (key, merge) in [
        ("partition_requested", flags.partition),
        ("brainstorm_requested", flags.brainstorm),
        ("approve_requested", flags.approve),
        ("skip_approve_requested", flags.skip_approve),
    ] {
        let current = members
            .iter()
            .find(|(name, _)| name == key)
            .is_some_and(|(_, value)| json_truthy(value));
        set_member(&mut members, key, OrderedJson::Bool(current || merge));
    }
    if !flags.difficulty.is_empty() {
        set_member(
            &mut members,
            "difficulty_override",
            OrderedJson::String(flags.difficulty.clone()),
        );
    }
    let Ok(rendered) = python_json_indent2(&OrderedJson::Object(members)) else {
        warn_lines.push(MERGE_PARSE_WARN.to_owned());
        return;
    };
    if fs::write(run_params, format!("{rendered}\n")).is_err() {
        warn_lines.push(MERGE_PARSE_WARN.to_owned());
    }
}

// ---------------------------------------------------------------------------
// `design route`
// ---------------------------------------------------------------------------

/// Seam over the still-Python `design pause-load` verb: `(exit_code, stdout)`.
type PauseLoad<'a> = &'a dyn Fn(&[OsString]) -> (i32, String);

fn live_pause_load(arguments: &[OsString]) -> (i32, String) {
    match run_python_verb(arguments.to_vec(), PAUSE_LOAD_TIMEOUT) {
        Ok(output) => (
            output.status().code().unwrap_or(1),
            String::from_utf8_lossy(output.stdout()).into_owned(),
        ),
        Err(_error) => (1, String::new()),
    }
}

/// The `design route` entry point: Step 0b routing decision.
pub fn route(arguments: &[OsString]) -> ExitCode {
    route_with(arguments, &live_pause_load)
}

struct RouteArguments {
    required: Vec<(&'static str, String)>,
    optional: Vec<(&'static str, String)>,
}

impl RouteArguments {
    fn value(&self, name: &str) -> &str {
        self.required
            .iter()
            .chain(self.optional.iter())
            .find(|(key, _)| *key == name)
            .map_or("", |(_, value)| value.as_str())
    }
}

fn scan_route_arguments(argv: &[String]) -> Result<RouteArguments, ExitCode> {
    let mut parsed = RouteArguments {
        required: vec![
            ("--design-tmpdir", String::new()),
            ("--issue", String::new()),
            ("--issue-title", String::new()),
            ("--issue-body-file", String::new()),
            ("--has-clarify-label", String::new()),
            ("--claude-pid", String::new()),
            ("--session-id", String::new()),
        ],
        optional: vec![
            ("--repo", String::new()),
            ("--partition-requested", "false".to_owned()),
            ("--brainstorm-requested", "false".to_owned()),
            ("--approve-requested", "false".to_owned()),
            ("--skip-approve-requested", "false".to_owned()),
            ("--difficulty", String::new()),
        ],
    };
    let mut index = 0;
    while index < argv.len() {
        let token = &argv[index];
        let slot = parsed
            .required
            .iter_mut()
            .chain(parsed.optional.iter_mut())
            .find(|(key, _)| key == token);
        if let Some((_, value)) = slot {
            let Some(next) = argv.get(index + 1) else {
                eprintln!("{ROUTE_PROGRAM}: {token} requires a value");
                return Err(ExitCode::from(2));
            };
            value.clone_from(next);
            index += 2;
            continue;
        }
        if token == "-h" || token == "--help" {
            eprintln!("{ROUTE_USAGE}");
            return Err(ExitCode::SUCCESS);
        }
        eprintln!("{ROUTE_PROGRAM}: unknown option: {token}");
        return Err(ExitCode::from(2));
    }
    if parsed.required.iter().any(|(_, value)| value.is_empty()) {
        eprintln!("{ROUTE_PROGRAM}: missing required arguments");
        return Err(ExitCode::from(2));
    }
    Ok(parsed)
}

#[allow(clippy::too_many_lines)] // One verb, one Python main ported branch for branch.
fn route_with(arguments: &[OsString], pause_load: PauseLoad<'_>) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let parsed = match scan_route_arguments(&argv) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let design_tmpdir = resolve_like_python(Path::new(parsed.value("--design-tmpdir")));
    let issue_body_file = Path::new(parsed.value("--issue-body-file"));
    if issue_body_file.is_symlink() || !issue_body_file.is_file() {
        eprintln!("{ROUTE_PROGRAM}: issue-body-file must be a readable regular file");
        return ExitCode::from(2);
    }

    let result_env = design_tmpdir.join(".design-route-result.env");
    let mut warn_lines: Vec<String> = Vec::new();
    let mut error_lines: Vec<String> = Vec::new();
    let route: String;
    let mut brainstorm_prefix = "false";
    let mut title_filter_reason = "";
    let mut title_filter_marker = String::new();
    let mut resume_step = String::new();
    let mut session_id = String::new();
    let mut run_id = String::new();
    let mut brainstorm_done = String::new();
    let mut marker_cleared = String::new();

    let body = String::from_utf8_lossy(&fs::read(issue_body_file).unwrap_or_default()).into_owned();
    if body.contains(PAUSE_MARKER) {
        let mut pause_arguments: Vec<OsString> = vec![
            "design".into(),
            "pause-load".into(),
            "--design-tmpdir".into(),
            design_tmpdir.as_os_str().to_owned(),
            "--issue".into(),
            parsed.value("--issue").into(),
        ];
        let repo = parsed.value("--repo");
        if !repo.is_empty() {
            pause_arguments.extend(["--repo".into(), repo.into()]);
        }
        let (pause_code, pause_stdout) = pause_load(&pause_arguments);
        let pause_kv = parse_stdout_kv(&pause_stdout);
        warn_lines.extend(
            kv_all(&pause_kv, "WARN")
                .iter()
                .map(|row| (*row).to_owned()),
        );
        error_lines.extend(
            kv_all(&pause_kv, "ERROR")
                .iter()
                .map(|row| (*row).to_owned()),
        );
        let load_ok = kv_last(&pause_kv, "LOAD_OK", "false") == "true";
        let has_step = pause_kv.iter().any(|(key, _)| key == "STEP");
        if pause_code == 0 && load_ok && has_step {
            kv_last(&pause_kv, "STEP", "").clone_into(&mut resume_step);
            kv_last(&pause_kv, "SESSION_ID", "").clone_into(&mut session_id);
            kv_last(&pause_kv, "RUN_ID", "").clone_into(&mut run_id);
            kv_last(&pause_kv, "BRAINSTORM_DONE", "").clone_into(&mut brainstorm_done);
            kv_last(&pause_kv, "MARKER_CLEARED", "").clone_into(&mut marker_cleared);
            route = format!("resume@{resume_step}");
        } else {
            route = "cancel-pause-load".to_owned();
            if pause_code != 0 {
                error_lines.push("design-pause-load-failed".to_owned());
            }
        }
    } else {
        let has_clarify = parsed.value("--has-clarify-label") == "true";
        let has_plan = parse_named_block(&body, "plan").ok().flatten().is_some();
        let title = parsed.value("--issue-title");
        if let Some(marker) = title_lifecycle_reject_marker(title) {
            if marker == DESIGNED_MARKER && has_plan {
                route = if has_clarify {
                    "clarify"
                } else {
                    "already-planned"
                }
                .to_owned();
            } else {
                title_filter_marker = marker;
                route = "cancel-title-filter".to_owned();
                title_filter_reason = "lifecycle";
            }
        } else if title_has_archival_report_prefix(title) {
            route = "cancel-title-filter".to_owned();
            title_filter_reason = "archival";
        } else {
            if title_starts_with_brainstorm(title) {
                brainstorm_prefix = "true";
            }
            route = if has_clarify {
                "clarify"
            } else if has_plan {
                "already-planned"
            } else {
                "proceed"
            }
            .to_owned();
        }
    }

    if route.starts_with("resume@") || route == "already-planned" {
        merge_router_flags(
            &design_tmpdir.join("run-params.json"),
            &mut warn_lines,
            &MergeFlags {
                partition: parsed.value("--partition-requested") == "true",
                brainstorm: parsed.value("--brainstorm-requested") == "true"
                    || brainstorm_prefix == "true",
                approve: parsed.value("--approve-requested") == "true",
                skip_approve: parsed.value("--skip-approve-requested") == "true",
                difficulty: parsed.value("--difficulty").to_owned(),
            },
        );
    }

    let mut out: Vec<(String, String)> = vec![
        ("ROUTE".to_owned(), route),
        ("BRAINSTORM_PREFIX".to_owned(), brainstorm_prefix.to_owned()),
    ];
    for (key, value) in [
        ("TITLE_FILTER_REASON", title_filter_reason.to_owned()),
        ("TITLE_FILTER_MARKER", title_filter_marker),
        ("RESUME_STEP", resume_step),
        ("SESSION_ID", session_id),
        ("RUN_ID", run_id),
        ("BRAINSTORM_DONE", brainstorm_done),
        ("MARKER_CLEARED", marker_cleared),
    ] {
        if !value.is_empty() {
            out.push((key.to_owned(), value));
        }
    }
    out.extend(
        warn_lines
            .into_iter()
            .map(|warning| ("WARN".to_owned(), warning)),
    );
    out.extend(
        error_lines
            .into_iter()
            .map(|error| ("ERROR".to_owned(), error)),
    );
    write_kv_file(&result_env, &out);
    for (key, value) in &out {
        println!("{key}={value}");
    }
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// `design init-runparams`
// ---------------------------------------------------------------------------

/// In-process effects the run-params initializer drives; unit tests inject
/// deterministic implementations for the subprocess-era branches.
trait InitRunparamsEffects {
    /// Refresh the `/design` session env; `true` means success.
    fn write_design_env(&self, arguments: &[OsString]) -> bool;
    /// Apply the `[DESIGNING]` rename and return the read-back renamed flag.
    fn rename_designing(&self, issue: &str, repository: Option<&str>) -> Result<bool, String>;
    /// Write the schema v3 run-params document; `true` means success.
    fn write_run_params(&self, arguments: &[OsString]) -> bool;
}

struct LiveInitEffects;

impl InitRunparamsEffects for LiveInitEffects {
    fn write_design_env(&self, arguments: &[OsString]) -> bool {
        session_env_commands::write_design_env(arguments) == ExitCode::SUCCESS
    }

    fn rename_designing(&self, issue: &str, repository: Option<&str>) -> Result<bool, String> {
        tracking_issue_commands::rename_designing_live(issue, repository)
    }

    fn write_run_params(&self, arguments: &[OsString]) -> bool {
        session_env_commands::write_run_params(arguments) == ExitCode::SUCCESS
    }
}

const INIT_OPTIONS: [&str; 10] = [
    "--design-tmpdir",
    "--issue",
    "--session-id",
    "--claude-pid",
    "--partition-requested",
    "--brainstorm-requested",
    "--approve-requested",
    "--skip-approve-requested",
    "--repo",
    "--difficulty",
];

const INIT_REQUIRED: [&str; 8] = [
    "--design-tmpdir",
    "--issue",
    "--session-id",
    "--claude-pid",
    "--partition-requested",
    "--brainstorm-requested",
    "--approve-requested",
    "--skip-approve-requested",
];

/// The `design init-runparams` entry point: Step 0b env, rename, run-params.
pub fn init_runparams(arguments: &[OsString]) -> ExitCode {
    init_runparams_with(arguments, &LiveInitEffects)
}

fn scan_init_arguments(argv: &[String]) -> Result<Vec<(String, String)>, ExitCode> {
    let mut parsed: Vec<(String, String)> = Vec::new();
    let mut index = 0;
    while index < argv.len() {
        let token = &argv[index];
        if INIT_OPTIONS.contains(&token.as_str()) {
            let Some(next) = argv.get(index + 1) else {
                eprintln!("{INIT_PROGRAM}: {token} requires a value");
                return Err(ExitCode::from(2));
            };
            if let Some((_, value)) = parsed.iter_mut().find(|(key, _)| key == token) {
                value.clone_from(next);
            } else {
                parsed.push((token.clone(), next.clone()));
            }
            index += 2;
            continue;
        }
        if token == "--classification" {
            // Accepted and ignored, consuming its value token like Python.
            index += 2;
            continue;
        }
        if token == "-h" || token == "--help" {
            return Err(ExitCode::SUCCESS);
        }
        eprintln!("{INIT_PROGRAM}: unknown option: {token}");
        return Err(ExitCode::from(2));
    }
    for needed in INIT_REQUIRED {
        let missing = !parsed
            .iter()
            .any(|(key, value)| key == needed && !value.is_empty());
        if missing {
            eprintln!("{INIT_PROGRAM}: missing required arguments");
            return Err(ExitCode::from(2));
        }
    }
    Ok(parsed)
}

fn parsed_value<'a>(parsed: &'a [(String, String)], key: &str) -> &'a str {
    parsed
        .iter()
        .find(|(name, _)| name == key)
        .map_or("", |(_, value)| value.as_str())
}

#[allow(clippy::too_many_lines)] // One verb, one Python main ported branch for branch.
fn init_runparams_with(arguments: &[OsString], effects: &dyn InitRunparamsEffects) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let parsed = match scan_init_arguments(&argv) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let value = |key: &str| parsed_value(&parsed, key);
    let design_tmpdir = resolve_like_python(Path::new(value("--design-tmpdir")));
    let result_env = design_tmpdir.join(".design-init-runparams-result.env");
    let run_params_path = design_tmpdir.join("run-params.json");
    let mut warn_lines: Vec<String> = Vec::new();

    let repo = value("--repo").to_owned();
    let mut env_arguments: Vec<OsString> = vec![
        "--output".into(),
        design_tmpdir.join("source-env.sh").into_os_string(),
        "--design-tmpdir".into(),
        design_tmpdir.as_os_str().to_owned(),
        "--session-id".into(),
        value("--session-id").into(),
        "--run-id".into(),
        value("--session-id").into(),
        "--issue-number".into(),
        value("--issue").into(),
        "--claude-pid".into(),
        value("--claude-pid").into(),
    ];
    if !repo.is_empty() {
        env_arguments.extend(["--repo".into(), repo.clone().into()]);
    }
    if !effects.write_design_env(&env_arguments) {
        write_kv_file(
            &result_env,
            &[
                ("INIT_STATUS".to_owned(), "env-refresh-failed".to_owned()),
                (
                    "RUN_PARAMS_PATH".to_owned(),
                    run_params_path.display().to_string(),
                ),
            ],
        );
        println!("INIT_STATUS=env-refresh-failed");
        return ExitCode::FAILURE;
    }

    let repository = if repo.is_empty() {
        None
    } else {
        Some(repo.as_str())
    };
    let renamed = match effects.rename_designing(value("--issue"), repository) {
        Ok(renamed) => bool_text(renamed).to_owned(),
        Err(_error) => {
            warn_lines.push(RENAME_WARN.to_owned());
            "false".to_owned()
        }
    };

    let params_arguments: Vec<OsString> = vec![
        "--partition-requested".into(),
        value("--partition-requested").into(),
        "--brainstorm-requested".into(),
        value("--brainstorm-requested").into(),
        "--approve-requested".into(),
        value("--approve-requested").into(),
        "--skip-approve-requested".into(),
        value("--skip-approve-requested").into(),
        "--difficulty".into(),
        value("--difficulty").into(),
        "--output".into(),
        run_params_path.as_os_str().to_owned(),
    ];
    if !effects.write_run_params(&params_arguments) {
        write_kv_file(
            &result_env,
            &[
                ("INIT_STATUS".to_owned(), "contract-drift".to_owned()),
                (
                    "RUN_PARAMS_PATH".to_owned(),
                    run_params_path.display().to_string(),
                ),
            ],
        );
        println!("INIT_STATUS=contract-drift");
        return ExitCode::FAILURE;
    }

    merge_router_flags(
        &run_params_path,
        &mut warn_lines,
        &MergeFlags {
            partition: value("--partition-requested") == "true",
            brainstorm: value("--brainstorm-requested") == "true",
            approve: value("--approve-requested") == "true",
            skip_approve: value("--skip-approve-requested") == "true",
            difficulty: value("--difficulty").to_owned(),
        },
    );
    let mut result_rows: Vec<(String, String)> = vec![
        ("INIT_STATUS".to_owned(), "ok".to_owned()),
        ("RENAMED".to_owned(), renamed),
        (
            "RUN_PARAMS_PATH".to_owned(),
            run_params_path.display().to_string(),
        ),
    ];
    result_rows.extend(
        warn_lines
            .into_iter()
            .map(|warning| ("WARN".to_owned(), warning)),
    );
    write_kv_file(&result_env, &result_rows);
    for (key, value) in &result_rows {
        println!("{key}={value}");
    }
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use std::{
        cell::RefCell,
        ffi::OsString,
        fs,
        path::{Path, PathBuf},
        process::ExitCode,
    };

    use larch_test_support::{DesignFixture, DesignSession, DesignStdoutSnapshot};

    use super::{
        InitRunparamsEffects, MergeFlags, init_runparams_with, merge_router_flags, parse_stdout_kv,
        python_json_indent2, quote_single, route_with,
    };

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn read(path: &Path) -> String {
        String::from_utf8_lossy(&fs::read(path).expect("read fixture file")).into_owned()
    }

    #[test]
    fn quote_single_splices_embedded_quotes() {
        assert_eq!(quote_single("plain"), "'plain'");
        assert_eq!(quote_single("it's"), "'it'\"'\"'s'");
    }

    #[test]
    fn stdout_kv_parsing_keeps_duplicates_in_order_and_skips_empty_keys() {
        let rows = parse_stdout_kv("STEP=old\nSTEP=latest\n=skipped\nno-equals\nWARN=w1\n");
        assert_eq!(
            rows,
            vec![
                ("STEP".to_owned(), "old".to_owned()),
                ("STEP".to_owned(), "latest".to_owned()),
                ("WARN".to_owned(), "w1".to_owned()),
            ]
        );
    }

    #[test]
    fn merge_preserves_key_order_and_python_dump_shape() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let run_params = session.root().join("run-params.json");
        fs::write(
            &run_params,
            "{\n  \"schema_version\": 3,\n  \"partition_requested\": false,\n  \"brainstorm_requested\": false,\n  \"approve_requested\": true,\n  \"skip_approve_requested\": false,\n  \"difficulty_override\": \"\"\n}\n",
        )
        .expect("seed run params");
        let mut warn_lines = Vec::new();
        merge_router_flags(
            &run_params,
            &mut warn_lines,
            &MergeFlags {
                partition: true,
                brainstorm: false,
                approve: false,
                skip_approve: false,
                difficulty: "HARD".to_owned(),
            },
        );
        assert!(warn_lines.is_empty());
        assert_eq!(
            read(&run_params),
            "{\n  \"schema_version\": 3,\n  \"partition_requested\": true,\n  \"brainstorm_requested\": false,\n  \"approve_requested\": true,\n  \"skip_approve_requested\": false,\n  \"difficulty_override\": \"HARD\"\n}\n"
        );
    }

    #[test]
    fn merge_warns_exactly_like_python_on_missing_and_malformed_files() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let missing = session.root().join("run-params.json");
        let mut warn_lines = Vec::new();
        merge_router_flags(
            &missing,
            &mut warn_lines,
            &MergeFlags {
                partition: true,
                brainstorm: false,
                approve: false,
                skip_approve: false,
                difficulty: String::new(),
            },
        );
        fs::write(&missing, "not json").expect("seed malformed file");
        merge_router_flags(
            &missing,
            &mut warn_lines,
            &MergeFlags {
                partition: true,
                brainstorm: false,
                approve: false,
                skip_approve: false,
                difficulty: String::new(),
            },
        );
        assert_eq!(
            warn_lines,
            vec![
                super::MERGE_MISSING_WARN.to_owned(),
                super::MERGE_PARSE_WARN.to_owned(),
            ]
        );
        // A non-object document returns silently without a rewrite, like Python.
        fs::write(&missing, "[1, 2]").expect("seed non-object file");
        let mut silent = Vec::new();
        merge_router_flags(
            &missing,
            &mut silent,
            &MergeFlags {
                partition: true,
                brainstorm: false,
                approve: false,
                skip_approve: false,
                difficulty: String::new(),
            },
        );
        assert!(silent.is_empty());
        assert_eq!(read(&missing), "[1, 2]");
    }

    #[test]
    fn indent2_renderer_matches_python_json_dumps() {
        let value: larch_core::OrderedJson =
            serde_json::from_str("{\"a\": [1, {\"b\": \"x\"}], \"empty\": {}, \"none\": null}")
                .expect("parse fixture JSON");
        assert_eq!(
            python_json_indent2(&value).expect("render"),
            "{\n  \"a\": [\n    1,\n    {\n      \"b\": \"x\"\n    }\n  ],\n  \"empty\": {},\n  \"none\": null\n}"
        );
    }

    #[test]
    fn route_resume_bridges_pause_load_and_merges_flags() {
        let session = DesignSession::builder(DesignFixture::Committed)
            .build()
            .expect("build design session");
        let design_tmpdir = session.design_tmpdir();
        fs::write(
            design_tmpdir.join("run-params.json"),
            "{\n  \"schema_version\": 3,\n  \"partition_requested\": false,\n  \"brainstorm_requested\": false,\n  \"approve_requested\": false,\n  \"skip_approve_requested\": false,\n  \"difficulty_override\": \"\"\n}\n",
        )
        .expect("seed run params");
        let recorded: RefCell<Vec<Vec<OsString>>> = RefCell::new(Vec::new());
        let pause_load = |pause_arguments: &[OsString]| {
            recorded.borrow_mut().push(pause_arguments.to_vec());
            (
                0,
                "WARN=stale marker\nLOAD_OK=true\nSTEP=step-3\nSESSION_ID=sid\nRUN_ID=rid\nBRAINSTORM_DONE=true\nMARKER_CLEARED=true\n"
                    .to_owned(),
            )
        };
        let code = route_with(
            &arguments(&[
                "--design-tmpdir",
                design_tmpdir.to_str().expect("utf8 tmpdir"),
                "--issue",
                "7680",
                "--issue-title",
                "[DESIGNING] Fixture",
                "--issue-body-file",
                session.issue_body_path().to_str().expect("utf8 body path"),
                "--has-clarify-label",
                "false",
                "--claude-pid",
                "4242",
                "--session-id",
                "sid",
                "--repo",
                "character-ai/larch",
                "--brainstorm-requested",
                "true",
            ]),
            &pause_load,
        );
        assert_eq!(code, ExitCode::SUCCESS);
        let calls = recorded.borrow();
        assert_eq!(calls.len(), 1);
        assert_eq!(calls[0][0], OsString::from("design"));
        assert_eq!(calls[0][1], OsString::from("pause-load"));
        assert!(calls[0].contains(&OsString::from("--repo")));
        let result = read(&design_tmpdir.join(".design-route-result.env"));
        assert_eq!(
            result,
            "ROUTE=resume@step-3\nBRAINSTORM_PREFIX=false\nRESUME_STEP=step-3\nSESSION_ID=sid\nRUN_ID=rid\nBRAINSTORM_DONE=true\nMARKER_CLEARED=true\nWARN=stale marker\n"
        );
        let merged = read(&design_tmpdir.join("run-params.json"));
        assert!(merged.contains("\"brainstorm_requested\": true"));
        assert!(merged.contains("\"partition_requested\": false"));
        let snapshot = DesignStdoutSnapshot::capture(result.as_bytes(), &session);
        assert_eq!(snapshot.fields[0].key, "ROUTE");
        assert_eq!(snapshot.fields[0].value.bytes, b"resume@step-3");
    }

    #[test]
    fn route_pause_load_failure_records_error_rows() {
        let session = DesignSession::builder(DesignFixture::Committed)
            .build()
            .expect("build design session");
        let design_tmpdir = session.design_tmpdir();
        let pause_load = |_pause_arguments: &[OsString]| (1, "ERROR=boom\n".to_owned());
        let code = route_with(
            &arguments(&[
                "--design-tmpdir",
                design_tmpdir.to_str().expect("utf8 tmpdir"),
                "--issue",
                "7680",
                "--issue-title",
                "[DESIGNING] Fixture",
                "--issue-body-file",
                session.issue_body_path().to_str().expect("utf8 body path"),
                "--has-clarify-label",
                "false",
                "--claude-pid",
                "4242",
                "--session-id",
                "sid",
            ]),
            &pause_load,
        );
        assert_eq!(code, ExitCode::SUCCESS);
        assert_eq!(
            read(&design_tmpdir.join(".design-route-result.env")),
            "ROUTE=cancel-pause-load\nBRAINSTORM_PREFIX=false\nERROR=boom\nERROR=design-pause-load-failed\n"
        );
    }

    struct RecordingEffects {
        env_ok: bool,
        rename: Result<bool, String>,
        params_ok: bool,
        calls: RefCell<Vec<String>>,
        rename_seen: RefCell<Vec<(String, Option<String>)>>,
    }

    impl InitRunparamsEffects for RecordingEffects {
        fn write_design_env(&self, _arguments: &[OsString]) -> bool {
            self.calls.borrow_mut().push("env".to_owned());
            self.env_ok
        }

        fn rename_designing(&self, issue: &str, repository: Option<&str>) -> Result<bool, String> {
            self.calls.borrow_mut().push("rename".to_owned());
            self.rename_seen
                .borrow_mut()
                .push((issue.to_owned(), repository.map(str::to_owned)));
            self.rename.clone()
        }

        fn write_run_params(&self, arguments: &[OsString]) -> bool {
            self.calls.borrow_mut().push("params".to_owned());
            if self.params_ok {
                // Materialize the schema v3 document the live writer produces.
                let output = arguments
                    .iter()
                    .position(|argument| argument == "--output")
                    .and_then(|index| arguments.get(index + 1))
                    .map(PathBuf::from)
                    .expect("run-params output path");
                fs::write(
                    output,
                    "{\n  \"schema_version\": 3,\n  \"partition_requested\": false,\n  \"brainstorm_requested\": false,\n  \"approve_requested\": false,\n  \"skip_approve_requested\": false,\n  \"difficulty_override\": \"\"\n}\n",
                )
                .expect("write run params");
            }
            self.params_ok
        }
    }

    fn init_arguments(design_tmpdir: &Path) -> Vec<OsString> {
        arguments(&[
            "--design-tmpdir",
            design_tmpdir.to_str().expect("utf8 tmpdir"),
            "--issue",
            "7680",
            "--session-id",
            "sid",
            "--claude-pid",
            "4242",
            "--partition-requested",
            "true",
            "--brainstorm-requested",
            "false",
            "--approve-requested",
            "false",
            "--skip-approve-requested",
            "false",
            "--repo",
            "character-ai/larch",
        ])
    }

    #[test]
    fn init_runparams_success_records_rename_and_merges_flags() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let design_tmpdir = session.root().join("design-tmpdir");
        fs::create_dir_all(&design_tmpdir).expect("create design tmpdir");
        let effects = RecordingEffects {
            env_ok: true,
            rename: Ok(true),
            params_ok: true,
            calls: RefCell::new(Vec::new()),
            rename_seen: RefCell::new(Vec::new()),
        };
        let code = init_runparams_with(&init_arguments(&design_tmpdir), &effects);
        assert_eq!(code, ExitCode::SUCCESS);
        assert_eq!(
            effects.calls.borrow().as_slice(),
            ["env", "rename", "params"]
        );
        assert_eq!(
            effects.rename_seen.borrow().as_slice(),
            [("7680".to_owned(), Some("character-ai/larch".to_owned()))]
        );
        let result = read(&design_tmpdir.join(".design-init-runparams-result.env"));
        assert!(result.starts_with("INIT_STATUS=ok\nRENAMED=true\nRUN_PARAMS_PATH="));
        assert!(!result.contains("WARN="));
        // The router flag merge applied --partition-requested true.
        assert!(
            read(&design_tmpdir.join("run-params.json")).contains("\"partition_requested\": true")
        );
    }

    #[test]
    fn init_runparams_rename_failure_takes_exact_warn_branch() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let design_tmpdir = session.root().join("design-tmpdir");
        fs::create_dir_all(&design_tmpdir).expect("create design tmpdir");
        let effects = RecordingEffects {
            env_ok: true,
            rename: Err("gh unavailable".to_owned()),
            params_ok: true,
            calls: RefCell::new(Vec::new()),
            rename_seen: RefCell::new(Vec::new()),
        };
        let code = init_runparams_with(&init_arguments(&design_tmpdir), &effects);
        assert_eq!(code, ExitCode::SUCCESS);
        let result = read(&design_tmpdir.join(".design-init-runparams-result.env"));
        assert!(result.contains("INIT_STATUS=ok\nRENAMED=false\n"));
        assert!(result.contains(&format!("WARN={}\n", super::RENAME_WARN)));
    }

    #[test]
    fn init_runparams_env_refresh_failure_stops_before_rename() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let design_tmpdir = session.root().join("design-tmpdir");
        fs::create_dir_all(&design_tmpdir).expect("create design tmpdir");
        let effects = RecordingEffects {
            env_ok: false,
            rename: Ok(true),
            params_ok: true,
            calls: RefCell::new(Vec::new()),
            rename_seen: RefCell::new(Vec::new()),
        };
        let code = init_runparams_with(&init_arguments(&design_tmpdir), &effects);
        assert_eq!(code, ExitCode::FAILURE);
        assert_eq!(effects.calls.borrow().as_slice(), ["env"]);
        let result = read(&design_tmpdir.join(".design-init-runparams-result.env"));
        assert!(result.starts_with("INIT_STATUS=env-refresh-failed\nRUN_PARAMS_PATH="));
    }

    #[test]
    fn init_runparams_contract_drift_stops_before_merge() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let design_tmpdir = session.root().join("design-tmpdir");
        fs::create_dir_all(&design_tmpdir).expect("create design tmpdir");
        let effects = RecordingEffects {
            env_ok: true,
            rename: Ok(false),
            params_ok: false,
            calls: RefCell::new(Vec::new()),
            rename_seen: RefCell::new(Vec::new()),
        };
        let code = init_runparams_with(&init_arguments(&design_tmpdir), &effects);
        assert_eq!(code, ExitCode::FAILURE);
        assert_eq!(
            effects.calls.borrow().as_slice(),
            ["env", "rename", "params"]
        );
        let result = read(&design_tmpdir.join(".design-init-runparams-result.env"));
        assert!(result.starts_with("INIT_STATUS=contract-drift\nRUN_PARAMS_PATH="));
    }
}
