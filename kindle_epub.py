#!/usr/bin/env python3
"""Build and validate simple, Kindle-friendly EPUB 3 books."""

from __future__ import annotations

import argparse
import html
import re
import sys
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET


CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
"""

CSS = """body { font-family: serif; line-height: 1.55; margin: 5%; }
h1 { font-size: 1.8em; margin: 2em 0 1em; text-align: center; }
h2 { font-size: 1.35em; margin-top: 1.6em; }
p { margin: 0 0 0.9em; text-indent: 1.5em; }
li p { text-indent: 0; }
.bilingual { display: block; }
.bilingual + .bilingual { margin-top: 0.35em; }
.english { font-style: italic; }
.title-page { text-align: center; margin-top: 28%; }
.title-page h1 { font-size: 2.3em; }
.author { font-size: 1.2em; }
"""


@dataclass
class Chapter:
    title: str
    paragraphs: list[str]


def inline_markup(value: str) -> str:
    """Escape text first, then support a small, safe Markdown subset."""
    if "||" in value:
        chinese, english = (part.strip() for part in value.split("||", 1))
        return (
            f'<span class="bilingual chinese">{inline_markup(chinese)}</span>'
            f'<span class="bilingual english">{inline_markup(english)}</span>'
        )
    value = html.escape(value, quote=False)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"\*(.+?)\*", r"<em>\1</em>", value)
    return value


def parse_markdown(source: str, fallback_title: str = "正文") -> list[Chapter]:
    chapters: list[Chapter] = []
    current_title = fallback_title
    blocks: list[str] = []
    list_items: list[str] = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{inline_markup(item)}</li>" for item in list_items) + "</ul>")
            list_items = []

    def flush_chapter() -> None:
        nonlocal blocks, current_title
        flush_list()
        if blocks:
            chapters.append(Chapter(current_title, blocks))
        blocks = []

    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line:
            flush_list()
            continue
        heading = re.match(r"^#{1,2}\s+(.+)$", line)
        if heading:
            flush_chapter()
            current_title = heading.group(1).strip()
        elif re.match(r"^[-*]\s+", line):
            list_items.append(re.sub(r"^[-*]\s+", "", line))
        else:
            flush_list()
            if line.startswith("> "):
                blocks.append(f"<blockquote>{inline_markup(line[2:])}</blockquote>")
            else:
                blocks.append(f"<p>{inline_markup(line)}</p>")
    flush_chapter()
    if not chapters:
        chapters.append(Chapter(fallback_title, []))
    return chapters


def document(title: str, author: str, body: str, language: str, heading: str | None = None) -> str:
    heading = heading or title
    html_language = "zh-CN" if language == "bilingual" else language
    return f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{html_language}">
<head><title>{html.escape(title)}</title><link rel="stylesheet" href="../styles/book.css" type="text/css" /></head>
<body><h1>{inline_markup(heading)}</h1>{body}</body>
</html>'''


def title_page(title: str, author: str, language: str) -> str:
    html_language = "zh-CN" if language == "bilingual" else language
    return f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{html_language}">
<head><title>{html.escape(title)}</title><link rel="stylesheet" href="../styles/book.css" type="text/css" /></head>
<body><section class="title-page"><h1>{inline_markup(title)}</h1><p class="author">{inline_markup(author)}</p></section></body>
</html>'''


def build_epub(input_path: Path, output_path: Path, title: str, author: str, language: str = "zh-CN") -> None:
    chapters = parse_markdown(input_path.read_text(encoding="utf-8"), title)
    book_id = f"urn:uuid:{uuid4()}"
    created = date.today().isoformat()
    manifest = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="css" href="styles/book.css" media-type="text/css"/>',
    ]
    spine = ['<itemref idref="title-page"/>']
    nav_links = ['<li><a href="text/title-page.xhtml">封面</a></li>']
    documents = {"EPUB/text/title-page.xhtml": title_page(title, author, language)}
    manifest.append('<item id="title-page" href="text/title-page.xhtml" media-type="application/xhtml+xml"/>')
    for index, chapter in enumerate(chapters, 1):
        item_id = f"chapter-{index}"
        href = f"text/chapter-{index}.xhtml"
        manifest.append(f'<item id="{item_id}" href="{href}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="{item_id}"/>')
        nav_links.append(f'<li><a href="{href}">{inline_markup(chapter.title)}</a></li>')
        documents[f"EPUB/{href}"] = document(title, author, "".join(chapter.paragraphs), language, chapter.title)

    language_metadata = "<dc:language>zh-CN</dc:language><dc:language>en</dc:language>" if language == "bilingual" else f"<dc:language>{language}</dc:language>"
    package = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="book-id">{book_id}</dc:identifier><dc:title>{html.escape(title)}</dc:title>
<dc:creator>{html.escape(author)}</dc:creator>{language_metadata}<meta property="dcterms:modified">{created}T00:00:00Z</meta>
</metadata><manifest>{''.join(manifest)}</manifest><spine>{''.join(spine)}</spine>
</package>'''
    nav = f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">
<head><title>目录</title></head><body><nav epub:type="toc" id="toc"><h1>目录</h1><ol>{''.join(nav_links)}</ol></nav></body></html>'''
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w") as archive:
        info = zipfile.ZipInfo("mimetype")
        info.compress_type = zipfile.ZIP_STORED
        archive.writestr(info, "application/epub+zip")
        archive.writestr("META-INF/container.xml", CONTAINER_XML)
        archive.writestr("EPUB/package.opf", package)
        archive.writestr("EPUB/nav.xhtml", nav)
        archive.writestr("EPUB/styles/book.css", CSS)
        for path, content in documents.items():
            archive.writestr(path, content)


def validate_epub(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if archive.read("mimetype").decode() != "application/epub+zip":
                errors.append("mimetype 内容错误")
            if archive.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
                errors.append("mimetype 必须未压缩")
            required = {"mimetype", "META-INF/container.xml", "EPUB/package.opf", "EPUB/nav.xhtml"}
            errors.extend(f"缺少文件: {name}" for name in sorted(required - names))
            if "EPUB/package.opf" in names:
                root = ET.fromstring(archive.read("EPUB/package.opf"))
                namespace = {"opf": "http://www.idpf.org/2007/opf"}
                for item in root.findall("opf:manifest/opf:item", namespace):
                    if f"EPUB/{item.attrib['href']}" not in names:
                        errors.append(f"清单引用不存在: {item.attrib['href']}")
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        errors.append(f"无法读取 EPUB: {exc}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="将 Markdown 文稿制作成 Kindle 友好的 EPUB 3 文件")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="生成 EPUB")
    build.add_argument("input", type=Path, help="UTF-8 Markdown 文稿")
    build.add_argument("output", type=Path, help="输出 .epub 文件")
    build.add_argument("--title", required=True, help="书名")
    build.add_argument("--author", default="未知作者", help="作者")
    build.add_argument("--language", choices=("zh-CN", "en", "bilingual"), default="zh-CN", help="书籍语言")
    validate = subparsers.add_parser("validate", help="检查 EPUB 包结构")
    validate.add_argument("epub", type=Path)
    args = parser.parse_args(argv)
    if args.command == "build":
        build_epub(args.input, args.output, args.title, args.author, args.language)
        print(f"已生成: {args.output}")
        return 0
    errors = validate_epub(args.epub)
    if errors:
        print("EPUB 校验失败:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"EPUB 校验通过: {args.epub}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
if __name__ == "__main__":
    raise SystemExit(main())