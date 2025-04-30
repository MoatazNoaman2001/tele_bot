FROM python:3.10-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot.py .

# Add modified database connection script
RUN echo '#!/bin/bash\n\
# Wait for MySQL to be ready\n\
echo "Waiting for MySQL..."\n\
while ! nc -z $DB_HOST 3320; do\n\
  sleep 1\n\
done\n\
echo "MySQL started"\n\
\n\
# Run the bot\n\
python bot.py' > start.sh

RUN apt-get update && apt-get install -y netcat-openbsd && \
    chmod +x start.sh

# Set environment variables
ENV DB_HOST=db \
    DB_USER=alya \
    DB_PASSWORD=mumdad2002 \
    DB_NAME=easymoneybot

CMD ["./start.sh"]