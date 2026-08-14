//! Rust owner for the four `/research` preparation commands.
//!
//! `banner`, `run-planner`, `render-findings-batch`, and `validate-citations`
//! were Python (`larch.research.research`) until #8499 made Rust their single
//! owner. The commands preserve the retired stdout/stderr/exit-code and wire-file
//! contracts byte-for-byte: the banner literal, the `COUNT=`/`OUTPUT=`/`REASON=`/
//! `SUMMARY=` grammar, the planner output file, the findings issue-batch payload,
//! and the citation-validation sidecar.
//!
//! `validate-citations` is the network-facing one. Its fetch path keeps every
//! Python SSRF guard: it refuses non-`https` URLs and private/loopback/
//! link-local/CGNAT/reserved/unspecified hosts before any lookup, resolves the
//! hostname, refuses again if any resolved address is private, then connects to
//! the pinned public address while preserving the hostname for SNI and the
//! `Host` header. The resolver and the connector are seams so tests exercise the
//! full FAIL/UNKNOWN/PASS taxonomy offline without touching the network.

use std::{
    collections::BTreeMap,
    ffi::OsString,
    fs,
    net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr, ToSocketAddrs as _},
    path::{Path, PathBuf},
    process::{Command, ExitCode},
    sync::{LazyLock, mpsc},
    thread,
    time::{Duration, Instant},
};

use larch_core::{emit_kv, file_line_regex, split_text_lines, universal_newlines};
use regex::Regex;

use crate::argparse_compat::parse;

mod render;

pub use render::render_findings_issue_batch;

/// The reduced-diversity banner literal, with `<N_FALLBACK>` left as a slot.
const BANNER_TEMPLATE: &str = "**⚠ Reduced lane diversity: <N_FALLBACK> of 4 external research lanes ran as Claude-fallback. The model-family heterogeneity claim does not hold for this run.**";

static URL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"https?://[A-Za-z0-9._~:/?#@!$&'()*+,;=%-]+").expect("static URL regex")
});
static DOI_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\b10\.[0-9]{4,9}/[A-Za-z0-9._;()/:-]+").expect("static DOI regex")
});
static VALID_DOI_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^10\.[0-9]{4,9}/[A-Za-z0-9._;()/:-]+$").expect("static valid-DOI regex")
});
static BANNER_LINE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^RESEARCH_[A-Z_]+_STATUS=fallback_").expect("static banner regex"));
static FILELINE_RE: LazyLock<Regex> = LazyLock::new(|| {
    let any = file_line_regex("any-re").expect("any-re owner");
    let extensionless = file_line_regex("extensionless-re").expect("extensionless-re owner");
    Regex::new(&format!("{any}|{extensionless}")).expect("composed file-line regex")
});
static FILELINE_KEEP_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"\.[A-Za-z]+(:[0-9]+(-[0-9]+)?)?$|^(Makefile|Dockerfile|GNUmakefile)(:[0-9]+(-[0-9]+)?)?$",
    )
    .expect("static file-line keep regex")
});
static FILELINE_CITE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^([^:]+):([0-9]+)(-([0-9]+))?$").expect("static file-line cite regex"));
static BULLET_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ \t]*[-*][ \t]+").expect("static bullet regex"));

/// One HTTP/DOI/file-line classification: a status plus its reason detail.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FetchResult {
    status: String,
    reason: String,
}

impl FetchResult {
    /// A passing classification carries no reason.
    #[must_use]
    pub fn pass() -> Self {
        Self {
            status: "PASS".to_owned(),
            reason: String::new(),
        }
    }

    /// A `status` classification (`FAIL`/`UNKNOWN`) with its `reason` detail.
    #[must_use]
    pub fn new(status: &str, reason: &str) -> Self {
        Self {
            status: status.to_owned(),
            reason: reason.to_owned(),
        }
    }

    /// Render `PASS` or `STATUS(reason)`, the ledger token Python emitted.
    #[must_use]
    pub fn token(&self) -> String {
        if self.status == "PASS" {
            "PASS".to_owned()
        } else {
            format!("{}({})", self.status, self.reason)
        }
    }
}

