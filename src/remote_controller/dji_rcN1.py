import serial
import struct
from .base_rc import BaseRemoteController, RCConnectionError

buttons = [
    ['button1', False],
    ['button2', False],
    ['button3', False],
    ['button4', False],
]

class DJIRCN1(BaseRemoteController):
    def __init__(self, port="COM4", baudrate=115200, deadzone_threshold_movement=0.1, deadzone_threshold_elevation=0.1):
        super().__init__(buttons, deadzone_threshold_movement=deadzone_threshold_movement, deadzone_threshold_elevation=deadzone_threshold_elevation)
        
        try:
            self.ser = serial.Serial(port, baudrate, timeout=0.1)
            # Enable Simulator Mode on the RC hardware immediately
            self.ser.write(bytearray.fromhex('550e04660a06eb34400624019436'))
            print(f"DJI RC-N1 connected on {port}")
        except RCConnectionError as e:
            print(f"Could not open serial port {port}: {e}")
            self.ser = None
            raise

    def _get_axis_value(self, data, index):
        """Internal helper to parse and normalize DJI 16-bit axis pairs."""
        # Unpack little-endian unsigned short
        raw = struct.unpack('<H', data[index:index+2])[0]
        
        # Normalize: DJI center is 1024. Range approx 364 to 1684 (660 throw)
        val = (raw - 1024) / 660.0
        
        # Clamp and apply deadzone from the base class
        clamped = max(min(val, 1.0), -1.0)
        return self.dead_zone(clamped)

    def update(self):
        if not self.ser:
            return False

        try:
            # Send the request for stick data (Command 0x01)
            self.ser.write(bytearray.fromhex('550d04330a06eb344006017424'))
            
            # Look for start byte
            if self.ser.read(1) == b'\x55':
                header_partial = self.ser.read(2)
                if len(header_partial) < 2: 
                    return False
                
                # Extract length from DUML header
                length = struct.unpack('<H', header_partial)[0] & 0x3FF
                payload = self.ser.read(length - 3)
                full_packet = b'\x55' + header_partial + payload

                if len(full_packet) == 38:
                    # Map the indices identified in your testing
                    self.roll     = self.dead_zone_movement(self._get_axis_value(full_packet, 13))
                    self.pitch    = self.dead_zone_movement(self._get_axis_value(full_packet, 16))
                    self.throttle = self.dead_zone_elevation(self._get_axis_value(full_packet, 19))
                    self.yaw      = self.dead_zone_movement(self._get_axis_value(full_packet, 22))
                    self.tilt     = self.dead_zone_movement(self._get_axis_value(full_packet, 25)) # Wheel mapped to tilt

                    # Buttons and Switches currently return False/0 
                    # as N1 doesn't stream them in this packet.
                    return True
            return False

        except Exception as e:
            print(f"N1 Update Error: {e}")
            return False
        
    @property
    def is_connected(self) -> bool:
        # Check if the serial object exists and the OS hasn't closed the port
        return self.serial_conn is not None and self.serial_conn.is_open

    def close(self):
        if self.ser:
            self.ser.close()





# def find_n1_port():
#     """Scans for the DJI 'For Protocol' COM port."""
#     ports = serial.tools.list_ports.comports()
#     for port in ports:
#         if "For Protocol" in port.description or "DJI" in port.description:
#             return port.device
#     return None