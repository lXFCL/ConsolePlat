const button = document.getElementById("copySkcButton");
const statusText = document.getElementById("statusText");

function setStatus(text) {
  statusText.textContent = text;
}

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function sendRunMessage(tabId) {
  try {
    return await chrome.tabs.sendMessage(tabId, { type: "APPLY_GOODS_COPY_SKC_IDS" });
  } catch (_error) {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["content.js"]
    });
    return chrome.tabs.sendMessage(tabId, { type: "APPLY_GOODS_COPY_SKC_IDS" });
  }
}

button.addEventListener("click", async () => {
  button.disabled = true;
  setStatus("正在执行：每页 50 条、全选、复制 SKC ID...");

  try {
    const tab = await getActiveTab();
    if (!tab?.id || !/^https:\/\/agentseller\.temu\.com\/goods\/list/.test(tab.url || "")) {
      setStatus("当前页不是 Temu 商品列表页。\n请先打开 https://agentseller.temu.com/goods/list");
      return;
    }

    const result = await sendRunMessage(tab.id);
    if (!result?.ok) {
      setStatus(result?.message || "执行失败，页面结构可能和预期不一致。");
      return;
    }

    setStatus(result.message);
  } catch (error) {
    setStatus(`执行失败：${error?.message || error}`);
  } finally {
    button.disabled = false;
  }
});

chrome.storage.local.get("lastCopySkcResult", ({ lastCopySkcResult }) => {
  if (lastCopySkcResult?.message) {
    setStatus(lastCopySkcResult.message);
  }
});
