(function () {
  function norm(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function collect() {
    const text = norm(document.body ? document.body.innerText : "");
    const tabCounts = {};
    for (const match of text.matchAll(/(全部|待创建|待发货|已送货|已收货|已入库|已作废|已取消|已超时)\s*\(?(\d+)\)?/g)) {
      tabCounts[match[1]] = Number(match[2]);
    }
    const isLoginLike = /登录|密码|手机号|授权登录|确认授权并前往/.test(text)
      && !/紧急备货建议|备货单号|备货件数/.test(text);
    window.__CONSOLEPLAT_MONITOR__ = {
      url: location.href,
      title: document.title,
      isLoginLike,
      tabCounts,
      textSample: text.slice(0, 2000),
      updatedAt: new Date().toISOString()
    };
  }

  collect();
  setInterval(collect, 2000);
})();
