#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    "requests",
    "pygithub>=1.43.3",
    "click",
    "tqdm",
    "pyyaml>=4.2b4",
    "packaging",
    "python-gitlab>=1.3.0",
    "dparse>=0.5.1",
    "safety>=1.9.0",
    "jinja2>=2.3"
]

setup(
    name='pyupio',
    version='1.1.2',
    description="A tool to update all your projects requirements",
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/x-rst',
    author="Jannis Gebauer",
    author_email='support@pyup.io',
    url='https://github.com/pyupio/pyup',
    packages=[
        'pyup',
        'pyup.providers'
    ],
    package_dir={'pyup':
                 'pyup'},
    include_package_data=True,
    install_requires=requirements,
    license="MIT",
    zip_safe=False,
    keywords='pyup',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python",
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    python_requires=">=3.5",
    entry_points={
        'console_scripts': [
            'pyup = pyup.cli:main',
        ]
    }
)
