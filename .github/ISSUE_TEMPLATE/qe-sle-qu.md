---
name: QE - SLE Quarterly Updates
about: Use this template for testing the SLE QU images
title: "Test the MLM installation on SLES 15 SP7 QUx"
labels: ["qe-squad","qu-images","sle-15"]
projects: ["SUSE/32"]
assignees: ''

---

# Description

We need to test that the MLM 5.1 Server and Proxy (when present) can be installed on SLES 15 SP7 QUx images. We should do so latest for the RC.

## Tasks

- [ ] Decide what snapshot we will test, see the planned schedule here: https://confluence.suse.com/spaces/QUP/pages/1796014338/Schedule+of+SP7+-+QUs

### x86

- [ ] test the installation of the MLM server
- [ ] test the installation of the MLM proxy
- [ ] test the installation of the MLM RBS

### aarch64

- [ ] test the installation of the MLM server
- [ ] test the installation of the MLM proxy
- [ ] test the installation of the MLM RBS

### ppc64le (if time permits)

- [ ] test the installation of the MLM server
- [ ] test the installation of the MLM proxy
- [ ] test the installation of the MLM RBS

### s390  (if time permits)

- [ ] test the installation of the MLM server
- [ ] test the installation of the MLM proxy
- [ ] test the installation of the MLM RBS

## Found issues/bugs

- ...

## Links

- https://confluence.suse.com/x/AgENaw
- https://confluence.suse.com/x/b4AXCQ

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
