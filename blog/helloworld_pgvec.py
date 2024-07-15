## REFERENCE: https://www.timescale.com/blog/postgresql-as-a-vector-database-create-store-and-query-openai-embeddings-with-pgvector/ 

import os
from openai import OpenAI
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import execute_values
import pandas as pd 
import numpy as np 
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) 
OPENAI_KEY = os.environ['OPENAI_API_KEY'] 

# Read data 
df = pd.read_csv('blog_posts_data_2.csv')
print("old df: ", df.head())

# Create embeddings 
def get_embeddings(text):
    response = OpenAI(api_key=OPENAI_KEY).embeddings.create(input = [text], model="text-embedding-3-small")
    return response.data[0].embedding

def get_distance(str1, str2):
    return np.dot(get_embeddings(str1), get_embeddings(str2))

# print("== SIMILARITY SCORES: ==")
# query1 = "The P versus NP problem is a major unsolved problem in theoretical computer science. Informally, it asks whether every problem whose solution can be quickly verified can also be quickly solved."
# query2 = """The relation between the complexity classes P and NP is studied in computational complexity theory, the part of the theory of computation dealing with the resources required during computation to solve a given problem. The most common resources are time (how many steps it takes to solve a problem) and space (how much memory it takes to solve a problem).
# In such analysis, a model of the computer for which time must be analyzed is required. Typically such models assume that the computer is deterministic (given the computer's present state and any inputs, there is only one possible action that the computer might take) and sequential (it performs actions one after the other).
# In this theory, the class P consists of all decision problems (defined below) solvable on a deterministic sequential machine in a duration polynomial in the size of the input; the class NP consists of all decision problems whose positive solutions are verifiable in polynomial time given the right information, or equivalently, whose solution can be found in polynomial time on a non-deterministic machine.[7] Clearly, P ⊆ NP. Arguably, the biggest open question in theoretical computer science concerns the relationship between those two classes:
# Is P equal to NP?"""
# query3 = """To attack the P = NP question, the concept of NP-completeness is very useful. NP-complete problems are problems that any other NP problem is reducible to in polynomial time and whose solution is still verifiable in polynomial time. That is, any NP problem can be transformed into any NP-complete problem. Informally, an NP-complete problem is an NP problem that is at least as "tough" as any other problem in NP.
# NP-hard problems are those at least as hard as NP problems; i.e., all NP problems can be reduced (in polynomial time) to them. NP-hard problems need not be in NP; i.e., they need not have solutions verifiable in polynomial time.
# For instance, the Boolean satisfiability problem is NP-complete by the Cook–Levin theorem, so any instance of any problem in NP can be transformed mechanically into a Boolean satisfiability problem in polynomial time. The Boolean satisfiability problem is one of many NP-complete problems. If any NP-complete problem is in P, then it would follow that P = NP. However, many important problems are NP-complete, and no fast algorithm for any of them is known.
# From the definition alone it is unintuitive that NP-complete problems exist; however, a trivial NP-complete problem can be formulated as follows: given a Turing machine M guaranteed to halt in polynomial time, does a polynomial-size input that M will accept exist?[11] It is in NP because (given an input) it is simple to check whether M accepts the input by simulating M; it is NP-complete because the verifier for any particular instance of a problem in NP can be encoded as a polynomial-time machine M that takes the solution to be verified as input. Then the question of whether the instance is a yes or no instance is determined by whether a valid input exists."""
# query4 = "Machine learning (ML) is a field of study in artificial intelligence concerned with the development and study of statistical algorithms that can learn from data and generalize to unseen data and thus perform tasks without explicit instructions.[1] Recently, artificial neural networks have been able to surpass many previous approaches in performance.[2]"
# print(get_distance(query1, query2))
# print(get_distance(query2, query3))
# print(get_distance(query1, query3))
# print(get_distance(query1, query4))
# print(get_distance(query2, query4))
# print(get_distance(query3, query4))

def embed_df(df):
    new_list = []
    # Split up the text into token sizes of around 512 tokens
    for i in range(len(df.index)):
        text = df['content'][i]
        new_list.append([df['title'][i], df['content'][i], get_embeddings(text)])

    # Create a new dataframe from the list
    df_new = pd.DataFrame(new_list, columns=['title', 'content', 'embeddings'])
    # print("new df: ", df_new.head())
    return df_new

df_new = embed_df(df)

# psql db
conn = psycopg2.connect(
    database="postgres",
    user='postgres',
    password='lycheesmatcha',
    host='localhost',
    port='5432'
)
cur = conn.cursor()

# install pgvector
cur.execute('CREATE EXTENSION IF NOT EXISTS vector')
conn.commit()
register_vector(conn)

# create embeddings table, if it doesn't already exist
cur.execute("select * from information_schema.tables where table_name=%s", ('embeddings2',))
if bool(not cur.rowcount):
    print("creating embeddings2 table...")
    table_create_command = """
        CREATE TABLE embeddings2 (
                    id bigserial primary key, 
                    title text,
                    url text,
                    content text,
                    tokens integer,
                    embedding vector(1536)
                    );
                    """

    cur.execute(table_create_command)
    cur.close()
    conn.commit()

    #Batch insert embeddings and metadata from dataframe into PostgreSQL database
    register_vector(conn)
    cur = conn.cursor()
    # Prepare the list of tuples to insert
    data_list = [(row['title'], row['content'], np.array(row['embeddings'])) for index, row in df_new.iterrows()]

    # print(data_list) 

    # Use execute_values to perform batch insertion
    execute_values(cur, "INSERT INTO embeddings2 (title, content, embedding) VALUES %s", data_list)
    # Commit after we insert all embeddings
    conn.commit()


# Helper function: Get top 3 most similar documents from the database
def get_top3_similar_docs(query_embedding, conn):
    embedding_array = np.array(query_embedding)
    # Register pgvector extension
    register_vector(conn)
    cur = conn.cursor()
    # Get the top 3 most similar documents using the KNN <=> operator
    cur.execute("SELECT content FROM embeddings2 ORDER BY embedding <=> %s LIMIT 3", (embedding_array,))
    top3_docs = cur.fetchall()
    return top3_docs

query = "Since we have the encoding of M through <M>, does this mean that it is safe to assume that we have access to the transition function/states of said TM?"
print("top 3: ", get_top3_similar_docs(get_embeddings(query), conn))

