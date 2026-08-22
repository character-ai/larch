//! `token` recording and staging verbs.
//!
//! Owns ledger mutation, budget checks, typed pull-request line totals,
//! sidecar staging, report rendering, pricing CLI compatibility, and
//! research-lane telemetry for the commands migrated by #8506, #8507, and
//! #8797. Analytical measurement verbs are composed in
//! `token_measurement_commands`; remaining analytical verb cutovers stay with
//! their own leaves.

use std::{
    collections::BTreeMap,
    env, fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    time::SystemTime,
};

use chrono::{DateTime, Utc};
use larch_adapters::{
    ConfinedPath, GixRepository, PathIntent, TemporaryRoot, absolute_lexical,
    assert_no_symlink_path_or_ancestors, atomic_write_utf8, read_kv_raw, write_confined_file,
};
use larch_core::report::{
    BLENDED_FALLBACK_WARNING, BlockMarkers, PullRequestLineCounts, TokenBudgetCheck, TokenCounts,
    TokenObservations, TokenVendor, active_ledger_vendor, contains_dotdot, default_ledger_basename,
    display_rates, full_report, lane_sidecar_body, lane_sidecar_name, mark_line,
    parse_token_record_sidecar, price_counts, pull_request_line_counts, read_ledger,
    read_report_inputs, render_cost_kv, render_cost_line, render_lane_report,
    render_token_report_buckets, render_token_report_json, render_token_report_markdown,
    render_token_report_summary_line, render_token_report_terse, replace_markdown_block,
    resolve_under_roots, sha256_hex, sidecar_ndjson_line, token_budget_check, transcript_sources,
    validate_lane_phase, validate_total_tokens, vendor_line,
};
use larch_core::{
    ParseOptions, RepositoryRead, bounded_ascii_identifier, parse_single_kv_row, python_str,
    sorted_paths_with_name_prefix,
};
use serde_json::Value;
use std::ffi::OsString;

#[cfg(unix)]
use std::os::unix::fs::OpenOptionsExt as _;

use crate::{
    argparse_compat::write_stdout,
    github_repository_resolution::remote_slug,
    github_service::with_github_service,
    ledger_append::{append_locked_line, restore_owner_only_permissions},
};

/// Record one step mark in the resolved token ledger.
pub fn mark(arguments: &[OsString]) -> ExitCode {
    mark_with_env(arguments, &[])
}

/// Record one step mark, resolving the ledger with caller-supplied env overrides.
///
/// Launchers learn session identity from files rather than from their own
/// environment. Passing those rows here reaches the resolver the same way the
/// retired Python child process did.
pub fn mark_with_env(arguments: &[OsString], overrides: &[(&str, String)]) -> ExitCode {
    let (rest, ledger) = match split_ledger(arguments) {
        Ok(value) => value,
        Err(message) => {
            eprintln!("token mark: {message}");
            return ExitCode::from(1);
        }
    };
    let Some(step) = rest.first().filter(|value| !value.is_empty()) else {
        eprintln!("token mark requires <step>");
        return ExitCode::from(1);
    };
    if mark_step(step, ledger.as_deref(), overrides) {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(1)
    }
}

/// Report current vendor-token usage since the latest ledger mark.
pub fn check_budget(arguments: &[OsString]) -> ExitCode {
    let values: Vec<String> = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect();
    let mut cap = None;
    let mut step = "unknown".to_owned();
    let mut index = 0;
    while index < values.len() {
        match values[index].as_str() {
            "--cap" if index + 1 < values.len() => {
                cap = values[index + 1].parse::<u64>().ok();
                index += 2;
            }
            "--step" if index + 1 < values.len() => {
                step.clone_from(&values[index + 1]);
                index += 2;
            }
            flag => {
                eprintln!("token check-budget: unknown flag: {flag}");
                return ExitCode::FAILURE;
            }
        }
    }
    let Some(cap) = cap.filter(|value| *value > 0) else {
        eprintln!("token check-budget: --cap must be >= 1");
        return ExitCode::FAILURE;
    };
    let check = budget_check(cap, &step);
    write_stdout(&format!(
        "STATUS={} TOTAL={} CAP={} STEP={}\n",
        check.status(),
        check.total,
        check.cap,
        check.step
    ))
}

/// Read the current token ledger and calculate one in-process budget check.
#[must_use]
pub fn budget_check(cap: u64, step: &str) -> TokenBudgetCheck {
    budget_check_with_env(cap, step, &[])
}

/// Calculate one budget check with the same explicit environment a retired
/// child invocation would have received.
#[must_use]
pub fn budget_check_with_env(
    cap: u64,
    step: &str,
    overrides: &[(&str, String)],
) -> TokenBudgetCheck {
    let rows = resolve_token_ledger_path(None, overrides)
        .ok()
        .flatten()
        .map_or_else(Vec::new, |path| read_ledger(&path));
    token_budget_check(&rows, cap, step)
}

/// Compute typed PR line counts and emit the legacy line-oriented wire.
pub fn compute_pr_line_counts(arguments: &[OsString]) -> ExitCode {
    let values: Vec<String> = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect();
    let options = flag_map(&values);
    let pr_raw = options.get("--pr-number").map_or("", String::as_str);
    let Some(pr_number) = positive_ascii_u64(pr_raw) else {
        return write_stdout("LINES_STATUS=skipped\nREASON=no-pr\n");
    };
    let explicit_repo = options.get("--repo").filter(|value| !value.is_empty());
    if explicit_repo.is_some_and(|repo| !is_compat_repo_slug(repo)) {
        return write_stdout("LINES_STATUS=skipped\nREASON=invalid-repo\n");
    }
    let repository = explicit_repo.cloned().or_else(|| remote_slug("origin"));
    let Some(repository) = repository else {
        return write_stdout("LINES_STATUS=unavailable\nREASON=gh-failed\n");
    };
    let Some(counts) = fetch_pr_line_counts(pr_number, &repository) else {
        return write_stdout("LINES_STATUS=unavailable\nREASON=gh-failed\n");
    };
    write_stdout(&format!(
        "LINES_STATUS=ok\nCODE_ADDED={}\nCODE_DELETED={}\nLOGS_ADDED={}\nLOGS_DELETED={}\n",
        counts.code_added, counts.code_deleted, counts.logs_added, counts.logs_deleted
    ))
}

/// Compatibility alias for `compute-pr-line-counts`.
pub fn compute_pr_lines(arguments: &[OsString]) -> ExitCode {
    compute_pr_line_counts(arguments)
}

/// Fetch and aggregate one pull request's typed file rows.
#[must_use]
pub fn fetch_pr_line_counts(pr_number: u64, repository: &str) -> Option<PullRequestLineCounts> {
    let resolved;
    let repository = if repository.is_empty() {
        resolved = remote_slug("origin")?;
        resolved.as_str()
    } else {
        repository
    };
    let (owner, repo) = split_compat_repo_slug(repository)?;
    with_github_service(async |service, cancellation| {
        service
            .pull_request_files(cancellation, owner, repo, pr_number)
            .await
            .map(|files| pull_request_line_counts(&files))
            .map_err(|error| error.to_string())
    })
    .ok()
}

