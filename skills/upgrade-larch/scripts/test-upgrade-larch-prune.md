# test-upgrade-larch-prune.sh

Standalone regression harness for `/upgrade-larch` install-stamp cache pruning (max 8 retained).

The harness runs `skills/upgrade-larch/scripts/upgrade-larch.sh` end-to-end in a temporary home with stubbed `claude`, `gh`, `rm`, and `stat` binaries. It seeds `.larch-installed-at` stamps and optional directory mtimes, then asserts the retained set matches install-stamp ordering (stamped before unstamped, then timestamp descending, then version basename).

Covered cases:

- over-eight-stamped-keeps-eight-newest: more than eight stamped dirs keeps exactly the eight newest stamps
- under-cap-keeps-all: fewer than eight cached dirs keeps all
- install-stamp-ordering: stamp timestamps determine retention order
- stamp-beats-unstamped-mtime: a stamped dir outranks an un-stamped dir with a newer directory mtime
- mtime-fallback-unstamped: un-stamped dirs fall back to directory mtime for ordering
- just-installed-seeded: the verified install target is retained even when its pre-install stamp would sort outside the cap
- install-then-prune-fills-eight: a successful install still prunes back to exactly eight cached dirs
- absent-target-cache-dir-fills-eight: a missing install-target cache dir does not consume a retention slot
- stamp-write-failure-existing-target: a failed target stamp write still retains the seeded existing target dir
- target-in-top-eight-exact-count: when the install target is already among the newest eight, exactly eight dirs remain (no off-by-one to nine)
- already-latest-prunes: idempotent already-latest path binds the installed version, refreshes its stamp, and prunes without reinstalling
- legacy-unstamped-backfilled-before-prune: legacy dirs without `.larch-installed-at` are backfilled from directory mtime before prune ordering
- stat-backfill-skipped-still-prunes: when `stat` fails for a legacy dir during backfill (`STAT_FAIL_VERSION` stub), that dir is not stamped, other legacy dirs are still backfilled, and prune completes at eight dirs

Edit in sync: update this harness, `upgrade-larch.sh`, `upgrade-larch.md`, `skills/upgrade-larch/SKILL.md`, `docs/installation-and-setup.md`, and `Makefile` when changing install-stamp pruning behavior or validation commands.
