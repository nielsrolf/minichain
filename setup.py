from setuptools import find_packages, setup

setup(
    name="minichain",
    version=0.1,
    description="utils for agi",
    license="Apache 2.0",
    packages=find_packages(),
    package_data={},
    scripts=[],
    install_requires=[
        "click==8.1.6",
        "python-dotenv==1.0.0",
        "openai==0.27.8",
        "replicate==0.9.0",
        "html2text==2020.1.16",
        "retry==0.9.2",
        "google-search-results==2.4.2",
        "duckduckgo_search==3.8.4",
        "playwright==1.36.0",
        "numpy",
    ],
    extras_require={
        "test": [
            "pytest",
            "pylint!=2.5.0",
            "black",
            "mypy",
            "flake8",
            "pytest-cov",
            "httpx",
        ],
    },
    entry_points={
        "console_scripts": [],
    },
    classifiers=[],
    tests_require=["pytest"],
    setup_requires=["pytest-runner"],
    keywords="",
)
