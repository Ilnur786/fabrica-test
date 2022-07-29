from typing import Union, Dict, Iterable, List
from db_api import Base
from sqlalchemy import inspect
from multimethod import multimethod as singledispatch


# MULTIMETHOD AS SINGLEDISPATCH
# cause singledispatch doesn't support some classes from typing module such as Iterable or List

@singledispatch
def object_as_dict(query_object) -> Union[List, Dict, Exception]:
	return NotImplementedError(f'Invalid type {type(query_object)}. Only Receives Model Class object or Model Class objects within iterable')


@object_as_dict.register
def _(query_object: Base) -> Dict:
	return {c.key: getattr(query_object, c.key) for c in inspect(query_object).mapper.column_attrs}


@object_as_dict.register
def _(query_object: Iterable[Base]) -> List:
	result = []
	for item in query_object:
		result.append({c.key: getattr(item, c.key) for c in inspect(item).mapper.column_attrs})
	return result


@singledispatch
def dynamic_update(query_object, attrs) -> Union[Iterable, Base, Exception]:
	return NotImplementedError(f'Invalid type {type(query_object)}. Only Receives Model Class object or Model Class objects within iterable')


@dynamic_update.register
def _(query_object: Base, attrs: Dict) -> Base:
	for k, v in attrs.items():
		if hasattr(query_object, k):
			setattr(query_object, k, v)
	return query_object


@dynamic_update.register
def _(query_object: Iterable[Base], attrs: Dict) -> Iterable[Base]:
	for obj in query_object:
		for k, v in attrs.items():
			if hasattr(obj, k):
				setattr(obj, k, v)
	return query_object


__all__ = ['object_as_dict', 'dynamic_update']