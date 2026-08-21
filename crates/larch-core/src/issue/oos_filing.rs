//! Composition for the post-ship accepted-OOS filer.
//!
//! `oos file` turns the run's accepted-OOS artifacts into public issues. Every
//! decision it makes about *what* to file — which blocks are still pending,
//! which already carry a filed URL, which stable identity a filed issue binds
//! to, and what the sentinel and run-log records say afterwards — is decided
//! here, against text, so the driver in `larch-cli` is left with the effects.
//!
//! Identity is the load-bearing part. A run that is interrupted mid-batch must
//! resume without refiling, and the only durable link between an accepted block
//! and the issue it became is its stable id: the block's own `OOS_<n>` heading
//! scoped by the artifact it came from, or a digest of its normalized text when
//! it has no canonical heading. Combining and capping can fold several source
//! blocks into one filed issue, so a filed issue records every source id it
//! absorbed rather than only the first.
//!
//! Ports the composition half of Python `larch.issue.oos_filer`.

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};

use regex::Regex;
use sha2::{Digest as _, Sha256};
use std::sync::LazyLock;

use super::oos_batch::{normalize_title, sanitize_public_text};
use super::oos_priority::is_high_risk_oos_block;
use super::oos_record::{
    BlockBoundary, OosItemKind, is_security_block_text, parse_canonical_heading, parse_oos_blocks,
};
use crate::text::ensure_ascii_json;

/// The artifact stem the legacy unscoped stable ids were minted from.
pub const LEGACY_PRIMARY_OOS_SOURCE: &str = "oos-accepted-main-agent";
/// Footer a body part carries when the remainder continues in a later issue.
const BODY_PART_FOOTER: &str = "\n\n*[Continued in a follow-up issue.]*";
/// Header every continuation body part opens with.
const BODY_PART_HEADER: &str = "\n\n*[Continuation of a prior out-of-scope issue.]*\n\n";
/// Notice a summarized body ends with when its detail could not be published.
const SUMMARY_NOTICE: &str = "\n\n*[OOS detail exceeded the GitHub issue body limit; full detail remains in the run logs.]*\n";

static GITHUB_URL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"https://[^\s|)]+/issues/[0-9]+").expect("github issue url expression")
});
static FILED_URL_LINE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^[ \t]*-[ \t]+\*\*Filed[ \t]URL\*\*[ \t]*:[ \t]+(https://\S+/issues/[0-9]+)")
        .expect("filed url expression")
});
static STABLE_ID_LINE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^[ \t]*-[ \t]+\*\*Stable ID\*\*:[ \t]*(\S+)").expect("stable id expression")
});
static TITLE_LINE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^[ \t]*-[ \t]+\*\*Title\*\*:[ \t]*(.+)$").expect("title line expression")
});
static SENTINEL_ROW_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^\|[ \t]*(.*?)[ \t]*\|[ \t]*#[0-9]+[ \t]*\|[ \t]*(https://[^|]+/issues/[0-9]+)[ \t]*\|",
    )
    .expect("sentinel table expression")
});
static BARE_ITEM_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(?:[^:]+:)?((?:OOS|FINDING)_[0-9]+)$").expect("bare item expression")
});
static OOS_HEADING_PREFIX_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?m)^### OOS_[0-9]+:").expect("oos heading prefix expression"));

/// One accepted, still-unfiled OOS block from the run's input artifacts.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct AcceptedBlock {
    /// The block's heading title, as written.
    pub title: String,
    /// Every byte of the block, heading included.
    pub body: String,
    /// The block's durable identity across retries.
    pub stable_id: String,
    /// Whether the block needs the high-risk OOS label.
    pub priority: bool,
}

/// One issue this run either filed or found already filed.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct FiledIssue {
    /// The issue title, as filed.
    pub title: String,
    /// The issue URL, or a `skipped://` placeholder under a carve-out.
    pub url: String,
    /// Whether the URL was recovered rather than created by this pass.
    pub duplicate: bool,
    /// The primary stable id this issue binds to.
    pub stable_id: String,
    /// Every source stable id this issue absorbed, first one primary.
    pub source_stable_ids: Vec<String>,
    /// Whether the issue carries the high-risk OOS label.
    pub priority: bool,
}

impl FiledIssue {
    /// Build one recovered record, which is always a duplicate by definition.
    fn recovered(title: String, url: String, source_stable_ids: Vec<String>) -> Self {
        Self {
            title,
            url,
            duplicate: true,
            stable_id: source_stable_ids.first().cloned().unwrap_or_default(),
            source_stable_ids,
            priority: false,
        }
    }
}

/// Return the `OOS_<n>` suffix of a stable id, dropping any source scope.
#[must_use]
pub fn bare_oos_item_suffix(stable_id: &str) -> Option<String> {
    BARE_ITEM_RE
        .captures(stable_id)
        .map(|captures| captures[1].to_owned())
}

/// Split a stable id into its source scope, which is empty when unscoped.
fn stable_id_source(stable_id: &str) -> &str {
    stable_id.rsplit_once(':').map_or("", |(source, _)| source)
}

/// Mint the durable identity for one accepted block.
///
/// A canonical `### OOS_<n>:` heading is the identity when the block has one,
/// because it survives rewording. Only a block without one falls back to a
/// digest, which changes whenever the text does.
#[must_use]
pub fn stable_identifier(title: &str, body: &str, source_key: &str) -> String {
    let heading = body
        .lines()
        .filter_map(parse_canonical_heading)
        .find(|heading| heading.kind == OosItemKind::Oos);
    let bare = if let Some(heading) = heading {
        heading.item_id
    } else {
        let normalized = normalize_title(&format!("{title}\n{body}")).to_lowercase();
        let digest = Sha256::digest(normalized.as_bytes());
        format!("{digest:x}")[..16].to_owned()
    };
    if source_key.is_empty() {
        bare
    } else {
        format!("{source_key}:{bare}")
    }
}

