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
import math

from PIL import Image

from beets.plugins import BeetsPlugin
import beetsplug
from beets.ui import Subcommand
from beets import config
from beets import logging
from beets import ui
from beets import util
from beets.util import normpath, bytestring_path
from beetsplug.embedart import EmbedCoverArtPlugin
from beetsplug.fetchart import FetchArtPlugin


class ArtToolsPlugin(BeetsPlugin):
    def __init__(self):
        super(ArtToolsPlugin, self).__init__()

        self.config.add({
            'aspect_ratio_thresh': 0.8,
            'size_thresh': 200,
            'additional_names': [],
            'collage_tilesize': 200,
            'collect_extract': True,
            'collect_fetch_sources': beetsplug.fetchart.SOURCES_ALL,
            'chooseart_weightings': {
                'aspect_ratio': 1,
                'pixels': 0.8,
                'bytes': 0.2
            },
            'host': u'127.0.0.1',
            'port': 8338
        })


    def commands(self):
        list_bound_art_command = Subcommand('listboundart',
                                            help='lists all cover arts of '
                                                 'selected albums')
        list_bound_art_command.func = self.list_bound_art

        list_bad_bound_art_command = Subcommand('listbadboundart',
                                                help='lists all cover arts of '
                                                     'selected albums which '
                                                     'are bad')
        list_bad_bound_art_command.func = self.list_bad_bound_art

        copy_bound_art_command = Subcommand('copyboundart',
                                            help='copys all cover arts of the '
                                                 'selected albums into a '
                                                 'single directory')
        copy_bound_art_command.func = self.copy_bound_art
        copy_bound_art_command.parser.add_option('-d', '--dir', dest='dir',
                                                 help='The directory to copy '
                                                      'the images to')
        copy_bound_art_command.parser.add_option('-p', '--pretend',
                                                 dest='pretend',
                                                 action='store_true',
                                                 default=False,
                                                 help='do not copy anything, '
                                                      'only print files this '
                                                      'command would copy')

        choose_art_command = Subcommand('chooseart',
                                        help='chooses the best album art file')
        choose_art_command.func = self.choose_art
        choose_art_command.parser.add_option('-p', '--pretend',
                                             dest='pretend',
                                             action='store_true',
                                             default=False,
                                             help='do not change anything, '
                                                  'only print files this '
                                                  'command would choose')

        delete_unused_art_command = Subcommand('deleteunusedart',
                                               help='deletes all image files '
                                                    'matching the art '
                                                    'filenames which are not '
                                                    'used')
        delete_unused_art_command.func = self.delete_unused_arts
        delete_unused_art_command.parser.add_option('-p', '--pretend',
                                                    dest='pretend',
                                                    action='store_true',
                                                    default=False,
                                                    help='do not delete, only '
                                                         'print files to '
                                                         'delete')

        list_art_command = Subcommand('listart',
                                      help='lists all album art files '
                                           'matching the configured names')
        list_art_command.func = self.list_art
        list_art_command.parser.add_option('-v', '--verbose', dest='verbose',
                                           action='store_true', default=False,
                                           help='verbose output')

        art_collage_command = Subcommand('artcollage',
                                         help='creates an image with all '
                                              'cover arts of the selected '
                                              'albums')
        art_collage_command.func = self.art_collage
        art_collage_command.parser.add_option('-o', '--out', dest='outFile',
                                              help='The name of the image to '
                                                   'create')
        art_collage_command.parser.add_option('-s', '--size', dest='tilesize',
                                              help='The size of each cover '
                                                   'art')

        collect_art_command = Subcommand('collectart',
                                         help='collects all configured cover'
                                              'arts')
        collect_art_command.func = self.collect_art
        collect_art_command.parser.add_option('-f', '--force', dest='force',
                                              action='store_true',
                                              default=False,
                                              help='Force extraction or '
                                                   'download even if the file '
                                                   'already exists')
        collect_art_command.parser.add_option('-v', '--verbose',
                                              dest='verbose',
                                              action='store_true',
                                              default=False,
                                              help='Output verbose logging '
                                                   'information')

        web_choose_command = Subcommand('webchoose',
                                        help='starts a webserver to choose art'
                                             ' files manually')
        web_choose_command.parser.add_option('-d', '--debug',
                                             action='store_true',
                                             default=False, help='debug mode')
        web_choose_command.func = self.web_choose

        return [list_bound_art_command, list_bad_bound_art_command,
                copy_bound_art_command, choose_art_command,
                list_art_command, art_collage_command,
                delete_unused_art_command, collect_art_command,
                web_choose_command]

    def list_bound_art(self, lib, opts, args):
        """List all art files bound to albums selected by the query"""
        albums = lib.albums(ui.decargs(args))
        for image in self._get_bound_art_files(albums):
            self._log.info(util.displayable_path(image))

    def list_bad_bound_art(self, lib, opts, args):
        """List all art files bound to albums selected by the query which
            do not match the rules for a good album art."""
        aspect_ratio_thresh = self.config['aspect_ratio_thresh'].get()
        size_thresh = self.config['size_thresh'].get()

        self._log.info(
            u"Art is bad if its aspect ratio is < {0} or either width or "
            u"height is < {1}", aspect_ratio_thresh, size_thresh)

        albums = lib.albums(ui.decargs(args))
        for image in self._get_bound_art_files(albums):
            try:
                width, height, size, aspect_ratio = self.get_image_info(image)
                if aspect_ratio < aspect_ratio_thresh or size < size_thresh:
                    self._log.info(u'{0} ({1} x {2}) AR:{3:.4}',
                                   util.displayable_path(image), width,
                                   height, aspect_ratio)
            except Exception:
                pass

    def copy_bound_art(self, lib, opts, args):
        if not opts.dir:
            self._log.info(u"Usage: beet copyart -d <destination directory> "
                           u"[<query>]")
            return

        dest_dir = os.path.normpath(opts.dir)
        if not os.path.exists(dest_dir) or not os.path.isdir(dest_dir):
            self._log.info(
                u"'{0}' does not exist or is not a directory. "
                u"Stopping.", util.displayable_path(dest_dir))
            return

        query = ui.decargs(args)
        self._log.info(u"Copying all album art to {0}",
                       util.displayable_path(dest_dir), )
        albums = lib.albums(query)
        for album in albums:
            if album.artpath:
                new_filename = album.evaluate_template(u"$albumartist - "
                                                       u"$album",
                                                       for_path=True)
                if album.albumtype == u'compilation':
                    new_filename = u"" + album.album
                # Add the file extension
                new_filename += os.path.splitext(album.artpath)[1]

                old_path = util.syspath(album.artpath)
                new_path = util.syspath(os.path.join(dest_dir, new_filename))

                self._log.info(u"Copy '{0}' to '{1}'",
                               util.displayable_path(old_path),
                               util.displayable_path(new_path))

                if not opts.pretend:
                    shutil.copy(old_path, new_path)

    def choose_art(self, lib, opts, args):
        art_filename = bytestring_path(config["art_filename"].get())
        albums = lib.albums(ui.decargs(args))
        for album in albums:
            chosen_image = bytestring_path(self.get_chosen_art(album))
            if not opts.pretend and chosen_image:
                new_image = os.path.join(album.item_dir(), art_filename +
                                         os.path.splitext(chosen_image)[1])
                if chosen_image != new_image:
                    shutil.copy(chosen_image, new_image)
                album.set_art(new_image)
                album.store()

    def get_chosen_art(self, album):
        aspect_ratio_thresh = self.config['aspect_ratio_thresh'].get()
        size_thresh = self.config['size_thresh'].get()
        album_path = album.item_dir()
        if album_path:
            images = self.get_art_files(album_path)
            if images and len(images) > 0:
                attributed_images = []
                for image in images:
                    width, height, size, aspect_ratio = self. \
                        get_image_info(util.syspath(image))
                    attributed_images.append({'file': image,
                                              'bytes': os.stat(
                                                  util.syspath(image)).st_size,
                                              'width': width,
                                              'height': height,
                                              'size': size,
                                              'pixels': width * height,
                                              'ar': aspect_ratio})

                filtered_images = \
                    filter(lambda i: i['ar'] >= aspect_ratio_thresh
                           and i['size'] >= size_thresh,
                           attributed_images)

                if len(filtered_images) == 0:
                    self._log.debug(
                        u"no image matched rules for album '{0}'", album.album)
                    filtered_images = attributed_images

                # Find the best image:
                # - Sort the images for aspect ratio, size in pixels and size
                #   in bytes
                # - Store the ordinals for each sort
                # - Summarize all ordinals per image (using weightings)
                # - Choose the one with the lowest sum
                self.add_points(filtered_images, 'ar', 0.0001)
                self.add_points(filtered_images, 'pixels')
                self.add_points(filtered_images, 'bytes')

                weightings = self.config['chooseart_weightings'].get()

                for filtered_image in filtered_images:
                    filtered_image['points'] = \
                        filtered_image['ar_points'] * weightings['aspect_ratio'] + \
                        filtered_image['pixels_points'] * weightings['pixels'] + \
                        filtered_image['bytes_points'] * weightings['bytes']
                filtered_images = sorted(filtered_images,
                                         key=lambda i: i['points'],
                                         reverse=True)

                chosen_image = filtered_images[0]['file']
                self._log.info(u"chosen {0}",
                               util.displayable_path(chosen_image))
                return chosen_image
            else:
                self._log.debug(
                    u"no image found for album {0}", album.album)

    @staticmethod
    def add_points(images, field, threshold=1.0):
        sorted_images = sorted(images, key=lambda image: image[field])
        ordinal = -1
        last_value = -1
        for i in range(len(sorted_images)):
            if abs(last_value - sorted_images[i][field]) > threshold:
                last_value = sorted_images[i][field]
                ordinal += 1
            sorted_images[i][field + '_points'] = ordinal

    def delete_unused_arts(self, lib, opts, args):
        art_filename = config["art_filename"].get()
        albums = lib.albums(ui.decargs(args))
        for album in albums:
            album_path = album.item_dir()
            if album_path:
                for image in self.get_art_files(album_path):
                    if os.path.splitext(os.path.basename(image))[0] != \
                            art_filename:
                        self._log.info(u"removing {0}",
                                       util.displayable_path(image))
                        if not opts.pretend:
                            os.remove(util.syspath(image))

    def list_art(self, lib, opts, args):
        """Prints all found images matching the configured names."""
        albums = lib.albums(ui.decargs(args))
        for album in albums:
            albumpath = album.item_dir()
            if albumpath:
                images = self.get_art_files(albumpath)
                for image in images:
                    info = u""
                    if opts.verbose:
                        width, height, size, aspect_ratio = \
                            self.get_image_info(util.syspath(image))
                        info = u" ({0} x {1}) AR:{2:.4}".format(width, height,
                                                                aspect_ratio)
                    self._log.info(util.displayable_path(image) + info)

    def art_collage(self, lib, opts, args):
        albums = lib.albums(ui.decargs(args))
        images = self._get_bound_art_files(albums)
        tile_size = opts.tilesize or self.config['collage_tilesize'].get()
        out_file = os.path.abspath(opts.outFile)

        if not opts.outFile:
            self._log.info(u"Usage: artcollage -f <output file> [-s <size>] "
                           u"[query]")
            return

        if os.path.isdir(out_file):
            out_file = os.path.join(out_file, "covers.jpg")

        if not os.path.exists(os.path.split(out_file)[0]):
            self._log.error(u"Destination does not exist.")
            return

        cols = int(math.floor(math.sqrt(len(images))))
        rows = int(math.ceil(len(images) / float(cols)))

        result = Image.new("RGB",
                           (cols * tile_size, rows * tile_size),
                           "black")

        for row in xrange(0, rows):
            for col in xrange(0, cols):
                if row * cols + col >= len(images):
                    break
                image = Image.open(util.syspath(images[row * cols + col]))
                if not image:
                    continue
                image = image.resize((tile_size, tile_size))
                result.paste(image, (col * tile_size, row * tile_size))

        result.save(out_file)

    def collect_art(self, lib, opts, args):
        albums = lib.albums(ui.decargs(args))
        if self.config['collect_extract'].get():
            self._log.info(u"Extracting cover arts for matched albums...")
            extractor = EmbedCoverArtPlugin()
            extractor._log.setLevel(logging.ERROR)
            success = 0
            skipped = 0
            for album in albums:
                artpath = normpath(os.path.join(album.path, 'extracted'))
                if self._art_file_exists(artpath) and not opts.force:
                    skipped += 1
                    if opts.verbose:
                        self._log.info(u"  Skipping extraction for '{0}': "
                                       u"file already exists.", album)
                    continue
                if extractor.extract_first(artpath, album.items()):
                    success += 1
                    if opts.verbose:
                        self._log.info(u"  Extracted art for '{0}'.",
                                       album)
                elif opts.verbose:
                    self._log.info(u"  Could not extract art for '{0}'.",
                                   album)
            self._log.info(u"  Success: {0} Skipped: {1} Failed: {2} Total: "
                           u"{3}",
                           success, skipped, len(albums) - success - skipped,
                           len(albums))

        if len(self.config['collect_fetch_sources'].get()) > 0:
            config['fetchart'].get()['remote_priority'] = True
            for source in self.config['collect_fetch_sources'].as_str_seq():
                self._log.info(u"Fetching album arts using source '{0}'",
                               source)
                success = 0
                skipped = 0
                config['fetchart'].get()['sources'] = [source]
                artname = b'fetched{0}'.format(source.title())
                fetcher = FetchArtPlugin()
                for album in albums:
                    if self._art_file_exists(os.path.join(album.path,
                                                          artname))\
                            and not opts.force:
                        skipped += 1
                        if opts.verbose:
                            self._log.info(u"  Skipping fetch for '{0}': file "
                                           u"already exists.", album)
                        continue

                    filename = fetcher.art_for_album(album, None)
                    if filename:
                        filename = bytestring_path(filename)
                        extension = os.path.splitext(filename)[1]
                        artpath = os.path.join(album.path, artname + extension)
                        shutil.move(filename, util.syspath(normpath(artpath)))
                        success += 1
                        if opts.verbose:
                            self._log.info(u"  Fetched art for '{0}'.",
                                           album)
                    elif opts.verbose:
                        self._log.info(u"  Could not fetch art for '{0}'.",
                                       album)
                self._log.info(u"  Success: {0} Skipped: {1} Failed: {2} "
                               u"Total: {3}",
                               success, skipped,
                               len(albums) - success - skipped, len(albums))

    def web_choose(self, lib, opts, args):
        import webchooser
        webchooser.web_choose(self, lib, self._log, opts.debug)

    def _art_file_exists(self, path):
        """Checks if an art file with a given name exists within a folder.
        The path is spitted into the the filename and the rest. The filename
        must not have an extension - all extensions will match.
        """
        path, filename = os.path.split(util.syspath(path))
        for current_path in self._get_image_files(path):
            current_file_name = os.path.split(util.syspath(current_path))[1]
            current_file_name = os.path.splitext(current_file_name)[0]
            if current_file_name == filename:
                return True
        return False

    def get_image_info(self, path):
        """Extracts some informations about the image at the given path.
        Returns the width, height, size and aspect ratio of the image.
        The size equals width if width < height."""
        im = Image.open(util.syspath(path))
        if not im:
            self._log.warn(u"badart: not able to open file '{0}'",
                           util.displayable_path(path))
            return
        width = im.size[0]
        height = im.size[1]
        size = width if width < height else height
        aspect_ratio = float(width) / float(height)
        if aspect_ratio > 1:
            aspect_ratio = 1 / aspect_ratio
        return width, height, size, aspect_ratio

    @staticmethod
    def _get_image_files(path):
        """Returns a list of files which seems to be images. This is determined
        using the file extension."""
        images = []
        path = util.syspath(path)
        for fileName in os.listdir(path):
            for ext in ['jpg', 'jpeg', 'png', 'bmp']:
                if fileName.lower().endswith('.' + ext) and os.path.isfile(
                        os.path.join(path, fileName)):
                    images.append(os.path.join(path, fileName))
                    break
        return images

    def get_art_files(self, path):
        """Searches for image files matching to the possible cover art names.
        The resulting list is sorted such that the images are ordered like the
        configured names."""
        # Find all files that look like images in the directory.
        images = self._get_image_files(path)

        names = self.config['additional_names'].as_str_seq()
        names.append(config['art_filename'].get())
        names.append('extracted')
        for source in self.config['collect_fetch_sources'].as_str_seq():
            names.append('fetched{0}'.format(source.title()))

        filtered = []
        for name in names:
            for image in images:
                if os.path.splitext(os.path.basename(image))[0] == name:
                    filtered.append(image)

        return filtered

    @staticmethod
    def _get_bound_art_files(albums):
        """Returns a list of all cover arts bound the list of albums given."""
        images = []
        for album in albums:
            if album.artpath:
                images.append(album.artpath)
        return images
