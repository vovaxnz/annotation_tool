import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

from api_requests import load_public_key
from config import settings


class RSAEncryption:

    public_key_pem_filename = f"public_key.pem"

    @property
    def public_key_filepath(self) -> Path:
        return Path(os.path.join(settings.data_dir, self.public_key_pem_filename))

    def encrypt(self, data: str) -> str:
        public_key = self.get_public_key()
        encrypted_data = public_key.encrypt(
            data.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        encrypted_data_b64 = base64.urlsafe_b64encode(encrypted_data).decode("ascii")
        return encrypted_data_b64

    def save_public_key(self, public_key_pem: str):
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.public_key_filepath.write_bytes(public_key_bytes)

    def get_public_key(self):
        if os.path.exists(self.public_key_filepath):
            public_key_bytes = self.public_key_filepath.read_bytes()
            try:
                public_key = serialization.load_pem_public_key(public_key_bytes)
            except ValueError as e:
                raise ValueError("Invalid public key format") from e

        else:
            public_key_pem = load_public_key()
            public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            self.save_public_key(public_key_pem=public_key_pem)

        return public_key

encryptor = RSAEncryption()
