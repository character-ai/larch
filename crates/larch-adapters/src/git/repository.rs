//! Trusted `gix` implementation of the core repository metadata read port.

use std::path::{Path, PathBuf};

use gix::bstr::ByteSlice;
use larch_core::{
    Commit, ConfigKey, ConfigScope, ConfigValue, GitPath, Head, Object, ObjectHash, ObjectId,
    ObjectKind, RefFormat, RefName, Reference, ReferenceKind, ReferenceTarget, Remote,
    RepositoryError, RepositoryErrorKind, RepositoryLocation, RepositoryRead, Revision, Upstream,
    Worktree,
};

/// The only production repository metadata reader.
#[derive(Debug)]
pub struct GixRepository {
    git_dir: PathBuf,
    location: RepositoryLocation,
}

impl GixRepository {
    /// Open a repository at a known path with strict configuration and ownership checks.
    ///
    /// # Errors
    /// Returns a stable, redacted repository error class.
    pub fn open(path: impl AsRef<Path>) -> Result<Self, RepositoryError> {
        let repository = gix::ThreadSafeRepository::open_opts(path.as_ref(), read_options())
            .map_err(|error| map_open_error(&error))?;
        Ok(Self::from_repository(&repository))
    }

    /// Discover a repository from `path` or its ancestors with ownership checks enabled.
    ///
    /// # Errors
    /// Returns a stable, redacted repository error class.
    pub fn discover(path: impl AsRef<Path>) -> Result<Self, RepositoryError> {
        let options = read_options();
        let trust = gix::sec::trust::Mapping {
            full: options.clone(),
            reduced: options,
        };
        let repository = gix::ThreadSafeRepository::discover_opts(
            path.as_ref(),
            gix::discover::upwards::Options::default(),
            trust,
        )
        .map_err(|error| map_discover_error(&error))?;
        Ok(Self::from_repository(&repository))
    }

    fn from_repository(repository: &gix::ThreadSafeRepository) -> Self {
        let local = repository.to_thread_local();
        let location = RepositoryLocation {
            git_dir: path(local.path()),
            common_dir: path(local.common_dir()),
            work_dir: local.workdir().map(path),
            object_hash: hash_kind(local.object_hash()),
        };
        Self {
            git_dir: repository.path().to_owned(),
            location,
        }
    }

    fn local(&self) -> Result<gix::Repository, RepositoryError> {
        self.trusted()
            .map(|repository| repository.to_thread_local())
    }

    fn trusted(&self) -> Result<gix::ThreadSafeRepository, RepositoryError> {
        gix::ThreadSafeRepository::open_opts(&self.git_dir, read_options().open_path_as_is(true))
            .map_err(|error| map_open_error(&error))
    }
}

impl RepositoryRead for GixRepository {
    fn location(&self) -> RepositoryLocation {
        self.location.clone()
    }

    fn config_values(&self, key: &ConfigKey) -> Result<Vec<ConfigValue>, RepositoryError> {
        let repository = self.local()?;
        let config = repository.config_snapshot();
        let (section_name, subsection_name, value_name) = config_key_parts(key)?;
        let mut output = Vec::new();
        let Some(sections) = config.sections_by_name(section_name) else {
            return Ok(output);
        };
        for section in sections {
            let subsection = section.header().subsection_name().map(AsRef::as_ref);
            if subsection != subsection_name.map(str::as_bytes) {
                continue;
            }
            output.extend(
                section
                    .values(value_name)
                    .into_iter()
                    .map(|value| ConfigValue {
                        value: value.into_owned().into(),
                        scope: config_scope(section.meta().source),
                        include_depth: section.meta().level,
                    }),
            );
        }
        Ok(output)
    }

    fn remotes(&self) -> Result<Vec<Remote>, RepositoryError> {
        let repository = self.local()?;
        repository
            .remote_names()
            .into_iter()
            .map(|name| {
                let remote = repository
                    .find_remote(name.as_ref())
                    .map_err(|_| error(RepositoryErrorKind::MalformedConfig))?;
                Ok(Remote {
                    name: name.as_ref().to_vec(),
                    fetch_url: remote
                        .url(gix::remote::Direction::Fetch)
                        .map(|url| url.to_bstring().into()),
                    push_url: remote
                        .url(gix::remote::Direction::Push)
                        .map(|url| url.to_bstring().into()),
                })
            })
            .collect()
    }

