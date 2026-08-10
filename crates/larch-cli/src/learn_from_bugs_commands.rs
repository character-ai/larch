//! Rust owner for `/learn-from-bugs` preparation, zones, and durable state.
//!
//! GitHub issue text and proposal JSONL are untrusted data.  This module keeps
//! the migration's artifact grammar local: it validates values before using
//! them as paths, never executes fetched text, and writes the mutable marker
//! through a locked, symlink-safe atomic replacement.

use std::{
    collections::{BTreeMap, BTreeSet, HashSet},
    env,
    ffi::OsString,
    fs::{self, OpenOptions},
    path::{Path, PathBuf},
    process::ExitCode,
    sync::LazyLock,
};

#[cfg(unix)]
use std::os::unix::fs::{MetadataExt as _, OpenOptionsExt as _, PermissionsExt as _};

#[cfg(unix)]
use nix::fcntl::{Flock, FlockArg};

use chrono::{DateTime, NaiveDate};
use larch_adapters::git::GixRepository;
use larch_adapters::{ensure_directory_chain, path_under};
#[cfg(test)]
use larch_core::DONE_PREFIX as DONE_TITLE_PREFIX;
use larch_core::{
    BUG_PREFIX, FILE_CONFLICT_DEFAULT_CLUSTER_CAP, FILE_CONFLICT_DEFAULT_GLOBAL_CAP,
    GUIDELINE_HEADING_RE, GitHubIssue, GitHubIssueSearch, GitHubIssueState, GitHubService,
    INVARIANT_HEADING_RE, bug_title_match, parse_issue_input, plan_file_conflict_deps,
    private_atomic_write, render_deps_tsv,
};
use regex::Regex;
use serde::Serialize;
use serde_json::{Map, Value};
use sha2::{Digest as _, Sha256};

use crate::{
    argparse_compat::{
        ParsedCommandLine, join_arguments, looks_like_option, parse_with_flags, usage_error,
    },
    github_repository_resolution::{
        RemoteRepoResult, ambient_repo, repository_ref, resolve_remote_repo,
    },
    github_service::with_github_service,
};

const PREPARE_PROGRAM: &str = "learn-from-bugs prepare";
const PREPARE_USAGE: &str = "usage: learn-from-bugs prepare [-h] [--search SEARCH] [--state STATE]\n                               [--limit LIMIT] [--repo REPO] --out OUT\n                               [--root ROOT] [--full]";
const PREPARE_HELP: &str = "usage: learn-from-bugs prepare [-h] [--search SEARCH] [--state STATE]\n                               [--limit LIMIT] [--repo REPO] --out OUT\n                               [--root ROOT] [--full]\n\noptions:\n  -h, --help       show this help message and exit\n  --search SEARCH\n  --state STATE\n  --limit LIMIT\n  --repo REPO\n  --out OUT\n  --root ROOT\n  --full\n";
const COVERAGE_PROGRAM: &str = "learn-from-bugs coverage-index";
const COVERAGE_USAGE: &str = "usage: learn-from-bugs coverage-index [-h] [--root ROOT] [--out OUT]";
const COVERAGE_HELP: &str = "usage: learn-from-bugs coverage-index [-h] [--root ROOT] [--out OUT]\n\noptions:\n  -h, --help   show this help message and exit\n  --root ROOT\n  --out OUT\n";
const READ_STATE_PROGRAM: &str = "learn-from-bugs read-state";
const READ_STATE_USAGE: &str = "usage: learn-from-bugs read-state [-h] --root ROOT";
const READ_STATE_HELP: &str = "usage: learn-from-bugs read-state [-h] --root ROOT\n\noptions:\n  -h, --help   show this help message and exit\n  --root ROOT\n";
const WRITE_STATE_PROGRAM: &str = "learn-from-bugs write-state";
const WRITE_STATE_USAGE: &str = "usage: learn-from-bugs write-state [-h] --root ROOT --repo REPO --search\n                                   SEARCH --state STATE --selected-count\n                                   SELECTED_COUNT\n                                   --highest-closed-issue-number-scanned\n                                   HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED\n                                   --run-date RUN_DATE --scan-started-at\n                                   SCAN_STARTED_AT\n                                   [--proposals-file PROPOSALS_FILE]\n                                   [--base-proposals-file BASE_PROPOSALS_FILE]";
const WRITE_STATE_HELP: &str = "usage: learn-from-bugs write-state [-h] --root ROOT --repo REPO --search\n                                   SEARCH --state STATE --selected-count\n                                   SELECTED_COUNT\n                                   --highest-closed-issue-number-scanned\n                                   HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED\n                                   --run-date RUN_DATE --scan-started-at\n                                   SCAN_STARTED_AT\n                                   [--proposals-file PROPOSALS_FILE]\n                                   [--base-proposals-file BASE_PROPOSALS_FILE]\n\noptions:\n  -h, --help            show this help message and exit\n  --root ROOT\n  --repo REPO\n  --search SEARCH\n  --state STATE\n  --selected-count SELECTED_COUNT\n  --highest-closed-issue-number-scanned HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED\n  --run-date RUN_DATE\n  --scan-started-at SCAN_STARTED_AT\n  --proposals-file PROPOSALS_FILE\n  --base-proposals-file BASE_PROPOSALS_FILE\n";
const ZONES_PROGRAM: &str = "learn-from-bugs resolve-zones";
const ZONES_USAGE: &str = "usage: learn-from-bugs resolve-zones [-h] --zones ZONES\n                                     [--has-explicit-search]\n                                     [--has-verbal-search]";
const ZONES_HELP: &str = "usage: learn-from-bugs resolve-zones [-h] --zones ZONES\n                                     [--has-explicit-search]\n                                     [--has-verbal-search]\n\noptions:\n  -h, --help            show this help message and exit\n  --zones ZONES\n  --has-explicit-search\n                        Set when --search was also present; forces a multi-\n                        source rejection.\n  --has-verbal-search   Set when verbal search text was also present; forces a\n                        multi-source rejection.\n";
const CHECK_PROPOSALS_PROGRAM: &str = "learn-from-bugs check-proposals";
const CHECK_PROPOSALS_USAGE: &str = "usage: learn-from-bugs check-proposals [-h] --root ROOT --repo REPO\n                                             --proposals-out PROPOSALS_OUT\n                                             --adoption-out ADOPTION_OUT\n                                             [--base-proposals-out BASE_PROPOSALS_OUT]";
const CHECK_PROPOSALS_HELP: &str = "usage: learn-from-bugs check-proposals [-h] --root ROOT --repo REPO\n                                             --proposals-out PROPOSALS_OUT\n                                             --adoption-out ADOPTION_OUT\n                                             [--base-proposals-out BASE_PROPOSALS_OUT]\n\noptions:\n  -h, --help            show this help message and exit\n  --root ROOT\n  --repo REPO\n  --proposals-out PROPOSALS_OUT\n  --adoption-out ADOPTION_OUT\n  --base-proposals-out BASE_PROPOSALS_OUT\n";
const VERIFY_ORIGIN_PROGRAM: &str = "learn-from-bugs verify-origin";
const VERIFY_ORIGIN_USAGE: &str =
    "usage: learn-from-bugs verify-origin [-h] --root ROOT --repo REPO";
const VERIFY_ORIGIN_HELP: &str = "usage: learn-from-bugs verify-origin [-h] --root ROOT --repo REPO\n\noptions:\n  -h, --help   show this help message and exit\n  --root ROOT\n  --repo REPO\n";
const VALIDATE_REPORT_PROGRAM: &str = "learn-from-bugs validate-report";
const VALIDATE_REPORT_USAGE: &str =
    "usage: learn-from-bugs validate-report [-h] --report REPORT --headline HEADLINE";
const VALIDATE_REPORT_HELP: &str = "usage: learn-from-bugs validate-report [-h] --report REPORT --headline HEADLINE\n\noptions:\n  -h, --help   show this help message and exit\n  --report REPORT\n  --headline HEADLINE\n";
const STATE_PUBLISH_PROGRAM: &str = "learn-from-bugs state-publish";
const STATE_PUBLISH_USAGE: &str = "usage: learn-from-bugs state-publish [-h] --root ROOT --repo REPO --run-dir\n                                     RUN_DIR --search SEARCH --state STATE\n                                     --selected-count SELECTED_COUNT\n                                     --highest-closed-issue-number-scanned\n                                     HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED --run-date\n                                     RUN_DATE --scan-started-at SCAN_STARTED_AT\n                                     --proposals-file PROPOSALS_FILE\n                                     [--base-proposals-file BASE_PROPOSALS_FILE]";
const STATE_PUBLISH_HELP: &str = "usage: learn-from-bugs state-publish [-h] --root ROOT --repo REPO --run-dir\n                                     RUN_DIR --search SEARCH --state STATE\n                                     --selected-count SELECTED_COUNT\n                                     --highest-closed-issue-number-scanned\n                                     HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED --run-date\n                                     RUN_DATE --scan-started-at SCAN_STARTED_AT\n                                     --proposals-file PROPOSALS_FILE\n                                     [--base-proposals-file BASE_PROPOSALS_FILE]\n\noptions:\n  -h, --help            show this help message and exit\n  --root ROOT\n  --repo REPO\n  --run-dir RUN_DIR\n  --search SEARCH\n  --state STATE\n  --selected-count SELECTED_COUNT\n  --highest-closed-issue-number-scanned HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED\n  --run-date RUN_DATE\n  --scan-started-at SCAN_STARTED_AT\n  --proposals-file PROPOSALS_FILE\n  --base-proposals-file BASE_PROPOSALS_FILE\n";
const FILING_DEPS_PROGRAM: &str = "learn-from-bugs filing-deps";
const FILING_DEPS_USAGE: &str = "usage: learn-from-bugs filing-deps [-h] --input-file INPUT_FILE\n                                    --proposal-map-file PROPOSAL_MAP_FILE\n                                    --proposal-deps-file PROPOSAL_DEPS_FILE\n                                    --output OUTPUT";
const FILING_DEPS_HELP: &str = "usage: learn-from-bugs filing-deps [-h] --input-file INPUT_FILE\n                                    --proposal-map-file PROPOSAL_MAP_FILE\n                                    --proposal-deps-file PROPOSAL_DEPS_FILE\n                                    --output OUTPUT\n\noptions:\n  -h, --help            show this help message and exit\n  --input-file INPUT_FILE\n  --proposal-map-file PROPOSAL_MAP_FILE\n  --proposal-deps-file PROPOSAL_DEPS_FILE\n  --output OUTPUT\n";

const DEFAULT_SEARCH_SUFFIX: &str = " in:title";
const DEFAULT_STATE: &str = "closed";
const DEFAULT_LIMIT: i64 = 50;
const STATE_RELPATH: &str = "learn-from-bugs/state.json";
const DIGEST_CHUNK_CHAR_LIMIT: usize = 38_000;
const TITLE_ONLY_PREFIX_MAX: usize = 40;
const FILING_DEPS_MAX_BYTES: u64 = 64 * 1024;
const PROSE_ONLY_MARKER: &str = "prose-only prevention: unlikely to stick";

