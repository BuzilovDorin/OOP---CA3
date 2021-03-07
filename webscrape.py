from urllib.request import urlopen
from requests import post
import datetime
from dateutil import parser
import requests
import bs4
from bs4 import BeautifulSoup
import os
from os.path import basename
import json
import re

################################################
# Module variables to connect to moodle api:
# Insert token and URL for your site here.
# Insert URL for class recordings here
# Define your unique semester start dates here.
################################################
KEY = "8cc87cf406775101c2df87b07b3a170d"
URL = "https://034f8a1dcb5c.eu.ngrok.io"
ENDPOINT = "/webservice/rest/server.php"
Recordings_URL = "https://drive.google.com/drive/folders/1pFHUrmpLv9gEJsvJYKxMdISuQuQsd_qX"
courseid = "20"
# Semester Start
# Format dates as year-month-day
sem1_start_week = "2020-09-28"
sem2_start_week = "2021-01-04"


################################################
# Rest-Api classes
################################################
def rest_api_parameters(in_args, prefix='', out_dict=None):
    """Transform dictionary/array structure to a flat dictionary, with key names
    defining the structure."""
    if out_dict == None:
        out_dict = {}
    if not type(in_args) in (list, dict):
        out_dict[prefix] = in_args
        return out_dict
    if prefix == '':
        prefix = prefix + '{0}'
    else:
        prefix = prefix + '[{0}]'
    if type(in_args) == list:
        for idx, item in enumerate(in_args):
            rest_api_parameters(item, prefix.format(idx), out_dict)
    elif type(in_args) == dict:
        for key, item in in_args.items():
            rest_api_parameters(item, prefix.format(key), out_dict)
    return out_dict


def call(fname, **kwargs):
    """Calls moodle API function with function name fname and keyword arguments."""
    parameters = rest_api_parameters(kwargs)
    parameters.update(
        {"wstoken": KEY, 'moodlewsrestformat': 'json', "wsfunction": fname})
    # print(parameters)
    response = post(URL+ENDPOINT, data=parameters).json()
    if type(response) == dict and response.get('exception'):
        raise SystemError("Error calling Moodle API\n", response)
    return response


class LocalGetSections(object):
    """Get settings of sections. Requires courseid. Optional you can specify sections via number or id."""

    def __init__(self, cid, secnums=[], secids=[]):
        self.getsections = call('local_wsmanagesections_get_sections',
                                courseid=cid, sectionnumbers=secnums, sectionids=secids)


class LocalUpdateSections(object):
    """Updates sectionnames. Requires: courseid and an array with sectionnumbers and sectionnames"""

    def __init__(self, cid, sectionsdata):
        self.updatesections = call(
            'local_wsmanagesections_update_sections', courseid=cid, sections=sectionsdata)


################################################
# Moodle_Auto_Updater.py
################################################

