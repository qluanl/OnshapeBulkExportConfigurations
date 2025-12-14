# Onshape Bulk Export Part Studio Configurations

This script uses the Onshape API to export all part studio configurations as STLs to an out/ directory.

Git clone/download the repository

Generate an API Key by going to the [Onshape Dev Portal](https://cad.onshape.com/appstore/dev-portal)

Create an secrets.env file with the following:

```
ONSHAPE_ACCESS_KEY=
ONSHAPE_SECRET_KEY=
WVM=w
```

Open a part studio and note the URL:

```
https://cad.onshape.com/documents/<Document ID>/w/<WVMID>/e/<EID>
```

Run

```bash
python3 -m venv .venv
source .venv/bin/activate

pip3 install -r requirements.txt
python3 exportConfigs.py <URL-OF-PART-STUDIO>
```

The script will ask you for the part and configuration inputs you want, outputting to out/.

#### Supported Config and Limitations
- This script currently supports multiple list configurations and generates their Cartesian combinations.
- Checkbox (boolean) configurations are allowed in the Part Studio but are not yet supported for export; i.e., you cannot select them in the inquire. (TODO)
- Variable configuration is not allowed in the Part Studio. (TODO)
- Configuration visibility conditions are not tested. It may or may not be acceptable to have conditions in the Part Studio.


## How it works
(This section needs revision)

```
1. Use the parts endpoint to grab the partID:
    partURL = f"https://cad.onshape.com/api/v12/parts/d/{DID}/{WVM}/{WVMID}/e/{EID}?withThumbnails=false&includePropertyDefaults=false"

2. Get all configurations for the part studio
    configurationURL = f"https://cad.onshape.com/api/v12/elements/d/{DID}/{WVM}/{WVMID}/e/{EID}/configuration"

    data = response.json()
    allConfigurationsOptions = data["configurationParameters"][0]["options"]

3. For each option, encode a configuration string to use for API requests
    encodeConfigurationURL = f"https://cad.onshape.com/api/v12/elements/d/{DID}/e/{EID}/configurationencodings"
    headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}
    payload = {
        "parameters": [
            {
                "parameterId": data["configurationParameters"][0]["parameterId"],
                "parameterValue": option["option"],
            }
        ],
    }

4. Get a 307 redirect URL for each option with the encoded configuration string
    getSTLURL = f"https://cad.onshape.com/api/v12/partstudios/d/{DID}/{WVM}/{WVMID}/e/{EID}/stl?partIds={partID}&version=0&includeExportIds=false&configuration={encodedId}&binaryExport=false"
    headers = {
        "Authorization": f"Basic {token}",
        "Accept": "*/*",
    }

    response = requests.get(getSTLURL, headers=headers, allow_redirects=False)

5. Authenticate and stream the redirect file
    download_url = response.headers["Location"]
    print("Download URL:", download_url)

    file_path = os.path.join("out", option["optionName"] + ".stl")
    with requests.get(download_url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


```


### Known Bugs

1. In a very complex Part Studio, when selecting from the “M Size” list (a parsed Python object shown below), choosing options with a decimal M size (e.g., M1.2) causes a download error (HTTP 400) with the message “No visible parts to export.” Other options (such as M2 or M3) download successfully. This bug is suspected to be caused by either the format of the option value or the decimal point in the option name.
Configuration List:
```python
{
    'btType': 'BTMConfigurationParameterEnum-105', 
    'parameterId': 'List_GiBqxlXSWl3t5r', 
    'enumName': 'List_GiBqxlXSWl3t5r_conf', 
    'isCosmetic': False, 
    'enumOptionVisibilityConditions': {
        'btType': 'BTEnumOptionVisibilityConditionList-2936', 'visibilityConditions': []
    }, 
    'defaultValue': 'M1', 
    'namespace': '', 
    'options': [
        {'btType': 'BTMEnumOption-592', 'optionName': 'M1', 'option': 'M1', 'nodeId': 'M5FKlYJQNpnFurlRb'}, 
        {'btType': 'BTMEnumOption-592', 'optionName': 'M1.2', 'option': 'M1_2', 'nodeId': 'MJLQhRSRB7hinalsf'}, 
        {'btType': 'BTMEnumOption-592', 'optionName': 'M1.4', 'option': 'M1_4', 'nodeId': 'MNEuK3byjT9ugSb2K'}, 
        {'btType': 'BTMEnumOption-592', 'optionName': 'M1.6', 'option': 'M1_6', 'nodeId': 'MKtqlo85Iq31ezLIi'}, 
        {'btType': 'BTMEnumOption-592', 'optionName': 'M1.8', 'option': 'M1_8', 'nodeId': 'MEht79qoDnEkYB8op'}, 
        {'btType': 'BTMEnumOption-592', 'optionName': 'M2', 'option': 'M2', 'nodeId': 'MhpODijB+9XDT6amY'}, 
        {'btType': 'BTMEnumOption-592', 'optionName': 'M2.5', 'option': 'M2_5', 'nodeId': 'MPPiPL3VBZ2pbMvK4'}, 
        {'btType': 'BTMEnumOption-592', 'optionName': 'M3', 'option': 'M3', 'nodeId': 'Mslujpxyqdc88G9zP'}, 
        {'btType': 'BTMEnumOption-592', 'optionName': 'M3.5', 'option': 'M3_5', 'nodeId': 'MLWDC8FZ6azvYfFiT'}, 
        {'btType': 'BTMEnumOption-592', 'optionName': 'M4', 'option': 'M4', 'nodeId': 'MquGeb+H4+iYl8kwj'}, 
        {'btType': 'BTMEnumOption-592', 'optionName': 'M5', 'option': 'M5', 'nodeId': 'MGT1DhBglkVDEp+F3'}, 
        {'btType': 'BTMEnumOption-592', 'optionName': 'M6', 'option': 'M6', 'nodeId': 'Mqs2/Sgh6SJxbKgS7'}, 
        {'btType': 'BTMEnumOption-592', 'optionName': 'M8', 'option': 'M8', 'nodeId': 'M3E4FeHKEvudibV1o'}
    ], 
    'nodeId': 'Mo5eLhRG64Zu8uns/', 
    'parameterName': 'M Size', 
    'visibilityCondition': {'btType': 'BTParameterVisibilityCondition-177'}
}
```
And error response:
```
body: {
  "moreInfoUrl" : "",
  "message" : "No visible parts to export",
  "status" : 400,
  "code" : 0
}
```