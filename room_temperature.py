import os
import json
import time
from mqtt_client import mqtt_client

## Paths config
_HERE = os.path.dirname(__file__)

## Read Settings
with open(os.path.join(_HERE, "config.json"), "r") as configfile:
    config = json.load(configfile)
mqtt_host = config["mqtt_host"]
mqtt_port = config["mqtt_port"]
mqtt_user = config["mqtt_user"]
mqtt_pass = config["mqtt_pass"]
mqtt_topic = config["mqtt_topic"]
mqtt_temp_key = config["mqtt_temp_key"]
mqtt_rH_key= config["mqtt_rH_key"]

class mqtt_temperature(mqtt_client):
    def __init__(self, host, port, user, password, topic):
        super().__init__(host=host, port=port, user=user, password=password, topic=topic)
        
    def get_temperature(self):
        if self.state != 0:
            return float(self.state[mqtt_temp_key])
        else: 
            return None
    
    def get_rH(self):
        if self.state != 0:
            return float(self.state[mqtt_rH_key])
        else: 
            return None
    

def main():
    my_temperature = mqtt_temperature(host=mqtt_host, port=mqtt_port, user=mqtt_user, password=mqtt_pass, topic=mqtt_topic)
    while(True):
        print(f"Temperatur: {my_temperature.get_temperature()}°C")
        print(f"rF: {my_temperature.get_rH()}%")
        time.sleep(5)

if __name__ == "__main__":
    main()
