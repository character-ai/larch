//! Pure drafter output grammar, status rendering, and drafter path rules.
//!
//! The drafter launchers publish a plan, an optional summary, an optional
//! scout manifest, and an optional dialectic block from one sentinel-delimited
//! vendor response. Every rule that decides whether a response is well formed
//! lives here so the launcher wiring only performs I/O.

use std::{collections::BTreeSet, error::Error, fmt};

use serde_json::Value;

use crate::{OrderedJson, ensure_ascii_json, split_text_lines};

/// Maximum accepted drafter timeout, in seconds.
pub const MAX_DRAFTER_TIMEOUT_SECONDS: u64 = 1800;
/// Design-tmpdir file that holds the raw dialectic payload between steps.
pub const DIALECTIC_RAW_PENDING_FILE: &str = ".dialectic-raw-pending.json";
/// Wire label recorded when no dialectic or scout block was emitted.
pub const DRAFTER_REASON_ABSENT: &str = "absent";

/// Trusted Codex instructions injected into the private drafter Codex home.
///
/// The focus-area alternatives are spelled out rather than composed from
/// [`crate::FocusArea`] because this is a frozen prompt contract: a future
/// focus-area addition must be an explicit prompt decision, not a silent
/// rewrite of instructions already relied on by recorded drafter outputs.
pub const CODEX_DRAFTER_TRUSTED_INSTRUCTIONS: &str = r#"STRICT CONSTRAINTS — your role is read-only plan drafting for /design Step 2b. Do not create, edit, delete, or overwrite repository or tmpdir files. The launcher enforces this with --sandbox read-only.

OUTPUT CONTRACT — these requirements override any conflicting Codex user configuration or instructions:
- Emit exactly one whole-line LARCH_PLAN_BEGIN and one whole-line LARCH_PLAN_END with a non-empty plan body between them.
- Optionally emit zero or one balanced LARCH_SUMMARY_BEGIN/LARCH_SUMMARY_END pair before the plan envelope.
- The plan body must end with a whole-line diff_lines: <N> trailer.
- Optionally emit zero or one balanced LARCH_DIALECTIC_BEGIN/LARCH_DIALECTIC_END JSON block after LARCH_PLAN_END and before LARCH_SCOUT_BEGIN.
- Use dialectic JSON only for genuine bistable forks: at most two decisions, each with id, title, option_a, option_b, tradeoff, drafter_pick (option_a or option_b), and why_this_matters.
- Malformed dialectic output after the plan is ignored by the launcher and must not affect a valid plan; dialectic sentinels inside the summary or plan are fatal.
- Emit zero or one balanced LARCH_SCOUT_BEGIN/LARCH_SCOUT_END pair after LARCH_PLAN_END on a best-effort basis.
- Use {"archetypes":[]} when no dynamic plan-review specialists are useful.
- The scout block must contain only compact JSON with this shape: {"archetypes":[{"name":"slug","focus_area":"code-quality | risk-integration | correctness | architecture | security","weight":1,"rationale":"...","prompt_body":"..."}]}.
- Malformed scout output after the plan is ignored by the launcher and must not affect a valid plan.
- Scout sentinels before or inside the summary or plan are fatal format errors.
- Return only the sentinel-delimited response format; do not omit required sentinels.
"#;

const PLAN_BEGIN: &str = "LARCH_PLAN_BEGIN";
const PLAN_END: &str = "LARCH_PLAN_END";
const SUMMARY_BEGIN: &str = "LARCH_SUMMARY_BEGIN";
const SUMMARY_END: &str = "LARCH_SUMMARY_END";
const SCOUT_BEGIN: &str = "LARCH_SCOUT_BEGIN";
const SCOUT_END: &str = "LARCH_SCOUT_END";
const DIALECTIC_BEGIN: &str = "LARCH_DIALECTIC_BEGIN";
const DIALECTIC_END: &str = "LARCH_DIALECTIC_END";

/// A drafter response that cannot yield a plan.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DrafterParseError(String);

impl DrafterParseError {
    fn new(message: &str) -> Self {
        Self(message.to_owned())
    }

    /// Borrow the legacy-compatible diagnostic text.
    #[must_use]
    pub fn message(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for DrafterParseError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl Error for DrafterParseError {}

/// Outcome of the optional scout-manifest block.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DrafterScout {
    /// No scout sentinels were present.
    Absent,
    /// Scout sentinels were present but unusable, with the wire fail reason.
    Invalid(&'static str),
    /// A well-shaped compact manifest, newline terminated.
    Manifest(String),
}

impl DrafterScout {
    /// Return the wire fail reason, or an empty string for a usable manifest.
    #[must_use]
    pub const fn fail_reason(&self) -> &'static str {
        match self {
            Self::Absent => DRAFTER_REASON_ABSENT,
            Self::Invalid(reason) => reason,
            Self::Manifest(_manifest) => "",
        }
    }
}

/// Outcome of the optional dialectic block before candidate validation.
///
/// Candidate validation itself stays with the design-domain owner, so this
/// carries the raw block text rather than a normalized payload.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DrafterDialectic {
    /// No dialectic sentinels were present.
    Absent,
    /// Dialectic sentinels were present but unusable, with the wire fail reason.
    Invalid(&'static str),
    /// Raw dialectic JSON text awaiting candidate validation.
    Candidate(String),
}

/// Everything one well-formed drafter response yields.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DrafterParse {
    /// Extracted plan body, newline terminated.
    pub plan_body: String,
    /// Number of plan lines between the plan sentinels after trailing trim.
    pub plan_lines: usize,
    /// Value of the terminal `diff_lines:` trailer.
    pub diff_lines: u64,
    /// Extracted summary body, newline terminated, when a summary was present.
    pub summary: Option<String>,
    /// Scout-manifest outcome.
    pub scout: DrafterScout,
    /// Dialectic-block outcome.
    pub dialectic: DrafterDialectic,
}

