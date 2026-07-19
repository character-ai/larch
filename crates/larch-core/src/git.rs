//! Byte-oriented repository metadata types and the sole read port for Git state.

use std::{error::Error, fmt};

/// The object hash algorithm used by a repository.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum ObjectHash {
    /// SHA-1 object identifiers contain 20 raw bytes.
    Sha1,
    /// SHA-256 object identifiers contain 32 raw bytes.
    Sha256,
}

impl ObjectHash {
    /// Return the required raw digest length.
    #[must_use]
    pub const fn digest_len(self) -> usize {
        match self {
            Self::Sha1 => 20,
            Self::Sha256 => 32,
        }
    }
}

/// A raw Git object identifier with its algorithm attached.
#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub struct ObjectId {
    hash: ObjectHash,
    digest: Vec<u8>,
}

impl ObjectId {
    /// Build an object identifier from raw digest bytes.
    ///
    /// # Errors
    /// Returns `InvalidInput` when the digest length does not match the algorithm.
    pub fn new(hash: ObjectHash, digest: impl Into<Vec<u8>>) -> Result<Self, RepositoryError> {
        let digest = digest.into();
        if digest.len() != hash.digest_len() {
            return Err(RepositoryError::new(RepositoryErrorKind::InvalidInput));
        }
        Ok(Self { hash, digest })
    }

    /// Return the hash algorithm.
    #[must_use]
    pub const fn hash(&self) -> ObjectHash {
        self.hash
    }

    /// Return the raw digest.
    #[must_use]
    pub fn digest(&self) -> &[u8] {
        &self.digest
    }
}

/// A path encoded in the repository platform's native bytes.
#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct GitPath(Vec<u8>);

impl GitPath {
    /// Preserve path bytes without interpreting them as UTF-8.
    #[must_use]
    pub fn new(bytes: impl Into<Vec<u8>>) -> Self {
        Self(bytes.into())
    }

    /// Return the raw path bytes.
    #[must_use]
    pub fn as_bytes(&self) -> &[u8] {
        &self.0
    }
}

/// A Git reference name stored as bytes.
#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct RefName(Vec<u8>);

impl RefName {
    /// Preserve a reference name without validating it for a specific use.
    #[must_use]
    pub fn new(bytes: impl Into<Vec<u8>>) -> Self {
        Self(bytes.into())
    }

    /// Return the raw reference name.
    #[must_use]
    pub fn as_bytes(&self) -> &[u8] {
        &self.0
    }
}

/// A revision expression accepted by the repository reader.
#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub struct Revision(Vec<u8>);

impl Revision {
    /// Preserve revision bytes for parsing at the adapter boundary.
    #[must_use]
    pub fn new(bytes: impl Into<Vec<u8>>) -> Self {
        Self(bytes.into())
    }

    /// Return the raw revision expression.
    #[must_use]
    pub fn as_bytes(&self) -> &[u8] {
        &self.0
    }
}

/// A validated dotted configuration key.
#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub struct ConfigKey(String);

impl ConfigKey {
    /// Create a key with `section.name` or `section.subsection.name` shape.
    ///
    /// # Errors
    /// Returns `InvalidInput` when the section or value name is missing.
    pub fn new(key: impl Into<String>) -> Result<Self, RepositoryError> {
        let key = key.into();
        let Some(first_dot) = key.find('.') else {
            return Err(RepositoryError::new(RepositoryErrorKind::InvalidInput));
        };
        let last_dot = key
            .rfind('.')
            .ok_or_else(|| RepositoryError::new(RepositoryErrorKind::InvalidInput))?;
        if first_dot == 0 || last_dot + 1 == key.len() {
            return Err(RepositoryError::new(RepositoryErrorKind::InvalidInput));
        }
        Ok(Self(key))
    }

    /// Return the dotted key.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// Location and format metadata discovered for a repository.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RepositoryLocation {
    pub git_dir: GitPath,
    pub common_dir: GitPath,
    pub work_dir: Option<GitPath>,
    pub object_hash: ObjectHash,
}

/// Source scope for a resolved configuration value.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ConfigScope {
    GitInstallation,
    System,
    User,
    Repository,
    Worktree,
    Environment,
    CommandLine,
    Api,
}

