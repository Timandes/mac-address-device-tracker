"""
From : https://github.com/mudape/iphonedetect

device_tracker:
  - platform: mac_address_device_tracker
    hosts:
      daddy: DC:A6:32:9B:98:D2
      mommy: C8:7F:54:56:0C:8E

"""
import logging
import socket
import subprocess

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
import voluptuous as vol
from homeassistant.components.device_tracker import PLATFORM_SCHEMA, SourceType
from homeassistant.components.device_tracker.const import (CONF_SCAN_INTERVAL, SCAN_INTERVAL,
                                                            CONF_CONSIDER_HOME, DEFAULT_CONSIDER_HOME,
                                                            ATTR_MAC)
from homeassistant.const import CONF_HOSTS, STATE_NOT_HOME, STATE_HOME
from homeassistant.helpers.event import track_point_in_utc_time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import track_point_in_utc_time

from .const import (
    HOME_STATES,
    CONST_MESSAGE,
    CONST_MESSAGE_PORT,
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOSTS): {cv.string: cv.string},
        vol.Optional(CONF_SCAN_INTERVAL): cv.time_period,
        vol.Optional(CONF_CONSIDER_HOME, default=DEFAULT_CONSIDER_HOME): vol.All(
            cv.time_period, cv.positive_timedelta
        ),
    }
)

_LOGGER = logging.getLogger(__name__)

REACHABLE_DEVICE_MAC_ADDRS = []

class Host:
    """Host object with arp detection."""

    def __init__(self, dev_id, dev_mac_addr):
        """Initialize the Host."""
        self.dev_id = dev_id
        self.dev_mac_addr = dev_mac_addr

    def ping_device(self):
        """Send UDP message to probe device."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(1)
            s.sendto(CONST_MESSAGE, (self.dev_mac_addr, CONST_MESSAGE_PORT))
        _LOGGER.debug(f"Probe sent to {self.dev_id} on {self.dev_mac_addr}")

    def update_device(self, see, consider_home: timedelta | None = None):
        """Update tracked devices"""
        _LOGGER.debug(f"REACHABLE_DEVICE_MAC_ADDRS: {REACHABLE_DEVICE_MAC_ADDRS}")
        if self.dev_mac_addr in REACHABLE_DEVICE_MAC_ADDRS:
            self.last_seen = dt_util.utcnow()
            location_name = STATE_HOME

        if self.stale(dt_util.utcnow(), consider_home):
            location_name = STATE_NOT_HOME

        _LOGGER.debug(f"Device {self.dev_id} on {self.dev_mac_addr} is {location_name}")
        see(dev_id = self.dev_id,
            attributes = {ATTR_MAC: self.dev_mac_addr},
            location_name = location_name,
            source_type = SourceType.ROUTER)

    @staticmethod
    def find_with_ip():
        """Queries the network neighbours and lists found MAC Addresses"""
        state_filter = " nud " + " nud ".join(HOME_STATES.values()).lower()
        """IPv4 only"""
        cmd = f"ip -4 neigh show {state_filter}".split()
        neighbours = subprocess.run(cmd, shell=False, capture_output=True, text=True)
        neighbours_mac_addr = [_.split()[4] for _ in neighbours.stdout.splitlines()]
        return neighbours_mac_addr

    @staticmethod
    def find_with_arp():
        """Queries the arp table and lists found MAC Addresses"""
        cmd = "arp -na"
        neighbours = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        neighbours_mac_addr = [_.split()[3] for _ in neighbours.stdout.splitlines() if _.count(":") == 5]
        return neighbours_mac_addr

    def stale(self, now: datetime | None = None, consider_home: timedelta | None = None) -> bool:
        """Return if device state is stale."""
        return (
            self.last_seen is None
            or (now or dt_util.utcnow()) - self.last_seen > consider_home
        )


def setup_scanner(hass: HomeAssistant, config, see, discovery_info=None):
    """Set up the Host objects and return the update function."""

    if subprocess.run("which ip", shell=True, stdout=subprocess.DEVNULL).returncode == 0:
        _LOGGER.debug("Using 'IP' to find tracked devices")
        _use_cmd_ip = True
    elif subprocess.run("which arp", shell=True, stdout=subprocess.DEVNULL).returncode == 0:
        _LOGGER.warn("Using 'ARP' to find tracked devices")
        _use_cmd_ip = False
    else:
        _LOGGER.fatal("Can't get neighbours from host OS!")
        return

    hosts = [Host(dev_id, dev_mac_addr) for (dev_id, dev_mac_addr) in
             config[CONF_HOSTS].items()]
    interval = config.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL)
    consider_home = config.get(CONF_CONSIDER_HOME, DEFAULT_CONSIDER_HOME)

    _LOGGER.info("Started mac_address_device_tracker with interval=%s on hosts: %s",
                  interval, ", ".join([host.dev_mac_addr for host in hosts]))


    def update_interval(now):
        """Update all the hosts on every interval time."""
        try:
            """
            for host in hosts:
                Host.ping_device(host)
            """

            global REACHABLE_DEVICE_MAC_ADDRS
            if _use_cmd_ip:
                REACHABLE_DEVICE_MAC_ADDRS = Host.find_with_ip()
            else:
                REACHABLE_DEVICE_MAC_ADDRS = Host.find_with_arp()

            for host in hosts:
                Host.update_device(host, see, consider_home)

        except Exception as e:
            _LOGGER.error(e)

        finally:
            track_point_in_utc_time(
                hass, update_interval, dt_util.utcnow() + interval)

    update_interval(None)
    return True
