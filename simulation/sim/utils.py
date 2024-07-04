import math

# returns the airtime of the packet in ms
def get_air_time(freq : float, mod : str, band : float, length : int, cr=5) -> int:

    # SF_1 doesn't exist and is for testing, handle it as SF 7
    if(mod == "SF_1"):
        SF = 7
    else:
        SF = int(mod.split("_")[1])

    symbol_duration = (2**SF) / (band)

    return math.ceil( (12 + 4.25 + 8 + math.ceil( (8*length - 4*SF +28)/(4*SF) )*cr )*symbol_duration )
