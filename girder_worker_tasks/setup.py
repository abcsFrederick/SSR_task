from setuptools import setup

setup(name='ssr_tasks',
      version='0.1.0',
      description='A girder_worker extension with ssr task examples',
      author='Kitware Inc.',
      author_email='kitware@kitware.com',
      license='Apache v2',
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'License :: OSI Approved :: Apache Software License'
          'Natural Language :: English',
          'Programming Language :: Python'
      ],
      entry_points={
          'girder_worker_plugins': [
              'ssr_tasks = ssr_tasks:SSRTasksGirderWorkerPlugin',
          ]
      },
      install_requires=[
          'girder_worker',
          'numpy',
          'shapely',
          'pyvips',
          'pillow'
      ],
      packages=['ssr_tasks'],
      zip_safe=False)
