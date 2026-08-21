//! Effect-free state transitions for `/design` OOS preparation and annotation.

use std::collections::{BTreeMap, BTreeSet, HashSet};
use std::sync::LazyLock;

use regex::Regex;

use crate::{
    BlockBoundary, OosItemKind, is_high_risk_oos_block, is_security_block_text,
    issue::combined_oos_blocks, next_oos_number, parse_oos_blocks,
};

static FILED_URL_LINE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^\s*-\s*\*\*Filed[ \t]*URL\*\*[ \t]*:").expect("filed URL line")
});
static FILED_URL_VALUE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^[ \t]*-[ \t]+\*\*Filed[ \t]*URL\*\*:[^\n]*(?:\n|$)").expect("filed URL value")
});
static VOTE_ACCEPTED_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?mi)^Vote tally:.*\bResult=accepted\b").expect("accepted vote"));
static VOTE_FILEABLE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?mi)^Vote tally:.*\bFileable=true\b").expect("fileable vote"));
static ITEM_HEADING_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^###\s+(?:OOS|FINDING)_\d+:").expect("item heading"));
static VOTE_TALLY_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?m)^Vote tally:.*(?:\n|$)").expect("vote tally"));
static WHITESPACE_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\s+").expect("whitespace"));
static ISSUE_URL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^https://github\.com/[^/\s]+/[^/\s]+/issues/\d+$").expect("issue URL")
});
static ISSUE_URL_KV_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^ISSUE_(?:(\d+)_)?(URL|DUPLICATE_OF_URL)=(.*)$").expect("issue URL row")
});
static ISSUE_FAILED_KV_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^ISSUE_(\d+)_FAILED=true$").expect("issue failure row"));

/// Parsed outcome rows emitted by `/issue`.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct DesignOosIssueOutput {
    pub urls: BTreeMap<usize, String>,
    pub duplicates: BTreeMap<usize, String>,
    pub failed: BTreeSet<usize>,
    pub issues_failed: usize,
}

/// The accepted document after annotation and its durable OOS-to-URL rows.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct DesignOosAnnotation {
    pub accepted: String,
    pub map_lines: Vec<String>,
}

/// Keep only unfiled OOS blocks, preserving their source numbering and text.
#[must_use]
pub fn design_oos_unfiled(text: &str) -> String {
    let blocks = parse_oos_blocks(text, BlockBoundary::OosHeading)
        .into_iter()
        .filter(|block| block.kind == OosItemKind::Oos && !FILED_URL_LINE_RE.is_match(&block.block))
        .map(|block| block.block.trim_end_matches('\n').to_owned())
        .collect::<Vec<_>>();
    if blocks.is_empty() {
        String::new()
    } else {
        format!("{}\n", blocks.join("\n\n"))
    }
}

fn aggregate_blocks(text: &str) -> Vec<String> {
    let normalized = text.replace("\r\n", "\n").replace('\r', "\n");
    parse_oos_blocks(&normalized, BlockBoundary::ItemHeading)
        .into_iter()
        .map(|block| format!("{}\n", block.block.trim_matches('\n')))
        .collect()
}

fn block_identity(block: &str) -> String {
    let body = FILED_URL_VALUE_RE.replace_all(block, "");
    let body = VOTE_TALLY_RE.replace_all(&body, "");
    let body = ITEM_HEADING_RE.replacen(body.trim(), 1, "### ITEM:");
    WHITESPACE_RE.replace_all(body.trim(), " ").to_lowercase()
}

/// Return the identity prefix used to validate a cross-session cache.
#[must_use]
pub fn design_oos_identity_signature(text: &str) -> Vec<String> {
    aggregate_blocks(text)
        .iter()
        .map(|block| block_identity(block))
        .filter(|identity| !identity.is_empty())
        .collect()
}

