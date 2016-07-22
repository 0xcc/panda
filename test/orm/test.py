
from panda import database
from panda import SelectQuery,UpdateQuery,DeleteQuery
db=database.MySQL(host='127.0.0.1',user='root',passwd='root',database="test")


class Post(db.Model):
	__tablename__ = 'self_define_post'

	id = database.PrimaryKeyField()
	title = database.CharField(100)
	#content = database.TextField()
	pub_date = database.DateField()

	def __repr__(self):
		return '<Post %s>' % self.title


class Author(db.Model):
	id=database.PrimaryKeyField()
	name = database.CharField(100)
	posts = database.ForeignKeyReverseField('self_define_post')

	def __repr__(self):
		return '<Author %s>' % self.name

db.create_all()
p=Post()
p.id=1
p.title='title1'
p.pub_date='2016-6-30'

db.add(p)
query=SelectQuery("",p.__tablename__)
print (type(query.where))
query.where("and",'title=jasd').where('and','id>45').orderby('id desc')
print query.sql

delete=DeleteQuery(p.__tablename__,"id=888")
print delete.sql


update=UpdateQuery(p.__tablename__,id=77,title=888)
print update.sql

a=Author()
a.id=1
a.name='Author1'
a.posts=1





