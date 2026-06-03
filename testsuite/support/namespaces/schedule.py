# Copyright (c) 2022-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

# Schedule namespace


class NamespaceSchedule:
    def __init__(self, api_test):
        self._api = api_test

    def list_all_actions(self):
        """Lists all actions."""
        return self._api.call("schedule.listAllActions")

    def list_in_progress_actions(self):
        """Returns a list of actions that are currently in progress."""
        return self._api.call("schedule.listInProgressActions")

    def list_in_progress_systems(self, action_id):
        """Returns a list of systems currently in progress for the given action."""
        return self._api.call("schedule.listInProgressSystems", action_id)

    def list_completed_actions(self):
        """Returns a list of completed actions for the current user."""
        return self._api.call("schedule.listCompletedActions")

    def list_failed_actions(self):
        """Returns a list of failed actions."""
        return self._api.call("schedule.listFailedActions")

    def list_failed_systems(self, action_id):
        """Returns a list of systems that failed to execute the action."""
        return self._api.call("schedule.listFailedSystems", action_id)

    def cancel_actions(self, actions):
        """Cancels actions in the schedule."""
        return self._api.call("schedule.cancelActions", actions)

    def fail_system_action(self, system_id, action_id):
        """Fails a system action."""
        return self._api.call("schedule.failSystemAction", system_id, action_id)
