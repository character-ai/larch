#!/usr/bin/env python3
from pathlib import Path

path = Path("/Users/zhupanov/larch1/crates/larch-cli/src/audit_umbrella_commands.rs")
text = path.read_text()

old = """    for number in &direct_numbers {
        if *number == umbrella {
            continue;
        }
        fetch_canonical_issue(service, cancellation, repository, &mut issues, *number).await?;
    }
    require_no_nested_umbrella_children(&issues, &direct_numbers)?;
    for number in &referenced_numbers {
        if *number == umbrella {
            continue;
        }
        fetch_canonical_issue(service, cancellation, repository, &mut issues, *number).await?;
    }"""

new = """    require_no_nested_umbrella_children(&issues, &direct_numbers)?;
    let mut canonical_numbers = BTreeSet::new();
    for number in &direct_numbers {
        if *number != umbrella {
            canonical_numbers.insert(*number);
        }
    }
    for number in &referenced_numbers {
        if *number != umbrella {
            canonical_numbers.insert(*number);
        }
    }
    for number in canonical_numbers {
        fetch_canonical_issue(service, cancellation, repository, &mut issues, number).await?;
    }"""

if old not in text:
    raise SystemExit("collect_snapshot_remote loop not found")
text = text.replace(old, new)
path.write_text(text)
print("ok")
