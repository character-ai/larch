//! Golden parity for the `/issue` input grammar and candidate allocator.
//!
//! Every expectation is the output the Python owners
//! (`larch.issue.issue_create.parse_issue_input` and `allocate_candidates`)
//! produced for the same input, taken from the pinned regression cases in
//! `python/tests/issue/test_issue_create.py`.

use std::fmt::Write as _;

use larch_core::{
    CandidateRowDefect, InputMode, ParsedItem, allocate_candidates, parse_issue_input,
    title_is_archival,
};

/// `(name, input, expected items as (title, body, reviewer, vote, phase, malformed))`.
type ParseCase = (
    &'static str,
    &'static str,
    &'static [(
        &'static str,
        &'static str,
        &'static str,
        &'static str,
        &'static str,
        bool,
    )],
);

const PARSE_CASES: &[ParseCase] = &[
    (
        // #129: an `### <heading>` inside an OOS description is absorbed once a
        // later metadata field proves it did not open a new item.
        "oos-subheading-absorption",
        "### OOS_1: Example bug\n- **Description**: First description paragraph.\n### Notes\nSecond paragraph after the subheading.\n- **Reviewer**: Codex\n- **Vote tally**: YES=3, NO=0\n- **Phase**: review\n",
        &[(
            "Example bug",
            "First description paragraph.\n### Notes\nSecond paragraph after the subheading.",
            "Codex",
            "YES=3, NO=0",
            "review",
            false,
        )],
    ),
    (
        // #129: the same bullets inside a generic item are body text, never
        // metadata, so nothing is lifted out of the body.
        "generic-body-preserves-oos-bullets",
        "### Regular issue title\nThis is preceding body text that must survive.\n- **Description**: stray description bullet that should stay in body\n- **Reviewer**: stray reviewer bullet\n- **Vote tally**: stray tally bullet\n- **Phase**: stray phase bullet\nTrailing body text after bullets.\n",
        &[(
            "Regular issue title",
            "This is preceding body text that must survive.\n- **Description**: stray description bullet that should stay in body\n- **Reviewer**: stray reviewer bullet\n- **Vote tally**: stray tally bullet\n- **Phase**: stray phase bullet\nTrailing body text after bullets.",
            "",
            "",
            "",
            false,
        )],
    ),
    (
        // #131: an empty inline description still captures its continuations,
        // including the blank line between them.
        "empty-inline-description",
        "### OOS_1: Description body from continuations only\n- **Description**:\n  First continuation line.\n\n  Third line after blank.\n- **Reviewer**: Code\n- **Vote tally**: YES=3, NO=0\n- **Phase**: design\n",
        &[(
            "Description body from continuations only",
            "  First continuation line.\n\n  Third line after blank.",
            "Code",
            "YES=3, NO=0",
            "design",
            false,
        )],
    ),
    (
        // #132: a nested OOS-shaped heading inside a generic body stays payload.
        "generic-body-absorbs-nested-oos-heading",
        "### Regular issue with nested OOS-shaped heading\nPreceding body text.\n### OOS_42: nested example\nTrailing body text after the nested heading.\n",
        &[(
            "Regular issue with nested OOS-shaped heading",
            "Preceding body text.\n### OOS_42: nested example\nTrailing body text after the nested heading.",
            "",
            "",
            "",
            false,
        )],
    ),
    (
        // #138: an ambiguous heading with no structured close splits the block
        // and marks the interrupted item malformed. A title with no body at all
        // is malformed too.
        "ambiguous-boundary-and-title-only",
        "### OOS_1: first\n- **Description**: body\n### Ambiguous\npending body\n### OOS_2: second\n- **Description**: ok\n- **Reviewer**: R\n- **Vote tally**: YES=1\n- **Phase**: review\n### title only\n",
        &[
            ("first", "body", "", "", "", true),
            ("Ambiguous", "pending body", "", "", "", false),
            ("second", "ok", "R", "YES=1", "review", false),
            ("title only", "", "", "", "", true),
        ],
    ),
    (
        // #5260: a FINDING-block OOS uses `Concern` and `Reviewer(s)`, and its
        // trailing prose is body rather than a dropped remainder.
        "finding-format-captures-body",
        "### OOS_1: [OUT_OF_SCOPE] Stale rubric cross-reference\n- **Reviewer(s)**: cursor-edge-cases, cursor-testing\n- **Severity**: latent\n- **Concern**: `plan-review.md` points to a renamed section; stale cross-doc guidance only.\n- **Suggested revisions (informational for voters; coder decides)**:\n  - From cursor-edge-cases: Update the bullet to the new contract.\n",
        &[(
            "[OUT_OF_SCOPE] Stale rubric cross-reference",
            "`plan-review.md` points to a renamed section; stale cross-doc guidance only.\n- **Suggested revisions (informational for voters; coder decides)**:\n  - From cursor-edge-cases: Update the bullet to the new contract.",
            "cursor-edge-cases, cursor-testing",
            "",
            "",
            false,
        )],
    ),
    (
        // #5260: prose directly under an OOS heading is captured even with no
        // field label at all.
        "oos-body-without-field-labels",
        "### OOS_1: Body prose with no field labels\nFirst body line under the heading.\nSecond body line.\n",
        &[(
            "Body prose with no field labels",
            "First body line under the heading.\nSecond body line.",
            "",
            "",
            "",
            false,
        )],
    ),
    (
        "generic-fenced-heading-stays-body",
        "### Fixture item: one intended item with a fenced payload\nIntro line before the fence.\n\n```markdown\n### G-Fake-1: fenced heading that is payload, not a boundary\n- Why: this line is verbatim payload inside a fenced block.\n```\n\nTrailing line after the fence.\n",
        &[(
            "Fixture item: one intended item with a fenced payload",
            "Intro line before the fence.\n\n```markdown\n### G-Fake-1: fenced heading that is payload, not a boundary\n- Why: this line is verbatim payload inside a fenced block.\n```\n\nTrailing line after the fence.",
            "",
            "",
            "",
            false,
        )],
    ),
    (
        "generic-fenced-oos-heading-stays-generic",
        "### Generic item with fenced OOS payload\nBefore fence.\n~~~markdown\n### OOS_42: fenced heading that must stay payload\nFenced OOS-shaped body.\n~~~\nAfter fence.\n",
        &[(
            "Generic item with fenced OOS payload",
            "Before fence.\n~~~markdown\n### OOS_42: fenced heading that must stay payload\nFenced OOS-shaped body.\n~~~\nAfter fence.",
            "",
            "",
            "",
            false,
        )],
    ),
    (
        // An unmatched opener fences nothing, so the later boundary still splits.
        "unclosed-fence-does-not-protect-later-boundary",
        "### First item with unclosed fence\n```markdown\nPlain text before the next real boundary.\n### Second item after unclosed fence\nSecond body.\n",
        &[
            (
                "First item with unclosed fence",
                "```markdown\nPlain text before the next real boundary.",
                "",
                "",
                "",
                false,
            ),
            (
                "Second item after unclosed fence",
                "Second body.",
                "",
                "",
                "",
                false,
            ),
        ],
    ),
    (
        "oos-description-fenced-heading-and-field-stay-body",
        "### OOS_1: Fenced payload in description\n- **Description**: Before fence.\n```markdown\n### Fenced heading stays payload\n- **Description**: fenced field-looking line stays body\n```\n- **Reviewer**: Codex\n- **Vote tally**: YES=1, NO=0\n- **Phase**: review\n",
        &[(
            "Fenced payload in description",
            "Before fence.\n```markdown\n### Fenced heading stays payload\n- **Description**: fenced field-looking line stays body\n```",
            "Codex",
            "YES=1, NO=0",
            "review",
            false,
        )],
    ),
    (
        "closed-fence-then-real-boundary-splits",
        "### First item with closed fence\n```\n### Payload heading inside fence\n```\n### Second item after fence\nSecond body.\n",
        &[
            (
                "First item with closed fence",
                "```\n### Payload heading inside fence\n```",
                "",
                "",
                "",
                false,
            ),
            ("Second item after fence", "Second body.", "", "", "", false),
        ],
    ),
    (
        // The closer of a balanced fence must not be read as a new opener.
        "fence-closer-is-not-reopened-to-swallow-boundary",
        "### First item with closed fence\n```markdown\n### Payload heading inside fence\n```\n### Second item must remain a boundary\nSecond body.\n```\n",
        &[
            (
                "First item with closed fence",
                "```markdown\n### Payload heading inside fence\n```",
                "",
                "",
                "",
                false,
            ),
            (
                "Second item must remain a boundary",
                "Second body.\n```",
                "",
                "",
                "",
                false,
            ),
        ],
    ),
    (
        // #8455: generic boundaries own one blank separator line, so inner
        // and EOF-final items preserve the same body bytes.
        "generic-boundaries-own-one-separator-newline",
        "### First generic item\nshared body\n\n### Inner generic item\nshared body\n\n### Final generic item\nshared body",
        &[
            ("First generic item", "shared body", "", "", "", false),
            ("Inner generic item", "shared body", "", "", "", false),
            ("Final generic item", "shared body", "", "", "", false),
        ],
    ),
    (
        // #8455: do not trim all trailing blank lines when one belongs to the
        // generic boundary.
        "generic-boundaries-retain-extra-blank-lines",
        "### First generic item\nshared body\n\n\n### Final generic item\nshared body",
        &[
            ("First generic item", "shared body\n", "", "", "", false),
            ("Final generic item", "shared body", "", "", "", false),
        ],
    ),
];

