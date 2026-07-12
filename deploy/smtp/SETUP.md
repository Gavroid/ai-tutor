# SMTP Setup для production

## Текущее состояние (2026-07-12)

`SMTP_URL` **не задан** в `.env`. Уведомления работают в режиме **dry_run**:
- EmailNotification запись создаётся в БД со `status="dry_run"`
- Реальная отправка email НЕ происходит
- В логах: `Email skipped (no SMTP_URL)`

## Как активировать реальный SMTP

### Шаг 1: Получить SMTP credentials

**Mailgun** (рекомендую для production, бесплатно 5000 писем/мес):
1. Зарегистрироваться на https://www.mailgun.com/
2. Добавить домен или использовать sandbox domain
3. Получить SMTP credentials: `smtp://postmaster@mg.example.com:password@smtp.mailgun.org:587`

**SendGrid** (100 emails/день бесплатно):
```
smtp://apikey:SG.xxx@smtp.sendgrid.net:587
```

**Gmail** (для тестов, не production):
1. Создать App Password: https://myaccount.google.com/apppasswords
2. `smtp://user@gmail.com:app-password@smtp.gmail.com:587`

### Шаг 2: Добавить в .env

```bash
# На проде 192.168.1.86:
ssh root@192.168.1.86
echo 'SMTP_URL="smtp://user:pass@smtp.example.com:587"' >> /opt/ai-tutor/.env
cat /opt/ai-tutor/.env | grep SMTP_URL
```

### Шаг 3: Тест подключения

```bash
ssh root@192.168.1.86
cd /opt/ai-tutor/deploy/smtp
SMTP_URL="smtp://user:pass@smtp.example.com:587" bash test-smtp.sh
```

Ожидаемый результат:
```
Parsed: user=user, host=smtp.example.com, port=587
OK: SMTP connection works to smtp.example.com:587 as user
```

### Шаг 4: Restart backend

```bash
cd /opt/ai-tutor/deploy
docker compose up -d backend
```

### Шаг 5: Тестовая отправка

Можно вызвать через API:
```bash
# Login admin
TOKEN=$(curl -sk -X POST https://192.168.1.86/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"strongpass1"}' | \
  python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Проверить что notifications отправляются
# (например, через diagnostic finish с user-ом с привязанным parent)
curl -sk -X POST https://192.168.1.86/api/v1/admin/notifications/test \
  -H "Authorization: Bearer $TOKEN"
```

(потребуется создать тестовый endpoint `/admin/notifications/test` если нужно)

### Шаг 6: Проверить БД

```bash
ssh root@192.168.1.86
docker compose exec db psql -U tutor -d tutor -c "
  SELECT to_email, subject, status, error, sent_at
  FROM email_notifications
  ORDER BY created_at DESC
  LIMIT 10;
"
```

Если `status="sent"` — всё работает.
Если `status="failed"` — смотрим `error` (таймаут, неверный пароль, firewall).

## Автоматический fallback

Если `SMTP_URL` не задан — backend не падает, уведомления просто сохраняются в БД.
При первой доступности SMTP можно отправить все `dry_run` через:
```sql
UPDATE email_notifications SET status = 'queued', sent_at = NULL
WHERE status = 'dry_run';
```

Затем restart backend — при следующем цикле уведомления уйдут.

## Безопасность

- Пароль в `.env`, **не в git** (`.env` в `.gitignore`)
- Использовать App Password (не основной пароль)
- Если production — TLS обязательно (порт 587 + STARTTLS, или 465 + SSL)

## Контакты провайдеров

- Mailgun: https://documentation.mailgun.com/en/latest/quickstart.html
- SendGrid: https://docs.sendgrid.com/for-developers/sending-email/integrating-with-the-smtp-api
- AWS SES: https://docs.aws.amazon.com/ses/latest/dg/send-email.html
- Yandex (для РФ): https://yandex.ru/support/mail/mail-clients.html
