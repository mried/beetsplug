# This file is part of beets.
# Copyright 2014, Malte Ried
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

import logging
import os
import re
from beets import config
from beets.importer import action, SingletonImportTask
from beets.plugins import BeetsPlugin
from beets.util import syspath

log = logging.getLogger('beets')


class RegexFileFilterPlugin(BeetsPlugin):
    def __init__(self):
        super(RegexFileFilterPlugin, self).__init__()

        self.register_listener('import_task_created',
                               self.import_task_created_event)

        self.config.add({
            'ignore_case': False,
            'invert_folder_result': False,
            'invert_file_result': False,
            'folder_name_regex': '.*',
            'file_name_regex': '.*'
        })
        flags = re.IGNORECASE if self.config['ignore_case'].get() else 0

        self.invert_folder_album_result = \
            self.invert_folder_singleton_result = \
            self.config['invert_folder_result'].get()
        self.invert_file_album_result = \
            self.invert_file_singleton_result = \
            self.config['invert_file_result'].get()
        self.folder_name_album_regex = \
            self.folder_name_singleton_regex = \
            re.compile(self.config['folder_name_regex'].get(), flags)
        self.file_name_album_regex = \
            self.file_name_singleton_regex = \
            re.compile(self.config['file_name_regex'].get(), flags)

        if 'album' in self.config:
            album_config = self.config['album']
            if 'invert_folder_result' in album_config:
                self.invert_folder_album_result = album_config[
                    'invert_folder_result'].get()
            if 'invert_file_result' in album_config:
                self.invert_file_album_result = album_config[
                    'invert_file_result'].get()
            if 'folder_name_regex' in album_config:
                self.folder_name_album_regex = re.compile(
                    album_config['folder_name_regex'].get(), flags)
            if 'file_name_regex' in album_config:
                self.file_name_album_regex = re.compile(
                    album_config['file_name_regex'].get(), flags)

        if 'singleton' in self.config:
            singleton_config = self.config['singleton']
            if 'invert_folder_result' in singleton_config:
                self.invert_folder_singleton_result = singleton_config[
                    'invert_folder_result'].get()
            if 'invert_file_result' in singleton_config:
                self.invert_file_singleton_result = singleton_config[
                    'invert_file_result'].get()
            if 'folder_name_regex' in singleton_config:
                self.folder_name_singleton_regex = re.compile(
                    singleton_config['folder_name_regex'].get(), flags)
            if 'file_name_regex' in singleton_config:
                self.file_name_singleton_regex = re.compile(
                    singleton_config['file_name_regex'].get(), flags)

    def import_task_created_event(self, session, task):
        if task.items and len(task.items) > 0:
            items_to_import = []
            for item in task.items:
                if self.file_filter(item['path'], session.paths):
                    items_to_import.append(item)
            if len(items_to_import) > 0:
                task.items = items_to_import
            else:
                task.choice_flag = action.SKIP
        elif isinstance(task, SingletonImportTask):
            if not self.file_filter(task.item['path'], session.paths):
                task.choice_flag = action.SKIP

    def file_filter(self, full_path, base_paths):
        """Checks if the configured regular expressions allow the import of the
        file given in full_path.
        """
        # The folder regex only checks the folder names starting from the
        # longest base path. Find this folder.
        matched_base_path = ''
        for base_path in base_paths:
            if full_path.startswith(base_path) and len(base_path) > len(matched_base_path):
                matched_base_path = base_path
        relative_path = full_path[len(matched_base_path):]

        if os.path.isdir(full_path):
            path = relative_path
            file_name = None
        else:
            path, file_name = os.path.split(relative_path)
        path, folder_name = os.path.split(path)

        import_config = dict(config['import'])
        if 'singletons' not in import_config or not import_config[
            'singletons']:
            # Album

            # Folder
            while len(folder_name) > 0:
                matched = self.folder_name_album_regex.match(
                    folder_name) is not None
                matched = not matched if self.invert_folder_album_result else matched
                if not matched:
                    return False
                path, folder_name = os.path.split(path)

            # File
            matched = self.file_name_album_regex.match(
                file_name) is not None
            matched = not matched if self.invert_file_album_result else matched
            if not matched:
                return False
            return True
        else:
            # Singleton

            # Folder
            while len(folder_name) > 0:
                matched = self.folder_name_singleton_regex.match(
                    folder_name) is not None
                matched = not matched if self.invert_folder_singleton_result else matched
                if not matched:
                    return False
                path, folder_name = os.path.split(path)

            # File
            matched = self.file_name_singleton_regex.match(
                file_name) is not None
            matched = not matched if self.invert_file_singleton_result else matched
            if not matched:
                return False
            return True