def Local_Files_Check():
    # Checking directory name to identify semester 1 or semester 2 [ooapp , ooapp2]
    # Getting start date of semester
    if not any(d.isdigit() for d in basename(os.path.abspath("."))):
        month = datetime.datetime.strptime(sem1_start_week, '%Y-%m-%d')
        sem = month.strftime("%V")
        sem_start_year = int(sem1_start_week[:4])
    else:
        month = datetime.datetime.strptime(sem2_start_week, '%Y-%m-%d')
        sem = month.strftime("%V")
        sem_start_year = int(sem2_start_week[:4])
    sem_next_year = sem_start_year + 1
    # Store all recordings from google drive in a dict
    Class_Recordings = Pull_Class_Recording(Recordings_URL)
    # Get all sections of moodle
    sec = LocalGetSections(courseid)
    moodle_Sections = {}
    sections_count = 0
    # Pulling all moodle sections and matching their dates to folder index's
    # First entry of moodle page is semester start date
    for i in range(len(sec.getsections)):
        prev_summary = sec.getsections[i]['name'].encode(
            "ascii", 'ignore').decode()
        title_week = re.search(r"\d+\s\w+", prev_summary)
        if title_week != None:
            sections_count += 1
            wk_title_string = str(title_week.group())
            i = wk_title_string.find(" ")
            date = wk_title_string[:i]
            if len(date) == 1:
                date = "0" + date
            month = datetime.datetime.strptime(
                wk_title_string[i+1:], "%B").month
            if len(str(month)) == 1:
                month = '0' + str(month)
            year = datetime.datetime.now().year
            section_title_parsed = str(year)+"-"+str(month)+"-"+str(date)
            date = datetime.datetime(
                year=sem_start_year, month=int(month), day=int(date))
            print(date)
            moodle_Sem_Week = date.strftime("%V")
            print(moodle_Sem_Week)
            # 52 weeks in a year, if the semester week is less then the start date of semester we passed into a new year
            if int(moodle_Sem_Week) < int(sem):
                date = date.replace(year=sem_next_year)
                moodle_Sem_Week = date.strftime("%V")
                moodle_Sections[moodle_Sem_Week] = sections_count
            else:
                moodle_Sections[moodle_Sem_Week] = sections_count
    # Scan local files
    for i in os.scandir():
        if i.is_dir() and "wk" in i.name:
            # Only files within folders containing "wk" name convention
            local_wk_index = ''.join([n for n in i.name if n.isdigit()])
            print(":::::", local_wk_index)
            Moodle_Update_list = {}
            real_week = 0
            for f in os.scandir(i.path):
                href_link = os.path.abspath(".") + f.path.lstrip(".")
                # Only files ending with .html or .pdf are valid
                if any(n in href_link for n in [".html", ".pdf"]):
                    # Parsing the local files index to match with moodle dates.
                    # Wk1 will match with the first date in moodle
                    real_week_index = int(sem) + (int(local_wk_index) - 1)
                    print("::", real_week_index)
                    for sections in moodle_Sections:
                        print(int(sections), ":", real_week_index)
                        if int(sections) == real_week_index:
                            real_week = moodle_Sections[sections]
                            print("->>", href_link)
                            if ".html" in href_link:
                                soup = BeautifulSoup(
                                    open(href_link), "html.parser")
                                title = soup.find('title').string.encode(
                                    'ascii', 'ignore').decode()
                                Moodle_Update_list[title] = href_link
                            else:
                                Moodle_Update_list[f.name] = href_link
                        else:
                            pass
            for key in list(Class_Recordings):
                key_filtered = re.search("wk(\d+)", key)
                if key_filtered.group() == "wk"+str(real_week_index):
                    Moodle_Update_list[key[4:]] = Class_Recordings[key]
                    Class_Recordings.pop(key)
            else:
                pass
            Moodle_Updater(real_week, Moodle_Update_list)


def Moodle_Updater(section_Num, update_List):
    # Get all sections of the course.
    sec = LocalGetSections(courseid)
    prev_summary = sec.getsections[int(section_Num)]['summary']
    #  Assemble the payload
    data = [{'type': 'num', 'section': 0, 'summary': '', 'summaryformat': 1, 'visible': 1,
             'highlight': 0, 'sectionformatoptions': [{'name': 'level', 'value': '1'}]}]
    for items in update_List:
        print("starting summary:", prev_summary)
        print(data[0]["summary"])
        print("--->", items)
        print("-->", update_List[items])
        # input("#1")
        # Assemble the correct summary
        summary = '<a href=' + \
            str(update_List[items]) + '>' + str(items) + '</a><br>'
        if summary in prev_summary:
            print(" --------------- ")
            print("didnt upload")
        else:
            print("  @@@@@@@@@@@@   ")
            # Assign the correct summary
            prev_summary += summary
            data[0]['section'] = section_Num
        print("sum:", data[0]["summary"])
        # input("#2")
    # Write the data back to Moodle
    data[0]['summary'] = prev_summary
    sec_write = LocalUpdateSections(courseid, data)
    sec = LocalGetSections(courseid)


def Pull_Class_Recording(URL):
    response = urlopen(URL)
    soup = BeautifulSoup(response, 'lxml')
    video = soup.find_all('div', class_='Q5txwe')
    vids = {}
    for i in reversed(video):
        vid_title = i.text.encode('ascii', 'ignore').decode()
        month = datetime.datetime.strptime(vid_title[:10], '%Y-%m-%d')
        sem_week = month.strftime("%V")
        if sem_week[0] == "0":
            sem_week = sem_week[1]
        vids[("wk" + sem_week + " recording " + vid_title[:24])
             ] = 'https://drive.google.com/file/d/' + i.parent.parent.parent.parent.attrs['data-id']
    return vids


