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
from beets.plugins import BeetsPlugin, find_plugins


class MultipleTaskCreated(BeetsPlugin):
    def __init__(self):
        super(MultipleTaskCreated, self).__init__()

        self.plugins = []
        self.register_listener('import_task_created',
                               self.import_task_created_event)
        self.register_listener('pluginload', self.loaded)

    def loaded(self):
        plugin_map = {}
        for plugin in find_plugins():
            if plugin.name in self.config['plugins'].get():
                plugin_map[plugin.name] = plugin
                plugin.chained = True

        for plugin in self.config['plugins'].get():
            if plugin in plugin_map:
                self.plugins.append(plugin_map[plugin])

    def import_task_created_event(self, session, task):
        """

        :type task: ImportTask
        :type session: ImportSession
        """
        tasks = [task]
        for plugin in self.plugins:
            new_tasks = []
            for current_task in tasks:
                new_tasks.extend(plugin.import_task_created_event(session, current_task,
                                                                  chained=True))
            tasks = new_tasks

        return tasks
