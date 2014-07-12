import os
import re
import datetime
import shutil
import jinja2
from PIL import Image, ExifTags
from pydgeot.processors import register, Processor
from pydgeot.utils.filesystem import is_hidden, create_symlink


@register()
class SimpleGalleryProcessor(Processor):
    priority = 100
    key_name = 'pydgeot_simple_gallery'
    thumb_dir = '.thumbs'

    def __init__(self, app):
        super().__init__(app)
        self.root = self._get_setting('directory')
        self.template = self._get_setting('template', '.template.html')
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
            self.root = self.app.source_path(self.root)
            self.build_root = self.app.target_path(self.root)

        self.is_valid = self._get_template(self.root) is not None

        if self.is_valid:
            self._env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.app.source_root))
            self._generate_directories = set()
            self._generate_files = set()

    def can_process(self, path):
        return self.is_valid and self.regex.search(os.path.relpath(path, self.app.source_root)) is not None

    def prepare(self, path):
        if os.path.basename(path) == os.path.basename(self.template):
            self.app.sources.add_source(path)
            path_dir = os.path.dirname(path)
            walk = list(os.walk(path_dir))
            directories = [path for path, dirs, files in walk if not is_hidden(path)]
            directories.append(path_dir)
            for directory in directories:
                self._generate_directories.add(directory)
            return

        self.app.sources.add_source(path)
        if not is_hidden(path) and not os.path.basename(path) == self.index:
            target_path = self.app.target_path(path)
            path_dir = os.path.dirname(path)

            self.app.sources.set_targets(path, [target_path])
            exif_data = self._get_exif_data(path)
            for name, value in exif_data.items():
                self.app.contexts.add_context(path, name, str(value))
            taken_date = datetime.datetime.fromtimestamp(os.stat(path).st_ctime)
            for name in ('DateTime', 'DateTimeOriginal', 'DateTimeDigitized'):
                if name in exif_data:
                    taken_date = datetime.datetime.strptime(exif_data[name], '%Y:%m:%d %H:%M:%S')
            self.app.contexts.add_context(path, 'date', taken_date)

            self._generate_files.add(path)
            self._generate_directories.add(path_dir)

            if path_dir != self.root:
                parent_directory = os.path.split(path_dir)[0]
                target_directory = self.app.target_path(os.path.dirname(path))
                if not os.path.exists(target_directory):
                    self._generate_directories.add(parent_directory)

    def generate(self, path):
        if path in self._generate_files:
            target_path = self.app.target_path(path)

            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            self.copy(path, target_path)

            # Generate thumbnail
            thumb_path = self._generate_thumbnail(path)
            if thumb_path is not None:
                self.app.sources.set_targets(path, [target_path, thumb_path])

    def delete(self, path):
        directory = os.path.dirname(path)
        self._generate_directories.add(directory)

        super().delete(path)

        if directory != self.root:
            parent = os.path.split(directory)[0]
            self._generate_directories.add(parent)

    def generation_complete(self):
        if not self.is_valid:
            return
        for directory in self._generate_directories:
            self._generate_index(directory)

    def _generate_index(self, directory):
        directories = []
        files = []
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if is_hidden(path) or os.path.split(path)[1] == os.path.basename(self.template):
                continue
            elif os.path.isfile(path):
                files.append(path)
            elif os.path.isdir(path):
                directories.append(path)

        directories = self._contextify_file_list(directory, directories)
        files = self._contextify_file_list(directory, files)

        target_directory = self.app.target_path(directory)
        target_path = os.path.join(target_directory, self.index)

        os.makedirs(target_directory, exist_ok=True)

        content = open(self._get_template(directory)).read()
        template = self._env.from_string(content)
        f = open(target_path, 'w', encoding='utf-8')
        rendered = template.render(
            dir_name=os.path.basename(directory),
            has_parent_dir=(directory != self.root),
            dirs=directories,
            files=files)
        f.write(rendered)
        f.close()

    def _get_template(self, directory):
        while True:
            filename = os.path.join(directory, os.path.basename(self.template))
            if os.path.isfile(filename):
                return filename
            if directory == self.root:
                return None
            directory = os.path.split(directory)[0]

    def _contextify_file_list(self, root, files):
        contexts = []
        for file in files:
            data = {
                'filename': os.path.basename(file),
                'date': 0
            }
            thumb = self._get_thumbnail(file)
            if thumb is not None:
                rel_thumb = os.path.relpath(thumb, self.app.build_root)
                rel_root = os.path.relpath(root, self.app.source_root)
                data['thumbname'] = os.path.relpath(rel_thumb, rel_root)
            for result in self.app.contexts.get_contexts(source=file):
                data[result.name] = result.value
            contexts.append(data)
        return contexts

    def _thumbnail_path(self, path):
        rel = os.path.relpath(path, self.root)
        directory = os.path.dirname(rel)
        file = os.path.basename(rel)
        return os.path.abspath(os.path.join(self.build_root, directory, self.thumb_dir, file))

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
            except IOError:
                pass
        return None

    @staticmethod
    def _get_exif_data(path):
        exif_data = {}
        try:
            image = Image.open(path)
            raw_data = image._getexif() if hasattr(image, '_getexif') else None
            if raw_data is not None:
                for id, value in raw_data.items():
                    name = ExifTags.TAGS[id] if id in ExifTags.TAGS else id
                    exif_data[name] = value
        except OSError:
            pass
        return exif_data

    def _get_setting(self, name, default=None):
        if self.key_name not in self.app.settings:
            self.app.settings[self.key_name] = {}
        if name not in self.app.settings[self.key_name]:
            return default
        return self.app.settings[self.key_name][name]
