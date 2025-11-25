from datetime import datetime
import json


RECORD_LENGTH_BYTE = 256
TAIL_LENGTH_BYTE   = 9
SPARE_LENGTH_BYTE  = 64
START_BYTE         = "07" # hex 
RECORDS_PER_PAGE   = 8

#----------------------------------
ACCELERATION_RESOLUTION = 0.125
ACCELERATION_DECIMAL_FIGURES = 3

ANGULAR_VEL_RESOLUTION = 1e-6
ANGULAR_VEL_DECIMAL_FIGURES = 6

ANGLE32_RESOLUTION = 1e-7
ANGLE32_DECIMAL_FIGURES = 7

ANGLE16_RESOLUTION = 0.1
ANGLE16_DECIMAL_FIGURES = 1

TEMPERATURE_RESOLUTION = 0.05
TEMPERATURE_OFFSET = 50.0
TEMPERATURE_DECIMAL_FIGURES = 2

VERTICAL = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]

EVENT_TYPE = ["OnCadence", "OnAxeTrig", "OnAngTrig", "OnVelTrig"]

CADENCE = [
    "30s",
    "1m",
    "1m30s",
    "2m",
    "3m",
    "4m",
    "5m",
    "10m",
    "15m",
    "20m",
    "30m",
    "1h",
    "2h",
    "6h",
    "12h",
    "24h",
]

AVERAGING = [125, 250, 500, 1000, 2000]

RANGE = ["2g", "4g", "8g"]

TRIGGERED_ANGLE = ["alpha1", "alpha2", "alpha3"]
#----------------------------------

def _twoscomp_str(_str, bitnum=8):
    temp = int(_str[: int(bitnum / 4)], 16)
    if temp >= 2 ** (bitnum - 1):
        temp -= 2**bitnum
    return temp

