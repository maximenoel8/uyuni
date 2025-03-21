/*
 * Copyright (c) 2009--2017 Red Hat, Inc.
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
package com.redhat.rhn.domain.channel;

import com.redhat.rhn.frontend.struts.Selectable;

import org.apache.commons.lang3.builder.EqualsBuilder;
import org.apache.commons.lang3.builder.HashCodeBuilder;

/**
 * Wrapper class to enable Channels to be used and be selectable
 * SelectableChannel
 */
public class SelectableChannel  implements Selectable, Comparable<SelectableChannel> {

    private Channel channel;
    private boolean selected = false;



    /**
     * Constuctor
     * @param chan the chan to wrap
     */
    public SelectableChannel(Channel chan) {
        channel = chan;
    }


    /**
     * checks to see if this is a base channel
     * @return true if it is a base channel, false otherwise
     */
    public boolean isBaseChannel() {
        return channel.isBaseChannel();
    }



    /**
     * @return Returns the channel.
     */
    public Channel getChannel() {
        return channel;
    }


    /**
     * @param channelIn The channel to set.
     */
    public void setChannel(Channel channelIn) {
        this.channel = channelIn;
    }


    /**
     * @return Returns the id.
     */
    public Long getId() {
        return channel.getId();
    }


    /**
     * @param id The id to set.
     */
    public void setId(Long id) {
        channel.setId(id);
    }


    /**
     * @return Returns the name.
     */
    public String getName() {
        return channel.getName();
    }


    /**
     * @param name The name to set.
     */
    public void setName(String name) {
        channel.setName(name);
    }

    /**
     * @return Returns true if the contained Channel has no parent, false otherwise
     */
    public boolean isParent() {
        return channel.isBaseChannel();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public String getSelectionKey() {
        return null;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public boolean isSelectable() {
        return true;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public boolean isSelected() {
        return selected;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public void setSelected(boolean selectedIn) {
        selected = selectedIn;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public int compareTo(SelectableChannel o) {
       return this.getChannel().getName().compareTo(o.getChannel().getName());
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public boolean equals(final Object other) {
        if (other instanceof Channel castOther) {
            return this.getChannel().equals(castOther);
        }
        if (!(other instanceof SelectableChannel castOther)) {
            return false;
        }
        return new EqualsBuilder().append(getId(), castOther.getId()).isEquals();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public int hashCode() {
        return new HashCodeBuilder().append(getId()).toHashCode();
    }
}
