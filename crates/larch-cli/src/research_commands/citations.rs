//! The `research validate-citations` orchestration, sidecar, and credibility.
//!
//! Byte parity with the retired Python covers the `SUMMARY=` grammar, the
//! degraded and no-op sidecar notices, the sorted ledger rows, the advisory
//! credibility block, and the always-`rc 0`-or-`rc 2` exit contract.

use std::{
    collections::BTreeMap,
    ffi::OsString,
    fmt::Write as _,
    path::Path,
    process::ExitCode,
    sync::LazyLock,
};

use larch_core::split_text_lines;
use regex::Regex;

use super::{
    CitationLedgerRow, FetchResult, FetchSeams, UrlParts, VALID_DOI_RE, check_fileline, diagnostic,
    extract_dois, extract_filelines, extract_urls, fetch_url, parallel_fetch_results,
    write_text_atomic,
};
use crate::argparse_compat::parse;

static EXCERPT_WS_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\s+").expect("excerpt ws regex"));
static POSITIVE_INT_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[0-9]+$").expect("positive-int regex"));

/// Host suffixes that the advisory credibility tier treats as reputable.
const CREDIBILITY_SUFFIXES: &[&str] = &[
    ".wikipedia.org",
    ".arxiv.org",
    ".acm.org",
    ".ietf.org",
    ".python.org",
    ".rust-lang.org",
    ".doi.org",
    ".github.com",
    ".githubusercontent.com",
    ".anthropic.com",
];

/// A validate-citations request: inputs, limits, and the wire output path.
pub struct ValidateRequest<'a> {
    pub report: &'a Path,
    pub output: &'a Path,
    pub tmpdir: &'a Path,
    pub budget_seconds: u64,
    pub per_fetch_timeout: u64,
    pub max_claims: usize,
}

/// The running PASS/FAIL/UNKNOWN tallies plus the total claim count.
#[derive(Clone, Copy, Default)]
struct Counts {
    pass: usize,
    fail: usize,
    unknown: usize,
    total: usize,
}

impl Counts {
    fn record(&mut self, status: &str) {
        match status {
            "PASS" => self.pass += 1,
            "FAIL" => self.fail += 1,
            _unknown => self.unknown += 1,
        }
    }
}

/// Validate every citation in `request.report`, writing the sidecar and summary.
///
/// `fetcher` and `git_root` are seams: production passes `None` for both, while
/// tests inject a deterministic fetcher and a known repository root to exercise
/// the full status taxonomy offline. Returns `(pass, fail, unknown, total)`.
pub fn validate_citations(
    request: &ValidateRequest<'_>,
    fetcher: Option<&(dyn Fn(&str) -> FetchResult + Sync)>,
    git_root: Option<&Path>,
) -> (usize, usize, usize, usize) {
    let Ok(metadata) = std::fs::metadata(request.report) else {
        return degraded(request.output, &unreadable_notice(request.report));
    };
    if !metadata.is_file() {
        return degraded(request.output, &unreadable_notice(request.report));
    }
    let _ignored = std::fs::create_dir_all(request.tmpdir);
    let Ok(text) = std::fs::read_to_string(request.report) else {
        return degraded(request.output, &unreadable_notice(request.report));
    };
    validate_text(request, &text, fetcher, git_root)
}

/// Refuse-and-return through the degraded status sidecar and a zero summary.
fn degraded(output: &Path, notice: &str) -> (usize, usize, usize, usize) {
    let _ignored = write_text_atomic(output, &sidecar_status(notice));
    emit_summary(Counts::default());
    (0, 0, 0, 0)
}

fn unreadable_notice(report: &Path) -> String {
    format!("input report not readable: `{}`", report.display())
}

/// Extract, truncate, fetch, classify, and render one report's citations.
fn validate_text(
    request: &ValidateRequest<'_>,
    text: &str,
    fetcher: Option<&(dyn Fn(&str) -> FetchResult + Sync)>,
    git_root: Option<&Path>,
) -> (usize, usize, usize, usize) {
    let claims = Claims::extract(text, request.max_claims);
    if claims.is_empty() {
        let _ignored =
            write_text_atomic(request.output, &sidecar_no_claims(text.len(), split_text_lines(text).len()));
        emit_summary(Counts::default());
        return (0, 0, 0, 0);
    }
    let fetch_results = run_fetches(request, &claims, fetcher);
    let ledger = build_ledger(&claims, &fetch_results, git_root);
    write_and_summarize(request, text, &claims, &ledger)
}

/// The extracted, order-preserving, capped claim lists for one report.
struct Claims {
    urls: Vec<String>,
    dois: Vec<String>,
    filelines: Vec<String>,
    truncated: bool,
}

