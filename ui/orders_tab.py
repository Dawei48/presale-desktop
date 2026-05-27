"""
订单管理 - 属于某个产品/品牌
支持日期选择、状态快捷切换、表格对齐
"""
import customtkinter as ctk
from datetime import datetime, date
from ui.styles import Colors, Fonts, Spacing, Radius
from ui.components import Dialog, ConfirmDialog, Toast, EmptyState, STATUS_MAP


class DatePicker(ctk.CTkFrame):
    """简易日期选择器"""
    def __init__(self, parent, initial=None, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self.date_var = ctk.StringVar(value=initial or date.today().strftime("%Y-%m-%d"))
        self.entry = ctk.CTkEntry(self, textvariable=self.date_var, font=Fonts.BODY, height=36,
                                  width=130, border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
                                  corner_radius=Radius.SM)
        self.entry.pack(side="left")
        ctk.CTkButton(self, text="📅", font=Fonts.BODY, width=36, height=36,
                      fg_color=Colors.BG_INPUT, hover_color=Colors.PRIMARY_LIGHT,
                      text_color=Colors.TEXT_SECONDARY, corner_radius=Radius.SM,
                      command=self._pick).pack(side="left", padx=(4, 0))

    def _pick(self):
        d = DatePickerDialog(self.winfo_toplevel(), self.date_var.get())
        self.winfo_toplevel().wait_window(d)
        if d.result:
            self.date_var.set(d.result)

    def get(self):
        return self.date_var.get()


class DatePickerDialog(ctk.CTkToplevel):
    """日历选择弹窗"""
    def __init__(self, parent, current_date=""):
        super().__init__(parent)
        self.title("选择日期")
        self.geometry("320x340")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=Colors.BG_CARD)
        self.result = None

        try:
            parts = current_date.split("-")
            self.current = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            self.current = date.today()

        self.year = self.current.year
        self.month = self.current.month

        self._build()
        self._center(parent)

    def _center(self, parent):
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        x = px + (pw - 320) // 2
        y = py + (ph - 340) // 2
        self.geometry(f"+{max(x,0)}+{max(y,0)}")

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        # 月份导航
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        ctk.CTkButton(nav, text="◀", width=36, height=32, font=Fonts.BODY,
                      fg_color="transparent", hover_color=Colors.PRIMARY_LIGHT,
                      text_color=Colors.PRIMARY, command=self._prev_month).pack(side="left")
        ctk.CTkLabel(nav, text=f"{self.year}年{self.month}月", font=Fonts.H2,
                     text_color=Colors.TEXT_PRIMARY).pack(side="left", expand=True)
        ctk.CTkButton(nav, text="▶", width=36, height=32, font=Fonts.BODY,
                      fg_color="transparent", hover_color=Colors.PRIMARY_LIGHT,
                      text_color=Colors.PRIMARY, command=self._next_month).pack(side="right")

        # 星期标题
        days_frame = ctk.CTkFrame(self, fg_color="transparent")
        days_frame.pack(fill="x", padx=Spacing.LG)
        for d in ["一", "二", "三", "四", "五", "六", "日"]:
            ctk.CTkLabel(days_frame, text=d, font=Fonts.SMALL_B, width=38,
                         text_color=Colors.TEXT_MUTED).pack(side="left", padx=1)

        # 日期格子
        cal_frame = ctk.CTkFrame(self, fg_color="transparent")
        cal_frame.pack(fill="x", padx=Spacing.LG, pady=Spacing.SM)
        import calendar
        cal = calendar.monthcalendar(self.year, self.month)
        for week in cal:
            row = ctk.CTkFrame(cal_frame, fg_color="transparent")
            row.pack(fill="x")
            for day in week:
                if day == 0:
                    ctk.CTkLabel(row, text="", width=38, height=32).pack(side="left", padx=1)
                else:
                    is_today = (self.year == date.today().year and
                                self.month == date.today().month and
                                day == date.today().day)
                    is_selected = (self.year == self.current.year and
                                   self.month == self.current.month and
                                   day == self.current.day)
                    if is_selected:
                        bg, fg = Colors.PRIMARY, "white"
                    elif is_today:
                        bg, fg = Colors.PRIMARY_LIGHT, Colors.PRIMARY
                    else:
                        bg, fg = "transparent", Colors.TEXT_PRIMARY
                    btn = ctk.CTkButton(row, text=str(day), width=38, height=32,
                                        font=Fonts.SMALL, fg_color=bg, text_color=fg,
                                        hover_color=Colors.PRIMARY_DIM,
                                        corner_radius=Radius.SM,
                                        command=lambda d=day: self._select(d))
                    btn.pack(side="left", padx=1)

        # 底部按钮
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=Spacing.LG, pady=Spacing.SM)
        ctk.CTkButton(bottom, text="今天", font=Fonts.SMALL, height=30,
                      fg_color=Colors.PRIMARY_LIGHT, hover_color=Colors.PRIMARY_DIM,
                      text_color=Colors.PRIMARY, corner_radius=Radius.MD,
                      command=self._today).pack(side="left")
        ctk.CTkButton(bottom, text="取消", font=Fonts.SMALL, height=30, width=60,
                      fg_color=Colors.BG_INPUT, hover_color=Colors.BORDER,
                      text_color=Colors.TEXT_SECONDARY, corner_radius=Radius.MD,
                      command=self.destroy).pack(side="right", padx=(4, 0))
        ctk.CTkButton(bottom, text="确定", font=Fonts.SMALL_B, height=30, width=60,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      corner_radius=Radius.MD,
                      command=self._confirm).pack(side="right")

    def _prev_month(self):
        if self.month == 1:
            self.month = 12; self.year -= 1
        else:
            self.month -= 1
        self._build()

    def _next_month(self):
        if self.month == 12:
            self.month = 1; self.year += 1
        else:
            self.month += 1
        self._build()

    def _select(self, day):
        self.result = f"{self.year}-{self.month:02d}-{day:02d}"
        self.destroy()

    def _today(self):
        self.result = date.today().strftime("%Y-%m-%d")
        self.destroy()

    def _confirm(self):
        self.result = f"{self.year}-{self.month:02d}-{self.current.day:02d}"
        self.destroy()


