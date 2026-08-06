//! Integration coverage for the Rust-owned `run-log publish-breadcrumbs` command.
//!
//! The command replaces one `breadcrumbs/` directory atomically, so the cases
//! below pin the published payload bytes, repeated publication, recovery from
//! an interrupted replacement, and every refusal that leaves the prior tree.

use std::{fs, os::unix::fs::symlink, path::PathBuf, process::Output};

use assert_cmd::Command as AssertCommand;

struct Fixture {
    _directory: tempfile::TempDir,
    session: PathBuf,
    destination: PathBuf,
}

impl Fixture {
    fn new() -> Self {
        let directory = tempfile::tempdir().expect("temporary root should create");
        // Canonicalize so macOS's `/var` -> `/private/var` link does not trip the
        // publisher's symlinked-ancestor refusals.
        let session =
            fs::canonicalize(directory.path()).expect("temporary root should canonicalize");
        let destination = session
            .join("larch-logs")
            .join("implement")
            .join("run-abc")
            .join("breadcrumbs");
        fs::create_dir_all(destination.parent().expect("run directory"))
            .expect("run directory should create");
        Self {
            _directory: directory,
            session,
            destination,
        }
    }

    fn write_quiet_log(&self, name: &str, body: &str) -> PathBuf {
        let path = self.session.join(name);
        fs::write(&path, body).expect("quiet log should write");
        path
    }

    /// Publish with the session root declared as the active `/implement` tmpdir.
    fn publish(&self) -> Output {
        self.publish_from(&self.session.join("breadcrumbs"))
    }

    fn publish_from(&self, source: &PathBuf) -> Output {
        let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
        command
            .arg("run-log")
            .arg("publish-breadcrumbs")
            .arg("--source-dir")
            .arg(source)
            .arg("--dest-dir")
            .arg(&self.destination)
            .env("IMPLEMENT_TMPDIR", &self.session)
            .env_remove("DESIGN_TMPDIR")
            .env_remove("REVIEW_TMPDIR")
            .env_remove("RESEARCH_TMPDIR");
        command.output().expect("command should launch")
    }

    fn quiet_log(&self) -> String {
        fs::read_to_string(self.destination.join("quiet.log")).expect("quiet log should read")
    }

    /// Return the dot-prefixed staging and backup leftovers beside the destination.
    fn leftovers(&self) -> Vec<String> {
        let parent = self.destination.parent().expect("destination parent");
        let mut names: Vec<String> = fs::read_dir(parent)
            .expect("destination parent should read")
            .map(|entry| {
                entry
                    .expect("entry should read")
                    .file_name()
                    .to_string_lossy()
                    .into_owned()
            })
            .filter(|name| name.starts_with('.'))
            .collect();
        names.sort();
        names
    }
}

#[test]
fn publishes_sorted_redacted_quiet_logs_and_republishes_idempotently() {
    let fixture = Fixture::new();
    let _ = fixture.write_quiet_log("larch-quiet-ship.py-222.log", "second breadcrumb\n");
    let _ = fixture.write_quiet_log("larch-quiet-design.sh-111.log", "first breadcrumb\n");
    // A non-matching sibling never reaches the payload.
    let _ = fixture.write_quiet_log("session-transcript.jsonl", "{}\n");

    let first = fixture.publish();
    assert!(first.status.success(), "publish should succeed");
    let expected = concat!(
        "=== larch-quiet-design.sh-111.log ===\n",
        "first breadcrumb\n",
        "=== larch-quiet-ship.py-222.log ===\n",
        "second breadcrumb\n",
    );
    assert_eq!(fixture.quiet_log(), expected);

    // Republishing the same session is idempotent: one quiet.log, same bytes,
    // and no duplicated breadcrumb directory beside it.
    let second = fixture.publish();
    assert!(second.status.success(), "republish should succeed");
    assert_eq!(fixture.quiet_log(), expected);
    let published: Vec<String> = fs::read_dir(&fixture.destination)
        .expect("breadcrumbs should read")
        .map(|entry| {
            entry
                .expect("entry should read")
                .file_name()
                .to_string_lossy()
                .into_owned()
        })
        .collect();
    assert_eq!(published, vec!["quiet.log".to_owned()]);
    assert!(
        fixture.leftovers().is_empty(),
        "no staging tree should remain"
    );
}

#[test]
fn redacts_secrets_and_session_paths_before_publication() {
    let fixture = Fixture::new();
    let _ = fixture.write_quiet_log(
        "larch-quiet-ship.py-1.log",
        "key=sk-ant-api03-AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHHIIIIJJJJKKKKLLLLMMMM\n",
    );

    let output = fixture.publish();

    assert!(output.status.success(), "publish should succeed");
    let published = fixture.quiet_log();
    assert!(
        !published.contains("sk-ant-api03-"),
        "secret must not survive publication: {published}"
    );
}

