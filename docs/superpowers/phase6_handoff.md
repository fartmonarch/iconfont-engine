# Phase 6–11 冲突解决与字体合并 Handoff

> 本文档记录截至 **2026-05-15** 的全链路完成状态。
> **所有冲突已清零，746-glyph 统一字体已生成。**
> 这是给下一个对话的交接文档，请务必先读完再操作。

---

## 1. 最终状态总览

| 指标             | 值                                |
| ---------------- | --------------------------------- |
| Registry entries | **747**（Type B 解决后，原 1346） |
| Type A 冲突      | **0**（原 401，全部解决）         |
| Type B 冲突      | **0**（原 392，全部解决）         |
| Type C Duplicate | **627**（正常多来源，已合并）     |
| False Positive   | **9**（已自动合并）               |
| 合并字体 glyphs  | **746**（1 条 no unicode 跳过）   |
| PUA 新分配范围   | E000–E0FF（~147 个）              |
| CSS aliases      | 66 个                             |

---

## 2. 输出文件

### 2.1 主要产出

| 文件                           | 说明                                               |
| ------------------------------ | -------------------------------------------------- |
| `output/iconfont_merged.ttf`   | 合并字体 TTF                                       |
| `output/iconfont_merged.woff2` | 合并字体 WOFF2                                     |
| `output/iconfont_merged.css`   | 完整 CSS（@font-face + 全量 icon class + aliases） |
| `output/iconfont_merged.json`  | 图标元数据（name/unicode/aliases/sources）         |
| `output/demo_index.html`       | 字体预览页（746 图标，PUA 标签仅 E000-E5FF）       |
| `output/merge_manifest.json`   | 构建元数据                                         |
| `output/package/`              | 标准分发包（iconfont.* 命名）                      |

### 2.2 Registry 文件

| 文件                                                          | 说明                                          |
| ------------------------------------------------------------- | --------------------------------------------- |
| `registry/glyph_registry.json`                                | 当前 registry（747 entries，Type A+B 全解决） |
| `registry/glyph_registry_resolved.json`                       | 最新 resolved 版本（同上）                    |
| `registry/glyph_registry_backup_before_typeb_resolution.json` | Type B 解决前备份（1346 entries）             |
| `registry/lineage.json`                                       | 全溯源链（含 assign_pua 记录）                |

### 2.3 决策文件

| 文件                                 | 说明                                              |
| ------------------------------------ | ------------------------------------------------- |
| `report/phase7_typeb_decisions.json` | Type B 人工审核决策（84 条）                      |
| `report/phase7_typea_decisions.json` | Type A 人工审核决策（101 条匹配）                 |
| `report/phase7_resolution.json`      | Phase 7 最终分辨结果（747 entries，Phase 8 输入） |

---

## 3. 全链路脚本执行顺序（重跑指南）

```bash
# 1. 从 Type B 前备份恢复
Copy-Item registry/glyph_registry_backup_before_typeb_resolution.json registry/glyph_registry.json

# 2. Phase 6 冲突检测（在原始 1346 registry 上）
python pipeline/06_detect_conflicts.py
python pipeline/06_5_filter_false_positives.py

# 3. Phase 6.8 应用 Type B 决策 → 747 entries
python pipeline/06_8_apply_name_resolution.py --decisions report/phase7_typeb_decisions.json
Copy-Item registry/glyph_registry_resolved.json registry/glyph_registry.json

# 4. Phase 6 重跑（在 747 registry 上）
python pipeline/06_detect_conflicts.py       # Type A=110, Type B=0
python pipeline/06_5_filter_false_positives.py

# 5. Phase 7 应用 Type A 决策 → Type A=0
python pipeline/07_apply_typea_resolution.py
Copy-Item registry/glyph_registry_resolved.json registry/glyph_registry.json

# 6. Phase 6 验证（Type A=0, Type B=0）
python pipeline/06_detect_conflicts.py
python pipeline/06_5_filter_false_positives.py

# 7. Phase 7 生成 phase7_resolution.json（747 entries）
python pipeline/07_resolve_conflicts.py

# 8. Phase 8-9 合并字体
python pipeline/08_merge_glyf.py

# 9. Phase 11 输出
node pipeline/11_generate_manifest.js
node pipeline/12_package_output.js
```

---

## 4. 冲突解决机制详解

### 4.1 Type B 解决（Phase 6.8）

脚本：`pipeline/06_8_apply_name_resolution.py`

