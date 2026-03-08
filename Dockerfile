FROM freqtradeorg/freqtrade:latest

COPY config.json /freqtrade/config.json

WORKDIR /freqtrade

EXPOSE 8080

# Override the default entrypoint and directly run the freqtrade binary
ENTRYPOINT []
CMD ["/usr/local/bin/freqtrade", "trade", "--config", "config.json"]
