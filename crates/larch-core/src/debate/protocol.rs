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
use std::{
    collections::{HashMap, HashSet},
    fmt,
    fmt::Write as _,
    sync::LazyLock,
};
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

// ---------------------------------------------------------------------------
// State module constants
// ---------------------------------------------------------------------------

/// Whether a resolution closes its point (mirrors `_RESOLVED_POINT_RESOLUTIONS`).
const fn is_resolved(resolution: PointResolution) -> bool {
    matches!(
        resolution,
        PointResolution::Agreed | PointResolution::Conceded
    )
}

/// Explicit legal `(phase, action)` edges (mirrors `_TRANSITION_TABLE`).
///
/// Payload rules and [`ROUND_LIMIT`] checks run only after an edge is admitted.
const LEGAL_EDGES: [(NonterminalPhase, TransitionAction); 9] = [
    (NonterminalPhase::BlindRound1, TransitionAction::SubmitRound),
    (NonterminalPhase::BlindRound1, TransitionAction::Abort),
    (NonterminalPhase::Round2, TransitionAction::SubmitRound),
    (NonterminalPhase::Round2, TransitionAction::Abort),
    (
        NonterminalPhase::AwaitingAdjudication,
        TransitionAction::DeclareStalemate,
    ),
    (
        NonterminalPhase::AwaitingAdjudication,
        TransitionAction::Adjudicate,
    ),
    (
        NonterminalPhase::AwaitingAdjudication,
        TransitionAction::Abort,
    ),
    (NonterminalPhase::Unconverged, TransitionAction::Adjudicate),
    (NonterminalPhase::Unconverged, TransitionAction::Abort),
];

/// Whether `(phase, action)` is an admitted transition-table edge.
fn is_legal_edge(phase: NonterminalPhase, action: TransitionAction) -> bool {
    LEGAL_EDGES
        .iter()
        .any(|&(edge_phase, edge_action)| edge_phase == phase && edge_action == action)
}

// ---------------------------------------------------------------------------
// Shared state validators
// ---------------------------------------------------------------------------

/// Index of `slot` in [`SLOT_ORDER`]; total for every [`Participant`].
const fn slot_order_index(slot: Participant) -> usize {
    match slot {
        Participant::Cursor => 0,
        Participant::Codex => 1,
        Participant::Claude => 2,
    }
}

/// Verify a ledger's row fingerprints against `run_local_values`.
fn verify_binding_fingerprints(
    ledger: &ParsedSlotLedger,
    fingerprints: &[ReasonFingerprint],
    run_local_values: &[&str],
) -> Result<(), ParseRejectionReason> {
    if fingerprints.len() != ledger.rows.len() {
        return Err(ParseRejectionReason::FingerprintMismatch);
    }
    for (row, expected) in ledger.rows.iter().zip(fingerprints.iter()) {
        let actual = fingerprint_reason(&row.reason, run_local_values)?;
        if actual != *expected {
            return Err(ParseRejectionReason::FingerprintMismatch);
        }
    }
    Ok(())
}

/// The ordered point ids of a parsed ledger.
fn ledger_point_ids(ledger: &ParsedSlotLedger) -> Vec<PointId> {
    ledger.rows.iter().map(|row| row.point_id).collect()
}

/// Validate a point universe: nonempty and free of duplicate numbers.
fn validate_point_universe(point_universe: &[PointId]) -> Result<(), ParseRejectionReason> {
    if point_universe.is_empty() {
        return Err(ParseRejectionReason::EmptyPointUniverse);
    }
    let mut seen: HashSet<u16> = HashSet::new();
    for point_id in point_universe {
        if !seen.insert(point_id.number()) {
            return Err(ParseRejectionReason::DuplicatePointId);
        }
    }
    Ok(())
}

/// Validate an adjudication position string.
///
/// Newline and carriage-return rejection precedes the control-character check,
/// so `"has\nnewline"` yields `MalformedAdjudication`, not `ForbiddenCharacter`.
fn validate_adjudication_position(text: &str) -> Result<(), ParseRejectionReason> {
    if text.is_empty() || text != text.trim() {
        return Err(ParseRejectionReason::MalformedAdjudication);
    }
    if text.contains('\n') || text.contains('\r') {
        return Err(ParseRejectionReason::MalformedAdjudication);
    }
    if text.chars().any(is_forbidden_char) {
        return Err(ParseRejectionReason::ForbiddenCharacter);
    }
    reject_forbidden_plan_content(text)
}

/// Require slots strictly ascending in [`SLOT_ORDER`] with no repeats.
fn require_ascending_slots(slots: &[Participant]) -> Result<(), ParseRejectionReason> {
    let mut previous: Option<usize> = None;
    let mut seen: HashSet<Participant> = HashSet::new();
    for slot in slots {
        if !seen.insert(*slot) {
            return Err(ParseRejectionReason::InvalidSlotOrdering);
        }
        let index = slot_order_index(*slot);
        if previous.is_some_and(|prev| index <= prev) {
            return Err(ParseRejectionReason::InvalidSlotOrdering);
        }
        previous = Some(index);
    }
    Ok(())
}

/// Validate a round's live-slot bindings: floor, ceiling, ordering, universe.
fn validate_round_bindings(bindings: &[SlotLedgerBinding]) -> Result<(), ParseRejectionReason> {
    if bindings.len() < LIVE_PANEL_MINIMUM {
        return Err(ParseRejectionReason::BelowLivePanelFloor);
    }
    if bindings.len() > LIVE_PANEL_MAXIMUM {
        return Err(ParseRejectionReason::AboveLivePanelCeiling);
    }
    let slots: Vec<Participant> = bindings.iter().map(SlotLedgerBinding::slot).collect();
    require_ascending_slots(&slots)?;
    let reference = ledger_point_ids(bindings[0].ledger());
    for binding in &bindings[1..] {
        if ledger_point_ids(binding.ledger()) != reference {
            return Err(ParseRejectionReason::PointUniverseMismatch);
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Round-state value objects
// ---------------------------------------------------------------------------

/// One live slot bound to exactly one parsed ledger and row fingerprints.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SlotLedgerBinding {
    slot: Participant,
    ledger: ParsedSlotLedger,
    fingerprints: Vec<ReasonFingerprint>,
}

impl SlotLedgerBinding {
    /// Bind `slot` to `ledger`, verifying `fingerprints` under `run_local_values`.
    ///
    /// `run_local_values` supplies the fingerprint replacement needles (the
    /// values of Python's run-local mapping); it is not stored, and its keys
    /// are behaviorally inert.
    ///
    /// # Errors
    ///
    /// Returns [`ParseRejectionReason::FingerprintMismatch`] when the
    /// fingerprint count or any recomputed fingerprint disagrees with the
    /// ledger, and [`ParseRejectionReason::EmptyReplacementNeedle`] for an
    /// empty needle.
    pub fn new(
        slot: Participant,
        ledger: ParsedSlotLedger,
        fingerprints: Vec<ReasonFingerprint>,
        run_local_values: &[&str],
    ) -> Result<Self, ParseRejectionReason> {
        verify_binding_fingerprints(&ledger, &fingerprints, run_local_values)?;
        Ok(Self {
            slot,
            ledger,
            fingerprints,
        })
    }

    /// The bound live slot.
    #[must_use]
    pub const fn slot(&self) -> Participant {
        self.slot
    }

    /// The bound parsed ledger.
    #[must_use]
    pub const fn ledger(&self) -> &ParsedSlotLedger {
        &self.ledger
    }

    /// The per-row reason fingerprints.
    #[must_use]
    pub fn fingerprints(&self) -> &[ReasonFingerprint] {
        &self.fingerprints
    }
}

/// Immutable assembly of one negotiation round's live slot bindings.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RoundState {
    round_number: RoundNumber,
    bindings: Vec<SlotLedgerBinding>,
}

impl RoundState {
    /// Assemble a validated round from `round_number` and `bindings`.
    ///
    /// # Errors
    ///
    /// Returns [`ParseRejectionReason::InvalidRoundNumber`] outside
    /// `1..=ROUND_LIMIT`, [`ParseRejectionReason::BelowLivePanelFloor`] or
    /// [`ParseRejectionReason::AboveLivePanelCeiling`] for the binding count,
    /// [`ParseRejectionReason::InvalidSlotOrdering`] for repeated or unordered
    /// slots, and [`ParseRejectionReason::PointUniverseMismatch`] when the
    /// bindings disagree on point ids.
    pub fn new(
        round_number: RoundNumber,
        bindings: Vec<SlotLedgerBinding>,
    ) -> Result<Self, ParseRejectionReason> {
        let number = round_number as u8;
        if !(1..=ROUND_LIMIT).contains(&number) {
            return Err(ParseRejectionReason::InvalidRoundNumber);
        }
        validate_round_bindings(&bindings)?;
        Ok(Self {
            round_number,
            bindings,
        })
    }

    /// The validated round number.
    #[must_use]
    pub const fn round_number(&self) -> RoundNumber {
        self.round_number
    }

    /// The round's live-slot bindings.
    #[must_use]
    pub fn bindings(&self) -> &[SlotLedgerBinding] {
        &self.bindings
    }

    /// The ordered live slots in binding order.
    #[must_use]
    pub fn live_slots(&self) -> Vec<Participant> {
        self.bindings.iter().map(SlotLedgerBinding::slot).collect()
    }

    /// The ordered point ids shared by every binding.
    #[must_use]
    pub fn point_ids(&self) -> Vec<PointId> {
        ledger_point_ids(self.bindings[0].ledger())
    }
}

/// Stalemate dispute for one point with at least two unchanged HOLD slots.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Dispute {
    point_id: PointId,
    holding_slots: Vec<Participant>,
}

