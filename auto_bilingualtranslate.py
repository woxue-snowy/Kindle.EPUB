import os
import sys
import zipfile
import tempfile
import subprocess
import glob
from deep_translator import GoogleTranslator

def translate_and_stack(raw_text):
    """
    自动检测语言并翻译，实现【上面英文、下面中文】的垂直双语排版
    """
    lines = raw_text.splitlines()
    md_lines = []
    
    sample = raw_text[:500]
    han_count = sum(1 for c in sample if '\u4e00' <= c <= '\u9fff')
    is_mostly_chinese = han_count > 10

    target_lang = 'en' if is_mostly_chinese else 'zh-CN'
    print(f"检测到文本主要为 {'中文 (将生成英文对照)' if is_mostly_chinese else '英文 (将生成中文对照)'} 模式...")
    translator = GoogleTranslator(source='auto', target=target_lang)

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 保留或识别章节标题
        if line.startswith("第") and ("章" in line[:10] or "节" in line[:10]):
            md_lines.append(f"\n# {line}\n")
            continue
        elif line.lower().startswith("chapter ") and len(line) < 30:
            md_lines.append(f"\n# {line}\n")
            continue
            
        try:
            translated = translator.translate(line)
            if translated:
                if is_mostly_chinese:
                    # 原文是中文：上面是英文(翻译)，下面是中文(原文)
                    md_lines.append(f"{translated}\n\n{line}\n")
                else:
                    # 原文是英文：上面是英文(原文)，下面是中文(翻译)
                    md_lines.append(f"{line}\n\n{translated}\n")
            else:
                md_lines.append(line + "\n")
        except Exception:
            md_lines.append(line + "\n")
            
    return "".join(md_lines)

def process_input(input_path):
    if not os.path.exists(input_path):
        print(f"错误: 找不到文件 {input_path}")
        return

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_epub = f"{base_name}_top_en_bottom_cn.epub"
    ext = os.path.splitext(input_path)[1].lower()

    temp_dir = tempfile.mkdtemp()
    try:
        md_file_path = ""
        if ext == '.zip':
            print(f"正在解压压缩包: {input_path}")
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            txt_files = sorted(glob.glob(os.path.join(temp_dir, '**/*.txt'), recursive=True))
            combined_content = ""
            for f in txt_files:
                with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                    combined_content += file.read() + "\n\n"
            
            md_file_path = os.path.join(temp_dir, "translated.md")
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(translate_and_stack(combined_content))

        elif ext in ['.txt', '.md']:
            print(f"正在读取并翻译文件: {input_path}")
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            content = translate_and_stack(content)
            md_file_path = os.path.join(temp_dir, "translated.md")
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            print(f"不支持的文件格式: {ext}")
            return

        print(f"正在打包生成上下对照 EPUB: {output_epub}")
        cmd = [
            sys.executable, "kindle_epub.py", "build", 
            md_file_path, output_epub, 
            "--title", base_name, 
            "--author", "未知作者",
            "--language", "bilingual"
        ]
        subprocess.run(cmd, check=True)
        print(f"转换成功！上下对照电子书已输出为: {output_epub}")

    except Exception as e:
        print(f"转换过程中出错: {e}")
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python3 auto_convert.py <你的纯单语文件.txt>")
    else:
        process_input(sys.argv[1])