    fn upstream(&self, branch: &RefName) -> Result<Option<Upstream>, RepositoryError> {
        let repository = self.local()?;
        let full_name: &gix::refs::FullNameRef = branch
            .as_bytes()
            .as_bstr()
            .try_into()
            .map_err(|_| error(RepositoryErrorKind::InvalidRef))?;
        if full_name.category() != Some(gix::refs::Category::LocalBranch) {
            return Err(error(RepositoryErrorKind::InvalidRef));
        }
        let Some(remote_ref) =
            repository.branch_remote_ref_name(full_name, gix::remote::Direction::Fetch)
        else {
            return Ok(None);
        };
        let remote_ref = remote_ref.map_err(|_| error(RepositoryErrorKind::MalformedConfig))?;
        let remote = repository
            .branch_remote_name(full_name.shorten(), gix::remote::Direction::Fetch)
            .ok_or_else(|| error(RepositoryErrorKind::MalformedConfig))?;
        let tracking_ref = repository
            .branch_remote_tracking_ref_name(full_name, gix::remote::Direction::Fetch)
            .transpose()
            .map_err(|_| error(RepositoryErrorKind::MalformedConfig))?
            .map(|name| RefName::new(name.as_bstr().to_vec()));
        Ok(Some(Upstream {
            remote: remote.as_bstr().to_vec(),
            remote_ref: RefName::new(remote_ref.as_bstr().to_vec()),
            tracking_ref,
        }))
    }

    fn head(&self) -> Result<Head, RepositoryError> {
        let repository = self.local()?;
        let head = repository
            .head()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        let referent = head
            .referent_name()
            .map(|name| RefName::new(name.as_bstr().to_vec()));
        match (head.is_unborn(), head.is_detached(), referent, head.id()) {
            (true, false, Some(name), None) => Ok(Head::Unborn { name }),
            (false, true, None, Some(target)) => Ok(Head::Detached {
                target: object_id(target.as_ref()),
            }),
            (false, false, Some(name), Some(target)) => Ok(Head::Symbolic {
                name,
                target: object_id(target.as_ref()),
            }),
            _ => Err(error(RepositoryErrorKind::CorruptRepository)),
        }
    }

    fn resolve_revision(&self, revision: &Revision) -> Result<ObjectId, RepositoryError> {
        let trusted = self.trusted()?;
        let objects_dir = trusted.objects_dir().to_owned();
        let repository = trusted.to_thread_local();
        let value = revision.as_bytes();
        if value.is_empty() || value.contains(&0) {
            return Err(error(RepositoryErrorKind::InvalidInput));
        }
        if value.windows(2).any(|pair| pair == b"..")
            || value.windows(3).any(|window| window == b"^{/")
            || value.contains(&b':')
        {
            return Err(error(RepositoryErrorKind::UnsupportedRevision));
        }
        if is_abbreviated_hex(value, repository.object_hash()) {
            match lookup_prefix(&objects_dir, repository.object_hash(), value)? {
                PrefixLookup::Missing => return Err(error(RepositoryErrorKind::RevisionNotFound)),
                PrefixLookup::Ambiguous => {
                    return Err(error(RepositoryErrorKind::AmbiguousRevision));
                }
                PrefixLookup::Unique => {}
            }
        }
        match repository.rev_parse_single(value.as_bstr()) {
            Ok(id) => Ok(object_id(id.as_ref())),
            Err(gix::revision::spec::parse::single::Error::RangedRev { .. }) => {
                Err(error(RepositoryErrorKind::UnsupportedRevision))
            }
            Err(gix::revision::spec::parse::single::Error::Parse(_)) => {
                Err(error(RepositoryErrorKind::RevisionNotFound))
            }
        }
    }

    fn references(&self) -> Result<Vec<Reference>, RepositoryError> {
        let repository = self.local()?;
        let platform = repository
            .references()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        let iter = platform
            .all()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        let mut output = Vec::new();
        for reference in iter {
            let reference = reference.map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
            let name = reference.name().as_bstr();
            let target = match reference.target() {
                gix::refs::TargetRef::Object(id) => ReferenceTarget::Object(object_id(id)),
                gix::refs::TargetRef::Symbolic(name) => {
                    ReferenceTarget::Symbolic(RefName::new(name.as_bstr().to_vec()))
                }
            };
            output.push(Reference {
                name: RefName::new(name.to_vec()),
                kind: reference_kind(name),
                target,
            });
        }
        output.sort_by(|left, right| left.name.cmp(&right.name));
        Ok(output)
    }

