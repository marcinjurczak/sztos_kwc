FROM python
ENV POETRY_HOME=/etc/poetry
# TODO: split off into two images
RUN apt-get update \
    && apt-get install build-essential \
    && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
COPY poetry.lock pyproject.toml /app/
WORKDIR /app
RUN $POETRY_HOME/bin/poetry install
COPY . /app
ENTRYPOINT ["/etc/poetry/bin/poetry", "run"]
