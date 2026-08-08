//! One-time, Rust-owned run-log layout and historical repair commands.
//!
//! These verbs intentionally keep their state local to an operator supplied
//! work directory.  They neither use a Python fallback nor mutate source
//! archives.

use std::{
    collections::{BTreeMap, BTreeSet, HashMap},
    ffi::OsString,
    fs,
    io::{Read as _, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
};

use chrono::{SecondsFormat, Utc};
use flate2::read::GzDecoder;
use larch_adapters::{run_lifecycle, runtime::LarchRuntime, s3_storage::S3Storage};
use larch_core::{
    ObjectStore, ObjectStoreError, OrderedJson, RemoteObject, RunLogSlug, StorageBase,
    parse_storage_base_uri, validate_client_repo,
};
use serde_json::{Map, Value};
use sha2::{Digest as _, Sha256};
use tar::Archive;
use tempfile::{NamedTempFile, TempDir};
use unicode_normalization::UnicodeNormalization as _;

use crate::argparse_compat::{ParsedCommandLine, parse, parse_with_flags};

const RETRO_V3_OPTIONS: &[&str] = &["--root"];
const RETRO_CURSOR_OPTIONS: &[&str] = &["--root", "--run-id"];
const RETRO_FLAGS: &[&str] = &["--dry-run"];
const RETRO_V3_USAGE: &str = "usage: cli.py [-h] [--root ROOT] [--dry-run]";
const RETRO_CURSOR_USAGE: &str = "usage: cli.py [-h] [--root ROOT] [--dry-run] [--run-id RUN_ID]";
const RETRO_V3_HELP: &str = "usage: cli.py [-h] [--root ROOT] [--dry-run]\n\nretro_v3_sweep.py \u{2014} transform committed session-transcript.jsonl files to v3\nformat.\n\noptions:\n  -h, --help   show this help message and exit\n  --root ROOT  Repo root (default: cwd)\n  --dry-run    Report without writing";
const RETRO_CURSOR_HELP: &str = "usage: cli.py [-h] [--root ROOT] [--dry-run] [--run-id RUN_ID]\n\nretro_fix_cursor.py \u{2014} retro-fix Cursor pricing in committed final-summary.md files.\n\noptions:\n  -h, --help         show this help message and exit\n  --root ROOT        Repo root (default: cwd)\n  --dry-run          Report without writing\n  --run-id RUN_ID    Fix only this specific run ID";

const V3_TRANSCRIPT_RELATIVE: &str = "larch-logs/implement/*/session-transcript.jsonl";
const CURSOR_INPUT_RATE_PER_M: f64 = 0.75;
const CURSOR_CACHE_READ_RATE_PER_M: f64 = 0.45;
const CURSOR_OUTPUT_RATE_PER_M: f64 = 2.75;

const PLAN_SCHEMA: &str = "larch-run-log-layout-plan-v1";
const REPORT_SCHEMA: &str = "larch-run-log-layout-report-v1";
const FINAL_REPORT_SCHEMA: &str = "larch-run-log-layout-final-report-v1";
const RUN_LOG_PREFIX: &str = "run-logs/";
const PLAN_OPTIONS: &[&str] = &[
    "--larch-source-uri",
    "--larch-target-uri",
    "--agent-lint-source-uri",
    "--agent-lint-target-uri",
    "--legacy-schema",
    "--legacy-source-commit",
    "--legacy-inventory-key",
    "--legacy-inventory-sha256",
    "--output",
    "--work-dir",
    "--operator",
    "--tool-version",
    "--source-commit",
];
const APPLY_OPTIONS: &[&str] = &["--plan", "--report", "--work-dir"];
const VERIFY_OPTIONS: &[&str] = &[
    "--plan",
    "--report",
    "--final-report",
    "--work-dir",
    "--publish-report-key",
];
const APPLY_FLAGS: &[&str] = &["--authorize-live-migration"];
const VERIFY_FLAGS: &[&str] = &["--authorize-report-publication"];
const MIGRATE_USAGE: &str = "usage: cli.py run-log migrate-layout [-h] {plan,apply,verify} ...";
const MIGRATE_HELP: &str = "usage: cli.py run-log migrate-layout [-h] {plan,apply,verify} ...\n\npositional arguments:\n  {plan,apply,verify}\n\noptions:\n  -h, --help           show this help message and exit";
const PLAN_USAGE: &str = "usage: cli.py run-log migrate-layout plan [-h] --larch-source-uri LARCH_SOURCE_URI --larch-target-uri LARCH_TARGET_URI --agent-lint-source-uri AGENT_LINT_SOURCE_URI --agent-lint-target-uri AGENT_LINT_TARGET_URI --legacy-schema LEGACY_SCHEMA --legacy-source-commit LEGACY_SOURCE_COMMIT --legacy-inventory-key LEGACY_INVENTORY_KEY --legacy-inventory-sha256 LEGACY_INVENTORY_SHA256 --output OUTPUT --work-dir WORK_DIR --operator OPERATOR --tool-version TOOL_VERSION --source-commit SOURCE_COMMIT";
const APPLY_USAGE: &str = "usage: cli.py run-log migrate-layout apply [-h] --plan PLAN --report REPORT --work-dir WORK_DIR [--authorize-live-migration]";
const VERIFY_USAGE: &str = "usage: cli.py run-log migrate-layout verify [-h] --plan PLAN --report REPORT --final-report FINAL_REPORT --work-dir WORK_DIR --publish-report-key PUBLISH_REPORT_KEY [--authorize-report-publication]";
const MAX_INVENTORY_BYTES: u64 = 96 * 1024 * 1024;
const MAX_INVENTORY_ARCHIVES: usize = 5_000;
const MAX_INVENTORY_SOURCE_FILES: usize = 250_000;
const MAX_ARCHIVE_MEMBERS: usize = 10_000;
const MAX_ARCHIVE_MEMBER_BYTES: u64 = 256 * 1024 * 1024;
const MAX_ARCHIVE_EXPANDED_BYTES: u64 = 1024 * 1024 * 1024;
const MAX_COMPRESSION_RATIO: u64 = 1_000;

/// Execute the one-time v3 session-transcript sweep.
#[must_use]
pub fn retro_v3_sweep(arguments: &[OsString]) -> ExitCode {
    if has_help(arguments) {
        println!("{RETRO_V3_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = parse_with_flags(arguments, RETRO_V3_OPTIONS, RETRO_FLAGS, 0);
    if let Some(error) = parsed.error() {
        return retro_argument_failure("retro-v3-sweep", RETRO_V3_USAGE, &error);
    }
    let root = parsed
        .value("--root")
        .map_or_else(|| PathBuf::from("."), PathBuf::from);
    let dry_run = parsed.flag("--dry-run");
    match retro_v3_sweep_impl(&root, dry_run) {
        Ok(outcome) => {
            if outcome.files.is_empty() {
                eprintln!(
                    "retro-v3-sweep: no files matched {V3_TRANSCRIPT_RELATIVE} under {}",
                    root.display()
                );
                return ExitCode::SUCCESS;
            }
            for file in outcome.changed {
                let key = if dry_run {
                    "DRY_RUN_PATH"
                } else {
                    "CHANGED_PATH"
                };
                println!("{key}={file}");
            }
            let verb = if dry_run {
                "would transform"
            } else {
                "transformed"
            };
            println!(
                "retro-v3-sweep: {verb} {}, skipped {} (already v3), empty/unparseable {}",
                outcome.counts.transformed, outcome.counts.skipped, outcome.counts.empty
            );
            ExitCode::SUCCESS
        }
        Err(error) => retro_failure("retro-v3-sweep", &error),
    }
}

/// Execute the one-time Cursor cost repair sweep.
#[must_use]
pub fn retro_fix_cursor(arguments: &[OsString]) -> ExitCode {
    if has_help(arguments) {
        println!("{RETRO_CURSOR_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = parse_with_flags(arguments, RETRO_CURSOR_OPTIONS, RETRO_FLAGS, 0);
    if let Some(error) = parsed.error() {
        return retro_argument_failure("retro-fix-cursor", RETRO_CURSOR_USAGE, &error);
    }
    let root = parsed
        .value("--root")
        .map_or_else(|| PathBuf::from("."), PathBuf::from);
    let run_id = match parsed.value("--run-id") {
        Some(value) => match value.to_str() {
            Some(value) => Some(value),
            None => {
                return retro_argument_failure(
                    "retro-fix-cursor",
                    RETRO_CURSOR_USAGE,
                    "argument --run-id must be valid UTF-8",
                );
            }
        },
        None => None,
    };
    let dry_run = parsed.flag("--dry-run");
    match retro_fix_cursor_impl(&root, dry_run, run_id) {
        Ok(outcome) => {
            if outcome.files.is_empty() {
                eprintln!("retro-fix-cursor: no final-summary.md files found");
                return ExitCode::SUCCESS;
            }
            for file in outcome.changed {
                let key = if dry_run {
                    "DRY_RUN_PATH"
                } else {
                    "CHANGED_PATH"
                };
                println!("{key}={file}");
            }
            let verb = if dry_run { "would fix" } else { "fixed" };
            println!(
                "retro-fix-cursor: {verb} {}, skipped-no-cursor {}, skipped-no-report {}, \
                 skipped-no-buckets {}, skipped-no-cache-read {}, skipped-already-correct {}, \
                 skipped-format-mismatch {}",
                outcome.counts.fixed,
                outcome.counts.no_cursor,
                outcome.counts.no_report,
                outcome.counts.no_buckets,
                outcome.counts.no_cache_read,
                outcome.counts.already_correct,
                outcome.counts.format_mismatch,
            );
            ExitCode::SUCCESS
        }
        Err(error) => retro_failure("retro-fix-cursor", &error),
    }
}

fn has_help(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .any(|argument| matches!(argument.to_str(), Some("-h" | "--help")))
}

fn retro_argument_failure(command: &str, usage: &str, message: &str) -> ExitCode {
    eprintln!("{usage}");
    eprintln!("cli.py run-log {command}: error: {message}");
    ExitCode::from(2)
}

fn retro_failure(command: &str, error: &str) -> ExitCode {
    eprintln!("{command} failed: {}", error.replace(['\n', '\r'], " "));
    ExitCode::FAILURE
}

#[derive(Default)]
struct RetroV3Counts {
    transformed: usize,
    skipped: usize,
    empty: usize,
}

struct RetroV3Outcome {
    files: Vec<PathBuf>,
    changed: Vec<String>,
    counts: RetroV3Counts,
}

fn retro_v3_sweep_impl(root: &Path, dry_run: bool) -> Result<RetroV3Outcome, String> {
    let root = trusted_root(root)?;
    let files = transcript_files(&root)?;
    let mut counts = RetroV3Counts::default();
    let mut changed = Vec::new();
    for path in &files {
        let status = transform_transcript(path, dry_run)?;
        match status {
            TranscriptStatus::Transformed => {
                counts.transformed += 1;
                changed.push(relative_display(&root, path)?);
            }
            TranscriptStatus::Skipped => counts.skipped += 1,
            TranscriptStatus::Empty => counts.empty += 1,
        }
    }
    Ok(RetroV3Outcome {
        files,
        changed,
        counts,
    })
}

#[derive(Clone, Copy)]
enum TranscriptStatus {
    Transformed,
    Skipped,
    Empty,
}

fn transform_transcript(path: &Path, dry_run: bool) -> Result<TranscriptStatus, String> {
    let content = read_regular_utf8_lossy(path)?;
    let lines: Vec<&str> = content.lines().collect();
    let Some(header_line) = lines.first() else {
        return Ok(TranscriptStatus::Empty);
    };
    let Ok(OrderedJson::Object(mut header)) = serde_json::from_str(header_line) else {
        return Ok(TranscriptStatus::Empty);
    };
    if ordered_number_is_three(ordered_field(&header, "v")) {
        return Ok(TranscriptStatus::Skipped);
    }
    ordered_insert(
        &mut header,
        "v",
        OrderedJson::Number(serde_json::Number::from(3)),
    );
    ordered_insert(
        &mut header,
        "policy",
        OrderedJson::String("prose-errors-only".to_owned()),
    );
    let mut turns = Vec::new();
    for line in lines
        .iter()
        .skip(1)
        .map(|line| line.trim())
        .filter(|line| !line.is_empty())
    {
        let Ok(OrderedJson::Object(mut record)) = serde_json::from_str(line) else {
            continue;
        };
        let Some(OrderedJson::Array(blocks)) = ordered_field(&record, "blocks") else {
            turns.push(OrderedJson::Object(record));
            continue;
        };
        let filtered: Vec<OrderedJson> = blocks
            .iter()
            .filter_map(|block| match block {
                OrderedJson::Object(block) => Some(block),
                _ => None,
            })
            .filter(|block| {
                let kind = ordered_field(block, "type").and_then(|value| match value {
                    OrderedJson::String(value) => Some(value.as_str()),
                    _ => None,
                });
                kind != Some("tool_call")
                    && (kind != Some("tool_result")
                        || ordered_field(block, "error").is_some_and(ordered_value_is_truthy)
                        || ordered_field(block, "warning").is_some_and(ordered_value_is_truthy))
            })
            .cloned()
            .map(OrderedJson::Object)
            .collect();
        if filtered.is_empty() {
            continue;
        }
        ordered_insert(&mut record, "blocks", OrderedJson::Array(filtered));
        turns.push(OrderedJson::Object(record));
    }
    ordered_insert(
        &mut header,
        "turns",
        OrderedJson::Number(serde_json::Number::from(turns.len())),
    );
    let mut rendered = serde_json::to_string(&OrderedJson::Object(header))
        .map_err(|error| format!("could not serialize transcript header: {error}"))?;
    for turn in turns {
        rendered.push('\n');
        rendered.push_str(
            &serde_json::to_string(&turn)
                .map_err(|error| format!("could not serialize transcript turn: {error}"))?,
        );
    }
    rendered.push('\n');
    if !dry_run {
        atomic_replace(path, rendered.as_bytes())?;
    }
    Ok(TranscriptStatus::Transformed)
}

fn ordered_field<'a>(object: &'a [(String, OrderedJson)], field: &str) -> Option<&'a OrderedJson> {
    object
        .iter()
        .find_map(|(key, value)| (key == field).then_some(value))
}

fn ordered_insert(object: &mut Vec<(String, OrderedJson)>, field: &str, value: OrderedJson) {
    if let Some((_, existing)) = object.iter_mut().find(|(key, _)| key == field) {
        *existing = value;
    } else {
        object.push((field.to_owned(), value));
    }
}

fn ordered_number_is_three(value: Option<&OrderedJson>) -> bool {
    matches!(value, Some(OrderedJson::Number(number)) if number.as_f64() == Some(3.0))
}

fn ordered_value_is_truthy(value: &OrderedJson) -> bool {
    match value {
        OrderedJson::Null => false,
        OrderedJson::Bool(value) => *value,
        OrderedJson::Number(value) => value.as_f64().is_some_and(|value| value != 0.0),
        OrderedJson::String(value) => !value.is_empty(),
        OrderedJson::Array(value) => !value.is_empty(),
        OrderedJson::Object(value) => !value.is_empty(),
    }
}

#[derive(Default)]
struct RetroCursorCounts {
    fixed: usize,
    no_cursor: usize,
    no_report: usize,
    no_buckets: usize,
    no_cache_read: usize,
    already_correct: usize,
    format_mismatch: usize,
}

struct RetroCursorOutcome {
    files: Vec<PathBuf>,
    changed: Vec<String>,
    counts: RetroCursorCounts,
}

fn retro_fix_cursor_impl(
    root: &Path,
    dry_run: bool,
    run_id: Option<&str>,
) -> Result<RetroCursorOutcome, String> {
    let root = trusted_root(root)?;
    let files = summary_files(&root, run_id)?;
    let mut counts = RetroCursorCounts::default();
    let mut changed = Vec::new();
    for path in &files {
        let status = transform_cursor_summary(path, dry_run)?;
        match status {
            CursorStatus::Fixed => {
                counts.fixed += 1;
                changed.push(relative_display(&root, path)?);
            }
            CursorStatus::NoCursor => counts.no_cursor += 1,
            CursorStatus::NoReport => counts.no_report += 1,
            CursorStatus::NoBuckets => counts.no_buckets += 1,
            CursorStatus::NoCacheRead => counts.no_cache_read += 1,
            CursorStatus::AlreadyCorrect => counts.already_correct += 1,
            CursorStatus::FormatMismatch => counts.format_mismatch += 1,
        }
    }
    Ok(RetroCursorOutcome {
        files,
        changed,
        counts,
    })
}

#[derive(Clone, Copy)]
enum CursorStatus {
    Fixed,
    NoCursor,
    NoReport,
    NoBuckets,
    NoCacheRead,
    AlreadyCorrect,
    FormatMismatch,
}

fn transform_cursor_summary(path: &Path, dry_run: bool) -> Result<CursorStatus, String> {
    let original = read_regular_utf8(path)?;
    let Some((cursor_start, cursor_end, stored_cursor)) = decimal_after(&original, "Cursor $")
    else {
        return Ok(CursorStatus::NoCursor);
    };
    if stored_cursor == 0.0 {
        return Ok(CursorStatus::NoCursor);
    }
    let Some(report_path) = token_report(
        path.parent()
            .ok_or_else(|| "summary parent is missing".to_owned())?,
    ) else {
        return Ok(CursorStatus::NoReport);
    };
    let Some(Value::Object(report)) = read_regular_utf8(&report_path)
        .ok()
        .and_then(|encoded| serde_json::from_str::<Value>(&encoded).ok())
    else {
        return Ok(CursorStatus::NoReport);
    };
    let Some(buckets) = report.get("BUCKETS_cursor").and_then(Value::as_object) else {
        return Ok(CursorStatus::NoBuckets);
    };
    let cache_read = value_as_i64(buckets.get("cache_read"));
    if cache_read == 0 {
        return Ok(CursorStatus::NoCacheRead);
    }
    let cost = cursor_cost(
        value_as_i64(buckets.get("input")),
        cache_read,
        value_as_i64(buckets.get("output")),
    );
    if (cost - stored_cursor).abs() < f64::EPSILON {
        return Ok(CursorStatus::AlreadyCorrect);
    }
    let Some((total_start, total_end, stored_total)) = decimal_after(&original, "TOTAL ~$") else {
        return Ok(CursorStatus::FormatMismatch);
    };
    let new_total = round_money(stored_total - stored_cursor + cost);
    let mut updated = original.clone();
    // A corrected total can change width (for example, $9.99 to $10.88).
    // Replace from right to left so the earlier byte range remains valid.
    let mut replacements = [
        (cursor_start, cursor_end, format!("{cost:.2}")),
        (total_start, total_end, format!("{new_total:.2}")),
    ];
    replacements.sort_unstable_by(|left, right| right.0.cmp(&left.0));
    for (start, end, replacement) in replacements {
        updated.replace_range(start..end, &replacement);
    }
    if updated == original {
        return Ok(CursorStatus::FormatMismatch);
    }
    if !dry_run {
        atomic_replace(path, updated.as_bytes())?;
    }
    Ok(CursorStatus::Fixed)
}

fn token_report(run_dir: &Path) -> Option<PathBuf> {
    ["token-report-final.json", "token-report.json"]
        .into_iter()
        .map(|name| run_dir.join(name))
        .find(|path| is_regular_nonsymlink(path))
}

fn decimal_after(value: &str, prefix: &str) -> Option<(usize, usize, f64)> {
    value.match_indices(prefix).find_map(|(prefix_start, _)| {
        let start = prefix_start.checked_add(prefix.len())?;
        let suffix = value.get(start..)?;
        let bytes = suffix.as_bytes();
        let integer_digits = bytes
            .iter()
            .take_while(|byte| byte.is_ascii_digit())
            .count();
        if integer_digits == 0 || bytes.get(integer_digits) != Some(&b'.') {
            return None;
        }
        let fraction_start = integer_digits + 1;
        let fraction_digits = bytes[fraction_start..]
            .iter()
            .take_while(|byte| byte.is_ascii_digit())
            .count();
        if fraction_digits == 0 {
            return None;
        }
        let end = fraction_start + fraction_digits;
        suffix
            .get(..end)?
            .parse::<f64>()
            .ok()
            .map(|parsed| (start, start + end, parsed))
    })
}

#[allow(
    clippy::cast_possible_truncation,
    clippy::cast_precision_loss,
    reason = "The retired Python helper intentionally applies int() to finite JSON floats."
)]
fn value_as_i64(value: Option<&Value>) -> i64 {
    let Some(value) = value else {
        return 0;
    };
    if let Value::Bool(value) = value {
        return i64::from(*value);
    }
    let Some(number) = value.as_number() else {
        return 0;
    };
    if let Some(integer) = number.as_i64() {
        return integer;
    }
    if let Some(integer) = number
        .as_u64()
        .and_then(|integer| i64::try_from(integer).ok())
    {
        return integer;
    }
    let Some(float) = number.as_f64().filter(|float| float.is_finite()) else {
        return 0;
    };
    if !(float >= i64::MIN as f64 && float <= i64::MAX as f64) {
        return 0;
    }
    float as i64
}

fn cursor_cost(input: i64, cache_read: i64, output: i64) -> f64 {
    // This is the historical composer-2.5 correction contract.  Going-forward
    // pricing remains owned by the report-pricing migration leaf (#8087).
    round_money(
        bucket_cost(input, CURSOR_INPUT_RATE_PER_M)
            + bucket_cost(cache_read, CURSOR_CACHE_READ_RATE_PER_M)
            + bucket_cost(output, CURSOR_OUTPUT_RATE_PER_M),
    )
}

#[allow(
    clippy::cast_precision_loss,
    reason = "The historical wire contract calculates bucket prices with binary floating point."
)]
fn bucket_cost(tokens: i64, rate: f64) -> f64 {
    if tokens <= 0 {
        return 0.0;
    }
    ((tokens as f64 / 1_000_000.0) * rate * 1_000_000.0).round_ties_even() / 1_000_000.0
}

