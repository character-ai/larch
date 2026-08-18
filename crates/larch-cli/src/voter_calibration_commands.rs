//! Rust owner for the `/voter-calibration` analyzer CLI surface.
//!
//! Mirrors the retired Python analyzer's argparse contract, report bytes, exit
//! codes, and degradation tokens (frozen reference:
//! `fixtures/rust-parity/voter_calibration_frozen/`). Pure math and rendering
//! live in `larch_core::voter_calibration`; this module owns argument parsing,
//! corpus discovery, era-boundary resolution through the typed GitHub owner,
//! and optional realized-outcome enrichment reusing the analyze-issues
//! helpers. Repository identity comes from `--repo` or gix-typed ambient
//! origin resolution; no path shells out to `gh issue`, `gh api`, or raw Git.

use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use chrono::{DateTime, Datelike as _, NaiveDate, Timelike as _, Utc};
use larch_core::{
    EraBoundaryDisplay, IssueLifecycle, RunLogCorpus, RunLogRoundSort, VoterCalibrationCorpus,
    render_era_boundary_unavailable, render_voter_calibration_era_report,
    render_voter_calibration_report, run_started_at_strict,
};

use crate::{
    analyze_issues_commands::{
        AnalysisIssue, FiledOos, fetch, fetch_filed_issue_details, fetch_incentive_issue,
        filed_oos_records, ground_truth_report, load_issues, merge_issue_detail,
    },
    argparse_compat::{
        parse_python_int, parse_with_flags, python_repr, usage_error, write_report_file,
        write_stdout,
    },
    github_repository_resolution::{ambient_repo, validate_repo_slug},
    run_log_publication_commands::{synchronized_corpus_root, synchronized_repository_root},
};

const PROGRAM: &str = "voter-calibration analyze";
const USAGE: &str = "usage: voter-calibration analyze [-h] [--log-root LOG_ROOT] [--min-votes MIN_VOTES] [--outlier-threshold OUTLIER_THRESHOLD] [--high-severity-threshold HIGH_SEVERITY_THRESHOLD] [--out OUT] [--era {all,pre,post}] [--era-since-date ERA_SINCE_DATE] [--realized-outcomes] [--repo REPO] [--filed-issue-details-json FILED_ISSUE_DETAILS_JSON]";
const HELP: &str = "\
usage: voter-calibration analyze [-h] [--log-root LOG_ROOT] [--min-votes MIN_VOTES] [--outlier-threshold OUTLIER_THRESHOLD] [--high-severity-threshold HIGH_SEVERITY_THRESHOLD] [--out OUT] [--era {all,pre,post}] [--era-since-date ERA_SINCE_DATE] [--realized-outcomes] [--repo REPO] [--filed-issue-details-json FILED_ISSUE_DETAILS_JSON]

options:
  -h, --help            show this help message and exit
  --log-root LOG_ROOT
  --min-votes MIN_VOTES
  --outlier-threshold OUTLIER_THRESHOLD
  --high-severity-threshold HIGH_SEVERITY_THRESHOLD
  --out OUT
  --era {all,pre,post}
  --era-since-date ERA_SINCE_DATE
  --realized-outcomes
  --repo REPO
  --filed-issue-details-json FILED_ISSUE_DETAILS_JSON";

const VALUE_OPTIONS: [&str; 9] = [
    "--log-root",
    "--min-votes",
    "--outlier-threshold",
    "--high-severity-threshold",
    "--out",
    "--era",
    "--era-since-date",
    "--repo",
    "--filed-issue-details-json",
];
const FLAG_OPTIONS: [&str; 1] = ["--realized-outcomes"];
const ERA_CHOICES: [&str; 3] = ["all", "pre", "post"];
const GROUND_TRUTH_TOP_K: usize = 10;

struct AnalyzeOptions {
    log_root_raw: String,
    min_votes: i64,
    outlier_threshold: f64,
    high_severity_threshold: f64,
    out: String,
    era: String,
    era_since_date: String,
    realized_outcomes: bool,
    repo: String,
    filed_issue_details_json: String,
}

