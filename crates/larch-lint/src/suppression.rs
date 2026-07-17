//! Reason-bearing, same-line lint suppression parsing.

use crate::LintError;

/// A validated inline suppression reason.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SuppressionReason<'source>(&'source str);

impl<'source> SuppressionReason<'source> {
    /// Return the non-empty operator-facing reason.
    #[must_use]
    pub const fn as_str(self) -> &'source str {
        self.0
    }
}

/// Read a same-line `lint-<rule>: ok <reason>` suppression from a comment.
///
/// # Errors
///
/// Returns an error when the suppression token is present but its reason is
/// absent. A missing token returns `Ok(None)`.
pub fn reason<'source>(
    line: &'source str,
    token: &str,
) -> Result<Option<SuppressionReason<'source>>, LintError> {
    let Some(offset) = line.find(token) else {
        return Ok(None);
    };
    let before = &line[..offset];
    if !before.contains('#') && !before.contains("//") && !before.contains("<!--") {
        return Ok(None);
    }
    let tail = &line[offset + token.len()..];
    let Some(reason) = tail.strip_prefix(": ok") else {
        return Ok(None);
    };
    let reason = reason.trim().trim_end_matches("-->").trim();
    if reason.is_empty() {
        return Err(LintError::new(format!(
            "suppression {token} lacks a reason"
        )));
    }
    Ok(Some(SuppressionReason(reason)))
}

#[cfg(test)]
mod tests {
    use super::reason;

    #[test]
    fn requires_a_reason_in_comment_forms() {
        assert_eq!(
            reason("// lint-demo: ok fixture exception", "lint-demo")
                .expect("valid suppression")
                .expect("suppressed")
                .as_str(),
            "fixture exception"
        );
        assert_eq!(
            reason("<!-- lint-demo: ok documented exception -->", "lint-demo")
                .expect("valid suppression")
                .expect("suppressed")
                .as_str(),
            "documented exception"
        );
        assert!(reason("# lint-demo: ok", "lint-demo").is_err());
    }

    #[test]
    fn ignores_tokens_outside_comments() {
        assert_eq!(
            reason("let value = lint-demo: ok", "lint-demo").expect("not a comment"),
            None
        );
    }
}