impl Dispute {
    /// Assemble a dispute over `point_id` held by `holding_slots`.
    ///
    /// # Errors
    ///
    /// Returns [`ParseRejectionReason::BelowLivePanelFloor`] for fewer than
    /// [`LIVE_PANEL_MINIMUM`] slots and
    /// [`ParseRejectionReason::InvalidSlotOrdering`] for repeated or unordered
    /// slots.
    pub fn new(
        point_id: PointId,
        holding_slots: Vec<Participant>,
    ) -> Result<Self, ParseRejectionReason> {
        if holding_slots.len() < LIVE_PANEL_MINIMUM {
            return Err(ParseRejectionReason::BelowLivePanelFloor);
        }
        require_ascending_slots(&holding_slots)?;
        Ok(Self {
            point_id,
            holding_slots,
        })
    }

    /// The disputed point id.
    #[must_use]
    pub const fn point_id(&self) -> PointId {
        self.point_id
    }

    /// The slots holding the disputed point.
    #[must_use]
    pub fn holding_slots(&self) -> &[Participant] {
        &self.holding_slots
    }
}

/// Selected-position adjudication for one unresolved point.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SelectedAdjudication {
    point_id: PointId,
    selected_position: String,
}

impl SelectedAdjudication {
    /// Validate a selected-position adjudication.
    ///
    /// # Errors
    ///
    /// Returns [`ParseRejectionReason::MalformedAdjudication`],
    /// [`ParseRejectionReason::ForbiddenCharacter`], or
    /// [`ParseRejectionReason::ForbiddenPlanContent`] for a malformed position.
    pub fn new(point_id: PointId, selected_position: String) -> Result<Self, ParseRejectionReason> {
        validate_adjudication_position(&selected_position)?;
        Ok(Self {
            point_id,
            selected_position,
        })
    }

    /// The adjudicated point id.
    #[must_use]
    pub const fn point_id(&self) -> PointId {
        self.point_id
    }

    /// The selected position text.
    #[must_use]
    pub fn selected_position(&self) -> &str {
        &self.selected_position
    }

    /// The adjudication decision kind.
    #[must_use]
    pub const fn decision(&self) -> AdjudicationDecision {
        AdjudicationDecision::Selected
    }
}

/// Split-position adjudication for one unresolved point.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SplitAdjudication {
    point_id: PointId,
    position_a: String,
    position_b: String,
}

impl SplitAdjudication {
    /// Validate a split-position adjudication.
    ///
    /// # Errors
    ///
    /// Returns [`ParseRejectionReason::MalformedAdjudication`],
    /// [`ParseRejectionReason::ForbiddenCharacter`], or
    /// [`ParseRejectionReason::ForbiddenPlanContent`] for a malformed position,
    /// including two equal positions.
    pub fn new(
        point_id: PointId,
        position_a: String,
        position_b: String,
    ) -> Result<Self, ParseRejectionReason> {
        validate_adjudication_position(&position_a)?;
        validate_adjudication_position(&position_b)?;
        if position_a == position_b {
            return Err(ParseRejectionReason::MalformedAdjudication);
        }
        Ok(Self {
            point_id,
            position_a,
            position_b,
        })
    }

    /// The adjudicated point id.
    #[must_use]
    pub const fn point_id(&self) -> PointId {
        self.point_id
    }

    /// The first split position text.
    #[must_use]
    pub fn position_a(&self) -> &str {
        &self.position_a
    }

    /// The second split position text.
    #[must_use]
    pub fn position_b(&self) -> &str {
        &self.position_b
    }

    /// The adjudication decision kind.
    #[must_use]
    pub const fn decision(&self) -> AdjudicationDecision {
        AdjudicationDecision::Split
    }
}

/// One adjudication record: a selected position or a split.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AdjudicationRecord {
    /// A selected-position adjudication.
    Selected(SelectedAdjudication),
    /// A split-position adjudication.
    Split(SplitAdjudication),
}

impl AdjudicationRecord {
    /// The adjudicated point id.
    #[must_use]
    pub const fn point_id(&self) -> PointId {
        match self {
            Self::Selected(record) => record.point_id(),
            Self::Split(record) => record.point_id(),
        }
    }

    /// The adjudication decision kind.
    #[must_use]
    pub const fn decision(&self) -> AdjudicationDecision {
        match self {
            Self::Selected(record) => record.decision(),
            Self::Split(record) => record.decision(),
        }
    }
}

// ---------------------------------------------------------------------------
// Point resolution
// ---------------------------------------------------------------------------

/// Whether a slot's row closes a point under the normative predicate.
#[must_use]
pub fn slot_closes_point(row: &LedgerRow) -> bool {
    if row.action == Action::Agree {
        return true;
    }
    row.action == Action::Concede && row.concession == ConcessionClassification::Cited
}

/// Resolve one point from every live slot's row for that point.
///
/// A point resolves only when every live slot closes it. Closing actions are
/// `AGREE` and cited `CONCEDE`. Folded concessions and `HOLD` never close.
///
/// # Errors
///
/// Returns [`ParseRejectionReason::BelowLivePanelFloor`] for empty rows.
pub fn resolve_point(rows: &[LedgerRow]) -> Result<PointResolution, ParseRejectionReason> {
    if rows.is_empty() {
        return Err(ParseRejectionReason::BelowLivePanelFloor);
    }
    if rows.iter().all(slot_closes_point) {
        if rows.iter().all(|row| row.action == Action::Agree) {
            return Ok(PointResolution::Agreed);
        }
        return Ok(PointResolution::Conceded);
    }
    if rows.iter().any(|row| row.action == Action::Hold) {
        return Ok(PointResolution::Held);
    }
    Ok(PointResolution::Folded)
}

/// The single ledger row for `point_id` in `binding`.
fn row_for_point(
    binding: &SlotLedgerBinding,
    point_id: PointId,
) -> Result<&LedgerRow, ParseRejectionReason> {
    let mut matches = binding
        .ledger()
        .rows
        .iter()
        .filter(|row| row.point_id == point_id);
    match (matches.next(), matches.next()) {
        (Some(row), None) => Ok(row),
        _ => Err(ParseRejectionReason::PointUniverseMismatch),
    }
}

/// Apply the normative predicate to every point in `round_state`.
///
/// # Errors
///
/// Returns [`ParseRejectionReason::PointUniverseMismatch`] when a slot lacks a
/// unique row for a point, or [`ParseRejectionReason::BelowLivePanelFloor`]
/// from [`resolve_point`].
pub fn resolve_round_points(
    round_state: &RoundState,
) -> Result<HashMap<PointId, PointResolution>, ParseRejectionReason> {
    let mut resolutions: HashMap<PointId, PointResolution> = HashMap::new();
    for point_id in round_state.point_ids() {
        let mut rows: Vec<LedgerRow> = Vec::with_capacity(round_state.bindings().len());
        for binding in round_state.bindings() {
            rows.push(row_for_point(binding, point_id)?.clone());
        }
        let _ignored = resolutions.insert(point_id, resolve_point(&rows)?);
    }
    Ok(resolutions)
}

/// The ordered unresolved point ids under the normative predicate.
///
/// # Errors
///
/// Propagates every error from [`resolve_round_points`].
pub fn unresolved_points(round_state: &RoundState) -> Result<Vec<PointId>, ParseRejectionReason> {
    let resolutions = resolve_round_points(round_state)?;
    Ok(round_state
        .point_ids()
        .into_iter()
        .filter(|point_id| !is_resolved(resolutions[point_id]))
        .collect())
}

