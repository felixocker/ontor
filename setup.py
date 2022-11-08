#!/usr/bin/env python3
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("./src/ontor/_about.py", "r") as fa:
    about = {}
    exec(fa.read(), about)

setuptools.setup(
    name=about["__name__"],
    version=about["__version__"],
    author=about["__author__"],
    author_email=about["__author_email__"],
    description="ontor - an ontology editor based on Owlready2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=about["__url__"],
    project_urls={
        "Bug Tracker": "https://github.com/felixocker/ontor/issues",
    },
    download_url=about["__download_url__"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    keywords=about["__keywords__"],
    include_package_data=True,  # include non-code files during installation
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[
        "networkx",
        "owlready2",
        "pandas",
        "pyvis==0.1.9",
    ],
)
