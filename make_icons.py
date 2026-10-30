"""icon.png から PWA 用アイコンを生成するスクリプト（パソコンで1回だけ実行）

使い方:
    pip install pillow
    python make_icons.py
→ static/ フォルダに icon-192.png / icon-512.png / apple-touch-icon.png が作られます。
"""
from pathlib import Path
from PIL import Image

base = Path(__file__).parent
out = base / "static"
out.mkdir(exist_ok=True)

src = Image.open(base / "icon.png").convert("RGBA")

# 正方形に整える（余白は白で埋める）
side = max(src.size)
square = Image.new("RGBA", (side, side), (255, 255, 255, 255))
square.paste(src, ((side - src.width) // 2, (side - src.height) // 2), src)

for name, size in [("icon-192.png", 192), ("icon-512.png", 512), ("apple-touch-icon.png", 180)]:
    img = square.resize((size, size), Image.LANCZOS).convert("RGB")  # 透過なし
    img.save(out / name)
    print("作成:", out / name)
