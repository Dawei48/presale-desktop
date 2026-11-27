/* ═══════════════════════════════════════════════════════════════════
   mock.js — 只在「浏览器直接打开 index.html」时生效
   目的：调样式 / 验交互时不必起 Python。pywebview 里会被真实后端覆盖。
   ═══════════════════════════════════════════════════════════════════ */
(function (g) {
  'use strict';
  if (g.pywebview) return;

  const today = new Date();
  const dt = d => {
    const x = new Date(today.getTime() - d * 86400000);
    return x.toISOString().slice(0, 19).replace('T', ' ');
  };

  let seq = 69238401760;
  const mk = (o) => Object.assign({
    id: ++seq, order_no: String(seq), quantity: 1, order_type: 'normal',
    status: 'ready', created_at: dt(0), amount: 0, shop_type: '抖音',
  }, o);

  const rows = [
    mk({ receiver_name: '赵敏', goods_name: '玉柏 · 青花缠枝四季花 · 茶壶', spec: '260ml',
         notes: '客户要礼盒', status: 'confirm', order_type: 'presale', amount: 1280, created_at: dt(1) }),
    mk({ receiver_name: '李雨桐', goods_name: '春风祥玉 · 青花缠枝莲 · 盖碗', spec: '110ml',
         status: 'confirm', order_type: 'presale', amount: 960, created_at: dt(1) }),
    mk({ receiver_name: '陈默', goods_name: '九段烧 · 釉里红 · 主人杯', spec: '85ml', quantity: 2,
         status: 'confirm', order_type: 'presale', amount: 1560, created_at: dt(2) }),
    mk({ receiver_name: '孙小满', goods_name: '春风祥玉 · 青花 · 压手杯', spec: '90ml',
         notes: '已报窑口 11-24', status: 'producing', order_type: 'presale', amount: 680, created_at: dt(4) }),
    mk({ receiver_name: '郑楠', goods_name: '艺林堂 · 粉彩四季花 · 赏瓶', spec: '32cm',
         status: 'producing', order_type: 'presale', amount: 3600, created_at: dt(5) }),
    mk({ receiver_name: '林秋', goods_name: '玉柏 · 青花缠枝莲 · 品茗杯', spec: '60ml', quantity: 4,
         status: 'producing', order_type: 'presale', amount: 880, created_at: dt(6) }),
    mk({ receiver_name: '吴岚', goods_name: '玉柏 · 青花缠枝莲 · 品茗杯', spec: '60ml', quantity: 4,
         notes: '现货', status: 'ready', amount: 880, created_at: dt(0) }),
    mk({ receiver_name: '周氏文旅', goods_name: '艺林堂 · 粉彩四季花 · 赏瓶', spec: '32cm', quantity: 4,
         notes: '政府消费券', status: 'stored', order_type: 'stored', amount: 14400, created_at: dt(2) }),
    mk({ receiver_name: '何书宁', goods_name: '九段烧 · 青花 · 盖碗', spec: '130ml',
         status: 'shipped', order_type: 'presale', amount: 1120, created_at: dt(9) }),
    mk({ receiver_name: '许知白', goods_name: '春风祥玉 · 青花缠枝莲 · 品茗杯', spec: '55ml', quantity: 2,
         status: 'done', amount: 760, created_at: dt(12) }),
  ];

  const counts = () => {
    const c = { total: rows.length };
    rows.forEach(r => { c[r.status] = (c[r.status] || 0) + 1; });
    return c;
  };

  const match = (r, filter, kw) => {
    if (filter && filter !== 'all') {
      if (['presale', 'normal', 'stored'].includes(filter)) { if (r.order_type !== filter) return false; }
      else if (r.status !== filter) return false;
    }
    if (kw) {
      const s = (r.order_no + r.receiver_name + r.goods_name + r.notes).toLowerCase();
      if (!s.includes(kw.toLowerCase())) return false;
    }
    return true;
  };

  g.MOCK = {
    summary: async () => ({ ok: true, data: { counts: counts(), todo: 8 } }),
    orders: async (filter, kw) => {
      const rs = rows.filter(r => match(r, filter, kw));
      return { ok: true, data: { rows: rs, counts: counts(), todo: rs.length } };
    },
    order_detail: async id => ({ ok: true, data: rows.find(r => r.id === +id) || null }),
    set_status: async (id, status) => {
      const r = rows.find(x => x.id === +id);
      if (!r) return { ok: false, error: '订单不存在' };
      r.status = status;
      return { ok: true };
    },
    set_order_type: async (id, t) => {
      const r = rows.find(x => x.id === +id);
      if (!r) return { ok: false, error: '订单不存在' };
      r.order_type = t;
      return { ok: true };
    },
    export_production: async () => ({ ok: true, data: { count: 3, path: '' } }),
    import_csv: async () => ({ ok: false, error: '浏览器预览模式无法导入' }),
    products: async () => {
      const map = {};
      rows.forEach(r => {
        const kiln = String(r.goods_name).split('·')[0].trim();
        const k = kiln + '|' + r.goods_name;
        map[k] = map[k] || { kiln, name: r.goods_name, order_count: 0, notes: r.spec };
        map[k].order_count += 1;
      });
      return { ok: true, data: Object.values(map) };
    },
    imports: async () => ({ ok: true, data: [
      { created_at: dt(1), filename: '抖音订单_1127.csv', details: '新增 42 单，跳过重复 3 单' },
      { created_at: dt(3), filename: '视频号_1125.csv', details: '新增 18 单' },
    ] }),
    get_settings: async () => ({ ok: true, data: {} }),
    save_settings: async () => ({ ok: true }),
    set_theme: async () => ({ ok: true }),
    open_path: async () => ({ ok: true }),
    save_file: async () => ({ ok: true }),
  };
})(window);
