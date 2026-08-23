//! `final-report write` and `final-report step18b`.
//!
//! The terminal `/implement` report: derived tally, cost, timing, and issue
//! fields, the review-phase and issue-detail prefixes, the architectural
//! knowledge sections, `summary-final.md`, the committed run-log copy, the
//! manifest reconcile, and the tracking-issue upsert.
//!
//! PR line counts and architectural assessment sections are rendered in
//! process. Remaining compatibility delegation stays behind the
//! [`crate::python_verb`] seam.

use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_adapters::{
    phase_detail::{self, PhaseSkill, RenderRequest},
    run_log_manifest::{ManifestStore, utc_now},
    stall_recovery,
};
use larch_core::{
    ChildEnvironment, RunLogLayout, RunLogSlug, claude_model_from_transcript, emit_kv,
    read_kv_from_text, redact,
    report::{
        self, RunSummaryCost, RunSummaryFields, RunSummaryIdentity, TokenCounts, TokenObservations,
        build_report_from_ledgers, display_rates, price_counts, render_cost_kv,
        run_log_ledger_path,
    },
};
use serde_json::{Map, Value};

use crate::{
    argparse_compat::{parse_with_flags, write_stdout},
    python_verb::{publish_session_environment, run_python_verb},
    run_log_entry_commands::{
        append_execution_issue, plugin_version, stage_append_batch, write_run_log_file,
    },
};

/// Timeout for one delegated Python helper verb.
const VERB_TIMEOUT: Duration = Duration::from_secs(300);
/// Lifecycle manifest schema version that can pin disabled publication.
const DISABLED_LIFECYCLE_SCHEMA_VERSION: i64 = 3;
/// Storage-resolution reasons that mean publication was disabled.
const DISABLED_STORAGE_REASONS: [&str; 3] = [
    "config-file-missing",
    "larch-table-missing",
    "storage-base-uri-omitted",
];
/// Execution-issue category the needs-user ship handoff records under.
const NEEDS_USER_CATEGORY: &str = "Tool Failures";
/// Rate-override environment names `--cost-overrides-json` may set.
const COST_OVERRIDE_ENV_NAMES: [&str; 43] = [
    "LARCH_CLAUDE_INPUT_RATE_PER_M",
    "LARCH_CLAUDE_CACHE_READ_RATE_PER_M",
    "LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M",
    "LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M",
    "LARCH_CLAUDE_OUTPUT_RATE_PER_M",
    "LARCH_CODEX_INPUT_RATE_PER_M",
    "LARCH_CODEX_CACHED_INPUT_RATE_PER_M",
    "LARCH_CODEX_OUTPUT_RATE_PER_M",
    "LARCH_CODEX_MINI_INPUT_RATE_PER_M",
    "LARCH_CODEX_MINI_CACHED_INPUT_RATE_PER_M",
    "LARCH_CODEX_MINI_OUTPUT_RATE_PER_M",
    "LARCH_CURSOR_INPUT_RATE_PER_M",
    "LARCH_CURSOR_CACHE_READ_RATE_PER_M",
    "LARCH_CURSOR_OUTPUT_RATE_PER_M",
    "LARCH_CLAUDE_RATE_PER_M",
    "LARCH_CODEX_RATE_PER_M",
    "LARCH_CURSOR_RATE_PER_M",
    "LARCH_CURSOR_GROK_INPUT_RATE_PER_M",
    "LARCH_CURSOR_GROK_CACHE_READ_RATE_PER_M",
    "LARCH_CURSOR_GROK_OUTPUT_RATE_PER_M",
    "LARCH_CURSOR_TEAMS_SURCHARGE_PER_M",
    "LARCH_TOKEN_RATE_PER_M",
    "LARCH_RATE_CLAUDE_INPUT",
    "LARCH_RATE_CLAUDE_CACHE_READ",
    "LARCH_RATE_CLAUDE_CACHE_CREATE",
    "LARCH_RATE_CLAUDE_CACHE_CREATE_5M",
    "LARCH_RATE_CLAUDE_CACHE_CREATE_1H",
    "LARCH_RATE_CLAUDE_OUTPUT",
    "LARCH_RATE_CLAUDE_AGGREGATE",
    "LARCH_RATE_CODEX_INPUT",
    "LARCH_RATE_CODEX_CACHE_READ",
    "LARCH_RATE_CODEX_CACHED_INPUT",
    "LARCH_RATE_CODEX_OUTPUT",
    "LARCH_RATE_CODEX_AGGREGATE",
    "LARCH_RATE_CODEX_MINI_INPUT",
    "LARCH_RATE_CODEX_MINI_CACHE_READ",
    "LARCH_RATE_CODEX_MINI_CACHED_INPUT",
    "LARCH_RATE_CODEX_MINI_OUTPUT",
    "LARCH_RATE_CURSOR_INPUT",
    "LARCH_RATE_CURSOR_CACHE_READ",
    "LARCH_RATE_CURSOR_OUTPUT",
    "LARCH_RATE_CURSOR_AGGREGATE",
    "LARCH_RATE_CLAUDE_SUB_AGGREGATE",
];

/// Serialize the configured token-rate overrides for a composed report child.
pub fn cost_overrides_from_environment() -> String {
    serde_json::to_string(
        &COST_OVERRIDE_ENV_NAMES
            .iter()
            .filter_map(|key| env::var(key).ok().map(|value| (*key, value)))
            .collect::<BTreeMap<_, _>>(),
    )
    .unwrap_or_else(|_error| "{}".to_owned())
}

/// One completed report render.
struct ReportOutcome {
    code: i32,
    comment_url: String,
    error: String,
}

impl ReportOutcome {
    fn failed(message: impl Into<String>) -> Self {
        Self {
            code: 1,
            comment_url: String::new(),
            error: message.into(),
        }
    }

    const fn ok(comment_url: String) -> Self {
        Self {
            code: 0,
            comment_url,
            error: String::new(),
        }
    }

    fn usage() -> Self {
        Self {
            code: 2,
            comment_url: String::new(),
            error: "usage".to_owned(),
        }
    }
}

/// Options one `final-report write` invocation carries.
struct WriteOptions {
    implement_tmpdir: PathBuf,
    comment_only: bool,
    print_stdout: bool,
    skip_tracking_upsert: bool,
    normalized_outcome: String,
    normalized_merge_downgraded: String,
    cost_overrides: BTreeMap<String, String>,
}

/// Run the `final-report write` command.
#[must_use]
pub fn write(arguments: &[OsString]) -> ExitCode {
    let outcome = execute_write(arguments);
    emit_kv("COMMENT_URL", &outcome.comment_url);
    emit_kv("STATUS", if outcome.code == 0 { "ok" } else { "failed" });
    if !outcome.error.is_empty() {
        emit_kv("ERROR", &collapse(&outcome.error));
    }
    exit_code(outcome.code)
}

