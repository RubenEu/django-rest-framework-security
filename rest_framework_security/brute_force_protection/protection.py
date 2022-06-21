from django.core.cache import caches, DEFAULT_CACHE_ALIAS
from rest_framework_security.brute_force_protection import config
from rest_framework_security.brute_force_protection.exceptions import (
    BruteForceProtectionException,
    BruteForceProtectionBanException,
    BruteForceProtectionCaptchaException,
)

try:
    from redis_cache import RedisCache
except ImportError:
    RedisCache = None


cache = caches[DEFAULT_CACHE_ALIAS]


class BruteForceProtection:
    def __init__(self, ip):
        self.ip = ip

    def get_cache_attemps_key(self):
        return f"{config.BRUTE_FORCE_PROTECTION_CACHE_PREFIX}:failed:ip:{self.ip}"

    def get_cache_soft_key(self):
        return f"{config.BRUTE_FORCE_PROTECTION_CACHE_PREFIX}:soft:ip:{self.ip}"

    def get_attempts(self):
        return cache.get(self.get_cache_attemps_key(), default=0)

    def get_soft_status(self):
        return cache.get(self.get_cache_soft_key(), default=False)

    def set_soft_status(self, value: bool):
        """
        :value bool: True if the soft ban challenge has been overcome
        """
        cache.set(
            self.get_cache_soft_key(),
            value,
            config.BRUTE_FORCE_PROTECTION_SOFT_EXPIRATION,
        )

    def increase_attempts(self):
        key = self.get_cache_attemps_key()
        cache.add(key, 0, config.BRUTE_FORCE_PROTECTION_EXPIRATION)
        cache.incr(key)
        self.set_soft_status(False)

    def delete_ip(self):
        cache.delete(self.get_cache_attemps_key())
        cache.delete(self.get_cache_soft_key())

    def list_keys(self, pattern):
        if RedisCache is not None and isinstance(cache, RedisCache):
            return [
                x.decode("utf-8").split(":")[-1]
                for x in cache.get_master_client().keys(f":1:{pattern}")
            ]
        else:
            return []

    def list_failed_ips(self):
        return self.list_keys(
            f"{config.BRUTE_FORCE_PROTECTION_CACHE_PREFIX}:failed:ip:*"
        )

    def list_soft_ips(self):
        return self.list_keys(f"{config.BRUTE_FORCE_PROTECTION_CACHE_PREFIX}:soft:ip:*")

    def _get_hours_or_seconds_string(self, time: int) -> str:
        """Convert seconds to a string of number of hours or minutes with the format: ``2 hours`` or ``3900 seconds``.

        :param time: amount of seconds.
        :return: string of the amount of hours or seconds.
        """
        if time % 3600 == 0:
            return f'{time // 3600} hours'
        else:
            return f'{time} seconds'

    def validate(self, require_captcha_always: bool = False):
        attemps = self.get_attempts()
        # Bypass attempts validation if captcha is mandatory anyway.
        if require_captcha_always and not self.get_soft_status():
            raise BruteForceProtectionCaptchaException("Captcha is mandatory")
        if attemps >= config.BRUTE_FORCE_PROTECTION_BAN_LIMIT:
            amount_time = self._get_hours_or_seconds_string(config.BRUTE_FORCE_PROTECTION_EXPIRATION)
            raise BruteForceProtectionBanException(
                f"Your ip has been banned after several login attempts for {amount_time}."
            )
        if (
            attemps >= config.BRUTE_FORCE_PROTECTION_SOFT_LIMIT
            and not self.get_soft_status()
        ):
            raise BruteForceProtectionCaptchaException("Captcha is mandatory")