/// Flatten one untrusted title the way match comparisons read it.
#[must_use]
pub fn normalized_title(text: &str) -> String {
    normalize_title(text).to_lowercase()
}

/// Report whether a filed issue is the one that owns `stable_id`.
///
/// The scopes deliberately bridge: a block minted before artifact scoping
/// existed carries a bare `OOS_<n>`, and the primary main-agent artifact is the
/// only source that may claim one, so a rerun does not refile it.
#[must_use]
pub fn issue_covers_stable_id(issue: &FiledIssue, stable_id: &str) -> bool {
    if stable_id.is_empty() {
        return false;
    }
    if issue.stable_id == stable_id || issue.source_stable_ids.iter().any(|id| id == stable_id) {
        return true;
    }
    let block_suffix = bare_oos_item_suffix(stable_id);
    if let Some(suffix) = block_suffix.as_deref()
        && issue.source_stable_ids.iter().any(|id| id == suffix)
    {
        let block_source = stable_id_source(stable_id);
        if block_source.is_empty() || block_source == LEGACY_PRIMARY_OOS_SOURCE {
            return true;
        }
    }
    let issue_suffix = bare_oos_item_suffix(&issue.stable_id);
    if issue_suffix.is_none() || issue_suffix != block_suffix {
        return false;
    }
    let issue_source = stable_id_source(&issue.stable_id);
    let block_source = stable_id_source(stable_id);
    match (issue_source.is_empty(), block_source.is_empty()) {
        (false, false) => issue_source == block_source,
        (true, false) => block_source == LEGACY_PRIMARY_OOS_SOURCE,
        (false, true) => issue_source == LEGACY_PRIMARY_OOS_SOURCE,
        (true, true) => true,
    }
}

/// Report whether a block's own text already records this filed URL.
fn block_has_filed_url(block: &AcceptedBlock, url: &str) -> bool {
    !url.is_empty() && block.body.contains(url)
}

/// One accepted-OOS input artifact: its stem and its text.
pub struct AcceptedSource<'a> {
    /// The file stem, which scopes every stable id minted from this artifact.
    pub source_key: &'a str,
    /// The artifact's full text.
    pub text: &'a str,
}