fn expect(entry: &(&str, &str, &str, &str, &str, bool)) -> ParsedItem {
    ParsedItem {
        title: entry.0.to_owned(),
        body: entry.1.to_owned(),
        reviewer: entry.2.to_owned(),
        vote: entry.3.to_owned(),
        phase: entry.4.to_owned(),
        malformed: entry.5,
    }
}

#[test]
fn the_parser_reproduces_every_pinned_python_case() {
    for (name, input, expected) in PARSE_CASES {
        let parsed = parse_issue_input(input);
        let wanted: Vec<ParsedItem> = expected.iter().map(expect).collect();
        assert_eq!(parsed.items, wanted, "{name}");
    }
}

#[test]
fn one_oos_heading_makes_the_whole_parse_oos() {
    assert_eq!(parse_issue_input("").mode, InputMode::Generic);
    assert_eq!(
        parse_issue_input("### Plain\nbody\n").mode,
        InputMode::Generic
    );
    // The mode latches: a generic item after an OOS block does not reset it.
    let mixed = parse_issue_input("### OOS_1: a\n- **Description**: b\n### Plain\nbody\n");
    assert_eq!(mixed.mode, InputMode::Oos);
    assert_eq!(mixed.mode.as_str(), "oos");
    assert_eq!(InputMode::Generic.as_str(), "generic");
}

