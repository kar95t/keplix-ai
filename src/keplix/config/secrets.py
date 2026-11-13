"""3-Tier Secret Manager: Env Vars -> OS Keyring -> Masked HITL Prompt."""

import getpass
import os
from typing import Optional

try:
    import keyring
except ImportError:
    keyring = None  # type: ignore[assignment]


class SecretManager:
    """Manages secure resolution of API keys across 3 priority tiers:
    1. Process Environment Variables
    2. OS Encrypted Keyring (via Python keyring)
    3. Human-in-the-Loop (HITL) masked prompt
    """

    SERVICE_NAME = "keplix"

    def __init__(self, service_name: str = SERVICE_NAME) -> None:
        self.service_name = service_name

    def get_secret(
        self,
        key_name: str,
        prompt_user: bool = True,
        save_to_keyring: bool = True,
    ) -> Optional[str]:
        """Resolve a secret by key name across all 3 tiers."""
        # Tier 1: Environment Variables
        env_val = os.getenv(key_name)
        if env_val:
            return env_val

        # Tier 2: OS Encrypted Keyring
        if keyring is not None:
            try:
                keyring_val = keyring.get_password(self.service_name, key_name)
                if keyring_val:
                    return keyring_val
            except Exception:
                # Keyring backend may be unavailable or unsupported in headless environments
                pass

        # Tier 3: Masked HITL Prompt (if enabled)
        if prompt_user:
            try:
                from keplix.cli.console import console

                console.print(
                    f"[bold yellow]Secret '{key_name}' not found in environment or keyring.[/bold yellow]"
                )
                user_val = getpass.getpass(f"Enter value for {key_name} (input hidden): ").strip()
                if user_val:
                    if save_to_keyring and keyring is not None:
                        try:
                            keyring.set_password(self.service_name, key_name, user_val)
                            console.print(f"[dim]Stored {key_name} in OS Keyring for future runs.[/dim]")
                        except Exception:
                            pass
                    return user_val
            except (KeyboardInterrupt, EOFError):
                return None

        return None

    def store_secret(self, key_name: str, value: str) -> bool:
        """Explicitly store a secret in the OS Keyring."""
        if keyring is None:
            return False
        try:
            keyring.set_password(self.service_name, key_name, value)
            return True
        except Exception:
            return False

    def delete_secret(self, key_name: str) -> bool:
        """Remove a secret from the OS Keyring."""
        if keyring is None:
            return False
        try:
            keyring.delete_password(self.service_name, key_name)
            return True
        except Exception:
            return False


_global_secret_manager = SecretManager()


def get_secret(key_name: str, prompt_user: bool = True) -> Optional[str]:
    """Convenience helper to retrieve a secret via global SecretManager."""
    return _global_secret_manager.get_secret(key_name, prompt_user=prompt_user)

