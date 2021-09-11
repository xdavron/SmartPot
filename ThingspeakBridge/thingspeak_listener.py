import time
from datetime import datetime
from ThingspeakBridge.homeCatalogRequests import catalog
from ThingspeakBridge.MQTTPlantCare import MQTTClient
import requests
import json

# THINGSPEAK API KEYS
water_tank_key = "LU5HO62YMNQOCDPR"
temperature_key = "UVUAU9M94J097UDV"
soil_key = "HQDRA9E6L56RQ10P"
lighting_key = "T8JHGHHOYLMN90LY"
update_base_url = f"https://api.thingspeak.com/update.json"
# ----------------------------------------------------------

key_list = [water_tank_key, temperature_key, soil_key, lighting_key]
thingspeak_keys_dict = {"dhtTopic": temperature_key, "soilTopic": soil_key, "lightTopic": lighting_key,
                        "waterTopic": water_tank_key}


# class used to implement bridge between plant sensors and thingspeak channels
# it will listen for MQTT msgs sent by sensors of plantID and send them to the respective thingspeak channel
# through REST
class ThingspeakListener(MQTTClient):

    DEBUG = True

    def __init__(self, key_dict, plantid, catalog_ip, catalog_port):
        self.key_dict = key_dict
        # get catalog data
        self.Hcatalog = catalog(catalog_ip, catalog_port)
        self.Hcatalog.requestAll()
        # get sensor topics of plant ID
        self.plantID_topics = self.Hcatalog.topics[plantid]["topic"]
        # instantiate MQTT client
        MQTTClient.__init__(self, f"thingspeak_listener_{plantid}", self.Hcatalog.broker["ip"], int(self.Hcatalog.broker["port"]))

    def start_client(self):
        # start MQTT client and subscribe to sensor topics
        self.start()
        time.sleep(5)
        topic_list = [self.plantID_topics[sensor_name] for sensor_name in self.key_dict.keys()]
        for topic in topic_list:
            self.mySubscribe(topic)

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        topic = msg.topic
        for sensor_name in self.plantID_topics.keys():
                if self.plantID_topics[sensor_name] == topic:
                    try:
                        sensor_data = json.loads(msg.payload)
                        value = sensor_data["value"]
                        self.send_reading_to_thingspeak(value, sensor_name)
                        break
                    except:
                        print("received packet with bad format")

    def send_reading_to_thingspeak(self, value, sensor_name):
        base_url = "https://api.thingspeak.com/update.json"
        url = base_url+f"?api_key={self.key_dict[sensor_name]}&field1={value}"
        if self.DEBUG:
            print(f"sending GET {url}")
        response = requests.get(url)
        if self.DEBUG:
            print("received response: ", response.text)


if __name__ == "__main__":
    catalog_ip = "smart-pot-catalog.herokuapp.com"
    catalog_port = ""
    print("initializing listener...")
    listener = ThingspeakListener(thingspeak_keys_dict, "plant1", catalog_ip, catalog_port)
    print(listener.Hcatalog.broker)
    print("connecting to MQTT broker...")
    listener.start_client()
    while 1:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print("stopping listener")
            break
