# waveshare-epd-weather-dashboard

A weather dashboard for waveshare 7.5 inch 800x480 v2 color e-paper display.

For more info: [check out the manual](https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT_(B))

### Configuration
Modify the included config.json.dist file and save it as config.json.

## Preview
![285678937-f5164779-c662-45e1-b39f-95d5a73963a0](https://github.com/figyl/waveshare-epd-weather-dashboard/assets/73833646/05b8c71c-dc8a-4c2d-bed6-faf771bf026a)


### Cronjobs
I use cronjobs to clear the screen at 2am, and update every 15 minutes from 6am to 2am the next day.
It is important to leave the screen in sleep mode for a long period of time to preserve its longevity.

- To update the weather:
``
*/15 4-23 * * * python3 /home/figyl/waveshare-epd-weather-dashboard/e-paper/weather.py >/dev/null 2>&1
``
- To clear the screen at night:
``
0 0 * * * python3 /home/figyl/waveshare-epd-weather-dashboard/e-paper/clean.py >/dev/null 2>&1
``

Please note that it is most likely that your system uses UTC time, set your cronjobs accordingly.

### Known bugs:
- Temperature scale not in sync with line graph,
- Min/Max temperature labels go out of bounds of the line graph area,
- Icons are not evenly padded (some cause weird artifacts),
- Long weather status on the left side can go out of bounds of the current weather area,
- High percentage of rain can cause the text to be displayed out of bounds of the respective day in the weekly forecast.

If you made improvements feel free to do a pull request.
