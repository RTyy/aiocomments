from setuptools import find_packages, setup


install_requires = ['aiofiles',
                    'aiohttp',
                    'aiopg[sa]',
                    'aiohttp-jinja2',
                    'lxml',
                    'trafaret-config']


setup(name='aiocomments',
      version='0.0.1',
      description='Comments server based on aiohttp',
      platforms=['POSIX'],
      packages=find_packages(),
      package_data={
          '': ['templates/*.html', 'static/*.*']
      },
      include_package_data=True,
      install_requires=install_requires,
      zip_safe=False)
