//! The `/triage` grammar: helper-owned blocks, outbound sanitation, protected
//! state, immutable-evidence paths, and the fixed probe allowlist.
//!
//! Ports the pure half of Python `larch.issue.triage`. Everything here decides
//! what `/triage` is *allowed* to say or run; the command layer owns the
//! `KEY=value` envelopes, the exit codes, and the GitHub and Git access.
//!
//! `/triage` reads an issue whose body, comments, and cited logs are written by
//! anyone (G-Sec-2), so the two directions are separated. Inbound text is only
//! ever classified — never interpreted — and outbound text is redacted, has its
//! `<!-- larch:` control markers neutralized, and is refused outright when the
//! scrub cannot prove the result is clean (G-Sec-3).

use std::{ffi::OsString, net::IpAddr, sync::LazyLock};

use regex::Regex;

use crate::{
    ExternalProgram, GitCliOperation, HostUtilityProgram, VendorProgram,
    issue::title::insert_tag_after_bug_prefix, redact_outbound,
};

/// Opening marker of the one helper-owned block `/triage` may republish.
pub const TRIAGE_MARKER_START: &str = "<!-- larch:triage:start -->";
/// Closing marker of the one helper-owned block `/triage` may republish.
pub const TRIAGE_MARKER_END: &str = "<!-- larch:triage:end -->";
/// Marker prefix that makes one published verdict comment idempotent.
pub const TRIAGE_VERDICT_COMMENT_PREFIX: &str = "<!-- larch:triage-verdict:";
/// Hard cap on the bytes one immutable-evidence read may publish.
pub const MAX_TRIAGE_EVIDENCE_BYTES: usize = 64 * 1024;
/// Hard cap on the bytes one bounded reproduction probe may publish.
pub const MAX_TRIAGE_PROBE_BYTES: usize = 16 * 1024;
/// Wall-clock seconds one bounded reproduction probe may run.
pub const TRIAGE_PROBE_TIMEOUT_SECONDS: u64 = 30;
/// Required name prefix of the canonical `/tmp` triage session root.
pub const TRIAGE_TMP_PREFIX: &str = "claude-triage-";
/// Tag inserted into a title once its report has been verified.
pub const TRIAGED_TAG: &str = "[TRIAGED]";
/// Replacement published in place of a redacted address.
const REDACTED_PII: &str = "<REDACTED-PII>";
/// Replacement published in place of a non-public URL.
const INTERNAL_URL: &str = "<INTERNAL-URL>";
/// Shortest trailing label a hostname needs before it reads as an address.
const MIN_EMAIL_TLD: usize = 2;

/// A body whose helper-owned triage markers do not pair exactly once.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TriageBlockDefect;

/// Why outbound triage prose could not be published.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TriageSanitizeError {
    /// The artifact carried something other than one validated triage block.
    Artifact,
    /// The body's helper-owned markers did not pair exactly once.
    Malformed,
    /// The redaction pass could not prove the address was gone.
    Unverified,
}

fn larch_marker_pattern() -> &'static Regex {
    // `[\s\x1c-\x1f]` is Python's `\s` for `str`, and `[\s\S]*?` is Python's
    // lazy any-character run.
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"(?s)<!--[\s\x1c-\x1f]*(?i-u:larch:).*?-->")
            .expect("larch marker regex is valid")
    });
    &PATTERN
}

fn protected_marker_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"<!--[\s\x1c-\x1f]*(?i-u:larch:)").expect("protected marker regex is valid")
    });
    &PATTERN
}

fn url_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"(?i-u:https?)://[^\s\x1c-\x1f<>()]+").expect("url regex is valid")
    });
    &PATTERN
}

fn security_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(concat!(
            r"\b(?i-u:credential(?:s)?|secret(?:s)?|api[ -]?key|",
            r"auth(?:entication|orization)? bypass|",
            r"remote code execution|rce|sql injection|command injection|",
            r"vulnerabilit(?:y|ies)|private key|token exposure)\b",
        ))
        .expect("security regex is valid")
    });
    &PATTERN
}

fn lifecycle_prefix_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(concat!(
            r"^\[(?i-u:IMPLEMENTING|DONE|DESIGNING|DESIGNED|STALLED|IN PROGRESS|PLANNED",
            r"|DEBATING|DEBATED)\][\s\x1c-\x1f]+",
        ))
        .expect("lifecycle prefix regex is valid")
    });
    &PATTERN
}

