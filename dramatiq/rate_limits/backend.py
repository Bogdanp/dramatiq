class RateLimiterBackend:
    """ABC for rate limiter backends.
    """

    def add(self, key, value, ttl):  # pragma: no cover
        """Add a key to the backend iff it doesn't exist.

        Parameters:
          key(str): The key to add.
          value(int): The value to add.
          ttl(int): The max amount of time in milliseconds the key can
            live in the backend for.
        """
        raise NotImplementedError

    def incr(self, key, amount, maximum, ttl):  # pragma: no cover
        """Atomically increment a key in the backend up to the given
        maximum.

        Parameters:
          key(str): The key to increment.
          amount(int): The amount to increment the value by.
          maximum(int): The maximum amount the value can have.
          ttl(int): The max amount of time in milliseconds the key can
            live in the backend for.

        Returns:
          bool: True if the key was successfully incremented.
        """
        raise NotImplementedError

    def decr(self, key, amount, minimum, ttl):  # pragma: no cover
        """Atomically decrement a key in the backend up to the given
        maximum.

        Parameters:
          key(str): The key to decrement.
          amount(int): The amount to decrement the value by.
          minimum(int): The minimum amount the value can have.
          ttl(int): The max amount of time in milliseconds the key can
            live in the backend for.

        Returns:
          bool: True if the key was successfully decremented.
        """
        raise NotImplementedError

    def incr_and_sum(self, key, keys, amount, maximum, ttl):  # pragma: no cover
        """Atomically increment a key and return the sum of a set of
        keys, unless the sum is greater than the given maximum.

        Parameters:
          key(str): The key to increment.
          amount(int): The amount to decrement the value by.
          maximum(int): The maximum sum of the keys.
          ttl(int): The max amount of time in milliseconds the key can
            live in the backend for.

        Returns:
          bool: True if the key was successfully incremented.
        """
        raise NotImplementedError
