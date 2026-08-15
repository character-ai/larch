//! The out-of-scope record: what one OOS item is, and which bytes it owns.
//!
//! An OOS record is a Markdown block a reviewer, a design pass, or an external
//! implementer wrote. It opens with a canonical `### OOS_<n>: <title>` heading
//! and runs to the next heading that closes it. Ports the OOS-facing subset of
//! Python `larch.core.findings` together with `larch.issue.oos`. This is
//! the one Rust owner of the canonical block: the manifest, gate, and filer
//! leaves consume it, and the review pipeline reuses it when its own umbrella
//! migrates rather than adding a second parser.
//!
//! Three rules carry the weight. A heading inside a code fence is payload, not
//! a boundary, because reviewers quote each other's headings. A block tagged
//! `[security]` is never serialized for public filing, and the tag is read
//! after fenced code is removed so a quoted example cannot forge one. And an
//! accepted block keeps its exact source bytes: only line one is rewritten, to
//! renumber the record into the sequence being filed.

use crate::text::{split_lines_keep_ends, split_text_lines, trim_python_whitespace};
use regex::{NoExpand, Regex};
use std::sync::LazyLock;

/// Which canonical reviewer item a heading opened.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum OosItemKind {
    /// An in-scope review finding, `### FINDING_<n>:`.
    Finding,
    /// An out-of-scope observation, `### OOS_<n>:`.
    Oos,
}

impl OosItemKind {
    /// Render the token the item id embeds.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Finding => "FINDING",
            Self::Oos => "OOS",
        }
    }
}

/// One canonical item heading parsed from a single Markdown line.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CanonicalHeading {
    /// `FINDING_<n>` or `OOS_<n>`, exactly as written.
    pub item_id: String,
    /// Which grammar the heading opened.
    pub kind: OosItemKind,
    /// The heading's ordinal. Saturates rather than wrapping.
    pub number: u64,
    /// Exact ordinal digits, retained for consumers that need an unbounded value.
    pub ordinal_digits: String,
    /// The title text after the colon, whitespace trimmed.
    pub title: String,
}

/// Which later heading ends the block a canonical heading opened.
///
/// The review pipeline's `finding-heading` and `level-three-heading` policies
/// stay with `larch.core.findings` until the final compatibility cutover;
/// no OOS consumer asks for them.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum BlockBoundary {
    /// Any canonical heading closes the block.
    #[default]
    ItemHeading,
    /// Only an `### OOS_<n>:` heading closes the block.
    OosHeading,
    /// Only a `### FINDING_<n>:` heading closes the block.
    FindingHeading,
    /// Every level-three Markdown heading closes the block.
    LevelThreeHeading,
}

/// One canonical block with the exact source slice it owns.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OosBlock {
    /// `FINDING_<n>` or `OOS_<n>`, exactly as written.
    pub item_id: String,
    /// Which grammar opened the block.
    pub kind: OosItemKind,
    /// The heading title, whitespace trimmed.
    pub title: String,
    /// Every byte from the heading to the boundary that closed it.
    pub block: String,
    /// Byte offset of the heading in the source text.
    pub start: usize,
    /// Byte offset one past the block's last byte.
    pub end: usize,
}

/// What one serialization pass produced and what it withheld.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct SerializedOos {
    /// The renumbered accepted blocks, ready to write.
    pub text: String,
    /// How many blocks were serialized.
    pub accepted: usize,
    /// How many security-tagged blocks were withheld from public filing.
    pub held_security: usize,
}