/// One byte-preserving configuration value with provenance.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ConfigValue {
    pub value: Vec<u8>,
    pub scope: ConfigScope,
    pub include_depth: u8,
}

/// A configured remote after Git URL rewrite rules are applied.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Remote {
    pub name: Vec<u8>,
    pub fetch_url: Option<Vec<u8>>,
    pub push_url: Option<Vec<u8>>,
}

/// A local branch's configured fetch upstream.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Upstream {
    pub remote: Vec<u8>,
    pub remote_ref: RefName,
    pub tracking_ref: Option<RefName>,
}

/// The three valid `HEAD` states.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Head {
    Symbolic { name: RefName, target: ObjectId },
    Detached { target: ObjectId },
    Unborn { name: RefName },
}

/// A reference target without exposing adapter types.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ReferenceTarget {
    Object(ObjectId),
    Symbolic(RefName),
}

/// A local, remote-tracking, tag, or other reference.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ReferenceKind {
    LocalBranch,
    RemoteBranch,
    Tag,
    Other,
}

/// One repository reference.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Reference {
    pub name: RefName,
    pub kind: ReferenceKind,
    pub target: ReferenceTarget,
}

/// A Git object type.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ObjectKind {
    Blob,
    Tree,
    Commit,
    Tag,
}

/// A fully loaded object whose bytes retain Git's canonical object payload.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Object {
    pub id: ObjectId,
    pub kind: ObjectKind,
    pub data: Vec<u8>,
}

/// Commit graph data returned during a walk.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Commit {
    pub id: ObjectId,
    pub parents: Vec<ObjectId>,
}

/// One linked or main worktree.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Worktree {
    pub id: Option<Vec<u8>>,
    pub path: GitPath,
    pub git_dir: GitPath,
    pub locked: bool,
}

/// Validation mode for a candidate ref name.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RefFormat {
    Full,
    Branch,
    Tag,
}

/// Stable repository-read failure classes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RepositoryErrorKind {
    NotRepository,
    UntrustedRepository,
    MalformedConfig,
    InvalidInput,
    InvalidRef,
    HashMismatch,
    RevisionNotFound,
    AmbiguousRevision,
    UnsupportedRevision,
    MissingObject,
    ObjectType,
    CorruptRepository,
    Io,
}

/// A bounded diagnostic that never includes paths, config values, or credentials.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RepositoryError {
    kind: RepositoryErrorKind,
}

impl RepositoryError {
    /// Create a repository error from its stable class.
    #[must_use]
    pub const fn new(kind: RepositoryErrorKind) -> Self {
        Self { kind }
    }

    /// Return the stable failure class.
    #[must_use]
    pub const fn kind(&self) -> RepositoryErrorKind {
        self.kind
    }
}

impl fmt::Display for RepositoryError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self.kind {
            RepositoryErrorKind::NotRepository => "not a Git repository",
            RepositoryErrorKind::UntrustedRepository => "repository ownership is not trusted",
            RepositoryErrorKind::MalformedConfig => "repository configuration is malformed",
            RepositoryErrorKind::InvalidInput => "repository query input is invalid",
            RepositoryErrorKind::InvalidRef => "reference name is invalid",
            RepositoryErrorKind::HashMismatch => "object hash does not match the repository",
            RepositoryErrorKind::RevisionNotFound => "revision was not found",
            RepositoryErrorKind::AmbiguousRevision => "revision is ambiguous",
            RepositoryErrorKind::UnsupportedRevision => "revision syntax is unsupported",
            RepositoryErrorKind::MissingObject => "required object is missing",
            RepositoryErrorKind::ObjectType => "object has an unexpected type",
            RepositoryErrorKind::CorruptRepository => "repository data is corrupt",
            RepositoryErrorKind::Io => "repository I/O failed",
        })
    }
}

impl Error for RepositoryError {}

