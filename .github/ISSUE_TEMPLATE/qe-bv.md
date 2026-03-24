---
name: QE - Build Validation
about: QE - Use this template for a new build validation
title: "BV "
labels: ["qe-squad", "build validation", "high-priority"]
projects: ["SUSE/32"]
assignees: ''

---

## Information

- Planned start date:
- Real start date:
- Planned deadline:
- Real end date:
- Resubmissions:

---

- Submission card:
- Jira card:
- Release notes draft:

---

- Jenkins pipeline:
  - Full:
  - Mini:
- Server URL:
  - Full:
  - Mini:

---

### Links

- [Step-by-step guide](https://confluence.suse.com/display/SUSEMANAGER/QE+Build+Validation)
- [Automated tests](https://confluence.suse.com/display/SUSEMANAGER/Automated+tests)
- [Pipeline parameters](https://confluence.suse.com/display/SUSEMANAGER/The+new+BV+pipeline)

---

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

---

## Manual tests and tasks

- [ ] Clean up the old environment
- [ ] Update the mirror / check if it is up to date

### Long-running environment

The official documentation is linked below, but you need to run the `upgrade` command with the correct MI container URL to get the correct container to update to.

- [ ] [Upgrade the server](https://documentation.suse.com/multi-linux-manager/5.1/en/docs/installation-and-upgrade/container-management/updating-server-containers.html)
- [ ] [Upgrade the proxy](https://documentation.suse.com/multi-linux-manager/5.1/en/docs/installation-and-upgrade/container-management/updating-proxy-containers.html)

### Release notes and new features

- [ ] Update and verify the release notes for server and proxy
- [ ] ...

### Fixed bugs to verify

- [ ] ...

---

## Automated tests and tasks

### Preparation

- [ ] Check the mirror
- [ ] JSON creation (go through the JSON file before using it)

### Proxy and Monitoring

- [ ] Proxy setup
- [ ] Monitoring server setup

### Client Bootstrap and Smoke Tests

- [ ] All supported systems were bootstrapped and passed smoke tests
  - [ ] Client bootstrap stage
  - [ ] Client smoke tests

### Migration Tests

- [ ] Product and Salt migration tests
  - [ ] SLES 15 SP6 minion → SP7
  - [ ] SLES 15 SP6 SSH minion → SP7
  - [ ] SL Micro 5.5 → 6.1
  - [ ] OS Salt → Salt Bundle

### Retail

- [ ] SLES 15 SP6
- [ ] SLES 15 SP7

### Second host OS

- [ ] Test the installation and setup of the server and proxy on the other supported host OS (SLES 15)
  - [ ] server installation
  - [ ] core & reposync
  - [ ] proxy

---

## Approval

- [ ] Ping our release engineers in Slack
- [ ] Approve all related MUs in [IBS](https://smelt.suse.de/overview/?7=qam-manager#testing) or via the [command line](https://confluence.suse.com/display/SUSEMANAGER/QE+Build+Validation)

---

## Report

- [ ] Prepare the report according to the template in [Confluence](https://confluence.suse.com/x/d4GTdg)
- [ ] Add the report to Confluence
- [ ] Send the report to `galaxy-devel@suse.de`

---

## Test suite issues or fixes

- [ ] ...

---

## Reported Bugs

### Non-blocker

- [ ] ...

### Blocker

- [ ] ...
