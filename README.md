# Shajara — oʻzbek oilalari uchun oilaviy arxiv (Django)

Asosiy til — **Oʻzbekcha (lotin)**, ikkinchi til — **Кириллча (oʻzbek kirill)**.
Ikkalasi ham Django’ning rasmiy i18n tizimi orqali ishlaydi (`gettext`, `.po` → `.mo`,
`LocaleMiddleware`, `JavaScriptCatalog`). Ingliz tili interfeysda yoʻq.

> Oldingi bir faylli prototip `files/` papkasida qoldirilgan. Qarindoshlik mantigʻi
> va lotin↔kirill qidiruvi oʻsha yerdan Pythonga koʻchirildi.

## Imkoniyatlar

- **Shajara daraxti** — bitta bogʻlangan chizma: ota va onaning oilalari yonma-yon, ajdodlarning aka-uka,
  opa-singillari «+ / −» bilan ochiladi va yopiladi; PNG va PDF eksport.
- **Qarindoshlik nomlari** avtomatik: aka/uka, opa/singil, amaki/amma/togʻa/xola, amakivachcha…,
  kelin/kuyov, qaynota/qaynona, yanga/pochcha, «Buvining ukasi», «Onaning xolavachchasi», «Togʻaning xotini».
- **Muchal** — har bir odamning muchali (yil Navroʻzda almashadi), keyingi muchal yili, Navroʻzda eslatma.
- **Oilaviy voqealar** — toʻy, fotiha, farzand kutilmoqda, tugʻilish, beshik toʻyi, sunnat toʻyi, yil oshi
  va boshqalar; oila xronikasi; kelajakdagi sanalar.
- **Doʻstlar** — istalgan kishining (oʻzingiz, dadangiz, buvingiz…) doʻstlari, tugʻilgan kunlari bilan.
- **Eslatmalar** — tugʻilgan kunlar, nikoh yilliklari, xotira kunlari, voqealar, muchal yili; saytdagi
  qoʻngʻiroqcha va **Telegram bot** orqali; har bir foydalanuvchi oʻzi yoqadi/oʻchiradi.
- **Kim kimga kim?** — ikki odam orasidagi qarindoshlik va bogʻlanish zanjiri.
- **Familiya taklifi** — oʻgʻil nevaraga ota tarafdagi bobosining ismidan (Madaminjon → Madaminov).
- **Eksport** — PDF (tarjimai hol, daraxt, shajara kitobi) va GEDCOM (boshqa shajara dasturlari uchun).
- **Yorugʻ / qorongʻi mavzu** va toʻrtta rang palitrasi, telefon ekraniga moslashgan dizayn, ikki yozuv (lotin va kirill).
- **Google orqali kirish**, **Boshqaruv paneli** (`/boshqaruv/`) va toʻliq zaxira nusxa.
- **Mac ilovasi** — [macos/](macos/README.md): alohida oyna, tizim bildirishnomalari, Dock belgisi.

Sayt: **https://shajara-liard.vercel.app** · Serverga joylash va koʻchirish: [DEPLOY.md](DEPLOY.md).

## Ishga tushirish

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py compilemessages --ignore=.venv
.venv/bin/python manage.py seed_demo        # namuna oila (ixtiyoriy)
.venv/bin/python manage.py runserver
.venv/bin/python manage.py run_worker      # eslatmalar va Telegram (alohida oynada, ixtiyoriy)
```

`seed_demo` uchta sinov foydalanuvchisini yaratadi: `namuna` (lotin), `dilnoza_a` (kirill, doʻst)
va `anvar_y` (kutilayotgan doʻstlik soʻrovi). Parol `apps/genealogy/management/commands/seed_demo.py` faylida
yozilgan va faqat lokal ishlab chiqish uchun moʻljallangan.

PostgreSQL uchun `DATABASE_URL=postgres://…` oʻzgaruvchisini bering (qarang: `.env.example`).
Oʻzgaruvchi berilmasa, SQLite ishlatiladi. Rasmlar ham bazada saqlanadi (`apps/core/storage.py`),
shuning uchun bazaning zaxira nusxasi hamma narsani oʻz ichiga oladi.

