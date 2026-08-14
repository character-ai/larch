//! `timing` ledger, report, harness, and telemetry verbs.
//!
//! The ledger is a shared append-only TSV that several processes write at the
//! same time, so every append takes an exclusive `flock` and every writer
//! degrades to a warning rather than failing the workflow it is measuring.
//! Wall-clock values arrive through one injected [`BusinessClock`], so tests
//! pin time instead of sleeping.

use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    time::UNIX_EPOCH,
};

use larch_adapters::{
    clock::SystemClock,
    progress_state::{self, ProgressPaths},
    resolve_allow_missing,
};
use larch_core::{
    BlockMarkers, BusinessClock, python_json_dumps, replace_markdown_block,
    report::timing::{
        self, DEFAULT_OUTLIER_THRESHOLD_S, LedgerRows, REPORT_UNAVAILABLE,
        TIMING_TASK_KINDS_ALLOWED,
    },
    validate_progress_run_id,
};

use crate::ledger_append::{append_locked_line, restore_owner_only_permissions};
/// Basename of a tmpdir-resolved ledger.
const LEDGER_BASENAME: &str = "timing-ledger.tsv";
/// Markdown block markers the appended timing section uses.
const BLOCK_BEGIN: &str = "timing-report-begin";
/// Closing marker of the appended timing section.
const BLOCK_END: &str = "timing-report-end";

/// A read-only environment snapshot with command-scoped overrides applied.
struct Environment(BTreeMap<String, String>);

impl Environment {
    fn ambient() -> Self {
        Self(
            env::vars_os()
                .filter_map(|(key, value)| {
                    Some((key.into_string().ok()?, value.into_string().ok()?))
                })
                .collect(),
        )
    }

    fn get(&self, key: &str) -> &str {
        self.0.get(key).map_or("", String::as_str)
    }

    fn os(&self, key: &str) -> Option<OsString> {
        self.0.get(key).map(OsString::from)
    }

    fn set(&mut self, key: &str, value: &str) {
        let _replaced = self.0.insert(key.to_owned(), value.to_owned());
    }

    fn skill(&self) -> String {
        let value = self.get("LARCH_TIMING_SKILL");
        if value.is_empty() {
            "implement".to_owned()
        } else {
            value.to_owned()
        }
    }
}

/// Record one step mark in the resolved ledger.
pub fn mark(arguments: &[OsString]) -> ExitCode {
    let (rest, ledger) = split_ledger(arguments);
    let mut positional: Vec<String> = Vec::new();
    let mut if_latest_differs = false;
    for value in rest {
        if value == "--if-latest-differs" {
            if_latest_differs = true;
        } else {
            positional.push(value);
        }
    }
    let Some(label) = positional.first() else {
        eprintln!("timing mark requires <step>");
        return ExitCode::from(1);
    };
    let environment = Environment::ambient();
    let skill = environment.skill();
    let path = match resolve_ledger_path(ledger.as_deref(), &environment) {
        Ok(Some(path)) => path,
        Ok(None) => return ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("timing mark: {message}");
            return ExitCode::from(1);
        }
    };
    if if_latest_differs {
        let rows = read_rows(&path);
        if rows
            .marks
            .iter()
            .rev()
            .find(|entry| entry.skill == skill)
            .is_some_and(|entry| entry.step == *label)
        {
            return ExitCode::SUCCESS;
        }
    }
    let row = timing::mark_row(epoch_now(), &skill, label);
    match append_row(&path, &row) {
        Ok(()) => {}
        Err(message) => {
            eprintln!("timing mark: WARNING: ledger write skipped: {message}");
            return ExitCode::SUCCESS;
        }
    }
    append_progress_mark(&environment, &skill, label);
    ExitCode::SUCCESS
}

/// Record one vendor task in the resolved ledger.
pub fn record_vendor_task(arguments: &[OsString]) -> ExitCode {
    record_vendor_task_with_environment(arguments, &[])
}

