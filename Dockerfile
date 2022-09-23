FROM nikolaik/python-nodejs:python3.9-nodejs16-alpine

WORKDIR /app
COPY . .

RUN pip3 install -r requirements.txt
RUN npm run build
