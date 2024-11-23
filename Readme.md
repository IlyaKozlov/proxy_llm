Proxy for LLM-s, for development
Cache LLM-s call and don't repeat the call to the LLM server, saves you time and money. 

How to configure and run it:

If you use langchain set the base_url
```python
from langchain_openai import ChatOpenAI

ChatOpenAI(..., base_url="http://127.0.0.1:1785/v1/")
```

If you use azure, you can do as following:
```python
from langchain_openai import AzureChatOpenAI

# not necessary to specify base_url
# you can use AZURE_OPENAI_ENDPOINT instead
AzureChatOpenAI(...)  
```
and set env variable `AZURE_OPENAI_ENDPOINT="http://127.0.0.1:1785"`

In this case you should change .env file.

Run with docker:
```shell
docker build -t proxy_llm -f Dockerfile .
docker run -ti --rm -p 1785:1785 proxy_llm 
```