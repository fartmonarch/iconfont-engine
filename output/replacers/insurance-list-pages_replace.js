// insurance-list-pages 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "public/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_806066_ow7azo4zaoi.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/components/cell/index.js", line: 5, from: "//res.winbaoxian.com/ali-iconfont/font_806066_ow7azo4zaoi.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/components/preserve-apply-item.vue", line: 39, from: "icon-arrows_down", to: "icon-arrows_down_v4", type: "icon_class" },
  { file: "src/components/preserve-apply-item.vue", line: 142, from: "icon-arrows_down", to: "icon-arrows_down_v4", type: "icon_class" },
  { file: "src/components/cell/c-cell.vue", line: 32, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/notice-board.vue", line: 13, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index-main.vue", line: 11, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index-main.vue", line: 79, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index-main.vue", line: 130, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index-main.vue", line: 145, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index-main.vue", line: 174, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index-main.vue", line: 214, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index-main.vue", line: 227, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index-old.vue", line: 16, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index-old.vue", line: 27, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index-old.vue", line: 32, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index.vue", line: 36, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index.vue", line: 51, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index.vue", line: 63, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index.vue", line: 103, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/claim-home/index.vue", line: 128, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/group-renewal-recommend/index.vue", line: 9, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/modify-history/check-status.vue", line: 18, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/modify-history/check-status.vue", line: 32, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/modify-history/check-status.vue", line: 38, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/modify-history/check-status.vue", line: 56, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/modify-index/modify-index.vue", line: 14, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/modify-index/modify-index.vue", line: 20, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/preserve-entry/App.vue", line: 22, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/preserve-home/app.vue", line: 12, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/preserve-home/app.vue", line: 25, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/preserve-home/app.vue", line: 33, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/preserve-home/app.vue", line: 47, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/preserve-home/index.vue", line: 14, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/preserve-home/index.vue", line: 21, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/preserve-home/index.vue", line: 27, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/preserve-home/index.vue", line: 36, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/preserve-home/index.vue", line: 44, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/preserve-home/index.vue", line: 50, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/preserve-apply-item.vue", line: 40, from: "icon-arrows_up", to: "icon-arrows_up_v4", type: "icon_class" },
  { file: "src/components/preserve-apply-item.vue", line: 143, from: "icon-arrows_up", to: "icon-arrows_up_v4", type: "icon_class" },
  { file: "src/components/preserve-apply-item-elec.vue", line: 5, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/components/preserve-apply-item.vue", line: 91, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/components/preserve-apply-item.vue", line: 135, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/components/preserve-apply-item.vue", line: 153, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-elec-policy-list/App.vue", line: 35, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-invoice-list/index.vue", line: 60, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/apply-paper-policy-list/App.vue", line: 31, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/bind/index.vue", line: 34, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/modify-history/check-status.vue", line: 28, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/components/claim-progress.vue", line: 24, from: "icon-choose_done", to: "icon-choose_done_v3", type: "icon_class" },
  { file: "src/components/preserve-apply-item-elec.vue", line: 8, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/components/preserve-apply-item.vue", line: 92, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/components/preserve-apply-item.vue", line: 136, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/components/preserve-apply-item.vue", line: 154, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/pages/apply-elec-policy-list/App.vue", line: 36, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/pages/apply-invoice-list/index.vue", line: 61, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/pages/apply-paper-policy-list/App.vue", line: 32, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/pages/bind/index.vue", line: 35, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/components/input.vue", line: 8, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/notice-board.vue", line: 14, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/search-bar.vue", line: 17, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/wy-input.vue", line: 14, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/modify-history/check-status.vue", line: 48, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/half-layer.vue", line: 8, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/components/pop-up-claim-index.vue", line: 6, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/bind/index.vue", line: 44, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/apply-elec-policy-list/App.vue", line: 8, from: "icon-edit", to: "icon-edit_v3", type: "icon_class" },
  { file: "src/pages/modify-list/modify-list.vue", line: 3, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/components/search-bar.vue", line: 6, from: "icon-search", to: "icon-search_v2", type: "icon_class" },
  { file: "src/pages/apply-claim-list/index.vue", line: 13, from: "icon-search", to: "icon-search_v2", type: "icon_class" },
  { file: "src/pages/my-claim-list/index.vue", line: 33, from: "icon-search", to: "icon-search_v2", type: "icon_class" },
  { file: "src/pages/apply-claim-list/index.vue", line: 31, from: "icon-inform", to: "icon-inform_v1", type: "icon_class" },
  { file: "src/pages/group-renewal-recommend/index.vue", line: 16, from: "icon-inform", to: "icon-inform_v1", type: "icon_class" },
  { file: "src/pages/modify-history/check-status.vue", line: 8, from: "icon-notify", to: "icon-notify_v2", type: "icon_class" },
  { file: "src/pages/preserve-home/index.vue", line: 18, from: "icon-means", to: "icon-means_v3", type: "icon_class" },
  { file: "src/pages/preserve-home/index.vue", line: 41, from: "icon-means", to: "icon-means_v3", type: "icon_class" },
  { file: "src/pages/preserve-home/index.vue", line: 25, from: "icon-history", to: "icon-history_v2", type: "icon_class" },
  { file: "src/pages/preserve-home/index.vue", line: 48, from: "icon-history", to: "icon-history_v2", type: "icon_class" },
  { file: "src/pages/bind/index.vue", line: 12, from: "icon-key", to: "icon-key_v2", type: "icon_class" },
  { file: "src/pages/modify-index/modify-index.vue", line: 11, from: "icon-bill", to: "icon-bill_v1", type: "icon_class" },
  { file: "src/pages/modify-index/modify-index.vue", line: 17, from: "icon-bill", to: "icon-bill_v1", type: "icon_class" },
  { file: "src/pages/preserve-home/index.vue", line: 11, from: "icon-bill", to: "icon-bill_v1", type: "icon_class" },
  { file: "src/pages/preserve-home/index.vue", line: 33, from: "icon-bill", to: "icon-bill_v1", type: "icon_class" },
  { file: "src/pages/modify-history/insure-detail.vue", line: 13, from: "icon-new_line", to: "icon-new_line_v3", type: "icon_class" },
  { file: "src/pages/modify-history/insure-detail.vue", line: 17, from: "icon-new_line", to: "icon-new_line_v3", type: "icon_class" },
  { file: "src/pages/modify-history/insure-detail.vue", line: 21, from: "icon-new_line", to: "icon-new_line_v3", type: "icon_class" },
  { file: "src/pages/modify-history/insure-detail.vue", line: 25, from: "icon-new_line", to: "icon-new_line_v3", type: "icon_class" },
  { file: "src/pages/modify-history/insure-detail.vue", line: 29, from: "icon-new_line", to: "icon-new_line_v3", type: "icon_class" },
  { file: "src/pages/modify-history/insure-detail.vue", line: 33, from: "icon-new_line", to: "icon-new_line_v3", type: "icon_class" },
  { file: "src/pages/modify-history/insure-detail.vue", line: 37, from: "icon-new_line", to: "icon-new_line_v3", type: "icon_class" },
  { file: "src/pages/modify-history/insure-detail.vue", line: 41, from: "icon-new_line", to: "icon-new_line_v3", type: "icon_class" },
  { file: "src/pages/modify-history/insure-detail.vue", line: 45, from: "icon-new_line", to: "icon-new_line_v3", type: "icon_class" },
  { file: "src/pages/modify-history/insure-detail.vue", line: 49, from: "icon-new_line", to: "icon-new_line_v3", type: "icon_class" },
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
