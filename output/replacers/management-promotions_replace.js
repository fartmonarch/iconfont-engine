// management-promotions 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "src/common/common.js", line: 35, from: "//res.winbaoxian.com/ali-iconfont/font_336721_74m4vln6iy919k9.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/components/header.vue", line: 9, from: "icon-edit", to: "icon-edit_v3", type: "icon_class" },
  { file: "src/pages/activity-frame.vue", line: 5, from: "icon-edit", to: "icon-edit_v3", type: "icon_class" },
  { file: "src/pages/activity-frame.vue", line: 6, from: "icon-add_image", to: "icon-add_image_v2", type: "icon_class" },
  { file: "src/pages/activity-frame.vue", line: 8, from: "icon-greeting_card", to: "icon-greeting_card_v2", type: "icon_class" },
  { file: "src/pages/layout.vue", line: 5, from: "icon-develop", to: "icon-develop_v2", type: "icon_class" },
  { file: "src/pages/layout.vue", line: 6, from: "icon-money", to: "icon-money_v3", type: "icon_class" },
  { file: "src/pages/activity-frame.vue", line: 7, from: "icon-service", to: "icon-service_v3", type: "icon_class" },
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