/// Analyze voter agreement, severity calibration, and chronic outliers over
/// one synchronized or explicitly supplied run-log corpus.
#[must_use]
pub fn analyze(arguments: &[OsString]) -> ExitCode {
    let options = match parse_analyze(arguments) {
        Ok(options) => options,
        Err(code) => return code,
    };
    if !options.era_since_date.is_empty() && options.era.is_empty() {
        eprintln!("voter-calibration: --era-since-date requires --era");
        return ExitCode::from(2);
    }
    let log_root = if options.log_root_raw.is_empty() {
        match synchronized_repository_root().and_then(|root| synchronized_corpus_root(&root)) {
            Ok(root) => root,
            Err(error) => {
                eprintln!("voter-calibration: {error}");
                return ExitCode::from(2);
            }
        }
    } else {
        expand_user(&options.log_root_raw)
    };
    let log_root = resolve_like_python(&log_root);
    if !log_root.is_dir() {
        eprintln!(
            "voter-calibration: resolved log root is missing: {}",
            log_root.display()
        );
        return ExitCode::from(2);
    }

    let discovered = discover(&log_root);
    if !options.era.is_empty() {
        return era_report(&options, &log_root, &discovered);
    }

    let mut corpus = VoterCalibrationCorpus::default();
    for file in &discovered {
        corpus.add_file(file.panel, &read_text(&file.path));
    }
    let realized = realized_section(&options, &log_root);
    let report = render_voter_calibration_report(
        &log_root.display().to_string(),
        &corpus,
        options.min_votes,
        options.outlier_threshold,
        options.high_severity_threshold,
        &realized,
    );
    emit_report(&options.out, &report)
}

fn era_report(
    options: &AnalyzeOptions,
    log_root: &Path,
    discovered: &[DiscoveredFile],
) -> ExitCode {
    let boundary = match resolve_era_boundary(options) {
        Ok(boundary) => boundary,
        Err(code) => return code,
    };
    let repo_display = boundary.repo.clone().unwrap_or_else(|| "n/a".to_owned());
    let report = if let Some(cutoff) = boundary.boundary {
        let (pre, post, excluded) = collect_era_corpora(cutoff, discovered);
        let realized = realized_section(options, log_root);
        render_voter_calibration_era_report(
            &log_root.display().to_string(),
            &options.era,
            &EraBoundaryDisplay {
                source: boundary.source.to_owned(),
                timestamp: python_isoformat_z(cutoff),
                repo: repo_display,
            },
            &pre,
            &post,
            discovered.len(),
            excluded,
            options.min_votes,
            options.outlier_threshold,
            options.high_severity_threshold,
            &realized,
        )
    } else {
        render_era_boundary_unavailable(
            &log_root.display().to_string(),
            boundary.source,
            &repo_display,
            &boundary.reason,
        )
    };
    emit_report(&options.out, &report)
}

fn realized_section(options: &AnalyzeOptions, log_root: &Path) -> String {
    if !options.realized_outcomes {
        return String::new();
    }
    load_realized_outcomes_section(log_root, &options.repo, &options.filed_issue_details_json)
}

fn parse_analyze(arguments: &[OsString]) -> Result<AnalyzeOptions, ExitCode> {
    let help = arguments.iter().position(|argument| {
        let text = argument.to_string_lossy();
        text == "-h" || text == "--help"
    });
    let parsed = parse_with_flags(
        &arguments[..help.unwrap_or(arguments.len())],
        &VALUE_OPTIONS,
        &FLAG_OPTIONS,
        0,
    );
    let mut min_votes: i64 = 20;
    let mut outlier_threshold: f64 = 0.50;
    let mut high_severity_threshold: f64 = 0.90;
    for (option, value) in parsed.entries() {
        let value = value.to_string_lossy();
        match *option {
            "--min-votes" => match parse_python_int(&value) {
                Some(parsed_value) => min_votes = parsed_value,
                None => {
                    return Err(usage_error(
                        USAGE,
                        PROGRAM,
                        &format!(
                            "argument --min-votes: invalid int value: {}",
                            python_repr(&value)
                        ),
                        2,
                    ));
                }
            },
            "--outlier-threshold" | "--high-severity-threshold" => {
                match parse_python_float(&value) {
                    Some(parsed_value) => {
                        if *option == "--outlier-threshold" {
                            outlier_threshold = parsed_value;
                        } else {
                            high_severity_threshold = parsed_value;
                        }
                    }
                    None => {
                        return Err(usage_error(
                            USAGE,
                            PROGRAM,
                            &format!(
                                "argument {option}: invalid float value: {}",
                                python_repr(&value)
                            ),
                            2,
                        ));
                    }
                }
            }
            "--era" => {
                if !ERA_CHOICES.contains(&value.as_ref()) {
                    return Err(usage_error(
                        USAGE,
                        PROGRAM,
                        &format!(
                            "argument --era: invalid choice: {} (choose from 'all', 'pre', 'post')",
                            python_repr(&value)
                        ),
                        2,
                    ));
                }
            }
            _ => {}
        }
    }
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(USAGE, PROGRAM, error, 2));
    }
    if help.is_some() {
        println!("{HELP}");
        return Err(ExitCode::SUCCESS);
    }
    if let Some(error) = parsed.error() {
        return Err(usage_error(USAGE, PROGRAM, &error, 2));
    }
    let text = |name: &str| {
        parsed
            .value(name)
            .map(|value| value.to_string_lossy().into_owned())
            .unwrap_or_default()
    };
    Ok(AnalyzeOptions {
        log_root_raw: text("--log-root"),
        min_votes,
        outlier_threshold,
        high_severity_threshold,
        out: text("--out"),
        era: text("--era"),
        era_since_date: text("--era-since-date"),
        realized_outcomes: parsed.flag("--realized-outcomes"),
        repo: text("--repo"),
        filed_issue_details_json: text("--filed-issue-details-json"),
    })
}

