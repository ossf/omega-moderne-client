#!/usr/bin/env python

import setuptools

if __name__ == "__main__":
    setuptools.setup(
        name="omega-moderne-client",
        version="0.0.1",
        author="Jonathan Leitschuh",
        author_email="Jonathan.Leitschuh@linuxfoundation.org",
        description="A client for the Omega Moderne service.",
        long_description=open("README.md").read(),
        long_description_content_type="text/markdown",
        url="https://github.com/ossf/omega-moderne-client",
        packages=setuptools.find_packages(),
        classifiers=[
            "Programming Language :: Python :: 3",
        ],
        python_requires='>=3.6',
        install_requires=[
          "gql[all]>=3.4.0"
        ],
    )
