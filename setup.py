from setuptools import setup, find_packages

setup(
    name='plex2mix',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'PlexAPI',
        'PyYAML',
    ],
    entry_points={
        'console_scripts': [
            'plex2mix = plex2mix.main:cli',
        ],
    },
)
