# Copyright (c) 2022-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

import base64

# Action Chain namespace


class NamespaceActionChain:
    def __init__(self, api_test):
        self._api = api_test

    def list_chains(self):
        """Returns a list of all the action chain labels in the account."""
        result = self._api.call("actionchain.listChains")
        if result is None:
            return []
        return [x["label"] for x in result]

    def create_chain(self, label):
        """Creates a new action chain with the given label."""
        return self._api.call("actionchain.createChain", label)

    def delete_chain(self, label):
        """Deletes an action chain with the specified label."""
        return self._api.call("actionchain.deleteChain", label)

    def remove_action(self, label, action_id):
        """Removes an action from an action chain."""
        return self._api.call("actionchain.removeAction", label, action_id)

    def rename_chain(self, old_label, new_label):
        """Renames an action chain."""
        return self._api.call("actionchain.renameChain", old_label, new_label)

    def add_script_run(self, system, label, uid, gid, timeout, script):
        """Adds a script run action to the action chain."""
        encoded_script = base64.b64encode(script.encode()).decode()
        return self._api.call(
            "actionchain.addScriptRun",
            system,
            label,
            uid,
            gid,
            timeout,
            encoded_script,
        )

    def list_chain_actions(self, label):
        """Lists all the actions in a given chain."""
        return self._api.call("actionchain.listChainActions", label)

    def add_system_reboot(self, system, label):
        """Adds a system reboot action to the action chain."""
        return self._api.call("actionchain.addSystemReboot", system, label)

    def add_package_install(self, system, packages, label):
        """Adds a package install action to the action chain for the given system."""
        return self._api.call("actionchain.addPackageInstall", system, packages, label)

    def add_package_upgrade(self, system, packages, label):
        """Adds a package upgrade action to the action chain."""
        return self._api.call("actionchain.addPackageUpgrade", system, packages, label)

    def add_package_verify(self, system, packages, label):
        """Adds a package verify action to the action chain."""
        return self._api.call("actionchain.addPackageVerify", system, packages, label)

    def add_package_removal(self, system, packages, label):
        """Adds a package removal action to the action chain for the specified system."""
        return self._api.call("actionchain.addPackageRemoval", system, packages, label)

    def schedule_chain(self, label, earliest):
        """Schedules a chain to run at a specific time."""
        return self._api.call("actionchain.scheduleChain", label, earliest)