/// One rendered citation-ledger row before the sidecar sorts and prints it.
#[derive(Clone, Debug)]
struct CitationLedgerRow {
    claim: String,
    claim_type: String,
    status: String,
    reason: String,
}

/// Write `text` to `path` atomically via a sibling temp file and a rename.
///
/// The rename gives readers either the old or the new bytes, never a partial
/// file, and the created file keeps the process umask's default mode, matching
/// the retired Python `larch_io.atomic_write` call that passed no explicit mode.
fn write_text_atomic(path: &Path, text: &str) -> std::io::Result<()> {
    if let Some(parent) = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
    {
        fs::create_dir_all(parent)?;
    }
    let file_name = path
        .file_name()
        .map_or_else(|| ".tmp".to_owned(), |name| name.to_string_lossy().into_owned());
    let temp = path.with_file_name(format!(".{file_name}.{}.tmp", std::process::id()));
    fs::write(&temp, text)?;
    match fs::rename(&temp, path) {
        Ok(()) => Ok(()),
        Err(error) => {
            let _ignored = fs::remove_file(&temp);
            Err(error)
        }
    }
}

/// Read a file the way Python `Path.read_text(errors="replace")` did.
///
/// The retired Python decoded UTF-8 lossily and opened in universal-newline
/// mode, so a report carrying a stray non-UTF-8 byte or `\r\n` endings still
/// validated rather than being refused as unreadable. Reading raw bytes,
/// decoding lossily, and translating newlines preserves that contract; the
/// result is byte-identical to `read_to_string` for UTF-8, `\n`-only input.
fn read_text_lossy(path: &Path) -> std::io::Result<String> {
    let bytes = fs::read(path)?;
    let decoded = String::from_utf8_lossy(&bytes);
    Ok(universal_newlines(&decoded).into_owned())
}

/// Print one contract-stream line to stdout, matching Python `logging_util.emit`.
fn emit_line(text: &str) {
    println!("{text}");
}

/// Print one operator diagnostic to stderr, matching `logging_util.diagnostic`.
fn diagnostic(message: &str) {
    eprintln!("{message}");
}

// ---------------------------------------------------------------------------
// banner
// ---------------------------------------------------------------------------

/// Compute the reduced-diversity banner for a lane-status file.
///
/// Returns the empty string for a missing or unreadable file or when fewer than
/// one lane ran as a Claude fallback.
#[must_use]
pub fn compute_banner(path: &Path) -> String {
    let Ok(text) = read_text_lossy(path) else {
        return String::new();
    };
    let count = split_text_lines(&text)
        .into_iter()
        .filter(|line| BANNER_LINE_RE.is_match(line))
        .count();
    if count < 1 {
        return String::new();
    }
    BANNER_TEMPLATE.replace("<N_FALLBACK>", &count.to_string())
}

/// Execute `research banner`.
#[must_use]
pub fn banner(arguments: &[OsString]) -> ExitCode {
    let usage = "Usage: banner <lane-status.txt>";
    if is_help(arguments) {
        println!("{usage}");
        return ExitCode::SUCCESS;
    }
    let Some(first) = arguments.first() else {
        diagnostic("WARNING: research banner requires <lane-status.txt-path>; emitting empty banner");
        return ExitCode::SUCCESS;
    };
    let banner = compute_banner(Path::new(first));
    if !banner.is_empty() {
        emit_line(&banner);
    }
    ExitCode::SUCCESS
}

/// Return whether `-h`/`--help` appears anywhere in the raw argument vector.
fn is_help(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .any(|argument| matches!(argument.to_str(), Some("-h" | "--help")))
}

// ---------------------------------------------------------------------------
// run-planner
// ---------------------------------------------------------------------------

