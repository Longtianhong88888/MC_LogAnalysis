# 使用说明 PPT（ppt-polished-deck-collab skill 出品）

重建步骤：
```bash
venv/bin/python docs/usage_deck/scripts/build_deck.py
venv/bin/python docs/usage_deck/scripts/render_preview_structure.py
```

构建前先重新派生 slide_specs（改过 deck_narrative.md 后）：
```bash
venv/bin/python /Users/user/.codex/skills/ppt-polished-deck-collab/scripts/derive_slide_specs_from_narrative.py \
  --narrative docs/usage_deck/deck_narrative.md \
  --out-yaml docs/usage_deck/build/generated/slide_specs.yaml
```

质量门：
```bash
venv/bin/python /Users/user/.codex/skills/ppt-polished-deck-collab/scripts/check_pptx_package_preflight.py \
  --pptx docs/usage_deck/build/pptx/usage_deck.pptx --workspace-dir docs/usage_deck --fail-on error
venv/bin/python /Users/user/.codex/skills/ppt-polished-deck-collab/scripts/check_pptx_structure_precheck.py \
  --pptx docs/usage_deck/build/pptx/usage_deck.pptx --workspace-dir docs/usage_deck \
  --inventory-out docs/usage_deck/validation/structure_precheck/shape_inventory.json --fail-on error
```
