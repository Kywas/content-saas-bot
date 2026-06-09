# Content Factory Bot

Telegram-бот для генерации контента с подпиской. Отдельный проект — не связан с `astro-telegram-bot`.

## Что делает

- Генерирует посты, хуки, контент-план на 7 дней и подписи
- Бесплатный тариф: 5 генераций в день (настраивается)
- Премиум: безлимит на 30 дней
- Оплата через Telegram Stars и/или карту (ЮKassa/Stripe token)
- Админ-команда `/stats` — статистика дохода и пользователей

## Быстрый старт

```bash
cd content-saas-bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Заполни `.env`:

- `BOT_TOKEN` — токен от [@BotFather](https://t.me/BotFather)
- `ADMIN_IDS` — твой Telegram ID (через [@userinfobot](https://t.me/userinfobot))
- `OPENAI_API_KEY` — опционально, для AI-генерации (без ключа работают шаблоны)
- `ENABLE_PAYMENTS=true` — когда подключишь оплату

Запуск:

```bash
python main.py
```

## Монетизация

| Тариф | Цена по умолчанию | Что даёт |
|-------|-------------------|----------|
| Free  | 0 ₽               | 5 генераций/день |
| Premium | 149 Stars / 299 ₽ / $4.99 | Безлимит 30 дней |

Цены меняются в `.env`: `PREMIUM_PRICE_STARS`, `PREMIUM_PRICE_RUB`, `PREMIUM_PRICE_USD`.

## Подключение оплаты

1. В [@BotFather](https://t.me/BotFather) → Payments → подключи провайдера (ЮKassa для ₽, Stripe для $)
2. Скопируй `PAYMENT_PROVIDER_TOKEN` в `.env`
3. Поставь `ENABLE_PAYMENTS=true`
4. Stars работают без provider token

## Структура

```
content-saas-bot/
├── main.py
├── app/
│   ├── bot.py          # хендлеры Telegram
│   ├── content.py      # генерация контента
│   ├── database.py     # SQLite
│   ├── payments.py     # оплата
│   └── premium.py      # логика подписки
└── content_saas.db     # создаётся автоматически
```

## Деплой на VPS + автообновление

Бот ставится в `/opt/content-saas-bot`. При каждом `push` в `main` GitHub Actions подключается по SSH и перезапускает сервис.

### Шаг 1 — репозиторий на GitHub

```bash
cd content-saas-bot
git init
git add .
git commit -m "Initial commit: Content Factory bot"
git branch -M main
git remote add origin https://github.com/YOUR_USER/content-saas-bot.git
git push -u origin main
```

### Шаг 2 — секреты в GitHub

В репозитории: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Значение |
|--------|----------|
| `VPS_HOST` | IP сервера |
| `VPS_USER` | `root` (или другой пользователь с sudo) |
| `VPS_SSH_KEY` | приватный SSH-ключ (весь файл `id_rsa`) |
| `VPS_PORT` | `22` |

Если астробот уже деплоится с того же VPS — можно использовать те же секреты.

### Шаг 3 — первичная настройка VPS (один раз)

Подключись к серверу по SSH и выполни:

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USER/content-saas-bot/main/scripts/bootstrap_vps.sh -o bootstrap.sh
bash bootstrap.sh https://github.com/YOUR_USER/content-saas-bot.git
```

Или скопируй `scripts/bootstrap_vps.sh` на сервер и запусти вручную.

Затем отредактируй `.env` на сервере:

```bash
nano /opt/content-saas-bot/.env
```

Минимум:

```env
BOT_TOKEN=твой_токен
ADMIN_IDS=твой_telegram_id
ENABLE_PAYMENTS=false
```

Запуск:

```bash
systemctl start contentbot
systemctl status contentbot
journalctl -u contentbot -f
```

### Шаг 4 — авто-деплой

После настройки каждый `git push origin main` автоматически:

1. делает `git pull` на VPS
2. обновляет зависимости
3. перезапускает `contentbot`

Проверка логов на сервере:

```bash
journalctl -u contentbot -n 50 --no-pager
```
