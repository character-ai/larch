use std::{ffi::OsString, path::PathBuf};

#[cfg(unix)]
use std::os::unix::ffi::OsStringExt;

use larch_adapters::git::GixRepository;
use larch_core::{
    ChangeKind, ConfigKey, ConfigScope, GitPath, Head, IgnoreKind, ObjectHash, ObjectId,
    ObjectKind, RefFormat, RefName, ReferenceTarget, RepositoryErrorKind, RepositoryRead, Revision,
    StatusOptions,
};
use larch_test_support::{
    ExecutionSnapshot, GitFixture, GitFixtureError, GitObjectFormat, GitRepository,
    SemanticSnapshot, TestWorkspace,
};

#[test]
fn repository_queries_match_installed_git_semantics() {
    let Some(fixture) = fixture(GitFixture::Refs, GitObjectFormat::Sha1) else {
        return;
    };
    fixture.write("second.txt", b"second\n").unwrap();
    git_ok(&fixture, ["add", "second.txt"]);
    git_ok(&fixture, ["commit", "--quiet", "-m", "second"]);
    git_ok(&fixture, ["pack-refs", "--all"]);
    fixture.write("nested/file.txt", b"nested\n").unwrap();
    fixture.write("ambiguous-a", b"ambiguous-16\n").unwrap();
    fixture.write("ambiguous-b", b"ambiguous-272\n").unwrap();
    git_ok(&fixture, ["hash-object", "-w", "ambiguous-a"]);
    git_ok(&fixture, ["hash-object", "-w", "ambiguous-b"]);
    let unrelated = git_id(
        &fixture,
        ["commit-tree", "HEAD^{tree}", "-m", "unrelated history"],
    );
    let before = SemanticSnapshot::capture(&fixture, ExecutionSnapshot::success()).unwrap();

    let reader = GixRepository::discover(fixture.root().join("nested")).unwrap();
    let location = reader.location();
    assert_eq!(
        canonical_path(location.work_dir.unwrap().as_bytes()),
        canonical_path(&git_line(&fixture, ["rev-parse", "--show-toplevel"]))
    );
    assert_eq!(
        canonical_path(location.git_dir.as_bytes()),
        canonical_path(&git_line(&fixture, ["rev-parse", "--absolute-git-dir"]))
    );
    assert_eq!(location.object_hash, ObjectHash::Sha1);

    let head = git_id(&fixture, ["rev-parse", "HEAD"]);
    assert_eq!(
        reader.resolve_revision(&Revision::new("HEAD")).unwrap(),
        head
    );
    assert_eq!(
        reader.head().unwrap(),
        Head::Symbolic {
            name: RefName::new("refs/heads/main"),
            target: head.clone(),
        }
    );

    assert_ref_and_object_queries(&reader, &fixture, &head);
    assert_graph_queries(&reader, &fixture, &head, &unrelated);
    assert_revision_validation(&reader, &fixture);

    let after = SemanticSnapshot::capture(&fixture, ExecutionSnapshot::success()).unwrap();
    assert_eq!(after, before);
}

fn assert_ref_and_object_queries(reader: &GixRepository, fixture: &GitRepository, head: &ObjectId) {
    let references = reader.references().unwrap();
    for name in [
        "refs/heads/main",
        "refs/heads/topic",
        "refs/remotes/origin/main",
        "refs/tags/v1",
    ] {
        let expected = git_id(fixture, ["show-ref", "--verify", "--hash", name]);
        let actual = references
            .iter()
            .find(|reference| reference.name.as_bytes() == name.as_bytes())
            .unwrap();
        assert_eq!(actual.target, ReferenceTarget::Object(expected));
    }

    let object = reader.object(head).unwrap().unwrap();
    assert_eq!(object.kind, ObjectKind::Commit);
    assert_eq!(
        object.data,
        git_bytes(fixture, ["cat-file", "commit", "HEAD"])
    );
    let missing = ObjectId::new(ObjectHash::Sha1, [0; 20]).unwrap();
    assert_eq!(reader.object(&missing).unwrap(), None);
}

fn assert_graph_queries(
    reader: &GixRepository,
    fixture: &GitRepository,
    head: &ObjectId,
    unrelated: &ObjectId,
) {
    let expected_walk: Vec<_> = git_lines(fixture, ["rev-list", "HEAD"])
        .into_iter()
        .map(|hex| id_from_hex(&hex))
        .collect();
    let walk = reader.walk_commits(head, usize::MAX).unwrap();
    assert_eq!(
        walk.iter()
            .map(|commit| commit.id.clone())
            .collect::<Vec<_>>(),
        expected_walk
    );
    assert_eq!(
        reader.commit_count(head).unwrap(),
        expected_walk.len() as u64
    );
    assert_eq!(reader.walk_commits(head, 1).unwrap().len(), 1);
    let topic = git_id(fixture, ["rev-parse", "topic"]);
    assert_eq!(
        reader.merge_base(head, &topic).unwrap(),
        git_id(fixture, ["merge-base", "HEAD", "topic"])
    );
    assert!(reader.is_ancestor(&topic, head).unwrap());
    assert!(!reader.is_ancestor(head, &topic).unwrap());
    assert!(!reader.is_ancestor(head, unrelated).unwrap());
    assert!(!reader.is_ancestor(unrelated, head).unwrap());
}

