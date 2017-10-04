FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN python clone.py --target http://example.com/ 
CMD ["python", "/usr/src/app/snare.py", "--port", "8080",  "--host-ip", "0.0.0.0", "--page-dir", "example.com"]