fn positive_ascii_u64(raw: &str) -> Option<u64> {
    (!raw.is_empty() && raw.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| raw.parse::<u64>().ok())
        .flatten()
        .filter(|value| *value > 0)
}

fn is_compat_repo_slug(raw: &str) -> bool {
    split_compat_repo_slug(raw).is_some()
}

fn split_compat_repo_slug(raw: &str) -> Option<(&str, &str)> {
    let (owner, repo) = raw.split_once('/')?;
    let valid = |segment: &str| {
        !segment.is_empty()
            && segment
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || b"_.-".contains(&byte))
    };
    (valid(owner) && valid(repo) && !repo.contains('/')).then_some((owner, repo))
}

/// Record one vendor usage row in the resolved token ledger.
pub fn record_vendor(arguments: &[OsString]) -> ExitCode {
    let (rest, ledger) = match split_ledger(arguments) {
        Ok(value) => value,
        Err(message) => {
            eprintln!("token record-vendor: {message}");
            return ExitCode::from(1);
        }
    };
    let Some(vendor) = rest.first().filter(|value| !value.is_empty()) else {
        eprintln!("token record-vendor requires <vendor>");
        return ExitCode::from(1);
    };
    let mut vals = VendorValues::default();
    for option in rest.iter().skip(1) {
        let Some(row) = parse_single_kv_row(option, ParseOptions::legacy()) else {
            eprintln!("token record-vendor: unknown argument: {option}");
            return ExitCode::from(1);
        };
        let key = row.key();
        let value = row.value();
        match key {
            "raw" => value.clone_into(&mut vals.raw),
            "model" => value.clone_into(&mut vals.model),
            "input" | "output" | "cache_read" | "cache_create" | "total" => {
                if !value.bytes().all(|byte| byte.is_ascii_digit()) {
                    eprintln!("token record-vendor: {key} must be a non-negative integer");
                    return ExitCode::from(1);
                }
                let parsed = value.parse::<u64>().unwrap_or(0);
                match key {
                    "input" => vals.input = parsed,
                    "output" => vals.output = parsed,
                    "cache_read" => vals.cache_read = parsed,
                    "cache_create" => vals.cache_create = parsed,
                    "total" => vals.total = parsed,
                    _ => {}
                }
            }
            _ => {
                eprintln!("token record-vendor: unknown argument: {option}");
                return ExitCode::from(1);
            }
        }
    }
    match record_vendor_values(vendor, &vals, ledger.as_deref()) {
        RecordOutcome::Ok => ExitCode::SUCCESS,
        RecordOutcome::Usage(message) => {
            eprintln!("token record-vendor: {message}");
            ExitCode::from(1)
        }
    }
}

/// Best-effort vendor append used by launchers that must not fail the vendor run.
pub fn record_vendor_best_effort(arguments: impl IntoIterator<Item = OsString>) {
    let values: Vec<OsString> = arguments.into_iter().collect();
    let _ignored = record_vendor(&values);
}

/// Append one active-ledger vendor row from a KEY=value sidecar.
pub fn record_vendor_sidecar(arguments: &[OsString]) -> ExitCode {
    let (rest, ledger) = match split_ledger(arguments) {
        Ok(value) => value,
        Err(message) => {
            eprintln!("token record-vendor-sidecar: {message}");
            return ExitCode::from(2);
        }
    };
    let options = flag_map(&rest);
    let input_path = options.get("--input").map(PathBuf::from);
    match record_vendor_from_sidecar(input_path.as_deref(), ledger.as_deref()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("token record-vendor-sidecar: {message}");
            ExitCode::from(2)
        }
    }
}

/// Best-effort sidecar→ledger append for launchers.
pub fn record_vendor_sidecar_best_effort(arguments: impl IntoIterator<Item = OsString>) {
    let values: Vec<OsString> = arguments.into_iter().collect();
    let _ignored = record_vendor_sidecar(&values);
}

/// Append one staging NDJSON row from a KEY=value sidecar.
pub fn append_record(arguments: &[OsString]) -> ExitCode {
    let options = flag_map(
        &arguments
            .iter()
            .map(|value| value.to_string_lossy().into_owned())
            .collect::<Vec<_>>(),
    );
    let Some(tmpdir) = options.get("--tmpdir").map(PathBuf::from) else {
        eprintln!("token append-record: '--tmpdir'");
        return ExitCode::from(2);
    };
    let input_path = options.get("--input").map(PathBuf::from);
    match append_token_record_from_sidecar(input_path.as_deref(), &tmpdir) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("token append-record: {message}");
            ExitCode::from(2)
        }
    }
}

/// Print the resolved ledger path and its raw contents.
pub fn dump(arguments: &[OsString]) -> ExitCode {
    let (_rest, ledger) = match split_ledger(arguments) {
        Ok(value) => value,
        Err(message) => {
            eprintln!("token dump: {message}");
            return ExitCode::from(1);
        }
    };
    let path = match resolve_token_ledger_path(ledger.as_deref(), &[]) {
        Ok(path) => path,
        Err(message) => {
            eprintln!("token dump: {message}");
            return ExitCode::from(1);
        }
    };
    let Some(path) = path else {
        return ExitCode::SUCCESS;
    };
    println!("{}", path.display());
    if path.is_file()
        && fs::metadata(&path)
            .map(|metadata| metadata.len() > 0)
            .unwrap_or(false)
    {
        match fs::read_to_string(&path) {
            Ok(text) => print!("{text}"),
            Err(error) => eprintln!("token dump: {error}"),
        }
    }
    ExitCode::SUCCESS
}

/// Write one research/validation lane token sidecar.
pub fn lane_write(arguments: &[OsString]) -> ExitCode {
    let options = flag_map(
        &arguments
            .iter()
            .map(|value| value.to_string_lossy().into_owned())
            .collect::<Vec<_>>(),
    );
    for required in ["--dir", "--phase", "--lane", "--tool", "--total-tokens"] {
        if !options.contains_key(required) {
            eprintln!("token lane-write: '{required}'");
            return ExitCode::from(1);
        }
    }
    let dir = options["--dir"].as_str();
    let phase = options["--phase"].as_str();
    let lane = options["--lane"].as_str();
    let tool = options["--tool"].as_str();
    let total_tokens = options["--total-tokens"].as_str();
    match write_lane(Path::new(dir), phase, lane, tool, total_tokens) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("token lane-write: {message}");
            ExitCode::from(1)
        }
    }
}

/// Render the research lane token-spend summary.
pub fn lane_report(arguments: &[OsString]) -> ExitCode {
    let options = flag_map(
        &arguments
            .iter()
            .map(|value| value.to_string_lossy().into_owned())
            .collect::<Vec<_>>(),
    );
    let Some(dir) = options.get("--dir") else {
        eprintln!("token lane-report: '--dir'");
        return ExitCode::from(1);
    };
    match report_lane(Path::new(dir)) {
        Ok(text) => {
            println!("{text}");
            ExitCode::SUCCESS
        }
        Err(message) => {
            eprintln!("token lane-report: {message}");
            ExitCode::from(1)
        }
    }
}