/// Split the run's accepted-OOS artifacts into pending blocks and filed URLs.
///
/// Security blocks never reach public filing. A block that already records a
/// `Filed URL` is reported as filed rather than pending, and its priority is
/// still carried onto whichever duplicate-titled block remains pending, so a
/// high-risk item does not lose its label by being restated.
#[must_use]
pub fn working_batch(sources: &[AcceptedSource<'_>]) -> (Vec<AcceptedBlock>, Vec<FiledIssue>) {
    let mut seen: HashMap<String, usize> = HashMap::new();
    let mut pending_priority: HashMap<String, bool> = HashMap::new();
    let mut blocks: Vec<AcceptedBlock> = Vec::new();
    let mut already: Vec<FiledIssue> = Vec::new();
    for source in sources {
        for item in parse_oos_blocks(source.text, BlockBoundary::ItemHeading) {
            if item.kind != OosItemKind::Oos {
                continue;
            }
            let body = item.block.trim_end().to_owned();
            if is_security_block_text(&body) {
                continue;
            }
            let normalized = normalized_title(&item.title);
            let stable_id = stable_identifier(&item.title, &body, source.source_key);
            let item_priority = is_high_risk_oos_block(&body);
            let filed: Vec<String> = FILED_URL_LINE_RE
                .captures_iter(&body)
                .map(|captures| captures[1].to_owned())
                .collect();
            if !filed.is_empty() {
                if let Some(&index) = seen.get(&normalized) {
                    blocks[index].priority |= item_priority;
                } else {
                    let entry = pending_priority.entry(normalized).or_insert(false);
                    *entry |= item_priority;
                }
                already.extend(filed.into_iter().map(|url| FiledIssue {
                    title: item.title.clone(),
                    url,
                    duplicate: true,
                    stable_id: stable_id.clone(),
                    source_stable_ids: Vec::new(),
                    priority: item_priority,
                }));
                continue;
            }
            if let Some(&index) = seen.get(&normalized) {
                blocks[index].priority |= item_priority;
                continue;
            }
            seen.insert(normalized.clone(), blocks.len());
            let priority = item_priority || pending_priority.remove(&normalized).unwrap_or(false);
            blocks.push(AcceptedBlock {
                title: item.title.clone(),
                body,
                stable_id,
                priority,
            });
        }
    }
    (blocks, already)
}

/// Render the pending batch as one renumbered document.
#[must_use]
pub fn render_blocks(blocks: &[AcceptedBlock]) -> String {
    let rendered: Vec<String> = blocks
        .iter()
        .enumerate()
        .map(|(index, block)| {
            let replacement = format!("### OOS_{}:", index + 1);
            OOS_HEADING_PREFIX_RE
                .replacen(&block.body, 1, regex::NoExpand(&replacement))
                .into_owned()
        })
        .collect();
    if rendered.is_empty() {
        return String::new();
    }
    let joined = rendered.join("\n\n");
    format!("{}\n", joined.trim_end())
}

/// Count the OOS blocks one composed document carries.
#[must_use]
pub fn combined_block_count(text: &str) -> usize {
    combined_oos_blocks(text).len()
}

/// Return the OOS blocks of one composed document, in order.
pub fn combined_oos_blocks(text: &str) -> Vec<String> {
    parse_oos_blocks(text, BlockBoundary::ItemHeading)
        .into_iter()
        .filter(|block| block.kind == OosItemKind::Oos)
        .map(|block| block.block)
        .collect()
}

/// Map each post-cap item position to the source stable ids it absorbed.
///
/// The tail matters: when combining or capping reduced the batch, the final
/// item aggregates every remaining source block, so it must carry all their
/// ids. Binding only the first would let a retry refile the rolled-up rest.
#[must_use]
pub fn stable_ids_by_combined_item(
    blocks: &[AcceptedBlock],
    combined_text: &str,
) -> BTreeMap<usize, Vec<String>> {
    let combined_count = combined_block_count(combined_text);
    let mut mapped: BTreeMap<usize, Vec<String>> = BTreeMap::new();
    if combined_count == 0 {
        return mapped;
    }
    if combined_count == blocks.len() {
        for (index, block) in blocks.iter().enumerate() {
            if !block.stable_id.is_empty() {
                mapped.insert(index + 1, vec![block.stable_id.clone()]);
            }
        }
        return mapped;
    }
    let source_ids: Vec<String> = blocks
        .iter()
        .filter(|block| !block.stable_id.is_empty())
        .map(|block| block.stable_id.clone())
        .collect();
    if combined_count == 1 && !source_ids.is_empty() {
        mapped.insert(1, source_ids);
        return mapped;
    }
    for index in 1..combined_count {
        if let Some(block) = blocks.get(index - 1)
            && !block.stable_id.is_empty()
        {
            mapped.insert(index, vec![block.stable_id.clone()]);
        }
    }
    let tail: Vec<String> = blocks
        .iter()
        .skip(combined_count - 1)
        .filter(|block| !block.stable_id.is_empty())
        .map(|block| block.stable_id.clone())
        .collect();
    if !tail.is_empty() {
        mapped.insert(combined_count, tail);
    }
    mapped
}

/// Return the post-cap item positions that need the high-risk OOS label.
#[must_use]
pub fn priority_by_combined_item(
    blocks: &[AcceptedBlock],
    combined_text: &str,
    stable_ids_by_item: &BTreeMap<usize, Vec<String>>,
) -> HashSet<usize> {
    let priority_by_stable_id: HashMap<&str, bool> = blocks
        .iter()
        .filter(|block| !block.stable_id.is_empty())
        .map(|block| (block.stable_id.as_str(), block.priority))
        .collect();
    combined_oos_blocks(combined_text)
        .iter()
        .enumerate()
        .filter_map(|(offset, block)| {
            let index = offset + 1;
            let source_priority = stable_ids_by_item.get(&index).is_some_and(|ids| {
                ids.iter().any(|id| {
                    priority_by_stable_id
                        .get(id.as_str())
                        .copied()
                        .unwrap_or(false)
                })
            });
            (source_priority || is_high_risk_oos_block(block)).then_some(index)
        })
        .collect()
}

/// Recover every filed issue the sentinel already records.
#[must_use]
pub fn sentinel_urls(text: &str) -> Vec<FiledIssue> {
    let mut stable_by_url: HashMap<String, Vec<String>> = HashMap::new();
    let mut title_by_url: HashMap<String, String> = HashMap::new();
    let mut current_stable_ids: Vec<String> = Vec::new();
    let mut current_title = String::new();
    for line in text.lines() {
        if let Some(captures) = STABLE_ID_LINE_RE.captures(line) {
            current_stable_ids.push(captures[1].to_owned());
            continue;
        }
        if let Some(captures) = TITLE_LINE_RE.captures(line) {
            captures[1].trim().clone_into(&mut current_title);
            current_stable_ids.clear();
            continue;
        }
        if let Some(captures) = FILED_URL_LINE_RE.captures(line) {
            let url = captures[1].to_owned();
            let _replaced =
                stable_by_url.insert(url.clone(), std::mem::take(&mut current_stable_ids));
            let _titled = title_by_url.insert(url, current_title.clone());
            continue;
        }
        if let Some(captures) = SENTINEL_ROW_RE.captures(line) {
            let title = captures[1].trim();
            let url = captures[2].trim();
            if !title.starts_with("OOS title") {
                let _inserted = title_by_url
                    .entry(url.to_owned())
                    .or_insert_with(|| title.to_owned());
            }
        }
    }
    let issues: Vec<FiledIssue> = GITHUB_URL_RE
        .find_iter(text)
        .map(|found| {
            let url = found.as_str();
            let title = title_by_url
                .get(url)
                .filter(|title| !title.is_empty())
                .cloned()
                .unwrap_or_else(|| "Recovered OOS disposition".to_owned());
            FiledIssue::recovered(
                title,
                url.to_owned(),
                stable_by_url.get(url).cloned().unwrap_or_default(),
            )
        })
        .collect();
    dedupe_filed(issues)
}

/// Recover every filed issue the run-log OOS batch already records.
#[must_use]
pub fn ndjson_filed_evidence(text: &str) -> Vec<FiledIssue> {
    let mut issues: Vec<FiledIssue> = Vec::new();
    for raw in text.lines() {
        if raw.trim().is_empty() {
            continue;
        }
        let Ok(serde_json::Value::Object(record)) = serde_json::from_str(raw) else {
            continue;
        };
        let body = record
            .get("body")
            .and_then(serde_json::Value::as_str)
            .unwrap_or_default();
        let mut urls: Vec<String> = FILED_URL_LINE_RE
            .captures_iter(body)
            .map(|captures| captures[1].to_owned())
            .collect();
        if urls.is_empty() {
            urls = GITHUB_URL_RE
                .find_iter(body)
                .map(|found| found.as_str().to_owned())
                .collect();
        }
        let title = TITLE_LINE_RE.captures(body).map_or_else(
            || "Recovered OOS disposition".to_owned(),
            |captures| captures[1].trim().to_owned(),
        );
        let stable_ids: Vec<String> = STABLE_ID_LINE_RE
            .captures_iter(body)
            .map(|captures| captures[1].to_owned())
            .collect();
        issues.extend(urls.into_iter().map(|url| FiledIssue {
            title: title.clone(),
            url,
            duplicate: true,
            stable_id: stable_ids.first().cloned().unwrap_or_default(),
            source_stable_ids: stable_ids.clone(),
            priority: false,
        }));
    }
    dedupe_filed(issues)
}

/// Keep the first record for each URL, preserving order.
#[must_use]
pub fn dedupe_filed(filed: Vec<FiledIssue>) -> Vec<FiledIssue> {
    let mut seen: HashSet<String> = HashSet::new();
    filed
        .into_iter()
        .filter(|issue| seen.insert(issue.url.clone()))
        .collect()
}

/// Report whether one recovered issue is the one this block became.
fn issue_matches_block(issue: &FiledIssue, block: &AcceptedBlock, allow_title_match: bool) -> bool {
    if issue_covers_stable_id(issue, &block.stable_id) || block_has_filed_url(block, &issue.url) {
        return true;
    }
    allow_title_match && normalized_title(&issue.title) == normalized_title(&block.title)
}

/// Split pending blocks into the ones still to file and the ones already filed.
///
/// A title match is only allowed when the batch holds exactly one block with
/// that title: two same-titled blocks would otherwise both bind to whichever
/// issue was recovered first, leaving the second silently unfiled.
#[must_use]
pub fn split_persisted_matches(
    blocks: &[AcceptedBlock],
    persisted: &[FiledIssue],
) -> (Vec<AcceptedBlock>, Vec<FiledIssue>) {
    let mut title_counts: HashMap<String, usize> = HashMap::new();
    for block in blocks {
        *title_counts
            .entry(normalized_title(&block.title))
            .or_insert(0) += 1;
    }
    let mut remaining: Vec<AcceptedBlock> = Vec::new();
    let mut matched: Vec<FiledIssue> = Vec::new();
    let mut used_urls: HashSet<String> = HashSet::new();
    for block in blocks {
        let allow_title_match =
            title_counts.get(&normalized_title(&block.title)).copied() == Some(1);
        let found = persisted.iter().find(|issue| {
            (!used_urls.contains(&issue.url) || issue_covers_stable_id(issue, &block.stable_id))
                && issue_matches_block(issue, block, allow_title_match)
        });
        match found {
            Some(issue) => {
                let _inserted = used_urls.insert(issue.url.clone());
                matched.push(issue.clone());
            }
            None => remaining.push(block.clone()),
        }
    }
    (remaining, matched)
}

/// Render recovered issues as a synthetic accepted-OOS artifact.
///
/// Sentinel evidence outlives the artifacts it came from, so a resumed run in
/// a pruned session directory still has blocks to bind its recovered URLs to.
#[must_use]
pub fn render_recovery_evidence(filed: &[FiledIssue]) -> String {
    filed
        .iter()
        .enumerate()
        .map(|(offset, issue)| {
            let index = offset + 1;
            let title = if issue.title.is_empty() || issue.title == "Recovered OOS disposition" {
                format!("Recovered OOS disposition {index}")
            } else {
                issue.title.clone()
            };
            let stable_id = if issue.stable_id.is_empty() {
                format!("OOS_{index}")
            } else {
                issue.stable_id.clone()
            };
            format!(
                "### OOS_{index}: {title}\n\
                 - **Description**: Recovered already filed OOS disposition from prior sentinel evidence.\n\
                 - **Filed URL**: {url}\n\
                 - **Stable ID**: {stable_id}\n\
                 - **Phase**: implement\n",
                url = issue.url,
            )
        })
        .collect::<Vec<String>>()
        .join("\n")
}

/// Wrap one sanitized OOS body in the public issue template.
#[must_use]
pub fn wrap_oos_body(body: &str, reviewer: &str, phase: &str, vote: &str) -> String {
    let reviewer = if reviewer.is_empty() { "N/A" } else { reviewer };
    let phase = if phase.is_empty() { "implement" } else { phase };
    let vote = if vote.is_empty() { "N/A" } else { vote };
    format!(
        "## Out-of-Scope Observation\n\n\
         **Surfaced by**: {reviewer}\n\
         **Phase**: {phase}\n\
         **Vote tally**: {vote}\n\n\
         ## Description\n\n\
         {body}\n\n\
         ---\n\
         *This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*\n",
        body = body.trim_end(),
    )
}

/// Truncate to at most `max_bytes`, never splitting a UTF-8 character.
fn truncate_utf8(text: &str, max_bytes: usize) -> &str {
    if text.len() <= max_bytes {
        return text;
    }
    let mut end = max_bytes;
    while end > 0 && !text.is_char_boundary(end) {
        end -= 1;
    }
    &text[..end]
}

/// Split one body into GitHub-sized parts, each labelled as a continuation.
#[must_use]
pub fn split_to_github_limit(body: &str, limit: usize) -> Vec<String> {
    if body.len() <= limit {
        return vec![body.to_owned()];
    }
    let mut chunks: Vec<String> = Vec::new();
    let mut remaining = body;
    while !remaining.is_empty() {
        let header = if chunks.is_empty() {
            ""
        } else {
            BODY_PART_HEADER
        };
        if !chunks.is_empty() && remaining.len() + header.len() <= limit {
            chunks.push(format!("{header}{remaining}"));
            break;
        }
        let footer_budget = BODY_PART_FOOTER.len();
        let max_content = limit.saturating_sub(header.len() + footer_budget);
        let content = truncate_utf8(remaining, max_content);
        // A limit too small for even one character would loop forever; the
        // whole remainder is published in one part instead of never finishing.
        if content.is_empty() {
            chunks.push(format!("{header}{remaining}"));
            break;
        }
        remaining = &remaining[content.len()..];
        let footer = if remaining.is_empty() {
            ""
        } else {
            BODY_PART_FOOTER
        };
        chunks.push(format!("{header}{content}{footer}"));
    }
    chunks
}

/// Truncate one body to the GitHub limit, saying where the detail went.
#[must_use]
pub fn summarize_to_github_limit(body: &str, limit: usize) -> String {
    if body.len() <= limit {
        return body.to_owned();
    }
    let max_content = limit.saturating_sub(SUMMARY_NOTICE.len());
    format!(
        "{}{SUMMARY_NOTICE}",
        truncate_utf8(body, max_content).trim_end()
    )
}

/// Report whether a body is the cap's aggregate rather than one observation.
#[must_use]
pub fn is_capped_rollup_body(body: &str) -> bool {
    body.contains("OOS_ISSUES_PER_RUN_CAP") && body.contains("rolled up")
}

/// Return the stable ids one filed issue records, primary first.
fn recorded_stable_ids(issue: &FiledIssue) -> Vec<String> {
    if issue.source_stable_ids.is_empty() {
        if issue.stable_id.is_empty() {
            Vec::new()
        } else {
            vec![issue.stable_id.clone()]
        }
    } else {
        issue.source_stable_ids.clone()
    }
}

/// Render the run's filing sentinel.
#[must_use]
pub fn render_sentinel(filed: &[FiledIssue]) -> String {
    let mut lines: Vec<String> = vec![
        "| OOS title | Issue | URL |".to_owned(),
        "|---|---|---|".to_owned(),
    ];
    for issue in filed {
        let number = issue.url.rsplit('/').next().unwrap_or_default();
        lines.push(format!("| {} | #{number} | {} |", issue.title, issue.url));
    }
    lines.push(String::new());
    for issue in filed {
        lines.push(format!("- **Title**: {}", issue.title));
        lines.extend(
            recorded_stable_ids(issue)
                .into_iter()
                .map(|stable_id| format!("- **Stable ID**: {stable_id}")),
        );
        lines.push(format!("- **Filed URL**: {}", issue.url));
    }
    lines.push(format!("- **Filed**: {}", filed.len()));
    format!("{}\n", lines.join("\n"))
}

/// Render the run-log OOS batch, one sanitized NDJSON record per filed issue.
#[must_use]
pub fn render_oos_ndjson(filed: &[FiledIssue], status: &str) -> String {
    if filed.is_empty() {
        return String::new();
    }
    let records: Vec<String> = filed
        .iter()
        .map(|issue| {
            let stable_lines = recorded_stable_ids(issue).into_iter().fold(
                String::new(),
                |mut rendered, stable_id| {
                    rendered.push_str("\n- **Stable ID**: ");
                    rendered.push_str(&stable_id);
                    rendered
                },
            );
            let body = format!(
                "## Accepted / Out-of-Scope Observations\n\n- **Disposition**: {status}\n- **Filed URL**: {url}\n- **Title**: {title}{stable_lines}",
                url = issue.url,
                title = issue.title,
            );
            // The batch reader is byte oriented and the record shape is a
            // published contract: the four keys keep their written order and
            // every non-ASCII scalar stays escaped, as `json.dumps` emitted it.
            let encoded = serde_json::Value::String(sanitize_public_text(&body)).to_string();
            ensure_ascii_json(&format!(
                "{{\"phase\":\"implement\",\"step\":\"9a.1\",\"category\":\"OOS\",\"body\":{encoded}}}"
            ))
        })
        .collect();
    format!("{}\n", records.join("\n"))
}

/// Report whether a filed record is a live issue rather than a carve-out stub.
fn is_real(issue: &FiledIssue) -> bool {
    !issue.url.starts_with("skipped://")
}

/// Collect the filed URLs that must carry the high-risk OOS label.
///
/// Three independent bindings are unioned because each alone is incomplete: a
/// record's own priority flag, its stable ids, and — only when the counts line
/// up exactly — its position in the composed batch.
#[must_use]
pub fn priority_urls(
    filed: &[FiledIssue],
    blocks: &[AcceptedBlock],
    combined_text: Option<&str>,
    stable_ids_by_item: &BTreeMap<usize, Vec<String>>,
) -> BTreeSet<String> {
    let mut urls: BTreeSet<String> = BTreeSet::new();
    for issue in filed.iter().filter(|issue| is_real(issue)) {
        if issue.priority {
            let _added = urls.insert(issue.url.clone());
            continue;
        }
        let high_risk = blocks
            .iter()
            .filter(|block| block.priority || is_high_risk_oos_block(&block.body))
            .any(|block| {
                issue_matches_block(issue, block, true) || block_has_filed_url(block, &issue.url)
            });
        if high_risk {
            let _added = urls.insert(issue.url.clone());
        }
    }
    let Some(combined_text) = combined_text else {
        return urls;
    };
    let combined = combined_oos_blocks(combined_text);
    let priority_indices: HashSet<usize> = combined
        .iter()
        .enumerate()
        .filter(|(_offset, block)| is_high_risk_oos_block(block))
        .map(|(offset, _block)| offset + 1)
        .collect();
    if priority_indices.is_empty() {
        return urls;
    }
    let real: Vec<&FiledIssue> = filed.iter().filter(|issue| is_real(issue)).collect();
    if real.is_empty() {
        return urls;
    }
    urls.extend(
        real.iter()
            .filter(|issue| issue.priority)
            .map(|issue| issue.url.clone()),
    );
    if combined.len() == 1 {
        urls.extend(real.iter().map(|issue| issue.url.clone()));
    } else if real.len() == combined.len() {
        urls.extend(
            real.iter()
                .enumerate()
                .filter(|(offset, _issue)| priority_indices.contains(&(offset + 1)))
                .map(|(_offset, issue)| issue.url.clone()),
        );
    }
    for index in &priority_indices {
        for stable_id in stable_ids_by_item.get(index).into_iter().flatten() {
            urls.extend(
                real.iter()
                    .filter(|issue| issue_covers_stable_id(issue, stable_id))
                    .map(|issue| issue.url.clone()),
            );
        }
    }
    urls
}

#[cfg(test)]
mod tests {
    use super::{
        AcceptedBlock, AcceptedSource, FiledIssue, bare_oos_item_suffix, combined_block_count,
        dedupe_filed, is_capped_rollup_body, issue_covers_stable_id, ndjson_filed_evidence,
        priority_by_combined_item, priority_urls, render_blocks, render_oos_ndjson,
        render_recovery_evidence, render_sentinel, sentinel_urls, split_persisted_matches,
        split_to_github_limit, stable_identifier, stable_ids_by_combined_item,
        summarize_to_github_limit, working_batch, wrap_oos_body,
    };
    use std::collections::BTreeMap;

    fn block(title: &str, stable_id: &str) -> AcceptedBlock {
        AcceptedBlock {
            title: title.to_owned(),
            body: format!("### OOS_1: {title}\n- **Description**: d\n"),
            stable_id: stable_id.to_owned(),
            priority: false,
        }
    }

    #[test]
    fn stable_identifier_prefers_the_canonical_heading() {
        let body = "### OOS_7: Something\n- **Description**: d\n";
        assert_eq!(
            stable_identifier("Something", body, "oos-accepted-review"),
            "oos-accepted-review:OOS_7"
        );
        assert_eq!(stable_identifier("Something", body, ""), "OOS_7");
    }

    #[test]
    fn stable_identifier_digests_a_block_without_a_heading() {
        let first = stable_identifier("A", "no heading here", "src");
        let second = stable_identifier("A", "no heading here", "src");
        let third = stable_identifier("A", "different text", "src");
        assert_eq!(first, second);
        assert_ne!(first, third);
        assert_eq!(first.len(), "src:".len() + 16);
    }

    #[test]
    fn bare_suffix_reads_scoped_and_unscoped_ids() {
        assert_eq!(bare_oos_item_suffix("src:OOS_2").as_deref(), Some("OOS_2"));
        assert_eq!(
            bare_oos_item_suffix("FINDING_9").as_deref(),
            Some("FINDING_9")
        );
        assert_eq!(bare_oos_item_suffix("deadbeef"), None);
    }

    #[test]
    fn coverage_bridges_only_the_legacy_primary_source() {
        let issue = FiledIssue {
            stable_id: "OOS_1".to_owned(),
            ..FiledIssue::default()
        };
        assert!(issue_covers_stable_id(
            &issue,
            "oos-accepted-main-agent:OOS_1"
        ));
        assert!(!issue_covers_stable_id(&issue, "oos-accepted-review:OOS_1"));
        assert!(!issue_covers_stable_id(&issue, ""));
        let scoped = FiledIssue {
            stable_id: "oos-accepted-review:OOS_1".to_owned(),
            ..FiledIssue::default()
        };
        assert!(issue_covers_stable_id(&scoped, "oos-accepted-review:OOS_1"));
        assert!(!issue_covers_stable_id(&scoped, "OOS_1"));
        let sourced = FiledIssue {
            stable_id: "oos-accepted-main-agent:OOS_3".to_owned(),
            ..FiledIssue::default()
        };
        assert!(issue_covers_stable_id(&sourced, "OOS_3"));
    }

    #[test]
    fn coverage_reads_absorbed_source_ids() {
        let issue = FiledIssue {
            stable_id: "src:OOS_1".to_owned(),
            source_stable_ids: vec!["src:OOS_1".to_owned(), "OOS_4".to_owned()],
            ..FiledIssue::default()
        };
        assert!(issue_covers_stable_id(&issue, "src:OOS_1"));
        assert!(issue_covers_stable_id(
            &issue,
            "oos-accepted-main-agent:OOS_4"
        ));
    }

    #[test]
    fn working_batch_holds_security_and_binds_filed_urls() {
        let text = "### OOS_1: Public one\n- **Description**: d\n\n\
                    ### OOS_2: [security] Private\n- **Description**: d\n\n\
                    ### OOS_3: Already done\n- **Description**: d\n- **Filed URL**: https://github.com/o/r/issues/5\n";
        let (blocks, already) = working_batch(&[AcceptedSource {
            source_key: "oos-accepted-review",
            text,
        }]);
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].title, "Public one");
        assert_eq!(already.len(), 1);
        assert_eq!(already[0].url, "https://github.com/o/r/issues/5");
        assert!(already[0].duplicate);
    }

    #[test]
    fn working_batch_carries_priority_onto_a_restated_block() {
        let filed = "### OOS_1: Same\n- **Description**: d\n- **focus-area**: correctness\n- **Filed URL**: https://github.com/o/r/issues/5\n";
        let pending = "### OOS_1: Same\n- **Description**: d\n";
        let (blocks, already) = working_batch(&[
            AcceptedSource {
                source_key: "a",
                text: filed,
            },
            AcceptedSource {
                source_key: "b",
                text: pending,
            },
        ]);
        assert_eq!(blocks.len(), 1);
        assert!(blocks[0].priority);
        assert_eq!(already.len(), 1);
    }

    #[test]
    fn working_batch_unions_priority_onto_an_earlier_duplicate() {
        let text = "### OOS_1: Same\n- **Description**: d\n\n\
                    ### OOS_2: Same\n- **Description**: d\n- **focus-area**: correctness\n";
        let (blocks, _already) = working_batch(&[AcceptedSource {
            source_key: "a",
            text,
        }]);
        assert_eq!(blocks.len(), 1);
        assert!(blocks[0].priority);
    }

    #[test]
    fn render_blocks_renumbers_and_terminates() {
        let blocks = vec![block("First", "a:OOS_1"), block("Second", "a:OOS_2")];
        let rendered = render_blocks(&blocks);
        assert!(rendered.starts_with("### OOS_1: First"));
        assert!(rendered.contains("### OOS_2: Second"));
        assert!(rendered.ends_with('\n'));
        assert_eq!(render_blocks(&[]), "");
        assert_eq!(combined_block_count(&rendered), 2);
    }

    #[test]
    fn stable_ids_bind_one_to_one_and_roll_the_tail_up() {
        let blocks = vec![
            block("A", "s:OOS_1"),
            block("B", "s:OOS_2"),
            block("C", "s:OOS_3"),
        ];
        let one_to_one = "### OOS_1: A\n- **Description**: d\n\n### OOS_2: B\n- **Description**: d\n\n### OOS_3: C\n- **Description**: d\n";
        let mapped = stable_ids_by_combined_item(&blocks, one_to_one);
        assert_eq!(mapped[&3], vec!["s:OOS_3".to_owned()]);

        let capped =
            "### OOS_1: A\n- **Description**: d\n\n### OOS_2: rollup\n- **Description**: d\n";
        let rolled = stable_ids_by_combined_item(&blocks, capped);
        assert_eq!(rolled[&1], vec!["s:OOS_1".to_owned()]);
        assert_eq!(rolled[&2], vec!["s:OOS_2".to_owned(), "s:OOS_3".to_owned()]);

        let single = "### OOS_1: everything\n- **Description**: d\n";
        let combined = stable_ids_by_combined_item(&blocks, single);
        assert_eq!(combined[&1].len(), 3);
        assert!(stable_ids_by_combined_item(&blocks, "").is_empty());
    }

    #[test]
    fn priority_follows_the_source_block_and_the_combined_text() {
        let mut blocks = vec![block("A", "s:OOS_1"), block("B", "s:OOS_2")];
        blocks[0].priority = true;
        let combined = "### OOS_1: A\n- **Description**: d\n\n### OOS_2: B\n- **Description**: d\n- **focus-area**: regression\n";
        let mapped = stable_ids_by_combined_item(&blocks, combined);
        let priority = priority_by_combined_item(&blocks, combined, &mapped);
        assert!(priority.contains(&1));
        assert!(priority.contains(&2));
    }

    #[test]
    fn sentinel_recovers_titles_stable_ids_and_table_rows() {
        let text = "| OOS title | Issue | URL |\n|---|---|---|\n\
                    | Table title | #4 | https://github.com/o/r/issues/4 |\n\n\
                    - **Title**: Detailed title\n\
                    - **Stable ID**: s:OOS_1\n\
                    - **Stable ID**: s:OOS_2\n\
                    - **Filed URL**: https://github.com/o/r/issues/9\n\
                    - **Filed**: 1\n";
        let recovered = sentinel_urls(text);
        assert_eq!(recovered.len(), 2);
        let detailed = recovered
            .iter()
            .find(|issue| issue.url.ends_with("/9"))
            .expect("recovered detailed row");
        assert_eq!(detailed.title, "Detailed title");
        assert_eq!(detailed.stable_id, "s:OOS_1");
        assert_eq!(detailed.source_stable_ids.len(), 2);
        let tabled = recovered
            .iter()
            .find(|issue| issue.url.ends_with("/4"))
            .expect("recovered table row");
        assert_eq!(tabled.title, "Table title");
        assert!(sentinel_urls("").is_empty());
    }

    #[test]
    fn ndjson_evidence_reads_bodies_and_skips_unreadable_lines() {
        let text = "{\"body\":\"- **Title**: T\\n- **Stable ID**: s:OOS_1\\n- **Filed URL**: https://github.com/o/r/issues/2\"}\n\
                    not json\n\
                    {\"body\":\"loose https://github.com/o/r/issues/3 url\"}\n\
                    \n";
        let recovered = ndjson_filed_evidence(text);
        assert_eq!(recovered.len(), 2);
        assert_eq!(recovered[0].title, "T");
        assert_eq!(recovered[0].stable_id, "s:OOS_1");
        assert_eq!(recovered[1].title, "Recovered OOS disposition");
    }

    #[test]
    fn dedupe_keeps_the_first_record_per_url() {
        let issues = vec![
            FiledIssue {
                url: "u".to_owned(),
                title: "first".to_owned(),
                ..FiledIssue::default()
            },
            FiledIssue {
                url: "u".to_owned(),
                title: "second".to_owned(),
                ..FiledIssue::default()
            },
        ];
        let deduped = dedupe_filed(issues);
        assert_eq!(deduped.len(), 1);
        assert_eq!(deduped[0].title, "first");
    }

    #[test]
    fn duplicate_titles_refuse_a_title_only_match() {
        let blocks = vec![block("Same", "s:OOS_1"), block("Same", "s:OOS_2")];
        let persisted = vec![FiledIssue {
            title: "Same".to_owned(),
            url: "https://github.com/o/r/issues/1".to_owned(),
            ..FiledIssue::default()
        }];
        let (remaining, matched) = split_persisted_matches(&blocks, &persisted);
        assert_eq!(remaining.len(), 2);
        assert!(matched.is_empty());

        let unique = vec![block("Same", "s:OOS_1")];
        let (left, bound) = split_persisted_matches(&unique, &persisted);
        assert!(left.is_empty());
        assert_eq!(bound.len(), 1);
    }

    #[test]
    fn recovery_evidence_names_untitled_rows_by_position() {
        let rendered = render_recovery_evidence(&[FiledIssue {
            title: "Recovered OOS disposition".to_owned(),
            url: "https://github.com/o/r/issues/1".to_owned(),
            ..FiledIssue::default()
        }]);
        assert!(rendered.contains("### OOS_1: Recovered OOS disposition 1"));
        assert!(rendered.contains("- **Stable ID**: OOS_1"));
    }

    #[test]
    fn body_parts_carry_continuation_markers() {
        let body = "x".repeat(300);
        let parts = split_to_github_limit(&body, 100);
        assert!(parts.len() > 2);
        assert!(parts[0].ends_with("*[Continued in a follow-up issue.]*"));
        assert!(parts[1].starts_with("\n\n*[Continuation of a prior out-of-scope issue.]*"));
        assert!(!parts[parts.len() - 1].ends_with("*[Continued in a follow-up issue.]*"));
        assert_eq!(
            split_to_github_limit("short", 100),
            vec!["short".to_owned()]
        );
        // A limit smaller than the markers still terminates, in one part.
        assert_eq!(split_to_github_limit(&body, 4), vec![body.clone()]);
    }

    #[test]
    fn summary_replaces_overlong_detail_with_a_pointer() {
        let body = "y".repeat(500);
        let summarized = summarize_to_github_limit(&body, 200);
        assert!(summarized.len() <= 200);
        assert!(summarized.ends_with("run logs.]*\n"));
        assert_eq!(summarize_to_github_limit("short", 200), "short");
    }

    #[test]
    fn rollup_bodies_are_recognized() {
        assert!(is_capped_rollup_body(
            "Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; items were rolled up"
        ));
        assert!(!is_capped_rollup_body("ordinary body"));
    }

    #[test]
    fn wrapped_bodies_fill_missing_fields() {
        let wrapped = wrap_oos_body("detail", "", "", "");
        assert!(wrapped.contains("**Surfaced by**: N/A"));
        assert!(wrapped.contains("**Phase**: implement"));
        assert!(wrapped.contains("**Vote tally**: N/A"));
    }

    #[test]
    fn sentinel_and_ndjson_record_every_absorbed_id() {
        let filed = vec![FiledIssue {
            title: "T".to_owned(),
            url: "https://github.com/o/r/issues/8".to_owned(),
            source_stable_ids: vec!["s:OOS_1".to_owned(), "s:OOS_2".to_owned()],
            ..FiledIssue::default()
        }];
        let sentinel = render_sentinel(&filed);
        assert!(sentinel.contains("| T | #8 | https://github.com/o/r/issues/8 |"));
        assert!(sentinel.contains("- **Stable ID**: s:OOS_2"));
        assert!(sentinel.ends_with("- **Filed**: 1\n"));
        let ndjson = render_oos_ndjson(&filed, "Filed");
        assert!(ndjson.starts_with(
            "{\"phase\":\"implement\",\"step\":\"9a.1\",\"category\":\"OOS\",\"body\":\""
        ));
        assert!(ndjson.contains("s:OOS_2"));
        assert_eq!(render_oos_ndjson(&[], "Filed"), "");
        // Non-ASCII in the disposition stays escaped the way `json.dumps` wrote it.
        let escaped = render_oos_ndjson(&filed, "Skipped — forked target");
        assert!(escaped.contains("Skipped \\u2014 forked target"));
    }

    #[test]
    fn priority_urls_union_flag_block_and_position_bindings() {
        let mut blocks = vec![block("A", "s:OOS_1"), block("B", "s:OOS_2")];
        blocks[1].priority = true;
        let filed = vec![
            FiledIssue {
                title: "A".to_owned(),
                url: "https://github.com/o/r/issues/1".to_owned(),
                stable_id: "s:OOS_1".to_owned(),
                ..FiledIssue::default()
            },
            FiledIssue {
                title: "B".to_owned(),
                url: "https://github.com/o/r/issues/2".to_owned(),
                stable_id: "s:OOS_2".to_owned(),
                ..FiledIssue::default()
            },
        ];
        let combined = "### OOS_1: A\n- **Description**: d\n\n### OOS_2: B\n- **Description**: d\n- **focus-area**: correctness\n";
        let mapped = stable_ids_by_combined_item(&blocks, combined);
        let urls = priority_urls(&filed, &blocks, Some(combined), &mapped);
        assert!(urls.contains("https://github.com/o/r/issues/2"));
        assert!(!urls.contains("https://github.com/o/r/issues/1"));
    }

    #[test]
    fn priority_urls_skip_carve_out_placeholders() {
        let filed = vec![FiledIssue {
            url: "skipped://oos/1".to_owned(),
            priority: true,
            ..FiledIssue::default()
        }];
        let urls = priority_urls(&filed, &[], None, &BTreeMap::new());
        assert!(urls.is_empty());
    }
}
