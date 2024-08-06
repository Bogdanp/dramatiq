import os
import xml.etree.ElementTree as ET
from datetime import datetime


def setup(app):
    app.connect("build-finished", build_sitemap)
    return {"version": "1.0"}


def collect_pages(basedir):
    for root, _dirs, files in os.walk(basedir):
        for filename in files:
            if not filename.endswith(".html"):
                continue

            if filename == "index.html":
                filename = ""

            priority = 0.8
            if "genindex" in filename or "modindex" in filename:
                priority = 0.4
            elif "_modules" in root:
                priority = 0.6
            elif filename == "":
                priority = 1

            path = os.path.join(root, filename)
            stat = os.stat(path)
            last_mod = datetime.fromtimestamp(stat.st_mtime).date().isoformat()

            page_path = path[len(basedir):].lstrip("/")
            yield page_path, last_mod, priority


def build_sitemap(app, exception):
    pages = collect_pages(app.outdir)
    root = ET.Element("urlset")
    root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    for page, mod, prio in sorted(pages, key=lambda t: -t[2]):
        url = ET.SubElement(root, "url")
        loc = ET.SubElement(url, "loc")
        lastmod = ET.SubElement(url, "lastmod")
        priority = ET.SubElement(url, "priority")
        loc.text = f"https://dramatiq.io/{page}"
        lastmod.text = mod
        priority.text = f"{prio:.02f}"

    filename = f"{app.outdir}/sitemap.xml"
    tree = ET.ElementTree(root)
    tree.write(filename, xml_declaration=True, encoding="utf-8", method="xml")