## Tuzilma

| Joy | Vazifasi |
|---|---|
| `config/settings.py` | `LANGUAGE_CODE="uz"`, `LANGUAGES` (`uz`, `uz-cyrl`), `LOCALE_PATHS`, middleware |
| `config/formats/uz`, `config/formats/uz_Cyrl` | Django sana/son formatlari |
| `apps/core/languages.py` | Tillar va ularning oʻz yozuvidagi nomlari (Oʻzbekcha / Кириллча) |
| `apps/core/middleware.py` | Tizimga kirgan foydalanuvchiga akkauntida saqlangan tilni yoqadi |
| `apps/core/dates.py` | Sanalar: *27-sentabr 2026-yil* / *2026 йил 27 сентябрь*; qisman sanalar ham |
| `apps/core/text.py` | Apostroflarni bir xil koʻrinishga keltirish va lotin/kirill qidiruv kaliti |
| `apps/core/django_messages.py` | Django’ning oʻz xabarlari (validatsiya, parol) — qayta tarjima uchun |
| `apps/genealogy/terminology.py` | **Qarindoshlik atamalari lugʻati** (yagona manba) |
| `apps/genealogy/kinship.py` | Aka/uka, opa/singil, amaki/amma/togʻa/xola, kelin/kuyov… ni aniqlash |
| `apps/genealogy/tree.py` | Shajara joylashuvi (sayt va PDF uchun umumiy) |
| `apps/genealogy/pdf.py` | PDF: tarjimai hol, shajara daraxti, shajara kitobi |
| `apps/friends/` | Doʻstlar (kontaktlar) va shajarani boshqa foydalanuvchilar bilan ulashish |
| `apps/genealogy/gedcom.py` | GEDCOM 5.5.1 eksport |
| `apps/core/muchal.py` | Muchal (12 yillik hayvonlar davri, Navroʻzdan boshlanadi) |
| `apps/notify/` | Eslatmalar: sanalarni hisoblash, qoʻngʻiroqcha, Telegram bot, `run_worker`, Cron |
| `apps/accounts/app_bridge.py` | Mac ilovasi uchun Google orqali kirish (`shajara://`) |
| `apps/core/storage.py` | Rasmlarni PostgreSQL’da saqlash |
| `vercel.json` | Vercel: migratsiyalar, Cron, hudud |
| `macos/` | Mac ilovasi (SwiftUI + WebKit) |
| `locale/uz`, `locale/uz_Cyrl` | `django.po` va `djangojs.po` (kompilyatsiya qilingan `.mo` bilan) |
| `fonts/` | DejaVu Sans — PDF ichiga joylanadi (Ў Қ Ғ Ҳ va ʻ ʼ belgilari bor) |
| `tools/i18n_audit.py` | Til auditi (quyida) |

## Til tizimi

* **Tanlash:** sarlavhadagi va pastki qismdagi *Oʻzbekcha | Кириллча* tugmalari, hamda *Sozlamalar → Til*.
* **Saqlash:** tizimga kirgan foydalanuvchi uchun `User.preferred_language` (`uz` yoki `uz-cyrl`)
  maydoniga yoziladi va har safar tizimga kirganda qoʻllanadi. Mehmonlar uchun `til` cookie,
  keyin brauzer tili, keyin standart holatda lotin yozuvi ishlatiladi. Ingliz yoki rus tilidagi brauzerga lotin yozuvi chiqadi.
