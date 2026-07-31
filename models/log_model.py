import os
import re
import pandas as pd
from utils.file_utils import read_files, clean_for_excel

class LogModel:
    def process(self, source_dir, output_dir, keywords=None, separator=None, progress_callback=None):
        # 步骤1: 读取文件（进度 10%）
        if progress_callback:
            progress_callback(10)
        
        all_data = read_files(source_dir)
        if not all_data:
            raise ValueError("未找到有效日志文件")
        df_all = pd.DataFrame(all_data)
        
        if progress_callback:
            progress_callback(30)

        # 步骤2: 筛选（进度 50%）
        if keywords:
            kw_list = re.split(r'[ ;、，]+', keywords)
            kw_list = [k for k in kw_list if k]
            if kw_list:
                pattern = '|'.join(re.escape(k) for k in kw_list)
                mask = df_all['Content'].str.contains(pattern, case=False, na=False)
                filtered_df = df_all[mask].copy()
            else:
                filtered_df = df_all.copy()
        else:
            filtered_df = df_all.copy()
        
        if progress_callback:
            progress_callback(50)

        # 步骤3: 决定是否生成 Filtered 表及拆分（进度 70%）
        has_filtered_rows = not filtered_df.empty
        has_separator = separator is not None and separator != ''
        generate_filtered = has_filtered_rows or has_separator

        if generate_filtered:
            if not has_filtered_rows and has_separator:
                filtered_df = df_all.copy()
                has_filtered_rows = True

            if has_separator:
                sep = separator
                if sep == '\\t':
                    sep = '\t'
                split_rows = []
                max_parts = 0
                for _, row in filtered_df.iterrows():
                    parts = row['Content'].split(sep)
                    parts = [clean_for_excel(p) for p in parts]
                    max_parts = max(max_parts, len(parts))
                    split_rows.append(parts)
                col_names = [f'Part_{i+1}' for i in range(max_parts)]
                split_data = []
                for parts in split_rows:
                    parts += [''] * (max_parts - len(parts))
                    split_data.append(parts)
                split_df = pd.DataFrame(split_data, columns=col_names)
                filtered_df = filtered_df.reset_index(drop=True)
                filtered_df = pd.concat([
                    filtered_df[['FileName']],
                    pd.DataFrame({'OriginalContent': filtered_df['Content']}),
                    split_df
                ], axis=1)
                # 删除原 Content 列（因为已经用 OriginalContent 替换）
                filtered_df = filtered_df.drop(columns=['Content'])

        if progress_callback:
            progress_callback(70)

        # 步骤4: 写入 Excel（进度 100%）
        out_path = os.path.join(output_dir, 'LogAnalysis.xlsx')
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            df_all.to_excel(writer, sheet_name='AllLogs', index=False)
            if generate_filtered and filtered_df is not None and not filtered_df.empty:
                filtered_df.to_excel(writer, sheet_name='Filtered', index=False)

        if progress_callback:
            progress_callback(100)

        return out_path