"""
Zoning and Plot Data Service for Indian Regions

Provides plot dimensions, floor restrictions, and zoning regulations
based on geographic location (lat/lng) for major Indian cities.
"""
from typing import Dict, Any, Optional, List
import math
from dataclasses import dataclass


@dataclass
class ZoningData:
    """Zoning regulations for a specific region"""
    city: str
    state: str
    zone_type: str  # residential, commercial, mixed, industrial
    max_floors: int
    max_height_m: float
    far_limit: float  # Floor Area Ratio
    ground_coverage_pct: float
    setback_front_m: float
    setback_side_m: float
    setback_rear_m: float
    min_plot_area_sqm: float
    max_plot_area_sqm: float
    typical_plot_width_m: float
    typical_plot_depth_m: float
    requires_fire_noc: bool
    notes: str


class ZoningService:
    """Service for providing zoning data based on geographic location"""
    
    def __init__(self):
        # Regional zoning database for major Indian cities
        self.zoning_db = self._build_zoning_database()
        
    def _build_zoning_database(self) -> Dict[str, ZoningData]:
        """Build zoning database for major Indian regions"""
        return {
            # Mumbai Metropolitan Region
            "mumbai_residential": ZoningData(
                city="Mumbai",
                state="Maharashtra",
                zone_type="residential",
                max_floors=4,
                max_height_m=15.0,
                far_limit=1.33,
                ground_coverage_pct=40,
                setback_front_m=3.0,
                setback_side_m=1.5,
                setback_rear_m=1.5,
                min_plot_area_sqm=45,
                max_plot_area_sqm=500,
                typical_plot_width_m=9.0,
                typical_plot_depth_m=12.0,
                requires_fire_noc=False,
                notes="CRZ regulations apply for coastal areas"
            ),
            "mumbai_commercial": ZoningData(
                city="Mumbai",
                state="Maharashtra",
                zone_type="commercial",
                max_floors=8,
                max_height_m=30.0,
                far_limit=2.0,
                ground_coverage_pct=50,
                setback_front_m=6.0,
                setback_side_m=3.0,
                setback_rear_m=3.0,
                min_plot_area_sqm=200,
                max_plot_area_sqm=2000,
                typical_plot_width_m=15.0,
                typical_plot_depth_m=20.0,
                requires_fire_noc=True,
                notes="Fire NOC required for buildings >15m height"
            ),
            
            # Delhi NCR
            "delhi_residential": ZoningData(
                city="Delhi",
                state="Delhi",
                zone_type="residential",
                max_floors=4,
                max_height_m=15.0,
                far_limit=2.0,
                ground_coverage_pct=50,
                setback_front_m=3.0,
                setback_side_m=3.0,
                setback_rear_m=3.0,
                min_plot_area_sqm=50,
                max_plot_area_sqm=400,
                typical_plot_width_m=10.0,
                typical_plot_depth_m=15.0,
                requires_fire_noc=False,
                notes="Master Plan 2021 regulations apply"
            ),
            "delhi_commercial": ZoningData(
                city="Delhi",
                state="Delhi",
                zone_type="commercial",
                max_floors=10,
                max_height_m=36.0,
                far_limit=3.5,
                ground_coverage_pct=60,
                setback_front_m=9.0,
                setback_side_m=6.0,
                setback_rear_m=6.0,
                min_plot_area_sqm=300,
                max_plot_area_sqm=5000,
                typical_plot_width_m=20.0,
                typical_plot_depth_m=25.0,
                requires_fire_noc=True,
                notes="Fire NOC mandatory for commercial buildings"
            ),
            
            # Bangalore
            "bangalore_residential": ZoningData(
                city="Bangalore",
                state="Karnataka",
                zone_type="residential",
                max_floors=4,
                max_height_m=15.0,
                far_limit=2.0,
                ground_coverage_pct=50,
                setback_front_m=3.0,
                setback_side_m=3.0,
                setback_rear_m=3.0,
                min_plot_area_sqm=60,
                max_plot_area_sqm=600,
                typical_plot_width_m=12.0,
                typical_plot_depth_m=18.0,
                requires_fire_noc=False,
                notes="BDA zoning regulations apply"
            ),
            "bangalore_commercial": ZoningData(
                city="Bangalore",
                state="Karnataka",
                zone_type="commercial",
                max_floors=8,
                max_height_m=24.0,
                far_limit=3.0,
                ground_coverage_pct=55,
                setback_front_m=6.0,
                setback_side_m=4.0,
                setback_rear_m=4.0,
                min_plot_area_sqm=250,
                max_plot_area_sqm=3000,
                typical_plot_width_m=18.0,
                typical_plot_depth_m=22.0,
                requires_fire_noc=True,
                notes="Fire NOC required for buildings >15m"
            ),
            
            # Chennai
            "chennai_residential": ZoningData(
                city="Chennai",
                state="Tamil Nadu",
                zone_type="residential",
                max_floors=4,
                max_height_m=15.0,
                far_limit=1.5,
                ground_coverage_pct=45,
                setback_front_m=3.0,
                setback_side_m=2.0,
                setback_rear_m=2.0,
                min_plot_area_sqm=55,
                max_plot_area_sqm=500,
                typical_plot_width_m=10.0,
                typical_plot_depth_m=15.0,
                requires_fire_noc=False,
                notes="CMDA regulations apply"
            ),
            "chennai_commercial": ZoningData(
                city="Chennai",
                state="Tamil Nadu",
                zone_type="commercial",
                max_floors=7,
                max_height_m=24.0,
                far_limit=2.5,
                ground_coverage_pct=50,
                setback_front_m=6.0,
                setback_side_m=4.0,
                setback_rear_m=4.0,
                min_plot_area_sqm=200,
                max_plot_area_sqm=2500,
                typical_plot_width_m=16.0,
                typical_plot_depth_m=20.0,
                requires_fire_noc=True,
                notes="Coastal Regulation Zone rules may apply"
            ),
            
            # Hyderabad
            "hyderabad_residential": ZoningData(
                city="Hyderabad",
                state="Telangana",
                zone_type="residential",
                max_floors=5,
                max_height_m=18.0,
                far_limit=2.0,
                ground_coverage_pct=50,
                setback_front_m=3.0,
                setback_side_m=3.0,
                setback_rear_m=3.0,
                min_plot_area_sqm=60,
                max_plot_area_sqm=600,
                typical_plot_width_m=12.0,
                typical_plot_depth_m=18.0,
                requires_fire_noc=False,
                notes="GHMC zoning regulations"
            ),
            "hyderabad_commercial": ZoningData(
                city="Hyderabad",
                state="Telangana",
                zone_type="commercial",
                max_floors=9,
                max_height_m=30.0,
                far_limit=3.0,
                ground_coverage_pct=55,
                setback_front_m=6.0,
                setback_side_m=4.0,
                setback_rear_m=4.0,
                min_plot_area_sqm=250,
                max_plot_area_sqm=3500,
                typical_plot_width_m=18.0,
                typical_plot_depth_m=22.0,
                requires_fire_noc=True,
                notes="Fire NOC mandatory for commercial"
            ),
            
            # Pune
            "pune_residential": ZoningData(
                city="Pune",
                state="Maharashtra",
                zone_type="residential",
                max_floors=4,
                max_height_m=15.0,
                far_limit=1.5,
                ground_coverage_pct=45,
                setback_front_m=3.0,
                setback_side_m=2.0,
                setback_rear_m=2.0,
                min_plot_area_sqm=50,
                max_plot_area_sqm=500,
                typical_plot_width_m=10.0,
                typical_plot_depth_m=15.0,
                requires_fire_noc=False,
                notes="PMC development control rules"
            ),
            "pune_commercial": ZoningData(
                city="Pune",
                state="Maharashtra",
                zone_type="commercial",
                max_floors=7,
                max_height_m=24.0,
                far_limit=2.5,
                ground_coverage_pct=50,
                setback_front_m=6.0,
                setback_side_m=4.0,
                setback_rear_m=4.0,
                min_plot_area_sqm=200,
                max_plot_area_sqm=2500,
                typical_plot_width_m=16.0,
                typical_plot_depth_m=20.0,
                requires_fire_noc=True,
                notes="Fire NOC required above 15m"
            ),
            
            # Kolkata
            "kolkata_residential": ZoningData(
                city="Kolkata",
                state="West Bengal",
                zone_type="residential",
                max_floors=4,
                max_height_m=15.0,
                far_limit=1.75,
                ground_coverage_pct=48,
                setback_front_m=3.0,
                setback_side_m=2.5,
                setback_rear_m=2.5,
                min_plot_area_sqm=50,
                max_plot_area_sqm=450,
                typical_plot_width_m=10.0,
                typical_plot_depth_m=14.0,
                requires_fire_noc=False,
                notes="KMC building rules apply"
            ),
            "kolkata_commercial": ZoningData(
                city="Kolkata",
                state="West Bengal",
                zone_type="commercial",
                max_floors=8,
                max_height_m=28.0,
                far_limit=2.75,
                ground_coverage_pct=52,
                setback_front_m=6.0,
                setback_side_m=4.0,
                setback_rear_m=4.0,
                min_plot_area_sqm=200,
                max_plot_area_sqm=3000,
                typical_plot_width_m=16.0,
                typical_plot_depth_m=20.0,
                requires_fire_noc=True,
                notes="Fire NOC mandatory for commercial"
            ),
            
            # Ahmedabad
            "ahmedabad_residential": ZoningData(
                city="Ahmedabad",
                state="Gujarat",
                zone_type="residential",
                max_floors=4,
                max_height_m=15.0,
                far_limit=1.5,
                ground_coverage_pct=45,
                setback_front_m=3.0,
                setback_side_m=2.0,
                setback_rear_m=2.0,
                min_plot_area_sqm=55,
                max_plot_area_sqm=500,
                typical_plot_width_m=10.0,
                typical_plot_depth_m=15.0,
                requires_fire_noc=False,
                notes="AUDA development plan rules"
            ),
            "ahmedabad_commercial": ZoningData(
                city="Ahmedabad",
                state="Gujarat",
                zone_type="commercial",
                max_floors=7,
                max_height_m=24.0,
                far_limit=2.5,
                ground_coverage_pct=50,
                setback_front_m=6.0,
                setback_side_m=4.0,
                setback_rear_m=4.0,
                min_plot_area_sqm=200,
                max_plot_area_sqm=2500,
                typical_plot_width_m=16.0,
                typical_plot_depth_m=20.0,
                requires_fire_noc=True,
                notes="Fire NOC required above 15m"
            ),
        }
    
    def _get_region_from_coordinates(self, lat: float, lng: float) -> Optional[str]:
        """
        Determine region/city from coordinates using bounding boxes
        Returns zoning key or None if not found
        """
        # City bounding boxes (approximate)
        city_bounds = {
            # Mumbai
            "mumbai": {"lat_min": 18.9, "lat_max": 19.3, "lng_min": 72.7, "lng_max": 73.0},
            # Delhi NCR
            "delhi": {"lat_min": 28.4, "lat_max": 28.9, "lng_min": 76.8, "lng_max": 77.4},
            # Bangalore
            "bangalore": {"lat_min": 12.8, "lat_max": 13.2, "lng_min": 77.4, "lng_max": 77.8},
            # Chennai
            "chennai": {"lat_min": 12.9, "lat_max": 13.3, "lng_min": 80.1, "lng_max": 80.4},
            # Hyderabad
            "hyderabad": {"lat_min": 17.2, "lat_max": 17.6, "lng_min": 78.2, "lng_max": 78.6},
            # Pune
            "pune": {"lat_min": 18.4, "lat_max": 18.6, "lng_min": 73.7, "lng_max": 74.1},
            # Kolkata
            "kolkata": {"lat_min": 22.4, "lat_max": 22.7, "lng_min": 88.2, "lng_max": 88.5},
            # Ahmedabad
            "ahmedabad": {"lat_min": 22.9, "lat_max": 23.1, "lng_min": 72.5, "lng_max": 72.7},
        }
        
        # Find which city the coordinates fall within
        for city, bounds in city_bounds.items():
            if (bounds["lat_min"] <= lat <= bounds["lat_max"] and
                bounds["lng_min"] <= lng <= bounds["lng_max"]):
                return city
        
        return None
    
    def get_zoning_data(self, lat: float, lng: float, zone_type: str = "residential") -> Optional[ZoningData]:
        """
        Get zoning data for a specific location and zone type
        
        Args:
            lat: Latitude
            lng: Longitude
            zone_type: "residential" or "commercial"
        
        Returns:
            ZoningData object or None if location not found
        """
        city = self._get_region_from_coordinates(lat, lng)
        if not city:
            # Return default zoning data for unknown locations
            return ZoningData(
                city="Unknown",
                state="Unknown",
                zone_type=zone_type,
                max_floors=4 if zone_type == "residential" else 8,
                max_height_m=15.0 if zone_type == "residential" else 24.0,
                far_limit=2.0 if zone_type == "residential" else 3.0,
                ground_coverage_pct=50,
                setback_front_m=3.0,
                setback_side_m=3.0,
                setback_rear_m=3.0,
                min_plot_area_sqm=50,
                max_plot_area_sqm=500,
                typical_plot_width_m=10.0,
                typical_plot_depth_m=15.0,
                requires_fire_noc=zone_type == "commercial",
                notes="Default zoning - verify with local authorities"
            )
        
        zoning_key = f"{city}_{zone_type}"
        return self.zoning_db.get(zoning_key)
    
    def get_all_cities(self) -> List[Dict[str, Any]]:
        """Get list of all supported cities with their coordinates"""
        city_centers = {
            "Mumbai": {"lat": 19.076, "lng": 72.8777, "state": "Maharashtra"},
            "Delhi": {"lat": 28.7041, "lng": 77.1025, "state": "Delhi"},
            "Bangalore": {"lat": 12.9716, "lng": 77.5946, "state": "Karnataka"},
            "Chennai": {"lat": 13.0827, "lng": 80.2707, "state": "Tamil Nadu"},
            "Hyderabad": {"lat": 17.3850, "lng": 78.4867, "state": "Telangana"},
            "Pune": {"lat": 18.5204, "lng": 73.8567, "state": "Maharashtra"},
            "Kolkata": {"lat": 22.5726, "lng": 88.3639, "state": "West Bengal"},
            "Ahmedabad": {"lat": 23.0225, "lng": 72.5714, "state": "Gujarat"},
        }
        
        return [
            {"name": name, **coords}
            for name, coords in city_centers.items()
        ]


# Global instance
zoning_service = ZoningService()
