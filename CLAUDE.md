# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**iconfont-engine** 是一个 **Agent-Orchestrated Font Engineering System**（Agent 编排的字体工程系统），不是简单的"字体合并工具"。

它从 60+ 前端项目中扫描 iconfont CSS/TTF，提取字形、构建 glyph 哈希注册表、解决冲突、合并字体，最终输出统一的 iconfont 包。

**系统本质**：Glyph 级别的资产数据库 + 可审计渲染管线

## Agent 角色

Agent **不做**：font parsing、glyph transform、file IO heavy ops、直接处理字体

Agent **只做 4 件事**：
1. 决策执行顺序（pipeline orchestration）
2. 生成/修改脚本（Node/Python）
3. 处理异常（conflict decision）
4. 校验结果（validation interpretation）

详细分工见 `plan.md` 第二节。

## Architecture

12 阶段 Pipeline（Phase 0–11），详见 `plan.md`：

| Phase | Name | 语言 | 脚本 | 说明 |
|-------|------|------|------|------|
| 0 | Task Planning | LLM | — | 生成 JSON pipeline plan |
| 1 | Repo Discovery | Node.js | `01_scan_repos_*.js` | 克隆仓库、扫描 HTML 提取 iconfont 链接 |
| 2 | Asset Resolver | Node.js | `02_resolve_download_assets.js` + 2 | CSS 下载(gzip)、@font-face 解析(TTF URL)、name→unicode 映射提取、TTF 下载 |
| Phase 3 | Glyph Extraction | Python | `03_extract_glyphs.py` | fontTools 解析 TTF、提取 contours | 🟢 已完成 |
| 4 | Geometry Normalization | Python | `04_normalize_glyphs.py` | UPM=1024、contour 标准化、glyphHash |
| 5 | Glyph Hash Registry | Python | `05_build_registry.py` | 核心数据库、多源合并、alias |
| 6 | Conflict Detection | Python/Node.js | `06_detect_conflicts_*.js` | unicode/name/glyph 冲突检测 |
| 7 | Conflict Resolution | Python/Node.js | `07_resolve_conflicts_*.js` | PUA 分配、rename、alias merge |
| 8 | Direct Glyf Merge | Python | `08_merge_glyf.py` | 核心合并：glyph deep copy、cmap rebuild |
| 9 | Font Build | Python | `09_build_font.py` | TTF/WOFF2 生成 |
| 10 | Validation | Node.js | `10_validate_render.js` | Playwright + pixelmatch 跨浏览器验证 |
| 11 | Output & Manifest | Node.js | `11_generate_manifest_*.js` | iconfont.css/json、manifest、demo |

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `pipeline/` | 所有流水线脚本（编号命名） |
| `sources/phase1_raw_links/` | Phase 1 原始数据：CSS 链接清单 |
| `sources/phase2_assets/` | Phase 2 下载资产：`<assetId>/iconfont.css` + `font.ttf` |
| `sources/phase3_glyphs/` | Phase 3 glyph 数据：`raw_glyphs.json` + `extraction_summary.json` |
| `sources/meta/` | 跨 Phase 元数据：assets_manifest.json、css_mappings.json、assets_validation.json |
| `registry/` | glyph 哈希数据库和中间数据（Phase 3-5） |
| `output/` | 最终生成的字体文件和 manifest（Phase 9-11） |
| `report/` | 各阶段验证/冲突报告（Phase 3 起） |
| `snapshots/` | 每阶段快照，用于回滚 |

## Tech Stack

- **Node.js**：Phases 1, 2, 6, 7, 10, 11 — 仓库克隆、CSS 解析、冲突检测、渲染验证
- **Python + fontTools**：Phases 3–9 — TTF 解析、glyph 提取、几何标准化、字体构建
- **Playwright + pixelmatch**：Phase 10 — 跨浏览器渲染对比

## Key Concepts

- **UPM (Units Per em)**：标准化为 1024
- **PUA (Private Use Area)**：Unicode 范围 E000–F8FF，用于冲突解决
- **Glyph Hash**：SHA-256 基于 canonical contours，是 glyph 的唯一身份标识
- **Source Tracking**：每个 glyph 记录来源项目和 URL
- **Deterministic Build**：同输入 = 同输出（glyph sort、table order fixed、timestamp removed）

