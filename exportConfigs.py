import os
import base64
import requests
import wget
from dotenv import load_dotenv
import sys
import re # For URL parse
from itertools import product # For config parameters combo generating

load_dotenv("secrets.env")

ACCESS_KEY = os.getenv("ONSHAPE_ACCESS_KEY")
SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY")
# DID = os.getenv("DOCUMENT_ID")
WVM = os.getenv("WVM")
# WVMID = os.getenv("WVMID")
# EID = os.getenv("EID")

# ANSI color codes for error and warning
HIGHLIGHT = "\033[1;33m"
RED     = "\033[0;31m"
GREEN   = "\033[0;32m"
YELLOW  = "\033[0;33m"
BLUE    = "\033[0;34m"
MAGENTA = "\033[0;35m"
CYAN    = "\033[0;36m"
NC      = "\033[0m" # No Color
SUCCEED = f"{GREEN}[Succeed]{NC} "
WARNING = f"{YELLOW}[Warning]{NC} "
ERROR   = f"{RED}[ Error ]{NC} "
INFO    = f"{BLUE}[ Info. ]{NC} "
INQUIRE = f"{MAGENTA}[Inquire]{NC} "
PROGRES = f"{CYAN}[Progres]{NC} "

def extract_IDs(url: str):
    pattern = rf"/documents/([^/]+)/{WVM}/([^/]+)/e/([^/]+)"
    match = re.search(pattern, url)
    if match:
        document_id, w_id, e_id = match.groups()
        return {
            "DID": document_id,
            "WVMID": w_id,
            "EID": e_id
        }
    else:
        raise ValueError("URL format should be https://cad.onshape.com/documents/<Document ID>/w/<WVMID>/e/<EID>")
