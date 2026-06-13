## Review Phase Detail

| Round | Suggestions | Accepted | OOS proposed | OOS accepted | Time | Cost | Reviewers |
|--:|--:|--:|--:|--:|:--|--:|--:|
| 1 | 4 | 3 | 0 | 0 | 14m 58s | $3.76 | 12 |
| 2 | 4 | 3 | 1 | 0 | 11m 50s | $3.37 | 5 |
| 3 | 2 | 2 | 0 | 0 | 12m 14s | $3.97 | 5 |
| 4 | 6 | 4 | 1 | 0 | 11m 38s | $3.45 | 5 |
| 5 | 2 | 1 | 0 | 0 | 10m 04s | $2.77 | 5 |
| **Total** | **18** | **13** | **2** | **0** | **1h 00m 44s** | **$17.32** | **32** |

### Round 1 reviewer timing

```
Round 1 reviewer timing  ·  window 0:00-14:58 (898s)
                                            0:00                                               14:58
                                           ┌────────────────────────────────────────────────────────┐
cursor/cursor-plan-innovation              │███████                                                 │ 116s
cursor/cursor-plan-pragmatic               │█████████                                               │ 139s
cursor/dyn-cursor-plan-ship-pr-fail-closed │█████████                                               │ 143s
cursor/cursor-plan-arch                    │██████████                                              │ 157s
cursor/dyn-cursor-plan-same-path-scout     │██████████                                              │ 162s
codex/dyn-codex-plan-ship-pr-fail-closed   │██████████                                              │ 163s
codex/codex-plan-innovation                │████████████                                            │ 186s
codex/dyn-codex-plan-same-path-scout       │████████████                                            │ 193s
codex/codex-plan-arch                      │████████████                                            │ 194s
codex/codex-plan-requirements              │████████                                                │ 126s
cursor/cursor-plan-requirements            │█████████                                               │ 142s
codex/codex-plan-pragmatic                 │██████████                                              │ 158s
cursor/plan-requirements                   │             ███████                                    │ 101s
unknown/aggregator                         │                       ███                              │  49s
codex/vote                                 │                          █████                         │  69s
cursor/vote                                │                          █████                         │  78s
claude/vote                                │                          ██████████████████████████    │ 406s
unknown/codex                              │                                                    ████│  56s
                                           └────────────────────────────────────────────────────────┘
```

### Round 2 reviewer timing

```
Round 2 reviewer timing  ·  window 0:00-11:50 (710s)
                                 0:00                                               11:50
                                ┌────────────────────────────────────────────────────────┐
cursor/cursor-plan-pragmatic    │████████                                                │ 101s
cursor/cursor-plan-requirements │██████████                                              │ 124s
cursor/cursor-plan-arch         │███████████                                             │ 141s
cursor/cursor-plan-innovation   │███████████                                             │ 141s
codex/codex-plan-generic        │██████████████████                                      │ 224s
unknown/aggregator              │                   ███                                  │  37s
cursor/vote                     │                      ███                               │  46s
codex/vote                      │                      █████                             │  65s
claude/vote                     │                      ██████████████████████            │ 286s
unknown/codex                   │                                             ███████████│ 134s
                                └────────────────────────────────────────────────────────┘
```

### Round 3 reviewer timing

```
Round 3 reviewer timing  ·  window 0:00-12:14 (734s)
                                 0:00                                               12:14
                                ┌────────────────────────────────────────────────────────┐
cursor/cursor-plan-requirements │███████                                                 │  85s
cursor/cursor-plan-innovation   │███████████                                             │ 149s
cursor/cursor-plan-arch         │████████████                                            │ 152s
cursor/cursor-plan-pragmatic    │████████████                                            │ 157s
codex/codex-plan-generic        │██████████████████                                      │ 238s
unknown/aggregator              │                   ██                                   │  28s
cursor/vote                     │                     ███                                │  41s
codex/vote                      │                     ████                               │  47s
claude/vote                     │                     ███████████████████████████████    │ 401s
unknown/codex                   │                                                    ████│  48s
                                └────────────────────────────────────────────────────────┘
```

### Round 4 reviewer timing

```
Round 4 reviewer timing  ·  window 0:00-11:38 (698s)
                                 0:00                                               11:38
                                ┌────────────────────────────────────────────────────────┐
cursor/cursor-plan-innovation   │███████████                                             │ 131s
cursor/cursor-plan-pragmatic    │███████████                                             │ 134s
cursor/cursor-plan-arch         │███████████                                             │ 139s
cursor/cursor-plan-requirements │█████████████████                                       │ 217s
codex/codex-plan-generic        │████████████████████                                    │ 246s
unknown/aggregator              │                     ███                                │  38s
cursor/vote                     │                        ██████                          │  70s
codex/vote                      │                        █████████████                   │ 158s
claude/vote                     │                        ███████████████████████████     │ 337s
unknown/codex                   │                                                    ████│  44s
                                └────────────────────────────────────────────────────────┘
```

### Round 5 reviewer timing

```
Round 5 reviewer timing  ·  window 0:00-10:04 (604s)
                                 0:00                                               10:04
                                ┌────────────────────────────────────────────────────────┐
cursor/cursor-plan-arch         │████████████████                                        │ 175s
cursor/cursor-plan-requirements │██████████                                              │ 106s
cursor/cursor-plan-innovation   │███████████████                                         │ 160s
cursor/cursor-plan-pragmatic    │█████████████████████                                   │ 219s
codex/codex-plan-generic        │███████████████████████                                 │ 248s
unknown/aggregator              │                        ██                              │  22s
cursor/vote                     │                          ██████                        │  67s
codex/vote                      │                          ███████████                   │ 116s
claude/vote                     │                          ████████████████████████      │ 261s
unknown/codex                   │                                                   █████│  51s
                                └────────────────────────────────────────────────────────┘
```

**Top reviewers** (by suggestions accepted, whole run):
- (no accepted suggestions attributed to a reviewer slot)

**Reviewer slot failures**: 1
- unknown/collector-failure-1: 1

_Cost is the per-round vendor cost (Codex + Cursor + Claude subprocess), attributed by token-ledger timestamp window; it excludes main-agent Claude, so it is less than the run Cost line above. Rendered as an em dash when per-round timing or the token ledger is unavailable._
