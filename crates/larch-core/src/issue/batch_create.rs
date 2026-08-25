//! Domain plan for one `/issue` batch-create pass.
//!
//! The skill's earlier phases still own candidate analysis and edge validation.
//! This module consumes their durable `KEY=value` result, proves that every
//! cross-item reference is usable, and produces one deterministic processing
//! order. The effectful CLI driver can then create, wire, roll back, and skip
//! descendants without re-deriving graph state in prompt-authored Bash.

use std::{
    collections::{BTreeMap, BTreeSet, VecDeque},
    error::Error,
    fmt,
};

use crate::{DuplicatePolicy, KvDocument, ParseOptions};

use super::oos_conflict::topological_create_order;

/// One validated dependency endpoint from the Step 5 result.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum BatchIssueReference {
    /// An existing issue in the target repository.
    Existing(u64),
    /// Another item in this batch, by its one-based input index.
    Item(usize),
}

impl fmt::Display for BatchIssueReference {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Existing(number) => write!(formatter, "{number}"),
            Self::Item(index) => write!(formatter, "ITEM_{index}"),
        }
    }
}

/// The Step 5 disposition for one parsed item.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum BatchItemVerdict {
    /// File the item.
    Create,
    /// Reuse one existing issue.
    DuplicateExisting { number: u64, url: String },
    /// Reuse another item after that item resolves to its ultimate target.
    DuplicateItem(usize),
    /// The parser found no publishable body.
    Malformed,
}

/// One item ready for the effectful create driver.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BatchCreateItem {
    index: usize,
    title: String,
    body_file: String,
    reviewer: String,
    phase: String,
    vote_tally: String,
    verdict: BatchItemVerdict,
    blocked_by: Vec<BatchIssueReference>,
    blocks: Vec<BatchIssueReference>,
}

impl BatchCreateItem {
    /// Return the one-based original input index.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Return the input title before prefix normalization.
    #[must_use]
    pub fn title(&self) -> &str {
        &self.title
    }

    /// Return the parser-owned body path.
    #[must_use]
    pub fn body_file(&self) -> &str {
        &self.body_file
    }

    /// Return the optional OOS reviewer field.
    #[must_use]
    pub fn reviewer(&self) -> &str {
        &self.reviewer
    }

    /// Return the optional OOS phase field.
    #[must_use]
    pub fn phase(&self) -> &str {
        &self.phase
    }

    /// Return the optional OOS vote field.
    #[must_use]
    pub fn vote_tally(&self) -> &str {
        &self.vote_tally
    }

    /// Return whether any OOS metadata was present in parser output.
    #[must_use]
    pub const fn is_oos(&self) -> bool {
        !self.reviewer.is_empty() || !self.phase.is_empty() || !self.vote_tally.is_empty()
    }

    /// Return the validated disposition.
    #[must_use]
    pub const fn verdict(&self) -> &BatchItemVerdict {
        &self.verdict
    }

    /// Return the Step 5 blocked-by list in source order after deduplication.
    #[must_use]
    pub fn blocked_by(&self) -> &[BatchIssueReference] {
        &self.blocked_by
    }

    /// Return the Step 5 blocks list in source order after deduplication.
    #[must_use]
    pub fn blocks(&self) -> &[BatchIssueReference] {
        &self.blocks
    }
}

/// A complete, checked batch-create plan.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BatchCreatePlan {
    items: Vec<BatchCreateItem>,
    order: Vec<usize>,
    successors: BTreeMap<usize, BTreeSet<usize>>,
    effective_blocked_by: BTreeMap<usize, Vec<BatchIssueReference>>,
    policy_blocker: Option<(u64, u64)>,
}

