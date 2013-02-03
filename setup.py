#!/usr/bin/env python
#encoding:utf-8

# This file is part of tolvutekapi.
# Copyright 2013, Steinthor Palsson.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.


from setuptools import setup

setup(
    name='tolvutekapi',
    version='0.1',
    description='Product api to tolvutek.is',
    author='Steinthor Palsson',
    author_email='steinitzu@gmail.com',
    url='https://github.com/steinitzu/humblebee',
    license='MIT',

    packages=[
        'tolvutek', 
        ]
    )
