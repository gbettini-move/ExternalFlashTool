
from libs.serial_handler import SerialController
from libs.dut import DUT
from libs.smartcable import SmartCableManager
import os
import time
from termcolor import colored
import module.read_page as rp
import xlsxwriter
from utils import search_in

HEADER = colored(r"""
  __  __                  ____        _       _   _                 
 |  \/  | _____   _____  / ___|  ___ | |_   _| |_(_) ___  _ __  ___ 
 | |\/| |/ _ \ \ / / _ \ \___ \ / _ \| | | | | __| |/ _ \| '_ \/ __|
 | |  | | (_) \ V /  __/  ___) | (_) | | |_| | |_| | (_) | | | \__ \
 |_|  |_|\___/ \_/ \___| |____/ \___/|_|\__,_|\__|_|\___/|_| |_|___/
                                                                    """, 'green')

XLSX_HEADER = ["Page n.", "Record n.", "Date", "Time", "Temperature [°C]", "Vertical Axis", "Alpha 1 [°]", "Alpha 2 [°]", "Alpha 3 [°]",
                "Acc. Peak [mg]", "Acc. RMS [mg]", "Avg. Samples", "Full scale", "Acc. Threshold [mg]"]

HELP = colored("""
1. Connect the SmartCable to the PC.
2. Connect the sensor to the SmartCable through the 8P connector.
3. Press Y to download the log file. 
""", 'magenta')

