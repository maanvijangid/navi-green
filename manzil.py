import requests
import folium
import polyline
import time
import os

# API Keys (Store in environment variables for security)
AQICN_API_KEY = os.getenv("AQICN_API_KEY", "your_aqicn_api_key")
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "your_tomtom_api_key")
OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving"

CO2_PER_LITER = 2.31  # kg CO2 per liter of gasoline

class RouteOptimizer:
    @staticmethod
    def get_weather_data(lat, lon):
        try:
            url = f"https://api.waqi.info/feed/geo:{lat};{lon}/"
            response = requests.get(url, params={"token": AQICN_API_KEY})
            response.raise_for_status()
            data = response.json()
            return data["data"]["aqi"] if data["status"] == "ok" else None
        except Exception as e:
            raise RuntimeError(f"Weather data fetch failed: {e}")

    @staticmethod
    def calculate_route(origin, destination, retries=3):
        for _ in range(retries):
            try:
                url = f"{OSRM_BASE_URL}/{origin};{destination}"
                response = requests.get(url, params={"overview": "full", "alternatives": "true"})
                response.raise_for_status()
                data = response.json()
                if "routes" in data:
                    return [
                        {"geometry": polyline.decode(route["geometry"]), "distance": route["distance"] / 1000}
                        for route in data["routes"]
                    ]
            except Exception as e:
                print(f"Error fetching route: {e}. Retrying...")
                time.sleep(2)
        raise RuntimeError("Failed to fetch routes after retries.")

    @staticmethod
    def estimate_emissions(distance_km, fuel_efficiency):
        total_fuel_used = distance_km / fuel_efficiency
        return total_fuel_used * CO2_PER_LITER

    @staticmethod
    def plot_routes_on_map(routes, origin_coords, destination_coords, map_name="routes_map.html"):
        map_ = folium.Map(location=origin_coords, zoom_start=13)
        colors = ["blue", "green", "red"]
        for idx, route in enumerate(routes):
            folium.PolyLine(route["geometry"], color=colors[idx % len(colors)], weight=2.5).add_to(map_)
            folium.Marker(route["geometry"][0], icon=folium.Icon(color=colors[idx % len(colors]))).add_to(map_)
        map_.save(map_name)
        print(f"Map saved as {map_name}")

    @staticmethod
    def get_traffic_data(origin, destination):
        try:
            url = f"https://api.tomtom.com/routing/1/calculateRoute/{origin}:{destination}/json"
            response = requests.get(url, params={"key": TOMTOM_API_KEY, "traffic": "true"})
            response.raise_for_status()
            data = response.json()
            return data["routes"][0]["summary"]["trafficTimeInSeconds"] / 60  # min
        except Exception as e:
            raise RuntimeError(f"Traffic data fetch failed: {e}")


def main():
    try:
        origin_coords = (12.9715987, 77.5945627)
        destination_coords = (13.0826802, 80.2707184)
        origin = f"{origin_coords[1]},{origin_coords[0]}"
        destination = f"{destination_coords[1]},{destination_coords[0]}"
        fuel_efficiency = float(input("Enter vehicle fuel efficiency (km per liter): "))

        aqi = RouteOptimizer.get_weather_data(origin_coords[0], origin_coords[1])
        print(f"AQI at origin: {aqi}")

        routes = RouteOptimizer.calculate_route(origin, destination)
        for idx, route in enumerate(routes[:2]):
            emissions = RouteOptimizer.estimate_emissions(route["distance"], fuel_efficiency)
            print(f"Route {idx + 1}: Distance = {route['distance']:.2f} km, Emissions = {emissions:.2f} kg CO2")

        RouteOptimizer.plot_routes_on_map(routes, origin_coords, destination_coords)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
