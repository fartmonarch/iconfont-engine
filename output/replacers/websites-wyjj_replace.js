// websites-wyjj 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "insurance-broker/src/pages/aboutUs/aboutUs.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_428664_lq56367snj1exw29.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "insurance-broker/src/pages/index/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_428664_lq56367snj1exw29.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "insurance-broker/src/pages/information/information.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_428664_lq56367snj1exw29.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "insurance-broker/src/pages/intro/intro.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_428664_lq56367snj1exw29.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "winbrokers/components/about/organization.js", line: 139, from: "icon-location", to: "icon-location_v4", type: "icon_class" },
  { file: "winbrokers/components/about/organization.js", line: 143, from: "icon-phone_surface", to: "icon-phone_surface_v1", type: "icon_class" },
  { file: "winbrokers/components/about/organization.js", line: 143, from: "icon-phone_surface", to: "icon-phone_surface_v3", type: "icon_class" },
  { file: "winbrokers/components/information/company.vue", line: 72, from: "icon-close_line_b", to: "icon-close_line_b_v2", type: "icon_class" },
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
