import serial
import struct
from .base_rc import BaseRemoteController, RCConnectionError

buttons = [
    ['button1', False],
    ['button2', False],
    ['button3', False],
    ['button4', False],
]

class DJIM300(BaseRemoteController):
    def __init__(self, port="COM5", baudrate=115200, deadzone_threshold=0.1):
        super().__init__(buttons, deadzone_threshold=deadzone_threshold)
        
        try:
            self.ser = serial.Serial(port, baudrate, timeout=0.1)
            # M300 specific Simulator Enable (Source 0x01, Target 0x06)
            self.ser.write(bytearray.fromhex('550E04660106EB3440062401552B'))
            print(f"DJI M300 Enterprise connected on {port}")
        except RCConnectionError as e:
            print(f"Connection Error: {e}")
            self.ser = None
            raise

    def _get_axis_value(self, data, index):
        raw = struct.unpack('<H', data[index:index+2])[0]
        # M300 uses the same 1024 center as other DJI gear
        val = (raw - 1024) / 660.0
        return self.dead_zone(max(min(val, 1.0), -1.0))

    def update(self):
        if not self.ser: return False
        try:
            # Request Stick Data for M300 (CmdSet 0x40, CmdID 0x01)
            self.ser.write(bytearray.fromhex('550D04330106EB34400601552B'))
            
            if self.ser.read(1) == b'\x55':
                header = self.ser.read(2)
                length = struct.unpack('<H', header)[0] & 0x3FF
                data = self.ser.read(length - 3)
                full = b'\x55' + header + data

                if len(full) >= 27:
                    # M300 byte offsets are usually identical to N1/N3
                    self.roll     = self._get_axis_value(full, 13)
                    self.pitch    = self._get_axis_value(full, 16)
                    self.throttle = self._get_axis_value(full, 19)
                    self.yaw      = self._get_axis_value(full, 22)
                    self.tilt     = self._get_axis_value(full, 25)
                    return True
            return False
        except:
            return False
        
    @property
    def is_connected(self) -> bool:
        # Check if the serial object exists and the OS hasn't closed the port
        return self.serial_conn is not None and self.serial_conn.is_open

    def close(self):
        if self.ser: self.ser.close()