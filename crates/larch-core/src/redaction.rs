//! Deterministic redaction for text crossing an observability or error boundary.

use crate::review::{BoundaryMode, ItemKind, parse_blocks};
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
    ]
});

static EXTRA_SECRET_FAMILIES: LazyLock<Vec<SecretFamily>> = LazyLock::new(|| {
    vec![
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

/// Session-tmpdir patterns only. Operator repository roots are deliberately
/// excluded: callers use these to detect a *session* pointer that must never be
/// persisted, and an operator path is redacted rather than refused.
static SESSION_TMPDIR_PATTERNS: LazyLock<Vec<PathPattern>> = LazyLock::new(|| {
    let session =
        r"(?:claude|larch)-(?:implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_.-]+";
    let boundary = r"[^A-Za-z0-9_./-]";
    let not_path = r#"[^/\s"\\]"#;
    vec![
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
    ]
});

/// Operator repository-root patterns applied after the session-tmpdir set.
static OPERATOR_PATH_PATTERNS: LazyLock<Vec<PathPattern>> = LazyLock::new(|| {
    let boundary = r"[^A-Za-z0-9_./-]";
    let mut patterns = Vec::new();
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

/// One PEM-aware streaming redaction pass and its carry state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StreamingRedactionResult {
    text: String,
    in_pem: bool,
}

impl StreamingRedactionResult {
    /// Borrow the redacted chunk.
    #[must_use]
    pub fn text(&self) -> &str {
        &self.text
    }

    /// Return whether the next chunk starts inside a private-key block.
    #[must_use]
    pub const fn in_pem(&self) -> bool {
        self.in_pem
    }
}

/// Finding text with submodule-owned findings removed plus an audit projection.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SubmoduleScrubResult {
    text: String,
    audit: String,
    count: usize,
}

impl SubmoduleScrubResult {
    /// Borrow the retained finding text.
    #[must_use]
    pub fn text(&self) -> &str {
        &self.text
    }

    /// Borrow the removed finding headings, one per line.
    #[must_use]
    pub fn audit(&self) -> &str {
        &self.audit
    }

    /// Return the number of removed findings.
    #[must_use]
    pub const fn count(&self) -> usize {
        self.count
    }
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

/// Invocation-owned exact-secret registry layered over family redaction.
///
/// This type intentionally has no `Debug` implementation. Registering the
/// exact runtime credential covers tokens whose format matches no known
/// prefix without introducing global mutable state between concurrent runs.
#[derive(Default)]
pub struct RuntimeRedactor {
    exact_secrets: Vec<Box<str>>,
}

impl RuntimeRedactor {
    /// Register one non-empty exact value. Returns false for an empty value.
    pub fn register_exact_secret(&mut self, secret: impl Into<String>) -> bool {
        let secret = secret.into();
        if secret.is_empty() {
            return false;
        }
        if !self
            .exact_secrets
            .iter()
            .any(|known| known.as_ref() == secret)
        {
            self.exact_secrets.push(secret.into_boxed_str());
            self.exact_secrets
                .sort_unstable_by_key(|value| std::cmp::Reverse(value.len()));
        }
        true
    }

    /// Redact registered exact values, sensitive paths, and known families.
    #[must_use]
    pub fn redact(&self, text: &str) -> RedactionResult {
        let mut exact_count = 0_usize;
        let mut scrubbed = String::from(text);
        for secret in &self.exact_secrets {
            exact_count += scrubbed.matches(secret.as_ref()).count();
            scrubbed = scrubbed.replace(secret.as_ref(), REDACTED_TOKEN);
        }
        let mut result = redact(&scrubbed);
        if exact_count != 0 {
            result.findings.insert("runtime-exact", exact_count);
        }
        result
    }

    /// Produce display-safe text with exact runtime values removed first.
    #[must_use]
    pub fn safe_text(&self, text: impl AsRef<str>) -> SafeText {
        let candidate = self.redact(text.as_ref()).text;
        let verified = self.redact(&candidate);
        if verified.findings.is_empty() {
            SafeText(candidate)
        } else {
            SafeText(String::from(REDACTION_FAILURE))
        }
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
        .chain(EXTRA_SECRET_FAMILIES.iter())
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

/// Redact the Python `redact_secrets_only` profile: base secret families only.
#[must_use]
pub fn redact_secrets_only(text: &str) -> String {
    let mut scrubbed = redact_pem_blocks(text);
    for family in SECRET_FAMILIES
        .iter()
        .filter(|family| family.name != "pem-private-key")
    {
        scrubbed = family
            .pattern
            .replace_all(&scrubbed, REDACTED_TOKEN)
            .into_owned();
    }
    if !scrubbed.is_empty() && !scrubbed.ends_with('\n') {
        scrubbed.push('\n');
    }
    scrubbed
}

/// Redact one stream chunk while carrying PEM state across invocations.
#[must_use]
pub fn redact_secrets_streaming(text: &str, mut in_pem: bool) -> StreamingRedactionResult {
    let mut output = String::new();
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
            output.push_str(&redact_base_line(line));
        }
    }
    StreamingRedactionResult {
        text: output,
        in_pem,
    }
}

/// Remove finding blocks that mention a discovered submodule as a complete path token.
#[must_use]
pub fn scrub_submodule_findings(text: &str, submodules: &[String]) -> SubmoduleScrubResult {
    let mut ordered = submodules
        .iter()
        .filter(|path| !path.is_empty())
        .cloned()
        .collect::<Vec<_>>();
    ordered.sort_by_key(|path| std::cmp::Reverse(path.len()));
    let mut output = String::new();
    let mut audit = String::new();
    let mut previous_end = 0;
    let mut count = 0;
    for parsed in parse_blocks(text, BoundaryMode::ItemHeading) {
        let start = byte_offset(text, parsed.start);
        let end = byte_offset(text, parsed.end);
        output.push_str(&text[previous_end..start]);
        previous_end = end;
        if parsed.kind != ItemKind::Finding
            || !ordered
                .iter()
                .any(|path| contains_complete_path_token(&parsed.block, path))
        {
            output.push_str(&parsed.block);
            continue;
        }
        count += 1;
        if let Some(heading) = parsed.block.lines().next() {
            audit.push_str(heading);
            audit.push('\n');
        }
    }
    output.push_str(&text[previous_end..]);
    SubmoduleScrubResult {
        text: output,
        audit,
        count,
    }
}

/// Redact session temporary directories and operator repository roots.
#[must_use]
pub fn redact_sensitive_paths(text: &str) -> String {
    let mut scrubbed = String::from(text);
    for pattern in SESSION_TMPDIR_PATTERNS
        .iter()
        .chain(&*OPERATOR_PATH_PATTERNS)
    {
        scrubbed = pattern
            .pattern
            .replace_all(&scrubbed, pattern.replacement)
            .into_owned();
    }
    scrubbed
}

/// True when `text` carries a recognized session-tmpdir pointer.
///
/// Operator repository paths do not count: they are redacted downstream, while
/// a session pointer is refused outright by the batches that reject it.
#[must_use]
pub fn contains_recognized_session_tmpdir_pointer(text: &str) -> bool {
    SESSION_TMPDIR_PATTERNS
        .iter()
        .any(|pattern| pattern.pattern.is_match(text))
}

/// Redact paths then secrets, ending the body with exactly one newline.
///
/// This is the line-oriented shape run-log batch payloads and `--redact`
/// failure bodies persist; [`redact`] preserves the caller's newline intent.
#[must_use]
pub fn redact_run_log_payload(text: &str) -> String {
    let mut redacted = redact(text).text;
    if !redacted.is_empty() && !redacted.ends_with('\n') {
        redacted.push('\n');
    }
    redacted
}

/// Redact sensitive paths first, then all secret families.
#[must_use]
pub fn redact(text: &str) -> RedactionResult {
    let path_scrubbed = redact_sensitive_paths(text);
    redact_secrets(&path_scrubbed)
}

fn count_secret_families(text: &str) -> BTreeMap<&'static str, usize> {
    let mut findings = BTreeMap::new();
    for family in SECRET_FAMILIES.iter().chain(EXTRA_SECRET_FAMILIES.iter()) {
        let count = family.pattern.find_iter(text).count();
        if count != 0 {
            findings.insert(family.name, count);
        }
    }
    findings
}

fn redact_base_line(line: &str) -> String {
    let mut scrubbed = String::from(line);
    for family in SECRET_FAMILIES
        .iter()
        .filter(|family| family.name != "pem-private-key")
    {
        scrubbed = family
            .pattern
            .replace_all(&scrubbed, REDACTED_TOKEN)
            .into_owned();
    }
    scrubbed
}

fn byte_offset(text: &str, character_offset: usize) -> usize {
    text.char_indices()
        .nth(character_offset)
        .map_or(text.len(), |(offset, _character)| offset)
}

fn contains_complete_path_token(text: &str, path: &str) -> bool {
    text.match_indices(path).any(|(start, matched)| {
        let before = text[..start].chars().next_back();
        let after = text[start + matched.len()..].chars().next();
        !before.is_some_and(is_path_token_character) && !after.is_some_and(is_path_token_character)
    })
}

const fn is_path_token_character(character: char) -> bool {
    character.is_ascii_alphanumeric() || matches!(character, '_' | '.' | '-')
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

    #[test]
    fn runtime_redactor_scrubs_exact_unknown_token_formats() {
        let mut redactor = RuntimeRedactor::default();
        assert!(redactor.register_exact_secret("short opaque credential"));

        let result = redactor.redact("Authorization: Bearer short opaque credential");

        assert_eq!(result.findings().get("runtime-exact"), Some(&1));
        assert_eq!(result.text(), "Authorization: Bearer <REDACTED-TOKEN>");
        assert!(
            !redactor
                .safe_text(result.text())
                .as_str()
                .contains("credential")
        );
    }

    #[test]
    fn runtime_redactor_rejects_empty_registration() {
        let mut redactor = RuntimeRedactor::default();
        assert!(!redactor.register_exact_secret(String::new()));
        assert_eq!(redactor.redact("ordinary text").text(), "ordinary text");
    }

    #[test]
    fn streaming_redaction_carries_pem_state_without_a_tail_marker() {
        let first_input = ["before\n-----BEGIN ", "PRIVATE KEY-----\nsecret\n"].concat();
        let first = redact_secrets_streaming(&first_input, false);
        assert_eq!(first.text(), "before\n<REDACTED-PRIVATE-KEY>\n");
        assert!(first.in_pem());

        let second = redact_secrets_streaming(
            "more secret\n-----END PRIVATE KEY-----\nafter sk-abcdefghijklmnopqrstuvwxyz\n",
            first.in_pem(),
        );
        assert_eq!(second.text(), "after <REDACTED-TOKEN>\n");
        assert!(!second.in_pem());
    }

    #[test]
    fn submodule_scrub_removes_only_matching_findings() {
        let text = concat!(
            "preamble\n",
            "### FINDING_1: dependency issue\n- **Location**: vendor/lib:12\nbody\n",
            "### OOS_1: vendor observation\nmentions vendor/lib\n",
            "### FINDING_2: sibling\n- File: vendor/library/file.rs\n",
        );
        let result = scrub_submodule_findings(text, &[String::new(), String::from("vendor/lib")]);

        assert_eq!(result.count(), 1);
        assert_eq!(result.audit(), "### FINDING_1: dependency issue\n");
        assert!(result.text().contains("preamble"));
        assert!(result.text().contains("### OOS_1"));
        assert!(result.text().contains("### FINDING_2"));
        assert!(!result.text().contains("### FINDING_1"));
    }
}
