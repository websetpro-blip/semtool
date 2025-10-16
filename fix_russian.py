# -*- coding: utf-8 -*-
"""Fix mojibake - replace with correct Russian"""

def fix_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Replacements dictionary - mojibake -> correct Russian
    fixes = [
        ('вљ пёЏ РџР РћР'Р•Р РљРђ: РџСЂРѕС„РёР»СЊ Р"РћР›Р¶РµРќ Р±С‹С‚СЊ РёР· Р'Р"!', 'ПРОВЕРКА: Профиль ДОЛЖЕН быть из БД!'),
        ('РЈ Р°РєРєР°СѓРЅС‚Р°', 'У аккаунта'),
        ('РќР•Рў profile_path РІ Р'Р"!', 'НЕТ profile_path в БД!'),
        ('РџСЂРѕС„РёР»СЊ РЅРµ СѓРєР°Р·Р°РЅ РІ Р'Р"', 'Профиль не указан в БД'),
        ('РџСЂРѕС„РёР»СЊ РёР· Р'Р]', 'Профиль из БД]'),
        ('РџСѓС‚СЊ РїСЂРµРѕР±СЂР°Р·РѕРІР°РЅ', 'Путь преобразован'),
        ('Р—Р°РїСѓСЃРє Р°РІС‚РѕР»РѕРіРёРЅР° РґР»СЏ', 'Запуск автологина для'),
        ('РќР°Р№РґРµРЅ СЃРѕС…СЂР°РЅРµРЅРЅС‹Р№ РѕС‚РІРµС‚ РЅР° СЃРµРєСЂРµС‚РЅС‹Р№ РІРѕРїСЂРѕСЃ', 'Найден сохраненный ответ на секретный вопрос'),
        ('РСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РїРѕСЂС‚', 'Используется порт'),
        ('РґР»СЏ', 'для'),
        ('РСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РїСЂРѕРєСЃРё', 'Используется прокси'),
        ('Р—Р°РїСѓСЃРєР°СЋ Р°РІС‚РѕР»РѕРіРёРЅ', 'Запускаю автологин'),
    ]
    
    count = 0
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            count += 1
            print(f"[OK] Fixed: {old[:30]}... -> {new[:30]}...")
    
    if content != original:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n[DONE] Fixed {count} mojibake patterns in {filename}")
        return True
    else:
        print(f"[INFO] No mojibake found in {filename}")
        return False

if __name__ == '__main__':
    fix_file('app/accounts_tab_extended.py')
