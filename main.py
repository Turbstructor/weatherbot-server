import requests
import json

import datetime

import sys
import getopt

import openweather as ow

def ugm3_to_ppm(ugm3 : float, pollutant : str):
    divider = {"so2" : 2.62, "co" : 1.15, "o3" : 1.96, "no2" : 1.88} # ppb and ug/m3, not ppm and ug/m3
    return ugm3 / divider[pollutant] / 1000 # ug/m3 to ppb, ppb to ppm

def pm_moving_average_24hr(pm : list, is_pm10 : bool):
    if len(pm) < 12:
        return
    else:
        pm = pm[-12:]

    M = 70 if is_pm10 else 30

    C12 = sum(pm) / len(pm)

    C4 = 0
    for Ci in pm[-4:]:
        if Ci < m:
            C4 += (Ci           / 4)
        elif 0.9 <= (Ci / C12) <= 1.7:
            C4 += ((Ci * 0.75)  / 4)
        else:
            C4 += (Ci           / 4)
    
    return ((C12 * 12) + (C4 * 12)) / 24

def calculate_CAI(so2 : float, co : float, o3 : float, no2 : float, pm10 : list, pm2_5 : list): # pm10 and pm2_5 needs at least 12 of standard-time measurement
    I = ((0, 50), (51, 100), (101, 250), (251, 500))

    BP = {}
    BP["so2"]   = ((0, 0.02),   (0.021, 0.05),  (0.051, 0.15),  (0.151, 1))     # ppm
    BP["co"]    = ((0, 2),      (2.1, 9),       (9.1, 15),      (15.1, 50))     # ppm
    BP["o3"]    = ((0, 0.03),   (0.031, 0.09),  (0.091, 0.15),  (0.151, 0.6))   # ppm
    BP["no2"]   = ((0, 0.03),   (0.031, 0.06),  (0.061, 0.2),   (0.201, 2))     # ppm
    BP["pm10"]  = ((0, 30),     (31, 80),       (81, 150),      (151, 600))     # ug/m3
    BP["pm2_5"] = ((0, 15),     (16, 35),       (36, 75),       (76, 500))      # ug/m3

    # Ip = ((I[x][1] - I[x][0]) / (BP[k][x][1] - BP[k][x][0])) * (Cp - BP[k][x][0]) + I[x][0]
    # where x is the grade index of score, and k is the kind of pollutant

    pollutant = ("so2", "co", "o3", "no2", "pm10", "pm2_5")
    lst = [so2, co, o3, no2, pm10, pm2_5]

    calculated_I = []
    bad_pollutants = 0
    worst_pollutant_index = 0
    CAI = 0

    for k in range(6):
        C = 0
        if k < 4:
            C = ugm3_to_ppm(lst[k], pollutant[k])
        else:
            C = pm_moving_average_24hr(lst[k], (pollutant[k] == "pm10"))

        x = 0
        while BP[pollutant[k]][1] < C:
            x += 1
        
        if x > 3:
            x = 3
        
        # Ip = ((I[x][1] - I[x][0]) / (BP[k][x][1] - BP[k][x][0])) * (Cp - BP[k][x][0]) + I[x][0]
        calculated_I = ((I[x][1] - I[x][0]) / (BP[pollutant[k]][x][1] - BP[pollutant[k]][x][0])) * (C - BP[pollutant[k]][x][0]) + I[x][0]

        I_level = 0
        while I[I_level][0] <= calculated_I <= I[I_level][1]:
            I_level += 1

        if I_level >= 2:
            bad_pollutants += 1
        if calculated_I[k] >= calculated_I[worst_pollutant_index]:
            worst_pollutant_index = k

    CAI = calculated_I[worst_pollutant_index]
    if bad_pollutant >= 3:
        CAI += 75
    elif bad_pollutant >= 2:
        CAI += 50
    else:
        pass

    return CAI, calculated_I

    


# def print_contents(element, tab):
    
#     for each in (element.keys() if type(element) == dict else range(len(element))):
#         if type(element[each]) == dict:
#             print(('    ' * tab) + '{} : dict'.format(each))
#             print_contents(element[each], tab + 1)
#         elif type(element[each]) == list:
#             print(('    ' * tab) + '{} : list'.format(each)) 
#             print_contents(element[each], tab + 1)
#         else:
#             print(('    ' * tab) + '{} : {}'.format(each, element[each]))

def read_weather(refresh, verbose):
    api_key = ''
    lat, lon = 36.101477, 129.390511

    req_onecall = None
    req_air = None

    if refresh:
        with open('.API_KEY', 'r') as in_file:
            api_key = in_file.readline()
            print(api_key)

        # url = 'https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&exclude={part}&appid={API key}'
        url = 'https://api.openweathermap.org/data/2.5/onecall?lat={}&lon={}&units=metric&lang=kr&appid={}'.format(lat, lon, api_key)
        req_onecall = requests.get(url)

        with open('onecall.json', 'wb') as f:
            f.write(req_onecall.content)
        
        req_onecall = req_onecall.json()

        url = 'http://api.openweathermap.org/data/2.5/air_pollution/forecast?lat={}&lon={}&appid={}'.format(lat, lon, api_key)
        req_air = requests.get(url)

        with open('air.json', 'wb') as f:
            f.write(req_air.content)

        req_air = req_air.json()

    else:
        with open('onecall.json', 'r') as f:
            req_onecall = json.loads(f.read())

        with open('air.json', 'r') as f:
            req_air = json.loads(f.read())

    if verbose:
        print(req_onecall)
        print()

        print(req_air)
        print()
            

    return req_onecall, req_air

def process_weather():
    timezone_offset = json_onecall['timezone_offset']

    # for each in json_air["list"]:
    #     # print(each.keys())
    #     ts = int(each["dt"] + timezone_offset)
    #     print(datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'), end = ' : ')
    #     print(("Good", "Fair", "Norm", "Poor", "Shit")[each["main"]["aqi"] - 1], " | [Ozone : {}, PM10 : {}, PM2.5 : {}]".format(each['components']['o3'], each['components']['pm10'], each['components']['pm2_5']))
    pass

def print_help():
    print("Usage: python3 main.py [-v] [--verbose] [-r] [--refresh]")
    print("-v / --verbose : prints byproducts")
    print("-r / --refresh : refreshes onecall.json and air.json")
    print()
    print("The program by default loads data from onecall.json and air.json if --refresh option is not given.")
    return


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "vr", ["verbose", "refresh"])
    except getopt.GetoptError as err:
        print(str(err))
        print_help()
        sys.exit(1)
 
    refresh = False
    verbose = False

    for opt, arg in opts:
        if (opt == "-r") or (opt == "--refresh"):
            refresh = True
        if (opt == "-v") or (opt == "--verbose"):
            verbose = True

    json_onecall, json_air = read_weather(refresh, verbose)

    # print_contents(json_onecall, 0)
    # print_contents(json_air, 0)
    # print(json.dumps(json_onecall, indent = 4, sort_keys = True))

    # Run the main codes here

    return

if __name__ == "__main__":
    main()