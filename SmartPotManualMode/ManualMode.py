# program for publishing commands to plant care actor through MQTT

import cherrypy
import time
import json
import os

import cherrypy_cors
import paho.mqtt.client as PahoMQTT
from datetime import datetime
import requests

from MQTTPlantCare import MQTTClient
from homeCatalogRequests import catalog

DEBUG = True  # set to true for debug messages
Hcatalog = None  # global variable to instantiate as the catalog class


class ManualModeMQTTClient(MQTTClient):
    # lists of plantIDs for which we are waiting for an ACK
    nonACKedDevices = {"water": [], "light": []}
    global Hcatalog

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        # override method of the base class
        # new message is received, msg is an instance of MQTTMessage, a class with members: topic, payload, qos, retain
        # d = json.loads(msg.payload)  # TO-DO: manage content of ACK message
        topic_list = msg.topic.split('/')
        deviceID = topic_list[1]  # format example "dataCenter/plant1/lightControlTopic",
        sys = topic_list[2]
        # when ACK is received remove specified deviceID for non-ACKED list
        # if self.DEBUG:
        #     print(f"received msg with topic {msg.topic}, payload: {msg.payload}")
        #     print(topic_list)
        if sys == "lightControlTopic":
            if deviceID in self.nonACKedDevices["light"]:
                if self.DEBUG:
                    print(f"received light command ACK from {deviceID}, message body {msg.payload}")
                self.nonACKedDevices["light"].remove(deviceID)
        elif sys == "waterControlTopic":
            if deviceID in self.nonACKedDevices["water"]:
                if self.DEBUG:
                    print(f"received water command ACK from {deviceID}, message body {msg.payload}")
                self.nonACKedDevices["water"].remove(deviceID)

    def ManualModeCommand(self, topic, cmdStr, ID = None, selCmd = None):
        if ID is not None:  # ACK mode
            if selCmd in self.nonACKedDevices:
                if ID in self.nonACKedDevices[selCmd]:  # client hasnt received an ACK of a previously sent command of the same type
                    print(f"WARNING: did not receive ACK for previous {selCmd} command of {ID}")
                    self.publishCommand(topic, cmdStr)
                else:
                    self.publishCommand(topic, cmdStr)
                    self.nonACKedDevices[selCmd].append(ID)


