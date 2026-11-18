# Lesson content format

Lesson content is authored here as YAML, imported into the backend once (`python -m aprende.content import aprende/content`),
and edited by staff in the admin pages afterwards (architecture D15). This folder is the seed, not a second source of truth.

```
aprende/content/
  sources.yaml          every source a legal statement may cite
  lessons/<id>.yaml     one file per lesson
```

## sources.yaml

```yaml
- id: pc-6110                     # unique; referenced by items
  kind: probate_code              # probate_code | courts_selfhelp
  cite: "6110"                    # probate_code: a section on carbon_intake.VERIFIED (read on leginfo in a real browser)
  url: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=PROB&sectionNum=6110
  read_on: 2026-11-15
- id: cc-wills
  kind: courts_selfhelp
  cite: Wills                     # the page title
  url: https://selfhelp.courts.ca.gov/...   # must be on selfhelp.courts.ca.gov
  read_on: 2026-11-18
```

## lessons/<id>.yaml

```yaml
id: will                          # lesson id; every step and item id starts with "<id>."
unit: will                        # will | trust | ahcd | poa | final | bonus
day: 1                            # core lessons 1-4, the final lesson 14, bonus lessons null
character: calavera               # host; an item may override it (Piñata runs the games)
sensitive: false                  # calm mode for the whole lesson (El Oso's lessons)
datos: [nombre, nacimiento]       # "Tus datos" question ids (carbon_intake guion-plan), asked after the lesson
title: {es: El testamento, en: The will}
steps:
  - id: will.1
    title: {es: ..., en: ...}
    items:
      - id: will.1.1
        kind: explain             # the character explains; text only
        legal: true               # states the law -> needs a source, and attorney approval before it publishes
        source: pc-6110
        es: {text: ...}
        en: {text: ...}
      - id: will.1.2
        kind: choice              # also: scenario (adds `story`) and listen (adds `say`, spoken by the character)
        legal: true
        source: pc-6110
        answer: 2                 # index into options; the same in both languages
        es: {prompt: ..., options: [..., ..., ...], explain: ...}
        en: {prompt: ..., options: [..., ..., ...], explain: ...}
      - id: will.1.3
        kind: truefalse
        answer: true
        es: {statement: ..., explain: ...}
        en: {statement: ..., explain: ...}
      - id: will.1.4
        kind: match               # pairs are written in their correct pairing; the player shuffles them
        character: pinata
        es: {prompt: ..., pairs: [[term, meaning], ...], explain: ...}
        en: {prompt: ..., pairs: [[term, meaning], ...], explain: ...}
      - id: will.1.5
        kind: order               # steps are written in their correct order; the player shuffles them
        es: {prompt: ..., steps: [..., ..., ...], explain: ...}
        en: {prompt: ..., steps: [..., ..., ...], explain: ...}
```

Optional on any item: `character`, `sensitive: true` (calm mode for that item).

## Rules the validator enforces

- Ids are unique; step and item ids start with their lesson id.
- `es` and `en` both exist and have the same fields; lists (options, pairs, steps) have the same length in both languages.
- `answer` is a valid index (choice, scenario, listen) or a boolean (truefalse); match and order have no `answer`.
- An item with `legal: true` has a `source` that exists in `sources.yaml`.
- A `probate_code` source cites a section on `carbon_intake.VERIFIED`; a `courts_selfhelp` source is on `https://selfhelp.courts.ca.gov/`.
- Lessons with a `day` have unique days; `unit` and `kind` come from the lists above; `datos` ids exist in `guion-plan`.
