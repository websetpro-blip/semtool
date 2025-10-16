# Direct fix without writing mojibake in script
import re

filename = 'app/accounts_tab_extended.py'

with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []
count = 0

for i, line in enumerate(lines):
    original = line
    
    # Replace specific patterns by line content detection
    # Line ~73
    if 'profile_path' in line and line.strip().startswith('#') and 'CHECK' not in line:
        line = '        # ПРОВЕРКА: Профиль ДОЛЖЕН быть из БД!\n'
        count += 1
    # Line ~75
    elif '[ERROR]' in line and 'profile_path' in line and 'account.name' in line and 'НЕТ' not in line:
        line = '            self.status_signal.emit(f"[ERROR] У аккаунта {self.account.name} НЕТ profile_path в БД!")\n'
        count += 1
    # Line ~76
    elif 'finished_signal.emit(False' in line and 'profile' in line.lower() and 'не указан' not in line:
        line = '            self.finished_signal.emit(False, "Профиль не указан в БД")\n'
        count += 1
    # Line ~79
    elif '[OK]' in line and 'profile' in line.lower() and 'из БД' not in line:
        line = '        self.status_signal.emit(f"[OK] Профиль из БД: {profile_path}")\n'
        count += 1
    # Line ~83
    elif '[INFO]' in line and 'profile_path' in line and 'преобразован' not in line:
        line = '            self.status_signal.emit(f"[INFO] Путь преобразован: {profile_path}")\n'
        count += 1
    # Line ~104
    elif '[CDP]' in line and 'account.name' in line and '...' in line and 'Запуск' not in line:
        line = '        self.status_signal.emit(f"[CDP] Запуск автологина для {self.account.name}...")\n'
        count += 1
    # Line ~108
    elif '[CDP]' in line and 'secret' in line.lower() and 'Найден' not in line:
        line = '            self.status_signal.emit(f"[CDP] Найден сохраненный ответ на секретный вопрос")\n'
        count += 1
    # Line ~111
    elif '[CDP]' in line and 'port' in line and 'account.name' in line and 'Используется' not in line:
        line = '        self.status_signal.emit(f"[CDP] Используется порт {port} для {self.account.name}")\n'
        count += 1
    # Line ~121
    elif '[INFO]' in line and 'proxy' in line and '@' in line and 'Используется' not in line:
        line = '            self.status_signal.emit(f"[INFO] Используется прокси: {proxy_to_use.split' + "('@')[0]}@***\")\n"
        count += 1
    # Line ~123
    elif '[SMART]' in line and 'autologin' in line.lower() and 'Запускаю' not in line:
        line = '        self.status_signal.emit(f"[SMART] Запускаю автологин...")\n'
        count += 1
    
    fixed_lines.append(line)

# Write back
with open(filename, 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print(f"[DONE] Fixed {count} lines with mojibake!")
print(f"[FILE] {filename}")
