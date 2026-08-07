//! The larch named issue-body block: a fail-closed, fence-aware wire grammar.
//!
//! Ports Python `larch.issue.issue_blocks` plus the pure block half of
//! `larch.issue.issue_wire`. Unlike `crate::report::markdown_block`, which
//! recovers from a lone marker by truncating, a malformed named block never
//! recovers: every defect returns a stable reason so a caller can refuse the
//! write. Markers inside balanced code fences are decompose or split examples
//! and never bound a block.

use std::{collections::BTreeSet, error::Error, fmt};

use crate::text::{balanced_fence_line_indices, split_lines_keep_ends};

/// The `/design` plan marker consumed by `/implement` preflight.
pub const PLAN_MARKER: &str = "plan";
/// The `/design` pause marker.
pub const DESIGN_PAUSE_MARKER: &str = "design-pause";
/// Every marker the named-block writers accept.
pub const ALLOWED_NAMED_BLOCK_MARKERS: [&str; 2] = [PLAN_MARKER, DESIGN_PAUSE_MARKER];

/// The M1 defect for an issue body carrying more than one plan block.
pub const MULTIPLE_PLAN_BLOCKS: &str = "multiple-plan-blocks";
/// The M1 defect for an issue body carrying no parseable plan block.
pub const MISSING_PLAN_BLOCK: &str = "missing-plan-block";

/// A neutralized comment opener: the same bytes plus a zero-width space.
const NEUTRALIZED_COMMENT_OPEN: &str = "<!--\u{200b}";

/// Why a named block failed to parse.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum NamedBlockDefect {
    /// More than one start marker.
    MultipleStart,
    /// More than one end marker.
    MultipleEnd,
    /// A start marker with no end marker.
    StartWithoutEnd,
    /// An end marker with no start marker.
    EndWithoutStart,
    /// The end marker precedes the start marker.
    EndBeforeStart,
}

impl NamedBlockDefect {
    /// Return the stable machine reason emitted as `MALFORMED=`.
    #[must_use]
    pub const fn reason(self) -> &'static str {
        match self {
            Self::MultipleStart => "multiple-start",
            Self::MultipleEnd => "multiple-end",
            Self::StartWithoutEnd => "start-without-end",
            Self::EndWithoutStart => "end-without-start",
            Self::EndBeforeStart => "end-before-start",
        }
    }
}

impl fmt::Display for NamedBlockDefect {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.reason())
    }
}

impl Error for NamedBlockDefect {}

/// Why a named-block write was refused.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum NamedBlockError {
    /// The marker is not one of [`ALLOWED_NAMED_BLOCK_MARKERS`].
    UnsupportedMarker,
    /// A plan write carried blank content.
    EmptyPlanContent,
    /// The existing body does not parse.
    Malformed(NamedBlockDefect),
}

impl NamedBlockError {
    /// Return the stable machine reason.
    #[must_use]
    pub const fn reason(self) -> &'static str {
        match self {
            Self::UnsupportedMarker => "unsupported-marker",
            Self::EmptyPlanContent => "empty-plan-content",
            Self::Malformed(defect) => defect.reason(),
        }
    }
}

impl fmt::Display for NamedBlockError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.reason())
    }
}

impl Error for NamedBlockError {}

impl From<NamedBlockDefect> for NamedBlockError {
    fn from(defect: NamedBlockDefect) -> Self {
        Self::Malformed(defect)
    }
}

/// The inclusive line span a named block occupies, marker lines included.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub struct NamedBlockSpan {
    start: usize,
    end: usize,
}

impl NamedBlockSpan {
    /// Return the 0-based index of the start-marker line.
    #[must_use]
    pub const fn start(self) -> usize {
        self.start
    }

    /// Return the 0-based index of the end-marker line.
    #[must_use]
    pub const fn end(self) -> usize {
        self.end
    }
}

/// How a named-block write changed the body.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum NamedBlockWriteMode {
    /// No block existed, so the composed block was appended.
    Appended,
    /// An existing block was replaced in place.
    Replaced,
    /// An existing block was deleted.
    Removed,
    /// A delete found no block, so the body is unchanged.
    AbsentNoop,
}

impl NamedBlockWriteMode {
    /// Return the exact `MODE=` value the named-block writer emits.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Appended => "appended",
            Self::Replaced => "replaced",
            Self::Removed => "removed",
            Self::AbsentNoop => "absent-noop",
        }
    }
}

/// The composed result of a named-block write, before redaction or transport.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NamedBlockWrite {
    mode: NamedBlockWriteMode,
    markers_present: bool,
    body: String,
}

impl NamedBlockWrite {
    /// Return how the write changed the body.
    #[must_use]
    pub const fn mode(&self) -> NamedBlockWriteMode {
        self.mode
    }

    /// Return whether the pre-write body already carried a parseable block.
    #[must_use]
    pub const fn markers_present(&self) -> bool {
        self.markers_present
    }