fn assert_revision_validation(reader: &GixRepository, fixture: &GitRepository) {
    for (name, format, git_name) in [
        ("refs/heads/topic", RefFormat::Full, "refs/heads/topic"),
        ("refs/heads/topic", RefFormat::Branch, "refs/heads/topic"),
        ("release/v1", RefFormat::Tag, "refs/tags/release/v1"),
        ("bad..name", RefFormat::Full, "bad..name"),
    ] {
        let git_valid = fixture
            .git(["check-ref-format", git_name])
            .unwrap()
            .success();
        assert_eq!(
            reader
                .validate_ref_name(&RefName::new(name), format)
                .is_ok(),
            git_valid
        );
    }
    assert_eq!(
        reader
            .resolve_revision(&Revision::new("HEAD..topic"))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::UnsupportedRevision
    );
    assert_eq!(
        reader
            .resolve_revision(&Revision::new("HEAD^{/second}"))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::UnsupportedRevision
    );
    assert_eq!(
        reader
            .resolve_revision(&Revision::new("missing-name"))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::RevisionNotFound
    );
    assert_eq!(
        reader
            .resolve_revision(&Revision::new("5978"))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::AmbiguousRevision
    );
    assert_eq!(
        reader
            .resolve_revision(&Revision::new("dead"))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::RevisionNotFound
    );
}

#[test]
fn config_remotes_and_upstream_match_git() {
    let Some(fixture) = fixture(GitFixture::HooksSigningAndRemotes, GitObjectFormat::Sha1) else {
        return;
    };
    fixture
        .write("included.cfg", b"[larch]\nraw = from-include\n")
        .unwrap();
    git_ok(&fixture, ["config", "include.path", "../included.cfg"]);
    git_ok(
        &fixture,
        [
            "config",
            "url.https://mirror.invalid/.insteadOf",
            "https://user:secret@example.invalid/",
        ],
    );
    git_ok(
        &fixture,
        [
            "config",
            "remote.origin.fetch",
            "+refs/heads/*:refs/remotes/origin/*",
        ],
    );
    git_ok(&fixture, ["config", "branch.main.remote", "origin"]);
    git_ok(&fixture, ["config", "branch.main.merge", "refs/heads/main"]);
    git_ok(&fixture, ["update-ref", "refs/remotes/origin/main", "HEAD"]);

    let reader = GixRepository::open(fixture.root()).unwrap();
    let values = reader
        .config_values(&ConfigKey::new("larch.raw").unwrap())
        .unwrap();
    assert_eq!(values.len(), 1);
    assert_eq!(values[0].value, b"from-include");
    assert_eq!(values[0].scope, ConfigScope::Repository);
    assert_eq!(values[0].include_depth, 1);

    let expected_names = git_lines(&fixture, ["remote"]);
    let remotes = reader.remotes().unwrap();
    assert_eq!(
        remotes
            .iter()
            .map(|remote| remote.name.clone())
            .collect::<Vec<_>>(),
        expected_names
    );
    let origin = remotes
        .iter()
        .find(|remote| remote.name == b"origin")
        .unwrap();
    assert_eq!(
        origin.fetch_url.as_deref().unwrap(),
        git_line(&fixture, ["remote", "get-url", "origin"])
    );
    assert_eq!(
        origin.push_url.as_deref().unwrap(),
        git_line(&fixture, ["remote", "get-url", "--push", "origin"])
    );

    let upstream = reader
        .upstream(&RefName::new("refs/heads/main"))
        .unwrap()
        .unwrap();
    assert_eq!(upstream.remote, b"origin");
    assert_eq!(upstream.remote_ref.as_bytes(), b"refs/heads/main");
    assert_eq!(
        upstream.tracking_ref.unwrap().as_bytes(),
        b"refs/remotes/origin/main"
    );
    let upstream_revision: String = ['@', '{', 'u', 'p', 's', 't', 'r', 'e', 'a', 'm', '}']
        .into_iter()
        .collect();
    assert_eq!(
        reader
            .resolve_revision(&Revision::new(upstream_revision.as_str()))
            .unwrap(),
        git_id(&fixture, ["rev-parse", upstream_revision.as_str()])
    );
}

