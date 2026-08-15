mod support;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn codex_exec_auth_covers_shell_markdown_and_rust_without_duplicate_shell_findings() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/bad.sh",
        b"#!/usr/bin/env bash\nCODEX_HOME=/tmp/codex codex exec --full-auto\nA=1 B=codex exec --full-auto\necho \"$(codex exec --full-auto)\"\n",
    );
    repository.write(
        "skills/example/scripts/bad.sh",
        b"#!/usr/bin/env bash\ncodex exec --full-auto\n",
    );
    repository.write(
        "scripts/test-fixture.sh",
        b"#!/usr/bin/env bash\ncodex exec --full-auto\n",
    );
    repository.write(
        "skills/example/SKILL.md",
        b"```Bash\ncodex exec --full-auto\n```\n```python\ncodex exec --full-auto\n```\n````bash\n``` codex exec --full-auto\n````\n",
    );
    repository.write(
        ".claude/skills/example/SKILL.md",
        b"~~~sh\ncodex \\\n  exec --full-auto\n~~~\n",
    );
    repository.write(
        "crates/example/src/direct.rs",
        b"use std::process::Command;\nfn run() { Command::new(\"codex\").args([\"exec\", \"--full-auto\"]); }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "codex-exec-auth"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "scripts/bad.sh:2: unwired Codex dispatch",
        ))
        .stdout(predicate::str::contains(
            "scripts/bad.sh:3: unwired Codex dispatch",
        ))
        .stdout(predicate::str::contains("scripts/bad.sh:4: unwired Codex dispatch").count(1))
        .stdout(predicate::str::contains(
            "skills/example/scripts/bad.sh:2: unwired Codex dispatch",
        ))
        .stdout(predicate::str::contains(
            "skills/example/SKILL.md:2: unwired Codex dispatch",
        ))
        .stdout(predicate::str::contains(
            "skills/example/SKILL.md:8: unwired Codex dispatch",
        ))
        .stdout(predicate::str::contains(
            ".claude/skills/example/SKILL.md:2: unwired Codex dispatch",
        ))
        .stdout(predicate::str::contains(
            "crates/example/src/direct.rs:2: unwired Codex dispatch",
        ))
        .stdout(predicate::str::contains("scripts/test-fixture.sh").not())
        .stdout(predicate::str::contains("SKILL.md:5:").not());
}

#[test]
fn codex_exec_auth_keeps_reasoned_suppressions_and_ignores_comments() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/suppressed.sh",
        b"#!/usr/bin/env bash\ncodex exec --full-auto # lint-codex-exec-auth: ok fixture uses the documented escape hatch\n# codex exec --full-auto\n",
    );
    repository.write(
        "skills/example/SKILL.md",
        b"```shell\ncodex exec --full-auto # lint-codex-exec-auth: ok fixture documentation\n# codex exec --full-auto\n```\n",
    );
    repository.write(
        "crates/example/src/direct.rs",
        b"use std::process::Command;\nfn run() { Command::new(\"codex\").arg(\"exec\"); } // lint-codex-exec-auth: ok fixture exercises Rust suppression\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "codex-exec-auth"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}

#[test]
fn codex_exec_auth_scans_python_dispatches() {
    let repository = TempRepo::new();
    repository.write(
        "python/new_launcher.py",
        b"import subprocess\nsubprocess.run([\"codex\", \"exec\", \"--full-auto\"])\n",
    );
    repository.write(
        "python/larch/agents/agents.py",
        b"child = [\"codex\", \"exec\", \"--full-auto\"]\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "codex-exec-auth"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "python/new_launcher.py:2: unwired Python Codex dispatch",
        ))
        .stdout(predicate::str::contains("python/larch/agents/agents.py").not());
}
