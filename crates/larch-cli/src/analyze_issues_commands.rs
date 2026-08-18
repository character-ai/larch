//! Rust owner for the issue-backlog analysis commands.
//!
//! The command deliberately keeps the fetch boundary and report renderer in one
//! module.  A saved issue dump is an untrusted data artifact: fetch serializes
//! it as JSON with owner-only permissions, and analysis parses only the bounded
//! fields represented by [`IssueSummary`].  No fetched title or body is ever
//! interpreted as a command, path, or prompt.

use std::{
    collections::{BTreeMap, BTreeSet, HashSet},
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::{
        LazyLock,
        atomic::{AtomicU64, Ordering},
    },
};

#[cfg(unix)]
use std::os::unix::fs::{OpenOptionsExt as _, PermissionsExt as _};

use chrono::{DateTime, Duration, NaiveDate, Utc};
use larch_core::{
    BlockBoundary, CorpusFilter, DONE_PREFIX, GitHubComment, GitHubIssue, GitHubIssueBodyMode,
    GitHubIssueList, GitHubIssueListMode, GitHubIssueState, GitHubService, GroundTruthCorpusScan,
    GroundTruthMode, GroundTruthRow, GroundTruthVoter, IncentiveEra, IssueLifecycle, IssueSummary,
    OOS_CORRECTNESS_LABEL, PanelVerdict, RunLogCorpus, RunLogCorpusEvent, RunLogSelection,
    STALLED_PREFIX, VerdictGateInputs, VoterBallot, analyze_ground_truth, apply_verdict_gate,
    categorize, category_breakdown, coverage_stats, issue_number_from_url, ndjson_filed_evidence,
    parse_oos_blocks, realized_alignment_rate,
    report::growth_chart::{self, GrowthRow},
    scan_ground_truth_corpus, strip_prefixes, version_meets_floor,
};
use regex::Regex;
use serde_json::{Map, Value, json};

use crate::{
    argparse_compat::{parse_with_flags, usage_error},
    github_repository_resolution::{ambient_repo, repository_ref, validate_repo_slug},
    github_service::with_github_service,
    run_log_publication_commands::synchronized_corpus_root,
};

const FETCH_PROGRAM: &str = "cli.py analyze-issues fetch";
const FETCH_USAGE: &str =
    "usage: cli.py analyze-issues fetch [-h] --repo REPO --limit LIMIT --output OUTPUT";
const FETCH_HELP: &str = "usage: cli.py analyze-issues fetch [-h] --repo REPO --limit LIMIT --output\n                                   OUTPUT\n\noptions:\n  -h, --help       show this help message and exit\n  --repo REPO\n  --limit LIMIT\n  --output OUTPUT\n";
const ANALYZE_PROGRAM: &str = "cli.py analyze-issues analyze";
const ANALYZE_USAGE: &str = "usage: cli.py analyze-issues analyze [-h] --json JSON [--span-days SPAN_DAYS]\n                                           [--top-k TOP_K] [--categories {auto,default}]\n                                           [--log-root LOG_ROOT] [--repo REPO]\n                                           [--filed-issue-details-json FILED_ISSUE_DETAILS_JSON]\n                                           [--ground-truth-verdict] [--since-date SINCE_DATE]\n                                           [--min-runs MIN_RUNS] [--min-larch-version MIN_LARCH_VERSION]\n                                           [--lenient]";
const ANALYZE_HELP: &str = "usage: cli.py analyze-issues analyze [-h] --json JSON [--span-days SPAN_DAYS]\n                                           [--top-k TOP_K] [--categories {auto,default}]\n                                           [--log-root LOG_ROOT] [--repo REPO]\n                                           [--filed-issue-details-json FILED_ISSUE_DETAILS_JSON]\n                                           [--ground-truth-verdict] [--since-date SINCE_DATE]\n                                           [--min-runs MIN_RUNS] [--min-larch-version MIN_LARCH_VERSION]\n                                           [--lenient]\n\noptions:\n  -h, --help            show this help message and exit\n  --json JSON\n  --span-days SPAN_DAYS\n  --top-k TOP_K\n  --categories {auto,default}\n  --log-root LOG_ROOT\n  --repo REPO\n  --filed-issue-details-json FILED_ISSUE_DETAILS_JSON\n  --ground-truth-verdict\n  --since-date SINCE_DATE\n  --min-runs MIN_RUNS\n  --min-larch-version MIN_LARCH_VERSION\n  --lenient             Suppress the >5% threshold abort in load_issues for\n                        non-dict, malformed-number, or duplicate-number\n                        elements. Per-element stderr warnings are still\n                        emitted; this flag only disables the threshold check.\n";
const RUN_PROGRAM: &str = "cli.py analyze-issues run";
const RUN_USAGE: &str = "usage: cli.py analyze-issues run [-h] [--limit LIMIT] [--span-days SPAN_DAYS]\n                                        [--top-K TOP_K] [--categories {auto,default}] [--lenient]\n                                        [--log-root LOG_ROOT] [--repo REPO]\n                                        [--ground-truth-verdict] [--since-date SINCE_DATE]\n                                        [--min-runs MIN_RUNS] [--min-larch-version MIN_LARCH_VERSION]";
const RUN_HELP: &str = "usage: cli.py analyze-issues run [-h] [--limit LIMIT] [--span-days SPAN_DAYS]\n                                 [--top-K TOP_K] [--categories {auto,default}]\n                                 [--lenient] [--log-root LOG_ROOT]\n                                 [--repo REPO] [--ground-truth-verdict]\n                                 [--since-date SINCE_DATE]\n                                 [--min-runs MIN_RUNS]\n                                 [--min-larch-version MIN_LARCH_VERSION]\n\noptions:\n  -h, --help            show this help message and exit\n  --limit LIMIT\n  --span-days SPAN_DAYS\n  --top-K TOP_K, --top-k TOP_K\n  --categories {auto,default}\n  --lenient\n  --log-root LOG_ROOT\n  --repo REPO\n  --ground-truth-verdict\n  --since-date SINCE_DATE\n  --min-runs MIN_RUNS\n  --min-larch-version MIN_LARCH_VERSION\n";
// A full bounded REST list can contain 20 responses of up to 2 MiB each.
// Keep the offline cap above that maximum so `run` can always re-read the
// private snapshot it just fetched, while still bounding untrusted input.
const MAX_INPUT_BYTES: u64 = 64 * 1024 * 1024;
const MAX_GROWTH_BUCKETS: usize = 10_000;
const DEFAULT_TOP_K: usize = 10;
const MAX_TARGETED_DETAILS: usize = 200;
const DEFAULT_SINCE_DATE: &str = "2026-06-26";
const DEFAULT_MIN_LARCH_VERSION: &str = "52.1.0";
const INCENTIVE_ISSUE: u64 = 5_544;

static FILE_REFERENCE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b[[:alnum:]_.-]+(?:/[[:alnum:]_.-]+)*\.(?:rs|py|md|toml|json|yaml|yml|sh|ts|tsx|js|jsx|go|java|cpp|c|h)\b")
        .expect("file reference expression")
});
static REVERSAL: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?is)\b(revert|undo|superseded|re-introduce|re-add|closed in favor of)\b.*?(#[0-9]+|[0-9a-f]{7,40}|https?://\S+)?")
        .expect("reversal expression")
});
static ATTRIBUTION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)^\s*(?:[-*]\s*)?(?:\*\*\s*)?(?:reviewer|surfaced\s+by)\s*(?:\*\*)?\s*[:\-]\s*(.+?)\s*$")
        .expect("reviewer attribution expression")
});
static TOOL: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(codex|cursor|claude|main\s+agent|code,\s*claude\s+code\s+reviewer|code)\b")
        .expect("review tool expression")
});
static PERSONA: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(architect|arch|correctness|edge-cases|edge|structure|testing|innovation|pragmatic|security|generic)\b")
        .expect("review persona expression")
});
static VOTE_TALLY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?i)YES\s*=\s*(\d+)\s*[,\s]+\s*NO\s*=\s*(\d+)(?:\s*[,\s]+\s*EXONERATE\s*=\s*(\d+))?",
    )
    .expect("vote tally expression")
});
static COMBINED_AWAY_MARKER: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)<!--\s*larch:combined-away\s+source=#\d+\s+target=#\d+\s*-->")
        .expect("combined-away marker expression")
});
static COMBINED_AWAY_COMMENT: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)<!--\s*larch:combined-away\s+source=#\d+\s+target=#\d+\s*-->|\bCombined\s+into\s+#\d+\b")
        .expect("combined-away comment expression")
});
static REVIEWER_LINE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?(?:reviewer\(s\)|reviewers?|surfaced\s+by)(?:\*\*)?\s*[:\-]\s*(.+?)\s*$")
        .expect("accepted OOS reviewer expression")
});
static PRIVATE_WRITE_NONCE: AtomicU64 = AtomicU64::new(0);

#[derive(Clone, Debug)]
pub struct AnalysisIssue {
    pub summary: IssueSummary,
    url: String,
    comments: Vec<String>,
    fetch_failed: bool,
    degraded_fields: BTreeSet<String>,
    present_fields: BTreeSet<String>,
}

impl AnalysisIssue {
    pub fn from_value(value: &Value) -> Option<Self> {
        let summary = IssueSummary::from_json(value)?;
        let object = value.as_object()?;
        let url = string(object, "url");
        let comments = object
            .get("comments")
            .and_then(Value::as_array)
            .map(|items| {
                items
                    .iter()
                    .filter_map(|item| match item {
                        Value::String(text) => Some(text.clone()),
                        Value::Object(fields) => Some(string(fields, "body")),
                        _ => None,
                    })
                    .collect()
            })
            .unwrap_or_default();
        let degraded_fields = object
            .get("_larch_degraded_fields")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .map(str::to_owned)
            .collect();
        let fetch_failed = object
            .get("__fetch_failed__")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let present_fields = object.keys().cloned().collect();
        Some(Self {
            summary,
            url,
            comments,
            fetch_failed,
            degraded_fields,
            present_fields,
        })
    }
}

#[derive(Clone, Debug)]
struct AnalyzeOptions {
    json_path: PathBuf,
    span_days: i64,
    top_k: usize,
    categories: CategoryChoice,
    log_root: PathBuf,
    repo: Option<String>,
    filed_details_path: Option<PathBuf>,
    ground_truth_verdict: bool,
    since_date: String,
    min_runs: String,
    min_larch_version: String,
    lenient: bool,
    enrichment_degradation: Option<String>,
    targeted_fetch_degradation: Option<String>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum CategoryChoice {
    Auto,
    Default,
}

impl CategoryChoice {
    const fn core(self) -> larch_core::CategoryMode {
        match self {
            Self::Auto => larch_core::CategoryMode::Auto,
            Self::Default => larch_core::CategoryMode::Default,
        }
    }
}

#[derive(Clone, Debug)]
struct RunOptions {
    limit: String,
    span_days: i64,
    top_k: usize,
    categories: CategoryChoice,
    log_root: Option<PathBuf>,
    repo: Option<String>,
    ground_truth_verdict: bool,
    since_date: String,
    min_runs: String,
    min_larch_version: String,
    lenient: bool,
}

/// Fetch a bounded private JSON issue snapshot through the typed GitHub service.
#[must_use]
pub fn fetch(arguments: &[OsString]) -> ExitCode {
    let help = help_position(arguments);
    let parsed = parse_with_flags(
        &arguments[..help.unwrap_or(arguments.len())],
        &["--repo", "--limit", "--output"],
        &[],
        0,
    );
    if let Some(error) = parsed.value_error() {
        return usage_error(FETCH_USAGE, FETCH_PROGRAM, error, 2);
    }
    if help.is_some() {
        print!("{FETCH_HELP}");
        return ExitCode::SUCCESS;
    }
    let missing: Vec<&str> = ["--repo", "--limit", "--output"]
        .into_iter()
        .filter(|name| parsed.value(name).is_none())
        .collect();
    if !missing.is_empty() {
        return usage_error(
            FETCH_USAGE,
            FETCH_PROGRAM,
            &format!(
                "the following arguments are required: {}",
                missing.join(", ")
            ),
            2,
        );
    }
    if let Some(error) = parsed.error() {
        return usage_error(FETCH_USAGE, FETCH_PROGRAM, &error, 2);
    }
    let repo = option_text(&parsed, "--repo");
    let limit = option_text(&parsed, "--limit");
    let output = PathBuf::from(option_text(&parsed, "--output"));
    let Some(limit) = digits_usize(&limit) else {
        eprintln!("ERROR=gh issue list failed for repo {repo}");
        return ExitCode::FAILURE;
    };
    let Ok(reference) = repository_ref(&repo) else {
        eprintln!("ERROR=gh issue list failed for repo {repo}");
        return ExitCode::FAILURE;
    };
    if limit == 0 {
        if let Err(error) = private_write(&output, "[]") {
            eprintln!("ERROR=gh issue list failed for repo {repo}: {error}");
            return ExitCode::FAILURE;
        }
        return ExitCode::SUCCESS;
    }
    let listed = with_github_service(async |service, cancellation| {
        let request = GitHubIssueList {
            repo: reference.clone(),
            state: GitHubIssueState::All,
            labels: Vec::new(),
            limit: limit.min(service.transport_policy().limits().items()),
            mode: GitHubIssueListMode::BoundedPartial,
            body_mode: GitHubIssueBodyMode::Include,
        };
        let issues = service
            .list_issues(&request, cancellation)
            .await
            .map_err(|error| error.to_string())?
            .issues;
        let wanted: BTreeSet<u64> = issues.iter().map(|issue| issue.number).collect();
        let closures = service
            .issue_closure_references(cancellation, reference.owner(), reference.name(), &wanted)
            .await
            .ok();
        Ok::<_, String>((issues, closures))
    });
    let Ok((issues, closures)) = listed else {
        eprintln!("ERROR=gh issue list failed for repo {repo}");
        return ExitCode::FAILURE;
    };
    let payload = Value::Array(
        issues
            .iter()
            .map(|issue| {
                issue_json(
                    issue,
                    closures
                        .as_ref()
                        .and_then(|rows| rows.get(&issue.number).map(Vec::as_slice)),
                )
            })
            .collect(),
    );
    let Ok(text) = serde_json::to_string(&payload) else {
        eprintln!("ERROR=gh issue list failed for repo {repo}");
        return ExitCode::FAILURE;
    };
    match private_write(&output, &text) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("ERROR=gh issue list failed for repo {repo}: {error}");
            ExitCode::FAILURE
        }
    }
}

/// Analyze one recorded JSON issue snapshot.
#[must_use]
pub fn analyze(arguments: &[OsString]) -> ExitCode {
    let options = match parse_analyze(arguments) {
        Ok(options) => options,
        Err(exit) => return exit,
    };
    analyze_options(&options)
}

/// Fetch a snapshot and analyze it with the synchronized corpus by default.
#[must_use]
pub fn run(arguments: &[OsString]) -> ExitCode {
    let options = match parse_run(arguments) {
        Ok(options) => options,
        Err(exit) => return exit,
    };
    let log_root = match options.log_root.clone() {
        Some(root) => root,
        None => match synchronized_corpus_root(Path::new(".")) {
            Ok(root) => root,
            Err(error) => {
                eprintln!("ERROR: {error}");
                return ExitCode::from(2);
            }
        },
    };
    let repo = options.repo.clone().or_else(ambient_repo);
    let Some(repo) = repo.filter(|candidate| validate_repo_slug(candidate)) else {
        eprintln!(
            "WARN targeted comment fetch unavailable: unable to detect GitHub repo owner/name"
        );
        return render_without_enrichment(
            &options,
            log_root,
            None,
            "repo_unavailable",
            &BTreeMap::new(),
            None,
        );
    };
    let temporary = env::temp_dir().join(format!(
        "{}-issues.json",
        repo.replace('/', "-")
            .chars()
            .filter(|character| character.is_ascii_alphanumeric() || matches!(character, '-' | '_'))
            .collect::<String>()
    ));
    let fetch_arguments = vec![
        OsString::from("--repo"),
        OsString::from(&repo),
        OsString::from("--limit"),
        OsString::from(&options.limit),
        OsString::from("--output"),
        temporary.as_os_str().to_owned(),
    ];
    if fetch(&fetch_arguments) != ExitCode::SUCCESS {
        eprintln!("WARN bulk gh issue list failed; continuing with log-only fate scoring");
        let records = filed_oos_records(&log_root);
        let (details, targeted_degradation) = fetch_filed_issue_details(&repo, &records, &[]);
        return render_without_enrichment(
            &options,
            log_root,
            Some(repo),
            "bulk_fetch_failed",
            &details,
            targeted_degradation,
        );
    }
    let mut analyze = AnalyzeOptions {
        json_path: temporary.clone(),
        span_days: options.span_days,
        top_k: options.top_k,
        categories: options.categories,
        log_root,
        repo: Some(repo),
        filed_details_path: None,
        ground_truth_verdict: options.ground_truth_verdict,
        since_date: options.since_date.clone(),
        min_runs: options.min_runs.clone(),
        min_larch_version: options.min_larch_version.clone(),
        lenient: options.lenient,
        enrichment_degradation: None,
        targeted_fetch_degradation: None,
    };
    match load_issues(&temporary, analyze.lenient) {
        Ok(issues) => {
            let (mut details, degradation) = fetch_filed_issue_details(
                analyze.repo.as_deref().unwrap_or_default(),
                &filed_oos_records(&analyze.log_root),
                &issues,
            );
            analyze.targeted_fetch_degradation = degradation;
            analyze_loaded(&issues, &mut details, &analyze)
        }
        Err(error) => {
            eprintln!("WARN corrupt issue dump; continuing with log-only fate scoring ({error})");
            let records = filed_oos_records(&analyze.log_root);
            let (details, targeted_degradation) = fetch_filed_issue_details(
                analyze.repo.as_deref().unwrap_or_default(),
                &records,
                &[],
            );
            render_without_enrichment(
                &options,
                analyze.log_root.clone(),
                analyze.repo,
                "bulk_fetch_failed",
                &details,
                targeted_degradation,
            )
        }
    }
}