#[cfg(unix)]
#[test]
fn non_utf8_config_values_are_preserved() {
    let Some(fixture) = fixture(GitFixture::Unborn, GitObjectFormat::Sha1) else {
        return;
    };
    let value = OsString::from_vec(b"raw-\xff-value".to_vec());
    let output = fixture
        .git([OsString::from("config"), OsString::from("larch.raw"), value])
        .unwrap();
    assert!(output.success(), "Git oracle failed");
    let reader = GixRepository::open(fixture.root()).unwrap();
    let values = reader
        .config_values(&ConfigKey::new("larch.raw").unwrap())
        .unwrap();
    assert_eq!(values[0].value, b"raw-\xff-value");
}

#[test]
fn head_worktrees_sha256_and_errors_have_typed_results() {
    let Some(unborn) = fixture(GitFixture::Unborn, GitObjectFormat::Sha1) else {
        return;
    };
    let reader = GixRepository::open(unborn.root()).unwrap();
    assert!(matches!(reader.head().unwrap(), Head::Unborn { .. }));
    let malformed = unborn.write(".git/config", b"[broken\n").unwrap();
    assert!(malformed.ends_with("config"));
    assert_eq!(
        reader.head().unwrap_err().kind(),
        RepositoryErrorKind::MalformedConfig
    );
    assert_eq!(
        GixRepository::open(unborn.root()).unwrap_err().kind(),
        RepositoryErrorKind::MalformedConfig
    );

    let Some(detached) = fixture(GitFixture::Detached, GitObjectFormat::Sha1) else {
        return;
    };
    assert!(matches!(
        GixRepository::open(detached.root())
            .unwrap()
            .head()
            .unwrap(),
        Head::Detached { .. }
    ));

    if let Some(linked) = fixture(GitFixture::LinkedWorktree, GitObjectFormat::Sha1) {
        let linked_path = linked.workspace_root().join("linked-worktree");
        git_ok(&linked, ["config", "extensions.worktreeConfig", "true"]);
        git_ok(
            &linked,
            [
                OsString::from("-C"),
                linked_path.as_os_str().to_owned(),
                OsString::from("config"),
                OsString::from("--worktree"),
                OsString::from("larch.scope"),
                OsString::from("linked"),
            ],
        );
        let reader = GixRepository::open(&linked_path).unwrap();
        assert!(reader.head().is_ok());
        let scoped = reader
            .config_values(&ConfigKey::new("larch.scope").unwrap())
            .unwrap();
        assert_eq!(scoped[0].scope, ConfigScope::Worktree);
        let mut expected: Vec<_> = git_bytes(&linked, ["worktree", "list", "--porcelain", "-z"])
            .split(|byte| *byte == 0)
            .filter_map(|line| line.strip_prefix(b"worktree ").map(<[u8]>::to_vec))
            .collect();
        expected = expected
            .into_iter()
            .map(|value| canonical_path(&value))
            .collect();
        expected.sort();
        let mut actual: Vec<_> = reader
            .worktrees()
            .unwrap()
            .into_iter()
            .map(|worktree| canonical_path(worktree.path.as_bytes()))
            .collect();
        actual.sort();
        assert_eq!(actual, expected);
    }

    if let Some(sha256) = fixture(GitFixture::Refs, GitObjectFormat::Sha256) {
        let reader = GixRepository::open(sha256.root()).unwrap();
        assert_eq!(reader.location().object_hash, ObjectHash::Sha256);
        assert_eq!(
            reader.resolve_revision(&Revision::new("HEAD")).unwrap(),
            git_id(&sha256, ["rev-parse", "HEAD"])
        );
        assert_eq!(
            reader
                .object(&ObjectId::new(ObjectHash::Sha1, [0; 20]).unwrap())
                .unwrap_err()
                .kind(),
            RepositoryErrorKind::HashMismatch
        );
    }

    let workspace = TestWorkspace::new().unwrap();
    let plain = workspace.create_dir("plain").unwrap();
    assert_eq!(
        GixRepository::discover(plain).unwrap_err().kind(),
        RepositoryErrorKind::NotRepository
    );
}

