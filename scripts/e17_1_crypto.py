"""
E17.1 — AES-256-GCM para backups (.db → .beaba.enc).

Chave: variável BEABA_BACKUP_KEY — base64 (32 bytes) ou hex (64 caracteres).
"""

from __future__ import annotations

import base64
import binascii
import os
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"BEA1"
VERSION = 1
AAD = b"beaba-backup-v1"


def parse_backup_key() -> bytes:
    raw = os.environ.get("BEABA_BACKUP_KEY", "").strip()
    if not raw:
        raise ValueError("BEABA_BACKUP_KEY ausente ou vazio")
    try:
        key = base64.b64decode(raw, validate=True)
    except binascii.Error:
        try:
            key = bytes.fromhex(raw)
        except ValueError:
            # Fallback: permite uma "password" comum em BEABA_BACKUP_KEY.
            # Derivação determinística para 32 bytes (AES-256): SHA-256(utf8(raw)).
            key = hashlib.sha256(raw.encode("utf-8")).digest()
    if len(key) != 32:
        raise ValueError("BEABA_BACKUP_KEY deve decodificar para exactamente 32 bytes (AES-256)")
    return key


def encrypt_file(path_in: Path, path_out: Path, key: bytes) -> None:
    pt = path_in.read_bytes()
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, pt, AAD)
    path_out.parent.mkdir(parents=True, exist_ok=True)
    path_out.write_bytes(MAGIC + bytes([VERSION]) + nonce + ct)


def decrypt_file(path_in: Path, path_out: Path, key: bytes) -> None:
    raw = path_in.read_bytes()
    if len(raw) < 4 + 1 + 12 + 16:
        raise ValueError("ficheiro encriptado demasiado curto")
    if raw[:4] != MAGIC:
        raise ValueError("magic BEA1 inválido")
    if raw[4] != VERSION:
        raise ValueError(f"versão não suportada: {raw[4]}")
    nonce = raw[5:17]
    ct = raw[17:]
    aes = AESGCM(key)
    pt = aes.decrypt(nonce, ct, AAD)
    path_out.parent.mkdir(parents=True, exist_ok=True)
    path_out.write_bytes(pt)
