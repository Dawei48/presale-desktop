"""
CSV订单导入 - 支持淘宝/拼多多/抖音等平台导出的订单文件
自动识别列名，预览后批量导入
"""
import csv
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from ui.styles import Colors, Fonts, Spacing, Radius
from config import ai_enabled, DEEPSEEK_API_KEY, PLATFORM_SHIP_DAYS, SHIP_DEADLINE_DAYS
from utils.ai_parser import parse_headers_with_ai, merge_mapping


# ── 各平台常见列名映射 ──
FIELD_MAP = {
    "order_no": {
        "patterns": ["订单号", "订单编号", "order_no", "order_id", "订单ID", "交易号"],
        "fallback": None,
    },
    "customer": {
        "patterns": ["收货人", "买家", "客户名称", "买家昵称", "收件人", "客户", "customer", "buyer", "name"],
        "fallback": "买家昵称",
    },
    "product": {
        "patterns": ["商品名称", "宝贝标题", "商品", "产品名称", "title", "product", "product_name", "item"],
        "fallback": "商品名称",
    },
    "quantity": {
        "patterns": ["数量", "件数", "qty", "quantity", "购买数量", "num"],
        "fallback": None,
    },
    "created_at": {
        "patterns": ["下单时间", "付款时间", "成交时间", "创建时间", "日期", "date", "time", "created"],
        "fallback": None,
    },
    "notes": {
        "patterns": ["备注", "买家留言", "留言", "remark", "note", "memo"],
        "fallback": "备注",
    },
}

PLATFORM_HINTS = {
    "taobao": {"收货人", "宝贝标题", "订单编号", "买家昵称", "成交时间"},
    "pdd": {"收件人", "商品名称", "订单号", "购买数量"},
    "douyin": {"收件人", "商品标题", "订单ID", "用户昵称", "下单时间"},
}


def detect_platform(headers):
    """检测数据来源平台"""
    header_set = {h.strip() for h in headers}
    scores = {}
    for platform, keywords in PLATFORM_HINTS.items():
        score = len(keywords & header_set)
        if score > 0:
            scores[platform] = score
    return max(scores, key=scores.get) if scores else "unknown"


def match_field(headers, field_name):
    """根据规则匹配列名"""
    config = FIELD_MAP[field_name]
    for h in headers:
        h_clean = h.strip().lower()
        # 精确匹配
        if h_clean in [p.lower() for p in config["patterns"]]:
            return h
        # 模糊匹配
        for pattern in config["patterns"]:
            if pattern.lower() in h_clean or h_clean in pattern.lower():
                return h
    return None


def parse_csv(filepath):
    """解析CSV文件，返回 (headers, rows, platform)"""
    rows = []
    headers = []

    # 尝试多种编码
    for encoding in ["utf-8-sig", "utf-8", "gbk", "gb2312", "gb18030"]:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                reader = csv.reader(f)
                headers = next(reader)
                # 清理BOM
                if headers and headers[0].startswith('\ufeff'):
                    headers[0] = headers[0][1:]
                # 跳过空行和汇总行
                for row in reader:
                    if row and any(cell.strip() for cell in row):
                        # 过滤掉"合计"等汇总行
                        first_cell = row[0].strip() if row else ""
                        if any(kw in first_cell for kw in ["合计", "总计", "共", "备注："]):
                            continue
                        rows.append(row)
                break
        except (UnicodeDecodeError, StopIteration):
            continue
        except Exception:
            continue

    platform = detect_platform(headers) if headers else "unknown"
    return headers, rows, platform