fn round_money(value: f64) -> f64 {
    (value * 100.0).round_ties_even() / 100.0
}

fn trusted_root(root: &Path) -> Result<PathBuf, String> {
    let metadata = fs::symlink_metadata(root)
        .map_err(|error| format!("configured run-log root is unavailable: {error}"))?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err("configured run-log root must be a real directory".to_owned());
    }
    fs::canonicalize(root)
        .map_err(|error| format!("configured run-log root is unavailable: {error}"))
}

fn transcript_files(root: &Path) -> Result<Vec<PathBuf>, String> {
    let logs = root.join("larch-logs");
    if !real_directory(&logs)? {
        return Ok(Vec::new());
    }
    let directory = logs.join("implement");
    direct_child_files(&directory, "session-transcript.jsonl")
}

fn summary_files(root: &Path, run_id: Option<&str>) -> Result<Vec<PathBuf>, String> {
    if let Some(run_id) = run_id {
        RunLogSlug::parse(run_id)
            .map_err(|_| "--run-id must be a valid run-log slug".to_owned())?;
    }
    let logs = root.join("larch-logs");
    if !real_directory(&logs)? {
        return Ok(Vec::new());
    }
    if let Some(run_id) = run_id {
        let mut result = Vec::new();
        for skill in ["implement", "design"] {
            let skill_directory = logs.join(skill);
            if !real_directory(&skill_directory)? {
                continue;
            }
            let run_directory = skill_directory.join(run_id);
            if !real_directory(&run_directory)? {
                continue;
            }
            let path = run_directory.join("final-summary.md");
            if is_regular_nonsymlink(&path) {
                result.push(path);
            }
        }
        return Ok(result);
    }
    let mut result = Vec::new();
    let skills =
        fs::read_dir(&logs).map_err(|error| format!("could not read run-log root: {error}"))?;
    for skill in skills {
        let skill = skill.map_err(|error| format!("could not read run-log root: {error}"))?;
        let kind = skill
            .file_type()
            .map_err(|error| format!("could not inspect run-log root: {error}"))?;
        if !kind.is_dir() || kind.is_symlink() {
            continue;
        }
        result.extend(direct_child_files(&skill.path(), "final-summary.md")?);
    }
    result.sort();
    Ok(result)
}

fn direct_child_files(directory: &Path, filename: &str) -> Result<Vec<PathBuf>, String> {
    if !real_directory(directory)? {
        return Ok(Vec::new());
    }
    let entries = fs::read_dir(directory)
        .map_err(|error| format!("could not read run-log directory: {error}"))?;
    let mut result = Vec::new();
    for entry in entries {
        let entry = entry.map_err(|error| format!("could not read run-log directory: {error}"))?;
        let kind = entry
            .file_type()
            .map_err(|error| format!("could not inspect run-log directory: {error}"))?;
        if !kind.is_dir() || kind.is_symlink() {
            continue;
        }
        let candidate = entry.path().join(filename);
        if is_regular_nonsymlink(&candidate) {
            result.push(candidate);
        }
    }
    result.sort();
    Ok(result)
}

fn real_directory(path: &Path) -> Result<bool, String> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            Err("refusing to follow a symlinked run-log directory".to_owned())
        }
        Ok(metadata) => Ok(metadata.is_dir()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(error) => Err(format!("could not inspect run-log directory: {error}")),
    }
}

fn relative_display(root: &Path, path: &Path) -> Result<String, String> {
    let relative = path
        .strip_prefix(root)
        .map_err(|_| "run-log path escaped configured root".to_owned())?;
    Ok(relative.to_string_lossy().replace('\\', "/"))
}

fn is_regular_nonsymlink(path: &Path) -> bool {
    fs::symlink_metadata(path)
        .is_ok_and(|metadata| !metadata.file_type().is_symlink() && metadata.file_type().is_file())
}

fn read_regular_utf8(path: &Path) -> Result<String, String> {
    if !is_regular_nonsymlink(path) {
        return Err("run-log input is not a regular file".to_owned());
    }
    fs::read_to_string(path).map_err(|error| format!("could not read run-log input: {error}"))
}

fn read_regular_utf8_lossy(path: &Path) -> Result<String, String> {
    if !is_regular_nonsymlink(path) {
        return Err("run-log input is not a regular file".to_owned());
    }
    fs::read(path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .map_err(|error| format!("could not read run-log input: {error}"))
}

fn atomic_replace(path: &Path, bytes: &[u8]) -> Result<(), String> {
    if !is_regular_nonsymlink(path) {
        return Err("refusing to replace a non-regular run-log file".to_owned());
    }
    let parent = path
        .parent()
        .ok_or_else(|| "run-log output parent is missing".to_owned())?;
    let parent_metadata = fs::symlink_metadata(parent)
        .map_err(|error| format!("run-log output parent is unavailable: {error}"))?;
    if parent_metadata.file_type().is_symlink() || !parent_metadata.is_dir() {
        return Err("run-log output parent is unsafe".to_owned());
    }
    let permissions = fs::metadata(path)
        .map_err(|error| format!("could not inspect run-log output: {error}"))?
        .permissions();
    let mut temporary = NamedTempFile::new_in(parent)
        .map_err(|error| format!("could not create run-log temporary file: {error}"))?;
    temporary
        .write_all(bytes)
        .and_then(|()| temporary.flush())
        .and_then(|()| temporary.as_file().sync_all())
        .map_err(|error| format!("could not write run-log temporary file: {error}"))?;
    temporary
        .as_file()
        .set_permissions(permissions)
        .map_err(|error| format!("could not set run-log temporary mode: {error}"))?;
    temporary
        .persist(path)
        .map_err(|error| format!("could not atomically replace run-log file: {}", error.error))?;
    Ok(())
}

// Layout migration stays beside the repair sweeps so a second command owner
// cannot be reintroduced.
#[must_use]
pub fn migrate_layout(arguments: &[OsString]) -> ExitCode {
    if arguments.is_empty() {
        return migrate_argument_failure(
            MIGRATE_USAGE,
            "the following arguments are required: phase",
        );
    }
    if matches!(
        arguments.first().and_then(|value| value.to_str()),
        Some("-h" | "--help")
    ) {
        println!("{MIGRATE_HELP}");
        return ExitCode::SUCCESS;
    }
    let Some(phase) = arguments.first().and_then(|value| value.to_str()) else {
        return migrate_argument_failure(MIGRATE_USAGE, "argument phase must be valid UTF-8");
    };
    match phase {
        "plan" => migrate_plan(&arguments[1..]),
        "apply" => migrate_apply(&arguments[1..]),
        "verify" => migrate_verify(&arguments[1..]),
        value => migrate_argument_failure(
            MIGRATE_USAGE,
            &format!(
                "argument phase: invalid choice: '{value}' (choose from 'plan', 'apply', 'verify')"
            ),
        ),
    }
}

fn migrate_plan(arguments: &[OsString]) -> ExitCode {
    if has_help(arguments) {
        println!("{PLAN_USAGE}\n\noptions:\n  -h, --help  show this help message and exit");
        return ExitCode::SUCCESS;
    }
    let parsed = parse(arguments, PLAN_OPTIONS, 0);
    if let Some(error) = parsed.error() {
        return migrate_argument_failure(PLAN_USAGE, &error);
    }
    let required = PLAN_OPTIONS;
    let values = match required_values(&parsed, required, PLAN_USAGE) {
        Ok(values) => values,
        Err(code) => return code,
    };
    let output = PathBuf::from(values["--output"].as_str());
    let work_dir = PathBuf::from(values["--work-dir"].as_str());
    let source_commit = values["--source-commit"].as_str();
    let operator = values["--operator"].as_str();
    let tool_version = values["--tool-version"].as_str();
    let mappings = match live_mappings(&values) {
        Ok(mappings) => mappings,
        Err(error) => return migrate_failure(&error),
    };
    let result = with_s3_store(|runtime, store| {
        runtime.block_on(plan_layout(
            store,
            &mappings,
            &output,
            &work_dir,
            operator,
            tool_version,
            source_commit,
        ))
    });
    match result {
        Ok(plan) => match plan_archive_count(&plan) {
            Ok(count) => {
                let digest = value_string(&plan, "plan_sha256").unwrap_or_default();
                println!("PLAN_PATH={}", output.display());
                println!("PLAN_SHA256={digest}");
                println!("PLANNED_ARCHIVES={count}");
                println!("MIGRATION_PLAN_OK=true");
                ExitCode::SUCCESS
            }
            Err(error) => migrate_failure(&error),
        },
        Err(error) => migrate_failure(&error),
    }
}

fn migrate_apply(arguments: &[OsString]) -> ExitCode {
    if has_help(arguments) {
        println!("{APPLY_USAGE}\n\noptions:\n  -h, --help  show this help message and exit");
        return ExitCode::SUCCESS;
    }
    let parsed = parse_with_flags(arguments, APPLY_OPTIONS, APPLY_FLAGS, 0);
    if let Some(error) = parsed.error() {
        return migrate_argument_failure(APPLY_USAGE, &error);
    }
    let values = match required_values(&parsed, APPLY_OPTIONS, APPLY_USAGE) {
        Ok(values) => values,
        Err(code) => return code,
    };
    if !parsed.flag("--authorize-live-migration") {
        return migrate_failure("live migration apply requires authorization");
    }
    let plan = PathBuf::from(values["--plan"].as_str());
    let report = PathBuf::from(values["--report"].as_str());
    let work_dir = PathBuf::from(values["--work-dir"].as_str());
    match with_s3_store(|runtime, store| {
        runtime.block_on(apply_layout(store, &plan, &report, &work_dir))
    }) {
        Ok(report_payload) => match report_row_count(&report_payload) {
            Ok(count) => {
                println!("REPORT_PATH={}", report.display());
                println!("MIGRATED_ARCHIVES={count}");
                println!("SOURCES_RETAINED=true");
                println!("MIGRATION_APPLY_OK=true");
                ExitCode::SUCCESS
            }
            Err(error) => migrate_failure(&error),
        },
        Err(error) => migrate_failure(&error),
    }
}

fn migrate_verify(arguments: &[OsString]) -> ExitCode {
    if has_help(arguments) {
        println!("{VERIFY_USAGE}\n\noptions:\n  -h, --help  show this help message and exit");
        return ExitCode::SUCCESS;
    }
    let parsed = parse_with_flags(arguments, VERIFY_OPTIONS, VERIFY_FLAGS, 0);
    if let Some(error) = parsed.error() {
        return migrate_argument_failure(VERIFY_USAGE, &error);
    }
    let values = match required_values(&parsed, VERIFY_OPTIONS, VERIFY_USAGE) {
        Ok(values) => values,
        Err(code) => return code,
    };
    if !parsed.flag("--authorize-report-publication") {
        return migrate_failure("final report publication requires authorization");
    }
    let plan = PathBuf::from(values["--plan"].as_str());
    let report = PathBuf::from(values["--report"].as_str());
    let final_report = PathBuf::from(values["--final-report"].as_str());
    let work_dir = PathBuf::from(values["--work-dir"].as_str());
    let publish_report_key = values["--publish-report-key"].as_str();
    match with_s3_store(|runtime, store| {
        runtime.block_on(verify_layout(
            store,
            &plan,
            &report,
            &final_report,
            &work_dir,
            publish_report_key,
        ))
    }) {
        Ok(final_payload) => {
            let result = (|| {
                let digest = value_string(&final_payload, "report_sha256")?;
                let verified = object_field(&final_payload, "independent_verification")?
                    .get("verified_archives")
                    .and_then(Value::as_u64)
                    .ok_or_else(|| "final migration report is invalid".to_owned())?;
                Ok::<_, String>((digest, verified))
            })();
            match result {
                Ok((digest, verified)) => {
                    println!("FINAL_REPORT_PATH={}", final_report.display());
                    println!("FINAL_REPORT_SHA256={digest}");
                    println!("VERIFIED_ARCHIVES={verified}");
                    println!("PUBLISHED_REPORT_KEY={publish_report_key}");
                    println!("MIGRATION_VERIFY_OK=true");
                    ExitCode::SUCCESS
                }
                Err(error) => migrate_failure(&error),
            }
        }
        Err(error) => migrate_failure(&error),
    }
}

fn required_values(
    parsed: &ParsedCommandLine,
    required: &[&str],
    usage: &str,
) -> Result<BTreeMap<String, String>, ExitCode> {
    let missing: Vec<&str> = required
        .iter()
        .copied()
        .filter(|option| parsed.value(option).is_none())
        .collect();
    if !missing.is_empty() {
        return Err(migrate_argument_failure(
            usage,
            &format!(
                "the following arguments are required: {}",
                missing.join(", ")
            ),
        ));
    }
    let mut values = BTreeMap::new();
    for option in required {
        let Some(value) = parsed.value(option).and_then(|value| value.to_str()) else {
            return Err(migrate_argument_failure(
                usage,
                &format!("argument {option} must be valid UTF-8"),
            ));
        };
        values.insert((*option).to_owned(), value.to_owned());
    }
    Ok(values)
}

fn migrate_argument_failure(usage: &str, message: &str) -> ExitCode {
    eprintln!("{usage}");
    eprintln!("cli.py run-log migrate-layout: error: {message}");
    ExitCode::from(2)
}

fn migrate_failure(error: &str) -> ExitCode {
    eprintln!(
        "run-log migrate-layout failed: {}",
        error.replace(['\n', '\r'], " ")
    );
    ExitCode::FAILURE
}

fn with_s3_store<T>(
    operation: impl FnOnce(&LarchRuntime, &S3Storage) -> Result<T, String>,
) -> Result<T, String> {
    let runtime = LarchRuntime::new().map_err(|error| error.to_string())?;
    let environment: HashMap<String, String> = std::env::vars().collect();
    let store = runtime
        .block_on(S3Storage::s3(&environment))
        .map_err(|_| "S3 object-store authentication failed".to_owned())?;
    operation(&runtime, &store)
}

#[derive(Clone)]
struct StorageRoot {
    base: StorageBase,
}

impl StorageRoot {
    fn parse(uri: &str) -> Result<Self, String> {
        parse_storage_base_uri(uri)
            .map(|base| Self { base })
            .map_err(|error| error.to_string())
    }

    fn uri(&self) -> String {
        self.base.uri()
    }

    fn key(&self, relative: &str) -> Result<String, String> {
        let prefix = relative.strip_suffix('/');
        validate_object_relative(prefix.unwrap_or(relative))?;
        Ok(if self.base.prefix.is_empty() {
            relative.to_owned()
        } else {
            format!("{}/{relative}", self.base.prefix)
        })
    }

    fn relative_key(&self, raw: &str) -> Result<String, String> {
        let relative = if self.base.prefix.is_empty() {
            raw
        } else {
            raw.strip_prefix(&format!("{}/", self.base.prefix))
                .ok_or_else(|| "remote object is outside configured storage root".to_owned())?
        };
        validate_object_relative(relative)?;
        Ok(relative.to_owned())
    }
}

#[derive(Clone)]
struct LegacyDescriptor {
    schema: String,
    source_commit: String,
    storage_root: String,
    inventory_key: String,
    inventory_sha256: String,
}

#[derive(Clone)]
struct LayoutMapping {
    client_repo: String,
    source: StorageRoot,
    target: StorageRoot,
    legacy_descriptor: Option<LegacyDescriptor>,
}

impl LayoutMapping {
    fn validate(&self) -> Result<(), String> {
        if validate_client_repo(&self.client_repo).map_err(|error| error.to_string())?
            != self.client_repo
        {
            return Err("client repository identity is not canonical".to_owned());
        }
        let allowed = match self.client_repo.as_str() {
            "larch" => Some(("s3://zhupanov/larch", "s3://zhupanov/larch/larch")),
            "agent-lint" => Some(("s3://zhupanov/agent-lint", "s3://zhupanov/larch/agent-lint")),
            _ => None,
        };
        let Some((source, target)) = allowed else {
            return Err("live mapping is not allowlisted".to_owned());
        };
        if self.source.uri() != source || self.target.uri() != target {
            return Err(format!(
                "live mapping is not allowlisted for {}",
                self.client_repo
            ));
        }
        if self.source.base.scheme != "s3" || self.target.base.scheme != "s3" {
            return Err("live layout migration supports S3 only".to_owned());
        }
        if self.source.base.bucket != self.target.base.bucket {
            return Err("source and target buckets differ".to_owned());
        }
        let source_logs = format!("{}/{RUN_LOG_PREFIX}", self.source.uri());
        let target_logs = format!("{}/{RUN_LOG_PREFIX}", self.target.uri());
        if source_logs == target_logs
            || source_logs.starts_with(&format!("{target_logs}/"))
            || target_logs.starts_with(&format!("{source_logs}/"))
        {
            return Err("source and target run-log prefixes overlap".to_owned());
        }
        if self.client_repo == "larch" && self.legacy_descriptor.is_none() {
            return Err("larch mapping requires a legacy descriptor".to_owned());
        }
        if self.client_repo != "larch" && self.legacy_descriptor.is_some() {
            return Err("only the larch mapping may use a legacy descriptor".to_owned());
        }
        Ok(())
    }
}

fn live_mappings(values: &BTreeMap<String, String>) -> Result<Vec<LayoutMapping>, String> {
    let required = |name| {
        values
            .get(name)
            .cloned()
            .ok_or_else(|| "migration parser lost a required value".to_owned())
    };
    let larch_source = StorageRoot::parse(&required("--larch-source-uri")?)?;
    let larch_target = StorageRoot::parse(&required("--larch-target-uri")?)?;
    let agent_source = StorageRoot::parse(&required("--agent-lint-source-uri")?)?;
    let agent_target = StorageRoot::parse(&required("--agent-lint-target-uri")?)?;
    let descriptor = LegacyDescriptor {
        schema: required("--legacy-schema")?,
        source_commit: required("--legacy-source-commit")?,
        storage_root: larch_source.uri(),
        inventory_key: required("--legacy-inventory-key")?,
        inventory_sha256: required("--legacy-inventory-sha256")?,
    };
    let mappings = vec![
        LayoutMapping {
            client_repo: "larch".to_owned(),
            source: larch_source,
            target: larch_target,
            legacy_descriptor: Some(descriptor),
        },
        LayoutMapping {
            client_repo: "agent-lint".to_owned(),
            source: agent_source,
            target: agent_target,
            legacy_descriptor: None,
        },
    ];
    for mapping in &mappings {
        mapping.validate()?;
    }
    Ok(mappings)
}

#[derive(Clone)]
struct RemoteArchive {
    key: String,
    skill: String,
    run_id: String,
    remote: RemoteObject,
}

async fn list_archives(
    store: &dyn ObjectStore,
    root: &StorageRoot,
) -> Result<BTreeMap<String, RemoteArchive>, String> {
    let prefix = root.key(RUN_LOG_PREFIX)?;
    let mut page_token = None;
    let mut archives = BTreeMap::new();
    let mut local_names = BTreeSet::new();
    loop {
        let page = store
            .list_page(&root.base.bucket, &prefix, page_token.as_deref())
            .await
            .map_err(|error| store_error("list", error))?;
        for remote in page.objects {
            let relative = root.relative_key(&remote.key)?;
            let (skill, run_id) = parse_archive_key(&relative)?;
            if remote.size == 0 || archives.contains_key(&relative) {
                return Err("remote run-log inventory is invalid".to_owned());
            }
            let identity = format!("{}\0{}", skill.to_lowercase(), run_id.to_lowercase());
            if !local_names.insert(identity) {
                return Err("remote run-log inventory is invalid".to_owned());
            }
            archives.insert(
                relative.clone(),
                RemoteArchive {
                    key: relative,
                    skill,
                    run_id,
                    remote,
                },
            );
        }
        page_token = page.next_page_token;
        if page_token.is_none() {
            break;
        }
    }
    Ok(archives)
}

fn parse_archive_key(key: &str) -> Result<(String, String), String> {
    let relative = key
        .strip_prefix(RUN_LOG_PREFIX)
        .ok_or_else(|| "remote run-log inventory is invalid".to_owned())?;
    let mut parts = relative.split('/');
    let (Some(skill), Some(filename), None) = (parts.next(), parts.next(), parts.next()) else {
        return Err("remote run-log inventory is invalid".to_owned());
    };
    let Some(run_id) = filename.strip_suffix(".tar.gz") else {
        return Err("remote run-log inventory is invalid".to_owned());
    };
    if !RunLogSlug::is_valid(skill) || !RunLogSlug::is_valid(run_id) {
        return Err("remote run-log inventory is invalid".to_owned());
    }
    Ok((skill.to_owned(), run_id.to_owned()))
}

fn validate_object_relative(value: &str) -> Result<(), String> {
    if value.is_empty()
        || value.starts_with('/')
        || value.ends_with('/')
        || value.contains('\\')
        || value.contains('\0')
        || value
            .split('/')
            .any(|part| part.is_empty() || matches!(part, "." | ".."))
    {
        return Err("object key is unsafe".to_owned());
    }
    if !value.nfc().eq(value.chars()) {
        return Err("object key is non-canonical".to_owned());
    }
    Ok(())
}

fn store_error(operation: &str, _error: ObjectStoreError) -> String {
    format!("S3 object-store {operation} failed")
}

fn ensure_work_dir(path: &Path) -> Result<(), String> {
    fs::create_dir_all(path)
        .map_err(|error| format!("could not create migration work directory: {error}"))?;
    let metadata = fs::symlink_metadata(path)
        .map_err(|error| format!("could not inspect migration work directory: {error}"))?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err("migration work directory is unsafe".to_owned());
    }
    Ok(())
}