fn help_position(arguments: &[OsString]) -> Option<usize> {
    arguments.iter().position(|argument| {
        let text = argument.to_string_lossy();
        text == "-h" || text == "--help"
    })
}

fn render_without_enrichment(
    options: &RunOptions,
    log_root: PathBuf,
    repo: Option<String>,
    degradation: &str,
    details: &BTreeMap<u64, AnalysisIssue>,
    targeted_degradation: Option<String>,
) -> ExitCode {
    let analyze = AnalyzeOptions {
        json_path: PathBuf::new(),
        span_days: options.span_days,
        top_k: options.top_k,
        categories: options.categories,
        log_root,
        repo,
        filed_details_path: None,
        ground_truth_verdict: options.ground_truth_verdict,
        since_date: options.since_date.clone(),
        min_runs: options.min_runs.clone(),
        min_larch_version: options.min_larch_version.clone(),
        lenient: true,
        enrichment_degradation: Some(degradation.to_owned()),
        targeted_fetch_degradation: targeted_degradation,
    };
    let issues = Vec::new();
    let mut details = details.clone();
    if analyze.ground_truth_verdict {
        return ground_truth_verdict(&issues, &mut details, &analyze);
    }
    print_report(&issues, &details, &analyze, Some(degradation));
    ExitCode::SUCCESS
}

fn analyze_options(options: &AnalyzeOptions) -> ExitCode {
    let issues = match load_issues(&options.json_path, options.lenient) {
        Ok(issues) => issues,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    let (mut filed_details, targeted_fetch_degradation) =
        match load_filed_details(options.filed_details_path.as_deref()) {
            Ok(details) => details,
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        };
    let mut options = options.clone();
    options.targeted_fetch_degradation = options
        .targeted_fetch_degradation
        .or(targeted_fetch_degradation);
    analyze_loaded(&issues, &mut filed_details, &options)
}

fn analyze_loaded(
    issues: &[AnalysisIssue],
    filed_details: &mut BTreeMap<u64, AnalysisIssue>,
    options: &AnalyzeOptions,
) -> ExitCode {
    if options.ground_truth_verdict {
        return ground_truth_verdict(issues, filed_details, options);
    }
    if issues.is_empty() {
        println!("No issues to analyze.");
        return ExitCode::SUCCESS;
    }
    let degraded = options
        .enrichment_degradation
        .clone()
        .or_else(|| issue_degradation(issues));
    print_report(issues, filed_details, options, degraded.as_deref());
    ExitCode::SUCCESS
}

fn parse_analyze(arguments: &[OsString]) -> Result<AnalyzeOptions, ExitCode> {
    const OPTIONS: &[&str] = &[
        "--json",
        "--span-days",
        "--top-k",
        "--categories",
        "--log-root",
        "--repo",
        "--filed-issue-details-json",
        "--since-date",
        "--min-runs",
        "--min-larch-version",
    ];
    const FLAGS: &[&str] = &["--ground-truth-verdict", "--lenient"];
    let help = help_position(arguments);
    let parsed = parse_with_flags(
        &arguments[..help.unwrap_or(arguments.len())],
        OPTIONS,
        FLAGS,
        0,
    );
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(ANALYZE_USAGE, ANALYZE_PROGRAM, error, 2));
    }
    let span_days = integer_option(&parsed, "--span-days", 0, ANALYZE_USAGE, ANALYZE_PROGRAM)?;
    let top_k = integer_option(&parsed, "--top-k", 10, ANALYZE_USAGE, ANALYZE_PROGRAM)?
        .max(1)
        .try_into()
        .map_err(|_| usage_error(ANALYZE_USAGE, ANALYZE_PROGRAM, "--top-k is too large", 2))?;
    let categories = categories_option(&parsed, ANALYZE_USAGE, ANALYZE_PROGRAM)?;
    if help.is_some() {
        print!("{ANALYZE_HELP}");
        return Err(ExitCode::SUCCESS);
    }
    if parsed.value("--json").is_none() {
        return Err(usage_error(
            ANALYZE_USAGE,
            ANALYZE_PROGRAM,
            "the following arguments are required: --json",
            2,
        ));
    }
    if let Some(error) = parsed.error() {
        return Err(usage_error(ANALYZE_USAGE, ANALYZE_PROGRAM, &error, 2));
    }
    Ok(AnalyzeOptions {
        json_path: PathBuf::from(option_text(&parsed, "--json")),
        span_days: span_days.max(0),
        top_k,
        categories,
        log_root: PathBuf::from(option_text_or(&parsed, "--log-root", "larch-logs")),
        repo: nonempty_option(&parsed, "--repo"),
        filed_details_path: nonempty_option(&parsed, "--filed-issue-details-json")
            .map(PathBuf::from),
        ground_truth_verdict: parsed.flag("--ground-truth-verdict"),
        since_date: option_text_or(&parsed, "--since-date", DEFAULT_SINCE_DATE),
        min_runs: option_text_or(&parsed, "--min-runs", "150"),
        min_larch_version: option_text_or(
            &parsed,
            "--min-larch-version",
            DEFAULT_MIN_LARCH_VERSION,
        ),
        lenient: parsed.flag("--lenient"),
        enrichment_degradation: None,
        targeted_fetch_degradation: None,
    })
}

fn parse_run(arguments: &[OsString]) -> Result<RunOptions, ExitCode> {
    const OPTIONS: &[&str] = &[
        "--limit",
        "--span-days",
        "--top-K",
        "--top-k",
        "--categories",
        "--log-root",
        "--repo",
        "--since-date",
        "--min-runs",
        "--min-larch-version",
    ];
    const FLAGS: &[&str] = &["--lenient", "--ground-truth-verdict"];
    let help = help_position(arguments);
    let parsed = parse_with_flags(
        &arguments[..help.unwrap_or(arguments.len())],
        OPTIONS,
        FLAGS,
        0,
    );
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(RUN_USAGE, RUN_PROGRAM, error, 2));
    }
    let categories = categories_option(&parsed, RUN_USAGE, RUN_PROGRAM)?;
    if help.is_some() {
        print!("{RUN_HELP}");
        return Err(ExitCode::SUCCESS);
    }
    if let Some(error) = parsed.error() {
        return Err(usage_error(RUN_USAGE, RUN_PROGRAM, &error, 2));
    }
    let top_k = parsed
        .entries()
        .iter()
        .rev()
        .find(|(name, _value)| *name == "--top-k" || *name == "--top-K")
        .and_then(|(_name, value)| digits_usize(&value.to_string_lossy()))
        .unwrap_or(DEFAULT_TOP_K)
        .max(1);
    Ok(RunOptions {
        limit: option_text_or(&parsed, "--limit", "2000"),
        span_days: digits_i64(&option_text_or(&parsed, "--span-days", "0")).unwrap_or(0),
        top_k,
        categories,
        log_root: nonempty_option(&parsed, "--log-root").map(PathBuf::from),
        repo: nonempty_option(&parsed, "--repo"),
        ground_truth_verdict: parsed.flag("--ground-truth-verdict"),
        since_date: option_text_or(&parsed, "--since-date", DEFAULT_SINCE_DATE),
        min_runs: option_text_or(&parsed, "--min-runs", "150"),
        min_larch_version: option_text_or(
            &parsed,
            "--min-larch-version",
            DEFAULT_MIN_LARCH_VERSION,
        ),
        lenient: parsed.flag("--lenient"),
    })
}

fn categories_option(
    parsed: &crate::argparse_compat::ParsedCommandLine,
    usage: &str,
    program: &str,
) -> Result<CategoryChoice, ExitCode> {
    match option_text_or(parsed, "--categories", "default").as_str() {
        "auto" => Ok(CategoryChoice::Auto),
        "default" => Ok(CategoryChoice::Default),
        value => Err(usage_error(
            usage,
            program,
            &format!(
                "argument --categories: invalid choice: '{value}' (choose from 'auto', 'default')"
            ),
            2,
        )),
    }
}

fn integer_option(
    parsed: &crate::argparse_compat::ParsedCommandLine,
    name: &str,
    default: i64,
    usage: &str,
    program: &str,
) -> Result<i64, ExitCode> {
    let Some(value) = parsed.value(name) else {
        return Ok(default);
    };
    let text = value.to_string_lossy();
    text.parse::<i64>().map_err(|_| {
        usage_error(
            usage,
            program,
            &format!("argument {name}: invalid int value: '{text}'"),
            2,
        )
    })
}

fn option_text(parsed: &crate::argparse_compat::ParsedCommandLine, name: &str) -> String {
    parsed
        .value(name)
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default()
}

fn option_text_or(
    parsed: &crate::argparse_compat::ParsedCommandLine,
    name: &str,
    default: &str,
) -> String {
    parsed.value(name).map_or_else(
        || default.to_owned(),
        |value| value.to_string_lossy().into_owned(),
    )
}

fn nonempty_option(
    parsed: &crate::argparse_compat::ParsedCommandLine,
    name: &str,
) -> Option<String> {
    let value = option_text(parsed, name);
    (!value.is_empty()).then_some(value)
}

fn digits_usize(value: &str) -> Option<usize> {
    (!value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| value.parse().ok())
        .flatten()
}

fn digits_u64(value: &str) -> Option<u64> {
    (!value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| value.parse().ok())
        .flatten()
        .filter(|value| *value > 0)
}

fn digits_i64(value: &str) -> Option<i64> {
    (!value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| value.parse().ok())
        .flatten()
}

fn issue_json(issue: &GitHubIssue, closure_references: Option<&[String]>) -> Value {
    let mut value = json!({
        "number": issue.number,
        "title": issue.title,
        "state": match issue.state { GitHubIssueState::Open => "OPEN", GitHubIssueState::Closed => "CLOSED", GitHubIssueState::All => "" },
        "createdAt": issue.created_at,
        "closedAt": issue.closed_at,
        "body": issue.body,
        "labels": issue.labels.iter().map(|label| json!({"name": label.name})).collect::<Vec<_>>(),
        "closedByPullRequestsReferences": closure_references.unwrap_or_default().iter().map(|url| json!({"url": url})).collect::<Vec<_>>(),
        "url": issue.url,
        "stateReason": issue.state_reason,
    });
    if closure_references.is_none() {
        value.as_object_mut().expect("JSON object").insert(
            "_larch_degraded_fields".to_owned(),
            json!(["closedByPullRequestsReferences"]),
        );
    }
    value
}

fn issue_with_comments(
    issue: &GitHubIssue,
    comments: &[GitHubComment],
    closure_references: Option<&[String]>,
) -> Option<AnalysisIssue> {
    let mut value = issue_json(issue, closure_references);
    value.as_object_mut()?.insert(
        "comments".to_owned(),
        Value::Array(
            comments
                .iter()
                .map(|comment| json!({"body": comment.body}))
                .collect(),
        ),
    );
    AnalysisIssue::from_value(&value)
}

fn failed_filed_issue(number: u64) -> AnalysisIssue {
    AnalysisIssue::from_value(&json!({"number": number, "__fetch_failed__": true}))
        .expect("a positive targeted issue number is always a valid summary")
}

pub fn fetch_filed_issue_details(
    repo: &str,
    records: &[FiledOos],
    bulk_issues: &[AnalysisIssue],
) -> (BTreeMap<u64, AnalysisIssue>, Option<String>) {
    let numbers: BTreeSet<u64> = records.iter().filter_map(|record| record.number).collect();
    if numbers.is_empty() {
        return (BTreeMap::new(), None);
    }
    let bounded: Vec<u64> = numbers.iter().copied().take(MAX_TARGETED_DETAILS).collect();
    let limit_degraded = numbers.len() > bounded.len();
    if limit_degraded {
        eprintln!("WARN targeted comment fetch capped at {MAX_TARGETED_DETAILS} filed OOS issues");
    }
    let Ok(reference) = repository_ref(repo) else {
        return (BTreeMap::new(), Some("targeted_repo_invalid".to_owned()));
    };
    let known_closures: BTreeMap<u64, Vec<String>> = bulk_issues
        .iter()
        .filter(|issue| {
            !issue
                .degraded_fields
                .iter()
                .any(|field| field == "closedByPullRequestsReferences")
        })
        .map(|issue| {
            (
                issue.summary.number,
                issue.summary.closed_by_pull_requests.clone(),
            )
        })
        .collect();
    let missing_closures: BTreeSet<u64> = bounded
        .iter()
        .copied()
        .filter(|number| !known_closures.contains_key(number))
        .collect();
    let fetched = with_github_service(async |service, cancellation| {
        let mut details = BTreeMap::new();
        let fetched_closures = if missing_closures.is_empty() {
            Some(BTreeMap::new())
        } else {
            service
                .issue_closure_references(
                    cancellation,
                    reference.owner(),
                    reference.name(),
                    &missing_closures,
                )
                .await
                .ok()
        };
        let mut failures = !missing_closures.is_empty()
            && fetched_closures
                .as_ref()
                .is_none_or(|closures| closures.len() != missing_closures.len());
        for number in &bounded {
            let Ok(issue) = service.issue(&reference, *number, cancellation).await else {
                failures = true;
                details.insert(*number, failed_filed_issue(*number));
                continue;
            };
            let Ok(comments) = service
                .list_comments(&reference, *number, cancellation)
                .await
            else {
                failures = true;
                details.insert(*number, failed_filed_issue(*number));
                continue;
            };
            if let Some(detail) = issue_with_comments(
                &issue,
                &comments,
                known_closures.get(number).map(Vec::as_slice).or_else(|| {
                    fetched_closures
                        .as_ref()
                        .and_then(|closures| closures.get(number).map(Vec::as_slice))
                }),
            ) {
                details.insert(*number, detail);
            } else {
                failures = true;
                details.insert(*number, failed_filed_issue(*number));
            }
        }
        Ok::<_, String>((details, failures))
    });
    match fetched {
        Ok((details, failed)) if !failed && !limit_degraded => (details, None),
        Ok((details, _)) => (details, Some("targeted_fetch_degraded".to_owned())),
        Err(_) => (BTreeMap::new(), Some("targeted_fetch_degraded".to_owned())),
    }
}

pub fn fetch_incentive_issue(repo: &str) -> Option<AnalysisIssue> {
    let reference = repository_ref(repo).ok()?;
    let wanted = BTreeSet::from([INCENTIVE_ISSUE]);
    with_github_service(async |service, cancellation| {
        let issue = service
            .issue(&reference, INCENTIVE_ISSUE, cancellation)
            .await
            .map_err(|error| error.to_string())?;
        let closures = service
            .issue_closure_references(cancellation, reference.owner(), reference.name(), &wanted)
            .await
            .map_err(|error| error.to_string())?;
        Ok::<_, String>(
            closures
                .get(&INCENTIVE_ISSUE)
                .and_then(|references| issue_with_comments(&issue, &[], Some(references))),
        )
    })
    .ok()
    .flatten()
}

/// Fill the verdict-only calibration prerequisite through the same typed
/// service read used for the bounded backlog when its snapshot omits #5544.
/// Normal reports remain fully offline once their inputs are loaded.
fn ensure_incentive_detail(
    issues: &[AnalysisIssue],
    details: &mut BTreeMap<u64, AnalysisIssue>,
    repo: Option<&str>,
    verdict_requested: bool,
) {
    if !verdict_requested
        || issues
            .iter()
            .any(|issue| issue.summary.number == INCENTIVE_ISSUE)
        || details.contains_key(&INCENTIVE_ISSUE)
    {
        return;
    }
    if let Some(repo) = repo
        && let Some(incentive) = fetch_incentive_issue(repo)
    {
        details.insert(INCENTIVE_ISSUE, incentive);
    }
}

fn private_write(path: &Path, text: &str) -> Result<(), String> {
    let parent = path.parent().unwrap_or_else(|| Path::new("."));
    let parent_metadata = fs::symlink_metadata(parent).map_err(|error| error.to_string())?;
    if parent_metadata.file_type().is_symlink() || !parent_metadata.is_dir() {
        return Err("output parent is not a directory".to_owned());
    }
    if let Ok(metadata) = fs::symlink_metadata(path)
        && (metadata.file_type().is_symlink() || !metadata.is_file())
    {
        return Err("output path is not a regular file".to_owned());
    }
    let nonce = PRIVATE_WRITE_NONCE.fetch_add(1, Ordering::Relaxed);
    let temporary = parent.join(format!(
        ".{}.tmp.{}.{}",
        path.file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("issues"),
        std::process::id(),
        nonce,
    ));
    let outcome = (|| {
        let mut options = fs::OpenOptions::new();
        options.write(true).create_new(true);
        #[cfg(unix)]
        options.mode(0o600);
        let mut file = options
            .open(&temporary)
            .map_err(|error| error.to_string())?;
        file.write_all(text.as_bytes())
            .map_err(|error| error.to_string())?;
        file.sync_all().map_err(|error| error.to_string())?;
        #[cfg(unix)]
        {
            fs::set_permissions(&temporary, fs::Permissions::from_mode(0o600))
                .map_err(|error| error.to_string())?;
        }
        fs::rename(&temporary, path).map_err(|error| error.to_string())
    })();
    if outcome.is_err() {
        let _removed = fs::remove_file(&temporary);
    }
    outcome
}