/// Parse a float the way Python `float(str)` does: surrounding whitespace,
/// underscores between digits, and case-insensitive `inf`/`infinity`/`nan`.
fn parse_python_float(raw: &str) -> Option<f64> {
    let text = raw.trim();
    if text.is_empty() {
        return None;
    }
    let mut cleaned = String::with_capacity(text.len());
    let bytes = text.as_bytes();
    for (index, byte) in bytes.iter().enumerate() {
        if *byte == b'_' {
            let digit_before = index > 0 && bytes[index - 1].is_ascii_digit();
            let digit_after = index + 1 < bytes.len() && bytes[index + 1].is_ascii_digit();
            if !digit_before || !digit_after {
                return None;
            }
            continue;
        }
        cleaned.push(*byte as char);
    }
    if !text.is_ascii() {
        return None;
    }
    cleaned.parse::<f64>().ok()
}

fn expand_user(raw: &str) -> PathBuf {
    if raw == "~" {
        if let Some(home) = env::var_os("HOME") {
            return PathBuf::from(home);
        }
    } else if let Some(rest) = raw.strip_prefix("~/")
        && let Some(home) = env::var_os("HOME")
    {
        return PathBuf::from(home).join(rest);
    }
    PathBuf::from(raw)
}

/// Resolve a path the way Python's non-strict `Path.resolve()` does for the
/// cases this analyzer meets: canonicalize when the path exists, else
/// canonicalize the deepest existing ancestor and keep the remainder.
fn resolve_like_python(path: &Path) -> PathBuf {
    if let Ok(resolved) = fs::canonicalize(path) {
        return resolved;
    }
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        env::current_dir().map_or_else(|_| path.to_path_buf(), |cwd| cwd.join(path))
    };
    if let (Some(parent), Some(name)) = (absolute.parent(), absolute.file_name())
        && let Ok(parent) = fs::canonicalize(parent)
    {
        return parent.join(name);
    }
    absolute
}

struct DiscoveredFile {
    panel: &'static str,
    run_dir: PathBuf,
    path: PathBuf,
}

/// Discover canonical classification TSVs in skill order, then run order,
/// then lexical path order, admitting pre-manifest historical runs.
fn discover(log_root: &Path) -> Vec<DiscoveredFile> {
    let mut files = Vec::new();
    for (skill, panel) in [
        ("design", "design"),
        ("implement", "code-review"),
        ("review", "code-review"),
    ] {
        let corpus = RunLogCorpus::new(log_root.join(skill));
        for (run_dir, path) in
            corpus.classification_paths_without_manifest(skill, RunLogRoundSort::Lexical)
        {
            files.push(DiscoveredFile {
                panel,
                run_dir,
                path,
            });
        }
    }
    files
}