/// Return the byte span of the one helper-owned triage block, when present.
///
/// # Errors
///
/// Returns [`TriageBlockDefect`] when the markers do not pair exactly once, so
/// a caller never rewrites half a block.
pub fn triage_block_span(body: &str) -> Result<Option<(usize, usize)>, TriageBlockDefect> {
    let starts = body.match_indices(TRIAGE_MARKER_START).count();
    let ends = body.match_indices(TRIAGE_MARKER_END).count();
    if starts == 0 && ends == 0 {
        return Ok(None);
    }
    let start = body.find(TRIAGE_MARKER_START);
    let end = body.find(TRIAGE_MARKER_END);
    match (starts, ends, start, end) {
        (1, 1, Some(start), Some(end)) if start < end + TRIAGE_MARKER_END.len() && start < end => {
            Ok(Some((start, end + TRIAGE_MARKER_END.len())))
        }
        _ => Err(TriageBlockDefect),
    }
}

/// Return the body with the helper-owned marker bytes removed.
///
/// The inner prose stays: the protected-state check runs over what is left, so
/// a foreign `<!-- larch:` marker inside the triage block is still seen.
///
/// # Errors
///
/// Returns [`TriageBlockDefect`] for a body whose markers do not pair.
pub fn body_without_triage_markers(body: &str) -> Result<String, TriageBlockDefect> {
    let Some((start, end)) = triage_block_span(body)? else {
        return Ok(body.to_owned());
    };
    let inner_start = start + TRIAGE_MARKER_START.len();
    let inner_end = end - TRIAGE_MARKER_END.len();
    Ok(format!(
        "{}{}{}",
        &body[..start],
        &body[inner_start..inner_end],
        &body[end..]
    ))
}

/// Splice `block` into `original`, replacing a prior triage block or appending.
///
/// # Errors
///
/// Returns [`TriageBlockDefect`] for a body whose markers do not pair.
pub fn replace_triage_block(original: &str, block: &str) -> Result<String, TriageBlockDefect> {
    let Some((start, end)) = triage_block_span(original)? else {
        let separator = if original.is_empty() {
            ""
        } else if original.ends_with('\n') {
            "\n"
        } else {
            "\n\n"
        };
        return Ok(format!("{original}{separator}{block}\n"));
    };
    Ok(format!("{}{block}{}", &original[..start], &original[end..]))
}

/// Redact outbound triage prose and neutralize its control markers.
///
/// With `allow_triage_block` the artifact must be exactly one validated triage
/// block, and the result is republished inside a freshly synthesized marker
/// pair: the only active `<!-- larch:` markers a triage write can publish are
/// the two this function writes itself.
///
/// # Errors
///
/// Returns [`TriageSanitizeError`] when the artifact is not one validated
/// block, when its markers do not pair, or when the address scrub cannot prove
/// itself (G-Sec-3).
pub fn sanitize_triage_outbound(
    text: &str,
    allow_triage_block: bool,
) -> Result<String, TriageSanitizeError> {
    let wrapped = allow_triage_block
        && (text.contains(TRIAGE_MARKER_START) || text.contains(TRIAGE_MARKER_END));
    let mut content = if wrapped {
        let span = triage_block_span(text).map_err(|_| TriageSanitizeError::Malformed)?;
        let Some((start, end)) = span else {
            return Err(TriageSanitizeError::Artifact);
        };
        if !text[..start].trim().is_empty() || !text[end..].trim().is_empty() {
            return Err(TriageSanitizeError::Artifact);
        }
        text[start + TRIAGE_MARKER_START.len()..end - TRIAGE_MARKER_END.len()].to_owned()
    } else {
        text.to_owned()
    };
    content = neutralize_larch_markers(&content);
    content = redact_addresses(&content);
    content = redact_private_urls(&content);
    content = redact_outbound(&content);
    if !find_addresses(&content).is_empty() {
        return Err(TriageSanitizeError::Unverified);
    }
    if allow_triage_block {
        return Ok(format!(
            "{TRIAGE_MARKER_START}\n{}\n{TRIAGE_MARKER_END}",
            content.trim()
        ));
    }
    Ok(content)
}

/// Defuse every `<!-- larch:` control marker in untrusted prose.
fn neutralize_larch_markers(text: &str) -> String {
    larch_marker_pattern()
        .replace_all(text, |captures: &regex::Captures<'_>| {
            captures[0].replacen("<!--", "<!--\u{200b}", 1)
        })
        .into_owned()
}