/// Sanitize one raw planner line: drop controls, tabs to spaces, strip a bullet.
fn sanitize_planner_line(line: &str) -> String {
    let filtered: String = line
        .chars()
        .filter(|&ch| ch == '\t' || (ch >= ' ' && ch != '\u{7f}'))
        .collect();
    let spaced = filtered.replace('\t', " ");
    BULLET_RE.replace(&spaced, "").trim().to_owned()
}

/// Turn a raw candidate file into the planner output, or a refusal reason.
///
/// Returns `(reason, exit_code)`. The `success` reason writes the questions to
/// `output` and exits `0`; every other reason writes nothing.
fn run_planner_core(raw: &Path, output: &Path) -> (&'static str, u8) {
    match fs::metadata(raw) {
        Ok(metadata) if metadata.is_file() && metadata.len() > 0 => {}
        _empty_or_missing => return ("empty_input", 1),
    }
    let parent = match output.parent() {
        Some(parent) if !parent.as_os_str().is_empty() => parent.to_path_buf(),
        _bare_filename => PathBuf::from("."),
    };
    if !parent.is_dir() {
        return ("bad_path", 2);
    }
    let Ok(text) = read_text_lossy(raw) else {
        return ("empty_input", 1);
    };
    let questions: Vec<String> = split_text_lines(&text)
        .into_iter()
        .map(sanitize_planner_line)
        .filter(|line| !line.is_empty() && line.ends_with('?'))
        .collect();
    if questions.iter().any(|question| question.contains("||")) {
        return ("delimiter_collision", 1);
    }
    if questions.len() < 2 {
        return ("count_below_minimum", 1);
    }
    if questions.len() > 4 {
        return ("count_above_maximum", 1);
    }
    let mut payload = questions.join("\n");
    payload.push('\n');
    match write_text_atomic(output, &payload) {
        Ok(()) => ("success", 0),
        Err(_error) => ("bad_path", 2),
    }
}

/// Execute `research run-planner`.
#[must_use]
pub fn run_planner(arguments: &[OsString]) -> ExitCode {
    let usage = "Usage: run-planner --raw <path> --output <path>";
    if is_help(arguments) {
        println!("{usage}");
        return ExitCode::SUCCESS;
    }
    let parsed = parse(arguments, &["--raw", "--output"], 0);
    let (Some(raw), Some(output)) = (parsed.value("--raw"), parsed.value("--output")) else {
        emit_kv("REASON", "missing_arg");
        return ExitCode::from(2);
    };
    if parsed.error().is_some() {
        emit_kv("REASON", "missing_arg");
        return ExitCode::from(2);
    }
    let output_path = Path::new(output);
    let (reason, code) = run_planner_core(Path::new(raw), output_path);
    if reason == "success" {
        let count = fs::read_to_string(output_path)
            .map(|text| split_text_lines(&text).len())
            .unwrap_or_default();
        emit_kv("COUNT", &count.to_string());
        emit_kv("OUTPUT", &output.to_string_lossy());
    } else {
        emit_kv("REASON", reason);
    }
    ExitCode::from(code)
}

// ---------------------------------------------------------------------------
// render-findings-batch
// ---------------------------------------------------------------------------

/// Execute `research render-findings-batch`.
#[must_use]
pub fn render_findings_batch(arguments: &[OsString]) -> ExitCode {
    let usage = "Usage: render-findings-batch --report <path> --output <path> --research-question-file <path> --branch <value> --commit <value>";
    if is_help(arguments) {
        println!("{usage}");
        return ExitCode::SUCCESS;
    }
    let options = &[
        "--report",
        "--output",
        "--research-question-file",
        "--branch",
        "--commit",
    ];
    let parsed = parse(arguments, options, 0);
    let values: Vec<&str> = options
        .iter()
        .filter_map(|name| parsed.value(name).and_then(std::ffi::OsStr::to_str))
        .collect();
    if parsed.error().is_some() || values.len() != options.len() || values.iter().any(|value| value.is_empty())
    {
        diagnostic(usage);
        return ExitCode::from(1);
    }
    render_findings_batch_run(&parsed)
}

