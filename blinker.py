from machine import Pin, Timer

class Blinker:
    def __init__(self, pin="LED", freq=4):
        self.led = Pin(pin, Pin.OUT)
        self.timer = Timer()
        self.freq = freq
        self._gpo_ring_state = 0

        if self.freq == "GPO":
            self.gpo_ring()

    def _blink(self, t):
        self.led.toggle()

    def blink(self):
        if self.freq == "GPO":
            self.gpo_ring()
        return

        self.timer.init(
            freq=self.freq,
            mode=Timer.PERIODIC,
            callback=self._blink
        )

    def _gpo_ring(self, t):
        if self._gpo_ring_state == 0:
            self.led.on()
            delay = 400
        elif self._gpo_ring_state == 1:
            self.led.off()
            delay = 200
        elif self._gpo_ring_state == 2:
            self.led.on()
            delay = 400
        else:
            self.led.off()
            delay = 2000

        self._gpo_ring_state = (self._gpo_ring_state + 1) % 4
        self.timer.init(
            mode=Timer.ONE_SHOT,
            period=delay,
            callback=self._gpo_ring
        )

    def gpo_ring(self):
        self.timer.deinit()
        self._gpo_ring_state = 0
        self._gpo_ring(None)

    def on(self):
        self.timer.deinit()
        self.led.on()

    def off(self):
        self.timer.deinit()
        self.led.off()
