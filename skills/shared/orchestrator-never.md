# Orchestrator NEVER List

Cross-skill anti-pattern rules for all single-iteration larch orchestrators. Load once per session via the MANDATORY directive in each skill's SKILL.md.

1. **NEVER improvise ScheduleWakeup outside skill-script direction.** **Why**: single-iteration skills end at their terminal cleanup step. The orchestrator calling `ScheduleWakeup` on its own initiative, or narrating "next iteration" / "loop sleeping until ..." prose, is improvisation outside the skill's steps. Recurring behavior is owned exclusively by `/loop`'s `<<autonomous-loop-dynamic>>` sentinel mechanism — never by orchestrator improvisation in a child skill's terminal turn. **How to apply**: do not call `ScheduleWakeup` from any skill that does not have a numbered step directing the call. See AGENTS.md for the project-wide rule. **CI-backed**: yes — `scripts/test-anti-improvised-wakeup.sh` pins the literal at this site.
