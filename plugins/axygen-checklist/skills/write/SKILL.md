---
name: write
description: Write or update a test checklist for the Axygen Checklist NVDA add-on, a JSON file a screen-reader tester walks by ear. Use when asked for a test checklist or a manual test plan, or to update or extend a checklist file (JSON with checklist_name and sections).
argument-hint: [what to test]
---

# Write a checklist

A checklist has two authors. You write what to check; the tester writes the results
through the add-on, into the same file, possibly while you are editing it. The format
and the craft of writing for the ear are in
[references/checklist-format.md](references/checklist-format.md). Read it in full
before step 1: every step below assumes it, and none of it is repeated here.

## 1. Pin the subject

The **subject** is what the checklist checks, in the user's words: `$ARGUMENTS`, or
the request that invoked you. **Sources** are what you derive items from: the diff of
the change, the issue or pull request, the code of the feature, the conversation so
far. Gather sources yourself; the user names the subject and nothing else.

Done when you can list the concrete actions the tester will perform and what each
one should sound like. If the subject cannot be turned into actions from what you
have, ask one question, then continue with the answer.

## 2. Find where checklists live

Search the project for JSON files that carry both `"checklist_name"` and
`"sections"`.

- Some exist: a checklist for this subject is the file to update; a new one goes
  beside them, in their language.
- None exist: propose `checklists/` at the project root and a file name made from
  the subject in kebab-case. Write in the language of the request.

## 3. Snapshot a file you are about to change

The file on disk is the live state of a run, and the tester's results in it are the
one thing you cannot recreate. Before the first edit, copy the file to a temporary
directory outside the project, and keep the path: step 5 compares against it.
Then read the file again right before writing, and write back what you read.

## 4. Write the items

Derive items from the sources: every behaviour the change touches gets one, and
one item is one action plus the result the tester expects to hear. The reference
says how an item reads well by ear, when a fact belongs in `note`, what goes in a
first section of preconditions, and how a fragment is marked; apply all of it.

When updating: existing items keep their `id`, a new item takes the next unused
number counting across the whole file, and every `status` and `comment` stays
verbatim, on items you are not otherwise touching too. An item that has become
obsolete is reported to the user in step 7 and left in place.

Done when every behaviour the sources touch has an item, and every item names an
action and an expected result.

## 5. Validate

The validator runs the schema and adds what the schema cannot check. New file:

```
uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/write/scripts/validate.py" <file>
```

Updated file, against the snapshot from step 3:

```
uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/write/scripts/validate.py" <file> --before <snapshot>
```

Fix every error and run again until it reports zero. Resolve each warning or carry
it into the report with a reason. If `uv` is missing, say so in the report and check
by hand against the reference: field names spelled exactly, `id` unique, and, for an
updated file, `id`, `status` and `comment` identical to the snapshot with new items
pending.

## 6. Leave the project ready for the next author

If the project's `AGENTS.md` or `CLAUDE.md` lacks the block under "Paste this into
your `AGENTS.md`" in the reference, add it, plus one line naming the folder the
checklists live in.

## 7. Report

Give the path, each section with its item count, the subject and the sources used,
what could not be derived and why, warnings left and the reason for each, obsolete
items if any, and one line reminding that `status` and `comment` are the tester's:
the add-on writes them.
