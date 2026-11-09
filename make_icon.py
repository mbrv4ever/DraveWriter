# Maakt assets/icon.png + assets/icon.ico voor DraveWriter.
# Eigen ontwerp: een open receptenboek met een gouden lepel en een dampend kommetje.
# Copyright (C) 2026 Dravenlock (Roger & Claudio). GNU GPL v3.0. Pillow nodig.
import os
from PIL import Image, ImageDraw, ImageFilter

HIER = os.path.dirname(os.path.abspath(__file__))
N = 512
img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((16, 16, N - 16, N - 16), radius=100, fill=(22, 19, 31, 255), outline=(127, 119, 221, 255), width=12)
gl = Image.new("RGBA", (N, N), (0, 0, 0, 0))
ImageDraw.Draw(gl).ellipse((80, 120, 440, 460), fill=(127, 119, 221, 110))
img = Image.alpha_composite(img, gl.filter(ImageFilter.GaussianBlur(45)))
d = ImageDraw.Draw(img)
# open boek: kaft (paars) en twee bladzijden
d.polygon([(70, 200), (256, 236), (442, 200), (442, 420), (256, 456), (70, 420)], fill=(108, 95, 199, 255))
d.polygon([(86, 186), (250, 222), (250, 432), (86, 400)], fill=(244, 240, 253, 255), outline=(22, 19, 31, 255))
d.polygon([(262, 222), (426, 186), (426, 400), (262, 432)], fill=(255, 255, 255, 255), outline=(22, 19, 31, 255))
d.line([(256, 222), (256, 440)], fill=(22, 19, 31, 255), width=6)
# regels tekst links
for i in range(5):
    y = 250 + i * 30
    d.line([(108, y + i * 1), (226, y + 26 + i * 1)], fill=(181, 156, 255, 255), width=8)
# kommetje met damp rechts
d.chord((285, 270, 405, 380), 0, 180, fill=(255, 200, 87, 255), outline=(22, 19, 31, 255), width=6)
d.line([(280, 325), (410, 325)], fill=(22, 19, 31, 255), width=7)
for x in (318, 345, 372):
    d.arc((x - 14, 214, x + 14, 266), 100, 260, fill=(181, 156, 255, 255), width=7)
    d.arc((x - 14, 252, x + 14, 304), 280, 80, fill=(181, 156, 255, 255), width=7)
# gouden lepel die uit het kommetje steekt
d = ImageDraw.Draw(img)
d.line([(368, 318), (432, 236)], fill=(22, 19, 31, 255), width=22)
d.line([(368, 318), (432, 236)], fill=(255, 200, 87, 255), width=11)
d.ellipse((424, 222, 446, 244), fill=(255, 200, 87, 255), outline=(22, 19, 31, 255), width=5)
# kommetje opnieuw erover, zodat de lepel erin staat
d.chord((285, 270, 405, 380), 0, 180, fill=(255, 200, 87, 255), outline=(22, 19, 31, 255), width=6)
d.line([(280, 325), (410, 325)], fill=(22, 19, 31, 255), width=7)
os.makedirs(os.path.join(HIER, "assets"), exist_ok=True)
img.save(os.path.join(HIER, "assets", "icon.png"))
img.save(os.path.join(HIER, "assets", "icon.ico"), format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icoon klaar")