static CANONICAL_HEADING_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^###[ \t]+(FINDING|OOS)_([0-9]+):(.*)$").expect("canonical heading expression")
});
static HEADER_TOKEN_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^###[ \t]+[A-Za-z]+_[0-9]+:").expect("header token expression"));
static SECURITY_HEADER_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^###[ \t]+(?i-u:OOS|FINDING)_\d+:[\s\x1c-\x1f]*(?:\[(?i-u:OUT_OF_SCOPE|OOS)\][\s\x1c-\x1f]*)?`?(?:\[(?i-u:security)\]|<(?i-u:security)>)`?(?:[\s\x1c-\x1f]|$|[:-])",
    )
    .expect("security heading expression")
});
static SECURITY_FIELD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^[ \t-]*(?i-u:focus)[- ](?i-u:area)[ \t]*[:=][ \t]*(?i-u:security)(?:[-a-zA-Z0-9 _]*)(?:[ \t]|$|\(|#|\.|,)",
    )
    .expect("security field expression")
});
static OOS_TAG_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:^|[\s\x1c-\x1f])\[(?i-u:OUT_OF_SCOPE|OOS)\](?:[\s\x1c-\x1f]|$|[:-])")
        .expect("OOS tag expression")
});
static PRESENT_RESULT_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(^|[ \t])Result=").expect("present result expression"));
static ACCEPTED_RESULT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(^|[ \t])Result=accepted([ \t]|$)").expect("accepted result expression")
});
static FILEABLE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^(?i-u:Vote tally:).*(?:^|[ \t])(?i-u:Fileable=true)(?:[ \t]|$)")
        .expect("fileable expression")
});

/// Shortest run of backticks or tildes that can open a Markdown code fence.
const FENCE_MIN_RUN: usize = 3;
/// Widest indent a Markdown code fence may carry.
const FENCE_MAX_INDENT: usize = 3;

/// A Markdown code-fence opener: how far it is indented, and its exact run.
struct FenceOpen<'a> {
    indent: usize,
    marker: &'a str,
}

/// Return the fence opener `line` carries, if any.
///
/// A fence indents at most three columns and repeats one backtick or tilde at
/// least three times. The run is returned whole because a closer has to repeat
/// it exactly, not merely start with it.
fn fence_open(line: &str) -> Option<FenceOpen<'_>> {
    let rest = line.trim_start_matches([' ', '\t']);
    let indent = line.len() - rest.len();
    if indent > FENCE_MAX_INDENT {
        return None;
    }
    let marker_char = rest.chars().next()?;
    if marker_char != '`' && marker_char != '~' {
        return None;
    }
    let run = rest
        .chars()
        .take_while(|character| *character == marker_char)
        .count();
    if run < FENCE_MIN_RUN {
        return None;
    }
    Some(FenceOpen {
        indent,
        marker: &rest[..run],
    })
}

/// Report whether `line` closes a fence opened with exactly `marker`.
fn closes_exact_fence(line: &str, marker: &str) -> bool {
    let rest = line.trim_start_matches([' ', '\t']);
    if line.len() - rest.len() > FENCE_MAX_INDENT {
        return false;
    }
    rest.strip_prefix(marker).is_some_and(|tail| {
        tail.chars()
            .all(|character| character == ' ' || character == '\t')
    })
}

/// Parse an exact `### FINDING_<n>:` or `### OOS_<n>:` heading line.
#[must_use]
pub fn parse_canonical_heading(line: &str) -> Option<CanonicalHeading> {
    let trimmed = line.trim_end_matches(['\r', '\n']);
    let captures = CANONICAL_HEADING_RE.captures(trimmed)?;
    let kind = if &captures[1] == "FINDING" {
        OosItemKind::Finding
    } else {
        OosItemKind::Oos
    };
    Some(CanonicalHeading {
        item_id: format!("{}_{}", kind.as_str(), &captures[2]),
        kind,
        number: captures[2].parse::<u64>().unwrap_or(u64::MAX),
        ordinal_digits: captures[2].to_owned(),
        title: trim_python_whitespace(&captures[3]).to_owned(),
    })
}

/// Report whether `line` is a canonical heading of the optional `kind`.
#[must_use]
pub fn is_canonical_heading(line: &str, kind: Option<OosItemKind>) -> bool {
    parse_canonical_heading(line)
        .is_some_and(|heading| kind.is_none_or(|wanted| heading.kind == wanted))
}

/// One source line: where it sits, and whether it opened a canonical block.
struct LineRecord {
    start: usize,
    heading: Option<CanonicalHeading>,
    level_three: bool,
}

