//! Pure debate protocol vocabulary: wire constants, ledger parsing, and
//! fingerprints.
//!
//! Ports the vocabulary half of `python/larch/debate/protocol.py` (work items
//! 1-6 of leaf #8597). Side-effect free: no filesystem, environment, clock,
//! subprocess, or network access. Imports only std, `regex`, `sha2`,
//! `unicode-normalization`, and `crate::design`.

use crate::design::{TrailerKey, iter_plan_headings, iter_trailer_lines};
use regex::Regex;
use sha2::{Digest, Sha256};
use std::{collections::HashSet, fmt, fmt::Write as _, sync::LazyLock};
use unicode_normalization::UnicodeNormalization;

// ---------------------------------------------------------------------------
// Wire constants
// ---------------------------------------------------------------------------

/// Supported protocol wire version.
pub const PROTOCOL_VERSION: &str = "1";
/// Supported fingerprint-algorithm version.
pub const FINGERPRINT_ALGORITHM_VERSION: &str = "1";
/// Length of the lowercase hex fingerprint prefix.
pub const FINGERPRINT_HEX_LENGTH: usize = 16;
/// Maximum negotiation round index.
pub const ROUND_LIMIT: u8 = 2;
/// Minimum point-id number.
pub const POINT_ID_MIN: u16 = 1;
/// Maximum point-id number.
pub const POINT_ID_MAX: u16 = 9999;

/// Fixed debate panel slot order.
///
/// Membership owner is Python `larch.core.external_defaults.VALID_TOOLS`; this
/// module's purity constraint forbids depending on runtime configuration, and
/// the ordered triple has no Rust owner. Update this array when that vendor
/// set changes.
pub const SLOT_ORDER: [&str; 3] = ["cursor", "codex", "claude"];
/// Live-panel floor; independent of `SLOT_ORDER` length (the maximum).
pub const LIVE_PANEL_MINIMUM: usize = 2;
/// Live-panel ceiling.
pub const LIVE_PANEL_MAXIMUM: usize = SLOT_ORDER.len();

/// Leading token of every ledger row.
pub const LEDGER_POINT_TOKEN: &str = "POINT";
/// Prefix of every canonical point id token.
pub const POINT_ID_PREFIX: &str = "POINT_";
/// `AGREE` action token.
pub const ACTION_AGREE: &str = "AGREE";
/// `CONCEDE` action token.
pub const ACTION_CONCEDE: &str = "CONCEDE";
/// `HOLD` action token.
pub const ACTION_HOLD: &str = "HOLD";
/// All accepted action tokens.
pub const ACTION_TOKENS: [&str; 3] = [ACTION_AGREE, ACTION_CONCEDE, ACTION_HOLD];

/// Opening delimiter of an artifact citation.
pub const ARTIFACT_CITATION_PREFIX: &str = "[[artifact:";
/// Closing delimiter of an artifact citation.
pub const ARTIFACT_CITATION_SUFFIX: &str = "]]";

const RUN_LOCAL_PLACEHOLDER_PREFIX: &str = "<run-local:";
const RUN_LOCAL_PLACEHOLDER_SUFFIX: &str = ">";

// Every pattern below is built from the wire constants above so each literal
// has exactly one owner. Editing a constant moves its parser with it.
static LEDGER_ROW_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(&format!(
        r"^{} (\S+) (\S+) (.*)$",
        regex::escape(LEDGER_POINT_TOKEN)
    ))
    .expect("ledger row regex")
});
static ARTIFACT_CITATION_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(&format!(
        r"{}([^\]]*){}",
        regex::escape(ARTIFACT_CITATION_PREFIX),
        regex::escape(ARTIFACT_CITATION_SUFFIX)
    ))
    .expect("artifact citation regex")
});

/// Whether `c` is a forbidden control or line-separator character.
///
/// Mirrors Python `_CONTROL_OR_FORBIDDEN_RE`: U+0000-U+0008, TAB, U+000B,
/// U+000C, CR, U+000E-U+001F, U+007F, U+2028, and U+2029. LF is permitted as
/// the row separator.
const fn is_forbidden_char(c: char) -> bool {
    matches!(
        c,
        '\u{0000}'..='\u{0008}'
            | '\t'
            | '\u{000B}'
            | '\u{000C}'
            | '\r'
            | '\u{000E}'..='\u{001F}'
            | '\u{007F}'
            | '\u{2028}'
            | '\u{2029}'
    )
}

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

/// Fixed debate panel slots.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum Participant {
    /// The `cursor` slot.
    Cursor,
    /// The `codex` slot.
    Codex,
    /// The `claude` slot.
    Claude,
}

impl Participant {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Cursor => "cursor",
            Self::Codex => "codex",
            Self::Claude => "claude",
        }
    }
}

/// Per-point ledger actions.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum Action {
    /// The `AGREE` action.
    Agree,
    /// The `CONCEDE` action.
    Concede,
    /// The `HOLD` action.
    Hold,
}

impl Action {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Agree => ACTION_AGREE,
            Self::Concede => ACTION_CONCEDE,
            Self::Hold => ACTION_HOLD,
        }
    }
}

/// Citation status for a ledger reason.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum ConcessionClassification {
    /// Concession with a valid point or artifact citation.
    Cited,
    /// Concession without a valid citation.
    Fold,
    /// Non-concession action.
    NonConcession,
}

impl ConcessionClassification {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Cited => "cited",
            Self::Fold => "fold",
            Self::NonConcession => "non-concession",
        }
    }
}

/// Stable fail-closed rejection tokens for protocol parsing and validation.
///
/// Each variant's stable wire token is returned by
/// [`ParseRejectionReason::as_str`].
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum ParseRejectionReason {
    EmptySubmission,
    BlankRow,
    ForbiddenCharacter,
    LeadingOrTrailingWhitespace,
    RepeatedSeparatorSpaces,
    MalformedRow,
    UnknownAction,
    EmptyReason,
    MalformedPointId,
    PointIdOutOfRange,
    DuplicatePointId,
    ForbiddenPlanContent,
    InvalidSlot,
    InvalidArtifactPath,
    InvalidProtocolVersion,
    InvalidFingerprintVersion,
    InvalidFingerprint,
    EmptyReplacementNeedle,
    InvalidRoundNumber,
    InvalidSlotOrdering,
    BelowLivePanelFloor,
    AboveLivePanelCeiling,
    PointUniverseMismatch,
    FingerprintMismatch,
    MalformedAdjudication,
    IncompleteAdjudicationCoverage,
    IllegalTransition,
    EmptyPointUniverse,
    NonadjacentRounds,
    InvalidRunLocalValues,
    InvalidProposalState,
}

