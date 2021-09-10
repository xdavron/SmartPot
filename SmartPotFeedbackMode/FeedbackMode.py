
# FEEDBACK MODE DESCRIPTION
# WATERING
# the program tries to keep a moisture level(user given) more or less constant (water only when below it),
# optimal moisture level will be adjusted according to temperature and humidity data

# LIGHTING
# the program tries to have the plant receive the optimal amount of light time, if by nighttime that amount hasn't
# been reached, it will turn on the LED strip and illuminate the plant until the optimal time is reached
# everytime a data packet is received, the daylight time counter is increased if the light data is above a threshold

# this actor functions through the callbacks of the MQTT client triggered when sensor data is received

import cherrypy
import time
import json
import os
import paho.mqtt.client as PahoMQTT
from datetime import datetime
import SmartPotFeedbackMode.MQTTPlantCare
import threading
import schedule
from SmartPotFeedbackMode.MQTTPlantCare import MQTTClient
from SmartPotFeedbackMode.homeCatalogRequests import catalog
import requests

# GLOBAL VARIABLES
deviceParameters = {}  # global variable containing the feedback mode parameters for each plant ID
# format: plantID : {"light_time": k, "hum_thresh": n, "illum_thresh": m, "last_hum_update": t};

# k integer time in seconds, n,m val between 0-100, t are datetime objects (timestamp of last rx update)
deviceLightCounter = {}  # global variable counting minutes of illumination for each deviceID
deviceStatus = {}  # dictionary containing the feedback mode status for each plant ID
# nighttime, time after which the led can be turned on to supplement lighting time
# TODO: allow user to set the night time or retrieve it from internet
nightTime_h = 18
nightTime_m = 0
default_illum_thresh_g = 70
default_hum_thresh_g = 500
default_light_time_g = 8*6000


