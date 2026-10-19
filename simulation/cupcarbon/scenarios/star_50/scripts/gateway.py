# CupCarbon IoT Python Script for Gateway
from cup_functions import *

while True:
    msg = cup_read()
    cup_print(msg)
