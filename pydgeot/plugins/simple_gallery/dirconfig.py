import os
from pydgeot.app.dirconfig import BaseDirConfig


class DirConfig(BaseDirConfig):
    _config_key = 'simple_gallery'
    _default_config = {
        'template': '.template.html',
        'index': 'index.html',
        'use_symlinks': False,
        'thumbs': '.thumbs',
        'thumb_size': (214, 160),
        'thumb_default': None
    }

    # noinspection PyMissingConstructor
    def __init__(self, app, path):
        """
        :type app: pydgeot.app.App
        :type path: str
        """
        from .processor import SimpleGalleryProcessor

        self.is_valid = any(processor.name == SimpleGalleryProcessor.name
                            for processor in app.get_config(path).processors)
        """:type: bool"""
        self.template = None
        """:type: str | None"""
        self.index = None
        """:type: str | None"""
        self.thumbs = None
        """:type: str | None"""
        self.thumb_size = None
        """:type: list[int] | tuple[int, int] | None"""
        self.thumb_default = None
        """:type: str | None"""
        self.use_symlinks = False
        """:type: bool"""

        super().__init__(app, path)

    def _parse(self, config_path, config, parent):
        """
        :type config_path: str
        :type config: dict[str, Any]
        :type parent: DirConfig | None
        """
        config = config.get(DirConfig._config_key, {})

        for name in ('index', 'use_symlinks', 'thumbs', 'thumb_size'):
            value = config.pop(name, None)
            if value is None:
                value = self._default_config.get(name) if parent is None else getattr(parent, name)
            setattr(self, name, value)

        for name in ('template', 'thumb_default'):
            value = config.pop(name, None)
            if value is None and parent is not None and parent.path != self.app.source_root:
                value = getattr(parent, name)
            else:
                if value is None:
                    value = self._default_config.get(name)
                if value is not None:
                    value = os.path.realpath(os.path.expanduser(os.path.join(self.path, value)))
            setattr(self, name, value)