/// Compose one report for an in-process caller that owns its own stdout.
///
/// The run-log terminal flush is the only such caller; routing it here keeps
/// one owner instead of re-entering the command through a child process.
///
/// # Errors
///
/// Returns the collapsed operator-facing reason the report did not publish.
pub fn write_report(arguments: &[OsString]) -> Result<(), String> {
    let outcome = execute_write(arguments);
    if outcome.code == 0 {
        return Ok(());
    }
    Err(collapse(&outcome.error))
}

fn execute_write(arguments: &[OsString]) -> ReportOutcome {
    let parsed = parse_with_flags(
        arguments,
        &[
            "--implement-tmpdir",
            "--normalized-outcome",
            "--normalized-merge-downgraded",
            "--cost-overrides-json",
        ],
        &[
            "--comment-only",
            "--print-stdout",
            "--skip-tracking-upsert",
            "--reconcile-stalled-summary",
            "--strict-stalled-summary",
        ],
        0,
    );
    let Some(tmpdir) = parsed.value("--implement-tmpdir") else {
        return ReportOutcome::usage();
    };
    if parsed.error().is_some() {
        return ReportOutcome::usage();
    }
    let merge_downgraded = parsed.value("--normalized-merge-downgraded").map_or_else(
        || "false".to_owned(),
        |value| value.to_string_lossy().into_owned(),
    );
    if !matches!(merge_downgraded.as_str(), "true" | "false") {
        return ReportOutcome::usage();
    }
    let normalized_outcome = parsed
        .value("--normalized-outcome")
        .map_or_else(String::new, |value| value.to_string_lossy().into_owned());
    let overrides_json = parsed.value("--cost-overrides-json").map_or_else(
        || "{}".to_owned(),
        |value| value.to_string_lossy().into_owned(),
    );

    let mut outcome = match validate(&overrides_json, &normalized_outcome) {
        Err(message) => ReportOutcome::failed(format!("final report render failed: {message}")),
        Ok(cost_overrides) => write_final_report(&WriteOptions {
            implement_tmpdir: PathBuf::from(tmpdir),
            comment_only: parsed.flag("--comment-only"),
            print_stdout: parsed.flag("--print-stdout"),
            skip_tracking_upsert: parsed.flag("--skip-tracking-upsert"),
            normalized_outcome,
            normalized_merge_downgraded: merge_downgraded,
            cost_overrides,
        }),
    };
    if outcome.code == 0 && parsed.flag("--reconcile-stalled-summary") {
        reconcile_stalled_summary(
            Path::new(tmpdir),
            parsed.flag("--strict-stalled-summary"),
            &mut outcome,
        );
    }
    outcome
}

/// Run the `final-report step18b` command.
#[must_use]
pub fn step18b(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--implement-tmpdir", "--step17-emitted"],
        &[],
        0,
    );
    let Some(tmpdir) = parsed.value("--implement-tmpdir") else {
        emit_kv("ERROR", "usage");
        return ExitCode::from(2);
    };
    let explicit = match parsed
        .value("--step17-emitted")
        .map(|value| value.to_string_lossy().into_owned())
    {
        None => None,
        Some(value) if value == "true" => Some(true),
        Some(value) if value == "false" => Some(false),
        Some(_invalid) => {
            emit_kv("ERROR", "usage");
            return ExitCode::from(2);
        }
    };
    let tmpdir = PathBuf::from(tmpdir);
    let step17_present =
        explicit.unwrap_or_else(|| tmpdir.join(".step17-emitted").symlink_metadata().is_ok());
    if tmpdir.join(".step16-16a-done").symlink_metadata().is_err() {
        let _ignored = delegate(
            &tmpdir,
            [
                "implement".into(),
                "step-16-16a".into(),
                "--implement-tmpdir".into(),
                OsString::from(&tmpdir),
            ],
        );
    }
    let summary = tmpdir.join("summary-final.md");
    let snapshot = tmpdir.join(".step18-prebody");
    let mut snapshot_status = "absent";
    if summary.symlink_metadata().is_ok() {
        match fs::read(&summary).and_then(|bytes| fs::write(&snapshot, bytes)) {
            Ok(()) => snapshot_status = "true",
            Err(_error) => {
                snapshot_status = "false";
                let _ignored = fs::remove_file(&snapshot);
            }
        }
    }
    let outcome = write_final_report(&WriteOptions {
        implement_tmpdir: tmpdir,
        comment_only: false,
        print_stdout: false,
        skip_tracking_upsert: false,
        normalized_outcome: String::new(),
        normalized_merge_downgraded: "false".to_owned(),
        cost_overrides: BTreeMap::new(),
    });
    let summary_bytes = fs::read(&summary).unwrap_or_default();
    let summary_present = summary.is_file() && !summary_bytes.is_empty();
    let snapshot_changed =
        snapshot.is_file() && fs::read(&snapshot).is_ok_and(|previous| previous != summary_bytes);
    let snapshot_unavailable = matches!(snapshot_status, "absent" | "false");
    let mut emit_body = !step17_present;
    if outcome.code == 0
        && summary_present
        && !emit_body
        && (snapshot_unavailable || snapshot_changed)
    {
        emit_body = true;
    }
    emit_kv(
        "EMIT_BODY",
        bool_text(emit_body && outcome.code == 0 && summary_present),
    );
    emit_kv("WFR_RC", &outcome.code.to_string());
    emit_kv("STEP17_EMITTED_PRESENT", bool_text(step17_present));
    emit_kv("SNAPSHOT_OK", snapshot_status);
    let error = collapse(&outcome.error);
    emit_kv("ERROR", &error);
    if !error.is_empty() {
        // Step 18's `append_failure_best_effort` captures this stream, and the
        // tmpdir is torn down right after, so stdout KVs alone are not durable.
        eprintln!("final report render failed: {error}");
    }
    exit_code(outcome.code)
}

fn exit_code(code: i32) -> ExitCode {
    u8::try_from(code).map_or(ExitCode::FAILURE, ExitCode::from)
}

const fn bool_text(value: bool) -> &'static str {
    if value { "true" } else { "false" }
}

/// Collapse whitespace and bound one operator-facing message.
fn collapse(message: &str) -> String {
    let collapsed = message.split_whitespace().collect::<Vec<&str>>().join(" ");
    collapsed.chars().take(500).collect()
}

