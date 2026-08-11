/*
 * Copyright (c) 2026 SUSE LLC
 * Copyright (c) 2009--2014 Red Hat, Inc.
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
package com.redhat.rhn.frontend.struts.test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import com.redhat.rhn.common.conf.Config;
import com.redhat.rhn.common.conf.ConfigDefaults;
import com.redhat.rhn.frontend.struts.RequestContext;
import com.redhat.rhn.testing.MockObjectTestCase;
import com.redhat.rhn.testing.RhnMockHttpServletRequest;
import com.redhat.rhn.testing.RhnMockHttpServletResponse;
import com.redhat.rhn.testing.RhnMockHttpSession;
import com.redhat.rhn.testing.UserTestUtils;

import com.suse.manager.webui.controllers.login.LoginController;
import com.suse.manager.webui.services.OidcAuthHandler;
import com.suse.manager.webui.utils.LoginHelper;

import org.junit.jupiter.api.Test;

import java.net.URI;
import java.util.HashMap;
import java.util.Optional;

import spark.ModelAndView;
import spark.RequestResponseFactory;
import spark.Response;
import spark.routematch.RouteMatch;

public class RequestContextTest extends MockObjectTestCase {

    @Test
    public final void testGetLoggedInUser() {
        Config.get().setBoolean(ConfigDefaults.SINGLE_SIGN_ON_ENABLED, "false");

        final String requestUrl = "http://localhost:8080/rhn/manager/login";
        final RouteMatch match = new RouteMatch(new Object(), requestUrl, requestUrl, "");
        final RhnMockHttpServletRequest mockRequest = new RhnMockHttpServletRequest();
        RhnMockHttpSession session = new RhnMockHttpSession();
        mockRequest.setSession(session);

        mockRequest.setRequestURL(requestUrl);
        mockRequest.setupGetMethod("POST");
        mockRequest.setMethod("POST");
        mockRequest.setupPathInfo(URI.create(requestUrl).getPath());
        mockRequest.setupAddParameter("url_bounce", "/rhn/users/UserDetails.do?uid=1");

        Response response = RequestResponseFactory.create(new RhnMockHttpServletResponse());
        // logging in
        LoginController loginController = new LoginController(new OidcAuthHandler(), Optional.empty());
        LoginHelper.successfulLogin(mockRequest, response.raw(), UserTestUtils.findNewUser("testUser", "testOrg" +
                this.getClass().getSimpleName()));
        ModelAndView result = loginController.loginView(RequestResponseFactory.create(match, mockRequest), response);
        @SuppressWarnings("unchecked")
        HashMap<String, String> model = (HashMap<String, String>) result.getModel();
        assertNotNull(session.getAttribute("webUserID"));
        assertEquals("/rhn/users/UserDetails.do?uid=1", model.get("url_bounce"));
        RequestContext requestContext = new RequestContext(RequestResponseFactory.create(match, mockRequest).raw());
        assertNotNull(requestContext.getCurrentUser());
    }

    @Test
    public void testProcessPaginationFirst() {
        RhnMockHttpServletRequest request = new RhnMockHttpServletRequest();
        request.setupAddParameter("First Page", "not null");
        request.setupAddParameter("first_lower", "1");
        RequestContext requestContext = new RequestContext(request);
        String rc = requestContext.processPagination();
        assertEquals("1", rc);
    }

    @Test
    public void testProcessPaginationPrev() {
        RhnMockHttpServletRequest request = new RhnMockHttpServletRequest();
        request.setupAddParameter("First Page", (String) null);
        request.setupAddParameter("Previous Page", "1");
        request.setupAddParameter("prev_lower", "10");
        RequestContext requestContext = new RequestContext(request);
        String rc = requestContext.processPagination();
        assertEquals("10", rc);
    }

    @Test
    public void testProcessPaginationLast() {
        RhnMockHttpServletRequest request = new RhnMockHttpServletRequest();
        request.setupAddParameter("First Page", (String) null);
        request.setupAddParameter("Previous Page", (String) null);
        request.setupAddParameter("Next Page", (String) null);
        request.setupAddParameter("Last Page", "1");
        request.setupAddParameter("last_lower", "30");
        RequestContext requestContext = new RequestContext(request);
        String rc = requestContext.processPagination();
        assertEquals("30", rc);
    }

    @Test
    public void testProcessPaginationNext() {
        RhnMockHttpServletRequest request = new RhnMockHttpServletRequest();
        request.setupAddParameter("First Page", (String)null);
        request.setupAddParameter("Prev Page", (String)null);
        request.setupAddParameter("Next Page", "1");
        request.setupAddParameter("next_lower", "20");
        RequestContext requestContext = new RequestContext(request);
        String rc = requestContext.processPagination();
        assertEquals("20", rc);
    }

    @Test
    public void testbuildPageLink() {
        RhnMockHttpServletRequest request = new RhnMockHttpServletRequest();
        request.setupAddParameter("someparam", "value");
        request.setupQueryString("otherparam=foo&barparam=beer");
        request.addAttribute("requestedUri", "http://localhost/rhn/somePage.do");

        RequestContext requestContext = new RequestContext(request);

        String url = requestContext.buildPageLink("someparam", "value");
        assertEquals("http://localhost/rhn/somePage.do?" +
                "someparam=value&otherparam=foo&barparam=beer", url);
        request.setupQueryString("otherparam=foo&barparam=beer&someparam=value");
        url = requestContext.buildPageLink("someparam", "zzzzz");

        assertEquals("http://localhost/rhn/somePage.do?" +
                "barparam=beer&otherparam=foo&someparam=zzzzz", url);
    }
}
