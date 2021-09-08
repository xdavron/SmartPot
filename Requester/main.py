
import requests
import time

def req():
    modeManager = 'https://smart-pot-mode-manager.herokuapp.com/system/start'
    manualmode = 'https://smart-pot-manual-mode.herokuapp.com/system/start'
    automode = 'https://smart-pot-auto-mode.herokuapp.com/system/start'
    feedbackmode = 'https://smart-pot-feedback-mode.herokuapp.com/system/start'
    myobj = {}

    mode = requests.post(modeManager, data=myobj)
    print(mode.content)
    time.sleep(1)
    manual = requests.post(manualmode, data=myobj)
    time.sleep(1)
    print(manual.content)
    auto = requests.post(automode, data=myobj)
    time.sleep(1)
    print(auto.content)
    feedback = requests.post(feedbackmode, data=myobj)
    time.sleep(1)
    print(feedback.content)
    time.sleep(800)

if __name__ == '__main__':
    while True:
        req()




