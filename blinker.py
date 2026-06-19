from machine import Pin, Timer

class Blinker:
    def __init__(self, pin="LED", freq=4):
        self.led = Pin(pin, Pin.OUT)
        self.timer = Timer()
        self.freq = freq

    def _blink(self, t):
        self.led.toggle()

    def on(self):
        freq=self.freq
        self.timer.init(
            freq=freq,
            mode=Timer.PERIODIC,
            callback=self._blink
        )

    def off(self):
        self.timer.deinit()
        self.led.off()
