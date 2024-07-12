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

from decimate.deci import result_open, result_sort, result_print, failTable
import json
import random
import os
import datetime

results_path = "./data/Example_decimate_bin_search_results_provided.txt"
minTests = 5

print("Previously saved results:")
results = result_open(results_path, False)

result_sort(results)

print("\n\n\n INCLUDING RESULTS FOR ALL INDIVIDUAL TESTS\n\n\n")

result_print(results, failTable, minTests=minTests, printLowRounds=True, platformList=[], 
             printSet= {}, 
             dateRange=["", str(datetime.datetime.now())], shortDatestamp=False, printAllIndividTests=True, printSorted = False)

print("\n\n\n NO RESULTS FOR INDIVIDUAL TESTS\n\n\n")

result_print(results, failTable, minTests=5, printLowRounds=True, platformList=[], 
             printSet= {"basic", "roundPass", "passList", "filename", "datestamp", "platform"}, 
             dateRange=["", ""], shortDatestamp=False, printAllIndividTests=False, printSorted = True)

print("\n\n\n ABBREVIATED FORMAT   and   ONLY PRINTING PLATFORM 'Existing'\n\n\n")

result_print(results, failTable, minTests=5, printLowRounds=False, platformList=['Existing'], 
             printSet={'roundPass', 'passList', 'datestamp'}, 
             shortDatestamp=False, printAllIndividTests=False)