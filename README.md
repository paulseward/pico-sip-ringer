Terrible, vibe coded, minimal SIP stack in micropython for the raspberry pi pico-w

* Connects to wifi
* REGISTERs every 90 seconds
* Responds to OPTIONS with "200 OK"
* Responds to INVITE with  "100 Trying" and "180 Ringing" and turns on an LED
* Responds to CANCEL with  "200 OK"

TODO:
* Make the wifi connection a bit better
* Useful debug info
* Gracefully catch SIP methods we haven't implemented
* Make it less terrible/more robust