/// Track fence state across one line and report whether that line is fenced.
///
/// The opening and the closing line both count as fenced, so a heading written
/// on either can never open a block.
fn advance_fence(line: &str, fence: &mut Option<(char, usize)>) -> bool {
    let was_open = fence.is_some();
    let Some(open) = fence_open(line) else {
        return was_open;
    };
    let marker_char = open
        .marker
        .chars()
        .next()
        .expect("a fence run is non-empty");
    let Some((current_char, current_len)) = *fence else {
        *fence = Some((marker_char, open.marker.len()));
        return true;
    };
    let tail = &line[open.indent + open.marker.len()..];
    if marker_char == current_char
        && open.marker.len() >= current_len
        && trim_python_whitespace(tail).is_empty()
    {
        *fence = None;
    }
    true
}

fn line_records(text: &str) -> Vec<LineRecord> {
    let mut records = Vec::new();
    let mut offset = 0;
    let mut fence: Option<(char, usize)> = None;
    for raw in split_lines_keep_ends(text) {
        let line = raw.trim_end_matches(['\r', '\n']);
        let fenced = advance_fence(line, &mut fence);
        records.push(LineRecord {
            start: offset,
            heading: if fenced {
                None
            } else {
                parse_canonical_heading(line)
            },
            level_three: !fenced && is_level_three_heading(line),
        });
        offset += raw.len();
    }
    records
}

fn is_level_three_heading(line: &str) -> bool {
    let rest = line.strip_prefix("###");
    rest.is_some_and(|tail| tail.is_empty() || tail.starts_with([' ', '\t']))
}

fn closes_block(boundary: BlockBoundary, record: &LineRecord) -> bool {
    match (boundary, record.heading.as_ref()) {
        (BlockBoundary::LevelThreeHeading, _) => record.level_three,
        (_, None) => false,
        (BlockBoundary::ItemHeading, Some(_)) => true,
        (BlockBoundary::OosHeading, Some(heading)) => heading.kind == OosItemKind::Oos,
        (BlockBoundary::FindingHeading, Some(heading)) => heading.kind == OosItemKind::Finding,
    }
}

/// Parse every canonical block in `text` under an explicit boundary policy.
#[must_use]
pub fn parse_oos_blocks(text: &str, boundary: BlockBoundary) -> Vec<OosBlock> {
    let records = line_records(text);
    let mut blocks = Vec::new();
    for (index, record) in records.iter().enumerate() {
        let Some(heading) = record.heading.as_ref() else {
            continue;
        };
        let end = records[index + 1..]
            .iter()
            .find(|next| closes_block(boundary, next))
            .map_or(text.len(), |next| next.start);
        blocks.push(OosBlock {
            item_id: heading.item_id.clone(),
            kind: heading.kind,
            title: heading.title.clone(),
            block: text[record.start..end].to_owned(),
            start: record.start,
            end,
        });
    }
    blocks
}

/// Return where the fence opened at `open_start` ends, if a line closes it.
///
/// A run longer than three shortens until a closer matches, because the
/// Python owner's greedy fence group backtracks the same way: a run of four
/// opens a four-character fence when one closes it, and a three-character
/// fence when only a run of three does. Longest run first, so the greedier
/// reading wins, exactly as the backtracking engine resolves it.
fn fence_close_end(text: &str, starts: &[usize], open_start: usize) -> Option<usize> {
    let open = fence_open(line_at(text, open_start))?;
    for length in (FENCE_MIN_RUN..=open.marker.len()).rev() {
        let marker = &open.marker[..length];
        let body_start = open_start + open.indent + length;
        let close_start = starts
            .iter()
            .filter(|start| **start >= body_start)
            .find(|start| closes_exact_fence(line_at(text, **start), marker));
        if let Some(&close_start) = close_start {
            return Some(close_start + line_at(text, close_start).len());
        }
    }
    None
}

