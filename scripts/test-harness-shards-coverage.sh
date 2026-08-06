#!/usr/bin/env bash
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MAKEFILE="$REPO_ROOT/Makefile"

usage() {
  printf 'Usage: %s [--self-test]\n' "$(basename "$0")" >&2
}

cleanup_tmpdir() {
  if [[ -n "${TMPDIR_SLICES:-}" && -d "$TMPDIR_SLICES" ]]; then
    rm -rf "$TMPDIR_SLICES"
  fi
}

make_tmpdir() {
  TMPDIR_SLICES="$(mktemp -d "${TMPDIR:-/tmp}/test-harness-shards-coverage.XXXXXX")"
  trap cleanup_tmpdir EXIT
}

append_section() {
  local title="$1"
  local prefix="$2"
  local file="$3"

  if [[ -s "$file" ]]; then
    {
      printf '@@ %s @@\n' "$title"
      while IFS= read -r line; do
        printf '%s %s\n' "$prefix" "$line"
      done < "$file"
    } >> "$REPORT"
  fi
}

# Single source of truth for documented standalone carve-outs (test-* recipe
# targets that are deliberately NOT part of the test-harnesses aggregate). When
# adding another standalone carve-out, append it to this list AND update the
# Makefile comments near that target AND scripts/test-harness-shards-coverage.md.
# The carve-out list is consumed by every awk program in this script via the
# CARVE_OUTS environment variable; do NOT hardcode names in additional awk
# blocks.
CARVE_OUTS="test-bgjob test-eval-set-structure test-eval-research-baseline-flag test-review-and-fix test-stall-recovery-report test-lib-design-tmpdir test-classify-bump test-promote-release test-release-prepare test-release-set-version test-compose-collector-failure-log test-wait-for-reviewers test-classify-diff-mode test-gather-branch-context"

# Awk snippet (used as -v CARVE=... -v COVERAGE=... and a BEGIN block) that
# returns 1 from is_carve_out(name) for any name matching the aggregate, the
# shard targets, the coverage harness itself, or any documented carve-out.
# Embedded as a string so each awk block can splice it in.
CARVE_OUT_FN='
  function is_carve_out(name,   i, n, parts) {
    if (name ~ /^test-harnesses(-[0-9]+)?$/) return 1
    if (name == COVERAGE) return 1
    n = split(CARVE, parts, " ")
    for (i = 1; i <= n; i++) {
      if (parts[i] != "" && name == parts[i]) return 1
    }
    return 0
  }
'

