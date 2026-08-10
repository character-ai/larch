//! Rust owner for the bounded bug-fix evidence, runtime, and report commands.
//!
//! The commands exchange private JSON artifacts with read-only agents. Everything
//! read from GitHub or an agent-produced JSONL file is data: it is bounded,
//! validated, and never interpreted as a command or prompt.

use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::LazyLock,
    time::Duration,
};

#[cfg(unix)]
use std::os::unix::fs::{OpenOptionsExt as _, PermissionsExt as _};

use chrono::Utc;
use larch_adapters::{GixRepository, unified_blob_diff};
use larch_core::{
    ChangeKind, Commit, ExternalProgram, GitHubIssue, GitHubIssueList, GitHubIssueState,
    GitHubService, GitPath, HostUtilityProgram, PLAN_MARKER, ProcessErrorKind, RepositoryRead,
    Revision, bug_title_match, emit_kv, epoch_now, private_atomic_write, require_enabled_storage,
    strip_named_block,
};
use serde_json::{Map, Value, json};
use sha2::{Digest as _, Sha256};
use uuid::Uuid;

use crate::{
    argparse_compat::{ParsedCommandLine, parse_with_flags, usage_error},
    child_process::{bounded_request_in, run_bounded_detailed},
    github_repository_resolution::{ambient_repo, repository_ref, validate_repo_slug},
    github_service::with_github_service,
};

const PREFETCH_PROGRAM: &str = "python/cli.py analyze-bugs prefetch";
const PREFETCH_USAGE: &str = "usage: python/cli.py analyze-bugs prefetch [-h] [--repo REPO] [-n COUNT]\n                                           [--cache-root CACHE_ROOT]\n                                           [--state-root STATE_ROOT]\n                                           [--batch-size BATCH_SIZE]\n                                           [--diff-cap DIFF_CAP]";
const PREFETCH_HELP: &str = "usage: python/cli.py analyze-bugs prefetch [-h] [--repo REPO] [-n COUNT]\n                                           [--cache-root CACHE_ROOT]\n                                           [--state-root STATE_ROOT]\n                                           [--batch-size BATCH_SIZE]\n                                           [--diff-cap DIFF_CAP]\n\noptions:\n  -h, --help            show this help message and exit\n  --repo REPO\n  -n COUNT, --count COUNT\n  --cache-root CACHE_ROOT\n  --state-root STATE_ROOT\n  --batch-size BATCH_SIZE\n  --diff-cap DIFF_CAP\n";
const LEDGER_PROGRAM: &str = "python/cli.py analyze-bugs ledger";
const LEDGER_USAGE: &str = "usage: python/cli.py analyze-bugs ledger [-h] --run-dir RUN_DIR --ledger-path\n                                         LEDGER_PATH [--manifest MANIFEST]\n                                         [--ingest-triage INGEST_TRIAGE]\n                                         [--ingest-deep INGEST_DEEP]\n                                         [--refresh] [--sample SAMPLE]\n                                         [--deep-max DEEP_MAX]\n                                         [--deep-model DEEP_MODEL]\n                                         [--batch-size BATCH_SIZE]";
const LEDGER_HELP: &str = "usage: python/cli.py analyze-bugs ledger [-h] --run-dir RUN_DIR --ledger-path\n                                         LEDGER_PATH [--manifest MANIFEST]\n                                         [--ingest-triage INGEST_TRIAGE]\n                                         [--ingest-deep INGEST_DEEP]\n                                         [--refresh] [--sample SAMPLE]\n                                         [--deep-max DEEP_MAX]\n                                         [--deep-model DEEP_MODEL]\n                                         [--batch-size BATCH_SIZE]\n\noptions:\n  -h, --help            show this help message and exit\n  --run-dir RUN_DIR\n  --ledger-path LEDGER_PATH\n  --manifest MANIFEST\n  --ingest-triage INGEST_TRIAGE\n  --ingest-deep INGEST_DEEP\n  --refresh\n  --sample SAMPLE\n  --deep-max DEEP_MAX\n  --deep-model DEEP_MODEL\n  --batch-size BATCH_SIZE\n";
const RUNTIME_PROGRAM: &str = "python/cli.py analyze-bugs runtime";
const RUNTIME_USAGE: &str = "usage: python/cli.py analyze-bugs runtime [-h] --run-dir RUN_DIR --manifest\n                                          MANIFEST --ledger-path LEDGER_PATH\n                                          [--runtime-max RUNTIME_MAX]\n                                          --repo-root REPO_ROOT";
const RUNTIME_HELP: &str = "usage: python/cli.py analyze-bugs runtime [-h] --run-dir RUN_DIR --manifest\n                                          MANIFEST --ledger-path LEDGER_PATH\n                                          [--runtime-max RUNTIME_MAX]\n                                          --repo-root REPO_ROOT\n\noptions:\n  -h, --help            show this help message and exit\n  --run-dir RUN_DIR\n  --manifest MANIFEST\n  --ledger-path LEDGER_PATH\n  --runtime-max RUNTIME_MAX\n  --repo-root REPO_ROOT\n";
const REPORT_PROGRAM: &str = "python/cli.py analyze-bugs report";
const REPORT_USAGE: &str = "usage: python/cli.py analyze-bugs report [-h] --run-dir RUN_DIR --manifest\n                                         MANIFEST --ledger-path LEDGER_PATH";
const REPORT_HELP: &str = "usage: python/cli.py analyze-bugs report [-h] --run-dir RUN_DIR --manifest\n                                         MANIFEST --ledger-path LEDGER_PATH\n\noptions:\n  -h, --help            show this help message and exit\n  --run-dir RUN_DIR\n  --manifest MANIFEST\n  --ledger-path LEDGER_PATH\n";

const DEFAULT_COUNT: usize = 200;
const DEFAULT_BATCH_SIZE: usize = 10;
const DEFAULT_DEEP_MAX: i64 = 30;
const DEFAULT_DIFF_CAP: usize = 60_000;
const DEFAULT_BODY_CAP: usize = 8_000;
const MAX_COMMITS: usize = 20_000;
const MAX_HISTORY_COMMITS: usize = 1_000;
const MAX_CONSUMER_FILES: usize = 25_000;
const MAX_CONSUMER_BYTES: usize = 64 * 1024 * 1024;
const MAX_EVIDENCE_BLOB_BYTES: usize = 2 * 1024 * 1024;
const MAX_CONSUMER_REFERENCES: usize = 10_000;
const MAX_CLOSURE_PULL_LOOKUPS: usize = 400;
const CONSUMER_CAP: usize = 40;
const MAX_MANIFEST_BYTES: u64 = 64 * 1024 * 1024;
const MAX_LEDGER_BYTES: u64 = 128 * 1024 * 1024;
const LEGACY_TRIAGE_WARN_LIMIT: usize = 20;
const DEFAULT_RUNTIME_MAX: i64 = 10;
const RUNTIME_TIMEOUT: Duration = Duration::from_secs(300);
const RUNTIME_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
const RUNTIME_OUTPUT_LIMIT: usize = 64 * 1024;
const RUNTIME_EVIDENCE_CAP: usize = 500;
const SCAN_OK: &str = "ok";
const SCAN_FAILED: &str = "failed";
const SCAN_NOT_RUN: &str = "not-run";
const METADATA_VERSION: u64 = 1;
const TRIAGE_VERDICTS: &[&str] = &["FIXED_CLEAR", "FIXED_LIKELY", "SUSPECT", "NEEDS_DEEP"];
const DEEP_VERDICTS: &[&str] = &[
    "CONFIRMED_FIXED",
    "INCOMPLETE",
    "REGRESSED",
    "NOT_FIXED",
    "UNVERIFIABLE",
];

static SIBLING_SITE: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"^[^:\s]+:[A-Za-z_][A-Za-z0-9_]*$")
        .expect("static sibling-site expression compiles")
});
static DIFF_FUNCTION_SYMBOL: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"^[+-]\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
        .expect("static function-symbol expression compiles")
});
static DIFF_FIELD_SYMBOL: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"^[+-]\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*")
        .expect("static field-symbol expression compiles")
});
static DIFF_DICT_SUBSCRIPT_SYMBOL: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r#"\[\s*['\"]([A-Za-z_][A-Za-z0-9_-]*)['\"]\s*\]"#)
        .expect("static dict-subscript expression compiles")
});
static DIFF_DICT_LITERAL_SYMBOL: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r#"(?:^|[,{]\s*)['\"]([A-Za-z_][A-Za-z0-9_-]*)['\"]\s*:"#)
        .expect("static dict-literal expression compiles")
});
static MARKER_PHRASE: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"(?i)(?:incomplete|persists\s+after|residual|regression\s+from|after\s+the)")
        .expect("static marker-phrase expression compiles")
});
static ISSUE_REFERENCE: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"#([1-9][0-9]*)").expect("static issue-reference expression compiles")
});

#[cfg(test)]
thread_local! {
    static SWEEP_REPOSITORY_ROOT: std::cell::RefCell<Option<PathBuf>> =
        const { std::cell::RefCell::new(None) };
}

/// Fetch bounded bug evidence and private hand-off bundles.
#[must_use]
#[allow(clippy::too_many_lines)] // The ordered artifact hand-off is one compatibility transaction.
pub fn prefetch(arguments: &[OsString]) -> ExitCode {
    prefetch_with_evidence(arguments, evidence_repository)
}

#[allow(clippy::too_many_lines)] // The ordered artifact hand-off is one compatibility transaction.
fn prefetch_with_evidence(
    arguments: &[OsString],
    load_evidence: impl FnOnce() -> Result<EvidenceRepository, String>,
) -> ExitCode {
    const OPTIONS: &[&str] = &[
        "--repo",
        "--count",
        "--cache-root",
        "--state-root",
        "--batch-size",
        "--diff-cap",
    ];
    let arguments = normalize_count_short_flag(arguments);
    let help = help_position(&arguments);
    let parsed = parse_with_flags(
        &arguments[..help.unwrap_or(arguments.len())],
        OPTIONS,
        &[],
        0,
    );
    if let Some(error) = parsed.value_error() {
        return usage_error(PREFETCH_USAGE, PREFETCH_PROGRAM, error, 2);
    }
    if help.is_some() {
        print!("{PREFETCH_HELP}");
        return ExitCode::SUCCESS;
    }
    if let Some(error) = parsed.error() {
        return usage_error(PREFETCH_USAGE, PREFETCH_PROGRAM, &error, 2);
    }
    let count = match positive_option(
        &parsed,
        "--count",
        DEFAULT_COUNT,
        PREFETCH_USAGE,
        PREFETCH_PROGRAM,
    ) {
        Ok(value) => value,
        Err(code) => return code,
    };
    let batch_size = match positive_option(
        &parsed,
        "--batch-size",
        DEFAULT_BATCH_SIZE,
        PREFETCH_USAGE,
        PREFETCH_PROGRAM,
    ) {
        Ok(value) => value,
        Err(code) => return code,
    };
    let diff_cap = match positive_option(
        &parsed,
        "--diff-cap",
        DEFAULT_DIFF_CAP,
        PREFETCH_USAGE,
        PREFETCH_PROGRAM,
    ) {
        Ok(value) => value,
        Err(code) => return code,
    };
    let repo = option_text(&parsed, "--repo");
    let repo = if repo.is_empty() {
        ambient_repo().unwrap_or_default()
    } else {
        repo
    };
    if !validate_repo_slug(&repo) || repository_ref(&repo).is_err() {
        eprintln!("ERROR: could not resolve GitHub repo; pass --repo OWNER/REPO");
        return ExitCode::FAILURE;
    }
    let cache_root = option_path_or(&parsed, "--cache-root", &default_cache_root());
    let state_root = match state_root(&parsed, &repo) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("ERROR: {error}");
            return ExitCode::FAILURE;
        }
    };
    let evidence = match load_evidence() {
        Ok(evidence) => evidence,
        Err(error) => {
            eprintln!("ERROR: {error}");
            return ExitCode::FAILURE;
        }
    };
    let Ok(reference) = repository_ref(&repo) else {
        unreachable!("validated repository slug has a repository reference");
    };
    let fetched = with_github_service(async |service, cancellation| {
        let request = GitHubIssueList {
            repo: reference.clone(),
            state: GitHubIssueState::All,
            labels: Vec::new(),
            // Scan a bounded recent corpus rather than only `count` newest
            // issues: most repositories interleave non-bug work with `[BUG]`
            // rows.  Staying below the transport ceiling leaves room for the
            // REST endpoint's pull-request rows, which the typed service
            // correctly filters out.
            limit: count
                .saturating_mul(5)
                .clamp(100, 1_000)
                .min(service.transport_policy().limits().items()),
        };
        let issues = service
            .list_issues(&request, cancellation)
            .await
            .map_err(|error| error.to_string())?;
        Ok::<_, String>(issues)
    });
    let issues = match fetched {
        Ok(value) => value,
        Err(error) => {
            eprintln!("ERROR: gh issue list failed: {}", error.into_detail());
            return ExitCode::FAILURE;
        }
    };
    let selected: Vec<GitHubIssue> = issues
        .into_iter()
        .filter(|issue| !issue.is_pull_request && bug_title_match(&issue.title))
        .take(count)
        .collect();
    let wanted: BTreeSet<u64> = selected.iter().map(|issue| issue.number).collect();
    let closure_data = with_github_service(async |service, cancellation| {
        let closures = service
            .issue_closure_references(cancellation, reference.owner(), reference.name(), &wanted)
            .await
            .map_err(|error| error.to_string())?;
        let mut merge_commits = BTreeMap::new();
        let mut pull_lookups = 0usize;
        for (issue, references) in &closures {
            let numbers = closure_pull_numbers(references);
            if pull_lookups.saturating_add(numbers.len()) > MAX_CLOSURE_PULL_LOOKUPS {
                continue;
            }
            pull_lookups += numbers.len();
            let mut commits = BTreeSet::new();
            for number in numbers {
                let Ok(pull) = service
                    .get_pull_request(cancellation, reference.owner(), reference.name(), number)
                    .await
                else {
                    continue;
                };
                if pull.merged()
                    && let Some(oid) = pull.merge_commit_oid()
                {
                    commits.insert(oid.to_owned());
                }
            }
            if !commits.is_empty() {
                merge_commits.insert(*issue, commits);
            }
        }
        Ok::<_, String>((closures, merge_commits))
    })
    .unwrap_or_default();
    let run_dir = match create_run_dir(&cache_root, &repo) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("ERROR: {error}");
            return ExitCode::FAILURE;
        }
    };
    if let Err(error) = private_dir(&run_dir) {
        eprintln!("ERROR: {error}");
        return ExitCode::FAILURE;
    }
    let evidence_ref = evidence.reference.clone();
    let rows: Result<Vec<Value>, String> = selected
        .iter()
        .map(|issue| {
            bundle_for_issue(
                issue,
                closure_data
                    .0
                    .get(&issue.number)
                    .map(Vec::as_slice)
                    .unwrap_or_default(),
                closure_data.1.get(&issue.number),
                &evidence,
                &run_dir,
                diff_cap,
            )
        })
        .collect();
    let rows = match rows {
        Ok(rows) => rows,
        Err(error) => {
            eprintln!("ERROR: {error}");
            return ExitCode::FAILURE;
        }
    };
    let deep_queue_path = run_dir.join("deep-queue.jsonl");
    if let Err(error) = private_write(&deep_queue_path, "") {
        eprintln!("ERROR: {error}");
        return ExitCode::FAILURE;
    }
    let triage_paths = match write_initial_batches(&run_dir, &rows, batch_size) {
        Ok(paths) => paths,
        Err(error) => {
            eprintln!("ERROR: {error}");
            return ExitCode::FAILURE;
        }
    };
    let ledger_path = state_root
        .join("analyze-bugs")
        .join(sanitize_repo(&repo))
        .join("ledger.jsonl");
    let manifest_path = run_dir.join("manifest.json");
    let manifest = json!({
        "schema_version": "1",
        "repo": repo,
        "run_id": run_dir.file_name().and_then(|value| value.to_str()).unwrap_or_default(),
        "run_dir": run_dir,
        "evidence_ref": evidence_ref,
        "bugs_requested": count,
        "bugs_selected": rows.len(),
        "generated_at": epoch_now(),
        "ledger_path": ledger_path,
        "triage_batch_paths": triage_paths,
        "deep_queue_path": deep_queue_path,
        "issues": rows,
    });
    if let Err(error) = write_json(&manifest_path, &manifest) {
        eprintln!("ERROR: {error}");
        return ExitCode::FAILURE;
    }
    emit_kv("EVIDENCE_REF", &evidence.reference);
    emit_kv("BUGS_REQUESTED", &count.to_string());
    emit_kv("BUGS_SELECTED", &rows.len().to_string());
    emit_path("RUN_DIR", &run_dir);
    emit_path("MANIFEST_PATH", &manifest_path);
    emit_path("LEDGER_PATH", &ledger_path);
    emit_kv("TRIAGE_BATCH_PATHS", &join_paths(&triage_paths));
    emit_path("DEEP_QUEUE_PATH", &deep_queue_path);
    ExitCode::SUCCESS
}

/// Reconcile or ingest the append-only per-bug verification ledger.
#[must_use]
#[allow(clippy::too_many_lines)] // Parsing and dispatch preserve the Python compatibility boundary.
pub fn ledger(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &[
        "--run-dir",
        "--ledger-path",
        "--manifest",
        "--ingest-triage",
        "--ingest-deep",
        "--sample",
        "--deep-max",
        "--deep-model",
        "--batch-size",
    ];
    const FLAGS: &[&str] = &["--refresh"];
    // Keep the Python `argparse` help boundary: flags after help are ignored,
    // but do not duplicate the generic analysis-command parser preamble.
    let help_at = help_position(arguments);
    let parsed = parse_with_flags(
        &arguments[..help_at.unwrap_or(arguments.len())],
        OPTIONS,
        FLAGS,
        0,
    );
    if let Some(error) = parsed.value_error() {
        return usage_error(LEDGER_USAGE, LEDGER_PROGRAM, error, 2);
    }
    if help_at.is_some() {
        print!("{LEDGER_HELP}");
        return ExitCode::SUCCESS;
    }
    let missing: Vec<&str> = ["--run-dir", "--ledger-path"]
        .into_iter()
        .filter(|name| parsed.value(name).is_none())
        .collect();
    if !missing.is_empty() {
        return usage_error(
            LEDGER_USAGE,
            LEDGER_PROGRAM,
            &format!(
                "the following arguments are required: {}",
                missing.join(", ")
            ),
            2,
        );
    }
    if let Some(error) = parsed.error() {
        return usage_error(LEDGER_USAGE, LEDGER_PROGRAM, &error, 2);
    }
    let run_dir = PathBuf::from(option_text(&parsed, "--run-dir"));
    let ledger_path = PathBuf::from(option_text(&parsed, "--ledger-path"));
    let manifest_path = nonempty_option(&parsed, "--manifest")
        .map_or_else(|| run_dir.join("manifest.json"), PathBuf::from);
    let triage_path = nonempty_option(&parsed, "--ingest-triage").map(PathBuf::from);
    let deep_path = nonempty_option(&parsed, "--ingest-deep").map(PathBuf::from);
    if triage_path.is_some() && deep_path.is_some() {
        eprintln!("ERROR: pass only one of --ingest-triage or --ingest-deep");
        return ExitCode::FAILURE;
    }
    let result = if let Some(path) = triage_path {
        ingest(&run_dir, &ledger_path, &manifest_path, &path, "triage")
    } else if let Some(path) = deep_path {
        ingest(&run_dir, &ledger_path, &manifest_path, &path, "deep")
    } else {
        let sample = match signed_option(&parsed, "--sample", 3, LEDGER_USAGE, LEDGER_PROGRAM) {
            Ok(value) => nonnegative_usize(value),
            Err(code) => return code,
        };
        let deep_max = match signed_option(
            &parsed,
            "--deep-max",
            DEFAULT_DEEP_MAX,
            LEDGER_USAGE,
            LEDGER_PROGRAM,
        ) {
            Ok(value) => nonnegative_usize(value),
            Err(code) => return code,
        };
        let batch_size = match signed_option(
            &parsed,
            "--batch-size",
            i64::try_from(DEFAULT_BATCH_SIZE).expect("small compatibility default"),
            LEDGER_USAGE,
            LEDGER_PROGRAM,
        ) {
            Ok(value) => nonnegative_usize(value).max(1),
            Err(code) => return code,
        };
        let model = option_text_or(&parsed, "--deep-model", "sonnet");
        compute(
            &run_dir,
            &ledger_path,
            &manifest_path,
            parsed.flag("--refresh"),
            sample,
            deep_max,
            &model,
            batch_size,
        )
    };
    match result {
        Ok(payload) => {
            emit_ledger_payload(&payload);
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("ERROR: {error}");
            ExitCode::FAILURE
        }
    }
}

struct EvidenceRepository {
    repository: GixRepository,
    reference: String,
    tip: larch_core::ObjectId,
    commits: Vec<Commit>,
    messages: BTreeMap<String, String>,
}

#[derive(Default)]
struct EvidenceScan {
    status: &'static str,
    output: String,
    reason: String,
}

impl EvidenceScan {
    const fn complete(output: String) -> Self {
        Self {
            status: SCAN_OK,
            output,
            reason: String::new(),
        }
    }

    fn failed(reason: impl Into<String>) -> Self {
        Self {
            status: SCAN_FAILED,
            output: String::new(),
            reason: reason.into(),
        }
    }

    fn not_run(reason: impl Into<String>) -> Self {
        Self {
            status: SCAN_NOT_RUN,
            output: String::new(),
            reason: reason.into(),
        }
    }
}

struct FixEvidence {
    sha: String,
    source: &'static str,
    reason: String,
    commit: Option<Commit>,
    fix_time: i64,
    touched_files: Vec<String>,
    added_lines: u64,
}

struct BundleScans {
    diff: EvidenceScan,
    consumers: EvidenceScan,
    later: EvidenceScan,
    revert: EvidenceScan,
    changed_symbols: Vec<String>,
    consumer_paths: Vec<String>,
    consumer_references: Vec<String>,
    consumers_truncated: bool,
    scan_files: Vec<String>,
}

fn evidence_repository() -> Result<EvidenceRepository, String> {
    let cwd = env::current_dir()
        .map_err(|_| "could not resolve evidence ref from origin/main or local main".to_owned())?;
    let refreshed = crate::admission_commands::fetch_origin_main(&cwd);
    let repository = GixRepository::discover(&cwd)
        .map_err(|_| "could not resolve evidence ref from origin/main or local main".to_owned())?;
    let origin = repository.resolve_revision(&Revision::new(b"origin/main"));
    if refreshed && let Ok(tip) = origin {
        return hydrate_evidence(repository, "origin/main".to_owned(), tip);
    }
    let local = repository.resolve_revision(&Revision::new(b"main"));
    if let Ok(tip) = local {
        eprintln!(
            "WARN: using local main as evidence ref because origin/main could not be refreshed"
        );
        return hydrate_evidence(repository, "main".to_owned(), tip);
    }
    Err("could not resolve evidence ref from origin/main or local main".to_owned())
}

fn hydrate_evidence(
    repository: GixRepository,
    reference: String,
    tip: larch_core::ObjectId,
) -> Result<EvidenceRepository, String> {
    let commits = repository
        .walk_commits(&tip, MAX_COMMITS)
        .map_err(|_| "could not inspect synced main evidence".to_owned())?;
    let mut messages = BTreeMap::new();
    for commit in &commits {
        let message = repository
            .object(&commit.id)
            .map_err(|_| "could not inspect synced main evidence".to_owned())?
            .map(|object| String::from_utf8_lossy(&object.data).into_owned())
            .unwrap_or_default();
        messages.insert(commit.id.to_hex(), message);
    }
    Ok(EvidenceRepository {
        repository,
        reference,
        tip,
        commits,
        messages,
    })
}

fn bundle_for_issue(
    issue: &GitHubIssue,
    closure_references: &[String],
    closure_merge_commits: Option<&BTreeSet<String>>,
    evidence: &EvidenceRepository,
    run_dir: &Path,
    diff_cap: usize,
) -> Result<Value, String> {
    let (stripped_body, malformed) = match strip_named_block(&issue.body, PLAN_MARKER) {
        Ok(body) => (body, String::new()),
        Err(defect) => (
            String::new(),
            format!("malformed larch:plan block: {defect}"),
        ),
    };
    let mut fix = find_fix(issue.number, closure_merge_commits, evidence)?;
    let (mut mechanical, mut reason) = if issue_state(issue.state) == "OPEN" {
        ("NOT_FIXED".to_owned(), "issue is still open".to_owned())
    } else if issue.state_reason.eq_ignore_ascii_case("NOT_PLANNED") {
        (
            "WONTFIX".to_owned(),
            "issue was closed as not planned".to_owned(),
        )
    } else if !malformed.is_empty() {
        ("NEEDS_DEEP".to_owned(), malformed)
    } else if fix.sha.is_empty() {
        ("NEEDS_DEEP".to_owned(), fix.reason.clone())
    } else {
        (String::new(), String::new())
    };
    let scans = scans_for_fix(&fix, evidence, diff_cap);
    fix.added_lines = added_line_count(&scans.diff.output);
    if !fix.sha.is_empty()
        && [
            ("fix-diff", &scans.diff),
            ("consumer", &scans.consumers),
            ("later-history", &scans.later),
            ("revert", &scans.revert),
        ]
        .into_iter()
        .any(|(_, scan)| scan.status != SCAN_OK)
    {
        let incomplete = incomplete_evidence_reason(&[
            ("fix-diff", &scans.diff),
            ("consumer", &scans.consumers),
            ("later-history", &scans.later),
            ("revert", &scans.revert),
        ]);
        mechanical.clear();
        mechanical.push_str("NEEDS_DEEP");
        reason = if reason.is_empty() {
            incomplete
        } else {
            format!("{reason}; {incomplete}")
        };
    }
    bundle_with_mechanical(
        issue,
        closure_references,
        run_dir,
        &stripped_body,
        &fix,
        &mechanical,
        &reason,
        &scans,
        &evidence.reference,
        diff_cap,
    )
}

#[allow(clippy::too_many_lines)] // The fallback chain is kept in discovery order for evidence parity.
fn find_fix(
    issue: u64,
    closure_merge_commits: Option<&BTreeSet<String>>,
    evidence: &EvidenceRepository,
) -> Result<FixEvidence, String> {
    let wanted = format!("fixes #{issue}");
    let mut found = None;
    for commit in &evidence.commits {
        let full = evidence
            .messages
            .get(&commit.id.to_hex())
            .map(String::as_str)
            .unwrap_or_default();
        if full.to_ascii_lowercase().contains(&wanted) && has_exact_issue_reference(full, issue) {
            found = Some(commit.clone());
            break;
        }
    }
    let mut source = "git-log";
    if found.is_none() {
        match closure_merge_commits.map_or(0, BTreeSet::len) {
            0 => {}
            1 => {
                let oid = closure_merge_commits
                    .and_then(|commits| commits.first())
                    .expect("one closure merge commit has one oid");
                if let Some(commit) = evidence
                    .commits
                    .iter()
                    .find(|commit| commit.id.to_hex() == *oid)
                {
                    found = Some(commit.clone());
                    source = "closedByPullRequestsReferences";
                }
            }
            _ => {
                return Ok(FixEvidence {
                    sha: String::new(),
                    source: "closedByPullRequestsReferences",
                    reason: "multiple PR merge commits".to_owned(),
                    commit: None,
                    fix_time: 0,
                    touched_files: Vec::new(),
                    added_lines: 0,
                });
            }
        }
    }
    let Some(commit) = found else {
        return Ok(FixEvidence {
            sha: String::new(),
            source: "git-log",
            reason: "no exact Fixes reference".to_owned(),
            commit: None,
            fix_time: 0,
            touched_files: Vec::new(),
            added_lines: 0,
        });
    };
    let mut touched_files = if let Some(parent_id) = commit.parents.first() {
        if let Some(parent) = evidence
            .commits
            .iter()
            .find(|candidate| candidate.id == *parent_id)
        {
            let changes = evidence
                .repository
                .tree_changes(&parent.tree, &commit.tree)
                .map_err(|_| "could not inspect synced main fix files".to_owned())?;
            changes
                .entries()
                .iter()
                .filter(|change| {
                    change
                        .new_mode
                        .or(change.old_mode)
                        .is_some_and(|mode| blob_or_link_mode(mode.raw()))
                })
                .map(|change| repository_path_text(&change.path))
                .collect::<Result<Vec<_>, _>>()?
        } else {
            // `fix_diff` reports this shallow-history condition as failed
            // evidence rather than treating it as an empty file set.
            Vec::new()
        }
    } else {
        evidence
            .repository
            .files_at_commit(&commit.id, MAX_CONSUMER_FILES)
            .map_err(|_| "could not inspect synced main fix files".to_owned())?
            .iter()
            .map(repository_path_text)
            .collect::<Result<Vec<_>, _>>()?
    };
    touched_files.sort();
    touched_files.dedup();
    let full = evidence
        .repository
        .object(&commit.id)
        .ok()
        .flatten()
        .map(|object| object.data)
        .unwrap_or_default();
    Ok(FixEvidence {
        sha: commit.id.to_hex(),
        source,
        reason: String::new(),
        commit: Some(commit),
        fix_time: commit_timestamp(&full),
        touched_files,
        added_lines: 0,
    })
}

