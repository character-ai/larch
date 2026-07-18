//! Reject case-variant lifecycle and bug title-prefix tokens on text surfaces.
//!
//! This ports the Python `prefix-case-variant` rule. It scans Markdown prompt
//! surfaces and the declared residual Bash inventory, preserving the canonical
//! lifecycle and bug-prefix owner shared with `lifecycle-prefix-literal`.

use std::sync::LazyLock;

use regex::Regex;

use super::lifecycle_prefix::PREFIXES;
use crate::{Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "prefix-case-variant";
const DESCRIPTION: &str = "Reject case-variant lifecycle and bug title-prefix tokens";
const MANIFEST_PATH: &str = "scripts/residual-bash-paths.txt";
const MARKDOWN_ROOTS: [&str; 3] = ["skills/", ".claude/skills/", "agents/"];
const EXCLUDED_PREFIXES: [&str; 2] = ["larch-logs/", "node_modules/"];

static BRACKET_TOKEN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\[[^\[\]]+\]").expect("bracket token expression is valid")
});
static MARKDOWN_SUPPRESSION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"<!--\s*lint-prefix-case-variant:\s*ok\s+(\S.*?)\s*-->\s*$")
        .expect("Markdown suppression expression is valid")
});
static BASH_SUPPRESSION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"#\s*lint-prefix-case-variant:\s*ok\s+(\S.*)$")
        .expect("Bash suppression expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/prefix-case-variant.toml",
);

#[derive(Debug)]
pub struct PrefixCaseVariantRule;

pub static RULE: PrefixCaseVariantRule = PrefixCaseVariantRule;

#[derive(Clone, Copy)]
enum Surface {
    Markdown,
    Bash,
}

impl Surface {
    fn suppressed(self, line: &str) -> bool {
        match self {
            Self::Markdown => MARKDOWN_SUPPRESSION.is_match(line),
            Self::Bash => BASH_SUPPRESSION.is_match(line),
        }
    }
}

impl Rule for PrefixCaseVariantRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let markdown = PathSelector::new(&["**/*.md"], &[])?;
        let mut findings = Vec::new();
        for path in markdown.select(repository) {
            if MARKDOWN_ROOTS
                .iter()
                .any(|root| path.as_str().starts_with(root))
            {
                findings.extend(scan_source(path.as_str(), &repository.read_utf8(path)?, Surface::Markdown)?);
            }
        }
        for path in residual_bash_paths(repository)? {
            findings.extend(scan_source(path.as_str(), &repository.read_utf8(&path)?, Surface::Bash)?);
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

fn residual_bash_paths(repository: &Repository) -> Result<Vec<RepoPath>, LintError> {
    let manifest = RepoPath::from_trusted(MANIFEST_PATH);
    let source = repository.read_required_utf8(
        &manifest,
        format!("could not read residual bash manifest: {MANIFEST_PATH}"),
    )?;
    let mut paths = Vec::new();
    for (index, line) in source.lines().enumerate() {
        let raw = line.trim();
        if raw.is_empty() || raw.starts_with('#') {
            continue;
        }
        validate_residual_path(raw, index + 1)?;
        if paths.iter().any(|path: &RepoPath| path.as_str() == raw) {
            return Err(LintError::new(format!(
                "duplicate residual bash path at {MANIFEST_PATH}:{}: {raw}",
                index + 1
            )));
        }
        let path = RepoPath::from_trusted(raw);
        if repository.paths().binary_search(&path).is_err() {
            return Err(LintError::new(format!("missing residual bash path: {raw}")));
        }
        paths.push(path);
    }
    Ok(paths)
}

fn validate_residual_path(raw: &str, line: usize) -> Result<(), LintError> {
    if raw.starts_with('/') || raw.contains('\0') || raw.split('/').any(|part| part == "..") {
        return Err(LintError::new(format!("invalid residual bash path: {raw:?}")));
    }
    if EXCLUDED_PREFIXES.iter().any(|prefix| raw.starts_with(prefix)) {
        return Err(LintError::new(format!("excluded residual bash path: {raw:?}")));
    }
    if raw.strip_suffix(".sh").is_none() && raw.strip_suffix(".inc.bash").is_none() {
        return Err(LintError::new(format!(
            "{MANIFEST_PATH}:{line}: residual bash path must end with .sh or .inc.bash: {raw:?}",
        )));
    }
    Ok(())
}

fn scan_source(path: &str, source: &str, surface: Surface) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    for (index, line) in source.lines().enumerate() {
        if surface.suppressed(line) {
            continue;
        }
        let line_number = u32::try_from(index + 1)
            .map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))?;
        for matched in BRACKET_TOKEN.find_iter(line) {
            let observed = matched.as_str();
            let Some(canonical) = PREFIXES
                .iter()
                .copied()
                .find(|prefix| observed.eq_ignore_ascii_case(prefix))
            else {
                continue;
            };
            if observed != canonical {
                findings.push(Finding::new(
                    path,
                    line_number,
                    format!("matched {observed}; use exact-case {canonical}"),
                ));
            }
        }
    }
    Ok(findings)
}

crate::register_rule!(METADATA, RULE);

#[cfg(test)]
mod tests {
    use super::{Surface, scan_source};

    #[test]
    fn flags_case_variants_and_allows_exact_tokens() {
        let source = "[Bug] [bug] [BUG] [feature]";
        let findings = scan_source("fixture.md", source, Surface::Markdown).expect("scan");
        assert_eq!(findings.len(), 2);
        assert_eq!(findings[0].to_string(), "fixture.md:1: matched [Bug]; use exact-case [BUG]");
        assert_eq!(findings[1].to_string(), "fixture.md:1: matched [bug]; use exact-case [BUG]");
    }

    #[test]
    fn requires_reason_bearing_surface_specific_suppressions() {
        assert!(scan_source(
            "fixture.md",
            "[Bug] <!-- lint-prefix-case-variant: ok fixture -->",
            Surface::Markdown
        )
        .expect("scan")
        .is_empty());
        assert_eq!(
            scan_source(
                "fixture.sh",
                "printf '%s\\n' '[bug]' # lint-prefix-case-variant: ok",
                Surface::Bash
            )
            .expect("scan")
            .len(),
            1
        );
    }
}
