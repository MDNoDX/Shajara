# Shajara — oʻzbek oilalari uchun oilaviy arxiv (Django)

Asosiy til — **Oʻzbekcha (lotin)**; toʻliq tarjimalar: **Ўзбекча (kirill)**, **Русский** va **English**.
Hammasi Django’ning rasmiy i18n tizimi orqali ishlaydi (`gettext`, `.po` → `.mo`,
`LocaleMiddleware`, `JavaScriptCatalog`).

> Oldingi bir faylli prototip `files/` papkasida qoldirilgan. Qarindoshlik mantigʻi
> va lotin↔kirill qidiruvi oʻsha yerdan Pythonga koʻchirildi.

## Imkoniyatlar

- **Shajara daraxti** — bitta bogʻlangan chizma. Tarmoqlar rang bilan ajratilgan (oʻz oilasi, ota tomoni,
  ona tomoni), toʻgʻri ajdodlar chizigʻi zarhal; chapda avlod nomlari, burchakda kichik xarita;
  uzoqlashtirganda kartalar soddalashadi. Kartani bosganda yon panel ochiladi va qarindosh **shu yerning oʻzida**
  qoʻshiladi. «Faqat ota tomoni / ona tomoni» koʻrinishi va **ajdodlar yelpigʻichi** ham bor.
- **Birgalikda tuzish** — qarindoshni havola orqali taklif qilasiz (koʻrish yoki tahrirlash huquqi bilan);
  u shajarani oʻz oʻrnidan nomlangan holda koʻradi. **Oʻzgarishlar tarixi**: kim nimani qoʻshgani koʻrinadi,
  xato oʻzgarish yoki oʻchirish ortga qaytariladi.
- **Dublikatlar** — qoʻshayotganda ogohlantirish, topilgan juftlarni birlashtirish (maʼlumot yoʻqolmaydi).
- **Albom** — har bir odamga suratlar, hujjatlar (PDF) va ovozli yozuvlar; suratlar yuklashda kichraytiriladi.
- **Hayot yoʻli va vaqt chizigʻi** — odam sahifasida tugʻilish, toʻy, farzandlar; butun oila boʻyicha oʻn yilliklar.
- **Qarindoshlik nomlari** avtomatik: aka/uka, opa/singil, amaki/amma/togʻa/xola, amakivachcha…,
  kelin/kuyov, qaynota/qaynona, yanga/pochcha, «Buvining ukasi», «Onaning xolavachchasi», «Togʻaning xotini».
- **Muchal** — har bir odamning muchali (yil Navroʻzda almashadi), keyingi muchal yili, Navroʻzda eslatma.
- **Oilaviy voqealar** — toʻy, fotiha, farzand kutilmoqda, tugʻilish, beshik toʻyi, sunnat toʻyi, yil oshi
  va boshqalar; kelajakdagi sanalar.
- **Doʻstlar** — istalgan kishining (oʻzingiz, dadangiz, buvingiz…) doʻstlari, tugʻilgan kunlari bilan.
- **Eslatmalar** — tugʻilgan kunlar, nikoh yilliklari, xotira kunlari, voqealar, muchal yili: saytda,
  **Telegram bot** orqali va **telefonga push-bildirishnoma** qilib (sayt bosh ekranga qoʻshilganda).
  Bosh sahifadagi «Bugun» blokidan bir bosishda tabrik yuboriladi.
- **Kim kimga kim?** — ikki odam orasidagi qarindoshlik va bogʻlanish zanjiri.
- **Familiya taklifi** — oʻgʻil nevaraga ota tarafdagi bobosining ismidan (Madaminjon → Madaminov).
- **Chop etish** — muqovali **shajara kitobi**, **devoriy plakat** (balandligi 42 yoki 59 sm, uzunligi oilaga qarab),
  tarjimai hol va daraxt PDF; PNG.
- **GEDCOM** — eksport va **import** (MyHeritage, Ancestry, Gramps va boshqalardan).
- **Xavfsizlik** — ikki bosqichli kirish (autentifikator ilovasi + tiklash kodlari), Google orqali kirish,
  boshqa qurilmalardan chiqish, notoʻgʻri parolda vaqtincha toʻxtatish.
- **Zaxira** — har hafta butun baza bitta fayl boʻlib administratorning Telegramiga yuboriladi; qoʻlda ham yuklab olinadi.
- **Dizayn** — «nil va zar» (toʻq koʻk + zarhal, ikat naqshi), Source Serif 4 + Inter, yorugʻ / qorongʻi / tizim
  mavzusi, chap yon menyu (yigʻiladi), telefonda pastki menyu, **⌘K / Ctrl+K** tezkor qidiruv, toʻrt til.
