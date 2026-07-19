mod support;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn larch_runtime_entrypoint_rejects_direct_binary_callers() {
    let repository = TempRepo::new();
    repository.write(
        "python/larch/core/direct.py",
        b"from pathlib import Path\nBINARY = Path('/plugin') / \"bin\" / \"larch\"\nOTHER = Path('/plugin', \"bin\", \"larch\")\n",
    );
    repository.write(
        "agents/direct.md",
        b"Run `\"$CLAUDE_PLUGIN_ROOT/bin/larch\" git clean-tree`.\n",
    );
    repository.write(
        "skills/example/SKILL.md",
        b"```bash\n${CLAUDE_PLUGIN_ROOT}/bin/larch git clean-tree\n```\n",
    );
    repository.write(
        "scripts/direct.sh",
        b"#!/usr/bin/env bash\nexec \"$CLAUDE_PLUGIN_ROOT/bin/larch\" \"$@\"\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "larch-runtime-entrypoint"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "python/larch/core/direct.py:2: direct bin/larch production entrypoint",
        ))
        .stdout(predicate::str::contains(
            "python/larch/core/direct.py:3: direct bin/larch production entrypoint",
        ))
        .stdout(predicate::str::contains(
            "agents/direct.md:1: direct bin/larch production entrypoint",
        ))
        .stdout(predicate::str::contains(
            "skills/example/SKILL.md:2: direct bin/larch production entrypoint",
        ))
        .stdout(predicate::str::contains(
            "scripts/direct.sh:2: direct bin/larch production entrypoint",
        ));
}

#[test]
fn larch_runtime_entrypoint_allows_bootstrap_verification_and_nonproduction_surfaces() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/larch.sh",
        b"#!/usr/bin/env bash\nexec \"$plugin_root/bin/larch\" \"$@\"\n",
    );
    repository.write(
        "python/larch/core/upgrade_larch.py",
        b"binary = root / \"bin/larch\"\n",
    );
    repository.write(
        "python/larch/core/caller.py",
        b"entrypoint = root / \"scripts/larch.sh\"\n",
    );
    repository.write(
        "scripts/test-entrypoint.sh",
        b"#!/usr/bin/env bash\n\"$CLAUDE_PLUGIN_ROOT/bin/larch\" example echo fixture\n",
    );
    repository.write(
        "plugin/agents/generated.md",
        b"Run `$CLAUDE_PLUGIN_ROOT/bin/larch`.\n",
    );
    repository.write("docs/example.md", b"`bin/larch` is installed output.\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "larch-runtime-entrypoint"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}
