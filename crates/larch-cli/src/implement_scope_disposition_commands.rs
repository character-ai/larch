//! Rust owner for `implement scope-disposition` (#8612).
//!
//! Classifies diff content against plan scope, records operator disposition,
//! and validates shipping gates. Wire contracts match the retired Python owner.

use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::GixRepository;
use larch_core::{
    DuplicatePolicy, KvDocument, ParseOptions, ProcessOutput, RepositoryRead as _, Revision,
    StatusOptions, emit_kv, extract_firm_scope_paths, private_atomic_write,
    read_universal_newlines,
};
use serde_json::{Map, Value};
use sha2::{Digest as _, Sha256};

use crate::{
    argparse_compat::{ParsedCommandLine, parse_with_flags, usage_error},
    implement_child_seam::resolve_plugin_root,
    implement_dispatch_commands::delegate_verified_larch,
};

const PROGRAM: &str = "cli.py implement scope-disposition";
const USAGE: &str = "usage: cli.py implement scope-disposition [-h] {compute,record,validate-ship,invalidate-if-stale,render-deferred-inventory,summary-line} [--tmpdir TMPDIR] [--repo-root REPO_ROOT] [--plan-file PLAN_FILE] [--manifest-path MANIFEST_PATH] [--disposition {proceed-partial,bail-rescope}] [--repo REPO] [--tracking-issue TRACKING_ISSUE] [--run-id RUN_ID]";
const HELP: &str = concat!(
    "usage: cli.py implement scope-disposition [-h]\n",
    "                                          {compute,record,validate-ship,invalidate-if-stale,render-deferred-inventory,summary-line}\n",
    "                                          [--tmpdir TMPDIR] [--repo-root REPO_ROOT]\n",
    "                                          [--plan-file PLAN_FILE]\n",
    "                                          [--manifest-path MANIFEST_PATH]\n",
    "                                          [--disposition {proceed-partial,bail-rescope}]\n",
    "                                          [--repo REPO] [--tracking-issue TRACKING_ISSUE]\n",
    "                                          [--run-id RUN_ID]\n",
    "\n",
    "positional arguments:\n",
    "  {compute,record,validate-ship,invalidate-if-stale,render-deferred-inventory,summary-line}\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --tmpdir TMPDIR\n",
    "  --repo-root REPO_ROOT\n",
    "  --plan-file PLAN_FILE\n",
    "  --manifest-path MANIFEST_PATH\n",
    "  --disposition {proceed-partial,bail-rescope}\n",
    "  --repo REPO\n",
    "  --tracking-issue TRACKING_ISSUE\n",
    "  --run-id RUN_ID"
);
const OPTIONS: [&str; 8] = [
    "--tmpdir",
    "--repo-root",
    "--plan-file",
    "--manifest-path",
    "--disposition",
    "--repo",
    "--tracking-issue",
    "--run-id",
];
const ACTIONS: [&str; 6] = [
    "compute",
    "record",
    "validate-ship",
    "invalidate-if-stale",
    "render-deferred-inventory",
    "summary-line",
];
const DISPOSITIONS: [&str; 2] = ["proceed-partial", "bail-rescope"];
const COVERAGE_JSON: &str = "plan-coverage.json";
const COVERAGE_ENV: &str = "plan-coverage.env";
const UNTOUCHED_PATHS: &str = "plan-coverage-untouched.txt";
const TODOS_LEFT: &str = "plan-coverage-todos-left.txt";
const DISPOSITION_JSON: &str = "scope-disposition.json";
const FALLBACK_PROVENANCE: &str = "scope-fallback-provenance.json";
const SHIP_PR_STATE: &str = "ship-pr-state.sh";
const SESSION_ENV: &str = "session-env.sh";
const MAX_TODO_ITEMS: usize = 20;
const MAX_TODO_CHARS: usize = 4000;
const MAX_UNTOUCHED_INVENTORY: usize = 80;
const MIDDLE_PERCENT: i64 = 20;
const MIDDLE_COUNT: i64 = 10;
const HIGH_PERCENT: i64 = 50;
const HIGH_COUNT: i64 = 30;
const STALE_LIVE: &str = "coverage artifact does not match live repository inputs";
const NO_TRUSTED_COVERAGE: &str = "scope disposition exists without trusted coverage";

