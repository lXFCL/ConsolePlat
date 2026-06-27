(() => {
  if (window.__applyGoodsContentLoaded) {
    return;
  }
  window.__applyGoodsContentLoaded = true;

  const ACTION = "APPLY_GOODS_COPY_SKC_IDS";
  const FLOAT_ID = "apply-goods-status";

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const normalize = (text) => String(text || "").replace(/\s+/g, " ").trim();

  function isVisible(element) {
    if (!element || !(element instanceof Element)) return false;
    const style = window.getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) {
      return false;
    }
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function textOf(element) {
    return normalize(element?.innerText || element?.textContent || "");
  }

  function dispatchClick(element) {
    if (!element) {
      throw new Error("没有找到可点击元素");
    }
    element.scrollIntoView({ block: "center", inline: "center" });
    const rect = element.getBoundingClientRect();
    const clientX = rect.left + rect.width / 2;
    const clientY = rect.top + rect.height / 2;
    for (const type of ["pointerover", "mouseover", "pointermove", "mousemove", "pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
      element.dispatchEvent(new MouseEvent(type, {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX,
        clientY
      }));
    }
  }

  function dispatchHover(element) {
    if (!element) return;
    element.scrollIntoView({ block: "center", inline: "center" });
    const rect = element.getBoundingClientRect();
    const clientX = rect.left + rect.width / 2;
    const clientY = rect.top + rect.height / 2;
    for (const type of ["pointerover", "mouseover", "pointermove", "mousemove"]) {
      element.dispatchEvent(new MouseEvent(type, {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX,
        clientY
      }));
    }
  }

  async function waitFor(predicate, timeout = 8000, interval = 150) {
    const started = Date.now();
    let lastError;
    while (Date.now() - started < timeout) {
      try {
        const result = predicate();
        if (result) return result;
      } catch (error) {
        lastError = error;
      }
      await sleep(interval);
    }
    if (lastError) throw lastError;
    return null;
  }

  function showStatus(message, tone = "info") {
    let box = document.getElementById(FLOAT_ID);
    if (!box) {
      box = document.createElement("div");
      box.id = FLOAT_ID;
      box.style.cssText = [
        "position:fixed",
        "top:76px",
        "right:24px",
        "z-index:2147483647",
        "max-width:360px",
        "padding:12px 14px",
        "border-radius:6px",
        "box-shadow:0 10px 28px rgba(15,23,42,.18)",
        "font:13px/1.5 Microsoft YaHei,Segoe UI,Arial,sans-serif",
        "white-space:pre-wrap"
      ].join(";");
      document.documentElement.appendChild(box);
    }
    const palette = tone === "error"
      ? ["#fff1f2", "#be123c", "#fecdd3"]
      : tone === "success"
        ? ["#ecfdf5", "#047857", "#bbf7d0"]
        : ["#eff6ff", "#1d4ed8", "#bfdbfe"];
    box.style.background = palette[0];
    box.style.color = palette[1];
    box.style.border = `1px solid ${palette[2]}`;
    box.textContent = message;
  }

  function getClickableAncestor(element) {
    return element?.closest?.("button,[role='button'],[role='combobox'],[role='menuitem'],li,.semi-button,.semi-select,.semi-dropdown-item,.ant-btn,.ant-select,.ant-dropdown-menu-item") || element;
  }

  function visibleElements(selector) {
    return Array.from(document.querySelectorAll(selector)).filter(isVisible);
  }

  function findByText(selector, matcher) {
    return visibleElements(selector).find((element) => matcher(textOf(element), element));
  }

  function findButtonByText(label) {
    const exact = (text) => text === label || text.replace(/[∨⌄⌃^]/g, "").trim() === label;
    return findByText("button,[role='button'],a,span,div", (text, element) => {
      if (!text.includes(label)) return false;
      const clickable = getClickableAncestor(element);
      return isVisible(clickable) && exact(textOf(clickable));
    });
  }

  function findGoodsTable() {
    const tables = visibleElements("table");
    return tables.find((table) => {
      const text = textOf(table);
      return text.includes("商品信息") && (text.includes("SKC ID") || text.includes("SKU ID"));
    }) || tables.find((table) => textOf(table).includes("商品信息"));
  }

  function currentPageSizeIs50() {
    return Boolean(findByText("div,span,button,[role='combobox']", (text) => /每页\s*50\s*条/.test(text)));
  }

  function findPageSizeControl() {
    const pageSizeText = findByText("div,span,button,[role='combobox']", (text) => /每页\s*\d+\s*条/.test(text));
    if (!pageSizeText) return null;
    return pageSizeText.closest("[role='combobox'],.semi-select,.ant-select,button") || getClickableAncestor(pageSizeText);
  }

  function menuLikeElements() {
    return visibleElements("[role='listbox'],[role='menu'],.semi-select-option,.semi-dropdown,.semi-portal,.ant-select-dropdown,.ant-dropdown,li,div,span")
      .filter((element) => {
        if (element.closest("[role='listbox'],[role='menu'],.semi-dropdown,.semi-portal,.ant-select-dropdown,.ant-dropdown")) {
          return true;
        }
        let node = element;
        for (let depth = 0; node && depth < 6; depth += 1, node = node.parentElement) {
          const style = window.getComputedStyle(node);
          const zIndex = Number.parseInt(style.zIndex, 10);
          if ((style.position === "fixed" || style.position === "absolute") && (!Number.isNaN(zIndex) || depth > 0)) {
            return true;
          }
        }
        return false;
      });
  }

  async function setPageSize50() {
    if (currentPageSizeIs50()) {
      return "每页已经是 50 条";
    }

    const control = findPageSizeControl();
    if (!control) {
      throw new Error("没有找到分页的“每页 xx 条”控件");
    }
    dispatchClick(control);

    const option = await waitFor(() => {
      const candidates = menuLikeElements();
      return candidates.find((element) => /^(50|50\s*条|每页\s*50\s*条)$/.test(textOf(element)));
    }, 5000);

    if (!option) {
      throw new Error("已打开分页控件，但没有找到 50 条选项");
    }
    dispatchClick(getClickableAncestor(option));

    await waitFor(() => currentPageSizeIs50(), 10000);
    await sleep(800);
    return "已切换为每页 50 条";
  }

  function checkboxIsChecked(element) {
    const input = element.matches("input[type='checkbox']") ? element : element.querySelector("input[type='checkbox']");
    if (input) return input.checked;
    const checked = element.getAttribute("aria-checked") || element.closest("[aria-checked]")?.getAttribute("aria-checked");
    return checked === "true" || checked === "mixed";
  }

  async function selectAllGoods() {
    const table = await waitFor(findGoodsTable, 10000);
    if (!table) {
      throw new Error("没有找到商品列表表格");
    }

    const header = table.tHead || table.querySelector("thead") || table.querySelector("tr");
    const selectors = [
      "input[type='checkbox']",
      "[role='checkbox']",
      ".semi-checkbox",
      ".ant-checkbox",
      "label"
    ];
    let checkbox = null;
    for (const selector of selectors) {
      checkbox = Array.from((header || table).querySelectorAll(selector)).find(isVisible);
      if (checkbox) break;
    }

    if (!checkbox) {
      checkbox = visibleElements("input[type='checkbox'],[role='checkbox'],.semi-checkbox,.ant-checkbox")
        .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0];
    }
    if (!checkbox) {
      throw new Error("没有找到表头全选框");
    }

    if (!checkboxIsChecked(checkbox)) {
      dispatchClick(getClickableAncestor(checkbox));
      await sleep(700);
    }
    return "已全选当前页商品";
  }

  function findFloatingItem(label, exact = true) {
    const candidates = menuLikeElements()
      .filter((element) => {
        const text = textOf(element);
        return exact ? text === label : text.includes(label);
      })
      .sort((a, b) => {
        const areaA = a.getBoundingClientRect().width * a.getBoundingClientRect().height;
        const areaB = b.getBoundingClientRect().width * b.getBoundingClientRect().height;
        return areaA - areaB;
      });
    return candidates[0] || null;
  }

  async function copySkcIdFromMoreMenu() {
    const moreButton = findButtonByText("更多");
    if (!moreButton) {
      throw new Error("没有找到“更多”按钮");
    }
    dispatchClick(getClickableAncestor(moreButton));

    const copyIdItem = await waitFor(() => findFloatingItem("批量复制ID", false), 5000);
    if (!copyIdItem) {
      throw new Error("没有找到“批量复制ID”菜单项");
    }
    dispatchHover(getClickableAncestor(copyIdItem));
    await sleep(250);
    if (!findFloatingItem("SKC ID", true)) {
      dispatchClick(getClickableAncestor(copyIdItem));
      await sleep(250);
    }

    const skcItem = await waitFor(() => findFloatingItem("SKC ID", true), 5000);
    if (!skcItem) {
      throw new Error("没有找到“SKC ID”子菜单项");
    }
    dispatchClick(getClickableAncestor(skcItem));

    await sleep(900);
    return "已点击 更多 > 批量复制ID > SKC ID";
  }

  async function readClipboardText() {
    try {
      if (!navigator.clipboard?.readText) return "";
      return await navigator.clipboard.readText();
    } catch (_error) {
      return "";
    }
  }

  function summarizeClipboard(text) {
    const ids = normalize(text).split(/[\s,，;；]+/).filter((item) => /^\d{5,}$/.test(item));
    if (!ids.length) return "";
    return `剪贴板检测到 ${ids.length} 个数字 ID。`;
  }

  async function runCopySkcIds() {
    showStatus("正在执行：切换每页 50 条...");
    const step1 = await setPageSize50();

    showStatus(`${step1}\n正在全选当前页商品...`);
    const step2 = await selectAllGoods();

    showStatus(`${step1}\n${step2}\n正在复制 SKC ID...`);
    const step3 = await copySkcIdFromMoreMenu();

    const clipboardText = await readClipboardText();
    const clipboardSummary = summarizeClipboard(clipboardText);
    const message = [
      step1,
      step2,
      step3,
      clipboardSummary || "复制动作已完成；浏览器未允许插件读回剪贴板内容。"
    ].join("\n");

    showStatus(message, "success");
    await chrome.storage.local.set({
      lastCopySkcResult: {
        ok: true,
        message,
        copiedAt: new Date().toISOString()
      }
    });
    return { ok: true, message };
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== ACTION) return undefined;

    runCopySkcIds()
      .then(sendResponse)
      .catch(async (error) => {
        const result = {
          ok: false,
          message: `执行失败：${error?.message || error}`
        };
        showStatus(result.message, "error");
        await chrome.storage.local.set({
          lastCopySkcResult: {
            ...result,
            copiedAt: new Date().toISOString()
          }
        });
        sendResponse(result);
      });

    return true;
  });
})();
