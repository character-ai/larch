# Count non-security ### OOS_* blocks in accepted-OOS markdown.
# Legacy support: tagged "### FINDING_N: ... [OUT_OF_SCOPE]" headers also
# start blocks; the [OUT_OF_SCOPE] literal is required for FINDING headers so
# bare "### FINDING_N:" stays in-scope in mixed accepted-findings files.
# Security routing: only a dedicated focus-area field line whose value
# begins with "security" (case-folded), optionally continued with -word
# tokens (e.g. security-hardening), and allowing backtick-wrapped labels or
# values. Matches both the rendered bold-spaced form emitted by
# plan-review-loop.sh ("- **Focus area**: security") and the legacy
# hyphenated form ("- **focus-area**: security"). Avoids prose occurrences
# inside **Description** bodies (no line-start focus-area label).
function is_security_header(line,    lower) {
  lower = tolower(line)
  return lower ~ /^###[[:space:]]+(oos_[0-9]+:|finding_[0-9]+:)[[:space:]]*(\[(out_of_scope|oos)\][[:space:]]*)?`?(\[security\]|<security>)`?([[:space:]]|$|[:-])/
}
BEGIN { n = 0; inblk = 0; sec = 0 }
/^###[[:space:]]+OOS_/ || ($0 ~ /^###[[:space:]]+FINDING_[0-9]+:/ && ($0 ~ /\[(OUT_OF_SCOPE|OOS)\]/)) {
  if (inblk && !sec) n++
  inblk = 1
  sec = is_security_header($0)
  next
}
inblk {
  line = tolower($0)
  gsub(/[`*]/, "", line)
  if (line ~ /^[[:space:]-]*focus[-[:space:]]area[[:space:]]*[:=][[:space:]]*security([-[:alnum:][:space:]_]*)([[:space:]]|$|\(|#|\.|,)/) sec = 1
}
END {
  if (inblk && !sec) n++
  print n + 0
}
