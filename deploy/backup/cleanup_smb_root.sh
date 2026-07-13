#!/bin/bash
SMB_CREDS=/root/.ai-tutor-secrets/smb.creds
# Файлы имеют атрибут "A" (только archive), директории — "D" или "DA" или "DAS".
# Нужны только файлы (строка начинается с имени файла и в колонке атрибутов есть A без D).
smbclient //192.168.1.91/Kirill-AI -A "$SMB_CREDS" -c "ls" 2>/dev/null | \
  awk '/^[[:space:]]+[A-Za-z0-9_.-]+[[:space:]]+A[[:space:]]+[0-9]+/ {print $1}' | \
  while read f; do
    [ -z "$f" ] && continue
    case "$f" in
      .|..) continue ;;
    esac
    smbclient //192.168.1.91/Kirill-AI -A "$SMB_CREDS" -c "del $f" >/dev/null 2>&1 && echo "deleted: $f"
  done