impl ParseRejectionReason {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::EmptySubmission => "empty-submission",
            Self::BlankRow => "blank-row",
            Self::ForbiddenCharacter => "forbidden-character",
            Self::LeadingOrTrailingWhitespace => "leading-or-trailing-whitespace",
            Self::RepeatedSeparatorSpaces => "repeated-separator-spaces",
            Self::MalformedRow => "malformed-row",
            Self::UnknownAction => "unknown-action",
            Self::EmptyReason => "empty-reason",
            Self::MalformedPointId => "malformed-point-id",
            Self::PointIdOutOfRange => "point-id-out-of-range",
            Self::DuplicatePointId => "duplicate-point-id",
            Self::ForbiddenPlanContent => "forbidden-plan-content",
            Self::InvalidSlot => "invalid-slot",
            Self::InvalidArtifactPath => "invalid-artifact-path",
            Self::InvalidProtocolVersion => "invalid-protocol-version",
            Self::InvalidFingerprintVersion => "invalid-fingerprint-version",
            Self::InvalidFingerprint => "invalid-fingerprint",
            Self::EmptyReplacementNeedle => "empty-replacement-needle",
            Self::InvalidRoundNumber => "invalid-round-number",
            Self::InvalidSlotOrdering => "invalid-slot-ordering",
            Self::BelowLivePanelFloor => "below-live-panel-floor",
            Self::AboveLivePanelCeiling => "above-live-panel-ceiling",
            Self::PointUniverseMismatch => "point-universe-mismatch",
            Self::FingerprintMismatch => "fingerprint-mismatch",
            Self::MalformedAdjudication => "malformed-adjudication",
            Self::IncompleteAdjudicationCoverage => "incomplete-adjudication-coverage",
            Self::IllegalTransition => "illegal-transition",
            Self::EmptyPointUniverse => "empty-point-universe",
            Self::NonadjacentRounds => "nonadjacent-rounds",
            Self::InvalidRunLocalValues => "invalid-run-local-values",
            Self::InvalidProposalState => "invalid-proposal-state",
        }
    }
}

impl fmt::Display for ParseRejectionReason {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

impl std::error::Error for ParseRejectionReason {}

/// Negotiation round index; membership is pinned to [`ROUND_LIMIT`].
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
#[repr(u8)]
pub enum RoundNumber {
    /// Round 1.
    Round1 = 1,
    /// Round 2.
    Round2 = 2,
}

/// Per-point resolution derived from the normative closure predicate.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum PointResolution {
    /// All live slots agreed.
    Agreed,
    /// Closed by concession.
    Conceded,
    /// Held open.
    Held,
    /// Folded concession.
    Folded,
}

impl PointResolution {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Agreed => "AGREED",
            Self::Conceded => "CONCEDED",
            Self::Held => "HELD",
            Self::Folded => "FOLDED",
        }
    }
}

/// Nonterminal proposal phases of the debate state machine.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum NonterminalPhase {
    /// Blind round 1.
    BlindRound1,
    /// Round 2.
    Round2,
    /// Awaiting adjudication.
    AwaitingAdjudication,
    /// Unconverged.
    Unconverged,
}

impl NonterminalPhase {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::BlindRound1 => "BLIND_ROUND_1",
            Self::Round2 => "ROUND_2",
            Self::AwaitingAdjudication => "AWAITING_ADJUDICATION",
            Self::Unconverged => "UNCONVERGED",
        }
    }
}

/// Terminal proposal outcomes; never enter the transition table as sources.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum TerminalOutcome {
    /// Converged.
    Converged,
    /// Stalemate.
    Stalemate,
    /// Both proposals viable.
    BothViable,
    /// Aborted.
    Aborted,
}

impl TerminalOutcome {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Converged => "CONVERGED",
            Self::Stalemate => "STALEMATE",
            Self::BothViable => "BOTH_VIABLE",
            Self::Aborted => "ABORTED",
        }
    }
}

/// Adjudication record variant.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum AdjudicationDecision {
    /// One position selected.
    Selected,
    /// Split decision.
    Split,
}

impl AdjudicationDecision {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Selected => "SELECTED",
            Self::Split => "SPLIT",
        }
    }
}

/// Whether stalemate detection ran or was skipped for changed membership.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum StalemateDetectionStatus {
    /// Detection ran to completion.
    Completed,
    /// Detection skipped because panel membership changed.
    MembershipChanged,
}

impl StalemateDetectionStatus {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Completed => "COMPLETED",
            Self::MembershipChanged => "MEMBERSHIP_CHANGED",
        }
    }
}

/// Explicit transition-table actions.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum TransitionAction {
    /// Submit a round.
    SubmitRound,
    /// Declare a stalemate.
    DeclareStalemate,
    /// Adjudicate.
    Adjudicate,
    /// Abort.
    Abort,
}

impl TransitionAction {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::SubmitRound => "SUBMIT_ROUND",
            Self::DeclareStalemate => "DECLARE_STALEMATE",
            Self::Adjudicate => "ADJUDICATE",
            Self::Abort => "ABORT",
        }
    }
}

// ---------------------------------------------------------------------------
// Validated value objects
// ---------------------------------------------------------------------------

/// Inclusive `POINT_1` … `POINT_9999` identity.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub struct PointId(u16);

impl PointId {
    /// Validate a point-id number into a [`PointId`].
    ///
    /// # Errors
    ///
    /// Returns [`ParseRejectionReason::PointIdOutOfRange`] outside
    /// [`POINT_ID_MIN`]..=[`POINT_ID_MAX`].
    pub const fn new(number: u16) -> Result<Self, ParseRejectionReason> {
        if number < POINT_ID_MIN || number > POINT_ID_MAX {
            return Err(ParseRejectionReason::PointIdOutOfRange);
        }
        Ok(Self(number))
    }

    /// The validated point-id number.
    #[must_use]
    pub const fn number(self) -> u16 {
        self.0
    }

    /// The canonical `POINT_N` token.
    #[must_use]
    pub fn token(self) -> String {
        format!("{POINT_ID_PREFIX}{}", self.0)
    }