/// Read the inputs, render the payload, write it, and emit the count contract.
fn render_findings_batch_run(parsed: &crate::argparse_compat::ParsedCommandLine) -> ExitCode {
    let report = PathBuf::from(parsed.value("--report").unwrap_or_default());
    let Ok(report_text) = read_regular_file(&report) else {
        diagnostic(&format!(
            "ERROR: report file not found: {}",
            parsed.value("--report").unwrap_or_default().to_string_lossy()
        ));
        return ExitCode::from(2);
    };
    let question_file = PathBuf::from(parsed.value("--research-question-file").unwrap_or_default());
    let question = first_nonblank_line(&question_file)
        .unwrap_or_else(|| "(research question unavailable)".to_owned());
    let timestamp = utc_timestamp();
    let (count, payload, section_absent) = render_findings_issue_batch(
        &report_text,
        &render::FindingsContext {
            research_question: &question,
            branch: &parsed.value("--branch").unwrap_or_default().to_string_lossy(),
            commit: &parsed.value("--commit").unwrap_or_default().to_string_lossy(),
            timestamp: &timestamp,
        },
    );
    if write_text_atomic(
        Path::new(parsed.value("--output").unwrap_or_default()),
        &payload,
    )
    .is_err()
    {
        diagnostic("ERROR: could not write findings batch output");
        return ExitCode::from(2);
    }
    emit_kv("COUNT", &count.to_string());
    if count == 0 {
        diagnostic(if section_absent {
            "WARNING: Findings Summary section not found in input (input may be malformed). The sidecar is empty; '/issue --input-file <path>' on it would create no issues."
        } else {
            "WARNING: Findings Summary section is empty (zero findings). The sidecar is empty; '/issue --input-file <path>' on it would create no issues."
        });
        return ExitCode::from(3);
    }
    ExitCode::SUCCESS
}

/// Read a path only when it is a regular file, mirroring Python `is_file`.
fn read_regular_file(path: &Path) -> std::io::Result<String> {
    if !fs::metadata(path)?.is_file() {
        return Err(std::io::Error::from(std::io::ErrorKind::NotFound));
    }
    read_text_lossy(path)
}

/// Return the first non-blank line of `path`, if the file is a readable regular.
fn first_nonblank_line(path: &Path) -> Option<String> {
    let text = read_regular_file(path).ok()?;
    split_text_lines(&text)
        .into_iter()
        .find(|line| !line.trim().is_empty())
        .map(str::to_owned)
}

/// Render the current instant as the Python `%Y-%m-%dT%H:%M:%SZ` UTC stamp.
fn utc_timestamp() -> String {
    chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string()
}

// ---------------------------------------------------------------------------
// validate-citations
// ---------------------------------------------------------------------------

mod citations;

/// Execute `research validate-citations`.
#[must_use]
pub fn validate_citations_command(arguments: &[OsString]) -> ExitCode {
    citations::run(arguments)
}

/// Extract sorted, unique URLs, trimming trailing sentence punctuation.
#[must_use]
pub fn extract_urls(text: &str) -> Vec<String> {
    sorted_unique(URL_RE.find_iter(text).map(|matched| trim_trailing(matched.as_str())))
}

/// Extract sorted, unique DOIs, trimming trailing sentence punctuation.
#[must_use]
pub fn extract_dois(text: &str) -> Vec<String> {
    sorted_unique(DOI_RE.find_iter(text).map(|matched| trim_trailing(matched.as_str())))
}

/// Extract sorted, unique `file:line` citations that survive the keep filter.
#[must_use]
pub fn extract_filelines(text: &str) -> Vec<String> {
    sorted_unique(FILELINE_RE.find_iter(text).filter_map(|matched| {
        let trimmed = strip_fileline_boundary(matched.as_str());
        FILELINE_KEEP_RE.is_match(&trimmed).then_some(trimmed)
    }))
}

/// Collect `values` into a byte-sorted, de-duplicated list.
fn sorted_unique(values: impl Iterator<Item = String>) -> Vec<String> {
    let set: std::collections::BTreeSet<String> = values.collect();
    set.into_iter().collect()
}

