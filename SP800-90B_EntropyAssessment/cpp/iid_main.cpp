/* VERSION information is kept in utils.h. Please update when a new version is released */

// iid_main.cpp was originally produced by NIST (version 1.1.7) and modified by 
// Teron Labs <https://www.teronlabs.com> <info@teronlabs.com> in July 2024. 
//
// Modification Author(s):
// Yvonne Cliff, Teron Labs <yvonne@teronlabs.com>.
// 
// Modifications by Teron Labs to iid_main.cpp in July 2024 are as follows:
//     Add the functionality of requesting specific IID tests with the -r <test_to_run> option.
//     Return to the calling function a string in JSON/Python dictionary format of the individual IID tests run and whether they passed or failed.
//     Split the Chi-squared testing into two separate function calls so that results for each test could be reported separately.
// End modification list.
//
// Licence for iid_main.cpp:
//
// NIST-developed software is provided by NIST as a public service. 
// You may use, copy, and distribute copies of the software in any medium, provided that you keep intact this entire notice. 
// You may improve, modify, and create derivative works of the software or any portion of the software, 
// and you may copy and distribute such modifications or works. 
// Modified works should carry a notice stating that you changed the software and should note the date and nature of any such change. 
// Please explicitly acknowledge the National Institute of Standards and Technology as the source of the software.

// NIST-developed software is expressly provided "AS IS." NIST MAKES NO WARRANTY OF ANY KIND, EXPRESS, IMPLIED, IN FACT, 
// OR ARISING BY OPERATION OF LAW, INCLUDING, WITHOUT LIMITATION, THE IMPLIED WARRANTY OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, 
// NON-INFRINGEMENT, AND DATA ACCURACY. NIST NEITHER REPRESENTS NOR WARRANTS THAT THE OPERATION OF THE SOFTWARE WILL BE UNINTERRUPTED OR ERROR-FREE, 
// OR THAT ANY DEFECTS WILL BE CORRECTED. NIST DOES NOT WARRANT OR MAKE ANY REPRESENTATIONS REGARDING THE USE OF THE SOFTWARE OR THE RESULTS THEREOF, 
// INCLUDING BUT NOT LIMITED TO THE CORRECTNESS, ACCURACY, RELIABILITY, OR USEFULNESS OF THE SOFTWARE.

// You are solely responsible for determining the appropriateness of using and distributing the software and you assume all risks associated 
// with its use, including but not limited to the risks and costs of program errors, compliance with applicable laws, damage to or loss of data, 
// programs or equipment, and the unavailability or interruption of operation. This software is not intended to be used in any situation where a 
// failure could cause risk of injury or damage to property. The software developed by NIST employees is not subject to copyright protection within 
// the United States.
//
// End Licence.

// Modification by Teron Labs: 
//      #include "iid_main.h" added
#include "iid_main.h"

#include "shared/utils.h"
#include "shared/most_common.h"
#include "shared/lrs_test.h"
#include "iid/iid_test_run.h"
#include "shared/TestRunUtils.h"
#include "iid/permutation_tests.h"
#include "iid/chi_square_tests.h"
#include <openssl/sha.h>
#include <omp.h>
#include <getopt.h>
#include <limits.h>

#include <iostream>
#include <fstream>

using namespace std;

