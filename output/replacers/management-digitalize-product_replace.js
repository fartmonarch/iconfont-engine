// management-digitalize-product 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换

  // 图标类名替换

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
