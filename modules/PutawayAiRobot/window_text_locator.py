import ctypes
import os
import re
import sys
import time
from ctypes import wintypes

from PyQt5 import QtCore, QtWidgets

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

_PADDLE_OCR = None


def _set_dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32


EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class RGBQUAD(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", wintypes.BYTE),
        ("rgbGreen", wintypes.BYTE),
        ("rgbRed", wintypes.BYTE),
        ("rgbReserved", wintypes.BYTE),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", RGBQUAD * 1),
    ]


def _get_window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _get_window_rect(hwnd: int):
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def _get_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def _get_process_exe(pid: int) -> str:
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return ""
        return buf.value
    finally:
        kernel32.CloseHandle(handle)


def list_top_level_windows(only_browsers: bool):
    results = []

    def _cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        title = _get_window_text(hwnd)
        if not title.strip():
            return True
        pid = _get_pid(hwnd)
        exe = _get_process_exe(pid)
        exe_base = os.path.basename(exe).lower() if exe else ""
        is_browser = exe_base in {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}
        if only_browsers and not is_browser:
            return True
        results.append(
            {
                "hwnd": int(hwnd),
                "title": title,
                "pid": pid,
                "exe": exe,
                "exe_base": exe_base,
                "is_browser": is_browser,
            }
        )
        return True

    user32.EnumWindows(EnumWindowsProc(_cb), 0)
    results.sort(key=lambda x: (0 if x["is_browser"] else 1, x["title"].lower()))
    return results


def _capture_window_bgra(hwnd: int):
    rect = _get_window_rect(hwnd)
    if not rect:
        raise RuntimeError("无法获取窗口尺寸")
    left, top, right, bottom = rect
    width = max(1, right - left)
    height = max(1, bottom - top)

    hdc_window = user32.GetWindowDC(hwnd)
    if not hdc_window:
        raise RuntimeError("无法获取窗口DC")
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    if not hdc_mem:
        user32.ReleaseDC(hwnd, hdc_window)
        raise RuntimeError("无法创建内存DC")

    hbmp = gdi32.CreateCompatibleBitmap(hdc_window, width, height)
    if not hbmp:
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hwnd, hdc_window)
        raise RuntimeError("无法创建位图")

    old = gdi32.SelectObject(hdc_mem, hbmp)
    try:
        PW_RENDERFULLCONTENT = 0x00000002
        ok = user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)
        if not ok:
            SRCCOPY = 0x00CC0020
            gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_window, 0, 0, SRCCOPY)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        buf_size = width * height * 4
        buf = (ctypes.c_ubyte * buf_size)()
        bits = gdi32.GetDIBits(
            hdc_mem,
            hbmp,
            0,
            height,
            ctypes.cast(buf, ctypes.c_void_p),
            ctypes.byref(bmi),
            0,
        )
        if bits == 0:
            raise RuntimeError("无法读取位图数据")
        return left, top, width, height, bytes(buf)
    finally:
        gdi32.SelectObject(hdc_mem, old)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hwnd, hdc_window)


def _bgra_to_numpy(bgra: bytes, width: int, height: int):
    try:
        import numpy as np
    except Exception as e:
        raise RuntimeError("缺少numpy，无法进行OCR输入转换") from e
    arr = np.frombuffer(bgra, dtype=np.uint8).reshape((height, width, 4))
    return arr


def _get_paddle_ocr():
    global _PADDLE_OCR
    if _PADDLE_OCR is not None:
        return _PADDLE_OCR
    from paddleocr import PaddleOCR

    def _try_create(kwargs):
        try:
            return PaddleOCR(**kwargs)
        except Exception as e:
            msg = str(e)
            if "Unknown argument" in msg and "show_log" in msg:
                kwargs = dict(kwargs)
                kwargs.pop("show_log", None)
                return PaddleOCR(**kwargs)
            raise

    try:
        _PADDLE_OCR = _try_create({"use_textline_orientation": False, "lang": "ch", "show_log": False})
    except TypeError:
        try:
            _PADDLE_OCR = _try_create({"use_angle_cls": False, "lang": "ch", "show_log": False})
        except TypeError:
            _PADDLE_OCR = _try_create({"use_angle_cls": False, "lang": "ch"})
    return _PADDLE_OCR


