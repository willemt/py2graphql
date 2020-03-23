import codecs
from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))


def long_description():
    with codecs.open('README.rst', encoding='utf8') as f:
        description = f.read()
        # Remove graphql specifiers to prevent rst failing to render on pypi
        return description.replace('.. code-block:: graphql', '.. code-block::')


setup(
    name='py2graphql',
    version='0.11.0',

    description='Pythonic GraphQL client',
    long_description=long_description(),

    # The project's main homepage.
    url='https://github.com/willemt/py2graphql',
    author='willemt',
    author_email='himself@willemthiart.com',
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: System :: Logging',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='development',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=['addict', 'requests'],
    package_data={},
    data_files=[],
    entry_points={},
)
