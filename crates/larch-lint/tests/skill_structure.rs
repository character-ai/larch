use predicates::prelude::*;

use crate::support::TempRepo;

#[test]
fn skill_structure_evaluates_live_text_order_count_and_path_contracts() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/config/skill-structure-pins.jsonl",
        br#"{"id":"required text","path":"skills/demo/SKILL.md","kind":"contains","needle":"alpha"}
{"id":"forbidden text","path":"skills/demo/SKILL.md","kind":"absent","needle":"retired"}
{"id":"ordered text","path":"skills/demo/SKILL.md","kind":"ordered","needle":"alpha","needle2":"omega","match_mode":"contains"}
{"id":"counted text","path":"skills/demo/SKILL.md","kind":"exact_count","needle":"entry","expected":2,"count_unit":"substring"}
{"id":"same line","path":"skills/demo/SKILL.md","kind":"same_line","tokens":["one","two"]}
{"id":"required path","path":"skills/demo/references","kind":"path_is_dir"}
"#,
    );
    repository.write(
        "skills/demo/SKILL.md",
        b"alpha\none two\nentry entry\nomega\n",
    );
    repository.write("skills/demo/references/detail.md", b"detail\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "skill-structure"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());

    repository.write(
        "skills/demo/SKILL.md",
        b"omega\none only\nentry\nretired\n",
    );
    TempRepo::command_from(repository.path())
        .args(["rule", "skill-structure"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "skills/demo/SKILL.md:1: required text: required text is missing",
        ))
        .stdout(predicate::str::contains(
            "skills/demo/SKILL.md:4: forbidden text: forbidden text is present",
        ))
        .stdout(predicate::str::contains(
            "ordered text: required anchors are missing or out of order",
        ))
        .stdout(predicate::str::contains(
            "counted text: expected count 2, observed 1",
        ))
        .stdout(predicate::str::contains(
            "same line: no line contains every required token",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn skill_structure_rejects_invalid_or_duplicate_manifest_rows() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/config/skill-structure-pins.jsonl",
        b"{\"id\":\"duplicate\",\"path\":\"skills/demo/SKILL.md\",\"kind\":\"contains\",\"needle\":\"one\"}\n{\"id\":\"duplicate\",\"path\":\"skills/demo/SKILL.md\",\"kind\":\"contains\",\"needle\":\"two\"}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "skill-structure"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("duplicate pin id \"duplicate\""));

    repository.write(
        "crates/larch-lint/config/skill-structure-pins.jsonl",
        b"{\"id\":\"unsafe\",\"path\":\"../outside\",\"kind\":\"path_exists\"}\n",
    );
    TempRepo::command_from(repository.path())
        .args(["rule", "skill-structure"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("pin \"unsafe\" has an unsafe path"));

    repository.write(
        "crates/larch-lint/config/skill-structure-pins.jsonl",
        b"{\"id\":\"bad adjacent unit\",\"path\":\"skills/demo/SKILL.md\",\"kind\":\"adjacent_pair_count_at_least\",\"needle\":\"one\",\"needle2\":\"two\",\"expected\":1}\n",
    );
    TempRepo::command_from(repository.path())
        .args(["rule", "skill-structure"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "pin \"bad adjacent unit\" requires count_unit adjacent_pair",
        ));

    repository.write(
        "crates/larch-lint/config/skill-structure-pins.jsonl",
        b"{\"id\":\"bad count unit\",\"path\":\"skills/demo/SKILL.md\",\"kind\":\"exact_count\",\"needle\":\"one\",\"expected\":1,\"count_unit\":\"adjacent_pair\"}\n",
    );
    TempRepo::command_from(repository.path())
        .args(["rule", "skill-structure"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "pin \"bad count unit\" may use count_unit adjacent_pair only with adjacent_pair_count_at_least",
        ));
}

#[test]
fn skill_structure_evaluates_regex_proximity_cross_file_and_path_contracts() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/config/skill-structure-pins.jsonl",
        br#"{"id":"regex required","path":"skills/demo/SKILL.md","kind":"regex_contains","needle":"(?m:^alpha$)"}
{"id":"regex forbidden","path":"skills/demo/SKILL.md","kind":"regex_absent","needle":"retired.+token"}
{"id":"minimum count","path":"skills/demo/SKILL.md","kind":"count_at_least","needle":"alpha","expected":2,"count_unit":"substring"}
{"id":"adjacent lines","path":"skills/demo/SKILL.md","kind":"adjacent_pair_count_at_least","needle":"alpha","needle2":"beta","expected":2,"count_unit":"adjacent_pair"}
{"id":"nearby text","path":"skills/demo/SKILL.md","kind":"near","needle":"anchor","needle2":"nearby","bound":20}
{"id":"cross file","path":"skills/demo/SKILL.md","kind":"cross_file_bound","needle":"anchor","path2":"skills/demo/other.md","needle2":"other anchor","bound":1}
{"id":"line prefix","path":"skills/demo/SKILL.md","kind":"line_starts_with","needle":"alpha"}
{"id":"forbidden prefix","path":"skills/demo/SKILL.md","kind":"line_not_starts_with","needle":"retired"}
{"id":"file exists","path":"skills/demo/SKILL.md","kind":"path_exists"}
{"id":"path absent","path":"skills/demo/missing.md","kind":"path_absent"}
{"id":"not a directory","path":"skills/demo/SKILL.md","kind":"path_not_dir"}
"#,
    );
    repository.write(
        "skills/demo/SKILL.md",
        b"alpha\nbeta\nanchor nearby\nalpha\nbeta\n",
    );
    repository.write("skills/demo/other.md", b"zero\nzero\nzero\nother anchor\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "skill-structure"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());

    repository.write(
        "skills/demo/SKILL.md",
        b"retired token\nanchor\npadding beyond bound\n",
    );
    TempRepo::command_from(repository.path())
        .args(["rule", "skill-structure"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "regex required: required regex does not match",
        ))
        .stdout(predicate::str::contains(
            "regex forbidden: forbidden regex matches",
        ))
        .stdout(predicate::str::contains(
            "adjacent lines: expected 2 adjacent pairs, observed 0",
        ))
        .stdout(predicate::str::contains(
            "nearby text: required text is outside the proximity bound",
        ))
        .stdout(predicate::str::contains(
            "cross file: cross-file anchors exceed their line bound",
        ))
        .stdout(predicate::str::contains(
            "line prefix: line-prefix contract is not satisfied",
        ))
        .stdout(predicate::str::contains(
            "forbidden prefix: line-prefix contract is not satisfied",
        ));
}