pub fn load_issues(path: &Path, lenient: bool) -> Result<Vec<AnalysisIssue>, String> {
    if path.as_os_str().is_empty() {
        return Ok(Vec::new());
    }
    let metadata = fs::metadata(path).map_err(|error| {
        format!(
            "ERROR=Unable to parse issue JSON dump at {}: {error}",
            path.display()
        )
    })?;
    if metadata.len() > MAX_INPUT_BYTES {
        return Err(format!(
            "ERROR=issue JSON exceeds {MAX_INPUT_BYTES} bytes: {}",
            path.display()
        ));
    }
    let bytes = fs::read(path).map_err(|error| {
        format!(
            "ERROR=Unable to parse issue JSON dump at {}: {error}",
            path.display()
        )
    })?;
    let parsed: Value = serde_json::from_slice(&bytes).map_err(|error| {
        format!(
            "ERROR=Unable to parse issue JSON dump at {}: {error}",
            path.display()
        )
    })?;
    let Some(rows) = parsed.as_array() else {
        return Err(format!(
            "ERROR=Issue JSON dump at {} is not a list",
            path.display()
        ));
    };
    let mut issues = Vec::new();
    let mut invalid = 0_usize;
    let mut seen = BTreeMap::new();
    for (index, row) in rows.iter().enumerate() {
        let Some(object) = row.as_object() else {
            invalid += 1;
            eprintln!(
                "WARN load_issues: skipping non-dict element at index {index}: {}",
                value_preview(row)
            );
            continue;
        };
        let Some(issue) = AnalysisIssue::from_value(row) else {
            invalid += 1;
            let reason = if object.contains_key("number") {
                "non-numeric"
            } else {
                "missing"
            };
            eprintln!(
                "WARN load_issues: skipping issue with {reason} number at index {index}: {}",
                value_preview(object.get("number").unwrap_or(&Value::Null))
            );
            continue;
        };
        if let Some(prior_index) = seen.insert(issue.summary.number, index) {
            invalid += 1;
            eprintln!(
                "WARN load_issues: skipping duplicate parsed number {} at index {index} (first occurrence at index {prior_index} retained)",
                issue.summary.number,
            );
            continue;
        }
        issues.push(issue);
    }
    if !lenient && !rows.is_empty() && invalid * 20 > rows.len() {
        #[expect(
            clippy::cast_precision_loss,
            reason = "the bounded issue snapshot count is exactly representable"
        )]
        let skipped_pct = invalid as f64 / rows.len() as f64 * 100.0;
        return Err(format!(
            "ERROR=load_issues skipped {invalid}/{} non-dict, malformed-number, or duplicate-number elements ({skipped_pct:.1}% > 5% threshold) in {}; pass --lenient to suppress this check",
            rows.len(),
            path.display()
        ));
    }
    Ok(issues)
}

fn value_preview(value: &Value) -> String {
    let preview = if value.is_null() {
        "None".to_owned()
    } else if let Some(value) = value.as_bool() {
        if value { "True" } else { "False" }.to_owned()
    } else if let Some(value) = value.as_str() {
        format!("{value:?}")
    } else {
        value.to_string()
    };
    let mut characters = preview.chars();
    let truncated: String = characters.by_ref().take(57).collect();
    if characters.next().is_some() {
        format!("{truncated}...")
    } else {
        preview
    }
}

fn load_filed_details(
    path: Option<&Path>,
) -> Result<(BTreeMap<u64, AnalysisIssue>, Option<String>), String> {
    let Some(path) = path else {
        return Ok((BTreeMap::new(), None));
    };
    let metadata = fs::metadata(path).map_err(|error| format!("ERROR={error}"))?;
    if metadata.len() > MAX_INPUT_BYTES {
        return Err(format!(
            "ERROR=filed issue details JSON exceeds {MAX_INPUT_BYTES} bytes: {}",
            path.display()
        ));
    }
    let bytes = fs::read(path).map_err(|error| format!("ERROR={error}"))?;
    let value: Value = serde_json::from_slice(&bytes).map_err(|error| {
        format!(
            "ERROR=invalid filed issue details JSON {}: {error}",
            path.display()
        )
    })?;
    let Some(rows) = value.as_object() else {
        return Err(format!(
            "ERROR=--filed-issue-details-json must contain an object: {}",
            path.display()
        ));
    };
    let mut details = BTreeMap::new();
    let mut targeted_fetch_failed = false;
    for (key, item) in rows {
        let Some(number) = digits_u64(key) else {
            return Err(format!(
                "ERROR=invalid filed issue details key '{key}': non-numeric"
            ));
        };
        let mut normalized = item.clone();
        let Some(fields) = normalized.as_object_mut() else {
            continue;
        };
        targeted_fetch_failed |= fields
            .get("__fetch_failed__")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        fields.insert("number".to_owned(), json!(number));
        if let Some(issue) = AnalysisIssue::from_value(&normalized) {
            details.insert(number, issue);
        }
    }
    Ok((
        details,
        targeted_fetch_failed.then_some("targeted_fetch_degraded".to_owned()),
    ))
}

fn string(object: &Map<String, Value>, field: &str) -> String {
    object
        .get(field)
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned()
}

fn issue_degradation(issues: &[AnalysisIssue]) -> Option<String> {
    let mut fields = BTreeSet::<String>::new();
    for issue in issues {
        // `IssueSummary` records state-reason degradation; the fixed GraphQL
        // closure query records its own unavailable-field marker.
        if issue.summary.state_reason_degraded {
            fields.insert("stateReason".to_owned());
        }
        fields.extend(issue.degraded_fields.iter().cloned());
    }
    (!fields.is_empty()).then(|| {
        format!(
            "bulk_issue_fields_degraded:{}",
            fields.into_iter().collect::<Vec<_>>().join(",")
        )
    })
}

fn print_report(
    issues: &[AnalysisIssue],
    filed_details: &BTreeMap<u64, AnalysisIssue>,
    options: &AnalyzeOptions,
    degradation: Option<&str>,
) {
    let report = build_report(issues, filed_details, options, degradation);
    println!("{report}");
}

fn build_report(
    issues: &[AnalysisIssue],
    filed_details: &BTreeMap<u64, AnalysisIssue>,
    options: &AnalyzeOptions,
    degradation: Option<&str>,
) -> String {
    let summaries: Vec<IssueSummary> = issues.iter().map(|issue| issue.summary.clone()).collect();
    let stats = coverage_stats(&summaries);
    let categories = categorize(&summaries, options.categories.core(), options.top_k);
    let category_counts = category_breakdown(&summaries, &categories);
    let reviewer = reviewer_effectiveness(issues);
    let sections = vec![
        executive_summary(&stats, &category_counts, &reviewer),
        render_coverage(&stats),
        render_category_breakdown(&category_counts),
        render_growth_chart(&summaries, &categories, options.span_days),
        pattern_observations(issues, options.top_k, &stats),
        wasteful_findings(issues, options.top_k),
        reviewer.text,
        render_high_risk_oos(issues, options.top_k),
        fate_adjusted_oos(
            issues,
            filed_details,
            &options.log_root,
            options.repo.as_deref(),
            degradation,
            options.targeted_fetch_degradation.as_deref(),
        ),
        ground_truth_report(
            issues,
            &options.log_root,
            degradation,
            options.top_k,
            None,
            None,
        ),
    ];
    sections.join("\n\n")
}

fn executive_summary(
    stats: &larch_core::CoverageStats,
    categories: &[larch_core::CategoryCount],
    reviewer: &ReviewerReport,
) -> String {
    let dominant = categories
        .iter()
        .take(3)
        .map(|row| row.label.as_str())
        .collect::<Vec<_>>()
        .join(", ");
    let dominant = if dominant.is_empty() {
        "no dominant categories"
    } else {
        &dominant
    };
    let best = reviewer.best.as_ref().map_or_else(
        || "no reviewer/persona pair with at least 10 findings".to_owned(),
        |row| {
            format!(
                "{} / {} ({}/{} done, {:.1}%)",
                row.tool,
                row.persona,
                row.done,
                row.total,
                row.rate * 100.0
            )
        },
    );
    format!(
        "## Executive Summary\nAnalyzed {} issues across {} to {}. Dominant categories: {dominant}. The strongest waste signals are duplicate titles, stalled issues, reversal/supersession mentions, and PR closure clusters listed below. Highest-ROI reviewer/persona signal: {best}.",
        stats.total,
        stats
            .oldest
            .map_or_else(|| "n/a".to_owned(), |date| date.to_string()),
        stats
            .newest
            .map_or_else(|| "n/a".to_owned(), |date| date.to_string()),
    )
}

fn render_coverage(stats: &larch_core::CoverageStats) -> String {
    format!(
        "## Coverage Stats\n- Total issues: {}\n- Open / closed: {} / {}\n- Created date range: {} -> {}\n- Time to close: median {}, P90 {}\n- Closed by PR reference: {:.1}% of closed issues",
        stats.total,
        stats.open,
        stats.closed,
        stats
            .oldest
            .map_or_else(|| "n/a".to_owned(), |date| date.to_string()),
        stats
            .newest
            .map_or_else(|| "n/a".to_owned(), |date| date.to_string()),
        fmt_days(stats.median_close_days),
        fmt_days(stats.p90_close_days),
        stats.pr_closed_pct,
    )
}

fn fmt_days(value: Option<f64>) -> String {
    value.map_or_else(|| "n/a".to_owned(), |value| format!("{value:.1}d"))
}

fn render_category_breakdown(rows: &[larch_core::CategoryCount]) -> String {
    let mut lines = vec!["## Category Breakdown".to_owned()];
    lines.extend(
        rows.iter()
            .map(|row| format!("- {}: {} ({:.1}%)", row.label, row.count, row.share_pct)),
    );
    lines.join("\n")
}

fn render_growth_chart(
    issues: &[IssueSummary],
    categories: &larch_core::CategoryIndex,
    span_days: i64,
) -> String {
    let mut dated: Vec<(&IssueSummary, DateTime<Utc>)> = issues
        .iter()
        .filter_map(|issue| issue.created_at.map(|created| (issue, created)))
        .collect();
    if dated.is_empty() {
        return "## Growth Chart\nNo growth data available.".to_owned();
    }
    dated.sort_by_key(|(_issue, created)| *created);
    let newest = dated.last().map_or_else(Utc::now, |(_issue, date)| *date);
    let mut oldest = dated.first().map_or(newest, |(_issue, date)| *date);
    if span_days > 0 {
        let Some(duration) = Duration::try_days(span_days) else {
            return growth_chart_limit_message();
        };
        let Some(window_start) = newest.checked_sub_signed(duration) else {
            return growth_chart_limit_message();
        };
        oldest = window_start;
        dated.retain(|(_issue, created)| *created >= oldest);
    }
    let span = (newest.date_naive() - oldest.date_naive())
        .num_days()
        .max(0);
    let weekly = span > 60;
    let step = if weekly { 7 } else { 1 };
    let Ok(bucket_count) = usize::try_from(span / step + 1) else {
        return growth_chart_limit_message();
    };
    if bucket_count > MAX_GROWTH_BUCKETS {
        return growth_chart_limit_message();
    }
    let buckets: Vec<String> = (0..bucket_count)
        .map(|index| {
            (oldest + Duration::days(i64::try_from(index).unwrap_or(0) * step))
                .date_naive()
                .to_string()
        })
        .collect();
    let mut labels: Vec<String> = dated
        .iter()
        .map(|(issue, _)| categories.label_for(issue.number).label())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    let mut matrix: BTreeMap<String, Vec<i64>> = labels
        .iter()
        .map(|label| (label.clone(), vec![0; bucket_count]))
        .collect();
    for (issue, created) in dated {
        let label = categories.label_for(issue.number).label();
        let index = (created.date_naive() - oldest.date_naive()).num_days() / step;
        if let Some(row) = matrix.get_mut(&label)
            && let Some(cell) = usize::try_from(index.max(0))
                .ok()
                .and_then(|index| row.get_mut(index))
        {
            *cell += 1;
        }
    }
    for values in matrix.values_mut() {
        let mut running = 0_i64;
        for value in values {
            running += *value;
            *value = running;
        }
    }
    if labels.len() > 26 {
        let tail = labels.split_off(25);
        let mut overflow = vec![0_i64; bucket_count];
        for label in tail {
            if let Some(values) = matrix.remove(&label) {
                for (index, value) in values.into_iter().enumerate() {
                    overflow[index] += value;
                }
            }
        }
        labels.push("Other (overflow)".to_owned());
        matrix.insert("Other (overflow)".to_owned(), overflow);
    }
    let rows: Vec<GrowthRow> = labels
        .iter()
        .enumerate()
        .map(|(index, label)| GrowthRow {
            key: char::from(b'A' + u8::try_from(index).unwrap_or(0)).to_string(),
            label: label.clone(),
            values: matrix.get(label).cloned().unwrap_or_default(),
        })
        .collect();
    format!(
        "## Growth Chart\n{}",
        growth_chart::render_chart(&buckets, &rows)
    )
}

fn growth_chart_limit_message() -> String {
    format!(
        "## Growth Chart\nGrowth data exceeds the {MAX_GROWTH_BUCKETS}-bucket safety limit; pass --span-days to narrow the report."
    )
}

#[expect(
    clippy::cast_precision_loss,
    reason = "the bounded issue snapshot has far fewer records than f64's exact range"
)]
fn pattern_observations(
    issues: &[AnalysisIssue],
    top_k: usize,
    stats: &larch_core::CoverageStats,
) -> String {
    let mut daily = BTreeMap::<NaiveDate, usize>::new();
    let mut paths = BTreeMap::<String, usize>::new();
    let mut automatic = 0_usize;
    for issue in issues {
        if let Some(created) = issue.summary.created_at {
            *daily.entry(created.date_naive()).or_default() += 1;
        }
        let text = issue.summary.text();
        for matched in FILE_REFERENCE.find_iter(&text) {
            *paths.entry(matched.as_str().to_lowercase()).or_default() += 1;
        }
        let lower = text.to_lowercase();
        if lower.contains("automatically created") || lower.contains("[oos]") {
            automatic += 1;
        }
    }
    let mean = if daily.is_empty() {
        0.0
    } else {
        issues.len() as f64 / daily.len() as f64
    };
    let mut bursts: Vec<(NaiveDate, usize)> = daily
        .iter()
        .filter_map(|(date, count)| {
            (mean > 0.0 && *count as f64 >= 2.0 * mean).then_some((*date, *count))
        })
        .collect();
    bursts.sort_by_key(|(date, count)| (std::cmp::Reverse(*count), *date));
    let mut hot: Vec<(String, usize)> = paths.into_iter().collect();
    hot.sort_by_key(|(path, count)| (std::cmp::Reverse(*count), path.clone()));
    let mut lines = vec![
        "## Pattern Observations".to_owned(),
        "- Bursty filing days:".to_owned(),
    ];
    if bursts.is_empty() {
        lines.push("  - None above 2x mean daily creation rate.".to_owned());
    } else {
        lines.extend(bursts.into_iter().take(5).map(|(day, count)| {
            format!(
                "  - {day}: {count} issues ({:.1}x mean)",
                count as f64 / mean
            )
        }));
    }
    lines.push("- File-path and skill-name hot spots:".to_owned());
    if hot.is_empty() {
        lines.push("  - None detected.".to_owned());
    } else {
        lines.extend(
            hot.into_iter()
                .take(top_k)
                .map(|(path, count)| format!("  - {path}: {count}")),
        );
    }
    let total = issues.len().max(1);
    lines.push(format!(
        "- Auto-spawned share: {automatic}/{} ({:.1}%)",
        issues.len(),
        automatic as f64 / total as f64 * 100.0
    ));
    lines.push(format!(
        "- Closure velocity: P25 {}, P50 {}, P75 {}, P90 {}",
        fmt_days(stats.p25_close_days),
        fmt_days(stats.median_close_days),
        fmt_days(stats.p75_close_days),
        fmt_days(stats.p90_close_days),
    ));
    lines.join("\n")
}