fn safe_snapshot_path(
    work_dir: &Path,
    area: &str,
    client: &str,
    key: &str,
) -> Result<PathBuf, String> {
    validate_object_relative(key)?;
    let (skill, run_id) = parse_archive_key(key)?;
    let base = work_dir.join(area).join(client).join("run-logs");
    let path = base.join(skill).join(format!("{run_id}.tar.gz"));
    if !path.starts_with(&base) {
        return Err("snapshot path escapes its client root".to_owned());
    }
    Ok(path)
}

async fn ensure_snapshot(
    store: &dyn ObjectStore,
    root: &StorageRoot,
    remote: &RemoteArchive,
    destination: &Path,
) -> Result<PathBuf, String> {
    if destination.is_symlink() {
        return Err("snapshot archive path is a symlink".to_owned());
    }
    if is_regular_nonsymlink(destination)
        && fs::metadata(destination)
            .map_err(|error| format!("could not inspect source snapshot: {error}"))?
            .len()
            == remote.remote.size
    {
        return Ok(destination.to_path_buf());
    }
    if destination.exists() {
        return Err("source snapshot has an unexpected type or size".to_owned());
    }
    let parent = destination
        .parent()
        .ok_or_else(|| "snapshot parent is missing".to_owned())?;
    fs::create_dir_all(parent)
        .map_err(|error| format!("could not create snapshot directory: {error}"))?;
    if fs::symlink_metadata(parent)
        .map_err(|error| format!("could not inspect snapshot directory: {error}"))?
        .file_type()
        .is_symlink()
    {
        return Err("snapshot directory is unsafe".to_owned());
    }
    store
        .download(&root.base.bucket, &root.key(&remote.key)?, destination)
        .await
        .map_err(|error| store_error("download", error))?;
    if !is_regular_nonsymlink(destination)
        || fs::metadata(destination)
            .map_err(|error| format!("could not inspect downloaded snapshot: {error}"))?
            .len()
            != remote.remote.size
    {
        return Err("downloaded snapshot size differs from listing".to_owned());
    }
    Ok(destination.to_path_buf())
}

