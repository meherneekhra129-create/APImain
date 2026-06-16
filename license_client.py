"""
License Client Library
======================
Drop this file into your Python project to validate license keys
against your License Key Manager API.

Usage:
    from license_client import LicenseClient

    client = LicenseClient("https://your-api.onrender.com")
    
    if client.activate("LIC-ABCD-1234-EFGH-5678"):
        print("License activated! Running app...")
        # Your app code here
    else:
        print("Invalid license key. Please purchase a valid key.")
        exit()
"""

import hashlib
import json
import os
import platform
import sys
import time
import urllib.request
import urllib.error


class LicenseError(Exception):
    """Base exception for license errors."""
    pass


class LicenseExpiredError(LicenseError):
    """Raised when the license key has expired."""
    pass


class LicenseRevokedError(LicenseError):
    """Raised when the license key has been revoked."""
    pass


class LicenseInvalidError(LicenseError):
    """Raised when the license key is invalid."""
    pass


class HWIDMismatchError(LicenseError):
    """Raised when the hardware ID doesn't match."""
    pass


class LicenseClient:
    """
    Client for validating license keys against the License Key Manager API.
    
    Args:
        api_url (str): Base URL of your License Key Manager API.
                       Example: "https://your-app.onrender.com"
        hwid_lock (bool): If True, binds the license to this machine's hardware ID.
                          Default: True
        cache_hours (int): Hours to cache a valid license locally (for offline use).
                           Set to 0 to disable caching. Default: 24
        timeout (int): Request timeout in seconds. Default: 10
    """

    def __init__(self, api_url: str, hwid_lock: bool = True, cache_hours: int = 24, timeout: int = 10):
        self.api_url = api_url.rstrip("/")
        self.hwid_lock = hwid_lock
        self.cache_hours = cache_hours
        self.timeout = timeout
        self._cache_dir = os.path.join(os.path.expanduser("~"), ".license_cache")
        self._license_key = None
        self._is_valid = False
        self._status = None
        self._expires_at = None
        self._message = None

    @property
    def is_valid(self) -> bool:
        """Whether the last validation was successful."""
        return self._is_valid

    @property
    def status(self) -> str:
        """Status from the last validation (active/expired/revoked/invalid)."""
        return self._status or "unknown"

    @property
    def expires_at(self) -> str:
        """Expiry date from the last validation."""
        return self._expires_at

    @property
    def message(self) -> str:
        """Message from the last validation."""
        return self._message or ""

    def get_hwid(self) -> str:
        """
        Generate a hardware ID based on the machine's characteristics.
        Uses a combination of platform info to create a unique identifier.
        """
        raw_parts = [
            platform.node(),           # Computer name
            platform.machine(),        # Machine type
            platform.processor(),      # Processor info
            platform.system(),         # OS name
            str(os.cpu_count()),       # CPU count
        ]

        # Try to get MAC address
        try:
            import uuid
            mac = uuid.getnode()
            raw_parts.append(str(mac))
        except Exception:
            pass

        raw_string = "|".join(raw_parts)
        return hashlib.sha256(raw_string.encode()).hexdigest()[:32]

    def activate(self, license_key: str) -> bool:
        """
        Validate and activate a license key.
        
        Args:
            license_key (str): The license key to validate.
            
        Returns:
            bool: True if the key is valid, False otherwise.
            
        Raises:
            LicenseExpiredError: If the key has expired.
            LicenseRevokedError: If the key has been revoked.
            LicenseInvalidError: If the key is not found.
            HWIDMismatchError: If the hardware ID doesn't match.
        """
        self._license_key = license_key.strip()

        # Try online validation first
        try:
            result = self._validate_online()
            if result:
                self._save_cache()
            return result
        except (urllib.error.URLError, ConnectionError, OSError) as e:
            # Network error — try cached validation
            print(f"[License] Network error: {e}. Checking cached validation...")
            return self._validate_cached()

    def check(self, license_key: str) -> bool:
        """
        Silently check if a license key is valid without raising exceptions.
        
        Args:
            license_key (str): The license key to check.
            
        Returns:
            bool: True if valid, False otherwise.
        """
        try:
            return self.activate(license_key)
        except LicenseError:
            return False

    def _validate_online(self) -> bool:
        """Validate the license key against the API server."""
        payload = {
            "license_key": self._license_key,
        }

        if self.hwid_lock:
            payload["hwid"] = self.get_hwid()

        data = json.dumps(payload).encode("utf-8")
        url = f"{self.api_url}/api/validate"

        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                result = json.loads(body)
            except json.JSONDecodeError:
                raise LicenseError(f"Server error ({e.code}): {body}")

        self._is_valid = result.get("valid", False)
        self._status = result.get("status", "unknown")
        self._expires_at = result.get("expires_at")
        self._message = result.get("message", "")

        if self._is_valid:
            return True

        # Raise specific errors based on status
        status = self._status
        message = self._message

        if status == "expired":
            raise LicenseExpiredError(message or "License key has expired.")
        elif status == "revoked":
            raise LicenseRevokedError(message or "License key has been revoked.")
        elif status == "hwid_mismatch":
            raise HWIDMismatchError(message or "This key is bound to a different machine.")
        else:
            raise LicenseInvalidError(message or "Invalid license key.")

    def _validate_cached(self) -> bool:
        """Check the local cache for a previously validated key."""
        if self.cache_hours <= 0:
            self._is_valid = False
            self._message = "No network connection and caching is disabled."
            return False

        cache_file = self._get_cache_path()

        if not os.path.exists(cache_file):
            self._is_valid = False
            self._message = "No cached validation found. Please connect to the internet."
            return False

        try:
            with open(cache_file, "r") as f:
                cache_data = json.load(f)

            # Verify cache integrity
            expected_hash = self._compute_cache_hash(cache_data.get("key", ""), cache_data.get("timestamp", 0))
            if cache_data.get("hash") != expected_hash:
                self._is_valid = False
                self._message = "Cache integrity check failed."
                os.remove(cache_file)
                return False

            # Check cache expiry
            cache_age_hours = (time.time() - cache_data["timestamp"]) / 3600
            if cache_age_hours > self.cache_hours:
                self._is_valid = False
                self._message = f"Cached validation expired ({int(cache_age_hours)}h ago). Please connect to the internet."
                return False

            # Check HWID match
            if self.hwid_lock and cache_data.get("hwid") != self.get_hwid():
                self._is_valid = False
                self._message = "Hardware ID mismatch in cache."
                return False

            # Check key match
            if cache_data.get("key") != self._license_key:
                self._is_valid = False
                self._message = "Cached key doesn't match."
                return False

            self._is_valid = True
            self._status = "active"
            self._expires_at = cache_data.get("expires_at")
            self._message = f"Validated from cache (cached {int(cache_age_hours)}h ago)."
            return True

        except (json.JSONDecodeError, KeyError, IOError):
            self._is_valid = False
            self._message = "Cache file corrupted. Please connect to the internet."
            return False

    def _save_cache(self):
        """Save successful validation to local cache."""
        if self.cache_hours <= 0:
            return

        os.makedirs(self._cache_dir, exist_ok=True)
        cache_file = self._get_cache_path()

        timestamp = time.time()
        cache_data = {
            "key": self._license_key,
            "hwid": self.get_hwid() if self.hwid_lock else None,
            "timestamp": timestamp,
            "expires_at": self._expires_at,
            "hash": self._compute_cache_hash(self._license_key, timestamp),
        }

        try:
            with open(cache_file, "w") as f:
                json.dump(cache_data, f)
        except IOError:
            pass  # Silently fail if we can't write cache

    def _get_cache_path(self) -> str:
        """Get the cache file path for the current license key."""
        key_hash = hashlib.md5(self._license_key.encode()).hexdigest()
        return os.path.join(self._cache_dir, f".lc_{key_hash}")

    def _compute_cache_hash(self, key: str, timestamp: float) -> str:
        """Compute integrity hash for cache data."""
        raw = f"{key}:{timestamp}:{self.api_url}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def __repr__(self):
        return (
            f"LicenseClient(api_url='{self.api_url}', "
            f"valid={self._is_valid}, status='{self.status}')"
        )


# ─── Quick usage example ─────────────────────────────────────────────────────

if __name__ == "__main__":
    # Replace with your API URL and license key
    API_URL = "https://your-app.onrender.com"
    LICENSE_KEY = "LIC-XXXX-XXXX-XXXX-XXXX"

    client = LicenseClient(API_URL)

    try:
        if client.activate(LICENSE_KEY):
            print(f"✅ License valid! Status: {client.status}")
            if client.expires_at:
                print(f"   Expires: {client.expires_at}")
            print("   Starting application...")
            # --- Your application code here ---
        else:
            print(f"❌ License invalid: {client.message}")
            sys.exit(1)
    except LicenseExpiredError:
        print("❌ Your license has expired. Please renew.")
        sys.exit(1)
    except LicenseRevokedError:
        print("❌ Your license has been revoked. Contact support.")
        sys.exit(1)
    except HWIDMismatchError:
        print("❌ This license is registered to a different machine.")
        sys.exit(1)
    except LicenseError as e:
        print(f"❌ License error: {e}")
        sys.exit(1)