/// Validate the cost-override map and the normalized-outcome choice.
fn validate(
    overrides_json: &str,
    normalized_outcome: &str,
) -> Result<BTreeMap<String, String>, String> {
    let parsed: Value = serde_json::from_str(overrides_json)
        .map_err(|error| format!("cost overrides must be a JSON string map: {error}"))?;
    let Some(object) = parsed.as_object() else {
        return Err("cost overrides must be a JSON string map".to_owned());
    };
    let mut overrides = BTreeMap::new();
    let mut unknown: Vec<&str> = Vec::new();
    for (key, value) in object {
        let Some(text) = value.as_str() else {
            return Err("cost overrides must be a JSON string map".to_owned());
        };
        if !COST_OVERRIDE_ENV_NAMES.contains(&key.as_str()) {
            unknown.push(key.as_str());
        }
        let _replaced = overrides.insert(key.clone(), text.to_owned());
    }
    if !unknown.is_empty() {
        unknown.sort_unstable();
        return Err(format!("unknown cost override key: {}", unknown[0]));
    }
    if !normalized_outcome.is_empty() && !report::NORMALIZED_OUTCOMES.contains(&normalized_outcome)
    {
        return Err("normalized outcome was invalid".to_owned());
    }
    Ok(overrides)
}

/// Run one delegated Python verb with the run's tmpdir published to the child.
fn delegate(
    implement_tmpdir: &Path,
    arguments: impl IntoIterator<Item = OsString>,
) -> Result<(i32, String), String> {
    publish_session_environment(vec![(
        ChildEnvironment::ImplementTmpdir,
        OsString::from(implement_tmpdir),
    )]);
    let output = run_python_verb(arguments, VERB_TIMEOUT)?;
    let code = output.status().code().unwrap_or(1);
    Ok((code, String::from_utf8_lossy(output.stdout()).into_owned()))
}

fn kv_value(text: &str, key: &str) -> String {
    read_kv_from_text(text, key).unwrap_or_default()
}

/// Clean a candidate identity value: trim, and treat placeholders as empty.
///
/// Shared with the `render run-summary` owner so the identity resolution has one
/// copy (mirrors Python `_resolve_run_identity.clean`).
pub fn identity_clean(value: &str) -> String {
    let text = value.trim();
    if matches!(text, "" | "unknown" | "None") {
        String::new()
    } else {
        text.to_owned()
    }
}

/// Resolve `(larch_version, main_model, effort)` for the summary identity rows.
///
/// Explicit overrides win, then the committed manifest, then live fallbacks.
/// Passing empty overrides reproduces the manifest-only `/implement` behavior;
/// the `render run-summary` owner passes its CLI overrides. Shared so both paths
/// resolve identity identically (Python `_resolve_run_identity`).
pub fn resolve_run_identity(
    manifest: &Path,
    larch_version: &str,
    main_model: &str,
    effort: &str,
) -> RunSummaryIdentity {
    let manifest_authoritative = manifest.is_file();
    let data = report::json_object(manifest);
    let roster_model = data
        .get("model_roster")
        .and_then(Value::as_object)
        .and_then(|roster| roster.get("main"))
        .and_then(Value::as_str)
        .unwrap_or_default();
    let version = [
        identity_clean(larch_version),
        identity_clean(
            data.get("larch_version")
                .and_then(Value::as_str)
                .unwrap_or_default(),
        ),
        plugin_version(),
    ]
    .into_iter()
    .find(|value| !value.is_empty())
    .unwrap_or_else(|| "unknown".to_owned());
    let mut model = [identity_clean(main_model), identity_clean(roster_model)]
        .into_iter()
        .find(|value| !value.is_empty())
        .unwrap_or_default();
    if model.is_empty() && !manifest_authoritative {
        model = live_main_model();
    }
    let effort = [
        identity_clean(effort),
        identity_clean(
            data.get("effort")
                .and_then(Value::as_str)
                .unwrap_or_default(),
        ),
        identity_clean(&env::var("CLAUDE_CODE_EFFORT_LEVEL").unwrap_or_default()),
        identity_clean(&env::var("CLAUDE_EFFORT").unwrap_or_default()),
    ]
    .into_iter()
    .find(|value| !value.is_empty())
    .unwrap_or_else(|| "unknown".to_owned());
    RunSummaryIdentity {
        larch_version: version,
        main_model: if model.is_empty() {
            "unknown".to_owned()
        } else {
            model
        },
        effort,
    }
}

/// Recover the main-agent model from the live session transcript.
///
/// Only reached when the run manifest is missing, which is the same degraded
/// path the Python owner covered with `tokens.read_main_model`. Resolves the
/// transcript in-process through the Rust `token claude-source` owner (#8557).
fn live_main_model() -> String {
    let Ok(source) = crate::token_commands::resolve_claude_source(None) else {
        return String::new();
    };
    let Ok(text) = fs::read_to_string(&source.transcript) else {
        return String::new();
    };
    let model = claude_model_from_transcript(&text);
    if model == "unknown" {
        String::new()
    } else {
        model
    }
}

/// Resolve the priced cost fields for the run, degrading to `cost_unavailable`.
fn cost_fields(
    implement_tmpdir: &Path,
    run_dir: &Path,
    overrides: &BTreeMap<String, String>,
) -> RunSummaryCost {
    let unavailable = RunSummaryCost {
        cost_unavailable: true,
        ..RunSummaryCost::default()
    };
    let Some(report_path) = resolve_token_report(implement_tmpdir, run_dir) else {
        return unavailable;
    };
    let mut data = report::json_object(&report_path);
    if data.is_empty() {
        return unavailable;
    }
    if data
        .get("claude")
        .and_then(Value::as_object)
        .and_then(|claude| claude.get("totals"))
        .and_then(Value::as_object)
        .is_none_or(Map::is_empty)
    {
        return unavailable;
    }
    enrich_by_model(&mut data, run_dir);
    let mut argv = report::token_argv_from_report(&data);
    if argv.is_empty() {
        return unavailable;
    }
    let main_model = report::json_object(&run_dir.join("manifest.json"))
        .get("model_roster")
        .and_then(Value::as_object)
        .and_then(|roster| roster.get("main"))
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned();
    if !main_model.is_empty() {
        argv.splice(0..0, ["--claude-model".to_owned(), main_model]);
    }
    let Some(cost) = price_run_cost(&argv, overrides) else {
        return unavailable;
    };
    if cost.total_cost == "N/A" {
        return unavailable;
    }
    cost
}