fn sha256_file(path: &Path) -> Result<String, String> {
    if !is_regular_nonsymlink(path) {
        return Err("migration archive is not a regular file".to_owned());
    }
    let mut file = fs::File::open(path)
        .map_err(|error| format!("could not open migration archive: {error}"))?;
    let mut digest = Sha256::new();
    let mut buffer = vec![0_u8; 64 * 1024];
    loop {
        let read = file
            .read(&mut buffer)
            .map_err(|error| format!("could not read migration archive: {error}"))?;
        if read == 0 {
            break;
        }
        digest.update(&buffer[..read]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn canonical_json(value: &Value) -> Result<Vec<u8>, String> {
    let mut encoded = serde_json::to_vec(value)
        .map_err(|error| format!("could not encode migration JSON: {error}"))?;
    encoded.push(b'\n');
    Ok(encoded)
}

fn write_json_atomic(path: &Path, value: &Value) -> Result<(), String> {
    let bytes = canonical_json(value)?;
    let parent = path
        .parent()
        .ok_or_else(|| "migration JSON output parent is missing".to_owned())?;
    fs::create_dir_all(parent)
        .map_err(|error| format!("could not create migration JSON directory: {error}"))?;
    let metadata = fs::symlink_metadata(parent)
        .map_err(|error| format!("could not inspect migration JSON directory: {error}"))?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() || path.is_symlink() {
        return Err("refusing unsafe migration JSON output path".to_owned());
    }
    let mut temporary = NamedTempFile::new_in(parent)
        .map_err(|error| format!("could not create migration JSON temporary: {error}"))?;
    temporary
        .write_all(&bytes)
        .and_then(|()| temporary.flush())
        .and_then(|()| temporary.as_file().sync_all())
        .map_err(|error| format!("could not write migration JSON temporary: {error}"))?;
    temporary
        .persist(path)
        .map_err(|error| format!("could not atomically write migration JSON: {}", error.error))?;
    Ok(())
}

fn read_json(path: &Path) -> Result<Value, String> {
    if !is_regular_nonsymlink(path) {
        return Err("migration JSON path is not a regular file".to_owned());
    }
    let bytes =
        fs::read(path).map_err(|error| format!("migration JSON file is unavailable: {error}"))?;
    let text = std::str::from_utf8(&bytes).map_err(|_| "migration JSON is invalid".to_owned())?;
    parse_unique_json(text, "migration JSON is invalid")
}

fn parse_unique_json(text: &str, error: &str) -> Result<Value, String> {
    let ordered = OrderedJson::parse_unique(text).map_err(|_| error.to_owned())?;
    serde_json::to_value(ordered).map_err(|_| error.to_owned())
}

fn object_field<'a>(value: &'a Value, field: &str) -> Result<&'a Map<String, Value>, String> {
    value
        .as_object()
        .ok_or_else(|| "migration JSON root must be an object".to_owned())?
        .get(field)
        .and_then(Value::as_object)
        .ok_or_else(|| format!("migration JSON object field is invalid: {field}"))
}

fn value_string(value: &Value, field: &str) -> Result<String, String> {
    value
        .as_object()
        .ok_or_else(|| "migration JSON root must be an object".to_owned())?
        .get(field)
        .and_then(Value::as_str)
        .filter(|value| !value.is_empty())
        .map(str::to_owned)
        .ok_or_else(|| format!("migration JSON string field is invalid: {field}"))
}

fn plan_archive_count(plan: &Value) -> Result<usize, String> {
    let mappings = plan
        .as_object()
        .and_then(|value| value.get("mappings"))
        .and_then(Value::as_array)
        .ok_or_else(|| "migration plan mappings are invalid".to_owned())?;
    mappings.iter().try_fold(0_usize, |count, mapping| {
        let rows = mapping
            .as_object()
            .and_then(|value| value.get("archives"))
            .and_then(Value::as_array)
            .ok_or_else(|| "migration plan mapping is invalid".to_owned())?;
        count
            .checked_add(rows.len())
            .ok_or_else(|| "migration plan archive count overflowed".to_owned())
    })
}

fn report_row_count(report: &Value) -> Result<usize, String> {
    report
        .as_object()
        .and_then(|value| value.get("rows"))
        .and_then(Value::as_array)
        .map(Vec::len)
        .ok_or_else(|| "migration report rows are invalid".to_owned())
}

fn now() -> String {
    let current = Utc::now();
    let precision = if current.timestamp_subsec_micros() == 0 {
        SecondsFormat::Secs
    } else {
        SecondsFormat::Micros
    };
    current.to_rfc3339_opts(precision, true)
}

struct ParsedPlan {
    plan_sha256: String,
    source_commit: String,
    tool_version: String,
    mappings: Vec<PlannedMapping>,
}

struct PlannedMapping {
    mapping: LayoutMapping,
    rows: Vec<Value>,
}

fn verified_plan(path: &Path) -> Result<ParsedPlan, String> {
    let value = read_json(path)?;
    let object = value
        .as_object()
        .ok_or_else(|| "migration JSON root must be an object".to_owned())?;
    exact_fields(
        object,
        &[
            "created_at",
            "mappings",
            "operator",
            "plan_sha256",
            "schema",
            "source_commit",
            "tool",
            "tool_version",
        ],
        "migration plan schema is invalid",
    )?;
    if value_at_string(object, "schema")? != PLAN_SCHEMA {
        return Err("migration plan schema is invalid".to_owned());
    }
    let plan_sha256 = value_at_string(object, "plan_sha256")?;
    if !is_lower_hex(&plan_sha256, 64) {
        return Err("migration plan digest is invalid".to_owned());
    }
    let mut unsigned = object.clone();
    unsigned.remove("plan_sha256");
    if sha256_bytes(&canonical_json(&Value::Object(unsigned))?) != plan_sha256 {
        return Err("migration plan digest does not match content".to_owned());
    }
    let source_commit = value_at_string(object, "source_commit")?;
    if !is_lower_hex(&source_commit, 40) {
        return Err("migration plan source commit is invalid".to_owned());
    }
    let tool_version = value_at_string(object, "tool_version")?;
    let mappings = object
        .get("mappings")
        .and_then(Value::as_array)
        .ok_or_else(|| "migration plan mappings are invalid".to_owned())?;
    if mappings.is_empty() {
        return Err("migration plan mappings are invalid".to_owned());
    }
    let mut parsed_mappings = Vec::new();
    let mut clients = BTreeSet::new();
    for raw in mappings {
        let mapping = parse_planned_mapping(raw)?;
        if !clients.insert(mapping.mapping.client_repo.clone()) {
            return Err("migration plan mappings contain duplicate clients".to_owned());
        }
        parsed_mappings.push(mapping);
    }
    Ok(ParsedPlan {
        plan_sha256,
        source_commit,
        tool_version,
        mappings: parsed_mappings,
    })
}

fn parse_planned_mapping(value: &Value) -> Result<PlannedMapping, String> {
    let object = value
        .as_object()
        .ok_or_else(|| "migration plan mapping is invalid".to_owned())?;
    exact_fields(
        object,
        &[
            "archives",
            "client_repo",
            "legacy_descriptor",
            "source_run_logs_uri",
            "source_uri",
            "target_existing_keys",
            "target_run_logs_uri",
            "target_uri",
        ],
        "migration plan mapping is invalid",
    )?;
    let client_repo = value_at_string(object, "client_repo")?;
    let source = StorageRoot::parse(&value_at_string(object, "source_uri")?)?;
    let target = StorageRoot::parse(&value_at_string(object, "target_uri")?)?;
    if value_at_string(object, "source_run_logs_uri")?
        != format!("{}/{RUN_LOG_PREFIX}", source.uri())
        || value_at_string(object, "target_run_logs_uri")?
            != format!("{}/{RUN_LOG_PREFIX}", target.uri())
    {
        return Err("migration plan mapping run-log roots are invalid".to_owned());
    }
    let mapping = LayoutMapping {
        client_repo,
        source,
        target,
        legacy_descriptor: descriptor_from_value(
            object
                .get("legacy_descriptor")
                .ok_or_else(|| "migration plan legacy descriptor is absent".to_owned())?,
        )?,
    };
    mapping.validate()?;
    let target_existing = object
        .get("target_existing_keys")
        .and_then(Value::as_array)
        .ok_or_else(|| "migration plan target inventory is invalid".to_owned())?;
    for key in target_existing {
        let key = key
            .as_str()
            .ok_or_else(|| "migration plan target inventory is invalid".to_owned())?;
        parse_archive_key(key)?;
    }
    let rows = object
        .get("archives")
        .and_then(Value::as_array)
        .ok_or_else(|| "migration plan archive rows are invalid".to_owned())?;
    let mut result = Vec::new();
    let mut source_keys = BTreeSet::new();
    for row in rows {
        validate_plan_row(row)?;
        let source_key = row_string(row, "source_key")?;
        if !source_keys.insert(source_key) {
            return Err("migration plan archive key is invalid".to_owned());
        }
        result.push(row.clone());
    }
    Ok(PlannedMapping {
        mapping,
        rows: result,
    })
}

fn descriptor_from_value(value: &Value) -> Result<Option<LegacyDescriptor>, String> {
    if value.is_null() {
        return Ok(None);
    }
    let object = value
        .as_object()
        .ok_or_else(|| "legacy descriptor is invalid".to_owned())?;
    exact_fields(
        object,
        &[
            "inventory_key",
            "inventory_sha256",
            "schema",
            "source_commit",
            "storage_root",
        ],
        "legacy descriptor fields are invalid",
    )?;
    Ok(Some(LegacyDescriptor {
        schema: value_at_string(object, "schema")?,
        source_commit: value_at_string(object, "source_commit")?,
        storage_root: value_at_string(object, "storage_root")?,
        inventory_key: value_at_string(object, "inventory_key")?,
        inventory_sha256: value_at_string(object, "inventory_sha256")?,
    }))
}

fn validate_plan_row(value: &Value) -> Result<(), String> {
    let row = value
        .as_object()
        .ok_or_else(|| "migration plan archive row is invalid".to_owned())?;
    exact_fields(
        row,
        &[
            "archive_kind",
            "expanded_bytes",
            "member_count",
            "run_id",
            "skill",
            "source_etag",
            "source_key",
            "source_sha256",
            "source_size",
            "source_version",
            "target_key",
            "transformation",
        ],
        "migration plan archive row is invalid",
    )?;
    let kind = row_string(value, "archive_kind")?;
    if !matches!(kind.as_str(), "modern" | "legacy") {
        return Err("migration row archive kind is invalid".to_owned());
    }
    let transformation = row_string(value, "transformation")?;
    if !matches!(
        (kind.as_str(), transformation.as_str()),
        ("modern", "byte-copy") | ("legacy", "normalize-manifest")
    ) {
        return Err("migration row transformation is invalid".to_owned());
    }
    let skill = row_string(value, "skill")?;
    let run_id = row_string(value, "run_id")?;
    let source_key = row_string(value, "source_key")?;
    let target_key = row_string(value, "target_key")?;
    if parse_archive_key(&source_key)? != (skill, run_id)
        || target_key != source_key
        || !is_lower_hex(&row_string(value, "source_sha256")?, 64)
    {
        return Err("migration row identity is invalid".to_owned());
    }
    let _ = row_u64(value, "source_size")?;
    let _ = row_u64(value, "expanded_bytes")?;
    let _ = row_u64(value, "member_count")?;
    for field in ["source_etag", "source_version"] {
        if !value
            .as_object()
            .and_then(|row| row.get(field))
            .is_some_and(|value| value.is_null() || value.is_string())
        {
            return Err(format!("migration row field is invalid: {field}"));
        }
    }
    Ok(())
}

fn row_string(value: &Value, field: &str) -> Result<String, String> {
    value
        .as_object()
        .and_then(|row| row.get(field))
        .and_then(Value::as_str)
        .filter(|value| !value.is_empty())
        .map(str::to_owned)
        .ok_or_else(|| format!("migration row field is invalid: {field}"))
}

fn row_u64(value: &Value, field: &str) -> Result<u64, String> {
    value
        .as_object()
        .and_then(|row| row.get(field))
        .and_then(Value::as_u64)
        .ok_or_else(|| format!("migration row field is invalid: {field}"))
}

async fn validate_frozen_source(
    store: &dyn ObjectStore,
    mapping: &LayoutMapping,
    rows: &[Value],
) -> Result<BTreeMap<String, RemoteArchive>, String> {
    let source = list_archives(store, &mapping.source).await?;
    let planned: BTreeSet<String> = rows
        .iter()
        .map(|row| row_string(row, "source_key"))
        .collect::<Result<_, _>>()?;
    if source.keys().cloned().collect::<BTreeSet<_>>() != planned {
        return Err("source inventory changed after planning".to_owned());
    }
    for row in rows {
        let key = row_string(row, "source_key")?;
        let remote = source
            .get(&key)
            .ok_or_else(|| "source inventory changed after planning".to_owned())?;
        if remote.remote.size != row_u64(row, "source_size")? {
            return Err("source size changed after planning".to_owned());
        }
        for (field, actual) in [
            ("source_etag", remote.remote.etag.as_ref()),
            ("source_version", remote.remote.version.as_ref()),
        ] {
            let expected = row
                .as_object()
                .and_then(|row| row.get(field))
                .ok_or_else(|| format!("migration row field is invalid: {field}"))?;
            if !expected.is_null() && expected.as_str() != actual.map(String::as_str) {
                return Err(format!(
                    "source {} changed after planning",
                    field.trim_start_matches("source_")
                ));
            }
        }
    }
    Ok(source)
}

#[allow(clippy::too_many_lines)] // One interrupted-sweep transaction keeps every durable write visible.
async fn apply_layout(
    store: &dyn ObjectStore,
    plan_path: &Path,
    report_path: &Path,
    work_dir: &Path,
) -> Result<Value, String> {
    let plan = verified_plan(plan_path)?;
    ensure_work_dir(work_dir)?;
    let mut report = load_or_create_report(report_path, &plan)?;
    let mut completed = completed_report_rows(&report)?;
    for planned in &plan.mappings {
        let source = validate_frozen_source(store, &planned.mapping, &planned.rows).await?;
        let target = list_archives(store, &planned.mapping.target).await?;
        let planned_keys: BTreeSet<String> = planned
            .rows
            .iter()
            .map(|row| row_string(row, "target_key"))
            .collect::<Result<_, _>>()?;
        if target.keys().any(|key| !planned_keys.contains(key)) {
            return Err("target contains an unplanned archive".to_owned());
        }
        let inventory = load_legacy_inventory(store, &planned.mapping, work_dir).await?;
        for (index, row) in planned.rows.iter().enumerate() {
            let source_key = row_string(row, "source_key")?;
            let target_key = row_string(row, "target_key")?;
            let remote = source
                .get(&source_key)
                .ok_or_else(|| "source inventory changed after planning".to_owned())?;
            let snapshot_path = safe_snapshot_path(
                work_dir,
                "source",
                &planned.mapping.client_repo,
                &source_key,
            )?;
            let source_snapshot =
                ensure_snapshot(store, &planned.mapping.source, remote, &snapshot_path).await?;
            if sha256_file(&source_snapshot)? != row_string(row, "source_sha256")? {
                return Err("source digest changed after planning".to_owned());
            }
            let (candidate, candidate_result) = candidate_archive(
                row,
                remote,
                &source_snapshot,
                &inventory,
                work_dir,
                &planned.mapping.client_repo,
            )?;
            let status = if target.contains_key(&target_key) {
                "present"
            } else {
                match store
                    .upload_create(
                        &planned.mapping.target.base.bucket,
                        &planned.mapping.target.key(&target_key)?,
                        &candidate,
                    )
                    .await
                {
                    Ok(_) => "created",
                    Err(ObjectStoreError::AlreadyExists) => "present",
                    Err(error) => return Err(store_error("create-only upload", error)),
                }
            };
            let (metadata, target_digest, target_result) = verify_target(
                store,
                &planned.mapping.target,
                &target_key,
                &candidate,
                remote,
                work_dir,
                &planned.mapping.client_repo,
            )
            .await?;
            if candidate_result.member_count != target_result.member_count
                || candidate_result.expanded_size != target_result.expanded_size
            {
                return Err("target materialization differs from candidate".to_owned());
            }
            let mut report_row = row
                .as_object()
                .cloned()
                .ok_or_else(|| "migration plan archive row is invalid".to_owned())?;
            report_row.insert(
                "client_repo".to_owned(),
                Value::String(planned.mapping.client_repo.clone()),
            );
            report_row.insert("error_token".to_owned(), Value::Null);
            report_row.insert("status".to_owned(), Value::String(status.to_owned()));
            report_row.insert(
                "target_etag".to_owned(),
                metadata.etag.map_or(Value::Null, Value::String),
            );
            report_row.insert(
                "target_expanded_bytes".to_owned(),
                Value::from(target_result.expanded_size),
            );
            report_row.insert(
                "target_member_count".to_owned(),
                Value::from(target_result.member_count),
            );
            report_row.insert("target_sha256".to_owned(), Value::String(target_digest));
            report_row.insert("target_size".to_owned(), Value::from(metadata.size));
            report_row.insert(
                "target_version".to_owned(),
                metadata.version.map_or(Value::Null, Value::String),
            );
            report_row.insert("verified".to_owned(), Value::Bool(true));
            completed.insert(
                (planned.mapping.client_repo.clone(), source_key),
                Value::Object(report_row),
            );
            update_partial_report(&mut report, &completed, None)?;
            write_json_atomic(report_path, &report)?;
            if (index + 1) % 100 == 0 {
                eprintln!(
                    "apply {}: verified {}/{}",
                    planned.mapping.client_repo,
                    index + 1,
                    planned.rows.len()
                );
            }
        }
    }
    let expected = plan
        .mappings
        .iter()
        .map(|mapping| mapping.rows.len())
        .sum::<usize>();
    if completed.len() != expected {
        return Err("migration report is incomplete".to_owned());
    }
    update_partial_report(&mut report, &completed, Some(now()))?;
    let rows = report
        .as_object()
        .and_then(|report| report.get("rows"))
        .and_then(Value::as_array)
        .ok_or_else(|| "migration report rows are invalid".to_owned())?
        .clone();
    let aggregates = report_aggregates(&rows)?;
    report
        .as_object_mut()
        .ok_or_else(|| "migration report is invalid".to_owned())?
        .insert("aggregates".to_owned(), aggregates);
    write_json_atomic(report_path, &report)?;
    Ok(report)
}

fn load_or_create_report(path: &Path, plan: &ParsedPlan) -> Result<Value, String> {
    if !path.exists() {
        return Ok(json_object([
            ("completed_at", Value::Null),
            ("plan_sha256", Value::String(plan.plan_sha256.clone())),
            ("rows", Value::Array(Vec::new())),
            ("schema", Value::String(REPORT_SCHEMA.to_owned())),
            ("source_commit", Value::String(plan.source_commit.clone())),
            ("source_objects_retained", Value::Bool(true)),
            ("started_at", Value::String(now())),
            ("target_writes_create_only", Value::Bool(true)),
            ("tool_version", Value::String(plan.tool_version.clone())),
        ]));
    }
    let report = read_json(path)?;
    let object = report
        .as_object()
        .ok_or_else(|| "existing migration report is incompatible".to_owned())?;
    if object.get("schema") != Some(&Value::String(REPORT_SCHEMA.to_owned()))
        || object.get("plan_sha256") != Some(&Value::String(plan.plan_sha256.clone()))
        || !object.get("rows").is_some_and(Value::is_array)
    {
        return Err("existing migration report is incompatible".to_owned());
    }
    Ok(report)
}

fn completed_report_rows(report: &Value) -> Result<BTreeMap<(String, String), Value>, String> {
    let rows = report
        .as_object()
        .and_then(|report| report.get("rows"))
        .and_then(Value::as_array)
        .ok_or_else(|| "existing migration report rows are invalid".to_owned())?;
    let mut result = BTreeMap::new();
    for row in rows {
        let client = row_string(row, "client_repo")?;
        let source_key = row_string(row, "source_key")?;
        if result.insert((client, source_key), row.clone()).is_some() {
            return Err("existing migration report has duplicate rows".to_owned());
        }
    }
    Ok(result)
}

fn update_partial_report(
    report: &mut Value,
    completed: &BTreeMap<(String, String), Value>,
    completed_at: Option<String>,
) -> Result<(), String> {
    let object = report
        .as_object_mut()
        .ok_or_else(|| "migration report is invalid".to_owned())?;
    object.insert(
        "rows".to_owned(),
        Value::Array(completed.values().cloned().collect()),
    );
    object.insert(
        "completed_at".to_owned(),
        completed_at.map_or(Value::Null, Value::String),
    );
    Ok(())
}

fn candidate_archive(
    row: &Value,
    remote: &RemoteArchive,
    source_archive: &Path,
    inventory: &LegacyInventory,
    work_dir: &Path,
    client_repo: &str,
) -> Result<(PathBuf, MaterializedCheck), String> {
    let kind = row_string(row, "archive_kind")?;
    if kind == "modern" {
        return Ok((
            source_archive.to_path_buf(),
            materialize_modern_for_check(source_archive, remote, work_dir)?,
        ));
    }
    if kind != "legacy" {
        return Err("migration row archive kind is invalid".to_owned());
    }
    let legacy = inventory
        .archive_for(&remote.key)
        .ok_or_else(|| "legacy migration row is absent from inventory".to_owned())?;
    let candidate_parent = work_dir
        .join("candidates")
        .join(client_repo)
        .join("run-logs")
        .join(&remote.skill);
    fs::create_dir_all(&candidate_parent)
        .map_err(|error| format!("could not create legacy candidate directory: {error}"))?;
    if fs::symlink_metadata(&candidate_parent)
        .map_err(|error| format!("could not inspect legacy candidate directory: {error}"))?
        .file_type()
        .is_symlink()
    {
        return Err("legacy candidate directory is unsafe".to_owned());
    }
    let candidate = candidate_parent.join(format!("{}.tar.gz", remote.run_id));
    if candidate.exists() {
        if !is_regular_nonsymlink(&candidate) {
            return Err("legacy candidate archive is unsafe".to_owned());
        }
    } else {
        let temporary = TempDir::new_in(work_dir)
            .map_err(|error| format!("could not create legacy conversion directory: {error}"))?;
        let staging = temporary.path().join("staging");
        materialize_legacy_to_staging(source_archive, legacy, &staging)?;
        let created = run_lifecycle::archive_run_directory(
            &staging,
            &candidate_parent,
            &remote.skill,
            &remote.run_id,
        )
        .map_err(|error| error.to_string())?;
        let created_path = fs::canonicalize(&created.archive_path)
            .map_err(|error| format!("could not resolve legacy candidate archive: {error}"))?;
        let expected_path = fs::canonicalize(&candidate)
            .map_err(|error| format!("could not resolve legacy candidate archive: {error}"))?;
        if created_path != expected_path {
            return Err("legacy candidate path is unexpected".to_owned());
        }
    }
    let check = materialize_modern_for_check(&candidate, remote, work_dir)?;
    Ok((candidate, check))
}

async fn verify_target(
    store: &dyn ObjectStore,
    target: &StorageRoot,
    key: &str,
    candidate: &Path,
    remote: &RemoteArchive,
    work_dir: &Path,
    client_repo: &str,
) -> Result<(RemoteObject, String, MaterializedCheck), String> {
    let metadata = store
        .metadata(&target.base.bucket, &target.key(key)?)
        .await
        .map_err(|error| store_error("metadata", error))?;
    let candidate_metadata = fs::metadata(candidate)
        .map_err(|error| format!("could not inspect migration candidate: {error}"))?;
    let candidate_digest = sha256_file(candidate)?;
    if metadata.size != candidate_metadata.len() {
        return Err("target size differs from candidate".to_owned());
    }
    let destination = safe_snapshot_path(work_dir, "target", client_repo, key)?;
    let downloaded = download_fresh(store, target, key, &destination, metadata.size).await?;
    let digest = sha256_file(&downloaded)?;
    if digest != candidate_digest {
        return Err("target digest differs from candidate".to_owned());
    }
    let check = materialize_modern_for_check(&downloaded, remote, work_dir)?;
    Ok((metadata, digest, check))
}

async fn download_fresh(
    store: &dyn ObjectStore,
    root: &StorageRoot,
    key: &str,
    destination: &Path,
    expected_size: u64,
) -> Result<PathBuf, String> {
    if destination.exists() {
        if !is_regular_nonsymlink(destination) {
            return Err("download snapshot path is unsafe".to_owned());
        }
        fs::remove_file(destination)
            .map_err(|error| format!("could not reset target snapshot: {error}"))?;
    }
    let parent = destination
        .parent()
        .ok_or_else(|| "target snapshot parent is missing".to_owned())?;
    fs::create_dir_all(parent)
        .map_err(|error| format!("could not create target snapshot directory: {error}"))?;
    store
        .download(&root.base.bucket, &root.key(key)?, destination)
        .await
        .map_err(|error| store_error("download", error))?;
    if !is_regular_nonsymlink(destination)
        || fs::metadata(destination)
            .map_err(|error| format!("could not inspect target snapshot: {error}"))?
            .len()
            != expected_size
    {
        return Err("downloaded target size differs from metadata".to_owned());
    }
    Ok(destination.to_path_buf())
}

fn report_aggregates(rows: &[Value]) -> Result<Value, String> {
    let mut by_client: BTreeMap<String, BTreeMap<String, u64>> = BTreeMap::new();
    let mut by_client_skill: BTreeMap<String, BTreeMap<String, BTreeMap<String, u64>>> =
        BTreeMap::new();
    let mut by_kind: BTreeMap<String, BTreeMap<String, u64>> = BTreeMap::new();
    let mut by_status: BTreeMap<String, u64> = BTreeMap::new();
    for row in rows {
        let client = row_string(row, "client_repo")?;
        let skill = row_string(row, "skill")?;
        let kind = row_string(row, "archive_kind")?;
        let status = row_string(row, "status")?;
        let source_size = row_u64(row, "source_size")?;
        let target_size = row_u64(row, "target_size")?;
        update_aggregate(
            by_client.entry(client.clone()).or_default(),
            source_size,
            target_size,
        )?;
        update_aggregate(
            by_client_skill
                .entry(client)
                .or_default()
                .entry(skill)
                .or_default(),
            source_size,
            target_size,
        )?;
        update_aggregate(by_kind.entry(kind).or_default(), source_size, target_size)?;
        *by_status.entry(status).or_default() += 1;
    }
    Ok(json_object([
        ("by_archive_kind", aggregate_map_value(by_kind)),
        ("by_client", aggregate_map_value(by_client)),
        (
            "by_client_and_skill",
            nested_aggregate_map_value(by_client_skill),
        ),
        (
            "by_status",
            Value::Object(
                by_status
                    .into_iter()
                    .map(|(key, value)| (key, Value::from(value)))
                    .collect(),
            ),
        ),
        ("total_archives", Value::from(rows.len())),
    ]))
}

fn update_aggregate(
    values: &mut BTreeMap<String, u64>,
    source: u64,
    target: u64,
) -> Result<(), String> {
    for (field, value) in [
        ("archives", 1),
        ("source_bytes", source),
        ("target_bytes", target),
    ] {
        *values.entry(field.to_owned()).or_default() = values
            .get(field)
            .copied()
            .unwrap_or_default()
            .checked_add(value)
            .ok_or_else(|| "migration aggregate overflowed".to_owned())?;
    }
    Ok(())
}

fn aggregate_map_value(values: BTreeMap<String, BTreeMap<String, u64>>) -> Value {
    Value::Object(
        values
            .into_iter()
            .map(|(name, row)| {
                (
                    name,
                    Value::Object(
                        row.into_iter()
                            .map(|(field, value)| (field, Value::from(value)))
                            .collect(),
                    ),
                )
            })
            .collect(),
    )
}

fn nested_aggregate_map_value(
    values: BTreeMap<String, BTreeMap<String, BTreeMap<String, u64>>>,
) -> Value {
    Value::Object(
        values
            .into_iter()
            .map(|(client, skills)| (client, aggregate_map_value(skills)))
            .collect(),
    )
}

#[allow(
    clippy::case_sensitive_file_extension_comparisons,
    clippy::too_many_lines,
    reason = "The immutable publication key intentionally requires a lowercase .json suffix."
)]
async fn verify_layout(
    store: &dyn ObjectStore,
    plan_path: &Path,
    report_path: &Path,
    final_report_path: &Path,
    work_dir: &Path,
    publish_report_key: &str,
) -> Result<Value, String> {
    if !publish_report_key.starts_with("migration-reports/")
        || publish_report_key.ends_with('/')
        || !publish_report_key.ends_with(".json")
    {
        return Err("published report key is invalid".to_owned());
    }
    validate_object_relative(publish_report_key)?;
    let plan = verified_plan(plan_path)?;
    ensure_work_dir(work_dir)?;
    let report = read_json(report_path)?;
    let report_object = report
        .as_object()
        .ok_or_else(|| "migration report is incomplete or incompatible".to_owned())?;
    if report_object.get("schema") != Some(&Value::String(REPORT_SCHEMA.to_owned()))
        || report_object.get("plan_sha256") != Some(&Value::String(plan.plan_sha256.clone()))
        || report_object.get("completed_at").is_none_or(Value::is_null)
        || !report_object.get("rows").is_some_and(Value::is_array)
    {
        return Err("migration report is incomplete or incompatible".to_owned());
    }
    let report_rows = completed_report_rows(&report)?;
    let mut verified_rows = Vec::new();
    let mut publication_root = None;
    for planned in &plan.mappings {
        let source = validate_frozen_source(store, &planned.mapping, &planned.rows).await?;
        let target = list_archives(store, &planned.mapping.target).await?;
        let planned_keys: BTreeSet<String> = planned
            .rows
            .iter()
            .map(|row| row_string(row, "target_key"))
            .collect::<Result<_, _>>()?;
        if target.keys().cloned().collect::<BTreeSet<_>>() != planned_keys {
            return Err("target inventory differs from plan".to_owned());
        }
        if planned.mapping.client_repo == "larch" {
            publication_root = Some(planned.mapping.target.clone());
        }
        let inventory = load_legacy_inventory(store, &planned.mapping, work_dir).await?;
        for (index, row) in planned.rows.iter().enumerate() {
            let source_key = row_string(row, "source_key")?;
            let target_key = row_string(row, "target_key")?;
            let report_row = report_rows
                .get(&(planned.mapping.client_repo.clone(), source_key.clone()))
                .ok_or_else(|| "migration report lacks a verified row".to_owned())?;
            if report_row.as_object().and_then(|row| row.get("verified"))
                != Some(&Value::Bool(true))
            {
                return Err("migration report lacks a verified row".to_owned());
            }
            let remote = target
                .get(&target_key)
                .ok_or_else(|| "target inventory differs from plan".to_owned())?;
            let expected_size = row_u64(report_row, "target_size")?;
            if remote.remote.size != expected_size {
                return Err("target size differs from migration report".to_owned());
            }
            let destination = safe_snapshot_path(
                work_dir,
                "verify-target",
                &planned.mapping.client_repo,
                &target_key,
            )?;
            let snapshot = download_fresh(
                store,
                &planned.mapping.target,
                &target_key,
                &destination,
                remote.remote.size,
            )
            .await?;
            let target_digest = sha256_file(&snapshot)?;
            if target_digest != row_string(report_row, "target_sha256")? {
                return Err("target digest differs from migration report".to_owned());
            }
            let source_remote = source
                .get(&source_key)
                .ok_or_else(|| "source inventory changed after planning".to_owned())?;
            let check = materialize_modern_for_check(&snapshot, source_remote, work_dir)?;
            if row_string(row, "archive_kind")? == "legacy" {
                let legacy = inventory
                    .archive_for(&source_key)
                    .ok_or_else(|| "legacy target is absent from pinned inventory".to_owned())?;
                verify_legacy_target(&snapshot, source_remote, legacy, work_dir)?;
            } else if target_digest != row_string(row, "source_sha256")? {
                return Err("modern target is not byte-identical to source".to_owned());
            }
            if check.member_count as u64 != row_u64(report_row, "target_member_count")?
                || check.expanded_size != row_u64(report_row, "target_expanded_bytes")?
            {
                return Err("target materialization differs from migration report".to_owned());
            }
            verified_rows.push(json_object([
                (
                    "archive_kind",
                    Value::String(row_string(row, "archive_kind")?),
                ),
                (
                    "client_repo",
                    Value::String(planned.mapping.client_repo.clone()),
                ),
                ("run_id", Value::String(row_string(row, "run_id")?)),
                ("skill", Value::String(row_string(row, "skill")?)),
                ("source_key", Value::String(source_key)),
                ("target_key", Value::String(target_key)),
                ("target_sha256", Value::String(target_digest)),
                ("target_size", Value::from(remote.remote.size)),
                ("verified", Value::Bool(true)),
            ]));
            if (index + 1) % 100 == 0 {
                eprintln!(
                    "verify {}: validated {}/{}",
                    planned.mapping.client_repo,
                    index + 1,
                    planned.rows.len()
                );
            }
        }
    }
    if verified_rows.len()
        != plan
            .mappings
            .iter()
            .map(|mapping| mapping.rows.len())
            .sum::<usize>()
    {
        return Err("independent verification is incomplete".to_owned());
    }
    let final_unsigned = json_object([
        (
            "apply_completed_at",
            report_object
                .get("completed_at")
                .cloned()
                .ok_or_else(|| "migration report is incomplete or incompatible".to_owned())?,
        ),
        (
            "independent_verification",
            json_object([
                ("completed_at", Value::String(now())),
                ("rows", Value::Array(verified_rows)),
                ("target_manifestless_archives", Value::from(0)),
                (
                    "verified_archives",
                    Value::from(
                        plan.mappings
                            .iter()
                            .map(|mapping| mapping.rows.len())
                            .sum::<usize>(),
                    ),
                ),
            ]),
        ),
        (
            "migration_aggregates",
            report_object
                .get("aggregates")
                .cloned()
                .unwrap_or(Value::Null),
        ),
        (
            "migration_plan_sha256",
            Value::String(plan.plan_sha256.clone()),
        ),
        ("schema", Value::String(FINAL_REPORT_SCHEMA.to_owned())),
        ("source_commit", Value::String(plan.source_commit.clone())),
        ("source_objects_retained", Value::Bool(true)),
        ("target_writes_create_only", Value::Bool(true)),
        ("tool_version", Value::String(plan.tool_version.clone())),
    ]);
    let final_report = self_hashed(&final_unsigned, "report_sha256")?;
    write_json_atomic(final_report_path, &final_report)?;
    let publication_root =
        publication_root.ok_or_else(|| "larch target store is absent".to_owned())?;
    publish_final_report(
        store,
        &publication_root,
        publish_report_key,
        final_report_path,
        work_dir,
    )
    .await?;
    Ok(final_report)
}

