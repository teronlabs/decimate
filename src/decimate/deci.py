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


from stats90b import iid_main
import json
from math import ceil, floor
import gc
import datetime
import sys
import os
from operator import itemgetter

# A function to return the least signficant 8 bits of a delta
def mod_256(delta):
    return (delta % 256)

# A function to drop the least significant bit of a delta and return the result modulo 256.
def shr1_mod256(delta):
    return ((delta >> 1) % 256)

# A function to drop the least significant bit of a delta and return the result modulo 255.
def shr1_mod255(delta):
    return ((delta >> 1) % 255)

# A function to keep the delta unchanged.
def unchanged(delta):
    return delta

# Purpose: Sometimes deltas in particular sequence positions are more likely to pass the IID tests than deltas in other sequence positions.
#          E.g. deltas in sequence position 0 modulo 4 might be more likely to pass IID tests than other deltas.
#          This function may be used to write deltas in the desired sequence positions to file; other deltas are discarded.
# Parameters:
#       in_path: File containing the input deltas
#       out_path: Path to file where desired deltas are to be written 
#       dec: modulus for the sequence position selection
#       delIdx: list of sequence positions to be ignored modulo dec (each value must be >= 0 and < dec).
#       delta_bytes: each delta must be delta_bytes bytes long 
#       byte_order: each delta must have the byte order as specified in byte_order (e.g. 'little').
#       verbose: if verbose=True, a status message is printed after the function has finished writing the file.
#
#          E.g. the in_path contains deltas: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 4, 7, 2, 3, 1, 8.
#               dec = 4
#               delIdx = [2, 3]
#               then the deltas output to the out_path will be: 0, 1, 4, 5, 8, 9, 7, 2, 8.
#
def write_decimated_delete_file(in_path, out_path, dec=4, delIdx=[3], verbose=True,  delta_bytes = 8, byte_order='little'):
    # Open the output file for writing (binary).
    with open(out_path, "wb") as out_file:
        # Open the input file of deltas for reading (binary).
        with open(in_path, "rb") as in_file:
            # i counts how many samples have been read from the input file.
            i = 0
            # samples counts how mnay samples have been written to the output file.
            samples = 0

            # Read the first delta, which is delta_bytes long.
            data = in_file.read(delta_bytes)

            # While there are still deltas in the file:
            while data:
                #If the delta which was read is not one that we wish to discard, convert it to an integer, and write it to the output file.
                if (i%dec) not in delIdx:
                    int_data = int.from_bytes(data, byteorder=byte_order, signed=False) 
                    out_file.write(int_data.to_bytes(delta_bytes, byte_order, signed=False))
                    # Count how mnay samples have been written to the output file.
                    samples += 1
                # Read the next delta and increase i, which counts how many deltas have been read.
                data = in_file.read(delta_bytes)
                i+= 1
    # We are finished. Write a status message if verbose output requested.
    if verbose:
        print("\nwrite_decimated_delete_file - Wrote "+ f"{samples:,d}" + " out of " + f"{i:,d}" + " samples.")
        print("write_decimated_delete_file - input path: ", in_path)
        print("write_decimated_delete_file - output path: ", out_path)
    return 0


