# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/docker_steps.rb.

Covers Docker / container image steps: image builds, inspections,
image stores, profiles, and scheduling via API.
"""

import os
import re
import time

from pytest_bdd import given, when, then, parsers

from support.remote_nodes_env import get_target
from support.commonlib import repeat_until_timeout, check_text
from support.env import DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# Profile path entry
# ---------------------------------------------------------------------------

@when(parsers.re(r'I enter "(?P<path>[^"]*)" relative to profiles as "(?P<field>[^"]*)"'))
def step_enter_relative_to_profiles(page, path: str, field: str):
    git_profiles = os.environ.get("GITPROFILES", "")
    system_name = get_target("server").full_hostname
    if re.search(r"\.mgr\.suse\.de$", system_name):
        domain_folder = "internal_nue"
    elif re.search(r"\.mgr\.slc1\.suse\.org$", system_name):
        domain_folder = "internal_slc1"
    elif re.search(r"sumaci\.aws$|\.compute\.internal$", system_name):
        domain_folder = "cloud_aws"
    else:
        print(f"Warning: Unknown domain pattern for system_name: {system_name}. Using root path.")
        domain_folder = ""

    full_path = os.path.join(git_profiles, "docker_profiles", domain_folder, path)
    page.locator(f"[name='{field}'], #{field}").first.fill(full_path)


# ---------------------------------------------------------------------------
# Registry credentials
# ---------------------------------------------------------------------------

@when("I enter URI, username and password for registry")
def step_enter_registry_credentials(page):
    creds = os.environ.get("AUTH_REGISTRY_CREDENTIALS", "|")
    auth_registry_username, auth_registry_password = creds.split("|", 1)
    auth_registry = os.environ.get("AUTH_REGISTRY", "")
    page.locator("[name='uri'], #uri").first.fill(auth_registry)
    page.locator("[name='username'], #username").first.fill(auth_registry_username)
    page.locator("[name='password'], #password").first.fill(auth_registry_password)


# ---------------------------------------------------------------------------
# Image build / inspect via API
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I wait at most (?P<timeout>\d+) seconds until image "(?P<name>[^"]*)" '
    r'with version "(?P<version>[^"]*)" is built successfully via API'
))
def step_wait_image_built_via_api(api_test, timeout: str, name: str, version: str):
    image_id = 0

    def _built():
        nonlocal image_id
        if image_id == 0:
            images_list = api_test.image.list_images()
            for element in images_list:
                if element["name"] == name and element["version"] == version:
                    image_id = element["id"]
                    break
        else:
            image_details = api_test.image.get_details(image_id)
            if image_details["buildStatus"] == "completed":
                return True
            if image_details["buildStatus"] == "failed":
                raise RuntimeError("image build failed.")
        time.sleep(5)
        return None

    repeat_until_timeout(_built, timeout=int(timeout),
                         message="image build did not complete")
    assert image_id != 0, "unable to find the image id"


@when(parsers.re(
    r'I wait at most (?P<timeout>\d+) seconds until image "(?P<name>[^"]*)" '
    r'with version "(?P<version>[^"]*)" is inspected successfully via API'
))
def step_wait_image_inspected_via_api(api_test, timeout: str, name: str, version: str):
    images_list = api_test.image.list_images()
    image_id = 0
    for element in images_list:
        if element["name"] == name and element["version"] == version:
            image_id = element["id"]
            break
    assert image_id != 0, "unable to find the image id"

    def _inspected():
        image_details = api_test.image.get_details(image_id)
        if image_details["inspectStatus"] == "completed":
            return True
        if image_details["inspectStatus"] == "failed":
            raise RuntimeError("image inspect failed.")
        time.sleep(5)
        return None

    repeat_until_timeout(_inspected, timeout=int(timeout),
                         message="image inspection did not complete")


@when(parsers.re(
    r'I wait at most (?P<timeout>\d+) seconds until all "(?P<count>[^"]*)" '
    r'container images are built correctly on the Image List page'
))
def step_wait_all_images_built(page, timeout: str, count: str):
    def _all_built():
        from support.embedded_steps.navigation_helper import follow_left_menu
        follow_left_menu(page, "Images > Image List")

        def _not_empty():
            if not page.get_by_text("There are no entries to show.").count():
                return True
            return None
        repeat_until_timeout(_not_empty, timeout=10)

        if page.locator(
            "xpath=//tr[td[text()='Container Image']][td//*[contains(@title, 'Failed')]]"
        ).count():
            raise RuntimeError("error detected while building images")
        if page.locator(
            f"xpath=//tr[td[text()='Container Image']][td//*[contains(@title, 'Built')]]"
        ).count() >= int(count):
            return True
        time.sleep(5)
        return None

    repeat_until_timeout(_all_built, timeout=int(timeout),
                         message="at least one image was not built correctly")


@when(parsers.re(r'I schedule the build of image "(?P<image>[^"]*)" via API calls'))
def step_schedule_image_build(api_test):
    pass  # image arg captured but not used here — called differently
    # This step requires both image name and is called via pattern matching


@when(parsers.re(r'I schedule the build of image "(?P<image>[^"]*)" via API calls'))
def step_schedule_image_build_v2(api_test, image: str):
    build_host_id = _retrieve_build_host_id(api_test)
    date_build = api_test.date_now()
    api_test.image.schedule_image_build(image, "", build_host_id, date_build)


@when(parsers.re(
    r'I schedule the build of image "(?P<image>[^"]*)" with version "(?P<version>[^"]*)" via API calls'
))
def step_schedule_image_build_with_version(api_test, image: str, version: str):
    build_host_id = _retrieve_build_host_id(api_test)
    date_build = api_test.date_now()
    api_test.image.schedule_image_build(image, version, build_host_id, date_build)


@when(parsers.re(
    r'I delete the image "(?P<image_name_todel>[^"]*)" with version "(?P<version>[^"]*)" via API calls'
))
def step_delete_image_via_api(api_test, image_name_todel: str, version: str):
    images_list = api_test.image.list_images()
    assert images_list is not None, "ERROR: no images at all were retrieved."
    image_id = 0
    for element in images_list:
        if element["name"].strip() == image_name_todel.strip() and element["version"].strip() == version.strip():
            image_id = element["id"]
    if image_id == 0:
        print(f"Image {image_name_todel} with version {version} does not exist, skipping")
    else:
        api_test.image.delete(image_id)


@then(parsers.re(
    r'the list of packages of image "(?P<name>[^"]*)" with version "(?P<version>[^"]*)" is not empty'
))
def step_image_packages_not_empty(api_test, name: str, version: str):
    images_list = api_test.image.list_images()
    image_id = 0
    for element in images_list:
        if element["name"] == name and element["version"] == version:
            image_id = element["id"]
            break
    assert image_id != 0, "unable to find the image id"
    image_details = api_test.image.get_details(image_id)
    assert image_details["installedPackages"] != 0, "the list of image packages is empty"


@then(parsers.re(
    r'the image "(?P<image_non_exist>[^"]*)" with version "(?P<version>[^"]*)" doesn\'t exist via API calls'
))
def step_image_doesnt_exist_via_api(api_test, image_non_exist: str, version: str):
    images_list = api_test.image.list_images()
    for element in images_list:
        assert not (element["name"] == image_non_exist and element["version"].strip() == version.strip()), \
            f"{image_non_exist} should not exist anymore"


# ---------------------------------------------------------------------------
# Image stores tests
# ---------------------------------------------------------------------------

@when("I create and delete an image store via API")
def step_create_delete_image_store(api_test):
    api_test.image.store.create("fake_store", "https://github.com/uyuni-project/uyuni", "registry")
    api_test.image.store.delete("fake_store")


@when("I list image store types and image stores via API")
def step_list_image_store_types(api_test):
    no_auth_registry = os.environ.get("NO_AUTH_REGISTRY", "")
    store_types = api_test.image.store.list_image_store_types()
    assert len(store_types) == 2, \
        "We have only type support for Registry and OS Image store type!"
    assert any(st["label"] == "registry" for st in store_types), \
        "We should have Registry as supported type"
    assert any(st["label"] == "os_image" for st in store_types), \
        "We should have OS Image as supported type"

    stores = api_test.image.store.list_image_stores()
    registry = next((s for s in stores if s["storetype"] == "registry"), None)
    assert registry["label"] == "galaxy-registry", \
        f"Label {registry['label']} is different than 'galaxy-registry'"
    assert registry["uri"] == no_auth_registry, \
        f"URI {registry['uri']} is different than '{no_auth_registry}'"


@when("I set and get details of image store via API")
def step_set_get_image_store_details(api_test):
    api_test.image.store.create("Norimberga", "https://github.com/uyuni-project/uyuni", "registry")
    details_store = {"uri": "Germania", "username": "", "password": ""}
    api_test.image.store.set_details("Norimberga", details_store)
    details = api_test.image.store.get_details("Norimberga")
    assert details["uri"] == "Germania", f"uri should be Germania but is {details['uri']}"
    assert details["username"] == "", f"username should be empty but is {details['username']}"
    api_test.image.store.delete("Norimberga")


# ---------------------------------------------------------------------------
# Profiles tests
# ---------------------------------------------------------------------------

@when("I create and delete profiles via API")
def step_create_delete_profiles(api_test):
    api_test.image.profile.create("fakeone", "dockerfile", "galaxy-registry", "BiggerPathBiggerTest", "")
    api_test.image.profile.delete("fakeone")
    api_test.image.profile.create("fakeone", "dockerfile", "galaxy-registry", "BiggerPathBiggerTest", "1-SUSE-KEY-x86_64")
    api_test.image.profile.delete("fakeone")


@when("I create and delete profile custom values via API")
def step_create_delete_profile_custom_values(api_test):
    api_test.image.profile.create("fakeone", "dockerfile", "galaxy-registry", "BiggerPathBiggerTest", "")
    api_test.system.custominfo.create_key("arancio", "test containers")
    values = {"arancio": "arancia API tests"}
    api_test.image.profile.set_custom_values("fakeone", values)
    pro_det = api_test.image.profile.get_custom_values("fakeone")
    assert pro_det["arancio"] == "arancia API tests", \
        f"setting custom profile value failed: {pro_det['arancio']} != 'arancia API tests'"

    pro_type = api_test.image.profile.list_image_profile_types()
    assert len(pro_type) == 2, f"Number of image profile types is {len(pro_type)}"
    assert pro_type[0] == "dockerfile", f"type {pro_type[0]} is not dockerfile"
    assert pro_type[1] == "kiwi", f"type {pro_type[1]} is not kiwi"

    key = ["arancio"]
    api_test.image.profile.delete_custom_values("fakeone", key)


@when("I list image profiles via API")
def step_list_image_profiles(api_test):
    ima_profiles = api_test.image.profile.list_image_profiles()
    imagelabel = [img for img in ima_profiles if img["label"] == "fakeone"]
    assert imagelabel[0]["label"] == "fakeone", \
        f"label of container should be fakeone! {imagelabel[0]['label']} != 'fakeone'"


@when("I set and get profile details via API")
def step_set_get_profile_details(api_test):
    details = {"storeLabel": "galaxy-registry", "path": "TestForFun", "activationKey": ""}
    api_test.image.profile.set_details("fakeone", details)
    cont_detail = api_test.image.profile.get_details("fakeone")
    assert cont_detail["label"] == "fakeone", \
        f"label test fail! {cont_detail['label']} != 'fakeone'"
    assert cont_detail["imageType"] == "dockerfile", \
        f"imagetype test fail! {cont_detail['imageType']} != 'dockerfile'"
    api_test.image.profile.delete("fakeone")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _retrieve_build_host_id(api_test) -> int:
    """Retrieve the build host system ID from the API."""
    build_host = os.environ.get("BUILD_HOST", "")
    if not build_host:
        return 0
    results = api_test.system.search_by_name(build_host)
    if results:
        return results[0]["id"]
    return 0
