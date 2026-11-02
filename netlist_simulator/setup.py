"""
Setup configuration for Circuit Simulator package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="circuit-simulator",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Automatic SPICE circuit simulator and plotter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/circuit-simulator",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PySpice>=1.5",
        "matplotlib>=3.5.0",
        "numpy>=1.20.0",
    ],
    extras_require={
        "yaml": ["PyYAML>=6.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "circuit-sim=circuit_simulator.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "circuit_simulator": ["examples/*.cir"],
    },
)
