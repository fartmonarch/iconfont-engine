// app-settlement 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "public/index.html", line: 9, from: "//res.winbaoxian.com/ali-iconfont/font_1311936_jf12otjodsq.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "public/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_336721_14yv3un7pqz.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "public/index.html", line: 11, from: "//res.winbaoxian.com/ali-iconfont/font_2607384_ql7dfkp013h.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/views/index/index.vue", line: 30, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/views/index/index.vue", line: 30, from: "icon-arrows_right", to: "icon-arrows_right_v5", type: "icon_class" },
  { file: "src/views/questions/questions.vue", line: 30, from: "icon-customer", to: "icon-customer_v1", type: "icon_class" },
  { file: "src/views/withdraw-money/withdraw-money.vue", line: 313, from: "icon-customer", to: "icon-customer_v1", type: "icon_class" },
  { file: "src/views/withdraw-money/withdraw-money.vue", line: 384, from: "icon-customer", to: "icon-customer_v1", type: "icon_class" },
  { file: "src/views/questions/questions.vue", line: 30, from: "icon-customer", to: "icon-customer_v1", type: "icon_class" },
  { file: "src/views/withdraw-money/withdraw-money.vue", line: 313, from: "icon-customer", to: "icon-customer_v1", type: "icon_class" },
  { file: "src/views/withdraw-money/withdraw-money.vue", line: 384, from: "icon-customer", to: "icon-customer_v1", type: "icon_class" },
  { file: "src/views/withdraw-money/withdraw-money.vue", line: 49, from: "icon-_huaban", to: "icon-_huaban_v1", type: "icon_class" },
  { file: "src/views/withdraw-money/withdraw-money.vue", line: 49, from: "icon-_huaban", to: "icon-_huaban_v2", type: "icon_class" },
  { file: "src/views/statement/statement.vue", line: 98, from: "icon-arrow_up_fill", to: "icon-arrow_up_fill_v1", type: "icon_class" },
  { file: "src/views/statement/statement.vue", line: 100, from: "icon-arrow_down_fill", to: "icon-arrow_down_fill_v2", type: "icon_class" },
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