fn read_text(path: &Path) -> String {
    fs::read(path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .unwrap_or_default()
}

fn collect_era_corpora(
    boundary: DateTime<Utc>,
    discovered: &[DiscoveredFile],
) -> (VoterCalibrationCorpus, VoterCalibrationCorpus, usize) {
    let mut pre = VoterCalibrationCorpus::default();
    let mut post = VoterCalibrationCorpus::default();
    let mut excluded: std::collections::BTreeSet<&Path> = std::collections::BTreeSet::new();
    for file in discovered {
        let Some(started_at) = run_started_at_strict(&file.run_dir) else {
            let _ = excluded.insert(file.run_dir.as_path());
            continue;
        };
        let corpus = if started_at < boundary {
            &mut pre
        } else {
            &mut post
        };
        corpus.add_file(file.panel, &read_text(&file.path));
    }
    (pre, post, excluded.len())
}

struct BoundaryOutcome {
    boundary: Option<DateTime<Utc>>,
    source: &'static str,
    repo: Option<String>,
    reason: String,
}

fn resolve_era_boundary(options: &AnalyzeOptions) -> Result<BoundaryOutcome, ExitCode> {
    if !options.era_since_date.is_empty() {
        return Ok(BoundaryOutcome {
            boundary: Some(parse_era_since_date(&options.era_since_date)?),
            source: "explicit-date",
            repo: None,
            reason: String::new(),
        });
    }
    Ok(resolve_era_boundary_auto(&options.repo))
}

fn parse_era_since_date(value: &str) -> Result<DateTime<Utc>, ExitCode> {
    if !date_shape_matches(value) {
        eprintln!("voter-calibration: --era-since-date must be YYYY-MM-DD");
        return Err(ExitCode::from(2));
    }
    let parsed = NaiveDate::parse_from_str(value, "%Y-%m-%d")
        .ok()
        .filter(|date| date.year() >= 1)
        .and_then(|date| date.and_hms_opt(0, 0, 0))
        .map(|value| value.and_utc());
    let Some(parsed) = parsed else {
        eprintln!("voter-calibration: --era-since-date must be a valid YYYY-MM-DD date");
        return Err(ExitCode::from(2));
    };
    Ok(parsed)
}

fn date_shape_matches(value: &str) -> bool {
    let bytes = value.as_bytes();
    bytes.len() == 10
        && bytes[0..4].iter().all(u8::is_ascii_digit)
        && bytes[4] == b'-'
        && bytes[5..7].iter().all(u8::is_ascii_digit)
        && bytes[7] == b'-'
        && bytes[8..10].iter().all(u8::is_ascii_digit)
}

/// Resolve the incentive repository: an explicit `--repo` wins, otherwise the
/// gix-typed ambient origin. This deliberately replaces the Python
/// plugin-root `git config` probe (see `docs/skills.md`).
fn resolve_incentive_repo(repo_override: &str) -> Option<String> {
    if !repo_override.is_empty() {
        return validate_repo_slug(repo_override).then(|| repo_override.to_owned());
    }
    ambient_repo().filter(|candidate| validate_repo_slug(candidate))
}

fn resolve_era_boundary_auto(repo_override: &str) -> BoundaryOutcome {
    const SOURCE: &str = "gh-issue-closedAt";
    let Some(repo) = resolve_incentive_repo(repo_override) else {
        return BoundaryOutcome {
            boundary: None,
            source: SOURCE,
            repo: None,
            reason: "repo_unresolved".to_owned(),
        };
    };
    let Some(issue) = fetch_incentive_issue(&repo) else {
        return BoundaryOutcome {
            boundary: None,
            source: SOURCE,
            repo: Some(repo),
            reason: "gh_issue_view_unavailable".to_owned(),
        };
    };
    let shipped = issue.summary.state == IssueLifecycle::Closed
        && !issue.summary.closed_by_pull_requests.is_empty()
        && !issue.summary.not_planned();
    if !shipped {
        return BoundaryOutcome {
            boundary: None,
            source: SOURCE,
            repo: Some(repo),
            reason: "calibration_incentive_not_shipped".to_owned(),
        };
    }
    let Some(boundary) = issue.summary.closed_at else {
        return BoundaryOutcome {
            boundary: None,
            source: SOURCE,
            repo: Some(repo),
            reason: "closedAt_unavailable".to_owned(),
        };
    };
    BoundaryOutcome {
        boundary: Some(boundary),
        source: SOURCE,
        repo: Some(repo),
        reason: String::new(),
    }
}

/// Render a UTC timestamp like Python `isoformat().replace("+00:00", "Z")`.
fn python_isoformat_z(value: DateTime<Utc>) -> String {
    if value.nanosecond() == 0 {
        value.format("%Y-%m-%dT%H:%M:%SZ").to_string()
    } else {
        value.format("%Y-%m-%dT%H:%M:%S%.6fZ").to_string()
    }
}

fn realized_outcomes_skip(reason: &str) -> String {
    [
        "## Realized-outcome voter calibration".to_owned(),
        String::new(),
        format!("- Skipped: `{reason}`."),
        "- Core voter calibration metrics are still available.".to_owned(),
    ]
    .join("\n")
}

/// Extract `owner/name` from a GitHub issue URL the way the Python
/// `extract_repo_from_url` regex did (case-insensitive host and `/issues/`).
fn repo_from_issue_url(url: &str) -> Option<String> {
    let lower = url.to_lowercase();
    let start = lower.find("github.com/")? + "github.com/".len();
    let rest = &url[start..];
    let rest_lower = &lower[start..];
    let issues = rest_lower.find("/issues/")?;
    let repo = &rest[..issues];
    let (owner, name) = repo.split_once('/')?;
    let valid = |segment: &str| {
        !segment.is_empty()
            && !segment
                .chars()
                .any(|c| c == '/' || c == '|' || c == ')' || c.is_whitespace())
    };
    (valid(owner) && valid(name)).then(|| format!("{owner}/{name}"))
}

fn number_from_issue_url(url: &str) -> Option<u64> {
    let start = url.find("/issues/")? + "/issues/".len();
    let digits: String = url[start..]
        .chars()
        .take_while(char::is_ascii_digit)
        .collect();
    (!digits.is_empty()).then(|| digits.parse().ok()).flatten()
}

/// Return whether `gh` resolves on `PATH`, mirroring `shutil.which("gh")`.
fn gh_available() -> bool {
    let Some(path) = env::var_os("PATH") else {
        return false;
    };
    env::split_paths(&path).any(|directory| {
        if directory.as_os_str().is_empty() {
            return false;
        }
        is_executable_file(&directory.join("gh"))
    })
}

#[cfg(unix)]
fn is_executable_file(path: &Path) -> bool {
    use std::os::unix::fs::PermissionsExt as _;
    fs::metadata(path)
        .map(|metadata| metadata.is_file() && metadata.permissions().mode() & 0o111 != 0)
        .unwrap_or(false)
}

#[cfg(not(unix))]
fn is_executable_file(path: &Path) -> bool {
    fs::metadata(path)
        .map(|metadata| metadata.is_file())
        .unwrap_or(false)
}

/// Load `--filed-issue-details-json`, mapping failures to the Python
/// exception-class skip tokens the retired analyzer emitted.
fn load_filed_issue_details(
    path: &Path,
) -> Result<(Vec<AnalysisIssue>, BTreeMap<u64, AnalysisIssue>), &'static str> {
    let bytes = fs::read(path).map_err(|error| match error.kind() {
        std::io::ErrorKind::NotFound => "FileNotFoundError",
        std::io::ErrorKind::PermissionDenied => "PermissionError",
        _ => "OSError",
    })?;
    let value: serde_json::Value = serde_json::from_slice(&bytes).map_err(|_| "JSONDecodeError")?;
    let Some(rows) = value.as_object() else {
        return Err("SystemExit");
    };
    let mut issues = Vec::new();
    let mut details = BTreeMap::new();
    for (key, item) in rows {
        let number = parse_details_key(key).ok_or("SystemExit")?;
        if !item.is_object() {
            continue;
        }
        if let Some(issue) = AnalysisIssue::from_value(item) {
            issues.push(issue.clone());
            details.insert(number, issue);
        }
    }
    Ok((issues, details))
}

