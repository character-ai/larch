//! Shared review voting policy and parsing primitives.
use super::{BoundaryMode, parse_blocks};
use crate::text::{
    ensure_ascii_json, is_python_whitespace, python_bigint, split_text_lines,
    trim_python_whitespace,
};
use num_bigint::BigInt;
use regex::{Regex, RegexBuilder};
use std::{
    collections::{BTreeMap, HashSet},
    fmt::Write as _,
    sync::LazyLock,
};
/// The plan-review classification schema exposed to shell callers.
pub const FINDINGS_CLASSIFICATION_HEADER: &str = "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity\tscope";
static TABLE_VOTE_ID: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^(?:FINDING|OOS)_[0-9]+$").expect("static table vote-id regex"));
static PYTHON_WORD_PREFIX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[\p{L}\p{N}_]").expect("static Python word regex"));
static REVIEWER_ATTRIBUTION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^[\s\x{1c}-\x{1f}-]*(?:\*\*Reviewer\(s\)\*\*|\*\*Reviewers?\*\*|Reviewer\(s\)|Reviewers?)[\s\x{1c}-\x{1f}]*:[\s\x{1c}-\x{1f}]*(.*?)[ \t]*$",
    )
    .expect("static reviewer attribution regex")
});
static BALLOT_FINDING_HEADING: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^### FINDING_[0-9]+:[\s\x{1c}-\x{1f}]*(.*)").expect("static ballot heading")
});
static OOS_TITLE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^\[(OUT_OF_SCOPE|OOS)\]").expect("static OOS title"));
static FALSE_POSITIVE_NEGATIONS: LazyLock<Regex> = LazyLock::new(|| {
    insensitive_regex(concat!(
        r"(?:(^|[^a-z])not\s+((a|an)\s+)?duplicate([^a-z]|$))|",
        r"(?:(^|[^a-z])not\s+((a|an)\s+)?false[- ]positive([^a-z]|$))",
    ))
});
static FALSE_POSITIVE_MATCHES: LazyLock<Regex> = LazyLock::new(|| {
    insensitive_regex(concat!(
        r"(?:(^|[^a-z])won[^\s]*t\s+fix([^a-z]|$))|(?:(^|[^a-z])wontfix([^a-z]|$))|",
        r"(?:(^|[^a-z])superseded(\s+by\s+#[0-9]+)?([^a-z]|$))|",
        r"(?:(^|[^a-z])not\s+an\s+issue([^a-z]|$))|(?:(^|[^a-z])not\s+a\s+bug([^a-z]|$))|",
        r"(?:(^|[^a-z])duplicate\s+of\s+#[0-9]+([^a-z]|$))|(?:(^|[^a-z])false[- ]positive([^a-z]|$))",
    ))
});
fn insensitive_regex(source: &str) -> Regex {
    RegexBuilder::new(source)
        .case_insensitive(true)
        .build()
        .expect("static case-insensitive regex")
}
#[rustfmt::skip]
fn python_regex_text(text: &str) -> String {
    text.chars().map(|c| match c { 'İ' | 'ı' => 'i', 'ſ' => 's', 'K' => 'k', '\u{1c}'..='\u{1f}' => ' ', _ => c }).collect()
}
#[rustfmt::skip]
fn scoped_vote_line<'a>(ballot_id: &str, line: &'a str) -> Option<&'a str> {
    let end = line.char_indices().nth(ballot_id.chars().count()).map_or(line.len(), |(index, _)| index);
    let (candidate, tail) = line.split_at(end);
    if !python_regex_text(candidate).eq_ignore_ascii_case(&python_regex_text(ballot_id)) { return None; }
    Some(tail.strip_prefix(':')?.trim_start_matches(is_python_whitespace))
}
#[rustfmt::skip]
fn vote_token(text: &str) -> Option<&'static str> {
    for (token, vote) in [("YES", "YES"), ("NO", "NO"), ("EXONERATE", "NO")] {
        let end = text.char_indices().nth(token.len()).map_or(text.len(), |(index, _)| index);
        let (candidate, tail) = text.split_at(end);
        if python_regex_text(candidate).eq_ignore_ascii_case(token)
            && (tail.is_empty() || tail.starts_with(is_python_whitespace) || tail.starts_with('-')) { return Some(vote); }
    }
    None
}
#[rustfmt::skip]
fn table_vote_token(text: &str) -> Option<&'static str> {
    for token in ["YES", "NO", "EXONERATE"] {
        let end = text.char_indices().nth(token.len()).map_or(text.len(), |(index, _)| index);
        let (candidate, tail) = text.split_at(end);
        if !PYTHON_WORD_PREFIX.is_match(tail) && python_regex_text(candidate).eq_ignore_ascii_case(token) { return Some(token); }
    }
    None
}
#[rustfmt::skip]
fn strip_markdown_markers(cell: &str) -> String { trim_python_whitespace(&cell.replace(['*', '`'], "")).to_owned() }
#[rustfmt::skip]
fn normalize_markdown_table_votes(text: &str) -> String {
    if !text.contains('|') {
        return text.to_owned();
    }
    split_text_lines(text)
        .into_iter()
        .map(|line| {
            let stripped = trim_python_whitespace(line);
            if !stripped.starts_with('|') {
                return line.to_owned();
            }
            let cells: Vec<String> = stripped
                .trim_matches('|')
                .split('|')
                .map(|cell| trim_python_whitespace(cell).to_owned())
                .collect();
            if cells.len() < 2 {
                return line.to_owned();
            }
            let ballot_id = strip_markdown_markers(&cells[0]).to_uppercase();
            let vote_cell = strip_markdown_markers(&cells[1]);
            let Some(vote) = table_vote_token(&vote_cell) else {
                return line.to_owned();
            };
            if !TABLE_VOTE_ID.is_match(&ballot_id) {
                return line.to_owned();
            }
            let mut axes = Vec::new();
            let mut reason = Vec::new();
            for cell in &cells[2..] {
                for part in strip_markdown_markers(cell).split(is_python_whitespace).filter(|part| !part.is_empty()) {
                    if ["CORRECTNESS=", "SEVERITY=", "QUALITY=", "UNCERTAIN="]
                        .iter()
                        .any(|prefix| part.starts_with(prefix))
                    {
                        axes.push(part.to_owned());
                    } else {
                        reason.push(part.to_owned());
                    }
                }
            }
            let mut output = format!("{ballot_id}: {vote}");
            if !axes.is_empty() {
                output.push(' ');
                output.push_str(&axes.join(" "));
            }
            if !reason.is_empty() {
                output.push_str(" -- ");
                output.push_str(&reason.join(" "));
            }
            output
        })
        .collect::<Vec<_>>()
        .join("\n")
}
fn vote_from_lines(ballot_id: &str, lines: &[&str]) -> &'static str {
    let mut result = "JUDGE_ERROR";
    for line in lines {
        if let Some(vote) = scoped_vote_line(ballot_id, line).and_then(vote_token) {
            result = vote;
        }
    }
    result
}
/// Parse the last anchored vote for one ballot id, with an optional safe alias.
#[must_use]
pub fn vote_for_id_text(ballot_id: &str, text: &str, alias_id: &str) -> &'static str {
    let normalized = normalize_markdown_table_votes(text);
    let lines = split_text_lines(&normalized);
    let result = vote_from_lines(ballot_id, &lines);
    if result != "JUDGE_ERROR" || alias_id.is_empty() {
        result
    } else {
        vote_from_lines(alias_id, &lines)
    }
}
/// Return a finding/OOS alias only when it cannot collide with another item.
#[must_use]
#[rustfmt::skip]
pub fn alias_ballot_id<S: std::hash::BuildHasher>(ballot_id: &str, ballot_ids: &HashSet<String, S>) -> String {
    if !ballot_ids.contains(ballot_id) {
        return String::new();
    }
    let Some((prefix, digits)) = ballot_id.split_once('_') else {
        return String::new();
    };
    if !digits.bytes().all(|byte| byte.is_ascii_digit()) || !matches!(prefix, "FINDING" | "OOS") {
        return String::new();
    }
    let alias = format!(
        "{}_{}",
        if prefix == "FINDING" {
            "OOS"
        } else {
            "FINDING"
        },
        digits
    );
    if ballot_ids.contains(&alias) {
        String::new()
    } else {
        alias
    }
}
/// Parsed judge axes for one ballot item.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ParsedJudgeVote {
    pub vote: String,
    pub correctness: String,
    pub severity: String,
    pub quality: String,
    pub uncertain: String,
}
fn assign_axis(target: &mut String, value: &str, choices: &[&str]) {
    if choices.contains(&value) {
        value.clone_into(target);
    } else {
        target.clear();
    }
}
#[rustfmt::skip]
fn parse_judge_vote_lines(ballot_id: &str, lines: &[&str]) -> ParsedJudgeVote {
    let mut parsed = ParsedJudgeVote::default();
    for line in lines {
        let Some(scoped) = scoped_vote_line(ballot_id, line) else { continue; };
        parsed = ParsedJudgeVote::default();
        let scoped = scoped
            .split_once(" -- ")
            .map_or(scoped, |(head, _)| head);
        if let Some(vote) = vote_token(scoped) { vote.clone_into(&mut parsed.vote); }
        for part in scoped.split(is_python_whitespace).filter(|part| !part.is_empty()) {
            if let Some(value) = part.strip_prefix("CORRECTNESS=") {
                assign_axis(
                    &mut parsed.correctness,
                    value,
                    &["true", "partially-true", "false-positive", "uncertain"],
                );
            } else if let Some(value) = part.strip_prefix("SEVERITY=") {
                assign_axis(&mut parsed.severity, value, &["major", "minor", "nit"]);
            } else if let Some(value) = part.strip_prefix("QUALITY=") {
                #[rustfmt::skip]
                const CHOICES: &[&str] = &["excellent", "good", "adequate", "weak", "no-fix", "uncertain"];
                assign_axis(&mut parsed.quality, value, CHOICES);
            } else if let Some(value) = part.strip_prefix("UNCERTAIN=") {
                assign_axis(&mut parsed.uncertain, value, &["true", "false"]);
            }
        }
    }
    if parsed.correctness.is_empty()
        || parsed.severity.is_empty()
        || parsed.quality.is_empty()
        || parsed.uncertain.is_empty()
    {
        "true".clone_into(&mut parsed.uncertain);
    }
    parsed
}
/// Parse one structured judge line, falling back to the supplied safe alias.
#[must_use]
pub fn parse_judge_vote_text(ballot_id: &str, text: &str, alias_id: &str) -> ParsedJudgeVote {
    let normalized = normalize_markdown_table_votes(text);
    let lines = split_text_lines(&normalized);
    let parsed = parse_judge_vote_lines(ballot_id, &lines);
    if !parsed.vote.is_empty() || alias_id.is_empty() {
        parsed
    } else {
        parse_judge_vote_lines(alias_id, &lines)
    }
}
/// Extract the first reviewer attribution from a finding block.
#[must_use]
pub fn reviewer_for_block_text(text: &str) -> String {
    for line in split_text_lines(text) {
        if let Some(captures) = REVIEWER_ATTRIBUTION.captures(line) {
            let value = trim_python_whitespace(&captures[1].replace('*', "")).to_owned();
            return if value.is_empty() {
                "unknown".to_owned()
            } else {
                value
            };
        }
    }
    "unknown".to_owned()
}
/// Parse canonical ballot blocks, refusing duplicate headings.
///
/// # Errors
///
/// Returns the duplicate item identifier when a heading is repeated.
pub fn ballot_blocks(text: &str) -> Result<Vec<(String, String)>, String> {
    let mut blocks = Vec::new();
    let mut seen = HashSet::new();
    for parsed in parse_blocks(text, BoundaryMode::ItemHeading) {
        if !seen.insert(parsed.item_id.clone()) {
            return Err(format!("duplicate ballot heading {}", parsed.item_id));
        }
        blocks.push((parsed.item_id, parsed.block));
    }
    Ok(blocks)
}
/// Parse the legacy sequential finding summary wire.
#[must_use]
#[rustfmt::skip]
pub fn ballot_parse_text(text: &str) -> Vec<String> {
    let mut output = Vec::new();
    let mut index = 0_usize;
    let mut title = String::new();
    let mut concern = String::new();
    let mut oos = false;
    let emit = |output: &mut Vec<String>, index: usize, title: &str, concern: &str, oos: bool| {
        if index > 0 {
            output.push(format!("FINDING_{index}_TITLE={title}"));
            output.push(format!("FINDING_{index}_CONCERN={}", trim_python_whitespace(concern)));
            output.push(format!(
                "FINDING_{index}_OOS={}",
                if oos { "true" } else { "false" }
            ));
        }
    };
    for line in split_text_lines(text) {
        if let Some(captures) = BALLOT_FINDING_HEADING.captures(line) {
            emit(&mut output, index, &title, &concern, oos);
            index += 1;
            captures[1].clone_into(&mut title);
            concern.clear();
            oos = OOS_TITLE.is_match(&title);
            continue;
        }
        if index > 0 {
            if let Some(value) = line.strip_prefix("- **Concern**:") {
                value.trim_start_matches(is_python_whitespace).clone_into(&mut concern);
            } else if !concern.is_empty() && !line.starts_with("- **") {
                concern.push(' ');
                concern.push_str(line);
            }
            if line.contains("[OUT_OF_SCOPE]") || line.contains("[OOS]") {
                oos = true;
            }
        }
    }
    emit(&mut output, index, &title, &concern, oos);
    output.push(format!("FINDING_COUNT={index}"));
    output
}
/// Whether prose contains a durable false-positive disposition.
#[must_use]
pub fn false_positive_match(text: &str) -> bool {
    let text = python_regex_text(text);
    !FALSE_POSITIVE_NEGATIONS.is_match(&text) && FALSE_POSITIVE_MATCHES.is_match(&text)
}
fn finding_accepted<T: From<u8> + PartialOrd>(yes: &T, eligible: &T) -> bool {
    if eligible <= &T::from(0) {
        false
    } else if eligible == &T::from(1) {
        yes == &T::from(1)
    } else if eligible == &T::from(2) {
        yes == &T::from(2)
    } else {
        yes >= &T::from(2)
    }
}
/// Whether the historical finding threshold accepts an unbounded CLI value.
#[must_use]
pub fn accept_finding(yes: &BigInt, eligible: &BigInt) -> bool {
    finding_accepted(yes, eligible)
}
/// Return the voter-panel tier for an eligible count.
#[must_use]
pub fn panel_tier(eligible: &BigInt) -> &'static str {
    if eligible >= &BigInt::from(3u8) {
        "full-3"
    } else if eligible == &BigInt::from(2u8) {
        "unanimous-2"
    } else if eligible == &BigInt::from(1u8) {
        "single-judge"
    } else {
        "main-agent-required"
    }
}
/// Classify a finding according to the historical one-, two-, and three-voter thresholds.
#[must_use]
fn classify_finding<T: From<u8> + PartialOrd>(yes: &T, eligible: &T) -> &'static str {
    if eligible <= &T::from(0) {
        return "rejected";
    }
    if finding_accepted(yes, eligible) {
        "accepted"
    } else if yes > &T::from(0) {
        "neutral"
    } else {
        "rejected"
    }
}
/// Classify the bounded counts used by the in-process tally engine.
#[must_use]
pub fn classify_result(yes: usize, eligible: usize) -> &'static str {
    classify_finding(&yes, &eligible)
}
/// Classify unbounded Python-compatible command-line counts.
#[must_use]
pub fn classify_unbounded_result(yes: &BigInt, eligible: &BigInt) -> &'static str {
    classify_finding(yes, eligible)
}
/// Classify an OOS item according to its distinct two-voter policy.
#[must_use]
pub const fn classify_oos_result(yes: usize, eligible: usize) -> &'static str {
    if eligible == 0 {
        return "rejected";
    }
    let accepted = if eligible == 1 {
        yes == 1
    } else if eligible == 2 {
        yes >= 1
    } else {
        yes >= 2
    };
    if accepted {
        "accepted"
    } else if yes > 0 {
        "neutral"
    } else {
        "rejected"
    }
}
fn strict_majority_yes_major(votes: &[String], severities: &[String]) -> bool {
    let mut yes = 0_usize;
    let mut major = 0_usize;
    for (index, vote) in votes.iter().enumerate() {
        if vote.trim().eq_ignore_ascii_case("YES") {
            yes += 1;
            if severities
                .get(index)
                .is_some_and(|severity| severity.trim().eq_ignore_ascii_case("major"))
            {
                major += 1;
            }
        }
    }
    yes > 0 && major * 2 > yes
}
/// Whether an accepted OOS item has a strict majority of major YES votes.
#[must_use]
pub fn oos_fileable_from_votes(result: &str, votes: &[String], severities: &[String]) -> bool {
    result == "accepted" && strict_majority_yes_major(votes, severities)
}
/// Whether a neutral item reroutes to OOS due to major YES evidence.
#[must_use]
pub fn neutral_high_severity_rescue_to_oos(
    result: &str,
    votes: &[String],
    severities: &[String],
) -> bool {
    result == "neutral" && strict_majority_yes_major(votes, severities)
}
/// Return the accepted finding weight, counting only YES-vote severities.
#[must_use]
pub fn accepted_finding_points_from_severities(votes: &[String], severities: &[String]) -> u8 {
    if strict_majority_yes_major(votes, severities) {
        2
    } else {
        1
    }
}

