# # # # import serial
# # # # import struct
# # # # import time





# # # # # Set your identified port
# # # # PORT = "COM5" 
# # # # BAUD = 115200

# # # # def print_header(length):
# # # #     indices = " ".join(f"{i:02}" for i in range(length))
# # # #     print("Index:  " + indices)
# # # #     print("-" * (length * 3 + 8))

# # # # try:
# # # #     s = serial.Serial(PORT, BAUD, timeout=0.1)
# # # #     # Ping the M300 to start data flow (Source 01, Target 06)
# # # #     s.write(bytearray.fromhex('550D04330106EB34400601552B'))
    
# # # #     print(f"Sniffing M300 on {PORT}...")
# # # #     last_packet = []

# # # #     while True:
# # # #         # Send request for data
# # # #         s.write(bytearray.fromhex('550D04330106EB34400601552B'))
        
# # # #         if s.read(1) == b'\x55':
# # # #             header_partial = s.read(2)
# # # #             if len(header_partial) < 2: continue
            
# # # #             # Calculate packet length from DUML header
# # # #             length = struct.unpack('<H', header_partial)[0] & 0x3FF
# # # #             remaining_data = s.read(length - 3)
# # # #             full_packet = b'\x55' + header_partial + remaining_data
            
# # # #             # Print header once or when length changes
# # # #             if len(full_packet) != len(last_packet):
# # # #                 print_header(len(full_packet))
            
# # # #             output = []
# # # #             for i, b in enumerate(full_packet):
# # # #                 # Highlight bytes that changed since last read
# # # #                 if len(last_packet) > i and b != last_packet[i]:
# # # #                     output.append(f"[{b:02X}]")
# # # #                 else:
# # # #                     output.append(f" {b:02X} ")
            
# # # #             print(f"\rData: {''.join(output)}", end="", flush=True)
# # # #             last_packet = list(full_packet)

# # # #         time.sleep(0.02)

# # # # except serial.SerialException as e:
# # # #     print(f"Error: Could not open {PORT}. Make sure DJI Assistant is closed.")
# # # # except KeyboardInterrupt:
# # # #     print("Stopped.")
# # # # finally:
    
# # # #     if 's' in locals(): s.close()




# # # import serial
# # # import time

# # # # Use your identified port
# # # s = serial.Serial("COM5", 115200, timeout=0.1)

# # # # 1. Packet to identify the PC as a Mobile App (Source 0x01)
# # # # 2. Packet to Enter Simulator Mode
# # # # 3. Packet to Request Stick Data
# # # init_sequence = [
# # #     '550E04660106EB34000700010000', # Handshake / App ID
# # #     '550E04660106EB340A062401552B', # Enter Simulator Mode
# # #     '550D04330106EB34400601552B'  # Request Stick Data
# # # ]

# # # print("Starting M300 Enterprise Initialization...")

# # # try:
# # #     for cmd in init_sequence:
# # #         s.write(bytearray.fromhex(cmd))
# # #         time.sleep(0.2)
# # #         print(f"Sent: {cmd[:10]}...")

# # #     while True:
# # #         # Request data every loop
# # #         s.write(bytearray.fromhex('550D04330106EB34400601552B'))
        
# # #         if s.in_waiting > 0:
# # #             b = s.read(1)
# # #             if b == b'\x55':
# # #                 header = s.read(2)
# # #                 length = (header[0] | (header[1] << 8)) & 0x3FF
# # #                 payload = s.read(length - 3)
# # #                 full = b'\x55' + header + payload
                
# # #                 # Format for display
# # #                 hex_str = ' '.join(f'{x:02X}' for x in full)
# # #                 print(f"\r[{len(full)} bytes] {hex_str[:60]}...", end="")
        
# # #         time.sleep(0.01)

# # # except KeyboardInterrupt:
# # #     print("Stopping...")
# # # finally:
# # #     s.close()


# # import serial
# # import struct
# # import time
# # import os

# # PORT = "COM5"
# # BAUD = 115200

# # def clear():
# #     os.system('cls' if os.name == 'nt' else 'clear')

# # try:
# #     s = serial.Serial(PORT, BAUD, timeout=0.1)
    
# #     # Store the latest packets
# #     packets = {14: None, 77: None, "other": None}
    
