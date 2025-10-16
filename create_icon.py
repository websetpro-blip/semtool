from PIL import Image, ImageDraw, ImageFont
import os

"""Generate KeySet icon (green circle with letter K)."""
SIZE = 256
BACKGROUND = (0, 0, 0, 0)
FILL = (76, 175, 80, 255)
BORDER = (56, 142, 60, 255)
SHADOW_COLOR = (0, 0, 0, 120)
MARGIN = 20
TEXT = 'K'
FONT_SIZE = 160
ICON_PATH = os.path.join(os.path.dirname(__file__), 'keyset_icon.ico')
PNG_PATH = os.path.join(os.path.dirname(__file__), 'keyset_icon.png')

img = Image.new('RGBA', (SIZE, SIZE), BACKGROUND)
draw = ImageDraw.Draw(img)

draw.ellipse([MARGIN, MARGIN, SIZE - MARGIN, SIZE - MARGIN], fill=FILL, outline=BORDER, width=8)

try:
    font = ImageFont.truetype('arial.ttf', FONT_SIZE)
except OSError:
    font = ImageFont.load_default()

bbox = draw.textbbox((0, 0), TEXT, font=font)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]
text_x = (SIZE - text_w) // 2
text_y = (SIZE - text_h) // 2 - 10

draw.text((text_x + 4, text_y + 4), TEXT, fill=SHADOW_COLOR, font=font)
draw.text((text_x, text_y), TEXT, fill=(255, 255, 255, 255), font=font)

sizes = [256, 128, 64, 32, 16]
icons = [img.resize((s, s), Image.Resampling.LANCZOS) for s in sizes]
icons[0].save(ICON_PATH, format='ICO', sizes=[(s, s) for s in sizes], append_images=icons[1:])
img.save(PNG_PATH, format='PNG')

print(f'[OK] Icon generated: {ICON_PATH}')
print(f'[OK] PNG preview: {PNG_PATH}')
