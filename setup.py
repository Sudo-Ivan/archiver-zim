from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="archiver-zim",
    version="0.3.6",
    packages=find_packages(),
    install_requires=[
        "yt-dlp>=2025.4.30",
        "python-dateutil>=2.9.0.post0",
        "click>=8.1.8",
        "rich>=14.0.0",
        "libzim>=3.7.0",
        "feedparser>=6.0.11",
        "requests>=2.32.3",
        "pyyaml>=6.0.2",
    ],
    entry_points={
        "console_scripts": [
            "archiver-zim=archiver.cli:main",
        ],
    },
    data_files=[
        ('share/man/man1', [
            'docs/man/man1/archiver-zim.1',
            'docs/man/man1/archiver-zim-archive.1',
            'docs/man/man1/archiver-zim-manage.1',
        ]),
    ],
    author="Sudo-Ivan",
    author_email="",
    description="A tool to download videos from various platforms and create ZIM archives",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Sudo-Ivan/archiver-zim",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10,<3.14",
)
