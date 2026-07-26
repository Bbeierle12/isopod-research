import os, json, re, time, urllib.request

VAULT = r"C:\Users\Bbeie\isopod-research"

def safe(n):
    return re.sub(r'[\\/:*?"<>|]', "-", n).strip()

def get_json(url):
    for _ in range(5):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(2)
    return None

def fetch_children(key, rank):
    limit = 200
    offset = 0
    results = []
    while True:
        url = f"https://api.gbif.org/v1/species/{key}/children?limit={limit}&offset={offset}"
        data = get_json(url)
        if not data or not data.get("results"):
            break
        for row in data["results"]:
            if row.get("rank") == rank:
                results.append(row)
        if data.get("endOfRecords"):
            break
        offset += limit
    return results

def main():
    map_path = os.path.join(VAULT, "data", "isopoda_suborders.json")
    with open(map_path, "r", encoding="utf-8") as f:
        suborder_map = json.load(f)["families"]
    
    isopoda_families = fetch_children(643, "FAMILY")
    
    # FOR DRY RUN
    # isopoda_families = [f for f in isopoda_families if f["scientificName"] == "Limnoriidae"]

    for i, fam_data in enumerate(isopoda_families, 1):
        fam_name = fam_data["scientificName"]
        fam_key = fam_data["key"]
        
        info = suborder_map.get(fam_name)
        if not info: continue
        suborder = info["suborder"]
        if suborder == "Oniscidea": continue
        realm = info["realm"]
        
        genera = fetch_children(fam_key, "GENUS")
        total_species = 0
        for gen_data in genera:
            gen_name = gen_data["canonicalName"] or gen_data["scientificName"]
            gen_key = gen_data["key"]
            species = fetch_children(gen_key, "SPECIES")
            
            for sp_data in species:
                if sp_data.get("taxonomicStatus") != "ACCEPTED": continue
                full_sp_name = sp_data.get("canonicalName")
                if not full_sp_name:
                    full_sp_name = sp_data.get("species")
                if not full_sp_name: continue
                
                auth = sp_data.get("authorship", "")
                gbif_id = sp_data.get("key")
                
                path = os.path.join(VAULT, "Isopoda", safe(suborder), safe(fam_name), safe(gen_name), f"{safe(full_sp_name)}.md")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                
                if not os.path.exists(path):
                    content = f"""---
type: species
scientificName: {full_sp_name}
authorship: "{auth.replace('"', '\\"')}"
genus: {gen_name}
family: {fam_name}
suborder: {suborder}
realm: {realm}
gbif_id: {gbif_id}
gbif_url: https://www.gbif.org/species/{gbif_id}
common_name:
distribution:
habitat:
ecomorph:
conglobation_type:
terrestrialization:
habitat_stratum:
trophic_guild:
reproduction_mode:
ecology_evidence:
sources:
status: stub
tags: [isopod, isopoda, {suborder.lower()}, {fam_name.lower()}]
---

# {full_sp_name} {auth}

**Order** Isopoda › **Suborder** {suborder} › **Family** [[_{fam_name} Index|{fam_name}]] › **Genus** [[_{gen_name}|{gen_name}]]

## Overview


## Distribution & habitat


## References
- GBIF: https://www.gbif.org/species/{gbif_id}
"""
                    with open(path, "w", encoding="utf-8") as out:
                        out.write(content)
                total_species += 1
        
        log_line = f"[{i}/{len(isopoda_families)}] {fam_name} genera={len(genera)} species={total_species}"
        print(log_line)
        with open(os.path.join(VAULT, "scratchpad.log"), "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
            
if __name__ == "__main__":
    main()