class ManualModeREST(object):
    MQTTbroker = 'test.mosquitto.org'
    exposed = True
    MQTT = ManualModeMQTTClient('manualMode', MQTTbroker, -1)
    MQTT.DEBUG = True  # DEBUG MODE FOR MQTT CLIENT
    deviceStatus = {}  # dict which stores status of each device
    active = False
    plantCommands = {"water": "waterControl", "light": "lightControl"}
    plantGeneralTopicKeys = {"waterCmdACK": "waterControlTopic", "lightCmdAck": "lightControlTopic", "prefix": "",
                             "waterCmd": "waterTopic", "lightCmd": "lightTopic"}  # prefix field is currently unused
    initialized = False
    statusListRx = False  # flag that indicates if the status list of the plants has been received from the ModeManager actor

    def __init__(self):
        pass

    def subToPlantAcks(self, ID, unsub=False):
        global Hcatalog
        waterAck = Hcatalog.getPlantAckTopic(ID, "water")
        lightAck = Hcatalog.getPlantAckTopic(ID, "light")
        if not unsub:
            self.MQTT.mySubscribe(topic=lightAck)
            self.MQTT.mySubscribe(topic=waterAck)
        else:
            self.MQTT.myUnsubscribe([waterAck, lightAck])

    def sendPlantCmd(self, cmd, deviceID, inputDict):
        global Hcatalog

        if "action" in inputDict.keys() and "duration" in inputDict.keys():
            # TO-DO: add a check if system is waiting for an ACK from ID for this action
            if inputDict["action"] == "on":
                mode = 1
            elif inputDict["action"] == "off":
                mode = 0
            else:
                return False
            d = inputDict["duration"]
            if cmd == self.plantCommands["water"]:
                selCmd = "water"
                topic = Hcatalog.getPlantCmdTopic(deviceID, "water")
            else:
                # light
                selCmd = "light"
                topic = Hcatalog.getPlantCmdTopic(deviceID, "light")
            timeStr = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            JSONmsg = json.dumps({"mode": mode, "time": timeStr, "duration": d})
            print(JSONmsg)
            self.MQTT.ManualModeCommand(topic, JSONmsg, deviceID, selCmd)
            return True
        else:  # invalid cmd syntax
            return False

    def parsePlantCommand(self, cmd):
        pass

    @cherrypy.tools.accept(media='application/json')
    def GET(self, *uri):
        global Hcatalog

        if len(uri) >= 1:
            deviceID = uri[0]
            cmd = uri[1]
            if cmd == "status":  # status of manual mode for each plant ('on' or 'off)
                if deviceID == "all":
                    self.requestActiveIDs()
                    return json.dumps(
                        self.deviceStatus)  # json file of struct {"plant1":status, "plant2":status..} status is a str = "on" or "off"
                elif deviceID in self.deviceStatus:
                    return str(self.deviceStatus[deviceID])
                else:
                    raise cherrypy.HTTPError(404, "specified device not found")
            else:
                raise cherrypy.HTTPError(404, "invalid url")

    # used for sending commands to plant care actor
    def POST(self, *uri, **params):  # allowed cmd: waterPump, light, stop, block(blocks commands), unblock
        global Hcatalog
        global DEBUG
        # cmdString should be a JSON string containing the command for the pump or light
        if len(uri) != 0:
            deviceID = uri[0]
            cmd = uri[1]

            if deviceID == "system":  # system management
                if cmd == 'stop':  # stop the cherrypy service and MQTT client
                    if self.active:  # turn off if it was on
                        print('stopping service')  # stop cherrypy engine
                        self.active = False
                        self.MQTT.stop()
                        cherrypy.engine.exit()
                elif cmd == 'start':  # start the mqtt client service
                    outputDict = {}
                    if not self.active:
                        # update broker port and address
                        self.MQTT.messageBroker = Hcatalog.broker["ip"]
                        self.MQTT.brokerPort = int(Hcatalog.broker["port"])
                        self.MQTT.start()
                        self.active = True
                    if not self.initialized:  # generate status dictionary, initialize all status as 'off'
                        for ID in Hcatalog.getPlantIDs():  # create a status entry for each plant ID in home catalog
                            self.deviceStatus[ID] = "off"
                        self.initialized = True
                    if not self.statusListRx and self.initialized:
                        self.initialized = True  # request from ModeManager list of active modes for each id, update self.deviceStatus
                        self.statusListRx = self.requestActiveIDs()  # false if system was unable to request status list from mode manager
                    outputDict["ID status list received"] = self.statusListRx
                    outputDict["ID status list initialized"] = self.initialized
                    outputDict["MQTT client active"] = self.active
                    return json.dumps(outputDict)
                else:
                    raise cherrypy.HTTPError(404, "invalid command for /system")

            elif deviceID in self.deviceStatus or deviceID == "all":  # plant devices management
                if not self.active:
                    raise cherrypy.HTTPError(500, "MQTT client is not active")
                if not self.initialized:
                    raise cherrypy.HTTPError(500, "actor does not have plant ID list")
                if cmd == 'disable':
                    if deviceID == "all":  # block all plants in system
                        for ID in list(self.deviceStatus.keys()):
                            if self.deviceStatus[ID] == "on":
                                self.subToPlantAcks(ID, unsub=True)
                                self.deviceStatus[ID] = "off"
                    else:
                        if self.deviceStatus[deviceID] == 'on':
                            self.subToPlantAcks(deviceID, unsub=True)
                            self.deviceStatus[deviceID] = "off"
                elif cmd == 'enable':
                    if deviceID == "all":
                        for ID in list(self.deviceStatus.keys()):
                            if self.deviceStatus[ID] == "off":
                                self.subToPlantAcks(ID)
                                self.deviceStatus[ID] = "on"
                    else:
                        if self.deviceStatus[deviceID] == 'off':
                            self.subToPlantAcks(deviceID)
                            self.deviceStatus[deviceID] = "on"

                elif cmd in self.plantCommands.values():  # direct command to plant
                    if self.deviceStatus[deviceID] == "off":  # ERROR: Manual Mode not enabled for that ID
                        raise cherrypy.HTTPError(500, "Manual mode disabled for specified device")
                    inputJson = cherrypy.request.body.read()
                    try:
                        inputDict = json.loads(inputJson)
                        print(inputDict)
                    except:
                        print("can't decode string: ", inputJson)
                    if not self.sendPlantCmd(cmd, deviceID, inputDict):
                        raise cherrypy.HTTPError(500, "Error in message body syntax")
                    # plantID is inserted in list of devIDs awaiting ACKS
                    # callback of MQTT client will remove the ID if it receives an ACK
                else:
                    raise cherrypy.HTTPError(404, f"invalid command for /{deviceID}")
            else:
                raise cherrypy.HTTPError(404, "invalid url")

    def OPTIONS(self, *uri, **params):
        if cherrypy.request.method == 'OPTIONS':
            # This is a request that browser sends in CORS prior to
            # sending a real request.

            # Set up extra headers for a pre-flight OPTIONS request.
            cherrypy_cors.preflight(allowed_methods=['GET', 'POST'])

    def requestActiveIDs(self):
        global Hcatalog
        modeActive = False
        suffix = '/all/status'
        ip = Hcatalog.urls["ModeManager"]["ip"]
        print(ip)
        # port = Hcatalog.urls["ModeManager"]["port"]
        # url = 'http://' + ip + ':' + port + suffix
        url = 'http://' + ip + suffix
        try:
            response = requests.get(url)
            # print(response.content)
        except:
            print("request to ModeManager failed")
            return False
        modeDict = json.loads(response.content)
        try:
            for el in modeDict.items():
                ID = el[0]
                modeList = el[1]
                # print(modeList)
                if "manual" in modeList:
                    if not self.deviceStatus[ID] == "on":  # check if mode is not already enabled
                        self.deviceStatus[ID] = "on"
                        self.subToPlantAcks(ID)
                else:
                    if not self.deviceStatus[ID] == "off":  # check if mode is not already enabled
                        self.deviceStatus[ID] = "off"
            # request device modes from ModeManager and update self.deviceStatus
            # print(self.deviceStatus)
        except:
            return False
        return True


