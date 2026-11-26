# Copyright (c) 2026 SUSE LLC.
# SPDX-License-Identifier: MIT

# "access" namespace: custom roles (access groups) of role-based access control.
#
# Calls here authenticate as Credentials.for(host), i.e. the last identity logged into the web UI,
# not as admin like the user.* calls. Run them right after logging in as admin.
class NamespaceAccess
  # Initializes a new instance of the NamespaceAccess class.
  #
  # @param api_test [Object] The test object passed in from the test script.
  def initialize(api_test)
    @test = api_test
  end

  # Lists the roles of the organization of the logged-in user, predefined and custom.
  #
  # @return [Array<Hash>] The roles, each with a 'label' and a 'description'.
  def list_roles
    @test.call('access.listRoles', sessionKey: @test.token)
  end

  # Deletes a custom role.
  #
  # @param label [String] The label of the role.
  # @return [Integer] 1 on success.
  def delete_role(label)
    @test.call('access.deleteRole', sessionKey: @test.token, label: label)
  end
end
