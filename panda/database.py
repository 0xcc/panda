#-*- coding:utf-8 -*-
'''
orm model
'''
import copy
import sys
import threading
import MySQLdb 
#-----------------------------------------Fields----------------------------------------------------
class Field(object):
	name=''
	@property
	def sql(self):
		pass

class IntegerField(Field):
	@property
	def sql(self):
		return '%s %s' % (self.name,'INTEGER')

class CharField(Field):
	def __init__(self,max_length=255):
	 	self.max_length=max_length

	@property
	def sql(self):
	    return '%s %s(%d) NOT NULL' % (self.name,'VARCHAR',self.max_length)

class DateField(Field):
	@property
	def sql(self):
	    return '%s %s' % (self.name, "DATETIME")

class PrimaryKeyField(IntegerField):
	@property
	def sql(self):
		return '%s %s NOT NULL PRIMARY KEY' % (self.name, "INTEGER")

class ForeignKeyField(IntegerField):
	def __init__(self, to_table):
		self.to_table = to_table
	
	@property
	def sql(self):
		return '%s %s NOT NULL REFERENCES "%s" ("%s")' % (
				self.name, 'INTEGER', self.to_table, 'id'
			)



class ForeignKeyReverseField(object):
	def __init__(self,from_table):
		self.from_table=from_table
		self.name=None
		self.tablename=None
		self.id=None
		self.db=None
		self.from_class=None
		self.re=None

	def update(self,name,tablename,db):
		self.name=name
		self.tablename=tablename
		self.db=db
		self.from_class=self.db.__tabledict__[self.from_table]

		for name,attr in self.from_class.__dict__.items():
			if isinstance(attr,ForeignKeyField) and attr.to_table==self.tablename:
				self.re=name

		def all(self):
			return self.from_class.select('*')

		def count(self):
			return self.from_class.select('*').where('='.join([self.re,str(self.id)])).all()

class ManyToManyField(object):
	pass
		

#----------------------------------------MetaModel-------------------------------------
				
class MetaModel(type):
	def __new__(clz,name,bases,attrs):

		clz=super(MetaModel,clz).__new__(clz,name,bases,attrs)
		#return clz
		#fields
		fields={}
		refed_fields={}
		clz_dict=clz.__dict__

		#设置表名
		if '__tablename__' in clz_dict.keys():
			setattr(clz,'__tablename__',clz_dict['__tablename__'])
		else:
			setattr(clz,'__tablename__',clz.__name__.lower())

		if hasattr(clz,'db'):
			getattr(clz,'db').__tabledict__[clz.__tablename__]=clz

		has_primary_key=False
		setattr(clz,'has_relationship',False)

		for name,attr in clz.__dict__.items():
			if isinstance(attr, ForeignKeyReverseField) or isinstance(attr, ManyToManyField):
				setattr(clz,'has_relationship',True)
				#print "attr: ",attr
				#print "tablename: ",clz.__tablename__
				#print "db:",clz.db
				attr.update(name,clz.__tablename__,clz.db)
				refed_fields[name]=attr
			if isinstance(attr, Field):
				attr.name=name
				fields[name]=attr
				if isinstance(attr,PrimaryKeyField):
					has_primary_key = True

		if not has_primary_key:
			pk=PrimaryKeyField()
			pk.name='id'
			fields['id'] = pk
		setattr(clz, '__fields__', fields)
		setattr(clz, '__refed_fields__', refed_fields)
		return clz

newBase=MetaModel('NewBase',(object,),{})
class Model(newBase):
	def __init__(self,**kwargs):
		for k, v in self.__refed_fields__.items():
			if isinstance(v, ForeignKeyReverseField) or isinstance(v, ManyToManyField):
				v.id=self.id
				t=copy.deepcopy(v)
				setattr(t,'db',v.db)
				setattr(self,k,t)

		for k, v in kwargs.items():
			setattr(self,k,v)	

	@classmethod
	def get(clz,*args,**kwargs):
		return SelectQuery(clz, args).where(**kwargs).first()

	@classmethod
	def select(clz,*args):
		return SelectQuery(clz, args)

	@classmethod
	def update(clz, *args, **kwargs):
		return UpdateQuery(clz, args, **kwargs)

	@classmethod
	def delete(cls, *args, **kwargs):
		return DeleteQuery(cls, args, **kwargs)


