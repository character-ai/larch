---
name: extract-and-format-context
description: "Use when extracting and formatting a block of text from a file."
---

# Extract and Format Context

This skill extracts and formats a block of text from a file.

## Usage

To use this skill, run the `run.sh` script with the following arguments:

```bash
<path-to-skill>/scripts/run.sh <file-path> <line-number> <context-lines>
```

- `<file-path>`: The path to the file to extract the context from.
- `<line-number>`: The line number to center the context around.
- `<context-radius>`: The number of lines of context to extract on each side of the center line. The total number of lines extracted will be `2 * <context-radius> + 1`.

The script will output the extracted context with line numbers.