impl BatchCreatePlan {
    /// Parse the parser output and the post-validation Step 5 result.
    ///
    /// Both inputs use strict environment-key grammar and reject duplicate or
    /// malformed rows. Values remain byte-preserving except for CRLF framing.
    ///
    /// # Errors
    ///
    /// Returns a stable diagnostic when a required field, item reference,
    /// verdict, dependency, or topological prerequisite is unusable.
    pub fn parse(parse_output: &str, decisions: &str) -> Result<Self, BatchCreatePlanError> {
        let parsed = strict_values(parse_output, "parse output")?;
        let decisions = strict_values(decisions, "decisions")?;
        let total = parse_index(required(&parsed, "ITEMS_TOTAL")?)
            .ok_or_else(|| error("ITEMS_TOTAL must be a non-negative ASCII integer"))?;
        if total > parsed.len() {
            return Err(error("ITEMS_TOTAL exceeds the available parse rows"));
        }

        let mut items = Vec::with_capacity(total);
        for index in 1..=total {
            let prefix = format!("ITEM_{index}_");
            let title = required(&parsed, &format!("{prefix}TITLE"))?.to_owned();
            let malformed = optional_boolean(&parsed, &format!("{prefix}MALFORMED"))?;
            let body_file = value(&parsed, &format!("{prefix}BODY_FILE")).to_owned();
            if !malformed && body_file.is_empty() {
                return Err(error(format!("item {index} is missing BODY_FILE")));
            }
            let verdict = if malformed {
                BatchItemVerdict::Malformed
            } else {
                parse_verdict(index, &decisions)?
            };
            let blocked_by = parse_references(
                value(&decisions, &format!("{prefix}BLOCKED_BY")),
                index,
                total,
                "BLOCKED_BY",
            )?;
            let blocks = parse_references(
                value(&decisions, &format!("{prefix}BLOCKS")),
                index,
                total,
                "BLOCKS",
            )?;
            if malformed && (!blocked_by.is_empty() || !blocks.is_empty()) {
                return Err(error(format!(
                    "malformed item {index} carries dependency edges"
                )));
            }
            if matches!(
                verdict,
                BatchItemVerdict::DuplicateExisting { .. } | BatchItemVerdict::DuplicateItem(_)
            ) && (!blocked_by.is_empty() || !blocks.is_empty())
            {
                return Err(error(format!(
                    "duplicate item {index} carries dependency edges"
                )));
            }
            items.push(BatchCreateItem {
                index,
                title,
                body_file,
                reviewer: value(&parsed, &format!("{prefix}REVIEWER")).to_owned(),
                phase: value(&parsed, &format!("{prefix}PHASE")).to_owned(),
                vote_tally: value(&parsed, &format!("{prefix}VOTE_TALLY")).to_owned(),
                verdict,
                blocked_by,
                blocks,
            });
        }

        validate_item_targets(&items)?;
        let policy_blocker = parse_policy_blocker(&decisions)?;
        let (order, successors, effective_blocked_by) = graph(&items)?;
        Ok(Self {
            items,
            order,
            successors,
            effective_blocked_by,
            policy_blocker,
        })
    }

    /// Return all items in original input order.
    #[must_use]
    pub fn items(&self) -> &[BatchCreateItem] {
        &self.items
    }

    /// Return the deterministic one-based processing order.
    #[must_use]
    pub fn order(&self) -> &[usize] {
        &self.order
    }

    /// Return one item by its one-based index.
    #[must_use]
    pub fn item(&self, index: usize) -> Option<&BatchCreateItem> {
        index
            .checked_sub(1)
            .and_then(|offset| self.items.get(offset))
    }

    /// Return the blocked-by edges to apply after this item is created.
    ///
    /// A sibling `BLOCKS=ITEM_j` is normalized here into
    /// `ITEM_j_BLOCKED_BY=ITEM_i`, so the client exists when the edge is
    /// applied. Existing-issue `BLOCKS` edges remain on their source item.
    #[must_use]
    pub fn effective_blocked_by(&self, index: usize) -> &[BatchIssueReference] {
        self.effective_blocked_by
            .get(&index)
            .map_or(&[], Vec::as_slice)
    }