if __name__ == '__main__':
    # retrieve topic data from the home catalog
    # file = open("configFile.json", "r")
    # jsonString = file.read()
    # file.close()
    # data = json.loads(jsonString)
    # catalog_ip = data["resourceCatalog"]["ip"]
    # catalog_port = data["resourceCatalog"]["port"]
    # myIP = data["manualMode"]["ip"]
    # myPort = data["manualMode"]["port"]

    catalog_ip = "smart-pot-catalog.herokuapp.com"
    catalog_port = ""

    # myIP = "127.0.0.1"
    # myPort = "8080"
    myIP = "0.0.0.0"
    myPort = os.getenv('PORT')

    # instantiate catalog class and send requests to the home catalog actor
    Hcatalog = catalog(catalog_ip, catalog_port)  # global variable
    Hcatalog.requestAll()  # request all topics and urls
    # print("rx topics: ", Hcatalog.topics)
    # print("rx urls ", Hcatalog.urls)
    # print("rx broker info :", Hcatalog.broker)

    def CORS():
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tool.session.on': True,
            'tools.CORS.on': True,
            'tools.response_headers.on': True
        }
    }
    cherrypy.tree.mount(ManualModeREST(), '/', conf)
    cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS)
    cherrypy.config.update({"server.socket_host": str(myIP), "server.socket_port": int(myPort)})
    cherrypy.engine.start()
    cherrypy.engine.block()