#[test]
fn configured_status_matches_git_for_clean_and_dirty_worktrees() {
    let Some(clean) = fixture(GitFixture::Refs, GitObjectFormat::Sha1) else {
        return;
    };
    let clean_status = GixRepository::open(clean.root())
        .unwrap()
        .status(&StatusOptions::default())
        .unwrap();
    assert!(!clean_status.is_dirty());

    let Some(changes) = fixture(GitFixture::Changes, GitObjectFormat::Sha1) else {
        return;
    };
    let reader = GixRepository::open(changes.root()).unwrap();
    let status = reader
        .status(&StatusOptions {
            include_ignored: true,
            ..StatusOptions::default()
        })
        .unwrap();
    assert!(status.is_dirty(), "untracked files must count as dirty");
    assert_eq!(
        status
            .tree_to_index
            .paths()
            .map(|path| path.as_bytes().to_vec())
            .collect::<Vec<_>>(),
        git_nul_paths(&changes, ["diff", "--cached", "--name-only", "-z"])
    );
    assert_eq!(status.tree_to_index.entries()[0].kind, ChangeKind::Added);
    assert_eq!(
        status
            .index_to_worktree
            .paths()
            .map(|path| path.as_bytes().to_vec())
            .collect::<Vec<_>>(),
        git_nul_paths(&changes, ["diff", "--name-only", "-z"])
    );
    assert_eq!(
        status
            .untracked
            .iter()
            .map(|path| path.as_bytes().to_vec())
            .collect::<Vec<_>>(),
        git_nul_paths(
            &changes,
            ["ls-files", "--others", "--exclude-standard", "-z"]
        )
    );
    assert_eq!(status.ignored[0].path, GitPath::new("ignored.txt"));
    assert_eq!(status.ignored[0].kind, IgnoreKind::Expendable);

    let scoped = reader
        .status(&StatusOptions {
            pathspecs: vec![GitPath::new("tracked.txt")],
            ..StatusOptions::default()
        })
        .unwrap();
    assert_eq!(
        scoped.index_to_worktree.paths().collect::<Vec<_>>(),
        vec![&GitPath::new("tracked.txt")]
    );
    assert!(scoped.tree_to_index.is_empty());
    assert!(scoped.untracked.is_empty());
    assert_eq!(scoped.tracked.len(), 1);
    assert_eq!(scoped.tracked[0].path, GitPath::new("tracked.txt"));

    git_ok(&changes, ["reset", "--hard", "--quiet"]);
    std::fs::remove_file(changes.root().join("untracked.txt")).unwrap();
    git_ok(&changes, ["add", ".gitignore"]);
    git_ok(&changes, ["commit", "--quiet", "-m", "track ignores"]);
    let ignored_only = reader
        .status(&StatusOptions {
            include_ignored: true,
            ..StatusOptions::default()
        })
        .unwrap();
    assert_eq!(ignored_only.ignored[0].path, GitPath::new("ignored.txt"));
    assert!(!ignored_only.is_dirty());
    let ignored_without_untracked = reader
        .status(&StatusOptions {
            include_untracked: false,
            include_ignored: true,
            ..StatusOptions::default()
        })
        .unwrap();
    assert!(ignored_without_untracked.untracked.is_empty());
    assert_eq!(
        ignored_without_untracked.ignored[0].path,
        GitPath::new("ignored.txt")
    );
    changes.write("only-untracked.txt", b"dirty\n").unwrap();
    let untracked_only = reader.status(&StatusOptions::default()).unwrap();
    assert_eq!(
        untracked_only.untracked,
        vec![GitPath::new("only-untracked.txt")]
    );
    assert!(untracked_only.is_dirty());
}

#[test]
fn conflicts_are_only_unmerged_and_preserve_all_index_stages() {
    let Some(conflict) = fixture(GitFixture::Conflict, GitObjectFormat::Sha1) else {
        return;
    };
    let status = GixRepository::open(conflict.root())
        .unwrap()
        .status(&StatusOptions::default())
        .unwrap();
    assert!(status.is_dirty());
    assert_eq!(status.unmerged.len(), 1);
    let entry = &status.unmerged[0];
    assert_eq!(entry.path.as_bytes(), b"tracked.txt");
    assert_eq!(
        entry
            .stages
            .iter()
            .map(|stage| stage.stage)
            .collect::<Vec<_>>(),
        vec![1, 2, 3]
    );
    assert!(
        entry
            .stages
            .iter()
            .all(|stage| stage.mode.raw() == 0o100_644)
    );
    assert!(status.tree_to_index.is_empty());
    assert!(status.index_to_worktree.is_empty());
}

#[test]
fn range_blob_and_conflict_stage_queries_match_git() {
    let Some(repository) = fixture(GitFixture::Refs, GitObjectFormat::Sha1) else {
        return;
    };
    repository.write("dir/file.txt", b"nested\n").unwrap();
    git_ok(&repository, ["add", "--all"]);
    git_ok(&repository, ["commit", "--quiet", "-m", "nested subject"]);

    let reader = GixRepository::open(repository.root()).unwrap();
    let include = git_id(&repository, ["rev-parse", "HEAD"]);
    let exclude = git_id(&repository, ["rev-parse", "HEAD~1"]);
    assert_range_queries(&reader, &repository, &exclude, &include);
    assert_blob_queries(&reader, &repository, &include);
    assert_file_queries(&reader, &repository, &include);

    let Some(conflict) = fixture(GitFixture::Conflict, GitObjectFormat::Sha1) else {
        return;
    };
    assert_conflict_stage_queries(&conflict);
}