    /// Return the composed body.
    ///
    /// For [`NamedBlockWriteMode::AbsentNoop`] this is the pre-write body with
    /// trailing newlines stripped, and nothing needs to be sent.
    #[must_use]
    pub fn body(&self) -> &str {
        &self.body
    }
}

/// Return whether `marker` is syntactically well formed.
///
/// Mirrors the writer's `^[a-z0-9][a-z0-9-]*$` argument check, which separates
/// a malformed marker from a well-formed but unsupported one.
#[must_use]
pub fn is_valid_named_block_marker(marker: &str) -> bool {
    let mut characters = marker.chars();
    let Some(first) = characters.next() else {
        return false;
    };
    (first.is_ascii_lowercase() || first.is_ascii_digit())
        && characters.all(|character| {
            character.is_ascii_lowercase() || character.is_ascii_digit() || character == '-'
        })
}

/// Return whether `marker` is one of [`ALLOWED_NAMED_BLOCK_MARKERS`].
#[must_use]
pub fn named_block_marker_allowed(marker: &str) -> bool {
    ALLOWED_NAMED_BLOCK_MARKERS.contains(&marker)
}

/// Locate the sole unfenced named block in `body`.
///
/// Returns `Ok(None)` when neither marker appears.
///
/// # Errors
///
/// Returns the [`NamedBlockDefect`] for a duplicated, unpaired, or inverted
/// marker pair.
pub fn classify_named_block(
    body: &str,
    marker: &str,
) -> Result<Option<NamedBlockSpan>, NamedBlockDefect> {
    classify_lines(&split_lines_keep_ends(body), marker)
}

/// Return the inner text of the sole unfenced named block in `body`.
///
/// Returns `Ok(None)` when the block is absent. The inner text keeps its line
/// terminators so a round trip through [`compose_named_block`] is byte stable.
///
/// # Errors
///
/// Returns the [`NamedBlockDefect`] for a malformed marker pair.
pub fn parse_named_block(body: &str, marker: &str) -> Result<Option<String>, NamedBlockDefect> {
    let lines = split_lines_keep_ends(body);
    Ok(classify_lines(&lines, marker)?.map(|span| lines[span.start + 1..span.end].concat()))
}

/// Remove only the named block for `marker`, leaving unrelated larch blocks.
///
/// # Errors
///
/// Returns the [`NamedBlockDefect`] for a malformed marker pair.
pub fn strip_named_block(body: &str, marker: &str) -> Result<String, NamedBlockDefect> {
    let lines = split_lines_keep_ends(body);
    let Some(span) = classify_lines(&lines, marker)? else {
        return Ok(body.to_owned());
    };
    Ok(splice(&lines, span, ""))
}

/// Render a named block around `inner`.
#[must_use]
pub fn compose_named_block(marker: &str, inner: &str) -> String {
    let stripped = inner.trim_end_matches('\n');
    let inner_line = if stripped.is_empty() {
        String::new()
    } else {
        format!("{stripped}\n")
    };
    format!("<!-- larch:{marker}:start -->\n{inner_line}<!-- larch:{marker}:end -->\n")
}

/// Return the M1 plan-marker defect for an issue body, or `None` when exactly
/// one plan block exists.
#[must_use]
pub fn issue_plan_marker_defect(body: &str) -> Option<&'static str> {
    match classify_named_block(body, PLAN_MARKER) {
        Ok(Some(_)) => None,
        Err(NamedBlockDefect::MultipleStart | NamedBlockDefect::MultipleEnd) => {
            Some(MULTIPLE_PLAN_BLOCKS)
        }
        // Absent, unpaired, and inverted markers all read as a missing plan.
        Ok(None) | Err(_) => Some(MISSING_PLAN_BLOCK),
    }
}

/// Render marker examples inert before embedding them in prose.
///
/// A zero-width space after `<!--` keeps the example readable while stopping it
/// from bounding a real block.
///
/// # Errors
///
/// Returns [`NamedBlockError::UnsupportedMarker`] for a marker outside
/// [`ALLOWED_NAMED_BLOCK_MARKERS`].
pub fn neutralize_named_block_markers(text: &str, marker: &str) -> Result<String, NamedBlockError> {
    if !named_block_marker_allowed(marker) {
        return Err(NamedBlockError::UnsupportedMarker);
    }
    // The Python pattern is multiline-anchored, so LF alone delimits a line here.
    let mut output = String::with_capacity(text.len());
    for segment in text.split_inclusive('\n') {
        let (content, terminator) = segment
            .strip_suffix('\n')
            .map_or((segment, ""), |content| (content, "\n"));
        if neutralizable_marker_line(content, marker) {
            output.push_str(&content.replacen("<!--", NEUTRALIZED_COMMENT_OPEN, 1));
        } else {
            output.push_str(content);
        }
        output.push_str(terminator);
    }
    Ok(output)
}