START_PAGE_NUM   = 64   # in dec
PAGE_PER_BLOCK   = 64
NUMBER_OF_BLOCKS = 512
HEX_IN_PAGE      = 4224 # 2112 * 2

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
        #smartc : SmartCableManager | None

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
        if os.path.exists("flash_content.xlsx"):
            os.remove("flash_content.xlsx")

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
            
            # try-finally construct to ensure the connection is closed if any problems arise
            try: 
                # Open serial connection
                self.dutDev = DUT( SerialController(self.smartc.sm.COMpath) )
                self.dutDev.serialP.open()
                
                # RESET DEVICE
                self.smartc.activateBootloader(False)

                # Enter test mode with AT+TST
                time.sleep(1)
                self.dutDev.ATmode()

                # Read only page 64 (0x40), first page
                # print(colored("\nStart reading memory content...","magenta"))
                # page_num = 40
                # self.dutDev.dumpPage(page_num, filename)

                # Execute an infinite loop where:
                #   1. Read page x (starting from page 0x40, or 64 in decimal).
                #   2. Check if the first character is 0x07 (start byte).
                #       [Y] Append to a binary file, save metadata to a log file, and print the page number (x of max y). Go back to point 1.
                #       [N] Download complete
                #   3. Generate a CSV file.

                # (OOOOOOOOOOOOOOOOOO::::::) idea for tqdm

                # Start from first page to page x
                print(colored("\nStart reading memory content...","magenta"))

                # Initialized parameter for the cycle
                page_num = START_PAGE_NUM
                is_blank = False
                start_time = time.monotonic() # Save download start time to get statistics

                # Find written block. Just have to read the first page of each block.
                while page_num < (PAGE_PER_BLOCK * NUMBER_OF_BLOCKS) : # The last check is pag n. 32704 < 32768 (total pages). Also, probabily diagnostic pages
                    print(f"Reading page {page_num}... ")
                    # dump page and collect is_blank flag
                    is_blank = self.dutDev.dumpPage(hex(page_num)[2:], filename) # convert dec page_num to hex -> 64 to '40'
                    if is_blank:
                        page_num += 64
                    else:
                        page_num += 1 # the first page is already added
                        break

                page_to_read = 60 # maximum number of page that you want to read
                # Read page of the block
                for i in range(page_to_read - 1): # The first page has already been read in the cycle above ( so - 1 is necessary )
                    print(f"Reading page {page_num}... ")
                    # dump page and collect is_blank flag
                    is_blank = self.dutDev.dumpPage(hex(page_num)[2:], filename) # convert dec page_num to hex -> 64 to '40'
                    if not is_blank:
                        page_num += 1
                    else:   # stop before if you find a blank
                        break

                #==================================================================
                # CLOSING COMMUNICATION WITH DEVICE

                # print read time
                print(colored(f"Time: {round((time.monotonic()-start_time), 2)}", 'blue'))

            finally:
                # Reset DUT information (eui, passkey, etc.) - Once communication with is no more needed
                self.endTest()
                self.dutDev.resetInfo()
                self.dutDev.serialP.close()

            #==================================================================
            # DECODE PAGES AND GENERATE XLSX FILE

            workbook  = xlsxwriter.Workbook("flash_content.xlsx") # xlsx file name
            worksheet = workbook.add_worksheet("eFlash") # generating the sheet

            header_format = workbook.add_format({
                "bold": True,
                "bg_color": "#E0AF76",   
                "font_color": "#000000",
                "border": 1,
                "align": "center",
                "valign": "vcenter"
                })
            
            # row format
            fmt_even = workbook.add_format({"bg_color": "#E0DEDE", "align": "left", "border": 1, "border_color": "#838080"})
            fmt_odd  = workbook.add_format({"bg_color": "#FFFFFF", "align": "left", "border": 1, "border_color": "#838080"})

            # page separator
            fmt_separator = workbook.add_format({"bg_color": "#E0DEDE", "align": "left", "border": 1, "border_color": "#838080", "bottom": 2, "bottom_color": "#000000"})

            row = 0

            for col, header in enumerate(XLSX_HEADER):
                worksheet.write(row, col, header, header_format) # row 0 -> headers
                col_width = max(len(header) + 2, 10) # adjust column width (> 10 for date and time)
                worksheet.set_column(col, col, col_width)

            tot_page = page_num - START_PAGE_NUM 

            # Open the hex_page.txt
            with open("dump.txt", 'r') as f: 
                log = f.read()
            
            rec_content = {}

            for index_page in range(tot_page): # cicle for the pages
                hex_page = log[index_page*HEX_IN_PAGE:(index_page + 1)*HEX_IN_PAGE]

                # Cuts hex_page into 8 blocks of length 256 bytes
                index  = 0
                record = [None] * rp.RECORDS_PER_PAGE
                for i in range (0, len(hex_page) - rp.SPARE_LENGTH_BYTE*2, rp.RECORD_LENGTH_BYTE*2): # *2 because we are working with hex
                    record[index] = hex_page[i : i + rp.RECORD_LENGTH_BYTE*2]
                    index += 1
                
                rec_content["Page n."] = index_page + 64

                # Reads data of all 8 records

                for i in range(0, rp.RECORDS_PER_PAGE): # cicle for the records
                    if (record[i] is not None and record[i][0:2] == rp.START_BYTE): # record[i] is not None to avoid error 'NoneType' object is not subscriptable
                        record[i] = record[i][2:] # Remove start byte

                        rec_content["Record n."] = i + 1 # record counted from 1 to 8
                        rec_content.update(rp.read_record(record[i]))

                        tail = record[i][-rp.TAIL_LENGTH_BYTE*2:] # 18 hex
                        len_pl = int(
                            tail[0:2], 16
                        )  # len payload record x (it consider also the start byte 0x07)
                        ts_rc = int(tail[2:10], 16)  # record timestamp
                        time_rc = rp.datetime.fromtimestamp(ts_rc).isoformat()

                        rec_content["Tail-Rec.Timestamp"] = time_rc # add also the tail content to the record_content
                        rec_content["Tail-Rec.Length"]    = len_pl

                        # add row to xlsx
                        row += 1 # move one row ahead
                        fmt = fmt_separator if row % 8 == 0 else fmt_even if row % 2 == 0 else fmt_odd # choose the format
                        for col, header in enumerate(XLSX_HEADER):
                            value = search_in(rec_content, header)
                            worksheet.write(row, col, value, fmt) # add record columns
                    else:
                        raise Exception ("Error decoding files - try again")

            workbook.close() # save the file


            break
        #endWhile
        print(colored("==============================", "magenta"))
        print(colored(f"TOTAL PAGES READ: {tot_page}", "light_blue"))

if __name__ == "__main__":

    print(colored("===================================================================","magenta"))
    print(HEADER)
    print(HELP)

    app = Eflash_reader_App()
    app.initApp()
    app.readExtFlash()

    print(colored("==============================", "magenta"))