def _ocr_candidates(image_bgra):
    try:
        ocr = _get_paddle_ocr()
        rgb = image_bgra[:, :, :3][:, :, ::-1]
        result = ocr.ocr(rgb, cls=False)
        candidates = []
        for line in result or []:
            for item in line or []:
                box, (text, score) = item
                if not text:
                    continue
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                x1, y1, x2, y2 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
                candidates.append((text, (x1, y1, x2, y2), float(score)))
        return candidates
    except ModuleNotFoundError:
        pass

    try:
        import pytesseract
        from PIL import Image
    except Exception as e:
        raise RuntimeError(
            "缺少OCR依赖：优先安装 paddleocr；或安装 pytesseract 并在系统中安装 Tesseract(含 chi_sim)。"
        ) from e

    rgba = image_bgra[:, :, [2, 1, 0, 3]]
    img = Image.fromarray(rgba, mode="RGBA").convert("RGB")
    data = pytesseract.image_to_data(img, lang="chi_sim", output_type=pytesseract.Output.DICT)
    n = len(data.get("text", []))
    candidates = []
    for i in range(n):
        text = (data["text"][i] or "").strip()
        if not text:
            continue
        score = float(data.get("conf", [0] * n)[i])
        x, y, w, h = int(data["left"][i]), int(data["top"][i]), int(data["width"][i]), int(data["height"][i])
        candidates.append((text, (x, y, x + w, y + h), score))
    return candidates


def _normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", s)
    return s


def _is_ordered_subsequence(needle: str, haystack: str) -> bool:
    if not needle:
        return False
    i = 0
    for ch in haystack:
        if ch == needle[i]:
            i += 1
            if i >= len(needle):
                return True
    return False


def _ocr_find_text_bbox(image_bgra, target_text: str):
    target_text = (target_text or "").strip()
    if not target_text:
        raise RuntimeError("目标文字为空")

    candidates = _ocr_candidates(image_bgra)
    target_norm = _normalize_text(target_text)
    if not target_norm:
        raise RuntimeError("目标文字为空")

    def _rank(c):
        text, _, score = c
        text_norm = _normalize_text(text)
        exact = 1 if text_norm == target_norm else 0
        contains = 1 if target_norm and (target_norm in text_norm) else 0
        ordered = 1 if _is_ordered_subsequence(target_norm, text_norm) else 0
        return (exact, contains, ordered, -len(text_norm), score)

    best = None
    for c in candidates:
        if best is None or _rank(c) > _rank(best):
            best = c
    if not best:
        raise RuntimeError("OCR未找到目标文字")
    best_norm = _normalize_text(best[0])
    if not _is_ordered_subsequence(target_norm, best_norm):
        raise RuntimeError("OCR未找到目标文字")
    return best[1], best[0], best[2]


def _ocr_find_temu_menu_bbox(image_bgra):
    candidates = _ocr_candidates(image_bgra)
    filtered = []
    target_norm = _normalize_text("创建temu产品")
    for text, bbox, score in candidates:
        norm = _normalize_text(text)
        if "temu" not in norm:
            continue
        if "半托管" in norm or "本土" in norm:
            continue
        if not _is_ordered_subsequence(target_norm, norm):
            continue
        filtered.append((text, bbox, score))
    if not filtered:
        raise RuntimeError("OCR未找到“创建[Temu]产品”菜单项")
    filtered.sort(key=lambda x: (x[1][1], -x[2], (x[1][0] + x[1][2]) / 2))
    text, bbox, score = filtered[0]
    return bbox, text, score


def _move_mouse_to_screen(x: int, y: int):
    user32.SetCursorPos(int(x), int(y))


def _click_left():
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def _click_screen(x: int, y: int):
    _move_mouse_to_screen(x, y)
    _click_left()


