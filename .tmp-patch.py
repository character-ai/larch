from pathlib import Path

path = Path('/Users/zhupanov/larch1/crates/larch-cli/src/audit_umbrella_commands.rs')
insert = Path('/Users/zhupanov/larch1/.tmp-insert-lines.txt').read_text()
lines = path.read_text().splitlines(keepends=True)

out = []
i = 0
while i < len(lines):
    out.append(lines[i])
    # Insert before Ok(()) that closes fetch_canonical_issue
    if (
        i > 0
        and 'flat_error(&error.to_string(), 500)' in lines[i - 1]
        and lines[i].strip() == 'Ok(())'
        and i + 1 < len(lines)
        and lines[i + 1].strip() == '}'
        and i + 2 < len(lines)
        and 'collect_snapshot_remote' in lines[i + 2]
    ):
        out.append(insert)
    i += 1

path.write_text(''.join(out))
print('inserted')
