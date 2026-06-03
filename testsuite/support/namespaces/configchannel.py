# Copyright (c) 2022-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

# Config Channel namespace


class NamespaceConfigChannel:
    def __init__(self, api_test):
        self._api = api_test

    def channel_exists(self, channel):
        """Checks if the configuration channel exists."""
        return self._api.call("configchannel.channelExists", channel)

    def list_files(self, channel):
        """Lists the files in a configuration channel."""
        return self._api.call("configchannel.listFiles", channel)

    def list_subscribed_systems(self, channel):
        """Returns a list of systems subscribed to the given configuration channel."""
        return self._api.call("configchannel.listSubscribedSystems", channel)

    def get_file_revision(self, channel, file_path, revision):
        """Gets a file revision of a configuration channel."""
        return self._api.call(
            "configchannel.getFileRevision", channel, file_path, revision
        )

    def create(self, label, name, description, type):
        """Creates a new configuration channel."""
        return self._api.call(
            "configchannel.create", label, name, description, type
        )

    def create_with_pathinfo(self, label, name, description, type, info):
        """Creates a new configuration channel with path information."""
        return self._api.call(
            "configchannel.create", label, name, description, type, info
        )

    def create_or_update_path(self, channel, file, contents):
        """Creates or updates a file in a configuration channel."""
        path_info = {
            "contents": contents,
            "owner": "root",
            "group": "root",
            "permissions": "644",
        }
        return self._api.call(
            "configchannel.createOrUpdatePath",
            channel,
            file,
            False,
            path_info,
        )

    def deploy_all_systems(self, channel):
        """Deploys all systems to the given configuration channel."""
        return self._api.call("configchannel.deployAllSystems", channel)

    def delete_channels(self, channels):
        """Deletes the specified configuration channels."""
        return self._api.call("configchannel.deleteChannels", channels)
