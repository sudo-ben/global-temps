def gen_geocode_get_lat_long_file():
    """
    Geocode.xyz uses only open data sources, including but not limited to OpenStreetMap, Geonames, Osmnames, openaddresses.io, UK Ordnance Survey, www.dati.gov.it, data.europa.eu/euodp/en/data, PSMA Geocoded National Address File (Australia), etc..
    You may cache our geocodes, display results on any map, store them however you want for as long as you want, use them however you want, even commercially - unless you wish to resell our services.
    """

    df = preprocess(load_data)

    df["web_key"] = (
        df["City"].astype("string")
        + ","
        + np.where(df["State"].isnull(), "", df["State"].astype("string") + ",")
        + df["Country"].astype("string")
    )

    country_cities = df[
        ["Country", "State", "City", "CityCountry", "web_key"]
    ].drop_duplicates()

    print(country_cities)

    all_data = {}
    with open("cities_lat_long.json", "r", encoding="utf-8") as f:
        all_data = json.load(f)

    for _i, row in country_cities.iterrows():
        country_query = urllib.parse.quote(row["web_key"])
        print(country_query)
        if str(row["CityCountry"]) not in all_data:
            url = f"https://geocode.xyz/{country_query}?json=True"
            print(url)

            try:
                with urllib.request.urlopen(url) as url_responce:
                    data = json.loads(url_responce.read().decode())
                    print(data)
                    all_data[str(row["CityCountry"])] = data
                with open("cities_lat_long.json", "w", encoding="utf-8") as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=4)
                time.sleep(5)
            except:
                time.sleep(60)
