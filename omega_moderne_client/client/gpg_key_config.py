import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GpgKeyConfig:
    key_passphrase: str
    key_private_key: str
    key_public_key: str

    @classmethod
    def load_from_env(cls) -> 'GpgKeyConfig':
        return GpgKeyConfig(
            key_passphrase=cls._load_env_variable("GPG_KEY_PASSPHRASE"),
            key_private_key=cls._load_env_variable("GPG_KEY_PRIVATE_KEY"),
            key_public_key=cls._load_env_variable("GPG_KEY_PUBLIC_KEY")
        )

    @staticmethod
    def _load_env_variable(env_name: str) -> str:
        env = os.getenv(env_name)
        if not env:
            raise Exception(f"{env_name} environment variable is not set")
        return env
