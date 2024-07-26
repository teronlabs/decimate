# EntropyAssessment

Cryptographic random bit generators (RBGs), also known as random number generators (RNGs), require a noise source that produces digital outputs with some level of unpredictability, expressed as min-entropy. [SP 800-90B](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-90B.pdf) provides a standardized means of estimating the quality of a source of entropy.

## License for SP800-90B_EntropyAssessment folder

### Modification List

The files in the [SP800-90B_EntropyAssessment](../SP800-90B_EntropyAssessment) folder were originally produced by NIST (version 1.1.7).

Teron Labs modified or added the following files in July 2024. 

[cpp/iid_main.cpp](cpp/iid_main.cpp)
* Add the functionality of requesting specific IID tests with the -r <test_to_run> option.
* Return to the calling function a string in JSON/Python dictionary format of the individual IID tests run and whether they passed or failed.
* Split the Chi-squared testing into two separate function calls so that results for each test could be reported separately.*

[cpp/iid_main.h](cpp/iid_main.h)
* This file was created by Teron Labs to facilitate importing the IID testing into Python.

[cpp/iid/chi_square_tests.h](cpp/iid/chi_square_tests.h)

* Copy the Chi-squared testing from function chi_square_tests into two separate function calls, chi_square_test1 and chi_square_test2, so that results for each test can be reported separately.

[cpp/iid/permutation_tests.h](cpp/iid/permutation_tests.h)

* Alter function permutation_tests to accept an additional parameter, the string res, to which results of each permutation test are appended as a pass or failed result, and re-name the function to permutation_tests_res.

* Create a wrapper function, perutation_tests with the original parameter list so that functions that do not require the results string do not need to change their interface.

* To this end, an additional function was created, string_dict_results.

[cpp/shared/utils.h](cpp/shared/utils.h)

* Alter attempts to assign to a string: `"... '%s' ...", file_path`
to avoid the compiler warning that "right operand of comma operator has no effect" by creating a temporary string `msg` and assigning each component to msg individually.

[README.md](README.md)

* This list of modifications was included. 
* The `bin/` folder containing binary files for testing purposes has not been provided in this distribution. (Only the [cpp](./cpp) folder is included.)
* The `-r` option has been added to the ea_iid description. 
* The 'How to run NIST's standalone tools' section may be ignored if standalone use of NIST's tools is not required.
* See [src/README.md](../src/README.md) for instructions on how to use the NIST IID testing tool in conjunction with Teron Labs' Decimate Python library.

### License

The following licence applies to all files in the [SP800-90B_EntropyAssessment](../SP800-90B_EntropyAssessment) folder. (Files which are not in that folder, including  files in the [src](../src) folder, are **not covered by this licence**. See [src/LICENSE.md](../src/LICENSE.md) instead for those files.)

NIST-developed software is provided by NIST as a public service. You may use, copy, and distribute copies of the software in any medium, provided that you keep intact this entire notice. You may improve, modify, and create derivative works of the software or any portion of the software, and you may copy and distribute such modifications or works. Modified works should carry a notice stating that you changed the software and should note the date and nature of any such change. Please explicitly acknowledge the National Institute of Standards and Technology as the source of the software.

NIST-developed software is expressly provided "AS IS." NIST MAKES NO WARRANTY OF ANY KIND, EXPRESS, IMPLIED, IN FACT, OR ARISING BY OPERATION OF LAW, INCLUDING, WITHOUT LIMITATION, THE IMPLIED WARRANTY OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT, AND DATA ACCURACY. NIST NEITHER REPRESENTS NOR WARRANTS THAT THE OPERATION OF THE SOFTWARE WILL BE UNINTERRUPTED OR ERROR-FREE, OR THAT ANY DEFECTS WILL BE CORRECTED. NIST DOES NOT WARRANT OR MAKE ANY REPRESENTATIONS REGARDING THE USE OF THE SOFTWARE OR THE RESULTS THEREOF, INCLUDING BUT NOT LIMITED TO THE CORRECTNESS, ACCURACY, RELIABILITY, OR USEFULNESS OF THE SOFTWARE.

You are solely responsible for determining the appropriateness of using and distributing the software and you assume all risks associated with its use, including but not limited to the risks and costs of program errors, compliance with applicable laws, damage to or loss of data, programs or equipment, and the unavailability or interruption of operation. This software is not intended to be used in any situation where a failure could cause risk of injury or damage to property. The software developed by NIST employees is not subject to copyright protection within the United States.

## Issues

Issues on this repository are strictly for problems or questions concerning the codebase as a standalone implementation of SP800-90B. Any questions or comments on the specification itself should be directed towards the authors of the document. 

## Requirements

This code package requires a C++11 compiler. The code uses OpenMP directives, so compiler support for OpenMP is expected. GCC is preferred (and the only platform tested). There is one method that involves a GCC built-in function (`chi_square_tests.h -> binary_goodness_of_fit() -> __builtin_popcount()`). To run this you will need some compiler that supplies this GCC built-in function (GCC and clang both do so).

