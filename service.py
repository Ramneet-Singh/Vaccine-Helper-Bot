import requests
import json
import datetime as datetime

BASE_URL = 'https://cdn-api.co-vin.in/api/v2/'
# https: // cdn-api.co-vin. in /api/v2/admin/location/states


def getStates():
    url = f'{BASE_URL}admin/location/states'
    response = requests.get(url)
    data = (response.json()['states'])
    tempDistrictDict = {}
    for state in data:
        url = f'{BASE_URL}admin/location/districts/{state["state_id"]}'
        districtsList = requests.get(url).json()['districts']
        # print(districtsList)
        tempDistrictDict[state["state_id"]] = districtsList
    print(json.dumps(tempDistrictDict))


def getVaccineAvailability(param, byPin, is18Plus):
    if byPin:
        url1 = f'{BASE_URL}appointment/sessions/public/findByPin?pincode={param}&date={datetime.date.today().strftime("%d-%m-%Y")}'
        url2 = f'{BASE_URL}appointment/sessions/public/findByPin?pincode={param}&date={(datetime.date.today() + datetime.timedelta(days=1)).strftime("%d-%m-%Y")}'
    else:
        url1 = f'{BASE_URL}appointment/sessions/public/findByDistrict?district_id={param}&date={datetime.date.today().strftime("%d-%m-%Y")}'
        url2 = f'{BASE_URL}appointment/sessions/public/findByDistrict?district_id={param}&date={(datetime.date.today() + datetime.timedelta(days=1)).strftime("%d-%m-%Y")}'

    data1 = requests.get(url1).json()
    data2 = requests.get(url2).json()

    availableSessions = []
    for session in data1['sessions']:
        if(session["available_capacity"] > 0 and (session["min_age_limit"] == 18 or (not is18Plus))):
            availableSessions.append(session)
    for session in data2['sessions']:
        if(session["available_capacity"] > 0 and (session["min_age_limit"] == 18 or (not is18Plus))):
            availableSessions.append(session)

    return availableSessions