fn redact_addresses(text: &str) -> String {
    let mut output = String::with_capacity(text.len());
    let mut cursor = 0;
    for (start, end) in find_addresses(text) {
        output.push_str(&text[cursor..start]);
        output.push_str(REDACTED_PII);
        cursor = end;
    }
    output.push_str(&text[cursor..]);
    output
}

fn redact_private_urls(text: &str) -> String {
    url_pattern()
        .replace_all(text, |captures: &regex::Captures<'_>| {
            let matched = &captures[0];
            if url_host_is_private(matched) {
                INTERNAL_URL.to_owned()
            } else {
                matched.to_owned()
            }
        })
        .into_owned()
}

/// Locate every email address, non-overlapping and left to right.
///
/// This is Python's `(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])`
/// written out, because the Rust engine carries no look-around. The lookbehind
/// is implied by leftmost matching, and the lookahead reduces to two rules: the
/// domain run must be taken whole, and the byte after it must not be `_`.
fn find_addresses(text: &str) -> Vec<(usize, usize)> {
    let bytes = text.as_bytes();
    let mut spans: Vec<(usize, usize)> = Vec::new();
    let mut cursor = 0;
    for (index, byte) in bytes.iter().enumerate() {
        if *byte != b'@' || index < cursor {
            continue;
        }
        let mut local = index;
        while local > cursor && is_local_byte(bytes[local - 1]) {
            local -= 1;
        }
        if local == index {
            continue;
        }
        let mut domain = index + 1;
        while domain < bytes.len() && is_domain_byte(bytes[domain]) {
            domain += 1;
        }
        if !domain_run_is_addressable(&text[index + 1..domain]) {
            continue;
        }
        if bytes.get(domain) == Some(&b'_') {
            continue;
        }
        spans.push((local, domain));
        cursor = domain;
    }
    spans
}

const fn is_local_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'.' | b'+' | b'-')
}

const fn is_domain_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'-')
}

/// Return whether a domain run splits as `<something>.<two-or-more letters>`.
fn domain_run_is_addressable(run: &str) -> bool {
    let Some((head, tail)) = run.rsplit_once('.') else {
        return false;
    };
    !head.is_empty()
        && tail.len() >= MIN_EMAIL_TLD
        && tail.bytes().all(|byte| byte.is_ascii_alphabetic())
}

/// IPv4 ranges Python's `ipaddress.is_private` reports, with its two holes.
const PRIVATE_V4: [(u32, u32); 14] = [
    (0x0000_0000, 8),
    (0x0a00_0000, 8),
    (0x7f00_0000, 8),
    (0xa9fe_0000, 16),
    (0xac10_0000, 12),
    (0xc000_0000, 29),
    (0xc000_00aa, 31),
    (0xc000_0200, 24),
    (0xc0a8_0000, 16),
    (0xc612_0000, 15),
    (0xc633_6400, 24),
    (0xcb00_7100, 24),
    (0xf000_0000, 4),
    (0xffff_ffff, 32),
];
/// The two addresses Python excludes from `192.0.0.0/29`.
const PRIVATE_V4_EXCEPTIONS: [u32; 2] = [0xc000_0009, 0xc000_000a];

/// Return whether one matched URL points at a non-public host.
fn url_host_is_private(url: &str) -> bool {
    let host = url_host(url.trim_end_matches(['.', ',', ';', ':', '!', '?']));
    let suffixed = |suffix: &str| host.len() > suffix.len() && host.ends_with(suffix);
    if matches!(host.as_str(), "localhost" | "127.0.0.1" | "::1")
        || suffixed(".internal")
        || suffixed(".local")
    {
        return true;
    }
    host.parse::<IpAddr>().is_ok_and(|address| match address {
        IpAddr::V4(v4) => {
            let bits = u32::from(v4);
            PRIVATE_V4
                .iter()
                .any(|(network, prefix)| in_v4_network(bits, *network, *prefix))
                && !PRIVATE_V4_EXCEPTIONS.contains(&bits)
        }
        IpAddr::V6(v6) => {
            v6.is_loopback()
                || v6.is_unspecified()
                || matches!(v6.segments()[0] & 0xfe00, 0xfc00)
                || matches!(v6.segments()[0] & 0xffc0, 0xfe80)
                || v6
                    .to_ipv4_mapped()
                    .is_some_and(|mapped| url_host_is_private(&format!("http://{mapped}/")))
        }
    })
}

const fn in_v4_network(address: u32, network: u32, prefix: u32) -> bool {
    let mask = if prefix == 0 {
        0
    } else {
        u32::MAX << (32 - prefix)
    };
    address & mask == network & mask
}

