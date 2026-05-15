// face-plus-auth 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "index.html", line: 8, from: "//res.winbaoxian.com/ali-iconfont/font_280767_yehzob4ie8kt9.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/App.vue", line: 15, from: "icon-choose_done_line", to: "icon-choose_done_line_v2", type: "icon_class" },
  { file: "src/App.vue", line: 21, from: "icon-choose_done_line", to: "icon-choose_done_line_v2", type: "icon_class" },
  { file: "src/App.vue", line: 27, from: "icon-choose_done_line", to: "icon-choose_done_line_v2", type: "icon_class" },
  { file: "src/App.vue", line: 97, from: "icon-close_circle_line", to: "icon-close_circle_line_v1", type: "icon_class" },
  { file: "src/App.vue", line: 48, from: "icon-refresh", to: "icon-refresh_v1", type: "icon_class" },
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
