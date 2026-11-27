/* ═══════════════════════════════════════════════════════════════════
   app.js — 界面逻辑
   ─────────────────────────────────────────────────────────────────
   约定：
   · 所有用户数据用 textContent 写入，绝不拼 innerHTML（防注入）
   · 每个数据区域都有 loading / empty / error / full 四态
   · 状态写入 URL hash，刷新/返回能回到原处
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  const $  = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.prototype.slice.call((r || document).querySelectorAll(s));

  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };

  /* ── 状态 ──────────────────────────────────────────────────── */
  const S = {
    page: 'todo',
    filter: 'all',
    keyword: '',
    rows: [],
    groups: [],
    sel: -1,          // 键盘选中行
    loading: false,
    error: null,
    theme: 'dark',
    settings: {},
  };

  const PAGE_META = {
    todo:       { title: '待办',     showFilters: true },
    orders:     { title: '全部订单', showFilters: true },
    kilns:      { title: '窑口',     showFilters: false },
    products:   { title: '商品库',   showFilters: false },
    imports:    { title: '导入记录', showFilters: false },
    settings:   { title: '设置',     showFilters: false },
  };

  /* ── 主题 ──────────────────────────────────────────────────── */
  const systemDark = () =>
    !!(globalThis.matchMedia && globalThis.matchMedia('(prefers-color-scheme: dark)').matches);

  function applyTheme(mode) {
    S.theme = mode;
    const real = mode === 'system' ? (systemDark() ? 'dark' : 'light') : mode;
    document.documentElement.setAttribute('data-theme', real);
    $$('#theme-switch button').forEach(b =>
      b.classList.toggle('on', b.dataset.setTheme === mode));
    try { localStorage.setItem('fx.theme', mode); } catch (_) {}
    API.setTheme(real);   // 让 Python 侧同步标题栏颜色
  }

  function initTheme() {
    let saved = null;
    try { saved = localStorage.getItem('fx.theme'); } catch (_) {}
    applyTheme(saved || 'dark');
    // 后端的设置更可靠：WebView2 默认不清 storage 但也不保证，双保险
    API.getSettings().then(r => {
      if (r.ok && r.data && r.data.theme && r.data.theme !== S.theme) applyTheme(r.data.theme);
    });
    if (globalThis.matchMedia) {
      globalThis.matchMedia('(prefers-color-scheme: dark)')
        .addEventListener('change', () => { if (S.theme === 'system') applyTheme('system'); });
    }
  }

  /* ── Toast ─────────────────────────────────────────────────── */
  let toastTimer;
  function toast(msg, kind) {
    const box = $('#toasts');
    box.textContent = '';
    const t = el('div', 'toast' + (kind === 'warn' ? ' warn' : ''));
    t.appendChild(el('span', 'dot'));
    t.appendChild(el('span', null, msg));
    box.appendChild(t);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { box.textContent = ''; }, 2600);
  }

  /* ── 数据加载 ──────────────────────────────────────────────── */
  async function load(page) {
    page = page || S.page;
    S.loading = true;
    S.error = null;
    render();

    if (page === 'todo' || page === 'orders') {
      const r = await API.orders(S.filter, S.keyword);
      S.loading = false;
      if (!r.ok) { S.error = r.error; S.rows = []; }
      else { S.rows = r.data.rows || []; S.counts = r.data.counts || {}; S.todo = r.data.todo || 0; }
      if (page === 'todo') buildGroups();
      render();
    } else if (page === 'kilns') {
      const r = await API.kilns();
      S.loading = false;
      if (!r.ok) { S.error = r.error; S.kilns = []; }
      else S.kilns = r.data || [];
      render();
    } else if (page === 'products') {
      const r = await API.products('');
      S.loading = false;
      if (!r.ok) { S.error = r.error; S.rows = []; }
      else S.rows = r.data || [];
      render();
    } else if (page === 'imports') {
      const r = await API.imports();
      S.loading = false;
      if (!r.ok) { S.error = r.error; S.rows = []; }
      else S.rows = r.data || [];
      render();
    } else if (page === 'settings') {
      const r = await API.getSettings();
      S.loading = false;
      if (r.ok) S.settings = r.data || {};
      render();
    }
    refreshNav();
    updateSub();
  }

  function buildGroups() {
    const order = ['confirm', 'producing', 'ready', 'stored'];
    const label = {
      confirm: '待确认延发', producing: '待生产', ready: '待发货',
      stored: '预存挂账', shipped: '已发货', done: '已完成',
    };
    const hint = {
      confirm: '在平台发延后发货申请，客户同意后转生产',
      producing: '按窑口合并后可一次导出生产单',
      ready: '现货优先，48 小时内必须出库',
      stored: '消费券挂账，不发货不生产',
    };
    const map = {};
    S.rows.forEach(o => {
      const k = o.status || 'ready';
      (map[k] = map[k] || []).push(o);
    });
    S.groups = order
      .filter(k => map[k] && map[k].length)
      .map(k => ({ key: k, label: label[k], hint: hint[k] || '', rows: map[k] }));
  }

  function buildProduction() {
    // 生产单：按窑口聚合
    const map = {};
    S.rows.forEach(o => {
      const kiln = o.kiln || (o.goods_name ? String(o.goods_name).split('·')[0].trim() : '未标注窑口');
      (map[kiln] = map[kiln] || []).push(o);
    });
    S.kilns = Object.keys(map).sort().map(k => ({
      key: k, label: k, rows: map[k],
      qty: map[k].reduce((a, o) => a + (o.quantity || 1), 0),
    }));
  }

  function todoCount() {
    const c = S.counts || {};
    return (c.confirm || 0) + (c.producing || 0) + (c.ready || 0);
  }

  function refreshNav() {
    const c = S.counts || {};
    $('#nav-todo').textContent = c.total != null ? todoCount() : '–';
    $('#nav-orders').textContent = c.total != null ? c.total : '–';
    $('#nav-prod').textContent = (c.confirm || 0) + (c.producing || 0) || '–';
  }

  function updateSub() {
    const c = S.counts || {};
    if (S.page === 'todo') {
      const urgent = c.confirm || 0;
      $('#page-sub').textContent = '';
      const b1 = el('b', null, todoCount() + ' 单');
      const b2 = el('b', null, urgent + ' 单');
      $('#page-sub').append('今天 ', b1, ' 没走完，', b2, ' 在等你动手');
    } else if (S.page === 'orders') {
      $('#page-sub').textContent = '共 ' + (c.total || S.rows.length) + ' 单，按导入时间倒序';
    } else if (S.page === 'kilns') {
      const n = (S.kilns || []).length;
      $('#page-sub').textContent = n
        ? `${n} 个窑口，共 ${(S.kilns || []).reduce((a, k) => a + k.orders, 0)} 单`
        : '还没有订单，导入后会按商品名自动分出窑口';
    } else {
      $('#page-sub').textContent = '';
    }
  }

  /* ── 渲染 ──────────────────────────────────────────────────── */
  function render() {
    const meta = PAGE_META[S.page];
    $('#page-title').textContent = meta.title;
    $('#tools').style.display = meta.showFilters ? '' : 'none';
    $$('.nav').forEach(b => b.classList.toggle('on', b.dataset.page === S.page));

    const list = $('#list');
    list.textContent = '';

    if (S.loading) return renderSkeleton(list);
    if (S.error) return renderError(list, S.error);

    if (S.page === 'todo' || S.page === 'orders') {
      if (!S.rows.length) return renderEmpty(list, S.keyword
        ? '没有找到「' + S.keyword + '」相关订单'
        : '还没有订单', S.keyword ? '换个关键词试试' : '导入一份 CSV 就能开始');
      if (S.page === 'todo') renderGroups(list);
      else renderFlat(list, S.rows);
    } else if (S.page === 'kilns') {
      if (!S.kilns || !S.kilns.length) {
        return renderEmpty(list, '还没有窑口', '导入订单后，会按商品名的第一段自动分出窑口');
      }
      renderKilns(list);
    } else if (S.page === 'products') {
      if (!S.rows.length) return renderEmpty(list, '商品库还是空的', '导入订单时会自动建立商品');
      renderProducts(list);
    } else if (S.page === 'imports') {
      if (!S.rows.length) return renderEmpty(list, '还没有导入记录', '每次导入都会留档');
      renderImports(list);
    } else if (S.page === 'settings') {
      renderSettings(list);
    }
  }

  function renderSkeleton(list) {
    for (let i = 0; i < 8; i++) {
      const r = el('div', 'skel');
      r.appendChild(el('i')); r.appendChild(el('i')); r.appendChild(el('i'));
      list.appendChild(r);
    }
  }

  function renderError(list, msg) {
    const box = el('div', 'err');
    box.appendChild(el('div', 't', '读取失败'));
    box.appendChild(el('div', 'd', msg || '未知错误'));
    const b = el('button', 'btn btn-ghost', '重试');
    b.style.marginTop = '10px';
    b.addEventListener('click', () => load());
    box.appendChild(b);
    list.appendChild(box);
  }

  function renderEmpty(list, title, desc) {
    const box = el('div', 'blank');
    box.appendChild(el('div', 't', title));
    if (desc) box.appendChild(el('div', 'd', desc));
    list.appendChild(box);
  }

  const fmtMoney = n => '¥' + Number(n || 0).toLocaleString('zh-CN');

  function rowEl(o, urgent) {
    const r = el('div', 'row' + (urgent ? ' urgent' : ''));
    r.dataset.id = o.id;

    r.appendChild(el('div', 'cust', o.receiver_name || o.customer || '—'));

    const item = el('div', 'item');
    item.appendChild(el('div', 'g', o.goods_name || o.product_name || '未命名商品'));
    const m = el('div', 'm');
    if (o.spec) m.append(o.spec + '　');
    if (o.notes) m.append(o.notes + '　');
    const no = el('i', null, o.order_no || '');
    m.appendChild(no);
    item.appendChild(m);
    r.appendChild(item);

    r.appendChild(el('div', 'qty', '×' + (o.quantity || 1)));

    const st = el('div', 'state st-' + statusClass(o.status));
    st.appendChild(el('span', 'dot'));
    st.append(statusLabel(o.status));
    r.appendChild(st);

    const acts = el('div', 'acts');
    const primary = primaryAction(o);
    if (primary) {
      const b = el('button', 'act' + (urgent ? ' primary' : ''), primary.text);
      b.addEventListener('click', ev => { ev.stopPropagation(); primary.fn(o); });
      acts.appendChild(b);
    }
    const more = el('button', 'act ellipsis', '⋯');
    more.addEventListener('click', ev => { ev.stopPropagation(); openDrawer(o); });
    acts.appendChild(more);
    r.appendChild(acts);

    r.addEventListener('click', () => openDrawer(o));
    return r;
  }

  function statusClass(s) {
    return ({ confirm: 'wait', producing: 'prod', ready: 'ship',
              stored: 'hold', shipped: 'done', done: 'done' })[s] || 'hold';
  }
  function statusLabel(s) {
    return ({ confirm: '待确认延发', producing: '待生产', ready: '待发货',
              stored: '已挂账', shipped: '已发货', done: '已完成',
              pending: '待发货', completed: '已完成', cancelled: '已取消' })[s] || s || '—';
  }
  function primaryAction(o) {
    if (o.status === 'confirm')   return { text: '标记已同意', fn: x => setStatus(x, 'producing') };
    if (o.status === 'producing') return { text: '查看生产单', fn: x => {
      const kiln = String(x.goods_name || '').split('·')[0].trim();
      go('production');
      setTimeout(() => {
        const h = [...document.querySelectorAll('#list .group-head h2')]
          .find(n => n.textContent.trim() === kiln);
        if (h) h.closest('.group').scrollIntoView({ block: 'start', behavior: 'smooth' });
      }, 320);
    } };
    if (o.status === 'ready')     return { text: '去发货',    fn: x => setStatus(x, 'shipped') };
    if (o.status === 'shipped')   return { text: '标记完成',  fn: x => setStatus(x, 'done') };
    return null;
  }

  function renderGroups(list) {
    S.groups.forEach(g => {
      const grp = el('div', 'group');
      const head = el('div', 'group-head');
      head.appendChild(el('h2', null, g.label));
      head.appendChild(el('span', 'cnt', g.rows.length + ' 单'));
      if (g.hint) head.appendChild(el('span', 'hint', g.hint));
      const more = el('button', 'more', '查看全部');
      head.appendChild(more);
      grp.appendChild(head);

      const cols = el('div', 'cols');
      cols.appendChild(el('span', null, '客户'));
      cols.appendChild(el('span', null, '商品'));
      const n = el('span', 'num', '数量'); cols.appendChild(n);
      cols.appendChild(el('span', null, '状态'));
      const a = el('span', 'act', '操作'); cols.appendChild(a);
      grp.appendChild(cols);

      g.rows.slice(0, 8).forEach(o => grp.appendChild(rowEl(o, g.key === 'confirm')));
      list.appendChild(grp);
    });
  }

  function renderFlat(list, rows) {
    const grp = el('div', 'group');
    const cols = el('div', 'cols');
    ['客户', '商品', '数量', '状态', '操作'].forEach((t, i) => {
      cols.appendChild(el('span', i === 2 ? 'num' : (i === 4 ? 'act' : null), t));
    });
    grp.appendChild(cols);
    rows.forEach(o => grp.appendChild(rowEl(o, false)));
    list.appendChild(grp);
  }

  function renderKilns(list) {
    S.kilns.forEach(k => {
      const grp = el('div', 'group');
      const head = el('div', 'group-head');
      head.appendChild(el('h2', null, k.name));
      head.appendChild(el('span', 'cnt',
        k.products.length + ' 款 · 待生产 ' + k.pending + ' 件'));
      head.appendChild(el('span', 'hint', '累计 ' + k.orders + ' 单'));
      const btn = el('button', 'more', '导出生产单');
      btn.addEventListener('click', () => exportKiln(k));
      head.appendChild(btn);
      grp.appendChild(head);

      const cols = el('div', 'cols kcols');
      ['商品', '规格', '待生产', '累计'].forEach((t, i) => {
        cols.appendChild(el('span', i >= 2 ? 'num' : null, t));
      });
      grp.appendChild(cols);

      k.products.forEach(p => {
        const r = el('div', 'row krow');
        const item = el('div', 'item');
        item.appendChild(el('div', 'g', p.name));
        r.appendChild(item);
        r.appendChild(el('div', 'spec', p.specs.length ? p.specs.join(' / ') : '—'));
        r.appendChild(el('div', 'qty', p.pending ? p.pending + ' 件' : '—'));
        r.appendChild(el('div', 'qty', p.orders + ' 单'));
        r.style.cursor = 'default';
        grp.appendChild(r);
      });

      list.appendChild(grp);
    });
  }

  function fileUrl(p) {
    if (!p) return '';
    if (/^https?:/i.test(p)) return p;
    return 'file:///' + String(p).replace(/\\/g, '/').replace(/^\/+/, '');
  }

  function renderProducts(list) {
    const grp = el('div', 'group');
    const cols = el('div', 'cols pcols');
    ['图', '商品', '单数', ''].forEach((t, i) =>
      cols.appendChild(el('span', i === 2 ? 'num' : (i === 3 ? 'act' : null), t)));
    grp.appendChild(cols);

    S.rows.forEach(p => {
      const r = el('div', 'row prow');
      r.style.cursor = 'default';

      const cellImg = el('div', 'thumb-cell');
      if (p.thumb) {
        const img = el('img', 'thumb');
        img.src = p.thumb;
        img.alt = '';
        img.addEventListener('error', () => {
          cellImg.textContent = '';
          cellImg.appendChild(el('span', 'thumb ph', '无'));
        });
        cellImg.appendChild(img);
      } else {
        cellImg.appendChild(el('span', 'thumb ph', '无'));
      }
      r.appendChild(cellImg);

      const item = el('div', 'item');
      item.appendChild(el('div', 'g', p.name || '—'));
      item.appendChild(el('div', 'm', (p.kiln || '') + (p.notes ? '　' + p.notes : '')));
      r.appendChild(item);

      r.appendChild(el('div', 'qty', String(p.order_count || 0)));

      const acts = el('div', 'acts');
      const b = el('button', 'act', p.thumb ? '换图' : '找图');
      b.addEventListener('click', () => openImagePicker(p));
      acts.appendChild(b);

      const up = el('button', 'act', '上传');
      up.addEventListener('click', async () => {
        up.disabled = true;
        const pick = await API.pickImage();
        up.disabled = false;
        if (!pick.ok) return toast(pick.error || '没选文件', 'warn');
        const r2 = await API.applyLocalImage(p.id, pick.data.path);
        if (!r2.ok) return toast(r2.error || '保存失败', 'warn');
        toast('已换成本地这张图');
        load();
      });
      acts.appendChild(up);
      r.appendChild(acts);

      grp.appendChild(r);
    });
    list.appendChild(grp);
  }

  /* ── 找图：先给候选，人选完才落库 ─────────────────────── */
  async function openImagePicker(p) {
    $('#drawer-title').textContent = '给「' + (p.name || '') + '」找图';
    const body = $('#drawer-body');
    body.textContent = '';
    body.appendChild(el('div', 'quiet', '正在搜索…'));

    const foot = $('#drawer-foot');
    foot.textContent = '';
    const cancel = el('button', 'btn btn-quiet', '取消');
    cancel.addEventListener('click', closeDrawer);
    foot.appendChild(cancel);

    openDrawerShell();

    const r = await API.fetchImages(p.name || '');
    body.textContent = '';
    if (!r.ok) {
      body.appendChild(el('div', 'blank-t', r.error || '搜索失败'));
      body.appendChild(el('div', 'blank-d', '可以换个更具体的商品名，或者直接手工上传'));
      return;
    }

    body.appendChild(el('div', 'pick-note',
      '搜索词：' + r.data.keyword + '　（搜到的不一定是你要的那款，点一张确认）'));

    const grid = el('div', 'imgpick');
    r.data.items.forEach(it => {
      const btn = el('button');
      const img = el('img');
      img.src = it.thumb;
      img.loading = 'lazy';
      img.alt = it.title || '';
      btn.appendChild(img);
      btn.title = it.title || '';
      btn.addEventListener('click', async () => {
        btn.classList.add('busy');
        const res = await API.applyImage(p.id, it.url, p.name);
        if (!res.ok) {
          btn.classList.remove('busy');
          return toast(res.error || '保存失败', 'warn');
        }
        closeDrawer();
        toast('已换上这张图');
        load();
      });
      grid.appendChild(btn);
    });
    body.appendChild(grid);
  }

  function renderImports(list) {
    const grp = el('div', 'group');
    S.rows.forEach(it => {
      const r = el('div', 'row');
      r.appendChild(el('div', 'cust', it.created_at ? it.created_at.slice(5, 16) : '—'));
      const item = el('div', 'item');
      item.appendChild(el('div', 'g', it.filename || '导入'));
      item.appendChild(el('div', 'm', it.details || ''));
      r.appendChild(item);
      r.appendChild(el('div', 'qty', ''));
      r.appendChild(el('div', 'acts'));
      grp.appendChild(r);
    });
    list.appendChild(grp);
  }

  function renderSettings(list) {
    const wrap = el('div', 'group');
    const head = el('div', 'group-head');
    head.appendChild(el('h2', null, '外观'));
    wrap.appendChild(head);

    const r = el('div', 'row');
    r.style.cursor = 'default';
    r.appendChild(el('div', 'cust', '主题'));
    const item = el('div', 'item');
    item.appendChild(el('div', 'm', '深色适合长时间盯单；浅色适合打印核对'));
    r.appendChild(item);
    const sw = el('div', 'themeswitch');
    ['light', 'dark', 'system'].forEach(m => {
      const b = el('button', m === S.theme ? 'on' : '', { light: '浅色', dark: '深色', system: '系统' }[m]);
      b.addEventListener('click', () => applyTheme(m));
      sw.appendChild(b);
    });
    r.appendChild(el('div'));
    r.appendChild(sw);
    wrap.appendChild(r);
    list.appendChild(wrap);
  }

  /* ── 交互 ──────────────────────────────────────────────────── */
  async function setStatus(o, status) {
    const prev = o.status;
    o.status = status;           // 乐观更新
    render();
    const r = await API.setStatus(o.id, status);
    if (!r.ok) {
      o.status = prev;
      render();
      toast(r.error || '更新失败', 'warn');
      return;
    }
    toast('已更新为「' + statusLabel(status) + '」');
    load();
  }

  function go(page) {
    S.page = page;
    S.sel = -1;
    location.hash = page;
    load(page);
  }

  function openDrawer(o) {
    $('#drawer-title').textContent = '订单 ' + (o.order_no || '');
    const body = $('#drawer-body');
    body.textContent = '';

    const dl = el('dl', 'kv');
    const add = (k, v) => {
      dl.appendChild(el('dt', null, k));
      const has = v !== null && v !== undefined && String(v).trim() !== '';
      dl.appendChild(el('dd', has ? null : 'empty', has ? String(v) : '未填写'));
    };
    add('客户', o.receiver_name || o.customer);
    add('电话', o.receiver_phone);
    add('地址', o.receiver_addr);
    add('商品', o.goods_name || o.product_name);
    add('规格', o.spec);
    add('数量', '×' + (o.quantity || 1));
    add('金额', o.amount ? fmtMoney(o.amount) : '—');
    add('类型', ({ presale: '预售', stored: '预存', normal: '现货' })[o.order_type] || '现货');
    add('状态', statusLabel(o.status));
    add('备注', o.notes);
    add('下单时间', o.created_at);
    body.appendChild(dl);

    const foot = $('#drawer-foot');
    foot.textContent = '';
    const primary = primaryAction(o);
    if (primary) {
      const b = el('button', 'btn btn-primary', primary.text);
      b.addEventListener('click', () => { closeDrawer(); primary.fn(o); });
      foot.appendChild(b);
    }
    const edit = el('button', 'btn btn-ghost', '编辑');
    edit.addEventListener('click', () => openOrderEditor(o));
    foot.appendChild(edit);

    const sp = el('div', 'sp'); foot.appendChild(sp);

    const del = el('button', 'btn btn-quiet danger', '删除');
    let armed = false;
    del.addEventListener('click', async () => {
      if (!armed) {
        armed = true;
        del.textContent = '确认删除？';
        setTimeout(() => { armed = false; del.textContent = '删除'; }, 2600);
        return;
      }
      const r = await API.deleteOrder(o.id);
      if (!r.ok) return toast(r.error || '删除失败', 'warn');
      closeDrawer();
      toast('已删除');
      load();
    });
    foot.appendChild(del);

    openDrawerShell();
  }

  function openDrawerShell() {
    $('#scrim').classList.add('on');
    $('#drawer').classList.add('on');
    $('#drawer').setAttribute('aria-hidden', 'false');
  }

  /* ── 订单表单（新建 / 编辑共用） ─────────────────────────── */
  async function openOrderEditor(order) {
    const isNew = !order;
    const o = order || { status: 'ready', order_type: 'normal', quantity: 1 };
    $('#drawer-title').textContent = isNew ? '新建订单' : '编辑订单';

    // 商品名补全：把商品库已有的名字喂给 datalist，少打字也少打错
    let names = [];
    try {
      const pr = await API.products('');
      if (pr.ok && Array.isArray(pr.data)) {
        names = pr.data.map(p => p.name).filter(Boolean).slice(0, 200);
      }
    } catch (_) {}

    const body = $('#drawer-body');
    body.textContent = '';
    const form = el('div', 'form');
    const dl = el('datalist');
    dl.id = 'goods-names';
    names.forEach(n => {
      const op = el('option');
      op.value = n;
      dl.appendChild(op);
    });
    body.appendChild(dl);

    const field = (label, key, opts) => {
      opts = opts || {};
      const wrap = el('label', opts.full ? 'full' : null);
      const cap = el('span', null, label);
      if (opts.required) {
        const star = el('i', 'req', ' *');
        cap.appendChild(star);
      }
      wrap.appendChild(cap);
      let input;
      if (opts.type === 'select') {
        input = el('select');
        opts.options.forEach(([v, t]) => {
          const op = el('option', null, t);
          op.value = v;
          input.appendChild(op);
        });
        input.value = o[key] != null ? o[key] : opts.options[0][0];
      } else if (opts.type === 'textarea') {
        input = el('textarea');
        input.rows = opts.rows || 3;
        input.value = o[key] || '';
      } else {
        input = el('input');
        input.type = opts.type || 'text';
        input.value = o[key] != null ? o[key] : (opts.default || '');
        if (opts.placeholder) input.placeholder = opts.placeholder;
        if (opts.list) input.setAttribute('list', opts.list);
        if (opts.money) {
          const box = el('div', 'money');
          box.appendChild(el('span', null, '¥'));
          box.appendChild(input);
          input.dataset.key = key;
          wrap.appendChild(box);
          form.appendChild(wrap);
          return input;
        }
      }
      input.dataset.key = key;
      wrap.appendChild(input);
      form.appendChild(wrap);
      return input;
    };

    field('客户', 'receiver_name', { placeholder: '收货人', required: true });
    field('电话', 'receiver_phone', { placeholder: '手机号' });
    field('商品名称', 'goods_name', {
      full: true, required: true, list: 'goods-names',
      placeholder: '可以从下拉里选，也可以直接打',
    });
    field('规格', 'spec', { placeholder: '如 110ml / 32cm' });
    field('数量', 'quantity', { type: 'number', default: 1 });
    field('订单号', 'order_no', { placeholder: '可留空，批量导入时才有' });
    field('金额', 'amount', { type: 'number', placeholder: '0', money: true });
    field('类型', 'order_type', {
      type: 'select',
      options: [['normal', '现货'], ['presale', '预售'], ['stored', '预存']],
    });
    field('状态', 'status', {
      type: 'select',
      options: [['ready', '待发货'], ['confirm', '待确认延发'], ['producing', '待生产'],
                ['stored', '已挂账'], ['shipped', '已发货'], ['done', '已完成']],
    });
    field('地址', 'receiver_addr', { full: true, type: 'textarea', rows: 2, placeholder: '收货地址' });
    const noteInput = field('备注', 'notes', {
      full: true, type: 'textarea',
      placeholder: '写「预售」会自动转生产，写「预存」会挂账',
    });

    // 备注里的关键词自动带出类型与状态，省得她自己判断
    const typeSel = form.querySelector('[data-key="order_type"]');
    const statusSel = form.querySelector('[data-key="status"]');
    noteInput.addEventListener('input', () => {
      const v = noteInput.value;
      if (v.includes('预存')) {
        typeSel.value = 'stored';
        statusSel.value = 'stored';
      } else if (v.includes('预售')) {
        typeSel.value = 'presale';
        if (statusSel.value === 'ready') statusSel.value = 'confirm';
      }
    });

    body.appendChild(form);

    const foot = $('#drawer-foot');
    foot.textContent = '';

    const save = el('button', 'btn btn-primary', isNew ? '保存订单' : '保存修改');
    save.addEventListener('click', async () => {
      const data = isNew ? {} : { id: o.id };
      form.querySelectorAll('[data-key]').forEach(inp => {
        data[inp.dataset.key] = inp.value;
      });
      if (!data.receiver_name || !String(data.receiver_name).trim()) {
        return toast('客户名字还没填', 'warn');
      }
      if (!data.goods_name || !String(data.goods_name).trim()) {
        return toast('商品名称还没填', 'warn');
      }
      save.disabled = true;
      save.textContent = '保存中…';
      const r = await API.saveOrder(data);
      save.disabled = false;
      save.textContent = isNew ? '保存订单' : '保存修改';
      if (!r.ok) return toast(r.error || '保存失败', 'warn');
      closeDrawer();
      toast(isNew ? '已新建订单' : '已保存');
      load();
    });
    foot.appendChild(save);

    const cancel = el('button', 'btn btn-quiet', '取消');
    cancel.addEventListener('click', () => (order ? openDrawer(order) : closeDrawer()));
    foot.appendChild(cancel);

    openDrawerShell();
  }

  function closeDrawer() {
    $('#scrim').classList.remove('on');
    $('#drawer').classList.remove('on');
    $('#drawer').setAttribute('aria-hidden', 'true');
  }

  async function exportKiln(k) {
    toast('正在生成生产单…');
    const r = await API.exportProduction({ kiln: k.name });
    if (!r.ok) return toast(r.error || '导出失败', 'warn');
    toast('已导出 ' + (r.data.count || 0) + ' 款，正在打开…');
    if (r.data.path) API.openPath(r.data.path);
  }

  /* ── 命令面板 ──────────────────────────────────────────────── */
  let cmdIndex = -1;
  function openCmd() {
    $('#cmd').classList.add('on');
    const inp = $('#cmd-input');
    inp.value = S.keyword || '';
    inp.focus();
    cmdSearch('');
  }
  function closeCmd() {
    $('#cmd').classList.remove('on');
    cmdIndex = -1;
  }
  async function cmdSearch(kw) {
    const box = $('#cmd-list');
    box.textContent = '';
    if (!kw) {
      const hint = el('div', 'cmd-item', '输入关键词搜索订单、客户、商品');
      hint.style.color = 'var(--ink-4)';
      box.appendChild(hint);
      return;
    }
    const r = await API.orders('all', kw);
    if (!r.ok) return;
    const rows = (r.data.rows || []).slice(0, 8);
    if (!rows.length) {
      box.appendChild(el('div', 'cmd-item', '没有匹配结果'));
      return;
    }
    rows.forEach(o => {
      const it = el('div', 'cmd-item');
      it.appendChild(el('span', null, (o.receiver_name || '') + '　' + (o.goods_name || '')));
      it.appendChild(el('span', 'k', o.order_no || ''));
      it.addEventListener('click', () => { closeCmd(); openDrawer(o); });
      box.appendChild(it);
    });
  }

  /* ── 键盘 ──────────────────────────────────────────────────── */
  function bindKeys() {
    document.addEventListener('keydown', e => {
      const inField = /^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName);

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault(); openCmd(); return;
      }
      if (e.key === 'Escape') {
        if ($('#cmd').classList.contains('on')) return closeCmd();
        if ($('#drawer').classList.contains('on')) return closeDrawer();
        return;
      }
      if (inField) return;

      const rows = $$('#list .row');
      if (!rows.length) return;

      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        S.sel = Math.max(0, Math.min(rows.length - 1,
          S.sel + (e.key === 'ArrowDown' ? 1 : -1)));
        rows.forEach((r, i) => r.setAttribute('aria-selected', i === S.sel));
        rows[S.sel].scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'Enter' && S.sel >= 0) {
        e.preventDefault();
        rows[S.sel].click();
      }
    });
  }

  /* ── 启动 ──────────────────────────────────────────────────── */
  function bindChrome() {
    $$('.nav').forEach(b =>
      b.addEventListener('click', () => go(b.dataset.page)));

    $$('#theme-switch button').forEach(b =>
      b.addEventListener('click', () => applyTheme(b.dataset.setTheme)));

    $('#filters').addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b) return;
      S.filter = b.dataset.filter;
      $$('#filters button').forEach(x => x.classList.toggle('on', x === b));
      load();
    });

    $('#btn-search').addEventListener('click', openCmd);
    $('#btn-new').addEventListener('click', () => openOrderEditor(null));
    $('#scrim').addEventListener('click', closeDrawer);
    $('#drawer-close').addEventListener('click', closeDrawer);
    $('#btn-import').addEventListener('click', async () => {
      toast('请选择要导入的 CSV 文件…');
      const r = await API.importCsv();
      if (!r.ok) return toast(r.error || '导入取消', 'warn');
      const d = r.data || {};
      let msg = '导入完成：新增 ' + (d.added || 0) + ' 单';
      if (d.dup) msg += '，跳过重复 ' + d.dup;
      if (d.ai_used && d.ai_fields && d.ai_fields.length) {
        msg += '　AI 认出了 ' + d.ai_fields.length + ' 个列名';
      }
      toast(msg);
      load();
    });

    $('#cmd-input').addEventListener('input', e => cmdSearch(e.target.value.trim()));
    $('#cmd-input').addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        const first = $('#cmd-list .cmd-item');
        if (first) first.click();
      }
    });
    document.addEventListener('click', e => {
      if (!e.target.closest('#cmd') && !e.target.closest('#btn-search')) closeCmd();
    });

    $$('#theme-switch button').forEach(b => b.addEventListener('click', closeCmd));
  }

  function start() {
    document.getElementById('list').style.paddingBottom = '28px';
    initTheme();
    bindChrome();
    bindKeys();
    const hash = (location.hash || '').replace('#', '');
    S.page = PAGE_META[hash] ? hash : 'todo';
    load(S.page);
    waitBridge(40);   // pywebviewready 不保证触发，自己轮询更可靠
  }

  /* 桥接就绪后必须重载一次：否则首屏可能停在 mock 假数据上。
     pywebview 注入窗口对象和注入 api 方法之间有时间差，所以用 summary()
     探一次真，确认后端真的答得上话再加载。 */
  async function waitBridge(tries) {
    const t = document.getElementById('sync-state');
    if (API.ready()) {
      const probe = await API.summary();
      if (probe.ok) {
        if (t) t.textContent = '已同步';
        load(S.page);
        return;
      }
    }
    if (tries <= 0) {
      if (t) t.textContent = '未连接后端（预览模式）';
      return;
    }
    setTimeout(() => waitBridge(tries - 1), 150);
  }

  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', start);
  else start();

  // pywebview 注入较晚：桥接可用后重载一次数据
  document.addEventListener('pywebviewready', () => load(S.page));
})();