## Three Absolute Principles（绝对原则）

1. **不重建 glyph**：禁止 SVG roundtrip、禁止 Bézier 重建，只能 copy glyph object（glyf level）
2. **geometry 是唯一真相**：优先级 contours > unicode > name
3. **所有冲突必须显式化**：不能自动覆盖，必须标记、分级、可回滚、可追溯

## Phase 进度状态

> ⬜ 未开始 | 🟡 进行中 | 🟢 已完成 | 🔧 脚本已收集待迁移

| Phase | 状态 |
|-------|------|
| Phase 0 | ⬜ 未开始 |
| Phase 1 | 🟢 已完成 |
| Phase 2 | 🟢 已完成（3个脚本：110/111 CSS + 110 TTF + 11494 图标映射） |
| Phase 3 | 🟢 已完成（2个脚本：110 TTF + 11528 glyph 记录提取，0 错误） |
| Phase 4 | ⬜ 待编写（fontTools） |
| Phase 5 | ⬜ 待编写（fontTools） |
| Phase 6 | 🔧 脚本已收集（2个） |
| Phase 7 | 🔧 脚本已收集（4个） |
| Phase 8 | ⬜ 待编写（fontTools） |
| Phase 9 | ⬜ 待编写（fontTools） |
| Phase 10 | ⬜ 待编写（Playwright） |
| Phase 11 | 🔧 脚本已收集（1个） |

**统计**：Phase 1 已完成（3个脚本）/ Phase 2 已完成（3个脚本）/ Phase 3 已完成（2个脚本）/ 已收集 6 个 / 待编写 4 个 / 共 17 个。详见 `script.md`。

## Phase 1 完成结果

2026-05-13 完成 Phase 1 仓库扫描，产出 **111 个唯一 iconfont CSS 链接**。

