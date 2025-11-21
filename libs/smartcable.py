
import hid, re, inquirer, time, os, serial
import serial.tools.list_ports
from typing import List, Any
from termcolor import colored


try :
    from libs.configurations import *
except ImportError as e :
    print('configuration not imported')
    if 'DEBUG' not in globals():
        def DEBUG( string : str, end : str = 'end' ) :
            if 0 :
                if end == '' :  print( colored(string, 'dark_grey'), end = '')
                else :          print( colored(string, 'dark_grey'))

SMARTCABLE_VID = 0x0483
SMARTCABLE_PID = 0x52A4

# definition of a smartcable 
class SmartCableEntry :
    HID : hid.device
    COMpath : str
    HIDpath : Any
    sn : str
    name : str

    def __init__(self, HIDpath : Any, sn : str, name : str, COMpath : str) :
        self.HID = hid.device()
        self.HIDpath = HIDpath
        self.sn = sn
        self.name = name
        self.COMpath = COMpath
    
    def printMe(self) :
        print(f'HIDpath: {self.HIDpath}')
        print(f'sn: {self.sn}')
        print(f'name: {self.name}')
        print(f'COMpath: {self.COMpath}')
    def openHID(self) :
        self.HID.open_path(self.HIDpath)   
    
    def closeHID(self) :
        self.HID.close()
    
    def sendReport(self, report : bytes) -> int:
        return self.HID.write([0] + report) # return the number of bytes written
    
    def getReport(self, report : bytes, bytes_to_read : int) -> bytes:
        self.HID.write([0] + report) # return the number of bytes written
        return self.HID.read(bytes_to_read)  # Reads from device 




