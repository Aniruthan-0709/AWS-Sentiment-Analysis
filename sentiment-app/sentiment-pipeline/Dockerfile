FROM bitnami/spark:3.4.1

# Switch to root to install Python packages
USER root

# Install Python dependencies
RUN pip install --no-cache-dir \
    boto3 \
    pandas \
    scikit-learn \
    joblib \
    python-dotenv

# Set working directory
WORKDIR /app

# Copy preprocessing and inference scripts
COPY run_clean.py .
COPY run_infer.py .
COPY run_all.py .

# Run the full pipeline (clean + infer)
ENTRYPOINT ["python", "run_all.py"]