fn verify_legacy_target(
    archive: &Path,
    remote: &RemoteArchive,
    legacy: &LegacyArchive,
    work_dir: &Path,
) -> Result<(), String> {
    let temporary = TempDir::new_in(work_dir).map_err(|error| {
        format!("could not create legacy target verification directory: {error}")
    })?;
    let run_dir = temporary.path().join(&remote.run_id);
    run_lifecycle::materialize_run_archive(archive, &run_dir, &remote.skill, &remote.run_id)
        .map_err(|error| error.to_string())?;
    let mut actual = BTreeMap::new();
    collect_regular_files(&run_dir, &run_dir, &mut actual)?;
    actual.remove("archive-manifest.json");
    if actual.len() != legacy.members.len() {
        return Err("legacy target members differ from inventory".to_owned());
    }
    for member in &legacy.members {
        let path = actual
            .get(&member.path)
            .ok_or_else(|| "legacy target members differ from inventory".to_owned())?;
        let metadata = fs::symlink_metadata(path)
            .map_err(|error| format!("could not inspect legacy target member: {error}"))?;
        if metadata.len() != member.size
            || sha256_file(path)? != member.sha256
            || unix_mode(&metadata) != member.mode
        {
            return Err("legacy target member metadata differs from inventory".to_owned());
        }
    }
    Ok(())
}

fn collect_regular_files(
    root: &Path,
    directory: &Path,
    files: &mut BTreeMap<String, PathBuf>,
) -> Result<(), String> {
    for entry in fs::read_dir(directory)
        .map_err(|error| format!("could not inspect legacy target: {error}"))?
    {
        let entry = entry.map_err(|error| format!("could not inspect legacy target: {error}"))?;
        let path = entry.path();
        let metadata = fs::symlink_metadata(&path)
            .map_err(|error| format!("could not inspect legacy target: {error}"))?;
        if metadata.file_type().is_symlink() {
            return Err("legacy target contains an unsupported member type".to_owned());
        }
        if metadata.is_dir() {
            collect_regular_files(root, &path, files)?;
        } else if metadata.is_file() {
            let relative = path
                .strip_prefix(root)
                .map_err(|_| "legacy target path escaped verification root".to_owned())?
                .to_str()
                .ok_or_else(|| "legacy target member path is invalid".to_owned())?
                .replace('\\', "/");
            if files.insert(relative, path).is_some() {
                return Err("legacy target members are ambiguous".to_owned());
            }
        } else {
            return Err("legacy target contains an unsupported member type".to_owned());
        }
    }
    Ok(())
}

#[cfg(unix)]
fn unix_mode(metadata: &fs::Metadata) -> u32 {
    use std::os::unix::fs::PermissionsExt as _;

    metadata.permissions().mode() & 0o777
}

#[cfg(not(unix))]
fn unix_mode(_metadata: &fs::Metadata) -> u32 {
    0o644
}

async fn publish_final_report(
    store: &dyn ObjectStore,
    target: &StorageRoot,
    key: &str,
    report: &Path,
    work_dir: &Path,
) -> Result<(), String> {
    let expected_size = fs::metadata(report)
        .map_err(|error| format!("could not inspect final migration report: {error}"))?
        .len();
    let remote = match store
        .upload_create(&target.base.bucket, &target.key(key)?, report)
        .await
    {
        Ok(remote) => remote,
        Err(ObjectStoreError::AlreadyExists) => store
            .metadata(&target.base.bucket, &target.key(key)?)
            .await
            .map_err(|error| store_error("metadata", error))?,
        Err(error) => return Err(store_error("create-only upload", error)),
    };
    if remote.size != expected_size {
        return Err("published report size differs from local report".to_owned());
    }
    let downloaded = work_dir.join("published-report.json");
    let downloaded = download_fresh(store, target, key, &downloaded, expected_size).await?;
    if sha256_file(&downloaded)? != sha256_file(report)? {
        return Err("published report digest differs from local report".to_owned());
    }
    Ok(())
}

#[derive(Clone)]
struct LegacyMember {
    path: String,
    size: u64,
    sha256: String,
    mode: u32,
}

#[derive(Clone)]
struct LegacyArchive {
    archive_size: u64,
    archive_sha256: String,
    member_count: usize,
    expanded_size: u64,
    members: Vec<LegacyMember>,
}

#[derive(Default)]
struct LegacyInventory {
    archives: BTreeMap<String, LegacyArchive>,
}

impl LegacyInventory {
    fn archive_for(&self, key: &str) -> Option<&LegacyArchive> {
        self.archives.get(key)
    }
}

#[allow(clippy::too_many_lines)] // Plan construction keeps frozen inventory checks in one audit path.
async fn plan_layout(
    store: &dyn ObjectStore,
    mappings: &[LayoutMapping],
    output: &Path,
    work_dir: &Path,
    operator: &str,
    tool_version: &str,
    source_commit: &str,
) -> Result<Value, String> {
    if operator.trim().is_empty() || tool_version.trim().is_empty() {
        return Err("operator and tool version are required".to_owned());
    }
    if !is_lower_hex(source_commit, 40) {
        return Err("source commit must be lowercase 40-hex".to_owned());
    }
    ensure_work_dir(work_dir)?;
    let mut rendered_mappings = Vec::new();
    for mapping in mappings {
        mapping.validate()?;
        let source = list_archives(store, &mapping.source).await?;
        let target = list_archives(store, &mapping.target).await?;
        if target.keys().any(|key| !source.contains_key(key)) {
            return Err("target contains key(s) absent from source".to_owned());
        }
        let inventory = load_legacy_inventory(store, mapping, work_dir).await?;
        if inventory
            .archives
            .keys()
            .any(|key| !source.contains_key(key))
        {
            return Err("legacy inventory has missing source archive(s)".to_owned());
        }
        let mut rows = Vec::new();
        for (index, archive) in source.values().enumerate() {
            let snapshot =
                safe_snapshot_path(work_dir, "source", &mapping.client_repo, &archive.key)?;
            let snapshot = ensure_snapshot(store, &mapping.source, archive, &snapshot).await?;
            let source_digest = sha256_file(&snapshot)?;
            let (kind, transformation, materialized) = match inventory.archive_for(&archive.key) {
                Some(legacy) => (
                    "legacy",
                    "normalize-manifest",
                    materialize_legacy_for_check(&snapshot, archive, legacy, work_dir)?,
                ),
                None => (
                    "modern",
                    "byte-copy",
                    materialize_modern_for_check(&snapshot, archive, work_dir)?,
                ),
            };
            rows.push(json_object([
                ("archive_kind", Value::String(kind.to_owned())),
                ("expanded_bytes", Value::from(materialized.expanded_size)),
                ("member_count", Value::from(materialized.member_count)),
                ("run_id", Value::String(archive.run_id.clone())),
                ("skill", Value::String(archive.skill.clone())),
                (
                    "source_etag",
                    archive
                        .remote
                        .etag
                        .clone()
                        .map_or(Value::Null, Value::String),
                ),
                ("source_key", Value::String(archive.key.clone())),
                ("source_sha256", Value::String(source_digest)),
                ("source_size", Value::from(archive.remote.size)),
                (
                    "source_version",
                    archive
                        .remote
                        .version
                        .clone()
                        .map_or(Value::Null, Value::String),
                ),
                ("target_key", Value::String(archive.key.clone())),
                ("transformation", Value::String(transformation.to_owned())),
            ]));
            if (index + 1) % 100 == 0 {
                eprintln!(
                    "plan {}: validated {}/{}",
                    mapping.client_repo,
                    index + 1,
                    source.len()
                );
            }
        }
        rendered_mappings.push(json_object([
            ("archives", Value::Array(rows)),
            ("client_repo", Value::String(mapping.client_repo.clone())),
            (
                "legacy_descriptor",
                descriptor_value(mapping.legacy_descriptor.as_ref()),
            ),
            (
                "source_run_logs_uri",
                Value::String(format!("{}/{RUN_LOG_PREFIX}", mapping.source.uri())),
            ),
            ("source_uri", Value::String(mapping.source.uri())),
            (
                "target_existing_keys",
                Value::Array(target.keys().cloned().map(Value::String).collect()),
            ),
            (
                "target_run_logs_uri",
                Value::String(format!("{}/{RUN_LOG_PREFIX}", mapping.target.uri())),
            ),
            ("target_uri", Value::String(mapping.target.uri())),
        ]));
    }
    let unsigned = json_object([
        ("created_at", Value::String(now())),
        ("mappings", Value::Array(rendered_mappings)),
        ("operator", Value::String(operator.trim().to_owned())),
        ("schema", Value::String(PLAN_SCHEMA.to_owned())),
        ("source_commit", Value::String(source_commit.to_owned())),
        ("tool", Value::String("larch".to_owned())),
        (
            "tool_version",
            Value::String(tool_version.trim().to_owned()),
        ),
    ]);
    let plan = self_hashed(&unsigned, "plan_sha256")?;
    write_json_atomic(output, &plan)?;
    Ok(plan)
}

fn descriptor_value(descriptor: Option<&LegacyDescriptor>) -> Value {
    descriptor.map_or(Value::Null, |descriptor| {
        json_object([
            (
                "inventory_key",
                Value::String(descriptor.inventory_key.clone()),
            ),
            (
                "inventory_sha256",
                Value::String(descriptor.inventory_sha256.clone()),
            ),
            ("schema", Value::String(descriptor.schema.clone())),
            (
                "source_commit",
                Value::String(descriptor.source_commit.clone()),
            ),
            (
                "storage_root",
                Value::String(descriptor.storage_root.clone()),
            ),
        ])
    })
}

fn json_object<const N: usize>(entries: [(&str, Value); N]) -> Value {
    Value::Object(
        entries
            .into_iter()
            .map(|(key, value)| (key.to_owned(), value))
            .collect(),
    )
}

fn self_hashed(value: &Value, field: &str) -> Result<Value, String> {
    let mut object = value
        .as_object()
        .cloned()
        .ok_or_else(|| "self-hashed migration payload is not an object".to_owned())?;
    object.remove(field);
    let digest = Sha256::digest(&canonical_json(&Value::Object(object.clone()))?);
    object.insert(field.to_owned(), Value::String(format!("{digest:x}")));
    Ok(Value::Object(object))
}

fn is_lower_hex(value: &str, length: usize) -> bool {
    value.len() == length
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || matches!(byte, b'a'..=b'f'))
}

struct MaterializedCheck {
    member_count: usize,
    expanded_size: u64,
}

fn materialize_modern_for_check(
    archive: &Path,
    remote: &RemoteArchive,
    work_dir: &Path,
) -> Result<MaterializedCheck, String> {
    let temporary = TempDir::new_in(work_dir)
        .map_err(|error| format!("could not create migration validation directory: {error}"))?;
    let result = run_lifecycle::materialize_run_archive(
        archive,
        &temporary.path().join(&remote.run_id),
        &remote.skill,
        &remote.run_id,
    )
    .map_err(|error| error.to_string())?;
    Ok(MaterializedCheck {
        member_count: result.member_count,
        expanded_size: result.expanded_size,
    })
}

async fn load_legacy_inventory(
    store: &dyn ObjectStore,
    mapping: &LayoutMapping,
    work_dir: &Path,
) -> Result<LegacyInventory, String> {
    let Some(descriptor) = mapping.legacy_descriptor.as_ref() else {
        return Ok(LegacyInventory::default());
    };
    if descriptor.storage_root != mapping.source.uri()
        || !is_lower_hex(&descriptor.source_commit, 40)
        || !is_lower_hex(&descriptor.inventory_sha256, 64)
    {
        return Err("legacy migration descriptor is invalid".to_owned());
    }
    validate_object_relative(&descriptor.inventory_key)?;
    let directory = work_dir.join("inventory").join(&mapping.client_repo);
    fs::create_dir_all(&directory)
        .map_err(|error| format!("could not create migration inventory directory: {error}"))?;
    if fs::symlink_metadata(&directory)
        .map_err(|error| format!("could not inspect migration inventory directory: {error}"))?
        .file_type()
        .is_symlink()
    {
        return Err("migration inventory directory is unsafe".to_owned());
    }
    let temporary = NamedTempFile::new_in(&directory)
        .map_err(|error| format!("could not create migration inventory temporary: {error}"))?;
    let inventory_path = temporary.path().to_path_buf();
    temporary
        .close()
        .map_err(|error| format!("could not prepare migration inventory path: {error}"))?;
    let result = async {
        store
            .download(
                &mapping.source.base.bucket,
                &mapping.source.key(&descriptor.inventory_key)?,
                &inventory_path,
            )
            .await
            .map_err(|error| store_error("download", error))?;
        let metadata = fs::symlink_metadata(&inventory_path)
            .map_err(|error| format!("could not inspect migration inventory: {error}"))?;
        if !metadata.file_type().is_file() || metadata.len() > MAX_INVENTORY_BYTES {
            return Err("migration inventory exceeds byte limit".to_owned());
        }
        let encoded = fs::read(&inventory_path)
            .map_err(|error| format!("could not read migration inventory: {error}"))?;
        if sha256_bytes(&encoded) != descriptor.inventory_sha256 {
            return Err("migration inventory digest does not match repository pin".to_owned());
        }
        parse_legacy_inventory(&encoded, descriptor, &mapping.source)
    }
    .await;
    let _ = fs::remove_file(&inventory_path);
    result
}

