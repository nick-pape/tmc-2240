import argparse
parser = argparse.ArgumentParser(description='Manually testing the TMC 2240 SPI Interface.')
parser.add_argument('--log_level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Set the log level (default: %(default)s)')
args = parser.parse_args()

import custom_logging
custom_logging.configure_logging(args.log_level)

import logging
from TMCDriver import TMCDriver
from Motor import Motor

driver = TMCDriver(spi_bus=0, spi_device=0)
motor = Motor(stepPin=33, dirPin=31)

logging.info('%s', driver)

MICROSTEP = 4
REVOLUTION = 200 * 90 * MICROSTEP


motor.forward()
for i in range(REVOLUTION):
    if (i%(REVOLUTION//10) == 0):
        logging.info('TSTEP: %.1f', driver.tstep.tstep)
        driver.tstep.read()
    motor.step()

motor.close()
driver.close()