# Count markdown blocks in accumulated-oos.md for OOS_WRITE_SEQ seeding.
# Unlike oos-non-security-block-count.awk, counts bare ### FINDING_N:
# openers too — accumulated-oos is an OOS-only sink where legacy resumes
# may still carry pre-normalization headers.
BEGIN { n = 0; inblk = 0 }
/^###[[:space:]]+(OOS_[0-9]+:|FINDING_[0-9]+:)/ {
  if (inblk) n++
  inblk = 1
  next
}
END {
  if (inblk) n++
  print n + 0
}