/// Whether every point in the round is AGREED or CONCEDED.
///
/// # Errors
///
/// Propagates every error from [`unresolved_points`].
pub fn round_is_fully_resolved(round_state: &RoundState) -> Result<bool, ParseRejectionReason> {
    Ok(unresolved_points(round_state)?.is_empty())
}

fn revalidate_round_against_proposal(
    proposal: &ProposalState,
    round_state: &RoundState,
) -> Result<(), ParseRejectionReason> {
    if round_state.point_ids().as_slice() != proposal.point_universe() {
        return Err(ParseRejectionReason::PointUniverseMismatch);
    }
    let needles = proposal.run_local_needles();
    for binding in round_state.bindings() {
        verify_binding_fingerprints(binding.ledger(), binding.fingerprints(), &needles)?;
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Stalemate detection
// ---------------------------------------------------------------------------

/// Stalemate-detection result separating empty success from a skipped run.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StalemateDetection {
    status: StalemateDetectionStatus,
    disputes: Vec<Dispute>,
}

impl StalemateDetection {
    /// Assemble a stalemate-detection result.
    ///
    /// # Errors
    ///
    /// Returns [`ParseRejectionReason::InvalidProposalState`] when a
    /// membership-changed result carries any dispute.
    pub fn new(
        status: StalemateDetectionStatus,
        disputes: Vec<Dispute>,
    ) -> Result<Self, ParseRejectionReason> {
        if status == StalemateDetectionStatus::MembershipChanged && !disputes.is_empty() {
            return Err(ParseRejectionReason::InvalidProposalState);
        }
        Ok(Self { status, disputes })
    }

    /// The detection status.
    #[must_use]
    pub const fn status(&self) -> StalemateDetectionStatus {
        self.status
    }

    /// The detected disputes.
    #[must_use]
    pub fn disputes(&self) -> &[Dispute] {
        &self.disputes
    }
}

/// Whether one slot holds `point_id` unchanged across both rounds.
fn slot_holds_unchanged(
    earlier_binding: &SlotLedgerBinding,
    later_binding: &SlotLedgerBinding,
    point_index: usize,
    point_id: PointId,
    needles: &[&str],
) -> Result<bool, ParseRejectionReason> {
    let earlier_row = &earlier_binding.ledger().rows[point_index];
    let later_row = &later_binding.ledger().rows[point_index];
    if earlier_row.point_id != point_id || later_row.point_id != point_id {
        return Err(ParseRejectionReason::PointUniverseMismatch);
    }
    if earlier_row.action != Action::Hold || later_row.action != Action::Hold {
        return Ok(false);
    }
    let earlier_fp = fingerprint_reason(&earlier_row.reason, needles)?;
    let later_fp = fingerprint_reason(&later_row.reason, needles)?;
    if earlier_fp != earlier_binding.fingerprints()[point_index]
        || later_fp != later_binding.fingerprints()[point_index]
    {
        return Err(ParseRejectionReason::FingerprintMismatch);
    }
    Ok(earlier_fp == later_fp)
}

/// Detect qualifying HOLD stalemates across adjacent rounds.
///
/// Requires adjacent round numbers. Forged or mismatched fingerprints reject.
/// A dispute requires at least two matching slots that `HOLD` in both rounds
/// with unchanged recomputed fingerprints under the proposal's run-local
/// snapshot. Changed live-slot membership skips detection and reports
/// [`StalemateDetectionStatus::MembershipChanged`], which is distinct from a
/// completed run that found no qualifying dispute.
///
/// # Errors
///
/// Returns [`ParseRejectionReason::NonadjacentRounds`],
/// [`ParseRejectionReason::PointUniverseMismatch`],
/// [`ParseRejectionReason::FingerprintMismatch`], or the errors from
/// [`Dispute::new`].
pub fn detect_stalemate_disputes(
    proposal: &ProposalState,
    earlier: &RoundState,
    later: &RoundState,
) -> Result<StalemateDetection, ParseRejectionReason> {
    if (later.round_number() as u8) != (earlier.round_number() as u8) + 1 {
        return Err(ParseRejectionReason::NonadjacentRounds);
    }
    revalidate_round_against_proposal(proposal, earlier)?;
    revalidate_round_against_proposal(proposal, later)?;

    if earlier.live_slots() != later.live_slots() {
        return StalemateDetection::new(StalemateDetectionStatus::MembershipChanged, Vec::new());
    }

    let earlier_by_slot: HashMap<Participant, &SlotLedgerBinding> = earlier
        .bindings()
        .iter()
        .map(|binding| (binding.slot(), binding))
        .collect();
    let later_by_slot: HashMap<Participant, &SlotLedgerBinding> = later
        .bindings()
        .iter()
        .map(|binding| (binding.slot(), binding))
        .collect();
    let needles = proposal.run_local_needles();
    let mut disputes: Vec<Dispute> = Vec::new();
    for (point_index, point_id) in proposal.point_universe().iter().enumerate() {
        let mut holding_slots: Vec<Participant> = Vec::new();
        for slot in earlier.live_slots() {
            let earlier_binding = earlier_by_slot[&slot];
            let later_binding = later_by_slot[&slot];
            if slot_holds_unchanged(
                earlier_binding,
                later_binding,
                point_index,
                *point_id,
                &needles,
            )? {
                holding_slots.push(slot);
            }
        }
        if holding_slots.len() >= LIVE_PANEL_MINIMUM {
            disputes.push(Dispute::new(*point_id, holding_slots)?);
        }
    }
    StalemateDetection::new(StalemateDetectionStatus::Completed, disputes)
}

// ---------------------------------------------------------------------------
// Adjudication coverage
// ---------------------------------------------------------------------------

/// Validate adjudication coverage, returning the covered set and split flag.
fn adjudication_coverage(
    unresolved: &[PointId],
    records: &[AdjudicationRecord],
) -> Result<bool, ParseRejectionReason> {
    if unresolved.is_empty() {
        return Err(ParseRejectionReason::MalformedAdjudication);
    }
    let unresolved_set: HashSet<PointId> = unresolved.iter().copied().collect();
    if unresolved_set.len() != unresolved.len() {
        return Err(ParseRejectionReason::DuplicatePointId);
    }
    if records.len() != unresolved.len() {
        return Err(ParseRejectionReason::IncompleteAdjudicationCoverage);
    }

    let mut seen: HashSet<PointId> = HashSet::new();
    let mut has_split = false;
    for record in records {
        let point_id = record.point_id();
        if seen.contains(&point_id) || !unresolved_set.contains(&point_id) {
            return Err(ParseRejectionReason::MalformedAdjudication);
        }
        let _ignored = seen.insert(point_id);
        has_split = has_split || matches!(record, AdjudicationRecord::Split(_));
    }
    if seen != unresolved_set {
        return Err(ParseRejectionReason::IncompleteAdjudicationCoverage);
    }
    Ok(has_split)
}

/// Validate a complete adjudication set against unresolved points.
///
/// Returns [`TerminalOutcome::Converged`] when every record is selected, or
/// [`TerminalOutcome::BothViable`] when any record is a split.
///
/// # Errors
///
/// Returns [`ParseRejectionReason::MalformedAdjudication`],
/// [`ParseRejectionReason::DuplicatePointId`], or
/// [`ParseRejectionReason::IncompleteAdjudicationCoverage`] for a coverage gap.
pub fn validate_adjudication_set(
    unresolved: &[PointId],
    records: &[AdjudicationRecord],
) -> Result<TerminalOutcome, ParseRejectionReason> {
    if adjudication_coverage(unresolved, records)? {
        Ok(TerminalOutcome::BothViable)
    } else {
        Ok(TerminalOutcome::Converged)
    }
}

// ---------------------------------------------------------------------------
// Proposal state and shape validation
// ---------------------------------------------------------------------------

const fn validate_proposal_phase_fields(
    phase: Option<NonterminalPhase>,
    terminal_outcome: Option<TerminalOutcome>,
) -> Result<(), ParseRejectionReason> {
    if phase.is_some() == terminal_outcome.is_some() {
        return Err(ParseRejectionReason::InvalidProposalState);
    }
    Ok(())
}

fn validate_proposal_rounds(
    point_universe: &[PointId],
    rounds: &[RoundState],
    run_local_values: &[&str],
) -> Result<(), ParseRejectionReason> {
    if rounds.len() > ROUND_LIMIT as usize {
        return Err(ParseRejectionReason::IllegalTransition);
    }
    for (index, round_state) in rounds.iter().enumerate() {
        if round_state.round_number() as usize != index + 1 {
            return Err(ParseRejectionReason::InvalidRoundNumber);
        }
        if round_state.point_ids().as_slice() != point_universe {
            return Err(ParseRejectionReason::PointUniverseMismatch);
        }
        for binding in round_state.bindings() {
            verify_binding_fingerprints(
                binding.ledger(),
                binding.fingerprints(),
                run_local_values,
            )?;
        }
    }
    Ok(())
}

fn validate_proposal_shape(
    phase: Option<NonterminalPhase>,
    terminal_outcome: Option<TerminalOutcome>,
    rounds: &[RoundState],
    disputes: &[Dispute],
    adjudications: &[AdjudicationRecord],
) -> Result<(), ParseRejectionReason> {
    let invalid = ParseRejectionReason::InvalidProposalState;
    if phase == Some(NonterminalPhase::BlindRound1) && !rounds.is_empty() {
        return Err(invalid);
    }
    if phase == Some(NonterminalPhase::Round2) && rounds.len() != 1 {
        return Err(invalid);
    }
    if matches!(
        phase,
        Some(NonterminalPhase::AwaitingAdjudication | NonterminalPhase::Unconverged)
    ) && rounds.len() != ROUND_LIMIT as usize
    {
        return Err(invalid);
    }
    if terminal_outcome == Some(TerminalOutcome::Stalemate)
        && (!adjudications.is_empty() || disputes.is_empty())
    {
        return Err(invalid);
    }
    if terminal_outcome == Some(TerminalOutcome::BothViable) && adjudications.is_empty() {
        return Err(invalid);
    }
    if terminal_outcome == Some(TerminalOutcome::Aborted)
        && (!disputes.is_empty() || !adjudications.is_empty())
    {
        return Err(invalid);
    }
    if phase == Some(NonterminalPhase::AwaitingAdjudication) && disputes.is_empty() {
        return Err(invalid);
    }
    if phase.is_some() && !adjudications.is_empty() {
        return Err(invalid);
    }
    Ok(())
}

/// Immutable proposal protocol state, including the fixed point universe.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProposalState {
    point_universe: Vec<PointId>,
    protocol_version: String,
    fingerprint_algorithm_version: String,
    run_local_values: Vec<String>,
    phase: Option<NonterminalPhase>,
    terminal_outcome: Option<TerminalOutcome>,
    rounds: Vec<RoundState>,
    disputes: Vec<Dispute>,
    adjudications: Vec<AdjudicationRecord>,
}

