/*
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

/*
 * AUTOMATICALLY GENERATED FILE, DO NOT EDIT.
 */
package com.redhat.rhn.common.security;

import com.redhat.rhn.common.RhnRuntimeException;
import com.redhat.rhn.common.conf.Config;
import com.redhat.rhn.common.conf.ConfigDefaults;
import com.redhat.rhn.common.localization.LocalizationService;
import com.redhat.rhn.domain.access.AccessGroup;
import com.redhat.rhn.domain.role.Role;
import com.redhat.rhn.frontend.html.HtmlTag;

/**
 * A RuntimeException indicating that the user has attempted something he or she does
 * not have permissions for.
 * <p>

 *
 */
public class PermissionException extends RhnRuntimeException  {

    private final String localizedTitle;
    private final String localizedSummary;
    /**
     * Constructor
     * @param message exception message
     */
    public PermissionException(String message) {
        this(message, null, null);
    }

    /**
     * Constructor
     * @param message exception message
     * @param cause the cause (which is saved for later retrieval
     * by the Throwable.getCause() method). (A null value is
     * permitted, and indicates that the cause is nonexistent or
     * unknown.)
     */
    public PermissionException(String message, Throwable cause) {
        this(message, cause, null, null);
    }

    /**
     * Constructor
     * @param role Cause for the exception (bad role)
     */
    public PermissionException(Role role) {
        this(role, null, null);
    }
    /**
     * Constructor
     * @param accessGroupIn Cause for the exception (bad role)
     */
    public PermissionException(AccessGroup accessGroupIn) {
        this(accessGroupIn, null, null);
    }

    /**
     * Constructor
     * @param message exception message
     * @param localizedTitleIn The localizedTitle to set.
     * @param localizedSummaryIn The localizedSummary to set.
     */
    public PermissionException(String message, String localizedTitleIn, String localizedSummaryIn) {
        super(message);
        LocalizationService ls = LocalizationService.getInstance();

        localizedTitle = localizedTitleIn != null ? localizedTitleIn : ls.getMessage("permission.jsp.title.acl");
        localizedSummary = localizedSummaryIn != null ? localizedSummaryIn : getDefaultSummary();
    }

    /**
     * Constructor
     * @param message exception message
     * @param cause the cause (which is saved for later retrieval
     * by the Throwable.getCause() method). (A null value is
     * permitted, and indicates that the cause is nonexistent or
     * unknown.)
     * @param localizedTitleIn The localizedTitle to set.
     * @param localizedSummaryIn The localizedSummary to set.
     */
    public PermissionException(String message, Throwable cause, String localizedTitleIn, String localizedSummaryIn) {
        super(message, cause);
        LocalizationService ls = LocalizationService.getInstance();

        localizedTitle = localizedTitleIn != null ? localizedTitleIn : ls.getMessage("permission.jsp.title.acl");
        localizedSummary = localizedSummaryIn != null ? localizedSummaryIn : getDefaultSummary();
    }

    /**
     * Constructor
     * @param role Cause for the exception (bad role)
     * @param localizedTitleIn The localizedTitle to set.
     * @param localizedSummaryIn The localizedSummary to set.
     */
    public PermissionException(Role role, String localizedTitleIn, String localizedSummaryIn) {
        this("You do not have permissions to " +
                "perform this action. You need to have at least a " + role.getName() +
                                 " role to perform this action", localizedTitleIn, localizedSummaryIn);
    }

    private String getDefaultSummary() {
        LocalizationService ls = LocalizationService.getInstance();
        //Set the summary. The default summary gives several reasons
        StringBuilder summary = new StringBuilder();
        summary.append(ls.getMessage("permission.jsp.summary.acl.header"));

        //wrap the reasons as an ordered list
        HtmlTag ol = new HtmlTag("ol");

        //The second reason gives the minutes for a login session to expire.
        int seconds = Config.get().getInt(ConfigDefaults.WEB_SESSION_DATABASE_LIFETIME);
        int minutes = seconds / 60;
        String loginUrl = "/";
        addReason(ol, "permission.jsp.summary.acl.reason2",
                new Object[] {minutes, loginUrl});

        //The third reason gives a way to report bugs in the site.
        addReason(ol, "permission.jsp.summary.acl.reason3", null);

        //You need cookies to view our site.
        addReason(ol, "permission.jsp.summary.acl.reason4", null);
        //You've done something naughty.
        addReason(ol, "permission.jsp.summary.acl.reason5", null);

        //finally set the summary.
        summary.append(ol.render());
        return summary.toString();
    }

    /**
     * Constructor
     * @param accessGroupIn Cause for the exception (bad role)
     * @param localizedTitleIn The localizedTitle to set.
     * @param localizedSummaryIn The localizedSummary to set.
     */
    public PermissionException(AccessGroup accessGroupIn, String localizedTitleIn, String localizedSummaryIn) {
        this("You do not have permissions to " +
                "perform this action. You need to have at least a " + accessGroupIn.getLabel() +
                " role to perform this action", localizedTitleIn, localizedSummaryIn);
    }

    private void addReason(HtmlTag parent, String key, Object[] args) {
        LocalizationService ls = LocalizationService.getInstance();

        HtmlTag reason = new HtmlTag("li");
        reason.addBody(ls.getMessage(key, args));
        parent.addBody(reason);
    }


    /**
     * @return Returns the localizedSummary.
     */
    public String getLocalizedSummary() {
        return localizedSummary;
    }


    /**
     * @return Returns the localizedTitle.
     */
    public String getLocalizedTitle() {
        return localizedTitle;
    }
}
