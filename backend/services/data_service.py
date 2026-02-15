"""
Data Service Module — Enhanced
Handles querying, aggregating, and visualizing ARGO oceanographic data
"""
from typing import Dict, List, Any, Optional
from sqlalchemy import func, and_, desc, distinct, text
from db.session import SessionLocal
from db.models import ArgoRecord, FloatMetadata
from datetime import datetime


class DataService:
    """Service for querying ARGO float data with chart/map support"""

    def __init__(self):
        self.session = None

    def _get_session(self):
        if not self.session:
            self.session = SessionLocal()
        return self.session

    def _safe_float(self, val):
        try:
            return round(float(val), 4) if val is not None else None
        except (TypeError, ValueError):
            return None

    # ─── Dataset Stats ─────────────────────────────────────────────

    def get_dataset_stats(self) -> Dict[str, Any]:
        """Get overall statistics about the ARGO dataset"""
        session = self._get_session()
        try:
            total = session.query(func.count(ArgoRecord.id)).scalar() or 0
            if total == 0:
                return {"total_records": 0, "message": "No data available. Run fetch_argovis.py to ingest."}

            floats = session.query(ArgoRecord.platform).distinct().all()
            float_list = sorted([f[0] for f in floats if f[0]])

            min_date = session.query(func.min(ArgoRecord.time)).scalar()
            max_date = session.query(func.max(ArgoRecord.time)).scalar()
            min_depth = session.query(func.min(ArgoRecord.depth)).scalar()
            max_depth = session.query(func.max(ArgoRecord.depth)).scalar()

            temp_stats = session.query(
                func.min(ArgoRecord.temperature),
                func.max(ArgoRecord.temperature),
                func.avg(ArgoRecord.temperature)
            ).filter(ArgoRecord.temperature.isnot(None)).first()

            sal_stats = session.query(
                func.min(ArgoRecord.salinity),
                func.max(ArgoRecord.salinity),
                func.avg(ArgoRecord.salinity)
            ).filter(ArgoRecord.salinity.isnot(None)).first()

            lat_bounds = session.query(func.min(ArgoRecord.latitude), func.max(ArgoRecord.latitude)).first()
            lon_bounds = session.query(func.min(ArgoRecord.longitude), func.max(ArgoRecord.longitude)).first()

            # Surface averages (depth < 10m) — scientifically defensible
            surface_temp = session.query(
                func.avg(ArgoRecord.temperature)
            ).filter(
                ArgoRecord.temperature.isnot(None),
                ArgoRecord.depth.isnot(None),
                ArgoRecord.depth < 10
            ).scalar()

            surface_sal = session.query(
                func.avg(ArgoRecord.salinity)
            ).filter(
                ArgoRecord.salinity.isnot(None),
                ArgoRecord.depth.isnot(None),
                ArgoRecord.depth < 10
            ).scalar()

            return {
                "total_records": total,
                "floats": float_list,
                "float_count": len(float_list),
                "date_range": {
                    "min": min_date.isoformat() if min_date else None,
                    "max": max_date.isoformat() if max_date else None,
                },
                "depth_range": {
                    "min": self._safe_float(min_depth),
                    "max": self._safe_float(max_depth),
                    "unit": "dbar",
                },
                "temperature": {
                    "min": self._safe_float(temp_stats[0]) if temp_stats else None,
                    "max": self._safe_float(temp_stats[1]) if temp_stats else None,
                    "avg": self._safe_float(temp_stats[2]) if temp_stats else None,
                    "unit": "°C",
                },
                "surface_temperature": {
                    "avg": self._safe_float(surface_temp),
                    "note": "averaged at depth < 10m",
                },
                "salinity": {
                    "min": self._safe_float(sal_stats[0]) if sal_stats else None,
                    "max": self._safe_float(sal_stats[1]) if sal_stats else None,
                    "avg": self._safe_float(sal_stats[2]) if sal_stats else None,
                    "unit": "PSU",
                },
                "surface_salinity": {
                    "avg": self._safe_float(surface_sal),
                    "note": "averaged at depth < 10m",
                },
                "geographic_bounds": {
                    "latitude": {"min": self._safe_float(lat_bounds[0]), "max": self._safe_float(lat_bounds[1])},
                    "longitude": {"min": self._safe_float(lon_bounds[0]), "max": self._safe_float(lon_bounds[1])},
                },
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            raise

    # ─── Float Metadata ────────────────────────────────────────────

    def get_all_floats(self) -> List[Dict[str, Any]]:
        """Get all float metadata for map/listing"""
        session = self._get_session()
        floats = session.query(FloatMetadata).all()

        if not floats:
            # Fallback: build from ArgoRecord
            platforms = session.query(
                ArgoRecord.platform,
                func.max(ArgoRecord.latitude).label("lat"),
                func.max(ArgoRecord.longitude).label("lon"),
                func.count(ArgoRecord.id).label("cnt"),
                func.min(ArgoRecord.time).label("first"),
                func.max(ArgoRecord.time).label("last"),
            ).group_by(ArgoRecord.platform).all()

            return [{
                "wmo_id": p.platform,
                "latitude": self._safe_float(p.lat),
                "longitude": self._safe_float(p.lon),
                "num_records": p.cnt,
                "first_date": p.first.isoformat() if p.first else None,
                "last_date": p.last.isoformat() if p.last else None,
                "ocean_region": "Indian Ocean",
                "status": "active",
            } for p in platforms if p.platform]

        return [{
            "wmo_id": f.wmo_id,
            "latitude": self._safe_float(f.last_latitude),
            "longitude": self._safe_float(f.last_longitude),
            "deploy_date": f.deploy_date.isoformat() if f.deploy_date else None,
            "last_date": f.last_date.isoformat() if f.last_date else None,
            "num_profiles": f.num_profiles,
            "ocean_region": f.ocean_region,
            "status": f.status,
            "summary": f.summary,
        } for f in floats]

    def get_float_detail(self, wmo_id: str) -> Dict[str, Any]:
        """Get detailed info for a specific float"""
        session = self._get_session()
        meta = session.query(FloatMetadata).filter(FloatMetadata.wmo_id == wmo_id).first()

        stats = session.query(
            func.count(ArgoRecord.id).label("records"),
            func.count(distinct(ArgoRecord.cycle_number)).label("cycles"),
            func.min(ArgoRecord.temperature).label("temp_min"),
            func.max(ArgoRecord.temperature).label("temp_max"),
            func.avg(ArgoRecord.temperature).label("temp_avg"),
            func.min(ArgoRecord.salinity).label("sal_min"),
            func.max(ArgoRecord.salinity).label("sal_max"),
            func.min(ArgoRecord.depth).label("depth_min"),
            func.max(ArgoRecord.depth).label("depth_max"),
        ).filter(ArgoRecord.platform == wmo_id).first()

        result = {
            "wmo_id": wmo_id,
            "total_records": stats.records if stats else 0,
            "total_cycles": stats.cycles if stats else 0,
            "temperature": {
                "min": self._safe_float(stats.temp_min),
                "max": self._safe_float(stats.temp_max),
                "avg": self._safe_float(stats.temp_avg),
            },
            "salinity": {
                "min": self._safe_float(stats.sal_min),
                "max": self._safe_float(stats.sal_max),
            },
            "depth_range": {
                "min": self._safe_float(stats.depth_min),
                "max": self._safe_float(stats.depth_max),
            },
        }

        if meta:
            result.update({
                "latitude": self._safe_float(meta.last_latitude),
                "longitude": self._safe_float(meta.last_longitude),
                "deploy_date": meta.deploy_date.isoformat() if meta.deploy_date else None,
                "last_date": meta.last_date.isoformat() if meta.last_date else None,
                "ocean_region": meta.ocean_region,
                "status": meta.status,
            })

        return result

    # ─── Trajectory ────────────────────────────────────────────────

    def get_float_trajectory(self, wmo_id: str) -> List[Dict[str, Any]]:
        """Get trajectory (lat/lon over time) for a float"""
        session = self._get_session()

        # Get one position per cycle
        results = session.query(
            ArgoRecord.latitude,
            ArgoRecord.longitude,
            ArgoRecord.time,
            ArgoRecord.cycle_number,
        ).filter(
            ArgoRecord.platform == wmo_id,
            ArgoRecord.latitude.isnot(None),
            ArgoRecord.longitude.isnot(None),
        ).group_by(
            ArgoRecord.cycle_number
        ).order_by(ArgoRecord.time).all()

        return [{
            "latitude": self._safe_float(r.latitude),
            "longitude": self._safe_float(r.longitude),
            "time": r.time.isoformat() if r.time else None,
            "cycle_number": r.cycle_number,
        } for r in results]

    # ─── Temperature Profile ───────────────────────────────────────

    def get_temperature_profile(self, platform: Optional[str] = None,
                                 cycle: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get temperature vs depth profile with platform info for region coloring"""
        session = self._get_session()

        query = session.query(
            ArgoRecord.depth,
            ArgoRecord.temperature,
            ArgoRecord.platform,
            ArgoRecord.cycle_number,
            ArgoRecord.time,
        ).filter(
            ArgoRecord.temperature.isnot(None),
            ArgoRecord.depth.isnot(None),
        )

        if platform:
            query = query.filter(ArgoRecord.platform == platform)
        if cycle:
            query = query.filter(ArgoRecord.cycle_number == cycle)

        # Use random sampling to show distribution across depths
        query = query.order_by(func.random())
        results = query.limit(2000).all()

        return [{
            "depth": self._safe_float(r.depth),
            "temperature": self._safe_float(r.temperature),
            "platform": r.platform,
            "cycle_number": r.cycle_number,
            "time": r.time.isoformat() if r.time else None,
        } for r in results]

    # ─── Salinity Profile ──────────────────────────────────────────

    def get_salinity_profile(self, platform: Optional[str] = None,
                              cycle: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get salinity vs depth profile"""
        session = self._get_session()

        query = session.query(
            ArgoRecord.depth,
            ArgoRecord.salinity,
            ArgoRecord.cycle_number,
            ArgoRecord.time,
        ).filter(
            ArgoRecord.salinity.isnot(None),
            ArgoRecord.depth.isnot(None),
        )

        if platform:
            query = query.filter(ArgoRecord.platform == platform)
        if cycle:
            query = query.filter(ArgoRecord.cycle_number == cycle)

        # Use random sampling for better visualization
        query = query.order_by(func.random())
        results = query.limit(2000).all()

        return [{
            "depth": self._safe_float(r.depth),
            "salinity": self._safe_float(r.salinity),
            "cycle_number": r.cycle_number,
            "time": r.time.isoformat() if r.time else None,
        } for r in results]

    # ─── T-S Diagram ───────────────────────────────────────────────

    def get_ts_diagram(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get Temperature-Salinity diagram data"""
        session = self._get_session()

        query = session.query(
            ArgoRecord.temperature,
            ArgoRecord.salinity,
            ArgoRecord.depth,
            ArgoRecord.platform,
        ).filter(
            ArgoRecord.temperature.isnot(None),
            ArgoRecord.salinity.isnot(None),
        )

        if platform:
            query = query.filter(ArgoRecord.platform == platform)

        # Random sample for scatter plot
        query = query.order_by(func.random())
        results = query.limit(3000).all()

        return [{
            "temperature": self._safe_float(r.temperature),
            "salinity": self._safe_float(r.salinity),
            "depth": self._safe_float(r.depth),
            "platform": r.platform,
        } for r in results]

    # ─── Depth-Time Section ────────────────────────────────────────

    def get_depth_time_data(self, platform: str) -> List[Dict[str, Any]]:
        """Get depth-time section data for a float"""
        session = self._get_session()

        results = session.query(
            ArgoRecord.depth,
            ArgoRecord.time,
            ArgoRecord.temperature,
            ArgoRecord.salinity,
            ArgoRecord.cycle_number,
        ).filter(
            ArgoRecord.platform == platform,
            ArgoRecord.depth.isnot(None),
            ArgoRecord.time.isnot(None),
        ).order_by(ArgoRecord.time, ArgoRecord.depth).limit(2000).all()

        return [{
            "depth": self._safe_float(r.depth),
            "time": r.time.isoformat() if r.time else None,
            "temperature": self._safe_float(r.temperature),
            "salinity": self._safe_float(r.salinity),
            "cycle_number": r.cycle_number,
        } for r in results]

    # ─── General Query ─────────────────────────────────────────────

    def query_records(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query ARGO records with filters"""
        session = self._get_session()
        query = session.query(ArgoRecord)

        if 'min_depth' in filters:
            query = query.filter(ArgoRecord.depth >= filters['min_depth'])
        if 'max_depth' in filters:
            query = query.filter(ArgoRecord.depth <= filters['max_depth'])
        if 'min_temp' in filters:
            query = query.filter(ArgoRecord.temperature >= filters['min_temp'])
        if 'max_temp' in filters:
            query = query.filter(ArgoRecord.temperature <= filters['max_temp'])
        if 'min_sal' in filters:
            query = query.filter(ArgoRecord.salinity >= filters['min_sal'])
        if 'max_sal' in filters:
            query = query.filter(ArgoRecord.salinity <= filters['max_sal'])
        if 'platform' in filters:
            query = query.filter(ArgoRecord.platform == filters['platform'])
        if 'min_lat' in filters:
            query = query.filter(ArgoRecord.latitude >= filters['min_lat'])
        if 'max_lat' in filters:
            query = query.filter(ArgoRecord.latitude <= filters['max_lat'])
        if 'min_lon' in filters:
            query = query.filter(ArgoRecord.longitude >= filters['min_lon'])
        if 'max_lon' in filters:
            query = query.filter(ArgoRecord.longitude <= filters['max_lon'])

        limit = filters.get('limit', 100)
        query = query.order_by(desc(ArgoRecord.time)).limit(limit)
        records = query.all()

        return [{
            "id": r.id,
            "time": r.time.isoformat() if r.time else None,
            "latitude": self._safe_float(r.latitude),
            "longitude": self._safe_float(r.longitude),
            "depth": self._safe_float(r.depth),
            "temperature": self._safe_float(r.temperature),
            "salinity": self._safe_float(r.salinity),
            "platform": r.platform,
            "cycle_number": r.cycle_number,
        } for r in records]

    # ─── Context for AI Chat ───────────────────────────────────────

    def get_relevant_context(self, user_query: str) -> Dict[str, Any]:
        """Get relevant ARGO data context for a user query"""
        query_lower = user_query.lower()
        stats = self.get_dataset_stats()
        context = {"stats": stats, "sample_data": [], "floats": []}

        # Add float list
        try:
            context["floats"] = self.get_all_floats()
        except Exception:
            pass

        filters = {}

        # Depth queries
        if any(w in query_lower for w in ['surface', 'shallow', 'top']):
            filters['max_depth'] = 50
            filters['limit'] = 30
        elif any(w in query_lower for w in ['deep', 'bottom', 'depth']):
            filters['min_depth'] = 500
            filters['limit'] = 30

        # Temperature queries
        if any(w in query_lower for w in ['warm', 'hot', 'temperature', 'temp']):
            filters['limit'] = 40

        # Region queries
        if 'arabian' in query_lower:
            filters['min_lat'] = 5
            filters['max_lat'] = 30
            filters['min_lon'] = 45
            filters['max_lon'] = 78
        elif 'bengal' in query_lower or 'bay' in query_lower:
            filters['min_lat'] = 5
            filters['max_lat'] = 25
            filters['min_lon'] = 78
            filters['max_lon'] = 100
        elif 'equat' in query_lower:
            filters['min_lat'] = -10
            filters['max_lat'] = 10

        # Get sample data
        try:
            context["sample_data"] = self.query_records(filters if filters else {'limit': 25})
        except Exception as e:
            print(f"Error getting sample data: {e}")

        return context

    # ─── Export ─────────────────────────────────────────────────────

    def export_data(self, filters: Dict[str, Any], format: str = "csv") -> str:
        """Export filtered data. Returns CSV string."""
        records = self.query_records({**filters, "limit": 5000})
        if not records:
            return ""

        import csv
        import io

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
        return output.getvalue()

    def __del__(self):
        if self.session:
            self.session.close()