fn closure_pull_numbers(references: &[String]) -> BTreeSet<u64> {
    references
        .iter()
        .filter_map(|reference| {
            reference
                .trim_end_matches('/')
                .rsplit_once("/pull/")
                .and_then(|(_, number)| number.parse::<u64>().ok())
                .filter(|number| *number > 0)
        })
        .collect()
}

#[allow(clippy::too_many_arguments, clippy::too_many_lines)] // The serialized bundle schema remains adjacent to its evidence inputs.
fn bundle_with_mechanical(
    issue: &GitHubIssue,
    closure_references: &[String],
    run_dir: &Path,
    stripped_body: &str,
    fix: &FixEvidence,
    mechanical: &str,
    reason: &str,
    scans: &BundleScans,
    evidence_ref: &str,
    diff_cap: usize,
) -> Result<Value, String> {
    let token = Uuid::new_v4().simple().to_string();
    let body_path = run_dir.join(format!("issue-{}-body.md", issue.number));
    let bundle_path = run_dir.join(format!("issue-{}-bundle.md", issue.number));
    let later_hash = later_history_hash(fix, evidence_ref, scans);
    let cache_key = digest_text(&format!(
        "{}\0{}\0{}\0{}\0{}",
        issue.number,
        fix.sha,
        later_hash,
        issue_state(issue.state),
        issue.state_reason.trim().to_ascii_uppercase()
    ));
    private_write(&body_path, &cap_text(stripped_body, DEFAULT_BODY_CAP))?;
    let rendered_touched_files = if fix.touched_files.is_empty() {
        "(none)".to_owned()
    } else {
        fix.touched_files.join("\n")
    };
    let (marker_references, marker_fingerprint) = marker_evidence(&issue.title, stripped_body);
    let zones = zones_for_files(&fix.touched_files);
    let baseline_extended = fix.touched_files.iter().any(|path| is_baseline_path(path));
    let state = format!("{} {}", issue_state(issue.state), issue.state_reason)
        .trim_end()
        .to_owned();
    let bundle = format!(
        "# Bug #{}: {}\nevidence_token: {token}\n\nURL: {}\nState: {}\nFix SHA: {}\nFix source: {}\nMechanical verdict: {}\nMechanical reason: {reason}\n\n## Stripped issue body\n{}\n\n## Touched files\n{}\n\n## Changed symbols\n{}\n\n## Consumers of changed symbols\nStatus: {}\n{}{}\n\n## Later commits touching evidence files\nStatus: {}\n{}{}\n\n## Revert scan\nStatus: {}\n{}{}\n\n## Capped fix diff\nStatus: {}\n{}{}\n",
        issue.number,
        issue.title,
        issue.url,
        state,
        if fix.sha.is_empty() {
            "(none)"
        } else {
            &fix.sha
        },
        fix.source,
        if mechanical.is_empty() {
            "(requires triage)"
        } else {
            mechanical
        },
        cap_text(stripped_body, DEFAULT_BODY_CAP),
        rendered_touched_files,
        display_or_none(&scans.changed_symbols),
        scans.consumers.status,
        scan_failure_line(&scans.consumers),
        if scans.consumers.status == SCAN_OK && scans.consumers.output.is_empty() {
            if scans.consumers_truncated {
                format!("Notice: consumers truncated to {CONSUMER_CAP} paths\n")
            } else {
                "(none)\n".to_owned()
            }
        } else {
            render_consumers(scans)
        },
        scans.later.status,
        scan_failure_line(&scans.later),
        display_scan_output(&scans.later),
        scans.revert.status,
        scan_failure_line(&scans.revert),
        display_scan_output(&scans.revert),
        scans.diff.status,
        scan_failure_line(&scans.diff),
        cap_text(&display_scan_output(&scans.diff), diff_cap),
    );
    private_write(&bundle_path, &bundle)?;
    Ok(json!({
        "issue_number": issue.number,
        "title": issue.title,
        "state": issue_state(issue.state),
        "state_reason": issue.state_reason,
        "url": issue.url,
        "body_path": body_path,
        "bundle_path": bundle_path,
        "fix_sha": fix.sha,
        "fix_source": fix.source,
        "linked_changes": closure_references,
        "touched_files": fix.touched_files,
        "later_history_hash": later_hash,
        "mechanical_verdict": mechanical,
        "mechanical_reason": reason,
        "cache_key": cache_key,
        "sampled": false,
        "fix_time": fix.fix_time,
        "added_lines": fix.added_lines,
        "marker_references": marker_references,
        "marker_fingerprint": marker_fingerprint,
        "zones": zones,
        "baseline_extended": baseline_extended,
        "changed_symbols": scans.changed_symbols,
        "consumer_paths": scans.consumer_paths,
        "consumer_references": scans.consumer_references,
        "consumers_truncated": scans.consumers_truncated,
        "scan_files": scans.scan_files,
        "diff_scan_status": scans.diff.status,
        "diff_scan_reason": scans.diff.reason,
        "consumer_scan_status": scans.consumers.status,
        "consumer_scan_reason": scans.consumers.reason,
        "later_history_scan_status": scans.later.status,
        "later_history_scan_reason": scans.later.reason,
        "revert_scan_status": scans.revert.status,
        "revert_scan_reason": scans.revert.reason,
    }))
}

fn scans_for_fix(fix: &FixEvidence, evidence: &EvidenceRepository, diff_cap: usize) -> BundleScans {
    if fix.sha.is_empty() {
        return BundleScans {
            diff: EvidenceScan::not_run("fix SHA is unavailable"),
            consumers: EvidenceScan::not_run("fix SHA is unavailable"),
            later: EvidenceScan::not_run("fix SHA is unavailable"),
            revert: EvidenceScan::not_run("fix SHA is unavailable"),
            changed_symbols: Vec::new(),
            consumer_paths: Vec::new(),
            consumer_references: Vec::new(),
            consumers_truncated: false,
            scan_files: Vec::new(),
        };
    }
    let diff = fix_diff(fix, evidence, diff_cap);
    let changed_symbols = if diff.status == SCAN_OK {
        changed_symbols(&diff.output)
    } else {
        Vec::new()
    };
    let (consumers, consumer_paths, consumer_references, consumers_truncated) =
        if diff.status == SCAN_OK {
            find_consumers(evidence, &changed_symbols, &fix.touched_files)
        } else {
            (
                EvidenceScan::failed("consumer scan skipped because fix-diff scan failed"),
                Vec::new(),
                Vec::new(),
                false,
            )
        };
    let mut scan_files = fix.touched_files.clone();
    scan_files.extend(consumer_paths.iter().cloned());
    scan_files.sort();
    scan_files.dedup();
    let later = history_scan(fix, evidence, &scan_files, false);
    let revert = history_scan(fix, evidence, &scan_files, true);
    BundleScans {
        diff,
        consumers,
        later,
        revert,
        changed_symbols,
        consumer_paths,
        consumer_references,
        consumers_truncated,
        scan_files,
    }
}

fn fix_diff(fix: &FixEvidence, evidence: &EvidenceRepository, cap: usize) -> EvidenceScan {
    let Some(commit) = &fix.commit else {
        return EvidenceScan::not_run("fix SHA is unavailable");
    };
    let parent = commit.parents.first();
    if parent.is_some()
        && !evidence
            .commits
            .iter()
            .any(|candidate| Some(&candidate.id) == parent)
    {
        return EvidenceScan::failed("fix-diff scan could not resolve the first parent");
    }
    let mut output = String::new();
    for path in &fix.touched_files {
        let git_path = GitPath::new(path.as_bytes().to_vec());
        let before = parent.map_or_else(
            || Ok(Vec::new()),
            |id| {
                evidence
                    .repository
                    .blob_at_commit(id, &git_path)
                    .map_err(|_| "fix-diff scan could not read the parent blob".to_owned())
                    .and_then(|blob| blob.map_or(Ok(Vec::new()), Ok))
            },
        );
        let after = evidence
            .repository
            .blob_at_commit(&commit.id, &git_path)
            .map_err(|_| "fix-diff scan could not read the fix blob".to_owned())
            .and_then(|blob| blob.map_or(Ok(Vec::new()), Ok));
        let before = match before {
            Ok(value) => value,
            Err(error) => return EvidenceScan::failed(error),
        };
        let after = match after {
            Ok(value) => value,
            Err(error) => return EvidenceScan::failed(error),
        };
        if before.len() > MAX_EVIDENCE_BLOB_BYTES || after.len() > MAX_EVIDENCE_BLOB_BYTES {
            return EvidenceScan::failed(format!(
                "fix-diff scan exceeded {MAX_EVIDENCE_BLOB_BYTES}-byte blob bound"
            ));
        }
        let header = format!("diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n");
        if !append_with_cap(&mut output, &header, cap) {
            return EvidenceScan::failed(format!("fix-diff scan exceeded {cap} bytes"));
        }
        let Ok(patch) = unified_blob_diff(&before, &after) else {
            return EvidenceScan::failed("fix-diff scan could not render a unified diff");
        };
        if !append_with_cap(&mut output, &patch, cap) {
            return EvidenceScan::failed(format!("fix-diff scan exceeded {cap} bytes"));
        }
    }
    EvidenceScan::complete(output)
}

#[allow(clippy::too_many_lines)] // The bounded scan keeps each fail-closed exit beside its resource check.
fn find_consumers(
    evidence: &EvidenceRepository,
    symbols: &[String],
    touched_files: &[String],
) -> (EvidenceScan, Vec<String>, Vec<String>, bool) {
    if symbols.is_empty() {
        return (
            EvidenceScan::complete(String::new()),
            Vec::new(),
            Vec::new(),
            false,
        );
    }
    let Ok(files) = evidence
        .repository
        .files_at_commit(&evidence.tip, MAX_CONSUMER_FILES)
    else {
        return (
            EvidenceScan::failed(format!(
                "consumer scan exceeded {MAX_CONSUMER_FILES} files or could not enumerate synced main"
            )),
            Vec::new(),
            Vec::new(),
            false,
        );
    };
    let touched: BTreeSet<&str> = touched_files.iter().map(String::as_str).collect();
    let mut bytes_read = 0usize;
    let mut references = BTreeSet::new();
    for path in files {
        let Ok(path_text) = repository_path_text(&path) else {
            return (
                EvidenceScan::failed("consumer scan encountered a path with a line break"),
                Vec::new(),
                Vec::new(),
                false,
            );
        };
        if touched.contains(path_text.as_str()) || excluded_consumer_path(&path_text) {
            continue;
        }
        let bytes = match evidence.repository.blob_at_commit(&evidence.tip, &path) {
            Ok(Some(bytes)) => bytes,
            Ok(None) => continue,
            Err(_) => {
                return (
                    EvidenceScan::failed("consumer scan could not read a synced-main blob"),
                    Vec::new(),
                    Vec::new(),
                    false,
                );
            }
        };
        if bytes.len() > MAX_EVIDENCE_BLOB_BYTES
            || bytes_read.saturating_add(bytes.len()) > MAX_CONSUMER_BYTES
        {
            return (
                EvidenceScan::failed(format!(
                    "consumer scan exceeded its {MAX_CONSUMER_BYTES}-byte evidence bound"
                )),
                Vec::new(),
                Vec::new(),
                false,
            );
        }
        bytes_read += bytes.len();
        if bytes.contains(&0) {
            continue;
        }
        let Ok(text) = std::str::from_utf8(&bytes) else {
            continue;
        };
        for (line_number, line) in text.lines().enumerate() {
            for symbol in symbols {
                if line.contains(symbol) {
                    references.insert((path_text.clone(), line_number + 1, symbol.clone()));
                    if references.len() > MAX_CONSUMER_REFERENCES {
                        return (
                            EvidenceScan::failed(format!(
                                "consumer scan exceeded its {MAX_CONSUMER_REFERENCES}-reference bound"
                            )),
                            Vec::new(),
                            Vec::new(),
                            false,
                        );
                    }
                }
            }
        }
    }
    let all_paths: Vec<String> = references
        .iter()
        .map(|(path, _, _)| path.clone())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    let consumer_paths = all_paths
        .iter()
        .take(CONSUMER_CAP)
        .cloned()
        .collect::<Vec<_>>();
    let retained: BTreeSet<&str> = consumer_paths.iter().map(String::as_str).collect();
    let consumer_references = references
        .into_iter()
        .filter(|(path, _, _)| retained.contains(path.as_str()))
        .map(|(path, line, symbol)| {
            format!(
                "{path}:{line}: `{symbol}`{}",
                if cross_language_consumer(&path) {
                    " [cross-language]"
                } else {
                    ""
                }
            )
        })
        .collect::<Vec<_>>();
    let output = consumer_references.join("\n");
    (
        EvidenceScan::complete(output),
        consumer_paths,
        consumer_references,
        all_paths.len() > CONSUMER_CAP,
    )
}

fn history_scan(
    fix: &FixEvidence,
    evidence: &EvidenceRepository,
    files: &[String],
    revert_only: bool,
) -> EvidenceScan {
    let Some(commit) = &fix.commit else {
        return EvidenceScan::not_run("fix SHA is unavailable");
    };
    if files.is_empty() {
        return EvidenceScan::complete(String::new());
    }
    let later = match evidence.repository.walk_commits_range(
        &commit.id,
        &evidence.tip,
        MAX_HISTORY_COMMITS + 1,
    ) {
        Ok(commits) if commits.len() <= MAX_HISTORY_COMMITS => commits,
        Ok(_) => {
            return EvidenceScan::failed(format!(
                "{} scan exceeded {MAX_HISTORY_COMMITS} commits",
                if revert_only {
                    "revert"
                } else {
                    "later-history"
                }
            ));
        }
        Err(_) => {
            return EvidenceScan::failed(format!(
                "{} scan could not inspect synced main history",
                if revert_only {
                    "revert"
                } else {
                    "later-history"
                }
            ));
        }
    };
    let all: BTreeMap<String, &Commit> = evidence
        .commits
        .iter()
        .map(|candidate| (candidate.id.to_hex(), candidate))
        .collect();
    let wanted: BTreeSet<&str> = files.iter().map(String::as_str).collect();
    let mut rows = Vec::new();
    for candidate in later {
        let Some(parent) = candidate.parents.first() else {
            continue;
        };
        let Some(parent) = all.get(&parent.to_hex()) else {
            return EvidenceScan::failed("history scan could not resolve a first parent");
        };
        let Ok(changes) = evidence
            .repository
            .tree_changes(&parent.tree, &candidate.tree)
        else {
            return EvidenceScan::failed("history scan could not compare commit trees");
        };
        let relevant = changes.paths().try_fold(false, |_, path| {
            repository_path_text(path).map(|path| wanted.contains(path.as_str()))
        });
        let Ok(relevant) = relevant else {
            return EvidenceScan::failed("history scan encountered a path with a line break");
        };
        if !relevant {
            continue;
        }
        if revert_only {
            let message = match evidence.repository.object(&candidate.id) {
                Ok(Some(object)) => String::from_utf8_lossy(&object.data).to_ascii_lowercase(),
                _ => return EvidenceScan::failed("revert scan could not inspect a commit message"),
            };
            if !message.contains("revert") {
                continue;
            }
        }
        let subject = inline_text(&String::from_utf8_lossy(&candidate.subject));
        rows.push(format!("{}:{subject}", candidate.id.to_hex()));
    }
    EvidenceScan::complete(if rows.is_empty() {
        String::new()
    } else {
        format!("{}\n", rows.join("\n"))
    })
}

fn changed_symbols(diff: &str) -> Vec<String> {
    let mut symbols = BTreeSet::new();
    for line in diff.lines() {
        if !line.starts_with(['+', '-']) || line.starts_with("+++") || line.starts_with("---") {
            continue;
        }
        if let Some(found) = DIFF_FUNCTION_SYMBOL
            .captures(line)
            .and_then(|found| found.get(1))
        {
            symbols.insert(found.as_str().to_owned());
        }
        if let Some(captures) = DIFF_FIELD_SYMBOL.captures(line)
            && let (Some(full), Some(symbol)) = (captures.get(0), captures.get(1))
            && !line[full.end()..].starts_with('=')
        {
            symbols.insert(symbol.as_str().to_owned());
        }
        for pattern in [&*DIFF_DICT_SUBSCRIPT_SYMBOL, &*DIFF_DICT_LITERAL_SYMBOL] {
            for found in pattern.captures_iter(line) {
                if let Some(symbol) = found.get(1) {
                    symbols.insert(symbol.as_str().to_owned());
                }
            }
        }
    }
    symbols.into_iter().collect()
}

fn later_history_hash(fix: &FixEvidence, evidence_ref: &str, scans: &BundleScans) -> String {
    let mut source = format!("fix={}\nref={evidence_ref}\n", fix.sha);
    for path in &scans.scan_files {
        let _ = writeln!(source, "file={path}");
    }
    for (name, scan) in [
        ("fix-diff", &scans.diff),
        ("consumer", &scans.consumers),
        ("later-history", &scans.later),
        ("revert", &scans.revert),
    ] {
        let _ = writeln!(source, "scan={name}\0{}\0{}", scan.status, scan.reason);
    }
    source.push_str(&scans.later.output);
    digest_text(&source)
}

fn incomplete_evidence_reason(scans: &[(&str, &EvidenceScan)]) -> String {
    let incomplete = scans
        .iter()
        .filter(|(_, scan)| scan.status != SCAN_OK)
        .map(|(name, scan)| {
            format!(
                "{name} ({})",
                if scan.reason.is_empty() {
                    scan.status
                } else {
                    scan.reason.as_str()
                }
            )
        })
        .collect::<Vec<_>>();
    format!("required evidence incomplete: {}", incomplete.join("; "))
}

fn append_with_cap(output: &mut String, fragment: &str, cap: usize) -> bool {
    if output.len().saturating_add(fragment.len()) > cap {
        return false;
    }
    output.push_str(fragment);
    true
}

fn added_line_count(diff: &str) -> u64 {
    u64::try_from(
        diff.lines()
            .filter(|line| line.starts_with('+') && !line.starts_with("+++"))
            .count(),
    )
    .unwrap_or(u64::MAX)
}

fn repository_path_text(path: &GitPath) -> Result<String, String> {
    let path = std::str::from_utf8(path.as_bytes())
        .map_err(|_| "repository path is not UTF-8 for a line-oriented artifact".to_owned())?
        .to_owned();
    if path.is_empty() || path.contains(['\n', '\r']) {
        return Err("repository path is unsafe for a line-oriented artifact".to_owned());
    }
    Ok(path)
}

fn excluded_consumer_path(path: &str) -> bool {
    path == "larch-logs" || path.starts_with("larch-logs/")
}

fn cross_language_consumer(path: &str) -> bool {
    Path::new(path)
        .extension()
        .is_some_and(|extension| extension.eq_ignore_ascii_case("sh"))
        || path.ends_with("SKILL.md")
        || path.starts_with("hooks/")
}

fn display_or_none(values: &[String]) -> String {
    if values.is_empty() {
        "(none)".to_owned()
    } else {
        values.join("\n")
    }
}

fn scan_failure_line(scan: &EvidenceScan) -> String {
    if scan.reason.is_empty() {
        String::new()
    } else {
        format!("Failure: {}\n", scan.reason)
    }
}

fn display_scan_output(scan: &EvidenceScan) -> String {
    if scan.output.is_empty() {
        "(none)\n".to_owned()
    } else {
        format!("{}\n", scan.output.trim_end())
    }
}

fn render_consumers(scans: &BundleScans) -> String {
    let mut rows = Vec::new();
    if scans.consumers_truncated {
        rows.push(format!(
            "Notice: consumers truncated to {CONSUMER_CAP} paths"
        ));
    }
    if scans.consumer_references.is_empty() {
        rows.push("(none)".to_owned());
    } else {
        rows.extend(scans.consumer_references.iter().cloned());
    }
    format!("{}\n", rows.join("\n"))
}

fn inline_text(value: &str) -> String {
    value.replace(['\n', '\r'], " ")
}

fn marker_evidence(title: &str, body: &str) -> (Vec<u64>, String) {
    let text = format!("{title}\n{body}");
    if !MARKER_PHRASE.is_match(&text) {
        return (Vec::new(), String::new());
    }
    let references = ISSUE_REFERENCE
        .captures_iter(&text)
        .filter(|found| {
            found.get(0).is_some_and(|whole| {
                !text[..whole.start()]
                    .chars()
                    .next_back()
                    .is_some_and(|character| character.is_ascii_alphanumeric())
            })
        })
        .filter_map(|found| {
            found
                .get(1)
                .and_then(|value| value.as_str().parse::<u64>().ok())
        })
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect::<Vec<_>>();
    if references.is_empty() {
        (references, String::new())
    } else {
        (references, digest_text(&text))
    }
}

fn zones_for_files(paths: &[String]) -> Vec<String> {
    paths
        .iter()
        .filter_map(|path| {
            let parts = path
                .split('/')
                .filter(|part| !part.is_empty() && *part != ".")
                .collect::<Vec<_>>();
            match parts.as_slice() {
                [] => None,
                ["python", "larch", third, ..] => Some(format!("python/larch/{third}")),
                ["scripts" | "docs", ..] => Some(parts[0].to_owned()),
                [first, second, ..] => Some(format!("{first}/{second}")),
                [first] => Some((*first).to_owned()),
            }
        })
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}

fn is_baseline_path(path: &str) -> bool {
    path.strip_prefix("python/")
        .is_some_and(|name| !name.contains('/') && name.ends_with("-baseline.json"))
}

const fn blob_or_link_mode(mode: u32) -> bool {
    matches!(mode & 0o170_000, 0o100_000 | 0o120_000)
}

#[allow(clippy::too_many_arguments, clippy::too_many_lines)] // The raw ledger flags map one-to-one to the compatibility calculation.
fn compute(
    run_dir: &Path,
    ledger_path: &Path,
    manifest_path: &Path,
    refresh: bool,
    sample: usize,
    deep_max: usize,
    model: &str,
    batch_size: usize,
) -> Result<BTreeMap<String, String>, String> {
    let (manifest, bundles) = load_manifest(manifest_path)?;
    let (mut ledger, corrupt) = load_ledger(ledger_path)?;
    let generated_at = manifest
        .get("generated_at")
        .and_then(Value::as_i64)
        .unwrap_or(0);
    let mut metadata = Vec::new();
    for bundle in &bundles {
        let key = string(bundle, "cache_key");
        if key.is_empty() {
            continue;
        }
        let next = metadata_record(bundle, ledger.get(&key), Some(generated_at));
        if metadata_changed(ledger.get(&key), &next) {
            ledger.insert(key, next.clone());
            metadata.push(next);
        }
    }
    let _ = append_records(ledger_path, &metadata)?;
    let (task_model, rate_model) = model_alias(model)?;
    warn_unverified_legacy_triage(&bundles, &ledger);
    let pending: Vec<&Value> = bundles
        .iter()
        .filter(|bundle| {
            !string(bundle, "fix_sha").is_empty()
                && string(bundle, "mechanical_verdict").is_empty()
                && (refresh || !triage_complete(record_for_bundle(&ledger, bundle)))
        })
        .collect();
    let triage_paths = write_pending_batches(run_dir, &pending, batch_size)?;
    let candidates = deep_candidates(&bundles, &ledger, refresh, sample);
    let selected = candidates
        .iter()
        .take(deep_max)
        .cloned()
        .collect::<Vec<_>>();
    let truncated = candidates
        .iter()
        .skip(deep_max)
        .cloned()
        .collect::<Vec<_>>();
    let deep_queue = run_dir.join("deep-queue.jsonl");
    write_jsonl(&deep_queue, &selected)?;
    let summary = json!({
        "TRIAGE_BATCH_PATHS": triage_paths,
        "TRIAGE_PENDING": pending.len(),
        "DEEP_QUEUE_PATH": deep_queue,
        "DEEP_PENDING": selected.len(),
        "DEEP_CAP_TRUNCATED": if truncated.is_empty() { "false" } else { "true" },
        "DEEP_TRUNCATED_ISSUES": truncated.iter().filter_map(|value| value.get("issue")).cloned().collect::<Vec<_>>(),
        "DEEP_TRUNCATED_CANDIDATES": truncated.iter().map(|value| json!({"issue": value.get("issue").cloned().unwrap_or(Value::Null), "reason": value.get("source").cloned().unwrap_or(Value::Null)})).collect::<Vec<_>>(),
        "DEEP_MODEL": task_model,
        "DEEP_RATE_MODEL": rate_model,
        "LEDGER_CORRUPT_LINES": corrupt,
    });
    write_json(&run_dir.join("ledger-summary.json"), &summary)?;
    if !truncated.is_empty() {
        let issues = truncated
            .iter()
            .filter_map(|value| value.get("issue"))
            .map(Value::to_string)
            .collect::<Vec<_>>()
            .join(",");
        eprintln!("WARN: deep cap truncated issues: {issues}");
    }
    let mut output = BTreeMap::new();
    output.insert("TRIAGE_BATCH_PATHS".to_owned(), join_paths(&triage_paths));
    output.insert("TRIAGE_PENDING".to_owned(), pending.len().to_string());
    output.insert("DEEP_QUEUE_PATH".to_owned(), path_text(&deep_queue)?);
    output.insert("DEEP_PENDING".to_owned(), selected.len().to_string());
    output.insert(
        "DEEP_CAP_TRUNCATED".to_owned(),
        (!truncated.is_empty()).to_string(),
    );
    output.insert(
        "DEEP_TRUNCATED_ISSUES".to_owned(),
        truncated
            .iter()
            .filter_map(|value| value.get("issue"))
            .map(Value::to_string)
            .collect::<Vec<_>>()
            .join(","),
    );
    output.insert(
        "DEEP_TRUNCATED_CANDIDATES".to_owned(),
        truncated
            .iter()
            .map(|value| {
                format!(
                    "{{'issue': {}, 'reason': '{}'}}",
                    value.get("issue").unwrap_or(&Value::Null),
                    string(value, "source")
                )
            })
            .collect::<Vec<_>>()
            .join(","),
    );
    output.insert("DEEP_MODEL".to_owned(), task_model.to_owned());
    output.insert("DEEP_RATE_MODEL".to_owned(), rate_model.to_owned());
    output.insert("LEDGER_CORRUPT_LINES".to_owned(), corrupt.to_string());
    let _ = manifest;
    Ok(output)
}

fn ingest(
    run_dir: &Path,
    ledger_path: &Path,
    manifest_path: &Path,
    input_path: &Path,
    stage: &str,
) -> Result<BTreeMap<String, String>, String> {
    let (_manifest, bundles) = load_manifest(manifest_path)?;
    let (mut ledger, corrupt) = load_ledger(ledger_path)?;
    if stage == "deep" && !input_path.is_file() {
        return Ok(ingest_output(stage, 0, 0, corrupt));
    }
    let text = read_lossy(input_path)
        .map_err(|_| format!("ingest file not found: {}", input_path.display()))?;
    let expected = stage_issue_numbers(run_dir, stage)?;
    let by_issue: BTreeMap<u64, &Value> = bundles
        .iter()
        .filter_map(|bundle| {
            positive_number(bundle.get("issue_number")).map(|number| (number, bundle))
        })
        .collect();
    let sampled = sampled_issues(run_dir);
    let mut accepted = Vec::new();
    let mut rejected = 0;
    let mut seen = BTreeSet::new();
    for (index, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let line_number = index + 1;
        let Ok(value) = serde_json::from_str::<Value>(line) else {
            reject_line(line_number, "not JSON");
            rejected += 1;
            continue;
        };
        let Some(object) = value.as_object() else {
            reject_line(line_number, "row is not object");
            rejected += 1;
            continue;
        };
        let issue = match validate_agent_row(object, stage) {
            Ok(issue) => issue,
            Err(reason) => {
                reject_line(line_number, &reason);
                rejected += 1;
                continue;
            }
        };
        if !seen.insert(issue) {
            reject_line(line_number, "duplicate issue in batch");
            rejected += 1;
            continue;
        }
        if !expected.is_empty() && !expected.contains(&issue) {
            reject_line(line_number, &format!("issue not in active {stage} batch"));
            rejected += 1;
            continue;
        }
        let Some(bundle) = by_issue.get(&issue).copied() else {
            reject_line(line_number, "issue not in current manifest");
            rejected += 1;
            continue;
        };
        if !required_evidence_complete(bundle) {
            reject_line(line_number, "required evidence is incomplete");
            rejected += 1;
            continue;
        }
        if stage == "triage"
            && let Err(reason) = validate_evidence_token(object, bundle)
        {
            reject_line(line_number, &reason);
            rejected += 1;
            continue;
        }
        let key = string(bundle, "cache_key");
        let next = ingest_record(
            ledger.get(&key),
            bundle,
            object,
            stage,
            sampled.contains(&issue),
        );
        if !same_record(ledger.get(&key), &next) {
            ledger.insert(key, next.clone());
            accepted.push(next);
        }
    }
    let appended = append_records(ledger_path, &accepted)?;
    Ok(ingest_output(stage, appended, rejected, corrupt))
}

