FROM python:3.7-alpine
LABEL Suhan Saha suhansaha@gmail.com
WORKDIR /code
ENV FLASK_APP app.py
ENV FLASK_RUN_HOST 0.0.0.0

#Install dependencies for python modules
RUN apk update
RUN apk --no-cache --update-cache add alpine-sdk musl-dev wget git \
build-base postgresql-dev libffi-dev python3-dev linux-headers \
gfortran perl libgcc libquadmath musl libgfortran lapack-dev \
gcc py-pip freetype-dev libpng-dev openblas-dev libstdc++ zlib

RUN pip install -U pip setuptools

# install openblas
RUN wget https://github.com/xianyi/OpenBLAS/archive/v0.3.6.tar.gz \
	&& tar -xf v0.3.6.tar.gz \
	&& cd OpenBLAS-0.3.6/ \
	&& make BINARY=64 FC=$(which gfortran) USE_THREAD=1 \
	&& make PREFIX=/usr/lib/openblas install

RUN ATLAS=/usr/lib/openblas/lib/libopenblas.so LAPACK=/usr/lib/openblas/lib/libopenblas.so pip install scipy==1.3
RUN export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/lib/openblas/lib/

RUN ln -s /usr/include/locale.h /usr/include/xlocale.h

# Install Various Python modules
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Install TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
  tar -xvzf ta-lib-0.4.0-src.tar.gz && \
  cd ta-lib/ && \
  ./configure --prefix=/usr && \
  make && \
  make install

ENV TA_LIBRARY_PATH=/usr/lib
ENV TA_INCLUDE_PATH=/usr/include

# Install Kite-Connect
RUN git clone https://github.com/mrjbq7/ta-lib.git ta-lib-py && cd ta-lib-py && python setup.py install
RUN pip install --upgrade kiteconnect
RUN pip install TA-lib

#RUN apk del musl-dev wget git \
#build-base postgresql-dev libffi-dev linux-headers \
#gfortran perl libgcc libquadmath musl libgfortran lapack-dev \
#gcc py-pip freetype-dev libpng-dev openblas-dev 

RUN apk add --no-cache \
            --allow-untrusted \
            --repository \
             http://dl-3.alpinelinux.org/alpine/edge/testing \
            hdf5 \
            hdf5-dev && \
    apk add --no-cache \
        build-base
RUN pip install --no-cache-dir --no-binary :all: tables h5py
RUN pip uninstall -y enum34
RUN pip install flask-login sqlalchemy flask-sqlalchemy alembic flask-migrate flask-mail dash-bootstrap-components  
RUN pip install dash-editor-components dash-auth
RUN pip install flask-login flask-session celery pymongo
RUN apk --no-cache del build-base
RUN apk add tzdata

RUN cp /usr/share/zoneinfo/Asia/Calcutta /etc/localtime
RUN echo "Asia/Calcutta" > /etc/timezone

WORKDIR /code
# Expose port 5000 for gunicorn and 8888 for Jupyter
EXPOSE 5000
EXPOSE 8888

# Delete build artifacts and tempfile
RUN rm -R v0.3.6.tar.gz OpenBLAS-0.3.6 ta-lib-0.4.0-src.tar.gz ta-lib ta-lib-py  
