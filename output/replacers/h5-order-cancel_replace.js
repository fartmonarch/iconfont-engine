// h5-order-cancel 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "config/index.js", line: 111, from: "//res.winbaoxian.com/ali-iconfont/font_590851_sszavby595mw8kt9.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/pages/order-cancel/components/reason.vue", line: 5, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/face-plus-auth/face-plus-auth.vue", line: 15, from: "icon-choose_done_line", to: "icon-choose_done_line_v2", type: "icon_class" },
  { file: "src/pages/face-plus-auth/face-plus-auth.vue", line: 21, from: "icon-choose_done_line", to: "icon-choose_done_line_v2", type: "icon_class" },
  { file: "src/pages/face-plus-auth/face-plus-auth.vue", line: 27, from: "icon-choose_done_line", to: "icon-choose_done_line_v2", type: "icon_class" },
  { file: "src/pages/mobile-change-result/partial/title.vue", line: 27, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/order-cancel-details/detailsTitle.vue", line: 8, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/order-cancel-details/detailsTitle.vue", line: 27, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/refund-result/refund-result.vue", line: 50, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/face-plus-auth/face-plus-auth.vue", line: 87, from: "icon-close_circle_line", to: "icon-close_circle_line_v1", type: "icon_class" },
  { file: "src/components/w-input/w-input.vue", line: 25, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/face-auth-result/face-auth-result.vue", line: 6, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/mobile-change-apply/partial/upload.vue", line: 11, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/mobile-change-apply/partial/upload.vue", line: 20, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/mobile-change-result/partial/title.vue", line: 45, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/order-cancel/components/upload.vue", line: 17, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/order-cancel/components/upload.vue", line: 32, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/order-cancel-details/detailsTitle.vue", line: 45, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/refund-appeal/components/upload-image.vue", line: 11, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/refund-appeal/components/upload-image.vue", line: 20, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/refund-result/refund-result.vue", line: 7, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/upload-material/partial/upload.vue", line: 12, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/upload-material/partial/upload.vue", line: 21, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/mobile-change-apply/partial/pop-case.vue", line: 3, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/order-cancel/components/pop-case.vue", line: 3, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/order-cancel/components/pop-statement.vue", line: 3, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/refund-appeal/components/pop-case.vue", line: 4, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/upload-material/partial/pop-case.vue", line: 3, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/confirm-info/confirm-info.vue", line: 11, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/mobile-change-result/partial/call.vue", line: 3, from: "icon-phone_line", to: "icon-phone_line_v3", type: "icon_class" },
  { file: "src/pages/mobile-change-apply/partial/baseInfo.vue", line: 5, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/order-cancel/components/baseInfo.vue", line: 5, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/upload-material/partial/baseInfo.vue", line: 5, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/mobile-change-result/partial/title.vue", line: 8, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/pages/refund-result/refund-result.vue", line: 26, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
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
