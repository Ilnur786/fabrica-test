from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Table, Column, Integer, DateTime, Float, Boolean, String, MetaData, ForeignKey
from datetime import datetime
import tzlocal
import pytz

Base = declarative_base()


class Distribution(Base):
	__tablename__ = 'distributions'

	id = Column(Integer, primary_key=True)
	# to receive time in that timezone: datetime.now(tz=pytz.timezone(tzlocal.get_localzone_name()))
	# maybe in the future it will require convert time into client tz
	# NOW it need declaration of given time format, in the API and convert str date into datetime object (strptime)
	distr_start_date = Column(DateTime, default=datetime.now(), comment='date when distribution will be started')
	distr_text = Column(String, comment='message text')
	client_filter = Column(String, comment='get some clients with filtering them by mobile operator code, tag or etc.')
	distr_end_date = Column(DateTime, comment='date when distribution will be ended')
	message = relationship("Message", back_populates="distribution", uselist=False)  # uselist=False is declarate one-to-one relate


class Client(Base):
	__tablename__ = 'clients'

	id = Column(Integer, primary_key=True)
	telephone_number = Column(Integer, comment='client telephone number')  # need constrainting length before added into db
	mobile_operator_code = Column(Integer, comment='7XXX9354758 - three number after country code')  # need constrainting length before added into db
	tag = Column(String, nullable=True, comment='free fillable field. Can be nullable')
	# after API will be ready, user can give tz in "Europe/Moscow" like format. Table with values are there: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
	# or it can look like datetime.timezone('MSC') with offset from UTC-time.
	timezone = Column(String(30), default=tzlocal.get_localzone_name(), comment='it looks like "Europe/Moscow"')
	message = relationship("Message", back_populates="client")


class Message(Base):
	__tablename__ = 'messages'

	id = Column(Integer, primary_key=True)
	send_date = Column(DateTime, default=datetime.now(), comment='date when message was send')
	sending_status = Column(Boolean, default=True)
	# one to one
	distribution_id = Column(Integer, ForeignKey('distributions.id'), comment='distribution id, where message was sended')
	distribution = relationship("Distribution", back_populates="message")
	# one to many. to one message can relate multiple clients
	client_id = Column(Integer, ForeignKey('clients.id'), comment='client id whose was send message')
	client = relationship('Client', back_populates='message')

