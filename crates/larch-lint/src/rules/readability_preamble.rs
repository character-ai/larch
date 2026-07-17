//! Require every readability preamble directive declared in the manifest.
//!
//! # Crate survey (issue #7607)
//!
//! | Need | Candidates | Selection |
//! |---|---|---|
//! | Markdown lines | workspace `pulldown-cmark`, handwritten splitter | Reuse `MarkdownDocument` so source-line matching shares the maintained Markdown support. |
//! | Skill and agent discovery | workspace `globset`, filesystem walk | Reuse `PathSelector` over the runner's validated Git snapshot. |
//! | Manifest parsing | `csv`, handwritten TSV fields | Parse the fixed five-column manifest directly. The remaining policy is specific to this lint. |

use regex::Regex;

use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::MarkdownDocument,
};

const NAME: &str = "readability-preamble";
const DESCRIPTION: &str = "Require manifest-declared readability preamble directives";
const MANIFEST_PATH: &str = "scripts/lint-readability-preamble.tsv";
const EXTERNAL_STYLE_LINE: &str = "Style requirements: `<READABILITY_STYLE>`.";
const PLAN_REVIEW_STYLE_LINE: &str =
    "Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`.";
const PUBLIC_STYLE_PATH: &str = "${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md";
const DEV_STYLE_PATH: &str = "$PWD/skills/shared/readability-style.md";
const ORCHESTRATOR_INLINE: &str = "orchestrator-inline";
const EXTERNAL_PROMPT: &str = "external-prompt";
const METADATA_FLOOR: &str = "metadata-min-count";
const SKILL_EXEMPT: &str = "skill-exempt";

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/readability-preamble.toml",
);

#[derive(Debug)]
pub struct ReadabilityPreambleRule;

pub static RULE: ReadabilityPreambleRule = ReadabilityPreambleRule;

impl Rule for ReadabilityPreambleRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let rows = manifest_rows(repository)?;
        let exemptions = validate_exemptions(&rows)?;
        let mut findings = check_floor(&rows)?;
        for row in &rows {
            match row.variant.as_str() {
                METADATA_FLOOR | SKILL_EXEMPT => {}
                ORCHESTRATOR_INLINE | EXTERNAL_PROMPT => {
                    findings.extend(check_counted_row(repository, row)?);
                }
                variant => {
                    return Err(LintError::new(format!(
                        "{MANIFEST_PATH}: unknown manifest variant: {variant}"
                    )));
                }
            }
        }
        findings.extend(check_skills(repository, &exemptions)?);
        findings.extend(check_agents(repository)?);
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

#[derive(Debug)]
struct ManifestRow {
    path: String,
    variant: String,
    expected_count: u64,
    prompt_kind: String,
    step_markers: String,
}

fn manifest_rows(repository: &Repository) -> Result<Vec<ManifestRow>, LintError> {
    let manifest = RepoPath::from_trusted(MANIFEST_PATH);
    if repository.paths().binary_search(&manifest).is_err() {
        return Err(LintError::new(format!("manifest not found: {MANIFEST_PATH}")));
    }
    let source = repository.read_utf8(&manifest)?;
    source
        .lines()
        .enumerate()
        .filter(|(_, line)| !line.is_empty() && !line.starts_with('#'))
        .map(|(index, line)| parse_manifest_row(index + 1, line))
        .collect()
}

fn parse_manifest_row(number: usize, line: &str) -> Result<ManifestRow, LintError> {
    let mut fields = line.split('\t');
    let path = fields.next().unwrap_or_default();
    let variant = fields.next().unwrap_or_default();
    let expected_count = fields.next().unwrap_or_default();
    let prompt_kind = fields.next().unwrap_or_default();
    let step_markers = fields.next().unwrap_or_default();
    if path.is_empty() || variant.is_empty() {
        return Err(LintError::new(format!(
            "invalid manifest row {number} in {MANIFEST_PATH}: path and variant are required"
        )));
    }
    if expected_count.is_empty() || !expected_count.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(LintError::new(format!(
            "invalid expected_count in {MANIFEST_PATH} for row {path}"
        )));
    }
    let expected_count = expected_count.parse::<u64>().map_err(|_| {
        LintError::new(format!(
            "invalid expected_count in {MANIFEST_PATH} for row {path}"
        ))
    })?;
    Ok(ManifestRow {
        path: path.to_owned(),
        variant: variant.to_owned(),
        expected_count,
        prompt_kind: prompt_kind.to_owned(),
        step_markers: step_markers.to_owned(),
    })
}

