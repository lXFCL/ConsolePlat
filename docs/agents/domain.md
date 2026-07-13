# Domain Docs

本文说明工程技能在探索代码库时应如何读取本仓库的领域文档。

## 探索前读取

- 读取仓库根目录的 `CONTEXT.md`。
- 如果根目录存在 `CONTEXT-MAP.md`，按其指引读取与当前任务有关的 `CONTEXT.md`。
- 读取 `docs/adr/` 中与当前工作区域有关的 ADR。
- 多上下文仓库还应检查 `src/<context>/docs/adr/` 中的上下文级 ADR。

如果这些文件不存在，直接继续，不报告缺失，也不预先建议创建。
`domain-modeling` 技能会在术语或架构决策真正明确后按需创建它们。

## 文件结构

本仓库采用 single-context 布局：

    /
    ├── CONTEXT.md
    ├── docs/adr/
    │   ├── 0001-example-decision.md
    │   └── 0002-another-decision.md
    └── consoleplat/

当前配置不会立即创建 `CONTEXT.md` 或空的 `docs/adr/`。这些文件将在有实际领域知识或架构决策需要记录时创建。

## 使用领域词汇

Issue 标题、重构建议、假设和测试名称中涉及领域概念时，应使用 `CONTEXT.md` 词汇表定义的术语，不随意改用同义词。

如果需要的概念尚未进入词汇表，应先判断：

- 是否使用了项目并不采用的语言；
- 是否确实存在需要由 `domain-modeling` 补充的领域知识空缺。

## 标记 ADR 冲突

当输出内容与现有 ADR 冲突时，必须明确指出，不得静默覆盖。例如：

> 与 ADR-0007 冲突，但由于现有约束发生变化，建议重新评估该决策。
