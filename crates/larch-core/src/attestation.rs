//! Closed domain inputs and verified outputs for larch release attestations.

use std::{collections::BTreeSet, error::Error, fmt};

const MAX_ASSETS: usize = 100;

/// Why caller-owned attestation input was rejected before transport access.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AttestationInputErrorKind {
    InvalidAssetName,
    InvalidDigest,
    InvalidTag,
    InvalidCommit,
    EmptyAssetSet,
    TooManyAssets,
    DuplicateAssetName,
    DuplicateAssetDigest,
}

/// A fixed diagnostic for invalid attestation input.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AttestationInputError {
    kind: AttestationInputErrorKind,
}

impl AttestationInputError {
    const fn new(kind: AttestationInputErrorKind) -> Self {
        Self { kind }
    }

    #[must_use]
    pub const fn kind(self) -> AttestationInputErrorKind {
        self.kind
    }
}

impl fmt::Display for AttestationInputError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self.kind {
            AttestationInputErrorKind::InvalidAssetName => "attestation asset name is invalid",
            AttestationInputErrorKind::InvalidDigest => "attestation digest is invalid",
            AttestationInputErrorKind::InvalidTag => "release attestation tag is invalid",
            AttestationInputErrorKind::InvalidCommit => "release source commit is invalid",
            AttestationInputErrorKind::EmptyAssetSet => "release attestation asset set is empty",
            AttestationInputErrorKind::TooManyAssets => {
                "release attestation asset set exceeds its item cap"
            }
            AttestationInputErrorKind::DuplicateAssetName => {
                "release attestation contains a duplicate asset name"
            }
            AttestationInputErrorKind::DuplicateAssetDigest => {
                "release attestation contains a duplicate asset digest"
            }
        })
    }
}

impl Error for AttestationInputError {}

/// One expected release asset and its lowercase SHA-256 digest.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReleaseAssetSubject {
    name: String,
    digest: String,
}

impl ReleaseAssetSubject {
    /// Validate one asset subject.
    ///
    /// # Errors
    /// Rejects unsafe names and non-lowercase SHA-256 digests.
    pub fn new(name: &str, digest: &str) -> Result<Self, AttestationInputError> {
        if name.is_empty()
            || name.len() > 255
            || name == "."
            || name == ".."
            || name
                .bytes()
                .any(|byte| byte.is_ascii_control() || matches!(byte, b'/' | b'\\'))
        {
            return Err(AttestationInputError::new(
                AttestationInputErrorKind::InvalidAssetName,
            ));
        }
        let Some(hex) = digest.strip_prefix("sha256:") else {
            return Err(AttestationInputError::new(
                AttestationInputErrorKind::InvalidDigest,
            ));
        };
        if !valid_lower_hex(hex, 64) {
            return Err(AttestationInputError::new(
                AttestationInputErrorKind::InvalidDigest,
            ));
        }
        Ok(Self {
            name: name.to_owned(),
            digest: digest.to_owned(),
        })
    }

    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }

    #[must_use]
    pub fn digest(&self) -> &str {
        &self.digest
    }

    #[must_use]
    pub fn digest_hex(&self) -> &str {
        self.digest.strip_prefix("sha256:").unwrap_or_default()
    }
}

/// The exact `vMAJOR.MINOR.PATCH` release tag verified by larch.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReleaseTag(String);

impl ReleaseTag {
    /// Validate the larch release-tag grammar.
    ///
    /// # Errors
    /// Rejects tags outside the closed larch version format.
    pub fn parse(value: &str) -> Result<Self, AttestationInputError> {
        let Some(version) = value.strip_prefix('v') else {
            return Err(AttestationInputError::new(
                AttestationInputErrorKind::InvalidTag,
            ));
        };
        let parts: Vec<&str> = version.split('.').collect();
        if parts.len() != 3
            || parts.iter().any(|part| {
                part.is_empty()
                    || !part.bytes().all(|byte| byte.is_ascii_digit())
                    || (part.len() > 1 && part.starts_with('0'))
            })
        {
            return Err(AttestationInputError::new(
                AttestationInputErrorKind::InvalidTag,
            ));
        }
        Ok(Self(value.to_owned()))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }

    #[must_use]
    pub fn source_ref(&self) -> String {
        format!("refs/tags/{}", self.0)
    }
}

/// The exact lowercase Git object id named by the release tag.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReleaseSourceCommit(String);

impl ReleaseSourceCommit {
    /// Validate a SHA-1 or SHA-256 Git object id.
    ///
    /// # Errors
    /// Rejects any other width or character set.
    pub fn parse(value: &str) -> Result<Self, AttestationInputError> {
        if !(valid_lower_hex(value, 40) || valid_lower_hex(value, 64)) {
            return Err(AttestationInputError::new(
                AttestationInputErrorKind::InvalidCommit,
            ));
        }
        Ok(Self(value.to_owned()))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }

    #[must_use]
    pub fn digest_with_algorithm(&self) -> String {
        let algorithm = if self.0.len() == 40 { "sha1" } else { "sha256" };
        format!("{algorithm}:{}", self.0)
    }
}

/// Closed input for one GitHub build-provenance attestation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ArtifactAttestationRequest {
    subject: ReleaseAssetSubject,
    tag: ReleaseTag,
    source_commit: ReleaseSourceCommit,
}

