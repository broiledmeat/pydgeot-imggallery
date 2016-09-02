import os
import datetime
import shutil
from pydgeot.processors import register, Processor
from pydgeot.filesystem import is_hidden, create_symlink


@register(name='simple_gallery')
class SimpleGalleryProcessor(Processor):
    config_key = 'simple_gallery'

    def __init__(self, app):
        """
        :param app: Parent App instance.
        :type app: pydgeot.app.App
        """
        import jinja2

        super().__init__(app)
        self._env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.app.source_root))
        self._generate_files = set()
        self._generate_directories = set()

    def can_process(self, path):
        from .dirconfig import DirConfig

        config = DirConfig.get(self.app, path)
        return config.is_valid

    def prepare(self, path):
        from .dirconfig import DirConfig

        config = DirConfig.get(self.app, path)
        if not config.is_valid:
            return

        if os.path.basename(path) == os.path.basename(config.template):
            self.app.sources.add_source(path)
            path_dir = os.path.dirname(path)
            walk = list(os.walk(path_dir))
            directories = [path for path, dirs, files in walk if not is_hidden(path)]
            directories.append(path_dir)
            for directory in directories:
                self._generate_directories.add(directory)
            return

        self.app.sources.add_source(path)
        if not os.path.basename(path) == config.index:
            target_path = self.app.target_path(path)
            directory = os.path.dirname(path)

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
            self._generate_directories.add(directory)

            parent_config = DirConfig.get(self.app, os.path.dirname(config.path))
            if parent_config.is_valid:
                target_directory = self.app.target_path(os.path.dirname(path))
                if not os.path.exists(target_directory):
                    self._generate_directories.add(parent_config.path)

    def generate(self, path):
        from .dirconfig import DirConfig

        if path in self._generate_files:
            config = DirConfig.get(self.app, path)
            if not config.is_valid:
                return

            target_path = self.app.target_path(path)

            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            if config.use_symlinks:
                create_symlink(path, target_path)
            else:
                shutil.copy2(path, target_path)

            # Generate thumbnail
            thumb_path = self._generate_thumbnail(config, path)
            if thumb_path is not None:
                self.app.sources.set_targets(path, [target_path, thumb_path])

    def delete(self, path):
        from .dirconfig import DirConfig

        directory = os.path.dirname(path)
        self._generate_directories.add(directory)

        super().delete(path)

        parent_path = os.path.dirname(directory)
        parent_config = DirConfig.get(self.app, parent_path)
        if parent_config.is_valid:
            self._generate_directories.add(parent_config.path)

    def generation_complete(self):
        for directory in self._generate_directories:
            self._generate_index(directory)
        self._generate_files.clear()
        self._generate_directories.clear()

    def _generate_index(self, directory):
        from .dirconfig import DirConfig

        config = DirConfig.get(self.app, directory)
        if not config.is_valid:
            return

        self.app.log.info('Generating index for \'{}\''.format(directory))

        directories = []
        files = []
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if is_hidden(path) or os.path.basename(path) == os.path.basename(config.template):
                continue
            elif os.path.isfile(path):
                files.append(path)
            elif os.path.isdir(path):
                directories.append(path)

        directories = self._contextify_file_list(config, directory, directories)
        files = self._contextify_file_list(config, directory, files)

        target_directory = self.app.target_path(directory)
        target_path = os.path.join(target_directory, config.index)

        os.makedirs(target_directory, exist_ok=True)

        content = open(config.template).read()
        template = self._env.from_string(content)
        f = open(target_path, 'w', encoding='utf-8')
        rendered = template.render(
            config=config,
            dir_name=os.path.basename(directory),
            has_parent_dir=(directory != self.app.source_root),
            dirs=directories,
            files=files)
        f.write(rendered)
        f.close()

    def _contextify_file_list(self, config, root, files):
        """
        :type config: .dirconfig.DirConfig
        :type root: str
        :type files: list[str]
        :rtype: dict[str, dict[str, Any]]
        """
        contexts = []
        for file in files:
            data = {
                'filename': os.path.basename(file),
                'date': 0
            }
            thumb = self._get_thumbnail(config, file)
            if thumb is not None:
                rel_thumb = os.path.relpath(thumb, self.app.build_root)
                rel_root = os.path.relpath(root, self.app.source_root)
                data['thumbname'] = os.path.relpath(rel_thumb, rel_root)
            for result in self.app.contexts.get_contexts(source=file):
                data[result.name] = result.value
            contexts.append(data)
        return contexts

    def _thumbnail_path(self, config, path):
        """
        :type config: .dirconfig.DirConfig
        :type path: str
        :rtype: str
        """
        return os.path.abspath(os.path.join(self.app.target_path(os.path.dirname(path)), config.thumbs,
                                            os.path.basename(path)))

    def _get_thumbnail(self, config, path):
        """
        :type config: .dirconfig.DirConfig
        :type path: str
        :rtype: str
        """
        thumb_path = self._thumbnail_path(config, path)
        if os.path.isfile(thumb_path):
            return thumb_path
        return config.thumb_default

    def _generate_thumbnail(self, config, path):
        """
        :type config: .dirconfig.DirConfig
        :type path: str
        """
        import imghdr

        if imghdr.what(path) is not None:
            from PIL import Image

            target = self._thumbnail_path(config, path)
            try:
                image = Image.open(path)
                image.thumbnail(config.thumb_size, Image.ANTIALIAS)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                image.save(target)
                return target
            except IOError:
                pass
        return None

    @staticmethod
    def _get_exif_data(path):
        from PIL import Image, ExifTags

        exif_data = {}
        try:
            image = Image.open(path)
            raw_data = image._getexif() if hasattr(image, '_getexif') else None
            if raw_data is not None:
                for id_, value in raw_data.items():
                    name = ExifTags.TAGS[id_] if id_ in ExifTags.TAGS else id_
                    exif_data[name] = value
        except OSError:
            pass
        return exif_data
