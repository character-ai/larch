//! Shared operator-facing string diagnostic error.

/// Fail-closed diagnostic carrying a single operator-facing message.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MessageError {
    message: String,
}

impl MessageError {
    pub(crate) fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }

    /// Return the operator-facing diagnostic.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.message
    }
}

impl std::fmt::Display for MessageError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl std::error::Error for MessageError {}
