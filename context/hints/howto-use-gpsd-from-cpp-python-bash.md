# How to read real-time GNSS data from gpsd (C++, Python, Bash)

This guide shows how to consume real-time GNSS data from gpsd in your own apps without any vendor-specific SDK. The CBGPS P‑9 outputs standard NMEA 0183; gpsd parses it and exposes a uniform JSON/C API. Any app can read from gpsd via standard interfaces.

Key point: You do not need a vendor-specific API. Use standard gpsd APIs/libraries.

## Prerequisites

- Device connection (one of):
  - USB: typically appears as `/dev/ttyACM0` or `/dev/ttyUSB0`.
  - Bluetooth SPP: pair the P‑9, bind an RFCOMM port (e.g., `/dev/rfcomm0`). See gpsd’s Bluetooth guide.
- gpsd installed and running, configured to watch your device.
  - Sanity check: run `cgps -s` or `xgps` and verify you see live data and a 2D/3D fix (mode 2/3).

References:
- gpsd Client HOWTO: https://gpsd.gitlab.io/gpsd/client-howto.html
- gpsd JSON protocol (TPV/SKY/etc.): https://gpsd.gitlab.io/gpsd/gpsd_json.html
- libgps (C/C++ client library): https://gpsd.gitlab.io/gpsd/libgps.html
- gpsd Bluetooth (RFCOMM) setup: https://gpsd.gitlab.io/gpsd/bt.html

## Start gpsd (examples)

USB device:

```bash
# Install (Debian/Ubuntu)
sudo apt-get install gpsd gpsd-clients
# Start gpsd on your device (adjust device path)
sudo systemctl stop gpsd.socket gpsd.service
sudo gpsd -N -n /dev/ttyACM0 -F /var/run/gpsd.sock
```

Bluetooth SPP (RFCOMM):

```bash
# Pair your P‑9, then bind an RFCOMM TTY (channel may vary)
sudo rfcomm connect /dev/rfcomm0 <BT_MAC_ADDRESS> 1
# Point gpsd at the rfcomm device
sudo gpsd -N -n /dev/rfcomm0 -F /var/run/gpsd.sock
```

Notes:
- Use `dpkg-reconfigure gpsd` on Debian/Ubuntu to persist configuration.
- The P‑9 outputs NMEA at up to 25 Hz; consider sampling/decimation in your client.

## C++: using libgpsmm

Install headers: `sudo apt-get install libgps-dev`

```cpp
#include <libgpsmm.h>
#include <iostream>
#include <cmath>    // isfinite

int main() {
  gpsmm gps("localhost", DEFAULT_GPSD_PORT);
  if (gps.stream(WATCH_ENABLE | WATCH_JSON) == nullptr) {
    std::cerr << "Failed to open GPSD stream\n";
    return 1;
  }
  while (true) {
    if (!gps.waiting(500000)) continue; // 500 ms timeout
    struct gps_data_t* data = gps.read();
    if (!data) continue;
    // Ensure we have a TPV fix
    if (!(data->set & MODE_SET) || data->fix.mode < 2) continue; // need 2D/3D
    if (std::isfinite(data->fix.latitude) && std::isfinite(data->fix.longitude)) {
      std::cout << "lat=" << data->fix.latitude
                << ", lon=" << data->fix.longitude
                << ", mode=" << data->fix.mode << "\n";
    }
  }
}
// Build: g++ main.cpp -o gps_client -lgps
```

More examples: https://gpsd.gitlab.io/gpsd/gpsd-client-example-code.html

## Python: gpsd “gps” module (from gpsd-clients)

Install gpsd clients (provides the modern `gps` Python module):

```bash
sudo apt-get install gpsd-clients
```

Example (filter on TPV, require mode ≥ 2):

```python
from gps import gps, WATCH_ENABLE, WATCH_JSON, MODE_SET, TIME_SET

session = gps(mode=WATCH_ENABLE | WATCH_JSON)
while True:
    if session.read() != 0:
        continue
    if not (session.valid & MODE_SET) or session.fix.mode < 2:
        continue
    lat = session.fix.latitude
    lon = session.fix.longitude
    if lat is not None and lon is not None:
        t = session.fix.time if (session.valid & TIME_SET) else None
        print(f"lat={lat} lon={lon} time={t} mode={session.fix.mode}")
```

Alternative (pure JSON streaming):

```python
from gpsdclient import GPSDClient

with GPSDClient(host="127.0.0.1", port=2947) as client:
    for msg in client.dict_stream(filter=["TPV"], convert_datetime=True):
        if msg.get("mode", 0) >= 2:
            print(msg.get("lat"), msg.get("lon"), msg.get("time"))
```

Client HOWTO: https://gpsd.gitlab.io/gpsd/client-howto.html

## Bash: gpspipe + jq

`gpspipe` can emit gpsd JSON; use `jq` to extract TPV fields.

```bash
# Install jq
sudo apt-get install jq

# Stream TPV lat/lon/time when mode>=2 (2D/3D)
gpspipe -w | jq -r 'select(.class=="TPV" and (.mode//0) >= 2) | "\(.lat),\(.lon),\(.time)"'
```

Raw NMEA (if needed):

```bash
gpspipe -r # raw NMEA sentences
```

## ROS 2: packages and quick-start

