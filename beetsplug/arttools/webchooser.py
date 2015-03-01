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
import json
import os

from flask import Flask, g
import flask
from werkzeug.exceptions import abort
from beets.util import bytestring_path, syspath

from beetsplug.web import QueryConverter


app = Flask(__name__)
app.url_map.converters['query'] = QueryConverter


def web_choose(plugin, lib, log, debug):
    app.config['lib'] = lib
    app.config['plugin'] = plugin
    app.config['log'] = log
    host = plugin.config['host'].get(unicode)
    port = plugin.config['port'].get(int)
    app.run(host=host, port=port, debug=debug, threaded=True)


@app.before_request
def before_request():
    g.lib = app.config['lib']
    g.plugin = app.config['plugin']
    g.log = app.config['log']


@app.route("/")
def home():
    size_thresh = g.plugin.config['size_thresh'].get()
    aspect_ratio_thresh = g.plugin.config['aspect_ratio_thresh'].get()
    return flask.render_template('index.html', size_thresh=size_thresh,
                                 ar_thresh=aspect_ratio_thresh)


@app.route("/query/")
def no_query():
    return query(None)


@app.route("/art/<album_id>/<file_name>")
def art(album_id, file_name):
    file_name = bytestring_path(file_name)
    if os.sep in file_name:
        abort(404)
    album = g.lib.albums(u"id:" + album_id).get()

    return flask.send_file(syspath(os.path.join(album.path, file_name)))


@app.route("/query/<query:queries>")
def query(queries):
    albums = g.lib.albums(queries)

    result = []
    for album in albums:
        art_files = []
        bound_art = None
        if album.artpath:
            bound_art = os.path.split(album.artpath)[1]
        chosen_art = g.plugin.get_chosen_art(album)
        if chosen_art:
            chosen_art = os.path.split(chosen_art)[1]
        for art_file in g.plugin.get_art_files(album.path):
            width, height, _, aspect_ratio = g.plugin.get_image_info(art_file)
            file_name = os.path.split(art_file)[1]
            art_files.append({'file_name': file_name,
                              'width': width,
                              'height': height,
                              'aspect_ratio': aspect_ratio,
                              'bound_art': file_name == bound_art,
                              'would_choose': file_name == chosen_art})
        result.append({'id': album.id,
                       'title': str(album),
                       'art_files': art_files})

    return json.dumps(result)