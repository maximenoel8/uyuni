# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/cobbler_steps.rb.

Covers all steps concerning Cobbler: daemon control, distro/profile/system
management, buildiso, xorriso verification, settings, and log checks.
"""

import json
import os

from pytest_bdd import given, when, then, parsers

from support.remote_nodes_env import get_target
from support.commonlib import repeat_until_timeout, check_text, click_button_and_wait
from support.env import DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# Cobbler daemon
# ---------------------------------------------------------------------------

@given("cobblerd is running")
def step_cobblerd_is_running():
    _out, code = get_target("server").run(
        "systemctl is-active cobblerd.service", check_errors=False
    )
    assert code == 0, "cobblerd is not running"


@when("I restart cobbler on the server")
def step_restart_cobbler():
    get_target("server").run("systemctl restart cobblerd.service")


@given(parsers.re(r'I am logged in via the Cobbler API as user "(?P<user>[^"]*)" with password "(?P<pwd>[^"]*)"'))
def step_login_cobbler_api(user: str, pwd: str, context_store):
    # Store credentials for later Cobbler API calls via spacecmd/cobbler CLI
    context_store["cobbler_user"] = user
    context_store["cobbler_password"] = pwd


@when("I log out from Cobbler via the API")
def step_logout_cobbler_api(context_store):
    context_store.pop("cobbler_user", None)
    context_store.pop("cobbler_password", None)


# ---------------------------------------------------------------------------
# Distro, profile, and system management
# ---------------------------------------------------------------------------

@given(parsers.re(r'distro "(?P<distro>[^"]*)" exists'))
def step_distro_exists(distro: str):
    out, code = get_target("server").run(
        f"cobbler distro list | grep -w {distro}", check_errors=False
    )
    assert code == 0, f"Distro {distro} does not exist"


@given(parsers.re(r'profile "(?P<profile>[^"]*)" exists'))
def step_profile_exists(profile: str):
    out, code = get_target("server").run(
        f"cobbler profile list | grep -w {profile}", check_errors=False
    )
    assert code == 0, f"Profile {profile} does not exist"


@when(parsers.re(r'I create distro "(?P<distro>[^"]*)"'))
def step_create_distro(distro: str):
    out, code = get_target("server").run(
        f"cobbler distro list | grep -w {distro}", check_errors=False
    )
    assert code != 0, f"Distro {distro} already exists"
    get_target("server").run(
        f"cobbler distro add --name={distro} "
        "--kernel=/var/autoinstall/SLES15-SP7-x86_64/DVD1/boot/x86_64/loader/linux "
        "--initrd=/var/autoinstall/SLES15-SP7-x86_64/DVD1/boot/x86_64/loader/initrd"
    )


@when(parsers.re(r'I create profile "(?P<profile>[^"]*)" for distro "(?P<distro>[^"]*)"'))
def step_create_profile(profile: str, distro: str):
    out, code = get_target("server").run(
        f"cobbler profile list | grep -w {profile}", check_errors=False
    )
    assert code != 0, f"Profile {profile} already exists"
    get_target("server").run(
        f"cobbler profile add --name={profile} --distro={distro} "
        "--autoinstall=/var/autoinstall/mock/empty.xml"
    )


@when(parsers.re(r'I create system "(?P<system>[^"]*)" for profile "(?P<profile>[^"]*)"'))
def step_create_system(system: str, profile: str):
    out, code = get_target("server").run(
        f"cobbler system list | grep -w {system}", check_errors=False
    )
    assert code != 0, f"System {system} already exists"
    get_target("server").run(
        f"cobbler system add --name={system} --profile={profile}"
    )


@when(parsers.re(r'I remove system "(?P<system>[^"]*)"'))
def step_remove_system(system: str):
    get_target("server").run(f"cobbler system remove --name={system}", check_errors=False)


@when(parsers.re(r'I remove profile "(?P<profile>[^"]*)"'))
def step_remove_profile(profile: str):
    get_target("server").run(f"cobbler profile remove --name={profile}", check_errors=False)


@when(parsers.re(r'I remove distro "(?P<distro>[^"]*)"'))
def step_remove_distro(distro: str):
    get_target("server").run(f"cobbler distro remove --name={distro}", check_errors=False)


# ---------------------------------------------------------------------------
# Cobbler reports
# ---------------------------------------------------------------------------

@when("I clear the caches on the server")
def step_clear_caches():
    get_target("server").run("spacecmd -u admin -p admin clear_caches")


@when(parsers.re(r'I click on profile "(?P<profile>[^"]*)"'))
def step_click_on_profile(page, profile: str):
    xpath = f"//a[text()='{profile}']/../../td[1]/input[@type='radio']"
    page.locator(f"xpath={xpath}").click()


@then(parsers.re(r'the cobbler report should contain "(?P<text>[^"]*)" for "(?P<host>[^"]*)"'))
def step_cobbler_report_contains_for_host(text: str, host: str):
    node = get_target(host)
    output, _code = get_target("server").run(
        f"cobbler system report --name {node.full_hostname}:1", check_errors=False
    )
    assert text in output, f"Not found:\n{output}"


@then(parsers.re(
    r'the cobbler report should contain "(?P<text>[^"]*)" for cobbler system name "(?P<name>[^"]*)"'
))
def step_cobbler_report_contains_for_name(text: str, name: str):
    output, _code = get_target("server").run(
        f"cobbler system report --name {name}", check_errors=False
    )
    assert text in output, f"Not found:\n{output}"


# ---------------------------------------------------------------------------
# buildiso
# ---------------------------------------------------------------------------

@when("I prepare Cobbler for the buildiso command")
def step_prepare_cobbler_buildiso():
    tmp_dir = "/var/cache/cobbler/buildiso"
    server = get_target("server")
    server.run(f"mkdir -p {tmp_dir}")
    out, code = server.run("cobbler mkloaders", verbose=True)
    assert code == 0, f"error in cobbler mkloaders.\nLogs:\n{out}"


@when(parsers.re(r'I run Cobbler buildiso for distro "(?P<distro>[^"]*)" and all profiles'))
def step_run_cobbler_buildiso_all_profiles(distro: str):
    tmp_dir = "/var/cache/cobbler/buildiso"
    iso_dir = "/var/cache/cobbler"
    server = get_target("server")
    out, code = server.run(
        f"cobbler buildiso --tempdir={tmp_dir} --iso {iso_dir}/profile_all.iso --distro={distro}",
        verbose=True
    )
    assert code == 0, f"error in cobbler buildiso.\nLogs:\n{out}"

    profiles = ["orchid", "flame", "pearl"]
    cobbler_profiles = []
    isolinux_profiles = []
    for profile in profiles:
        result_cobbler, code = server.run(
            f"cobbler profile list | grep -o {profile}", verbose=True
        )
        if code == 0:
            cobbler_profiles.append(result_cobbler.strip())
        result_isolinux, _code = server.run(
            f"cat {tmp_dir}/isolinux/isolinux.cfg | grep -o {profile} | cut -c -6 | head -n 1"
        )
        if result_isolinux.strip():
            isolinux_profiles.append(result_isolinux.strip())
    assert cobbler_profiles == isolinux_profiles, \
        f"Cobbler profiles don't match isolinux profiles.\nCobbler: {cobbler_profiles}\nisolinux: {isolinux_profiles}"


@when(parsers.re(
    r'I run Cobbler buildiso for distro "(?P<distro>[^"]*)" and profile "(?P<profile>[^"]*)"'
))
def step_run_cobbler_buildiso_profile(distro: str, profile: str):
    tmp_dir = "/var/cache/cobbler/buildiso"
    iso_dir = "/var/cache/cobbler"
    out, code = get_target("server").run(
        f"cobbler buildiso --tempdir={tmp_dir} --iso {iso_dir}/{profile}.iso "
        f"--distro={distro} --profile={profile}",
        verbose=True
    )
    assert code == 0, f"error in cobbler buildiso.\nLogs:\n{out}"


@when(parsers.re(
    r'I run Cobbler buildiso for distro "(?P<distro>[^"]*)" and profile "(?P<profile>[^"]*)" '
    r'without dns entries'
))
def step_run_cobbler_buildiso_no_dns(distro: str, profile: str):
    tmp_dir = "/var/cache/cobbler/buildiso"
    iso_dir = "/var/cache/cobbler"
    server = get_target("server")
    out, code = server.run(
        f"cobbler buildiso --tempdir={tmp_dir} --iso {iso_dir}/{profile}.iso "
        f"--distro={distro} --profile={profile} --exclude-dns",
        verbose=True
    )
    assert code == 0, f"error in cobbler buildiso.\nLogs:\n{out}"
    result, code = server.run(
        f"cat {tmp_dir}/isolinux/isolinux.cfg | grep -o nameserver", check_errors=False
    )
    assert code != 0, \
        f"error in Cobbler buildiso, nameserver parameter found in isolinux.cfg but should not be found.\nLogs:\n{result}"


@when(parsers.re(r'I run Cobbler buildiso "(?P<param>[^"]*)" for distro "(?P<distro>[^"]*)"'))
def step_run_cobbler_buildiso_param(param: str, distro: str):
    step_run_cobbler_buildiso_all_profiles(distro)
    tmp_dir = "/var/cache/cobbler/buildiso"
    iso_dir = "/var/cache/cobbler"
    source_dir = f"/var/cache/cobbler/source_{param}"
    server = get_target("server")
    server.run(f"mv {tmp_dir} {source_dir}")
    server.run(f"mkdir -p {tmp_dir}")
    out, code = server.run(
        f"cobbler buildiso --tempdir={tmp_dir} --iso {iso_dir}/{param}.iso "
        f"--distro={distro} --{param} --source={source_dir}",
        verbose=True
    )
    assert code == 0, f"error in cobbler buildiso.\nLogs:\n{out}"


@when(parsers.re(r'I check Cobbler buildiso ISO "(?P<name>[^"]*)" with xorriso'))
def step_check_cobbler_buildiso_iso_xorriso(name: str):
    tmp_dir = "/var/cache/cobbler"
    server = get_target("server")
    server.run(f"cat >{tmp_dir}/test_image <<-EOF\nBIOS\nUEFI\nEOF")
    xorriso = f"xorriso -indev {tmp_dir}/{name}.iso -report_el_torito 2>/dev/null"
    iso_filter = r"awk '/^El Torito boot img[[:space:]]+:[[:space:]]+[0-9]+[[:space:]]+[a-zA-Z]+[[:space:]]+y/{print $7}'"
    iso_file = f"{tmp_dir}/xorriso_{name}"
    out, code = server.run(f"{xorriso} | {iso_filter} >> {iso_file}")
    assert code == 0, f"error while executing xorriso.\nLogs:\n{out}"
    out, code = server.run(f"diff {tmp_dir}/test_image {tmp_dir}/xorriso_{name}")
    assert code == 0, f"error in verifying Cobbler buildiso image with xorriso.\nLogs:\n{out}"


# ---------------------------------------------------------------------------
# xorriso
# ---------------------------------------------------------------------------

@when("I cleanup xorriso temp files")
def step_cleanup_xorriso_temp_files():
    get_target("server").run("rm /var/cache/cobbler/xorriso_*", check_errors=False)


# ---------------------------------------------------------------------------
# cobbler settings
# ---------------------------------------------------------------------------

@given("cobbler settings are successfully migrated")
def step_cobbler_settings_migrated():
    out, code = get_target("server").run(
        "cobbler-settings migrate -t /etc/cobbler/settings.yaml"
    )
    assert code == 0, f"error when running cobbler-settings to migrate current settings.\nLogs:\n{out}"


# ---------------------------------------------------------------------------
# cobbler parameters
# ---------------------------------------------------------------------------

@then(parsers.re(
    r'I add the Cobbler parameter "(?P<param>[^"]*)" with value "(?P<value>[^"]*)" '
    r'to item "(?P<item>distro|profile|system)" with name "(?P<name>[^"]*)"'
))
def step_add_cobbler_parameter(param: str, value: str, item: str, name: str):
    result, code = get_target("server").run(
        f"cobbler {item} edit --name={name} --{param}={value}", verbose=True
    )
    assert code == 0, f"error in adding parameter and value to Cobbler {item}.\nLogs:\n{result}"


@when(parsers.re(
    r'I check the Cobbler parameter "(?P<param>[^"]*)" with value "(?P<value>[^"]*)" '
    r'in the isolinux.cfg'
))
def step_check_cobbler_parameter_isolinux(param: str, value: str):
    tmp_dir = "/var/cache/cobbler/buildiso"
    result, code = get_target("server").run(
        f"cat {tmp_dir}/isolinux/isolinux.cfg | grep -o {param}={value}"
    )
    assert code == 0, f"error while verifying isolinux.cfg parameter for Cobbler buildiso.\nLogs:\n{result}"


# ---------------------------------------------------------------------------
# backup step
# ---------------------------------------------------------------------------

@when("I backup Cobbler settings file")
def step_backup_cobbler_settings():
    get_target("server").run(
        "cp /etc/cobbler/settings.yaml /etc/cobbler/settings.yaml.bak 2> /dev/null",
        check_errors=False
    )


# ---------------------------------------------------------------------------
# cleanup steps
# ---------------------------------------------------------------------------

@when("I cleanup after Cobbler buildiso")
def step_cleanup_after_cobbler_buildiso():
    result, code = get_target("server").run("rm -Rf /var/cache/cobbler")
    assert code == 0, f"Error during Cobbler buildiso cleanup.\nLogs:\n{result}"


# ---------------------------------------------------------------------------
# cobbler commands
# ---------------------------------------------------------------------------

@when("I copy autoinstall mocked files on server")
def step_copy_autoinstall_mocked_files():
    from support.file_management import file_inject
    server = get_target("server")
    target_dirs = (
        "/var/autoinstall/Fedora_12_i386/images/pxeboot "
        "/var/autoinstall/SLES15-SP7-x86_64/DVD1/boot/x86_64/loader "
        "/var/autoinstall/mock"
    )
    server.run(f"mkdir -p {target_dirs}")
    base_dir = os.path.join(
        os.path.dirname(__file__), "../features/upload_files/autoinstall/cobbler/"
    )
    source_dir = "/var/autoinstall/"
    injections = [
        (f"{base_dir}fedora12/vmlinuz", f"{source_dir}Fedora_12_i386/images/pxeboot/vmlinuz"),
        (f"{base_dir}fedora12/initrd.img", f"{source_dir}Fedora_12_i386/images/pxeboot/initrd.img"),
        (f"{base_dir}mock/empty.xml", f"{source_dir}mock/empty.xml"),
        (f"{base_dir}sles15sp7/initrd", f"{source_dir}SLES15-SP7-x86_64/DVD1/boot/x86_64/loader/initrd"),
        (f"{base_dir}sles15sp7/linux", f"{source_dir}SLES15-SP7-x86_64/DVD1/boot/x86_64/loader/linux"),
    ]
    for local, remote in injections:
        success = file_inject(server, local, remote)
        assert success, f"File injection failed: {local} -> {remote}"


@when(parsers.re(r'I run Cobbler sync (?P<checking>with|without) error checking'))
def step_run_cobbler_sync(checking: str):
    out, _code = get_target("server").run("cobbler sync")
    if checking == "with":
        assert "Push failed" not in out, "cobbler sync failed"


@when("I start local monitoring of Cobbler")
def step_start_local_monitoring_of_cobbler():
    server = get_target("server")
    cobbler_conf_file = "/etc/cobbler/logging_config.conf"
    cobbler_log_file = "/var/log/cobbler/cobbler_debug.log"
    server.run(f"rm {cobbler_log_file}", check_errors=False)
    _result, code = server.run(f"test -f {cobbler_conf_file}.old", check_errors=False)
    if code == 0:
        server.run("systemctl restart cobblerd")
    else:
        handler_name = "FileLogger02"
        formatter_name = "JSONlogfile"
        handler_class = (
            f'"\n[handler_{handler_name}]\n'
            "class=FileHandler\n"
            "level=DEBUG\n"
            f"formatter={formatter_name}\n"
            f"args=('{cobbler_log_file}', 'a')\n\n"
            f"[formatter_{formatter_name}]\n"
            "format ={\\''threadName\\'': \\''%(threadName)s\\'', "
            "\\''asctime\\'': \\''%(asctime)s\\'', \\''levelname\\'':  \\''%(levelname)s\\'', "
            "\\''message\\'': \\''%(message)s\\''}\n\""
        )
        command = (
            f"cp {cobbler_conf_file} {cobbler_conf_file}.old && "
            f"line_number=`awk \"/\\[handlers\\]/{{ print NR; exit }}\" {cobbler_conf_file}` && "
            f"sed -e \"$(($line_number + 1))s/$/,{handler_name}/\" -i {cobbler_conf_file} && "
            f"line_number=`awk \"/\\[formatters\\]/{{ print NR; exit }}\" {cobbler_conf_file}` && "
            f"sed -e \"$(($line_number + 1))s/$/,{formatter_name}/\" -i {cobbler_conf_file} && "
            f"line_number=`awk \"/\\[logger_root\\]/{{ print NR; exit }}\" {cobbler_conf_file}` && "
            f"sed -e \"$(($line_number + 2))s/$/,{handler_name}/\" -i {cobbler_conf_file} && "
            f"echo -e {handler_class} >> {cobbler_conf_file}"
        )
        server.run(f"{command} && systemctl restart cobblerd")
    import time
    time.sleep(3)


@then("the local logs for Cobbler should not contain errors")
def step_cobbler_logs_no_errors():
    from support.file_management import file_extract
    node = get_target("server")

    # Normal log
    cobbler_log_file = "/var/log/cobbler/cobbler.log"
    remote_file = "/tmp/cobbler.copy"
    local_file = "/tmp/cobbler.log"
    node.run(f"cp {cobbler_log_file} {remote_file}")
    success = file_extract(node, remote_file, local_file)
    assert success, "File extraction failed"

    with open(local_file) as f:
        output = [line for line in f if "ERROR" in line]

    if output:
        node.run(f'cp {remote_file} {cobbler_log_file}-$(date +"%Y_%m_%d_%I_%M_%p")')

    # Debug log
    cobbler_log_file = "/var/log/cobbler/cobbler_debug.log"
    remote_file = "/tmp/cobbler_debug.copy"
    local_file = "/tmp/cobbler_debug.log"
    node.run(f"cp {cobbler_log_file} {remote_file}")
    success = file_extract(node, remote_file, local_file)
    assert success, "File extraction failed"

    with open(local_file) as f:
        file_data = f.read()

    # Parse JSON log lines
    output_debug = []
    for line in file_data.splitlines():
        line = line.strip().rstrip(",")
        if not line:
            continue
        try:
            entry = json.loads(line)
            if isinstance(entry, dict) and entry.get("levelname") == "ERROR":
                output_debug.append(entry)
        except json.JSONDecodeError:
            pass

    if output_debug:
        node.run(f'cp {remote_file} {cobbler_log_file}-$(date +"%Y_%m_%d_%I_%M_%p")')

    assert not output and not output_debug, "Errors in Cobbler logs"
