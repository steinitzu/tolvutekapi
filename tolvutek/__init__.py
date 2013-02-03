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

import codecs
from urllib import urlencode, quote
from cookielib import CookieJar
from urllib2 import build_opener, HTTPCookieProcessor
import logging
from HTMLParser import HTMLParser

from bs4 import BeautifulSoup

def get_log():
    log = logging.getLogger('tolvutek')
    formatter = logging.Formatter(
        '%(levelname)s:%(module)s.%(funcName)s: %(message)s'
        )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)
    return log

log = logging.getLogger('tolvutek')

class TolvutekError(Exception):
    pass

class Product(object): 
    def __init__(self, **kwargs):
        for key,value in kwargs.iteritems():
            if key == 'common_price' or key == 'discount_price':
                value = int(value.replace('.',''))
            elif isinstance(value, basestring):
                value = unicode(value)
            self.__setattr__(key,value)

    def __str__(self):
        s = u'{} - {} kr.'.format(
            self.name, self.discount_price
            )
        return s.encode('utf-8')

    def __unicode__(self):
        return str(self).decode('utf-8')

class Tolvutek(object):

    url_base = u'http://tolvutek.is'
    url_product_base = u'/vorur'
    url_login = u'/login/loginsubmit'
    url_cart = u'/karfa'
    url_add_to_cart = u'/karfa/add_to_cart'
    url_search = u'/leita'

    def __init__(self, username=None, password=None):
        self.session = self.get_session(username, password)
        self.products = {} #url:Product dict
        self.cats = self.get_categories()
        
    def search(self, query):
        """
        Search for products matching query.
        Returns a list of Product.
        """
        query = quote(query)
        u = self.url_search+'/'+query
        soup = self.get_soup(u)
        return self.get_products(soup=soup)

    def get_cart(self):
        """
        Get products in cart for given session.
        """
        csoup = self.get_soup(self.url_cart)
        return self._extract_products(csoup, cart=True)

    def add_to_cart(self, product):
        """
        Add given product to cart.
        """
        body = {'varaId':product.add_to_cart_id}
        resp = self.post(self.url_add_to_cart, body)
        if resp.code >= 300:
            raise TolvutekError(
                u'Error occured when adding {} to cart. HTTP code: {}'.format(
                    product, resp.code)
                )        

    def get_product(self, url, usecache=True):
        """
        Get a `Product` object from `soup`.
        """
        if usecache:
            try:
                return self.products[url]
            except KeyError:
                pass
        h = HTMLParser()
        soup = self.get_soup(url)
        leftsoup = soup.find('div', 'leftcontent')
        soup = soup.find('div', 'rightcontent')
        info = soup.findAll('span', 'modelnr')

        product = Product(
            model_no = h.unescape(info[0].contents[0])[len('typunumer: '):],
            catalog_no = h.unescape(info[1].contents[0])[len('Vorunumer: '):],
            common_price = info[2].contents[0][len('agv: '):-3],
            name = soup.find('h2').contents[0],
            discount_price = soup.find('div', 'price').contents[0][:-3],
            description = h.unescape(soup.find('div', 'boxinfo').contents[2]).strip(),
            add_to_cart_id = soup.find('input').attrs['value'],
            image_url = leftsoup.find('a', attrs={'rel':'prettyPhoto'}).attrs['href'],            
            )    
        self.products[url] = product
        return product

    def get_products(self, cat=None, subcat=None, subsubcat=None, soup=None):
        """
        Get all products in given category and subcategory.
        Can also take a `BeautifulSoup` of a products page.
        """
        if not soup:
            u = u'/{}/{}'.format(cat,subcat)
            if subsubcat:
                u+=u'/'+subsubcat
            u+=u'?'
            url = self.url_base+self.url_product_base+u
            log.debug(u'product url: %s', url)
            soup = self.get_soup(url)
        pages = soup.find('div', 'paginationControl')
        if not pages:
            return self._extract_products(soup)            
        pages = pages.findAll('a')
        #strip the garbage links
        pages = pages[2:-2]
        products = self._extract_products(soup)        
        for page in pages[1:]:
            soup = self.get_soup(self.url_base+page.attrs['href'])
            ps = self._extract_products(soup)
            products += ps
        return products

    def get_categories(self):
        """
        Get all product categories, sub categories and sub-sub categories.
        {'cat':{'subcat':['subsubcats'], 'subcat2':['subsubcats']}
        """
        def stripurl(url):
            return url.strip('/vorur/').strip('?')
        soup = self.get_soup(self.url_base)
        catsoup = soup.find('ul', attrs={'id':'valmynd'})

        #all the <li class=''> trees in a list
        catsoups = [catsoup.findNext('li', '')]
        catsoups+= catsoups[0].fetchNextSiblings()

        cats = {}

        for cat in catsoups:
            catname = stripurl(cat.findNext('a').attrs['href'])
            subsoup = cat.find('ul', 'submenu')
            subcats = {}
            for href in subsoup.findAll('a'):
                href = stripurl(href.attrs['href'])
                cubs = href.split('/')
                subcat = cubs[1]
                if len(cubs) == 3:
                    subsubcat = cubs[2]
                else:
                    subsubcat = None
                if not subcats.has_key(subcat):
                    subcats[subcat] = []
                if subsubcat:
                    subcats[subcat].append(subsubcat)
            cats[catname] = subcats
        return cats                

    def get_soup(self, url, body=None):
        """
        Get a BeautifulSoup object for given url and request body.
        """
        url = self.get_url(url)
        return BeautifulSoup(self._get_html(url, body=body))

    def get_session(self, user, pw):
        """
        Get the session urlopener.
        """
        cj = CookieJar()
        opener = build_opener(HTTPCookieProcessor(cj))
        data = urlencode(
            {'username':user,'password':pw}
            )
        opener.open(self.url_base+self.url_login, data)
        return opener

    def post(self, url, body):
        """
        Do a post and get response object.
        """
        url = self.get_url(url)
        body = urlencode(body)
        response = self.session.open(url, body)
        return response
        
    def get_url(self, url):
        """
        Get absolute url for given url.
        """
        if not url.startswith(self.url_base):
            url = self.url_base+url
        return url
        

    def _extract_products(self, soup, cart=False):
        """
        Get products from given BeautifulSoup.
        Set `cart` to True if `soup` is a cart.
        """
        if cart:
            product_soups = soup.findAll('div', 'details')
        else:
            product_soups = soup.findAll('div', attrs={'class':'box-middle'})
        products = []
        for s in product_soups:
            purl = s.find('a').attrs['href']
            prod = self.get_product(purl)
            products.append(prod)
        return products

    def _get_html(self, url, body=None):
        if body is not None:
            body = urlencode(body)
        html = self.session.open(url, body).read()
        html = html.decode('utf-8', 'mixed')
        return html


last_pos = -1
def mixed_decoder(unicode_error):
    global last_pos
    string = unicode_error[1]
    pos = unicode_error.start
    if pos <= last_pos:
        pos = last_pos+1
    last_pos = pos
    new_char = string[pos].decode('ISO-8859-1')
    return new_char, pos+1

codecs.register_error('mixed', mixed_decoder)
