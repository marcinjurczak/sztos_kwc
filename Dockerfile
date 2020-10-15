FROM debian AS builder

WORKDIR /bwrap

RUN apt-get update \
    && apt-get install -y build-essential libcap-dev curl \
    && curl https://github.com/containers/bubblewrap/releases/download/v0.4.1/bubblewrap-0.4.1.tar.xz -L -o bubblewrap.tar.xz \
    && tar -xf bubblewrap.tar.xz \
    && cd bubblewrap-0.4.1 \
    && ./configure --prefix=/usr \
    && make install

FROM python
ENV POETRY_HOME=/etc/poetry
# TODO: split off into two images
COPY --from=builder /usr/bin/bwrap /usr/bin/bwrap
RUN apt-get update \
    && apt-get install build-essential \
    && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
COPY poetry.lock pyproject.toml /app/
WORKDIR /app
RUN $POETRY_HOME/bin/poetry install
COPY . /app
ENTRYPOINT ["/etc/poetry/bin/poetry", "run"]