impl Claims {
    fn extract(text: &str, max_claims: usize) -> Self {
        let mut urls = extract_urls(text);
        let mut dois = extract_dois(text);
        let mut filelines = extract_filelines(text);
        let raw_total = urls.len() + dois.len() + filelines.len();
        let truncated = raw_total > max_claims;
        let mut remaining = max_claims;
        urls.truncate(remaining);
        remaining = remaining.saturating_sub(urls.len());
        dois.truncate(remaining);
        remaining = remaining.saturating_sub(dois.len());
        filelines.truncate(remaining);
        Self {
            urls,
            dois,
            filelines,
            truncated,
        }
    }

    const fn is_empty(&self) -> bool {
        self.urls.is_empty() && self.dois.is_empty() && self.filelines.is_empty()
    }
}

/// Fetch every URL and valid DOI target, or an empty map when there are none.
fn run_fetches(
    request: &ValidateRequest<'_>,
    claims: &Claims,
    fetcher: Option<&(dyn Fn(&str) -> FetchResult + Sync)>,
) -> BTreeMap<String, FetchResult> {
    let mut targets: BTreeMap<String, String> = BTreeMap::new();
    for url in &claims.urls {
        targets.insert(url.clone(), url.clone());
    }
    for doi in &claims.dois {
        if VALID_DOI_RE.is_match(doi) {
            targets.insert(format!("doi:{doi}"), format!("https://doi.org/{doi}"));
        }
    }
    if targets.is_empty() {
        return BTreeMap::new();
    }
    let per_fetch = request.per_fetch_timeout;
    let real = move |target: &str| fetch_url(target, per_fetch, &FetchSeams::default());
    let fetcher: &(dyn Fn(&str) -> FetchResult + Sync) = fetcher.unwrap_or(&real);
    parallel_fetch_results(&targets, request.budget_seconds, per_fetch, fetcher)
}

/// The classified rows and the credibility hosts gathered while building them.
struct Ledger {
    rows: Vec<CitationLedgerRow>,
    counts: Counts,
    hosts: Vec<String>,
}

/// Classify every claim into a ledger row, tallying counts and hosts.
fn build_ledger(
    claims: &Claims,
    fetch_results: &BTreeMap<String, FetchResult>,
    git_root: Option<&Path>,
) -> Ledger {
    let mut ledger = Ledger {
        rows: Vec::new(),
        counts: Counts::default(),
        hosts: Vec::new(),
    };
    for url in &claims.urls {
        if let Some(host) = url_host(url) {
            ledger.hosts.push(host);
        }
        let result = fetch_results
            .get(url)
            .cloned()
            .unwrap_or_else(|| FetchResult::new("UNKNOWN", "timeout"));
        ledger.push(url, "url", &result);
    }
    for doi in &claims.dois {
        classify_doi(&mut ledger, doi, fetch_results);
    }
    for cite in &claims.filelines {
        let result = check_fileline(cite, git_root);
        ledger.push(cite, "file-line", &result);
    }
    ledger.counts.total = ledger.rows.len();
    ledger
}

impl Ledger {
    fn push(&mut self, claim: &str, claim_type: &str, result: &FetchResult) {
        self.counts.record(result.status());
        self.rows.push(CitationLedgerRow::new(claim, claim_type, result));
    }
}

impl FetchResult {
    /// The bare status word (`PASS`, `FAIL`, or `UNKNOWN`).
    fn status(&self) -> &str {
        &self.status
    }

    /// The reason detail, empty for a passing result.
    fn reason(&self) -> &str {
        &self.reason
    }
}

/// Classify one DOI, mapping a resolved or redirected fetch to PASS.
fn classify_doi(ledger: &mut Ledger, doi: &str, fetch_results: &BTreeMap<String, FetchResult>) {
    if !VALID_DOI_RE.is_match(doi) {
        ledger.push(doi, "doi", &FetchResult::new("FAIL", "doi-syntax"));
        return;
    }
    ledger.hosts.push("doi.org".to_owned());
    let raw = fetch_results
        .get(&format!("doi:{doi}"))
        .cloned()
        .unwrap_or_else(|| FetchResult::new("UNKNOWN", "timeout"));
    if raw.status() == "PASS" || raw.token() == "UNKNOWN(redirect-not-followed)" {
        ledger.push(doi, "doi", &FetchResult::pass());
    } else {
        ledger.push(doi, "doi", &FetchResult::new("UNKNOWN", "doi-unresolved"));
    }
}

