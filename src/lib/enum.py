iota_count = 0

def iota(reset:bool=False, start:int=0):
    global iota_count
    if reset:
        iota_count = start
    iota_count += 1
    return iota_count