fn ingest_output(
    stage: &str,
    accepted: usize,
    rejected: usize,
    corrupt: usize,
) -> BTreeMap<String, String> {
    BTreeMap::from([
        ("INGEST_STAGE".to_owned(), stage.to_owned()),
        ("INGEST_ACCEPTED".to_owned(), accepted.to_string()),
        ("INGEST_REJECTED".to_owned(), rejected.to_string()),
        ("LEDGER_CORRUPT_LINES".to_owned(), corrupt.to_string()),
    ])
}

fn emit_ledger_payload(payload: &BTreeMap<String, String>) {
    const COMPUTE_KEYS: &[&str] = &[
        "TRIAGE_BATCH_PATHS",
        "TRIAGE_PENDING",
        "DEEP_QUEUE_PATH",
        "DEEP_PENDING",
        "DEEP_CAP_TRUNCATED",
        "DEEP_TRUNCATED_ISSUES",
        "DEEP_TRUNCATED_CANDIDATES",
        "DEEP_MODEL",
        "DEEP_RATE_MODEL",
        "LEDGER_CORRUPT_LINES",
    ];
    const INGEST_KEYS: &[&str] = &[
        "INGEST_STAGE",
        "INGEST_ACCEPTED",
        "INGEST_REJECTED",
        "LEDGER_CORRUPT_LINES",
    ];
    let ordered = if payload.contains_key("INGEST_STAGE") {
        INGEST_KEYS
    } else {
        COMPUTE_KEYS
    };
    for key in ordered {
        if let Some(value) = payload.get(*key) {
            emit_kv(key, value);
        }
    }
}

fn load_manifest(path: &Path) -> Result<(Map<String, Value>, Vec<Value>), String> {
    let value = load_json(path, MAX_MANIFEST_BYTES)?;
    let object = value
        .as_object()
        .cloned()
        .ok_or_else(|| format!("expected JSON object in {}", path.display()))?;
    let issues = object
        .get("issues")
        .and_then(Value::as_array)
        .ok_or_else(|| format!("manifest lacks issues array: {}", path.display()))?
        .iter()
        .filter(|value| value.is_object())
        .cloned()
        .collect();
    Ok((object, issues))
}

fn load_ledger(path: &Path) -> Result<(BTreeMap<String, Value>, usize), String> {
    if !path.exists() {
        return Ok((BTreeMap::new(), 0));
    }
    let metadata = fs::metadata(path).map_err(|error| error.to_string())?;
    if metadata.len() > MAX_LEDGER_BYTES {
        return Err(format!(
            "ledger exceeds {MAX_LEDGER_BYTES} bytes: {}",
            path.display()
        ));
    }
    let text = read_lossy(path)?;
    let mut records = BTreeMap::new();
    let mut corrupt = Vec::new();
    for line in text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        let parsed = serde_json::from_str::<Value>(line);
        let Ok(value) = parsed else {
            corrupt.push(line);
            continue;
        };
        let Some(object) = value.as_object() else {
            corrupt.push(line);
            continue;
        };
        let key = string_value(object, "cache_key");
        if key.is_empty() || positive_number(object.get("issue")).is_none() {
            corrupt.push(line);
            continue;
        }
        records.insert(key, value);
    }
    if !corrupt.is_empty() {
        private_write(
            &path.with_file_name(format!(
                "{}.corrupt-{}",
                path.file_name()
                    .and_then(|name| name.to_str())
                    .unwrap_or("ledger.jsonl"),
                epoch_now()
            )),
            &format!("{}\n", corrupt.join("\n")),
        )?;
    }
    Ok((records, corrupt.len()))
}

fn metadata_record(bundle: &Value, old: Option<&Value>, updated_at: Option<i64>) -> Value {
    let old = old.and_then(Value::as_object);
    let current_fix_time = positive_number(bundle.get("fix_time"));
    let current_added_lines = positive_number(bundle.get("added_lines"));
    json!({
        "cache_key": string(bundle, "cache_key"),
        "issue": positive_number(bundle.get("issue_number")).unwrap_or_default(),
        "fix_sha": string(bundle, "fix_sha"),
        "later_history_hash": string(bundle, "later_history_hash"),
        "triage_verdict": old.map(|value| string_value(value, "triage_verdict")).unwrap_or_default(),
        "triage_reason": old.map(|value| string_value(value, "triage_reason")).unwrap_or_default(),
        "triage_missing_items": old.and_then(|value| value.get("triage_missing_items")).cloned().unwrap_or_else(|| json!([])),
        "triage_needs_deep": old.and_then(|value| value.get("triage_needs_deep")).and_then(Value::as_bool).unwrap_or(false),
        "triage_evidence_verified": old.and_then(|value| value.get("triage_evidence_verified")).and_then(Value::as_bool).unwrap_or(false),
        "triage_introduced_risk": old.map(|value| string_value(value, "triage_introduced_risk")).unwrap_or_default(),
        "triage_introduced_risk_reason": old.map(|value| string_value(value, "triage_introduced_risk_reason")).unwrap_or_default(),
        "deep_verdict": old.map(|value| string_value(value, "deep_verdict")).unwrap_or_default(),
        "deep_reason": old.map(|value| string_value(value, "deep_reason")).unwrap_or_default(),
        "deep_introduced_risk": old.map(|value| string_value(value, "deep_introduced_risk")).unwrap_or_default(),
        "deep_introduced_risk_reason": old.map(|value| string_value(value, "deep_introduced_risk_reason")).unwrap_or_default(),
        "class_complete": old.and_then(|value| value.get("class_complete")).and_then(Value::as_bool).unwrap_or(false),
        "sibling_sites": old.and_then(|value| value.get("sibling_sites")).cloned().unwrap_or_else(|| json!([])),
        "legacy_schema": old.and_then(|value| value.get("legacy_schema")).and_then(Value::as_bool).unwrap_or(true),
        "sampled": old.and_then(|value| value.get("sampled")).and_then(Value::as_bool).unwrap_or(false),
        "stages_complete": old.and_then(|value| value.get("stages_complete")).cloned().unwrap_or_else(|| json!([])),
        "updated_at": updated_at.unwrap_or_else(epoch_now),
        "touched_files": inherited_nonempty_value(bundle, old, "touched_files", json!([])),
        "fix_time": if current_fix_time.is_some() { bundle.get("fix_time").cloned().unwrap_or_else(|| json!(0)) } else { old.and_then(|value| value.get("fix_time")).cloned().unwrap_or_else(|| json!(0)) },
        "added_lines": if current_fix_time.is_some() || current_added_lines.is_some() { bundle.get("added_lines").cloned().unwrap_or_else(|| json!(0)) } else { old.and_then(|value| value.get("added_lines")).cloned().unwrap_or_else(|| json!(0)) },
        "marker_references": inherited_nonempty_value(bundle, old, "marker_references", json!([])),
        "marker_fingerprint": inherited_nonempty_value(bundle, old, "marker_fingerprint", json!("")),
        "zones": inherited_nonempty_value(bundle, old, "zones", json!([])),
        "baseline_extended": bundle.get("baseline_extended").and_then(Value::as_bool).filter(|value| *value).map(Value::Bool).or_else(|| old.and_then(|value| value.get("baseline_extended")).cloned()).unwrap_or(Value::Bool(false)),
        "metadata_version": METADATA_VERSION,
    })
}

fn inherited_nonempty_value(
    bundle: &Value,
    old: Option<&Map<String, Value>>,
    field: &str,
    fallback: Value,
) -> Value {
    bundle
        .get(field)
        .filter(|value| {
            value.as_str().is_none_or(|text| !text.is_empty())
                && value.as_array().is_none_or(|items| !items.is_empty())
        })
        .cloned()
        .or_else(|| old.and_then(|value| value.get(field)).cloned())
        .unwrap_or(fallback)
}

fn metadata_changed(old: Option<&Value>, next: &Value) -> bool {
    const FIELDS: &[&str] = &[
        "touched_files",
        "fix_time",
        "added_lines",
        "marker_references",
        "marker_fingerprint",
        "zones",
        "baseline_extended",
        "metadata_version",
    ];
    old.is_none_or(|old| {
        FIELDS
            .iter()
            .any(|field| old.get(*field) != next.get(*field))
    })
}

#[allow(clippy::too_many_lines)] // Both ingest stages update one compatibility record atomically.
fn ingest_record(
    old: Option<&Value>,
    bundle: &Value,
    row: &Map<String, Value>,
    stage: &str,
    sampled: bool,
) -> Value {
    let mut record = metadata_record(bundle, old, None);
    let object = record
        .as_object_mut()
        .expect("metadata record is an object");
    let mut stages = object
        .get("stages_complete")
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(Value::as_str)
                .map(str::to_owned)
                .collect::<BTreeSet<_>>()
        })
        .unwrap_or_default();
    stages.insert(stage.to_owned());
    if stage == "triage" {
        stages.remove("deep");
        object.insert(
            "triage_verdict".to_owned(),
            row.get("verdict").cloned().unwrap_or(Value::Null),
        );
        object.insert(
            "triage_reason".to_owned(),
            row.get("reason").cloned().unwrap_or(Value::Null),
        );
        object.insert(
            "triage_missing_items".to_owned(),
            row.get("missing_items")
                .cloned()
                .unwrap_or_else(|| json!([])),
        );
        object.insert(
            "triage_needs_deep".to_owned(),
            row.get("needs_deep").cloned().unwrap_or(Value::Bool(false)),
        );
        object.insert("triage_evidence_verified".to_owned(), json!(true));
        object.insert(
            "triage_introduced_risk".to_owned(),
            row.get("introduced_risk")
                .cloned()
                .unwrap_or_else(|| json!("")),
        );
        object.insert(
            "triage_introduced_risk_reason".to_owned(),
            row.get("introduced_risk_reason")
                .cloned()
                .unwrap_or_else(|| json!("")),
        );
        object.insert("deep_verdict".to_owned(), json!(""));
        object.insert("deep_reason".to_owned(), json!(""));
        object.insert("deep_introduced_risk".to_owned(), json!(""));
        object.insert("deep_introduced_risk_reason".to_owned(), json!(""));
        object.insert("class_complete".to_owned(), json!(false));
        object.insert("sibling_sites".to_owned(), json!([]));
    } else {
        object.insert(
            "deep_verdict".to_owned(),
            row.get("verdict").cloned().unwrap_or(Value::Null),
        );
        object.insert(
            "deep_reason".to_owned(),
            row.get("reason").cloned().unwrap_or(Value::Null),
        );
        object.insert(
            "deep_introduced_risk".to_owned(),
            row.get("introduced_risk")
                .cloned()
                .unwrap_or_else(|| json!("")),
        );
        object.insert(
            "deep_introduced_risk_reason".to_owned(),
            row.get("introduced_risk_reason")
                .cloned()
                .unwrap_or_else(|| json!("")),
        );
        object.insert(
            "class_complete".to_owned(),
            row.get("class_complete")
                .cloned()
                .unwrap_or(Value::Bool(false)),
        );
        object.insert(
            "sibling_sites".to_owned(),
            row.get("sibling_sites")
                .cloned()
                .unwrap_or_else(|| json!([])),
        );
    }
    object.insert(
        "legacy_schema".to_owned(),
        json!(!row.contains_key("introduced_risk")),
    );
    object.insert(
        "sampled".to_owned(),
        json!(
            sampled
                || object
                    .get("sampled")
                    .and_then(Value::as_bool)
                    .unwrap_or(false)
        ),
    );
    object.insert("stages_complete".to_owned(), json!(stages));
    object.insert("updated_at".to_owned(), json!(epoch_now()));
    record
}

fn deep_candidates(
    bundles: &[Value],
    ledger: &BTreeMap<String, Value>,
    refresh: bool,
    sample: usize,
) -> Vec<Value> {
    let chronic = chronic_zones(bundles, ledger);
    let mut prioritized = Vec::new();
    let mut seen = BTreeSet::new();
    for bundle in bundles {
        if !required_evidence_complete(bundle) {
            continue;
        }
        let issue = positive_number(bundle.get("issue_number")).unwrap_or_default();
        let record = record_for_bundle(ledger, bundle);
        if !refresh && !string(bundle, "fix_sha").is_empty() && deep_complete(record) {
            continue;
        }
        let source = if string(bundle, "mechanical_verdict") == "NEEDS_DEEP" {
            Some((0, "mechanical"))
        } else if triage_complete(record)
            && matches!(
                record
                    .and_then(|row| row.get("triage_verdict"))
                    .and_then(Value::as_str),
                Some("SUSPECT")
            )
        {
            Some((1, "triage"))
        } else if triage_complete(record)
            && (matches!(
                record
                    .and_then(|row| row.get("triage_verdict"))
                    .and_then(Value::as_str),
                Some("NEEDS_DEEP")
            ) || record
                .and_then(|row| row.get("triage_needs_deep"))
                .and_then(Value::as_bool)
                .unwrap_or(false))
        {
            Some((2, "triage"))
        } else if triage_complete(record)
            && matches!(
                record
                    .and_then(|row| row.get("triage_verdict"))
                    .and_then(Value::as_str),
                Some("FIXED_CLEAR" | "FIXED_LIKELY")
            )
        {
            risk_source(bundle, &chronic)
        } else {
            None
        };
        if let Some((priority, source)) = source {
            prioritized.push((
                priority,
                issue,
                json!({"issue": issue, "cache_key": string(bundle, "cache_key"), "bundle_path": string(bundle, "bundle_path"), "source": source, "sampled": record.and_then(|row| row.get("sampled")).and_then(Value::as_bool).unwrap_or(false)}),
            ));
        }
    }
    prioritized.sort_by_key(|(priority, issue, _)| (*priority, *issue));
    let mut candidates = Vec::new();
    for (_, issue, candidate) in prioritized {
        if seen.insert(issue) {
            candidates.push(candidate);
        }
    }
    if sample > 0 {
        let mut pool = Vec::new();
        for bundle in bundles {
            let issue = positive_number(bundle.get("issue_number")).unwrap_or_default();
            if seen.contains(&issue) || !required_evidence_complete(bundle) {
                continue;
            }
            let record = record_for_bundle(ledger, bundle);
            let triage_ok = matches!(
                record
                    .and_then(|row| row.get("triage_verdict"))
                    .and_then(Value::as_str),
                Some("FIXED_CLEAR" | "FIXED_LIKELY")
            );
            if triage_ok && (refresh || !deep_complete(record)) {
                pool.push((
                    digest_text(&format!("analyze-bugs-sample\0{issue}")),
                    issue,
                    bundle,
                ));
            }
        }
        pool.sort_by(|left, right| left.0.cmp(&right.0).then(left.1.cmp(&right.1)));
        let mut sampled = pool.into_iter().take(sample).collect::<Vec<_>>();
        sampled.sort_by_key(|(_, issue, _)| *issue);
        for (_, issue, bundle) in sampled {
            seen.insert(issue);
            candidates.push(json!({"issue": issue, "cache_key": string(bundle, "cache_key"), "bundle_path": string(bundle, "bundle_path"), "source": "sample", "sampled": true}));
        }
    }
    candidates
}

fn chronic_zones(bundles: &[Value], ledger: &BTreeMap<String, Value>) -> BTreeSet<String> {
    let mut members = BTreeMap::<String, BTreeSet<u64>>::new();
    let mut collect = |row: &Value, issue_field: &str| {
        let issue = positive_number(row.get(issue_field)).unwrap_or_default();
        if issue == 0 {
            return;
        }
        for zone in string_array(row, "zones") {
            members.entry(zone).or_default().insert(issue);
        }
    };
    for bundle in bundles {
        collect(bundle, "issue_number");
    }
    for record in ledger.values() {
        collect(record, "issue");
    }
    members
        .into_iter()
        .filter_map(|(zone, issues)| (issues.len() >= 3).then_some(zone))
        .collect()
}

fn risk_source(bundle: &Value, chronic: &BTreeSet<String>) -> Option<(u8, &'static str)> {
    if bundle
        .get("marker_references")
        .and_then(Value::as_array)
        .is_some_and(|items| !items.is_empty())
    {
        return Some((3, "chain-linked"));
    }
    if string_array(bundle, "zones")
        .iter()
        .any(|zone| chronic.contains(zone))
    {
        return Some((4, "chronic-zone"));
    }
    let files = string_array(bundle, "touched_files");
    if files.iter().any(|path| path.starts_with("python/"))
        && files
            .iter()
            .any(|path| path.starts_with("scripts/") || path.starts_with("skills/"))
    {
        return Some((5, "cross-language"));
    }
    (positive_number(bundle.get("added_lines")).is_some_and(|lines| lines > 300))
        .then_some((6, "size"))
}

fn write_initial_batches(
    run_dir: &Path,
    rows: &[Value],
    batch_size: usize,
) -> Result<Vec<PathBuf>, String> {
    let selected: Vec<&Value> = rows
        .iter()
        .filter(|row| {
            !string(row, "fix_sha").is_empty() && string(row, "mechanical_verdict").is_empty()
        })
        .collect();
    write_batches(run_dir, "triage-batch", &selected, batch_size)
}

fn write_pending_batches(
    run_dir: &Path,
    rows: &[&Value],
    batch_size: usize,
) -> Result<Vec<PathBuf>, String> {
    for entry in fs::read_dir(run_dir).map_err(|error| error.to_string())? {
        let path = entry.map_err(|error| error.to_string())?.path();
        if pending_batch_path(&path) {
            fs::remove_file(path).map_err(|error| error.to_string())?;
        }
    }
    write_batches(run_dir, "triage-pending", rows, batch_size)
}

fn write_batches<T>(
    run_dir: &Path,
    prefix: &str,
    rows: &[T],
    batch_size: usize,
) -> Result<Vec<PathBuf>, String>
where
    T: std::borrow::Borrow<Value>,
{
    let mut paths = Vec::new();
    for group in rows.chunks(batch_size) {
        let path = run_dir.join(format!("{prefix}-{}.jsonl", paths.len() + 1));
        let payload = group
            .iter()
            .map(|row| {
                let row = row.borrow();
                json!({"issue": row.get("issue_number").cloned().unwrap_or(Value::Null), "cache_key": string(row, "cache_key"), "bundle_path": string(row, "bundle_path")}).to_string()
            })
            .collect::<Vec<_>>()
            .join("\n");
        private_write(&path, &format!("{payload}\n"))?;
        paths.push(path);
    }
    Ok(paths)
}

fn write_jsonl(path: &Path, rows: &[Value]) -> Result<(), String> {
    let payload = rows
        .iter()
        .map(Value::to_string)
        .collect::<Vec<_>>()
        .join("\n");
    let text = if payload.is_empty() {
        String::new()
    } else {
        format!("{payload}\n")
    };
    private_write(path, &text)
}

fn append_records(path: &Path, records: &[Value]) -> Result<usize, String> {
    if records.is_empty() {
        return Ok(0);
    }
    append_locked(path, records)
}

fn append_atomically_locked(
    path: &Path,
    parent: &Path,
    records: &[Value],
) -> Result<usize, String> {
    // Re-read after taking the lock. A retried or concurrent sweep may have
    // committed the same durable record after this command loaded its input.
    // The lock is independent of the atomically replaced ledger file.
    if fs::symlink_metadata(path)
        .is_ok_and(|metadata| metadata.file_type().is_symlink() || !metadata.is_file())
    {
        return Err(format!(
            "analysis state is not a regular file: {}",
            path.display()
        ));
    }
    let (existing, _) = load_ledger(path)?;
    let pending = records
        .iter()
        .filter(|record| !same_record(existing.get(&string(record, "cache_key")), record))
        .collect::<Vec<_>>();
    if pending.is_empty() {
        return Ok(0);
    }
    let mut text = if path.exists() {
        read_lossy(path)?
    } else {
        String::new()
    };
    for record in &pending {
        let _ = writeln!(text, "{record}");
    }
    private_atomic_write(path, &text, parent).map_err(|error| error.to_string())?;
    Ok(pending.len())
}

#[cfg(unix)]
fn append_locked(path: &Path, records: &[Value]) -> Result<usize, String> {
    use nix::fcntl::{Flock, FlockArg};

    let parent = path
        .parent()
        .ok_or_else(|| "ledger has no parent".to_owned())?;
    private_dir(parent)?;
    if fs::symlink_metadata(path)
        .is_ok_and(|metadata| metadata.file_type().is_symlink() || !metadata.is_file())
    {
        return Err(format!(
            "analysis state is not a regular file: {}",
            path.display()
        ));
    }
    let lock = path.with_file_name(format!(
        ".{}.lock",
        path.file_name()
            .and_then(|name| name.to_str())
            .ok_or_else(|| "ledger has an unsafe file name".to_owned())?
    ));
    if fs::symlink_metadata(&lock)
        .is_ok_and(|metadata| metadata.file_type().is_symlink() || !metadata.is_file())
    {
        return Err(format!("analysis state lock is unsafe: {}", lock.display()));
    }
    let file = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .mode(0o600)
        .custom_flags(nix::libc::O_NOFOLLOW)
        .open(lock)
        .map_err(|error| error.to_string())?;
    let _locked =
        Flock::lock(file, FlockArg::LockExclusive).map_err(|(_file, error)| error.to_string())?;
    append_atomically_locked(path, parent, records)
}

#[cfg(not(unix))]
fn append_locked(path: &Path, records: &[Value]) -> Result<usize, String> {
    let parent = path
        .parent()
        .ok_or_else(|| "ledger has no parent".to_owned())?;
    private_dir(parent)?;
    let lock = path.with_file_name(format!(
        "{}.lock.d",
        path.file_name()
            .and_then(|name| name.to_str())
            .ok_or_else(|| "ledger has an unsafe file name".to_owned())?
    ));
    crate::run_log_entry_commands::acquire_append_lock(&lock)?;
    let result = append_atomically_locked(path, parent, records);
    let _ = fs::remove_dir(&lock);
    result
}

#[allow(clippy::too_many_lines)] // The stable rejection ordering is the untrusted-agent wire contract.
fn validate_agent_row(row: &Map<String, Value>, stage: &str) -> Result<u64, String> {
    let legacy = match stage {
        "triage" => [
            "issue",
            "verdict",
            "missing_items",
            "reason",
            "needs_deep",
            "evidence_token",
        ],
        _ => ["issue", "verdict", "reason", "", "", ""],
    };
    let current = match stage {
        "triage" => [
            "issue",
            "verdict",
            "missing_items",
            "reason",
            "needs_deep",
            "evidence_token",
            "introduced_risk",
            "introduced_risk_reason",
        ],
        _ => [
            "issue",
            "verdict",
            "reason",
            "introduced_risk",
            "introduced_risk_reason",
            "class_complete",
            "sibling_sites",
            "",
        ],
    };
    let expected: BTreeSet<&str> = legacy
        .into_iter()
        .filter(|value| !value.is_empty())
        .collect();
    let current_expected: BTreeSet<&str> = current
        .into_iter()
        .filter(|value| !value.is_empty())
        .collect();
    let actual: BTreeSet<&str> = row.keys().map(String::as_str).collect();
    if actual != expected && actual != current_expected {
        return Err(format!("{stage} row has unexpected or missing fields"));
    }
    let issue = positive_number(row.get("issue"))
        .ok_or_else(|| format!("{stage} issue must be a positive integer"))?;
    let verdict = string_value(row, "verdict");
    let allowed = if stage == "triage" {
        TRIAGE_VERDICTS
    } else {
        DEEP_VERDICTS
    };
    if !allowed.contains(&verdict.as_str()) {
        return Err(format!("{stage} verdict is unknown"));
    }
    if !row.get("reason").is_some_and(Value::is_string) {
        return Err(format!("{stage} reason must be a string"));
    }
    if stage == "triage" {
        if !row.get("missing_items").is_some_and(|value| {
            value
                .as_array()
                .is_some_and(|items| items.iter().all(Value::is_string))
        }) {
            return Err("triage missing_items must be strings".to_owned());
        }
        if !row.get("needs_deep").is_some_and(Value::is_boolean) {
            return Err("triage needs_deep must be boolean".to_owned());
        }
        if string_value(row, "evidence_token").is_empty() {
            return Err("triage evidence_token must be a non-empty string".to_owned());
        }
    }
    if actual == current_expected {
        for field in ["introduced_risk", "introduced_risk_reason"] {
            if string_value(row, field).is_empty() {
                return Err(format!("{stage} {field} must be a non-empty string"));
            }
        }
        if stage == "deep" {
            if !row.get("class_complete").is_some_and(Value::is_boolean) {
                return Err("deep class_complete must be boolean".to_owned());
            }
            let sites = row
                .get("sibling_sites")
                .and_then(Value::as_array)
                .ok_or_else(|| "deep sibling_sites must be valid path:symbol strings".to_owned())?;
            if !sites.iter().all(|site| {
                site.as_str()
                    .is_some_and(|site| SIBLING_SITE.is_match(site))
            }) {
                return Err("deep sibling_sites must be valid path:symbol strings".to_owned());
            }
            let complete = row
                .get("class_complete")
                .and_then(Value::as_bool)
                .unwrap_or(false);
            if complete && !sites.is_empty() {
                return Err("deep class_complete requires an empty sibling_sites list".to_owned());
            }
            if verdict == "CONFIRMED_FIXED" && !complete && sites.is_empty() {
                return Err("deep confirmed-fixed class-open row requires sibling_sites".to_owned());
            }
        }
    }
    Ok(issue)
}

fn validate_evidence_token(row: &Map<String, Value>, bundle: &Value) -> Result<(), String> {
    let token = string_value(row, "evidence_token");
    let path = PathBuf::from(string(bundle, "bundle_path"));
    let text = fs::read(path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .map_err(|error| format!("bundle unreadable: {error}"))?;
    let expected = text.lines().take(20).find_map(|line| {
        line.strip_prefix("evidence_token: ")
            .is_some_and(|expected| !expected.is_empty() && !expected.contains(char::is_whitespace))
            .then(|| line.strip_prefix("evidence_token: ").unwrap_or_default())
    });
    let expected = expected.ok_or_else(|| "bundle lacks evidence_token line".to_owned())?;
    if token == expected {
        Ok(())
    } else {
        Err("triage evidence_token did not match bundle".to_owned())
    }
}

fn record_for_bundle<'a>(ledger: &'a BTreeMap<String, Value>, bundle: &Value) -> Option<&'a Value> {
    if !required_evidence_complete(bundle) {
        return None;
    }
    let record = ledger.get(&string(bundle, "cache_key"))?;
    let object = record.as_object()?;
    (string_value(object, "fix_sha") == string(bundle, "fix_sha")
        && string_value(object, "later_history_hash") == string(bundle, "later_history_hash"))
    .then_some(record)
}

fn triage_complete(record: Option<&Value>) -> bool {
    record.is_some_and(|record| {
        stage_complete(record, "triage")
            && record
                .get("triage_evidence_verified")
                .and_then(Value::as_bool)
                .unwrap_or(false)
    })
}

fn warn_unverified_legacy_triage(bundles: &[Value], ledger: &BTreeMap<String, Value>) {
    let mut issues = bundles
        .iter()
        .filter(|bundle| required_evidence_complete(bundle))
        .filter_map(|bundle| {
            let record = record_for_bundle(ledger, bundle)?;
            (stage_complete(record, "triage")
                && !record
                    .get("triage_evidence_verified")
                    .and_then(Value::as_bool)
                    .unwrap_or(false))
            .then(|| positive_number(bundle.get("issue_number")).unwrap_or_default())
        })
        .collect::<Vec<_>>();
    issues.sort_unstable();
    issues.dedup();
    if issues.is_empty() {
        return;
    }
    let shown = issues
        .iter()
        .take(LEGACY_TRIAGE_WARN_LIMIT)
        .map(u64::to_string)
        .collect::<Vec<_>>()
        .join(",");
    let suffix = if issues.len() > LEGACY_TRIAGE_WARN_LIMIT {
        format!(" (+{} more)", issues.len() - LEGACY_TRIAGE_WARN_LIMIT)
    } else {
        String::new()
    };
    eprintln!("WARN: ignoring unverified legacy triage rows for issues: {shown}{suffix}");
}

