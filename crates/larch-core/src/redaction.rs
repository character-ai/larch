//! Deterministic redaction for text crossing an observability or error boundary.

use regex::Regex;
use std::{collections::BTreeMap, fmt, sync::LazyLock};

const REDACTED_TOKEN: &str = "<REDACTED-TOKEN>";
const REDACTED_PRIVATE_KEY: &str = "<REDACTED-PRIVATE-KEY>";
const REDACTION_FAILURE: &str = "[content withheld: redaction verification failed]";
const UNTERMINATED_PEM: &str =
    "[content truncated: unterminated PEM block; tail of body dropped for safety]";

struct SecretFamily {
    name: &'static str,
    pattern: Regex,
}

impl SecretFamily {
    fn new(name: &'static str, pattern: &str) -> Self {
        Self {
            name,
            pattern: Regex::new(pattern).expect("static secret regex must compile"),
        }
    }
}

static SECRET_FAMILIES: LazyLock<Vec<SecretFamily>> = LazyLock::new(|| {
    vec![
        SecretFamily::new("anthropic-openai-key", r"sk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
        SecretFamily::new(
            "github-token",
            r"(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}",
        ),
        SecretFamily::new("aws-akia", r"AKIA[0-9A-Z]{16}"),
        SecretFamily::new(
            "jwt",
            r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        ),
        SecretFamily::new("pem-private-key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        SecretFamily::new(
            "cursor-api-key",
            r"(?:crsr_[A-Za-z0-9_-]{20,}|key_[A-Za-z0-9]{32,})",
        ),
        SecretFamily::new("slack-token", r"xox[baprs]-[A-Za-z0-9-]{10,}"),
        SecretFamily::new("google-api-key", r"AIza[0-9A-Za-z_-]{35}"),
        SecretFamily::new("stripe-live-key", r"(?:sk|rk)_live_[0-9A-Za-z]{16,}"),
        SecretFamily::new("gitlab-pat", r"glpat-[0-9A-Za-z_-]{20,}"),
    ]
});

static PEM_BEGIN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[\t \x0b\x0c\r>]*-----BEGIN [A-Z ]*PRIVATE KEY-----")
        .expect("static PEM begin regex must compile")
});
static PEM_END: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[\t \x0b\x0c\r>]*-----END [A-Z ]*PRIVATE KEY-----")
        .expect("static PEM end regex must compile")
});

struct PathPattern {
    pattern: Regex,
    replacement: &'static str,
}

impl PathPattern {
    fn new(pattern: &str, replacement: &'static str) -> Self {
        Self {
            pattern: Regex::new(pattern).expect("static path regex must compile"),
            replacement,
        }
    }
}

