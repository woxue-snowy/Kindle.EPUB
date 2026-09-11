# Kindle Bilingual EPUB Studio 

An automated Python tool that transforms any raw `.txt` or `.zip` text file into a Kindle-ready bilingual EPUB book, featuring real-time translation and a clean **top-English, bottom-Chinese** vertical layout.

## Core Features

* **Universal Input**: No need to manually write Markdown. Directly accepts raw `.txt` files or `.zip` archives containing multi-chapter texts.
* **Smart Automated Translation**: Powered by a free translation engine, it automatically detects source language and translates paragraphs line-by-line for bilingual comparison.
* **Vertical Bilingual Layout**: Implements a refined HTML/Markdown hybrid structure to provide a comfortable **top-English, bottom-Chinese** reading experience.
* **Native EPUB 3 Standards**: Built on pure Python with zero heavy dependencies, ensuring seamless Kindle compatibility.

## Installation & Setup

Ensure Python 3 is installed on your system, then install the required translation library via terminal:

```bash
pip3 install deep-translator

```

## Usage

Place the core script (`kindle_epub.py`) and the automation script (`auto_bilingualtranslate.py`) in the same folder, then run the following command in your terminal:

```bash
python3 auto_bilingualtranslate.py your_book.txt

```

Alternatively, pass in a `.zip` archive:

```bash
python3 auto_bilingualtranslate.py your_chapters.zip

```

Once execution completes, a polished `yourbook__bilingual.epub` file will be generated in your directory, ready to be transferred straight to your Kindle.