/// Remove every balanced fenced code block, leaving the surrounding prose.
///
/// An opener with no closer is left alone, and scanning resumes one byte
/// later, so a truncated fence hides nothing that follows it.
fn strip_fenced_code_blocks(text: &str) -> String {
    let mut starts: Vec<usize> = vec![0];
    starts.extend(text.match_indices('\n').map(|(index, _)| index + 1));
    let mut output = String::new();
    let mut copied = 0;
    let mut cursor = 0;
    while let Some(&open_start) = starts.iter().find(|start| **start >= cursor) {
        match fence_close_end(text, &starts, open_start) {
            Some(close_end) => {
                output.push_str(&text[copied..open_start]);
                copied = close_end;
                cursor = close_end;
            }
            None => cursor = open_start + 1,
        }
    }
    output.push_str(&text[copied..]);
    output
}

/// Return the line beginning at `start`, without its trailing newline.
fn line_at(text: &str, start: usize) -> &str {
    let rest = &text[start..];
    rest.find('\n').map_or(rest, |index| &rest[..index])
}

/// Report whether a block carries an explicit security tag.
///
/// Fenced code is removed first: a reviewer quoting a security heading inside
/// an example must not route the quoting block to the private channel.
#[must_use]
pub fn is_security_block_text(text: &str) -> bool {
    let without_fences = strip_fenced_code_blocks(text);
    let lines = split_text_lines(&without_fences);
    if lines
        .first()
        .is_some_and(|first| SECURITY_HEADER_RE.is_match(first))
    {
        return true;
    }
    lines.iter().any(|line| {
        let cleaned = line.replace(['`', '*'], "");
        SECURITY_FIELD_RE.is_match(trim_python_whitespace(&cleaned))
    })
}

/// Report whether a canonical block is eligible for OOS filing.
///
/// An `OOS` block always is. A `FINDING` block qualifies only when its heading
/// carries an explicit `[OUT_OF_SCOPE]` or `[OOS]` tag.
#[must_use]
pub fn is_oos_eligible_block(block: &OosBlock) -> bool {
    if block.kind == OosItemKind::Oos {
        return true;
    }
    split_text_lines(&block.block)
        .first()
        .is_some_and(|first| OOS_TAG_RE.is_match(first))
}

/// Count fileable OOS blocks in `text`, excluding security-tagged ones.
#[must_use]
pub fn count_non_security_blocks(text: &str) -> usize {
    parse_oos_blocks(text, BlockBoundary::ItemHeading)
        .iter()
        .filter(|block| is_oos_eligible_block(block) && !is_security_block_text(&block.block))
        .count()
}

/// Rewrite only line one of `block_text` to the canonical `### OOS_<seq>:` id.
///
/// Every other byte survives, including the trailing newline shape, because
/// the block's body is the reviewer's own prose and filing must not edit it.
#[must_use]
pub fn normalize_oos_block_header(seq: u64, block_text: &str) -> String {
    let lines = split_lines_keep_ends(block_text);
    let Some(first) = lines.first() else {
        return block_text.to_owned();
    };
    let replacement = format!("### OOS_{seq}:");
    let mut output = HEADER_TOKEN_RE
        .replacen(first, 1, NoExpand(&replacement))
        .into_owned();
    for line in &lines[1..] {
        output.push_str(line);
    }
    output
}

/// Report whether a review artifact marked this block fileable.
fn artifact_marked_fileable(block: &str) -> bool {
    FILEABLE_RE.is_match(block)
}

/// Report whether `block` carries an accepted, fileable vote tally.
fn is_vote_tally_eligible(block: &str) -> bool {
    let mut found_result = false;
    let mut found_accepted = false;
    for line in split_text_lines(block) {
        if !line.starts_with("Vote tally: ") || !PRESENT_RESULT_RE.is_match(line) {
            continue;
        }
        found_result = true;
        found_accepted |= ACCEPTED_RESULT_RE.is_match(line);
    }
    found_result && found_accepted && artifact_marked_fileable(block)
}

/// Report whether `block` re-parses as exactly one OOS-eligible record.
fn is_single_oos_block(block: &str) -> bool {
    let parsed = parse_oos_blocks(block, BlockBoundary::ItemHeading);
    parsed.len() == 1 && is_oos_eligible_block(&parsed[0])
}

