# Prompt: improve the interactive attorney avatar

Paste everything below the line into another AI coding assistant that can read and edit the files in this folder.

---

You are taking over a working product and your job is to make it better. Read this whole brief, then read the code, before changing anything.

## What the product is

A talking avatar of attorney Pankaj Raval (Carbon Law Group, Los Angeles) that runs on one Windows PC and is shown to clients through Zoom screen share. It speaks Spanish or English, explains estate planning, interviews the client, and records and transcribes the answers so the attorney can draft a will or trust. The people on the other end are members of the public, often older, often on a phone, often not technical. The attorney's staff operate it. Neither group will read code or logs.

It has two modes:

- **Scripted**: reads a fixed script and records each answer.
- **Conversation** (`?chat=1`): after the consent step, a Claude model leads a spoken back-and-forth, using the script as its source of explanations and its checklist of questions.

## How it works

| File | What it does |
|---|---|
| `server.py` | Python standard-library web server on `127.0.0.1:8765`. Serves the page; proxies ElevenLabs for voice (`/tts`, returns audio plus the start time of every character) and transcription (`/answer`); calls the Anthropic Messages API for conversation (`/chat`) and for the attorney memo (`/summary`); writes `sessions/<timestamp>/`. `python server.py --check` runs its self-check. |
| `index.html` | The whole front end, one file. three.js loads `avatar.glb` and animates it: jaw from loudness, lip shape from the character being spoken, blinking, eyebrow lift, breathing, nodding while listening. Also the interview loop, voice-activity detection, and Zoom audio capture. |
| `guion*.json` | The scripts. `guion.json` is the will intake, `guion-fideicomiso.json` the California living-trust walkthrough; `-en` files are the English versions. Each step is `{id, label, say, ask?, consent?}`. |
| `prep_photo.py` | Turns a portrait into `pankaj2.png` (background removed, face sharpened) and `pankaj2.json` (98 face landmarks). Runs in the Python environment at `%USERPROFILE%\avatar-tools\venv`. |
| `make_avatar.py` | Run by Blender 5.3 headless. Builds the avatar from the prepared portrait: a relief mesh with a real mouth slit, shape keys `jawOpen`, `blink`, `mouthRound`, `browUp`, a mouth interior, and a blurred bookshelf backdrop. Writes `avatar.blend` and `avatar.glb`. |
| `render.py` | Optional and never yet run: pre-renders photoreal talking clips with SadTalker. The page plays a clip instead of the 3D avatar when one exists. |
| `.env` | `ELEVENLABS_API_KEY`, `ANTHROPIC_API_KEY`, optional `ELEVENLABS_VOICE_ID`, `ANTHROPIC_MODEL`. Never print, log, commit or transmit these values. |

Page addresses: `/` (Spanish will intake), `?guion=guion-fideicomiso` (trust walkthrough), `&lang=en` (English), `&chat=1` (conversation mode).

Each session folder holds one audio file per answer, `answers.json`, `intake.md` (the transcript), and `summary.md` (the attorney memo, written when the model key is present).

## Rules that are not yours to relax

These exist because this is a law office talking to the public in California. Do not weaken them to make a demo smoother.

1. **Disclosure and consent come first.** The avatar must say it is an AI program and not the attorney, and must get a spoken yes to recording, before anything else happens. A no ends the session. California requires all parties to consent to recording.
2. **General information only.** The avatar never gives legal advice about the client's own situation, never quotes fees, never promises results, never says a document is done. Specific questions are noted for the attorney.
3. **The attorney approves the words.** Anything the avatar says in scripted mode, and the material the model draws on in conversation mode, comes from the script files. If you change legal content, flag it for attorney review in your report; do not present your own legal wording as final.
4. **Client data stays on the PC.** The server binds to localhost. Session files and `.env` are never served. Do not add analytics, cloud storage, or new outside services that receive client audio or text without saying so plainly and getting a yes from the user. Reflection's Beam (transcript text) receives client data, approved by the firm on 2026-11-15 (ElevenLabs is approved too but is off by default since voice and transcription moved onto the PC on 2026-11-16) and documented in `README.md` under "Where client information goes"; that approval covers those two services only, not a licence for more.
5. **Never lose an interview.** Audio is written to disk before transcription is attempted, and the transcript is saved after every answer. Keep it that way.
6. **It is his likeness.** Do not use the avatar, voice or photos for anything except this product.

## How to work

