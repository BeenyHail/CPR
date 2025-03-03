import sys
import os

def makeDir(directory): #make directory
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
        except OSError:
            print("Error: Failed to create the directory.")
            sys.exit()

def detectZeroStreak(hex_data):
        zero_byte = b'\x00'
        #Set the number of consecutive 00 bytes to check for.
        min_consecutive_zeros = 48 
        consecutive_zeros = zero_byte * min_consecutive_zeros

        return consecutive_zeros in hex_data