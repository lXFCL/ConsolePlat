# ApplyGoods

Temu Agent Seller 商品申请自动化项目。

当前主线已经从 Chrome 扩展验证迁移到 Python Playwright。`chrome-extension/` 仍保留，用于快速验证页面交互和选择器。

## 当前已实现

当前流程：

1. 打开或连接到 `https://agentseller.temu.com/goods/list`。
2. 将商品列表切换为每页 50 条。
3. 全选当前页商品。
4. 通过 `更多 > 批量复制ID > SKC ID` 执行 Temu 原生批量复制。
5. 软件只显示已获取到的 SKC ID 数量，不展示明细。
6. 进入 `https://agentseller.temu.com/sample/clothing-set`。
7. 点击套版组管理里的“添加”。
8. 将批量复制出来的 SKC ID 填入“添加同面料套版 SKC”，点击“搜索”，再点击“提交”。
9. 在 PyQt 桌面界面显示运行日志。

## 运行环境

优先使用 conda 的 `flask` 环境：

```powershell
conda run -n flask python main.py
```

如果缺少依赖：

```powershell
conda run -n flask python -m pip install -r requirements.txt
conda run -n flask python -m playwright install chromium
```

## 浏览器登录态

程序优先连接：

```text
http://127.0.0.1:9222
```

如果没有可连接的 Chrome 调试端口，会启动一个独立浏览器，并使用项目内的 `.browser-profile/` 保存登录态。

## 使用方式

1. 运行程序。
2. 点击“打开/连接浏览器”。
3. 如果页面要求登录，先在打开的浏览器里完成 Temu 登录。
4. 回到程序，点击“套版组管理”。
5. 需要连续上传合规信息时，点击“批量上传合规信息”。
6. 只需要执行某一个合规上传时，点击“单项合规上传”，再在弹窗中选择具体项目。
7. 检查日志中的执行数量、失败步骤和提交结果。

## 说明

- 当前版本只处理商品列表当前页，也就是切换到每页 50 条后的当前页商品。
- 当前 Playwright 版本以 Temu 原生批量复制结果为准，界面只显示获取数量。
- 页面自动化任务在后台线程执行，运行时主窗口应保持可拖动、可重绘。
- 后续申请商品流程会按用户指令逐步补齐。
