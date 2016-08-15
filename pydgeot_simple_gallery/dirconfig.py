import os
from pydgeot.app import DirConfig as _DirConfig


class DirConfig(_DirConfig):
    _config_key = 'simple_gallery'

    # noinspection PyMissingConstructor
    def __init__(self, app, path):
        """
        :type app: pydgeot.app.App
        :type path: str
        """
        self.app = app
        self.path = path

        self.is_valid = any(processor.name == 'SimpleGallery' for processor in app.get_config(path).processors)
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

        if self.is_valid:
            self._load()

    def _parse(self, config_path, config, parent):
        """
        :type config_path: str
        :type config: dict[str, Any]
        :type parent: DirConfig | None
        """
        config = config.get(DirConfig._config_key, {})

        def _set_option(name, default):
            prop = config.pop(name, None)
            if prop is None:
                prop = default if parent is not None and parent.path == self.app.source_root else getattr(parent, name)
            setattr(self, name, prop)

        def _set_option_path(name, default):
            prop = config.pop(name, None)
            if prop is None and parent is not None and parent.path != self.app.source_root:
                prop = getattr(parent, name)
            else:
                if prop is None:
                    prop = default
                if prop is not None:
                    prop = os.path.realpath(os.path.expanduser(os.path.join(self.path, prop)))
            setattr(self, name, prop)

        _set_option_path('template', '.template.html')
        _set_option('index', 'index.html')
        _set_option('use_symlinks', False)

        _set_option('thumbs', '.thumbs')
        _set_option('thumb_size', (214, 160))
        _set_option_path('thumb_default', None)
