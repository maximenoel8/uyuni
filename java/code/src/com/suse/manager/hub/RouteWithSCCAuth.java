/*
 * Copyright (c) 2024--2025 SUSE LLC
 *
 * This software is licensed to you under the GNU General Public License,
 * version 2 (GPLv2). There is NO WARRANTY for this software, express or
 * implied, including the implied warranties of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
 * along with this software; if not, see
 * http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
 */
package com.suse.manager.hub;

import com.redhat.rhn.domain.credentials.HubSCCCredentials;

import spark.Request;
import spark.Response;

/**
 *
 */
@FunctionalInterface
public interface RouteWithSCCAuth {

    /**
     *
     * @param request the request object
     * @param response the response object
     * @param credentials hub credentials used to authenticate
     * @return the content to be set in the response
     */
    Object handle(Request request, Response response, HubSCCCredentials credentials);
}