/// Record one vendor task, resolving the ledger with caller-supplied overrides.
///
/// A launcher learns its session identity from files rather than from its own
/// environment, which this process must not mutate. Passing those rows here
/// reaches the resolver the same way the retired child process did.
pub fn record_vendor_task_with_environment(
    arguments: &[OsString],
    overrides: &[(&str, OsString)],
) -> ExitCode {
    let (rest, ledger) = split_ledger(arguments);
    let options = flag_map(&rest);
    let label = "timing record-vendor-task";
    let (Some(vendor), Some(task_kind), Some(start_raw), Some(end_raw), Some(output)) = (
        options.get("--vendor"),
        options.get("--task-kind"),
        options.get("--start-s"),
        options.get("--end-s"),
        options.get("--output"),
    ) else {
        eprintln!("{label}: {}", missing_flag(&options));
        return ExitCode::from(1);
    };
    let (Some(start), Some(end)) = (parse_seconds(start_raw), parse_seconds(end_raw)) else {
        eprintln!("{label}: --start-s and --end-s must be numbers");
        return ExitCode::from(1);
    };
    let Some(exit_code) = parse_integer(options.get("--exit-code").map_or("0", String::as_str))
    else {
        eprintln!("{label}: --exit-code must be an integer");
        return ExitCode::from(1);
    };
    let mut environment = Environment::ambient();
    for (key, value) in overrides {
        environment.set(key, &value.to_string_lossy());
    }
    let path = match resolve_ledger_path(ledger.as_deref(), &environment) {
        Ok(Some(path)) => path,
        Ok(None) => return ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("{label}: {message}");
            return ExitCode::from(1);
        }
    };
    if !timing::is_known_vendor(vendor) {
        eprintln!("{label}: vendor must be codex, cursor, or claude");
        return ExitCode::from(1);
    }
    if !timing::is_wellformed_task_kind(task_kind) {
        eprintln!("{label}: malformed task-kind: {task_kind}");
        return ExitCode::from(1);
    }
    if !timing::is_known_task_kind(task_kind) {
        eprintln!("timing: WARNING: unknown task-kind: {task_kind}");
    }
    let requested_status = options
        .get("--status")
        .filter(|value| !value.is_empty())
        .map_or("complete", String::as_str);
    let Some(mut status) = timing::normalize_status(requested_status) else {
        eprintln!("{label}: --status must be complete, signal, unknown, OK, ERROR, or TIMEOUT");
        return ExitCode::from(1);
    };
    if end < start {
        status = "unknown";
        eprintln!("timing: WARNING: end_s precedes start_s; clamping duration_s to 0");
    }
    let row = timing::vendor_row(
        epoch_now(),
        &environment.skill(),
        vendor,
        task_kind,
        start,
        end,
        (end - start).max(0),
        base_name(output),
        exit_code,
        status,
    );
    if let Err(message) = append_row(&path, &row) {
        eprintln!("{label}: WARNING: ledger write skipped: {message}");
    }
    ExitCode::SUCCESS
}

/// Record one vendor task's wall-clock through the Rust timing writer.
pub fn record_vendor_timing(
    vendor: &str,
    task_kind: &str,
    start_s: impl std::fmt::Display,
    end_s: impl std::fmt::Display,
    output: &Path,
    exit_code: i32,
    status: &str,
) -> ExitCode {
    record_vendor_task(&vendor_timing_arguments(
        vendor, task_kind, start_s, end_s, output, exit_code, status,
    ))
}

/// Build the flag list both vendor-timing entry points record.
pub fn vendor_timing_arguments(
    vendor: &str,
    task_kind: &str,
    start_s: impl std::fmt::Display,
    end_s: impl std::fmt::Display,
    output: &Path,
    exit_code: i32,
    status: &str,
) -> Vec<OsString> {
    vec![
        OsString::from("--vendor"),
        OsString::from(vendor),
        OsString::from("--task-kind"),
        OsString::from(task_kind),
        OsString::from("--start-s"),
        OsString::from(start_s.to_string()),
        OsString::from("--end-s"),
        OsString::from(end_s.to_string()),
        OsString::from("--output"),
        output.as_os_str().to_os_string(),
        OsString::from("--exit-code"),
        OsString::from(exit_code.to_string()),
        OsString::from("--status"),
        OsString::from(status),
    ]
}

