//! Deterministic test-shard packing and Makefile shard-line handling.

use serde::{Deserialize, Serialize};
use std::{cmp::Ordering, collections::BTreeMap};

/// One measured test target used by the LPT packer.
#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct TestShardTiming {
    pub target: String,
    pub seconds: f64,
}

/// Shard members keyed by their one-based shard identifier.
pub type TestShardMap = BTreeMap<u32, Vec<String>>;

struct ShardState {
    id: u32,
    total: f64,
    item_count: usize,
    targets: Vec<String>,
}

struct WeightedTarget {
    target: String,
    seconds: f64,
}

/// Pack measured targets and optional unmeasured extras with greedy LPT.
///
/// Timings with equal durations retain their input order. Extras have zero
/// weight and use item count then shard id as deterministic tie-breakers, so
/// they fan out instead of collecting in the first shard.
///
/// # Errors
///
/// Returns an error when `n_shards` is zero or a timing is negative or
/// non-finite.
pub fn pack_test_shards(
    timings: &[TestShardTiming],
    n_shards: u32,
    guard: &str,
    extras: &[String],
) -> Result<TestShardMap, String> {
    if n_shards == 0 {
        return Err("n_shards must be at least 1".to_owned());
    }

    let mut targets = Vec::with_capacity(timings.len().saturating_add(extras.len()));
    for timing in timings {
        if !timing.seconds.is_finite() || timing.seconds < 0.0 {
            return Err(format!(
                "timing for {:?} must be a non-negative finite number",
                timing.target
            ));
        }
        targets.push(WeightedTarget {
            target: timing.target.clone(),
            seconds: normalize_zero(timing.seconds),
        });
    }
    targets.sort_by(|left, right| right.seconds.total_cmp(&left.seconds));
    targets.extend(extras.iter().cloned().map(|target| WeightedTarget {
        target,
        seconds: 0.0,
    }));

    let shard_count =
        usize::try_from(n_shards).map_err(|_| format!("n_shards is too large: {n_shards}"))?;
    let mut shards = (1..=n_shards)
        .map(|id| ShardState {
            id,
            total: 0.0,
            item_count: 0,
            targets: Vec::new(),
        })
        .collect::<Vec<_>>();

    debug_assert_eq!(shards.len(), shard_count);
    for target in targets {
        let mut lightest = 0;
        for candidate in 1..shards.len() {
            if lighter_than(&shards[candidate], &shards[lightest]) {
                lightest = candidate;
            }
        }
        let shard = &mut shards[lightest];
        shard.total += target.seconds;
        shard.item_count += 1;
        shard.targets.push(target.target);
    }

    if !guard.is_empty() {
        for shard in &mut shards {
            if let Some(index) = shard.targets.iter().position(|target| target == guard) {
                let target = shard.targets.remove(index);
                shard.targets.insert(0, target);
                break;
            }
        }
    }

    Ok(shards
        .into_iter()
        .map(|shard| (shard.id, shard.targets))
        .collect())
}

/// Read literal single-line `test-harnesses-N:` rules from Makefile text.
#[must_use]
pub fn read_makefile_shards(source: &str) -> TestShardMap {
    source.lines().filter_map(parse_shard_line).collect()
}

/// Replace only supplied literal `test-harnesses-N:` rules in Makefile text.
///
/// Each replacement is emitted on exactly one physical line with a trailing
/// newline. All other bytes remain unchanged.
#[must_use]
pub fn rewrite_makefile_shards(source: &str, shards: &TestShardMap) -> String {
    let mut output = String::with_capacity(source.len());
    for line in source.split_inclusive('\n') {
        let logical_line = line.strip_suffix('\n').unwrap_or(line);
        if let Some((shard, _)) = parse_shard_line(logical_line)
            && let Some(prerequisites) = shards.get(&shard)
        {
            output.push_str("test-harnesses-");
            output.push_str(&shard.to_string());
            output.push_str(": ");
            output.push_str(&prerequisites.join(" "));
            output.push('\n');
        } else {
            output.push_str(line);
        }
    }
    output
}

fn normalize_zero(seconds: f64) -> f64 {
    if seconds == 0.0 { 0.0 } else { seconds }
}

fn lighter_than(candidate: &ShardState, current: &ShardState) -> bool {
    match candidate.total.total_cmp(&current.total) {
        Ordering::Less => true,
        Ordering::Greater => false,
        Ordering::Equal => {
            candidate.item_count < current.item_count
                || (candidate.item_count == current.item_count && candidate.id < current.id)
        }
    }
}

