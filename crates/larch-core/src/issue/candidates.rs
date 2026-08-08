//! The `/issue` Phase 1 dedup candidate allocator.
//!
//! Ports Python `larch.issue.issue_create.allocate_candidates`. A read-only
//! verdict subagent nominates `CAND <item> <issue> <kind> <confidence>` rows;
//! this owner turns them into the bounded, deterministic candidate set Phase 2
//! fetches. The rows are model output, so every field is validated and a row
//! that fails validation is dropped with a reason rather than trusted.
//!
//! Two passes fill the [`CANDIDATE_CAP`] slots. Pass A reserves a per-item floor
//! so no item loses its coverage to a noisier neighbour, crediting every item
//! that nominated a candidate already in the union. Pass B fills what is left by
//! global confidence ranking.

use crate::text::{split_text_lines, unsigned_integer};
use std::collections::{BTreeMap, BTreeSet};

/// The most candidates Phase 2 will ever fetch bodies and comments for.
pub const CANDIDATE_CAP: usize = 30;

/// The most coverage slots one item can reserve in Pass A.
const MAX_FLOOR: u64 = 3;

/// Why one `CAND` row was not counted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CandidateRowDefect {
    TooFewFields,
    NonNumericItem,
    ItemOutOfRange { item: u64, total: u64 },
    NonPositiveIssue,
}

/// One dropped row, kept verbatim so the operator can see what was rejected.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CandidateRowDrop {
    pub defect: CandidateRowDefect,
    pub row: String,
}

impl CandidateRowDrop {
    /// Render the fixed diagnostic `/issue` operators already read on stderr.
    #[must_use]
    pub fn message(&self) -> String {
        let detail = match self.defect {
            CandidateRowDefect::TooFewFields => "too few fields".to_owned(),
            CandidateRowDefect::NonNumericItem => "non-numeric item index".to_owned(),
            CandidateRowDefect::ItemOutOfRange { item, total } => {
                format!("item index {item} out of range 1..{total}")
            }
            CandidateRowDefect::NonPositiveIssue => {
                "non-numeric or non-positive issue number".to_owned()
            }
        };
        format!(
            "**⚠ /issue: dropped malformed CAND row ({detail}): {}**",
            self.row
        )
    }
}

/// The allocated candidates and every row that did not survive validation.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct CandidateAllocation {
    pub candidates: Vec<u64>,
    pub dropped: Vec<CandidateRowDrop>,
}

/// One accepted nomination, reduced to the three fields the passes read.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Nomination {
    confidence: u8,
    item: u64,
    issue: u64,
}

/// Allocate the bounded candidate set for `total_items` items.
///
/// An empty result is a normal outcome: no rows survived, or there were none.
#[must_use]
pub fn allocate_candidates(total_items: u64, rows_text: &str) -> CandidateAllocation {
    let mut allocation = CandidateAllocation::default();
    if total_items == 0 {
        return allocation;
    }
    let nominations = scan_rows(total_items, rows_text, &mut allocation.dropped);
    if nominations.is_empty() {
        return allocation;
    }
    let mut union: BTreeSet<u64> = BTreeSet::new();
    reserve_floor(total_items, &nominations, &mut union);
    fill_spillover(&nominations, &mut union);
    allocation.candidates = union.into_iter().collect();
    allocation
}

/// Validate every `CAND` row and reduce duplicates to their best confidence.
///
/// A repeated `(item, issue)` pair keeps its highest confidence, so a candidate
/// nominated as both a duplicate and a dependency is counted once. The `kind`
/// column is required for the row to be well formed but never read: Python
/// normalized an unrecognized kind to `dup` and then used the value nowhere,
/// so an unknown kind has always been accepted rather than dropped.
fn scan_rows(
    total_items: u64,
    rows_text: &str,
    dropped: &mut Vec<CandidateRowDrop>,
) -> Vec<Nomination> {
    let mut best: BTreeMap<(u64, u64), u8> = BTreeMap::new();
    for original in split_text_lines(rows_text) {
        let line = original.trim();
        let Some(rest) = line.strip_prefix("CAND ") else {
            continue;
        };
        let mut fields = rest.split_whitespace();
        let (Some(item_text), Some(issue_text), Some(_kind)) =
            (fields.next(), fields.next(), fields.next())
        else {
            dropped.push(drop_row(CandidateRowDefect::TooFewFields, original));
            continue;
        };
        let confidence = confidence_rank(fields.next().unwrap_or("low"));
        let Some(item) = unsigned_integer(item_text) else {
            dropped.push(drop_row(CandidateRowDefect::NonNumericItem, original));
            continue;
        };
        if item < 1 || item > total_items {
            dropped.push(drop_row(
                CandidateRowDefect::ItemOutOfRange {
                    item,
                    total: total_items,
                },
                original,
            ));
            continue;
        }
        let Some(issue) = unsigned_integer(issue_text).filter(|issue| *issue > 0) else {
            dropped.push(drop_row(CandidateRowDefect::NonPositiveIssue, original));
            continue;
        };
        best.entry((item, issue))
            .and_modify(|current| *current = (*current).max(confidence))
            .or_insert(confidence);
    }
    best.into_iter()
        .map(|((item, issue), confidence)| Nomination {
            confidence,
            item,
            issue,
        })
        .collect()
}