/// Promote accepted, fileable, non-security aggregate-pool items once.
#[must_use]
pub fn design_oos_promote_pool(accepted: &str, pool: &str) -> String {
    let mut output = accepted.to_owned();
    let mut seen = aggregate_blocks(accepted)
        .iter()
        .map(|block| block_identity(block))
        .collect::<HashSet<_>>();
    let mut number = next_oos_number(accepted);
    for block in aggregate_blocks(pool) {
        if is_security_block_text(&block)
            || !VOTE_ACCEPTED_RE.is_match(&block)
            || !VOTE_FILEABLE_RE.is_match(&block)
        {
            continue;
        }
        let identity = block_identity(&block);
        if identity.is_empty() || !seen.insert(identity) {
            continue;
        }
        let replacement = format!("### OOS_{number}:");
        let promoted = ITEM_HEADING_RE.replacen(&block, 1, replacement.as_str());
        if !output.is_empty() && !output.ends_with('\n') {
            output.push('\n');
        }
        output.push_str(promoted.trim_end_matches('\n'));
        output.push('\n');
        number = number.saturating_add(1);
    }
    output
}

fn block_range(text: &str, number: &str) -> Option<(usize, usize)> {
    let item_id = format!("OOS_{number}");
    parse_oos_blocks(text, BlockBoundary::ItemHeading)
        .into_iter()
        .find(|block| block.kind == OosItemKind::Oos && block.item_id == item_id)
        .map(|block| (block.start, block.end))
}

fn add_filed_url(text: &str, number: &str, url: &str) -> Option<(String, bool)> {
    let (start, end) = block_range(text, number)?;
    let block = &text[start..end];
    if FILED_URL_LINE_RE.is_match(block) {
        return Some((text.to_owned(), false));
    }
    let replacement = format!("{}\n- **Filed URL**: {url}\n", block.trim_end_matches('\n'));
    Some((
        format!("{}{}{}", &text[..start], replacement, &text[end..]),
        true,
    ))
}

/// Restore accepted-file annotations from a durable sentinel.
#[must_use]
pub fn design_oos_recover_accepted(accepted: &str, sentinel: &str) -> Option<String> {
    let mut maps = Vec::new();
    let mut plain = Vec::new();
    for line in sentinel.lines() {
        if let Some(rest) = line.strip_prefix("OOS_FILE_MAP\t") {
            let mut fields = rest.splitn(2, '\t');
            let number = fields.next().unwrap_or_default().trim();
            let url = fields.next().unwrap_or_default().trim();
            if !number.is_empty() && !url.is_empty() {
                maps.push((number, url));
            }
        } else if line.trim().starts_with("http") {
            plain.push(line.trim());
        }
    }
    let mut output = accepted.to_owned();
    if !maps.is_empty() {
        for (number, url) in maps {
            output = add_filed_url(&output, number, url)?.0;
        }
        return Some(output);
    }
    if plain.is_empty() {
        return Some(output);
    }
    let unfiled = parse_oos_blocks(accepted, BlockBoundary::ItemHeading)
        .iter()
        .filter(|block| block.kind == OosItemKind::Oos && !FILED_URL_LINE_RE.is_match(&block.block))
        .count();
    if plain.len() > 1 || unfiled > 1 {
        return None;
    }
    let number = parse_oos_blocks(accepted, BlockBoundary::ItemHeading)
        .into_iter()
        .find(|block| block.kind == OosItemKind::Oos && !FILED_URL_LINE_RE.is_match(&block.block))
        .and_then(|block| block.item_id.strip_prefix("OOS_").map(str::to_owned));
    match (plain.first(), number) {
        (Some(url), Some(number)) => add_filed_url(&output, &number, url).map(|value| value.0),
        _ => Some(output),
    }
}

/// Parse URL, duplicate, and failure rows emitted by `/issue`.
#[must_use]
pub fn parse_design_oos_issue_output(text: &str) -> DesignOosIssueOutput {
    let mut output = DesignOosIssueOutput::default();
    for line in text.lines() {
        if let Some(value) = line.strip_prefix("ISSUES_FAILED=") {
            output.issues_failed = value.trim().parse().unwrap_or(0);
        }
        if let Some(captures) = ISSUE_URL_KV_RE.captures(line) {
            let index = captures.get(1).map_or("1", |value| value.as_str());
            let Ok(index) = index.parse::<usize>() else {
                continue;
            };
            let value = captures[3].trim();
            if value.is_empty() {
                continue;
            }
            if &captures[2] == "URL" {
                output.urls.insert(index, value.to_owned());
            } else {
                output.duplicates.insert(index, value.to_owned());
            }
        } else if let Some(captures) = ISSUE_FAILED_KV_RE.captures(line)
            && let Ok(index) = captures[1].parse()
        {
            output.failed.insert(index);
        }
    }
    output
}