const COST_USAGE: &str = "Usage: cli.py token cost [--per-bucket flags...] [--claude-tokens N ...]";
const RENDER_COST_LINE_USAGE: &str =
    "Usage: cli.py token render-cost-line [--per-bucket flags...] [--quiet-on-empty]";

#[derive(Default)]
struct ReportArguments {
    mode: Option<String>,
    format: String,
    output: Option<PathBuf>,
    ledger: Option<String>,
    transcript: Option<PathBuf>,
    session_dir: Option<PathBuf>,
    source_file: Option<PathBuf>,
    implement_tmpdir: Option<PathBuf>,
    append: Option<PathBuf>,
    buckets: bool,
    vendor: Option<String>,
    scrape_output: Option<PathBuf>,
    scrape_timing_output: Option<PathBuf>,
    scrape_sidecars: Vec<(String, PathBuf)>,
    scrape_timing_sidecars: Vec<(String, PathBuf)>,
}

/// Render a token report while preserving the historical fail-open envelope.
pub fn report(arguments: &[OsString]) -> ExitCode {
    match report_result(arguments) {
        Ok(status) => status,
        Err(message) => {
            eprintln!("Token report unavailable: {message}");
            ExitCode::SUCCESS
        }
    }
}

/// Render a token report for an in-process caller that needs the failure detail.
pub fn report_result(arguments: &[OsString]) -> Result<ExitCode, String> {
    report_inner(arguments)
}

fn report_inner(arguments: &[OsString]) -> Result<ExitCode, String> {
    let options = parse_report_arguments(arguments)?;
    if options.scrape_output.is_some() {
        scrape_sidecars(&options)?;
        return Ok(ExitCode::SUCCESS);
    }
    let overrides: Vec<(&str, String)> = options
        .implement_tmpdir
        .as_ref()
        .map(|path| vec![("IMPLEMENT_TMPDIR", path.to_string_lossy().into_owned())])
        .unwrap_or_default();
    let ledger = resolve_token_ledger_path(options.ledger.as_deref(), &overrides)?
        .ok_or_else(|| "ledger path unavailable".to_owned())?;
    let transcript_paths = report_transcript_paths(&options)?;
    let inputs =
        read_report_inputs(&ledger, &transcript_paths).map_err(|error| error.to_string())?;
    if options.buckets {
        let vendor = options
            .vendor
            .as_deref()
            .and_then(token_vendor)
            .ok_or_else(|| "unknown vendor".to_owned())?;
        return Ok(write_stdout(&format!(
            "{}\n",
            render_token_report_buckets(&inputs, vendor)
        )));
    }
    let mode = options
        .mode
        .as_deref()
        .ok_or_else(|| "missing report mode".to_owned())?;
    if !matches!(options.format.as_str(), "json" | "markdown") {
        return Err(format!("unknown format: {}", options.format));
    }
    let rendered = match (mode, options.format.as_str()) {
        ("summary", "json") => {
            render_token_report_json(&larch_core::report::summary_report(&inputs))
                .map_err(|error| error.to_string())?
        }
        ("summary", _) => render_token_report_summary_line(&inputs),
        ("terse", _) => render_token_report_terse(&inputs),
        ("full", "json") => {
            render_token_report_json(&full_report(&inputs)).map_err(|error| error.to_string())?
        }
        ("full", _) => render_token_report_markdown(&inputs),
        _ => return Err("missing report mode".to_owned()),
    };
    if let Some(target) = options.append.as_deref() {
        append_report_block(target, &rendered)?;
    }
    let text = format!("{rendered}\n");
    if mode == "full"
        && let Some(output) = options.output.as_deref()
    {
        write_report_output(output, &text)?;
    } else if options.append.is_none() {
        return Ok(write_stdout(&text));
    }
    Ok(ExitCode::SUCCESS)
}

#[allow(clippy::too_many_lines)] // Legacy flags stay adjacent in parser order for compatibility review.
fn parse_report_arguments(arguments: &[OsString]) -> Result<ReportArguments, String> {
    let values: Vec<String> = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect();
    let mut options = ReportArguments {
        format: "markdown".to_owned(),
        ..ReportArguments::default()
    };
    let mut index = 0;
    while index < values.len() {
        let value = &values[index];
        match value.as_str() {
            "--since-last-mark" | "--terse" => {
                options.mode = Some("terse".to_owned());
                index += 1;
            }
            "--summary" => {
                options.mode = Some("summary".to_owned());
                index += 1;
            }
            "--full" => {
                options.mode = Some("full".to_owned());
                index += 1;
            }
            "--markdown" => {
                "markdown".clone_into(&mut options.format);
                index += 1;
            }
            "--format" => {
                options.format = report_value(&values, index)?;
                index += 2;
            }
            "--output" => {
                options.output = Some(PathBuf::from(report_value(&values, index)?));
                index += 2;
            }
            "--ledger" => {
                options.ledger = Some(report_value(&values, index)?);
                index += 2;
            }
            "--transcript" => {
                options.transcript = Some(PathBuf::from(report_value(&values, index)?));
                index += 2;
            }
            "--session-dir" => {
                options.session_dir = Some(PathBuf::from(report_value(&values, index)?));
                index += 2;
            }
            "--source-file" => {
                options.source_file = Some(PathBuf::from(report_value(&values, index)?));
                index += 2;
            }
            "--implement-tmpdir" => {
                options.implement_tmpdir = Some(PathBuf::from(report_value(&values, index)?));
                index += 2;
            }
            "--append-token-report" => {
                options.append = Some(PathBuf::from(report_value(&values, index)?));
                options.mode = Some("full".to_owned());
                index += 2;
            }
            "--buckets" => {
                options.buckets = true;
                index += 1;
            }
            "--vendor" => {
                options.vendor = Some(report_value(&values, index)?);
                index += 2;
            }
            "--scrape-sidecar" | "--scrape-timing-sidecar" => {
                let raw = report_value(&values, index)?;
                let Some(row) = parse_single_kv_row(&raw, ParseOptions::legacy()) else {
                    return Err(format!("invalid sidecar: {raw}"));
                };
                let tool = row.key();
                let path = row.value();
                if tool.is_empty() || path.is_empty() {
                    return Err(format!("invalid sidecar: {raw}"));
                }
                let entry = (tool.to_owned(), PathBuf::from(path));
                if value == "--scrape-sidecar" {
                    options.scrape_sidecars.push(entry);
                } else {
                    options.scrape_timing_sidecars.push(entry);
                }
                index += 2;
            }
            "--scrape-run-output" => {
                options.scrape_output = Some(PathBuf::from(report_value(&values, index)?));
                index += 2;
            }
            "--scrape-timing-output" => {
                options.scrape_timing_output = Some(PathBuf::from(report_value(&values, index)?));
                index += 2;
            }
            _ => return Err(format!("unknown flag: {value}")),
        }
    }
    Ok(options)
}

