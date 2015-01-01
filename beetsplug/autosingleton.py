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
import os
from beets.importer import ImportTask, SingletonImportTask, action
from beets.plugins import BeetsPlugin
from beets.util import pipeline


class AutoSingletonPlugin(BeetsPlugin):
    def __init__(self):
        super(AutoSingletonPlugin, self).__init__()

        self.register_listener('import_task_created',
                               self.import_task_created_event)

    def import_task_created_event(self, session, task):
        """

        :type task: ImportTask
        """
        if isinstance(task, SingletonImportTask):
            return

        path, folder = os.path.split(task.paths[0])
        if folder.lower() == 'misc':
            # Singletons
            self.emit_singletons(task)
            return

        # Are there any directories in the folder of the current task?
            # Singletons
            # return self.emit_singletons(task)

        # Do th file names of all items start with two digits?
            # Album
            # return task

        # Else:
        # Singletons
        # return self.emit_singletons(task)

    def emit_singletons(self, task):
        task.choice_flag = action.SKIP
        new_tasks = []
        for item in task.items:
            new_tasks.append(SingletonImportTask(task.toppath, item))

        pipeline.multiple(new_tasks)