class FeedbackModeMQTTClient(MQTTClient):
    global Hcatalog
    global default_illum_thresh_g

    lightSensorInterval = 30
    default_illum_thresh = default_illum_thresh_g  # default illumination threhsold

    # subscribe to the topics of soil and light sensors of deviceID
    def subToSensorData(self, deviceID):
        global Hcatalog
        try:
            soil_topic = Hcatalog.topics[deviceID]["topic"]["soilTopic"]
            light_topic = Hcatalog.topics[deviceID]["topic"]["lightTopic"]
            self.mySubscribe(soil_topic)
            self.mySubscribe(light_topic)
        except:
            print(f"Warning: could not find topics for device: {deviceID}")
    # overwrites callback in original function
    # each time soil sensor reading is received, check if the value is within the threshold
    # if it isn't send command to water

    # each time lighting sensor reading is received, check if value is over illumination threshold, if it is then the
    # plant is considered illuminated so increase the light counter
    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        global nightTime_m
        global nightTime_h
        topic = msg.topic
        deviceID, sensor_type = self.getIDfromTopic(topic)
        if deviceID not in deviceStatus:
            return
        if sensor_type == "soilTopic":
            if deviceStatus[deviceID] is "on":  # humidity check only if fb mode is active
                sensor_data = json.loads(msg.payload)
                if self.humidityCheck(deviceID, sensor_data):  # check if action is necessary
                    cmd_topic = Hcatalog.getPlantCmdTopic(deviceID, "water")
                    cmd_payload = {"mode": 1, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "duration": 1000}
                    self.publishCommand(cmd_topic, json.dumps(cmd_payload))  # water the plant
        elif sensor_type == "lightTopic" and datetime.now() < datetime.now().replace(hour=nightTime_h, minute=nightTime_m):
            # if current time is after set night time it ignores light data
            # light counter updated also if fb mode is inactive
            sensor_data = json.loads(msg.payload)
            # check if illumination is above threshold and update light counter accordingly
            if self.illuminationCheck(deviceID, sensor_data):
                self.lightCounterUpdate(deviceID)

    def getIDfromTopic(self, input_topic):
        global Hcatalog
        for deviceID, devID_data in Hcatalog.topics.items():
            for topic_n, topic_v in devID_data["topic"]:
                if topic_v == input_topic:
                    return deviceID, topic_n

    def humidityCheck(self, devID, sensorData):
        global deviceParameters
        global Hcatalog
        if deviceParameters[devID]["hum_thresh"] != -1:  # humidity control is active
            try:
                # sensorData format: {“value”:..,"time":”2020-08-10 15:17:28”}
                sensorData_dict = json.loads(sensorData)
                new_t = datetime.strptime(sensorData_dict["time"], "%Y-%m-%d %H:%M:%S")
                if "last_hum_update" not in deviceParameters[devID]:
                    deviceParameters[devID]["last_hum_update"] = new_t
                    if sensorData["value"] < deviceParameters[devID]["hum_thresh"]:  # compare sensor data with threshold
                        return True
                    return False
                else:
                    if new_t > deviceParameters[devID]["last_hum_update"]:
                        # update timestamp
                        deviceParameters[devID]["last_hum_update"] = new_t
                        if sensorData["value"] < deviceParameters[devID]["hum_thresh"]:  # compare sensor data with threshold
                            return True
                    return False
            except:
                print(f"WARNING: Could not parse sensor data of device {devID}, received payload str: ", sensorData)
                return False
        else:
            return False

    def illuminationCheck(self, devID, sensorData):
        global deviceLightCounter
        global deviceParameters
        try:
            # sensorData format: {“value”:..,"time":”2020-08-10 15:17:28”}
            sensorData_dict = json.loads(sensorData)
            new_t = datetime.strptime(sensorData_dict["time"], "%Y-%m-%d %H:%M:%S")
            # we check all received data, and assume a constant sensor tx interval so that each sensor reading add
            # a fixed amount of light time
            if devID in deviceParameters:
                if sensorData["value"] < deviceParameters[devID]["illum_thresh"]:  # compare sensor data with devID threshold
                    return True
            else:
                if sensorData["value"] < self.default_illum_thresh:  # compare sensor data with default threshold
                    return True
            return False
        except:
            print(f"WARNING: Could not parse sensor data of device {devID}, received payload str: ", sensorData)
            return False

    def lightCounterUpdate(self, devID):
        global deviceParameters
        global deviceLightCounter
        deviceLightCounter[devID] += self.lightSensorInterval  # this is doable if sensor transmit at intervals

    def giveLightCmd(self, devID, duration):
        global Hcatalog
        # duration is an int specifying illumination duration in seconds
        cmd_topic = Hcatalog.getPlantCmdTopic(devID, "light")
        duration_ms = duration*1000
        cmd_payload = {"mode": 1, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "duration": duration_ms}
        self.publishCommand(cmd_topic, json.dumps(cmd_payload))

    def turnOffLight(self, devID):
        global Hcatalog
        # duration is an int specifying illumination duration in seconds
        cmd_topic = Hcatalog.getPlantCmdTopic(devID, "light")
        cmd_payload = {"mode": 0, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "duration": -1}
        self.publishCommand(cmd_topic, json.dumps(cmd_payload))

    def removePlantIDParams(self, devID):
        global deviceParameters
        global deviceLightCounter
        if devID in deviceParameters:
            deviceParameters.pop(devID)
        if devID in deviceLightCounter:
            deviceLightCounter.pop(devID)


