//! Closed validators for Git CLI compatibility inputs.

use std::ffi::{OsStr, OsString};

use super::{GitCliInputError, GitCliInputErrorKind};

macro_rules! git_value {
    ($name:ident, $label:literal) => {
        #[derive(Clone, Debug, Eq, PartialEq)]
        pub struct $name(OsString);

        impl $name {
            /// # Errors
            /// Rejects empty, option-like, or NUL values.
            pub fn new(value: impl Into<OsString>) -> Result<Self, GitCliInputError> {
                let value = value.into();
                reject_empty(&value, $label)?;
                reject_nul(&value, $label)?;
                reject_option_like(&value, $label)?;
                Ok(Self(value))
            }

            #[must_use]
            pub fn as_os_str(&self) -> &OsStr {
                &self.0
            }
        }
    };
}

git_value!(GitUrl, "url");
git_value!(GitToken, "token");

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitPath(OsString);

impl GitPath {
    /// # Errors
    /// Rejects empty, absolute, option-like, NUL, or `..` path segments.
    pub fn new(value: impl Into<OsString>) -> Result<Self, GitCliInputError> {
        let value = value.into();
        reject_empty(&value, "path")?;
        reject_nul(&value, "path")?;
        reject_option_like(&value, "path")?;
        let path = std::path::Path::new(&value);
        if path.is_absolute() {
            return Err(GitCliInputError::new(
                GitCliInputErrorKind::AbsolutePath,
                "path must be relative to the repository",
            ));
        }
        for component in path.components() {
            match component {
                std::path::Component::Normal(part) => {
                    reject_empty(part, "path")?;
                    reject_nul(part, "path")?;
                }
                std::path::Component::CurDir => {}
                _ => {
                    return Err(GitCliInputError::new(
                        GitCliInputErrorKind::UnsafePath,
                        "path must not contain .. or prefix components",
                    ));
                }
            }
        }
        Ok(Self(value))
    }

    #[must_use]
    pub fn as_os_str(&self) -> &OsStr {
        &self.0
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitRef(OsString);

impl GitRef {
    /// # Errors
    /// Rejects empty, option-like, NUL, whitespace, and injection shapes.
    pub fn new(value: impl Into<OsString>) -> Result<Self, GitCliInputError> {
        let value = value.into();
        reject_empty(&value, "ref")?;
        reject_nul(&value, "ref")?;
        reject_option_like(&value, "ref")?;
        let Some(text) = value.to_str() else {
            return Err(GitCliInputError::new(
                GitCliInputErrorKind::NonUnicode,
                "ref must be valid Unicode",
            ));
        };
        if text.chars().any(char::is_whitespace)
            || text.contains("..")
            || (text.contains('@') && text.contains('{'))
            || text.contains('\\')
            || text.starts_with('/')
            || text.ends_with('/')
            || text.ends_with('.')
            || text.contains("//")
        {
            return Err(GitCliInputError::new(
                GitCliInputErrorKind::InvalidRef,
                "ref has an invalid shape",
            ));
        }
        Ok(Self(value))
    }

    #[must_use]
    pub fn as_os_str(&self) -> &OsStr {
        &self.0
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitRemote(OsString);

impl GitRemote {
    /// # Errors
    /// Rejects empty, option-like, NUL, or whitespace remote names.
    pub fn new(value: impl Into<OsString>) -> Result<Self, GitCliInputError> {
        let value = value.into();
        reject_empty(&value, "remote")?;
        reject_nul(&value, "remote")?;
        reject_option_like(&value, "remote")?;
        let Some(text) = value.to_str() else {
            return Err(GitCliInputError::new(
                GitCliInputErrorKind::NonUnicode,
                "remote must be valid Unicode",
            ));
        };
        if text.chars().any(char::is_whitespace) || text.contains(':') || text.contains('\\') {
            return Err(GitCliInputError::new(
                GitCliInputErrorKind::InvalidRemote,
                "remote contains a disallowed character",
            ));
        }
        Ok(Self(value))
    }

    #[must_use]
    pub fn as_os_str(&self) -> &OsStr {
        &self.0
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitRefspec(OsString);

impl GitRefspec {
    /// # Errors
    /// Rejects empty, option-like, NUL, whitespace, or empty-side refspecs.
    pub fn new(value: impl Into<OsString>) -> Result<Self, GitCliInputError> {
        let value = value.into();
        reject_empty(&value, "refspec")?;
        reject_nul(&value, "refspec")?;
        reject_option_like(&value, "refspec")?;
        let Some(text) = value.to_str() else {
            return Err(GitCliInputError::new(
                GitCliInputErrorKind::NonUnicode,
                "refspec must be valid Unicode",
            ));
        };
        if text.chars().any(char::is_whitespace) {
            return Err(GitCliInputError::new(
                GitCliInputErrorKind::InvalidRefspec,
                "refspec must not contain whitespace",
            ));
        }
        let body = text.strip_prefix('+').unwrap_or(text);
        if body.is_empty() || body.starts_with(':') || body.ends_with(':') || body.contains("::") {
            return Err(GitCliInputError::new(
                GitCliInputErrorKind::InvalidRefspec,
                "refspec has an empty source or destination",
            ));
        }
        Ok(Self(value))
    }

    #[must_use]
    pub fn as_os_str(&self) -> &OsStr {
        &self.0
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitConfigKey(OsString);

impl GitConfigKey {
    /// # Errors
    /// Rejects empty, option-like, NUL, or malformed config keys.
    pub fn new(value: impl Into<OsString>) -> Result<Self, GitCliInputError> {
        let value = value.into();
        reject_empty(&value, "config key")?;
        reject_nul(&value, "config key")?;
        reject_option_like(&value, "config key")?;
        let Some(text) = value.to_str() else {
            return Err(GitCliInputError::new(
                GitCliInputErrorKind::NonUnicode,
                "config key must be valid Unicode",
            ));
        };
        let parts: Vec<&str> = text.split('.').collect();
        if parts.len() < 2
            || parts.iter().any(|part| part.is_empty())
            || text.chars().any(|ch| ch.is_whitespace() || ch == '=')
        {
            return Err(GitCliInputError::new(
                GitCliInputErrorKind::InvalidConfigKey,
                "config key must be section.key or section.subsection.key",
            ));
        }
        Ok(Self(value))
    }

    #[must_use]
    pub fn as_os_str(&self) -> &OsStr {
        &self.0
    }
}

fn reject_empty(value: &OsStr, label: &str) -> Result<(), GitCliInputError> {
    if value.is_empty() {
        Err(GitCliInputError::new(
            GitCliInputErrorKind::Empty,
            format!("{label} must not be empty"),
        ))
    } else {
        Ok(())
    }
}

fn reject_nul(value: &OsStr, label: &str) -> Result<(), GitCliInputError> {
    if value.as_encoded_bytes().contains(&0) {
        Err(GitCliInputError::new(
            GitCliInputErrorKind::NulByte,
            format!("{label} must not contain NUL"),
        ))
    } else {
        Ok(())
    }
}

fn reject_option_like(value: &OsStr, label: &str) -> Result<(), GitCliInputError> {
    if value.as_encoded_bytes().first() == Some(&b'-') {
        Err(GitCliInputError::new(
            GitCliInputErrorKind::OptionInjection,
            format!("{label} must not look like a command option"),
        ))
    } else {
        Ok(())
    }
}
