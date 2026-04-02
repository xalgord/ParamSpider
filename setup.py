from setuptools import setup, find_packages
from pathlib import Path

setup(
    name='paramspider',
    version='0.1.1',
    author='Devansh Batham',
    author_email='devanshbatham009@gmail.com',
    description='Mining parameters from dark corners of Web Archives',
    packages=find_packages(),
    install_requires=[
        'requests',
        'colorama',
        'python-dotenv'
    ],
    entry_points={
        'console_scripts': [
            'paramspider = paramspider.main:main'
        ]
    },
    python_requires='>=3.7',
    license='MIT',
    long_description=Path('README.md').read_text(encoding='utf-8'),
    long_description_content_type='text/markdown'
)
