import requests

# Electricity Maps API Key
key = "TSp6BpVHdhrPS95s8X4j"

# API Request
response = requests.get(
    "https://api.electricitymap.org/v3/carbon-intensity/latest",
    headers={
        "auth-token": key
    },
    params={
        "zone": "IN-SO"
    }
)

# Print response
print("Status Code:", response.status_code)
print("Response:")

data = response.json()
print(data)

# Optional formatted output
if response.status_code == 200:
    print("\nCarbon Intensity Details")
    print("-------------------------")
    print("Zone:", data.get("zone"))
    print("Carbon Intensity:", data.get("carbonIntensity"), "gCO2eq/kWh")
    print("Datetime:", data.get("datetime"))
else:
    print("\nError:", data.get("message"))