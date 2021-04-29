#!/usr/bin/env python3
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ontor",
    version="0.0.1",
    author="Felix Ocker",
    author_email="felix.ocker@googlemail.com",
    description="ontor - an ontology editor based on Owlready2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/felixocker/ontor",
    project_urls={
        "Bug Tracker": "https://github.com/felixocker/ontor/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "ontor"},
    packages=setuptools.find_packages(where="ontor"),
    python_requires=">=3.8",
)

