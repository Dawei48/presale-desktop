"""
产品管理 - 属于某个品牌
支持产品图片上传，无备注（备注在订单层）
"""
import os
import shutil
import uuid
import customtkinter as ctk
from tkinter import filedialog
from ui.styles import Colors, Fonts, Spacing, Radius
from ui.components import Dialog, ConfirmDialog, Toast, EmptyState
from config import IMAGES_DIR


class ProductDialog(Dialog):
    def __init__(self, parent, db, brand_id, product=None, on_save=None):
        self.db = db
        self.brand_id = brand_id
        self.product = product
        self.on_save = on_save
        self.image_path = product.get("image_path", "") if product else ""
        super().__init__(parent, "编辑产品" if product else "新增产品", width=420, height=360)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)
        form.columnconfigure(1, weight=1)

        # 图片区域
        img_row = ctk.CTkFrame(form, fg_color="transparent")
        img_row.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, Spacing.MD))

        self.img_label = ctk.CTkLabel(img_row, text="📷\n选择图片",
                                      font=Fonts.SMALL, text_color=Colors.TEXT_MUTED,
                                      width=100, height=100,
                                      fg_color=Colors.BG_INPUT, corner_radius=Radius.MD)
        self.img_label.pack(side="left")
        self.img_label.bind("<Button-1>", lambda e: self._pick_image())

        btn_col = ctk.CTkFrame(img_row, fg_color="transparent")
        btn_col.pack(side="left", padx=(Spacing.MD, 0))
        ctk.CTkButton(btn_col, text="📁 选择图片", font=Fonts.SMALL, height=32,
                      fg_color=Colors.PRIMARY_LIGHT, hover_color=Colors.PRIMARY_DIM,
                      text_color=Colors.PRIMARY, corner_radius=Radius.MD,
                      command=self._pick_image).pack(anchor="w")
        if self.image_path:
            ctk.CTkButton(btn_col, text="✕ 移除图片", font=Fonts.SMALL, height=32,
                          fg_color=Colors.DANGER_LIGHT, hover_color="#FECACA",
                          text_color=Colors.DANGER, corner_radius=Radius.MD,
                          command=self._remove_image).pack(anchor="w", pady=(4, 0))

        self._refresh_preview()

        self.entry_name = self._make_field(form, "产品名称 *", 1)
        self.entry_price = self._make_field(form, "价格 (元)", 2)
        self._make_buttons(form, 3)

        if product:
            self.entry_name.insert(0, product["name"])
            self.entry_price.insert(0, str(product.get("price", 0)))

    def _pick_image(self):
        filetypes = [("图片", "*.png *.jpg *.jpeg *.gif *.webp"), ("所有文件", "*.*")]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            ext = os.path.splitext(path)[1].lower()
            filename = f"{uuid.uuid4().hex[:12]}{ext}"
            dest = os.path.join(IMAGES_DIR, filename)
            shutil.copy2(path, dest)
            self.image_path = dest
            self._refresh_preview()

    def _remove_image(self):
        self.image_path = ""
        self._refresh_preview()

    def _refresh_preview(self):
        if self.image_path and os.path.exists(self.image_path):
            try:
                from PIL import Image as PILImage
                img = PILImage.open(self.image_path)
                img.thumbnail((100, 100))
                from customtkinter import CTkImage
                ctk_img = CTkImage(light_mode=img, dark_mode=img, size=img.size)
                self.img_label.configure(image=ctk_img, text="", width=100, height=100)
                self.img_label._img = ctk_img
            except Exception as e:
                self.img_label.configure(text=f"⚠\n{str(e)[:20]}", image="")
        else:
            self.img_label.configure(text="📷\n选择图片", image="", width=100, height=100)

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
            "notes": "",
            "image_path": self.image_path,
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
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.XL, pady=(Spacing.XL, Spacing.LG))

        if self.brand:
            ctk.CTkButton(header, text="← 返回品牌", font=Fonts.SMALL, height=32,
                          fg_color=Colors.PRIMARY_LIGHT, hover_color=Colors.PRIMARY_DIM,
                          text_color=Colors.PRIMARY, corner_radius=Radius.MD,
                          command=self._go_back).pack(side="left")
            ctk.CTkLabel(header, text=f"  {self.brand['name']}", font=Fonts.H1,
                         text_color=Colors.TEXT_PRIMARY).pack(side="left", padx=(Spacing.SM, 0))
        else:
            ctk.CTkLabel(header, text="产品管理", font=Fonts.H1,
                         text_color=Colors.TEXT_PRIMARY).pack(side="left")

        ctk.CTkButton(header, text="＋ 新增产品", font=Fonts.BODY_B, height=38,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      corner_radius=Radius.MD, command=self._add).pack(side="right")

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

            # 缩略图
            img_path = p.get("image_path", "")
            if img_path and os.path.exists(img_path):
                try:
                    from PIL import Image as PILImage
                    from customtkinter import CTkImage
                    img = PILImage.open(img_path)
                    img.thumbnail((64, 64))
                    ctk_img = CTkImage(light_mode=img, dark_mode=img, size=img.size)
                    lbl = ctk.CTkLabel(inner, image=ctk_img, text="", width=64, height=64)
                    lbl._img = ctk_img
                    lbl.pack(side="left", padx=(0, Spacing.MD))
                except Exception:
                    pass

            left = ctk.CTkFrame(inner, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(left, text=p["name"], font=Fonts.H2,
                         text_color=Colors.TEXT_PRIMARY).pack(side="left")
            ctk.CTkLabel(left, text=f"  ¥{p['price']:,.0f}", font=Fonts.H2,
                         text_color=Colors.PRIMARY).pack(side="left", padx=(Spacing.MD, 0))
            order_count = len(self.db.get_orders(product_id=p["id"]))
            ctk.CTkLabel(left, text=f"  {order_count} 笔订单",
                         font=Fonts.SMALL, text_color=Colors.TEXT_MUTED).pack(
                side="left", padx=(Spacing.SM, 0))

            btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
            btn_frame.pack(side="right")
            ctk.CTkButton(btn_frame, text="📋 订单", font=Fonts.SMALL, width=72, height=30,
                          fg_color=Colors.PRIMARY_LIGHT, hover_color=Colors.PRIMARY_DIM,
                          text_color=Colors.PRIMARY, corner_radius=Radius.MD,
                          command=lambda p=p: self._go_orders(p)).pack(side="left", padx=3)
            ctk.CTkButton(btn_frame, text="✏️", font=Fonts.SMALL, width=32, height=30,
                          fg_color=Colors.BG_INPUT, hover_color=Colors.PRIMARY_LIGHT,
                          text_color=Colors.TEXT_SECONDARY, corner_radius=Radius.MD,
                          command=lambda p=p: self._edit(p)).pack(side="left", padx=3)
            ctk.CTkButton(btn_frame, text="🗑", font=Fonts.SMALL, width=32, height=30,
                          fg_color=Colors.BG_INPUT, hover_color=Colors.DANGER_LIGHT,
                          text_color=Colors.TEXT_MUTED, corner_radius=Radius.MD,
                          command=lambda p=p: self._delete(p)).pack(side="left", padx=3)

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
            self.db.update_product(product["id"], name=data["name"], price=data["price"],
                                   notes=data["notes"], image_path=data["image_path"])
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
