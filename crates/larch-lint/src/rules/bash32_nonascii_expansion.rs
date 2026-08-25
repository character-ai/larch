//! Reject bare shell variables immediately followed by non-ASCII text.
//!
//! macOS Bash 3.2 can consume the first UTF-8 byte after `$name` as part of
//! the variable name. Braced expansion fixes the boundary. This rule scans
//! every committed shell source and executable Bash fence, while ignoring
//! single-quoted literals and shell comments.

use crate::{
    Finding, LintError, PathSelector, Repository, Rule, RuleMetadata, RuleOutput,
    suppression::reason,
    syntax::{FenceState, MarkdownDocument, parse_bash},
};

const NAME: &str = "bash32-nonascii-expansion";
const DESCRIPTION: &str = "Require braces before non-ASCII text in Bash 3.2 variable expansions";
const SUPPRESSION_TOKEN: &str = "lint-bash32-nonascii-expansion";
const MESSAGE: &str =
    "bare $name immediately before non-ASCII text is unsafe on Bash 3.2; use ${name}";

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/bash32-nonascii-expansion.toml",
);

#[derive(Debug)]
pub struct Bash32NonasciiExpansionRule;

pub static RULE: Bash32NonasciiExpansionRule = Bash32NonasciiExpansionRule;

impl Rule for Bash32NonasciiExpansionRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let shell = PathSelector::new(
            &["**/*.sh", "**/*.inc.bash"],
            &["larch-logs/**", "node_modules/**"],
        )?;
        let markdown = PathSelector::new(
            &["**/*.md"],
            &["larch-logs/**", "node_modules/**"],
        )?;
        let mut findings = Vec::new();
        for path in shell.select(repository) {
            findings.extend(scan_shell(
                path.as_str(),
                &repository.read_utf8(path)?,
                0,
            )?);
        }
        for path in markdown.select(repository) {
            findings.extend(scan_markdown(
                path.as_str(),
                &repository.read_utf8(path)?,
            )?);
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

fn scan_shell(path: &str, source: &str, line_offset: usize) -> Result<Vec<Finding>, LintError> {
    let bytes = source.as_bytes();
    let lines: Vec<&str> = source.lines().collect();
    let mut findings = Vec::new();
    let syntax = parse_bash(source)?;
    let mut pending = vec![syntax.root_node()];
    while let Some(node) = pending.pop() {
        if node.kind() == "simple_expansion" && unsafe_boundary(node, bytes) {
            let line = node.start_position().row + 1;
            let source_line = lines.get(line - 1).copied().unwrap_or("");
            if reason(source_line, SUPPRESSION_TOKEN)?.is_none() {
                let number = u32::try_from(line_offset + line)
                    .map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))?;
                findings.push(Finding::new(path, number, MESSAGE));
            }
        }
        let mut cursor = node.walk();
        pending.extend(node.children(&mut cursor));
    }
    findings.sort();
    findings.dedup();
    Ok(findings)
}

/// Detect the ASCII variable prefix even when a parser includes the following
/// UTF-8 bytes in the expansion node, as macOS Bash 3.2 itself does.
fn unsafe_boundary(node: tree_sitter::Node<'_>, source: &[u8]) -> bool {
    let start = node.start_byte();
    let end = node.end_byte();
    if source.get(start) != Some(&b'$') {
        return false;
    }
    let mut boundary = start + 1;
    if !source
        .get(boundary)
        .is_some_and(|byte| byte.is_ascii_alphabetic() || *byte == b'_')
    {
        return false;
    }
    boundary += 1;
    while source
        .get(boundary)
        .is_some_and(|byte| byte.is_ascii_alphanumeric() || *byte == b'_')
    {
        boundary += 1;
    }
    boundary <= end && source.get(boundary).is_some_and(|byte| !byte.is_ascii())
}

fn scan_markdown(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    let mut block = String::new();
    let mut block_start = 0_usize;
    for line in MarkdownDocument::new(source).lines() {
        let inside_shell = matches!(
            line.fence_state(),
            FenceState::Inside { language: Some(language) } if is_shell(language)
        ) && !line.is_fence_boundary();
        if inside_shell {
            if block.is_empty() {
                block_start = line.number().saturating_sub(1);
            }
            block.push_str(line.text());
            block.push('\n');
        } else if !block.is_empty() {
            findings.extend(scan_shell(path, &block, block_start)?);
            block.clear();
        }
    }
    if !block.is_empty() {
        findings.extend(scan_shell(path, &block, block_start)?);
    }
    Ok(findings)
}

const fn is_shell(language: &str) -> bool {
    language.eq_ignore_ascii_case("bash")
        || language.eq_ignore_ascii_case("sh")
        || language.eq_ignore_ascii_case("shell")
}

#[cfg(test)]
mod tests {
    use super::{scan_markdown, scan_shell};

    #[test]
    fn scanner_distinguishes_unsafe_expansion_from_safe_boundaries_and_literals() {
        let source = concat!(
            "i=3\n",
            "printf '%s\\n' \"$i…\"\n",
            "printf '%s\\n' \"${i}…\" \"$i...\"\n",
            "printf '%s\\n' '$i…'\n",
            "# printf '%s\\n' \"$i…\"\n",
            "printf '%s\\n' \"$(printf '%s' '$nested…')\"\n",
        );
        let findings = scan_shell("fixture.sh", source, 0).expect("scan");
        assert_eq!(findings.len(), 1);
        assert_eq!(
            findings[0].to_string(),
            "fixture.sh:2: bare $name immediately before non-ASCII text is unsafe on Bash 3.2; use ${name}"
        );
    }

    #[test]
    fn scanner_descends_into_active_command_substitutions() {
        let source = "printf '%s\\n' \"$(printf '%s' \"$nested…\")\"\n";
        let findings = scan_shell("fixture.sh", source, 0).expect("scan");
        assert_eq!(findings.len(), 1);
        assert!(findings[0].to_string().starts_with("fixture.sh:1:"));
    }

    #[test]
    fn markdown_scanner_reads_only_executable_shell_fences() {
        let source = concat!(
            "`$outside…`\n",
            "```text\n$item…\n```\n",
            "```bash\nprintf '%s\\n' \"$item→\"\n```\n",
        );
        let findings = scan_markdown("fixture.md", source).expect("scan");
        assert_eq!(findings.len(), 1);
        assert_eq!(
            findings[0].to_string(),
            "fixture.md:6: bare $name immediately before non-ASCII text is unsafe on Bash 3.2; use ${name}"
        );
    }
}