# Unified direct-Bash-leaf inventory:
# - recipe-bearing test-* targets whose complete recipe is Bash-harness work
#   (no pytest invocation)
# - recipe-bearing *-bash-harness leaves (including non-test-* names)
# Excludes recipe-less aggregates, direct pytest recipes, and mixed recipes
# that contain any pytest invocation. Shard members must be inventory leaves.
extract_individual_targets() {
  local makefile="$1"

  awk -F: -v CARVE="$CARVE_OUTS" -v COVERAGE="test-harness-shards-coverage" "
    $CARVE_OUT_FN
    function is_inventory_candidate(name) {
      if (name ~ /^test/) return 1
      if (name ~ /-bash-harness\$/) return 1
      return 0
    }
    function flush(   keep) {
      if (cur == \"\") return
      keep = 0
      if (has_recipe && !cur_is_pytest && is_inventory_candidate(cur) && !is_carve_out(cur)) {
        keep = 1
      }
      if (keep) print cur
      cur = \"\"
      cur_is_pytest = 0
      has_recipe = 0
    }
    BEGIN { cur = \"\"; cur_is_pytest = 0; has_recipe = 0 }
    /^[[:space:]]*#/ { next }
    /^[^[:space:]#][^:]*:/ {
      flush()
      name = \$1
      if (is_inventory_candidate(name) && !is_carve_out(name)) cur = name
      next
    }
    /^\t/ {
      if (cur != \"\") {
        has_recipe = 1
        if (/pytest/) cur_is_pytest = 1
      }
      next
    }
    { flush() }
    END { flush() }
  " "$makefile" | sort -u
}

# Classify makefile targets for shard-member rejection: aggregate (recipe-less),
# pytest (recipe contains pytest), or unknown (not declared).
extract_nonleaf_classifications() {
  local makefile="$1"
  local out="$2"

  awk -F: "
    function flush() {
      if (cur == \"\") return
      if (!has_recipe) kind[cur] = \"aggregate\"
      else if (cur_is_pytest) kind[cur] = \"pytest\"
      else kind[cur] = \"leaf\"
      cur = \"\"
      cur_is_pytest = 0
      has_recipe = 0
    }
    BEGIN { cur = \"\"; cur_is_pytest = 0; has_recipe = 0 }
    /^[[:space:]]*#/ { next }
    /^[^[:space:]#][^:]*:/ {
      flush()
      cur = \$1
      next
    }
    /^\t/ {
      if (cur != \"\") {
        has_recipe = 1
        if (/pytest/) cur_is_pytest = 1
      }
      next
    }
    { flush() }
    END {
      flush()
      for (name in kind) print name \"\\t\" kind[name]
    }
  " "$makefile" | sort > "$out"
}

extract_shard_prereqs() {
  local makefile="$1"
  local out_all="$2"
  local out_expected_shards="${3:-}"
  local n
  local count
  local line
  local prereq
  local first_prereq
  local contains_guard
  local discovered_shards
  discovered_shards="$(grep -Eo '^test-harnesses-[0-9]+:' "$makefile" | awk '{ sub(/^test-harnesses-/, ""); sub(/:$/, ""); print }' | sort -nu)"

  : > "$out_all"
  if [[ -n "$out_expected_shards" ]]; then
    : > "$out_expected_shards"
  fi
  GUARD_SLICE_NAME=""
  GUARD_SLICE_FIRST=""
  GUARD_SLICE_COUNT=0

  if [[ -z "$discovered_shards" ]]; then
    printf 'no test-harnesses-N rules declared in Makefile\n' >> "$MISSING_SLICE_RULES"
    return
  fi

  for n in $discovered_shards; do
    if [[ -n "$out_expected_shards" ]]; then
      printf 'test-harnesses-%s\n' "$n" >> "$out_expected_shards"
    fi
  done

  for n in $discovered_shards; do
    count="$(grep -Ec "^test-harnesses-$n:" "$makefile" || true)"
    if [[ "$count" != "1" ]]; then
      printf 'test-harnesses-%s must be declared exactly once (found %s)\n' "$n" "$count" >> "$MISSING_SLICE_RULES"
      continue
    fi

    line="$(grep -E "^test-harnesses-$n:" "$makefile")"
    line="${line#*:}"
    first_prereq=""
    contains_guard=0
    for prereq in $line; do
      if [[ -z "$first_prereq" ]]; then
        first_prereq="$prereq"
      fi
      printf '%s\n' "$prereq" >> "$out_all"
      if [[ "$prereq" == "test-harness-shards-coverage" ]]; then
        contains_guard=1
      fi
    done

    if (( contains_guard )); then
      GUARD_SLICE_COUNT=$((GUARD_SLICE_COUNT + 1))
      if [[ -z "$GUARD_SLICE_NAME" ]]; then
        GUARD_SLICE_NAME="test-harnesses-$n"
        GUARD_SLICE_FIRST="$first_prereq"
      fi
    fi
  done
}

extract_test_harnesses_prereqs() {
  local makefile="$1"
  local out="$2"
  local count
  local line
  local prereq

  : > "$out"
  count="$(grep -Ec '^test-harnesses:' "$makefile" || true)"
  if [[ "$count" != "1" ]]; then
    printf 'test-harnesses aggregate must be declared exactly once (found %s)\n' "$count" >> "$ROLLUP_DECL_ERRORS"
    return
  fi

  line="$(grep -E '^test-harnesses:' "$makefile")"
  line="${line#*:}"
  for prereq in $line; do
    printf '%s\n' "$prereq" >> "$out"
  done
}

validate_makefile() {
  local makefile="$1"

  REPORT="$TMPDIR_SLICES/report"
  MISSING_SLICE_RULES="$TMPDIR_SLICES/missing-shard-rules"
  ROLLUP_DECL_ERRORS="$TMPDIR_SLICES/rollup-decl-errors"
  : > "$REPORT"
  : > "$MISSING_SLICE_RULES"
  : > "$ROLLUP_DECL_ERRORS"

  local naming_violations="$TMPDIR_SLICES/naming-violations"
  local continuation_violations="$TMPDIR_SLICES/continuation-violations"
  local individual="$TMPDIR_SLICES/individual"
  local slice_all="$TMPDIR_SLICES/slice-all"
  local slice_no_self="$TMPDIR_SLICES/slice-no-self"
  local duplicates="$TMPDIR_SLICES/duplicates"
  local missing="$TMPDIR_SLICES/missing"
  local orphan="$TMPDIR_SLICES/orphan"
  local th_prereqs="$TMPDIR_SLICES/th-prereqs-actual"
  local th_prereqs_expected="$TMPDIR_SLICES/th-prereqs-expected"
  local th_prereqs_missing="$TMPDIR_SLICES/th-prereqs-missing"
  local th_prereqs_extra="$TMPDIR_SLICES/th-prereqs-extra"
  local phony="$TMPDIR_SLICES/phony"
  local phony_missing="$TMPDIR_SLICES/phony-missing"

  # Naming violation = any test-prefixed inventory candidate whose full name does
  # not match ^test-[a-z0-9-]+$. Carve-outs (aggregate roll-up, shards, coverage,
  # standalone evals) are excluded. Non-test-* Bash leaves (e.g. *-bash-harness)
  # are not subject to the test-* naming convention.
  awk -v CARVE="$CARVE_OUTS" -v COVERAGE="test-harness-shards-coverage" "
    $CARVE_OUT_FN
    /^test[^[:space:]:]*:/ {
      colon = index(\$0, \":\")
      name = substr(\$0, 1, colon - 1)
      if (is_carve_out(name)) next
      if (name !~ /^test-[a-z0-9-]+\$/) {
        printf \"%d:%s\n\", NR, \$0
      }
    }
  " "$makefile" > "$naming_violations" || true
  # Match any numeric shard, mirroring extract_shard_prereqs's dynamic
  # discovery — leaving this hardcoded to [1-5] would silently allow a
  # backslash continuation on test-harnesses-6 (or any future shard) to
  # bypass the single-physical-line invariant.
  grep -nE "^test-harnesses-[0-9]+:.*\\\\" "$makefile" > "$continuation_violations" || true

  extract_individual_targets "$makefile" > "$individual"
  extract_shard_prereqs "$makefile" "$slice_all" "$th_prereqs_expected"

  local nonleaf_kinds="$TMPDIR_SLICES/nonleaf-kinds"
  local nonleaf_in_shards="$TMPDIR_SLICES/nonleaf-in-shards"
  extract_nonleaf_classifications "$makefile" "$nonleaf_kinds"
  : > "$nonleaf_in_shards"
  while IFS= read -r prereq; do
    [[ -z "$prereq" || "$prereq" == "test-harness-shards-coverage" ]] && continue
    kind="$(awk -F '\t' -v n="$prereq" '$1 == n { print $2; exit }' "$nonleaf_kinds")"
    if [[ -z "$kind" ]]; then
      printf '%s\tunknown\n' "$prereq" >> "$nonleaf_in_shards"
    elif [[ "$kind" == "aggregate" || "$kind" == "pytest" ]]; then
      printf '%s\t%s\n' "$prereq" "$kind" >> "$nonleaf_in_shards"
    fi
  done < "$slice_all"
  sort -u "$nonleaf_in_shards" -o "$nonleaf_in_shards"

  grep -Fxv 'test-harness-shards-coverage' "$slice_all" | sort -u > "$slice_no_self" || true
  sort "$slice_all" | uniq -d > "$duplicates"
  comm -23 "$individual" "$slice_no_self" > "$missing"
  # Orphans = shard members not in the Bash-leaf inventory. Non-leaf
  # classifications (aggregate/pytest/unknown) are reported separately below
  # so a scheduled aggregate is not only an opaque orphan.
  comm -13 "$individual" "$slice_no_self" > "$orphan"
  if [[ -s "$nonleaf_in_shards" ]]; then
    # Drop non-leaf names from the generic orphan list to avoid double-reporting.
    awk -F '\t' '{ print $1 }' "$nonleaf_in_shards" | sort -u > "$TMPDIR_SLICES/nonleaf-names"
    comm -23 "$orphan" "$TMPDIR_SLICES/nonleaf-names" > "$TMPDIR_SLICES/orphan-filtered"
    mv "$TMPDIR_SLICES/orphan-filtered" "$orphan"
  fi

  extract_test_harnesses_prereqs "$makefile" "$th_prereqs"
  # th_prereqs_expected was populated by extract_shard_prereqs above using the
  # set of test-harnesses-N rules actually declared in the Makefile (any N≥1),
  # so the partition guard stays shard-count-agnostic — adding or removing a
  # shard updates the comparison automatically.
  sort -u "$th_prereqs_expected" -o "$th_prereqs_expected"
  sort -u "$th_prereqs" > "$th_prereqs.sorted"
  comm -23 "$th_prereqs_expected" "$th_prereqs.sorted" > "$th_prereqs_missing"
  comm -13 "$th_prereqs_expected" "$th_prereqs.sorted" > "$th_prereqs_extra"

  # .PHONY membership check (R2_F9): every shard-bound inventory leaf must
  # appear in some .PHONY declaration. The Makefile may have multiple .PHONY
  # lines; we union all tokens after the first colon. Continuation lines
  # ending with backslash are folded onto the prior line.
  awk '
    BEGIN { in_phony = 0; buf = "" }
    {
      line = $0
      # Continuation handling: if previous line ended with `\`, append.
      while (sub(/\\$/, "", line) && (getline next_line) > 0) {
        line = line " " next_line
      }
      if (line ~ /^\.PHONY:/) {
        sub(/^\.PHONY:[[:space:]]*/, "", line)
        n = split(line, parts, /[[:space:]]+/)
        for (i = 1; i <= n; i++) {
          if (parts[i] != "") print parts[i]
        }
      }
    }
  ' "$makefile" | sort -u > "$phony"
  # Missing-from-phony = individual − phony. Plus an explicit assertion for
  # `test-harness-shards-coverage` itself, which is excluded from `individual`
  # by the carve-out filter but is still a shard-bound test-* recipe whose
  # `.PHONY` membership matters (without it, a same-named file or directory
  # could shadow the guard target and silently skip the partition check on
  # shard-6).
  comm -23 "$individual" "$phony" > "$phony_missing"
  if ! grep -Fxq 'test-harness-shards-coverage' "$phony"; then
    printf 'test-harness-shards-coverage\n' >> "$phony_missing"
  fi

  append_section "shard rule declaration errors" "!" "$MISSING_SLICE_RULES"
  append_section "harness recipe target uses non-standard naming - convention is lowercase-hyphenated. See scripts/test-harness-shards-coverage.md" "!" "$naming_violations"
  append_section "shard rule must be on a single physical line - see scripts/test-harness-shards-coverage.md" "!" "$continuation_violations"
  append_section "missing from shards" "-" "$missing"
  append_section "orphan in shards" "+" "$orphan"
  if [[ -s "$nonleaf_in_shards" ]]; then
    {
      printf '@@ non-leaf in shards (aggregate, pytest, or unknown) @@\n'
      while IFS=$'\t' read -r name kind; do
        printf '+ %s (%s)\n' "$name" "$kind"
      done < "$nonleaf_in_shards"
    } >> "$REPORT"
  fi
  append_section "duplicate across shards" "!" "$duplicates"
  append_section "test-harnesses aggregate declaration errors" "!" "$ROLLUP_DECL_ERRORS"
  append_section "test-harnesses aggregate missing shard targets" "-" "$th_prereqs_missing"
  append_section "test-harnesses aggregate has unexpected prerequisites" "+" "$th_prereqs_extra"
  append_section "missing from .PHONY" "-" "$phony_missing"

  if ! grep -Fxq 'test-harness-shards-coverage' "$slice_all"; then
    {
      printf '@@ self-reference missing @@\n'
      printf -- '- test-harness-shards-coverage\n'
    } >> "$REPORT"
  fi

  local guard_shard_name="${GUARD_SLICE_NAME:-test-harnesses-N}"
  if [[ "${GUARD_SLICE_COUNT:-0}" == "1" && "${GUARD_SLICE_FIRST:-}" != "test-harness-shards-coverage" ]]; then
    {
      printf '@@ self-reference misplaced @@\n'
      printf '! test-harness-shards-coverage must be the first prerequisite of %s\n' "$guard_shard_name"
    } >> "$REPORT"
  fi

  if [[ -s "$REPORT" ]]; then
    {
      printf 'test-harness-shards-coverage: partition invariant failed\n'
      printf -- '--- expected\n'
      printf -- '+++ actual\n'
      while IFS= read -r line; do
        printf '%s\n' "$line"
      done < "$REPORT"
    } >&2
    return 1
  fi

  return 0
}

write_happy_fixture() {
  local path="$1"

  cat > "$path" <<'EOF'
.PHONY: test-harnesses test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 test-alpha test-beta test-gamma test-delta test-zeta write-final-report-bash-harness test-harness-shards-coverage test-eval-set-structure test-eval-research-baseline-flag eval-research
test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5
test-harnesses-1: test-alpha write-final-report-bash-harness
test-harnesses-2: test-beta
test-harnesses-3: test-gamma
test-harnesses-4: test-delta
test-harnesses-5: test-harness-shards-coverage test-zeta
test-alpha:
	bash scripts/test-alpha.sh
test-beta:
	bash scripts/test-beta.sh
test-gamma:
	bash scripts/test-gamma.sh
test-delta:
	bash scripts/test-delta.sh
test-zeta:
	bash scripts/test-zeta.sh
write-final-report-bash-harness:
	bash scripts/test-write-final-report.sh
test-harness-shards-coverage:
	bash scripts/test-harness-shards-coverage.sh
test-eval-set-structure:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_research_eval.py
test-eval-research-baseline-flag:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_research_eval.py
eval-research:
	python3 python/cli.py eval research
EOF
}

run_self_case() {
  local name="$1"
  local expected_status="$2"
  local expected_stderr="$3"
  local fixture="$TMPDIR_SLICES/$name.mk"
  local stderr_file="$TMPDIR_SLICES/$name.stderr"
  local status=0

  write_happy_fixture "$fixture"

  case "$name" in
    missing-target)
      {
        printf 'test-newthing:\n'
        printf '\tbash scripts/test-newthing.sh\n'
      } >> "$fixture"
      ;;
    orphan-in-shards)
      awk '{ sub(/^test-harnesses-3: test-gamma$/, "test-harnesses-3: test-gamma test-newthing"); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    duplicate-across-shards)
      awk '{ sub(/^test-harnesses-5: test-harness-shards-coverage test-zeta$/, "test-harnesses-5: test-harness-shards-coverage test-zeta test-beta"); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    backslash-continuation-violation)
      awk '{ sub(/^test-harnesses-3: test-gamma$/, "test-harnesses-3: test-gamma \\"); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    naming-convention-violation)
      {
        printf 'test_foo:\n'
        printf '\tbash scripts/test-foo.sh\n'
      } >> "$fixture"
      ;;
    underscore-naming-violation)
      # FINDING_1: `test-foo_bar:` (underscore after first hyphen) used to
      # escape both the inventory parser and the legacy 5th-char naming guard.
      # The widened parsers now catch it as a naming violation AND surface it
      # as missing-from-shards.
      {
        printf 'test-foo_bar:\n'
        printf '\tbash scripts/test-foo-bar.sh\n'
      } >> "$fixture"
      ;;
    self-reference-not-first)
      # FINDING_4 (repurposed): assert failure when test-harness-shards-coverage
      # is not the first prerequisite of the shard that owns the
      # partition-invariant guard. Swap the order so test-zeta comes first.
      awk '{ sub(/^test-harnesses-5: test-harness-shards-coverage test-zeta$/, "test-harnesses-5: test-zeta test-harness-shards-coverage"); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    self-reference-non-last)
      # The guard shard may be followed by later heavy-test shards; it still
      # must remain first within the shard that contains it.
      awk '{ sub(/^test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5$/, "test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 test-harnesses-6"); sub(/^test-harnesses-5: test-harness-shards-coverage test-zeta$/, "test-harnesses-5: test-harness-shards-coverage"); print } END { print "test-harnesses-6: test-zeta" }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    harnesses-aggregate-missing-shard)
      # FINDING_3: assert failure when test-harnesses: does not list every
      # test-harnesses-N. Drop test-harnesses-5 from the aggregate line.
      awk '{ sub(/^test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5$/, "test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4"); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    harnesses-aggregate-extra-shard)
      # FINDING_3: assert failure when test-harnesses: lists an unexpected
      # prerequisite (typo / orphan shard target).
      awk '{ sub(/^test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5$/, "test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 test-harnesses-6"); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    missing-phony)
      # R2_F9: assert failure when a shard-bound test-* target is missing
      # from the .PHONY declaration. Drop test-zeta from .PHONY.
      awk '{ gsub(/ test-zeta /, " "); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    missing-phony-self)
      # R3 (Codex): assert failure when test-harness-shards-coverage itself
      # is missing from .PHONY. The carve-out filter excludes it from the
      # `individual` set, so a separate explicit assertion guards this case.
      awk '{ gsub(/ test-harness-shards-coverage /, " "); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    bash-harness-missing)
      # Unsharded non-test-* Bash leaf must be reported missing.
      awk '{ sub(/^test-harnesses-1: test-alpha write-final-report-bash-harness$/, "test-harnesses-1: test-alpha"); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    bash-harness-orphan-unknown)
      # Unknown non-test-* prerequisite in a shard is rejected as non-leaf.
      awk '{ sub(/^test-harnesses-3: test-gamma$/, "test-harnesses-3: test-gamma mystery-bash-harness"); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    aggregate-in-shard)
      # Recipe-less aggregate combining pytest + Bash must not be a shard leaf.
      {
        printf 'test-write-final-report: write-final-report-py-harness write-final-report-bash-harness\n'
        printf 'write-final-report-py-harness:\n'
        printf '\tpython3 -m pytest -q python/tests/report/test_final_report.py\n'
      } >> "$fixture"
      awk '{ sub(/^test-harnesses-3: test-gamma$/, "test-harnesses-3: test-gamma test-write-final-report"); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    pytest-recipe-in-shard)
      # Direct pytest recipe excluded from inventory and rejected if scheduled.
      {
        printf 'test-only-pytest:\n'
        printf '\tpython3 -m pytest -q python/tests/example.py\n'
      } >> "$fixture"
      awk '{ sub(/^test-harnesses-3: test-gamma$/, "test-harnesses-3: test-gamma test-only-pytest"); gsub(/ test-zeta /, " test-zeta test-only-pytest "); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    mixed-pytest-bash-in-shard)
      # Multi-command recipe containing pytest is not a Bash leaf.
      {
        printf 'test-mixed-lane:\n'
        printf '\tpython3 -m pytest -q python/tests/example.py\n'
        printf '\tbash scripts/test-mixed-lane.sh\n'
      } >> "$fixture"
      awk '{ sub(/^test-harnesses-3: test-gamma$/, "test-harnesses-3: test-gamma test-mixed-lane"); gsub(/ test-zeta /, " test-zeta test-mixed-lane "); print }' "$fixture" > "$fixture.tmp"
      mv "$fixture.tmp" "$fixture"
      ;;
    happy-path)
      ;;
    *)
      printf 'unknown self-test case: %s\n' "$name" >&2
      return 1
      ;;
  esac

  set +e
  validate_makefile "$fixture" > /dev/null 2> "$stderr_file"
  status="$?"
  set -e

  if [[ "$expected_status" == "0" && "$status" != "0" ]]; then
    printf 'self-test %s: expected success, got exit %s\n' "$name" "$status" >&2
    cat "$stderr_file" >&2
    return 1
  fi
  if [[ "$expected_status" != "0" && "$status" == "0" ]]; then
    printf 'self-test %s: expected failure, got success\n' "$name" >&2
    return 1
  fi
  if [[ -n "$expected_stderr" ]] && ! grep -Fq "$expected_stderr" "$stderr_file"; then
    printf 'self-test %s: expected stderr substring not found: %s\n' "$name" "$expected_stderr" >&2
    cat "$stderr_file" >&2
    return 1
  fi
}