#[expect(
    clippy::too_many_lines,
    reason = "the five report signatures share one fixed output section and ordering contract"
)]
fn wasteful_findings(issues: &[AnalysisIssue], top_k: usize) -> String {
    let mut titles = BTreeMap::<String, Vec<&AnalysisIssue>>::new();
    for issue in issues {
        titles
            .entry(strip_prefixes(&issue.summary.title).to_lowercase())
            .or_default()
            .push(issue);
    }
    let mut lines = vec![
        "## Wasteful-work Findings".to_owned(),
        "- W1 duplicate-titled issues opened within 7 days:".to_owned(),
    ];
    let mut duplicates = 0_usize;
    for (title, group) in &titles {
        let mut group = group.clone();
        group.sort_by_key(|issue| (issue.summary.created_at, issue.summary.number));
        for pair in group.windows(2) {
            let (Some(left), Some(right)) =
                (pair[0].summary.created_at, pair[1].summary.created_at)
            else {
                continue;
            };
            if right - left <= Duration::days(7) {
                lines.push(format!(
                    "  - #{} and #{}: {title}",
                    pair[0].summary.number, pair[1].summary.number
                ));
                duplicates += 1;
                if duplicates >= top_k {
                    break;
                }
            }
        }
        if duplicates >= top_k {
            break;
        }
    }
    if duplicates == 0 {
        lines.push("  - None detected.".to_owned());
    }
    lines.push("- W2 reversal/supersession mentions:".to_owned());
    let mut reversals = 0_usize;
    for issue in issues {
        let text = format!(
            "{}\n{}",
            issue.summary.title,
            issue.summary.body.chars().take(3_072).collect::<String>()
        );
        if let Some(found) = REVERSAL.captures(&text) {
            let verb = found.get(1).map_or("", |value| value.as_str());
            let reference = found
                .get(2)
                .map_or("no explicit PR/commit reference", |value| value.as_str());
            lines.push(format!(
                "  - #{}: {verb} ({reference})",
                issue.summary.number
            ));
            reversals += 1;
            if reversals >= top_k {
                break;
            }
        }
    }
    if reversals == 0 {
        lines.push("  - None detected.".to_owned());
    }
    let stalled: Vec<&AnalysisIssue> = issues
        .iter()
        .filter(|issue| {
            issue
                .summary
                .title
                .trim_start()
                .to_lowercase()
                .starts_with(&STALLED_PREFIX.trim_end().to_lowercase())
        })
        .collect();
    lines.push(format!("- W3 [STALLED] issues: {} total", stalled.len()));
    lines.extend(
        stalled
            .into_iter()
            .take(top_k)
            .map(|issue| format!("  - #{} {}", issue.summary.number, issue.summary.title)),
    );
    let mut clusters = BTreeMap::<String, Vec<u64>>::new();
    for issue in issues {
        for reference in &issue.summary.closed_by_pull_requests {
            clusters
                .entry(reference.clone())
                .or_default()
                .push(issue.summary.number);
        }
    }
    let mut clusters: Vec<(String, Vec<u64>)> = clusters
        .into_iter()
        .filter(|(_reference, numbers)| numbers.len() >= 3)
        .collect();
    clusters
        .sort_by_key(|(reference, numbers)| (std::cmp::Reverse(numbers.len()), reference.clone()));
    lines.push("- W4 PR-to-issue closure clusters:".to_owned());
    if clusters.is_empty() {
        lines.push("  - None detected.".to_owned());
    } else {
        lines.extend(
            clusters
                .into_iter()
                .take(top_k)
                .map(|(reference, mut numbers)| {
                    numbers.sort_unstable();
                    format!(
                        "  - {reference}: closes {} issues ({})",
                        numbers.len(),
                        numbers
                            .into_iter()
                            .map(|number| format!("#{number}"))
                            .collect::<Vec<_>>()
                            .join(", ")
                    )
                }),
        );
    }
    let mut loops: Vec<(String, Vec<&AnalysisIssue>)> = titles
        .into_iter()
        .filter(|(title, group)| !title.is_empty() && group.len() >= 2)
        .collect();
    loops.sort_by_key(|(title, group)| (std::cmp::Reverse(group.len()), title.clone()));
    lines.push("- W5 auto-loop duplicate filings:".to_owned());
    if loops.is_empty() {
        lines.push("  - None detected.".to_owned());
    } else {
        lines.extend(loops.into_iter().take(top_k).map(|(title, mut group)| {
            group.sort_by_key(|issue| issue.summary.number);
            format!(
                "  - {title}: {} issues ({})",
                group.len(),
                group
                    .into_iter()
                    .map(|issue| format!("#{}", issue.summary.number))
                    .collect::<Vec<_>>()
                    .join(", ")
            )
        }));
    }
    lines.join("\n")
}

struct ReviewerReport {
    text: String,
    best: Option<ReviewerBest>,
}

struct ReviewerBest {
    tool: String,
    persona: String,
    total: usize,
    done: usize,
    rate: f64,
}

#[expect(
    clippy::cast_precision_loss,
    reason = "reviewer counts are bounded by the issue snapshot"
)]
#[expect(
    clippy::too_many_lines,
    reason = "the fixed reviewer report preserves the established four-table order"
)]
fn reviewer_effectiveness(issues: &[AnalysisIssue]) -> ReviewerReport {
    let mut pairs = BTreeMap::<(String, String), (usize, usize)>::new();
    let mut tools = BTreeMap::<String, (usize, usize)>::new();
    let mut votes = Vec::new();
    for issue in issues {
        let Some(attribution) = issue.summary.body.lines().find_map(|line| {
            ATTRIBUTION
                .captures(line)
                .and_then(|found| found.get(1))
                .map(|value| value.as_str())
        }) else {
            continue;
        };
        let tool = TOOL
            .captures(attribution)
            .and_then(|found| found.get(1))
            .map_or_else(
                || "unknown".to_owned(),
                |value| normalize_tool(value.as_str()),
            );
        let persona = PERSONA
            .captures(attribution)
            .and_then(|found| found.get(1))
            .map_or_else(
                || "generic".to_owned(),
                |value| normalize_persona(value.as_str()),
            );
        let done = issue
            .summary
            .title
            .trim_start()
            .to_uppercase()
            .starts_with(DONE_PREFIX.trim_end());
        let pair = pairs.entry((tool.clone(), persona.clone())).or_default();
        pair.0 += 1;
        if done {
            pair.1 += 1;
        }
        let total = tools.entry(tool.clone()).or_default();
        total.0 += 1;
        if done {
            total.1 += 1;
        }
        if let Some(found) = VOTE_TALLY.captures(&issue.summary.body) {
            let mut tally = format!("YES={} NO={}", &found[1], &found[2]);
            if let Some(exonerate) = found.get(3) {
                let _ = write!(tally, " EXONERATE={}", exonerate.as_str());
            }
            votes.push((issue.summary.number, tool, persona, tally));
        }
    }
    let mut tool_rows: Vec<(String, (usize, usize))> = tools.into_iter().collect();
    tool_rows.sort_by_key(|(tool, row)| (std::cmp::Reverse(row.0), tool.clone()));
    let mut pair_rows: Vec<((String, String), (usize, usize))> = pairs.into_iter().collect();
    pair_rows.sort_by_key(|(pair, row)| (std::cmp::Reverse(row.0), pair.clone()));
    let mut lines = vec![
        "## Reviewer/Persona Tables".to_owned(),
        "Aggregate per tool:".to_owned(),
    ];
    if tool_rows.is_empty() {
        lines.push("- No reviewer attribution lines detected.".to_owned());
    }
    lines.extend(tool_rows.iter().map(|(tool, (total, done))| {
        format!(
            "- {tool}: {total} findings, {done} done ({:.1}%)",
            *done as f64 / *total as f64 * 100.0
        )
    }));
    lines.push("Per tool/persona:".to_owned());
    if pair_rows.is_empty() {
        lines.push("- No tool/persona pairs detected.".to_owned());
    }
    lines.extend(pair_rows.iter().map(|((tool, persona), (total, done))| {
        format!(
            "- {tool} / {persona}: {total} findings, {done} done ({:.1}%)",
            *done as f64 / *total as f64 * 100.0
        )
    }));
    lines.push("Design-phase vote findings:".to_owned());
    if votes.is_empty() {
        lines.push("- None with explicit YES=N NO=M tallies.".to_owned());
    }
    lines.extend(votes.into_iter().map(|(number, tool, persona, tally)| {
        format!("- #{number}: {tool} / {persona} ({tally})")
    }));
    let mut eligible: Vec<ReviewerBest> = pair_rows
        .into_iter()
        .filter_map(|((tool, persona), (total, done))| {
            (total >= 10).then_some(ReviewerBest {
                tool,
                persona,
                total,
                done,
                rate: done as f64 / total as f64,
            })
        })
        .collect();
    eligible.sort_by(|left, right| {
        right
            .rate
            .total_cmp(&left.rate)
            .then_with(|| left.tool.cmp(&right.tool))
            .then_with(|| left.persona.cmp(&right.persona))
    });
    lines.push("Top ROI reviewer/persona pairs:".to_owned());
    if eligible.is_empty() {
        lines.push("- None with at least 10 findings.".to_owned());
    }
    lines.extend(eligible.iter().take(3).map(|row| {
        format!(
            "- {} / {}: {}/{} done ({:.1}%)",
            row.tool,
            row.persona,
            row.done,
            row.total,
            row.rate * 100.0
        )
    }));
    ReviewerReport {
        text: lines.join("\n"),
        best: eligible.into_iter().next(),
    }
}

fn normalize_tool(value: &str) -> String {
    let value = value.to_lowercase();
    if value.starts_with("code,") || value == "code" {
        "claude".to_owned()
    } else if value == "main agent" {
        "main agent".to_owned()
    } else {
        value
    }
}

fn normalize_persona(value: &str) -> String {
    match value.to_lowercase().as_str() {
        "arch" => "architect".to_owned(),
        "edge" => "edge-cases".to_owned(),
        other => other.to_owned(),
    }
}

fn render_high_risk_oos(issues: &[AnalysisIssue], top_k: usize) -> String {
    let mut rows: Vec<&AnalysisIssue> = issues
        .iter()
        .filter(|issue| {
            issue.summary.state == IssueLifecycle::Open
                && issue
                    .summary
                    .title
                    .trim()
                    .to_lowercase()
                    .starts_with("[oos]")
                && issue
                    .summary
                    .labels
                    .iter()
                    .any(|label| label == OOS_CORRECTNESS_LABEL)
        })
        .collect();
    rows.sort_by_key(|issue| (issue.summary.created_at, issue.summary.number));
    let mut lines = vec!["## High-risk OOS Backlog".to_owned()];
    if rows.is_empty() {
        lines.push("No open high-risk OOS issues found.".to_owned());
        return lines.join("\n");
    }
    let today = Utc::now().date_naive();
    lines.extend(rows.into_iter().take(top_k).map(|issue| {
        let (age, created) = issue.summary.created_at.map_or_else(
            || ("unknown".to_owned(), "unknown".to_owned()),
            |value| {
                (
                    (today - value.date_naive()).num_days().max(0).to_string(),
                    value.date_naive().to_string(),
                )
            },
        );
        let suffix = if issue.url.is_empty() {
            String::new()
        } else {
            format!(" — {}", issue.url)
        };
        format!(
            "- #{} ({}d, {}): {}{suffix}",
            issue.summary.number, age, created, issue.summary.title
        )
    }));
    lines.join("\n")
}

#[derive(Clone)]
pub struct FiledOos {
    identity: String,
    pub number: Option<u64>,
    pub url: String,
    reviewers: Vec<String>,
}

fn fate_adjusted_oos(
    issues: &[AnalysisIssue],
    details: &BTreeMap<u64, AnalysisIssue>,
    log_root: &Path,
    repo: Option<&str>,
    degradation: Option<&str>,
    targeted_degradation: Option<&str>,
) -> String {
    let records = filed_oos_records(log_root);
    let mut lines = vec!["## Fate-adjusted OOS Scoring".to_owned()];
    if let Some(reason) = degradation {
        lines.push(format!("- Note: GitHub issue enrichment unavailable ({reason}); filed OOS fate uses partial or offline data."));
    }
    if let Some(reason) = targeted_degradation {
        lines.push(format!("- Note: targeted filed-OOS detail fetch unavailable ({reason}); combined-away comments are provisional."));
    }
    if records.is_empty() {
        lines.push("No filed OOS run-log evidence found.".to_owned());
        return lines.join("\n");
    }
    let mut index: BTreeMap<u64, AnalysisIssue> = issues
        .iter()
        .map(|issue| (issue.summary.number, issue.clone()))
        .collect();
    for (number, detail) in details {
        let merged = merge_issue_detail(index.get(number), detail);
        index.insert(*number, merged);
    }
    let mut reviewer_totals = BTreeMap::<String, [usize; 3]>::new();
    let mut buckets = BTreeMap::<String, usize>::new();
    let mut totals = [0_usize; 3];
    let mut seen = HashSet::new();
    for record in records {
        if !seen.insert(record.identity.clone()) {
            continue;
        }
        if let Some(repo) = repo
            && let Some(found) = github_repo_from_issue_url(&record.url)
            && !found.eq_ignore_ascii_case(repo)
        {
            *buckets
                .entry("skipped missing issue".to_owned())
                .or_default() += 1;
            continue;
        }
        let issue = record.number.and_then(|number| index.get(&number));
        let fate = issue.map_or_else(
            || {
                if degradation.is_some() {
                    ("enrichment unavailable", 1, 1, false)
                } else {
                    ("skipped missing issue", 0, 0, false)
                }
            },
            classify_fate,
        );
        *buckets.entry(fate.0.to_owned()).or_default() += 1;
        if issue.is_some_and(|issue| issue.fetch_failed) {
            *buckets
                .entry("degraded comment fetch".to_owned())
                .or_default() += 1;
        }
        if fate.0 == "skipped missing issue" {
            continue;
        }
        for reviewer in record.reviewers {
            let row = reviewer_totals.entry(reviewer).or_default();
            row[0] += fate.1;
            row[1] += fate.2;
            row[2] += usize::from(fate.3);
            totals[0] += fate.1;
            totals[1] += fate.2;
            totals[2] += usize::from(fate.3);
        }
    }
    lines.push(format!("- Overall provisional points: {}", totals[0]));
    lines.push(format!("- Overall fate-adjusted points: {}", totals[1]));
    lines.push(format!("- Overall docked count: {}", totals[2]));
    lines.push("Reviewer rows:".to_owned());
    if reviewer_totals.is_empty() {
        lines.push("- No reviewer-attributed filed OOS rows detected.".to_owned());
    }
    let mut reviewer_rows: Vec<(String, [usize; 3])> = reviewer_totals.into_iter().collect();
    reviewer_rows
        .sort_by_key(|(reviewer, row)| (std::cmp::Reverse(row[1]), reviewer.to_lowercase()));
    lines.extend(reviewer_rows.into_iter().map(|(reviewer, row)| {
        format!(
            "- {reviewer}: provisional {}, adjusted {}, docked {}",
            row[0], row[1], row[2]
        )
    }));
    lines.push("Fate buckets:".to_owned());
    for bucket in [
        "kept by PR",
        "provisional open",
        "provisional unknown",
        "docked closed-unfixed",
        "docked combined-away",
        "skipped missing issue",
        "degraded comment fetch",
        "enrichment unavailable",
    ] {
        lines.push(format!(
            "- {bucket}: {}",
            buckets.get(bucket).copied().unwrap_or(0)
        ));
    }
    lines.join("\n")
}

fn merge_issue_detail(current: Option<&AnalysisIssue>, detail: &AnalysisIssue) -> AnalysisIssue {
    let Some(current) = current else {
        return detail.clone();
    };
    let mut merged = detail.clone();
    if !detail.present_fields.contains("title") {
        merged.summary.title.clone_from(&current.summary.title);
    }
    if !detail.present_fields.contains("body") {
        merged.summary.body.clone_from(&current.summary.body);
    }
    if !detail.present_fields.contains("state") {
        merged.summary.state = current.summary.state;
    }
    if detail.present_fields.contains("stateReason") && !detail.summary.state_reason.is_empty() {
        merged.summary.state_reason_degraded = false;
        merged.degraded_fields.remove("stateReason");
    } else if detail.present_fields.contains("stateReason") {
        // Python only clears a bulk `stateReason` degradation marker when a
        // targeted response actually supplied a non-empty replacement. An
        // empty optional field is not proof that the missing bulk field was
        // successfully enriched, particularly for the verdict gate.
        merged.summary.state_reason_degraded = current.summary.state_reason_degraded;
        if current.degraded_fields.contains("stateReason") {
            merged.degraded_fields.insert("stateReason".to_owned());
        }
    } else {
        merged
            .summary
            .state_reason
            .clone_from(&current.summary.state_reason);
        merged.summary.state_reason_degraded = current.summary.state_reason_degraded;
    }
    if !detail.present_fields.contains("labels") {
        merged.summary.labels.clone_from(&current.summary.labels);
    }
    if !detail.present_fields.contains("createdAt") {
        merged.summary.created_at = current.summary.created_at;
    }
    if !detail.present_fields.contains("closedAt") {
        merged.summary.closed_at = current.summary.closed_at;
    }
    if !detail
        .present_fields
        .contains("closedByPullRequestsReferences")
        || detail
            .degraded_fields
            .contains("closedByPullRequestsReferences")
    {
        merged
            .summary
            .closed_by_pull_requests
            .clone_from(&current.summary.closed_by_pull_requests);
        if current
            .degraded_fields
            .contains("closedByPullRequestsReferences")
        {
            merged
                .degraded_fields
                .insert("closedByPullRequestsReferences".to_owned());
        } else {
            merged
                .degraded_fields
                .remove("closedByPullRequestsReferences");
        }
    }
    if !detail.present_fields.contains("url") {
        merged.url.clone_from(&current.url);
    }
    if !detail.present_fields.contains("comments") {
        merged.comments.clone_from(&current.comments);
    }
    merged.fetch_failed = current.fetch_failed || detail.fetch_failed;
    merged
        .present_fields
        .extend(current.present_fields.iter().cloned());
    merged
}

