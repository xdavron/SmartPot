# program for publishing commands to plant care actor through MQTT following a preset schedule

import cherrypy
import time
import json
import cherrypy_cors
import paho.mqtt.client as PahoMQTT
from datetime import datetime
from MQTTPlantCare import MQTTClient
from homeCatalogRequests import catalog
import threading
import schedule
import os
import requests

stop = 0
Hcatalog = {}
ScheduleDict = {}  # structure: {"plant1": schedule, "plant2: schedule}
# schedule structure: {“water”: {“time1”:duration, “time2”:duration}, “light”: {“time1”:duration, “time2”:duration}}

# this actor employs a thread which executes scheduled actions to send commands to the plants, scheduled actions are
# updated at the start of each day, when the mode is activated for a new plantID, when a plantID schedule is changed


class AutoModeMQTTClient(MQTTClient):
    global Hcatalog
    # MAYBE ADD SOME CALLBACKS WHEN RECEIVING ACKS


# class that implements the thread for the job scheduler
class JobSchedulerThread(threading.Thread):

    global Hcatalog
    global ScheduleDict  # contains ALL jobs scheduled for the current day, format {"plantID1":jobs,"plantID2":jobs}
    # jobs = {"water":{"t1":dur, "t2":dur}, "light":{"t1":dur, "t2"dur}}
    toSet = False  # flag that means the daily schedule has to be set, initialized as false, must be set to true after initialization
    # to start scheduling
    threadStop = False
    DEBUG = True  # set true for debug messages
    MQTT = None

    def __init__(self):
        threading.Thread.__init__(self)
        # instance an MQTT client class and start it
        # get current date
        today = datetime.today()
        self.currMonth = today.month
        self.currDay = today.day

    def getSchedule(self):
        # returns the daily preset that is currently being followed
        return ScheduleDict

    # send a GET to mode manager for a schedule for each activated plantID
    # this method should be called at the start of each day
    def requestDailySchedule(self):
        global ScheduleDict
        global Hcatalog
        ip = Hcatalog.urls["ModeManager"]["ip"]
        port = Hcatalog.urls["ModeManager"]["port"]
        suffix = "/all/auto/schedule/daily/?onlyActives=True"
        url = "http://"+ip+suffix
        response = requests.get(url)
        ScheduleDict = json.loads(response.content.decode('utf-8'))

    def setDailySchedule(self):
        self.requestDailySchedule()  # updates ScheduleDict global variable
        # set a daily schedule using the module schedules
        today = datetime.today()
        # update current date
        self.currDay = today.day
        self.currMonth = today.month

        for scheduledJobs in list(ScheduleDict.items()):
            plantID = scheduledJobs[0]
            sched = scheduledJobs[1]
            self.schedulePlantJobs(plantID, sched)

        # at the end of the day(00:00) it will clear all jobs and reschedule
        schedule.every().day.at('00:00:00').do(self.resetSchedule)
        self.toSet = False

    def schedulePlantJobs(self, plantID, scheduledJobs):
        # schedules jobs in schedule tagging them with plantID
        # schedule is a dictionary with format {“water”: {“time1”:duration, “time2”:duration}, “light”: {“time1”:duration, “time2”:duration}}
        waterJobs = {}
        lightJobs = {}
        if "water" in scheduledJobs.keys():
            waterJobs = scheduledJobs["water"]
        if "light" in scheduledJobs.keys():
            lightJobs = scheduledJobs["light"]
        if len(waterJobs) != 0:
            for jobParams in list(waterJobs.items()):
                paramDict = {"type": "water", "duration": jobParams[1], "deviceID": plantID}
                time = jobParams[0]
                if self.DEBUG:
                    print(f"scheduling job at {time}, params:{paramDict}")
                schedule.every().day.at(time).do(self.PlantCareJob, paramDict).tag(plantID)
        if len(lightJobs) != 0:
            for jobParams in list(lightJobs.items()):
                paramDict = {"type": "light", "duration": jobParams[1], "deviceID": plantID}
                time = jobParams[0]
                if self.DEBUG:
                    print(f"scheduling job at {time}, params:{paramDict}")
                schedule.every().day.at(time).do(self.PlantCareJob, paramDict).tag(plantID)

    def removeScheduledJobs(self, plantID):
        # REMOVE ALL JOBS WITH TAG plantID
        if self.DEBUG:
            print("clearing jobs with ID:", plantID)
        schedule.clear(plantID)

    def resetSchedule(self):
        # REMOVE ALL JOBS
        schedule.clear()
        self.toSet = True

    def run(self):
        while not self.threadStop:
            if self.toSet:
                self.setDailySchedule()
            schedule.run_pending()
            time.sleep(1)
        print("Thread loop ended...")

    # jobs performed by the scheduler
    def PlantCareJob(self, parameters):
        # check format
        if not("type" in parameters.keys() and "duration" in parameters.keys() and "deviceID" in parameters.keys()):
            print("Job with bad parameters")
            return
        deviceID = parameters['deviceID']
        jobType = parameters['type']
        duration = parameters['duration']
        timeStr = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cmdDict = {"mode": jobType, "time": timeStr, "duration": duration}
        cmdJSON = json.loads(cmdDict)
        # get topic
        topic = Hcatalog.getPlantCmdTopic(deviceID, jobType)
        self.MQTT.publishCommand(topic, cmdJSON)

    def stop(self):
        self.threadStop = True
        # close the MQTT client and clear schedule
        schedule.clear()
        self.MQTT.stop()