fn report_value(values: &[String], index: usize) -> Result<String, String> {
    values
        .get(index + 1)
        .cloned()
        .ok_or_else(|| "list index out of range".to_owned())
}

fn token_vendor(value: &str) -> Option<TokenVendor> {
    match value {
        "claude" => Some(TokenVendor::Claude),
        "codex" => Some(TokenVendor::Codex),
        "cursor" => Some(TokenVendor::Cursor),
        "claude_sub" => Some(TokenVendor::ClaudeSub),
        _ => None,
    }
}

fn append_report_block(target: &Path, body: &str) -> Result<(), String> {
    let target = absolute_lexical(target);
    assert_no_symlink_path_or_ancestors(&target)?;
    let parent = target
        .parent()
        .ok_or_else(|| "append token report target has no parent".to_owned())?;
    fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    let markers = BlockMarkers::new("token-report-begin", "token-report-end")
        .map_err(|error| error.to_string())?;
    let block = format!(
        "<!-- token-report-begin -->\n## Token Report\n\n{body}\n<!-- token-report-end -->\n"
    );
    replace_markdown_block(&target, &block, &markers, "token report")
        .map_err(|error| error.to_string())?;
    assert_no_symlink_path_or_ancestors(&target)
}

fn write_report_output(output: &Path, text: &str) -> Result<(), String> {
    let output = absolute_lexical(output);
    assert_no_symlink_path_or_ancestors(&output)?;
    let parent = output
        .parent()
        .ok_or_else(|| "token report output has no parent".to_owned())?;
    fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    write_confined_file(&output, text, 0o600, "token report")
}

/// Price token buckets and render the historical key-value output.
pub fn cost(arguments: &[OsString]) -> ExitCode {
    render_cost(arguments, false)
}

/// Price token buckets and render the historical one-line output.
pub fn render_cost_line_command(arguments: &[OsString]) -> ExitCode {
    render_cost(arguments, true)
}

fn render_cost(arguments: &[OsString], line: bool) -> ExitCode {
    let mut values: Vec<String> = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect();
    let quiet = if line {
        let quiet = values.iter().any(|value| value == "--quiet-on-empty");
        values.retain(|value| value != "--quiet-on-empty");
        quiet
    } else {
        false
    };
    if values
        .iter()
        .any(|value| matches!(value.as_str(), "-h" | "--help"))
    {
        eprintln!(
            "{}",
            if line {
                RENDER_COST_LINE_USAGE
            } else {
                COST_USAGE
            }
        );
        return ExitCode::SUCCESS;
    }
    let (counts, claude_model) = match TokenCounts::from_cost_argv(&values) {
        Ok(parsed) => parsed,
        Err(error) => {
            eprintln!(
                "{}: {error}",
                if line {
                    "token render-cost-line"
                } else {
                    "token cost"
                }
            );
            return ExitCode::from(2);
        }
    };
    if line && quiet && counts.is_zero() {
        return ExitCode::SUCCESS;
    }
    let environment: BTreeMap<String, String> = env::vars().collect();
    let mut observations = TokenObservations::default();
    let rates = display_rates(&environment, &claude_model, &mut observations);
    let priced = price_counts(&counts, &rates);
    if priced.blended_fallback {
        eprintln!("{BLENDED_FALLBACK_WARNING}");
    }
    if line {
        write_stdout(&render_cost_line(&priced))
    } else {
        write_stdout(&render_cost_kv(&priced))
    }
}

#[derive(Clone, Debug)]
pub struct ClaudeSource {
    pub transcript: PathBuf,
    pub session_dir: Option<PathBuf>,
    pub session_uuid: String,
}

/// Resolve the active Claude transcript source in-process.
///
/// Mirrors the retired `token claude-source` Python verb: an explicit source
/// snapshot (positional argument or `LARCH_CLAUDE_SOURCE_FILE`) takes priority,
/// falling back to scanning the Claude project directory. In-process callers use
/// this instead of spawning the former Python child (#8557).
pub fn resolve_claude_source(source_file: Option<PathBuf>) -> Result<ClaudeSource, String> {
    let source_file =
        source_file.or_else(|| env::var_os("LARCH_CLAUDE_SOURCE_FILE").map(PathBuf::from));
    source_file
        .as_deref()
        .and_then(claude_source_from_snapshot)
        .map_or_else(claude_source_from_project, Ok)
}

/// Resolve and print the active Claude transcript source as KV stdout.
///
/// Migrated from the retired `token claude-source` Python verb (#8557): prints
/// `TRANSCRIPT_PATH`, then `SESSION_DIR` and `SESSION_UUID` when present, exiting
/// zero; on failure prints `STATUS=unavailable` with the reason and exits one.
pub fn claude_source(arguments: &[OsString]) -> ExitCode {
    let source_file = arguments.first().map(PathBuf::from);
    match resolve_claude_source(source_file) {
        Ok(source) => {
            let mut lines = vec![format!("TRANSCRIPT_PATH={}", source.transcript.display())];
            if let Some(session_dir) = &source.session_dir {
                lines.push(format!("SESSION_DIR={}", session_dir.display()));
            }
            if !source.session_uuid.is_empty() {
                lines.push(format!("SESSION_UUID={}", source.session_uuid));
            }
            let mut rendered = lines.join("\n");
            rendered.push('\n');
            write_stdout(&rendered)
        }
        Err(reason) => {
            let _ = write_stdout(&format!("STATUS=unavailable\nREASON={reason}\n"));
            ExitCode::from(1)
        }
    }
}

fn report_transcript_paths(options: &ReportArguments) -> Result<Vec<PathBuf>, String> {
    if let Some(transcript) = options.transcript.as_deref() {
        return transcript_sources(transcript, options.session_dir.as_deref())
            .map_err(|error| error.to_string());
    }
    let source = resolve_claude_source(options.source_file.clone())?;
    transcript_sources(&source.transcript, source.session_dir.as_deref())
        .map_err(|error| error.to_string())
}

/// Resolve a path the way Python's non-strict `Path.resolve()` does.
///
/// Canonicalizes the deepest existing ancestor (following symlinks) and
/// re-appends the missing tail. Unlike `fs::canonicalize`, the path itself need
/// not exist, matching the retired Python `_validate_snapshot_replay`, which
/// resolves a `SESSION_DIR` that a bootstrap snapshot names before its session
/// directory is created.
fn resolve_lenient(path: &Path) -> PathBuf {
    for ancestor in path.ancestors() {
        if let Ok(canonical) = fs::canonicalize(ancestor) {
            let tail = path
                .strip_prefix(ancestor)
                .unwrap_or_else(|_| Path::new(""));
            // Joining an empty tail would append a trailing separator; a fully
            // existing path resolves to the canonical form with no trailing slash,
            // matching Python's `Path.resolve()`.
            return if tail.as_os_str().is_empty() {
                canonical
            } else {
                canonical.join(tail)
            };
        }
    }
    absolute_lexical(path)
}

