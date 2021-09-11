import json
import requests


# class to implement communication with the home catalog
# and store its information
class catalog:
    requestsFormat = {"urls request": "/urls", "topics request": "/topics",
                      "broker url request": "/broker", "all": "/all"}

    plantCommands = {"water": "waterControl", "light": "lightControl"}
    plantGeneralTopicKeys = {"waterCmdAck": "waterControlTopic", "lightCmdAck": "lightControlTopic", "prefix": "",
                          "waterCmd": "waterControlOrder", "lightCmd": "lightControlOrder"} # prefix field is currently unused

    def __init__(self, homeCatalogURL, homeCatalogPort, requestsFormat = None):
        if not homeCatalogURL.startswith("http://"):
            self.catalogURL = "http://"+homeCatalogURL#+':'+str(homeCatalogPort)
        else:
            self.catalogURL = homeCatalogURL#+':'+str(homeCatalogPort)
        self.topics = {}
        self.urls = {}
        self.broker = {}

    def requestURLS(self):
        r = requests.get(self.catalogURL+self.requestsFormat["urls request"])
        rawData = r.content
        self.urls = json.loads(rawData)

    def requestTopics(self):
        r = requests.get(self.catalogURL + self.requestsFormat["topics request"])
        rawData = r.content
        self.topics = json.loads(rawData)

    def requestBrokerInfo(self):
        r = requests.get(self.catalogURL + self.requestsFormat["topics request"])
        rawData = r.content
        self.broker = json.loads(rawData)

    def requestAll(self):  # get broker urls, topics and urls
        r = requests.get(self.catalogURL + self.requestsFormat["all"])
        if r.status_code != 200:  # expected status code
            raise ConnectionError("unexpected status code from home catalog")
        rawData = r.content
        jsonDict = json.loads(rawData.decode('utf-8'))
        try:
            self.urls = jsonDict["urls"]
        except:
            raise KeyError("data from home catalog has no 'urls' key")
        try:
            self.topics = jsonDict["topics"]
        except:
            raise KeyError("data from home catalog has no 'topics' key")
        try:
            self.broker = jsonDict["broker"]
        except:
            raise KeyError("data from home catalog has no 'broker' key")
        return True

    def getPlantIDs(self):  # return a list of all plant IDs
        return list(self.topics.keys())

   # return topic to send water command to specified ID, sys = water or light
    def getPlantCmdTopic(self, ID, sys):
        if sys == "water":
            return self.topics[ID]["topic"][self.plantGeneralTopicKeys["waterCmd"]]
        elif sys == "light":
            return self.topics[ID]["topic"][self.plantGeneralTopicKeys["lightCmd"]]
        else:
            raise ValueError("sys must be 'light' or 'water'")

    def getPlantAckTopic(self, ID, sys):
        if sys == "water":
            try:
                return self.topics[ID]["topic"][self.plantGeneralTopicKeys["waterCmdAck"]]
            except:
                print(self.topics[ID])
        elif sys == "light":
            return self.topics[ID]["topic"][self.plantGeneralTopicKeys["lightCmdAck"]]
        else:
            raise ValueError("sys must be 'light' or 'water'")