#[test]
fn text_before_the_first_heading_is_discarded() {
    // Nothing is in body capture yet, so a preamble belongs to no item.
    let parsed = parse_issue_input("preamble\n- **Description**: not a field yet\n### T\nbody\n");
    assert_eq!(parsed.items.len(), 1);
    assert_eq!(parsed.items[0].title, "T");
    assert_eq!(parsed.items[0].body, "body");
}

#[test]
fn a_heading_needs_the_exact_three_hash_and_space_spelling() {
    // Deeper headings and a bare `###` are body text, which is what lets an
    // author use `####` for subsections inside a generic body.
    let parsed = parse_issue_input("### T\n#### Sub\n###\n##### Deeper\n");
    assert_eq!(parsed.items.len(), 1);
    assert_eq!(parsed.items[0].body, "#### Sub\n###\n##### Deeper");
}

#[test]
fn a_reviewer_field_ends_body_capture_until_the_next_body_field() {
    // `Reviewer`, `Vote tally`, and `Phase` are metadata, so trailing prose
    // after them is dropped rather than appended to the body.
    let parsed = parse_issue_input(
        "### OOS_1: t\n- **Description**: body\n- **Phase**: review\ntrailing prose\n",
    );
    assert_eq!(parsed.items[0].body, "body");
    assert_eq!(parsed.items[0].phase, "review");
}

