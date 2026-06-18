# Copyright (c) 2022-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

# Kickstart namespace


class NamespaceKickstart:
    def __init__(self, api_test):
        self._api = api_test
        self.tree = NamespaceKickstartTree(api_test)
        self.profile = NamespaceKickstartProfile(api_test)

    def create_profile(self, name, kstreelabel, kshost):
        """Creates a new kickstart profile using the default download URL."""
        return self._api.call(
            "kickstart.profile.createProfile",
            name,
            "none",
            kstreelabel,
            kshost,
            "linux",
            "all",
        )

    def create_profile_using_import_file(self, name, kstreelabel, filename):
        """Imports a raw kickstart file into the product."""
        with open(filename, "r") as f:
            file_content = f.read()
        return self._api.call(
            "kickstart.importRawFile",
            name,
            "none",
            kstreelabel,
            file_content,
        )


class NamespaceKickstartProfile:
    def __init__(self, api_test):
        self._api = api_test

    def set_variables(self, profile, variables):
        """Associates a list of kickstart variables with the specified kickstart profile."""
        return self._api.call("kickstart.profile.setVariables", profile, variables)


class NamespaceKickstartTree:
    def __init__(self, api_test):
        self._api = api_test

    def create_distro(self, distro, path, label, install):
        """Creates a Kickstart tree (Distribution)."""
        return self._api.call(
            "kickstart.tree.create", distro, path, label, install
        )

    def create_distro_w_kernel_options(
        self, distro, path, label, install, options, post_options
    ):
        """Creates a Kickstart tree (Distribution) with kernel options."""
        return self._api.call(
            "kickstart.tree.create",
            distro,
            path,
            label,
            install,
            options,
            post_options,
        )

    def update_distro(self, distro, path, label, install, options, post_options):
        """Updates a Kickstart tree (Distribution)."""
        return self._api.call(
            "kickstart.tree.update",
            distro,
            path,
            label,
            install,
            options,
            post_options,
        )

    def delete_tree_and_profiles(self, distro):
        """Deletes a Kickstart tree and all profiles associated with it."""
        return self._api.call("kickstart.tree.deleteTreeAndProfiles", distro)
