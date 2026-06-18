# Copyright (c) 2024 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/support/keyvalue_store.rb.

Provides KeyValueStore: a thin wrapper around a Redis client that exposes
Set-oriented operations (add / get / remove) with optional database selection.
"""

try:
    import redis
except ImportError:  # optional dependency — not available in all environments
    redis = None  # type: ignore[assignment]


class KeyValueStore:
    """Key-Value Store backed by Redis."""

    def __init__(self, host, port, username, password):
        """
        Initialize a connection with the Redis database.

        :param host: hostname of the Redis server
        :param port: port of the Redis server
        :param username: username for authentication
        :param password: password for authentication
        :raises ValueError: if any required parameter is missing or empty
        """
        if not host or not port or not username or not password:
            raise ValueError(
                "All Redis parameters required: host, port, username, password")
        if redis is None:
            raise RuntimeError(
                "redis package is not installed. "
                "Add redis>=5.0 to the project dependencies.")
        try:
            self._client = redis.Redis(
                host=host,
                port=int(port),
                username=username,
                password=password,
                decode_responses=True,
            )
        except Exception as e:
            import warnings
            warnings.warn(f"Error initializing KeyValueStore: {e}")
            raise

    def close(self):
        """Close the connection with the Redis database."""
        try:
            self._client.close()
        except Exception:
            pass

    def add(self, key: str, value: str, database: int = 0):
        """
        Add a value to the Set stored at key.

        :param key: the key whose Set to add to
        :param value: the value to add
        :param database: optional Redis database index (default: 0)
        :raises Exception: re-raises on Redis errors
        """
        try:
            self._client.select(database)
            self._client.sadd(key, value)
        except Exception as e:
            import warnings
            warnings.warn(f"Error adding a key-value: {e}")
            raise

    def get(self, key: str, database: int = 0) -> set:
        """
        Return all members of the Set stored at key.

        :param key: the key to read from
        :param database: optional Redis database index (default: 0)
        :return: set of member strings (empty set on error)
        :raises Exception: re-raises on Redis errors
        """
        try:
            self._client.select(database)
            return self._client.smembers(key)
        except Exception as e:
            import warnings
            warnings.warn(f"Error getting a key-value: {e}")
            raise

    def remove(self, key: str, value: str, database: int = 0) -> int:
        """
        Remove a value from the Set stored at key.

        :param key: the key whose Set to remove from
        :param value: the value to remove
        :param database: optional Redis database index (default: 0)
        :return: number of members removed
        :raises Exception: re-raises on Redis errors
        """
        try:
            self._client.select(database)
            return self._client.srem(key, value)
        except Exception as e:
            import warnings
            warnings.warn(f"Error removing a key-value: {e}")
            raise
