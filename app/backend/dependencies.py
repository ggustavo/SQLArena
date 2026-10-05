"""
Dependências do FastAPI (injeção) para os gerenciadores de AWS.

Uma instância nova por requisição é barata (os managers só guardam config e um
cliente boto3) e evita problemas de estado compartilhado entre requisições.
"""
from app.dynamodb.dynamo_manager import DynamoDBManager
from app.s3.s3_manager import S3Manager


def get_s3_manager() -> S3Manager:
    return S3Manager()


def get_dynamo_manager() -> DynamoDBManager:
    return DynamoDBManager()
