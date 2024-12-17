#!/usr/bin/env python
from setuptools import setup, find_packages


long_description = (
    open('README.md').read()
)

version = '2.0.0'


setup(
    name='bookbook',
    description=(
        'This package that will let the user render several ipynb notebooks into '
        'LaTeX files and a consequent PDF.'
    ),
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/juliusdeane/bookbook',
    license='MIT',
    author='Julius Deane',
    author_email='books@juliusdeane.com',
    packages=find_packages(),
    version=version,
    install_requires=[
        'jsonschema>=4.17.3',
        'nbconvert>=7.16.4',
        'pandoc>=2.4',
        'pandocfilters>=1.5.1',
        'pdflatex>=0.1.3',
        'Jinja2>=3.1.4'
    ],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    zip_safe=False,
    include_package_data=True
)