/// Add successful filed URLs to accepted blocks and render durable map rows.
#[must_use]
pub fn design_oos_annotate(
    order: &[String],
    accepted: &str,
    combined: &str,
    issue_output: &DesignOosIssueOutput,
) -> DesignOosAnnotation {
    let successes = issue_output
        .urls
        .iter()
        .chain(&issue_output.duplicates)
        .filter(|(_index, url)| !url.is_empty())
        .collect::<Vec<_>>();
    let rollup =
        (order.len() > 1 && combined_oos_blocks(combined).len() == 1 && successes.len() == 1)
            .then(|| successes[0])
            .filter(|(index, _url)| **index == 1)
            .map_or("", |(_index, url)| url.as_str());
    let mut output = accepted.to_owned();
    let mut map_lines = Vec::new();
    for (offset, number) in order.iter().enumerate() {
        let index = offset + 1;
        if issue_output.failed.contains(&index) {
            continue;
        }
        let url = if rollup.is_empty() {
            issue_output
                .urls
                .get(&index)
                .or_else(|| issue_output.duplicates.get(&index))
                .map_or("", String::as_str)
        } else {
            rollup
        };
        if url.is_empty() {
            continue;
        }
        let Some((updated, inserted)) = add_filed_url(&output, number, url) else {
            continue;
        };
        output = updated;
        if inserted || !rollup.is_empty() {
            map_lines.push(format!("OOS_FILE_MAP\t{number}\t{url}"));
        }
    }
    DesignOosAnnotation {
        accepted: output,
        map_lines,
    }
}

fn push_mapping(rows: &mut Vec<(String, bool)>, url: &str, priority: bool) {
    if let Some((_url, value)) = rows.iter_mut().find(|(existing, _)| existing == url) {
        *value = priority;
    } else {
        rows.push((url.to_owned(), priority));
    }
}

fn sentinel_maps(text: &str) -> Vec<(String, String)> {
    text.lines()
        .filter_map(|line| line.strip_prefix("OOS_FILE_MAP\t"))
        .filter_map(|rest| rest.split_once('\t'))
        .map(|(number, url)| (number.trim().to_owned(), url.trim().to_owned()))
        .filter(|(number, url)| !number.is_empty() && !url.is_empty())
        .collect()
}

fn sentinel_urls(text: &str) -> Vec<String> {
    let mut urls = Vec::new();
    for line in text.lines() {
        let url = line
            .strip_prefix("OOS_FILE_MAP\t")
            .and_then(|rest| rest.split_once('\t'))
            .map_or_else(|| line.trim(), |(_number, url)| url.trim());
        if ISSUE_URL_RE.is_match(url) && !urls.iter().any(|seen| seen == url) {
            urls.push(url.to_owned());
        }
    }
    urls
}

/// Report whether a sentinel contains at least one validated GitHub issue URL.
#[must_use]
pub fn design_oos_has_filed_urls(sentinel: &str) -> bool {
    !sentinel_urls(sentinel).is_empty()
}