/// Strip trailing `.`, `,`, `;`, and `:` the way Python `rstrip(".,;:")` did.
fn trim_trailing(value: &str) -> String {
    value.trim_end_matches([',', '.', ';', ':']).to_owned()
}

/// Drop one leading and one trailing boundary byte from a file-line match.
fn strip_fileline_boundary(value: &str) -> String {
    let mut chars: Vec<char> = value.chars().collect();
    if chars.first().is_some_and(|&ch| !is_lead_char(ch)) {
        chars.remove(0);
    }
    if chars.last().is_some_and(|&ch| !is_trail_char(ch)) {
        chars.pop();
    }
    chars.into_iter().collect()
}

/// Whether a byte may lead a file-line citation (`[A-Za-z0-9._/-]`).
const fn is_lead_char(ch: char) -> bool {
    ch.is_ascii_alphanumeric() || matches!(ch, '.' | '_' | '/' | '-')
}

/// Whether a byte may end a file-line citation (`[A-Za-z0-9._/:-]`).
const fn is_trail_char(ch: char) -> bool {
    ch.is_ascii_alphanumeric() || matches!(ch, '.' | '_' | '/' | ':' | '-')
}

// ---------------------------------------------------------------------------
// SSRF-guarded fetch engine (shared by validate-citations)
// ---------------------------------------------------------------------------

/// The IANA-reserved and private ranges the SSRF guard refuses to connect to.
fn is_blocked_ip(value: &str) -> bool {
    let trimmed = value.trim_matches(['[', ']']);
    match trimmed.parse::<IpAddr>() {
        Ok(IpAddr::V4(ip)) => is_blocked_v4(ip),
        Ok(IpAddr::V6(ip)) => is_blocked_v6(ip),
        Err(_not_an_ip) => false,
    }
}

/// Refuse RFC1918, loopback, link-local, CGNAT, documentation, and reserved v4.
const fn is_blocked_v4(ip: Ipv4Addr) -> bool {
    let octets = ip.octets();
    ip.is_private()
        || ip.is_loopback()
        || ip.is_link_local()
        || ip.is_unspecified()
        || ip.is_broadcast()
        || ip.is_documentation()
        || (octets[0] == 100 && (octets[1] & 0b1100_0000) == 0b0100_0000) // 100.64.0.0/10 (CGNAT)
        || (octets[0] == 198 && (octets[1] == 18 || octets[1] == 19)) // 198.18.0.0/15
        || octets[0] >= 240 // 240.0.0.0/4 (reserved)
}

/// Refuse loopback, unspecified, unique-local, link-local, and mapped-v4 v6.
const fn is_blocked_v6(ip: Ipv6Addr) -> bool {
    if ip.is_loopback() || ip.is_unspecified() {
        return true;
    }
    if let Some(mapped) = ip.to_ipv4_mapped() {
        return is_blocked_v4(mapped);
    }
    let segments = ip.segments();
    (segments[0] & 0xfe00) == 0xfc00 // fc00::/7 (unique local)
        || (segments[0] & 0xffc0) == 0xfe80 // fe80::/10 (link local)
        || (segments[0] == 0x2001 && segments[1] == 0x0db8) // 2001:db8::/32 (documentation)
}

/// Whether a hostname is a loopback alias or resolves to a blocked literal.
fn is_private_hostname(host: &str) -> bool {
    let lowered = host.trim_matches(['[', ']']).to_lowercase();
    if lowered == "localhost" || lowered == "localhost.localdomain" || lowered.ends_with(".localhost")
    {
        return true;
    }
    is_blocked_ip(&lowered)
}

/// The DNS resolver seam: hostname to a list of textual addresses.
type Resolver<'a> = dyn Fn(&str, u16) -> Result<Vec<String>, &'static str> + 'a;
/// The connector seam: (url, pinned address, timeout) to an HTTP status code.
type Connector<'a> = dyn Fn(&str, &str, u64) -> Result<u16, &'static str> + 'a;