# Purpose: re-arrange deltas into a decimated order, ready for decimation testing.
# Parameters: 
#       in_path: the path to the input file containing the deltas
#       out_path: the path to the output file where the decimated deltas will be written
#       dec: the decimation level
#       numSets: How many decimated sets of data will be seprately IID tested
#       setSize: How many deltas will be in each set sent for IID testing
#       input_delta_bytes: Number of bytes per delta in the in_path file.
#       output_delta_bytes: Number of bytes per delta to write to the out_path file.
#       convert_delta: function that takes as input any positive integer which was input_delta_bytes bytes long 
#                       and a returns an integer that can be represented with no more than output_delta_bytes bytes.
#       byte_order: The order of the bytes of each delta in the in_path file and out_path file (e.g. 'little')
#       verbose: Set to True if status updates should be printed.
# E.g.
#       If the in_path contains deltas 0, 1, 2, 3,| 4, 5, 6, 7,| 8, 9, 10, 54, |57, 52, 53, 51, |58, 59, 50, 47, |42, 45, 43, 49,|44, 32, 39, 33 | 35.
#           and dec = 4
#           and setSize = 3
#           and numSets = 5
#       Then the out_path will contain deltas: 0, 4, 8, | 57, 58, 42, | 1, 5, 9, | 52, 59, 45, | 2, 6, 10, | 53, 50, 43, | 3, 7, 54, | 51, 47, 49.
#       Where the '|' character is not part of the input or output but inserted here for readability.
def write_decimated_file(in_path, out_path, dec=1, numSets=1, setSize=1000000, convert_delta=unchanged, verbose = True, input_delta_bytes = 8, 
                          output_delta_bytes = 8, byte_order='little'):

    # rounds = how many lots of (dec x setSize) deltas we need
    # There are (rounds * setSize) deltas from each conjugate class, and 'dec' conjugate classes.
    rounds = ceil(numSets/dec)
    #Total number of input deltas needed to be able to output 'numSets' sets of data, each of size 'setSize'
    dataNeeded = rounds* dec*setSize 

    # Set up an array or list into which we can copy the deltas as they are read.
    # The decSamples array/list will contain the deltas in a decimated order.
    # Use a bytearray if the output is only one byte per delta, otherwise use a list of integers.
    if output_delta_bytes == 1:
        decSamples = bytearray(dataNeeded)
    else:
        decSamples = [0]*(dataNeeded)
    
    # Open the output file for writing (binary)
    with open(out_path, "wb") as out_file:
        # Open the input file for reading (binary)
        with open(in_path, "rb") as in_file:

            if verbose:
                statusStr = "write_decimated_file - Number of data sets read so far: "
                print(statusStr, end="")
                printLen = len(f"{(dataNeeded//setSize):,d}")
                spaces = " "*(printLen-1)
                backspaces = "\b"*printLen
                print(spaces + "0", end = "", flush=True)


            # Use i to count how many deltas are read (a total of dataNeeded deltas must be read).
            for i in range(dataNeeded):
                # Read the next delta
                data = in_file.read(input_delta_bytes) 

                # Print an error message and exit the program if the input file ended too soon:
                if not data:
                    print("write_decimated_file - ERROR: FILE ENDED TOO SOON - i =", i)
                    print("write_decimated_file - NUMBER OF DELTAS REQUIRED: ", dataNeeded, ".")
                    print("write_decimated_file - rounds = ceil(numSets/dec) = ceil(", numSets, "/", dec, ") = ", rounds, ".")
                    print("write_decimated_file - dec x rounds x setSize = ", dec, "x", rounds, "x", setSize)
                    sys.exit(-1)
                
                # Work out where to store the delta in the decSamples array/list:
                # Find the conjugate class for the delta:
                conjClass = i % dec
                # Find the number of the delta in this conjugate class:
                conjDeltaNum = i // dec
                # Find the index into the decSamples list/array:
                idx = conjDeltaNum + conjClass * rounds * setSize

                # Convert the delta to an integer, and pass it to the convert_delta function which will reduce the size if necessary.
                intData = int.from_bytes(data, byteorder=byte_order, signed=False)
                intData = convert_delta(intData)
                # Save the converted delta to the decSamples array/list.
                decSamples[idx]=intData

                # Run the garbage collector after reading one set to try to increase performance
                # Print the status every 40 sets if verbose is True
                if i % setSize == setSize-1:
                    collected = gc.collect()
                    
                    if ((i+1)//setSize)%1 ==0:
                        if verbose:
                            print(backspaces, end = "")
                            setsRead = f"{((i+1)//setSize):,d}"
                            spaces = " "*(printLen-len(setsRead))
                            print(spaces+setsRead, end="", flush=True)
            if verbose:
                backspaces = "\b"*(len(statusStr)+printLen)
                print(backspaces, end = "", flush=True)
        # We have finished reading all the data we need. Now write the decSamples array/list to the output path.
        for i in range(dataNeeded):
            out_file.write(decSamples[i].to_bytes(output_delta_bytes, byte_order, signed=False))

    # Print a status message if verbose is True
    if verbose:
        print("write_decimated_file - Wrote "+f"{(dataNeeded):,d}" + " samples.     ", end = "")
        print("dec x rounds x setSize = ", dec, "x", rounds, "x", setSize, "; rounds = ceil( numSets =", numSets, " / dec =", dec, ").")


# Purpose: Given an input file of deltas, write a file with the delta replaced with the ID of the subdistribution.
#
# Parameters:
#       in_path: The path to the file of deltas.
#       out_path: The path of the output file. 
#       input_delta_bytes: Number of bytes per delta in the in_path file.
#       subdist_cutoffs: A list of cutoffs for the subdistributions. 
#                       The first sub-distribution is from 0 to subdist_cutoffs[0]-1
#                       The ith sub-distribution is from subdist_cutoffs[i] to subdist_cutoffs[i+1]-1
#                       The last sub-distribution is from subdist_cutoffs[-1] to the maximum delta.
#                       There are len(subdist_cutoffs) + 1 sub-distributions.
#       byte_order: The order of the bytes of each delta in the in_path file and out_path file (e.g. 'little')
#       writeText: Whether the subdistribution number should be written as text rather than a binary value.
#                   NOTE: If writeText is True, there must be 36 or fewer subdistributions (i.e. len(subdist_cutoffs) <= 35)
# Return value:
#       A list of how many deltas are in each subdistribution.      
def write_subDist_id_file(in_path, out_path, input_delta_bytes = 8, subdist_cutoffs=[], verbose=True, byte_order = 'little', writeText = True):

    # Count how many deltas have been written in total to all the output files.
    countAll=0

    # Count how many deltas are written for each individual subdistribution.
    count = []

    # Keep a list of opened output files.
    fileList = []

    if writeText and len(subdist_cutoffs)>9+26:
        raise Exception("Error in function write_subDist_id_file - too many sub-distributions to write to text file; maximum number of cutoffs is 35; try writing in binary instead.\n \t write_subDist_id_file(" + in_path + ", " + out_path + ")")  
    elif len(subdist_cutoffs)>255:
        raise Exception("Error in function write_subDist_id_file - too many sub-distributions to write to binary file; maximum number of cutoffs is 255.\n \t write_subDist_id_file(" + in_path + ", " + out_path + ")")  

    try:
        # Open one output file, and set the count of deltas written so far to 0.
        if writeText:
            fileList.append(open(out_path, "w"))
        else:
            fileList.append(open(out_path, "wb"))
        for i in range(len(subdist_cutoffs)+1):
            count.append(0)

        # Open the input file (which has already been decimated).
        with open(in_path, "rb") as in_file:
            
            # Read the first delta
            data = in_file.read(input_delta_bytes) 

            #While there is still input data in the input file:
            while data:
                # Convert the delta to an integer.
                intData = int.from_bytes(data, byteorder=byte_order, signed=False)
                
                # Find to which number sub-distribution the delta should be written.
                # The default sub-distribution is the last file.
                subDistNum = len(subdist_cutoffs)

                # Check if the correct sub-distribution number is an earlier file, starting at file i=0.
                i=0
                while i < len(subdist_cutoffs):
                    if intData < subdist_cutoffs[i]:
                        subDistNum = i
                        break
                    i += 1
                
                # Format the sub-distribution number and write it to file.
                if writeText:
                    if subDistNum <= 9:
                        numToWrite=str(subDistNum)
                    else:
                        numToWrite = chr(ord("A") + subDistNum-10)
                else:
                    numToWrite = subDistNum.to_bytes(1, byte_order, signed=False)

                fileList[0].write(numToWrite)
                    
                # Count how many deltas have been written to the file.
                count[subDistNum] += 1
                # Count how many deltas have been written all together.
                countAll += 1

                # Read the next delta:
                data = in_file.read(input_delta_bytes)
    except:
        raise Exception("Error in function write_subDist_id_file(" + in_path + ", " + out_path + ")")     
    finally:
        fileList[0].close()
        if verbose:
            for i in range(len(subdist_cutoffs)+1):
                print("write_subDist_id_file - Wrote "+ f"{(count[i]):,d}" + " from subdistribution", i)
        if verbose:
            print("write_subDist_id_file - Wrote "+ f"{(countAll):,d}" + " samples in total.")
    return count    


# Purpose: Given an input file of (decimated) deltas, write multiple output files, 
#           where each output file contains only those deltas from one of the specified sub-distributions.
#           The output files may then be used for non_iid testing to generate an entropy estimate for the decimated data.
# Parameters:
#       in_path: The path to the file of decimated deltas.
#       out_path: The prefix for the path of the output files ("_<number>.bin" is appended for each output file). 
#       input_delta_bytes: Number of bytes per delta in the in_path file.
#       output_delta_bytes: Number of bytes per delta to write to the out_path files.
#       convert_delta: function that takes as input any positive integer which was input_delta_bytes bytes long 
#                       and returns an integer that can be represented with no more than output_delta_bytes bytes.
#       subdist_cutoffs: A list of cutoffs for the subdistributions. 
#                       The first sub-distribution is from 0 to subdist_cutoffs[0]-1
#                       The ith sub-distribution is from subdist_cutoffs[i] to subdist_cutoffs[i+1]-1
#                       The last sub-distribution is from subdist_cutoffs[-1] to the maximum delta.
#                       There are len(subdist_cutoffs) + 1 sub-distributions.
#       verbose: When True, write a status message with the number of samples written per file before returning.
#       byte_order: The order of the bytes of each delta in the in_path file and out_path file (e.g. 'little')
# Return value:
#       A list of how many deltas are in each subdistribution.  
#       
def write_subfile(in_path, out_path, convert_delta=unchanged, input_delta_bytes = 8, output_delta_bytes = 8, subdist_cutoffs=[], 
                  verbose=True, byte_order = 'little'):

    # Count how many deltas have been written in total to all the output files.
    countAll=0

    # Count how many deltas are written to each individual output file.
    count = []

    # Keep a list of opened output files.
    fileList = []

    try:
        # Open one output file for each sub-distribution, and set the count of deltas written so far to 0.
        for i in range(len(subdist_cutoffs)+1):
            out_pathi = out_path + "_" +str(i) + ".bin"
            fileList.append(open(out_pathi, "wb"))
            count.append(0)

        # Open the input file (which has already been decimated).
        with open(in_path, "rb") as in_file:
            
            # Read the first delta
            data = in_file.read(input_delta_bytes) 

            #While there is still input data in the input file:
            while data:
                # Convert the delta to an integer.
                intData = int.from_bytes(data, byteorder=byte_order, signed=False)
                
                # Find to which number file the delta should be written.
                # The default file is the last file.
                fileNum = len(subdist_cutoffs)

                # Check if the correct file number is an earlier file, starting at file i=0.
                i=0
                while i < len(subdist_cutoffs):
                    if intData < subdist_cutoffs[i]:
                        fileNum = i
                        break
                    i += 1
                
                # Send the delta to the 'convert_delta' function for any further conversion (e.g. down to 8 bits)
                intData = convert_delta(intData)

                # Write the delta to the correct file, which is number 'fileNum'
                fileList[fileNum].write(intData.to_bytes(output_delta_bytes, 'little', signed=False))
                    
                # Count how many deltas have been written to the file.
                count[fileNum] += 1
                # Count how many deltas have been written all together.
                countAll += 1

                # Read the next delta:
                data = in_file.read(input_delta_bytes)
    except:
        raise Exception("Error in function write_subfile(" + in_path + ", " + out_path + ")") 
 
    finally:
        # Close all the output files and if verbose = True, print a status message.
        for i in range(len(fileList)):
            fileList[i].close()
            if verbose:
                print("write_subfile - Wrote "+ f"{(count[i]):,d}" + " samples to "+out_path + "_" +str(i) + ".bin")
        if verbose:
            print("write_subfile - Wrote "+ f"{(countAll):,d}" + " samples in total.")
        return count


##  Purpose: This is a function that has as input the number of testing rounds performed and returns 
#       how many times any one of the 22 individual IID test may fail before there is an overall fail
#       for the decimation level being tested.
#   Parameters:
#       numTests: The number of testing rounds that will be performed.
#   Return value: 
#       The maximum number of rounds allowed to fail for an overall passing result.
#       This function returns Cutoff = binomial_cdf_inverse(n=numTests, p=1/1000, 1-q)
#       where q = 1 - (1-alpha)^(1/22) = 0.00046 and alpha = 0.01.
#       p = 1/1000 = the NIST designed false reject rate for each of the 22 different IID tests.
#       alpha = Pr(data that is IID fails numTests rounds of IID testing) = p-value or significance.
#       q = Pr(data that is IID fails numTests rounds of a single one of the 22 different IID tests).
def failTable(numTests):

    if numTests <= 1:
        return 0
    elif numTests <= 31:
        return 1
    elif numTests <= 146:
        return 2
    elif numTests <= 347:
        return 3
    elif numTests <= 621:
        return 4
    elif numTests <= 952:
        return 5
    elif numTests <= 1330:
        return 6
    else:
        return 7


# Purpose: Run IID testing on a decimated data file. Split the data into tests of 'setSize' deltas each, and record results of each test.
#          Save results in the format of exampleResultsList to the results_path. If overwrite==False, the previous contents of results_path is also written.
# Parameters:
#       in_path: Path to decimated deltas; deltas must be 1 byte each, ready for the NIST tool to read.
#       results_path: The path of the file where results should be written as they are generated.
#       overwrite: When True, overwrite the contents of the results_path. 
#              When False, read the results_path, append the results generated, and then write them to the results_path.
#       platform: A string that describes the data being tested, e.g. the OE name, project name, etc.
#       dec: The decimation level being tested. This has no impact on the testing run, since in_path is already decimated, 
#            but is recorded as part of the results.
#       numTests: How many rounds of IID testing should be performed.
#                 NOTE: If there is insufficient data, an exception is raised.
#       maxFails: A function that has as input the number of testing rounds performed and returns 
#               how many times any one of the 22 individual IID test may fail before there is an overall fail
#                for the decimation level being tested. E.g. use the failTable function.
#       setSize: The number of deltas in each IID testing round.
#       verboseRounds: Results of each testing round are printed as they are completed when verboseRounds is True.
#       verboseFinal: Overall results for each of the 22 IID tests are printed for all of the testing rounds when verboseFinal is true.
#       failEarly: When True, the testing will stop as soon as one or more IID tests have failed more  than maxFails times, 
#           instead of completing all the tests.
#       messageStart: The message to print at the start of the decimation testing when verboseRounds is True.
#       messageEnd: The message to print at the end of the decimation testing prior to printing the results when verboseRounds or verboseFinal is True.
#       IID tests: The arguments to pass to iid_main from stats90b, e.g. if only the chi1 test should be performed, use "-r chi1".
#             If testing for a single round should stop as soon as one of the 22 individual tests fails, use "-r abort1fail"
#             Leaving the string empty is equivalent to running all IID tests without aborting the round on the first failure.
# Return values: ('failure', 'totalPasses', 'totals', 'roundPassCount', 'roundTotalCount') 
#       failure: a boolean indicating whether the overall testing result for all rounds is a failure.
#       totalPasses: a dictionary providing the number of total passes for each of the 22 individual IID tests.
#       totals: a dictionary providing the total number of tests performed for each of the 22 individual IID tests.
#       roundPassCount: How many testing rounds passed overall (i.e. how many rounds where all 22 different IID tests passed)
#       roundTotalCount: How many testing rounds were carried out.
# NOTE: results in the format of exampleResultsList will be written to the results_path. This is different to the format of the values retuned by the function.
#       If overwrite==False, the previous contents of results_path is also written.
#       The result of testing this decimation level is in the last item of the results list in the results_path.
#       Results are written and overwritten as they are generated, so if the testing is killed before it completes, all results generated so far may be read from results_path.
#
def test_decimated_file(in_path, results_path, overwrite="", platform="<unspecified>", dec=0, numTests=1, maxFails=failTable, setSize=1000000, verboseRounds=True, verboseFinal=False, failEarly=False, 
                        messageStart="", messageEnd="", IIDtests=""):

    # Initialise status messages:
    if messageStart == "":
        messageStart = f"Starting testing for platform {platform}, decimation level = {dec} ..."
    if messageEnd == "":
        messageEnd = f"Overall result for platform {platform}, decimation level = {dec}:"

    # Initialise the dictionaries used to store the results.
    totalPasses = {}
    totals = {}
    roundPassCount =0
    roundTotalCount =0
    # Set a temporary file name for storing enough deltas for one round of testing.
    out_path = "temp_test_decimated_file.bin"

    # If we are not overwriting the contents of the results_path, read the existing results:
    results = result_open(results_path, overwrite)

    # So far, the testing has not failed.
    failure = False

    # Open the delta file.
    with open(in_path, "rb") as in_file:

        # If we are printing results of individual rounds, start the output...
        if verboseRounds:
            print("\n"+messageStart)
            print("{ testing round #: result }")
            print("{ ", end="")

        # For each round of testing...
        for i in range(numTests):

            # Store the deltas for this round of testing in the temporary file.  
            # If there are no deltas to read, print an error message and exit the program. 
            with open(out_path, "wb") as out_file:
                data = in_file.read(setSize)
                if not data:
                    raise Exception(f"test_decimated_file: ERROR: INPUT FILE ", in_path, " ENDED TOO SOON.\ntest_decimated_file: Needed {numTests} sets of size {setSize} deltas; only read i = {i} sets.")
                    sys.exit(-1)
                out_file.write(data)

            # Get ready the arguments to pass to the NIST testing suite. 
            # -q means 'quiet'
            # -r all means run all available IID tests
            # (other options are -r chi1, -r chi2, -r LRS, -r perm)
            if IIDtests == "":
                IIDtests = " -r all "
            argStr = "-q " + IIDtests + " " + out_path

            # Call the NIST IID testing tool, and store the results in a string.
            resStr = iid_main(argStr)

            # Convert the results string to a Python dictionary.
            res = json.loads(resStr)

            # Assume this round of testing passed until proven otherwise.
            thisTestPass = True

            # For each test name in the result dictionary, make sure it is in the dictionaries storing the number of passes and the total tests.
            # If this test name is a pass, add it to the count of passes for that test.
            # Add one to the total count for that test.
            # If any test did not pass, note that this round of testing failed by setting thisTestPass = False.
            for testName in res.keys():
                if testName not in totalPasses.keys():
                    totalPasses[testName]=0
                if testName not in totals.keys():
                    totals[testName]=0
                if res[testName]=="pass":
                    totalPasses[testName] += 1
                else:
                    thisTestPass = False
                totals[testName] += 1

                # If this particular IID test name has failed more times than allowed, set the overall failure variable to True.
                if totals[testName] - totalPasses[testName] > maxFails(numTests):
                    failure = True
            #Record whether this round of 22 tests passed.
            if thisTestPass:
                roundPassCount += 1
            roundTotalCount += 1

            # If printed output is required, write whether this round of testing passed or failed in a dictionary format.
            if verboseRounds:
                if i > 0:
                    print(", \t", end="")
                if thisTestPass:
                    print(i, ": \"pass\"", end="", flush=True)
                else:
                    print(i, ": \"FAILED\"", end="", flush=True)
            
            # Save the results to the results_path
            if i == 0:
                result_append(results, dec, totalPasses, totals, roundPassCount, roundTotalCount, platform, filename=in_path, datestamp=str(datetime.datetime.now()))
            else:
                result_overwrite_last(results, dec, totalPasses, totals, roundPassCount, roundTotalCount, platform, filename=in_path, datestamp=str(datetime.datetime.now()))
            result_write(results, results_path)


            # If we are to stop testing as soon as more tests than allowed have failed, check if we have failed.
            # If so, break out of the for loop so we can print and return the results.
            if failEarly:
                if failure:
                    break
                
    # All testing rounds have finished (or we failed early and are finished). 

    # Remove the temporary file:
    if os.path.exists(out_path):
        os.remove(out_path)

    # Print the results if required and return the results.
    if verboseRounds:
        print("}")

    if verboseFinal:
        print("\ntotal passes / total tests; maximum allowed fails = ", maxFails(numTests))

    testingRoundsCompleted = 0
    for testName in totals.keys():
        testingRoundsCompleted = totals[testName]
        if totals[testName] - totalPasses[testName] > maxFails(numTests):
            failure = True
            if verboseFinal:
                print(totalPasses[testName], "/", totals[testName], " : FAILED :" , testName)
        else:
            if verboseFinal:
                print(totalPasses[testName], "/", totals[testName], " : pass : " , testName)

    minPass = min(totalPasses.values())
    minKey = min(totalPasses, key=totalPasses.get)
    minTotal = totals[ minKey ]

    if verboseRounds or verboseFinal:
        print("")
        print(messageEnd+"\n", end="")
        str2 = f"\t| Rounds: {roundPassCount} / {roundTotalCount} = {roundPassCount/roundTotalCount*100:6.2f}%"
        str2 += f"\t| All individ. tests: {sum(totalPasses.values())} / {sum(totals.values())} = {sum(totalPasses.values())/sum(totals.values())*100:6.2f}% "
        print(str2, end = "")
        print("| Worst individ. test:", minPass, "/", minTotal, "=", f"{minPass/minTotal*100:6.2f}%", end="")
        if failure:
            print(" - FAILED ", end="")
        else:
            print(" - pass   ", end="")
        if minPass < minTotal:
            print("-", minKey, end="")
        print(" |\n")

    return failure, totalPasses, totals, roundPassCount, roundTotalCount


# BinSearchItem is a class for faciliting a binary search of decimation levels.
# Each BinSearchItem will be stored in a list with indicies from 0 to the maximum decimation level.
# Each BinSearchItem stores:
#   initialized: whether the following items have been initialized: parent, value, left, right, myMin, myMax 
#   value: its own decimation level, 
#   right: which decimation level to test next if this level passes (right < value)
#   left: which decimation level to test next if this level fails (left > value)
#   parent: which decimation level was tested immediately before this one 
#   myMin & myMax: the range of decimation levels that could still need testing if this node was reached (from myMin to myMax inclusive)
#   results: whether testing results for this decimation level exist 
#   failed: whether testing of this level failed 
#   passCount: a dictionary of the total passes for each of the 22 IID tests for this decimation level 
#   passTotalCount: a dictionary of the total tests carried out for each of the 22 IID tests for this decimation level 
#   roundPassCount: The number rounds where all 22 individual IID tests passed for this decimation level.
#   roundTotalCount: The total number of testing rounds carried out for this decimation level.
#   totalIndividualPasses: The total number of individual tests that passed for this decimation level (over all rounds and individual tests).
#   totalIndividualTests: The total number of individual tests for this decimation level (over all rounds and individual tests).
class BinSearchItem():
    def __init__(self):
        self.initialized = False
        self.parent = None
        self.value = None
        self.left = None
        self.right = None
        self.myMin = None
        self.myMax = None
        self.results = False
        self.failed = None
        self.passCount = None
        self.passTotalCount = None
        self.roundPassCount = 0
        self.roundTotalCount = 0
        self.totalIndividualPasses = 0
        self.totalIndividualTests = 0

    # Enable printing of value, parent, left, right myMin & myMax for debug purposes.
    def __str__(self):
        mystr = ""
        if self.initialized:
            mystr += "BinSearchItem: \n" 
            mystr += "\t" + str(self.value) + "\t: value " + "\n"
            mystr += "\t" + str(self.parent) + "\t: parent " + "\n"
            mystr += "\t" + str(self.left) + "\t: left " + "\n"
            mystr += "\t" + str(self.right) + "\t: right " + "\n"
            mystr += "\t" + str(self.myMin) + "\t: myMin " + "\n"
            mystr += "\t" + str(self.myMax) + "\t: myMax " + "\n"
            return mystr
        else:
           return "BinSearchItem: NOT INITIALIZED\n"

    # Initialise the BinSearchItem by providing a parent item.
    # This item will be to the right of the parent, and tested if the parent passes testing.
    # parent.right, parent.myMin, parent.vaue must already be set.
    def set_parent_right(self, parent):
        if parent.right != parent.value:
            self.initialized = True
            self.parent = parent.value
            self.value = parent.right
            # The range still needing testing if this item is reached is from the parent's minimum up to one less than the parent's value.
            self.myMin = parent.myMin
            self.myMax = parent.value - 1
            # If this item passes, we will next test an item midway between this item's value and the minimum (min. is the same for parent and this item.)
            self.right = (self.value-1-(self.myMin-1))//2 + self.myMin
            # If this item fails, we will next test an item midway between this item's value and the maximum (max. is one less than the parent's value)
            self.left = self.myMax - (self.myMax-(self.value+1-1))//2 

    # Initialise the BinSearchItem by providing a parent item.
    # This item will be to the left of the parent, and tested if the parent fails testing.
    # parent.left, parent.myMax, parent.vaue must already be set.
    def set_parent_left(self, parent):
        if parent.left != parent.value:
            self.initialized = True
            self.parent = parent.value
            self.value = parent.left
            # The range still needing testing if this item is reached is from the parent's value+1 up to the parent's maximum.
            self.myMin = parent.value + 1
            self.myMax = parent.myMax
            # If this item passes, we will next test an item midway between this item's value and the minimum (min. is the parent's value + 1)
            self.right = (self.value-1-(self.myMin-1))//2 + self.myMin
            # If this item fails, we will next test an item midway between this item's value and the maximum (max. is the parent's max.)
            self.left = self.myMax - (self.myMax-(self.value+1-1))//2 

    #Initialise the root of the binary tree. This item has no parent. 
    # The range of decimation levels to test is from this item's value to the minimum provided in myMin.
    def set_root(self, value, myMin):
        self.initialized = True
        self.parent = None
        self.value = value
        self.myMin = myMin
        self.myMax = value
        # If this item passes, we will next test an item midway between this item's value and the minimum.
        self.right = (self.value-1-(self.myMin-1))//2 + self.myMin
        # If this item fails, we will next test an item midway between this item's value and the maximum.
        # Since this item's value is equal to the maximum, self.left = self.value
        self.left = self.myMax - (self.myMax-(self.value+1-1))//2 

    # Save the decimation results (failed, passCount, passTotalCount, roundPassCount, roundTotalCount) for a decimation level in a BinSearchItem.
    # Also compute and save the results self.totalIndividualPasses and self.totalIndividualTests by summing the values in passCount and passTotalCount.
    def set_results(self, failed, passCount, passTotalCount, roundPassCount, roundTotalCount):
        self.results = True
        self.failed = failed
        self.passCount = passCount
        self.passTotalCount = passTotalCount

        self.roundPassCount = roundPassCount
        self.roundTotalCount = roundTotalCount
        self.totalIndividualPasses = sum(passCount.values())
        self.totalIndividualTests = sum(passTotalCount.values())


# init_sub_binary_tree is used to recursively initialise the binary tree. It should only be called by init_binary_tree.
# The 'tree' provided should be a list of BinSearchItems, with indicies up to the maximum decimation level.
# The tree[value] item must already be initialised. This funciton will recursively initialise the left and right items of tree[value].
# This function initialises the value, parent, left, right, myMin & myMax properties of the BinSearchItems, but does not do any decimation testing.
def init_sub_binary_tree(tree, value):
    # If the left or right item is the same as this one, then it has already been set.
    # Otherwise, use set_parent_right and set_parent_left to initialise the left and right items, 
    #   and then recursively call this function to initialise the children of the left and right items.
    if value != tree[value].right:
        tree[tree[value].right].set_parent_right(tree[value])
        init_sub_binary_tree(tree, tree[value].right)
    if value != tree[value].left:
        tree[tree[value].left].set_parent_left(tree[value])
        init_sub_binary_tree(tree, tree[value].left)


# Purpose: Initialise and return a binary tree, given a maximum decimation level, 'value' and minimum decimation level, 'minDec.'
#   This initialises the value, parent, left, right, myMin & myMax properties of the BinSearchItems, but does not do any decimation testing.
# Parameters:
#   value: The maximum decimation level to be tested.
#   minDec: The minimum decimation level to be tested.
#
# Return value: 
#    A list of initialised BinSearchItems.
#
def init_binary_tree(value, minDec):
    # Create the tree as a list of BinSearchItems, one item for each decimation level.
    tree = [BinSearchItem() for i in range(value+1)]
    # Initialise the root BinSearchItem of the tree, which will be the 'value' item.
    tree[value].set_root(value, minDec)
    # Call init_sub_binary_tree to recursively initialise the children of the root node.
    init_sub_binary_tree(tree, tree[value].value)
    return tree



exampleResultItem =      {
    "dec": 2, # Decimation level tested
    "passList": {
        "chiSqIndependence": [ #Name of individual IID test carried out
            2, # Number of passing chiSqIndependence tests
            5  # Total number of chiSpIndependence tests
        ],
        "chiSqGoodnessFit": [ #Insert as manay test names as were carried out in the "passList" dictionary.
            2,
            2
        ]
    },
    "roundPass": 2, # Number of passing rounds of testing carried out. One round consists of running each of the 22 (or fewer) IID tests once.
    "roundTotal": 5, # Number of rounds of testing carried out
    "platform": "OE # 1", # The identifier for the platform that produced the data
    "filename": "./data/Example_decimate_bin_search_File1.bin", # The name of the file containing un-decimated data
    "datestamp": "2024-07-07 22:07:28.683159" # The time all round#Name of individual IID test carried outTotal rounds of testing ended.
    }
exampleResultItem2 =     {
    "dec": 3,
    "passList": {
        "chiSqIndependence": [
            5,
            5
        ],
        "chiSqGoodnessFit": [
            4,
            5
        ]
    },
    "roundPass": 4,
    "roundTotal": 5,
    "platform": "OE # 1",
    "filename": "./data/Example_decimate_bin_search_File1.bin",
    "datestamp": "2024-07-07 22:26:20.560120"
    }
exampleResultsList = [exampleResultItem, exampleResultItem2]

# Pupose: Read the decimation testing results from file.
# Parameters:
#   results_path: The path where the results should be read in JSON format (same format as exampleResultsList).
#   overwrite: When True, instead of reading the file, an empty list is returned.
# Return value:
#   results: The results read from results_path, or an empty list when the file does not exist, its size is 0, or overwrite==True.
def result_open(results_path, overwrite):
    if overwrite or (not os.path.exists(results_path)) or os.path.getsize(results_path)==0:
        results = []
    else:
        with open(results_path, "r") as resFile:
            results = json.loads(resFile.read())
            if not isinstance(results, list):
                raise Exception(f"Error in function result_open - \n\t\tFile = {results_path} \n\t\tFile did not contain a JSON/Python list.")
            for i in range(len(results)):
                if "dec" not in results[i].keys():
                    raise Exception(f"Error in function result_open - \n\t\tList index = {i}; File = {results_path} \n\t\tList index does not contain key \"dec\" with decimation level.")  
                if "passList" not in results[i].keys():
                    raise Exception(f"Error in function result_open - \n\t\tList index = {i}; File = {results_path} \n\t\tList index does not contain key \"passList\" with list of how many passes for each IID test type.")  
                if "roundPass" not in results[i].keys():
                    raise Exception(f"Error in function result_open - \n\t\tList index = {i}; File = {results_path} \n\t\tList index does not contain key \"roundPass\" with total number of passing rounds.")  
                if "roundTotal" not in results[i].keys():
                    raise Exception(f"Error in function result_open - \n\t\tList index = {i}; File = {results_path} \n\t\tList index does not contain key \"roundTotal\" with total number of rounds tested.")
                if "platform" not in results[i].keys():
                    raise Exception(f"Error in function result_open - \n\t\tList index = {i}; File = {results_path} \n\t\tList index does not contain key \"platform\" with details of platform being tested.")
                if "filename" not in results[i].keys():
                    raise Exception(f"Error in function result_open - \n\t\tList index = {i}; File = {results_path} \n\t\tList index does not contain key \"filename\" with details of filename of data being tested.")
                if "datestamp" not in results[i].keys():
                    raise Exception(f"Error in function result_open - \n\t\tList index = {i}; File = {results_path} \n\t\tList index does not contain key \"datestamp\" with details of when test was run.")
    return results


# Pupose: Save the decimation testing results to file.
# Parameters:
#   results: The list of results (same format as exampleResultsList)
#   results_path: The path where the results should be written in JSON format.
def result_write(results, results_path):
    with open(results_path, "w") as resFile:
        resFile.write(json.dumps(results, indent=5))



# Purpose: Append the results of testing one decimation level to the list of results.
# Parameters: 
#   results: The current list of results (same format as exampleResultsList)
#   The remaining parameters contain the testing details to insert in the new item appended to results:
#       dec: the decimation level tested
#       passList: The dictionary of individual IID tests stating how many tests passed, e.g. {"chiSqIndependence": 5, ...}
#       passListTotals: The dictionary of individual IID tests stating how many tests were done in total, e.g. {"chiSqIndependence": 7, ...}
#       roundPass: The total number of passing rounds (one round consists of all the individual tests being tested.)
#       roundTotal: The total number of rounds completed.
#       platform: A string that describes the data that were tested, e.g. the OE name, project name, etc.
#       filename: The file path of the un-decimated deltas that were tested.
#       datestamp: A string with the datestamp of when the testing completed.
# Outcome:
#   A new item with the details provided is appended to results.
#
def result_append(results, dec, passList, passListTotals, roundPass, roundTotal, platform="", filename="", datestamp=""):
    newRoundPass = {test:[passList[test], passListTotals[test]] for test in passList}
    results.append({"dec": dec, "passList": newRoundPass, "roundPass": roundPass, "roundTotal": roundTotal, "platform": platform, "filename": filename, "datestamp": str(datestamp)})


# Purpose: Sort the recorded results by the following values: platform, then decimation level, then total testing rounds, then total passing individual IID tests.
# Parameters: 
#   results: The current list of results (same format as exampleResultsList)
# Note: results is modified by sorting. There is no return value.
#
def result_sort(results):
    results.sort(key=lambda d: d['platform']+"!!!"+str(((1000000+d['dec'])*1000000+d['roundTotal'])*10000000+
                                                       sum( map(itemgetter(0), d['passList'].values()) )))
    


# Purpose: For internal use - Results from each round of testing are saved at the end of the results list as they are generated.
#          Each time a new round is completed, the results previously written are overwritten with the latest round's results included.
# Parameters: 
#   results: The current list of results (same format as exampleResultsList)
#   The remaining parameters contain the testing details to insert in the new item appended to results:
#       dec: the decimation level tested
#       passList: The dictionary of individual IID tests stating how many tests passed, e.g. {"chiSqIndependence": 5}
#       passListTotals: The dictionary of individual IID tests stating how many tests were done in total, e.g. {"chiSqIndependence": 7}
#       roundPass: The total number of passing rounds (one round consists of all the individual tests being tested.)
#       roundTotal: The total number of rounds completed.
#       platform: A string that describes the data that were tested, e.g. the OE name, project name, etc.
#       filename: The file path of the un-decimated deltas that were tested.
#       datestamp: A string with the datestamp of when the testing completed.
# Outcome:
#   The last item in results is removed, and a new item with the details provided is appended in its place.
#
def result_overwrite_last(results, dec, passList, passListTotals, roundPass, roundTotal, platform="", filename="", datestamp=""):
    results.pop()
    result_append(results, dec, passList, passListTotals,  roundPass,  roundTotal, platform=platform, filename=filename, datestamp=datestamp)

    

# Purpose: Return a string indicating whether results[resNum] passed or failed, including whether 
#          the minimum number of requested tests were carried out.
# Parameters:
#   results: The list of results (same format as exampleResultsList)
#   resNum: results[resNum] is the item whose pass/fail status should be returned.
#   minTests: A desired minimum number of tests or rounds to be carried out. Passing tests having fewer than 
#             minTests rounds will be flagged with an *. Fails with fewer than maxFails(minTests) 
#             test faillures will also be flagged with an *.
#   testID: A string containing the name of the individual IID test to check. 
#           If testID="", the 'worst' test is selected and checked. 
#           'Worst' means the tests having the lowest number of passes, and of those, the test with the maximum total tests.
#   maxFails: A function which takes as input the number of tests and 
#             returns the maximum number of failing tests compatible with an overall pass.
#             E.g. if at least 147 passes out of 150 tests is required to declare a pass over the 150 tests, then 
#             maxFails(150) returns 3 = 150 - 147.
#             Typically, the provided 'failTable' function is used, but users may supply their own if desired.
# Return value: outcome
#   outcome has the following possible values and meanings:
#       "FAIL" - Enough individual tests failed that the overall result is a fail,
#                    whether the cutoff is for the actual number of rounds or the minimum number of rounds.
#       "FAIL *" - The actual number of rounds failed, but not enough rounds were tested to know if it would
#                    have failed if the requested number of rounds were tested.
#       "pass *" - The actual number of rounds passed, but less than the requested minimum number of rounds were tested.
#       "pass" - At least the requested minimum number of rounds were tested and they passed.
def result_outcome(results, resNum, minTests, testID="", maxFails=failTable):
    needStarMessage = False
    # Find how many tests passed for test 'testID', or the minimum if testID == ""
    # Also find the maximum total out of which there were this many passes.
    if testID == "":
        passing = min(map(itemgetter(0),results[resNum]["passList"].values()))
        testIDs = { t:results[resNum]["passList"][t] \
                    for t in [test for test in results[resNum]["passList"].keys() if results[resNum]["passList"][test][0] == passing]}
        total = max(map(itemgetter(1), testIDs.values()))
        testID = [k for k in testIDs.keys() if testIDs[k][1]==total][0]
    else:
        passing = results[resNum]["passList"][testID][0]
        total = results[resNum]["passList"][testID][1]


    # Find the maximum number of fails to still pass for the actual number of rounds tested.
    thisMaxFails = maxFails(total)
    # Find the maximum number of fails to still pass for the requested minimum number of rounds tested.
    maxMaxFails = maxFails(minTests)
    # Find out the actual number of fails there were.
    thisFails = total - passing
    # Set the outcome
    if thisFails > thisMaxFails:
        if thisFails > maxMaxFails:
            # It failed whether the cutoff is for 
            # the actual number of rounds or the desired minimum number of rounds.
            outcome = "FAIL"
        else:
            # It failed for the actual number of rounds, but not enough rounds were tested
            #  to know if if would have failed for the requested minimum number of rounds.
            outcome = "FAIL *"
            needStarMessage = True
    else:
        if total < minTests:
            # It passed for the actual number of rounds, but not enough rounds were tested
            # to meet the minimum requested number of rounds.
            outcome = "pass *"
            needStarMessage = True
        else:
            # It passed and enough rounds were tested.
            outcome = "pass"
    return outcome, needStarMessage


# Purpose: Return a list of results containing only those results in the specified dateRange.
# Parameters:
#   results: The list of results (same format as exampleResultsList)
#   dateRange:  Use dateRange=["",""] or ["earliest", "latest"] to return all results. 
#               Otherwise, set the strings in the list to the datestamps at the start and end of the range to be returned.
#               NOTE: An example of a full datestamp is: "2024-07-08 09:52:44.204973" - even if the datestamps printed are truncated.
#                     If you use shorter strings in the dateRange, make sure that the when sorted, the full datestamp strings for the desired results
#                     fall between the strings you specify (e.g. you may need to add a second to the last datestamp to retrieve all desired items).
# Return value: newResults
#   newResults: Items from results within the specified dateRange.
def result_datestamp_range(results, dateRange):
    # Set results to a new list containing only those results with dates in the desired datestamp range.
    # A start datestamp of "" or "earliest" means include dates starting from the earliest datestamp in the list.
    # An end datestamp of "" or "latest" means include dates going to the latest datestamp in the list.
    if dateRange[1] == "" or dateRange[1]=="latest":
        endDate = str(datetime.datetime.now())[:]
    else:
        endDate = dateRange[1]

    if (dateRange[0] == "" or dateRange[0]=="earliest"):
        startDate = "earliest"
    else:
        startDate = dateRange[0]

    if (startDate != "earliest"):
        # Return only results with datestamp > startdate and < endDate
        newResults = [results[i] for i in range(len(results)) if (results[i]["datestamp"]>= startDate) and results[i]["datestamp"]<= endDate]
    else:
        # Return results with datestamp < endDate
        newResults = [results[i] for i in range(len(results)) if results[i]["datestamp"]<= endDate]
    return newResults




# Purpose: Print the results of decimation testing
# Parameters:
#       resultsList: A list of individual Decimation test results. 
#                   Each result in the list is a dictionary with the same structure as the exampleResultItem above.
#       maxFails:   A function which takes as input the number of tests and 
#                   returns the maximum number of failing tests compatible with an overall pass.
#                   E.g. if at least 147 passes out of 150 tests is required to declare a pass over the 150 tests, then 
#                   maxFails(150) returns 3 = 150 - 147.
#                   Typically, the provided 'failTable' function is used, but users may supply their own if desired.
#       minTests:   A desired minimum number of tests or rounds to be carried out. Testing which has fewer than 
#                   minTests rounds may be suppressed with printLowRounds=False.
#                   When not suppressed, passing tests having fewer than minTests rounds will be flagged with an `*`. 
#                   Fails with fewer than maxFails(minTests) test faillures will also be flagged with an `*`.
#       printLowRounds: When False, results with fewer than 'minTests' rounds are not printed.
#                   NOTE: This excludes results based on the overall rounds only (results[resNum]["roundTotal"]), 
#                       not the rounds for individual IID tests (results[resNum]["passList"][testName][1]),
#                       which may be fewer if testing used the "-r abort1Fail" option.
#       platformList:   A list of platforms to print. Other platforms are ignored. If platformList == [], all platforms are printed.
#       printSet:   A set of table columns to print in the output. 
#                   To print all columns, use an empty set, {}, or list all options: {"roundPass", "passList", "filename", "datestamp", "platform"}.
#                   For the minimum columns, {"basic"} may be used.
#                   Otherwise, include the desired columns out of {"roundPass", "passList", "filename", "datestamp", "platform"}.
#       dateRange:  Use dateRange=["",""] to print all dates. Otherwise, set the strings in the list to the datestamps at the 
#                   start and end of the range to be printed.
#                   NOTE: An example of a full datestamp is: "2024-07-08 09:52:44.204973" - even if the datestamps printed are truncated.
#                       If you use shorter strings in the dateRange, make sure that the when sorted, the full datestamp strings in the results
#                       fall between the strings you specify (e.g. you may need to add a second to the last datestamp to retrieve all desired items).
#       shortDatestamp: When True, results are printed with datestamps truncated to the seconds, e.g. "2024-07-08 09:52". This does not affect 
#                   the length of the datestamp stored in the results; nor does it affect the dateRange, which is still based on the full length.
#       printAllIndividTestResults: When True, results for each of the individual IID tests in the "passList" are printed for each result item, one per line.
#                   When False, each result item is summarised in a single line of output, with only the results of the worst individual IID test listed.
#                   NOTE: When printAllIndividTestResults = False, if more than one individual IID test is 'worst', only one is printed.
#                   NOTE: 'worst' is considered to be the tests with the minimum number of passes, and of those, the test with the maximum number of tests.
#       printSorted: Set to True if a copy of the resultsList should be sorted before printing. Otherwise, results are grouped by platform but printed unsorted.
#                       NOTE: A copy of the resultsList is sorted before the results are printed, so that the original list 
#                             remains unsorted but the results are printed in a sorted order.
def result_print(resultsList, maxFails=failTable, minTests=1, printLowRounds=True, platformList=[], printSet={}, dateRange=["",""], 
                 shortDatestamp=False, printAllIndividTests=False, printSorted=True):
    
    # When printing sorted results, copy the results so they may be sorted without modifying them.
    if printSorted:
        results = resultsList.copy()
        result_sort(results)
    else:
        results = resultsList

    # Count how many result items were printed and report it at the end.
    numResultsPrinted = 0

    # Set the length of the table border based on which columns are being printed.
    tableHorizBorderLen = 186 
    if len(printSet) > 0:
        if "platform" not in printSet:
            tableHorizBorderLen -= 28
        if "datestamp" not in printSet:
                tableHorizBorderLen -= 29
        if "filename" not in printSet:
            tableHorizBorderLen -= 12
        if "passList" not in printSet:
            tableHorizBorderLen -= 75
        if "roundPass" not in printSet:
            tableHorizBorderLen -= 24
        if "datestamp" in printSet and shortDatestamp:
            tableHorizBorderLen -= 10
    else:
        if shortDatestamp:
            tableHorizBorderLen -= 10

    # Print a boundary string for the start of the output from this funciton.
    boundaryStr = "_"*80
    print(boundaryStr)

    # Record the total number of results in the list.
    totalResultsInList = len(results)

    # If required, set results to a new list containing only those results with dates in the desired datestamp range.
    # A start datestamp of "" or "earliest" means include dates starting from the earliest datestamp in the list.
    # An end datestamp of "" or "latest" means include dates going to the latest datestamp in the list.
    results = result_datestamp_range(results, dateRange)

    # Print the time that the results are printed.
    print(f"\n Decimation results printed at: {datetime.datetime.now()}\n")

    # Provide information about which options were passed to the function, and which results out of the list will be printed.
    if dateRange[1] == "" or dateRange[1]=="latest":
        endDate = str(datetime.datetime.now())[:]
    else:
        endDate = dateRange[1]
    if (dateRange[0] == "" or dateRange[0]=="earliest"):
        startDate = "earliest"
    else:
        startDate = dateRange[0]
    print(f"   There are a total of {totalResultsInList} results in the list and {len(results)} results in {[startDate, endDate]}.")
    if not printLowRounds:
        print(f"   Results with fewer than {minTests} rounds of testing will not be printed.")
    if len(platformList) > 0:
        print(f"   Only results for the following platforms will be printed:    {platformList}.")
    else:
        print("   Results for all platforms will be printed.")
    if len(printSet) > 0:
        printAllSet = {"basic", "roundPass", "passList", "filename", "datestamp", "platform"}
        print(f"   Data must be in this printSet to be printed:      {printSet}")
        print('        (to print all, use printSet={} or printSet={"basic", "roundPass", "passList", "filename", "datestamp", "platform"}')
    print("")

    # Define the longest test name and create an equivalent number of spaces for printing purposes later.
    longestTestName = "longestRepeatedSubstring"
    longestTestNameSpaces = " "*len(longestTestName)

    # If a list of attributes to print was not provided, print every key type in the results list.
    if len(printSet) == 0:
        printSet = {k for j in range(len(results)) for k in results[j].keys()}

    # If a list of platforms to print was not provided, 
    # make a sorted list of all the different platforms in the results.
    if len(platformList) == 0:
        platformList = sorted({ results[j]["platform"] for j in range(len(results)) })

    # Now we are ready to start printing results for each platform...
    for plat in range(len(platformList)):

        # Printing the platform header containing the platform name:
        platStr = f"----------  PLATFORM: {platformList[plat]} ----------"
        dashStr = "-"*len(platStr)
        print(" " + dashStr)
        print(" " + platStr)
        print(" " + dashStr)
        print("")

        # Create a list of the results for this platform only.
        platResults = [results[j] for j in range(len(results)) if results[j]["platform"]==platformList[plat]]

        # If filenames were requested, list these at the beginning of the output for each platform
        # and assign a file ID to be printed in the result listing.
        # The fileID uses a 3 digit platform number followed by a 3 digit file number.
        # If the same filename is used for different platforms, it will be assigned a different ID for each platform.
        if "filename" in printSet:
            # We are printing filenames. 
            fileList = sorted({platResults[j]["filename"] for j in range(len(platResults))})
            fileID = {fileList[j] : f"F.{plat+1:03d}.{j+1:03d}" for j in range(len(fileList))}
            print("   File list:")
            for j in range(len(fileList)):
                print(f"\t+ {fileID[fileList[j]]} = \"{fileList[j]}\"")
            print("")

        # Print the headings for the results table:
        tableHorizBorder = "-"*tableHorizBorderLen
        tableHorizBorder = "\t" + tableHorizBorder
        print(tableHorizBorder)
        print("\t|", end = "")
        print(f" Dec  |", end = "")
        print(f" Outcome |", end = "")
        if "roundPass" in printSet:
            print(f"   Testing Rounds      |", end = "")
        if "passList" in printSet:
            print(f" Individual IID Tests  |", end = "")
            print(f" Worst Individ. Test     ", end = "")
            print(longestTestNameSpaces + " |", end = "")
        if "filename" in printSet:  
            print(f"  File ID  |", end = "")
        if "datestamp" in printSet:
            # Print the heading for the datestamps, e.g.     Date  /  Time         
            #                                            2024-07-05 19:15:42.891574     
            if shortDatestamp:
                print("   Date  /  Time  |", end = "")   
            else:
                print("     Date  /  Time          |", end = "")   
        if "platform" in printSet:     
            print("  Platform  ", end = "")   
        
        print("")
        print(tableHorizBorder)

        # Record whether asterisks were used to indicate results with too few numbers of tests completed.
        needStarMessage = False

        # Make sets to record the passing decimation levels for this platform. The minimum will be printed at the end.
        passingDecSet = set()
        passingStarDecSet = set()

        # Loop through platResults to print each result, one result per line
        for res in range(len(platResults)):

            # If there were less than the desired minimum number of rounds of testing and printLowRounds is False, don't print this result.
            if not printLowRounds:
                if platResults[res]["roundTotal"] < minTests:
                    continue
            
            # Count how many results have been printed.
            numResultsPrinted += 1

            # Print decimation level
            print("\t|", end = "")
            print(f" {platResults[res]['dec']:4d} |", end = "")

            # Print overall outcome based on the 22 individual IID testing results.

            # Find the outcome:
            if platResults[res]["roundTotal"]==0 or len(platResults[res]["passList"]) == 0:
                # There were 0 rounds tested. Probably testing was requested but there was
                # not enough data to test the level of decimation requested.
                outcome = "NO DATA"

                # Print the outcome but do not print any further details from this result to avoid divide-by-zero errors.
                print(f" {outcome} |")
                continue
            else:
                # Make sure there was at least one test that ran at least once.
                if sum(map(itemgetter(1), platResults[res]["passList"].values())) == 0:
                    outcome = "0 TESTS"
                    # Print the outcome but do not print any further details from this result to avoid divide-by-zero errors.
                    print(f" {outcome} |")
                    continue
                else:
                    # Call result_outcome to find the 'worst' of the 22 IID tests and whether it is an overall pass or fail.
                    # This also returns whether we need to print the message for asterisks 
                    #   (i.e. if there less than the requested number of tests)
                    outcome, needStarMessageTemp = result_outcome(platResults, res, minTests, testID="", maxFails=maxFails )
                    needStarMessage = needStarMessage or needStarMessageTemp
                    
                    if outcome == "pass":
                        passingDecSet.add(platResults[res]["dec"])
                        passingStarDecSet.add(platResults[res]["dec"])
                    if outcome == "pass *":
                        passingStarDecSet.add(platResults[res]["dec"])

                    # Make the outcome the right length:
                    outcome = outcome + " "*(7-len(outcome))
            
            # Print the outcome
            print(f" {outcome} |", end="")
            
            # Print the overall round results (all 22 IID tests = 1 round)
            if "roundPass" in printSet:
                print(f" {platResults[res]['roundPass']:4d} / {platResults[res]['roundTotal']:4d} = {platResults[res]['roundPass']/platResults[res]['roundTotal']*100:6.2f}% |", end = "")

            # Print the overall stats for all the individual IID tests and the 'worst' of the individual IID test results
            if "passList" in printSet:
                # For all individual IID tests, print total passes.
                passListSum = sum(map(itemgetter(0), platResults[res]["passList"].values()))
                passListSumOutOf = sum(map(itemgetter(1), platResults[res]["passList"].values()))
                print(f" {passListSum:4d} / {passListSumOutOf:4d} = {passListSum/passListSumOutOf*100:6.2f}% |", end = "")
            
                # Print the worst individual IID test result.
                # This is the minimum number of passes, and out of possible totals for that number of passes, the maximum total.
                minPass = min(map(itemgetter(0), platResults[res]["passList"].values()))
                testIDs = { t:platResults[res]["passList"][t] \
                    for t in [test for test in platResults[res]["passList"].keys() if platResults[res]["passList"][test][0] == minPass]}
                minTotal = max(map(itemgetter(1), testIDs.values()))
                if minTotal > 0:
                    rate = minPass/minTotal
                else:
                    rate = 0.00
                minKey = [k for k in testIDs.keys() if testIDs[k][1]==minTotal][0]

                # If all of the tests passed for the 'worst' test, assume that every individual IID test passed, and there is
                # no need to print which test was the 'worst' test since they all passed.
                if minPass == minTotal:
                    minKey = ""
                spaces = " "*(len(longestTestName) - len(minKey))
                print(f" {minPass:4d} / {minTotal:4d} = {rate*100:6.2f}% - {minKey}{spaces} |", end = "")

            # Print the file ID
            if "filename" in printSet:     
                print(f" {fileID[platResults[res]['filename']]} |", end="")

            # Print the datestamp
            if "datestamp" in printSet:
                if platResults[res]["datestamp"] == "":
                    if shortDatestamp:
                        print("                  |", end="")
                    else:    
                        print("                            |", end="")
                else:
                    if shortDatestamp:
                        print(f" {platResults[res]['datestamp'][:16]} |", end="")
                    else:    
                        print(f" {platResults[res]['datestamp']} |", end="")

            # Print the platform
            if "platform" in printSet:
                # Print the platform
                print(f" {platResults[res]['platform']} |", end="")
        
            # Start a new line of output.
            print("")

            # If separate results for each of the 22 individual IID tests are requested, print them with one test per line.
            if printAllIndividTests:
                spaces = "\t" + " "*19
                print(f"{spaces}{'~'*47}")
                for testName in platResults[res]["passList"].keys():
                    outcome, needStarMessageTemp = result_outcome(platResults, res, minTests,  testID=testName, maxFails=maxFails)
                    needStarMessage = needStarMessage or needStarMessageTemp
                    if platResults[res]['passList'][testName][1] > 0:
                        rate = platResults[res]['passList'][testName][0] / platResults[res]['passList'][testName][1]
                    else:
                        rate = 0.0
                    print(f"{spaces} {platResults[res]['passList'][testName][0]:4d} / {platResults[res]['passList'][testName][1]:4d} = {rate*100:6.2f}% : {outcome} : {testName}")
                # Separate individual tests from the next table line with two blank lines.
                print(f"")
                print("")

        # Finish the results table for each platform with the table border.
        print(tableHorizBorder)

        # Print the minimum passing decimation levels
        if len(passingDecSet)==0:
            passingDecLevel = "None"
        else:
            passingDecLevel = min(passingDecSet)
        if len(passingStarDecSet)==0:
            passingStarDecLevel = "None"
        else:
            passingStarDecLevel = min(passingStarDecSet)
        print(f"\t  Minimum passing level (at least {minTests:6d} tests):         {passingDecLevel}.")
        
        # Print the asterisk messages if any were used.
        if needStarMessage:
            print(f"\t  Minimum passing level (no minimum tests requirement):  {passingStarDecLevel} *.")
            print(f"\n\t  * = Total testing rounds < minimum number of testing rounds requested = {minTests}.\n")

    # Print how many result items were printed in total, and a boundary for the end of the function output.        
    boundaryStr = "="*80
    print(f" Printed {numResultsPrinted} of {totalResultsInList} results.")
    print(boundaryStr)
    print("")



# Purpose: Return the minimum passing decimation level for the requested results.
# Parameters:
#       resultsList: A list of individual Decimation test results. 
#                   Each result in the list is a dictionary with the same structure as the exampleResultItem above.
#       maxFails:   A function which takes as input the number of tests and 
#                   returns the maximum number of failing tests compatible with an overall pass.
#                   E.g. if at least 147 passes out of 150 tests is required to declare a pass over the 150 tests, then 
#                   maxFails(150) returns 3 = 150 - 147.
#                   Typically, the provided 'failTable' function is used, but users may supply their own if desired.
#       minTests:   A desired minimum number of tests or rounds to be carried out. Testing which has fewer than 
#                   minTests rounds may be ignored with checkLowRounds=False.
#                   When not ignored, passing tests having fewer than minTests rounds will be flagged. 
#                   Fails with fewer than maxFails(minTests) test faillures will also be flagged.
#       checkLowRounds: When False, results with fewer than 'minTests' rounds are not checked.
#                   NOTE: This excludes results based on the overall rounds only (results[resNum]["roundTotal"]), 
#                       not the rounds for individual IID tests (results[resNum]["passList"][testName][1]),
#                       which may be fewer if testing used the "-r abort1Fail" option.
#                       However, if the 'worst' of the individual IID tests passes with fewer than minTests rounds, 
#                       it will be included in calculations for minPassingStarDecLevel, not minPassingDecLevel.
#       platformList:   A list of platforms to check. Other platforms are ignored. If platformList == [], all platforms are checked.
#       dateRange:  Use dateRange=["",""] to check all dates. Otherwise, set the strings in the list to the datestamps at the 
#                   start and end of the range to be checked.
#                   NOTE: An example of a full datestamp is: "2024-07-08 09:52:44.204973" - even if the datestamps printed are truncated.
#                       If you use shorter strings in the dateRange, make sure that the when sorted, the full datestamp strings in the results
#                       fall between the strings you specify (e.g. you may need to add a second to the last datestamp to retrieve all desired items).
#        NOTE: 'worst' is considered to be the test(s) with the minimum number of passes, and of those, the test(s) with the maximum number of tests.

def result_min_pass_level(results, maxFails=failTable, minTests=1, checkLowRounds=True, platformList=[], dateRange=["",""]):

    # If required, set results to a new list containing only those results with dates in the desired datestamp range.
    # A start datestamp of "" or "earliest" means include dates starting from the earliest datestamp in the list.
    # An end datestamp of "" or "latest" means include dates going to the latest datestamp in the list.
    results = result_datestamp_range(results, dateRange)

    # Check only those results for the platform(s) selected. If no platforms are selected, check all results.
    if len(platformList) != 0:
        results = [results[j] for j in range(len(results)) if (results[j]["platform"] in platformList) ]

    # Make sets to record the passing decimation levels. The minimum will be returned at the end.
    passingDecSet = set()
    passingStarDecSet = set()

    # Loop through results to find the passing decimation levels.
    for res in range(len(results)):

        # If there were less than the desired minimum number of rounds of testing and checkLowRounds is False, 
        #   don't check this result.
        if not checkLowRounds:
            if results[res]["roundTotal"] < minTests:
                continue
        
        # Find overall outcome based on the 22 individual IID testing results.

        # Find the outcome:
        if results[res]["roundTotal"]==0 or len(results[res]["passList"]) == 0:
            # There were 0 rounds tested. Probably testing was requested but there was
            # not enough data to test the level of decimation requested.
            outcome = "NO DATA"

            # Do not check any further details from this result.
            continue
        else:
            # Make sure there was at least one test that ran at least once.
            if sum(map(itemgetter(1), results[res]["passList"].values())) == 0:
                outcome = "0 TESTS"
                # Do not check any further details from this result.
                continue
            else:
                # Call result_outcome to find the 'worst' of the 22 IID tests and whether it is an overall pass or fail.
                # This also returns whether there was less than the requested number of tests (needStarMessageTemp).
                outcome, needStarMessageTemp = result_outcome(results, res, minTests, testID="", maxFails=maxFails )
                
                if outcome == "pass":
                    passingDecSet.add(results[res]["dec"])
                    passingStarDecSet.add(results[res]["dec"])
                if outcome == "pass *":
                    passingStarDecSet.add(results[res]["dec"])


    # Return the minimum passing decimation levels
    if len(passingDecSet)==0:
        passingDecLevel = None
    else:
        passingDecLevel = min(passingDecSet)

    if len(passingStarDecSet)==0:
        passingStarDecLevel = None
    else:
        passingStarDecLevel = min(passingStarDecSet)
    
    return [passingDecLevel, passingStarDecLevel]





# Purpose: Use a binary search to find the lowest passing decimation level for a given file of (un-decimated) deltas.
# Parameters:
#   delta_path: The path of the file containing the un-decimated deltas.
#   results_path: The path of the file where results should be written as they are generated.
#  overwrite: When True, overwrite the contents of the results_path. 
#              When False, read the results_path, append the results generated and then write them to the results_path.
#  platform: A string that describes the data being tested, e.g. the OE name, project name, etc.
#   maxDec: The maximum decimation level to test.
#   minDec: The minimum decimation level to test.
#   numTestsRequested: The number of tests to perform per decimation level. If there are insufficient deltas, fewer tests will be performed.
#               Warning: If there is insufficient data for any test, the program will perform fewer tests for that level of decimation testing. 
##  maxFails: A function that has as input the number of testing rounds performed and returns 
#               how many times any one of the 22 individual IID test may fail before there is an overall fail
#                for the decimation level being tested.
#   testSize: How many deltas are tested in each IID test
#   dec_multiplier: Only decimation levels which are multiples of dec_multiplier will be tested.  Use dec_multiplier = 1 to test all levels.
#   input_delta_bytes: Number of bytes per delta in the in_path file.
#   convert_delta: function that takes as input any positive integer which was input_delta_bytes bytes long 
#                       and a returns an integer that can be represented with no more than one byte. E.g. use mod_256, shr1_mod256, etc.
#   byte_order: The order of the bytes of each delta in the in_path file and out_path file (e.g. 'little')
#   verbose: When True, print results as they are generated.
#   fail_early: set to True if the testing of a decimation level should stop for that level as soon as a failure is guaranteed for that level.
#               (i.e. testing stops for a decimation level once there are more than maxFails(numTestsRequested) failures for any of the 22 individual IID tests.)
##   IIDtests: The arguments to pass to iid_main from stats90b, e.g. if only the chi1 test should be performed, use "-r chi1".
#             If testing for a single round should stop as soon as one of the 22 individual tests fails, use "-r abort1fail"
#             Leaving the string empty is equivalent to running all IID tests without aborting the round on the first failure.
## Returned values: (results, datestampList, passedLevels)
#   results: The list of results (including prior results from results_path if overwrite==False). 
#   datestampList: The new results have datestamps between datestampList[0] and datestampList[1].
#   passedLevels = [passLevel, passStarLevel]
#       passLevel = None if no round has a worst test that passed with at least numTestsRequested tests. Otherwise, the minimim
#           decimation level with a passing worst test having at least numTestsRequested tests.
#       passStarLevel = None if no round has a worst test that passed (including rounds/tests with less than numTestsRequested tests). 
#           Otherwise, the minimim decimation level with a worst test that passed (including rounds/tests with less than numTestsRequested tests).
#   NOTE: If verbose is True, results are printed as they are generated. However, for a summary of results,
#           call the result_print function after calling this one. Function result_print will sort the results by decimation level if requested.
#   NOTE: results in the format of exampleResultsList will be written to the results_path. If overwrite==False, the previous contents of results_path is also written.
#       The result of testing carried out by this function is appended at the end of the results list in the results_path, but may consist of more than one list item.
#       Results are written and overwritten as they are generated, so if the testing is killed before it completes, all results generated so far may be read from results_path.
#
def decimated_binary_search(delta_path, results_path, overwrite=False, platform="", maxDec=200, minDec=1, numTestsRequested=1, maxFails=failTable, testSize=1000000, dec_multiplier=1,
                            input_delta_bytes=1, convert_delta=unchanged, byte_order='little', verbose=False, failEarly=False, IIDtests=""):

    # The NIST testing requires deltas to be one byte in size:
    output_delta_bytes = 1
    # Create a temporary file name to store the decimated deltas.
    dec_path = "temp_decimated_binary_search_data.bin"
    tempFileCreated=False

    # If we are not overwriting the contents of the results_path, read the existing results:
    results = result_open(results_path, overwrite)
  
    # Initialise the binary search tree so that it can be used to select the next decimation level to test and store the results.
    # If decimation levels must be multiples of the dec_multiplier, then the tree will not store the actual decimation levels.
    # The true decimation level will be the value stored in the tree multiplied by the dec_multiplier.
    tree = init_binary_tree(maxDec//dec_multiplier, ceil(minDec/dec_multiplier))
    
    # Use dec to store the decimation level we are currently testing 
    # (or more accurately the multiple of the dec_multiplier that we are currently testing)
    # Start at the largest possible decimation level.
    dec = maxDec//dec_multiplier

    # Set the starting date/time so that results between these datestamps can be retrieved.
    startDate = str(datetime.datetime.now())
    if verbose:
        print(f"Starting testing at {startDate}.")

    # Loop over the decimation levels being tested.
    while True:
        # If there are already results for the decimation level we need to test next, then
        # we are finished testing and can find the lowest passing decimation level and return the results.
        # Results may be printed by the calling function using the result_print function if desired.
        # Results are not printed here, except for those printed as they are generated by the test_decimated_file function when verbose is True.
        if tree[dec].results:
            endDate = str(datetime.datetime.now())
            passLevels = result_min_pass_level(results, maxFails=maxFails, minTests=numTestsRequested, checkLowRounds=True, 
                                       platformList=[platform], dateRange=[startDate, endDate])
    
            if verbose:
                print(f"\t  Minimum passing level (at least {numTestsRequested:6d} tests):         {passLevels[0]}.")
                print(f"\t  Minimum passing level (no minimum tests requirement):  {passLevels[1]} *.")
            # Delete the temporary file
            if tempFileCreated and os.path.exists(dec_path):
                os.remove(dec_path)
            
            return results, [startDate, endDate], passLevels

        # There were no results for this decimation level already existing. Test this level.

        # Find how many deltas there are available to work with by using file size / input_delta_bytes.
        numDeltasAvail = os.path.getsize(delta_path) // input_delta_bytes
        # Find how many deltas we need to do the requested amount of testing.
        numDeltasNeeded = ceil(numTestsRequested/(dec*dec_multiplier)) * dec * dec_multiplier * testSize
        numTests = numTestsRequested
        # Reduce the number of tests we will do, numTests, if there is insufficient data.
        if numDeltasAvail < numDeltasNeeded:
            numTests = (numDeltasAvail//(dec*dec_multiplier*testSize))*(dec * dec_multiplier)
            if verbose:
                print("decimated_binary_search - Decimation level: ", dec * dec_multiplier, " - Reducing number of tests to ", numTests, 
                      "instead of ", numTestsRequested, " due to insufficient data (only " + f"{numDeltasAvail:,d}" + " deltas available; would have needed "+ 
                      f"{numDeltasNeeded:,d}" + ").")

        
        if numTests == 0:
            # We are doing no tests, probably due to insufficient data; go to the right as this will give a smaller decimation level 
            # which is more likely to have enough data.
            tree[dec].set_results(True, {}, {}, 0, 0)
            result_append(results, dec= dec * dec_multiplier, passList = {}, passListTotals={}, roundPass=0, roundTotal=0, platform=platform, filename=delta_path, datestamp=str(datetime.datetime.now())) 
            result_write(results, results_path)
            dec = tree[dec].right
        else:
            # Decimate the data and save it in the temporary file path.
            write_decimated_file(delta_path, dec_path, dec*dec_multiplier, numTests, testSize, 
                                convert_delta, verbose, input_delta_bytes, output_delta_bytes, byte_order)
            tempFileCreated=True

            # Do the decimation testing.
            failed, b, c, d, e = test_decimated_file(dec_path, results_path, overwrite, platform, dec*dec_multiplier, numTests, maxFails, testSize, verbose, False, failEarly, 
                                            "Starting testing for decimation level " + f"{(dec*dec_multiplier):,d}" + " ...",
                                            "Overall result for decimation = " + f"{(dec*dec_multiplier):,d}" + ":", IIDtests)

            # Save the results of the decimation testing in the binary tree.
            tree[dec].set_results(failed, b, c, d, e)
            # Save the results in the 'results' list as well as writing the updated list to the results_path.
            result_append(results, dec= dec * dec_multiplier, passList = b, passListTotals=c, roundPass=d, roundTotal=e, platform=platform, filename=delta_path, datestamp=str(datetime.datetime.now()))
            result_write(results, results_path)

            if failed:
                dec = tree[dec].left
            else:
                dec = tree[dec].right
    


# Purpose: Test all the decimation levels in a given range for a given file of (un-decimated) deltas.
# Parameters:
#   delta_path: The path of the file containing the un-decimated deltas.
#   results_path: The path of the file where results should be written as they are generated.
#   overwrite: When True, overwrite the contents of the results_path. 
#              When False, read the results_path, append the results generated and then write them to the results_path.
#   platform: A string that describes the data being tested, e.g. the OE name, project name, etc.
#   maxDec: The maximum decimation level to test.
#   minDec: The minimum decimation level to test.
#   numTestsRequested: The number of tests to perform per decimation level. If there are insufficient deltas, fewer tests will be performed.
#               Warning: If there is insufficient data for any test, the program will perform fewer tests for that level of decimation testing. 
##  maxFails: A function that has as input the number of testing rounds performed and returns 
#               how many times any one of the 22 individual IID test may fail before there is an overall fail
#                for the decimation level being tested.
#   testSize: How many deltas are tested in each IID test
#   dec_multiplier: Only decimation levels which are multiples of dec_multiplier will be tested.  Use dec_multiplier = 1 to test all levels.
#   input_delta_bytes: Number of bytes per delta in the in_path file.
#   convert_delta: function that takes as input any positive integer which was input_delta_bytes bytes long 
#                       and a returns an integer that can be represented with no more than one byte. E.g. use mod_256, shr1_mod256, etc.
#   byte_order: The order of the bytes of each delta in the in_path file and out_path file (e.g. 'little')
#   verbose: When True, print results as they are generated.
#   fail_early: set to True if the testing of a decimation level should stop for that level as soon as a failure is guaranteed for that level.
#               (i.e. testing stops for a decimation level once there are more than maxFails(numTestsRequested) failures for any of the 22 individual IID tests.)
#   IIDtests: The arguments to pass to iid_main from stats90b, e.g. if only the chi1 test should be performed, use "-r chi1".
#             If testing for a single round should stop as soon as one of the 22 individual tests fails, use "-r abort1fail"
#             Leaving the string empty is equivalent to running all IID tests without aborting the round on the first failure.
#   Returned values: (results, datestampList, passLevels)
#   results: The list of results (including prior results from results_path if overwrite==False). 
#   datestampList: The new results have datestamps between datestampList[0] and datestampList[1].
#   passedLevels = [passLevel, passStarLevel]
#       passLevel = None if no round has a worst test that passed with at least numTestsRequested tests. Otherwise, the minimim
#           decimation level with a passing worst test having at least numTestsRequested tests.
#       passStarLevel = None if no round has a worst test that passed (including rounds/tests with less than numTestsRequested tests). 
#           Otherwise, the minimim decimation level with a worst test that passed (including rounds/tests with less than numTestsRequested tests).
#   NOTE: If verbose is True, results are printed as they are generated. However, for a summary of results,
#           call the result_print function after calling this one. Function result_print will sort the results by decimation level if requested.
#   NOTE: results in the format of exampleResultsList will be written to the results_path. If overwrite==False, the previous contents of results_path is also written.
#       The result of testing carried out by this function is appended at the end of the results list in the results_path, but may consist of more than one list item.
#       Results are written and overwritten as they are generated, so if the testing is killed before it completes, all results generated so far may be read from results_path.
#
def decimated_range_test(delta_path, results_path, overwrite=False, platform="", maxDec=200, minDec=1, numTestsRequested=1, maxFails=failTable, 
                         testSize=1000000, dec_multiplier=1,
                        input_delta_bytes=1, convert_delta=unchanged, byte_order='little', verbose=False, failEarly=False, IIDtests=""):

    # The NIST testing requires deltas to be one byte in size:
    output_delta_bytes = 1
    # Create a temporary file name to store the decimated deltas.
    dec_path = "temp_decimated_binary_search_data.bin"
    tempFileCreated=False

    # If we are not overwriting the contents of the results_path, read the existing results:
    results = result_open(results_path, overwrite)
     
    # Set the starting date/time so that results between these datestamps can be retrieved.
    startDate = str(datetime.datetime.now())
    if verbose:
        print(f"Starting testing at {startDate}.")

    # Loop over the decimation levels being tested.
    # Use dec to store the decimation level we are currently testing 
    # (or more accurately the multiple of the dec_multiplier that we are currently testing)
    # Start at the largest possible decimation level.

    for dec in range(maxDec//dec_multiplier, max(ceil(minDec/dec_multiplier) - 1, 0), -1):

        # Test this level.

        # Find how many deltas there are available to work with by using file size / input_delta_bytes.
        numDeltasAvail = os.path.getsize(delta_path) // input_delta_bytes
        # Find how many deltas we need to do the requested amount of testing.
        numDeltasNeeded = ceil(numTestsRequested/(dec*dec_multiplier)) * dec * dec_multiplier * testSize
        numTests = numTestsRequested
        # Reduce the number of tests we will do, numTests, if there is insufficient data.
        if numDeltasAvail < numDeltasNeeded:
            numTests = (numDeltasAvail//(dec*dec_multiplier*testSize))*(dec * dec_multiplier)
            if verbose:
                print("decimated_binary_search - Decimation level: ", dec * dec_multiplier, " - Reducing number of tests to ", numTests, 
                      "instead of ", numTestsRequested, " due to insufficient data (only " + f"{numDeltasAvail:,d}" + " deltas available; would have needed "+ 
                      f"{numDeltasNeeded:,d}" + ").")
        
        if numTests == 0:
            # We are doing no tests, probably due to insufficient data; go to the right as this will give a smaller decimation level 
            # which is more likely to have enough data.
            result_append(results, dec= dec * dec_multiplier, passList = {}, passListTotals={}, roundPass=0, roundTotal=0, platform=platform, filename=delta_path, datestamp=str(datetime.datetime.now())) 
            result_write(results, results_path)
        else:
            # Decimate the data and save it in the temporary file path.
            write_decimated_file(delta_path, dec_path, dec*dec_multiplier, numTests, testSize, 
                                convert_delta, verbose, input_delta_bytes, output_delta_bytes, byte_order)
            tempFileCreated=True

            # Do the decimation testing.
            failed, b, c, d, e = test_decimated_file(dec_path, results_path, overwrite, platform, dec*dec_multiplier, numTests, maxFails, testSize, verbose, False, failEarly, 
                                            "Starting testing for decimation level " + f"{(dec*dec_multiplier):,d}" + " ...",
                                            "Overall result for decimation = " + f"{(dec*dec_multiplier):,d}" + ":", IIDtests)

            # Save the results in the 'results' list as well as writing the updated list to the results_path.
            result_append(results, dec= dec * dec_multiplier, passList = b, passListTotals=c, roundPass=d, roundTotal=e, platform=platform, filename=delta_path, datestamp=str(datetime.datetime.now()))
            result_write(results, results_path)

    # we are finished testing and can find the lowest passing decimation level and return the results.
    # Results may be printed by the calling function using the result_print function if desired.
    # Results are not printed here, except for those printed as they are generated by the test_decimated_file function when verbose is True.
    endDate = str(datetime.datetime.now())

    passLevels = result_min_pass_level(results, maxFails=maxFails, minTests=numTestsRequested, checkLowRounds=True, 
                                       platformList=[platform], dateRange=[startDate, endDate])
    
    if verbose:
        print(f"\t  Minimum passing level (at least {numTestsRequested:6d} tests):         {passLevels[0]}.")
        print(f"\t  Minimum passing level (no minimum tests requirement):  {passLevels[1]} *.")

    # Delete the temporary file
    if tempFileCreated and os.path.exists(dec_path):
        os.remove(dec_path)
    
    return results, [startDate, endDate], passLevels