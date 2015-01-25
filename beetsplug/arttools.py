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
from beets.ui import Subcommand
from beets import config
from beets import ui
from beets import util


class ArtToolsPlugin(BeetsPlugin):
    def __init__(self):
        super(ArtToolsPlugin, self).__init__()

        self.config.add({
            'aspect_ratio_thresh': 0.8,
            'size_thresh': 200,
            'names': ['cover'],
            'collage_tilesize': 200,
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

        copy_bound_art_command = Subcommand('copyart',
                                            help='copys all cover arts of the '
                                                 'selected albums into a '
                                                 'single directory')
        copy_bound_art_command.func = self.copy_bound_art
        copy_bound_art_command.parser.add_option('-d', '--dir', dest='dir',
                                                 help='The directory to copy '
                                                      'the images to')
        copy_bound_art_command.parser.add_option('-n', '--no-action',
                                                 dest='noAction',
                                                 action='store_true',
                                                 default=False,
                                                 help='do not copy anything, '
                                                      'only print files this '
                                                      'command would copy')

        choose_art_command = Subcommand('chooseart',
                                        help='chooses the best album art file')
        choose_art_command.func = self.choose_art
        choose_art_command.parser.add_option('-n', '--no-action',
                                             dest='noAction',
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
        delete_unused_art_command.parser.add_option('-n', '--no-action',
                                                    dest='noAction',
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

        return [list_bound_art_command, list_bad_bound_art_command,
                copy_bound_art_command, choose_art_command,
                list_art_command, art_collage_command,
                delete_unused_art_command]

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
                width, height, size, aspect_ratio = self._get_image_info(image)
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
                       util.displayable_path(dest_dir),)
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

                if not opts.noAction:
                    shutil.copy(old_path, new_path)

    def choose_art(self, lib, opts, args):
        aspect_ratio_thresh = self.config['aspect_ratio_thresh'].get()
        size_thresh = self.config['size_thresh'].get()
        art_filename = config["art_filename"].get()
        albums = lib.albums(ui.decargs(args))
        for album in albums:
            album_path = album.item_dir()
            if album_path:
                images = self._get_art_files(album_path)
                if images and len(images) > 0:
                    filtered_images = []
                    for image in images:
                        width, height, size, aspect_ratio = self.\
                            _get_image_info(util.syspath(image))
                        if aspect_ratio >= aspect_ratio_thresh and \
                           size >= size_thresh:
                            filtered_images.append(image)

                    if len(filtered_images) == 0:
                        self._log.debug(
                            u"no image matched rules for album '{0}', "
                            u"choosing first", album.album)
                        chosen_image = images[0]
                    else:
                        # Get the file size for each image
                        file_sizes = map(
                            lambda file_name: os.stat(util.syspath(file_name))
                            .st_size, filtered_images)
                        # Find the image with the greatest file size
                        max_value = max(file_sizes)
                        max_index = file_sizes.index(max_value)

                        chosen_image = images[max_index]
                    self._log.info(u"choosed {0}",
                                   util.displayable_path(chosen_image))
                    new_image = os.path.join(album_path, art_filename +
                                             os.path.splitext(chosen_image)[1])
                    if not opts.noAction:
                        if chosen_image != new_image:
                            shutil.copy(chosen_image, new_image)
                        album.set_art(new_image)
                        album.store()
                else:
                    self._log.debug(
                        u"no image found for album {0}", album.album)

    def delete_unused_arts(self, lib, opts, args):
        art_filename = config["art_filename"].get()
        albums = lib.albums(ui.decargs(args))
        for album in albums:
            album_path = album.item_dir()
            if album_path:
                for image in self._get_art_files(album_path):
                    if os.path.splitext(os.path.basename(image))[0] !=\
                            art_filename:
                        self._log.info(u"removing {0}",
                                       util.displayable_path(image))
                        if not opts.noAction:
                            os.remove(util.syspath(image))

    def list_art(self, lib, opts, args):
        """Prints all found images matching the configured names."""
        albums = lib.albums(ui.decargs(args))
        for album in albums:
            albumpath = album.item_dir()
            if albumpath:
                images = self._get_art_files(albumpath)
                for image in images:
                    info = u""
                    if opts.verbose:
                        width, height, size, aspect_ratio = \
                            self._get_image_info(util.syspath(image))
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

    def _get_image_info(self, path):
        """Extracts some informations about the image at the given path.
        Returns the width, height, size and aspect ratio of the image.
        The size equals width if width < height."""
        im = Image.open(util.syspath(path))
        if not im:
            self._log.warn(u"badart: not able to open file '{0}'", path)
            return
        width = im.size[0]
        height = im.size[1]
        size = width if width < height else height
        aspect_ratio = float(width) / float(height)
        if aspect_ratio > 1:
            aspect_ratio = 1 / aspect_ratio
        return width, height, size, aspect_ratio

    def _get_art_files(self, path):
        """Searches for image files matching to the possible names configured.
        The resulting list is sorted such that the images are ordered like the
        configured names."""
        names = self.config['names'].as_str_seq()

        # Find all files that look like images in the directory.
        images = []
        for fileName in os.listdir(path):
            for ext in ['png', 'jpg', 'jpeg']:
                if fileName.lower().endswith('.' + ext) and os.path.isfile(
                        os.path.join(path, fileName)):
                    images.append(os.path.join(path, fileName))
                    break

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
