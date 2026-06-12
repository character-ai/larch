## Goal
Implement issue #4109: [IMPLEMENTING] 1. in /implement and /design, Codex reviewers, currently spawned on first 2….

## Implementation Plan
1. in /implement and /design, Codex reviewers, currently spawned on first 2 review rounds, should only spawn on first round.  Starting with 2nd round and on through the rest of the rounds (up to 5), 1 generic Codex reviewer should be spawned.  It is, however, subject to same weed-out policy of "no tangible suggestions produced on last 2 rounds -- you are out).  On round 5, instead of spawning all specialized Codex reviewers, just 1 generic Codex reviewer should be spawned (in total, so for round 5 exactly 1 Codex generic reviewer is spawned, in addition to all the Cursor specialists).  2. In /implement, replace Codex with Cursor as default agent to apply review suggestions, and do same to aggregator/deduplicator of review suggestions.

## Test plan
(no test plan section in plan-file)