impl ArtifactAttestationRequest {
    #[must_use]
    pub const fn new(
        subject: ReleaseAssetSubject,
        tag: ReleaseTag,
        source_commit: ReleaseSourceCommit,
    ) -> Self {
        Self {
            subject,
            tag,
            source_commit,
        }
    }

    #[must_use]
    pub const fn subject(&self) -> &ReleaseAssetSubject {
        &self.subject
    }

    #[must_use]
    pub const fn tag(&self) -> &ReleaseTag {
        &self.tag
    }

    #[must_use]
    pub const fn source_commit(&self) -> &ReleaseSourceCommit {
        &self.source_commit
    }
}

/// Closed input for GitHub's immutable-release attestation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ImmutableReleaseAttestationRequest {
    tag: ReleaseTag,
    source_commit: ReleaseSourceCommit,
    assets: Vec<ReleaseAssetSubject>,
}

impl ImmutableReleaseAttestationRequest {
    /// Validate the final, complete release asset set.
    ///
    /// # Errors
    /// Rejects empty, oversized, or duplicate subject sets.
    pub fn new(
        tag: ReleaseTag,
        source_commit: ReleaseSourceCommit,
        mut assets: Vec<ReleaseAssetSubject>,
    ) -> Result<Self, AttestationInputError> {
        if assets.is_empty() {
            return Err(AttestationInputError::new(
                AttestationInputErrorKind::EmptyAssetSet,
            ));
        }
        if assets.len() > MAX_ASSETS {
            return Err(AttestationInputError::new(
                AttestationInputErrorKind::TooManyAssets,
            ));
        }
        let names: BTreeSet<&str> = assets.iter().map(ReleaseAssetSubject::name).collect();
        if names.len() != assets.len() {
            return Err(AttestationInputError::new(
                AttestationInputErrorKind::DuplicateAssetName,
            ));
        }
        let digests: BTreeSet<&str> = assets.iter().map(ReleaseAssetSubject::digest).collect();
        if digests.len() != assets.len() {
            return Err(AttestationInputError::new(
                AttestationInputErrorKind::DuplicateAssetDigest,
            ));
        }
        assets.sort_by(|left, right| left.name.cmp(&right.name));
        Ok(Self {
            tag,
            source_commit,
            assets,
        })
    }

    #[must_use]
    pub const fn tag(&self) -> &ReleaseTag {
        &self.tag
    }

    #[must_use]
    pub const fn source_commit(&self) -> &ReleaseSourceCommit {
        &self.source_commit
    }

    #[must_use]
    pub fn assets(&self) -> &[ReleaseAssetSubject] {
        &self.assets
    }
}

/// Proof that one artifact passed cryptographic and hosted-provenance policy.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedArtifactAttestation {
    pub subject: ReleaseAssetSubject,
    pub tag: ReleaseTag,
    pub source_commit: ReleaseSourceCommit,
}

/// Proof that one immutable release bound the final tag, commit, and asset set.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedReleaseAttestation {
    pub tag: ReleaseTag,
    pub source_commit: ReleaseSourceCommit,
    pub asset_count: usize,
}

fn valid_lower_hex(value: &str, width: usize) -> bool {
    value.len() == width
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

#[cfg(test)]
mod tests {
    use super::*;

    const DIGEST: &str = "sha256:1111111111111111111111111111111111111111111111111111111111111111";
    const COMMIT: &str = "2222222222222222222222222222222222222222";

    fn asset(name: &str, digest: &str) -> ReleaseAssetSubject {
        ReleaseAssetSubject::new(name, digest).expect("asset")
    }

    #[test]
    fn closed_inputs_reject_path_names_digest_variants_and_nonrelease_tags() {
        assert!(ReleaseAssetSubject::new("../asset", DIGEST).is_err());
        assert!(ReleaseAssetSubject::new("asset", &DIGEST.to_uppercase()).is_err());
        assert!(ReleaseTag::parse("release-1.2.3").is_err());
        assert!(ReleaseTag::parse("v01.2.3").is_err());
        assert!(ReleaseSourceCommit::parse("deadbeef").is_err());
    }

    #[test]
    fn release_request_sorts_and_rejects_duplicate_subjects() {
        let tag = ReleaseTag::parse("v1.2.3").expect("tag");
        let commit = ReleaseSourceCommit::parse(COMMIT).expect("commit");
        let other = "sha256:3333333333333333333333333333333333333333333333333333333333333333";
        let request = ImmutableReleaseAttestationRequest::new(
            tag.clone(),
            commit.clone(),
            vec![asset("z", DIGEST), asset("a", other)],
        )
        .expect("request");
        assert_eq!(request.assets()[0].name(), "a");

        let duplicate_name = ImmutableReleaseAttestationRequest::new(
            tag.clone(),
            commit.clone(),
            vec![asset("same", DIGEST), asset("same", other)],
        )
        .expect_err("duplicate name");
        assert_eq!(
            duplicate_name.kind(),
            AttestationInputErrorKind::DuplicateAssetName
        );

        let duplicate_digest = ImmutableReleaseAttestationRequest::new(
            tag,
            commit,
            vec![asset("one", DIGEST), asset("two", DIGEST)],
        )
        .expect_err("duplicate digest");
        assert_eq!(
            duplicate_digest.kind(),
            AttestationInputErrorKind::DuplicateAssetDigest
        );
    }
}