/// The sole production interface for repository metadata reads.
pub trait RepositoryRead: Send + Sync {
    /// Return immutable repository location and object-format metadata.
    fn location(&self) -> RepositoryLocation;
    /// Return all resolved values and scopes for `key`.
    ///
    /// # Errors
    /// Returns a typed config or repository read failure.
    fn config_values(&self, key: &ConfigKey) -> Result<Vec<ConfigValue>, RepositoryError>;
    /// Return configured remotes with rewritten fetch and push URLs.
    ///
    /// # Errors
    /// Returns a typed config or repository read failure.
    fn remotes(&self) -> Result<Vec<Remote>, RepositoryError>;
    /// Return the configured fetch upstream for a local branch.
    ///
    /// # Errors
    /// Returns a typed invalid-ref, config, or repository read failure.
    fn upstream(&self, branch: &RefName) -> Result<Option<Upstream>, RepositoryError>;
    /// Return symbolic, detached, or unborn `HEAD` state.
    ///
    /// # Errors
    /// Returns a typed corrupt-repository or read failure.
    fn head(&self) -> Result<Head, RepositoryError>;
    /// Resolve one supported revision expression to an object ID.
    ///
    /// # Errors
    /// Returns a typed input, resolution, or repository read failure.
    fn resolve_revision(&self, revision: &Revision) -> Result<ObjectId, RepositoryError>;
    /// Return all references, including packed references.
    ///
    /// # Errors
    /// Returns a typed corrupt-repository or read failure.
    fn references(&self) -> Result<Vec<Reference>, RepositoryError>;
    /// Load an object, or return `None` when its ID is absent.
    ///
    /// # Errors
    /// Returns a typed hash or repository read failure.
    fn object(&self, id: &ObjectId) -> Result<Option<Object>, RepositoryError>;
    /// Walk at most `limit` commits from `start`.
    ///
    /// # Errors
    /// Returns a typed hash, missing-object, or repository read failure.
    fn walk_commits(&self, start: &ObjectId, limit: usize) -> Result<Vec<Commit>, RepositoryError>;
    /// Count every commit reachable from `start`.
    ///
    /// # Errors
    /// Returns a typed hash, missing-object, or repository read failure.
    fn commit_count(&self, start: &ObjectId) -> Result<u64, RepositoryError>;
    /// Return the best merge base for two commits.
    ///
    /// # Errors
    /// Returns a typed hash, resolution, or repository read failure.
    fn merge_base(&self, left: &ObjectId, right: &ObjectId) -> Result<ObjectId, RepositoryError>;
    /// Report whether `ancestor` is reachable from `descendant`.
    ///
    /// # Errors
    /// Returns a typed hash, resolution, or repository read failure.
    fn is_ancestor(
        &self,
        ancestor: &ObjectId,
        descendant: &ObjectId,
    ) -> Result<bool, RepositoryError>;
    /// Return the main and linked worktree records.
    ///
    /// # Errors
    /// Returns a typed I/O or repository read failure.
    fn worktrees(&self) -> Result<Vec<Worktree>, RepositoryError>;
    /// Validate a name under the requested Git ref format.
    ///
    /// # Errors
    /// Returns `InvalidRef` when the name does not satisfy the format.
    fn validate_ref_name(&self, name: &RefName, format: RefFormat) -> Result<(), RepositoryError>;
}

#[cfg(test)]
mod tests {
    use super::{ConfigKey, ObjectHash, ObjectId, RepositoryErrorKind};

    #[test]
    fn object_ids_require_the_algorithm_digest_length() {
        assert!(ObjectId::new(ObjectHash::Sha1, [0; 20]).is_ok());
        assert!(ObjectId::new(ObjectHash::Sha256, [0; 32]).is_ok());
        assert_eq!(
            ObjectId::new(ObjectHash::Sha1, [0; 32]).unwrap_err().kind(),
            RepositoryErrorKind::InvalidInput
        );
    }

    #[test]
    fn config_keys_have_a_bounded_dotted_shape() {
        assert!(ConfigKey::new("core.bare").is_ok());
        assert!(ConfigKey::new("remote.origin.url").is_ok());
        assert!(ConfigKey::new("url.https://example.invalid/.insteadOf").is_ok());
        for invalid in ["", "core", ".bare", "core."] {
            assert_eq!(
                ConfigKey::new(invalid).unwrap_err().kind(),
                RepositoryErrorKind::InvalidInput
            );
        }
    }
}