fn deep_complete(record: Option<&Value>) -> bool {
    record.is_some_and(|record| stage_complete(record, "deep"))
}

fn stage_issue_numbers(run_dir: &Path, stage: &str) -> Result<BTreeSet<u64>, String> {
    let paths = if stage == "deep" {
        vec![run_dir.join("deep-queue.jsonl")]
    } else {
        fs::read_dir(run_dir)
            .map_err(|error| error.to_string())?
            .filter_map(Result::ok)
            .map(|entry| entry.path())
            .filter(|path| pending_batch_path(path))
            .collect()
    };
    let mut numbers = BTreeSet::new();
    for path in paths {
        if let Ok(text) = read_lossy(&path) {
            for line in text.lines() {
                if let Ok(value) = serde_json::from_str::<Value>(line)
                    && let Some(number) = positive_number(value.get("issue"))
                {
                    numbers.insert(number);
                }
            }
        }
    }
    Ok(numbers)
}

fn sampled_issues(run_dir: &Path) -> BTreeSet<u64> {
    read_lossy(&run_dir.join("deep-queue.jsonl"))
        .ok()
        .map(|text| {
            text.lines()
                .filter_map(|line| serde_json::from_str::<Value>(line).ok())
                .filter(|value| value.get("sampled").and_then(Value::as_bool) == Some(true))
                .filter_map(|value| positive_number(value.get("issue")))
                .collect()
        })
        .unwrap_or_default()
}

fn pending_batch_path(path: &Path) -> bool {
    path.file_name()
        .and_then(|name| name.to_str())
        .is_some_and(|name| {
            name.starts_with("triage-pending-")
                && path
                    .extension()
                    .is_some_and(|extension| extension.eq_ignore_ascii_case("jsonl"))
        })
}

fn same_record(old: Option<&Value>, next: &Value) -> bool {
    let Some(old) = old else {
        return false;
    };
    let mut old = old.clone();
    let mut next = next.clone();
    if let Some(object) = old.as_object_mut() {
        object.remove("updated_at");
    }
    if let Some(object) = next.as_object_mut() {
        object.remove("updated_at");
    }
    old == next
}

fn model_alias(alias: &str) -> Result<(&'static str, &'static str), String> {
    match alias {
        "sonnet" => Ok(("claude-sonnet-4-6", "claude-sonnet-4-6")),
        "opus" => Ok(("claude-opus-4-8", "claude-opus-4-8")),
        "fable" => Ok(("claude-fable-5", "claude-fable-5")),
        _ => Err(format!(
            "unsupported --deep-model '{alias}'; expected sonnet|opus|fable"
        )),
    }
}

fn state_root(parsed: &ParsedCommandLine, repo: &str) -> Result<PathBuf, String> {
    if let Some(path) = nonempty_option(parsed, "--state-root") {
        let path = expand_home(PathBuf::from(path));
        return if path.is_absolute() {
            Ok(path)
        } else {
            env::current_dir()
                .map(|current| current.join(path))
                .map_err(|_| "could not resolve analysis-state root".to_owned())
        };
    }
    let environment = crate::run_log_commands::resolve_repository_environment_path(None)
        .map_err(|_| "could not resolve analysis-state root".to_owned())?;
    let (_, resolution, _) = crate::run_log_commands::resolve_storage_from_environment(environment)
        .map_err(|error| match error {
            crate::run_log_commands::PreflightFailure::Configuration(error) => error.to_string(),
            crate::run_log_commands::PreflightFailure::Provider(error) => error.to_string(),
        })?;
    let storage = require_enabled_storage(&resolution).map_err(|error| error.to_string())?;
    let home = env::var_os("XDG_STATE_HOME")
        .map(PathBuf::from)
        .or_else(|| env::var_os("HOME").map(|value| PathBuf::from(value).join(".local/state")))
        .ok_or_else(|| "could not resolve analysis-state root".to_owned())?;
    let home = expand_home(home);
    if !home.is_absolute() {
        return Err("analysis state home must be an absolute path".to_owned());
    }
    let _ = repo;
    let client_repo = storage.client_repo.clone();
    let storage_origin_id = storage.storage_origin_id();
    Ok(home
        .join("larch/analysis-state/v2")
        .join(client_repo)
        .join(storage_origin_id))
}

fn default_cache_root() -> PathBuf {
    env::var_os("XDG_CACHE_HOME")
        .map(PathBuf::from)
        .or_else(|| env::var_os("HOME").map(|value| PathBuf::from(value).join(".cache")))
        .unwrap_or_else(|| PathBuf::from(".cache"))
        .join("larch/analyze-bugs")
}

fn create_run_dir(cache_root: &Path, repo: &str) -> Result<PathBuf, String> {
    let base = cache_root.join(sanitize_repo(repo)).join("runs");
    private_dir(&base)?;
    let now = epoch_now();
    for suffix in std::iter::once(String::new()).chain(std::iter::repeat_with(|| {
        format!("-{}", Uuid::new_v4().simple())
    })) {
        let candidate = base.join(format!("{now}{suffix}"));
        match fs::create_dir(&candidate) {
            Ok(()) => return Ok(candidate),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {}
            Err(error) => return Err(error.to_string()),
        }
    }
    unreachable!("unbounded UUID stream always yields another candidate")
}

fn private_dir(path: &Path) -> Result<(), String> {
    fs::create_dir_all(path).map_err(|error| error.to_string())?;
    let metadata = fs::symlink_metadata(path).map_err(|error| error.to_string())?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err("analysis state directory is not a regular directory".to_owned());
    }
    #[cfg(unix)]
    fs::set_permissions(path, fs::Permissions::from_mode(0o700))
        .map_err(|error| error.to_string())?;
    Ok(())
}

fn private_write(path: &Path, text: &str) -> Result<(), String> {
    let parent = path
        .parent()
        .ok_or_else(|| "output path has no parent".to_owned())?;
    private_dir(parent)?;
    private_atomic_write(path, text, parent).map_err(|error| error.to_string())
}

fn write_json(path: &Path, value: &Value) -> Result<(), String> {
    let mut text = serde_json::to_string_pretty(value).map_err(|error| error.to_string())?;
    text.push('\n');
    private_write(path, &text)
}

fn load_json(path: &Path, max_bytes: u64) -> Result<Value, String> {
    let metadata = fs::metadata(path).map_err(|error| error.to_string())?;
    if metadata.len() > max_bytes {
        return Err(format!(
            "input exceeds {max_bytes} bytes: {}",
            path.display()
        ));
    }
    serde_json::from_slice(&fs::read(path).map_err(|error| error.to_string())?)
        .map_err(|error| error.to_string())
}

fn read_lossy(path: &Path) -> Result<String, String> {
    fs::read(path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .map_err(|error| error.to_string())
}

fn normalize_count_short_flag(arguments: &[OsString]) -> Vec<OsString> {
    arguments
        .iter()
        .map(|argument| {
            let text = argument.to_string_lossy();
            if text == "-n" {
                return OsString::from("--count");
            }
            if let Some(value) = text.strip_prefix("-n") {
                let value = value.strip_prefix('=').unwrap_or(value);
                return OsString::from(format!("--count={value}"));
            }
            argument.clone()
        })
        .collect()
}

fn help_position(arguments: &[OsString]) -> Option<usize> {
    arguments
        .iter()
        .position(|argument| matches!(argument.to_string_lossy().as_ref(), "-h" | "--help"))
}

fn positive_option(
    parsed: &ParsedCommandLine,
    name: &str,
    default: usize,
    usage: &str,
    program: &str,
) -> Result<usize, ExitCode> {
    let value = option_text_or(parsed, name, &default.to_string());
    let argument = if name == "--count" {
        "-n/--count"
    } else {
        name
    };
    value
        .parse::<usize>()
        .ok()
        .filter(|value| *value > 0)
        .ok_or_else(|| {
            usage_error(
                usage,
                program,
                &format!("argument {argument}: {name} must be a positive integer"),
                2,
            )
        })
}

fn signed_option(
    parsed: &ParsedCommandLine,
    name: &str,
    default: i64,
    usage: &str,
    program: &str,
) -> Result<i64, ExitCode> {
    let value = option_text_or(parsed, name, &default.to_string());
    value.parse::<i64>().map_err(|_| {
        usage_error(
            usage,
            program,
            &format!("argument {name}: invalid int value: '{value}'"),
            2,
        )
    })
}

fn option_text(parsed: &ParsedCommandLine, name: &str) -> String {
    parsed
        .value(name)
        .and_then(|value| value.to_str())
        .unwrap_or_default()
        .to_owned()
}

fn option_text_or(parsed: &ParsedCommandLine, name: &str, default: &str) -> String {
    parsed
        .value(name)
        .and_then(|value| value.to_str())
        .unwrap_or(default)
        .to_owned()
}

fn nonempty_option(parsed: &ParsedCommandLine, name: &str) -> Option<String> {
    let value = option_text(parsed, name);
    (!value.is_empty()).then_some(value)
}

fn option_path_or(parsed: &ParsedCommandLine, name: &str, default: &Path) -> PathBuf {
    nonempty_option(parsed, name)
        .map(PathBuf::from)
        .map_or_else(|| default.to_path_buf(), expand_home)
}

fn expand_home(path: PathBuf) -> PathBuf {
    if path.as_os_str() == "~" {
        return env::var_os("HOME").map(PathBuf::from).unwrap_or(path);
    }
    if let Some(text) = path.to_str()
        && let Some(rest) = text.strip_prefix("~/")
        && let Some(home) = env::var_os("HOME")
    {
        return PathBuf::from(home).join(rest);
    }
    path
}

fn sanitize_repo(repo: &str) -> String {
    let value: String = repo
        .trim()
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() || matches!(character, '_' | '.' | '-') {
                character
            } else {
                '-'
            }
        })
        .collect();
    value
        .trim_matches(['.', '-'])
        .to_owned()
        .if_empty("unknown-repo")
}

trait EmptyFallback {
    fn if_empty(self, fallback: &str) -> String;
}
impl EmptyFallback for String {
    fn if_empty(self, fallback: &str) -> String {
        if self.is_empty() {
            fallback.to_owned()
        } else {
            self
        }
    }
}

fn string(value: &Value, field: &str) -> String {
    value
        .as_object()
        .map_or_else(String::new, |object| string_value(object, field))
}
fn string_array(value: &Value, field: &str) -> Vec<String> {
    value
        .get(field)
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(Value::as_str)
                .map(str::to_owned)
                .collect()
        })
        .unwrap_or_default()
}
fn string_value(object: &Map<String, Value>, field: &str) -> String {
    object
        .get(field)
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned()
}
fn positive_number(value: Option<&Value>) -> Option<u64> {
    value.and_then(Value::as_u64).filter(|value| *value > 0)
}
const fn issue_state(state: GitHubIssueState) -> &'static str {
    match state {
        GitHubIssueState::Open => "OPEN",
        GitHubIssueState::Closed => "CLOSED",
        GitHubIssueState::All => "ALL",
    }
}
fn digest_text(value: &str) -> String {
    format!("{:x}", Sha256::digest(value.as_bytes()))
}
fn cap_text(value: &str, cap: usize) -> String {
    if value.chars().count() <= cap {
        value.to_owned()
    } else {
        format!(
            "{}\n\n[content truncated to {cap} characters]\n",
            value.chars().take(cap).collect::<String>()
        )
    }
}
fn path_text(path: &Path) -> Result<String, String> {
    let text = path.to_string_lossy().into_owned();
    (!text.contains(['\n', '\r']))
        .then_some(text)
        .ok_or_else(|| "path contains a line break".to_owned())
}
fn emit_path(key: &str, path: &Path) {
    emit_kv(key, &path_text(path).unwrap_or_else(|_| String::new()));
}
fn join_paths(paths: &[PathBuf]) -> String {
    paths
        .iter()
        .filter_map(|path| path_text(path).ok())
        .collect::<Vec<_>>()
        .join(",")
}
fn reject_line(line: usize, reason: &str) {
    eprintln!("WARN: rejected line {line}: {reason}");
}

fn nonnegative_usize(value: i64) -> usize {
    usize::try_from(value.max(0)).unwrap_or(usize::MAX)
}
fn has_exact_issue_reference(text: &str, issue: u64) -> bool {
    let needle = format!("#{issue}");
    text.match_indices(&needle).any(|(index, _)| {
        !text[..index]
            .chars()
            .next_back()
            .is_some_and(|character| character.is_ascii_digit())
            && !text[index + needle.len()..]
                .chars()
                .next()
                .is_some_and(|character| character.is_ascii_digit())
    })
}
fn commit_timestamp(bytes: &[u8]) -> i64 {
    String::from_utf8_lossy(bytes)
        .lines()
        .find_map(|line| {
            line.strip_prefix("committer ")
                .and_then(|value| {
                    value.rsplit_once(' ').and_then(|(timestamp, _zone)| {
                        timestamp
                            .rsplit_once(' ')
                            .map(|(_identity, timestamp)| timestamp)
                    })
                })
                .and_then(|timestamp| timestamp.parse().ok())
        })
        .unwrap_or(0)
}

/// Execute the bounded runtime verification wave for selected bug fixes.
#[must_use]
pub fn runtime(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &[
        "--run-dir",
        "--manifest",
        "--ledger-path",
        "--runtime-max",
        "--repo-root",
    ];
    let help_at = help_position(arguments);
    let parsed = parse_with_flags(
        &arguments[..help_at.unwrap_or(arguments.len())],
        OPTIONS,
        &[],
        0,
    );
    if let Some(error) = parsed.value_error() {
        return usage_error(RUNTIME_USAGE, RUNTIME_PROGRAM, error, 2);
    }
    if help_at.is_some() {
        print!("{RUNTIME_HELP}");
        return ExitCode::SUCCESS;
    }
    let missing: Vec<&str> = ["--run-dir", "--manifest", "--ledger-path", "--repo-root"]
        .into_iter()
        .filter(|name| parsed.value(name).is_none())
        .collect();
    if !missing.is_empty() {
        return usage_error(
            RUNTIME_USAGE,
            RUNTIME_PROGRAM,
            &format!(
                "the following arguments are required: {}",
                missing.join(", ")
            ),
            2,
        );
    }
    if let Some(error) = parsed.error() {
        return usage_error(RUNTIME_USAGE, RUNTIME_PROGRAM, &error, 2);
    }
    let runtime_max = option_text_or(&parsed, "--runtime-max", &DEFAULT_RUNTIME_MAX.to_string());
    let Ok(runtime_max) = runtime_max.parse::<i64>() else {
        return usage_error(
            RUNTIME_USAGE,
            RUNTIME_PROGRAM,
            &format!(
                "argument --runtime-max: invalid int value: '{}'",
                option_text(&parsed, "--runtime-max")
            ),
            2,
        );
    };
    let run_dir = PathBuf::from(option_text(&parsed, "--run-dir"));
    let manifest_path = PathBuf::from(option_text(&parsed, "--manifest"));
    let repo_root = PathBuf::from(option_text(&parsed, "--repo-root"));
    let result = (|| {
        let (_manifest, bundles) = load_manifest(&manifest_path)?;
        runtime_verify(&run_dir, &bundles, runtime_max, &repo_root)
    })();
    match result {
        Ok((selected, skipped)) => {
            emit_path(
                "RUNTIME_RESULTS_PATH",
                &run_dir.join("runtime-results.jsonl"),
            );
            emit_kv("RUNTIME_SELECTED_UNIQUE_SHAS", &selected.to_string());
            emit_kv("RUNTIME_SKIPPED_UNIQUE_SHAS", &skipped.to_string());
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("ERROR: {error}");
            ExitCode::FAILURE
        }
    }
}

#[derive(Clone)]
struct RuntimeBindingData {
    issue: u64,
    cache_key: String,
    fix_sha: String,
}

struct RuntimeGroup {
    fix_sha: String,
    bindings: Vec<RuntimeBindingData>,
    touched_paths: Vec<String>,
    max_fix_time: i64,
}

#[derive(Clone)]
struct RuntimeComponentData {
    name: String,
    status: String,
    evidence: String,
}

#[derive(Clone)]
struct RuntimeResultData {
    fix_sha: String,
    bindings: Vec<RuntimeBindingData>,
    components: Vec<RuntimeComponentData>,
    uncovered_zones: Vec<String>,
}

#[allow(clippy::too_many_lines)] // Cap, discovery, execution, and durable artifacts are one ordered runtime transaction.
fn runtime_verify(
    run_dir: &Path,
    bundles: &[Value],
    runtime_max: i64,
    repo_root: &Path,
) -> Result<(usize, usize), String> {
    if runtime_max < 0 {
        return Err("--runtime-max must be nonnegative".to_owned());
    }
    let mut grouped: BTreeMap<String, RuntimeGroup> = BTreeMap::new();
    for bundle in bundles {
        let fix_sha = string(bundle, "fix_sha");
        if fix_sha.is_empty() {
            continue;
        }
        let issue = positive_number(bundle.get("issue_number")).unwrap_or_default();
        if !full_sha(&fix_sha) {
            return Err(format!(
                "runtime verification received invalid fix SHA for issue #{issue}"
            ));
        }
        let entry = grouped
            .entry(fix_sha.clone())
            .or_insert_with(|| RuntimeGroup {
                fix_sha: fix_sha.clone(),
                bindings: Vec::new(),
                touched_paths: Vec::new(),
                max_fix_time: 0,
            });
        entry.bindings.push(RuntimeBindingData {
            issue,
            cache_key: string(bundle, "cache_key"),
            fix_sha,
        });
        entry
            .touched_paths
            .extend(string_array(bundle, "touched_files"));
        entry.max_fix_time = entry
            .max_fix_time
            .max(bundle.get("fix_time").and_then(Value::as_i64).unwrap_or(0));
    }
    let mut ranked = grouped.into_values().collect::<Vec<_>>();
    ranked.sort_by(|left, right| {
        right
            .max_fix_time
            .cmp(&left.max_fix_time)
            .then_with(|| left.fix_sha.cmp(&right.fix_sha))
    });
    if runtime_max == 0 {
        private_write(&run_dir.join("runtime-results.jsonl"), "")?;
        write_json(
            &run_dir.join("runtime-summary.json"),
            &json!({"selected_unique_shas": 0, "skipped_unique_shas": ranked.len()}),
        )?;
        return Ok((0, ranked.len()));
    }
    let selected_limit = usize::try_from(runtime_max).unwrap_or(usize::MAX);
    let total_groups = ranked.len();
    let selected = ranked.into_iter().take(selected_limit).collect::<Vec<_>>();
    let skipped = total_groups.saturating_sub(selected.len());
    let runtime_context = if selected.is_empty() {
        None
    } else {
        let resolved_repo = absolute_directory(repo_root, "runtime repo root")?;
        let repository = GixRepository::discover(&resolved_repo)
            .map_err(|error| format!("runtime test discovery failed: {error}"))?;
        Some((resolved_repo, repository))
    };
    let mut results = Vec::new();
    for group in selected {
        let (resolved_repo, repository) = runtime_context
            .as_ref()
            .expect("selected runtime group has a repository context");
        let tests = discover_runtime_tests(repository, &group.fix_sha, resolved_repo)?;
        let mut components = Vec::new();
        if tests.is_empty() {
            components.push(RuntimeComponentData {
                name: "pytest".to_owned(),
                status: "absent".to_owned(),
                evidence: "no runnable commit test files".to_owned(),
            });
        } else {
            let base_temp = run_dir.join("runtime-pytest-tmp").join(&group.fix_sha);
            let mut arguments = vec![
                OsString::from("-m"),
                OsString::from("pytest"),
                OsString::from("-p"),
                OsString::from("no:cacheprovider"),
                OsString::from("--basetemp"),
                base_temp.into_os_string(),
                OsString::from("--"),
            ];
            arguments.extend(tests.iter().map(OsString::from));
            components.push(runtime_component(
                "pytest",
                ExternalProgram::HostUtility(HostUtilityProgram::Pytest),
                arguments,
                resolved_repo,
            ));
        }
        for target in runtime_harnesses(&group.touched_paths) {
            components.push(runtime_component(
                &target,
                ExternalProgram::HostUtility(HostUtilityProgram::Make),
                vec![OsString::from(target.clone())],
                resolved_repo,
            ));
        }
        results.push(RuntimeResultData {
            fix_sha: group.fix_sha,
            bindings: group.bindings,
            components,
            uncovered_zones: runtime_uncovered_zones(&group.touched_paths),
        });
    }
    let mut artifact = String::new();
    for result in &results {
        artifact.push_str(
            &serde_json::to_string(&runtime_result_value(result))
                .map_err(|error| error.to_string())?,
        );
        artifact.push('\n');
    }
    private_write(&run_dir.join("runtime-results.jsonl"), &artifact)?;
    write_json(
        &run_dir.join("runtime-summary.json"),
        &json!({"selected_unique_shas": results.len(), "skipped_unique_shas": skipped}),
    )?;
    Ok((results.len(), skipped))
}

fn absolute_directory(path: &Path, label: &str) -> Result<PathBuf, String> {
    let path = if path.is_absolute() {
        path.to_path_buf()
    } else {
        env::current_dir()
            .map_err(|error| format!("could not resolve {label}: {error}"))?
            .join(path)
    };
    let metadata =
        fs::metadata(&path).map_err(|error| format!("could not resolve {label}: {error}"))?;
    if !metadata.is_dir() {
        return Err(format!("{label} is not a directory"));
    }
    Ok(path)
}

fn full_sha(value: &str) -> bool {
    value.len() == 40
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || matches!(byte, b'a'..=b'f'))
}

fn discover_runtime_tests(
    repository: &GixRepository,
    fix_sha: &str,
    repo_root: &Path,
) -> Result<Vec<String>, String> {
    let commit_id = repository
        .resolve_revision(&Revision::new(fix_sha.as_bytes().to_vec()))
        .map_err(|error| format!("runtime test discovery for {fix_sha} failed: {error}"))?;
    let commit = repository
        .walk_commits(&commit_id, 1)
        .map_err(|error| format!("runtime test discovery for {fix_sha} failed: {error}"))?
        .into_iter()
        .next()
        .ok_or_else(|| format!("runtime test discovery for {fix_sha} failed: commit missing"))?;
    let Some(parent_id) = commit.parents.first() else {
        return Ok(Vec::new());
    };
    let parent = repository
        .walk_commits(parent_id, 1)
        .map_err(|error| format!("runtime test discovery for {fix_sha} failed: {error}"))?
        .into_iter()
        .next()
        .ok_or_else(|| format!("runtime test discovery for {fix_sha} failed: parent missing"))?;
    let changes = repository
        .tree_changes(&parent.tree, &commit.tree)
        .map_err(|error| format!("runtime test discovery for {fix_sha} failed: {error}"))?;
    let mut tests = BTreeSet::new();
    for change in changes.entries() {
        if !matches!(change.kind, ChangeKind::Added | ChangeKind::Modified) {
            continue;
        }
        let candidate = repository_path_text(&change.path)
            .map_err(|error| format!("runtime test discovery for {fix_sha} failed: {error}"))?;
        if candidate.starts_with("python/tests/")
            && safe_runtime_path(&candidate)
            && repo_root.join(&candidate).is_file()
        {
            tests.insert(candidate);
        }
    }
    Ok(tests.into_iter().collect())
}

fn safe_runtime_path(value: &str) -> bool {
    let path = Path::new(value);
    !value.is_empty()
        && !path.is_absolute()
        && !value.contains('\\')
        && !path.components().any(|component| {
            matches!(
                component,
                std::path::Component::ParentDir | std::path::Component::CurDir
            )
        })
}

fn safe_sweep_path(value: &str) -> bool {
    safe_runtime_path(value) && !value.starts_with('~') && !value.chars().any(char::is_control)
}

fn runtime_harnesses(paths: &[String]) -> Vec<String> {
    [
        ("skills/implement/", "test-architectural-guidelines-step"),
        (
            "scripts/test-implement-anti-halt.sh",
            "test-implement-anti-halt",
        ),
    ]
    .into_iter()
    .filter(|(prefix, _)| paths.iter().any(|path| path.starts_with(prefix)))
    .map(|(_, target)| target.to_owned())
    .collect()
}

fn runtime_uncovered_zones(paths: &[String]) -> Vec<String> {
    const ZONES: &[&str] = &[
        "skills/",
        "scripts/",
        "hooks/",
        "agents/",
        "python/larch/implement/",
        "python/larch/design/",
    ];
    const HARNESSES: &[&str] = &["skills/implement/", "scripts/test-implement-anti-halt.sh"];
    paths
        .iter()
        .filter_map(|path| {
            ZONES
                .iter()
                .filter(|prefix| path.starts_with(**prefix))
                .max_by_key(|prefix| prefix.len())
                .filter(|_| !HARNESSES.iter().any(|prefix| path.starts_with(prefix)))
                .map(|zone| zone.trim_end_matches('/').to_owned())
        })
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}

fn runtime_component(
    name: &str,
    program: ExternalProgram,
    arguments: Vec<OsString>,
    repo_root: &Path,
) -> RuntimeComponentData {
    let request = bounded_request_in(
        program,
        arguments,
        repo_root,
        RUNTIME_TIMEOUT,
        RUNTIME_SHUTDOWN_GRACE,
        RUNTIME_OUTPUT_LIMIT,
    );
    let request = match request {
        Ok(request) => request,
        Err(error) => {
            return RuntimeComponentData {
                name: name.to_owned(),
                status: "failed".to_owned(),
                evidence: cap_text(&error, RUNTIME_EVIDENCE_CAP),
            };
        }
    };
    match run_bounded_detailed(request) {
        Ok(output) if output.status().success() => RuntimeComponentData {
            name: name.to_owned(),
            status: "passed".to_owned(),
            evidence: String::new(),
        },
        Ok(output) => RuntimeComponentData {
            name: name.to_owned(),
            status: "failed".to_owned(),
            evidence: runtime_evidence(output.stderr(), output.stdout()),
        },
        Err(error) => {
            let (status, stderr, stdout) = match &error {
                error if error.kind() == ProcessErrorKind::TimedOut => (
                    "timeout",
                    error.output().map_or(&[][..], |output| output.stderr()),
                    error.output().map_or(&[][..], |output| output.stdout()),
                ),
                _ => ("failed", &[][..], &[][..]),
            };
            let evidence = if stderr.is_empty() && stdout.is_empty() {
                cap_text(error.message(), RUNTIME_EVIDENCE_CAP)
            } else {
                runtime_evidence(stderr, stdout)
            };
            RuntimeComponentData {
                name: name.to_owned(),
                status: status.to_owned(),
                evidence,
            }
        }
    }
}

fn runtime_evidence(stderr: &[u8], stdout: &[u8]) -> String {
    let source = if stderr.is_empty() { stdout } else { stderr };
    let cleaned = String::from_utf8_lossy(source)
        .replace(['\r', '\n'], " ")
        .chars()
        .map(|character| {
            if character.is_control() {
                ' '
            } else {
                character
            }
        })
        .collect::<String>()
        .replace('|', "\\|");
    cap_text(cleaned.trim(), RUNTIME_EVIDENCE_CAP)
}

fn runtime_result_value(result: &RuntimeResultData) -> Value {
    json!({
        "schema_version": "1",
        "fix_sha": result.fix_sha,
        "bindings": result.bindings.iter().map(|binding| json!({
            "issue": binding.issue,
            "cache_key": binding.cache_key,
            "fix_sha": binding.fix_sha,
        })).collect::<Vec<_>>(),
        "components": result.components.iter().map(|component| json!({
            "name": component.name,
            "status": component.status,
            "evidence": component.evidence,
        })).collect::<Vec<_>>(),
        "uncovered_zones": result.uncovered_zones,
    })
}

