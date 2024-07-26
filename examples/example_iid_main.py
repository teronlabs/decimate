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
import random
import os


decimated_file_path = "./data/Example_iid_main_File1.bin"

# Generate a random file for test purposes.
with open(decimated_file_path, "wb") as myFile:
    myFile.write(random.randbytes(1000000))

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

# Clean up the temporary file.
if os.path.exists(decimated_file_path):
    os.remove(decimated_file_path)