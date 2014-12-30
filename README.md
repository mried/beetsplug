# beetsplug

Here are some plugins I wrote for my personal use. They might not be very
stable so use them at your own risk...

## dirfields
This little plugin adds a field for each directory of its original path to a
media file. For example, if you import the following file:
```
/music/artist/album/01 - track.mp3
```
The following fields will be added to the database entry of this file:
```
dir0: music
dir1: artist
dir2: album
dir3: 01 - track.mp3
```
(OK, `dir3` is not a directory in this case...) Note that the original path is
used, not the one the file might be copied or moved to. This can help you if
your files are already sorted into some directories and you don't want to loose
these folders.

### Configuration
To load the plugin, simply add it to your list of plugins:
```
plugins: dirfields
```

#### Levels
You can configure which directories should be added. To do so, use the `levels`
configuration option. List any directory (zero based) level you want to see
added. Ranges are also allowed. See the example below. The default is not set
so all levels are added.

#### Field renaming
If you don't want the fields to be named `dir4` or so, you can configure other
names as you wish. Just use `dirN` where `N` is the appropriate level as the
configuration key and specify the new name as the value.
**Warning**: You *can* rename them to fields which are already present like
`artist` or so. This might work but is not tested nor intended. It might lead
to confusing results.

#### Example
```
dirfields:
    levels: 8,-1,6,4-3,10-
    dir4: my_section
```

## regexfilefilter
A plugin which allows you to filter the files to import using regular
expressions. The base functionality is added to the `ihate` plugin as of
writing this. The plugin is only here for reference purposes.