class CSVImportDialog(ctk.CTkToplevel):
    """CSV导入预览对话框"""

    def __init__(self, parent, db, current_user, product=None, brand=None, on_done=None):
        super().__init__(parent)
        self.title("📥 导入CSV订单")
        self.geometry("800x600")
        self.resizable(True, True)
        self.minsize(700, 500)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=Colors.BG_CARD)

        self.db = db
        self.current_user = current_user
        self.target_product = product
        self.target_brand = brand
        self.on_done = on_done

        self.headers = []
        self.rows = []
        self.platform = ""
        self.mapping = {}  # 列名 → 字段名
        self.skip_rows = set()

        self._build()
        self._center(parent)

        # 自动打开文件选择
        self._select_file()

    def _center(self, parent):
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        w, h = 800, 600
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{max(x,0)}+{max(y,0)}")

    def _build(self):
        # 顶部操作区
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=Spacing.XL, pady=(Spacing.XL, Spacing.MD))

        self.file_label = ctk.CTkLabel(top, text="未选择文件", font=Fonts.BODY,
                                       text_color=Colors.TEXT_MUTED)
        self.file_label.pack(side="left")

        ctk.CTkButton(top, text="📂 选择文件", font=Fonts.BODY, height=34,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      corner_radius=Radius.SM, command=self._select_file).pack(side="right")

        # 映射配置区
        self.map_frame = ctk.CTkFrame(self, fg_color=Colors.BG_INPUT, corner_radius=Radius.MD)
        self.map_frame.pack(fill="x", padx=Spacing.XL, pady=(0, Spacing.MD))

        # 预览区
        self.preview_frame = ctk.CTkScrollableFrame(self, fg_color="transparent",
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED)
        self.preview_frame.pack(fill="both", expand=True, padx=Spacing.XL)

        # 底部按钮
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)

        self.count_label = ctk.CTkLabel(bottom, text="", font=Fonts.SMALL,
                                        text_color=Colors.TEXT_MUTED)
        self.count_label.pack(side="left")

        ctk.CTkButton(bottom, text="取消", font=Fonts.BODY, height=34,
                      fg_color=Colors.BG_INPUT, hover_color=Colors.BORDER,
                      text_color=Colors.TEXT_SECONDARY, corner_radius=Radius.SM,
                      command=self.destroy).pack(side="right", padx=(Spacing.SM, 0))
        ctk.CTkButton(bottom, text="✅ 导入", font=Fonts.BODY_B, height=34,
                      fg_color=Colors.SUCCESS, hover_color="#059669",
                      corner_radius=Radius.SM,
                      command=self._do_import).pack(side="right")

    def _select_file(self):
        filepath = filedialog.askopenfilename(
            parent=self,
            title="选择订单CSV文件",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if not filepath:
            return

        self.headers, self.rows, self.platform = parse_csv(filepath)
        if not self.headers or not self.rows:
            messagebox.showwarning("解析失败", "无法读取CSV文件，请确认文件格式正确。", parent=self)
            return

        self.file_label.configure(
            text=f"📄 {filepath.split('/')[-1]}  ({len(self.rows)}条记录, 来源: {self.platform})"
        )

        # 自动匹配列名
        self._auto_map()
        self._build_map_ui()
        # AI 显性化：规则匹配有漏的字段时，提示用户用 AI 识别
        if ai_enabled():
            unmatched = [f for f in FIELD_MAP if f not in self.mapping]
            if unmatched:
                self.ai_btn.configure(text=f"🤖 AI 识别 {len(unmatched)} 个未识别字段")
        self._build_preview()
        self.count_label.configure(text=f"共 {len(self.rows)} 条订单，0 条跳过")

    def _auto_map(self):
        """自动匹配列名映射"""
        self.mapping = {}
        for field in FIELD_MAP:
            matched = match_field(self.headers, field)
            if matched:
                self.mapping[field] = matched

    def _build_map_ui(self):
        for w in self.map_frame.winfo_children():
            w.destroy()

        # 顶部：标题 + AI 识别按钮
        top_row = ctk.CTkFrame(self.map_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=Spacing.MD, pady=(Spacing.MD, Spacing.SM))
        ctk.CTkLabel(top_row, text="列名映射（可手动调整）：",
                     font=Fonts.SMALL_B, text_color=Colors.TEXT_SECONDARY).pack(side="left")
        self.ai_btn = ctk.CTkButton(top_row, text="🤖 AI 智能识别", font=Fonts.SMALL_B, height=28,
                                    fg_color=Colors.PRIMARY_LIGHT, hover_color=Colors.PRIMARY_DIM,
                                    text_color=Colors.PRIMARY, corner_radius=Radius.SM,
                                    command=self._ai_map).pack(side="right")
        if not ai_enabled():
            self.ai_btn.configure(state="disabled", text="🤖 AI 未配置")

        grid = ctk.CTkFrame(self.map_frame, fg_color="transparent")
        grid.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.MD))

        fields = [
            ("order_no", "订单号 *"),
            ("customer", "客户名 *"),
            ("product", "产品名"),
            ("quantity", "数量"),
            ("created_at", "下单时间"),
            ("notes", "备注"),
        ]

        row_idx = 0
        for field, label in fields:
            ctk.CTkLabel(grid, text=label, font=Fonts.SMALL,
                         text_color=Colors.TEXT_PRIMARY, width=100, anchor="e").grid(
                row=row_idx, column=0, padx=(0, Spacing.SM), pady=2, sticky="e")

            options = ["（不映射）"] + self.headers
            current = self.mapping.get(field, "（不映射）")
            combo = ctk.CTkComboBox(grid, values=options, font=Fonts.SMALL, width=200, height=30,
                                    corner_radius=Radius.SM,
                                    border_color=Colors.BORDER,
                                    fg_color=Colors.BG_MAIN,
                                    button_color=Colors.PRIMARY)
            combo.set(current)
            combo.grid(row=row_idx, column=1, pady=2, sticky="w")

            # 绑定变量
            setattr(self, f"_combo_{field}", combo)
            row_idx += 1

    def _ai_map(self):
        """调用 AI 识别列名，补充规则匹配没识别出的字段"""
        if not ai_enabled():
            messagebox.showwarning("AI 未配置", "未找到 AI key，无法使用 AI 识别。", parent=self)
            return
        if not self.headers:
            return

        self.ai_btn.configure(text="🤖 AI 识别中...", state="disabled")
        self.update_idletasks()
        try:
            ai_mapping = parse_headers_with_ai(self.headers, DEEPSEEK_API_KEY)
        except Exception:
            ai_mapping = {}
        finally:
            if ai_enabled():
                self.ai_btn.configure(text="🤖 AI 智能识别", state="normal")

        if not ai_mapping:
            messagebox.showwarning("AI 识别失败",
                                   "AI 未能识别出新的列名映射，可能是网络问题或 key 无效。\n已保留规则匹配结果。",
                                   parent=self)
            return

        # 合并到规则匹配结果（规则优先，AI 补充）
        self.mapping = merge_mapping(self.mapping, ai_mapping)
        self._build_map_ui()
        self._build_preview()
        self.count_label.configure(text=f"🤖 AI 补充识别了 {len(ai_mapping)} 个字段")

    def _build_preview(self):
        for w in self.preview_frame.winfo_children():
            w.destroy()

        if not self.rows:
            return

        # 表头
        hdr = ctk.CTkFrame(self.preview_frame, fg_color=Colors.SIDEBAR_BG,
                           corner_radius=Radius.MD, height=34)
        hdr.pack(fill="x", pady=(0, 2))
        hdr.pack_propagate(False)

        preview_fields = ["订单号", "客户", "产品", "数量", "时间", "备注"]
        widths = [140, 80, 160, 50, 130, 80]
        for i, (f, w) in enumerate(zip(preview_fields, widths)):
            ctk.CTkLabel(hdr, text=f, font=Fonts.SMALL_B, text_color="white",
                         width=w, anchor="w").grid(row=0, column=i, sticky="w",
                                                    padx=Spacing.SM, pady=4)

        # 数据行（最多显示50行）
        for idx, row in enumerate(self.rows[:50]):
            bg = Colors.BG_INPUT if idx % 2 == 0 else "transparent"
            r = ctk.CTkFrame(self.preview_frame, fg_color=bg, corner_radius=Radius.SM, height=32)
            r.pack(fill="x", pady=1)
            r.pack_propagate(False)

            vals = self._extract_row(row)
            for col, (f, w) in enumerate(zip(preview_fields, widths)):
                txt = vals.get(f, "") or ""
                if len(txt) > 20:
                    txt = txt[:18] + ".."
                ctk.CTkLabel(r, text=str(txt), font=Fonts.TINY,
                             text_color=Colors.TEXT_PRIMARY,
                             width=w, anchor="w").grid(row=0, column=col, sticky="w",
                                                        padx=Spacing.SM, pady=4)

        if len(self.rows) > 50:
            ctk.CTkLabel(self.preview_frame,
                         text=f"... 还有 {len(self.rows) - 50} 条未显示",
                         font=Fonts.TINY, text_color=Colors.TEXT_MUTED).pack(pady=Spacing.SM)

    def _get_current_mapping(self):
        """获取当前用户设置的映射"""
        mapping = {}
        fields = ["order_no", "customer", "product", "quantity", "created_at", "notes"]
        for field in fields:
            combo = getattr(self, f"_combo_{field}", None)
            if combo:
                val = combo.get()
                if val and val != "（不映射）":
                    mapping[field] = val
        return mapping

    def _extract_row(self, row):
        """根据映射从行数据提取字段"""
        mapping = self._get_current_mapping()
        result = {}
        for field, col_name in mapping.items():
            try:
                col_idx = self.headers.index(col_name)
                result[field] = row[col_idx].strip() if col_idx < len(row) else ""
            except (ValueError, IndexError):
                result[field] = ""
        # 映射预览显示的字段名
        vals = {
            "订单号": result.get("order_no", ""),
            "客户": result.get("customer", ""),
            "产品": result.get("product", ""),
            "数量": result.get("quantity", "1"),
            "时间": result.get("created_at", ""),
            "备注": result.get("notes", ""),
        }
        return vals

    def _ensure_default_product(self):
        """确保存在「未分类」产品，返回其 id（从全部订单页导入时兜底）"""
        brands = self.db.get_brands()
        brand = next((b for b in brands if b.get("name") == "未分类"), None)
        brand_id = self.db.add_brand("未分类") if not brand else brand["id"]
        products = self.db.get_products(brand_id)
        product = next((p for p in products if p.get("name") == "未分类"), None)
        return self.db.add_product(brand_id, "未分类") if not product else product["id"]

    def _do_import(self):
        mapping = self._get_current_mapping()
        if "order_no" not in mapping or "customer" not in mapping:
            messagebox.showwarning("缺少必填字段",
                                   "请至少映射「订单号」和「客户名」后再导入。", parent=self)
            return

        success_count = 0
        skip_count = 0
        dup_count = 0
        errors = []

        for idx, row in enumerate(self.rows):
            try:
                data = {}
                for field, col_name in mapping.items():
                    col_idx = self.headers.index(col_name)
                    val = row[col_idx].strip() if col_idx < len(row) else ""
                    data[field] = val

                # 必填项检查
                if not data.get("order_no") or not data.get("customer"):
                    skip_count += 1
                    continue

                # 数量处理
                try:
                    qty = int(data.get("quantity", 1))
                except (ValueError, TypeError):
                    qty = 1

                # 日期处理
                created_at = data.get("created_at", "")
                if not created_at:
                    from datetime import datetime
                    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # 产品上下文：优先当前产品，否则归「未分类」
                product_id = (self.target_product["id"] if self.target_product
                              else self._ensure_default_product())

                # 发货期限：按平台默认（抖音2天/淘宝3天/未知30天）
                ship_days = PLATFORM_SHIP_DAYS.get(self.platform, SHIP_DEADLINE_DAYS)

                # 插入订单（product_name 由 product_id 关联获取，status 默认 pending）
                order_data = {
                    "order_no": data.get("order_no", ""),
                    "customer": data.get("customer", ""),
                    "quantity": qty,
                    "notes": data.get("notes", ""),
                    "created_at": created_at,
                    "ship_days": ship_days,
                }

                # 查重：订单号已存在则跳过（保留你手动更新的发货状态）
                if self.db.get_order_by_no(order_data["order_no"]):
                    dup_count += 1
                    continue

                self.db.add_order(product_id, **order_data)
                success_count += 1

            except Exception as e:
                errors.append(f"第{idx+1}行: {e}")
                skip_count += 1

        # 记录操作日志
        log_msg = f"导入 {success_count} 条订单"
        if skip_count:
            log_msg += f"，跳过 {skip_count} 条"
        self.db.log("CSV导入", log_msg,
                    self.current_user["id"], self.current_user["username"])

        # 结果提示
        msg = f"✅ 成功导入 {success_count} 条订单"
        if dup_count:
            msg += f"\n🔁 跳过 {dup_count} 条重复订单"
        if skip_count:
            msg += f"\n⏭️ 跳过 {skip_count} 条无效记录"
        if errors:
            msg += f"\n\n⚠️ 错误详情（前5条）:\n" + "\n".join(errors[:5])

        messagebox.showinfo("导入完成", msg, parent=self)

        self.destroy()
        if self.on_done:
            self.on_done()


def open_csv_import(parent, db, current_user, product=None, brand=None, on_done=None):
    """打开CSV导入对话框"""
    CSVImportDialog(parent, db, current_user, product=product, brand=brand, on_done=on_done)
