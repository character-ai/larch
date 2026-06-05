### OOS_1:
- **Description**: Plan changes design-pause-load.sh to rm restored .pause-requested but does not update the sibling contract doc. Scenario: Future readers of design-pause-load.md will miss the post-restore clear behavior and may reintroduce the immediate re-pause loop
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/design-pause-load.md:14-40
- **Phase**: design

