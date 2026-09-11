# Kindle EPUB

A zero-dependency Python command-line tool for turning UTF-8 Markdown into Kindle-ready EPUB 3 books. It supports Chinese, English, and bilingual books.

## 使用

```bash
python3 kindle_epub.py build example.md book.epub --title "我的第一本书 || My First Book" --author "作者名 || Author Name" --language bilingual
python3 kindle_epub.py validate book.epub
```

Markdown 支持：`#` 或 `##` 章节标题、普通段落、`-`/`*` 无序列表、`**加粗**`、`*斜体*` 和 `> 引用`。使用 `中文 || English` 将两种语言排在同一段中；标题、作者、正文和列表都支持这种格式。

For an English-only book, use `--language en`. For bilingual text, write the Chinese and English versions on one line separated by `||`, then use `--language bilingual`.

## 设计取舍

- 只使用 Python 标准库，不需要安装依赖。
- `mimetype` 按 EPUB 规范以未压缩方式写入。
- `validate` 会检查 ZIP、必需文件、OPF XML 和 manifest 引用。
- `--language` 支持 `zh-CN`、`en` 和 `bilingual`，默认保持中文单语模式。
- 当前不内置封面图片；Kindle 会使用书名页作为内容首页。