    /// Parse a canonical `POINT_N` token.
    ///
    /// ASCII digits only. Python `str.isdigit()` also accepts non-ASCII
    /// digits, but such tokens cannot round-trip through the canonical
    /// grammar, and the executable-contract tests pin ASCII only; they are
    /// rejected here as malformed.
    ///
    /// # Errors
    ///
    /// Returns [`ParseRejectionReason::MalformedPointId`] for a missing
    /// prefix, empty or non-digit rest, or a leading zero, and
    /// [`ParseRejectionReason::PointIdOutOfRange`] above [`POINT_ID_MAX`].
    pub fn from_token(token: &str) -> Result<Self, ParseRejectionReason> {
        let Some(rest) = token.strip_prefix(POINT_ID_PREFIX) else {
            return Err(ParseRejectionReason::MalformedPointId);
        };
        if rest.is_empty() || !rest.bytes().all(|byte| byte.is_ascii_digit()) {
            return Err(ParseRejectionReason::MalformedPointId);
        }
        if rest.starts_with('0') {
            return Err(ParseRejectionReason::MalformedPointId);
        }
        // Arbitrary-length digit runs overflow u32 only when far above the
        // maximum, so overflow classifies as out-of-range like Python int().
        let number: u32 = rest
            .parse()
            .map_err(|_| ParseRejectionReason::PointIdOutOfRange)?;
        if number > u32::from(POINT_ID_MAX) {
            return Err(ParseRejectionReason::PointIdOutOfRange);
        }
        Self::new(u16::try_from(number).map_err(|_| ParseRejectionReason::PointIdOutOfRange)?)
    }
}

/// Validated 16-character lowercase hex fingerprint prefix.
#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub struct ReasonFingerprint(String);

impl ReasonFingerprint {
    /// Validate a fingerprint hex prefix.
    ///
    /// # Errors
    ///
    /// Returns [`ParseRejectionReason::InvalidFingerprint`] unless the value
    /// is exactly [`FINGERPRINT_HEX_LENGTH`] lowercase hexadecimal characters.
    pub fn new(value: String) -> Result<Self, ParseRejectionReason> {
        if is_valid_fingerprint(&value) {
            Ok(Self(value))
        } else {
            Err(ParseRejectionReason::InvalidFingerprint)
        }
    }

    /// The validated fingerprint text.
    #[must_use]
    pub fn value(&self) -> &str {
        &self.0
    }
}

/// One parsed `POINT POINT_N <ACTION> <reason>` row.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LedgerRow {
    /// The row's point identity.
    pub point_id: PointId,
    /// The row's action.
    pub action: Action,
    /// The verbatim reason text.
    pub reason: String,
    /// Concession citation classification.
    pub concession: ConcessionClassification,
}

/// Parsed rows for one slot submission.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParsedSlotLedger {
    /// Parsed rows in submission order.
    pub rows: Vec<LedgerRow>,
}

// ---------------------------------------------------------------------------
// Lexical validators
// ---------------------------------------------------------------------------

/// Whether `value` is one of the fixed panel slots.
#[must_use]
pub fn is_valid_slot(value: &str) -> bool {
    SLOT_ORDER.contains(&value)
}

/// Parse a slot name into [`Participant`].
///
/// # Errors
///
/// Returns [`ParseRejectionReason::InvalidSlot`] for an unknown slot.
pub fn parse_slot(value: &str) -> Result<Participant, ParseRejectionReason> {
    match value {
        "cursor" => Ok(Participant::Cursor),
        "codex" => Ok(Participant::Codex),
        "claude" => Ok(Participant::Claude),
        _ => Err(ParseRejectionReason::InvalidSlot),
    }
}

/// Whether `token` is a canonical `POINT_N` in range.
#[must_use]
pub fn is_valid_point_token(token: &str) -> bool {
    PointId::from_token(token).is_ok()
}

/// Whether `path` is a nonempty relative POSIX artifact path.
///
/// Rejects absolute paths, empty or `.` / `..` segments, parent traversal,
/// backslashes, controls, and malformed separators. Spaces inside otherwise
/// valid segments are permitted.
#[must_use]
pub fn is_valid_artifact_path(path: &str) -> bool {
    if path.is_empty() || path.starts_with('/') || path.contains('\\') || path.ends_with('/') {
        return false;
    }
    if path.chars().any(is_forbidden_char) {
        return false;
    }
    if path.contains("//") {
        return false;
    }
    path.split('/')
        .all(|segment| !segment.is_empty() && segment != "." && segment != "..")
}

/// Whether `value` is the supported protocol version.
#[must_use]
pub fn is_valid_protocol_version(value: &str) -> bool {
    value == PROTOCOL_VERSION
}

/// Whether `value` is the supported fingerprint-algorithm version.
#[must_use]
pub fn is_valid_fingerprint_version(value: &str) -> bool {
    value == FINGERPRINT_ALGORITHM_VERSION
}

/// Whether `value` is exactly 16 lowercase hexadecimal characters.
#[must_use]
pub fn is_valid_fingerprint(value: &str) -> bool {
    value.len() == FINGERPRINT_HEX_LENGTH
        && value
            .bytes()
            .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
}

/// Accept the supported protocol version.
///
/// # Errors
///
/// Returns [`ParseRejectionReason::InvalidProtocolVersion`] otherwise.
pub fn parse_protocol_version(value: &str) -> Result<&str, ParseRejectionReason> {
    if is_valid_protocol_version(value) {
        Ok(value)
    } else {
        Err(ParseRejectionReason::InvalidProtocolVersion)
    }
}

/// Accept the supported fingerprint-algorithm version.
///
/// # Errors
///
/// Returns [`ParseRejectionReason::InvalidFingerprintVersion`] otherwise.
pub fn parse_fingerprint_version(value: &str) -> Result<&str, ParseRejectionReason> {
    if is_valid_fingerprint_version(value) {
        Ok(value)
    } else {
        Err(ParseRejectionReason::InvalidFingerprintVersion)
    }
}

/// Parse a fingerprint hex prefix into [`ReasonFingerprint`].
///
/// # Errors
///
/// Returns [`ParseRejectionReason::InvalidFingerprint`] for a malformed value.
pub fn parse_fingerprint(value: &str) -> Result<ReasonFingerprint, ParseRejectionReason> {
    ReasonFingerprint::new(value.to_owned())
}

// ---------------------------------------------------------------------------
// Forbidden plan content
// ---------------------------------------------------------------------------

