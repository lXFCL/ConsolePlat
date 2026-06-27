# ConsolePlat v1.6.0

## 便携发布包

- 新增 `ConsolePlat-v1.6.0-portable.zip`，默认从解压目录内加载 `modules/`、`resources/` 和 `runtime/`。
- 新增 `ConsolePlat-prints-v1.6.0.zip`，完整图集作为独立资产包发布，主包只保留 `resources/prints` 占位说明。
- 主包不包含账号、浏览器登录态、历史输出、日志、缓存、ComfyUI、模型文件或本机生成目录。

## PosAiImg 资源

- `设置 -> 生图 / 改图` 新增 PosAiImg 资源区，可配置 ComfyUI 目录、模型目录和下载目录。
- 内置资源下载器支持 zip 下载、进度显示、解压安装、空间不足提示和失败提示。
- 默认下载 URL 允许为空；未配置时界面会提示“下载地址待配置”，不会崩溃。

## 使用说明

1. 下载并解压 `ConsolePlat-v1.6.0-portable.zip`。
2. 运行 `scripts/setup_portable_env.ps1` 安装 Python 依赖和 Playwright Chromium。
3. 运行 `启动ConsolePlat.bat`。
4. 如需本地图集，下载 `ConsolePlat-prints-v1.6.0.zip` 并解压到 `resources/prints`。
5. 如需本地生图，在设置页配置或下载 PosAiImg 的 ComfyUI 和模型资源。