static PLAN_MARKER: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^[ \t]*<!--[ \t]+larch:plan:start[ \t]+-->[ \t]*\r?$")
        .expect("plan marker regex compiles")
});
static PLAN_HEADING: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?im)^##\s+Plan\s*\r?$").expect("plan heading regex compiles"));
static APPROACH_HEADING: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?im)^##\s+Approach\s*\r?$").expect("approach heading regex compiles")
});
static PLAN_ACTION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?im)^###\s+(?:NEW|UPDATED|REWRITTEN|MAY_UPDATE):")
        .expect("plan action regex compiles")
});
static HEADING: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^#{2,4}\s+(.+?)\s*$").expect("heading regex compiles"));
static BOLD_HEADING: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)^\*\*(Impact|Classification|Repro)\*\*(?:[ \t]*:[ \t]*|[ \t]*)(.*)$")
        .expect("bold heading regex compiles")
});
static CLASSIFICATION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)^\s*([A-Z][A-Z0-9_]*)(?:\s*\([^\n)]*\))?\s*,\s*owning\s+surface\s+([A-Z][A-Z0-9_]*)\b")
        .expect("classification regex compiles")
});
static HARNESS_CLASS: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\broot[- ]cause\s+class\s*(?::\s*)?`?([A-Z][A-Z0-9_]*)`?\b")
        .expect("harness class regex compiles")
});
static HARNESS_SURFACE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\bowning\s+surface\s*(?::\s*)?`?([A-Z][A-Z0-9_]*)`?\b")
        .expect("harness surface regex compiles")
});
static FENCE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^(`{3,}|~{3,})(.*)$").expect("fence regex compiles"));
static DONE_PREFIX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^\[DONE\]\s*").expect("done prefix regex compiles"));
static NEWLINES: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\n{2,}").expect("newline regex"));
static BARE_REGRESSION: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)\bregression\b").expect("regression regex compiles"));
static ORIGIN_REFS: LazyLock<Vec<Regex>> = LazyLock::new(|| {
    [
        r"(?i)introduced\s+by\s+PR\s*#(\d+)",
        r"(?i)introduced\s+by\s+#(\d+)",
        r"(?i)introduced\s+in\s+#(\d+)",
        r"(?i)incomplete\s+fix\s+of\s+#(\d+)",
        r"(?i)persists\s+after\s+#(\d+)",
        r"(?i)residual\s+of\s+#(\d+)",
    ]
    .into_iter()
    .map(|pattern| Regex::new(pattern).expect("origin reference regex compiles"))
    .collect()
});
static UNMARKED_GUIDELINE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^#{2,3}\s+(.+?)(?:\s+#+)?\s*$").expect("fallback heading regex"));
static PROPOSAL_ID: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[a-z0-9]+(?:-[a-z0-9]+)*$").expect("proposal id regex"));
static FIX_TOKEN: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[a-z0-9]+(?:-[a-z0-9]+)*$").expect("fix token regex"));
static CHECK_SYMBOL: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z_][A-Za-z0-9_]*$").expect("check symbol regex"));
static TEST_NAME: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^test_[A-Za-z0-9_]+$").expect("test name regex"));
static SECTION2_HEADING: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?im)^#{1,6}\s+.*root-cause clusters.*$|^\d+\.\s+\*\*Root-cause clusters\.\*\*")
        .expect("section two heading regex")
});
static NEXT_TOP_SECTION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?im)^#{1,3}\s+\d*\.?\s*(?:\*\*)?(?:Already covered|Proposed mechanical|Proposed architectural|Proposed guideline|Proposed regression|Issues to file|Scope and cost)")
        .expect("next report heading regex")
});
static MECHANICAL_ALTERNATIVE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(?:lint|hook|invariant(?:[-\s]?test)?)\b|no mechanical alternative")
        .expect("mechanical alternative regex")
});

/// Dispatch `learn-from-bugs prepare`.
#[must_use]
#[allow(clippy::too_many_lines)] // Ordered artifacts and KV output share one compatibility transaction.
pub fn prepare(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &[
        "--search", "--state", "--limit", "--repo", "--out", "--root",
    ];
    const FLAGS: &[&str] = &["--full"];
    if let Some(code) = help_explicit_argument(arguments, false, PREPARE_USAGE, PREPARE_PROGRAM) {
        return code;
    }
    if help_requested(arguments, false) {
        print!("{PREPARE_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = match strict_parse(
        arguments,
        OPTIONS,
        FLAGS,
        PREPARE_USAGE,
        PREPARE_PROGRAM,
        false,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let integer_values =
        match parse_integer_options(&parsed, &["--limit"], PREPARE_USAGE, PREPARE_PROGRAM) {
            Ok(values) => values,
            Err(code) => return code,
        };
    let limit = integer_values
        .get("--limit")
        .copied()
        .unwrap_or(DEFAULT_LIMIT);
    let out = match required_option(&parsed, "--out", PREPARE_USAGE, PREPARE_PROGRAM) {
        Ok(value) => path_from_argument(&value),
        Err(code) => return code,
    };
    if let Some(error) = strict_unrecognized(arguments, OPTIONS, FLAGS) {
        return usage_refusal(PREPARE_USAGE, PREPARE_PROGRAM, &error);
    }
    let root = parsed.value("--root").map_or_else(
        || PathBuf::from("."),
        |value| path_from_argument(&value.to_string_lossy()),
    );
    let root = match canonical_root(&root) {
        Ok(root) => root,
        Err(error) => return command_error(PREPARE_PROGRAM, &error),
    };
    let search = option_text(&parsed, "--search")
        .unwrap_or_else(|| format!("{BUG_PREFIX}{DEFAULT_SEARCH_SUFFIX}"));
    let state = option_text(&parsed, "--state").unwrap_or_else(|| DEFAULT_STATE.to_owned());
    let explicit_search = arguments.iter().any(|argument| {
        argument.to_string_lossy().as_ref() == "--search"
            || argument.to_string_lossy().starts_with("--search=")
    });
    let explicit_repo = option_text(&parsed, "--repo").unwrap_or_default();
    let repo = match resolve_repo(&explicit_repo) {
        Ok(repo) => repo,
        Err(error) => return command_error(PREPARE_PROGRAM, &error),
    };
    let marker = match state_path(&root) {
        Ok(path) => path,
        Err(error) => return command_error(PREPARE_PROGRAM, &error),
    };
    let marker_exists = fs::symlink_metadata(&marker).is_ok();
    let prior = match read_state_file(&marker) {
        Ok(state) => state,
        Err(_) if marker_exists => {
            return command_error(
                PREPARE_PROGRAM,
                "existing state marker is invalid or unsupported",
            );
        }
        Err(error) => return command_error(PREPARE_PROGRAM, &error),
    };
    if marker_exists && prior.is_none() {
        return command_error(
            PREPARE_PROGRAM,
            "existing state marker is invalid or unsupported",
        );
    }
    if let Some(prior) = &prior
        && prior.repo != repo
    {
        return command_error(
            PREPARE_PROGRAM,
            "--repo does not match the durable learn-from-bugs state repository",
        );
    }
    let scan_started_at = chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string();
    let raw_issues = match fetch_issues(&repo, &search, &state, limit) {
        Ok(issues) => issues,
        Err(error) => {
            return command_error(PREPARE_PROGRAM, &format!("gh issue list failed: {error}"));
        }
    };
    let highest = raw_issues
        .iter()
        .map(|issue| issue.number)
        .max()
        .unwrap_or(0);
    let mut issues: Vec<_> = raw_issues
        .iter()
        .filter(|issue| !issue.is_pull_request && bug_title_match(&issue.title))
        .cloned()
        .collect();
    let filtered = raw_issues.len().saturating_sub(issues.len());
    let prior_highest = prior
        .as_ref()
        .map_or(0, |value| value.highest.max(0).cast_unsigned());
    let previously_scanned = if prior.is_some() {
        issues
            .iter()
            .filter(|issue| issue.number <= prior_highest)
            .count()
    } else {
        0
    };
    let incremental = prior.is_some() && !parsed.flag("--full") && !explicit_search;
    if incremental {
        issues.retain(|issue| issue.number > prior_highest);
    }
    let digests: Vec<_> = issues.iter().map(build_digest).collect();
    let out = match create_out_dir(&out) {
        Ok(path) => path,
        Err(error) => return command_error(PREPARE_PROGRAM, &error),
    };
    let (digest_paths, digest_chars) = match write_digest_chunks(&out, &digests) {
        Ok(value) => value,
        Err(error) => return command_error(PREPARE_PROGRAM, &error),
    };
    let coverage = coverage_index(&root);
    let coverage_path = out.join("coverage-index.json");
    let mut coverage_text = match serde_json::to_string_pretty(&coverage) {
        Ok(text) => ascii_json(&text),
        Err(error) => return command_error(PREPARE_PROGRAM, &error.to_string()),
    };
    coverage_text.push('\n');
    if let Err(error) = plain_atomic_write(&coverage_path, &coverage_text) {
        return command_error(PREPARE_PROGRAM, &error);
    }
    let headline = render_origin_headline(&digests);
    let headline_path = out.join("origin-headline.md");
    if let Err(error) = plain_atomic_write(&headline_path, &headline) {
        return command_error(PREPARE_PROGRAM, &error);
    }
    let structured = digests.iter().filter(|digest| digest.structured).count();
    println!("RUN_DIR={}", out.display());
    for path in &digest_paths {
        println!("DIGEST_PATH={}", path.display());
    }
    println!("COVERAGE_INDEX_PATH={}", coverage_path.display());
    println!("ORIGIN_HEADLINE_PATH={}", headline_path.display());
    println!("REPO={repo}");
    println!("SEARCH={search}");
    println!("STATE={state}");
    println!("SCAN_STARTED_AT={scan_started_at}");
    println!("HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED={highest}");
    println!("ISSUES_SELECTED={}", digests.len());
    println!("ISSUES_PREVIOUSLY_SCANNED={previously_scanned}");
    println!("INCREMENTAL={incremental}");
    println!("ISSUES_FILTERED_NON_BUG={filtered}");
    println!("STRUCTURED={structured}");
    println!("FREEFORM_OR_TITLE_ONLY={}", digests.len() - structured);
    println!("DIGEST_CHARS={digest_chars}");
    println!("DIGEST_TOKENS_EST={}", digest_chars.div_ceil(2));
    println!("GUIDELINES_INDEXED={}", coverage.guidelines.len());
    println!("GUIDELINES_INDEX_STATUS={}", coverage.guidelines_status);
    println!("INVARIANTS_INDEXED={}", coverage.invariants.len());
    println!("PYTHON_LINTS_INDEXED={}", coverage.python_lints.len());
    println!("SCRIPT_LINTS_INDEXED={}", coverage.script_lints.len());
    ExitCode::SUCCESS
}

/// Dispatch `learn-from-bugs coverage-index`.
#[must_use]
pub fn coverage_index_command(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--root", "--out"];
    if let Some(code) = help_explicit_argument(arguments, true, COVERAGE_USAGE, COVERAGE_PROGRAM) {
        return code;
    }
    if help_requested(arguments, true) {
        print!("{COVERAGE_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = match strict_parse(
        arguments,
        OPTIONS,
        &[],
        COVERAGE_USAGE,
        COVERAGE_PROGRAM,
        true,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let root = parsed.value("--root").map_or_else(
        || PathBuf::from("."),
        |value| path_from_argument(&value.to_string_lossy()),
    );
    let coverage = coverage_index(&root);
    let payload = match serde_json::to_string_pretty(&coverage) {
        Ok(value) => ascii_json(&value),
        Err(error) => return command_error(COVERAGE_PROGRAM, &error.to_string()),
    };
    if let Some(out) = option_text(&parsed, "--out").filter(|value| !value.is_empty())
        && let Err(error) = fs::write(out, format!("{payload}\n"))
    {
        return command_error(COVERAGE_PROGRAM, &error.to_string());
    }
    println!("{payload}");
    ExitCode::SUCCESS
}

/// Dispatch `learn-from-bugs resolve-zones`.
#[must_use]
pub fn resolve_zones(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--zones"];
    const FLAGS: &[&str] = &["--has-explicit-search", "--has-verbal-search"];
    if let Some(code) = help_explicit_argument(arguments, false, ZONES_USAGE, ZONES_PROGRAM) {
        return code;
    }
    if help_requested(arguments, false) {
        print!("{ZONES_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = match strict_parse(arguments, OPTIONS, FLAGS, ZONES_USAGE, ZONES_PROGRAM, false) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let zones = match required_option(&parsed, "--zones", ZONES_USAGE, ZONES_PROGRAM) {
        Ok(value) => value,
        Err(code) => return code,
    };
    if let Some(error) = strict_unrecognized(arguments, OPTIONS, FLAGS) {
        return usage_refusal(ZONES_USAGE, ZONES_PROGRAM, &error);
    }
    let query = match resolve_zone_search(
        &zones,
        parsed.flag("--has-explicit-search"),
        parsed.flag("--has-verbal-search"),
    ) {
        Ok(query) => query,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::from(2);
        }
    };
    println!("RESOLVED_SEARCH={query}");
    ExitCode::SUCCESS
}

/// Dispatch `learn-from-bugs read-state`.
#[must_use]
pub fn read_state(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--root"];
    if let Some(code) =
        help_explicit_argument(arguments, false, READ_STATE_USAGE, READ_STATE_PROGRAM)
    {
        return code;
    }
    if help_requested(arguments, false) {
        print!("{READ_STATE_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = match strict_parse(
        arguments,
        OPTIONS,
        &[],
        READ_STATE_USAGE,
        READ_STATE_PROGRAM,
        false,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let root = match required_option(&parsed, "--root", READ_STATE_USAGE, READ_STATE_PROGRAM) {
        Ok(root) => path_from_argument(&root),
        Err(code) => return code,
    };
    if let Some(error) = strict_unrecognized(arguments, OPTIONS, &[]) {
        return usage_refusal(READ_STATE_USAGE, READ_STATE_PROGRAM, &error);
    }
    let path = match canonical_root(&root).and_then(|root| state_path(&root)) {
        Ok(path) => path,
        Err(error) => return command_error(READ_STATE_PROGRAM, &error),
    };
    if let Ok(Some(state)) = read_state_file(&path) {
        println!("LEARN_FROM_BUGS_STATE_FOUND=true");
        println!("STATE_RELPATH={STATE_RELPATH}");
        println!("STATE_PATH={}", path.display());
        println!("RUN_DATE={}", state.run_date);
        println!("REPO={}", state.repo);
        println!("SEARCH={}", state.search);
        println!("STATE={}", state.state);
        println!("SELECTED_COUNT={}", state.selected_count);
        println!("HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED={}", state.highest);
        println!("SCHEMA_VERSION=2");
        println!("PROPOSAL_COUNT={}", state.proposals.len());
        if let Some(scan_started_at) = state.scan_started_at {
            println!("SCAN_STARTED_AT={scan_started_at}");
        }
    } else {
        println!("LEARN_FROM_BUGS_STATE_FOUND=false");
        println!("STATE_RELPATH={STATE_RELPATH}");
        println!("STATE_PATH={}", path.display());
    }
    ExitCode::SUCCESS
}

/// Dispatch `learn-from-bugs write-state`.
#[must_use]
#[allow(clippy::too_many_lines)] // Required-option parsing and exact output form one compatibility boundary.
pub fn write_state(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &[
        "--root",
        "--repo",
        "--search",
        "--state",
        "--selected-count",
        "--highest-closed-issue-number-scanned",
        "--run-date",
        "--scan-started-at",
        "--proposals-file",
        "--base-proposals-file",
    ];
    if let Some(code) =
        help_explicit_argument(arguments, false, WRITE_STATE_USAGE, WRITE_STATE_PROGRAM)
    {
        return code;
    }
    if help_requested(arguments, false) {
        print!("{WRITE_STATE_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = match strict_parse(
        arguments,
        OPTIONS,
        &[],
        WRITE_STATE_USAGE,
        WRITE_STATE_PROGRAM,
        false,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let integer_values = match parse_integer_options(
        &parsed,
        &["--selected-count", "--highest-closed-issue-number-scanned"],
        WRITE_STATE_USAGE,
        WRITE_STATE_PROGRAM,
    ) {
        Ok(values) => values,
        Err(code) => return code,
    };
    let required = [
        "--root",
        "--repo",
        "--search",
        "--state",
        "--selected-count",
        "--highest-closed-issue-number-scanned",
        "--run-date",
        "--scan-started-at",
    ];
    let mut values = BTreeMap::new();
    for option in required {
        match required_option(&parsed, option, WRITE_STATE_USAGE, WRITE_STATE_PROGRAM) {
            Ok(value) => {
                values.insert(option, value);
            }
            Err(code) => return code,
        }
    }
    if let Some(error) = strict_unrecognized(arguments, OPTIONS, &[]) {
        return usage_refusal(WRITE_STATE_USAGE, WRITE_STATE_PROGRAM, &error);
    }
    let selected_count = integer_values["--selected-count"];
    let highest = integer_values["--highest-closed-issue-number-scanned"];
    let root = match canonical_root(&path_from_argument(&values["--root"])) {
        Ok(root) => root,
        Err(error) => return command_error(WRITE_STATE_PROGRAM, &error),
    };
    let path = match state_path(&root) {
        Ok(path) => path,
        Err(error) => return command_error(WRITE_STATE_PROGRAM, &error),
    };
    let snapshot = match state_snapshot(&path) {
        Ok(snapshot) => snapshot,
        Err(error) => return command_error(WRITE_STATE_PROGRAM, &error),
    };
    let proposals_file = option_text(&parsed, "--proposals-file").filter(|value| !value.is_empty());
    let base_file = option_text(&parsed, "--base-proposals-file").filter(|value| !value.is_empty());
    let result = write_state_locked(
        &path,
        StateRecord {
            run_date: values["--run-date"].clone(),
            repo: values["--repo"].clone(),
            search: values["--search"].clone(),
            state: values["--state"].clone(),
            selected_count,
            highest,
            scan_started_at: Some(values["--scan-started-at"].clone()),
            proposals: Vec::new(),
        },
        proposals_file.as_deref().map(Path::new),
        base_file.as_deref().map(Path::new),
        &root,
        &snapshot,
    );
    let (state, digest) = match result {
        Ok(value) => value,
        Err(error) => return command_error(WRITE_STATE_PROGRAM, &error),
    };
    println!("STATE_RELPATH={STATE_RELPATH}");
    println!("STATE_PATH={}", path.display());
    println!("RUN_DATE={}", state.run_date);
    println!(
        "SCAN_STARTED_AT={}",
        state.scan_started_at.unwrap_or_default()
    );
    println!("HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED={}", state.highest);
    println!("SCHEMA_VERSION=2");
    println!("PROPOSAL_COUNT={}", state.proposals.len());
    println!("STATE_DIGEST={digest}");
    ExitCode::SUCCESS
}

/// Dispatch `learn-from-bugs check-proposals`.
#[must_use]
#[allow(clippy::too_many_lines)] // The durable-state and GitHub checks form one compatibility boundary.
pub fn check_proposals(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &[
        "--root",
        "--repo",
        "--proposals-out",
        "--adoption-out",
        "--base-proposals-out",
    ];
    if let Some(code) = help_explicit_argument(
        arguments,
        false,
        CHECK_PROPOSALS_USAGE,
        CHECK_PROPOSALS_PROGRAM,
    ) {
        return code;
    }
    if help_requested(arguments, false) {
        print!("{CHECK_PROPOSALS_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = match strict_parse(
        arguments,
        OPTIONS,
        &[],
        CHECK_PROPOSALS_USAGE,
        CHECK_PROPOSALS_PROGRAM,
        false,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let root = match required_option(
        &parsed,
        "--root",
        CHECK_PROPOSALS_USAGE,
        CHECK_PROPOSALS_PROGRAM,
    ) {
        Ok(value) => path_from_argument(&value),
        Err(code) => return code,
    };
    let repo = match required_option(
        &parsed,
        "--repo",
        CHECK_PROPOSALS_USAGE,
        CHECK_PROPOSALS_PROGRAM,
    ) {
        Ok(value) => value,
        Err(code) => return code,
    };
    let proposals_out = match required_option(
        &parsed,
        "--proposals-out",
        CHECK_PROPOSALS_USAGE,
        CHECK_PROPOSALS_PROGRAM,
    ) {
        Ok(value) => path_from_argument(&value),
        Err(code) => return code,
    };
    let adoption_out = match required_option(
        &parsed,
        "--adoption-out",
        CHECK_PROPOSALS_USAGE,
        CHECK_PROPOSALS_PROGRAM,
    ) {
        Ok(value) => path_from_argument(&value),
        Err(code) => return code,
    };
    if let Some(error) = strict_unrecognized(arguments, OPTIONS, &[]) {
        return usage_refusal(CHECK_PROPOSALS_USAGE, CHECK_PROPOSALS_PROGRAM, &error);
    }
    let root = match canonical_root(&root) {
        Ok(root) => root,
        Err(error) => return command_error(CHECK_PROPOSALS_PROGRAM, &error),
    };
    let state_path = match state_path(&root) {
        Ok(path) => path,
        Err(error) => return command_error(CHECK_PROPOSALS_PROGRAM, &error),
    };
    let marker_exists = fs::symlink_metadata(&state_path).is_ok();
    let state = match read_state_file(&state_path) {
        Ok(state) => state,
        Err(_) if marker_exists => {
            return command_error(
                CHECK_PROPOSALS_PROGRAM,
                "existing state marker is invalid or unsupported",
            );
        }
        Err(error) => return command_error(CHECK_PROPOSALS_PROGRAM, &error),
    };
    if marker_exists && state.is_none() {
        return command_error(
            CHECK_PROPOSALS_PROGRAM,
            "existing state marker is invalid or unsupported",
        );
    }
    if state.as_ref().is_some_and(|state| state.repo != repo) {
        return command_error(
            CHECK_PROPOSALS_PROGRAM,
            "--repo does not match the durable learn-from-bugs state repository",
        );
    }
    let proposals = state.map_or_else(Vec::new, |state| state.proposals);
    let checked = match refresh_proposals(&proposals, &root, &repo) {
        Ok(checked) => checked,
        Err(error) => return command_error(CHECK_PROPOSALS_PROGRAM, &error),
    };
    let proposals_out = match output_path(&proposals_out) {
        Ok(path) => path,
        Err(error) => return command_error(CHECK_PROPOSALS_PROGRAM, &error),
    };
    let adoption_out = match output_path(&adoption_out) {
        Ok(path) => path,
        Err(error) => return command_error(CHECK_PROPOSALS_PROGRAM, &error),
    };
    let checked_text = checked
        .iter()
        .map(checked_proposal_line)
        .collect::<String>();
    if let Err(error) = plain_atomic_write(&proposals_out, &checked_text) {
        return command_error(CHECK_PROPOSALS_PROGRAM, &error);
    }
    if let Err(error) = plain_atomic_write(&adoption_out, &render_adoption_summary(&checked)) {
        return command_error(CHECK_PROPOSALS_PROGRAM, &error);
    }
    println!("PROPOSALS_COUNT={}", checked.len());
    println!(
        "PROPOSALS_ADOPTED={}",
        checked
            .iter()
            .filter(|proposal| proposal.proposal.status == "adopted")
            .count()
    );
    println!(
        "PROPOSALS_PENDING={}",
        checked
            .iter()
            .filter(|proposal| proposal.proposal.status == "pending")
            .count()
    );
    println!(
        "PROPOSALS_ORPHANED={}",
        checked
            .iter()
            .filter(|proposal| proposal.proposal.status == "orphaned")
            .count()
    );
    println!("CHECKED_PROPOSALS_PATH={}", proposals_out.display());
    println!("ADOPTION_SUMMARY_PATH={}", adoption_out.display());
    if let Some(base_out) =
        option_text(&parsed, "--base-proposals-out").filter(|value| !value.is_empty())
    {
        let base_out = match output_path(&path_from_argument(&base_out)) {
            Ok(path) => path,
            Err(error) => return command_error(CHECK_PROPOSALS_PROGRAM, &error),
        };
        let base_text = proposals.iter().map(proposal_line).collect::<String>();
        if let Err(error) = plain_atomic_write(&base_out, &base_text) {
            return command_error(CHECK_PROPOSALS_PROGRAM, &error);
        }
        println!("BASE_PROPOSALS_PATH={}", base_out.display());
    }
    ExitCode::SUCCESS
}

/// Dispatch `learn-from-bugs verify-origin`.
#[must_use]
pub fn verify_origin(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--root", "--repo"];
    if let Some(code) =
        help_explicit_argument(arguments, false, VERIFY_ORIGIN_USAGE, VERIFY_ORIGIN_PROGRAM)
    {
        return code;
    }
    if help_requested(arguments, false) {
        print!("{VERIFY_ORIGIN_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = match strict_parse(
        arguments,
        OPTIONS,
        &[],
        VERIFY_ORIGIN_USAGE,
        VERIFY_ORIGIN_PROGRAM,
        false,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let root = match required_option(
        &parsed,
        "--root",
        VERIFY_ORIGIN_USAGE,
        VERIFY_ORIGIN_PROGRAM,
    ) {
        Ok(value) => path_from_argument(&value),
        Err(code) => return code,
    };
    let repo = match required_option(
        &parsed,
        "--repo",
        VERIFY_ORIGIN_USAGE,
        VERIFY_ORIGIN_PROGRAM,
    ) {
        Ok(value) => value,
        Err(code) => return code,
    };
    if let Some(error) = strict_unrecognized(arguments, OPTIONS, &[]) {
        return usage_refusal(VERIFY_ORIGIN_USAGE, VERIFY_ORIGIN_PROGRAM, &error);
    }
    let Ok(root) = canonical_root(&root) else {
        return verify_origin_missing();
    };
    let origin =
        GixRepository::discover(&root).ok().and_then(|repository| {
            match resolve_remote_repo("origin", Some(&repository)) {
                RemoteRepoResult::Ok { repo } => Some(repo),
                RemoteRepoResult::Usage | RemoteRepoResult::ParseFailure => None,
            }
        });
    let Some(origin) = origin else {
        return verify_origin_missing();
    };
    if !origin.eq_ignore_ascii_case(&repo) {
        return command_error(
            VERIFY_ORIGIN_PROGRAM,
            &format!("origin remote {origin:?} does not identify publication repository {repo:?}"),
        );
    }
    println!("ORIGIN_REPO={origin}");
    println!("PUBLICATION_REPO={repo}");
    println!("ORIGIN_MATCHES_REPO=true");
    ExitCode::SUCCESS
}

fn verify_origin_missing() -> ExitCode {
    command_error(
        VERIFY_ORIGIN_PROGRAM,
        "state publication requires the origin remote to resolve to a GitHub OWNER/REPO slug",
    )
}

/// Dispatch `learn-from-bugs validate-report`.
#[must_use]
pub fn validate_report(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--report", "--headline"];
    if let Some(code) = help_explicit_argument(
        arguments,
        false,
        VALIDATE_REPORT_USAGE,
        VALIDATE_REPORT_PROGRAM,
    ) {
        return code;
    }
    if help_requested(arguments, false) {
        print!("{VALIDATE_REPORT_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = match strict_parse(
        arguments,
        OPTIONS,
        &[],
        VALIDATE_REPORT_USAGE,
        VALIDATE_REPORT_PROGRAM,
        false,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let report_path = match required_option(
        &parsed,
        "--report",
        VALIDATE_REPORT_USAGE,
        VALIDATE_REPORT_PROGRAM,
    ) {
        Ok(value) => path_from_argument(&value),
        Err(code) => return code,
    };
    let headline_path = match required_option(
        &parsed,
        "--headline",
        VALIDATE_REPORT_USAGE,
        VALIDATE_REPORT_PROGRAM,
    ) {
        Ok(value) => path_from_argument(&value),
        Err(code) => return code,
    };
    if let Some(error) = strict_unrecognized(arguments, OPTIONS, &[]) {
        return usage_refusal(VALIDATE_REPORT_USAGE, VALIDATE_REPORT_PROGRAM, &error);
    }
    if !report_path.is_file() {
        eprintln!("report not found: {}", report_path.display());
        return ExitCode::from(2);
    }
    if !headline_path.is_file() {
        eprintln!("headline not found: {}", headline_path.display());
        return ExitCode::from(2);
    }
    let report = String::from_utf8_lossy(&fs::read(&report_path).unwrap_or_default()).into_owned();
    let headline =
        String::from_utf8_lossy(&fs::read(&headline_path).unwrap_or_default()).into_owned();
    if let Err(error) = validate_report_contract(&report, &headline) {
        eprintln!("{error}");
        return ExitCode::from(2);
    }
    println!("REPORT_CONTRACT=pass");
    ExitCode::SUCCESS
}

/// Dispatch `learn-from-bugs state-publish`.
#[must_use]
#[allow(clippy::too_many_lines)] // It preserves the write-state option and failure wire exactly.
pub fn state_publish(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &[
        "--root",
        "--repo",
        "--run-dir",
        "--search",
        "--state",
        "--selected-count",
        "--highest-closed-issue-number-scanned",
        "--run-date",
        "--scan-started-at",
        "--proposals-file",
        "--base-proposals-file",
    ];
    if let Some(code) =
        help_explicit_argument(arguments, false, STATE_PUBLISH_USAGE, STATE_PUBLISH_PROGRAM)
    {
        return code;
    }
    if help_requested(arguments, false) {
        print!("{STATE_PUBLISH_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = match strict_parse(
        arguments,
        OPTIONS,
        &[],
        STATE_PUBLISH_USAGE,
        STATE_PUBLISH_PROGRAM,
        false,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let integers = match parse_integer_options(
        &parsed,
        &["--selected-count", "--highest-closed-issue-number-scanned"],
        STATE_PUBLISH_USAGE,
        STATE_PUBLISH_PROGRAM,
    ) {
        Ok(values) => values,
        Err(code) => return code,
    };
    let required = [
        "--root",
        "--repo",
        "--run-dir",
        "--search",
        "--state",
        "--selected-count",
        "--highest-closed-issue-number-scanned",
        "--run-date",
        "--scan-started-at",
        "--proposals-file",
    ];
    let mut values = BTreeMap::new();
    for option in required {
        match required_option(&parsed, option, STATE_PUBLISH_USAGE, STATE_PUBLISH_PROGRAM) {
            Ok(value) => {
                values.insert(option, value);
            }
            Err(code) => return code,
        }
    }
    if let Some(error) = strict_unrecognized(arguments, OPTIONS, &[]) {
        return usage_refusal(STATE_PUBLISH_USAGE, STATE_PUBLISH_PROGRAM, &error);
    }
    let Ok(root) = canonical_root(&path_from_argument(&values["--root"])) else {
        return state_publish_write_failure();
    };
    let Ok(path) = state_path(&root) else {
        return state_publish_write_failure();
    };
    let Ok(snapshot) = state_snapshot(&path) else {
        return state_publish_write_failure();
    };
    let result = write_state_locked(
        &path,
        StateRecord {
            run_date: values["--run-date"].clone(),
            repo: values["--repo"].clone(),
            search: values["--search"].clone(),
            state: values["--state"].clone(),
            selected_count: integers["--selected-count"],
            highest: integers["--highest-closed-issue-number-scanned"],
            scan_started_at: Some(values["--scan-started-at"].clone()),
            proposals: Vec::new(),
        },
        Some(Path::new(&values["--proposals-file"])),
        option_text(&parsed, "--base-proposals-file")
            .filter(|value| !value.is_empty())
            .as_deref()
            .map(Path::new),
        &root,
        &snapshot,
    );
    if result.is_err() {
        return state_publish_write_failure();
    }
    println!("STATE_PUBLISH_STATUS=saved");
    println!("STATE_PATH={}", path.display());
    ExitCode::SUCCESS
}

fn state_publish_write_failure() -> ExitCode {
    println!("STATE_PUBLISH_STATUS=write-state-failed");
    eprintln!("learn-from-bugs write-state failed during state publication");
    ExitCode::from(2)
}

/// Dispatch `learn-from-bugs filing-deps`.
#[must_use]
pub fn filing_deps(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &[
        "--input-file",
        "--proposal-map-file",
        "--proposal-deps-file",
        "--output",
    ];
    if let Some(code) =
        help_explicit_argument(arguments, false, FILING_DEPS_USAGE, FILING_DEPS_PROGRAM)
    {
        return code;
    }
    if help_requested(arguments, false) {
        print!("{FILING_DEPS_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = match strict_parse(
        arguments,
        OPTIONS,
        &[],
        FILING_DEPS_USAGE,
        FILING_DEPS_PROGRAM,
        false,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let input = match required_option(
        &parsed,
        "--input-file",
        FILING_DEPS_USAGE,
        FILING_DEPS_PROGRAM,
    ) {
        Ok(value) => path_from_argument(&value),
        Err(code) => return code,
    };
    let proposal_map = match required_option(
        &parsed,
        "--proposal-map-file",
        FILING_DEPS_USAGE,
        FILING_DEPS_PROGRAM,
    ) {
        Ok(value) => path_from_argument(&value),
        Err(code) => return code,
    };
    let proposal_deps = match required_option(
        &parsed,
        "--proposal-deps-file",
        FILING_DEPS_USAGE,
        FILING_DEPS_PROGRAM,
    ) {
        Ok(value) => path_from_argument(&value),
        Err(code) => return code,
    };
    let output = match required_option(&parsed, "--output", FILING_DEPS_USAGE, FILING_DEPS_PROGRAM)
    {
        Ok(value) => path_from_argument(&value),
        Err(code) => return code,
    };
    if let Some(error) = strict_unrecognized(arguments, OPTIONS, &[]) {
        return usage_refusal(FILING_DEPS_USAGE, FILING_DEPS_PROGRAM, &error);
    }
    let result = filing_dependencies(&input, &proposal_map, &proposal_deps)
        .and_then(|edges| plain_atomic_write(&output, &render_deps_tsv(&edges)));
    if let Err(error) = result {
        eprintln!("{FILING_DEPS_PROGRAM}: {error}");
        return ExitCode::from(1);
    }
    ExitCode::SUCCESS
}

fn help_requested(arguments: &[OsString], allow_abbreviations: bool) -> bool {
    arguments.iter().any(|argument| {
        let argument = argument.to_string_lossy();
        matches!(argument.as_ref(), "-h" | "--help")
            || (allow_abbreviations
                && argument.starts_with("--")
                && "--help".starts_with(argument.as_ref()))
    })
}

fn help_explicit_argument(
    arguments: &[OsString],
    allow_abbreviations: bool,
    usage: &str,
    program: &str,
) -> Option<ExitCode> {
    for argument in arguments {
        let text = argument.to_string_lossy();
        let Some((name, value)) = split_inline_option(&text) else {
            continue;
        };
        let is_help = matches!(name, "-h" | "--help")
            || (allow_abbreviations && name.starts_with("--") && "--help".starts_with(name));
        if is_help {
            return Some(usage_error(
                usage,
                program,
                &format!("argument -h/--help: ignored explicit argument '{value}'"),
                2,
            ));
        }
    }
    None
}

fn strict_parse(
    arguments: &[OsString],
    options: &[&'static str],
    flags: &[&'static str],
    usage: &str,
    program: &str,
    allow_abbreviations: bool,
) -> Result<ParsedCommandLine, ExitCode> {
    let parsed = parse_with_flags(arguments, options, flags, 0);
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(usage, program, error, 2));
    }
    if allow_abbreviations && let Some(error) = parsed.error() {
        return Err(usage_error(usage, program, &error, 2));
    }
    Ok(parsed)
}

fn strict_unrecognized(arguments: &[OsString], options: &[&str], flags: &[&str]) -> Option<String> {
    let mut unknown = Vec::new();
    let mut positionals_only = false;
    let mut index = 0;
    while let Some(argument) = arguments.get(index) {
        let text = argument.to_string_lossy();
        if !positionals_only && text == "--" {
            positionals_only = true;
            unknown.push(argument.clone());
        } else if !positionals_only {
            let (name, inline) = split_inline_option(&text).map_or_else(
                || (text.as_ref(), None),
                |(name, value)| (name, Some(value)),
            );
            if options.contains(&name) {
                if inline.is_none()
                    && arguments
                        .get(index + 1)
                        .is_some_and(|value| !looks_like_option(value))
                {
                    index += 1;
                }
            } else if !flags.contains(&name) {
                unknown.push(argument.clone());
            }
        } else {
            unknown.push(argument.clone());
        }
        index += 1;
    }
    (!unknown.is_empty()).then(|| format!("unrecognized arguments: {}", join_arguments(&unknown)))
}

fn usage_refusal(usage: &str, program: &str, error: &str) -> ExitCode {
    usage_error(usage, program, error, 2)
}

/// Split an inline command-line option (`--name=value`) without treating it as
/// a `KEY=value` wire record.
fn split_inline_option(text: &str) -> Option<(&str, &str)> {
    let separator = text.find('=')?;
    Some((&text[..separator], &text[separator + '='.len_utf8()..]))
}

fn required_option(
    parsed: &ParsedCommandLine,
    option: &str,
    usage: &str,
    program: &str,
) -> Result<String, ExitCode> {
    parsed
        .value(option)
        .map(|value| value.to_string_lossy().into_owned())
        .ok_or_else(|| {
            usage_error(
                usage,
                program,
                &format!("the following arguments are required: {option}"),
                2,
            )
        })
}

fn option_text(parsed: &ParsedCommandLine, option: &str) -> Option<String> {
    parsed
        .value(option)
        .map(|value| value.to_string_lossy().into_owned())
}

fn path_from_argument(value: &str) -> PathBuf {
    if value.is_empty() {
        PathBuf::from(".")
    } else {
        PathBuf::from(value)
    }
}

fn parse_int(value: &str, option: &str, usage: &str, program: &str) -> Result<i64, ExitCode> {
    value.parse().map_err(|_| {
        usage_error(
            usage,
            program,
            &format!("argument {option}: invalid int value: '{value}'"),
            2,
        )
    })
}

fn parse_integer_options(
    parsed: &ParsedCommandLine,
    options: &[&'static str],
    usage: &str,
    program: &str,
) -> Result<BTreeMap<&'static str, i64>, ExitCode> {
    let mut values = BTreeMap::new();
    for (option, value) in parsed.entries() {
        if options.contains(option) {
            values.insert(
                *option,
                parse_int(&value.to_string_lossy(), option, usage, program)?,
            );
        }
    }
    Ok(values)
}

fn command_error(program: &str, error: &str) -> ExitCode {
    eprintln!("{program}: {error}");
    ExitCode::from(1)
}

fn canonical_root(root: &Path) -> Result<PathBuf, String> {
    fs::canonicalize(root)
        .map_err(|error| format!("cannot resolve analysis root {}: {error}", root.display()))
}

fn resolve_repo(explicit: &str) -> Result<String, String> {
    if !explicit.is_empty() {
        repository_ref(explicit).map_err(|()| format!("invalid repository: {explicit}"))?;
        return Ok(explicit.to_owned());
    }
    ambient_repo().ok_or_else(|| "could not resolve GitHub repository".to_owned())
}

fn fetch_issues(
    repo: &str,
    search: &str,
    state: &str,
    limit: i64,
) -> Result<Vec<GitHubIssue>, String> {
    if limit == 0 {
        return Ok(Vec::new());
    }
    let limit = usize::try_from(limit).map_err(|_| "invalid issue limit".to_owned())?;
    let repo = repository_ref(repo).map_err(|()| "invalid repository".to_owned())?;
    let query = if state.eq_ignore_ascii_case("all") {
        search.to_owned()
    } else {
        format!("{search} state:{state}")
    };
    with_github_service(async |service, cancellation| {
        let request = GitHubIssueSearch {
            repo: repo.clone(),
            query: query.clone(),
            limit: limit.min(service.transport_policy().limits().items()),
        };
        service
            .search_issues(&request, cancellation)
            .await
            .map_err(|error| error.to_string())
    })
    .map_err(crate::github_service::ServiceFailure::into_detail)
}

fn create_out_dir(path: &Path) -> Result<PathBuf, String> {
    fs::create_dir_all(path).map_err(|error| error.to_string())?;
    fs::canonicalize(path).map_err(|error| error.to_string())
}

fn plain_atomic_write(path: &Path, contents: &str) -> Result<(), String> {
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    private_atomic_write(path, contents, parent).map_err(|error| error.to_string())
}

fn output_path(path: &Path) -> Result<PathBuf, String> {
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    let parent = fs::canonicalize(parent).map_err(|error| error.to_string())?;
    let name = path
        .file_name()
        .ok_or_else(|| format!("output path has no file name: {}", path.display()))?;
    Ok(parent.join(name))
}

#[derive(Clone, Debug)]
struct Digest {
    number: u64,
    title: String,
    closed_at: String,
    url: String,
    state: String,
    structured: bool,
    prefix_chars: usize,
    sections: Vec<(String, String)>,
    origin: Origin,
    classification: Option<BugClass>,
}

#[derive(Clone, Debug)]
struct BugClass {
    kind: String,
    surface: String,
}

#[derive(Clone, Debug)]
struct Origin {
    kind: &'static str,
    reference: Option<u64>,
    unknown_reason: Option<&'static str>,
}

fn build_digest(issue: &GitHubIssue) -> Digest {
    let prefix = diagnostic_prefix(&issue.body);
    let title = DONE_PREFIX.replace(&issue.title, "").into_owned();
    let (sections, structured, classification) = pick_sections(&prefix);
    let origin = classify_origin(&title, &prefix, classification.as_ref());
    Digest {
        number: issue.number,
        title,
        closed_at: issue.closed_at.chars().take(10).collect(),
        url: issue.url.clone(),
        state: github_state(issue.state).to_owned(),
        structured,
        prefix_chars: prefix.chars().count(),
        sections,
        origin,
        classification,
    }
}

const fn github_state(state: GitHubIssueState) -> &'static str {
    match state {
        GitHubIssueState::Open => "OPEN",
        GitHubIssueState::Closed => "CLOSED",
        GitHubIssueState::All => "ALL",
    }
}

fn diagnostic_prefix(body: &str) -> String {
    let mut cuts = [
        PLAN_MARKER.find(body),
        PLAN_HEADING.find(body),
        APPROACH_HEADING.find(body),
        PLAN_ACTION.find(body),
    ]
    .into_iter()
    .flatten()
    .map(|matched| matched.start())
    .collect::<Vec<_>>();
    cuts.sort_unstable();
    cuts.first()
        .map_or_else(|| body.to_owned(), |cut| body[..*cut].to_owned())
}

fn line_starts(text: &str) -> Vec<(usize, &str)> {
    let mut lines = Vec::new();
    let mut start = 0;
    for (offset, _) in text.match_indices('\n') {
        let mut line = &text[start..offset];
        if let Some(trimmed) = line.strip_suffix('\r') {
            line = trimmed;
        }
        lines.push((start, line));
        start = offset + 1;
    }
    if start < text.len() {
        let mut line = &text[start..];
        if let Some(trimmed) = line.strip_suffix('\r') {
            line = trimmed;
        }
        lines.push((start, line));
    }
    lines
}

fn fenced_indices(lines: &[&str]) -> HashSet<usize> {
    let mut fenced = HashSet::new();
    let mut opened: Option<(usize, char, usize)> = None;
    for (index, line) in lines.iter().enumerate() {
        let matched = FENCE.captures(line.trim());
        let Some(captures) = matched else { continue };
        let marker = captures.get(1).expect("marker group").as_str();
        let suffix = captures.get(2).expect("suffix group").as_str();
        match opened {
            None => opened = Some((index, marker.as_bytes()[0] as char, marker.len())),
            Some((open_at, character, length))
                if marker.as_bytes()[0] as char == character
                    && marker.len() >= length
                    && suffix.trim().is_empty() =>
            {
                fenced.extend((open_at + 1)..index);
                opened = None;
            }
            Some(_) => {}
        }
    }
    if let Some((open_at, _, _)) = opened {
        fenced.extend((open_at + 1)..lines.len());
    }
    fenced
}

fn diagnostic_sections(prefix: &str) -> Vec<(String, String)> {
    let positioned = line_starts(prefix);
    let lines: Vec<_> = positioned.iter().map(|(_, line)| *line).collect();
    let fenced = fenced_indices(&lines);
    let mut headings = Vec::<(String, usize, usize)>::new();
    for (index, (start, line)) in positioned.iter().enumerate() {
        if fenced.contains(&index) {
            continue;
        }
        if let Some(captures) = HEADING.captures(line) {
            let name = captures
                .get(1)
                .expect("heading group")
                .as_str()
                .replace('`', "")
                .trim()
                .to_lowercase();
            let end = HEADING.find(line).expect("heading match").end();
            headings.push((name, *start, *start + end));
        } else if let Some(captures) = BOLD_HEADING.captures(line) {
            let name = captures.get(1).expect("bold name").as_str().to_lowercase();
            let end = captures.get(2).expect("bold body").start();
            headings.push((name, *start, *start + end));
        }
    }
    headings
        .iter()
        .enumerate()
        .map(|(index, (name, _, content_start))| {
            let end = headings
                .get(index + 1)
                .map_or(prefix.len(), |(_, start, _)| *start);
            (name.clone(), prefix[*content_start..end].trim().to_owned())
        })
        .collect()
}