class OrderDialog(Dialog):
    def __init__(self, parent, db, product, order=None, on_save=None):
        self.db = db
        self.product = product
        self.order = order
        self.on_save = on_save
        super().__init__(parent, "编辑订单" if order else "新增订单", width=420, height=380)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)
        form.columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text=f"📦 {product['name']}  ¥{product['price']:,.0f}",
                     font=Fonts.BODY_B, text_color=Colors.PRIMARY).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, Spacing.MD))

        self.entry_order_no = self._make_field(form, "订单号", 1)
        self.entry_customer = self._make_field(form, "客户 *", 2)
        self.entry_qty = self._make_field(form, "数量 *", 3)
        self.entry_notes = self._make_field(form, "备注", 4)

        # 日期选择器
        ctk.CTkLabel(form, text="日期", font=Fonts.BODY,
                     text_color=Colors.TEXT_SECONDARY).grid(
            row=5, column=0, sticky="w", pady=(Spacing.SM, 2), padx=Spacing.XS)
        initial_date = order.get("created_at", "")[:10] if order else ""
        self.date_picker = DatePicker(form, initial=initial_date if initial_date else None)
        self.date_picker.grid(row=5, column=1, sticky="w", pady=(Spacing.SM, 2), padx=Spacing.XS)

        if order:
            self.entry_order_no.insert(0, order.get("order_no", ""))
            self.entry_customer.insert(0, order.get("customer", ""))
            self.entry_qty.insert(0, str(order.get("quantity", 1)))
            self.entry_notes.insert(0, order.get("notes", ""))

        self._make_buttons(form, 6)

    def _on_ok(self):
        customer = self.entry_customer.get().strip()
        if not customer:
            Toast(self, "客户名称不能为空", "error")
            return
        try:
            qty = int(self.entry_qty.get() or 1)
        except ValueError:
            Toast(self, "数量必须是数字", "error")
            return
        self.result = {
            "order_no": self.entry_order_no.get().strip(),
            "customer": customer,
            "quantity": qty,
            "notes": self.entry_notes.get().strip(),
            "created_at": self.date_picker.get() + " " + datetime.now().strftime("%H:%M:%S"),
        }
        if self.on_save:
            self.on_save(self.result)
        self.destroy()