/// Compose the body a named-block write would publish.
///
/// `content` is the block's inner text; `None` requests a delete. The returned
/// body is the exact bytes the writer sends, before redaction. Trailing
/// newlines are stripped from `body` first, matching the writer's read.
///
/// # Errors
///
/// Returns [`NamedBlockError::UnsupportedMarker`] for an unsupported marker,
/// [`NamedBlockError::EmptyPlanContent`] for a blank plan write, and
/// [`NamedBlockError::Malformed`] when the existing body does not parse.
pub fn plan_named_block_write(
    body: &str,
    marker: &str,
    content: Option<&str>,
) -> Result<NamedBlockWrite, NamedBlockError> {
    if !named_block_marker_allowed(marker) {
        return Err(NamedBlockError::UnsupportedMarker);
    }
    let current = body.trim_end_matches('\n');
    let lines = split_lines_keep_ends(current);
    let span = classify_lines(&lines, marker)?;
    let markers_present = span.is_some();
    let Some(content) = content else {
        let (mode, composed) = span.map_or_else(
            || (NamedBlockWriteMode::AbsentNoop, current.to_owned()),
            |span| (NamedBlockWriteMode::Removed, splice(&lines, span, "")),
        );
        return Ok(NamedBlockWrite {
            mode,
            markers_present,
            body: composed,
        });
    };
    if marker == PLAN_MARKER && content.trim().is_empty() {
        return Err(NamedBlockError::EmptyPlanContent);
    }
    let block = compose_named_block(marker, content);
    let (mode, composed) = span.map_or_else(
        || {
            let composed = if current.is_empty() {
                block.clone()
            } else {
                format!("{current}\n\n{block}")
            };
            (NamedBlockWriteMode::Appended, composed)
        },
        |span| (NamedBlockWriteMode::Replaced, splice(&lines, span, &block)),
    );
    Ok(NamedBlockWrite {
        mode,
        markers_present,
        body: composed,
    })
}

fn splice(lines: &[&str], span: NamedBlockSpan, replacement: &str) -> String {
    let mut composed = lines[..span.start].concat();
    composed.push_str(replacement);
    composed.push_str(&lines[span.end + 1..].concat());
    composed
}

fn classify_lines(
    lines: &[&str],
    marker: &str,
) -> Result<Option<NamedBlockSpan>, NamedBlockDefect> {
    let fenced = balanced_fence_line_indices(lines);
    let starts = marker_indexes(lines, &fenced, marker, "start");
    let ends = marker_indexes(lines, &fenced, marker, "end");
    match (starts.as_slice(), ends.as_slice()) {
        ([], []) => Ok(None),
        ([_, _, ..], _) => Err(NamedBlockDefect::MultipleStart),
        (_, [_, _, ..]) => Err(NamedBlockDefect::MultipleEnd),
        ([_], []) => Err(NamedBlockDefect::StartWithoutEnd),
        ([], [_]) => Err(NamedBlockDefect::EndWithoutStart),
        ([start], [end]) if end < start => Err(NamedBlockDefect::EndBeforeStart),
        ([start], [end]) => Ok(Some(NamedBlockSpan {
            start: *start,
            end: *end,
        })),
    }
}

fn marker_indexes(
    lines: &[&str],
    fenced: &BTreeSet<usize>,
    marker: &str,
    kind: &str,
) -> Vec<usize> {
    let token = marker_token(marker, kind);
    lines
        .iter()
        .enumerate()
        .filter(|(index, line)| !fenced.contains(index) && is_marker_line(line, &token))
        .map(|(index, _)| index)
        .collect()
}

fn marker_token(marker: &str, kind: &str) -> String {
    format!("larch:{marker}:{kind}")
}

/// Match Python `^[ \t]*<!--[ \t]+{token}[ \t]+-->[ \t]*\r?$`.
///
/// The comparison is case sensitive, and the marker text has no regex meaning:
/// only exact bytes bound a block.
fn is_marker_line(line: &str, token: &str) -> bool {
    let text = line.trim_end_matches(['\r', '\n']);
    let Some(rest) = text.trim_start_matches([' ', '\t']).strip_prefix("<!--") else {
        return false;
    };
    let Some(rest) = strip_after_blanks(rest, token) else {
        return false;
    };
    let Some(rest) = strip_after_blanks(rest, "-->") else {
        return false;
    };
    rest.chars()
        .all(|character| character == ' ' || character == '\t')
}

/// Strip `token` after at least one required space or tab.
fn strip_after_blanks<'a>(text: &'a str, token: &str) -> Option<&'a str> {
    let trimmed = text.trim_start_matches([' ', '\t']);
    if trimmed.len() == text.len() {
        return None;
    }
    trimmed.strip_prefix(token)
}

/// The neutralize pattern ends at `[ \t]*$`, so a trailing CR is not a marker.
fn neutralizable_marker_line(content: &str, marker: &str) -> bool {
    !content.ends_with('\r')
        && (is_marker_line(content, &marker_token(marker, "start"))
            || is_marker_line(content, &marker_token(marker, "end")))
}
