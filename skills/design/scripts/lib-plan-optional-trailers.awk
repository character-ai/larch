# Shared optional-trailer metadata block parser for /design plan-size gating.
# Invoked with -v mode=keys|values|parse|has_key and -v trailer_nr=N (last non-empty line).
# has_key mode also requires -v key=diff_added|diff_deleted|mechanical_churn.

BEGIN {
    if (mode == "") {
        mode = "parse"
    }
}

{
    lines[NR] = $0
}

END {
    block_len = 0
    for (i = trailer_nr - 1; i >= 1; i--) {
        line = lines[i]
        if (line ~ /^diff_added: [0-9]+$/) {
            block[++block_len] = line
            continue
        }
        if (line ~ /^diff_deleted: [0-9]+$/) {
            block[++block_len] = line
            continue
        }
        if (line ~ /^mechanical_churn: (true|false)$/) {
            block[++block_len] = line
            continue
        }
        break
    }

    diff_added = ""
    diff_deleted = ""
    mechanical_churn = "false"
    has_added = 0
    has_deleted = 0
    has_mech = 0

    for (j = block_len; j >= 1; j--) {
        line = block[j]
        if (line ~ /^diff_added: [0-9]+$/) {
            diff_added = substr(line, 13)
            has_added = 1
            continue
        }
        if (line ~ /^diff_deleted: [0-9]+$/) {
            diff_deleted = substr(line, 15)
            has_deleted = 1
            continue
        }
        if (line ~ /^mechanical_churn: true$/) {
            mechanical_churn = "true"
            has_mech = 1
            continue
        }
        if (line ~ /^mechanical_churn: false$/) {
            mechanical_churn = "false"
            has_mech = 1
        }
    }

    if (mode == "has_key") {
        if (key == "diff_added" && has_added) {
            exit 0
        }
        if (key == "diff_deleted" && has_deleted) {
            exit 0
        }
        if (key == "mechanical_churn" && has_mech) {
            exit 0
        }
        exit 1
    }

    if (mode == "keys") {
        if (has_added) {
            print "diff_added"
        }
        if (has_deleted) {
            print "diff_deleted"
        }
        if (has_mech) {
            print "mechanical_churn"
        }
        exit 0
    }

    if (mode == "values") {
        if (has_added) {
            print "diff_added=" diff_added
        }
        if (has_deleted) {
            print "diff_deleted=" diff_deleted
        }
        if (has_mech) {
            print "mechanical_churn=" mechanical_churn
        }
        exit 0
    }

    # mode == parse (default): subtract only winning optional keys (last-match-wins), not duplicate block lines
    metadata_trailer_lines = has_added + has_deleted + has_mech
    printf "%d\n", metadata_trailer_lines
    if (diff_added == "") {
        print "-"
    } else {
        print diff_added
    }
    if (diff_deleted == "") {
        print "-"
    } else {
        print diff_deleted
    }
    print mechanical_churn
}
