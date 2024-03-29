import time
import Jetson.GPIO as GPIO

class Motor():
    MICROSECONDS = 0.000001

    def __init__(self, stepPin, dirPin):
        self.stepPin = stepPin
        self.dirPin = dirPin

        self.pins = [stepPin, dirPin]

        GPIO.setmode(GPIO.BOARD)    
        GPIO.setup(self.pins, GPIO.OUT, initial=GPIO.LOW)

    def back(self):
        GPIO.output(self.dirPin, GPIO.HIGH)

    def forward(self):
        GPIO.output(self.dirPin, GPIO.LOW)

    def close(self): 
        GPIO.cleanup(self.pins)

    def step(self, delay = 3*MICROSECONDS):
        GPIO.output(self.stepPin, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(self.stepPin, GPIO.LOW)
        time.sleep(delay)