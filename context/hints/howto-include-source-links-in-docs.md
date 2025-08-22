# How to Include Source Code Links in Documentation

## The Problem

Documentation often needs to reference source code, but maintaining valid links is challenging because:
- File paths change during refactoring
- Line numbers shift as code evolves  
- Relative links break in different documentation contexts
- Dead links create poor developer experience

## Solution Approaches

### 1. External Repository Links (Recommended)

**Best for**: Production documentation, public projects, long-term maintenance

```markdown
<!-- ✅ Good: External GitHub link with line anchor -->
[`WorkflowHandle.submit()`](https://github.com/owner/repo/blob/main/src/workflow.py#L42){:target="_blank"}

<!-- ❌ Avoid: Relative links that break -->
[WorkflowHandle.submit()](../src/workflow.py#L42)
```

**Pros:**
- ✅ Always clickable and accessible
- ✅ Opens in new tab (preserves context)
- ✅ Works across different hosting environments
- ✅ No broken link warnings in build tools
- ✅ Exact line number navigation

**Cons:**
- ❌ Requires repository to be public
- ❌ Links may become stale if files are moved
- ❌ Manual maintenance for line numbers

### 2. Documentation Tool Plugins

**Best for**: Large codebases, automated workflows

#### MkDocs with mkdocs-macros-plugin
```yaml
# mkdocs.yml
plugins:
  - macros:
      variables:
        repo_url: "https://github.com/owner/repo"
        src_branch: "main"
```

```markdown
<!-- Usage in docs -->
[`MyClass`]({{ repo_url }}/blob/{{ src_branch }}/src/myclass.py#L15){:target="_blank"}
```

#### Sphinx with sphinx.ext.linkcode
```python
# conf.py
def linkcode_resolve(domain, info):
    if domain != 'py':
        return None
    
    modname = info['module']
    fullname = info['fullname']
    
    filename = modname.replace('.', '/') + '.py'
    return f"https://github.com/owner/repo/blob/main/src/{filename}"
```

### 3. Automated Link Generation

**Best for**: API documentation, generated docs

#### Using mkdocs-gen-files
```python
# scripts/generate_source_links.py
import mkdocs_gen_files
import ast
import os

def generate_api_links():
    """Generate API documentation with automatic source links"""
    
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                
                # Parse Python AST to find classes/functions
                with open(file_path, 'r') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        github_link = f"https://github.com/owner/repo/blob/main/{file_path}#L{node.lineno}"
                        
                        # Generate markdown with source link
                        doc_content = f"""
# {node.name}

Source: [`{node.name}`]({github_link}){{:target="_blank"}}
"""
                        
                        with mkdocs_gen_files.open(f"api/{node.name}.md", "w") as doc_file:
                            doc_file.write(doc_content)
```

## Implementation Strategies

### Strategy 1: Manual External Links

```markdown
<!-- Template for consistent formatting -->
## MyClass

Core implementation: [`MyClass`](https://github.com/owner/repo/blob/main/src/myclass.py#L42){:target="_blank"}

### Methods
- [`process()`](https://github.com/owner/repo/blob/main/src/myclass.py#L56){:target="_blank"} - Main processing method
- [`validate()`](https://github.com/owner/repo/blob/main/src/myclass.py#L78){:target="_blank"} - Input validation
```

### Strategy 2: Configuration-Driven Links

```yaml
# _config.yml or mkdocs.yml
repository:
  url: https://github.com/owner/repo
  branch: main
  source_path: src

markdown_extensions:
  - attr_list  # Enable {: } syntax for link attributes
```

```markdown
<!-- Use consistent helper pattern -->
{% assign repo = site.repository %}
[`MyClass`]({{ repo.url }}/blob/{{ repo.branch }}/{{ repo.source_path }}/myclass.py#L42){:target="_blank"}
```

### Strategy 3: Build-Time Link Validation

```python
# scripts/validate_links.py
import requests
import re
import os

def validate_github_links(docs_dir):
    """Validate that GitHub source links are accessible"""
    
    github_link_pattern = r'\[.*?\]\((https://github\.com/[^)]+)\)'
    broken_links = []
    
    for root, dirs, files in os.walk(docs_dir):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                
                with open(file_path, 'r') as f:
                    content = f.read()
                
                links = re.findall(github_link_pattern, content)
                
                for link in links:
                    # Remove line anchor for HEAD request
                    check_url = link.split('#')[0]
                    
                    try:
                        response = requests.head(check_url, timeout=5)
                        if response.status_code != 200:
                            broken_links.append((file_path, link))
                    except requests.RequestException:
                        broken_links.append((file_path, link))
    
    return broken_links
```

## Tool-Specific Solutions

### MkDocs Material

```yaml
# mkdocs.yml - Enable external link features
markdown_extensions:
  - attr_list          # {: } attributes
  - pymdownx.magiclink: # Auto-link GitHub references
      repo_url_shorthand: true
      user: owner
      repo: repository

plugins:
  - privacy:           # Auto add target="_blank" to external links
      links_attr_map:
        target: _blank
```

### GitBook

```javascript
// .gitbook.yaml
plugins:
  - github-source-links:
      repository: "owner/repo"
      branch: "main"
      source_root: "src/"
```

### VuePress

