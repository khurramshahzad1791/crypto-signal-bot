FROM freqtradeorg/freqtrade:latest

COPY config.json /freqtrade/config.json

WORKDIR /freqtrade

EXPOSE 8080

# Override entrypoint and run the correct binary
ENTRYPOINT []
CMD ["/usr/local/bin/freqtrade", "trade", "--config", "config.json"]
