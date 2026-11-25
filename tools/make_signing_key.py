#!/usr/bin/env python3
"""Один раз создать локальный ключ подписи Щитка 2; существующий ключ не заменяется."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "keys" / "shchitok2.p12"
if OUT.exists():
    raise SystemExit("Ключ уже существует; отказываюсь его заменять: " + str(OUT))
OUT.parent.mkdir(parents=True, exist_ok=True)
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
name = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "Shchitok 2")])
now = datetime.now(timezone.utc)
cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=10950)).add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256()))
blob = pkcs12.serialize_key_and_certificates(b"shchitok2", key, cert, None, serialization.BestAvailableEncryption(b"android"))
OUT.write_bytes(blob)
fingerprint = ":".join(f"{b:02X}" for b in sha256(cert.public_bytes(serialization.Encoding.DER)).digest())
print("Создан ключ:", OUT)
print("SHA-256 сертификата:", fingerprint)
print("Не публикуйте ключ и сохраните отдельную резервную копию.")
