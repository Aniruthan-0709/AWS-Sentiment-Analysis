FROM bitnami/spark:3.4.1

# Install Python packages inside Spark container
USER root
RUN pip install boto3 pandas

# Copy your Spark job script into the container
COPY run_clean.py .

# Use spark-submit to run the job
ENTRYPOINT ["spark-submit", "run_clean.py"]
