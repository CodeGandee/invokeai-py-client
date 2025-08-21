#!/usr/bin/env python3
"""
InvokeAI DNN Models API Demo

This demo shows how to get and interpret DNN model information from InvokeAI.
Demonstrates comprehensive model data access, filtering, and interpretation.

API Endpoints demonstrated:
- GET /api/v2/models/ - List all models with filtering options
- GET /api/v2/models/i/{key} - Get specific model details
- GET /api/v1/app/version - Test API connection

Model Types covered:
- main: Primary diffusion models (FLUX, SDXL)
- controlnet: ControlNet models for guided generation
- vae: Variational Auto-Encoders
- clip_vision: CLIP vision encoders
- clip_embed: CLIP text encoders
- ip_adapter: IP-Adapter models
- t5_encoder: T5 text encoders
"""

import requests
import json
from typing import List, Dict, Any, Optional, Literal, Union
from dataclasses import dataclass
from enum import Enum


# InvokeAI API base URL
BASE_URL = "http://localhost:9090"

# Type definitions for better code clarity
ModelType = Literal["main", "controlnet", "vae", "clip_vision", "clip_embed", "ip_adapter", "t5_encoder"]
BaseModelType = Literal["flux", "sdxl", "any"]
ModelFormat = Literal["checkpoint", "diffusers", "invokeai", "bnb_quantized_int8b"]


class ModelTypeEnum(Enum):
    """Enumeration of available model types in InvokeAI."""
    MAIN = "main"
    CONTROLNET = "controlnet"
    VAE = "vae"
    CLIP_VISION = "clip_vision"
    CLIP_EMBED = "clip_embed"
    IP_ADAPTER = "ip_adapter"
    T5_ENCODER = "t5_encoder"


@dataclass
class ModelInfo:
    """
    Strongly-typed data class representing an InvokeAI DNN model.
    
    This class provides a clean, typed interface to InvokeAI model data,
    making it easier to work with model information in a type-safe manner.
    """
    key: str
    name: str
    type: ModelType
    base: BaseModelType
    format: ModelFormat
    hash: str
    description: str
    path: str
    source: str
    file_size: Optional[int] = None
    variant: Optional[str] = None
    prediction_type: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelInfo':
        """Create ModelInfo instance from API response dictionary."""
        return cls(
            key=data.get("key", ""),
            name=data.get("name", ""),
            type=data.get("type", "main"),
            base=data.get("base", "any"),
            format=data.get("format", "checkpoint"),
            hash=data.get("hash", ""),
            description=data.get("description", ""),
            path=data.get("path", ""),
            source=data.get("source", ""),
            file_size=data.get("file_size"),
            variant=data.get("variant"),
            prediction_type=data.get("prediction_type")
        )
    
    def format_file_size(self) -> str:
        """Format file size in human-readable format."""
        if self.file_size is None:
            return "Unknown"
        
        size = float(self.file_size)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    def get_model_category(self) -> str:
        """Get human-readable category description for the model."""
        categories = {
            "main": "Primary Diffusion Model",
            "controlnet": "ControlNet (Guided Generation)",
            "vae": "Variational Auto-Encoder",
            "clip_vision": "CLIP Vision Encoder",
            "clip_embed": "CLIP Text Encoder", 
            "ip_adapter": "IP-Adapter (Image Prompting)",
            "t5_encoder": "T5 Text Encoder"
        }
        return categories.get(self.type, f"Unknown ({self.type})")
    
    def is_compatible_with_base(self, base_model: str) -> bool:
        """Check if this model is compatible with a specific base model."""
        return self.base == "any" or self.base == base_model
    
    def __str__(self) -> str:
        """String representation of the model."""
        return f"{self.name} ({self.type}, {self.base}, {self.format_file_size()})"