/// Extract the lowercase hostname from one matched URL, as `urlparse` does.
fn url_host(url: &str) -> String {
    let authority = url
        .split_once("://")
        .map_or("", |(_scheme, rest)| rest)
        .split(['/', '?', '#'])
        .next()
        .unwrap_or_default();
    let host = authority.rsplit_once('@').map_or(authority, |(_, h)| h);
    let host = host.strip_prefix('[').map_or_else(
        || host.split_once(':').map_or(host, |(name, _)| name),
        |rest| rest.split_once(']').map_or(rest, |(inside, _)| inside),
    );
    host.to_lowercase()
}

/// Return whether one label names a security classification.
#[must_use]
pub fn triage_label_is_security(label: &str) -> bool {
    let lowered = label.to_lowercase();
    lowered == "security" || lowered == "vulnerability"
}

/// Return whether prose reads as a security report.
#[must_use]
pub fn triage_text_is_security_sensitive(text: &str) -> bool {
    security_pattern().is_match(text)
}

/// Return whether a title still carries a workflow lifecycle prefix.
#[must_use]
pub fn triage_title_has_lifecycle_prefix(title: &str) -> bool {
    lifecycle_prefix_pattern().is_match(title)
}

/// Strip every leading workflow lifecycle prefix from a title.
#[must_use]
pub fn strip_triage_lifecycle_prefixes(title: &str) -> String {
    let mut restored = title.to_owned();
    while let Some(found) = lifecycle_prefix_pattern().find(&restored) {
        let end = found.end();
        restored.replace_range(..end, "");
    }
    restored
}

/// Return whether the body carries a `<!-- larch:` marker outside the triage
/// block's own marker bytes.
///
/// # Errors
///
/// Returns [`TriageBlockDefect`] for a body whose markers do not pair.
pub fn body_has_foreign_larch_marker(body: &str) -> Result<bool, TriageBlockDefect> {
    Ok(protected_marker_pattern().is_match(&body_without_triage_markers(body)?))
}

/// Return the verified title, with `[TRIAGED]` after any `[BUG]` prefix.
#[must_use]
pub fn triaged_title(title: &str) -> String {
    insert_tag_after_bug_prefix(title, TRIAGED_TAG)
}

/// Validate one repository-relative evidence path.
///
/// Returns `None` for an empty, absolute, escaping, or option-shaped path, and
/// for a path carrying a control byte. Git permits a newline inside a tracked
/// path, and the accepted path is published as an `EVIDENCE_PATH=` row, so a
/// control byte there could forge a second contract line (G-IO-2).
#[must_use]
pub fn validate_triage_evidence_path(value: &str) -> Option<String> {
    if value.is_empty()
        || value.chars().any(char::is_control)
        || value.contains('\\')
        || value.starts_with('/')
        || value.starts_with('-')
    {
        return None;
    }
    // Python built a `PurePosixPath`, whose parts drop empty and `.` segments.
    let parts: Vec<&str> = value
        .split('/')
        .filter(|part| !part.is_empty() && *part != ".")
        .collect();
    if parts.contains(&"..") || parts.is_empty() {
        return None;
    }
    Some(parts.join("/"))
}

/// One bounded, no-shell reproduction probe the allowlist approved.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TriageProbe {
    /// The approved executable this probe runs.
    pub program: ExternalProgram,
    /// The fixed arguments the probe passes, after the program's own prefix.
    pub arguments: Vec<OsString>,
}

/// Why one requested probe is not in the fixed read-only allowlist.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TriageProbeError {
    /// An argument carried shell metacharacters.
    ShellSyntax,
    /// The name or the argument shape is outside the allowlist.
    NotAllowed,
}

/// Resolve one probe name and its arguments against the fixed allowlist.
///
/// The probes are read-only by construction: they report a version or ask a
/// sandboxed vendor agent one fixed question.
///
/// # Errors
///
/// Returns [`TriageProbeError`] for an argument carrying shell syntax and for
/// any name or argument shape outside the allowlist.
pub fn triage_probe_command(
    name: &str,
    arguments: &[String],
) -> Result<TriageProbe, TriageProbeError> {
    if arguments
        .iter()
        .any(|value| value.contains([';', '&', '|', '`', '$', '<', '>', '\n', '\r']))
    {
        return Err(TriageProbeError::ShellSyntax);
    }
    match (name, arguments) {
        ("python-version", []) => Ok(TriageProbe {
            program: ExternalProgram::HostUtility(HostUtilityProgram::Python3),
            arguments: vec![OsString::from("--version")],
        }),
        ("git-version", []) => Ok(TriageProbe {
            program: ExternalProgram::Git(GitCliOperation::Version),
            arguments: Vec::new(),
        }),
        ("codex-model-readonly", [model]) if is_probe_model(model) => Ok(TriageProbe {
            program: ExternalProgram::Vendor(VendorProgram::Codex),
            arguments: ["exec", "--sandbox", "read-only", "--model", model]
                .into_iter()
                .map(OsString::from)
                .chain(std::iter::once(OsString::from("Reply with OK only.")))
                .collect(),
        }),
        _ => Err(TriageProbeError::NotAllowed),
    }
}