class LightSupplement(threading.Thread):
    # THIS THREAD IMPLEMENTS A SCHEDULE THAT RESET LIGHTCOUNTERS AT THE NIGHT HOUR
    # AND SEND COMMAND FOR TURNING ON LIGHT SUPPLEMENT

    global Hcatalog
    global ScheduleDict  # contains ALL jobs scheduled for the current day, format {"plantID1":jobs,"plantID2":jobs}
    # jobs = {"water":{"t1":dur, "t2":dur}, "light":{"t1":dur, "t2"dur}}
    toSet = False  # flag that means the schedule has to be set
    # to start scheduling
    threadStop = False
    DEBUG = True  # set true for debug messages
    MQTT = None

    def __init__(self, MQTT):
        # MQTT must be the FeedbackModeMQTTClient class instance used in the system
        self.MQTT = MQTT
        threading.Thread.__init__(self)
        # instance an MQTT client class and start it
        # get current date
        today = datetime.today()
        self.currMonth = today.month
        self.currDay = today.day

    # method called every day at nightTime, or when a deviceID has fb mode activated after nightTime
    # if allIDs is True then supplement will be given to all deviceID with fb mode active
    def giveLightSupplement(self, devID=None, allIDs=False):
        global deviceStatus
        global deviceParameters
        global deviceLightCounter
        if allIDs:
            for ID in deviceStatus:
                if deviceStatus[ID] == "on":
                    if deviceParameters[ID]["light_time"] != -1:  # light control is enabled
                        diff = deviceLightCounter[ID] - deviceParameters[ID]["light_time"]
                        # "light_time": k, "hum_thresh": n, "illum_thresh": m, "last_hum_update": t
                        if diff > 0:
                            self.MQTT.giveLightCmd(ID, diff)
        else:
            if devID is None:
                return
            if deviceStatus[devID] == "on":
                diff = deviceLightCounter[devID] - deviceParameters[devID]["light_time"]
                # "light_time": k, "hum_thresh": n, "illum_thresh": m, "last_hum_update": t
                if diff > 0:
                    self.MQTT.giveLightCmd(devID, diff)

    def lightSupplementCheck(self):
        global deviceLightCounter
        self.giveLightSupplement(allIDs=True)  # give the light supplement for the day
        for ID in deviceLightCounter:
            deviceLightCounter[ID] = 0

    def setSchedule(self):
        global nightTime_h
        global nightTime_m
        # at the end of the day(00:00) it will clear all jobs and reschedule
        check_time = str(nightTime_h)+':'+str(nightTime_m)
        schedule.every().day.at(check_time+':30').do(self.lightSupplementCheck)
        schedule.every().day.at('23:59:59').do(self.reset)
        self.toSet = False

    def reset(self):
        # REMOVE ALL JOBS
        schedule.clear()
        self.toSet = True
        # RESET LIGHT COUNTERS
        self.resetLightCounter()

    def resetLightCounter(self):
        global deviceLightCounter
        for ID in deviceLightCounter:
            deviceLightCounter[ID] = 0

    def run(self):
        while not self.threadStop:
            if self.toSet:
                self.setSchedule()
            schedule.run_pending()
            time.sleep(1)
        print("Thread loop ended...")

    def stop(self):
        self.threadStop = True
        # close the MQTT client and clear schedule
        schedule.clear()


