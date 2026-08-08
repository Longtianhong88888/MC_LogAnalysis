# Visual Review Log

## 高保真复核（v3，2026-08-08）
- PowerPoint 自动化已可用，导出 13 页高保真预览（`build/rendered/ppt_preview/`，144dpi）+ contact sheet。
- render_review：通过（0 error / 0 warning / 0 not_checked）。
- 修复：① 模板 SLIDE_NUMBER 占位在 add_slide 时未实例化 → 每页右下补页码（NAVY，n / 13，已确认随页递增）；② python-pptx 默认表格样式带模板红色条纹 → 所有表格单元格显式填充（表头 NAVY、数据行白/浅灰交替），浅红像素已清零。
- 模板继承确认：PowerPoint 渲染后每页版权行、右上 logo 正常显示；封面 54pt 红橙标题、甘特页 BITMAP 图、目录/内容页 layout 均正常。

## 模板化修订（v2，2026-08-08）
- 改用根目录 `PPT模板.pptx`（鸿海/富士康风格模板）：master-first 路线，删除模板示例页后用 1_cover / 1_agenda / 1_content page layout 重建 13 页，继承 master 版权行、右上 logo、页码/页脚。
- 配色按模板主题调整：强调色 EF5149（封面标题/大数字/章节小字）、深蓝 083C63（次级标题/表头/线条）、浅红底提示（FDEFEE）。
- 封面标题沿用模板真实字号 54pt（模板字号例外，structure_precheck 以 warning 记录）；其余字号收敛到 token 档位。
- 模板 TITLE 占位实例化后宽度为 0（模板 xfrm 继承问题），构建时显式设置占位符几何修复；structure_precheck 0 error。

## 预览方式（v1 结构近似，v3 已升级为 PowerPoint 高保真）
- 环境限制：本机 Microsoft PowerPoint 自动化导出 PDF 失败（macOS Automation 权限，错误 -9074）；无 LibreOffice / pdftoppm。
- v3 起逐页预览为 **PowerPoint 高保真渲染**（`build/rendered/ppt_preview/`）；v1 的 PIL 结构近似渲染保留在 `build/rendered/structure_preview/` 供对比。
- 结论：`render_review`（边界触墨 / 扁平化图像内部文字）标记为 `not_checked`，需在装有 PowerPoint 的环境中人工复核成图。

## Fatal
- 无。

## Warning
- 甘特示例为 PNG 图片，内部文字不在结构检查范围（`structure_precheck` 已标记 `not_checked`）；已在页面标注“示例/示意”。
- 封面/结尾大标题 54pt 与 40pt 为模板字号体系（封面 54pt 来自模板示例页），已在 review note 记录。

## Preference
- 封面与结尾的大标题可再拉开与副标题的间距。
- 概览页三个大数字下方的说明宽度较窄，可适当放宽或缩短文案。

## Residual Risk
- 未完成 PowerPoint 高保真成图复核；最终 pptx 为可编辑原生对象，建议用户用 PowerPoint 打开做最终确认。
