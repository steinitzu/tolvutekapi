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

from tolvutek import Tolvutek, TolvutekError

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

    def get_rams(self, ramtype, size=None):
        """
        Get all ram products matching `size` and `ram_type`. 
        (e.g. 8 and ddr3 for all 8gb ddr3).
        """
        #jn = True if size else False
        rams = self.api.get_products(
            'tolvuihlutir', 'vinnsluminni-bordtolvur', ramtype
            )
        if not size:
            return rams
        newrams = []
        ms = r'.+%sGB %s' % (size, ramtype)
        for ram in rams:
            if re.match(ms, ram.name, re.IGNORECASE):
                newrams.append(ram)
        self.api.sort_products(newrams)
        return newrams

    def get_mobo_ram_type(self, motherboard):
        match = None
        for ram in self.get_ram_types():
            if ram.lower() in motherboard.description.lower():
                if match == 'ddr' or not match:
                    match = ram
        if not match:
            raise TolvutekError(
                'No supported ram type found for: {}'.format(motherboard)
                )
        return match

    def get_cpus(self, socket):
        return self.api.get_products('tolvuihlutir', 'orgjorvar', socket)

    def get_motherboards(self, socket):
        return self.api.get_products('tolvuihlutir', 'modurbord', socket)

    def get_drives(self, drivetype, size=None):        
        if drivetype == 'HDD':
            overview = self.api.get_products(
                'tolvuihlutir', 'hardir-diskar-35', 'sata3'
                )
        elif drivetype == 'SSD':
            overview = self.api.get_products(
                'tolvuihlutir', 'ssd-diskar', 'sata3'
                )
        else:
            raise TolvutekError(
                'drivetype argument must be "SSD" or "HDD"'
                )
        if not size:
            return overview
        ms = r'^%s.+' % size
        newdrives = []
        for drive in overview:
            if re.match(ms, drive.name, re.IGNORECASE):
                newdrives.append(drive)
        self.api.sort_products(newdrives)
        return newdrives

    def write_build(self, fn, format='txt'):
        """
        Write `self.build` to file in given format.
        """
        t = u''
        total = 0
        totalcommon = 0
        for prod in self.build.itervalues():
            if not prod: continue
            self.api.fill_product(prod)
            line = u'{name} - {discount_price} / {common_price} ({url})\n'.format(
                **prod.__dict__
                )
            t += line
            total+=prod.discount_price
            totalcommon+=prod.common_price
        t += u'Heildarverð:{}\n'.format(total)
        t += u'Almennt verð:{}\n'.format(totalcommon)            
        f = open(fn, 'w')
        f.write(t.encode('utf-8'))
        f.close()        

class BuilderUI(object):

    def __init__(self, ttuser=None, ttpassword=None):
        if not ttuser or not ttpassword:
            ttuser = raw_input('Notendanafn: ')
            ttpassword = getpass.getpass()
        self.builder = Builder(ttuser, ttpassword)
        self.build = self.builder.build

    def choice(self, question, options, detailsfunc=None, returninput=False):
        """
        Give a string `qeustion` and list of options.
        Prints the question and option to screen and returns 
        the user selected options.
        Objects in `options` can be anything, their __str__ represenation 
        will be given to the user.

        `detailsfunc` is the function item is passed through 
        when '?\d' option is selected.

        if `returninput` is True, whatever the user enters is returned.
        options will be ignored.
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
            if returninput:
                return selection
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
            s = u'\n{}/{} kr.\n{}\n{}'.format(
                item, item.common_price, item.description, item.url)
            return s
        sockets = self.builder.get_sockets()
        socket = self.choice(
            'Veldu sökkul:', 
            sockets,
            )
        b = self.build
        b['cpu'] = self.choice(
            'Veldu örgjörva:', 
            self.builder.get_cpus(socket),
            detailsfunc=detailsfunc
            )
        b['motherboard'] = self.choice(
            'Veldu móðurborð',
            self.builder.get_motherboards(socket),
            detailsfunc=detailsfunc
            )
        ramtype = self.builder.get_mobo_ram_type(b['motherboard'])
        ramsize = self.choice(
            'Hvað viltu mikið vinnsluminni (GB)?',
            [],
            returninput=True
            )
        rams = self.builder.get_rams(ramtype, ramsize)
        b['ram'] = self.choice(
            'Veldu vinnsluminni:',
            rams,
            detailsfunc=detailsfunc
            )        
        drivetype = self.choice(
            'Hvernig disk viltu?',
            ['HDD', 'SSD']
            )
        drivesize = self.choice(
            'Hversu storann disk (t.d. 1TB eða 120GB)? (autt til að sjá alla).',
            [],
            returninput=True
            )
        b['storage'] = self.choice(
            'Veldu disk:',
            self.builder.get_drives(drivetype, drivesize),
            detailsfunc=detailsfunc
            )

        self.builder.write_build('/tmp/build.txt')
        
        
if __name__ == '__main__':
    b = BuilderUI()
    b.do_build()





