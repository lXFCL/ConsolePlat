# ConsolePlat v1.7.0

## 自动上架

- 自动上架运行设置新增“申报价格”，默认值从固定的 `13` 调整为 `14`。
- 申报价格支持自定义大于 `0` 且最多两位小数的金额，并持久化到 PutawayAiRobot 运行设置。
- 批次启动时冻结本次价格，确认框会显示有效商品数量和本批次申报价格。
- 旧配置缺失或价格非法时回退为 `14`。

## 界面与帮助

- 增加各主要页面的内置帮助引导和教程截图。
- 调整教程内容展示，避免详情文字被截断。

## 发布包安全

- 便携包不包含 PutawayAiRobot 的商品图片、Excel 批次数据、账号设置、浏览器登录态、日志或历史输出。
- PutawayAiRobot 的 `data/pic/1` 与 `data/pic/2` 在便携包中保留为空目录，业务素材由用户在本机配置。

## 使用说明

1. 下载并解压 `ConsolePlat-v1.7.0-portable.zip`。
2. 运行 `scripts/setup_portable_env.ps1` 安装依赖和 Playwright Chromium。
3. 运行 `启动ConsolePlat.bat`。
4. 在自动上架运行设置中确认申报价格；新安装默认显示 `14`。