    fn object(&self, id: &ObjectId) -> Result<Option<Object>, RepositoryError> {
        let repository = self.local()?;
        let id = gix_id(id, repository.object_hash())?;
        let Some(object) = repository
            .try_find_object(id)
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?
        else {
            return Ok(None);
        };
        Ok(Some(Object {
            id: object_id(&object.id),
            kind: object_kind(object.kind),
            data: object.data.clone(),
        }))
    }

    fn walk_commits(&self, start: &ObjectId, limit: usize) -> Result<Vec<Commit>, RepositoryError> {
        let repository = self.local()?;
        let start = gix_id(start, repository.object_hash())?;
        let walk = repository
            .rev_walk([start])
            .all()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        walk.take(limit)
            .map(|info| {
                let info = info.map_err(|_| error(RepositoryErrorKind::MissingObject))?;
                Ok(Commit {
                    id: object_id(&info.id),
                    parents: info.parent_ids().map(|id| object_id(id.as_ref())).collect(),
                })
            })
            .collect()
    }

    fn commit_count(&self, start: &ObjectId) -> Result<u64, RepositoryError> {
        let repository = self.local()?;
        let start = gix_id(start, repository.object_hash())?;
        let walk = repository
            .rev_walk([start])
            .all()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        let mut count = 0_u64;
        for info in walk {
            info.map_err(|_| error(RepositoryErrorKind::MissingObject))?;
            count = count
                .checked_add(1)
                .ok_or_else(|| error(RepositoryErrorKind::CorruptRepository))?;
        }
        Ok(count)
    }

    fn merge_base(&self, left: &ObjectId, right: &ObjectId) -> Result<ObjectId, RepositoryError> {
        let repository = self.local()?;
        let left = gix_id(left, repository.object_hash())?;
        let right = gix_id(right, repository.object_hash())?;
        repository
            .merge_base(left, right)
            .map(|id| object_id(id.as_ref()))
            .map_err(|_| error(RepositoryErrorKind::RevisionNotFound))
    }

    fn is_ancestor(
        &self,
        ancestor: &ObjectId,
        descendant: &ObjectId,
    ) -> Result<bool, RepositoryError> {
        let repository = self.local()?;
        let ancestor = gix_id(ancestor, repository.object_hash())?;
        let descendant = gix_id(descendant, repository.object_hash())?;
        repository
            .merge_base(ancestor, descendant)
            .map(|base| base.as_ref() == ancestor)
            .map_err(|_| error(RepositoryErrorKind::RevisionNotFound))
    }

    fn worktrees(&self) -> Result<Vec<Worktree>, RepositoryError> {
        let repository = self.local()?;
        let mut output = Vec::new();
        let mut current_is_linked = false;
        if let Some(worktree) = repository.worktree() {
            current_is_linked = worktree.id().is_some();
            output.push(Worktree {
                id: worktree.id().map(|id| id.to_vec()),
                path: path(worktree.base()),
                git_dir: path(repository.path()),
                locked: worktree.is_locked(),
            });
        }
        if current_is_linked {
            let main = repository
                .main_repo()
                .map_err(|_| error(RepositoryErrorKind::Io))?;
            if let Some(worktree) = main.worktree() {
                output.push(Worktree {
                    id: None,
                    path: path(worktree.base()),
                    git_dir: path(main.path()),
                    locked: false,
                });
            }
        }
        for proxy in repository
            .worktrees()
            .map_err(|_| error(RepositoryErrorKind::Io))?
        {
            output.push(Worktree {
                id: Some(proxy.id().to_vec()),
                path: path(&proxy.base().map_err(|_| error(RepositoryErrorKind::Io))?),
                git_dir: path(proxy.git_dir()),
                locked: proxy.is_locked(),
            });
        }
        output.sort_by(|left, right| left.path.cmp(&right.path));
        output.dedup_by(|left, right| left.path == right.path);
        Ok(output)
    }

