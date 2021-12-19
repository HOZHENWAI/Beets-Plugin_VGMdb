# Beets-Plugin_VGMdb
A small plugin to collect metadata from VGMdb and manage a VGMdb collection

Beets link : https://beets.io/

It can:
    - search on VGMdb for a release
    - use the best track name distance for track matching (for the case where you can have the track in another language)
    - log to your vgmdb account and on album import (where the data source came from vgmdb) add the album to your account

Config:
    "login": "ExampleLogin"
    
    "password": "ExamplePassword"
    
    "lang-priority": 'en, ja-latn, ja'
    
    "autoimport': True # VGMdb import require login and password set
    
    "autoremove": False # on album remove, remove the album from your VGMdb account
    
    "source_weight": 0.0

Installation:

https://beets.readthedocs.io/en/stable/plugins/index.html#other-plugins

TODO: 
- fetch art using vgmdb
- advanced search api