fn validate_exemptions(rows: &[ManifestRow]) -> Result<Vec<&str>, LintError> {
    let mut exemptions = Vec::new();
    for row in rows {
        if row.variant != SKILL_EXEMPT {
            continue;
        }
        if row.expected_count != 0 || (row.prompt_kind.is_empty() && row.step_markers.is_empty()) {
            return Err(LintError::new(format!(
                "invalid skill exemption row for {}: expected_count must be 0 and reason required",
                row.path
            )));
        }
        exemptions.push(row.path.as_str());
    }
    Ok(exemptions)
}

fn check_floor(rows: &[ManifestRow]) -> Result<Vec<Finding>, LintError> {
    let floors: Vec<u64> = rows
        .iter()
        .filter(|row| row.variant == METADATA_FLOOR)
        .map(|row| row.expected_count)
        .collect();
    if floors.len() > 1 {
        return Ok(vec![finding(
            MANIFEST_PATH,
            "duplicate metadata-min-count rows",
        )]);
    }
    let Some(floor) = floors.first() else {
        return Ok(Vec::new());
    };
    let total = rows
        .iter()
        .filter(|row| matches!(row.variant.as_str(), ORCHESTRATOR_INLINE | EXTERNAL_PROMPT))
        .try_fold(0_u64, |total, row| total.checked_add(row.expected_count))
        .ok_or_else(|| LintError::new("manifest expected_count total exceeds u64"))?;
    if total >= *floor {
        Ok(Vec::new())
    } else {
        Ok(vec![finding(
            MANIFEST_PATH,
            format!("expected_count floor {floor} exceeds manifest total {total}"),
        )])
    }
}

fn check_counted_row(
    repository: &Repository,
    row: &ManifestRow,
) -> Result<Vec<Finding>, LintError> {
    let path = RepoPath::from_trusted(&row.path);
    if repository.paths().binary_search(&path).is_err() {
        return Ok(vec![finding(
            &row.path,
            format!("missing {} readability-style directive", row.variant),
        )]);
    }
    let source = repository.read_utf8(&path)?;
    match row.variant.as_str() {
        EXTERNAL_PROMPT => Ok(check_external_prompt(row, &source)),
        ORCHESTRATOR_INLINE => check_orchestrator(row, &source),
        _ => Ok(Vec::new()),
    }
}

fn check_external_prompt(row: &ManifestRow, source: &str) -> Vec<Finding> {
    let expected = if row.prompt_kind == "plan-review" {
        PLAN_REVIEW_STYLE_LINE
    } else {
        EXTERNAL_STYLE_LINE
    };
    let count = MarkdownDocument::new(source)
        .lines()
        .filter(|line| line.text() == expected)
        .count();
    count_finding(&row.path, row.expected_count, count, EXTERNAL_PROMPT)
}

fn check_orchestrator(row: &ManifestRow, source: &str) -> Result<Vec<Finding>, LintError> {
    let directive = directive_regex(style_path(&row.path))?;
    let count = MarkdownDocument::new(source)
        .lines()
        .filter(|line| directive.is_match(line.text()))
        .count();
    let mut findings = count_finding(&row.path, row.expected_count, count, ORCHESTRATOR_INLINE);
    if findings.is_empty() && !row.step_markers.is_empty() {
        findings.extend(check_step_placement(row, source));
    }
    Ok(findings)
}

fn count_finding(path: &str, expected: u64, actual: usize, variant: &str) -> Vec<Finding> {
    let actual = u64::try_from(actual).unwrap_or(u64::MAX);
    if actual == expected {
        Vec::new()
    } else {
        vec![finding(
            path,
            format!(
                "expected {expected} {variant} readability-style directives, found {actual}"
            ),
        )]
    }
}

