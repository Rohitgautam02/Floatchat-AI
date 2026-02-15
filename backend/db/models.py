"""
Database Models for FloatChat-AI
Enhanced schema for ARGO oceanographic data with metadata tracking
"""
from sqlalchemy.orm import declarative_base, mapped_column, Mapped
from sqlalchemy import Integer, Float, String, DateTime, Text, Index
from datetime import datetime

Base = declarative_base()


class FloatMetadata(Base):
    """Metadata about each ARGO float platform"""
    __tablename__ = "float_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wmo_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    deploy_date: Mapped[str] = mapped_column(DateTime, nullable=True)
    last_date: Mapped[str] = mapped_column(DateTime, nullable=True)
    last_latitude: Mapped[float] = mapped_column(Float, nullable=True)
    last_longitude: Mapped[float] = mapped_column(Float, nullable=True)
    num_profiles: Mapped[int] = mapped_column(Integer, default=0)
    ocean_region: Mapped[str] = mapped_column(String, nullable=True)  # e.g. "Arabian Sea"
    status: Mapped[str] = mapped_column(String, default="active")  # active / inactive
    summary: Mapped[str] = mapped_column(Text, nullable=True)  # text summary for RAG


class ArgoRecord(Base):
    """Individual ARGO float measurement record"""
    __tablename__ = "argo_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    time: Mapped[str] = mapped_column(DateTime)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    depth: Mapped[float] = mapped_column(Float)            # dbar (pressure)
    temperature: Mapped[float] = mapped_column(Float, nullable=True)  # °C
    salinity: Mapped[float] = mapped_column(Float, nullable=True)     # PSU
    platform: Mapped[str] = mapped_column(String, nullable=True, index=True)  # WMO ID
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=True)
    profile_id: Mapped[str] = mapped_column(String, nullable=True)
    data_mode: Mapped[str] = mapped_column(String, nullable=True)  # R=realtime, D=delayed, A=adjusted

    __table_args__ = (
        Index('idx_platform_cycle', 'platform', 'cycle_number'),
        Index('idx_lat_lon', 'latitude', 'longitude'),
        Index('idx_time', 'time'),
    )
