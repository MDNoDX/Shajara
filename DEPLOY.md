# Saytni internetga joylash

Hozirgi ishlab turgan manzil: **https://shajara-liard.vercel.app** (Vercel + Neon PostgreSQL, Frankfurt).
GitHub’dagi `main` tarmogʻiga har bir `git push` saytni avtomatik yangilaydi.

Barcha maʼlumotlar — odamlar, voqealar, doʻstlar, eslatmalar **va rasmlar** — bitta PostgreSQL
bazasida saqlanadi. Shuning uchun boshqa serverga koʻchish = bazani koʻchirish (quyida, 3-boʻlim).

---

## 1. Vercel (hozirgi usul)

| Qism | Qayerda |
|---|---|
| Sayt (Django) | Vercel Python funksiyasi (`config/wsgi.py`), hudud `fra1` |
| Baza | Neon PostgreSQL (Vercel Marketplace orqali ulangan, `DATABASE_URL`) |
| Rasmlar | Bazaning `core_storedfile` jadvalida (`apps/core/storage.py`) |
| Kunlik eslatmalar | Vercel Cron → `/cron/kunlik/` har kuni 03:00 UTC (08:00 Toshkent) |
| Telegram bot | Webhook → `/telegram/webhook/` |
| Migratsiyalar | Har bir deploy’da avtomatik (`vercel.json` → `buildCommand`) |

### Muhit oʻzgaruvchilari (Vercel → Project → Settings → Environment Variables)

| Nom | Majburiy | Izoh |
|---|---|---|
| `DATABASE_URL`, `DATABASE_URL_UNPOOLED` | ha | Neon integratsiyasi oʻzi qoʻshadi |
| `DJANGO_SECRET_KEY` | ha | uzun tasodifiy qator |
| `CRON_SECRET` | ha | Vercel Cron shu kalit bilan keladi |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google orqali kirish uchun | quyida |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME` | Telegram eslatmalari uchun | quyida |
| `EMAIL_*`, `DJANGO_EMAIL_BACKEND` | parolni tiklash xatlari uchun | `.env.example` ga qarang |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | faqat oʻz domeningiz boʻlsa | `*.vercel.app` manzillari avtomatik qoʻshiladi |

Oʻzgaruvchi qoʻshilgach, **Deployments → Redeploy** qiling.

### Google orqali kirish

1. https://console.cloud.google.com → yangi loyiha → **APIs & Services → OAuth consent screen**
   (External, ilova nomi «Shajara», email).
2. **Credentials → Create credentials → OAuth client ID → Web application**.
3. *Authorized redirect URIs*: `https://shajara-liard.vercel.app/accounts/google/login/callback/`
   (oʻz domeningiz boʻlsa, uni ham qoʻshing).
4. Berilgan *Client ID* va *Client secret* ni Vercel’ga `GOOGLE_CLIENT_ID` va `GOOGLE_CLIENT_SECRET` qilib yozing → Redeploy.

Kirish sahifasida «Google orqali davom etish» tugmasi paydo boʻladi. Google’dagi email mavjud akkaunt
emailiga mos kelsa, oʻsha akkauntga ulanadi; aks holda yangi akkaunt ochiladi va profilni toʻldirish soʻraladi.

### Telegram bot

