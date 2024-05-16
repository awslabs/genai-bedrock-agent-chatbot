from sqlalchemy import create_engine
from llama_index.core.objects import ObjectIndex, SQLTableNodeMapping, SQLTableSchema
from llama_index.core.indices.struct_store import SQLTableRetrieverQueryEngine
from llama_index.core import VectorStoreIndex
from llama_index.core import SQLDatabase
from llama_index.core import ServiceContext
from llama_index.embeddings.bedrock import BedrockEmbedding
from llama_index.core.prompts import Prompt
from connections import Connections
from prompt_templates import SQL_TEMPLATE_STR, RESPONSE_TEMPLATE_STR, table_details
from llama_index.core.schema import TextNode
from llama_index.core.prompts import PromptTemplate
import csv
import json

import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def create_sql_engine():
    """
    Connects to Amazon Athena.

    Args:
        None

    Returns:
        engine (sqlalchemy.engine.base.Engine): SQL Alchemy engine.
    """
    s3_staging_dir = Connections.athena_bucket_name
    region = Connections.region_name
    database = Connections.text2sql_database
    # Construct the connection string
    conn_url = f"awsathena+rest://athena.{region}.amazonaws.com/{database}?s3_staging_dir=s3://{s3_staging_dir}"
    # Create an SQLAlchemy engine
    engine = create_engine(conn_url)
    return engine


def get_few_shot_retriever(FEWSHOT_EXAMPLES_PATH):
    """
    Creates a fewshot retriever from a csv file.

    Args:
        FEWSHOT_EXAMPLES_PATH (str): Path to fewshot examples csv file.

    Returns:
        few_shot_retriever (VectorStoreIndex): VectorStoreIndex with fewshot examples.
        data_dict (dict): Dictionary with fewshot examples.
    """
    with open(FEWSHOT_EXAMPLES_PATH, newline="", encoding="utf-8-sig") as csvfile:
        # with StringIO(file_content) as file_like_object:
        reader = csv.DictReader(csvfile)
        data, data_dict, few_shot_nodes = [], {}, []
        data, data_dict, few_shot_nodes = [], {}, []
        for row in reader:
            data.append(row["example_input_question"])
            data_dict[row["example_input_question"]] = row
            few_shot_nodes.append(
                TextNode(text=json.dumps(row["example_input_question"]))
            )

    embed_model = BedrockEmbedding(
        client=Connections.bedrock_client, model_name="amazon.titan-embed-text-v1"
    )

    few_shot_service_context = ServiceContext.from_defaults(
        embed_model=embed_model, llm=None
    )

    few_shot_index = VectorStoreIndex(
        few_shot_nodes, service_context=few_shot_service_context
    )
    few_shot_retriever = few_shot_index.as_retriever(similarity_top_k=2)
    return few_shot_retriever, data_dict


def few_shot_examples_fn(**kwargs):
    """
    Retrieves fewshot examples.

    Args:
        kwargs (dict): Dictionary with query_str.

    Returns:
        example_set (str): Example set.
    """
    question = kwargs["query_str"]
    retrieved_nodes = few_shot_retriever.retrieve(question)
    result_strs = []
    example_set = "No example set provided"
    for n in retrieved_nodes:
        logger.info(f"Few shots node:\n {n}")
        content = json.loads(n.get_content())
        raw_dict = data_dict[content]
        example = [f"{k.capitalize()}: {raw_dict[k]}" for k in raw_dict.keys()]

        result_str = "\n".join(example)
        result_strs.append(result_str)

    example_set = "\n\n".join(result_strs)
    logger.info("- Example set provided:")
    logger.info(example_set)
    return example_set


few_shot_retriever, data_dict = get_few_shot_retriever(
    Connections.fewshot_examples_path
)

SQL_PROMPT = PromptTemplate(
    SQL_TEMPLATE_STR,
    function_mappings={
        "few_shot_examples": few_shot_examples_fn,
    },
)

RESPONSE_PROMPT = Prompt(RESPONSE_TEMPLATE_STR)


def create_query_engine(
    model_name="ClaudeInstant", SQL_PROMPT=SQL_PROMPT, RESPONSE_PROMPT=RESPONSE_PROMPT
):
    """Generates a query engine and object index fo answering questions using SQL retrieval.

    Args:
        model_name (str): Model to use. Defaults to "ClaudeInstant".
        SQL_PROMPT (PromptTemplate): Prompt for generating SQL. Defaults to SQL_PROMPT.
        RESPONSE_PROMPT (Prompt): Prompt for generating final response. Defaults to RESPONSE_PROMPT.

    Returns:
        query_engine (SQLTableRetrieverQueryEngine): SQLTableRetrieverQueryEngine object.
        obj_index (ObjectIndex): ObjectIndex object.
    """
    # create sql database object
    engine = create_sql_engine()
    sql_database = SQLDatabase(engine, sample_rows_in_table_info=2)

    embed_model = BedrockEmbedding(
        client=Connections.bedrock_client, model_name="amazon.titan-embed-text-v1"
    )

    # initialize llm
    llm = Connections.get_bedrock_llm(model_name=model_name, max_tokens=1024)

    # initialize service context
    service_context = ServiceContext.from_defaults(llm=llm, embed_model=embed_model)

    table_node_mapping = SQLTableNodeMapping(sql_database)
    table_schema_objs = []
    tables = list(sql_database._all_tables)
    for table in tables:
        table_schema_objs.append(
            (SQLTableSchema(table_name=table, context_str=table_details[table]))
        )

    obj_index = ObjectIndex.from_objects(
        table_schema_objs,
        table_node_mapping,
        VectorStoreIndex,
        service_context=service_context,
    )

    query_engine = SQLTableRetrieverQueryEngine(
        sql_database,
        obj_index.as_retriever(similarity_top_k=5),
        service_context=service_context,
        text_to_sql_prompt=SQL_PROMPT,
        response_synthesis_prompt=RESPONSE_PROMPT,
    )
    prompts_dict = query_engine.get_prompts()
    logger.info(f"prompts_dict{prompts_dict}")

    return query_engine, obj_index


query_engine, obj_index = create_query_engine()
