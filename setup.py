import setuptools

with open('README.md') as fp:
    long_description = fp.read()

setuptools.setup(
    name="fastapi-decorators",
    version="0.0.3",
    author="Anders Brams",
    author_email="anders@brams.dk",
    description="Decorate FastAPI endpoints with custom decorators.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=[
        "fastapi",
        "decorators",
        "middleware",
        "dependency",
        "dependencies",
    ],
    url="https://github.com/Minibrams/fastapi-decorators",
    packages=setuptools.find_packages(where='src'),
    package_dir={
        '': 'src'
    },
    install_requires=[
        "fastapi",
    ],
    python_requires='>=3',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