* **URL:** til prefikssiz (`/uz-cyrl/…` yoʻq): til cookie va akkaunt orqali saqlanadi, havolalar ikkala tilda bir xil.
* **Kirill katalogi:** Django’da `uz_Cyrl` katalogi yoʻq, shuning uchun foydalanuvchi koʻradigan barcha Django
  xabarlari `locale/uz_Cyrl` ichida qayta tarjima qilingan. Lotin katalogida ham Django xabarlari qayta
  yozilgan, chunki Django’ning oʻz tarjimasida apostroflar aralash (o', o‘, oʻ).
* **Apostroflar:** interfeysda `Oʻ oʻ Gʻ gʻ` uchun U+02BB, tutuq belgisi `ʼ` uchun U+02BC ishlatiladi. Ism va joy
  maydonlarida foydalanuvchi yozgan `'`, `‘`, `’`, `` ` `` shu belgilarga keltiriladi; harflar oʻzgarmaydi.
* **Foydalanuvchi maʼlumotlari:** ism, familiya, hikoyalar qanday yozilgan boʻlsa, shunday saqlanadi.
  Transliteratsiya qilinmaydi. Qidiruv uchun alohida `search_key` maydoni bor, shuning uchun
  *Alisher* ↔ *Алишер*, *Jamshid Qodirov* ↔ *Джамшид Кадыров* bir-birini topadi.
* **PDF** foydalanuvchi tanlagan tilda chiqadi, fayl nomi ham (`shajara.pdf` / `шажара.pdf`).

### Yangi matn qoʻshilganda

```bash
.venv/bin/python manage.py makemessages -l uz -l uz_Cyrl --ignore=.venv --ignore=files --no-obsolete
.venv/bin/python manage.py makemessages -d djangojs -l uz -l uz_Cyrl --ignore=.venv --ignore=files
# locale/uz/… va locale/uz_Cyrl/… dagi .po fayllarni tarjima qiling (fuzzy belgisini olib tashlang)
.venv/bin/python manage.py compilemessages --ignore=.venv
.venv/bin/python tools/i18n_audit.py
```

Manba matnlar (msgid) inglizcha — bu Django’ning odatiy yondashuvi. Foydalanuvchi ularni hech qachon koʻrmaydi:
audit va testlar tarjima qilinmagan satr qolmaganini tekshiradi.

## Til sifati nazorati

`tools/i18n_audit.py` (test ichida ham ishlaydi) quyidagilarni tekshiradi:

1. Ikkala katalogda har bir satr tarjima qilingan, `fuzzy` yoʻq, oʻrin toʻldiruvchilar mos keladi.
2. Lotin katalogida kirill harfi va notoʻgʻri apostrof (`o'`, `o‘`, `g’` …) yoʻq.
3. Kirill katalogida lotin harfi yoʻq (istisnolar: PDF, PNG, MB va qidiruvdagi «Alisher» misoli).
4. Shablonlarda `{% translate %}` dan tashqarida matn qolmagan.
5. JavaScript’dagi jumlalar `gettext()` orqali oʻtadi.
6. Python’dagi `messages.*`, `ValidationError`, `add_error`, `Http404` va `PermissionDenied` chaqiruvlari tarjimasiz qoldirilmagan.

`tests/test_i18n.py` har bir sahifani ikkala tilda ochadi va quyidagilarni tekshiradi: kirill sahifada lotin
matni, lotin sahifada kirill matni va inglizcha manba matn yoʻq. Tekshiruvga validatsiya xatolari, 404/403 sahifalari,
JS katalogi, shajara JSON va PDF fayl nomlari ham kiradi.

```bash
.venv/bin/python manage.py test
```

## Maʼlum cheklovlar

* Django admin (`/admin/`) oddiy foydalanuvchi uchun emas. Kirill rejimida u Django’ning lotincha tarjimasida qoladi.
* Veb shrift (Noto Sans) Google Fonts’dan yuklanadi. Internet boʻlmasa, tizim shrifti ishlatiladi:
  macOS, Windows va Android shriftlari oʻzbek kirill harflarini qoʻllaydi.
* Qarindoshlik nomlari qon qarindoshlik, nikoh, kelin/kuyov, qaynota/qaynona, yanga/pochcha va oʻgay
  qarindoshlarni qamraydi. Uzoqroq qarindoshlar «Qarindosh» deb koʻrsatiladi.
