//! Shared Rust source scan support for rules with reason-bearing suppressions.

use crate::{Finding, LintError, suppression, syntax::RustSyntax};

/// Parse Rust source, collect line/message pairs, and apply same-line suppressions.
///
/// Unparseable Rust is skipped to preserve the compatibility rule behavior.
pub(super) fn findings(
    path: &str,
    source: &str,
    suppression_token: &str,
    collect: impl FnOnce(&syn::File) -> Vec<(usize, String)>,
) -> Result<Vec<Finding>, LintError> {
    let Ok(syntax) = RustSyntax::parse(path, source) else {
        return Ok(Vec::new());
    };
    let mut findings = Vec::new();
    for (line, message) in collect(syntax.file()) {
        let number = suppression::number_unless_suppressed(source, line, suppression_token)
            .map_err(|error| LintError::new(format!("{path}: {error}")))?;
        if let Some(number) = number {
            findings.push(Finding::new(path, number, message));
        }
    }
    Ok(findings)
}
