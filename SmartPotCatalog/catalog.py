# resource catalog web service: exposing the data to others by GET; the web page can be updated by POST

import cherrypy
import json
import os
import requests


class resourceCatalog(object):
    exposed = True

    updateURL = 'https://smart-pot-mode-manager.herokuapp.com/all/update'

    @cherrypy.tools.accept(media='application/json')
    def GET(self, *uri, **params):
        # reading the file with the informations
        try:
            file = open("initialData.json", "r")
            self.jsonString = file.read()
            file.close()
        except:
            raise KeyError("* resourceCatalog: ERROR IN READING INITIAL DATA *")
        self.jsonDic = json.loads(self.jsonString)
        # print(self.jsonDic)

        # item will contain the request information
        try:
            item = uri[0]
            if (item in self.jsonDic):
                result = self.jsonDic[item]
                requestedData = json.dumps(result)
                return requestedData
            elif (item == "all"):
                return self.jsonString
            else:
                raise cherrypy.HTTPError(404, "invalid url")
        except:
            raise cherrypy.HTTPError(404, "invalid url")

    @cherrypy.tools.accept(media='application/json')
    def POST(self, *uri, **params):
        try:
            file = open("initialData.json", "r")
            self.jsonString = file.read()
            file.close()
        except:
            raise KeyError("* resourceCatalog: ERROR IN READING INITIAL DATA *")
        self.jsonDic = json.loads(self.jsonString)
        # print(self.jsonDic['topics'])

        if len(uri) != 0:
            cmd = uri[0]
            if cmd == 'add':
                # read message body extract ID
                inputJson = cherrypy.request.body.read()
                print(inputJson)
                inputDict = json.loads(inputJson)
                inputID = inputDict['id']
                plantName = inputDict['name']
                # create list of plant ID
                listOfId = self.jsonDic['topics'].keys()
                # check input Id is available in list
                found = False
                for plantId in listOfId:
                    if inputID == plantId:
                        found = True
                #  if exists raise error if not add to list
                if found:
                    raise cherrypy.HTTPError(500, "This " + inputID + " plant Id exists in catalog")
                else:
                    # create topics for new ID
                    self.jsonDic['topics'][inputID] = {
                        'name': plantName,
                        'topic': {
                            'lightControlTopic': 'dataCenter/' + inputID + '/lightControlTopic',
                            "waterControlTopic": "dataCenter/" + inputID + "/waterControlTopic",
                            "waterControlOrder": "dataCenter/" + inputID + "/waterControlOrder",
                            "lightControlOrder": "dataCenter/" + inputID + "/lightControlOrder",
                            "dhtTopic": "dataCenter/" + inputID + "/tempHum",
                            "soilTopic": "dataCenter/" + inputID + "/soil",
                            "lightTopic": "dataCenter/" + inputID + "/light",
                            "waterTopic": "dataCenter/" + inputID + "/water"
                        },
                        "thresholds": {
                            "minHum": "1.0",
                            "minTemp": "1.0",
                            "maxHum": "10.0",
                            "maxTemp": "10.0"
                        }}
                    # save new ID
                    with open("initialData.json", "w") as fp:
                        json.dump(self.jsonDic, fp)

                    updateMode = requests.get(self.updateURL)
                    print(updateMode.status_code, updateMode.content)

            elif cmd == 'remove':
                # read message body extract ID
                inputJson = cherrypy.request.body.read()
                inputDict = json.loads(inputJson)
                inputID = inputDict['id']
                # create list of plant ID
                listOfId = self.jsonDic['topics'].keys()
                # check input Id is available in list
                found = False
                for plantId in listOfId:
                    if inputID == plantId:
                        found = True
                #  if exists delete else raise error
                if found:
                    # remove plant ID and save to file
                    del self.jsonDic['topics'][inputID]
                    with open("initialData.json", "w") as fp:
                        json.dump(self.jsonDic, fp)
                    updateMode = requests.get(self.updateURL)
                    print(updateMode.status_code,updateMode.content)
                else:
                    raise cherrypy.HTTPError(500, "This " + inputID + " plantId does not exists in catalog")


if __name__ == '__main__':
    # reading the config file to set the url and the port on which expose the web service
    # file = open("configFile.json", "r")
    # jsonString = file.read()
    # file.close()
    # data = json.loads(jsonString)
    # ip = data["resourceCatalog"]["ip"]
    # port = data["resourceCatalog"]["port"]
    # # client = mqtt.Client()
    # # configuration for the web service
    #
    def CORS():
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
        cherrypy.response.headers["Access-Control-Allow-Credentials"] = "true"
        cherrypy.response.headers["Access-Control-Allow-Methods"] = "GET,HEAD,OPTIONS,POST,PUT"
        cherrypy.response.headers["Access-Control-Allow-Headers"] = "Access-Control-Allow-Headers, Origin,Accept, X-Requested-With, Content-Type, Access-Control-Request-Method, Access-Control-Request-Headers"


    # def CORS():
    #     if cherrypy.request.method == 'OPTIONS':
    #         cherrypy.response.headers['Access-Control-Allow-Headers'] = 'content-type'
    #         cherrypy.response.headers['Access-Congitrol-Allow-Origin'] = '*'
    #         return True
    #     else:
    #         cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'

    # cherrypy.tools.CORS = cherrypy._cptools.HandlerTool(CORS)
    #
    #
    # conf = {'/':
    #     {
    #         'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
    #         'tools.sessions.on': True,
    #         'tools.CORS.on': True,
    #         'tools.response_headers.on': True
    #     }
    # }
    # cherrypy.tree.mount(resourceCatalog(), '/', conf)
    # cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS)
    # cherrypy.config.update({"server.socket_host": '0.0.0.0', "server.socket_port": int(os.environ.get('PORT', 8000))})
    # cherrypy.engine.start()
    # cherrypy.engine.block()

    config = {
        'global': {
            'server.socket_host': '0.0.0.0',
            'server.socket_port': int(os.getenv('PORT'))
            # 'server.socket_port': int('8080'),
        },
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.CORS.on': True
        }
    }

    cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS)
    cherrypy.quickstart(resourceCatalog(), '/', config=config)
