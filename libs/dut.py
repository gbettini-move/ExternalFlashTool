from libs.serial_handler import SerialController, ATShell
import serial.tools.list_ports

import time

from tqdm import trange
from hashlib import sha256
from typing import List, Tuple

BYTES_PER_PAGE   = 2115  # Counting also O\r\n [2112+3]
MESSAGE_START_ID = 7 # 07 in hex

class recordInfo:
    done: bool
    acquired: int

# DUT control class, it perform all the communications with DUT
class DUT :
    serialP : SerialController
    AT : ATShell

    dev_sn : str
    deveui : str
    appkey : str
    appeui : str
    mam_fw : str
    mic_fw : str
    DUT_SIMULATION : bool


    def __init__(self, serial_test : SerialController, dutSimulation : bool = False) :
        self.serialP = serial_test
        self.AT = ATShell(serial_test)

        self.dev_sn = ''
        self.deveui = ''
        self.appkey = ''
        self.appeui = ''
        self.mam_fw = ''
        self.mic_fw = ''
        self.DUT_SIMULATION = dutSimulation

    def resetInfo(self) :
        self.dev_sn = ''
        self.deveui = ''
        self.appkey = ''
        self.appeui = ''
        self.mic_fw = ''
        self.mam_fw = ''

    # Enter AT mode sending AT+TST
    def ATmode(self) :
        ok : bool = False
        idx : int = 0
        self.serialP.flush()
        while idx < 5 and not ok:
            time.sleep(0.5)
            idx += 1
            ok = self.AT.sendCommand('TST')[0]
        if not ok :
            raise RuntimeError('DUT-ATmode - FAIL')
        print('DUT -> TST')
    
    # Get ACTI from DUT
    def getACTI(self) -> bool :
        ok : bool
        ret : list[str]
        ok, ret = self.AT.sendCommand('ACTI')
        if not (ok and len(ret) > 0) :
            raise RuntimeError('DUT-getACTI - FAIL')
        print(f"DUT -> ACTI {ret[0]}")
        return (ret[0] == '1')

    # Get SN from the device
    def getSN(self) -> str :
        ok : bool
        ret : list[str]
        ok, ret = self.AT.sendCommand('SN')
        if not (ok and len(ret) > 0) :
            raise RuntimeError('DUT-getSN - FAIL')
        print(f'DUT -> SN {ret[0]}')
        return ret[0]
    
    # Get UID from the device
    def getUID(self) -> str :
        ok : bool
        ret : list[str]
        ok, ret = self.AT.sendCommand('UID')
        if not (ok and len(ret) > 0) :
            raise RuntimeError('DUT-getUID - FAIL')
        print(f'DUT -> UID {ret[0]}')
        return ret[0]

    
    # Erase ext flash
    def eraseExtFlash(self) :
        if not (self.AT.sendCommand('FLSDEL', c_timeout=35)[0]) :
            raise RuntimeError('DUT-eraseExtFlash - FAIL')
        print('DUT -> FLSDEL')
    
    # Set APPEUI and Key to the device
    def getAPPEUIandKEY(self) -> list[str] :
        ok : bool
        ret : list[str]
        ok, ret = self.AT.sendCommand('KEYS')
        if not (ok and len(ret) > 0) :
            raise RuntimeError('DUT-getAPPEUIandKEY - FAIL')
        ret = [ ret[0], ret[1].split()[0], ret[2].split()[0] ]
        print(f'DUT -> KEYS={ret[0]};{ret[1]};{ret[2]}')
        return ret
    
    # Get FW hash
    def getFWHASH(self) -> str :
        ok : bool
        ret : list[str]
        ok, ret = self.AT.sendCommand('FWHASH')
        if not (ok and len(ret) > 0) :
            raise RuntimeError('DUT-getFWHASH - FAIL')
        print(f'DUT -> FW-FWHASH={ret[0]}')
        return ret[0]
    
    # Get FW version
    def getFWVERSION(self) -> str :
        ok : bool
        ret : list[str]
        ok, ret = self.AT.sendCommand('FWVER')
        if not (ok and len(ret) > 0) :
            raise RuntimeError('DUT-getFWVERSION - FAIL')
        print(f'DUT -> FW-VERSION={ret[0]}')
        return ret[0]
    
    # Read page content
    def dumpPage(self, page: str, filename : str, skip_counter : int, c_timeout : float = 2, max_attempts: int = 3) -> tuple[bool, int]:
        """
        Read one page of external flash memory and append the content in:
            - <filname>.bin as binary
            - <filname>.txt as hex

        Return:
            bool: True when it finds a blank page
            int:  Takes the count of the number of pages that has been skipped 'couse of multiple timeout error (skip_counter += 1)
        """
        cmd = f"AT+EFLASHRP={page};0;840\r\n"
        len_cmd = len(cmd)
        EXPECTED_RESPONSE = BYTES_PER_PAGE + len_cmd

        for attempt in range(1, max_attempts + 1):
            self.serialP.ser.flushInput()
            self.serialP.ser.timeout = 0.5  # Short timeout for read()

            buffer = b""
            start_time = time.monotonic()

            # send command
            self.serialP.ser.write(cmd.encode("utf-8"))

            # Read page until you have read it all or the timeout occurs
            while len(buffer) < EXPECTED_RESPONSE and (time.monotonic() - start_time) < c_timeout:
                remaining = EXPECTED_RESPONSE - len(buffer)
                chunk = self.serialP.ser.read(remaining)
                if chunk:
                    buffer += chunk

            if len(buffer) < EXPECTED_RESPONSE:
                print(f"WARN: Timeout (attempt {attempt}/{max_attempts}) | Received {len(buffer)}/{EXPECTED_RESPONSE} bytes")
                if attempt < max_attempts:
                    time.sleep(0.1)  # short delay before retry
                    continue
                else:
                    # last attempt failed -> increment skip_counter to see the next page
                    skip_counter += 1
                    return False, skip_counter

            # if everything good
            cln_buff = buffer[len_cmd:len_cmd + (BYTES_PER_PAGE - 3)]  # Remove cmd and O\r\n

            if cln_buff and cln_buff[0] == MESSAGE_START_ID:  # check if the page is written or blank
                # Append if is written
                with open(filename + ".bin", 'ab') as rawfile:
                    rawfile.write(cln_buff)
                hex_page = cln_buff.hex()
                with open(filename + ".txt", "a") as hexfile:
                    hexfile.write(hex_page)
                return False, skip_counter  # page has been read correctly
            else:
                # Blank page detected
                return True, skip_counter


    
    # read all the MIC memory to bin file (recording data)
    # Function do not use the AT class bc it's complicated -> directly use the serial
    def dumpMicMemory(self, filename : str) :

        self.serialP.ser.flushInput()
        self.serialP.ser.timeout = 5
        self.serialP.ser.write(b"AT+TST:rd")
        msg = self.serialP.ser.read_until(b"O\r\n")
        buffer = b""
        if b"O\r\n" in msg :
            while True:
                last_received_time = time.monotonic()
                chunk = self.serialP.ser.read(512)  # Read in chunks
                buffer += chunk
                # No data received, check if transmission has ended
                if (time.monotonic() - last_received_time) > 0.9:
                    break  # Exit the loop
        # buffer = buffer[12:-10]
        buffer = buffer[12:-13]
        print(f'Data recv len {len(buffer)}')
        with open(filename, 'bw') as rawfile:
            rawfile.write(buffer)


    # Perform the programming of MIC mcu with the old method (flash mass erase, sending each page to MAM and the MAM perform the programming)
    # it's more time consuming than the bridge programming style
    def flashMICFirmwareOLD(self, fw_mic : str, mic_fw_hash : str) :
        print('Loading Firmware MIC...')
        with open(fw_mic, 'rb') as f:
            data = f.read()
        if len(data) > 0x20000:
            raise RuntimeError("Firmware too big")
        
        datapadded = data + b'\xff' * (0x20000 - len(data))
        binhash = sha256(datapadded).digest().hex().upper()
        if mic_fw_hash != binhash : return False
        print(f'MIC firmware sha: {binhash}')

        self.enMICPS('1')
        print("Entering Boot Mode...")
        self.enableMICBootloader(True)

        print("Doing Mass Erase... (This should take around 20 seconds)")
        self.eraseMICMemory(0)
        
        print("Downloading firmware to target...")
        SLICE = 256
        for addr in trange(0x08000000, 0x08000000+len(data), SLICE):
            self.writeMICFlash(addr, data[:SLICE])
            data = data[SLICE:]


        print("Download completed, resetting the device...")
        self.enableMICBootloader(False)
        self.enMICPS('0')
        time.sleep(0.2)

        self.enMICPS('1')
        time.sleep(0.5)
        print("Checking Hash...")
        hash = self.getMICFWHash()
        self.enMICPS('0')

        if hash != binhash:
            raise RuntimeError(f"Hash mismatch: {hash} != {binhash}")

        

