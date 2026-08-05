//! Validated vendor session handles for resume argv builders.

use regex::Regex;
use std::{error::Error, fmt, sync::OnceLock};

/// Vendors that support explicit session resume handles.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VendorSessionVendor {
    /// Codex thread UUID resume.
    Codex,
    /// Cursor chat-id resume.
    Cursor,
}

impl VendorSessionVendor {
    /// Parse a vendor key accepted by session handles.
    ///
    /// # Errors
    /// Rejects vendors other than `codex` and `cursor`.
    pub fn parse(vendor: &str) -> Result<Self, VendorSessionError> {
        match vendor {
            "codex" => Ok(Self::Codex),
            "cursor" => Ok(Self::Cursor),
            _ => Err(VendorSessionError {
                kind: VendorSessionErrorKind::UnsupportedVendor,
            }),
        }
    }

    /// Wire key for this vendor.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Codex => "codex",
            Self::Cursor => "cursor",
        }
    }
}

/// Frozen vendor identity plus an explicit session identifier for resume argv.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VendorSessionHandle {
    vendor: VendorSessionVendor,
    session_id: String,
}

impl VendorSessionHandle {
    /// Validate and construct a session handle.
    ///
    /// # Errors
    /// Rejects unsupported vendors, empty or whitespace-bearing ids, control
    /// characters, flag-like ids, non-UUID Codex ids, and invalid Cursor ids.
    pub fn create(vendor: &str, session_id: &str) -> Result<Self, VendorSessionError> {
        let typed = VendorSessionVendor::parse(vendor)?;
        validate_session_id(typed, session_id)?;
        Ok(Self {
            vendor: typed,
            session_id: session_id.to_owned(),
        })
    }

    /// Vendor family for this handle.
    #[must_use]
    pub const fn vendor(&self) -> VendorSessionVendor {
        self.vendor
    }

    /// Validated session identifier.
    #[must_use]
    pub fn session_id(&self) -> &str {
        &self.session_id
    }
}

/// Session-handle validation failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct VendorSessionError {
    kind: VendorSessionErrorKind,
}

impl VendorSessionError {
    /// Stable failure category.
    #[must_use]
    pub const fn kind(self) -> VendorSessionErrorKind {
        self.kind
    }
}

/// Categories of session-handle rejection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VendorSessionErrorKind {
    /// Vendor is not `codex` or `cursor`.
    UnsupportedVendor,
    /// Session id failed structural validation.
    InvalidSessionId,
}

impl fmt::Display for VendorSessionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self.kind {
            VendorSessionErrorKind::UnsupportedVendor => {
                "unsupported vendor session handle vendor"
            }
            VendorSessionErrorKind::InvalidSessionId => "invalid vendor session id",
        })
    }
}

impl Error for VendorSessionError {}

fn validate_session_id(
    vendor: VendorSessionVendor,
    session_id: &str,
) -> Result<(), VendorSessionError> {
    if session_id.is_empty()
        || session_id.trim() != session_id
        || session_id.chars().any(char::is_whitespace)
    {
        return Err(VendorSessionError {
            kind: VendorSessionErrorKind::InvalidSessionId,
        });
    }
    if session_id.chars().any(char::is_control) {
        return Err(VendorSessionError {
            kind: VendorSessionErrorKind::InvalidSessionId,
        });
    }
    if session_id.starts_with('-') {
        return Err(VendorSessionError {
            kind: VendorSessionErrorKind::InvalidSessionId,
        });
    }
    let ok = match vendor {
        VendorSessionVendor::Codex => codex_session_uuid_re().is_match(session_id),
        VendorSessionVendor::Cursor => session_id_re().is_match(session_id),
    };
    if ok {
        Ok(())
    } else {
        Err(VendorSessionError {
            kind: VendorSessionErrorKind::InvalidSessionId,
        })
    }
}

fn session_id_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$").expect("session id regex"))
}

fn codex_session_uuid_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        )
        .expect("codex uuid regex")
    })
}