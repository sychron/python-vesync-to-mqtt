# python-vesync-to-mqtt
python script to bridge between mqtt and vesync devices.

This allows MQTT dashboard apps or Home Automation systems like iobroker to control vesync air purifiers via MQTT.

This is not a binding for iobroker, but a standalone script. 

## State

This script is in a usable state and currently deployd to my home automation system.

But: it currently only supports the functionalty I actually need.

Might be expanded in the future to support more devices and features, feel free to contribute.

## Prerequisites:

- python 3.
- `pip3 install paho-mqtt`
- `pip3 install pyvesync`

## Configuration
 
You need to create an ini file with all needed credentials. 

The ini file is excluded via .gitignore

    [vesync]
    username=<username of vesync account>
    password=<password of vesync account>
    timezone=<your timezone, for example Europe/Berlin>

    [mqtt]
    brokerip=<ip address of your broker>
    brokerport=<port of your broker, defaults to 1833 if not set>
    brokerauth=<does the broker require auth? (username/passwort only supported by now)
    username=<broker username>
    password=<broker password>
    clientid=<a unique client id. will default to python-vesync-to-mqtt if not set.>
    roottopic=<the root topic the script will subscribe and publish to. defaults to vesync if not set>

## Starting and stopping

### General usage

- start the script as usual: `python3 python-vesync-to-mqtt.py`
- stop the script using `ctrl+c`    
    
### Using the script as a background task in linux (continue running after user logout)

- make the script executable
- start the script using `nohup ./python-vesync-to-mqtt.py >/dev/null 2>&1 &`
- stop the script using `ps -fA | grep python` to get the PID and `kill PID` to stop the script

## Usage

The script connects to the specified vesync accound and gets a list of active devices. It then starts monitoring these devices and posts status updates via mqtt.
Currently only Levoid Air Purifiers are supported.

### device status information

topics are build following the schema `<root-topic>/<Device Name>/#`

| subtopic   | information | payload values      |
| ---------- | ----------- |-------------------- |
| `level`    | fan speed   | 1, 2, 3             |
| `mode`     | device mode | sleep, manual, auto |
| `combined` | see below   | 0, 1, 2, 3          |

### setting values

This script follows the style of espurna devices. To set a value, attach `/set` to the topic.

For example to activate sleep mode, send payload `sleep` to `<root topic>/<device name>/mode/set`.

### the combined setting

`combined` is a calculated value. It's an extension  to the fan speed using speed 0 to indicate sleep mode.

So if a purifier is set to fan speed 3 and sleep mode, `combined` will read 0 while `level` will read 3

This allows to use only one widget in your favorite MQTT control app to switch between for example sleep mode and fan level 3.

