// management-insurance-template 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换

  // 图标类名替换
  { file: "src/components/Upload/upload-list.vue", line: 30, from: "icon-download", to: "icon-download_v2", type: "icon_class" },
  { file: "src/components/UploadList/index.vue", line: 31, from: "icon-download", to: "icon-download_v2", type: "icon_class" },
  { file: "src/views/chart-profession/profession.vue", line: 35, from: "icon-download", to: "icon-download_v2", type: "icon_class" },
  { file: "src/views/dev-tools/interface-config.vue", line: 99, from: "icon-download", to: "icon-download_v2", type: "icon_class" },
  { file: "src/views/dev-tools/interface-policy-query.vue", line: 53, from: "icon-download", to: "icon-download_v2", type: "icon_class" },
  { file: "src/views/add-product/component/newProductInfo/base-info.vue", line: 27, from: "icon-edit", to: "icon-edit_v3", type: "icon_class" },
  { file: "src/views/dev-tools/interface-config.vue", line: 94, from: "icon-edit", to: "icon-edit_v3", type: "icon_class" },
  { file: "src/views/dev-tools/interface-policy-query.vue", line: 51, from: "icon-edit", to: "icon-edit_v3", type: "icon_class" },
  { file: "src/views/dev-tools/interface-config-wrapper.vue", line: 13, from: "icon-search", to: "icon-search_v2", type: "icon_class" },
  { file: "src/views/dev-tools/interface-config.vue", line: 5, from: "icon-search", to: "icon-search_v2", type: "icon_class" },
  { file: "src/views/dev-tools/interface-policy-query.vue", line: 12, from: "icon-search", to: "icon-search_v2", type: "icon_class" },
  { file: "src/views/add-product/component/insuredRules/dynamic-process-config.vue", line: 172, from: "icon-share", to: "icon-share_v1", type: "icon_class" },
  { file: "src/views/add-product/component/insuredRules/dynamic-process-config.vue", line: 243, from: "icon-share", to: "icon-share_v1", type: "icon_class" },
  { file: "src/views/add-product/component/insuredRules/dynamic-process-config.vue", line: 247, from: "icon-share", to: "icon-share_v1", type: "icon_class" },
  { file: "src/views/add-product/component/insuredRules/dynamic-process-config.vue", line: 320, from: "icon-share", to: "icon-share_v1", type: "icon_class" },
  { file: "src/views/interface/index.vue", line: 80, from: "icon-share", to: "icon-share_v1", type: "icon_class" },
  { file: "src/views/policy-info-list/components/riskOrder.vue", line: 115, from: "icon-share", to: "icon-share_v1", type: "icon_class" },
  { file: "src/views/policy-info-list/index.vue", line: 295, from: "icon-share", to: "icon-share_v1", type: "icon_class" },
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
