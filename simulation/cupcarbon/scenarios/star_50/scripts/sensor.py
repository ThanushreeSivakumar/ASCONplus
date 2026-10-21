# CupCarbon IoT Python Script for Sensor Node
from cup_functions import *

while True:
    cup_send("DATA", "0 1")
    cup_wait(1)