/// Return the accepted finding weight from the standard classification fields.
///
/// Both code-review and plan-review consumers store the three voter columns
/// under the same names, so this keeps their field lookup and weighting rule
/// in one owner.
#[must_use]
pub fn accepted_finding_points_from_classification_fields(
    value: impl Fn(&str) -> Option<String>,
) -> u8 {
    let votes = ["v1_vote", "v2_vote", "v3_vote"].map(|field| value(field).unwrap_or_default());
    let severities =
        ["v1_severity", "v2_severity", "v3_severity"].map(|field| value(field).unwrap_or_default());
    accepted_finding_points_from_severities(&votes, &severities)
}

fn reviewer_tokens(cell: &str, labels: &[String]) -> Vec<String> {
    let label_set: HashSet<&str> = labels
        .iter()
        .filter(|label| !label.is_empty())
        .map(String::as_str)
        .collect();
    let mut sorted: Vec<&str> = label_set.iter().copied().collect();
    sorted.sort_by(|left, right| {
        right
            .chars()
            .count()
            .cmp(&left.chars().count())
            .then_with(|| left.cmp(right))
    });
    let mut tokens = Vec::new();
    let mut seen = HashSet::new();
    for raw_segment in cell.split(',') {
        let segment = trim_python_whitespace(raw_segment);
        if segment.is_empty() {
            continue;
        }
        if label_set.contains(segment) {
            if seen.insert(segment.to_owned()) {
                tokens.push(segment.to_owned());
            }
            continue;
        }
        let mut position = 0;
        while position < segment.len() {
            let Some(character) = segment[position..].chars().next() else {
                break;
            };
            if is_python_whitespace(character) {
                position += character.len_utf8();
                continue;
            }
            let Some(label) = sorted.iter().find(|label| {
                if !segment[position..].starts_with(**label) {
                    return false;
                }
                let end = position + label.len();
                end == segment.len()
                    || segment[end..]
                        .chars()
                        .next()
                        .is_some_and(is_python_whitespace)
            }) else {
                break;
            };
            if seen.insert((*label).to_owned()) {
                tokens.push((*label).to_owned());
            }
            position += label.len();
        }
    }
    tokens
}