#[derive(Clone)]
struct InventoryArchiveRow {
    object_key: String,
    relative_key: String,
    kind: String,
    skill: Option<String>,
    run_id: Option<String>,
    archive_bytes: u64,
    sha256: String,
    member_count: usize,
    uncompressed_bytes: u64,
}

#[allow(clippy::too_many_lines)] // The strict legacy schema is safest when cross-checks remain adjacent.
fn parse_legacy_inventory(
    encoded: &[u8],
    descriptor: &LegacyDescriptor,
    root: &StorageRoot,
) -> Result<LegacyInventory, String> {
    if encoded.len() as u64 > MAX_INVENTORY_BYTES {
        return Err("migration inventory exceeds byte limit".to_owned());
    }
    let text = std::str::from_utf8(encoded)
        .map_err(|_| "migration inventory is not valid UTF-8 JSON".to_owned())?;
    let value = parse_unique_json(text, "migration inventory is not valid UTF-8 JSON")?;
    let object = value
        .as_object()
        .ok_or_else(|| "migration inventory must be an object".to_owned())?;
    exact_fields(
        object,
        &[
            "archives",
            "schema",
            "source_commit",
            "source_files",
            "storage_root",
            "totals",
        ],
        "migration inventory has invalid fields",
    )?;
    if value_at_string(object, "schema")? != descriptor.schema
        || value_at_string(object, "source_commit")? != descriptor.source_commit
        || value_at_string(object, "storage_root")? != descriptor.storage_root
        || descriptor.storage_root != root.uri()
    {
        return Err("migration inventory is not pinned by the repository".to_owned());
    }
    let raw_archives = object
        .get("archives")
        .and_then(Value::as_array)
        .ok_or_else(|| {
            "migration inventory archive and source-file rows must be lists".to_owned()
        })?;
    let raw_sources = object
        .get("source_files")
        .and_then(Value::as_array)
        .ok_or_else(|| {
            "migration inventory archive and source-file rows must be lists".to_owned()
        })?;
    if raw_archives.is_empty() || raw_archives.len() > MAX_INVENTORY_ARCHIVES {
        return Err("migration inventory archive count is outside limits".to_owned());
    }
    if raw_sources.is_empty() || raw_sources.len() > MAX_INVENTORY_SOURCE_FILES {
        return Err("migration inventory source-file count is outside limits".to_owned());
    }
    let mut archive_rows = BTreeMap::new();
    let mut archive_order = Vec::new();
    let mut archive_casefold = BTreeSet::new();
    for raw in raw_archives {
        let row = parse_inventory_archive(raw, root)?;
        if !archive_casefold.insert(row.object_key.to_lowercase()) {
            return Err("duplicate or case-colliding migration archive keys".to_owned());
        }
        archive_order.push(row.object_key.clone());
        archive_rows.insert(row.object_key.clone(), row);
    }
    let mut members_by_archive: BTreeMap<String, Vec<LegacyMember>> = archive_rows
        .keys()
        .cloned()
        .map(|key| (key, Vec::new()))
        .collect();
    let mut member_names = BTreeSet::new();
    let mut source_paths = BTreeSet::new();
    for raw in raw_sources {
        let source = raw
            .as_object()
            .ok_or_else(|| "migration inventory source-file row must be an object".to_owned())?;
        exact_fields(
            source,
            &[
                "archive_member_path",
                "archive_object_key",
                "bytes",
                "git_oid",
                "mode",
                "path",
                "sha256",
            ],
            "migration inventory source-file row has invalid fields",
        )?;
        let archive_key = value_at_string(source, "archive_object_key")?;
        validate_object_relative(&archive_key)?;
        let archive = archive_rows.get(&archive_key).ok_or_else(|| {
            "migration inventory source file references an unknown archive".to_owned()
        })?;
        let member_path = value_at_string(source, "archive_member_path")?;
        validate_member_path(&member_path)?;
        let source_path = value_at_string(source, "path")?;
        validate_object_relative(&source_path)?;
        let expected_source = match (&archive.skill, &archive.run_id) {
            (Some(skill), Some(run_id)) if archive.kind == "run" => {
                format!("larch-logs/{skill}/{run_id}/{member_path}")
            }
            (None, None) if archive.kind == "residual" => format!("larch-logs/{member_path}"),
            _ => {
                return Err(
                    "migration inventory source path does not match archive identity".to_owned(),
                );
            }
        };
        if source_path != expected_source {
            return Err(
                "migration inventory source path does not match archive identity".to_owned(),
            );
        }
        let size = value_at_u64(source, "bytes")?;
        if size > MAX_ARCHIVE_MEMBER_BYTES {
            return Err("migration inventory source file exceeds member-size limit".to_owned());
        }
        let digest = value_at_string(source, "sha256")?;
        if !is_lower_hex(&digest, 64) || !is_lower_hex(&value_at_string(source, "git_oid")?, 40) {
            return Err("migration inventory digest is malformed".to_owned());
        }
        let mode = match value_at_string(source, "mode")?.as_str() {
            "100644" => 0o644,
            "100755" => 0o755,
            _ => return Err("migration inventory source-file mode is unsupported".to_owned()),
        };
        if !member_names.insert(format!(
            "{}\0{}",
            archive_key.to_lowercase(),
            member_path.to_lowercase()
        )) || !source_paths.insert(source_path.to_lowercase())
        {
            return Err("duplicate or case-colliding migration members".to_owned());
        }
        members_by_archive
            .get_mut(&archive_key)
            .ok_or_else(|| {
                "migration inventory source file references an unknown archive".to_owned()
            })?
            .push(LegacyMember {
                path: member_path,
                size,
                sha256: digest,
                mode,
            });
    }
    let mut archive_bytes = 0_u64;
    let mut uncompressed_bytes = 0_u64;
    for row in archive_rows.values() {
        archive_bytes = archive_bytes
            .checked_add(row.archive_bytes)
            .ok_or_else(|| "migration inventory totals overflow".to_owned())?;
        uncompressed_bytes = uncompressed_bytes
            .checked_add(row.uncompressed_bytes)
            .ok_or_else(|| "migration inventory totals overflow".to_owned())?;
        let members = members_by_archive
            .get_mut(&row.object_key)
            .ok_or_else(|| "migration inventory archive is missing members".to_owned())?;
        members.sort_by(|left, right| left.path.cmp(&right.path));
        if members.len() != row.member_count
            || members.iter().map(|member| member.size).sum::<u64>() != row.uncompressed_bytes
        {
            return Err("migration inventory per-archive totals are inconsistent".to_owned());
        }
    }
    let totals = object
        .get("totals")
        .and_then(Value::as_object)
        .ok_or_else(|| "migration inventory totals must be an object".to_owned())?;
    exact_fields(
        totals,
        &[
            "archive_bytes",
            "archive_objects",
            "members",
            "run_directories",
            "source_paths",
            "uncompressed_bytes",
        ],
        "migration inventory totals have invalid fields",
    )?;
    let expected_totals = [
        ("archive_bytes", archive_bytes),
        ("archive_objects", archive_rows.len() as u64),
        ("members", raw_sources.len() as u64),
        (
            "run_directories",
            archive_rows
                .values()
                .filter(|row| row.kind == "run")
                .count() as u64,
        ),
        ("source_paths", source_paths.len() as u64),
        ("uncompressed_bytes", uncompressed_bytes),
    ];
    for (field, expected) in expected_totals {
        if value_at_u64(totals, field)? != expected {
            return Err("migration inventory global totals are inconsistent".to_owned());
        }
    }
    let mut result = LegacyInventory::default();
    for key in archive_order {
        let row = archive_rows
            .get(&key)
            .ok_or_else(|| "migration inventory archive disappeared".to_owned())?;
        if row.kind == "run" {
            result.archives.insert(
                row.relative_key.clone(),
                LegacyArchive {
                    archive_size: row.archive_bytes,
                    archive_sha256: row.sha256.clone(),
                    member_count: row.member_count,
                    expanded_size: row.uncompressed_bytes,
                    members: members_by_archive.remove(&key).unwrap_or_default(),
                },
            );
        }
    }
    Ok(result)
}

fn parse_inventory_archive(raw: &Value, root: &StorageRoot) -> Result<InventoryArchiveRow, String> {
    let row = raw
        .as_object()
        .ok_or_else(|| "migration inventory archive row must be an object".to_owned())?;
    exact_fields(
        row,
        &[
            "archive_bytes",
            "kind",
            "member_count",
            "object_key",
            "run_id",
            "sha256",
            "skill",
            "uncompressed_bytes",
        ],
        "migration inventory archive row has invalid fields",
    )?;
    let object_key = value_at_string(row, "object_key")?;
    let relative_key = root.relative_key(&object_key)?;
    let kind = value_at_string(row, "kind")?;
    if !matches!(kind.as_str(), "run" | "residual") {
        return Err("migration inventory archive kind is invalid".to_owned());
    }
    let archive_bytes = value_at_u64(row, "archive_bytes")?;
    let member_count = usize::try_from(value_at_u64(row, "member_count")?)
        .map_err(|_| "migration inventory archive member count is invalid".to_owned())?;
    let uncompressed_bytes = value_at_u64(row, "uncompressed_bytes")?;
    if archive_bytes == 0
        || member_count == 0
        || member_count > MAX_ARCHIVE_MEMBERS
        || archive_bytes > MAX_ARCHIVE_EXPANDED_BYTES
        || uncompressed_bytes > MAX_ARCHIVE_EXPANDED_BYTES
    {
        return Err("migration inventory archive limits are invalid".to_owned());
    }
    let sha256 = value_at_string(row, "sha256")?;
    if !is_lower_hex(&sha256, 64) {
        return Err("migration inventory archive digest is malformed".to_owned());
    }
    let skill = row.get("skill").and_then(Value::as_str).map(str::to_owned);
    let run_id = row.get("run_id").and_then(Value::as_str).map(str::to_owned);
    if kind == "run" {
        let (Some(skill), Some(run_id)) = (&skill, &run_id) else {
            return Err("migration inventory run archive identity is invalid".to_owned());
        };
        let expected = format!("run-logs/{skill}/{run_id}.tar.gz");
        if relative_key != expected || !RunLogSlug::is_valid(skill) || !RunLogSlug::is_valid(run_id)
        {
            return Err("migration inventory run archive identity is invalid".to_owned());
        }
    } else if skill.is_some() || run_id.is_some() || !relative_key.starts_with("migration/") {
        return Err("migration inventory residual archive identity is invalid".to_owned());
    }
    Ok(InventoryArchiveRow {
        object_key,
        relative_key,
        kind,
        skill,
        run_id,
        archive_bytes,
        sha256,
        member_count,
        uncompressed_bytes,
    })
}

fn exact_fields(object: &Map<String, Value>, expected: &[&str], error: &str) -> Result<(), String> {
    (object.len() == expected.len() && expected.iter().all(|field| object.contains_key(*field)))
        .then_some(())
        .ok_or_else(|| error.to_owned())
}

fn value_at_string(object: &Map<String, Value>, field: &str) -> Result<String, String> {
    object
        .get(field)
        .and_then(Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| format!("migration inventory field is invalid: {field}"))
}

fn value_at_u64(object: &Map<String, Value>, field: &str) -> Result<u64, String> {
    object
        .get(field)
        .and_then(Value::as_u64)
        .ok_or_else(|| format!("migration inventory field is invalid: {field}"))
}

fn validate_member_path(value: &str) -> Result<(), String> {
    validate_object_relative(value)?;
    if value == "archive-manifest.json" {
        return Err("migration inventory source file uses a reserved member path".to_owned());
    }
    Ok(())
}

