# Drop the trailing contiguous metadata block (diff_added/diff_deleted/diff_lines/
# mechanical_churn) and trailing blank lines from plan.txt, leaving the plan body.
{ lines[NR] = $0 }
END {
  last = NR
  while (last > 0 && (lines[last] ~ /^(diff_added|diff_deleted|diff_lines|mechanical_churn):/ || lines[last] ~ /^[[:space:]]*$/)) last--
  for (i = 1; i <= last; i++) print lines[i]
}
