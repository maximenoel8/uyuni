---
name: Leavers checklist
about: Use this template when someone leaves the SUSE Multi-Linux team
title: 'Leaver <name>'
labels: team
assignees: ''
---

General template for tasks to be done by Team Leads for leavers from the SUSE Multi-Linux team.

# Leaving date

**Official:** YYYY-MM-DD
**Last work day:** YYYY-MM-DD

# Some days before the member's last work day

Team Lead to handle the following tasks:

- [ ] **General SUSE Procedure:** Review the [team members leaving the company](https://sites.google.com/suse.com/resources/team-leader-quick-links), in particular the `Information Guide when a Team Member is Leaving`. Those documents contain information about everything that needs to be returned, and things to be done by the team lead and the team member (not just hardware!)
- [ ] **Exit interview:** Conduct an [exit interview](https://en.wikipedia.org/wiki/Exit_interview) and store the notes at [Confluence](https://confluence.suse.com/display/SUSEMANAGER/Exit+Interviews)
- [ ] **Hardware:** Evaluate if the leaver jas access to something special which also needs to get transferred to another person (SSH access to a server, permissions to special pages on wikis, Confluence, resources in the cloud, VMs, Raspberry Pi hardware, etc.)
- [ ] **Bugzilla:** Remind the **leaver to remove all ["watches"](https://bugzilla.suse.com/userprefs.cgi?tab=email) in Bugzilla before leaving**
- [ ] **Bugzilla:** Review the [responsibles for the bugzilla team accounts](https://confluence.suse.com/display/IAM/5.+UCS+Role+Model+and+Entitlements+Management#id-5.UCSRoleModelandEntitlementsManagement-Bot/Serviceentitlements) and nominate a new one person if needed
- [ ] **Packages:** Run `OUSER=<LEAVER>; osc search -i ${OUSER}; osc -A https://api.suse.de maintainer -U ${OUSER}` (replace `<LEAVER>` with the leaver's username), and if the leaver is a bugowner of any package, look for a new bugowner (ideally a group, not a single person, home projects can be ignored)
- [ ] **Code:** Consider any code stored in personal accounts and create forks accordingly (e.g. in GitLab)
- [ ] **Credentials:** Consider any credentials known only to that leaver (e.g. for mailing lists) and share
- [ ] **Mailing lists:** Transfer mailing list administration to someone else (usually only needed when a Team Lead is leaving)
- [ ] **Content:** Consider any content that could be present in e.g. https://w3.suse.de or Google Drive, and maybe should be stored it permanently (e.g. recordings, slides, moving them to Google Drive)

# The day after the member leaves the team

Team Lead to handle the following tasks:

- [ ] GitHub:
  - [ ] Remove the leaver from the [Multi-Linux Manager Team](https://github.com/orgs/SUSE/teams/multi-linux-manager-team/members)
  - [ ] Remove the leaver from the [Multi-Linux Administrators](https://github.com/orgs/SUSE/teams/multi-linux-manager-administrators/members)
  - [ ] Remove the leaver from the [Multi-Linux CI Administrators](https://github.com/orgs/SUSE/teams/multi-linux-manager-ci-administrators/members)
  - [ ] Remove the leaver from the [Uyuni organization](https://github.com/orgs/uyuni-project/people) and [teams](https://github.com/orgs/uyuni-project/teams). It can remain a member (but not owner), if it will keep contributing.
- [ ] Confluence:
  - [ ] Remove the leaver the [team overview page](https://confluence.suse.com/display/SUSEMANAGER/)
  - [ ] Remove the leaver the [squads page](https://confluence.suse.com/display/SUSEMANAGER/Squads%2C+People+and+Topics), cleaning ownerships if needed
  - [ ] Depending the role, remove the leaver from the groups [multi-linux-teamleads](https://gitlab.suse.de/jira/ldap-server/-/blob/master/teams/user/multi-linux-teamleads.def) and [multi-linux-lt](https://gitlab.suse.de/jira/ldap-server/-/blob/master/teams/user/multi-linux-lt.def) with a GitLab MR
- [ ] Mailing lists, remove the leaver from:
  - [ ] [galaxy-alerts](https://mailman.suse.de/mailman/admin/galaxy-alerts/members/remove)
  - [ ] [galaxy-bugs](https://mailman.suse.de/mailman/admin/galaxy-bugs/members/remove)
  - [ ] [galaxy-ci](https://mailman.suse.de/mailman/admin/galaxy-ci/members/remove)
  - [ ] [galaxy-devel](https://mailman.suse.de/mailman/admin/galaxy-devel/members/remove)
  - [ ] [galaxy-infra](https://mailman.suse.de/mailman/admin/galaxy-infra/members/remove)
  - [ ] [galaxy-noise](https://mailman.suse.de/mailman/admin/galaxy-noise/members/remove)
  - [ ] [galaxy-releng](https://mailman.suse.de/mailman/admin/galaxy-releng/members/remove)
  - [ ] [salt](https://mailman.suse.de/mailman/admin/salt/members/remove)
  - [ ] [salt-maintainers](https://mailman.suse.de/mailman/admin/salt-maintainers/members/remove)
  - [ ] [multi-linux-manager](https://mailman.suse.de/mailman/admin/multi-linux-manager/members/remove)
  - [ ] [tomcat-maintainers](https://mailman.suse.de/mailman/admin/tomcat-maintainers/members/remove)
  - [ ] [uyuni-leader](https://mailman.suse.de/mailman/admin/uyuni-leader/members/remove)
  - [ ] uyuni announce as [user](https://lists.opensuse.org/manage/lists/announce.lists.uyuni-project.org/members/member/) (to prevent bounces later), and maybe [moderator](https://lists.opensuse.org/manage/lists/announce.lists.uyuni-project.org/members/moderator/) and [owner](https://lists.opensuse.org/manage/lists/announce.lists.uyuni-project.org/members/owner/)
- [ ] Slack:
  - [ ] Remove the leaver from the workflows (daily standup, meetings, etc.)
  - [ ] Remove the lieaver from the groups (left menu -> `Home` -> `Directories` -> `User Groups`)
    - [ ] `multi-linux-manager-engineers`
    - [ ] `multi-linux-manager-infra`, if leaver is part of the [Infra squad](https://confluence.suse.com/display/SUSEMANAGER/Squads%2C+People+and+Topics)
    - [ ] `multi-linux-manager-coordinators`, if leaver is a [squad coordinator](https://confluence.suse.com/display/SUSEMANAGER/Squads%2C+People+and+Topics)
    - [ ] Squad specific group
- [ ] Remove the leaver from Google [SUSE Multi-Linux Team](https://groups.google.com/a/suse.com/g/multi-linux-all/members) and squads groups (if available)
- [ ] Check the Google meeting events and remove if needed (in case the leaver got the meeting with a forward):
  - [ ] Multi-Linux Team Review Meeting
  - [ ] Priorities, Help and Planning (PHP)
  - [ ] Multi-Linux Team Retrospective
- [ ] Hardware: Are there somewhere machines (e.g. RPI) or VMs around managed by this person? Stop them, and remove them after a few days.
- [ ] Cloud resources (accounts for each cloud at the [Landing Zones](https://confluence.suse.com/display/CCOE/Cloud+Landing+Zone+Access#CloudLandingZoneAccess-OktaGroupNaming/PermissionScheme#Roles) confluence page):
  - [ ] AWS
  - [ ] Azure
  - [ ] Google Cloud
- [ ] Remove the leaver from the relevant IBS/OBS groups:
  - [ ] https://build.suse.de/groups/monitoring
  - [ ] https://build.suse.de/groups/salt-maintainers
  - [ ] https://build.suse.de/groups/scap-security-guide-maintainers
  - [ ] https://build.suse.de/groups/suse-manager-maintainers
  - [ ] https://build.suse.de/groups/suse-manager-developers
  - [ ] https://build.suse.de/groups/susemanager-releng
  - [ ] https://build.opensuse.org/groups/uyuni-maintainers
  - [ ] https://build.opensuse.org/groups/salt-maintainers
- Git Workflow: Until this [issue is fixed](https://github.com/openSUSE/openSUSE-git/issues/140), also prepare PRs to remove the leaver (or replace it if the leaver is the last one, as you will need a new maintainer) from the following places:
  - [ ] https://src.suse.de/products/MultiLinuxManagerTools-SL-Micro/src/branch/6/workflow.config and the same file in all `6*` branches
  - [ ] https://src.suse.de/products/MLMTools-products/src/branch/mlmtools_sle16-stable/workflow.config and the same file in all maintained branches
  - [ ] https://src.suse.de/products/SUSE_Multi-Linux_Manager/src/branch/mlm_sle16-5.2/workflow.config and the same file in all maintained branches
  - [ ] https://src.suse.de/products/SUSE_Multi-Linux_Manager-packages/src/branch/mlm-5.2/workflow.config and the same file for all maintained branches
  - [ ] https://src.suse.de/products/ManagerToolsBetaForMicro/src/branch/6/workflow.config and the same file in all maintained branches
  - [ ] https://src.suse.de/products/ManagerToolsForMicro/src/branch/6/workflow.config and the same file in all maintained branches
- [ ] Internal:
  - [ ] Remove SSH public key from the [galaxy/infrastructure repository](https://gitlab.suse.de/galaxy/infrastructure/-/blob/master/srv/pillar/team-ssh-pubkeys.sls)
  - [ ] Remove SSH public key from the [OPS-Service/repository](https://gitlab.suse.de/OPS-Service/salt/-/blob/production/pillar/ssh_keys/groups/suma-infra.sls) (make sure you also remove the key from the `users` folder)
  - [ ] Remove leaver's GPG key from the [credentials repository](https://gitlab.suse.de/galaxy/credentials/), if present
  - [ ] Remove leaver from SCC organization [SUSE Multi-Linux Manager Team Playground](https://scc.suse.com/organizations/432530/users) for SCC mirror credentials
  - [ ] Remove leaver from SCC organization [SUSE Multi-Linux Stable (Infra/CI/MU validation)](https://scc.suse.com/organizations/784242/users) for SCC mirror credentials
  - [ ] Remove SUMA account on [manager.mgr.suse.de](https://manager.mgr.suse.de)
  - [ ] Buildservice - Bugowner: is the leaver the bug owner of some packages? Find a new one and remove the mail address for maintainers and bug owners. Also projects where this person is the only maintainer needs to be transferred.
  - [ ] Remove the leaver from our [GitLab group](https://gitlab.suse.de/groups/galaxy/-/group_members)
  - [ ] Update the [finglonger config](https://gitlab.suse.de/galaxy/infrastructure/-/blob/master/srv/salt/bugguy-finglonger/galaxy.edn)
- [ ] QE specific:
  - [ ] IBS/OBS: Remove from the https://build.suse.de/groups/qam-manager group
  - [ ] Remove QE account on [manager.mgr.suse.de](https://manager.mgr.suse.de) for the QE organization
  - [ ] Remove leaver entries for private hypervisor from [SUMA infrastructure](https://gitlab.suse.de/galaxy/infrastructure/-/blob/master/srv/salt/qa/users/init.sls)
  - [ ] Remove leaver entries for DNS from the [galaxy/infrastructure repository](https://gitlab.suse.de/galaxy/infrastructure/-/tree/master/srv/salt/bind-server)
  - [ ] Remove leaver entries for DHCP from the [galaxy/infrastructure repository](https://gitlab.suse.de/galaxy/infrastructure/-/tree/master/srv/salt/dhcpd-server)
  - [ ] Remove from [galaxy-qa](https://mailman.suse.de/mailman/admin/galaxy-qa/members/remove) mailing list
  - [ ] Remove from [Multi-Linux Manager QE Team](https://github.com/orgs/SUSE/teams/multi-linux-manager-qe/members) on GitHub
  - [ ] Remove from [Uyuni QE developer Team](https://github.com/orgs/uyuni-project/teams/qe) on GitHub
  - [ ] Remove from [QE Retrospective project](https://github.com/orgs/SUSE/projects/54) on GitHub
  - [ ] Remove from [QE project board member list](https://github.com/orgs/SUSE/projects/32/views/1?pane=info) on GitHub
  - [ ] Remove from the Google [Multi Linux Manager QE Squad](https://groups.google.com/a/suse.com/g/multi-linux-qe/members) group
