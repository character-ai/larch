### OOS_2: Specialist payload accounting omits inlined competition notice
- **Description**: Specialist payload accounting omits inlined competition notice. Scenario: `render specialist` inlines `competition_notice_file` content when `--competition-notice` is set, but the plan’s payload helpers only name description/plan/feature text. Implement review rounds with competition notices will show inflated scaffold in `measure-panel-cost` rankings.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:883-890
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/6176
