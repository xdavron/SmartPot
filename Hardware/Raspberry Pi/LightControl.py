import paho.mqtt.client as PahoMQTT
import RPi.GPIO as GPIO
import time
import datetime
import requests
import json
from threading import Timer


class MySubscriber:
    def __init__(self, clientID, broker,port, plantId, plantIdUrl, url):
        self.clientID = clientID
        # create an instance of paho.mqtt.client
        self._paho_mqtt = PahoMQTT.Client(clientID, False)

        # register the callback
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived
        self.currentMode="0"
        self.url = url
        self.messageBroker = broker
        self.port = port
        self.plantId= plantId
        self.plantIdUrl= plantIdUrl
        self.LightControl_Topic=""
        self.LightControlPub_Topic=""

    def load_topics(self):
            # sending request to the resource catalog to get the topics related to the room id
        try:
            self.respond = requests.get(self.url)
            json_format = json.loads(self.respond.text)
            self.LightControl_Topic = json_format[self.plantId]["topic"]["lightControlOrder"]
            print("PublishData:: BROKER VARIABLES ARE READY")
        except:
            print("PublishData: ERROR IN CONNECTING TO THE SERVER FOR READING BROKER TOPICS")
    
    def load_publish_topics(self):
            # sending request to the resource catalog to get the topics related to the room id
        try:
            self.respond = requests.get(self.url)
            json_format = json.loads(self.respond.text)
            self.LightControlPub_Topic = json_format[self.plantId]["topic"]["lightControlTopic"]
            print("PublishData:: BROKER VARIABLES ARE READY")
        except:
            print("PublishData: ERROR IN CONNECTING TO THE SERVER FOR READING BROKER TOPICS")


    def start(self):
        # manage connection to broker
        self._paho_mqtt.connect(self.messageBroker, self.port)
        self._paho_mqtt.loop_start()
        # subscribe for a topic
        self._paho_mqtt.subscribe(self.LightControl_Topic, 2)

    def stop(self):
        self._paho_mqtt.unsubscribe(self.LightControl_Topic)
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print("Connected to %s with result code: %d" % (self.messageBroker, rc))

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        # A new message is received
        #print("Topic:'" + msg.topic + "', QoS: '" + str(msg.qos) + "' Message: '" + str(msg.payload) + "'")
        message = msg.payload.decode("utf-8","ignore")
        water_contol_data = json.loads(message)
        # {'mode': 0 or 1, 'time': '2021-03-21 22:12:18', 'duration': 2000}
        mode, duration = water_contol_data["mode"], water_contol_data["duration"]
        if self.currentMode != mode:
            if duration == -1:
                self.currentMode = mode
                GPIO.output(20,mode)
                print(mode)
            else:
                self.currentMode = mode
                GPIO.output(20,mode)
                time.sleep(duration)                
                self.currentMode = 0
                GPIO.output(20,0)
       

if __name__ == "__main__":
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(20,GPIO.OUT)
    GPIO.output(20,0)
    
    try:
        # reading the config file to set the resource catalog url and the room id
        file = open("config_file.json", "r")
        json_string = file.read()
        file.close()
    except:
        raise KeyError("***** PubSubData: ERROR IN READING CONFIG FILE *****")

    config_json = json.loads(json_string)
    resourceCatalogIP = config_json["reSourceCatalog"]["url"]
    plantIdUrl = config_json["reSourceCatalog"]["plantIdUrl"]
    plantId = config_json["reSourceCatalog"]["plantId"]
    url = resourceCatalogIP + plantIdUrl

    try:
        # requesting the vroker info from resource catalog
        respond = requests.get(resourceCatalogIP + "/broker")
        json_format = json.loads(respond.text)
        broker_ip = json_format["ip"]
        port = json_format["port"]
    except:
        print("PubSubData: ERROR IN CONNECTING TO THE SERVER FOR READING BROKER IP")

    test = MySubscriber("LightPubSub", broker_ip, int(port), plantId, plantIdUrl, url)  # "IoT/#"
    test.load_topics()
    test.load_publish_topics()
    test.start()

    while True:
        time.sleep(1)

