# Aprende y Planea — Phase 3 (Characters) report

Date: 2026-11-18. Status: **complete**. Tickets T3-01 to T3-07 merged (#25, #26, #27).

## What exists now

- **One build for every character.** `python characters/build.py` draws the art in code, turns each state into an overlay,
  packs one texture, runs Blender (`characters/make_character.py`) and copies the GLB, a still image and the backdrop into the app.
- **Three rigged characters on one rig.** The prototype's eight shape keys, plus `think` and the state overlays:

  | Character | States | GLB |
  |---|---|---|
  | La Calavera (look unchanged) | celebrating (happy eyes), thinking, waving (raised skeletal hand), dancing; costumes: reading glasses (day 9), fountain pen (signing day) | 1.3 MB (was 11 MB) |
  | Piñata | celebrating, thinking, talking | 0.7 MB |
  | El Oso | celebrating, thinking, comforting (eyes closed, paws offered) | 0.8 MB |

- **One animation engine** (`aprende/src/core/character/`), ported from the prototype with the same constants and framing,
  driving all three; `CharacterStage` shows a character with the permanent "Programa de IA · no es el abogado" label, a
  still-image fallback without WebGL, reduced-motion support, and three.js loaded only when a stage appears.
- **Characters API** (`/characters`): which characters are on, which units they host, their voices; La Calavera cannot be turned off.

![Final lineup](characters/lineup-final.png)

![The stage on a phone](phase3/stage-phone.png) ![At side-panel size](phase3/side-panel-160px.png)

## Verification on `main`

- La Calavera rebuilt by the new pipeline vs. his original GLB, four frozen poses: 0.00 %, 0.25 %, 0.03 %, 0.04 % of pixels differ (target ≤ 1 %).
- Every state of every character rendered through the real engine and reviewed (screenshots in the PR history); mouths and El Oso's comfort pose read at 160 px.
- `pytest`: 112 passed. `aprende`: typecheck, lint, i18n (52 keys), 22 unit tests, both builds; Playwright 11 passed. CI green.

## Found and fixed

- The prototype's Blender pipeline exported every shape key with a default weight of 1 (the prototype masked it by setting all keys each frame). Fixed in the new pipeline.
- The first engine port rendered black (materials and camera not ported) and committed an 11 MB GLB to history; both reworked before merge.

## Open for the firm

- **Q-C1** La Calavera's name (the app uses "La Calavera" until then; names are one translation key each).
- **Q-C2** a native-speaker / community review of the characters.
- **Q-C3** voices for Piñata and El Oso — only relevant once server voice is approved (F-003); with the browser voice all characters use the device's Spanish or English voice.

## Next: Phase 4 (Learning)

Opus writes the four core lessons, the final lesson and the bonus lessons with their sources; Beam builds the content
tables, the learning API, the lesson player, the exercise types, motivation (petals, candle, seals) and the price card.
Needed from the firm during Phase 4: who reviews the Spanish (Q-L1) and how the attorney wants to review lesson content (Q-L2).