/// Reject canonical plan headings and whole-line `diff_lines:` trailers.
///
/// Uses the `crate::design` plan-grammar iterators only; other trailer keys
/// such as `difficulty:` and `review_status:` are not rejected as trailers.
///
/// # Errors
///
/// Returns [`ParseRejectionReason::ForbiddenPlanContent`] when `text`
/// contains a canonical plan heading or a `diff_lines:` trailer line.
pub fn reject_forbidden_plan_content(text: &str) -> Result<(), ParseRejectionReason> {
    if !iter_plan_headings(text, None).is_empty() {
        return Err(ParseRejectionReason::ForbiddenPlanContent);
    }
    if !iter_trailer_lines(text, Some(&[TrailerKey::DiffLines])).is_empty() {
        return Err(ParseRejectionReason::ForbiddenPlanContent);
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Ledger parsing
// ---------------------------------------------------------------------------

fn preflight_charset(submission: &str) -> Result<(), ParseRejectionReason> {
    if submission.chars().any(is_forbidden_char) {
        return Err(ParseRejectionReason::ForbiddenCharacter);
    }
    Ok(())
}

/// Match one LF-free row and return `(point token, action token, reason)`.
fn match_ledger_row(row: &str) -> Result<(&str, &str, &str), ParseRejectionReason> {
    if row.starts_with(' ') {
        return Err(ParseRejectionReason::LeadingOrTrailingWhitespace);
    }
    let Some(captures) = LEDGER_ROW_RE.captures(row) else {
        if row.contains("  ") {
            return Err(ParseRejectionReason::RepeatedSeparatorSpaces);
        }
        return Err(ParseRejectionReason::MalformedRow);
    };
    let (Some(point), Some(action), Some(reason)) =
        (captures.get(1), captures.get(2), captures.get(3))
    else {
        return Err(ParseRejectionReason::MalformedRow);
    };
    // Structural separators are the single spaces before the reason. Reason-
    // internal spacing, including doubled spaces, is preserved byte for byte.
    if row[..reason.start()].contains("  ") {
        return Err(ParseRejectionReason::RepeatedSeparatorSpaces);
    }
    Ok((point.as_str(), action.as_str(), reason.as_str()))
}

fn parse_point_id(token: &str, seen: &mut HashSet<u16>) -> Result<PointId, ParseRejectionReason> {
    let point_id = PointId::from_token(token).map_err(|reason| {
        if reason == ParseRejectionReason::PointIdOutOfRange {
            reason
        } else {
            ParseRejectionReason::MalformedPointId
        }
    })?;
    if !seen.insert(point_id.number()) {
        return Err(ParseRejectionReason::DuplicatePointId);
    }
    Ok(point_id)
}

fn parse_action(token: &str) -> Result<Action, ParseRejectionReason> {
    match token {
        ACTION_AGREE => Ok(Action::Agree),
        ACTION_CONCEDE => Ok(Action::Concede),
        ACTION_HOLD => Ok(Action::Hold),
        _ => Err(ParseRejectionReason::UnknownAction),
    }
}

fn parse_ledger_row(row: &str, seen: &mut HashSet<u16>) -> Result<LedgerRow, ParseRejectionReason> {
    let (point_token, action_token, reason) = match_ledger_row(row)?;
    if reason.is_empty() {
        return Err(ParseRejectionReason::EmptyReason);
    }
    if reason.ends_with(' ') {
        return Err(ParseRejectionReason::LeadingOrTrailingWhitespace);
    }

    let point_id = parse_point_id(point_token, seen)?;
    let action = parse_action(action_token)?;
    reject_forbidden_plan_content(reason)?;
    Ok(LedgerRow {
        point_id,
        action,
        reason: reason.to_owned(),
        concession: classify_concession(action, reason),
    })
}

/// Parse one slot submission with LF-only row separation.
///
/// Splits only on literal LF. A trailing newline yields a final empty segment
/// and is rejected as a blank row. Duplicate point tracking is local to this
/// call.
///
/// # Errors
///
/// Returns the exact [`ParseRejectionReason`] for the first defective row:
/// empty submission, forbidden characters, blank rows, whitespace and
/// separator defects, malformed rows, unknown actions, empty reasons, point-id
/// defects and duplicates, and forbidden plan content inside reasons.
pub fn parse_slot_ledger(submission: &str) -> Result<ParsedSlotLedger, ParseRejectionReason> {
    if submission.is_empty() {
        return Err(ParseRejectionReason::EmptySubmission);
    }
    preflight_charset(submission)?;

    let segments: Vec<&str> = submission.split('\n').collect();
    if segments.iter().any(|segment| segment.is_empty()) {
        return Err(ParseRejectionReason::BlankRow);
    }

    let mut seen: HashSet<u16> = HashSet::new();
    let rows = segments
        .into_iter()
        .map(|segment| parse_ledger_row(segment, &mut seen))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(ParsedSlotLedger { rows })
}

// ---------------------------------------------------------------------------
// Concession citation classification
// ---------------------------------------------------------------------------

/// Whether `reason` contains a bounded `POINT POINT_N` citation.
///
/// The `regex` crate has no lookaround, so this reimplements Python
/// `_POINT_CITATION_RE` semantics explicitly: the character before each
/// `POINT POINT_` occurrence (if any) must not be ASCII alphanumeric or `_`,
/// and the maximal `[0-9A-Za-z_]` run after the prefix must fully match
/// `[1-9][0-9]{0,3}` and pass [`is_valid_point_token`].
fn has_valid_point_citation(reason: &str) -> bool {
    let needle = format!("{LEDGER_POINT_TOKEN} {POINT_ID_PREFIX}");
    for (start, _) in reason.match_indices(&needle) {
        let bounded_before = reason[..start]
            .chars()
            .next_back()
            .is_none_or(|previous| !(previous.is_ascii_alphanumeric() || previous == '_'));
        if !bounded_before {
            continue;
        }
        let after = &reason[start + needle.len()..];
        let run_len = after
            .bytes()
            .take_while(|byte| byte.is_ascii_alphanumeric() || *byte == b'_')
            .count();
        let run = &after[..run_len];
        let digits_in_range = (1..=4).contains(&run.len())
            && run.starts_with(|c: char| c.is_ascii_digit() && c != '0')
            && run.bytes().all(|byte| byte.is_ascii_digit());
        if digits_in_range && is_valid_point_token(&format!("{POINT_ID_PREFIX}{run}")) {
            return true;
        }
    }
    false
}

fn has_valid_artifact_citation(reason: &str) -> bool {
    ARTIFACT_CITATION_RE
        .captures_iter(reason)
        .filter_map(|captures| captures.get(1))
        .any(|path| is_valid_artifact_path(path.as_str()))
}

/// Classify a reason's concession citation status.
///
/// `CONCEDE` reasons are `cited` when they contain at least one complete
/// bounded `POINT POINT_N` citation or an exact
/// `[[artifact:RELATIVE_POSIX_PATH]]` citation with a valid path. Otherwise
/// they are `fold`. Non-concession actions receive `non-concession`.
/// Malformed near-miss citations do not invalidate the reason; they simply
/// leave a concession classified as a fold. The original reason is retained
/// by the caller in either case.
#[must_use]
pub fn classify_concession(action: Action, reason: &str) -> ConcessionClassification {
    if action != Action::Concede {
        return ConcessionClassification::NonConcession;
    }
    if has_valid_point_citation(reason) || has_valid_artifact_citation(reason) {
        return ConcessionClassification::Cited;
    }
    ConcessionClassification::Fold
}

// ---------------------------------------------------------------------------
// Fingerprinting
// ---------------------------------------------------------------------------

/// NFKC-normalize `reason` and replace run-local values deterministically.
///
/// Replacement needles are taken from `run_local_values`. Empty needles are
/// rejected. Needles are applied longest-first (by code-point count), then
/// lexicographically, so overlapping values and caller order cannot change
/// the result. Placeholders are not protected from later needles, matching
/// Python's naive sequential replacement byte for byte.
///
/// # Errors
///
/// Returns [`ParseRejectionReason::EmptyReplacementNeedle`] when any needle
/// is empty.
pub fn normalize_reason_for_fingerprint(
    reason: &str,
    run_local_values: &[&str],
) -> Result<String, ParseRejectionReason> {
    if run_local_values.iter().any(|needle| needle.is_empty()) {
        return Err(ParseRejectionReason::EmptyReplacementNeedle);
    }

    let mut text: String = reason.nfkc().collect();
    let mut unique: Vec<&str> = run_local_values.to_vec();
    unique.sort_unstable();
    unique.dedup();
    // Python sorts by (-len(item), item); str len counts code points and str
    // order is code-point order, which UTF-8 byte order preserves.
    unique.sort_by(|left, right| {
        right
            .chars()
            .count()
            .cmp(&left.chars().count())
            .then_with(|| left.cmp(right))
    });
    for (index, needle) in unique.iter().enumerate() {
        let placeholder =
            format!("{RUN_LOCAL_PLACEHOLDER_PREFIX}{index}{RUN_LOCAL_PLACEHOLDER_SUFFIX}");
        text = text.replace(needle, &placeholder);
    }
    Ok(text)
}

/// Return a versioned 16-character lowercase SHA-256 fingerprint prefix.
///
/// Domain-separates the hash with [`FINGERPRINT_ALGORITHM_VERSION`]. Does not
/// read clocks, environment, filesystem, working directory, or other ambient
/// metadata unless the caller supplies those values for placeholder
/// replacement.
///
/// # Errors
///
/// Returns [`ParseRejectionReason::EmptyReplacementNeedle`] when any needle
/// is empty.
pub fn fingerprint_reason(
    reason: &str,
    run_local_values: &[&str],
) -> Result<ReasonFingerprint, ParseRejectionReason> {
    let normalized = normalize_reason_for_fingerprint(reason, run_local_values)?;
    let payload = format!("{FINGERPRINT_ALGORITHM_VERSION}\0{normalized}");
    let digest = Sha256::digest(payload.as_bytes());
    let mut hex = String::with_capacity(FINGERPRINT_HEX_LENGTH);
    for byte in digest.iter().take(FINGERPRINT_HEX_LENGTH / 2) {
        let _ignored = write!(&mut hex, "{byte:02x}");
    }
    ReasonFingerprint::new(hex)
}

#[cfg(test)]
mod tests {
    use super::{
        ACTION_AGREE, ACTION_CONCEDE, ACTION_HOLD, ACTION_TOKENS, ARTIFACT_CITATION_PREFIX,
        ARTIFACT_CITATION_SUFFIX, Action as A, AdjudicationDecision, ConcessionClassification as C,
        FINGERPRINT_ALGORITHM_VERSION, FINGERPRINT_HEX_LENGTH, LEDGER_POINT_TOKEN,
        LIVE_PANEL_MAXIMUM, LIVE_PANEL_MINIMUM, NonterminalPhase, POINT_ID_MAX, POINT_ID_MIN,
        POINT_ID_PREFIX, PROTOCOL_VERSION, ParseRejectionReason as R, Participant, PointId,
        PointResolution, ROUND_LIMIT, RoundNumber, SLOT_ORDER, StalemateDetectionStatus,
        TerminalOutcome, TransitionAction, classify_concession, fingerprint_reason,
        is_valid_artifact_path, is_valid_fingerprint, is_valid_fingerprint_version,
        is_valid_point_token, is_valid_protocol_version, is_valid_slot,
        normalize_reason_for_fingerprint, parse_fingerprint, parse_fingerprint_version,
        parse_protocol_version, parse_slot, parse_slot_ledger, reject_forbidden_plan_content,
    };

    // -----------------------------------------------------------------------
    // Constants and enum membership (mirrors test_protocol.py:257-328)
    // -----------------------------------------------------------------------

    #[test]
    fn exported_constants() {
        assert_eq!(PROTOCOL_VERSION, "1");
        assert_eq!(FINGERPRINT_ALGORITHM_VERSION, "1");
        assert_eq!(FINGERPRINT_HEX_LENGTH, 16);
        assert_eq!(ROUND_LIMIT, 2);
        assert_eq!(POINT_ID_MIN, 1);
        assert_eq!(POINT_ID_MAX, 9999);
        assert_eq!(SLOT_ORDER, ["cursor", "codex", "claude"]);
        assert_eq!(LIVE_PANEL_MINIMUM, 2);
        assert_eq!(SLOT_ORDER.len(), LIVE_PANEL_MAXIMUM);
        assert_eq!(LEDGER_POINT_TOKEN, "POINT");
        assert_eq!(POINT_ID_PREFIX, "POINT_");
        assert_eq!(ACTION_AGREE, "AGREE");
        assert_eq!(ACTION_CONCEDE, "CONCEDE");
        assert_eq!(ACTION_HOLD, "HOLD");
        assert_eq!(ACTION_TOKENS, [ACTION_AGREE, ACTION_CONCEDE, ACTION_HOLD]);
        assert_eq!(ARTIFACT_CITATION_PREFIX, "[[artifact:");
        assert_eq!(ARTIFACT_CITATION_SUFFIX, "]]");
    }

    #[test]
    #[rustfmt::skip]
    fn enum_membership_and_values() {
        assert_eq!([Participant::Cursor, Participant::Codex, Participant::Claude].map(Participant::as_str), SLOT_ORDER);
        assert_eq!([A::Agree, A::Concede, A::Hold].map(A::as_str), ACTION_TOKENS);
        assert_eq!([C::Cited, C::Fold, C::NonConcession].map(C::as_str), ["cited", "fold", "non-concession"]);
        assert_eq!(
            [PointResolution::Agreed, PointResolution::Conceded, PointResolution::Held, PointResolution::Folded]
                .map(PointResolution::as_str),
            ["AGREED", "CONCEDED", "HELD", "FOLDED"]
        );
        assert_eq!(
            [NonterminalPhase::BlindRound1, NonterminalPhase::Round2, NonterminalPhase::AwaitingAdjudication, NonterminalPhase::Unconverged]
                .map(NonterminalPhase::as_str),
            ["BLIND_ROUND_1", "ROUND_2", "AWAITING_ADJUDICATION", "UNCONVERGED"]
        );
        assert_eq!(
            [TerminalOutcome::Converged, TerminalOutcome::Stalemate, TerminalOutcome::BothViable, TerminalOutcome::Aborted]
                .map(TerminalOutcome::as_str),
            ["CONVERGED", "STALEMATE", "BOTH_VIABLE", "ABORTED"]
        );
        assert_eq!(
            [AdjudicationDecision::Selected, AdjudicationDecision::Split].map(AdjudicationDecision::as_str),
            ["SELECTED", "SPLIT"]
        );
        assert_eq!(
            [StalemateDetectionStatus::Completed, StalemateDetectionStatus::MembershipChanged]
                .map(StalemateDetectionStatus::as_str),
            ["COMPLETED", "MEMBERSHIP_CHANGED"]
        );
        assert_eq!(
            [TransitionAction::SubmitRound, TransitionAction::DeclareStalemate, TransitionAction::Adjudicate, TransitionAction::Abort]
                .map(TransitionAction::as_str),
            ["SUBMIT_ROUND", "DECLARE_STALEMATE", "ADJUDICATE", "ABORT"]
        );
    }

    #[test]
    fn round_number_membership_pins_round_limit() {
        // Mirrors _pin_round_number_enum: discriminants == 1..=ROUND_LIMIT.
        let members = [RoundNumber::Round1, RoundNumber::Round2];
        let discriminants: Vec<u8> = members.iter().map(|member| *member as u8).collect();
        let expected: Vec<u8> = (1..=ROUND_LIMIT).collect();
        assert_eq!(discriminants, expected);
    }

    #[test]
    #[rustfmt::skip]
    fn rejection_reason_tokens_match_python() {
        let tokens = [
            (R::EmptySubmission, "empty-submission"),
            (R::BlankRow, "blank-row"),
            (R::ForbiddenCharacter, "forbidden-character"),
            (R::LeadingOrTrailingWhitespace, "leading-or-trailing-whitespace"),
            (R::RepeatedSeparatorSpaces, "repeated-separator-spaces"),
            (R::MalformedRow, "malformed-row"),
            (R::UnknownAction, "unknown-action"),
            (R::EmptyReason, "empty-reason"),
            (R::MalformedPointId, "malformed-point-id"),
            (R::PointIdOutOfRange, "point-id-out-of-range"),
            (R::DuplicatePointId, "duplicate-point-id"),
            (R::ForbiddenPlanContent, "forbidden-plan-content"),
            (R::InvalidSlot, "invalid-slot"),
            (R::InvalidArtifactPath, "invalid-artifact-path"),
            (R::InvalidProtocolVersion, "invalid-protocol-version"),
            (R::InvalidFingerprintVersion, "invalid-fingerprint-version"),
            (R::InvalidFingerprint, "invalid-fingerprint"),
            (R::EmptyReplacementNeedle, "empty-replacement-needle"),
            (R::InvalidRoundNumber, "invalid-round-number"),
            (R::InvalidSlotOrdering, "invalid-slot-ordering"),
            (R::BelowLivePanelFloor, "below-live-panel-floor"),
            (R::AboveLivePanelCeiling, "above-live-panel-ceiling"),
            (R::PointUniverseMismatch, "point-universe-mismatch"),
            (R::FingerprintMismatch, "fingerprint-mismatch"),
            (R::MalformedAdjudication, "malformed-adjudication"),
            (R::IncompleteAdjudicationCoverage, "incomplete-adjudication-coverage"),
            (R::IllegalTransition, "illegal-transition"),
            (R::EmptyPointUniverse, "empty-point-universe"),
            (R::NonadjacentRounds, "nonadjacent-rounds"),
            (R::InvalidRunLocalValues, "invalid-run-local-values"),
            (R::InvalidProposalState, "invalid-proposal-state"),
        ];
        assert_eq!(tokens.len(), 31);
        for (reason, token) in tokens {
            assert_eq!(reason.as_str(), token);
            assert_eq!(reason.to_string(), token);
        }
    }

    // -----------------------------------------------------------------------
    // Version and fingerprint parsers (mirrors test_protocol.py:329-352)
    // -----------------------------------------------------------------------

    #[test]
    fn version_and_fingerprint_parsers() {
        assert_eq!(parse_protocol_version("1"), Ok("1"));
        assert_eq!(parse_fingerprint_version("1"), Ok("1"));
        assert!(is_valid_protocol_version("1"));
        assert!(is_valid_fingerprint_version("1"));
        assert!(!is_valid_protocol_version("2"));
        assert!(!is_valid_fingerprint_version("0"));
        assert_eq!(parse_protocol_version("2"), Err(R::InvalidProtocolVersion));
        assert_eq!(
            parse_fingerprint_version("0"),
            Err(R::InvalidFingerprintVersion)
        );
        assert!(is_valid_fingerprint(&"a".repeat(FINGERPRINT_HEX_LENGTH)));
        assert!(!is_valid_fingerprint(&"A".repeat(FINGERPRINT_HEX_LENGTH)));
        assert!(!is_valid_fingerprint(
            &"a".repeat(FINGERPRINT_HEX_LENGTH - 1)
        ));
        assert_eq!(
            parse_fingerprint("0123456789abcdef").map(|fp| fp.value().to_owned()),
            Ok("0123456789abcdef".to_owned())
        );
        assert_eq!(
            parse_fingerprint("not-hex-fingerprint"),
            Err(R::InvalidFingerprint)
        );
    }

    // -----------------------------------------------------------------------
    // Lexical validation (mirrors test_protocol.py:440-579)
    // -----------------------------------------------------------------------

    #[test]
    #[rustfmt::skip]
    fn slot_validation() {
        let cases = [
            ("cursor", true), ("codex", true), ("claude", true),
            ("Cursor", false), ("gpt", false), ("", false),
        ];
        for (value, ok) in cases {
            assert_eq!(is_valid_slot(value), ok, "slot {value:?}");
            if ok {
                assert_eq!(parse_slot(value).map(Participant::as_str), Ok(value));
            } else {
                assert_eq!(parse_slot(value), Err(R::InvalidSlot));
            }
        }
    }

    #[test]
    #[rustfmt::skip]
    fn point_token_validation() {
        let cases = [
            ("POINT_1", true), ("POINT_9999", true), ("POINT_0", false),
            ("POINT_01", false), ("POINT_10000", false), ("POINT_", false),
            ("POINT_1a", false), ("point_1", false), ("P1", false),
        ];
        for (token, ok) in cases {
            assert_eq!(is_valid_point_token(token), ok, "token {token:?}");
        }
    }

    #[test]
    #[rustfmt::skip]
    fn artifact_path_validation() {
        let cases = [
            ("docs/x.md", true), ("a b/c.md", true), ("file.md", true),
            ("", false), ("/abs.md", false), ("a\\b.md", false),
            ("a/../b.md", false), ("./x.md", false), ("a//b.md", false),
            ("a/", false), ("a/\tb.md", false),
        ];
        for (path, ok) in cases {
            assert_eq!(is_valid_artifact_path(path), ok, "path {path:?}");
        }
    }

    #[test]
    fn forbidden_plan_content() {
        let cases = [
            "### NEW: x.py",
            "### UPDATED: x.py",
            "### REWRITTEN: x.py",
            "### MAY_UPDATE: x.py",
            "diff_lines: 12",
        ];
        for text in cases {
            assert_eq!(
                reject_forbidden_plan_content(text),
                Err(R::ForbiddenPlanContent),
                "text {text:?}"
            );
        }
    }

    #[test]
    fn non_forbidden_trailers_are_allowed() {
        assert_eq!(reject_forbidden_plan_content("difficulty: HARD"), Ok(()));
        assert_eq!(
            reject_forbidden_plan_content("review_status: complete"),
            Ok(())
        );
        assert_eq!(
            reject_forbidden_plan_content("ordinary prose about NEW files"),
            Ok(())
        );
    }

    #[test]
    #[rustfmt::skip]
    fn point_id_bounds() {
        assert_eq!(PointId::new(POINT_ID_MIN).map(PointId::token), Ok("POINT_1".to_owned()));
        assert_eq!(PointId::new(POINT_ID_MAX).map(PointId::token), Ok("POINT_9999".to_owned()));
        assert_eq!(PointId::new(0), Err(R::PointIdOutOfRange));
        assert_eq!(PointId::new(POINT_ID_MAX + 1), Err(R::PointIdOutOfRange));
        assert_eq!(PointId::from_token("POINT_01"), Err(R::MalformedPointId));
        assert_eq!(PointId::from_token("POINT_10000"), Err(R::PointIdOutOfRange));
    }

    // -----------------------------------------------------------------------
    // Ledger parsing (mirrors test_protocol.py:587-706)
    // -----------------------------------------------------------------------

    #[test]
    #[rustfmt::skip]
    fn ledger_accepted_rows() {
        let cases = [
            ("POINT POINT_1 AGREE looks good", vec![(1, A::Agree, "looks good", C::NonConcession)]),
            ("POINT POINT_1 CONCEDE see POINT POINT_2\nPOINT POINT_2 HOLD keep this", vec![
                (1, A::Concede, "see POINT POINT_2", C::Cited),
                (2, A::Hold, "keep this", C::NonConcession),
            ]),
            ("POINT POINT_3 CONCEDE no citation here", vec![(3, A::Concede, "no citation here", C::Fold)]),
            ("POINT POINT_1 AGREE reason  with  spaces", vec![(1, A::Agree, "reason  with  spaces", C::NonConcession)]),
        ];
        for (submission, expected) in cases {
            let parsed = parse_slot_ledger(submission).expect("accepted submission");
            assert_eq!(parsed.rows.len(), expected.len(), "{submission:?}");
            for (row, (number, action, reason, concession)) in parsed.rows.iter().zip(expected.iter()) {
                assert_eq!(row.point_id.number(), *number, "{submission:?}");
                assert_eq!(row.action, *action, "{submission:?}");
                assert_eq!(row.reason, *reason, "{submission:?}");
                assert_eq!(row.concession, *concession, "{submission:?}");
            }
        }
    }

    #[test]
    #[rustfmt::skip]
    fn ledger_rejection_classes() {
        let cases = [
            ("", R::EmptySubmission),
            ("POINT POINT_1 AGREE ok\n", R::BlankRow),
            ("\nPOINT POINT_1 AGREE ok", R::BlankRow),
            ("POINT POINT_1 AGREE ok\n\nPOINT POINT_2 AGREE ok", R::BlankRow),
            ("POINT POINT_1 AGREE ok\r", R::ForbiddenCharacter),
            ("POINT POINT_1 AGREE\tok", R::ForbiddenCharacter),
            ("POINT POINT_1 AGREE ok\x00", R::ForbiddenCharacter),
            (" POINT POINT_1 AGREE ok", R::LeadingOrTrailingWhitespace),
            ("POINT POINT_1 AGREE ok ", R::LeadingOrTrailingWhitespace),
            ("POINT  POINT_1 AGREE ok", R::RepeatedSeparatorSpaces),
            ("POINT POINT_1  AGREE ok", R::RepeatedSeparatorSpaces),
            ("NOT A ROW", R::MalformedRow),
            ("POINT POINT_1 ok", R::MalformedRow),
            ("POINT POINT_1 YES no", R::UnknownAction),
            ("POINT POINT_1 AGREE", R::MalformedRow),
            ("POINT POINT_1 AGREE ", R::EmptyReason),
            ("POINT POINT_X AGREE ok", R::MalformedPointId),
            ("POINT POINT_0 AGREE ok", R::MalformedPointId),
            ("POINT POINT_10000 AGREE ok", R::PointIdOutOfRange),
            ("POINT POINT_1 AGREE a\nPOINT POINT_1 HOLD b", R::DuplicatePointId),
            ("POINT POINT_1 AGREE ### NEW: x.py", R::ForbiddenPlanContent),
            ("POINT POINT_1 HOLD diff_lines: 9", R::ForbiddenPlanContent),
        ];
        assert_eq!(cases.len(), 22);
        for (submission, reason) in cases {
            assert_eq!(parse_slot_ledger(submission), Err(reason), "submission {submission:?}");
        }
    }

    // -----------------------------------------------------------------------
    // Citations and concessions (mirrors test_protocol.py:714-765)
    // -----------------------------------------------------------------------

    #[test]
    #[rustfmt::skip]
    fn concession_matrix() {
        let cases = [
            (A::Agree, "POINT POINT_1", C::NonConcession),
            (A::Hold, "[[artifact:docs/x.md]]", C::NonConcession),
            (A::Concede, "see POINT POINT_1 please", C::Cited),
            (A::Concede, "see POINT POINT_9999", C::Cited),
            (A::Concede, "see [[artifact:docs/x.md]]", C::Cited),
            (A::Concede, "no citation", C::Fold),
            (A::Concede, "POINT POINT_0 bad", C::Fold),
            (A::Concede, "POINTPOINT_1 glued", C::Fold),
            (A::Concede, "xPOINT POINT_1", C::Fold),
            (A::Concede, "POINT POINT_1x", C::Fold),
            (A::Concede, "[[artifact:/abs.md]]", C::Fold),
            (A::Concede, "[[artifact:../x.md]]", C::Fold),
            (A::Concede, "[[artifact:]]", C::Fold),
            (A::Concede, "[artifact:docs/x.md]", C::Fold),
            (A::Concede, "POINT POINT_1 and more", C::Cited),
        ];
        assert_eq!(cases.len(), 15);
        for (action, reason, expected) in cases {
            assert_eq!(classify_concession(action, reason), expected, "action {action:?} reason {reason:?}");
        }
    }

    #[test]
    fn uncited_concession_retains_original_reason() {
        let parsed =
            parse_slot_ledger("POINT POINT_1 CONCEDE original fold reason").expect("valid ledger");
        let row = &parsed.rows[0];
        assert_eq!(row.concession, C::Fold);
        assert_eq!(row.reason, "original fold reason");
    }

    // -----------------------------------------------------------------------
    // Fingerprints (mirrors test_protocol.py:773-828 plus Python-pinned
    // byte-parity golden fixtures computed from live Python at repo HEAD)
    // -----------------------------------------------------------------------

    #[test]
    fn fingerprint_nfkc_and_shape() {
        // U+FB01 LATIN SMALL LIGATURE FI normalizes to "fi" under NFKC.
        let ligature = fingerprint_reason("\u{fb01}", &[]).expect("ligature fingerprint");
        let plain = fingerprint_reason("fi", &[]).expect("plain fingerprint");
        assert_eq!(ligature, plain);
        assert_eq!(ligature.value(), "3ac863e164ce7536");
        assert_eq!(ligature.value().len(), FINGERPRINT_HEX_LENGTH);
        assert!(
            ligature
                .value()
                .bytes()
                .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
        );
    }

    #[test]
    fn fingerprint_matches_python_golden_fixture() {
        let looks_good = fingerprint_reason("looks good", &[]).expect("fingerprint");
        assert_eq!(looks_good.value(), "b6137b06d3d72e41");
    }

    #[test]
    fn fingerprint_replacement_order_independence() {
        let reason = "prefix-ab-suffix";
        let left = fingerprint_reason(reason, &["a", "ab"]).expect("left fingerprint");
        let right = fingerprint_reason(reason, &["ab", "a"]).expect("right fingerprint");
        assert_eq!(left, right);
        assert_eq!(left.value(), "a35d465753308d8b");
        // Needle "a" rewrites inside the "ab" placeholder; this is
        // intentional Python parity for naive sequential replacement.
        assert_eq!(
            normalize_reason_for_fingerprint(reason, &["a", "ab"]),
            Ok("prefix-<run-loc<run-local:1>l:0>-suffix".to_owned())
        );
    }

    #[test]
    fn fingerprint_overlapping_and_duplicate_needles() {
        let reason = "aaaa";
        let with_dupes = fingerprint_reason(reason, &["aa", "aa", "a"]).expect("dupes");
        let without = fingerprint_reason(reason, &["aa", "a"]).expect("no dupes");
        assert_eq!(with_dupes, without);
    }

    #[test]
    fn fingerprint_excludes_ambient_unless_supplied() {
        let base = fingerprint_reason("stable text", &[]).expect("base");
        // Supplying path/run tokens changes the digest only when they appear.
        let altered = fingerprint_reason(
            "stable text with /tmp/run and run-9",
            &["/tmp/run", "run-9"],
        )
        .expect("altered");
        assert_ne!(base, altered);
        assert_eq!(altered.value(), "30b7374ec52e0031");
        assert_eq!(
            normalize_reason_for_fingerprint(
                "stable text with /tmp/run and run-9",
                &["/tmp/run", "run-9"],
            ),
            Ok("stable text with <run-local:0> and <run-local:1>".to_owned())
        );
        // Same reason without those substrings ignores unused needles.
        let unused = fingerprint_reason("stable text", &["/tmp/run", "run-9"]).expect("unused");
        assert_eq!(unused, base);
    }

    #[test]
    fn fingerprint_empty_needle_rejected() {
        assert_eq!(
            normalize_reason_for_fingerprint("x", &[""]),
            Err(R::EmptyReplacementNeedle)
        );
        assert_eq!(
            fingerprint_reason("x", &[""]),
            Err(R::EmptyReplacementNeedle)
        );
    }
}