def Local_Files_Checks():
    # Checking directory name to identify semester 1 or semester 2 [OOAPP , OOAPP2]
    if not any(d.isdigit() for d in basename(os.path.abspath("."))):
        print(basename(os.path.abspath(".")) + " - semester 1")
        sem = sem1_start_week
    else:
        print(basename(os.path.abspath(".")) + " - semester 2")
        sem = sem2_start_week
    # Scan local files
    recordings_Checklist = []
    for i in os.scandir():
        if i.is_dir() and "wk" in i.name:
            # Only files within folders containing "wk" name convention
            wk_index = ''.join([n for n in i.name if n.isdigit()])
            for f in os.scandir(i.path):
                href_link = os.path.abspath(".") + f.path.lstrip(".")
                # Only files ending with .html or .pdf are valid
                if any(n in href_link for n in [".html", ".pdf"]):
                    if ".html" in href_link:
                        soup = BeautifulSoup(open(href_link), "html.parser")
                        title = soup.find('title').string.encode(
                            'ascii', 'ignore').decode()
                        Moodle_Update(sem, sem_wk, href_link, title)
                        if "wk"+wk_index not in recordings_Checklist:
                            recordings_Checklist.append("wk"+wk_index)

                    else:
                        Moodle_Update(sem, sem_wk, href_link, f.name)
                        if "wk"+wk_index not in recordings_Checklist:
                            recordings_Checklist.append("wk"+wk_index)
    Pull_Class_Recordings(sem, Recordings_URL, recordings_Checklist)


def Moodle_Update(Sem, WeekNum, URL, Title):
    # Get all sections of the course.
    sec = LocalGetSections(courseid)
    prev_summary = sec.getsections[WeekNum]['summary']
    print(sec.getsections[1]["name"])
    # Split the section name by dash and convert the date into the timestamp, it takes the current year, so think of a way for making sure it has the correct year!
    month = parser.parse(list(sec.getsections)[WeekNum]['name'].split('-')[0])
    # Extract the week number from the start of the calendar year
    sem_week = month.strftime("%V")
    #  Assemble the payload
    data = [{'type': 'num', 'section': 0, 'summary': '', 'summaryformat': 1, 'visible': 1,
             'highlight': 0, 'sectionformatoptions': [{'name': 'level', 'value': '1'}]}]
    # Assemble the correct summary
    summary = '<a href=' + URL + '>' + Title + '</a><br>'
    if summary in prev_summary:
        # If the summary already contains this file then just skip to the next file otherwise update
        pass
    else:
        # Assign the correct summary
        data[0]['summary'] = prev_summary + ' ' + summary
        # Set the correct section number
        data[0]['section'] = WeekNum
        # Write the data back to Moodle
        sec_write = LocalUpdateSections(courseid, data)
        sec = LocalGetSections(courseid)
        print(
            "After:"+json.dumps(sec.getsections[WeekNum]['summary'], indent=4, sort_keys=True))


def Pull_Class_Recordings(Sem, URL, record_Checklist):
    response = urlopen(URL)
    soup = BeautifulSoup(response, 'lxml')
    video = soup.find_all('div', class_='Q5txwe')
    vids = {}
    for i in reversed(video):
        vid_title = i.text.encode('ascii', 'ignore').decode()
        month = datetime.datetime.strptime(vid_title[:10], '%Y-%m-%d')
        sem_week = month.strftime("%V")
        if sem_week[0] == "0":
            sem_week = sem_week[1]
        vids[("wk" + sem_week + " recording " + vid_title[:24])
             ] = 'https://drive.google.com/file/d/' + i.parent.parent.parent.parent.attrs['data-id']
    for record in record_Checklist:
        for key in list(vids):
            key_filtered = re.search("wk(\d+)", key)
            if key_filtered.group() in record:
                Moodle_Update(Sem, int(record[2:]), vids[key], key)
                vids.pop(key)
            else:
                pass


Local_Files_Check()
