"""The staff admin loads several plain scripts into one global scope. A top-level name defined twice silently
replaces the first one (content.js's `api` replaced auth.js's for the whole admin), so every script admin.html loads must
keep its own names private."""
import os
import re

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
TOP = re.compile(r"^(?:const|let|var|function|async function|class)\s+([A-Za-z_$][\w$]*)", re.M)


def scripts(page):
    html = open(os.path.join(WEB, page), encoding="utf-8").read()
    return re.findall(r'<script src="([\w.-]+\.js)"', html)


def test_no_two_admin_scripts_define_the_same_global_name():
    seen = {}
    for name in scripts("admin.html"):
        for ident in TOP.findall(open(os.path.join(WEB, name), encoding="utf-8").read()):
            assert ident not in seen, f"{ident} is defined in both {seen[ident]} and {name}"
            seen[ident] = name