fn pick_sections(prefix: &str) -> (Vec<(String, String)>, bool, Option<BugClass>) {
    let ordered = diagnostic_sections(prefix);
    let mut found = BTreeMap::new();
    for (name, body) in &ordered {
        found.insert(name.clone(), body.clone());
    }
    let classification = found
        .get("classification")
        .and_then(|value| parse_classification(value))
        .or_else(|| parse_harness_classification(prefix));
    let wants = [
        ("summary", 600),
        ("impact", 600),
        ("classification", 400),
        ("root cause analysis", 1000),
        ("root cause", 1000),
        ("suggested fix(es)", 400),
        ("suggested fix", 400),
        ("repro", 400),
    ];
    let mut picked = Vec::new();
    let mut roots = HashSet::new();
    for (want, cap) in wants {
        let root = want.split(' ').next().expect("want root");
        if let Some(value) = found.get(want)
            && roots.insert(root)
        {
            picked.push((want.to_owned(), squeeze(value, cap)));
        }
    }
    if !picked.is_empty() {
        return (picked, true, classification);
    }
    if prefix.trim().chars().count() < TITLE_ONLY_PREFIX_MAX {
        return (
            vec![("_title_only".to_owned(), String::new())],
            false,
            classification,
        );
    }
    (
        vec![("_freeform".to_owned(), squeeze(&elide_tables(prefix), 1100))],
        false,
        classification,
    )
}

