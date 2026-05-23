### [Plan Review] FINDING_10

### FINDING_10: Marker-only lint cannot catch contradictory `run_in_background: true` co-occurrence
- **Concern (latent)**: A future SKILL.md edit could add the canonical banner + inline comment near a Family B basename AND still use `run_in_background: true` in the Bash tool metadata (or `&` shell backgrounding in the fence). Markdown-only lint cannot inspect Bash tool metadata; the invariant could be violated while the lint stays green.
- **Suggested resolution**: Optional — extend the lint to additionally reject same-fence co-occurrence of a denylisted basename with `& ` or `nohup` patterns inside the fence. Bash tool metadata is out of scope (not in `.md` files). Add fixtures for the negative case.
- **Reviewers**: Codex-Edge (1 of 10, latent severity).


