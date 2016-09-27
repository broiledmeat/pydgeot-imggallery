#!/usr/bin/env python3
from distutils.core import setup


setup(
    name='pydgeot_simple_gallery',
    description='Simple image gallery processor for Pydgeot.',
    url='https://github.com/broiledmeat/pydgeot_simple_gallery',
    license='Apache License, Version 2.0',
    author='Derrick Staples',
    author_email='broiledmeat@gmail.com',
    version='0.4',
    packages=['pydgeot.plugins.simple_gallery'],
    requires=['pydgeot', 'jinja2', 'pillow'],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup'
    ]
)
