import os
import sys
import zipfile
import tempfile
import subprocess
import glob
import time
from deep_translator import GoogleTranslator

def translate_and_stack(raw_text):
    """
    2026.2 修复版：加入防封禁延迟与错误过滤，彻底杜绝 Error 500 污染文本
    """
    lines = raw_text.splitlines()
    md_lines = []
    
    sample = raw_text[:500]
    han_count = sum(1 for c in sample if '\u4e00' <= c <= '\u9fff')
    is_mostly_chinese = han_count > 10

    target_lang = 'en' if is_mostly_chinese else 'zh-CN'
    print(f"🌍 智能引擎启动: 检测到 {'中文 (将生成英文对照)' if is_mostly_chinese else '英文 (将生成中文对照)'} 模式...")
    
    translator = GoogleTranslator(source='auto', target=target_lang)

    total_lines = len([l for l in lines if l.strip()])
    current_count = 0

    for line in lines:
        original_line = line.strip()
        if not original_line:
            continue
            
        current_count += 1
        
        # 识别章节标题
        if original_line.startswith("第") and ("章" in original_line[:10] or "节" in original_line[:10]):
            md_lines.append(f"\n# {original_line}\n")
            continue
        elif original_line.lower().startswith("chapter ") and len(original_line) < 30:
            md_lines.append(f"\n# {original_line}\n")
            continue
            
        print(f"[{current_count}/{total_lines}] 正在翻译: {original_line[:30]}...")

        translated = ""
        try:
            # 限制单次翻译长度
            translated = translator.translate(original_line[:4900])
            # 检查是否误触发了谷歌的错误提示页面
            if not translated or "Error 500" in translated or "That’s an error" in translated:
                translated = ""
        except Exception:
            translated = ""

        # 智能组合：如果翻译成功则双语对照，失败则仅保留原文，绝不写入报错代码
        if translated:
            if is_mostly_chinese:
                md_lines.append(f"<p><b>{translated}</b><br/>{original_line}</p>\n")
            else:
                md_lines.append(f"<p><b>{original_line}</b><br/>{translated}</p>\n")
        else:
            md_lines.append(f"<p>{original_line}</p>\n")
            
        # 每次请求后暂停 0.3 秒，防止触发免费接口频率限制
        time.sleep(0.3)
            
    return "".join(md_lines)

def process_input(input_path):
    if not os.path.exists(input_path):
        print(f"❌ 错误: 找不到文件 {input_path}")
        return

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_epub = f"{base_name}_fixed_bilingual.epub"
    ext = os.path.splitext(input_path)[1].lower()

    temp_dir = tempfile.mkdtemp()
    try:
        md_file_path = ""
        if ext == '.zip':
            print(f"📦 正在解压压缩包: {input_path}")
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
            print(f"📖 正在读取并翻译文件: {input_path}")
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            content = translate_and_stack(content)
            md_file_path = os.path.join(temp_dir, "translated.md")
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            print(f"❌ 不支持的文件格式: {ext}")
            return

        print(f"📚 正在打包生成修复版 EPUB: {output_epub}")
        cmd = [
            sys.executable, "kindle_epub.py", "build", 
            md_file_path, output_epub, 
            "--title", f"{base_name} (双语版)", 
            "--author", "未知作者",
            "--language", "bilingual"
        ]
        subprocess.run(cmd, check=True)
        print(f"✨ 转换成功！文件已保存在下载目录: {output_epub}")

    except Exception as e:
        print(f"❌ 转换过程中出错: {e}")
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python3 auto_bilingualtranslate.py <你的纯单语文件.txt>")
    else:
        process_input(sys.argv[1])