/// Price one `token cost` argv through the reused pricing pipeline, returning the
/// filled [`RunSummaryCost`] or `None` when the argv does not parse.
///
/// Shared by the `/implement` final report and the `render run-summary` owner so
/// the pricing tail (`from_cost_argv` → `display_rates` → `price_counts` →
/// `render_cost_kv` → field reads) has one copy. Callers apply their own
/// unavailability policy on the result.
pub fn price_run_cost(
    argv: &[String],
    overrides: &BTreeMap<String, String>,
) -> Option<RunSummaryCost> {
    let (counts, claude_model) = TokenCounts::from_cost_argv(argv).ok()?;
    let mut environment: BTreeMap<String, String> = env::vars().collect();
    environment.extend(
        overrides
            .iter()
            .map(|(key, value)| (key.clone(), value.clone())),
    );
    let mut observations = TokenObservations::default();
    let rates = display_rates(&environment, &claude_model, &mut observations);
    let values = price_counts(&counts, &rates);
    let rendered = render_cost_kv(&values);
    let read = |key: &str| {
        let value = kv_value(&rendered, key);
        if value.is_empty() {
            "N/A".to_owned()
        } else {
            value
        }
    };
    let optional = |key: &str| {
        let value = kv_value(&rendered, key);
        (!value.is_empty()).then_some(value)
    };
    Some(RunSummaryCost {
        cost_unavailable: false,
        total_cost: read("TOTAL_COST"),
        claude_cost: read("CLAUDE_COST"),
        codex_cost: read("CODEX_COST"),
        codex_gpt_5_5_cost: read("CODEX_GPT_5_5_COST"),
        codex_gpt_5_4_mini_cost: read("CODEX_GPT_5_4_MINI_COST"),
        cursor_cost: read("CURSOR_COST"),
        cursor_composer_cost: optional("CURSOR_COMPOSER_COST"),
        cursor_grok_cost: optional("CURSOR_GROK_COST"),
        claude_sub_cost: read("CLAUDE_SUB_COST"),
        total_tokens: kv_value(&rendered, "TOTAL_TOKENS")
            .parse::<i64>()
            .unwrap_or(0),
    })
}

/// Locate the rendered token report, generating one through the Rust owner.
fn resolve_token_report(implement_tmpdir: &Path, run_dir: &Path) -> Option<PathBuf> {
    for candidate in [
        run_dir.join("token-report.json"),
        implement_tmpdir.join("token-report-rendered.json"),
    ] {
        if candidate.is_file()
            && !candidate
                .symlink_metadata()
                .is_ok_and(|meta| meta.is_symlink())
        {
            return Some(candidate);
        }
    }
    let generated = implement_tmpdir.join("token-report-truth.json");
    let arguments: Vec<OsString> = vec![
        "--full".into(),
        "--format".into(),
        "json".into(),
        "--output".into(),
        OsString::from(&generated),
        "--implement-tmpdir".into(),
        OsString::from(implement_tmpdir),
    ];
    if crate::token_commands::report(&arguments) == ExitCode::SUCCESS && generated.is_file() {
        Some(generated)
    } else {
        None
    }
}

/// Merge per-model Codex and spawned-Claude buckets from the committed ledger.
fn enrich_by_model(data: &mut Map<String, Value>, run_dir: &Path) {
    let missing: Vec<&str> = ["BUCKETS_codex_by_model", "BUCKETS_claude_sub_by_model"]
        .into_iter()
        .filter(|key| {
            data.get(*key)
                .and_then(Value::as_object)
                .is_none_or(Map::is_empty)
        })
        .collect();
    if missing.is_empty() {
        return;
    }
    let Some(ledger) = run_log_ledger_path(run_dir) else {
        return;
    };
    let mut observations = TokenObservations::default();
    let Ok(recovered) = build_report_from_ledgers(&[ledger], &mut observations) else {
        return;
    };
    for key in missing {
        if let Some(split) = recovered
            .get(key)
            .and_then(Value::as_object)
            .filter(|split| !split.is_empty())
        {
            let _replaced = data.insert(key.to_owned(), Value::Object(split.clone()));
        }
    }
}

