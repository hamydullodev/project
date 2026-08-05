from app.api.geoapify import GeoapifyClient


def test_parse_feature_extracts_iata_from_osm_raw_tag():
    feature = {
        "geometry": {"coordinates": [69.281, 41.257]},
        "properties": {
            "name": "Tashkent International Airport",
            "city": "Tashkent",
            "country": "Uzbekistan",
            "datasource": {"raw": {"iata": "tas"}},
        },
    }

    airport = GeoapifyClient._parse_feature(feature)

    assert airport.iata_code == "TAS"
    assert airport.city == "Tashkent"
    assert airport.latitude == 41.257
    assert airport.longitude == 69.281


def test_parse_feature_without_iata_tag_is_empty_not_guessed():
    feature = {
        "geometry": {"coordinates": [0.0, 0.0]},
        "properties": {"name": "Some Airfield", "datasource": {"raw": {}}},
    }

    airport = GeoapifyClient._parse_feature(feature)

    assert airport.iata_code == ""
