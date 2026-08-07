//! The untrusted content-block envelope.
//!
//! Ports the untrusted half of `larch.issue.issue_wire`. Fetched issue text is
//! attacker controlled, so it is redacted first and only then escaped, and the
//! escape runs before the text is placed inside an XML-ish tag a prompt reader
//! treats as a boundary.

use crate::redaction::redact_run_log_payload;

/// Escape a value for an XML attribute.
#[must_use]
pub fn xml_escape_attr(text: &str) -> String {
    text.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

/// Redact secrets and sensitive paths, then escape the markup delimiters.
///
/// Matches Python `html.escape(redact(text), quote=False)`: redaction runs
/// first so a secret can never survive as escaped text, and `&` is escaped
/// before `<` and `>` so an escape is never double applied.
///
/// Python's `redact.redact` is line oriented and terminates a non-empty result
/// with one newline, which is the shape [`redact_run_log_payload`] owns.
#[must_use]
pub fn redact_untrusted_stream(text: &str) -> String {
    redact_run_log_payload(text)
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
}

/// Wrap untrusted text in a labelled, redacted content block.
///
/// The `encoding="literal-redacted"` attribute tells a prompt reader that the
/// contents are data, never instructions.
#[must_use]
pub fn untrusted_content_block(tag: &str, text: &str) -> String {
    format!(
        "<{tag} encoding=\"literal-redacted\">\n{}\n</{tag}>\n\n",
        redact_untrusted_stream(text)
    )
}