impl ProposalState {
    /// Run every shape and content invariant on the assembled fields.
    fn validate(&self) -> Result<(), ParseRejectionReason> {
        validate_point_universe(&self.point_universe)?;
        let _ = parse_protocol_version(&self.protocol_version)?;
        let _ = parse_fingerprint_version(&self.fingerprint_algorithm_version)?;
        validate_proposal_phase_fields(self.phase, self.terminal_outcome)?;
        let needles = self.run_local_needles();
        validate_proposal_rounds(&self.point_universe, &self.rounds, &needles)?;
        validate_proposal_shape(
            self.phase,
            self.terminal_outcome,
            &self.rounds,
            &self.disputes,
            &self.adjudications,
        )
    }

    /// Run-local replacement needles as borrowed `&str` values.
    fn run_local_needles(&self) -> Vec<&str> {
        self.run_local_values.iter().map(String::as_str).collect()
    }

    /// Struct-update this proposal's mutable state fields and re-validate.
    fn replace(
        &self,
        phase: Option<NonterminalPhase>,
        terminal_outcome: Option<TerminalOutcome>,
        rounds: Vec<RoundState>,
        disputes: Vec<Dispute>,
        adjudications: Vec<AdjudicationRecord>,
    ) -> Result<Self, ParseRejectionReason> {
        let next = Self {
            point_universe: self.point_universe.clone(),
            protocol_version: self.protocol_version.clone(),
            fingerprint_algorithm_version: self.fingerprint_algorithm_version.clone(),
            run_local_values: self.run_local_values.clone(),
            phase,
            terminal_outcome,
            rounds,
            disputes,
            adjudications,
        };
        next.validate()?;
        Ok(next)
    }

    /// The fixed point universe.
    #[must_use]
    pub fn point_universe(&self) -> &[PointId] {
        &self.point_universe
    }

    /// The current nonterminal phase, if any.
    #[must_use]
    pub const fn phase(&self) -> Option<NonterminalPhase> {
        self.phase
    }

    /// The terminal outcome, if any.
    #[must_use]
    pub const fn terminal_outcome(&self) -> Option<TerminalOutcome> {
        self.terminal_outcome
    }

    /// The submitted rounds in order.
    #[must_use]
    pub fn rounds(&self) -> &[RoundState] {
        &self.rounds
    }

    /// The carried stalemate disputes.
    #[must_use]
    pub fn disputes(&self) -> &[Dispute] {
        &self.disputes
    }

    /// The recorded adjudications.
    #[must_use]
    pub fn adjudications(&self) -> &[AdjudicationRecord] {
        &self.adjudications
    }

    /// The run-local replacement values.
    #[must_use]
    pub fn run_local_values(&self) -> &[String] {
        &self.run_local_values
    }
}

/// Construct a proposal in blind round 1 with no prior rounds.
///
/// `run_local_values` supplies the fingerprint replacement values (Python's
/// run-local mapping values); the mapping keys are behaviorally inert.
///
/// # Errors
///
/// Returns [`ParseRejectionReason::EmptyPointUniverse`] or
/// [`ParseRejectionReason::DuplicatePointId`] for a defective universe.
pub fn new_proposal(
    point_universe: &[PointId],
    run_local_values: &[&str],
) -> Result<ProposalState, ParseRejectionReason> {
    let proposal = ProposalState {
        point_universe: point_universe.to_vec(),
        protocol_version: PROTOCOL_VERSION.to_owned(),
        fingerprint_algorithm_version: FINGERPRINT_ALGORITHM_VERSION.to_owned(),
        run_local_values: run_local_values
            .iter()
            .map(|value| (*value).to_owned())
            .collect(),
        phase: Some(NonterminalPhase::BlindRound1),
        terminal_outcome: None,
        rounds: Vec::new(),
        disputes: Vec::new(),
        adjudications: Vec::new(),
    };
    proposal.validate()?;
    Ok(proposal)
}

// ---------------------------------------------------------------------------
// Transition machine
// ---------------------------------------------------------------------------

const fn require_nonterminal(
    proposal: &ProposalState,
) -> Result<NonterminalPhase, ParseRejectionReason> {
    let Some(phase) = proposal.phase() else {
        return Err(ParseRejectionReason::IllegalTransition);
    };
    if proposal.terminal_outcome().is_some() {
        return Err(ParseRejectionReason::IllegalTransition);
    }
    Ok(phase)
}

fn admit_transition(
    phase: NonterminalPhase,
    action: TransitionAction,
) -> Result<(), ParseRejectionReason> {
    if is_legal_edge(phase, action) {
        Ok(())
    } else {
        Err(ParseRejectionReason::IllegalTransition)
    }
}

fn expected_submit_round_number(
    proposal: &ProposalState,
) -> Result<RoundNumber, ParseRejectionReason> {
    let next_index = proposal.rounds().len() + 1;
    if next_index > ROUND_LIMIT as usize {
        return Err(ParseRejectionReason::IllegalTransition);
    }
    match next_index {
        1 => Ok(RoundNumber::Round1),
        2 => Ok(RoundNumber::Round2),
        _ => Err(ParseRejectionReason::InvalidRoundNumber),
    }
}

fn classify_round_two(
    proposal: &ProposalState,
    round_state: &RoundState,
) -> Result<(NonterminalPhase, Vec<Dispute>), ParseRejectionReason> {
    let earlier = &proposal.rounds()[0];
    let detection = detect_stalemate_disputes(proposal, earlier, round_state)?;
    let unresolved = unresolved_points(round_state)?;
    if detection.status() == StalemateDetectionStatus::MembershipChanged {
        return Ok((NonterminalPhase::Unconverged, Vec::new()));
    }
    let dispute_ids: HashSet<PointId> =
        detection.disputes().iter().map(Dispute::point_id).collect();
    let unresolved_set: HashSet<PointId> = unresolved.iter().copied().collect();
    if !unresolved.is_empty() && dispute_ids == unresolved_set {
        return Ok((
            NonterminalPhase::AwaitingAdjudication,
            detection.disputes().to_vec(),
        ));
    }
    Ok((NonterminalPhase::Unconverged, Vec::new()))
}