#[derive(Clone, Debug, PartialEq)]
struct PlanCoverage {
    total: i64,
    touched: i64,
    untouched: i64,
    untouched_percent: i64,
    band: String,
    plan_paths: Vec<String>,
    touched_paths: Vec<String>,
    untouched_paths: Vec<String>,
    todos_left_count: i64,
    todos_left: Vec<String>,
    fingerprint: String,
    disposition_required: bool,
    plan_fidelity_forced: bool,
    coverage_file: String,
    untouched_file: String,
    todos_file: String,
}

#[derive(Clone, Debug, PartialEq)]
struct DispositionRecord {
    disposition: String,
    fingerprint: String,
    followup_issue_number: String,
    followup_issue_url: String,
    coverage_file: String,
}

#[derive(Clone, Debug)]
struct ValidationResult {
    ok: bool,
    required: bool,
    reason: String,
    coverage: Option<PlanCoverage>,
}

#[derive(Clone, Debug)]
struct BaselineResolution {
    sha: String,
    frozen_fallback_active: bool,
}

/// Internal provenance for frozen-fallback committed-path attribution.
#[derive(Clone, Debug)]
struct FallbackProvenance {
    session_id: String,
    anchor_head: String,
    path_signatures: BTreeMap<String, String>,
}

fn choices(values: &[&str]) -> String {
    values
        .iter()
        .map(|value| format!("'{value}'"))
        .collect::<Vec<_>>()
        .join(", ")
}

/// Public entry for `implement scope-disposition`.
pub fn scope_disposition(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, &OPTIONS, &["-h", "--help"], 1);
    if parsed.flag("-h") || parsed.flag("--help") {
        println!("{HELP}");
        return ExitCode::SUCCESS;
    }
    if let Some(error) = parsed.value_error() {
        return usage_error(USAGE, PROGRAM, error, 2);
    }
    let Some(action) = parsed
        .positional(0)
        .map(|value| value.to_string_lossy().into_owned())
    else {
        return usage_error(
            USAGE,
            PROGRAM,
            "the following arguments are required: action",
            2,
        );
    };
    if !ACTIONS.contains(&action.as_str()) {
        return usage_error(
            USAGE,
            PROGRAM,
            &format!(
                "argument action: invalid choice: '{action}' (choose from {})",
                choices(&ACTIONS)
            ),
            2,
        );
    }
    if let Some(error) = parsed.error() {
        return usage_error(USAGE, PROGRAM, &error, 2);
    }
    let tmpdir_raw = opt(&parsed, "--tmpdir")
        .or_else(|| env::var("IMPLEMENT_TMPDIR").ok())
        .unwrap_or_default();
    let tmpdir = PathBuf::from(&tmpdir_raw);
    if tmpdir_raw.is_empty() || !tmpdir.is_dir() {
        eprintln!("implement scope-disposition: --tmpdir is required");
        return ExitCode::from(2);
    }
    let repo_root = {
        let raw = opt(&parsed, "--repo-root").unwrap_or_default();
        if raw.is_empty() {
            env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
        } else {
            PathBuf::from(raw)
        }
    };
    let repo_root = fs::canonicalize(&repo_root).unwrap_or(repo_root);
    let manifest = opt_path(&parsed, "--manifest-path");
    let plan_file = opt_path(&parsed, "--plan-file");
    let disposition = opt(&parsed, "--disposition").unwrap_or_else(|| "proceed-partial".to_owned());
    if !DISPOSITIONS.contains(&disposition.as_str()) {
        return usage_error(
            USAGE,
            PROGRAM,
            &format!(
                "argument --disposition: invalid choice: '{disposition}' (choose from {})",
                choices(&DISPOSITIONS)
            ),
            2,
        );
    }
    let request = ScopeRequest {
        action,
        tmpdir,
        repo_root,
        plan_file,
        manifest,
        disposition,
        repo: opt(&parsed, "--repo").unwrap_or_default(),
        tracking_issue: opt(&parsed, "--tracking-issue").unwrap_or_default(),
        run_id: opt(&parsed, "--run-id").unwrap_or_default(),
    };
    match run_action(&request) {
        Ok(code) => code,
        Err(message) => {
            eprintln!("implement scope-disposition: {}", safe_line(&message, 300));
            ExitCode::from(4)
        }
    }
}

