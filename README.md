# Beets-Plugin_VGMdb
A small plugin to collect metadata from VGMdb and manage a VGMdb collection

Beets link : https://beets.io/

It can:
    
    - search on VGMdb for a release
    - use the best track name distance for track matching (for the case where you can have the track in another language)
    - log to your vgmdb account and on album import (where the data source came from vgmdb) add the album to your account
    - add new option to give vgmdb id or search vgmdb using a query 

### Configuration:
There are two plugin name for different feature:
- VGMplug
- VGMCollection

Example config.yaml
```
plugins: VGMplug VGMCollection
```
Options are given below:

VGMplug Config:

    "lang-priority": 'en, ja-latn, ja'
    
    "source_weight": 0.0
    
    "artist-priority" : "composers,performers,arrangers"
    
VGMCollection config:

    "username": "ExampleLogin"
    "password": "ExamplePassword"
    "autoimport': True # VGMdb import require login and password set
    "autoremove": False # on album remove, remove the album from your VGMdb account

Installation:

https://beets.readthedocs.io/en/stable/plugins/index.html#other-plugins

## Note on using VGMplug with the plugin `albumtype`
The list of possible albumtype given by VGMdb is:
- Original Soundtrack
- Remaster
- Drama
- Arrangement
- Prototype/Unused
- Talk
- Remix
- Vocal
- Live Event
- Original Work
- Video
- Sound Effect
- Data

## TODO: 
- fetch art using vgmdb
- better error handling
- tests for api changes
- advanced search api
