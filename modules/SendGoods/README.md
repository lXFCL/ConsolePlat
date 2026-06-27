# SendGoods

PyQt 桌面工具，用于从 Temu Agent Seller 备货页面读取 SKU、颜色、尺码、备货件数和高清商品图，并按 `1.cleaned.xlsx` 模板生成拿货表。

## 运行环境

优先使用用户指定的 conda 环境。如果本机没有 `PutawayAIRobot`，当前已验证 `flask` 环境具备本项目所需依赖：

```powershell
conda run -n flask python main.py
```

注意：`flask` 在这里只是 conda 环境名，本项目不是 Flask Web 项目。

## 使用方式

1. 运行软件。
2. 点击“打开/连接浏览器”。
3. 在打开的浏览器中登录 Temu，并进入：
   `https://agentseller.temu.com/stock/fully-mgt/order-manage-urgency`
4. 回到软件点击“采集当前页”。
5. 检查采集结果后点击“生成 Excel”。

如果你已经用远程调试方式启动了 Chrome，软件会优先连接 `http://127.0.0.1:9222`。

## 快速测试 Excel 写入

```powershell
conda run -n flask python tools_test_excel.py
```

该命令会用两条示例数据生成一个 Excel，适合先验证模板写入和图片插入流程。

## 打包 exe

```powershell
.\build_exe.ps1
```

打包结果：

- `dist/SendGoods.exe`

打包策略：

- 使用 `flask` conda 环境中的 Python 和依赖。
- 生成单个 exe，内置 Python 运行时、PyQt5、Playwright Python 依赖和 `1.cleaned.xlsx` 模板。
- 程序优先连接本机 Chrome 调试端口；如果目标电脑没有 Chrome 或 Playwright 浏览器组件，需要额外验证浏览器可用性。
- 不打包 `outputs/`、`downloads/`、`.browser-profile/`、`__pycache__/` 等运行时数据。

## 输出规则

- 黑色写入模板左侧区域。
- 白色写入模板右侧区域。
- SKU 货号如 `SZW-2138-M` 会解析为货号 `SZW-2138` 和尺码 `M`。
- 同货号、同颜色、同尺码会累加件数。
- 图片使用高清原图地址，不使用 `thumbnail/180x` 缩略图。
