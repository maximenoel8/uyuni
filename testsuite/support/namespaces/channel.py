# Copyright (c) 2022-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

# Channel namespace


class NamespaceChannel:
    def __init__(self, api_test):
        self._api = api_test
        self.software = NamespaceChannelSoftware(api_test)
        self.appstreams = NamespaceChannelAppstreams(api_test)

    def get_software_channels_count(self):
        """Returns the number of software channels in the system."""
        channels = self._api.call("channel.listSoftwareChannels")
        return 0 if channels is None else len(channels)

    def channel_verified(self, label):
        """Checks if a channel with the given label exists. Returns True if valid."""
        channels = self._api.call("channel.listSoftwareChannels")
        if channels is None:
            return False
        return label in [c["label"] for c in channels]

    def list_all_channels(self):
        """Lists all channels in the system as a dict keyed by label."""
        channels = self._api.call("channel.listAllChannels")
        if channels is None:
            return {}
        return {
            channel["label"]: {
                "id": channel["id"],
                "name": channel["name"],
                "provider_name": channel.get("provider_name"),
                "packages": channel.get("packages"),
                "systems": channel.get("systems"),
                "arch_name": channel.get("arch_name"),
            }
            for channel in channels
        }

    def list_software_channels(self):
        """Lists the labels of all software channels in the system."""
        channels = self._api.call("channel.listSoftwareChannels")
        if channels is None:
            return []
        return [channel["label"] for channel in channels]


class NamespaceChannelSoftware:
    def __init__(self, api_test):
        self._api = api_test

    def create(self, label, name, summary, arch, parent):
        """Creates a new software channel."""
        return self._api.call(
            "channel.software.create", label, name, summary, arch, parent
        )

    def delete(self, label):
        """Deletes the channel with the given label."""
        return self._api.call("channel.software.delete", label)

    def create_repo(self, label, url, type="yum"):
        """Creates a new repository with the given label and URL."""
        return self._api.call("channel.software.createRepo", label, type, url)

    def associate_repo(self, channel_label, repo_label):
        """Associates a repository with a channel."""
        return self._api.call(
            "channel.software.associateRepo", channel_label, repo_label
        )

    def remove_repo(self, label):
        """Removes a repository."""
        return self._api.call("channel.software.removeRepo", label)

    def parent_channel(self, child, parent):
        """Verifies if a given channel is a child of the given parent channel."""
        channel = self._api.call("channel.software.getDetails", child)
        return channel.get("parent_channel_label") == parent

    def get_details(self, label):
        """Gets the details of a channel with the given label."""
        return self._api.call("channel.software.getDetails", label)

    def list_child_channels(self, parent_channel):
        """Lists the child channels for a given parent channel."""
        channels = self._api.call("channel.listSoftwareChannels")
        if channels is None:
            return []
        channel_labels = [channel["label"] for channel in channels]
        return [c for c in channel_labels if self.parent_channel(c, parent_channel)]

    def list_user_repos(self):
        """Lists all the repos that the user has access to."""
        repos = self._api.call("channel.software.listUserRepos")
        if repos is None:
            return []
        return [key["label"] for key in repos]

    def list_system_channels(self, system_id):
        """Lists the names of channels the system with the given system ID is subscribed to."""
        channels = self._api.call("channel.software.listSystemChannels", system_id)
        if channels is None:
            return []
        return [channel["name"] for channel in channels]


class NamespaceChannelAppstreams:
    def __init__(self, api_test):
        self._api = api_test

    def modular(self, label):
        """Checks if channel is modular. Returns True if modular, False otherwise."""
        return self._api.call("channel.appstreams.isModular", label)

    def list_modular_channels(self):
        """Lists modular channels in the user's organization."""
        channels = self._api.call("channel.appstreams.listModular")
        if channels is None:
            return []
        return [channel["name"] for channel in channels]

    def list_module_streams(self, label):
        """Lists available module streams for a given channel."""
        return self._api.call("channel.appstreams.listModuleStreams", label)