fn classify_fate(issue: &AnalysisIssue) -> (&'static str, usize, usize, bool) {
    if issue.fetch_failed
        && !issue.present_fields.contains("state")
        && issue.summary.closed_by_pull_requests.is_empty()
    {
        return ("skipped missing issue", 0, 0, false);
    }
    if issue.summary.state == IssueLifecycle::Open {
        return ("provisional open", 1, 1, false);
    }
    if !issue.summary.closed_by_pull_requests.is_empty() {
        return ("kept by PR", 1, 1, false);
    }
    if COMBINED_AWAY_MARKER.is_match(&issue.summary.body)
        || issue
            .comments
            .iter()
            .any(|comment| COMBINED_AWAY_COMMENT.is_match(comment))
    {
        return ("docked combined-away", 1, 0, true);
    }
    if issue.summary.state == IssueLifecycle::Closed && issue.summary.not_planned() {
        return ("docked closed-unfixed", 1, 0, true);
    }
    ("provisional unknown", 1, 1, false)
}

pub fn filed_oos_records(log_root: &Path) -> Vec<FiledOos> {
    let mut records = Vec::new();
    for event in RunLogCorpus::new(log_root).select(RunLogSelection::all()) {
        let RunLogCorpusEvent::Run(run) = event else {
            continue;
        };
        if !matches!(run.layout().skill().as_str(), "design" | "implement") {
            continue;
        }
        let reviewers = accepted_oos_reviewers(&run);
        for path in run.files_named("oos-issues.ndjson") {
            let Ok(text) = fs::read_to_string(path) else {
                continue;
            };
            for filed in ndjson_filed_evidence(&text) {
                let number = issue_number_from_url(&filed.url).parse::<u64>().ok();
                let stable_ids = if filed.source_stable_ids.is_empty() {
                    vec![filed.stable_id]
                } else {
                    filed.source_stable_ids
                };
                let reviewer_values: Vec<String> = stable_ids
                    .iter()
                    .filter_map(|stable| reviewers.get(stable).cloned())
                    .flatten()
                    .collect();
                records.push(FiledOos {
                    identity: format!("{}:{}", run.directory().display(), filed.url),
                    number,
                    url: filed.url,
                    reviewers: if reviewer_values.is_empty() {
                        vec!["unknown".to_owned()]
                    } else {
                        reviewer_values
                    },
                });
            }
        }
        for path in run.files_named("oos-issues-created.md") {
            let Ok(text) = fs::read_to_string(path) else {
                continue;
            };
            for line in text.lines() {
                let mut fields = line.split('\t');
                let (Some("OOS_FILE_MAP"), Some(sequence), Some(url)) =
                    (fields.next(), fields.next(), fields.next())
                else {
                    continue;
                };
                let stable_id = format!("OOS_{}", sequence.trim());
                let reviewer_values: Vec<String> = reviewers
                    .iter()
                    .filter(|(key, _)| key.ends_with(&format!(":{stable_id}")))
                    .flat_map(|(_key, values)| values.clone())
                    .collect();
                records.push(FiledOos {
                    identity: format!("{}:{url}", run.directory().display()),
                    number: issue_number_from_url(url).parse::<u64>().ok(),
                    url: url.to_owned(),
                    reviewers: if reviewer_values.is_empty() {
                        vec!["unknown".to_owned()]
                    } else {
                        reviewer_values
                    },
                });
            }
        }
    }
    records
}

fn accepted_oos_reviewers(run: &larch_core::RunLogRun) -> BTreeMap<String, Vec<String>> {
    let mut out = BTreeMap::new();
    for path in run.files() {
        let name = path
            .file_name()
            .and_then(|name| name.to_str())
            .unwrap_or_default();
        if !name.starts_with("oos-accepted-")
            || !Path::new(name)
                .extension()
                .is_some_and(|extension| extension.eq_ignore_ascii_case("md"))
        {
            continue;
        }
        let Ok(text) = fs::read_to_string(&path) else {
            continue;
        };
        for block in parse_oos_blocks(&text, BlockBoundary::ItemHeading) {
            let reviewers = REVIEWER_LINE
                .captures(&block.block)
                .and_then(|found| found.get(1))
                .map_or_else(
                    || vec!["unknown".to_owned()],
                    |value| split_reviewers(value.as_str()),
                );
            let stem = path
                .file_stem()
                .and_then(|name| name.to_str())
                .unwrap_or_default();
            out.insert(format!("{}:{}", stem, block.item_id), reviewers);
        }
    }
    out
}

fn split_reviewers(value: &str) -> Vec<String> {
    value
        .split(',')
        .map(str::trim)
        .filter(|item| !item.is_empty())
        .map(str::to_owned)
        .collect()
}

fn github_repo_from_issue_url(url: &str) -> Option<&str> {
    let remainder = url.strip_prefix("https://github.com/")?;
    let (repo, tail) = remainder.split_once("/issues/")?;
    (!repo.is_empty() && !tail.is_empty()).then_some(repo)
}

pub struct VerdictReport {
    qualifying_runs: usize,
    required_runs: usize,
    since_date: String,
    min_larch_version: String,
    incentive_era_shipped: bool,
    incentive_gate_reason: &'static str,
    enrichment_degraded: Option<String>,
    targeted_fetch_degraded: Option<String>,
    gate_reason: Option<String>,
}

#[expect(
    clippy::too_many_lines,
    reason = "the report's stable Markdown layout keeps diagnostics and tables together"
)]
pub fn ground_truth_report(
    issues: &[AnalysisIssue],
    log_root: &Path,
    degradation: Option<&str>,
    top_k: usize,
    scan: Option<GroundTruthCorpusScan>,
    verdict: Option<&VerdictReport>,
) -> String {
    let scan = scan.unwrap_or_else(|| {
        scan_ground_truth_corpus(
            log_root,
            GroundTruthMode::Calibration,
            &CorpusFilter::default(),
        )
    });
    let mut rows = Vec::new();
    let mut scanned_rows = 0_usize;
    let mut ineligible = 0_usize;
    for source in &scan.sources {
        let Ok(text) = fs::read_to_string(&source.path) else {
            continue;
        };
        let (parsed, rejected) =
            parse_ground_truth_rows(source, &text, &ground_truth_prose(source));
        scanned_rows += parsed.len() + rejected;
        ineligible += rejected;
        rows.extend(parsed);
    }
    let summaries: Vec<IssueSummary> = issues.iter().map(|issue| issue.summary.clone()).collect();
    let analysis = analyze_ground_truth(&rows, &summaries, degradation);
    let mut lines = if let Some(status) = verdict {
        let mut verdict_lines = vec![
            "## Ground-truth Verdict for Token Allocation".to_owned(),
            String::new(),
            "Capstone evidence for token-allocation decision.".to_owned(),
        ];
        let degraded: Vec<&str> = [
            status.enrichment_degraded.as_deref(),
            status.targeted_fetch_degraded.as_deref(),
        ]
        .into_iter()
        .flatten()
        .collect();
        if !degraded.is_empty() {
            verdict_lines.push(format!("- Degraded evidence: {}.", degraded.join(", ")));
        }
        if analysis.stats.large_corpus_skip {
            verdict_lines.push(
                "- Note: corpus exceeds 5000 rows; accepted-finding index disabled. Per-voter rates may be incomplete."
                    .to_owned(),
            );
        }
        verdict_lines.extend([
            String::new(),
            "Verdict corpus:".to_owned(),
            format!("- Log root: `{}`", log_root.display()),
            format!("- Since date: {}", status.since_date),
            format!("- Min larch version: {}", status.min_larch_version),
            format!("- Required runs: {}", status.required_runs),
            format!("- Qualifying runs: {}", status.qualifying_runs),
            format!(
                "- Excluded pre-since runs: {}",
                scan.stats.excluded_pre_since_runs
            ),
            format!(
                "- Excluded missing `started_at` runs: {}",
                scan.stats.excluded_missing_started_at_runs
            ),
            format!(
                "- Excluded below-version runs: {}",
                scan.stats.excluded_below_version_runs
            ),
            format!(
                "- Excluded missing-version runs: {}",
                scan.stats.excluded_missing_version_runs
            ),
            format!(
                "- Excluded `gc-slimmed` runs: {}",
                scan.stats.excluded_gc_slimmed_runs
            ),
            format!(
                "- Classification TSV files scanned: {}",
                scan.stats.files_seen
            ),
            format!("- Classification rows scanned: {scanned_rows}"),
            format!(
                "- Eligible rows with parseable voter ballots: {}",
                rows.len()
            ),
            format!("- Decisive realized rows: {}", analysis.stats.decisive_rows),
            format!(
                "- Weak/provisional/non-decisive rows: {}",
                analysis.stats.weak_rows
            ),
            format!(
                "- Incentive-era shipped: {}",
                if status.incentive_era_shipped {
                    "yes"
                } else {
                    "no"
                }
            ),
            format!("- Incentive gate reason: {}", status.incentive_gate_reason),
            format!(
                "- Enrichment degraded: {}",
                status.enrichment_degraded.as_deref().unwrap_or("none")
            ),
            format!(
                "- Targeted fetch degraded: {}",
                status.targeted_fetch_degraded.as_deref().unwrap_or("none")
            ),
            format!(
                "- Gate result: {}",
                if status.gate_reason.is_some() {
                    "FAIL"
                } else {
                    "PASS"
                }
            ),
            format!(
                "- Gate reason: {}",
                status.gate_reason.as_deref().unwrap_or("none")
            ),
            String::new(),
            "Outcome buckets:".to_owned(),
            "| Bucket | Rows | Decisive |".to_owned(),
            "|---|---:|---:|".to_owned(),
        ]);
        verdict_lines
    } else {
        let mut diagnostic = vec![
            "## Ground-truth Voter Calibration".to_owned(),
            String::new(),
            "Diagnostic only. This section does not change live scoring, thresholds, tokens, or reviewer points.".to_owned(),
        ];
        if let Some(reason) = degradation {
            diagnostic.push(format!("- Note: GitHub issue enrichment unavailable ({reason}); in-scope realized-outcome buckets may be suppressed or partial."));
        }
        diagnostic.extend([
            String::new(),
            "Corpus:".to_owned(),
            format!("- Log root: `{}`", log_root.display()),
            format!(
                "- Classification TSV files scanned: {}",
                scan.stats.files_seen
            ),
            "- Unsupported TSV files skipped: 0".to_owned(),
            format!("- Classification rows scanned: {scanned_rows}"),
            format!(
                "- Eligible rows with parseable voter ballots: {}",
                rows.len()
            ),
            format!("- Ineligible rows: {ineligible}"),
            format!(
                "- Rows with prose evidence: {}",
                rows.iter().filter(|row| !row.prose_text.is_empty()).count()
            ),
            format!(
                "- GC-slimmed or missing voter TSV runs: {}",
                scan.stats.gc_slimmed_runs
            ),
            format!("- Decisive realized rows: {}", analysis.stats.decisive_rows),
            format!(
                "- Weak/provisional/non-decisive rows: {}",
                analysis.stats.weak_rows
            ),
            format!(
                "- Timestamp-degraded matches: {}",
                analysis.stats.timestamp_degraded
            ),
            format!(
                "- Verdict-disagreement rows: {}",
                analysis.stats.verdict_disagreement
            ),
            "- Rejected-OOS-panel rows: 0".to_owned(),
            format!(
                "- Enrichment-degraded rows: {}",
                analysis.stats.enrichment_degraded_rows
            ),
            String::new(),
            "Outcome buckets:".to_owned(),
            "| Bucket | Rows | Decisive |".to_owned(),
            "|---|---:|---:|".to_owned(),
        ]);
        diagnostic
    };
    if analysis.stats.buckets.is_empty() {
        lines.push("| no-evidence | 0 | 0 |".to_owned());
    }
    for (bucket, count) in &analysis.stats.buckets {
        let decisive = if bucket.is_decisive() { *count } else { 0 };
        lines.push(format!("| {} | {count} | {decisive} |", bucket.as_str()));
    }
    lines.extend([String::new(), "Per-voter realized alignment:".to_owned(), "| Panel | Voter | Decisive | Aligned | Misaligned | Missing | Realized alignment | False positive YES | False negative NO |".to_owned(), "|---|---|---:|---:|---:|---:|---:|---:|---:|".to_owned()]);
    if analysis.metrics.is_empty() {
        lines.push("| n/a | n/a | 0 | 0 | 0 | 0 | n/a | 0 | 0 |".to_owned());
    }
    for metric in &analysis.metrics {
        lines.push(format!(
            "| {} | {} | {} | {} | {} | {} | {} | {} | {} |",
            metric.panel.as_str(),
            metric.voter,
            metric.decisive,
            metric.aligned,
            metric.misaligned,
            metric.missing,
            fmt_rate(realized_alignment_rate(metric.aligned, metric.misaligned)),
            metric.false_positive_yes,
            metric.false_negative_no
        ));
    }
    lines.extend([String::new(), "Severity slice for decisive YES votes:".to_owned(), "| Panel | Voter | Severity | Decisive YES rows | Aligned | Misaligned | Realized alignment | Missing-severity rows |".to_owned(), "|---|---|---|---:|---:|---:|---:|---:|".to_owned()]);
    if analysis.severity_metrics.is_empty() {
        lines.push("| n/a | n/a | n/a | 0 | 0 | 0 | n/a | 0 |".to_owned());
    }
    for metric in &analysis.severity_metrics {
        lines.push(format!(
            "| {} | {} | {} | {} | {} | {} | {} | {} |",
            metric.panel.as_str(),
            metric.voter,
            metric.severity,
            metric.decisive_yes,
            metric.aligned,
            metric.misaligned,
            fmt_rate(realized_alignment_rate(metric.aligned, metric.misaligned)),
            metric.missing_severity
        ));
    }
    lines.extend([String::new(), "Examples:".to_owned()]);
    if analysis.outcomes.is_empty() {
        lines.push("- None.".to_owned());
    } else {
        lines.extend(
            analysis
                .outcomes
                .iter()
                .take(top_k)
                .map(|outcome| format!("- {}. {}", outcome.bucket.as_str(), outcome.reason)),
        );
    }
    lines.extend([
        String::new(),
        "Notes:".to_owned(),
        "- Ground-truth alignment is against realized outcomes, not panel self-agreement."
            .to_owned(),
        "- Conservative matching can undercount resurfacing and reversals.".to_owned(),
        "- Provisional OOS fates and rejected OOS panel results are non-decisive.".to_owned(),
        "- `realized_alignment_rate` uses decisive aligned/misaligned ballots only.".to_owned(),
    ]);
    lines.join("\n")
}

fn fmt_rate(value: Option<f64>) -> String {
    value.map_or_else(|| "n/a".to_owned(), |value| format!("{value:.3}"))
}

#[expect(
    clippy::too_many_lines,
    reason = "one TSV row decoder keeps header selection and voter slots in one deterministic pass"
)]
fn parse_ground_truth_rows(
    source: &larch_core::ClassificationSource,
    text: &str,
    prose: &BTreeMap<String, (String, String, String)>,
) -> (Vec<GroundTruthRow>, usize) {
    let mut lines = text.lines();
    let Some(header) = lines.next() else {
        return (Vec::new(), 0);
    };
    let headers: Vec<&str> = header.split('\t').collect();
    let Some(finding_index) = headers.iter().position(|name| *name == "finding_id") else {
        return (Vec::new(), 0);
    };
    let result_index = headers.iter().position(|name| *name == "voting_result");
    let scope_index = headers.iter().position(|name| *name == "scope");
    let voter_columns: Vec<(usize, Option<usize>, Option<usize>)> = headers
        .iter()
        .enumerate()
        .filter_map(|(index, name)| {
            name.strip_prefix('v')
                .and_then(|rest| rest.strip_suffix("_vote"))
                .filter(|number| number.bytes().all(|byte| byte.is_ascii_digit()))
                .map(|number| {
                    let severity = headers
                        .iter()
                        .position(|candidate| *candidate == format!("v{number}_severity"));
                    let tool = headers
                        .iter()
                        .position(|candidate| *candidate == format!("v{number}_tool"));
                    (index, severity, tool)
                })
        })
        .collect();
    let mut accepted = Vec::new();
    let mut rejected = 0_usize;
    for line in lines.filter(|line| !line.is_empty()) {
        let values: Vec<&str> = line.split('\t').collect();
        let finding_id = values
            .get(finding_index)
            .copied()
            .unwrap_or_default()
            .trim();
        let verdict = match result_index
            .and_then(|index| values.get(index))
            .copied()
            .unwrap_or_default()
            .trim()
            .to_lowercase()
            .as_str()
        {
            "accepted" => PanelVerdict::Accepted,
            "rejected" => PanelVerdict::Rejected,
            _ => {
                rejected += 1;
                continue;
            }
        };
        if scope_index
            .and_then(|index| values.get(index))
            .is_some_and(|scope| scope.trim().eq_ignore_ascii_case("oos"))
        {
            rejected += 1;
            continue;
        }
        let voters: Vec<GroundTruthVoter> = voter_columns
            .iter()
            .enumerate()
            .map(|(slot, (vote_index, severity_index, tool_index))| {
                let vote = values
                    .get(*vote_index)
                    .copied()
                    .unwrap_or_default()
                    .trim()
                    .to_uppercase();
                let ballot = match vote.as_str() {
                    "YES" => VoterBallot::Yes,
                    "NO" => VoterBallot::No,
                    _ => VoterBallot::Missing,
                };
                let voter = tool_index
                    .and_then(|index| values.get(index))
                    .copied()
                    .unwrap_or_default()
                    .trim();
                GroundTruthVoter {
                    voter: if voter.is_empty() {
                        format!("v{}", slot + 1)
                    } else {
                        voter.to_owned()
                    },
                    ballot,
                    severity: severity_index
                        .and_then(|index| values.get(index))
                        .copied()
                        .unwrap_or_default()
                        .trim()
                        .to_owned(),
                }
            })
            .collect();
        let evidence = prose.get(finding_id).or_else(|| {
            prose
                .values()
                .find(|(_title, body, _category)| body.contains(&format!("### {finding_id}:")))
        });
        accepted.push(GroundTruthRow {
            panel_kind: source.panel_kind,
            run_id: source.run_id.clone(),
            run_dir_key: source.run_dir_key.clone(),
            round_num: source.round_num,
            started_at: source.started_at,
            run_ended_at: source.run_ended_at,
            multi_round: source.multi_round,
            finding_id: finding_id.to_owned(),
            title: evidence.map_or_else(
                || finding_id.to_owned(),
                |(title, _body, _category)| title.clone(),
            ),
            prose_text: evidence.map_or_else(String::new, |(_title, body, _category)| body.clone()),
            category: evidence
                .map_or_else(String::new, |(_title, _body, category)| category.clone()),
            verdict,
            weak_reason: None,
            voters,
        });
    }
    (accepted, rejected)
}

