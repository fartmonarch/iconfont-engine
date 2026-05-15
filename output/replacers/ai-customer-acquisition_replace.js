// ai-customer-acquisition 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "src/pages/ai-article/index.html", line: 23, from: "//res.winbaoxian.com/ali-iconfont/font_5147685_3yj1cl522ql.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/ai-poster/index.html", line: 23, from: "//res.winbaoxian.com/ali-iconfont/font_428664_7itacmrlk3.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/pages/ai-article/views/index/components/bottom-user-card/index.vue", line: 94, from: "icon-close_circle_line", to: "icon-close_circle_line_v2", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/bottom-user-card/index.vue", line: 94, from: "icon-close_circle_line", to: "icon-close_circle_line_v3", type: "icon_class" },
  { file: "src/pages/ai-poster/views/intellect-create/index.vue", line: 73, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v3", type: "icon_class" },
  { file: "src/common/components/AudienceSelector.vue", line: 13, from: "icon-close_line", to: "icon-close_line_v3", type: "icon_class" },
  { file: "src/common/components/PopUp.vue", line: 15, from: "icon-close_line", to: "icon-close_line_v3", type: "icon_class" },
  { file: "src/common/components/AudienceSelector.vue", line: 13, from: "icon-close_line", to: "icon-close_line_v4", type: "icon_class" },
  { file: "src/common/components/PopUp.vue", line: 15, from: "icon-close_line", to: "icon-close_line_v4", type: "icon_class" },
  { file: "src/pages/ai-poster/views/ai-poster-result-generation-page/index.vue", line: 109, from: "icon-refresh", to: "icon-refresh_v2", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/bottom-user-card/index.vue", line: 16, from: "icon-me_surface", to: "icon-me_surface_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/user-card/index.vue", line: 40, from: "icon-me_surface", to: "icon-me_surface_v1", type: "icon_class" },
  { file: "src/pages/ai-poster/views/intellect-create/components/FilePickerPopup.vue", line: 25, from: "icon-add_image_after", to: "icon-add_image_after_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/bottom-user-card/index.vue", line: 76, from: "icon-phone_surface", to: "icon-phone_surface_v3", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/bottom-user-card/index.vue", line: 76, from: "icon-phone_surface", to: "icon-phone_surface_v3", type: "icon_class" },
  { file: "src/pages/ai-rednote/views/result/components/submit-button.vue", line: 5, from: "icon-edit", to: "icon-edit_v2", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/bottom-user-card/index.vue", line: 29, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/bottom-user-card/index.vue", line: 39, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/bottom-user-card/index.vue", line: 49, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/user-card/index.vue", line: 12, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/user-card/index.vue", line: 20, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/user-card/index.vue", line: 29, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/bottom-user-card/index.vue", line: 29, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/bottom-user-card/index.vue", line: 39, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/bottom-user-card/index.vue", line: 49, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/user-card/index.vue", line: 12, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/user-card/index.vue", line: 20, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/ai-article/views/index/components/user-card/index.vue", line: 29, from: "icon-arrow_right_fill", to: "icon-arrow_right_fill_v1", type: "icon_class" },
  { file: "src/pages/ai-scene/views/ai-scene-detail/components/WechatMoments.vue", line: 116, from: "icon-download_surface", to: "icon-download_surface_v1", type: "icon_class" },
  { file: "src/pages/ai-poster/views/intellect-create/components/FilePickerPopup.vue", line: 41, from: "icon-document", to: "icon-document_v1", type: "icon_class" },
  { file: "src/pages/ai-poster/views/intellect-create/index.vue", line: 37, from: "icon-document", to: "icon-document_v1", type: "icon_class" },
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