/// Record one review round in the resolved ledger.
pub fn record_round(arguments: &[OsString]) -> ExitCode {
    let (rest, ledger) = split_ledger(arguments);
    let options = flag_map(&rest);
    let label = "timing record-round";
    let (Some(skill), Some(step)) = (options.get("--skill"), options.get("--step")) else {
        eprintln!("{label}: {}", missing_flag(&options));
        return ExitCode::from(1);
    };
    let mut numbers = Vec::new();
    for flag in [
        "--round",
        "--start-s",
        "--end-s",
        "--accepted",
        "--rejected",
    ] {
        let Some(raw) = options.get(flag) else {
            eprintln!("{label}: '{flag}'");
            return ExitCode::from(1);
        };
        let parsed = if matches!(flag, "--start-s" | "--end-s") {
            parse_seconds(raw)
        } else {
            parse_integer(raw)
        };
        let Some(value) = parsed else {
            eprintln!("{label}: {flag} must be a number");
            return ExitCode::from(1);
        };
        numbers.push(value);
    }
    let oos = if let Some(raw) = options.get("--oos").filter(|value| !value.is_empty()) {
        let Some(value) = parse_integer(raw) else {
            eprintln!("{label}: --oos must be an integer");
            return ExitCode::from(1);
        };
        Some(value)
    } else {
        None
    };
    let environment = Environment::ambient();
    let path = match resolve_ledger_path(ledger.as_deref(), &environment) {
        Ok(Some(path)) => path,
        Ok(None) => return ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("{label}: {message}");
            return ExitCode::from(1);
        }
    };
    if skill != "implement" && skill != "design" {
        eprintln!("{label}: --skill must be implement or design");
        return ExitCode::from(1);
    }
    let (round, start, end, accepted, rejected) =
        (numbers[0], numbers[1], numbers[2], numbers[3], numbers[4]);
    let ledger_text = read_text(&path);
    if options.contains_key("--if-round-exists")
        && round_exists_for_compatibility(&ledger_text, skill, round)
    {
        return ExitCode::SUCCESS;
    }
    // A stall recovery reruns the same round number in one ledger (issue #5504).
    // Retries run strictly after the prior attempt returns, so counting prior
    // rows for this (skill, round) is race-free.
    let attempt = timing::next_round_attempt(&ledger_text, skill, round);
    let row = timing::round_row(
        epoch_now(),
        skill,
        step,
        round,
        start,
        end,
        (end - start).max(0),
        accepted,
        rejected,
        oos,
        attempt,
    );
    if let Err(message) = append_row(&path, &row) {
        eprintln!("{label}: WARNING: ledger write skipped: {message}");
    }
    ExitCode::SUCCESS
}

/// Print the resolved ledger path and its raw contents.
pub fn dump(arguments: &[OsString]) -> ExitCode {
    let (_rest, ledger) = split_ledger(arguments);
    let environment = Environment::ambient();
    let path = match resolve_ledger_path(ledger.as_deref(), &environment) {
        Ok(Some(path)) => path,
        Ok(None) => return ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("timing dump: {message}");
            return ExitCode::from(1);
        }
    };
    println!("{}", path.display());
    let text = read_text(&path);
    if !text.is_empty() {
        print!("{text}");
    }
    ExitCode::SUCCESS
}

/// Render the timing report for the resolved ledger.
pub fn report(arguments: &[OsString]) -> ExitCode {
    match render_report(arguments) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("Timing report unavailable: {message}");
            ExitCode::SUCCESS
        }
    }
}

/// Print the canonical `--timing-task-kind` allow-list.
pub fn task_kinds(_arguments: &[OsString]) -> ExitCode {
    let mut out = String::new();
    for kind in TIMING_TASK_KINDS_ALLOWED {
        out.push_str(kind);
        out.push('\n');
    }
    print!("{out}");
    ExitCode::SUCCESS
}

/// Run one command and publish its wall-clock duration on stdout.
pub fn harness_mark(arguments: &[OsString]) -> ExitCode {
    larch_harness_mark::harness_mark(arguments)
}