fn parse_classification(value: &str) -> Option<BugClass> {
    let captures = CLASSIFICATION.captures(value)?;
    Some(BugClass {
        kind: captures.get(1)?.as_str().to_uppercase(),
        surface: captures.get(2)?.as_str().to_uppercase(),
    })
}

fn parse_harness_classification(value: &str) -> Option<BugClass> {
    let lines: Vec<_> = value.lines().collect();
    let fenced = fenced_indices(&lines);
    let diagnostic = lines
        .iter()
        .enumerate()
        .filter(|(index, _)| !fenced.contains(index))
        .map(|(_, line)| *line)
        .collect::<Vec<_>>()
        .join("\n");
    let kind = HARNESS_CLASS.captures(&diagnostic)?;
    let surface = HARNESS_SURFACE.find_at(&diagnostic, kind.get(0)?.end())?;
    let surface = HARNESS_SURFACE.captures(&diagnostic[surface.start()..])?;
    Some(BugClass {
        kind: kind.get(1)?.as_str().to_uppercase(),
        surface: surface.get(1)?.as_str().to_uppercase(),
    })
}

fn is_table_row(line: &str) -> bool {
    let line = line.trim();
    if line.is_empty() {
        return false;
    }
    if line.starts_with('|') && line.ends_with('|') && line.matches('|').count() >= 2 {
        return true;
    }
    let box_count = line
        .chars()
        .filter(|character| ('\u{2500}'..='\u{257f}').contains(character))
        .count();
    box_count * 2 >= line.chars().count()
        || (box_count >= 2
            && line
                .chars()
                .next()
                .is_some_and(|c| ('\u{2500}'..='\u{257f}').contains(&c))
            && line
                .chars()
                .last()
                .is_some_and(|c| ('\u{2500}'..='\u{257f}').contains(&c)))
}