fn assert_range_queries(
    reader: &GixRepository,
    repository: &GitRepository,
    exclude: &ObjectId,
    include: &ObjectId,
) {
    assert_eq!(
        reader.commit_count_range(exclude, include).unwrap(),
        git_line(repository, ["rev-list", "--count", "HEAD~1..HEAD"])
            .iter()
            .fold(0_u64, |value, byte| value * 10 + u64::from(byte - b'0'))
    );
    assert_eq!(
        reader.commit_subjects_range(exclude, include).unwrap(),
        vec![b"nested subject".to_vec()]
    );
    assert_eq!(
        reader
            .commit_messages_range(Some(exclude), include)
            .unwrap(),
        vec![b"nested subject\n".to_vec()]
    );
    assert!(reader.commit_messages_range(None, include).unwrap().len() > 1);
}

fn assert_blob_queries(reader: &GixRepository, repository: &GitRepository, include: &ObjectId) {
    assert_eq!(
        reader
            .blob_at_commit(include, &GitPath::new("dir/file.txt"))
            .unwrap(),
        Some(b"nested\n".to_vec())
    );
    assert_eq!(
        reader
            .blob_id_at_commit(include, &GitPath::new("dir/file.txt"))
            .unwrap(),
        Some(git_id(repository, ["rev-parse", "HEAD:dir/file.txt"]))
    );
    assert_eq!(
        reader
            .blob_id_at_commit(include, &GitPath::new("missing.txt"))
            .unwrap(),
        None
    );
    assert_eq!(
        reader
            .blob_id_at_commit(include, &GitPath::new(""))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::InvalidInput
    );
    assert_eq!(
        reader
            .blob_id_at_commit(include, &GitPath::new("dir"))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::ObjectType
    );
    assert_eq!(
        reader
            .blob_at_commit(include, &GitPath::new("missing.txt"))
            .unwrap(),
        None
    );
    assert_eq!(
        reader
            .blob_at_commit(include, &GitPath::new(""))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::InvalidInput
    );
    assert_eq!(
        reader
            .blob_at_commit(include, &GitPath::new("dir"))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::ObjectType
    );
}

fn assert_file_queries(reader: &GixRepository, repository: &GitRepository, include: &ObjectId) {
    let mut expected_files = git_lines(repository, ["ls-tree", "-r", "--name-only", "HEAD"])
        .into_iter()
        .map(GitPath::new)
        .collect::<Vec<_>>();
    let mut actual_files = reader.files_at_commit(include, usize::MAX).unwrap();
    expected_files.sort();
    actual_files.sort();
    assert_eq!(actual_files, expected_files);
    assert_eq!(
        reader
            .files_at_commit(include, actual_files.len().saturating_sub(1))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::InvalidInput
    );
}

fn assert_conflict_stage_queries(conflict: &GitRepository) {
    let conflict_reader = GixRepository::open(conflict.root()).unwrap();
    for stage in 1..=3 {
        let spec = format!(":{stage}:tracked.txt");
        assert_eq!(
            conflict_reader.stage_blob(b"tracked.txt", stage).unwrap(),
            git_bytes(conflict, ["show", spec.as_str()])
        );
    }
    assert_eq!(
        conflict_reader
            .stage_blob(b"tracked.txt", 0)
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::InvalidInput
    );
    assert_eq!(
        conflict_reader
            .stage_blob(b"missing.txt", 1)
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::RevisionNotFound
    );
}

#[test]
fn repository_covers_optional_refs_and_compatibility_status() {
    let Some(repository) = fixture(GitFixture::Refs, GitObjectFormat::Sha1) else {
        return;
    };
    git_ok(
        &repository,
        ["symbolic-ref", "refs/heads/current", "refs/heads/main"],
    );
    let reader = GixRepository::open(repository.root()).unwrap();
    assert_eq!(
        reader.upstream(&RefName::new("refs/heads/topic")).unwrap(),
        None
    );
    assert_eq!(
        reader
            .upstream(&RefName::new("refs/tags/v1"))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::InvalidRef
    );
    assert!(reader.references().unwrap().iter().any(|reference| {
        reference.name.as_bytes() == b"refs/heads/current"
            && reference.target == ReferenceTarget::Symbolic(RefName::new("refs/heads/main"))
    }));
    assert_eq!(
        reader
            .resolve_revision(&Revision::new(""))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::InvalidInput
    );
    assert_eq!(
        reader
            .resolve_revision(&Revision::new("HEAD:tracked.txt"))
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::UnsupportedRevision
    );

    let Some(filtered) = fixture(GitFixture::AttributesAndFilters, GitObjectFormat::Sha1) else {
        return;
    };
    let filtered_reader = GixRepository::open(filtered.root()).unwrap();
    assert!(
        filtered_reader
            .local_status(&StatusOptions::default())
            .is_ok()
    );

    let head_tree = git_id(&repository, ["rev-parse", "HEAD^{tree}"]);
    git_ok(&repository, ["config", "diff.fixture.textconv", "cat"]);
    assert_eq!(
        reader
            .tree_changes(&head_tree, &head_tree)
            .unwrap_err()
            .kind(),
        RepositoryErrorKind::UnsupportedSemantics
    );
}

