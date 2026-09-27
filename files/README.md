# Oilaviy arxiv — loyiha fayllari

## Tayyor sayt
- **family-archive.html** — butun sayt bitta faylda. Ikki marta bosib brauzerda ochish mumkin.
  Onlayn nusxasi: https://claude.ai/artifact/Hue6DdTfe7X1cUBeUaT7FC

## Ma'lumotlar bazasi
- **family-archive-schema.sql** — kelajakdagi server uchun to'liq jadval tuzilmasi (barcha 5 bosqich uchun).

## Manba kodi (shu papkaning o'zida)
| Fayl | Vazifasi |
|---|---|
| style.css | Dizayn va ranglar (yorug' va qorong'i rejim) |
| i18n.js | Til tizimi: tarjima, o'zbekcha sanalar va qarindoshlik nomlari |
| uz.js | O'zbekcha lug'at va namuna oila matnlari |
| core.js | Ma'lumotlar modeli, noaniq sanalar, saqlash, ziddiyatlarni aniqlash |
| demo.js | To'qima namuna oila (Nurmatovlar) |
| tree.js | Oila daraxtini joylashtirish, chizish, SVG/PNG eksport |
| views.js | Sahifalar: bosh sahifa, odamlar, profil, manbalar, sozlamalar |
| search.js | Qidiruv (lotin/kirill, xatoga chidamli) va "Nimalarni aniqlash kerak" |
| accounts.js | Hisoblar, parol, kirish sahifasi |
| forms.js | Formalar, import/eksport, ishga tushirish |
| build.sh | Hammasini bitta family-archive.html fayliga yig'adi |

Qayta yig'ish: shu papkada `bash build.sh` (Linux/macOS).

## Holati
1-bosqich + o'zbek tili, qidiruv va hisoblar tayyor.
Keyingi: 2-bosqich (xronologiya, hikoyalar, suratlar, hujjatlar, joylar) yoki haqiqiy server.
