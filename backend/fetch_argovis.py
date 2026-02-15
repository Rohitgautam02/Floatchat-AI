"""
ARGO Data Fetcher — Multi-Float Indian Ocean Pipeline
Fetches real ARGO float data from the Argovis API for multiple Indian Ocean floats.
"""
import os
import time
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from db.models import Base, ArgoRecord, FloatMetadata
from db.session import engine, SessionLocal

load_dotenv()

# Indian Ocean ARGO floats — verified coordinates via Argovis API
# Each float confirmed to be within Indian Ocean basin (20-120°E, 35°S-30°N)
INDIAN_OCEAN_FLOATS = [
    # Arabian Sea (verified: lon 49-70°E, lat 10-14°N)
    {"wmo": "2901339", "region": "Arabian Sea"},       # 70°E/10°N, INCOIS, 329 profiles
    {"wmo": "2901474", "region": "Arabian Sea"},       # 49°E/14°N, western Arabian Sea, 215 profiles
    # Bay of Bengal (verified: lon 85-90°E, lat 10-20°N)
    {"wmo": "2902086", "region": "Bay of Bengal"},     # ~85°E/15°N, 243 profiles
    {"wmo": "2902196", "region": "Bay of Bengal"},     # ~88°E/12°N, 167 profiles
    {"wmo": "2902197", "region": "Bay of Bengal"},     # ~87°E/10°N, 204 profiles
    # Equatorial Indian Ocean (verified: lon 85-90°E, lat 0-5°N)
    {"wmo": "2902150", "region": "Equatorial Indian Ocean"},  # ~85°E/1°N, 200 profiles
    {"wmo": "2901862", "region": "Equatorial Indian Ocean"},  # 88°E/-4°S, 6 profiles
    # Southern Indian Ocean (verified: lon ~106°E, lat -34°S)
    {"wmo": "5903955", "region": "Southern Indian Ocean"},    # 106°E/-34°S, CSIRO BGC, 719 profiles
]

ARGOVIS_BASE = "https://argovis-api.colorado.edu"
ARGOVIS_V2_BASE = "https://argovis2.colorado.edu/api/v2"


def is_indian_ocean(lat, lon):
    """Strict check: is this coordinate in the Indian Ocean basin?"""
    if lat is None or lon is None:
        return False
    # Indian Ocean bounds: lat -35 to 30, lon 20 to 120
    # Exclude South China Sea / West Pacific (lon > 100 and lat > 0)
    if lon > 100 and lat > 0:
        return False
    return -35 <= lat <= 30 and 20 <= lon <= 120


def classify_region(lat, lon):
    """Classify Indian Ocean sub-region from coordinates"""
    if lat is None or lon is None:
        return "Unknown"
    if not is_indian_ocean(lat, lon):
        return "Outside Indian Ocean"
    if lat > 5 and lon >= 78:
        return "Bay of Bengal"
    if lat > 5 and lon < 78:
        return "Arabian Sea"
    if -10 <= lat <= 5:
        return "Equatorial Indian Ocean"
    if lat < -10:
        return "Southern Indian Ocean"
    return "Indian Ocean"


def fetch_float_profiles(wmo_id, region="Indian Ocean", max_retries=3):
    """Fetch all profiles for an ARGO float from Argovis API"""
    print(f"[INFO] Fetching float {wmo_id} ({region})...")

    headers = {"Accept": "application/json"}

    for attempt in range(max_retries):
        # Try v2 API first
        try:
            url = f"{ARGOVIS_V2_BASE}/platforms/ARGO/{wmo_id}"
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if data and isinstance(data, list) and len(data) > 0:
                    print(f"[OK] Got {len(data)} profiles for {wmo_id}")
                    return data
                else:
                    print(f"[WARN] No profiles in V2 response for {wmo_id}")
        except Exception as e:
            pass # V2 failed, proceed to V1 fallback

        # Try alternate V1 endpoint as fallback directly
        try:
            # Explicitly request data columns to ensure we get measurements
            url_alt = f"{ARGOVIS_BASE}/argo?platform={wmo_id}&data=pressure,temperature,salinity"
            r2 = requests.get(url_alt, headers=headers, timeout=30)
            if r2.status_code == 200:
                data = r2.json()
                if data and len(data) > 0:
                    print(f"[OK] Got {len(data)} profiles for {wmo_id} (alt API)")
                    return data
            else:
                pass
        except Exception as e:
            print(f"[ERROR] V1 API error for {wmo_id}: {e}")

        if attempt < max_retries - 1:
            time.sleep(2)

    return []