# class that implements the REST APIs to access to actor
# scheduling of actions is implemented though the JobSchedulerThread class, a single thread manages schedule for all
# plants, scheduled jobs belonging to a plant schedule have as tag the plant ID, when a plant switches out of auto mode,
# jobs with its tag are removed from the scheduler
class AutomaticModeREST(object):
    exposed = True
    MQTTbroker = 'test.mosquitto.org'  # MQTT client instance is handled by the job thread
#    MQTT = AutoModeMQTTClient('test', MQTTbroker, 'auto')
    # schedulerThread = None
    active = False
    initialized = False
    deviceStatus = {}
    schedulerThread = JobSchedulerThread()

    def subToPlantAcks(self, ID, unsub = False):
        global Hcatalog
        waterAck = Hcatalog.getPlantAckTopic(ID, "water")
        lightAck = Hcatalog.getPlantAckTopic(ID, "light")
        if not unsub:
            self.schedulerThread.MQTT.mySubscribe(topic=lightAck)
            self.schedulerThread.MQTT.mySubscribe(topic=waterAck)
        else:
            self.schedulerThread.MQTT.myUnsubscribe([waterAck, lightAck])

    @cherrypy.tools.accept(media='application/json')
    def GET(self, *uri):
        global Hcatalog
        global ScheduleDict

        if len(uri) != 0:
            deviceID = uri[0]
            cmd = uri[1]
            if not self.initialized:
                raise cherrypy.HTTPError(500, "device list not initialized")
            if deviceID != "all" and deviceID not in self.deviceStatus:
                raise cherrypy.HTTPError(404, "specified device not found")
            if cmd == "status":
                if deviceID in self.deviceStatus:
                    return str(self.deviceStatus[deviceID])
                elif deviceID == "all":
                    return json.dumps(self.deviceStatus)
            elif cmd == "schedule":  # returns stored daily schedule
                if deviceID in ScheduleDict:
                    return json.dumps(ScheduleDict[deviceID])
                elif deviceID == "all":
                    return json.dumps(ScheduleDict)
            else:
                cherrypy.HTTPError(404, "invalid url")

    # used for turning on and off the preset mode and for stopping the service
    @cherrypy.tools.accept(media='application/json')
    def POST(self, *uri, **params):
        global stop
        global Hcatalog
        global ScheduleDict
        if len(uri) != 0:
            deviceID = uri[0]  # ID of the device to which the PlantCare commands will be sent
            cmd = str(uri[1])
            if deviceID == "system":  # system management
                if cmd == 'stop':
                    # turns off preset mode and the REST API service
                    # stop thread
                    if self.active:
                        print('Stopping scheduler thread...')
                        self.schedulerThread.stop()
                        self.schedulerThread.join()
                        print('Scheduler thread stopped')
                    # close REST API service
                    print('Stopping API service...')
                    cherrypy.engine.exit()
                elif cmd == 'start':  # start the service, MUST BE ALWAYS CALLED AFTER SCRIPT STARTS
                    outputDict = {}
                    if not self.active:
                        # self.MQTT.messageBroker = Hcatalog.broker["ip"]
                        # self.MQTT.brokerPort = int(Hcatalog.broker["port"])
                        # self.active = True
                        # self.MQTT.start()  # NOTE: if the thread deals with MQTT ACKS this client is redundant
                        # start scheduler thread
                        # instantiate scheduler and start it
                        # start MQTT client of the job scheduler
                        self.schedulerThread.MQTT = AutoModeMQTTClient("AutomaticModeScheduledJobs", Hcatalog.broker["ip"], int(Hcatalog.broker["port"]))
                        print('starting scheduler MQTT client')
                        self.schedulerThread.MQTT.start()
                        print('scheduler MQTT client started')
                        print('Starting scheduler thread...')
                        self.schedulerThread.start()
                        print('Scheduler thread online')
                        self.active = True
                    if not self.initialized:
                        for ID in Hcatalog.getPlantIDs():  # create a status entry for each plant ID in home catalog
                            self.deviceStatus[ID] = "off"
                        try:
                            # self.requestActiveIDs() request modes of all device IDs from ModeManager,
                            # if at least one has auto mode active return True
                            if self.requestActiveIDs():
                                self.schedulerThread.toSet = True
                                # thread will now request list of daily jobs and schedule them
                            self.initialized = True
                        except:
                            print("couldn't retrieve active ID list from ModeManager")
                    outputDict["ID status list initialized"] = self.initialized
                    outputDict["Scheduler Thread active"] = self.active
                    return json.dumps(outputDict)

            elif deviceID in self.deviceStatus:  # schedule management and mode activation
                if cmd == 'disable':
                    if self.deviceStatus[deviceID] == "on":
                        self.schedulerThread.removeScheduledJobs(deviceID)
                        del ScheduleDict[deviceID]  # remove schedule from daily schedule dict
                        self.subToPlantAcks(deviceID, unsub=True)  # unsub the  MQTT acks,
                        self.deviceStatus[deviceID] = "off"

                # requires a schedule dictionary as JSON string in the message body
                # which contain the daily jobs for the plant
                elif cmd == 'enable':
                    if self.deviceStatus[deviceID] == "off":
                        try:
                            jsonPayload = cherrypy.request.body.read().decode('utf8')
                            scheduledJobs = json.loads(jsonPayload)
                            ScheduleDict[deviceID] = scheduledJobs  # add schedule to daily schedule dict
                        except:
                            raise cherrypy.HTTPError(500, "invalid message body format")
                        self.schedulerThread.schedulePlantJobs(deviceID, scheduledJobs)  # add jobs to schedule
                        self.subToPlantAcks(deviceID)
                        self.deviceStatus[deviceID] = "on"
                    else:
                        raise cherrypy.HTTPError(500, "automatic mode already enabled")
                # change daily schedule of the plant
                elif cmd == 'changeSchedule':
                    if self.deviceStatus[deviceID] == "on":
                        try:
                            jsonPayload = cherrypy.request.body.read().decode('utf8')
                            scheduledJobs = json.loads(jsonPayload)
                        except:
                            raise cherrypy.HTTPError(500, "message body absent or not in json format")
                        self.schedulerThread.removeScheduledJobs(deviceID)  # remove old jobs
                        try:
                            self.schedulerThread.schedulePlantJobs(deviceID, scheduledJobs)  # schedule received jobs
                            ScheduleDict[deviceID] = scheduledJobs  # replace old schedule in daily schedule dict
                        except:
                            self.schedulerThread.schedulePlantJobs(deviceID, ScheduleDict[deviceID])  # reschedule old jobs
                            raise cherrypy.HTTPError(500, "message body has invalid format")
                    else:
                        raise cherrypy.HTTPError(500, "automatic mode not enabled for specified ID")

            elif deviceID == "all":
                if cmd == "disable":
                    # remove all scheduled jobs, delete all entries from schedule dict, unsubscribe from all
                    # active plantIDS, set all statuses to off
                    for ID in list(self.deviceStatus.keys()):
                        if self.deviceStatus[ID] == "on":
                            self.subToPlantAcks(ID, unsub=True)
                            self.deviceStatus[ID] = "off"
                            self.schedulerThread.removeScheduledJobs(deviceID)
                            del ScheduleDict[ID]  # remove schedule from daily schedule dict
            else:
                raise cherrypy.HTTPError(404, "invalid url")

    def requestActiveIDs(self):
        global Hcatalog
        modeActive = False
        suffix = '/all/status'
        ip = Hcatalog.urls["ModeManager"]["ip"]
        port = Hcatalog.urls["ModeManager"]["port"]
        url = 'http://'+ip+suffix
        response = requests.get(url)
        modeDict = json.loads(response.content)
        for el in modeDict.items():
            id = el[0]
            modeList = el[1]
            if "auto" in modeList:
                self.deviceStatus[id] = "on"
                self.subToPlantAcks(id)
                modeActive = True
        # request device modes from ModeManager and update self.deviceStatus
        return modeActive  # true if at least 1 id has auto mode enabled


if __name__ == '__main__':
    def CORS():
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
    # retrieve topic data from the home catalog
    # file = open("configFile.json", "r")
    # jsonString = file.read()
    # file.close()
    # data = json.loads(jsonString)
    # catalog_ip = data["resourceCatalog"]["ip"]
    # catalog_port = data["resourceCatalog"]["port"]
    # myIP = data["automaticMode"]["ip"]
    # myPort = data["automaticMode"]["port"]
    catalog_ip = "smart-pot-catalog.herokuapp.com"
    catalog_port = ""
    myIP = '0.0.0.0'
    myPort = os.getenv('PORT')
    # instantiate catalog class and send requests to the home catalog actor
    Hcatalog = catalog(catalog_ip, catalog_port)  # global variable
    Hcatalog.requestAll()  # request all topics and urls

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tool.session.on': True,
            'tools.CORS.on': True,
            'tools.response_headers.on': True
        }
    }
    # START THE REST API SERVICE
    cherrypy.tree.mount(AutomaticModeREST(), '/', conf)
    cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS)
    cherrypy.config.update({"server.socket_host": str(myIP), "server.socket_port": int(myPort)})
    cherrypy.engine.start()
    cherrypy.engine.block()