#[test]
fn a_concern_extends_a_body_a_description_replaces_it() {
    let extended = parse_issue_input("### OOS_1: t\nprose\n- **Concern**: added\n");
    assert_eq!(extended.items[0].body, "prose\nadded");
    let replaced = parse_issue_input("### OOS_1: t\nprose\n- **Description**: only\n");
    assert_eq!(replaced.items[0].body, "only");
    // An empty `Concern` after existing body text adds no blank line.
    let empty = parse_issue_input("### OOS_1: t\nprose\n- **Concern**:\n");
    assert_eq!(empty.items[0].body, "prose");
}

#[test]
fn the_allocator_reproduces_every_pinned_python_case() {
    // Union credit: item 2's nomination of 10 is credited without re-adding it.
    assert_eq!(
        allocate_candidates(
            2,
            "CAND 1 10 dup high\nCAND 1 11 dup medium\nCAND 2 10 dup low\nCAND 2 12 dep high"
        )
        .candidates,
        vec![10, 11, 12]
    );
    // N=30 gives every item exactly one slot.
    let thirty = (1..=30).fold(String::new(), |mut rows, item| {
        let _ = writeln!(rows, "CAND {item} {} dup high", item * 100);
        rows
    });
    assert_eq!(
        allocate_candidates(30, &thirty).candidates,
        (1..=30).map(|item| item * 100).collect::<Vec<u64>>()
    );
    // `both` is first class, and one candidate shared by two items is one slot.
    assert_eq!(
        allocate_candidates(2, "CAND 1 100 both high\nCAND 2 100 both medium\n").candidates,
        vec![100]
    );
    // A missing confidence reads as `low`, and an unknown kind is still counted.
    assert_eq!(
        allocate_candidates(1, "CAND 1 100 dup\nCAND 1 101 dup high\n").candidates,
        vec![100, 101]
    );
    assert_eq!(
        allocate_candidates(1, "CAND 1 100 unknown high\nCAND 1 101 weird medium\n").candidates,
        vec![100, 101]
    );
    // Equal confidence within one item breaks ties by ascending issue number.
    assert_eq!(
        allocate_candidates(
            10,
            "CAND 1 105 dup medium\nCAND 1 102 dup medium\nCAND 1 101 dup medium\nCAND 1 104 dup medium\nCAND 1 103 dup medium\n"
        )
        .candidates,
        vec![101, 102, 103, 104, 105]
    );
    assert!(
        allocate_candidates(0, "CAND 1 100 dup high\n")
            .candidates
            .is_empty()
    );
    assert!(allocate_candidates(5, "").candidates.is_empty());
}

