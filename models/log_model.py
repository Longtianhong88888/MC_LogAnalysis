import os
import re
import pandas as pd
from utils.file_utils import read_files, clean_for_excel

class LogModel:
    def process(self, source_dir, output_dir, keywords=None, separator=None):
        # 读取所有文件
        all_data = read_files(source_dir)  # 返回 list of dict
        if not all_data:
            raise ValueError("未找到有效日志文件")

        df_all = pd.DataFrame(all_data)

        # 筛选
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

        # 决定是否生成 Filtered 表
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
                # 删掉原 Content
                # 注意：由于新拼接后列名包含'Content'，但我们需要保留 OriginalContent，且不再有 Content
                # 但上面的concat中，filtered_df['Content'] 已经作为 OriginalContent，实际OriginalContent列是单独加的，所以还需删除原Content
                # 下面更稳妥：
                filtered_df = filtered_df.drop(columns=['Content'])

        # 写 Excel
        out_path = os.path.join(output_dir, 'LogAnalysis.xlsx')
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            df_all.to_excel(writer, sheet_name='AllLogs', index=False)
            if generate_filtered and filtered_df is not None and not filtered_df.empty:
                filtered_df.to_excel(writer, sheet_name='Filtered', index=False)

        return out_path