import argparse
parser = argparse.ArgumentParser(description='Manually testing the TMC 2240 SPI Interface.')
parser.add_argument('--log_level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Set the log level (default: %(default)s)')
args = parser.parse_args()

import custom_logging
custom_logging.configure_logging(args.log_level)

import logging
from TMCDriver import TMCDriver

driver = TMCDriver(spi_bus=0, spi_device=0)

logging.info('%s', driver)

logging.info('ADC Temp: %.1f c', (driver.adc_temp.adc_temp - 2038) / 7.7)

driver.close()