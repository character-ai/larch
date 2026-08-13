//! End-to-end coverage for `/umbrella` command discovery.

use std::process::{Command, Output};

const UMBRELLA_VERBS: [(&str, &str); 8] = [
    ("prepare", "Usage: umbrella prepare "),
    ("persist-proposal", "Usage: umbrella persist-proposal "),
    ("mark-in-flight", "Usage: umbrella mark-in-flight "),
    ("record-resolved", "Usage: umbrella record-resolved "),
    (
        "reconcile-in-flight",
        "Usage: umbrella reconcile-in-flight ",
    ),
    ("mutate", "Usage: umbrella mutate "),
    ("verify", "Usage: umbrella verify "),
    ("verify-completion", "Usage: umbrella verify-completion "),
];

fn run(verb: &str, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(["umbrella", verb])
        .args(arguments)
        .output()
        .expect("run umbrella command")
}

#[test]
fn every_umbrella_verb_prints_usage_for_help_and_usage_refusals() {
    for (verb, usage_prefix) in UMBRELLA_VERBS {
        let refusal = run(verb, &[]);
        assert_eq!(
            refusal.status.code(),
            Some(2),
            "umbrella {verb} missing arguments must refuse"
        );
        assert_eq!(
            refusal.stdout, b"UMBRELLA_FAILED=true\nREASON=usage\n",
            "umbrella {verb} must preserve its machine refusal envelope"
        );
        let usage = String::from_utf8(refusal.stderr).expect("usage stderr is UTF-8");
        assert!(
            usage.starts_with(usage_prefix),
            "umbrella {verb} usage stderr: {usage:?}"
        );

        for help in ["-h", "--help"] {
            let output = run(verb, &[help]);
            assert_eq!(
                output.status.code(),
                Some(0),
                "umbrella {verb} {help} must succeed"
            );
            assert!(
                output.stdout.is_empty(),
                "umbrella {verb} {help} must not emit machine rows"
            );
            let stderr = String::from_utf8(output.stderr).expect("help stderr is UTF-8");
            assert_eq!(
                stderr, usage,
                "umbrella {verb} {help} must print the usage refusal text"
            );
            if verb == "persist-proposal" {
                assert!(
                    stderr.contains("ProposalRecord JSON object"),
                    "persist-proposal help must identify its proposal shape"
                );
            }
        }
    }
}
