import logging
import spidev
from tabulate import tabulate
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
    READONLY = 0x01

    def __init__(self, address: hex, name: str, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int], value_map):
        if (address == None):
            raise Exception("Must specify the register address")
        self.address: hex = address
        self.name: str = name

        self.__spi: TMCSPIWrapper = spi
        self.__status_cb: Callable[[hex], None] = status_cb

        self._values = {}
        self._value_map = value_map

        for name, _, _, _, *optional in self._value_map:
            getter = lambda self, name=name: self._values[name]
    
            prop = property(getter)

            if (len(optional) == 0 or optional[0] != TMCRegister.READONLY):
                setter = lambda self, value, name=name: self._values.__setitem__(name, value)
                prop = prop.setter(setter)

            setattr(self.__class__, name, prop)

        self.read()

    def read(self):
        data = self.__spi.read(self.address)

        formatted_data = "".join([f"{format(i, '02X')}" for i in data])
        logging.debug(f"Read from 0x{format(self.address, '02X')} : 0x{formatted_data}")

        self.__status_cb(data[0])
        self._decode(data[1:])

    def _decode(self, data: [hex, hex, hex, hex]):
        data_word = (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
        
        for name, start, length, T in self._value_map:
            mask = (1 << length) - 1
            self._values[name] = T(data_word >> (start - length + 1) & mask)

    def _encode(self) -> hex:
        raise Exception("Not Implemented")

    def __str__(self):
        return tabulate(list(self._values.items()), headers=[self.name, ''], tablefmt='pretty')

class GlobalConfigRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x00, 'gconf', spi, status_cb, [
            ['direct_mode',      16, 1, bool],
            ['stop_enable',      15, 1, bool],
            ['small_hysteresis', 14, 1, bool],
            ['diag1_pushpull',   13, 1, bool],
            ['diag0_pushpull',   12, 1, bool],
            ['diag1_onstate',    10, 1, bool],
            ['diag1_index',       9, 1, bool],
            ['diag1_stall',       8, 1, bool],
            ['diag0_stall',       7, 1, bool],
            ['diag0_otpw',        6, 1, bool],
            ['diag0_error',       5, 1, bool],
            ['shaft',             4, 1, bool],
            ['multistep_filt',    3, 1, bool],
            ['en_pwm_mode',       2, 1, bool],
            ['fast_standstill',   1, 1, bool]
        ])

class GlobalStatusRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x01, 'gstat', spi, status_cb, [
            ['vm_uvlo',        4, 1, bool],
            ['register_reset', 3, 1, bool],
            ['uv_cp',          2, 1, bool],
            ['drv_err',        1, 1, bool],
            ['reset',          0, 1, bool]
        ])

class IOInputRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x04, 'ioin', spi, status_cb, [
            ['version',     31, 8, int,  TMCRegister.READONLY],
            ['silicon_rev', 18, 3, int,  TMCRegister.READONLY],
            ['adc_err',     15, 1, bool, TMCRegister.READONLY],
            ['ext_clk',     14, 1, bool, TMCRegister.READONLY],
            ['ext_res_det', 13, 1, bool, TMCRegister.READONLY],
            ['output',      12, 1, bool],
            ['comp_b1_b2',  11, 1, bool, TMCRegister.READONLY],
            ['comp_a1_a2',  10, 1, bool, TMCRegister.READONLY],
            ['comp_b',      9,  1, bool, TMCRegister.READONLY],
            ['comp_a',      8,  1, bool, TMCRegister.READONLY],
            ['uart_en',     6,  1, bool, TMCRegister.READONLY],
            ['encn',        5,  1, bool, TMCRegister.READONLY],
            ['drv_enn',     4,  1, bool, TMCRegister.READONLY],
            ['enca',        3,  1, bool, TMCRegister.READONLY],  
            ['encb',        2,  1, bool, TMCRegister.READONLY],
            ['dir',         1,  1, bool, TMCRegister.READONLY],
            ['step',        0,  1, bool, TMCRegister.READONLY]
        ])

class DriveConfigRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x0A, 'drv_conf', spi, status_cb, [
            ['slope_control', 5, 2, int],
            ['current_range', 1, 2, int]
        ])

class GlobalScalerRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x0B, 'global_scaler', spi, status_cb, [
            ['globalscaler', 7, 8, int]
        ])

class CurrentRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x10, 'ihold_irun', spi, status_cb, [
            ['irundelay',  27, 4, int],
            ['iholddelay', 19, 4, int],
            ['irun',       12, 5, int],
            ['irundelay',   4, 5, int]
        ])

class PowerdownRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x11, 'tpowerdown', spi, status_cb, [
            ['tpowerdown',  7, 8, int]
        ])

class TStepRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x12, 'tstep', spi, status_cb, [
            ['tstep',  19, 20, int, TMCRegister.READONLY]
        ])

class TPWMThresholdRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x13, 'tpwmthrs', spi, status_cb, [
            ['tpwmthrs',  19, 20, int]
        ])

class TCoolThreshold(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x14, 'tcoolthrs', spi, status_cb, [
            ['tpwmthrs',  19, 20, int]
        ])

class THighRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x15, 'thigh', spi, status_cb, [
            ['thigh',  19, 20, int]
        ])

class DirectModeRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x2D, 'direct_mode', spi, status_cb, [
            ['direct_coil_b',  24, 9, int],
            ['direct_coil_a',  8, 9, int],
        ])

class EncoderModeRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x38, 'encmode', spi, status_cb, [
            ['enc_sel_decimal',  10, 1, bool],
            ['clr_enc_x',         8, 1, bool],
            ['pos_neg_edge',      7, 2, int],
            ['clr_once',          5, 1, bool],
            ['clr_cont',          4, 1, bool],
            ['ignore_ab',         3, 1, bool],
            ['pol_n',             2, 1, bool],
            ['pol_b',             1, 1, bool],
            ['pol_a',             1, 1, bool],
        ])

class XEncoderRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x39, 'x_enc', spi, status_cb, [
            ['x_enc',  31, 32, int]
        ])

class EncoderConstantRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x3A, 'enc_const', spi, status_cb, [
            ['enc_const',  31, 32, int] # or float, based on enc_sel_decimal
        ])

class EncoderStatusRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x3B, 'enc_status', spi, status_cb, [
            ['n_event',  0, 1, bool]
        ])

class EncoderLatchRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x3C, 'enc_latch', spi, status_cb, [
            ['enc_const',  31, 32, int, TMCRegister.READONLY]
        ])

class ADCRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x50, 'adc_vsupply_ain', spi, status_cb, [
            ['adc_ain',      28, 13, int, TMCRegister.READONLY],
            ['adc_vsupply',  12, 13, int, TMCRegister.READONLY],
        ])

class ADCTempRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x51, 'adc_temp', spi, status_cb, [
            ['adc_temp',     12, 13, int, TMCRegister.READONLY],
        ])

class OvertempOvervoltageRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x52, 'otw_ov_vth', spi, status_cb, [
            ['overtempprewarning_vth', 28, 13, int],
            ['overvoltage_vth', 12, 13, int]
        ])

class MicrostepCounterRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x6A, 'mscnt', spi, status_cb, [
            ['mscnt', 9, 10, int, TMCRegister.READONLY],
        ])

class MicrostepCurrentRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x6B, 'mscuract', spi, status_cb, [
            ['cur_a', 24, 9, int, TMCRegister.READONLY],
            ['cur_b', 8, 9, int, TMCRegister.READONLY],
        ])

class ChopperConfigRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x6C, 'chopconf', spi, status_cb, [
            ['diss2vs',     31, 1, bool],
            ['diss2g',      30, 1, bool],
            ['dedge',       29, 1, bool],
            ['intpol',      28, 1, bool],
            ['mres',        27, 4, int],
            ['tpfd',        23, 4, int],
            ['vhighchm',    19, 1, bool],
            ['vhighfs',     18, 1, bool],
            ['tbl',         16, 2, int],
            ['chm',         14, 1, bool],
            ['disfdcc',     12, 1, bool],
            ['fd3',         11, 1, bool],
            ['hend_offset', 10, 4, int],
            ['hstrt_tfd210', 6, 3, int],
            ['toff',         3, 4, int],
        ])

class CoolstepConfigRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x6D, 'coolconf', spi, status_cb, [
            ['sfilt',  24, 1, bool],
            ['sgt',    22, 7, int],
            ['seimin', 15, 1, bool],
            ['sedn',   14, 2, int],
            ['semax',  11, 4, int],
            ['seup',    6, 2, int],
            ['semin',   3, 4, int]
        ])

class DriveStatusRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x6F, 'drv_status', spi, status_cb, [
            ['stst',       31, 1, bool, TMCRegister.READONLY],
            ['olb',        30, 1, bool, TMCRegister.READONLY],
            ['ola',        29, 1, bool, TMCRegister.READONLY],
            ['s2gb',       28, 1, bool, TMCRegister.READONLY],
            ['s2ga',       27, 1, bool, TMCRegister.READONLY],
            ['optw',       26, 1, bool, TMCRegister.READONLY],
            ['ot',         25, 1, bool, TMCRegister.READONLY],
            ['stallguard', 24, 1, bool, TMCRegister.READONLY],
            ['cs_actual',  20, 5, int,  TMCRegister.READONLY],
            ['fsactive',   15, 1, bool, TMCRegister.READONLY],
            ['stealth',    14, 1, bool, TMCRegister.READONLY],
            ['s2vsb',      13, 1, bool, TMCRegister.READONLY],
            ['s2vsa',      12, 1, bool, TMCRegister.READONLY],
            ['sg_result',   9, 10, int, TMCRegister.READONLY],
        ])

class PWMConfigRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x70, 'pwmconf', spi, status_cb, [
            ['pwm_lim',            31, 4, int],
            ['pwm_reg',            27, 4, int],
            ['pwm_dis_reg_stst',   24, 1, bool],
            ['pwm_meas_sd_enable', 23, 1, bool],
            ['freewheel',          24, 2, int],
            ['pwm_autograd',       19, 1, bool],
            ['pwm_autoscale',      18, 1, bool],
            ['pwm_freq',           17, 2, int],
            ['pwm_grad',           15, 8, int],
            ['pwm_ofs',             7, 8, int],
        ])

class PWMScaleRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x71, 'pwm_scale', spi, status_cb, [
            ['pwm_scale_auto', 24, 9, int, TMCRegister.READONLY],
            ['pwm_scale_sum',  9, 10, int, TMCRegister.READONLY],
        ])

class PWMAutoRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x72, 'pwm_auto', spi, status_cb, [
            ['pwm_grad_auto', 23, 8, int, TMCRegister.READONLY],
            ['pwm_ofs_auto',   7, 8, int, TMCRegister.READONLY],
        ])

class StallguardThresholdRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x74, 'sg4_thrs', spi, status_cb, [
            ['sg_angle_offset', 9, 1, bool],
            ['sg4_filt_en',     8, 1, bool],
            ['sf4_thrs',        7, 8, int]
        ])

class StallguardResultRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x75, 'sg4_result', spi, status_cb, [
            ['sg4_result', 9, 10, int, TMCRegister.READONLY],
        ])

class StallguardIndependentRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x76, 'sg4_ind', spi, status_cb, [
            ['sg4_ind_3', 31, 8, int, TMCRegister.READONLY],
            ['sg4_ind_2', 23, 8, int, TMCRegister.READONLY],
            ['sg4_ind_1', 15, 8, int, TMCRegister.READONLY],
            ['sg4_ind_0',  7, 8, int, TMCRegister.READONLY],
        ])

class TMCDriver():
    def __init__(self, spi_bus, spi_device):
        self.__spi: TMCSPIWrapper = TMCSPIWrapper(spi_bus, spi_device)

        registers = [
            GlobalConfigRegister,
            GlobalStatusRegister,
            IOInputRegister,
            DriveConfigRegister,
            GlobalScalerRegister,
            CurrentRegister,
            PowerdownRegister,
            TStepRegister,
            TPWMThresholdRegister,
            TCoolThreshold,
            THighRegister,
            DirectModeRegister,
            EncoderModeRegister,
            XEncoderRegister,
            EncoderConstantRegister,
            EncoderStatusRegister,
            EncoderLatchRegister,
            ADCRegister,
            ADCTempRegister,
            OvertempOvervoltageRegister,
            MicrostepCounterRegister,
            MicrostepCurrentRegister,
            ChopperConfigRegister,
            CoolstepConfigRegister,
            DriveStatusRegister,
            PWMConfigRegister,
            PWMScaleRegister,
            PWMAutoRegister,
            StallguardThresholdRegister,
            StallguardResultRegister,
            StallguardIndependentRegister
        ]

        self.__registers = {}

        for RegisterClass in registers:
            register = RegisterClass(self.__spi, self.__set_status)
            name = register.name
            self.__registers[name] = register
            getter = lambda self, name=name: self.__registers[name]
            setattr(self.__class__, name, property(getter))

    def read(self):
        for name in self.__registers:
            self.__registers[name].read()

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

        return tabulate(list(self.__status.items()), headers=['Status Flags', ''], tablefmt='pretty') + '\n\n' \
            + '\n\n'.join([str(register) for _, register in self.__registers.items()])

