
import serial
import threading
import time
import regex
from typing import List, Tuple
import serial.tools.list_ports

err_pattern = regex.compile(r'E(-1|[0-9]{3})')
BAUDRATE_SERIAL_DEF  = 115200   # Fixed baudrate constant - default
BAUDRATE_SERIAL_FAST = 460800
TIMEOUT_SERIAL = 3    # Fixed timeout constant
TERMINATION_SERIAL = '\r\n'

"""
    SerialController class takes control over the given COM and it's principle works around send message / wait message.
    The messages must implement the termination string to work
"""
class SerialController:
    BAUDRATE = BAUDRATE_SERIAL_DEF   # Constant baudrate
    TIMEOUT  = TIMEOUT_SERIAL        # Constant timeout in seconds
    received_messages : List[str]
    
    def __init__(self, port: str, termination_str: str = TERMINATION_SERIAL):
        self.port = port  # The COM port (e.g., 'COM7')
        self.ser = None  # The serial connection object
        self.received_messages = []  # List to store received messages
        self._listening_thread = None  # Thread for listening to the serial port
        self._listening = False  # Flag to control the listening loop
        self.termination_str = termination_str.encode()  # Encode termination string for sending

    def open(self):
        """Opens the serial port and starts listening for messages."""
        self.ser = serial.Serial(self.port, baudrate=self.BAUDRATE, timeout=self.TIMEOUT)
        self._listening = True
        self._listening_thread = threading.Thread(target=self._listen)
        self._listening_thread.start()

    def close(self):
        """Closes the serial port and stops listening for messages."""
        # print('close COM')
        self._listening = False
        if self._listening_thread:
            self._listening_thread.join()
        if self.ser and self.ser.is_open:
            self.ser.close()
    
    def flush(self) :
        if len(self.received_messages) > 0 :
            self.received_messages = []

    def send_message(self, message: str, response_timeout: float = 2.0) :
        """Sends a message through the serial port and waits for a response.
        
        Returns the response message as a string.
        """
        if not self.ser or not self.ser.is_open:
            raise Exception('Serial port is not open')
        
        # Send the message
        self.ser.write(f'{message}{self.termination_str.decode()}'.encode())

    
    def read_message(self) -> str:
        """Read a message from the received messages list.
        
        Returns the message as a string.
        """
        if not self.ser or not self.ser.is_open:
            raise Exception('Serial port is not open')
        
        response = None
        
        # Check if there is messages stored
        if len(self.received_messages) > 0 :
            response = self.received_messages.pop(0)
        
        return response
        

    def _listen(self):
        """Internal method to continuously listen for incoming messages."""
        while self._listening :
            if self.ser.in_waiting > 0:
                # Use read_until to read until the termination string is found
                message = self.ser.read_until(self.termination_str).decode(errors='ignore').strip()
                if message :  # Check if message is not just whitespace
                        self.received_messages.append(message)
            time.sleep(0.05)  # Small delay to prevent busy-waiting

# Variables:
# - port: str  # The COM port to use (e.g., 'COM7')
# - ser: serial.Serial  # The serial connection object
# - received_messages: list[str]  # List to store received messages
# - _listening_thread: threading.Thread  # Thread for listening to the serial port
# - _listening: bool  # Flag to control the listening loop
# - termination_str: bytes  # Termination string for messages encoded to bytes

# Methods:
# - __init__(port: str, termination_str: str) -> None
#   # Initializes the SerialController with a COM port and termination string.
#   # Takes 'port' as a parameter (the COM port to use) and 'termination_str' as a parameter (the string to terminate messages).
#
# - open() -> None
#   # Opens the serial port and starts listening for messages.
#   # No parameters.
#
# - close() -> None
#   # Closes the serial port and stops listening for messages.
#   # No parameters.
#
# - send_message(message: str, response_timeout: float) -> str
#   # Sends a message through the serial port and waits for a response.
#   # Takes 'message' as a parameter (the message to send) and 'response_timeout' (the time to wait for a response).
#   # Returns the last response message as a string or None if no response is received within the timeout.
#
# - read_message() -> str
#   # Read a message from the received messages list.
#   # No parameters.
#   # Returns the last response message as a string or None if list is empty.
#
# - _listen() -> None
#   # Internal method to continuously listen for incoming messages.
#   # No parameters.


# Class that control the AT shell communication (sending correct AT commands with given parameters)
class ATShell :
    RESPONSE_TIMEOUT : float = 3
    port : SerialController
    test :list[str]

    def __init__(self, s : SerialController) :
        self.port = s
        self.RESPONSE_TIMEOUT = 3
        self.test = []

    def sendCommand(self, cmd : str, args : str = '' , c_timeout : float = RESPONSE_TIMEOUT) -> Tuple[bool, List[str]] : 
        ret:list[str] = []
        msg : str
        if not ('AT' in cmd[:2] ) :
            msg = 'AT+' + cmd
        else :
            msg = cmd
        
        if args != '' :
            msg += '=' + args

        self.port.flush()

        self.port.send_message(msg + TERMINATION_SERIAL, 1)
        
        # Record the current time
        start_time = time.monotonic()

        # Wait for a response that was received after the message was sent
        tmp = None
        response = ''
        while tmp == None and (time.monotonic() - start_time) < c_timeout :
            tmp = self.port.read_message()
            if tmp != None :
                # print(tmp)
                self.test.append(tmp)
                if regex.match(err_pattern, tmp) :
                    raise Exception(f'wrong msg {msg} error: {tmp}')
                elif tmp == 'O' :
                    ret.append(response)
                    break
                elif not (msg in tmp) :
                    ret.append(tmp)
                    #response += tmp
                tmp = None
            time.sleep(0.001)  # Small delay to prevent busy-waiting
        if (time.monotonic() - start_time) < c_timeout :
            return ( (len(ret) > 0), ret )
        else :
            return ( False, ret )
    


