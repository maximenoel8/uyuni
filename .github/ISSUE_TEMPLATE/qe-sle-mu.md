---
name: QE - SLE Maintenance Updates
about: Use this template for the SLE Maintenance updates role
title: "SLE Maintenance Update Testing Week "
labels: ["qe-squad", "sle-maintenance-update"]
projects: ["SUSE/32"]
assignees: ''

---

# Tasks
Validate a Maintenance Incident depending its content:

- **Server or Proxy dependencies** (examples: tomcat, apache, log4j, hibernate, etc ):
  - [manager-4.3-qe-mi-validation-sles](https://jenkins.mgr.suse.de/view/By%20Functionality/view/SLEMu/job/manager-4.3-qe-mi-validation-sles/)
  - [manager-5.0-qe-mi-validation-bci](https://jenkins.mgr.suse.de/view/By%20Functionality/view/SLEMu/job/manager-5.0-qe-mi-validation-bci/)
  - [manager-5.1-qe-mi-validation-bci](https://jenkins.mgr.suse.de/view/By%20Functionality/view/SLEMu/job/manager-5.1-qe-mi-validation-bci/)
  - [manager-5.2-qe-mi-validation-bci](https://jenkins.mgr.suse.de/view/By%20Functionality/view/SLEMu/job/manager-5.2-qe-mi-validation-bci/)

- **Mgr-Tools dependencies** (examples: podman, netavark, etc)
  - [manager-5.0-qe-mi-validation-mgrtools](https://jenkins.mgr.suse.de/view/By%20Functionality/view/SLEMu/job/manager-5.0-qe-mi-validation-mgrtools/)
  - [manager-5.1-qe-mi-validation-mgrtools](https://jenkins.mgr.suse.de/view/By%20Functionality/view/SLEMu/job/manager-5.1-qe-mi-validation-mgrtools/)
  - [manager-5.2-qe-mi-validation-mgrtools](https://jenkins.mgr.suse.de/view/By%20Functionality/view/SLEMu/job/manager-5.2-qe-mi-validation-mgrtools/)

- Take care of incoming SLE MUs following priorities [smelt.suse.de](https://smelt.suse.de/overview/?7=qam-manager#testing)
- For all SLE MUs that have the susemanager-releng reviewer tag, please also ping susemanager-releng on slack after approval

Additional information: [QE SLE Maintenance Updates](https://confluence.suse.com/display/SUSEMANAGER/QE+SLE+Maintenance+Updates)
