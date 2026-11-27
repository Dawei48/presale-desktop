/* ═══════════════════════════════════════════════════════════════════
   api.js — 前端与 Python 后端的唯一通道
   ─────────────────────────────────────────────────────────────────
   · pywebview 里走 window.pywebview.api.*（返回 Promise）
   · 浏览器里直接打开 index.html 时走 MOCK，方便纯前端调试样式
   · 任何异常都转成 {ok:false, error}，绝不让 UI 卡在 loading
   ═══════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  const TIMEOUT = 15000;

  function bridgeReady() {
    return !!(global.pywebview && global.pywebview.api);
  }

  function withTimeout(promise, ms) {
    return Promise.race([
      promise,
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('后端响应超时，请重试')), ms)
      ),
    ]);
  }

  async function call(method, ...args) {
    if (!bridgeReady()) {
      if (global.MOCK && typeof global.MOCK[method] === 'function') {
        return global.MOCK[method](...args);
      }
      return { ok: false, error: '未连接后端（浏览器预览模式）' };
    }
    try {
      const r = await withTimeout(global.pywebview.api[method](...args), TIMEOUT);
      // 后端约定：一律返回 {ok:true, data} 或 {ok:false, error}
      if (r && typeof r === 'object' && 'ok' in r) return r;
      return { ok: true, data: r };
    } catch (e) {
      return { ok: false, error: (e && e.message) || String(e) };
    }
  }

  const API = {
    ready: bridgeReady,
    summary:        ()              => call('summary'),
    orders:         (filter, kw)    => call('orders', filter || 'all', kw || ''),
    orderDetail:    (id)            => call('order_detail', id),
    setStatus:      (id, status)    => call('set_status', id, status),
    setOrderType:   (id, type)      => call('set_order_type', id, type),
    saveOrder:      (data)          => call('save_order', data),
    deleteOrder:    (id)            => call('delete_order', id),
    saveProduct:    (data)          => call('save_product', data),
    deleteProduct:  (id)            => call('delete_product', id),
    pickImage:      ()              => call('pick_image'),
    exportProduction: (opts)        => call('export_production', opts || {}),
    importCsv:      ()              => call('import_csv'),
    kilns:          ()              => call('kilns'),
    fetchImages:    (name)          => call('fetch_images', name),
    applyImage:     (pid, url, nm)  => call('apply_image', pid, url, nm || ''),
    applyLocalImage: (pid, path)    => call('apply_local_image', pid, path),
    products:       (kw)            => call('products', kw || ''),
    imports:        ()              => call('imports'),
    getSettings:    ()              => call('get_settings'),
    saveSettings:   (s)             => call('save_settings', s),
    setTheme:       (name)          => call('set_theme', name),
    openPath:       (p)             => call('open_path', p),
    saveFile:       (name, b64)     => call('save_file', name, b64),
  };

  global.API = API;
})(window);