fn elide_tables(text: &str) -> String {
    let lines: Vec<_> = text.lines().collect();
    let mut out = Vec::new();
    let mut index = 0;
    while index < lines.len() {
        if !is_table_row(lines[index]) {
            out.push(lines[index].to_owned());
            index += 1;
            continue;
        }
        let start = index;
        while index < lines.len() && is_table_row(lines[index]) {
            index += 1;
        }
        if index - start == 1 {
            out.push(lines[start].to_owned());
        } else {
            out.push(format!("[table elided: {} lines]", index - start));
        }
    }
    out.join("\n")
}

fn squeeze(value: &str, cap: usize) -> String {
    let collapsed = NEWLINES.replace_all(value, "\n");
    let collapsed = collapsed.trim();
    let count = collapsed.chars().count();
    if count <= cap {
        return collapsed.to_owned();
    }
    let prefix: String = collapsed.chars().take(cap).collect();
    format!("{prefix}…")
}

fn classify_origin(title: &str, prefix: &str, classification: Option<&BugClass>) -> Origin {
    let ordered = diagnostic_sections(prefix);
    let structured = ordered.iter().any(|(name, _)| {
        matches!(
            name.as_str(),
            "summary"
                | "impact"
                | "classification"
                | "root cause analysis"
                | "root cause"
                | "suggested fix(es)"
                | "suggested fix"
                | "repro"
        )
    });
    let mut sources = vec![title.to_owned()];
    sources.extend(
        ordered
            .iter()
            .filter(|(name, _)| name.starts_with("root cause"))
            .map(|(_, body)| body.clone()),
    );
    if !structured && prefix.trim().chars().count() >= TITLE_ONLY_PREFIX_MAX {
        sources.push(prefix.to_owned());
    }
    if let Some(reference) = first_origin_reference(&sources) {
        return Origin {
            kind: "regression",
            reference: Some(reference),
            unknown_reason: None,
        };
    }
    if sources
        .iter()
        .any(|source| BARE_REGRESSION.is_match(source))
    {
        return Origin {
            kind: "regression",
            reference: None,
            unknown_reason: None,
        };
    }
    let has = |phrases: &[&str]| {
        sources.iter().any(|source| {
            let lower = source.to_lowercase();
            phrases.iter().any(|phrase| lower.contains(phrase))
        })
    };
    if has(&["never designed", "was never told", "no handling for"])
        || classification
            .is_some_and(|class| matches!(class.kind.as_str(), "CONFIGURATION_GAP" | "DESIGN_GAP"))
    {
        return Origin {
            kind: "spec-gap",
            reference: None,
            unknown_reason: None,
        };
    }
    if has(&["first time this path ran", "newly added"])
        || classification.is_some_and(|class| class.kind == "IMPLEMENTATION_BUG")
    {
        return Origin {
            kind: "new-code",
            reference: None,
            unknown_reason: None,
        };
    }
    let signal = ordered
        .iter()
        .any(|(name, _)| name == "classification" || name.starts_with("root cause"));
    Origin {
        kind: "unknown",
        reference: None,
        unknown_reason: Some(if signal || classification.is_some() {
            "inconclusive"
        } else {
            "no-classification-signal"
        }),
    }
}

fn first_origin_reference(sources: &[String]) -> Option<u64> {
    for source in sources {
        let mut best: Option<(usize, u64)> = None;
        for pattern in ORIGIN_REFS.iter() {
            if let Some(captures) = pattern.captures(source)
                && let (Some(whole), Some(number)) = (captures.get(0), captures.get(1))
                && let Ok(number) = number.as_str().parse()
                && best.is_none_or(|(start, _)| whole.start() < start)
            {
                best = Some((whole.start(), number));
            }
        }
        if let Some((_, number)) = best {
            return Some(number);
        }
    }
    None
}

fn ascii_json_string(value: &str) -> String {
    let mut out = String::with_capacity(value.len() + 2);
    out.push('"');
    for character in value.chars() {
        match character {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0c}' => out.push_str("\\f"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            character if (character as u32) < 0x20 => {
                let _ = std::fmt::write(&mut out, format_args!("\\u{:04x}", character as u32));
            }
            character if (character as u32) <= 0x7f => out.push(character),
            character if (character as u32) <= 0xffff => {
                let _ = std::fmt::write(&mut out, format_args!("\\u{:04x}", character as u32));
            }
            character => {
                let value = character as u32 - 0x1_0000;
                let high = 0xd800 + (value >> 10);
                let low = 0xdc00 + (value & 0x3ff);
                let _ = std::fmt::write(&mut out, format_args!("\\u{high:04x}\\u{low:04x}"));
            }
        }
    }
    out.push('"');
    out
}

/// Preserve Python's `json.dumps(..., ensure_ascii=True)` wire encoding.
fn ascii_json(value: &str) -> String {
    let mut out = String::with_capacity(value.len());
    for character in value.chars() {
        if character.is_ascii() {
            out.push(character);
        } else if (character as u32) <= 0xffff {
            let _ = std::fmt::write(&mut out, format_args!("\\u{:04x}", character as u32));
        } else {
            let value = character as u32 - 0x1_0000;
            let high = 0xd800 + (value >> 10);
            let low = 0xdc00 + (value & 0x3ff);
            let _ = std::fmt::write(&mut out, format_args!("\\u{high:04x}\\u{low:04x}"));
        }
    }
    out
}

fn serialize_digest(digest: &Digest) -> String {
    let sections = digest
        .sections
        .iter()
        .map(|(key, value)| format!("{}: {}", ascii_json_string(key), ascii_json_string(value)))
        .collect::<Vec<_>>()
        .join(", ");
    let origin = format!(
        "{{\"kind\": {}, \"ref\": {}}}",
        ascii_json_string(digest.origin.kind),
        digest
            .origin
            .reference
            .map_or_else(|| "null".to_owned(), |value| value.to_string())
    );
    let mut fields = vec![
        format!("\"number\": {}", digest.number),
        format!("\"title\": {}", ascii_json_string(&digest.title)),
        format!("\"closed_at\": {}", ascii_json_string(&digest.closed_at)),
        format!("\"url\": {}", ascii_json_string(&digest.url)),
        format!("\"state\": {}", ascii_json_string(&digest.state)),
        format!("\"structured\": {}", digest.structured),
        format!("\"prefix_chars\": {}", digest.prefix_chars),
        format!("\"sections\": {{{sections}}}"),
        format!("\"origin\": {origin}"),
    ];
    if let Some(classification) = &digest.classification {
        fields.push(format!(
            "\"class\": {{\"kind\": {}, \"surface\": {}}}",
            ascii_json_string(&classification.kind),
            ascii_json_string(&classification.surface)
        ));
    }
    format!("{{{}}}\n", fields.join(", "))
}

fn write_digest_chunks(out: &Path, digests: &[Digest]) -> Result<(Vec<PathBuf>, usize), String> {
    let records: Vec<_> = digests.iter().map(serialize_digest).collect();
    let mut chunks = vec![Vec::<String>::new()];
    let mut chunk_chars = 0;
    for record in &records {
        let chars = record.chars().count();
        if chars > DIGEST_CHUNK_CHAR_LIMIT {
            return Err("digest record exceeds the configured chunk token limit".to_owned());
        }
        if !chunks.last().is_some_and(Vec::is_empty)
            && chunk_chars + chars > DIGEST_CHUNK_CHAR_LIMIT
        {
            chunks.push(Vec::new());
            chunk_chars = 0;
        }
        chunks
            .last_mut()
            .expect("initial chunk")
            .push(record.clone());
        chunk_chars += chars;
    }
    let mut paths = Vec::new();
    for (index, chunk) in chunks.iter().enumerate() {
        let path = out.join(format!("digest-{:02}.jsonl", index + 1));
        plain_atomic_write(&path, &chunk.concat())?;
        paths.push(path);
    }
    Ok((
        paths,
        records.iter().map(|record| record.chars().count()).sum(),
    ))
}

#[derive(Serialize)]
struct CoverageIndex {
    guidelines: Vec<(String, String)>,
    invariants: Vec<(String, String)>,
    python_lints: Vec<String>,
    script_lints: Vec<String>,
    #[serde(skip)]
    guidelines_status: &'static str,
}

fn coverage_index(root: &Path) -> CoverageIndex {
    let guidelines_path = root.join("ARCHITECTURAL_GUIDELINES.md");
    let guidelines = scan_guidelines(&guidelines_path);
    let guidelines_status = if !guidelines_path.is_file() {
        "missing"
    } else if guidelines.is_empty() {
        "empty"
    } else {
        "indexed"
    };
    CoverageIndex {
        guidelines,
        invariants: scan_marked(
            &root.join("ARCHITECTURAL_INVARIANTS.md"),
            &INVARIANT_HEADING_RE,
        ),
        python_lints: scan_lints(&root.join("python/larch/lint"), "lint_", ".py"),
        script_lints: scan_lints(&root.join("scripts"), "lint-", ""),
        guidelines_status,
    }
}

fn scan_guidelines(path: &Path) -> Vec<(String, String)> {
    if !path.is_file() {
        return Vec::new();
    }
    let text = String::from_utf8_lossy(&fs::read(path).unwrap_or_default()).into_owned();
    let lines: Vec<_> = text.lines().collect();
    let fenced = fenced_indices(&lines);
    let marked = lines
        .iter()
        .enumerate()
        .filter(|(index, _)| !fenced.contains(index))
        .filter_map(|(_, line)| {
            GUIDELINE_HEADING_RE.captures(line).map(|caps| {
                (
                    caps.get(1).expect("id").as_str().to_owned(),
                    caps.get(2).expect("title").as_str().to_owned(),
                )
            })
        })
        .collect::<Vec<_>>();
    if !marked.is_empty() {
        return marked;
    }
    lines
        .iter()
        .enumerate()
        .filter(|(index, _)| !fenced.contains(index))
        .filter_map(|(_, line)| {
            UNMARKED_GUIDELINE.captures(line).map(|caps| {
                let title = caps.get(1).expect("title").as_str().to_owned();
                (title.clone(), title)
            })
        })
        .collect()
}

fn scan_marked(path: &Path, pattern: &Regex) -> Vec<(String, String)> {
    if !path.is_file() {
        return Vec::new();
    }
    let text = String::from_utf8_lossy(&fs::read(path).unwrap_or_default()).into_owned();
    let lines: Vec<_> = text.lines().collect();
    let fenced = fenced_indices(&lines);
    lines
        .iter()
        .enumerate()
        .filter(|(index, _)| !fenced.contains(index))
        .filter_map(|(_, line)| {
            pattern.captures(line).map(|caps| {
                (
                    caps.get(1).expect("id").as_str().to_owned(),
                    caps.get(2).expect("title").as_str().to_owned(),
                )
            })
        })
        .collect()
}

fn scan_lints(directory: &Path, prefix: &str, suffix: &str) -> Vec<String> {
    let Ok(entries) = fs::read_dir(directory) else {
        return Vec::new();
    };
    let mut names = entries
        .filter_map(Result::ok)
        .filter_map(|entry| {
            let path = entry.path();
            let name = path.file_name()?.to_str()?;
            if !name.starts_with(prefix) || (!suffix.is_empty() && !name.ends_with(suffix)) {
                return None;
            }
            path.file_stem()?.to_str().map(str::to_owned)
        })
        .collect::<Vec<_>>();
    names.sort();
    names
}