If you're using ROS 2 (Python or C++), you don't need a vendor SDK. Use one of these standard packages to read the P‑9 (NMEA 0183) and publish `sensor_msgs/msg/NavSatFix`:

- nmea_navsat_driver (serial/socket NMEA)
  - Node: `nmea_serial_driver` (reads from `/dev/tty*`), `nmea_socket_driver` (TCP/UDP)
  - Publishes: `/fix` (NavSatFix), `/time_reference` (optional)
  - Links: ROS Index https://index.ros.org/p/nmea_navsat_driver/ · GitHub https://github.com/ros-drivers/nmea_navsat_driver
- gps_umd (gpsd client)
  - Node: `gpsd_client` (reads from a running gpsd on 2947)
  - Publishes: `/fix` (NavSatFix)
  - Links: ROS Index https://index.ros.org/p/gps_umd/ · GitHub https://github.com/swri-robotics/gps_umd

Install (Ubuntu/Debian; replace $ROS_DISTRO with your distro, e.g., humble/jazzy):

```bash
sudo apt update
sudo apt install ros-$ROS_DISTRO-nmea-navsat-driver ros-$ROS_DISTRO-gps-umd
```

Quick start (choose one path):

1) Direct serial via nmea_navsat_driver

```bash
# Find your device path: e.g., /dev/ttyACM0 (USB) or /dev/rfcomm0 (Bluetooth SPP)
ros2 run nmea_navsat_driver nmea_serial_driver \
  --ros-args -p port:=/dev/ttyACM0 -p baud:=115200 -p frame_id:=gps -p use_gps_time:=true
```

2) Via gpsd using gps_umd

```bash
# Ensure gpsd is running and receiving data (see earlier sections)
ros2 run gps_umd gpsd_client \
  --ros-args -p host:=127.0.0.1 -p port:=2947 -p frame_id:=gps
```

Validate topics:

```bash
ros2 topic echo /fix --once
ros2 topic hz /fix
```

Tiny subscriber examples

- Python (rclpy):

```python
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix

class FixEcho(Node):
    def __init__(self):
        super().__init__('fix_echo')
        self.create_subscription(NavSatFix, 'fix', self.cb, 10)

    def cb(self, msg: NavSatFix):
        self.get_logger().info(f"lat={msg.latitude:.7f}, lon={msg.longitude:.7f}, alt={msg.altitude:.2f}")

def main():
    rclpy.init()
    node = FixEcho()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

- C++ (rclcpp):

```cpp
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/nav_sat_fix.hpp>

class FixEcho : public rclcpp::Node {
public:
  FixEcho() : Node("fix_echo") {
    sub_ = create_subscription<sensor_msgs::msg::NavSatFix>(
      "fix", 10,
      [this](sensor_msgs::msg::NavSatFix::SharedPtr msg){
        RCLCPP_INFO(get_logger(), "lat=%.7f lon=%.7f alt=%.2f", msg->latitude, msg->longitude, msg->altitude);
      }
    );
  }
private:
  rclcpp::Subscription<sensor_msgs::msg::NavSatFix>::SharedPtr sub_;
};

int main(int argc, char** argv){
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<FixEcho>());
  rclcpp::shutdown();
  return 0;
}
```

Notes

- Serial speed: common NMEA rates are 9600/38400/115200 baud. The P‑9 often uses 115200 for high update rates.
- Bluetooth: prefer Bluetooth Classic SPP bound to `/dev/rfcommN` so it appears as a serial port. BLE needs a forwarder to TCP/TTY; alternatively, let gpsd read BLE (via a helper) and use `gps_umd`.
- Time source: set `use_gps_time:=true` if you want `time_reference` and GPS time stamps; ensure your system time sync expectations are clear.
- Frame IDs: set `frame_id:=gps` (or your choice) for downstream TF consumers.
- Fusion: to fuse GNSS with IMU/wheel odom into a filtered odometry, see `robot_localization` (ekf/ukf) with `/fix` and IMU inputs.

## Tips & edge cases

- Always gate on `mode` (2 = 2D, 3 = 3D); until fix, TPV may have `mode:1`.
- Float fields may be NaN/inf; in C/C++ check with `isfinite()`.
- Multiple devices: use the `device` field to disambiguate or run separate gpsd instances.
- Bluetooth SPP: prefer RFCOMM (/dev/rfcommN) for gpsd; BLE requires a custom forwarder.

## Related vendor docs (P‑9)

- SPP (Bluetooth Classic) outputs standard NMEA 0183: https://cbgps.com/p9/app/developer/spp/index_en.htm
- BLE UUID/characteristics (if you choose to build a BLE→TTY forwarder): https://cbgps.com/p9/app/developer/btle/index_en.htm

---

Sources and further reading:
- gpsd Client Example Code: https://gpsd.gitlab.io/gpsd/gpsd-client-example-code.html
- gpsd JSON protocol: https://gpsd.gitlab.io/gpsd/gpsd_json.html
- libgps manual: https://gpsd.gitlab.io/gpsd/libgps.html
- gpspipe manual: http://rpm.pbone.net/manpage_idpl_17916548_numer_1_nazwa_gpspipe.html
- gpsd Bluetooth setup: https://gpsd.gitlab.io/gpsd/bt.html
