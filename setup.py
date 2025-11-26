from setuptools import setup, find_packages
from pathlib import Path

# Read version from __init__.py
version = {}
with open(Path(__file__).parent / "plex2mix" / "__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            exec(line, version)
            break

setup(
    name="plex2mix",
    version=version["__version__"],
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
