Two minor advisory deviations; neither blocks the plan.

- G-Cfg-1 (define wire-literals once; aggregate rather than re-list): the plan adds one shared fileable-predicate helper in voting.py (good), but the severity-string sets remain re-listed across `_ALLOWED_SEVERITIES` (research_eval), `_STRUCTURED_GATE_B_SEVERITIES` (plan_review_gate_b), `HIGH_SEVERITIES` (voting), and `_AGGREGATE_HIGH_SEVERITIES` (design_oos), each repointed independently. Where the review/research domain boundary allows, prefer deriving the unified set from the JudgeSeverity enum to avoid future drift.
- G-Py-8 (re-verify security-critical postcondition): the security-drop partition (drops routed away from the public oos-dropped-before-vote.md) is security-bearing; the implementer should re-verify the public audit contains no security-tagged block after writing.

Otherwise conforms: keeps the JudgeSeverity StrEnum domain type (G-Py-3/G-Py-1), the silent nit-drop is a documented degraded path with an audit lineage (G-Py-4 carve-out), and prompt-invariant/validator tests add mechanical enforcement (G-Enf-1).
