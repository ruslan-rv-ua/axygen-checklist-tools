# Axygen Checklist Tools

Маркетплейс Claude Code з одним плагіном `axygen-checklist`: скілл `write`, що
пише й оновлює чеклісти для NVDA-аддона
[Axygen Checklist](https://github.com/ruslan-rv-ua/axygen-checklist) у чужому
проєкті, і валідатор, який скілл запускає після запису.

## Джерело правди — в аддоні

Формат чекліста, статуси, фрагменти, правила письма «на слух» нормує специфікація
аддона (§2 `docs/requirements.md`) і її англійський переказ для агентів,
`docs/checklist-format.md`. Тут їх не переказують ніде: ані в `SKILL.md`, ані в
README, ані в коді валідатора. `SKILL.md` описує **процес** (звідки беруться
пункти, як не зіпсувати чужий прогін), а формат бере з еталона.

**Еталон** — два файли в `plugins/axygen-checklist/skills/write/references/`,
дослівні копії `docs/checklist-format.md` і `docs/checklist-v1.schema.json` з
гілки `main` аддона. Їх не редагують: CI (`checks.yml`, job `reference`) порівнює
їх з аддоном байт у байт на кожен push і щотижня. Червона перевірка означає рівно
одну дію: скопіювати обидва файли знову й випустити патч-версію. Гілку аддона
називає одне місце — `ADDON_REF` у `checks.yml`. Чому копія, а не посилання чи
завантаження, — [`docs/adr/0001-reference-is-a-verbatim-copy.md`](docs/adr/0001-reference-is-a-verbatim-copy.md).

Поки аддон не випустив реліз із цими двома файлами, `main` їх не має, і job
`reference` червоний за побудовою; еталон узято з `develop` аддона.

## Валідатор

`plugins/axygen-checklist/skills/write/scripts/validate.py` — PEP 723-скрипт,
запуск `uv run --script`, Python від 3.12, єдина залежність `jsonschema`. Схему
бере поруч із собою, з еталона, а не з мережі. Перевіряє те, чого схема не може:
унікальність `id`, ключі, схожі на описку в імені поля, непарні зворотні
апострофи, а з `--before <знімок>` — незмінність `id`, `status` і `comment` проти
знімка, зробленого перед правкою, і те, що новий пункт бере наступний вільний
номер. Знімок, а не `HEAD`: на диску можуть лежати результати тестувальника, яких у
коміті ще немає.

Тести — `uv run python -m unittest discover -s tests -v`; `pytest` тут немає.
Перевірки перед комітом — `uv run prek run --all-files`, те саме, що CI.

## Гілкування й версія

git-flow (`git-flow-next`), конфіг у `.gitflow`. Робота лягає в `develop`; `main`
рухається лише через `release/*` і `hotfix/*`. Версію піднімають у гілці релізу в
`plugins/axygen-checklist/.claude-plugin/plugin.json` — єдине місце, де вона
записана; `marketplace.json` версії не має навмисно. До 1.0.0 аддона плагін іде як
0.x; major 1 він дістає разом із замороженням формату (§7 спеки аддона).

## Мова

Українською — `CLAUDE.md`, `CONTEXT.md`, ADR. Англійською — усе, що читає
незнайомець: `SKILL.md`, README, скрипт, тести, повідомлення комітів. Еталон
англійський, бо такий оригінал.

## Навички агентів

Трекер задач — GitHub Issues у `ruslan-rv-ua/axygen-checklist-tools`, операції
через `gh`, домовленості ті самі, що в аддоні:
[issue-tracker.md](https://github.com/ruslan-rv-ua/axygen-checklist/blob/develop/docs/agents/issue-tracker.md).
Мітки тріажу — ті самі п'ять:
[triage-labels.md](https://github.com/ruslan-rv-ua/axygen-checklist/blob/develop/docs/agents/triage-labels.md).
Доменні документи — `CONTEXT.md` і `docs/adr/` у корені.
