import os
import re
import shutil
import pystacia
import jinja2
from pydgeot.processors import register, Processor

@register()
class ImgGalleryProcessor(Processor):
    priority = 100
    key_name = 'imggallery'
    thumb_dir = '.thumbs'
    def __init__(self, app):
        super().__init__(app)
        self.root = self._get_setting('directory')
        self.template = self._get_setting('template')
        self.index = self._get_setting('index', 'index.html')
        self.default_thumb = self._get_setting('default_thumb', None)
        self.thumbable_exts = self._get_setting('thumbable_exts', ['.jpg', '.jpeg', '.gif', '.png'])
        self.ext_thumbs = self._get_setting('ext_thumbs', {})
        self.max_width = self._get_setting('width', 214)
        self.max_height = self._get_setting('height', 160)

        if self.root is not None and self.template is not None:
            self.regex = re.compile('^{0}{1}(.*)$'.format(self.root, os.sep).replace('\\', '\\\\'))
            self.root = os.path.abspath(os.path.join(self.app.content_root, self.root))
            self.build_root = os.path.join(self.app.build_root, os.path.relpath(self.root, self.app.content_root))
            self.template = os.path.abspath(os.path.join(self.app.content_root, self.template))

        self.is_valid = os.path.isdir(self.root) and os.path.isfile(self.template)

        if self.is_valid:
            self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.app.content_root))
            self._generate_dirs = {}


    def can_process(self, path):
        return self.is_valid and self.regex.search(os.path.relpath(path, self.app.content_root)) is not None

    def process_update(self, path):
        if path == self.template:
            walk = list(os.walk(self.root))
            dirs = [path for path, dirs, files in walk if not self._is_hidden(path)]
            dirs.append(self.root)
            for dir in dirs:
                if dir not in self._generate_dirs:
                    self._generate_dirs[dir] = []
            return []
        if self._is_hidden(path):
            return []

        # Copy original
        rel = os.path.relpath(path, self.app.content_root)
        target = os.path.join(self.app.build_root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(path, target)
        targets = [target]

        # Generate thumbnail
        thumb = self._generate_thumbnail(path)
        if thumb is not None:
            targets.append(thumb)

        dir = os.path.dirname(path)
        if dir not in self._generate_dirs:
            self._generate_dirs[dir] = []

        return targets

    def process_delete(self, path):
        dir = os.path.dirname(path)
        if dir not in self._generate_dirs:
            self._generate_dirs[dir] = []
        self._generate_dirs[dir].append(path)

    def process_changes_complete(self):
        for directory, excludes in self._generate_dirs.items():
            self._generate_index(directory, excludes)

    def _generate_index(self, directory, exclude=None):
        dirs = []
        files = []
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if self._is_hidden(path) or path in exclude or path == self.template:
                continue
            elif os.path.isfile(path):
                files.append(path)
            elif os.path.isdir(path):
                dirs.append(path)

        dirs = self._contextify_file_list(directory, dirs)
        files = self._contextify_file_list(directory, files)

        rel = os.path.relpath(directory, self.app.content_root)
        target = os.path.join(self.app.build_root, rel)
        os.makedirs(target, exist_ok=True)
        content = open(self.template).read()
        template = self.env.from_string(content)
        f = open(os.path.join(target, self.index), 'w')
        f.write(template.render(
            has_parent_dir=(directory != self.root),
            dirs=dirs,
            files=files))
        f.close()

    def _contextify_file_list(self, root, files):
        for file in files:
            thumb = self._get_thumbnail(file)
            if thumb is not None:
                thumb = os.path.relpath(thumb, root)
            yield (os.path.basename(file), thumb)

    def _thumbnail_path(self, path):
        rel = os.path.relpath(path, self.root)
        dir = os.path.dirname(rel)
        file = os.path.basename(rel)
        return os.path.abspath(os.path.join(self.build_root, dir, self.thumb_dir, file))

    def _get_thumbnail(self, path):
        thumb = self._thumbnail_path(path)
        if os.path.isfile(thumb):
            return thumb
        ext = os.path.splitext(path)[1]
        if ext in self.ext_thumbs:
            return self.ext_thumbs[ext]
        return self.default_thumb

    def _generate_thumbnail(self, path):
        if os.path.splitext(path)[1] in self.thumbable_exts:
            target = self._thumbnail_path(path)
            image = None
            try:
                image = pystacia.read(path)
                if image.width > self.max_width or image.height > self.max_height:
                    ratio = min(self.max_width / image.width, self.max_height / image.height)
                    image.rescale(int(ratio * image.width), int(ratio * image.height))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                image.write(target)
                return target
            except:
                pass
            finally:
                if image is not None:
                    image.close()
        return None

    def _is_hidden(self, path):
        if os.path.basename(path).lower() == 'thumbs.db':
            return True
        rel = os.path.relpath(path, self.root)
        parts = rel.split(os.sep)
        return any([part != '..' and part.startswith('.') for part in parts])

    def _get_setting(self, name, default=None):
        if self.key_name not in self.app.settings:
            self.app.settings[self.key_name] = {}
        if name not in self.app.settings[self.key_name]:
            return default
        return self.app.settings[self.key_name][name]