FROM freqtradeorg/freqtrade:latest

COPY config.json /freqtrade/config.json

WORKDIR /freqtrade

EXPOSE 8080

ENTRYPOINT ["freqtrade"]
CMD ["trade", "--config", "config.json"]