- **Boshqaruv paneli** (`/boshqaruv/`) — holat, foydalanuvchilar, zaxira.
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

`seed_demo` uchta sinov foydalanuvchisini yaratadi: `namuna` (lotin), `dilnoza_a` (kirill, shajarani koʻra oladi)
va `anvar_y` (unga taklif havolasi tayyorlangan). Parol `apps/genealogy/management/commands/seed_demo.py` faylida
yozilgan va faqat lokal ishlab chiqish uchun moʻljallangan.

PostgreSQL uchun `DATABASE_URL=postgres://…` oʻzgaruvchisini bering (qarang: `.env.example`).
Oʻzgaruvchi berilmasa, SQLite ishlatiladi. Rasmlar ham bazada saqlanadi (`apps/core/storage.py`),
shuning uchun bazaning zaxira nusxasi hamma narsani oʻz ichiga oladi.

## Tuzilma

| Joy | Vazifasi |
|---|---|
| `config/settings.py` | `LANGUAGE_CODE="uz"`, `LANGUAGES` (`uz`, `uz-cyrl`, `ru`, `en`), `LOCALE_PATHS`, middleware |
| `static/css/app.css` | Dizayn tizimi: ranglar, shriftlar, radiuslar (8 / 12 / 18), barcha komponentlar |
| `config/formats/uz`, `config/formats/uz_Cyrl` | Django sana/son formatlari |
| `apps/core/languages.py` | Tillar va ularning oʻz yozuvidagi nomlari (Oʻzbekcha / Кириллча) |
| `apps/core/middleware.py` | Tizimga kirgan foydalanuvchiga akkauntida saqlangan tilni yoqadi |
| `apps/core/dates.py` | Sanalar: *27-sentabr 2026-yil* / *2026 йил 27 сентябрь*; qisman sanalar ham |
| `apps/core/text.py` | Apostroflarni bir xil koʻrinishga keltirish va lotin/kirill qidiruv kaliti |
| `apps/core/django_messages.py` | Django’ning oʻz xabarlari (validatsiya, parol) — qayta tarjima uchun |
| `apps/genealogy/terminology.py` | **Qarindoshlik atamalari lugʻati** (yagona manba) |
| `apps/genealogy/kinship.py` | Aka/uka, opa/singil, amaki/amma/togʻa/xola, kelin/kuyov… ni aniqlash |
| `apps/genealogy/tree.py` | Shajara joylashuvi (sayt va PDF uchun umumiy) |
| `apps/genealogy/pdf.py` | PDF: tarjimai hol, shajara daraxti, devoriy plakat, muqovali shajara kitobi |
| `apps/friends/` | Doʻstlar (kontaktlar) |
| `apps/accounts/sharing.py` | Umumiy shajara: aʼzolik (`Membership`), taklif havolalari (`Invite`), huquqlar |
| `apps/accounts/totp.py` | Ikki bosqichli kirish (TOTP, tiklash kodlari) |
| `apps/genealogy/history.py` | Oʻzgarishlar tarixi va ortga qaytarish |
| `apps/genealogy/duplicates.py` | Dublikatlarni topish va birlashtirish |
| `apps/genealogy/gedcom.py` | GEDCOM 5.5.1 eksport va import |
| `apps/notify/push.py` | Push-bildirishnomalar (Web Push, VAPID); `templates/sw.js` — service worker |
| `apps/core/backup.py` | Toʻliq zaxira nusxa (qoʻlda va haftalik) |
| `apps/core/images.py` | Suratlarni yuklashda kichraytirish |
| `tools/make_icons.py` | Logotip, sayt va Mac ilovasi belgilarini yaratadi |
| `apps/core/muchal.py` | Muchal (12 yillik hayvonlar davri, Navroʻzdan boshlanadi) |
| `apps/notify/` | Eslatmalar: sanalarni hisoblash, qoʻngʻiroqcha, Telegram bot, `run_worker`, Cron |
| `apps/accounts/app_bridge.py` | Mac ilovasi uchun Google orqali kirish (`shajara://`) |
| `apps/core/storage.py` | Rasmlarni PostgreSQL’da saqlash |
| `vercel.json` | Vercel: migratsiyalar, Cron, hudud |
| `macos/` | Mac ilovasi (SwiftUI + WebKit) |
| `locale/uz`, `locale/uz_Cyrl`, `locale/ru`, `locale/en` | `django.po` va `djangojs.po` (kompilyatsiya qilingan `.mo` bilan) |
| `apps/core/timezones.py` | Foydalanuvchi vaqt mintaqalari (eslatma soati shu boʻyicha) |
| `fonts/` | DejaVu Sans — PDF ichiga joylanadi (Ў Қ Ғ Ҳ va ʻ ʼ belgilari bor) |
| `tools/i18n_audit.py` | Til auditi (quyida) |

