//! Trusted `gix` implementation of the core repository metadata read port.

use std::path::{Path, PathBuf};

use gix::bstr::ByteSlice;
use larch_core::{
    Change, ChangeKind, ChangeSet, Commit, ConfigKey, ConfigScope, ConfigValue, ConflictKind,
    ConflictStage, GitMode, GitPath, Head, IgnoreKind, IgnoredEntry, IndexFlags, Object,
    ObjectHash, ObjectId, ObjectKind, RefFormat, RefName, Reference, ReferenceKind,
    ReferenceTarget, Remote, RepositoryError, RepositoryErrorKind, RepositoryLocation,
    RepositoryRead, RepositoryStatus, Revision, StatusOptions, TrackedEntry, UnmergedEntry,
    Upstream, Worktree,
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

    /// Return every path represented in the repository index.
    ///
    /// # Errors
    ///
    /// Returns a stable, redacted repository error when the trusted repository
    /// cannot read its index.
    pub fn tracked_paths(&self) -> Result<Vec<GitPath>, RepositoryError> {
        let repository = self.local()?;
        let index = repository
            .index()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        let mut paths: Vec<GitPath> = index
            .entries()
            .iter()
            .map(|entry| GitPath::new(entry.path(&index).to_vec()))
            .collect();
        paths.sort();
        paths.dedup();
        Ok(paths)
    }

    /// Return local status for a compatibility command without interpreting diff text.
    ///
    /// This deliberately retains configured filters in the gix traversal: these
    /// commands report only status and untracked names, unlike callers that need
    /// exact diff semantics and must use the strict port method below.
    ///
    /// # Errors
    ///
    /// Returns the same typed discovery, index, or status failure as the strict
    /// repository-read port.
    pub fn local_status(
        &self,
        options: &StatusOptions,
    ) -> Result<RepositoryStatus, RepositoryError> {
        self.status_with_policy(options, false)
    }

    fn status_with_policy(
        &self,
        options: &StatusOptions,
        reject_unsupported_semantics: bool,
    ) -> Result<RepositoryStatus, RepositoryError> {
        let repository = self.local()?;
        if reject_unsupported_semantics {
            reject_unsupported_status_semantics(&repository)?;
        }
        let index = repository
            .index_or_empty()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        let untracked = if options.include_untracked || options.include_ignored {
            gix::status::UntrackedFiles::Files
        } else {
            gix::status::UntrackedFiles::None
        };
        let mut platform = repository
            .status(gix::progress::Discard)
            .map_err(|_| error(RepositoryErrorKind::MalformedConfig))?
            .index(gix::worktree::IndexPersistedOrInMemory::Persisted(
                index.clone(),
            ))
            .untracked_files(untracked);
        if options.include_ignored {
            platform = platform.dirwalk_options(|dirwalk| {
                dirwalk.emit_ignored(Some(gix::dir::walk::EmissionMode::Matching))
            });
        }
        let patterns = options
            .pathspecs
            .iter()
            .map(|path| path.as_bytes().into())
            .collect::<Vec<gix::bstr::BString>>();
        let tracked = tracked_entries(&repository, &index, &patterns)?;
        let iter = platform
            .into_iter(patterns)
            .map_err(|error_value| map_status_init_error(&error_value))?;
        let mut staged = Vec::new();
        let mut unstaged = Vec::new();
        let mut untracked_paths = Vec::new();
        let mut ignored = Vec::new();
        let mut unmerged = Vec::new();
        for item in iter {
            match item.map_err(|error_value| map_status_item_error(&error_value))? {
                gix::status::Item::TreeIndex(change) => staged.push(index_change(change, &index)),
                gix::status::Item::IndexWorktree(item) => collect_worktree_item(
                    item,
                    &mut unstaged,
                    &mut untracked_paths,
                    &mut ignored,
                    &mut unmerged,
                ),
            }
        }
        unmerged.sort_by(|left, right| left.path.cmp(&right.path));
        staged.retain(|change| !unmerged.iter().any(|entry| entry.path == change.path));
        unstaged.retain(|change| !unmerged.iter().any(|entry| entry.path == change.path));
        sort_changes(&mut staged);
        sort_changes(&mut unstaged);
        untracked_paths.sort();
        untracked_paths.dedup();
        if !options.include_untracked {
            untracked_paths.clear();
        }
        ignored.sort_by(|left, right| left.path.cmp(&right.path));
        ignored.dedup_by(|left, right| left.path == right.path);
        Ok(RepositoryStatus {
            tracked,
            tree_to_index: ChangeSet::new(staged),
            index_to_worktree: ChangeSet::new(unstaged),
            untracked: untracked_paths,
            ignored,
            unmerged,
        })
    }

    /// Read the blob bytes stored at an index conflict stage for `path`.
    ///
    /// `stage` must be 1 (base), 2 (ours), or 3 (theirs), matching `git show :N:path`.
    ///
    /// # Errors
    ///
    /// Returns `RevisionNotFound` when the path/stage is absent, or a stable
    /// repository error when the index or object store cannot be read.
    pub fn stage_blob(&self, path: &[u8], stage: u8) -> Result<Vec<u8>, RepositoryError> {
        let wanted = match stage {
            1 => gix::index::entry::Stage::Base,
            2 => gix::index::entry::Stage::Ours,
            3 => gix::index::entry::Stage::Theirs,
            _ => return Err(error(RepositoryErrorKind::InvalidInput)),
        };
        let repository = self.local()?;
        let index = repository
            .index()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        let entry = index
            .entries()
            .iter()
            .find(|entry| entry.stage() == wanted && entry.path(&index) == path.as_bstr())
            .ok_or_else(|| error(RepositoryErrorKind::RevisionNotFound))?;
        let object = repository
            .find_object(entry.id)
            .map_err(|_| error(RepositoryErrorKind::MissingObject))?;
        Ok(object.data.clone())
    }

    /// Count commits reachable from `include` and not from `exclude` (`exclude..include`).
    ///
    /// # Errors
    ///
    /// Returns a typed hash, missing-object, or repository read failure.
    pub fn commit_count_range(
        &self,
        exclude: &ObjectId,
        include: &ObjectId,
    ) -> Result<u64, RepositoryError> {
        let repository = self.local()?;
        let start = gix_id(include, repository.object_hash())?;
        let hidden = gix_id(exclude, repository.object_hash())?;
        let walk = repository
            .rev_walk([start])
            .with_hidden([hidden])
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

    /// Return the whole message of every commit reachable from `include` and
    /// not from `exclude`, which is `git log --format=%B exclude..include`.
    ///
    /// `exclude` is optional so a caller can ask for everything reachable from
    /// one revision, which is what a bare `HEAD` range means. Whole messages,
    /// not subjects, because the breadcrumbs the disposition gate counts are
    /// written in the commit body.
    ///
    /// # Errors
    /// Returns a typed hash, missing-object, object-type, or repository read
    /// failure.
    pub fn commit_messages_range(
        &self,
        exclude: Option<&ObjectId>,
        include: &ObjectId,
    ) -> Result<Vec<Vec<u8>>, RepositoryError> {
        let repository = self.local()?;
        let start = gix_id(include, repository.object_hash())?;
        let mut walk = repository.rev_walk([start]);
        if let Some(exclude) = exclude {
            walk = walk.with_hidden([gix_id(exclude, repository.object_hash())?]);
        }
        let walk = walk
            .all()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        let mut messages = Vec::new();
        for info in walk {
            let info = info.map_err(|_| error(RepositoryErrorKind::MissingObject))?;
            let commit = repository
                .find_commit(info.id)
                .map_err(|_| error(RepositoryErrorKind::MissingObject))?;
            messages.push(
                commit
                    .message_raw()
                    .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?
                    .to_vec(),
            );
        }
        Ok(messages)
    }

    /// Return the raw first line of every commit reachable from `include` and
    /// not from `exclude` (`exclude..include`).
    ///
    /// # Errors
    /// Returns a typed hash, missing-object, object-type, or repository read
    /// failure.
    pub fn commit_subjects_range(
        &self,
        exclude: &ObjectId,
        include: &ObjectId,
    ) -> Result<Vec<Vec<u8>>, RepositoryError> {
        let repository = self.local()?;
        let start = gix_id(include, repository.object_hash())?;
        let hidden = gix_id(exclude, repository.object_hash())?;
        let walk = repository
            .rev_walk([start])
            .with_hidden([hidden])
            .all()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        let mut subjects = Vec::new();
        for info in walk {
            let info = info.map_err(|_| error(RepositoryErrorKind::MissingObject))?;
            let object = repository
                .find_object(info.id)
                .map_err(|_| error(RepositoryErrorKind::MissingObject))?;
            if object.kind != gix::objs::Kind::Commit {
                return Err(error(RepositoryErrorKind::ObjectType));
            }
            let body_start = object
                .data
                .windows(2)
                .position(|window| window == b"\n\n")
                .map_or(object.data.len(), |index| index + 2);
            let subject_end = object.data[body_start..]
                .iter()
                .position(|byte| *byte == b'\n')
                .map_or(object.data.len(), |index| body_start + index);
            subjects.push(object.data[body_start..subject_end].to_vec());
        }
        Ok(subjects)
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
                commit_record(&repository, &info)
            })
            .collect()
    }

    fn walk_commits_range(
        &self,
        exclude: &ObjectId,
        include: &ObjectId,
        limit: usize,
    ) -> Result<Vec<Commit>, RepositoryError> {
        let repository = self.local()?;
        let start = gix_id(include, repository.object_hash())?;
        let hidden = gix_id(exclude, repository.object_hash())?;
        let walk = repository
            .rev_walk([start])
            .with_hidden([hidden])
            .all()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        walk.take(limit)
            .map(|info| {
                let info = info.map_err(|_| error(RepositoryErrorKind::MissingObject))?;
                commit_record(&repository, &info)
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

    fn status(&self, options: &StatusOptions) -> Result<RepositoryStatus, RepositoryError> {
        self.status_with_policy(options, true)
    }

    fn tree_changes(
        &self,
        old_tree: &ObjectId,
        new_tree: &ObjectId,
    ) -> Result<ChangeSet, RepositoryError> {
        let repository = self.local()?;
        reject_external_diff_drivers(&repository)?;
        let old = repository
            .try_find_object(gix_id(old_tree, repository.object_hash())?)
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?
            .ok_or_else(|| error(RepositoryErrorKind::MissingObject))?
            .try_into_tree()
            .map_err(|_| error(RepositoryErrorKind::ObjectType))?;
        let new = repository
            .try_find_object(gix_id(new_tree, repository.object_hash())?)
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?
            .ok_or_else(|| error(RepositoryErrorKind::MissingObject))?
            .try_into_tree()
            .map_err(|_| error(RepositoryErrorKind::ObjectType))?;
        let mut changes = Vec::new();
        let mut configured = old
            .changes()
            .map_err(|_| error(RepositoryErrorKind::MalformedConfig))?;
        configured
            .for_each_to_obtain_tree(&new, |change| {
                changes.push(tree_change(change));
                Ok::<_, std::convert::Infallible>(std::ops::ControlFlow::Continue(()))
            })
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        let copy_sources = changes
            .iter()
            .filter(|change| change.kind == ChangeKind::Copied)
            .filter_map(|change| change.source_path.clone())
            .collect::<Vec<_>>();
        if !copy_sources.is_empty() {
            let mut without_rewrites = old
                .changes()
                .map_err(|_| error(RepositoryErrorKind::MalformedConfig))?;
            without_rewrites.options(|options| {
                options.track_rewrites(None);
            });
            without_rewrites
                .for_each_to_obtain_tree(&new, |change| {
                    let change = tree_change(change);
                    if copy_sources.contains(&change.path)
                        && !changes.iter().any(|existing| {
                            existing.path == change.path && existing.kind == change.kind
                        })
                        && matches!(
                            change.kind,
                            ChangeKind::Modified
                                | ChangeKind::TypeChanged
                                | ChangeKind::SubmoduleModified
                        )
                    {
                        changes.push(change);
                    }
                    Ok::<_, std::convert::Infallible>(std::ops::ControlFlow::Continue(()))
                })
                .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        }
        sort_changes(&mut changes);
        Ok(ChangeSet::new(changes))
    }

    fn blob_at_commit(
        &self,
        commit: &ObjectId,
        path: &GitPath,
    ) -> Result<Option<Vec<u8>>, RepositoryError> {
        if path.as_bytes().is_empty() || path.as_bytes().contains(&0) {
            return Err(error(RepositoryErrorKind::InvalidInput));
        }
        let repository = self.local()?;
        let commit = repository
            .find_commit(gix_id(commit, repository.object_hash())?)
            .map_err(|_| error(RepositoryErrorKind::MissingObject))?;
        let tree = commit
            .tree()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
        let Some(entry) = tree
            .lookup_entry(path.as_bytes().split(|byte| *byte == b'/'))
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?
        else {
            return Ok(None);
        };
        if !entry.mode().is_blob() {
            return Err(error(RepositoryErrorKind::ObjectType));
        }
        entry
            .object()
            .map(|object| Some(object.data.clone()))
            .map_err(|_| error(RepositoryErrorKind::MissingObject))
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

fn commit_record(
    repository: &gix::Repository,
    info: &gix::revision::walk::Info,
) -> Result<Commit, RepositoryError> {
    let commit = repository
        .find_commit(info.id)
        .map_err(|_| error(RepositoryErrorKind::MissingObject))?;
    Ok(Commit {
        id: object_id(&info.id),
        parents: info.parent_ids().map(|id| object_id(id.as_ref())).collect(),
        tree: object_id(
            commit
                .tree_id()
                .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?
                .as_ref(),
        ),
        subject: commit
            .message_raw()
            .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?
            .lines()
            .next()
            .unwrap_or_default()
            .to_vec(),
    })
}

fn reject_unsupported_status_semantics(
    repository: &gix::Repository,
) -> Result<(), RepositoryError> {
    let config = repository.config_snapshot();
    let external_filters = config.sections_by_name("filter").is_some_and(|sections| {
        sections
            .into_iter()
            .any(|section| section.value("clean").is_some() || section.value("process").is_some())
    });
    let repository_filters = config.sections_by_name("filter").is_some_and(|sections| {
        sections.into_iter().any(|section| {
            matches!(
                section.meta().source,
                gix::config::Source::Local | gix::config::Source::Worktree
            ) && (section.value("clean").is_some() || section.value("process").is_some())
        })
    });
    let attributes = attribute_semantics(repository)?;
    if repository_filters || attributes.conversion || attributes.filter && external_filters {
        return Err(error(RepositoryErrorKind::UnsupportedSemantics));
    }
    Ok(())
}

#[derive(Clone, Copy, Debug, Default)]
struct AttributeSemantics {
    conversion: bool,
    filter: bool,
}

fn attribute_semantics(
    repository: &gix::Repository,
) -> Result<AttributeSemantics, RepositoryError> {
    const ENTRY_MAX: usize = 1_000_000;
    let index = repository
        .index_or_empty()
        .map_err(|_| error(RepositoryErrorKind::CorruptRepository))?;
    let mut stack = repository
        .attributes_only(
            &index,
            gix::worktree::stack::state::attributes::Source::WorktreeThenIdMapping,
        )
        .map_err(|_| error(RepositoryErrorKind::MalformedConfig))?;
    let mut output = AttributeSemantics::default();
    for entry in index.entries() {
        merge_path_attribute_semantics(
            &mut stack,
            gix::path::from_bstr(entry.path(&index)),
            Some(entry.mode),
            &mut output,
        )?;
    }
    let Some(workdir) = repository.workdir() else {
        return Ok(output);
    };
    let mut pending = vec![workdir.to_owned()];
    let mut entries_seen = 0_usize;
    while let Some(directory) = pending.pop() {
        let entries = std::fs::read_dir(directory).map_err(|_| error(RepositoryErrorKind::Io))?;
        for entry in entries {
            let entry = entry.map_err(|_| error(RepositoryErrorKind::Io))?;
            entries_seen = entries_seen
                .checked_add(1)
                .ok_or_else(|| error(RepositoryErrorKind::UnsupportedSemantics))?;
            if entries_seen > ENTRY_MAX {
                return Err(error(RepositoryErrorKind::UnsupportedSemantics));
            }
            let file_type = entry
                .file_type()
                .map_err(|_| error(RepositoryErrorKind::Io))?;
            if file_type.is_dir() {
                let name = entry.file_name();
                let path = entry.path();
                let is_dot_git = name.to_string_lossy().as_ref().eq_ignore_ascii_case(".git");
                let is_nested_repository = std::fs::symlink_metadata(path.join(".git")).is_ok();
                if !is_dot_git && !is_nested_repository {
                    pending.push(path);
                }
                continue;
            }
            if !file_type.is_file() {
                continue;
            }
            let relative = entry
                .path()
                .strip_prefix(workdir)
                .map_err(|_| error(RepositoryErrorKind::Io))?
                .to_owned();
            merge_path_attribute_semantics(&mut stack, relative, None, &mut output)?;
        }
    }
    Ok(output)
}

fn merge_path_attribute_semantics(
    stack: &mut gix::AttributeStack<'_>,
    path: impl AsRef<Path>,
    mode: Option<gix::index::entry::Mode>,
    output: &mut AttributeSemantics,
) -> Result<(), RepositoryError> {
    let mut matches = stack.selected_attribute_matches([
        "text",
        "eol",
        "crlf",
        "ident",
        "working-tree-encoding",
        "filter",
    ]);
    stack
        .at_path(path, mode)
        .map_err(|_| error(RepositoryErrorKind::Io))?
        .matching_attributes(&mut matches);
    for match_value in matches.iter_selected() {
        if matches!(
            match_value.assignment.state,
            gix::attrs::StateRef::Unspecified
        ) {
            continue;
        }
        if match_value.assignment.name.as_str() == "filter" {
            output.filter = true;
        } else {
            output.conversion = true;
        }
    }
    Ok(())
}

fn reject_external_diff_drivers(repository: &gix::Repository) -> Result<(), RepositoryError> {
    let config = repository.config_snapshot();
    if config.sections_by_name("diff").is_some_and(|sections| {
        sections.into_iter().any(|section| {
            matches!(
                section.meta().source,
                gix::config::Source::Local | gix::config::Source::Worktree
            ) && section.header().subsection_name().is_some()
                && (section.value("command").is_some() || section.value("textconv").is_some())
        })
    }) {
        return Err(error(RepositoryErrorKind::UnsupportedSemantics));
    }
    Ok(())
}

fn tracked_entries(
    repository: &gix::Repository,
    index: &gix::index::State,
    patterns: &[gix::bstr::BString],
) -> Result<Vec<TrackedEntry>, RepositoryError> {
    let mut pathspec = repository
        .pathspec(
            true,
            patterns,
            true,
            index,
            gix::worktree::stack::state::attributes::Source::WorktreeThenIdMapping,
        )
        .map_err(|_| error(RepositoryErrorKind::InvalidInput))?;
    let mut output = index
        .entries()
        .iter()
        .filter(|entry| entry.stage() == gix::index::entry::Stage::Unconflicted)
        .filter(|entry| {
            pathspec.is_included(
                entry.path(index),
                Some(entry.mode == gix::index::entry::Mode::DIR),
            )
        })
        .map(|entry| TrackedEntry {
            path: GitPath::new(entry.path(index).to_vec()),
            mode: GitMode::new(entry.mode.bits()),
            id: object_id(&entry.id),
            flags: index_flags(entry.flags),
        })
        .collect::<Vec<_>>();
    output.sort_by(|left, right| left.path.cmp(&right.path));
    Ok(output)
}

const fn map_status_init_error(error_value: &gix::status::into_iter::Error) -> RepositoryError {
    match error_value {
        gix::status::into_iter::Error::HeadTreeDiff(
            gix::status::tree_index::Error::TreeIndexDiff(gix::diff::index::Error::IsSparse),
        ) => error(RepositoryErrorKind::UnsupportedSemantics),
        gix::status::into_iter::Error::Pathspec(_) => error(RepositoryErrorKind::InvalidInput),
        gix::status::into_iter::Error::ConfigSkipHash(_)
        | gix::status::into_iter::Error::PrepareSubmodules(_) => {
            error(RepositoryErrorKind::MalformedConfig)
        }
        _ => error(RepositoryErrorKind::CorruptRepository),
    }
}

const fn map_status_item_error(error_value: &gix::status::iter::Error) -> RepositoryError {
    match error_value {
        gix::status::iter::Error::TreeIndex(gix::status::tree_index::Error::TreeIndexDiff(
            gix::diff::index::Error::IsSparse,
        )) => error(RepositoryErrorKind::UnsupportedSemantics),
        _ => error(RepositoryErrorKind::CorruptRepository),
    }
}

fn collect_worktree_item(
    item: gix::status::index_worktree::Item,
    changes: &mut Vec<Change>,
    untracked: &mut Vec<GitPath>,
    ignored: &mut Vec<IgnoredEntry>,
    unmerged: &mut Vec<UnmergedEntry>,
) {
    use gix::status::index_worktree::Item;
    use gix::status::plumbing::index_as_worktree::{Change as WorktreeChange, EntryStatus};
    match item {
        Item::Modification {
            entry,
            rela_path,
            status,
            ..
        } => match status {
            EntryStatus::Conflict { summary, entries } => {
                let stages = entries
                    .iter()
                    .enumerate()
                    .filter_map(|(index, entry)| {
                        entry.as_ref().map(|entry| ConflictStage {
                            stage: u8::try_from(index + 1).expect("three conflict stages"),
                            mode: GitMode::new(entry.mode.bits()),
                            id: object_id(&entry.id),
                            flags: index_flags(entry.flags),
                        })
                    })
                    .collect();
                unmerged.push(UnmergedEntry {
                    path: GitPath::new(rela_path.to_vec()),
                    kind: conflict_kind(summary),
                    stages,
                });
            }
            EntryStatus::Change(change) => {
                let old_mode = entry.mode.bits();
                let (kind, new_mode) = match change {
                    WorktreeChange::Removed => (ChangeKind::Deleted, None),
                    WorktreeChange::Type { worktree_mode } => {
                        (ChangeKind::TypeChanged, Some(worktree_mode.bits()))
                    }
                    WorktreeChange::Modification {
                        executable_bit_changed,
                        ..
                    } => {
                        let mode =
                            executable_bit_changed.then(|| toggled_executable_mode(old_mode));
                        (ChangeKind::Modified, mode.or(Some(old_mode)))
                    }
                    WorktreeChange::SubmoduleModification(_) => {
                        (ChangeKind::SubmoduleModified, Some(old_mode))
                    }
                };
                changes.push(Change {
                    kind,
                    path: GitPath::new(rela_path.to_vec()),
                    source_path: None,
                    old_mode: Some(GitMode::new(old_mode)),
                    new_mode: new_mode.map(GitMode::new),
                    old_id: Some(object_id(&entry.id)),
                    new_id: None,
                    index_flags: Some(index_flags(entry.flags)),
                });
            }
            EntryStatus::IntentToAdd => changes.push(Change {
                kind: ChangeKind::Added,
                path: GitPath::new(rela_path.to_vec()),
                source_path: None,
                old_mode: None,
                new_mode: Some(GitMode::new(entry.mode.bits())),
                old_id: None,
                new_id: None,
                index_flags: Some(index_flags(entry.flags)),
            }),
            EntryStatus::NeedsUpdate(_) => {}
        },
        Item::DirectoryContents { entry, .. } => {
            collect_directory_entry(&entry, untracked, ignored);
        }
        Item::Rewrite {
            source,
            dirwalk_entry,
            dirwalk_entry_id,
            copy,
            ..
        } => changes.push(worktree_rewrite(
            &source,
            &dirwalk_entry,
            &dirwalk_entry_id,
            copy,
        )),
    }
}

fn collect_directory_entry(
    entry: &gix::dir::Entry,
    untracked: &mut Vec<GitPath>,
    ignored: &mut Vec<IgnoredEntry>,
) {
    match entry.status {
        gix::dir::entry::Status::Untracked => {
            untracked.push(GitPath::new(entry.rela_path.to_vec()));
        }
        gix::dir::entry::Status::Ignored(kind) => ignored.push(IgnoredEntry {
            path: GitPath::new(entry.rela_path.to_vec()),
            kind: match kind {
                gix::ignore::Kind::Expendable => IgnoreKind::Expendable,
                gix::ignore::Kind::Precious => IgnoreKind::Precious,
            },
        }),
        gix::dir::entry::Status::Pruned | gix::dir::entry::Status::Tracked => {}
    }
}

fn worktree_rewrite(
    source: &gix::status::index_worktree::RewriteSource,
    destination: &gix::dir::Entry,
    destination_id: &gix::hash::ObjectId,
    copy: bool,
) -> Change {
    Change {
        kind: if copy {
            ChangeKind::Copied
        } else {
            ChangeKind::Renamed
        },
        path: GitPath::new(destination.rela_path.to_vec()),
        source_path: Some(GitPath::new(source.rela_path().to_vec())),
        old_mode: None,
        new_mode: None,
        old_id: None,
        new_id: (!destination_id.is_null()).then(|| object_id(destination_id)),
        index_flags: rewrite_source_flags(source),
    }
}

fn index_change(change: gix::diff::index::Change, index: &gix::index::State) -> Change {
    use gix::diff::index::Change;
    match change {
        Change::Addition {
            location,
            index: entry_index,
            entry_mode,
            id,
            ..
        } => with_index_flags(
            typed_change(
                ChangeKind::Added,
                location.as_ref(),
                None,
                None,
                Some(entry_mode.bits()),
                None,
                Some(id.as_ref()),
            ),
            index_flags(index.entries()[entry_index].flags),
        ),
        Change::Deletion {
            location,
            entry_mode,
            id,
            ..
        } => typed_change(
            ChangeKind::Deleted,
            location.as_ref(),
            None,
            Some(entry_mode.bits()),
            None,
            Some(id.as_ref()),
            None,
        ),
        Change::Modification {
            location,
            index: entry_index,
            previous_entry_mode,
            previous_id,
            entry_mode,
            id,
            ..
        } => with_index_flags(
            typed_change(
                modified_kind(previous_entry_mode.bits(), entry_mode.bits()),
                location.as_ref(),
                None,
                Some(previous_entry_mode.bits()),
                Some(entry_mode.bits()),
                Some(previous_id.as_ref()),
                Some(id.as_ref()),
            ),
            index_flags(index.entries()[entry_index].flags),
        ),
        Change::Rewrite {
            source_location,
            source_entry_mode,
            source_id,
            location,
            index: entry_index,
            entry_mode,
            id,
            copy,
            ..
        } => with_index_flags(
            typed_change(
                if copy {
                    ChangeKind::Copied
                } else {
                    ChangeKind::Renamed
                },
                location.as_ref(),
                Some(source_location.as_ref()),
                Some(source_entry_mode.bits()),
                Some(entry_mode.bits()),
                Some(source_id.as_ref()),
                Some(id.as_ref()),
            ),
            index_flags(index.entries()[entry_index].flags),
        ),
    }
}

fn tree_change(change: gix::object::tree::diff::Change<'_, '_, '_>) -> Change {
    use gix::object::tree::diff::Change;
    match change {
        Change::Addition {
            location,
            entry_mode,
            id,
            ..
        } => typed_change(
            ChangeKind::Added,
            location,
            None,
            None,
            Some(u32::from(entry_mode.value())),
            None,
            Some(id.as_ref()),
        ),
        Change::Deletion {
            location,
            entry_mode,
            id,
            ..
        } => typed_change(
            ChangeKind::Deleted,
            location,
            None,
            Some(u32::from(entry_mode.value())),
            None,
            Some(id.as_ref()),
            None,
        ),
        Change::Modification {
            location,
            previous_entry_mode,
            previous_id,
            entry_mode,
            id,
        } => typed_change(
            modified_kind(
                u32::from(previous_entry_mode.value()),
                u32::from(entry_mode.value()),
            ),
            location,
            None,
            Some(u32::from(previous_entry_mode.value())),
            Some(u32::from(entry_mode.value())),
            Some(previous_id.as_ref()),
            Some(id.as_ref()),
        ),
        Change::Rewrite {
            source_location,
            source_entry_mode,
            source_id,
            location,
            entry_mode,
            id,
            copy,
            ..
        } => typed_change(
            if copy {
                ChangeKind::Copied
            } else {
                ChangeKind::Renamed
            },
            location,
            Some(source_location),
            Some(u32::from(source_entry_mode.value())),
            Some(u32::from(entry_mode.value())),
            Some(source_id.as_ref()),
            Some(id.as_ref()),
        ),
    }
}

fn typed_change(
    kind: ChangeKind,
    path_value: &[u8],
    source_path: Option<&[u8]>,
    old_mode: Option<u32>,
    new_mode: Option<u32>,
    old_id: Option<&gix::hash::oid>,
    new_id: Option<&gix::hash::oid>,
) -> Change {
    Change {
        kind,
        path: GitPath::new(path_value),
        source_path: source_path.map(GitPath::new),
        old_mode: old_mode.map(GitMode::new),
        new_mode: new_mode.map(GitMode::new),
        old_id: old_id.map(object_id),
        new_id: new_id.map(object_id),
        index_flags: None,
    }
}

const fn with_index_flags(mut change: Change, flags: IndexFlags) -> Change {
    change.index_flags = Some(flags);
    change
}

const fn rewrite_source_flags(
    source: &gix::status::index_worktree::RewriteSource,
) -> Option<IndexFlags> {
    use gix::status::index_worktree::RewriteSource;
    match source {
        RewriteSource::RewriteFromIndex { source_entry, .. } => {
            Some(index_flags(source_entry.flags))
        }
        RewriteSource::CopyFromDirectoryEntry { .. } => None,
    }
}

const fn modified_kind(old_mode: u32, new_mode: u32) -> ChangeKind {
    if old_mode == 0o160_000 && new_mode == 0o160_000 {
        ChangeKind::SubmoduleModified
    } else if old_mode & 0o170_000 != new_mode & 0o170_000 {
        ChangeKind::TypeChanged
    } else {
        ChangeKind::Modified
    }
}

const fn toggled_executable_mode(mode: u32) -> u32 {
    if mode == 0o100_755 {
        0o100_644
    } else {
        0o100_755
    }
}

const fn index_flags(flags: gix::index::entry::Flags) -> IndexFlags {
    IndexFlags {
        assume_valid: flags.contains(gix::index::entry::Flags::ASSUME_VALID),
        intent_to_add: flags.contains(gix::index::entry::Flags::INTENT_TO_ADD),
        skip_worktree: flags.contains(gix::index::entry::Flags::SKIP_WORKTREE),
    }
}

const fn conflict_kind(kind: gix::status::plumbing::index_as_worktree::Conflict) -> ConflictKind {
    use gix::status::plumbing::index_as_worktree::Conflict;
    match kind {
        Conflict::BothDeleted => ConflictKind::BothDeleted,
        Conflict::AddedByUs => ConflictKind::AddedByUs,
        Conflict::DeletedByThem => ConflictKind::DeletedByThem,
        Conflict::AddedByThem => ConflictKind::AddedByThem,
        Conflict::DeletedByUs => ConflictKind::DeletedByUs,
        Conflict::BothAdded => ConflictKind::BothAdded,
        Conflict::BothModified => ConflictKind::BothModified,
    }
}

fn sort_changes(changes: &mut [Change]) {
    changes.sort_by(|left, right| {
        left.path
            .cmp(&right.path)
            .then_with(|| left.source_path.cmp(&right.source_path))
    });
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
