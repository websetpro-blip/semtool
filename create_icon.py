"""
Создание зеленой иконки для SemTool
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Создаем иконку 256x256 (максимальный размер для .ico)
size = 256
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Зеленый круг (как основа)
circle_color = (76, 175, 80, 255)  # #4CAF50 - Material Green
border_color = (56, 142, 60, 255)  # Темнее для границы

# Рисуем круг с градиентом (визуально)
margin = 20
draw.ellipse([margin, margin, size-margin, size-margin], fill=circle_color, outline=border_color, width=8)

# Добавляем букву "S" в центр
try:
    # Пытаемся загрузить системный шрифт
    font_size = 160
    font = ImageFont.truetype("arial.ttf", font_size)
except:
    # Если не получилось, используем стандартный
    font = ImageFont.load_default()

# Текст "S" (SemTool)
text = "S"
text_bbox = draw.textbbox((0, 0), text, font=font)
text_width = text_bbox[2] - text_bbox[0]
text_height = text_bbox[3] - text_bbox[1]

text_x = (size - text_width) // 2 - 5
text_y = (size - text_height) // 2 - 10

# Тень для объемности
shadow_offset = 3
draw.text((text_x + shadow_offset, text_y + shadow_offset), text, fill=(0, 0, 0, 100), font=font)

# Основной текст (белый)
draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)

# Сохраняем в разных размерах для .ico
icon_path = os.path.join(os.path.dirname(__file__), "semtool_icon.ico")

# Создаем мультисайз иконку (256, 128, 64, 32, 16)
sizes = [256, 128, 64, 32, 16]
icons = []
for s in sizes:
    resized = img.resize((s, s), Image.Resampling.LANCZOS)
    icons.append(resized)

# Сохраняем как .ico
icons[0].save(icon_path, format='ICO', sizes=[(s, s) for s in sizes], append_images=icons[1:])

print(f"[OK] Иконка создана: {icon_path}")
print(f"[OK] Размеры: {', '.join(str(s) for s in sizes)}")

# Также сохраняем PNG для превью
png_path = os.path.join(os.path.dirname(__file__), "semtool_icon.png")
img.save(png_path, format='PNG')
print(f"[OK] PNG превью: {png_path}")
