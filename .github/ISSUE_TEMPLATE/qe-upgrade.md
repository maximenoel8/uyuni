---
name: QE - Testing MLM upgrades
about: Use this template for testing MLM upgrades
title: "Test the upgrade from X to Y"
labels: ["qe-squad","manual tests"]
projects: ["SUSE/32"]
assignees: ''

---

# Description

This tests the upgrade from X to Y.

## Information

- Start date:
- End date:
- Environment:
- MLM version:

---

## Tasks

### Prerequisites

- [ ] Wait for all related submissions
- [ ] Open the MLM documentation
- [ ] Install the server + proxy VM
- [ ] Register and set up the proxy
- [ ] Sync a product
- [ ] Onboard a Minion

### Upgrade the `mgr-*tools`

Depending on what we test, we get the new `mgr-*tools` version with the updated host OS and the updated MLM extensions.
However, we more frequently test unreleased versions, so we need to update the `mgr-*tools` from an MI.

- [ ] Add the MI repository to the server host and update the `mgr-*tools`
- [ ] Verify the new version is present with `mgradm --version`/`mgrctl --version` (`rpm -qa --changelog mgradm | head -n 10`)
- [ ] Verify the default version with `mgradm --help`
- [ ] Add the MI repository to the proxy host and update the `mgr-*tools`
- [ ] Verify the new version is present with `mgrpxy --version` (`rpm -qa --changelog mgrpxy | head -n 10`)
- [ ] Verify the default version with `mgrpxy --help`

### Upgrade the server and the proxy container

- [ ] check the podman images with `podman image list` on the server and the proxy
- [ ] get the correct container image URLs from the Jira card
- [ ] perform the upgrade on the server with `mgradm upgrade podman --registry-host <> --tag <>`
- [ ] verify the server containers are healthy afterwards with `mgradm status` and check the webUI
- [ ] Check the connection between server/proxy and Minion still works (e.g. remote command, package upgrade/installation)
- [ ] perform the upgrade on the proxy with `mgrpxy upgrade podman --registry-host <> --tag <>`
- [ ] verify the proxy containers are healthy afterwards with `mgrpxy status`
- [ ] Check the connection between server/proxy and Minion still works (e.g. remote command, package upgrade/installation)
- [ ] Reboot server/proxy/Minion and check everything still works (e.g. remote command)

### Regression tests

- [ ] sync a new product in the Product Wizard (SL Micro is small and fast)
- [ ] check the log files on the container (e.g. `/var/log/rhn/rhn_web_ui.log`)

## Found issues/bugs

- ...

## Links

- [Server documentation](https://documentation.suse.com/multi-linux-manager/5.1/en/docs/installation-and-upgrade/container-management/updating-server-containers.html)
- [Proxy documentation](https://documentation.suse.com/multi-linux-manager/5.1/en/docs/installation-and-upgrade/container-management/updating-proxy-containers.html)
- ...

## Legend

- Selected checkbox means, we tested it and the testing is completed with no
  pending blockers to be verified as fixed in a resubmission
- :white_check_mark: : Test/verification was successful
- :x: : Test/verification was not successful
- :test_tube: : Test failed due to test suite issue but succeeded manually
- If multiple emotes: task was run several times
  - Example: :x: :white_check_mark: = first run failed, second run passed (resubmission)
  - Example: In case of a blocker, we should wait for the fix and retest -> :x:
    and not checked checkbox. In case of non-blocker -> :x: and checked
    checkbox.
