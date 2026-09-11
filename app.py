import os
import glob
import shutil
import zipfile
import tempfile
import subprocess
import sys

import streamlit as st

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None


# -------------------------
# 基础工具
# -------------------------

def detect_language(text):
    """简单判断文本主要是中文还是英文"""
    sample = text[:1000]
    chinese_count = sum(
        1 for c in sample
        if "\u4e00" <= c <= "\u9fff"
    )

    return "zh" if chinese_count > 20 else "en"


def is_chapter_title(line):
    """识别常见章节标题"""
    line = line.strip()

    if line.startswith("第") and (
        "章" in line[:15] or
        "节" in line[:15] or
        "卷" in line[:15]
    ):
        return True

    lower = line.lower()

    if lower.startswith("chapter ") and len(line) < 60:
        return True

    return False


def clean_text(text):
    """普通 EPUB 模式：清理文本并转换成 Markdown"""
    output = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        if is_chapter_title(line):
            output.append(f"\n# {line}\n")
        else:
            output.append(line + "\n")

    return "\n".join(output)


# -------------------------
# 双语翻译
# -------------------------

def bilingual_text(text, progress_callback=None):

    if GoogleTranslator is None:
        raise RuntimeError(
            "没有安装 deep-translator。\n"
            "请运行：pip install deep-translator"
        )

    language = detect_language(text)

    if language == "zh":
        target = "en"
    else:
        target = "zh-CN"

    translator = GoogleTranslator(
        source="auto",
        target=target
    )

    paragraphs = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    output = []

    total = len(paragraphs)

    for index, paragraph in enumerate(paragraphs):

        if progress_callback:
            progress_callback(
                (index + 1) / total
            )

        # 标题暂时不翻译
        if is_chapter_title(paragraph):

            output.append(
                f"\n# {paragraph}\n"
            )

            continue

        try:

            translated = translator.translate(
                paragraph[:4900]
            )

            if not translated:
                translated = ""

            # 永远保持：
            # 英文在上
            # 中文在下

            if language == "zh":

                english = translated
                chinese = paragraph

            else:

                english = paragraph
                chinese = translated

            output.append(
                f"""
<div class="bilingual">
<p class="english">{english}</p>
<p class="chinese">{chinese}</p>
</div>

"""
            )

        except Exception:

            # 翻译失败也不要让整本书失败
            output.append(
                f"<p>{paragraph}</p>\n"
            )

    return "".join(output)


# -------------------------
# 文件读取
# -------------------------

def read_uploaded_file(uploaded_file):

    filename = uploaded_file.name

    extension = os.path.splitext(
        filename
    )[1].lower()

    temp_dir = tempfile.mkdtemp()

    input_path = os.path.join(
        temp_dir,
        filename
    )

    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:

        # TXT / Markdown
        if extension in [".txt", ".md"]:

            with open(
                input_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as f:

                return f.read()

        # ZIP
        if extension == ".zip":

            extract_dir = os.path.join(
                temp_dir,
                "book"
            )

            os.makedirs(
                extract_dir,
                exist_ok=True
            )

            with zipfile.ZipFile(
                input_path,
                "r"
            ) as zip_file:

                zip_file.extractall(
                    extract_dir
                )

            files = []

            files.extend(
                glob.glob(
                    os.path.join(
                        extract_dir,
                        "**/*.txt"
                    ),
                    recursive=True
                )
            )

            files.extend(
                glob.glob(
                    os.path.join(
                        extract_dir,
                        "**/*.md"
                    ),
                    recursive=True
                )
            )

            files = sorted(files)

            if not files:
                raise RuntimeError(
                    "ZIP 里面没有找到 txt 或 md 文件。"
                )

            contents = []

            for file in files:

                with open(
                    file,
                    "r",
                    encoding="utf-8",
                    errors="ignore"
                ) as f:

                    contents.append(
                        f.read()
                    )

            return "\n\n".join(contents)

        raise RuntimeError(
            "只支持 .txt、.md 和 .zip"
        )

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# -------------------------
# EPUB 生成
# -------------------------

def build_epub(
    markdown_text,
    title,
    author
):

    temp_dir = tempfile.mkdtemp()

    try:

        md_path = os.path.join(
            temp_dir,
            "book.md"
        )

        output_path = os.path.join(
            temp_dir,
            "book.epub"
        )

        with open(
            md_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(markdown_text)

        kindle_script = os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)
            ),
            "kindle_epub.py"
        )

        if not os.path.exists(
            kindle_script
        ):
            raise RuntimeError(
                "找不到 kindle_epub.py。\n"
                "请把 app.py 和 kindle_epub.py "
                "放在同一个文件夹。"
            )

        command = [
            sys.executable,
            kindle_script,
            "build",
            md_path,
            output_path,
            "--title",
            title,
            "--author",
            author,
        ]

        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        with open(
            output_path,
            "rb"
        ) as f:

            return f.read()

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# -------------------------
# 网页
# -------------------------

st.set_page_config(
    page_title="Kindle EPUB Maker",
    page_icon="📖",
    layout="centered"
)

st.title("📖 Kindle EPUB Maker")

st.write(
    "把小说丢进来，自动生成 Kindle EPUB。"
)

uploaded_file = st.file_uploader(
    "上传小说",
    type=[
        "txt",
        "md",
        "zip"
    ]
)

bilingual = st.toggle(
    "🌏 生成中英双语版",
    value=True
)

with st.expander(
    "高级设置"
):

    custom_title = st.text_input(
        "书名（留空自动使用文件名）"
    )

    author = st.text_input(
        "作者",
        value="Unknown"
    )


if uploaded_file:

    filename = os.path.splitext(
        uploaded_file.name
    )[0]

    title = (
        custom_title.strip()
        or filename
    )

    st.success(
        f"已选择：{uploaded_file.name}"
    )

    if st.button(
        "✨ 生成 EPUB",
        type="primary",
        use_container_width=True
    ):

        try:

            with st.spinner(
                "正在读取小说..."
            ):

                raw_text = read_uploaded_file(
                    uploaded_file
                )

            if bilingual:

                progress = st.progress(0)

                status = st.empty()

                status.write(
                    "🌏 正在生成中英双语版本..."
                )

                def update_progress(value):
                    progress.progress(
                        min(
                            int(value * 100),
                            100
                        )
                    )

                markdown = bilingual_text(
                    raw_text,
                    update_progress
                )

                progress.progress(100)

                output_name = (
                    f"{filename}_bilingual.epub"
                )

            else:

                markdown = clean_text(
                    raw_text
                )

                output_name = (
                    f"{filename}.epub"
                )

            with st.spinner(
                "📚 正在制作 EPUB..."
            ):

                epub = build_epub(
                    markdown,
                    title,
                    author
                )

            st.success(
                "🎉 EPUB 已生成！"
            )

            st.download_button(
                "⬇️ 下载 EPUB",
                data=epub,
                file_name=output_name,
                mime="application/epub+zip",
                use_container_width=True
            )

        except Exception as error:

            st.error(
                f"生成失败：{error}"
            )


st.divider()

st.caption(
    "TXT / Markdown / ZIP → Kindle EPUB"
)
