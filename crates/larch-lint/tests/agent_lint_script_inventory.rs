use std::collections::BTreeSet;
use std::path::Path;

use larch_lint::{GitCli, Repository};

const RESIDUAL_MANIFEST: &str = "scripts/residual-bash-paths.txt";
const AGENT_LINT_INVENTORY: &str = "scripts/agent-lint-script-inventory.txt";
const EXCLUDED_PREFIXES: [&str; 2] = ["larch-logs/", "node_modules/"];

#[derive(Clone, Copy)]
enum InventoryKind {
    ResidualBash,
    AgentLint,
}

impl InventoryKind {
    fn accepts(self, path: &str) -> bool {
        path.strip_suffix(".sh").is_some()
            || path.strip_suffix(".inc.bash").is_some()
            || matches!(self, Self::AgentLint) && path.strip_suffix(".awk").is_some()
    }
}

fn read_inventory(
    repository: &Repository,
    manifest_path: &str,
    kind: InventoryKind,
) -> BTreeSet<String> {
    let manifest = repository
        .paths()
        .iter()
        .find(|path| path.as_str() == manifest_path)
        .unwrap_or_else(|| panic!("missing inventory manifest: {manifest_path}"));
    let source = repository
        .read_utf8(manifest)
        .unwrap_or_else(|error| panic!("could not read {manifest_path}: {error}"));
    let mut paths = BTreeSet::new();

    for (index, line) in source.lines().enumerate() {
        let raw = line.trim();
        if raw.is_empty() || raw.starts_with('#') {
            continue;
        }

        assert!(
            !raw.starts_with('/')
                && !raw.contains('\0')
                && !raw.split('/').any(|part| part == ".."),
            "{manifest_path}:{}: invalid inventory path: {raw:?}",
            index + 1
        );
        assert!(
            !EXCLUDED_PREFIXES
                .iter()
                .any(|prefix| raw.starts_with(prefix)),
            "{manifest_path}:{}: excluded inventory path: {raw:?}",
            index + 1
        );
        assert!(
            kind.accepts(raw),
            "{manifest_path}:{}: unsupported inventory path type: {raw:?}",
            index + 1
        );
        assert!(
            paths.insert(raw.to_owned()),
            "duplicate inventory path at {manifest_path}:{}: {raw}",
            index + 1
        );
        assert!(
            repository
                .paths()
                .binary_search_by(|path| path.as_str().cmp(raw))
                .is_ok(),
            "missing inventory path: {raw}"
        );
    }

    paths
}

#[test]
fn agent_lint_inventory_covers_the_residual_bash_manifest() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let repository =
        Repository::discover(&GitCli, &root).expect("discover the live larch repository");
    let residual = read_inventory(
        &repository,
        RESIDUAL_MANIFEST,
        InventoryKind::ResidualBash,
    );
    let agent_lint = read_inventory(
        &repository,
        AGENT_LINT_INVENTORY,
        InventoryKind::AgentLint,
    );
    let missing: Vec<_> = residual
        .difference(&agent_lint)
        .map(String::as_str)
        .collect();

    assert!(
        missing.is_empty(),
        "{AGENT_LINT_INVENTORY} must include every path from {RESIDUAL_MANIFEST}; missing: {}",
        missing.join(", ")
    );
}