#[test]
fn tree_changes_report_names_statuses_modes_and_configured_rewrites() {
    let Some(repository) = fixture(GitFixture::Refs, GitObjectFormat::Sha1) else {
        return;
    };
    repository
        .write("rename.txt", b"rename me\nsame line\n")
        .unwrap();
    repository.write("copy.txt", b"copy me\n").unwrap();
    git_ok(&repository, ["add", "--all"]);
    git_ok(&repository, ["commit", "--quiet", "-m", "sources"]);
    git_ok(&repository, ["config", "diff.renames", "copies"]);
    let old_tree = git_id(&repository, ["rev-parse", "HEAD^{tree}"]);
    git_ok(&repository, ["mv", "rename.txt", "renamed.txt"]);
    let staged = GixRepository::open(repository.root())
        .unwrap()
        .status(&StatusOptions::default())
        .unwrap();
    assert!(staged.tree_to_index.entries().iter().any(|change| {
        change.kind == ChangeKind::Renamed
            && change.source_path.as_ref().unwrap().as_bytes() == b"rename.txt"
            && change.path.as_bytes() == b"renamed.txt"
    }));
    repository
        .write("renamed.txt", b"rename me\nsame line\nchanged\n")
        .unwrap();
    repository.write("copy.txt", b"copy changed\n").unwrap();
    repository.write("copy-2.txt", b"copy changed\n").unwrap();
    git_ok(&repository, ["add", "--all"]);
    git_ok(&repository, ["commit", "--quiet", "-m", "rewrites"]);
    let new_tree = git_id(&repository, ["rev-parse", "HEAD^{tree}"]);

    let changes = GixRepository::open(repository.root())
        .unwrap()
        .tree_changes(&old_tree, &new_tree)
        .unwrap();
    assert_eq!(changes.entries().len(), 3);
    assert!(changes.entries().iter().any(|change| {
        change.kind == ChangeKind::Renamed
            && change.source_path.as_ref().unwrap().as_bytes() == b"rename.txt"
            && change.path.as_bytes() == b"renamed.txt"
    }));
    assert!(changes.entries().iter().any(|change| {
        change.kind == ChangeKind::Copied
            && change.source_path.as_ref().unwrap().as_bytes() == b"copy.txt"
            && change.path.as_bytes() == b"copy-2.txt"
    }));
    assert!(changes.entries().iter().any(|change| {
        change.kind == ChangeKind::Modified && change.path.as_bytes() == b"copy.txt"
    }));
    assert!(changes.entries().iter().all(|change| {
        change.old_mode.unwrap().raw() == 0o100_644
            && change.new_mode.unwrap().raw() == 0o100_644
            && change.old_id.is_some()
            && change.new_id.is_some()
    }));
}

#[cfg(unix)]
#[test]
fn status_preserves_non_utf8_paths_and_file_type_changes() {
    use std::fs;
    use std::os::unix::fs::PermissionsExt;

    let Some(repository) = fixture(GitFixture::SpecialFiles, GitObjectFormat::Sha1) else {
        return;
    };
    let old_tree = git_id(&repository, ["rev-parse", "HEAD^{tree}"]);
    fs::remove_file(repository.root().join("link")).unwrap();
    repository.write("link", b"regular now\n").unwrap();
    fs::set_permissions(
        repository.root().join("executable.sh"),
        fs::Permissions::from_mode(0o644),
    )
    .unwrap();
    let status = GixRepository::open(repository.root())
        .unwrap()
        .status(&StatusOptions::default())
        .unwrap();
    assert!(status.index_to_worktree.entries().iter().any(|change| {
        change.path.as_bytes() == b"link" && change.kind == ChangeKind::TypeChanged
    }));
    assert!(status.index_to_worktree.entries().iter().any(|change| {
        change.path.as_bytes() == b"executable.sh"
            && change.old_mode.unwrap().raw() == 0o100_755
            && change.new_mode.unwrap().raw() == 0o100_644
    }));
    git_ok(&repository, ["add", "link"]);
    git_ok(&repository, ["commit", "--quiet", "-m", "replace symlink"]);
    let new_tree = git_id(&repository, ["rev-parse", "HEAD^{tree}"]);
    let tree_changes = GixRepository::open(repository.root())
        .unwrap()
        .tree_changes(&old_tree, &new_tree)
        .unwrap();
    assert_eq!(tree_changes.entries()[0].kind, ChangeKind::TypeChanged);
    assert_eq!(tree_changes.entries()[0].old_mode.unwrap().raw(), 0o120_000);
    assert_eq!(tree_changes.entries()[0].new_mode.unwrap().raw(), 0o100_644);

    let raw_name = OsString::from_vec(b"untracked-\xff".to_vec());
    if let Err(error) = repository.write(std::path::Path::new(&raw_name), b"raw\n") {
        eprintln!("fixture skipped: raw byte path is unsupported: {error}");
        return;
    }
    let status = GixRepository::open(repository.root())
        .unwrap()
        .status(&StatusOptions::default())
        .unwrap();
    assert!(
        status
            .untracked
            .iter()
            .any(|path| path.as_bytes() == b"untracked-\xff")
    );
}