fn is_probe_model(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
}

#[cfg(test)]
mod tests {
    use crate::issue::title::{BUG_PREFIX, DONE_PREFIX};

    use super::{
        TRIAGE_MARKER_END, TRIAGE_MARKER_START, TRIAGED_TAG, TriageProbeError, TriageSanitizeError,
        body_has_foreign_larch_marker, find_addresses, replace_triage_block,
        sanitize_triage_outbound, strip_triage_lifecycle_prefixes, triage_block_span,
        triage_probe_command, triage_text_is_security_sensitive, triaged_title,
        url_host_is_private, validate_triage_evidence_path,
    };

    #[test]
    fn a_block_span_is_found_once_or_refused() {
        let body = format!("a{TRIAGE_MARKER_START}x{TRIAGE_MARKER_END}b");
        assert_eq!(
            triage_block_span(&body),
            Ok(Some((1, body.len() - 1))),
            "one pair spans exactly its markers"
        );
        assert_eq!(triage_block_span("plain body"), Ok(None));
        for broken in [
            format!("{TRIAGE_MARKER_START}open"),
            format!("close{TRIAGE_MARKER_END}"),
            format!("{TRIAGE_MARKER_END}x{TRIAGE_MARKER_START}"),
            format!("{TRIAGE_MARKER_START}{TRIAGE_MARKER_START}x{TRIAGE_MARKER_END}"),
        ] {
            assert!(triage_block_span(&broken).is_err(), "{broken}");
        }
    }

    #[test]
    fn a_replacement_appends_or_swaps_in_place() {
        assert_eq!(replace_triage_block("", "B"), Ok("B\n".to_owned()));
        assert_eq!(
            replace_triage_block("body", "B"),
            Ok("body\n\nB\n".to_owned())
        );
        assert_eq!(
            replace_triage_block("body\n", "B"),
            Ok("body\n\nB\n".to_owned())
        );
        assert_eq!(
            replace_triage_block(
                &format!("a{TRIAGE_MARKER_START}old{TRIAGE_MARKER_END}b"),
                "B"
            ),
            Ok("aBb".to_owned())
        );
    }

    #[test]
    fn outbound_prose_is_scrubbed_and_its_markers_defused() {
        let sanitized = sanitize_triage_outbound(
            "mail me@example.com at <!-- larch:plan:start --> http://127.0.0.1/x",
            false,
        )
        .unwrap_or_else(|_| panic!("clean prose"));

        assert!(sanitized.contains("<REDACTED-PII>"), "{sanitized}");
        assert!(
            sanitized.contains("<!--\u{200b} larch:plan:start -->"),
            "{sanitized}"
        );
        assert!(sanitized.contains("<INTERNAL-URL>"), "{sanitized}");
        assert!(!sanitized.contains("example.com"), "{sanitized}");
    }

    #[test]
    fn a_wrapped_artifact_must_be_exactly_one_block() {
        let block = format!("{TRIAGE_MARKER_START}\ndiagnosis\n{TRIAGE_MARKER_END}");
        assert_eq!(
            sanitize_triage_outbound(&block, true),
            Ok(format!(
                "{TRIAGE_MARKER_START}\ndiagnosis\n{TRIAGE_MARKER_END}"
            ))
        );
        assert_eq!(
            sanitize_triage_outbound(&format!("lead {block}"), true),
            Err(TriageSanitizeError::Artifact)
        );
        assert_eq!(
            sanitize_triage_outbound(&format!("{TRIAGE_MARKER_START}open"), true),
            Err(TriageSanitizeError::Malformed)
        );
        // Without the marker pair the artifact is wrapped verbatim.
        assert_eq!(
            sanitize_triage_outbound("bare", true),
            Ok(format!("{TRIAGE_MARKER_START}\nbare\n{TRIAGE_MARKER_END}"))
        );
    }

