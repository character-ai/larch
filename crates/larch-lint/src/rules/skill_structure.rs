//! Enforce declarative structure contracts for shipped skill prompts.
//!
//! # Crate survey (issue #8900)
//!
//! | Need | Candidates | Selection |
//! |---|---|---|
//! | Contract storage | Rust constants, JSONL manifest | Use a JSONL manifest so prompt wording remains data and the rule stays a stable evaluator. |
//! | Fixed and regex matching | handwritten scans, workspace `regex` | Use direct string scans for literals and the workspace regex engine for the few legacy regex contracts. |
//! | Repository state | filesystem calls, shared `Repository` | Reuse the immutable repository snapshot so missing files, symlinks, and non-UTF-8 input fail closed consistently. |

use std::collections::BTreeSet;

use regex::Regex;
use serde::Deserialize;

use super::python_boundary::offset_line_number;
use crate::{
    Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
};

const NAME: &str = "skill-structure";
const DESCRIPTION: &str = "Require live skill prompt structure declared by the shared pin manifest";
const MANIFEST_PATH: &str = "crates/larch-lint/config/skill-structure-pins.jsonl";

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/skill-structure.toml",
);

#[derive(Debug)]
pub struct SkillStructureRule;

pub static RULE: SkillStructureRule = SkillStructureRule;

#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
enum PinKind {
    Contains,
    Absent,
    RegexContains,
    RegexAbsent,
    ExactCount,
    CountAtLeast,
    Ordered,
    SameLine,
    AdjacentPairCountAtLeast,
    CrossFileBound,
    Near,
    PathExists,
    PathAbsent,
    PathIsDir,
    PathNotDir,
    LineStartsWith,
    LineNotStartsWith,
}

#[derive(Clone, Copy, Debug, Default, Deserialize)]
#[serde(rename_all = "snake_case")]
enum CountUnit {
    #[default]
    MatchingLine,
    PhysicalLine,
    Substring,
    AdjacentPair,
}

