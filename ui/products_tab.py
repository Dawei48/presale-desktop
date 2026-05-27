"""
产品管理 - 属于某个品牌
"""
import customtkinter as ctk
from ui.styles import Colors, Fonts, Spacing, Radius
from ui.components import Dialog, ConfirmDialog, Toast, EmptyState


class ProductDialog(Dialog):
    def __init__(self, parent, db, brand_id, product=None, on_save=None):
        self.db = db
        self.brand_id = brand_id
        self.product = product
        self.on_save = on_save
        super().__init__(parent, "编辑产品" if product else "新增产品", width=400, height=280)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)
        form.columnconfigure(1, weight=1)
        self.entry_name = self._make_field(form, "产品名称 *", 0)
        self.entry_price = self._make_field(form, "价格 (元)", 1)
        self.entry_notes = self._make_field(form, "备注", 2)
        self._make_buttons(form, 3)

        if product:
            self.entry_name.insert(0, product["name"])
            self.entry_price.insert(0, str(product.get("price", 0)))
            self.entry_notes.insert(0, product.get("notes", ""))

    def _on_ok(self):
        name = self.entry_name.get().strip()
        if not name:
            Toast(self, "产品名称不能为空", "error")
            return
        try:
            price = float(self.entry_price.get() or 0)
        except ValueError:
            Toast(self, "价格必须是数字", "error")
            return
        self.result = {
            "brand_id": self.brand_id,
            "name": name,
            "price": price,
            "notes": self.entry_notes.get().strip(),
        }
        if self.on_save:
            self.on_save(self.result)
        self.destroy()


class ProductsTab(ctk.CTkFrame):
    def __init__(self, parent, db, current_user, brand=None, on_back=None):
        super().__init__(parent, fg_color=Colors.BG_MAIN)
        self.db = db
        self.current_user = current_user
        self.brand = brand
        self.on_back = on_back
        self._build()
        self._load()

    def _build(self):
        # 标题行 + 返回按钮
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.XL, pady=(Spacing.XL, Spacing.LG))

        if self.brand:
            ctk.CTkButton(header, text="← 返回品牌", font=Fonts.SMALL, height=32,
                          fg_color="transparent", hover_color=Colors.PRIMARY_LIGHT,
                          text_color=Colors.PRIMARY, corner_radius=Radius.SM,
                          command=self._go_back).pack(side="left")
            ctk.CTkLabel(header, text=f"  {self.brand['name']}", font=Fonts.H1,
                         text_color=Colors.TEXT_PRIMARY).pack(side="left", padx=(Spacing.SM, 0))
        else:
            ctk.CTkLabel(header, text="产品管理", font=Fonts.H1,
                         text_color=Colors.TEXT_PRIMARY).pack(side="left")

        ctk.CTkButton(header, text="＋ 新增产品", font=Fonts.BODY_B, height=36,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      corner_radius=Radius.SM, command=self._add).pack(side="right")

        self.count_label = ctk.CTkLabel(self, text="", font=Fonts.SMALL,
                                        text_color=Colors.TEXT_MUTED)
        self.count_label.pack(anchor="w", padx=Spacing.XL, pady=(0, Spacing.SM))

        self.list_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=Spacing.XL, pady=(0, Spacing.XL))

    def _go_back(self):
        if self.on_back:
            self.on_back()

    def _load(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        products = self.db.get_products(brand_id=self.brand["id"] if self.brand else None)
        self.count_label.configure(text=f"共 {len(products)} 个产品")
        if not products:
            EmptyState(self.list_frame, "📦", "暂无产品").pack(fill="x")
            return
        for p in products:
            card = ctk.CTkFrame(self.list_frame, fg_color=Colors.BG_CARD,
                                corner_radius=Radius.LG, border_width=1,
                                border_color=Colors.BORDER)
            card.pack(fill="x", pady=(0, Spacing.SM))
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=Spacing.LG, pady=Spacing.LG)
            left = ctk.CTkFrame(inner, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(left, text=p["name"], font=Fonts.H2,
                         text_color=Colors.TEXT_PRIMARY).pack(side="left")
            ctk.CTkLabel(left, text=f"  ¥{p['price']:,.0f}", font=Fonts.H2,
                         text_color=Colors.PRIMARY).pack(side="left", padx=(Spacing.MD, 0))
            # 查看订单数
            order_count = len(self.db.get_orders(product_id=p["id"]))
            ctk.CTkLabel(left, text=f"  {order_count} 笔订单",
                         font=Fonts.SMALL, text_color=Colors.TEXT_MUTED).pack(
                side="left", padx=(Spacing.SM, 0))
            if p.get("notes"):
                ctk.CTkLabel(left, text=f"  {p['notes']}", font=Fonts.SMALL,
                             text_color=Colors.TEXT_MUTED).pack(side="left", padx=(Spacing.SM, 0))
            btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
            btn_frame.pack(side="right")
            ctk.CTkButton(btn_frame, text="查看订单", font=Fonts.SMALL, width=70, height=28,
                          fg_color=Colors.PRIMARY_LIGHT, hover_color=Colors.PRIMARY_DIM,
                          text_color=Colors.PRIMARY, corner_radius=Radius.SM,
                          command=lambda p=p: self._go_orders(p)).pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text="编辑", font=Fonts.SMALL, width=48, height=28,
                          fg_color="transparent", hover_color=Colors.PRIMARY_LIGHT,
                          text_color=Colors.PRIMARY, corner_radius=Radius.SM,
                          command=lambda p=p: self._edit(p)).pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text="删除", font=Fonts.SMALL, width=48, height=28,
                          fg_color="transparent", hover_color=Colors.DANGER_LIGHT,
                          text_color=Colors.DANGER, corner_radius=Radius.SM,
                          command=lambda p=p: self._delete(p)).pack(side="left", padx=2)

    def _go_orders(self, product):
        from ui.orders_tab import OrdersTab
        for w in self.master.winfo_children():
            w.destroy()
        OrdersTab(self.master, self.db, self.current_user,
                  product=product, brand=self.brand,
                  on_back=lambda: self.__class__(self.master, self.db, self.current_user,
                                                 self.brand, self.on_back)).pack(fill="both", expand=True)

    def _add(self):
        def on_save(data):
            self.db.add_product(**data)
            self.db.log("新增产品", f"产品: {data['name']}", self.current_user["id"], self.current_user["username"])
            Toast(self, "✅ 产品已添加")
            self._load()
        ProductDialog(self, self.db, self.brand["id"], on_save=on_save)

    def _edit(self, product):
        def on_save(data):
            self.db.update_product(product["id"], name=data["name"], price=data["price"], notes=data["notes"])
            self.db.log("编辑产品", f"产品: {data['name']}", self.current_user["id"], self.current_user["username"])
            Toast(self, "✅ 产品已更新")
            self._load()
        ProductDialog(self, self.db, self.brand["id"], product=product, on_save=on_save)

    def _delete(self, product):
        d = ConfirmDialog(self, f"确定要删除产品「{product['name']}」吗？\n该产品下所有订单都会被删除。")
        self.wait_window(d)
        if d.result:
            self.db.delete_product(product["id"])
            self.db.log("删除产品", f"产品: {product['name']}", self.current_user["id"], self.current_user["username"])
            Toast(self, "🗑️ 产品已删除")
            self._load()

    def refresh(self):
        self._load()
