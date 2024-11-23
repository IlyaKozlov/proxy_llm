FROM python:3.13.0-alpine3.20
RUN mkdir /llm_proxy

ADD requirements.txt /llm_proxy
RUN pip install -r /llm_proxy/requirements.txt
ADD proxy /llm_proxy/proxy
ADD .env /llm_proxy

CMD python3 /llm_proxy/proxy/api.py