fn claude_source_from_snapshot(source_file: &Path) -> Option<ClaudeSource> {
    if !source_file.is_file() {
        return None;
    }
    let fields: BTreeMap<String, String> = read_kv_raw(source_file).ok()?.into_iter().collect();
    let transcript = fields.get("TRANSCRIPT_PATH")?;
    let session_dir = fields.get("SESSION_DIR")?;
    let session_uuid = fields.get("SESSION_UUID")?;
    if !bounded_ascii_identifier(session_uuid, false) {
        return None;
    }
    let transcript = fs::canonicalize(transcript).ok()?;
    let session_dir = resolve_lenient(Path::new(session_dir));
    if !transcript.is_file() {
        return None;
    }
    let under_session = transcript.starts_with(&session_dir);
    let under_project = claude_project_dir()
        .ok()
        .is_some_and(|project_dir| transcript.starts_with(project_dir));
    if !under_session && !under_project {
        return None;
    }
    Some(ClaudeSource {
        transcript,
        session_dir: Some(session_dir),
        session_uuid: session_uuid.clone(),
    })
}

fn claude_source_from_project() -> Result<ClaudeSource, String> {
    let project_dir = claude_project_dir()?;
    let requested = requested_claude_session();
    let transcript = if requested.is_empty() {
        let mut transcripts: Vec<PathBuf> = fs::read_dir(&project_dir)
            .map_err(|error| error.to_string())?
            .filter_map(Result::ok)
            .map(|entry| entry.path())
            .filter(|path| {
                path.extension()
                    .is_some_and(|extension| extension == "jsonl")
            })
            .filter(|path| path.is_file())
            .collect();
        transcripts.sort_by(|left, right| {
            let left_time = fs::metadata(left)
                .and_then(|metadata| metadata.modified())
                .unwrap_or(SystemTime::UNIX_EPOCH);
            let right_time = fs::metadata(right)
                .and_then(|metadata| metadata.modified())
                .unwrap_or(SystemTime::UNIX_EPOCH);
            right_time.cmp(&left_time).then_with(|| right.cmp(left))
        });
        transcripts
            .into_iter()
            .next()
            .ok_or_else(|| "no Claude transcript jsonl files found".to_owned())?
    } else {
        let candidate = project_dir.join(format!("{requested}.jsonl"));
        if !candidate.is_file() {
            return Err(format!(
                "Claude transcript for session {requested} not found"
            ));
        }
        candidate
    };
    let stem = transcript
        .file_stem()
        .ok_or_else(|| "Claude transcript source unavailable".to_owned())?;
    let session_uuid = stem.to_string_lossy().into_owned();
    let session_dir = project_dir.join(stem);
    Ok(ClaudeSource {
        transcript,
        session_dir: Some(session_dir),
        session_uuid,
    })
}

fn claude_project_dir() -> Result<PathBuf, String> {
    let cwd = env::current_dir().map_err(|_| "not inside a git repository".to_owned())?;
    let repository =
        GixRepository::discover(&cwd).map_err(|_| "not inside a git repository".to_owned())?;
    let work_dir = repository
        .location()
        .work_dir
        .ok_or_else(|| "not inside a git repository".to_owned())?;
    let repo_root = fs::canonicalize(PathBuf::from(
        String::from_utf8_lossy(work_dir.as_bytes()).into_owned(),
    ))
    .map_err(|_| "not inside a git repository".to_owned())?;
    let home = env::var_os("HOME").ok_or_else(|| "HOME is not set".to_owned())?;
    let project_dir = PathBuf::from(home)
        .join(".claude")
        .join("projects")
        .join(repo_root.to_string_lossy().replace('/', "-"));
    if !project_dir.is_dir() {
        return Err("Claude project directory not found".to_owned());
    }
    Ok(project_dir)
}

fn requested_claude_session() -> String {
    for key in ["LARCH_CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID"] {
        let value = env::var(key).unwrap_or_default();
        if bounded_ascii_identifier(&value, false) {
            return value;
        }
    }
    String::new()
}

fn scrape_sidecars(options: &ReportArguments) -> Result<(), String> {
    let tmpdir = options
        .implement_tmpdir
        .as_deref()
        .ok_or_else(|| "scrape mode requires --implement-tmpdir".to_owned())?;
    let root = temporary_root(tmpdir)?;
    let output = confined_scrape_output(
        &root,
        options
            .scrape_output
            .as_deref()
            .ok_or_else(|| "scrape mode requires --implement-tmpdir".to_owned())?,
    )?;
    let timing_output = options
        .scrape_timing_output
        .as_deref()
        .map(|path| confined_scrape_output(&root, path))
        .transpose()?;
    let token_lines = scrape_token_lines(&options.scrape_sidecars)?;
    if !token_lines.is_empty() {
        atomic_write_utf8(&output, &format!("{}\n", token_lines.join("\n")), 0o600)
            .map_err(|error| error.to_string())?;
    }
    if let Some(output) = timing_output {
        let timing_lines = scrape_timing_lines(&options.scrape_timing_sidecars)?;
        if !timing_lines.is_empty() {
            atomic_write_utf8(&output, &format!("{}\n", timing_lines.join("\n")), 0o600)
                .map_err(|error| error.to_string())?;
        }
    }
    Ok(())
}

fn temporary_root(path: &Path) -> Result<TemporaryRoot, String> {
    let absolute = absolute_lexical(path);
    assert_no_symlink_path_or_ancestors(&absolute)?;
    let canonical = fs::canonicalize(&absolute).map_err(|error| error.to_string())?;
    TemporaryRoot::resolve(Some(&canonical)).map_err(|error| error.to_string())
}

fn confined_scrape_output(root: &TemporaryRoot, output: &Path) -> Result<ConfinedPath, String> {
    let absolute = absolute_lexical(output);
    assert_no_symlink_path_or_ancestors(&absolute)?;
    let parent = absolute
        .parent()
        .ok_or_else(|| "scrape output must stay under --implement-tmpdir".to_owned())?;
    let parent = fs::canonicalize(parent).map_err(|error| error.to_string())?;
    if parent != root.path() && !parent.starts_with(root.path()) {
        return Err("scrape output must stay under --implement-tmpdir".to_owned());
    }
    let name = absolute
        .file_name()
        .ok_or_else(|| "scrape output must stay under --implement-tmpdir".to_owned())?;
    root.confine(parent.join(name), PathIntent::Write)
        .map_err(|error| error.to_string())
}

