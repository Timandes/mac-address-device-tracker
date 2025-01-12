# MAC Address Device Tracker

MAC address device tracker for Home Assistant. Most codes are derived from [@mudape's iPhone Detect](https://github.com/mudape/iphonedetect).

## Installation

### Git clone from GitHub

```shell
cd config
git clone https://github.com/Timandes/mac-address-device-tracker.git
cd mac-address-device-tracker
./install.sh /config
```

Then restart Home Assistant.

Update for vx.x.x:

```shell
cd config/mac-address-device-tracker
git fetch
git checkout vx.x.x
./install.sh /config
```

### Configuration

Open and edit configuration.yaml located in `/config` directory:

```yaml
device_tracker:
  - platform: mac_address_device_tracker
    consider_home: 180
    scan_interval: 12
    hosts:
      daddy: 9C:A6:92:99:98:D2
      mommy: 98:7F:53:56:1C:9E
```

Restart Home Assistant. That will create entities named `device_tracker.daddy` and `device_tracker.mommy`.