## Til tizimi

* **Tanlash:** foydalanuvchi menyusi (yon menyu pastida), mehmonlar uchun yuqoridagi globus, hamda *Sozlamalar → Til*.
* **Saqlash:** tizimga kirgan foydalanuvchi uchun `User.preferred_language` (`uz`, `uz-cyrl`, `ru`, `en`)
  maydoniga yoziladi va har safar tizimga kirganda qoʻllanadi. Mehmonlar uchun `til` cookie,
  keyin brauzer tili (faqat oʻzbek lotin/kirill), keyin standart holatda lotin yozuvi ishlatiladi. Rus va ingliz tillari
  faqat foydalanuvchi oʻzi tanlaganda yoqiladi: sayt avval oʻzbek tilida ochiladi.
* **Rus tili grammatikasi:** koʻplik uch shaklda (1 год, 2 года, 5 лет), sanada oy qaratqich kelishigida
  (27 сентября), qarindoshlik zanjiri ham («Младший брат бабушки») — `terminology.KIN_OF`.
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
.venv/bin/python manage.py makemessages -l uz -l uz_Cyrl -l ru -l en --ignore=.venv --ignore=files --ignore=macos --no-obsolete
.venv/bin/python manage.py makemessages -d djangojs -l uz -l uz_Cyrl -l ru -l en --ignore=.venv --ignore=files --ignore=macos --ignore=staticfiles
# locale/uz/… va locale/uz_Cyrl/… dagi .po fayllarni tarjima qiling (fuzzy belgisini olib tashlang)
.venv/bin/python manage.py compilemessages --ignore=.venv
.venv/bin/python tools/i18n_audit.py
```

Manba matnlar (msgid) inglizcha — bu Django’ning odatiy yondashuvi. Foydalanuvchi ularni hech qachon koʻrmaydi:
audit va testlar tarjima qilinmagan satr qolmaganini tekshiradi.

## Til sifati nazorati

`tools/i18n_audit.py` (test ichida ham ishlaydi) quyidagilarni tekshiradi:

1. Har bir katalogda har bir satr tarjima qilingan (ingliz tilida manba matn ishlatilishi mumkin), `fuzzy` yoʻq,
   oʻrin toʻldiruvchilar mos keladi, rus koʻpligi uch shaklda, rus katalogida oʻzbekcha harflar (ў қ ғ ҳ) yoʻq.
2. Lotin katalogida kirill harfi va notoʻgʻri apostrof (`o'`, `o‘`, `g’` …) yoʻq.
3. Kirill katalogida lotin harfi yoʻq (istisnolar: PDF, PNG, MB va qidiruvdagi «Alisher» misoli).
4. Shablonlarda `{% translate %}` dan tashqarida matn qolmagan.
5. JavaScript’dagi jumlalar `gettext()` orqali oʻtadi.
6. Python’dagi `messages.*`, `ValidationError`, `add_error`, `Http404` va `PermissionDenied` chaqiruvlari tarjimasiz qoldirilmagan.

`tests/test_i18n.py` har bir sahifani toʻrt tilda ochadi va quyidagilarni tekshiradi: kirill sahifada lotin
matni, lotin sahifada kirill matni, oʻzbek va rus sahifalarida inglizcha manba matn, rus sahifasida oʻzbekcha harf yoʻq. Tekshiruvga validatsiya xatolari, 404/403 sahifalari,
JS katalogi, shajara JSON va PDF fayl nomlari ham kiradi.

```bash
.venv/bin/python manage.py test
```

## Maʼlum cheklovlar

* Django admin (`/admin/`) oddiy foydalanuvchi uchun emas. Oʻzbek kirill rejimida u Django’ning lotincha tarjimasida qoladi.
* Veb shriftlar (Source Serif 4, Inter) Google Fonts’dan yuklanadi; ikkalasida ham Ў Қ Ғ Ҳ va ʻ ʼ bor.
  Internet boʻlmasa, tizim shrifti ishlatiladi.
* Push-bildirishnomalar iPhone/iPad’da faqat sayt bosh ekranga qoʻshilgandan keyin ishlaydi (iOS 16.4+).
* Umumiy shajarada har bir hisobning oʻz arxivi saqlanadi; ikki alohida arxivni bittaga qoʻshish uchun
  GEDCOM yoki JSON import va dublikatlarni birlashtirish ishlatiladi.
* Qarindoshlik nomlari qon qarindoshlik, nikoh, kelin/kuyov, qaynota/qaynona, yanga/pochcha va oʻgay
  qarindoshlarni qamraydi. Uzoqroq qarindoshlar «Qarindosh» deb koʻrsatiladi.
