#!/usr/bin/env python
#encoding:utf-8

# This file is part of tolvutekbuilder.
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

import getpass
import logging
import re

from tolvutek import Tolvutek

log = logging.getLogger('tolvutek')

class BuildItem(object):
    def __init__(self, product, quantity):
        self.product = product
        self.quantity = quantity


class Builder(object):
    
    def __init__(self, ttuser, ttpassword):
        self.api = Tolvutek(username=ttuser, password=ttpassword)

        self.build = {
            'cpu':None,
            'motherboard':None,
            'storage':None,
            'memory':None,
            'case':None,
            'psu':None,
            'os':None,
            }

    def get_operating_systems(self):
        """
        Get avaialable operating systems.
        """
        prods = self.api.get_products('hugbunadur', 'microsoft-windows')
        return prods

    def get_sockets(self):
        """
        Get available cpu sockets.
        """
        socks = self.api.cats['tolvuihlutir']['orgjorvar']
        socks.remove('orgjorvakaelingar')
        socks.remove('kaelikrem')
        return socks

    def get_ram_types(self):
        """
        Get available ram types.
        """
        rams = self.api.cats['tolvuihlutir']['vinnsluminni-bordtolvur']
        return rams

    def get_cpus(self, socket):
        return self.api.get_products('tolvuihlutir', 'orgjorvar', socket)

    def get_motherboards(self, socket):
        return self.api.get_products('tolvuihlutir', 'modurbord', socket)        


class BuilderUI(object):

    def __init__(self, ttuser=None, ttpassword=None):
        if not ttuser or not ttpassword:
            ttuser = raw_input('Notendanafn: ')
            ttpassword = getpass.getpass()
        self.builder = Builder(ttuser, ttpassword)
        self.build = self.builder.build

    def choice(self, question, options, detailsfunc=None):
        """
        Give a string `qeustion` and list of options.
        Prints the question and option to screen and returns 
        the user selected options.
        Objects in `options` can be anything, their __str__ represenation 
        will be given to the user.
        """
        def dat(item): return item
        if not detailsfunc:
            detailsfunc = dat
        opts = ''
        for i,v in enumerate(options):
            s = '%d - %s' % (i+1, v)
            opts+=s
            opts+='\n'
        q = '\n'+question+'\n'+opts
        q+='?[%d-%d] - Fyrir frekari upplýsingar.\n' % (1, len(options))
        q+='veldu [%d-%d]> ' % (1, len(options))
        
        while True:
            selection = raw_input(q)
            r = re.match(r'^\?(?P<num>\d+)$', selection)
            if r:
                sel = int(r.groupdict()['num'])
                try:
                    print detailsfunc(options[sel-1])
                except IndexError:
                    pass                    
                continue
            try:
                selection = int(selection)
                return options[selection-1]
            except (ValueError, IndexError) as e:
                continue        

    def do_build(self):
        def detailsfunc(item):
            s = u'\n{}\n{}\n{}'.format(item, item.description, item.url)
            return s
        sockets = self.builder.get_sockets()
        socket = self.choice(
            'Veldu sökkul:', 
            sockets,
            )
        cpu = self.choice(
            'Veldu örgjörva:', 
            self.builder.get_cpus(socket),
            detailsfunc=detailsfunc
            )
        motherboard = self.choice(
            'Veldu móðurborð',
            self.builder.get_motherboards(socket),
            detailsfunc=detailsfunc
            )
        log.debug(cpu)
        

if __name__ == '__main__':
    b = BuilderUI()
    b.do_build()





