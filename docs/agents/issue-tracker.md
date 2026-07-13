# Issue Tracker：GitHub

本仓库的 Issue 和 PRD 存放在 GitHub Issues 中。所有操作使用 `gh` CLI。

## 约定

- 创建 Issue：`gh issue create --title "..." --body "..."`
- 读取 Issue：`gh issue view <number> --comments`
- 列出 Issue：使用 `gh issue list`，并根据任务增加 `--label` 和 `--state`
- 评论：`gh issue comment <number> --body "..."`
- 添加或删除标签：`gh issue edit <number> --add-label "..."` 或 `--remove-label "..."`
- 关闭 Issue：`gh issue close <number> --comment "..."`

在仓库克隆目录中运行命令，由 `gh` 根据 `git remote -v` 自动确定仓库。

## Pull Request 是否作为分类入口

**PRs as a request surface: no.**

当前不把外部 Pull Request 作为需求或 Issue 的分类入口。如需启用，可将此值改为 `yes`。

启用后：

- 读取 PR：`gh pr view <number> --comments`，并使用 `gh pr diff <number>` 查看差异
- 列出待分类的外部 PR：使用 `gh pr list`，只保留作者关系为 `CONTRIBUTOR`、`FIRST_TIME_CONTRIBUTOR` 或 `NONE` 的 PR
- 评论、添加标签和关闭：使用对应的 `gh pr comment`、`gh pr edit` 和 `gh pr close`

GitHub 的 Issue 和 PR 共用编号空间。遇到 `#42` 之类的编号时，先运行
`gh pr view 42`，失败后再运行 `gh issue view 42`。

## 技能要求“发布到 Issue Tracker”时

创建一个 GitHub Issue。

## 技能要求“获取相关 Ticket”时

运行 `gh issue view <number> --comments`。

## Wayfinder 操作

`wayfinder` 使用一个 Map Issue 管理多个子 Issue：

- Map：带有 `wayfinder:map` 标签的单个 Issue，正文保存 Notes、Decisions-so-far 和 Fog。
- Child ticket：优先使用 GitHub Sub-issues 关联；不可用时，在 Map 正文使用任务列表，并在子 Issue 顶部写入 `Part of #<map>`。
- Ticket 类型标签：`wayfinder:research`、`wayfinder:prototype`、`wayfinder:grilling` 或 `wayfinder:task`。
- Blocking：优先使用 GitHub 原生 Issue Dependencies；不可用时，在子 Issue 顶部写入 `Blocked by: #<n>, #<n>`。
- Frontier query：按 Map 顺序查找没有未关闭阻塞项、也没有负责人认领的第一个开放子 Issue。
- Claim：`gh issue edit <n> --add-assignee @me`。
- Resolve：先评论答案，再关闭 Issue，最后把上下文链接写入 Map 的 Decisions-so-far。
