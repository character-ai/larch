### FINDING_2: Structural pins require ≥3 wrapper fences but plan only defines two invoke sites
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-stdio-routing
- **Severity**: important
- **Concern**: Proposed structure-test pins (plan / `scripts/test-implement-structure.sh` around the wrapper-fence checks; plan also references `skills/implement/SKILL.md` Step 0 / dirty-tree prose) require **≥3** `set +e` / `_inv_rc` wrapper fences, while the planned SKILL edit only has **two** executable wrapper call sites: Step 0 `--mode initial` and dirty-tree recovery `--mode resume` (no separate Step 0 resume bash block). Scenario: `make test-implement-structure` fails after a correct implementation, or the implementer adds a phantom third fence/call site only to satisfy CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Retarget pins to ≥2 sites matching implement-bootstrap-invoke.sh --mode initial and --mode resume only; drop the ≥3 requirement
  - From Cursor-dyn-stdio-routing: Align pins and prose to two sites: initial Step 0 + dirty-tree `--mode resume`; change `≥3` to `≥2` (or drop the third-site requirement) and replace “all three call sites” with “both wrapper call sites”

---

**Merge notes (for voters, not machine fields):** No `[OUT_OF_SCOPE]` inputs; no `### OOS_N:` blocks. Severity on FINDING_1 uses **important** (Cursor-Innovation) over **latent** (Cursor-Edge). Do not emit `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` because two merged finding blocks are present.