fn positions(lines: &[&str], marker: &str) -> Vec<usize> {
    lines
        .iter()
        .enumerate()
        .filter_map(|(index, line)| (*line == marker).then_some(index))
        .collect()
}

/// Parse one raw drafter response into its plan, summary, scout, and dialectic parts.
///
/// # Errors
/// Returns the legacy diagnostic text for any fatal sentinel, plan-body, or
/// trailer violation. Malformed scout and dialectic blocks are reported through
/// [`DrafterParse`] instead, because they must never invalidate a good plan.
pub fn parse_drafter_output(text: &str) -> Result<DrafterParse, DrafterParseError> {
    let lines = split_text_lines(text);
    let plan_begin = positions(&lines, PLAN_BEGIN);
    let plan_end = positions(&lines, PLAN_END);
    let summary_begin = positions(&lines, SUMMARY_BEGIN);
    let summary_end = positions(&lines, SUMMARY_END);
    let scout_begin = positions(&lines, SCOUT_BEGIN);
    let scout_end = positions(&lines, SCOUT_END);
    let dialectic_begin = positions(&lines, DIALECTIC_BEGIN);
    let dialectic_end = positions(&lines, DIALECTIC_END);

    let (plan_open, plan_close) = validate_plan_sentinels(&plan_begin, &plan_end)?;
    let summary_span = validate_summary_sentinels(
        &summary_begin,
        &summary_end,
        plan_open,
        plan_close,
        &scout_begin,
        &scout_end,
    )?;
    validate_dialectic_placement(
        &dialectic_begin,
        &dialectic_end,
        plan_open,
        plan_close,
        summary_span,
    )?;

    let (plan_body, plan_lines) = extract_plan_body(&lines, plan_open, plan_close)?;
    let diff_lines = terminal_diff_lines(&plan_body)
        .ok_or_else(|| DrafterParseError::new("missing final diff_lines trailer"))?;
    if plan_contains_standalone_scout_manifest(&plan_body) {
        return Err(DrafterParseError::new(
            "invalid plan body: standalone scout manifest JSON is not allowed inside plan",
        ));
    }
    let summary = extract_summary_body(&lines, summary_span)?;
    Ok(DrafterParse {
        plan_body,
        plan_lines,
        diff_lines,
        summary,
        scout: extract_scout(&lines, &scout_begin, &scout_end),
        dialectic: extract_dialectic(
            &lines,
            &dialectic_begin,
            &dialectic_end,
            plan_close,
            &scout_begin,
        ),
    })
}

fn validate_plan_sentinels(
    begin: &[usize],
    end: &[usize],
) -> Result<(usize, usize), DrafterParseError> {
    let (Some(&open), Some(&close)) = (begin.first(), end.first()) else {
        return Err(DrafterParseError::new(
            "invalid plan sentinels: require exactly one LARCH_PLAN_BEGIN and LARCH_PLAN_END",
        ));
    };
    if begin.len() != 1 || end.len() != 1 {
        return Err(DrafterParseError::new(
            "invalid plan sentinels: require exactly one LARCH_PLAN_BEGIN and LARCH_PLAN_END",
        ));
    }
    if open >= close {
        return Err(DrafterParseError::new(
            "invalid plan sentinels: reversed or empty plan envelope",
        ));
    }
    Ok((open, close))
}

fn validate_summary_sentinels(
    begin: &[usize],
    end: &[usize],
    plan_open: usize,
    plan_close: usize,
    scout_begin: &[usize],
    scout_end: &[usize],
) -> Result<Option<(usize, usize)>, DrafterParseError> {
    if begin.is_empty() != end.is_empty() || begin.len() > 1 || end.len() > 1 {
        return Err(DrafterParseError::new(
            "invalid summary sentinels: require zero or one balanced pair",
        ));
    }
    let span = match (begin.first(), end.first()) {
        (Some(&open), Some(&close)) => {
            if open >= close {
                return Err(DrafterParseError::new(
                    "invalid summary sentinels: reversed or empty summary envelope",
                ));
            }
            if (plan_open < open && open < plan_close) || (plan_open < close && close < plan_close)
            {
                return Err(DrafterParseError::new(
                    "invalid sentinels: nested summary inside plan envelope",
                ));
            }
            if open < plan_open && plan_close < close {
                return Err(DrafterParseError::new(
                    "invalid sentinels: nested plan inside summary envelope",
                ));
            }
            if close >= plan_open {
                return Err(DrafterParseError::new(
                    "invalid summary sentinels: summary must appear before plan envelope",
                ));
            }
            Some((open, close))
        }
        _ => None,
    };
    if scout_begin
        .iter()
        .chain(scout_end)
        .any(|index| *index < plan_close)
    {
        return Err(DrafterParseError::new(
            "invalid scout sentinels: scout block may appear only after LARCH_PLAN_END",
        ));
    }
    Ok(span)
}

