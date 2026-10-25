FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# libs gráficas exigidas pelo opencv que o iopaint instala
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# torch só-CPU (a versão padrão do PyPI puxa CUDA e fica enorme)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir iopaint

EXPOSE 8080

# O modelo (lama) é baixado na primeira execução e guardado em /root/.cache (volume)
CMD ["iopaint", "start", "--model=lama", "--device=cpu", "--host=0.0.0.0", "--port=8080"]