import socket

class DetectionTrigger:
    """
    A lightweight, reusable UDP client to trigger AI events without 
    blocking the main execution loop.
    """
    def __init__(self, ip="127.0.0.1", port=5005):
        self.addr = (ip, port)
        # Initialize the socket once to save resources
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Performance: Set a tiny buffer so we don't clog the network stack
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1)

    def trigger(self, signal="detect"):
        """
        Fire-and-forget trigger.
        Cost: ~0.05ms. Safety: Won't crash if receiver is offline.
        """
        try:
            # We encode the string to bytes
            self.sock.sendto(signal.encode(), self.addr)
        except Exception:
            # Silently fail to protect the main loop
            pass

    def __del__(self):
        """Cleanup when the object is destroyed"""
        try:
            self.sock.close()
        except:
            pass