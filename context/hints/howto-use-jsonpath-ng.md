# How to Use jsonpath-ng - A Comprehensive Guide

`jsonpath-ng` is a robust Python library for querying and manipulating JSON data using JSONPath expressions. It's a final implementation that aims to be standard compliant, including arithmetic and binary comparison operators.

## Installation

```bash
pip install jsonpath-ng
```

## Basic Usage

### 1. Simple Path Extraction

```python
from jsonpath_ng import parse

# Parse a JSONPath expression
jsonpath_expr = parse('foo[*].baz')

# Sample data
data = {'foo': [{'baz': 1}, {'baz': 2}]}

# Extract values
values = [match.value for match in jsonpath_expr.find(data)]
# Result: [1, 2]

# Get full paths
paths = [str(match.full_path) for match in jsonpath_expr.find(data)]
# Result: ['foo.[0].baz', 'foo.[1].baz']
```

### 2. Updating Values

```python
# Update all matching values
result = jsonpath_expr.update(data, 3)
# Result: {'foo': [{'baz': 3}, {'baz': 3}]}

# Update specific match
matches = jsonpath_expr.find(data)
matches[0].full_path.update(data, 5)
# Updates only the first match
```

### 3. Filtering and Removing Values

```python
# Remove all values matching a path
result = jsonpath_expr.filter(lambda d: True, data)
# Result: {'foo': [{}, {}]}

# Remove values containing specific data
result = jsonpath_expr.filter(lambda d: d == 2, data)
# Result: {'foo': [{'baz': 1}, {}]}
```

## JSONPath Syntax Reference

### Atomic Expressions

| Syntax | Meaning |
|--------|---------|
| `$` | The root object |
| `this` | The "current" object |
| `foo` | Named operators to extend JSONPath |
| `field` | Specified field(s) |
| `[field]` | Same as field |
| `[idx]` | Array access |

### JSONPath Operators

| Syntax | Meaning |
|--------|---------|
| `jsonpath1.jsonpath2` | All nodes matched by jsonpath2 starting at any node matching jsonpath1 |
| `jsonpath[whatever]` | Same as jsonpath.whatever |
| `jsonpath1..jsonpath2` | All nodes matched by jsonpath2 that descend from any node matching jsonpath1 |
| `jsonpath1 where jsonpath2` | Any nodes matching jsonpath1 with a child matching jsonpath2 |
| `jsonpath1 wherenot jsonpath2` | Any nodes matching jsonpath1 with a child not matching jsonpath2 |
| `jsonpath1\|jsonpath2` | Union of jsonpath1 and jsonpath2 |

### Field Specifiers

| Syntax | Meaning |
|--------|---------|
| `fieldname` | The field fieldname |
| `"fieldname"` | Same as above, allows special characters |
| `'fieldname'` | Same as above |
| `*` | Any field |
| `field,field` | Either of the named fields |

### Array Specifiers

| Syntax | Meaning |
|--------|---------|
| `[n]` | Array index (may be comma-separated list) |
| `[start:end]` | Array slicing |
| `[*]` | Any array index |

## Advanced Features

### 1. Programmatic JSONPath Creation

```python
from jsonpath_ng.jsonpath import Fields, Slice, Index, Child

# Direct creation (more robust than parsing)
expr = Fields('foo').child(Slice('*')).child(Fields('baz'))
# Equivalent to parse('foo[*].baz')
```

### 2. Named Operators

```python
# Using the 'parent' operator
expr = parse('a.*.b.`parent`.c')
data = {'a': {'x': {'b': 1, 'c': 'number one'}, 'y': {'b': 2, 'c': 'number two'}}}
values = [match.value for match in expr.find(data)]
# Result: ['number one', 'number two']
```

### 3. Automatic IDs

```python
import jsonpath_ng.jsonpath as jsonpath

# Enable automatic ID generation
jsonpath.auto_id_field = 'id'

# Missing IDs will be auto-generated based on JSONPath
expr = parse('foo[*].id')
data = {'foo': [{'id': 'bizzle'}, {'baz': 3}]}
values = [match.value for match in expr.find(data)]
# Result: ['foo.bizzle', 'foo.[1]']
```

## Extensions (jsonpath_ng.ext)

For advanced features, import from `jsonpath_ng.ext`:

```python
from jsonpath_ng.ext import parse
```

### 1. Length Operator

```python
# Get length of arrays/objects
expr = parse('$.objects.`len`')
```

### 2. String Operations

