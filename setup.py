"""Setup script for Jupyter Kernel Wrapper."""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from __init__.py
version = {}
with open("kernel_wrapper/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            exec(line, version)

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

setup(
    name="jupyter-kernel-wrapper",
    version=version.get("__version__", "0.2.0"),
    description="A Jupyter kernel that wraps other kernels with jumper_extension support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/jupyter-kernel-wrapper",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'kernel_wrapper': ['kernelspec/kernel.json'],
    },
    install_requires=[
        "ipykernel>=6.0.0",
        "jupyter-client>=7.0.0",
        "jumper-extension>=0.1.0",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Framework :: Jupyter",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        'console_scripts': [
            'install-kernel-wrapper=kernel_wrapper.install:main',
        ],
    },
)