fn reviewer_segment_fully_tokenized(segment: &str, labels: &[String]) -> bool {
    if labels.iter().all(String::is_empty) {
        return false;
    }
    let mut sorted: Vec<&str> = labels
        .iter()
        .filter(|label| !label.is_empty())
        .map(String::as_str)
        .collect();
    sorted.sort_by(|left, right| {
        right
            .chars()
            .count()
            .cmp(&left.chars().count())
            .then_with(|| left.cmp(right))
    });
    let mut position = 0;
    while position < segment.len() {
        let Some(character) = segment[position..].chars().next() else {
            break;
        };
        if is_python_whitespace(character) {
            position += character.len_utf8();
            continue;
        }
        let Some(label) = sorted.iter().find(|label| {
            if !segment[position..].starts_with(**label) {
                return false;
            }
            let end = position + label.len();
            end == segment.len()
                || segment[end..]
                    .chars()
                    .next()
                    .is_some_and(is_python_whitespace)
        }) else {
            return false;
        };
        position += label.len();
    }
    true
}

fn grow_reviewer_labels(labels: &mut Vec<String>, cells: impl IntoIterator<Item = String>) {
    let mut seen: HashSet<String> = labels.iter().cloned().collect();
    for cell in cells {
        for raw_segment in cell.split(',') {
            let segment = trim_python_whitespace(raw_segment);
            if segment.is_empty() {
                continue;
            }
            let matched = reviewer_tokens(segment, labels);
            if matched.is_empty() && !segment.contains(' ') && !segment.contains('\t') {
                if seen.insert(segment.to_owned()) {
                    labels.push(segment.to_owned());
                }
            } else {
                for token in matched {
                    if seen.insert(token.clone()) {
                        labels.push(token);
                    }
                }
            }
        }
    }
}

