import setuptools

with open('README.md') as fp:
    long_description = fp.read()

setuptools.setup(
    name="fastapi-decorators",
    version="1.0.1",
    author="Anders Brams",
    author_email="anders@brams.dk",
    description="Create decorators that leverage FastAPI's `Depends()` and built-in dependencies, enabling you to inject dependencies directly into your decorators.",
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
    install_requires=[],
    python_requires='>=3',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
