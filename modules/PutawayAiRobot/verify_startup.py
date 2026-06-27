import importlib
import sys


REQUIRED_MODULES = [
    "PyQt5",
    "openpyxl",
    "numpy",
    "PIL",
    "playwright",
]


def check_modules():
    missing = []
    for name in REQUIRED_MODULES:
        try:
            importlib.import_module(name)
        except Exception:
            missing.append(name)
    return missing


def main():
    missing = check_modules()
    if missing:
        print("依赖检查失败：缺少模块 -> " + ", ".join(missing))
        return 1
    print("依赖检查通过")
    print("Python版本: " + sys.version.replace("\n", " "))
    print("启动验证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
