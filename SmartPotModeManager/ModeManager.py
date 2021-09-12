from SmartPotModeManager.homeCatalogRequests import catalog
# from MQTTPlantCare import MQTTClient
import json
from datetime import datetime
import cherrypy
import requests
import os
import time


feedbackModeDataFileName = "storedTresholds.json"  # file acting as storage for feedback mode thresholds
scheduleFileName = "storedSchedules.json"  # file acting as storage for auto mode schedules
Hcatalog = {}  # this dictionary contains all data retrieved from the device catalog (list of plantIDs, their MQTT topics)
scheduleDB = None  # global object managing schedule storage

# this actor stores general statuses of the three modes (microservice status)
# it also stores the list of modes enabled for each plant in the system
# acts as DB to store the full schedules of each plantID, when requested it will send the daily schedules to Auto Mode
# manages requests from UI to manage the smart pots (activating/disabling modes, changing mode parameters)


def isTimeFormat(input):
    try:
        time.strptime(input, '%H:%M')
        return True
    except ValueError:
        return False


class scheduleStorage:
    # "weekday" is the weekday of the date the schedule was loaded (to make sure current daily schedule is not updated)
    # it contains the water/lighting jobs of the day for each plant

    # "schedule" will contain a dict with entries of format "plantID":dailySchedule
    dailySchedule = {"weekday": "", "schedule": {}}
    # fullSchedule is a dict with entries "plantID":fullScheduleData, where fullSchedule data is a dict of format:
    # {"type":schedType, "schedData":scheduleData}
    fullSchedule = {}
    DEBUG = False

    def __init__(self, fileName):  # load full schedule and daily schedule from file
        self.storageFileName = fileName
        with open(fileName, "r") as fp:
            schedDict = json.load(fp)
        self.fullSchedule = schedDict
        self.loadDailySchedules()  # overwrites current daily schedule in self.dailySchedule["schedule"]
        fp.close()

    def getWeeklyJobs(self, deviceID):
        if deviceID == "all":
            return self.fullSchedule
        elif deviceID in self.fullSchedule:
            return self.fullSchedule[deviceID]["schedData"]
        else:
            return None

    def getDailyJobs(self, deviceID):
        # return the dictionary containing auto mode jobs for the day
        # if the current daily schedule refers to the day before, then load a new schedule returning daily jobs
        if datetime.today().weekday() != self.dailySchedule["weekday"]:
            self.loadDailySchedules()
        if deviceID == "all":
            return self.dailySchedule["schedule"]
        elif deviceID in self.dailySchedule["schedule"]:
            return self.dailySchedule["schedule"][deviceID]
        else:
            return None

    def addSchedule(self, devID, scheduleJSON):
        # add a schedule entry for specified devID
        # if there is already a schedule entry for this devID it will be overwritten
        try:
            jsonDict = json.loads(scheduleJSON)
        except:
            return False
        scheduleData = jsonDict[devID]
        if "type" in scheduleData and "schedData" in scheduleData:
            self.fullSchedule[devID] = scheduleData
            if self.DEBUG:
                print(f"adding following schedule for device {devID}")
                print(self.fullSchedule)
            if scheduleData["type"] == "daily":
                self.dailySchedule["schedule"][devID] = scheduleData["schedData"]
                if self.DEBUG:
                    print(f"daily schedule for device {devID}")
                    print(self.dailySchedule)
                return True
            elif scheduleData["type"] == "weekly":
                weekday = datetime.today().weekday()  # get number corresponding to weekday (0-mon, 6-sun)
                self.dailySchedule["schedule"][devID] = scheduleData["schedData"][weekday]
                if self.DEBUG:
                    print(f"daily schedule for device {devID}")
                    print(self.dailySchedule)
                return True
            else:
                raise cherrypy.HTTPError(500, f"unsupported schedule type: {scheduleData['type']}")
        else:
            return False

    def updateScheduleFile(self):  # write stored fullschedule in schedule file
        with open(self.storageFileName, "w") as fp:
            json.dump(self.fullSchedule, fp)

    def updateFullSchedule(self, devID, scheduleJSON, weekday_n):
        # changes a single day in daily schedule of devID, only possible for weekly schedules
        try:
            jsonDict = json.loads(scheduleJSON)
        except:
            return False
        scheduleData = jsonDict[devID]
        if "type" in scheduleData and "schedData" in scheduleData:
            self.fullSchedule[devID][weekday_n] = scheduleData
            if weekday_n == datetime.today().weekday():  # get number corresponding to weekday (0-mon, 6-sun)
                self.dailySchedule["schedule"][devID] = scheduleData["schedData"][weekday_n]
            else:
                raise cherrypy.HTTPError(500, f"unsupported schedule type: {scheduleData['type']}")
        else:
            return False

    def loadDailySchedules(self):
        # for each plantID get the jobs to be performed for the day
        self.dailySchedule["weekday"] = datetime.today().weekday()  # weekday of the loaded daily schedule
        for sched in list(self.fullSchedule.items()):
            plantID = sched[0]
            schedData = sched[1]
            # if the schedule type is "daily" then just get the schedule data
            if schedData["type"] == "daily":
                dailyJobs = schedData["schedData"]
            # if the schedule type is "weekly" get the schedule data of the current weekday
            elif schedData["type"] == "weekly":
                weekday = datetime.today().weekday()  # get number corresponding to weekday (0-mon, 6-sun)
                dailyJobs = schedData["schedData"][weekday]
            else:
                raise ValueError("Unrecognized schedule type")
            # format of dailyJobs : {"water":{"time":"duration"}, "light":{"time":"duration"}
            self.dailySchedule["schedule"][plantID] = dailyJobs

    def removePlantID(self, devID):
        # remove plantID from the schedule dictionaries
        if devID in self.dailySchedule["schedule"].keys():
            self.dailySchedule["schedule"].pop(devID)
        if devID in self.fullSchedule["schedule"].keys():
            self.fullSchedule["schedule"].pop(devID)

    # returns True if format is correct, False otherwise
    def checkScheduleFormat(self, schedule):
        pass


