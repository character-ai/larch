//! Vendor credential preflight decisions and probe child-environment overlays.
//!
//! Every function here is pure. Keychain reads, process spawning, and
//! environment application belong to the adapter layer, so a credential never
//! reaches this module's return values except through [`CursorCredential`],
//! which is redacted out of its own `Debug` rendering.

use crate::{ChildEnvironment, vendor::review::ReviewAuthVerdict};
use std::{ffi::OsString, fmt, time::Duration};

/// Exit code the Cursor preflight reports for a proven credential failure.
pub const CURSOR_PREFLIGHT_AUTH_RC: i32 = 2;

/// Bounded keychain read attempts before the preflight fails closed.
pub const CURSOR_AUTH_MAX_ATTEMPTS: usize = 3;

/// Pause between bounded keychain read attempts.
pub const CURSOR_AUTH_RETRY_DELAY: Duration = Duration::from_millis(200);

/// Keychain account queried for the Cursor service token.
pub const CURSOR_KEYCHAIN_ACCOUNT: &str = "cursor-user";

/// Keychain service queried for the Cursor service token.
pub const CURSOR_KEYCHAIN_SERVICE: &str = "cursor-access-token";

/// Host platform class that decides whether a keychain read applies.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum HostPlatform {
    /// macOS, where Cursor stores its service token in the login keychain.
    Darwin,
    /// Every other platform, where no keychain preflight exists.
    Other,
}

impl HostPlatform {
    /// Classify a `uname`-style platform name.
    #[must_use]
    pub fn classify(name: &str) -> Self {
        if name == "Darwin" {
            Self::Darwin
        } else {
            Self::Other
        }
    }
}

/// A Cursor service token held only long enough to reach a child process.
#[derive(Clone, Eq, PartialEq)]
pub struct CursorCredential(String);

impl CursorCredential {
    /// Accept a raw `CURSOR_API_KEY` or keychain value as a usable credential.
    ///
    /// A value carrying an embedded newline or carriage return is rejected
    /// outright: it cannot be written into a `KEY=value` child environment
    /// without splicing, and the legacy preflight cleared it for that reason.
    #[must_use]
    pub fn parse(raw: &str) -> Option<Self> {
        if raw.contains('\n') || raw.contains('\r') {
            return None;
        }
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            return None;
        }
        Some(Self(trimmed.to_owned()))
    }

    /// Expose the credential for injection into an approved child request.
    #[must_use]
    pub fn expose(&self) -> &str {
        &self.0
    }
}

impl fmt::Debug for CursorCredential {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("CursorCredential(<redacted>)")
    }
}

/// Refuse a launch whose Cursor credentials could not be proved.
///
/// The verdict type is the shared [`ReviewAuthVerdict`] owner so a review
/// launcher's `CursorReviewAuthPort` consumes this result unchanged.
#[must_use]
pub fn cursor_preflight_refusal(caller: &str) -> ReviewAuthVerdict {
    ReviewAuthVerdict::refuse(
        CURSOR_PREFLIGHT_AUTH_RC,
        cursor_preflight_failure_message(caller),
    )
}

/// Render the exact operator guidance for a failed Cursor preflight.
#[must_use]
pub fn cursor_preflight_failure_message(caller: &str) -> String {
    format!(
        "{caller}: cursor-auth-preflight failed.\n\
         \x20 CURSOR_API_KEY is unset/empty AND the `cursor-user` / `cursor-access-token`\n\
         \x20 keychain entry is missing or unreadable (-w denied) on this Darwin host.\n\
         \x20 Cursor would otherwise emit the cryptic `Security process exited with code: 45`.\n\n\
         \x20 See docs/installation-and-setup.md (Cursor section) for setup.\n\n\
         \x20 To fix, choose one:\n\
         \x20   (a) export CURSOR_API_KEY=<your-cursor-api-key>\n\
         \x20   (b) security delete-generic-password -a cursor-user 2>/dev/null; cursor login"
    )
}

/// Fixed `security find-generic-password` arguments for the Cursor token.
///
/// `-w` reads the secret itself rather than testing for existence. An
/// access-controlled entry can pass an existence check and still deny the read
/// without user interaction (#5518), so an existence-only preflight reports
/// green while Cursor's own in-process read fails.
#[must_use]
pub const fn cursor_keychain_arguments() -> [&'static str; 6] {
    [
        "find-generic-password",
        "-a",
        CURSOR_KEYCHAIN_ACCOUNT,
        "-s",
        CURSOR_KEYCHAIN_SERVICE,
        "-w",
    ]
}

/// Interpret one `security -w` read into a usable credential.
///
/// A zero exit with an empty or whitespace-only token is treated as a failed
/// read, matching the legacy fail-closed preflight. `security` terminates the
/// secret with a newline, so surrounding whitespace is stripped before the
/// line-splicing check that [`CursorCredential::parse`] applies.
#[must_use]
pub fn keychain_credential(exit_code: i32, stdout: &str) -> Option<CursorCredential> {
    if exit_code != 0 {
        return None;
    }
    CursorCredential::parse(stdout.trim())
}

