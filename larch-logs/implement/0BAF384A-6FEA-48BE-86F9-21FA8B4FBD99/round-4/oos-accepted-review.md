### OOS_4: [OUT_OF_SCOPE] Upgrade prune can run outside cache-shaped roots
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `upgrade_larch.py` can prune sibling cache version directories when the plugin root is not cache-shaped, such as dev `--plugin-dir` usage on an already-latest path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


