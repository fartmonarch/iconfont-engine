// insurance-policy-refund 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "page.config.js", line: 6, from: "//res.winbaoxian.com/ali-iconfont/font_590851_sszavby595mw8kt9.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "public/index.html", line: 10, from: "//res.wyins.net/ali-iconfont/font_280767_gc9nad8nz5mi.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/cancel-guide/index.html", line: 10, from: "//res.wyins.net/ali-iconfont/font_280767_gc9nad8nz5mi.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/electronic-signature/index.html", line: 11, from: "//res.wyins.net/ali-iconfont/font_280767_p4qiup9lop.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/map-test/index.html", line: 10, from: "//res.wyins.net/ali-iconfont/font_280767_gc9nad8nz5mi.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/pages/apply-refund/index.vue", line: 13, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/apply-refund/index.vue", line: 49, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/apply-refund/index.vue", line: 51, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/order-cancel/components/reason.vue", line: 5, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/apply-refund/index.vue", line: 13, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/apply-refund/index.vue", line: 49, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/apply-refund/index.vue", line: 51, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/order-cancel/components/reason.vue", line: 5, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 13, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 20, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 93, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 127, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 241, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/index.vue", line: 28, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/face-auth-result/face-auth-result.vue", line: 25, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 48, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 13, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 20, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 93, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 127, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 241, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/index.vue", line: 28, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/face-auth-result/face-auth-result.vue", line: 25, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 48, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/components/claim-progress.vue", line: 24, from: "icon-choose_done", to: "icon-choose_done_v3", type: "icon_class" },
  { file: "src/components/claim-progress.vue", line: 24, from: "icon-choose_done", to: "icon-choose_done_v3", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 44, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 44, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/components/w-input/w-input.vue", line: 25, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/wy-input.vue", line: 14, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 38, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 75, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/face-auth-result/face-auth-result.vue", line: 6, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 77, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 101, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 132, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 179, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/w-input/w-input.vue", line: 25, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/wy-input.vue", line: 14, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 38, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 75, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/face-auth-result/face-auth-result.vue", line: 6, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 77, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 101, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 132, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 179, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/half-layer.vue", line: 8, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/components/half-layer.vue", line: 8, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 173, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 179, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 185, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 191, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 197, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 285, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 290, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 295, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 300, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 305, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 173, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 179, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 185, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 191, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 197, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 285, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 290, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 295, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 300, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 305, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/pages/confirm-info/confirm-info.vue", line: 11, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/confirm-info/confirm-info.vue", line: 11, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 9, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/order-cancel/components/baseInfo.vue", line: 5, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/image-material/components/doc-upload.vue", line: 9, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/order-cancel/components/baseInfo.vue", line: 5, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 59, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/pages/apply-result/components/check-status.vue", line: 59, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
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