// Modificaiton by Teron Labs:
//      Usage is modified to add the -r <test_to_run> option.
[[ noreturn ]] void print_usage() {
    // The following line was modified by Teron Labs to add the -r <test_to_run> option:
    printf("Usage is: ea_iid [-i|-c] [-a|-t] [-v] [-q] [-l <index>,<samples> ] [-r <test_to_run>] <file_name> [bits_per_symbol]\n\n");

    printf("\t <file_name>: Must be relative path to a binary file with at least 1 million entries (samples).\n");
    printf("\t [bits_per_symbol]: Must be between 1-8, inclusive. By default this value is inferred from the data.\n");
    printf("\t [-i|-c]: '-i' for initial entropy estimate, '-c' for conditioned sequential dataset entropy estimate. The initial entropy estimate is the default.\n");
    printf("\t [-a|-t]: '-a' produces the 'H_bitstring' assessment using all read bits, '-t' truncates the bitstring used to produce the `H_bitstring` assessment to %d bits. Test all data by default.\n", MIN_SIZE);
    printf("\t Note: When testing binary data, no `H_bitstring` assessment is produced, so the `-a` and `-t` options produce the same results for the initial assessment of binary data.\n");
    printf("\t -v: Optional verbosity flag for more output. Can be used multiple times.\n");
    printf("\t -q: Quiet mode, less output to screen. This will override any verbose flags.\n");
    printf("\t -l <index>,<samples>\tRead the <index> substring of length <samples>.\n");
    printf("\n");
    printf("\t Samples are assumed to be packed into 8-bit values, where the least significant 'bits_per_symbol'\n");
    printf("\t bits constitute the symbol.\n");
    printf("\n");
    printf("\t -i: Initial Entropy Estimate (Section 3.1.3)\n");
    printf("\n");
    printf("\t\t Computes the initial entropy estimate H_I as described in Section 3.1.3\n");
    printf("\t\t (not accounting for H_submitter) using the entropy estimators specified in\n");
    printf("\t\t Section 6.3.  If 'bits_per_symbol' is greater than 1, the samples are also\n");
    printf("\t\t converted to bitstrings and assessed to create H_bitstring; for multi-bit symbols,\n");
    printf("\t\t two entropy estimates are computed: H_original and H_bitstring.\n");
    printf("\t\t Returns min(H_original, bits_per_symbol X H_bitstring). The initial entropy\n");
    printf("\t\t estimate H_I = min(H_submitter, H_original, bits_per_symbol X H_bitstring).\n");
    printf("\n");
    printf("\t -c: Conditioned Sequential Dataset Entropy Estimate (Section 3.1.5.2)\n");
    printf("\n");
    printf("\t\t Computes the entropy estimate per bit h' for the conditioned sequential dataset if the\n");
    printf("\t\t conditioning function is non-vetted. The samples are converted to a bitstring.\n");
    printf("\t\t Returns h' = min(H_bitstring).\n");
    printf("\n");
    printf("\t -o: Set Output Type to JSON\n");
    printf("\n");
    printf("\t\t Changes the output format to JSON and sets the file location for the output file.\n");
    printf("\n");
    printf("\t --version: Prints tool version information");
    printf("\n");
    printf("\n");

    // Modification by Teron Labs:
    //     Add the following usage lines:
    printf("\t -r: Specifies which test to run where test_to_run is one of the following:\n");
    printf("\t\t chi1 = Chi Square Independence Test\n");
    printf("\t\t chi2 = Chi Square Goodness of Fit Test\n");
    printf("\t\t LRS = Longest Repeated Substring Test\n");
    printf("\t\t perm = All 19 of the permutation tests\n");
    printf("\t\t all = All of above tests.\n");
    printf("\t\t abort1fail = Abort the testing and return existing results upon the first failure of a test.\n");
    printf("\t\t If the -r option is not used, all tests are run.\n");
    // End modification.

    exit(-1);
}