/// Mark one `/implement` step in both the token and timing ledgers.
pub fn telemetry_mark(arguments: &[OsString]) -> ExitCode {
    let values: Vec<String> = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect();
    let options = flag_map(&values);
    let Some(raw) = options
        .get("--implement-tmpdir")
        .filter(|value| !value.is_empty())
    else {
        return ExitCode::SUCCESS;
    };
    let tmpdir = PathBuf::from(raw);
    let label = options.get("--label").map_or("", String::as_str);
    if !tmpdir.is_absolute() || !tmpdir.is_dir() || label.is_empty() {
        return ExitCode::SUCCESS;
    }
    let mut environment = Environment::ambient();
    environment.set("IMPLEMENT_TMPDIR", raw);
    let session = tmpdir.join("session-env.sh");
    let session_text = read_text(&session);
    let mut overrides = vec![("IMPLEMENT_TMPDIR".to_owned(), raw.to_owned())];
    for key in [
        "LARCH_TOKEN_SESSION_ID",
        "LARCH_CLAUDE_SOURCE_FILE",
        "LARCH_TIMING_LEDGER",
        "LARCH_TOKEN_LEDGER",
    ] {
        let value = session_value(&session_text, key);
        if !value.is_empty() {
            environment.set(key, &value);
            overrides.push((key.to_owned(), value));
        }
    }
    let override_refs: Vec<(&str, String)> = overrides
        .iter()
        .map(|(key, value)| (key.as_str(), value.clone()))
        .collect();
    let mark_args = if let Some((_, ledger)) = overrides
        .iter()
        .find(|(key, _)| key == "LARCH_TOKEN_LEDGER")
    {
        vec![
            OsString::from("--ledger"),
            OsString::from(ledger),
            OsString::from(label),
        ]
    } else {
        vec![OsString::from(label)]
    };
    let _ignored = crate::token_commands::mark_with_env(&mark_args, &override_refs);
    environment.set("DESIGN_TMPDIR", "");
    environment.set("LARCH_TIMING_SKILL", "implement");
    match resolve_ledger_path(None, &environment) {
        Ok(Some(path)) => {
            if let Err(message) =
                append_row(&path, &timing::mark_row(epoch_now(), "implement", label))
            {
                eprintln!("timing telemetry-mark: timing mark skipped: {message}");
            }
        }
        Ok(None) => {}
        Err(message) => eprintln!("timing telemetry-mark: timing mark skipped: {message}"),
    }
    ExitCode::SUCCESS
}

/// Render the timing report for callers that already own their argument list.
///
/// # Errors
/// Returns the operator diagnostic the `timing report` verb would print when
/// the flags, the ledger, or the write target cannot be used.
pub fn render_report_arguments(arguments: &[OsString]) -> Result<(), String> {
    render_report(arguments)
}

/// One parsed `timing report` invocation.
#[derive(Default)]
struct ReportRequest {
    mode: &'static str,
    format: &'static str,
    output: Option<PathBuf>,
    append: Option<PathBuf>,
    ledger: Option<String>,
    implement_tmpdir: String,
    outlier_threshold: String,
    test_now: String,
}

fn parse_report_arguments(values: &[String]) -> Result<ReportRequest, String> {
    let mut request = ReportRequest {
        format: "markdown",
        ..ReportRequest::default()
    };
    let mut index = 0;
    while index < values.len() {
        let flag = values[index].as_str();
        let value = || -> Result<String, String> {
            values
                .get(index + 1)
                .cloned()
                .ok_or_else(|| format!("{flag} requires a value"))
        };
        match flag {
            "--since-last-mark" | "--terse" => {
                request.mode = "terse";
                index += 1;
            }
            "--summary" => {
                request.mode = "summary";
                index += 1;
            }
            "--full" => {
                request.mode = "full";
                index += 1;
            }
            "--markdown" => {
                request.format = "markdown";
                index += 1;
            }
            "--format" => {
                request.format = match value()?.as_str() {
                    "json" => "json",
                    "markdown" => "markdown",
                    other => return Err(format!("unknown format: {other}")),
                };
                index += 2;
            }
            "--output" => {
                request.output = Some(PathBuf::from(value()?));
                index += 2;
            }
            "--ledger" => {
                request.ledger = Some(value()?);
                index += 2;
            }
            "--implement-tmpdir" => {
                request.implement_tmpdir = value()?;
                index += 2;
            }
            "--outlier-threshold" => {
                request.outlier_threshold = value()?;
                index += 2;
            }
            "--test-now" => {
                request.test_now = value()?;
                index += 2;
            }
            "--append-timing-section" => {
                request.append = Some(PathBuf::from(value()?));
                request.mode = "full";
                index += 2;
            }
            other => return Err(format!("unknown flag: {other}")),
        }
    }
    if request.mode.is_empty() {
        return Err("missing report mode".to_owned());
    }
    Ok(request)
}

