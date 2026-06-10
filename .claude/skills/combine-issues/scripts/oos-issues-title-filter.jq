# Title filter for /combine-issues --oos mode.
# Keeps only issues whose title starts with the literal prefix "[OOS] "
# (prefix match, not substring; matches exactly ^[OOS] ).
[
  .[] |
  select(.title | test("^\\[OOS\\] "))
]
