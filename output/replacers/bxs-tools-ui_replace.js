// bxs-tools-ui 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "demo/index.html", line: 6, from: "https://res.winbaoxian.com/ali-iconfont/font_428664_ioax9hc9ckg.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "docs/index.html", line: 6, from: "https://res.winbaoxian.com/ali-iconfont/font_428664_ioax9hc9ckg.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "index.html", line: 6, from: "//res.winbaoxian.com/ali-iconfont/font_428664_ioax9hc9ckg.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/components/common/common-title.vue", line: 24, from: "icon-arrows_right", to: "icon-arrows_right_v5", type: "icon_class" },
  { file: "packages/planbook-input/components/product-table.vue", line: 42, from: "icon-more_circle", to: "icon-more_circle_v4", type: "icon_class" },
  { file: "packages/planbook-input/components/product-table.vue", line: 83, from: "icon-more_circle", to: "icon-more_circle_v4", type: "icon_class" },
  { file: "packages/person-info/crm-popup.vue", line: 37, from: "icon-client", to: "icon-client_v2", type: "icon_class" },
  { file: "packages/adjust-baoe/index.vue", line: 64, from: "icon-edit", to: "icon-edit_v2", type: "icon_class" },
  { file: "packages/person-info/index.vue", line: 55, from: "icon-edit", to: "icon-edit_v2", type: "icon_class" },
  { file: "packages/product-info/index.vue", line: 81, from: "icon-edit", to: "icon-edit_v2", type: "icon_class" },
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