/// Map each filed URL to the high-risk verdict of its post-cap slot.
#[must_use]
pub fn design_oos_priority_map(
    sentinel: &str,
    combined: &str,
    order: Option<&[String]>,
    issue_stdout: Option<&str>,
) -> Vec<(String, bool)> {
    let blocks = combined_oos_blocks(combined);
    if blocks.is_empty() {
        return Vec::new();
    }
    let priority = blocks
        .iter()
        .map(|block| is_high_risk_oos_block(block))
        .collect::<Vec<_>>();
    let sentinel_urls = sentinel_urls(sentinel);
    if sentinel_urls.is_empty() {
        return Vec::new();
    }
    let verdict = |index: usize| {
        if blocks.len() == 1 {
            priority.iter().any(|value| *value)
        } else {
            priority
                .get(index.saturating_sub(1))
                .copied()
                .unwrap_or(false)
        }
    };
    if let Some(stdout) = issue_stdout {
        let parsed = parse_design_oos_issue_output(stdout);
        let mut rows = Vec::new();
        let slot_count = blocks.len().max(order.map_or(0, <[String]>::len)).max(
            parsed
                .urls
                .keys()
                .chain(parsed.duplicates.keys())
                .chain(&parsed.failed)
                .copied()
                .max()
                .unwrap_or(0),
        );
        for index in 1..=slot_count {
            if parsed.failed.contains(&index) {
                continue;
            }
            if let Some(url) = parsed
                .urls
                .get(&index)
                .or_else(|| parsed.duplicates.get(&index))
            {
                push_mapping(&mut rows, url, verdict(index));
            }
        }
        if !rows.is_empty() {
            return rows;
        }
    }
    let maps = sentinel_maps(sentinel);
    let mut rows = Vec::new();
    if let Some(order) = order {
        for (index, number) in order.iter().enumerate() {
            if let Some((_number, url)) = maps.iter().rev().find(|(mapped, _url)| mapped == number)
            {
                push_mapping(&mut rows, url, verdict(index + 1));
            }
        }
    } else {
        for (number, url) in &maps {
            if let Ok(index) = number.parse() {
                push_mapping(&mut rows, url, verdict(index));
            }
        }
    }
    if !rows.is_empty() {
        return rows;
    }
    if blocks.len() == 1 {
        return sentinel_urls
            .into_iter()
            .map(|url| (url, verdict(1)))
            .collect();
    }
    if sentinel_urls.len() != blocks.len() {
        return Vec::new();
    }
    sentinel_urls
        .into_iter()
        .enumerate()
        .map(|(index, url)| (url, verdict(index + 1)))
        .collect()
}

