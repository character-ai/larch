# render-assessor-prompt.sh

Renders assessor prompt with inlined plans and `ASSESSMENT:` / `REASONING:` / `QUALIFICATIONS:` grammar (distinct from voter `FINDING_N` lines).

The feature file is untrusted scope evidence, whether it is the staged plan-review scope anchor or a legacy `feature-description.txt` fallback. It is redacted, XML-escaped, and wrapped in a literal evidence block with framing that forbids treating embedded text as prompt instructions.