/// Render the report-only result for a bounded bug-verification run.
#[must_use]
pub fn report(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--run-dir", "--manifest", "--ledger-path"];
    let help_at = help_position(arguments);
    let parsed = parse_with_flags(
        &arguments[..help_at.unwrap_or(arguments.len())],
        OPTIONS,
        &[],
        0,
    );
    if let Some(error) = parsed.value_error() {
        return usage_error(REPORT_USAGE, REPORT_PROGRAM, error, 2);
    }
    if help_at.is_some() {
        print!("{REPORT_HELP}");
        return ExitCode::SUCCESS;
    }
    let missing: Vec<&str> = ["--run-dir", "--manifest", "--ledger-path"]
        .into_iter()
        .filter(|name| parsed.value(name).is_none())
        .collect();
    if !missing.is_empty() {
        return usage_error(
            REPORT_USAGE,
            REPORT_PROGRAM,
            &format!(
                "the following arguments are required: {}",
                missing.join(", ")
            ),
            2,
        );
    }
    if let Some(error) = parsed.error() {
        return usage_error(REPORT_USAGE, REPORT_PROGRAM, &error, 2);
    }
    let rendered = render_report(
        &PathBuf::from(option_text(&parsed, "--manifest")),
        &PathBuf::from(option_text(&parsed, "--ledger-path")),
        &PathBuf::from(option_text(&parsed, "--run-dir")),
    );
    match rendered {
        Ok(report) => {
            print!("{report}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("ERROR: {error}");
            ExitCode::FAILURE
        }
    }
}

#[derive(Clone)]
struct RuntimeReportResult {
    components: Vec<RuntimeComponentData>,
    uncovered_zones: Vec<String>,
}

#[derive(Clone)]
struct ReportRow {
    issue: u64,
    fix_sha: String,
    url: String,
    verdict: String,
    tier: String,
    reason: String,
    missing: Vec<String>,
    sampled: bool,
}

#[derive(Clone)]
struct AnalyticsRecordData {
    issue: u64,
    cache_key: String,
    fix_sha: String,
    touched_files: Vec<String>,
    fix_time: i64,
    marker_references: Vec<u64>,
    zones: Vec<String>,
    baseline_extended: bool,
    active: bool,
}

#[derive(Clone)]
struct AnalyticsViewData {
    edges: Vec<(u64, u64, String)>,
    chronic: Vec<(String, Vec<u64>, Vec<String>)>,
    baseline_issues: Vec<u64>,
}

#[derive(Clone)]
struct SweepCandidateData {
    merge_sha: String,
    file: String,
    symbol: String,
    description: String,
    severity: String,
    confidence: String,
}

struct SweepReportData {
    pinned_tip: String,
    selected_count: u64,
    skipped_count: u64,
    pending_shas: Vec<String>,
    coverage_incomplete: bool,
    candidates: Vec<SweepCandidateData>,
    selected_manifest: Value,
}

#[allow(clippy::cognitive_complexity, clippy::too_many_lines)] // The fixed report section order is a Python compatibility contract.
fn render_report(
    manifest_path: &Path,
    ledger_path: &Path,
    run_dir: &Path,
) -> Result<String, String> {
    let (manifest, bundles) = load_manifest(manifest_path)?;
    let (ledger, corrupt_count) = load_ledger(ledger_path)?;
    let runtime_results = load_runtime_results(&run_dir.join("runtime-results.jsonl"), &bundles)?;
    let runtime_summary = if run_dir.join("runtime-summary.json").exists() {
        load_json(&run_dir.join("runtime-summary.json"), MAX_MANIFEST_BYTES)?
    } else {
        json!({})
    };
    let sweep = load_validated_sweep(run_dir)?;
    let summary = if run_dir.join("ledger-summary.json").exists() {
        load_json(&run_dir.join("ledger-summary.json"), MAX_MANIFEST_BYTES)?
    } else {
        json!({})
    };
    let truncated = summary
        .get("DEEP_TRUNCATED_ISSUES")
        .and_then(Value::as_array)
        .map(|values| {
            values
                .iter()
                .filter_map(Value::as_u64)
                .collect::<BTreeSet<_>>()
        })
        .unwrap_or_default();
    let mut rows = Vec::new();
    let mut coverage_gaps: BTreeMap<String, BTreeSet<u64>> = BTreeMap::new();
    let mut introduced_risk_rows = Vec::new();
    let mut class_open_rows = Vec::new();
    let mut verified_issues = Vec::new();
    for bundle in &bundles {
        let record = report_record_for_bundle(&ledger, bundle).cloned();
        let (mut verdict, mut tier, mut reason, missing, sampled) =
            final_verdict(bundle, record.as_ref());
        let issue = positive_number(bundle.get("issue_number")).unwrap_or_default();
        if truncated.contains(&issue) {
            "NEEDS_DEEP".clone_into(&mut verdict);
            tier.clear();
            "deep cap truncated this candidate".clone_into(&mut reason);
        }
        if let Some(runtime) = runtime_results.get(&string(bundle, "cache_key")) {
            let (next_verdict, next_tier, next_reason, annotations) =
                runtime_overlay(&verdict, &tier, &reason, runtime);
            verdict = next_verdict;
            tier = next_tier;
            reason = next_reason;
            if !annotations.is_empty() {
                reason = if reason.is_empty() {
                    annotations.join("; ")
                } else {
                    format!("{}; {}", reason, annotations.join("; "))
                };
            }
            for annotation in annotations {
                coverage_gaps.entry(annotation).or_default().insert(issue);
            }
        }
        if let Some((stage, risk, evidence)) = selected_introduced_risk(record.as_ref())
            && risk != "none found"
        {
            introduced_risk_rows.push((bundle.clone(), stage, risk, evidence));
        }
        if let Some(sites) = class_open_siblings(record.as_ref()) {
            class_open_rows.push((
                bundle.clone(),
                sites,
                record
                    .as_ref()
                    .map_or_else(String::new, |value| string(value, "deep_reason")),
            ));
        }
        if verified_issue(&verdict, &tier) {
            verified_issues.push(issue);
        }
        rows.push(ReportRow {
            issue,
            fix_sha: string(bundle, "fix_sha"),
            url: string(bundle, "url"),
            verdict,
            tier,
            reason,
            missing,
            sampled,
        });
    }
    let analytics = analytics_view(&manifest, &bundles, &ledger);
    let counts = report_counts(&rows);
    let count_table = markdown_table(&[
        vec!["Metric".to_owned(), "Count".to_owned()],
        vec!["Total".to_owned(), counts.0.to_string()],
        vec!["Confirmed or likely fixed".to_owned(), counts.1.to_string()],
        vec!["Needs deep".to_owned(), counts.2.to_string()],
        vec!["Not fixed".to_owned(), counts.3.to_string()],
        vec!["Incomplete".to_owned(), counts.4.to_string()],
        vec!["Regressed".to_owned(), counts.5.to_string()],
        vec!["Won't fix".to_owned(), counts.6.to_string()],
        vec!["Unverifiable".to_owned(), counts.7.to_string()],
    ]);
    let mut issue_table = vec![vec![
        "Issue".to_owned(),
        "Fix".to_owned(),
        "Tier".to_owned(),
        "Verdict".to_owned(),
        "Reason".to_owned(),
        "Missing items".to_owned(),
    ]];
    for row in &rows {
        let issue = if row.url.is_empty() {
            format!("#{}", row.issue)
        } else {
            format!("[#{}]({})", row.issue, row.url)
        };
        issue_table.push(vec![
            issue,
            short_sha(&row.fix_sha),
            if row.tier.is_empty() {
                "PENDING".to_owned()
            } else {
                row.tier.clone()
            },
            row.verdict.clone(),
            row.reason.clone(),
            row.missing.join("; "),
        ]);
    }
    let followups = rows
        .iter()
        .filter(|row| {
            matches!(
                row.verdict.as_str(),
                "NOT_FIXED" | "INCOMPLETE" | "REGRESSED"
            )
        })
        .cloned()
        .collect::<Vec<_>>();
    let followup_path = run_dir.join("follow-up-issue.md");
    if !followups.is_empty()
        || !class_open_rows.is_empty()
        || sweep
            .as_ref()
            .is_some_and(|sweep| !sweep.candidates.is_empty())
    {
        let mut body = vec![
            "# Analyze-bugs follow-up".to_owned(),
            String::new(),
            format!("Repo: {}", string_value(&manifest, "repo")),
            String::new(),
            "Findings:".to_owned(),
        ];
        body.extend(
            followups
                .iter()
                .map(|row| format!("- #{}: {}. {}", row.issue, row.verdict, row.reason)),
        );
        for (bundle, sites, deep_reason) in &class_open_rows {
            body.push(format!(
                "- #{}: Instance fixed, class open. Sibling sites: {}. {}",
                positive_number(bundle.get("issue_number")).unwrap_or_default(),
                sites.join(", "),
                deep_reason
            ));
        }
        if let Some(sweep) = &sweep
            && !sweep.candidates.is_empty()
        {
            body.push(String::new());
            body.push("Sweep candidates:".to_owned());
            body.extend(sweep.candidates.iter().map(|candidate| {
                format!(
                    "- {} {} `{}`: {}/{}. {}",
                    short_sha(&candidate.merge_sha),
                    candidate.file,
                    candidate.symbol,
                    candidate.severity,
                    candidate.confidence,
                    candidate.description
                )
            }));
        }
        private_write(&followup_path, &format!("{}\n", body.join("\n")))?;
    }
    let generated_at = manifest
        .get("generated_at")
        .and_then(Value::as_i64)
        .unwrap_or(0);
    let repo = string_value(&manifest, "repo");
    let selected_issues = bundles
        .iter()
        .filter_map(|bundle| positive_number(bundle.get("issue_number")))
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect::<Vec<_>>();
    verified_issues.sort_unstable();
    verified_issues.dedup();
    let chronic_zones = analytics
        .chronic
        .iter()
        .map(|(zone, _, _)| zone.clone())
        .collect::<Vec<_>>();
    let edge_ids = analytics
        .edges
        .iter()
        .map(|(from, to, kind)| format!("{from}>{to}:{kind}"))
        .collect::<Vec<_>>();
    let previous = previous_snapshot(run_dir, &repo, generated_at);
    let prior_selected = previous
        .as_ref()
        .map_or_else(BTreeSet::new, |snapshot| snapshot.selected.clone());
    let prior_verified = previous
        .as_ref()
        .map_or_else(BTreeSet::new, |snapshot| snapshot.verified.clone());
    let prior_edges = previous
        .as_ref()
        .map_or_else(BTreeSet::new, |snapshot| snapshot.edges.clone());
    let prior_zones = previous
        .as_ref()
        .map_or_else(BTreeSet::new, |snapshot| snapshot.zones.clone());
    let current_zones = chronic_zones.iter().cloned().collect::<BTreeSet<_>>();
    let mut zone_table = vec![vec![
        "Zone".to_owned(),
        "Bug count".to_owned(),
        "Member issues".to_owned(),
        "Churned files".to_owned(),
    ]];
    for (zone, issues, churned) in &analytics.chronic {
        zone_table.push(vec![
            zone.clone(),
            issues.len().to_string(),
            format_issues(issues),
            if churned.is_empty() {
                "None".to_owned()
            } else {
                churned.join(", ")
            },
        ]);
    }
    let mut chain_table = vec![vec![
        "From".to_owned(),
        "To".to_owned(),
        "Detector".to_owned(),
    ]];
    for (from, to, kind) in &analytics.edges {
        chain_table.push(vec![format!("#{from}"), format!("#{to}"), kind.clone()]);
    }
    let bundle_by_issue = bundles
        .iter()
        .filter_map(|bundle| {
            positive_number(bundle.get("issue_number")).map(|issue| (issue, bundle))
        })
        .collect::<BTreeMap<_, _>>();
    let mut baseline_table = vec![vec!["Issue".to_owned(), "Fix".to_owned()]];
    for issue in &analytics.baseline_issues {
        baseline_table.push(vec![
            format!("#{issue}"),
            bundle_by_issue.get(issue).map_or_else(
                || "historical".to_owned(),
                |bundle| short_sha(&string(bundle, "fix_sha")),
            ),
        ]);
    }
    let mut parts = vec![
        "# Analyze Bugs Report".to_owned(),
        String::new(),
        format!("Repo: {repo}"),
        format!("Evidence ref: {}", string_value(&manifest, "evidence_ref")),
        format!(
            "Requested: {}",
            display_json_field(&manifest, "bugs_requested")
        ),
        format!(
            "Selected: {}",
            display_json_field(&manifest, "bugs_selected")
        ),
        String::new(),
        "## Counts".to_owned(),
        String::new(),
        count_table,
        String::new(),
    ];
    if !class_open_rows.is_empty() {
        let mut table = vec![vec![
            "Issue".to_owned(),
            "Fix".to_owned(),
            "Sibling sites".to_owned(),
            "Verification".to_owned(),
        ]];
        for (bundle, sites, deep_reason) in &class_open_rows {
            let issue = positive_number(bundle.get("issue_number")).unwrap_or_default();
            let url = string(bundle, "url");
            table.push(vec![
                if url.is_empty() {
                    format!("#{issue}")
                } else {
                    format!("[#{issue}]({url})")
                },
                short_sha(&string(bundle, "fix_sha")),
                sites.join(", "),
                deep_reason.clone(),
            ]);
        }
        parts.extend([
            "## Instance fixed, class open".to_owned(),
            String::new(),
            markdown_table(&table),
            String::new(),
        ]);
    }
    if !introduced_risk_rows.is_empty() {
        let mut table = vec![vec![
            "Issue".to_owned(),
            "Stage".to_owned(),
            "Risk".to_owned(),
            "Evidence".to_owned(),
        ]];
        for (bundle, stage, risk, evidence) in &introduced_risk_rows {
            let issue = positive_number(bundle.get("issue_number")).unwrap_or_default();
            let url = string(bundle, "url");
            table.push(vec![
                if url.is_empty() {
                    format!("#{issue}")
                } else {
                    format!("[#{issue}]({url})")
                },
                stage.clone(),
                risk.clone(),
                evidence.clone(),
            ]);
        }
        parts.extend([
            "## Introduced risk".to_owned(),
            String::new(),
            markdown_table(&table),
            String::new(),
        ]);
    }
    parts.extend([
        "## Issues".to_owned(),
        String::new(),
        markdown_table(&issue_table),
        String::new(),
        "## Harness coverage gaps".to_owned(),
        String::new(),
        if coverage_gaps.is_empty() {
            "None.".to_owned()
        } else {
            let mut table = vec![vec!["Coverage gap".to_owned(), "Issues".to_owned()]];
            for (gap, issues) in &coverage_gaps {
                table.push(vec![
                    gap.clone(),
                    format_issues(&issues.iter().copied().collect::<Vec<_>>()),
                ]);
            }
            markdown_table(&table)
        },
        String::new(),
        format!(
            "Runtime selected unique SHAs: {}",
            runtime_summary
                .get("selected_unique_shas")
                .and_then(Value::as_i64)
                .unwrap_or(0)
        ),
        format!(
            "Runtime skipped unique SHAs: {}",
            runtime_summary
                .get("skipped_unique_shas")
                .and_then(Value::as_i64)
                .unwrap_or(0)
        ),
        String::new(),
        "## Chronic zones".to_owned(),
        String::new(),
        if analytics.chronic.is_empty() {
            "None.".to_owned()
        } else {
            markdown_table(&zone_table)
        },
        String::new(),
        "## Fix chains".to_owned(),
        String::new(),
        if analytics.edges.is_empty() {
            "None.".to_owned()
        } else {
            markdown_table(&chain_table)
        },
        String::new(),
        "## Baseline-extending fixes".to_owned(),
        String::new(),
        if analytics.baseline_issues.is_empty() {
            "None.".to_owned()
        } else {
            markdown_table(&baseline_table)
        },
        String::new(),
        "## Since last run".to_owned(),
        String::new(),
        if previous.is_none() {
            "First run: yes".to_owned()
        } else {
            "First run: no".to_owned()
        },
        format_issues_line(
            "Newly selected",
            &selected_issues
                .iter()
                .copied()
                .filter(|issue| !prior_selected.contains(issue))
                .collect::<Vec<_>>(),
        ),
        format_issues_line(
            "Newly verified",
            &verified_issues
                .iter()
                .copied()
                .filter(|issue| !prior_verified.contains(issue))
                .collect::<Vec<_>>(),
        ),
        format!(
            "New chain edges: {}",
            edge_ids
                .iter()
                .filter(|edge| !prior_edges.contains(*edge))
                .cloned()
                .collect::<Vec<_>>()
                .join(", ")
                .if_empty("None")
        ),
        format!(
            "Zones entering chronic status: {}",
            current_zones
                .difference(&prior_zones)
                .cloned()
                .collect::<Vec<_>>()
                .join(", ")
                .if_empty("None")
        ),
        format!(
            "Zones leaving chronic status: {}",
            prior_zones
                .difference(&current_zones)
                .cloned()
                .collect::<Vec<_>>()
                .join(", ")
                .if_empty("None")
        ),
        String::new(),
        "## Sample calibration".to_owned(),
        String::new(),
        format!(
            "Sample size: {}",
            rows.iter().filter(|row| row.sampled).count()
        ),
        format!(
            "Sampled failures: {}",
            rows.iter()
                .filter(|row| row.sampled
                    && matches!(
                        row.verdict.as_str(),
                        "INCOMPLETE" | "REGRESSED" | "NOT_FIXED" | "UNVERIFIABLE"
                    ))
                .count()
        ),
        format!(
            "Triage false-pass rate: {:.2}%",
            sampled_failure_rate(&rows) * 100.0
        ),
        String::new(),
    ]);
    if corrupt_count > 0 {
        parts.extend([
            format!("Ledger corrupt lines quarantined: {corrupt_count}"),
            String::new(),
        ]);
    }
    if !followups.is_empty()
        || !class_open_rows.is_empty()
        || sweep
            .as_ref()
            .is_some_and(|sweep| !sweep.candidates.is_empty())
    {
        parts.extend([
            "## Follow-up issue body".to_owned(),
            String::new(),
            format!("Follow-up body file: {}", path_text(&followup_path)?),
            String::new(),
        ]);
    }
    if !analytics.chronic.is_empty() {
        parts.extend([
            format!(
                "Suggestion: run /learn-from-bugs scoped to {}.",
                chronic_zones.join(", ")
            ),
            String::new(),
        ]);
    }
    let rate_model = summary
        .get("DEEP_RATE_MODEL")
        .and_then(Value::as_str)
        .unwrap_or("claude-sonnet-4-6");
    parts.push(format!(
        "ANALYZE_BUGS_COST_ESTIMATE={}",
        estimate_cost(&bundles, rate_model)
    ));
    if let Some(sweep) = &sweep {
        let mut table = vec![vec![
            "Merge".to_owned(),
            "File".to_owned(),
            "Symbol".to_owned(),
            "Severity".to_owned(),
            "Confidence".to_owned(),
            "Description".to_owned(),
        ]];
        for candidate in &sweep.candidates {
            table.push(vec![
                short_sha(&candidate.merge_sha),
                candidate.file.clone(),
                candidate.symbol.clone(),
                candidate.severity.clone(),
                candidate.confidence.clone(),
                candidate.description.clone(),
            ]);
        }
        parts.extend([
            "## Sweep candidates".to_owned(),
            String::new(),
            if sweep.candidates.is_empty() {
                "None.".to_owned()
            } else {
                markdown_table(&table)
            },
            String::new(),
            format!("Sweep selected merges: {}", sweep.selected_count),
            format!("Sweep skipped merges: {}", sweep.skipped_count),
            format!("Sweep pending frontier: {}", sweep.pending_shas.len()),
        ]);
        if sweep.coverage_incomplete {
            parts.extend([
                "Sweep coverage incomplete: pending eligible merges will be retried.".to_owned(),
                String::new(),
            ]);
        } else {
            parts.push(String::new());
        }
        parts.push(format!(
            "ANALYZE_BUGS_SWEEP_COST_ESTIMATE={}",
            estimate_sweep_cost(run_dir, &sweep.selected_manifest)?
        ));
    }
    let report = format!("{}\n", parts.join("\n"));
    private_write(&run_dir.join("report.md"), &report)?;
    write_json(
        &run_dir.join("run-state.json"),
        &json!({
            "schema_version": "1",
            "repo": repo,
            "run_id": string_value(&manifest, "run_id").if_empty(run_dir.file_name().and_then(|name| name.to_str()).unwrap_or_default()),
            "generated_at": generated_at,
            "selected_issues": selected_issues,
            "verified_issues": verified_issues,
            "chronic_zones": chronic_zones,
            "chain_edges": edge_ids,
            "verified_predicate": "certifiable-fixed-runtime-v2",
        }),
    )?;
    if let Some(sweep) = sweep {
        write_json(
            &sweep_state_path(ledger_path)?,
            &json!({
                "last_sweep_sha": sweep.pinned_tip,
                "last_sweep_at": Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string(),
                "schema_version": 1,
                "pending_shas": sweep.pending_shas,
            }),
        )?;
    }
    Ok(report)
}

fn load_runtime_results(
    path: &Path,
    bundles: &[Value],
) -> Result<BTreeMap<String, RuntimeReportResult>, String> {
    if !path.exists() {
        return Ok(BTreeMap::new());
    }
    let expected = bundles
        .iter()
        .map(|bundle| {
            (
                positive_number(bundle.get("issue_number")).unwrap_or_default(),
                string(bundle, "cache_key"),
                string(bundle, "fix_sha"),
            )
        })
        .collect::<BTreeSet<_>>();
    let text = read_lossy(path)?;
    let mut matched = BTreeMap::new();
    for line in text.lines().filter(|line| !line.trim().is_empty()) {
        let raw = serde_json::from_str::<Value>(line)
            .map_err(|_| format!("malformed runtime result artifact: {}", path.display()))?;
        let (fix_sha, bindings, result) = parse_runtime_result(&raw)
            .map_err(|()| format!("malformed runtime result artifact: {}", path.display()))?;
        for binding in bindings {
            if binding.fix_sha == fix_sha
                && expected.contains(&(binding.issue, binding.cache_key.clone(), binding.fix_sha))
                && matched
                    .insert(binding.cache_key.clone(), result.clone())
                    .is_some()
            {
                return Err(format!(
                    "duplicate current runtime result for {}",
                    binding.cache_key
                ));
            }
        }
    }
    Ok(matched)
}

fn parse_runtime_result(
    value: &Value,
) -> Result<(String, Vec<RuntimeBindingData>, RuntimeReportResult), ()> {
    let object = value.as_object().ok_or(())?;
    if !exact_keys(
        object,
        &[
            "schema_version",
            "fix_sha",
            "bindings",
            "components",
            "uncovered_zones",
        ],
    ) || string_value(object, "schema_version") != "1"
    {
        return Err(());
    }
    let fix_sha = string_value(object, "fix_sha");
    if !full_sha(&fix_sha) {
        return Err(());
    }
    let mut bindings = Vec::new();
    for item in object.get("bindings").and_then(Value::as_array).ok_or(())? {
        let binding = item.as_object().ok_or(())?;
        if !exact_keys(binding, &["issue", "cache_key", "fix_sha"]) {
            return Err(());
        }
        let issue = positive_number(binding.get("issue")).ok_or(())?;
        let cache_key = string_value(binding, "cache_key");
        let binding_sha = string_value(binding, "fix_sha");
        if !full_sha(&binding_sha) {
            return Err(());
        }
        bindings.push(RuntimeBindingData {
            issue,
            cache_key,
            fix_sha: binding_sha,
        });
    }
    let mut components = Vec::new();
    for item in object
        .get("components")
        .and_then(Value::as_array)
        .ok_or(())?
    {
        let component = item.as_object().ok_or(())?;
        if !exact_keys(component, &["name", "status", "evidence"]) {
            return Err(());
        }
        let name = string_value(component, "name");
        let status = string_value(component, "status");
        let evidence = string_value(component, "evidence");
        if !matches!(status.as_str(), "passed" | "failed" | "timeout" | "absent")
            || component.get("name").and_then(Value::as_str).is_none()
            || component.get("evidence").and_then(Value::as_str).is_none()
        {
            return Err(());
        }
        components.push(RuntimeComponentData {
            name,
            status,
            evidence,
        });
    }
    let mut uncovered_zones = Vec::new();
    for zone in object
        .get("uncovered_zones")
        .and_then(Value::as_array)
        .ok_or(())?
    {
        let zone = zone.as_str().filter(|zone| !zone.is_empty()).ok_or(())?;
        uncovered_zones.push(zone.to_owned());
    }
    Ok((
        fix_sha,
        bindings,
        RuntimeReportResult {
            components,
            uncovered_zones,
        },
    ))
}

fn exact_keys(object: &Map<String, Value>, expected: &[&str]) -> bool {
    object.len() == expected.len() && expected.iter().all(|key| object.contains_key(*key))
}

fn report_record_for_bundle<'a>(
    ledger: &'a BTreeMap<String, Value>,
    bundle: &Value,
) -> Option<&'a Value> {
    required_evidence_complete(bundle).then_some(())?;
    let record = ledger.get(&string(bundle, "cache_key"))?;
    (string(record, "fix_sha") == string(bundle, "fix_sha")
        && string(record, "later_history_hash") == string(bundle, "later_history_hash"))
    .then_some(record)
}

fn required_evidence_complete(bundle: &Value) -> bool {
    [
        "diff_scan_status",
        "consumer_scan_status",
        "later_history_scan_status",
        "revert_scan_status",
    ]
    .into_iter()
    .all(|field| bundle.get(field).and_then(Value::as_str).unwrap_or(SCAN_OK) == SCAN_OK)
}

#[allow(clippy::too_many_lines)] // Verdict precedence mirrors the public Python artifact contract.
fn final_verdict(
    bundle: &Value,
    record: Option<&Value>,
) -> (String, String, String, Vec<String>, bool) {
    if !required_evidence_complete(bundle) {
        let incomplete = [
            ("fix-diff", "diff_scan_status", "diff_scan_reason"),
            ("consumer", "consumer_scan_status", "consumer_scan_reason"),
            (
                "later-history",
                "later_history_scan_status",
                "later_history_scan_reason",
            ),
            ("revert", "revert_scan_status", "revert_scan_reason"),
        ]
        .into_iter()
        .filter_map(|(name, status, reason)| {
            let status = bundle
                .get(status)
                .and_then(Value::as_str)
                .unwrap_or(SCAN_OK);
            (status != SCAN_OK).then(|| {
                let reason = string(bundle, reason);
                format!(
                    "{name} ({})",
                    if reason.is_empty() { status } else { &reason }
                )
            })
        })
        .collect::<Vec<_>>();
        return (
            "NEEDS_DEEP".to_owned(),
            "MECH".to_owned(),
            format!("required evidence incomplete: {}", incomplete.join("; ")),
            Vec::new(),
            false,
        );
    }
    if let Some(record) = record {
        let deep = string(record, "deep_verdict");
        if !deep.is_empty() {
            return (
                deep,
                "DEEP".to_owned(),
                string(record, "deep_reason"),
                Vec::new(),
                record
                    .get("sampled")
                    .and_then(Value::as_bool)
                    .unwrap_or(false),
            );
        }
    }
    let mechanical = string(bundle, "mechanical_verdict");
    if !mechanical.is_empty() && mechanical != "NEEDS_DEEP" {
        return (
            mechanical,
            "MECH".to_owned(),
            string(bundle, "mechanical_reason"),
            Vec::new(),
            false,
        );
    }
    if let Some(record) = record {
        let triage = string(record, "triage_verdict");
        let triage_complete = stage_complete(record, "triage")
            && record
                .get("triage_evidence_verified")
                .and_then(Value::as_bool)
                .unwrap_or(false);
        if triage_complete && !triage.is_empty() {
            let needs_deep = matches!(triage.as_str(), "SUSPECT" | "NEEDS_DEEP")
                || record
                    .get("triage_needs_deep")
                    .and_then(Value::as_bool)
                    .unwrap_or(false);
            return (
                if needs_deep {
                    "NEEDS_DEEP".to_owned()
                } else {
                    triage
                },
                "TRIAGE".to_owned(),
                string(record, "triage_reason"),
                string_array(record, "triage_missing_items"),
                record
                    .get("sampled")
                    .and_then(Value::as_bool)
                    .unwrap_or(false),
            );
        }
    }
    if !mechanical.is_empty() {
        return (
            mechanical,
            "MECH".to_owned(),
            string(bundle, "mechanical_reason"),
            Vec::new(),
            false,
        );
    }
    (
        "NEEDS_DEEP".to_owned(),
        String::new(),
        "not yet triaged".to_owned(),
        Vec::new(),
        false,
    )
}

fn stage_complete(record: &Value, stage: &str) -> bool {
    record
        .get("stages_complete")
        .and_then(Value::as_array)
        .is_some_and(|stages| stages.iter().any(|value| value.as_str() == Some(stage)))
}

