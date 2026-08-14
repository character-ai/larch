//! Canonical residual Bash manifest reader shared by the released CLI and CI.

use std::{
    collections::BTreeSet,
    fmt::Write as _,
    fs,
    path::{Component, Path},
};

/// Repository-relative path to the residual Bash manifest.
pub const RESIDUAL_BASH_MANIFEST: &str = "scripts/residual-bash-paths.txt";

const SHELL_SUFFIXES: [&str; 2] = [".sh", ".inc.bash"];

/// Read and validate residual Bash paths in manifest order.
///
/// # Errors
///
/// Returns an error when the manifest cannot be read, contains an invalid or
/// duplicate path, or names a missing file while `check_exists` is true.
pub fn read_residual_bash_paths(root: &Path, check_exists: bool) -> Result<Vec<String>, String> {
    let manifest = root.join(RESIDUAL_BASH_MANIFEST);
    let source = fs::read_to_string(&manifest).map_err(|_| {
        format!(
            "could not read residual bash manifest: {}",
            manifest.display()
        )
    })?;
    let mut paths = Vec::new();
    let mut seen = BTreeSet::new();
    for (offset, line) in source.lines().enumerate() {
        let value = line.trim();
        if value.is_empty() || value.starts_with('#') {
            continue;
        }
        validate_residual_path(value)?;
        if !seen.insert(value.to_owned()) {
            return Err(format!(
                "duplicate residual bash path at {}:{}: {value}",
                manifest.display(),
                offset + 1
            ));
        }
        if check_exists && !root.join(value).is_file() {
            return Err(format!(
                "missing residual bash path under {}: {value}",
                root.display()
            ));
        }
        paths.push(value.to_owned());
    }
    Ok(paths)
}

/// Return whether a raw repository path has an allowed shell suffix.
#[must_use]
pub fn has_shell_suffix_bytes(path: &[u8]) -> bool {
    SHELL_SUFFIXES
        .iter()
        .any(|suffix| path.ends_with(suffix.as_bytes()))
}

fn validate_residual_path(value: &str) -> Result<(), String> {
    if value.starts_with('/') || value.contains('\0') {
        return Err(format!(
            "invalid residual bash path: {}",
            python_repr(value)
        ));
    }
    if Path::new(value)
        .components()
        .any(|component| component == Component::ParentDir)
    {
        return Err(format!(
            "invalid residual bash path: {}",
            python_repr(value)
        ));
    }
    if value.starts_with("larch-logs/") || value.starts_with("node_modules/") {
        return Err(format!(
            "excluded residual bash path: {}",
            python_repr(value)
        ));
    }
    if !has_shell_suffix_bytes(value.as_bytes()) {
        return Err(format!(
            "residual bash path must end with .sh or .inc.bash: {}",
            python_repr(value)
        ));
    }
    Ok(())
}

fn python_repr(value: &str) -> String {
    let mut rendered = String::from("'");
    for character in value.chars() {
        match character {
            '\\' => rendered.push_str("\\\\"),
            '\'' => rendered.push_str("\\'"),
            '\n' => rendered.push_str("\\n"),
            '\r' => rendered.push_str("\\r"),
            '\t' => rendered.push_str("\\t"),
            character if character.is_control() => {
                let _ = write!(rendered, "\\x{:02x}", character as u32);
            }
            character => rendered.push(character),
        }
    }
    rendered.push('\'');
    rendered
}

#[cfg(test)]
mod tests {
    use super::{has_shell_suffix_bytes, read_residual_bash_paths};
    use std::{
        fs,
        sync::atomic::{AtomicU64, Ordering},
    };

    static NEXT_FIXTURE: AtomicU64 = AtomicU64::new(0);

    fn fixture_root() -> std::path::PathBuf {
        let root = std::env::temp_dir().join(format!(
            "larch-residual-bash-{}-{}",
            std::process::id(),
            NEXT_FIXTURE.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(root.join("scripts")).expect("create residual Bash fixture");
        root
    }

    #[test]
    fn reads_checked_paths_in_manifest_order() {
        let root = fixture_root();
        fs::write(
            root.join("scripts/residual-bash-paths.txt"),
            "# retained\nscripts/first.sh\n\nskills/second.inc.bash\n",
        )
        .expect("write manifest");
        fs::create_dir_all(root.join("skills")).expect("create skill fixture");
        fs::write(root.join("scripts/first.sh"), "").expect("write first path");
        fs::write(root.join("skills/second.inc.bash"), "").expect("write second path");

        assert_eq!(
            read_residual_bash_paths(&root, true).expect("read checked manifest"),
            ["scripts/first.sh", "skills/second.inc.bash"]
        );
        fs::remove_dir_all(root).expect("remove residual Bash fixture");
    }

    #[test]
    fn rejects_duplicates_and_invalid_suffixes() {
        let root = fixture_root();
        let manifest = root.join("scripts/residual-bash-paths.txt");
        fs::write(&manifest, "scripts/kept.sh\nscripts/kept.sh\n")
            .expect("write duplicate manifest");
        assert!(
            read_residual_bash_paths(&root, false)
                .expect_err("duplicate must fail")
                .contains("duplicate residual bash path")
        );

        fs::write(&manifest, "scripts/not-shell.txt\n").expect("write invalid manifest");
        assert!(
            read_residual_bash_paths(&root, false)
                .expect_err("invalid suffix must fail")
                .contains("must end with .sh or .inc.bash")
        );
        assert!(has_shell_suffix_bytes(b"scripts/kept.sh"));
        assert!(has_shell_suffix_bytes(b"scripts/include.inc.bash"));
        assert!(!has_shell_suffix_bytes(b"scripts/not-shell.txt"));
        fs::remove_dir_all(root).expect("remove residual Bash fixture");
    }
}
