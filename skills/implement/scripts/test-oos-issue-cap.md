# skills/implement/scripts/test-oos-issue-cap.sh — contract

`test-oos-issue-cap.sh` is the fixture-driven regression harness for
`skills/implement/scripts/oos-issue-cap.sh`. It exercises the helper's cap,
pass-through, in-place rewrite, failure cleanup, malformed item, UTF-8
truncation, markdown normalization, file-reference preservation, and structural
warning-string consistency behavior. The authoritative runtime contract lives
in `skills/implement/scripts/oos-issue-cap.md`.