fn parse_shard_line(line: &str) -> Option<(u32, Vec<String>)> {
    let (target, prerequisites) = line.split_once(':')?;
    let shard = target.strip_prefix("test-harnesses-")?;
    if shard.is_empty() || !shard.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    let shard = shard.parse::<u32>().ok()?;
    if shard == 0 {
        return None;
    }
    Some((
        shard,
        prerequisites
            .split_whitespace()
            .map(str::to_owned)
            .collect(),
    ))
}

#[cfg(test)]
mod tests {
    use super::{TestShardTiming, pack_test_shards, read_makefile_shards, rewrite_makefile_shards};
    use std::collections::BTreeMap;

    fn timings(values: &[(&str, f64)]) -> Vec<TestShardTiming> {
        values
            .iter()
            .map(|(target, seconds)| TestShardTiming {
                target: (*target).to_owned(),
                seconds: *seconds,
            })
            .collect()
    }

    #[test]
    fn pack_uses_lpt_with_stable_ties() {
        let packed = pack_test_shards(
            &timings(&[
                ("test-a", 10.0),
                ("test-b", 8.0),
                ("test-c", 6.0),
                ("test-d", 4.0),
            ]),
            2,
            "",
            &[],
        )
        .expect("pack targets");

        assert_eq!(packed[&1], ["test-a", "test-d"]);
        assert_eq!(packed[&2], ["test-b", "test-c"]);
    }

    #[test]
    fn pack_spreads_zero_weight_extras_and_pins_the_guard() {
        let extras = [
            "test-harness-shards-coverage".to_owned(),
            "test-new-1".to_owned(),
            "test-new-2".to_owned(),
            "test-new-3".to_owned(),
        ];
        let packed = pack_test_shards(&[], 2, &extras[0], &extras).expect("pack targets");

        assert_eq!(packed[&1], ["test-harness-shards-coverage", "test-new-2"]);
        assert_eq!(packed[&2], ["test-new-1", "test-new-3"]);
    }

    #[test]
    fn pack_rejects_invalid_inputs() {
        assert_eq!(
            pack_test_shards(&[], 0, "", &[]),
            Err("n_shards must be at least 1".to_owned())
        );
        assert!(pack_test_shards(&timings(&[("test-a", -1.0)]), 1, "", &[]).is_err());
    }

    #[test]
    fn makefile_reader_and_writer_preserve_the_line_contract() {
        let source = concat!(
            ".PHONY: test-harnesses-1 test-harnesses-2\n",
            "test-harnesses-1: test-alpha test-beta\n",
            "test-harnesses-2: test-gamma\n",
            "test-alpha:\n",
            "\ttrue\n",
        );
        assert_eq!(
            read_makefile_shards(source),
            BTreeMap::from([
                (1, vec!["test-alpha".to_owned(), "test-beta".to_owned()]),
                (2, vec!["test-gamma".to_owned()]),
            ])
        );

        let rewritten = rewrite_makefile_shards(
            source,
            &BTreeMap::from([(1, vec!["test-gamma".to_owned()])]),
        );
        assert_eq!(
            rewritten,
            concat!(
                ".PHONY: test-harnesses-1 test-harnesses-2\n",
                "test-harnesses-1: test-gamma\n",
                "test-harnesses-2: test-gamma\n",
                "test-alpha:\n",
                "\ttrue\n",
            )
        );
    }

    #[test]
    fn makefile_reader_and_writer_support_empty_and_large_shards() {
        let source = concat!(
            "all: test-harnesses-3 test-harnesses-20\n",
            "test-harnesses-3:\n",
            "test-harnesses-20: test-last\n",
            "test-last:\n",
            "\ttrue\n",
        );
        assert_eq!(
            read_makefile_shards(source),
            BTreeMap::from([(3, Vec::new()), (20, vec!["test-last".to_owned()])])
        );

        let rewritten = rewrite_makefile_shards(
            source,
            &BTreeMap::from([(20, vec!["test-first".to_owned(), "test-last".to_owned()])]),
        );
        assert_eq!(
            rewritten,
            concat!(
                "all: test-harnesses-3 test-harnesses-20\n",
                "test-harnesses-3:\n",
                "test-harnesses-20: test-first test-last\n",
                "test-last:\n",
                "\ttrue\n",
            )
        );
    }

    #[test]
    fn makefile_reader_preserves_legacy_first_line_behavior_and_rejects_zero_shards() {
        let source = concat!(
            "test-harnesses-0: test-zero\n",
            "test-harnesses-1: test-one \\\n",
            " test-two\n",
        );
        assert_eq!(
            read_makefile_shards(source),
            BTreeMap::from([(1, vec!["test-one".to_owned(), "\\".to_owned()])])
        );
    }
}