/// The optional resolver and connector seams a fetch is driven through.
#[derive(Default)]
struct FetchSeams<'a> {
    resolver: Option<&'a Resolver<'a>>,
    connector: Option<&'a Connector<'a>>,
}

/// Resolve `host` to public addresses, refusing any private resolved address.
///
/// Returns `(addresses, refusal)`: a non-empty refusal means the addresses are
/// empty and the caller maps the refusal to a FAIL or UNKNOWN classification.
fn resolve_public_ips(
    host: &str,
    port: u16,
    timeout: u64,
    resolver: Option<&Resolver<'_>>,
) -> (Vec<String>, Option<&'static str>) {
    let addresses = match resolver {
        Some(resolve) => match resolve(host, port) {
            Ok(addresses) => addresses,
            Err(reason) => return (Vec::new(), Some(reason)),
        },
        None => match resolve_real(host, port, timeout) {
            Ok(addresses) => addresses,
            Err(reason) => return (Vec::new(), Some(reason)),
        },
    };
    if addresses.iter().any(|address| is_blocked_ip(address)) {
        return (Vec::new(), Some("ssrf-private-resolved"));
    }
    (addresses, None)
}

/// Resolve a hostname on a worker thread bounded by `timeout` seconds.
fn resolve_real(host: &str, port: u16, timeout: u64) -> Result<Vec<String>, &'static str> {
    let (sender, receiver) = mpsc::channel();
    let query = format!("{host}:{port}");
    thread::spawn(move || {
        let _ignored = sender.send(query.to_socket_addrs().map(|addresses| {
            let mut seen: Vec<String> = Vec::new();
            for address in addresses {
                let text = address.ip().to_string();
                if !seen.contains(&text) {
                    seen.push(text);
                }
            }
            seen
        }));
    });
    match receiver.recv_timeout(Duration::from_secs(timeout.max(1))) {
        Ok(Ok(addresses)) => Ok(addresses),
        Ok(Err(_error)) => Err("network-error"),
        Err(mpsc::RecvTimeoutError::Timeout) => Err("timeout"),
        Err(mpsc::RecvTimeoutError::Disconnected) => Err("network-error"),
    }
}

/// Classify one URL, keeping every Python SSRF guard and status mapping.
fn fetch_url(url: &str, timeout: u64, seams: &FetchSeams<'_>) -> FetchResult {
    let Some(parts) = UrlParts::parse(url) else {
        return FetchResult::new("FAIL", "non-https");
    };
    if is_private_hostname(&parts.host) {
        return FetchResult::new("FAIL", "ssrf-private-host");
    }
    let (addresses, refusal) =
        resolve_public_ips(&parts.host, parts.port, timeout, seams.resolver);
    match refusal {
        Some("ssrf-private-resolved") => return FetchResult::new("FAIL", "ssrf-private-resolved"),
        Some(reason @ ("timeout" | "network-error")) => return FetchResult::new("UNKNOWN", reason),
        Some(other) => return FetchResult::new("UNKNOWN", other),
        None => {}
    }
    let Some(pinned) = addresses.first() else {
        return FetchResult::new("UNKNOWN", "network-error");
    };
    match connect(url, pinned, timeout, seams.connector) {
        Ok(code) => classify_status(code),
        Err(reason) => FetchResult::new("UNKNOWN", reason),
    }
}

/// Drive the connector seam, or the real pinned-IP HEAD request.
fn connect(
    url: &str,
    pinned: &str,
    timeout: u64,
    connector: Option<&Connector<'_>>,
) -> Result<u16, &'static str> {
    connector.map_or_else(
        || connect_real(url, pinned, timeout),
        |connect| connect(url, pinned, timeout),
    )
}

