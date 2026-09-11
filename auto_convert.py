import os
import sys
import zipfile
import tempfile
import subprocess
import glob

def clean_text_to_markdown(raw_text):
    """简单的文本清洗：将普通文本转为合规的Markdown段落"""
    lines = raw_text.splitlines()
    md_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 简单识别常见的章节标题（如 第1章、Chapter 1 等），自动加 #
        if line.startswith("第") and ("章" in line[:10] or "节" in line[:10]):
            md_lines.append(f"\n# {line}\n")
        elif line.lower().startswith("chapter ") and len(line) < 30:
            md_lines.append(f"\n# {line}\n")
        else:
            md_lines.append(line + "\n")
    return "\n".join(md_lines)

def process_input(input_path):
    if not os.path.exists(input_path):
        print(f"错误: 找不到文件 {input_path}")
        return

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_epub = f"{base_name}.epub"
    ext = os.path.splitext(input_path)[1].lower()

    temp_dir = tempfile.mkdtemp()
    try:
        md_file_path = ""
        if ext == '.zip':
            print(f"正在解压压缩包: {input_path}")
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # 寻找解压后的 txt 或 md 文件并合并
            txt_files = sorted(glob.glob(os.path.join(temp_dir, '**/*.txt'), recursive=True))
            md_files = sorted(glob.glob(os.path.join(temp_dir, '**/*.md'), recursive=True))
            
            combined_content = ""
            for f in md_files:
                with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                    combined_content += file.read() + "\n\n"
            for f in txt_files:
                with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                    combined_content += file.read() + "\n\n"
            
            if not combined_content.strip():
                print("错误: 压缩包内没有找到任何 .txt 或 .md 文件！")
                return
            
            md_file_path = os.path.join(temp_dir, "combined.md")
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(clean_text_to_markdown(combined_content))

        elif ext in ['.txt', '.md']:
            print(f"正在处理文本文件: {input_path}")
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            if ext == '.txt':
                content = clean_text_to_markdown(content)
            
            md_file_path = os.path.join(temp_dir, "converted.md")
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            print(f"不支持的文件格式: {ext} (支持 .txt, .md, .zip)")
            return

        # 调用原有的 kindle_epub.py 进行构建
        print(f"正在生成 EPUB: {output_epub}")
        cmd = [
            sys.executable, "kindle_epub.py", "build", 
            md_file_path, output_epub, 
            "--title", base_name, 
            "--author", "未知作者"
        ]
        subprocess.run(cmd, check=True)
        print(f"转换成功！已输出: {output_epub}")

    except Exception as e:
        print(f"转换过程中出错: {e}")
    finally:
        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python3 auto_convert.py <你的文件.txt/.zip/.md>")
    else:
        process_input(sys.argv[1])
