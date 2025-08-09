"""
Check available SDXL models and their details
"""

import requests
import json

def check_models():
    base_url = "http://127.0.0.1:9090"
    session = requests.Session()
    
    print("=" * 70)
    print("CHECKING AVAILABLE MODELS")
    print("=" * 70)
    
    response = session.get(f"{base_url}/api/v2/models/")
    if response.status_code == 200:
        models_data = response.json()
        
        sdxl_models = []
        other_models = []
        
        for model in models_data['models']:
            if model['type'] == 'main':
                if model['base'] == 'sdxl':
                    sdxl_models.append(model)
                else:
                    other_models.append(model)
        
        print(f"\nFound {len(sdxl_models)} SDXL models:")
        print("-" * 70)
        for i, model in enumerate(sdxl_models, 1):
            print(f"\n{i}. {model['name']}")
            print(f"   Key: {model['key']}")
            print(f"   Base: {model['base']}")
            print(f"   Type: {model['type']}")
            print(f"   Path: {model.get('path', 'N/A')}")
            print(f"   Hash: {model.get('hash', 'N/A')[:16]}...")
            if 'description' in model:
                print(f"   Description: {model['description']}")
        
        if other_models:
            print(f"\n\nFound {len(other_models)} other models:")
            print("-" * 70)
            for model in other_models[:5]:  # Show first 5
                print(f"- {model['name']} (base: {model['base']})")
        
        return sdxl_models
    else:
        print(f"Failed to get models: {response.status_code}")
        return []

if __name__ == "__main__":
    models = check_models()
    
    if len(models) > 1:
        print("\n" + "=" * 70)
        print("MULTIPLE SDXL MODELS AVAILABLE")
        print("You can modify the script to use a different model by index")
        print("=" * 70)