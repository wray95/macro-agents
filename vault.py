"""Encryption at rest for local data (authenticated Fernet: AES-128-CBC + HMAC-SHA256).

Key sources, strongest first:
  1. MACRO_AGENTS_PASSPHRASE env var -> key derived with scrypt (salt stored beside the data).
     Nothing secret is written to disk, so a stolen copy of the folder is useless without it.
  2. Otherwise a random key file (mode 0600) is created next to the database. This protects
     against casual reads and accidental commits, but not against someone who copies the whole folder.
"""
import base64
import hashlib
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

PREFIX = "enc:v1:"


def _write_private(path: Path, data: bytes):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)


def private_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _fernet(directory: Path) -> Fernet:
    private_dir(directory)
    passphrase = os.getenv("MACRO_AGENTS_PASSPHRASE")
    if passphrase:
        salt_file = directory / ".salt"
        if not salt_file.exists():
            _write_private(salt_file, os.urandom(16))
        salt = salt_file.read_bytes()
        raw = hashlib.scrypt(passphrase.encode(), salt=salt, n=2**15, r=8, p=1, dklen=32, maxmem=64 * 1024 * 1024)
        return Fernet(base64.urlsafe_b64encode(raw))
    key_file = directory / ".key"
    if not key_file.exists():
        try:
            _write_private(key_file, Fernet.generate_key())
        except FileExistsError:
            pass
    return Fernet(key_file.read_bytes().strip())


def encrypt(text: str, directory: Path) -> str:
    return PREFIX + _fernet(directory).encrypt(text.encode()).decode()


def decrypt(value: str, directory: Path) -> str:
    """Decrypt a stored value; legacy plaintext (no prefix) is returned unchanged."""
    if not value.startswith(PREFIX):
        return value
    try:
        return _fernet(directory).decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken:
        raise ValueError("Cannot decrypt data: wrong passphrase/key, or the data was tampered with") from None


def is_encrypted(value: str) -> bool:
    return value.startswith(PREFIX)
