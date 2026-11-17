"""Markdown -> .docx for carbon_intake (stdlib only)."""
import io, re, zipfile
from xml.sax.saxutils import escape
from .drafting import BANNER


def docx(md, name="document"):
    """The draft's simple markdown -> a Word file, standard library only. Times New Roman 12 pt, 1-inch margins.
    "# " title (starts a new page, so the review notes are a cover sheet), "## " article headings centred,
    "### " sub-headings, "- " bullets, **bold**; [ATTORNEY TO COMPLETE ...] highlighted yellow and
    [ATTORNEY TO CONFIRM ...] green; a header with the draft label and a footer with "Page X of Y".
    ponytail: direct formatting, no Word styles; use python-docx if the firm wants its own template."""
    font = '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>'

    def runs(text, bold=False, size=24, color="", caps=False):
        out = []
        for i, part in enumerate(text.split("**")):
            for piece in re.split(r"(\[[^\]]*\])", part):
                if piece:
                    mark = ('<w:highlight w:val="green"/>' if piece.startswith("[ATTORNEY TO CONFIRM") else
                            '<w:highlight w:val="yellow"/>' if piece.startswith("[") else "")
                    out.append(f'<w:r><w:rPr>{font}{"<w:b/>" if bold or i % 2 else ""}{"<w:caps/>" if caps else ""}'
                               f'{color}<w:sz w:val="{size}"/>{mark}</w:rPr><w:t xml:space="preserve">{escape(piece)}</w:t></w:r>')
        return "".join(out)
    field = lambda f: (f'<w:r><w:rPr>{font}<w:sz w:val="20"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
                       f'<w:r><w:rPr>{font}<w:sz w:val="20"/></w:rPr><w:instrText xml:space="preserve"> {f} </w:instrText></w:r>'
                       f'<w:r><w:rPr>{font}<w:sz w:val="20"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r>')
    paras = [('<w:jc w:val="center"/>', runs(BANNER, True, 22, '<w:color w:val="C00000"/>'))]
    for line in md.splitlines():
        line = line.strip()
        if not line or line in ("---", f"**{BANNER}**"):
            continue
        if line.startswith("# "):   # the instrument starts on its own page, after the review notes
            paras.append(('<w:pageBreakBefore/><w:jc w:val="center"/><w:spacing w:before="480" w:after="480"/>',
                          runs(line[2:], True, 28, caps=True)))
        elif line.startswith("## ") and line[3:].upper().startswith(("ARTICLE", "PART", "SCHEDULE")):
            paras.append(('<w:keepNext/><w:jc w:val="center"/><w:spacing w:before="360" w:after="180"/>',
                          runs(line[3:], True, 24, caps=True)))
        elif line.startswith(("## ", "### ")):
            paras.append(('<w:keepNext/><w:spacing w:before="240" w:after="120"/>', runs(line.lstrip("# "), True, 24)))
        elif line.startswith(("- ", "* ")):
            paras.append(('<w:ind w:left="720" w:hanging="360"/><w:spacing w:after="80"/>', runs("\u2022\t" + line[2:])))
        else:
            paras.append(('<w:spacing w:after="200" w:line="360" w:lineRule="auto"/><w:ind w:firstLine="720"/><w:jc w:val="both"/>',
                          runs(line)))
    body = "".join(f"<w:p><w:pPr>{ppr}</w:pPr>{r}</w:p>" for ppr, r in paras)
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    red, label = '<w:color w:val="C00000"/>', runs(name.title() + "  \u2014  Page ", size=20)   # no backslash in f-strings on 3.11
    header = f'{xml}<w:hdr xmlns:w="{W}"><w:p><w:pPr><w:jc w:val="right"/></w:pPr>{runs(BANNER, False, 18, red)}</w:p></w:hdr>'
    footer = (f'{xml}<w:ftr xmlns:w="{W}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
              f'{label}{field("PAGE")}{runs(" of ", size=20)}{field("NUMPAGES")}</w:p></w:ftr>')
    files = {
        "[Content_Types].xml": f'{xml}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
            '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>',
        "_rels/.rels": f'{xml}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/_rels/document.xml.rels": f'{xml}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rIdH" Type="{R}/header" Target="header1.xml"/><Relationship Id="rIdF" Type="{R}/footer" Target="footer1.xml"/></Relationships>',
        "word/header1.xml": header,
        "word/footer1.xml": footer,
        "word/document.xml": f'{xml}<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>{body}'
            '<w:sectPr><w:headerReference w:type="default" r:id="rIdH"/><w:footerReference w:type="default" r:id="rIdF"/>'
            '<w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
            '</w:body></w:document>',
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for part, data in files.items():
            z.writestr(part, data)
    return buf.getvalue()