- Keep it small. Standard library and browser features first. One page, one server file. Add a dependency only when a few lines of code cannot do the job, and say why.
- Understand before you edit. Trace the path a spoken answer takes: microphone or Zoom audio, voice-activity detection, `/answer`, transcription, `answers.json`, and on to `/chat` or the next script step.
- Change one thing at a time and prove it. After a change to the server, run `python server.py --check` and extend that check when you add logic with a branch in it. After a change to the page or the avatar, open it in a browser and look at it. For the avatar, freeze a pose with `window.__pose = [jaw, blink, round, brow]` in the console and inspect the face.
- To test without a microphone, replace `navigator.mediaDevices.getUserMedia` with a stream from an oscillator and set `window.confirm = () => true`. To test conversation mode without spending model credits, replace `window.fetch` for `/chat` with canned replies. Use the `Siguiente` / `Next` button to skip speech and end listening.
- Judge the avatar by watching it speak a full paragraph at normal size, not by a still frame. Ask of every visual change: would a client on a phone find this more trustworthy, or more strange?
- Report honestly: what you changed, what you watched working, what you could not test, and what needs the attorney's decision. A real Zoom call with a real person answering has never been tested; say so until someone does it.

## Known weaknesses, most valuable first

Pick from the top unless the user directs otherwise. Each item says what "better" means.

