FROM debian AS builder

RUN apt-get update \
    && apt-get install -y build-essential libcap-dev curl

WORKDIR /bwrap
RUN curl https://github.com/containers/bubblewrap/releases/download/v0.4.1/bubblewrap-0.4.1.tar.xz -L -o bubblewrap.tar.xz \
    && tar -xf bubblewrap.tar.xz \
    && cd bubblewrap-0.4.1 \
    && ./configure --prefix=/usr \
    && make install

WORKDIR /setrlimit
COPY c/setrlimit.c /setrlimit/
RUN gcc -O3 -Wall -Wpedantic -Wextra -Werror setrlimit.c -o setrlimit && chmod +x setrlimit

FROM python
ENV POETRY_HOME=/etc/poetry
# TODO: split off into two images
RUN apt-get update \
    && apt-get install build-essential \
    && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

COPY --from=builder /usr/bin/bwrap /usr/bin/bwrap
COPY --from=builder /setrlimit/setrlimit /usr/bin/setrlimit

COPY poetry.lock pyproject.toml /app/
WORKDIR /app
RUN $POETRY_HOME/bin/poetry install
COPY . /app
ENTRYPOINT ["/etc/poetry/bin/poetry", "run"]