/// Resolve the four PR line counts, refreshing the ship-state cache on success.
fn pr_line_counts(repo: &str, repo_unavailable: bool, pr_number: &str, ship: &Path) -> [String; 4] {
    let empty = [const { String::new() }; 4];
    if repo_unavailable || pr_number.is_empty() || pr_number == "0" {
        return empty;
    }
    if report::read_state_kv(ship, "LINES_PR_NUMBER") == pr_number
        && report::read_state_kv(ship, "LINES_STATUS") == "ok"
    {
        let cached = ["CODE_ADDED", "CODE_DELETED", "LOGS_ADDED", "LOGS_DELETED"]
            .map(|key| report::read_state_kv(ship, key));
        if cached
            .iter()
            .all(|value| !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
        {
            return cached;
        }
    }
    let Ok(pr_number_value) = pr_number.parse::<u64>() else {
        return empty;
    };
    let Some(result) = crate::token_commands::fetch_pr_line_counts(pr_number_value, repo) else {
        return empty;
    };
    let counts = [
        result.code_added.to_string(),
        result.code_deleted.to_string(),
        result.logs_added.to_string(),
        result.logs_deleted.to_string(),
    ];
    cache_line_counts(ship, pr_number, &counts);
    counts
}

/// Rewrite the ship-state line-count cache, skipping an unwritable state file.
fn cache_line_counts(ship: &Path, pr_number: &str, counts: &[String; 4]) {
    if !ship.is_file() || ship.symlink_metadata().is_ok_and(|meta| meta.is_symlink()) {
        return;
    }
    let Ok(existing) = fs::read_to_string(ship) else {
        return;
    };
    let rows = [
        ("LINES_STATUS", "ok".to_owned()),
        ("CODE_ADDED", counts[0].clone()),
        ("CODE_DELETED", counts[1].clone()),
        ("LOGS_ADDED", counts[2].clone()),
        ("LOGS_DELETED", counts[3].clone()),
    ];
    let merged = report::merged_line_count_state(&existing, pr_number, &rows);
    let temporary = ship.with_extension("sh.tmp");
    if fs::write(&temporary, merged).is_ok() {
        let _ignored = fs::rename(&temporary, ship);
    }
}

/// Render the review-phase detail prefix, degrading to empty.
fn review_detail(implement_tmpdir: &Path, run_dir: &Path) -> String {
    let rounds_root = if run_dir.is_dir() {
        run_dir.to_path_buf()
    } else {
        implement_tmpdir.to_path_buf()
    };
    if !rounds_root.is_dir() {
        return String::new();
    }
    let timing = implement_tmpdir.join("timing-ledger.tsv");
    let token_ledger = report::latest_token_ledger(implement_tmpdir);
    let mut findings = run_dir.join("review-findings-full.jsonl");
    if !findings.is_file() {
        findings = implement_tmpdir.join("review-findings-full.jsonl");
    }
    let rendered = phase_detail::render_phase_detail(&RenderRequest {
        rounds_root: &rounds_root,
        skill: PhaseSkill::Implement,
        timing_ledger: timing.is_file().then_some(timing.as_path()),
        token_ledger: token_ledger.as_deref(),
        findings_file: findings.is_file().then_some(findings.as_path()),
        top_n: 7,
        gantt_enabled: true,
    });
    if rendered.trim().is_empty() {
        return String::new();
    }
    let redacted = redact(&rendered);
    let text = redacted.text();
    if text.contains("[content truncated") {
        return String::new();
    }
    text.to_owned()
}

/// Render the provider-neutral run-log reference for the summary.
pub fn run_log_reference(session: &Path, run_id: &str, implement_tmpdir: &Path) -> String {
    if run_id.is_empty() {
        return "N/A".to_owned();
    }
    let disabled = format!(
        "no archive published because run-log storage was disabled, skill `implement`, \
run ID `{run_id}`"
    );
    let lifecycle = implement_tmpdir
        .join("larch-logs")
        .join("implement")
        .join(run_id)
        .join("manifest.json");
    if lifecycle.is_file()
        && !lifecycle
            .symlink_metadata()
            .is_ok_and(|meta| meta.is_symlink())
        && pins_disabled_publication(&report::json_object(&lifecycle), run_id)
    {
        return disabled;
    }
    let repo_root = report::read_state_kv(session, "REPO_ROOT");
    if repo_root.is_empty() {
        return format!("provider `unknown`, skill `implement`, run ID `{run_id}`");
    }
    let Ok((_root, origin, environment)) =
        crate::run_log_commands::resolve_repository_environment_path(Some(Path::new(&repo_root)))
    else {
        return format!("provider `unknown`, skill `implement`, run ID `{run_id}`");
    };
    match larch_core::resolve_run_log_storage(Path::new(&repo_root), &environment, &origin) {
        Err(_unresolved) => format!("provider `unknown`, skill `implement`, run ID `{run_id}`"),
        Ok(resolution) => match larch_core::require_enabled_storage(&resolution) {
            Err(_disabled) => disabled,
            Ok(storage) => format!(
                "provider `{}`, skill `implement`, run ID `{run_id}`",
                storage.scheme()
            ),
        },
    }
}

/// Whether a lifecycle manifest pins this run to disabled publication.
fn pins_disabled_publication(manifest: &Map<String, Value>, run_id: &str) -> bool {
    let text = |key: &str| {
        manifest
            .get(key)
            .and_then(Value::as_str)
            .unwrap_or_default()
    };
    if manifest
        .get("lifecycle_schema_version")
        .and_then(Value::as_i64)
        != Some(DISABLED_LIFECYCLE_SCHEMA_VERSION)
        || text("publication_mode") != "disabled"
        || !DISABLED_STORAGE_REASONS.contains(&text("storage_resolution_reason"))
        || text("skill") != "implement"
        || text("run_id") != run_id
    {
        return false;
    }
    let namespace = text("local_namespace_id");
    if namespace.len() != 64
        || !namespace
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return false;
    }
    ["storage_base_uri", "tool_repo_uri", "storage_origin_id"]
        .iter()
        .all(|field| manifest.get(*field).is_none_or(Value::is_null))
}