fn ground_truth_prose(
    source: &larch_core::ClassificationSource,
) -> BTreeMap<String, (String, String, String)> {
    let mut paths = BTreeSet::from([source.run_dir.join("review-findings-full.jsonl")]);
    if let Some(parent) = source.path.parent() {
        paths.insert(parent.join("review-findings-full.jsonl"));
    }
    let mut rows = BTreeMap::new();
    for path in paths {
        let Ok(text) = fs::read_to_string(path) else {
            continue;
        };
        for line in text.lines().filter(|line| !line.trim().is_empty()) {
            let Ok(Value::Object(record)) = serde_json::from_str(line) else {
                continue;
            };
            let id = string(&record, "id");
            let body = string(&record, "prose_body");
            if id.is_empty() || body.is_empty() {
                continue;
            }
            let title = body
                .lines()
                .find_map(|line| {
                    line.strip_prefix("### ")
                        .and_then(|line| line.split_once(": "))
                })
                .map_or_else(|| id.clone(), |(_heading, title)| title.to_owned());
            rows.insert(id, (title, body, string(&record, "category")));
        }
    }
    rows
}

const fn incentive_gate_reason(incentive: IncentiveEra) -> &'static str {
    match incentive {
        IncentiveEra::Shipped => "",
        IncentiveEra::NotShipped => "calibration_incentive_not_shipped",
        IncentiveEra::CheckUnavailable => "calibration_incentive_check_unavailable",
    }
}

fn verdict_incentive(
    issues: &[AnalysisIssue],
    details: &BTreeMap<u64, AnalysisIssue>,
) -> IncentiveEra {
    let bulk_incentive = issues
        .iter()
        .find(|issue| issue.summary.number == INCENTIVE_ISSUE);
    let merged_incentive = details
        .get(&INCENTIVE_ISSUE)
        .map(|detail| merge_issue_detail(bulk_incentive, detail));
    match merged_incentive.as_ref().or(bulk_incentive) {
        Some(issue)
            if issue.summary.state == IssueLifecycle::Closed
                && !issue.summary.closed_by_pull_requests.is_empty()
                && !issue.summary.not_planned() =>
        {
            IncentiveEra::Shipped
        }
        Some(_) => IncentiveEra::NotShipped,
        None => IncentiveEra::CheckUnavailable,
    }
}

