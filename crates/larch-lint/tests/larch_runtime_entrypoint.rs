use crate::support;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn larch_runtime_entrypoint_rejects_direct_binary_callers() {
    let repository = TempRepo::new();
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
fn larch_runtime_entrypoint_allows_bootstrap_and_nonproduction_surfaces() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/larch.sh",
        b"#!/usr/bin/env bash\nexec \"$plugin_root/bin/larch\" \"$@\"\n",
    );
    repository.write(
        "scripts/test-entrypoint.sh",
        b"#!/usr/bin/env bash\n\"$CLAUDE_PLUGIN_ROOT/bin/larch\" example echo fixture\n",
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

#[test]
fn larch_runtime_entrypoint_rejects_retired_python_bridge_in_rust() {
    let repository = TempRepo::new();
    repository.write(
        "crates/example/src/bridge.rs",
        b"let program = PythonVerbProgram::new(root)?;\nlet child = ExternalProgram::PythonVerb(program);\nrun_python_verb(args)?;\nlet dispatcher = root.join(\"python/cli.py\");\nlet alternate = root.join(\"python\").join(\"cli.py\");\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "larch-runtime-entrypoint"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "crates/example/src/bridge.rs:1: retired Python runtime bridge",
        ))
        .stdout(predicate::str::contains(
            "crates/example/src/bridge.rs:2: retired Python runtime bridge",
        ))
        .stdout(predicate::str::contains(
            "crates/example/src/bridge.rs:3: retired Python runtime bridge",
        ))
        .stdout(predicate::str::contains(
            "crates/example/src/bridge.rs:4: retired Python runtime bridge",
        ))
        .stdout(predicate::str::contains(
            "crates/example/src/bridge.rs:5: retired Python runtime bridge",
        ));
}
