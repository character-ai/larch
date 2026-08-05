//! Round identity for run-log round directories.

use std::{error::Error, fmt};

/// A positive 1-based run-log round number.
#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct RoundNumber(u32);

impl RoundNumber {
    /// Parse a positive round number.
    ///
    /// # Errors
    ///
    /// Returns [`RoundNumberError`] when the value is zero.
    pub const fn new(value: u32) -> Result<Self, RoundNumberError> {
        if value == 0 {
            return Err(RoundNumberError);
        }
        Ok(Self(value))
    }

    /// Return the round number.
    #[must_use]
    pub const fn get(self) -> u32 {
        self.0
    }

    /// Return the directory basename `round-<n>`.
    #[must_use]
    pub fn dir_name(self) -> String {
        format!("round-{}", self.0)
    }

    /// Parse a directory basename such as `round-3`.
    ///
    /// # Errors
    ///
    /// Returns [`RoundNumberError`] when the name is not a positive `round-<n>`.
    pub fn from_dir_name(name: &str) -> Result<Self, RoundNumberError> {
        let Some(suffix) = name.strip_prefix("round-") else {
            return Err(RoundNumberError);
        };
        let value: u32 = suffix.parse().map_err(|_| RoundNumberError)?;
        Self::new(value)
    }
}

impl fmt::Display for RoundNumber {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}", self.0)
    }
}

/// Invalid round identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RoundNumberError;

impl fmt::Display for RoundNumberError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("round number must be a positive integer")
    }
}

impl Error for RoundNumberError {}

#[cfg(test)]
mod tests {
    use super::RoundNumber;

    #[test]
    fn round_identity_round_trips() {
        let round = RoundNumber::new(3).unwrap();
        assert_eq!(round.dir_name(), "round-3");
        assert_eq!(RoundNumber::from_dir_name("round-3").unwrap(), round);
        assert!(RoundNumber::new(0).is_err());
        assert!(RoundNumber::from_dir_name("round-0").is_err());
        assert!(RoundNumber::from_dir_name("panel").is_err());
    }
}
