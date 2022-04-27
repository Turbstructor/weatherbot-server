import os
import sys
import time
import datetime as dt

import openweather

def main(args):
    updated = False
    while True:
        now = dt.datetime.now()

        if now.minute % 10 == 0:
            if not updated:
                openweather.get_weather(True)
            else:
                pass # file has been updated.
        else:
            updated = False
            Time.sleep(1)




if __name__ == '__main__':
    main(sys.argv)