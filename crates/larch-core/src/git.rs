//! Byte-oriented repository metadata types and the sole read port for Git state.

use std::{error::Error, fmt, fmt::Write as _};

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

    /// Render the complete lowercase hexadecimal object identifier.
    #[must_use]
    pub fn to_hex(&self) -> String {
        self.digest.iter().fold(
            String::with_capacity(self.digest.len() * 2),
            |mut output, byte| {
                let _ = write!(output, "{byte:02x}");
                output
            },
        )
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
    pub tree: ObjectId,
    pub subject: Vec<u8>,
}

/// One linked or main worktree.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Worktree {
    pub id: Option<Vec<u8>>,
    pub path: GitPath,
    pub git_dir: GitPath,
    pub locked: bool,
}

/// A raw Git tree or index mode.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub struct GitMode(u32);

impl GitMode {
    /// Preserve a mode without interpreting adapter-specific bitflags.
    #[must_use]
    pub const fn new(raw: u32) -> Self {
        Self(raw)
    }

    /// Return the raw mode bits.
    #[must_use]
    pub const fn raw(self) -> u32 {
        self.0
    }
}

/// The semantic kind of a typed repository change.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum ChangeKind {
    /// A path exists only in the destination.
    Added,
    /// A path exists only in the source.
    Deleted,
    /// Content or executable permission changed.
    Modified,
    /// The tree entry or filesystem kind changed.
    TypeChanged,
    /// A source path moved to a destination path.
    Renamed,
    /// A destination was copied from a source path.
    Copied,
    /// A gitlink target or submodule worktree changed.
    SubmoduleModified,
}

/// One byte-oriented tree, index, or worktree change.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Change {
    /// The semantic name-status kind.
    pub kind: ChangeKind,
    /// The destination path, or affected path for non-rewrites.
    pub path: GitPath,
    /// The source path for a rename or copy.
    pub source_path: Option<GitPath>,
    /// The source mode when available.
    pub old_mode: Option<GitMode>,
    /// The destination mode when available.
    pub new_mode: Option<GitMode>,
    /// The source object ID when available.
    pub old_id: Option<ObjectId>,
    /// The destination object ID when available.
    pub new_id: Option<ObjectId>,
    /// Flags from the relevant index entry, when this change crosses the index.
    pub index_flags: Option<IndexFlags>,
}

/// A deterministic name-status change set. `paths()` is its name-only view.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ChangeSet(Vec<Change>);

impl ChangeSet {
    /// Build a change set whose entries are already in deterministic order.
    #[must_use]
    pub const fn new(entries: Vec<Change>) -> Self {
        Self(entries)
    }

    /// Return typed name-status entries.
    #[must_use]
    pub fn entries(&self) -> &[Change] {
        &self.0
    }

    /// Return the destination paths used by name-only callers.
    pub fn paths(&self) -> impl Iterator<Item = &GitPath> {
        self.0.iter().map(|entry| &entry.path)
    }

    /// Report whether the set has no changes.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.0.is_empty()
    }
}

/// Persistent index flags callers need to interpret status safely.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct IndexFlags {
    /// Git may skip stat checks and assume the worktree matches.
    pub assume_valid: bool,
    /// The entry promises a future addition without an indexed blob.
    pub intent_to_add: bool,
    /// Sparse checkout omits the entry from the worktree.
    pub skip_worktree: bool,
}

/// One unconflicted entry currently recorded in the index.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TrackedEntry {
    /// The repository-relative byte path.
    pub path: GitPath,
    /// The raw index mode.
    pub mode: GitMode,
    /// The indexed object ID.
    pub id: ObjectId,
    /// Persistent caller-relevant index flags.
    pub flags: IndexFlags,
}

/// The safety class of one excluded worktree path.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IgnoreKind {
    /// The ignored path may be replaced by checkout-like operations.
    Expendable,
    /// The ignored path is marked for preservation by gitoxide semantics.
    Precious,
}

/// One ignored worktree entry.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IgnoredEntry {
    /// The repository-relative byte path.
    pub path: GitPath,
    /// Whether the ignored entry is expendable or precious.
    pub kind: IgnoreKind,
}