fn render_origin_headline(digests: &[Digest]) -> String {
    let mut counts = BTreeMap::from([
        ("regression", 0usize),
        ("new-code", 0),
        ("spec-gap", 0),
        ("unknown", 0),
    ]);
    let mut reasons = BTreeMap::from([("no-classification-signal", 0usize), ("inconclusive", 0)]);
    let mut chains = Vec::new();
    let mut suspect = Vec::new();
    for digest in digests {
        *counts.get_mut(digest.origin.kind).expect("known origin") += 1;
        if digest.origin.kind == "unknown" {
            *reasons
                .get_mut(digest.origin.unknown_reason.unwrap_or("inconclusive"))
                .expect("known reason") += 1;
        }
        if digest.origin.kind == "regression"
            && let Some(reference) = digest.origin.reference
        {
            let chain = format!("#{reference} -> #{}", digest.number);
            if reference == digest.number {
                suspect.push(format!("{chain} (suspect: self-reference)"));
            } else {
                chains.push(chain);
            }
        }
    }
    let selected = digests.len();
    let mut lines = vec![format!("#### Origin distribution (selected={selected})")];
    for kind in ["regression", "new-code", "spec-gap", "unknown"] {
        let count = counts[kind];
        lines.push(format!(
            "- {kind}: {count} ({}%)",
            pct_one_decimal(count, selected)
        ));
    }
    if counts["unknown"] > 0 {
        for (reason, label) in [
            ("no-classification-signal", "no classification signal"),
            ("inconclusive", "signal present but inconclusive"),
        ] {
            let count = reasons[reason];
            lines.push(format!(
                "  - {label}: {count} ({}%)",
                pct_one_decimal(count, selected)
            ));
        }
    }
    lines.push("#### Referenced regression chains".to_owned());
    if chains.is_empty() && suspect.is_empty() {
        lines.push("(none)".to_owned());
    } else {
        lines.extend(
            chains
                .into_iter()
                .chain(suspect)
                .map(|value| format!("- {value}")),
        );
    }
    lines.push("#### Regression ratio".to_owned());
    if selected == 0 {
        lines.push("n/a (0/0)".to_owned());
    } else {
        lines.push(format!(
            "{}/{} ({}%)",
            counts["regression"],
            selected,
            pct_one_decimal(counts["regression"], selected)
        ));
    }
    format!("{}\n", lines.join("\n"))
}

#[allow(clippy::cast_precision_loss)] // GitHub transport bounds selected records far below f64's exact integer range.
fn pct_one_decimal(count: usize, total: usize) -> String {
    if total == 0 {
        "0.0".to_owned()
    } else {
        format!("{:.1}", count as f64 * 100.0 / total as f64)
    }
}

fn resolve_zone_search(
    zones_csv: &str,
    has_explicit: bool,
    has_verbal: bool,
) -> Result<String, String> {
    if has_explicit {
        return Err("--zones cannot be combined with --search".to_owned());
    }
    if has_verbal {
        return Err("--zones cannot be combined with verbal search text".to_owned());
    }
    if zones_csv.trim().is_empty() {
        return Err("--zones requires at least one non-empty zone name".to_owned());
    }
    let mut zones = Vec::new();
    for zone in zones_csv.split(',') {
        let zone = zone.trim();
        if zone.is_empty() {
            return Err("--zones contains an empty zone name".to_owned());
        }
        zones.push(zone);
    }
    Ok(format!(
        "{BUG_PREFIX} ({}) in:title,body",
        zones.join(" OR ")
    ))
}

#[derive(Clone, Debug)]
struct StateRecord {
    run_date: String,
    repo: String,
    search: String,
    state: String,
    selected_count: i64,
    highest: i64,
    scan_started_at: Option<String>,
    proposals: Vec<Proposal>,
}

#[derive(Clone, Debug)]
struct StateSnapshot {
    data: Option<Vec<u8>>,
    digest: String,
}

#[derive(Clone, Debug)]
struct Proposal {
    id: String,
    kind: String,
    target: String,
    run_date: String,
    status: String,
    filed_issue: Option<i64>,
}

#[derive(Clone, Debug)]
struct CheckedProposal {
    proposal: Proposal,
    adoption_evidence: Option<String>,
}

fn refresh_proposals(
    proposals: &[Proposal],
    root: &Path,
    repo: &str,
) -> Result<Vec<CheckedProposal>, String> {
    if proposals
        .iter()
        .any(|proposal| !valid_target(&proposal.kind, &proposal.target, Some(root)))
    {
        return Err("invalid proposal record".to_owned());
    }
    let statuses = filed_issue_statuses(proposals, repo)?;
    proposals
        .iter()
        .map(|proposal| {
            let target_verified = proposal_target_adopted(proposal, root)?;
            let filed_status = proposal
                .filed_issue
                .map(|number| {
                    statuses
                        .get(&number)
                        .cloned()
                        .ok_or_else(|| "gh issue view returned mismatched issue data".to_owned())
                })
                .transpose()?
                .flatten();
            let status = filed_status.as_ref().map_or_else(
                || {
                    if target_verified {
                        "adopted".to_owned()
                    } else if matches!(proposal.status.as_str(), "adopted" | "orphaned") {
                        "orphaned".to_owned()
                    } else {
                        "pending".to_owned()
                    }
                },
                Clone::clone,
            );
            let adoption_evidence = if status != "adopted" {
                None
            } else if target_verified && filed_status.as_deref() == Some("adopted") {
                Some("both".to_owned())
            } else if target_verified {
                Some("target-verified".to_owned())
            } else if filed_status.as_deref() == Some("adopted") {
                Some("issue-closed-only".to_owned())
            } else {
                return Err("adopted proposal has no adoption evidence".to_owned());
            };
            let mut proposal = proposal.clone();
            proposal.status = status;
            Ok(CheckedProposal {
                proposal,
                adoption_evidence,
            })
        })
        .collect()
}

fn filed_issue_statuses(
    proposals: &[Proposal],
    repo: &str,
) -> Result<BTreeMap<i64, Option<String>>, String> {
    let repo = repository_ref(repo).map_err(|()| format!("invalid repository: {repo}"))?;
    let numbers: BTreeSet<i64> = proposals
        .iter()
        .filter_map(|proposal| proposal.filed_issue)
        .collect();
    if numbers.is_empty() {
        return Ok(BTreeMap::new());
    }
    with_github_service(async |service, cancellation| {
        let mut statuses = BTreeMap::new();
        for number in &numbers {
            let issue = service
                .issue(&repo, number.cast_unsigned(), cancellation)
                .await
                .map_err(|error| error.to_string())?;
            if issue.number != number.cast_unsigned() {
                return Err("gh issue view returned mismatched issue data".to_owned());
            }
            let status = match issue.state {
                GitHubIssueState::Open => Some("pending".to_owned()),
                GitHubIssueState::Closed => match issue.state_reason.as_str() {
                    "NOT_PLANNED" => Some("orphaned".to_owned()),
                    "COMPLETED" => Some("adopted".to_owned()),
                    "DUPLICATE" => None,
                    _ => {
                        return Err(
                            "gh issue view returned an unknown closed issue reason".to_owned()
                        );
                    }
                },
                GitHubIssueState::All => {
                    return Err("gh issue view returned an unknown issue state".to_owned());
                }
            };
            statuses.insert(*number, status);
        }
        Ok(statuses)
    })
    .map_err(crate::github_service::ServiceFailure::into_detail)
}

fn proposal_target_adopted(proposal: &Proposal, root: &Path) -> Result<bool, String> {
    if proposal.kind == "fix" {
        return Ok(false);
    }
    if proposal.target.starts_with("check:") {
        let (path, symbol) = proposal
            .target
            .trim_start_matches("check:")
            .split_once('#')
            .ok_or_else(|| format!("invalid check target: {:?}", proposal.target))?;
        return Ok(target_file(root, path).is_some_and(|path| file_has_symbol(&path, symbol)));
    }
    match proposal.kind.as_str() {
        "lint" if proposal.target.starts_with("module:") => {
            Ok(target_file(root, proposal.target.trim_start_matches("module:")).is_some())
        }
        "lint" if proposal.target.starts_with("registration:") => {
            let name = proposal.target.trim_start_matches("registration:");
            Ok(lint_registration_adopted(name, root))
        }
        "invariant" | "guideline" => architectural_target_adopted(&proposal.target, root),
        "hook" => hook_target_adopted(&proposal.target, root),
        "test" => test_target_adopted(&proposal.target, root),
        _ => Ok(false),
    }
}

fn lint_registration_adopted(name: &str, root: &Path) -> bool {
    let Ok(text) = fs::read_to_string(root.join("python/larch/cli.py")) else {
        return false;
    };
    let registry = Regex::new(r"(?m)^\s*_REGISTRY(?:\s*:[^=\n]+)?\s*=")
        .expect("registry assignment regex compiles");
    let entry = Regex::new(&format!(
        r#"(?m)^(?:\s*_REGISTRY(?:\s*:[^=\n]+)?\s*=\s*\{{\s*)?\(\s*[\"']lint[\"']\s*,\s*[\"']{}[\"']\s*\)\s*:"#,
        regex::escape(name)
    ))
    .expect("registry entry regex compiles");
    registry.is_match(&text) && entry.is_match(&text)
}

fn target_file(root: &Path, relative: &str) -> Option<PathBuf> {
    valid_relative_path(relative, &[], Some(root))
        .then(|| root.join(relative))
        .filter(|path| path.is_file())
}

fn architectural_target_adopted(target: &str, root: &Path) -> Result<bool, String> {
    let (relative, fragment) = target
        .split_once('#')
        .ok_or_else(|| format!("invalid architectural target: {target:?}"))?;
    let Some(path) = target_file(root, relative) else {
        return Ok(false);
    };
    let text = fs::read_to_string(path).map_err(|error| error.to_string())?;
    let lines: Vec<_> = text.lines().collect();
    let fenced = fenced_indices(&lines);
    Ok(lines.iter().enumerate().any(|(index, line)| {
        if fenced.contains(&index) || !line.starts_with('#') {
            return false;
        }
        let heading = line.trim_start_matches('#').trim();
        let identifier = heading.split_once(':').map_or(heading, |(value, _)| value);
        fragment == heading || fragment == identifier
    }))
}

fn test_target_adopted(target: &str, root: &Path) -> Result<bool, String> {
    let (relative, symbol) = target
        .split_once("::")
        .map_or((target, None), |(path, symbol)| (path, Some(symbol)));
    let Some(path) = target_file(root, relative) else {
        return Ok(false);
    };
    let Some(symbol) = symbol else {
        return Ok(true);
    };
    if Path::new(relative)
        .extension()
        .is_some_and(|extension| extension.eq_ignore_ascii_case("rs"))
    {
        return Ok(file_has_symbol(&path, symbol));
    }
    let text = fs::read_to_string(path).map_err(|error| error.to_string())?;
    let pattern = Regex::new(&format!(r"(?m)^def\s+{}\s*\(", regex::escape(symbol)))
        .map_err(|error| error.to_string())?;
    Ok(pattern.is_match(&text))
}

fn file_has_symbol(path: &Path, symbol: &str) -> bool {
    let Ok(text) = fs::read_to_string(path) else {
        return false;
    };
    Regex::new(&format!(r"\b{}\b", regex::escape(symbol)))
        .is_ok_and(|pattern| pattern.is_match(&text))
}

fn hook_target_adopted(target: &str, root: &Path) -> Result<bool, String> {
    let path = root.join("hooks/hooks.json");
    let Ok(text) = fs::read_to_string(path) else {
        return Ok(false);
    };
    let value: Value = serde_json::from_str(&text)
        .map_err(|error| format!("invalid hooks configuration: {error}"))?;
    Ok(hook_value_matches(
        &value,
        target.trim_start_matches("hook:"),
        root,
        "",
    ))
}

fn hook_value_matches(value: &Value, token: &str, root: &Path, key: &str) -> bool {
    match value {
        Value::Object(object) => object
            .iter()
            .any(|(child_key, child)| hook_value_matches(child, token, root, child_key)),
        Value::Array(values) => values
            .iter()
            .any(|child| hook_value_matches(child, token, root, key)),
        Value::String(value) if key == "matcher" => value == token,
        Value::String(value) if key == "command" => value
            .split_whitespace()
            .map(|argument| argument.trim_matches(['\'', '\"']))
            .any(|argument| normalize_hook_command(argument, root) == token),
        Value::Null | Value::Bool(_) | Value::Number(_) | Value::String(_) => false,
    }
}

fn normalize_hook_command(command: &str, root: &Path) -> String {
    let command = command
        .strip_prefix("${CLAUDE_PLUGIN_ROOT}/")
        .or_else(|| command.strip_prefix("$CLAUDE_PLUGIN_ROOT/"))
        .unwrap_or(command);
    let path = Path::new(command);
    if path.is_absolute()
        && let Ok(relative) = path.strip_prefix(root)
    {
        return relative.to_string_lossy().replace('\\', "/");
    }
    command.replace('\\', "/")
}

fn proposal_line(proposal: &Proposal) -> String {
    format!(
        "{{\"id\": {}, \"type\": {}, \"target\": {}, \"run_date\": {}, \"status\": {}, \"filed_issue\": {}}}\n",
        ascii_json_string(&proposal.id),
        ascii_json_string(&proposal.kind),
        ascii_json_string(&proposal.target),
        ascii_json_string(&proposal.run_date),
        ascii_json_string(&proposal.status),
        proposal
            .filed_issue
            .map_or_else(|| "null".to_owned(), |number| number.to_string()),
    )
}

fn checked_proposal_line(checked: &CheckedProposal) -> String {
    let proposal = &checked.proposal;
    let evidence = checked
        .adoption_evidence
        .as_deref()
        .map_or_else(|| "null".to_owned(), ascii_json_string);
    format!(
        "{{\"id\": {}, \"type\": {}, \"target\": {}, \"run_date\": {}, \"status\": {}, \"filed_issue\": {}, \"adoption_evidence\": {evidence}}}\n",
        ascii_json_string(&proposal.id),
        ascii_json_string(&proposal.kind),
        ascii_json_string(&proposal.target),
        ascii_json_string(&proposal.run_date),
        ascii_json_string(&proposal.status),
        proposal
            .filed_issue
            .map_or_else(|| "null".to_owned(), |number| number.to_string()),
    )
}

