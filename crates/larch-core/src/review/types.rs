//! Typed review wire values and wrappers around the canonical item parser.

use crate::issue::{self, BlockBoundary, OosItemKind};
use num_bigint::BigUint;
use regex::Regex;
use std::{fmt, fs, path::Path, str::FromStr, sync::LazyLock};

/// Canonical prompt focus areas in their stable rendering order.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum FocusArea {
    CodeQuality,
    RiskIntegration,
    Correctness,
    Architecture,
    Security,
}

/// Stable prompt-rendering order for [`FocusArea`].
pub const FOCUS_AREA_VALUES: [&'static str; 5] = [
    "code-quality",
    "risk-integration",
    "correctness",
    "architecture",
    "security",
];

/// Stable membership projection for parsing reviewer input.
#[must_use]
pub fn focus_area_set() -> std::collections::BTreeSet<&'static str> {
    FOCUS_AREA_VALUES.iter().copied().collect()
}

/// Stable prompt-rendering order for [`FindingScope`].
pub const FINDING_SCOPE_VALUES: [&'static str; 2] = ["in_scope", "out_of_scope"];

/// Stable membership projection for parsing reviewer scope input.
#[must_use]
pub fn finding_scope_set() -> std::collections::BTreeSet<&'static str> {
    FINDING_SCOPE_VALUES.iter().copied().collect()
}

impl FocusArea {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::CodeQuality => "code-quality",
            Self::RiskIntegration => "risk-integration",
            Self::Correctness => "correctness",
            Self::Architecture => "architecture",
            Self::Security => "security",
        }
    }

    /// Stable declaration order.
    #[must_use]
    pub const fn all() -> [Self; 5] {
        [
            Self::CodeQuality,
            Self::RiskIntegration,
            Self::Correctness,
            Self::Architecture,
            Self::Security,
        ]
    }
}

impl fmt::Display for FocusArea {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

/// Scope values accepted by review classification wires.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum FindingScope {
    InScope,
    OutOfScope,
}

impl FindingScope {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::InScope => "in_scope",
            Self::OutOfScope => "out_of_scope",
        }
    }
}

/// Preserve unrecognized review statuses rather than coercing them.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ReviewCoreStatus {
    Ok,
    FixRequired,
    CapReached,
    ZeroFindings,
    PanelFailed,
    AggregatorValidationExhausted,
    MainAgentVoteRequired,
    PruneSkipped,
    Error,
    Exception,
    UnknownStatus,
    Unknown(String),
}

impl ReviewCoreStatus {
    /// Convert a wire value without losing forward-compatible values.
    #[must_use]
    pub fn from_wire(value: impl Into<String>) -> Self {
        let value = value.into();
        match value.as_str() {
            "ok" => Self::Ok,
            "fix-required" => Self::FixRequired,
            "cap-reached" => Self::CapReached,
            "zero-findings" => Self::ZeroFindings,
            "panel-failed" => Self::PanelFailed,
            "aggregator-validation-exhausted" => Self::AggregatorValidationExhausted,
            "main-agent-vote-required" => Self::MainAgentVoteRequired,
            "prune-skipped" => Self::PruneSkipped,
            "error" => Self::Error,
            "exception" => Self::Exception,
            "unknown" => Self::UnknownStatus,
            _ => Self::Unknown(value),
        }
    }

    /// Stable wire value for a known status, or the preserved unknown value.
    #[must_use]
    pub fn as_str(&self) -> &str {
        match self {
            Self::Ok => "ok",
            Self::FixRequired => "fix-required",
            Self::CapReached => "cap-reached",
            Self::ZeroFindings => "zero-findings",
            Self::PanelFailed => "panel-failed",
            Self::AggregatorValidationExhausted => "aggregator-validation-exhausted",
            Self::MainAgentVoteRequired => "main-agent-vote-required",
            Self::PruneSkipped => "prune-skipped",
            Self::Error => "error",
            Self::Exception => "exception",
            Self::UnknownStatus => "unknown",
            Self::Unknown(value) => value,
        }
    }
}

/// Preserve unrecognized votes rather than coercing them.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ReviewVote {
    Yes,
    No,
    JudgeError,
    Unknown(String),
}

impl ReviewVote {
    /// Convert a wire value without losing forward-compatible values.
    #[must_use]
    pub fn from_wire(value: impl Into<String>) -> Self {
        let value = value.into();
        match value.as_str() {
            "YES" => Self::Yes,
            "NO" => Self::No,
            "JUDGE_ERROR" => Self::JudgeError,
            _ => Self::Unknown(value),
        }
    }

    /// Stable wire value for a known vote, or the preserved unknown value.
    #[must_use]
    pub fn as_str(&self) -> &str {
        match self {
            Self::Yes => "YES",
            Self::No => "NO",
            Self::JudgeError => "JUDGE_ERROR",
            Self::Unknown(value) => value,
        }
    }
}

