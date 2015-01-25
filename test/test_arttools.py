# This file is part of beets.
# Copyright 2015, Malte Ried
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

import os
import shutil
from PIL import Image

from beets import config, util
import beetsplug

from test import _common
from test.helper import TestHelper, capture_log

RSRC = os.path.join(os.path.dirname(__file__), 'rsrc')


class ArtToolsPluginTest(_common.TestCase, TestHelper):
    """ Test the arttools plugin
    """

    @classmethod
    def setUpClass(cls):
        config['pluginpath'] = [os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "..", "beetsplug")]
        beetsplug.__path__ = config['pluginpath'].get() + beetsplug.__path__

    def setUp(self):
        self.setup_beets()
        self.load_plugins('arttools')

    def tearDown(self):
        self.unload_plugins()
        self.teardown_beets()

    def __create_album(self, artist='Artist', album='Album', art_width=None,
                       art_height=None):
        album = self.add_album(albumartist=artist, artist=artist, album=album)
        src = os.path.join(_common.RSRC, 'full.mp3')
        for item in album.items():
            item.path = src
            item.move(copy=True)
            item.store()
        if art_width and art_height:
            art_filename = '{0}x{1}.png'.format(art_width, art_height)
            album.set_art(os.path.join(RSRC, art_filename), copy=True)
            album['art_width'] = art_width
            album['art_height'] = art_height
            album.store()
        return album

    def __copy_art_to_album(self, art_width, art_height, album, dest_filename):
        art_filename = '{0}x{1}.png'.format(art_width, art_height)
        dest_path = os.path.join(album.path, dest_filename)
        shutil.copy(os.path.join(RSRC, art_filename), dest_path)

        return dest_path

    def assertSize(self, image_path, width, height):
        im = Image.open(util.syspath(image_path))
        self.assertEqual(im.size, (width, height))

    def test_list_no_art(self):
        self.__create_album('No Art', 'Nil')

        with capture_log('beets.arttools') as logs:
            self.run_command('listboundart')
        self.assertEqual(logs, [])

    def test_list_bound_art(self):
        albums = []
        self.__create_album('No Art', 'Nil')
        albums.append(self.__create_album('Good Art', 'Small', 200, 200))
        albums.append(self.__create_album('Good Art', 'Medium', 300, 300))

        with capture_log('beets.arttools') as logs:
            self.run_command('listboundart')
        expected = sorted(['arttools: ' + util.displayable_path(album.artpath)
                           for album in albums])
        self.assertEqual(logs, expected)

        with capture_log('beets.arttools') as logs:
            self.run_command('listboundart', 'Not there')
        self.assertEqual(logs, [])

        with capture_log('beets.arttools') as logs:
            self.run_command('listboundart', 'Small')
        expected = ['arttools: ' + util.displayable_path(albums[0].artpath)]
        self.assertEqual(logs, expected)

    def test_list_bad_bound_art(self):
        albums = []
        self.__create_album('No Art', 'Nil')
        self.__create_album('Good Art', 'Small', 200, 200)
        self.__create_album('Good Art', 'Medium', 300, 300)
        self.__create_album('Good Art', 'Non Square', 250, 240)
        albums.append(self.__create_album('Bad Art', 'Tiny', 100, 100))
        albums.append(
            self.__create_album('Bad Art', 'Small Aspect V', 100, 150))
        albums.append(
            self.__create_album('Bad Art', 'Small Aspect H', 150, 100))
        albums.append(
            self.__create_album('Bad Art', 'Medium Aspect V', 200, 300))
        albums.append(
            self.__create_album('Bad Art', 'Medium Aspect H', 300, 200))

        with capture_log('beets.arttools') as logs:
            self.run_command('listbadboundart')
        expected = sorted(['arttools: {0} ({1} x {2}) AR:{3:.4}'.format(
            util.displayable_path(album.artpath),
            album.art_width,
            album.art_height,
            float(album.art_width) / float(album.art_height)
            if float(album.art_width) < float(album.art_height)
            else float(album.art_height) / float(album.art_width)
        ) for album in albums])
        expected = ['arttools: Art is bad if its aspect ratio is < 0.8 or '
                    'either width or height is < 200'] + expected
        self.assertEqual(logs, expected)

        with capture_log('beets.arttools') as logs:
            self.run_command('listbadboundart', 'Not there')
        expected = ['arttools: Art is bad if its aspect ratio is < 0.8 or '
                    'either width or height is < 200']
        self.assertEqual(logs, expected)

        with capture_log('beets.arttools') as logs:
            self.run_command('listbadboundart', 'Tiny')
        expected = ['arttools: {0} ({1} x {2}) AR:{3:.4}'.format(
            util.displayable_path(albums[0].artpath),
            albums[0].art_width,
            albums[0].art_height,
            float(albums[0].art_width) / float(albums[0].art_height)
            if float(albums[0].art_width) < float(albums[0].art_height)
            else float(albums[0].art_height) / float(albums[0].art_width)
        )]
        expected = ['arttools: Art is bad if its aspect ratio is < 0.8 or '
                    'either width or height is < 200'] + expected
        self.assertEqual(logs, expected)

    def test_list_art(self):
        config['arttools']['names'] = ['cover', 'extracted']

        paths = []
        album = self.__create_album()
        paths += [self.__copy_art_to_album(200, 200, album, 'cover.png')]
        paths += [self.__copy_art_to_album(300, 300, album, 'extracted.png')]
        self.__copy_art_to_album(250, 240, album, 'dummy.png')
        album2 = self.__create_album('ArtistB', 'AlbumB')
        paths += [self.__copy_art_to_album(200, 200, album2, 'cover.png')]
        paths += [self.__copy_art_to_album(300, 300, album2, 'extracted.png')]
        self.__copy_art_to_album(250, 240, album2, 'dummy.png')

        with capture_log('beets.arttools') as logs:
            self.run_command('listart')
        expected = ['arttools: ' + util.displayable_path(path) for path in
                    sorted(paths)]
        self.assertEqual(sorted(logs), expected)

        with capture_log('beets.arttools') as logs:
            self.run_command('listart', 'Not there')
        self.assertEqual(logs, [])

        with capture_log('beets.arttools') as logs:
            self.run_command('listart', 'AlbumB')
        expected = ['arttools: ' + util.displayable_path(path) for path in
                    sorted(paths[2:])]
        self.assertEqual(sorted(logs), expected)

    def test_list_art_verbose(self):
        config['arttools']['names'] = ['cover', 'extracted']

        paths = []
        album = self.__create_album()
        paths += [self.__copy_art_to_album(200, 200, album, 'cover.png') +
                  ' (200 x 200) AR:1.0']
        paths += [self.__copy_art_to_album(250, 240, album, 'extracted.png') +
                  ' (250 x 240) AR:0.96']
        self.__copy_art_to_album(300, 300, album, 'dummy.png')
        album2 = self.__create_album('ArtistB', 'AlbumB')
        paths += [self.__copy_art_to_album(200, 200, album2, 'cover.png') +
                  ' (200 x 200) AR:1.0']
        paths += [self.__copy_art_to_album(250, 240, album2, 'extracted.png') +
                  ' (250 x 240) AR:0.96']
        self.__copy_art_to_album(250, 240, album2, 'dummy.png')

        with capture_log('beets.arttools') as logs:
            self.run_command('listart', '-v')
        expected = ['arttools: ' + util.displayable_path(path) for path in
                    sorted(paths)]
        self.assertEqual(sorted(logs), expected)

        with capture_log('beets.arttools') as logs:
            self.run_command('listart', '-v', 'Not there')
        self.assertEqual(logs, [])

        with capture_log('beets.arttools') as logs:
            self.run_command('listart', '-v', 'AlbumB')
        expected = ['arttools: ' + util.displayable_path(path) for path in
                    sorted(paths[2:])]
        self.assertEqual(sorted(logs), expected)

    def test_copy_bound_art(self):
        albums = []
        self.__create_album('No Art', 'Nil')
        albums.append(self.__create_album('Good Art', 'Small', 200, 200))
        albums.append(self.__create_album('Good Art', 'Medium', 300, 300))
        albums.append(self.__create_album('Good Art', 'Compilation', 300, 300))
        albums[2].albumtype = 'compilation'
        albums[2].store()

        with capture_log('beets.arttools') as logs:
            self.run_command('copyboundart')
        self.assertEqual(len(logs), 1)
        self.assertTrue(logs[0].startswith('arttools: Usage:'))

        with capture_log('beets.arttools') as logs:
            self.run_command('copyboundart', '-d', 'NotThere')
        self.assertEqual(len(logs), 1)
        self.assertTrue(logs[0].startswith("arttools: 'NotThere' does not "
                                           "exist"))

        files = [os.path.join(self.temp_dir,
                              '{0} - {1}.png'.format(album.albumartist,
                                                     album.album))
                 for album in albums[0:1]]
        files += [os.path.join(self.temp_dir, albums[2].album + '.png')]
        for f in files:
            self.assertNotExists(f)

        self.run_command('copyboundart', '-d', self.temp_dir)
        for f in files:
            self.assertExists(f)
            os.remove(f)

        self.run_command('copyboundart', '-d', self.temp_dir, '-n')
        for f in files:
            self.assertNotExists(f)

        with capture_log('beets.arttools') as logs:
            self.run_command('copyboundart', '-d', self.temp_dir, 'NotThere')
        self.assertEqual(len(logs), 1)
        self.assertTrue(logs[0].startswith("arttools: Copying all album art to"
                                           " {0}".format(self.temp_dir)))

        self.run_command('copyboundart', '-d', self.temp_dir, 'Small')
        self.assertExists(files[0])
        os.remove(files[0])

    def test_delete_unused_arts(self):
        config['arttools']['names'] = ['cover', 'extracted']
        config['art_filename'] = 'cover'

        paths = []
        self.__create_album('No Art', 'Nil')
        album = self.__create_album(art_width=200, art_height=200)
        paths += [album.artpath]
        paths += [self.__copy_art_to_album(300, 300, album, 'extracted.png')]
        self.__copy_art_to_album(250, 240, album, 'dummy.png')
        album2 = self.__create_album('ArtistB', 'AlbumB', art_width=200,
                                     art_height=200)
        paths += [album2.artpath]
        paths += [self.__copy_art_to_album(300, 300, album2, 'extracted.png')]
        self.__copy_art_to_album(250, 240, album2, 'dummy.png')

        self.run_command('deleteunusedart', 'Not There')
        for path in paths:
            self.assertExists(path)

        self.run_command('deleteunusedart', '-n')
        for path in paths:
            self.assertExists(path)

        self.run_command('deleteunusedart', 'AlbumB')
        for path in paths[0:2]:
            self.assertExists(path)
        self.assertNotExists(paths[3])

        self.run_command('deleteunusedart')
        for path in [paths[0], paths[2]]:
            self.assertExists(path)
        for path in [paths[1], paths[3]]:
            self.assertNotExists(path)

    def test_art_collage(self):
        albums = []
        self.__create_album('No Art', 'Nil')
        albums.append(self.__create_album('Good Art', 'Small', 200, 200))
        albums.append(self.__create_album('Good Art', 'Medium', 300, 300))

        with capture_log('beets.arttools') as logs:
            self.run_command('artcollage')
        self.assertEqual(len(logs), 1)
        self.assertTrue(logs[0].startswith("arttools: Usage:"))

        path = os.path.join(self.temp_dir, 'foo.jpg')
        self.run_command('artcollage', '-o', path)
        self.assertExists(path)

        path = os.path.join(self.temp_dir, 'covers.jpg')
        self.run_command('artcollage', '-o', self.temp_dir)
        self.assertExists(path)
        self.assertSize(path, 200, 400)

        self.run_command('artcollage', '-o', path, 'Small')
        self.assertExists(path)
        self.assertSize(path, 200, 200)

        self.run_command('artcollage', '-o', path, '-s', 50)
        self.assertExists(path)
        self.assertSize(path, 50, 100)

    def test_choose_art(self):
        config['arttools']['names'] = ['cover', 'extracted']

        albums = []
        # Don't do anything
        albums += [self.__create_album('Artist', 'Album Without Art')]
        # Choose best art
        albums += [self.__create_album('Artist', 'Album Without Bound Art')]
        self.__copy_art_to_album(200, 200, albums[1], 'cover.png')
        self.__copy_art_to_album(300, 300, albums[1], 'extracted.png')
        self.__copy_art_to_album(250, 240, albums[1], 'dummy.png')
        # Replace with better art
        albums += [self.__create_album('Artist', 'Album With Bound Art', 200,
                                       200)]
        self.__copy_art_to_album(300, 300, albums[2], 'extracted.png')
        self.__copy_art_to_album(250, 240, albums[2], 'dummy.png')
        # Choose best bad art
        albums += [self.__create_album('Artist', 'Album With Unbound Bad Art')]
        self.__copy_art_to_album(100, 100, albums[3], 'cover.png')
        self.__copy_art_to_album(200, 300, albums[3], 'extracted.png')
        self.__copy_art_to_album(300, 200, albums[3], 'dummy.png')

        def update_albums():
            for i in range(0, len(albums)):
                albums[i] = self.lib.albums(albums[i].album).get()

        self.run_command('chooseart', '-n')
        update_albums()
        self.assertIsNone(albums[0].artpath)
        self.assertIsNone(albums[1].artpath)
        self.assertSize(albums[2].artpath, 200, 200)
        self.assertIsNone(albums[3].artpath)

        self.run_command('chooseart', 'Not there')
        update_albums()
        self.assertIsNone(albums[0].artpath)
        self.assertIsNone(albums[1].artpath)
        self.assertSize(albums[2].artpath, 200, 200)
        self.assertIsNone(albums[3].artpath)

        self.run_command('chooseart', 'Unbound')
        update_albums()
        self.assertIsNone(albums[0].artpath)
        self.assertIsNone(albums[1].artpath)
        self.assertIsNotNone(albums[2].artpath)
        self.assertSize(albums[2].artpath, 200, 200)
        self.assertIsNotNone(albums[3].artpath)
        self.assertSize(albums[3].artpath, 100, 100)

        self.run_command('chooseart')
        update_albums()
        self.assertIsNone(albums[0].artpath)
        self.assertIsNotNone(albums[1].artpath)
        self.assertSize(albums[1].artpath, 300, 300)
        self.assertIsNotNone(albums[2].artpath)
        self.assertSize(albums[2].artpath, 300, 300)
        self.assertIsNotNone(albums[3].artpath)
        self.assertSize(albums[3].artpath, 100, 100)
