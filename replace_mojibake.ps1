# Replace all mojibake with English text
$file = "app\accounts_tab_extended.py"
$content = Get-Content $file -Raw -Encoding UTF8

# Replace all mojibake patterns with English
$replacements = @{
    "Р—Р°РїСѓСЃРє СѓРјРЅРѕРіРѕ Р°РІС‚РѕР»РѕРіРёРЅР° РЅР° РѕСЃРЅРѕРІРµ СЂРµС€РµРЅРёСЏ GPT" = "Start smart autologin based on GPT solution"
    "вљ пёЏ РџР РћР'Р•Р РљРђ: РџСЂРѕС„РёР»СЊ Р"РћР›Р¶РµРќ Р±С‹С‚СЊ РёР· Р'Р"!" = "# CHECK: Profile MUST be from DB!"
    "РЈ Р°РєРєР°СѓРЅС‚Р°" = "Account"
    "РќР•Рў profile_path РІ Р'Р"!" = "has NO profile_path in DB!"
    "РџСЂРѕС„РёР»СЊ РЅРµ СѓРєР°Р·Р°РЅ РІ Р'Р"" = "Profile not specified in DB"
    "РџСЂРѕС„РёР»СЊ РёР· Р'Р]" = "Profile from DB]"
    "РџСѓС‚СЊ РїСЂРµРѕР±СЂР°Р·РѕРІР°РЅ" = "Path converted"
    "Р¤Р°Р№Р» accounts.json РЅРµ РЅР°Р№РґРµРЅ!" = "File accounts.json not found!"
    "Р¤Р°Р№Р» accounts.json РЅРµ РЅР°Р№РґРµРЅ" = "File accounts.json not found"
    "РђРєРєР°СѓРЅС‚" = "Account"
    "РЅРµ РЅР°Р№РґРµРЅ РІ accounts.json!" = "not found in accounts.json!"
    "РЅРµ РЅР°Р№РґРµРЅ РІ accounts.json" = "not found in accounts.json"
    "Р—Р°РїСѓСЃРє Р°РІС‚РѕР»РѕРіРёРЅР° РґР»СЏ" = "Starting autologin for"
    "РќР°Р№РґРµРЅ СЃРѕС…СЂР°РЅРµРЅРЅС‹Р№ РѕС‚РІРµС‚ РЅР° СЃРµРєСЂРµС‚РЅС‹Р№ РІРѕРїСЂРѕСЃ" = "Found saved secret question answer"
    "РСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РїРѕСЂС‚" = "Using port"
    "РґР»СЏ" = "for"
    "РСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РїСЂРѕРєСЃРё" = "Using proxy"
    "Р—Р°РїСѓСЃРєР°СЋ Р°РІС‚РѕР»РѕРіРёРЅ..." = "Starting autologin..."
    "РђРІС‚РѕР»РѕРіРёРЅ СѓСЃРїРµС€РµРЅ РґР»СЏ" = "Autologin successful for"
    "РђРІС‚РѕСЂРёР·Р°С†РёСЏ СѓСЃРїРµС€РЅР°" = "Authorization successful"
    "РђРІС‚РѕР»РѕРіРёРЅ РЅРµ СѓРґР°Р»СЃСЏ РґР»СЏ" = "Autologin failed for"
    "РћС€РёР±РєР° Р°РІС‚РѕСЂРёР·Р°С†РёРё" = "Authorization error"
}

$count = 0
foreach ($key in $replacements.Keys) {
    if ($content -match [regex]::Escape($key)) {
        $content = $content -replace [regex]::Escape($key), $replacements[$key]
        $count++
        Write-Host "[OK] Replaced: $($key.Substring(0, [Math]::Min(30, $key.Length)))..."
    }
}

# Save file
$content | Set-Content $file -Encoding UTF8 -NoNewline

Write-Host ""
Write-Host "[DONE] Replaced $count mojibake patterns!"
Write-Host "[FILE] $file"
