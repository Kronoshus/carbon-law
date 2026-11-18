# Characters

La Calavera, Piñata and El Oso: art drawn in code, rigged in Blender with one shared set of shape keys, exported as GLB.

    python characters/build.py              # all three; or: python characters/build.py oso

Needs `pip install -r characters/requirements.txt` and Blender 5.3 (`BLENDER=/path/to/blender`; from WSL the Windows
Blender is used by default). Writes `characters/out/<name>/` (atlas, rig description, `.blend`) and copies the GLB, a
still image and the backdrop into `aprende/public/characters/`.

| File | What it is |
|---|---|
| `charkit.py` | the shared drawing kit: La Calavera's outline, palette, eyes and cheeks |
| `pinata_art.py`, `oso_art.py` | each character's art, `draw(**state)` and its moving-parts map `rig()` |
| `calavera_states.py` | La Calavera's state and costume layers; his base art is `avatar-intake/calavera.png`, unchanged |
| `build.py` | draws, turns each state into an overlay, packs the atlas, runs Blender, copies to the app |
| `make_character.py` | the Blender script: the sheet, the shape keys, the overlays, the export |
| `viewer.html` | renders any pose of a GLB the way the app does (for review) |

Shape keys: the prototype's eight (`jawOpen blink mouthRound browUp lookX headYaw headPitch headRoll`), `think`, and one per
overlay (`celebrate`, `comfort`, `wave` + `waveSwing`, `glasses`, `pen`). Every key starts at 0. Only Opus changes the art
(brief section 0); builders wire the files into the app.