fn submit_round(
    proposal: &ProposalState,
    round_state: &RoundState,
) -> Result<ProposalState, ParseRejectionReason> {
    let expected = expected_submit_round_number(proposal)?;
    if round_state.round_number() != expected {
        return Err(ParseRejectionReason::InvalidRoundNumber);
    }
    revalidate_round_against_proposal(proposal, round_state)?;

    let mut new_rounds = proposal.rounds().to_vec();
    new_rounds.push(round_state.clone());
    if round_is_fully_resolved(round_state)? {
        return proposal.replace(
            None,
            Some(TerminalOutcome::Converged),
            new_rounds,
            Vec::new(),
            Vec::new(),
        );
    }
    if expected == RoundNumber::Round1 {
        return proposal.replace(
            Some(NonterminalPhase::Round2),
            None,
            new_rounds,
            Vec::new(),
            Vec::new(),
        );
    }
    let (next_phase, disputes) = classify_round_two(proposal, round_state)?;
    proposal.replace(Some(next_phase), None, new_rounds, disputes, Vec::new())
}

fn declare_stalemate(proposal: &ProposalState) -> Result<ProposalState, ParseRejectionReason> {
    if proposal.disputes().is_empty() {
        return Err(ParseRejectionReason::IllegalTransition);
    }
    proposal.replace(
        None,
        Some(TerminalOutcome::Stalemate),
        proposal.rounds().to_vec(),
        proposal.disputes().to_vec(),
        Vec::new(),
    )
}

fn adjudicate(
    proposal: &ProposalState,
    records: &[AdjudicationRecord],
) -> Result<ProposalState, ParseRejectionReason> {
    if proposal.rounds().len() != ROUND_LIMIT as usize {
        return Err(ParseRejectionReason::IllegalTransition);
    }
    let latest = &proposal.rounds()[proposal.rounds().len() - 1];
    let unresolved = unresolved_points(latest)?;
    let outcome = validate_adjudication_set(&unresolved, records)?;
    proposal.replace(
        None,
        Some(outcome),
        proposal.rounds().to_vec(),
        proposal.disputes().to_vec(),
        records.to_vec(),
    )
}

fn abort(proposal: &ProposalState) -> Result<ProposalState, ParseRejectionReason> {
    proposal.replace(
        None,
        Some(TerminalOutcome::Aborted),
        proposal.rounds().to_vec(),
        Vec::new(),
        Vec::new(),
    )
}

