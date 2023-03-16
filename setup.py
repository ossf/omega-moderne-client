#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="omega-moderne-client",
    version="0.0.1",
    author="Jonathan Leitschuh",
    author_email="Jonathan.Leitschuh@linuxfoundation.org",
    description="A client for the Omega Moderne service.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ossf/omega-moderne-client",
    package_dir={'': 'src'},
    packages=find_packages(where="src"),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.9',
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
    },
    entry_points={
        "console_scripts": [
            "omega-moderne-client=omega_moderne_client.__main__:cli",
        ],
    },
)
