from typing import Union, List

import hashlib
import requests
import requests.exceptions

from bs4 import BeautifulSoup
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand


class LoginError(Exception):
    pass


class VGMdbCollection(BeetsPlugin):
    login_url = "https://vgmdb.net/forums/login.php"
    add_url = "https://vgmdb.net/db/collection.php?do=add"
    delete_url = "https://vgmdb.net/db/collection.php?do=manage&type=albums"
    collection_view = "https://vgmdb.net/db/collection.php?do=view"

    # OTHER CONFIG CONSTANT
    album_catalog_number = "cn"
    album_id = "id"
    default_folder = "root"
    data_source = "VGMdb"

    def __init__(self) -> None:
        super(VGMdbCollection, self).__init__()

        self.config.add(
            {
                "on_import": True,
                "on_remove": False,
                "folder_name": self.default_folder,
                "username": None,
                "password": None,
            }
        )
        self.config["username"].redact = True
        self.config["password"].redact = True

        self._collection_cache = None
        self.session = requests.session()
        self.update_cookies()
        self.sanitize_folder()

        if self.config["on_import"].get():
            self.register_listener("album_imported", self.album_imported)
        if self.config["on_remove"].get():
            self.register_listener("album_remove", self.album_removed)
        self._collections_cache = []

    def album_imported(self, lib, album):
        albums = self._get_albums_in_collection()
        if album.catalognum not in [al["catalog_number"] for al in albums]:
            self.add_album(album.catalognum, self.album_catalog_number)

    def album_removed(self, lib, album):
        albums = self._get_albums_in_collection()
        for al in albums:
            if al["catalog_number"] == album.catalognum:
                self.remove_album(al["collection_ref"])

    def sanitize_folder(self):
        self.folder_id = None
        if self.config["folder_name"].get() == self.default_folder:
            self.folder_id = "0"
        else:
            self._collections_cache = self._get_collections()
            self.update_folder_id()
            if self.folder_id is None:
                self._create_collection(self.config["folder_name"].get())
                self._collections_cache = self._get_collections()
                self.update_folder_id()
                assert self.folder_id is not None

    def update_folder_id(self):
        for collection_name, collection_id in self._collections_cache:
            if collection_name == self.config["folder_name"].get():
                self.folder_id = collection_id

    def _create_collection(self, collection_name):
        forms = {
            "formfoldername": collection_name,
            "formfolder": "0",
            "action": "addfolder",
            "add_folder": "Add+Folders",
        }
        self.session.post(self.add_url, forms, cookies=self.session.cookies)

    def _get_collections(self):
        collection_request = self.session.get(self.collection_view, cookies=self.session.cookies)
        soup = BeautifulSoup(collection_request.text, "lxml")
        mycollection = soup.find("ul", {"class": "treeview"})
        listofCollection = []
        if mycollection is not None:
            for collection in mycollection.find_all("li", {"class": "submenu"}):
                collection_name = collection.next_element.strip()
                collection_id = collection["ref"]
                listofCollection.append((collection_name, collection_id))
        return listofCollection

    def format_album(self, album_soup):
        title = album_soup.find("a")["title"]
        vgmdb_id = album_soup.find("a")["href"].split("/")[-1]
        catalog_number = album_soup.find("span", {"class": "catalog"}).next_element
        return title, vgmdb_id, catalog_number, album_soup["ref"]

    def _get_albums_in_collection(self):
        collection_request = self.session.get(self.collection_view, cookies=self.session.cookies)
        soup = BeautifulSoup(collection_request.text, "lxml")
        mycollection = soup.find("ul", {"class": "treeview"})
        myalbums = []
        for collection_name, collection_id in self._collections_cache:
            collection_soup = mycollection.find("li", {"ref": collection_id})
            for album_soup in collection_soup.find_all("li"):
                title, vgmdb_id, catalog_number, collection_ref = self.format_album(album_soup)
                myalbums.append(
                    {
                        "title": title,
                        "vgmdb_id": vgmdb_id,
                        "catalog_number": catalog_number,
                        "collection_id": collection_id,
                        "collection_ref": collection_ref,
                    }
                )
        # root album
        if mycollection is not None:
            for album_soup in mycollection.findChildren("li", {"class": None}, recursive=False):
                title, vgmdb_id, catalog_number, collection_ref = self.format_album(album_soup)
                myalbums.append(
                    {
                        "title": title,
                        "vgmdb_id": vgmdb_id,
                        "catalog_number": catalog_number,
                        "collection_id": "0",
                        "collection_ref": collection_ref,
                    }
                )
        return myalbums

    def commands(self):
        mbupdate = Subcommand("vgmdbupdate", help="Update VGMdb collection")
        mbupdate.parser.add_option(
            "-r",
            "--remove",
            action="store_true",
            default=None,
            dest="remove",
            help="Remove albums not in beets library",
        )
        mbupdate.func = self.update_collection
        return [mbupdate]

    def update_collection(self, lib, opts, args):
        self.config.set_args(opts)
        remove_missing = self.config["on_remove"].get(bool)
        self.update_album_list(lib, lib.albums(), remove_missing)
        self._log.info("Finished updating vgmdb collection")

    def update_album_list(self, lib, album_list, remove_missing=False):
        vgm_albums = self._get_albums_in_collection()

        album_catalogs = []
        for album in album_list:
            album_catalogs.append(album["catalognum"])

        to_add = [
            catalog
            for catalog in album_catalogs
            if catalog not in [al["catalog_number"] for al in vgm_albums]
        ]
        self.add_album(to_add, self.album_catalog_number)

        if remove_missing:
            to_remove = [
                al["collection_ref"]
                for al in vgm_albums
                if al["catalog_number"] not in album_catalogs
            ]
            self.remove_album(to_remove)

    def update_cookies(self) -> None:
        """

        :param task:
        :param session:
        :return:
        """
        if (self.config["username"].get() is not None) and (
            self.config["password"].get() is not None
        ):
            hash = hashlib.md5(self.config["password"].get().encode())
            md5 = hash.hexdigest()
            data = {
                "vb_login_username": self.config["username"].get(),
                "cookieuser": "1",
                "securitytoken": "guest",
                "do": "login",
                "vb_login_md5password": md5,
                "vb_login_md5password_utf": md5,
            }
            try:
                self.session.post(self.login_url, data)
                if "vgmpassword" not in self.session.cookies.keys():
                    self._log.error(
                        "VGMdb Login Failed! Are you sure you have to correct password?"
                    )
                    raise LoginError
                else:
                    self._log.info("Successfully logged into VGMdb")
            except requests.exceptions.RequestException as e:
                self._log.exception(e)
        else:
            raise LoginError

    def add_album(self, catalog_or_id: Union[str, List[str]], nb_type: str) -> None:
        """

        :param catalog_or_id:
        :param nb_type:
        :return:
        """
        if isinstance(catalog_or_id, str):
            post = catalog_or_id
        else:
            post = "\r\n".join(catalog_or_id)

        forms = {
            "formalbumids": post,
            "formfolder": self.folder_id,
            "action": "addalbum",
            "add_album": "Add+Albums",
        }
        if nb_type == self.album_catalog_number:
            forms.update({"formfield": self.album_catalog_number})
        else:
            forms.update({"formfield": self.album_id})
        self.session.post(self.add_url, forms, cookies=self.session.cookies)

    def remove_album(self, albums_ref: Union[str, List[str]]):
        forms = {"action": "delete", "submit": "Submit"}

        if isinstance(albums_ref, str):
            forms.update({f"album[{albums_ref}]": "1"})
        else:
            forms.update({f"album[{album}]": "1" for album in albums_ref})

        self.session.post(self.delete_url, forms, cookies=self.session.cookies)
