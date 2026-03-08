FROM freqtradeorg/freqtrade:latest

# Copy your custom strategy and config
COPY config.json /freqtrade/config.json
COPY strategies/ /freqtrade/user_data/strategies/

WORKDIR /freqtrade

EXPOSE 8080

ENTRYPOINT ["freqtrade"]
CMD ["trade", "--config", "config.json", "--strategy", "SimpleStrategy"]