/// Typed child-environment overrides every Cursor child process receives.
///
/// `NO_OPEN_BROWSER` suppresses cursor-agent's deeplink opener so a headless
/// lane never launches the Cursor.app Composer window (#5797). The credential
/// is injected only when it is usable; an absent or malformed key yields no
/// `CURSOR_API_KEY` entry at all rather than an empty one.
#[must_use]
pub fn cursor_child_environment(
    credential: Option<&CursorCredential>,
) -> Vec<(ChildEnvironment, OsString)> {
    let mut overrides = vec![(
        ChildEnvironment::NoOpenBrowser,
        OsString::from(NO_OPEN_BROWSER_ON),
    )];
    if let Some(credential) = credential {
        overrides.push((
            ChildEnvironment::CursorApiKey,
            OsString::from(credential.expose()),
        ));
    }
    overrides
}

/// Value assigned to `NO_OPEN_BROWSER` for every Cursor child.
pub const NO_OPEN_BROWSER_ON: &str = "1";

#[cfg(test)]
mod tests {
    use super::{
        CURSOR_PREFLIGHT_AUTH_RC, ChildEnvironment, CursorCredential, HostPlatform,
        ReviewAuthVerdict, cursor_child_environment, cursor_keychain_arguments,
        cursor_preflight_failure_message, cursor_preflight_refusal, keychain_credential,
    };

    #[test]
    fn credential_rejects_blank_and_line_spliced_values() {
        assert!(CursorCredential::parse("").is_none());
        assert!(CursorCredential::parse("   ").is_none());
        assert!(CursorCredential::parse("key\nEXTRA=1").is_none());
        assert!(CursorCredential::parse("key\rEXTRA=1").is_none());
        assert_eq!(
            CursorCredential::parse("  secret-token  ")
                .expect("token")
                .expose(),
            "secret-token"
        );
    }

    #[test]
    fn credential_never_renders_its_secret() {
        let credential = CursorCredential::parse("super-secret-token").expect("token");
        let rendered = format!("{credential:?}");
        assert!(!rendered.contains("super-secret-token"));
        assert_eq!(rendered, "CursorCredential(<redacted>)");
    }

    #[test]
    fn keychain_read_fails_closed_on_nonzero_exit_or_empty_token() {
        assert!(keychain_credential(1, "ignored").is_none());
        assert!(keychain_credential(0, "").is_none());
        assert!(keychain_credential(0, "\n").is_none());
        assert!(keychain_credential(0, "token\nEXTRA=1\n").is_none());
        assert_eq!(
            keychain_credential(0, "token\n").expect("token").expose(),
            "token"
        );
    }

    #[test]
    fn verdicts_preserve_the_legacy_exit_codes_and_guidance() {
        let allowed = ReviewAuthVerdict::ok();
        assert!(allowed.ok);
        assert_eq!(allowed.rc, 0);
        assert!(allowed.message.is_empty());

        let denied = cursor_preflight_refusal("agent cursor-auth-preflight");
        assert!(!denied.ok);
        assert_eq!(denied.rc, CURSOR_PREFLIGHT_AUTH_RC);
        assert_eq!(
            denied.message,
            cursor_preflight_failure_message("agent cursor-auth-preflight")
        );
    }

    #[test]
    fn failure_message_matches_the_published_operator_text() {
        let message = cursor_preflight_failure_message("agent check-reviewers");
        assert_eq!(
            message,
            "agent check-reviewers: cursor-auth-preflight failed.\n  CURSOR_API_KEY is unset/empty AND the `cursor-user` / `cursor-access-token`\n  keychain entry is missing or unreadable (-w denied) on this Darwin host.\n  Cursor would otherwise emit the cryptic `Security process exited with code: 45`.\n\n  See docs/installation-and-setup.md (Cursor section) for setup.\n\n  To fix, choose one:\n    (a) export CURSOR_API_KEY=<your-cursor-api-key>\n    (b) security delete-generic-password -a cursor-user 2>/dev/null; cursor login"
        );
    }

    #[test]
    fn keychain_arguments_read_the_secret_rather_than_probing_existence() {
        assert_eq!(
            cursor_keychain_arguments(),
            [
                "find-generic-password",
                "-a",
                "cursor-user",
                "-s",
                "cursor-access-token",
                "-w",
            ]
        );
    }

    #[test]
    fn child_environment_omits_the_key_when_no_credential_resolved() {
        let without = cursor_child_environment(None);
        assert_eq!(without.len(), 1);
        assert_eq!(without[0].0, ChildEnvironment::NoOpenBrowser);
        assert_eq!(without[0].1, "1");

        let credential = CursorCredential::parse("token").expect("token");
        let with = cursor_child_environment(Some(&credential));
        assert_eq!(with.len(), 2);
        assert_eq!(with[1].0, ChildEnvironment::CursorApiKey);
        assert_eq!(with[1].1, "token");
    }

    #[test]
    fn only_darwin_reaches_the_keychain_gate() {
        assert_eq!(HostPlatform::classify("Darwin"), HostPlatform::Darwin);
        assert_eq!(HostPlatform::classify("Linux"), HostPlatform::Other);
        assert_eq!(HostPlatform::classify(""), HostPlatform::Other);
    }
}