fn runtime_overlay(
    verdict: &str,
    tier: &str,
    reason: &str,
    result: &RuntimeReportResult,
) -> (String, String, String, Vec<String>) {
    let annotations = result
        .uncovered_zones
        .iter()
        .map(|zone| format!("UNVERIFIED_RUNTIME: no harness covers {zone}"))
        .collect::<Vec<_>>();
    let failures = result
        .components
        .iter()
        .filter(|component| matches!(component.status.as_str(), "failed" | "timeout"))
        .map(|component| {
            format!(
                "{} {}: {}",
                component.name, component.status, component.evidence
            )
            .trim_end_matches(": ")
            .to_owned()
        })
        .collect::<Vec<_>>();
    if !failures.is_empty() {
        return (
            "SUSPECT".to_owned(),
            "RUNTIME".to_owned(),
            failures.join("; "),
            annotations,
        );
    }
    let executed = result
        .components
        .iter()
        .any(|component| component.status == "passed");
    if executed && matches!(verdict, "CONFIRMED_FIXED" | "FIXED_CLEAR" | "FIXED_LIKELY") {
        return (
            verdict.to_owned(),
            "RUNTIME".to_owned(),
            reason.to_owned(),
            annotations,
        );
    }
    (
        verdict.to_owned(),
        tier.to_owned(),
        reason.to_owned(),
        annotations,
    )
}

fn verified_issue(verdict: &str, tier: &str) -> bool {
    matches!(tier, "TRIAGE" | "DEEP" | "RUNTIME")
        && matches!(verdict, "CONFIRMED_FIXED" | "FIXED_CLEAR" | "FIXED_LIKELY")
}

fn current_ledger_schema(record: &Value) -> bool {
    record.as_object().is_some_and(|object| {
        [
            "triage_introduced_risk",
            "triage_introduced_risk_reason",
            "deep_introduced_risk",
            "deep_introduced_risk_reason",
            "class_complete",
            "sibling_sites",
            "legacy_schema",
        ]
        .into_iter()
        .all(|field| object.contains_key(field))
            && !object
                .get("legacy_schema")
                .and_then(Value::as_bool)
                .unwrap_or(false)
    })
}

fn selected_introduced_risk(record: Option<&Value>) -> Option<(String, String, String)> {
    let record = record?;
    if !current_ledger_schema(record) {
        return None;
    }
    for (stage, risk, reason) in [
        (
            "DEEP",
            "deep_introduced_risk",
            "deep_introduced_risk_reason",
        ),
        (
            "TRIAGE",
            "triage_introduced_risk",
            "triage_introduced_risk_reason",
        ),
    ] {
        if stage_complete(record, stage.to_ascii_lowercase().as_str()) {
            let risk = string(record, risk);
            let reason = string(record, reason);
            if !risk.is_empty() && !reason.is_empty() {
                return Some((stage.to_owned(), risk, reason));
            }
        }
    }
    None
}

fn class_open_siblings(record: Option<&Value>) -> Option<Vec<String>> {
    let record = record?;
    if !current_ledger_schema(record)
        || !stage_complete(record, "deep")
        || string(record, "deep_verdict") != "CONFIRMED_FIXED"
        || record
            .get("class_complete")
            .and_then(Value::as_bool)
            .unwrap_or(false)
    {
        return None;
    }
    let sites = string_array(record, "sibling_sites");
    (!sites.is_empty() && sites.iter().all(|site| SIBLING_SITE.is_match(site))).then_some(sites)
}

#[allow(clippy::too_many_lines)] // The time windows and graph passes intentionally stay in report order.
fn analytics_view(
    manifest: &Map<String, Value>,
    bundles: &[Value],
    ledger: &BTreeMap<String, Value>,
) -> AnalyticsViewData {
    let generated_at = manifest
        .get("generated_at")
        .and_then(Value::as_i64)
        .unwrap_or(0);
    let window_start = generated_at.saturating_sub(14 * 86_400);
    let mut records = BTreeMap::new();
    for record in ledger.values() {
        let Some(issue) = positive_number(record.get("issue")) else {
            continue;
        };
        let current = analytics_record_from_ledger(record, false);
        if current.fix_sha.is_empty()
            && !(window_start < current.fix_time && current.fix_time <= generated_at)
        {
            continue;
        }
        let replace = records
            .get(&issue)
            .is_none_or(|previous: &AnalyticsRecordData| {
                let next_updated = record
                    .get("updated_at")
                    .and_then(Value::as_i64)
                    .unwrap_or(0);
                let previous_updated = ledger
                    .get(&previous.cache_key)
                    .and_then(|value| value.get("updated_at"))
                    .and_then(Value::as_i64)
                    .unwrap_or(0);
                (next_updated, current.cache_key.as_str())
                    > (previous_updated, previous.cache_key.as_str())
            });
        if replace {
            records.insert(issue, current);
        }
    }
    for bundle in bundles {
        let issue = positive_number(bundle.get("issue_number")).unwrap_or_default();
        let record = report_record_for_bundle(ledger, bundle);
        records.insert(issue, analytics_record_from_bundle(bundle, record));
    }
    records.retain(|_, record| {
        record.active || (window_start < record.fix_time && record.fix_time <= generated_at)
    });
    let mut edges = BTreeSet::new();
    for record in records.values() {
        for reference in &record.marker_references {
            if *reference != record.issue {
                edges.insert((record.issue, *reference, "marker".to_owned()));
            }
        }
    }
    let mut ordered = records
        .values()
        .filter(|record| record.fix_time != 0)
        .cloned()
        .collect::<Vec<_>>();
    ordered.sort_by_key(|record| (record.fix_time, record.issue));
    for (index, newer) in ordered.iter().enumerate() {
        let newer_files = newer.touched_files.iter().collect::<BTreeSet<_>>();
        if newer_files.is_empty() {
            continue;
        }
        for prior in &ordered[..index] {
            if newer.issue == prior.issue
                || newer.fix_sha == prior.fix_sha
                || newer.fix_time.saturating_sub(prior.fix_time) >= 14 * 86_400
            {
                continue;
            }
            if prior
                .touched_files
                .iter()
                .any(|path| newer_files.contains(path))
            {
                edges.insert((newer.issue, prior.issue, "file_intersection".to_owned()));
            }
        }
    }
    let edges = edges.into_iter().collect::<Vec<_>>();
    let seven_day_start = generated_at.saturating_sub(7 * 86_400);
    let mut commits_by_file: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for record in records.values() {
        if record.fix_sha.is_empty()
            || !(seven_day_start < record.fix_time && record.fix_time <= generated_at)
        {
            continue;
        }
        for path in &record.touched_files {
            commits_by_file
                .entry(path.clone())
                .or_default()
                .insert(record.fix_sha.clone());
        }
    }
    let churned_files = commits_by_file
        .into_iter()
        .filter_map(|(path, commits)| (commits.len() >= 3).then_some(path))
        .collect::<Vec<_>>();
    let mut zone_members: BTreeMap<String, BTreeSet<u64>> = BTreeMap::new();
    for record in records.values() {
        if record.fix_time == 0
            || !(window_start < record.fix_time && record.fix_time <= generated_at)
        {
            continue;
        }
        for zone in &record.zones {
            zone_members
                .entry(zone.clone())
                .or_default()
                .insert(record.issue);
        }
    }
    let record_issues = records.keys().copied().collect::<BTreeSet<_>>();
    let components = chain_components(
        &edges
            .iter()
            .filter(|(from, to, _)| record_issues.contains(from) && record_issues.contains(to))
            .cloned()
            .collect::<Vec<_>>(),
    );
    let mut chronic = Vec::new();
    for (zone, members) in zone_members {
        let connected = components
            .iter()
            .any(|component| component.intersection(&members).count() >= 2);
        if members.len() >= 3 || connected {
            let zone_churn = churned_files
                .iter()
                .filter(|path| zones_for_files(&[(*path).clone()]).contains(&zone))
                .cloned()
                .collect::<Vec<_>>();
            chronic.push((zone, members.into_iter().collect(), zone_churn));
        }
    }
    let baseline_issues = records
        .values()
        .filter(|record| record.baseline_extended)
        .map(|record| record.issue)
        .collect::<Vec<_>>();
    AnalyticsViewData {
        edges,
        chronic,
        baseline_issues,
    }
}

fn analytics_record_from_bundle(bundle: &Value, record: Option<&Value>) -> AnalyticsRecordData {
    let bundle_files = string_array(bundle, "touched_files");
    let record_files = record.map_or_else(Vec::new, |record| string_array(record, "touched_files"));
    let touched_files = if bundle_files.is_empty() {
        record_files
    } else {
        bundle_files
    };
    let bundle_time = signed_number(bundle.get("fix_time"));
    let record_time = record.map_or(0, |record| signed_number(record.get("fix_time")));
    let bundle_markers = positive_numbers(bundle.get("marker_references"));
    let record_markers = record.map_or_else(Vec::new, |record| {
        positive_numbers(record.get("marker_references"))
    });
    let zones = string_array(bundle, "zones");
    let zones = if zones.is_empty() {
        record
            .map(|record| string_array(record, "zones"))
            .filter(|zones| !zones.is_empty())
            .unwrap_or_else(|| zones_for_files(&touched_files))
    } else {
        zones
    };
    AnalyticsRecordData {
        issue: positive_number(bundle.get("issue_number")).unwrap_or_default(),
        cache_key: string(bundle, "cache_key"),
        fix_sha: string(bundle, "fix_sha"),
        touched_files: touched_files.clone(),
        fix_time: if bundle_time != 0 {
            bundle_time
        } else {
            record_time
        },
        marker_references: if bundle_markers.is_empty() {
            record_markers
        } else {
            bundle_markers
        },
        zones,
        baseline_extended: bundle
            .get("baseline_extended")
            .and_then(Value::as_bool)
            .unwrap_or(false)
            || record
                .and_then(|record| record.get("baseline_extended"))
                .and_then(Value::as_bool)
                .unwrap_or(false)
            || touched_files.iter().any(|path| is_baseline_path(path)),
        active: true,
    }
}

fn analytics_record_from_ledger(record: &Value, active: bool) -> AnalyticsRecordData {
    let touched_files = string_array(record, "touched_files");
    let zones = string_array(record, "zones");
    AnalyticsRecordData {
        issue: positive_number(record.get("issue")).unwrap_or_default(),
        cache_key: string(record, "cache_key"),
        fix_sha: string(record, "fix_sha"),
        touched_files: touched_files.clone(),
        fix_time: signed_number(record.get("fix_time")),
        marker_references: positive_numbers(record.get("marker_references")),
        zones: if zones.is_empty() {
            zones_for_files(&touched_files)
        } else {
            zones
        },
        baseline_extended: record
            .get("baseline_extended")
            .and_then(Value::as_bool)
            .unwrap_or(false)
            || touched_files.iter().any(|path| is_baseline_path(path)),
        active,
    }
}

fn signed_number(value: Option<&Value>) -> i64 {
    value
        .and_then(Value::as_i64)
        .or_else(|| {
            value
                .and_then(Value::as_u64)
                .and_then(|value| i64::try_from(value).ok())
        })
        .unwrap_or(0)
}

fn positive_numbers(value: Option<&Value>) -> Vec<u64> {
    value
        .and_then(Value::as_array)
        .map(|values| {
            values
                .iter()
                .filter_map(|value| value.as_u64().filter(|value| *value > 0))
                .collect::<BTreeSet<_>>()
                .into_iter()
                .collect()
        })
        .unwrap_or_default()
}

fn chain_components(edges: &[(u64, u64, String)]) -> Vec<BTreeSet<u64>> {
    let mut adjacency: BTreeMap<u64, BTreeSet<u64>> = BTreeMap::new();
    for (from, to, _) in edges {
        adjacency.entry(*from).or_default().insert(*to);
        adjacency.entry(*to).or_default().insert(*from);
    }
    let mut seen = BTreeSet::new();
    let mut components = Vec::new();
    for issue in adjacency.keys().copied() {
        if !seen.insert(issue) {
            continue;
        }
        let mut pending = vec![issue];
        let mut component = BTreeSet::new();
        while let Some(current) = pending.pop() {
            if !component.insert(current) {
                continue;
            }
            if let Some(next) = adjacency.get(&current) {
                pending.extend(next.iter().copied());
            }
        }
        seen.extend(component.iter().copied());
        components.push(component);
    }
    components
}

struct SnapshotData {
    generated_at: i64,
    run_id: String,
    selected: BTreeSet<u64>,
    verified: BTreeSet<u64>,
    zones: BTreeSet<String>,
    edges: BTreeSet<String>,
}

fn previous_snapshot(run_dir: &Path, repo: &str, generated_at: i64) -> Option<SnapshotData> {
    let root = run_dir.parent()?;
    let entries = fs::read_dir(root).ok()?;
    entries
        .filter_map(Result::ok)
        .filter_map(|entry| snapshot_from_path(&entry.path().join("run-state.json")))
        .filter(|snapshot| snapshot.0 == repo && snapshot.1.generated_at < generated_at)
        .map(|(_, snapshot)| snapshot)
        .max_by(|left, right| {
            (left.generated_at, left.run_id.as_str())
                .cmp(&(right.generated_at, right.run_id.as_str()))
        })
}

fn snapshot_from_path(path: &Path) -> Option<(String, SnapshotData)> {
    let value = load_json(path, MAX_MANIFEST_BYTES).ok()?;
    let object = value.as_object()?;
    if !exact_keys(
        object,
        &[
            "schema_version",
            "repo",
            "run_id",
            "generated_at",
            "selected_issues",
            "verified_issues",
            "chronic_zones",
            "chain_edges",
            "verified_predicate",
        ],
    ) || string_value(object, "schema_version") != "1"
        || string_value(object, "verified_predicate") != "certifiable-fixed-runtime-v2"
    {
        return None;
    }
    let numbers = |field: &str| {
        object
            .get(field)
            .and_then(Value::as_array)
            .and_then(|values| {
                values
                    .iter()
                    .map(Value::as_u64)
                    .collect::<Option<BTreeSet<_>>>()
            })
    };
    let strings = |field: &str| {
        object
            .get(field)
            .and_then(Value::as_array)
            .and_then(|values| {
                values
                    .iter()
                    .map(|value| value.as_str().map(str::to_owned))
                    .collect::<Option<BTreeSet<_>>>()
            })
    };
    Some((
        string_value(object, "repo"),
        SnapshotData {
            generated_at: signed_number(object.get("generated_at")),
            run_id: string_value(object, "run_id"),
            selected: numbers("selected_issues")?,
            verified: numbers("verified_issues")?,
            zones: strings("chronic_zones")?,
            edges: strings("chain_edges")?,
        },
    ))
}

fn report_counts(rows: &[ReportRow]) -> (usize, usize, usize, usize, usize, usize, usize, usize) {
    let count = |verdict: &str| rows.iter().filter(|row| row.verdict == verdict).count();
    (
        rows.len(),
        rows.iter()
            .filter(|row| {
                matches!(
                    row.verdict.as_str(),
                    "CONFIRMED_FIXED" | "FIXED_CLEAR" | "FIXED_LIKELY"
                )
            })
            .count(),
        count("NEEDS_DEEP"),
        count("NOT_FIXED"),
        count("INCOMPLETE"),
        count("REGRESSED"),
        count("WONTFIX"),
        count("UNVERIFIABLE"),
    )
}

fn markdown_table(rows: &[Vec<String>]) -> String {
    let Some(header) = rows.first() else {
        return String::new();
    };
    let mut output = vec![
        format!("| {} |", header.join(" | ")),
        format!(
            "| {} |",
            std::iter::repeat_n("---", header.len())
                .collect::<Vec<_>>()
                .join(" | ")
        ),
    ];
    output.extend(rows.iter().skip(1).map(|row| {
        format!(
            "| {} |",
            row.iter()
                .map(|cell| cell.replace('\n', " ").replace('|', "\\|"))
                .collect::<Vec<_>>()
                .join(" | ")
        )
    }));
    output.join("\n")
}

fn short_sha(sha: &str) -> String {
    sha.chars().take(12).collect()
}

fn format_issues(values: &[u64]) -> String {
    if values.is_empty() {
        "None".to_owned()
    } else {
        values
            .iter()
            .map(|issue| format!("#{issue}"))
            .collect::<Vec<_>>()
            .join(", ")
    }
}

fn format_issues_line(label: &str, values: &[u64]) -> String {
    format!("{label}: {}", format_issues(values))
}

fn display_json_field(object: &Map<String, Value>, field: &str) -> String {
    object
        .get(field)
        .map_or_else(String::new, |value| match value {
            Value::String(value) => value.clone(),
            _ => value.to_string(),
        })
}

#[allow(clippy::cast_precision_loss)] // The report prints a bounded sample ratio to two decimals.
fn sampled_failure_rate(rows: &[ReportRow]) -> f64 {
    let sampled = rows.iter().filter(|row| row.sampled).collect::<Vec<_>>();
    if sampled.is_empty() {
        0.0
    } else {
        let failures = sampled
            .iter()
            .filter(|row| {
                matches!(
                    row.verdict.as_str(),
                    "INCOMPLETE" | "REGRESSED" | "NOT_FIXED" | "UNVERIFIABLE"
                )
            })
            .count();
        failures as f64 / sampled.len() as f64
    }
}

#[allow(clippy::cast_precision_loss, clippy::suboptimal_flops)] // This is an explicitly approximate, bounded offline cost estimate.
fn estimate_cost(bundles: &[Value], model: &str) -> String {
    let characters = bundles
        .iter()
        .map(|bundle| string(bundle, "bundle_path"))
        .filter(|path| !path.is_empty())
        .filter_map(|path| fs::read(path).ok())
        .map(|bytes| String::from_utf8_lossy(&bytes).chars().count())
        .sum::<usize>();
    let (input_rate, output_rate) = match model {
        "claude-sonnet-4-6" => (3.0, 15.0),
        "claude-fable-5" => (10.0, 50.0),
        _ => (5.0, 25.0),
    };
    let input_tokens = characters as f64 / 4.0;
    let output_tokens = bundles.len() as f64 * 400.0;
    format!(
        "${:.2} estimated",
        (input_tokens / 1_000_000.0 * input_rate) + (output_tokens / 1_000_000.0 * output_rate)
    )
}

fn sweep_state_path(ledger_path: &Path) -> Result<PathBuf, String> {
    let ledger_path = if ledger_path.is_absolute() {
        ledger_path.to_path_buf()
    } else {
        env::current_dir()
            .map_err(|error| format!("could not resolve sweep state path: {error}"))?
            .join(ledger_path)
    };
    let parent = ledger_path
        .parent()
        .ok_or_else(|| "ledger path has no parent for sweep state".to_owned())?;
    let parent = if parent.exists() {
        fs::canonicalize(parent)
            .map_err(|error| format!("could not resolve sweep state path: {error}"))?
    } else {
        parent.to_path_buf()
    };
    Ok(parent.join("sweep-state.json"))
}

#[allow(clippy::too_many_lines)] // Every coupled sweep artifact field must be checked before report state advances.
fn load_validated_sweep(run_dir: &Path) -> Result<Option<SweepReportData>, String> {
    const VALIDATED: &str = "sweep-validated.json";
    const SELECTED: &str = "sweep-selected-merges.json";
    let artifact_path = run_dir.join(VALIDATED);
    if !artifact_path.exists() {
        return Ok(None);
    }
    let raw = load_json(&artifact_path, MAX_MANIFEST_BYTES)?;
    let artifact = raw.as_object().ok_or_else(|| {
        format!(
            "malformed validated sweep artifact keys: {}",
            artifact_path.display()
        )
    })?;
    if !exact_keys(
        artifact,
        &[
            "pinned_tip",
            "selected_manifest_path",
            "selected_count",
            "skipped_count",
            "pending_shas",
            "coverage_incomplete",
            "candidates",
        ],
    ) {
        return Err(format!(
            "malformed validated sweep artifact keys: {}",
            artifact_path.display()
        ));
    }
    let selected_path = run_dir.join(SELECTED);
    let expected_path = fs::canonicalize(&selected_path).map_err(|_| {
        format!(
            "selected-merge manifest missing: {}",
            selected_path.display()
        )
    })?;
    let declared_path = artifact
        .get("selected_manifest_path")
        .and_then(Value::as_str)
        .ok_or_else(|| {
            "validated sweep artifact has a foreign selected manifest path".to_owned()
        })?;
    if fs::canonicalize(declared_path).ok().as_deref() != Some(expected_path.as_path()) {
        return Err("validated sweep artifact has a foreign selected manifest path".to_owned());
    }
    let selected_manifest = load_json(&expected_path, MAX_MANIFEST_BYTES)?;
    let selected = selected_manifest
        .as_object()
        .ok_or_else(|| "selected sweep manifest has unexpected keys".to_owned())?;
    if !exact_keys(
        selected,
        &[
            "pinned_tip",
            "selected_count",
            "skipped_count",
            "coverage_incomplete",
            "pending_shas",
            "selected",
        ],
    ) {
        return Err("selected sweep manifest has unexpected keys".to_owned());
    }
    let selected_tip =
        required_sweep_sha(selected.get("pinned_tip"), "selected manifest pinned_tip")?;
    let selected_rows = selected
        .get("selected")
        .and_then(Value::as_array)
        .ok_or_else(|| "selected sweep manifest lacks selected array".to_owned())?;
    let mut selected_shas = BTreeSet::new();
    for row in selected_rows {
        let row = row
            .as_object()
            .ok_or_else(|| "selected sweep manifest entry is not an object".to_owned())?;
        selected_shas.insert(required_sweep_sha(
            row.get("merge_sha"),
            "selected merge_sha",
        )?);
    }
    if selected_shas.len() != selected_rows.len() {
        return Err("selected sweep manifest has duplicate selected merge SHAs".to_owned());
    }
    let selected_count = required_count(selected.get("selected_count"), "selected sweep manifest")?;
    let skipped_count = required_count(selected.get("skipped_count"), "selected sweep manifest")?;
    let coverage_incomplete = selected
        .get("coverage_incomplete")
        .and_then(Value::as_bool)
        .ok_or_else(|| "selected sweep manifest has malformed coverage fields".to_owned())?;
    let manifest_pending = sweep_shas(selected.get("pending_shas"), "selected sweep pending SHA")?;
    if selected_count != selected_rows.len() as u64
        || skipped_count != manifest_pending.len() as u64
        || coverage_incomplete == manifest_pending.is_empty()
    {
        return Err("selected sweep manifest has inconsistent coverage fields".to_owned());
    }
    let pinned_tip = required_sweep_sha(artifact.get("pinned_tip"), "validated sweep pinned_tip")?;
    let artifact_selected_count =
        required_count(artifact.get("selected_count"), "validated sweep artifact")?;
    let artifact_skipped_count =
        required_count(artifact.get("skipped_count"), "validated sweep artifact")?;
    let artifact_coverage = artifact
        .get("coverage_incomplete")
        .and_then(Value::as_bool)
        .ok_or_else(|| "malformed validated sweep artifact coverage fields".to_owned())?;
    let pending_shas = sweep_shas(artifact.get("pending_shas"), "validated sweep pending SHA")?;
    if pinned_tip != selected_tip
        || artifact_selected_count != selected_count
        || artifact_skipped_count != skipped_count
        || artifact_coverage != coverage_incomplete
        || pending_shas != manifest_pending
    {
        return Err(
            "validated sweep artifact coverage does not match selected manifest".to_owned(),
        );
    }
    let candidates = artifact
        .get("candidates")
        .and_then(Value::as_array)
        .ok_or_else(|| "validated sweep artifact candidates must be an array".to_owned())?
        .iter()
        .map(|value| sweep_candidate(value, &selected_shas))
        .collect::<Result<Vec<_>, _>>()?;
    let cwd = sweep_repository_root()?;
    let repository = GixRepository::discover(&cwd)
        .map_err(|_| "could not resolve current origin/main for sweep report".to_owned())?;
    let current_tip = repository
        .resolve_revision(&Revision::new(b"origin/main"))
        .map_err(|_| "could not resolve current origin/main for sweep report".to_owned())?
        .to_hex();
    if !full_sha(&current_tip) || current_tip != pinned_tip {
        return Err("validated sweep artifact is stale for the current origin/main tip".to_owned());
    }
    Ok(Some(SweepReportData {
        pinned_tip,
        selected_count,
        skipped_count,
        pending_shas,
        coverage_incomplete,
        candidates,
        selected_manifest,
    }))
}

fn sweep_repository_root() -> Result<PathBuf, String> {
    #[cfg(test)]
    if let Some(root) = SWEEP_REPOSITORY_ROOT.with(|root| root.borrow().clone()) {
        return Ok(root);
    }
    env::current_dir().map_err(|error| format!("sweep report tip verification failed: {error}"))
}

#[cfg(test)]
struct SweepRepositoryRootGuard {
    previous: Option<PathBuf>,
}

#[cfg(test)]
impl Drop for SweepRepositoryRootGuard {
    fn drop(&mut self) {
        SWEEP_REPOSITORY_ROOT.with(|root| {
            root.replace(self.previous.take());
        });
    }
}

#[cfg(test)]
fn test_sweep_repository_root(root: &Path) -> SweepRepositoryRootGuard {
    let previous = SWEEP_REPOSITORY_ROOT.with(|current| current.replace(Some(root.to_path_buf())));
    SweepRepositoryRootGuard { previous }
}

fn required_sweep_sha(value: Option<&Value>, label: &str) -> Result<String, String> {
    let value = value
        .and_then(Value::as_str)
        .filter(|value| full_sha(value))
        .ok_or_else(|| format!("{label} must be a full 40-character lowercase SHA"))?;
    Ok(value.to_owned())
}

fn required_count(value: Option<&Value>, label: &str) -> Result<u64, String> {
    value
        .and_then(Value::as_u64)
        .ok_or_else(|| format!("{label} has malformed coverage fields"))
}

fn sweep_shas(value: Option<&Value>, label: &str) -> Result<Vec<String>, String> {
    let values = value
        .and_then(Value::as_array)
        .ok_or_else(|| format!("{label}s must be an array"))?;
    let values = values
        .iter()
        .map(|value| required_sweep_sha(Some(value), label))
        .collect::<Result<Vec<_>, _>>()?;
    if values.iter().collect::<BTreeSet<_>>().len() != values.len() {
        return Err(format!("{label}s has duplicate SHAs"));
    }
    Ok(values)
}

fn sweep_candidate(
    value: &Value,
    selected: &BTreeSet<String>,
) -> Result<SweepCandidateData, String> {
    let value = value
        .as_object()
        .ok_or_else(|| "validated sweep artifact candidate is not an object".to_owned())?;
    if !exact_keys(
        value,
        &[
            "merge_sha",
            "file",
            "symbol",
            "description",
            "severity",
            "confidence",
        ],
    ) {
        return Err(
            "validated sweep artifact candidate has unexpected or missing fields".to_owned(),
        );
    }
    let merge_sha = required_sweep_sha(
        value.get("merge_sha"),
        "validated sweep candidate merge_sha",
    )?;
    if !selected.contains(&merge_sha) {
        return Err("validated sweep artifact candidate belongs to an unselected merge".to_owned());
    }
    let file = value
        .get("file")
        .and_then(Value::as_str)
        .filter(|file| safe_sweep_path(file) && file.len() <= 512)
        .ok_or_else(|| "validated sweep artifact candidate has invalid file".to_owned())?;
    let symbol = sweep_text(value.get("symbol"), 200, "symbol")?;
    let description = sweep_text(value.get("description"), 2_000, "description")?;
    let severity = value
        .get("severity")
        .and_then(Value::as_str)
        .filter(|value| matches!(*value, "high" | "medium" | "low"))
        .ok_or_else(|| "validated sweep artifact candidate has invalid severity".to_owned())?;
    let confidence = value
        .get("confidence")
        .and_then(Value::as_str)
        .filter(|value| matches!(*value, "high" | "medium" | "low"))
        .ok_or_else(|| "validated sweep artifact candidate has invalid confidence".to_owned())?;
    Ok(SweepCandidateData {
        merge_sha,
        file: file.to_owned(),
        symbol,
        description,
        severity: severity.to_owned(),
        confidence: confidence.to_owned(),
    })
}

fn sweep_text(value: Option<&Value>, limit: usize, label: &str) -> Result<String, String> {
    let value = value
        .and_then(Value::as_str)
        .filter(|value| value.len() <= limit && !value.contains('\0'))
        .ok_or_else(|| format!("validated sweep artifact candidate has invalid {label}"))?;
    Ok(value
        .chars()
        .filter(|character| *character == '\t' || *character == '\n' || !character.is_control())
        .collect::<String>()
        .trim()
        .to_owned())
}

