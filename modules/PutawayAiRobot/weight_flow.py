import time

from config_store import DEFAULT_WEIGHTS, normalize_weights


def _fill_one_input(inp, value: str):
    try:
        inp.scroll_into_view_if_needed(timeout=900)
    except Exception:
        pass
    try:
        inp.click(timeout=900)
    except Exception:
        pass
    inp.fill(value, timeout=1500)


def _validate_weights(weights):
    try:
        values = list(weights)
    except (TypeError, ValueError) as e:
        raise ValueError("重量必须是五个正整数") from e
    if len(values) != len(DEFAULT_WEIGHTS) or any(type(weight) is not int or weight <= 0 for weight in values):
        raise ValueError("重量必须是五个正整数")
    return normalize_weights(values)


def fill_weights(page, weights=DEFAULT_WEIGHTS, progress=None):
    weights = _validate_weights(weights)
    count = len(weights)

    if progress:
        progress("填写重量…")

    inputs = page.locator('input[name="weight"]:visible')
    total = 0
    try:
        total = int(inputs.count())
    except Exception:
        total = 0

    if total < count:
        for _ in range(8):
            try:
                page.wait_for_timeout(120)
            except Exception:
                time.sleep(0.12)
            try:
                total = int(inputs.count())
            except Exception:
                total = 0
            if total >= count:
                break

    if total < count:
        raise RuntimeError(f"可见重量输入框不足：需要{count}个，实际{total}个")

    for i in range(count):
        value = str(weights[i])
        inp = inputs.nth(i)
        _fill_one_input(inp, value)


def fill_weight_sequence(page, start_weight: int = 142, step: int = 5, count: int = 5, progress=None):
    start_weight = int(start_weight)
    step = int(step)
    count = int(count)
    if count != len(DEFAULT_WEIGHTS):
        raise ValueError("重量必须是五个正整数")
    return fill_weights(page, [start_weight + index * step for index in range(count)], progress=progress)