fn parse_details_key(key: &str) -> Option<u64> {
    (!key.is_empty() && key.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| key.parse::<u64>().ok())
        .flatten()
        .filter(|value| *value > 0)
}

/// Build the optional realized-outcome section: resolve the repository,
/// filter filed-OOS candidates, load offline details or fetch a bounded
/// snapshot plus targeted details through the typed service, then append the
/// shared ground-truth calibration report.
fn load_realized_outcomes_section(
    log_root: &Path,
    repo_override: &str,
    filed_issue_details_json: &str,
) -> String {
    let Some(repo) = resolve_incentive_repo(repo_override) else {
        return realized_outcomes_skip("repo_unresolved");
    };
    let records = filed_oos_records(log_root);
    let mut candidate_numbers = std::collections::BTreeSet::new();
    let mut filtered: Vec<FiledOos> = Vec::new();
    for record in records {
        if !record.url.is_empty()
            && let Some(url_repo) = repo_from_issue_url(&record.url)
            && !url_repo.eq_ignore_ascii_case(&repo)
        {
            continue;
        }
        let Some(number) = record.number.or_else(|| number_from_issue_url(&record.url)) else {
            continue;
        };
        let _ = candidate_numbers.insert(number);
        filtered.push(record);
    }
    if candidate_numbers.is_empty() && filed_issue_details_json.is_empty() {
        return realized_outcomes_skip("no_repo_filtered_filed_oos_candidates");
    }
    let mut issues: Vec<AnalysisIssue> = Vec::new();
    let mut details: BTreeMap<u64, AnalysisIssue> = BTreeMap::new();
    let mut enrichment_degraded: Option<&'static str> = None;
    let mut targeted_fetch_degraded: Option<String> = None;
    if filed_issue_details_json.is_empty() {
        if !gh_available() {
            return realized_outcomes_skip("gh_unavailable");
        }
        let dump = env::temp_dir().join(format!(
            "voter-calibration-issues-{}.json",
            std::process::id()
        ));
        let fetch_arguments = vec![
            OsString::from("--repo"),
            OsString::from(&repo),
            OsString::from("--limit"),
            OsString::from("2000"),
            OsString::from("--output"),
            dump.as_os_str().to_owned(),
        ];
        if fetch(&fetch_arguments) == ExitCode::SUCCESS {
            match load_issues(&dump, false) {
                Ok(loaded) => issues = loaded,
                Err(_) => enrichment_degraded = Some("bulk_load_failed"),
            }
        } else {
            enrichment_degraded = Some("bulk_fetch_failed");
        }
        let _ = fs::remove_file(&dump);
        if !candidate_numbers.is_empty() {
            let (fetched, degradation) = fetch_filed_issue_details(&repo, &filtered, &issues);
            details = fetched;
            targeted_fetch_degraded = degradation;
        }
    } else {
        match load_filed_issue_details(Path::new(filed_issue_details_json)) {
            Ok((loaded_issues, loaded_details)) => {
                issues = loaded_issues;
                details = loaded_details;
            }
            Err(name) => {
                return realized_outcomes_skip(&format!("filed_issue_details_unavailable:{name}"));
            }
        }
    }
    issues = merge_filed_details(&issues, &details);
    if issues.is_empty() {
        let targeted = if targeted_fetch_degraded.is_some() {
            "targeted_fetch_failed"
        } else {
            "insufficient_corpus"
        };
        return realized_outcomes_skip(enrichment_degraded.unwrap_or(targeted));
    }
    ground_truth_report(
        &issues,
        log_root,
        enrichment_degraded,
        GROUND_TRUTH_TOP_K,
        None,
        None,
    )
}

