FROM freqtradeorg/freqtrade:latest

COPY config.json /freqtrade/config.json

WORKDIR /freqtrade

EXPOSE 8080

CMD ["freqtrade", "trade", "--config", "config.json"]
