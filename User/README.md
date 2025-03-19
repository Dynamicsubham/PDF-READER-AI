# RAG with Bedrock Application

## Overview

This project is a Retrieval-Augmented Generation (RAG) system utilizing AWS Bedrock and FAISS for efficient document retrieval and question-answering. The application consists of a backend built with FastAPI and a frontend built with React.

## Prerequisites

Ensure you have the following installed before running the application:

- Docker & Docker Compose
- AWS Credentials (for S3 and Bedrock access)
- Node.js (for frontend development, if running without Docker)
- Python 3.9+ (for backend development, if running without Docker)s

## Project Structure

```
├── backend
│   ├── main.py       # FastAPI application
│   ├── requirements.txt  # Python dependencies
│   ├── Dockerfile    # Backend container setup
├── frontend
│   ├── src
│   │   ├── App.js    # React application entry point
│   │   ├── App.css   # Styling for UI
│   ├── package.json  # Frontend dependencies
│   ├── Dockerfile    # Frontend container setup
├── docker-compose.yml  # Docker Compose for running frontend & backend





```

## Project Architecture Design

![Architecture Diagram](https://github.com/Dynamicsubham/PDF-Reader-User/blob/master/AI%20Architechture%20design.png)

## Installation & Setup

### Using Docker (Recommended)

Build and run the application using Docker:

```sh
# Build the Docker images
docker-compose build

# Start the services
docker-compose up
```

The application will be available at:

- **Backend API (Swagger Docs):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend Application:** [http://localhost:3000](http://localhost:3000)

### Running Manually (Without Docker)

#### Backend Setup

1. Navigate to the backend directory:
   ```sh
   cd backend
   ```
2. Create a virtual environment and install dependencies:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Start the FastAPI server:
   ```sh
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

1. Navigate to the frontend directory:
   ```sh
   cd frontend
   ```
2. Install dependencies:
   ```sh
   npm install
   ```
3. Start the React application:
   ```sh
   npm start
   ```

The frontend should now be running at [http://localhost:3000](http://localhost:3000).

## API Endpoints

| Endpoint                 | Method | Description                                            |
| ------------------------ | ------ | ------------------------------------------------------ |
| `/list-contexts`         | GET    | Lists available FAISS contexts                         |
| `/load-context`          | POST   | Loads a specific FAISS context                         |
| `/preview-context`       | GET    | Retrieves a preview of a selected context              |
| `/generate-auto-prompts` | POST   | Generates common questions from context                |
| `/ask`                   | POST   | Asks a question and retrieves an AI-generated response |

## Frontend Features

- Dropdown selection for available contexts
- Context preview (first 500 characters)
- Question input and response retrieval
- Clean and responsive UI

## Environment Variables

Ensure the following environment variables are set:

```sh
BUCKET_NAME=your_s3_bucket
AWS_REGION=your_aws_region
AWS_ACCESS_KEY=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
```

These variables should be provided via `.env` files or Docker environment settings.

## License

This project is licensed under the MIT License.

## Contact

For any inquiries or issues, reach out to **Subham Agarwal**.

=======
# PDF-Reader-User