The resulting binary is linked with bzlib, divsufsort, jsoncpp, GMP MP and GNU MPFR, so these libraries (and their associated include files) must be installed and accessible to the compiler.

On Ubuntu they can be installed with `apt-get install libbz2-dev libdivsufsort-dev libjsoncpp-dev libssl-dev libmpfr-dev`.

See [the wiki](https://github.com/usnistgov/SP800-90B_EntropyAssessment/wiki/Installing-Packages) for some distribution-specific instructions on installing the mentioned packages.

## Overview

* `cpp/` holds the C++ codebase

## How to run NIST's standalone tools 

For instructions on using the IID testing tool in conjunction with Teron Labs' Decimate Python library, see the [src/README.md](../src/README.md) file. The following instructions may be ignored if standalone use of NIST's tools is not required.

The project is divided into two sections, IID tests and non-IID tests. They are intended to be separate. One provides an assurance that a dataset is IID [(independent and identically distributed)](https://en.wikipedia.org/wiki/Independent_and_identically_distributed_random_variables) and the other provides an estimate for min-entropy for any data provided. Please note that most commonly used entropy sources are not IID; see IG7.18 for the additional justification necessary to support any IID claim.

One can make all the binaries using:

	make

After compiling, one can test that your compilation behaves as expected by using the self-test functionality:
	
	cd selftest
	./selftest

Any observed delta less than 1.0E-6 is considered a pass for the self test.

For IID tests use the Makefile to compile the program:

    make iid

Then you can run the program with

    ./ea_iid [-i|-c] [-a|-t] [-v] [-l <index>,<samples>] [-r <test_to_run>] <file_name> [bits_per_symbol]

You may specify either `-i` or `-c`, and either `-a` or `-t`. These correspond to the following:

* `-i`: Indicates the data is unconditioned and returns an initial entropy estimate. This is the default.
* `-c`: Indicates the data is conditioned, and should only be assessed as a bitstring.
* `-a`: The calculated `H_bitstring` assessment is produced using all data that is read.
* `-t`: Truncates the data used to calculate the `H_bitstring` assessment to the first one million bits.
* Note: When testing binary data, no `H_bitstring` assessment is produced, so the `-a` and `-t` options produce the same results for the initial assessment of binary data.
* `-l`: Reads (at most) `samples` data samples after indexing into the file by `index*samples` bytes.
* `-v`: Optional verbosity flag for more output. Can be used multiple times.
* bits_per_symbol are the number of bits per symbol. Each symbol is expected to fit within a single byte.
* `-r`: Specifies which test to run where test_to_run is one of the following: chi1, chi2, LRS, perm, all, abort1fail. If the -r option is not used, all tests are run. chi1 = independence, chi2 = goodness of fit. abort1fail = abort the remainder of the testing upon completing a test that fails. 

To run the non-IID tests, use the Makefile to compile:

    make non_iid

Running this works the same way. This looks like

	./ea_non_iid [-i|-c] [-a|-t] [-v] [-l <index>,<samples> ] <file_name> [bits_per_symbol]

To run the restart testing, use the Makefile to compile:
    
    make restart

Running this is similar.
	
	./ea_restart [-i|-n] [-v] <file_name> [bits_per_symbol] <H_I>

The file should be in the "row dataset" format described in SP800-90B Section 3.1.4.1.

* `-i`: Indicates IID data.
* `-n`: Indicates non-IID data.
* `-v`: Optional verbosity flag for more output. Can be used multiple times.
* bits_per_symbol are the number of bits per symbol. Each symbol is expected to fit within a single byte.
* `H_I` is the assessed entropy.

To calculate the entropy reduction due to conditioning, use the Makefile to compile:
    
    make conditioning

Running this is similar.

    ./ea_conditioning [-v] <n_in> <n_out> <nw> <h_in>

or

    ea_conditioning -n <n_in> <n_out> <nw> <h_in> <h'>

* `-v`: The conditioning function is vetted.
* `-n`: The conditioning function is non-vetted.
* `n_in`: The number of bits entering the conditioning step per output.
* `n_out`: The number of bits per conditioning step output.
* `nw`: The narrowest width of the conditioning step.
* `h_in`: The amount of entropy entering the conditioning step per output. Must be less than n_in.
* `h'`:  The entropy estimate per bit of conditioned sequential dataset (only for '-n' option).

## Make

A `Makefile` is provided.

## How to cross-compile

To cross-compiling for a different CPU architecture, set `ARCH` and `CROSS_COMPILE` variables in you Makefile commandline

    make ARCH=aarch64 CROSS_COMPILE=aarch64-linux-gnu-

## More Information

For more information on the estimation methods, see [SP 800-90B](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-90B.pdf).

## Contributions

Pull requests are welcome and will be reviewed before being merged. No timelines are promised. The code is maintained by Chris Celi (NIST).