/// One conflict-stage entry from the index.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ConflictStage {
    /// Index stage 1 (base), 2 (ours), or 3 (theirs).
    pub stage: u8,
    /// The stage's raw index mode.
    pub mode: GitMode,
    /// The stage's object ID.
    pub id: ObjectId,
    /// The stage's persistent caller-relevant flags.
    pub flags: IndexFlags,
}

/// Git's stable conflict classification.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ConflictKind {
    /// Both sides deleted distinct versions.
    BothDeleted,
    /// Our side added while their side modified.
    AddedByUs,
    /// Their side deleted while our side modified.
    DeletedByThem,
    /// Their side added while our side modified.
    AddedByThem,
    /// Our side deleted while their side modified.
    DeletedByUs,
    /// Both sides added distinct versions.
    BothAdded,
    /// Both sides modified the entry differently.
    BothModified,
}

/// An unmerged path with every present base, ours, and theirs stage.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UnmergedEntry {
    /// The conflicted byte path.
    pub path: GitPath,
    /// The conflict classification.
    pub kind: ConflictKind,
    /// Every present base, ours, and theirs stage.
    pub stages: Vec<ConflictStage>,
}

/// Policy for one configured status iteration.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StatusOptions {
    /// Git pathspec patterns, interpreted from repository-relative byte paths.
    pub pathspecs: Vec<GitPath>,
    /// Include individual untracked files.
    pub include_untracked: bool,
    /// Include individual ignored files.
    pub include_ignored: bool,
}

impl Default for StatusOptions {
    fn default() -> Self {
        Self {
            pathspecs: Vec::new(),
            include_untracked: true,
            include_ignored: false,
        }
    }
}

/// Typed changes across `HEAD`, the index, and the worktree.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RepositoryStatus {
    /// Unconflicted tracked entries selected by the pathspec.
    pub tracked: Vec<TrackedEntry>,
    /// Changes from `HEAD`'s tree to the index.
    pub tree_to_index: ChangeSet,
    /// Changes from the index to the worktree.
    pub index_to_worktree: ChangeSet,
    /// Untracked paths selected by policy and pathspec.
    pub untracked: Vec<GitPath>,
    /// Ignored entries selected by policy and pathspec.
    pub ignored: Vec<IgnoredEntry>,
    /// Conflicted paths, kept separate from ordinary change sets.
    pub unmerged: Vec<UnmergedEntry>,
}

impl RepositoryStatus {
    /// Match larch's dirty policy. Ignored paths alone do not make a repository dirty.
    #[must_use]
    pub const fn is_dirty(&self) -> bool {
        !self.tree_to_index.is_empty()
            || !self.index_to_worktree.is_empty()
            || !self.untracked.is_empty()
            || !self.unmerged.is_empty()
    }
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
    UnsupportedSemantics,
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
            RepositoryErrorKind::UnsupportedSemantics => {
                "repository operation requires exact Git compatibility"
            }
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
    /// Walk commits reachable from `include` but not from `exclude`.
    ///
    /// # Errors
    /// Returns a typed hash, missing-object, or repository read failure.
    fn walk_commits_range(
        &self,
        exclude: &ObjectId,
        include: &ObjectId,
        limit: usize,
    ) -> Result<Vec<Commit>, RepositoryError>;
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
    /// Return typed staged, unstaged, untracked, ignored, and unmerged state.
    ///
    /// # Errors
    /// Returns a typed failure for corrupt state or semantics that require the exact-diff adapter.
    fn status(&self, options: &StatusOptions) -> Result<RepositoryStatus, RepositoryError>;
    /// Compare two tree object IDs with configured rename and copy behavior.
    ///
    /// # Errors
    /// Returns a typed missing-object, object-type, or unsupported-semantics failure.
    fn tree_changes(
        &self,
        old_tree: &ObjectId,
        new_tree: &ObjectId,
    ) -> Result<ChangeSet, RepositoryError>;
    /// Read one blob from a commit tree by repository-relative byte path.
    ///
    /// # Errors
    /// Returns a typed hash, path, object-type, or repository read failure.
    fn blob_at_commit(
        &self,
        commit: &ObjectId,
        path: &GitPath,
    ) -> Result<Option<Vec<u8>>, RepositoryError>;
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
        let sha1 = ObjectId::new(ObjectHash::Sha1, [0xab; 20]).unwrap();
        assert_eq!(sha1.to_hex(), "abababababababababababababababababababab");
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