class Database(threading.local):
	pass

class DatabaseException(Exception):
	pass


class MySQL(Database):
	def __init__(self,host,user,passwd,database):
		self.database=database
		self.conn=MySQLdb.Connect(host=host,user=user,passwd=passwd,db=database)
		self.__tabledict__={}
		self.__db__=self
		setattr(self, 'Model', Model)
		c = getattr(self, 'Model')
		if hasattr(self, '__db__'):
			setattr(c, 'db', getattr(self, '__db__'))

	def create_all(self):
		for k,v in self.__tabledict__.items():
			if issubclass(v,self.Model):
				print("create table %s..." % k)
				self.create_table(v)

	def create_table(self,model):
		self.drop_table(model)
		c=[]
		for field in model.__fields__.values():
			c.append(field.sql)

		sql=' create table %s (%s);' % (model.__tablename__, ', '.join(c))
		print sql
		cursor=self.conn.cursor()
		cursor.execute(sql)
		self.commit()

	def drop_table(self,model):
		cursor=self.conn.cursor()
		cursor.execute('DROP TABLE IF EXISTS  %s;' % model.__tablename__)
		self.commit()
		#del self.__tabledict__[model.__tablename__]

	def add(self,instance):
		colk=[]
		colv=[]
		#print instance
		for k,v in instance.__dict__.items():
			if isinstance(v,ManyToManyField) or isinstance(v,ForeignKeyReverseField):
				continue
			colk.append(k)
			colv.append('\''+str(v)+'\'')
		cursor=self.conn.cursor()
		cursor.execute('insert into %s (%s) values (%s)'
				%(instance.__class__.__tablename__,','.join(colk),','.join(colv)))
		return cursor

	def execute(self,sql,commit=False):
		pass

	def commit(self):
		self.conn.commit()

	def rollback(self):
		self.conn.rollback()


#-----------------------------------------------------------


class BaseQuery(object):

	def where(self,andor,condition):
		w=" %s (%s) " %(andor,condition)
		self._where+=w
		return self

	@property
	def sql(self):
	    pass

class QueryException(DatabaseException):
	pass
	


class SelectQuery(BaseQuery):
	'''
	SELECT pub_date,id,title from self_define_post 
	where id=1 and pub_date>'2016' and (title like '%ad%')
	GROUP BY title
	HAVING sum(id)>89
	ORDER BY pub_date
	'''
	def __init__(self,table,column):
		self._table=table
		if isinstance(column,list):
			self._column=column
		elif isinstance(column,str):
			self._column=column.split(',')
		else:
			self.column=[]
		self._where='(1=1) '
		self._groupby=''
		self._having=''
		self._orderby=''
	
	def column(self,col):
		self._column.append(col)
		return self

	def groupby(self,groupby):
		self._groupby=(" group by %s " % groupby)
		return self

	def having(self,having):
		self._having=(" having %s ") % having
		return self

	def orderby(self,orderby):
		self._orderby=(" order by %s ") % orderby
		return self

	@property
	def sql(self):
		if not self._column:
			self._column=['*']
		sql='select %s from %s where %s ' % (",".join(self._column),self._table,self._where)
		if self._groupby:
			sql+=self._groupby
			if self._having:
				sql+=self._having
		if self._orderby:
			sql+=self._orderby
		return sql
	

class UpdateQuery(BaseQuery):
	def __init__(self,table,where=' 1=1 ',**values):
		self.table=table
		self._where=where
		self.values=values

	def set(self,name,value):
		self.values[name]=value


	@property
	def sql(self):
		#print self.values
		sql='update %s set %s where %s ' %(self.table, ",".join(["=".join((key,str(self.values[key]))) for key in self.values]),self._where)
		return sql

class DeleteQuery(BaseQuery):
	def __init__(self,table,where=" 1=1 "):
		self.table=table
		self._where=where

	@property
	def sql(self):
	   sql="delete from %s where %s " % (self.table,self._where)
	   return sql
