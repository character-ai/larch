---
paths: ["python/test_*.py"]
---

# Python Test Monkeypatch Lambdas

Pyright strict mode can flag untyped lambda parameters in
`monkeypatch.setattr` callables.

- Prefer a typed helper function when monkeypatching callables with
  parameters.
- If an inline `monkeypatch.setattr(..., lambda ...)` lacks type context
  for lambda parameters, add `# type: ignore[arg-type]` on that
  `monkeypatch.setattr` line.
- Preserve existing pyright suppressions. Add only the minimum needed
  suppression.
- See the existing pattern in `python/test_pr_body.py`.
- Run `make py-lint` after touching `python/test_*.py`.
