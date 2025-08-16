# Setup Instructions

## Prerequisites

- Python 3.12 or higher
- RabbitMQ credentials
- (Optional) Access to upload endpoint with JWT token

## Installation

1. Create and activate a virtual environment:
```bash
python -m venv higgs_audio_env
source higgs_audio_env/bin/activate  # On Windows: higgs_audio_env\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```

2. Update the `.env` file with your credentials:

### RabbitMQ Configuration
```
RABBITMQ_PASSWORD=your_actual_password_here
```

Replace `your_actual_password_here` with the actual RabbitMQ password provided in the RABBITMQ_PYTHON_CONSUMER.md file.

### Upload Configuration (Optional)
If you want to enable automatic upload to the server:
```
UPLOAD_ENABLED=true
UPLOAD_TOKEN=your_actual_jwt_token_here
```

Replace `your_actual_jwt_token_here` with your actual JWT token.

## Running the Application

1. Make sure RabbitMQ is accessible at the configured host
2. Run the application:
```bash
python src/main.py
```

The application will:
- Connect to RabbitMQ
- Start consuming messages from the queue
- Process speech messages by generating audio
- (Optional) Upload generated audio to the configured endpoint

## Troubleshooting

### Authentication Error
If you see "ACCESS_REFUSED - Login was refused using authentication mechanism PLAIN":
- Verify the RabbitMQ password in your `.env` file
- Ensure the username `admin` has access to the virtual host `/`
- Check that the RabbitMQ server is accessible at `rabbit.oscgre.com:5672`

### Upload Errors
If uploads are failing:
- Verify the JWT token is valid and not expired
- Ensure the upload endpoint is accessible
- Check that the speech UUID exists on the server

### Mock Audio Generation
The current implementation uses a mock audio generator for testing. To use the actual Higgs Audio Engine, you'll need to implement the `HiggsAudioGenerator` class following the pattern in `test2.py`.