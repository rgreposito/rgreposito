# Contributing

## Local checks

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m relay_lab
```

Keep changes small and reviewable. Each lifecycle change should include success and failure/out-of-order tests. Never include real credentials or payment data in fixtures.