fn report_environment(request: &ReportRequest) -> Environment {
    let mut environment = Environment::ambient();
    if !request.implement_tmpdir.is_empty() {
        environment.set("IMPLEMENT_TMPDIR", &request.implement_tmpdir);
        environment.set("LARCH_TIMING_SKILL", "implement");
        environment.set("DESIGN_TMPDIR", "");
    }
    if !request.outlier_threshold.is_empty() {
        environment.set(
            "LARCH_TIMING_OUTLIER_THRESHOLD_S",
            &request.outlier_threshold,
        );
    }
    if !request.test_now.is_empty() {
        environment.set("LARCH_TEST_TIMING_NOW", &request.test_now);
    }
    environment
}

fn render_report(arguments: &[OsString]) -> Result<(), String> {
    let values: Vec<String> = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect();
    let request = parse_report_arguments(&values)?;
    let environment = report_environment(&request);
    let path = resolve_ledger_path(request.ledger.as_deref(), &environment)?
        .ok_or_else(|| "ledger path unavailable".to_owned())?;
    let rows = read_rows(&path);
    let now = environment
        .get("LARCH_TEST_TIMING_NOW")
        .parse::<i64>()
        .unwrap_or_else(|_error| epoch_now());
    let rendered = match request.mode {
        "summary" => timing::summary_line(&rows, now),
        "terse" => timing::terse_line(&rows, &environment.skill(), now),
        _ if rows.marks.is_empty() => REPORT_UNAVAILABLE.to_owned(),
        _ => {
            let threshold = positive_or(
                environment.get("LARCH_TIMING_OUTLIER_THRESHOLD_S"),
                DEFAULT_OUTLIER_THRESHOLD_S,
            );
            let data = timing::build_report(&rows, now, threshold);
            if request.format == "json" {
                python_json_dumps(&timing::report_json(&data)).map_err(|error| error.to_string())?
            } else {
                timing::report_markdown(&data)
            }
        }
    };
    if let Some(target) = request.append.as_deref() {
        let block = format!(
            "<!-- {BLOCK_BEGIN} -->\n## Timing Report\n\n{rendered}\n<!-- {BLOCK_END} -->\n"
        );
        write_timing_section(target, &block)?;
    }
    let text = format!("{rendered}\n");
    if request.mode == "full"
        && let Some(target) = request.output.as_deref()
    {
        atomic_write(target, &text)?;
    } else if request.append.is_none() {
        print!("{text}");
    }
    Ok(())
}

fn write_timing_section(target: &Path, block: &str) -> Result<(), String> {
    let markers =
        BlockMarkers::new(BLOCK_BEGIN, BLOCK_END).map_err(|error| format!("{error:?}"))?;
    replace_markdown_block(target, block, &markers, "timing report")
        .map_err(|error| error.to_string())
}

fn atomic_write(target: &Path, text: &str) -> Result<(), String> {
    let parent = target
        .parent()
        .filter(|value| !value.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    let mut temporary = tempfile::Builder::new()
        .prefix(".timing-report-")
        .tempfile_in(parent)
        .map_err(|error| error.to_string())?;
    temporary
        .write_all(text.as_bytes())
        .map_err(|error| error.to_string())?;
    if fs::symlink_metadata(target).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(format!(
            "refusing to follow a symlink: {}",
            target.display()
        ));
    }
    temporary
        .persist(target)
        .map_err(|error| error.to_string())
        .map(|_file| ())
}