/// Serialize the accepted non-security OOS records found in `text`.
///
/// Records are renumbered from one in source order, so the output is a
/// self-consistent batch no matter which records the vote dropped. Every
/// other byte of an accepted record survives, so a caller reading the findings
/// file must apply [`crate::universal_newlines`] exactly when the Python
/// reader it replaces did, or the round trip stops being byte stable.
#[must_use]
pub fn serialize_accepted_oos(text: &str) -> SerializedOos {
    let mut result = SerializedOos::default();
    for block in parse_oos_blocks(text, BlockBoundary::ItemHeading) {
        if !is_single_oos_block(&block.block) {
            continue;
        }
        if is_security_block_text(&block.block) {
            result.held_security += 1;
            continue;
        }
        if !is_vote_tally_eligible(&block.block) {
            continue;
        }
        result.accepted += 1;
        let seq = u64::try_from(result.accepted).unwrap_or(u64::MAX);
        result
            .text
            .push_str(&normalize_oos_block_header(seq, &block.block));
        result.text.push('\n');
    }
    result
}

#[cfg(test)]
mod tests {
    use super::{
        BlockBoundary, OosItemKind, count_non_security_blocks, is_canonical_heading,
        is_oos_eligible_block, is_security_block_text, normalize_oos_block_header,
        parse_canonical_heading, parse_oos_blocks, serialize_accepted_oos,
        strip_fenced_code_blocks,
    };

    const ACCEPTED: &str = concat!(
        "### OOS_7: Widen the retry window\n",
        "- **Description**: The backoff is too tight.\n",
        "Vote tally: Result=accepted Fileable=true\n",
    );

    #[test]
    fn heading_parse_keeps_the_written_ordinal() {
        let heading = parse_canonical_heading("###\tOOS_012:  Trim  ").expect("heading");
        assert_eq!(heading.item_id, "OOS_012");
        assert_eq!(heading.number, 12);
        assert_eq!(heading.title, "Trim");
        assert_eq!(heading.kind.as_str(), "OOS");
    }

    #[test]
    fn heading_ordinal_saturates_instead_of_wrapping() {
        let heading =
            parse_canonical_heading(&format!("### FINDING_{}9: x", u64::MAX)).expect("heading");
        assert_eq!(heading.number, u64::MAX);
        assert_eq!(heading.kind, OosItemKind::Finding);
    }

    #[test]
    fn non_headings_and_kind_filters_are_rejected() {
        assert!(parse_canonical_heading("## OOS_1: nope").is_none());
        assert!(parse_canonical_heading("### OOS_1: a\nb").is_none());
        assert!(!is_canonical_heading(
            "### OOS_1: a",
            Some(OosItemKind::Finding)
        ));
        assert!(is_canonical_heading("### OOS_1: a", None));
    }