1. Telegramda [@BotFather](https://t.me/BotFather) → `/newbot` → nom va foydalanuvchi nomi.
2. Tokenni Vercel’ga `TELEGRAM_BOT_TOKEN`, nomini (`@` siz) `TELEGRAM_BOT_USERNAME` qilib yozing → Redeploy.
3. Saytda **Boshqaruv paneli** (`/boshqaruv/`) → **«Botni saytga ulash»** tugmasi.
4. Foydalanuvchilar **Sozlamalar → Eslatmalar → Telegramni ulash** orqali ulanadi.

### Oʻz domeningiz

Vercel → Project → **Domains** → domenni qoʻshing va koʻrsatilgan DNS yozuvlarini registratorda kiriting.
Keyin `DJANGO_ALLOWED_HOSTS=shajara.uz` va `DJANGO_CSRF_TRUSTED_ORIGINS=https://shajara.uz` qoʻshing,
Google’dagi redirect URI’ni yangilang va Telegram webhookni qayta oʻrnating.

### Bepul rejim cheklovlari

Neon bepul rejimi: 0,5 GB baza — bir necha ming odam va yuzlab rasm uchun yetarli (bitta rasm
koʻpi bilan 5 MB). Hajmni Boshqaruv panelida kuzating.

---

## 2. Boshqaruv (administrator)

* **`/boshqaruv/`** — statistika, foydalanuvchilar, rasmlar hajmi, Telegram va Cron holati,
  **toʻliq zaxira** yuklab olish. Faqat superuser koʻradi (foydalanuvchi menyusida havola bor).
* **`/admin/`** — Django admin: istalgan yozuvni koʻrish va tahrirlash.
* Yangi administrator: `python manage.py createsuperuser` (lokal, production bazaga ulangan holda) yoki
  admin’da foydalanuvchiga *Superuser status* belgisini qoʻying.

---

## 3. Zaxira nusxa va boshqa serverga koʻchish

Maʼlumotlar yoʻqolmasligi uchun uchta yoʻl bor — bittasini muntazam qiling:

| Usul | Nima saqlanadi | Qanday |
|---|---|---|
| **Toʻliq zaxira** (tavsiya) | Butun sayt: foydalanuvchilar, parollar, arxivlar, rasmlar, eslatmalar | `/boshqaruv/` → *Toʻliq zaxira nusxa (JSON)* |
| Oila arxivi | Bitta foydalanuvchining shajarasi (rasmlar bilan) | *Sozlamalar → Maʼlumotlaringiz → Maʼlumotlarimni yuklab olish (JSON)* |
| `pg_dump` | Bazaning aynan nusxasi | `pg_dump "$DATABASE_URL_UNPOOLED" > shajara.sql` |

### Yangi serverga tiklash

```bash
# yangi serverda (Docker yoki boshqa hosting), bazani yaratib:
python manage.py migrate
python manage.py loaddata shajara-zaxira-2026-09-30.json      # toʻliq zaxira
# yoki bitta oila arxivi:
python manage.py import_archive arxiv.json --user MDNoDX
# yoki pg_dump nusxasi:
psql "$DATABASE_URL" < shajara.sql
```

Rasmlar bazada boʻlgani uchun alohida koʻchirish shart emas. Parollar ham koʻchadi.

---

## 4. Docker bilan oʻz serveringizda (muqobil)

Istalgan Linux VPS (1 vCPU, 1–2 GB RAM, Ubuntu 22.04/24.04): Hetzner, DigitalOcean, Ahost.uz va boshqalar.

| Xizmat | Vazifasi |
|---|---|
| `web` | Django + gunicorn |
| `worker` | Eslatmalar va Telegram bot (*long polling*, webhook shart emas) |
| `db` | PostgreSQL 17 (maʼlumotlar va rasmlar) |
| `caddy` | HTTPS (Let’s Encrypt) avtomatik |

```bash
ssh root@SERVER_IP
curl -fsSL https://get.docker.com | sh
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
git clone https://github.com/MDNoDX/Shajara.git shajara && cd shajara
cp .env.example .env && nano .env         # DOMAIN, DJANGO_SECRET_KEY, POSTGRES_PASSWORD …
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

DNS’da domenning **A-yozuvi** server IP’ga yoʻnaltirilgan boʻlishi kerak. Tekshirish: `https://DOMEN/salomatlik/` → `{"status": "ok"}`.

Yangilash: `git pull && docker compose up -d --build` (migratsiyalar avtomatik).

Zaxira:

```bash
docker compose exec -T db pg_dump -U shajara shajara | gzip > backup-$(date +%F).sql.gz
gunzip -c backup-2026-09-30.sql.gz | docker compose exec -T db psql -U shajara shajara   # tiklash
```

Vercel’dan koʻchganda Telegram webhookni oʻchiring (`docker compose exec web python manage.py telegram_webhook --delete`) — shunda `worker` botni oʻzi tinglaydi — va Google redirect URI’ni yangi domenga moslang.

---

## 5. Muammolar

| Belgi | Sabab |
|---|---|
| `400 Bad Request` | `DJANGO_ALLOWED_HOSTS` da domen yoʻq |
| Forma yuborilganda 403 | `DJANGO_CSRF_TRUSTED_ORIGINS` da `https://DOMEN` yoʻq |
| Google tugmasi yoʻq | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` berilmagan yoki Redeploy qilinmagan |
| Google «redirect_uri_mismatch» | Google Console’dagi redirect URI sayt manziliga mos emas |
| Telegram javob bermayapti | Token notoʻgʻri yoki webhook oʻrnatilmagan (`/boshqaruv/`) |
| Eslatmalar kelmayapti | `CRON_SECRET` yoʻq; Vercel → Project → **Cron Jobs** loglarini koʻring |

Loglar: Vercel → Project → **Logs** (yoki `vercel logs`), Docker’da `docker compose logs -f web`.

## Xavfsizlik

- `DJANGO_DEBUG=0` (Vercel’da standart), HTTPS, HSTS, xavfsiz cookie yoqilgan.
- Maxfiy kalitlar faqat Vercel/`.env` da; `.env` gitga qoʻshilmaydi.
- `seed_demo` foydalanuvchilarining paroli repozitoriyda ochiq — ularni production’ga yuklamang.
