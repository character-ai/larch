use crate::support;

use predicates::prelude::*;
use support::TempRepo;

const MESSAGE: &str = "production shell script must be listed in scripts/residual-bash-paths.txt or be an at-most-25-line exec-only scripts/larch.sh shim";

#[test]
fn residual_bash_shim_allows_inventory_shims_fixtures_and_harnesses() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/residual-bash-paths.txt",
        b"# approved residual\nscripts/retained.sh\nscripts/helpers.inc.bash\n",
    );
    repository.write(
        "scripts/retained.sh",
        b"#!/usr/bin/env bash\nprintf 'residual\\n'\n",
    );
    repository.write("scripts/helpers.inc.bash", b"fixture_helper() { :; }\n");
    repository.write(
        "skills/example/scripts/delegate.sh",
        b"#!/usr/bin/env bash\nset -euo pipefail\nSCRIPT_DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd -P)\"\nPLUGIN_ROOT=\"${CLAUDE_PLUGIN_ROOT:-$(cd \"$SCRIPT_DIR/../../..\" && pwd -P)}\"\nexport CLAUDE_PLUGIN_ROOT=\"$PLUGIN_ROOT\"\nexec env LARCH_MODE=fixture \"$PLUGIN_ROOT/scripts/larch.sh\" example echo \"$@\"\n",
    );
    let mut maximum = String::from("#!/usr/bin/env bash\nset -euo pipefail\n");
    for _ in 0..22 {
        maximum.push_str("# padding\n");
    }
    maximum.push_str("exec \"$CLAUDE_PLUGIN_ROOT/scripts/larch.sh\" example echo \"$@\"\n");
    repository.write("scripts/maximum-shim.sh", maximum.as_bytes());
    repository.write("scripts/test-harness.sh", b"#!/usr/bin/env bash\nprintf 'test\\n'\n");
    repository.write("fixtures/example/body.sh", b"#!/usr/bin/env bash\nprintf 'fixture\\n'\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "residual-bash-shim"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}

#[test]
fn residual_bash_shim_rejects_unlisted_business_logic_and_non_larch_exec() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/business.sh",
        b"#!/usr/bin/env bash\nset -euo pipefail\nprintf 'business logic\\n'\n",
    );
    repository.write(
        "scripts/wrong-exec.sh",
        b"#!/usr/bin/env bash\nset -euo pipefail\nexec /usr/bin/true\n",
    );
    repository.write(
        "scripts/sudo-exec.sh",
        b"#!/usr/bin/env bash\nset -euo pipefail\nexec sudo \"$CLAUDE_PLUGIN_ROOT/scripts/larch.sh\" example echo\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "residual-bash-shim"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(format!(
            "scripts/business.sh:1: {MESSAGE}\n"
        )))
        .stdout(predicate::str::contains(format!(
            "scripts/wrong-exec.sh:1: {MESSAGE}\n"
        )))
        .stdout(predicate::str::contains(format!(
            "scripts/sudo-exec.sh:1: {MESSAGE}\n"
        )))
        .stderr("");
}

#[test]
fn residual_bash_shim_rejects_overlong_and_multi_command_delegates() {
    let repository = TempRepo::new();
    let mut overlong = String::from("#!/usr/bin/env bash\nset -euo pipefail\n");
    for _ in 0..23 {
        overlong.push_str("# padding\n");
    }
    overlong.push_str("exec \"$CLAUDE_PLUGIN_ROOT/scripts/larch.sh\" example echo \"$@\"\n");
    repository.write("scripts/overlong.sh", overlong.as_bytes());
    repository.write(
        "scripts/multiple.sh",
        b"#!/usr/bin/env bash\nset -euo pipefail\n\"$CLAUDE_PLUGIN_ROOT/scripts/larch.sh\" example first\nexec \"$CLAUDE_PLUGIN_ROOT/scripts/larch.sh\" example second\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "residual-bash-shim"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(format!(
            "scripts/overlong.sh:1: {MESSAGE}\n"
        )))
        .stdout(predicate::str::contains(format!(
            "scripts/multiple.sh:1: {MESSAGE}\n"
        )))
        .stderr("");
}

#[test]
fn residual_bash_shim_fails_closed_on_invalid_inventory() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/residual-bash-paths.txt",
        b"scripts/missing.sh\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "residual-bash-shim"])
        .assert()
        .code(2)
        .stdout("")
        .stderr(predicate::str::contains(
            "missing residual bash path: scripts/missing.sh",
        ));
}