fn validate_dialectic_placement(
    begin: &[usize],
    end: &[usize],
    plan_open: usize,
    plan_close: usize,
    summary_span: Option<(usize, usize)>,
) -> Result<(), DrafterParseError> {
    if begin
        .iter()
        .chain(end)
        .any(|index| plan_open < *index && *index < plan_close)
    {
        return Err(DrafterParseError::new(
            "invalid dialectic sentinels: dialectic block may not appear inside plan envelope",
        ));
    }
    if let Some((summary_open, summary_close)) = summary_span
        && begin
            .iter()
            .chain(end)
            .any(|index| summary_open < *index && *index < summary_close)
    {
        return Err(DrafterParseError::new(
            "invalid dialectic sentinels: dialectic block may not appear inside summary envelope",
        ));
    }
    Ok(())
}

fn extract_plan_body(
    lines: &[&str],
    plan_open: usize,
    plan_close: usize,
) -> Result<(String, usize), DrafterParseError> {
    let mut body: Vec<&str> = lines[plan_open + 1..plan_close].to_vec();
    if body.iter().all(|line| line.trim().is_empty()) {
        return Err(DrafterParseError::new("empty extracted plan body"));
    }
    while body.last() == Some(&"") {
        body.pop();
    }
    Ok((format!("{}\n", body.join("\n")), body.len()))
}

fn extract_summary_body(
    lines: &[&str],
    span: Option<(usize, usize)>,
) -> Result<Option<String>, DrafterParseError> {
    let Some((open, close)) = span else {
        return Ok(None);
    };
    let body = &lines[open + 1..close];
    if body.iter().all(|line| line.trim().is_empty()) {
        return Err(DrafterParseError::new("empty extracted summary body"));
    }
    Ok(Some(format!(
        "{}\n",
        body.join("\n").trim_end_matches('\n')
    )))
}

fn extract_scout(lines: &[&str], begin: &[usize], end: &[usize]) -> DrafterScout {
    if begin.is_empty() && end.is_empty() {
        return DrafterScout::Absent;
    }
    let (Some(&open), Some(&close)) = (begin.first(), end.first()) else {
        return DrafterScout::Invalid("invalid_scout_sentinels");
    };
    if begin.len() != 1 || end.len() != 1 || open >= close {
        return DrafterScout::Invalid("invalid_scout_sentinels");
    }
    let text = lines[open + 1..close].join("\n");
    let text = text.trim();
    if text.is_empty() {
        return DrafterScout::Invalid("empty_scout_json");
    }
    let Ok(payload) = serde_json::from_str::<OrderedJson>(text) else {
        return DrafterScout::Invalid("json_parse");
    };
    let OrderedJson::Object(members) = &payload else {
        return DrafterScout::Invalid("invalid_archetypes_shape");
    };
    let archetypes = members.iter().find(|(key, _value)| key == "archetypes");
    if !matches!(archetypes, Some((_key, OrderedJson::Array(_items)))) {
        return DrafterScout::Invalid("invalid_archetypes_shape");
    }
    match serde_json::to_string(&payload) {
        Ok(compact) => DrafterScout::Manifest(format!("{}\n", ensure_ascii_json(&compact))),
        Err(_error) => DrafterScout::Invalid("json_parse"),
    }
}

fn extract_dialectic(
    lines: &[&str],
    begin: &[usize],
    end: &[usize],
    plan_close: usize,
    scout_begin: &[usize],
) -> DrafterDialectic {
    if begin.is_empty() && end.is_empty() {
        return DrafterDialectic::Absent;
    }
    if begin.len() != 1 || end.len() != 1 {
        return DrafterDialectic::Invalid("invalid_dialectic_sentinels");
    }
    let (open, close) = (begin[0], end[0]);
    let misplaced = open >= close
        || open <= plan_close
        || scout_begin.first().is_some_and(|scout| close >= *scout);
    if misplaced {
        return DrafterDialectic::Invalid("invalid_dialectic_sentinels");
    }
    let text = lines[open + 1..close].join("\n");
    let text = text.trim();
    if text.is_empty() {
        return DrafterDialectic::Invalid("empty_dialectic_json");
    }
    DrafterDialectic::Candidate(text.to_owned())
}