def iter_payloads_with_name(configParameters):
    """
    configParameters Example:
    [
      {"parameterId": "color", "options": [{"option": "Red", "optionName": "Red"}, {"option": "Blue", "optionName": "Blue"}]},
      {"parameterId": "size",  "options": [{"option": "S", "optionName": "Small"}, {"option": "M", "optionName": "Medium"}]},
    ]

    Output:
    {
      "name": "Red x Small",
      "parameters": [
        {"parameterId": "color", "parameterValue": "Red"},
        {"parameterId": "size",  "parameterValue": "S"},
      ]
    }
    """
    per_cp_items = []
    for cp in configParameters:
        pID = cp["parameterId"]
        pName = cp["parameterName"]
        opts = cp["options"]
        # Generate: (Parameter fragment, display name) for each option of this cp
        items = [
            ({"parameterId": pID, "parameterValue": opt["option"]}, opt["optionName"])
            for opt in opts if "option" in opt
        ]
        per_cp_items.append(items)

    # Do the Cartesian product; Each element is several (param_item, display_name)
    for combo in product(*per_cp_items):
        params = [p for p, _disp in combo]
        names  = [disp for _p, disp in combo]
        yield {
            "name": " x ".join(names),
            "parameters": params
        }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    try:
        result = extract_IDs(url)
        DID = result["DID"]
        WVMID = result["WVMID"]
        EID = result["EID"]
    except ValueError as e:
        print(ERROR, e)

    token = base64.b64encode(f"{ACCESS_KEY}:{SECRET_KEY}".encode()).decode()

    ## Get partID
    partURL = f"https://cad.onshape.com/api/v12/parts/d/{DID}/{WVM}/{WVMID}/e/{EID}?withThumbnails=false&includePropertyDefaults=false"
    headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}
    response = requests.get(partURL, headers=headers)

    # print(response.status_code, response.json())

    data = response.json()
    ## Choose the part to export
    if len(data)==1:
        selectionInput = 0
        print(f"{INFO}Found only one part: {data[selectionInput]["name"]}. Skip choose")
    else:
        print(f"{INFO}Found multiple parts:")
        for idx, part in enumerate(data, start=1):
            print(f"{GREEN}{idx}){NC} {part['name']}")
        while True:
            selectionInput = input(f"{INQUIRE}Please select part to be exported:").strip()
            if selectionInput.isdigit() and int(selectionInput)>=0 and int(selectionInput)<=len(data):
                selectionInput = int(selectionInput) - 1
                print(f"{INFO}Chosen part: {GREEN}{data[selectionInput]["name"]}{NC}")
                break
            else:
                print(f"{ERROR}Cannot parse input, try again.")
    partID = data[selectionInput]["partId"]
    partName = data[selectionInput]["name"]

    ## Get all available configuration options
    configurationURL = f"https://cad.onshape.com/api/v12/elements/d/{DID}/{WVM}/{WVMID}/e/{EID}/configuration"
    response = requests.get(configurationURL, headers=headers)

    # print(response.status_code, response.json())
    # print(response.json(), file=open("response.json","w"))

    data = response.json()

    ## Show configuration parameters and ask user to choose
    print(f"{INFO}Found configurations: (with {HIGHLIGHT}default option{NC})")
    print(f"{GREEN}0){NC} Select All")
    for idx, configParameter in enumerate(data["configurationParameters"], start=1):
        configType = configParameter["btType"]
        defaultOpt = configParameter["defaultValue"]
        if configType == "BTMConfigurationParameterEnum-105": # List Configuration
            optionNames = [
                f"{HIGHLIGHT}{opt['optionName']}{NC}"
                if opt["option"] == defaultOpt
                else opt["optionName"]
                for opt in configParameter["options"]
            ]
        elif configType == "BTMConfigurationParameterBoolean-2550": # Check (Bool) Configuration
            optionNames = [f"{HIGHLIGHT}{str(defaultOpt)}{NC}", str(not defaultOpt)]

        # Display configuration
        print(f"{GREEN}{idx}){NC} {configParameter['parameterName']} : {', '.join(optionNames)}")
    while True:
        selectionInput = input(f"{INQUIRE}Please select configuration inputs to be exported (use , to seperate multiple selections, 0 means all):\n").strip()
        configParameterIndicesRaw = [int(x.strip()) for x in selectionInput.split(",") if x.strip().isdigit()]
        configParameterIndices = [x for x in configParameterIndicesRaw if x>=0 and x<=len(data["configurationParameters"])]
        if len(configParameterIndices)>0:
            break
        else:
            print(f"{ERROR}Cannot parse input, try again.")

    if 0 in configParameterIndices:
        chosenConfigParameters = data["configurationParameters"]
    else:
        chosenConfigParameters = [data["configurationParameters"][i - 1] for i in configParameterIndices]
    print(f"{INFO}Seleted configuration inputs are: {GREEN}{', '.join([cp['parameterName'] for cp in chosenConfigParameters])}{NC}")


    ## Check total number of combinations
    total = 1
    for cp in chosenConfigParameters:
        total *= len(cp["options"])
    if total > 42:
        confirm = input(f"{WARNING}{total} many combinations to be downloaded, are you sure? [Y/n]")
        if confirm.strip().lower() != 'y':
            print("Exiting.")
            exit(0)
    else:
        print(f"{INFO}Downloading {total} combinations...")

    for payload in iter_payloads_with_name(chosenConfigParameters):
        # print(payload)

        ## Get encoded configuration string
        encodeConfigurationURL = f"https://cad.onshape.com/api/v12/elements/d/{DID}/e/{EID}/configurationencodings"

        response = requests.post(encodeConfigurationURL, headers=headers, json=payload)

        encodedId = response.json()["encodedId"]
        queryParam = response.json()["queryParam"]

        # print(encodedId, queryParam)

        ## Export part as STL Synchronously
        getSTLURL = f"https://cad.onshape.com/api/v12/partstudios/d/{DID}/{WVM}/{WVMID}/e/{EID}/stl?partIds={partID}&mode=binary&grouping=true&units=millimeter&configuration={encodedId}"
        exportHeaders = {
            "Authorization": f"Basic {token}",
            "Accept": "*/*",
        }

        response = requests.get(getSTLURL, headers=exportHeaders, allow_redirects=False)

        os.makedirs("out", exist_ok=True)
        try:
            download_url = response.headers["Location"]
            # print("Download URL:", download_url)
        except Exception as e:
            print(f"{ERROR}Bad response of STL exporting.")
            print("Exception:", repr(e))
            print("Status:", response.status_code)
            # print("Headers:", response.headers)
            print("Body:", response.text[:1000])
            raise


        file_name = partName + "-" + payload["name"] + ".stl"
        file_path = os.path.join("out", file_name)

        ## Download - stop with error
        # with requests.get(download_url, headers=exportHeaders, stream=True) as r:
        #     r.raise_for_status()
        #     with open(file_path, "wb") as f:
        #         for chunk in r.iter_content(chunk_size=8192):
        #             f.write(chunk)

        ## Download - print and continue with error
        with requests.get(download_url, headers=exportHeaders, stream=True) as r:
            if not r.ok:
                print("\n[Error] status:", r.status_code)
                print("[Error] url:", r.url)
                try:
                    print("[Error] body:", r.text)  # Onshape error message
                except Exception:
                    pass
                
                # r.raise_for_status()  # Raise error OR continue
                continue
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        print(f"{PROGRES}Downloaded: {file_name}")
    

    file_name_example = partName + "-" + " x ".join([cp['parameterName'] for cp in chosenConfigParameters])
    print("File name pattern:\n"+file_name_example, file=open(os.path.join("out", file_name_example+".txt"),"w"))
    print(f"{SUCCEED}All selected configurations are downloaded.")