self_test() {
  make_tmpdir
  run_self_case happy-path 0 ""
  run_self_case missing-target 1 "missing from shards"
  run_self_case orphan-in-shards 1 "non-leaf in shards"
  run_self_case duplicate-across-shards 1 "duplicate across shards"
  run_self_case backslash-continuation-violation 1 "shard rule must be on a single physical line"
  run_self_case naming-convention-violation 1 "harness recipe target uses non-standard naming"
  run_self_case underscore-naming-violation 1 "harness recipe target uses non-standard naming"
  run_self_case self-reference-not-first 1 "self-reference misplaced"
  run_self_case self-reference-non-last 0 ""
  run_self_case harnesses-aggregate-missing-shard 1 "test-harnesses aggregate missing shard targets"
  run_self_case harnesses-aggregate-extra-shard 1 "test-harnesses aggregate has unexpected prerequisites"
  run_self_case missing-phony 1 "missing from .PHONY"
  run_self_case missing-phony-self 1 "missing from .PHONY"
  run_self_case bash-harness-missing 1 "missing from shards"
  run_self_case bash-harness-orphan-unknown 1 "non-leaf in shards"
  run_self_case aggregate-in-shard 1 "non-leaf in shards"
  run_self_case pytest-recipe-in-shard 1 "non-leaf in shards"
  run_self_case mixed-pytest-bash-in-shard 1 "non-leaf in shards"
}

main() {
  if [[ "$#" -gt 1 ]]; then
    usage
    return 2
  fi

  if [[ "${1:-}" == "--self-test" ]]; then
    self_test
    return 0
  fi

  if [[ "$#" == "1" ]]; then
    usage
    return 2
  fi

  make_tmpdir
  validate_makefile "$MAKEFILE"
}

main "$@"
