import os, json, datetime

VAULT = r"C:\Users\Bbeie\isopod-research"

def main():
    root = os.path.join(VAULT, "Isopoda")
    map_path = os.path.join(VAULT, "data", "isopoda_suborders.json")
    
    with open(map_path, "r", encoding="utf-8") as f:
        suborders_map = json.load(f)["families"]
        
    suborder_info = {}
    for fam, info in suborders_map.items():
        sub = info["suborder"]
        if sub not in suborder_info:
            suborder_info[sub] = {"realm": info["realm"], "families": {}}
        suborder_info[sub]["families"][fam] = {"genera": set(), "species": 0}
        
    # count species
    for sub in os.listdir(root):
        sub_path = os.path.join(root, sub)
        if not os.path.isdir(sub_path): continue
        if sub not in suborder_info:
            continue
            
        for fam in os.listdir(sub_path):
            fam_path = os.path.join(sub_path, fam)
            if not os.path.isdir(fam_path): continue
            
            for gen in os.listdir(fam_path):
                gen_path = os.path.join(fam_path, gen)
                if not os.path.isdir(gen_path): continue
                
                if fam in suborder_info[sub]["families"]:
                    suborder_info[sub]["families"][fam]["genera"].add(gen)
                
                for sp in os.listdir(gen_path):
                    if sp.endswith(".md") and not sp.startswith("_"):
                        if fam in suborder_info[sub]["families"]:
                            suborder_info[sub]["families"][fam]["species"] += 1
                            
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    total_suborders = len(suborder_info)
    total_families = 0
    total_genera = 0
    total_species = 0
    
    suborder_rows = []
    
    for sub, sinfo in sorted(suborder_info.items()):
        sub_families = sinfo["families"]
        s_fam_count = len(sub_families)
        s_gen_count = sum(len(f["genera"]) for f in sub_families.values())
        s_sp_count = sum(f["species"] for f in sub_families.values())
        
        total_families += s_fam_count
        total_genera += s_gen_count
        total_species += s_sp_count
        
        suborder_rows.append(f"| [[_{sub} Index\\|{sub}]] | {sinfo['realm']} | {s_fam_count} | {s_gen_count} | {s_sp_count} |")
        
        # Write suborder index
        sub_content = f"""---
type: index
group: {sub}
family_count: {s_fam_count}
genus_count: {s_gen_count}
species_count: {s_sp_count}
realm: {sinfo['realm']}
source: GBIF Backbone Taxonomy (api.gbif.org)
generated: {today}
tags: [isopod, {sub.lower()}, master-index]
---

# {sub} (Suborder)

This vault section covers **{s_fam_count} families, {s_gen_count} genera, and {s_sp_count} accepted species**.
Realm: {sinfo['realm']}

## Families

| Family | Genera | Species |
|---|---:|---:|
"""
        for fam in sorted(sub_families.keys()):
            f_gen = len(sub_families[fam]["genera"])
            f_sp = sub_families[fam]["species"]
            sub_content += f"| [[_{fam} Index\\|{fam}]] | {f_gen} | {f_sp} |\n"
            
        sub_content += f"| **TOTAL** | **{s_gen_count}** | **{s_sp_count}** |\n"
        
        sub_path = os.path.join(root, sub)
        os.makedirs(sub_path, exist_ok=True)
        with open(os.path.join(sub_path, f"_{sub} Index.md"), "w", encoding="utf-8") as out:
            out.write(sub_content)

    # Write master index
    master_content = f"""---
type: index
group: Isopoda
suborder_count: {total_suborders}
family_count: {total_families}
genus_count: {total_genera}
species_count: {total_species}
source: GBIF Backbone Taxonomy (api.gbif.org)
generated: {today}
tags: [isopod, isopoda, master-index]
---

# Isopoda (Order)

The order Isopoda. This vault section covers **{total_suborders} suborders, {total_families} families, {total_genera} genera, and {total_species} accepted species**.

## Suborders

| Suborder | Realm | Families | Genera | Species |
|---|---|---:|---:|---:|
"""
    master_content += "\n".join(suborder_rows)
    master_content += f"\n| **TOTAL** | | **{total_families}** | **{total_genera}** | **{total_species}** |\n"
    
    with open(os.path.join(root, "_Isopoda Index.md"), "w", encoding="utf-8") as out:
        out.write(master_content)
        
    print(f"Generated indexes for {total_suborders} suborders, {total_families} families, {total_species} species.")

if __name__ == "__main__":
    main()