    /// Return all transitive descendants of `index`, lowest index first.
    #[must_use]
    pub fn descendants(&self, index: usize) -> Vec<usize> {
        let mut found = BTreeSet::new();
        let mut pending = VecDeque::from([index]);
        while let Some(current) = pending.pop_front() {
            if let Some(children) = self.successors.get(&current) {
                for child in children {
                    if found.insert(*child) {
                        pending.push_back(*child);
                    }
                }
            }
        }
        found.into_iter().collect()
    }

    /// Return a cached node id for the probed policy blocker, when supplied.
    #[must_use]
    pub fn policy_blocker_id(&self, number: u64) -> Option<u64> {
        self.policy_blocker
            .filter(|(policy_number, _)| *policy_number == number)
            .map(|(_, identifier)| identifier)
    }
}

/// One unusable batch plan.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BatchCreatePlanError(String);

impl fmt::Display for BatchCreatePlanError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl Error for BatchCreatePlanError {}

fn error(message: impl Into<String>) -> BatchCreatePlanError {
    BatchCreatePlanError(message.into())
}

fn strict_values(
    text: &str,
    label: &str,
) -> Result<BTreeMap<String, String>, BatchCreatePlanError> {
    if text.contains('\r') {
        return Err(error(format!("invalid {label}: carriage return")));
    }
    KvDocument::parse(text, ParseOptions::environment())
        .map(|document| document.select(DuplicatePolicy::Last))
        .map_err(|detail| error(format!("invalid {label}: {detail}")))
}

fn required<'values>(
    values: &'values BTreeMap<String, String>,
    key: &str,
) -> Result<&'values str, BatchCreatePlanError> {
    values
        .get(key)
        .filter(|value| !value.is_empty())
        .map(String::as_str)
        .ok_or_else(|| error(format!("missing required row {key}")))
}

fn value<'values>(values: &'values BTreeMap<String, String>, key: &str) -> &'values str {
    values.get(key).map_or("", String::as_str)
}

fn optional_boolean(
    values: &BTreeMap<String, String>,
    key: &str,
) -> Result<bool, BatchCreatePlanError> {
    match value(values, key) {
        "" | "false" => Ok(false),
        "true" => Ok(true),
        other => Err(error(format!("{key} must be true or false, got {other}"))),
    }
}

fn parse_index(raw: &str) -> Option<usize> {
    if raw.is_empty() || !raw.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    raw.parse().ok()
}

fn parse_positive_u64(raw: &str) -> Option<u64> {
    if raw.is_empty() || !raw.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    raw.parse().ok().filter(|number| *number > 0)
}

fn parse_verdict(
    index: usize,
    decisions: &BTreeMap<String, String>,
) -> Result<BatchItemVerdict, BatchCreatePlanError> {
    let prefix = format!("ITEM_{index}_");
    match required(decisions, &format!("{prefix}VERDICT"))? {
        "CREATE" => Ok(BatchItemVerdict::Create),
        "DUPLICATE" => {
            let existing = value(decisions, &format!("{prefix}DUPLICATE_OF"));
            let item = value(decisions, &format!("{prefix}DUPLICATE_OF_ITEM"));
            match (existing.is_empty(), item.is_empty()) {
                (false, true) => {
                    let number = parse_positive_u64(existing)
                        .ok_or_else(|| error(format!("item {index} has invalid DUPLICATE_OF")))?;
                    let url = required(decisions, &format!("{prefix}DUPLICATE_OF_URL"))?;
                    Ok(BatchItemVerdict::DuplicateExisting {
                        number,
                        url: url.to_owned(),
                    })
                }
                (true, false) => parse_index(item)
                    .map(BatchItemVerdict::DuplicateItem)
                    .ok_or_else(|| error(format!("item {index} has invalid DUPLICATE_OF_ITEM"))),
                _ => Err(error(format!(
                    "duplicate item {index} must name exactly one target"
                ))),
            }
        }
        other => Err(error(format!("item {index} has unknown verdict {other}"))),
    }
}

