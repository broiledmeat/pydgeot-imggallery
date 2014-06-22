#!/usr/bin/env python3
from distutils.core import setup

setup(
    name='pydgeot_simple_gallery',
    version='0.2',
    packages=['pydgeot_simple_gallery'],
    requires=['pydgeot', 'jinja2', 'pillow'],
    url='https://github.com/broiledmeat/pydgeot_simple_gallery',
    license='Apache License, Version 2.0',
    author='Derrick Staples',
    author_email='broiledmeat@gmail.com',
    description='Simple image gallery processor for Pydgeot.'
)
