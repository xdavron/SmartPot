# MQTT Client that sends messages to Plant Care actor, in order to control water pump and light
# message format: {'mode' : ('man', 'auto' or 'fb'), 'command':(cmdString), 'timestamp': time at which msg is sent}
# NOTE: cmdString is a string that should specify the amount of time the device should be on

import time
import json
import paho.mqtt.client as PahoMQTT
from datetime import datetime


class MQTTClient:
    QoS = 2  # quality of service
    brokerPort = 1883 # TCP port
    DEBUG = False

    def __init__(self, clientID, brokerIP, brokerPort):
        self.clientID = clientID
        self.messageBroker = brokerIP
        self.brokerPort = brokerPort
        self._paho_mqtt = PahoMQTT.Client(self.clientID, False)
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

    def start(self):
        # connect to server and start loop
        self._paho_mqtt.connect(host=self.messageBroker, port=self.brokerPort)
        self._paho_mqtt.loop_start()

    def stop(self):
        # abort connection and stop the loop
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

    def publishCommand(self, topic, msgStr):
        # publish a message with a certain topic
        dateTimeObj = datetime.now()
        timestampStr = dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S)")
        if self.DEBUG:
            print(f'publising message: topic: {topic} cmdStr: {msgStr}')
        self._paho_mqtt.publish(topic, msgStr, self.QoS)

    def mySubscribe(self, topic, multiSub = False):
        if multiSub == False:
            self._paho_mqtt.subscribe(topic=topic, qos=self.QoS)
            if self.DEBUG:
                print("subscribed to topic: ", topic)
        else:
            self._paho_mqtt.subscribe(topic=topic)
        # multiple subscription can be made using a single command
        # e.g.subscribe(topic = [("my/topic", 0), ("another/topic", 2)]) note: qos field is not used
        # which is more efficient than using multiple calls

    def myUnsubscribe(self, topic):
        self._paho_mqtt.unsubscribe(topic) # note: it can unsubscribe from multiple topics at once(with list)
        # Returns a tuple(result, mid), where result is MQTT_ERR_SUCCESS to indicate success, or (MQTT_ERR_NO_CONN, None)
        # if the client is not currently connected.mid is the message ID for the unsubscribe request.
        # The mid value can be used to track the unsubscribe request by checking against the mid argument
        # in the on_unsubscribe() callback if it is defined.

    # CALLBACKS
    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print("Connected to %s with result code: %d" % (self.messageBroker, rc))

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        # CURRENTLY UNUSED, COULD BE USEFUL FOR HAVING AN ACKNOWDLEGDE
        # new message is received, msg is an instance of MQTTMessage, a class with members: topic, payload, qos, retain
        d = json.loads(msg.payload)
        # JSON string
        message = d['cmd']
        ID = d['ID']
        system = d['system']
        print(f'message received with payload: deviceID: {ID}, system: {system}, cmd: {message}')


# MQTT LISTENER FOR DEBUGGING
if __name__ == '__main__':
    broker = 'test.mosquitto.org'
    listener = MQTTClient('teSt1', broker, 'man')
    listener.brokerPort = 1883
    listener.start()
    listener.mySubscribe('device1/PlantCare/water')
    while 1:
        time.sleep(1)
    listener.stop()