class ModeManagerREST(object):
    exposed = True
    default_illum_thresh = 70  # threshold of the illum sensor value after which it the plant is considered illuminated
    schedulerThread = None
    active = False
    initialized = False
    deviceMode = {}  # dict of struct {"plant1":modelist, "plant2":modelist,..} modelist is a list of active modes for that
    # plant ("manual", "auto", "feedback"), NOTE: system also stores schedules for plantIDs with auto mode not curr active
    initialModeFileName = "storedModes.json"

    feedback_mode_thresholds = {}  # dict of struct "plantID": {"type":"const" or "sched", "data":tr_dict}

    def return_value_check(self, service, ret_val):
        if ret_val == 404:
            raise cherrypy.HTTPError(404, f"{service} mode could not be reched or url was invalid")
        if ret_val == 500:
            raise cherrypy.HTTPError(500, f"{service} mode had an internal error")

    # tr_dict={"light_time":n, "hum_tresh":t}, n is the minimum number, if type "sched" we have a dict:
    # {t1:tr_dict1, t2:tr_dict2} where t1,t2,.. are timestamps
    # of minutes the plant must be irradiated, t the minimum soil humidity treshold to keep
    @cherrypy.tools.accept(media='application/json')
    def GET(self, *uri, **params):
        global Hcatalog
        global scheduleDB
        if len(uri) != 0:
            devID = uri[0]

            if devID == 'update':  # update plantIDs
                Hcatalog.requestAll()
                keys = self.deviceMode.copy()
                for plantID in keys.keys():
                    if plantID not in Hcatalog.getPlantIDs():
                        self.deviceMode.pop(plantID)
                        scheduleDB.removePlantID(plantID)
                for ID in Hcatalog.getPlantIDs():  # create a status entry for each new plant ID in home catalog
                    if ID not in self.deviceMode.keys():
                        self.deviceMode[ID] = []

            mode = uri[1]
            # requests concerning automatic mode
            if not (devID == "all" or devID in self.deviceMode):
                raise cherrypy.HTTPError(404, "specified id not found")
            if mode == "status":
                Hcatalog.requestAll()

                if devID == "all":
                    return json.dumps(self.deviceMode)
                else:
                    return json.dumps(self.deviceMode[devID])
            if mode == "auto":
                cmd = uri[2]
                if cmd == "schedule":
                    schedType = uri[3]
                    if devID == "all":  # return schedule of all plantIDs with active auto mode
                        if "onlyActives" not in params:
                            raise cherrypy.HTTPError(500, "missing url parameter 'onlyActives'")
                        if schedType == "daily":  # this request is called daily by auto mode
                            tmpDict = {}
                            if len(self.deviceMode) == 0:
                                raise cherrypy.HTTPError(500, "device ID list is empty")
                            for ID in self.deviceMode:
                                if params["onlyActives"] == "True":  # return schedules of ids with active auto mode
                                    if self.isModeActive(ID, "auto"):
                                        tmpDict[ID] = scheduleDB.getDailyJobs(ID)
                                elif params["onlyActives"] == "False":  # return all stored schedules
                                    jobs = scheduleDB.getDailyJobs(ID)
                                    if jobs is not None:
                                        tmpDict[ID] = jobs
                                else:
                                    raise cherrypy.HTTPError(500,
                                                             'invalid value for parameter "onlyActives", acceptable values are ["True", "False"]')
                            outputJson = json.dumps(tmpDict)
                            tmpDict.clear()
                            return outputJson
                        elif schedType == "complete":
                            if len(self.deviceMode) == 0:
                                raise cherrypy.HTTPError(500, "device ID list is empty")
                            if params["onlyActives"] == "True":
                                tmpDict = {}
                                for ID in self.deviceMode:
                                    if self.isModeActive(ID, "auto"):
                                        tmpDict[ID] = scheduleDB.fullSchedule[ID]
                                outputJson = json.dumps(tmpDict)
                                tmpDict.clear()
                                return outputJson
                            elif params["onlyActives"] == "False":
                                return json.dumps(scheduleDB.fullSchedule)
                            else:
                                raise cherrypy.HTTPError(500,
                                                         'invalid value for parameter "onlyActives", acceptable values are ["True", "False"]')
                        else:
                            raise cherrypy.HTTPError(404, "invalid url")
                    if devID in self.deviceMode:  # return stored schedule (regardless of device mode)
                        if schedType == "daily":
                            s = scheduleDB.getDailyJobs(devID)
                            if s is None:  # no stored schedule
                                return "empty"
                            else:
                                return json.dumps(s)
                        if schedType == "weekly":
                            s = scheduleDB.getWeeklyJobs(devID)
                            if s is None:  # no stored schedule
                                return "empty"
                            else:
                                return json.dumps(s)

    @cherrypy.tools.accept(media='application/json')
    def POST(self, *uri, **params):
        global Hcatalog
        global scheduleDB
        if len(uri) != 0:
            devID = uri[0]
            if devID == "system":
                cmd = uri[1]
                if cmd == "start":
                    outputDict = {}
                    if not self.initialized:
                        # when turned on for the first time auto mode disabled for all plantIDs
                        # system will try to retrieve initial modes from a file
                        for ID in Hcatalog.getPlantIDs():  # create a status entry for each plant ID in home catalog
                            print(ID)
                            self.deviceMode[ID] = []
                        # read initial modes in the file
                        try:
                            with open(self.initialModeFileName, "r") as fp:
                                initialModes = json.load(fp)
                                for storedData in list(initialModes.items()):
                                    id = storedData[0]
                                    modes = storedData[1]
                                    self.deviceMode[id].extend(modes)
                                self.initialized = True
                        except:
                            raise cherrypy.HTTPError(500, "unable to open initial modes file")
                    outputDict["ID status list initialized"] = self.initialized
                    return json.dumps(outputDict)

            if devID in self.deviceMode or devID == "all":  # only "disable" commands are supported with "all" as target
                mode = uri[1]
                # requests to enable/disable manual mode
                if mode == "manual":
                    cmd = uri[2]
                    if cmd == "enable":
                        if devID == "all":
                            raise cherrypy.HTTPError(500, "not implemented")
                        if "manual" not in self.deviceMode[devID]:
                            if not self.modeConflict("manual", devID):
                                self.deviceMode[devID].append("manual")
                                ret_code = self.manualModeRequest(devID, "enable")
                                self.return_value_check("manual", ret_code)  # raises HTTPerror if code is 404 or 500
                                return
                            raise cherrypy.HTTPError(500, "cannot enable due to mode conflict")
                        else:
                            raise cherrypy.HTTPError(500, "mode already enabled")
                    if cmd == "disable":
                        if devID == "all":
                            for dev in list(self.deviceMode.items()):
                                ID = dev[0]
                                if "manual" in self.deviceMode[ID]:
                                    self.deviceMode[devID].remove("manual")
                                    ret_code = self.manualModeRequest(devID, "disable")
                                    self.return_value_check("manual",
                                                            ret_code)  # raises HTTPerror if code is 404 or 500
                        elif "manual" in self.deviceMode[devID]:
                            self.deviceMode[devID].remove("manual")
                            self.manualModeRequest(devID, "disable")
                            # add error if it can't reach manual mode
                        else:
                            raise cherrypy.HTTPError(500, "mode already disabled")

                # requests to enable/disable auto mode and add to add schedules
                if mode == "auto":
                    cmd = uri[2]
                    # requires a parameter "newSchedule", if True then a schedule must also be sent in msg body
                    # if False then system will use the stored schedule, if no stored schedule is found, http error
                    if cmd == "enable":
                        if devID == "all":
                            raise cherrypy.HTTPError(500, "enable command can only be called on single IDs")
                        if "auto" not in self.deviceMode[devID]:
                            if "newSchedule" not in params:
                                raise cherrypy.HTTPError(500, "missing url parameter 'newSchedule' ")
                            if not self.modeConflict("auto", devID):
                                if params["newSchedule"] == "False":
                                    daily_jobs = scheduleDB.getDailyJobs(devID)
                                    if daily_jobs is not None:  # CHECK IF THERE IS A STORED SCHEDULE
                                        self.deviceMode[devID].append("auto")
                                        ret_code = self.autoModeRequest(devID, "enable", daily_jobs)
                                        self.return_value_check("auto",
                                                                ret_code)  # raises HTTPerror if code is 404 or 500

                                    else:
                                        raise cherrypy.HTTPError(500, "no scheduled stored for specified id")
                                elif params["newSchedule"] == "True":
                                    try:
                                        jsonPayload = cherrypy.request.body.read().decode('utf8')
                                        print(jsonPayload)
                                    except:
                                        raise cherrypy.HTTPError(500, "error in retrieving request body")
                                    if scheduleDB.addSchedule(devID, jsonPayload):
                                        daily_jobs = scheduleDB.getDailyJobs(devID)
                                        if daily_jobs is not None:  # CHECK IF SCHEDULE IS STORED CORRECTLY
                                            self.deviceMode[devID].append("auto")
                                            ret_code = self.autoModeRequest(devID, "enable", daily_jobs)
                                            self.return_value_check("auto",
                                                                    ret_code)  # raises HTTPerror if code is 404 or 500
                                            scheduleDB.updateScheduleFile()  # store new schedule in file
                                        else:
                                            raise cherrypy.HTTPError(500, "error in storing the schedule")
                                    else:
                                        raise cherrypy.HTTPError(500, "bad request body format")
                                else:
                                    raise cherrypy.HTTPError(500,
                                                             "invalid parameter value, acceptable values are [True, False]")
                            else:
                                raise cherrypy.HTTPError(500, "cannot enable due to mode conflict")
                        else:
                            raise cherrypy.HTTPError(500, "automatic mode already enabled")
                    if cmd == "disable":
                        if devID == "all":
                            for dev in list(self.deviceMode.items()):
                                ID = dev[0]
                                if "auto" in self.deviceMode[ID]:
                                    try:
                                        self.autoModeRequest(devID, "disable")
                                        self.deviceMode[devID].remove("auto")
                                    except:
                                        raise cherrypy.HTTPError(500, "error in communicating with Automatic Mode")
                        elif "auto" in self.deviceMode[devID]:
                            try:
                                self.autoModeRequest(devID, "disable")
                                self.deviceMode[devID].remove("auto")
                            except:
                                raise cherrypy.HTTPError(500, "error in communicating with Automatic Mode")
                        else:
                            raise cherrypy.HTTPError(500, f"automatic mode already disabled for {devID}")
                    if cmd == "newSchedule":  # command to send a new schedule to store, it will overwrite old schedule,
                        if devID == "all":
                            raise cherrypy.HTTPError(500, "newSchedule command can only be called on single IDs")
                        if "weekday" in params:  # change only a single day
                            try:
                                weekday_n = int(params["weekday"])
                            except:
                                raise cherrypy.HTTPError(500, "parameter 'weekday' is not a valid integer")
                            if 0 < weekday_n < 6:
                                raise cherrypy.HTTPError(500, "parameter 'weekday' is not an integer between 0 and 6")

                            try:
                                jsonPayload = cherrypy.request.body.read().decode('utf8')
                                if not scheduleDB.updateFullSchedule(devID, jsonPayload, weekday_n):
                                    raise cherrypy.HTTPError(500, "bad message body format")
                                if "auto" in self.deviceMode[devID]:  # update daily schedule if auto mode is active
                                    try:
                                        dailyJob = scheduleDB.getDailyJobs(devID)
                                        self.autoModeRequest(devID, "changeSchedule", dailyJob)
                                    except:
                                        raise cherrypy.HTTPError(500, "error in communicating with Automatic Mode")
                            except:
                                raise cherrypy.HTTPError(500, "message not a valid json format")

                        else:  # change whole schedule
                            try:
                                jsonPayload = cherrypy.request.body.read().decode('utf8')
                                print("msg")
                                print(jsonPayload)
                                if not scheduleDB.addSchedule(devID, jsonPayload):
                                    raise cherrypy.HTTPError(500, "bad message body format")
                                if "auto" in self.deviceMode[devID]:  # update daily schedule if auto mode is active
                                    try:
                                        dailyJob = scheduleDB.getDailyJobs(devID)
                                        self.autoModeRequest(devID, "changeSchedule", dailyJob)
                                    except:
                                        raise cherrypy.HTTPError(500, "error in communicating with Automatic Mode")
                            except:
                                raise cherrypy.HTTPError(500, "message not a valid json format")
                if mode == "feedback":
                    cmd = uri[2]
                    if cmd == "enable":
                        if devID == "all":
                            raise cherrypy.HTTPError(500,
                                                     "enable command can only be called on single IDs")
                        if "feedback" not in self.deviceMode[devID]:
                            if not self.modeConflict("feedback", devID):
                                # get message body
                                try:
                                    jsonPayload = cherrypy.request.body.read().decode('utf8')
                                except:
                                    raise cherrypy.HTTPError(500, "error in retrieving request body")
                                try:
                                    msg_body_dict = json.loads(jsonPayload)
                                except:
                                    raise cherrypy.HTTPError(500,
                                                             "message body is not in valid JSON format")
                                # expected format {"type":"const", "data":{"light_time":-, "hum_thresh:-, "illum_thresh":-}}

                                feedback_mode_msg = {}
                                # {"light_time": n, "hum_thresh": t}, t,n between 0 and 100
                                if "hum_thresh" in msg_body_dict:
                                    # check data correctness
                                    # TO-DO: implement partial feedback mode at FB mode side
                                    if 0 <= float(msg_body_dict["hum_thresh"]) <= 1023:
                                        feedback_mode_msg["hum_thresh"] = msg_body_dict["hum_thresh"]
                                    else:
                                        raise cherrypy.HTTPError(500,
                                                                 "humidity threshold must be a value between 0 and 100")
                                if "light_time" in msg_body_dict:
                                    if 0 <= int(msg_body_dict["light_time"]) <= 21600:
                                        feedback_mode_msg["light_time"] = msg_body_dict["light_time"]
                                    if "illum_thresh" in msg_body_dict:
                                        if 0 <= int(msg_body_dict["illum_thresh"]) <= 1023:
                                            feedback_mode_msg["illum_thresh"] = msg_body_dict[
                                                "illum_thresh"]
                                        else:
                                            feedback_mode_msg[
                                                "illum_thresh"] = self.default_illum_thresh
                                    else:
                                        feedback_mode_msg["illum_thresh"] = self.default_illum_thresh

                                if len(msg_body_dict) == 0:
                                    raise cherrypy.HTTPError(500, "invalid message body")

                                # light_time or hum_tresh can be omitted (in that case partial FB mode is implemented)
                                if "light_time" not in feedback_mode_msg:
                                    feedback_mode_msg["light_time"] = -1
                                    feedback_mode_msg["illum_thresh"] = self.default_illum_thresh
                                if "hum_thresh" not in feedback_mode_msg:
                                    feedback_mode_msg["hum_thresh"] = -1
                                # SEND ENABLE REQUEST TO FEEDBACK MODE ACTOR
                                ret_code = self.feedbackModeRequest(devID, req="enable",
                                                         paramData=feedback_mode_msg)
                                self.return_value_check("feedback", ret_code)
                                self.deviceMode[devID].append("feedback")
                            else:
                                raise cherrypy.HTTPError(500, "cannot enable due to mode conflict")
                        else:
                            raise cherrypy.HTTPError(500, "feedback mode already enabled")

                    if cmd == "disable":
                        if devID == "all":
                            for dev in list(self.deviceMode.items()):
                                ID = dev[0]
                                if "feedback" in self.deviceMode[ID]:
                                    try:
                                        ret_code = self.feedbackModeRequest(devID, "disable")
                                        self.deviceMode[devID].remove("feedback")
                                        self.return_value_check("feedback", ret_code)
                                    except:
                                        raise cherrypy.HTTPError(500,
                                                                 "error in communicating with Feedback Mode Actor")
                        elif "feedback" in self.deviceMode[devID]:
                            try:
                                self.deviceMode[devID].remove("feedback")
                                ret_code = self.feedbackModeRequest(devID, "disable")
                                self.return_value_check("feedback", ret_code)
                            except:
                                raise cherrypy.HTTPError(500,
                                                         "error in communicating with Feedback Mode Actor")
                        else:
                            raise cherrypy.HTTPError(500, f"feedback mode already disabled for {devID}")

                    if cmd == "paramChange":  # command to set new thresholds, can also change type (const or sched)
                        # can be called on devIDs for which fb mode is not active (it will just store the parameters)
                        if devID == "all":
                            raise cherrypy.HTTPError(500,
                                                     "paramChange command can only be called on single IDs")
                        try:
                            jsonPayload = cherrypy.request.body.read().decode('utf8')
                        except:
                            raise cherrypy.HTTPError(500, "error in retrieving request body")
                        try:
                            msg_body_dict = json.loads(jsonPayload)
                        except:
                            raise cherrypy.HTTPError(500, "message body is not in valid JSON format")
                        # expected format {"type":"const", "data":{"light_time":-, "hum_thresh:-, "illum_thresh":-}}

                        feedback_mode_msg = {}
                        # {"light_time": n, "hum_thresh": t}, t,n between 0 and 100
                        if "hum_thresh" in msg_body_dict:
                            # check data correctness
                            # TO-DO: implement partial feedback mode at FB mode side
                            if 0 <= float(msg_body_dict["hum_thresh"]) <= 1023:
                                feedback_mode_msg["hum_thresh"] = msg_body_dict["hum_thresh"]
                            else:
                                raise cherrypy.HTTPError(500,
                                                         "humidity threshold must be a value between 0 and 100")
                        if "light_time" in msg_body_dict:
                            if 0 <= int(msg_body_dict["light_time"]) <= 21600:
                                feedback_mode_msg["light_time"] = msg_body_dict["light_time"]
                            if "illum_thresh" in msg_body_dict:
                                if 0 <= int(msg_body_dict["illum_thresh"]) <= 1023:
                                    feedback_mode_msg["illum_thresh"] = msg_body_dict["illum_thresh"]
                                else:
                                    feedback_mode_msg["illum_thresh"] = self.default_illum_thresh
                            else:
                                feedback_mode_msg["illum_thresh"] = self.default_illum_thresh

                        if len(msg_body_dict) == 0:
                            raise cherrypy.HTTPError(500, "invalid message body")

                        # light_time or hum_tresh can be omitted (in that case partial FB mode is implemented)
                        if "light_time" not in feedback_mode_msg:
                            feedback_mode_msg["light_time"] = -1
                            feedback_mode_msg["illum_thresh"] = self.default_illum_thresh
                        if "hum_thresh" not in feedback_mode_msg:
                            feedback_mode_msg["hum_thresh"] = -1
                        # TO-DO: STORE FB MODE DATA IN MODE MANAGER?
                        # SEND ENABLE REQUEST TO FEEDBACK MODE ACTOR
                        self.feedbackModeRequest(devID, req="paramChange", paramData=feedback_mode_msg)
            else:
                raise cherrypy.HTTPError(404, "invalid url")

    def isModeActive(self, plantID, mode):
        if not mode in ["manual", "auto", "feedback"]:
            print("warning: searched status for invalid mode: ", mode)
            return False
        if mode in self.deviceMode[plantID]:
            return True
        else:
            return False

    def modeConflict(self, newMode, plantID):  # feedback mode can't be active with manual or auto
        # returns true if there is a conflict (we try to activate a conflicting mode)
        if newMode == "feedback":
            if "manual" in self.deviceMode[plantID] or "auto" in self.deviceMode[plantID]:
                return True
        if newMode == "auto" or newMode == "manual":
            if "feedback" in self.deviceMode[plantID]:
                return True
        else:
            return False

    def manualModeRequest(self, devID, req):
        global Hcatalog
        ip = Hcatalog.urls["manualMode"]["ip"]
        url = "http://" + ip + '/' + devID + '/' + req
        retval = requests.post(url)
        return retval.status_code

    def autoModeRequest(self, devID, req, dailySched=None):
        global Hcatalog
        ip = Hcatalog.urls["automaticMode"]["ip"]
        url = "http://" + ip + '/' + devID + '/' + req
        if req == "enable" or req == "changeSchedule":
            if dailySched is None:
                raise ValueError("daily schedule for auto mode enable request is empty")
            dailySchedJSON = json.dumps(dailySched)
            ret_val = requests.post(url, data=dailySchedJSON)
            return ret_val.status_code
        elif req == "disable":
            ret_val = requests.post(url)
            return ret_val.status_code

    def feedbackModeRequest(self, devID, req, paramData=None):
        global Hcatalog
        # possible cmds: enable, disable, paramChange
        ip = Hcatalog.urls["feedbackMode"]["ip"]
        url = "http://" + ip + '/' + devID + '/' + req
        if req == "enable" or req == "paramChange":
            if paramData is None:
                raise ValueError("parameter data absent for feedback mode 'enable' or 'paramChange' request")
            ParamDataJSON = json.dumps(paramData)
            ret_val = requests.post(url, data=ParamDataJSON)
            return ret_val.status_code
        elif req == "disable":
            ret_val = requests.post(url)
            return ret_val.status_code


if __name__ == '__main__':
    def CORS():
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"

    # retrieve schedule data from file
    try:
        scheduleDB = scheduleStorage(scheduleFileName)
    except:
        print("warning: could not open schedule file")

    # retrieve topic data from the home catalog
    catalog_ip = "smart-pot-catalog.herokuapp.com"
    catalog_port = ""  # data["resourceCatalog"]["port"]

    myIP = "0.0.0.0"
    myPort = os.getenv('PORT')

    Hcatalog = catalog(catalog_ip, catalog_port)  # global variable
    Hcatalog.requestAll()  # request all topics and urls

    conf = {
        'global': {
            'server.socket_host': '0.0.0.0',
            'server.socket_port': int(os.getenv('PORT'))
            # 'server.socket_port': int('8080'),
        },
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tool.session.on': True,
            'tools.CORS.on': True,
            'tools.response_headers.on': True
        }
    }
    cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS)
    cherrypy.quickstart(ModeManagerREST(), '/', config=conf)