def parse_profiles(profiles, wmo_id, region):
    """Parse Argovis API response into flat measurement rows + metadata"""
    rows = []
    first_date = None
    last_date = None
    last_lat = None
    last_lon = None

    for i, profile in enumerate(profiles):
        # Extract lat/lon from top level or geolocation object
        lat = profile.get("lat") or profile.get("latitude")
        lon = profile.get("lon") or profile.get("longitude")
        
        if lat is None and "geolocation" in profile:
            coords = profile["geolocation"].get("coordinates")
            if coords and len(coords) >= 2:
                lon = coords[0]
                lat = coords[1]

        date_str = profile.get("date") or profile.get("timestamp")
        cycle = profile.get("cycle_number", i + 1)
        profile_id = profile.get("_id", f"{wmo_id}_{cycle}")
        data_mode = profile.get("data_mode", "R")

        try:
            dt = pd.to_datetime(date_str, utc=True)
        except Exception:
            dt = None

        if dt:
            if first_date is None or dt < first_date:
                first_date = dt
            if last_date is None or dt > last_date:
                last_date = dt
                last_lat = lat
                last_lon = lon

        # Extract measurements
        measurements = profile.get("measurements", [])
        data = profile.get("data") # Can be dict or list of lists

        # Case 1: 'measurements' list of dicts (standard V2)
        if measurements:
             for m in measurements:
                rows.append({
                    "time": dt.to_pydatetime() if dt else None,
                    "latitude": lat,
                    "longitude": lon,
                    "depth": m.get("pres", m.get("pressure")),
                    "temperature": m.get("temp", m.get("temperature")),
                    "salinity": m.get("psal", m.get("salinity")),
                    "platform": wmo_id,
                    "cycle_number": cycle,
                    "profile_id": str(profile_id),
                    "data_mode": data_mode,
                })
             continue

        # Case 2: 'data' field (V1 or specialized V2)
        if data:
            pressures = []
            temps = []
            sals = []
            
            # Dictionary format {pressure: [...], temperature: [...]}
            if isinstance(data, dict):
                pressures = data.get("pres", data.get("pressure", []))
                temps = data.get("temp", data.get("temperature", []))
                sals = data.get("psal", data.get("salinity", []))
            
            # List format [[p1..pn], [t1..tn], [s1..sn]]
            # Order depends on query param &data=pressure,temperature,salinity
            elif isinstance(data, list) and len(data) >= 3:
                pressures = data[0]
                temps = data[1]
                sals = data[2]
            
            # Ensure valid lists
            if pressures and isinstance(pressures, list):
                length = len(pressures)
                # Pad if needed
                if not temps or len(temps) != length: temps = [None] * length
                if not sals or len(sals) != length: sals = [None] * length
                
                for j in range(length):
                    rows.append({
                        "time": dt.to_pydatetime() if dt else None,
                        "latitude": lat,
                        "longitude": lon,
                        "depth": pressures[j],
                        "temperature": temps[j],
                        "salinity": sals[j],
                        "platform": wmo_id,
                        "cycle_number": cycle,
                        "profile_id": str(profile_id),
                        "data_mode": data_mode,
                    })

    actual_region = region
    if last_lat is not None and last_lon is not None:
        actual_region = classify_region(last_lat, last_lon)

    metadata = {
        "wmo_id": wmo_id,
        "deploy_date": first_date.to_pydatetime() if first_date else None,
        "last_date": last_date.to_pydatetime() if last_date else None,
        "last_latitude": last_lat,
        "last_longitude": last_lon,
        "num_profiles": len(profiles),
        "ocean_region": actual_region,
        "status": "active",
    }

    return rows, metadata


def build_float_summary(metadata, stats):
    """Build a text summary for RAG indexing"""
    parts = [
        f"ARGO Float {metadata['wmo_id']} is located in the {metadata['ocean_region']}.",
    ]
    if metadata.get("last_latitude") and metadata.get("last_longitude"):
        parts.append(
            f"Last known position: {metadata['last_latitude']:.2f}°N, "
            f"{metadata['last_longitude']:.2f}°E."
        )
    if metadata.get("deploy_date"):
        parts.append(f"First profile recorded on {metadata['deploy_date'].strftime('%Y-%m-%d')}.")
    if metadata.get("last_date"):
        parts.append(f"Most recent profile on {metadata['last_date'].strftime('%Y-%m-%d')}.")
    parts.append(f"Total profiles collected: {metadata['num_profiles']}.")
    if stats:
        parts.append(
            f"Temperature range: {stats.get('temp_min', 'N/A'):.2f}°C to "
            f"{stats.get('temp_max', 'N/A'):.2f}°C."
        )
        parts.append(
            f"Salinity range: {stats.get('sal_min', 'N/A'):.2f} to "
            f"{stats.get('sal_max', 'N/A'):.2f} PSU."
        )
        parts.append(
            f"Depth range: {stats.get('depth_min', 0):.0f} to "
            f"{stats.get('depth_max', 0):.0f} dbar."
        )
    return " ".join(parts)