# #     print(f"Listening on {PORT}... Move sticks/switches to see if bytes change.")

# #     while True:
# #         # Request data (The M300 poll command)
# #         s.write(bytearray.fromhex('550D04330106EB34400601552B'))
        
# #         if s.in_waiting > 0:
# #             char = s.read(1)
# #             if char == b'\x55':
# #                 header = s.read(2)
# #                 if len(header) < 2: continue
# #                 length = (header[0] | (header[1] << 8)) & 0x3FF
# #                 payload = s.read(length - 3)
# #                 full = b'\x55' + header + payload
                
# #                 # Categorize the packet
# #                 p_len = len(full)
# #                 if p_len in [14, 77]:
# #                     packets[p_len] = full
# #                 else:
# #                     packets["other"] = full

# #                 # Update Display
# #                 print("\033[H", end="") # Move cursor to top
# #                 print(f"=== M300 PACKET MONITOR [PORT: {PORT}] ===")
                
# #                 # Print 14-byte Heartbeat
# #                 if packets[14]:
# #                     hex_14 = ' '.join(f'{x:02X}' for x in packets[14])
# #                     print(f"[14 Byte Heartbeat]:{hex_14}")
                
# #                 # Print 77-byte System Status
# #                 if packets[77]:
# #                     hex_77 = ' '.join(f'{x:02X}' for x in packets[77])
# #                     # Split into lines for readability
# #                     print(f"[77 Byte Status]:")
# #                     print(hex_77[:57]) # First part
# #                     print(hex_77[57:]) # Second part

# #                 # Print if a new packet type appears (the stick data we want!)
# #                 if packets["other"]:
# #                     p_other = packets["other"]
# #                     print(f"\033[92m[NEW PACKET DETECTED - {len(p_other)} Bytes]:\033[0m")
# #                     print(' '.join(f'{x:02X}' for x in p_other))

# #         time.sleep(0.01)

# # except KeyboardInterrupt:
# #     print("Stopped.")
# # finally:
# #     s.close()




# import serial
# import time

# s = serial.Serial("COM5", 115200, timeout=0.1)

# # M300 Activation Pings
# s.write(bytearray.fromhex('550E04660106EB34000700010000'))
# s.write(bytearray.fromhex('550E04660106EB340A062401552B'))

# try:
#     while True:
#         # Keep asking for sticks
#         s.write(bytearray.fromhex('550D04330106EB34400601552B'))
        
#         if s.in_waiting > 0:
#             char = s.read(1)
#             if char == b'\x55':
#                 header = s.read(2)
#                 if len(header) < 2: continue
#                 length = (header[0] | (header[1] << 8)) & 0x3FF
#                 payload = s.read(length - 3)
#                 full = b'\x55' + header + payload
                
#                 # Simple raw print: [Length] HexData
#                 if len(full) == 14:
#                     print(f"[{len(full):02d}] {' '.join(f'{x:02X}' for x in full)}")
        
#         time.sleep(0.01)
# except KeyboardInterrupt:
#     s.close()




import serial
import time

s = serial.Serial("COM5", 115200, timeout=0.1)

# This is the "Master Activation" for M300 Enterprise
# It tells the RC: "I am a high-priority SDK device, send me everything."
master_ping = bytearray.fromhex('550E04660106EB34000700010000')
enable_sticks = bytearray.fromhex('550D04330106EB34400601552B')

print("Sending M300 Force-Enable...")
s.write(master_ping)
time.sleep(0.5)

try:
    while True:
        # Polling command
        s.write(enable_sticks)
        
        if s.in_waiting > 0:
            char = s.read(1)
            if char == b'\x55':
                header = s.read(2)
                length = (header[0] | (header[1] << 8)) & 0x3FF
                payload = s.read(length - 3)
                full = b'\x55' + header + payload
                
                # Check the 77-byte packet specifically
                if len(full) == 77:
                    # Monitor the bytes at index 14, 15, 16, 17
                    # In M300 Enterprise, sticks often shift here
                    sticks_segment = full[14:30]
                    hex_seg = ' '.join(f'{x:02X}' for x in sticks_segment)
                    print(f"\rStick Segment [14-30]: {hex_seg}", end="")
        
        time.sleep(0.01)
except KeyboardInterrupt:
    s.close()