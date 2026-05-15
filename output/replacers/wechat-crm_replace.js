// wechat-crm 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "src/pages/activity/app.vue", line: 201, from: "../home/style/iconfont.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/activity/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_280767_3owth2dyrnpl23xr.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/activity-detail/app.vue", line: 237, from: "../home/style/iconfont.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/activity-detail/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_280767_3owth2dyrnpl23xr.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/center/main.vue", line: 58, from: "../home/style/iconfont.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/custody-confirm/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_280767_3owth2dyrnpl23xr.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/custody-login/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_280767_3owth2dyrnpl23xr.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/custody-result/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_280767_3owth2dyrnpl23xr.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/debug-cookie/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_280767_3owth2dyrnpl23xr.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/dingtalk-qrcode/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_280767_3owth2dyrnpl23xr.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/dingtalk-signin/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_280767_3owth2dyrnpl23xr.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/home/main.vue", line: 197, from: "./style/iconfont.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/invation/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_280767_3owth2dyrnpl23xr.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/login/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_280767_3owth2dyrnpl23xr.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/platform-operate/index.vue", line: 62, from: "../home/style/iconfont.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "src/pages/static/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_280767_3owth2dyrnpl23xr.css", to: "iconfont_merged.css", type: "css_link" },
  { file: "userConf/createDemo/index.html", line: 10, from: "//res.winbaoxian.com/ali-iconfont/font_280767_3owth2dyrnpl23xr.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/pages/home/pages/income/index.vue", line: 11, from: "icon-arrows_down", to: "icon-arrows_down_v4", type: "icon_class" },
  { file: "src/pages/home/pages/income/index.vue", line: 23, from: "icon-arrows_down", to: "icon-arrows_down_v4", type: "icon_class" },
  { file: "src/pages/home/pages/income/index.vue", line: 35, from: "icon-arrows_down", to: "icon-arrows_down_v4", type: "icon_class" },
  { file: "src/components/calendar-function/activity-time-select/index.vue", line: 13, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/calendar-function/activity-time-select/index.vue", line: 14, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/calendar-function/activity-time-select/time-select.vue", line: 15, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/calendar-function/operate-time-select/index.vue", line: 13, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/calendar-function/operate-time-select/index.vue", line: 14, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/calendar-function/operate-time-select/time-select.vue", line: 17, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/calendar-function/personal-operate.vue", line: 11, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/calendar-function/personal-operate.vue", line: 16, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/calendar-function/progress-expert/confirm-info.vue", line: 16, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/calendar-function/progress-expert/confirm-info.vue", line: 25, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/calendar-function/progress-sign/modal.vue", line: 21, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/router-forms/index.vue", line: 38, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/components/router-forms/index.vue", line: 74, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/center/pages/center.vue", line: 13, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/center/pages/center.vue", line: 14, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/center/pages/center.vue", line: 15, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/center/pages/friend.vue", line: 8, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/center/pages/mine-attention.vue", line: 5, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/customer-detail/components/client-member.vue", line: 17, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/customer-detail/components/client-member.vue", line: 30, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/customer-detail/components/client-member.vue", line: 82, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/customer-detail/components/detail-block.vue", line: 6, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/customer-detail/components/other-info.vue", line: 94, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/detail/components/client-member.vue", line: 17, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/detail/components/client-member.vue", line: 30, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/detail/components/client-member.vue", line: 82, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/detail/components/detail-block.vue", line: 6, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/detail/components/operate-tactisc-activity.vue", line: 13, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/detail/components/operate-tactisc-meetlist.vue", line: 7, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/detail/components/other-info.vue", line: 94, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/components/behaviour-manager/behaviour-form.vue", line: 21, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/components/behaviour-manager/behaviour-form.vue", line: 32, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/components/behaviour-manager/behaviour-form.vue", line: 35, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/components/behaviour-manager/behaviour-form.vue", line: 46, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/components/behaviour-manager/behaviour-form.vue", line: 49, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/components/behaviour-manager/behaviour-users.vue", line: 12, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/components/behaviour-manager/behaviour-users.vue", line: 15, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/calendar_/components/calendar/index.vue", line: 14, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/calendar_/components/event-sign.vue", line: 33, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/calendar_/components/remind.vue", line: 5, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/client-cmn/index.vue", line: 24, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/customer/components/customers/sign-ceremony.vue", line: 32, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/customer/components/recieve.vue", line: 7, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/customer/components/year-data.vue", line: 5, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/customer/components/year-data.vue", line: 6, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/customer/components/year-data.vue", line: 7, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/index/components/name-card.vue", line: 16, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/index/components/target-block/target-client.vue", line: 4, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/index/components/target-block/target-item.vue", line: 4, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/index/components/target-block/target-item.vue", line: 17, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/index/components/target-block/target-sign.vue", line: 4, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/index/index.vue", line: 8, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/meet/components/house-present.vue", line: 8, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/meet/components/house-present.vue", line: 26, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/meet/meet-list.vue", line: 8, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/rights/index.vue", line: 5, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/rights/index.vue", line: 41, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/rights/index.vue", line: 80, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/rights/index.vue", line: 144, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/platform-operate/club-serve/components/house-present.vue", line: 7, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/platform-operate/club-serve/components/house-present.vue", line: 18, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/home/pages/calendar_/components/calendar/index.vue", line: 8, from: "icon-arrows_left", to: "icon-arrows_left_v2", type: "icon_class" },
  { file: "src/pages/home/pages/calendar_/components/event-sign.vue", line: 27, from: "icon-arrows_left", to: "icon-arrows_left_v2", type: "icon_class" },
  { file: "src/pages/home/pages/rights/index.vue", line: 118, from: "icon-arrows_left", to: "icon-arrows_left_v2", type: "icon_class" },
  { file: "src/pages/custody-confirm/components/form/index.vue", line: 27, from: "icon-choose_done_line", to: "icon-choose_done_line_v2", type: "icon_class" },
  { file: "src/pages/custody-login/components/form/index.vue", line: 25, from: "icon-choose_done_line", to: "icon-choose_done_line_v2", type: "icon_class" },
  { file: "src/pages/custody-confirm/components/form/index.vue", line: 28, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/custody-login/components/form/index.vue", line: 26, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/activity/components/list-tab-c.vue", line: 14, from: "icon-choose_done", to: "icon-choose_done_v3", type: "icon_class" },
  { file: "src/pages/activity/components/list-tab.vue", line: 13, from: "icon-choose_done", to: "icon-choose_done_v3", type: "icon_class" },
  { file: "src/pages/activity-detail/app.vue", line: 24, from: "icon-choose_done", to: "icon-choose_done_v3", type: "icon_class" },
  { file: "src/pages/center/pages/activity.vue", line: 21, from: "icon-choose_done", to: "icon-choose_done_v3", type: "icon_class" },
  { file: "src/pages/center/pages/activity.vue", line: 41, from: "icon-choose_done", to: "icon-choose_done_v3", type: "icon_class" },
  { file: "src/pages/home/components/sick-pop.vue", line: 7, from: "icon-close_circle_line", to: "icon-close_circle_line_v1", type: "icon_class" },
  { file: "src/pages/oa/components/approval-flow.vue", line: 17, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/components/calendar-function/activity-time-select/time-select.vue", line: 12, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/components/calendar-function/operate-time-select/time-select.vue", line: 14, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/components/pop-up.vue", line: 16, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/customer-detail/components/detail-header-info.vue", line: 23, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/detail/components/detail-header-info.vue", line: 23, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/detail/components/operate-tactisc-activity.vue", line: 101, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/home/components/behaviour-manager/behaviour-form.vue", line: 44, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/home/pages/income/index.vue", line: 190, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/home/pages/meet/components/duty-list.vue", line: 8, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/home/pages/meet/components/house-present.vue", line: 31, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/platform-operate/club-serve/components/duty-list.vue", line: 8, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/platform-operate/club-serve/components/house-present.vue", line: 23, from: "icon-close_line", to: "icon-close_line_v2", type: "icon_class" },
  { file: "src/pages/home/components/behaviour-manager/behaviour-form.vue", line: 41, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/home/pages/meet/components/duty-list.vue", line: 3, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/home/pages/meet/components/house-present.vue", line: 7, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/home/pages/meet/components/house-present.vue", line: 11, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/platform-operate/club-serve/components/duty-list.vue", line: 3, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/platform-operate/club-serve/components/house-present.vue", line: 6, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/platform-operate/club-serve/components/house-present.vue", line: 10, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/home/pages/calendar_/components/remind.vue", line: 4, from: "icon-news", to: "icon-news_v3", type: "icon_class" },
  { file: "src/components/router-forms/index.vue", line: 30, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/home/pages/income/index.vue", line: 16, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/home/pages/income/index.vue", line: 28, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/home/pages/income/index.vue", line: 33, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/home/pages/income/index.vue", line: 40, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
  { file: "src/pages/activity-detail/app.vue", line: 16, from: "icon-approve_after", to: "icon-approve_after_v1", type: "icon_class" },
  { file: "src/pages/center/pages/detail.vue", line: 9, from: "icon-approve_after", to: "icon-approve_after_v1", type: "icon_class" },
  { file: "src/pages/center/pages/friend.vue", line: 28, from: "icon-approve_after", to: "icon-approve_after_v1", type: "icon_class" },
  { file: "src/pages/center/pages/mine-attention.vue", line: 24, from: "icon-approve_after", to: "icon-approve_after_v1", type: "icon_class" },
  { file: "src/pages/home/pages/invitation/index.vue", line: 14, from: "icon-location", to: "icon-location_v2", type: "icon_class" },
  { file: "src/components/pdf-preview.vue", line: 65, from: "icon-handbook", to: "icon-handbook_v1", type: "icon_class" },
  { file: "src/pages/home/pages/client/components/user-list-normal/user-item.vue", line: 57, from: "icon-birthday", to: "icon-birthday_v1", type: "icon_class" },
  { file: "src/pages/home/pages/customer/components/customers/list.vue", line: 10, from: "icon-birthday", to: "icon-birthday_v1", type: "icon_class" },
  { file: "src/pages/home/pages/customer/components/customers-new/gaoke-user-card.vue", line: 6, from: "icon-birthday", to: "icon-birthday_v1", type: "icon_class" },
  { file: "src/pages/home/pages/customer/components/customers-new/list.vue", line: 21, from: "icon-birthday", to: "icon-birthday_v1", type: "icon_class" },
  { file: "src/pages/home/pages/customer/components/project-list.vue", line: 10, from: "icon-birthday", to: "icon-birthday_v1", type: "icon_class" },
  { file: "src/pages/home/pages/gk365/index.vue", line: 20, from: "icon-birthday", to: "icon-birthday_v1", type: "icon_class" },
  { file: "src/pages/platform-operate/activity-rights/index.vue", line: 5, from: "icon-arrow_down", to: "icon-arrow_down_v2", type: "icon_class" },
  { file: "src/pages/platform-operate/activity-rights/index.vue", line: 7, from: "icon-arrow_down", to: "icon-arrow_down_v2", type: "icon_class" },
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
