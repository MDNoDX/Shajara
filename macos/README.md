# Shajara — Mac ilovasi

Saytni alohida, qulay Mac oynasida ochadi va unga Mac’ning oʻz imkoniyatlarini qoʻshadi:

- **Tizim bildirishnomalari** — tugʻilgan kunlar, yilliklar va voqealar haqida, **oʻz ovozi** bilan
  (Shajara qoʻngʻirogʻi / tizim ovozi / ovozsiz); har 10 daqiqada va ilova ochilganda tekshiradi;
- **Menyu satridagi qoʻngʻiroqcha** — oʻqilmagan eslatmalar roʻyxati va tezkor havolalar;
- **Dock belgisi** — oʻqilmagan eslatmalar soni; Dock’da oʻng tugma — tezkor menyu;
- **Fonda ishlash** — oyna yopilsa ham eslatmalar keladi; **kompyuter yoqilganda ishga tushadi** (ixtiyoriy);
- **Sayt tilida** — menyular va sozlamalar saytda tanlangan tilga oʻzi oʻtadi (oʻzbek lotin / kirill, rus, ingliz);
- **Google orqali kirish** — Mac’ning xavfsiz kirish oynasida (Google ilova ichidagi sahifada kirishga ruxsat bermaydi);
- **Telegram** — «@bot ni ochish» tugmasi toʻgʻridan-toʻgʻri Telegram ilovasini ochadi;
- **Yuklab olish** — PDF, PNG, GEDCOM va JSON fayllar «Saqlash» oynasi orqali, keyin Finder’da koʻrsatiladi;
- **Chop etish** (⌘P), rasm va arxiv faylini tanlash, tasdiqlash oynalari; tashqi havolalar oddiy brauzerda ochiladi;
- Oxirgi ochilgan sahifa va masshtab eslab qolinadi;
- Tugmalar: ⌘1 Shajaram, ⌘2 Qarindoshlarim, ⌘3 Voqealar, ⌘4 Doʻstlarim, ⌘F Qidiruv, ⌘N Qarindosh qoʻshish,
  ⇧⌘B Bildirishnomalar, ⌘R Yangilash, ⌘[ / ⌘] Orqaga / Oldinga, ⌘+ / ⌘− / ⌘0 Masshtab, ⌘, Sozlamalar;
- Internet boʻlmasa — «Qayta urinish» oynasi; tizimga bir marta kirasiz, keyingi safar eslab qoladi.

macOS 13 (Ventura) va yangilari, Apple Silicon va Intel.

## Yigʻish va oʻrnatish

Xcode (yoki Command Line Tools) oʻrnatilgan boʻlishi kerak.

```bash
cd macos
./build.sh install
```

`build/Shajara.app` yaratiladi va `/Applications` ga nusxalanadi. Launchpad yoki Spotlight’dan «Shajara» deb oching.
Birinchi ochilishda bildirishnomalarga ruxsat soʻraladi — «Ruxsat berish» ni bosing.

Faqat yigʻish (oʻrnatmasdan): `./build.sh`.

## Sozlamalar (⌘,)

- **Umumiy** — sayt manzili (standart `https://shajara-liard.vercel.app`; saytni boshqa serverga yoki oʻz
  domeningizga koʻchirsangiz, yangi manzilni yozing — ilovani qayta yigʻish shart emas), kirishda ishga tushirish,
  fonda ishlash, menyu satridagi qoʻngʻiroqcha.
- **Bildirishnomalar** — yoqish / oʻchirish, ovozni tanlash, «Sinab koʻrish».
- **Ilova haqida** — versiya.

## Boshqa Mac’larga tarqatish va App Store

`build.sh` ilovani *ad-hoc* imzolaydi: u shu Mac’da ishlaydi. Boshqa kompyuterlarda macOS
«noaniq dasturchi» deb ogohlantiradi (Finder’da oʻng tugma → **Ochish** bilan ochiladi).

Ogohlantirishsiz tarqatish yoki App Store uchun:

1. [Apple Developer Program](https://developer.apple.com/programs/) aʼzoligi (yiliga 99 $).
2. Developer ID bilan imzolash va notarizatsiya:
   ```bash
   SIGN_IDENTITY="Developer ID Application: Ism Familiya (TEAMID)" ./build.sh
   ditto -c -k --keepParent build/Shajara.app Shajara.zip
   xcrun notarytool submit Shajara.zip --apple-id EMAIL --team-id TEAMID --wait
   xcrun stapler staple build/Shajara.app
   ```
3. App Store uchun Xcode’da yangi *macOS App* loyihasi oching, `Shajara/*.swift`, `Info.plist`,
   `Shajara.entitlements` va `Resources/AppIcon.icns` ni qoʻshing, *Signing & Capabilities* da jamoangizni
   tanlang va **Product → Archive → Distribute App → App Store Connect** qiling.

## Tuzilma

| Fayl | Vazifasi |
|---|---|
| `Shajara/ShajaraApp.swift` | Ilova, oyna, menyular, menyu satri, Dock menyusi, oflayn oyna |
| `Shajara/Browser.swift` | WebKit oynasi, navigatsiya, Google orqali kirish |
| `Shajara/WebView.swift` | Yuklab olish, rasm tanlash, tasdiqlash oynalari, tashqi havolalar |
| `Shajara/Notifier.swift` | Bildirishnomalar, ovoz va Dock belgisi (`/xabarlar/holat.json`) |
| `Shajara/SettingsView.swift` | Sozlamalar oynasi |
| `Shajara/L10n.swift` | Ilova matnlari toʻrt tilda |
| `make_sound.py` | Bildirishnoma ovozini yaratadi (`Resources/Shajara.wav`) |
| `make_icon.py` | Ilova belgisini yaratadi (`Resources/AppIcon.icns`) |
| `build.sh` | Universal (arm64 + x86_64) `Shajara.app` yigʻadi va imzolaydi |

Google orqali kirish qanday ishlaydi: ilova `/ilova/kirish/boshlash/` sahifasini Mac’ning kirish oynasida ochadi →
Google’dan keyin sayt bir martalik, 2 daqiqa amal qiladigan kalit bilan `shajara://kirish?token=…` ga qaytaradi →
ilova shu kalit bilan `/ilova/kirish/` orqali tizimga kiradi.