1. **Never tested live.** No real person has answered through a real microphone, and no real Zoom call has been run. Better: a written, step-by-step operator checklist proven on an actual call, with fixes for whatever breaks (echo, the avatar hearing itself, audio device selection, Zoom's "share sound").
2. **Turn-taking is crude.** The avatar decides the client has finished after 2.5 seconds of quiet, judged by loudness alone. Slow speakers get cut off; background noise holds the turn open. The client cannot interrupt. Better: a proper voice-activity detector, a visible "listening" cue the client can understand, and interruption that stops the avatar when the client starts talking.
3. **Conversation mode is only lightly proven.** It now runs on Reflection's Beam (`REFLECTION_API_KEY`); typed test conversations in Spanish and English took 1 to 5 seconds per reply and the model refused an injection attempt and a request for advice. Two Beam behaviours are handled in code, not trusted to the prompt: it must be sent its own `reasoning_content` for every earlier reply (the page keeps it), and it sometimes loops, repeating one question hundreds of times, so `spoken()` trims every reply to the first repeat, the first question and 220 words, and `looping()` rejects a looping memo or draft. It still over-asks for spellings. Not yet run with a spoken client, because the ElevenLabs credits are used up. Better: measured turn latency under about two seconds (streaming the model reply sentence by sentence into the voice is the obvious route), and a set of test conversations showing the model stays within the rules above, including when the client pushes for advice, changes subject, withdraws consent, or is in distress.
4. **The face is one photo pushed into relief.** It can only turn a few degrees; the lips are driven by spelling, not sounds, which is fair for Spanish and rough for English; the photo's smile never fully relaxes; the teeth do not part; the eyes do not move. The portrait shows him younger than he is now. Better: any of a true 3D head built from several photos, phoneme-accurate mouth shapes, eye movement, or a current portrait, each judged by watching it speak.
5. **Transcription errors go straight into the record.** Names, dates, and amounts are the facts a will depends on. Better: the avatar reads back names and numbers for confirmation, and the memo marks low-confidence items against the audio.
6. **The draft will needs the attorney's eye.** `draft_will()` in `server.py` follows Carbon Law Group's drafting standards (from the `Kronoshus/carbon-law` repo: `prompt-library/PRD_Carbon_Law_CA_Estate_Document_Drafting.md`, `pour-over-will-drafter.md`, `docs/scope-and-review-standards.md`): no inferred terms, `[ATTORNEY TO COMPLETE - ...]` for every gap, no execution block, client data fenced as untrusted, labels added outside the model's text, malformed or looping output rejected with nothing written. `VERIFIED` holds eight Probate Code sections read from leginfo.legislature.ca.gov on 2026-11-15; drafts may cite only those, and `unverified_cites()` flags any other on the draft. Each draft gets `draft-will.ai-record.json` in the field names of Bailment's `document_manifest.py` (hashes only). Beam drafts of the fictional test client are in `sessions/2026-11-15T19-47-40/` (v1 before these rules, current after). Better: the attorney's review of several drafts, his own clause language and Word template, and re-checking `VERIFIED` when statutes change.
7. **Operator experience.** `start.bat` starts it, a drop-down picks the version, a pill on the avatar shows listening / transcribing / thinking, and `README.md` is the operator guide. None of it has been used by the firm's staff. Better: watch a non-technical person run a practice call from the guide alone and fix every place they hesitate.
8. **Scripts are drafts.** All four were written by an AI and have not been reviewed by the attorney. Better: his corrections applied, and the Spanish checked by a native speaker for the firm's client base.

## State of testing (2026-11-15)

- The ElevenLabs account is on the free plan and its monthly characters are used up. Until that changes, the avatar speaks with the browser's backup voice (lip shapes still follow the letters), and any test that needs the real voice or more transcription will fail with `quota_exceeded`. Do not burn credits on long test runs; test animation with the backup voice.
- Full runs with a spoken test client have passed: the English will intake (all 12 answers transcribed almost word for word; only name spellings drifted, e.g. Mendez -> Mendes, Daniela -> Daniella) and the English trust walkthrough. No Spanish full run yet: Windows on this PC has no Spanish voice to play the client.
- Conversation mode without a model key falls back to the scripted questions and tells the operator; it has still never talked to the real model.
- Operator-only notices (backup voice, model errors) go in `#note` in the bottom bar, never on the stage the client sees. After the first ElevenLabs failure the session stays on the backup voice so the avatar never switches voices mid-interview.
- Consent (fixed 2026-11-15): the old check accepted "No, no acepto" because it looked for a yes word first. Now `consent(text)` in `index.html` returns false for refusal words alone, true for yes words alone, and null (operator decides; Cancel = no) when both or neither appear. `window.__consent` exposes it; keep a phrase table passing (28 cases were checked: Spanish and English refusals, accepts, mixed, empty). A refusal calls `/declined`, which deletes the consent answer's audio and transcript and leaves only a note. When testing, never stub `window.confirm` to always return true without also testing a refusal; that stub hid this bug.
- `testclient/no.wav` is a spoken refusal for that test.
- Test client: `testclient/0.wav` to `12.wav` are English answers to the 13 will-intake prompts (consent first), made with the Windows "Zira" voice. To play them: give the page a `MediaStreamDestination` stream as its microphone, watch `#status` for "Escuchando" / "Listening", and play the next clip into that destination each time. A full will intake takes about five and a half minutes with the backup voice.
- The avatar also has `headYaw`, `headPitch`, `headRoll` and `lookX` shape keys (driven from -1 to 1); `window.__pose = [jaw, blink, round, brow, yaw, pitch, roll, look]` freezes all eight.

## Posture and background (2026-11-16)

The source portrait leans about 5 degrees at the shoulders and 10 at the head. `prep_photo.py` rotates the whole photo by `TILT` (-6) before cutting him out, which levels the shoulders without a slanted bottom edge; `make_avatar.py` levels the rest of the head on the neck (`level()`, from the eye-line angle). Photo textures use clamp-to-edge (a wrapped bottom row drew a line over his head). The backdrop has no title bands, heavier blur and lower contrast; a soft `Shadow` quad sits on the wall behind him. Earlier files are in `photos/*-before-straighten.*`.

## Free local voice and transcription (added 2026-11-16)

`VOICE_ENGINE=local` (the default) runs Kokoro (`kokoro-onnx`, Apache 2.0) for the voice and `faster-whisper` for transcription, in the Python 3.11 environment `%USERPROFILE%\avatar-tools\voice-venv` (start.bat and the preview config use it), with models in `%USERPROFILE%\avatar-tools\voices`. `local_tts()` returns the same shape as ElevenLabs' timed reply (WAV instead of MP3), with `rough_alignment()` spreading letters over the voiced part of the clip for the lip shapes. A full English interview ran entirely locally (about 4 s from end of answer to next question on the CPU); Spanish recognition was checked with Kokoro's `em_santa` voice as the client. Do not use Piper `en_US-ryan` (non-commercial licence). Whisper on the GPU (`WHISPER_DEVICE=cuda`) is untested: it needs CUDA 12 cuBLAS/cuDNN DLLs.

## Conflict check (added 2026-11-16)

Every script has a `conflicto` step (`"conflict": true`) right after consent that asks for names only. `/conflict` checks them against `conflicts.csv` (`conflict_hits()`: accent-folded, fuzzy per word, words of a listed name must appear together) and writes `conflict.md`. The page receives only `clear` / `possible` / `no_list`, never matched names: those are other clients' confidential information and the operator's screen is shared over Zoom. A possible conflict, a refusal, or a failure ends the session with no memo, no draft and no further model calls. Conversation mode starts only after the conflict step. The firm must supply `conflicts.csv`; none exists yet.

## What to hand back

A short report: the change, why it was the most valuable one available, exactly how you verified it, what remains unverified, and any decision the attorney or the user must make. No plan documents and no new files that the product does not need.

## Steering back on track (added 2026-11-16)

Conversation mode keeps a checklist of the script's questions. Each model reply ends with a hidden `[DONE: id, ...]` tag; `checklist()` strips it before speech and the covered list only grows. The next `system_prompt(guion, lang, covered)` names the covered ids and the next open question, and tells the model to acknowledge tangents in one sentence and end every turn by steering back to it. The page sends `covered` back and stores `history` (the reply *with* its tag) as the assistant turn: without the tag in the history Beam copies its untagged past turns and stops tagging. The operator bar shows the open ids. Tested with Beam on a client who asked off-topic questions (neighbour's advice, weather, a plumber, refusing to discuss money): it steered back every turn, replies in 1-3 s. Not yet tried in Spanish or by voice.