#[test]
fn status_respects_case_configuration_and_reports_submodule_changes() {
    let Some(changes) = fixture(GitFixture::Changes, GitObjectFormat::Sha1) else {
        return;
    };
    git_ok(&changes, ["config", "core.ignoreCase", "true"]);
    let scoped = GixRepository::open(changes.root())
        .unwrap()
        .status(&StatusOptions {
            pathspecs: vec![GitPath::new("TRACKED.TXT")],
            ..StatusOptions::default()
        })
        .unwrap();
    assert_eq!(scoped.index_to_worktree.entries().len(), 1);

    let Some(submodule) = fixture(GitFixture::Submodule, GitObjectFormat::Sha1) else {
        return;
    };
    submodule
        .write("submodule/child.txt", b"child changed\n")
        .unwrap();
    let status = GixRepository::open(submodule.root())
        .unwrap()
        .status(&StatusOptions::default())
        .unwrap();
    assert!(status.index_to_worktree.entries().iter().any(|change| {
        change.path.as_bytes() == b"submodule" && change.kind == ChangeKind::SubmoduleModified
    }));
}

#[test]
fn external_filters_and_sparse_indexes_fail_explicitly() {
    if let Some(filtered) = fixture(GitFixture::AttributesAndFilters, GitObjectFormat::Sha1) {
        assert_eq!(
            GixRepository::open(filtered.root())
                .unwrap()
                .status(&StatusOptions::default())
                .unwrap_err()
                .kind(),
            RepositoryErrorKind::UnsupportedSemantics
        );
    }

    if let Some(sparse) = fixture(GitFixture::SparseCheckout, GitObjectFormat::Sha1) {
        let converted = sparse.git(["sparse-checkout", "reapply", "--sparse-index"]);
        if converted.is_ok_and(|output| output.success()) {
            let result = GixRepository::open(sparse.root())
                .unwrap()
                .status(&StatusOptions::default());
            match result {
                Ok(status) => assert!(!status.is_dirty()),
                Err(error) => {
                    assert_eq!(error.kind(), RepositoryErrorKind::UnsupportedSemantics);
                }
            }
        }
    }
}

#[test]
fn crlf_status_difference_routes_to_exact_compatibility() {
    let Some(repository) = fixture(GitFixture::Unborn, GitObjectFormat::Sha1) else {
        return;
    };
    repository
        .write(".gitattributes", b"crlf.txt text eol=crlf\n")
        .unwrap();
    repository.write("crlf.txt", b"one\r\ntwo\r\n").unwrap();
    git_ok(&repository, ["add", "--all"]);
    git_ok(&repository, ["commit", "--quiet", "-m", "crlf"]);
    repository.write("crlf.txt", b"one\ntwo\n").unwrap();
    let reader = GixRepository::open(repository.root()).unwrap();
    assert!(repository.git(["diff", "--quiet"]).unwrap().success());
    assert_eq!(
        reader.status(&StatusOptions::default()).unwrap_err().kind(),
        RepositoryErrorKind::UnsupportedSemantics
    );
}

#[test]
fn tracked_entries_preserve_flags_and_precious_ignore_kind() {
    let Some(repository) = fixture(GitFixture::Refs, GitObjectFormat::Sha1) else {
        return;
    };
    repository.write("skip.txt", b"skip\n").unwrap();
    git_ok(&repository, ["add", "skip.txt"]);
    git_ok(&repository, ["commit", "--quiet", "-m", "add skip entry"]);
    git_ok(
        &repository,
        ["update-index", "--assume-unchanged", "tracked.txt"],
    );
    git_ok(&repository, ["update-index", "--skip-worktree", "skip.txt"]);
    repository.write("intent.txt", b"intent\n").unwrap();
    git_ok(&repository, ["add", "--intent-to-add", "intent.txt"]);
    repository.write(".gitignore", b"$precious.txt\n").unwrap();
    repository.write("precious.txt", b"keep\n").unwrap();
    git_ok(&repository, ["config", "gitoxide.parsePrecious", "true"]);

    let status = GixRepository::open(repository.root())
        .unwrap()
        .status(&StatusOptions {
            include_ignored: true,
            ..StatusOptions::default()
        })
        .unwrap();
    let tracked = status
        .tracked
        .iter()
        .find(|entry| entry.path.as_bytes() == b"tracked.txt")
        .unwrap();
    assert!(tracked.flags.assume_valid);
    let skipped = status
        .tracked
        .iter()
        .find(|entry| entry.path.as_bytes() == b"skip.txt")
        .unwrap();
    assert!(skipped.flags.skip_worktree);
    let intent = status
        .tracked
        .iter()
        .find(|entry| entry.path.as_bytes() == b"intent.txt")
        .unwrap();
    assert!(intent.flags.intent_to_add);
    assert!(status.index_to_worktree.entries().iter().any(|change| {
        change.path.as_bytes() == b"intent.txt" && change.index_flags.unwrap().intent_to_add
    }));
    assert!(status.ignored.iter().any(|entry| {
        entry.path.as_bytes() == b"precious.txt" && entry.kind == IgnoreKind::Precious
    }));
}