/// Detect a bare scout manifest published inside the plan body.
///
/// Only an unfenced object that starts at column zero and owns its closing line
/// counts, matching the legacy scan. An unterminated code fence disables fence
/// stripping entirely so a truncated response is still inspected.
#[must_use]
pub fn plan_contains_standalone_scout_manifest(plan_text: &str) -> bool {
    let mut in_fence = false;
    let mut unfenced: Vec<&str> = Vec::new();
    for line in split_text_lines(plan_text) {
        if line.trim_start().starts_with("```") {
            in_fence = !in_fence;
            continue;
        }
        if !in_fence {
            unfenced.push(line);
        }
    }
    let joined;
    let scanned = if in_fence {
        plan_text
    } else {
        joined = unfenced.join("\n");
        &joined
    };
    line_start_offsets(scanned)
        .into_iter()
        .filter(|offset| scanned.as_bytes().get(*offset) == Some(&b'{'))
        .any(|offset| standalone_manifest_at(scanned, offset))
}

fn line_start_offsets(text: &str) -> Vec<usize> {
    let mut offsets = vec![0_usize];
    offsets.extend(
        text.bytes()
            .enumerate()
            .filter_map(|(index, byte)| (byte == b'\n').then_some(index + 1)),
    );
    offsets
}

fn standalone_manifest_at(text: &str, offset: usize) -> bool {
    let mut stream = serde_json::Deserializer::from_str(&text[offset..]).into_iter::<Value>();
    let Some(Ok(parsed)) = stream.next() else {
        return false;
    };
    let end = offset + stream.byte_offset();
    let line_end = text[end..]
        .find('\n')
        .map_or(text.len(), |relative| end + relative);
    if !text[end..line_end].trim().is_empty() {
        return false;
    }
    parsed
        .as_object()
        .and_then(|object| object.get("archetypes"))
        .is_some_and(Value::is_array)
}

/// Read the value of a terminal `diff_lines:` plan trailer.
///
/// The trailer block is the final run of valid trailer lines after trailing
/// blank lines are discarded. `diff_lines` must be the last trailer in it.
#[must_use]
pub fn terminal_diff_lines(text: &str) -> Option<u64> {
    let mut lines = split_text_lines(text);
    while lines.last().is_some_and(|line| line.trim().is_empty()) {
        lines.pop();
    }
    let mut trailers: Vec<(&str, &str)> = Vec::new();
    for line in lines.iter().rev() {
        let Some(trailer) = match_trailer_line(line) else {
            break;
        };
        trailers.push(trailer);
    }
    trailers.reverse();
    if trailers.last()?.0 != "diff_lines" {
        return None;
    }
    trailers
        .iter()
        .rev()
        .find(|(key, _value)| *key == "diff_lines")
        .and_then(|(_key, value)| value.parse::<u64>().ok())
}

fn match_trailer_line(line: &str) -> Option<(&str, &str)> {
    let line = line.trim_end_matches(['\r', '\n']);
    let (key, value) = line.split_once(": ")?;
    if value.is_empty() || value.contains(['\r', '\n']) {
        return None;
    }
    let valid = match key {
        "review_status" => !value.trim().is_empty(),
        "rounds_completed" | "diff_lines" => is_ascii_digits(value),
        "diff_added" | "diff_deleted" => is_size_integer(value),
        "difficulty" => matches!(value, "TRIVIAL" | "MODERATE" | "HARD"),
        "mechanical_churn" => matches!(value, "true" | "false"),
        "oversize_override" => value == "operator",
        _ => false,
    };
    valid.then_some((key, value))
}

fn is_ascii_digits(value: &str) -> bool {
    !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit())
}

fn is_size_integer(value: &str) -> bool {
    let mut bytes = value.bytes();
    match bytes.next() {
        Some(b'0') => bytes.all(|byte| (b'0'..=b'7').contains(&byte)),
        Some(byte) if byte.is_ascii_digit() => bytes.all(|byte| byte.is_ascii_digit()),
        _ => false,
    }
}

/// Fields of one drafter status file.
///
/// The Boolean density mirrors the fixed `KEY=value` status record its readers
/// parse; grouping the flags would change the wire format, not clarify it.
#[allow(
    clippy::struct_excessive_bools,
    reason = "one field per status-file key"
)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DrafterStatus<'a> {
    /// Terminal status token (`OK`, `ERROR`, `TIMEOUT`).
    pub status: &'a str,
    /// Whether `plan.txt` was published.
    pub plan_written: bool,
    /// Number of published plan lines.
    pub plan_lines: usize,
    /// Terminal `diff_lines` trailer value.
    pub diff_lines: u64,
    /// Whether a plan summary was published.
    pub summary_written: bool,
    /// Whether a filtered scout manifest was published.
    pub scout_written: bool,
    /// Scout fail reason, omitted when empty.
    pub scout_fail_reason: &'a str,
    /// Whether dialectic candidates validated.
    pub dialectic_parsed: bool,
    /// Whether the raw dialectic payload was persisted.
    pub dialectic_raw_pending_written: bool,
    /// Dialectic fail reason, omitted when empty.
    pub dialectic_fail_reason: &'a str,
    /// Whether the drafter vendor was launched.
    pub launched: bool,
    /// Terminal reason, omitted when empty.
    pub reason: &'a str,
}