fn parse_references(
    raw: &str,
    source: usize,
    total: usize,
    field: &str,
) -> Result<Vec<BatchIssueReference>, BatchCreatePlanError> {
    if raw.is_empty() {
        return Ok(Vec::new());
    }
    let mut seen = BTreeSet::new();
    let mut references = Vec::new();
    for part in raw.split(',').map(str::trim) {
        let reference = if let Some(item) = part.strip_prefix("ITEM_") {
            let target = parse_index(item).ok_or_else(|| {
                error(format!(
                    "item {source} has invalid {field} reference {part}"
                ))
            })?;
            if target == source || target == 0 || target > total {
                return Err(error(format!(
                    "item {source} has out-of-range {field} reference {part}"
                )));
            }
            BatchIssueReference::Item(target)
        } else {
            BatchIssueReference::Existing(parse_positive_u64(part).ok_or_else(|| {
                error(format!(
                    "item {source} has invalid {field} reference {part}"
                ))
            })?)
        };
        if seen.insert(reference) {
            references.push(reference);
        }
    }
    Ok(references)
}

fn validate_item_targets(items: &[BatchCreateItem]) -> Result<(), BatchCreatePlanError> {
    for item in items {
        let dependency_targets =
            item.blocked_by
                .iter()
                .chain(&item.blocks)
                .filter_map(|reference| match reference {
                    BatchIssueReference::Item(index) => Some(*index),
                    BatchIssueReference::Existing(_) => None,
                });
        for target in dependency_targets {
            let Some(target_item) = items.get(target.saturating_sub(1)) else {
                return Err(error(format!(
                    "item {} references missing item {target}",
                    item.index
                )));
            };
            if target == item.index || target_item.verdict == BatchItemVerdict::Malformed {
                return Err(error(format!(
                    "item {} references unusable item {target}",
                    item.index
                )));
            }
            if matches!(
                target_item.verdict,
                BatchItemVerdict::DuplicateExisting { .. } | BatchItemVerdict::DuplicateItem(_)
            ) {
                return Err(error(format!(
                    "item {} dependency references duplicate item {target}",
                    item.index
                )));
            }
        }
        if let BatchItemVerdict::DuplicateItem(target) = item.verdict {
            let Some(target_item) = items.get(target.saturating_sub(1)) else {
                return Err(error(format!(
                    "item {} references missing item {target}",
                    item.index
                )));
            };
            if target == item.index || target_item.verdict == BatchItemVerdict::Malformed {
                return Err(error(format!(
                    "item {} references unusable item {target}",
                    item.index
                )));
            }
        }
    }
    Ok(())
}

fn parse_policy_blocker(
    decisions: &BTreeMap<String, String>,
) -> Result<Option<(u64, u64)>, BatchCreatePlanError> {
    let number = value(decisions, "BLOCKED_BY_ISSUE");
    let identifier = value(decisions, "BLOCKED_BY_ISSUE_ID");
    match (number.is_empty(), identifier.is_empty()) {
        (true, true) => Ok(None),
        (false, false) => Ok(Some((
            parse_positive_u64(number)
                .ok_or_else(|| error("BLOCKED_BY_ISSUE must be a positive integer"))?,
            parse_positive_u64(identifier)
                .ok_or_else(|| error("BLOCKED_BY_ISSUE_ID must be a positive integer"))?,
        ))),
        _ => Err(error(
            "BLOCKED_BY_ISSUE and BLOCKED_BY_ISSUE_ID must appear together",
        )),
    }
}

type BatchGraph = (
    Vec<usize>,
    BTreeMap<usize, BTreeSet<usize>>,
    BTreeMap<usize, Vec<BatchIssueReference>>,
);

