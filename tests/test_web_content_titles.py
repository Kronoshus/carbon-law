"""web/content-titles.js is generated from aprende/content. This fails when the content changed and the file was not rebuilt."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_content_titles_match_the_content():
    spec = importlib.util.spec_from_file_location("build_content_titles", ROOT / "scripts" / "build-content-titles.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    current = (ROOT / "web" / "content-titles.js").read_text(encoding="utf-8")
    assert current == build.build(), "web/content-titles.js is out of date: run python scripts/build-content-titles.py"
