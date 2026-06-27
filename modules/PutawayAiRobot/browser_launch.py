import os


def _iter_browser_executable_candidates():
    env_path = (os.environ.get("PUTAWAY_BROWSER_PATH") or "").strip()
    if env_path:
        yield env_path
    local_app_data = (os.environ.get("LOCALAPPDATA") or "").strip()
    program_files = (os.environ.get("ProgramFiles") or r"C:\Program Files").strip()
    program_files_x86 = (os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)").strip()
    common = [
        os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(local_app_data, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for p in common:
        if p:
            yield p
    try:
        import winreg

        reg_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"),
        ]
        for root, sub in reg_keys:
            try:
                with winreg.OpenKey(root, sub) as k:
                    v, _ = winreg.QueryValueEx(k, None)
                    vv = (v or "").strip()
                    if vv:
                        yield vv
            except Exception:
                continue
    except Exception:
        pass


def detect_available_browsers():
    found = []
    seen = set()
    for p in _iter_browser_executable_candidates():
        key = (p or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        if os.path.isfile(p):
            base = os.path.basename(p).lower()
            if base == "msedge.exe":
                found.append({"value": "msedge", "label": f"Microsoft Edge（检测到）", "path": p})
            elif base == "chrome.exe":
                found.append({"value": "chrome", "label": f"Google Chrome（检测到）", "path": p})
    values = {x["value"] for x in found}
    out = [{"value": "auto", "label": "自动选择（推荐）", "path": ""}]
    if "msedge" in values:
        out.append({"value": "msedge", "label": "Microsoft Edge（检测到）", "path": ""})
    if "chrome" in values:
        out.append({"value": "chrome", "label": "Google Chrome（检测到）", "path": ""})
    return out


def launch_persistent_context_with_fallback(chromium, user_data_dir: str, args: list, browser_preference: str = "auto"):
    pref = (browser_preference or "auto").strip().lower()
    tried = []
    launch_attempts = []
    if pref in {"msedge", "chrome"}:
        launch_attempts.append((f"channel:{pref}", {"channel": pref}))
        launch_attempts.append(("bundled", {}))
        other = "chrome" if pref == "msedge" else "msedge"
        launch_attempts.append((f"channel:{other}", {"channel": other}))
    else:
        launch_attempts = [
            ("bundled", {}),
            ("channel:msedge", {"channel": "msedge"}),
            ("channel:chrome", {"channel": "chrome"}),
        ]
    for exe_path in _iter_browser_executable_candidates():
        if os.path.isfile(exe_path):
            launch_attempts.append((f"path:{exe_path}", {"executable_path": exe_path}))

    last_error = None
    for name, extra in launch_attempts:
        tried.append(name)
        try:
            return chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=args,
                **extra,
            )
        except Exception as e:
            last_error = e
            msg = str(e)
            if "Executable doesn't exist" in msg or "playwright install" in msg:
                continue
            raise
    raise RuntimeError(
        "浏览器启动失败：未找到可用浏览器。已尝试 "
        + " -> ".join(tried)
        + "。可设置环境变量 PUTAWAY_BROWSER_PATH 指向 chrome.exe 或 msedge.exe。原始错误："
        + str(last_error)
    )
