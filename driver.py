import spidev
from typing import Callable

class TMCSPIWrapper:
    def __init__(self, bus, device):
        self.__spi = TMCSPIWrapper.__initialize_spi(bus, device)

    def read(self, address: hex) -> [hex, hex, hex, hex, hex]:
        # Read twice because the response will be from the last operation we sent
        data_to_send = [address, 0x00, 0x00, 0x00, 0x00]
        dummy_data = [0x00, 0x00, 0x00, 0x00, 0x00]
        
        self.__spi.xfer2(data_to_send)
        return self.__spi.xfer2(dummy_data)

    def write(self, address: hex, data: [hex, hex, hex, hex]) -> [hex, hex, hex, hex, hex]:
        self.__spi.xfer2([address | 0x80, data[0], data[1], data[2], data[3]])

    def close(self):
        self.__spi.close()

    @staticmethod
    def __initialize_spi(bus, device):
        spi = spidev.SpiDev()

        # Open SPI bus 0, device 0 (i.e., /dev/spidev0.0)
        spi.open(bus, device)

        # Set SPI speed and mode
        spi.max_speed_hz = 500000
        spi.mode = 0b11  # SPI_MODE3: CPOL = 1, CPHA = 1

        # Set MSB of the byte as the first one
        spi.lsbfirst = False

        # clear the spi buffer
        return spi

class TMCRegister():
    def __init__(self, address: hex, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        if (address == None):
            raise Exception("Must specify the register address")
        self.address: hex = address
        self.__spi: TMCSPIWrapper = spi
        self.__status_cb: Callable[[hex], None] = status_cb

        self._values = {}

        self.read()

    def read(self):
        print('Reading from ', self.address)
        data = self.__spi.read(self.address)

        formatted_data = "".join([f"{format(i, '02X')}" for i in data])
        print(f"Read from 0x{format(self.address, '02X')} : 0x{formatted_data}")

        self.__status_cb(data[0])
        self._decode(data[1:])

    def _decode(self, data: [hex, hex, hex, hex]):
        raise Exception("Not Implemented")

    def _encode(self) -> hex:
        raise Exception("Not Implemented")

    def __str__(self):
        return '\n'.join(f'[{key}] {self._values[key]}' for key in self._values)

class IOInputRegister(TMCRegister):
    def _decode(self, data: [hex, hex, hex, hex]):
        self._values['version']     = int(data[0])
        
        self._values['silicon_rev'] = int(data[1] >> 5 & 0b111)

        self._values['adc_err']     = bool(data[2] >> 7 & 0b1)
        self._values['ext_clk']     = bool(data[2] >> 6 & 0b1)
        self._values['ext_res_det'] = bool(data[2] >> 5 & 0b1)
        self._values['output']      = bool(data[2] >> 4 & 0b1)
        self._values['comp_b1_b2']  = bool(data[2] >> 3 & 0b1)
        self._values['comp_a1_a2']  = bool(data[2] >> 2 & 0b1)
        self._values['comp_b']      = bool(data[2] >> 1 & 0b1)
        self._values['comp_a']      = bool(data[2]      & 0b1)

        self._values['uart_en']     = bool(data[3] >> 6 & 0b1)
        self._values['encn']        = bool(data[3] >> 5 & 0b1)
        self._values['drv_enn']     = bool(data[3] >> 4 & 0b1)
        self._values['enca']        = bool(data[3] >> 3 & 0b1)
        self._values['encb']        = bool(data[3] >> 2 & 0b1)
        self._values['dir']         = bool(data[3] >> 1 & 0b1)
        self._values['step']        = bool(data[3]      & 0b1)

    @property
    def version(self):
        return self._values['version']

    @property
    def silicon_rev(self):
        return self._values['silicon_rev']

    @property
    def adc_err(self):
        return self._values['adc_err']

    @property
    def ext_clk(self):
        return self._values['ext_clk']

    @property
    def ext_res_det(self):
        return self._values['ext_res_det']

    @property
    def output(self):
        return self._values['output']

    @property
    def comp_b1_b2(self):
        return self._values['comp_b1_b2']

    @property
    def comp_a1_a2(self):
        return self._values['comp_a1_a2']

    @property
    def comp_b(self):
        return self._values['comp_b']

    @property
    def comp_a(self):
        return self._values['comp_a']

    @property
    def uart_en(self):
        return self._values['uart_en']

    @property
    def encn(self):
        return self._values['encn']

    @property
    def drv_enn(self):
        return self._values['drv_enn']

    @property
    def enca(self):
        return self._values['enca']

    @property
    def encb(self):
        return self._values['encb']

    @property
    def dir(self):
        return self._values['dir']

    @property
    def step(self):
        return self._values['step']

class TMCDriver():
    def __init__(self, spi_bus, spi_device):
        self.__spi: TMCSPIWrapper = TMCSPIWrapper(spi_bus, spi_device)

        self.__ioin = IOInputRegister(0x04, self.__spi, self.__set_status)

        self.__registers = [
            self.__ioin
        ]

    def read(self):
        for register in self.__registers:
            register.read()

    def close(self):
        self.__spi.close()
        self = None

    def __set_status(self, status: hex):
        self.__status = {
            'standstill':   bool((status >> 3) & 1),
            'sg2':          bool((status >> 2) & 1),
            'driver_error': bool((status >> 1) & 1),
            'reset_flag':   bool(status & 1)
        }

    @property
    def ioin(self):
        return self.__ioin

    @property
    def standstill(self):
        return self.__status['standstill']
    
    @property
    def sg2(self):
        return self.__status['sg2']

    @property
    def driver_error(self):
        return self.__status['driver_error']

    @property
    def reset_flag(self):
        return self.__status['reset_flag']

    def __str__(self):
        if self.__status == None:
            return 'Status not yet read.'
        return '\n'.join(f'[{key}] {self.__status[key]}' for key in self.__status)


import Jetson.GPIO as GPIO

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

GPIO.cleanup([STEP_PIN, DIR_PIN])
driver.close()