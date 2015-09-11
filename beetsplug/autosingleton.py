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
import re

from beets import util
from beets.importer import ImportTask, SingletonImportTask,\
    SentinelImportTask, ArchiveImportTask, ImportTaskFactory
from beets.plugins import BeetsPlugin


class AutoSingletonPlugin(BeetsPlugin):
    def __init__(self):
        super(AutoSingletonPlugin, self).__init__()

        self.chained = False

        self.register_listener('import_task_created',
                               self.import_task_created_event)

    def import_task_created_event(self, session, task, chained=False):
        """

        :type task: ImportTask
        """
        if self.chained and not chained:
            return None

        if isinstance(task, SingletonImportTask) \
                or isinstance(task, SentinelImportTask)\
                or isinstance(task, ArchiveImportTask):
            return task

        if self.is_singleton(task):
            return self.get_singletons(task, session)
        return [task]

    @staticmethod
    def get_singletons(task, session):
        factory = ImportTaskFactory(task.toppath, session)
        new_tasks = []
        for item in task.items:
            new_task = factory.singleton(item.path)
            if new_task:
                new_tasks.append(new_task)

        return new_tasks

    def is_singleton(self, task):
        task_path = util.syspath(task.paths[0])
        path, folder = os.path.split(task_path)
        if folder.lower() == 'misc':
            # Singletons
            return True

        # Are there any directories in the folder of the current task?
        for sub_entry in os.listdir(task_path):
            sub_entry = os.path.join(task_path, sub_entry)
            if os.path.isdir(sub_entry):
                # Singletons
                return True

        # Do any of the file names of all items does not start with two digits?
        pattern = re.compile('\\d\\d+ - ', re.IGNORECASE)
        for path in [util.syspath(item['path']) for item in task.items]:
            _, file_name = os.path.split(path)
            if path.endswith('.mp3') and not pattern.match(file_name):
                # Singleton
                return True

        # Album
        return False