impl DrafterStatus<'_> {
    /// Build the pre-launch failure status the launchers publish first.
    #[must_use]
    pub const fn prelaunch(reason: &str) -> DrafterStatus<'_> {
        DrafterStatus {
            status: "ERROR",
            plan_written: false,
            plan_lines: 0,
            diff_lines: 0,
            summary_written: false,
            scout_written: false,
            scout_fail_reason: "",
            dialectic_parsed: false,
            dialectic_raw_pending_written: false,
            dialectic_fail_reason: "",
            launched: false,
            reason,
        }
    }

    /// Build a post-launch failure status carrying one reason token.
    #[must_use]
    pub const fn launched_failure<'a>(status: &'a str, reason: &'a str) -> DrafterStatus<'a> {
        DrafterStatus {
            status,
            launched: true,
            reason,
            ..Self::prelaunch(reason)
        }
    }
}

/// Render one drafter status file body.
#[must_use]
pub fn render_drafter_status(status: &DrafterStatus<'_>) -> String {
    let mut lines = vec![
        format!("STATUS={}", status.status),
        format!("PLAN_WRITTEN={}", status.plan_written),
        format!("PLAN_LINES={}", status.plan_lines),
        format!("DIFF_LINES={}", status.diff_lines),
        format!("SUMMARY_WRITTEN={}", status.summary_written),
        format!("SCOUT_WRITTEN={}", status.scout_written),
        format!("DIALECTIC_CANDIDATES_PARSED={}", status.dialectic_parsed),
        format!(
            "DIALECTIC_RAW_PENDING_WRITTEN={}",
            status.dialectic_raw_pending_written
        ),
    ];
    if !status.scout_fail_reason.is_empty() {
        lines.push(format!("SCOUT_FAIL_REASON={}", status.scout_fail_reason));
    }
    if !status.dialectic_fail_reason.is_empty() {
        lines.push(format!(
            "DIALECTIC_CANDIDATES_FAIL_REASON={}",
            status.dialectic_fail_reason
        ));
    }
    lines.push(format!("DRAFTER_LAUNCHED={}", status.launched));
    if !status.reason.is_empty() {
        lines.push(format!("REASON={}", status.reason));
    }
    format!("{}\n", lines.join("\n"))
}

/// Working-tree evidence available when the dirty-tree sidecar is rendered.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DrafterDirtyTree<'a> {
    /// The launcher exited before the drafter vendor started.
    NotLaunched,
    /// The drafter vendor started and a porcelain probe was attempted.
    Launched {
        /// Vendor label used in the reason token.
        tool: &'a str,
        /// Porcelain output, or `None` when the probe failed.
        porcelain: Option<&'a str>,
        /// Pre-launch baseline contents when a baseline file was readable.
        baseline: Option<&'a str>,
    },
}

/// Render one drafter dirty-tree sidecar body.
///
/// The baseline and the post-launch probe can come from different porcelain
/// producers while the design step that captures the baseline is still Python,
/// so the comparison is over the set of reported entries rather than raw bytes.
/// Formatting or ordering differences between producers must not be reported as
/// a drafter mutation.
#[must_use]
pub fn render_drafter_dirty_tree(evidence: DrafterDirtyTree<'_>) -> String {
    let (status, mode, reason) = match evidence {
        DrafterDirtyTree::NotLaunched => (
            "unknown",
            "prelaunch",
            "launcher-exited-before-drafter-launch".to_owned(),
        ),
        DrafterDirtyTree::Launched {
            tool,
            porcelain,
            baseline: Some(baseline),
        } => match porcelain {
            Some(current) if porcelain_entries(current) == porcelain_entries(baseline) => (
                "clean",
                "baseline-delta",
                format!("{tool}-drafter-no-new-mutations"),
            ),
            Some(_current) => (
                "dirty",
                "baseline-delta",
                format!("{tool}-drafter-new-mutations"),
            ),
            None => ("unknown", "baseline-delta", "git-status-failed".to_owned()),
        },
        DrafterDirtyTree::Launched {
            tool,
            porcelain,
            baseline: None,
        } => match porcelain {
            Some(current) if porcelain_entries(current).is_empty() => (
                "clean",
                "absolute",
                format!("{tool}-drafter-clean-working-tree"),
            ),
            Some(_current) => (
                "unknown",
                "no-baseline",
                format!("{tool}-drafter-no-usable-baseline"),
            ),
            None => ("unknown", "no-baseline", "git-status-failed".to_owned()),
        },
    };
    format!("STATUS={status}\nMODE={mode}\nREASON={reason}\n")
}

fn porcelain_entries(text: &str) -> BTreeSet<&str> {
    split_text_lines(text)
        .into_iter()
        .map(str::trim_end)
        .filter(|line| !line.trim().is_empty())
        .collect()
}

/// Why a `--timeout` value is unusable for a drafter launch.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DrafterTimeoutError {
    /// The value is not a positive decimal integer.
    NotPositive,
    /// The value exceeds [`MAX_DRAFTER_TIMEOUT_SECONDS`].
    TooLarge,
}

