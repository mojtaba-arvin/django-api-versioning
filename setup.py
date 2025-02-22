from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="django-api-versioning",
    version="0.1.3",
    author="Mojtaba Arvin",
    author_email="ArvinDevDay@gmail.com",
    description= (
    "Django API versioning decorator provides a solution "
    "for managing multiple API versions within "
    "the Django framework, enabling versioning "
    "through URLs with backward compatibility "
    "and automatically registering routes."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mojtaba-arvin/django-api-versioning",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "Django>=3.2",
    ],
    extras_require={
        "dev": [
            "black>=22.0.0",
            "flake8>=4.0.0",
            "isort>=5.0.0",
            "mypy>=0.900",
            "pytest>=6.0",
            "pytest-django>=4.0",
            "pytest-cov>=3.0.0",
            "pre-commit>=2.0.0",
            "twine>=4.0.0",
            "build>=0.8.0",
        ],
    },
    include_package_data=True,
    package_data={
        '': ['.pre-commit-config.yaml'],
    },
)