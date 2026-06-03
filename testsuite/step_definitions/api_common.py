# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/api_common.rb.

Covers all API-driven steps: system, user, channel, activationkey,
actionchain, schedule, powermanagement, audit, configchannel, kickstart,
and appstream namespaces.
"""

import time

from pytest_bdd import given, when, then, parsers
from support.remote_nodes_env import get_target
from support.commonlib import repeat_until_timeout
from support.env import DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_system_name(host: str) -> str:
    """Return the full hostname for a logical host name."""
    try:
        node = get_target(host)
        return node.full_hostname
    except (NotImplementedError, KeyError):
        return host


def _get_system_id(api_test, host: str) -> int:
    """Return the numeric system ID for a host via the API."""
    system_name = _get_system_name(host)
    return api_test.system.retrieve_server_id(system_name)


# ---------------------------------------------------------------------------
# system namespace
# ---------------------------------------------------------------------------

@when("I delete all the imported terminals")
def step_delete_all_imported_terminals(api_test):
    current_systems = api_test.system.list_systems()
    # Delete everything that is not a minion or client
    full_names = [
        s["name"] for s in current_systems
        if not any(k in s["name"] for k in ("minion", "client"))
    ]
    if full_names:
        api_test.system.delete_systems_by_name(full_names)


@when(parsers.re(r'I delete "(?P<host>[^"]*)" system using the api'))
def step_delete_system_using_api(api_test, host: str):
    system_name = _get_system_name(host)
    api_test.system.delete_systems_by_name([system_name])


@given(parsers.re(r'I want to operate on this "(?P<host>[^"]*)"'))
def step_want_to_operate_on(api_test, scenario_state, host: str):
    system_name = _get_system_name(host)
    matches = api_test.system.search_by_name(system_name)
    first_match = matches[0] if matches else None
    assert first_match is not None, f"Could not find system with hostname {system_name}"
    scenario_state["client_id"] = first_match["id"]


@when(parsers.re(
    r'I call system\.bootstrap\(\) on host "(?P<host>[^"]*)" and salt-ssh "(?P<salt_ssh_enabled>[^"]*)"'
))
def step_bootstrap_system(api_test, host: str, salt_ssh_enabled: str):
    system_name = _get_system_name(host)
    salt_ssh = (salt_ssh_enabled == "enabled")
    akey = "1-SUSE-SSH-KEY-x86_64" if salt_ssh else "1-SUSE-KEY-x86_64"
    result = api_test.system.bootstrap_system(system_name, akey, salt_ssh)
    assert result == 1, f"Bootstrap return code not equal to 1: {result}"


@when("I call system.bootstrap() on unknown host, I should get an API fault")
def step_bootstrap_unknown_host(api_test):
    exception_thrown = False
    try:
        api_test.system.bootstrap_system("imprettysureidontexist", "", False)
    except Exception:
        exception_thrown = True
    assert exception_thrown, "Exception must be thrown for non-existing host."


@when(
    "I call system.bootstrap() on a Salt minion with saltSSH = true, "
    "but with activation key with default contact method, I should get an API fault"
)
def step_bootstrap_salt_minion_wrong_key(api_test):
    exception_thrown = False
    try:
        node = get_target("sle_minion")
        api_test.system.bootstrap_system(node.full_hostname, "1-SUSE-KEY-x86_64", True)
    except Exception:
        exception_thrown = True
    assert exception_thrown, "Exception must be thrown for non-compatible activation keys."


@when(parsers.re(r'I schedule a highstate for "(?P<host>[^"]*)" via API'))
def step_schedule_highstate_via_api(api_test, host: str):
    system_name = _get_system_name(host)
    node_id = api_test.system.retrieve_server_id(system_name)
    date_high = api_test.date_now()
    api_test.system.schedule_apply_highstate(node_id, date_high, False)


@when(parsers.re(
    r'I unsubscribe "(?P<host>[^"]*)" from configuration channel "(?P<channel>[^"]*)"'
))
def step_unsubscribe_from_config_channel(api_test, scenario_state, host: str, channel: str):
    system_name = _get_system_name(host)
    node_id = api_test.system.retrieve_server_id(system_name)
    api_test.system.config.remove_channels([node_id], [channel])


@when("I create a system record")
def step_create_system_record(api_test):
    dev = {
        "name": "eth0", "ip": "1.1.1.1",
        "mac": "00:22:22:77:EE:CC", "dnsname": "testserver.example.com",
    }
    api_test.system.create_system_record(
        "testserver", "fedora_kickstart_profile_upload", "", "my test server", [dev]
    )


@when(parsers.re(
    r'I create a system record with name "(?P<name>[^"]*)" and kickstart label "(?P<label>[^"]*)"'
))
def step_create_system_record_with_name(api_test, name: str, label: str):
    dev = {
        "name": "eth0", "ip": "1.1.1.2",
        "mac": "00:22:22:77:EE:DD", "dnsname": "testserver.example.com",
    }
    api_test.system.create_system_record(name, label, "", "my test server", [dev])


@when("I wait for the OpenSCAP audit to finish")
def step_wait_for_openscap_audit(api_test, scenario_state):
    node_id = api_test.system.retrieve_server_id(get_target("sle_minion").full_hostname)
    scenario_state["sle_id"] = node_id

    def _check():
        scans = api_test.system.scap.list_xccdf_scans(node_id)
        return True if len(scans) > 1 else None

    repeat_until_timeout(_check, message="OpenSCAP process did not complete")


@when(parsers.re(r'I retrieve the relevant errata for (?P<raw_hosts>.+)'))
def step_retrieve_relevant_errata(api_test, raw_hosts: str):
    hosts = [h.strip() for h in raw_hosts.split(",")]
    sids = [_get_system_id(api_test, h) for h in hosts]
    if len(sids) == 1:
        api_test.system.get_system_errata(sids[0])
    else:
        api_test.system.get_systems_errata(sids)


@when(parsers.re(
    r'I call system\.create_system_profile\(\) with name "(?P<name>[^"]*)" and HW address "(?P<hw_address>[^"]*)"'
))
def step_create_system_profile_hw(api_test, name: str, hw_address: str):
    profile_id = api_test.system.create_system_profile(name, {"hwAddress": hw_address})
    assert profile_id is not None, "create_system_profile returned None"


@when(parsers.re(
    r'I call system\.create_system_profile\(\) with name "(?P<name>[^"]*)" and hostname "(?P<hostname>[^"]*)"'
))
def step_create_system_profile_hostname(api_test, name: str, hostname: str):
    profile_id = api_test.system.create_system_profile(name, {"hostname": hostname})
    assert profile_id is not None, "create_system_profile returned None"


@when(r'I call system.list_empty_system_profiles()')
def step_list_empty_system_profiles(api_test, scenario_state):
    scenario_state["output"] = api_test.system.list_empty_system_profiles()


@then(parsers.re(r'"(?P<profile_name>[^"]*)" should be present in the result'))
def step_profile_present_in_result(scenario_state, profile_name: str):
    output = scenario_state.get("output", [])
    assert any(p["name"] == profile_name for p in output), (
        f"Profile '{profile_name}' not found in {output}"
    )


# ---------------------------------------------------------------------------
# user namespace
# ---------------------------------------------------------------------------

@when("I call user.list_users()")
def step_list_users(api_test, scenario_state):
    scenario_state["users"] = api_test.user.list_users()


@then(parsers.re(r'I should get at least user "(?P<user>[^"]*)"'))
def step_should_get_at_least_user(scenario_state, user: str):
    logins = [u["login"] for u in scenario_state.get("users", [])]
    assert user in logins, f"User '{user}' not found in {logins}"


@when(parsers.re(r'I call user\.list_roles\(\) on user "(?P<user>[^"]*)"'))
def step_list_roles(api_test, scenario_state, user: str):
    scenario_state["roles"] = api_test.user.list_roles(user)


@then(parsers.re(r'I should get at least one role that matches "(?P<suffix>[^"]*)" suffix'))
def step_get_role_with_suffix(scenario_state, suffix: str):
    roles = scenario_state.get("roles", [])
    matching = [r for r in roles if suffix in r]
    assert matching, f"No role matching suffix '{suffix}' found in {roles}"


@then(parsers.re(r'I should get role "(?P<rolename>[^"]*)"'))
def step_should_get_role(scenario_state, rolename: str):
    assert rolename in scenario_state.get("roles", []), (
        f"Role '{rolename}' not in {scenario_state.get('roles', [])}"
    )


@then(parsers.re(r'I should not get role "(?P<rolename>[^"]*)"'))
def step_should_not_get_role(scenario_state, rolename: str):
    assert rolename not in scenario_state.get("roles", []), (
        f"Role '{rolename}' should not be in {scenario_state.get('roles', [])}"
    )


@when(parsers.re(r'I call user\.create\(\) with login "(?P<user>[^"]*)"'))
def step_create_user(api_test, user: str):
    result = api_test.user.create(user, "JamesBond007", "Hans", "Mustermann",
                                  "hans.mustermann@suse.com")
    assert result == 1, f"user.create returned {result!r}"


@when(parsers.re(r'I call user\.add_role\(\) on "(?P<user>[^"]*)" with the role "(?P<role>[^"]*)"'))
def step_add_role(api_test, user: str, role: str):
    result = api_test.user.add_role(user, role)
    assert result == 1, f"user.add_role returned {result!r}"


@when(parsers.re(r'I delete user "(?P<user>[^"]*)"'))
def step_delete_user(api_test, user: str):
    api_test.user.delete(user)


@when(parsers.re(r'I make sure "(?P<user>[^"]*)" is not present'))
def step_make_sure_user_not_present(api_test, user: str):
    logins = [u["login"] for u in api_test.user.list_users()]
    if user in logins:
        api_test.user.delete(user)


@when(parsers.re(
    r'I call user\.remove_role\(\) on "(?P<luser>[^"]*)" with the role "(?P<rolename>[^"]*)"'
))
def step_remove_role(api_test, luser: str, rolename: str):
    result = api_test.user.remove_role(luser, rolename)
    assert result == 1, f"user.remove_role returned {result!r}"


@given(parsers.re(
    r'I create a user with name "(?P<user>[^"]*)" and password "(?P<password>[^"]*)"'
    r'(?: with roles "(?P<roles_string>[^"]*)")?'
))
def step_create_user_with_name_and_password(
    api_test, scenario_state, user: str, password: str, roles_string: str
):
    scenario_state["current_user"] = user
    scenario_state["current_password"] = password
    existing = [u["login"] for u in api_test.user.list_users()]
    if user in existing:
        return
    default_roles = [
        "org_admin", "channel_admin", "config_admin",
        "system_group_admin", "activation_key_admin", "image_admin",
    ]
    roles_to_assign = (
        [r.strip() for r in roles_string.split(",") if r.strip()]
        if roles_string
        else default_roles
    )
    try:
        api_test.user.create(user, password, user, user, "galaxy-noise@localhost")
        for role in roles_to_assign:
            api_test.user.add_role(user, role)
        scenario_state["user_creation_status"] = "success"
    except Exception as e:
        scenario_state["user_creation_status"] = "error"
        scenario_state["user_creation_error"] = str(e)


# ---------------------------------------------------------------------------
# channel namespace
# ---------------------------------------------------------------------------

@when(parsers.re(r'I create a repo with label "(?P<label>[^"]*)" and url'))
def step_create_repo(api_test, label: str):
    server_host = get_target("server").full_hostname
    url = f"http://{server_host}/pub/AnotherRepo/"
    assert api_test.channel.software.create_repo(label, url)


@when(parsers.re(
    r'I associate repo "(?P<repo_label>[^"]*)" with channel "(?P<channel_label>[^"]*)"'
))
def step_associate_repo(api_test, repo_label: str, channel_label: str):
    assert api_test.channel.software.associate_repo(channel_label, repo_label)


@when("I create the following channels:")
def step_create_channels(api_test, datatable):
    for row in datatable:
        label = row["LABEL"]
        name = row["NAME"]
        summary = row["SUMMARY"]
        arch = row["ARCH"]
        parent = row["PARENT"]
        result = api_test.channel.software.create(label, name, summary, arch, parent)
        assert result == 1, f"channel.create returned {result!r}"


@when(parsers.re(r'I delete the software channel with label "(?P<label>[^"]*)"'))
def step_delete_software_channel(api_test, label: str):
    result = api_test.channel.software.delete(label)
    assert result == 1, f"channel.delete returned {result!r}"


@when(parsers.re(r'I delete the repo with label "(?P<label>[^"]*)"'))
def step_delete_repo(api_test, label: str):
    result = api_test.channel.software.remove_repo(label)
    assert result == 1, f"channel.remove_repo returned {result!r}"


@then("something should get listed with a call of listSoftwareChannels")
def step_something_listed_software_channels(api_test):
    count = api_test.channel.get_software_channels_count()
    assert count >= 1, f"Expected at least 1 software channel, got {count}"


@then(parsers.re(r'"(?P<label>[^"]*)" should get listed with a call of listSoftwareChannels'))
def step_label_listed_software_channels(api_test, label: str):
    assert api_test.channel.channel_verified(label), (
        f"Channel '{label}' not found in software channels"
    )


@then(parsers.re(
    r'"(?P<label>[^"]*)" should not get listed with a call of listSoftwareChannels'
))
def step_label_not_listed_software_channels(api_test, label: str):
    assert not api_test.channel.channel_verified(label), (
        f"Channel '{label}' should not be listed"
    )


@then(parsers.re(r'"(?P<parent>[^"]*)" should be the parent channel of "(?P<child>[^"]*)"'))
def step_parent_channel(api_test, parent: str, child: str):
    assert api_test.channel.software.parent_channel(child, parent), (
        f"'{parent}' is not the parent of '{child}'"
    )


@then(parsers.re(
    r'channel "(?P<label>[^"]*)" should have attribute "(?P<attr>[^"]*)" that is a date'
))
def step_channel_has_date_attr(api_test, label: str, attr: str):
    ret = api_test.channel.software.get_details(label)
    assert ret, f"No details for channel '{label}'"
    assert api_test.is_date(ret.get(attr)), (
        f"Attribute '{attr}' is not a date: {ret.get(attr)}"
    )


@then(parsers.re(
    r'channel "(?P<label>[^"]*)" should not have attribute "(?P<attr>[^"]*)"'
))
def step_channel_no_attr(api_test, label: str, attr: str):
    ret = api_test.channel.software.get_details(label)
    assert ret, f"No details for channel '{label}'"
    assert attr not in ret, f"Channel '{label}' unexpectedly has attribute '{attr}'"


@then(parsers.re(
    r'channel "(?P<channel>[^"]*)" should be (?P<state>enabled|disabled) on "(?P<host>[^"]*)"'
))
def step_channel_state_on_host(api_test, channel: str, state: str, host: str):
    system_id = _get_system_id(api_test, host)
    channels = api_test.channel.software.list_system_channels(system_id)
    if state == "enabled":
        assert channel in channels, f"Channel '{channel}' not enabled on '{host}'"
    else:
        assert channel not in channels, f"Channel '{channel}' should be disabled on '{host}'"


@then(parsers.re(r'"(?P<count>\d+)" channels should be enabled on "(?P<host>[^"]*)"'))
def step_n_channels_enabled(api_test, count: str, host: str):
    system_id = _get_system_id(api_test, host)
    channels = api_test.channel.software.list_system_channels(system_id)
    assert len(channels) == int(count), (
        f"Expected {count} channels, got {len(channels)}"
    )


@then(parsers.re(
    r'"(?P<count>\d+)" channels with prefix "(?P<prefix>[^"]*)" should be enabled on "(?P<host>[^"]*)"'
))
def step_n_channels_with_prefix_enabled(api_test, count: str, prefix: str, host: str):
    system_id = _get_system_id(api_test, host)
    channels = api_test.channel.software.list_system_channels(system_id)
    matching = [c for c in channels if c.startswith(prefix)]
    assert len(matching) == int(count), (
        f"Expected {count} channels with prefix '{prefix}', got {len(matching)}"
    )


# ---------------------------------------------------------------------------
# activationkey namespace
# ---------------------------------------------------------------------------

@then("I should get some activation keys")
def step_should_get_some_activation_keys(api_test):
    count = api_test.activationkey.get_activation_keys_count()
    assert count >= 1, f"Expected at least 1 activation key, got {count}"


@when(parsers.re(
    r'I create an activation key with id "(?P<id>[^"]*)", description "(?P<description>[^"]*)"'
    r'(?:, base channel "(?P<base_channel_label>[^"]*)")?'
    r'(?:, limit of (?P<usage_limit_str>\d+))?'
    r'(?: and contact method "(?P<contact_method>[^"]*)")?'
))
def step_create_activation_key(
    api_test, id: str, description: str,
    base_channel_label: str, usage_limit_str: str, contact_method: str
):
    base_channel_label = base_channel_label or ""
    contact_method = contact_method or "default"
    usage_limit = int(usage_limit_str) if usage_limit_str else 10

    activation_key = api_test.activationkey.create(
        id, description, base_channel_label, usage_limit
    )
    assert activation_key is not None, "Key creation failed"
    assert activation_key == f"1-{id}", f"Bad key name: {activation_key}"

    success = api_test.activationkey.details_set(
        activation_key, description, base_channel_label, usage_limit, contact_method
    )
    assert success, "Failed to set activation key details"


@when(parsers.re(
    r'I set the entitlements of the activation key "(?P<activation_key>[^"]*)" to "(?P<entitlements>[^"]*)"'
))
def step_set_entitlements(api_test, activation_key: str, entitlements: str):
    entitlements_array = [e.strip() for e in entitlements.split(",") if e.strip()]
    api_test.activationkey.set_entitlement(activation_key, entitlements_array)


@then(parsers.re(r'I should get the new activation key "(?P<activation_key>[^"]*)"'))
def step_should_get_new_activation_key(api_test, activation_key: str):
    assert api_test.activationkey.verified(activation_key), (
        f"Activation key '{activation_key}' not verified"
    )


@when(parsers.re(r'I delete the activation key "(?P<activation_key>[^"]*)"'))
def step_delete_activation_key(api_test, activation_key: str):
    assert api_test.activationkey.delete(activation_key), (
        f"Could not delete activation key '{activation_key}'"
    )
    assert not api_test.activationkey.verified(activation_key), (
        f"Activation key '{activation_key}' still exists after deletion"
    )


@when(parsers.re(
    r'I set the description of the activation key "(?P<activation_key>[^"]*)" to "(?P<description>[^"]*)"'
))
def step_set_activation_key_description(api_test, activation_key: str, description: str):
    assert api_test.activationkey.details_set(
        activation_key, description, "", 10, "default"
    ), f"Failed to set description of activation key '{activation_key}'"


@then(parsers.re(
    r'I get the description "(?P<description>[^"]*)" for the activation key "(?P<activation_key>[^"]*)"'
))
def step_get_activation_key_description(api_test, description: str, activation_key: str):
    details = api_test.activationkey.get_details(activation_key)
    assert details["description"] == description, (
        f"Expected description '{description}', got '{details.get('description')}'"
    )


@when(parsers.re(
    r'I create an activation key including custom channels for "(?P<client>[^"]*)" via API'
))
def step_create_activation_key_with_channels(api_test, client: str):
    from support.constants import BASE_CHANNEL_BY_CLIENT, LABEL_BY_BASE_CHANNEL
    from support.env import USE_SALT_BUNDLE
    from conftest import _session_cache

    id_ = description = f"{client}_key"
    product = _session_cache.get("product", "")

    # Adjust for non-transactional proxy
    effective_client = client
    is_transactional = _session_cache.get("is_transactional_server", True)
    if client == "proxy" and not is_transactional:
        effective_client = "proxy_nontransactional"

    base_channel = BASE_CHANNEL_BY_CLIENT.get(product, {}).get(effective_client, "")
    base_channel_label = LABEL_BY_BASE_CHANNEL.get(product, {}).get(base_channel, "")

    key = api_test.activationkey.create(id_, description, base_channel_label, 100)
    assert key is not None, "Error creating activation key via the API"

    is_ssh_minion = "ssh_minion" in client
    api_test.activationkey.details_set(
        key, description, base_channel_label, 100,
        "ssh-push" if is_ssh_minion else "default"
    )

    if "buildhost" in client:
        api_test.activationkey.set_entitlement(key, ["osimage_build_host"])

    child_channels = api_test.channel.software.list_child_channels(base_channel_label)

    # Filter out wrong child channels
    channel_filters = {
        r"sle15sp6|slemicro55": [
            "suse-manager-proxy",
            "suse-manager-retail-branch-server",
            "suse-manager-server",
        ],
        r"sle15sp7|slmicro6[12]": [
            "suse-multi-linux-manager-proxy",
            "suse-multi-linux-manager-retail-branch-server",
            "suse-multi-linux-manager-server",
        ],
    }
    import re as _re
    for pattern, exclusions in channel_filters.items():
        if _re.search(pattern, effective_client):
            child_channels = [
                c for c in child_channels
                if not any(ex in c for ex in exclusions)
            ]

    if effective_client == "proxy_nontransactional":
        version = _session_cache.get("product_version_full", "")
        if "5.1" in version:
            version_to_exclude = "5.2"
        elif "5.2" in version or "head" in version:
            version_to_exclude = "5.1"
        else:
            version_to_exclude = None
        if version_to_exclude:
            child_channels = [c for c in child_channels if version_to_exclude not in c]

    api_test.activationkey.add_child_channels(key, child_channels)


# ---------------------------------------------------------------------------
# actionchain namespace
# ---------------------------------------------------------------------------

@when(parsers.re(r'I create an action chain with label "(?P<label>[^"]*)" via API'))
def step_create_action_chain(api_test, scenario_state, label: str):
    action_id = api_test.actionchain.create_chain(label)
    assert action_id >= 1, f"Action chain creation returned invalid id: {action_id}"
    scenario_state["chain_label"] = label


@when(parsers.re(r'I see label "(?P<label>[^"]*)" when I list action chains via API'))
def step_see_label_in_action_chains(api_test, label: str):
    chains = api_test.actionchain.list_chains()
    assert label in chains, f"Label '{label}' not found in action chains: {chains}"


@when("I delete the action chain via API")
def step_delete_action_chain(api_test, scenario_state):
    api_test.actionchain.delete_chain(scenario_state["chain_label"])


@when(parsers.re(r'I delete an action chain, labeled "(?P<label>[^"]*)", via API'))
def step_delete_action_chain_by_label(api_test, label: str):
    api_test.actionchain.delete_chain(label)


@when("I delete all action chains via API")
def step_delete_all_action_chains(api_test):
    for label in api_test.actionchain.list_chains():
        api_test.actionchain.delete_chain(label)


@then(parsers.re(r'I rename the action chain with label "(?P<old_label>[^"]*)" to "(?P<new_label>[^"]*)" via API'))
def step_rename_action_chain(api_test, old_label: str, new_label: str):
    api_test.actionchain.rename_chain(old_label, new_label)


@then(parsers.re(
    r'there should be a new action chain with the label "(?P<label>[^"]*)" listed via API'
))
def step_action_chain_label_exists(api_test, label: str):
    chains = api_test.actionchain.list_chains()
    assert label in chains, f"Label '{label}' not in action chains: {chains}"


@then(parsers.re(
    r'there should be no action chain with the label "(?P<label>[^"]*)" listed via API'
))
def step_action_chain_label_not_exists(api_test, label: str):
    chains = api_test.actionchain.list_chains()
    assert label not in chains, f"Label '{label}' should not be in action chains: {chains}"


@when(parsers.re(r'I add the script "(?P<script>[^"]*)" to the action chain via API'))
def step_add_script_to_action_chain(api_test, scenario_state, script: str):
    client_id = scenario_state["client_id"]
    chain_label = scenario_state["chain_label"]
    result = api_test.actionchain.add_script_run(
        client_id, chain_label, "root", "root", 300, f"#!/bin/bash\n{script}"
    )
    assert result >= 1, f"add_script_run returned {result!r}"


@then("I should be able to see all these actions in the action chain via API")
def step_see_actions_in_chain(api_test, scenario_state):
    actions = api_test.actionchain.list_chain_actions(scenario_state["chain_label"])
    assert actions is not None, "list_chain_actions returned None"


@when("I add a system reboot to the action chain via API")
def step_add_system_reboot(api_test, scenario_state):
    result = api_test.actionchain.add_system_reboot(
        scenario_state["client_id"], scenario_state["chain_label"]
    )
    assert result >= 1, f"add_system_reboot returned {result!r}"


@when("I add a package install to the action chain via API")
def step_add_package_install(api_test, scenario_state):
    pkgs = api_test.system.list_all_installable_packages(scenario_state["client_id"])
    assert pkgs, "No installable packages found"
    result = api_test.actionchain.add_package_install(
        scenario_state["client_id"], [pkgs[0]["id"]], scenario_state["chain_label"]
    )
    assert result >= 1, f"add_package_install returned {result!r}"


@when("I add a package removal to the action chain via API")
def step_add_package_removal(api_test, scenario_state):
    pkgs = api_test.system.list_all_installable_packages(scenario_state["client_id"])
    result = api_test.actionchain.add_package_removal(
        scenario_state["client_id"], [pkgs[0]["id"]], scenario_state["chain_label"]
    )
    assert result >= 1, f"add_package_removal returned {result!r}"


@when("I add a package upgrade to the action chain via API")
def step_add_package_upgrade(api_test, scenario_state):
    pkgs = api_test.system.list_latest_upgradable_packages(scenario_state["client_id"])
    assert pkgs, "No upgradable packages found"
    result = api_test.actionchain.add_package_upgrade(
        scenario_state["client_id"], [pkgs[0]["to_package_id"]], scenario_state["chain_label"]
    )
    assert result >= 1, f"add_package_upgrade returned {result!r}"


@when("I add a package verification to the action chain via API")
def step_add_package_verify(api_test, scenario_state):
    pkgs = api_test.system.list_all_installable_packages(scenario_state["client_id"])
    assert pkgs, "No installable packages found"
    result = api_test.actionchain.add_package_verify(
        scenario_state["client_id"], [pkgs[0]["id"]], scenario_state["chain_label"]
    )
    assert result >= 1, f"add_package_verify returned {result!r}"


@when("I remove each action within the chain via API")
def step_remove_each_action(api_test, scenario_state):
    actions = api_test.actionchain.list_chain_actions(scenario_state["chain_label"])
    assert actions is not None
    for action in actions:
        result = api_test.actionchain.remove_action(
            scenario_state["chain_label"], action["id"]
        )
        assert result >= 0, f"remove_action returned {result!r}"


@then("the current action chain should be empty")
def step_action_chain_empty(api_test, scenario_state):
    actions = api_test.actionchain.list_chain_actions(scenario_state["chain_label"])
    assert not actions, f"Action chain still has actions: {actions}"


@when("I schedule the action chain via API")
def step_schedule_action_chain(api_test, scenario_state):
    import datetime
    result = api_test.actionchain.schedule_chain(
        scenario_state["chain_label"], datetime.datetime.now()
    )
    assert result >= 0, f"schedule_chain returned {result!r}"


@when("I wait until there are no more action chains listed via API")
def step_wait_no_action_chains(api_test):
    def _check():
        chains = api_test.actionchain.list_chains()
        return True if not chains else None

    repeat_until_timeout(_check, message="Action Chains still present")


# ---------------------------------------------------------------------------
# schedule namespace
# ---------------------------------------------------------------------------

@then(parsers.re(
    r'I should see scheduled action, called "(?P<label>[^"]*)", listed via API'
))
def step_see_scheduled_action(api_test, label: str):
    names = [a["name"] for a in api_test.schedule.list_in_progress_actions()]
    assert label in names, f"Scheduled action '{label}' not found in {names}"


@then("I cancel all scheduled actions via API")
def step_cancel_all_scheduled_actions(api_test):
    actions = [
        a for a in api_test.schedule.list_in_progress_actions()
        if not a.get("prerequisite")
    ]
    for action in actions:
        try:
            api_test.schedule.cancel_actions([action["id"]])
        except Exception:
            systems = api_test.schedule.list_in_progress_systems(action["id"])
            for system in systems:
                api_test.schedule.fail_system_action(system["server_id"], action["id"])


@then("I wait until there are no more scheduled actions listed via API")
def step_wait_no_scheduled_actions(api_test):
    def _check():
        actions = api_test.schedule.list_in_progress_actions()
        return True if not actions else None

    repeat_until_timeout(_check, message="Scheduled actions still present")


# ---------------------------------------------------------------------------
# provisioning.powermanagement namespace
# ---------------------------------------------------------------------------

@when("I fetch power management values")
def step_fetch_power_management(api_test, scenario_state):
    scenario_state["powermgmt_result"] = (
        api_test.system.provisioning.powermanagement.get_details(
            scenario_state["client_id"]
        )
    )


@then(parsers.re(
    r'power management results should have "(?P<value>[^"]*)" for "(?P<hkey>[^"]*)"'
))
def step_power_mgmt_results(scenario_state, value: str, hkey: str):
    result = scenario_state.get("powermgmt_result", {})
    assert result.get(hkey) == value, (
        f"Expected '{value}' for '{hkey}', got '{result.get(hkey)}'"
    )


@then(parsers.re(
    r'I set power management value "(?P<value>[^"]*)" for "(?P<hkey>[^"]*)"'
))
def step_set_power_management_value(api_test, scenario_state, value: str, hkey: str):
    api_test.system.provisioning.powermanagement.set_details(
        scenario_state["client_id"], {hkey: value}
    )


@then("I turn power on")
def step_turn_power_on(api_test, scenario_state):
    api_test.system.provisioning.powermanagement.power_on(scenario_state["client_id"])


@then("I turn power off")
def step_turn_power_off(api_test, scenario_state):
    api_test.system.provisioning.powermanagement.power_off(scenario_state["client_id"])


@then("I do power management reboot")
def step_power_management_reboot(api_test, scenario_state):
    api_test.system.provisioning.powermanagement.reboot(scenario_state["client_id"])


@then(parsers.re(r'the power status is "(?P<estat>[^"]*)"'))
def step_power_status(api_test, scenario_state, estat: str):
    stat = api_test.system.provisioning.powermanagement.get_status(
        scenario_state["client_id"]
    )
    if estat == "on":
        assert stat, "Power status should be 'on'"
    elif estat == "off":
        assert not stat, "Power status should be 'off'"


# ---------------------------------------------------------------------------
# audit namespace
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I call audit\.list_systems_by_patch_status\(\) with CVE identifier "(?P<cve_identifier>[^"]*)"'
))
def step_list_systems_by_patch_status(api_test, scenario_state, cve_identifier: str):
    scenario_state["result_list"] = api_test.audit.list_systems_by_patch_status(
        cve_identifier
    ) or []


@then(parsers.re(
    r'I should get status "(?P<status>[^"]+)" for system "(?P<system_id>[0-9]+)"'
))
def step_get_status_for_system(scenario_state, status: str, system_id: str):
    results = [
        item for item in scenario_state.get("result_list", [])
        if item["system_id"] == int(system_id)
    ]
    assert results, f"No results for system_id {system_id}"
    scenario_state["result"] = results[0]
    assert results[0]["patch_status"] == status, (
        f"Expected status '{status}', got '{results[0].get('patch_status')}'"
    )


@then(parsers.re(r'I should get status "(?P<status>[^"]+)" for "(?P<host>[^"]+)"'))
def step_get_status_for_host(api_test, scenario_state, status: str, host: str):
    system_id = _get_system_id(api_test, host)
    results = [
        item for item in scenario_state.get("result_list", [])
        if item["system_id"] == system_id
    ]
    assert results, f"No results for host '{host}' (id={system_id})"
    scenario_state["result"] = results[0]
    assert results[0]["patch_status"] == status, (
        f"Expected status '{status}', got '{results[0].get('patch_status')}'"
    )


@then(parsers.re(r'I should get the "(?P<channel_label>[^"]*)" channel label'))
def step_get_channel_label(scenario_state, channel_label: str):
    result = scenario_state.get("result", {})
    assert channel_label in result.get("channel_labels", []), (
        f"'{channel_label}' not in {result.get('channel_labels')}"
    )


@then(parsers.re(r'I should get the "(?P<patch>[^"]*)" patch'))
def step_get_patch(scenario_state, patch: str):
    result = scenario_state.get("result", {})
    assert patch in result.get("errata_advisories", []), (
        f"'{patch}' not in {result.get('errata_advisories')}"
    )


# ---------------------------------------------------------------------------
# configchannel namespace
# ---------------------------------------------------------------------------

@then(parsers.re(r'channel "(?P<channel>[^"]*)" should exist'))
def step_channel_should_exist(api_test, channel: str):
    result = api_test.configchannel.channel_exists(channel)
    assert result == 1, f"Config channel '{channel}' does not exist"


@then(parsers.re(
    r'channel "(?P<channel>[^"]*)" should contain file "(?P<file>[^"]*)"'
))
def step_channel_contains_file(api_test, channel: str, file: str):
    result = api_test.configchannel.list_files(channel)
    count = sum(1 for item in result if item["path"] == file)
    assert count == 1, f"File '{file}' not found in channel '{channel}'"


@then(parsers.re(
    r'"(?P<host>[^"]*)" should be subscribed to channel "(?P<channel>[^"]*)"'
))
def step_should_be_subscribed(api_test, host: str, channel: str):
    system_name = _get_system_name(host)
    result = api_test.configchannel.list_subscribed_systems(channel)
    count = sum(1 for item in result if item["name"] == system_name)
    assert count == 1, f"'{host}' not subscribed to channel '{channel}'"


@then(parsers.re(
    r'"(?P<host>[^"]*)" should not be subscribed to channel "(?P<channel>[^"]*)"'
))
def step_should_not_be_subscribed(api_test, host: str, channel: str):
    system_name = _get_system_name(host)
    result = api_test.configchannel.list_subscribed_systems(channel)
    count = sum(1 for item in result if item["name"] == system_name)
    assert count == 0, f"'{host}' should not be subscribed to channel '{channel}'"


@when(parsers.re(r'I create state channel "(?P<channel>[^"]*)" via API$'))
def step_create_state_channel(api_test, channel: str):
    api_test.configchannel.create(channel, channel, channel, "state")


@when(parsers.re(
    r'I create state channel "(?P<channel>[^"]*)" containing '
    r'"(?P<contents>[^"]*)" via API'
))
def step_create_state_channel_with_contents(api_test, channel: str, contents: str):
    api_test.configchannel.create_with_pathinfo(
        channel, channel, channel, "state", {"contents": contents}
    )


@when(parsers.re(
    r'I call configchannel\.get_file_revision\(\) with file "(?P<file_path>[^"]*)", '
    r'revision "(?P<revision>[^"]*)" and channel "(?P<channel>[^"]*)" via API'
))
def step_call_get_file_revision(api_test, scenario_state,
                                file_path: str, revision: str, channel: str):
    result = api_test.configchannel.get_file_revision(channel, file_path, int(revision))
    scenario_state["get_file_revision_result"] = result


@then(parsers.re(r'I should get file contents "(?P<contents>[^"]*)"'))
def step_should_get_file_contents(scenario_state, contents: str):
    result = scenario_state.get("get_file_revision_result", {})
    actual = result.get("contents", "")
    assert actual == contents, (
        f"Expected file contents: {contents!r}\nGot: {actual!r}"
    )


@when(parsers.re(
    r'I add file "(?P<file>[^"]*)" containing "(?P<contents>[^"]*)" to channel "(?P<channel>[^"]*)"'
))
def step_add_file_to_channel(api_test, file: str, contents: str, channel: str):
    api_test.configchannel.create_or_update_path(channel, file, contents)


@when(parsers.re(r'I deploy all systems registered to channel "(?P<channel>[^"]*)"'))
def step_deploy_all_systems(api_test, channel: str):
    api_test.configchannel.deploy_all_systems(channel)


@when(parsers.re(
    r'I delete channel "(?P<channel>[^"]*)" via API(?P<error_control>(?: without error control)?)$'
))
def step_delete_channel_via_api(api_test, channel: str, error_control: str):
    try:
        api_test.configchannel.delete_channels([channel])
    except Exception:
        if not error_control.strip():
            raise


@then(parsers.re(
    r'I delete channel "(?P<channel>[^"]*)" via API(?P<error_control>(?: without error control)?)$'
))
def step_then_delete_channel_via_api(api_test, channel: str, error_control: str):
    step_delete_channel_via_api(api_test, channel, error_control)


# ---------------------------------------------------------------------------
# kickstart / tree namespace
# ---------------------------------------------------------------------------

@when(parsers.re(r'I create "(?P<distro_name>[^"]*)" kickstart tree via the API'))
def step_create_kickstart_tree(api_test, distro_name: str):
    if distro_name == "fedora_kickstart_distro_api":
        api_test.kickstart.tree.create_distro(
            distro_name, "/var/autoinstall/Fedora_12_i386/",
            "fake-base-channel-rh-like", "fedora18"
        )
    elif distro_name == "testdistro":
        api_test.kickstart.tree.create_distro(
            distro_name, "/var/autoinstall/SLES15-SP7-x86_64/DVD1/",
            "sle-product-sles15-sp7-pool-x86_64", "sles15generic"
        )
    else:
        raise ValueError(f"Unrecognized distro name: {distro_name}")


@when(parsers.re(
    r'I create a "(?P<profile_name>[^"]*)" profile via the API using import file for "(?P<distro_name>[^"]*)" distribution'
))
def step_create_kickstart_profile_from_import(api_test, profile_name: str, distro_name: str):
    import os
    canonical_path = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "../features/upload_files/autoinstall/cobbler/mock/empty.xml"
        )
    )
    api_test.kickstart.create_profile_using_import_file(
        profile_name, distro_name, canonical_path
    )


@when("I create a kickstart tree with kernel options via the API")
def step_create_kickstart_tree_with_kernel_options(api_test):
    api_test.kickstart.tree.create_distro_w_kernel_options(
        "fedora_kickstart_distro_kernel_api",
        "/var/autoinstall/Fedora_12_i386/",
        "fake-base-channel-rh-like",
        "fedora18",
        "self_update=0",
        "self_update=1",
    )


@when("I update a kickstart tree via the API")
def step_update_kickstart_tree(api_test):
    api_test.kickstart.tree.update_distro(
        "fedora_kickstart_distro_api",
        "/var/autoinstall/Fedora_12_i386/",
        "fake-base-channel-rh-like",
        "generic_rpm",
        "self_update=0",
        "self_update=1",
    )


@when(parsers.re(
    r'I delete profile and distribution using the API for "(?P<distro_name>[^"]*)" kickstart tree'
))
def step_delete_kickstart_tree(api_test, distro_name: str):
    api_test.kickstart.tree.delete_tree_and_profiles(distro_name)


# ---------------------------------------------------------------------------
# appstream / modular channels namespace
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I verify channel "(?P<channel_label>[^"]*)" is(?P<not_modular> not)? modular via the API'
))
def step_verify_channel_modular(api_test, channel_label: str, not_modular: str):
    is_modular = api_test.channel.appstreams.modular(channel_label)
    expected = not_modular is None or not_modular.strip() == ""
    assert is_modular == expected, (
        f"Channel '{channel_label}' is modular? Expected: {expected} - got: {is_modular}"
    )


@when(parsers.re(
    r'channel "(?P<channel>[^"]*)" is(?P<not_present> not)? present in the modular channels listed via the API'
))
def step_channel_in_modular_list(api_test, channel: str, not_present: str):
    modular_channels = api_test.channel.appstreams.list_modular_channels()
    is_present = channel in modular_channels
    expected = not_present is None or not_present.strip() == ""
    assert is_present == expected, (
        f"Expected '{channel}' in modular channels? {expected} - got: {is_present}"
    )


@when(parsers.re(
    r'"(?P<module_name>[^"]*)" module streams "(?P<streams>[^"]*)" are available for channel "(?P<channel_label>[^"]*)" via the API'
))
def step_module_streams_available(api_test, module_name: str, streams: str, channel_label: str):
    expected_streams = [s.strip() for s in streams.split(",")]
    available_streams = api_test.channel.appstreams.list_module_streams(channel_label)
    for expected_stream in expected_streams:
        found = any(
            s.get("module") == module_name and s.get("stream") == expected_stream
            for s in available_streams
        )
        assert found, (
            f"Stream '{expected_stream}' for module '{module_name}' not found "
            f"in available streams for channel '{channel_label}'"
        )


# ---------------------------------------------------------------------------
# kickstart system profile (with table)
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I create and modify the kickstart system "(?P<name>[^"]*)" with kickstart label '
    r'"(?P<kslabel>[^"]*)" and hostname "(?P<hostname>[^"]*)" via XML-RPC'
))
def step_create_and_modify_kickstart_system(
    api_test, scenario_state, name: str, kslabel: str, hostname: str, datatable
):
    sid = api_test.system.create_system_profile(name, {"hostname": hostname})
    api_test.system.create_system_record_with_sid(sid, kslabel)
    variables = {row[0]: row[1] for row in datatable}
    api_test.system.set_variables(sid, variables)
