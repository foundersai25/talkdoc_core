from core.talkdoc_core.prompts import get_chat_history_to_json_prompt

import json
import logging
import os
import requests
from agno.tools import tool

logging.basicConfig(level=logging.INFO)


# Standalone Tool-Funktion für Agno (außerhalb der Klasse)
@tool
def validate_address(address_string: str) -> str:
    """
    Validiert eine Adresse oder einen Ort und gibt die korrekte, vollständige Adresse zurück.
    Fokus auf Straßen und Städte, nicht auf Geschäfte oder POIs.
    
    Args:
        address_string (str): Die zu validierende Adresse oder der Ort (z.B. "Berliner Str. 123, Hamburg" oder "München")
        
    Returns:
        str: Validierungsergebnis mit korrekter Adresse oder Fehlermeldung
    """
    logging.info(f"🗺️ Adressvalidierung gestartet für: '{address_string}'")
    
    google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    if not google_maps_api_key:
        logging.error("❌ Google Maps API Key nicht verfügbar")
        return "❌ Google Maps API Key nicht verfügbar. Adressvalidierung nicht möglich."
    
    try:
        # Google Geocoding API für Adressvalidierung
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': address_string,
            'key': google_maps_api_key,
            'language': 'de',
            'region': 'de'  # Bevorzuge deutsche Ergebnisse
        }
        
        logging.info(f"📡 Google Maps API Aufruf für: {address_string}")
        response = requests.get(url, params=params)
        data = response.json()
        logging.info(f"📊 Google Maps API Status: {data.get('status', 'Unknown')}")
        
        if data['status'] == 'OK' and data['results']:
            result = data['results'][0]
            
            # Extrahiere relevante Adressteile
            address_components = result.get('address_components', [])
            formatted_address = result.get('formatted_address', '')
            
            # Prüfe ob es sich um eine gültige Straße/Stadt handelt
            has_street = any(
                'route' in component.get('types', []) 
                for component in address_components
            )
            has_locality = any(
                'locality' in component.get('types', []) or 
                'administrative_area_level_1' in component.get('types', []) or
                'administrative_area_level_2' in component.get('types', [])
                for component in address_components
            )
            
            # Extrahiere Stadt und Land
            city = ""
            country = ""
            postal_code = ""
            
            for component in address_components:
                types = component.get('types', [])
                if 'locality' in types:
                    city = component.get('long_name', '')
                elif 'country' in types:
                    country = component.get('long_name', '')
                elif 'postal_code' in types:
                    postal_code = component.get('long_name', '')
            
            # Formatiere die Antwort
            if has_street or has_locality:
                result_text = f"✅ **Adresse gefunden und validiert:**\n"
                result_text += f"📍 {formatted_address}\n"
                
                if city:
                    result_text += f"🏙️ Stadt: {city}\n"
                if postal_code:
                    result_text += f"📮 PLZ: {postal_code}\n"
                if country and country != "Deutschland":
                    result_text += f"🌍 Land: {country}\n"
                
                return result_text
            else:
                return f"⚠️ '{address_string}' wurde gefunden, scheint aber kein Straßen-/Stadtname zu sein."
                
        elif data['status'] == 'ZERO_RESULTS':
            return f"❌ Adresse nicht gefunden: '{address_string}' existiert nicht oder ist unvollständig."
        else:
            return f"❌ Fehler bei der Adressvalidierung: {data.get('status', 'Unbekannter Fehler')}"
            
    except Exception as e:
        logging.error(f"Google Geocoding API Fehler: {e}")
        return f"❌ Fehler bei der Adressvalidierung: {str(e)}"


# Hilfsfunktion für API Key Validierung
def check_google_maps_api_key(api_key: str = None) -> bool:
    """Prüft, ob der Google Maps API Key gültig ist."""
    test_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
    if not test_key:
        return False
    return len(test_key) > 10 and test_key.startswith(('AIza', 'Goog'))


def get_json_from_chat_history_agent(gpt, messages_history, orig_parsed_json_fields):
    instructions = get_chat_history_to_json_prompt(
        messages_history, orig_parsed_json_fields
    )

    messages = gpt.add_user_prompt([], instructions)

    json_res = gpt.chat(messages, stream=False, json_mode=True)
    json_res = json.loads(json_res)
    logging.info(json_res)
    return json_res
