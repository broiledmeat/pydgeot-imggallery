import os
import re
import shutil
import jinja2
from PIL import Image
from pydgeot.processors import register, Processor
from pydgeot.utils.filesystem import is_hidden, create_symlink


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

        if self._get_setting('use_symlinks', False):
            self.copy = create_symlink
        else:
            self.copy = shutil.copy2

        if self.root is not None and self.template is not None:
            self.regex = re.compile('^{0}{1}(.*)$'.format(self.root, os.sep).replace('\\', '\\\\'))
            self.root = os.path.abspath(os.path.join(self.app.source_root, self.root))
            self.build_root = os.path.join(self.app.build_root, os.path.relpath(self.root, self.app.source_root))
            self.template = os.path.abspath(os.path.join(self.app.source_root, self.template))

        self.is_valid = os.path.isdir(self.root) and os.path.isfile(self.template)

        if self.is_valid:
            self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.app.source_root))
            self._generate_dirs = []

    def can_process(self, path):
        return self.is_valid and self.regex.search(os.path.relpath(path, self.app.source_root)) is not None

    def process_update(self, path):
        if path == self.template:
            walk = list(os.walk(self.root))
            dirs = [path for path, dirs, files in walk if not is_hidden(path)]
            dirs.append(self.root)
            for dir in dirs:
                if dir not in self._generate_dirs:
                    self._generate_dirs.append(dir)
            return []
        if is_hidden(path) or os.path.basename(path) == self.index:
            return []

        rel = os.path.relpath(path, self.app.source_root)
        parent = os.path.dirname(path)
        target = os.path.join(self.app.build_root, rel)
        target_dir = os.path.dirname(target)
        target_parent = os.path.split(target_dir)[0]
        if not os.path.exists(target_parent) and parent not in self._generate_dirs:
            self._generate_dirs.append(parent)

        os.makedirs(target_dir, exist_ok=True)
        self.copy(path, target)
        targets = [target]

        # Generate thumbnail
        thumb = self._generate_thumbnail(path)
        if thumb is not None:
            targets.append(thumb)

        dir = os.path.dirname(path)
        if dir not in self._generate_dirs:
            self._generate_dirs.append(dir)

        return targets

    def process_delete(self, path):
        dir = os.path.dirname(path)
        if dir not in self._generate_dirs:
            self._generate_dirs.append(dir)
        super().process_delete(path)
        if dir is not self.root and not os.path.exists(dir):
            parent = os.path.split(dir)[0]
            if parent not in self._generate_dirs:
                self._generate_dirs.append(parent)

    def process_changes_complete(self):
        if not self.is_valid:
            return
        for directory in self._generate_dirs:
            self._generate_index(directory)

    def _generate_index(self, directory):
        if not os.path.isdir(directory):
            return
        dirs = []
        files = []
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if is_hidden(path) or path == self.template:
                continue
            elif os.path.isfile(path):
                files.append(path)
            elif os.path.isdir(path):
                dirs.append(path)

        dirs = self._contextify_file_list(directory, dirs)
        files = self._contextify_file_list(directory, files)

        rel = os.path.relpath(directory, self.app.source_root)
        target = os.path.join(self.app.build_root, rel)
        os.makedirs(target, exist_ok=True)
        content = open(self.template).read()
        template = self.env.from_string(content)
        f = open(os.path.join(target, self.index), 'w', encoding='utf-8')
        rendered = template.render(
            dir_name=os.path.basename(directory),
            has_parent_dir=(directory != self.root),
            dirs=dirs,
            files=files)
        f.write(rendered)
        f.close()

    def _contextify_file_list(self, root, files):
        for file in files:
            thumb = self._get_thumbnail(file)
            if thumb is not None:
                rel_thumb = os.path.relpath(thumb, self.app.build_root)
                rel_root = os.path.relpath(root, self.app.source_root)
                thumb = os.path.relpath(rel_thumb, rel_root)
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
        if os.path.splitext(path)[1].lower() in self.thumbable_exts:
            target = self._thumbnail_path(path)
            try:
                image = Image.open(path)
                image.thumbnail((self.max_width, self.max_height), Image.ANTIALIAS)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                image.save(target)
                return target
            except:
                pass
        return None

    def _get_setting(self, name, default=None):
        if self.key_name not in self.app.settings:
            self.app.settings[self.key_name] = {}
        if name not in self.app.settings[self.key_name]:
            return default
        return self.app.settings[self.key_name][name]
