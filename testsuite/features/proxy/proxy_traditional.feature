# Copyright (c) 2017-2025 SUSE LLC
# Licensed under the terms of the MIT license.
#
# The scenarios in this feature are skipped if there is no proxy
# ($proxy is nil)
#
# Alternative: Bootstrap the proxy as Salt minion from GUI

@skip_if_containerized_server
@scope_proxy
@proxy
Feature: Setup Uyuni proxy
  In order to use a proxy with the Uyuni server
  As the system administrator
  I want to register the proxy to the server

  Scenario: Install proxy software
    When I refresh the metadata for "proxy"
    # TODO: uncomment when SCC product becomes available
    # And I install "SUSE-Manager-Proxy" product on the proxy
    And I install proxy pattern on the proxy
    And I let squid use avahi on the proxy

  Scenario: Log in as admin user
    Given I am authorized for the "Admin" section

  Scenario: Bootstrap the proxy as a Salt minion
    When I follow the left menu "Systems > Bootstrapping"
    Then I should see a "Bootstrap Minions" text
    When I enter the hostname of "proxy" as "hostname"
    And I enter "22" as "port"
    And I enter "root" as "user"
    And I enter "linux" as "password"
    And I select "1-PROXY-KEY-x86_64" from "activationKeys"
    And I click on "Bootstrap"
    And I wait until I see "Bootstrap process initiated." text

  Scenario: Wait until the proxy appears
    When I wait until onboarding is completed for "proxy"

  Scenario: Detect latest Salt changes on the proxy
    When I query latest Salt changes on "proxy"

  Scenario: Copy the keys and configure the proxy
    When I copy server's keys to the proxy
    And I configure the proxy
    Then I should see "proxy" via spacecmd
    And service "salt-broker" is active on "proxy"

@susemanager
  Scenario: Check proxy system details
    When I am on the Systems overview page of this "proxy"
    Then I should see "proxy" hostname
    # TODO: uncomment when SCC product becomes available
    # When I wait until I see "SUSE Manager Proxy" text, refreshing the page
    Then I should see a "Proxy" link in the content area

@uyuni
  Scenario: Check proxy system details
    When I am on the Systems overview page of this "proxy"
    Then I should see "proxy" hostname
    Then I should see a "Proxy" link in the content area

  Scenario: Check events history for failures on the proxy
    Given I am on the Systems overview page of this "proxy"
    Then I check for failed events on history event page

@uyuni
  Scenario: Assign the correct channels to the proxy
    Given I am on the Systems overview page of this "proxy"
    When I follow "Software" in the content area
    And I follow "Software Channels" in the content area
    And I wait until I do not see "Loading..." text
    And I check radio button "openSUSE Leap 15.6 (x86_64)"
    And I wait until I do not see "Loading..." text
    And I check "Uyuni Client Tools for openSUSE Leap 15.6 (x86_64)"
    And I check "Uyuni Proxy Devel for openSUSE Leap 15.6 (x86_64)"
    And I click on "Next"
    Then I should see a "Confirm Software Channel Change" text
    When I click on "Confirm"
    Then I should see a "Changing the channels has been scheduled." text
    When I follow "scheduled" in the content area
    And I wait until I see "1 system successfully completed this action." text, refreshing the page