fn scrape_token_lines(entries: &[(String, PathBuf)]) -> Result<Vec<String>, String> {
    let mut lines = Vec::new();
    for (tool, path) in entries {
        if !path.is_file() {
            continue;
        }
        let body = fs::read_to_string(path).map_err(|error| error.to_string())?;
        let Ok(Value::Object(fields)) = serde_json::from_str(&body) else {
            continue;
        };
        let input = sidecar_integer(fields.get("input_tokens"));
        let output = sidecar_integer(fields.get("output_tokens"));
        let cache_read = sidecar_integer(fields.get("cache_read_tokens"));
        let cache_create = sidecar_integer(fields.get("cache_create_tokens"));
        let mut total = sidecar_integer(fields.get("total_tokens"));
        if total == 0 {
            total = input
                .saturating_add(output)
                .saturating_add(cache_read)
                .saturating_add(cache_create);
        }
        let has_token_field = [
            "input_tokens",
            "output_tokens",
            "cache_read_tokens",
            "cache_create_tokens",
            "total_tokens",
        ]
        .iter()
        .any(|key| fields.contains_key(*key));
        if total == 0 && !has_token_field {
            continue;
        }
        let mut record = BTreeMap::from([
            ("cache_create_tokens".to_owned(), Value::from(cache_create)),
            ("cache_read_tokens".to_owned(), Value::from(cache_read)),
            ("input_tokens".to_owned(), Value::from(input)),
            ("output_tokens".to_owned(), Value::from(output)),
            ("tool".to_owned(), Value::from(tool.clone())),
            ("total_tokens".to_owned(), Value::from(total)),
        ]);
        let model = python_str(fields.get("model"));
        if !model.is_empty() {
            let _prior = record.insert("model".to_owned(), Value::from(model));
        }
        let record = record.into_iter().collect();
        lines.push(render_token_report_json(&record).map_err(|error| error.to_string())?);
    }
    Ok(lines)
}

fn scrape_timing_lines(entries: &[(String, PathBuf)]) -> Result<Vec<String>, String> {
    let mut lines = Vec::new();
    for (tool, path) in entries {
        if !path.is_file() {
            continue;
        }
        let body = fs::read_to_string(path).map_err(|error| error.to_string())?;
        let Ok(Value::Object(fields)) = serde_json::from_str(&body) else {
            continue;
        };
        let duration = fields
            .get("duration_ms")
            .or_else(|| fields.get("elapsed_ms"))
            .and_then(sidecar_duration)
            .filter(|value| *value > 0);
        let Some(duration) = duration else {
            continue;
        };
        let record = BTreeMap::from([
            ("duration_ms".to_owned(), Value::from(duration)),
            ("tool".to_owned(), Value::from(tool.clone())),
        ]);
        let record = record.into_iter().collect();
        lines.push(render_token_report_json(&record).map_err(|error| error.to_string())?);
    }
    Ok(lines)
}

fn sidecar_integer(value: Option<&Value>) -> i64 {
    match value {
        Some(Value::Bool(flag)) => i64::from(*flag),
        Some(Value::Number(_)) => larch_core::report::safe_int(value, 0),
        Some(Value::String(text)) => text.trim().parse::<i64>().unwrap_or(0),
        None | Some(Value::Null | Value::Array(_) | Value::Object(_)) => 0,
    }
}

fn sidecar_duration(value: &Value) -> Option<i64> {
    match value {
        Value::Bool(flag) => Some(i64::from(*flag)),
        Value::Number(_) => Some(larch_core::report::safe_int(Some(value), 0)),
        Value::String(text) => text.trim().parse::<i64>().ok(),
        Value::Null | Value::Array(_) | Value::Object(_) => None,
    }
}

#[derive(Clone, Debug)]
enum RecordOutcome {
    Ok,
    Usage(String),
}

#[derive(Clone, Debug, Default)]
struct VendorValues {
    input: u64,
    output: u64,
    cache_read: u64,
    cache_create: u64,
    total: u64,
    raw: String,
    model: String,
}

fn mark_step(step: &str, ledger: Option<&str>, overrides: &[(&str, String)]) -> bool {
    let path = match resolve_token_ledger_path(ledger, overrides) {
        Ok(Some(path)) => path,
        Ok(None) => return true,
        Err(message) => {
            eprintln!("token mark: {message}");
            return false;
        }
    };
    let line = mark_line(step, &timestamp_utc());
    match append_jsonl(&path, &line) {
        Ok(()) => true,
        Err(AppendError::Invalid(message)) => {
            eprintln!("token mark: {message}");
            false
        }
        Err(AppendError::Io(error)) => {
            eprintln!("token mark: write skipped: {error}");
            true
        }
    }
}

fn record_vendor_values(vendor: &str, vals: &VendorValues, ledger: Option<&str>) -> RecordOutcome {
    let path = match resolve_token_ledger_path(ledger, &[]) {
        Ok(Some(path)) => path,
        Ok(None) => return RecordOutcome::Ok,
        Err(message) => return RecordOutcome::Usage(message),
    };
    let line = match vendor_line(
        vendor,
        vals.input,
        vals.output,
        vals.cache_read,
        vals.cache_create,
        vals.total,
        &vals.raw,
        &vals.model,
        &timestamp_utc(),
    ) {
        Ok(line) => line,
        Err(message) => return RecordOutcome::Usage(message),
    };
    match append_jsonl(&path, &line) {
        Ok(()) => RecordOutcome::Ok,
        Err(AppendError::Invalid(message)) => RecordOutcome::Usage(message),
        Err(AppendError::Io(error)) => {
            eprintln!("token record-vendor: write skipped: {error}");
            RecordOutcome::Ok
        }
    }
}

fn record_vendor_from_sidecar(
    input_path: Option<&Path>,
    ledger: Option<&str>,
) -> Result<(), String> {
    let Some(input_path) = input_path else {
        return Ok(());
    };
    let Some(payload) = read_sidecar_payload(input_path) else {
        return Ok(());
    };
    let mut vendor = payload.tool.clone();
    if vendor == "claude" {
        "claude_sub".clone_into(&mut vendor);
    }
    let Some(active) = active_ledger_vendor(&vendor) else {
        let raw_tool = raw_tool_from_sidecar(input_path);
        let raw_note = if !raw_tool.is_empty() && raw_tool != vendor {
            format!(" (raw TOOL={raw_tool})")
        } else {
            String::new()
        };
        eprintln!(
            "token record-vendor-sidecar: unsupported TOOL={vendor}{raw_note}; active-ledger append skipped for {}",
            input_path.display()
        );
        return Ok(());
    };
    let Some(path) = resolve_token_ledger_path(ledger, &[])? else {
        return Ok(());
    };
    let line = vendor_line(
        active,
        payload.input,
        payload.output,
        payload.cache_read,
        payload.cache_create,
        payload.total,
        &payload.raw,
        &payload.model,
        &timestamp_utc(),
    )?;
    if let Err(error) = append_jsonl(&path, &line) {
        match error {
            AppendError::Invalid(message) => return Err(message),
            AppendError::Io(error) => {
                eprintln!("token record-vendor: write skipped: {error}");
            }
        }
    }
    Ok(())
}