def _bring_to_front(hwnd: int):
    SW_RESTORE = 9
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("窗口OCR点击")
        self.resize(720, 240)

        self.only_browsers = QtWidgets.QCheckBox("仅显示浏览器窗口")
        self.only_browsers.setChecked(True)
        self.refresh_btn = QtWidgets.QPushButton("刷新窗口列表")
        self.window_combo = QtWidgets.QComboBox()
        self.window_combo.setMinimumWidth(560)
        self.locate_btn = QtWidgets.QPushButton("点击“产品”→悬停“创建产品”→点“创建[Temu]产品”")
        self.locate_btn.setEnabled(False)
        self.status = QtWidgets.QLabel("")
        self.status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        top = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(top)
        row1 = QtWidgets.QHBoxLayout()
        row1.addWidget(self.only_browsers)
        row1.addWidget(self.refresh_btn)
        row1.addStretch(1)
        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(QtWidgets.QLabel("目标窗口："))
        row2.addWidget(self.window_combo, 1)
        row3 = QtWidgets.QHBoxLayout()
        row3.addWidget(self.locate_btn)
        row3.addStretch(1)
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row3)
        layout.addWidget(self.status)
        self.setCentralWidget(top)

        self._windows = []
        self.refresh_btn.clicked.connect(self.refresh_windows)
        self.only_browsers.toggled.connect(self.refresh_windows)
        self.window_combo.currentIndexChanged.connect(self._on_window_changed)
        self.locate_btn.clicked.connect(self.click_product_create)

        QtCore.QTimer.singleShot(0, self.refresh_windows)

    def refresh_windows(self):
        only = self.only_browsers.isChecked()
        self._windows = list_top_level_windows(only_browsers=only)
        self.window_combo.blockSignals(True)
        self.window_combo.clear()
        for w in self._windows:
            exe = w["exe_base"] or "unknown.exe"
            self.window_combo.addItem(f'{w["title"]}  ({exe})', w["hwnd"])
        self.window_combo.blockSignals(False)
        self._on_window_changed()

    def _on_window_changed(self):
        hwnd = self.window_combo.currentData()
        enabled = bool(hwnd)
        self.locate_btn.setEnabled(enabled)
        if enabled:
            self.status.setText(f"已选择窗口 HWND={int(hwnd)}")
        else:
            self.status.setText("未选择窗口")

    def _locate_text_in_window(self, hwnd: int, target_text: str):
        left, top, width, height, bgra = _capture_window_bgra(int(hwnd))
        img = _bgra_to_numpy(bgra, width, height)
        bbox, hit_text, score = _ocr_find_text_bbox(img, target_text)
        x1, y1, x2, y2 = bbox
        cx = left + int((x1 + x2) / 2)
        cy = top + int((y1 + y2) / 2)
        return hit_text, score, cx, cy, left, top, width, height

    def _click_text_in_window(self, hwnd: int, target_text: str):
        hit_text, score, cx, cy, _, _, _, _ = self._locate_text_in_window(hwnd, target_text)
        _click_screen(cx, cy)
        return hit_text, score, cx, cy

    def click_product_create(self):
        hwnd = self.window_combo.currentData()
        if not hwnd:
            return

        try:
            self.locate_btn.setEnabled(False)
            _bring_to_front(int(hwnd))
            self.status.setText("正在点击：产品")
            QtWidgets.QApplication.processEvents()
            hit1, score1, x1, y1 = self._click_text_in_window(int(hwnd), "产品")
            self.status.setText(f"已点击：{hit1}  score={score1:.3f}  坐标=({x1},{y1})，定位“创建产品”")
            QtWidgets.QApplication.processEvents()
            time.sleep(0.6)

            hit2, score2, x2, y2, left, top, width, height = self._locate_text_in_window(int(hwnd), "创建产品")
            _move_mouse_to_screen(x2, y2)
            self.status.setText(f"已悬停：{hit2}  score={score2:.3f}  坐标=({x2},{y2})，等待菜单出现")
            QtWidgets.QApplication.processEvents()
            time.sleep(0.6)

            last_err = None
            for _ in range(25):
                QtWidgets.QApplication.processEvents()
                try:
                    l2, t2, w2, h2, bgra2 = _capture_window_bgra(int(hwnd))
                    img2 = _bgra_to_numpy(bgra2, w2, h2)
                    rel_x = max(0, min(w2 - 1, int(x2 - l2)))
                    rel_y = max(0, min(h2 - 1, int(y2 - t2)))
                    roi_x1 = max(0, rel_x - 220)
                    roi_y1 = max(0, rel_y - 40)
                    roi_x2 = w2
                    roi_y2 = min(h2, rel_y + 520)
                    cropped = img2[roi_y1:roi_y2, roi_x1:roi_x2]
                    bbox3, hit3, score3 = _ocr_find_temu_menu_bbox(cropped)
                    x1r, y1r, x2r, y2r = bbox3
                    cx3 = l2 + roi_x1 + int((x1r + x2r) / 2)
                    cy3 = t2 + roi_y1 + int((y1r + y2r) / 2)
                    _click_screen(cx3, cy3)
                    self.status.setText(f"已点击：{hit3}  score={score3:.3f}  坐标=({cx3},{cy3})")
                    break
                except Exception as e:
                    last_err = e
                    time.sleep(0.35)
            else:
                raise RuntimeError(f"未找到“创建[Temu]产品”：{last_err}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "失败", str(e))
        finally:
            self.locate_btn.setEnabled(bool(self.window_combo.currentData()))


def main():
    _set_dpi_aware()
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
