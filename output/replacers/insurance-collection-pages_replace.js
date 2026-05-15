// insurance-collection-pages 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "src/pages/savings-zone-page/index.html", line: 11, from: "//res.winbaoxian.com/ali-iconfont/font_428664_oq3fahn36yo.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/pages/savings-zone-page/components/Vue3-InterestSelectionDetail/index.vue", line: 54, from: "icon-arrows_right", to: "icon-arrows_right_v5", type: "icon_class" },
  { file: "src/pages/savings-zone-page/components/Vue3-InterestSelectionDetail/index.vue", line: 212, from: "icon-arrows_right", to: "icon-arrows_right_v5", type: "icon_class" },
  { file: "src/pages/savings-zone-page/components/Vue3-InterestSelectionDetail/index.vue", line: 197, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v4", type: "icon_class" },
  { file: "src/pages/savings-zone-page/components/Vue3-InterestSelectionDetail/index.vue", line: 201, from: "icon-choose_none_line", to: "icon-choose_none_line_v3", type: "icon_class" },
  { file: "src/components/person-card.vue", line: 98, from: "icon-close_circle_line", to: "icon-close_circle_line_v3", type: "icon_class" },
  { file: "src/components/ImagePreview.vue", line: 3, from: "icon-close_line", to: "icon-close_line_v4", type: "icon_class" },
  { file: "src/pages/savings-zone-page/components/Vue3-InterestSelectionDetail/index.vue", line: 418, from: "icon-close_line", to: "icon-close_line_v4", type: "icon_class" },
  { file: "src/components/person-card.vue", line: 80, from: "icon-phone_surface", to: "icon-phone_surface_v3", type: "icon_class" },
  { file: "src/pages/savings-zone-page/components/Vue3-InterestSelectionDetail/index.vue", line: 39, from: "icon-arrow_down", to: "icon-arrow_down_v1", type: "icon_class" },
  { file: "src/components/compare3/index.vue", line: 170, from: "icon-add_surface", to: "icon-add_surface_v2", type: "icon_class" },
  { file: "src/components/person-card.vue", line: 33, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/components/person-card.vue", line: 43, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/components/person-card.vue", line: 53, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/elderly-care-community/components/recommend-product.vue", line: 31, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/medical-concept/views/detail/components/ProductSelectPopup.vue", line: 48, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
];

function applyReplacements(projectDir) {
  for (const r of replacements) {
    const filePath = path.join(projectDir, r.file);
    if (!fs.existsSync(filePath)) continue;
    let content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split('\n');
    if (r.line > 0 && r.line <= lines.length) {
      const oldLine = lines[r.line - 1];
      if (r.type === 'css_link') {
        lines[r.line - 1] = oldLine.replace(r.from, r.to);
      } else if (r.type === 'icon_class') {
        const re = new RegExp('\\b' + r.from.replace(/-/g, '\\-') + '\\b', 'g');
        lines[r.line - 1] = oldLine.replace(re, r.to);
      }
      fs.writeFileSync(filePath, lines.join('\n'), 'utf-8');
      console.log('Replaced:', r.file, 'line', r.line);
    }
  }
}

if (require.main === module) {
  const dir = process.argv[2] || '.';
  applyReplacements(dir);
}

module.exports = { applyReplacements };
