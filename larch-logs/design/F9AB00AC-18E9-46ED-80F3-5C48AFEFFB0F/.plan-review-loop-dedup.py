import os
import re
import subprocess
import sys
import tempfile

helper = os.environ.get("SCOPE_MARKER_HELPER")


def split_all_blocks(text):
    parts = re.split(r"(?m)^(?=### (?:FINDING|OOS)_[0-9]+:)", text)
    fins, oos = [], []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = re.match(r"^### (FINDING|OOS)_[0-9]+:", p)
        if not m:
            continue
        (fins if m.group(1) == "FINDING" else oos).append(p)
    return fins, oos


def is_tagged(block):
    if not helper:
        return False
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as fh:
        fh.write(block)
        name = fh.name
    try:
        proc = subprocess.run([sys.executable, helper, "dirty-tree", "scope-marker", "--file", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if proc.returncode == 0:
            return True
        if proc.returncode == 1:
            return False
        print("ERROR: scope marker helper failed (rc=%d); refusing to dedup scope-reduction findings" % proc.returncode, file=sys.stderr)
        raise SystemExit(2)
    finally:
        try:
            os.unlink(name)
        except OSError:
            pass


def problem_text(block):
    candidate_lines = []
    for line in re.sub(r"```.*?```", "", block, flags=re.S).splitlines():
        stripped = line.strip()
        for pattern in (
            r"^###\s+(?:FINDING|OOS)_[0-9]+:\s*(.*)$",
            r"^-?\s*(?:\*\*)?Concern(?:\*\*)?:\s*(.*)$",
            r"^\s*what:\s*(.*)$",
        ):
            m = re.match(pattern, stripped, re.I)
            if m and m.group(1).strip():
                candidate_lines.append(m.group(1).strip())
    if is_tagged(block):
        for label in ("Concern", "Description"):
            m = re.search(r"- \*\*%s\*\*:\s*(.+?)(?:\.\s*Scenario:|\s*Scenario:|(?=\n- \*\*)|\Z)" % label, block, re.S)
            if m and m.group(1).strip():
                return m.group(1).strip()
        if candidate_lines:
            return candidate_lines[0]
    for label in ("Concern", "Description"):
        m = re.search(r"- \*\*%s\*\*:\s*(.+?)(?:\.\s*Scenario:|\s*Scenario:|(?=\n- \*\*)|\Z)" % label, block, re.S)
        if m and m.group(1).strip():
            return m.group(1).strip()
    if candidate_lines:
        return candidate_lines[0]
    head = block.splitlines()[0] if block.splitlines() else block
    return re.sub(r"^###\s+(?:FINDING|OOS)_[0-9]+:\s*", "", head).strip() or block


def comparison_text(block):
    text = problem_text(block)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)
    text = re.sub(r"^\s*\[(?:important|nit|latent)\]\s*", "", text, flags=re.I)
    text = re.sub(r"^\s*\[SCOPE-REDUCTION\]\s*", "", text, flags=re.I)
    return text


def tokens(s):
    return set(re.findall(r"[A-Za-z0-9_]+", s.lower()))


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def reviewer_line(block):
    m = re.search(r"(\*\*Reviewer\(s\)\*\*: )([^\n]+)", block)
    if m:
        return m
    return re.search(r"(\*\*Reviewers?\*\*: )([^\n]+)", block)


def merge_reviewers(a, b):
    ma = reviewer_line(a)
    mb = reviewer_line(b)
    if not ma or not mb:
        return a
    existing = [x.strip() for x in ma.group(2).split(",") if x.strip()]
    for item in [x.strip() for x in mb.group(2).split(",") if x.strip()]:
        if item not in existing:
            existing.append(item)
    return a[:ma.start(2)] + ", ".join(existing) + a[ma.end(2):]


def choose_tagged_body(a, b):
    return b if len(tokens(comparison_text(b))) > len(tokens(comparison_text(a))) else a


def dedup(blocks, thresh=0.6):
    kept = []
    kept_tagged = []
    for blk in blocks:
        t = tokens(comparison_text(blk))
        tagged = is_tagged(blk)
        merged = False
        for i, kb in enumerate(kept):
            if jaccard(t, tokens(comparison_text(kb))) > thresh:
                if tagged and kept_tagged[i]:
                    kept[i] = merge_reviewers(choose_tagged_body(kb, blk), kb if choose_tagged_body(kb, blk) is blk else blk)
                    kept_tagged[i] = True
                elif tagged and not kept_tagged[i]:
                    kept[i] = merge_reviewers(blk, kb)
                    kept_tagged[i] = True
                else:
                    kept[i] = merge_reviewers(kb, blk)
                    kept_tagged[i] = kept_tagged[i] or tagged
                merged = True
                break
        if not merged:
            kept.append(blk)
            kept_tagged.append(tagged)
    return kept


def renumber(fins, oos):
    out = []
    for i, b in enumerate(fins, 1):
        out.append(re.sub(r"^### FINDING_[0-9]+:", "### FINDING_%d:" % i, b, count=1, flags=re.M))
    for i, b in enumerate(oos, 1):
        out.append(re.sub(r"^### OOS_[0-9]+:", "### OOS_%d:" % i, b, count=1, flags=re.M))
    return out


def main():
    raw = sys.stdin.read()
    fins, oos = split_all_blocks(raw)
    fins2 = dedup(fins)
    fin_keys = {" ".join(sorted(tokens(comparison_text(b)))) for b in fins2}
    oos2 = []
    for b in dedup(oos):
        if " ".join(sorted(tokens(comparison_text(b)))) in fin_keys:
            continue
        oos2.append(b)
    out = renumber(fins2, oos2)
    sys.stdout.write("\n\n".join(out))
    if out:
        sys.stdout.write("\n")

if __name__ == "__main__":
    main()