### 扫描范围
- **57 个仓库**（`D:\work\codestore\` 下全部项目）
- **20 个手动链接**（从外部系统补充）
- **27 个项目**有 iconfont 链接，30 个无

### 输出文件
- `sources/all_iconfont_links.json` — 完整数据（版本 2.0.0）
- `sources/iconfont_urls.txt` — 111 行纯链接列表
- `sources/<项目名>_iconfont_links.json` — 57 个单独项目文件

### Phase 1 脚本能力
- 全程脚本覆盖扫描：html/vue/css/scss/js/ts/env/config，不依赖 index.html
- webpack 模板变量自动替换（读取 vue.config.js / config/index.js）
- CDN 域名统一：res.wyins.net → res.winbaoxian.com
- CDN 去重：同文件名只留最短 URL
- 注释过滤：JS/TS/HTML/Vue 中的注释链接自动排除
- 完整文件读取：不截断，避免遗漏后半部分的链接

> **扫描语义**：全程脚本覆盖扫描的是**"文本里存在的完整链接"**，而不是**"运行时最终生效的链接"**。
> 模板变量替换（如 `<%= htmlWebpackPlugin.options.path %>` → 实际路径）是在提取阶段做文本替换，后续 Phase 7 替换项目中 iconfont 链接时，需要**还原回模板变量形式**，以保持项目构建一致性。

## Development Workflow

脚本按 Phase 顺序依次执行。Agent 负责编排和决策，具体重操作由脚本完成。

```bash
# 示例：顺序执行
node pipeline/01_scan_repos_*.js
node pipeline/02_resolve_iconfont_links_*.js
python pipeline/03_extract_glyphs.py
# ... 依次到 Phase 11
```

## Related Projects

Source repositories 托管在 Codeup（`codeup.aliyun.com/wy-front`）。详见父工作区 `D:\work\CLAUDE.md`。

前端项目已爬取完毕，存放在 `D:\work\codestore` 下。

## Key Files

| File | Purpose |
|------|---------|
| `plan.md` | 完整系统设计文档：架构图、Agent 角色、核心算法、Phase 进度 |
| `script.md` | 全部脚本清单：来源、目标路径、依赖、状态 |
| `CLAUDE.md` | 项目快速参考（本文档） |

<!-- superpowers-zh:begin (do not edit between these markers) -->
# Superpowers-ZH 中文增强版

本项目已安装 superpowers-zh 技能框架（20 个 skills）。

## 核心规则

1. **收到任务时，先检查是否有匹配的 skill** — 哪怕只有 1% 的可能性也要检查
2. **设计先于编码** — 收到功能需求时，先用 brainstorming skill 做需求分析
3. **测试先于实现** — 写代码前先写测试（TDD）
4. **验证先于完成** — 声称完成前必须运行验证命令

## 可用 Skills

Skills 位于 `.claude/skills/` 目录，每个 skill 有独立的 `SKILL.md` 文件。

- **brainstorming**: 在任何创造性工作之前必须使用此技能——创建功能、构建组件、添加功能或修改行为。在实现之前先探索用户意图、需求和设计。
- **chinese-code-review**: 中文 review 沟通参考——话术模板、分级标注（必须修复/建议修改/仅供参考）、国内团队常见反模式应对。仅在用户显式 /chinese-code-review 时调用，不要根据上下文自动触发。
- **chinese-commit-conventions**: 中文 commit 与 changelog 配置参考——Conventional Commits 中文适配、commitlint/husky/commitizen 中文模板、conventional-changelog 中文配置。仅在用户显式 /chinese-commit-conventions 时调用，不要根据上下文自动触发。
- **chinese-documentation**: 中文文档排版参考——中英文空格、全半角标点、术语保留、链接格式、中文文案排版指北约定。仅在用户显式 /chinese-documentation 时调用，不要根据上下文自动触发。
- **chinese-git-workflow**: 国内 Git 平台配置参考——Gitee、Coding.net、极狐 GitLab、CNB 的 SSH/HTTPS/凭据/CI 接入差异与镜像同步配置。仅在用户显式 /chinese-git-workflow 时调用，不要根据上下文自动触发。
- **dispatching-parallel-agents**: 当面对 2 个以上可以独立进行、无共享状态或顺序依赖的任务时使用
- **executing-plans**: 当你有一份书面实现计划需要在单独的会话中执行，并设有审查检查点时使用
- **finishing-a-development-branch**: 当实现完成、所有测试通过、需要决定如何集成工作时使用——通过提供合并、PR 或清理等结构化选项来引导开发工作的收尾
- **mcp-builder**: MCP 服务器构建方法论 — 系统化构建生产级 MCP 工具，让 AI 助手连接外部能力
- **receiving-code-review**: 收到代码审查反馈后、实施建议之前使用，尤其当反馈不明确或技术上有疑问时——需要技术严谨性和验证，而非敷衍附和或盲目执行
- **requesting-code-review**: 完成任务、实现重要功能或合并前使用，用于验证工作成果是否符合要求
- **subagent-driven-development**: 当在当前会话中执行包含独立任务的实现计划时使用
- **systematic-debugging**: 遇到任何 bug、测试失败或异常行为时使用，在提出修复方案之前执行
- **test-driven-development**: 在实现任何功能或修复 bug 时使用，在编写实现代码之前
- **using-git-worktrees**: 当需要开始与当前工作区隔离的功能开发或执行实现计划之前使用——创建具有智能目录选择和安全验证的隔离 git 工作树
- **using-superpowers**: 在开始任何对话时使用——确立如何查找和使用技能，要求在任何响应（包括澄清性问题）之前调用 Skill 工具
- **verification-before-completion**: 在宣称工作完成、已修复或测试通过之前使用，在提交或创建 PR 之前——必须运行验证命令并确认输出后才能声称成功；始终用证据支撑断言
- **workflow-runner**: 在 Claude Code / OpenClaw / Cursor 中直接运行 agency-orchestrator YAML 工作流——无需 API key，使用当前会话的 LLM 作为执行引擎。当用户提供 .yaml 工作流文件或要求多角色协作完成任务时触发。
- **writing-plans**: 当你有规格说明或需求用于多步骤任务时使用，在动手写代码之前
- **writing-skills**: 当创建新技能、编辑现有技能或在部署前验证技能是否有效时使用

## 如何使用

当任务匹配某个 skill 时，使用 `Skill` 工具加载对应 skill 并严格遵循其流程。绝不要用 Read 工具读取 SKILL.md 文件。

如果你认为哪怕只有 1% 的可能性某个 skill 适用于你正在做的事情，你必须调用该 skill 检查。
<!-- superpowers-zh:end -->