```python
# Substitute with regex
expr = parse('$.field.`sub(/foo\\+(.*)/,\\1)`')

# Split strings
expr = parse('$.field.`split(+, 2, -1)`')
expr = parse('$.field.`split(",", *, -1)`')
```

### 3. Sorting

```python
# Sort arrays
expr = parse('$.objects.`sorted`')
expr = parse('$.objects[`some_field`]')
```

### 4. Filtering with Conditions

```python
# Comparison operators
expr = parse('$.objects[?(@.some_field > 5)]')
expr = parse('$.objects[?some_field = "foobar")]')
expr = parse('$.objects[?some_field =~ "foobar")]')  # Regex match

# Combine conditions
expr = parse('$.objects[?some_field > 5 & other < 2)]')
```

### 5. Arithmetic Operations

```python
# Basic arithmetic
expr = parse('$.foo + "" + $.bar')
expr = parse('$.foo * 12')
expr = parse('$.objects[*].cow + $.objects[*].cat')
```

## Real-World Examples

### 1. Workflow JSON Manipulation

```python
from jsonpath_ng import parse

# Find all input fields in a workflow
workflow_data = {
    "nodes": [
        {
            "id": "node1",
            "data": {
                "inputs": {
                    "model": {"name": "model", "value": {"key": "old-key"}},
                    "prompt": {"name": "prompt", "value": "old prompt"}
                }
            }
        }
    ]
}

# Find model input for specific node
expr = parse("$.nodes[?(@.id='node1')].data.inputs.model.value")
matches = expr.find(workflow_data)

# Update the model
new_model = {"key": "new-key", "name": "new-model", "base": "sdxl"}
for match in matches:
    match.full_path.update(workflow_data, new_model)
```

### 2. Extract Data from Nested Structures

```python
# Extract all movie titles from nested data
movies_data = {
    "movies": [
        {"title": "Movie 1", "year": 1985, "cast": ["Actor A"]},
        {"title": "Movie 2", "year": 1995, "cast": ["Actor B", "Actor C"]}
    ]
}

# Get all titles
titles_expr = parse("$.movies[*].title")
titles = [match.value for match in titles_expr.find(movies_data)]

# Get movies before 1990
old_movies_expr = parse("$.movies[?(@.year < 1990)]")
old_movies = [match.value for match in old_movies_expr.find(movies_data)]
```

### 3. Configuration Management

```python
# Update configuration values
config = {
    "database": {
        "connections": [
            {"name": "primary", "host": "localhost", "port": 5432},
            {"name": "secondary", "host": "backup.local", "port": 5432}
        ]
    }
}

# Update primary database port
expr = parse("$.database.connections[?(@.name='primary')].port")
expr.update(config, 5433)
```

## Best Practices

### 1. Store JSONPath Expressions

When working with workflows or repeated operations, store the JSONPath expression rather than the raw path string:

```python
class WorkflowInput:
    def __init__(self, name, jsonpath_expr, default_value=None):
        self.name = name
        self.jsonpath_expr = jsonpath_expr  # Store parsed expression
        self.default_value = default_value
    
    def update_workflow(self, workflow_data, new_value):
        matches = self.jsonpath_expr.find(workflow_data)
        for match in matches:
            match.full_path.update(workflow_data, new_value)
```

### 2. Error Handling

```python
def safe_jsonpath_update(data, path_string, new_value):
    try:
        expr = parse(path_string)
        matches = expr.find(data)
        if matches:
            for match in matches:
                match.full_path.update(data, new_value)
            return True
        else:
            print(f"No matches found for path: {path_string}")
            return False
    except Exception as e:
        print(f"Error parsing JSONPath '{path_string}': {e}")
        return False
```

### 3. Performance Considerations

- Parse expressions once and reuse them
- Use specific paths rather than broad searches when possible
- Consider using the programmatic API for complex expressions

## Common Pitfalls

1. **PLY and Docstrings**: The library doesn't work with `PYTHONOPTIMIZE=2` or `python -OO` due to docstring removal
2. **Extension Import**: Remember to import from `jsonpath_ng.ext` for advanced features
3. **Filter Syntax**: Use `@` to reference the current object in filters: `[?(@.field > value)]`
4. **String vs JSONPath**: In arithmetic operations, fully define JSONPath expressions to avoid ambiguity

## References

- [Official PyPI Documentation](https://pypi.org/project/jsonpath-ng/)
- [GitHub Repository](https://github.com/h2non/jsonpath-ng)
- [JSONPath Specification](http://goessner.net/articles/JsonPath/)
- [Examples and Tutorials](https://scrapfly.io/blog/posts/parse-json-jsonpath-python)
