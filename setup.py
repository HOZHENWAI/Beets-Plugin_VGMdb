from setuptools import setup

setup(name="beets-vgmdb",
      version="1.2.0",
      description=" Beets VGMdb metadata plugin and collection manager",
      long_description=open('README.md').read(),
      author= "HO Zhen Wai Olivier",
      author_email="hozhenwai@gmail.com",
      url = "https://github.com/HOZHENWAI/Beets-Plugin_VGMdb",
      platforms='ALL',
      packages=['beetsplug'],
      install_requires=['beets>=1.6.0', 'requests']
      )