class InvokeAIModelsAPI:
    """
    Strongly-typed API client for InvokeAI model operations.
    
    Provides methods to fetch, filter, and interpret model information
    from the InvokeAI API with proper error handling and type safety.
    """
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def test_connection(self) -> bool:
        """Test if the InvokeAI API is accessible."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/app/version", timeout=10)
            if response.status_code == 200:
                version_info = response.json()
                print(f"API Connection successful - InvokeAI version: {version_info.get('version', 'unknown')}")
                return True
            else:
                print(f"API returned status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"API Connection failed: {e}")
            return False
    
    def get_all_models(self) -> List[ModelInfo]:
        """
        Fetch all models from InvokeAI.
        
        Returns:
            List of ModelInfo objects representing all available models
        """
        endpoint = f"{self.base_url}/api/v2/models/"
        
        try:
            response = self.session.get(endpoint, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            models_data = data.get("models", [])
            
            return [ModelInfo.from_dict(model_data) for model_data in models_data]
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching models: {e}")
            return []
    
    def get_model_by_key(self, model_key: str) -> Optional[ModelInfo]:
        """
        Fetch a specific model by its key.
        
        Args:
            model_key: The unique key identifier for the model
            
        Returns:
            ModelInfo object if found, None otherwise
        """
        endpoint = f"{self.base_url}/api/v2/models/i/{model_key}"
        
        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            
            model_data = response.json()
            return ModelInfo.from_dict(model_data)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching model {model_key}: {e}")
            return None
    
    def filter_models_by_type(self, models: List[ModelInfo], model_type: ModelType) -> List[ModelInfo]:
        """Filter models by their type."""
        return [model for model in models if model.type == model_type]
    
    def filter_models_by_base(self, models: List[ModelInfo], base_model: BaseModelType) -> List[ModelInfo]:
        """Filter models by their base model architecture."""
        return [model for model in models if model.base == base_model or model.base == "any"]
    
    def get_models_by_size_range(self, models: List[ModelInfo], 
                                min_size_gb: float = 0, max_size_gb: float = float('inf')) -> List[ModelInfo]:
        """Filter models by file size range (in GB)."""
        filtered = []
        for model in models:
            if model.file_size is not None:
                size_gb = model.file_size / (1024**3)
                if min_size_gb <= size_gb <= max_size_gb:
                    filtered.append(model)
        return filtered


def demonstrate_basic_model_access() -> None:
    """Demonstrate basic model access and interpretation."""
    print("\n" + "="*80)
    print("BASIC MODEL ACCESS DEMONSTRATION")
    print("="*80)
    
    # Create API client
    api = InvokeAIModelsAPI()
    
    # Test connection
    if not api.test_connection():
        print("Cannot proceed - API connection failed")
        return
    
    # Fetch all models
    print("\nFetching all models...")
    models = api.get_all_models()
    
    if not models:
        print("No models found or error occurred")
        return
    
    print(f"Found {len(models)} models total")
    
    # Display model type distribution
    type_counts: Dict[str, int] = {}
    for model in models:
        type_counts[model.type] = type_counts.get(model.type, 0) + 1
    
    print("\nModel distribution by type:")
    for model_type, count in sorted(type_counts.items()):
        print(f"  {model_type}: {count} models")


def demonstrate_model_filtering() -> None:
    """Demonstrate advanced model filtering and interpretation."""
    print("\n" + "="*80)
    print("MODEL FILTERING DEMONSTRATION")
    print("="*80)
    
    api = InvokeAIModelsAPI()
    models = api.get_all_models()
    
    if not models:
        return
    
    # Filter by type - show main models
    main_models = api.filter_models_by_type(models, "main")
    print(f"\nMain Models ({len(main_models)}):")
    for model in main_models:
        print(f"  - {model.name}")
        print(f"    Base: {model.base}, Variant: {model.variant or 'N/A'}")
        print(f"    Size: {model.format_file_size()}, Format: {model.format}")
        print()
    
    # Filter by base model - show FLUX models
    flux_models = api.filter_models_by_base(models, "flux")
    print(f"FLUX Compatible Models ({len(flux_models)}):")
    for model in flux_models:
        print(f"  - {model.name} ({model.get_model_category()})")
        print(f"    Size: {model.format_file_size()}")
        print()
    
    # Filter by size - show large models (>10GB)
    large_models = api.get_models_by_size_range(models, min_size_gb=10.0)
    print(f"Large Models (>10GB) ({len(large_models)}):")
    for model in large_models:
        print(f"  - {model.name}: {model.format_file_size()}")


def demonstrate_model_details() -> None:
    """Demonstrate detailed model information access."""
    print("\n" + "="*80)
    print("DETAILED MODEL INFORMATION DEMONSTRATION")
    print("="*80)
    
    api = InvokeAIModelsAPI()
    models = api.get_all_models()
    
    if not models:
        return
    
    # Show detailed info for first few models of each type
    types_shown: set[str] = set()
    for model in models:
        if model.type not in types_shown and len(types_shown) < 3:
            types_shown.add(model.type)
            
            print(f"\nDetailed Info: {model.name}")
            print(f"  Type: {model.get_model_category()}")
            print(f"  Key: {model.key}")
            print(f"  Base Model: {model.base}")
            print(f"  Format: {model.format}")
            print(f"  File Size: {model.format_file_size()}")
            print(f"  Hash: {model.hash[:32]}..." if len(model.hash) > 32 else f"  Hash: {model.hash}")
            print(f"  Description: {model.description[:100]}..." if len(model.description) > 100 else f"  Description: {model.description}")
            print(f"  Source: {model.source[:80]}..." if len(model.source) > 80 else f"  Source: {model.source}")
            
            if model.type == "main":
                print(f"  Variant: {model.variant or 'N/A'}")
                print(f"  Prediction Type: {model.prediction_type or 'N/A'}")


def demonstrate_model_compatibility() -> None:
    """Demonstrate model compatibility checking."""
    print("\n" + "="*80)
    print("MODEL COMPATIBILITY DEMONSTRATION")
    print("="*80)
    
    api = InvokeAIModelsAPI()
    models = api.get_all_models()
    
    if not models:
        return
    
    # Show which models work with SDXL
    print("\nModels compatible with SDXL:")
    sdxl_compatible = [m for m in models if m.is_compatible_with_base("sdxl")]
    for model_type in ["main", "controlnet", "vae", "ip_adapter"]:
        type_models = [m for m in sdxl_compatible if m.type == model_type]
        if type_models:
            print(f"\n  {model_type.upper()} ({len(type_models)}):")
            for model in type_models:
                print(f"    - {model.name}")
    
    # Show which models work with FLUX
    print("\n\nModels compatible with FLUX:")
    flux_compatible = [m for m in models if m.is_compatible_with_base("flux")]
    for model_type in ["main", "controlnet", "vae"]:
        type_models = [m for m in flux_compatible if m.type == model_type]
        if type_models:
            print(f"\n  {model_type.upper()} ({len(type_models)}):")
            for model in type_models:
                print(f"    - {model.name}")


def demonstrate_model_analysis() -> None:
    """Demonstrate model analysis and statistics."""
    print("\n" + "="*80)
    print("MODEL ANALYSIS DEMONSTRATION")
    print("="*80)
    
    api = InvokeAIModelsAPI()
    models = api.get_all_models()
    
    if not models:
        return
    
    # Calculate storage statistics
    total_size = sum(m.file_size or 0 for m in models)
    models_with_size = [m for m in models if m.file_size is not None]
    
    print(f"\nStorage Analysis:")
    print(f"  Total models: {len(models)}")
    print(f"  Models with size info: {len(models_with_size)}")
    print(f"  Total storage used: {total_size / (1024**3):.2f} GB")
    
    if models_with_size:
        avg_size = total_size / len(models_with_size)
        print(f"  Average model size: {avg_size / (1024**3):.2f} GB")
        
        # Find largest and smallest models
        largest = max(models_with_size, key=lambda m: m.file_size or 0)
        smallest = min(models_with_size, key=lambda m: m.file_size or float('inf'))
        
        print(f"  Largest model: {largest.name} ({largest.format_file_size()})")
        print(f"  Smallest model: {smallest.name} ({smallest.format_file_size()})")
    
    # Format distribution
    format_counts: Dict[str, int] = {}
    for model in models:
        format_counts[model.format] = format_counts.get(model.format, 0) + 1
    
    print(f"\nFormat Distribution:")
    for format_type, count in sorted(format_counts.items()):
        print(f"  {format_type}: {count} models")


def main() -> None:
    """
    Main demonstration function.
    
    This function runs through all the model API demonstrations,
    showing different ways to access and interpret DNN model information.
    """
    print("InvokeAI DNN Models API Demo")
    print("This demo shows how to get and interpret DNN model information from InvokeAI")
    
    try:
        # Run all demonstrations
        demonstrate_basic_model_access()
        demonstrate_model_filtering()
        demonstrate_model_details()
        demonstrate_model_compatibility()
        demonstrate_model_analysis()
        
        print("\n" + "="*80)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nKey Takeaways:")
        print("- Use ModelInfo class for strongly-typed model data")
        print("- Filter models by type, base architecture, or file size")
        print("- Check model compatibility with specific base models")
        print("- Access detailed metadata including hash, source, and descriptions")
        print("- Analyze storage usage and model distributions")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()