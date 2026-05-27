"""
图片工具 - 印章风格边框
"""
from PIL import Image, ImageDraw


SEAL_RED = "#C0392B"  # 朱砂红


def add_seal_border(pil_img, border_width=2, border_color=SEAL_RED):
    """给图片加朱砂红边框，返回新 PIL Image"""
    w, h = pil_img.size
    bw = border_width
    new_w = w + bw * 2
    new_h = h + bw * 2
    canvas = Image.new("RGB", (new_w, new_h), "white")
    canvas.paste(pil_img, (bw, bw))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, new_w - 1, new_h - 1], outline=border_color, width=bw)
    return canvas


def load_logo(path, size=(80, 80)):
    """加载 logo 返回 CTkImage"""
    try:
        from customtkinter import CTkImage
        img = Image.open(path)
        img.thumbnail(size)
        return CTkImage(light_image=img, dark_image=img, size=img.size)
    except Exception:
        return None