/// Validate a drafter `--timeout` argument.
///
/// # Errors
/// Rejects non-positive values and values above [`MAX_DRAFTER_TIMEOUT_SECONDS`].
pub fn validate_drafter_timeout(raw: &str) -> Result<u64, DrafterTimeoutError> {
    if !is_ascii_digits(raw) {
        return Err(DrafterTimeoutError::NotPositive);
    }
    let seconds = raw
        .parse::<u64>()
        .map_err(|_error| DrafterTimeoutError::TooLarge)?;
    if seconds == 0 {
        return Err(DrafterTimeoutError::NotPositive);
    }
    if seconds > MAX_DRAFTER_TIMEOUT_SECONDS {
        return Err(DrafterTimeoutError::TooLarge);
    }
    Ok(seconds)
}

/// Accept a drafter path argument free of control characters and `..` segments.
#[must_use]
pub fn drafter_path_text_allowed(raw: &str) -> bool {
    !raw.is_empty() && !contains_control(raw) && !raw.contains("..")
}

/// Accept a drafter `--model` argument: one non-empty token with no whitespace.
#[must_use]
pub fn drafter_model_allowed(raw: &str) -> bool {
    !raw.is_empty() && !contains_control(raw) && !raw.chars().any(char::is_whitespace)
}

fn contains_control(raw: &str) -> bool {
    raw.chars()
        .any(|character| character.is_control() || character == '\u{7f}')
}

/// Map a drafter timing task kind to its token-record `RAW` label.
#[must_use]
pub fn drafter_token_raw_label(task_kind: &str) -> &'static str {
    if task_kind.contains("draft") {
        "claude_draft"
    } else if task_kind.contains("scout") {
        "claude_scout"
    } else if task_kind.contains("voter") {
        "claude_vote"
    } else {
        "claude_review"
    }
}

#[cfg(test)]
mod tests {
    use super::{
        DrafterDialectic, DrafterDirtyTree, DrafterScout, DrafterStatus, DrafterTimeoutError,
        drafter_model_allowed, drafter_path_text_allowed, drafter_token_raw_label,
        parse_drafter_output, plan_contains_standalone_scout_manifest, render_drafter_dirty_tree,
        render_drafter_status, terminal_diff_lines, validate_drafter_timeout,
    };

    fn plan(body: &str) -> String {
        format!("LARCH_PLAN_BEGIN\n{body}\nLARCH_PLAN_END\n")
    }

    #[test]
    fn extracts_plan_summary_scout_and_dialectic_from_a_full_response() {
        let raw = concat!(
            "noise\n",
            "LARCH_SUMMARY_BEGIN\nsummary body\n\nLARCH_SUMMARY_END\n",
            "LARCH_PLAN_BEGIN\n### NEW: a.rs\nwork\ndiff_lines: 42\n\nLARCH_PLAN_END\n",
            "LARCH_DIALECTIC_BEGIN\n  {\"decisions\": []}  \nLARCH_DIALECTIC_END\n",
            "LARCH_SCOUT_BEGIN\n{\"archetypes\" : [ ]}\nLARCH_SCOUT_END\n",
        );
        let parsed = parse_drafter_output(raw).expect("well-formed response");
        assert_eq!(parsed.plan_body, "### NEW: a.rs\nwork\ndiff_lines: 42\n");
        assert_eq!(parsed.plan_lines, 3);
        assert_eq!(parsed.diff_lines, 42);
        assert_eq!(parsed.summary.as_deref(), Some("summary body\n"));
        assert_eq!(
            parsed.scout,
            DrafterScout::Manifest("{\"archetypes\":[]}\n".to_owned())
        );
        assert_eq!(
            parsed.dialectic,
            DrafterDialectic::Candidate("{\"decisions\": []}".to_owned())
        );
    }

