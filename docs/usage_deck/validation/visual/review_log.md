# Visual Review Log

## 预览方式
- 环境限制：本机 Microsoft PowerPoint 自动化导出 PDF 失败（macOS Automation 权限，错误 -9074）；无 LibreOffice / pdftoppm。
- 因此逐页预览为 **PIL 结构近似渲染**（`build/rendered/structure_preview/slide_*.png` + `contact_sheet.png`），非 PowerPoint 高保真成图。
- 结论：`render_review`（边界触墨 / 扁平化图像内部文字）标记为 `not_checked`，需在装有 PowerPoint 的环境中人工复核成图。

## Fatal
- 无。

## Warning
- 甘特示例为 PNG 图片，内部文字不在结构检查范围（`structure_precheck` 已标记 `not_checked`）；已在页面标注“示例/示意”。
- 由于非高保真预览，字号实际渲染效果（如中文宋体在 PowerPoint 中的行距）建议在 PowerPoint 中打开确认。

## Preference
- 封面与结尾的大标题可再拉开与副标题的间距。
- 概览页三个大数字下方的说明宽度较窄，可适当放宽或缩短文案。

## Residual Risk
- 未完成 PowerPoint 高保真成图复核；最终 pptx 为可编辑原生对象，建议用户用 PowerPoint 打开做最终确认。
