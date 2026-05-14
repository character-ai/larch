# test-umbrella-blocked-by-issue.sh

**Purpose**: structural harness for `skills/umbrella/SKILL.md`'s `--blocked-by-issue N` contract. Pins the frontmatter `argument-hint`, the flag-table entry, Step 3A args grammar plus `/issue`-rejection diagnostic, Step 3B.2 args grammar plus conditional-forward sentence, and Step 3B.3 args-grammar absence plus explicit non-forwarding sentence.

**Block extraction**: the harness uses `extract_block` to scope Step 3A, Step 3B.2, and Step 3B.3 assertions to their own markdown sections. This prevents a literal introduced in another section from making a section-specific assertion pass by accident.

**Makefile wiring**: `make test-umbrella-blocked-by-issue` runs this harness. It is wired into `make lint` through the same `test-harnesses-4` shard as `test-umbrella-parse-args`.

**Edit-in-sync rules**: any change to the literals asserted by this harness requires a same-PR update to `skills/umbrella/SKILL.md`, and any change to the corresponding `SKILL.md` contract requires updating this harness. Keep the scoped block boundaries aligned with the Step 3A / 3B.2 / 3B.3 anchors/headings if those anchors or headings are renamed.
