// insurance-claims-2 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "index.html", line: 9, from: "//res.wyins.net/ali-iconfont/font_01jw0edrq1ev1jor.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "index.html", line: 10, from: "//res.wyins.net/ali-iconfont/font_111804_9z98t2tokmrhpvi.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "index.html", line: 11, from: "//res.wyins.net/ali-iconfont/font_590851_1dp59g7ssygjsjor.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "index.html", line: 12, from: "//res.winbaoxian.com/ali-iconfont/font_1964111_jn3xutqpl8l.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/pages/claim-material/claim-material-bankCard-modify.vue", line: 15, from: "icon-arrows_down", to: "icon-arrows_down_v4", type: "icon_class" },
  { file: "src/pages/claims-guide.vue", line: 11, from: "icon-arrows_down", to: "icon-arrows_down_v4", type: "icon_class" },
  { file: "src/components/evaluate-item.vue", line: 23, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/evaluate-item.vue", line: 40, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/notice-board.vue", line: 7, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-cost-selection.vue", line: 8, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-detail.vue", line: 138, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-bankCard-modify.vue", line: 35, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-bankCard-modify.vue", line: 102, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-bankCard.vue", line: 14, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-bankCard.vue", line: 191, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-report-modify.vue", line: 46, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-report-modify.vue", line: 48, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-report-modify.vue", line: 61, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-report-modify.vue", line: 96, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-report.vue", line: 96, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-report.vue", line: 98, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-report.vue", line: 156, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-video-modify.vue", line: 13, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-bankCard-modify.vue", line: 36, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-bankCard-modify.vue", line: 49, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-bankCard.vue", line: 42, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-bankCard.vue", line: 66, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-report.vue", line: 72, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-report.vue", line: 93, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-report.vue", line: 158, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-report.vue", line: 162, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-report.vue", line: 235, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-report.vue", line: 254, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-report.vue", line: 278, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/easy-claim.vue", line: 32, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/easy-claim.vue", line: 48, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/index.vue", line: 15, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/index.vue", line: 25, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/index.vue", line: 29, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/material-submitted.vue", line: 58, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claims-guide.vue", line: 11, from: "icon-arrows_up", to: "icon-arrows_up_v4", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 222, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/bind/bindSuccess.vue", line: 4, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/bind/bindUser.vue", line: 34, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-doc-upload-report.vue", line: 32, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-doc-upload.vue", line: 32, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/material-submitted.vue", line: 26, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/components/claimsucess-progress.vue", line: 35, from: "icon-choose_done", to: "icon-choose_done_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-progress-port.vue", line: 37, from: "icon-choose_done", to: "icon-choose_done_v3", type: "icon_class" },
  { file: "src/pages/claim-material/claim-progress.vue", line: 37, from: "icon-choose_done", to: "icon-choose_done_v3", type: "icon_class" },
  { file: "src/pages/bind/bindUser.vue", line: 35, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-doc-upload-report.vue", line: 31, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-doc-upload.vue", line: 31, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 56, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 91, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 224, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 335, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 388, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 403, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/input.vue", line: 8, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/notice-board.vue", line: 8, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/wy-input.vue", line: 14, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/bind/bindFail.vue", line: 4, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-doc-upload-report.vue", line: 43, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-doc-upload-report.vue", line: 69, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-doc-upload.vue", line: 43, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-doc-upload.vue", line: 69, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-report.vue", line: 27, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/claim-material/images-detail.vue", line: 13, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/claimsucess-progress.vue", line: 42, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/components/half-layer.vue", line: 8, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/components/pop-up-shanpei.vue", line: 5, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/bind/bindUser.vue", line: 44, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/components/star.vue", line: 6, from: "icon-collect_line", to: "icon-collect_line_v3", type: "icon_class" },
  { file: "src/components/star.vue", line: 7, from: "icon-collect_line", to: "icon-collect_line_v3", type: "icon_class" },
  { file: "src/components/star.vue", line: 8, from: "icon-collect_line", to: "icon-collect_line_v3", type: "icon_class" },
  { file: "src/components/star.vue", line: 9, from: "icon-collect_line", to: "icon-collect_line_v3", type: "icon_class" },
  { file: "src/components/star.vue", line: 10, from: "icon-collect_line", to: "icon-collect_line_v3", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 422, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 426, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 430, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 434, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 438, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 487, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 490, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 493, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 496, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 499, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/star.vue", line: 15, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/star.vue", line: 16, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/star.vue", line: 17, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/star.vue", line: 18, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/star.vue", line: 19, from: "icon-collect_surface", to: "icon-collect_surface_v1", type: "icon_class" },
  { file: "src/components/imgViews.vue", line: 28, from: "icon-download", to: "icon-download_v2", type: "icon_class" },
  { file: "src/components/imgViews.vue", line: 28, from: "icon-download", to: "icon-download_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-report.vue", line: 116, from: "icon-edit", to: "icon-edit_v3", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-report.vue", line: 183, from: "icon-edit", to: "icon-edit_v3", type: "icon_class" },
  { file: "src/pages/claim-detail.vue", line: 118, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/fill-logistics.vue", line: 66, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/my-claim.vue", line: 26, from: "icon-search", to: "icon-search_v2", type: "icon_class" },
  { file: "src/pages/claim-material-list.vue", line: 4, from: "icon-inform", to: "icon-inform_v1", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-bankCard-modify.vue", line: 4, from: "icon-inform", to: "icon-inform_v1", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-video-modify copy.vue", line: 4, from: "icon-inform", to: "icon-inform_v1", type: "icon_class" },
  { file: "src/pages/claim-port/claim-port-video-modify.vue", line: 4, from: "icon-inform", to: "icon-inform_v1", type: "icon_class" },
  { file: "src/pages/my-claim.vue", line: 44, from: "icon-inform", to: "icon-inform_v1", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 24, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 48, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 105, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/claim-flow.vue", line: 36, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/claim-material/claim-doc-upload-report.vue", line: 12, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/claim-material/claim-doc-upload.vue", line: 12, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-bankCard.vue", line: 37, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 7, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 33, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 135, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 163, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/components/check-status.vue", line: 181, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-group-material.vue", line: 4, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-bankCard-modify.vue", line: 4, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-bankCard.vue", line: 5, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-bankCard.vue", line: 43, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-report-modify.vue", line: 4, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/pages/claim-material/claim-material-video-modify.vue", line: 4, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/pages/bind/bindUser.vue", line: 12, from: "icon-key", to: "icon-key_v2", type: "icon_class" },
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
