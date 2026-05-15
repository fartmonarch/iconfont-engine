// payment-cashier-mobile 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
  { file: "index.html", line: 7, from: "//res.winbaoxian.com/ali-iconfont/font_280767_yehzob4ie8kt9.css", to: "iconfont_merged.css", type: "css_link" },
  // 图标类名替换
  { file: "src/components/OrderDetail.vue", line: 16, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/pay-home/PayHome.vue", line: 48, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/pay-home/PayHome.vue", line: 69, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/pay-home/PayHome.vue", line: 72, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/pay-quickmoney/pay-quickmoney.vue", line: 40, from: "icon-arrows_right", to: "icon-arrows_right_v3", type: "icon_class" },
  { file: "src/pages/pay-quickmoney/pay-quickmoney.vue", line: 81, from: "icon-choose_done_line", to: "icon-choose_done_line_v2", type: "icon_class" },
  { file: "src/pages/union-pay/UnionPay.vue", line: 54, from: "icon-choose_done_line", to: "icon-choose_done_line_v2", type: "icon_class" },
  { file: "src/pages/pay-home/PayHome.vue", line: 105, from: "icon-choose_done_surface", to: "icon-choose_done_surface_v2", type: "icon_class" },
  { file: "src/pages/pay-quickmoney/pay-quickmoney.vue", line: 80, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/pages/union-pay/UnionPay.vue", line: 53, from: "icon-choose_none_line", to: "icon-choose_none_line_v2", type: "icon_class" },
  { file: "src/pages/pay-home/PayHome.vue", line: 123, from: "icon-close_circle_surface", to: "icon-close_circle_surface_v2", type: "icon_class" },
  { file: "src/pages/alipay-contract/alipay-contract.vue", line: 12, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/pay-home/PayHome.vue", line: 88, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/pay-quickmoney/pay-quickmoney.vue", line: 13, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/union-pay/UnionPay.vue", line: 26, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/pages/wechat-contract/wechat-contract.vue", line: 13, from: "icon-help", to: "icon-help_v5", type: "icon_class" },
  { file: "src/components/TopTip.vue", line: 4, from: "icon-inform", to: "icon-inform_v1", type: "icon_class" },
  { file: "src/pages/pay-home/PayHome.vue", line: 25, from: "icon-common_problem", to: "icon-common_problem_v4", type: "icon_class" },
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
