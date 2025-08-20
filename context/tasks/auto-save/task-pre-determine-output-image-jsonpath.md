# Task: Pre-determine JSONPath for Output Image Filenames Before Submission

Command / Goal Breakdown:
- Assess feasibility of computing JSONPath expressions for final output image filenames *prior* to workflow submission.
- Leverage existing stored input JSONPath patterns (e.g., `$.nodes[?(@.id='<node_id>')].data.inputs.<field_name>`) as precedent.
- Analyze runtime structures: `session.results`, `prepared_source_mapping`, `execution_graph`, and how prepared node IDs may alter deterministic paths.
- Determine if a stable pre-submission JSONPath to future `image.image_name` is possible for each declared output node.
- If possible, specify the JSONPath template; if not, document why and offer best-effort predictive forms plus post-run resolution strategy.
- Implement code changes or helper to expose best-effort JSONPath (or resolver) in `WorkflowHandle`.
