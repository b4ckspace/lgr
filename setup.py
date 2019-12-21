from setuptools import setup

setup(
    name='lgr',
    version='0.1.3',
    packages=['lgr'],
    include_package_data=True,
    install_requires=[
        'django',
        'django-auth-ldap',
        'djangorestframework',
        'django-filter',
        'mysqlclient',
        'django-nose',
        'coverage',
    ],
    entry_points={
        'console_scripts': [
            'lgr=lgr.manage:main'
        ],
    },
)
