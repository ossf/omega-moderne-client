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
        include_package_data=True,
        classifiers=[
            "Programming Language :: Python :: 3",
        ],
        python_requires='>=3.6',
        install_requires=[
            "gql[all]>=3.4.0",
            "requests>=2.28.2"
        ],
        extras_require={
            "cli": [
                "rich>=11.0.0",
                "rich-argparse>=1.0.0",
                "isodate>=0.6.1",
            ],
            "github-scripts": [
                "croniter>=1.3.8",
                "pytz>=2022",
            ]
        }
    )