/// Map an HTTP status code to the frozen FAIL/UNKNOWN/PASS taxonomy.
fn classify_status(code: u16) -> FetchResult {
    match code {
        200..=299 => FetchResult::pass(),
        300..=399 => FetchResult::new("UNKNOWN", "redirect-not-followed"),
        403 | 405 | 501 => FetchResult::new("UNKNOWN", "head-not-supported"),
        404 | 410 => FetchResult::new("FAIL", "head-not-found"),
        400..=499 => FetchResult::new("FAIL", &format!("head-client-error-{code}")),
        500..=599 => FetchResult::new("FAIL", &format!("head-server-error-{code}")),
        _other => FetchResult::new("UNKNOWN", &format!("unrecognized-status-{code}")),
    }
}

/// A parsed `https` URL: hostname and port, the only fields the guard needs.
struct UrlParts {
    host: String,
    port: u16,
}

impl UrlParts {
    /// Parse an `https` URL, returning `None` for any non-`https` or hostless URL.
    fn parse(url: &str) -> Option<Self> {
        let rest = url.strip_prefix("https://")?;
        let authority = rest.split(['/', '?', '#']).next().unwrap_or("");
        let authority = authority.rsplit('@').next().unwrap_or(authority);
        let (host, port) = Self::split_host_port(authority)?;
        if host.is_empty() {
            return None;
        }
        Some(Self { host, port })
    }

    /// Split an authority into host and port, honoring bracketed IPv6 literals.
    fn split_host_port(authority: &str) -> Option<(String, u16)> {
        if let Some(after_bracket) = authority.strip_prefix('[') {
            let (host, tail) = after_bracket.split_once(']')?;
            let port = Self::parse_port(tail.strip_prefix(':'))?;
            return Some((host.to_lowercase(), port));
        }
        match authority.rsplit_once(':') {
            Some((host, port)) => Some((host.to_lowercase(), Self::parse_port(Some(port))?)),
            None => Some((authority.to_lowercase(), 443)),
        }
    }

    /// Parse an optional port string, defaulting to 443.
    fn parse_port(port: Option<&str>) -> Option<u16> {
        match port {
            None | Some("") => Some(443),
            Some(text) => text.parse::<u16>().ok(),
        }
    }
}

/// Real pinned-IP HEAD request preserving the hostname for SNI and `Host`.
fn connect_real(url: &str, pinned: &str, timeout: u64) -> Result<u16, &'static str> {
    let Some(parts) = UrlParts::parse(url) else {
        return Err("network-error");
    };
    let Ok(ip) = pinned.parse::<IpAddr>() else {
        return Err("network-error");
    };
    let client = reqwest::blocking::Client::builder()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(Duration::from_secs(timeout.max(1)))
        .resolve(&parts.host, SocketAddr::new(ip, parts.port))
        .build()
        .map_err(|_error| "network-error")?;
    match client.head(url).send() {
        Ok(response) => Ok(response.status().as_u16()),
        Err(error) if error.is_timeout() => Err("timeout"),
        Err(_error) => Err("network-error"),
    }
}

/// Fetch every target under a per-fetch timeout and a total wall-clock budget.
///
/// Targets that do not report within the budget are recorded as UNKNOWN
/// timeouts, matching the Python engine that terminated overrunning fetches.
fn parallel_fetch_results(
    targets: &BTreeMap<String, String>,
    budget: u64,
    per_fetch: u64,
    fetcher: &(dyn Fn(&str) -> FetchResult + Sync),
) -> BTreeMap<String, FetchResult> {
    let mut results = BTreeMap::new();
    if targets.is_empty() {
        return results;
    }
    let (sender, receiver) = mpsc::channel();
    thread::scope(|scope| {
        for (key, target) in targets {
            let sender = sender.clone();
            let fetcher = &fetcher;
            scope.spawn(move || {
                let _ignored = sender.send((key.clone(), fetcher(target)));
            });
        }
        drop(sender);
        let deadline = Instant::now() + Duration::from_secs(budget.max(1));
        while results.len() < targets.len() {
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() {
                break;
            }
            match receiver.recv_timeout(remaining) {
                Ok((key, result)) => {
                    results.insert(key, result);
                }
                Err(_timeout) => break,
            }
        }
    });
    for key in targets.keys() {
        results
            .entry(key.clone())
            .or_insert_with(|| FetchResult::new("UNKNOWN", "timeout"));
    }
    let _ = per_fetch;
    results
}

