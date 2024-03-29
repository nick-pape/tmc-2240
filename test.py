import Jetson.GPIO as GPIO
from TMCDriver import TMCDriver

STEP_PIN = 33
DIR_PIN = 31
GPIO.setmode(GPIO.BOARD)    
GPIO.setup([STEP_PIN, DIR_PIN], GPIO.OUT, initial=GPIO.LOW)

driver = TMCDriver(spi_bus=0, spi_device=0)

print('Direction:', driver.ioin.dir)
print('Standstill:', driver.standstill)

GPIO.output(DIR_PIN, GPIO.HIGH)
driver.read()

print('Direction:', driver.ioin.dir)
print('Standstill:', driver.standstill)

print()
print(driver.gconf)

GPIO.cleanup([STEP_PIN, DIR_PIN])
driver.close()