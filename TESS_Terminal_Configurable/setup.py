#!/usr/bin/env python3
"""
Setup script for TESS Terminal Configurable Edition.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
req_path = Path(__file__).parent / "requirements.txt"
requirements = []
if req_path.exists():
    with open(req_path) as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith("#")
        ]

setup(
    name="tess-terminal-configurable",
    version="1.0.0",
    description="A configurable terminal AI agent with interactive setup",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="TESS Configurable Edition",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "tess=tess_configurable.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
        "Topic :: System :: Systems Administration",
    ],
    keywords="ai agent automation cli terminal assistant",
    project_urls={
        "Source": "https://github.com/yourusername/tess-configurable",
    },
)
