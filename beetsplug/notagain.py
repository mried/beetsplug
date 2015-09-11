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
from beets import config
from beets.importer import SingletonImportTask, SentinelImportTask, ArchiveImportTask
from beets.library import PathQuery
from beets.plugins import BeetsPlugin


class NotAgain(BeetsPlugin):
    def __init__(self):
        super(NotAgain, self).__init__()

        self.chained = False

        self.register_listener('import_task_created',
                               self.import_task_created_event)

    def import_task_created_event(self, session, task, chained=False):
        """

        :type task: ImportTask
        :type session: ImportSession
        """
        if self.chained and not chained:
            return None

        if isinstance(task, SentinelImportTask) \
                or isinstance(task, ArchiveImportTask):
            return [task]

        library_base_path = config['directory'].get()
        items_to_remove = []
        if isinstance(task, SingletonImportTask):
            for item in task.items:
                # Check if path of current item is located inside the library
                if item.path.startswith(library_base_path) and \
                        session.lib.items(PathQuery('path', item.path)):
                    items_to_remove.append(item)

            for item in items_to_remove:
                task.items.remove(item)
                if item.path in task.paths:
                    task.paths.remove(item.path)
                self._log.info(
                    'Skipping item {0}: already present at the library.'.format(item.path))

            return [task] if len(task.items) > 0 else []

        # This is an album. Check if all files which should be imported
        # are already in the library. Import again if not.
        for item in task.items:
            # Check if path of current item is located inside the library
            if not item.path.startswith(library_base_path) or \
                    not session.lib.items(PathQuery('path', item.path)):
                return [task]

        self._log.info('Skipping album {0}: already present at the library.'.format(task.paths[0]))
        return []
