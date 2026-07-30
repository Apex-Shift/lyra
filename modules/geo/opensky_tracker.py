from typing import Any, Dict
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "OpenSky ADS-B Live Aircraft Monitor",
        "description": "Télécharge les télémétries de vol (ADS-B) en temps réel sur un rayon géographique spécifique.",
        "author": "Lyra Core Dev Team",
        "category": "geo"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["LATITUDE"] = Option(50.62925, required=True, description="Latitude du centre de la zone d'intérêt")
        self.options["LONGITUDE"] = Option(3.05725, required=True, description="Longitude du centre de la zone d'intérêt")
        self.options["DELTA"] = Option(1.0, required=False, description="Périmètre de détection en degrés (~100km)")

    async def run(self) -> Dict[str, Any]:
        lat = float(self.options["LATITUDE"].value)
        lon = float(self.options["LONGITUDE"].value)
        delta = float(self.options["DELTA"].value)

        # Calcul des limites de la bounding box
        lamin, lamax = lat - delta, lat + delta
        lomin, lomax = lon - delta, lon + delta

        url = f"https://opensky-network.org/api/states/all?lamin={lamin}&lamax={lamax}&lomin={lomin}&lomax={lomax}"
        print(f"[*] Analyse du trafic aérien ADS-B sur BBox : [{lamin}, {lamax}, {lomin}, {lomax}]...")

        client = self.core.network_director.get_authenticated_client()
        detected_aircrafts = []

        try:
            async with client as session:
                resp = await session.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    states = data.get("states") or []
                    for s in states:
                        icao24 = s[0]
                        callsign = s[1].strip() if s[1] else "N/A"
                        origin_country = s[2]
                        altitude = s[7]
                        velocity = s[9]

                        aircraft_info = {
                            "icao24": icao24,
                            "callsign": callsign,
                            "country": origin_country,
                            "altitude_m": altitude,
                            "velocity_ms": velocity
                        }
                        detected_aircrafts.append(aircraft_info)

                        # Injection dans le graphe d'investigation
                        node_id = f"aircraft_{icao24}"
                        await self.core.context.add_entity(node_id, "Aircraft", f"{callsign} ({icao24})", aircraft_info)
                else:
                    return {"status": "error", "message": f"Erreur API OpenSky: {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"Échec de connexion : {e}"}

        print(f"[+] {len(detected_aircrafts)} aéronef(s) localisé(s) dans la zone d'intérêt.")
        return {
            "center": {"lat": lat, "lon": lon},
            "total_aircrafts": len(detected_aircrafts),
            "aircrafts": detected_aircrafts
        }