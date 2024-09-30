import os
import openai
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) 
openai.api_key  = os.environ['OPENAI_API_KEY'] 

def get_embeddings(text):
    response = OpenAI().embeddings.create(input = [text], model="text-embedding-3-small")
    return response.data[0].embedding
