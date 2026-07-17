use std::{collections::{BTreeMap, BTreeSet}, sync::LazyLock};

use regex::Regex;
use serde::Deserialize;

use crate::{
    Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::{FenceState, MarkdownDocument},
};

const NAME: &str = "guideline-no-exception";
const DESCRIPTION: &str = "Require baselines for no-exception architectural guidelines";
const GUIDELINES_PATH: &str = "ARCHITECTURAL_GUIDELINES.md";
const BASELINE_PATH: &str = "crates/larch-lint/config/guideline-no-exception-baseline.json";

static GUIDELINE_HEADING: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^###\s+(G-[A-Za-z0-9-]+-\d+):\s*(.+?)\s*$")
        .expect("guideline heading expression is valid")
});
static MARKDOWN_HEADING: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^#{1,6}\s+\S").expect("heading expression is valid"));
static NO_EXCEPTION_DEVIATE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^- Deviate when:\s*(n/a|never)\b")
        .expect("no-exception deviate expression is valid")
});
static GUIDELINE_ID: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^G-[A-Za-z][A-Za-z0-9-]*-\d+$").expect("guideline identifier expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/guideline-no-exception.toml",
);

#[derive(Debug)]
pub struct GuidelineNoExceptionRule;

pub static RULE: GuidelineNoExceptionRule = GuidelineNoExceptionRule;

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct BaselineRow {
    guideline_id: String,
    reason: String,
}

#[derive(Debug)]
struct GuidelineEntry {
    identifier: String,
    start_line: u32,
    deviate_line: Option<u32>,
    saw_body: bool,
}

impl Rule for GuidelineNoExceptionRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let baseline = load_baseline(repository)?;
        let guidelines = repository.read_utf8(&RepoPath::from_trusted(GUIDELINES_PATH))?;
        let live = scan_guidelines(&guidelines)?;
        let live_ids: BTreeSet<String> = live
            .iter()
            .map(|entry| entry.identifier.clone())
            .collect();
        let mut findings = Vec::new();
        let mut warnings = Vec::new();
        for entry in live {
            if baseline.contains_key(&entry.identifier) {
                warnings.push(format!(
                    "{} line {} has a no-exception deviate clause (baselined)",
                    entry.identifier,
                    entry.deviate_line.expect("live entries have deviate lines")
                ));
                continue;
            }
            findings.push(Finding::new(
                GUIDELINES_PATH,
                entry.deviate_line.expect("live entries have deviate lines"),
                format!(
                    "{} has a no-exception deviate clause; promote it, add a real deviate clause, or add a reason to {BASELINE_PATH}",
                    entry.identifier
                ),
            ));
        }
        for identifier in baseline
            .keys()
            .filter(|identifier| !live_ids.contains(identifier.as_str()))
        {
            findings.push(Finding::new(
                BASELINE_PATH,
                1,
                format!("stale baseline row: {identifier}"),
            ));
        }
        Ok(RuleOutput::new(findings, warnings))
    }
}

fn load_baseline(repository: &Repository) -> Result<BTreeMap<String, BaselineRow>, LintError> {
    let text = repository.read_utf8(&RepoPath::from_trusted(BASELINE_PATH))?;
    let rows: Vec<BaselineRow> = serde_json::from_str(&text)
        .map_err(|error| LintError::new(format!("{BASELINE_PATH}: invalid JSON baseline: {error}")))?;
    let mut baseline = BTreeMap::new();
    for (index, row) in rows.into_iter().enumerate() {
        if !GUIDELINE_ID.is_match(&row.guideline_id)
            || !is_nonempty_single_line(&row.reason)
        {
            return Err(LintError::new(format!(
                "{BASELINE_PATH}: baseline row {} has invalid guideline row",
                index + 1
            )));
        }
        let identifier = row.guideline_id.clone();
        if baseline.insert(identifier.clone(), row).is_some() {
            return Err(LintError::new(format!(
                "{BASELINE_PATH}: duplicate guideline id {identifier}"
            )));
        }
    }
    Ok(baseline)
}

fn is_nonempty_single_line(value: &str) -> bool {
    !value.trim().is_empty() && !value.contains(['\n', '\r'])
}

fn scan_guidelines(source: &str) -> Result<Vec<GuidelineEntry>, LintError> {
    let mut entries = Vec::new();
    let mut seen = BTreeSet::new();
    let mut current = None;
    let mut saw_heading = false;
    for line in MarkdownDocument::new(source).lines() {
        if line.fence_state() != FenceState::Outside {
            continue;
        }
        if let Some(captures) = GUIDELINE_HEADING.captures(line.text()) {
            saw_heading = true;
            finish_entry(&mut current, &mut seen, &mut entries)?;
            current = Some(GuidelineEntry {
                identifier: captures[1].to_owned(),
                start_line: u32::try_from(line.number())
                    .map_err(|_| LintError::new("guideline line number exceeds u32"))?,
                deviate_line: None,
                saw_body: false,
            });
            continue;
        }
        if MARKDOWN_HEADING.is_match(line.text()) {
            finish_entry(&mut current, &mut seen, &mut entries)?;
            continue;
        }
        let Some(entry) = current.as_mut() else {
            continue;
        };
        if !line.text().trim().is_empty() {
            entry.saw_body = true;
        }
        if entry.deviate_line.is_none() && NO_EXCEPTION_DEVIATE.is_match(line.text()) {
            entry.deviate_line = Some(
                u32::try_from(line.number())
                    .map_err(|_| LintError::new("guideline line number exceeds u32"))?,
            );
        }
    }
    finish_entry(&mut current, &mut seen, &mut entries)?;
    if !saw_heading && !source.trim().is_empty() {
        return Err(LintError::new(
            "ARCHITECTURAL_GUIDELINES.md: no recognized guideline entries",
        ));
    }
    Ok(entries)
}

fn finish_entry(
    current: &mut Option<GuidelineEntry>,
    seen: &mut BTreeSet<String>,
    findings: &mut Vec<GuidelineEntry>,
) -> Result<(), LintError> {
    let Some(entry) = current.take() else {
        return Ok(());
    };
    if !entry.saw_body {
        return Err(LintError::new(format!(
            "ARCHITECTURAL_GUIDELINES.md: guideline entry {} at line {} is missing body content",
            entry.identifier, entry.start_line
        )));
    }
    if !seen.insert(entry.identifier.clone()) {
        return Err(LintError::new(format!(
            "ARCHITECTURAL_GUIDELINES.md: duplicate guideline id {}",
            entry.identifier
        )));
    }
    if entry.deviate_line.is_some() {
        findings.push(entry);
    }
    Ok(())
}

crate::register_rule!(METADATA, RULE);
