from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Table, Column, Integer, DateTime, Float, Boolean, String, MetaData, ForeignKey
from datetime import datetime
import tzlocal
import pytz
from dataclasses import dataclass
from .database import Base


@dataclass
class ModelsConfig:
	datetime_format = '%Y-%m-%d %H:%M'


class Distribution(Base, ModelsConfig):
	__tablename__ = 'distributions'

	id = Column(Integer, primary_key=True)
	# to receive time in that timezone: datetime.now(tz=pytz.timezone(tzlocal.get_localzone_name()))
	# maybe in the future it will require convert time into client tz
	# NOW it need declaration of given time format in the API docs and convert str date into datetime object (strptime)
	start_date = Column(DateTime, default=datetime.now(), comment='date when distribution will be started')
	text = Column(String, comment='message text')
	client_filter = Column(String, nullable=True,
							  comment='get some clients with filtering them by mobile operator code, tag or etc.')
	end_date = Column(DateTime, comment='date when distribution will be ended')
	was_deleted = Column(Boolean, default=False, comment='Shows if this row has been removed')
	message = relationship("Message", backref="distributions", lazy=True, uselist=False)

	# uselist=False is declarate one-to-one relate

	def __repr__(self):
		return f'<Distribution: id: {self.id}, start_date: {self.start_date.strftime(self.datetime_format)}, ' \
			   f'text: "{self.text}", client_filter: "{self.client_filter}", ' \
			   f'end_date: {self.end_date.strftime(self.datetime_format)}, was_deleted: {self.was_deleted}>'


class Client(Base, ModelsConfig):
	__tablename__ = 'clients'

	id = Column(Integer, primary_key=True)
	mobile_number = Column(String(15),
							  comment='client telephone number')  # need constrainting length before added into db
	mobile_operator_code = Column(String(5),
									 comment='7XXX9354758 - three number after country code')  # need constrainting length before added into db
	tag = Column(String, comment='free fillable field. Can be nullable')
	# after API will be ready, user can give tz in "Europe/Moscow" like format.
	# Table with values are there: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
	timezone = Column(String(30), comment='it will be look like "Europe/Moscow"')
	was_deleted = Column(Boolean, default=False, comment='Shows if this row has been removed')
	message = relationship("Message", backref="clients", lazy=True)

	def __repr__(self):
		return f'<Client: id: {self.id}, mobile_number: "{self.mobile_number}", ' \
			   f'operator_code: "{self.mobile_operator_code}", tag: "{self.tag}", timezone: "{self.timezone}, ' \
			   f'was_deleted: {self.was_deleted}">'


class Message(Base):
	__tablename__ = 'messages'

	id = Column(Integer, primary_key=True)
	send_date = Column(DateTime, nullable=True, default=datetime.now(),
					   comment='date when message was send. If NULL, it mean that message was not send yet')
	sending_status = Column(Boolean, default=True)
	# one to one
	distribution_id = Column(Integer, ForeignKey('distributions.id'),
							 comment='distribution id, where message was sended')
	distribution = relationship("Distribution", back_populates="message")
	# one to many. to one message can relate multiple clients
	client_id = Column(Integer, ForeignKey('clients.id'), comment='client id whose was send message')
	client = relationship('Client', back_populates='message')

	def __repr__(self):
		return f'<Message: id: {self.id}, ' \
			   f'send_date: {self.send_date.strftime(self.datetime_format) if self.send_date else None}, ' \
			   f'sending_status: {self.sending_status}, distribution.id: {self.distribution_id}, ' \
			   f'client.id: {self.client_id}, was_deleted: {self.was_deleted}>'