    #[test]
    fn fenced_headings_never_open_blocks() {
        let text = "### OOS_1: real\n```\n### OOS_2: quoted\n```\ntail\n";
        let blocks = parse_oos_blocks(text, BlockBoundary::ItemHeading);
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block, text);
    }

    #[test]
    fn deeply_indented_and_short_runs_are_not_fences() {
        let text = "     ```\n### OOS_1: real\n``\n";
        assert_eq!(parse_oos_blocks(text, BlockBoundary::ItemHeading).len(), 1);
    }

    #[test]
    fn oos_boundary_lets_a_finding_stay_inside_the_block() {
        let text = "### OOS_1: a\n### FINDING_2: b\n### OOS_3: c\n";
        let item = parse_oos_blocks(text, BlockBoundary::ItemHeading);
        assert_eq!(item.len(), 3);
        let oos = parse_oos_blocks(text, BlockBoundary::OosHeading);
        assert_eq!(oos.len(), 3);
        assert_eq!(oos[0].block, "### OOS_1: a\n### FINDING_2: b\n");
        assert_eq!((oos[1].start, oos[1].end), (13, 30));
        assert_eq!(oos[2].end, text.len());
    }

    #[test]
    fn tilde_fence_closes_only_on_its_own_marker() {
        let text = "~~~\n```\n### OOS_1: hidden\n~~~~\ntail\n";
        assert!(parse_oos_blocks(text, BlockBoundary::ItemHeading).is_empty());
    }

    #[test]
    fn unclosed_fence_still_hides_the_rest_of_the_file() {
        let text = "```\n### OOS_1: hidden\n";
        assert!(parse_oos_blocks(text, BlockBoundary::ItemHeading).is_empty());
    }

    #[test]
    fn security_tag_is_read_after_fenced_code_is_removed() {
        let quoted = "### OOS_1: safe\n```\n- focus-area: security\n```\n";
        assert!(!is_security_block_text(quoted));
        assert!(is_security_block_text(
            "### OOS_1: safe\n- **focus-area**: security-review\n"
        ));
        assert!(is_security_block_text(
            "### OOS_1: [OOS] `[security]` leak\n"
        ));
        assert!(is_security_block_text("### FINDING_2: <security> leak\n"));
    }

    #[test]
    fn unclosed_fence_leaves_its_contents_visible_to_the_security_scan() {
        assert_eq!(strip_fenced_code_blocks("a\n```\nb\n"), "a\n```\nb\n");
        assert_eq!(strip_fenced_code_blocks("a\n```\nb\n```\nc\n"), "a\n\nc\n");
        assert_eq!(strip_fenced_code_blocks("````\nb\n```\n````\n"), "\n");
    }

    #[test]
    fn finding_blocks_need_an_explicit_out_of_scope_tag() {
        let tagged = parse_oos_blocks(
            "### FINDING_1: [OUT_OF_SCOPE] later\n",
            BlockBoundary::ItemHeading,
        );
        assert!(is_oos_eligible_block(&tagged[0]));
        let plain = parse_oos_blocks("### FINDING_2: now\n", BlockBoundary::ItemHeading);
        assert!(!is_oos_eligible_block(&plain[0]));
        assert!(parse_oos_blocks("", BlockBoundary::ItemHeading).is_empty());
    }

    #[test]
    fn non_security_count_excludes_tagged_and_in_scope_blocks() {
        let text = concat!(
            "### OOS_1: keep\n",
            "### OOS_2: [security] hold\n",
            "### FINDING_3: in scope\n",
        );
        assert_eq!(count_non_security_blocks(text), 1);
    }

    #[test]
    fn header_normalization_touches_only_line_one() {
        assert_eq!(
            normalize_oos_block_header(4, "### FINDING_9: t\nbody\n"),
            "### OOS_4: t\nbody\n"
        );
        assert_eq!(normalize_oos_block_header(1, ""), "");
        assert_eq!(normalize_oos_block_header(1, "plain\n"), "plain\n");
    }

    #[test]
    fn serialization_renumbers_and_holds_security_records() {
        let text = format!(
            "{ACCEPTED}### OOS_8: [security] hold\nVote tally: Result=accepted Fileable=true\n{ACCEPTED}"
        );
        let serialized = serialize_accepted_oos(&text);
        assert_eq!(serialized.accepted, 2);
        assert_eq!(serialized.held_security, 1);
        assert!(
            serialized
                .text
                .starts_with("### OOS_1: Widen the retry window\n")
        );
        assert!(
            serialized
                .text
                .contains("### OOS_2: Widen the retry window\n")
        );
    }

    #[test]
    fn serialization_drops_records_the_vote_did_not_accept() {
        for tally in [
            "Vote tally: Result=rejected Fileable=true",
            "Vote tally: Result=accepted",
            "Vote tally: Fileable=true",
            "Vote tally: Result=acceptedish Fileable=true",
        ] {
            let text = format!("### OOS_1: t\n- **Description**: d\n{tally}\n");
            assert_eq!(serialize_accepted_oos(&text).accepted, 0, "{tally}");
        }
    }

    #[test]
    fn serialization_skips_blocks_that_are_not_oos_eligible() {
        let text = "### FINDING_1: in scope\nVote tally: Result=accepted Fileable=true\n";
        let serialized = serialize_accepted_oos(text);
        assert_eq!(serialized, super::SerializedOos::default());
    }
}