## Full plan: choose documents, cover each, draft each (added 2026-11-16)

`guion-plan.json` / `guion-plan-en.json` (always conversation mode): consent, conflict check, then a step marked `"choose"` asks which of four documents the client wants. Codes: `will`, `trust`, `poa`, `ahcd` (`DOCS` in server.py). A step with `"doc": [...]` is on the checklist only once one of its documents is chosen (`questions(guion, docs)`); the model reports the choice in a hidden `[DOCS: ...]` tag beside `[DONE: ...]`, the page keeps `docs`, sends it back each turn and saves it in `answers.json`. If the client cannot choose, all four are covered. `drafter(kind)` builds each document's prompt from one template (the will's standards: facts only, `[ATTORNEY TO COMPLETE - ...]`, no execution block, labels added outside the model) plus that document's entry in `DOCS` (what not to infer, what to cover, what to flag), taken from the carbon-law repo's four drafter prompts. `draft_all()` drafts the chosen documents in parallel threads, one retry each. Citations are checked per document: `DOCS[kind]["cites"]` lists the `VERIFIED` sections that document may cite (24 more sections read from leginfo on 2026-11-16: trusts 15200-15402, powers of attorney 4121-4402, health care directives 4659-4701). Section 4401's statutory form text is not on the official site, so the power of attorney draft leaves the form choice to the attorney. The Spanish legal wording of the new questions has not been reviewed by the attorney.

## Full-length instruments (added 2026-11-17)

Kevin found the drafts too short and unprofessional (outlines of about 1,000 words) and chose to have the model write full standard clauses rather than wait for firm templates. `drafter(kind)` now asks for a complete instrument of the length a firm delivers (`DOCS[kind]["pages"]`), in numbered articles (`DOCS[kind]["articles"]`) and numbered sections. Client facts stay facts-only (`DOCS[kind]["facts"]`, `[ATTORNEY TO COMPLETE - ...]`); standard terms the client did not choose are written with the conventional choice inside `[ATTORNEY TO CONFIRM - ...]` (green in Word, yellow stays for missing facts) and listed in the review notes. `draft()` writes each instrument in parts of at most six articles at the same time (`drafter(kind, first, last)`; Beam writes only about 2,500 words per reply), joins them, and builds the list of every `[ATTORNEY TO CONFIRM]` term from the text. `draft_all()` first requires `DOCS[kind]["min"]` words and every article heading, and retries once without those checks. Test client result 2026-11-17: will 11 pages, trust 27, power of attorney 15, health care directive 12, all citations verified, in about 5 minutes. 24 more sections verified on leginfo 2026-11-17 (246, 6120, 8481, 10402-10403, 21310-21311, 15300-15301, 16000, 16040, 16061.7, 16200, 4126-4127, 4203-4206, 4303, 4680-4686). `docx()` adds a header, "Page X of Y" footer, centred article headings, first-line indents. The standard clause wording is model-written: the attorney must review all of it, and firm templates would still be better.

## Calavera avatar (added 2026-11-17)

`?avatar=calavera` loads `calavera.glb` instead of `avatar.glb`: a flat 2D Day of the Dead skull in a suit and sombrero, papel picado backdrop. Art: `calavera_art.py` (PIL, avatar-tools venv) writes `calavera.png`, `calavera-bg.png` and `calavera.json` (where the jaw, eyes, pupils, brows and neck are). Model: `blender -b -P make_calavera.py` makes a 320x320 sheet with the same shape keys as Pankaj, so the page animates it unchanged; the jaw opens by stretching the dark gap between the teeth, the blink squashes each socket, lookX slides the pupils inside the plain dark sockets. With the calavera the consent line drops "con su imagen" / "that uses his likeness" and the chat prompt says it appears as a calavera. Desktop shortcut **Calavera Demo** (Spanish full plan).
