"""The eight tables from the user-supplied November 2026 dedc.sql.

This metadata is the persistent schema. app.database.Base describes transient
SQLite query projections only; never create those tables in the configured DB.
"""
from sqlalchemy import (
    MetaData, Table, Column, Integer, SmallInteger, String, Text, DateTime,
    ForeignKey, Boolean, Index, func,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateColumn

metadata = MetaData()

def identity(name):
    return Column(name, Integer, primary_key=True, autoincrement=True)

ministry = Table('ministry', metadata,
    identity('ministryId'), Column('ministryName', String(255), nullable=False, unique=True))
university = Table('university', metadata,
    identity('uniId'), Column('uniType', String(100), nullable=False),
    Column('uniName', String(255), nullable=False, unique=True))
userrole = Table('userrole', metadata,
    identity('roleId'), Column('roleName', String(100), nullable=False, unique=True))
user = Table('user', metadata,
    identity('userId'), Column('roleId', ForeignKey('userrole.roleId', onupdate='CASCADE'), nullable=False),
    Column('uniId', ForeignKey('university.uniId', onupdate='CASCADE')),
    Column('ministryId', ForeignKey('ministry.ministryId', onupdate='CASCADE')),
    Column('userName', String(100), nullable=False, unique=True),
    Column('passwordHash', String(255), nullable=False),
    Column('isActive', Boolean, nullable=False, server_default='1'),
    Column('createdAt', DateTime, nullable=False, server_default=func.current_timestamp()))

def questions(name, pk, detail):
    return Table(name, metadata, identity(pk), Column(detail, Text, nullable=False),
        Column('description', Text), Column('yearFrom', SmallInteger, nullable=False),
        Column('yearTo', SmallInteger, nullable=False))

uniquestion = questions('uniquestion', 'uQId', 'uQDetail')
ministryquestion = questions('ministryquestion', 'mQId', 'mQDetail')

def surveys(name, pk, organization, question, target):
    return Table(name, metadata, identity(pk),
        Column(organization, ForeignKey(target, onupdate='CASCADE'), nullable=False),
        Column(question, ForeignKey(('uniquestion.uQId' if name == 'unisurvey' else 'ministryquestion.mQId'), onupdate='CASCADE'), nullable=False),
        Column('hasItem', Boolean, nullable=False), Column('itemCount', Integer),
        Column('surveyDescription', Text), Column('remark', Text),
        Column('submittedAt', DateTime, nullable=False, server_default=func.current_timestamp()),
        Column('updatedAt', DateTime, onupdate=func.current_timestamp()))

unisurvey = surveys('unisurvey', 'uniSurveyId', 'uniId', 'uQId', 'university.uniId')
ministrysurvey = surveys('ministrysurvey', 'mSurveyId', 'ministryId', 'mQId', 'ministry.ministryId')

for table, names in [
    (user, [('idx_user_roleId', 'roleId'), ('idx_user_uniId', 'uniId'), ('idx_user_ministryId', 'ministryId')]),
    (unisurvey, [('idx_uniSurvey_uniId', 'uniId'), ('idx_uniSurvey_uQId', 'uQId')]),
    (ministrysurvey, [('idx_ministrySurvey_ministryId', 'ministryId'), ('idx_ministrySurvey_mQId', 'mQId')]),
]:
    for name, column in names:
        Index(name, table.c[column])

for table in metadata.tables.values():
    table.dialect_options['mysql']['engine'] = 'InnoDB'
    table.dialect_options['mysql']['charset'] = 'utf8mb4'
    table.dialect_options['mysql']['collate'] = 'utf8mb4_unicode_ci'


@compiles(CreateColumn, 'mysql')
def mysql_column(element, compiler, **kwargs):
    rendered = compiler.visit_create_column(element, **kwargs)
    if element.element.table.metadata is metadata and element.element.name == 'updatedAt':
        return rendered + ' DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP'
    return rendered
