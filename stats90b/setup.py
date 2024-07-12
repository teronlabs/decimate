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

from setuptools import setup, Extension

module = Extension(
    'stats90b',
    sources=['stats90b.cpp', '../SP800-90B_EntropyAssessment/cpp/iid_main.cpp'],
    extra_link_args=["-std=c++11", "-fopenmp", "-O2", "-ffloat-store", "-I/usr/include/jsoncpp", "-msse2", "-march=native"],
    extra_compile_args=["-std=c++11", "-fopenmp", "-O2", "-ffloat-store", "-I/usr/include/jsoncpp", "-msse2", "-march=native"],
    libraries = ["bz2", "pthread", "divsufsort", "divsufsort64", "jsoncpp", "crypto"]
)

setup(
    name='stats90b',
    version='1.1.7.post1',
    description='A Python C-extension to run the NIST SP 800-90B IID statistical tests',
    ext_modules=[module],
)
