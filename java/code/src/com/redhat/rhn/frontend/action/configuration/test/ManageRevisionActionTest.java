/*
 * Copyright (c) 2009--2012 Red Hat, Inc.
 *
 * This software is licensed to you under the GNU General Public License,
 * version 2 (GPLv2). There is NO WARRANTY for this software, express or
 * implied, including the implied warranties of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
 * along with this software; if not, see
 * http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
 *
 * Red Hat trademarks are not licensed under GPLv2. No permission is
 * granted to use or replicate Red Hat trademarks that are incorporated
 * in this software or its documentation.
 */
package com.redhat.rhn.frontend.action.configuration.test;

import static org.junit.jupiter.api.Assertions.assertNotNull;

import com.redhat.rhn.domain.access.AccessGroupFactory;
import com.redhat.rhn.domain.config.ConfigRevision;
import com.redhat.rhn.frontend.dto.ConfigRevisionDto;
import com.redhat.rhn.frontend.struts.RequestContext;
import com.redhat.rhn.testing.ConfigTestUtils;
import com.redhat.rhn.testing.RhnMockStrutsTestCase;
import com.redhat.rhn.testing.UserTestUtils;

import org.junit.jupiter.api.Test;

/**
 * ManageRevisionActionTest
 */
public class ManageRevisionActionTest extends RhnMockStrutsTestCase {

    @Test
    public void testExecute() {
        UserTestUtils.addAccessGroup(user, AccessGroupFactory.CONFIG_ADMIN);

        ConfigRevision revision = ConfigTestUtils.createConfigRevision(user.getOrg());

        setRequestPathInfo("/configuration/file/ManageRevision");
        addRequestParameter("cfid", revision.getConfigFile().getId().toString());
        actionPerform();
        assertNotNull(request.getParameter("cfid"));
        verifyList(RequestContext.PAGE_LIST, ConfigRevisionDto.class);
    }
}

