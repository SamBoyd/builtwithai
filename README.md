# BuiltWithAI

## Prototype CLI

Run the prototype CLI as a Python module from the repository root:

```bash
python3 -m prototype.cli prototype/spec.md --pr 3
```

Do not run it as `python3 prototype/cli.py`; module execution keeps package imports clean until the project has a packaged console script.
