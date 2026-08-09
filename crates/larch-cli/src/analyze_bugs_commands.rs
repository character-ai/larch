//! Rust owner for the bounded bug-fix evidence prefetch and ledger commands.
//!
//! The two commands exchange private JSON artifacts with the Python-owned
//! `analyze-bugs runtime` and `analyze-bugs report` verbs.  Everything read
//! from GitHub or an agent-produced JSONL file is data: it is bounded,
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
};

#[cfg(unix)]
use std::os::unix::fs::{OpenOptionsExt as _, PermissionsExt as _};

use larch_adapters::{GixRepository, unified_blob_diff};
use larch_core::{
    Commit, GitHubIssue, GitHubIssueList, GitHubIssueState, GitHubService, GitPath, PLAN_MARKER,
    RepositoryRead, Revision, bug_title_match, emit_kv, epoch_now, private_atomic_write,
    require_enabled_storage, resolve_run_log_storage, strip_named_block,
};
use serde_json::{Map, Value, json};
use sha2::{Digest as _, Sha256};
use uuid::Uuid;

use crate::{
    argparse_compat::{ParsedCommandLine, parse_with_flags, usage_error},
    github_repository_resolution::{ambient_repo, repository_ref, validate_repo_slug},
    github_service::with_github_service,
};

const PREFETCH_PROGRAM: &str = "python/cli.py analyze-bugs prefetch";
const PREFETCH_USAGE: &str = "usage: python/cli.py analyze-bugs prefetch [-h] [--repo REPO] [-n COUNT]\n                                           [--cache-root CACHE_ROOT]\n                                           [--state-root STATE_ROOT]\n                                           [--batch-size BATCH_SIZE]\n                                           [--diff-cap DIFF_CAP]";
const PREFETCH_HELP: &str = "usage: python/cli.py analyze-bugs prefetch [-h] [--repo REPO] [-n COUNT]\n                                           [--cache-root CACHE_ROOT]\n                                           [--state-root STATE_ROOT]\n                                           [--batch-size BATCH_SIZE]\n                                           [--diff-cap DIFF_CAP]\n\noptions:\n  -h, --help            show this help message and exit\n  --repo REPO\n  -n COUNT, --count COUNT\n  --cache-root CACHE_ROOT\n  --state-root STATE_ROOT\n  --batch-size BATCH_SIZE\n  --diff-cap DIFF_CAP\n";
const LEDGER_PROGRAM: &str = "python/cli.py analyze-bugs ledger";
const LEDGER_USAGE: &str = "usage: python/cli.py analyze-bugs ledger [-h] --run-dir RUN_DIR --ledger-path\n                                         LEDGER_PATH [--manifest MANIFEST]\n                                         [--ingest-triage INGEST_TRIAGE]\n                                         [--ingest-deep INGEST_DEEP]\n                                         [--refresh] [--sample SAMPLE]\n                                         [--deep-max DEEP_MAX]\n                                         [--deep-model DEEP_MODEL]\n                                         [--batch-size BATCH_SIZE]";
const LEDGER_HELP: &str = "usage: python/cli.py analyze-bugs ledger [-h] --run-dir RUN_DIR --ledger-path\n                                         LEDGER_PATH [--manifest MANIFEST]\n                                         [--ingest-triage INGEST_TRIAGE]\n                                         [--ingest-deep INGEST_DEEP]\n                                         [--refresh] [--sample SAMPLE]\n                                         [--deep-max DEEP_MAX]\n                                         [--deep-model DEEP_MODEL]\n                                         [--batch-size BATCH_SIZE]\n\noptions:\n  -h, --help            show this help message and exit\n  --run-dir RUN_DIR\n  --ledger-path LEDGER_PATH\n  --manifest MANIFEST\n  --ingest-triage INGEST_TRIAGE\n  --ingest-deep INGEST_DEEP\n  --refresh\n  --sample SAMPLE\n  --deep-max DEEP_MAX\n  --deep-model DEEP_MODEL\n  --batch-size BATCH_SIZE\n";

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

/// Fetch bounded bug evidence and private hand-off bundles.
#[must_use]
#[allow(clippy::too_many_lines)] // The ordered artifact hand-off is one compatibility transaction.
pub fn prefetch(arguments: &[OsString]) -> ExitCode {
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
    let evidence = match evidence_repository() {
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

fn stage_complete(record: &Value, stage: &str) -> bool {
    record
        .get("stages_complete")
        .and_then(Value::as_array)
        .is_some_and(|stages| stages.iter().any(|value| value.as_str() == Some(stage)))
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
    let (repo_root, origin, environment) =
        crate::run_log_commands::resolve_repository_environment_path(None)
            .map_err(|_| "could not resolve analysis-state root".to_owned())?;
    let storage = resolve_run_log_storage(&repo_root, &environment, &origin)
        .and_then(|resolution| require_enabled_storage(&resolution))
        .map_err(|error| error.to_string())?;
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

#[cfg(test)]
mod tests {
    use std::{
        fs,
        sync::{Arc, Barrier},
    };

    use super::{
        SIBLING_SITE, append_records, changed_symbols, deep_candidates, has_exact_issue_reference,
        ingest, load_ledger, marker_evidence, metadata_record, model_alias, validate_agent_row,
        validate_evidence_token,
    };
    use larch_adapters::unified_blob_diff;
    use larch_core::BUG_PREFIX;
    use serde_json::json;

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

    #[test]
    fn exact_issue_reference_rejects_digits_that_extend_the_number() {
        assert!(has_exact_issue_reference("Fixes #12", 12));
        assert!(!has_exact_issue_reference("Fixes #123", 12));
        assert!(!has_exact_issue_reference("Fixes #012", 12));
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
}
