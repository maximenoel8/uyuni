# Copyright (c) 2022-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

# System namespace


class NamespaceSystem:
    def __init__(self, api_test):
        self._api = api_test
        self.config = NamespaceSystemConfig(api_test)
        self.custominfo = NamespaceSystemCustominfo(api_test)
        self.provisioning = NamespaceSystemProvisioning(api_test)
        self.scap = NamespaceSystemScap(api_test)
        self.search = NamespaceSystemSearch(api_test)

    def retrieve_server_id(self, server):
        """Retrieves the server ID for a given server name."""
        systems = self.list_systems()
        if systems is None:
            raise RuntimeError("Cannot list systems")
        matches = [s["id"] for s in systems if s["name"] == server]
        if not matches:
            raise RuntimeError(f"Cannot find {server}")
        return matches[0]

    def list_systems(self):
        """Lists all systems in the server."""
        return self._api.call("system.listSystems")

    def search_by_name(self, name):
        """Searches for a system based on its name."""
        return self._api.call("system.searchByName", name)

    def list_all_installable_packages(self, server):
        """Lists all the packages that can be installed on a server."""
        return self._api.call("system.listAllInstallablePackages", server)

    def delete_system(self, system_id):
        """Deletes a system profile via system.deleteSystem."""
        return self._api.call("system.deleteSystem", system_id)

    def delete_systems_by_name(self, names_to_delete):
        """Deletes a list of systems specified by their exact names."""
        all_systems = self.list_systems()
        deleted_systems = []
        for name in names_to_delete:
            system_to_delete = next(
                (s for s in all_systems if s["name"] == name), None
            )
            if system_to_delete:
                system_id = system_to_delete["id"]
                self.delete_system(system_id)
                deleted_systems.append({"name": name, "id": system_id})
        return deleted_systems

    def list_latest_upgradable_packages(self, server):
        """Lists the packages that are upgradable on a given server."""
        return self._api.call("system.listLatestUpgradablePackages", server)

    def bootstrap_system(self, host, activation_key, salt_ssh, proxy_id=None):
        """Bootstraps a system. Optionally uses a proxy."""
        if proxy_id is None:
            return self._api.call(
                "system.bootstrap",
                host,
                22,
                "root",
                "linux",
                activation_key,
                salt_ssh,
            )
        return self._api.call(
            "system.bootstrap",
            host,
            22,
            "root",
            "linux",
            activation_key,
            proxy_id,
            salt_ssh,
        )

    def schedule_apply_highstate(self, server, date, test):
        """Schedules a highstate to be applied to a server at a given date."""
        return self._api.call(
            "system.scheduleApplyHighstate", server, date, test
        )

    def schedule_package_refresh(self, server, date):
        """Schedules a package refresh on a server."""
        return self._api.call("system.schedulePackageRefresh", server, date)

    def schedule_reboot(self, server, date):
        """Schedules a reboot for a server on a specific date."""
        return self._api.call("system.scheduleReboot", server, date)

    def schedule_script_run(self, server, uid, gid, timeout, script, date):
        """Schedules a script to run on a server at a specified date and time."""
        return self._api.call(
            "system.scheduleScriptRun",
            server,
            uid,
            gid,
            timeout,
            script,
            date,
        )

    def create_system_record(self, name, kslabel, koptions, comment, netdevices):
        """Creates a Cobbler system record for a system not registered on the MLM server."""
        return self._api.call(
            "system.createSystemRecord",
            name,
            kslabel,
            koptions,
            comment,
            netdevices,
        )

    def create_system_record_with_sid(self, sid, kslabel):
        """Creates a Cobbler system record with the specified kickstart label."""
        return self._api.call("system.createSystemRecord", sid, kslabel)

    def create_system_profile(self, name, data):
        """Creates a system profile with the given name and data."""
        return self._api.call("system.createSystemProfile", name, data)

    def list_empty_system_profiles(self):
        """Lists system profiles that have no systems assigned to them."""
        return self._api.call("system.listEmptySystemProfiles")

    def obtain_reactivation_key(self, server):
        """Gets the reactivation key of a server."""
        return self._api.call("system.obtainReactivationKey", server)

    def set_variables(self, server, variables):
        """Sets a list of kickstart variables in the Cobbler system record for the specified server."""
        return self._api.call("system.setVariables", server, True, variables)

    def get_system_errata(self, system_id):
        """Returns a list of all errata that are relevant to the system with the given SID."""
        return self._api.call("system.getRelevantErrata", system_id)

    def get_systems_errata(self, system_ids):
        """Returns a list of all errata that are relevant to the systems with the given SIDs."""
        return self._api.call("system.getRelevantErrata", system_ids)

    def get_event_history(self, system_id, offset, limit):
        """Returns the event history for a system."""
        return self._api.call("system.getEventHistory", system_id, offset, limit)

    def get_event_details(self, system_id, event_id):
        """Returns the event details for a system."""
        return self._api.call("system.getEventDetails", system_id, event_id)


class NamespaceSystemConfig:
    def __init__(self, api_test):
        self._api = api_test

    def remove_channels(self, servers, channels):
        """Removes the specified channels from the specified servers."""
        return self._api.call("system.config.removeChannels", servers, channels)


class NamespaceSystemCustominfo:
    def __init__(self, api_test):
        self._api = api_test

    def create_key(self, value, desc):
        """Creates a custom info key."""
        return self._api.call("system.custominfo.createKey", value, desc)


class NamespaceSystemProvisioning:
    def __init__(self, api_test):
        self._api = api_test
        self.powermanagement = NamespaceSystemProvisioningPowermanagement(api_test)


class NamespaceSystemProvisioningPowermanagement:
    def __init__(self, api_test):
        self._api = api_test

    def list_types(self):
        """Lists the power management types available for a given system."""
        return self._api.call("system.provisioning.powermanagement.listTypes")

    def get_details(self, server):
        """Returns the power management details of a server."""
        return self._api.call(
            "system.provisioning.powermanagement.getDetails", server
        )

    def get_status(self, server):
        """Returns the power status of a server."""
        return self._api.call(
            "system.provisioning.powermanagement.getStatus", server
        )

    def set_details(self, server, data):
        """Sets the power management details for a server."""
        return self._api.call(
            "system.provisioning.powermanagement.setDetails", server, data
        )

    def power_on(self, server):
        """Powers on a server."""
        return self._api.call(
            "system.provisioning.powermanagement.powerOn", server
        )

    def power_off(self, server):
        """Powers off a server."""
        return self._api.call(
            "system.provisioning.powermanagement.powerOff", server
        )

    def reboot(self, server):
        """Reboots a server."""
        return self._api.call(
            "system.provisioning.powermanagement.reboot", server
        )


class NamespaceSystemScap:
    def __init__(self, api_test):
        self._api = api_test

    def list_xccdf_scans(self, server):
        """Lists all XCCDF scans for a given server."""
        return self._api.call("system.scap.listXccdfScans", server)


class NamespaceSystemSearch:
    def __init__(self, api_test):
        self._api = api_test

    def hostname(self, server):
        """Takes a server name as an argument and returns the hostname of the server."""
        return self._api.call("system.search.hostname", server)
