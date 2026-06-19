from machine import Pin, Timer

class Blinker:
    def __init__(self, pin="LED"):
        self.led = Pin(pin, Pin.OUT)
        self.timer = Timer()

    def _blink(self, t):
        self.led.toggle()

    def on(self, freq=5):
        self.timer.init(
            freq=freq,
            mode=Timer.PERIODIC,
            callback=self._blink
        )

    def off(self):
        self.timer.deinit()
        self.led.off()
