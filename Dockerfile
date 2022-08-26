FROM python:3.9.13

WORKDIR /discordgsm

COPY . .

RUN pip3 install -r requirements.txt

RUN curl -sL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs
RUN npm run build
