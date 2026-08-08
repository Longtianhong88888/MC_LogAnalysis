# Visual Review Log

## 模板化修订（v2，2026-08-08）
- 改用根目录 `PPT模板.pptx`（鸿海/富士康风格模板）：master-first 路线，删除模板示例页后用 1_cover / 1_agenda / 1_content page layout 重建 13 页，继承 master 版权行、右上 logo、页码/页脚。
- 配色按模板主题调整：强调色 EF5149（封面标题/大数字/章节小字）、深蓝 083C63（次级标题/表头/线条）、浅红底提示（FDEFEE）。
- 封面标题沿用模板真实字号 54pt（模板字号例外，structure_precheck 以 warning 记录）；其余字号收敛到 token 档位。
- 模板 TITLE 占位实例化后宽度为 0（模板 xfrm 继承问题），构建时显式设置占位符几何修复；structure_precheck 0 error。

## 预览方式
- 环境限制：本机 Microsoft PowerPoint 自动化导出 PDF 失败（macOS Automation 权限，错误 -9074）；无 LibreOffice / pdftoppm。
- 因此逐页预览为 **PIL 结构近似渲染**（`build/rendered/structure_preview/slide_*.png` + `contact_sheet.png`），非 PowerPoint 高保真成图。
- 结构近似渲染只绘制 slide 层形状；模板 master/layout 的版权行、右上 logo、页码/页脚由 PowerPoint 渲染时继承，不在近似预览中显示——最终效果请以 PowerPoint 打开为准。
- 结论：`render_review`（边界触墨 / 扁平化图像内部文字）标记为 `not_checked`，需在装有 PowerPoint 的环境中人工复核成图。

## Fatal
- 无。

## Warning
- 甘特示例为 PNG 图片，内部文字不在结构检查范围（`structure_precheck` 已标记 `not_checked`）；已在页面标注“示例/示意”。
- 由于非高保真预览，字号实际渲染效果（如中文宋体在 PowerPoint 中的行距）建议在 PowerPoint 中打开确认。
- 封面/结尾大标题 54pt 与 40pt 为模板字号体系（封面 54pt 来自模板示例页），已在 review note 记录。

## Preference
- 封面与结尾的大标题可再拉开与副标题的间距。
- 概览页三个大数字下方的说明宽度较窄，可适当放宽或缩短文案。

## Residual Risk
- 未完成 PowerPoint 高保真成图复核；最终 pptx 为可编辑原生对象，建议用户用 PowerPoint 打开做最终确认。
