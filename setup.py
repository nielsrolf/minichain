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
        "click",
        "python-dotenv",
        "openai",
        "replicate",
        "retry",
        "google-search-results",
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