static PATH_PATTERNS: LazyLock<Vec<PathPattern>> = LazyLock::new(|| {
    let session =
        r"(?:claude|larch)-(?:implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_.-]+";
    let boundary = r"[^A-Za-z0-9_./-]";
    let not_path = r#"[^/\s"\\]"#;
    let mut patterns = vec![
        PathPattern::new(
            &format!(
                r#"(?m)(^|{boundary})/(?:private/)?tmp/+(?:{not_path}+/)*larch-report-tokens[.-][^/\s"\\]+"#
            ),
            "$1<TMPDIR>",
        ),
        PathPattern::new(
            &format!(
                r#"(?m)(^|{boundary})/(?:private/)?var/folders/[^/]+/[^/]+/T/(?:{not_path}+/)*larch-report-tokens[.-][^/\s"\\]+"#
            ),
            "$1<TMPDIR>",
        ),
        PathPattern::new(
            &format!(r"(?m)(^|{boundary})/(?:private/)?tmp/+(?:{not_path}+/)*{session}"),
            "$1<TMPDIR>",
        ),
        PathPattern::new(
            &format!(
                r"(?m)(^|{boundary})/(?:private/)?var/folders/[^/]+/[^/]+/T/(?:{not_path}+/)*{session}"
            ),
            "$1<TMPDIR>",
        ),
        PathPattern::new(
            &format!(r"(?m)(^|{boundary})/(?:{not_path}+/)*larch/sessions/{session}"),
            "$1<TMPDIR>",
        ),
        PathPattern::new(
            &format!(r"(?m)(\\n)/(?:{not_path}+/)*larch/sessions/{session}"),
            "$1<TMPDIR>",
        ),
        PathPattern::new(
            &format!(r"(?m)(\\n)/(?:private/)?tmp/+(?:{not_path}+/)*{session}"),
            "$1<TMPDIR>",
        ),
        PathPattern::new(
            &format!(
                r"(?m)(\\n)/(?:private/)?var/folders/[^/]+/[^/]+/T/(?:{not_path}+/)*{session}"
            ),
            "$1<TMPDIR>",
        ),
    ];
    let operator_specs = [
        (r#"[^/\s"\\]+/"#, "$1<OPERATOR_REPO_PATH>/"),
        (r#"[^/\s"\\,]+,"#, "$1<OPERATOR_REPO_PATH>,"),
        (r#"[^/\s"\\;]+;"#, "$1<OPERATOR_REPO_PATH>;"),
        (r#"[^/\s"\\:]+:"#, "$1<OPERATOR_REPO_PATH>:"),
        (r#"[^/\s"\\}]+"\}"#, "$1<OPERATOR_REPO_PATH>\"}"),
        (r#"[^/\s"\\},]+","#, "$1<OPERATOR_REPO_PATH>\","),
        (r#"[^/\s"\\]+"$"#, "$1<OPERATOR_REPO_PATH>"),
        (r#"[^/\s"\\]+$"#, "$1<OPERATOR_REPO_PATH>"),
    ];
    for prefix in [format!(r"(?m)(^|{boundary})"), String::from(r"(?m)(\\n)")] {
        for (repo_and_suffix, replacement) in operator_specs {
            patterns.push(PathPattern::new(
                &format!(r#"{prefix}(?:/Users|/home)/[^/\s"\\]+/{repo_and_suffix}"#),
                replacement,
            ));
        }
    }
    patterns
});

/// Redacted text plus deterministic occurrence counts from the original input.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RedactionResult {
    text: String,
    findings: BTreeMap<&'static str, usize>,
}

impl RedactionResult {
    /// Borrow the redacted text.
    #[must_use]
    pub fn text(&self) -> &str {
        &self.text
    }

    /// Return secret-family counts from the original input.
    #[must_use]
    pub const fn findings(&self) -> &BTreeMap<&'static str, usize> {
        &self.findings
    }
}

/// Text safe to display, persist, or include in an external diagnostic.
///
/// The only constructor treats its input as untrusted. If a second scan finds
/// a secret after scrubbing, the complete value is replaced by a fixed marker.
#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub struct SafeText(String);

impl SafeText {
    /// Redact untrusted process, service, repository, or workflow text.
    #[must_use]
    pub fn from_untrusted(text: impl AsRef<str>) -> Self {
        let first = redact(text.as_ref());
        let candidate = first.text;
        let verification = redact_secrets(&candidate);
        if verification.findings.is_empty() {
            Self(candidate)
        } else {
            Self(String::from(REDACTION_FAILURE))
        }
    }

    /// Redact untrusted text and remove terminal control bytes for one diagnostic line.
    #[must_use]
    pub fn diagnostic(text: impl AsRef<str>) -> Self {
        let line: String = text
            .as_ref()
            .chars()
            .filter(|character| *character >= ' ' && *character != '\u{7f}')
            .collect();
        Self::from_untrusted(line)
    }

    /// Borrow the safe text.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for SafeText {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

/// Redact every supported secret family while preserving newline intent.
#[must_use]
pub fn redact_secrets(text: &str) -> RedactionResult {
    let findings = count_secret_families(text);
    let pem_scrubbed = redact_pem_blocks(text);
    let mut scrubbed = pem_scrubbed;
    for family in SECRET_FAMILIES
        .iter()
        .filter(|family| family.name != "pem-private-key")
    {
        scrubbed = family
            .pattern
            .replace_all(&scrubbed, REDACTED_TOKEN)
            .into_owned();
    }
    RedactionResult {
        text: scrubbed,
        findings,
    }
}

/// Redact session temporary directories and operator repository roots.
#[must_use]
pub fn redact_sensitive_paths(text: &str) -> String {
    let mut scrubbed = String::from(text);
    for pattern in PATH_PATTERNS.iter() {
        scrubbed = pattern
            .pattern
            .replace_all(&scrubbed, pattern.replacement)
            .into_owned();
    }
    scrubbed
}

/// Redact sensitive paths first, then all secret families.
#[must_use]
pub fn redact(text: &str) -> RedactionResult {
    let path_scrubbed = redact_sensitive_paths(text);
    redact_secrets(&path_scrubbed)
}

fn count_secret_families(text: &str) -> BTreeMap<&'static str, usize> {
    let mut findings = BTreeMap::new();
    for family in SECRET_FAMILIES.iter() {
        let count = family.pattern.find_iter(text).count();
        if count != 0 {
            findings.insert(family.name, count);
        }
    }
    findings
}

fn redact_pem_blocks(text: &str) -> String {
    let mut output = String::new();
    let mut in_pem = false;
    for line in text.split_inclusive('\n') {
        let logical = line.strip_suffix('\n').unwrap_or(line);
        if in_pem {
            if PEM_END.is_match(logical) {
                in_pem = false;
            }
            continue;
        }
        if PEM_BEGIN.is_match(logical) {
            output.push_str(REDACTED_PRIVATE_KEY);
            if line.ends_with('\n') {
                output.push('\n');
            }
            in_pem = true;
        } else {
            output.push_str(line);
        }
    }
    if in_pem {
        if output.is_empty() || output.ends_with('\n') {
            output.push_str(UNTERMINATED_PEM);
            output.push('\n');
        } else {
            output.push_str(UNTERMINATED_PEM);
        }
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_fixture_family_is_counted_and_redacted() {
        for row in include_str!("../../../fixtures/rust-redaction/secret-families.tsv").lines() {
            if row.is_empty() || row.starts_with('#') {
                continue;
            }
            let mut columns = row.splitn(3, '\t');
            let name = columns.next().expect("fixture family should exist");
            let prefix = columns.next().expect("fixture prefix should exist");
            let suffix = columns.next().expect("fixture suffix should exist");
            let secret = format!("{prefix}{suffix}");

            let input = if name == "pem-private-key" {
                secret.clone()
            } else {
                format!("before {secret} after")
            };
            let result = redact_secrets(&input);

            assert_eq!(result.findings().get(name), Some(&1), "family {name}");
            assert!(!result.text().contains(&secret), "family {name}");
        }
    }

    #[test]
    fn path_fixture_matches_python_contract() {
        for row in include_str!("../../../fixtures/rust-redaction/sensitive-paths.tsv").lines() {
            if row.is_empty() || row.starts_with('#') {
                continue;
            }
            let (raw, expected) = row
                .split_once('\t')
                .expect("fixture should have two columns");
            let input = raw.replace(r"\n", "\n");
            let expected = expected.replace(r"\n", "\n");

            assert_eq!(redact_sensitive_paths(&input), expected, "input {raw}");
        }
    }

    #[test]
    fn pem_blocks_are_swallowed_and_unterminated_tails_fail_closed() {
        let input = "opening\n> -----BEGIN RSA PRIVATE KEY-----\nsecret body\ntail-secret-value";
        let result = redact_secrets(input);

        assert!(result.text().contains(REDACTED_PRIVATE_KEY));
        assert!(result.text().contains("content truncated"));
        assert!(!result.text().contains("secret body"));
        assert!(!result.text().contains("tail-secret-value"));
    }

    #[test]
    fn redaction_is_idempotent_and_paths_run_before_tokens() {
        let input = "/tmp/claude-implement-sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD/file";
        let once = redact(input).text().to_owned();
        let twice = redact(&once).text().to_owned();

        assert_eq!(once, "<TMPDIR>/file");
        assert_eq!(twice, once);
    }

    #[test]
    fn safe_text_scrubs_all_external_text_families() {
        let raw = ["service returned ", "xox", "b-1234567890-abcdefghijklmnop"].concat();
        let safe = SafeText::from_untrusted(&raw);

        assert_eq!(safe.as_str(), "service returned <REDACTED-TOKEN>");
        assert!(!safe.as_str().contains(&raw));
    }

    #[test]
    fn diagnostic_text_removes_terminal_controls_and_line_forgery() {
        let safe = SafeText::diagnostic("bad\u{1b}[31m\nforged\u{7f}");

        assert_eq!(safe.as_str(), "bad[31mforged");
    }
}
