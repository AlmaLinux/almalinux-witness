import setuptools


with open("README.md", "r", encoding="utf-8") as fd:
    long_description = fd.read()


setuptools.setup(
    name="almawitness",
    version="0.0.1",
    author="Eugene Zamriy",
    author_email="ezamriy@almalinux.org",
    description="AlmaLinux OS monitoring project",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AlmaLinux/almalinux-witness",
    project_urls={
        "Bug Tracker": "https://github.com/AlmaLinux/almalinux-witness/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
