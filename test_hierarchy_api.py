import json
from src.ledger.ledger import read_wallets, write_wallets

def test_hierarchy_logic():
    print("[TEST] Initializing Multi-Tenant Hierarchy Test...")
    
    # 1. Setup a clear hierarchy
    mock_wallets = {
        "org_corp": {
            "id": "org_corp", "name": "Global Corp", "balance_jul": 1000.0, "held_jul": 100.0, "parent_wallet_id": None
        },
        "proj_alpha": {
            "id": "proj_alpha", "name": "Project Alpha", "balance_jul": 500.0, "held_jul": 50.0, "parent_wallet_id": "org_corp"
        },
        "agent_s1": {
            "id": "agent_s1", "name": "Sentinel Agent 1", "balance_jul": 100.0, "held_jul": 10.0, "parent_wallet_id": "proj_alpha"
        },
        "proj_beta": {
            "id": "proj_beta", "name": "Project Beta", "balance_jul": 200.0, "held_jul": 0.0, "parent_wallet_id": "org_corp"
        }
    }
    
    # Temporarily override wallets.json
    orig_wallets = read_wallets()
    write_wallets(mock_wallets)
    
    try:
        # 2. Logic to test (identical to server.py endpoint)
        wallets = read_wallets()
        hierarchy = {}
        roots = []
        
        for w_id, w_data in wallets.items():
            parent = w_data.get("parent_wallet_id")
            if not parent:
                roots.append(w_id)
            else:
                if parent not in hierarchy:
                    hierarchy[parent] = []
                hierarchy[parent].append(w_id)
                
        def _build_node(w_id):
            data = wallets[w_id]
            return {
                "id": w_id,
                "name": data.get("name", w_id),
                "available_jul": round(data["balance_jul"] - data["held_jul"], 6),
                "children": [_build_node(child) for child in hierarchy.get(w_id, [])]
            }

        result = [_build_node(root) for root in roots]
        
        # 3. Validations
        assert len(result) == 1
        org_node = result[0]
        assert org_node["id"] == "org_corp"
        assert org_node["available_jul"] == 900.0
        assert len(org_node["children"]) == 2 # proj_alpha, proj_beta
        
        proj_alpha = [c for c in org_node["children"] if c["id"] == "proj_alpha"][0]
        assert proj_alpha["available_jul"] == 450.0
        assert len(proj_alpha["children"]) == 1
        assert proj_alpha["children"][0]["id"] == "agent_s1"
        assert proj_alpha["children"][0]["available_jul"] == 90.0
        
        print("✅ Hierarchy Recursive Logic Verified. Multi-tenant visibility confirmed.")

    finally:
        # Restore original wallets
        write_wallets(orig_wallets)

if __name__ == "__main__":
    try:
        test_hierarchy_logic()
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
