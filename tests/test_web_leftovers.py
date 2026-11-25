"""web/ is edited by hand and once by shell heredocs. Leftover heredoc lines ("CSS", "echo done") broke styles.css
(the next rule was dropped, so the main buttons lost their fill) and printed "CSS" at the bottom of five pages."""
import glob
import os
import re

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
LEFTOVER = re.compile(r"^\s*(?:[A-Z]{2,}|echo\b.*|cat\s*<<.*)\s*$")    # a bare heredoc tag (CSS, EOF), an echo, a cat <<


def files(pattern):
    return sorted(glob.glob(os.path.join(WEB, pattern)))


def test_nothing_follows_the_closing_html_tag():
    for path in files("*.html"):
        text = open(path, encoding="utf-8").read()
        assert text.rstrip().endswith("</html>"), f"{os.path.basename(path)} has text after </html>"


def test_no_shell_leftovers_in_web_pages_or_the_stylesheet():
    for path in files("*.html") + [os.path.join(WEB, "styles.css")]:
        for number, line in enumerate(open(path, encoding="utf-8"), 1):
            assert not LEFTOVER.match(line), f"{os.path.basename(path)}:{number} looks like a shell leftover: {line.strip()!r}"