    #[test]
    fn addresses_honour_the_python_boundary_rules() {
        assert_eq!(find_addresses("a.b+c@ex.co.uk!"), vec![(0, 14)]);
        // A trailing underscore keeps the run from ever terminating cleanly.
        assert!(find_addresses("a@b.com_x").is_empty());
        assert!(find_addresses("a@b.c").is_empty(), "one-letter tail");
        assert!(find_addresses("@b.com").is_empty(), "no local part");
        assert_eq!(find_addresses("x a@b.com y").len(), 1);
    }

    #[test]
    fn only_non_public_hosts_are_replaced() {
        for private in [
            "http://localhost/x",
            "https://127.0.0.1:8080/y",
            "http://[::1]/z",
            "http://10.1.2.3/",
            "https://build.internal/a",
            "http://box.local",
            "http://169.254.1.1/",
        ] {
            assert!(url_host_is_private(private), "{private}");
        }
        for public in [
            "https://github.com/x",
            "http://8.8.8.8/",
            "https://192.0.0.9/",
        ] {
            assert!(!url_host_is_private(public), "{public}");
        }
    }

    #[test]
    fn protected_state_reads_through_the_triage_block() {
        let clean = format!("report{TRIAGE_MARKER_START}\nnotes\n{TRIAGE_MARKER_END}");
        assert_eq!(body_has_foreign_larch_marker(&clean), Ok(false));
        let foreign =
            format!("report<!-- larch:plan:start -->{TRIAGE_MARKER_START}\nx\n{TRIAGE_MARKER_END}");
        assert_eq!(body_has_foreign_larch_marker(&foreign), Ok(true));
    }

    #[test]
    fn lifecycle_prefixes_are_detected_and_peeled() {
        assert_eq!(
            strip_triage_lifecycle_prefixes(&format!("{DONE_PREFIX}[implementing] fix")),
            "fix"
        );
        let bug = format!("{BUG_PREFIX} fix");
        assert_eq!(strip_triage_lifecycle_prefixes(&bug), bug);
    }

    #[test]
    fn the_verified_title_lands_after_a_bug_prefix() {
        assert_eq!(
            triaged_title(&format!("{BUG_PREFIX} x")),
            format!("{BUG_PREFIX} {TRIAGED_TAG} x")
        );
        assert_eq!(triaged_title("x"), format!("{TRIAGED_TAG} x"));
        let tagged = format!("{TRIAGED_TAG} x");
        assert_eq!(triaged_title(&tagged), tagged);
    }

    #[test]
    fn security_prose_is_recognized() {
        assert!(triage_text_is_security_sensitive("an RCE in the parser"));
        assert!(triage_text_is_security_sensitive("leaked API-key"));
        assert!(!triage_text_is_security_sensitive("a keyboard shortcut"));
    }

    #[test]
    fn only_bounded_repository_relative_evidence_paths_pass() {
        assert_eq!(
            validate_triage_evidence_path("larch-logs/a/b.md"),
            Some("larch-logs/a/b.md".to_owned())
        );
        assert_eq!(
            validate_triage_evidence_path("./a.md"),
            Some("a.md".to_owned())
        );
        for rejected in [
            "",
            "/etc/passwd",
            "a/../b",
            "-flag",
            "a\\b",
            "a\0b",
            ".",
            "a\nEVIDENCE_PATH=b",
        ] {
            assert_eq!(validate_triage_evidence_path(rejected), None, "{rejected}");
        }
    }

    #[test]
    fn the_probe_allowlist_is_closed() {
        assert!(triage_probe_command("git-version", &[]).is_ok());
        assert!(triage_probe_command("python-version", &[]).is_ok());
        assert!(triage_probe_command("codex-model-readonly", &["gpt-5.1".to_owned()]).is_ok());
        for (name, arguments) in [
            ("git-version", vec!["extra".to_owned()]),
            ("codex-model-readonly", vec![]),
            ("codex-model-readonly", vec!["a b".to_owned()]),
            ("shell", vec![]),
        ] {
            assert_eq!(
                triage_probe_command(name, &arguments),
                Err(TriageProbeError::NotAllowed),
                "{name} {arguments:?}"
            );
        }
        // Shell syntax is refused ahead of the allowlist, with its own reason.
        assert_eq!(
            triage_probe_command("codex-model-readonly", &["x;rm".to_owned()]),
            Err(TriageProbeError::ShellSyntax)
        );
    }
}