fn sha256_bytes(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn materialize_legacy_for_check(
    archive: &Path,
    remote: &RemoteArchive,
    legacy: &LegacyArchive,
    work_dir: &Path,
) -> Result<MaterializedCheck, String> {
    let temporary = TempDir::new_in(work_dir)
        .map_err(|error| format!("could not create legacy validation directory: {error}"))?;
    let staging = temporary.path().join("staging");
    materialize_legacy_to_staging(archive, legacy, &staging)?;
    let output = temporary.path().join("output");
    let created =
        run_lifecycle::archive_run_directory(&staging, &output, &remote.skill, &remote.run_id)
            .map_err(|error| error.to_string())?;
    let result = run_lifecycle::materialize_run_archive(
        &created.archive_path,
        &temporary.path().join("check").join(&remote.run_id),
        &remote.skill,
        &remote.run_id,
    )
    .map_err(|error| error.to_string())?;
    Ok(MaterializedCheck {
        member_count: result.member_count,
        expanded_size: result.expanded_size,
    })
}

#[allow(clippy::too_many_lines)] // Legacy extraction validates each archive member transactionally.
fn materialize_legacy_to_staging(
    archive: &Path,
    legacy: &LegacyArchive,
    staging: &Path,
) -> Result<(), String> {
    let metadata = fs::symlink_metadata(archive)
        .map_err(|error| format!("could not inspect legacy archive: {error}"))?;
    if !metadata.file_type().is_file() || metadata.len() != legacy.archive_size {
        return Err("legacy archive size does not match migration inventory".to_owned());
    }
    if sha256_file(archive)? != legacy.archive_sha256 {
        return Err("legacy archive digest does not match migration inventory".to_owned());
    }
    if legacy.member_count != legacy.members.len()
        || legacy.expanded_size != legacy.members.iter().map(|member| member.size).sum::<u64>()
        || legacy.member_count > MAX_ARCHIVE_MEMBERS
        || legacy.expanded_size > MAX_ARCHIVE_EXPANDED_BYTES
        || legacy.expanded_size > metadata.len().saturating_mul(MAX_COMPRESSION_RATIO)
    {
        return Err("legacy archive inventory is inconsistent".to_owned());
    }
    fs::create_dir(staging)
        .map_err(|error| format!("could not create legacy staging directory: {error}"))?;
    let file = fs::File::open(archive)
        .map_err(|error| format!("could not open legacy archive: {error}"))?;
    let mut archive = Archive::new(GzDecoder::new(file));
    let entries = archive
        .entries()
        .map_err(|_| "legacy archive could not be read".to_owned())?;
    let mut seen = 0_usize;
    for entry in entries {
        let mut entry = entry.map_err(|_| "legacy archive could not be read".to_owned())?;
        let expected = legacy
            .members
            .get(seen)
            .ok_or_else(|| "legacy archive members do not match migration inventory".to_owned())?;
        let raw_path = entry
            .path()
            .map_err(|_| "legacy archive member path is unsafe".to_owned())?;
        let path = raw_path
            .to_str()
            .ok_or_else(|| "legacy archive member path is unsafe".to_owned())?;
        validate_member_path(path)?;
        let mode = entry
            .header()
            .mode()
            .map_err(|_| "legacy archive member mode is invalid".to_owned())?
            & 0o777;
        let header = entry.header();
        let normalized_metadata = header.mtime().is_ok_and(|value| value == 0)
            && header.uid().is_ok_and(|value| value == 0)
            && header.gid().is_ok_and(|value| value == 0)
            && header
                .username()
                .is_ok_and(|value| value.is_none_or(str::is_empty))
            && header
                .groupname()
                .is_ok_and(|value| value.is_none_or(str::is_empty));
        if !entry.header().entry_type().is_file()
            || path != expected.path
            || entry.size() != expected.size
            || mode != expected.mode
        {
            return Err("legacy archive members do not match migration inventory".to_owned());
        }
        if !normalized_metadata {
            return Err("legacy archive member metadata is not normalized".to_owned());
        }
        let destination = staging.join(path);
        let parent = destination
            .parent()
            .ok_or_else(|| "legacy archive member parent is missing".to_owned())?;
        fs::create_dir_all(parent)
            .map_err(|error| format!("could not create legacy archive member parent: {error}"))?;
        if fs::symlink_metadata(parent)
            .map_err(|error| format!("could not inspect legacy archive member parent: {error}"))?
            .file_type()
            .is_symlink()
        {
            return Err("legacy archive member parent is unsafe".to_owned());
        }
        let mut destination_file = fs::File::create(&destination)
            .map_err(|error| format!("could not create legacy archive member: {error}"))?;
        let mut digest = Sha256::new();
        let mut copied = 0_u64;
        let mut buffer = vec![0_u8; 64 * 1024];
        loop {
            let read = entry
                .read(&mut buffer)
                .map_err(|_| "legacy archive member could not be read".to_owned())?;
            if read == 0 {
                break;
            }
            copied = copied
                .checked_add(read as u64)
                .ok_or_else(|| "legacy archive member size overflowed".to_owned())?;
            if copied > expected.size {
                return Err(
                    "legacy archive member size differs from migration inventory".to_owned(),
                );
            }
            digest.update(&buffer[..read]);
            destination_file
                .write_all(&buffer[..read])
                .map_err(|error| format!("could not write legacy archive member: {error}"))?;
        }
        destination_file
            .sync_all()
            .map_err(|error| format!("could not sync legacy archive member: {error}"))?;
        if copied != expected.size || format!("{:x}", digest.finalize()) != expected.sha256 {
            return Err("legacy archive member digest differs from migration inventory".to_owned());
        }
        set_legacy_mode(&destination, expected.mode)?;
        seen += 1;
    }
    if seen != legacy.members.len() {
        return Err("legacy archive members do not match migration inventory".to_owned());
    }
    Ok(())
}

#[cfg(unix)]
fn set_legacy_mode(path: &Path, mode: u32) -> Result<(), String> {
    use std::os::unix::fs::PermissionsExt as _;

    fs::set_permissions(path, fs::Permissions::from_mode(mode))
        .map_err(|error| format!("could not set legacy archive member mode: {error}"))
}

#[cfg(not(unix))]
fn set_legacy_mode(_path: &Path, _mode: u32) -> Result<(), String> {
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{
        LayoutMapping, LegacyDescriptor, StorageRoot, apply_layout, cursor_cost, decimal_after,
        live_mappings, migrate_layout, parse_legacy_inventory, plan_layout, read_json,
        retro_fix_cursor, retro_fix_cursor_impl, retro_v3_sweep, retro_v3_sweep_impl,
        transform_cursor_summary, transform_transcript, validate_member_path,
        validate_object_relative, value_as_i64, verify_layout,
    };
    use larch_adapters::{run_lifecycle, runtime::LarchRuntime};
    use larch_core::{
        ObjectPage, ObjectStore, ObjectStoreError, ObjectStoreFuture, OrderedJson, RemoteObject,
    };
    use serde_json::{Value, json};
    use sha2::{Digest as _, Sha256};
    use std::{
        collections::BTreeMap, ffi::OsString, fs, io::Write as _, path::Path, process::ExitCode,
        sync::Mutex,
    };

    #[derive(Default)]
    struct MemoryStore {
        objects: Mutex<BTreeMap<String, Vec<u8>>>,
    }

    impl MemoryStore {
        fn with_objects(objects: BTreeMap<String, Vec<u8>>) -> Self {
            Self {
                objects: Mutex::new(objects),
            }
        }

        fn has(&self, key: &str) -> bool {
            self.objects
                .lock()
                .expect("memory store lock")
                .contains_key(key)
        }

        fn bytes(&self, key: &str) -> Vec<u8> {
            self.objects
                .lock()
                .expect("memory store lock")
                .get(key)
                .cloned()
                .expect("memory store object")
        }
    }

    impl ObjectStore for MemoryStore {
        fn preflight_prefix<'a>(
            &'a self,
            _bucket: &'a str,
            _prefix: &'a str,
        ) -> ObjectStoreFuture<'a, ()> {
            Box::pin(async { Ok(()) })
        }

        fn list_page<'a>(
            &'a self,
            _bucket: &'a str,
            prefix: &'a str,
            _page_token: Option<&'a str>,
        ) -> ObjectStoreFuture<'a, ObjectPage> {
            Box::pin(async move {
                let objects = self.objects.lock().map_err(|_| ObjectStoreError::LocalIo)?;
                Ok(ObjectPage {
                    objects: objects
                        .iter()
                        .filter(|(key, _value)| key.starts_with(prefix))
                        .map(|(key, value)| remote_object(key, value))
                        .collect(),
                    next_page_token: None,
                })
            })
        }

        fn upload_create<'a>(
            &'a self,
            _bucket: &'a str,
            key: &'a str,
            source: &'a Path,
        ) -> ObjectStoreFuture<'a, RemoteObject> {
            Box::pin(async move {
                let value = fs::read(source).map_err(|_| ObjectStoreError::LocalIo)?;
                let mut objects = self.objects.lock().map_err(|_| ObjectStoreError::LocalIo)?;
                if objects.contains_key(key) {
                    return Err(ObjectStoreError::AlreadyExists);
                }
                objects.insert(key.to_owned(), value.clone());
                drop(objects);
                Ok(remote_object(key, &value))
            })
        }

        fn download<'a>(
            &'a self,
            _bucket: &'a str,
            key: &'a str,
            destination: &'a Path,
        ) -> ObjectStoreFuture<'a, ()> {
            Box::pin(async move {
                let value = self
                    .objects
                    .lock()
                    .map_err(|_| ObjectStoreError::LocalIo)?
                    .get(key)
                    .cloned()
                    .ok_or(ObjectStoreError::NotFound)?;
                let mut destination =
                    fs::File::create_new(destination).map_err(|_| ObjectStoreError::LocalIo)?;
                destination
                    .write_all(&value)
                    .map_err(|_| ObjectStoreError::LocalIo)
            })
        }

        fn metadata<'a>(
            &'a self,
            _bucket: &'a str,
            key: &'a str,
        ) -> ObjectStoreFuture<'a, RemoteObject> {
            Box::pin(async move {
                let value = self
                    .objects
                    .lock()
                    .map_err(|_| ObjectStoreError::LocalIo)?
                    .get(key)
                    .cloned()
                    .ok_or(ObjectStoreError::NotFound)?;
                Ok(remote_object(key, &value))
            })
        }
    }

    fn remote_object(key: &str, value: &[u8]) -> RemoteObject {
        RemoteObject {
            key: key.to_owned(),
            size: value.len() as u64,
            etag: Some(format!("{:x}", Sha256::digest(value))),
            version: None,
        }
    }

    fn modern_archive(root: &Path, skill: &str, run_id: &str, content: &[u8]) -> Vec<u8> {
        let staging = root.join(format!("staging-{run_id}"));
        let output = root.join(format!("output-{run_id}"));
        fs::create_dir_all(&staging).expect("staging directory");
        fs::write(staging.join("result.txt"), content).expect("archive fixture content");
        let archive = run_lifecycle::archive_run_directory(&staging, &output, skill, run_id)
            .expect("modern archive fixture");
        fs::read(archive.archive_path).expect("modern archive bytes")
    }

    fn legacy_archive(content: &[u8]) -> Vec<u8> {
        legacy_archive_with_mtime(content, 0)
    }

    fn legacy_archive_with_mtime(content: &[u8], mtime: u64) -> Vec<u8> {
        use flate2::{Compression, write::GzEncoder};
        use tar::Builder;

        let mut encoded = Vec::new();
        let gzip_writer = GzEncoder::new(&mut encoded, Compression::default());
        let mut archive = Builder::new(gzip_writer);
        let mut header = tar::Header::new_gnu();
        header.set_size(content.len() as u64);
        header.set_mode(0o644);
        header.set_mtime(mtime);
        header.set_uid(0);
        header.set_gid(0);
        header.set_cksum();
        archive
            .append_data(&mut header, "result.txt", content)
            .expect("legacy archive member");
        archive.finish().expect("legacy archive finish");
        archive
            .into_inner()
            .expect("legacy compression stream")
            .finish()
            .expect("legacy archive compression finish");
        encoded
    }

    fn argv(values: &[&str]) -> Vec<OsString> {
        values.iter().map(|value| OsString::from(*value)).collect()
    }

    fn live_plan_values() -> BTreeMap<String, String> {
        BTreeMap::from([
            (
                "--larch-source-uri".to_owned(),
                "s3://zhupanov/larch".to_owned(),
            ),
            (
                "--larch-target-uri".to_owned(),
                "s3://zhupanov/larch/larch".to_owned(),
            ),
            (
                "--agent-lint-source-uri".to_owned(),
                "s3://zhupanov/agent-lint".to_owned(),
            ),
            (
                "--agent-lint-target-uri".to_owned(),
                "s3://zhupanov/larch/agent-lint".to_owned(),
            ),
            (
                "--legacy-schema".to_owned(),
                "larch-run-log-migration-inventory-v1".to_owned(),
            ),
            ("--legacy-source-commit".to_owned(), "1".repeat(40)),
            (
                "--legacy-inventory-key".to_owned(),
                "migration/inventory.json".to_owned(),
            ),
            ("--legacy-inventory-sha256".to_owned(), "2".repeat(64)),
        ])
    }

    fn legacy_inventory_fixture() -> (LegacyDescriptor, StorageRoot, Vec<u8>) {
        let descriptor = LegacyDescriptor {
            schema: "larch-run-log-migration-inventory-v1".to_owned(),
            source_commit: "1".repeat(40),
            storage_root: "s3://zhupanov/larch".to_owned(),
            inventory_key: "migration/inventory.json".to_owned(),
            inventory_sha256: "2".repeat(64),
        };
        let root = StorageRoot::parse(&descriptor.storage_root).expect("storage root");
        let payload = json!({
            "archives": [{
                "archive_bytes": 100,
                "kind": "run",
                "member_count": 1,
                "object_key": "larch/run-logs/design/legacy-run.tar.gz",
                "run_id": "legacy-run",
                "sha256": "3".repeat(64),
                "skill": "design",
                "uncompressed_bytes": 7,
            }],
            "schema": descriptor.schema,
            "source_commit": descriptor.source_commit,
            "source_files": [{
                "archive_member_path": "result.txt",
                "archive_object_key": "larch/run-logs/design/legacy-run.tar.gz",
                "bytes": 7,
                "git_oid": "4".repeat(40),
                "mode": "100644",
                "path": "larch-logs/design/legacy-run/result.txt",
                "sha256": "5".repeat(64),
            }],
            "storage_root": descriptor.storage_root,
            "totals": {
                "archive_bytes": 100,
                "archive_objects": 1,
                "members": 1,
                "run_directories": 1,
                "source_paths": 1,
                "uncompressed_bytes": 7,
            },
        });
        (
            descriptor,
            root,
            serde_json::to_vec(&payload).expect("inventory JSON"),
        )
    }

    fn write_cursor_case(root: &Path, run_id: &str, summary: &str, report: Option<&str>) {
        let run = root.join("larch-logs/implement").join(run_id);
        fs::create_dir_all(&run).expect("cursor case directory");
        fs::write(run.join("final-summary.md"), summary).expect("cursor case summary");
        if let Some(report) = report {
            fs::write(run.join("token-report-final.json"), report).expect("cursor case report");
        }
    }

    #[test]
    fn cursor_cost_preserves_the_historical_surcharge() {
        assert!((cursor_cost(0, 1_000_000, 0) - 0.45).abs() < f64::EPSILON);
    }

    #[test]
    fn decimal_parser_requires_a_decimal_value() {
        assert_eq!(
            decimal_after("Cursor $1.20", "Cursor $").map(|value| value.2),
            Some(1.2)
        );
        assert!(decimal_after("Cursor $12", "Cursor $").is_none());
        assert!(decimal_after("Cursor $.20", "Cursor $").is_none());
        assert!(decimal_after("Cursor $1.", "Cursor $").is_none());
        assert_eq!(
            decimal_after("Cursor $.20; Cursor $1.20", "Cursor $").map(|value| value.2),
            Some(1.2)
        );
    }

    #[test]
    fn migration_json_and_object_paths_stay_canonical() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let path = directory.path().join("plan.json");
        fs::write(&path, r#"{"schema":"one","schema":"two"}"#).expect("fixture");
        assert!(read_json(&path).is_err());
        assert!(validate_object_relative("run-logs/e\u{301}/run.tar.gz").is_err());
    }

    #[test]
    fn legacy_archives_reject_non_normalized_metadata() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let content = b"legacy\n";
        let archive = legacy_archive_with_mtime(content, 1);
        let path = directory.path().join("legacy.tar.gz");
        fs::write(&path, &archive).expect("legacy archive fixture");
        let legacy = super::LegacyArchive {
            archive_size: archive.len() as u64,
            archive_sha256: format!("{:x}", Sha256::digest(&archive)),
            member_count: 1,
            expanded_size: content.len() as u64,
            members: vec![super::LegacyMember {
                path: "result.txt".to_owned(),
                size: content.len() as u64,
                sha256: format!("{:x}", Sha256::digest(content)),
                mode: 0o644,
            }],
        };
        assert!(super::materialize_legacy_to_staging(
            &path,
            &legacy,
            &directory.path().join("staging"),
        )
        .is_err());
    }

    #[test]
    fn transcript_transform_filters_tool_blocks() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let path = directory.path().join("session-transcript.jsonl");
        fs::write(
            &path,
            "{\"z\":0,\"v\":2,\"a\":1}\n{\"tail\":true,\"blocks\":[{\"type\":\"tool_call\"},{\"type\":\"text\",\"text\":\"keep\"}]}\n",
        )
        .expect("fixture");
        assert!(matches!(
            transform_transcript(&path, false),
            Ok(super::TranscriptStatus::Transformed)
        ));
        let rendered = fs::read_to_string(path).expect("rendered transcript");
        assert!(rendered.starts_with(
            "{\"z\":0,\"v\":3,\"a\":1,\"policy\":\"prose-errors-only\",\"turns\":1}\n{\"tail\":true,\"blocks\":[{\"type\":\"text\",\"text\":\"keep\"}]}\n"
        ));
        assert!(rendered.contains("\"policy\":\"prose-errors-only\""));
        assert!(!rendered.contains("tool_call"));
    }

    #[test]
    fn transcript_with_a_float_v3_header_is_left_untouched() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let path = directory.path().join("session-transcript.jsonl");
        let original = "{\"v\":3.0}\n";
        fs::write(&path, original).expect("fixture");

        assert!(matches!(
            transform_transcript(&path, false),
            Ok(super::TranscriptStatus::Skipped)
        ));
        assert_eq!(
            fs::read_to_string(path).expect("rendered transcript"),
            original
        );
    }

    #[test]
    fn cursor_repair_falls_back_to_the_nonfinal_token_report() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let summary = directory.path().join("final-summary.md");
        fs::write(&summary, "- **Cost**: TOTAL ~$9.99 — Cursor $0.01\n").expect("summary fixture");
        fs::write(
            directory.path().join("token-report.json"),
            "{\"BUCKETS_cursor\":{\"input\":0,\"cache_read\":2000000,\"output\":0}}",
        )
        .expect("token fixture");

        assert!(matches!(
            super::transform_cursor_summary(&summary, false),
            Ok(super::CursorStatus::Fixed)
        ));
        let rendered = fs::read_to_string(summary).expect("rewritten summary");
        assert!(rendered.contains("Cursor $0.90"));
        assert!(rendered.contains("TOTAL ~$10.88"));
    }

    #[test]
    fn dry_runs_name_the_same_files_that_live_retro_sweeps_change() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let implement = directory.path().join("larch-logs/implement/run-1");
        fs::create_dir_all(&implement).expect("implement fixture directory");
        let transcript = implement.join("session-transcript.jsonl");
        fs::write(
            &transcript,
            "{\"v\":2}\n{\"blocks\":[{\"type\":\"text\",\"text\":\"keep\"}]}\n",
        )
        .expect("transcript fixture");
        let summary = implement.join("final-summary.md");
        fs::write(
            &summary,
            "- **Cost**: \\u{1f4b0} TOTAL ~$20.97 \\u{2014} Cursor $2.66\n",
        )
        .expect("summary fixture");
        fs::write(
            implement.join("token-report-final.json"),
            "{\"BUCKETS_cursor\":{\"input\":1030521,\"cache_read\":9188853,\"output\":122940}}",
        )
        .expect("token fixture");

        let transcript_dry = retro_v3_sweep_impl(directory.path(), true).expect("v3 dry run");
        let cursor_dry =
            retro_fix_cursor_impl(directory.path(), true, None).expect("cursor dry run");
        assert_eq!(
            transcript_dry.changed,
            ["larch-logs/implement/run-1/session-transcript.jsonl"]
        );
        assert_eq!(
            cursor_dry.changed,
            ["larch-logs/implement/run-1/final-summary.md"]
        );
        assert!(
            !fs::read_to_string(&transcript)
                .expect("dry transcript")
                .contains("\"v\":3")
        );
        assert!(
            fs::read_to_string(&summary)
                .expect("dry summary")
                .contains("Cursor $2.66")
        );

        let transcript_live = retro_v3_sweep_impl(directory.path(), false).expect("v3 live run");
        let cursor_live =
            retro_fix_cursor_impl(directory.path(), false, None).expect("cursor live run");
        assert_eq!(transcript_live.changed, transcript_dry.changed);
        assert_eq!(cursor_live.changed, cursor_dry.changed);
        assert!(
            fs::read_to_string(&transcript)
                .expect("live transcript")
                .contains("\"v\":3")
        );
        assert!(
            fs::read_to_string(&summary)
                .expect("live summary")
                .contains("Cursor $5.25")
        );

        let transcript_repeat = retro_v3_sweep_impl(directory.path(), false).expect("v3 repeat");
        let cursor_repeat =
            retro_fix_cursor_impl(directory.path(), false, None).expect("cursor repeat");
        assert!(transcript_repeat.changed.is_empty());
        assert!(cursor_repeat.changed.is_empty());
        assert_eq!(transcript_repeat.counts.skipped, 1);
        assert_eq!(cursor_repeat.counts.already_correct, 1);
    }

    #[cfg(unix)]
    #[test]
    fn retro_sweeps_reject_a_symlinked_root() {
        use std::os::unix::fs::symlink;

        let directory = tempfile::tempdir().expect("temporary directory");
        let linked = directory.path().join("linked-root");
        symlink(directory.path(), &linked).expect("symlink fixture");
        assert!(retro_v3_sweep_impl(&linked, true).is_err());
        assert!(retro_fix_cursor_impl(&linked, true, None).is_err());
    }

    #[cfg(unix)]
    #[test]
    fn retro_sweeps_reject_a_symlinked_log_subtree() {
        use std::os::unix::fs::symlink;

        let directory = tempfile::tempdir().expect("temporary directory");
        let outside = tempfile::tempdir().expect("outside directory");
        fs::create_dir_all(outside.path().join("implement/run-1"))
            .expect("outside run-log directory");
        symlink(outside.path(), directory.path().join("larch-logs")).expect("symlink fixture");
        assert!(retro_v3_sweep_impl(directory.path(), true).is_err());
        assert!(retro_fix_cursor_impl(directory.path(), true, None).is_err());
    }

    #[test]
    fn cursor_run_id_cannot_escape_the_configured_root() {
        let directory = tempfile::tempdir().expect("temporary directory");
        assert!(retro_fix_cursor_impl(directory.path(), true, Some("../outside")).is_err());
    }

    #[test]
    fn retro_command_entrypoints_cover_live_dry_and_failure_paths() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let root = directory.path().to_str().expect("UTF-8 root");
        let run = directory.path().join("larch-logs/implement/run-1");
        fs::create_dir_all(&run).expect("run directory");
        fs::write(
            run.join("session-transcript.jsonl"),
            "{\"v\":2}\n{\"blocks\":[{\"type\":\"text\",\"text\":\"keep\"}]}\n",
        )
        .expect("transcript fixture");
        fs::write(
            run.join("final-summary.md"),
            "- **Cost**: TOTAL ~$9.99 — Cursor $0.01\n",
        )
        .expect("summary fixture");
        fs::write(
            run.join("token-report-final.json"),
            "{\"BUCKETS_cursor\":{\"input\":0,\"cache_read\":2000000,\"output\":0}}",
        )
        .expect("token fixture");

        assert_eq!(
            retro_v3_sweep(&argv(&["--root", root, "--dry-run"])),
            ExitCode::SUCCESS
        );
        assert_eq!(retro_v3_sweep(&argv(&["--root", root])), ExitCode::SUCCESS);
        assert_eq!(
            retro_fix_cursor(&argv(&["--root", root, "--dry-run"])),
            ExitCode::SUCCESS
        );
        assert_eq!(
            retro_fix_cursor(&argv(&["--root", root])),
            ExitCode::SUCCESS
        );
        assert_eq!(retro_v3_sweep(&argv(&["--unknown"])), ExitCode::from(2));
        assert_eq!(retro_fix_cursor(&argv(&["--unknown"])), ExitCode::from(2));

        let unavailable = directory.path().join("unavailable");
        let unavailable = unavailable.to_str().expect("UTF-8 unavailable root");
        assert_eq!(
            retro_v3_sweep(&argv(&["--root", unavailable])),
            ExitCode::FAILURE
        );
        assert_eq!(
            retro_fix_cursor(&argv(&["--root", unavailable])),
            ExitCode::FAILURE
        );
    }

    #[test]
    fn migration_command_entrypoints_validate_every_phase() {
        assert_eq!(migrate_layout(&argv(&[])), ExitCode::from(2));
        assert_eq!(migrate_layout(&argv(&["unknown"])), ExitCode::from(2));
        assert_eq!(migrate_layout(&argv(&["--help"])), ExitCode::SUCCESS);
        assert_eq!(
            migrate_layout(&argv(&["plan", "--help"])),
            ExitCode::SUCCESS
        );
        assert_eq!(
            migrate_layout(&argv(&["apply", "--help"])),
            ExitCode::SUCCESS
        );
        assert_eq!(
            migrate_layout(&argv(&["verify", "--help"])),
            ExitCode::SUCCESS
        );
        assert_eq!(migrate_layout(&argv(&["plan"])), ExitCode::from(2));
        assert_eq!(
            migrate_layout(&argv(&["plan", "--unknown"])),
            ExitCode::from(2)
        );
        assert_eq!(
            migrate_layout(&argv(&[
                "apply",
                "--plan",
                "plan.json",
                "--report",
                "report.json",
                "--work-dir",
                "work",
            ])),
            ExitCode::FAILURE
        );
        assert_eq!(
            migrate_layout(&argv(&[
                "verify",
                "--plan",
                "plan.json",
                "--report",
                "report.json",
                "--final-report",
                "final.json",
                "--work-dir",
                "work",
                "--publish-report-key",
                "migration/final.json",
            ])),
            ExitCode::FAILURE
        );
        assert_eq!(
            migrate_layout(&argv(&[
                "plan",
                "--larch-source-uri",
                "s3://untrusted/larch",
                "--larch-target-uri",
                "s3://zhupanov/larch/larch",
                "--agent-lint-source-uri",
                "s3://zhupanov/agent-lint",
                "--agent-lint-target-uri",
                "s3://zhupanov/larch/agent-lint",
                "--legacy-schema",
                "larch-run-log-migration-inventory-v1",
                "--legacy-source-commit",
                "1111111111111111111111111111111111111111",
                "--legacy-inventory-key",
                "migration/inventory.json",
                "--legacy-inventory-sha256",
                "2222222222222222222222222222222222222222222222222222222222222222",
                "--output",
                "plan.json",
                "--work-dir",
                "work",
                "--operator",
                "tester",
                "--tool-version",
                "test",
                "--source-commit",
                "3333333333333333333333333333333333333333",
            ])),
            ExitCode::FAILURE
        );
    }

    #[test]
    fn live_mapping_allowlist_accepts_only_the_two_live_roots() {
        let values = live_plan_values();
        let mappings = live_mappings(&values).expect("allowlisted mappings");
        assert_eq!(mappings.len(), 2);
        assert_eq!(mappings[0].client_repo, "larch");
        assert_eq!(mappings[1].client_repo, "agent-lint");

        let mut missing = values;
        missing.remove("--larch-target-uri");
        assert!(live_mappings(&missing).is_err());

        let mut mismatched = mappings[0].clone();
        mismatched.target =
            StorageRoot::parse("s3://zhupanov/larch/not-larch").expect("mismatched target");
        assert!(mismatched.validate().is_err());
    }

    #[test]
    fn retro_transformations_classify_legacy_input_shapes() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let transcript = directory.path().join("session-transcript.jsonl");
        fs::write(&transcript, "").expect("empty transcript");
        assert!(matches!(
            transform_transcript(&transcript, true),
            Ok(super::TranscriptStatus::Empty)
        ));
        fs::write(&transcript, "not JSON\n").expect("invalid transcript");
        assert!(matches!(
            transform_transcript(&transcript, true),
            Ok(super::TranscriptStatus::Empty)
        ));
        fs::write(
            &transcript,
            "{\"v\":2}\n{\"without_blocks\":true}\n{\"blocks\":[{\"type\":\"tool_call\"}]}\n",
        )
        .expect("mixed transcript");
        assert!(matches!(
            transform_transcript(&transcript, true),
            Ok(super::TranscriptStatus::Transformed)
        ));

        let summary = directory.path().join("final-summary.md");
        fs::write(&summary, "Cursor $0.00").expect("zero cursor summary");
        assert!(matches!(
            transform_cursor_summary(&summary, true),
            Ok(super::CursorStatus::NoCursor)
        ));
        fs::write(&summary, "Cursor $1.00").expect("missing report summary");
        assert!(matches!(
            transform_cursor_summary(&summary, true),
            Ok(super::CursorStatus::NoReport)
        ));
        fs::write(directory.path().join("token-report-final.json"), "{}").expect("empty report");
        assert!(matches!(
            transform_cursor_summary(&summary, true),
            Ok(super::CursorStatus::NoBuckets)
        ));
        fs::write(
            directory.path().join("token-report-final.json"),
            "{\"BUCKETS_cursor\":{\"cache_read\":0}}",
        )
        .expect("zero-cache report");
        assert!(matches!(
            transform_cursor_summary(&summary, true),
            Ok(super::CursorStatus::NoCacheRead)
        ));
        fs::write(
            directory.path().join("token-report-final.json"),
            "{\"BUCKETS_cursor\":{\"cache_read\":1000000}}",
        )
        .expect("cost report");
        assert!(matches!(
            transform_cursor_summary(&summary, true),
            Ok(super::CursorStatus::FormatMismatch)
        ));
        fs::write(&summary, "TOTAL ~$10.45 — Cursor $0.45").expect("correct summary");
        assert!(matches!(
            transform_cursor_summary(&summary, true),
            Ok(super::CursorStatus::AlreadyCorrect)
        ));
    }

    #[test]
    fn retro_helpers_preserve_the_old_python_coercion_and_truthiness_rules() {
        assert_eq!(value_as_i64(None), 0);
        assert_eq!(value_as_i64(Some(&json!(true))), 1);
        assert_eq!(value_as_i64(Some(&json!(false))), 0);
        assert_eq!(value_as_i64(Some(&json!(-3))), -3);
        assert_eq!(value_as_i64(Some(&json!(2.8))), 2);
        assert_eq!(value_as_i64(Some(&json!(u64::MAX))), 0);
        assert_eq!(value_as_i64(Some(&json!("7"))), 0);

        assert!(!super::ordered_value_is_truthy(&OrderedJson::Null));
        assert!(!super::ordered_value_is_truthy(&OrderedJson::Bool(false)));
        assert!(super::ordered_value_is_truthy(&OrderedJson::Bool(true)));
        assert!(!super::ordered_value_is_truthy(&OrderedJson::Number(
            serde_json::Number::from(0)
        )));
        assert!(super::ordered_value_is_truthy(&OrderedJson::Number(
            serde_json::Number::from(1)
        )));
        assert!(!super::ordered_value_is_truthy(&OrderedJson::String(
            String::new()
        )));
        assert!(super::ordered_value_is_truthy(&OrderedJson::Array(vec![
            OrderedJson::Null
        ])));
        assert!(super::ordered_value_is_truthy(&OrderedJson::Object(vec![
            ("key".to_owned(), OrderedJson::Null),
        ])));
    }

    #[test]
    fn run_log_discovery_keeps_summaries_inside_a_real_root() {
        let directory = tempfile::tempdir().expect("temporary directory");
        assert!(
            super::summary_files(directory.path(), None)
                .expect("missing logs")
                .is_empty()
        );
        let implement = directory.path().join("larch-logs/implement/run-1");
        let design = directory.path().join("larch-logs/design/run-1");
        fs::create_dir_all(&implement).expect("implement directory");
        fs::create_dir_all(&design).expect("design directory");
        fs::write(implement.join("final-summary.md"), "summary").expect("implement summary");
        fs::write(design.join("final-summary.md"), "summary").expect("design summary");
        fs::write(implement.join("session-transcript.jsonl"), "{\"v\":3}\n").expect("transcript");

        assert_eq!(
            super::summary_files(directory.path(), None)
                .expect("all summaries")
                .len(),
            2
        );
        assert_eq!(
            super::summary_files(directory.path(), Some("run-1"))
                .expect("selected summaries")
                .len(),
            2
        );
        assert_eq!(
            super::transcript_files(directory.path())
                .expect("transcripts")
                .len(),
            1
        );
        assert!(super::summary_files(directory.path(), Some("../run-1")).is_err());
    }

    #[test]
    fn retro_sweeps_report_empty_roots_and_account_for_every_cursor_skip() {
        let empty = tempfile::tempdir().expect("empty root");
        let empty_root = empty.path().to_str().expect("UTF-8 root");
        assert_eq!(
            retro_v3_sweep(&argv(&["--root", empty_root])),
            ExitCode::SUCCESS
        );
        assert_eq!(
            retro_fix_cursor(&argv(&["--root", empty_root])),
            ExitCode::SUCCESS
        );

        let directory = tempfile::tempdir().expect("temporary directory");
        write_cursor_case(directory.path(), "no-cursor", "no cursor here", None);
        write_cursor_case(directory.path(), "no-report", "Cursor $1.00", None);
        write_cursor_case(directory.path(), "no-buckets", "Cursor $1.00", Some("{}"));
        write_cursor_case(
            directory.path(),
            "no-cache",
            "Cursor $1.00",
            Some("{\"BUCKETS_cursor\":{\"cache_read\":0}}"),
        );
        write_cursor_case(
            directory.path(),
            "format",
            "Cursor $1.00",
            Some("{\"BUCKETS_cursor\":{\"cache_read\":1000000}}"),
        );
        write_cursor_case(
            directory.path(),
            "correct",
            "TOTAL ~$10.45 — Cursor $0.45",
            Some("{\"BUCKETS_cursor\":{\"cache_read\":1000000}}"),
        );
        let empty_transcript = directory
            .path()
            .join("larch-logs/implement/empty/session-transcript.jsonl");
        fs::create_dir_all(empty_transcript.parent().expect("transcript parent"))
            .expect("transcript directory");
        fs::write(empty_transcript, "").expect("empty transcript");

        let cursor = retro_fix_cursor_impl(directory.path(), true, None).expect("cursor sweep");
        assert_eq!(cursor.counts.no_cursor, 1);
        assert_eq!(cursor.counts.no_report, 1);
        assert_eq!(cursor.counts.no_buckets, 1);
        assert_eq!(cursor.counts.no_cache_read, 1);
        assert_eq!(cursor.counts.format_mismatch, 1);
        assert_eq!(cursor.counts.already_correct, 1);
        let transcript = retro_v3_sweep_impl(directory.path(), true).expect("v3 sweep");
        assert_eq!(transcript.counts.empty, 1);
    }

    #[test]
    fn transcript_and_storage_helpers_reject_noncanonical_records() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let transcript = directory.path().join("session-transcript.jsonl");
        fs::write(
            &transcript,
            "{\"v\":2}\nnot-json\n{\"blocks\":[1,{\"type\":true},{\"type\":\"tool_result\",\"error\":true}]}\n",
        )
        .expect("transcript fixture");
        assert!(matches!(
            transform_transcript(&transcript, true),
            Ok(super::TranscriptStatus::Transformed)
        ));

        let root = StorageRoot::parse("s3://bucket").expect("root without prefix");
        assert_eq!(root.key("run-logs/").expect("root key"), "run-logs/");
        assert_eq!(
            root.relative_key("run-logs/implement/run.tar.gz")
                .expect("relative key"),
            "run-logs/implement/run.tar.gz"
        );
        assert!(super::parse_archive_key("run-logs/implement/run.tar.gz").is_ok());
        assert!(super::parse_archive_key("run-logs/implement/nested/run.tar.gz").is_err());
        assert!(super::parse_archive_key("not-a-run-log").is_err());
    }

    #[test]
    fn legacy_inventory_parser_rejects_mutated_pinned_rows() {
        let (descriptor, root, encoded) = legacy_inventory_fixture();
        let inventory = parse_legacy_inventory(&encoded, &descriptor, &root).expect("inventory");
        assert!(
            inventory
                .archive_for("run-logs/design/legacy-run.tar.gz")
                .is_some()
        );
        assert!(
            parse_legacy_inventory(br#"{"schema":"one","schema":"two"}"#, &descriptor, &root,)
                .is_err()
        );

        let payload: Value = serde_json::from_slice(&encoded).expect("fixture value");
        let mut invalid_kind = payload.clone();
        invalid_kind["archives"][0]["kind"] = json!("unknown");
        assert!(
            parse_legacy_inventory(
                &serde_json::to_vec(&invalid_kind).expect("invalid kind JSON"),
                &descriptor,
                &root,
            )
            .is_err()
        );
        let mut unsafe_member = payload.clone();
        unsafe_member["source_files"][0]["archive_member_path"] = json!("../escape");
        assert!(
            parse_legacy_inventory(
                &serde_json::to_vec(&unsafe_member).expect("unsafe member JSON"),
                &descriptor,
                &root,
            )
            .is_err()
        );
        let mut wrong_total = payload;
        wrong_total["totals"]["members"] = json!(2);
        assert!(
            parse_legacy_inventory(
                &serde_json::to_vec(&wrong_total).expect("wrong total JSON"),
                &descriptor,
                &root,
            )
            .is_err()
        );
        assert!(validate_member_path("archive-manifest.json").is_err());
    }

    #[allow(clippy::too_many_lines)] // One in-memory transaction fixture binds plan, apply, and verify.
    #[test]
    fn layout_plan_apply_verify_is_create_only_and_resumable() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let legacy_content = b"legacy\n";
        let legacy_archive = legacy_archive(legacy_content);
        let larch_archive = modern_archive(directory.path(), "issue", "modern-run", b"larch\n");
        let agent_archive = modern_archive(directory.path(), "triage", "agent-run", b"agent\n");
        let inventory = json!({
            "archives": [{
                "archive_bytes": legacy_archive.len(),
                "kind": "run",
                "member_count": 1,
                "object_key": "larch/run-logs/design/legacy-run.tar.gz",
                "run_id": "legacy-run",
                "sha256": format!("{:x}", Sha256::digest(&legacy_archive)),
                "skill": "design",
                "uncompressed_bytes": legacy_content.len()
            }],
            "schema": "larch-run-log-migration-inventory-v1",
            "source_commit": "1111111111111111111111111111111111111111",
            "source_files": [{
                "archive_member_path": "result.txt",
                "archive_object_key": "larch/run-logs/design/legacy-run.tar.gz",
                "bytes": legacy_content.len(),
                "git_oid": "2222222222222222222222222222222222222222",
                "mode": "100644",
                "path": "larch-logs/design/legacy-run/result.txt",
                "sha256": format!("{:x}", Sha256::digest(legacy_content))
            }],
            "storage_root": "s3://zhupanov/larch",
            "totals": {
                "archive_bytes": legacy_archive.len(),
                "archive_objects": 1,
                "members": 1,
                "run_directories": 1,
                "source_paths": 1,
                "uncompressed_bytes": legacy_content.len()
            }
        });
        let inventory = serde_json::to_vec(&inventory).expect("inventory JSON");
        let descriptor = LegacyDescriptor {
            schema: "larch-run-log-migration-inventory-v1".to_owned(),
            source_commit: "1111111111111111111111111111111111111111".to_owned(),
            storage_root: "s3://zhupanov/larch".to_owned(),
            inventory_key: "migration/inventory.json".to_owned(),
            inventory_sha256: format!("{:x}", Sha256::digest(&inventory)),
        };
        let mappings = vec![
            LayoutMapping {
                client_repo: "larch".to_owned(),
                source: StorageRoot::parse("s3://zhupanov/larch").expect("larch source"),
                target: StorageRoot::parse("s3://zhupanov/larch/larch").expect("larch target"),
                legacy_descriptor: Some(descriptor),
            },
            LayoutMapping {
                client_repo: "agent-lint".to_owned(),
                source: StorageRoot::parse("s3://zhupanov/agent-lint").expect("agent source"),
                target: StorageRoot::parse("s3://zhupanov/larch/agent-lint").expect("agent target"),
                legacy_descriptor: None,
            },
        ];
        let store = MemoryStore::with_objects(BTreeMap::from([
            (
                "larch/run-logs/design/legacy-run.tar.gz".to_owned(),
                legacy_archive.clone(),
            ),
            (
                "larch/run-logs/issue/modern-run.tar.gz".to_owned(),
                larch_archive.clone(),
            ),
            (
                "larch/larch/run-logs/issue/modern-run.tar.gz".to_owned(),
                larch_archive.clone(),
            ),
            (
                "agent-lint/run-logs/triage/agent-run.tar.gz".to_owned(),
                agent_archive,
            ),
            ("larch/migration/inventory.json".to_owned(), inventory),
        ]));
        let plan_path = directory.path().join("plan.json");
        let report_path = directory.path().join("report.json");
        let final_path = directory.path().join("final.json");
        let work_dir = directory.path().join("work");
        let runtime = LarchRuntime::current_thread().expect("test runtime");
        let plan = runtime
            .block_on(plan_layout(
                &store,
                &mappings,
                &plan_path,
                &work_dir,
                "test-operator",
                "test",
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ))
            .expect("plan");
        assert_eq!(super::plan_archive_count(&plan).expect("plan rows"), 3);
        let first_report = runtime
            .block_on(apply_layout(&store, &plan_path, &report_path, &work_dir))
            .expect("first apply");
        assert_eq!(
            super::report_row_count(&first_report).expect("report rows"),
            3
        );
        let resumed_report = runtime
            .block_on(apply_layout(&store, &plan_path, &report_path, &work_dir))
            .expect("resumed apply");
        assert_eq!(
            super::report_row_count(&resumed_report).expect("resumed report rows"),
            3
        );
        assert!(store.has("larch/larch/run-logs/design/legacy-run.tar.gz"));
        assert!(store.has("larch/larch/run-logs/issue/modern-run.tar.gz"));
        assert!(store.has("larch/agent-lint/run-logs/triage/agent-run.tar.gz"));
        assert!(store.has("larch/run-logs/issue/modern-run.tar.gz"));
        assert!(store.has("agent-lint/run-logs/triage/agent-run.tar.gz"));
        assert_ne!(
            store.bytes("larch/larch/run-logs/design/legacy-run.tar.gz"),
            legacy_archive
        );
        assert_eq!(
            store.bytes("larch/larch/run-logs/issue/modern-run.tar.gz"),
            larch_archive
        );
        let final_report = runtime
            .block_on(verify_layout(
                &store,
                &plan_path,
                &report_path,
                &final_path,
                &work_dir,
                "migration-reports/final.json",
            ))
            .expect("verification");
        assert_eq!(
            super::value_string(&final_report, "report_sha256")
                .expect("final hash")
                .len(),
            64
        );
        assert!(store.has("larch/larch/migration-reports/final.json"));
    }
}