    #[test]
    fn rejects_every_fatal_sentinel_and_body_shape() {
        let cases = [
            ("", "invalid plan sentinels: require exactly one"),
            ("LARCH_PLAN_END\nLARCH_PLAN_BEGIN\n", "reversed or empty"),
            (
                "LARCH_PLAN_BEGIN\nLARCH_PLAN_BEGIN\nx\nLARCH_PLAN_END\n",
                "require exactly one",
            ),
            (
                "LARCH_SUMMARY_BEGIN\nLARCH_PLAN_BEGIN\nx\ndiff_lines: 1\nLARCH_PLAN_END\nLARCH_SUMMARY_END\n",
                "nested plan inside summary envelope",
            ),
            (
                "LARCH_PLAN_BEGIN\nLARCH_SUMMARY_BEGIN\nLARCH_SUMMARY_END\nx\nLARCH_PLAN_END\n",
                "nested summary inside plan envelope",
            ),
            (
                "LARCH_PLAN_BEGIN\nx\ndiff_lines: 1\nLARCH_PLAN_END\nLARCH_SUMMARY_BEGIN\ns\nLARCH_SUMMARY_END\n",
                "summary must appear before plan envelope",
            ),
            (
                "LARCH_SCOUT_BEGIN\n{}\nLARCH_SCOUT_END\nLARCH_PLAN_BEGIN\nx\ndiff_lines: 1\nLARCH_PLAN_END\n",
                "scout block may appear only after LARCH_PLAN_END",
            ),
            (
                "LARCH_PLAN_BEGIN\nLARCH_DIALECTIC_BEGIN\nLARCH_DIALECTIC_END\nx\nLARCH_PLAN_END\n",
                "dialectic block may not appear inside plan envelope",
            ),
            (&plan("   \n  "), "empty extracted plan body"),
            (&plan("work only"), "missing final diff_lines trailer"),
            (
                &plan("{\"archetypes\":[]}\ndiff_lines: 1"),
                "standalone scout manifest JSON is not allowed",
            ),
            (
                "LARCH_SUMMARY_BEGIN\n\nLARCH_SUMMARY_END\nLARCH_PLAN_BEGIN\nx\ndiff_lines: 1\nLARCH_PLAN_END\n",
                "empty extracted summary body",
            ),
            (
                "LARCH_SUMMARY_BEGIN\nLARCH_PLAN_BEGIN\nx\ndiff_lines: 1\nLARCH_PLAN_END\n",
                "require zero or one balanced pair",
            ),
        ];
        for (raw, expected) in cases {
            let error = parse_drafter_output(raw).expect_err("fatal response");
            assert!(
                error.message().contains(expected),
                "{raw:?} produced {:?}, expected {expected:?}",
                error.message()
            );
        }
    }

    #[test]
    fn scout_and_dialectic_failures_never_invalidate_a_good_plan() {
        let body = "LARCH_PLAN_BEGIN\nx\ndiff_lines: 1\nLARCH_PLAN_END\n";
        let cases = [
            (
                format!("{body}LARCH_SCOUT_BEGIN\nLARCH_SCOUT_END\n"),
                "empty_scout_json",
            ),
            (
                format!("{body}LARCH_SCOUT_BEGIN\nnot json\nLARCH_SCOUT_END\n"),
                "json_parse",
            ),
            (
                format!("{body}LARCH_SCOUT_BEGIN\n{{\"archetypes\":1}}\nLARCH_SCOUT_END\n"),
                "invalid_archetypes_shape",
            ),
            (
                format!("{body}LARCH_SCOUT_END\n"),
                "invalid_scout_sentinels",
            ),
        ];
        for (raw, expected) in cases {
            let parsed = parse_drafter_output(&raw).expect("plan still valid");
            assert_eq!(parsed.scout, DrafterScout::Invalid(expected));
            assert_eq!(parsed.scout.fail_reason(), expected);
        }
        let absent = parse_drafter_output(body).expect("plan still valid");
        assert_eq!(absent.scout, DrafterScout::Absent);
        assert_eq!(absent.scout.fail_reason(), "absent");
        assert_eq!(absent.dialectic, DrafterDialectic::Absent);

        let empty_dialectic = parse_drafter_output(&format!(
            "{body}LARCH_DIALECTIC_BEGIN\n \nLARCH_DIALECTIC_END\n"
        ))
        .expect("plan still valid");
        assert_eq!(
            empty_dialectic.dialectic,
            DrafterDialectic::Invalid("empty_dialectic_json")
        );
        let after_scout = parse_drafter_output(&format!(
            "{body}LARCH_SCOUT_BEGIN\n{{\"archetypes\":[]}}\nLARCH_SCOUT_END\nLARCH_DIALECTIC_BEGIN\n{{}}\nLARCH_DIALECTIC_END\n"
        ))
        .expect("plan still valid");
        assert_eq!(
            after_scout.dialectic,
            DrafterDialectic::Invalid("invalid_dialectic_sentinels")
        );
    }

    #[test]
    fn truncated_and_fenced_plans_follow_the_legacy_scout_manifest_scan() {
        assert!(!plan_contains_standalone_scout_manifest(
            "```\n{\"archetypes\":[]}\n```\n"
        ));
        assert!(plan_contains_standalone_scout_manifest(
            "```\n{\"archetypes\":[]}\n"
        ));
        assert!(!plan_contains_standalone_scout_manifest(
            "  {\"archetypes\":[]}\n"
        ));
        assert!(!plan_contains_standalone_scout_manifest(
            "{\"archetypes\":[]} trailing\n"
        ));
        assert!(!plan_contains_standalone_scout_manifest("{\"other\":[]}\n"));
        assert!(plan_contains_standalone_scout_manifest(
            "prose\n{\n  \"archetypes\": []\n}\nmore\n"
        ));
    }