/// Compose and publish one terminal final report.
#[expect(
    clippy::too_many_lines,
    reason = "One terminal report composition; splitting it would hide the ordered publication contract."
)]
fn write_final_report(options: &WriteOptions) -> ReportOutcome {
    let tmpdir = options.implement_tmpdir.as_path();
    let parent = tmpdir.join("parent-issue.md");
    let session = tmpdir.join("session-env.sh");
    let ship = tmpdir.join("ship-pr-state.sh");
    let finalize = tmpdir.join("finalize-state.sh");
    let run_flags = tmpdir.join("run-flags.sh");
    let issue = {
        let value = report::read_state_kv(&parent, "ISSUE_NUMBER");
        if value.is_empty() {
            "0".to_owned()
        } else {
            value
        }
    };
    let mut run_id = report::read_state_kv(&parent, "RUN_ID");
    if run_id.is_empty() {
        let session_id = tmpdir.join("session-id");
        run_id = if session_id.is_file() {
            fs::read_to_string(&session_id)
                .unwrap_or_default()
                .trim()
                .to_owned()
        } else {
            "unknown".to_owned()
        };
    }
    if run_id.contains('/') || run_id.contains("..") {
        return ReportOutcome::failed("invalid RUN_ID (path-traversal characters rejected)");
    }
    let resolved_run_id = if run_id.is_empty() {
        "unknown".to_owned()
    } else {
        run_id.clone()
    };
    let run_dir = tmpdir
        .join("larch-logs")
        .join("implement")
        .join(&resolved_run_id);
    let repo = report::read_state_kv(&session, "REPO");
    let repo_unavailable = report::read_state_kv(&session, "REPO_UNAVAILABLE") == "true";
    let mut pr_number = report::read_state_kv(&ship, "PR_NUMBER");
    if pr_number.is_empty() {
        pr_number = report::read_state_kv(&finalize, "PR_NUMBER");
    }
    let mut pr_url = report::read_state_kv(&ship, "PR_URL");
    if pr_url.is_empty() {
        pr_url = report::read_state_kv(&finalize, "PR_URL");
    }
    if pr_url.is_empty() {
        "N/A".clone_into(&mut pr_url);
    }
    let issue_url = if !repo.is_empty() && issue != "0" {
        format!("https://github.com/{repo}/issues/{issue}")
    } else {
        String::new()
    };

    let counts = pr_line_counts(&repo, repo_unavailable, &pr_number, &ship);
    let plan_review_line = {
        let cached = report::read_state_kv(&ship, "PLAN_REVIEW_LINE");
        if cached.is_empty() {
            report::derive_review_line(&run_dir, "plan-review-tally.json")
        } else {
            cached
        }
    };
    let code_review_line = report::derive_review_line(&run_dir, "code-review-tally.json");
    let (derived_oos_count, derived_oos_urls) = report::derive_oos_fields(&run_dir);
    let oos_count = {
        let cached = report::read_state_kv(&ship, "OOS_COUNT");
        let value = if cached.is_empty() {
            derived_oos_count
        } else {
            cached
        };
        if value.is_empty() {
            "0".to_owned()
        } else {
            value
        }
    };
    let oos_urls = {
        let cached = report::read_state_kv(&ship, "OOS_URLS");
        if cached.is_empty() {
            derived_oos_urls
        } else {
            cached
        }
    };
    let fallback = |value: &String, key: &str| -> String {
        if value.is_empty() {
            report::read_state_kv(&ship, key)
        } else {
            value.clone()
        }
    };

    let cost = cost_fields(tmpdir, &run_dir, &options.cost_overrides);
    let outcome_values: BTreeMap<String, String> = if options.normalized_outcome.is_empty() {
        stall_recovery::normalize_outcome(tmpdir, "")
            .unwrap_or_default()
            .into_iter()
            .collect()
    } else {
        [
            (
                "IMPLEMENT_NORMALIZED_OUTCOME".to_owned(),
                options.normalized_outcome.clone(),
            ),
            (
                "IMPLEMENT_MERGE_DOWNGRADED".to_owned(),
                options.normalized_merge_downgraded.clone(),
            ),
        ]
        .into_iter()
        .collect()
    };
    let outcome = report::outcome_with_manifest_only_backstop(
        &run_dir,
        outcome_values
            .get("IMPLEMENT_NORMALIZED_OUTCOME")
            .map_or("bailed", String::as_str),
        &ship,
        &finalize,
    );
    // #7074: a terminal needs-user ship handoff creates the PR but skips the merge
    // and CI watch, so it must not render as DONE. Prime the exec-issues row from
    // the committed handoff before the issue counts load, so the row is counted.
    let (needs_user_reason, needs_user_next_action) =
        match prime_needs_user_execution_issue(tmpdir, &run_dir, &outcome) {
            Ok(pair) => pair,
            Err(message) => return ReportOutcome::failed(message),
        };
    let load_result = report::load_issue_detail_groups(tmpdir, Some(&run_dir), true);
    let (exec_count, warn_count) = report::count_load_result(&load_result);
    let plan_coverage_line = match plan_coverage_line(tmpdir) {
        Ok(line) => line,
        Err(message) => return ReportOutcome::failed(message),
    };

    let summary_body = report::render_run_summary(&RunSummaryFields {
        skill: "implement".to_owned(),
        outcome: outcome.clone(),
        run_id: resolved_run_id.clone(),
        workflow_path: report::read_state_kv(&session, "WORKFLOW_PATH"),
        duration: report::final_report_duration(&run_dir, &ship),
        issue_number: issue.clone(),
        issue_url,
        pr_number,
        pr_url,
        plan_review_line,
        plan_coverage_line,
        difficulty_line: report::difficulty_summary_line(&run_dir),
        dynamic_archetypes_line: report::dynamic_archetypes_line(tmpdir),
        code_review_line,
        code_added: fallback(&counts[0], "CODE_ADDED"),
        code_deleted: fallback(&counts[1], "CODE_DELETED"),
        logs_added: fallback(&counts[2], "LOGS_ADDED"),
        logs_deleted: fallback(&counts[3], "LOGS_DELETED"),
        oos_count,
        oos_urls,
        exec_issues: exec_count,
        warnings: warn_count,
        run_logs_path: run_log_reference(&session, &run_id, tmpdir),
        force_requested: report::read_state_kv(&run_flags, "FORCE_REQUESTED"),
        merge_downgraded: outcome_values
            .get("IMPLEMENT_MERGE_DOWNGRADED")
            .cloned()
            .unwrap_or_else(|| "false".to_owned()),
        needs_user_reason,
        needs_user_next_action,
        identity: resolve_run_identity(&run_dir.join("manifest.json"), "", "", ""),
        cost,
    });
    let issue_detail = report::build_issue_detail_section(&load_result, |kind, details| {
        assess_issue_details(tmpdir, kind, details)
    });
    let body = report::join_prefixed_summary(
        &[
            &review_detail(tmpdir, &run_dir),
            &issue_detail,
            &architectural_sections(tmpdir),
        ],
        &summary_body,
    );

    let summary = tmpdir.join("summary-final.md");
    if let Err(error) = write_run_log_file(&summary, &body) {
        return finish(
            options,
            &body,
            ReportOutcome::failed(format!("summary-final write failed: {error}")),
        );
    }
    if !options.comment_only {
        if let Err(error) = write_run_log_file(&run_dir.join("final-summary.md"), &body) {
            return finish(
                options,
                &body,
                ReportOutcome::failed(format!("final-summary write failed: {error}")),
            );
        }
        if !options.skip_tracking_upsert
            && let Err(message) = reconcile_manifest(tmpdir, &resolved_run_id, &outcome)
        {
            return finish(options, &body, ReportOutcome::failed(message));
        }
        if options.skip_tracking_upsert {
            return finish(options, &body, ReportOutcome::ok(String::new()));
        }
    }
    let mut comment_url = String::new();
    if issue != "0" && !repo_unavailable {
        let marker = format!("<!-- larch:final-summary v1 runid={run_id} -->");
        match crate::tracking_issue_commands::upsert_summary_rows(
            &issue,
            &marker,
            &summary.to_string_lossy(),
            (!repo.is_empty()).then_some(repo.as_str()),
        ) {
            Ok(rows) => {
                comment_url = rows
                    .into_iter()
                    .find_map(|(key, value)| (key == "COMMENT_URL").then_some(value))
                    .unwrap_or_default();
            }
            Err(message) => {
                return finish(
                    options,
                    &body,
                    ReportOutcome::failed(message.chars().take(500).collect::<String>()),
                );
            }
        }
    }
    finish(options, &body, ReportOutcome::ok(comment_url))
}

/// Emit the composed body when requested, then return the outcome unchanged.
fn finish(options: &WriteOptions, body: &str, outcome: ReportOutcome) -> ReportOutcome {
    if options.print_stdout {
        let _written = write_stdout(body);
    }
    outcome
}