class SmartCableManager :
    sm : SmartCableEntry | None
    gpios_status : int
    isOpen : bool

    MCP2200_COMMAND_SET_CLEAR_OUTPUTS : int = 0x08
    MCP2200_COMMAND_READ_ALL : int = 0x80

    MCP2200_HSS_EN_PIN : int = 0x20
    MCP2200_HSS_FAULT_PIN : int = 0x80
    MCP2200_RESET_PIN : int = 0x08
    MCP2200_BOOT_PIN : int = 0x40

    def __init__(self) :
        sm_selected : str
        sm_names_list : list[str] = []
        sm_list : list[SmartCableEntry] = SmartCableManager.getSmartcableEntries( sm_names_list )
        self.sm = None
        self.gpios_status = 0
        self.isOpen = False
        
        # If there are none smartcables, raise an error
        if len(sm_list) == 0 :
            raise RuntimeError('no Smartcables connected')
        
        # If there are more than 1 smartcable, select the correct device
        if len(sm_list) > 1 :
            choicelist = [inquirer.List( 'smartcable', message='Select the program to RUN', choices=sm_names_list)]
            sm_selected = inquirer.prompt(choicelist)['smartcable']
        else :
            sm_selected = sm_list[0].name
        
        # Extract the device selected
        for dev in sm_list :
            if dev.name == sm_selected :
                self.sm = dev
        
        DEBUG(f"Chosen {self.sm.name} device")
        self._openHID()
    

    # Check if device name is a smartcable pattern
    sm_name_pattern = re.compile(r'^SMARTCABLE-[A-Z0-9]{4}$')
    def is_SmartCable_Name(sm_name) -> bool:
        return bool(re.match(SmartCableManager.sm_name_pattern, sm_name))

    # Get smartcable com port with the serial number
    def getSmartcableCOM( sn : str ) -> str :
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if sn == port.serial_number :
                return port.name
        raise RuntimeError('NO SMARTCABLE COM FOUND')

    def getSmartcableEntries(names : list[str] = []) -> List[SmartCableEntry]:
        # Get the list of all HID devices connected
        devices = hid.enumerate()
        ret : List[SmartCableEntry] = []
        
        # Loop through each device and extract only the smartcables
        for device in devices:
            if device['vendor_id'] == SMARTCABLE_VID and device['product_id'] == SMARTCABLE_PID :
                if SmartCableManager.is_SmartCable_Name( device['product_string'] ) :
                    ret.append(SmartCableEntry(device['path'], device['serial_number'], device['product_string'], SmartCableManager.getSmartcableCOM(device['serial_number'])))
                    names.append( device['product_string'] )
                    # device['path'] = device['path'].decode('utf-8')
                    DEBUG('Device found:')
                    DEBUG(f"Manufacturer: {device['manufacturer_string']}")
                    DEBUG(f"Product: {device['product_string']}")
                    DEBUG(f"Serial Number: {device['serial_number']}")
                    DEBUG(f"COM: {ret[len(ret)-1].COMpath}")
        return ret
            
    def _openHID(self) :
        self.sm.openHID()
        self.getGPIOStatus()
        self.getGPIOStatus()
        self.getGPIOStatus()
        self.isOpen = True
    def __del__(self) :
        if(self.sm == None) :
            return
        self.powerFromUSB(False)

    def toggleHSS_EN(self) :
        self.powerFromUSB( not ((self.gpios_status & SmartCableManager.MCP2200_HSS_EN_PIN) > 0) )

    def powerFromUSB(self, on : bool) :
        report : bytearray = [0x00] * 0x10
        report[0] = SmartCableManager.MCP2200_COMMAND_SET_CLEAR_OUTPUTS
        if on :
            report[11] = SmartCableManager.MCP2200_HSS_EN_PIN
            self.gpios_status |= SmartCableManager.MCP2200_HSS_EN_PIN 
        else :
            report[12] = SmartCableManager.MCP2200_HSS_EN_PIN
            self.gpios_status &= ~SmartCableManager.MCP2200_HSS_EN_PIN
            
        return self.sm.sendReport(report)
            
    def toggleBOOT(self) :
        self.enBOOT( not ((self.gpios_status & SmartCableManager.MCP2200_BOOT_PIN) > 0) )
        
    def enBOOT(self, on : bool) :
        report : bytearray = [0x00] * 0x10
        report[0] = SmartCableManager.MCP2200_COMMAND_SET_CLEAR_OUTPUTS
        if on :
            report[11] = SmartCableManager.MCP2200_BOOT_PIN
            self.gpios_status |= SmartCableManager.MCP2200_BOOT_PIN 
        else :
            report[12] = SmartCableManager.MCP2200_BOOT_PIN
            self.gpios_status &= ~SmartCableManager.MCP2200_BOOT_PIN
        return self.sm.sendReport(report)
            
    def toggleRESET(self) :
        self.enRESET( not ((self.gpios_status & SmartCableManager.MCP2200_RESET_PIN) > 0) )

    def enRESET(self, on : bool) :
        report : bytearray = [0x00] * 0x10
        report[0] = SmartCableManager.MCP2200_COMMAND_SET_CLEAR_OUTPUTS
        if on :
            report[11] = SmartCableManager.MCP2200_RESET_PIN
            self.gpios_status |= SmartCableManager.MCP2200_RESET_PIN 
        else :
            report[12] = SmartCableManager.MCP2200_RESET_PIN
            self.gpios_status &= ~SmartCableManager.MCP2200_RESET_PIN
        return self.sm.sendReport(report)
        
    def activateBootloader(self, on : bool) :
        if on :
            self.enBOOT(True)
        else :
            self.enBOOT(False)
        time.sleep(0.3)
        self.enRESET(False)
        time.sleep(0.3)
        self.enRESET(True)
        time.sleep(0.3)
    
    def getGPIOStatus(self) :
        report : bytearray = [0x00] * 0x10
        report[0] = SmartCableManager.MCP2200_COMMAND_READ_ALL
        report = self.sm.getReport(report, 0x10)
        self.gpios_status = report[10]

    def printGPIO(self) :
        self.getGPIOStatus()
        self.getGPIOStatus()

        print('GPIO STATUS')
        print('HSS_EN      (', end = '')
        if (self.gpios_status & SmartCableManager.MCP2200_HSS_EN_PIN) > 0 : print(colored('X', 'green'), end = '')
        else : print(' ', end = '')
        print(')')

        print('HSS_FAULT   (', end = '')
        if (self.gpios_status & SmartCableManager.MCP2200_HSS_FAULT_PIN) > 0 : print(colored('X', 'green'), end = '')
        else : print(' ', end = '')
        print(')')

        print('BOOT        (', end = '')
        if (self.gpios_status & SmartCableManager.MCP2200_BOOT_PIN) > 0 : print(colored('X', 'green'), end = '')
        else : print(' ', end = '')
        print(')')
        
        print('RESET       (', end = '')
        if (self.gpios_status & SmartCableManager.MCP2200_RESET_PIN) > 0 : print(colored('X', 'green'), end = '')
        else : print(' ', end = '')
        print(')')
    
    # Control smartcable gpio with the console
    def controller(self) :
        while( True ) :
            actions : list[str] = []
            choice : str
            actions.append('Enable BOOTLOADER')     # 0
            actions.append('Reset Device')          # 1
            actions.append('Update GPIO_Status')    # 2
            actions.append(f"Toggle HSS_EN    ({'X' if (self.gpios_status & SmartCableManager.MCP2200_HSS_EN_PIN) > 0 else ' '})")   # 3
            actions.append(f"Toggle BOOT      ({'X' if (self.gpios_status & SmartCableManager.MCP2200_BOOT_PIN) > 0 else ' '})")   # 4
            actions.append(f"Toggle RESET     ({'X' if (self.gpios_status & SmartCableManager.MCP2200_RESET_PIN) > 0 else ' '})")   # 5
            actions.append(f"Status HSS_FAULT ({'X' if (self.gpios_status & SmartCableManager.MCP2200_HSS_FAULT_PIN) > 0 else ' '})")   # 6
            actions.append('Exit')     # 7

            os.system('cls')
            choicelist = [inquirer.List( 'action', message='Select the program to RUN', choices=actions)]
            choice = inquirer.prompt(choicelist)['action']
            
            if 'HSS_EN' in choice :
                self.toggleHSS_EN()
            elif 'BOOT' in choice :
                self.toggleBOOT()
            elif 'RESET' in choice :
                self.toggleRESET()
            elif 'BOOTLOADER' in choice :
                self.activateBootloader(True)
            elif 'Reset Device' in choice :
                self.activateBootloader(False)
            elif 'Exit' in choice :
                break
            else :
                self.getGPIOStatus()
                self.getGPIOStatus()


if __name__ == "__main__":
    SmartCableManager().controller()