fn append_token_record_from_sidecar(
    input_path: Option<&Path>,
    tmpdir: &Path,
) -> Result<(), String> {
    if !tmpdir.is_dir() {
        return Err("--tmpdir must exist".to_owned());
    }
    let Some(input_path) = input_path else {
        return Ok(());
    };
    let Some(payload) = read_sidecar_payload(input_path) else {
        let absent_or_empty = !input_path.is_file()
            || fs::metadata(input_path)
                .map(|metadata| metadata.len() == 0)
                .unwrap_or(true);
        if absent_or_empty && !tmpdir.join("execution-issues.md").exists() {
            eprintln!(
                "append token record: token sidecar absent: {}",
                input_path.display()
            );
        }
        return Ok(());
    };
    let target = tmpdir.join("token-report.ndjson");
    append_plain(&target, &sidecar_ndjson_line(&payload)).map_err(|error| error.to_string())?;
    Ok(())
}

fn write_lane(
    root: &Path,
    phase: &str,
    lane: &str,
    tool: &str,
    total_tokens: &str,
) -> Result<(), String> {
    validate_research_dir(root)?;
    validate_lane_phase(phase)?;
    validate_total_tokens(total_tokens)?;
    fs::create_dir_all(root).map_err(|error| error.to_string())?;
    let path = root.join(lane_sidecar_name(phase, lane));
    fs::write(&path, lane_sidecar_body(phase, lane, tool, total_tokens))
        .map_err(|error| error.to_string())
}

fn report_lane(root: &Path) -> Result<String, String> {
    validate_research_dir(root)?;
    if !root.is_dir() {
        return Ok(render_lane_report(
            &BTreeMap::new(),
            &BTreeMap::new(),
            &BTreeMap::new(),
            &BTreeMap::new(),
            0.0,
            true,
        ));
    }
    let mut lanes: BTreeMap<&'static str, Vec<String>> =
        BTreeMap::from([("research", Vec::new()), ("validation", Vec::new())]);
    let mut totals: BTreeMap<&'static str, u64> =
        BTreeMap::from([("research", 0), ("validation", 0)]);
    let mut measured: BTreeMap<&'static str, u64> =
        BTreeMap::from([("research", 0), ("validation", 0)]);
    let mut unknown: BTreeMap<&'static str, u64> =
        BTreeMap::from([("research", 0), ("validation", 0)]);
    let entries = sorted_paths_with_name_prefix(
        fs::read_dir(root).map_err(|error| error.to_string())?,
        "lane-tokens-",
    )
    .into_iter()
    .filter(|path| path.extension().is_some_and(|ext| ext == "txt"));
    for sidecar in entries {
        let Ok(rows) = read_kv_raw(&sidecar) else {
            continue;
        };
        let kv: BTreeMap<String, String> = rows.into_iter().collect::<BTreeMap<_, _>>();
        let phase = kv.get("PHASE").map_or("", String::as_str);
        let phase_key = match phase {
            "research" => "research",
            "validation" => "validation",
            _ => continue,
        };
        lanes
            .entry(phase_key)
            .or_default()
            .push(kv.get("LANE").cloned().unwrap_or_default());
        let total = kv.get("TOTAL_TOKENS").map_or("", String::as_str);
        if !total.is_empty() && total.bytes().all(|byte: u8| byte.is_ascii_digit()) {
            *totals.entry(phase_key).or_default() += total.parse::<u64>().unwrap_or(0);
            *measured.entry(phase_key).or_default() += 1;
        } else {
            *unknown.entry(phase_key).or_default() += 1;
        }
    }
    let rate = env::var("LARCH_TOKEN_RATE_PER_M")
        .ok()
        .and_then(|raw| raw.parse::<f64>().ok())
        .unwrap_or(0.0);
    Ok(render_lane_report(
        &lanes, &totals, &measured, &unknown, rate, false,
    ))
}

fn read_sidecar_payload(path: &Path) -> Option<larch_core::report::TokenSidecarPayload> {
    if !path.is_file()
        || fs::metadata(path)
            .map(|metadata| metadata.len() == 0)
            .unwrap_or(true)
    {
        return None;
    }
    let rows = read_kv_raw(path).ok()?;
    let kv: BTreeMap<String, String> = rows.into_iter().collect();
    parse_token_record_sidecar(&kv)
}

fn raw_tool_from_sidecar(path: &Path) -> String {
    read_kv_raw(path)
        .ok()
        .into_iter()
        .flatten()
        .find_map(|(key, value)| (key == "TOOL").then_some(value))
        .unwrap_or_default()
}

fn resolve_token_ledger_path(
    ledger: Option<&str>,
    overrides: &[(&str, String)],
) -> Result<Option<PathBuf>, String> {
    let mut env_map: BTreeMap<String, String> = env::vars().collect();
    for (key, value) in overrides {
        let _replaced = env_map.insert((*key).to_owned(), value.clone());
    }
    if let Some(raw) = ledger.filter(|value| !value.is_empty()) {
        return Ok(Some(validate_under_tmp(raw, &env_map)?));
    }
    if let Some(raw) = env_map
        .get("LARCH_TOKEN_LEDGER")
        .filter(|value| !value.is_empty())
        .cloned()
        && let Ok(path) = validate_under_tmp(&raw, &env_map)
    {
        return Ok(Some(path));
    }
    let slug = sha256_hex(&resolve_session_id(&env_map));
    for key in ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "RESEARCH_TMPDIR"] {
        if let Some(root) = canonical_dir(env_map.get(key).map_or("", String::as_str)) {
            return Ok(Some(root.join(default_ledger_basename(&slug))));
        }
    }
    if let Some(session_env) = env_map
        .get("SESSION_ENV_PATH")
        .filter(|value| !value.is_empty())
        .cloned()
        && let Some(root) = Path::new(&session_env)
            .parent()
            .and_then(|parent| canonical_dir(parent.to_str().unwrap_or("")))
    {
        return Ok(Some(root.join(default_ledger_basename(&slug))));
    }
    Ok(None)
}

fn validate_under_tmp(raw: &str, env_map: &BTreeMap<String, String>) -> Result<PathBuf, String> {
    let root = tmp_root(env_map).ok_or_else(|| "cannot canonicalize TMPDIR".to_owned())?;
    let mut allowed = vec![root.clone()];
    if let Some(private) = canonical_dir("/private/tmp") {
        allowed.push(private);
    }
    for key in ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "RESEARCH_TMPDIR"] {
        if let Some(workflow_root) = canonical_dir(env_map.get(key).map_or("", String::as_str)) {
            allowed.push(workflow_root);
        }
    }
    let candidate = {
        let path = PathBuf::from(raw);
        if path.is_absolute() {
            path
        } else {
            root.join(path)
        }
    };
    if let Some(parent) = candidate
        .parent()
        .filter(|value| !value.as_os_str().is_empty())
    {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    resolve_under_roots(raw, &root, &allowed)
}

fn resolve_session_id(env_map: &BTreeMap<String, String>) -> String {
    if let Some(value) = env_map
        .get("LARCH_TOKEN_SESSION_ID")
        .filter(|value| !value.is_empty())
    {
        return value.clone();
    }
    for key in ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "RESEARCH_TMPDIR"] {
        let root = env_map.get(key).map_or("", String::as_str);
        if root.is_empty() {
            continue;
        }
        let candidate = Path::new(root).join("session-id");
        if candidate.is_file() {
            return fs::read_to_string(candidate)
                .unwrap_or_default()
                .trim()
                .to_owned();
        }
    }
    let cwd = env::current_dir()
        .ok()
        .and_then(|path| path.canonicalize().ok())
        .unwrap_or_else(|| PathBuf::from("."));
    sha256_hex(&cwd.to_string_lossy())
}

