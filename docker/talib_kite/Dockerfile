FROM python:3.7
WORKDIR /code
ENV FLASK_APP app.py
ENV FLASK_RUN_HOST 0.0.0.0
#RUN apk add --no-cache gcc musl-dev linux-headers make
#RUN sudo apt-get install python3.7-dev
RUN pip install -U pip setuptools
#RUN apt-get install libffi-dev python-dev python3.7-dev

RUN pip install numpy
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && cd ta-lib/ && \
     ./configure --prefix=/usr && make && make install

ENV TA_LIBRARY_PATH=/usr/lib
ENV TA_INCLUDE_PATH=/usr/include
#ENV TA_LIBRARY_PATH=/code/talib/lib
#ENV TA_INCLUDE_PATH=/code/talib/include
#WORKDIR /code
RUN pip install TA-Lib
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install -U pip setuptools
RUN pip install --upgrade kiteconnect
RUN rm -R ta-lib ta-lib-0.4.0-src.tar.gz
COPY . .
#CMD ["flask", "run"]