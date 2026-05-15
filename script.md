# 脚本清单

本文档汇总了 iconfont-engine 项目已收集和计划编写的全部脚本文件。

## 命名规范

```
{Phase序号}_{功能模块}_{源文件名}.js
```

例：`01_scan_repos_clone_repos.js`、`06_detect_conflicts_iconfont_compare.js`

---

## 脚本总览

| #   | 目标路径                                                 | 来源                          | 语言    | 对应 Phase | 状态                                                                   | 说明                                                                                         |
| --- | -------------------------------------------------------- | ----------------------------- | ------- | ---------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| 01  | `pipeline/01_scan_repos_clone_repos.js`                  | codeup-clone skill            | Node.js | Phase 1    | 🟢 已完成                                                               | 批量克隆 Codeup 仓库，HTTPS→SSH 转换、去重、超时控制                                         |
| 02  | `pipeline/01_scan_repos_iconfont_check.js`               | **重写**                      | Node.js | Phase 1    | 🟢 已完成                                                               | 单项目全局扫描：源码扫描 + webpack模板变量替换 + CDN去重 + 注释过滤 + 完整文件读取（不截断） |
| 03  | `pipeline/01_scan_repos_iconfont_scan_multi.js`          | **重写**                      | Node.js | Phase 1    | 🟢 已完成                                                               | 多项目扫描 + 20手动链接整合 → 111个CSS链接，输出 all_iconfont_links.json + iconfont_urls.txt |
| 04  | `pipeline/02_resolve_download_assets.js`                 | **新编写**                    | Node.js | Phase 2    | 🟢 已完成                                                               | 下载 110/111 CSS + 110 TTF，gzip/相对路径修复，输出 assets_manifest.json                     |
| 05  | `pipeline/02_resolve_parse_css_mappings.js`              | **新编写**                    | Node.js | Phase 2    | 🟢 已完成                                                               | 11494 个图标映射提取，symbol 逗号 selector 修复，输出 css_mappings.json                      |
| 06  | `pipeline/02_resolve_validate_assets.js`                 | **新编写**                    | Node.js | Phase 2    | 🟢 已完成                                                               | TTF header 校验 + 文件完整性检查，输出 assets_validation.json                                |
| 06  | `pipeline/03_extract_glyphs.py`                          | **新编写**                    | Python  | Phase 3    | 🟢 已完成                                                               | 解析 110 TTF，提取 cmap/contours/hmtx，11528 条 glyph 记录，0 错误                           |
| 07  | `pipeline/04_normalize_glyphs.py`                        | **新编写**                    | Python  | Phase 4    | 🟢 已完成                                                               | UPM 统一(1024)、contour 排序、起点统一、精度 round(6)、glyphHash(sha256) + 17 单元测试       |
| 07b | `pipeline/test_04_normalize.py`                          | **新编写**                    | Python  | Phase 4    | 🟢 已完成                                                               | 17 个单元测试覆盖所有标准化函数                                                              |
| 08  | `pipeline/05_build_registry.py`                          | **新编写**                    | Python  | Phase 5    | 🟢 已完成                                                               | glyphHash 分组、canonical 选择、alias 收集、source tracking + 12 单元测试                    |
| 08b | `pipeline/test_05_registry.py`                           | **新编写**                    | Python  | Phase 5    | 🟢 已完成                                                               | 12 个单元测试覆盖分组、canonical、alias、source、确定性输出                                  |
| 08c | `pipeline/04_normalize_glyphs.py`                        | **修改**                      | Python  | Phase 4    | 🟢 已完成                                                               | round 精度 6→4，减少坐标微小差异导致的假阳性                                                 |
| 09  | `pipeline/06_detect_conflicts.py`                        | **新编写**                    | Python  | Phase 6    | 🟢 已完成                                                               | 1,698 冲突记录检测（Type A/B/C）+ 16 单元测试                                                |
| 09b | `pipeline/test_06_conflicts.py`                          | **新编写**                    | Python  | Phase 6    | 🟢 已完成                                                               | 16 个单元测试覆盖冲突检测核心函数                                                            |
| 09c | `pipeline/_visual_similarity.js`                         | **新编写**                    | Node.js | Phase 6.5  | 🟢 已完成                                                               | @napi-rs/canvas 像素渲染比对，64x64 bitmap 比较                                              |
| 09d | `pipeline/06_5_filter_false_positives.py`                | **新编写**                    | Python  | Phase 6.5  | 🟢 已完成                                                               | 视觉相似度为主 + 几何相似度 fallback，minScore 判断                                          |
| 09e | `pipeline/06_8_apply_name_resolution.py`                 | **新编写**                    | Python  | Phase 6.8  | 🟢 已完成                                                               | Type B 决策应用：保留组合并 + PUA 组重命名 `_v2`/`_v3` + 编码释放                            |
| 09f | `pipeline/07_generate_resolver_ui.py`                    | **增强**                      | Python  | Phase 7    | 🟢 已完成                                                               | 审核 UI 生成：支持 `--type-filter` 参数化过滤 + Type A/B 分阶段审核                          |
| 09g | `pipeline/gen_name_mapping.py`                           | **新编写**                    | Python  | Phase 6.8  | 🟢 已完成                                                               | 生成 name_resolution_mapping.md（Name → Unicode 溯源映射表）                                 |
| 10  | `pipeline/06_detect_conflicts_iconfont_compare.js`       | iconfont-superset-check skill | Node.js | Phase 6    | 双链接模式 B：判断两个 iconfont 链接的超集关系，生成对比报告           |
| 10  | `pipeline/06_detect_conflicts_iconfont_conflicts_doc.js` | iconfont_merge                | Node.js | Phase 6    | 按图标逐个生成冲突清单 HTML，含 SVG 预览                               |
| 11  | `pipeline/07_resolve_conflicts_apply_rename.js`          | iconfont_merge                | Node.js | Phase 7    | 仓库级图标类名替换（带边界匹配、临时标记两遍替换、互换算子处理）       |
| 12  | `pipeline/07_resolve_conflicts_apply_alias.js`           | iconfont-superset-check skill | Node.js | Phase 7    | 别名替换模式 D：从扫描结果中提取匹配映射，自动替换项目中的旧 icon 类名 |
| 13  | `pipeline/07_resolve_conflicts_cmp_replace_test.js`      | iconfont_merge                | Node.js | Phase 7    | 替换算法对比测试：简单替换 vs 边界匹配替换                             |
| 14  | `pipeline/07_resolve_conflicts_cmp2_test.js`             | iconfont_merge                | Node.js | Phase 7    | 单文件替换算法验证对比                                                 |
| 15  | `pipeline/08_merge_glyf.py`                              | **新编写**                    | Python  | Phase 8-9  | 🟢 已完成                                                               | glyph deep copy、cmap rebuild、hmtx normalize、TTF/WOFF2/CSS/JSON/HTML 输出                  |
| 16  | ~~`pipeline/09_build_font.py`~~                          | ~~待编写~~                    | Python  | Phase 9    | 🟢 已合并到 Phase 8                                                     | 合并到 08_merge_glyf.py                                                                      |
| 17  | `pipeline/10_validate_render.js`                         | **新编写**                    | Node.js | Phase 10   | 🟢 已完成                                                               | Chrome/Firefox 渲染对比、pixel diff、输出 diff report（Playwright + pixelmatch）             |
| 18  | `pipeline/11_generate_manifest.js`                       | **新编写**                    | Node.js | Phase 11   | 🟢 已完成                                                               | merge_manifest.json + demo_index.html + phase11_output.md                                    |
| 19  | `pipeline/07_apply_typea_resolution.py`                  | **新编写**                    | Python  | Phase 7    | 🟢 已完成                                                               | Type A 决策三段处理：用户决策107条 + typea_data补全 + fallback自动PUA分配 → Type A清零       |
| 20  | `pipeline/07_resolve_conflicts.py`                       | **新编写**                    | Python  | Phase 7    | 🟢 已完成                                                               | 生成 phase7_resolution.json（747 entries，全含registry，单来源标记 single_source）           |
| 21  | `pipeline/12_package_output.js`                          | **新编写**                    | Node.js | Phase 11   | 🟢 已完成                                                               | 生成 output/package/（iconfont.ttf/woff2/css/json + demo_index.html，标准分发包）            |
| 22  | `pipeline/13_enhance_lineage.py`                         | **新编写**                    | Python  | Phase 13   | 🟢 已完成                                                               | 增强 lineage.json：注入 replacement 字段（nameChanged/unicodeChanged/新旧值）                |
| 23  | `pipeline/14_generate_replacer.js`                       | **新编写**                    | Node.js | Phase 14   | 🟢 已完成                                                               | 按项目生成替换脚本 output/replacers/<proj>_replace.js + 替换指南 report/replacement_guides/  |
| 24  | `pipeline/15_rebuild_resolver_data.py`                   | **新编写**                    | Python  | Phase 15   | 🟢 已完成                                                               | 重建 conflict_resolver_data.json 含 lineage resolved 完整数据                                |
| 25  | `pipeline/16_apply_replacements.js`                      | **待编写**                    | Node.js | Phase 16   | 🔵 待执行                                                               | 替换执行器：接收 --project/--repo-dir/--css-cdn-url，应用 replacer 规则到实际仓库            |

