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

from beets.plugins import BeetsPlugin
from beets.ui import Subcommand
import beetsplug
from beetsplug.arttools.commands import Commands
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
            'host': u'127.0.0.1',
            'port': 8338
        })

        self.base_commands = Commands(self.config, self._log)

    def commands(self):
        web_choose_command = Subcommand('webchoose',
                                        help='starts a webserver to choose art'
                                             ' files manually')
        web_choose_command.parser.add_option('-d', '--debug',
                                             action='store_true',
                                             default=False, help='debug mode')
        web_choose_command.func = self.web_choose

        return self.base_commands.commands() + [web_choose_command]

    def web_choose(self, lib, opts, args):
        import webchooser
        webchooser.web_choose(self.config['host'].get(unicode),
                              self.config['port'].get(int),
                              opts.debug, lib, self.config, self._log)
