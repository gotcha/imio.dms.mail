#! -*- coding: utf8 -*-

from setuptools import setup, find_packages

version = '2.0.dev0'

long_description = (
    open('README.rst').read()
    + '\n' +
    'Contributors\n'
    '============\n'
    + '\n' +
    open('CONTRIBUTORS.rst').read()
    + '\n' +
    open('CHANGES.rst').read()
    + '\n')

setup(name='imio.dms.mail',
      version=version,
      description="Imio dms mail",
      long_description=long_description,
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Environment :: Web Environment",
        "Framework :: Plone",
        "Framework :: Plone :: 4.2",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='',
      author='',
      author_email='',
      url='http://svn.communesplone.org/svn/communesplone/imio.dms.mail',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['imio', 'imio.dms'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'Plone',
          'Products.CPUtils',
          'Products.PasswordStrength',
          'collective.ckeditor',
          'collective.contact.core',
          'collective.contact.duplicated',
          'collective.contact.facetednav',
          'collective.contact.plonegroup',
          'collective.dexteritytextindexer',
          'collective.dms.basecontent',
          'collective.dms.batchimport',
          'collective.dms.mailcontent',
          'collective.dms.scanbehavior',
          'collective.documentgenerator',
          'collective.externaleditor',
          'collective.js.fancytree',
          'collective.messagesviewlet',
          'collective.querynextprev',
          'collective.task',
          'communesplone.layout',
          'dexterity.localrolesfield',
          'imio.dashboard',
          'imio.helpers',
          'imio.migrator',
          'plone.app.dexterity[grok]',
          'plone.app.lockingbehavior',
          'plonetheme.imioapps',
          'z3c.unconfigure',
          # -*- Extra requirements: -*-
      ],
      extras_require={'test':
        ['plone.app.testing',
         'plone.app.robotframework',
         'plonetheme.imioapps',]},
      entry_points="""
      # -*- Entry points: -*-

      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