def read_record(pl: str):

    ts = int(pl[6:8] + pl[4:6] + pl[2:4] + pl[0:2], 16)

    t = int(pl[11:12] + pl[8:10], 16)
    vert = int(pl[10:11], 16) & 0b0111

    a1 = _twoscomp_str(pl[18:20] + pl[16:18] + pl[14:16] + pl[12:14], 32)
    a2 = _twoscomp_str(pl[26:28] + pl[24:26] + pl[22:24] + pl[20:22], 32)
    a3 = _twoscomp_str(pl[34:36] + pl[32:34] + pl[30:32] + pl[28:30], 32)

    pk = _twoscomp_str(pl[38:40] + pl[36:38], 16)

    rms = _twoscomp_str(pl[42:44] + pl[40:42], 16)

    type = (int(pl[44:46], 16) >> 6) & 0b11

    ret = {
        "time": datetime.fromtimestamp(ts).isoformat(),
        "temperature": round(
            float(t) * TEMPERATURE_RESOLUTION - TEMPERATURE_OFFSET,
            TEMPERATURE_DECIMAL_FIGURES,
        ),
        "verticalAxis": VERTICAL[vert],
        "alpha1": round(float(a1) * ANGLE32_RESOLUTION, ANGLE32_DECIMAL_FIGURES),
        "alpha2": round(float(a2) * ANGLE32_RESOLUTION, ANGLE32_DECIMAL_FIGURES),
        "alpha3": round(float(a3) * ANGLE32_RESOLUTION, ANGLE32_DECIMAL_FIGURES),
        "axePeak": round(float(pk) * ACCELERATION_RESOLUTION, ACCELERATION_DECIMAL_FIGURES),
        "axeRms": round(float(rms) * ACCELERATION_RESOLUTION, ACCELERATION_DECIMAL_FIGURES),
    }

    if type == 0:  # programmed
        # if len(pl) != (2 * 24):  # 24 bytes
        #     raise Exception("Wrong payload length")

        stdCad = (int(pl[44:46], 16) >> 2) & 0b1111

        avgSmp = (int(pl[46:48], 16) >> 2) & 0b111
        rng = (int(pl[46:48], 16)) & 0b11

        ret["stdCad"] = CADENCE[stdCad]
        ret["avgSamp"] = AVERAGING[avgSmp]
        ret["range"] = RANGE[rng]

    if type == 1:  # acceleration triggered
        # if len(pl) != (2 * 25):  # 25 bytes
        #     raise Exception("Wrong payload length")

        avgSmp = (int(pl[44:46], 16) >> 2) & 0b111
        rng = int(pl[44:46], 16) & 0b11

        axeTh = int(pl[48:50] + pl[46:48], 16)

        ret["avgSamp"] = AVERAGING[avgSmp]
        ret["range"] = RANGE[rng]
        ret["axeTh"] = round(
            float(axeTh) * ACCELERATION_RESOLUTION, ACCELERATION_DECIMAL_FIGURES
        )

    if type == 2:  # angle triggered
        # if len(pl) != (2 * 37):  # 37 bytes
        #     raise Exception("Wrong payload length")

        trgAngl = int(pl[44:45], 16) & 0b11
        a1en = (int(pl[45:46], 16) >> 3) & 0b1
        a2en = (int(pl[45:46], 16) >> 2) & 0b1
        a3en = (int(pl[45:46], 16) >> 1) & 0b1

        avgSmp = (int(pl[46:48], 16) >> 2) & 0b111
        rng = int(pl[46:48], 16) & 0b11

        a1lt = _twoscomp_str(pl[50:52] + pl[48:50], 16)
        a1ht = _twoscomp_str(pl[54:56] + pl[52:54], 16)
        a2lt = _twoscomp_str(pl[58:60] + pl[56:58], 16)
        a2ht = _twoscomp_str(pl[62:64] + pl[60:62], 16)
        a3lt = _twoscomp_str(pl[66:68] + pl[64:66], 16)
        a3ht = _twoscomp_str(pl[70:72] + pl[68:70], 16)

        fstCad = int(pl[72:73], 16)

        ret["fstCad"] = CADENCE[fstCad]
        ret["trigAngle"] = TRIGGERED_ANGLE[trgAngl]
        ret["alpha1En"] = a1en
        ret["alpha2En"] = a2en
        ret["alpha3En"] = a3en
        ret["avgSamp"] = AVERAGING[avgSmp]
        ret["range"] = RANGE[rng]
        ret["alpha1LowTh"] = round(
            float(a1lt) * ANGLE16_RESOLUTION, ANGLE16_DECIMAL_FIGURES
        )
        ret["alpha1HighTh"] = round(
            float(a1ht) * ANGLE16_RESOLUTION, ANGLE16_DECIMAL_FIGURES
        )
        ret["alpha2LowTh"] = round(
            float(a2lt) * ANGLE16_RESOLUTION, ANGLE16_DECIMAL_FIGURES
        )
        ret["alpha2HighTh"] = round(
            float(a2ht) * ANGLE16_RESOLUTION, ANGLE16_DECIMAL_FIGURES
        )
        ret["alpha3LowTh"] = round(
            float(a3lt) * ANGLE16_RESOLUTION, ANGLE16_DECIMAL_FIGURES
        )
        ret["alpha3HighTh"] = round(
            float(a3ht) * ANGLE16_RESOLUTION, ANGLE16_DECIMAL_FIGURES
        )

    if type == 3:  # angular velocity triggered
        # if len(pl) != (2 * 27):  # 27 bytes
        #     raise Exception("Wrong payload length")

        trgAngl = int(pl[44:45], 16) & 0b11
        a1en = (int(pl[45:46], 16) >> 3) & 0b1
        a2en = (int(pl[45:46], 16) >> 2) & 0b1
        a3en = (int(pl[45:46], 16) >> 1) & 0b1

        avgSmp = (int(pl[46:48], 16) >> 2) & 0b111
        rng = int(pl[46:48], 16) & 0b11

        angVelThr = int(pl[52:54] + pl[50:52] + pl[48:50], 16)

        ret["trigAngle"] = TRIGGERED_ANGLE[trgAngl]
        ret["alpha1En"] = a1en
        ret["alpha2En"] = a2en
        ret["alpha3En"] = a3en
        ret["avgSamp"] = AVERAGING[avgSmp]
        ret["range"] = RANGE[rng]
        ret["angVelTh"] = round(
            float(angVelThr) * ANGULAR_VEL_RESOLUTION, ANGULAR_VEL_DECIMAL_FIGURES
        )
    
    return ret

    # print(json.dumps(ret, indent=4)) // uncomment if you want to print the records


# ________________________________________
if __name__ == "__main__":
    # Open the hex_page.txt
    with open("dump.txt", 'r') as f:  # "hex_page.txt"
        hex_page = f.read()
    
    record_one = hex_page[:4224]
    record_two = hex_page[4224:] # 2112 * 2

    hex_page = record_two

    # Cuts hex_page into 8 blocks of length 256 bytes
    index  = 0
    record = [None] * RECORDS_PER_PAGE
    for i in range (0, len(hex_page) - SPARE_LENGTH_BYTE*2, RECORD_LENGTH_BYTE*2): # *2 because we are working with hex
        record[index] = hex_page[i : i + RECORD_LENGTH_BYTE*2]
        index += 1

    # Reads data of all 8 records
    for i in range(0, RECORDS_PER_PAGE):
        if (record[i][0:2] == START_BYTE):
            record[i] = record[i][2:] # Remove start byte
            print("------------------------------")
            print(f"RECORD {i} PAYLOAD:")
            read_record(record[i])
            
            print("TAIL CONTENT")
            tail = record[i][-TAIL_LENGTH_BYTE*2:] # 18 hex
            len_pl = int(
                tail[0:2], 16
            )  # len payload record x (it consider also the start byte 0x07)
            ts_rc = int(tail[2:10], 16)  # record timestamp
            time_rc = datetime.fromtimestamp(ts_rc).isoformat()
            print(f"Record timestamp: {time_rc}")
            print(f"Record length: {len_pl}")