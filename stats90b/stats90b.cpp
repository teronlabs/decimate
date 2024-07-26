// This file is part of Teron Labs' Decimate distribution.
// Copyright (C) 2024 Teron Labs <https://www.teronlabs.com/>, <info@teronlabs.com>
//
// Licensed under the GNU General Public License v3.0 (GPLv3). For details see the LICENSE.md file.
//
// Author(s)
// Yvonne Cliff, Teron Labs <yvonne@teronlabs.com>.
//
//   This program is free software: you can redistribute it and/or modify
//   it under the terms of the GNU General Public License as published by
//   the Free Software Foundation, version 3 of the License.
//
//    This program is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU General Public License for more details.
//
//    You should have received a copy of the GNU General Public License
//    along with this program.  If not, see <https://www.gnu.org/licenses/>.




#include <Python.h>
#include "../SP800-90B_EntropyAssessment/cpp/iid_main.h"
#include <iostream>
#include <string>
#include <vector>
using namespace std;


// Create customSplit() function to split a string into a vector of words of type char*.  
// This is used on the arguments to be passed to the NIST iid_main.cpp code
// so that they may be passed as an array in argv.
void customSplit(string str, vector < char * > *argvP) {
    unsigned int startIndex = 0, endIndex = 0;
    for (unsigned int i = 0; i <= str.size(); i++) {
        
        // If we reached the end of the word or the end of the input:
        if (str[i] == ' ' || str[i] == '\t' || i == str.size()) {
            if (i == startIndex) {
                // We found whitespace; move the startIndex along by 1 character.
                startIndex += 1;
            } else {
                // We found a word going from startIndex to i. Save it to the argvP vector.
                endIndex = i;
                string temp;
                temp.append(str, startIndex, endIndex - startIndex);
                char *tempC = new char[temp.size()+1];
                strcpy(tempC, temp.c_str());
                argvP->push_back(tempC);
                startIndex = endIndex + 1;
            }
        }
    }
}

// Create the method that will call the IID testing from the NIST suite.
static PyObject *method_iid_main(PyObject *self, PyObject *args) {

    char *str  = NULL;

    // Create the string to pass as argv to NIST's iid_main.cpp
    // The string starts with the program name, ea_iid:
    string argvStart="ea_iid ";

    /* Parse arguments */
    // Store the arguments passed from Python in a single char*, str.
    if(!PyArg_ParseTuple(args, "s", &str)) {

        return NULL;

    }
    // argv is a vector to store each word in the arguments.
    vector < char * > argv;
    // Convert str to a C++ string, argvEnd.
    string argvEnd(str);
    // Create a C++ string (argvStr) containing the program name (argvStart) and arguments from Python (argvEnd).
    string argvStr = argvStart + argvEnd;
    // Split argvStr into a vector of words, argv.
    customSplit(argvStr, &argv);

    // Call NIST's iid_main.cpp with argc = argv.size, and argv.
    // Save the results in string res.
    string res = iid_main(argv.size(), &argv[0]);

    // Delete each word in argv.
    for ( size_t i = 0 ; i < argv.size() ; i++ )
            delete [] argv[i];

    // Return the results in string res.
    return PyUnicode_FromString(res.c_str());

}


// List the methods exported from the NIST SP 800-90B statistical testing code.
// Currently, only the IID testing is exported.
static PyMethodDef Stats90bMethods[] = {
    {"iid_main", method_iid_main, METH_VARARGS, "Python interface for IID testing from ea_iid"},
    {NULL, NULL, 0, NULL}
};

// Define the module being exported.
static struct PyModuleDef stats90bmodule = {
    PyModuleDef_HEAD_INIT,
    "stats90b",
    "Python interface for the NIST SP 800-90B Entropy Assessment Statistical Testing Suite",
    -1,
    Stats90bMethods
};


PyMODINIT_FUNC PyInit_stats90b(void) {
    return PyModule_Create(&stats90bmodule);
}