/// Split one classification reviewer cell using the legacy column-specific grammar.
#[must_use]
#[rustfmt::skip]
pub fn split_classification_attribution(cell: &str, column: &str, labels: &[String]) -> Vec<String> {
    let cell = trim_python_whitespace(cell);
    if cell.is_empty() {
        return Vec::new();
    }
    if column == "finding_reviewers" {
        reviewer_tokens(cell, labels)
    } else if column == "reviewer_slots" {
        cell.split('|')
            .map(trim_python_whitespace)
            .filter(|part| !part.is_empty())
            .map(str::to_owned)
            .collect()
    } else {
        vec![cell.to_owned()]
    }
}

/// Return the raw sole-finder attribution used to decide unique-bonus eligibility.
#[must_use]
pub fn raw_sole_finder_attribution(
    cell: &str,
    column: &str,
    corpus_labels: &[String],
) -> Vec<String> {
    let cell = trim_python_whitespace(cell);
    if cell.is_empty() {
        return Vec::new();
    }
    if column != "finding_reviewers" {
        return split_classification_attribution(cell, column, &[]);
    }
    let comma_parts: Vec<&str> = cell
        .split(',')
        .map(trim_python_whitespace)
        .filter(|part| !part.is_empty())
        .collect();
    if comma_parts.len() != 1 {
        return Vec::new();
    }
    let segment = comma_parts[0];
    let tokens = reviewer_tokens(segment, corpus_labels);
    if tokens.is_empty() {
        return vec![segment.to_owned()];
    }
    if reviewer_segment_fully_tokenized(segment, corpus_labels) {
        tokens
    } else {
        Vec::new()
    }
}