/// Preserve unrecognized severity values rather than coercing them.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum JudgeSeverity {
    Major,
    Minor,
    Nit,
    Unknown(String),
}

impl JudgeSeverity {
    /// Convert a wire value without losing forward-compatible values.
    #[must_use]
    pub fn from_wire(value: impl Into<String>) -> Self {
        let value = value.into();
        match value.as_str() {
            "major" => Self::Major,
            "minor" => Self::Minor,
            "nit" => Self::Nit,
            _ => Self::Unknown(value),
        }
    }

    /// Stable wire value for a known severity, or the preserved unknown value.
    #[must_use]
    pub fn as_str(&self) -> &str {
        match self {
            Self::Major => "major",
            Self::Minor => "minor",
            Self::Nit => "nit",
            Self::Unknown(value) => value,
        }
    }
}

/// A review heading ordinal without the OOS parser's compatibility saturation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReviewOrdinal {
    /// Exact decimal digits as authored, including leading zeroes.
    pub digits: String,
    /// Arbitrary-precision numeric projection of `digits`.
    pub value: BigUint,
}

/// One canonical heading exposed by the review library.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CanonicalHeading {
    /// Original item identifier.
    pub item_id: String,
    /// `FINDING` or `OOS`.
    pub kind: ItemKind,
    /// Lossless ordinal projection.
    pub ordinal: ReviewOrdinal,
    /// Heading title with Python-compatible whitespace removed.
    pub title: String,
}

/// Canonical reviewer-item kind.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ItemKind {
    Finding,
    Oos,
}

impl ItemKind {
    const fn from_issue(kind: OosItemKind) -> Self {
        match kind {
            OosItemKind::Finding => Self::Finding,
            OosItemKind::Oos => Self::Oos,
        }
    }
}

/// A source block whose public offsets count Unicode code points, not bytes.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParsedBlock {
    /// Original item identifier.
    pub item_id: String,
    /// Item kind.
    pub kind: ItemKind,
    /// Heading title.
    pub title: String,
    /// Exact source slice.
    pub block: String,
    /// Unicode-code-point offset of the start.
    pub start: usize,
    /// Unicode-code-point offset one past the end.
    pub end: usize,
}

/// Return the canonical code-review classification header.
#[must_use]
pub fn code_review_classification_header(include_tools: bool, include_scope: bool) -> String {
    let mut columns = vec![
        "finding_id".to_owned(),
        "reviewer_slots".to_owned(),
        "voting_result".to_owned(),
    ];
    for voter in 1..=3 {
        for field in [
            "vote",
            "correctness",
            "severity",
            "quality",
            "uncertain",
            "tool",
        ] {
            if include_tools || field != "tool" {
                columns.push(format!("v{voter}_{field}"));
            }
        }
    }
    if include_scope {
        columns.push("scope".to_owned());
    }
    columns.join("\t")
}

/// Return the required-column projection for a canonical header variant.
#[must_use]
pub fn code_review_classification_required_fields(
    include_tools: bool,
    include_scope: bool,
) -> std::collections::BTreeSet<String> {
    code_review_classification_header(include_tools, include_scope)
        .split('\t')
        .map(str::to_owned)
        .collect()
}

/// Render canonical wire values with the Python-compatible delimiters.
#[must_use]
pub fn render_wire_values(values: &[&str], delimiter: &str, quoted: bool) -> String {
    values
        .iter()
        .map(|value| {
            if quoted {
                format!("`{value}`")
            } else {
                (*value).to_owned()
            }
        })
        .collect::<Vec<_>>()
        .join(&format!(" {delimiter} "))
}

/// Parse an exact canonical heading, keeping the ordinal losslessly.
#[must_use]
pub fn parse_canonical_heading(line: &str) -> Option<CanonicalHeading> {
    let heading = issue::parse_canonical_heading(line)?;
    let value = BigUint::from_str(&heading.ordinal_digits).ok()?;
    Some(CanonicalHeading {
        item_id: heading.item_id,
        kind: ItemKind::from_issue(heading.kind),
        ordinal: ReviewOrdinal {
            digits: heading.ordinal_digits,
            value,
        },
        title: heading.title,
    })
}

/// Parse canonical blocks through the canonical issue parser.
#[must_use]
pub fn parse_blocks(text: &str, boundary: BoundaryMode) -> Vec<ParsedBlock> {
    issue::parse_oos_blocks(text, boundary.into())
        .into_iter()
        .map(|block| ParsedBlock {
            item_id: block.item_id,
            kind: ItemKind::from_issue(block.kind),
            title: block.title,
            block: block.block,
            start: text[..block.start].chars().count(),
            end: text[..block.end].chars().count(),
        })
        .collect()
}

/// Legacy finding-parser boundary selection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CompatibilityBoundary {
    /// Split only on `### FINDING_` headings.
    FindingHeading,
    /// Split on every level-three heading.
    AnyHeading,
}

