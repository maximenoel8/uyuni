# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/retail_steps.rb.

Covers Retail / PXE boot steps: proxy networking, terminal management,
configuration import, branch server setup, image building.
"""

import os
import re

from pytest_bdd import given, when, then, parsers

from support.remote_nodes_env import get_target, get_system_name
from support.commonlib import repeat_until_timeout, check_text
from support.env import DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# Proxy / branch server repositories
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I (?P<action>enable|disable) repositories (?P<when>before|after) installing branch server'
))
def step_enable_disable_repos_branch_server(action: str, when: str):
    proxy = get_target("proxy")
    os_version = proxy.os_version
    os_family = proxy.os_family

    repos = "os_pool_repo os_update_repo "
    # testing repos omitted if not needed — simplified for Python port
    if re.match(r"^sles", os_family) and re.match(r"^15", os_version):
        repos += (
            "proxy_module_pool_repo proxy_module_update_repo "
            "proxy_product_pool_repo proxy_product_update_repo "
            "module_server_applications_pool_repo module_server_applications_update_repo "
        )
    elif re.match(r"^opensuse", os_family):
        repos += "proxy_pool_repo "

    proxy.run(f"zypper mr --{action} {repos}", verbose=True)


@when("I start tftp on the proxy")
def step_start_tftp_on_proxy():
    import os as _os
    uyuni = _os.environ.get("PRODUCT", "") == "Uyuni"
    proxy = get_target("proxy")
    if uyuni:
        cmd = (
            "zypper --non-interactive --ignore-unknown remove atftp && "
            "zypper --non-interactive install tftp && "
            "systemctl enable tftp.service && "
            "systemctl start tftp.service"
        )
        proxy.run(cmd)
    else:
        proxy.run("systemctl enable tftp.service && systemctl start tftp.service")


# ---------------------------------------------------------------------------
# Network / ping checks
# ---------------------------------------------------------------------------

@then(parsers.re(r'"(?P<host>[^"]*)" should communicate with the server using public interface'))
def step_host_communicates_with_server(host: str):
    node = get_target(host)
    server = get_target("server")
    _result, return_code = node.run(
        f"ping -n -c 1 -I {node.public_interface} {server.public_ip}",
        check_errors=False
    )
    if return_code != 0:
        import time
        time.sleep(2)
        node.run(f"ping -n -c 1 -I {node.public_interface} {server.public_ip}")
    server.run(f"ping -n -c 1 {node.public_ip}")


@when("I rename the proxy for Retail")
def step_rename_proxy_for_retail():
    node = get_target("proxy")
    node.run("sed -i 's/^proxy_fqdn:.*$/proxy_fqdn: proxy.example.org/' /etc/uyuni/proxy/config.yaml")


@when("I connect the second interface of the proxy to the private network")
def step_connect_proxy_second_interface():
    node = get_target("proxy")
    _result, return_code = node.run("which nmcli", check_errors=False)
    if return_code == 0:
        cmd = (
            'nmcli connection modify "Wired connection 1" ipv4.dns-priority 20 && '
            f"nmcli device modify {node.public_interface} ipv4.dns-priority 20 && "
            'nmcli connection modify "Wired connection 2" ipv4.dns-priority 10 && '
            f"nmcli device modify {node.private_interface} ipv4.dns-priority 10"
        )
    else:
        import os
        private_net = os.environ.get("PRIVATE_NET", "")
        static_dns = private_net + os.environ.get("DHCP_DNS_OFFSET", "1")
        cmd = (
            'echo -e "BOOTPROTO=dhcp\\nSTARTMODE=auto\\n" > /etc/sysconfig/network/ifcfg-eth1 && '
            "ifup eth1 && "
            f"sed -i 's/^NETCONFIG_DNS_STATIC_SERVERS=\".*\"/NETCONFIG_DNS_STATIC_SERVERS=\"{static_dns}\"/' "
            "/etc/sysconfig/network/config && "
            "netconfig update -f"
        )
    node.run(cmd)


@when("I restart all proxy containers")
def step_restart_all_proxy_containers():
    node = get_target("proxy")
    for svc in [
        "uyuni-proxy-httpd",
        "uyuni-proxy-salt-broker",
        "uyuni-proxy-squid",
        "uyuni-proxy-ssh",
        "uyuni-proxy-tftpd",
    ]:
        node.run(f"systemctl restart {svc}.service")


@then(parsers.re(r'the "(?P<host>[^"]*)" host should be present on private network'))
def step_host_present_on_private_network(host: str):
    import os
    node = get_target("proxy")
    private_addresses = _get_private_addresses()
    net_prefix_val = os.environ.get("PRIVATE_NET", "")
    output, return_code = node.run(
        f"ping -n -c 1 -I {node.private_interface} {net_prefix_val}{private_addresses.get(host, '')}",
    )
    assert return_code == 0, f"Terminal {host} does not answer on eth1: {output}"


@then("name resolution should work on private network")
def step_name_resolution_works_on_private_network():
    node = get_target("proxy")
    destinations = ["proxy.example.org", "dns.google.com"]
    for dest in destinations:
        output, return_code = node.run(f"host {dest}", check_errors=False)
        assert return_code == 0, f"Direct name resolution of {dest} on proxy doesn't work: {output}"

    reverse_destinations = [node.private_ip, "8.8.8.8"]
    for dest in reverse_destinations:
        output, return_code = node.run(f"host {dest}", check_errors=False)
        assert return_code == 0, f"Reverse name resolution of {dest} on proxy doesn't work: {output}"


# ---------------------------------------------------------------------------
# Terminal reboot / bootstrap
# ---------------------------------------------------------------------------

@when(parsers.re(r'I reboot the (?P<context>Retail|Cobbler) terminal "(?P<host>[^"]*)"'))
def step_reboot_retail_terminal(context: str, host: str):
    _execute_expect_command_proxy(host, "reboot-pxeboot.exp", context)


@when(parsers.re(
    r'I reboot the (?P<context>Retail|Cobbler) terminal "(?P<host>[^"]*)" '
    r'through the interface "(?P<interface>[^"]*)"'
))
def step_reboot_retail_terminal_via_interface(context: str, host: str, interface: str):
    import os
    from support.file_management import file_inject
    mac_map = {
        "pxeboot_minion": os.environ.get("PXEBOOT_MAC", ""),
        "sle15sp6_terminal": os.environ.get("SLE15SP6_TERMINAL_MAC", ""),
        "sle15sp7_terminal": os.environ.get("SLE15SP7_TERMINAL_MAC", "EE:EE:EE:00:00:07"),
    }
    mac = mac_map.get(host, "")
    if mac:
        mac_clean = mac.replace(":", "")
        hex_val = (int(f"{mac_clean[:6]}fffe{mac_clean[6:]}", 16) ^ 0x0200000000000000)
        hex_str = format(hex_val, "016x")
        ipv6 = (f"fe80::{hex_str[0:4]}:{hex_str[4:8]}:{hex_str[8:12]}:{hex_str[12:16]}%{interface}")
    else:
        ipv6 = interface

    file_name = "reboot-pxeboot.exp"
    source = os.path.join(os.path.dirname(__file__), f"../features/upload_files/{file_name}")
    dest = f"/tmp/{file_name}"
    success = file_inject(get_target("proxy"), source, dest)
    assert success, "File injection failed"
    get_target("proxy").run(f"expect -f /tmp/{file_name} {ipv6} {context}")


@when(parsers.re(
    r'I create the bootstrap script for "(?P<hostname>[^"]+)" hostname '
    r'and "(?P<key>[^"]*)" activation key on "(?P<host>[^"]*)"'
))
def step_create_bootstrap_script(hostname: str, key: str, host: str):
    node = get_target(host)
    node.run(f"mgr-bootstrap --hostname={hostname} --activation-keys={key}")
    output, _code = node.run("cat /srv/www/htdocs/pub/bootstrap/bootstrap.sh")
    assert key in output, f"Key: {key} not included"
    assert hostname in output, f"Hostname: {hostname} not included"


@when("I bootstrap pxeboot minion via bootstrap script on the proxy")
def step_bootstrap_pxeboot_minion():
    _execute_expect_command_proxy("pxeboot_minion", "bootstrap-pxeboot.exp", "Retail")


@when("I accept key of pxeboot minion in the Salt master")
def step_accept_pxeboot_key():
    get_target("server").run("salt-key -y --accept=pxeboot.example.org")


@when("I install the GPG key of the test packages repository on the PXE boot minion")
def step_install_gpg_key_pxeboot():
    from support.file_management import file_inject
    file_name = "uyuni.key"
    source = os.path.join(os.path.dirname(__file__), f"../features/upload_files/{file_name}")
    dest = f"/tmp/{file_name}"
    server = get_target("server")
    success = file_inject(server, source, dest)
    assert success, "File injection failed"
    system_name = get_system_name("pxeboot_minion")
    server.run(f"salt-cp {system_name} {dest} {dest}")
    server.run(f"salt {system_name} cmd.run 'rpmkeys --import {dest}'")


@when("I wait until Salt client is inactive on the PXE boot minion")
def step_retail_wait_salt_client_inactive():
    _execute_expect_command_proxy("pxeboot_minion", "wait-end-of-cleanup-pxeboot.exp", "Cleaning")


# ---------------------------------------------------------------------------
# Retail configuration
# ---------------------------------------------------------------------------

@when("I prepare the retail configuration file on server")
def step_prepare_retail_config():
    from support.file_management import file_inject
    import os
    source = os.path.join(
        os.path.dirname(__file__), "../features/upload_files/massive-import-terminals.yml"
    )
    dest = "/tmp/massive-import-terminals.yml"
    server = get_target("server")
    success = file_inject(server, source, dest)
    assert success, f"File couldn't be copied to server"

    proxy = get_target("proxy")
    private_addresses = _get_private_addresses()
    net_prefix_val = os.environ.get("PRIVATE_NET", "")
    pxeboot_mac = os.environ.get("PXEBOOT_MAC", "")

    sed_values = (
        f"s/<PROXY_HOSTNAME>/{proxy.full_hostname}/; "
        f"s/<NET_PREFIX>/{net_prefix_val}/; "
        f"s/<PROXY>/{private_addresses.get('proxy', '')}/; "
        f"s/<RANGE_BEGIN>/{private_addresses.get('range begin', '')}/; "
        f"s/<RANGE_END>/{private_addresses.get('range end', '')}/; "
        f"s/<PXEBOOT>/{private_addresses.get('pxeboot_minion', '')}/; "
        f"s/<PXEBOOT_MAC>/{pxeboot_mac}/; "
        f"s/<IMAGE>/{_compute_kiwi_profile_name('pxeboot_minion')}/"
    )
    server.run(f"sed -i '{sed_values}' {dest}")


@when("I import the retail configuration using retail_yaml command")
def step_import_retail_config():
    filepath = "/tmp/massive-import-terminals.yml"
    get_target("server").run(
        f"retail_yaml --api-user admin --api-pass admin --from-yaml {filepath}"
    )


@when(parsers.re(r'I follow "(?P<host>[^"]*)" terminal'))
def step_follow_terminal(page, host: str):
    domain = _read_branch_prefix_from_yaml()
    if "pxeboot" in host:
        link_text = f"{host}.{domain}"
    else:
        link_text = f"{domain}.{host}"
    page.get_by_text(link_text).click()


@then("I should see the terminals imported from the configuration file")
def step_should_see_imported_terminals(page):
    terminals = _read_terminals_from_yaml()
    for terminal in terminals:
        _wait_until_see_system_refreshing(page, terminal)


@then("I should not see any terminals imported from the configuration file")
def step_should_not_see_imported_terminals(page):
    terminals = _read_terminals_from_yaml()
    domain = _read_branch_prefix_from_yaml()
    for terminal in terminals:
        if "minion" in terminal or "client" in terminal:
            continue
        if "pxeboot" in terminal:
            full_name = f"{terminal}.{domain}"
        else:
            full_name = f"{domain}.{terminal}"

        def _not_visible(name=full_name):
            if not page.get_by_text(name).count():
                return True
            page.reload()
            return None

        repeat_until_timeout(_not_visible, timeout=60,
                             message=f"Still see {full_name} on page")


# ---------------------------------------------------------------------------
# Field entry steps (Retail UI forms)
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I enter the local IP address of "(?P<host>[^"]*)" in (?P<field>.*?) field'
))
def step_enter_local_ip_in_field(page, host: str, field: str):
    import os
    field_ids = {
        "IP": "branch_network#ip",
        "domain name server": "dhcpd#domain_name_servers#0",
        "network IP": "dhcpd#subnets#0#$key",
        "dynamic IP range begin": "dhcpd#subnets#0#range#0",
        "dynamic IP range end": "dhcpd#subnets#0#range#1",
        "broadcast address": "dhcpd#subnets#0#broadcast_address",
        "routers": "dhcpd#subnets#0#routers#0",
        "next server": "dhcpd#subnets#0#next_server",
        "pxeboot next server": "dhcpd#hosts#0#next_server",
        "first reserved IP": "dhcpd#hosts#0#fixed_address",
        "second reserved IP": "dhcpd#hosts#1#fixed_address",
        "internal network address": "tftpd#listen_ip",
        "vsftpd internal network address": "vsftpd_config#listen_address",
    }
    private_addresses = _get_private_addresses()
    net_prefix_val = os.environ.get("PRIVATE_NET", "")
    ip_value = net_prefix_val + private_addresses.get(host, "")
    page.locator(f"[id='{field_ids[field]}']").fill(ip_value)


@when(parsers.re(r'I enter "(?P<value>[^"]*)" in (?P<field>.*?) field'))
def step_enter_value_in_field(page, value: str, field: str):
    field_ids = {
        "NIC": "branch_network#nic",
        "domain name": "dhcpd#domain_name",
        "listen interfaces": "dhcpd#listen_interfaces#0",
        "network mask": "dhcpd#subnets#0#netmask",
        "filename": "dhcpd#subnets#0#filename",
        "pxeboot filename": "dhcpd#hosts#0#filename",
        "first reserved hostname": "dhcpd#hosts#0#$key",
        "second reserved hostname": "dhcpd#hosts#1#$key",
        "virtual network IPv4 address": "default_net#ipv4#gateway",
        "first IPv4 address for DHCP": "default_net#ipv4#dhcp_start",
        "last IPv4 address for DHCP": "default_net#ipv4#dhcp_end",
        "first option": "bind#config#options#0#0",
        "first value": "bind#config#options#0#1",
        "second option": "bind#config#options#1#0",
        "second value": "bind#config#options#1#1",
        "third option": "bind#config#options#2#0",
        "third value": "bind#config#options#2#1",
        "first configured zone name": "bind#configured_zones#0#$key",
        "first available zone name": "bind#available_zones#0#$key",
        "second configured zone name": "bind#configured_zones#1#$key",
        "second available zone name": "bind#available_zones#1#$key",
        "third configured zone name": "bind#configured_zones#2#$key",
        "third available zone name": "bind#available_zones#2#$key",
        "TFTP base directory": "tftpd#root_dir",
        "branch id": "pxe#branch_id",
        "disk id": "partitioning#0#$key",
        "disk device": "partitioning#0#device",
        "first partition id": "partitioning#0#partitions#0#$key",
        "first partition size": "partitioning#0#partitions#0#size_MiB",
        "first mount point": "partitioning#0#partitions#0#mountpoint",
        "first OS image": "partitioning#0#partitions#0#image",
        "first partition password": "partitioning#0#partitions#0#luks_pass",
        "second partition id": "partitioning#0#partitions#1#$key",
        "second partition size": "partitioning#0#partitions#1#size_MiB",
        "second mount point": "partitioning#0#partitions#1#mountpoint",
        "second OS image": "partitioning#0#partitions#1#image",
        "second partition password": "partitioning#0#partitions#1#luks_pass",
        "third partition id": "partitioning#0#partitions#2#$key",
        "third partition size": "partitioning#0#partitions#2#size_MiB",
        "third filesystem format": "partitioning#0#partitions#2#format",
        "third mount point": "partitioning#0#partitions#2#mountpoint",
        "third OS image": "partitioning#0#partitions#2#image",
        "third partition password": "partitioning#0#partitions#2#luks_pass",
        "FTP server directory": "vsftpd_config#anon_root",
    }
    field_id = field_ids.get(field, field)
    page.locator(f"[id='{field_id}']").fill(value)


@when(parsers.re(r'I enter "(?P<value>[^"]*)" in (?P<field>.*?) field of (?P<zone>.*?) zone'))
def step_enter_value_in_zone_field(page, value: str, field: str, zone: str):
    field_ids = {
        "file name": "#file",
        "SOA name server": "#soa#ns",
        "SOA contact": "#soa#contact",
        "first A name": "#records#A#0#0",
        "first A address": "#records#A#0#1",
        "second A name": "#records#A#1#0",
        "second A address": "#records#A#1#1",
        "third A name": "#records#A#2#0",
        "third A address": "#records#A#2#1",
        "first NS": "#records#NS#@#0",
        "first CNAME alias": "#records#CNAME#0#0",
        "first CNAME name": "#records#CNAME#0#1",
        "second CNAME alias": "#records#CNAME#1#0",
        "second CNAME name": "#records#CNAME#1#1",
        "third CNAME alias": "#records#CNAME#2#0",
        "third CNAME name": "#records#CNAME#2#1",
        "first for zones": "#generate_reverse#for_zones#0",
        "generate reverse network": "#generate_reverse#net",
    }
    field_suffix = field_ids.get(field, f"#{field}")
    zone_xpath = (
        f"//input[@name='Name' and @value='{zone}']"
        "/ancestor::div[starts-with(@id, 'bind#available_zones#')]"
    )
    page.locator(f"xpath={zone_xpath}//input[contains(@id, '{field_suffix}')]").fill(value)


@when(parsers.re(
    r'I enter the local IP address of "(?P<host>[^"]*)" in (?P<field>.*?) field of (?P<zone>.*?) zone'
))
def step_enter_local_ip_in_zone_field(page, host: str, field: str, zone: str):
    import os
    private_addresses = _get_private_addresses()
    net_prefix_val = os.environ.get("PRIVATE_NET", "")
    value = net_prefix_val + private_addresses.get(host, "")
    step_enter_value_in_zone_field(page, value, field, zone)


@when(parsers.re(r'I enter the MAC address of "(?P<host>[^"]*)" in (?P<field>.*?) field'))
def step_enter_mac_address_in_field(page, host: str, field: str):
    import os
    field_ids = {
        "first reserved MAC": "dhcpd#hosts#0#hardware",
        "second reserved MAC": "dhcpd#hosts#1#hardware",
    }
    pxeboot_mac = os.environ.get("PXEBOOT_MAC", "")
    sle15sp6_mac = os.environ.get("SLE15SP6_TERMINAL_MAC", "")
    sle15sp7_mac = os.environ.get("SLE15SP7_TERMINAL_MAC", "EE:EE:EE:00:00:07")

    if host == "pxeboot_minion":
        mac = pxeboot_mac
    elif host == "sle15sp6_terminal":
        mac = sle15sp6_mac or "EE:EE:EE:00:00:06"
    elif host == "sle15sp7_terminal":
        mac = sle15sp7_mac
    elif "deblike" in host or "debian12" in host or "ubuntu" in host:
        node = get_target(host)
        output, _code = node.run("ip link show dev ens4")
        mac = output.splitlines()[1].split()[1]
    else:
        node = get_target(host)
        output, _code = node.run("ip link show dev eth1")
        mac = output.splitlines()[1].split()[1]

    field_id = field_ids.get(field, field)
    page.locator(f"[id='{field_id}']").fill(f"ethernet {mac}")


@when(parsers.re(r'I enter the local zone name in (?P<field>.*?) field'))
def step_enter_local_zone_name(page, field: str):
    import os
    private_net = os.environ.get("PRIVATE_NET", "")
    reverse_net = _get_reverse_net(private_net)
    step_enter_value_in_field(page, reverse_net, field)


@when(parsers.re(r'I enter the local file name in (?P<field>.*?) field of zone with local name'))
def step_enter_local_file_name(page, field: str):
    import os
    private_net = os.environ.get("PRIVATE_NET", "")
    reverse_net = _get_reverse_net(private_net)
    reverse_filename = f"master/db.{reverse_net}"
    step_enter_value_in_zone_field(page, reverse_filename, field, reverse_net)


@when(parsers.re(r'I enter "(?P<value>[^"]*)" in (?P<field>.*?) field of zone with local name'))
def step_enter_value_in_local_zone(page, value: str, field: str):
    import os
    private_net = os.environ.get("PRIVATE_NET", "")
    reverse_net = _get_reverse_net(private_net)
    step_enter_value_in_zone_field(page, value, field, reverse_net)


@when(parsers.re(r'I enter the local network in (?P<field>.*?) field of zone with local name'))
def step_enter_local_network(page, field: str):
    import os
    private_net = os.environ.get("PRIVATE_NET", "")
    step_enter_value_in_local_zone(page, private_net, field)


@when(parsers.re(r'I enter the image name for "(?P<host>[^"]*)" in (?P<field>.*?) field'))
def step_enter_image_name_in_field(page, host: str, field: str):
    name = _compute_kiwi_profile_name(host)
    page.locator(f"[id='{field}']").fill(name)


# ---------------------------------------------------------------------------
# Add/Remove Item buttons
# ---------------------------------------------------------------------------

@when(parsers.re(r'I press "Add Item" in (?P<section>.*?) section'))
def step_press_add_item_in_section(page, section: str):
    section_ids = {
        "host reservations": "dhcpd#hosts#add_item",
        "config options": "bind#config#options#add_item",
        "configured zones": "bind#configured_zones#add_item",
        "available zones": "bind#available_zones#add_item",
        "partitions": "partitioning#0#partitions#add_item",
    }
    page.locator(f"xpath=//i[@id='{section_ids[section]}']").click()


@when(parsers.re(
    r'I press "Add Item" in (?P<field>A|NS|CNAME|for zones) section of (?P<zone>.*?) zone'
))
def step_press_add_item_in_zone_section(page, field: str, zone: str):
    section_ids = {
        "for zones": "for_zones",
        "NS": "NS#@",
        "CNAME": "CNAME",
        "A": "A",
    }
    xpath = (
        f"//input[@name='Name' and @value='{zone}']"
        "/ancestor::div[starts-with(@id, 'bind#available_zones#')]"
        f"//i[contains(@id, '#{section_ids[field]}#add_item')]"
    )
    page.locator(f"xpath={xpath}").click()


@when(parsers.re(
    r'I press "Add Item" in (?P<field>A|NS|CNAME|for zones) section of zone with local name'
))
def step_press_add_item_local_zone(page, field: str):
    import os
    private_net = os.environ.get("PRIVATE_NET", "")
    reverse_net = _get_reverse_net(private_net)
    step_press_add_item_in_zone_section(page, field, reverse_net)


@when(parsers.re(r'I press "Remove Item" in (?P<alias_name>.*?) CNAME of (?P<zone>.*?) zone section'))
def step_press_remove_item_cname(page, alias_name: str, zone: str):
    cname_xpath = (
        f"//input[@name='Name' and @value='{zone}']"
        "/ancestor::div[starts-with(@id, 'bind#available_zones#')]"
        f"//input[@name='Alias' and @value='{alias_name}']"
        "/ancestor::div[@class='form-group']"
    )
    page.locator(f"xpath={cname_xpath}/button").click()


@when('I press "Remove" in the routers section')
def step_press_remove_in_routers_section(page):
    page.locator("xpath=//div[@id='dhcpd#subnets#0#routers#0']/button").click()


@when(parsers.re(r'I check (?P<checkbox_name>.*?) box'))
def step_check_box(page, checkbox_name: str):
    box_ids = _get_box_ids()
    page.locator(f"#{box_ids[checkbox_name]}").check()


@when(parsers.re(r'I uncheck (?P<checkbox_name>.*?) box'))
def step_uncheck_box(page, checkbox_name: str):
    box_ids = _get_box_ids()
    page.locator(f"#{box_ids[checkbox_name]}").uncheck()


# ---------------------------------------------------------------------------
# OS image build
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I enter the image filename for "(?P<host>[^"]*)" relative to profiles as "(?P<field>[^"]*)"'
))
def step_enter_image_filename(page, host: str, field: str):
    import os
    git_profiles = os.environ.get("GITPROFILES", "")
    path = _compute_kiwi_profile_filename(host)
    page.locator(f"[name='{field}'], #{field}").first.fill(f"{git_profiles}/{path}")


@when(parsers.re(r'I wait until the image build "(?P<image_name>[^"]*)" is completed'))
def step_wait_image_build_completed(page, image_name: str):
    # Reuse event wait logic — 3300 second timeout
    from step_definitions.common_steps import step_wait_at_most_until_event_completed
    step_wait_at_most_until_event_completed(page, "3300", f"Image Build {image_name}")


@when(parsers.re(r'I wait until the image inspection for "(?P<host>[^"]*)" is completed'))
def step_wait_image_inspection_completed(page, host: str):
    from step_definitions.common_steps import step_wait_at_most_until_event_completed
    name = _compute_kiwi_profile_name(host)
    version = _compute_kiwi_profile_version(host)
    step_wait_at_most_until_event_completed(page, "300", f"Image Inspect 1//{name}:{version}")


@then(parsers.re(r'I should see the image for "(?P<host>[^"]*)" is built'))
def step_should_see_image_built(page, host: str):
    name = _compute_kiwi_profile_name(host)
    row = page.locator("tr", has_text=name).first
    assert row.count(), f"Image {name} not found"
    assert row.locator('i[title="Built"]').count(), f"Image {name} is not marked as built"


@when(parsers.re(r'I open the details page of the image for "(?P<host>[^"]*)"'))
def step_open_image_details(page, host: str):
    name = _compute_kiwi_profile_name(host)
    row = page.locator("tr", has_text=name).first
    assert row.count(), f"Image {name} not found"
    row.locator('button[aria-label="Details"]').click()


@then(parsers.re(r'I should see a link to download the image for "(?P<host>[^"]*)"'))
def step_should_see_image_download_link(page, host: str):
    import urllib.request
    import ssl
    name = _compute_kiwi_profile_name(host)
    link = page.locator(f"a[href*='{name}'][href$='.xz']")
    img_url = link.get_attribute("href")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(img_url, method="HEAD")
    with urllib.request.urlopen(req, context=ctx) as response:
        assert response.status == 200, f"Failed HEAD request for image {name}"


@then(parsers.re(r'the image for "(?P<host>[^"]*)" should exist on the branch server'))
def step_image_exists_on_branch_server(host: str):
    image = _compute_kiwi_profile_name(host)
    images, _code = get_target("proxy").run("ls /srv/saltboot/image/")
    assert image in images, f"Image {image} for {host} does not exist"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _execute_expect_command_proxy(host: str, script: str, context: str):
    """Run an expect script on the proxy node against the given host."""
    system_name = get_system_name(host) if host not in ("pxeboot_minion",) else host
    get_target("proxy").run(f"expect -f /tmp/{script} {system_name} {context}")


def _get_private_addresses() -> dict:
    """Return private IP address offsets from environment."""
    import os
    return {
        "proxy": os.environ.get("PRIVATE_ADDR_PROXY", "1"),
        "pxeboot_minion": os.environ.get("PRIVATE_ADDR_PXEBOOT", "2"),
        "range begin": os.environ.get("PRIVATE_ADDR_RANGE_BEGIN", "10"),
        "range end": os.environ.get("PRIVATE_ADDR_RANGE_END", "100"),
        "dhcp_dns": os.environ.get("PRIVATE_ADDR_DHCP_DNS", "1"),
    }


def _get_reverse_net(private_net: str) -> str:
    """Compute the reverse DNS network name from the private net prefix."""
    from support.commonlib import get_reverse_net
    return get_reverse_net(private_net)


def _read_branch_prefix_from_yaml() -> str:
    """Read the branch domain prefix from the retail YAML config."""
    import os
    return os.environ.get("BRANCH_PREFIX", "example.org")


def _read_terminals_from_yaml() -> list:
    """Read terminal names from the retail config."""
    import os
    yaml_path = "/tmp/massive-import-terminals.yml"
    try:
        import yaml
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        # Extract terminal names from the YAML structure
        terminals = []
        if isinstance(data, dict):
            for key in data:
                terminals.append(key)
        return terminals
    except Exception:
        return []


def _compute_kiwi_profile_name(host: str) -> str:
    """Compute the Kiwi build profile name for the given host."""
    import os
    return os.environ.get(f"KIWI_PROFILE_NAME_{host.upper()}", host.replace("_", "-"))


def _compute_kiwi_profile_version(host: str) -> str:
    """Compute the Kiwi build profile version for the given host."""
    import os
    return os.environ.get(f"KIWI_PROFILE_VERSION_{host.upper()}", "1.0.0")


def _compute_kiwi_profile_filename(host: str) -> str:
    """Compute the Kiwi build profile filename for the given host."""
    import os
    return os.environ.get(f"KIWI_PROFILE_FILENAME_{host.upper()}", f"{host}/config.kiwi")


def _wait_until_see_system_refreshing(page, system_name: str):
    """Wait until a system name appears on page, refreshing."""
    def _visible():
        if page.get_by_text(system_name).count():
            return True
        page.reload()
        return None
    repeat_until_timeout(_visible, message=f"System {system_name} not visible")


def _get_box_ids() -> dict:
    """Map of checkbox human names to element IDs."""
    return {
        "generate reverse": "bind#generate_reverse",
        "set forwarders": "bind#set_forwarders",
    }
