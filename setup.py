import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="libhttpcam",
    version="0.1.3",
    author="Helpful Scripts",
    author_email="helpfulscripts@gmail.com",
    description="Accessing webcams via REST API",
    keywords='http camera foscam wansview',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HelpfulScripts/libhttpcam",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
