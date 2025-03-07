"""
Setup script for the Sitta package.
"""

from setuptools import setup, find_packages

setup(
    name="sitta",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "psycopg>=3.1.12",
        "tqdm>=4.65.0",
    ],
    entry_points={
        "console_scripts": [
            "sitta=sitta.cli:main",
        ],
    },
    author="Danny Wyatt",
    author_email="dannywyatt@gmail.com",
    description="A bird lifer recommendation system",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/dannybirds/ebird_hotspot_recs",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: None",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)