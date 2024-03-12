# Tables used by Agent for text to SQL
table_details = {
    "ec2_pricing": "Informatione about EC2 instance pricing and other details.",
}

# prompts for pricing details retrieval
SQL_TEMPLATE_STR = """Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
    You can order the results by a relevant column to return the most interesting examples in the database.\n\n
    Never query for all the columns from a specific table, only ask for a few relevant columns given the question.\n\n
    Pay attention to use only the column names that you can see in the schema description. Be careful to not query for columns that do not exist.
    Qualify column names with the table name when needed.

    Ec2 instance summary:
    m*: "standard instances that offer a balance of compute, memory, and networking resources, suited for a broad range of machine learning tasks with various options for vCPUs and memory configurations."
    c*: "compute-optimized instances, ideal for machine learning workloads that demand high CPU performance, with multiple options to scale up vCPUs and memory to match the compute requirements."
    p*: "accelerated computing instances, equipped with GPU resources, designed for advanced machine learning computations, including deep learning training and inference tasks."
    g*: "accelerated computing instances that provide GPU acceleration, tailored for graphics-intensive applications and machine learning workloads requiring high-performance graphics processing."
    trn*: "accelerated computing instances specifically optimized for cost-effective machine learning training tasks, providing a balance of compute, memory, and networking."

    You are required to use the following format, each taking one line:\n\nQuestion: Question here\nSQLQuery: SQL Query to run\n
    SQLResult: Result of the SQLQuery\nAnswer: Final answer here\n\nOnly use tables listed below.\n{schema}\n\n
    Do not under any circumstance use SELECT * in your query.

    You must convert any mentioned instance names to the format INSTANCE_FAMILY.INSTANCE_SIZE. A few examples:

    Query: "how much is p3.8xlarge per hour?"
    Response: "SELECT instance_name, on_demand_hourly_price \nFROM ec2_pricing\nWHERE instance_name = 'p3.8xlarge'\nORDER BY on_demand_hourly_price DESC"

    Query: "how much does p32xlarge, p3 8xlarge and p3.16xlarge cost per hour?"
    Response: "SELECT instance_name, on_demand_hourly_price \nFROM ec2_pricing\nWHERE instance_name IN ('p3.2xlarge', 'p3.8xlarge', 'p3.16xlarge')\nORDER BY on_demand_hourly_price;"

    Query: "Compare the price per hour of c5.4xlarge and trn1n.32xlarge."
    Response: "SELECT instance_name, on_demand_hourly_price \nFROM ec2_pricing\nWHERE instance_name IN ('c5.4xlarge', 'trn1n.32xlarge')\nORDER BY on_demand_hourly_price ASC;"

    Here are some other useful examples:
    {few_shot_examples}

    Question: {query_str}\nSQLQuery: """

# prompt for summarize pricing details retrieval
RESPONSE_TEMPLATE_STR = """If the <SQL Response> below contains data, then given an input question, synthesize a response from the query results.
    If the <SQL Response> is empty, then you should not synthesize a response and instead respond that no data was found for the quesiton..\n

    \nQuery: {query_str}\nSQL: {sql_query}\n<SQL Response>: {context_str}\n</SQL Response>\n

    Do not make any mention of queries or databases in your response, instead you can say 'according to the latest information' .\n\n
    Please make sure to mention any additional details from the context supporting your response.
    If the final answer contains <dollar_sign>$</dollar_sign>, ADD '\' ahead of each <dollar_sign>$</dollar_sign>.

    Response: """
