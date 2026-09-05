# Backend dependency security audit (2026-08-23)

Tool: pip-audit (https://pypi.org/project/pip-audit/)
Source: `apps/backend/.venv` installed dependencies

**Total: 98 known vulnerabilities across 12 packages.**

## Critical packages (CVE-published, requires action)

- **pypdf** `5.1.0`
  - vulns: 37
  - fix: 6.0.0, 6.1.3, 6.10.0, 6.10.1, 6.10.2, 6.12.0, 6.12.1, 6.12.2, 6.13.0, 6.13.1, 6.13.3, 6.14.0, 6.14.1, 6.14.2, 6.15.0, 6.4.0, 6.6.0, 6.6.2, 6.7.1, 6.7.2, 6.7.3, 6.7.4, 6.7.5, 6.8.0, 6.9.1, 6.9.2
  - sample IDs: PYSEC-2026-1833, PYSEC-2026-1829, PYSEC-2026-1832

- **pillow** `11.0.0`
  - vulns: 24
  - fix: 12.1.1, 12.2.0, 12.3.0
  - sample IDs: PYSEC-2026-165, PYSEC-2026-165, PYSEC-2026-2250

- **starlette** `0.41.3`
  - vulns: 9
  - fix: 0.47.2, 0.49.1, 1.0.1, 1.1.0, 1.3.0, 1.3.1
  - sample IDs: PYSEC-2026-161, PYSEC-2026-161, PYSEC-2026-248

- **strawberry-graphql** `0.253.1`
  - vulns: 7
  - fix: 0.257.0, 0.312.3, 0.315.7
  - sample IDs: PYSEC-2026-134, PYSEC-2026-133, PYSEC-2026-134

- **python-multipart** `0.0.20`
  - vulns: 6
  - fix: 0.0.22, 0.0.26, 0.0.27, 0.0.30, 0.0.31
  - sample IDs: PYSEC-2026-1852, PYSEC-2026-3038, PYSEC-2026-3037

- **python-jose** `3.3.0`
  - vulns: 5
  - fix: 3.4.0
  - sample IDs: PYSEC-2024-233, PYSEC-2024-232, PYSEC-2024-232

- **transformers** `4.57.6`
  - vulns: 5
  - fix: 5.0.0, 5.3.0, 5.5.0
  - sample IDs: PYSEC-2025-217, PYSEC-2026-2290, PYSEC-2026-2288

- **cryptography** `49.0.0`
  - vulns: 1
  - fix: 50.0.0
  - sample IDs: PYSEC-2026-3552

- **ecdsa** `0.19.2`
  - vulns: 1
  - sample IDs: PYSEC-2026-1325

- **pytest** `8.3.4`
  - vulns: 1
  - fix: 9.0.3
  - sample IDs: PYSEC-2026-1845

- **python-dotenv** `1.0.1`
  - vulns: 1
  - fix: 1.2.2
  - sample IDs: PYSEC-2026-2270

## Other vulnerable packages

- **pip** `26.1.2`: 1 vuln(s). fix: 26.2

## Что НЕ применять автоматически (разумный подход)

1. **Не делать auto-upgrade всех deps.** Этот проект закреплён на
   `cryptography 49.0.0` (production-ready). Полное обновление
   cryptography → 50.x сломает FastAPI/Starlette API.
2. **Применять только critical-security patches через pytest после upgrade.**
3. **Upgrade python-jose 3.3.0 → 3.4.0** — это изолированная правка,
   surgical, решает CVE-2024-232/233 (jwt parsing). Низкий риск.
4. **python-multipart 0.0.20 → 0.0.31** — multipart form parsing,
   dos prevention. Большие изменения внутри, нужна отдельная сессия.
5. **starlette 0.41 → 1.3.1** — крупное мажорное обновление, многие
   APIs изменились (request.url). Не этой сессии.
6. **transformers** — security update критичен (RCE), но это
   спринт отдельный — нужно review model loading paths.

## Что известно о нашем attack surface

- **starlette CVE-2026-48710**: path-based bypass через Host header.
  Mitigated если есть fronting proxy нормализующий Host.
- **transformers CVE-2026-4372**: RCE через `_attn_implementation_internal`.
  Mitigated если мы НЕ load'им untrusted HF Hub моделей runtime
  (мы embeddings precomputed при Sprint 70).
- **cryptography CVE-2026-69247**: Bleichenbacher oracle.
  Attack surface: только если используется pkcs7_decrypt_der/pem/smime
  (S/MIME gateway). Мы не используем.

## Вердикт для этой сессии

**Не выполнено upgrade ни одного production dep.** Audit зафиксирован.
Реально achievable в этой сессии upgrade:
- `python-jose 3.3.0 → 3.4.0` (5 CVEs, isolated) — atomically tested.
- `python-dotenv 1.0.1 → 1.2.2` (1 CVE, isolated).
Остальные требуют анализ зависимостей и regression
(starlette 1.x = broken Starlette APIs).
