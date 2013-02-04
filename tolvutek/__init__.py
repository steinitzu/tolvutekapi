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
import operator
from urllib import urlencode, quote
from cookielib import CookieJar
from urllib2 import build_opener, HTTPCookieProcessor
import logging
from HTMLParser import HTMLParser

import mechanize

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
    def __init__(self, api=None, **kwargs):
        self.api = api
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


    def __getattribute__(self, attr):
        try:
            return super(Product, self).__getattribute__(attr)
        except AttributeError:
            self.api.fill_product(self)
        return super(Product, self).__getattribute__(attr)                    

class Tolvutek(object):

    url_base = u'http://tolvutek.is'
    url_product_base = u'/vorur'
    url_login = u'/login/loginsubmit'
    url_cart = u'/karfa'
    url_add_to_cart = u'/karfa/add_to_cart'
    url_search = u'/leita'
    url_asearch = u'/leit'

    def __init__(self, username=None, password=None):
        self.soup_cache = {} #url:BeautifulSoup
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

    def advanced_search(self, **kwargs):
        """
        """
        defs = {
            'title':'',
            'productnr':'',
            'pricerange':'0+-+250.000',
            'category':'',
            'manufacture':''
            }
        for key, value in defs.iteritems():
            if not kwargs.has_key(key):
                kwargs[key] = value
            elif not key == 'pricerange': #can't quote pricerange cause reasons
                kwargs[key] = quote(kwargs[key])
        url = '?title={title}&productNr={productnr}&pricerange={pricerange}&category={category}&manufacture={manufacture}'
        url = url.format(**kwargs)
        url = self.url_asearch+'/'+url
        soup = self.get_soup(url)
        return self.get_products(soup=soup)

    def get_cart(self):
        """
        Get products in cart for given session.
        """
        csoup = self.get_soup(self.url_cart, use_cache=False)
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

    def fill_product(self, product):
        """
        Fill given product with info from web.
        """
        newp = self.get_product(product.url)
        product.__dict__.update(newp.__dict__)

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
        url = self.get_url(url)
        soup = self.get_soup(url)
        leftsoup = soup.find('div', 'leftcontent')
        soup = soup.find('div', 'rightcontent')
        info = soup.findAll('span', 'modelnr')

        product = Product(
            api=self,
            model_no = h.unescape(info[0].contents[0])[len('typunumer: '):],
            catalog_no = h.unescape(info[1].contents[0])[len('Vorunumer: '):],
            common_price = info[2].contents[0][len('agv: '):-3],
            name = soup.find('h2').contents[0],
            discount_price = soup.find('div', 'price').contents[0][:-3],
            description = h.unescape(soup.find('div', 'boxinfo').contents[2]).strip(),
            add_to_cart_id = soup.find('input').attrs['value'],
            image_url = leftsoup.find('a', attrs={'rel':'prettyPhoto'}).attrs['href'],
            url = self.get_url(url)
            )    
        self.products[url] = product
        return product

    def get_products(
        self,
        cat=None,
        subcat=None,
        subsubcat=None, 
        soup=None,
        quick=True
        ):
        """
        Get all products in given category and subcategory as a list.
        Can also take a `BeautifulSoup` of a products page.
        If `just_names`, returnes a dict {'productname':'url'}. 
        Individual products will then not be scraped.
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
            products = self._extract_products(
                soup, quick=quick
                )
            self.sort_products(products)
            return products
        pages = pages.findAll('a')
        #strip the garbage links
        pages = pages[2:-2]
        products = self._extract_products(soup, quick=quick)        
        for page in pages[1:]:
            soup = self.get_soup(self.url_base+page.attrs['href'])
            ps = self._extract_products(soup, quick=quick)
            products += ps
        self.sort_products(products)
        return products

    def sort_products(self, products, field='discount_price'):
        """
        Sort given product list by given field.
        """
        products.sort(key=operator.attrgetter(field))        

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

    def get_soup(self, url, body=None, use_cache=True):
        """
        Get a BeautifulSoup object for given url and request body.
        """
        url = self.get_url(url)
        log.debug(url)
        if use_cache:
            try:
                return self.soup_cache[url]
            except KeyError:
                pass        
        soup = BeautifulSoup(self._get_html(url, body=body))
        self.soup_cache[url] = soup
        return soup

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
        self.cookie = cj._cookies['tolvutek.is']['/']['PHPSESSID']        
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

    def _extract_products(self, soup, cart=False, quick=False):
        """
        Get products from given BeautifulSoup.
        Set `cart` to True if `soup` is a cart.

        If `just_names`, returns a dict {'productname':'url'}.
        """
        if cart:
            product_soups = soup.findAll('div', 'details')
        else:
            product_soups = soup.findAll('div', attrs={'class':'box-middle'})
        products = []
        for s in product_soups:
            purl = s.find('a').attrs['href']
            if quick:
                name = s.findAll('a')[1].contents[0].strip()
                price = s.find('div', 'price').contents[0]
                prod = Product(
                    api=self, name=name, discount_price=price, url=purl
                    )
            else:
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
