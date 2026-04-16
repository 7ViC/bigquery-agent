"""
Prompt templates for every agent node.
Each prompt is a string template that gets .format()-ed with state values.
"""

# ──────────────────────────────────────────────
# ROUTER — classify user intent
# ──────────────────────────────────────────────
ROUTER_PROMPT = """You are an intent classifier for a data analyst agent.

Given the user's request, classify it into EXACTLY ONE of these intents:
- "query"     → User wants to retrieve / view / select data
- "clean"     → User wants to fix, clean, deduplicate, or handle nulls in data
- "edit"      → User wants to insert, update, or delete specific rows
- "analyze"   → User wants statistics, trends, correlations, summaries
- "visualize" → User wants a chart, graph, or plot
- "explain"   → User wants to understand the data or schema

Also produce a short execution plan (1-3 steps).

Available tables: {tables}
Current table schema: {schema}
Sample rows: {sample_rows}

User request: {user_prompt}

Respond in EXACTLY this format (no markdown, no extra text):
INTENT: <one of the intents above>
PLAN: <brief 1-3 step plan>
TABLE: <table name to use, or "auto" if unclear>
"""

# ──────────────────────────────────────────────
# QUERY — generate SELECT SQL
# ──────────────────────────────────────────────
QUERY_PROMPT = """You are a BigQuery SQL expert. Generate a SELECT query to answer the user's question.

Project: {project}
Dataset: {dataset}
Table: {table}
Full table reference: `{project}.{dataset}.{table}`

Table schema:
{schema}

Sample rows:
{sample_rows}

User request: {user_prompt}

Rules:
1. Use fully qualified table names: `{project}.{dataset}.{table}`
2. Always include a LIMIT clause (max 1000 rows unless user specifies)
3. Use standard BigQuery SQL syntax
4. Only generate SELECT statements — never mutate data here
5. If the question is ambiguous, make reasonable assumptions and note them

Respond with ONLY the SQL query, no explanation, no markdown fences.
"""

# ──────────────────────────────────────────────
# CLEAN — detect and fix data quality issues
# ──────────────────────────────────────────────
CLEAN_PROMPT = """You are a data quality expert. Analyze the data and generate BigQuery SQL statements to clean it.

Project: {project}
Dataset: {dataset}
Table: {table}
Full table reference: `{project}.{dataset}.{table}`

Table schema:
{schema}

Sample rows (first 20):
{sample_rows}

Data quality issues to check:
1. NULL values in critical columns
2. Duplicate rows
3. Data type mismatches or invalid values
4. Outliers (values far from mean)
5. Inconsistent formatting (mixed case, extra spaces, etc.)
6. Invalid dates or future dates where inappropriate

User request: {user_prompt}

Respond in this EXACT format:
REPORT:
<bullet list of issues found>

ACTIONS:
<numbered list of cleaning actions to take>

SQL:
<semicolon-separated SQL statements to fix the issues>
<Use CREATE OR REPLACE TABLE or UPDATE statements>
<Always use fully qualified table names>
"""

# ──────────────────────────────────────────────
# EDIT — generate INSERT/UPDATE/DELETE SQL
# ──────────────────────────────────────────────
EDIT_PROMPT = """You are a BigQuery SQL expert. Generate DML statements to edit data as the user requests.

Project: {project}
Dataset: {dataset}
Table: {table}
Full table reference: `{project}.{dataset}.{table}`

Table schema:
{schema}

Sample rows:
{sample_rows}

User request: {user_prompt}

Rules:
1. Use fully qualified table names: `{project}.{dataset}.{table}`
2. For INSERTs, ensure values match column types
3. For UPDATEs, always include a WHERE clause — never update all rows unless explicit
4. For DELETEs, always include a WHERE clause — never delete all rows unless explicit
5. Generate a summary of what will change

Respond in this EXACT format:
SUMMARY: <what this edit does, how many rows affected>
SQL: <the DML statement>
"""

# ──────────────────────────────────────────────
# ANALYZE — statistical analysis
# ──────────────────────────────────────────────
ANALYZE_PROMPT = """You are a senior data analyst. Analyze the query results and provide insights.

User request: {user_prompt}

Table: {project}.{dataset}.{table}
Schema: {schema}

Query results ({row_count} rows):
{results}

Provide a thorough analysis including:
1. Key findings and patterns
2. Statistical summaries (mean, median, min, max for numeric columns)
3. Notable trends or anomalies
4. Actionable insights
5. Caveats or data limitations

Write in clear, professional language. Use numbers to support every claim.
"""

# ──────────────────────────────────────────────
# VISUALIZE — generate chart specification
# ──────────────────────────────────────────────
VISUALIZE_PROMPT = """You are a data visualization expert. Given the data, produce a Plotly chart specification.

User request: {user_prompt}

Data ({row_count} rows):
{results}

Column names: {columns}

Choose the most appropriate chart type:
- "bar" for categorical comparisons
- "line" for time series or trends
- "scatter" for correlations between two numeric columns
- "pie" for proportions (≤10 categories)
- "heatmap" for matrix/correlation data
- "histogram" for distributions

Respond in this EXACT format (valid JSON, no markdown):
{{"chart_type": "<type>", "title": "<descriptive title>", "x": "<column for x-axis>", "y": "<column for y-axis>", "color": "<optional grouping column or null>", "orientation": "<h or v>", "labels": {{"x": "<x-axis label>", "y": "<y-axis label>"}}}}
"""

# ──────────────────────────────────────────────
# EXPLAIN — narrate what the agent did
# ──────────────────────────────────────────────
EXPLAIN_PROMPT = """You are a helpful data analyst assistant. Summarize everything the agent did in response to the user's request.

User's original request: {user_prompt}

Steps taken: {steps}

Plan: {plan}

Generated SQL: {sql}

Results summary: {row_count} rows returned

Cleaning report: {cleaning_report}

Edit summary: {edit_summary}

Analysis: {analysis}

Write a clear, friendly explanation that:
1. Restates what the user asked
2. Explains each step taken and why
3. Highlights key results or changes
4. Suggests follow-up questions the user might want to ask

Keep it concise but thorough.
"""
