
from libs.serial_handler import SerialController
from libs.dut import DUT
from libs.smartcable import SmartCableManager
import os
import time
from termcolor import colored
import module.read_page as rp

HEADER = colored(r"""
  __  __                  ____        _       _   _                 
 |  \/  | _____   _____  / ___|  ___ | |_   _| |_(_) ___  _ __  ___ 
 | |\/| |/ _ \ \ / / _ \ \___ \ / _ \| | | | | __| |/ _ \| '_ \/ __|
 | |  | | (_) \ V /  __/  ___) | (_) | | |_| | |_| | (_) | | | \__ \
 |_|  |_|\___/ \_/ \___| |____/ \___/|_|\__,_|\__|_|\___/|_| |_|___/
                                                                    """, 'green')

HELP = colored("""
1. Connect the SmartCable to the PC.
2. Connect the sensor to the SmartCable through the 8P connector.
3. Press Y to download the log file. 
""", 'magenta')

START_PAGE_NUM = 64   # in dec
HEX_IN_PAGE    = 4224 # 2112 * 2

Eflash_reader_App_APPNAME : str = 'Eflash_reader'

class Eflash_reader_App :
    smartc : SmartCableManager | None
    
    dutDev : DUT
    db_log : dict

    APPVERSION : str = '1.0'
    APPNAME : str = Eflash_reader_App_APPNAME
    APPLONGNAME : str = 'External flash reader'
    
    def __init__(self) :        
        self.download_log = {}
        self.smartc = None

    # Open conection with smartcable and turn on the USB power supply
    def initApp(self) -> bool :
        smartc : SmartCableManager | None

        if(self.smartc is None) :
            self.smartc = SmartCableManager()
        self.smartc.powerFromUSB(True)
        
        time.sleep(0.2)
        return True

    # Reset device and turn off the USB power supply
    def endTest(self) :
        self.smartc.activateBootloader(False)
        self.smartc.powerFromUSB(False)

    # Start external flash download
    def readExtFlash(self):
        start_time : float

        # clear interface     
        os.system('cls')

        # clear files
        filename = "dump"
        if os.path.exists(filename + ".bin"):
            os.remove(filename + ".bin")
        if os.path.exists(filename + ".txt"):
            os.remove(filename + ".txt")

        while(True) :
            
            print(HEADER)
            print(colored(f"*** {self.APPLONGNAME}, SW ver:{self.APPVERSION} ***", 'green'))
            print(colored("Enter Y to download external flash memory","magenta"))
            
            if not self.initApp() : 
                return
            
            user_input : str = input().strip()
            if(user_input != 'Y'):
                print(colored('Invalid character, please enter again...', 'red'))
                continue
            
            # Open serial connection
            self.dutDev = DUT( SerialController(self.smartc.sm.COMpath) )
            self.dutDev.serialP.open()

            # Save download start time to get statistics
            start_time = time.monotonic()

            # RESET DEVICE
            self.smartc.activateBootloader(False)

            # Enter test mode with AT+TST
            time.sleep(1)
            self.dutDev.ATmode()

            # Read only page 64 (0x40), first page
            # print(colored("\nStart reading memory content...","magenta"))
            # page_num = 40
            # self.dutDev.dumpPage(page_num, filename)

            # Test a generic AT command
            # time.sleep(1)
            # self.dutDev.getAPPEUIandKEY()

            # Execute an infinite loop where:
            #   1. Read page x (starting from page 0x40, or 64 in decimal).
            #   2. Check if the first character is 0x07 (start byte).
            #       [Y] Append to a binary file, save metadata to a log file, and print the page number (x of max y). Go back to point 1.
            #       [N] Download complete
            #   3. Generate a CSV file.

            # Start from first page to page x
            print(colored("\nStart reading memory content...","magenta"))

            # Initialized parameter for the cycle
            page_num = START_PAGE_NUM
            find_blank = False

            while ( page_num < (START_PAGE_NUM + 5) ) and ( not find_blank ): # read n pages or stop before if you find a blank
                print(f"Reading page {page_num}... ")
                # dump page and collect find_blank flag
                find_blank = self.dutDev.dumpPage(hex(page_num)[2:], filename) # convert dec page_num to hex -> 64 to '40'
                page_num += 1

            #==================================================================
            # CLOSING COMMUNICATION WITH DEVICE

            # print read time
            print(colored(f"Time: {round((time.monotonic()-start_time), 2)}", 'blue'))

            # Reset DUT information (eui, passkey, etc.) - Once communication with is no more needed
            self.endTest()
            self.dutDev.resetInfo()
            self.dutDev.serialP.close()
            #==================================================================
            # DECODE PAGES

            tot_page = page_num - START_PAGE_NUM 

            # Open the hex_page.txt
            with open("dump.txt", 'r') as f: 
                log = f.read()

            for index_page in range(tot_page):
                hex_page = log[index_page*HEX_IN_PAGE:(index_page + 1)*HEX_IN_PAGE]

                # Cuts hex_page into 8 blocks of length 256 bytes
                index  = 0
                record = [None] * rp.RECORDS_PER_PAGE
                for i in range (0, len(hex_page) - rp.SPARE_LENGTH_BYTE*2, rp.RECORD_LENGTH_BYTE*2): # *2 because we are working with hex
                    record[index] = hex_page[i : i + rp.RECORD_LENGTH_BYTE*2]
                    index += 1

                    # Reads data of all 8 records
                print(colored("==============================", "magenta"))
                print(colored(f"CONTENT OF PAGE {64 + index_page}", "magenta"))
                for i in range(0, rp.RECORDS_PER_PAGE):
                    if (record[i][0:2] == rp.START_BYTE):
                        record[i] = record[i][2:] # Remove start byte
                        print(colored("------------------------------", "yellow"))
                        print(colored(f"RECORD {i} PAYLOAD:", "yellow"))
                        rp.read_record(record[i])
                        
                        print("TAIL CONTENT")
                        tail = record[i][-rp.TAIL_LENGTH_BYTE*2:] # 18 hex
                        len_pl = int(
                            tail[0:2], 16
                        )  # len payload record x (it consider also the start byte 0x07)
                        ts_rc = int(tail[2:10], 16)  # record timestamp
                        time_rc = rp.datetime.fromtimestamp(ts_rc).isoformat()
                        print(f"Record timestamp: {time_rc}")
                        print(f"Record length: {len_pl}")



            break
        #endWhile
        print(colored("==============================", "magenta"))
        print(colored(f"TOTAL PAGE READED: {tot_page}", "light_blue"))

if __name__ == "__main__":

    print(colored("===================================================================","magenta"))
    print(HEADER)
    print(HELP)

    app = Eflash_reader_App()
    app.initApp()
    app.readExtFlash()

    print(colored("===================================================================","magenta"))