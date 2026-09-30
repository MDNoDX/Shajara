# Saytni internetga joylash

Loyiha Docker bilan istalgan Linux serverda (VPS) ishlaydi: Hetzner, DigitalOcean, AWS Lightsail,
Ahost.uz, Uzhost va boshqalar. Kerakli minimal server: 1 vCPU, 1–2 GB RAM, 20 GB disk, Ubuntu 22.04/24.04.

Tarkib (`docker-compose.yml`):

| Xizmat | Vazifasi |
|---|---|
| `web` | Django + gunicorn (sayt) |
| `worker` | Eslatmalarni har kuni yaratadi, Telegramga yuboradi, botga javob beradi |
| `db` | PostgreSQL 17 |
| `caddy` | HTTPS sertifikatini avtomatik oladi (Let’s Encrypt), rasmlarni beradi |

## 1. Domen

Domen sotib oling (masalan, `.uz` — cctld.uz roʻyxatidagi registratorlardan). DNS sozlamalarida
**A-yozuv**ni server IP manziliga yoʻnaltiring: `shajara.example.uz → 203.0.113.10`.

## 2. Serverni tayyorlash

```bash
ssh root@SERVER_IP
curl -fsSL https://get.docker.com | sh
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
```

## 3. Loyihani yuklash

```bash
git clone <repozitoriy-manzili> shajara && cd shajara
cp .env.example .env
nano .env        # DOMAIN, DJANGO_SECRET_KEY, POSTGRES_PASSWORD va boshqalarni toʻldiring
```

`DJANGO_SECRET_KEY` uchun: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`.

## 4. Ishga tushirish

```bash
docker compose up -d --build
docker compose exec web python manage.py createsuperuser   # administrator
```

Bir-ikki daqiqadan soʻng `https://DOMEN` ochiladi. Tekshirish: `https://DOMEN/salomatlik/` → `{"status": "ok"}`.

## 5. Telegram eslatmalari (ixtiyoriy)

1. Telegramda [@BotFather](https://t.me/BotFather) → `/newbot` → nom va foydalanuvchi nomini bering.
2. Berilgan tokenni `.env` ga yozing: `TELEGRAM_BOT_TOKEN=...`, `TELEGRAM_BOT_USERNAME=shajara_bot`.
3. `docker compose up -d` — `worker` botni ishga tushiradi.
4. Foydalanuvchilar **Sozlamalar → Eslatma sozlamalari → Telegramni ulash** tugmasi orqali ulanadi.

Bot webhook emas, *long polling* bilan ishlaydi — qoʻshimcha sozlash kerak emas.

## 6. Yangilash

```bash
git pull
docker compose up -d --build        # migratsiyalar avtomatik bajariladi
```

## 7. Zaxira nusxa (backup)

Maʼlumotlar bazasi:

```bash
docker compose exec -T db pg_dump -U shajara shajara | gzip > backup-$(date +%F).sql.gz
```

Tiklash:

```bash
gunzip -c backup-2026-09-28.sql.gz | docker compose exec -T db psql -U shajara shajara
```

Rasmlar (`media` hajmi):

```bash
docker run --rm -v shajara_media:/m -v "$PWD":/b alpine tar czf /b/media-$(date +%F).tgz -C /m .
```

Kunlik avtomatik zaxira uchun yuqoridagi buyruqni `crontab -e` ga qoʻshing, nusxalarni boshqa joyda ham saqlang.

## 8. Loglar va muammolar

```bash
docker compose ps
docker compose logs -f web
docker compose logs -f worker
```

| Belgi | Sabab |
|---|---|
| Sertifikat olinmayapti | DNS hali yangilanmagan yoki 80/443 portlar yopiq |
| `400 Bad Request` | `DJANGO_ALLOWED_HOSTS` da domen yoʻq |
| Forma yuborilganda 403 | `DJANGO_CSRF_TRUSTED_ORIGINS` da `https://DOMEN` yoʻq |
| Telegram ishlamayapti | `TELEGRAM_BOT_TOKEN` notoʻgʻri yoki `worker` toʻxtagan |

## Xavfsizlik

- `DJANGO_DEBUG=0` (standart), HTTPS majburiy, HSTS, xavfsiz cookie — `settings.py` da yoqilgan.
  `python manage.py check --deploy` hech qanday ogohlantirish bermaydi.
- Rasmlar tasodifiy nomlar bilan saqlanadi, lekin havolani bilgan odam ularni koʻra oladi.
- `.env` faylini hech kimga bermang va gitga qoʻshmang (`.gitignore` da bor).
