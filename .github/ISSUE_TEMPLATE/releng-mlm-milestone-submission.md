---
name: SUSE Multi-Linux Manager Milestone submission
about: Use this template for SUSE Multi-Linux Manager Milestone submissions
title: 'X.Y <MILESTONE_NAME> Milestone submission'
labels: ["vega-squad"]
projects: ["SUSE/35"]
assignees: ''

---

# Important changes, for the release notes

- 

# Deadlines

Check the [Release Calendar](https://confluence.suse.com/display/SUSEMANAGER/Release+calendar)
Freeze: 
Submission: 
Release: 

# Jira

- 

# Procedure

https://confluence.suse.com/pages/viewpage.action?pageId=1082228986

# Needed issues or EPICs to be included in this version

Add any additional bugzilla report, PR, or EPIC that must be included in this release.

You can also create sub-issues if preferred, but the needed information must be mentioned in this section for having an overview of still pending changes that could block the release.

# TODO some days before "Last day for Changes"

Add more tasks if needed

- [ ] Create the JIRA ticket, with placeholders for the IDs
- [ ] Ask the Doc Squad to submit an update of the doc package to the `Devel:Galaxy:Manager:Head` project 1 day after "Last day for Changes", and ask them to warn the translators so they can start their work. A Merge Request for the [documentation.suse.com repository](https://gitlab.suse.de/susedoc/docserv-external-tree-suma) should get created a few days before the release
- [ ] Request a Snapshot refresh at the "buildops" Team (https://gitlab.suse.de/buildops/release-support/-/issues)
- [ ] Ask the Ion Squad to promote all salt versions that have updates, including bundle (maybe multiple times - latest on the "Last day for Changes")
- [ ] Adjust `web.version` in `web/conf/rhn_web.conf` for `master` to match the Milestone (for example `5.1.0 Alpha1`)
  - [ ] Check also the [push.sh](https://github.com/uyuni-project/uyuni-tools/blob/main/push.sh) script for 'uyuni-tools'. Adjust the sed that replaces the default tag for SUSE Multi-Linux Manager.
- [ ] Check for updates needed in `_config` (Project Config) for changing milestone names.
- [ ] Check GITEA for changes in the devel products (updates for project config, products and release packages) which need to be submitted via cherry-pick to the target branch.
      Open the needed Pull Requests (Product PRs).


# TODO after "Last day for Changes"

Add more tasks if needed

- [ ] Lock the `uyuni-project/uyuni:master` and `uyuni-project/uyuni-tools:main` branches
- [ ] Send an email to galaxy-devel@suse.de informing that branches `uyuni-project/uyuni:master` and `uyuni-project/uyuni-tools:main` are locked, and adjust the topic on the slack [#team-multi-linux-manager](https://app.slack.com/client/T02863RC2AC/C02D78LLS04) channel
- [ ] After the branch freeze, ask [Orion](https://suse.slack.com/archives/C02DDMY6R0R) to prepare the PR for the code translations. If nobody from Orion is available, ask @parlt91. They will add us as reviewers.
- [ ] Confirm that the SR for the documentation is available and merged, and translators warned
- [ ] Merge the PR for the translations with the option `Merge pull request`
- [ ] Quick review changelogs with `tito-wrapper`, and request changes if needed
- [ ] Check all the [tests](https://ci.suse.de/view/Manager/view/Manager-Head/): everything should be green, or otherwise submission must be approved by QA

# TODO during the submission window

Add more tasks if needed (for example, asking Maintenace to change the channel definitions).

- [ ] Check all the [tests](https://ci.suse.de/view/Manager/view/Manager-Head/): everything should be green, or otherwise submission must be approved by QA
- [ ] Check if the schema directory exists with the correct versions (more at https://github.com/SUSE/spacewalk/wiki/Maintenance-Update-procedure)
- [ ] Check if schema migration directories exist between older and newer SUSE Manager version (more at https://github.com/SUSE/spacewalk/wiki/Maintenance-Update-procedure)
- [ ] Push changes to `master` and `main`
- [ ] Tag everything with `tito tag --use-release=0`
- [ ] For all the packages with changes at `Devel:Galaxy:Manager:Main` and `Devel:Galaxy:Manager:Head:Kit` submit SRs to the GA codestream, and ping autobuild for review
      For all packages managed with the GIT Workflow create a PR. (See [Submit server and proxy](https://confluence.suse.com/spaces/SUSEMANAGER/pages/1082228986/Submission+of+new+major+versions+Alpha+Beta+RC+GMC#Submissionofnewmajorversions(Alpha%2CBeta%2CRC%2CGMC)-Submitserverandproxy) and [Client Tools](https://confluence.suse.com/spaces/SUSEMANAGER/pages/1082228986/Submission+of+new+major+versions+Alpha+Beta+RC+GMC#Submissionofnewmajorversions(Alpha%2CBeta%2CRC%2CGMC)-ClientTools))
- [ ] Prepare the submissions with `mu-massive-task` or `patch-creator` for the client tools, salt and salt bundle. For any new packages that will be added to the codestreams, fetch the groups which will maintain them (one per package) and document this at the release card.
- [ ] Add the IDs (and notes, if any), to the JIRA ticket, and ping the Maintenace Team at [#discuss-multi-linux-manager-maintenance](https://app.slack.com/client/T02863RC2AC/C02DEF2U0E5)
- [ ] Verify that also the "Product PRs" are reviewed and merged.
- [ ] Once autobuild approves all MRs, verify that all artifacts where build and published. After this is the case, "release" the artifacts to `:toTest:`
  - [ ] `suma-release-tools/release-with-token -p SUSE:SLE-15-SP7:Update:Products:MultiLinuxManager52 -r charts -r containerfile -r images-SP7 [--doit]`
  - [ ] `suma-release-tools/release-with-token -p SUSE:SLFO:Products:Multi-Linux-Manager:5.2 -r product -r containerkiwi [--doit]`
  - [ ] "Beta" Client Tools if needed: `iosc release <PROJECT>`
- [ ] Once autobuild approves all MRs, create the `Manager-X.Y-MILESTONE` branches on both `uyuni-project/uyuni` and `uyuni-project/uyuni-tools` (for example `Manager-5.1-Alpha1`) and push them.
- [ ] Before unlocking `master` and `main`, consider PRs for merge that became ready during the branch freeze looking for the ["merge-candidate" label](https://github.com/uyuni-project/uyuni/pulls?q=is%3Apr+is%3Aopen+label%3Amerge-candidate) or ["merge-candidate" label on uyuni-tools](https://github.com/uyuni-project/uyuni-tools/pulls?q=is%3Apr+is%3Aopen+label%3Amerge-candidate) or ping reviewers to take care of it
- [ ] Send an email to galaxy-devel@suse.de informing that the branch `uyuni-project/uyuni:master` and `uyuni-project/uyuni-tools:main` are unlocked , and adjust the topic on the slack [#team-multi-linux-manager](https://app.slack.com/client/T02863RC2AC/C02D78LLS04) channel
- [ ] Ask release notes from the PO. For milestones there are no patchinfos
- [ ] Submit the release notes
- [ ] Prepare a draft for the email announcement during the release date
- [ ] Create the GitHub issues for the submission and release of the next MU.
