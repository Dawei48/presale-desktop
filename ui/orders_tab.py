"""
订单管理 - 属于某个产品/品牌
"""
import customtkinter as ctk
from ui.styles import Colors, Fonts, Spacing, Radius
from ui.components import Dialog, ConfirmDialog, Toast, EmptyState, StatusBadge, STATUS_MAP


class OrderDialog(Dialog):
    def __init__(self, parent, db, product, order=None, on_save=None):
        self.db = db
        self.product = product
        self.order = order
        self.on_save = on_save
        super().__init__(parent, "编辑订单" if order else "新增订单", width=400, height=320)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)
        form.columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text=f"产品: {product['name']}  ¥{product['price']:,.0f}",
                     font=Fonts.BODY_B, text_color=Colors.PRIMARY).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, Spacing.MD))
        self.entry_order_no = self._make_field(form, "订单号", 1)
        self.entry_customer = self._make_field(form, "客户", 2)
        self.entry_qty = self._make_field(form, "数量 *", 3)
        self.entry_notes = self._make_field(form, "备注", 4)

        if order:
            self.entry_order_no.insert(0, order.get("order_no", ""))
            self.entry_customer.insert(0, order.get("customer", ""))
            self.entry_qty.insert(0, str(order.get("quantity", 1)))
            self.entry_notes.insert(0, order.get("notes", ""))

        self._make_buttons(form, 5)

    def _on_ok(self):
        try:
            qty = int(self.entry_qty.get() or 1)
        except ValueError:
            Toast(self, "数量必须是数字", "error")
            return
        self.result = {
            "order_no": self.entry_order_no.get().strip(),
            "customer": self.entry_customer.get().strip(),
            "quantity": qty,
            "notes": self.entry_notes.get().strip(),
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
                          fg_color="transparent", hover_color=Colors.PRIMARY_LIGHT,
                          text_color=Colors.PRIMARY, corner_radius=Radius.SM,
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

        ctk.CTkButton(header, text="＋ 新增订单", font=Fonts.BODY_B, height=36,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      corner_radius=Radius.SM, command=self._add).pack(side="right")

        # 搜索 + 状态筛选
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=Spacing.XL, pady=(0, Spacing.MD))

        ctk.CTkEntry(toolbar, textvariable=self.search_var,
                     placeholder_text="🔍  搜索订单号、客户...",
                     font=Fonts.BODY, height=38, width=300,
                     border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
                     corner_radius=Radius.SM).pack(side="left")

        self.filter_btns = {}
        btn = ctk.CTkButton(toolbar, text="全部", font=Fonts.SMALL, height=28, width=56,
                            fg_color=Colors.PRIMARY, corner_radius=Radius.SM,
                            command=lambda: self._filter(""))
        btn.pack(side="left", padx=(Spacing.MD, 4))
        self.filter_btns[""] = btn
        for key, (label, fg, bg) in STATUS_MAP.items():
            b = ctk.CTkButton(toolbar, text=label, font=Fonts.SMALL, height=28, width=56,
                              fg_color="transparent", text_color=fg, hover_color=bg,
                              border_width=1, border_color=fg, corner_radius=Radius.SM,
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

        # 表头
        hdr = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 4))
        cols = [("订单号", 100), ("客户", 80), ("产品", 100), ("数量", 50),
                ("状态", 60), ("备注", 120), ("日期", 80), ("", 120)]
        for i, (h, w) in enumerate(cols):
            ctk.CTkLabel(hdr, text=h, font=Fonts.SMALL_B, text_color=Colors.TEXT_MUTED,
                         anchor="w", width=w).grid(row=0, column=i, sticky="w", padx=Spacing.SM)

        for idx, order in enumerate(orders):
            bg = Colors.BG_INPUT if idx % 2 == 0 else "transparent"
            row = ctk.CTkFrame(self.scroll, fg_color=bg, corner_radius=Radius.SM, height=38)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            vals = [
                order.get("order_no", ""),
                order.get("customer", ""),
                order.get("product_name", ""),
                str(order.get("quantity", 0)),
                order.get("status", "pending"),
                order.get("notes", ""),
                order.get("created_at", "")[:10],
            ]
            widths = [100, 80, 100, 50, 60, 120, 80]
            for i, v in enumerate(vals):
                if i == 4:
                    f = ctk.CTkFrame(row, fg_color="transparent")
                    f.grid(row=0, column=i, sticky="w", padx=Spacing.SM)
                    StatusBadge(f, v)
                else:
                    ctk.CTkLabel(row, text=v, font=Fonts.BODY,
                                 text_color=Colors.TEXT_PRIMARY, anchor="w",
                                 width=widths[i]).grid(row=0, column=i, sticky="w", padx=Spacing.SM)

            btn_f = ctk.CTkFrame(row, fg_color="transparent")
            btn_f.grid(row=0, column=len(vals), sticky="w", padx=Spacing.SM)
            ctk.CTkButton(btn_f, text="编辑", font=Fonts.SMALL, width=48, height=26,
                          fg_color="transparent", hover_color=Colors.PRIMARY_LIGHT,
                          text_color=Colors.PRIMARY, corner_radius=Radius.SM,
                          command=lambda o=order: self._edit(o)).pack(side="left", padx=2)
            ctk.CTkButton(btn_f, text="删除", font=Fonts.SMALL, width=48, height=26,
                          fg_color="transparent", hover_color=Colors.DANGER_LIGHT,
                          text_color=Colors.DANGER, corner_radius=Radius.SM,
                          command=lambda o=order: self._delete(o)).pack(side="left", padx=2)

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
