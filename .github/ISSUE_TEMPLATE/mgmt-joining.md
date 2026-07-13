---
name: New joiner checklist
about: Use this template when someone joins the SUSE Multi-Linux team
title: 'New joiner <name>'
labels: team
assignees: ''
---

General template for tasks to be done by Team Leads for new joiners of the SUSE Multi-Linux team.

A few of the tasks are to be done by the new joiner and will be marked as such with bold text.

- [ ] Go through the general [onboarding guide](https://geekos.io/onboarding) for new employees.
- [ ] GitHub account with SUSE email address:
  - [ ] Add the joiner to the [to SUSE org](https://confluence.suse.com/pages/viewpage.action?spaceKey=IAM&title=Github+account+and+access)
  - [ ] Add the joiner to the [Multi-Linux Manager Team](https://github.com/orgs/SUSE/teams/multi-linux-manager-team/members)
    - [ ] Add the joiner to the [relevant multi-linux-manager subteams](https://github.com/orgs/SUSE/teams/multi-linux-manager-team/teams)
  - [ ] Add the joiner to the [Uyuni organization and teams](https://github.com/orgs/uyuni-project/people)
    - [ ] Add the joiner to the [relevant Developer subteams](https://github.com/orgs/uyuni-project/teams/developers/teams)
- [ ] Add the joiner to [manager.mgr.suse.de](https://manager.mgr.suse.de) (NIS acccount)
- [ ] [Trello account](https://confluence.suse.com/display/IAM/Trello+account+and+access)
- [ ] Tell the **joiner to [request IBS access](https://confluence.suse.com/display/devops/How+to+request+IBS+access)**
- [ ] Confluence:
  - [ ] Add the joiner to the [squads page](https://confluence.suse.com/display/SUSEMANAGER/Squads%2C+People+and+Topics)
  - [ ] Add the joiner to the [team overview page](https://confluence.suse.com/display/SUSEMANAGER/)
  - [ ] Depending the role, add the joiner to the groups [multi-linux-teamleads](https://gitlab.suse.de/jira/ldap-server/-/blob/master/teams/user/multi-linux-teamleads.def) and [multi-linux-lt](https://gitlab.suse.de/jira/ldap-server/-/blob/master/teams/user/multi-linux-lt.def) with a GitLab MR
- [ ] Subscribe the joiner to the following mailing lists:
  - [ ] [galaxy-devel](https://mailman.suse.de/mailman/admin/galaxy-devel/members/add)
  - [ ] [multi-linux-manager](https://mailman.suse.de/mailman/admin/multi-linux-manager/members/add)
  - According to the role and squad, add the joiner to the relevant lists:
    - [ ] [galaxy-alerts](https://mailman.suse.de/mailman/admin/galaxy-alerts/members/add) (usually members of infra squad)
    - [ ] [galaxy-bugs](https://mailman.suse.de/mailman/admin/galaxy-bugs/members/add) (developers)
    - [ ] [galaxy-ci](https://mailman.suse.de/mailman/admin/galaxy-ci/members/add) (developers)
    - [ ] [galaxy-infra](https://mailman.suse.de/mailman/admin/galaxy-infra/members/add) (usually members of infra squad)
    - [ ] [galaxy-noise](https://mailman.suse.de/mailman/admin/galaxy-noise/members/add)
    - [ ] [galaxy-releng](https://mailman.suse.de/mailman/admin/galaxy-releng/members/add) (releng)
    - [ ] [salt](https://mailman.suse.de/mailman/admin/salt/members/add) (Ion)
    - [ ] [salt-maintainers](https://mailman.suse.de/mailman/admin/salt-maintainers/members/add) (Ion)
    - [ ] [tomcat-maintainers](https://mailman.suse.de/mailman/admin/tomcat-maintainers/members/add)
    - [ ] [uyuni-leader](https://mailman.suse.de/mailman/admin/uyuni-leader/members/add) (Team Leads)
- [ ] Tell the **joiner to subscribe to the following lists**:
  - [ ] [Uyuni announce](https://lists.opensuse.org/archives/list/announce@lists.uyuni-project.org/) (mandatory)
  - [ ] [SUSE](https://mailman.suse.de), at the very least [devel](https://mailman.suse.de/mailman/listinfo/devel), [users](https://mailman.suse.de/mailman/listinfo/users), recommended subscribing to [research](https://mailman.suse.de/mailman/listinfo/research) and [results](https://mailman.suse.de/mailman/listinfo/results)
- [ ] Tell the **joiner to have a look at the recommended lists, and subscribe if interested**:
  - [Linux Info](https://lists.suse.com/mailman/listinfo/linux) (strongly recommended for Release Engineers)
  - Lists at [openSUSE](https://lists.opensuse.org) (whatever is interesting for the joiner, such as for example `buildservice`, `users`, `packaging` or `factory`)
  - Lists at [suse.com](https://lists.suse.com/mailman/listinfo)  (whatever is interesting for the joiner, such as for example `sle-security-updates`, `sle-container-updates`, or `suma-updates`)
- [ ] Slack:
  - [ ] Add the joiner to the relevant workflows (daily standup, meetings, etc.)
  - [ ] Add the joiner to the relevant groups (left menu -> `Home` -> `Directories` -> `User Groups`):
    - [ ] `multi-linux-manager-engineers`
    - [ ] Squad specific group
  - [ ] Add the joiner to the channels:
    - [ ] `#team-multi-linux-manager`
    - [ ] Channel for the squad
    - [ ] Other channels (depending on the role, LT, TL, those releng are part of) or delegate this on the mentor
- [ ] Add the joiner to the Google [SUSE Multi-Linux Team](https://groups.google.com/a/suse.com/g/multi-linux-all/members) and squad groups (if available), to get access to the calendar (PHP, Retrospective, and all other events), and to emails send to the mailing list for the group
- GitLab:
  - [ ] Add the joiner to the [Galaxy organization](https://gitlab.suse.de/groups/galaxy/-/group_members) (as `Owner` for team leads, otherwise as `Developer`)
  - [ ] Add the joiner to the [credentials repository](https://gitlab.suse.de/galaxy/credentials/), if needed (usually for team leads, release engineers or people working on infrastructure)
  - [ ] Tell the **joiner to create a PR to add his/her SSH public key to the [galaxy/infrastructure repository](https://gitlab.suse.de/galaxy/infrastructure/-/blob/master/srv/pillar/team-ssh-pubkeys.sls)**
  - [ ] Tell the **joiner to create a PR to add him/herself the [finglonger config](https://gitlab.suse.de/galaxy/infrastructure/-/blob/master/srv/salt/bugguy-finglonger/galaxy.edn)**
- [ ] Invite the joiner to SCC organization [SUSE Multi-Linux Manager Team Playground](https://scc.suse.com/organizations/432530/users) for SCC mirror credentials
- [ ] Add the joiner to the relevant IBS/OBS groups:
  - [ ] Add to https://build.suse.de/groups/monitoring (monitoring & releng)
  - [ ] Add to https://build.suse.de/groups/salt-maintainers (Ion & releng)
  - [ ] Add to https://build.suse.de/groups/scap-security-guide-maintainers (releng)
  - [ ] Add to https://build.suse.de/groups/suse-manager-maintainers (releng)
  - [ ] Add to https://build.suse.de/groups/suse-manager-developers (developers)
  - [ ] Add to https://build.suse.de/groups/susemanager-releng (releng)
  - [ ] Add to https://build.opensuse.org/groups/uyuni-maintainers (releng)
  - [ ] Add to https://build.opensuse.org/groups/salt-maintainers (Ion & releng)
- Git Workflow: Until this [issue is fixed](https://github.com/openSUSE/openSUSE-git/issues/140), also prepare PRs to add the joiner to the following places:
  - For release engineering:
    - [ ] https://src.suse.de/products/MultiLinuxManagerTools-SL-Micro/src/branch/6/workflow.config and the same file in all `6*` branches
    - [ ] https://src.suse.de/products/MLMTools-products/src/branch/mlmtools_sle16-stable/workflow.config and the same file in all maintained branches
    - [ ] https://src.suse.de/products/SUSE_Multi-Linux_Manager/src/branch/mlm_sle16-5.2/workflow.config and the same file in all maintained branches
    - [ ] https://src.suse.de/products/SUSE_Multi-Linux_Manager-packages/src/branch/mlm-5.2/workflow.config and the same file for all maintained branches
    - [ ] https://src.suse.de/products/ManagerToolsBetaForMicro/src/branch/6/workflow.config and the same file in all maintained branches
    - [ ] https://src.suse.de/products/ManagerToolsForMicro/src/branch/6/workflow.config and the same file in all maintained branches
- [ ] Schedule new joiner meetups with at least one [member from each squad](https://confluence.suse.com/x/OIGAOQ), with the PO and with the architect (optionally with Director, PM and TLs)
- [ ] QE specific:
  - [ ] IBS/OBS: Add to the https://build.suse.de/groups/qam-manager group
  - [ ] Add QE account on [manager.mgr.suse.de](https://manager.mgr.suse.de) for the QE organization
  - [ ] Add joiner entries for private hypervisor to [SUMA infrastructure](https://gitlab.suse.de/galaxy/infrastructure/-/blob/master/srv/salt/qa/users/init.sls)
  - [ ] Add joiner entries for DNS to the [galaxy/infrastructure repository](https://gitlab.suse.de/galaxy/infrastructure/-/tree/master/srv/salt/bind-server)
  - [ ] Add joiner entries for DHCP to the [galaxy/infrastructure repository](https://gitlab.suse.de/galaxy/infrastructure/-/tree/master/srv/salt/dhcpd-server)
  - [ ] Add the joiner to [galaxy-qa](https://mailman.suse.de/mailman/admin/galaxy-qa/members/add) mailing list
  - [ ] Add the joiner to the [Multi-Linux Manager QE Team](https://github.com/orgs/SUSE/teams/multi-linux-manager-qe/members) on GitHub
  - [ ] Add the joiner to the [Uyuni QE developer Team](https://github.com/orgs/uyuni-project/teams/qe) on GitHub
  - [ ] Add the joiner to the [QE Retrospective project](https://github.com/orgs/SUSE/projects/54) on GitHub
  - [ ] Add the joiner to the [QE project board member list](https://github.com/orgs/SUSE/projects/32/views/1?pane=info) on GitHub
  - [ ] Add the joiner to the Google [Multi Linux Manager QE Squad](https://groups.google.com/a/suse.com/g/multi-linux-qe/members) group
