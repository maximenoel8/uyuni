---
name: QE - Testing MLM Extensions
about: Use this template for testing MLM Extensions
title: "Test the MLM extension for X on Y"
labels: ["qe-squad","manual tests"]
projects: ["SUSE/32"]
assignees: ''

---

# Description

This tests the MLM server, proxy and RBS extensions on architecture X.

## Information

- Start date:
- End date:
- Environment:
- MLM version:

---

## Tasks

### Prerequisites

- [ ] Wait until the extensions are present in SCC
- [ ] Open the MLM documentation
- [ ] Install the server/proxy/RBS VMs from image <X>

### Installing the MLM Extensions

#### Server

- [ ] Install the server extension
  - activate the host OS from SCC with `SUSEConnect`
  - verify the activation with `SUSEConnect -s`
  - list the extensions with `SUSEConnect --list-extensions`
  - activate and enable the server extension
  - verify the extension is active with `SUSEConnect --status-text`

#### Proxy

- [ ] Install the proxy extension
  - activate the host OS from SCC with `SUSEConnect`
  - verify the activation with `SUSEConnect -s`
  - list the extensions with `SUSEConnect --list-extensions`
  - activate and enable the proxy extension
  - verify the extension is active with `SUSEConnect --status-text`

#### Retail Branch Server (RBS)

- [ ] Install the Retail Branch Server (RBS) extension
  - activate the host OS from SCC with `SUSEConnect`
  - verify the activation with `SUSEConnect -s`
  - list the extensions with `SUSEConnect --list-extensions`
  - activate and enable the RBS extension
  - verify the extension is active with `SUSEConnect --status-text`

Depending on personal preference, you can either start with the RPM container
image tests or the registry container tests in the next section.

### Tests with the RPM images

#### Server

- [ ] Install the server container image RPM files with zypper
  - E.g search with `zypper se suse-multi-linux-manager-*`
- [ ] Install the server with `mgradm install podman <FQDN>`
  - Verify that the RPMs are used
- [ ] Verify the successful installation (e.g by visiting the webUI)

#### Proxy

- [ ] Install the proxy container image RPM files with zypper
  - E.g search with `zypper se suse-multi-linux-manager-*`
- [ ] Install the proxy with `mgrpxy install podman config.tar.gz`
  - Verify that the RPMs are used
- [ ] Verify the successful installation

### Cleanup

- Delete the Proxy Minion
- Uninstall the proxy with `mgrpxy uninstall --purge-volumes --purge-images --force`
- Uninstall the server with `mgradm uninstall --purge-volumes --purge-images --force`
- Remove the RPMs with zypper (for the test with the image registry)

### Tests with the container registry images

#### Server

- [ ] Deploy the server with `mgradm install podman <FQDN>`

#### Proxy

- [ ] Onboard and set up the proxy (if the client tools are available)
- [ ] Deploy the proxy with `mgrpxy install podman config.tar.gz`

### Cleanup

- Delete the Proxy Minion
- Uninstall the proxy with `mgrpxy uninstall --purge-volumes --purge-images --force`
- Uninstall the server with `mgradm uninstall --purge-volumes --purge-images --force`
- Verify that the containers are remove with `podman image list`

## Found issues/bugs

- ...

## Links

- [Server documentation](https://documentation.suse.com/multi-linux-manager/5.1/en/docs/installation-and-upgrade/container-deployment/mlm/server-deployment-mlm.html#deploy-mlm-server-sles)
- ...

## Legend

- Selected checkbox means, we tested it and the testing is completed with no
  pending blockers to be verified as fixed in a resubmission
- :white_check_mark: : Test/verification was successful
- :x: : Test/verification was not successful
- :test_tube: : Test failed due to test suite issue but succeed manually
- If multiple emotes: task was run several times
  - Example: :x: :white_check_mark: = first run failed, second run passed (resubmission)
  - Example: In case of a blocker, we should wait for the fix and retest -> :x:
    and not checked checkbox. In case of non-blocker -> :x: and checked
    checkbox.
