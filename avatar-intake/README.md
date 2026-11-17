# Attorney avatar — operator guide

A talking avatar of attorney Pankaj Raval that explains estate planning in Spanish or English, interviews the client, and saves the recording and transcript for the attorney.

> In the public carbon-law repository this folder has no keys, no interview sessions and no photos or face model of the attorney (see `.gitignore`). The calavera works out of the box; the photo avatar needs `pankaj2.png` from the firm, then `prep_photo.py` and `make_avatar.py`.

> These Zoom steps have not yet been proven on a real call. Do a practice call with a colleague before using it with a client.

## Start

1. Double-click **Pankaj Avatar Demo** on the desktop (it opens the full plan in English), or `start.bat` here (the Spanish will intake). A minimised "Avatar server" window starts (leave it open; close it to stop) and the default browser opens the page once the server is ready. Running it again while the server is up just opens the page.
   **Calavera Demo** on the desktop opens the same full plan in Spanish with a cheerful 2D Day of the Dead skull in a sombrero instead of the photo of Pankaj (add `&avatar=calavera` to any page address). The calavera tells the client it is an AI program but does not claim to be his likeness.
2. Pick the version in the drop-down at the bottom left; Spanish or English:
   - **Plan completo / Full plan** — the main one. After consent and the conflict check, the avatar asks which documents the client wants (will, living trust, financial power of attorney, health care directive), goes through each chosen document in turn, and a first draft of each is written afterwards. Needs the model key.
   - Will intake (fixed questions), trust walkthrough (explanation only), free conversation (will questions).

## On a Zoom call

1. Join the Zoom meeting on this PC. Use headphones, so the avatar does not hear itself.
2. In Zoom: **Share Screen**, choose the Chrome window with the avatar, and tick **Share sound**. The client now sees and hears the avatar.
3. On the avatar page click **Llamada de Zoom** / **Zoom call**. Chrome asks what to share: choose **Entire screen** and tick **Also share system audio**. This is how the page hears the client.
4. The avatar introduces itself, says it is an AI and asks permission to record. If the client says no, it stops and deletes the recording of that answer. If the answer is unclear (for example "no, no acepto" or silence), a box asks **you** whether the client agreed: click **OK** only if you clearly heard yes; **Cancel** stops the interview.
5. The pill over the avatar shows what it is doing: listening, transcribing, thinking.
6. In free conversation, the client can wander off topic or ask questions; the avatar answers briefly and always brings them back to the next question it still needs. The bar at the bottom shows you **Still to ask:** with the questions not yet covered.

While it runs:

- **Siguiente ▶ / Next ▶** skips the line being spoken, or ends listening if the avatar is waiting too long.
- **Umbral de voz / Voice threshold**: if the avatar cuts people off, slide left; if it never stops listening (noisy line), slide right. The **Nivel / Level** bar should jump when the client talks.
- The avatar moves on after about 2.5 seconds of silence.

To test alone, without Zoom: the page asks for the microphone as soon as it opens. Click **Allow**; the avatar starts speaking 7 seconds later (**Siguiente ▶ / Next ▶** starts at once). If Chrome wants a click before it plays sound, the page says so: click anywhere. If you dismissed the request, click **Probar con micrófono** / **Test with microphone**.

For a Zoom call, open the page with `?zoom=1` added to the address (for example `http://localhost:8765/?zoom=1`) so it does not take the microphone; Chrome only lets screen and system-audio sharing start from a click on **Llamada de Zoom** / **Zoom call**.

## Conflict check

Right after the client agrees to be recorded, the avatar asks for **names only** (the client, spouse or partner, children, and anyone else in the plan) and checks them against `conflicts.csv` in this folder before asking anything else.

- `conflicts.csv`: one name per row in the first column (current and former clients, adverse parties); a first row reading `name` is ignored. Export it from the firm's matter list and keep it current. Names of two or more words are checked; spelling slips like Mendez/Mendes still match.
- **Possible match:** the avatar thanks the client, says the office will be in touch, and stops. It never says why. Nothing further is collected or sent anywhere. The match is written only to `conflict.md` in the session folder.
- **No `conflicts.csv`:** a box asks you whether the firm has already cleared this client. **OK** continues; **Cancel** stops the same way.
- `conflict.md` in every session records the names given and the result. The automatic check compares names only, so still run the firm's own check on those names.

## After the call

Each interview is a folder in `sessions`, named by date and time:

