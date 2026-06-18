# Copyright (c) 2022-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

# User namespace


class NamespaceUser:
    def __init__(self, api_test):
        self._api = api_test

    def list_users(self):
        """Lists all users."""
        return self._api.call("user.listUsers")

    def list_roles(self, user):
        """Lists the roles of a user."""
        return self._api.call("user.listRoles", user)

    def create(self, user, password, first, last, email):
        """Creates a user with the given parameters."""
        return self._api.call("user.create", user, password, first, last, email)

    def delete(self, user):
        """Deletes a user from the system."""
        return self._api.call("user.delete", user)

    def add_role(self, user, role):
        """Adds a role to a user."""
        return self._api.call("user.addRole", user, role)

    def remove_role(self, user, role):
        """Removes a role from a user."""
        return self._api.call("user.removeRole", user, role)

    def get_details(self, user):
        """Gets the details of a user."""
        return self._api.call("user.getDetails", user)
