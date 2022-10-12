FROM nikolaik/python-nodejs:python3.9-nodejs16-alpine

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN npm install