```javascript
// .vuepress/config.js
module.exports = {
  themeConfig: {
    repo: 'owner/repo',
    editLinks: true,
    editLinkText: 'Edit this page on GitHub',
    
    // Custom source link helper
    sourceLinks: {
      base: 'https://github.com/owner/repo/blob/main/',
      transform: (path) => path.replace(/^src\//, '')
    }
  }
}
```

## Best Practices (2024)

### 1. Consistency and Automation
```markdown
<!-- ✅ Use consistent link format -->
Source: [`ClassName.method()`](https://github.com/owner/repo/blob/main/src/module.py#L42){:target="_blank"}

<!-- ✅ Document the pattern in your style guide -->
## Documentation Style Guide

### Source Code Links
- Always link to specific line numbers when referencing implementations
- Use `{:target="_blank"}` to open in new tabs
- Format as: `[ClassName.method()](github_url#L123){:target="_blank"}`
```

### 2. Link Maintenance Strategy
```bash
#!/bin/bash
# scripts/update-source-links.sh

# Update source links when files are moved
find docs/ -name "*.md" -exec sed -i 's|old/path/file.py|new/path/file.py|g' {} \;

# Validate links during CI
python scripts/validate_links.py docs/ || exit 1
```

### 3. Developer Experience
```markdown
<!-- ✅ Provide context and multiple entry points -->
## WorkflowHandle

Main implementation: [`WorkflowHandle`](https://github.com/owner/repo/blob/main/src/workflow/handle.py#L25){:target="_blank"}

Key methods:
- [`submit()`](https://github.com/owner/repo/blob/main/src/workflow/handle.py#L67){:target="_blank"} - Submit workflow for execution
- [`wait_for_completion()`](https://github.com/owner/repo/blob/main/src/workflow/handle.py#L145){:target="_blank"} - Wait for results

See also: [Examples](examples.md) | [API Reference](api.md)
```

### 4. CI/CD Integration
```yaml
# .github/workflows/docs.yml
name: Documentation

on: [push, pull_request]

jobs:
  validate-links:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Validate documentation links
        run: |
          pip install requests
          python scripts/validate_links.py docs/
          
      - name: Build documentation
        run: |
          mkdocs build --strict  # Fail on warnings
```

## Migration Strategy

### From Internal to External Links

```bash
#!/bin/bash
# migrate-links.sh

# Replace relative source links with external GitHub links
REPO_URL="https://github.com/owner/repo/blob/main"

find docs/ -name "*.md" -exec sed -i -E \
  "s|\(\.\./src/([^)]+)\)|($REPO_URL/src/\1){:target=\"_blank\"}|g" {} \;
```

### Gradual Adoption
1. **Phase 1**: Convert critical API documentation
2. **Phase 2**: Add automation for new documentation  
3. **Phase 3**: Migrate remaining documentation
4. **Phase 4**: Implement link validation in CI/CD

## Common Pitfalls

### ❌ Avoid These Patterns

```markdown
<!-- Don't use relative links in documentation -->
[source](../src/file.py)

<!-- Don't hardcode line numbers without validation -->
[method](github.com/repo/file.py#L999)  # Line might not exist

<!-- Don't mix link styles inconsistently -->
[class1](../src/file.py)
[class2](https://github.com/owner/repo/blob/main/src/file2.py)
```

### ✅ Follow These Patterns

```markdown
<!-- Use consistent external links -->
[`Class1`](https://github.com/owner/repo/blob/main/src/file1.py#L25){:target="_blank"}
[`Class2`](https://github.com/owner/repo/blob/main/src/file2.py#L67){:target="_blank"}

<!-- Provide fallback when line numbers are uncertain -->
Source: [`MyClass`](https://github.com/owner/repo/blob/main/src/myclass.py){:target="_blank"} (see `MyClass` definition)

<!-- Group related links for better UX -->
Implementation files:
- [`core.py`](https://github.com/owner/repo/blob/main/src/core.py){:target="_blank"} - Core functionality  
- [`utils.py`](https://github.com/owner/repo/blob/main/src/utils.py){:target="_blank"} - Utility functions
```

## Resources

### Documentation Tools
- **MkDocs**: [Material theme](https://squidfunk.github.io/mkdocs-material/)
- **Sphinx**: [sphinx.ext.linkcode](https://www.sphinx-doc.org/en/master/usage/extensions/linkcode.html)
- **GitBook**: [Source linking](https://docs.gitbook.com/)
- **VuePress**: [Theme configuration](https://vuepress.vuejs.org/theme/)

### Automation Tools
- **mkdocs-gen-files**: [Generate docs programmatically](https://github.com/oprypin/mkdocs-gen-files)
- **mkdocs-macros**: [Template variables](https://github.com/fralau/mkdocs-macros-plugin)
- **Link checkers**: [markdown-link-check](https://github.com/tcort/markdown-link-check)

### Best Practice Guides
- [Google Documentation Style Guide](https://google.github.io/styleguide/docguide/best_practices.html)
- [GitHub Documentation Best Practices](https://docs.github.com/en/contributing/writing-for-github-docs/best-practices-for-github-docs)
- [Write the Docs](https://www.writethedocs.org/guide/)

---

*Last updated: 2024 - Based on modern documentation practices and tooling*