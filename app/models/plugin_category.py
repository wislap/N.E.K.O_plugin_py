from sqlalchemy import Column, Integer, ForeignKey, Table

from app.core.database import Base


class PluginCategory(Base):
    __tablename__ = "plugin_categories"
    
    plugin_id = Column(Integer, ForeignKey("plugins.id"), primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), primary_key=True)