- `intake.md` — every question and the transcribed answer
- `summary.md` — a memo for the attorney (only when the model key is set)
- `draft-will.docx`, `draft-trust.docx`, `draft-poa.docx`, `draft-ahcd.docx` (each also as `.md`) — a first draft of every document the client chose (will; revocable living trust; durable power of attorney for financial matters; advance health care directive), for the attorney to edit in Word, written to Carbon Law Group's drafting rules. Each is a complete instrument in numbered articles with every standard provision written out (for example a will of about 10–15 pages), with a page header and page numbers. The first pages are the attorney's review notes; the instrument starts on a new page. A fact the client did not give is a yellow `[ATTORNEY TO COMPLETE - ...]`; a standard term the client did not choose (a survivorship period, bond waiver, compensation, an age) is written with the usual California choice in a green `[ATTORNEY TO CONFIRM - ...]`, and each is listed in the review notes. The standard wording is written by the AI, not taken from a firm form, so the attorney must review every clause. None has a signature, witness or notary block, on purpose; each is marked DRAFT — FOR ATTORNEY REVIEW — NOT FOR SIGNING and is never to be given to the client or signed as it stands. A line at the top says whether every statute it cites is on the list checked against the official California code for that kind of document. When the client asks for a trust and a will, the will is drafted as a pour-over will. Needs the model key. To make them again, or for an older interview, run `python server.py --draft <session folder name>`; add the documents to choose them yourself, for example `python server.py --draft <session folder name> will,poa` (codes: `will`, `trust`, `poa`, `ahcd`).
- `draft-<document>.ai-record.json` — which AI model wrote each draft and when, with fingerprints (hashes) of what it was given and what it returned. No client information is in it.
- one `.webm` audio file per answer — check names, dates and amounts against these before drafting

## Voice and transcription

By default both run free on this PC, with no ElevenLabs account:

- **Voice:** two free engines that run on this PC, both allowed for commercial use: Spanish is Piper `es_MX-ald-medium` (Mexican accent; public-domain training data), English is Kokoro `am_adam` (Apache 2.0). Chosen by Kevin on 2026-11-16 from the samples in `voice-samples` (open `listen.html` there to hear them). To change, add a line to `.env`, for example `LOCAL_VOICE_ES=kokoro:em_alex` or `LOCAL_VOICE_EN=kokoro:am_michael`.
- **Transcription:** Whisper `small`, on the processor. `WHISPER_MODEL=medium` hears names better but is slower.
- Needs the Python environment in `%USERPROFILE%\avatar-tools\voice-venv` and the model files in `%USERPROFILE%\avatar-tools\voices`; `start.bat` uses them automatically.
- To go back to ElevenLabs, put `VOICE_ENGINE=elevenlabs` in `.env` (needs `ELEVENLABS_API_KEY` with credits).

## Keys

Put these in the `.env` file in this folder, one per line, then restart:

- `REFLECTION_API_KEY=` (Beam, the same model the Carbon Law backend uses) or `ANTHROPIC_API_KEY=` (Claude) — the model behind the free conversation, the attorney memo and the draft will. Beam is used when its key is set. Without either, use the scripted versions.
- `ELEVENLABS_API_KEY=` — only if you switch the voice back to ElevenLabs.

## Where client information goes

Approved by the firm on 2026-11-15 (relayed by Kevin): client interviews may be processed by the hosted services below. This replaces, for this tool, the Carbon Law repo's default rule against hosted processing of real client data.

| Goes to | What | Why |
|---|---|---|
| Reflection AI, Beam (api.reflection.ai) | the text transcript only, no audio | conversation mode, the attorney memo, the draft will |
| Stays on this PC only | all audio (voice and transcription run here since 2026-11-16), `answers.json`, `intake.md`, `conflict.md`, `summary.md`, the draft will | the `sessions` folder; the page never serves it |
| ElevenLabs (elevenlabs.io) | nothing, unless `VOICE_ENGINE=elevenlabs` is set; then each answer's audio and every spoken line | the older voice and transcription option |

- If a client says no to recording, nothing of theirs is kept. With the default local transcription their answer never leaves this PC.
- A possible conflict of interest stops the interview before anything is sent to Beam.
- Not done yet: settings for how long Reflection keeps data, and a retention period for the `sessions` folder. The firm should decide these.
- Use only keys on the firm's own accounts, not personal or throwaway keys, once real clients are interviewed.

## Changing what it says

Edit the `guion*.json` files (the `say` lines). The full plan is `guion-plan.json` (Spanish) and `guion-plan-en.json` (English); a question marked `"doc"` is asked only when the client chose one of those documents. The attorney should approve any change to legal wording.

For developers and other AI assistants: see `IMPROVE_PROMPT.md`.
