"""Pre-render a lip-synced talking video for every script line.
Run:  python render.py            (all guion*.json)   or   python render.py guion-fideicomiso
Re-run after editing a script; lines whose text did not change are skipped.

Needs: ElevenLabs key in .env, ffmpeg on PATH, and SadTalker + its Python env in
%USERPROFILE%\\avatar-tools (face-animation model, runs on the local NVIDIA GPU).
"""
import json, subprocess, sys, tempfile, wave
from pathlib import Path
from server import ROOT, tts

TOOLS = Path.home() / "avatar-tools"
PY, SAD = TOOLS / "venv" / "Scripts" / "python.exe", TOOLS / "SadTalker"
PHOTO = ROOT / "pankaj.jpg"
VIDEO = ROOT / "video"


def animate(audio, out):
    """Photo + audio -> talking-head mp4 that browsers can play."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([PY, "inference.py", "--driven_audio", audio, "--source_image", PHOTO,
                        "--result_dir", tmp, "--still", "--preprocess", "full", "--enhancer", "gfpgan"],
                       cwd=SAD, check=True)
        made = max(Path(tmp).glob("*.mp4"), key=lambda p: p.stat().st_mtime)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", made, "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", out], check=True)


def render(name):
    d = VIDEO / name
    d.mkdir(parents=True, exist_ok=True)
    for step in json.loads((ROOT / f"{name}.json").read_text(encoding="utf-8")):
        mp4, txt = d / f"{step['id']}.mp4", d / f"{step['id']}.txt"
        if mp4.exists() and txt.exists() and txt.read_text(encoding="utf-8") == step["say"]:
            continue
        print(f"rendering {name}/{step['id']} ...", flush=True)
        mp3, wav = d / "_tmp.mp3", d / "_tmp.wav"
        mp3.write_bytes(tts(step["say"]))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, wav], check=True)
        animate(wav, mp4)
        txt.write_text(step["say"], encoding="utf-8")  # written last: a crashed render is redone
        mp3.unlink(), wav.unlink()


def idle():
    """Silent clip (blinks, small movements) looped while the avatar listens."""
    out = VIDEO / "idle.mp4"
    if out.exists():
        return
    print("rendering idle ...", flush=True)
    VIDEO.mkdir(exist_ok=True)
    wav = VIDEO / "_silence.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000)
        w.writeframes(b"\0\0" * 16000 * 8)
    animate(wav, out)
    wav.unlink()


if __name__ == "__main__":
    idle()
    for name in sys.argv[1:] or sorted(p.stem for p in ROOT.glob("guion*.json")):
        render(name)
    print("done")
