# Axygen Checklist Tools

Tools for writing checklists for
[Axygen Checklist](https://github.com/ruslan-rv-ua/axygen-checklist), an NVDA add-on
for testers who work by ear. The add-on walks a checklist with global hotkeys while
the system focus stays in the application under test, and records the outcome of
every item back into the same JSON file.

This repository is a Claude Code plugin marketplace with one plugin:

- [`axygen-checklist`](plugins/axygen-checklist/) — the `/axygen-checklist:write`
  skill, which writes and updates checklist files inside the project under test,
  and a validator that checks what the add-on's schema cannot.

## Install

```
/plugin marketplace add ruslan-rv-ua/axygen-checklist-tools
/plugin install axygen-checklist@axygen-checklist-tools
```

The validator needs [`uv`](https://docs.astral.sh/uv/) on the machine the agent
runs on.

## Develop

```
uv sync
uv run python -m unittest discover -s tests -v
uv run prek run --all-files
claude --plugin-dir ./plugins/axygen-checklist
```

The two files under `plugins/axygen-checklist/skills/write/references/` are verbatim
copies of `docs/checklist-format.md` and `docs/checklist-v1.schema.json` from the
add-on's `main` branch. CI compares them byte for byte on every push and once a
week; when the add-on changes them, copy them again and release a patch. The
reasons are in [`docs/adr/0001-reference-is-a-verbatim-copy.md`](docs/adr/0001-reference-is-a-verbatim-copy.md).

## License

GPL-2.0-or-later, the license of the add-on whose documents this repository
carries. See [`COPYING.txt`](COPYING.txt).
