# Count non-security ### OOS_* blocks in accepted-OOS markdown.
# Security routing: only a dedicated **focus-area** field line whose value
# begins with "security" (case-folded), optionally continued with -word
# tokens (e.g. security-hardening). Avoids prose like "focus-area = security"
# inside **Description** bodies (no **focus-area** label on that line).
BEGIN { n = 0; inblk = 0; sec = 0 }
/^###[[:space:]]+OOS_/ {
  if (inblk && !sec) n++
  inblk = 1
  sec = 0
  next
}
inblk && tolower($0) ~ /^[[:space:]]*-[[:space:]]*\*\*focus-area\*\*[[:space:]]*:[[:space:]]*security([-[:alnum:][:space:]_]*)([[:space:]]|$|\(|#|\.|,)/ {
  sec = 1
}
END {
  if (inblk && !sec) n++
  print n + 0
}
