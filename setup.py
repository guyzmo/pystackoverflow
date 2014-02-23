from setuptools import setup
import os
import sys


def read(*names):
    values = dict()
    for name in names:
        if os.path.isfile(name):
            value = open(name).read()
        else:
            value = ''
        values[name] = value
    return values

long_description = """

%(README.rst)s

""" % read('README.rst')

setup(name='pystackoverflow',
      version='1.2',
      description="Tool to use Stack Overflow services from CLI",
      long_description=long_description,
      classifiers=[
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Operating System :: Unix',
      ],
      keywords='stackoverflow api openid',
      author='Bernard `Guyzmo` Pratz',
      author_email='stackoverflow@m0g.net',
      url='http://m0g.net',
      license='GPLv3',
      packages=['stackoverflow'],
      zip_safe=False,
      data_files=[('config', ['etc/so-config.ini'])],
      install_requires=[
          'BeautifulSoup',
          'requests',
          'argparse',
          'setuptools',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      sotool = stackoverflow.cli:run
      """,
      )

if "install" in sys.argv:
    print """
Stack Overflow CLI Tool is now installed!
"""
