from setuptools import setup, find_packages

setup(
    name="lgr",
    version="0.1.3",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "django",
        "django-auth-ldap",
        "djangorestframework",
        "django-filter",
        "mysqlclient",
        "django-nose",
        "coverage",
    ],
    entry_points={"console_scripts": ["lgr=lgr.manage:main"],},
)