/// Fold targeted filed-issue details into the bulk snapshot the way the frozen
/// Python `_merged_issue_index` did: a detail wins field-wise for its own
/// number, and a detail-only number joins the corpus. Without this the
/// targeted fetch would pay for issues the report never sees.
fn merge_filed_details(
    bulk: &[AnalysisIssue],
    details: &BTreeMap<u64, AnalysisIssue>,
) -> Vec<AnalysisIssue> {
    let mut merged: Vec<AnalysisIssue> = bulk
        .iter()
        .map(|issue| {
            details.get(&issue.summary.number).map_or_else(
                || issue.clone(),
                |detail| merge_issue_detail(Some(issue), detail),
            )
        })
        .collect();
    let known: std::collections::BTreeSet<u64> =
        bulk.iter().map(|issue| issue.summary.number).collect();
    merged.extend(
        details
            .iter()
            .filter(|(number, _detail)| !known.contains(number))
            .map(|(_number, detail)| detail.clone()),
    );
    merged
}

/// Normalize a raw `--out` argument the way `str(pathlib.Path(raw))` does.
fn python_path_display(raw: &str) -> String {
    let absolute = raw.starts_with('/');
    let segments: Vec<&str> = raw
        .split('/')
        .filter(|segment| !segment.is_empty() && *segment != ".")
        .collect();
    if segments.is_empty() {
        return if absolute {
            "/".to_owned()
        } else {
            ".".to_owned()
        };
    }
    let joined = segments.join("/");
    if absolute {
        format!("/{joined}")
    } else {
        joined
    }
}

