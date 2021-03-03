# steps involved:
# 1] Script checks each week folder and compares to previous log.
#    If a new element is found it is added to a new list or if an element is missing it is added to a second list.
# 2] The script will then go to the provided website url, verify that the files need to be updated and do so.

import json
import os
from pprint import pprint
# "Logs": [
#     {
#         "15/09/2020": 0,
#         "wk3": " css.html  - upload",
#         "wk5": " proo.html  - deleted"
#     },
#     {
#         "12/09/2020": 0,
#         "wk1": " index.html  - upload",
#         "wk2": " index.html  - removed"
#     }
# ]

rec_URL = "https://drive.google.com/drive/folders/1pFHUrmpLv9gEJsvJYKxMdISuQuQsd_qX"
KEY = "8cc87cf406775101c2df87b07b3a170d"
URL = "https://034f8a1dcb5c.eu.ngrok.io"
ENDPOINT = "/webservice/rest/server.php"


# Check if this files system is run for the first time
def Files_Check():
    with open('FilesLog.json', "r") as f:
        data = json.load(f)
        if data["Initialize"] == "yes":
            # Mark it off as no so the script will no every subsequent run will not be the first time
            # data["Initialize"] = "no"
            with open('FilesLog.json', 'w') as file:
                json.dump(data, file)
            System_Init()
        else:
            System_Update()


# Do this only the first time the script is run
def System_Init():
    upload_files = []
    # https://github.com/mikhail-cct/ca3-test/blob/master/wk1/index.html
    # Search the folder of which this script is placed within
    subfolders = [f.path for f in os.scandir() if f.is_dir()]
    files = [f.path for f in os.scandir(subfolders[0])]
    for i in os.scandir():
        if i.is_dir():
            for f in os.scandir(i.path):
                upload_files.append(f.path)
    pprint(upload_files)


def System_Update():
    # update the files on the ngrok server
    return None


Files_Check()
