use crate::support;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn rejects_unsafe_script_and_shell_fence_expansions() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/example.sh",
        concat!(
            "#!/bin/bash\n",
            "i=3\n",
            "printf '%s\\n' \"$i…\"\n",
            "printf '%s\\n' \"${i}…\" \"$i...\" '$i…'\n",
            "# printf '%s\\n' \"$i…\"\n",
        )
        .as_bytes(),
    );
    repository.write(
        "skills/example/SKILL.md",
        concat!(
            "`$outside…`\n",
            "```text\n$item…\n```\n",
            "```bash\nprintf '%s\\n' \"$item→\"\n```\n",
        )
        .as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "bash32-nonascii-expansion"])
        .assert()
        .failure()
        .stdout(predicate::eq(concat!(
            "scripts/example.sh:3: bare $name immediately before non-ASCII text is unsafe on Bash 3.2; use ${name}\n",
            "skills/example/SKILL.md:6: bare $name immediately before non-ASCII text is unsafe on Bash 3.2; use ${name}\n",
        )));
}