    #[test]
    fn terminal_trailers_require_diff_lines_last_in_the_final_block() {
        assert_eq!(terminal_diff_lines("body\ndiff_lines: 7\n\n\n"), Some(7));
        assert_eq!(
            terminal_diff_lines("difficulty: HARD\ndiff_lines: 0\n"),
            Some(0)
        );
        assert_eq!(
            terminal_diff_lines("diff_lines: 7\nreview_status: x\n"),
            None
        );
        assert_eq!(terminal_diff_lines("diff_lines: seven\n"), None);
        assert_eq!(terminal_diff_lines("diff_lines: 1\nbody\n"), None);
        assert_eq!(
            terminal_diff_lines("diff_lines: 1\ndiff_lines: 2\n"),
            Some(2)
        );
        // `08` is not a valid size integer, so it ends the trailer block early
        // without hiding the `diff_lines` trailer that follows it.
        assert_eq!(
            terminal_diff_lines("diff_added: 08\ndiff_lines: 3\n"),
            Some(3)
        );
        assert_eq!(
            terminal_diff_lines("diff_added: 07\ndiff_lines: 3\n"),
            Some(3)
        );
    }

    #[test]
    fn status_rendering_omits_empty_optional_keys() {
        let mut status = DrafterStatus::prelaunch("prelaunch");
        assert_eq!(
            render_drafter_status(&status),
            "STATUS=ERROR\nPLAN_WRITTEN=false\nPLAN_LINES=0\nDIFF_LINES=0\nSUMMARY_WRITTEN=false\nSCOUT_WRITTEN=false\nDIALECTIC_CANDIDATES_PARSED=false\nDIALECTIC_RAW_PENDING_WRITTEN=false\nDRAFTER_LAUNCHED=false\nREASON=prelaunch\n"
        );
        status.reason = "";
        status.scout_fail_reason = "json_parse";
        status.dialectic_fail_reason = "invalid_dialectic_json";
        let rendered = render_drafter_status(&status);
        assert!(rendered.contains("SCOUT_FAIL_REASON=json_parse\n"));
        assert!(rendered.contains("DIALECTIC_CANDIDATES_FAIL_REASON=invalid_dialectic_json\n"));
        assert!(rendered.ends_with("DRAFTER_LAUNCHED=false\n"));
    }

    #[test]
    fn dirty_tree_rendering_covers_every_baseline_and_probe_combination() {
        assert_eq!(
            render_drafter_dirty_tree(DrafterDirtyTree::NotLaunched),
            "STATUS=unknown\nMODE=prelaunch\nREASON=launcher-exited-before-drafter-launch\n"
        );
        let launched = |porcelain, baseline| {
            render_drafter_dirty_tree(DrafterDirtyTree::Launched {
                tool: "codex",
                porcelain,
                baseline,
            })
        };
        assert_eq!(
            launched(Some(" M a\n"), Some(" M a\n")),
            "STATUS=clean\nMODE=baseline-delta\nREASON=codex-drafter-no-new-mutations\n"
        );
        // Producer differences in ordering and trailing whitespace are not mutations.
        assert_eq!(
            launched(Some(" M b\n M a\n"), Some(" M a  \n\n M b\n")),
            "STATUS=clean\nMODE=baseline-delta\nREASON=codex-drafter-no-new-mutations\n"
        );
        assert_eq!(
            launched(Some(" M b\n"), Some(" M a\n")),
            "STATUS=dirty\nMODE=baseline-delta\nREASON=codex-drafter-new-mutations\n"
        );
        assert_eq!(
            launched(None, Some(" M a\n")),
            "STATUS=unknown\nMODE=baseline-delta\nREASON=git-status-failed\n"
        );
        assert_eq!(
            launched(Some(""), None),
            "STATUS=clean\nMODE=absolute\nREASON=codex-drafter-clean-working-tree\n"
        );
        assert_eq!(
            launched(Some(" M a\n"), None),
            "STATUS=unknown\nMODE=no-baseline\nREASON=codex-drafter-no-usable-baseline\n"
        );
        assert_eq!(
            launched(None, None),
            "STATUS=unknown\nMODE=no-baseline\nREASON=git-status-failed\n"
        );
    }

    #[test]
    fn argument_rules_match_the_legacy_launcher_guards() {
        assert_eq!(validate_drafter_timeout("1800"), Ok(1800));
        assert_eq!(
            validate_drafter_timeout("1801"),
            Err(DrafterTimeoutError::TooLarge)
        );
        assert_eq!(
            validate_drafter_timeout("0"),
            Err(DrafterTimeoutError::NotPositive)
        );
        assert_eq!(
            validate_drafter_timeout("-1"),
            Err(DrafterTimeoutError::NotPositive)
        );
        assert!(drafter_path_text_allowed("/tmp/design/plan.txt"));
        assert!(!drafter_path_text_allowed("/tmp/../etc/passwd"));
        assert!(!drafter_path_text_allowed("/tmp/a\u{7f}b"));
        assert!(!drafter_path_text_allowed(""));
        assert!(drafter_model_allowed("claude-opus-5"));
        assert!(!drafter_model_allowed("claude opus"));
        assert!(!drafter_model_allowed(""));
        assert_eq!(drafter_token_raw_label("claude-plan-draft"), "claude_draft");
        assert_eq!(drafter_token_raw_label("claude-scout"), "claude_scout");
        assert_eq!(drafter_token_raw_label("voter-1"), "claude_vote");
        assert_eq!(drafter_token_raw_label("other"), "claude_review");
    }
}
