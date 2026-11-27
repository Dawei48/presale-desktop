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

  function normalize(r) {
    // 后端约定：一律返回 {ok:true, data} 或 {ok:false, error}
    if (r && typeof r === 'object' && 'ok' in r) return r;
    return { ok: true, data: r };
  }

  /* 超时只认「先到的那个」，之后一律忽略。
     ⚠ 不能写成 Promise.race([api[method](...), timeout])——pywebview 的
     api 返回的是它自己的 thenable 而不是标准 Promise，塞进 race 后经常
     永远不 settle：界面就一直挂在上一次的结果上。 */
  function invoke(method, args, ms) {
    return new Promise(resolve => {
      let settled = false;
      const timer = setTimeout(
        () => { if (!settled) { settled = true; resolve({ ok: false, error: '后端响应超时，请重试' }); } },
        ms);
      const done = v => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(v);
      };
      try {
        const ret = global.pywebview.api[method](...args);
        if (ret && typeof ret.then === 'function') {
          ret.then(v => done(normalize(v)))
             .catch(e => done({ ok: false, error: (e && e.message) || String(e) }));
        } else {
          done(normalize(ret));   // 同步返回值
        }
      } catch (e) {
        done({ ok: false, error: (e && e.message) || String(e) });
      }
    });
  }

  async function call(method, ...args) {
    if (!bridgeReady()) {
      if (global.MOCK && typeof global.MOCK[method] === 'function') {
        return global.MOCK[method](...args);
      }
      return { ok: false, error: '未连接后端（浏览器预览模式）' };
    }
    return invoke(method, args, TIMEOUT);
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
    products:       ()              => call('products'),
    imports:        ()              => call('imports'),
    getSettings:    ()              => call('get_settings'),
    saveSettings:   (s)             => call('save_settings', s),
    setTheme:       (name)          => call('set_theme', name),
    openPath:       (p)             => call('open_path', p),
    saveFile:       (name, b64)     => call('save_file', name, b64),
  };

  global.API = API;
})(window);
