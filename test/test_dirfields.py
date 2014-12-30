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
from beets import config
import beetsplug
from test import _common
from test.test_importer import ImportHelper, AutotagStub


class DirFieldsPluginTest(_common.TestCase, ImportHelper):
    """ Test the dir field plugin
    """

    def __init__(self, method_name='runTest'):
        super(DirFieldsPluginTest, self).__init__(method_name)
        self.matcher = None

    def setUp(self):
        super(DirFieldsPluginTest, self).setUp()
        self.setup_beets()
        self._create_import_dir(2)
        self._setup_import_session()
        self.matcher = AutotagStub().install()
        self.matcher.macthin = AutotagStub.GOOD
        config['pluginpath'] = [os.path.join(os.path.dirname(os.path.realpath(__file__)), "..",
                                             "beetsplug")]
        beetsplug.__path__ = config['pluginpath'].get() + beetsplug.__path__
        self.load_plugins('dirfields')

    def tearDown(self):
        self.teardown_beets()
        self.matcher.restore()
        self.unload_plugins()

    def test_fields(self):
        import_files = [self.import_dir]
        self._setup_import_session()
        self.importer.paths = import_files

        self.importer.run()

        dirs = {}
        for idx, dir_name in enumerate(import_files[0].split(os.path.sep)):
            dirs["dir%i" % idx] = dir_name
        for item in self.lib.items():
            self.assertDictContainsSubset(dirs, item)

    def test_fields_rename(self):
        config['dirfields']['dir0'] = 'foo'
        config['dirfields']['dir3'] = 'bar'
        config['dirfields']['dir100'] = 'abc'
        import_files = [self.import_dir]
        self._setup_import_session()
        self.importer.paths = import_files

        self.importer.run()

        dirs = {}
        for idx, dir_name in enumerate(import_files[0].split(os.path.sep)):
            dirs["dir%i" % idx] = dir_name
        dirs['foo'] = dirs['dir0']
        dirs['bar'] = dirs['dir3']
        dirs.pop('dir0', None)
        dirs.pop('dir3', None)
        for item in self.lib.items():
            self.assertDictContainsSubset(dirs, item)
            self.assertNotIn('abc', item)

    def test_fields_levels(self):
        config['dirfields']['levels'] = '6,-1,6,4-3,8-'
        import_files = [self.import_dir]
        self._setup_import_session()
        self.importer.paths = import_files

        self.importer.run()

        dirs = {}
        missing_dirs = []
        levels = [0, 1, 3, 4, 6, 8, 9]
        for idx, dir_name in enumerate(import_files[0].split(os.path.sep)):
            if idx in levels:
                dirs["dir%i" % idx] = dir_name
            else:
                missing_dirs.append("dir%i" % idx)
        for item in self.lib.items():
            self.assertDictContainsSubset(dirs, item)
            for level in missing_dirs:
                self.assertNotIn(level, item)
