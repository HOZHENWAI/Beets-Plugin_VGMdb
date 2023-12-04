from typing import Dict, List, Sequence, Optional, Iterable
import requests
import requests.exceptions
import re

from beets.plugins import BeetsPlugin
from beets.autotag.hooks import AlbumInfo, TrackInfo, Distance, string_dist
from beets.ui.commands import PromptChoice, input_
from beets.autotag.match import Proposal, _add_candidate, _recommendation

TRACK_NAME_CONVENTION = {"en": "English", "ja-latn": "Romaji", "ja": "Japanese"}


class VGMdbPlugin(BeetsPlugin):
    data_source = "VGMdb"  # MetadataSourcePlugin

    search_url = "https://vgmdb.info/search/"
    search_albums_url = "https://vgmdb.info/search/albums/"
    album_url = "https://vgmdb.info/album/"

    def __init__(self):
        super(VGMdbPlugin, self).__init__()
        self._log.setLevel("ERROR")
        self.config.add({"lang-priority": "en,ja-latn,ja", "source_weight": 0.0})

        self.config.add({"artist-priority": "composers,performers,arrangers"})
        self.artist_priority = self.config["artist-priority"].get().replace(" ", "").split(",")
        self.source_weight = self.config["source_weight"].as_number()
        self.lang = self.config["lang-priority"].get().replace(" ", "").split(",")
        self.track_pref = [TRACK_NAME_CONVENTION[lang] for lang in self.lang]
        self.register_listener("before_choose_candidate", self.before_choose_candidate_event)

    def before_choose_candidate_event(self, session, task):
        if task.is_album:
            return [
                PromptChoice("v", "type Vgmdb id", self.insert_manual_id),
                PromptChoice("q", "type vgmdb Query", self.custom_query),
            ]

    def parse_vgmdbinfo_artist(self, albuminfo, key, optional_album):
        self._log.info(f"Completing artist info using {key}")
        artist_found = False
        va = False
        if len(albuminfo[key]) > 0:
            self._log.info(f"Found {len(albuminfo[key])} {key}")
            artist_found = True
            main_artist = list(albuminfo[key][0]["names"].values())[0]
            main_artist_id = (
                albuminfo[key][0]["link"].split("/")[1]
                if "link" in albuminfo[key][0].keys()
                else None
            )
            for lan in self.lang:
                if lan in albuminfo[key][0]["names"]:
                    main_artist = albuminfo[key][0]["names"][lan]
                    self._log.info(f"Final artist choice is {main_artist}")
                    break
            optional_album.update(self.format_list_of_person(albuminfo[key], key))
        else:
            main_artist = ""
            main_artist_id = None
        if len(albuminfo["composers"]) > 1:
            va = True
        return artist_found, main_artist, main_artist_id, va

    def insert_manual_id(self, session, task):
        """Get a new `Proposal` using a manually-entered ID.

        Input an ID, either for an album ("release") or a track ("recording").
        """
        prompt = "Enter {} ID:".format("release" if task.is_album else "recording")
        search_id = input_(prompt).strip()

        candidates = {}

        custom_album = self.album_for_id(search_id)
        if custom_album is not None:
            _add_candidate(task.items, candidates, custom_album)
            rec = _recommendation(list(candidates.values()))
            return Proposal(list(candidates.values()), rec)
        else:
            self._log.error(f"Asking a manual id that has issues. {search_id}")
            return None

    def custom_query(self, session, task):
        """Get a new `Proposal` using a manually-entered ID.

        Input an ID, either for an album ("release") or a track ("recording").
        """
        prompt = "Enter {} query:".format("release" if task.is_album else "recording")
        query = input_(prompt).strip()

        query_results = self._search_vgmdbinfo(query)
        candidates = {}
        if len(query_results)>0:
            self._log.info(f'Found {len(query_results)} result for the query.'
                           f' Selecting the first choice.')
            _add_candidate(
                task.items, candidates, query_results[0]
            )  # TODO add error handling
            rec = _recommendation(list(candidates.values()))

            return Proposal(list(candidates.values()), rec)
        else:
            self._log.warning(f"No query result for {query}")
            return None

    def track_distance(self, item, info: TrackInfo) -> Distance:
        """

        :param item:
        :param info:
        :return:
        """
        dist = Distance()

        if info.data_source == self.data_source:
            min_dist = 1
            for key in info.keys():
                if key.startswith("vgmdb_track_name"):
                    name_dist = string_dist(item.title, info[key])
                    if name_dist < min_dist:
                        min_dist = name_dist
            dist.add("track_title", min_dist)
            dist.add("source", self.source_weight)
        return dist

    def album_distance(self, items: List, album_info: AlbumInfo, mapping: Dict) -> Distance:
        """

        :param items:
        :param album_info:
        :param mapping:
        :return:
        """
        dist = Distance()
        if album_info.data_source == self.data_source:
            dist.add("source", self.source_weight)
        return dist

    def _search_vgmdbinfo(self, query: str):
        """
        VGMdb.info can only return Album level information as there are not track level information
        :param query:
        :return:
        """
        try:
            req = requests.get(f"{self.search_albums_url}{query}?format=json")
            items = req.json()
            albums = []
            self._log.debug(
                f"Found {len(items['results']['albums'])} albums on VGMdb for query: {query}"
            )
            for album in items["results"]["albums"]:
                album_id = album["link"].split("/")[1]
                candidate_album = self.album_for_id(album_id)
                if candidate_album is not None:
                    albums.append(candidate_album)
                if len(albums) >= 5:
                    self._log.debug("Too many result on VGMDB, breaking")
                    break
            return albums
        except requests.exceptions.RequestException as e:
            self._log.error(f"Network Exception: {query}")
        except requests.exceptions.ChunkedEncodingError:
            self._log.error(f"Chunked Encoding Exception: {query}")
        except requests.exceptions.JSONDecodeError:
            self._log.error(f"Json Decode Error: {query}")
        return []

    def _format_track_info(self, albuminfo, url):
        tracks = []
        track_album_index = 0
        for disc_index, disc in enumerate(albuminfo["discs"]):
            disc_length = disc["disc_length"]
            for track_index, track in enumerate(disc["tracks"]):
                optional_args = {}
                track_album_index += 1

                track_l = track["track_length"].split(":")
                if (len(track_l) > 0) & (track_l[0] != "Unknown"):
                    track_length = 60 * int(track_l[0]) + int(track_l[1])
                else:
                    track_length = None

                track_title = list(track["names"].values())[0]

                for lang in self.track_pref:
                    if lang in track["names"].keys():
                        track_title = track["names"][lang]
                        break
                for lang in track["names"].keys():
                    optional_args.update({f"vgmdb_track_name_{lang}": track["names"][lang]})

                tracks.append(
                    TrackInfo(
                        title=track_title,
                        track_id=None,
                        release_track_id=None,
                        artist=None,
                        artist_id=None,
                        length=float(track_length) if track_length is not None else None,
                        index=track_album_index,
                        medium=disc_index + 1,
                        medium_index=track_index + 1,
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
                        **optional_args,
                    )
                )
        return tracks

    def format_list_of_person(self, listofVGMPerson: List, typeofPerson: str):
        out = {}
        if len(listofVGMPerson) > 0:
            if "names" in listofVGMPerson[0].keys():
                for lang in listofVGMPerson[0]["names"].keys():
                    out[f"{typeofPerson}_{lang}"] = ",".join(
                        [
                            person["names"][lang]
                            for person in listofVGMPerson
                            if lang in person["names"].keys()
                        ]
                    )
        return out

    def format_album_vgmdbinfo(self, albuminfo: Dict, url: Optional[str] = None) -> AlbumInfo:
        """

        :param albuminfo:
        :return:
        """

        main_artist = ""
        main_artist_id = None
        va = False
        optional_album = {}
        tracks = self._format_track_info(albuminfo, url)

        # Album Name
        album_name = albuminfo["name"]
        for lang in self.lang:
            if lang in albuminfo["names"].keys():
                album_name = albuminfo["names"][lang]
                break

        # Album VGMdb ID
        album_id = albuminfo["link"].split("/")[1]
        optional_album.update({"vgmdb_id": album_id})

        # Artist
        for key in self.artist_priority:
            artist_found, main_artist, main_artist_id, va = self.parse_vgmdbinfo_artist(
                albuminfo, key, optional_album
            )
            if artist_found:
                break

        # release date
        date = albuminfo["release_date"].split("-")
        if len(date) == 3:
            year, month, day = date
            year = int(year)
            month = int(month)
            day = int(day)
        else:
            year = None
            month = None
            day = None

        # label
        publisher = (
            list(albuminfo["publisher"]["names"].values())[0]
            if len(albuminfo["publisher"]["names"]) > 0
            else None
        )
        for lang in self.lang:
            if lang in albuminfo["publisher"]["names"].keys():
                publisher = albuminfo["publisher"]["names"][lang]

        return AlbumInfo(
            tracks=tracks,
            album=album_name,
            album_id=f"vgmdb-{album_id}",
            artist=main_artist,
            artist_id=main_artist_id,
            asin=None,
            albumtype=albuminfo.get("classification", None),
            va=va,
            year=year,
            month=month,
            day=day,
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
            **optional_album,
        )

    def sanitize(self, title: str) -> str:
        """
        Clean text for VGMdb search as a simple date in the album title can negative positive result
        :param title:
        :return:
        """
        clean = re.sub(r"(?u)\W+", " ", title)
        clean = re.sub(r"(?i)\b(CD|disc)\s*\d+", "", clean)
        self._log.debug(f"Title satinize: {title} -> {clean}")
        return clean

    def candidates(
        self,
        items: List[str],
        artist: str,
        album: str,
        va_likely: bool,
        extra_tags=None,
    ) -> Sequence[AlbumInfo]:
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
        albums = []
        queries = self._format_query(artist, album, va_likely)

        for query in queries:
            albums += self._search_vgmdbinfo(query)
        return albums

    def _format_query(self, artist, album, va_likely) -> Iterable:
        """

        :param artist:
        :param album:
        :param va_likely:
        :return:
        """
        return [self.sanitize(text) for text in album.split(" -") if len(self.sanitize(text)) > 0]

    def album_for_id(self, album_id: int) -> Optional[AlbumInfo]:
        """
        Take a VGMdb id and return an AlbumInfo object
        :param album_id: the album id in vgmdb
        :return: an albuminfo object
        """
        self._log.debug(f"Querying VgmDB for release {album_id}")
        try:
            req = requests.get(f"{self.album_url}{album_id}?format=json")
            url = f"{self.album_url}{album_id}"
            vgmdbinfo = req.json()
            return self.format_album_vgmdbinfo(vgmdbinfo, url=url)
        except requests.exceptions.RequestException:
            self._log.error(f"Network Problem: {album_id}")
        except requests.exceptions.JSONDecodeError:
            self._log.error(f"JsonDecodeError: {album_id}")
        return None