/// Write the ledger sidecar, emit the summary, and return the counts.
fn write_and_summarize(
    request: &ValidateRequest<'_>,
    text: &str,
    claims: &Claims,
    ledger: &Ledger,
) -> (usize, usize, usize, usize) {
    let truncation = if claims.truncated {
        format!(
            "claim count exceeded `--max-claims={}`. Excess claims were dropped from the ledger; consider re-running with `--max-claims` raised.",
            request.max_claims
        )
    } else {
        String::new()
    };
    let sidecar = sidecar_ledger(&SidecarLedger {
        synth_bytes: text.len(),
        synth_lines: split_text_lines(text).len(),
        counts: ledger.counts,
        rows: &ledger.rows,
        truncation: &truncation,
        hosts: &ledger.hosts,
    });
    let _ignored = write_text_atomic(request.output, &sidecar);
    emit_summary(ledger.counts);
    (
        ledger.counts.pass,
        ledger.counts.fail,
        ledger.counts.unknown,
        ledger.counts.total,
    )
}

impl CitationLedgerRow {
    fn new(claim: &str, claim_type: &str, result: &FetchResult) -> Self {
        Self {
            claim: claim.to_owned(),
            claim_type: claim_type.to_owned(),
            status: result.status().to_owned(),
            reason: result.reason().to_owned(),
        }
    }
}

fn emit_summary(counts: Counts) {
    emit_kv_line(&format!(
        "SUMMARY=PASS={} FAIL={} UNKNOWN={} TOTAL={}",
        counts.pass, counts.fail, counts.unknown, counts.total
    ));
}

/// Emit one already-formatted contract line, mirroring Python `emit`.
fn emit_kv_line(line: &str) {
    println!("{line}");
}

/// The public `https` host of a URL, or `None` for any other scheme.
fn url_host(url: &str) -> Option<String> {
    UrlParts::parse(url).map(|parts| parts.host)
}

// ---------------------------------------------------------------------------
// sidecar rendering
// ---------------------------------------------------------------------------

/// Render the degraded/notice sidecar shown when no claims can be validated.
fn sidecar_status(status: &str) -> String {
    format!(
        "## Citation Validation\n\n\
**Validator**: validate-citations.sh v1\n\
**Status**: {status}\n\n\
No claims were extracted; Step 3 splice will display this notice.\n"
    )
}

/// Render the sidecar shown when a readable report has no citable provenance.
fn sidecar_no_claims(synth_bytes: usize, synth_lines: usize) -> String {
    format!(
        "## Citation Validation\n\n\
**Validator**: validate-citations.sh v1\n\
**Synthesis**: {synth_bytes} bytes, {synth_lines} lines\n\
**Claims extracted**: 0\n\
**Status counts**: 0 PASS · 0 FAIL · 0 UNKNOWN\n\n\
_No citable provenance (URLs, DOIs, file:line) found in the synthesis. Citation validation is a no-op for this report._\n"
    )
}

/// The bundled inputs of the full ledger sidecar.
struct SidecarLedger<'a> {
    synth_bytes: usize,
    synth_lines: usize,
    counts: Counts,
    rows: &'a [CitationLedgerRow],
    truncation: &'a str,
    hosts: &'a [String],
}

/// Render the full ledger sidecar with sorted rows and the credibility block.
fn sidecar_ledger(ledger: &SidecarLedger<'_>) -> String {
    let mut rows: Vec<&CitationLedgerRow> = ledger.rows.iter().collect();
    rows.sort_by(|left, right| {
        (
            &left.claim_type,
            sanitize_excerpt(&left.claim),
            &left.status,
            &left.reason,
        )
            .cmp(&(
                &right.claim_type,
                sanitize_excerpt(&right.claim),
                &right.status,
                &right.reason,
            ))
    });
    let mut body = String::new();
    for row in rows {
        let _ = writeln!(
            body,
            "| `{}` | {} | {} | {} |  |",
            sanitize_excerpt(&row.claim),
            row.claim_type,
            row.status,
            row.reason
        );
    }
    let notice = if ledger.truncation.is_empty() {
        String::new()
    } else {
        format!("\n_Note: {}_\n", ledger.truncation)
    };
    format!(
        "## Citation Validation\n\n\
**Validator**: validate-citations.sh v1\n\
**Synthesis**: {} bytes, {} lines\n\
**Claims extracted**: {}\n\
**Status counts**: {} PASS · {} FAIL · {} UNKNOWN\n\n\
| Claim | Type | Status | Reason | Cited by |\n\
|---|---|---|---|---|\n\
{body}{notice}{credibility}",
        ledger.synth_bytes,
        ledger.synth_lines,
        ledger.counts.total,
        ledger.counts.pass,
        ledger.counts.fail,
        ledger.counts.unknown,
        credibility = render_credibility_block(ledger.hosts),
    )
}

/// Collapse whitespace, drop pipes, and clip one claim to 80 display columns.
fn sanitize_excerpt(text: &str) -> String {
    let replaced = text.replace('|', " ");
    let collapsed = EXCERPT_WS_RE.replace_all(&replaced, " ");
    let value = collapsed.trim();
    let chars: Vec<char> = value.chars().collect();
    if chars.len() > 80 {
        let head: String = chars[..77].iter().collect();
        format!("{head}...")
    } else {
        value.to_owned()
    }
}