- **False Positive 自动合并**：308 条（视觉相似度 minScore >= 0.90）
- **按人工决策合并**：84 条（`report/phase7_typeb_decisions.json`）
- **保留组**：合并到第一个变体编码，其他变体编码释放
- **PUA 组**：所有 variant 合并成 **1 条 entry**，分配 **1 个新 PUA 编码（E000+）**，命名规则 `原name_v2`

> **关键修复**（2026-05-15）：旧逻辑对 PUA 组每个 variant 各生成独立 entry，导致同字形多个 PUA 码。
> 修复后调用 `merge_variants_to_entry(group_variants, pua_name, pua=new_pua)` 合并为 1 条。

### 4.2 Type A 解决（Phase 7）

脚本：`pipeline/07_apply_typea_resolution.py`

三段处理逻辑：
1. **用户决策段**：从 `phase7_typea_decisions.json` + `conflict_resolver_typea_data.json` 建立 `id_to_record` 映射，应用 107 条手动决策
2. **typea_data 自动补全段**：处理 typea_data 中未完整分组的 variants，带 `keep_uc` 防重复判断
3. **fallback 段**：读取当前 `conflict_records.json` 处理 Type B 合并后产生的新冲突（按 sourceCount 保留最高的）

关键 ID 映射说明：`phase7_typea_decisions.json` 的 key 是 `conflict_resolver_typea_data.json` 的 id（546-722 范围），**不是** `conflict_records.json` 的数组下标。

### 4.3 phase7_resolution.json 生成（07_resolve_conflicts.py）

**修复**（2026-05-15）：`resolve_type_c_auto` 原来跳过 `len(sources) <= 1` 的单来源 entry，导致 ~87 个 glyph 丢失。
修复后包含全部 747 registry 条目（单来源标记 `resolution: 'single_source'`，多来源标记 `alias_merged`）。

---

## 5. PUA 编码规范

| 范围      | 含义                                 | Demo 标签     |
| --------- | ------------------------------------ | ------------- |
| E000–E5FF | Pipeline 新分配（Type A/B 冲突解决） | 橙色 PUA 标签 |
| E600–EAxx | 原始来源图标编码（iconfont.cn 分配） | 无标签        |

Demo HTML 判断：`parseInt(unicode, 16) >= 0xE000 && parseInt(unicode, 16) < 0xE600`

---

## 6. 关键数据变化链

```
原始 registry:   1346 entries
  ↓ Phase 6.8 Type B 解决（308 FP + 84 手动）
registry:         747 entries（-599）
  ↓ Phase 7 Type A 解决（107 手动 + fallback）
registry:         747 entries（只改 canonicalUnicode，不改条数）
  ↓ Phase 7 resolve_conflicts
phase7_resolution: 747 entries
  ↓ Phase 8-9 merge（跳过1条 no unicode）
merged font:      746 glyphs
```

---

## 7. 已知问题与待办

### 后续工作（字体已完成，进入替换阶段）

- [ ] **Phase 12/14：项目替换** — 用 `output/package/` 替换各前端项目的 iconfont 链接
  - 需要 `14_generate_replacer.js` 生成各项目的替换指南
  - `report/replacement_guides/` 已有部分项目的替换指南
- [ ] **Phase 13：溯源增强** — `13_enhance_lineage.py` 增强 lineage 数据
- [ ] **Phase 15：Resolver 数据重建** — `15_rebuild_resolver_data.py`

### 已解决的历史问题

| 问题                               | 根因                                                           | 修复                            |
| ---------------------------------- | -------------------------------------------------------------- | ------------------------------- |
| Type A 只处理 33 条                | decisions key 是 typea_data.id，不是 conflict_records 数组下标 | 改用 id_to_record 映射          |
| 重复 PUA 分配（15 个）             | 第二段自动处理遍历了已被第一段处理的 record                    | 加 keep_uc 防重复判断           |
| Type B PUA 各自独立编码            | merge_variants_to_entry 未传 pua 参数                          | 传入 pua=new_pua 合并为单 entry |
| demo 全部显示 PUA 标签             | isPua 判断 >= E000，原始图标也在 E600+                         | 改为 E000-E5FF 才打标签         |
| phase7_resolution 丢失 87 个 glyph | resolve_type_c_auto 跳过单来源 entry                           | 去掉 `len(sources) <= 1` 过滤   |

---

> **Handoff 时间**: 2026-05-15
> **完成状态**: Phase 1–11 全部完成
> **下一个 Phase**: 项目替换（Phase 12/14）
