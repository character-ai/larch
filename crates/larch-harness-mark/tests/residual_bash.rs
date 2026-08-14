use std::{
    fs,
    process::Command,
    sync::atomic::{AtomicU64, Ordering},
};

static NEXT_FIXTURE: AtomicU64 = AtomicU64::new(0);

fn fixture_root() -> std::path::PathBuf {
    let root = std::env::temp_dir().join(format!(
        "larch-residual-bash-command-{}-{}",
        std::process::id(),
        NEXT_FIXTURE.fetch_add(1, Ordering::Relaxed)
    ));
    fs::create_dir_all(root.join("scripts")).expect("create residual Bash command fixture");
    root
}

#[test]
fn command_emits_checked_nul_delimited_manifest_order() {
    let root = fixture_root();
    fs::write(
        root.join("scripts/residual-bash-paths.txt"),
        "# retained\nscripts/first.sh\n\nskills/second.inc.bash\n",
    )
    .expect("write manifest");
    fs::create_dir_all(root.join("skills")).expect("create skill fixture");
    fs::write(root.join("scripts/first.sh"), "").expect("write first path");
    fs::write(root.join("skills/second.inc.bash"), "").expect("write second path");

    let output = Command::new(env!("CARGO_BIN_EXE_larch-residual-bash-paths"))
        .args(["--root", root.to_str().expect("UTF-8 fixture root")])
        .output()
        .expect("run residual Bash reader");

    assert!(output.status.success());
    assert_eq!(output.stdout, b"scripts/first.sh\0skills/second.inc.bash\0");
    assert!(output.stderr.is_empty());
    fs::remove_dir_all(root).expect("remove residual Bash command fixture");
}

#[test]
fn command_rejects_a_missing_manifest_path() {
    let root = fixture_root();
    fs::write(
        root.join("scripts/residual-bash-paths.txt"),
        "scripts/missing.sh\n",
    )
    .expect("write manifest");

    let output = Command::new(env!("CARGO_BIN_EXE_larch-residual-bash-paths"))
        .args(["--root", root.to_str().expect("UTF-8 fixture root")])
        .output()
        .expect("run residual Bash reader");

    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty());
    assert!(
        String::from_utf8(output.stderr)
            .expect("UTF-8 error")
            .contains("missing residual bash path")
    );
    fs::remove_dir_all(root).expect("remove residual Bash command fixture");
}
