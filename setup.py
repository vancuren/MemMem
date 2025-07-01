"""Setup script for MemoryBank SDK."""

from setuptools import setup, find_packages

# This file is kept for compatibility with older pip versions
# The actual configuration is in pyproject.toml

setup(
    name="memorybank",
    use_scm_version=False,
    packages=find_packages(),
    python_requires=">=3.8",
)