fn graph(items: &[BatchCreateItem]) -> Result<BatchGraph, BatchCreatePlanError> {
    let mut edges = BTreeSet::new();
    let mut effective: BTreeMap<usize, Vec<BatchIssueReference>> = items
        .iter()
        .map(|item| (item.index, item.blocked_by.clone()))
        .collect();
    for item in items {
        for reference in &item.blocked_by {
            if let BatchIssueReference::Item(blocker) = reference {
                edges.insert((*blocker, item.index));
            }
        }
        for reference in &item.blocks {
            if let BatchIssueReference::Item(blocked) = reference {
                edges.insert((item.index, *blocked));
                let normalized = BatchIssueReference::Item(item.index);
                let references = effective.entry(*blocked).or_default();
                if !references.contains(&normalized) {
                    references.push(normalized);
                }
            }
        }
        if let BatchItemVerdict::DuplicateItem(blocker) = item.verdict {
            edges.insert((blocker, item.index));
        }
    }
    let edge_rows: Vec<(usize, usize)> = edges.iter().copied().collect();
    let order = topological_create_order(items.len(), &edge_rows);
    let positions: BTreeMap<usize, usize> = order
        .iter()
        .enumerate()
        .map(|(position, item)| (*item, position))
        .collect();
    if edges.iter().any(|(blocker, blocked)| {
        positions.get(blocker).unwrap_or(&usize::MAX)
            >= positions.get(blocked).unwrap_or(&usize::MAX)
    }) {
        return Err(error("batch dependency graph contains a cycle"));
    }
    let mut successors: BTreeMap<usize, BTreeSet<usize>> = BTreeMap::new();
    for (blocker, blocked) in edges {
        successors.entry(blocker).or_default().insert(blocked);
    }
    Ok((order, successors, effective))
}

#[cfg(test)]
mod tests {
    use super::{BatchCreatePlan, BatchIssueReference, BatchItemVerdict};

    const PARSED: &str = concat!(
        "ITEM_1_TITLE=One\n",
        "ITEM_1_BODY_FILE=/tmp/body-1\n",
        "ITEM_2_TITLE=Two\n",
        "ITEM_2_BODY_FILE=/tmp/body-2\n",
        "ITEM_3_TITLE=Three\n",
        "ITEM_3_BODY_FILE=/tmp/body-3\n",
        "ITEM_4_TITLE=Four\n",
        "ITEM_4_BODY_FILE=/tmp/body-4\n",
        "ITEMS_TOTAL=4\n",
    );

    #[test]
    fn topological_ties_use_original_input_index() {
        let decisions = concat!(
            "ITEM_1_VERDICT=CREATE\n",
            "ITEM_1_BLOCKED_BY=ITEM_3\n",
            "ITEM_2_VERDICT=CREATE\n",
            "ITEM_2_BLOCKED_BY=ITEM_4\n",
            "ITEM_3_VERDICT=CREATE\n",
            "ITEM_4_VERDICT=CREATE\n",
        );
        let plan = BatchCreatePlan::parse(PARSED, decisions).expect("valid plan");
        assert_eq!(plan.order(), [3, 1, 4, 2]);
        assert_eq!(plan.descendants(3), [1]);
        assert_eq!(plan.descendants(4), [2]);
    }

    #[test]
    fn sibling_blocks_are_normalized_onto_the_later_client() {
        let parsed = PARSED.replace("ITEMS_TOTAL=4\n", "ITEMS_TOTAL=2\n");
        let decisions = concat!(
            "ITEM_1_VERDICT=CREATE\n",
            "ITEM_1_BLOCKS=ITEM_2,99\n",
            "ITEM_2_VERDICT=CREATE\n",
        );
        let plan = BatchCreatePlan::parse(&parsed, decisions).expect("valid plan");
        assert_eq!(plan.order(), [1, 2]);
        assert_eq!(plan.effective_blocked_by(2), [BatchIssueReference::Item(1)]);
        assert_eq!(
            plan.item(1).expect("item").blocks(),
            [
                BatchIssueReference::Item(2),
                BatchIssueReference::Existing(99)
            ]
        );
    }