fn append_progress_mark(environment: &Environment, skill: &str, label: &str) {
    let tmpdir = {
        let implement = environment.get("IMPLEMENT_TMPDIR");
        if implement.is_empty() {
            environment.get("DESIGN_TMPDIR")
        } else {
            implement
        }
    };
    let Some(run_id) = owned_run_id(environment, tmpdir) else {
        return;
    };
    let Ok(repository) = env::current_dir() else {
        return;
    };
    let cache_home = progress_state::progress_cache_home(
        environment.os("LARCH_TEST_CACHE_HOME").as_deref(),
        environment.os("XDG_CACHE_HOME").as_deref(),
        environment.os("HOME").as_deref(),
    );
    let paths: ProgressPaths = progress_state::progress_paths(&cache_home, &repository);
    let step = timing::progress_step_from_label(label);
    let _written = progress_state::append_breadcrumb_for_run(
        &paths,
        &run_id,
        skill,
        &step,
        &format!("{label} started"),
    );
}

fn owned_run_id(environment: &Environment, tmpdir: &str) -> Option<String> {
    let mut candidates = vec![environment.get("LARCH_RUN_ID").to_owned()];
    if !tmpdir.is_empty() {
        let root = Path::new(tmpdir);
        for name in ["session-env.sh", "source-env.sh"] {
            let text = read_text(&root.join(name));
            for line in text.lines() {
                for prefix in ["LARCH_RUN_ID=", "export LARCH_RUN_ID="] {
                    if let Some(value) = line.strip_prefix(prefix) {
                        candidates.push(value.trim().trim_matches(['"', '\'']).to_owned());
                    }
                }
            }
        }
    }
    candidates
        .into_iter()
        .find(|candidate| validate_progress_run_id(candidate).is_some())
}

fn session_value(text: &str, key: &str) -> String {
    let plain = [key, "="].concat();
    let exported = ["export ", key, "="].concat();
    for line in text.lines() {
        let trimmed = line.trim_start();
        if let Some(value) = trimmed
            .strip_prefix(plain.as_str())
            .or_else(|| trimmed.strip_prefix(exported.as_str()))
        {
            return value.trim().trim_matches(['"', '\'']).to_owned();
        }
    }
    String::new()
}

fn read_text(path: &Path) -> String {
    fs::read(path).map_or_else(
        |_error| String::new(),
        |bytes| String::from_utf8_lossy(&bytes).into_owned(),
    )
}

/// Match the retired design helper's idempotency scan, including legacy short rows.
fn round_exists_for_compatibility(text: &str, skill: &str, round: i64) -> bool {
    let skill = timing::sanitize(skill);
    let round = round.to_string();
    text.lines().any(|line| {
        let columns: Vec<&str> = line.split('\t').collect();
        columns.len() >= 8
            && columns[0] == "v1"
            && columns[1] == "round"
            && columns[3] == skill
            && columns[5] == round
    })
}

fn read_rows(path: &Path) -> LedgerRows {
    let rows = timing::parse_ledger(&read_text(path));
    for warning in &rows.warnings {
        eprintln!("{warning}");
    }
    rows
}

fn epoch_now() -> i64 {
    let now = BusinessClock::now(&SystemClock);
    now.duration_since(UNIX_EPOCH).map_or(0, |elapsed| {
        i64::try_from(elapsed.as_secs()).unwrap_or(i64::MAX)
    })
}

fn positive_or(raw: &str, fallback: i64) -> i64 {
    raw.parse::<i64>()
        .ok()
        .filter(|value| *value > 0)
        .unwrap_or(fallback)
}

/// Truncate a decimal second count toward zero, matching Python's `int(float)`.
fn parse_seconds(raw: &str) -> Option<i64> {
    let value: f64 = raw.trim().parse().ok()?;
    if !value.is_finite() {
        return None;
    }
    #[expect(
        clippy::cast_possible_truncation,
        reason = "ledger seconds stay far below the i64 bound"
    )]
    Some(value.trunc() as i64)
}

fn parse_integer(raw: &str) -> Option<i64> {
    raw.trim().parse::<i64>().ok()
}

fn base_name(value: &str) -> &str {
    Path::new(value)
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or(value)
}

fn missing_flag(options: &BTreeMap<String, String>) -> String {
    for flag in [
        "--vendor",
        "--task-kind",
        "--start-s",
        "--end-s",
        "--output",
        "--skill",
        "--step",
    ] {
        if !options.contains_key(flag) {
            return format!("'{flag}'");
        }
    }
    "'--vendor'".to_owned()
}

