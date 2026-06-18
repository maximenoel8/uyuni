# Copyright (c) 2022-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

# Activation Key namespace


class NamespaceActivationKey:
    def __init__(self, api_test):
        self._api = api_test
        self._keys = None

    def create(self, id, descr, base_channel, limit):
        """Creates an activation key."""
        return self._api.call(
            "activationkey.create",
            id,
            descr,
            base_channel,
            limit,
            [],
            False,
        )

    def delete(self, id):
        """Deletes an activation key."""
        result = self._api.call("activationkey.delete", id)
        self._keys = self._api.call("activationkey.listActivationKeys")
        return result

    def get_activation_keys_count(self):
        """Returns the number of activation keys."""
        self._keys = self._api.call("activationkey.listActivationKeys")
        return 0 if self._keys is None else len(self._keys)

    def get_activated_systems_count(self, id):
        """Returns the number of activated systems for a given activation key."""
        systems = self._api.call("activationkey.listActivatedSystems", id)
        return 0 if systems is None else len(systems)

    def get_config_channels_count(self, id):
        """Returns the number of channels in the configuration with the given ID."""
        channels = self._api.call("activationkey.listConfigChannels", id)
        return 0 if channels is None else len(channels)

    def verified(self, id):
        """Checks if the activation key with the given ID exists and is active."""
        keys = self._api.call("activationkey.listActivationKeys")
        if keys is None:
            return False
        return id in [key["key"] for key in keys]

    def add_config_channels(self, id, config_channels):
        """Adds configuration channels to an activation key."""
        return self._api.call(
            "activationkey.addConfigChannels", id, config_channels, False
        )

    def add_child_channels(self, id, child_channels):
        """Adds child channels to an activation key."""
        return self._api.call("activationkey.addChildChannels", id, child_channels)

    def get_details(self, id):
        """Returns the details of an activation key."""
        return self._api.call("activationkey.getDetails", id)

    def details_set(self, id, description, base_channel_label, usage_limit, contact_method):
        """Sets the details of an activation key. Returns True if successful."""
        details = {
            "description": description,
            "base_channel_label": base_channel_label,
            "usage_limit": usage_limit,
            "universal_default": False,
            "contact_method": contact_method,
        }
        result = self._api.call("activationkey.setDetails", id, details)
        return int(result) == 1

    def set_entitlement(self, id, entitlements):
        """Sets the entitlements of an activation key."""
        return self._api.call("activationkey.addEntitlements", id, entitlements)
