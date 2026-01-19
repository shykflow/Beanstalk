import math

EARTH_RADIUS_IN_KILOMETERS = 6371
EARTH_RADIUS_IN_MILES = 3959

# Latitude lines run horizontally parallel to equator
# They measure distance north or south of equator
MIN_LATITUDE = -90
MAX_LATITUDE = 90

# Longitude lines run vertically from pole to pole
# They measure distance east or west of prime meridian
MIN_LONGITUDE = -180
MAX_LONGITUDE = 180

class EarthHelper:
    def __init__(self, use_kilometers: bool = False):
        if use_kilometers:
            self.earth_radius = EARTH_RADIUS_IN_KILOMETERS
            self._approximate_latitude_distance = 111
            self._approximate_longitude_distance = 87.9
        else:
            self.earth_radius = EARTH_RADIUS_IN_MILES
            self._approximate_latitude_distance = 69
            self._approximate_longitude_distance = 54.6

    @staticmethod
    def valid_coordinates(lat: float | int, lng: float | int) -> bool:
        """
        Returns whether `lat` and `lng` are valid coordinates.

        `lat` and `lng` must be a float or int type.
        If not, the coordinates are considered invalid.
        """
        valid_types = (float, int)
        if not isinstance(lat, valid_types) or not isinstance(lng, valid_types):
            return False
        return MIN_LATITUDE <= lat <= MAX_LATITUDE and \
            MIN_LONGITUDE <= lng <= MAX_LONGITUDE

    def haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculates and returns the great circle distance between two points on Earth.

        See https://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
        """
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        lat_diff = lat2 - lat1
        lng_diff = lng2 - lng1
        a = math.sin(lat_diff/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(lng_diff/2)**2
        return 2 * math.asin(math.sqrt(a)) * self.earth_radius

    def distance_to_latitude(self, distance: float | int) -> float:
        """
        Return the approximate degrees latitude represented by `distance`.

        Distance between latitude lines remain fairly constant so this should be a good approximation.

        See https://www.usgs.gov/faqs/how-much-distance-does-degree-minute-and-second-cover-your-maps

        """
        return distance / self._approximate_latitude_distance

    def distance_to_longitude(self, distance: float | int) -> float:
        """
        Return the approximate degrees longitude represented by `distance`.

        Distances between longitude lines converge toward the poles,
        so this method will tend to overestimate the distance between longitudes close to the poles.

        See https://www.usgs.gov/faqs/how-much-distance-does-degree-minute-and-second-cover-your-maps

        """
        return distance / self._approximate_longitude_distance