/// Split `--ledger VALUE` out of an argument list, keeping the remaining order.
fn split_ledger(arguments: &[OsString]) -> (Vec<String>, Option<String>) {
    let values: Vec<String> = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect();
    let mut rest = Vec::new();
    let mut ledger = None;
    let mut index = 0;
    while index < values.len() {
        if values[index] == "--ledger" {
            ledger = Some(values.get(index + 1).cloned().unwrap_or_default());
            index += 2;
        } else {
            rest.push(values[index].clone());
            index += 1;
        }
    }
    (rest, ledger)
}

/// Collect `--flag value` pairs the way the retired Python parser did.
fn flag_map(values: &[String]) -> BTreeMap<String, String> {
    let mut options = BTreeMap::new();
    let mut index = 0;
    while index < values.len() {
        if !values[index].starts_with("--") {
            index += 1;
            continue;
        }
        let has_value = values
            .get(index + 1)
            .is_some_and(|next| !next.starts_with("--"));
        if has_value {
            let _replaced = options.insert(values[index].clone(), values[index + 1].clone());
            index += 2;
        } else {
            let _replaced = options.insert(values[index].clone(), String::new());
            index += 1;
        }
    }
    options
}

/// Resolve the ledger a verb writes, or `None` when no session names one.
fn resolve_ledger_path(
    ledger: Option<&str>,
    environment: &Environment,
) -> Result<Option<PathBuf>, String> {
    if let Some(raw) = ledger.filter(|value| !value.is_empty()) {
        return validate_ledger_path(raw, environment).map(Some);
    }
    let declared = environment.get("LARCH_TIMING_LEDGER");
    if !declared.is_empty()
        && let Ok(path) = validate_ledger_path(declared, environment)
    {
        return Ok(Some(path));
    }
    for key in [
        "IMPLEMENT_TMPDIR",
        "SESSION_ENV_PATH",
        "DESIGN_TMPDIR",
        "REVIEW_TMPDIR",
    ] {
        let raw = environment.get(key);
        if raw.is_empty() {
            continue;
        }
        let candidate = if key == "SESSION_ENV_PATH" {
            Path::new(raw)
                .parent()
                .unwrap_or_else(|| Path::new(""))
                .to_path_buf()
        } else {
            PathBuf::from(raw)
        };
        if candidate.is_dir()
            && let Ok(resolved) = fs::canonicalize(&candidate)
        {
            return Ok(Some(resolved.join(LEDGER_BASENAME)));
        }
    }
    Ok(None)
}

/// Confine a caller-supplied ledger path to one of the session temporary roots.
fn validate_ledger_path(raw: &str, environment: &Environment) -> Result<PathBuf, String> {
    if raw.is_empty()
        || Path::new(raw)
            .components()
            .any(|part| part.as_os_str() == "..")
    {
        return Err(format!(
            "ledger path must not be empty or contain '..': {raw}"
        ));
    }
    let roots = allowed_roots(environment);
    let default_root = roots.first().cloned().unwrap_or_else(|| {
        resolve_allow_missing("/tmp").unwrap_or_else(|_error| PathBuf::from("/tmp"))
    });
    let candidate = if Path::new(raw).is_absolute() {
        PathBuf::from(raw)
    } else {
        default_root.join(raw)
    };
    if !under_allowed_root(&candidate, &roots) {
        return Err(format!("ledger path not under an allowed root: {raw}"));
    }
    let parent = candidate
        .parent()
        .unwrap_or_else(|| Path::new("/"))
        .to_path_buf();
    fs::create_dir_all(&parent).map_err(|error| error.to_string())?;
    let parent = fs::canonicalize(&parent).map_err(|error| error.to_string())?;
    let resolved = parent.join(candidate.file_name().unwrap_or_default());
    if !under_allowed_root(&resolved, &roots) {
        return Err(format!("ledger path not under an allowed root: {raw}"));
    }
    match fs::symlink_metadata(&resolved) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            Err(format!("ledger is a symlink: {}", resolved.display()))
        }
        Ok(metadata) if !metadata.is_file() => Err(format!(
            "ledger exists but is not a regular file: {}",
            resolved.display()
        )),
        _ => Ok(resolved),
    }
}