#[test]
fn the_floor_shrinks_as_the_batch_grows_and_spillover_fills_the_rest() {
    // N=11 reserves two per item (11 x 3 would exceed the cap), then Pass B
    // fills the last eight slots by confidence and issue order.
    let eleven = (1..=11).fold(String::new(), |mut rows, item| {
        let base = item * 100;
        let _ = writeln!(
            rows,
            "CAND {item} {base} dup high\nCAND {item} {} dup high\nCAND {item} {} dup medium",
            base + 1,
            base + 2
        );
        rows
    });
    let expected: Vec<u64> = "100,101,102,200,201,202,300,301,302,400,401,402,500,501,502,600,601,602,700,701,702,800,801,802,900,901,1000,1001,1100,1101"
        .split(',')
        .map(|value| value.parse().expect("pinned issue number"))
        .collect();
    assert_eq!(allocate_candidates(11, &eleven).candidates, expected);

    // N=16 reserves one per item and spills the remaining fourteen.
    let sixteen = (1..=16).fold(String::new(), |mut rows, item| {
        let base = item * 100;
        let _ = writeln!(
            rows,
            "CAND {item} {base} dup high\nCAND {item} {} dup high",
            base + 1
        );
        rows
    });
    let expected: Vec<u64> = "100,101,200,201,300,301,400,401,500,501,600,601,700,701,800,801,900,901,1000,1001,1100,1101,1200,1201,1300,1301,1400,1401,1500,1600"
        .split(',')
        .map(|value| value.parse().expect("pinned issue number"))
        .collect();
    assert_eq!(allocate_candidates(16, &sixteen).candidates, expected);
}

#[test]
fn above_the_cap_the_floor_vanishes_and_ranking_decides() {
    let rows = (1..=15).fold(String::new(), |mut rows, item| {
        let base = item * 100;
        let _ = writeln!(
            rows,
            "CAND {item} {base} dup high\nCAND {item} {} dup medium\nCAND {item} {} dup low",
            base + 50,
            base + 75
        );
        rows
    });
    let expected: Vec<u64> = (1..=15)
        .flat_map(|item| [item * 100, item * 100 + 50])
        .collect();
    assert_eq!(allocate_candidates(31, &rows).candidates, expected);

    // The cap holds however many rows survive.
    let flood = (1..=5)
        .flat_map(|item| (0..10).map(move |offset| (item, item * 1000 + offset)))
        .fold(String::new(), |mut rows, (item, issue)| {
            let _ = writeln!(rows, "CAND {item} {issue} dup high");
            rows
        });
    assert_eq!(allocate_candidates(5, &flood).candidates.len(), 30);
}

#[test]
fn every_rejected_row_is_reported_with_its_reason() {
    let allocation = allocate_candidates(
        2,
        "noise\nCAND 1 10\nCAND x 10 dup\nCAND 9 10 dup\nCAND 1 0 dup\nCAND 1 abc dup\nCAND\tno-space 1 dup\n",
    );
    let defects: Vec<CandidateRowDefect> = allocation
        .dropped
        .iter()
        .map(|dropped| dropped.defect)
        .collect();
    assert_eq!(
        defects,
        vec![
            CandidateRowDefect::TooFewFields,
            CandidateRowDefect::NonNumericItem,
            CandidateRowDefect::ItemOutOfRange { item: 9, total: 2 },
            CandidateRowDefect::NonPositiveIssue,
            CandidateRowDefect::NonPositiveIssue,
        ]
    );
    assert!(allocation.candidates.is_empty());
    // The diagnostic echoes the row exactly as it arrived, before trimming.
    assert_eq!(
        allocation.dropped[0].message(),
        "**⚠ /issue: dropped malformed CAND row (too few fields): CAND 1 10**"
    );
    assert_eq!(
        allocation.dropped[2].message(),
        "**⚠ /issue: dropped malformed CAND row (item index 9 out of range 1..2): CAND 9 10 dup**"
    );
}

#[test]
fn archival_titles_are_recognized_however_they_are_cased_or_indented() {
    for title in [
        "Research the thing",
        "  research the thing",
        "[Research] the thing",
        "INVESTIGATE the thing",
        "[investigate] the thing",
        "[Audit Report] findings",
        "[report] findings",
    ] {
        assert!(title_is_archival(title), "{title}");
    }
    for title in [
        "Researching the thing",
        "[BUG] research is broken",
        "report without a bracket",
        "[report]no space",
        "",
    ] {
        assert!(!title_is_archival(title), "{title}");
    }
}