/// Assess execution-issue materiality through one bounded Claude subprocess.
///
/// Every failure degrades to no assessments, which renders the same section
/// without the per-item sentences, matching the Python owner's fail-soft path.
pub fn assess_issue_details(
    tmpdir: &Path,
    category: &str,
    details: &[report::IssueDetail],
) -> BTreeMap<String, String> {
    let empty = BTreeMap::new();
    if details.is_empty() {
        return empty;
    }
    let rows: Vec<Value> = details
        .iter()
        .enumerate()
        .map(|(index, detail)| {
            serde_json::json!({
                "id": index.to_string(),
                "display_text": report::assessment_prompt_text(&detail.display_text),
                "count": detail.count,
            })
        })
        .collect();
    let prompt = format!(
        "You assess execution-issue materiality for a larch run final summary.\n\
Category: {category}\n\
For each item, write one short sentence (max 25 words) on materiality/impact for operators.\n\
Return ONLY valid JSON matching this schema:\n\
{{\"assessments\": [{{\"id\": \"<same id from input>\", \"assessment\": \"<one sentence>\"}}]}}\n\
Include an assessment entry for every input id. No markdown fences. No extra keys.\n\
Input:\n\
{}\n",
        Value::Array(rows)
    );
    let work = tmpdir.join(".exec-issue-assessment");
    if fs::create_dir_all(&work).is_err() {
        return empty;
    }
    let prompt_file = work.join("prompt.txt");
    let output_file = work.join("output.txt");
    let _stale = fs::remove_file(&output_file);
    if fs::write(&prompt_file, prompt).is_err() {
        return empty;
    }
    let model = env::var(report::ENV_EXEC_ISSUE_ASSESSMENT_MODEL)
        .unwrap_or_default()
        .trim()
        .to_owned();
    let model = if model.is_empty() {
        report::DEFAULT_ASSESSMENT_MODEL.to_owned()
    } else {
        model
    };
    let arguments = crate::agent_commands::AgentRawArguments {
        arguments: vec![
            "--prompt-file".into(),
            OsString::from(&prompt_file),
            "--output-file".into(),
            OsString::from(&output_file),
            "--timeout".into(),
            report::ASSESSMENT_TIMEOUT_SECONDS.to_string().into(),
            "--model".into(),
            model.into(),
            "--timing-task-kind".into(),
            "exec-issue-assessment".into(),
        ],
    };
    if crate::claude_commands::launch_claude_subprocess(&arguments) != ExitCode::SUCCESS {
        return empty;
    }
    let Ok(inner) = fs::read_to_string(&output_file) else {
        return empty;
    };
    let parsed = parse_assessments(inner.trim());
    let _cleanup = fs::remove_dir_all(&work);
    parsed
}

/// Parse the assessment payload, keeping only well-formed string rows.
fn parse_assessments(text: &str) -> BTreeMap<String, String> {
    let mut parsed = BTreeMap::new();
    let Ok(Value::Object(body)) = serde_json::from_str::<Value>(text) else {
        return parsed;
    };
    let Some(items) = body.get("assessments").and_then(Value::as_array) else {
        return parsed;
    };
    for item in items {
        let Some(row) = item.as_object() else {
            continue;
        };
        let (Some(id), Some(assessment)) = (
            row.get("id").and_then(Value::as_str),
            row.get("assessment").and_then(Value::as_str),
        ) else {
            continue;
        };
        let cleaned = report::assessment_sentence(assessment);
        if !cleaned.is_empty() {
            let _replaced = parsed.insert(id.to_owned(), cleaned);
        }
    }
    parsed
}

/// Read the plan-coverage line from its Rust scope-disposition owner.
///
/// The owner runs in this process after #8612, so a returned error is a genuine
/// coverage-integrity failure and fails the report; the expected post-merge
/// stale-fingerprint mismatch degrades to an empty line inside the owner itself.
fn plan_coverage_line(tmpdir: &Path) -> Result<String, String> {
    match crate::implement_scope_disposition_commands::plan_coverage_report_line(tmpdir, None) {
        Ok(line) => Ok(line),
        Err(error) => Err(format!("plan coverage summary failed: {error}")),
    }
}

/// Read the architectural invariant and guideline sections, fail-soft.
fn architectural_sections(tmpdir: &Path) -> String {
    crate::architectural_assessment_commands::architectural_sections_for_report(tmpdir)
}

/// Append the needs-user execution issue, or resolve a superseded one.
fn prime_needs_user_execution_issue(
    tmpdir: &Path,
    run_dir: &Path,
    outcome: &str,
) -> Result<(String, String), String> {
    let handoff = tmpdir.join(".ship-route-exit-handoff.env");
    let reason = report::read_state_kv(&handoff, "NEEDS_USER_REASON");
    let next_action = report::read_state_kv(&handoff, "NEXT_ACTION");
    if report::MERGE_COMPLETED_OUTCOMES.contains(&outcome) {
        if !reason.is_empty() {
            resolve_needs_user_execution_issue(tmpdir, run_dir, &reason, &next_action)?;
        }
        return Ok((String::new(), String::new()));
    }
    if reason.is_empty() {
        return Ok((String::new(), String::new()));
    }
    let entry = report::needs_user_execution_entry(&reason, &next_action);
    let _best_effort = append_execution_issue(
        &tmpdir.join("execution-issues.md"),
        NEEDS_USER_CATEGORY,
        &entry,
    );
    Ok((reason, next_action))
}

/// Record a durable resolution before removing the live needs-user entry.
fn resolve_needs_user_execution_issue(
    tmpdir: &Path,
    run_dir: &Path,
    reason: &str,
    next_action: &str,
) -> Result<(), String> {
    let entry = report::needs_user_execution_entry(reason, next_action);
    let identity = report::execution_issue_identity(NEEDS_USER_CATEGORY, &entry);
    let batch = run_dir.join("execution-issues.ndjson");
    if batch.is_file() {
        let text = fs::read_to_string(&batch).unwrap_or_default();
        if !batch_has_resolution(&text, &identity) {
            let record = format!(
                "{}\n",
                serde_json::json!({
                    "event": "execution-issue-resolved",
                    "issue_ids": [identity],
                    "resolution": "merge-completed",
                })
            );
            let staged = run_dir.join(".execution-issue-resolution.ndjson");
            fs::write(&staged, &record)
                .map_err(|error| format!("execution-issue resolution failed: {error}"))?;
            let appended = stage_append_batch(
                &tmpdir.join("larch-logs"),
                "implement",
                &run_dir
                    .file_name()
                    .map(|name| name.to_string_lossy().into_owned())
                    .unwrap_or_default(),
                "execution-issues",
                &staged,
            );
            let _ignored = fs::remove_file(&staged);
            let path =
                appended.map_err(|error| format!("execution-issue resolution failed: {error}"))?;
            let published = fs::read_to_string(&path).unwrap_or_default();
            if !batch_has_resolution(&published, &identity) {
                return Err("execution-issue resolution was not persisted".to_owned());
            }
        }
    }
    remove_live_execution_issue(&tmpdir.join("execution-issues.md"), &entry)
        .map_err(|error| format!("execution-issue live resolution failed: {error}"))
}

/// Whether the committed batch already resolves this execution-issue identity.
fn batch_has_resolution(text: &str, identity: &str) -> bool {
    text.lines().any(|line| {
        serde_json::from_str::<Value>(line)
            .ok()
            .and_then(|row| row.as_object().cloned())
            .is_some_and(|row| {
                row.get("event").and_then(Value::as_str) == Some("execution-issue-resolved")
                    && row
                        .get("issue_ids")
                        .and_then(Value::as_array)
                        .is_some_and(|ids| ids.iter().any(|id| id.as_str() == Some(identity)))
            })
    })
}