fn emit_report(out: &str, report: &str) -> ExitCode {
    if out.is_empty() {
        return write_stdout(report);
    }
    // `write_report_file` prints the path back, so normalize the raw argument
    // to the `str(pathlib.Path(raw))` spelling first.
    write_report_file(&PathBuf::from(python_path_display(out)), report)
}

#[cfg(test)]
mod tests {
    use super::{
        BoundaryOutcome, date_shape_matches, merge_filed_details, parse_python_float,
        python_isoformat_z, python_path_display, repo_from_issue_url, resolve_era_boundary_auto,
        resolve_incentive_repo,
    };
    use crate::analyze_issues_commands::AnalysisIssue;
    use crate::argparse_compat::parse_python_int;
    use crate::github_service::with_test_github_service;
    use chrono::{TimeZone as _, Utc};
    use larch_adapters::github::OctocrabGitHubService;
    use larch_test_support::{IssueServiceExchange, IssueServiceStub};
    use serde_json::json;
    use std::collections::BTreeMap;
    use std::sync::Arc;

    fn incentive_fixture(state: &str, closed_at: Option<&str>) -> serde_json::Value {
        let mut issue: serde_json::Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("fixture");
        issue["number"] = json!(5_544);
        issue["state"] = json!(state);
        issue["state_reason"] = if state == "closed" {
            json!("completed")
        } else {
            serde_json::Value::Null
        };
        issue["closed_at"] = closed_at.map_or(serde_json::Value::Null, |value| json!(value));
        issue["pull_request"] = serde_json::Value::Null;
        issue
    }

    fn closure_exchange(references: serde_json::Value) -> IssueServiceExchange {
        IssueServiceExchange::json(
            "POST",
            "/graphql",
            200,
            json!({
                "data": {"repository": {"issues": {
                    "nodes": [{
                        "number": 5_544,
                        "closedByPullRequestsReferences": {
                            "nodes": references,
                            "pageInfo": {"hasNextPage": false}
                        }
                    }],
                    "pageInfo": {"hasNextPage": false, "endCursor": null}
                }}}
            })
            .to_string(),
        )
        .expect("closure exchange")
    }

    fn boundary_with_service(exchanges: Vec<IssueServiceExchange>) -> (BoundaryOutcome, usize) {
        let server = IssueServiceStub::start(exchanges).expect("server");
        let base = server.base_url().to_owned();
        let service: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        let outcome = with_test_github_service(service, || resolve_era_boundary_auto("o/r"));
        let requests = server.finish().expect("requests").len();
        (outcome, requests)
    }

    #[test]
    fn shipped_incentive_yields_the_closed_at_boundary() {
        let (outcome, requests) = boundary_with_service(vec![
            IssueServiceExchange::any_json(
                200,
                incentive_fixture("closed", Some("2026-06-26T12:30:00Z")).to_string(),
            )
            .expect("issue exchange"),
            closure_exchange(json!([{"url": "https://github.com/o/r/pull/1"}])),
        ]);

        assert_eq!(outcome.repo.as_deref(), Some("o/r"));
        assert_eq!(outcome.reason, "");
        assert_eq!(
            outcome.boundary.map(python_isoformat_z).as_deref(),
            Some("2026-06-26T12:30:00Z")
        );
        assert_eq!(requests, 2);
    }

    #[test]
    fn unshipped_incentive_reports_the_not_shipped_reason() {
        let (outcome, _requests) = boundary_with_service(vec![
            IssueServiceExchange::any_json(200, incentive_fixture("open", None).to_string())
                .expect("issue exchange"),
            closure_exchange(json!([])),
        ]);

        assert!(outcome.boundary.is_none());
        assert_eq!(outcome.reason, "calibration_incentive_not_shipped");
    }

    #[test]
    fn missing_closed_at_reports_closed_at_unavailable() {
        let (outcome, _requests) = boundary_with_service(vec![
            IssueServiceExchange::any_json(200, incentive_fixture("closed", None).to_string())
                .expect("issue exchange"),
            closure_exchange(json!([{"url": "https://github.com/o/r/pull/1"}])),
        ]);

        assert!(outcome.boundary.is_none());
        assert_eq!(outcome.reason, "closedAt_unavailable");
    }