#[allow(clippy::cast_precision_loss, clippy::suboptimal_flops)] // This is an explicitly approximate, bounded offline cost estimate.
fn estimate_sweep_cost(run_dir: &Path, manifest: &Value) -> Result<String, String> {
    let selected = manifest
        .get("selected")
        .and_then(Value::as_array)
        .ok_or_else(|| {
            "selected sweep manifest lacks selected array for cost estimate".to_owned()
        })?;
    let run_dir = fs::canonicalize(run_dir)
        .map_err(|error| format!("could not resolve active run directory: {error}"))?;
    let mut finder_chars = 0usize;
    for row in selected {
        let row = row.as_object().ok_or_else(|| {
            "selected sweep manifest has non-object entry for cost estimate".to_owned()
        })?;
        let path = row
            .get("bundle_path")
            .and_then(Value::as_str)
            .ok_or_else(|| {
                "selected sweep manifest lacks bundle path for cost estimate".to_owned()
            })?;
        let path = fs::canonicalize(path)
            .map_err(|error| format!("could not read sweep bundle for cost estimate: {error}"))?;
        if path.parent() != Some(run_dir.as_path()) {
            return Err(
                "selected sweep manifest has a bundle outside the active run directory".to_owned(),
            );
        }
        finder_chars = finder_chars.saturating_add(
            String::from_utf8_lossy(&fs::read(path).map_err(|error| error.to_string())?)
                .chars()
                .count(),
        );
    }
    let queue = run_dir.join("sweep-refuter-queue.jsonl");
    let (queue_chars, queue_rows) = if queue.exists() {
        let text = String::from_utf8_lossy(&fs::read(&queue).map_err(|error| error.to_string())?)
            .into_owned();
        let rows = text
            .lines()
            .filter(|line| !line.trim().is_empty())
            .map(serde_json::from_str::<Map<String, Value>>)
            .collect::<Result<Vec<_>, _>>()
            .map_err(|_| "malformed sweep refuter queue for cost estimate".to_owned())?;
        (text.chars().count(), rows.len())
    } else {
        (0, 0)
    };
    let input_tokens = (finder_chars + queue_chars) as f64 / 4.0;
    let output_tokens = selected.len() as f64 * 400.0 + queue_rows as f64 * 80.0;
    Ok(format!(
        "${:.2} estimated",
        input_tokens / 1_000_000.0 * 3.0 + output_tokens / 1_000_000.0 * 15.0
    ))
}

#[cfg(test)]
mod tests {
    use std::{
        ffi::OsString,
        fs,
        process::ExitCode,
        sync::{Arc, Barrier},
    };

    use super::{
        SIBLING_SITE, append_records, bundle_for_issue, cap_text, changed_symbols,
        closure_pull_numbers, compute, cross_language_consumer, deep_candidates,
        excluded_consumer_path, find_fix, has_exact_issue_reference, hydrate_evidence, ingest,
        is_baseline_path, ledger, load_ledger, load_runtime_results, marker_evidence,
        metadata_record, model_alias, path_text, prefetch, prefetch_with_evidence, render_report,
        report, repository_path_text, required_evidence_complete, runtime, runtime_verify,
        sanitize_repo, test_sweep_repository_root, validate_agent_row, validate_evidence_token,
        zones_for_files,
    };
    use crate::github_service::with_test_github_service;
    use larch_adapters::{GixRepository, github::OctocrabGitHubService, unified_blob_diff};
    use larch_core::{
        BUG_PREFIX, GitHubIssue, GitHubIssueState, GitPath, RepositoryRead, Revision,
    };
    use larch_test_support::{GitFixture, GitRepository, IssueServiceExchange, IssueServiceStub};
    use serde_json::{Value, json};

    fn write_ingest_fixture(
        root: &std::path::Path,
        evidence_status: &str,
    ) -> (std::path::PathBuf, std::path::PathBuf, std::path::PathBuf) {
        let run_dir = root.join("run");
        fs::create_dir_all(&run_dir).expect("run directory");
        let bundle = run_dir.join("issue-1-bundle.md");
        fs::write(&bundle, "# Bundle\nevidence_token: proof-token\n\nbody\n").expect("bundle");
        let manifest = run_dir.join("manifest.json");
        fs::write(
            &manifest,
            json!({
                "issues": [{
                    "issue_number": 1,
                    "cache_key": "cache-key",
                    "fix_sha": "f".repeat(40),
                    "later_history_hash": "later",
                    "bundle_path": bundle,
                    "diff_scan_status": evidence_status,
                    "consumer_scan_status": evidence_status,
                    "later_history_scan_status": evidence_status,
                    "revert_scan_status": evidence_status,
                }]
            })
            .to_string(),
        )
        .expect("manifest");
        fs::write(
            run_dir.join("triage-pending-1.jsonl"),
            "{\"issue\":1,\"cache_key\":\"cache-key\",\"bundle_path\":\"bundle\"}\n",
        )
        .expect("active batch");
        let input = run_dir.join("triage.jsonl");
        fs::write(
            &input,
            "{\"issue\":1,\"verdict\":\"FIXED_CLEAR\",\"missing_items\":[],\"reason\":\"clear\",\"needs_deep\":false,\"evidence_token\":\"proof-token\"}\n",
        )
        .expect("agent row");
        (run_dir, manifest, input)
    }