fn ground_truth_verdict(
    issues: &[AnalysisIssue],
    details: &mut BTreeMap<u64, AnalysisIssue>,
    options: &AnalyzeOptions,
) -> ExitCode {
    let Some(min_runs) = digits_usize(options.min_runs.trim()) else {
        eprintln!(
            "ERROR=invalid --min-runs {:?}; expected a non-negative integer",
            options.min_runs
        );
        return ExitCode::FAILURE;
    };
    let Ok(since) = NaiveDate::parse_from_str(&options.since_date, "%Y-%m-%d") else {
        eprintln!(
            "ERROR=invalid --since-date {:?}; expected YYYY-MM-DD",
            options.since_date
        );
        return ExitCode::FAILURE;
    };
    let since = since.and_hms_opt(0, 0, 0).map(|value| value.and_utc());
    let minimum_since = NaiveDate::from_ymd_opt(2026, 6, 26)
        .and_then(|date| date.and_hms_opt(0, 0, 0))
        .map(|value| value.and_utc());
    if since < minimum_since {
        eprintln!(
            "ERROR=invalid --since-date {}; verdict mode requires >= {DEFAULT_SINCE_DATE}",
            options.since_date
        );
        return ExitCode::FAILURE;
    }
    if !version_meets_floor(&options.min_larch_version, DEFAULT_MIN_LARCH_VERSION) {
        eprintln!(
            "ERROR=invalid --min-larch-version {:?}; verdict mode requires >= {DEFAULT_MIN_LARCH_VERSION}",
            options.min_larch_version
        );
        return ExitCode::FAILURE;
    }
    if min_runs < 150 {
        eprintln!("ERROR=invalid --min-runs {min_runs}; verdict mode requires >= 150");
        return ExitCode::FAILURE;
    }
    ensure_incentive_detail(issues, details, options.repo.as_deref(), true);
    let filter = CorpusFilter {
        since_date: since,
        min_larch_version: Some(options.min_larch_version.clone()),
    };
    let scan = scan_ground_truth_corpus(&options.log_root, GroundTruthMode::Verdict, &filter);
    let incentive = verdict_incentive(issues, details);
    let issue_degradation = options
        .enrichment_degradation
        .clone()
        .or_else(|| issue_degradation(issues));
    let gate = apply_verdict_gate(
        incentive,
        VerdictGateInputs {
            enrichment_degraded: options.enrichment_degradation.is_some()
                || verdict_enrichment_degraded(issues),
            targeted_fetch_degraded: options.targeted_fetch_degradation.is_some(),
            qualifying_runs: scan.stats.qualifying_runs,
            min_runs,
        },
    );
    let verdict = VerdictReport {
        qualifying_runs: scan.stats.qualifying_runs,
        required_runs: min_runs,
        since_date: options.since_date.clone(),
        min_larch_version: options.min_larch_version.clone(),
        incentive_era_shipped: incentive == IncentiveEra::Shipped,
        incentive_gate_reason: incentive_gate_reason(incentive),
        enrichment_degraded: issue_degradation.clone(),
        targeted_fetch_degraded: options.targeted_fetch_degradation.clone(),
        gate_reason: gate.map(|failure| failure.as_str().to_owned()),
    };
    let text = ground_truth_report(
        issues,
        &options.log_root,
        issue_degradation.as_deref(),
        options.top_k,
        Some(scan),
        Some(&verdict),
    );
    println!("{text}");
    if let Some(reason) = verdict.gate_reason {
        eprintln!(
            "ERROR=ground_truth_verdict_failed reason={reason} qualifying_runs={} required_runs={}",
            verdict.qualifying_runs, verdict.required_runs
        );
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
}

fn verdict_enrichment_degraded(issues: &[AnalysisIssue]) -> bool {
    issues.iter().any(|issue| {
        issue.summary.state_reason_degraded
            || issue.degraded_fields.iter().any(|field| {
                matches!(
                    field.as_str(),
                    "stateReason" | "url" | "closedByPullRequestsReferences"
                )
            })
    })
}

#[cfg(test)]
mod tests {
    use super::{
        AnalysisIssue, AnalyzeOptions, CategoryChoice, FiledOos, VerdictReport, analyze,
        build_report, classify_fate, ensure_incentive_detail, fate_adjusted_oos, fetch,
        fetch_filed_issue_details, filed_oos_records, ground_truth_report, ground_truth_verdict,
        issue_degradation, load_filed_details, load_issues, merge_issue_detail, parse_analyze,
        parse_run, pattern_observations, private_write, render_growth_chart, render_high_risk_oos,
        reviewer_effectiveness, run, value_preview, verdict_enrichment_degraded, wasteful_findings,
    };
    use crate::github_service::with_test_github_service;
    use larch_adapters::github::OctocrabGitHubService;
    use larch_core::{
        CategoryMode, ClassificationSource, CorpusScanStats, GroundTruthCorpusScan, IssueSummary,
        PanelKind, categorize, coverage_stats,
    };
    use larch_test_support::{IssueServiceExchange, IssueServiceStub};
    use serde_json::json;
    use std::{collections::BTreeMap, ffi::OsString, fmt::Write as _, fs, path::Path, sync::Arc};
    use tempfile::tempdir;

    #[test]
    fn recorded_fixture_keeps_the_basic_report_contract() {
        let fixture = tempdir().expect("fixture");
        let path = fixture.path().join("issues.json");
        fs::write(
            &path,
            include_str!("../../../python/analyze-issues-fixture.json"),
        )
        .expect("write fixture");
        let issues = load_issues(&path, false).expect("load fixture");
        let options = AnalyzeOptions {
            json_path: path,
            span_days: 0,
            top_k: 3,
            categories: CategoryChoice::Default,
            log_root: fixture.path().join("missing"),
            repo: None,
            filed_details_path: None,
            ground_truth_verdict: false,
            since_date: "2026-06-26".to_owned(),
            min_runs: "150".to_owned(),
            min_larch_version: "52.1.0".to_owned(),
            lenient: false,
            enrichment_degradation: None,
            targeted_fetch_degradation: None,
        };
        let report = build_report(&issues, &BTreeMap::new(), &options, None);
        for expected in [
            "Bug fix: 3 (",
            "Documentation/contract drift: 2 (",
            "Other: 1 (",
            "Auto-spawned share: 1/10",
            "bug fix: crash in foo",
            "YES=2 NO=1",
            "## Fate-adjusted OOS Scoring",
            "## Ground-truth Voter Calibration",
        ] {
            assert!(report.contains(expected), "missing {expected}: {report}");
        }
    }

    #[test]
    fn growth_data_is_repeatable() {
        let records = [
            json!({"number": 1, "title": "Fix one", "state": "OPEN", "createdAt": "2026-01-01T00:00:00Z"}),
            json!({"number": 2, "title": "Fix two", "state": "OPEN", "createdAt": "2026-01-02T00:00:00Z"}),
        ];
        let issues: Vec<AnalysisIssue> = records
            .iter()
            .filter_map(AnalysisIssue::from_value)
            .collect();
        let summaries: Vec<IssueSummary> =
            issues.iter().map(|issue| issue.summary.clone()).collect();
        let categories = categorize(&summaries, CategoryMode::Default, 10);
        assert_eq!(
            render_growth_chart(&summaries, &categories, 0),
            render_growth_chart(&summaries, &categories, 0)
        );
    }

    #[test]
    fn growth_chart_bounds_an_untrusted_span_before_allocating() {
        let issue = AnalysisIssue::from_value(&json!({
            "number": 1,
            "title": "Fix one",
            "state": "OPEN",
            "createdAt": "2026-01-01T00:00:00Z",
        }))
        .expect("issue");
        let summaries = vec![issue.summary];
        let categories = categorize(&summaries, CategoryMode::Default, 10);

        assert!(
            render_growth_chart(&summaries, &categories, i64::MAX)
                .contains("Growth data exceeds the 10000-bucket safety limit")
        );
    }

    #[test]
    fn combined_away_requires_the_durable_marker_in_an_issue_body() {
        let legacy_body = AnalysisIssue::from_value(&json!({
            "number": 12,
            "state": "CLOSED",
            "body": "Discussion quoted Combined into #99 elsewhere.",
        }))
        .expect("issue");
        let marked_comment = AnalysisIssue::from_value(&json!({
            "number": 13,
            "state": "CLOSED",
            "comments": [{"body": "Combined into #99"}],
        }))
        .expect("issue");

        assert_eq!(classify_fate(&legacy_body).0, "provisional unknown");
        assert_eq!(classify_fate(&marked_comment).0, "docked combined-away");
    }

    #[test]
    fn filed_detail_sidecar_merges_instead_of_erasing_bulk_fields() {
        let bulk = AnalysisIssue::from_value(&json!({
            "number": 12,
            "state": "CLOSED",
            "closedByPullRequestsReferences": [{"url": "https://github.com/o/r/pull/13"}],
            "_larch_degraded_fields": ["stateReason"],
        }))
        .expect("bulk issue");
        let detail = AnalysisIssue::from_value(&json!({
            "number": 12,
            "stateReason": "NOT_PLANNED",
        }))
        .expect("detail issue");
        let merged = merge_issue_detail(Some(&bulk), &detail);

        assert_eq!(merged.summary.state, larch_core::IssueLifecycle::Closed);
        assert!(merged.summary.not_planned());
        assert_eq!(
            merged.summary.closed_by_pull_requests,
            vec!["https://github.com/o/r/pull/13"]
        );
    }

    #[test]
    fn empty_targeted_state_reason_does_not_clear_bulk_degradation() {
        let bulk = AnalysisIssue::from_value(&json!({
            "number": 12,
            "state": "CLOSED",
            "_larch_degraded_fields": ["stateReason"],
        }))
        .expect("bulk issue");
        let detail = AnalysisIssue::from_value(&json!({
            "number": 12,
            "stateReason": "",
        }))
        .expect("detail issue");

        let merged = merge_issue_detail(Some(&bulk), &detail);
        assert!(merged.summary.state_reason_degraded);
        assert!(merged.degraded_fields.contains("stateReason"));
    }

    #[test]
    fn degraded_targeted_closure_data_preserves_complete_bulk_references() {
        let bulk = AnalysisIssue::from_value(&json!({
            "number": 12,
            "closedByPullRequestsReferences": [{"url": "https://github.com/o/r/pull/13"}],
        }))
        .expect("bulk issue");
        let detail = AnalysisIssue::from_value(&json!({
            "number": 12,
            "closedByPullRequestsReferences": [],
            "_larch_degraded_fields": ["closedByPullRequestsReferences"],
        }))
        .expect("detail issue");

        let merged = merge_issue_detail(Some(&bulk), &detail);
        assert_eq!(
            merged.summary.closed_by_pull_requests,
            vec!["https://github.com/o/r/pull/13"]
        );
        assert!(
            !merged
                .degraded_fields
                .contains("closedByPullRequestsReferences")
        );
    }

    #[test]
    fn failed_filed_detail_sidecar_marks_the_verdict_fetch_as_degraded() {
        let directory = tempdir().expect("directory");
        let path = directory.path().join("details.json");
        fs::write(
            &path,
            r#"{"12":{"__fetch_failed__":true},"13":{"state":"CLOSED"}}"#,
        )
        .expect("write sidecar");

        let (details, degradation) = load_filed_details(Some(&path)).expect("load sidecar");
        assert_eq!(details.len(), 2);
        assert_eq!(degradation.as_deref(), Some("targeted_fetch_degraded"));
    }

    #[test]
    fn failed_targeted_detail_preserves_a_usable_bulk_fate() {
        let bulk = AnalysisIssue::from_value(&json!({
            "number": 12,
            "state": "CLOSED",
            "body": "still under review",
        }))
        .expect("bulk issue");
        let failed = AnalysisIssue::from_value(&json!({
            "number": 12,
            "__fetch_failed__": true,
        }))
        .expect("failed detail");
        let merged = merge_issue_detail(Some(&bulk), &failed);

        assert!(merged.fetch_failed);
        assert_eq!(classify_fate(&merged).0, "provisional unknown");
    }

    #[test]
    fn missing_closure_references_degrade_the_verdict_gate() {
        let issue = AnalysisIssue::from_value(&json!({
            "number": 12,
            "_larch_degraded_fields": ["closedByPullRequestsReferences"],
        }))
        .expect("issue");

        assert!(verdict_enrichment_degraded(&[issue]));
    }

    #[test]
    fn verdict_incentive_uses_a_typed_fallback_when_the_snapshot_omits_it() {
        let mut incentive: serde_json::Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("fixture");
        incentive["number"] = json!(5_544);
        incentive["state"] = json!("closed");
        incentive["state_reason"] = json!("completed");
        incentive["pull_request"] = serde_json::Value::Null;
        let server = IssueServiceStub::start([
            IssueServiceExchange::any_json(200, incentive.to_string()).expect("issue exchange"),
            IssueServiceExchange::json(
                "POST",
                "/graphql",
                200,
                json!({
                    "data": {"repository": {"issues": {
                        "nodes": [{
                            "number": 5_544,
                            "closedByPullRequestsReferences": {
                                "nodes": [{"url": "https://github.com/o/r/pull/1"}],
                                "pageInfo": {"hasNextPage": false}
                            }
                        }],
                        "pageInfo": {"hasNextPage": false, "endCursor": null}
                    }}}
                })
                .to_string(),
            )
            .expect("closure exchange"),
        ])
        .expect("server");
        let base = server.base_url().to_owned();
        let service: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        let mut details = BTreeMap::new();

        with_test_github_service(service, || {
            ensure_incentive_detail(&[], &mut details, Some("o/r"), true);
        });

        let incentive = details.get(&5_544).expect("fallback issue");
        assert_eq!(incentive.summary.state, larch_core::IssueLifecycle::Closed);
        assert_eq!(
            incentive.summary.closed_by_pull_requests,
            vec!["https://github.com/o/r/pull/1"]
        );
        assert_eq!(server.finish().expect("requests").len(), 2);
    }

    #[test]
    fn filed_oos_records_read_design_file_maps() {
        let root = tempdir().expect("log root");
        let run = root.path().join("design/run-1");
        fs::create_dir_all(&run).expect("run directory");
        fs::write(run.join("manifest.json"), r#"{"issue_number":1}"#).expect("manifest");
        fs::write(
            run.join("oos-accepted-design.md"),
            "### OOS_7: design item\n- **Reviewer**: architect\n",
        )
        .expect("accepted finding");
        fs::write(
            run.join("oos-issues-created.md"),
            "OOS_FILE_MAP\t7\thttps://github.com/o/r/issues/77\n",
        )
        .expect("file map");

        let records = filed_oos_records(root.path());
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].number, Some(77));
        assert_eq!(records[0].reviewers, vec!["architect"]);
    }

    #[test]
    fn degraded_bulk_enrichment_keeps_filed_oos_provisional() {
        let root = tempdir().expect("log root");
        let run = root.path().join("design/run-1");
        fs::create_dir_all(&run).expect("run directory");
        fs::write(run.join("manifest.json"), r#"{"issue_number":1}"#).expect("manifest");
        fs::write(
            run.join("oos-accepted-design.md"),
            "### OOS_7: design item\n- **Reviewer**: architect\n",
        )
        .expect("accepted finding");
        fs::write(
            run.join("oos-issues-created.md"),
            "OOS_FILE_MAP\t7\thttps://github.com/o/r/issues/77\n",
        )
        .expect("file map");

        let report = fate_adjusted_oos(
            &[],
            &BTreeMap::new(),
            root.path(),
            Some("o/r"),
            Some("bulk_fetch_failed"),
            None,
        );
        assert!(report.contains("- Overall provisional points: 1"));
        assert!(report.contains("- Overall fate-adjusted points: 1"));
        assert!(report.contains("- enrichment unavailable: 1"));
    }

    #[test]
    fn legacy_help_flags_exit_successfully() {
        assert_eq!(
            fetch(&[OsString::from("--help")]),
            std::process::ExitCode::SUCCESS
        );
    }

    #[test]
    fn typed_argument_errors_precede_a_later_help_flag() {
        let arguments = [
            "--json",
            "ignored.json",
            "--span-days",
            "not-an-integer",
            "--help",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        assert_eq!(analyze(&arguments), std::process::ExitCode::from(2));
    }

    #[test]
    fn zero_limit_writes_an_empty_private_snapshot_without_a_network_read() {
        let directory = tempdir().expect("directory");
        let output = directory.path().join("issues.json");
        let arguments = [
            "--repo",
            "o/r",
            "--limit",
            "0",
            "--output",
            output.to_str().expect("UTF-8 output"),
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();

        assert_eq!(fetch(&arguments), std::process::ExitCode::SUCCESS);
        assert_eq!(fs::read_to_string(&output).expect("snapshot"), "[]");
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;
            assert_eq!(
                fs::metadata(&output).expect("mode").permissions().mode() & 0o777,
                0o600
            );
        }
    }

    #[test]
    fn top_k_aliases_keep_argparse_last_option_wins_behavior() {
        let arguments = ["--top-k", "2", "--top-K", "7"]
            .into_iter()
            .map(OsString::from)
            .collect::<Vec<_>>();
        assert_eq!(parse_run(&arguments).expect("valid arguments").top_k, 7);
    }

    #[test]
    fn typed_fetch_writes_a_private_untrusted_snapshot() {
        let mut issue: serde_json::Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("fixture");
        issue["number"] = json!(7);
        issue["title"] = json!("{{untrusted title}}");
        issue["body"] = json!("{{untrusted body}}");
        issue["state"] = json!("open");
        issue["html_url"] = json!("https://github.com/o/r/issues/7");
        issue["labels"] = json!([]);
        issue["pull_request"] = serde_json::Value::Null;
        let server = IssueServiceStub::start([
            IssueServiceExchange::any_json(200, json!([issue]).to_string())
                .expect("issue-list exchange"),
            IssueServiceExchange::json(
                "POST",
                "/graphql",
                200,
                json!({
                    "data": {
                        "repository": {
                            "issues": {
                                "nodes": [{
                                    "number": 7,
                                    "closedByPullRequestsReferences": {
                                        "nodes": [{"url": "https://github.com/o/r/pull/8"}],
                                        "pageInfo": {"hasNextPage": false}
                                    }
                                }],
                                "pageInfo": {"hasNextPage": false, "endCursor": null}
                            }
                        }
                    }
                })
                .to_string(),
            )
            .expect("closure exchange"),
        ])
        .expect("server");
        let base = server.base_url().to_owned();
        let service: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        let directory = tempdir().expect("directory");
        let output = directory.path().join("issues.json");
        let arguments = [
            "--repo",
            "o/r",
            "--limit",
            "10",
            "--output",
            output.to_str().expect("UTF-8 output"),
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();

        assert_eq!(
            with_test_github_service(service, || fetch(&arguments)),
            std::process::ExitCode::SUCCESS
        );
        let payload: serde_json::Value =
            serde_json::from_slice(&fs::read(&output).expect("snapshot")).expect("JSON");
        assert_eq!(payload[0]["title"], "{{untrusted title}}");
        assert_eq!(
            payload[0]["closedByPullRequestsReferences"],
            json!([{"url": "https://github.com/o/r/pull/8"}])
        );
        assert!(payload[0].get("_larch_degraded_fields").is_none());
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;
            assert_eq!(
                fs::metadata(&output).expect("mode").permissions().mode() & 0o777,
                0o600
            );
        }
        let requests = server.finish().expect("requests");
        assert_eq!(requests.len(), 2);
        assert_eq!(requests[1].path, "/graphql");
    }

    #[test]
    fn run_keeps_its_private_snapshot_for_follow_up_reanalysis() {
        let fixture = tempdir().expect("fixture directory");
        let nonce: String = fixture
            .path()
            .file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("fixture")
            .chars()
            .filter(char::is_ascii_alphanumeric)
            .collect();
        let repo = format!("o/r-{nonce}");
        let snapshot = std::env::temp_dir().join(format!("o-r-{nonce}-issues.json"));
        assert!(
            !snapshot.exists(),
            "the unique test snapshot must not overwrite an existing file"
        );
        let mut issue: serde_json::Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("fixture");
        issue["number"] = json!(7);
        issue["title"] = json!("Persisted snapshot");
        issue["body"] = json!("Snapshot body");
        issue["state"] = json!("open");
        let api_host = ["api", "github", "com"].join(".");
        issue["repository_url"] = json!(format!("https://{api_host}/repos/{repo}"));
        issue["html_url"] = json!("https://github.com/o/r/issues/7");
        issue["labels"] = json!([]);
        issue["pull_request"] = serde_json::Value::Null;
        let server = IssueServiceStub::start([
            IssueServiceExchange::any_json(200, json!([issue]).to_string())
                .expect("issue-list exchange"),
            IssueServiceExchange::json(
                "POST",
                "/graphql",
                200,
                json!({
                    "data": {
                        "repository": {
                            "issues": {
                                "nodes": [{
                                    "number": 7,
                                    "closedByPullRequestsReferences": {
                                        "nodes": [],
                                        "pageInfo": {"hasNextPage": false}
                                    }
                                }],
                                "pageInfo": {"hasNextPage": false, "endCursor": null}
                            }
                        }
                    }
                })
                .to_string(),
            )
            .expect("closure exchange"),
        ])
        .expect("server");
        let base = server.base_url().to_owned();
        let service: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        let arguments = [
            "--repo",
            repo.as_str(),
            "--limit",
            "10",
            "--log-root",
            fixture.path().to_str().expect("UTF-8 log root"),
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();

        assert_eq!(
            with_test_github_service(service, || run(&arguments)),
            std::process::ExitCode::SUCCESS
        );
        assert!(
            snapshot.is_file(),
            "run must leave the fetched snapshot in place"
        );
        let observed = server.requests().expect("observed requests");
        assert_eq!(
            observed.len(),
            2,
            "run must request list plus closures: {observed:#?}"
        );
        let snapshot_text = fs::read_to_string(&snapshot).expect("read snapshot");
        assert!(
            snapshot_text.contains("\"number\":7"),
            "run snapshot omitted the fetched issue: {snapshot_text}"
        );
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;
            assert_eq!(
                fs::metadata(&snapshot).expect("mode").permissions().mode() & 0o777,
                0o600
            );
        }
        fs::remove_file(&snapshot).expect("remove unique test snapshot");
        let requests = server.finish().expect("requests");
        assert_eq!(requests.len(), 2);
    }

    fn analysis_issue(value: &serde_json::Value) -> AnalysisIssue {
        AnalysisIssue::from_value(value).expect("valid analysis issue")
    }

    #[test]
    fn rich_backlog_fixture_exercises_every_report_section() {
        let issues: Vec<AnalysisIssue> = (1_u64..=12)
            .map(|number| {
                let title = match number {
                    1 => "[DONE] Fix duplicate parser".to_owned(),
                    2 => "Fix duplicate parser".to_owned(),
                    3 => "[STALLED] Revert stale configuration".to_owned(),
                    4 => "[OOS] Fix high-risk parser crash".to_owned(),
                    5..=7 => format!("Fix closure cluster {number}"),
                    _ => format!("Fix reviewer finding {number}"),
                };
                let state = if number == 3 || number == 4 {
                    "OPEN"
                } else {
                    "CLOSED"
                };
                let labels = if number == 4 {
                    json!([{"name": "oos-correctness"}])
                } else {
                    json!([])
                };
                let references = if (5..=7).contains(&number) {
                    json!([{"url": "https://github.com/o/r/pull/42"}])
                } else {
                    json!([])
                };
                analysis_issue(&json!({
                    "number": number,
                    "title": title,
                    "state": state,
                    "createdAt": if number <= 8 { "2026-07-01T00:00:00Z" } else { "2026-07-02T00:00:00Z" },
                    "closedAt": "2026-07-03T00:00:00Z",
                    "body": "Reviewer: Code, Claude Code Reviewer Architect\nYES=2 NO=1 EXONERATE=1\nAutomatically created after revert #deadbeef in src/parser.rs",
                    "labels": labels,
                    "closedByPullRequestsReferences": references,
                    "url": format!("https://github.com/o/r/issues/{number}"),
                }))
            })
            .collect();
        let root = tempdir().expect("log root");
        let options = AnalyzeOptions {
            json_path: root.path().join("issues.json"),
            span_days: 0,
            top_k: 10,
            categories: CategoryChoice::Default,
            log_root: root.path().join("missing"),
            repo: Some("o/r".to_owned()),
            filed_details_path: None,
            ground_truth_verdict: false,
            since_date: "2026-06-26".to_owned(),
            min_runs: "150".to_owned(),
            min_larch_version: "52.1.0".to_owned(),
            lenient: false,
            enrichment_degradation: None,
            targeted_fetch_degradation: None,
        };

        let report = build_report(&issues, &BTreeMap::new(), &options, None);
        for expected in [
            "Bursty filing days:",
            "src/parser.rs",
            "W1 duplicate-titled issues",
            "W2 reversal/supersession",
            "W3 [STALLED] issues: 1 total",
            "W4 PR-to-issue closure clusters",
            "closes 3 issues",
            "W5 auto-loop duplicate filings",
            "claude / architect: 1/12 done",
            "#4 (",
        ] {
            assert!(report.contains(expected), "missing {expected}: {report}");
        }
    }

    #[test]
    fn fate_report_handles_every_observable_filed_issue_state() {
        let root = tempdir().expect("log root");
        let run = root.path().join("design/run-1");
        fs::create_dir_all(&run).expect("run directory");
        fs::write(run.join("manifest.json"), r#"{"issue_number":1}"#).expect("manifest");
        fs::write(
            run.join("oos-accepted-design.md"),
            "### OOS_1: one\n- Reviewer: architect\n\
             ### OOS_2: two\n- Reviewer: architect\n\
             ### OOS_3: three\n- Reviewer: architect\n\
             ### OOS_4: four\n- Reviewer: architect\n\
             ### OOS_5: five\n- Reviewer: architect\n\
             ### OOS_6: six\n- Reviewer: architect\n",
        )
        .expect("accepted findings");
        let mut maps = String::new();
        for (index, number) in (77_u64..=82).enumerate() {
            writeln!(
                maps,
                "OOS_FILE_MAP\t{}\thttps://github.com/o/r/issues/{number}",
                index + 1
            )
            .expect("write file map");
        }
        fs::write(run.join("oos-issues-created.md"), maps).expect("file maps");
        let issues = vec![
            analysis_issue(&json!({"number": 77, "state": "OPEN"})),
            analysis_issue(&json!({
                "number": 78,
                "state": "CLOSED",
                "closedByPullRequestsReferences": [{"url": "https://github.com/o/r/pull/1"}],
            })),
            analysis_issue(&json!({
                "number": 79,
                "state": "CLOSED",
                "body": "<!-- larch:combined-away source=#79 target=#1 -->",
            })),
            analysis_issue(&json!({
                "number": 80,
                "state": "CLOSED",
                "stateReason": "NOT_PLANNED",
            })),
            analysis_issue(&json!({"number": 81, "state": "CLOSED"})),
        ];
        let details = BTreeMap::from([(82_u64, super::failed_filed_issue(82))]);

        let report = fate_adjusted_oos(&issues, &details, root.path(), Some("o/r"), None, None);
        for expected in [
            "- kept by PR: 1",
            "- provisional open: 1",
            "- provisional unknown: 1",
            "- docked closed-unfixed: 1",
            "- docked combined-away: 1",
            "- skipped missing issue: 1",
            "- degraded comment fetch: 1",
        ] {
            assert!(report.contains(expected), "missing {expected}: {report}");
        }
    }

    #[allow(clippy::too_many_lines)] // One fixture keeps classification evidence and verdict inputs adjacent.
    #[test]
    fn ground_truth_rendering_and_verdict_cover_rich_classification_evidence() {
        let root = tempdir().expect("log root");
        let run = root.path().join("design/run-1");
        let round = run.join("plan-review/round-1");
        fs::create_dir_all(&round).expect("round directory");
        fs::write(
            run.join("manifest.json"),
            r#"{"issue_number":1,"started_at":"2026-07-01T00:00:00Z","ended_at":"2026-07-02T00:00:00Z","larch_version":"52.1.0"}"#,
        )
        .expect("manifest");
        let classification = round.join("findings-classification.tsv");
        fs::write(
            &classification,
            "finding_id\tvoting_result\tscope\tv1_vote\tv1_severity\tv1_tool\tv2_vote\tv2_severity\tv2_tool\n\
             F1\taccepted\tin_scope\tYES\tmajor\tcodex\tNO\tminor\tcursor\n\
             F2\trejected\tin_scope\tNO\tminor\tcodex\tYES\tmajor\tcursor\n\
             OOS_1\taccepted\toos\tYES\tmajor\tcodex\tNO\tminor\tcursor\n\
             BAD\tneutral\tin_scope\tMAYBE\t\t\t\t\t\n",
        )
        .expect("classification");
        fs::write(
            run.join("review-findings-full.jsonl"),
            "{\"id\":\"F1\",\"prose_body\":\"### F1: Parser crash\\nThe parser crashes in src/parser.rs.\",\"category\":\"Bug fix\"}\n\
             {\"id\":\"F2\",\"prose_body\":\"### F2: Unmatched finding\\nNo matching issue.\",\"category\":\"Other\"}\n",
        )
        .expect("prose");
        let source = ClassificationSource {
            panel_kind: PanelKind::Design,
            path: classification,
            run_dir: run,
            run_dir_key: "design/run-1".to_owned(),
            run_id: "run-1".to_owned(),
            round_num: 1,
            started_at: Some("2026-06-30T00:00:00Z".parse().expect("started at")),
            run_ended_at: None,
            multi_round: false,
        };
        let scan = GroundTruthCorpusScan {
            sources: vec![source],
            stats: CorpusScanStats {
                files_seen: 1,
                qualifying_runs: 1,
                ..CorpusScanStats::default()
            },
            warnings: Vec::new(),
        };
        let issues = vec![
            analysis_issue(&json!({
                "number": 1,
                "title": "[DONE] Revert parser crash",
                "body": "Revert parser crash in src/parser.rs.",
                "state": "CLOSED",
                "createdAt": "2026-07-01T00:00:00Z",
                "closedAt": "2026-07-03T00:00:00Z",
                "closedByPullRequestsReferences": [{"url": "https://github.com/o/r/pull/1"}],
            })),
            analysis_issue(&json!({
                "number": 2,
                "title": "[DONE] Fix unmatched finding",
                "body": "Fix unmatched finding.",
                "state": "CLOSED",
                "createdAt": "2026-07-01T00:00:00Z",
                "closedAt": "2026-07-03T00:00:00Z",
                "closedByPullRequestsReferences": [{"url": "https://github.com/o/r/pull/2"}],
            })),
            analysis_issue(&json!({
                "number": 5_544,
                "state": "CLOSED",
                "closedByPullRequestsReferences": [{"url": "https://github.com/o/r/pull/3"}],
            })),
        ];
        let calibration =
            ground_truth_report(&issues, root.path(), None, 3, Some(scan.clone()), None);
        assert!(calibration.contains("Classification rows scanned: 4"));
        assert!(calibration.contains("Per-voter realized alignment:"));
        assert!(calibration.contains("Severity slice for decisive YES votes:"));
        assert!(calibration.contains("| design | codex |"), "{calibration}");

        let verdict = VerdictReport {
            qualifying_runs: 1,
            required_runs: 150,
            since_date: "2026-06-26".to_owned(),
            min_larch_version: "52.1.0".to_owned(),
            incentive_era_shipped: true,
            incentive_gate_reason: "",
            enrichment_degraded: Some("bulk_fetch_failed".to_owned()),
            targeted_fetch_degraded: Some("targeted_fetch_degraded".to_owned()),
            gate_reason: Some("corpus_below_min_runs".to_owned()),
        };
        let verdict_text = ground_truth_report(
            &issues,
            root.path(),
            Some("bulk_fetch_failed"),
            3,
            Some(scan),
            Some(&verdict),
        );
        assert!(verdict_text.contains("## Ground-truth Verdict for Token Allocation"));
        assert!(verdict_text.contains("- Gate result: FAIL"));

        let options = AnalyzeOptions {
            json_path: root.path().join("issues.json"),
            span_days: 0,
            top_k: 3,
            categories: CategoryChoice::Default,
            log_root: root.path().to_path_buf(),
            repo: Some("o/r".to_owned()),
            filed_details_path: None,
            ground_truth_verdict: true,
            since_date: "2026-06-26".to_owned(),
            min_runs: "150".to_owned(),
            min_larch_version: "52.1.0".to_owned(),
            lenient: false,
            enrichment_degradation: None,
            targeted_fetch_degradation: None,
        };
        let mut details = BTreeMap::new();
        assert_eq!(
            ground_truth_verdict(&issues, &mut details, &options),
            std::process::ExitCode::FAILURE
        );
    }

    #[test]
    fn command_inputs_preserve_lenient_and_empty_snapshot_paths() {
        let directory = tempdir().expect("directory");
        let dump = directory.path().join("issues.json");
        fs::write(
            &dump,
            "[null,{\"number\":1,\"title\":\"first\"},{\"number\":1,\"title\":\"duplicate\"},{\"number\":\"bad\"}]",
        )
        .expect("dump");
        assert!(load_issues(&dump, false).is_err());
        assert_eq!(load_issues(&dump, true).expect("lenient").len(), 1);

        let empty = directory.path().join("empty.json");
        fs::write(&empty, "[]").expect("empty dump");
        let arguments = ["--json", empty.to_str().expect("UTF-8 path")]
            .into_iter()
            .map(OsString::from)
            .collect::<Vec<_>>();
        assert_eq!(analyze(&arguments), std::process::ExitCode::SUCCESS);
        assert_eq!(fetch(&[]), std::process::ExitCode::from(2));
        assert_eq!(
            fetch(&[
                OsString::from("--repo"),
                OsString::from("o/r"),
                OsString::from("--limit"),
                OsString::from("not-a-number"),
                OsString::from("--output"),
                OsString::from(directory.path().join("ignored.json").as_os_str()),
            ]),
            std::process::ExitCode::FAILURE
        );
    }

    #[test]
    fn targeted_issue_details_use_typed_comments_and_closure_reads() {
        let mut issue: serde_json::Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("fixture");
        issue["number"] = json!(77);
        issue["state"] = json!("closed");
        issue["html_url"] = json!("https://github.com/o/r/issues/77");
        issue["pull_request"] = serde_json::Value::Null;
        let server = IssueServiceStub::start([
            IssueServiceExchange::json(
                "POST",
                "/graphql",
                200,
                json!({
                    "data": {"repository": {"issues": {
                        "nodes": [{
                            "number": 77,
                            "closedByPullRequestsReferences": {
                                "nodes": [{"url": "https://github.com/o/r/pull/8"}],
                                "pageInfo": {"hasNextPage": false}
                            }
                        }],
                        "pageInfo": {"hasNextPage": false, "endCursor": null}
                    }}}
                })
                .to_string(),
            )
            .expect("closure exchange"),
            IssueServiceExchange::any_json(200, issue.to_string()).expect("issue exchange"),
            IssueServiceExchange::any_json(200, json!([]).to_string()).expect("comments exchange"),
        ])
        .expect("server");
        let base = server.base_url().to_owned();
        let service: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        let records = vec![FiledOos {
            identity: "run:https://github.com/o/r/issues/77".to_owned(),
            number: Some(77),
            url: "https://github.com/o/r/issues/77".to_owned(),
            reviewers: vec!["architect".to_owned()],
        }];

        let (details, degradation) =
            with_test_github_service(service, || fetch_filed_issue_details("o/r", &records, &[]));
        let detail = details.get(&77).expect("targeted detail");
        assert_eq!(degradation, None);
        assert!(detail.comments.is_empty());
        assert_eq!(
            detail.summary.closed_by_pull_requests,
            vec!["https://github.com/o/r/pull/8"]
        );
        assert_eq!(server.finish().expect("requests").len(), 3);

        assert_eq!(
            fetch_filed_issue_details("bad-repo", &records, &[])
                .1
                .as_deref(),
            Some("targeted_repo_invalid")
        );
        assert!(fetch_filed_issue_details("o/r", &[], &[]).0.is_empty());
    }

    #[test]
    fn targeted_detail_failures_remain_explicitly_degraded() {
        let mut issue: serde_json::Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("fixture");
        issue["number"] = json!(78);
        issue["html_url"] = json!("https://github.com/o/r/issues/78");
        issue["pull_request"] = serde_json::Value::Null;
        let server = IssueServiceStub::start([
            IssueServiceExchange::any_json(404, "{}").expect("missing issue"),
            IssueServiceExchange::any_json(200, issue.to_string()).expect("issue exchange"),
            IssueServiceExchange::any_json(404, "{}").expect("missing comments"),
        ])
        .expect("server");
        let base = server.base_url().to_owned();
        let service: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        let records = [77_u64, 78]
            .into_iter()
            .map(|number| FiledOos {
                identity: format!("run:https://github.com/o/r/issues/{number}"),
                number: Some(number),
                url: format!("https://github.com/o/r/issues/{number}"),
                reviewers: vec!["architect".to_owned()],
            })
            .collect::<Vec<_>>();
        let bulk = records
            .iter()
            .map(|record| {
                analysis_issue(&json!({
                    "number": record.number,
                    "closedByPullRequestsReferences": [],
                }))
            })
            .collect::<Vec<_>>();

        let (details, degradation) = with_test_github_service(service, || {
            fetch_filed_issue_details("o/r", &records, &bulk)
        });
        assert_eq!(degradation.as_deref(), Some("targeted_fetch_degraded"));
        assert!(details.values().all(|detail| detail.fetch_failed));
        assert_eq!(server.finish().expect("requests").len(), 3);
    }

    #[test]
    fn parser_and_filesystem_failures_keep_their_legacy_exit_paths() {
        let directory = tempdir().expect("directory");
        let not_directory = directory.path().join("not-a-directory");
        fs::write(&not_directory, "file").expect("file");
        assert_eq!(
            private_write(&not_directory.join("issues.json"), "[]"),
            Err("output parent is not a directory".to_owned())
        );
        assert_eq!(
            private_write(directory.path(), "[]"),
            Err("output path is not a regular file".to_owned())
        );

        let malformed = directory.path().join("malformed.json");
        fs::write(&malformed, "not JSON").expect("malformed dump");
        assert!(load_issues(&malformed, false).is_err());
        fs::write(&malformed, "{}").expect("object dump");
        assert!(load_issues(&malformed, false).is_err());
        assert!(
            load_filed_details(Some(&malformed))
                .expect("empty sidecar")
                .0
                .is_empty()
        );
        fs::write(&malformed, r#"{"wrong":{"body":"ignored"}}"#).expect("sidecar");
        assert!(load_filed_details(Some(&malformed)).is_err());

        let invalid_category = ["--json", "issues.json", "--categories", "unsupported"]
            .into_iter()
            .map(OsString::from)
            .collect::<Vec<_>>();
        assert!(parse_analyze(&invalid_category).is_err());
        assert!(parse_run(&invalid_category[2..]).is_err());
    }

    #[test]
    fn empty_and_windowed_reports_cover_the_nonfinding_paths() {
        let empty = Vec::<AnalysisIssue>::new();
        let empty_root = tempdir().expect("empty root");
        assert!(wasteful_findings(&empty, 1).contains("None detected."));
        assert!(
            reviewer_effectiveness(&empty)
                .text
                .contains("No reviewer attribution")
        );
        assert!(render_high_risk_oos(&empty, 1).contains("No open high-risk"));
        assert!(
            fate_adjusted_oos(
                &empty,
                &BTreeMap::new(),
                empty_root.path(),
                None,
                None,
                None,
            )
            .contains("No filed OOS run-log evidence")
        );

        let issues: Vec<AnalysisIssue> = (1_u64..=6)
            .map(|number| {
                let created = if number <= 4 {
                    "2026-07-01T00:00:00Z"
                } else if number == 5 {
                    "2026-07-02T00:00:00Z"
                } else {
                    "2026-07-03T00:00:00Z"
                };
                analysis_issue(&json!({
                    "number": number,
                    "title": format!("Fix window {number}"),
                    "state": "OPEN",
                    "createdAt": created,
                }))
            })
            .collect();
        let summaries: Vec<IssueSummary> =
            issues.iter().map(|issue| issue.summary.clone()).collect();
        let categories = categorize(&summaries, CategoryMode::Default, 10);
        let chart = render_growth_chart(&summaries, &categories, 2);
        assert!(chart.contains("2026-07-01 -> 2026-07-03"));
        let patterns = pattern_observations(&issues, 1, &coverage_stats(&summaries));
        assert!(patterns.contains("2026-07-01: 4 issues"));
        assert!(patterns.contains("None detected."));
    }

    #[test]
    fn failed_bulk_fetch_falls_back_without_leaving_the_typed_boundary() {
        let root = tempdir().expect("log root");
        let server = IssueServiceStub::start([
            IssueServiceExchange::any_json(200, "{}").expect("malformed list response")
        ])
        .expect("server");
        let base = server.base_url().to_owned();
        let service: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        let arguments = [
            "--repo",
            "o/r",
            "--log-root",
            root.path().to_str().expect("UTF-8 path"),
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();

        assert_eq!(
            with_test_github_service(service, || run(&arguments)),
            std::process::ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("requests").len(), 1);
    }

    #[test]
    fn run_without_a_valid_repo_remains_offline_and_reports_degradation() {
        let root = tempdir().expect("log root");
        let arguments = [
            "--repo",
            "not-a-repository",
            "--log-root",
            root.path().to_str().expect("UTF-8 path"),
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        assert_eq!(run(&arguments), std::process::ExitCode::SUCCESS);

        let verdict_arguments = [
            "--repo",
            "not-a-repository",
            "--log-root",
            root.path().to_str().expect("UTF-8 path"),
            "--ground-truth-verdict",
            "--min-runs",
            "not-a-number",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        assert_eq!(run(&verdict_arguments), std::process::ExitCode::FAILURE);
    }

    #[test]
    fn loaders_keep_untrusted_boundary_failures_and_previews_explicit() {
        let directory = tempdir().expect("directory");
        assert!(
            load_issues(Path::new(""), false)
                .expect("empty input")
                .is_empty()
        );
        assert!(load_issues(&directory.path().join("missing.json"), false).is_err());

        let oversized = directory.path().join("oversized.json");
        fs::File::create(&oversized)
            .expect("oversized file")
            .set_len(64 * 1024 * 1024 + 1)
            .expect("sparse size");
        assert!(load_issues(&oversized, false).is_err());

        let details = directory.path().join("details.json");
        fs::write(&details, "[]").expect("non-object details");
        assert!(load_filed_details(Some(&details)).is_err());
        fs::write(&details, r#"{"0":{"body":"ignored"}}"#).expect("zero details key");
        assert!(load_filed_details(Some(&details)).is_err());

        assert_eq!(value_preview(&json!(true)), "True");
        assert_eq!(value_preview(&json!(42)), "42");
        assert_eq!(
            value_preview(&json!("x".repeat(60))),
            format!("\"{}...", "x".repeat(56))
        );
        let issue = analysis_issue(&json!({
            "number": 1,
            "comments": ["literal", {"body": "object"}, 9],
            "_larch_degraded_fields": ["stateReason"],
        }));
        assert_eq!(issue.comments, ["literal", "object"]);
        assert_eq!(
            issue_degradation(&[issue]).as_deref(),
            Some("bulk_issue_fields_degraded:stateReason")
        );
    }

    #[test]
    fn verdict_validation_refuses_each_bounded_operator_override() {
        let root = tempdir().expect("log root");
        let base = AnalyzeOptions {
            json_path: root.path().join("issues.json"),
            span_days: 0,
            top_k: 1,
            categories: CategoryChoice::Default,
            log_root: root.path().to_path_buf(),
            repo: None,
            filed_details_path: None,
            ground_truth_verdict: true,
            since_date: "2026-06-26".to_owned(),
            min_runs: "150".to_owned(),
            min_larch_version: "52.1.0".to_owned(),
            lenient: false,
            enrichment_degradation: None,
            targeted_fetch_degradation: None,
        };
        for options in [
            AnalyzeOptions {
                since_date: "not-a-date".to_owned(),
                ..base.clone()
            },
            AnalyzeOptions {
                since_date: "2026-06-25".to_owned(),
                ..base.clone()
            },
            AnalyzeOptions {
                min_larch_version: "1.0.0".to_owned(),
                ..base.clone()
            },
            AnalyzeOptions {
                min_runs: "149".to_owned(),
                ..base
            },
        ] {
            assert_eq!(
                ground_truth_verdict(&[], &mut BTreeMap::new(), &options),
                std::process::ExitCode::FAILURE
            );
        }
    }

    #[test]
    fn ndjson_filed_evidence_carries_reviewer_identity_into_oos_scoring() {
        let root = tempdir().expect("log root");
        let run = root.path().join("design/run-1");
        fs::create_dir_all(&run).expect("run directory");
        fs::write(run.join("manifest.json"), r#"{"issue_number":1}"#).expect("manifest");
        fs::write(
            run.join("oos-accepted-design.md"),
            "### OOS_7: design item\n- **Reviewer**: architect, testing\n",
        )
        .expect("accepted finding");
        fs::write(
            run.join("oos-issues.ndjson"),
            "{\"body\":\"- **Filed URL**: https://github.com/o/r/issues/77\\n- **Stable ID**: oos-accepted-design:OOS_7\"}\n",
        )
        .expect("filed evidence");

        let records = filed_oos_records(root.path());
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].number, Some(77));
        assert_eq!(records[0].reviewers, ["architect", "testing"]);
    }

    #[test]
    fn reviewer_report_normalizes_unknown_and_tied_roi_rows_deterministically() {
        let mut issues: Vec<AnalysisIssue> = (1_u64..=20)
            .map(|number| {
                let codex = number <= 10;
                let title = if number % 10 == 0 {
                    format!("Open finding {number}")
                } else {
                    format!("{}Finding {number}", super::DONE_PREFIX)
                };
                analysis_issue(&json!({
                    "number": number,
                    "title": title,
                    "body": if codex { "Reviewer: codex, architect" } else { "Reviewer: main agent, edge" },
                }))
            })
            .collect();
        issues.push(analysis_issue(&json!({
            "number": 21,
            "title": "Open unattributed shape",
            "body": "Reviewer: no recognized tool or persona",
        })));

        let report = reviewer_effectiveness(&issues);
        assert!(
            report
                .text
                .contains("- unknown / generic: 1 findings, 0 done")
        );
        assert!(report.text.contains("- main agent / edge-cases: 9/10 done"));
        let best = report.best.expect("best reviewer pair");
        assert_eq!(
            (best.tool.as_str(), best.persona.as_str()),
            ("codex", "architect")
        );
        assert_eq!((best.done, best.total), (9, 10));
    }

    #[test]
    fn parser_usage_and_private_zero_limit_failures_remain_compatible() {
        assert!(parse_analyze(&[]).is_err());
        assert!(parse_run(&[OsString::from("--limit")]).is_err());
        assert_eq!(
            fetch(&[OsString::from("--repo")]),
            std::process::ExitCode::from(2)
        );

        let directory = tempdir().expect("directory");
        let arguments = [
            "--repo",
            "o/r",
            "--limit",
            "0",
            "--output",
            directory.path().to_str().expect("UTF-8 path"),
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        assert_eq!(fetch(&arguments), std::process::ExitCode::FAILURE);
    }
}