    #[test]
    fn typed_fetch_failure_reports_gh_issue_view_unavailable() {
        let (outcome, _requests) = boundary_with_service(vec![
            IssueServiceExchange::any_json(404, "{}".to_owned()).expect("issue exchange"),
        ]);

        assert!(outcome.boundary.is_none());
        assert_eq!(outcome.reason, "gh_issue_view_unavailable");
        assert_eq!(outcome.repo.as_deref(), Some("o/r"));
    }

    #[test]
    fn invalid_repo_overrides_stay_unresolved() {
        assert_eq!(resolve_incentive_repo("not-a-slug"), None);
        assert_eq!(
            resolve_incentive_repo("o/r"),
            Some("o/r".to_owned()),
            "a valid override wins without any service call"
        );
    }

    #[test]
    fn python_int_spellings_parse_like_int() {
        assert_eq!(parse_python_int(" 20 "), Some(20));
        assert_eq!(parse_python_int("-7"), Some(-7));
        assert_eq!(parse_python_int("1_0"), Some(10));
        assert_eq!(parse_python_int("1__0"), None);
        assert_eq!(parse_python_int("x"), None);
        assert_eq!(parse_python_int("1.5"), None);
    }

    #[test]
    fn python_float_spellings_parse_like_float() {
        assert_eq!(parse_python_float("0.50"), Some(0.5));
        assert_eq!(parse_python_float(" 1e-3 "), Some(0.001));
        assert_eq!(parse_python_float("1_0.5"), Some(10.5));
        assert_eq!(parse_python_float("_1"), None);
        assert_eq!(parse_python_float(""), None);
        assert_eq!(parse_python_float("nope"), None);
        assert!(parse_python_float("inf").is_some_and(f64::is_infinite));
    }

    #[test]
    fn era_date_shape_requires_ascii_yyyy_mm_dd() {
        assert!(date_shape_matches("2026-06-26"));
        assert!(!date_shape_matches("2026-6-26"));
        assert!(!date_shape_matches("2026-06-26T00:00:00"));
    }

    #[test]
    fn boundary_timestamps_render_like_python_isoformat() {
        let whole = Utc.with_ymd_and_hms(2026, 6, 26, 0, 0, 0).unwrap();
        assert_eq!(python_isoformat_z(whole), "2026-06-26T00:00:00Z");
        let fractional = whole + chrono::Duration::microseconds(250_000);
        assert_eq!(
            python_isoformat_z(fractional),
            "2026-06-26T00:00:00.250000Z"
        );
    }

    #[test]
    fn issue_url_repo_extraction_matches_the_python_regex() {
        assert_eq!(
            repo_from_issue_url("https://github.com/example/larch/issues/5461"),
            Some("example/larch".to_owned())
        );
        assert_eq!(
            repo_from_issue_url("https://GitHub.com/Example/Larch/Issues/5461"),
            Some("Example/Larch".to_owned())
        );
        assert_eq!(
            repo_from_issue_url("https://github.com/example/larch/pull/1"),
            None
        );
    }

    #[test]
    fn targeted_details_reach_the_realized_outcome_corpus() {
        let bulk = vec![
            AnalysisIssue::from_value(&json!({"number": 1, "title": "bulk one", "state": "OPEN"}))
                .expect("bulk issue"),
        ];
        let mut details: BTreeMap<u64, AnalysisIssue> = BTreeMap::new();
        let _ = details.insert(
            1,
            AnalysisIssue::from_value(&json!({"number": 1, "state": "CLOSED"}))
                .expect("targeted detail"),
        );
        let _ = details.insert(
            7,
            AnalysisIssue::from_value(&json!({"number": 7, "title": "detail only"}))
                .expect("detail-only issue"),
        );

        let merged = merge_filed_details(&bulk, &details);

        let numbers: Vec<u64> = merged.iter().map(|issue| issue.summary.number).collect();
        assert_eq!(
            numbers,
            [1, 7],
            "a detail-only filed issue joins the corpus"
        );
        assert_eq!(
            merged[0].summary.title, "bulk one",
            "a field the targeted response omitted keeps the bulk value"
        );
        assert_eq!(
            merged[0].summary.state,
            larch_core::IssueLifecycle::Closed,
            "the targeted response wins for the fields it supplied"
        );
    }

    #[test]
    fn out_paths_normalize_like_pathlib() {
        assert_eq!(python_path_display("/a//b/./c/"), "/a/b/c");
        assert_eq!(python_path_display("./x"), "x");
        assert_eq!(python_path_display("/"), "/");
    }
}