    #[test]
    fn duplicate_chains_are_prerequisites_and_cycles_refuse() {
        let parsed = PARSED.replace("ITEMS_TOTAL=4\n", "ITEMS_TOTAL=3\n");
        let decisions = concat!(
            "ITEM_1_VERDICT=CREATE\n",
            "ITEM_2_VERDICT=DUPLICATE\n",
            "ITEM_2_DUPLICATE_OF_ITEM=1\n",
            "ITEM_3_VERDICT=DUPLICATE\n",
            "ITEM_3_DUPLICATE_OF_ITEM=2\n",
        );
        let plan = BatchCreatePlan::parse(&parsed, decisions).expect("valid chain");
        assert_eq!(plan.order(), [1, 2, 3]);
        assert_eq!(plan.descendants(1), [2, 3]);
        assert_eq!(
            plan.item(3).expect("item").verdict(),
            &BatchItemVerdict::DuplicateItem(2)
        );

        let duplicate_edge = decisions.replace(
            "ITEM_2_DUPLICATE_OF_ITEM=1\n",
            "ITEM_2_DUPLICATE_OF_ITEM=1\nITEM_2_BLOCKED_BY=ITEM_1\n",
        );
        assert_eq!(
            BatchCreatePlan::parse(&parsed, &duplicate_edge)
                .expect_err("duplicate edge")
                .to_string(),
            "duplicate item 2 carries dependency edges"
        );

        let duplicate_target = concat!(
            "ITEM_1_VERDICT=CREATE\n",
            "ITEM_2_VERDICT=DUPLICATE\n",
            "ITEM_2_DUPLICATE_OF_ITEM=1\n",
            "ITEM_3_VERDICT=CREATE\n",
            "ITEM_3_BLOCKED_BY=ITEM_2\n",
        );
        assert_eq!(
            BatchCreatePlan::parse(&parsed, duplicate_target)
                .expect_err("dependency target was not collapsed")
                .to_string(),
            "item 3 dependency references duplicate item 2"
        );

        let cycle = decisions.replace(
            "ITEM_1_VERDICT=CREATE\n",
            "ITEM_1_VERDICT=DUPLICATE\nITEM_1_DUPLICATE_OF_ITEM=3\n",
        );
        assert_eq!(
            BatchCreatePlan::parse(&parsed, &cycle)
                .expect_err("cycle")
                .to_string(),
            "batch dependency graph contains a cycle"
        );
    }

    #[test]
    fn strict_wire_and_policy_blocker_inputs_fail_closed() {
        let parsed = "ITEM_1_TITLE=One\nITEM_1_BODY_FILE=/tmp/body\nITEMS_TOTAL=1\n";
        let decisions = "ITEM_1_VERDICT=CREATE\nBLOCKED_BY_ISSUE=42\nBLOCKED_BY_ISSUE_ID=9001\nITEM_1_BLOCKED_BY=42\n";
        let plan = BatchCreatePlan::parse(parsed, decisions).expect("policy edge");
        assert_eq!(plan.policy_blocker_id(42), Some(9001));
        assert_eq!(plan.policy_blocker_id(43), None);
        assert!(
            BatchCreatePlan::parse(parsed, "ITEM_1_VERDICT=CREATE\nITEM_1_VERDICT=CREATE\n")
                .is_err()
        );
        assert!(
            BatchCreatePlan::parse(parsed, "ITEM_1_VERDICT=CREATE\nBLOCKED_BY_ISSUE=42\n").is_err()
        );
        assert!(BatchCreatePlan::parse(parsed, "ITEM_1_VERDICT=CREATE\r").is_err());
        let unbounded = format!("ITEMS_TOTAL={}\n", usize::MAX);
        assert_eq!(
            BatchCreatePlan::parse(&unbounded, "ITEM_1_VERDICT=CREATE\n")
                .expect_err("unbounded total")
                .to_string(),
            "ITEMS_TOTAL exceeds the available parse rows"
        );
    }
}
