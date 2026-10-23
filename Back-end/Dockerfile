
FROM python:3.14

FROM docker.io/pytorch/pytorch
ARG gh_username=JaidedAI
ARG service_home="/home/EasyOCR"

WORKDIR /code



COPY ./requirements.txt /code/requirements.txt


RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

RUN apt-get update -y && \
    apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-dev \
    git \
    # cleanup
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists

RUN cd "$service_home" \
    && python setup.py build_ext --inplace -j 4 \
    && python -m pip install -e .

COPY ./app /code/app


CMD ["fastapi", "run", "app/main.py", "--port", "80"]