    fn fixture_git<const N: usize>(repository: &GitRepository, arguments: [&str; N]) {
        let output = repository.git(arguments).expect("run fixture git");
        assert!(
            output.success(),
            "fixture git failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    fn commit_fixture(repository: &GitRepository, subject: &str) {
        fixture_git(repository, ["add", "-A"]);
        fixture_git(repository, ["commit", "--quiet", "-m", subject]);
    }

    fn fixture_evidence(repository: &GitRepository) -> super::EvidenceRepository {
        let reader = GixRepository::open(repository.root()).expect("open evidence repository");
        let tip = reader
            .resolve_revision(&Revision::new(b"HEAD"))
            .expect("resolve evidence tip");
        hydrate_evidence(reader, "main".to_owned(), tip).expect("hydrate evidence")
    }

    fn service(
        exchanges: impl IntoIterator<Item = IssueServiceExchange>,
    ) -> (
        Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync>,
        IssueServiceStub,
    ) {
        let server = IssueServiceStub::start(exchanges).expect("start issue service stub");
        let base_url = server.base_url().to_owned();
        let factory: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base_url));
        (factory, server)
    }

    fn github_issue_response(number: u64) -> Value {
        let mut issue: Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("valid issue fixture");
        issue["id"] = json!(number);
        issue["number"] = json!(number);
        issue["title"] = json!(format!("{BUG_PREFIX} prefetch regression #{number}"));
        issue["body"] = json!("residual behavior after the fix #7");
        issue["state"] = json!("closed");
        issue["state_reason"] = json!("completed");
        issue["closed_at"] = json!("2026-07-19T00:00:00Z");
        issue
    }

    fn bug_issue(number: u64, state: GitHubIssueState, body: &str) -> GitHubIssue {
        GitHubIssue {
            id: number,
            number,
            title: format!("{BUG_PREFIX} regression #{number}"),
            body: body.to_owned(),
            state,
            state_reason: String::new(),
            url: format!("https://example.invalid/issues/{number}"),
            author: "fixture".to_owned(),
            labels: Vec::new(),
            comments: 0,
            created_at: String::new(),
            closed_at: String::new(),
            updated_at: String::new(),
            is_pull_request: false,
        }
    }

    fn bundle_row(
        issue: u64,
        cache_key: &str,
        fix_sha: &str,
        mechanical: &str,
    ) -> serde_json::Value {
        json!({
            "issue_number": issue,
            "cache_key": cache_key,
            "fix_sha": fix_sha,
            "later_history_hash": format!("history-{issue}"),
            "bundle_path": format!("bundle-{issue}.md"),
            "mechanical_verdict": mechanical,
            "touched_files": [format!("python/larch/zone-{issue}.py")],
            "fix_time": issue,
            "added_lines": issue * 100,
            "marker_references": [],
            "marker_fingerprint": "",
            "zones": ["python/larch/shared"],
            "baseline_extended": false,
            "diff_scan_status": "ok",
            "consumer_scan_status": "ok",
            "later_history_scan_status": "ok",
            "revert_scan_status": "ok",
        })
    }

    fn argv(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn exact_issue_reference_rejects_digits_that_extend_the_number() {
        assert!(has_exact_issue_reference("Fixes #12", 12));
        assert!(!has_exact_issue_reference("Fixes #123", 12));
        assert!(!has_exact_issue_reference("Fixes #012", 12));
    }

    #[test]
    fn artifact_helpers_bound_and_normalize_untrusted_evidence() {
        assert_eq!(
            closure_pull_numbers(&[
                "https://example.invalid/o/r/pull/7".to_owned(),
                "https://example.invalid/o/r/pull/7/".to_owned(),
                "https://example.invalid/o/r/issues/8".to_owned(),
                "https://example.invalid/o/r/pull/zero".to_owned(),
            ]),
            std::collections::BTreeSet::from([7])
        );
        assert_eq!(sanitize_repo(" ../owner/repo.. "), "owner-repo");
        assert_eq!(sanitize_repo("..."), "unknown-repo");
        assert_eq!(
            cap_text("abcdef", 3),
            "abc\n\n[content truncated to 3 characters]\n"
        );
        assert!(path_text(std::path::Path::new("unsafe\npath")).is_err());
        assert_eq!(
            repository_path_text(&GitPath::new(b"python/larch/a.py".to_vec())),
            Ok("python/larch/a.py".to_owned())
        );
        assert!(repository_path_text(&GitPath::new(b"unsafe\npath".to_vec())).is_err());
        assert_eq!(
            zones_for_files(&[
                "python/larch/issue.py".to_owned(),
                "scripts/check.sh".to_owned(),
                "docs/contract.md".to_owned(),
                "crates/larch-cli/main.rs".to_owned(),
                "README.md".to_owned(),
            ]),
            vec![
                "README.md".to_owned(),
                "crates/larch-cli".to_owned(),
                "docs".to_owned(),
                "python/larch/issue.py".to_owned(),
                "scripts".to_owned(),
            ]
        );
        assert!(excluded_consumer_path("larch-logs/run.json"));
        assert!(!excluded_consumer_path("scripts/run.sh"));
        assert!(cross_language_consumer("scripts/run.sh"));
        assert!(cross_language_consumer("skills/review/SKILL.md"));
        assert!(!cross_language_consumer("python/larch/a.py"));
        assert!(is_baseline_path("python/bugs-baseline.json"));
        assert!(!is_baseline_path("python/larch/bugs-baseline.json"));
        assert!(required_evidence_complete(&json!({
            "diff_scan_status": "ok",
            "consumer_scan_status": "ok",
            "later_history_scan_status": "ok",
            "revert_scan_status": "ok",
        })));
        assert!(!required_evidence_complete(
            &json!({"diff_scan_status": "failed"})
        ));
    }

    #[test]
    #[allow(clippy::too_many_lines)] // One matrix keeps Python-compatible error boundaries visible together.
    fn command_entrypoints_preserve_the_argument_boundary_before_network_access() {
        assert_eq!(prefetch(&argv(&["--help"])), ExitCode::SUCCESS);
        assert_eq!(prefetch(&argv(&["--repo"])), ExitCode::from(2));
        assert_eq!(prefetch(&argv(&["--unexpected"])), ExitCode::from(2));
        assert_eq!(prefetch(&argv(&["--count", "0"])), ExitCode::from(2));
        assert_eq!(
            prefetch(&argv(&["--count", "not-a-number"])),
            ExitCode::from(2)
        );
        assert_eq!(
            prefetch(&argv(&[
                "--count",
                "1",
                "--batch-size",
                "1",
                "--diff-cap",
                "1",
                "--repo",
                "not-a-repository",
            ])),
            ExitCode::FAILURE
        );

        let temporary = tempfile::tempdir().expect("temporary state");
        let (run_dir, manifest, input) = write_ingest_fixture(temporary.path(), "ok");
        let ledger_path = temporary.path().join("ledger.jsonl");
        assert_eq!(
            prefetch_with_evidence(
                &argv(&[
                    "--repo",
                    "o/r",
                    "--cache-root",
                    temporary.path().to_str().expect("cache root"),
                    "--state-root",
                    temporary.path().to_str().expect("state root"),
                ]),
                || Err("fixture evidence unavailable".to_owned()),
            ),
            ExitCode::FAILURE
        );
        let arguments = argv(&[
            "--run-dir",
            run_dir.to_str().expect("run path"),
            "--ledger-path",
            ledger_path.to_str().expect("ledger path"),
            "--manifest",
            manifest.to_str().expect("manifest path"),
            "--ingest-triage",
            input.to_str().expect("input path"),
        ]);
        assert_eq!(ledger(&arguments), ExitCode::SUCCESS);
        assert_eq!(ledger(&argv(&["--help"])), ExitCode::SUCCESS);
        assert_eq!(ledger(&argv(&[])), ExitCode::from(2));
        assert_eq!(ledger(&argv(&["--run-dir"])), ExitCode::from(2));
        assert_eq!(
            ledger(&argv(&[
                "--run-dir",
                run_dir.to_str().expect("run path"),
                "--ledger-path",
                ledger_path.to_str().expect("ledger path"),
                "--manifest",
                manifest.to_str().expect("manifest path"),
                "--ingest-triage",
                input.to_str().expect("input path"),
                "--ingest-deep",
                input.to_str().expect("input path"),
            ])),
            ExitCode::FAILURE
        );
        assert_eq!(
            ledger(&argv(&[
                "--run-dir",
                run_dir.to_str().expect("run path"),
                "--ledger-path",
                ledger_path.to_str().expect("ledger path"),
                "--manifest",
                manifest.to_str().expect("manifest path"),
                "--refresh",
                "--sample",
                "-4",
                "--deep-max",
                "1",
                "--deep-model",
                "fable",
                "--batch-size",
                "0",
            ])),
            ExitCode::SUCCESS
        );
        assert_eq!(
            ledger(&argv(&[
                "--run-dir",
                run_dir.to_str().expect("run path"),
                "--ledger-path",
                ledger_path.to_str().expect("ledger path"),
                "--sample",
                "not-an-int",
            ])),
            ExitCode::from(2)
        );
        assert_eq!(
            ledger(&argv(&[
                "--run-dir",
                run_dir.to_str().expect("run path"),
                "--ledger-path",
                ledger_path.to_str().expect("ledger path"),
                "--manifest",
                manifest.to_str().expect("manifest path"),
                "--deep-model",
                "unknown",
            ])),
            ExitCode::FAILURE
        );
        assert_eq!(runtime(&argv(&["--help"])), ExitCode::SUCCESS);
        assert_eq!(runtime(&argv(&[])), ExitCode::from(2));
        assert_eq!(report(&argv(&["--help"])), ExitCode::SUCCESS);
        assert_eq!(report(&argv(&[])), ExitCode::from(2));
    }

    #[test]
    fn prefetch_command_writes_the_private_handoff_from_typed_github_data() {
        let repository = GitRepository::builder(GitFixture::Unborn)
            .build()
            .expect("fixture repository");
        repository
            .write(
                "python/larch/bug.py",
                b"def repaired_name():\n    return 2\n",
            )
            .expect("fixed source");
        repository
            .write("scripts/consumer.sh", b"#!/bin/sh\nrepaired_name\n")
            .expect("fixed consumer");
        commit_fixture(&repository, "Fixes #42 repair old_name");
        let evidence = fixture_evidence(&repository);
        let temporary = tempfile::tempdir().expect("temporary state");
        let cache_root = temporary.path().join("cache");
        let state_root = temporary.path().join("state");
        let (github, server) = service([
            IssueServiceExchange::any_json(200, json!([github_issue_response(42)]).to_string())
                .expect("issue response"),
            IssueServiceExchange::any_json(
                200,
                json!({
                    "data": {"repository": {"issues": {
                        "nodes": [{
                            "number": 42,
                            "closedByPullRequestsReferences": {
                                "nodes": [], "pageInfo": {"hasNextPage": false}
                            }
                        }],
                        "pageInfo": {"hasNextPage": false, "endCursor": null}
                    }}}
                })
                .to_string(),
            )
            .expect("closure response"),
        ]);
        let arguments = argv(&[
            "--repo",
            "o/r",
            "-n=1",
            "--cache-root",
            cache_root.to_str().expect("cache root"),
            "--state-root",
            state_root.to_str().expect("state root"),
            "--batch-size",
            "1",
            "--diff-cap",
            "60000",
        ]);

        assert_eq!(
            with_test_github_service(github, || {
                prefetch_with_evidence(&arguments, || Ok::<_, String>(evidence))
            }),
            ExitCode::SUCCESS
        );

        let run = fs::read_dir(cache_root.join("o-r/runs"))
            .expect("runs")
            .filter_map(Result::ok)
            .map(|entry| entry.path())
            .next()
            .expect("one run");
        let manifest: Value =
            serde_json::from_slice(&fs::read(run.join("manifest.json")).expect("manifest"))
                .expect("manifest JSON");
        assert_eq!(manifest.get("bugs_selected"), Some(&json!(1)));
        assert_eq!(
            manifest.pointer("/issues/0/diff_scan_status"),
            Some(&json!("ok"))
        );
        assert!(run.join("triage-batch-1.jsonl").is_file());
        assert_eq!(server.finish().expect("GitHub requests").len(), 2);
    }

    #[test]
    fn triage_rejects_untrusted_extra_fields_with_the_stable_reason() {
        let row = json!({"issue": 1, "verdict": "FIXED_CLEAR", "missing_items": [], "reason": "ok", "needs_deep": false, "evidence_token": "token", "unexpected": true});
        assert_eq!(
            validate_agent_row(row.as_object().expect("object"), "triage"),
            Err("triage row has unexpected or missing fields".to_owned())
        );
    }

    #[test]
    fn triage_rejects_a_bundle_missing_its_evidence_token_with_the_stable_reason() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let bundle_path = temporary.path().join("bundle.md");
        fs::write(&bundle_path, "# Bundle\nno token here\n").expect("bundle");
        let row = json!({"evidence_token": "proof-token"});
        let bundle = json!({"bundle_path": bundle_path});
        assert_eq!(
            validate_evidence_token(row.as_object().expect("agent row"), &bundle,),
            Err("bundle lacks evidence_token line".to_owned())
        );
    }

    #[test]
    fn deep_requires_a_class_accounting_for_confirmed_fix() {
        let row = json!({"issue": 1, "verdict": "CONFIRMED_FIXED", "reason": "ok", "introduced_risk": "none found", "introduced_risk_reason": "checked", "class_complete": false, "sibling_sites": []});
        assert_eq!(
            validate_agent_row(row.as_object().expect("object"), "deep"),
            Err("deep confirmed-fixed class-open row requires sibling_sites".to_owned())
        );
        assert!(SIBLING_SITE.is_match("python/larch/a.py:thing"));
    }

    #[test]
    fn deep_model_aliases_stay_pinned_to_the_python_contract() {
        assert_eq!(
            model_alias("sonnet"),
            Ok(("claude-sonnet-4-6", "claude-sonnet-4-6"))
        );
        assert_eq!(
            model_alias("unknown"),
            Err("unsupported --deep-model 'unknown'; expected sonnet|opus|fable".to_owned())
        );
    }

    #[test]
    fn interrupted_triage_retry_is_idempotent_after_the_first_durable_append() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let (run_dir, manifest, input) = write_ingest_fixture(temporary.path(), "ok");
        let ledger = temporary.path().join("ledger.jsonl");
        let first = ingest(&run_dir, &ledger, &manifest, &input, "triage").expect("first ingest");
        let retry = ingest(&run_dir, &ledger, &manifest, &input, "triage").expect("retry ingest");
        assert_eq!(first.get("INGEST_ACCEPTED"), Some(&"1".to_owned()));
        assert_eq!(retry.get("INGEST_ACCEPTED"), Some(&"0".to_owned()));
        assert_eq!(
            fs::read_to_string(ledger).expect("ledger").lines().count(),
            1
        );
    }

    #[test]
    fn malformed_ledger_bytes_are_quarantined_without_blocking_resume() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let ledger = temporary.path().join("ledger.jsonl");
        fs::write(&ledger, b"{\"cache_key\":\"valid\",\"issue\":1}\n\xff\n").expect("ledger");
        let (records, corrupt) = load_ledger(&ledger).expect("ledger load");
        assert_eq!(records.len(), 1);
        assert_eq!(corrupt, 1);
        assert!(
            fs::read_dir(temporary.path())
                .expect("temporary entries")
                .filter_map(Result::ok)
                .any(|entry| entry
                    .file_name()
                    .to_string_lossy()
                    .starts_with("ledger.jsonl.corrupt-"))
        );
    }

    #[cfg(unix)]
    #[test]
    fn concurrent_append_only_commits_one_equivalent_ledger_record() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let ledger = temporary.path().join("ledger.jsonl");
        let record = json!({"cache_key": "cache-key", "issue": 1, "stages_complete": []});
        let barrier = Arc::new(Barrier::new(2));
        let (first, second) = std::thread::scope(|scope| {
            let first_barrier = Arc::clone(&barrier);
            let second_barrier = Arc::clone(&barrier);
            let first_ledger = &ledger;
            let second_ledger = &ledger;
            let first_record = &record;
            let second_record = &record;
            let first = scope.spawn(move || {
                first_barrier.wait();
                append_records(first_ledger, std::slice::from_ref(first_record))
                    .expect("first append")
            });
            let second = scope.spawn(move || {
                second_barrier.wait();
                append_records(second_ledger, std::slice::from_ref(second_record))
                    .expect("second append")
            });
            (
                first.join().expect("first thread"),
                second.join().expect("second thread"),
            )
        });
        assert_eq!(first + second, 1);
        assert_eq!(
            fs::read_to_string(ledger).expect("ledger").lines().count(),
            1
        );
    }

    #[test]
    fn incomplete_evidence_rejects_an_agent_row_without_creating_a_ledger() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let (run_dir, manifest, input) = write_ingest_fixture(temporary.path(), "failed");
        let ledger = temporary.path().join("ledger.jsonl");
        let result = ingest(&run_dir, &ledger, &manifest, &input, "triage").expect("ingest");
        assert_eq!(result.get("INGEST_ACCEPTED"), Some(&"0".to_owned()));
        assert_eq!(result.get("INGEST_REJECTED"), Some(&"1".to_owned()));
        assert!(!ledger.exists());
    }

    #[test]
    fn fix_diff_only_contributes_symbols_from_changed_lines() {
        let diff = unified_blob_diff(
            b"def old_name():\n    return 1\n\ndef untouched_name():\n    return 2\n",
            b"def new_name():\n    return 1\n\ndef untouched_name():\n    return 2\n",
        )
        .expect("unified diff");
        let symbols = changed_symbols(&diff);
        assert!(symbols.contains(&"old_name".to_owned()));
        assert!(symbols.contains(&"new_name".to_owned()));
        assert!(!symbols.contains(&"untouched_name".to_owned()));
    }

    #[test]
    fn no_fix_mechanical_candidates_remain_queued_after_a_stale_deep_record() {
        let bundle = json!({
            "issue_number": 1,
            "cache_key": "cache-key",
            "fix_sha": "",
            "later_history_hash": "later",
            "mechanical_verdict": "NEEDS_DEEP",
        });
        let ledger = std::collections::BTreeMap::from([(
            "cache-key".to_owned(),
            json!({
                "cache_key": "cache-key",
                "fix_sha": "",
                "later_history_hash": "later",
                "stages_complete": ["deep"],
            }),
        )]);
        let candidates = deep_candidates(&[bundle], &ledger, false, 0);
        assert_eq!(candidates.len(), 1);
        assert_eq!(candidates[0].get("source"), Some(&json!("mechanical")));
    }

    #[test]
    fn verified_clear_triage_routes_marker_linked_evidence_to_the_deep_queue() {
        let bundle = json!({
            "issue_number": 1, "cache_key": "cache-key", "fix_sha": "fix", "later_history_hash": "later",
            "mechanical_verdict": "", "marker_references": [2], "zones": [], "touched_files": [], "added_lines": 0,
        });
        let verified = std::collections::BTreeMap::from([(
            "cache-key".to_owned(),
            json!({
                "cache_key": "cache-key", "issue": 1, "fix_sha": "fix", "later_history_hash": "later",
                "triage_verdict": "FIXED_CLEAR", "triage_evidence_verified": true, "stages_complete": ["triage"],
            }),
        )]);
        let queued = deep_candidates(std::slice::from_ref(&bundle), &verified, false, 0);
        assert_eq!(queued[0].get("source"), Some(&json!("chain-linked")));

        let unverified = std::collections::BTreeMap::from([(
            "cache-key".to_owned(),
            json!({
                "cache_key": "cache-key", "issue": 1, "fix_sha": "fix", "later_history_hash": "later",
                "triage_verdict": "FIXED_CLEAR", "stages_complete": ["triage"],
            }),
        )]);
        assert!(deep_candidates(&[bundle], &unverified, false, 0).is_empty());
    }

    #[test]
    fn metadata_refresh_keeps_prior_analytics_when_new_evidence_is_empty() {
        let bundle = json!({
            "cache_key": "cache-key", "issue_number": 1, "fix_sha": "f", "later_history_hash": "later",
            "touched_files": [], "fix_time": 0, "added_lines": 0,
            "marker_references": [], "marker_fingerprint": "", "zones": [], "baseline_extended": false,
        });
        let old = json!({
            "touched_files": ["python/larch/old.py"], "fix_time": 7, "added_lines": 2,
            "marker_references": [42], "marker_fingerprint": "marker", "zones": ["python/larch/old"],
            "baseline_extended": true,
        });
        let record = metadata_record(&bundle, Some(&old), Some(123));
        assert_eq!(
            record.get("touched_files"),
            Some(&json!(["python/larch/old.py"]))
        );
        assert_eq!(record.get("fix_time"), Some(&json!(7)));
        assert_eq!(record.get("added_lines"), Some(&json!(2)));
        assert_eq!(record.get("marker_references"), Some(&json!([42])));
        assert_eq!(record.get("marker_fingerprint"), Some(&json!("marker")));
        assert_eq!(record.get("zones"), Some(&json!(["python/larch/old"])));
        assert_eq!(record.get("baseline_extended"), Some(&json!(true)));
        assert_eq!(record.get("updated_at"), Some(&json!(123)));
    }

    #[test]
    fn marker_evidence_requires_a_phrase_and_a_standalone_issue_reference() {
        let marker = format!("{BUG_PREFIX} residual #42");
        assert_eq!(
            marker_evidence(&marker, ""),
            (vec![42], super::digest_text(&format!("{marker}\n")))
        );
        assert_eq!(
            marker_evidence("residual x#42", ""),
            (Vec::new(), String::new())
        );
    }

    #[test]
    #[allow(clippy::too_many_lines)] // One fixture verifies every required evidence outcome and fallback.
    fn prefetch_bundle_collects_bounded_synced_main_evidence() {
        let repository = GitRepository::builder(GitFixture::Unborn)
            .build()
            .expect("fixture repository");
        repository
            .write("python/larch/bug.py", b"def old_name():\n    return 1\n")
            .expect("initial source");
        repository
            .write("scripts/consumer.sh", b"#!/bin/sh\nold_name\n")
            .expect("initial consumer");
        commit_fixture(&repository, "initial evidence");
        repository
            .write(
                "python/larch/bug.py",
                b"def repaired_name():\n    return 2\n",
            )
            .expect("fixed source");
        repository
            .write("scripts/consumer.sh", b"#!/bin/sh\nrepaired_name\n")
            .expect("fixed consumer");
        commit_fixture(&repository, "Fixes #42 repair old_name");
        repository
            .write(
                "python/larch/bug.py",
                b"def repaired_name():\n    return 3\n",
            )
            .expect("follow-up source");
        commit_fixture(&repository, "Revert review-only experiment");

        let reader = GixRepository::open(repository.root()).expect("open evidence repository");
        let tip = reader
            .resolve_revision(&Revision::new(b"HEAD"))
            .expect("resolve evidence tip");
        let evidence = hydrate_evidence(reader, "main".to_owned(), tip).expect("hydrate evidence");
        let temporary = tempfile::tempdir().expect("run directory");
        let issue = bug_issue(
            42,
            GitHubIssueState::Closed,
            "residual behavior after the fix #7",
        );

        let bundle = bundle_for_issue(
            &issue,
            &["https://example.invalid/o/r/pull/42".to_owned()],
            None,
            &evidence,
            temporary.path(),
            60_000,
        )
        .expect("prefetch bundle");

        assert_eq!(bundle.get("diff_scan_status"), Some(&json!("ok")));
        assert_eq!(bundle.get("consumer_scan_status"), Some(&json!("ok")));
        assert_eq!(bundle.get("later_history_scan_status"), Some(&json!("ok")));
        assert_eq!(bundle.get("revert_scan_status"), Some(&json!("ok")));
        assert_eq!(bundle.get("marker_references"), Some(&json!([7, 42])));
        assert!(
            bundle
                .get("fix_sha")
                .and_then(serde_json::Value::as_str)
                .is_some_and(|value| value.len() == 40)
        );
        let rendered = fs::read_to_string(
            bundle
                .get("bundle_path")
                .and_then(serde_json::Value::as_str)
                .expect("bundle path"),
        )
        .expect("rendered bundle");
        assert!(rendered.contains("repaired_name"));
        assert!(rendered.contains("scripts/consumer.sh"));

        let fix_sha = bundle
            .get("fix_sha")
            .and_then(Value::as_str)
            .expect("fix SHA")
            .to_owned();
        let closure_fix = find_fix(
            99,
            Some(&std::collections::BTreeSet::from([fix_sha.clone()])),
            &evidence,
        )
        .expect("closure fix");
        assert_eq!(closure_fix.source, "closedByPullRequestsReferences");
        assert_eq!(closure_fix.sha, fix_sha);
        assert_eq!(
            find_fix(99, None, &evidence).expect("missing fix").reason,
            "no exact Fixes reference"
        );
        assert_eq!(
            find_fix(
                99,
                Some(&std::collections::BTreeSet::from([
                    "a".to_owned(),
                    "b".to_owned(),
                ])),
                &evidence,
            )
            .expect("ambiguous closure")
            .reason,
            "multiple PR merge commits"
        );
        let open_without_fix = bundle_for_issue(
            &bug_issue(99, GitHubIssueState::Open, "no matching closure"),
            &[],
            None,
            &evidence,
            temporary.path(),
            60_000,
        )
        .expect("open no-fix bundle");
        assert_eq!(
            open_without_fix.get("mechanical_verdict"),
            Some(&json!("NOT_FIXED"))
        );
        assert_eq!(
            open_without_fix.get("diff_scan_status"),
            Some(&json!("not-run"))
        );
        let capped = bundle_for_issue(&issue, &[], None, &evidence, temporary.path(), 1)
            .expect("capped bundle");
        assert_eq!(capped.get("diff_scan_status"), Some(&json!("failed")));
        assert_eq!(capped.get("mechanical_verdict"), Some(&json!("NEEDS_DEEP")));
    }

    #[test]
    fn ledger_compute_refreshes_metadata_and_caps_the_deep_queue() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let run_dir = temporary.path().join("run");
        fs::create_dir_all(&run_dir).expect("run directory");
        let fixed = "f".repeat(40);
        let mut chained = bundle_row(3, "chain", &fixed, "");
        chained["marker_references"] = json!([9]);
        let sampled = bundle_row(4, "sample", &fixed, "");
        let manifest = run_dir.join("manifest.json");
        fs::write(
            &manifest,
            json!({
                "generated_at": 17,
                "issues": [
                    bundle_row(1, "triage", &fixed, ""),
                    bundle_row(2, "mechanical", &fixed, "NEEDS_DEEP"),
                    chained,
                    sampled,
                ],
            })
            .to_string(),
        )
        .expect("manifest");
        let ledger = temporary.path().join("ledger.jsonl");
        fs::write(
            &ledger,
            format!(
                "{}\n{}\n",
                json!({
                    "cache_key": "chain", "issue": 3, "fix_sha": fixed,
                    "later_history_hash": "history-3", "triage_verdict": "FIXED_CLEAR",
                    "triage_evidence_verified": true, "stages_complete": ["triage"],
                }),
                json!({
                    "cache_key": "sample", "issue": 4, "fix_sha": fixed,
                    "later_history_hash": "history-4", "triage_verdict": "FIXED_CLEAR",
                    "triage_evidence_verified": true, "stages_complete": ["triage"],
                })
            ),
        )
        .expect("ledger");

        let output = compute(&run_dir, &ledger, &manifest, false, 1, 1, "sonnet", 1)
            .expect("ledger compute");
        assert_eq!(output.get("TRIAGE_PENDING"), Some(&"1".to_owned()));
        assert_eq!(output.get("DEEP_PENDING"), Some(&"1".to_owned()));
        assert_eq!(output.get("DEEP_CAP_TRUNCATED"), Some(&"true".to_owned()));
        assert_eq!(
            output.get("DEEP_MODEL"),
            Some(&"claude-sonnet-4-6".to_owned())
        );
        let queue = fs::read_to_string(run_dir.join("deep-queue.jsonl")).expect("deep queue");
        assert!(queue.contains("mechanical"));
        assert!(run_dir.join("triage-pending-1.jsonl").is_file());
        assert!(run_dir.join("ledger-summary.json").is_file());
    }

    #[test]
    fn ledger_ingest_rejects_malformed_duplicate_and_inactive_rows() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let (run_dir, manifest, input) = write_ingest_fixture(temporary.path(), "ok");
        fs::write(
            &input,
            concat!(
                "not-json\n",
                "{\"issue\":2,\"verdict\":\"FIXED_CLEAR\",\"missing_items\":[],\"reason\":\"clear\",\"needs_deep\":false,\"evidence_token\":\"proof-token\"}\n",
                "{\"issue\":1,\"verdict\":\"FIXED_CLEAR\",\"missing_items\":[],\"reason\":\"clear\",\"needs_deep\":false,\"evidence_token\":\"proof-token\"}\n",
                "{\"issue\":1,\"verdict\":\"FIXED_CLEAR\",\"missing_items\":[],\"reason\":\"clear\",\"needs_deep\":false,\"evidence_token\":\"proof-token\"}\n"
            ),
        )
        .expect("agent rows");
        let ledger = temporary.path().join("ledger.jsonl");
        let output = ingest(&run_dir, &ledger, &manifest, &input, "triage").expect("ingest");
        assert_eq!(output.get("INGEST_ACCEPTED"), Some(&"1".to_owned()));
        assert_eq!(output.get("INGEST_REJECTED"), Some(&"3".to_owned()));
        let missing = run_dir.join("missing-deep.jsonl");
        let deep =
            ingest(&run_dir, &ledger, &manifest, &missing, "deep").expect("absent deep ingest");
        assert_eq!(deep.get("INGEST_ACCEPTED"), Some(&"0".to_owned()));
    }

    #[test]
    fn deep_ingest_marks_a_queued_sample_complete_without_replaying_triage() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let (run_dir, manifest, _triage_input) = write_ingest_fixture(temporary.path(), "ok");
        fs::write(
            run_dir.join("deep-queue.jsonl"),
            "{\"issue\":1,\"sampled\":true}\n",
        )
        .expect("deep queue");
        let deep_input = run_dir.join("deep.jsonl");
        fs::write(
            &deep_input,
            concat!(
                "{\"issue\":1,\"verdict\":\"CONFIRMED_FIXED\",\"reason\":\"checked\",",
                "\"introduced_risk\":\"none found\",\"introduced_risk_reason\":\"checked\",",
                "\"class_complete\":true,\"sibling_sites\":[]}\n"
            ),
        )
        .expect("deep row");
        let ledger = temporary.path().join("ledger.jsonl");

        let output = ingest(&run_dir, &ledger, &manifest, &deep_input, "deep").expect("ingest");

        assert_eq!(output.get("INGEST_ACCEPTED"), Some(&"1".to_owned()));
        let (records, corrupt) = load_ledger(&ledger).expect("ledger");
        assert_eq!(corrupt, 0);
        let record = records.get("cache-key").expect("record");
        assert_eq!(record.get("deep_verdict"), Some(&json!("CONFIRMED_FIXED")));
        assert_eq!(record.get("sampled"), Some(&json!(true)));
        assert_eq!(record.get("stages_complete"), Some(&json!(["deep"])));
    }

    #[test]
    fn runtime_cap_zero_replaces_the_artifact_without_needing_a_repository() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let run_dir = temporary.path().join("run");
        let fix_sha = "a".repeat(40);
        let (selected, skipped) = runtime_verify(
            &run_dir,
            &[bundle_row(1, "cache-key", &fix_sha, "")],
            0,
            std::path::Path::new("/not-needed-for-zero-cap"),
        )
        .expect("zero-cap runtime verification");

        assert_eq!((selected, skipped), (0, 1));
        assert_eq!(
            fs::read_to_string(run_dir.join("runtime-results.jsonl")).expect("runtime results"),
            ""
        );
        assert_eq!(
            serde_json::from_slice::<Value>(
                &fs::read(run_dir.join("runtime-summary.json")).expect("runtime summary"),
            )
            .expect("runtime summary JSON"),
            json!({"selected_unique_shas": 0, "skipped_unique_shas": 1})
        );
    }

    #[test]
    fn runtime_ranks_unique_shas_and_maps_static_harnesses() {
        let repository = GitRepository::builder(GitFixture::Unborn)
            .build()
            .expect("fixture repository");
        repository
            .write("README.md", b"first runtime commit\n")
            .expect("first source");
        commit_fixture(&repository, "first runtime commit");
        let reader = GixRepository::open(repository.root()).expect("open fixture repository");
        let older = reader
            .resolve_revision(&Revision::new(b"HEAD"))
            .expect("resolve older revision")
            .to_hex();
        repository
            .write("README.md", b"second runtime commit\n")
            .expect("second source");
        commit_fixture(&repository, "second runtime commit");
        let reader = GixRepository::open(repository.root()).expect("reopen fixture repository");
        let newer = reader
            .resolve_revision(&Revision::new(b"HEAD"))
            .expect("resolve newer revision")
            .to_hex();
        let mut older_bundle = bundle_row(1, "older", &older, "");
        older_bundle["fix_time"] = json!(1);
        let mut newer_bundle = bundle_row(2, "newer", &newer, "");
        newer_bundle["fix_time"] = json!(2);
        let temporary = tempfile::tempdir().expect("temporary state");
        let run_dir = temporary.path().join("run");

        let (selected, skipped) = runtime_verify(
            &run_dir,
            &[older_bundle, newer_bundle],
            1,
            repository.root(),
        )
        .expect("runtime verification");

        assert_eq!((selected, skipped), (1, 1));
        let result: Value = serde_json::from_str(
            &fs::read_to_string(run_dir.join("runtime-results.jsonl")).expect("runtime result"),
        )
        .expect("runtime result JSON");
        assert_eq!(result.get("fix_sha"), Some(&json!(newer)));
        assert_eq!(
            super::runtime_harnesses(&[
                "skills/implement/SKILL.md".to_owned(),
                "scripts/test-implement-anti-halt.sh".to_owned(),
            ]),
            vec![
                "test-architectural-guidelines-step".to_owned(),
                "test-implement-anti-halt".to_owned(),
            ]
        );
        assert_eq!(
            super::runtime_uncovered_zones(&[
                "skills/triage/SKILL.md".to_owned(),
                "scripts/other.sh".to_owned(),
            ]),
            vec!["scripts".to_owned(), "skills".to_owned()]
        );
    }

    #[test]
    fn runtime_command_discovers_and_executes_a_changed_python_test() {
        let repository = GitRepository::builder(GitFixture::Unborn)
            .build()
            .expect("fixture repository");
        repository
            .write("README.md", b"initial runtime fixture\n")
            .expect("initial source");
        commit_fixture(&repository, "initial runtime fixture");
        repository
            .write(
                "python/tests/test_runtime_fixture.py",
                b"def test_runtime_fixture():\n    assert True\n",
            )
            .expect("runtime test");
        // A fixture-local module keeps this Rust-only test independent of a
        // host pytest installation while asserting that runtime discovery
        // forwards the changed test path to the fixed command.
        repository
            .write(
                "pytest.py",
                b"from pathlib import Path\nimport runpy\nimport sys\n\nexpected = 'python/tests/test_runtime_fixture.py'\nif expected not in sys.argv:\n    raise SystemExit(2)\nPath('.runtime-pytest-shim-ran').write_text('ran\\n')\nnamespace = runpy.run_path(expected)\nnamespace['test_runtime_fixture']()\n",
            )
            .expect("pytest fixture module");
        commit_fixture(&repository, "add runtime test");
        let reader = GixRepository::open(repository.root()).expect("open fixture repository");
        let fix_sha = reader
            .resolve_revision(&Revision::new(b"HEAD"))
            .expect("resolve fixture HEAD")
            .to_hex();
        let temporary = tempfile::tempdir().expect("temporary state");
        let run_dir = temporary.path().join("run");
        let manifest = temporary.path().join("manifest.json");
        fs::write(
            &manifest,
            json!({"issues": [bundle_row(1, "runtime", &fix_sha, "")]}).to_string(),
        )
        .expect("manifest");
        let arguments = vec![
            OsString::from("--run-dir"),
            run_dir.as_os_str().to_os_string(),
            OsString::from("--manifest"),
            manifest.as_os_str().to_os_string(),
            OsString::from("--ledger-path"),
            temporary.path().join("ledger.jsonl").into_os_string(),
            OsString::from("--runtime-max"),
            OsString::from("1"),
            OsString::from("--repo-root"),
            repository.root().as_os_str().to_os_string(),
        ];

        assert_eq!(runtime(&arguments), ExitCode::SUCCESS);
        let artifact: Value = serde_json::from_str(
            &fs::read_to_string(run_dir.join("runtime-results.jsonl")).expect("runtime results"),
        )
        .expect("runtime result JSON");
        assert_eq!(artifact.get("schema_version"), Some(&json!("1")));
        assert_eq!(artifact.get("fix_sha"), Some(&json!(fix_sha)));
        assert_eq!(
            fs::read_to_string(repository.root().join(".runtime-pytest-shim-ran"))
                .expect("pytest fixture marker"),
            "ran\n"
        );
        assert_eq!(
            artifact.pointer("/components/0/status"),
            Some(&json!("passed"))
        );
    }

    #[test]
    fn report_rejects_duplicate_current_runtime_bindings() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let artifact = temporary.path().join("runtime-results.jsonl");
        let fix_sha = "b".repeat(40);
        let bundle = bundle_row(1, "cache-key", &fix_sha, "");
        fs::write(
            &artifact,
            json!({
                "schema_version": "1",
                "fix_sha": fix_sha,
                "bindings": [
                    {"issue": 1, "cache_key": "cache-key", "fix_sha": "b".repeat(40)},
                    {"issue": 1, "cache_key": "cache-key", "fix_sha": "b".repeat(40)}
                ],
                "components": [],
                "uncovered_zones": []
            })
            .to_string(),
        )
        .expect("runtime artifact");

        match load_runtime_results(&artifact, &[bundle]) {
            Err(error) => assert_eq!(error, "duplicate current runtime result for cache-key"),
            Ok(_) => panic!("duplicate binding was accepted"),
        }
    }

    #[test]
    fn report_rejects_malformed_runtime_artifacts_and_ignores_foreign_bindings() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let artifact = temporary.path().join("runtime-results.jsonl");
        let fix_sha = "d".repeat(40);
        let bundle = bundle_row(1, "cache-key", &fix_sha, "");
        fs::write(&artifact, "{}\n").expect("malformed runtime artifact");
        assert!(load_runtime_results(&artifact, std::slice::from_ref(&bundle)).is_err());

        fs::write(
            &artifact,
            json!({
                "schema_version": "1",
                "fix_sha": fix_sha,
                "bindings": [{"issue": 2, "cache_key": "foreign", "fix_sha": "d".repeat(40)}],
                "components": [{"name": "pytest", "status": "passed", "evidence": ""}],
                "uncovered_zones": []
            })
            .to_string(),
        )
        .expect("foreign runtime artifact");
        assert!(
            load_runtime_results(&artifact, &[bundle])
                .expect("foreign binding is ignored")
                .is_empty()
        );
    }

    #[test]
    fn report_is_local_only_and_preserves_the_machine_cost_field() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let run_dir = temporary.path().join("run");
        fs::create_dir_all(&run_dir).expect("run directory");
        let fix_sha = "c".repeat(40);
        let bundle_path = run_dir.join("issue-1-bundle.md");
        fs::write(&bundle_path, "# Bundle\n").expect("bundle");
        let mut bundle = bundle_row(1, "cache-key", &fix_sha, "NEEDS_DEEP");
        bundle["url"] = json!("https://example.invalid/issues/1");
        bundle["bundle_path"] = json!(bundle_path);
        let manifest = run_dir.join("manifest.json");
        fs::write(
            &manifest,
            json!({
                "repo": "owner/repository",
                "run_id": "run-1",
                "evidence_ref": "origin/main",
                "bugs_requested": 1,
                "bugs_selected": 1,
                "generated_at": 1,
                "issues": [bundle],
            })
            .to_string(),
        )
        .expect("manifest");
        let ledger = temporary.path().join("ledger.jsonl");
        fs::write(
            &ledger,
            json!({
                "cache_key": "cache-key",
                "issue": 1,
                "fix_sha": fix_sha,
                "later_history_hash": "history-1",
                "deep_verdict": "CONFIRMED_FIXED",
                "deep_reason": "deep verifier found the fix",
                "stages_complete": ["deep"],
                "sampled": false,
            })
            .to_string(),
        )
        .expect("ledger");

        let report = render_report(&manifest, &ledger, &run_dir).expect("render report");

        assert!(report.contains("| Confirmed or likely fixed | 1 |"));
        assert!(report.contains("| [#1](https://example.invalid/issues/1) | cccccccccccc | DEEP | CONFIRMED_FIXED | deep verifier found the fix |  |"));
        assert!(report.contains("ANALYZE_BUGS_COST_ESTIMATE=$"));
        assert_eq!(
            fs::read_to_string(run_dir.join("report.md")).expect("report file"),
            report
        );
        assert!(!run_dir.join("follow-up-issue.md").exists());
    }

    #[test]
    #[allow(clippy::too_many_lines)] // The fixture exercises one coupled report artifact transaction.
    fn report_renders_runtime_analytics_and_local_followup_artifacts() {
        let temporary = tempfile::tempdir().expect("temporary state");
        let runs = temporary.path().join("runs");
        let previous = runs.join("previous");
        let run_dir = runs.join("current");
        fs::create_dir_all(&previous).expect("previous run directory");
        fs::create_dir_all(&run_dir).expect("current run directory");
        let first_sha = "1".repeat(40);
        let second_sha = "2".repeat(40);
        let third_sha = "3".repeat(40);
        let fourth_sha = "4".repeat(40);
        let first_bundle_path = run_dir.join("issue-1-bundle.md");
        let second_bundle_path = run_dir.join("issue-2-bundle.md");
        let third_bundle_path = run_dir.join("issue-3-bundle.md");
        let fourth_bundle_path = run_dir.join("issue-4-bundle.md");
        for path in [
            &first_bundle_path,
            &second_bundle_path,
            &third_bundle_path,
            &fourth_bundle_path,
        ] {
            fs::write(path, "# bounded bundle\n").expect("bundle");
        }

        let mut first = bundle_row(1, "first", &first_sha, "");
        first["url"] = json!("https://example.invalid/issues/1");
        first["bundle_path"] = json!(first_bundle_path.display().to_string());
        first["fix_time"] = json!(999_700);
        first["touched_files"] = json!(["skills/triage/SKILL.md", "python/larch/zone.py"]);
        first["marker_references"] = json!([2]);
        first["zones"] = json!(["skills/triage"]);
        first["baseline_extended"] = json!(true);
        let mut second = bundle_row(2, "second", &second_sha, "NOT_FIXED");
        second["url"] = json!("https://example.invalid/issues/2");
        second["bundle_path"] = json!(second_bundle_path.display().to_string());
        second["fix_time"] = json!(999_800);
        second["touched_files"] = json!(["skills/triage/SKILL.md"]);
        second["zones"] = json!(["skills/triage"]);
        let mut third = bundle_row(3, "third", &third_sha, "");
        third["url"] = json!("https://example.invalid/issues/3");
        third["bundle_path"] = json!(third_bundle_path.display().to_string());
        third["fix_time"] = json!(999_900);
        third["touched_files"] = json!(["skills/triage/SKILL.md"]);
        third["zones"] = json!(["skills/triage"]);
        let mut fourth = bundle_row(4, "fourth", &fourth_sha, "FIXED_LIKELY");
        fourth["url"] = json!("https://example.invalid/issues/4");
        fourth["bundle_path"] = json!(fourth_bundle_path.display().to_string());
        fourth["fix_time"] = json!(999_950);
        fourth["touched_files"] = json!(["scripts/other.sh"]);
        fourth["zones"] = json!(["scripts"]);
        fourth["diff_scan_status"] = json!("failed");
        fourth["diff_scan_reason"] = json!("bounded diff unavailable");
        let manifest = run_dir.join("manifest.json");
        fs::write(
            &manifest,
            json!({
                "repo": "owner/repository",
                "run_id": "current",
                "evidence_ref": "origin/main",
                "bugs_requested": 4,
                "bugs_selected": 4,
                "generated_at": 1_000_000,
                "issues": [first, second, third, fourth],
            })
            .to_string(),
        )
        .expect("manifest");
        fs::write(
            previous.join("run-state.json"),
            json!({
                "schema_version": "1",
                "repo": "owner/repository",
                "run_id": "previous",
                "generated_at": 999_000,
                "selected_issues": [1],
                "verified_issues": [1],
                "chronic_zones": ["old-zone"],
                "chain_edges": ["1>9:marker"],
                "verified_predicate": "certifiable-fixed-runtime-v2",
            })
            .to_string(),
        )
        .expect("previous snapshot");
        fs::write(
            run_dir.join("runtime-results.jsonl"),
            format!(
                "{}\n{}\n{}\n",
                json!({
                    "schema_version": "1",
                    "fix_sha": first_sha,
                    "bindings": [{"issue": 1, "cache_key": "first", "fix_sha": "1".repeat(40)}],
                    "components": [{"name": "pytest", "status": "passed", "evidence": ""}],
                    "uncovered_zones": [],
                }),
                json!({
                    "schema_version": "1",
                    "fix_sha": third_sha,
                    "bindings": [{"issue": 3, "cache_key": "third", "fix_sha": "3".repeat(40)}],
                    "components": [{"name": "pytest", "status": "failed", "evidence": "assertion failed"}],
                    "uncovered_zones": ["skills/triage"],
                }),
                json!({
                    "schema_version": "1",
                    "fix_sha": fourth_sha,
                    "bindings": [{"issue": 4, "cache_key": "fourth", "fix_sha": "4".repeat(40)}],
                    "components": [{"name": "pytest", "status": "absent", "evidence": "no tests"}],
                    "uncovered_zones": ["scripts"],
                }),
            ),
        )
        .expect("runtime results");
        fs::write(
            run_dir.join("runtime-summary.json"),
            json!({"selected_unique_shas": 3, "skipped_unique_shas": 1}).to_string(),
        )
        .expect("runtime summary");
        fs::write(
            run_dir.join("ledger-summary.json"),
            json!({
                "DEEP_TRUNCATED_ISSUES": [4],
                "DEEP_RATE_MODEL": "claude-fable-5",
            })
            .to_string(),
        )
        .expect("ledger summary");
        let ledger = temporary.path().join("ledger.jsonl");
        let records = [
            json!({
                "cache_key": "first",
                "issue": 1,
                "fix_sha": "1".repeat(40),
                "later_history_hash": "history-1",
                "deep_verdict": "CONFIRMED_FIXED",
                "deep_reason": "deep verifier confirmed the fix",
                "stages_complete": ["deep"],
                "sampled": true,
                "triage_introduced_risk": "none found",
                "triage_introduced_risk_reason": "",
                "deep_introduced_risk": "race introduced",
                "deep_introduced_risk_reason": "bounded evidence",
                "class_complete": false,
                "sibling_sites": ["module.py:handle"],
                "legacy_schema": false,
                "touched_files": ["skills/triage/SKILL.md", "python/larch/zone.py"],
                "fix_time": 999_700,
                "marker_references": [2],
                "zones": ["skills/triage"],
                "baseline_extended": true,
                "updated_at": 10,
            }),
            json!({
                "cache_key": "third",
                "issue": 3,
                "fix_sha": "3".repeat(40),
                "later_history_hash": "history-3",
                "deep_verdict": "",
                "deep_reason": "",
                "stages_complete": ["triage"],
                "triage_verdict": "FIXED_CLEAR",
                "triage_reason": "triage evidence was clear",
                "triage_missing_items": ["manual audit"],
                "triage_needs_deep": false,
                "triage_evidence_verified": true,
                "sampled": true,
                "triage_introduced_risk": "none found",
                "triage_introduced_risk_reason": "",
                "deep_introduced_risk": "",
                "deep_introduced_risk_reason": "",
                "class_complete": true,
                "sibling_sites": [],
                "legacy_schema": false,
                "touched_files": ["skills/triage/SKILL.md"],
                "fix_time": 999_900,
                "marker_references": [],
                "zones": ["skills/triage"],
                "baseline_extended": false,
                "updated_at": 11,
            }),
        ];
        let mut ledger_text = records
            .iter()
            .map(Value::to_string)
            .collect::<Vec<_>>()
            .join("\n");
        ledger_text.push_str("\nnot-json\n");
        fs::write(&ledger, ledger_text).expect("ledger");
        let repository = GitRepository::builder(GitFixture::Unborn)
            .build()
            .expect("fixture sweep repository");
        repository
            .write("README.md", b"sweep report fixture\n")
            .expect("sweep fixture source");
        commit_fixture(&repository, "sweep report fixture");
        fixture_git(
            &repository,
            ["update-ref", "refs/remotes/origin/main", "HEAD"],
        );
        let _repository_root = test_sweep_repository_root(repository.root());
        let repository =
            GixRepository::discover(repository.root()).expect("discover sweep repository");
        let pinned_tip = repository
            .resolve_revision(&Revision::new(b"origin/main"))
            .expect("resolve current origin/main")
            .to_hex();
        let sweep_bundle = run_dir.join("sweep-selected-1.md");
        fs::write(&sweep_bundle, "# bounded sweep bundle\n").expect("sweep bundle");
        let selected_sweep = run_dir.join("sweep-selected-merges.json");
        fs::write(
            &selected_sweep,
            json!({
                "pinned_tip": pinned_tip,
                "selected_count": 1,
                "skipped_count": 1,
                "coverage_incomplete": true,
                "pending_shas": [fourth_sha],
                "selected": [{
                    "merge_sha": pinned_tip,
                    "bundle_path": sweep_bundle.display().to_string(),
                }],
            })
            .to_string(),
        )
        .expect("selected sweep manifest");
        fs::write(
            run_dir.join("sweep-validated.json"),
            json!({
                "pinned_tip": pinned_tip,
                "selected_manifest_path": fs::canonicalize(&selected_sweep)
                    .expect("canonical selected sweep manifest")
                    .display()
                    .to_string(),
                "selected_count": 1,
                "skipped_count": 1,
                "pending_shas": ["4".repeat(40)],
                "coverage_incomplete": true,
                "candidates": [{
                    "merge_sha": pinned_tip,
                    "file": "python/larch/sweep.py",
                    "symbol": "scan",
                    "description": "bounded sweep finding",
                    "severity": "high",
                    "confidence": "medium",
                }],
            })
            .to_string(),
        )
        .expect("validated sweep artifact");
        fs::write(
            run_dir.join("sweep-refuter-queue.jsonl"),
            "{\"merge_sha\":\"queued\"}\n",
        )
        .expect("sweep queue");

        let rendered = render_report(&manifest, &ledger, &run_dir).expect("render rich report");

        for expected in [
            "## Instance fixed, class open",
            "## Introduced risk",
            "## Harness coverage gaps",
            "UNVERIFIED_RUNTIME: no harness covers skills/triage",
            "## Chronic zones",
            "## Fix chains",
            "## Baseline-extending fixes",
            "First run: no",
            "Ledger corrupt lines quarantined: 1",
            "## Follow-up issue body",
            "ANALYZE_BUGS_COST_ESTIMATE=$",
            "## Sweep candidates",
            "Sweep coverage incomplete: pending eligible merges will be retried.",
            "ANALYZE_BUGS_SWEEP_COST_ESTIMATE=$",
        ] {
            assert!(
                rendered.contains(expected),
                "missing {expected}: {rendered}"
            );
        }
        assert!(rendered.contains("Runtime selected unique SHAs: 3"));
        assert!(rendered.contains("Runtime skipped unique SHAs: 1"));
        let report_arguments = vec![
            OsString::from("--run-dir"),
            run_dir.as_os_str().to_os_string(),
            OsString::from("--manifest"),
            manifest.as_os_str().to_os_string(),
            OsString::from("--ledger-path"),
            ledger.as_os_str().to_os_string(),
        ];
        assert_eq!(report(&report_arguments), ExitCode::SUCCESS);
        let followup = fs::read_to_string(run_dir.join("follow-up-issue.md")).expect("followup");
        assert!(followup.contains("#2: NOT_FIXED"));
        assert!(followup.contains("Instance fixed, class open"));
        assert!(run_dir.join("run-state.json").is_file());
        assert!(temporary.path().join("sweep-state.json").is_file());
    }
}
