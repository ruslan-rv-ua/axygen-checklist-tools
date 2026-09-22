# Changelog

## 0.1.0 (2026-09-22)

First release. Written for `format_version` 1 of the add-on, as released in
Axygen Checklist 0.1.0.

- Plugin `axygen-checklist` with the `write` skill: writes a new checklist for a
  subject, or updates a live one while keeping the tester's results.
- Validator: the add-on's schema plus unique `id`, misspelled field names, unpaired
  backticks, and, against a snapshot taken before an edit, untouched `status`,
  `comment` and item numbers.
