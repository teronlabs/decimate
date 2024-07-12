# Decimate

Decimate is a Python library published by [Teron Labs](https://www.teronlabs.com/) (<info@teronlabs.com>) for running decimation testing on data from a non-IID [(independent and identically distributed)](https://en.wikipedia.org/wiki/Independent_and_identically_distributed_random_variables) noise source.

Decimation testing first 'decimates' the data with decimation level `i` by writing every `i`th sample from the data to a new file to be tested. This new file is then split into multiple sub-files, each of which then undergoes IID testing to determine whether the data appears to be IID. If the IID testing passes, an entropy estimate, `H_d` may be obtained for the decimated data, and the value `H_d`/`i` may be used as an entropy estimate for the original data file.

The IID testing used by [Teron Labs](https://www.teronlabs.com/)' Decimate Python library is from NIST's C++ [SP800-90B_EntropyAssessment](https://github.com/usnistgov/SP800-90B_EntropyAssessment) tool. Teron Labs modified the tool slightly and made it into a Python extension module called "stats90b". The modifications changed the IID testing to return the results of each of the 22 different types of IID testing performed as a JSON/Python dictionary.  The tool was also modified to allow the user to elect to perform only some of the 22 IID tests instead of all of them. The NIST IID testing tool may be called directly from Python if desired, but it is likely more convenient to use one of the higher level functions provided by Teron Labs in `decimate.deci`.


# stats90b: How to compile the IID testing from  NIST's C++ SP800-90B_EntropyAssessment tool as a Python library

Before using `decimate`, the IID testing from  NIST's C++ SP800-90B_EntropyAssessment tool must be compiled as a Python library. This library is called `stats90b`.

1. Install all of the libraries needed to compile NIST's C++ code.

    The following text is from NIST's `README.md`:

    * This code package requires a C++11 compiler. The code uses OpenMP directives, so compiler support for OpenMP is expected. GCC is preferred (and the only platform tested). There is one method that involves a GCC built-in function (`chi_square_tests.h -> binary_goodness_of_fit() -> __builtin_popcount()`). To run this you will need some compiler that supplies this GCC built-in function (GCC and clang both do so).

    * The resulting binary is linked with bzlib, divsufsort, jsoncpp, GMP MP and GNU MPFR, so these libraries (and their associated include files) must be installed and accessible to the compiler.

    * On Ubuntu they can be installed with `apt-get install libbz2-dev libdivsufsort-dev libjsoncpp-dev libssl-dev libmpfr-dev`.

    * See [the wiki](https://github.com/usnistgov/SP800-90B_EntropyAssessment/wiki/Installing-Packages) for some distribution-specific instructions on installing the mentioned packages.

2. Ensure `pip` and `setuptools` are installed.
    ```console
    $ sudo apt update
    $ sudo apt install python3-pip
    $ sudo pip install -U setuptools
    $ python3 -m pip install build
    $ apt install python3.10-venv
    ```

3. In the `stats90b` directory, run Python on `setup.py` with option `build`, then run again with option `install`, e.g.
    ```console
    $cd stats90b
    $python3 setup.py build
    $python3 setup.py install
    ```
    If the default install directory is unwriteable, it may be necessary to use:
    ```console
    $sudo python3 setup.py install
    ```

4. If you wish to have direct access to NIST's library, import the `stats90b` library into your Python code.

    Note: If you are importing and using functions from `decimate.deci`, and do not need direct access to `stats90b`, this step is already completed by `decimate.deci` and need not be carried out separately.
    
    To convert the string returned from `iid_main` to a Python dictionary you will also want to import the `json` library. 

    Example usage (see `example_iid_main.py`):

    ```console
    from stats90b import iid_main
    import json

    decimated_file_path = "./data/File1.bin"

    # `-q` means quiet
    # `-r all` means run all available IID tests
    # (other options are `-r chi1`, `-r chi2`, `-r LRS`, `-r perm`)
    # Additional options are available - see NIST ea_iid documentation or pass an empty argument string to see the usage.
    argument_string = "-q -r all " + decimated_file_path
    result_string = iid_main(argument_string)

    # Convert the results string to a Python dictionary.
    res = json.loads(result_string)
    # Print the dictionary of results.
    for test in res.keys():
        print(res[test], "-", test)
    ```
## Usage for iid_main from stats90b
Usage is: iid_main(" [-i|-c] [-a|-t] [-v] [-q] [-l <index>,<samples> ] [-r <test_to_run>] <file_name> [bits_per_symbol] ")

* <file_name>: Must be relative path to a binary file with at least 1 million entries (samples).

* [bits_per_symbol]: Must be between 1-8, inclusive. By default this value is inferred from the data.

* [-i|-c]: '-i' for initial entropy estimate, '-c' for conditioned sequential dataset entropy estimate. The initial entropy estimate is the default.

* [-a|-t]: '-a' produces the 'H_bitstring' assessment using all read bits, '-t' truncates the bitstring used to produce the `H_bitstring` assessment to 1000000 bits. Test all data by default.

* Note: When testing binary data, no `H_bitstring` assessment is produced, so the `-a` and `-t` options produce the same results for the initial assessment of binary data.

* -v: Optional verbosity flag for more output. Can be used multiple times.

* -q: Quiet mode, less output to screen. This will override any verbose flags.

* -l <index>,<samples>   Read the <index> substring of length <samples>.

* Samples are assumed to be packed into 8-bit values, where the least significant 'bits_per_symbol'
    bits constitute the symbol.

* -i: Initial Entropy Estimate (Section 3.1.3)

    Computes the initial entropy estimate H_I as described in Section 3.1.3 (not accounting for H_submitter) using the entropy estimators specified in Section 6.3.  If 'bits_per_symbol' is greater than 1, the samples are also converted to bitstrings and assessed to create H_bitstring; for multi-bit symbols, two entropy estimates are computed: H_original and H_bitstring.

    Returns min(H_original, bits_per_symbol X H_bitstring). The initial entropy estimate H_I = min(H_submitter, H_original, bits_per_symbol X H_bitstring).

* -c: Conditioned Sequential Dataset Entropy Estimate (Section 3.1.5.2)

    Computes the entropy estimate per bit h' for the conditioned sequential dataset if the conditioning function is non-vetted. The samples are converted to a bitstring.

    Returns h' = min(H_bitstring).

* -o: Set Output Type to JSON

    Changes the output format to JSON and sets the file location for the output file.

* --version: Prints tool version information

* -r: Specifies which test to run where test_to_run is one of the following:

    * chi1 = Chi Square Independence Test

    * chi2 = Chi Square Goodness of Fit Test

    * LRS = Longest Repeated Substring Test

    * perm = All 19 of the permutation tests

    * all = All of above tests.

    * abort1fail = Abort the testing and return existing results upon the first failure of a test.

    * If the -r option is not used, all tests are run.

# decimate installation
Once `stats90b` has been installed, the decimate package may be built and installed. In the root directory of the project, use the following commands:
```console
$python3 -m build
$python3 -m pip install .
```
You can then import and use functions from `decimate.deci` in your Python scripts.

# decimate examples
The [examples](../examples) directory provides examples of the usage of the decimate library.

# decimate.deci functions

## Functions to provide mappings for deltas

Deltas often need mapping from a large size (e.g. 64 bits) to the 8 bits required for the NIST IID testing. These functions
facilitate that process and may be passed to various functions in `decimate.deci` to perform the mapping. The user may also create additional functions and use them instead.

### mod_256 - A function to return the least signficant 8 bits of a delta
def mod_256(delta):

    return (delta % 256)

### shr1_mod256 - A function to drop the least significant bit of a delta and return the result modulo 256
def shr1_mod256(delta):

    return ((delta >> 1) % 256)

### shr1_mod255 - A function to drop the least significant bit of a delta and return the result modulo 255
def shr1_mod255(delta):

    return ((delta >> 1) % 255)

### unchanged - A function to keep the delta unchanged
def unchanged(delta):

    return delta

## Functions to decimate data files

### write_decimated_delete_file
* Purpose: Sometimes deltas in particular sequence positions are more likely to pass the IID tests than deltas in other sequence positions.
    
    E.g. deltas in sequence position 0 modulo 4 might be more likely to pass IID tests than other deltas.

    This function may be used to write deltas in the desired sequence positions to file; other deltas are discarded.

* Parameters:
    * in_path: File containing the input deltas

    * out_path: Path to file where desired deltas are to be written 
    
    * dec: modulus for the sequence position selection
    
    * delIdx: list of sequence positions to be ignored modulo dec (each value must be >= 0 and < dec).
      
    * delta_bytes: each delta must be delta_bytes bytes long        
    
    * byte_order: each delta must have the byte order as specified in byte_order (e.g. 'little').
    
    * verbose: if verbose=True, a status message is printed after the function has finished writing the file.

    * E.g. the in_path contains deltas: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 4, 7, 2, 3, 1, 8.
        * dec = 4
        * delIdx = [2, 3]
        * then the deltas output to the out_path will be: 0, 1, 4, 5, 8, 9, 7, 2, 8.

* Usage: 

    write_decimated_delete_file(in_path, out_path, dec=4, delIdx=[3], verbose=True,  delta_bytes = 8, byte_order='little')

### write_decimated_file
* Purpose: re-arrange deltas into a decimated order, ready for decimation testing.
* Parameters: 
    * in_path: the path to the input file containing the deltas
    * out_path: the path to the output file where the decimated deltas will be written
    * dec: the decimation level
    * numSets: How many decimated sets of data will be seprately IID tested
    * setSize: How many deltas will be in each set sent for IID testing
    * convert_delta: function that takes as input any positive integer which was input_delta_bytes bytes long and a returns an integer that can be represented with no more than output_delta_bytes bytes.
    * verbose: Set to True if status updates should be printed.
    * input_delta_bytes: Number of bytes per delta in the in_path file.
    * output_delta_bytes: Number of bytes per delta to write to the out_path file.
    * byte_order: The order of the bytes of each delta in the in_path file and out_path file (e.g. 'little')
    
* *E.g.
    * If the in_path contains deltas 0, 1, 2, 3,| 4, 5, 6, 7,| 8, 9, 10, 54, |57, 52, 53, 51, |58, 59, 50, 47, |42, 45, 43, 49,|44, 32, 39, 33 | 35;
        * dec = 4
        * setSize = 3
        * numSets = 5
    * Then the out_path will contain deltas: 0, 4, 8, | 57, 58, 42, | 1, 5, 9, | 52, 59, 45, | 2, 6, 10, | 53, 50, 43, | 3, 7, 54, | 51, 47, 49.
    
    * Note: The '|' character is not part of the input or output but inserted here for readability. 
    * Note: The number of sets produced is 8 rather than 5 since the function finishes writing the rest of the data that starts at the offset position in the same group of dec = 4 deltas. I.e. if it is necessary to write the delta set starting at 0 then delta sets starting at 1, 2, and 3 will also be written when dec = 4. 
* Usage:

    write_decimated_file(in_path, out_path, dec=1, numSets=1, setSize=1000000, convert_delta=unchanged, verbose = True, input_delta_bytes = 8, output_delta_bytes = 8, byte_order='little')

## Functions to separate deltas into sub-distributions

### write_subDist_id_file

* Purpose: Given an input file of deltas, write a file with the delta replaced with the ID of the subdistribution.
* Parameters:
    * in_path: The path to the file of deltas.
    * out_path: The path of the output file. 
    * input_delta_bytes: Number of bytes per delta in the in_path file.
    * subdist_cutoffs: A list of cutoffs for the subdistributions. 
        * The first sub-distribution is from 0 to subdist_cutoffs[0]-1
        * The ith sub-distribution is from subdist_cutoffs[i] to subdist_cutoffs[i+1]-1
        * The last sub-distribution is from subdist_cutoffs[-1] to the maximum delta.
        * There are len(subdist_cutoffs) + 1 sub-distributions.
    * byte_order: The order of the bytes of each delta in the in_path file and out_path file (e.g. 'little')
    * writeText: Whether the subdistribution number should be written as text (0-9 then A-Z) rather than a binary value.
        * NOTE: If writeText is True, there must be 36 or fewer subdistributions (i.e. len(subdist_cutoffs) <= 35)
* Return value:

    A list of how many deltas are in each subdistribution.    

* Usage:

    write_subDist_id_file(in_path, out_path, input_delta_bytes = 8, subdist_cutoffs=[], verbose=True, byte_order = 'little', writeText = True)

### write_subfile

* Purpose: Given an input file of (decimated) deltas, write multiple output files, where each output file contains only those deltas from one of the specified sub-distributions.

    The output files may then be used for non_iid testing to generate an entropy estimate for the decimated data.

* Parameters:
    * in_path: The path to the file of decimated deltas.
    * out_path: The prefix for the path of the output files ("_\<number\>.bin" is appended for each output file). 
    * convert_delta: function that takes as input any positive integer which was input_delta_bytes bytes long and returns an integer that can be represented with no more than output_delta_bytes bytes.
    * input_delta_bytes: Number of bytes per delta in the in_path file.
    * output_delta_bytes: Number of bytes per delta to write to the out_path files.
    * subdist_cutoffs: A list of cutoffs for the subdistributions. 
        * The first sub-distribution is from 0 to subdist_cutoffs[0]-1
        * The ith sub-distribution is from subdist_cutoffs[i] to subdist_cutoffs[i+1]-1
        * The last sub-distribution is from subdist_cutoffs[-1] to the maximum delta.
        * There are len(subdist_cutoffs) + 1 sub-distributions.
    * verbose: When True, write a status message with the number of samples written per file before returning.
    * byte_order: The order of the bytes of each delta in the in_path file and out_path file (e.g. 'little')
* Return value:

    * A list of how many deltas are in each subdistribution.  

* Usage:

    write_subfile(in_path, out_path, convert_delta=unchanged, input_delta_bytes = 8, output_delta_bytes = 8, subdist_cutoffs=[], verbose=True, byte_order = 'little')

## Functions to perform decimation testing

### failTable

* Purpose: This is a function that has as input the number of testing rounds performed and returns how many times any one of the 22 individual IID test may fail before there is an overall fail for the decimation level being tested. It is typically passed to test_decimated_file or decimated_binary_search, but the user may define and use their own function if desired.
* Parameters:
    * numTests: The number of testing rounds that will be performed.
*Return value: 
    * The maximum number of rounds allowed to fail for an overall passing result.
        * if   numTests <= 1:   return 0
        * elif numTests <= 31:  return 1
        * elif numTests <= 146: return 2
        * elif numTests <= 347: return 3
        * elif numTests <= 621: return 4
        * elif numTests <= 952: return 5
        * elif numTests <= 1330: return 6
        * else:                 return 7
    * This function returns Cutoff = binomial_cdf_inverse(n=numTests, p=1/1000, 1-q)
    * where q = 1 - (1-alpha)^(1/22) = 0.00046 and alpha = 0.01.
    * p = 1/1000 = the NIST designed false reject rate for each of the 22 different IID tests.
    * alpha = Pr(data that is IID fails numTests rounds of IID testing) = p-value or significance = 0.01.
    * q = Pr(data that is IID fails numTests rounds of a single one of the 22 different IID tests).
* Usage:

    failTable(numTests)

### test_decimated_file

* Purpose: Run IID testing on a decimated data file. Split the data into tests of 'setSize' deltas each, and return results of each test. This function tests a single decimation level only, and the data must have already been decimated before calling this function.
* Parameters:
    * in_path: Path to decimated deltas; deltas must be 1 byte each, ready for the NIST tool to read.
    * results_path: The path of the file where results should be written as they are generated.
    * overwrite: When True, overwrite the contents of the results_path. When False, read the results_path, append the results generated, and then write them to the results_path.
    * platform: A string that describes the data being tested, e.g. the OE name, project name, etc.
    * dec: The decimation level being tested. This has no impact on the testing run, since in_path is already decimated, but is recorded as part of the results.
    * numTests: How many rounds of IID testing should be performed.
        * NOTE: If there is insufficient data, an exception is raised.
    * maxFails: A function that has as input the number of testing rounds performed and returns how many times any one of the 22 individual IID test may fail before there is an overall fail for the decimation level being tested. E.g. use the failTable function.
    * setSize: The number of deltas in each IID testing round.
    * verboseRounds: Results of each testing round are printed as they are completed when verboseRounds is True.
    * verboseFinal: Overall results for each of the 22 IID tests are printed for all of the testing rounds when verboseFinal is true.
    * failEarly: When True, the testing will stop as soon as one or more IID tests have failed more than maxFails times, instead of completing all the tests.
    * messageStart: The message to print at the start of the decimation testing when verboseRounds is True. Leave as "" for the default message, f"Starting testing for platform {platform}, decimation level = {dec} ..."
    * messageEnd: The message to print at the end of the decimation testing prior to printing the results when verboseRounds or verboseFinal is True. Leave as "" for the default message, f"Overall result for platform {platform}, decimation level = {dec}:"
    * IID tests: The arguments to pass to iid_main from stats90b. See iid_main documentation for all options.
        * e.g. if only the chi1 test should be performed, use "-r chi1". 
        * If testing for a single round should stop as soon as one of the 22 individual tests fails, include "-r abort1fail" 
        * Leaving the string empty is equivalent to running all IID tests without aborting the round on the first failure.
* Return values: ('failure', 'totalPasses', 'totals', 'roundPassCount', 'roundTotalCount') 
    * failure: a boolean indicating whether the overall testing result for all rounds is a failure.
    * totalPasses: a dictionary providing the number of total passes for each of the 22 individual IID tests.
    * totals: a dictionary providing the total number of tests performed for each of the 22 individual IID tests.
    * roundPassCount: How many testing rounds passed overall (i.e. how many rounds where all 22 different IID tests passed)
    * roundTotalCount: How many testing rounds were carried out.
    * NOTE: 
        * results in the format of exampleResultsList will be written to the results_path. This is different to the format of the values retuned by this function. 
        * If overwrite==False, the previous content of results_path is also written to the results_path.
        * The result of testing this decimation level is in the last item of the results list in the results_path.
        * Results are written and overwritten as they are generated, so if the testing is killed before it completes, all results generated so far may be read from results_path.
* Usage:

    (failure, totalPasses, totals, roundPassCount, roundTotalCount) = test_decimated_file(in_path, results_path, overwrite="", platform="<unspecified>", dec=0, numTests=1, maxFails=failTable, setSize=1000000, verboseRounds=True, verboseFinal=False, failEarly=False, messageStart="", messageEnd="", IIDtests="")

### decimated_binary_search

* Purpose: Use a binary search to find the lowest passing decimation level for a given file of (un-decimated) deltas.
* Parameters:
    * delta_path: The path of the file containing the un-decimated deltas.
    * results_path: The path of the file where results should be written as they are generated.
    * overwrite: When True, overwrite the contents of the results_path. When False, read the results_path, append the results generated and then write them to the results_path.
    * platform: A string that describes the data being tested, e.g. the OE name, project name, etc.
    * maxDec: The maximum decimation level to test.
    * minDec: The minimum decimation level to test.
    * numTestsRequested: The number of tests to perform per decimation level. 
        * Warning: If there is insufficient data for any test, the program will perform fewer tests for that level of decimation testing. 
    * maxFails: A function that has as input the number of testing rounds performed and returns how many times any one of the 22 individual IID test may fail before there is an overall fail for the decimation level being tested. E.g. use the failTable function.
    * testSize: How many deltas are tested in each IID test. 
    * dec_multiplier: Only decimation levels which are multiples of dec_multiplier will be tested. Use dec_multiplier = 1 to test all levels.
    * input_delta_bytes: Number of bytes per delta in the in_path file.
    * convert_delta: function that takes as input any positive integer which was input_delta_bytes bytes long  and a returns an integer that can be represented with no more than one byte. E.g. use mod_256, shr1_mod256, etc.
    * byte_order: The order of the bytes of each delta in the in_path file and out_path file (e.g. 'little')
    * verbose: When verbose = True, print results as they are generated.
    * fail_early: set to True if the testing of a decimation level should stop for that level as soon as a failure is guaranteed for that level. (i.e. testing stops for a decimation level once there are more than maxFails(numTestsRequested) failures for any one or more of the 22 individual IID tests.)
    * IIDtests: The arguments to pass to iid_main from stats90b.
        * e.g. if only the chi1 test should be performed, use "-r chi1".
        * If testing for a single round should stop as soon as one of the 22 individual tests fails, use "-r abort1fail"
        * Leaving the string empty is equivalent to running all IID tests without aborting the round on the first failure.
* Returned values: (results, datestampList, passedLevels)
    * results: The list of results (including prior results from results_path if overwrite==False). 
    * datestampList: The new results have datestamps between datestampList[0] and datestampList[1].
    * passedLevels = [passLevel, passStarLevel]
        * passLevel = None if no round has a worst test that passed with at least numTestsRequested tests. Otherwise, the minimim decimation level with a passing worst test having at least numTestsRequested tests.
        * passStarLevel = None if no round has a worst test that passed (including rounds/tests with less than numTestsRequested tests). Otherwise, the minimim decimation level with a worst test that passed (including rounds/tests with less than numTestsRequested tests).
        * 'Worst' means the test(s) having the lowest number of passes, and of those, the test(s) with the maximum total tests.
    * NOTE: 
        * If verbose is True, results are printed as they are generated. However, for a nicely formatted summary of results, call the result_print function after calling this one. Function result_print will sort the results by decimation level if requested.
        * results in the format of exampleResultsList will be written to the results_path. If overwrite==False, the previous contents of results_path is also written.
        *The result of testing carried out by this function is appended at the end of the results list in the results_path, but may consist of more than one list item.
        * Results are written and overwritten as they are generated, so if the testing is killed before it completes, all results generated so far may be read from results_path.
* Usage:

    results, datestampList, passed, best_decimation_level = decimated_binary_search(delta_path, results_path, overwrite=False, platform="", maxDec=200, minDec=1, numTestsRequested=1, maxFails=failTable, testSize=1000000, dec_multiplier=1, input_delta_bytes=1, convert_delta=unchanged, byte_order='little', verbose=False, failEarly=False, IIDtests="")

### decimated_range_test

* Purpose: Test all the decimation levels in a given range for a given file of (un-decimated) deltas.
* Parameters:
    * delta_path: The path of the file containing the un-decimated deltas.
    * results_path: The path of the file where results should be written as they are generated.
    * overwrite: When True, overwrite the contents of the results_path. When False, read the results_path, append the results generated and then write them to the results_path.
    * platform: A string that describes the data being tested, e.g. the OE name, project name, etc.
    * maxDec: The maximum decimation level to test.
    * minDec: The minimum decimation level to test.
    * numTestsRequested: The number of tests to perform per decimation level. 
        * Warning: If there is insufficient data for any test, the program will perform fewer tests for that level of decimation testing. 
    * maxFails: A function that has as input the number of testing rounds performed and returns how many times any one of the 22 individual IID test may fail before there is an overall fail for the decimation level being tested. E.g. use the failTable function.
    * testSize: How many deltas are tested in each IID test. 
    * dec_multiplier: Only decimation levels which are multiples of dec_multiplier will be tested. Use dec_multiplier = 1 to test all levels.
    * input_delta_bytes: Number of bytes per delta in the in_path file.
    * convert_delta: function that takes as input any positive integer which was input_delta_bytes bytes long  and a returns an integer that can be represented with no more than one byte. E.g. use mod_256, shr1_mod256, etc.
    * byte_order: The order of the bytes of each delta in the in_path file and out_path file (e.g. 'little')
    * verbose: When verbose = True, print results as they are generated.
    * fail_early: set to True if the testing of a decimation level should stop for that level as soon as a failure is guaranteed for that level. (i.e. testing stops for a decimation level once there are more than maxFails(numTestsRequested) failures for any one or more of the 22 individual IID tests.)
    * IIDtests: The arguments to pass to iid_main from stats90b.
        * e.g. if only the chi1 test should be performed, use "-r chi1".
        * If testing for a single round should stop as soon as one of the 22 individual tests fails, use "-r abort1fail"
        * Leaving the string empty is equivalent to running all IID tests without aborting the round on the first failure.
* Returned values: (results, datestampList, passedLevels)
    * results: The list of results (including prior results from results_path if overwrite==False). 
    * datestampList: The new results have datestamps between datestampList[0] and datestampList[1].
    * passedLevels = [passLevel, passStarLevel]
        * passLevel = None if no round has a worst test that passed with at least numTestsRequested tests. Otherwise, the minimim decimation level with a passing worst test having at least numTestsRequested tests.
        * passStarLevel = None if no round has a worst test that passed (including rounds/tests with less than numTestsRequested tests). Otherwise, the minimim decimation level with a worst test that passed (including rounds/tests with less than numTestsRequested tests).
        * 'Worst' means the test(s) having the lowest number of passes, and of those, the test(s) with the maximum total tests.
    * NOTE: 
        * If verbose is True, results are printed as they are generated. However, for a nicely formatted summary of results, call the result_print function after calling this one. Function result_print will sort the results by decimation level if requested.
        * results in the format of exampleResultsList will be written to the results_path. If overwrite==False, the previous contents of results_path is also written.
        *The result of testing carried out by this function is appended at the end of the results list in the results_path, but may consist of more than one list item.
        * Results are written and overwritten as they are generated, so if the testing is killed before it completes, all results generated so far may be read from results_path.
* Usage:

    results, datestampList, passed, best_decimation_level = decimated_range_test(delta_path, results_path, overwrite=False, platform="", maxDec=200, minDec=1, numTestsRequested=1, maxFails=failTable, testSize=1000000, dec_multiplier=1, input_delta_bytes=1, convert_delta=unchanged, byte_order='little', verbose=False, failEarly=False, IIDtests="")

## Functions for Results (open, write, append, sort, outcome, datestamp_range, print)

Results used by these functions have the following format:
```console
    * exampleResultsList = [exampleResultItem, item2, ... ]
    * exampleResultItem =      
        {
            "dec": 2, # Decimation level tested
            "passList": {
                "chiSqIndependence": #Name of individual IID test carried out
                [ 
                    2, # Number of passing chiSqIndependence tests
                    5  # Total number of chiSpIndependence tests
                ],
                "chiSqGoodnessFit": #Insert as manay test names as were carried out in the "passList" dictionary.
                [
                    2, 2
                ]
            },
            "roundPass": 2, # Number of passing rounds of testing completed. 
                # One round consists of running each of the 22 (or fewer) IID tests once.
            "roundTotal": 5, # Number of rounds of testing carried out.
            "platform": "OE # 1", # The identifier for the platform that produced the data.
            "filename": "./data/Example_decimate_bin_search_File1.bin", # The name of the file containing un-decimated data.
            "datestamp": "2024-07-07 22:07:28.683159" # The time all roundTotal rounds of testing ended.
        } 
```

### result_open

* Pupose: Read the decimation testing results from file.
* Parameters:
    * results_path: The path where the results should be read in JSON format (same format as exampleResultsList).
    * overwrite: When True, instead of reading the file, an empty list is returned.
* Return value:
    * results: The results read from results_path, or an empty list when the file does not exist, its size is 0, or overwrite==True.
* Usage:

    results = result_open(results_path, overwrite)

### result_write

* Pupose: Save the decimation testing results to file.
* Parameters:
    * results: The list of results (same format as exampleResultsList)
    * results_path: The path where the results should be written in JSON format.
* NOTE:
    * The contents of results_path are overwritten.
* Usage:

    result_write(results, results_path)

### result_append

* Purpose: Append the results of testing one decimation level to the list of results.
* Parameters:
    * results: The current list of results (same format as exampleResultsList)
    * The remaining parameters contain the testing details to insert in the new item appended to results. The parameters passList, passListTotals, roundPass and roundTotal are the same format as the corresponding outputs from the test_decimated_file function:
        * dec: the decimation level tested
        * passList: The dictionary of individual IID tests stating how many tests passed, e.g. {"chiSqIndependence": 5, ...}
        * passListTotals: The dictionary of individual IID tests stating how many tests were done in total, e.g. {"chiSqIndependence": 7, ...}
        * roundPass: The total number of passing rounds (one round consists of all the individual tests being tested.)
        * roundTotal: The total number of rounds completed.
        * platform: A string that describes the data that were tested, e.g. the OE name, project name, etc.
        * filename: The file path of the un-decimated deltas that were tested.
        * datestamp: A string with the datestamp of when the testing completed.
* Outcome:
    * Results is modified by having a new item with the details provided appended. The function does not have a return value.
* Usage:

    result_append(results, dec, passList, passListTotals, roundPass, roundTotal, platform="", filename="", datestamp="")

### result_sort

* Purpose: Sort the recorded results by the following values: platform, then decimation level, then total testing rounds, then total passing individual IID tests.
* Parameters: 
    * results: The current list of results (same format as exampleResultsList)
* Outcome: results is modified by sorting. There is no return value.
* Usage:

    result_sort(results)

### result_outcome

* Purpose: Return a string indicating whether results\[resNum\] passed or failed, including whether the minimum number of requested tests were carried out.
* Parameters:
    * results: The list of results (same format as exampleResultsList)
    * resNum: results[resNum] is the item whose pass/fail status should be returned.
    * minTests: A desired minimum number of tests or rounds to be carried out. Passing tests having fewer than minTests rounds will be flagged with an `*`. Fails with fewer than maxFails(minTests) test faillures will also be flagged with an `*`.
    * testID: A string containing the name of the individual IID test to check. 
        * If testID="", the 'worst' test is selected and checked. 
        * 'Worst' means the test(s) having the lowest number of passes, and of those, the test(s) with the maximum total tests.
    * maxFails: A function which takes as input the number of tests and returns the maximum number of failing tests compatible with an overall pass.
        * E.g. if at least 147 passes out of 150 tests is required to declare a pass over the 150 tests, then maxFails(150) returns 3 = 150 - 147.
        * Typically, the provided 'failTable' function is used, but users may supply their own if desired.
* Return value: outcome
    * outcome has the following possible values and meanings:
        * "FAIL" - Enough individual tests failed that the overall result is a fail, whether the cutoff is for the actual number of rounds or the minimum number of rounds.
        * "FAIL *" - The actual number of rounds failed, but not enough rounds were tested to know if it would have failed if the requested number of rounds were tested.
        * "pass *" - The actual number of rounds passed, but less than the requested minimum number of rounds were tested.
        * "pass" - At least the requested minimum number of rounds were tested and they passed.
* Usage:

    result_outcome(results, resNum, minTests, testID="", maxFails=failTable)

### result_datestamp_range
* Purpose: Return a list of results containing only those results in the specified dateRange.
* Parameters:
    * results: The list of results (same format as exampleResultsList)
    * dateRange:  Use dateRange=["",""] or ["earliest", "latest"] to return all results. Otherwise, set the strings in the list to the datestamps at the start and end of the range to be returned.
        * NOTE: An example of a full datestamp is: "2024-07-08 09:52:44.204973" - even if the datestamps printed are truncated. If you use shorter strings in the dateRange, make sure that the when sorted, the full datestamp strings for the desired results fall between the strings you specify (e.g. you may need to add some time to the last datestamp to retrieve all desired items).
* Return value: newResults
    * newResults: List of items from results within the specified dateRange.
* Usage:

    newResults = result_datestamp_range(results, dateRange)

### result_print

* Purpose: Print the results of decimation testing
* Parameters:
    * resultsList: A list of individual Decimation test results. Each result in the list is a dictionary with the same structure as the exampleResultItem.
    * maxFails:   A function which takes as input the number of tests and returns the maximum number of failing tests compatible with an overall pass.
        * E.g. if at least 147 passes out of 150 tests is required to declare a pass over the 150 tests, then maxFails(150) returns 3 = 150 - 147.
        * Typically, the provided 'failTable' function is used, but users may supply their own if desired.

    * minTests:   A desired minimum number of tests or rounds to be carried out. 
        * Testing which has fewer than minTests rounds may be suppressed with printLowRounds=False.
        * When not suppressed, passing tests having fewer than minTests rounds will be flagged with an `*`. Fails with fewer than maxFails(minTests) test faillures will also be flagged with an `*`.
    * printLowRounds: When False, results with fewer than 'minTests' rounds are not printed.
        * NOTE: This excludes results based on the overall rounds only (results[resNum]["roundTotal"]), not the rounds for individual IID tests (results[resNum]["passList"][testName][1]), which may be fewer if testing used the "-r abort1Fail" option.
    * platformList:   A list of platforms to print. Other platforms are ignored. If platformList == [], all platforms are printed.
    * printSet:   A set of table columns to print in the output. 
        * To print all columns, use an empty set, {}, or list all options: {"roundPass", "passList", "filename", "datestamp", "platform"}.
        * For the minimum columns, {"basic"} may be used.
        * Otherwise, include the desired columns out of {"roundPass", "passList", "filename", "datestamp", "platform"}.
    * dateRange:  Use dateRange=["",""] to print all dates. Otherwise, set the strings in the list to the datestamps at the start and end of the range to be printed.
        * NOTE: An example of a full datestamp is: "2024-07-08 09:52:44.204973" - even if the datestamps printed are truncated. If you use shorter strings in the dateRange, make sure that the when sorted, the full datestamp strings for the desired results fall between the strings you specify (e.g. you may need to add some time to the last datestamp to retrieve all desired items).
    * shortDatestamp: When True, results are printed with datestamps truncated to the seconds, e.g. "2024-07-08 09:52". This does not affect the length of the datestamp stored in the results; nor does it affect the dateRange, which is still based on the full length.
    * printAllIndividTestResults: 
        * When True, results for each of the individual IID tests in the "passList" are printed for each result item, one per line.
        * When False, each result item is summarised in a single line of output, with only the results of the worst individual IID test listed.
        * NOTE: When printAllIndividTestResults = False, if more than one individual IID test is 'worst', only one is printed.
        * NOTE: 'worst' is considered to be the test(s) with the minimum number of passes, and of those, the test(s) with the maximum number of tests.
    * printSorted: Set to True if a copy of the resultsList should be sorted before printing. Otherwise, results are grouped by platform but printed unsorted.
        * NOTE: A copy of the resultsList is sorted before the results are printed, so that the original list remains unsorted but the results are printed in a sorted order.
* Usage:

    result_print(resultsList, maxFails=failTable, minTests=1, printLowRounds=True, platformList=[], printSet={}, dateRange=["",""], 
                 shortDatestamp=False, printAllIndividTests=False, printSorted=True)

### result_min_pass_level

* Purpose: Return the minimum passing decimation level for the requested results.
* Parameters:
    * resultsList: A list of individual Decimation test results. Each result in the list is a dictionary with the same structure as the exampleResultItem.
    * maxFails:   A function which takes as input the number of tests and returns the maximum number of failing tests compatible with an overall pass.
        * E.g. if at least 147 passes out of 150 tests is required to declare a pass over the 150 tests, then maxFails(150) returns 3 = 150 - 147.
        * Typically, the provided 'failTable' function is used, but users may supply their own if desired.

    * minTests:   A desired minimum number of tests or rounds to be carried out. 
        * Testing which has fewer than minTests rounds may be ignored with checkLowRounds=False.
        * When not ignored, passing tests having fewer than minTests rounds will be flagged. Fails with fewer than maxFails(minTests) test faillures will also be flagged.
    * checkLowRounds: When False, results with fewer than 'minTests' rounds are ignored.
        * NOTE: This excludes results based on the overall rounds only (results[resNum]["roundTotal"]), not the rounds for individual IID tests (results[resNum]["passList"][testName][1]), which may be fewer if testing used the "-r abort1Fail" option. However, if the 'worst' of the individual IID tests passes with fewer than minTests rounds, it will be included in calculations for minPassingStarDecLevel, not minPassingDecLevel.
    * platformList:   A list of platforms to check. Other platforms are ignored. If platformList == [], all platforms are checked.
    * dateRange:  Use dateRange=["",""] to check all dates. Otherwise, set the strings in the list to the datestamps at the start and end of the range to be checked.
        * NOTE: An example of a full datestamp is: "2024-07-08 09:52:44.204973" - even if the datestamps printed are truncated. If you use shorter strings in the dateRange, make sure that the when sorted, the full datestamp strings for the desired results fall between the strings you specify (e.g. you may need to add some time to the last datestamp to retrieve all desired items).
* Return value: [minPassingDecLevel, minPassingStarDecLevel]
    * minPassingDecLevel: For the 'worst' individual IID test with at least minTests tests from each result item checked, the minimum passing decimation level.
    * minPassingStarDecLevel: For the 'worst' individual IID test (with any number of tests > 0) from each result item checked, the minimum passing decimation level.
    * NOTE: 'worst' is considered to be the test(s) with the minimum number of passes, and of those, the test(s) with the maximum number of tests.
* Usage:

    [minPassingDecLevel, minPassingStarDecLevel] = result_min_pass_level(results, maxFails=failTable, minTests=1, checkLowRounds=True, platformList=[], dateRange=["",""])