fn fixture(kind: GitFixture, format: GitObjectFormat) -> Option<GitRepository> {
    match GitRepository::builder(kind).object_format(format).build() {
        Ok(repository) => Some(repository),
        Err(GitFixtureError::Skip(skip)) => {
            eprintln!("fixture skipped: {skip}");
            None
        }
        Err(error) => panic!("fixture failed: {error}"),
    }
}

fn git_ok<I, S>(repository: &GitRepository, arguments: I)
where
    I: IntoIterator<Item = S>,
    S: AsRef<std::ffi::OsStr>,
{
    assert!(
        repository.git(arguments).unwrap().success(),
        "Git oracle failed"
    );
}

fn git_bytes<I, S>(repository: &GitRepository, arguments: I) -> Vec<u8>
where
    I: IntoIterator<Item = S>,
    S: AsRef<std::ffi::OsStr>,
{
    let output = repository.git(arguments).unwrap();
    assert!(output.success(), "Git oracle failed");
    output.stdout
}

fn git_line<I, S>(repository: &GitRepository, arguments: I) -> Vec<u8>
where
    I: IntoIterator<Item = S>,
    S: AsRef<std::ffi::OsStr>,
{
    let mut output = git_bytes(repository, arguments);
    while matches!(output.last(), Some(b'\n' | b'\r')) {
        output.pop();
    }
    output
}

fn git_lines<I, S>(repository: &GitRepository, arguments: I) -> Vec<Vec<u8>>
where
    I: IntoIterator<Item = S>,
    S: AsRef<std::ffi::OsStr>,
{
    git_bytes(repository, arguments)
        .split(|byte| *byte == b'\n')
        .filter(|line| !line.is_empty())
        .map(<[u8]>::to_vec)
        .collect()
}

fn git_nul_paths<I, S>(repository: &GitRepository, arguments: I) -> Vec<Vec<u8>>
where
    I: IntoIterator<Item = S>,
    S: AsRef<std::ffi::OsStr>,
{
    let mut paths = git_bytes(repository, arguments)
        .split(|byte| *byte == 0)
        .filter(|path| !path.is_empty())
        .map(<[u8]>::to_vec)
        .collect::<Vec<_>>();
    paths.sort();
    paths
}

fn git_id<I, S>(repository: &GitRepository, arguments: I) -> ObjectId
where
    I: IntoIterator<Item = S>,
    S: AsRef<std::ffi::OsStr>,
{
    id_from_hex(&git_line(repository, arguments))
}

fn id_from_hex(hex: &[u8]) -> ObjectId {
    let hash = match hex.len() {
        40 => ObjectHash::Sha1,
        64 => ObjectHash::Sha256,
        _ => panic!("unexpected object ID length"),
    };
    let digest = hex
        .chunks_exact(2)
        .map(|pair| (nibble(pair[0]) << 4) | nibble(pair[1]))
        .collect::<Vec<_>>();
    ObjectId::new(hash, digest).unwrap()
}

fn nibble(byte: u8) -> u8 {
    match byte {
        b'0'..=b'9' => byte - b'0',
        b'a'..=b'f' => byte - b'a' + 10,
        _ => panic!("non-hex object ID"),
    }
}

#[cfg(unix)]
fn canonical_path(bytes: &[u8]) -> Vec<u8> {
    use std::os::unix::ffi::OsStrExt;

    std::fs::canonicalize(PathBuf::from(OsString::from_vec(bytes.to_vec())))
        .unwrap()
        .as_os_str()
        .as_bytes()
        .to_vec()
}

#[cfg(not(unix))]
fn canonical_path(bytes: &[u8]) -> Vec<u8> {
    std::fs::canonicalize(PathBuf::from(String::from_utf8(bytes.to_vec()).unwrap()))
        .unwrap()
        .to_string_lossy()
        .into_owned()
        .into_bytes()
}
