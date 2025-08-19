#!/usr/bin/env python3
"""
Test script for the DNN Model Repository subsystem.

This script validates the dnn-model-repo implementation by:
1. Listing all available models from InvokeAI
2. Demonstrating user-side filtering capabilities
3. Testing specific model lookup by key
4. Showing model compatibility checking
"""

import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client.client import InvokeAIClient
from invokeai_py_client.dnn_model import (
    DnnModelType,
    BaseDnnModelType,
    DnnModelFormat,
    DnnModel,
    DnnModelRepository,
)


def test_dnn_model_repository():
    """Test the DNN Model Repository functionality."""
    print("=" * 80)
    print("DNN Model Repository Test Script")
    print("=" * 80)
    
    # Create client
    client = InvokeAIClient.from_url("http://localhost:9090")
    
    # Get DNN model repository
    dnn_model_repo = client.dnn_model_repo
    print(f"\nDNN Model Repository: {dnn_model_repo}")
    
    # Test 1: List all models (API call)
    print("\n--- Test 1: List all models ---")
    models = dnn_model_repo.list_models()
    print(f"Total models found: {len(models)}")
    
    if not models:
        print("No models found. Make sure InvokeAI is running at http://localhost:9090")
        return
    
    # Test 2: User-side filtering by type
    print("\n--- Test 2: User-side filtering by type ---")
    
    # Count models by type
    type_counts = {}
    for model in models:
        model_type = model.type
        if model_type not in type_counts:
            type_counts[model_type] = 0
        type_counts[model_type] += 1
    
    print("Model distribution by type:")
    for model_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {model_type.value}: {count}")
    
    # Filter specific types
    main_models = [m for m in models if m.type == DnnModelType.Main]
    controlnets = [m for m in models if m.type == DnnModelType.ControlNet]
    vaes = [m for m in models if m.type == DnnModelType.VAE]
    loras = [m for m in models if m.type == DnnModelType.LoRA]
    
    print(f"\nFiltered counts:")
    print(f"  - Main models: {len(main_models)}")
    print(f"  - ControlNets: {len(controlnets)}")
    print(f"  - VAEs: {len(vaes)}")
    print(f"  - LoRAs: {len(loras)}")
    
    # Test 3: Architecture compatibility
    print("\n--- Test 3: Architecture compatibility ---")
    
    # Check compatibility with different base models
    base_compatibility = {}
    base_types = [BaseDnnModelType.Flux, BaseDnnModelType.StableDiffusionXL, BaseDnnModelType.StableDiffusion1, BaseDnnModelType.StableDiffusion2]
    
    for base_type in base_types:
        compatible = [m for m in models if m.is_compatible_with_base(base_type)]
        if compatible:
            base_compatibility[base_type] = len(compatible)
    
    print("Model compatibility by base architecture:")
    for base_type, count in base_compatibility.items():
        print(f"  - {base_type.value}: {count} models")
    
    # Test 4: Specific model lookup (API call)
    print("\n--- Test 4: Specific model lookup ---")
    
    # Pick the first main model for testing
    if main_models:
        test_model = main_models[0]
        print(f"\nLooking up model by key: {test_model.key}")
        
        # Fetch model by key (API call)
        fetched_model = dnn_model_repo.get_model_by_key(test_model.key)
        
        if fetched_model:
            print(f"Successfully fetched: {fetched_model.name}")
            print(f"  - Type: {fetched_model.type.value}")
            print(f"  - Base: {fetched_model.base.value}")
            print(f"  - Format: {fetched_model.format.value if fetched_model.format else 'N/A'}")
            print(f"  - Category: {fetched_model.get_category()}")
            if fetched_model.file_size:
                print(f"  - Size: {fetched_model.format_file_size()}")
        else:
            print(f"Failed to fetch model by key: {test_model.key}")
    
    # Test 5: Non-existent model lookup
    print("\n--- Test 5: Non-existent model lookup ---")
    missing = dnn_model_repo.get_model_by_key("nonexistent-key-12345")
    print(f"Lookup non-existent key result: {missing}")  # Should be None
    
    # Test 6: User-side name search
    print("\n--- Test 6: User-side name search ---")
    
    # Search for models by name patterns
    search_terms = ["flux", "sdxl", "controlnet", "vae"]
    
    for term in search_terms:
        matching = [m for m in models if term.lower() in m.name.lower()]
        if matching:
            print(f"Models containing '{term}': {len(matching)}")
            # Show first match
            if matching:
                first = matching[0]
                print(f"  Example: {first.name} ({first.type.value})")
    
    # Test 7: Workflow component discovery
    print("\n--- Test 7: Workflow component discovery ---")
    
    # Find all components needed for a FLUX workflow
    flux_workflow_types = {
        DnnModelType.Main: "Main Model",
        DnnModelType.VAE: "VAE",
        DnnModelType.CLIPEmbed: "CLIP Embed",
        DnnModelType.T5Encoder: "T5 Encoder",
    }
    
    print("Checking FLUX workflow viability:")
    flux_viable = True
    for model_type, description in flux_workflow_types.items():
        compatible = [m for m in models 
                     if m.type == model_type and m.is_compatible_with_base(BaseDnnModelType.Flux)]
        print(f"  - {description}: {len(compatible)} available")
        if not compatible:
            flux_viable = False
    
    print(f"\nFLUX workflow viable: {flux_viable}")
    
    # Test 8: Storage analysis
    print("\n--- Test 8: Storage analysis ---")
    
    models_with_size = [m for m in models if m.file_size is not None]
    if models_with_size:
        total_size = sum(m.file_size for m in models_with_size)
        avg_size = total_size / len(models_with_size)
        
        print(f"Storage statistics:")
        print(f"  - Models with size info: {len(models_with_size)}/{len(models)}")
        print(f"  - Total storage: {total_size / (1024**3):.2f} GB")
        print(f"  - Average model size: {avg_size / (1024**3):.2f} GB")
        
        # Find largest models
        largest = sorted(models_with_size, key=lambda m: m.file_size, reverse=True)[:3]
        print(f"\nLargest models:")
        for model in largest:
            print(f"  - {model.name}: {model.format_file_size()}")
    
    print("\n" + "=" * 80)
    print("DNN Model Repository tests completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_dnn_model_repository()
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)