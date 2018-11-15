# This file is a part of Remoulade.
#
# Copyright (C) 2017,2018 WIREMIND SAS <dev@wiremind.fr>
#
# Remoulade is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Remoulade is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import signal
import time
from unittest.mock import Mock

from remoulade.brokers.stub import StubBroker
from remoulade.middleware import TimeLimit


def test_no_timer_signal_after_shutdown():
    # Given a broker
    broker = StubBroker()

    # With a TimeLimit middleware
    for middleware in broker.middleware:
        if isinstance(middleware, TimeLimit):
            # That emit a signal every ms
            middleware.interval = 1

    broker.emit_after("process_boot")

    handler = Mock()

    signal.signal(signal.SIGALRM, handler)

    broker.emit_before("process_stop")

    # If i wait enough time to get a signal
    time.sleep(2 / 1000)

    # No signal should have been sent
    assert not handler.called
