# Exit 0 when a legacy ### FINDING_N: block opener exists (pre-normalization).
# Body citations after an OOS_ block opener are ignored (#3550).
BEGIN { seen_oos = 0; legacy = 0 }
/^###[[:space:]]+OOS_/ { seen_oos = 1; next }
/^###[[:space:]]+FINDING_[0-9]+:/ {
  if (!seen_oos) legacy = 1
}
END { exit (legacy ? 0 : 1) }
