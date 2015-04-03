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
import random

from flask import Flask, g
import flask
import shutil
import thread
from werkzeug.exceptions import abort
from beets import config
from beets.util import bytestring_path, syspath

from beetsplug.web import QueryConverter


app = Flask(__name__)
app.url_map.converters['query'] = QueryConverter


def web_choose(plugin, lib, log, debug):
    app.config['lib'] = lib
    app.config['plugin'] = plugin
    app.config['log'] = log
    app.config['collect_tasks'] = []
    host = plugin.config['host'].get(unicode)
    port = plugin.config['port'].get(int)
    app.run(host=host, port=port, debug=debug, threaded=True)


@app.before_request
def before_request():
    g.lib = app.config['lib']
    g.plugin = app.config['plugin']
    g.log = app.config['log']
    g.collect_tasks = app.config['collect_tasks']


@app.route("/")
def home():
    size_thresh = g.plugin.config['size_thresh'].get()
    aspect_ratio_thresh = g.plugin.config['aspect_ratio_thresh'].get()
    return flask.render_template('index.html', size_thresh=size_thresh,
                                 ar_thresh=aspect_ratio_thresh)


@app.route("/query/")
def get_no_query_json():
    return get_query_json(None)


@app.route("/query/<query:queries>")
def get_query_json(queries):
    albums = g.lib.albums(queries)

    result = []
    for album in albums:
        result.append(get_album_dict(album))

    return json.dumps(result)


@app.route("/album/<album_id>")
def get_album_json(album_id):
    album = g.lib.albums(u"id:" + album_id).get()

    return json.dumps(get_album_dict(album))


@app.route("/art/<album_id>/<file_name>")
def get_art_file(album_id, file_name):
    file_name = bytestring_path(file_name)
    if os.sep in file_name:
        abort(404)
    album = g.lib.albums(u"id:" + album_id).get()

    return flask.send_file(syspath(os.path.join(album.path, file_name)))


@app.route("/deleteArt/<album_id>/<file_name>")
def delete_art_file(album_id, file_name):
    file_name = bytestring_path(file_name)
    if os.sep in file_name:
        abort(404)

    album = g.lib.albums(u"id:" + album_id).get()
    if not album:
        abort(404)

    art_path = syspath(os.path.join(album.path, file_name))
    if os.path.isfile(art_path):
        os.remove(art_path)
    else:
        abort(404)

    return json.dumps({'result': 'ok'})


@app.route("/chooseArt/<album_id>/<file_name>")
def choose_art_file(album_id, file_name):
    file_name = bytestring_path(file_name)
    if os.sep in file_name:
        abort(404)

    album = g.lib.albums(u"id:" + album_id).get()
    if not album:
        abort(404)

    art_path = syspath(os.path.join(album.path, file_name))
    if os.path.isfile(art_path):
        # Set new cover art
        art_filename = bytestring_path(config["art_filename"].get())
        new_image = syspath(os.path.join(album.item_dir(), art_filename +
                                         os.path.splitext(file_name)[1]))
        if art_path != new_image:
            shutil.copy(art_path, new_image)
        album.set_art(new_image, copy=False)
        album.store()

        # Delete other files
        g.plugin.delete_unused_art_of_album(album)
    else:
        abort(404)

    return json.dumps({'result': 'ok'})


@app.route("/collectArt/<album_id>")
def collect_art(album_id):
    album = g.lib.albums(u"id:" + album_id).get()
    if not album:
        abort(404)

    if album_id in g.collect_tasks:
        return json.dumps({})

    collect_tasks = g.collect_tasks
    plugin = g.plugin
    collect_tasks.append(album.id)

    def collect(album):
        plugin.collect_art_for_albums([album], False, False)
        collect_tasks.remove(album.id)

    thread.start_new_thread(collect, (album,))

    return json.dumps({'result': 'ok'})


def get_album_dict(album):
    art_files = []
    bound_art = None
    if album.artpath:
        bound_art = os.path.split(album.artpath)[1]
    chosen_art = g.plugin.get_chosen_art(album)
    if chosen_art:
        chosen_art = os.path.split(chosen_art)[1]
    for art_file in g.plugin.get_art_files(album.path):
        try:
            width, height, _, aspect_ratio = g.plugin.get_image_info(art_file)
        except IOError:
            continue
        file_name = os.path.split(art_file)[1]
        art_files.append({'file_name': file_name,
                          'width': width,
                          'height': height,
                          'aspect_ratio': aspect_ratio,
                          'bound_art': file_name == bound_art,
                          'would_choose': file_name == chosen_art})
    album_dict = {'id': album.id,
                  'title': str(album),
                  'art_files': art_files,
                  'collecting': album.id in g.collect_tasks}
    return album_dict