/// One validated invocation of `implement scope-disposition`.
struct ScopeRequest {
    action: String,
    tmpdir: PathBuf,
    repo_root: PathBuf,
    plan_file: Option<PathBuf>,
    manifest: Option<PathBuf>,
    disposition: String,
    repo: String,
    tracking_issue: String,
    run_id: String,
}

fn run_action(request: &ScopeRequest) -> Result<ExitCode, String> {
    let tmpdir = request.tmpdir.as_path();
    let repo_root = request.repo_root.as_path();
    let manifest = request.manifest.as_deref();
    match request.action.as_str() {
        "summary-line" => Ok(emit_summary_line(tmpdir, manifest)),
        "compute" => {
            let coverage =
                compute_and_write(tmpdir, repo_root, request.plan_file.as_deref(), manifest)?;
            emit_coverage(&coverage);
            Ok(ExitCode::SUCCESS)
        }
        "record" => {
            let record = record_disposition(
                tmpdir,
                &request.disposition,
                repo_root,
                manifest,
                &request.repo,
                &request.tracking_issue,
                &request.run_id,
            )?;
            emit_kv("SCOPE_DISPOSITION_RECORDED", "true");
            emit_kv("SCOPE_DISPOSITION", &record.disposition);
            if !record.followup_issue_number.is_empty() {
                emit_kv("FOLLOWUP_ISSUE_NUMBER", &record.followup_issue_number);
                emit_kv("FOLLOWUP_ISSUE_URL", &record.followup_issue_url);
            }
            Ok(ExitCode::SUCCESS)
        }
        "render-deferred-inventory" => {
            print!("{}", deferred_inventory(tmpdir, repo_root, manifest)?);
            Ok(ExitCode::SUCCESS)
        }
        "invalidate-if-stale" | "validate-ship" => {
            let result = validate_for_ship(tmpdir, repo_root, manifest)?;
            if request.action == "invalidate-if-stale"
                && result.reason == "scope-disposition-stale"
            {
                let _ = fs::remove_file(tmpdir.join(DISPOSITION_JSON));
            }
            if let Some(coverage) = &result.coverage {
                emit_coverage(coverage);
            }
            emit_kv(
                "SCOPE_DISPOSITION_VALID",
                if result.ok { "true" } else { "false" },
            );
            emit_kv(
                "SCOPE_DISPOSITION_REQUIRED",
                if result.required { "true" } else { "false" },
            );
            if !result.reason.is_empty() {
                emit_kv("SCOPE_DISPOSITION_REASON", &result.reason);
            }
            Ok(if result.ok {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(3)
            })
        }
        other => Err(format!("unknown action {other}")),
    }
}

fn opt(parsed: &ParsedCommandLine, name: &str) -> Option<String> {
    parsed
        .value(name)
        .map(|value| value.to_string_lossy().into_owned())
}

fn opt_path(parsed: &ParsedCommandLine, name: &str) -> Option<PathBuf> {
    opt(parsed, name)
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

fn safe_line(value: &str, limit: usize) -> String {
    let text = value.replace(['\r', '\n'], " ").trim().to_owned();
    if text.chars().count() > limit {
        let mut out: String = text.chars().take(limit.saturating_sub(1)).collect();
        out.push('…');
        out
    } else {
        text
    }
}

fn artifact_present(path: &Path) -> bool {
    path.exists() || path.symlink_metadata().is_ok()
}

fn json_text(value: &Value) -> String {
    let mut text = serde_json::to_string_pretty(value).unwrap_or_else(|_| "{}".to_owned());
    text.push('\n');
    text
}

fn read_trusted_text(path: &Path) -> Result<String, String> {
    read_universal_newlines(path).ok_or_else(|| format!("unreadable: {}", path.display()))
}

fn write_trusted(path: &Path, text: &str, root: &Path) -> Result<(), String> {
    private_atomic_write(path, text, root).map_err(|error| error.to_string())
}

// Continued in part 2 via include — keep helpers below.
include!("implement_scope_disposition_commands_impl.rs");
