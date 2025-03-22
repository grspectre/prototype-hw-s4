from datetime import datetime
from sqlalchemy import Column, DateTime, func, event
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Query, scoped_session, sessionmaker

class TimestampMixin:
    """Миксин для автоматических timestamp полей."""
    
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=func.now(), nullable=False)
    
    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

class SoftDeleteQuery(Query):
    """Класс запросов с поддержкой мягкого удаления."""
    
    def __new__(cls, *args, **kwargs):
        obj = super(SoftDeleteQuery, cls).__new__(cls)
        obj._with_deleted = kwargs.pop('with_deleted', False)
        return obj
    
    def __init__(self, *args, **kwargs):
        super(SoftDeleteQuery, self).__init__(*args, **kwargs)
        if hasattr(self, '_with_deleted') and not self._with_deleted:
            self._criterion = (self._criterion & (self._entities[0].class_.deleted_at == None))
    
    def with_deleted(self):
        return self.__class__(self._entities, self.session, with_deleted=True)
    
    def only_deleted(self):
        return self.with_deleted().filter(self._entities[0].class_.deleted_at != None)

class SoftDeleteMixin:
    """Миксин для поддержки мягкого удаления."""
    
    query_class = SoftDeleteQuery
    
    @declared_attr
    def deleted_at(cls):
        return Column(DateTime, nullable=True)
    
    def soft_delete(self, session=None):
        self.deleted_at = datetime.utcnow()
        if session:
            session.add(self)
    
    def restore(self, session=None):
        self.deleted_at = None
        if session:
            session.add(self)

class TimestampSoftDeleteMixin(TimestampMixin, SoftDeleteMixin):
    """Миксин, объединяющий функциональность timestamp полей и мягкого удаления."""
    pass