class FeedbackModeREST(object):
    global deviceParameters  # dictionary containing feedback mode parameters for all devices
    global deviceLightCounter # minutes of illumination of each plant (counter is updated for all deviceIDs, even if fb mode is inactive)
    # PARAMETERS TO GET FROM MODE MANAGERS
    illumination_threshold = -1  # between 0 and 100, the min light sensor reading at which the plat is considered under
    # light
    MQTTbroker = 'test.mosquitto.org'
    exposed = True
    deviceID = 'device1'  # retrieved from home catalog
    active = False
    initialized = False
    global deviceStatus  # dictionary containing the feedback mode status for each plant ID
    MQTT = None

    def subToPlantAcks(self, ID, unsub=False):
        global Hcatalog
        waterAck = Hcatalog.getPlantAckTopic(ID, "water")
        lightAck = Hcatalog.getPlantAckTopic(ID, "light")
        if not unsub:
            self.MQTT.mySubscribe(topic=lightAck)
            self.MQTT.mySubscribe(topic=waterAck)
        else:
            self.MQTT.myUnsubscribe([waterAck, lightAck])

    def requestActiveIDs(self):
        global Hcatalog
        global deviceStatus
        global deviceParameters
        global default_illum_thresh_g
        global default_hum_thresh_g
        global default_light_time_g
        modeActive = False
        suffix = '/all/status'
        ip = Hcatalog.urls["ModeManager"]["ip"]
        url = 'http://'+ip+suffix
        response = requests.get(url)
        modeDict = json.loads(response.content)
        for el in modeDict.items():
            id = el[0]
            modeList = el[1]
            if "feedback" in modeList:
                deviceStatus[id] = "on"
                deviceParameters = {"light_time": default_light_time_g, "hum_thresh": default_hum_thresh_g,
                                    "illum_thresh": default_illum_thresh_g}
                modeActive = True
        # request device modes from ModeManager and update self.deviceStatus
        return modeActive  # true if at least 1 id has auto mode enabled


    @cherrypy.tools.accept(media='application/json')
    def GET(self, *uri):
        global deviceParameters
        global deviceLightCounter
        global deviceStatus

        # placeholder for possible status variable
        if len(uri) > 1:
            if not self.initialized:
                raise cherrypy.HTTPError(500, "device list not initialized")
            if uri[0] == "update":
                Hcatalog.requestAll()
                keys = deviceStatus.copy()
                for plantID in keys.keys():
                    if plantID not in Hcatalog.getPlantIDs():
                        if deviceStatus[plantID] == "on":
                            self.MQTT.turnOffLight(plantID)
                            self.subToPlantAcks(plantID, unsub=True)  # unsubscribe from topics
                            # remove schedule
                        self.MQTT.removePlantIDParams(plantID)
                        deviceStatus.pop(plantID)
                for ID in Hcatalog.getPlantIDs():  # create a status entry for each new plant ID in home catalog
                    if ID not in self.deviceStatus.keys():
                        self.deviceStatus[ID] = "off"
            deviceID = uri[0]
            cmd = uri[1]
            if deviceID != "all" and deviceID not in deviceStatus:
                raise cherrypy.HTTPError(404, "specified device not found")
            # returns "on" or "off" depending whether the plantID has auto mode currently active or not
            # if deviceID is "all" then a dict with structure {plantID: mode} is returned (mode is "on" or "off")
            if cmd == "status":
                if deviceID in deviceStatus:
                    return str(deviceStatus[deviceID])
                elif deviceID == "all":
                    return json.dumps(deviceStatus)
            if cmd == "thresholds":
                if deviceID in deviceParameters:
                    devID_params = deviceParameters[deviceID].copy()
                    devID_params.pop("last_hum_update", None)
                    return json.dumps(devID_params)
                else:
                    cherrypy.HTTPError(404, "thresholds params for this ID not found")
            else:
                cherrypy.HTTPError(404, "invalid url")

    # used for sending commands to plant care actor
    @cherrypy.tools.accept(media='application/json')
    def POST(self, *uri, **params):
        global stop
        global deviceID
        global deviceStatus
        global deviceLightCounter
        if len(uri) > 0:
            deviceID = uri[0]  # ID of the device to which the PlantCare commands will be sent
            print("devID: ", deviceID)
            cmd = str(uri[1])
            if deviceID == "system":
                if cmd == 'stop':
                    # turns off feedback mode and the REST API service
                    # stop thread if it was active
                    if self.active:
                        print('Stopping MQTT client...')
                        self.MQTT.stop()
                        print('MQTT client stopped')
                        print("Stopping schedule thread...")
                        self.scheduleThread.stop()
                        self.scheduleThread.join()
                        print("Schedule thread stopped")

                    # close REST API service
                    print('Stopping API service...')
                    cherrypy.engine.exit()
                elif cmd == 'start':
                    outputDict = {}
                    if not self.active:
                        print('starting the MQTT client...')
                        self.MQTT = FeedbackModeMQTTClient("FeedbackModeClient", Hcatalog.broker["ip"], int(Hcatalog.broker["port"]))
                        self.MQTT.start()
                        print('scheduler MQTT client started')
                        self.active = True
                    if not self.initialized:
                        print("Initializing sensor listener...")
                        for ID in Hcatalog.getPlantIDs():  # create a status entry for each plant ID in home catalog
                            deviceStatus[ID] = "off"  # initialize all as inactive
                            deviceLightCounter[ID] = 0  # set all counters to 0 (TO-DO: store light counters in modeManager)
                            print("Subscribing to sensor data of device: ", ID)
                            self.MQTT.subToSensorData(ID)  # sub to device data and start monitoring illumination
                        self.requestActiveIDs()
                        print("Initializing thread for regulating Light Supplement...")
                        self.scheduleThread = LightSupplement(self.MQTT)
                        self.scheduleThread.start()
                        self.initialized = True
                    # plantIDs are initialized with the default parameters inside catalog
                    outputDict["ID status list initialized"] = self.initialized
                    outputDict["MQTT client"] = self.active
                    print("...System Initialized")
                    return json.dumps(outputDict)

            elif deviceID in deviceStatus:
                if cmd == "enable":
                    # requires a msg body containing device parameters
                    if deviceStatus[deviceID] is "on":
                        raise cherrypy.HTTPError(500, "feedback mode already active for that device")
                    deviceStatus[deviceID] = "on"
                    jsonPayload = cherrypy.request.body.read().decode('utf8')
                    deviceParams = json.loads(jsonPayload)
                    if "light_time" in deviceParams and "hum_thresh" in deviceParams and "illum_thresh" in deviceParams:
                        deviceParameters[deviceID] = deviceParams
                        deviceParams["last_hum_update"] = datetime.now().replace(hour=0, minute=0)
                    else:
                        raise cherrypy.HTTPError(500, "msg body format is incorrect")
                    if deviceID not in deviceLightCounter:
                        deviceLightCounter[deviceID] = 0
                    # {"light_time": k, "hum_thresh": n, "illum_thresh": m, "last_hum_update": t};1
                    if deviceParams["light_time"] != -1:  # light control is enabled
                        if datetime.now() > datetime.now().replace(hour=nightTime_h, minute=nightTime_m):
                            # check if night time has passed, if it has make the illum time check
                            self.scheduleThread.giveLightSupplement(deviceID)
                if cmd == "disable":
                    if deviceStatus[deviceID] is "off":
                        raise cherrypy.HTTPError(500, "feedback mode already off for that device")
                    deviceStatus[deviceID] = "off"
                    if datetime.now() > datetime.now().replace(hour=nightTime_h, minute=nightTime_m):
                        self.MQTT.turnOffLight(deviceID)
                if cmd == 'paramChange':
                    jsonPayload = cherrypy.request.body.read().decode('utf8')
                    deviceParams = json.loads(jsonPayload)
                    if "light_time" in deviceParams and "hum_thresh" in deviceParams and "illum_thresh" in deviceParams:
                        if deviceID not in deviceParameters:
                            deviceParameters[deviceID] = deviceParams
                            deviceParams["last_hum_update"] = datetime.now().replace(hour=0, minute=0)
                        else:
                            deviceParameters[deviceID]["light_time"] = deviceParams["light_time"]
                            deviceParameters[deviceID]["hum_thresh"] = deviceParams["hum_thresh"]
                            deviceParameters[deviceID]["illum_thresh"] = deviceParams["illum_thresh"]
            else:
                raise cherrypy.HTTPError(500, "unrecognized deviceID")


if __name__ == '__main__':
    def CORS():
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
    # retrieve topic data from the home catalog
    # file = open("configFile.json", "r")
    # jsonString = file.read()
    # file.close()
    # data = json.loads(jsonString)
    catalog_ip = "smart-pot-catalog.herokuapp.com"
    catalog_port = ""
    myIP = '0.0.0.0'
    myPort = os.getenv('PORT')
    # instantiate catalog class and send requests to the home catalog actor
    Hcatalog = catalog(catalog_ip, catalog_port)  # global variable
    Hcatalog.requestAll()  # request all topics and urls
    # print("Loaded topic data:", Hcatalog.topics)
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tool.session.on': True,
            'tools.CORS.on': True,
            'tools.response_headers.on': True
        }
    }
    cherrypy.tree.mount(FeedbackModeREST(), '/', conf)
    cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS)
    cherrypy.config.update({"server.socket_host": str(myIP), "server.socket_port": int(myPort)})
    cherrypy.engine.start()
    cherrypy.engine.block()