/// Apply one explicit transition-table edge with payload-gated validation.
///
/// The edge table is checked before payload-specific validation so illegal
/// edges cannot bypass the two-round cap or terminal immutability.
///
/// # Errors
///
/// Returns [`ParseRejectionReason::IllegalTransition`] for a terminal source,
/// an inadmissible edge, or a mismatched payload, plus the round, resolution,
/// stalemate, and adjudication errors from the admitted action.
pub fn transition(
    proposal: &ProposalState,
    action: TransitionAction,
    round_state: Option<&RoundState>,
    adjudications: Option<&[AdjudicationRecord]>,
) -> Result<ProposalState, ParseRejectionReason> {
    let phase = require_nonterminal(proposal)?;
    admit_transition(phase, action)?;

    match action {
        TransitionAction::SubmitRound => {
            let Some(round_state) = round_state else {
                return Err(ParseRejectionReason::IllegalTransition);
            };
            if adjudications.is_some() {
                return Err(ParseRejectionReason::IllegalTransition);
            }
            submit_round(proposal, round_state)
        }
        TransitionAction::DeclareStalemate => {
            if round_state.is_some() || adjudications.is_some() {
                return Err(ParseRejectionReason::IllegalTransition);
            }
            declare_stalemate(proposal)
        }
        TransitionAction::Adjudicate => {
            let Some(adjudications) = adjudications else {
                return Err(ParseRejectionReason::IllegalTransition);
            };
            if round_state.is_some() {
                return Err(ParseRejectionReason::IllegalTransition);
            }
            adjudicate(proposal, adjudications)
        }
        TransitionAction::Abort => {
            if round_state.is_some() || adjudications.is_some() {
                return Err(ParseRejectionReason::IllegalTransition);
            }
            abort(proposal)
        }
    }
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

#[cfg(test)]
mod state_tests {
    use super::{
        Action as A, AdjudicationDecision, AdjudicationRecord, ConcessionClassification as C,
        Dispute, FINGERPRINT_HEX_LENGTH, LEDGER_POINT_TOKEN, LEGAL_EDGES, LedgerRow,
        NonterminalPhase, POINT_ID_PREFIX, ParseRejectionReason as R, Participant, PointId,
        PointResolution, ReasonFingerprint, RoundNumber, RoundState, SelectedAdjudication,
        SlotLedgerBinding, SplitAdjudication, StalemateDetection, StalemateDetectionStatus,
        TerminalOutcome, TransitionAction, detect_stalemate_disputes, fingerprint_reason,
        is_legal_edge, new_proposal, parse_slot_ledger, resolve_point, resolve_round_points,
        round_is_fully_resolved, slot_closes_point, transition, unresolved_points,
        validate_adjudication_set,
    };

    // -----------------------------------------------------------------------
    // Fixture helpers (mirror test_protocol.py:120-249)
    // -----------------------------------------------------------------------

    fn pid(number: u16) -> PointId {
        PointId::new(number).expect("valid point id")
    }

    fn ledger_from_specs(specs: &[(u16, A, &str)]) -> super::ParsedSlotLedger {
        let lines: Vec<String> = specs
            .iter()
            .map(|(number, action, reason)| {
                format!(
                    "{LEDGER_POINT_TOKEN} {POINT_ID_PREFIX}{number} {} {reason}",
                    action.as_str()
                )
            })
            .collect();
        parse_slot_ledger(&lines.join("\n")).expect("valid ledger from specs")
    }

    fn agree_ledger(points: &[u16]) -> super::ParsedSlotLedger {
        let specs: Vec<(u16, A, String)> = points
            .iter()
            .map(|number| (*number, A::Agree, format!("agree {number}")))
            .collect();
        let borrowed: Vec<(u16, A, &str)> = specs
            .iter()
            .map(|(number, action, reason)| (*number, *action, reason.as_str()))
            .collect();
        ledger_from_specs(&borrowed)
    }

    fn hold_ledger(reason: &str, points: &[u16]) -> super::ParsedSlotLedger {
        let specs: Vec<(u16, A, &str)> = points
            .iter()
            .map(|number| (*number, A::Hold, reason))
            .collect();
        ledger_from_specs(&specs)
    }

    fn mixed_hold_agree(hold_reason: &str) -> super::ParsedSlotLedger {
        ledger_from_specs(&[(1, A::Hold, hold_reason), (2, A::Agree, "agreed second")])
    }

    fn binding(
        slot: Participant,
        ledger: super::ParsedSlotLedger,
        needles: &[&str],
    ) -> SlotLedgerBinding {
        let fingerprints: Vec<ReasonFingerprint> = ledger
            .rows
            .iter()
            .map(|row| fingerprint_reason(&row.reason, needles).expect("row fingerprint"))
            .collect();
        SlotLedgerBinding::new(slot, ledger, fingerprints, needles).expect("valid binding")
    }

    fn round(number: RoundNumber, bindings: Vec<SlotLedgerBinding>) -> RoundState {
        RoundState::new(number, bindings).expect("valid round")
    }

    fn two_slot_round(
        number: RoundNumber,
        ledger: &super::ParsedSlotLedger,
        needles: &[&str],
    ) -> RoundState {
        round(
            number,
            vec![
                binding(Participant::Cursor, ledger.clone(), needles),
                binding(Participant::Codex, ledger.clone(), needles),
            ],
        )
    }

    fn proposal_after_round1_holds(hold_reason: &str) -> super::ProposalState {
        let proposal = new_proposal(&[pid(1), pid(2)], &[]).expect("proposal");
        let ledger = mixed_hold_agree(hold_reason);
        let round1 = two_slot_round(RoundNumber::Round1, &ledger, &[]);
        transition(
            &proposal,
            TransitionAction::SubmitRound,
            Some(&round1),
            None,
        )
        .expect("submit round 1")
    }

    fn proposal_awaiting_adjudication(hold_reason: &str) -> super::ProposalState {
        let after_r1 = proposal_after_round1_holds(hold_reason);
        let ledger = mixed_hold_agree(hold_reason);
        let round2 = two_slot_round(RoundNumber::Round2, &ledger, &[]);
        transition(
            &after_r1,
            TransitionAction::SubmitRound,
            Some(&round2),
            None,
        )
        .expect("submit round 2")
    }

    fn proposal_unconverged() -> super::ProposalState {
        let proposal = new_proposal(&[pid(1), pid(2)], &[]).expect("proposal");
        let r1_ledger = ledger_from_specs(&[(1, A::Hold, "round1 hold"), (2, A::Agree, "ok")]);
        let after_r1 = transition(
            &proposal,
            TransitionAction::SubmitRound,
            Some(&two_slot_round(RoundNumber::Round1, &r1_ledger, &[])),
            None,
        )
        .expect("submit round 1");
        let cursor_ledger = ledger_from_specs(&[(1, A::Hold, "round1 hold"), (2, A::Agree, "ok")]);
        let codex_ledger =
            ledger_from_specs(&[(1, A::Concede, "uncited fold"), (2, A::Agree, "ok")]);
        let round2 = round(
            RoundNumber::Round2,
            vec![
                binding(Participant::Cursor, cursor_ledger, &[]),
                binding(Participant::Codex, codex_ledger, &[]),
            ],
        );
        transition(
            &after_r1,
            TransitionAction::SubmitRound,
            Some(&round2),
            None,
        )
        .expect("submit round 2")
    }

    fn ledger_row(number: u16, action: A, reason: &str, concession: C) -> LedgerRow {
        LedgerRow {
            point_id: pid(number),
            action,
            reason: reason.to_owned(),
            concession,
        }
    }

    fn selected(number: u16, position: &str) -> AdjudicationRecord {
        AdjudicationRecord::Selected(
            SelectedAdjudication::new(pid(number), position.to_owned()).expect("selected"),
        )
    }

    fn split(number: u16, position_a: &str, position_b: &str) -> AdjudicationRecord {
        AdjudicationRecord::Split(
            SplitAdjudication::new(pid(number), position_a.to_owned(), position_b.to_owned())
                .expect("split"),
        )
    }

    // -----------------------------------------------------------------------
    // Binding and round assembly (test_protocol.py:831-922)
    // -----------------------------------------------------------------------

    #[test]
    fn forged_binding_fingerprint_rejected() {
        let ledger = agree_ledger(&[1]);
        let forged = vec![
            ReasonFingerprint::new("0".repeat(FINGERPRINT_HEX_LENGTH)).expect("forged fingerprint"),
        ];
        assert_eq!(
            SlotLedgerBinding::new(Participant::Cursor, ledger, forged, &[]),
            Err(R::FingerprintMismatch)
        );
    }

    #[test]
    fn round_construction_happy_path_and_ceiling() {
        let ledger = agree_ledger(&[1, 2]);
        let bindings = vec![
            binding(Participant::Cursor, ledger.clone(), &[]),
            binding(Participant::Codex, ledger.clone(), &[]),
            binding(Participant::Claude, ledger, &[]),
        ];
        let round_state = round(RoundNumber::Round1, bindings);
        assert_eq!(
            round_state.live_slots(),
            vec![Participant::Cursor, Participant::Codex, Participant::Claude]
        );
        assert_eq!(round_state.point_ids(), vec![pid(1), pid(2)]);
    }

    #[test]
    fn one_slot_below_live_panel_floor() {
        let ledger = agree_ledger(&[1]);
        assert_eq!(
            RoundState::new(
                RoundNumber::Round1,
                vec![binding(Participant::Cursor, ledger, &[])]
            ),
            Err(R::BelowLivePanelFloor)
        );
    }

    #[test]
    fn above_live_panel_ceiling() {
        let ledger = agree_ledger(&[1]);
        let bindings = vec![
            binding(Participant::Cursor, ledger.clone(), &[]),
            binding(Participant::Codex, ledger.clone(), &[]),
            binding(Participant::Claude, ledger.clone(), &[]),
            binding(Participant::Cursor, ledger, &[]),
        ];
        assert_eq!(
            RoundState::new(RoundNumber::Round1, bindings),
            Err(R::AboveLivePanelCeiling)
        );
    }

    #[test]
    fn point_universe_mismatch_and_empty() {
        let left = agree_ledger(&[1, 2]);
        let right = agree_ledger(&[1, 3]);
        assert_eq!(
            RoundState::new(
                RoundNumber::Round1,
                vec![
                    binding(Participant::Cursor, left, &[]),
                    binding(Participant::Codex, right, &[]),
                ]
            ),
            Err(R::PointUniverseMismatch)
        );
        assert_eq!(new_proposal(&[], &[]), Err(R::EmptyPointUniverse));
    }

    #[test]
    fn duplicate_points_in_universe_rejected() {
        assert_eq!(
            new_proposal(&[pid(1), pid(1)], &[]),
            Err(R::DuplicatePointId)
        );
    }

    #[test]
    fn invalid_slot_ordering_rejected() {
        let ledger = agree_ledger(&[1]);
        assert_eq!(
            RoundState::new(
                RoundNumber::Round1,
                vec![
                    binding(Participant::Codex, ledger.clone(), &[]),
                    binding(Participant::Cursor, ledger, &[]),
                ]
            ),
            Err(R::InvalidSlotOrdering)
        );
    }

    // -----------------------------------------------------------------------
    // Resolution (test_protocol.py:925-1039)
    // -----------------------------------------------------------------------

    #[test]
    fn resolution_matrix() {
        let cases = [
            (
                vec![
                    ledger_row(1, A::Agree, "a", C::NonConcession),
                    ledger_row(1, A::Agree, "b", C::NonConcession),
                ],
                PointResolution::Agreed,
            ),
            (
                vec![
                    ledger_row(1, A::Agree, "a", C::NonConcession),
                    ledger_row(1, A::Concede, "see POINT POINT_1", C::Cited),
                ],
                PointResolution::Conceded,
            ),
            (
                vec![
                    ledger_row(1, A::Concede, "fold", C::Fold),
                    ledger_row(1, A::Agree, "a", C::NonConcession),
                ],
                PointResolution::Folded,
            ),
            (
                vec![
                    ledger_row(1, A::Hold, "h", C::NonConcession),
                    ledger_row(1, A::Agree, "a", C::NonConcession),
                ],
                PointResolution::Held,
            ),
        ];
        for (rows, expected) in cases {
            assert_eq!(resolve_point(&rows), Ok(expected));
            let first = &rows[0];
            let closes = first.action == A::Agree
                || (first.action == A::Concede && first.concession == C::Cited);
            assert_eq!(slot_closes_point(first), closes);
        }
        assert_eq!(resolve_point(&[]), Err(R::BelowLivePanelFloor));
    }

    #[test]
    fn point_universe_order_continues_across_bindings_and_rounds() {
        let points = [pid(2), pid(1)];
        let proposal = new_proposal(&points, &[]).expect("proposal");
        assert_eq!(proposal.point_universe(), points.as_slice());
        let ledger =
            ledger_from_specs(&[(2, A::Agree, "second first"), (1, A::Agree, "first second")]);
        let round1 = two_slot_round(RoundNumber::Round1, &ledger, &[]);
        assert_eq!(round1.point_ids(), vec![pid(2), pid(1)]);
        let converged = transition(
            &proposal,
            TransitionAction::SubmitRound,
            Some(&round1),
            None,
        )
        .expect("converged");
        assert_eq!(
            converged.terminal_outcome(),
            Some(TerminalOutcome::Converged)
        );
        assert_eq!(converged.point_universe(), points.as_slice());
        assert_eq!(converged.rounds()[0].point_ids(), vec![pid(2), pid(1)]);
    }

    #[test]
    fn resolve_round_points_and_unresolved() {
        let ledger = mixed_hold_agree("hold");
        let round_state = two_slot_round(RoundNumber::Round1, &ledger, &[]);
        let resolutions = resolve_round_points(&round_state).expect("resolutions");
        assert_eq!(resolutions[&pid(1)], PointResolution::Held);
        assert_eq!(resolutions[&pid(2)], PointResolution::Agreed);
        assert_eq!(unresolved_points(&round_state), Ok(vec![pid(1)]));
        assert!(!round_is_fully_resolved(&round_state).expect("resolved"));
    }

    // -----------------------------------------------------------------------
    // Stalemate detection (test_protocol.py:1047-1198)
    // -----------------------------------------------------------------------

    #[test]
    fn stalemate_two_and_three_matching_holds() {
        let proposal = new_proposal(&[pid(1)], &[]).expect("proposal");
        let ledger = hold_ledger("unchanged hold text", &[1]);
        let earlier = two_slot_round(RoundNumber::Round1, &ledger, &[]);
        let later = two_slot_round(RoundNumber::Round2, &ledger, &[]);
        let detection = detect_stalemate_disputes(&proposal, &earlier, &later).expect("detection");
        assert_eq!(detection.status(), StalemateDetectionStatus::Completed);
        assert_eq!(detection.disputes().len(), 1);
        assert_eq!(
            detection.disputes()[0].holding_slots().to_vec(),
            vec![Participant::Cursor, Participant::Codex]
        );

        let three = round(
            RoundNumber::Round1,
            vec![
                binding(Participant::Cursor, ledger.clone(), &[]),
                binding(Participant::Codex, ledger.clone(), &[]),
                binding(Participant::Claude, ledger.clone(), &[]),
            ],
        );
        let three_later = round(
            RoundNumber::Round2,
            vec![
                binding(Participant::Cursor, ledger.clone(), &[]),
                binding(Participant::Codex, ledger.clone(), &[]),
                binding(Participant::Claude, ledger, &[]),
            ],
        );
        let detection3 =
            detect_stalemate_disputes(&proposal, &three, &three_later).expect("detection3");
        assert_eq!(
            detection3.disputes()[0].holding_slots().to_vec(),
            vec![Participant::Cursor, Participant::Codex, Participant::Claude]
        );
    }

    #[test]
    fn stalemate_one_matching_slot_is_empty_completed() {
        let proposal = new_proposal(&[pid(1)], &[]).expect("proposal");
        let cursor_hold = hold_ledger("same", &[1]);
        let earlier = round(
            RoundNumber::Round1,
            vec![
                binding(Participant::Cursor, cursor_hold.clone(), &[]),
                binding(Participant::Codex, hold_ledger("same", &[1]), &[]),
            ],
        );
        let later_codex = ledger_from_specs(&[(1, A::Agree, "changed mind")]);
        let later = round(
            RoundNumber::Round2,
            vec![
                binding(Participant::Cursor, cursor_hold, &[]),
                binding(Participant::Codex, later_codex, &[]),
            ],
        );
        let detection = detect_stalemate_disputes(&proposal, &earlier, &later).expect("detection");
        assert_eq!(detection.status(), StalemateDetectionStatus::Completed);
        assert!(detection.disputes().is_empty());
    }

    #[test]
    fn stalemate_changed_reason_or_action_skips_dispute() {
        let proposal = new_proposal(&[pid(1)], &[]).expect("proposal");
        let earlier = two_slot_round(RoundNumber::Round1, &hold_ledger("v1", &[1]), &[]);
        let later = two_slot_round(RoundNumber::Round2, &hold_ledger("v2", &[1]), &[]);
        let detection = detect_stalemate_disputes(&proposal, &earlier, &later).expect("detection");
        assert_eq!(detection.status(), StalemateDetectionStatus::Completed);
        assert!(detection.disputes().is_empty());
    }

    #[test]
    fn stalemate_membership_changed_distinct_from_empty() {
        let proposal = new_proposal(&[pid(1)], &[]).expect("proposal");
        let ledger = hold_ledger("same", &[1]);
        let earlier = two_slot_round(RoundNumber::Round1, &ledger, &[]);
        let later = round(
            RoundNumber::Round2,
            vec![
                binding(Participant::Cursor, ledger.clone(), &[]),
                binding(Participant::Claude, ledger, &[]),
            ],
        );
        let detection = detect_stalemate_disputes(&proposal, &earlier, &later).expect("detection");
        assert_eq!(
            detection.status(),
            StalemateDetectionStatus::MembershipChanged
        );
        assert!(detection.disputes().is_empty());
    }

    #[test]
    fn stalemate_nonadjacent_and_forged_fingerprints() {
        let proposal = new_proposal(&[pid(1)], &[]).expect("proposal");
        let ledger = hold_ledger("same", &[1]);
        let r1 = two_slot_round(RoundNumber::Round1, &ledger, &[]);
        assert_eq!(
            detect_stalemate_disputes(&proposal, &r1, &r1),
            Err(R::NonadjacentRounds)
        );
        // Construct a binding to exercise the public API, mirroring the Python
        // fixture that builds and discards a binding.
        let forged_binding = SlotLedgerBinding::new(
            Participant::Cursor,
            ledger.clone(),
            vec![fingerprint_reason("same", &[]).expect("fingerprint")],
            &[],
        );
        assert!(forged_binding.is_ok());
        let later = two_slot_round(RoundNumber::Round2, &ledger, &[]);
        let mismatched = new_proposal(&[pid(1)], &["same"]).expect("mismatched proposal");
        assert_eq!(
            detect_stalemate_disputes(&mismatched, &r1, &later),
            Err(R::FingerprintMismatch)
        );
    }

    #[test]
    fn stalemate_partial_dispute_coverage() {
        let proposal = new_proposal(&[pid(1), pid(2)], &[]).expect("proposal");
        let earlier_ledger = ledger_from_specs(&[(1, A::Hold, "stable"), (2, A::Hold, "moves")]);
        let later_ledger = ledger_from_specs(&[(1, A::Hold, "stable"), (2, A::Hold, "moved")]);
        let earlier = two_slot_round(RoundNumber::Round1, &earlier_ledger, &[]);
        let later = two_slot_round(RoundNumber::Round2, &later_ledger, &[]);
        let detection = detect_stalemate_disputes(&proposal, &earlier, &later).expect("detection");
        assert_eq!(detection.status(), StalemateDetectionStatus::Completed);
        let dispute_points: Vec<PointId> =
            detection.disputes().iter().map(Dispute::point_id).collect();
        assert_eq!(dispute_points, vec![pid(1)]);
    }

    #[test]
    fn dispute_requires_two_holding_slots() {
        assert_eq!(
            Dispute::new(pid(1), vec![Participant::Cursor]),
            Err(R::BelowLivePanelFloor)
        );
    }

    #[test]
    fn membership_changed_cannot_carry_disputes() {
        let dispute =
            Dispute::new(pid(1), vec![Participant::Cursor, Participant::Codex]).expect("dispute");
        assert_eq!(
            StalemateDetection::new(StalemateDetectionStatus::MembershipChanged, vec![dispute]),
            Err(R::InvalidProposalState)
        );
    }

    // -----------------------------------------------------------------------
    // Adjudication (test_protocol.py:1206-1290)
    // -----------------------------------------------------------------------

    #[test]
    fn selected_and_split_adjudication() {
        let selected =
            SelectedAdjudication::new(pid(1), "take cursor position".to_owned()).expect("selected");
        assert_eq!(selected.decision(), AdjudicationDecision::Selected);
        let split =
            SplitAdjudication::new(pid(1), "pos a".to_owned(), "pos b".to_owned()).expect("split");
        assert_eq!(split.decision(), AdjudicationDecision::Split);
        assert_eq!(
            SplitAdjudication::new(pid(1), "same".to_owned(), "same".to_owned()),
            Err(R::MalformedAdjudication)
        );
        assert_eq!(
            SelectedAdjudication::new(pid(1), String::new()),
            Err(R::MalformedAdjudication)
        );
        assert_eq!(
            SelectedAdjudication::new(pid(1), " leading".to_owned()),
            Err(R::MalformedAdjudication)
        );
        assert_eq!(
            SelectedAdjudication::new(pid(1), "has\nnewline".to_owned()),
            Err(R::MalformedAdjudication)
        );
        assert_eq!(
            SelectedAdjudication::new(pid(1), "### NEW: x.py".to_owned()),
            Err(R::ForbiddenPlanContent)
        );
    }

    #[test]
    fn adjudication_coverage_and_outcomes() {
        let unresolved = [pid(1), pid(2)];
        let selected_set = [selected(1, "a"), selected(2, "b")];
        assert_eq!(
            validate_adjudication_set(&unresolved, &selected_set),
            Ok(TerminalOutcome::Converged)
        );
        let split_set = [selected(1, "a"), split(2, "b1", "b2")];
        assert_eq!(
            validate_adjudication_set(&unresolved, &split_set),
            Ok(TerminalOutcome::BothViable)
        );
        assert_eq!(
            validate_adjudication_set(&[], &selected_set),
            Err(R::MalformedAdjudication)
        );
        assert_eq!(
            validate_adjudication_set(&unresolved, &[selected(1, "a")]),
            Err(R::IncompleteAdjudicationCoverage)
        );
        assert_eq!(
            validate_adjudication_set(&unresolved, &[selected(1, "a"), selected(3, "foreign")]),
            Err(R::MalformedAdjudication)
        );
        assert_eq!(
            validate_adjudication_set(&unresolved, &[selected(1, "a"), selected(1, "dup")]),
            Err(R::MalformedAdjudication)
        );
        assert_eq!(
            validate_adjudication_set(&[pid(1), pid(1)], &[selected(1, "a"), selected(1, "b")]),
            Err(R::DuplicatePointId)
        );
    }

    // -----------------------------------------------------------------------
    // Transition matrix (test_protocol.py:1298-1525)
    // -----------------------------------------------------------------------

    #[test]
    fn legal_edge_count_and_illegal_pairs() {
        let phases = [
            NonterminalPhase::BlindRound1,
            NonterminalPhase::Round2,
            NonterminalPhase::AwaitingAdjudication,
            NonterminalPhase::Unconverged,
        ];
        let actions = [
            TransitionAction::SubmitRound,
            TransitionAction::DeclareStalemate,
            TransitionAction::Adjudicate,
            TransitionAction::Abort,
        ];
        assert_eq!(phases.len() * actions.len(), 16);
        assert_eq!(LEGAL_EDGES.len(), 9);
        let illegal = phases
            .iter()
            .flat_map(|phase| actions.iter().map(move |action| (*phase, *action)))
            .filter(|(phase, action)| !is_legal_edge(*phase, *action))
            .count();
        assert_eq!(illegal, 7);
    }

    #[test]
    fn each_legal_edge_from_blind_and_round2() {
        let blind_abort = transition(
            &new_proposal(&[pid(1)], &[]).unwrap(),
            TransitionAction::Abort,
            None,
            None,
        )
        .expect("blind abort");
        assert_eq!(
            blind_abort.terminal_outcome(),
            Some(TerminalOutcome::Aborted)
        );
        assert_eq!(blind_abort.phase(), None);

        let blind_submit = transition(
            &new_proposal(&[pid(1)], &[]).unwrap(),
            TransitionAction::SubmitRound,
            Some(&two_slot_round(
                RoundNumber::Round1,
                &agree_ledger(&[1]),
                &[],
            )),
            None,
        )
        .expect("blind submit");
        assert_eq!(
            blind_submit.terminal_outcome(),
            Some(TerminalOutcome::Converged)
        );

        let round2 = proposal_after_round1_holds("stable hold reason");
        assert_eq!(round2.phase(), Some(NonterminalPhase::Round2));
        let round2_abort =
            transition(&round2, TransitionAction::Abort, None, None).expect("round2 abort");
        assert_eq!(
            round2_abort.terminal_outcome(),
            Some(TerminalOutcome::Aborted)
        );

        let ledger = mixed_hold_agree("stable hold reason");
        let round2_submit = transition(
            &proposal_after_round1_holds("stable hold reason"),
            TransitionAction::SubmitRound,
            Some(&two_slot_round(RoundNumber::Round2, &ledger, &[])),
            None,
        )
        .expect("round2 submit");
        assert_eq!(
            round2_submit.phase(),
            Some(NonterminalPhase::AwaitingAdjudication)
        );
        assert!(!round2_submit.disputes().is_empty());
    }

    #[test]
    fn each_legal_edge_from_awaiting_and_unconverged() {
        let stalemate = transition(
            &proposal_awaiting_adjudication("stable hold reason"),
            TransitionAction::DeclareStalemate,
            None,
            None,
        )
        .expect("stalemate");
        assert_eq!(
            stalemate.terminal_outcome(),
            Some(TerminalOutcome::Stalemate)
        );

        let adjudicated = transition(
            &proposal_awaiting_adjudication("stable hold reason"),
            TransitionAction::Adjudicate,
            None,
            Some(&[selected(1, "pick a")]),
        )
        .expect("adjudicated");
        assert_eq!(
            adjudicated.terminal_outcome(),
            Some(TerminalOutcome::Converged)
        );

        let await_abort = transition(
            &proposal_awaiting_adjudication("stable hold reason"),
            TransitionAction::Abort,
            None,
            None,
        )
        .expect("await abort");
        assert_eq!(
            await_abort.terminal_outcome(),
            Some(TerminalOutcome::Aborted)
        );
        assert!(await_abort.disputes().is_empty());

        let unconverged = proposal_unconverged();
        assert_eq!(unconverged.phase(), Some(NonterminalPhase::Unconverged));
        let both_viable = transition(
            &unconverged,
            TransitionAction::Adjudicate,
            None,
            Some(&[split(1, "left", "right")]),
        )
        .expect("both viable");
        assert_eq!(
            both_viable.terminal_outcome(),
            Some(TerminalOutcome::BothViable)
        );

        let unconv_abort = transition(&proposal_unconverged(), TransitionAction::Abort, None, None)
            .expect("unconv abort");
        assert_eq!(
            unconv_abort.terminal_outcome(),
            Some(TerminalOutcome::Aborted)
        );
    }

    #[test]
    fn illegal_edges_reject_before_payload() {
        let blind = new_proposal(&[pid(1)], &[]).expect("blind");
        let round2 = proposal_after_round1_holds("stable hold reason");
        let awaiting = proposal_awaiting_adjudication("stable hold reason");
        let unconverged = proposal_unconverged();
        let round_payload = two_slot_round(RoundNumber::Round1, &agree_ledger(&[1]), &[]);
        let adj_payload = [selected(1, "x")];

        let cases: [(&super::ProposalState, TransitionAction); 7] = [
            (&blind, TransitionAction::DeclareStalemate),
            (&blind, TransitionAction::Adjudicate),
            (&round2, TransitionAction::DeclareStalemate),
            (&round2, TransitionAction::Adjudicate),
            (&awaiting, TransitionAction::SubmitRound),
            (&unconverged, TransitionAction::SubmitRound),
            (&unconverged, TransitionAction::DeclareStalemate),
        ];
        for (proposal, action) in cases {
            let round_arg = if action == TransitionAction::SubmitRound {
                Some(&round_payload)
            } else {
                None
            };
            let adj_arg = if action == TransitionAction::Adjudicate {
                Some(&adj_payload[..])
            } else {
                None
            };
            assert_eq!(
                transition(proposal, action, round_arg, adj_arg),
                Err(R::IllegalTransition),
                "phase {:?} action {action:?}",
                proposal.phase()
            );
        }
    }

    #[test]
    fn terminal_immutability() {
        let terminal = transition(
            &new_proposal(&[pid(1)], &[]).unwrap(),
            TransitionAction::SubmitRound,
            Some(&two_slot_round(
                RoundNumber::Round1,
                &agree_ledger(&[1]),
                &[],
            )),
            None,
        )
        .expect("terminal");
        assert_eq!(
            terminal.terminal_outcome(),
            Some(TerminalOutcome::Converged)
        );
        for action in [
            TransitionAction::SubmitRound,
            TransitionAction::DeclareStalemate,
            TransitionAction::Adjudicate,
            TransitionAction::Abort,
        ] {
            assert_eq!(
                transition(&terminal, action, None, None),
                Err(R::IllegalTransition)
            );
        }
    }

    #[test]
    fn submit_round_payload_misuse_and_wrong_round() {
        let proposal = new_proposal(&[pid(1)], &[]).expect("proposal");
        let ledger = agree_ledger(&[1]);
        let round1 = two_slot_round(RoundNumber::Round1, &ledger, &[]);
        let adj = [selected(1, "x")];
        assert_eq!(
            transition(
                &proposal,
                TransitionAction::SubmitRound,
                Some(&round1),
                Some(&adj[..])
            ),
            Err(R::IllegalTransition)
        );
        assert_eq!(
            transition(&proposal, TransitionAction::SubmitRound, None, None),
            Err(R::IllegalTransition)
        );
        let wrong = two_slot_round(RoundNumber::Round2, &ledger, &[]);
        assert_eq!(
            transition(&proposal, TransitionAction::SubmitRound, Some(&wrong), None),
            Err(R::InvalidRoundNumber)
        );
    }

    #[test]
    fn abort_payload_must_be_empty() {
        let proposal = new_proposal(&[pid(1)], &[]).expect("proposal");
        let round1 = two_slot_round(RoundNumber::Round1, &agree_ledger(&[1]), &[]);
        assert_eq!(
            transition(&proposal, TransitionAction::Abort, Some(&round1), None),
            Err(R::IllegalTransition)
        );
    }

    #[test]
    fn round2_convergence_without_disputes() {
        let proposal = new_proposal(&[pid(1)], &[]).expect("proposal");
        let after_r1 = transition(
            &proposal,
            TransitionAction::SubmitRound,
            Some(&two_slot_round(
                RoundNumber::Round1,
                &hold_ledger("temp", &[1]),
                &[],
            )),
            None,
        )
        .expect("round 1");
        let converged = transition(
            &after_r1,
            TransitionAction::SubmitRound,
            Some(&two_slot_round(
                RoundNumber::Round2,
                &agree_ledger(&[1]),
                &[],
            )),
            None,
        )
        .expect("round 2");
        assert_eq!(
            converged.terminal_outcome(),
            Some(TerminalOutcome::Converged)
        );
        assert_eq!(converged.phase(), None);
    }
}
