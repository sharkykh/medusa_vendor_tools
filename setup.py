from setuptools import find_packages, setup

from mvt import __version__

try:
    from pathlib import Path
    readme_path = Path(__file__).with_name('readme.md')
    long_description = readme_path.read_text()
except ImportError:
    long_description = None

setup(
    name='mvt',
    version=__version__,
    description='medusa_vendor_tools :: Tools for dealing with the vendored libraries and requirement lists in pymedusa/Medusa',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/sharkykh/medusa_vendor_tools',
    author='sharkykh',
    author_email=None,
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: MIT License',
    ],
    packages=find_packages(),
    include_package_data=False,
    python_requires='>=3.7.0',
    install_requires=[
        'pip >=19.1.1',
        'requests >=2.18.4,<3.0.0',
        'setuptools >=41.0.0',
    ],
    entry_points={
        'console_scripts': [
            'mvt = mvt.__main__:main',
        ],
    },
)
