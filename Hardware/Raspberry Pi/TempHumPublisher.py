from TempandHumidity import DHT11_Reader
import paho.mqtt.client as mqttc
import time
import datetime
import requests
import json


class PublishData(object):

    def __init__(self, url, sensor_t_h, plantIdUrl, plantId, client):
        self.url = url
        self.sensor_t_h = sensor_t_h
        self.client = client
        self.plantIdUrl=plantIdUrl
        self.plantId=plantId
        self.DHT_Topic=""

    def load_topics(self):
        # sending request to the resource catalog to get the topics related to the plant id
        try:
            self.respond = requests.get(self.url)
            json_format = json.loads(self.respond.text)
            self.DHT_Topic = json_format[self.plantId]["topic"]["dhtTopic"]
            print("PublishData:: BROKER VARIABLES ARE READY")
        except:
            print("PublishData: ERROR IN CONNECTING TO THE SERVER FOR READING BROKER TOPICS")

    @staticmethod
    def on_connect(client, userdata, flags, rc):
        # get the current time
        get_time = datetime.datetime.now()
        current_time = get_time.strftime("%Y-%m-%d %H:%M:%S")
        print ('CONN ACK received with code: ' + str(rc))
        print ("at time: " + str(current_time))
        return str(rc)

    @classmethod
    def on_publish(cls, client, userdata, mid):
        # get the current time
        get_time = datetime.datetime.now()
        current_time =  get_time.strftime("%Y-%m-%d %H:%M:%S")
        print("mid: " + str(mid))
        print ("at time: " + str(current_time))
        print("--------------------------------------------------------------------")
        return str(mid)

    def publish_sensor_data(self):
        #This function will publish the data related to temperature and humidity
        try:
            json_format = self.sensor_t_h.sensorData()
            temp_hum_data = json.loads(json_format)
            temp = temp_hum_data["temperature"]
            hum = temp_hum_data["humidity"]
            time = temp_hum_data["time"]
            new_json_format=json.dumps({"subject":"temp_hum_data","plantId":self.plantId,"value": temp, "humidity": hum,"time":time})
            msg_info = client.publish(self.DHT_Topic, str(new_json_format), qos=1)
            if msg_info.is_published() == True:
                print ("\nMessage is published.")
            # This call will block until the message is published
            msg_info.wait_for_publish()
            return ("HELLO", json_format)
        except:
            get_time = datetime.datetime.now()
            current_time = get_time.strftime("%Y-%m-%d %H:%M:%S")
            print("PublishData: ERROR IN PUBLISHING DATA RELATED TO THE SENSORS")
            print ("at time: " + str(current_time))


if __name__ == '__main__':

    try:
        # reading the config file to set the resource catalog url and the room id
        file = open("config_file.json", "r")
        json_string = file.read()
        file.close()
    except:
        raise KeyError("***** PublishData: ERROR IN READING CONFIG FILE *****")

    config_json = json.loads(json_string)
    resourceCatalogIP = config_json["reSourceCatalog"]["url"]
    plantIdUrl = config_json["reSourceCatalog"]["plantIdUrl"]
    plantId = config_json["reSourceCatalog"]["plantId"]
    url = resourceCatalogIP + plantIdUrl
    
    try:
        # create an object from ReadingDHT class
        sensor_data = DHT11_Reader()
    except:
        print("PublishData: ERROR IN GETTING DATA FROM SENSOR ")

    client = mqttc.Client()
    sens = PublishData(url, sensor_data, plantIdUrl, plantId, client)

    while True:
        try:
            #requesting the vroker info from resource catalog
            respond = requests.get(resourceCatalogIP+"/broker")
            json_format = json.loads(respond.text)
            broker_ip = json_format["ip"]
            port = json_format["port"]
        except:
            print("PublishData: ERROR IN CONNECTING TO THE SERVER FOR READING BROKER IP")

        try:
            client.on_connect = PublishData.on_connect
            client.on_publish = PublishData.on_publish
            client.connect(broker_ip, int(port))
            client.loop_start()
        except:
            print("PublishData: ERROR IN CONNECTING TO THE BROKER")

        while True:
            sens.load_topics()
            sens.publish_sensor_data()
            time.sleep(30)
