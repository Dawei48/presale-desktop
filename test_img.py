import os, sys, customtkinter as ctk
from config import IMAGES_DIR

# 创建测试图片
from PIL import Image as PILImage
test_path = os.path.join(IMAGES_DIR, "test.png")
img = PILImage.new("RGB", (200, 200), color=(37, 99, 235))
img.save(test_path)
print(f"Test image saved: {test_path}")

root = ctk.CTk()
root.geometry("300x300")

# 方法1: CTkImage
try:
    from customtkinter import CTkImage
    pil = PILImage.open(test_path)
    pil.thumbnail((100, 100))
    ctk_img = CTkImage(light_image=pil, dark_image=pil, size=pil.size)
    lbl = ctk.CTkLabel(root, text="", image=ctk_img, width=100, height=100)
    lbl._img = ctk_img
    lbl._pil = pil
    lbl.pack(pady=10)
    print("CTkImage: OK")
except Exception as e:
    print(f"CTkImage FAILED: {e}")

# 方法2: ImageTk.PhotoImage
try:
    from PIL import ImageTk
    pil2 = PILImage.open(test_path)
    pil2.thumbnail((100, 100))
    photo = ImageTk.PhotoImage(pil2)
    lbl2 = ctk.CTkLabel(root, text="", width=100, height=100)
    lbl2.pack(pady=10)
    # CTkLabel用image参数不行的话试configure
    lbl2.configure(image=photo)
    lbl2._photo = photo
    lbl2._pil2 = pil2
    print("ImageTk: OK")
except Exception as e:
    print(f"ImageTk FAILED: {e}")

root.after(3000, root.destroy)
root.mainloop()
print("DONE")
