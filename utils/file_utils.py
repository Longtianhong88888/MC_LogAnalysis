import os
import re
import chardet

# ---------- 清理非法字符 ----------
def clean_for_excel(text):
    """移除 Excel 单元格中不允许的控制字符（保留 \\t, \\n, \\r）"""
    if not isinstance(text, str):
        return text
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)
    return cleaned

# ---------- 编码检测 ----------
def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw = f.read(10000)
        result = chardet.detect(raw)
        return result['encoding'] or 'utf-8'

# ---------- 读取单个文件（带回退编码） ----------
def read_file_with_fallback(file_path):
    encodings = [detect_encoding(file_path), 'utf-8', 'gbk', 'gb2312', 'latin-1']
    for enc in encodings:
        if enc is None:
            continue
        try:
            with open(file_path, 'r', encoding=enc, errors='strict') as f:
                lines = f.readlines()
            cleaned_lines = [clean_for_excel(line.rstrip('\n\r')) for line in lines]
            return cleaned_lines, enc
        except (UnicodeDecodeError, LookupError):
            continue
    # 兜底
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    cleaned_lines = [clean_for_excel(line.rstrip('\n\r')) for line in lines]
    return cleaned_lines, 'utf-8 (with replacement)'

# ---------- 批量读取目录中的所有日志文件（返回列表字典） ----------
def read_files(source_dir):
    """
    读取 source_dir 下所有 .log 和 .txt 文件，返回列表，每个元素为 {'FileName': 文件名, 'Content': 清理后的行内容}
    """
    all_rows = []
    files = [f for f in os.listdir(source_dir) if f.lower().endswith(('.log', '.txt'))]
    for fname in files:
        fpath = os.path.join(source_dir, fname)
        lines, _ = read_file_with_fallback(fpath)
        for line in lines:
            if line.strip() == '':
                continue
            all_rows.append({'FileName': fname, 'Content': clean_for_excel(line)})
    return all_rows