/// Drop one resolved entry from the mutable execution-issue log.
fn remove_live_execution_issue(log: &Path, entry: &str) -> Result<(), String> {
    if !log.is_file() {
        return Ok(());
    }
    let text = fs::read_to_string(log).map_err(|error| error.to_string())?;
    let mut removed = false;
    let kept: Vec<&str> = text
        .lines()
        .filter(|line| {
            if !removed && *line == entry {
                removed = true;
                return false;
            }
            true
        })
        .collect();
    if !removed {
        return Ok(());
    }
    let mut rewritten = kept.join("\n").trim_end().to_owned();
    rewritten.push('\n');
    fs::write(log, rewritten).map_err(|error| error.to_string())
}

/// Stamp the terminal `steps_ran`, `status`, and `pr_number` manifest fields.
fn reconcile_manifest(tmpdir: &Path, run_id: &str, outcome: &str) -> Result<(), String> {
    if run_id.is_empty() || run_id == "unknown" {
        return Ok(());
    }
    let run_dir = tmpdir.join("larch-logs").join("implement").join(run_id);
    if !run_dir.join("manifest.json").is_file() {
        return Ok(());
    }
    let mut fields: Vec<(String, Value)> = Vec::new();
    if !run_dir.join("run-statistics.md").is_file() {
        fields.push(("steps_ran.step9a1".to_owned(), Value::Bool(false)));
    }
    let step8 = run_dir.join("final-summary.md").is_file()
        || run_dir.join("version-bump-reasoning.md").is_file();
    fields.push(("steps_ran.step8".to_owned(), Value::Bool(step8)));
    let step7a = [
        "token-report.json",
        "timing-report.json",
        "execution-issues.ndjson",
        "session-transcript.jsonl",
    ]
    .iter()
    .any(|name| run_dir.join(name).is_file());
    fields.push(("steps_ran.step7a".to_owned(), Value::Bool(step7a)));
    if matches!(outcome, "pr-created" | "pr-created-draft" | "shipping") {
        fields.push((
            "status".to_owned(),
            Value::String(report::MANIFEST_STATUS_IN_PROGRESS.to_owned()),
        ));
    }
    let mut pr_number = report::read_state_kv(&tmpdir.join("ship-pr-state.sh"), "PR_NUMBER");
    if pr_number.is_empty() {
        pr_number = report::read_state_kv(&tmpdir.join("finalize-state.sh"), "PR_NUMBER");
    }
    let pr_number = pr_number.trim();
    if !pr_number.is_empty()
        && pr_number.bytes().all(|byte| byte.is_ascii_digit())
        && pr_number.parse::<i64>().is_ok_and(|value| value > 0)
    {
        fields.push((
            "pr_number".to_owned(),
            Value::Number(pr_number.parse::<i64>().unwrap_or_default().into()),
        ));
    }
    let log_root = tmpdir.join("larch-logs");
    let store = ManifestStore::open(&log_root)
        .map_err(|error| format!("run-log manifest reconcile failed: {error}"))?;
    let skill = RunLogSlug::parse("implement").map_err(|error| error.to_string())?;
    let slug = RunLogSlug::parse(run_id).map_err(|error| error.to_string())?;
    let layout = RunLogLayout::new(&log_root, skill, slug);
    store
        .update(&layout, &fields, &utc_now())
        .map(|_path| ())
        .map_err(|error| format!("run-log manifest reconcile failed: {error}"))
}

/// Rewrite a manifest-only shipped summary away from `stalled`.
fn reconcile_stalled_summary(tmpdir: &Path, strict: bool, outcome: &mut ReportOutcome) {
    let mut run_id = report::read_state_kv(&tmpdir.join("parent-issue.md"), "RUN_ID");
    if run_id.is_empty() && tmpdir.join("session-id").is_file() {
        fs::read_to_string(tmpdir.join("session-id"))
            .unwrap_or_default()
            .trim()
            .clone_into(&mut run_id);
    }
    let run_dir = tmpdir.join("larch-logs").join("implement").join(&run_id);
    let needed = report::stalled_summary_manifest_reconciliation_needed(&run_dir);
    let mut changed = false;
    if let Some(rewritten) = report::reconciled_stalled_summary(&run_dir) {
        changed = write_run_log_file(&run_dir.join("final-summary.md"), &rewritten).is_ok();
        if !changed && outcome.error.is_empty() {
            "stalled summary reconciliation failed".clone_into(&mut outcome.error);
        }
    }
    let still_needed = report::stalled_summary_manifest_reconciliation_needed(&run_dir);
    if strict && needed && (!changed || still_needed) {
        outcome.code = 1;
        if outcome.error.is_empty() {
            "stalled summary reconciliation failed".clone_into(&mut outcome.error);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unknown_cost_override_keys_are_rejected() {
        let error = validate(r#"{"LARCH_NOT_A_RATE":"1"}"#, "").expect_err("rejects");
        assert_eq!(error, "unknown cost override key: LARCH_NOT_A_RATE");
    }

    #[test]
    fn non_string_cost_override_values_are_rejected() {
        assert!(validate(r#"{"LARCH_TOKEN_RATE_PER_M":1}"#, "").is_err());
        assert!(validate("[]", "").is_err());
    }

    #[test]
    fn known_cost_overrides_and_outcomes_are_accepted() {
        let parsed = validate(r#"{"LARCH_TOKEN_RATE_PER_M":"3"}"#, "merged").expect("accepts");
        assert_eq!(
            parsed.get("LARCH_TOKEN_RATE_PER_M").map(String::as_str),
            Some("3")
        );
    }

    #[test]
    fn invalid_normalized_outcomes_are_rejected() {
        assert!(validate("{}", "not-an-outcome").is_err());
    }

    #[test]
    fn disabled_publication_requires_every_pin() {
        let manifest: Map<String, Value> = serde_json::from_str(&format!(
            r#"{{"lifecycle_schema_version":3,"publication_mode":"disabled",
                 "storage_resolution_reason":"config-file-missing",
                 "skill":"implement","run_id":"r1","local_namespace_id":"{}"}}"#,
            "a".repeat(64)
        ))
        .expect("fixture parses");
        assert!(pins_disabled_publication(&manifest, "r1"));
        assert!(!pins_disabled_publication(&manifest, "other"));
    }

    #[test]
    fn collapse_bounds_and_flattens_messages() {
        assert_eq!(collapse("a\n b\tc"), "a b c");
        assert_eq!(collapse(&"x".repeat(900)).len(), 500);
    }
}
