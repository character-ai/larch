//! Ordered review-item adjudication shared by tally families.

use super::voting;
use std::path::PathBuf;

/// One prepared judge cell.
pub type VoteCell = (String, String, String, String, String, Option<String>);

/// Inputs prepared by a tally family for one item.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ItemContext {
    /// Item identifier.
    pub item_id: String,
    /// Backing block path.
    pub block_path: PathBuf,
    /// Canonical block text.
    pub block_text: String,
    /// Artifact text.
    pub artifact_text: String,
    /// Proposing reviewer.
    pub reviewer: String,
    /// Parsed judge cells.
    pub cells: Vec<VoteCell>,
    /// YES count.
    pub yes: usize,
    /// NO count.
    pub no: usize,
    /// Judge-error count.
    pub judge_error: usize,
    /// Whether this started as an OOS item.
    pub is_oos: bool,
    /// Eligible voter count.
    pub eligible_voters: usize,
    /// Per-voter vote values.
    pub voter_votes: Vec<(String, String)>,
    /// Per-voter severity values.
    pub voter_severities: Vec<String>,
}

/// Policy decision before and after the security hook.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ItemAdjudicationResult {
    /// Prepared item context.
    pub context: ItemContext,
    /// Base vote classification.
    pub voting_result: String,
    /// In-scope or OOS classification.
    pub classification_scope: String,
    /// Whether major YES evidence rerouted a neutral finding.
    pub neutral_rescued: bool,
    /// Whether an OOS result is fileable.
    pub fileable_oos: bool,
    /// Score domain.
    pub score_kind: String,
    /// Score result.
    pub score_result: String,
    /// Accepted finding weight.
    pub accepted_weight: u8,
    /// Whether sole-finder bonus eligibility applies.
    pub unique_finder_eligible: bool,
    /// Ledger outcome.
    pub ledger_outcome: String,
    /// Artifact reroute marker.
    pub reroute_marker: String,
    /// Artifact bucket.
    pub artifact_bucket: String,
    /// Security classification after the security hook.
    pub security: Option<bool>,
}

/// Adjudicate a prepared item exactly once.
#[must_use]
pub fn adjudicate_item(context: ItemContext) -> ItemAdjudicationResult {
    let votes: Vec<String> = context
        .voter_votes
        .iter()
        .map(|(_, vote)| vote.clone())
        .collect();
    let voting_result = if context.is_oos {
        voting::classify_oos_result(context.yes, context.eligible_voters)
    } else {
        voting::classify_result(context.yes, context.eligible_voters)
    }
    .to_owned();
    let fileable_oos =
        voting::oos_fileable_from_votes(&voting_result, &votes, &context.voter_severities);
    let neutral_rescued = voting::neutral_high_severity_rescue_to_oos(
        &voting_result,
        &votes,
        &context.voter_severities,
    );
    let score_kind = if context.is_oos || neutral_rescued {
        "oos"
    } else {
        "finding"
    }
    .to_owned();
    let score_result = if context.is_oos && voting_result == "accepted" && !fileable_oos {
        "neutral".to_owned()
    } else {
        voting_result.clone()
    };
    let accepted_weight = if score_kind == "finding" && score_result == "accepted" {
        voting::accepted_finding_points_from_severities(&votes, &context.voter_severities)
    } else {
        0
    };
    let classification_scope = if context.is_oos || neutral_rescued {
        "oos"
    } else {
        "in_scope"
    }
    .to_owned();
    let ledger_outcome = if classification_scope == "oos" {
        "oos".to_owned()
    } else {
        voting_result.clone()
    };
    let artifact_bucket = if classification_scope == "oos" {
        "oos"
    } else if voting_result == "accepted" {
        "accepted"
    } else {
        "rejected"
    }
    .to_owned();
    ItemAdjudicationResult {
        context,
        voting_result,
        classification_scope,
        neutral_rescued,
        fileable_oos,
        score_kind: score_kind.clone(),
        score_result: score_result.clone(),
        accepted_weight,
        unique_finder_eligible: score_kind == "finding" && score_result == "accepted",
        ledger_outcome,
        reroute_marker: if neutral_rescued {
            "neutral-rescued".to_owned()
        } else {
            String::new()
        },
        artifact_bucket,
        security: None,
    }
}

/// Execute prepare, serialize, security, then publish in order, stopping at the first error.
///
/// # Errors
///
/// Returns the first hook error without preparing later items.
pub fn run_items<E>(
    contexts: impl IntoIterator<Item = ItemContext>,
    mut serialize: impl FnMut(&ItemAdjudicationResult) -> Result<(), E>,
    mut security_hook: impl FnMut(&ItemContext) -> Result<bool, E>,
    mut publish: impl FnMut(&ItemAdjudicationResult) -> Result<(), E>,
) -> Result<Vec<ItemAdjudicationResult>, E> {
    let mut completed = Vec::new();
    for context in contexts {
        let mut result = adjudicate_item(context);
        serialize(&result)?;
        result.security = Some(security_hook(&result.context)?);
        publish(&result)?;
        completed.push(result);
    }
    Ok(completed)
}
