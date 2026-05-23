# shellcheck shell=bash
# Sourced title-marker grammar helpers. Bash 3.2-compatible; do not execute.

# insert_signal_marker <title> <marker>
# Echoes <title> with [<marker>] inserted into the leading bracket-block
# sequence. Full contract lives in scripts/tracking-issue-write.md.
insert_signal_marker() {
    local title="$1"
    local marker="$2"
    local marker_block="[$marker]"
    local rest="$title"
    local after_open block after_block
    local found=false

    if [ -z "$title" ]; then
        printf '[%s]' "$marker"
        return 0
    fi

    while [[ "$rest" == \[* ]]; do
        after_open="${rest#\[}"
        case "$after_open" in
            *'] '*)
                block="[${after_open%%] *}]"
                after_block="${after_open#*] }"
                if [ "$block" = "$marker_block" ]; then
                    found=true
                    break
                fi
                rest="$after_block"
                ;;
            *)
                break
                ;;
        esac
    done

    if [ "$found" = true ]; then
        printf '%s' "$title"
        return 0
    fi

    case "$title" in
        '[DESIGNING] '*)
            printf '[DESIGNING] [%s] %s' "$marker" "${title#\[DESIGNING\] }"
            ;;
        '[DESIGNED] '*)
            printf '[DESIGNED] [%s] %s' "$marker" "${title#\[DESIGNED\] }"
            ;;
        '[IMPLEMENTING] '*)
            printf '[IMPLEMENTING] [%s] %s' "$marker" "${title#\[IMPLEMENTING\] }"
            ;;
        '[DONE] '*)
            printf '[DONE] [%s] %s' "$marker" "${title#\[DONE\] }"
            ;;
        '[STALLED] '*)
            printf '[STALLED] [%s] %s' "$marker" "${title#\[STALLED\] }"
            ;;
        '[IN PROGRESS] '*)
            printf '[IN PROGRESS] [%s] %s' "$marker" "${title#\[IN PROGRESS\] }"
            ;;
        '[PLANNED] '*)
            printf '[PLANNED] [%s] %s' "$marker" "${title#\[PLANNED\] }"
            ;;
        *)
            printf '[%s] %s' "$marker" "$title"
            ;;
    esac
}
