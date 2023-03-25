#!/usr/bin/env python3

from configparser import ConfigParser
import paho.mqtt.client as mqtt
from pyvesync import VeSync

DEBUG = False
CONTROL_TOPIC = "vesync"

class VesyncToMqtt:
    """Handles VeSync to MQTT translation"""
    fanbuffer=dict()
    debug = False

    # === Constructor ===============================================

    def __init__(self, debug = False):
        self.debug=debug
        self.init_config()
        self.init_vesync(debug)

    # === Config ====================================================

    Config = ConfigParser()

    def init_config(self):
        """Read config file from disk."""
        self.Config.read("python-vesync-to-mqtt.ini")

    # === VeSync ====================================================

    fans = []

    def init_vesync(self, debug = False):
        """Initializes the vesync connection."""
        manager = VeSync(
            self.Config.get('vesync','username'),
            self.Config.get('vesync','password'),
            self.Config.get('vesync','timezone'),
            debug)
        manager.login()
        manager.update()
        self.fans = manager.fans
        for fan in self.fans:
            self.fanbuffer[fan.device_name]={"mode":0,"level":0,"status":0, "combined":0}
            if debug:
                print (fan)
            else:
                print (fan.device_name)

    def process_fan_info(self):
        """Detect changes in vesync fan information and publish them"""
        for fan in self.fans:
            change = False
            fan.update()
            basetopic="vesync/"+fan.device_name+"/"
            if self.fanbuffer[fan.device_name]["level"] != fan.fan_level:
                self.fanbuffer[fan.device_name]["level"] = fan.fan_level
                self.Mqtt_client.publish(basetopic + "level", fan.fan_level, retain=True)
                change = True
            if self.fanbuffer[fan.device_name]["status"] != fan.device_status:
                self.fanbuffer[fan.device_name]["status"] = fan.device_status
                self.Mqtt_client.publish(basetopic + "status", fan.device_status, retain=True)
            if self.fanbuffer[fan.device_name]["mode"] != fan.mode:
                self.fanbuffer[fan.device_name]["mode"] = fan.mode
                self.Mqtt_client.publish(basetopic + "mode", fan.mode, retain=True)
                change = True
            if change:
                if "manual" == fan.mode:
                    self.fanbuffer[fan.device_name]["combined"] = fan.fan_level
                elif "sleep" == fan.mode:
                    self.fanbuffer[fan.device_name]["combined"] = 0
                self.Mqtt_client.publish(
                    basetopic + "combined",
                    self.fanbuffer[fan.device_name]["combined"],
                    retain=True)

    def set_combined(self, fan, value):
        """Interpret combined state and set fan accordingly."""
        if self.debug:
            print ("Setting combined.")
        value = int(value)
        if (value > 0) and (value < 4):
            fan.change_fan_speed(value)
        elif value == 0:
            fan.sleep_mode()
            return False
        return True

    def set_fan_level(self, fan, value):
        """Check bounds of fan level value and transmit to vesync if ok."""
        if self.debug:
            print ("Setting level.")
        value = int(value)
        if (value > 0) and (value < 4):
            fan.change_fan_speed(value)
        else:
            if self.debug:
                print ("invalid speed: ", value)
            return False
        return True

    def set_fan_mode(self, fan, mode):
        """transmit fan mode to vesync if legal."""
        if self.debug:
            print ("Setting mode.")
        if "sleep " == mode:
            fan.sleep_mode()
        elif "manual" == mode:
            fan.manual_mode()
        elif "auto" == mode:
            fan.auto_mode()
        else:
            if self.debug:
                print ("invalid mode: ", mode)
            return False
        return True

    # === MQTT ======================================================

    Mqtt_client = None

    def set_mqtt_client(self, the_client):
        """Sets local client reference"""
        self.Mqtt_client = the_client

    def on_connect(self, client, userdata, flags, rc):
        """MQTT event handler: connect notification"""
        print("MQTT Connected, result code "+str(rc))
        client.subscribe(CONTROL_TOPIC + "/#")

    def on_message(self, client, userdata, msg):
        """Handle messages received by the client"""
        topic = msg.topic.split("/")
        if not CONTROL_TOPIC == topic[0]:
            return
        if len(topic) < 4:    # topic long enaugh?
            if self.debug:
                print ("topic too short")
            return
        if topic[3] != "set": # no setter, no service
            return
        the_fan = dict()
        found = False
        for fan in self.fans:
            if fan.device_name==topic[1]:
                the_fan = fan
                found = True
        if not found:
            if self.debug:
                print ("device unknown")
            return
        payload = msg.payload.decode("utf-8")
        if self.debug:
            print ("Addressing fan:", the_fan.device_name)
        if "combined" == topic[2]:
            self.set_combined (the_fan, payload)
        elif "mode" == topic[2]:
            self.set_fan_mode (the_fan, payload)
        elif "level" == topic[2]:
            self.set_fan_level (the_fan, payload)
        else:
            if self.debug:
                print ("invalid control command: ", topic[2])

# === Setup the handler class ===================================

vesync_to_mqtt = VesyncToMqtt(DEBUG)

# === Setup PAHO MQTT (cannot be inside the class) ==============

def mqtt_on_connect(client, userdata, flags, rc):
    """PAHO MQTT event handler: connect notification"""
    vesync_to_mqtt.on_connect(client, userdata, flags, rc)

def mqtt_on_message(client, userdata, msg):
    """PAHO MQTT event handler: message received"""
    vesync_to_mqtt.on_message(client, userdata, msg)

def init_mqtt(vesync_connector):
    """Setup PAHO MQTT client."""
    client = mqtt.Client()
    client.reinitialise(
        vesync_connector.Config.get(
            'mqtt','clientid',
            fallback="python-vesync-to-mqtt"))
    client.on_connect = mqtt_on_connect
    client.on_message = mqtt_on_message
    client.username_pw_set(
        vesync_connector.Config.get('mqtt','username'),
        vesync_connector.Config.get('mqtt','password'))
    client.connect(
        vesync_connector.Config.get('mqtt','brokerip'),
        vesync_connector.Config.getint('mqtt','brokerport',fallback=1883),
        60)
    client.loop_start()
    return client

mqtt_client = init_mqtt(vesync_to_mqtt)
vesync_to_mqtt.set_mqtt_client(mqtt_client)


# === Main ======================================================

# it's a variable, not a constant
# pylint: disable=C0103
run_loop = True
# pylint: enable=C0103

while run_loop:
    #client.loop(timeout=1.0, max_packets=10)
    vesync_to_mqtt.process_fan_info()
