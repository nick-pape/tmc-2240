import argparse
parser = argparse.ArgumentParser(description='Manually testing the TMC 5160 SPI Interface.')
parser.add_argument('--log_level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Set the log level (default: %(default)s)')
args = parser.parse_args()

import custom_logging
custom_logging.configure_logging(args.log_level)

import logging
from TMC5160 import TMC5160

driver = TMC5160(spi_bus=0, spi_device=0)

logging.info('%s', driver)

driver.gconf.read()

driver.gconf.diag0_pushpull = True

driver.spi.write(driver.gconf.address, [0x03, 0x00, 0x00, 0x09])
driver.gconf.read()

driver.close()