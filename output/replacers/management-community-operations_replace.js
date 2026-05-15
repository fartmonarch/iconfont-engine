// management-community-operations 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "index.html", line: 10, from: "<%= htmlWebpackPlugin.options.assetsPublicPath %>static/iconfont/20231024/iconfont.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "standalone.html", line: 9, from: "<%= htmlWebpackPlugin.options.assetsPublicPath %>static/iconfont/20231024/iconfont.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/components/kpi-top-bar/index.vue", line: 17, from: "icon-a-zongbiaobao1x", to: "icon-a-zongbiaobao1x_v2", type: "icon_class" },
  { file: "src/components/Upload/upload-list.vue", line: 32, from: "icon-delete", to: "icon-delete_v2", type: "icon_class" },
  { file: "src/components/UploadList/index.vue", line: 33, from: "icon-delete", to: "icon-delete_v2", type: "icon_class" },
  { file: "src/views/customer-service/knowledge-base/components/biz/knowledge-content/qa-content/components/detail-ask.vue", line: 7, from: "icon-delete", to: "icon-delete_v2", type: "icon_class" },
  { file: "src/views/customer-service/knowledge-base/components/biz/knowledge-list-item/index.vue", line: 10, from: "icon-delete", to: "icon-delete_v2", type: "icon_class" },
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