fn row_is_oos(row: &BTreeMap<String, String>, has_scope: bool) -> bool {
    if has_scope {
        row.get("scope")
            .is_some_and(|scope| trim_python_whitespace(scope).eq_ignore_ascii_case("oos"))
    } else {
        row.get("finding_id")
            .is_some_and(|item| trim_python_whitespace(item).starts_with("OOS_"))
    }
}

/// Replay reviewer scores from one plan- or code-review classification TSV.
///
/// # Errors
///
/// Returns a CSV error when the tab-delimited input is malformed.
pub fn scoreboard_scores_from_tsv(
    text: &str,
    reviewer_labels: &[String],
    unique_finder_bonus: f64,
) -> Result<BTreeMap<String, f64>, csv::Error> {
    let mut scores: BTreeMap<String, f64> = reviewer_labels
        .iter()
        .cloned()
        .map(|label| (label, 0.0))
        .collect();
    let mut reader = csv::ReaderBuilder::new()
        .delimiter(b'\t')
        .flexible(true)
        .from_reader(text.as_bytes());
    let headers: Vec<String> = reader.headers()?.iter().map(str::to_owned).collect();
    let mut rows = Vec::new();
    for record in reader.records() {
        let record = record?;
        let mut row = BTreeMap::new();
        for (index, header) in headers.iter().enumerate() {
            row.insert(header.clone(), record.get(index).unwrap_or("").to_owned());
        }
        rows.push(row);
    }
    let reviewer_column = if headers.iter().any(|header| header == "finding_reviewers") {
        "finding_reviewers"
    } else {
        "reviewer_slots"
    };
    let mut corpus_labels = reviewer_labels.to_vec();
    if reviewer_column == "finding_reviewers" {
        grow_reviewer_labels(
            &mut corpus_labels,
            rows.iter()
                .map(|row| row.get(reviewer_column).cloned().unwrap_or_default()),
        );
    }
    let has_scope = headers.iter().any(|header| header == "scope");
    for row in rows {
        let result = trim_python_whitespace(row.get("voting_result").map_or("", String::as_str));
        if !matches!(result, "accepted" | "rejected" | "neutral") {
            continue;
        }
        let reviewer_cell = row.get(reviewer_column).map_or("", String::as_str);
        let reviewers =
            split_classification_attribution(reviewer_cell, reviewer_column, reviewer_labels);
        let raw_reviewers =
            raw_sole_finder_attribution(reviewer_cell, reviewer_column, &corpus_labels);
        let oos = row_is_oos(&row, has_scope);
        let delta = if result == "accepted" {
            let accepted_oos = row
                .get("scope")
                .is_some_and(|scope| trim_python_whitespace(scope) == "oos");
            let base = if !has_scope || accepted_oos {
                1.0
            } else {
                f64::from(accepted_finding_points_from_classification_fields(
                    |field| row.get(field).cloned(),
                ))
            };
            if unique_finder_bonus > 0.0 && !oos && raw_reviewers.len() == 1 {
                base + unique_finder_bonus
            } else {
                base
            }
        } else if result == "rejected" {
            -1.0
        } else if oos {
            0.0
        } else {
            -0.25
        };
        for reviewer in reviewers {
            if let Some(score) = scores.get_mut(&reviewer) {
                *score += delta;
            }
        }
    }
    Ok(scores)
}

