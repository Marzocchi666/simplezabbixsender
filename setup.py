#!/usr/bin/env python

from distutils.core import setup
# you can also import from setuptools

setup(
    name = 'simplezabbixsender',
    packages = ['simplezabbixsender'],
    version = '0.0.8.4',

    description = 'Implementation of Zabbix Sender protocol',
    long_description = ( 'This module implements Zabbix Sender Protocol.\n'
                         'It allows to build list of items and send items and send '
                         'them as trapper.\n'
                         'It currently supports items as well as Low Level Discovery.\n'
                         'Based on the work by:\n'
                         'Jean Baptiste Favre @ https://github.com/jbfavre\n'
                         'kurt @ https://github.com/kmomberg\n'
                         ),    
    author = 'Matt Parr',
    author_email = 'matt@parr.geek.nz',
    license = 'GPL',
    url='https://github.com/MattParr/zabbix-sender',
    download_url = 'https://github.com/MattParr/zabbix-sender/tarball/0.0.8.3',
    keywords = ['monitoring','zabbix','trappers'],
    classifiers = [],
   )
