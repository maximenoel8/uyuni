#  pylint: disable=missing-module-docstring
#
# Copyright (c) 2008--2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import os
import sys
import time
from spacewalk.server import rhnSQL

print((os.getpid()))
rhnSQL.initDB("rhnuser/rhnuser@webdev")

h = rhnSQL.prepare("select 1 from dual")

start = time.time()
write = sys.stderr.write
i = 0
while i < 10000:
    h.execute()
    if i % 100 == 0:
        # pylint: disable-next=unspecified-encoding
        f = open("/proc/self/status")
        l = f.readlines()
        vmsize = l[10][10:-1]
        vmrss = l[12][10:-1]
        f.close()
        # pylint: disable-next=consider-using-f-string
        write("%d %.3f vsz: %s rss: %s \n" % (i, time.time() - start, vmsize, vmrss))
    i = i + 1
