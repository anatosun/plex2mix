from setuptools import setup, find_packages

setup(
    name='plex2mix',
    version='0.1.0',
    packages=find_packages(),
    description='Python cli utility to download Plex playlists.',
    author='Anatosun',
    author_email='z4jyol8l@duck.com',
    url='https://github.com/anatosun/plex2mix',
    include_package_data=True,
    install_requires=[
        'Click',
        'click-aliases',
        'PlexAPI',
        'PyYAML',
    ],
    entry_points={
        'console_scripts': [
            'plex2mix = plex2mix.main:cli',
        ],
    },
)