/// Values needed to compose one byte-stable run-log tally record.
pub struct TallyRecordFields<'a> {
    pub phase: &'a str,
    pub batch: &'a str,
    pub mode: &'a str,
    pub rounds: &'a str,
    pub accepted: &'a str,
    pub rejected: &'a str,
    pub exonerated: &'a str,
    pub body: Option<&'a str>,
}

/// Compose the byte-stable run-log tally record.
#[must_use]
pub fn compose_tally_record_json(fields: &TallyRecordFields<'_>) -> String {
    let mut record = format!(
        "{{\"schema_version\":2,\"phase\":{},\"batch\":{},\"mode\":{},\"rounds\":{},\"accepted_count\":{},\"rejected_count\":{},\"exonerated_count\":{}",
        serde_json::Value::String(fields.phase.to_owned()),
        serde_json::Value::String(fields.batch.to_owned()),
        serde_json::Value::String(fields.mode.to_owned()),
        fields.rounds,
        fields.accepted,
        fields.rejected,
        fields.exonerated,
    );
    if let Some(body) = fields.body {
        record.push_str(",\"body\":");
        record.push_str(&serde_json::Value::String(body.to_owned()).to_string());
    }
    record.push('}');
    ensure_ascii_json(&record)
}

/// Compose the exact self-review findings JSONL paired with a tally record.
#[must_use]
pub fn compose_self_review_findings_jsonl(accepted: usize, rejected: usize) -> String {
    let mut output = String::new();
    for (outcome, count, prefix) in [
        ("accepted", accepted, "SELF_REVIEW_ACCEPTED"),
        ("rejected", rejected, "SELF_REVIEW_REJECTED"),
    ] {
        for index in 1..=count {
            let _ = writeln!(
                output,
                "{{\"id\":\"{prefix}_{index}\",\"issue_number\":\"0\",\"phase\":\"code-review\",\"outcome\":\"{outcome}\",\"schema_version\":\"2\",\"reviewer_slots\":[\"self-review\"],\"round_num\":\"1\",\"category\":\"\",\"body_severity\":\"\",\"focus_area\":\"\",\"prose_body\":\"\"}}"
            );
        }
    }
    output
}

/// Expand a self-review tally document into its exact findings JSONL records.
#[must_use]
pub fn compose_self_review_findings_from_tally_json(text: &str) -> String {
    let Ok(serde_json::Value::Object(record)) = serde_json::from_str(text) else {
        return String::new();
    };
    if record.get("mode").and_then(serde_json::Value::as_str) != Some("self-review") {
        return String::new();
    }
    let count = |name: &str| -> usize {
        let raw = match record.get(name) {
            Some(serde_json::Value::String(value)) => value.clone(),
            Some(serde_json::Value::Number(value)) => value.to_string(),
            _ => return 0,
        };
        python_bigint(&raw)
            .filter(|value| value.sign() != num_bigint::Sign::Minus)
            .and_then(|value| usize::try_from(value).ok())
            .unwrap_or(0)
    };
    compose_self_review_findings_jsonl(count("accepted_count"), count("rejected_count"))
}
