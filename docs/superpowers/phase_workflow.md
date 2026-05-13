# Phase 标准工作流程

> 本文档定义 iconfont-engine 项目的标准 Phase 开发流程。
> 每个新 Phase 开始时应严格遵循此流程，确保一致性、可追溯性和高质量交付。

---

## 总览

每个 Phase 按以下步骤执行，不可跳过：

```
1. Brainstorming（需求分析 + 设计规格）
2. Writing Plans（TDD 实现计划）
3. TDD 实现（子代理驱动，逐任务 commit）
4. 验证 + Commit
5. 更新记忆和文档
6. Handoff 文档
```

---

## 步骤 1: Brainstorming — 需求分析

**触发方式：** `/brainstorming`

**目标：** 理解需求、确认设计方案、生成结构化规格文档

**流程：**
1. 探索项目上下文（读取 registry/输出文件、最近的 commit、现有代码）
2. 提出澄清问题（每次一个问题，优先选择题）
3. 提出 2-3 种方案 + 推荐
4. 分节展示设计，每节获得用户批准
5. 编写设计规格文档 → `docs/superpowers/specs/YYYY-MM-DD-<phase-name>-design.md`
6. 规格自检（占位符扫描、内部一致性、范围检查、模糊性检查）
7. 用户审查书面规格，获得批准

**产出：**
- `docs/superpowers/specs/YYYY-MM-DD-<phase-name>-design.md`

**关键约定：**
- 在展示设计并获得批准前，**不得编写任何代码**
- 规格文档必须 commit 到 git

---

## 步骤 2: Writing Plans — 实现计划

**触发方式：** `/writing-plans`

**目标：** 将规格文档转化为可执行的小步骤 TDD 实现计划

**流程：**
1. 读取规格文档
2. 读取已有代码模式（参考前一个 Phase 的脚本和测试风格）
3. 列出将要创建/修改的文件 + 每个文件职责
4. 将实现拆分为小步骤任务（每步 2-5 分钟操作）
5. 每个任务包含：失败的测试 → 运行验证失败 → 最少实现 → 运行验证通过 → commit
6. 编写完整计划 → `docs/superpowers/plans/YYYY-MM-DD-<phase-name>.md`
7. 规格覆盖度自检

**产出：**
- `docs/superpowers/plans/YYYY-MM-DD-<phase-name>.md`

**计划格式要求：**
- 头部包含：目标、架构、技术栈
- 每个任务包含：文件列表、TDD 步骤（带代码块）、commit 命令
- 禁止占位符：不得有 "TODO"、"待定"、"后续实现"、"类似任务 N"

---

## 步骤 3: TDD 实现 — 子代理驱动

**触发方式：** 选择子代理驱动执行计划

**目标：** 按实现计划逐任务执行，严格 TDD

**每个任务的流程：**
1. 调度新子代理（general-purpose agent）
2. 子代理编写失败的测试
3. 子代理运行测试验证失败
4. 子代理编写最少实现代码
5. 子代理运行测试验证通过
6. 主会话验收测试结果
7. `git add` + `git commit`（每个任务一个 commit）

**关键约定：**
- 每个任务一个 commit，不可合并
- 测试必须先于实现编写
- 每次 commit 前必须运行测试验证全部通过

---

## 步骤 4: 验证 + 最终 Commit

**检查清单：**
- [ ] 所有单元测试通过
- [ ] 主脚本在真实数据上正常运行
- [ ] 输出文件存在且格式正确
- [ ] `git status` 无遗漏文件
- [ ] 执行最终 commit

---

## 步骤 5: 更新记忆和文档

**必须更新的文件：**

| 文件 | 更新内容 |
|------|---------|
| `CLAUDE.md` | Phase 进度表：状态、脚本数、关键数据 |
| `plan.md` | Phase 进度表：状态行 + 脚本统计 |
| `memory/MEMORY.md` | 添加新的 Phase 完成状态索引 |
| `memory/phaseN_completion.md` | 创建 Phase 完成状态记录 |
| `memory/pipeline_architecture.md` | 更新 Phase 状态 |

**Phase 完成状态记录模板：**

```markdown
---
name: Phase N 完成状态
description: Phase N [简述]，[关键数据]
type: project
---
## Phase N 完成结果

日期：YYYY-MM-DD
关键数据：[数字]

## 脚本清单

| 脚本 | 状态 | 说明 |
|------|------|------|
| `pipeline/NN_*.py` | 🟢 已完成 | [说明] |
| `pipeline/test_NN_*.py` | 🟢 已完成 | [N] 个单元测试 |

## 输出文件

| 文件 | 说明 |
|------|------|
| `output/file.ext` | [说明] |

## 验证方式

1. `python pipeline/NN_*.py` 正常运行
2. `python pipeline/test_NN_*.py` [N] 个测试通过
```

---

## 步骤 6: Handoff 文档

**目标：** 编写 Phase 核心技术文档，供下一个 Phase 参考

**文件位置：** `docs/superpowers/phaseN_handoff.md`

**必须包含的章节：**

1. **输入/输出** — 读取什么文件、产出什么文件、大小和格式
2. **数据结构** — 输出 JSON 的完整格式定义
3. **核心算法** — 关键算法的步骤和保证条件
4. **统计事实** — 关键数字、分布、Top N 列表
5. **对接点** — 下一个 Phase 读取什么、处理什么、需要额外哪些文件
6. **运行方式** — 重跑命令、测试命令、验证命令
7. **测试覆盖** — 测试函数列表和覆盖范围

---

## 快速参考

### 文件位置约定

| 类型 | 路径模式 |
|------|---------|
| 主脚本 | `pipeline/NN_*.py` |
| 测试脚本 | `pipeline/test_NN_*.py` |
| 设计规格 | `docs/superpowers/specs/YYYY-MM-DD-<phase-name>-design.md` |
| 实现计划 | `docs/superpowers/plans/YYYY-MM-DD-<phase-name>.md` |
| Handoff 文档 | `docs/superpowers/phaseN_handoff.md` |
| 输出报告 | `report/phaseN_*.md` |
| 结构化输出 | `report/*.json` |
| 记忆文件 | `memory/phaseN_completion.md` |

### 状态标记

| 标记 | 含义 |
|------|------|
| ⬜ | 未开始 |
| 🟡 | 进行中 |
| 🟢 | 已完成 |
| 🔧 | 脚本已收集待迁移 |

### Commit 格式

| 类型 | 格式 |
|------|------|
| 新功能 | `feat(phaseN): [描述]` |
| 测试 | `test(phaseN): [描述]` |
| 修复 | `fix(phaseN): [描述]` |
| 文档 | `docs: [描述]` |

---

## 禁止事项

- ❌ 跳过 Brainstorming 直接写代码
- ❌ 跳过 Writing Plans 直接执行
- ❌ 先写实现后写测试（必须 TDD）
- ❌ 多个任务合并为一个 commit
- ❌ 更新代码但不更新文档
- ❌ 不写 Handoff 文档就进入下一个 Phase
