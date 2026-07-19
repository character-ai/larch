use std::{ffi::OsString, path::PathBuf};

#[cfg(unix)]
use std::os::unix::ffi::OsStringExt;

use larch_adapters::git::GixRepository;
use larch_core::{
    ConfigKey, ConfigScope, Head, ObjectHash, ObjectId, ObjectKind, RefFormat, RefName,
    ReferenceTarget, RepositoryErrorKind, RepositoryRead, Revision,
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
    assert_graph_queries(&reader, &fixture, &head);
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

fn assert_graph_queries(reader: &GixRepository, fixture: &GitRepository, head: &ObjectId) {
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