    fn validate_ref_name(&self, name: &RefName, format: RefFormat) -> Result<(), RepositoryError> {
        let name = name.as_bytes().as_bstr();
        let valid = match format {
            RefFormat::Full => gix::validate::reference::name(name).is_ok(),
            RefFormat::Branch => gix::validate::reference::branch_name(name).is_ok(),
            RefFormat::Tag => gix::validate::tag::name(name).is_ok(),
        };
        if valid {
            Ok(())
        } else {
            Err(error(RepositoryErrorKind::InvalidRef))
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum PrefixLookup {
    Missing,
    Unique,
    Ambiguous,
}

fn lookup_prefix(
    objects_dir: &Path,
    hash: gix::hash::Kind,
    value: &[u8],
) -> Result<PrefixLookup, RepositoryError> {
    let candidate = object_id_from_hex_prefix(value, hash)?;
    let prefix = gix::hash::Prefix::new(&candidate, value.len())
        .map_err(|_| error(RepositoryErrorKind::InvalidInput))?;
    let options = gix::odb::store::init::Options {
        object_hash: hash,
        ..Default::default()
    };
    let database =
        gix::odb::at_opts(objects_dir, [], options).map_err(|_| error(RepositoryErrorKind::Io))?;
    match database
        .lookup_prefix(prefix, None)
        .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?
    {
        None => Ok(PrefixLookup::Missing),
        Some(Ok(_)) => Ok(PrefixLookup::Unique),
        Some(Err(())) => Ok(PrefixLookup::Ambiguous),
    }
}

fn read_options() -> gix::open::Options {
    gix::open::Options::default()
        .bail_if_untrusted(true)
        .strict_config(true)
}

const fn map_open_error(open_error: &gix::open::Error) -> RepositoryError {
    match open_error {
        gix::open::Error::UnsafeGitDir { .. } => error(RepositoryErrorKind::UntrustedRepository),
        gix::open::Error::Config(_) => error(RepositoryErrorKind::MalformedConfig),
        gix::open::Error::NotARepository { .. } => error(RepositoryErrorKind::NotRepository),
        gix::open::Error::Io(_) | gix::open::Error::EnvironmentAccessDenied(_) => {
            error(RepositoryErrorKind::Io)
        }
        gix::open::Error::PrefixNotRelative(_) => error(RepositoryErrorKind::InvalidInput),
    }
}

const fn map_discover_error(discover_error: &gix::discover::Error) -> RepositoryError {
    match discover_error {
        gix::discover::Error::Open(error) => map_open_error(error),
        gix::discover::Error::Discover(upwards_error) => match upwards_error {
            gix::discover::upwards::Error::InvalidInput { .. }
            | gix::discover::upwards::Error::NoMatchingCeilingDir => {
                error(RepositoryErrorKind::InvalidInput)
            }
            gix::discover::upwards::Error::NoTrustedGitRepository { .. } => {
                error(RepositoryErrorKind::UntrustedRepository)
            }
            gix::discover::upwards::Error::NoGitRepository { .. }
            | gix::discover::upwards::Error::NoGitRepositoryWithinCeiling { .. }
            | gix::discover::upwards::Error::NoGitRepositoryWithinFs { .. } => {
                error(RepositoryErrorKind::NotRepository)
            }
            gix::discover::upwards::Error::CurrentDir(_)
            | gix::discover::upwards::Error::InaccessibleDirectory { .. }
            | gix::discover::upwards::Error::CheckTrust { .. } => error(RepositoryErrorKind::Io),
        },
    }
}

const fn error(kind: RepositoryErrorKind) -> RepositoryError {
    RepositoryError::new(kind)
}

fn path(value: &Path) -> GitPath {
    GitPath::new(gix::path::into_bstr(value).into_owned())
}

fn hash_kind(kind: gix::hash::Kind) -> ObjectHash {
    match kind {
        gix::hash::Kind::Sha1 => ObjectHash::Sha1,
        gix::hash::Kind::Sha256 => ObjectHash::Sha256,
        _ => unreachable!("the workspace enables only SHA-1 and SHA-256"),
    }
}

fn object_id(id: &gix::hash::oid) -> ObjectId {
    ObjectId::new(hash_kind(id.kind()), id.as_bytes().to_vec())
        .expect("gix object IDs have the algorithm's digest length")
}

fn gix_id(
    id: &ObjectId,
    repository_hash: gix::hash::Kind,
) -> Result<gix::ObjectId, RepositoryError> {
    if hash_kind(repository_hash) != id.hash() {
        return Err(error(RepositoryErrorKind::HashMismatch));
    }
    let mut output = gix::ObjectId::null(repository_hash);
    output.as_mut_slice().copy_from_slice(id.digest());
    Ok(output)
}

const fn object_kind(kind: gix::objs::Kind) -> ObjectKind {
    match kind {
        gix::objs::Kind::Blob => ObjectKind::Blob,
        gix::objs::Kind::Tree => ObjectKind::Tree,
        gix::objs::Kind::Commit => ObjectKind::Commit,
        gix::objs::Kind::Tag => ObjectKind::Tag,
    }
}

fn reference_kind(name: &gix::bstr::BStr) -> ReferenceKind {
    if name.starts_with(b"refs/heads/") {
        ReferenceKind::LocalBranch
    } else if name.starts_with(b"refs/remotes/") {
        ReferenceKind::RemoteBranch
    } else if name.starts_with(b"refs/tags/") {
        ReferenceKind::Tag
    } else {
        ReferenceKind::Other
    }
}

fn is_abbreviated_hex(value: &[u8], hash: gix::hash::Kind) -> bool {
    let full_len = match hash {
        gix::hash::Kind::Sha1 => 40,
        gix::hash::Kind::Sha256 => 64,
        _ => return false,
    };
    value.len() < full_len && value.len() >= 4 && value.iter().all(u8::is_ascii_hexdigit)
}

fn object_id_from_hex_prefix(
    value: &[u8],
    hash: gix::hash::Kind,
) -> Result<gix::ObjectId, RepositoryError> {
    let mut id = gix::ObjectId::null(hash);
    for (index, byte) in value.iter().copied().enumerate() {
        let nibble = match byte {
            b'0'..=b'9' => byte - b'0',
            b'a'..=b'f' => byte - b'a' + 10,
            b'A'..=b'F' => byte - b'A' + 10,
            _ => return Err(error(RepositoryErrorKind::InvalidInput)),
        };
        if index % 2 == 0 {
            id.as_mut_slice()[index / 2] = nibble << 4;
        } else {
            id.as_mut_slice()[index / 2] |= nibble;
        }
    }
    Ok(id)
}

fn config_key_parts(key: &ConfigKey) -> Result<(&str, Option<&str>, &str), RepositoryError> {
    let raw = key.as_str();
    let first = raw
        .find('.')
        .ok_or_else(|| error(RepositoryErrorKind::InvalidInput))?;
    let last = raw
        .rfind('.')
        .ok_or_else(|| error(RepositoryErrorKind::InvalidInput))?;
    let subsection = (first != last).then(|| &raw[first + 1..last]);
    Ok((&raw[..first], subsection, &raw[last + 1..]))
}

const fn config_scope(source: gix::config::Source) -> ConfigScope {
    match source {
        gix::config::Source::GitInstallation => ConfigScope::GitInstallation,
        gix::config::Source::System => ConfigScope::System,
        gix::config::Source::Git | gix::config::Source::User => ConfigScope::User,
        gix::config::Source::Local => ConfigScope::Repository,
        gix::config::Source::Worktree => ConfigScope::Worktree,
        gix::config::Source::Env | gix::config::Source::EnvOverride => ConfigScope::Environment,
        gix::config::Source::Cli => ConfigScope::CommandLine,
        gix::config::Source::Api => ConfigScope::Api,
    }
}

#[cfg(test)]
mod tests {
    use super::map_open_error;
    use larch_core::RepositoryErrorKind;
    use std::path::PathBuf;

    #[test]
    fn unsafe_repository_errors_do_not_render_the_path() {
        let secret_path = PathBuf::from("/private/credential-bearing/repository");
        let error = map_open_error(&gix::open::Error::UnsafeGitDir {
            path: secret_path.clone(),
        });

        assert_eq!(error.kind(), RepositoryErrorKind::UntrustedRepository);
        assert!(
            !error
                .to_string()
                .contains(secret_path.to_string_lossy().as_ref())
        );
    }
}