fn allowed_roots(environment: &Environment) -> Vec<PathBuf> {
    let mut roots: Vec<PathBuf> = Vec::new();
    let tmpdir = environment.get("TMPDIR");
    let primary = if tmpdir.is_empty() { "/tmp" } else { tmpdir };
    let mut candidates: Vec<PathBuf> = vec![PathBuf::from(primary), PathBuf::from("/private/tmp")];
    for key in ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "REVIEW_TMPDIR"] {
        let raw = environment.get(key);
        if !raw.is_empty() {
            candidates.push(PathBuf::from(raw));
        }
    }
    let session = environment.get("SESSION_ENV_PATH");
    if !session.is_empty()
        && let Some(parent) = Path::new(session).parent()
    {
        candidates.push(parent.to_path_buf());
    }
    for candidate in candidates {
        if !candidate.is_dir() {
            continue;
        }
        if let Ok(resolved) = fs::canonicalize(&candidate)
            && !roots.contains(&resolved)
        {
            roots.push(resolved);
        }
    }
    roots
}

fn under_allowed_root(path: &Path, roots: &[PathBuf]) -> bool {
    let Ok(resolved) = resolve_allow_missing(path) else {
        return false;
    };
    roots
        .iter()
        .any(|root| resolved == *root || resolved.starts_with(root.as_path()))
}

/// Append one row under an exclusive lock, then restore owner-only permissions.
fn append_row(path: &Path, row: &str) -> Result<(), String> {
    ensure_ledger(path)?;
    let line = format!("{row}\n");
    append_locked_line(path, &line, "timing")?;
    restore_owner_only_permissions(path);
    Ok(())
}

fn ensure_ledger(path: &Path) -> Result<(), String> {
    if fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(format!(
            "ledger is a symlink, refusing to write: {}",
            path.display()
        ));
    }
    if let Some(parent) = path.parent().filter(|value| !value.as_os_str().is_empty()) {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    if let Ok(metadata) = fs::metadata(path)
        && !metadata.is_file()
    {
        return Err(format!(
            "ledger exists but is not a regular file: {}",
            path.display()
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{base_name, flag_map, parse_seconds, session_value, split_ledger};
    use std::ffi::OsString;

    #[test]
    fn ledger_flag_is_removed_from_any_position() {
        let arguments: Vec<OsString> = ["a", "--ledger", "/tmp/x.tsv", "--if-latest-differs"]
            .iter()
            .map(OsString::from)
            .collect();
        let (rest, ledger) = split_ledger(&arguments);
        assert_eq!(rest, vec!["a".to_owned(), "--if-latest-differs".to_owned()]);
        assert_eq!(ledger.as_deref(), Some("/tmp/x.tsv"));
    }

    #[test]
    fn flag_map_treats_a_following_flag_as_an_empty_value() {
        let values: Vec<String> = ["--a", "1", "--b", "--c", "2"]
            .iter()
            .map(|value| (*value).to_owned())
            .collect();
        let options = flag_map(&values);
        assert_eq!(options.get("--a").map(String::as_str), Some("1"));
        assert_eq!(options.get("--b").map(String::as_str), Some(""));
        assert_eq!(options.get("--c").map(String::as_str), Some("2"));
    }

    #[test]
    fn seconds_truncate_toward_zero_like_python_int() {
        assert_eq!(parse_seconds("12.9"), Some(12));
        assert_eq!(parse_seconds("-12.9"), Some(-12));
        assert_eq!(parse_seconds("nope"), None);
    }

    #[test]
    fn session_values_drop_export_quoting_and_whitespace() {
        let text = "LARCH_TIMING_LEDGER=\"/tmp/a.tsv\"\nOTHER=1\n";
        assert_eq!(session_value(text, "LARCH_TIMING_LEDGER"), "/tmp/a.tsv");
        assert_eq!(session_value(text, "MISSING"), "");
        assert_eq!(base_name("/tmp/dir/out.txt"), "out.txt");
    }
}