#[allow(clippy::too_many_lines, clippy::cast_precision_loss)] // Exact Python one-decimal summary wire.
fn render_adoption_summary(proposals: &[CheckedProposal]) -> String {
    let adopted = proposals
        .iter()
        .filter(|proposal| proposal.proposal.status == "adopted")
        .collect::<Vec<_>>();
    let count = |status| {
        proposals
            .iter()
            .filter(|proposal| proposal.proposal.status == status)
            .count()
    };
    let evidence_order = ["target-verified", "issue-closed-only", "both"];
    let evidence = evidence_order
        .iter()
        .filter_map(|kind| {
            let count = adopted
                .iter()
                .filter(|proposal| proposal.adoption_evidence.as_deref() == Some(*kind))
                .count();
            (count > 0).then(|| format!("{count} {kind}"))
        })
        .collect::<Vec<_>>();
    let unavailable = adopted.len().saturating_sub(
        evidence_order
            .iter()
            .map(|kind| {
                adopted
                    .iter()
                    .filter(|proposal| proposal.adoption_evidence.as_deref() == Some(*kind))
                    .count()
            })
            .sum(),
    );
    let mut evidence = evidence;
    if unavailable > 0 {
        evidence.push(format!("{unavailable} unavailable"));
    }
    let total = proposals.len();
    let adopted_count = count("adopted");
    let adopted_line = if evidence.is_empty() {
        format!("- Adopted: {adopted_count}")
    } else {
        format!("- Adopted: {adopted_count} ({})", evidence.join(", "))
    };
    let mut lines = vec![
        "## Proposal adoption".to_owned(),
        String::new(),
        adopted_line,
        format!("- Pending: {}", count("pending")),
        format!("- Orphaned: {}", count("orphaned")),
        format!(
            "- Adoption rate: {:.1}%",
            if total == 0 {
                0.0
            } else {
                adopted_count as f64 * 100.0 / total as f64
            }
        ),
        String::new(),
        "### Adoption evidence".to_owned(),
        String::new(),
    ];
    let mut adopted = adopted;
    adopted.sort_by_key(|proposal| (&proposal.proposal.run_date, &proposal.proposal.id));
    if adopted.is_empty() {
        lines.push("None.".to_owned());
    } else {
        for proposal in adopted {
            lines.push(format!(
                "- `{}`: `{}`",
                proposal.proposal.id,
                proposal
                    .adoption_evidence
                    .as_deref()
                    .unwrap_or("unavailable")
            ));
        }
    }
    lines.extend([
        String::new(),
        "### Oldest pending".to_owned(),
        String::new(),
    ]);
    let mut pending = proposals
        .iter()
        .filter(|proposal| proposal.proposal.status == "pending")
        .collect::<Vec<_>>();
    pending.sort_by_key(|proposal| (&proposal.proposal.run_date, &proposal.proposal.id));
    if pending.is_empty() {
        lines.push("None.".to_owned());
    } else {
        let today = chrono::Utc::now().date_naive();
        for proposal in pending.into_iter().take(5) {
            let date = proposal
                .proposal
                .run_date
                .get(..10)
                .and_then(|value| NaiveDate::parse_from_str(value, "%Y-%m-%d").ok())
                .unwrap_or(today);
            let days = today.signed_duration_since(date).num_days().max(0);
            lines.push(format!(
                "- `{}`: {days} days, `{}`",
                proposal.proposal.id, proposal.proposal.target
            ));
        }
    }
    format!("{}\n", lines.join("\n"))
}

fn validate_report_contract(report: &str, headline: &str) -> Result<(), String> {
    let section = SECTION2_HEADING
        .find(report)
        .ok_or_else(|| "report missing Root-cause clusters section heading".to_owned())?;
    let after_heading = &report[section.end()..];
    let section_body = NEXT_TOP_SECTION
        .find(after_heading)
        .map_or(after_heading, |next| &after_heading[..next.start()]);
    let needle = headline.trim();
    if needle.is_empty() {
        return Err("origin headline is empty".to_owned());
    }
    let position = section_body
        .find(needle)
        .or_else(|| section_body.find(needle.trim_end_matches('\n')))
        .ok_or_else(|| {
            "generated origin headline must appear verbatim as the first block in Section 2"
                .to_owned()
        })?;
    if !section_body[..position].trim().is_empty() {
        return Err(
            "generated origin headline must appear before cluster rows in Section 2".to_owned(),
        );
    }
    let mut start = 0;
    while let Some(relative) = report[start..].find(PROSE_ONLY_MARKER) {
        let index = start + relative;
        let window_start = index.saturating_sub(400);
        let window_end = (index + PROSE_ONLY_MARKER.len() + 800).min(report.len());
        let window = &report[window_start..window_end];
        for citation in ["character-ai/larch#6746", "character-ai/larch#6747"] {
            if !window.contains(citation) {
                return Err(format!(
                    "prose-only marker requires citation {citation} near the marker"
                ));
            }
        }
        if !MECHANICAL_ALTERNATIVE.is_match(window) {
            return Err(
                "prose-only marker requires a named lint, hook, or invariant-test alternative, or an explicit no-mechanical-alternative statement".to_owned(),
            );
        }
        start = index + PROSE_ONLY_MARKER.len();
    }
    Ok(())
}

fn filing_dependencies(
    input_file: &Path,
    proposal_map_file: &Path,
    proposal_deps_file: &Path,
) -> Result<Vec<(usize, usize)>, String> {
    let input = read_regular_text(input_file, "batch input", false)?;
    let parsed = parse_issue_input(&input);
    if parsed.items.is_empty() {
        return Err("batch input has no issue items".to_owned());
    }
    if parsed.items.iter().any(|item| item.malformed) {
        return Err("batch input contains a malformed issue item".to_owned());
    }
    let mapping = proposal_batch_map(proposal_map_file, parsed.items.len())?;
    let declared = declared_filing_edges(proposal_deps_file, &mapping)?;
    let plan = plan_file_conflict_deps(
        &parsed.items,
        FILE_CONFLICT_DEFAULT_CLUSTER_CAP,
        FILE_CONFLICT_DEFAULT_GLOBAL_CAP,
    )
    .map_err(|error| error.message())?;
    let mut combined = BTreeSet::new();
    for edge in declared {
        if filing_path_exists(&combined, edge.1, edge.0) {
            return Err("proposal dependencies contain a cycle".to_owned());
        }
        combined.insert(edge);
    }
    for edge in plan.deps {
        if !combined.contains(&edge) && !filing_path_exists(&combined, edge.1, edge.0) {
            combined.insert(edge);
        }
    }
    if combined.len() > FILE_CONFLICT_DEFAULT_GLOBAL_CAP {
        return Err(format!(
            "filing dependency output exceeds {FILE_CONFLICT_DEFAULT_GLOBAL_CAP} rows"
        ));
    }
    Ok(combined.into_iter().collect())
}

fn read_regular_text(path: &Path, label: &str, reject_cr: bool) -> Result<String, String> {
    let metadata = fs::symlink_metadata(path)
        .map_err(|_| format!("{label} is not a regular file: {}", path.display()))?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(format!("{label} is not a regular file: {}", path.display()));
    }
    if metadata.len() > FILING_DEPS_MAX_BYTES && label != "batch input" {
        return Err(format!(
            "{label} exceeds {FILING_DEPS_MAX_BYTES} bytes: {}",
            path.display()
        ));
    }
    let text = fs::read_to_string(path).map_err(|error| error.to_string())?;
    if reject_cr && text.contains('\r') {
        return Err(format!(
            "{label} contains carriage returns: {}",
            path.display()
        ));
    }
    Ok(text)
}

fn filing_tsv(path: &Path, label: &str) -> Result<Vec<(usize, String)>, String> {
    let text = read_regular_text(path, label, true)?;
    let lines = text.lines().map(str::to_owned).collect::<Vec<_>>();
    if lines.len() > FILE_CONFLICT_DEFAULT_GLOBAL_CAP {
        return Err(format!(
            "{label} exceeds {FILE_CONFLICT_DEFAULT_GLOBAL_CAP} rows"
        ));
    }
    Ok(lines
        .into_iter()
        .enumerate()
        .map(|(index, line)| (index + 1, line))
        .collect())
}

fn proposal_batch_map(path: &Path, item_count: usize) -> Result<BTreeMap<String, usize>, String> {
    let rows = filing_tsv(path, "proposal batch map")?;
    if rows.is_empty() {
        return Err("proposal batch map is empty".to_owned());
    }
    let mut mapping = BTreeMap::new();
    for (line_number, line) in rows {
        let fields = line.split('\t').collect::<Vec<_>>();
        let [proposal_id, item_raw] = fields.as_slice() else {
            return Err(format!(
                "proposal batch map line {line_number} must have two TSV fields"
            ));
        };
        if !PROPOSAL_ID.is_match(proposal_id) {
            return Err(format!(
                "proposal batch map line {line_number} has invalid proposal id"
            ));
        }
        if mapping.contains_key(*proposal_id) {
            return Err(format!(
                "proposal batch map line {line_number} repeats proposal id {proposal_id}"
            ));
        }
        let item = item_raw.parse::<usize>().ok().filter(|item| {
            item_raw.bytes().all(|byte| byte.is_ascii_digit()) && (1..=item_count).contains(item)
        });
        let Some(item) = item else {
            return Err(format!(
                "proposal batch map line {line_number} has out-of-range batch item"
            ));
        };
        mapping.insert((*proposal_id).to_owned(), item);
    }
    let missing = (1..=item_count)
        .filter(|item| !mapping.values().any(|mapped| mapped == item))
        .map(|item| item.to_string())
        .collect::<Vec<_>>();
    if !missing.is_empty() {
        return Err(format!(
            "proposal batch map does not cover batch item(s): {}",
            missing.join(",")
        ));
    }
    Ok(mapping)
}

fn declared_filing_edges(
    path: &Path,
    mapping: &BTreeMap<String, usize>,
) -> Result<BTreeSet<(usize, usize)>, String> {
    let rows = filing_tsv(path, "proposal dependency file")?;
    let mut proposal_edges = BTreeSet::new();
    let mut item_edges = BTreeSet::new();
    for (line_number, line) in rows {
        let fields = line.split('\t').collect::<Vec<_>>();
        let [blocker, blocked_id] = fields.as_slice() else {
            return Err(format!(
                "proposal dependency line {line_number} must have two TSV fields"
            ));
        };
        if blocker == blocked_id {
            return Err(format!(
                "proposal dependency line {line_number} is a self-dependency"
            ));
        }
        for proposal_id in [*blocker, *blocked_id] {
            if !PROPOSAL_ID.is_match(proposal_id) {
                return Err(format!(
                    "proposal dependency line {line_number} has invalid proposal id"
                ));
            }
            if !mapping.contains_key(proposal_id) {
                return Err(format!(
                    "proposal dependency line {line_number} names unmapped proposal {proposal_id}"
                ));
            }
        }
        if !proposal_edges.insert(((*blocker).to_owned(), (*blocked_id).to_owned())) {
            return Err(format!(
                "proposal dependency line {line_number} repeats an earlier edge"
            ));
        }
        let edge = (mapping[*blocker], mapping[*blocked_id]);
        if edge.0 == edge.1 {
            continue;
        }
        if item_edges.contains(&(edge.1, edge.0)) {
            return Err("proposal dependencies map to reciprocal batch-item edges".to_owned());
        }
        item_edges.insert(edge);
    }
    Ok(item_edges)
}

fn filing_path_exists(edges: &BTreeSet<(usize, usize)>, start: usize, target: usize) -> bool {
    let mut pending = vec![start];
    let mut visited = BTreeSet::new();
    while let Some(node) = pending.pop() {
        if node == target {
            return true;
        }
        if !visited.insert(node) {
            continue;
        }
        pending.extend(
            edges
                .iter()
                .filter_map(|(left, right)| (*left == node).then_some(*right)),
        );
    }
    false
}

fn state_path(root: &Path) -> Result<PathBuf, String> {
    let storage =
        crate::run_log_commands::resolve_enabled_storage_path(Some(root)).map_err(|error| {
            match error {
                crate::run_log_commands::PreflightFailure::Configuration(error) => {
                    error.to_string()
                }
                crate::run_log_commands::PreflightFailure::Provider(error) => error.to_string(),
            }
        })?;
    let home = env::var_os("XDG_STATE_HOME")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .or_else(|| {
            env::var_os("HOME")
                .filter(|value| !value.is_empty())
                .map(|home| PathBuf::from(home).join(".local/state"))
        })
        .ok_or_else(|| "could not resolve analysis-state root".to_owned())?;
    if !home.is_absolute() {
        return Err("analysis state home must be an absolute path".to_owned());
    }
    let home = fs::canonicalize(&home).unwrap_or(home);
    let storage_origin_id = storage.storage_origin_id();
    Ok(home
        .join("larch/analysis-state/v2")
        .join(storage.client_repo)
        .join(storage_origin_id)
        .join(STATE_RELPATH))
}

fn read_state_file(path: &Path) -> Result<Option<StateRecord>, String> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_file() => {
            return Ok(None);
        }
        Ok(_) => {}
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Ok(None),
    }
    if has_symlink_ancestor(path) {
        return Ok(None);
    }
    let bytes = fs::read(path).map_err(|error| error.to_string())?;
    let value = serde_json::from_slice(&bytes).map_err(|_| "invalid state".to_owned())?;
    Ok(state_from_value(&value))
}

fn state_snapshot(path: &Path) -> Result<StateSnapshot, String> {
    if has_symlink_ancestor(path) {
        return Err(format!(
            "refusing symlinked analysis state: {}",
            path.display()
        ));
    }
    let before = match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_file() => {
            return Err(format!(
                "analysis state is not a regular file: {}",
                path.display()
            ));
        }
        Ok(metadata) => metadata,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(StateSnapshot {
                data: None,
                digest: "missing".to_owned(),
            });
        }
        Err(error) => return Err(format!("analysis state is unreadable: {error}")),
    };
    let data = fs::read(path).map_err(|error| format!("analysis state is unreadable: {error}"))?;
    let after = fs::symlink_metadata(path)
        .map_err(|error| format!("analysis state changed while reading: {error}"))?;
    if after.file_type().is_symlink() || !after.is_file() || !same_state_metadata(&before, &after) {
        return Err(format!(
            "analysis state changed while reading: {}",
            path.display()
        ));
    }
    Ok(StateSnapshot {
        digest: format!("{:x}", Sha256::digest(&data)),
        data: Some(data),
    })
}

fn same_state_metadata(before: &fs::Metadata, after: &fs::Metadata) -> bool {
    if before.len() != after.len() || before.modified().ok() != after.modified().ok() {
        return false;
    }
    #[cfg(unix)]
    {
        before.dev() == after.dev()
            && before.ino() == after.ino()
            && before.mtime() == after.mtime()
            && before.mtime_nsec() == after.mtime_nsec()
    }
    #[cfg(not(unix))]
    {
        true
    }
}

fn has_symlink_ancestor(path: &Path) -> bool {
    let mut current = path.parent();
    while let Some(candidate) = current {
        if fs::symlink_metadata(candidate).is_ok_and(|metadata| refused_symlink(&metadata)) {
            return true;
        }
        current = candidate.parent();
    }
    false
}

fn refused_symlink(metadata: &fs::Metadata) -> bool {
    if !metadata.file_type().is_symlink() {
        return false;
    }
    #[cfg(unix)]
    {
        metadata.uid() != 0
    }
    #[cfg(not(unix))]
    {
        true
    }
}