---

## 来源明细

### A. `iconfont-superset-check` skill（5 个）

路径：`C:\Users\win-boweng\.claude\skills\iconfont-superset-check\scripts\`

| 文件                       | 目标编号 | 说明                              |
| -------------------------- | -------- | --------------------------------- |
| `iconfont_check.js`        | 02       | 模式 A：单链接超集检查 + 自动替换 |
| `iconfont_compare.js`      | 09       | 模式 B：双链接超集对比            |
| `iconfont_scan_multi.js`   | 03       | 模式 C：多项目批量扫描            |
| `iconfont_apply_alias.js`  | 12       | 模式 D：别名类名替换              |
| `iconfont_file_compare.js` | 05       | 模式 E：URL/本地文件混合对比      |

### B. `codeup-clone` skill（1 个）

路径：`C:\Users\win-boweng\.claude\skills\codeup-clone\scripts\`

| 文件             | 目标编号 | 说明                 |
| ---------------- | -------- | -------------------- |
| `clone_repos.js` | 01       | 批量克隆 Codeup 仓库 |

### C. 参考脚本（不迁入 pipeline）

| 文件                                                                                          | 说明                                                     |
| --------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| `D:\work\build_superset.js`                                                                   | CSS 下载 + @font-face 解析逻辑可参考（已验证可正常下载） |
| `C:\Users\win-boweng\.claude\skills\iconfont-superset-check\scripts\iconfont_file_compare.js` | URL/本地文件混合对比，可参考 CSS 解析模式                |

### D. `D:\work\iconfont_merge\`（6 个脚本 + 1 个文档）

| 文件                          | 目标编号 | 说明                             |
| ----------------------------- | -------- | -------------------------------- |
| `gen_merged_demo.js`          | 18       | 合并字体 demo 预览页             |
| `iconfont_conflicts_doc.js`   | 10       | 冲突图标清单 HTML（含 SVG 预览） |
| `apply_rename_to_projects.js` | 11       | 仓库级类名替换引擎               |
| `_cmp_replace.js`             | 13       | 替换算法对比测试                 |
| `_cmp2.js`                    | 14       | 单文件替换验证                   |
| `GPT_ttf合并流程规范.md`      | —        | 参考文档（TTF 合并流程规范）     |

### E. 待编写（1 个）

| 编号 | 文件                                | 语言    | 说明                                                                         |
| ---- | ----------------------------------- | ------- | ---------------------------------------------------------------------------- |
| 25   | `pipeline/16_apply_replacements.js` | Node.js | 替换执行器：--project/--repo-dir/--css-cdn-url，应用 replacer 脚本到实际仓库 |

---

## 扫描语义

Phase 1 全程脚本覆盖扫描的是**"文本里存在的完整链接"**，而不是**"运行时最终生效的链接"**。

- **做了什么**：脚本扫描源码文件中所有文本形式的 iconfont 链接（含 CDN、本地 CSS、模板变量替换后的真实路径）
- **没做什么**：不判断运行时哪些链接实际生效（如环境差异、条件渲染、注释已过滤）
- **模板变量替换**：`<%= htmlWebpackPlugin.options.path %>` 等变量在提取阶段被替换为真实 CDN 路径，**后续 Phase 7 替换项目中 iconfont 链接时，需还原回模板变量形式**，以保持项目构建一致性

---

## 依赖汇总

### Node.js 脚本依赖

| 脚本                      | 关键依赖                                    |
| ------------------------- | ------------------------------------------- |
| 01 clone_repos            | `fs`, `path`, `child_process`（内置）       |
| 02 iconfont_check         | `cheerio`, `fonteditor-core`, `https`, `fs` |
| 03 iconfont_scan_multi    | `cheerio`, `fonteditor-core`, `https`, `fs` |
| 04 download_assets        | `https`, `http`, `fs`, `crypto`, `path`     |
| 05 parse_css_mappings     | `fs`, `path`, `regex`                       |
| 06 validate_assets        | `fs`, `path`                                |
| 09 iconfont_compare       | `cheerio`, `fonteditor-core`, `https`, `fs` |
| 10 iconfont_conflicts_doc | `fs`, `path`（内置）                        |
| 11 apply_rename           | `fs`, `path`（内置）                        |
| 12 apply_alias            | `fs`, `path`, `glob`（需确认）              |
| 13/14 cmp 测试            | `fs`, `path`（内置）                        |
| 18 gen_demo               | `fs`, `path`（内置）                        |

### Python 脚本依赖

| 脚本                | 关键依赖                                        |
| ------------------- | ----------------------------------------------- |
| 03 extract_glyphs   | `fontTools`, `hashlib`, `json`                  |
| 04 normalize_glyphs | `fontTools`, `numpy`（可选）, `json`            |
| 05 build_registry   | `fontTools`, `hashlib`, `sha256`, `json`        |
| 08 merge_glyf       | `fontTools`, `copy`, `json`                     |
| 09 build_font       | `fontTools` (FontBuilder), `subprocess` (woff2) |

---

## 状态图

```
Phase 1-2 扫描/解析  Phase 3-5 提取/注册  Phase 6-7 冲突治理     Phase 8-11 合并/输出  Phase 12-15 溯源/分发   Phase 16 替换
  [01-06] 🟢 ×6       [06-08] 🟢 ×4        [09-09g] 🟢 ×8          [15-21] 🟢 ×7          [22-24] 🟢 ×3            [25] 🔵 待编写
```

- 🟢 = 已完成  🔵 = 已规划待执行  🔧 = 已收集待迁移  ⬜ = 待编写