// Modification by Teron Labs:
//     Have iid_main return a string of results.
string iid_main(int argc, char* argv[]) {

    // Modification by Teron Labs:
    //      Reset options to be read from the beginning again.
    //      This is necessary when calling iid_main multiple times during the one program execution.

    optind = 1;

    // End modification.

    bool initial_entropy, all_bits;
    int verbose = 1; //verbose 0 is for JSON output, 1 is the normal mode, 2 is the NIST tool verbose mode, and 3 is for extra verbose output
    double rawmean, median;
    char* file_path;
    data_t data;
    int opt;
    unsigned long subsetIndex = ULONG_MAX;
    unsigned long subsetSize = 0;
    unsigned long long inint;
    char *nextOption;

    data.word_size = 0;
    initial_entropy = true;
    all_bits = true;

    bool quietMode = false;
    bool jsonOutput = false;
    string timestamp = getCurrentTimestamp();
    string outputfilename;
    string commandline = recreateCommandLine(argc, argv);

    IidTestRun testRun;
    testRun.timestamp = timestamp;
    testRun.commandline = commandline;

    // Modification by Teron Labs:
    //     Declare booleans to indicate which IID tests should be run: runChi1, runChi2, runLRS, runPerm.
    //     Declare a boolean to indicate whether testing should stop after the first failure (abort1fail).
    bool runChi1 = false;
    bool runChi2 = false;
    bool runLRS = false;
    bool runPerm = false;
    bool abort1fail = false;
    // End modification.
    
    for (int i = 0; i < argc; i++) {
        std::string Str = std::string(argv[i]);
        if ("--version" == Str) {
            printVersion("iid");
            exit(0);
        }
    }

    // Modification by Teron Labs:
    //      Add the r: option to the while condition.
    while ((opt = getopt(argc, argv, "icatvl:qo:r:")) != -1) {
        switch (opt) {
            case 'i':
                initial_entropy = true;
                break;
            case 'c':
                initial_entropy = false;
                break;
            case 'a':
                all_bits = true;
                break;
            case 't':
                all_bits = false;
                break;
            case 'v':
                verbose++;
                break;
            case 'l':
                inint = strtoull(optarg, &nextOption, 0);
                if ((inint > ULONG_MAX) || (errno == EINVAL) || (nextOption == NULL) || (*nextOption != ',')) {

                    testRun.errorLevel = -1;
                    testRun.errorMsg = "Error on index/samples.";

                    if (jsonOutput) {
                        ofstream output;
                        output.open(outputfilename);
                        output << testRun.GetAsJson();
                        output.close();
                    }
                    print_usage();
                }
                subsetIndex = inint;

                nextOption++;

                inint = strtoull(nextOption, NULL, 0);
                if ((inint > ULONG_MAX) || (errno == EINVAL)) {
                    testRun.errorLevel = -1;
                    testRun.errorMsg = "Error on index/samples.";

                    if (jsonOutput) {
                        ofstream output;
                        output.open(outputfilename);
                        output << testRun.GetAsJson();
                        output.close();
                    }
                    print_usage();
                }

                subsetSize = inint;
                break;

            // Modification by Teron Labs:
            //     Read the -r option in the arguments and set the booleans indicating which IID tests should be run.
            case 'r':
                {
                    string runOpt = optarg;
                    if (runOpt == "chi1"){
                        runChi1 = true;
                    } 
                    if (runOpt == "chi2"){
                        runChi2 = true;
                    }
                    if (runOpt == "LRS"){
                        runLRS = true;
                    }
                    if (runOpt == "perm"){
                        runPerm = true;
                    }
                    if (runOpt == "all"){
                        runChi1 = true;
                        runChi2 = true;
                        runLRS = true;
                        runPerm = true;
                    }
                    if (runOpt == "abort1fail"){
                        abort1fail = true;
                    }     
                }         
                break;
            // End modification.

            case 'q':
                quietMode = true;
                break;
            case 'o':
                jsonOutput = true;
                outputfilename = optarg;
                break;
            default:
                print_usage();
        }
    }

    argc -= optind;
    argv += optind;

    // Parse args
    if ((argc != 2) && (argc != 1)) {
        printf("Incorrect usage.\n");
        print_usage();
    }

    // Modification by Teron Labs:
    //   If no particular IID tests have been requested, set the booleans to run all of them.
    if (!runChi1 && !runChi2 && !runLRS && !runPerm){
        runChi1 = true;
        runChi2 = true;
        runLRS = true;
        runPerm = true;       
    }
    // End modification.

    // If quiet mode is enabled, force minimum verbose
    if (quietMode) {
        verbose = 0;
    }

    // get filename
    file_path = argv[0];

    testRun.filename = file_path;

    if (argc == 2) {
        // get bits per word
        data.word_size = atoi(argv[1]);
        if (data.word_size < 1 || data.word_size > 8) {

            testRun.errorLevel = -1;
            testRun.errorMsg = "Invalid bits per symbol: " + std::to_string(data.word_size) + ".";

            if (jsonOutput) {
                ofstream output;
                output.open(outputfilename);
                output << testRun.GetAsJson();
                output.close();
            }

            printf("Invalid bits per symbol: %d.\n", data.word_size);
            print_usage();
        }
    }

    // Record hash of input file
    char hash[2*SHA256_DIGEST_LENGTH+1];
    sha256_file(file_path, hash);
    testRun.sha256 = hash;

    if (verbose > 1) {
        if (subsetSize == 0) {
            printf("Opening file: '%s' (SHA-256 hash %s)\n", file_path, hash);
        } else {
            printf("Opening file: '%s' (SHA-256 hash %s), reading block %ld of size %ld\n", file_path, hash, subsetIndex, subsetSize);
        }
    }
    if (!read_file_subset(file_path, &data, subsetIndex, subsetSize, &testRun)) {
        if (jsonOutput) {
            ofstream output;
            output.open(outputfilename);
            output << testRun.GetAsJson();
            output.close();
        }

        printf("Error reading file.\n");
        print_usage();
    }

    if (verbose > 1) printf("Loaded %ld samples of %d distinct %d-bit-wide symbols\n", data.len, data.alph_size, data.word_size);

    if (data.alph_size <= 1) {

        testRun.errorLevel = -1;
        testRun.errorMsg = "Symbol alphabet consists of 1 symbol. No entropy awarded...";

        if (jsonOutput) {
            ofstream output;
            output.open(outputfilename);
            output << testRun.GetAsJson();
            output.close();
        }

        printf("Symbol alphabet consists of 1 symbol. No entropy awarded...\n");
        free_data(&data);
        exit(-1);
    }

    if (!all_bits && (data.blen > MIN_SIZE)) data.blen = MIN_SIZE;

    if ((verbose > 1) && ((data.alph_size > 2) || !initial_entropy)) printf("Number of Binary samples: %ld\n", data.blen);
    if (data.len < MIN_SIZE) printf("\n*** Warning: data contains less than %d samples ***\n\n", MIN_SIZE);
    if (verbose > 1) {
        if (data.alph_size < (1 << data.word_size)) printf("\nSamples have been translated\n");
    }

    // Calculate baseline statistics
    int alphabet_size = data.alph_size;
    int sample_size = data.len;

    if ((verbose == 1) || (verbose == 2))
        printf("Calculating baseline statistics...\n");

    calc_stats(&data, rawmean, median);

    if (verbose == 2) {
        printf("\tRaw Mean: %f\n", rawmean);
        printf("\tMedian: %f\n", median);
        printf("\tBinary: %s\n\n", (alphabet_size == 2 ? "true" : "false"));
    } else if (verbose > 2) {
        printf("Raw Mean = %.17g\n", rawmean);
        printf("Median = %.17g\n", median);
        printf("Binary = %s\n", (alphabet_size == 2 ? "true" : "false"));
    }

    IidTestCase tc;
    tc.mean = rawmean;
    tc.median = median;
    tc.binary = (alphabet_size == 2);

    double H_original = data.word_size;
    double H_bitstring = 1.0;

    // Compute the min-entropy of the dataset
    if (initial_entropy) {
        H_original = most_common(data.symbols, sample_size, alphabet_size, verbose, "Literal");
    }
    tc.h_original = H_original;

    if (((data.alph_size > 2) || !initial_entropy)) {
        H_bitstring = most_common(data.bsymbols, data.blen, 2, verbose, "Bitstring");
    }
    tc.h_bitstring = H_bitstring;

    double h_assessed = data.word_size;
    if ((verbose == 1) || (verbose == 2)) {
        if (initial_entropy) {
            printf("H_original: %f\n", H_original);
            if (data.alph_size > 2) {
                printf("H_bitstring: %f\n", H_bitstring);
                printf("min(H_original, %d X H_bitstring): %f\n", data.word_size, min(H_original, data.word_size * H_bitstring));
            }
        } else {
            printf("h': %f\n", H_bitstring);
        }
    } else if (verbose > 2) {
        h_assessed = data.word_size;

        if ((data.alph_size > 2) || !initial_entropy) {
            h_assessed = min(h_assessed, H_bitstring * data.word_size);
            printf("H_bitstring = %.17g\n", H_bitstring);
            printf("H_bitstring Per Symbol = %.17g\n", H_bitstring * data.word_size);
        }

        if (initial_entropy) {
            h_assessed = min(h_assessed, H_original);
            printf("H_original = %.17g\n", H_original);
        }

        printf("Assessed min entropy: %.17g\n", h_assessed);
    }
    tc.h_assessed = h_assessed;

    // Modificaiton by Teron Labs:
    //    Set up JSON/Python results string:

    string res = "{ ";

    // End modification.

    // Modification by Teron Labs:
    //     Split the previous "chi_squre_test_pass" function into two separate functions, one for each chi-squared test,
    //     "chi_square_test1" and "chi_square_test2".
    //     Also, save the results of each test to the results string, res.
    //     There is no longer a separate message printed when verbose == 1 or 2 compared to verbose > 2; also, the message is slightly different.

    // Compute chi square stats
    bool chi_square_test_pass1 = false;

    if (runChi1) {
        chi_square_test_pass1 = chi_square_test1(data.symbols, sample_size, alphabet_size, verbose);
        res = res + "\"chiSqIndependence\": ";
        if (chi_square_test_pass1) {
            res = res + "\"pass\" ";
        } else {
            res = res + "\"FAIL\" ";
        }

        if ((verbose >= 1) ) {
            if (chi_square_test_pass1) {
                printf("** Passed chi square test 1\n\n");
            } else {
                printf("** FAILED *** FAILED *** chi square test 1\n\n");
            }
        }
        // Modification by Teron Labs:
        //      If this test failed, and we are aborting the testing after the first failed test,
        //      set the booleans for running the remaining tests to false.
        if (abort1fail && !chi_square_test_pass1) {
            if (verbose >= 1) {
                printf("iid_main - Aborting after chi1\n");
            }
            runChi2 = false;
            runLRS = false;
            runPerm = false;
        }
    }

    bool chi_square_test_pass2 = false;
    if (runChi2){
        chi_square_test_pass2 = chi_square_test2(data.symbols, sample_size, alphabet_size, verbose);
        if (res != "{ "){
            res = res + ", ";
        }
        res = res + "\"chiSqGoodnessFit\": ";
        if (chi_square_test_pass2) {
            res = res + "\"pass\" ";
        } else {
            res = res + "\"FAIL\" ";
        }
        if ((verbose >= 1) ) {
            if (chi_square_test_pass2) {
                printf("** Passed chi square test 2\n\n");
            } else {
                printf("** FAILED *** FAILED *** chi square test 2\n\n");
            }
        }
        // Modification by Teron Labs:
        //      If this test failed, and we are aborting the testing after the first failed test,
        //      set the booleans for running the remaining tests to false.
        if (abort1fail && !chi_square_test_pass2) {
            if (verbose >= 1) {
                printf("iid_main - Aborting after chi2\n");
            }
            printf("aborting after chi2\n");
            runLRS = false;
            runPerm = false;
        }
    }
    
    
    bool chi_square_test_pass = chi_square_test_pass1 && chi_square_test_pass2;
    tc.passed_chi_square_tests = chi_square_test_pass;

    // End modification.


    // Modification by Teron Labs:
    //     Only run each test if requested.
    //     If a test is run, save the results to string res.
    //     There is no longer a separate message printed when verbose == 1 or 2 compared to verbose > 2; also, the message is slightly different.

    // Compute length of the longest repeated substring stats
    bool len_LRS_test_pass = false;
    if (runLRS) {
        len_LRS_test_pass = len_LRS_test(data.symbols, sample_size, alphabet_size, verbose, "Literal");

        if (res != "{ "){
            res = res + ", ";
        }
        res = res + "\"longestRepeatedSubstring\": ";
        if (len_LRS_test_pass) {
            res = res + "\"pass\" ";
        } else {
            res = res + "\"FAIL\" ";
        }

        if ((verbose >= 1) ) {
            if (len_LRS_test_pass) {
                printf("** Passed length of longest repeated substring test\n\n");
            } else {
                printf("** FAILED *** FAILED *** length of longest repeated substring test\n\n");
            } 
        }
        // Modification by Teron Labs:
        //      If this test failed, and we are aborting the testing after the first failed test,
        //      set the booleans for running the remaining tests to false.
        if (abort1fail && !len_LRS_test_pass) {
            if (verbose >= 1) {
                printf("iid_main - Aborting after LRS\n");
            }
            runPerm = false;
        }
    }
    tc.passed_longest_repeated_substring_test = len_LRS_test_pass;


    // Compute permutation stats
    bool perm_test_pass = false;
    if (runPerm) {
        if (res != "{ "){
            res = res + ", ";
        }

        perm_test_pass = permutation_tests_res(&data, rawmean, median, verbose, tc, res);

        if ((verbose >= 1) ) {
            if (perm_test_pass) {
                printf("** Passed IID permutation tests\n\n");
            } else {
                printf("** FAILED *** FAILED *** IID permutation tests\n\n");
            } 
        }
    }
    tc.passed_iid_permutation_tests = perm_test_pass;

    // End modification.

    testRun.testCases.push_back(tc);
    testRun.errorLevel = 0;

    if (jsonOutput) {
        ofstream output;
        output.open(outputfilename);
        output << testRun.GetAsJson();
        output.close();
    }

    free_data(&data);

    // Modification by Teron Labs:
    //    Return the string of results, res.

    res = res + "}";
    return res;

    // End modification.
}

int main(int argc, char* argv[]) {
    cout << iid_main(argc, argv);
    return 0;
}