fn state_from_value(value: &Value) -> Option<StateRecord> {
    let object = value.as_object()?;
    let version = scalar_string(object.get("schema_version")?)?;
    if version != "1" && version != "2" {
        return None;
    }
    let run_date = scalar_string(object.get("run_date")?)?;
    let repo = scalar_string(object.get("repo")?)?;
    if run_date.is_empty() || repo.is_empty() {
        return None;
    }
    let proposals = if version == "2" {
        object
            .get("proposals")
            .and_then(Value::as_array)?
            .iter()
            .map(|proposal| proposal_from_value(proposal, None))
            .collect::<Option<Vec<_>>>()?
    } else {
        Vec::new()
    };
    let mut ids = HashSet::new();
    if proposals
        .iter()
        .any(|proposal| !ids.insert(proposal.id.clone()))
    {
        return None;
    }
    Some(StateRecord {
        run_date,
        repo,
        search: object
            .get("search")
            .and_then(scalar_string)
            .unwrap_or_default(),
        state: object
            .get("state")
            .and_then(scalar_string)
            .unwrap_or_default(),
        selected_count: int_field(object.get("selected_count"), 0),
        highest: int_field(object.get("highest_closed_issue_number_scanned"), 0),
        scan_started_at: object
            .get("scan_started_at")
            .and_then(scalar_string)
            .filter(|value| !value.is_empty()),
        proposals,
    })
}

fn scalar_string(value: &Value) -> Option<String> {
    match value {
        Value::String(value) => Some(value.clone()),
        Value::Number(value) => Some(value.to_string()),
        Value::Bool(value) => Some(if *value { "True" } else { "False" }.to_owned()),
        Value::Null => Some(String::new()),
        _ => None,
    }
}

fn int_field(value: Option<&Value>, default: i64) -> i64 {
    value
        .and_then(scalar_string)
        .and_then(|value| value.parse().ok())
        .unwrap_or(default)
}

fn proposal_from_value(value: &Value, root: Option<&Path>) -> Option<Proposal> {
    let object = value.as_object()?;
    let id = object.get("id").and_then(scalar_string)?;
    let kind = object.get("type").and_then(scalar_string)?;
    let target = object.get("target").and_then(scalar_string)?;
    let run_date = object.get("run_date").and_then(scalar_string)?;
    let status = object.get("status").and_then(scalar_string)?;
    let filed_issue = match object.get("filed_issue")? {
        Value::Null => None,
        Value::Number(number) => Some(number.as_i64().filter(|value| *value > 0)?),
        _ => return None,
    };
    if !PROPOSAL_ID.is_match(&id)
        || !matches!(
            kind.as_str(),
            "lint" | "invariant" | "guideline" | "hook" | "test" | "fix"
        )
        || !matches!(
            status.as_str(),
            "proposed" | "adopted" | "pending" | "orphaned"
        )
        || !valid_date(&run_date)
        || !valid_target(&kind, &target, root)
    {
        return None;
    }
    Some(Proposal {
        id,
        kind,
        target,
        run_date,
        status,
        filed_issue,
    })
}

fn valid_date(value: &str) -> bool {
    if value.is_empty() {
        return false;
    }
    if value.contains('T') {
        DateTime::parse_from_rfc3339(value).is_ok()
            || DateTime::parse_from_rfc3339(&format!("{}+00:00", value.trim_end_matches('Z')))
                .is_ok()
    } else {
        NaiveDate::parse_from_str(value, "%Y-%m-%d").is_ok()
    }
}

fn valid_target(kind: &str, target: &str, root: Option<&Path>) -> bool {
    if kind == "fix" {
        return target
            .strip_prefix("fix:")
            .is_some_and(|value| FIX_TOKEN.is_match(value));
    }
    if kind == "hook" {
        return target
            .strip_prefix("hook:")
            .is_some_and(|value| !value.is_empty() && !value.contains(['\r', '\n']));
    }
    if matches!(kind, "lint" | "test")
        && let Some(value) = target.strip_prefix("check:")
    {
        if value.matches('#').count() != 1 {
            return false;
        }
        let (path, symbol) = value.split_once('#').expect("one check fragment separator");
        return valid_relative_path(path, &[], root) && CHECK_SYMBOL.is_match(symbol);
    }
    match kind {
        "lint" if target.starts_with("registration:") => {
            FIX_TOKEN.is_match(target.trim_start_matches("registration:"))
        }
        "lint" if target.starts_with("module:") => {
            valid_relative_path(target.trim_start_matches("module:"), &[".py"], root)
        }
        "invariant" | "guideline" => {
            target.matches('#').count() == 1
                && target.split_once('#').is_some_and(|(path, fragment)| {
                    !fragment.is_empty()
                        && !fragment.contains(['\r', '\n'])
                        && valid_relative_path(path, &[".md"], root)
                })
        }
        "test" => {
            let (path, separator, symbol) = target
                .split_once("::")
                .map_or((target, false, ""), |(path, symbol)| (path, true, symbol));
            let suffixes = [".py", ".rs"];
            valid_relative_path(path, &suffixes, root)
                && (!separator
                    || (Path::new(path)
                        .extension()
                        .is_some_and(|extension| extension.eq_ignore_ascii_case("py"))
                        && TEST_NAME.is_match(symbol))
                    || (Path::new(path)
                        .extension()
                        .is_some_and(|extension| extension.eq_ignore_ascii_case("rs"))
                        && CHECK_SYMBOL.is_match(symbol)))
        }
        _ => false,
    }
}

fn valid_relative_path(value: &str, suffixes: &[&str], root: Option<&Path>) -> bool {
    !value.is_empty()
        && !value.contains('\\')
        && !Path::new(value).is_absolute()
        && value
            .split('/')
            .all(|part| !part.is_empty() && !matches!(part, "." | ".."))
        && (suffixes.is_empty() || suffixes.iter().any(|suffix| value.ends_with(suffix)))
        && root.is_none_or(|root| path_under(root.join(value), root))
}

fn read_proposals(path: &Path, root: &Path) -> Result<Vec<Proposal>, String> {
    let text =
        fs::read_to_string(path).map_err(|error| format!("cannot read proposals file: {error}"))?;
    let mut proposals: Vec<Proposal> = Vec::new();
    let mut positions: BTreeMap<String, usize> = BTreeMap::new();
    for (line_number, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let value: Value = serde_json::from_str(line)
            .map_err(|error| format!("invalid proposal JSONL line {}: {error}", line_number + 1))?;
        let proposal = proposal_from_value(&value, Some(root))
            .ok_or_else(|| "invalid proposal record".to_owned())?;
        if let Some(index) = positions.get(&proposal.id).copied() {
            let prior = &proposals[index];
            if (
                prior.kind.as_str(),
                prior.target.as_str(),
                prior.run_date.as_str(),
            ) != (
                proposal.kind.as_str(),
                proposal.target.as_str(),
                proposal.run_date.as_str(),
            ) {
                return Err(format!(
                    "conflicting stable proposal content for {}",
                    proposal.id
                ));
            }
            if prior.filed_issue.is_some()
                && proposal.filed_issue.is_some()
                && prior.filed_issue != proposal.filed_issue
            {
                return Err(format!("conflicting filed issues for {}", proposal.id));
            }
            proposals[index] = Proposal {
                id: prior.id.clone(),
                kind: prior.kind.clone(),
                target: prior.target.clone(),
                run_date: prior.run_date.clone(),
                status: if prior.status == "proposed" {
                    proposal.status
                } else {
                    prior.status.clone()
                },
                filed_issue: proposal.filed_issue.or(prior.filed_issue),
            };
        } else {
            positions.insert(proposal.id.clone(), proposals.len());
            proposals.push(proposal);
        }
    }
    Ok(proposals)
}

fn reconcile_proposals(
    prior: &[Proposal],
    residuals: &[Proposal],
    base: &[Proposal],
) -> Result<Vec<Proposal>, String> {
    let base_status: BTreeMap<_, _> = base
        .iter()
        .map(|proposal| (proposal.id.as_str(), proposal.status.as_str()))
        .collect();
    let mut out = prior.to_vec();
    let mut positions: BTreeMap<String, usize> = out
        .iter()
        .enumerate()
        .map(|(index, proposal)| (proposal.id.clone(), index))
        .collect();
    for residual in residuals {
        let Some(index) = positions.get(&residual.id).copied() else {
            positions.insert(residual.id.clone(), out.len());
            out.push(residual.clone());
            continue;
        };
        let historical = &out[index];
        if (
            historical.kind.as_str(),
            historical.target.as_str(),
            historical.run_date.as_str(),
        ) != (
            residual.kind.as_str(),
            residual.target.as_str(),
            residual.run_date.as_str(),
        ) {
            return Err(format!(
                "conflicting stable proposal content for {}",
                residual.id
            ));
        }
        if historical.filed_issue.is_some()
            && residual.filed_issue.is_some()
            && historical.filed_issue != residual.filed_issue
        {
            return Err(format!("conflicting filed issues for {}", residual.id));
        }
        let status = if base_status
            .get(residual.id.as_str())
            .is_some_and(|base| *base == historical.status)
        {
            residual.status.clone()
        } else {
            historical.status.clone()
        };
        out[index] = Proposal {
            id: historical.id.clone(),
            kind: historical.kind.clone(),
            target: historical.target.clone(),
            run_date: historical.run_date.clone(),
            status,
            filed_issue: historical.filed_issue.or(residual.filed_issue),
        };
    }
    Ok(out)
}

fn write_state_locked(
    path: &Path,
    mut next: StateRecord,
    proposals_file: Option<&Path>,
    base_file: Option<&Path>,
    root: &Path,
    expected_snapshot: &StateSnapshot,
) -> Result<(StateRecord, String), String> {
    let parent = path
        .parent()
        .ok_or_else(|| "state path has no parent".to_owned())?;
    ensure_directory_chain(parent).map_err(|error| error.to_string())?;
    #[cfg(unix)]
    fs::set_permissions(parent, fs::Permissions::from_mode(0o700))
        .map_err(|error| error.to_string())?;
    let _lock = lock_state(path)?;
    let current_snapshot = state_snapshot(path)?;
    if current_snapshot.digest != expected_snapshot.digest {
        return Err(format!(
            "analysis state changed concurrently: {}",
            path.display()
        ));
    }
    let existing = current_snapshot
        .data
        .as_deref()
        .and_then(|data| serde_json::from_slice(data).ok())
        .and_then(|value| state_from_value(&value));
    if current_snapshot.data.is_some() && existing.is_none() {
        return Err("existing state marker is invalid or unsupported".to_owned());
    }
    if let Some(proposals_path) = proposals_file {
        let residuals = read_proposals(proposals_path, root)?;
        next.proposals = if let Some(existing) = &existing {
            let base = match base_file {
                Some(path) => read_proposals(path, root)?,
                None => Vec::new(),
            };
            reconcile_proposals(&existing.proposals, &residuals, &base)?
        } else {
            residuals
        };
    } else if existing
        .as_ref()
        .is_some_and(|state| !state.proposals.is_empty())
    {
        return Err("--proposals-file is required to preserve proposal history".to_owned());
    }
    let text = serialize_state(&next)?;
    private_atomic_write(path, &text, parent).map_err(|error| error.to_string())?;
    let digest = format!("{:x}", Sha256::digest(text.as_bytes()));
    Ok((next, digest))
}

fn lock_state(path: &Path) -> Result<Flock<fs::File>, String> {
    let lock = path.with_file_name(format!(
        ".{}.lock",
        path.file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("state")
    ));
    if fs::symlink_metadata(&lock).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(format!("could not lock analysis state: {}", path.display()));
    }
    let mut options = OpenOptions::new();
    options.read(true).write(true).create(true);
    #[cfg(unix)]
    {
        options.mode(0o600).custom_flags(nix::libc::O_NOFOLLOW);
    }
    let file = options
        .open(&lock)
        .map_err(|error| format!("could not lock analysis state: {error}"))?;
    if !file
        .metadata()
        .map_err(|error| format!("could not lock analysis state: {error}"))?
        .is_file()
    {
        return Err(format!("could not lock analysis state: {}", path.display()));
    }
    #[cfg(unix)]
    fs::set_permissions(&lock, fs::Permissions::from_mode(0o600))
        .map_err(|error| format!("could not lock analysis state: {error}"))?;
    #[cfg(unix)]
    Flock::lock(file, FlockArg::LockExclusive)
        .map_err(|(_file, error)| format!("could not lock analysis state: {error}"))
}

fn serialize_state(state: &StateRecord) -> Result<String, String> {
    let mut object = Map::new();
    object.insert("schema_version".to_owned(), Value::from(2));
    object.insert("run_date".to_owned(), Value::from(state.run_date.clone()));
    object.insert("repo".to_owned(), Value::from(state.repo.clone()));
    object.insert("search".to_owned(), Value::from(state.search.clone()));
    object.insert("state".to_owned(), Value::from(state.state.clone()));
    object.insert(
        "selected_count".to_owned(),
        Value::from(state.selected_count),
    );
    object.insert(
        "highest_closed_issue_number_scanned".to_owned(),
        Value::from(state.highest),
    );
    object.insert(
        "proposals".to_owned(),
        Value::Array(state.proposals.iter().map(proposal_value).collect()),
    );
    if let Some(scan_started_at) = &state.scan_started_at {
        object.insert(
            "scan_started_at".to_owned(),
            Value::from(scan_started_at.clone()),
        );
    }
    let mut value = ascii_json(
        &serde_json::to_string_pretty(&Value::Object(object)).map_err(|error| error.to_string())?,
    );
    value.push('\n');
    Ok(value)
}

fn proposal_value(proposal: &Proposal) -> Value {
    let mut object = Map::new();
    object.insert("id".to_owned(), Value::from(proposal.id.clone()));
    object.insert("type".to_owned(), Value::from(proposal.kind.clone()));
    object.insert("target".to_owned(), Value::from(proposal.target.clone()));
    object.insert(
        "run_date".to_owned(),
        Value::from(proposal.run_date.clone()),
    );
    object.insert("status".to_owned(), Value::from(proposal.status.clone()));
    object.insert(
        "filed_issue".to_owned(),
        proposal.filed_issue.map_or(Value::Null, Value::from),
    );
    Value::Object(object)
}

#[cfg(test)]
#[path = "../tests/support/learn_from_bugs_commands_unit.rs"]
mod tests;