impl Default for CompatibilityBoundary {
    fn default() -> Self {
        Self::AnyHeading
    }
}

/// Parser boundary compatibility modes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BoundaryMode {
    FindingHeading,
    OosHeading,
    ItemHeading,
    LevelThreeHeading,
}

impl From<BoundaryMode> for BlockBoundary {
    fn from(value: BoundaryMode) -> Self {
        match value {
            BoundaryMode::FindingHeading => Self::FindingHeading,
            BoundaryMode::OosHeading => Self::OosHeading,
            BoundaryMode::ItemHeading => Self::ItemHeading,
            BoundaryMode::LevelThreeHeading => Self::LevelThreeHeading,
        }
    }
}

/// Read a UTF-8 finding file with replacement decoding.
///
/// # Errors
///
/// Returns I/O errors other than a missing path.
pub fn read_finding_text(path: impl AsRef<Path>) -> Result<String, std::io::Error> {
    match fs::read(path) {
        Ok(bytes) => Ok(String::from_utf8_lossy(&bytes).into_owned()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(String::new()),
        Err(error) => Err(error),
    }
}

/// Parse only finding blocks with the legacy compatibility boundary selection.
#[must_use]
pub fn parse_findings_text(text: &str, boundary: CompatibilityBoundary) -> Vec<Finding> {
    let boundary_mode = match boundary {
        CompatibilityBoundary::FindingHeading => BoundaryMode::FindingHeading,
        CompatibilityBoundary::AnyHeading => BoundaryMode::LevelThreeHeading,
    };
    parse_blocks(text, boundary_mode)
        .into_iter()
        .filter(|block| block.kind == ItemKind::Finding)
        .map(|block| Finding {
            finding_id: block.item_id,
            title: block.title,
            block: block.block,
        })
        .collect()
}

/// Parse findings from a UTF-8 file with replacement decoding.
#[must_use]
pub fn parse_findings(path: impl AsRef<Path>, boundary: CompatibilityBoundary) -> Vec<Finding> {
    let text = read_finding_text(path).unwrap_or_else(|_| String::new());
    parse_findings_text(&text, boundary)
}

/// Report whether `line` is a canonical heading of the optional `kind`.
#[must_use]
pub fn is_canonical_heading(line: &str, kind: Option<ItemKind>) -> bool {
    let issue_kind = kind.map(|wanted| match wanted {
        ItemKind::Finding => OosItemKind::Finding,
        ItemKind::Oos => OosItemKind::Oos,
    });
    issue::is_canonical_heading(line, issue_kind)
}

/// Count fileable OOS blocks in `text`, excluding security-tagged ones.
#[must_use]
pub fn count_non_security_blocks(text: &str) -> usize {
    issue::count_non_security_blocks(text)
}

/// A finding-only compatibility value.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Finding {
    /// Canonical finding identifier.
    pub finding_id: String,
    /// Finding title.
    pub title: String,
    /// Exact markdown block.
    pub block: String,
}

/// Delegate security classification to the canonical parser owner.
#[must_use]
pub fn is_security_block_text(text: &str) -> bool {
    issue::is_security_block_text(text)
}

/// Delegate OOS eligibility to the canonical parser owner.
#[must_use]
pub fn is_oos_eligible_block(block: &ParsedBlock) -> bool {
    let issue_block = issue::OosBlock {
        item_id: block.item_id.clone(),
        kind: match block.kind {
            ItemKind::Finding => OosItemKind::Finding,
            ItemKind::Oos => OosItemKind::Oos,
        },
        title: block.title.clone(),
        block: block.block.clone(),
        start: 0,
        end: block.block.len(),
    };
    issue::is_oos_eligible_block(&issue_block)
}

static FIELD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^- \*\*((?i-u:Location|Concern))\*\*:\s*(.*?)\s*$").expect("field regex")
});
static FINDING_HEADER_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?m)^### FINDING_[0-9]+:.*$").expect("header regex"));
static SPACE_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\s+").expect("space regex"));

/// Return the stable Location/Concern finding identity used across rounds.
#[must_use]
pub fn finding_dedup_key(block: &str) -> String {
    let mut location: Option<&str> = None;
    let mut concern: Option<&str> = None;
    for captures in FIELD_RE.captures_iter(block) {
        if captures[1].eq_ignore_ascii_case("Location") && location.is_none() {
            location = Some(captures.get(2).map_or("", |value| value.as_str()));
        }
        if captures[1].eq_ignore_ascii_case("Concern") && concern.is_none() {
            concern = Some(captures.get(2).map_or("", |value| value.as_str()));
        }
    }
    let location = location.unwrap_or("");
    let concern = concern.unwrap_or("");
    let raw = if location.is_empty() && concern.is_empty() {
        FINDING_HEADER_RE.replace_all(block, "").into_owned()
    } else {
        format!("{location}\u{1f}{concern}")
    };
    SPACE_RE.replace_all(&raw, " ").trim().to_lowercase()
}
