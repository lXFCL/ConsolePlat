from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from urllib.request import urlopen


Logger = Callable[[str], None]


class BrowserSession:
    def __init__(
        self,
        user_data_dir: str | Path,
        cdp_endpoint: str = "http://127.0.0.1:9222",
        logger: Logger | None = None,
    ) -> None:
        self.user_data_dir = Path(user_data_dir)
        self.cdp_endpoint = cdp_endpoint
        self.logger = logger or (lambda _message: None)
        self._playwright = None
        self.browser = None
        self.context = None
        self._launched_process: subprocess.Popen | None = None
        self._owns_browser = False

    def log(self, message: str) -> None:
        self.logger(message)

    def start(self) -> None:
        if self._playwright is not None:
            return
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()

    def connect_or_launch(self) -> None:
        self.start()
        if self.context is not None:
            return

        try:
            self.log(f"尝试连接 Chrome 调试端口：{self.cdp_endpoint}")
            self._connect_to_cdp(owns_browser=False)
            self.log("已连接到现有 Chrome。")
            return
        except Exception as exc:  # noqa: BLE001 - fallback is intended.
            self.log(f"未连接到调试端口，准备启动带调试端口的 Chrome：{exc}")

        try:
            self._launch_debug_chrome()
            self._wait_for_cdp_endpoint()
            self._connect_to_cdp(owns_browser=True)
            self.log(f"已启动并连接 Chrome 调试端口：{self.cdp_endpoint}")
        except Exception as exc:  # noqa: BLE001 - make the recovery path explicit.
            raise RuntimeError(
                "无法启动可调试 Chrome。请关闭旧版软件打开的 Chrome 窗口后重试；"
                "如果仍失败，请检查 Chrome 调试地址是否为 http://127.0.0.1:9222。"
            ) from exc

    def _connect_to_cdp(self, owns_browser: bool) -> None:
        self.browser = self._playwright.chromium.connect_over_cdp(self.cdp_endpoint)
        self.context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
        self._owns_browser = owns_browser

    def _launch_debug_chrome(self) -> None:
        host, port = self._debug_host_port()
        chrome_path = self._find_chrome_executable()
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        debug_host = "127.0.0.1" if host.lower() == "localhost" else host
        command = [
            str(chrome_path),
            f"--remote-debugging-address={debug_host}",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={self.user_data_dir}",
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ]
        self.log(f"正在启动 Chrome 调试端口：{debug_host}:{port}")
        self._launched_process = subprocess.Popen(  # noqa: S603 - controlled executable path and args.
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )

    def _wait_for_cdp_endpoint(self, timeout: float = 15.0) -> None:
        version_url = self.cdp_endpoint.rstrip("/") + "/json/version"
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            if self._launched_process is not None and self._launched_process.poll() is not None:
                raise RuntimeError("Chrome 进程已退出，可能是旧浏览器仍占用同一个登录目录。")
            try:
                with urlopen(version_url, timeout=0.5) as response:  # noqa: S310 - localhost DevTools endpoint.
                    if response.status == 200:
                        return
            except Exception as exc:  # noqa: BLE001 - retry until Chrome opens the port.
                last_error = exc
            time.sleep(0.25)
        raise RuntimeError(f"等待 Chrome 调试端口超时：{self.cdp_endpoint}；最后错误：{last_error}")

    def _debug_host_port(self) -> tuple[str, int]:
        parsed = urlparse(self.cdp_endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise RuntimeError("Chrome 调试地址格式不正确，应类似：http://127.0.0.1:9222")
        return parsed.hostname, parsed.port or 9222

    def _find_chrome_executable(self) -> Path:
        candidates = [
            shutil.which("chrome"),
            shutil.which("chrome.exe"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
        ]
        try:
            candidates.append(self._playwright.chromium.executable_path)
        except Exception:  # noqa: BLE001 - bundled Chromium is only a fallback candidate.
            pass

        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if path.exists():
                return path
        raise RuntimeError("未找到 Chrome 或 Playwright Chromium 可执行文件。")

    def page_for(self, url_contains: str):
        self.connect_or_launch()
        pages = list(self.context.pages)
        for page in pages:
            if url_contains in page.url:
                return page
        usable_pages = [page for page in pages if not page.url.startswith("chrome-error://")]
        return usable_pages[-1] if usable_pages else self.context.new_page()

    def close(self) -> None:
        try:
            if self.browser is not None:
                self.browser.close()
            elif self.context is not None and self.browser is None:
                self.context.close()
        finally:
            if self._launched_process is not None and self._launched_process.poll() is None:
                self._launched_process.terminate()
                try:
                    self._launched_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._launched_process.kill()
            self._launched_process = None
            self.context = None
            self.browser = None
            self._owns_browser = False
            if self._playwright is not None:
                self._playwright.stop()
                self._playwright = None

    def close_remote_browser(self) -> None:
        self.start()
        try:
            if self.browser is None:
                self._connect_to_cdp(owns_browser=True)
            self.close()
        except Exception:
            self.close()
            raise

    def detach(self) -> None:
        self.context = None
        self.browser = None
        self._owns_browser = False
        self._launched_process = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
