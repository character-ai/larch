//! Effect-free session-root derivation shared by state adapters and commands.

use std::{ffi::OsStr, path::PathBuf};

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
    use super::{allowed_session_roots, cleanup_cache_sessions_root, implement_session_roots};
    use std::{ffi::OsStr, path::PathBuf};

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
