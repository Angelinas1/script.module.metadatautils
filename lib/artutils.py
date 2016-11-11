#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.module.artutils
    Provides all kind of mediainfo for kodi media, returned as dict with details
'''

from helpers.animatedart import AnimatedArt
from helpers.tmdb import Tmdb
from helpers.omdb import Omdb
from helpers.imdb import Imdb
from helpers.google import GoogleImages
from helpers.channellogos import ChannelLogos
from helpers.fanarttv import FanartTv
from helpers.kodidb import KodiDb
import helpers.kodi_constants as kodi_constants
from helpers.pvrartwork import PvrArtwork
from helpers.studiologos import StudioLogos
from helpers.musicartwork import MusicArtwork
from helpers.utils import log_msg, get_duration, log_exception, ADDON_ID
from helpers.utils import extend_dict, get_clean_image, process_method_on_list, detect_plugin_content
from simplecache import use_cache, SimpleCache
from thetvdb import TheTvDb
import xbmc
import xbmcaddon
import xbmcvfs
import datetime
import os


class ArtUtils(object):
    '''
        Provides all kind of mediainfo for kodi media, returned as dict with details
    '''

    # path to use to lookup studio logos, must be set by the calling addon
    studiologos_path = ""

    def __init__(self):
        '''Initialize and load all our helpers'''
        self.studiologos_path = ""
        self.cache = SimpleCache()
        self.addon = xbmcaddon.Addon(ADDON_ID)
        self.kodidb = KodiDb()
        self.omdb = Omdb(self.cache)
        self.tmdb = Tmdb(self.cache)
        self.channellogos = ChannelLogos(self.kodidb)
        self.fanarttv = FanartTv(self.cache)
        self.imdb = Imdb(self.cache)
        self.google = GoogleImages(self.cache)
        self.studiologos = StudioLogos(self.cache)
        self.animatedart = AnimatedArt(self.cache, self.kodidb)
        self.thetvdb = TheTvDb()
        self.musicart = MusicArtwork(self)
        self.pvrart = PvrArtwork(self)
        log_msg("Initialized")

    def close(self):
        '''Cleanup Kodi Cpython instances'''
        self.cache.close()
        del self.addon
        log_msg("Exited")

    @use_cache(14, True)
    def get_extrafanart(self, file_path, media_type):
        '''helper to retrieve the extrafanart path for a kodi media item'''
        from helpers.extrafanart import get_extrafanart
        return get_extrafanart(file_path, media_type)

    def get_music_artwork(self, artist="", album="", track="", disc="", ignore_cache=False):
        '''method to get music artwork for the goven artist/album/song'''
        result = self.musicart.get_music_artwork(
            artist, album, track, disc, ignore_cache=ignore_cache)
        log_msg(
            "get_music_artwork --> artist: %s - album: %s - track: %s --- result: %s" %
            (artist, album, track, result))
        return result

    def music_artwork_options(self, artist="", album="", track="", disc=""):
        '''options for music metadata for specific item'''
        return self.musicart.music_artwork_options(artist, album, track, disc)

    @use_cache(14, True)
    def get_extended_artwork(self, imdb_id="", tvdb_id="", media_type=""):
        '''get extended artwork for the given imdbid or tvdbid'''
        result = {}
        if "movie" in media_type and imdb_id:
            result["art"] = self.fanarttv.movie(imdb_id)
        elif media_type in ["tvshow", "tvshows", "seasons", "episodes"]:
            if not tvdb_id:
                if imdb_id and not imdb_id.startswith("tt"):
                    tvdb_id = imdb_id
                elif imdb_id:
                    tvdb_id = self.thetvdb.get_series_by_imdb_id(imdb_id).get("tvdb_id")
            if tvdb_id:
                result["art"] = self.fanarttv.tvshow(tvdb_id)
        return result

    @use_cache(14, True)
    def get_tmdb_details(
            self,
            imdb_id="",
            tvdb_id="",
            title="",
            year="",
            media_type="",
            manual_select=False,
            preftype=""):
        '''returns details from tmdb'''
        result = {}
        title = title.split(" (")[0]
        if imdb_id:
            result = self.tmdb.get_video_details_by_external_id(
                imdb_id, "imdb_id")
        elif tvdb_id:
            result = self.tmdb.get_video_details_by_external_id(
                tvdb_id, "tvdb_id")
        elif title and media_type in ["movies", "setmovies", "movie"]:
            result = self.tmdb.search_movie(
                title, year, manual_select=manual_select)
        elif title and media_type in ["tvshows", "tvshow"]:
            result = self.tmdb.search_tvshow(
                title, year, manual_select=manual_select)
        elif title:
            result = self.tmdb.search_video(
                title, year, preftype=preftype, manual_select=manual_select)
        if result.get("status"):
            result["status"] = self.translate_string(result["status"])
        if result.get("runtime"):
            result["runtime"] = result["runtime"] / 60
            result.update(get_duration(result["runtime"]))
        return result

    def get_moviesetdetails(self, set_id):
        '''get a nicely formatted dict of the movieset details which we can for example set as window props'''
        from helpers.moviesetdetails import get_moviesetdetails
        return get_moviesetdetails(
            self.cache,
            self.kodidb,
            set_id,
            self.studiologos,
            self.studiologos_path)

    @use_cache(14, True)
    def get_streamdetails(self, db_id, media_type, ignore_cache=False):
        '''get a nicely formatted dict of the streamdetails '''
        from helpers.streamdetails import get_streamdetails
        return get_streamdetails(self.kodidb, db_id, media_type)

    def get_pvr_artwork(
            self,
            title,
            channel="",
            genre="",
            manual_select=False,
            ignore_cache=False):
        '''get artwork and mediadetails for PVR entries'''
        return self.pvrart.get_pvr_artwork(
            title,
            channel,
            genre,
            manual_select=manual_select,
            ignore_cache=ignore_cache)

    def pvr_artwork_options(self, title, channel="", genre=""):
        '''options for pvr metadata for specific item'''
        return self.pvrart.pvr_artwork_options(title, channel, genre)

    @use_cache(14, True)
    def get_channellogo(self, channelname):
        '''get channellogo from the given channel name'''
        return self.channellogos.get_channellogo(channelname)

    def get_studio_logo(self, studio):
        '''get studio logo for the given studio'''
        # dont use cache at this level because of changing logospath
        return self.studiologos.get_studio_logo(studio, self.studiologos_path)

    @property
    def studiologos_path(self):
        '''path to use to lookup studio logos, must be set by the calling addon'''
        return self._studiologos_path

    @studiologos_path.setter
    def studiologos_path(self, value):
        '''path to use to lookup studio logos, must be set by the calling addon'''
        self._studiologos_path = value

    @use_cache(1, False)
    def get_animated_artwork(
            self,
            imdb_id,
            ignore_cache=False,
            manual_select=False):
        '''get animated artwork, perform extra check if local version still exists'''
        artwork = self.animatedart.get_animated_artwork(
            imdb_id, manual_select, ignore_cache=ignore_cache)
        refresh_needed = False
        if artwork.get("animatedposter") and not xbmcvfs.exists(
                artwork["animatedposter"]):
            refresh_needed = True
        if artwork.get("animatedfanart") and not xbmcvfs.exists(
                artwork["animatedfanart"]):
            refresh_needed = True
        if refresh_needed:
            artwork = self.animatedart.get_animated_artwork(
                imdb_id, manual_select, ignore_cache=True)
        return artwork

    @use_cache(14, True)
    def get_omdb_info(self, imdb_id, title="", year="", content_type=""):
        title = title.split(" (")[0]  # strip year appended to title
        result = {}
        if imdb_id:
            result = self.omdb.get_details_by_imdbid(imdb_id)
        elif title and content_type in ["seasons", "season", "episodes", "episode", "tvshows", "tvshow"]:
            result = self.omdb.get_details_by_title(title, "", "tvshows")
        elif title and year:
            result = self.omdb.get_details_by_title(title, year, content_type)
        if result.get("status"):
            result["status"] = self.translate_string(result["status"])
        if result.get("runtime"):
            result["runtime"] = result["runtime"] / 60
            result.update(get_duration(result["runtime"]))
        return result

    @use_cache(7, True)
    def get_top250_rating(self, imdb_id):
        '''get the position in the IMDB top250 for the given IMDB ID'''
        return self.imdb.get_top250_rating(imdb_id)

    @use_cache(7, True)
    def get_duration(self, duration):
        '''helper to get a formatted duration'''
        if ":" in duration:
            dur_lst = duration.split(":")
            return {
                "Duration": "%s:%s" % (dur_lst[0], dur_lst[1]),
                "Duration.Hours": dur_lst[0],
                "Duration.Minutes": dur_lst[1],
                "Runtime": str((int(dur_lst[0]) * 60) + dur_lst[1]),
            }
        else:
            return get_duration(duration)

    @use_cache(1, True)
    def get_tvdb_details(self, imdbid="", tvdbid=""):
        '''get metadata from tvdb by providing a tvdbid or tmdbid'''
        result = {}
        self.thetvdb.days_ahead = 365
        if not tvdbid and imdbid and not imdbid.startswith("tt"):
            # assume imdbid is actually a tvdbid...
            tvdbid = imdbid
        if tvdbid:
            result = self.thetvdb.get_series(tvdbid)
        elif imdbid:
            result = self.thetvdb.get_series_by_imdb_id(imdbid)
        if result:
            if result["status"] == "Continuing":
                # include next episode info
                result["nextepisode"] = self.thetvdb.get_nextaired_episode(result["tvdb_id"])
            # include last episode info
            result["lastepisode"] = self.thetvdb.get_last_episode_for_series(result["tvdb_id"])
            result["status"] = self.translate_string(result["status"])
            if result.get("runtime"):
                result["runtime"] = result["runtime"] / 60
                result.update(get_duration(result["runtime"]))
        return result

    def translate_string(self, _str):
        '''translate the received english string from the various sources like tvdb, tmbd etc'''
        translation = _str
        _str = _str.lower()
        if "continuing" in _str:
            translation = self.addon.getLocalizedString(32037)
        elif "ended" in _str:
            translation = self.addon.getLocalizedString(32038)
        elif "released" in _str:
            translation = self.addon.getLocalizedString(32040)
        return translation