/// The advisory-only credibility tier of one host.
fn credibility_tier(host: &str) -> &'static str {
    let lowered = host.to_lowercase();
    if matches!(
        lowered.as_str(),
        "arxiv.org" | "doi.org" | "github.com" | "anthropic.com"
    ) {
        return "allow";
    }
    if CREDIBILITY_SUFFIXES
        .iter()
        .any(|suffix| lowered.ends_with(suffix))
    {
        "allow"
    } else {
        "unknown"
    }
}

/// Render the advisory credibility `<details>` block, or `""` when empty.
fn render_credibility_block(hosts: &[String]) -> String {
    let mut unique: Vec<String> = hosts
        .iter()
        .filter(|host| !host.is_empty())
        .map(|host| host.to_lowercase())
        .collect();
    unique.sort();
    unique.dedup();
    if unique.is_empty() {
        return String::new();
    }
    let mut rows = String::new();
    for host in unique {
        let tier = credibility_tier(&host);
        let note = if tier == "allow" {
            "well-known reputable origin"
        } else {
            "no allow-list entry; classification heuristic only — NOT a FAIL signal"
        };
        let _ = writeln!(rows, "| {host} | {tier} | {note} |");
    }
    format!(
        "\n\n<details><summary>Domain credibility (advisory only)</summary>\n\n\
| Domain | Tier | Notes |\n\
|---|---|---|\n\
{rows}</details>"
    )
}

// ---------------------------------------------------------------------------
// CLI entrypoint
// ---------------------------------------------------------------------------

const USAGE: &str = "Usage: validate-citations --report <path> --output <path> --tmpdir <path> [--budget-seconds N] [--per-fetch-timeout N] [--max-claims N]";

/// Execute `research validate-citations`.
#[must_use]
pub fn run(arguments: &[OsString]) -> ExitCode {
    if super::is_help(arguments) {
        println!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    let options = &[
        "--report",
        "--output",
        "--tmpdir",
        "--budget-seconds",
        "--per-fetch-timeout",
        "--max-claims",
    ];
    let parsed = parse(arguments, options, 0);
    let (report, output, tmpdir) = (
        parsed.value("--report"),
        parsed.value("--output"),
        parsed.value("--tmpdir"),
    );
    let (Some(report), Some(output), Some(tmpdir)) = (report, output, tmpdir) else {
        diagnostic(USAGE);
        return ExitCode::from(2);
    };
    if parsed.error().is_some() {
        diagnostic(USAGE);
        return ExitCode::from(2);
    }
    let output_path = Path::new(output);
    let limits = match Limits::parse(&parsed) {
        Ok(limits) => limits,
        Err(message) => {
            let _ignored = write_text_atomic(
                output_path,
                &sidecar_status(&format!("invalid argument ({message}); sidecar is degraded")),
            );
            emit_summary(Counts::default());
            diagnostic(&format!("validate-citations: {message}"));
            return ExitCode::from(2);
        }
    };
    let request = ValidateRequest {
        report: Path::new(report),
        output: output_path,
        tmpdir: Path::new(tmpdir),
        budget_seconds: limits.budget_seconds,
        per_fetch_timeout: limits.per_fetch_timeout,
        max_claims: limits.max_claims,
    };
    let _counts = validate_citations(&request, None, None);
    ExitCode::SUCCESS
}

/// The validated positive-integer limits parsed from the command line.
struct Limits {
    budget_seconds: u64,
    per_fetch_timeout: u64,
    max_claims: usize,
}

impl Limits {
    fn parse(parsed: &crate::argparse_compat::ParsedCommandLine) -> Result<Self, String> {
        let budget = positive_int(parsed, "--budget-seconds", "300")?;
        let per_fetch = positive_int(parsed, "--per-fetch-timeout", "10")?;
        let max_claims = positive_int(parsed, "--max-claims", "200")?;
        Ok(Self {
            budget_seconds: budget,
            per_fetch_timeout: per_fetch,
            max_claims: usize::try_from(max_claims).unwrap_or(usize::MAX),
        })
    }
}

/// Parse one positive-integer option, rendering Python's refusal message.
fn positive_int(
    parsed: &crate::argparse_compat::ParsedCommandLine,
    flag: &str,
    default: &str,
) -> Result<u64, String> {
    let value = parsed
        .value(flag)
        .and_then(std::ffi::OsStr::to_str)
        .unwrap_or(default)
        .to_owned();
    let parsed_value = value.parse::<u64>().ok().filter(|number| *number > 0);
    match parsed_value {
        Some(number) if POSITIVE_INT_RE.is_match(&value) => Ok(number),
        _invalid => Err(format!("{flag} must be a positive integer (got: {value})")),
    }
}