fn tmp_root(env_map: &BTreeMap<String, String>) -> Option<PathBuf> {
    let raw = env_map
        .get("TMPDIR")
        .filter(|value| !value.is_empty())
        .map_or("/tmp", String::as_str);
    Path::new(raw).canonicalize().ok()
}

fn canonical_dir(path: &str) -> Option<PathBuf> {
    if path.is_empty() {
        return None;
    }
    let candidate = Path::new(path);
    if !candidate.is_dir() {
        return None;
    }
    candidate.canonicalize().ok()
}

fn validate_research_dir(path: &Path) -> Result<(), String> {
    let raw = path.to_string_lossy();
    if raw.is_empty() || contains_dotdot(&raw) {
        return Err(format!(
            "--dir must not contain '..' segments (got: {})",
            path.display()
        ));
    }
    let cache_root = env::var_os("XDG_CACHE_HOME")
        .map_or_else(
            || {
                env::var_os("HOME")
                    .map_or_else(|| PathBuf::from("/"), PathBuf::from)
                    .join(".cache")
            },
            PathBuf::from,
        )
        .join("larch")
        .join("sessions");
    let prefixes = [
        PathBuf::from("/tmp"),
        PathBuf::from("/private/tmp"),
        cache_root.clone(),
    ];
    if !prefixes.iter().any(|prefix| {
        let prefix = prefix.to_string_lossy();
        raw == prefix || raw.starts_with(&format!("{prefix}/"))
    }) {
        return Err(format!(
            "--dir must be under /tmp/, /private/tmp/, or {}/ (got: {})",
            cache_root.display(),
            path.display()
        ));
    }
    let mut probe = path.to_path_buf();
    while !probe.exists() {
        let Some(parent) = probe.parent().map(Path::to_path_buf) else {
            break;
        };
        if parent == probe {
            break;
        }
        probe = parent;
    }
    if !probe.exists() || probe.is_file() {
        return Err(format!(
            "--dir nearest existing ancestor is not a directory: {}",
            probe.display()
        ));
    }
    let resolved = probe
        .canonicalize()
        .map_err(|_error| format!("--dir resolves outside allowed roots: {}", path.display()))?;
    let allowed = prefixes
        .into_iter()
        .filter_map(|prefix| {
            prefix
                .exists()
                .then(|| prefix.canonicalize().ok())
                .flatten()
        })
        .collect::<Vec<_>>();
    if !allowed
        .iter()
        .any(|root| &resolved == root || resolved.starts_with(root))
    {
        return Err(format!(
            "--dir resolves outside allowed roots: {}",
            resolved.display()
        ));
    }
    Ok(())
}

#[derive(Debug)]
enum AppendError {
    Invalid(String),
    Io(String),
}

fn append_jsonl(path: &Path, line: &str) -> Result<(), AppendError> {
    ensure_regular_file(path)?;
    append_locked_line(path, line, "token").map_err(AppendError::Io)?;
    restore_owner_only_permissions(path);
    Ok(())
}

fn append_plain(path: &Path, line: &str) -> Result<(), std::io::Error> {
    fs::OpenOptions::new()
        .append(true)
        .create(true)
        .open(path)
        .and_then(|mut handle| handle.write_all(line.as_bytes()))
}

fn ensure_regular_file(path: &Path) -> Result<(), AppendError> {
    if let Some(parent) = path.parent().filter(|value| !value.as_os_str().is_empty()) {
        fs::create_dir_all(parent).map_err(|error| AppendError::Io(error.to_string()))?;
    }
    if fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(AppendError::Invalid(format!(
            "ledger is a symlink: {}",
            path.display()
        )));
    }
    if path.exists() && !path.is_file() {
        return Err(AppendError::Invalid(format!(
            "ledger exists but is not a regular file: {}",
            path.display()
        )));
    }
    if !path.exists() {
        #[cfg(unix)]
        {
            fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .mode(0o600)
                .open(path)
                .map_err(|error| AppendError::Io(error.to_string()))?;
        }
        #[cfg(not(unix))]
        {
            fs::File::create(path).map_err(|error| AppendError::Io(error.to_string()))?;
        }
    }
    Ok(())
}

fn timestamp_utc() -> String {
    DateTime::<Utc>::from(SystemTime::now())
        .format("%Y-%m-%dT%H:%M:%SZ")
        .to_string()
}

fn split_ledger(arguments: &[OsString]) -> Result<(Vec<String>, Option<String>), String> {
    let mut rest = Vec::new();
    let mut ledger = None;
    let mut index = 0;
    let values: Vec<String> = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect();
    while index < values.len() {
        if values[index] == "--ledger" {
            if index + 1 >= values.len() {
                return Err("--ledger requires a value".to_owned());
            }
            ledger = Some(values[index + 1].clone());
            index += 2;
        } else {
            rest.push(values[index].clone());
            index += 1;
        }
    }
    Ok((rest, ledger))
}

fn flag_map(values: &[String]) -> BTreeMap<String, String> {
    let mut options = BTreeMap::new();
    let mut index = 0;
    while index < values.len() {
        let flag = values[index].clone();
        if !flag.starts_with("--") {
            index += 1;
            continue;
        }
        if index + 1 < values.len() && !values[index + 1].starts_with("--") {
            options.insert(flag, values[index + 1].clone());
            index += 2;
        } else {
            options.insert(flag, String::new());
            index += 1;
        }
    }
    options
}

#[cfg(test)]
mod tests {
    use super::fetch_pr_line_counts;
    use crate::github_service::with_test_github_service;
    use larch_adapters::github::OctocrabGitHubService;
    use larch_test_support::{IssueServiceExchange, IssueServiceStub};
    use serde_json::json;
    use std::sync::Arc;

    #[test]
    fn pr_line_fetch_aggregates_the_typed_service_response() {
        let response = json!([
            {"filename": "src/lib.rs", "additions": 10, "deletions": 2},
            {
                "filename": "larch-logs/implement/run-x/summary.md",
                "additions": 5,
                "deletions": 1,
            },
        ]);
        let server =
            IssueServiceStub::start([
                IssueServiceExchange::any_json(200, response.to_string()).expect("response")
            ])
            .expect("stub service");
        let base = server.base_url().to_owned();
        let service = Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        let counts = with_test_github_service(service, || fetch_pr_line_counts(42, "o/r"))
            .expect("line counts");
        assert_eq!(counts.code_added, 10);
        assert_eq!(counts.code_deleted, 2);
        assert_eq!(counts.logs_added, 5);
        assert_eq!(counts.logs_deleted, 1);
        let requests = server.finish().expect("stub requests");
        assert_eq!(requests.len(), 1);
        assert!(requests[0].path.starts_with("/repos/o/r/pulls/42/files?"));
    }
}
