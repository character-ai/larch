//! Effect-free session-root derivation and temp-directory lifecycle rules
//! shared by state adapters and commands.

use std::{ffi::OsStr, path::PathBuf};

/// Relative paths whose presence marks a directory as an implement session.
///
/// Order is significant: the first existing entry supplies the freshness mtime.
pub const IMPLEMENT_SENTINEL_RELATIVE_PATHS: [&str; 4] = [
    "design-export/manifest.env",
    "review-round-summary.md",
    ".bump-version-armed",
    ".release-armed",
];

/// Default freshness window, in seconds, for a session-unbound implement tmpdir.
pub const IMPLEMENT_TMPDIR_TTL_SECONDS: i64 = 21_600;

/// The directory-name prefix every implement session tmpdir carries.
pub const IMPLEMENT_TMPDIR_PREFIX: &str = "claude-implement-";

/// Resolve the implement-tmpdir freshness window from its environment override.
///
/// Only an all-ASCII-digit override is honored; anything else keeps the default.
/// A value too large for `i64` saturates instead of wrapping, so an absurd
/// override still disables expiry rather than silently restoring the default.
#[must_use]
pub fn implement_tmpdir_ttl(raw: Option<&str>) -> i64 {
    raw.filter(|value| !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
        .map_or(IMPLEMENT_TMPDIR_TTL_SECONDS, |value| {
            value.parse::<i64>().unwrap_or(i64::MAX)
        })
}

/// Reject a design tmpdir whose spelling violates the wire contract.
///
/// Returns the exact operator diagnostic for the first violated rule, or `None`
/// when the candidate is syntactically acceptable. Containment against the
/// resolved allowlist is a separate, filesystem-backed check.
#[must_use]
pub fn design_tmpdir_syntax_error(candidate: &str) -> Option<&'static str> {
    if candidate.is_empty() {
        return Some("design-tmpdir: path is required");
    }
    if candidate.contains('\n') || candidate.contains('\r') {
        return Some("design-tmpdir: path must not contain newline or carriage return");
    }
    if !candidate.starts_with('/') {
        return Some("Invalid --design-tmpdir: must be an absolute path");
    }
    if candidate
        .split('/')
        .any(|segment| segment == "." || segment == "..")
    {
        return Some("design-tmpdir: path must not contain '.' or '..' segments");
    }
    None
}

/// Return whether `candidate` outranks the current best implement tmpdir.
///
/// Newest sentinel mtime wins; equal mtimes break the tie on the lexically
/// smaller path so concurrent sessions in one clone resolve deterministically.
#[must_use]
pub fn prefers_implement_candidate(
    candidate: &str,
    candidate_mtime: i64,
    best: &str,
    best_mtime: i64,
) -> bool {
    candidate_mtime > best_mtime
        || (candidate_mtime == best_mtime && (best.is_empty() || candidate < best))
}

/// Derive the cache-backed session root from an explicit environment snapshot.
#[must_use]
pub fn cleanup_cache_sessions_root(
    xdg_cache_home: Option<&OsStr>,
    home: Option<&OsStr>,
) -> PathBuf {
    let base = xdg_cache_home
        .filter(|value| !value.is_empty())
        .map_or_else(
            || {
                home.filter(|value| !value.is_empty()).map_or_else(
                    || PathBuf::from("/tmp/.cache"),
                    |value| PathBuf::from(value).join(".cache"),
                )
            },
            PathBuf::from,
        );
    base.join("larch").join("sessions")
}

/// Return the legacy HOME-backed root for PID-keyed current-session pointers.
///
/// Unlike durable session directories, these pointers intentionally retain the
/// historical `$HOME/.cache` location even when `XDG_CACHE_HOME` redirects
/// session artifact storage. Cleanup and publication must use this one shared
/// derivation so they synchronize over the same authority.
#[must_use]
pub fn session_pointer_root(home: Option<&OsStr>) -> PathBuf {
    PathBuf::from(home.unwrap_or_else(|| OsStr::new("")))
        .join(".cache")
        .join("larch")
        .join("sessions")
}

/// Return the roots accepted for implementation session directories.
#[must_use]
pub fn implement_session_roots(
    xdg_cache_home: Option<&OsStr>,
    home: Option<&OsStr>,
) -> [PathBuf; 3] {
    [
        cleanup_cache_sessions_root(xdg_cache_home, home),
        PathBuf::from("/tmp"),
        PathBuf::from("/private/tmp"),
    ]
}

