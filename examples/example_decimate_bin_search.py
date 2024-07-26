# This file is part of Teron Labs' Decimate distribution.
# Copyright (C) 2024 Teron Labs <https://www.teronlabs.com/>, <info@teronlabs.com> 
#
# Licensed under the GNU General Public License v3.0 (GPLv3). For details see the LICENSE.md file.
#
# Author(s)
# Yvonne Cliff, Teron Labs <yvonne@teronlabs.com>.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https:#www.gnu.org/licenses/>.

from decimate.deci import decimated_binary_search, result_open, result_print, failTable, unchanged
import json
import random
import secrets
import os

delta_path = "./data/Example_decimate_bin_search_Mod4_relationship.bin"
results_path = "./data/Example_decimate_bin_search_results.txt"
generateFile = False
eraseFile = False
numTests = 5
maxDecimation = 10
testSize = 1000000
numDeltas = 2 * maxDecimation * testSize
dependencyModulus = 4

print("\n\nPREVIOUSLY SAVED RESULTS:\n\n")
results = result_open(results_path, False)
result_print(results, failTable, minTests=numTests, printLowRounds=True, platformList=[], printSet={}, printAllIndividTests=False)


if (not os.path.exists(delta_path)) or (os.path.getsize(delta_path) < numDeltas) or generateFile:
    if (not os.path.exists(delta_path)):
        print("No existing delta file.")
    elif (os.path.getsize(delta_path) < numDeltas):
        print(f"Existing file only {os.path.getsize(delta_path)} bytes instead of {numDeltas} bytes.")
    else:
        print(f"generateFile = {generateFile}")
    print(f"\n\n GENERATING A FILE OF SAMPLES \n\twith dependent groups of samples of size {dependencyModulus}:\n\n")
    # Generate a random file for test purposes.
    with open(delta_path, "wb") as myFile:
        for i in range(numDeltas):
            if i%dependencyModulus ==0:
                lastRand = secrets.randbelow(128)
                lastNum = lastRand + secrets.randbelow(128)    
            else:
                lastNum = lastRand + secrets.randbelow(128)
            myFile.write(lastNum.to_bytes(length=1, byteorder='little', signed=False))
    print(f"Wrote delta file {delta_path} which is {os.path.getsize(delta_path)} bytes long.")

print("\n\n STARTING DECIMATION TESTING:\n\n")

results, dateStamps, passedLevels = \
    decimated_binary_search(delta_path, results_path, overwrite=False, 
        platform=f"{dependencyModulus} dependent", maxDec=maxDecimation, minDec=1, numTestsRequested=numTests, maxFails=failTable, testSize=testSize, 
        dec_multiplier=1,
        input_delta_bytes=1, convert_delta=unchanged, byte_order='little', verbose=True, failEarly=False, IIDtests="-r all -r abort1fail")

print("\n\n PRINTING FINAL RESULTS - WITH ALL INDIVIDUAL TEST RESULTS INCLUDED:\n\n")

result_print(results, failTable, minTests=5, printLowRounds=True, platformList=[], printSet={'roundPass', 'passList', 'datestamp'}, 
             dateRange=dateStamps, printAllIndividTests=True)

print("\n\n PRINTING FINAL RESULTS - No individual test results:\n\n")

result_print(results, failTable, minTests=5, printLowRounds=True, platformList=[], printSet={'roundPass', 'passList', 'datestamp'}, 
             dateRange=dateStamps, printAllIndividTests=False)

if eraseFile:
    if os.path.exists(delta_path):
        os.remove(delta_path)