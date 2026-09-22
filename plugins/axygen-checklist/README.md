# axygen-checklist

A Claude Code plugin for writing checklists for
[Axygen Checklist](https://github.com/ruslan-rv-ua/axygen-checklist), an NVDA add-on
that walks a checklist by ear while the tester's focus stays in the application
under test.

## What it does

One skill, `/axygen-checklist:write`, that turns "make me a test checklist for the
settings dialog" into a checklist file the add-on can open. It also fires on its own
when a project's agent is asked for a test checklist or to update one.

The skill knows the format and the craft of writing for the ear from a verbatim copy
of the add-on's authoring guide, `docs/checklist-format.md`, and validates what it
wrote with a script that runs the add-on's JSON Schema and adds what the schema
cannot express: unique `id`, misspelled field names, and, for a file that already
carries results, that no `status` or `comment` of the tester was touched and no item
was renumbered.

Files written for `format_version` 1.

## Requirements

[`uv`](https://docs.astral.sh/uv/) on the machine the agent runs on: the validator
is a PEP 723 script and `uv run --script` installs its one dependency. Without `uv`
the skill checks by hand and says so.

## The validator by hand

```
uv run --script skills/write/scripts/validate.py path/to/checklist.json
uv run --script skills/write/scripts/validate.py path/to/checklist.json --before path/to/snapshot.json
```

Exit code 0 means no errors, 1 means errors, 2 means the file is not readable JSON.