class OrdersTab(ctk.CTkFrame):
    def __init__(self, parent, db, current_user, product=None, brand=None, on_back=None):
        super().__init__(parent, fg_color=Colors.BG_MAIN)
        self.db = db
        self.current_user = current_user
        self.product = product
        self.brand = brand
        self.on_back = on_back
        self.current_status_filter = ""
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._load())
        self._build()
        self._load()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.XL, pady=(Spacing.XL, Spacing.LG))

        if self.on_back:
            ctk.CTkButton(header, text="← 返回", font=Fonts.SMALL, height=32,
                          fg_color=Colors.PRIMARY_LIGHT, hover_color=Colors.PRIMARY_DIM,
                          text_color=Colors.PRIMARY, corner_radius=Radius.MD,
                          command=self._go_back).pack(side="left")

        title = ""
        if self.brand:
            title += self.brand["name"]
        if self.product:
            title += f" / {self.product['name']}"
        if not title:
            title = "全部订单"

        ctk.CTkLabel(header, text=title, font=Fonts.H1,
                     text_color=Colors.TEXT_PRIMARY).pack(side="left", padx=(Spacing.SM, 0))

        ctk.CTkButton(header, text="＋ 新增订单", font=Fonts.BODY_B, height=38,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      corner_radius=Radius.MD, command=self._add).pack(side="right")

        # 搜索 + 状态筛选
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=Spacing.XL, pady=(0, Spacing.MD))

        ctk.CTkEntry(toolbar, textvariable=self.search_var,
                     placeholder_text="🔍  搜索订单号、客户...",
                     font=Fonts.BODY, height=38, width=260,
                     border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
                     corner_radius=Radius.MD).pack(side="left")

        self.filter_btns = {}
        btn = ctk.CTkButton(toolbar, text="全部", font=Fonts.SMALL, height=28, width=56,
                            fg_color=Colors.PRIMARY, corner_radius=Radius.MD,
                            command=lambda: self._filter(""))
        btn.pack(side="left", padx=(Spacing.MD, 4))
        self.filter_btns[""] = btn
        for key, (label, fg, bg) in STATUS_MAP.items():
            b = ctk.CTkButton(toolbar, text=label, font=Fonts.SMALL, height=28, width=56,
                              fg_color="transparent", text_color=fg, hover_color=bg,
                              border_width=1, border_color=fg, corner_radius=Radius.MD,
                              command=lambda k=key: self._filter(k))
            b.pack(side="left", padx=4)
            self.filter_btns[key] = b

        self.count_label = ctk.CTkLabel(toolbar, text="", font=Fonts.SMALL,
                                        text_color=Colors.TEXT_MUTED)
        self.count_label.pack(side="right")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
            scrollbar_button_color=Colors.BORDER, scrollbar_button_hover_color=Colors.TEXT_MUTED)
        self.scroll.pack(fill="both", expand=True, padx=Spacing.XL, pady=(0, Spacing.XL))

    def _go_back(self):
        if self.on_back:
            self.on_back()

    def _filter(self, status):
        self.current_status_filter = status
        for key, btn in self.filter_btns.items():
            if key == status:
                fg = Colors.PRIMARY if key == "" else STATUS_MAP[key][1]
                btn.configure(fg_color=fg, text_color="white", border_width=0)
            else:
                fg = Colors.TEXT_MUTED if key == "" else STATUS_MAP[key][1]
                btn.configure(fg_color="transparent", text_color=fg, border_width=1, border_color=fg)
        self._load()

    def _load(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        keyword = self.search_var.get().strip() or None
        orders = self.db.get_orders(
            product_id=self.product["id"] if self.product else None,
            brand_id=self.brand["id"] if self.brand and not self.product else None,
            status=self.current_status_filter or None,
            keyword=keyword,
        )
        self.count_label.configure(text=f"共 {len(orders)} 笔")
        if not orders:
            EmptyState(self.scroll, "📋", "暂无订单").pack(fill="x")
            return

        # 表格容器
        table = ctk.CTkFrame(self.scroll, fg_color="transparent")
        table.pack(fill="x")

        # 列定义: (标题, 宽度)
        cols = [("订单号", 130), ("客户", 80), ("产品", 120), ("数量", 50),
                ("状态", 180), ("备注", 100), ("日期", 90), ("", 80)]

        # 表头
        hdr = ctk.CTkFrame(table, fg_color=Colors.SIDEBAR_BG, corner_radius=Radius.MD, height=38)
        hdr.pack(fill="x", pady=(0, 2))
        hdr.pack_propagate(False)
        for i, (h, w) in enumerate(cols):
            ctk.CTkLabel(hdr, text=h, font=Fonts.SMALL_B, text_color="white",
                         anchor="w", width=w).grid(row=0, column=i, sticky="w",
                                                    padx=Spacing.SM, pady=Spacing.XS)

        # 数据行
        for idx, order in enumerate(orders):
            bg = Colors.BG_INPUT if idx % 2 == 0 else "transparent"
            row = ctk.CTkFrame(table, fg_color=bg, corner_radius=Radius.SM, height=40)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            vals = [
                order.get("order_no", ""),
                order.get("customer", ""),
                order.get("product_name", ""),
                str(order.get("quantity", 0)),
                STATUS_MAP.get(order.get("status", "pending"), ("未知", "", ""))[0],
                order.get("notes", ""),
                order.get("created_at", "")[:10],
            ]
            widths = [130, 80, 120, 50, 180, 100, 90, 80]

            for i, v in enumerate(vals):
                if i == 4:
                    # 状态列: 4个快捷按钮
                    sf = ctk.CTkFrame(row, fg_color="transparent")
                    sf.grid(row=0, column=i, sticky="w", padx=Spacing.SM)
                    for skey, (slabel, sfg, sbg) in STATUS_MAP.items():
                        is_active = (skey == order.get("status", "pending"))
                        ctk.CTkButton(sf, text=slabel, font=Fonts.TINY, width=40, height=22,
                                      fg_color=sfg if is_active else "transparent",
                                      text_color="white" if is_active else sfg,
                                      hover_color=sfg,
                                      border_width=0 if is_active else 1,
                                      border_color=sfg,
                                      corner_radius=Radius.SM,
                                      command=lambda o=order, sk=skey: self._set_status(o, sk)).pack(
                            side="left", padx=1)
                else:
                    ctk.CTkLabel(row, text=v, font=Fonts.BODY,
                                 text_color=Colors.TEXT_PRIMARY, anchor="w",
                                 width=widths[i]).grid(row=0, column=i, sticky="w",
                                                        padx=Spacing.SM)

            # 操作按钮
            btn_f = ctk.CTkFrame(row, fg_color="transparent")
            btn_f.grid(row=0, column=len(vals), sticky="w", padx=Spacing.SM)
            ctk.CTkButton(btn_f, text="✏️", font=Fonts.SMALL, width=28, height=26,
                          fg_color=Colors.BG_INPUT, hover_color=Colors.PRIMARY_LIGHT,
                          text_color=Colors.TEXT_SECONDARY, corner_radius=Radius.SM,
                          command=lambda o=order: self._edit(o)).pack(side="left", padx=2)
            ctk.CTkButton(btn_f, text="🗑", font=Fonts.SMALL, width=28, height=26,
                          fg_color=Colors.BG_INPUT, hover_color=Colors.DANGER_LIGHT,
                          text_color=Colors.TEXT_MUTED, corner_radius=Radius.SM,
                          command=lambda o=order: self._delete(o)).pack(side="left", padx=2)

    def _set_status(self, order, new_status):
        self.db.update_order(order["id"], status=new_status)
        self.db.log("更新状态", f"订单 {order.get('order_no', '')} → {STATUS_MAP[new_status][0]}",
                    self.current_user["id"], self.current_user["username"])
        Toast(self, f"✅ 已切换为{STATUS_MAP[new_status][0]}")
        self._load()

    def _add(self):
        def on_save(data):
            self.db.add_order(product_id=self.product["id"], **data)
            self.db.log("新增订单", f"订单: {data.get('order_no', '')}",
                        self.current_user["id"], self.current_user["username"])
            Toast(self, "✅ 订单已创建")
            self._load()
        OrderDialog(self, self.db, self.product, on_save=on_save)

    def _edit(self, order):
        def on_save(data):
            self.db.update_order(order["id"], **data)
            self.db.log("编辑订单", f"订单: {data.get('order_no', '')}",
                        self.current_user["id"], self.current_user["username"])
            Toast(self, "✅ 订单已更新")
            self._load()
        OrderDialog(self, self.db, self.product, order=order, on_save=on_save)

    def _delete(self, order):
        d = ConfirmDialog(self, "确定要删除这笔订单吗？")
        self.wait_window(d)
        if d.result:
            self.db.delete_order(order["id"])
            self.db.log("删除订单", f"订单: {order.get('order_no', '')}",
                        self.current_user["id"], self.current_user["username"])
            Toast(self, "🗑️ 订单已删除")
            self._load()

    def refresh(self):
        self._load()
