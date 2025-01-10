from TMCDriver import TMCRegister, TMCSPIWrapper
from typing import Callable
from tabulate import tabulate

class GlobalConfigRegister(TMCRegister):
    def __init__(self, spi: TMCSPIWrapper, status_cb: Callable[[str, str], int]):
        super().__init__(0x00, 'gconf', spi, status_cb, [
            ['test_mode',           17, 1, bool],  # 2
            ['direct_mode',         16, 1, bool],  # 1
            ['stop_enable',         15, 1, bool],  # 8
            ['small_hysteresis',    14, 1, bool],  # 4
            ['diag1_pushpull',      13, 1, bool],  # 2
            ['diag0_pushpull',      12, 1, bool],  # 1
            ['diag1_steps_skipped', 11, 1, bool],  # 8
            ['diag1_onstate',       10, 1, bool],  # 4
            ['diag1_index',          9, 1, bool],  # 2
            ['diag1_stall',          8, 1, bool],  # 1
            ['diag0_stall',          7, 1, bool],  # 8
            ['diag0_otpw',           6, 1, bool],  # 4
            ['diag0_error',          5, 1, bool],  # 2
            ['shaft',                4, 1, bool],  # 1
            ['multistep_filt',       3, 1, bool],  # 8
            ['en_pwm_mode',          2, 1, bool],  # 4
            ['fast_standstill',      1, 1, bool],  # 2
            ['recalibrate',          0, 1, bool]   # 1
        ])


class TMC5160():
    def __init__(self, spi_bus, spi_device):
        self.__spi: TMCSPIWrapper = TMCSPIWrapper(spi_bus, spi_device)

        registers = [
            GlobalConfigRegister
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
            'status_stop_r':   bool((status >> 7) & 1),
            'status_stop_l':   bool((status >> 6) & 1),
            'position_reached':   bool((status >> 5) & 1),
            'velocity_reached':   bool((status >> 4) & 1),
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
    
    @property
    def status_stop_r(self):
        return self.__status['status_stop_r']
    
    @property
    def position_reached(self):
        return self.__status['position_reached']
    
    @property
    def velocity_reached(self):
        return self.__status['velocity_reached']
    
    @property
    def reset_flag(self):
        return self.__status['reset_flag']

    def __str__(self):
        if self.__status == None:
            return 'Status not yet read.'

        return tabulate(list(self.__status.items()), headers=['Status Flags', ''], tablefmt='pretty') + '\n\n' \
            + '\n\n'.join([str(register) for _, register in self.__registers.items()])

