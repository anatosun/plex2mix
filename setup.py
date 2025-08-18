from setuptools import setup, find_packages

setup(
    name="plex2mix",
    version="1.0.0",
    description="Download Plex playlists and export them to various formats",
    packages=find_packages(),
    author='Anatosun',
    author_email='z4jyol8l@duck.com',
    url='https://github.com/anatosun/plex2mix',
    include_package_data=True,
    install_requires=[
        "click>=8.0",
        "plexapi>=4.9",
        "pyyaml>=6.0",
    ],
    entry_points={
        'console_scripts': [
            'plex2mix=plex2mix.main:cli',
        ],
    },
    python_requires=">=3.8",
)
