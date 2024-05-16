# Tables used by Agent for text to SQL
table_details = {
    "hardware_pricing": "Information about tools pricing and other details.",
}

# prompts for pricing details retrieval
SQL_TEMPLATE_STR = """Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
    You can order the results by a relevant column to return the most interesting examples in the database.\n\n
    Never query for all the columns from a specific table, only ask for a few relevant columns given the question.\n\n
    Pay attention to use only the column names that you can see in the schema description. Be careful to not query for columns that do not exist.
    Qualify column names with the table name when needed.

    You are required to use the following format, each taking one line:\n\nQuestion: Question here\nSQLQuery: SQL Query to run\n
    SQLResult: Result of the SQLQuery\nAnswer: Final answer here\n\nOnly use tables listed below.\n{schema}\n\n
    Do not under any circumstance use SELECT * in your query.
    
    Only search for sku nunber if there is specific mention of a number starting with "sku_". If no specific sku_id is mentioned match it to one of these types to get some general information and data. If there is text in the image starting with "sku_" then you must call this out. 
    tool_types = ['Hammer', 'Screwdriver', 'Wrench', 'Drill', 'Saw', 'Pliers', 'Chisel', 'Level', 'Tape Measure', 'Utility Knife', 'Other']

    Never filter on more than one tool type.
    A valid sku must start with "sku_", only filter on sku if the question mentions a valid sku number.


    Question: {query_str}\nSQLQuery: """

# prompt for summarize pricing details retrieval
RESPONSE_TEMPLATE_STR = """If the <SQL Response> below contains data, then given an input question, synthesize a response from the query results.
    If the <SQL Response> is empty, then you should not synthesize a response and instead respond that no data was found for the quesiton..\n

    \nQuery: {query_str}\nSQL: {sql_query}\n<SQL Response>: {context_str}\n</SQL Response>\n

    Do not make any mention of queries or databases in your response, instead you can say 'according to the latest information' .\n\n
    Please make sure to mention any additional details from the context supporting your response.
    If the final answer contains <dollar_sign>$</dollar_sign>, ADD '\' ahead of each <dollar_sign>$</dollar_sign>.

    Response: """