/// Report whether the composed batch contains any high-risk item.
#[must_use]
pub fn design_oos_has_priority(combined: &str) -> bool {
    combined_oos_blocks(combined)
        .iter()
        .any(|block| is_high_risk_oos_block(block))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unfiled_extraction_and_recovery_preserve_intervening_findings() {
        let accepted = concat!(
            "### OOS_1: one\nbody\n",
            "### FINDING_2: middle\nfinding\n",
            "### OOS_3: three\n- **Filed URL**: https://github.com/o/r/issues/3\n",
        );
        assert_eq!(
            design_oos_unfiled(accepted),
            "### OOS_1: one\nbody\n### FINDING_2: middle\nfinding\n"
        );
        let recovered = design_oos_recover_accepted(
            accepted,
            "OOS_FILE_MAP\t1\thttps://github.com/o/r/issues/1\n",
        )
        .expect("mapping recovers");
        assert!(recovered.contains("### FINDING_2: middle\nfinding\n"));
        assert!(recovered.contains("Filed URL**: https://github.com/o/r/issues/1"));
        let ambiguous = accepted.replace(
            "- **Filed URL**: https://github.com/o/r/issues/3\n",
            "unfiled\n",
        );
        assert!(
            design_oos_recover_accepted(&ambiguous, "https://github.com/o/r/issues/1\n").is_none()
        );
    }

    #[test]
    fn priority_mapping_uses_slot_gaps_and_rollup_semantics() {
        let sentinel = concat!(
            "OOS_FILE_MAP\t1\thttps://github.com/o/r/issues/101\n",
            "OOS_FILE_MAP\t3\thttps://github.com/o/r/issues/103\n",
        );
        let combined = concat!(
            "### OOS_1: one\n- **Focus area**: correctness\n\n",
            "### OOS_2: two\n- **Focus area**: risk\n\n",
            "### OOS_3: three\n- **Focus area**: regression\n",
        );
        let stdout = concat!(
            "ISSUE_1_URL=https://github.com/o/r/issues/101\n",
            "ISSUE_2_FAILED=true\n",
            "ISSUE_3_URL=https://github.com/o/r/issues/103\n",
        );
        assert_eq!(
            design_oos_priority_map(sentinel, combined, None, Some(stdout)),
            vec![
                ("https://github.com/o/r/issues/101".into(), true),
                ("https://github.com/o/r/issues/103".into(), true),
            ]
        );
        assert!(design_oos_has_filed_urls(sentinel));
        assert!(!design_oos_has_filed_urls("OOS_FILE_MAP\t1\tnot-a-url\n"));
    }

    #[test]
    fn prepared_rollup_reparses_through_the_issue_contract() {
        let pool = concat!(
            "### FINDING_1: one\n- **Concern**: first\nVote tally: Result=accepted Fileable=true\n\n",
            "### FINDING_2: two\n- **Description**: second\nVote tally: Result=accepted Fileable=true\n",
        );
        let prepared = design_oos_unfiled(&design_oos_promote_pool("", pool));
        let capped = crate::apply_issue_cap(&prepared, 1)
            .expect("valid OOS batch")
            .expect("two items roll up at cap one");
        let parsed = crate::parse_issue_input(&capped);
        assert_eq!(parsed.mode, crate::InputMode::Oos);
        assert_eq!(parsed.items.len(), 1);
        assert!(parsed.items.iter().all(|item| !item.malformed));

        let output = parse_design_oos_issue_output(
            "ISSUE_URL=https://github.com/o/r/issues/9\nISSUES_FAILED=1\n",
        );
        let annotated = design_oos_annotate(&["1".into(), "2".into()], &prepared, &capped, &output);
        assert_eq!(annotated.accepted.matches("issues/9").count(), 2);
        assert_eq!(annotated.map_lines.len(), 2);
    }

    #[test]
    fn promotion_filters_ineligible_and_duplicate_pool_entries() {
        let accepted = "### OOS_4: existing\n- **Description**: same body";
        let pool = concat!(
            "### FINDING_1: existing\n- **Description**: same body\nVote tally: Result=accepted Fileable=true\n\n",
            "### FINDING_2: rejected\n- **Description**: no\nVote tally: Result=rejected Fileable=true\n\n",
            "### FINDING_3: private\n- **Focus area**: security-hardening\nVote tally: Result=accepted Fileable=true\n\n",
            "### FINDING_4: not fileable\n- **Description**: no\nVote tally: Result=accepted Fileable=false\n\n",
            "### FINDING_5: promoted\n- **Concern**: unique\nVote tally: Result=accepted Fileable=true\n",
        );
        let promoted = design_oos_promote_pool(accepted, pool);
        assert!(promoted.contains("### OOS_5: promoted"), "{promoted}");
        assert_eq!(promoted.matches("same body").count(), 1);
        assert!(!promoted.contains("rejected"));
        assert!(!promoted.contains("private"));
        assert!(!promoted.contains("not fileable"));
        assert_eq!(design_oos_identity_signature(&promoted).len(), 2);
        assert_eq!(
            design_oos_unfiled(
                "### OOS_1: filed\n- **Filed URL**: https://github.com/o/r/issues/1\n"
            ),
            ""
        );
    }

    #[test]
    fn recovery_and_issue_output_cover_legacy_and_partial_shapes() {
        let accepted = "### OOS_8: one\nbody\n";
        assert_eq!(
            design_oos_recover_accepted(accepted, ""),
            Some(accepted.to_owned())
        );
        let recovered = design_oos_recover_accepted(accepted, "https://github.com/o/r/issues/8\n")
            .expect("one legacy URL is unambiguous");
        assert!(recovered.contains("Filed URL**: https://github.com/o/r/issues/8"));
        assert_eq!(
            design_oos_recover_accepted(
                &recovered,
                "OOS_FILE_MAP\t8\thttps://github.com/o/r/issues/8\n",
            ),
            Some(recovered.clone())
        );
        assert!(
            design_oos_recover_accepted(
                accepted,
                "OOS_FILE_MAP\t99\thttps://github.com/o/r/issues/99\n",
            )
            .is_none()
        );

        let output = parse_design_oos_issue_output(concat!(
            "ISSUE_URL=\n",
            "ISSUE_2_DUPLICATE_OF_URL=https://github.com/o/r/issues/2\n",
            "ISSUE_3_FAILED=true\n",
            "ISSUES_FAILED=not-a-number\n",
            "ISSUE_999999999999999999999999_URL=https://github.com/o/r/issues/9\n",
        ));
        assert!(output.urls.is_empty());
        assert_eq!(
            output.duplicates.get(&2).map(String::as_str),
            Some("https://github.com/o/r/issues/2")
        );
        assert_eq!(output.failed, BTreeSet::from([3]));
        assert_eq!(output.issues_failed, 0);

        let annotated = design_oos_annotate(
            &["8".into(), "missing".into(), "failed".into()],
            accepted,
            accepted,
            &DesignOosIssueOutput {
                urls: BTreeMap::from([
                    (1, "https://github.com/o/r/issues/8".into()),
                    (2, "https://github.com/o/r/issues/2".into()),
                    (3, "https://github.com/o/r/issues/3".into()),
                ]),
                failed: BTreeSet::from([3]),
                ..DesignOosIssueOutput::default()
            },
        );
        assert_eq!(annotated.map_lines.len(), 1);
        assert!(annotated.accepted.contains("issues/8"));
    }

    #[test]
    fn priority_mapping_falls_back_without_issue_stdout() {
        let two_blocks = concat!(
            "### OOS_1: docs\n- **Focus area**: documentation\n\n",
            "### OOS_2: regression\n- **Focus area**: regression\n",
        );
        let duplicate_stdout = concat!(
            "ISSUE_1_URL=https://github.com/o/r/issues/10\n",
            "ISSUE_2_DUPLICATE_OF_URL=https://github.com/o/r/issues/10\n",
        );
        assert_eq!(
            design_oos_priority_map(
                "https://github.com/o/r/issues/10\n",
                two_blocks,
                None,
                Some(duplicate_stdout),
            ),
            vec![("https://github.com/o/r/issues/10".into(), true)]
        );

        let mapped = concat!(
            "OOS_FILE_MAP\t7\thttps://github.com/o/r/issues/7\n",
            "OOS_FILE_MAP\t8\thttps://github.com/o/r/issues/8\n",
        );
        assert_eq!(
            design_oos_priority_map(
                mapped,
                two_blocks,
                Some(&["7".into(), "8".into()]),
                Some("unrecognized output\n"),
            ),
            vec![
                ("https://github.com/o/r/issues/7".into(), false),
                ("https://github.com/o/r/issues/8".into(), true),
            ]
        );
        let positional = concat!(
            "OOS_FILE_MAP\t1\thttps://github.com/o/r/issues/7\n",
            "OOS_FILE_MAP\t2\thttps://github.com/o/r/issues/8\n",
        );
        assert_eq!(
            design_oos_priority_map(positional, two_blocks, None, None),
            vec![
                ("https://github.com/o/r/issues/7".into(), false),
                ("https://github.com/o/r/issues/8".into(), true),
            ]
        );

        let single = "### OOS_1: correctness\n- **Focus area**: correctness\n";
        assert_eq!(
            design_oos_priority_map("https://github.com/o/r/issues/1\n", single, None, None,),
            vec![("https://github.com/o/r/issues/1".into(), true)]
        );
        assert!(design_oos_priority_map("", single, None, None).is_empty());
        assert!(
            design_oos_priority_map("https://github.com/o/r/issues/1\n", "", None, None,)
                .is_empty()
        );
        assert!(
            design_oos_priority_map("https://github.com/o/r/issues/1\n", two_blocks, None, None,)
                .is_empty()
        );
        assert_eq!(
            design_oos_priority_map(
                concat!(
                    "https://github.com/o/r/issues/1\n",
                    "https://github.com/o/r/issues/2\n",
                ),
                two_blocks,
                None,
                None,
            ),
            vec![
                ("https://github.com/o/r/issues/1".into(), false),
                ("https://github.com/o/r/issues/2".into(), true),
            ]
        );
    }
}
