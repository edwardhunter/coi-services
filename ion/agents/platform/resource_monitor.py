#!/usr/bin/env python

"""
@package ion.agents.platform.resource_monitor
@file    ion/agents/platform/resource_monitor.py
@author  Carlos Rueda
@brief   Platform resource monitoring
"""

__author__ = 'Carlos Rueda'
__license__ = 'Apache 2.0'


from pyon.public import log

from ion.agents.platform.platform_driver_event import AttributeValueDriverEvent
from ion.agents.platform.util import ntp_2_ion_ts

import logging
from gevent import Greenlet, sleep


# A small "ION System time" compliant increment to the latest received timestamp
# for purposes of the next request so we don't get that last sample repeated.
# Since "ION system time" is in milliseconds, this delta is in milliseconds.
_DELTA_TIME = 10


class ResourceMonitor(object):
    """
    Monitor for specific attributes in a given platform.
    Currently it only supports a single attribute.
    @todo expand to support multiple attributes that can be monitored using the
          same (or almost same) polling rate.
    """

    def __init__(self, platform_id, attr_id, attr_defn,
                 get_attribute_values, notify_driver_event):
        """
        Creates a monitor for a specific attribute in a given platform.
        Call start to start the monitoring greenlet.

        @param platform_id Platform ID
        @param attr_id Attribute name
        @param attr_defn Corresponding attribute definition
        @param get_attribute_values Function to retrieve attribute
                 values for the specific platform, called like this:
                 get_attribute_values([self._attr_id], from_time)
        @param notify_driver_event Callback to notify whenever a value is
                retrieved.
        """
        if log.isEnabledFor(logging.DEBUG):
            log.debug("%r: ResourceMonitor entered. attr_defn=%s",
                      platform_id, attr_defn)

        assert platform_id, "must give a valid platform ID"
        assert 'monitorCycleSeconds' in attr_defn, "must include monitorCycleSeconds"

        self._get_attribute_values = get_attribute_values
        self._platform_id = platform_id
        self._attr_defn = attr_defn
        self._notify_driver_event = notify_driver_event

        self._attr_id = attr_id
        self._monitorCycleSeconds = attr_defn['monitorCycleSeconds']

        # "ION System time" compliant timestamp of last retrieved attribute value
        self._last_ts = None

        self._active = False

        if log.isEnabledFor(logging.DEBUG):
            log.debug("%r: ResourceMonitor created. attr_defn=%s",
                      self._platform_id, attr_defn)

    def __str__(self):
        return "%s{platform_id=%r; attr_id=%r; attr_defn=%r}" % (
            self.__class__.__name__,
            self._platform_id, self._attr_id, self._attr_defn)

    def start(self):
        """
        Starts greenlet for resource monitoring.
        """
        if log.isEnabledFor(logging.DEBUG):
            log.debug("%r: starting resource monitoring %s", self._platform_id, str(self))
        self._active = True
        runnable = Greenlet(self._run)
        runnable.start()

    def _run(self):
        """
        The target for the greenlet.
        """
        while self._active:
            sleep(self._monitorCycleSeconds)
            if self._active:
                self._retrieve_attribute_value()

        if log.isEnabledFor(logging.DEBUG):
            log.debug("%r: attr_id=%r: greenlet stopped.", self._platform_id, self._attr_id)

    def _retrieve_attribute_value(self):
        """
        Retrieves the attribute value using the given function and calls
        _values_retrieved with retrieved values.
        """
        attrNames = [self._attr_id]
        # note that int(x) returns a long object if needed.
        from_time = (int(self._last_ts) + _DELTA_TIME) if self._last_ts else 0

        log.debug("%r: _retrieve_attribute_value: attribute=%r from_time=%s",
                  self._platform_id, self._attr_id, from_time)

        retrieved_vals = self._get_attribute_values(attrNames, from_time)

        log.debug("%r: _retrieve_attribute_value: _get_attribute_values "
                  "for attribute %r and from_time=%s returned %s",
                  self._platform_id,
                  self._attr_id, from_time, retrieved_vals)

        if self._attr_id in retrieved_vals:
            values = retrieved_vals[self._attr_id]
            if values:
                self._values_retrieved(values)

            else:
                log.debug("%r: No values reported for attribute=%r from_time=%f",
                          self._platform_id, self._attr_id, from_time)
        else:
            log.warn("%r: _retrieve_attribute_value: unexpected: "
                     "response does not include requested attribute %r",
                     self._platform_id, self._attr_id)

    def _values_retrieved(self, values):
        """
        A values response has been received. Create and notify
        corresponding event to platform agent.
        """
        if log.isEnabledFor(logging.DEBUG):
            ln = len(values)
            # just show a couple of elements
            arrstr = "["
            if ln <= 3:
                vals = [str(e) for e in values[:ln]]
                arrstr += ", ".join(vals)
            else:
                vals = [str(e) for e in values[:2]]
                last_e = values[-1]
                arrstr += ", ".join(vals)
                arrstr += ", ..., " +str(last_e)
            arrstr += "]"
            log.debug("%r: attr=%r: values retrieved(%s) = %s",
                self._platform_id, self._attr_id, ln, arrstr)

        # update _last_ts based on last element's timestamp in values: note
        # that the timestamp is reported in NTP so we need to convert it to
        # ION system time for a subsequent request:
        _, ntp_ts = values[-1]

        self._last_ts = ntp_2_ion_ts(ntp_ts)
        log.debug("%r: _values_retrieved: _last_ts=%s", self._platform_id, self._last_ts)

        driver_event = AttributeValueDriverEvent(self._platform_id,
                                                 self._attr_id, values)
        self._notify_driver_event(driver_event)

    def stop(self):
        if log.isEnabledFor(logging.DEBUG):
            log.debug("%r: stopping resource monitoring %s", self._platform_id, str(self))
        self._active = False
