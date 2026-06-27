import datetime
import os
import re


def _log_dir():
    base = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(base, "log")
    os.makedirs(p, exist_ok=True)
    return p


def _safe_name(name: str):
    name = (name or "").strip()
    if not name:
        return "task"
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", "_", name)
    return name[:80] or "task"


def start_publish_log(task_name: str):
    now = datetime.datetime.now()
    day_dir = os.path.join(_log_dir(), now.strftime("%Y%m%d"))
    os.makedirs(day_dir, exist_ok=True)
    safe_task = _safe_name(task_name)
    file_path = os.path.join(day_dir, f"{now.strftime('%H%M%S')}_{safe_task}.log")
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"任务开始：{now.strftime('%Y-%m-%d %H:%M:%S')} | 任务名={task_name}\n")
    return {"file_path": file_path, "task_name": task_name, "started_at": now}


def write_publish_log(session, index: int, total: int, row: dict, ok: bool, reason: str = ""):
    now = datetime.datetime.now()
    file_path = (session or {}).get("file_path") or os.path.join(_log_dir(), "publish_fallback.log")
    status = "成功" if bool(ok) else "失败"
    reason_text = (reason or "").strip() if not ok else ""
    line = (
        f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] "
        f"[{int(index)}/{int(total)}] "
        f"[{status}] "
        f"店铺={((row.get('shop_name') or '').strip())} | "
        f"分类={((row.get('category') or '').strip())} | "
        f"标题={((row.get('title') or '').strip())} | "
        f"SKU={((row.get('sku') or '').strip())} | "
        f"颜色={((row.get('color') or '').strip())}"
    )
    if reason_text:
        line += f" | 原因={reason_text}"
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return file_path


def finish_publish_log(session, success_count: int, failed_count: int, done: int, total: int, elapsed_sec: float, stopped: bool = False, reason: str = ""):
    now = datetime.datetime.now()
    file_path = (session or {}).get("file_path") or os.path.join(_log_dir(), "publish_fallback.log")
    mm = int(max(0.0, float(elapsed_sec)) // 60)
    ss = int(max(0.0, float(elapsed_sec)) % 60)
    state = "暂停结束" if stopped else "正常结束"
    tail = (
        f"任务结束：{now.strftime('%Y-%m-%d %H:%M:%S')} | 状态={state} | "
        f"成功={int(success_count)} | 失败={int(failed_count)} | 完成={int(done)}/{int(total)} | 用时={mm:02d}:{ss:02d}"
    )
    if reason:
        tail += f" | 原因={reason}"
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(tail + "\n")
    return file_path
