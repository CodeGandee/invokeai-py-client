# Architecture

InvokeAI Python Client architecture and design patterns.

## Overview

The client follows a layered architecture with clear separation of concerns:

```mermaid
flowchart TD
    UA[User Application]
    
    subgraph Client ["InvokeAI Python Client"]
        subgraph Components ["Repository & Field System Layer"]
            WR[Workflow Repository]
            BR[Board Repository]
            FS[Field System]
        end
        
        HL[HTTP/WebSocket Layer]
    end
    
    API[InvokeAI Server API]
    
    UA --> WR
    UA --> BR
    UA --> FS
    
    WR --> HL
    BR --> HL
    FS --> HL
    
    HL --> API
    
    style UA fill:#e1f5fe
    style Client fill:#f3e5f5
    style Components fill:#fff3e0
    style HL fill:#e8f5e8
    style API fill:#fce4ec
```

## Repository Pattern

The client uses the Repository pattern to manage resources:

- **WorkflowRepository**: Manages workflow definitions and handles
- **BoardRepository**: Manages boards and image operations
- **Client**: Orchestrates repositories and manages connections

## Field Type System

Strongly-typed field system with Pydantic validation:

- **IvkField[T]**: Generic base class for all fields
- **Primitive Fields**: String, Integer, Float, Boolean
- **Resource Fields**: Image, Board, Latents, Tensor
- **Model Fields**: ModelIdentifier, UNet, CLIP, etc.

## Workflow Execution

1. **Definition Loading**: Parse workflow JSON
2. **Input Mapping**: Create IvkWorkflowInput instances
3. **Model Sync**: Match models to server availability
4. **Submission**: Send to execution queue
5. **Monitoring**: Poll or stream events
6. **Output Mapping**: Extract results

## Data Flow

```mermaid
flowchart LR
    subgraph Input ["Input Flow"]
        UI[User Input] --> FV[Field Validation]
        FV --> AF[API Format]
        AF --> SRV1[Server]
    end
    
    subgraph Output ["Output Flow"]  
        SRV2[Server Result] --> OM[Output Mapping]
        OM --> FO[Field Objects]
        FO --> USR[User]
    end
    
    style Input fill:#e8f5e8
    style Output fill:#fff3e0
    style UI fill:#e1f5fe
    style USR fill:#e1f5fe
    style SRV1 fill:#fce4ec
    style SRV2 fill:#fce4ec
```

## Error Handling

Hierarchical exception system:

```mermaid
flowchart TD
    IE[InvokeAIError<br/><em>base exception</em>]
    
    IE --> CE[ConnectionError]
    IE --> WE[WorkflowError]
    IE --> BE[BoardError]
    IE --> VE[ValidationError]
    IE --> AE[APIError]
    
    style IE fill:#ffebee,stroke:#c62828,stroke-width:2px
    style CE fill:#e3f2fd,stroke:#1976d2
    style WE fill:#e8f5e8,stroke:#388e3c
    style BE fill:#fff3e0,stroke:#f57c00
    style VE fill:#f3e5f5,stroke:#7b1fa2
    style AE fill:#fce4ec,stroke:#c2185b
```

## Best Practices

1. **Immutable Workflows**: Never modify workflow JSON structure
2. **Type Safety**: Use field types for validation
3. **Resource Management**: Clean up uploaded assets
4. **Connection Pooling**: Reuse client instances
5. **Error Recovery**: Implement retry logic

See [Contributing](contributing.md) for development guidelines.
