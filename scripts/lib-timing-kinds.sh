# shellcheck shell=bash
# lib-timing-kinds.sh — Canonical timing task-kind allow-list.

# shellcheck disable=SC2034
TIMING_TASK_KINDS_ALLOWED=(
    codex-review
    cursor-review
    gemini-review
    codex-review-generic
    cursor-review-generic
    gemini-review-generic
    codex-implement
    cursor-implement
    gemini-implement
    codex-sketch-arch
    codex-sketch-edge
    codex-sketch-innovation
    codex-sketch-pragmatic
    cursor-sketch-arch
    cursor-sketch-edge
    cursor-sketch-innovation
    cursor-sketch-pragmatic
    codex-sketch-generic
    cursor-sketch-generic
    codex-plan-arch
    codex-plan-edge
    codex-plan-innovation
    codex-plan-pragmatic
    cursor-plan-arch
    cursor-plan-edge
    cursor-plan-innovation
    cursor-plan-pragmatic
    codex-plan-voter
    cursor-plan-voter
    codex-review-voter
    cursor-review-voter
    cursor-specialist-correctness-edges
    cursor-specialist-security-structure-tests
    codex-specialist-correctness-edges
    codex-specialist-security-structure-tests
    codex-debate-thesis
    codex-debate-antithesis
    cursor-debate-thesis
    cursor-debate-antithesis
    codex-judge
    cursor-judge
    vendor-misc
)