// ---------------------------------------------------------------------------
// file-line checking
// ---------------------------------------------------------------------------

/// Classify one `path:line` (or bare `path`) citation against the repository.
///
/// `git_root` is a seam: when `None`, the repository root is probed with `git`,
/// and an unavailable root is an UNKNOWN classification rather than a failure.
#[must_use]
pub fn check_fileline(cite: &str, git_root: Option<&Path>) -> FetchResult {
    let range = FileLineRange::parse(cite);
    let owned_root;
    let root = match git_root {
        Some(root) => root,
        None => match probe_git_root() {
            Some(root) => {
                owned_root = root;
                owned_root.as_path()
            }
            None => return FetchResult::new("UNKNOWN", "git-root-unavailable"),
        },
    };
    check_fileline_at(cite, &range, root)
}

/// Resolve, contain, and range-check one citation under a known root.
fn check_fileline_at(cite: &str, range: &FileLineRange, root: &Path) -> FetchResult {
    let mut target = root.join(&range.rel);
    if !target.exists() && Path::new(&range.rel).exists() {
        target = PathBuf::from(&range.rel);
    }
    if !target.exists() {
        return FetchResult::new("FAIL", "file-not-found");
    }
    let (Ok(root_real), Ok(target_real)) = (fs::canonicalize(root), fs::canonicalize(&target))
    else {
        return FetchResult::new("UNKNOWN", "broken-symlink");
    };
    if !target_real.starts_with(&root_real) {
        return FetchResult::new("UNKNOWN", "out-of-tree-path-after-realpath");
    }
    let Ok(metadata) = fs::metadata(&target_real) else {
        return FetchResult::new("UNKNOWN", "broken-symlink");
    };
    if metadata.is_dir() {
        return FetchResult::new("FAIL", "path-is-directory");
    }
    if !metadata.is_file() {
        return FetchResult::new("UNKNOWN", "broken-symlink");
    }
    check_range(cite, range, &target_real)
}

/// Apply the line-range portion of a citation once the file is confirmed.
fn check_range(cite: &str, range: &FileLineRange, target: &Path) -> FetchResult {
    if !range.has_range {
        return FetchResult::pass();
    }
    if range.start > range.end {
        return FetchResult::new("FAIL", "line-range-empty");
    }
    let Ok(text) = read_text_lossy(target) else {
        return FetchResult::new("UNKNOWN", "file-unreadable");
    };
    let _ = cite;
    if range.end > split_text_lines(&text).len() {
        return FetchResult::new("FAIL", "line-out-of-range");
    }
    FetchResult::pass()
}

/// The parsed relative path and optional line range of a citation.
struct FileLineRange {
    rel: String,
    start: usize,
    end: usize,
    has_range: bool,
}

impl FileLineRange {
    /// Parse `path:start[-end]`, falling back to a bare path with no range.
    fn parse(cite: &str) -> Self {
        if let Some(captures) = FILELINE_CITE_RE.captures(cite) {
            let start = captures[2].parse().unwrap_or(0);
            let end = captures
                .get(4)
                .and_then(|group| group.as_str().parse().ok())
                .unwrap_or(start);
            return Self {
                rel: captures[1].to_owned(),
                start,
                end,
                has_range: true,
            };
        }
        Self {
            rel: cite.to_owned(),
            start: 0,
            end: 0,
            has_range: false,
        }
    }
}

/// Probe the repository root with `git rev-parse --show-toplevel`.
fn probe_git_root() -> Option<PathBuf> {
    let output = Command::new("git")
        .args(["rev-parse", "--show-toplevel"])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let text = String::from_utf8_lossy(&output.stdout);
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return None;
    }
    Some(PathBuf::from(trimmed))
}

#[cfg(test)]
mod tests;
