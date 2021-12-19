from typing import Dict, List, Sequence, Optional
import requests
import requests.exceptions as re_ex
import hashlib
import re

from beets.plugins import BeetsPlugin
from beets.ui import Subcommand
from beets.autotag.hooks import AlbumInfo, TrackInfo, Distance, string_dist
from beets.library import Item, Library, Album


class VGMdbPlugin(BeetsPlugin):
    data_source = 'VGMdb' # MetadataSourcePlugin

    # Reference : https://vgmdb.info/
    search_items_url = "https://vgmdb.info/search/"
    search_url = "https://vgmdb.info/search/" # MetadataSourcePlugin
    search_albums_url = "https://vgmdb.info/search/albums/"
    albums_url = "https://vgmdb.info/album/"
    album_url = "https://vgmdb.info/album/" # MetadataSourcePlugin
    search_artists_url = "https://vgmdb.info/search/artists/"
    artists_url = "https://vgmdb.info/artist/"
    search_orgs_url = "https://vgmdb.info/search/orgs/"
    orgs_url = "https://vgmdb.info/org/"
    search_product_url = "https://vgmdb.info/search/products/"
    product_url = "https://vgmdb.info/product/"

    # the main site: vgmdb.net
    login_url = "https://vgmdb.net/forums/login.php"
    add_url = "https://vgmdb.net/db/collection.php?do=add"
    delete_url = "https://vgmdb.net/db/collection.php?do=manage&type=albums"

    def __init__(self):
        super(VGMdbPlugin, self).__init__()

        self.config.add({'login': None,
                         'password': None,
                         'lang-priority': 'en,ja-latn,ja',
                         'autoimport': True,
                         'autoremove': False,
                         'source_weight':0.0
                         })

        self.source_weight = self.config['source_weight'].as_number()
        self.lang = self.config['lang-priority'].get().split(",")

        track_naming_convention = {"en":"English", "ja-latn":"Romaji", "ja":"Japanese"}
        self.track_pref = [track_naming_convention[lang] for lang in self.lang]
        self.cookies = None

        if self.config["autoimport"].get():
            self.register_listener("import_task_created", self.login) # Login here may be mistake inducing since
            self.register_listener("album_imported", self.add_vgmdb_list)

        if self.config["autoremove"].get():
            self.register_listener("album_removed", self.remove_vgmdb_list)


    def login(self, task, session):
        if (self.config["login"].get() is not None) and (self.config["password"].get() is not None):
            hash = hashlib.md5(self.config["password"].get().encode())
            md5 = hash.hexdigest()
            data = {
                "vb_login_username":self.config["login"].get(),
                "cookieuser":"1",
                "securitytoken":"guest",
                "do":"login",
                "vb_login_md5password":md5,
                "vb_login_md5password_utf":md5
            }
            try:
                log = requests.post(self.login_url, data)
                if "vgmpassword" in log.cookies.keys():
                    self.cookies = log.cookies
                else:
                    self._log.error("VGMdb Login Failed! Are you sure you have to correct password?")
            except re_ex.RequestException as e:
                self._log.error(e)

    def clean_vgmdb_list(self):
        raise NotImplementedError

    def add_vgmdb_list(self, lib:Library, album:Album):
        # Check for data_source
        try:
            if album._types["data_source"] == self.data_source:
                if self.cookies is not None: # there is not check for cookies validity yet
                    forms = {
                        "formalbumids": album._fields["catalognum"], #alternatively : album._fields["id"]
                        "formfield":"cn", #using the catalog number, alternatively "id"
                        "formfolder":"0", # only on the base folder, can be an option
                        "action":"addalbum",
                        "add_album":"Add+Albums"
                    }
                    req = requests.post(self.add_url,forms, cookies=self.cookies)
        except re_ex.RequestException as e:
            self._log.exception("") # may do something else
        except Exception as e:
            self._log.exception("")

    def remove_vgmdb_list(self, album):
        try:
            if album._types["data_source"] == self.data_source:
                if self.cookies is not None:
                    id = f"album{album._fields['id']}"
                    forms = {
                        id:"1",
                        "action":"delete",
                        "formfpmder":"0",
                        "submit":"Submit"
                    }
                    req = requests.post(self.delete_url, forms, cookies=self.cookies)
        except re_ex.RequestException as e:
            self._log.error(e) # may do something else
        except Exception as e:
            self._log.error(e)

    def track_distance(self, item: Item, info: TrackInfo) -> Distance:
        """

        :param item:
        :param info:
        :return:
        """
        dist = Distance()

        if info.data_source == self.data_source:
            # check if there is many name, find the closed match
            min_dist = 1
            if "names" in info.keys():
                for name in info["names"].values():
                    name_dist = string_dist(item.title, name)
                    if name_dist<min_dist:
                        min_dist = name_dist
                dist.add("best_track_title", min_dist)
            dist.add("source",self.source_weight)
        return dist

    def album_distance(self, items: List[Item], album_info: AlbumInfo, mapping:Dict) -> Distance:
        """

        :param items:
        :param album_info:
        :param mapping:
        :return:
        """
        dist = Distance()
        if album_info.data_source == self.data_source:
            dist.add("source",self.source_weight)
        return dist

    def sanitize(self, title: str) -> str:
        """
        Clean text for VGMdb search as a simple date in the album title can negative positive result
        :param title:
        :return:
        """
        clean = re.sub(r'(?u)\W+', ' ', title)
        clean = re.sub(r'(?i)\b(CD|disc)\s*\d+', '', clean)
        self._log.debug(f"Title satinize: {title} -> {clean}")
        return clean

    def _search_vgmdbinfo(self, query:str):
        """
        VGMdb.info can only return Album level information as there are not track level information
        :param query:
        :return:
        """
        req = requests.get(f"{self.search_albums_url}{query}?format=json")
        items = req.json()
        albums = []
        for album in items["results"]["albums"]:
            album_id = album["link"].split("/")[1]
            albums.append(self._album_vgmdbinfo(album_id))
            if len(albums) >=10:
                self._log.info("Too many result on VGMDB, breaking")
                break
        return albums

    def _album_vgmdbinfo(self, id:int):
        """
        It does exactly what album for id does, we split into two since, there may be a need to implement an advanced search system (parsing for example date or artist in folder name)
        :param id:
        :return:
        """
        self._log.debug(f"Querying VgmDB for release {id}")
        req = requests.get(f"{self.album_url}{id}?format=json")
        url = f"{self.album_url}{id}"
        vgmdbinfo = req.json()
        return self.format_album_vgmdbinfo(vgmdbinfo, url=url)

    def format_album_vgmdbinfo(self,albuminfo:Dict, url:Optional[str]=None)->AlbumInfo:
        """

        :param albuminfo:
        :return:
        """
        
        optional_album = {}
        
        # Tracks Info
        tracks = []
        track_album_index = 0 # THIS IS BECAUSE TRACKS REQUIRE A MUSICBRAIN ID!
        for disc_index, disc in enumerate(albuminfo["discs"]):
            disc_length = disc["disc_length"]
            for track_index, track in enumerate(disc["tracks"]):
                optional_args = {}
                track_album_index +=1

                track_l = track["track_length"].split(":")
                if len(track_l)>0:
                    track_length = 60*int(track_l[0])+int(track_l[1])
                else:
                    track_length = None

                track_title = list(track["names"].values())[0]

                for lang in self.track_pref:
                    if lang in track["names"].keys():
                        track_title = track["names"][lang]
                        break
                optional_args.update({"names":track["names"]})
                tracks.append(TrackInfo(title=track_title,
                                        track_id=None, # Since we are not using musicbrainz
                                        release_track_id=None, # Not sure what this is
                                        artist=None,
                                        artist_id=None,
                                        length=float(track_length),
                                        index=track_album_index,
                                        medium=disc_index,
                                        medium_index=track_index,
                                        medium_total=len(disc["tracks"]),
                                        artist_sort=None,
                                        disctitle=disc["name"] if "name" in disc.keys() else None,
                                        artist_credit=None,
                                        data_source=self.data_source,
                                        data_url=url,
                                        media=None,
                                        lyricist=None,
                                        composer=None,
                                        composer_sort=None,
                                        arranger=None,
                                        track_alt=None,
                                        work=None,
                                        mb_workid=None,
                                        work_disambig=None,
                                        bpm=None,
                                        initial_key=None,
                                        genre=None,
                                        **optional_args))


        # Album Name
        album_name = albuminfo["name"]
        for lang in self.lang:
            if lang in albuminfo["names"].keys():
                album_name = albuminfo["names"][lang]
                break

        # Album VGMdb ID
        album_id = albuminfo["link"].split("/")[1]

        # Artist
        va = False
        artist_found = False
        if "performers" in albuminfo.keys():
            if len(albuminfo["performers"])>0:
                artist_found = True
                main_artist = albuminfo["performers"][0]["names"].items()[0]
                main_artist_id = albuminfo["performers"][0]["link"].split("/")[1] if "link" in albuminfo["performers"][0].keys() else None
                for lan in self.lang:
                    if lan in albuminfo["performers"][0]["names"]:
                        main_artist = albuminfo["performers"][0]["names"][lan]
                        break
                optional_album.update({"performers":albuminfo["performers"]})
            if len(albuminfo["performers"])>1:
                va = True

        if not artist_found:
            if len(albuminfo["composers"])>0:
                main_artist = list(albuminfo["composers"][0]["names"].values())[0]
                main_artist_id = albuminfo["composers"][0]["link"].split("/")[1] if "link" in albuminfo["composers"][
                    0].keys() else None
                for lan in self.lang:
                    if lan in albuminfo["composers"][0]["names"]:
                        main_artist = albuminfo["composers"][0]["names"][lan]
                        break
                optional_album.update({"composers": albuminfo["composers"]})
            else:
                main_artist=None,
                main_artist_id=None,
            if len(albuminfo["composers"])>1:
                va = True
        if "arrangers" in albuminfo.keys():
            optional_album.update({"arrangers": albuminfo["arrangers"]})

        # release date
        year, month, day = albuminfo["release_date"].split("-")

        # label
        publisher = list(albuminfo["publisher"]["names"].values())[0]
        for lang in self.lang:
            if lang in albuminfo["publisher"]["names"].keys():
                publisher = albuminfo["publisher"]["names"][lang]

        return AlbumInfo(tracks=tracks,
                         album=album_name,
                         album_id=album_id,
                         artist=main_artist,
                         artist_id=main_artist_id,
                         asin=None,
                         albumtype=None,
                         va=va,
                         year=int(year),
                         month=int(month),
                         day=int(day),
                         label=publisher,
                         mediums=len(albuminfo["discs"]),
                         artist_sort=None,
                         releasegroup_id=None,
                         catalognum=albuminfo["catalog"],
                         script=None,
                         language=None,
                         country=None,
                         style=None,
                         genre=albuminfo["category"],
                         albumstatus=None,
                         media=albuminfo["media_format"],
                         albumdisambig=None,
                         releasegroupdisambig=None,
                         artist_credit=None,
                         original_year=None,
                         original_month=None,
                         original_day=None,
                         data_source=self.data_source,
                         data_url=albuminfo["vgmdb_link"],
                         **optional_album
                         )


    def candidates(self, items: List[str], artist: str, album: str, va_likely: bool, extra_tags=None) -> Sequence[
        AlbumInfo]:
        """
        Given
        :param items:
        :param artist:
        :param album:
        :param va_likely: Various Artist Likely
        :param extra_tags:
        :return:
        """
        self._log.debug(f"Searching for candidate in VGMdb for {album}")
        cleaned_album = self.sanitize(album)
        cleaned_artist = self.sanitize(artist)
        if va_likely:
            query = cleaned_album  # also the name of the folder
        else:
            query = f"{cleaned_artist} {cleaned_album}"
        try:
            return self._search_vgmdbinfo(query)
        except Exception as e:
            self._log.exception("")
            return []

    def album_for_id(self, album_id:int) -> Optional[AlbumInfo]:
        """

        :param album_id:
        :return:
        """
        try:
            return self._album_vgmdbinfo(album_id)
        except Exception as e:
            self._log.exception("")
            return None

    # def _search_api(self, query_type, filters, keywords=''):
    #     pass