/// Reserve up to `floor` coverage slots for each item, in item order.
///
/// A candidate already in the union still credits the item that nominated it,
/// and admitting one credits every other item that nominated it too, so shared
/// candidates do not consume the batch's floor twice.
fn reserve_floor(total_items: u64, nominations: &[Nomination], union: &mut BTreeSet<u64>) {
    let floor = per_item_floor(total_items);
    if floor == 0 {
        return;
    }
    let mut nominators: BTreeMap<u64, Vec<u64>> = BTreeMap::new();
    for nomination in nominations {
        nominators
            .entry(nomination.issue)
            .or_default()
            .push(nomination.item);
    }
    // `floor > 0` only holds at or below the cap, so one credit slot per item
    // is a bounded allocation whatever the caller supplied.
    let mut credit: Vec<u64> = vec![0; usize::try_from(total_items).unwrap_or(CANDIDATE_CAP)];
    for item in 1..=total_items {
        let mut ranked: Vec<&Nomination> = nominations
            .iter()
            .filter(|nomination| nomination.item == item)
            .collect();
        ranked.sort_by_key(|nomination| (u8::MAX - nomination.confidence, nomination.issue));
        let index = usize::try_from(item - 1).unwrap_or(0);
        for nomination in ranked {
            if credit[index] >= floor {
                break;
            }
            if union.contains(&nomination.issue) {
                credit[index] += 1;
                continue;
            }
            if union.len() >= CANDIDATE_CAP {
                break;
            }
            let _ = union.insert(nomination.issue);
            for nominator in nominators.get(&nomination.issue).into_iter().flatten() {
                if let Some(slot) = credit.get_mut(usize::try_from(*nominator - 1).unwrap_or(0)) {
                    *slot += 1;
                }
            }
        }
    }
}

/// Fill the remaining slots by confidence, then issue, then item.
fn fill_spillover(nominations: &[Nomination], union: &mut BTreeSet<u64>) {
    if union.len() >= CANDIDATE_CAP {
        return;
    }
    let mut leftovers: Vec<&Nomination> = nominations
        .iter()
        .filter(|nomination| !union.contains(&nomination.issue))
        .collect();
    leftovers.sort_by_key(|nomination| {
        (
            u8::MAX - nomination.confidence,
            nomination.issue,
            nomination.item,
        )
    });
    for nomination in leftovers {
        if union.len() >= CANDIDATE_CAP {
            break;
        }
        let _ = union.insert(nomination.issue);
    }
}

/// Return the per-item coverage floor, which vanishes above the cap.
///
/// Above the cap there are fewer slots than items, so a floor would starve the
/// ranking without covering anything; every slot goes to Pass B instead.
fn per_item_floor(total_items: u64) -> u64 {
    let Ok(total) = usize::try_from(total_items) else {
        return 0;
    };
    if total == 0 || total > CANDIDATE_CAP {
        return 0;
    }
    MAX_FLOOR.min(u64::try_from(CANDIDATE_CAP / total).unwrap_or(MAX_FLOOR))
}

fn confidence_rank(value: &str) -> u8 {
    match value {
        "high" => 3,
        "medium" => 2,
        _ => 1,
    }
}

fn drop_row(defect: CandidateRowDefect, row: &str) -> CandidateRowDrop {
    CandidateRowDrop {
        defect,
        row: row.to_owned(),
    }
}
