# ConsolePlat v1.7.1

## Windows EXE

- 新增可直接双击启动的 `ConsolePlat.exe`，无需手动安装 Python 或进入 Conda 环境。
- Python、PyQt5、Playwright、图片处理和 Excel 运行依赖已随程序打包。
- 修复冻结运行时后台 CLI 和外部项目脚本的启动方式，避免子进程递归打开主窗口。
- 冻结版本以 EXE 所在目录作为项目根目录，便于使用相邻的模块、资源和运行目录。

## 发布包精简

- 不包含测试目录、浏览器登录 Profile、账号配置、Cookie 数据、日志、历史输出或 Putaway 业务数据。
- 不包含 ComfyUI、AI 模型、印花图库以及未使用的大型 Python 依赖。
- ComfyUI、模型和印花资源仍按原有设置连接，避免主程序压缩包膨胀到数 GB。

## 使用说明

1. 下载 `ConsolePlat-v1.7.1-windows-x64.zip`。
2. 将压缩包完整解压到本地目录。
3. 双击 `ConsolePlat\ConsolePlat.exe`。
4. 不要单独移动 EXE；相邻的 `_internal`、`modules`、`resources` 和 `runtime` 目录需要保持完整。
