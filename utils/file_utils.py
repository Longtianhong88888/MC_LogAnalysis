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
        enc = result['encoding'] or 'utf-8'
        # chardet 对中文日志（UTF-8 或 GBK）常误判为单字节编码（latin-1/iso-8859-* 等）导致中文乱码。
        # 遇到单字节编码时不信任该结果：优先按 UTF-8 尝试，失败后由调用方回退 GBK。
        low = enc.lower()
        if any(k in low for k in ('latin', 'iso-8859', 'windows-125', 'mac_')):
            return 'utf-8'
        return enc

# ---------- 读取单个文件（带回退编码） ----------
def read_file_with_fallback(file_path):
    with open(file_path, 'rb') as f:
        raw = f.read()
    # 单次读盘：依次按检测编码/UTF-8/GBK 解码，避免每个候选编码都重新读全文件
    encodings = [detect_encoding(file_path), 'utf-8', 'gbk', 'gb2312']
    for enc in encodings:
        if enc is None:
            continue
        try:
            text = raw.decode(enc)
            cleaned_lines = [clean_for_excel(line.rstrip('\n\r')) for line in text.splitlines()]
            return cleaned_lines, enc
        except (UnicodeDecodeError, LookupError):
            continue
    # strict 全部失败：中文机台日志常见 UTF-8（含少量非法字节）或 GBK。
    # 用忽略模式分别解码，比较 UTF-8 丢失的字节比例：丢失少说明是 UTF-8，否则按 GBK 处理。
    utf8_text = raw.decode('utf-8', errors='ignore')
    total = len(raw)
    dropped = total - len(utf8_text.encode('utf-8', errors='ignore'))
    if dropped / total < 0.01:
        cleaned_lines = [clean_for_excel(line.rstrip('\n\r')) for line in utf8_text.splitlines()]
        return cleaned_lines, 'utf-8 (ignore)'
    gbk_text = raw.decode('gbk', errors='ignore')
    cleaned_lines = [clean_for_excel(line.rstrip('\n\r')) for line in gbk_text.splitlines()]
    return cleaned_lines, 'gbk (ignore)'
    # 兜底

# ---------- 批量读取目录中的所有日志文件（返回列表字典） ----------
def read_files(source_dir, progress_callback=None, file_filters=None, cancel_event=None):
    """
    递归读取 source_dir 下所有 .log 和 .txt 文件，返回列表，每个元素为 {'FileName': 相对路径, 'Content': 清理后的行内容}
    progress_callback: 可选回调，每读完一个文件调用一次，参数为 (已读文件数 / 总文件数)
    file_filters: 可选，文件名关键词列表（相对路径模糊匹配，任一命中即包含）；None 表示读取全部
    """
    all_rows = []
    files = []
    for dirpath, _, filenames in os.walk(source_dir):
        for fname in sorted(filenames):
            if fname.lower().endswith(('.log', '.txt')):
                fpath = os.path.join(dirpath, fname)
                rel_name = os.path.relpath(fpath, source_dir).replace(os.sep, '/')
                if file_filters and not any(f.lower() in rel_name.lower() for f in file_filters):
                    continue
                files.append((fpath, rel_name))
    files.sort()
    if not files:
        raise ValueError(f"未找到日志文件：{source_dir} 及其子目录下没有 .log / .txt 文件")
    total = len(files)
    for idx, (fpath, rel_name) in enumerate(files):
        if cancel_event is not None and cancel_event.is_set():
            from models.exceptions import OperationCancelled
            raise OperationCancelled()
        lines, _ = read_file_with_fallback(fpath)
        for ln_idx, line in enumerate(lines):
            if ln_idx % 50000 == 0 and cancel_event is not None and cancel_event.is_set():
                from models.exceptions import OperationCancelled
                raise OperationCancelled()
            if line.strip() == '':
                continue
            all_rows.append({'FileName': rel_name, 'Content': clean_for_excel(line)})
        if progress_callback and total > 0:
            progress_callback((idx + 1) / total)
    return all_rows
