# Beets-Plugin_VGMdb
A small plugin to collect metadata from VGMdb and manage a VGMdb collection.

Beets link : https://beets.io/

It can:
    
    - search on VGMdb for a release
    - use the best track name distance for track matching (for the case where you can have the track in another language)
    - log to your vgmdb account and on album import (where the data source came from vgmdb) add the album to your account
    - add new option to give vgmdb id or search vgmdb using a query

# Notes
There are some issues with vgmdb.net as a source of metadata for your musics: there are actually no track details.
Or at least, not easily parsable track details, it happens that VGMdb has no table or page for each singular tracks, 
this means that finding the correct artist for a track should be impossible. This is not impossible though, as user
have the note field to write about tracks details. The issue here is that most users have no set standard on the way to
write this information resulting in hard to parse information.
Another important steps is that as game tracks, visuals novels tracks and anime, there may be a lot of performers, etc...
Following beets standard, this means you will have a lot of variable artist album which may not be what you want.
This is customisable in the settings.

## Config
config.yaml:
```
plugins: VGMplug VGMCollection
VGMplug:
    lang-priority: "en, ja-latn, ja"
    source_weight: 0.0
    artist-priority: "composers,performers,arrangers"
VGMCollection:
    username: login
    password: password
    autoimport: True
    autoremove: True
```

## Installation:

https://beets.readthedocs.io/en/stable/plugins/index.html#other-plugins

## Notes
For a long time, I thought vgmdb.net had no official api to access its database and therefore I used the vgmdb.info api.
Unfortunately, there are some connexion issues with this site, so tried to create my own scrapper. 
There are actually an open port for the cddb/freedb database of VgmDb.net, the issue is that there are no python3 client for freedb
## Issues
- 

## TODO:
- fetch art using vgmdb
- better error handling
- tests for api changes
- advanced search api