#[derive(Clone, Copy, Debug, Default, Deserialize)]
#[serde(rename_all = "snake_case")]
enum MatchMode {
    #[default]
    ExactLine,
    Contains,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Pin {
    id: String,
    path: String,
    kind: PinKind,
    #[serde(default)]
    needle: String,
    #[serde(default)]
    needle2: String,
    #[serde(default)]
    tokens: Vec<String>,
    #[serde(default)]
    path2: String,
    expected: Option<usize>,
    bound: Option<usize>,
    #[serde(default)]
    count_unit: CountUnit,
    #[serde(default)]
    match_mode: MatchMode,
}

impl Rule for SkillStructureRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let manifest_path = RepoPath::from_trusted(MANIFEST_PATH);
        let manifest = repository.read_required_utf8(
            &manifest_path,
            format!("{MANIFEST_PATH}: required skill-structure manifest is missing"),
        )?;
        let pins = parse_manifest(&manifest)?;
        let mut findings = Vec::new();
        for pin in &pins {
            evaluate(repository, pin, &mut findings)?;
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

fn parse_manifest(source: &str) -> Result<Vec<Pin>, LintError> {
    let mut pins = Vec::new();
    let mut ids = BTreeSet::new();
    for (index, line) in source.lines().enumerate() {
        let line_number = index + 1;
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        let pin: Pin = serde_json::from_str(trimmed).map_err(|error| {
            LintError::new(format!(
                "{MANIFEST_PATH}:{line_number}: invalid skill-structure pin: {error}"
            ))
        })?;
        validate_pin(&pin, line_number)?;
        if !ids.insert(pin.id.clone()) {
            return Err(LintError::new(format!(
                "{MANIFEST_PATH}:{line_number}: duplicate pin id {:?}",
                pin.id
            )));
        }
        pins.push(pin);
    }
    Ok(pins)
}

fn validate_pin(pin: &Pin, line_number: usize) -> Result<(), LintError> {
    let invalid = |message: &str| {
        LintError::new(format!(
            "{MANIFEST_PATH}:{line_number}: pin {:?} {message}",
            pin.id
        ))
    };
    if pin.id.is_empty() {
        return Err(invalid("has an empty id"));
    }
    RepoPath::parse(&pin.path).map_err(|_| invalid("has an unsafe path"))?;
    match pin.kind {
        PinKind::SameLine if pin.tokens.is_empty() => {
            return Err(invalid("requires non-empty tokens"));
        }
        PinKind::PathExists
        | PinKind::PathAbsent
        | PinKind::PathIsDir
        | PinKind::PathNotDir
        | PinKind::SameLine => {}
        PinKind::Ordered | PinKind::AdjacentPairCountAtLeast => {
            if pin.needle.is_empty() || pin.needle2.is_empty() {
                return Err(invalid("requires needle and needle2"));
            }
        }
        PinKind::CrossFileBound => {
            if pin.needle.is_empty() || pin.needle2.is_empty() || pin.path2.is_empty() {
                return Err(invalid("requires needle, needle2, and path2"));
            }
            RepoPath::parse(&pin.path2).map_err(|_| invalid("has an unsafe path2"))?;
            if pin.bound.is_none() {
                return Err(invalid("requires bound"));
            }
        }
        PinKind::Near => {
            if pin.needle.is_empty() || pin.needle2.is_empty() || pin.bound.is_none() {
                return Err(invalid("requires needle, needle2, and bound"));
            }
        }
        _ if pin.needle.is_empty() => return Err(invalid("requires a non-empty needle")),
        _ => {}
    }
    match pin.kind {
        PinKind::ExactCount
        | PinKind::CountAtLeast
        | PinKind::AdjacentPairCountAtLeast
            if pin.expected.is_none() =>
        {
            Err(invalid("requires expected"))
        }
        _ => Ok(()),
    }?;
    match (pin.kind, pin.count_unit) {
        (PinKind::AdjacentPairCountAtLeast, CountUnit::AdjacentPair) => Ok(()),
        (PinKind::AdjacentPairCountAtLeast, _) => {
            Err(invalid("requires count_unit adjacent_pair"))
        }
        (_, CountUnit::AdjacentPair) => Err(invalid(
            "may use count_unit adjacent_pair only with adjacent_pair_count_at_least",
        )),
        _ => Ok(()),
    }
}

fn evaluate(
    repository: &Repository,
    pin: &Pin,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let path = RepoPath::parse(&pin.path)?;
    let exists = repository.paths().binary_search(&path).is_ok();
    let directory = is_directory(repository, &pin.path);
    if evaluate_path_contract(pin, exists, directory, findings) {
        return Ok(());
    }
    if !exists {
        findings.push(finding(pin, 1, "required target file is missing"));
        return Ok(());
    }
    let source = repository.read_utf8(&path)?;
    evaluate_text_contract(repository, pin, &source, findings)
}

fn evaluate_path_contract(
    pin: &Pin,
    exists: bool,
    directory: bool,
    findings: &mut Vec<Finding>,
) -> bool {
    match pin.kind {
        PinKind::PathExists => {
            if !exists && !directory {
                findings.push(finding(pin, 1, "required path is missing"));
            }
            true
        }
        PinKind::PathAbsent => {
            if exists || directory {
                findings.push(finding(pin, 1, "retired path is present"));
            }
            true
        }
        PinKind::PathIsDir => {
            if !directory {
                findings.push(finding(pin, 1, "required directory is missing"));
            }
            true
        }
        PinKind::PathNotDir => {
            if directory {
                findings.push(finding(pin, 1, "forbidden directory is present"));
            }
            true
        }
        _ => false,
    }
}

fn evaluate_text_contract(
    repository: &Repository,
    pin: &Pin,
    source: &str,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    match pin.kind {
        PinKind::Contains => {
            if !source.contains(&pin.needle) {
                findings.push(finding(pin, 1, "required text is missing"));
            }
        }
        PinKind::Absent => {
            if let Some(offset) = source.find(&pin.needle) {
                findings.push(finding(
                    pin,
                    offset_line_number(source, offset),
                    "forbidden text is present",
                ));
            }
        }
        PinKind::RegexContains | PinKind::RegexAbsent => {
            evaluate_regex(pin, source, findings)?;
        }
        PinKind::ExactCount | PinKind::CountAtLeast => {
            evaluate_count(pin, source, findings);
        }
        PinKind::Ordered => {
            let first = anchor(source, &pin.needle, pin.match_mode);
            let second = anchor(source, &pin.needle2, pin.match_mode);
            if first.zip(second).is_none_or(|(left, right)| left >= right) {
                findings.push(finding(pin, 1, "required anchors are missing or out of order"));
            }
        }
        PinKind::SameLine => {
            if !source
                .lines()
                .any(|line| pin.tokens.iter().all(|token| line.contains(token)))
            {
                findings.push(finding(pin, 1, "no line contains every required token"));
            }
        }
        PinKind::AdjacentPairCountAtLeast => {
            evaluate_adjacent_pairs(pin, source, findings);
        }
        PinKind::CrossFileBound => {
            evaluate_cross_file(repository, pin, source, findings)?;
        }
        PinKind::Near => {
            evaluate_near(pin, source, findings);
        }
        PinKind::LineStartsWith | PinKind::LineNotStartsWith => {
            let matched = source.lines().any(|line| line.starts_with(&pin.needle));
            if matched != matches!(pin.kind, PinKind::LineStartsWith) {
                findings.push(finding(pin, 1, "line-prefix contract is not satisfied"));
            }
        }
        PinKind::PathExists
        | PinKind::PathAbsent
        | PinKind::PathIsDir
        | PinKind::PathNotDir => unreachable!("path predicates return before source loading"),
    }
    Ok(())
}

fn evaluate_regex(pin: &Pin, source: &str, findings: &mut Vec<Finding>) -> Result<(), LintError> {
    let expression = Regex::new(&pin.needle)
        .map_err(|error| LintError::new(format!("pin {:?} has an invalid regex: {error}", pin.id)))?;
    let matched = expression.find(source);
    if matches!(pin.kind, PinKind::RegexContains) && matched.is_none() {
        findings.push(finding(pin, 1, "required regex does not match"));
    } else if matches!(pin.kind, PinKind::RegexAbsent)
        && let Some(found) = matched
    {
        findings.push(finding(
            pin,
            offset_line_number(source, found.start()),
            "forbidden regex matches",
        ));
    }
    Ok(())
}

fn evaluate_count(pin: &Pin, source: &str, findings: &mut Vec<Finding>) {
    let observed = count(source, &pin.needle, pin.count_unit);
    let expected = pin.expected.expect("validated count");
    let failed = match pin.kind {
        PinKind::ExactCount => observed != expected,
        PinKind::CountAtLeast => observed < expected,
        _ => unreachable!("count evaluator called for non-count predicate"),
    };
    if failed {
        findings.push(finding(
            pin,
            1,
            &format!("expected count {expected}, observed {observed}"),
        ));
    }
}

fn evaluate_adjacent_pairs(pin: &Pin, source: &str, findings: &mut Vec<Finding>) {
    let lines: Vec<_> = source.lines().collect();
    let observed = lines
        .windows(2)
        .filter(|pair| pair[0] == pin.needle && pair[1] == pin.needle2)
        .count();
    let expected = pin.expected.expect("validated adjacent count");
    if observed < expected {
        findings.push(finding(
            pin,
            1,
            &format!("expected {expected} adjacent pairs, observed {observed}"),
        ));
    }
}

fn evaluate_cross_file(
    repository: &Repository,
    pin: &Pin,
    source: &str,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let path2 = RepoPath::parse(&pin.path2)?;
    if repository.paths().binary_search(&path2).is_err() {
        findings.push(finding(pin, 1, "required second target file is missing"));
        return Ok(());
    }
    let source2 = repository.read_utf8(&path2)?;
    let left = matching_lines(source, &pin.needle);
    let right = matching_lines(&source2, &pin.needle2);
    let bound = pin.bound.expect("validated bound");
    if !left
        .iter()
        .any(|a| right.iter().any(|b| a.abs_diff(*b) <= bound))
    {
        findings.push(finding(pin, 1, "cross-file anchors exceed their line bound"));
    }
    Ok(())
}

fn evaluate_near(pin: &Pin, source: &str, findings: &mut Vec<Finding>) {
    let bound = pin.bound.expect("validated proximity bound");
    let Some(anchor_offset) = source.find(&pin.needle) else {
        findings.push(finding(pin, 1, "proximity anchor is missing"));
        return;
    };
    let mut start = anchor_offset.saturating_sub(bound);
    while !source.is_char_boundary(start) {
        start += 1;
    }
    let mut end = anchor_offset.saturating_add(bound).min(source.len());
    while !source.is_char_boundary(end) {
        end -= 1;
    }
    if !source[start..end].contains(&pin.needle2) {
        findings.push(finding(
            pin,
            offset_line_number(source, anchor_offset),
            "required text is outside the proximity bound",
        ));
    }
}

fn is_directory(repository: &Repository, raw: &str) -> bool {
    let prefix = format!("{}/", raw.trim_end_matches('/'));
    repository
        .paths()
        .iter()
        .any(|path| path.as_str().starts_with(&prefix))
}

fn count(source: &str, needle: &str, unit: CountUnit) -> usize {
    match unit {
        CountUnit::MatchingLine | CountUnit::PhysicalLine => {
            source.lines().filter(|line| line.contains(needle)).count()
        }
        CountUnit::Substring => source.match_indices(needle).count(),
        CountUnit::AdjacentPair => unreachable!("validated adjacent-pair count unit"),
    }
}

fn anchor(source: &str, needle: &str, mode: MatchMode) -> Option<usize> {
    source.lines().position(|line| match mode {
        MatchMode::ExactLine => line == needle,
        MatchMode::Contains => line.contains(needle),
    })
}

fn matching_lines(source: &str, needle: &str) -> Vec<usize> {
    source
        .lines()
        .enumerate()
        .filter_map(|(index, line)| line.contains(needle).then_some(index + 1))
        .collect()
}

fn finding(pin: &Pin, line: u32, message: &str) -> Finding {
    Finding::new(&pin.path, line, format!("{}: {message}", pin.id))
}

crate::register_rule!(METADATA, RULE);