/// Return every root accepted by legacy session writers and cleanup guards.
#[must_use]
pub fn allowed_session_roots(xdg_cache_home: Option<&OsStr>, home: Option<&OsStr>) -> [PathBuf; 5] {
    [
        PathBuf::from("/tmp"),
        PathBuf::from("/private/tmp"),
        PathBuf::from("/var/folders"),
        PathBuf::from("/private/var/folders"),
        cleanup_cache_sessions_root(xdg_cache_home, home),
    ]
}

#[cfg(test)]
mod tests {
    use super::{
        IMPLEMENT_TMPDIR_TTL_SECONDS, allowed_session_roots, cleanup_cache_sessions_root,
        design_tmpdir_syntax_error, implement_session_roots, implement_tmpdir_ttl,
        prefers_implement_candidate, session_pointer_root,
    };
    use std::{ffi::OsStr, path::PathBuf};

    #[test]
    fn ttl_override_accepts_only_digits_and_saturates() {
        assert_eq!(implement_tmpdir_ttl(None), IMPLEMENT_TMPDIR_TTL_SECONDS);
        assert_eq!(implement_tmpdir_ttl(Some("")), IMPLEMENT_TMPDIR_TTL_SECONDS);
        assert_eq!(
            implement_tmpdir_ttl(Some("-5")),
            IMPLEMENT_TMPDIR_TTL_SECONDS
        );
        assert_eq!(
            implement_tmpdir_ttl(Some("12x")),
            IMPLEMENT_TMPDIR_TTL_SECONDS
        );
        assert_eq!(implement_tmpdir_ttl(Some("0")), 0);
        assert_eq!(implement_tmpdir_ttl(Some("90")), 90);
        assert_eq!(implement_tmpdir_ttl(Some(&"9".repeat(30))), i64::MAX);
    }

    #[test]
    fn design_tmpdir_syntax_reports_the_first_violated_rule() {
        assert_eq!(
            design_tmpdir_syntax_error(""),
            Some("design-tmpdir: path is required")
        );
        assert_eq!(
            design_tmpdir_syntax_error("/tmp/a\nb"),
            Some("design-tmpdir: path must not contain newline or carriage return")
        );
        assert_eq!(
            design_tmpdir_syntax_error("relative/path"),
            Some("Invalid --design-tmpdir: must be an absolute path")
        );
        assert_eq!(
            design_tmpdir_syntax_error("/tmp/../escape"),
            Some("design-tmpdir: path must not contain '.' or '..' segments")
        );
        assert_eq!(design_tmpdir_syntax_error("/tmp/design//x/"), None);
    }

    #[test]
    fn candidate_preference_is_newest_then_lexically_smallest() {
        assert!(prefers_implement_candidate("/tmp/b", 20, "/tmp/a", 10));
        assert!(!prefers_implement_candidate("/tmp/b", 5, "/tmp/a", 10));
        assert!(prefers_implement_candidate("/tmp/a", 10, "/tmp/b", 10));
        assert!(!prefers_implement_candidate("/tmp/b", 10, "/tmp/a", 10));
        assert!(prefers_implement_candidate("/tmp/a", -1, "", -1));
    }

    #[test]
    fn cache_root_uses_xdg_then_home_then_tmp_fallback() {
        assert_eq!(
            cleanup_cache_sessions_root(Some(OsStr::new("/cache")), Some(OsStr::new("/home/u"))),
            PathBuf::from("/cache/larch/sessions")
        );
        assert_eq!(
            cleanup_cache_sessions_root(Some(OsStr::new("")), Some(OsStr::new("/home/u"))),
            PathBuf::from("/home/u/.cache/larch/sessions")
        );
        assert_eq!(
            cleanup_cache_sessions_root(None, Some(OsStr::new(""))),
            PathBuf::from("/tmp/.cache/larch/sessions")
        );
        assert_eq!(
            session_pointer_root(Some(OsStr::new("/home/u"))),
            PathBuf::from("/home/u/.cache/larch/sessions")
        );
        assert_eq!(
            session_pointer_root(None),
            PathBuf::from(".cache/larch/sessions")
        );
    }

    #[test]
    fn implementation_and_writer_roots_preserve_legacy_order() {
        assert_eq!(
            implement_session_roots(None, Some(OsStr::new("/home/u"))),
            [
                PathBuf::from("/home/u/.cache/larch/sessions"),
                PathBuf::from("/tmp"),
                PathBuf::from("/private/tmp"),
            ]
        );
        assert_eq!(
            allowed_session_roots(None, None)[2],
            PathBuf::from("/var/folders")
        );
    }
}