fn check_step_placement(row: &ManifestRow, source: &str) -> Vec<Finding> {
    let lines: Vec<&str> = MarkdownDocument::new(source)
        .lines()
        .map(crate::syntax::MarkdownLine::text)
        .collect();
    row.step_markers
        .split(',')
        .map(str::trim)
        .filter(|step| !step.is_empty())
        .filter_map(|step| check_step(row, &lines, step))
        .collect()
}

fn check_step(row: &ManifestRow, lines: &[&str], step: &str) -> Option<Finding> {
    let marker = Regex::new(&format!(r"^<!--\s*step:{}(?:\s|:)", regex::escape(step)))
        .expect("step marker expression is valid");
    let anchor = format!("`{}`.**", style_path(&row.path));
    let mut active = false;
    let mut found_marker = false;
    let mut directive_count = 0_u64;
    for line in lines {
        if marker.is_match(line) {
            if active && directive_count == 0 {
                return Some(step_missing_finding(&row.path, step));
            }
            active = true;
            found_marker = true;
            directive_count = 0;
            continue;
        }
        if active && line.starts_with("<!-- step:") {
            if directive_count == 0 {
                return Some(step_missing_finding(&row.path, step));
            }
            active = false;
            directive_count = 0;
        }
        if active && line.contains(&anchor) {
            directive_count += 1;
        }
    }
    if !found_marker {
        Some(finding(
            &row.path,
            format!("step {step:?}: orchestrator-inline step marker not found"),
        ))
    } else if active && directive_count == 0 {
        Some(step_missing_finding(&row.path, step))
    } else {
        None
    }
}

fn step_missing_finding(path: &str, step: &str) -> Finding {
    finding(
        path,
        format!(
            "step {step:?}: expected >=1 orchestrator-inline readability-style directive in step body, found 0"
        ),
    )
}

fn check_skills(repository: &Repository, exemptions: &[&str]) -> Result<Vec<Finding>, LintError> {
    let selector = PathSelector::new(&["skills/*/SKILL.md", ".claude/skills/*/SKILL.md"], &[])?;
    let mut findings = Vec::new();
    for path in selector.select(repository) {
        if exemptions.contains(&path.as_str()) {
            continue;
        }
        let source = repository.read_utf8(path)?;
        findings.extend(check_style_path(
            path.as_str(),
            &source,
            "missing per-skill readability directive for",
        )?);
    }
    Ok(findings)
}

fn check_agents(repository: &Repository) -> Result<Vec<Finding>, LintError> {
    let selector = PathSelector::new(&["agents/code-reviewer.md", "agents/reviewer-*.md"], &[])?;
    let mut findings = Vec::new();
    for path in selector.select(repository) {
        let source = repository.read_utf8(path)?;
        findings.extend(check_style_path(
            path.as_str(),
            &source,
            "missing reviewer readability directive for",
        )?);
    }
    Ok(findings)
}

fn check_style_path(path: &str, source: &str, missing: &str) -> Result<Vec<Finding>, LintError> {
    let expected = style_path(path);
    let forbidden = if expected == DEV_STYLE_PATH {
        PUBLIC_STYLE_PATH
    } else {
        DEV_STYLE_PATH
    };
    let directive = directive_regex(expected)?;
    let document = MarkdownDocument::new(source);
    let mut findings = Vec::new();
    if !document.lines().any(|line| directive.is_match(line.text())) {
        findings.push(finding(path, format!("{missing} {expected}")));
    }
    if source.contains(forbidden) {
        findings.push(finding(path, "uses wrong readability directive path form"));
    }
    Ok(findings)
}

fn style_path(path: &str) -> &'static str {
    if path.starts_with(".claude/skills/") {
        DEV_STYLE_PATH
    } else {
        PUBLIC_STYLE_PATH
    }
}

fn directive_regex(style_path: &str) -> Result<Regex, LintError> {
    Regex::new(&format!(
        r"(?i)^\*\*MANDATORY:\s+READ\s+ENTIRE\s+FILE.*`{}`\.\*\*$",
        regex::escape(style_path)
    ))
    .map_err(|error| LintError::new(format!("cannot compile readability directive expression: {error}")))
}

fn finding(path: &str, message: impl Into<String>) -> Finding {
    Finding::new(path, 1, message)
}
