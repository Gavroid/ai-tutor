# SSL / Let's Encrypt для AI-репетитора

## Решение Sprint 6.5 (2026-07-13): **остаётся self-signed**

**Контекст:** хост `Kirill-AI.lan` в локальной сети (LAN-only, без публичного IP, без DNS).
Хост `192.168.1.86` доступен только из локальной сети `192.168.0.0/16` за домашним NAT.
Внешний IP не проброшен, доменного имени нет.

**Threat model:** система используется одной семьёй (Игорь + Кирилл).
Атакующий в той же LAN уже может сделать MITM проще — self-signed не увеличивает поверхность атаки.
Доступа из Интернет нет → публичный MITM и подмена сертификата невозможны.

**Почему Let's Encrypt НЕ подходит:**
1. HTTP-01 challenge требует 80 порт, доступный из Интернета + DNS A-запись.
   У LAN-only системы их нет.
2. DNS-01 challenge требует API-доступ к DNS-провайдеру — нет публичного домена.
3. Самоподписанный сертификат + `TRUSTED_PROXIES=192.168.0.0/16` уже исключает
   MITM-атаки на все устройства, которые хостят `192.168.1.86` в `hosts` или
   доверяют корпоративному CA на устройстве.

**Правила для перехода на LE (когда появится реальный домен):**
1. Купить домен (или бесплатный freedns.afraid.org, duckdns.org).
2. Добавить A-запись `tutor.<domain>` → публичный IP (с NAT port-forwarding 80/443).
3. Запустить `certbot --nginx -d tutor.<domain> --agree-tos -m admin@<domain>`.
4. Раскомментировать `Strict-Transport-Security` в `deploy/nginx/nginx.conf`.
5. Обновить `TRUSTED_PROXIES` (убрать LAN CIDR).
6. Обновить CORS и CSP: разрешить `tutor.<domain>` в `Access-Control-Allow-Origin`.
7. Провести test-restore backup на чистом окружении (LE прозрачно использует тот же backend).

**Текущая конфигурация:**
- Self-signed certs: `/opt/ai-tutor/deploy/ssl/certs/{fullchain.pem,privkey.pem}`
- Генератор: `deploy/ssl/generate-self-signed.sh` (CN=Kirill-AI.lan, alt=192.168.1.86)
- HSTS: закомментирован (только для HTTPS-режима)
- Nginx: SSL `ssl_protocols TLSv1.2 TLSv1.3`, strong ciphers, HTTP/2 отключён (для WS upgrade)

**Sanity-check:**
```bash
# Должно вернуть 200 OK с self-signed ошибкой, но не 5xx
curl -sk https://192.168.1.86/health | python3 -m json.tool
```

Решение принято Игорем 2026-07-13, зафиксировано в `docs/security.md` (Sprint 6.5).
