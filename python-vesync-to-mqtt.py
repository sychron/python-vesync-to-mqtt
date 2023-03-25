#!/usr/bin/env python3

from configparser import ConfigParser
import paho.mqtt.client as mqtt
from pyvesync import VeSync

# === Config ====================================================

DEBUG = False

config = ConfigParser()

def init_config():
    global config
    config.read("python-vesync-to-mqtt.ini")

# === VeSync ====================================================

fanbuffer=dict()
fans = []

def init_vesync(debug = False):
    """Initializes the vesync connection."""
    global fans
    global fanbuffer
    global config
    manager = VeSync(
        config.get('vesync','username'),
        config.get('vesync','password'),
        config.get('vesync','timezone'),
        debug)
    manager.login()
    manager.update()
    fans = manager.fans
    for fan in fans:
        fanbuffer[fan.device_name]={"mode":0,"level":0,"status":0, "combined":0}
        if debug:
            print (fan)
        else:
            print (fan.device_name)

def process_fan_info():
    """Detect changes in vesync fan information and publish them"""
    global fans
    global fanbuffer
    for fan in fans:
        change = False
        fan.update()
        basetopic="vesync/"+fan.device_name+"/"
        if fanbuffer[fan.device_name]["level"] != fan.fan_level:
            fanbuffer[fan.device_name]["level"] = fan.fan_level
            client.publish(basetopic + "level", fan.fan_level, retain=True)
            change = True
        if fanbuffer[fan.device_name]["status"] != fan.device_status:
            fanbuffer[fan.device_name]["status"] = fan.device_status
            client.publish(basetopic + "status", fan.device_status, retain=True)
        if fanbuffer[fan.device_name]["mode"] != fan.mode:
            fanbuffer[fan.device_name]["mode"] = fan.mode
            client.publish(basetopic + "mode", fan.mode, retain=True)
            change = True
        if change:
            if "manual" == fan.mode:
                fanbuffer[fan.device_name]["combined"] = fan.fan_level
            elif "sleep" == fan.mode:
                fanbuffer[fan.device_name]["combined"] = 0
            client.publish(basetopic + "combined", fanbuffer[fan.device_name]["combined"], retain=True)

def setCombined(fan, value):
    global DEBUG
    if DEBUG:
        print ("Setting combined.")
    value = int(value)
    if (value > 0) and (value < 4):
        fan.change_fan_speed(value)
    elif (value == 0):
        fan.sleep_mode()
    return

def setFanLevel(fan, value):
    global DEBUG
    if DEBUG:
        print ("Setting level.")
    value = int(value)
    if (value > 0) and (value < 4):
        fan.change_fan_speed(value)
    else:
        if DEBUG:
            print ("invalid speed: ", value)
    return

def setFanMode(fan, mode):
    global DEBUG
    if DEBUG:
        print ("Setting mode.")
    if "sleep " == mode:
        fan.sleep_mode()
    elif "manual" == mode:
        fan.manual_mode()
    elif "auto" == mode:
        fan.auto_mode()
    else:
        if DEBUG:
            print ("invalid mode: ", mode)
    return

# === MQTT ======================================================

client = mqtt.Client()

controlTopic = "vesync"
RunLoop = True

def on_connect(client, userdata, flags, rc):
    global controlTopic
    print("MQTT Connected, result code "+str(rc))
    client.subscribe(controlTopic + "/#")

def on_message(client, userdata, msg):
    """Handle messages received by the client"""
    global DEBUG
    global controlTopic
    global fanbuffer
    global fans
    topic = msg.topic.split("/")
    if not (topic[0] == controlTopic):
        return
    if len(topic) < 4:    # topic long enaugh?
        if DEBUG:
            print ("topic too short")
        return
    if topic[3] != "set": # no setter, no service
        return
    theFan = dict()
    found = False
    for fan in fans:
        if ( fan.device_name==topic[1] ):
            theFan = fan
            found = True
    if not found:
        if DEBUG:
            print ("device unknown")
        return False
    payload = msg.payload.decode("utf-8")
    if DEBUG:
        print ("Addressing fan:", theFan.device_name)
    if "combined" == topic[2]:
        setCombined (theFan, payload)
    elif "mode" == topic[2]:
        setFanMode (theFan, payload)
    elif "level" == topic[2]:
        setFanLevel (theFan, payload)

def init_mqtt():
    global config
    client.reinitialise(
        config.get('mqtt','clientid',
            fallback="python-vesync-to-mqtt"))
    client.on_connect = on_connect
    client.on_message = on_message
    client.username_pw_set(
        config.get('mqtt','username'),
        config.get('mqtt','password'))
    client.connect(
        config.get('mqtt','brokerip'),
        config.getint('mqtt','brokerport',fallback=1883),
        60)
    client.loop_start()

# === Main ======================================================

init_config()
init_vesync(DEBUG)
init_mqtt()

while RunLoop:
    #client.loop(timeout=1.0, max_packets=10)
    process_fan_info()