def ingest_to_db(all_rows, all_metadata):
    """Ingest parsed data into SQLite database"""
    print("\n[INFO] Creating database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        # Insert float metadata
        for meta in all_metadata:
            session.add(FloatMetadata(
                wmo_id=meta["wmo_id"],
                deploy_date=meta.get("deploy_date"),
                last_date=meta.get("last_date"),
                last_latitude=meta.get("last_latitude"),
                last_longitude=meta.get("last_longitude"),
                num_profiles=meta.get("num_profiles", 0),
                ocean_region=meta.get("ocean_region", "Indian Ocean"),
                status=meta.get("status", "active"),
                summary=meta.get("summary", ""),
            ))

        # Insert measurement records in batches
        batch_size = 500
        for i in range(0, len(all_rows), batch_size):
            batch = all_rows[i:i + batch_size]
            for row in batch:
                session.add(ArgoRecord(
                    time=row["time"],
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    depth=row["depth"],
                    temperature=row["temperature"],
                    salinity=row["salinity"],
                    platform=row["platform"],
                    cycle_number=row.get("cycle_number"),
                    profile_id=row.get("profile_id"),
                    data_mode=row.get("data_mode"),
                ))
            session.commit()
            print(f"[INFO] Committed batch {i // batch_size + 1} ({min(i + batch_size, len(all_rows))}/{len(all_rows)} rows)")

    print(f"[OK] Ingested {len(all_rows)} measurements from {len(all_metadata)} floats")


def fetch_all():
    """Main pipeline: fetch all Indian Ocean floats and return data"""
    float_list = INDIAN_OCEAN_FLOATS
    custom_floats = os.getenv("FLOAT_IDS", "")
    if custom_floats:
        float_list = [{"wmo": f.strip(), "region": "Indian Ocean"} for f in custom_floats.split(",")]

    all_rows = []
    all_metadata = []
    successful = 0

    print(f"[INFO] Fetching data for {len(float_list)} ARGO floats...\n")

    for entry in float_list:
        wmo = entry["wmo"]
        region = entry["region"]

        profiles = fetch_float_profiles(wmo, region)
        if not profiles:
            continue

        rows, metadata = parse_profiles(profiles, wmo, region)
        if not rows:
            print(f"[WARN] No measurements parsed for {wmo}")
            continue

        # STRICT: Reject floats outside Indian Ocean based on ACTUAL coordinates
        actual_region = metadata.get("ocean_region", "")
        if actual_region == "Outside Indian Ocean":
            lat_val = metadata.get("last_latitude")
            lon_val = metadata.get("last_longitude")
            print(f"[SKIP] Float {wmo} is at ({lat_val}, {lon_val}) — outside Indian Ocean, discarding")
            continue

        # Calculate stats for summary
        df_temp = pd.DataFrame(rows)
        stats = {}
        if "temperature" in df_temp.columns and df_temp["temperature"].notna().any():
            stats["temp_min"] = df_temp["temperature"].min()
            stats["temp_max"] = df_temp["temperature"].max()
        if "salinity" in df_temp.columns and df_temp["salinity"].notna().any():
            stats["sal_min"] = df_temp["salinity"].min()
            stats["sal_max"] = df_temp["salinity"].max()
        if "depth" in df_temp.columns and df_temp["depth"].notna().any():
            stats["depth_min"] = df_temp["depth"].min()
            stats["depth_max"] = df_temp["depth"].max()

        metadata["summary"] = build_float_summary(metadata, stats)
        all_rows.extend(rows)
        all_metadata.append(metadata)
        successful += 1
        print(f"[OK] Accepted {wmo} — {actual_region} ({len(rows)} measurements)")

        # Rate limiting
        time.sleep(1)

    print(f"\n[INFO] Summary: {successful}/{len(float_list)} floats accepted (Indian Ocean only), {len(all_rows)} measurements")
    return all_rows, all_metadata


if __name__ == "__main__":
    all_rows, all_metadata = fetch_all()

    if all_rows:
        ingest_to_db(all_rows, all_metadata)

        # Save CSV backup
        os.makedirs("data", exist_ok=True)
        df = pd.DataFrame(all_rows)
        df.to_csv("data/argo_indian_ocean.csv", index=False)
        print(f"[OK] Saved CSV: data/argo_indian_ocean.csv ({len(df)} rows)")

        print("\n[OK] Data pipeline complete!")
    else:
        print("[ERROR] No real data fetched from Argovis API.")
        print("[INFO] Check your internet connection and try again.")
        print("[INFO] No synthetic/fake data will be generated.")