#[test]
fn replaces_a_live_breadcrumbs_tree_without_losing_it_on_refusal() {
    let fixture = Fixture::new();
    fs::create_dir_all(&fixture.destination).expect("destination should create");
    fs::write(fixture.destination.join("quiet.log"), "previous\n").expect("previous should write");
    let quiet = fixture.write_quiet_log("larch-quiet-ship.py-1.log", "fresh\n");
    let hardlink = fixture.session.join("larch-quiet-ship.py-2.log");
    fs::hard_link(&quiet, &hardlink).expect("hard link should create");

    let refused = fixture.publish();

    assert_eq!(refused.status.code(), Some(1), "hardlinked log is refused");
    assert!(
        String::from_utf8_lossy(&refused.stderr).contains("publish-breadcrumbs:"),
        "refusal names the command"
    );
    // Fail-closed: the previously published tree is untouched.
    assert_eq!(fixture.quiet_log(), "previous\n");
    assert!(
        fixture.leftovers().is_empty(),
        "no staging tree should remain"
    );

    fs::remove_file(&hardlink).expect("hard link should remove");
    let accepted = fixture.publish();

    assert!(accepted.status.success(), "publish should succeed");
    assert_eq!(
        fixture.quiet_log(),
        "=== larch-quiet-ship.py-1.log ===\nfresh\n"
    );
}

#[test]
fn refuses_a_symlinked_quiet_log() {
    let fixture = Fixture::new();
    let real = fixture.session.join("outside.log");
    fs::write(&real, "smuggled\n").expect("outside log should write");
    symlink(&real, fixture.session.join("larch-quiet-ship.py-1.log"))
        .expect("symlink should create");

    let output = fixture.publish();

    assert_eq!(output.status.code(), Some(1), "symlinked log is refused");
    assert!(!fixture.destination.exists(), "nothing is published");
}

#[test]
fn recovers_an_interrupted_replacement_from_its_backup() {
    let fixture = Fixture::new();
    // Model a crash between the destination rename and the staged rename: the
    // previous tree survives only under the `.breadcrumbs.removing` backup.
    let backup = fixture
        .destination
        .parent()
        .expect("destination parent")
        .join(".breadcrumbs.removing");
    fs::create_dir_all(&backup).expect("backup should create");
    fs::write(backup.join("quiet.log"), "interrupted\n").expect("backup payload should write");
    let _ = fixture.write_quiet_log("larch-quiet-ship.py-1.log", "recovered\n");

    let output = fixture.publish();

    assert!(output.status.success(), "publish should succeed");
    assert_eq!(
        fixture.quiet_log(),
        "=== larch-quiet-ship.py-1.log ===\nrecovered\n"
    );
    assert!(fixture.leftovers().is_empty(), "the backup is reclaimed");
}

#[test]
fn reclaims_a_stale_backup_left_beside_a_live_destination() {
    let fixture = Fixture::new();
    // Model the other interruption point: the staged rename already landed, so
    // the destination is current and only the backup cleanup was lost.
    fs::create_dir_all(&fixture.destination).expect("destination should create");
    fs::write(fixture.destination.join("quiet.log"), "current\n").expect("current should write");
    let backup = fixture
        .destination
        .parent()
        .expect("destination parent")
        .join(".breadcrumbs.removing");
    fs::create_dir_all(&backup).expect("backup should create");
    fs::write(backup.join("quiet.log"), "stale\n").expect("stale payload should write");
    let _ = fixture.write_quiet_log("larch-quiet-ship.py-1.log", "next\n");

    let output = fixture.publish();

    assert!(output.status.success(), "publish should succeed");
    // The stale backup is discarded, never promoted over the newer tree.
    assert_eq!(
        fixture.quiet_log(),
        "=== larch-quiet-ship.py-1.log ===\nnext\n"
    );
    assert!(
        fixture.leftovers().is_empty(),
        "the stale backup is reclaimed"
    );
}

#[test]
fn publishes_nothing_without_quiet_logs_or_outside_the_session_root() {
    let fixture = Fixture::new();

    let empty = fixture.publish();
    assert!(empty.status.success(), "an empty session publishes nothing");
    assert!(!fixture.destination.exists(), "nothing is published");

    // A hint whose session root falls outside every active session tmpdir is a
    // publish-nothing no-op, not a refusal.
    let outside = tempfile::tempdir().expect("outside root should create");
    let outside_root = fs::canonicalize(outside.path()).expect("outside root should canonicalize");
    fs::write(outside_root.join("larch-quiet-ship.py-1.log"), "foreign\n")
        .expect("foreign log should write");

    let escaped = fixture.publish_from(&outside_root.join("breadcrumbs"));

    assert!(escaped.status.success(), "an escaped hint is a no-op");
    assert!(!fixture.destination.exists(), "nothing is published");
}

#[test]
fn rejects_a_missing_required_option() {
    let fixture = Fixture::new();
    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
    command
        .arg("run-log")
        .arg("publish-breadcrumbs")
        .arg("--source-dir")
        .arg(fixture.session.join("breadcrumbs"));

    let output = command.output().expect("command should launch");

    assert_eq!(output.status.code(), Some(2), "argparse parity exit code");
}
