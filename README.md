# Simple Gallery for Pydgeot
A plugin for [Pydgeot](http://www.github.com/broiledmeat/pydgeot) to generate thumbnails and indexes for a directory and
its subdirectories.

### Features
- Generate and update indexes for files in a directory (and its children.)
- Generate and update thumbnails for images.
- Template support.
- Not a whole lot else.

### Requirements
- Python 3.*
- [Pydgeot](http://www.github.com/broiledmeat/pydgeot)
- [Jinja2](https://github.com/mitsuhiko/jinja2)
- [Pillow](http://python-pillow.github.io/)

### Installation
```bash
git clone https://github.com/broiledmeat/pydgeot_simple_gallery.git pydgeot_simple_gallery
cd pydgeot_simple_gallery
python setup.py install
```

### Configuration
Add `simple_gallery` to your pydgeot.conf `plugins` list. Simple Gallery looks for options under a `simple_gallery` key.
- `template` Relative path (to the first parent directory to use the processor) to a Jinja template to use for index pages. _Default: .template.html_
- `index` Filename to generate the index as. _Default: index.html_
- `thumb_size` Maximum width and height for generated thumbnails, as a two element list. _Default: [214, 160]_
- `thumb_default` Path to thumbnail image to use when no thumb can be generated. _Default: None_
- `use_symlinks` Create symlinks for original files instead of copying them over to the build directory. _Default: False_

```json
{
    "plugins": ["simple_gallery"],
    "processors": ["simple_gallery"],
    "simple_gallery": {
        "directory": "mygallery",
        "use_symlinks": true
    }
}
```

### Template Variables
- `dir_name` Name of the indexed directory.
- `has_parent_dir` If this index is a child of the root index.
- `dirs` List of file information for directories in the indexed directory.
- `files` List of file information for files in the indexed directory.

File information for directories and files are dictionaries with the following members:
- `filename` Name of the directory or file.
- `date` Modified date. Exif data will be used if available.
- `thumbname` Name of the thumbnail for this directory or file. The key does not exist if there is no thumbnail.
- Any exif data properties.
